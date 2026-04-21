"""InvestigateState — /investigate per-hypothesis state machine with auto-freeze.

§04-CONTEXT D-15 / D-16 / §REQUIREMENTS SAFETY-05 / QUALITY-07. Per-hypothesis
iron-law loop: reviewer declares a module path -> state validates + freezes the
path via FreezeRegistry (Phase 2) -> reviewer tests hypothesis -> on
confirmed/disconfirmed/abandon the state unfreezes. Max 3 hypotheses
(halt-after-3 policy).

Persistence: JSON under
  ~/.clawteam/teams/<team>/sprints/<sprint_id>/skills/investigate/reviewer/state.json
via file_locked + atomic_write_text.

Module-path rule (D-16): reviewer declares an explicit path; state machine
validates existence + workspace-containment + NO glob characters. No regex-
from-stack-trace. Safety: one wrong wildcard would freeze the whole tree.

FreezeRegistry reason format: 'investigate:<sprint_id>:<hypothesis_id>'.
Grep-correlatable via freeze_audit.jsonl (Phase 7 operator tooling).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.harness.freeze_registry import FreezeRegistry
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir


InvestigateStateName = Literal[
    "idle",
    "hypothesis_declared",
    "hypothesis_testing",
    "hypothesis_disconfirmed",
    "resolved",
    "halted_after_3",
    "abandoned",
]

InvestigateEvent = Literal[
    "open_investigation",
    "module_validated",
    "confirmed",
    "disconfirmed",
    "next_hypothesis_if_under_3",
    "reached_3",
    "abandon",
]


# Single source of truth; golden test asserts matches fixture JSON.
_TRANSITIONS: dict[tuple[InvestigateStateName, InvestigateEvent], InvestigateStateName] = {
    ("idle",                    "open_investigation"):         "hypothesis_declared",
    ("hypothesis_declared",     "module_validated"):           "hypothesis_testing",
    ("hypothesis_testing",      "confirmed"):                  "resolved",
    ("hypothesis_testing",      "disconfirmed"):               "hypothesis_disconfirmed",
    ("hypothesis_disconfirmed", "next_hypothesis_if_under_3"): "hypothesis_declared",
    ("hypothesis_disconfirmed", "reached_3"):                  "halted_after_3",
    ("hypothesis_testing",      "abandon"):                    "abandoned",
    ("hypothesis_declared",     "abandon"):                    "abandoned",
}

_FINAL_STATES: tuple[InvestigateStateName, ...] = ("resolved", "halted_after_3", "abandoned")
MAX_HYPOTHESES: int = 3
TURN_BUDGET: int = 12
FREEZE_REASON_TEMPLATE = "investigate:{sprint_id}:{hypothesis_id}"

# States where FreezeRegistry holds a module (i.e., post-module_validated,
# pre-unfreeze). Used by abandon/complete to decide whether to unfreeze.
_FROZEN_STATES: frozenset[InvestigateStateName] = frozenset({
    "hypothesis_testing", "hypothesis_disconfirmed",
})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_module_path(module_path: str, workspace_branch: str) -> Path:
    """D-16: reject glob characters + enforce workspace containment.

    Raises ValueError on violation. Returns the resolved Path on success.
    """
    if not module_path or not isinstance(module_path, str):
        raise ValueError("module_path must be a non-empty string")
    for bad in ("**", "*", "?", "["):
        if bad in module_path:
            raise ValueError(
                f"module_path must be an explicit path, not a glob "
                f"(contains {bad!r}): {module_path!r}"
            )
    if not workspace_branch:
        raise ValueError("workspace_branch is empty; cannot validate scope")

    ws = Path(workspace_branch).resolve(strict=False)
    candidate = Path(module_path)
    resolved = (
        candidate.resolve(strict=False)
        if candidate.is_absolute()
        else (ws / candidate).resolve(strict=False)
    )

    try:
        resolved.relative_to(ws)
    except ValueError as exc:
        raise ValueError(
            f"module_path {module_path!r} is outside workspace_branch {workspace_branch!r}"
        ) from exc

    return resolved


class InvestigateTransition(BaseModel):
    from_state: InvestigateStateName
    to_state: InvestigateStateName
    event: InvestigateEvent
    ts: str
    turn: int
    hypothesis_id: int | None = None
    module_path: str | None = None


class InvestigateResult(BaseModel):
    ok: bool
    reason: str = ""
    new_state: InvestigateStateName | None = None
    freeze_applied: bool = False
    unfreeze_applied: bool = False


class InvestigateState(BaseModel):
    """Per-hypothesis /investigate state machine (reviewer persona, Review phase)."""

    skill: Literal["investigate"] = "investigate"
    role: Literal["reviewer"] = "reviewer"
    team: str
    sprint_id: str
    workspace_branch: str = ""
    current_state: InvestigateStateName = "idle"
    history: list[InvestigateTransition] = Field(default_factory=list)
    hypothesis_count: int = 0
    current_hypothesis_id: int | None = None
    current_module_path: str | None = None
    completed_at: str | None = None

    def handle(
        self,
        event: InvestigateEvent,
        *,
        turn: int,
        module_path: str | None = None,
        hypothesis_id: int | None = None,
        registry: FreezeRegistry | None = None,
    ) -> InvestigateResult:
        """Advance the state machine by one event, applying freeze/unfreeze side effects.

        Callers (SprintConductor Plan 04-10) pass the FreezeRegistry instance;
        tests may pass a fake for isolation.
        """
        if self.current_state in _FINAL_STATES:
            return InvestigateResult(
                ok=False, reason=f"state machine already final: {self.current_state}"
            )

        key = (self.current_state, event)
        if key not in _TRANSITIONS:
            return InvestigateResult(
                ok=False,
                reason=f"invalid transition {self.current_state} --{event}-->",
            )
        next_state = _TRANSITIONS[key]

        freeze_applied = False
        unfreeze_applied = False

        # -- Side effects per transition --------------------------------

        if event == "module_validated":
            if module_path is None or hypothesis_id is None:
                return InvestigateResult(
                    ok=False,
                    reason="module_validated requires module_path and hypothesis_id",
                )
            try:
                _validate_module_path(module_path, self.workspace_branch)
            except ValueError as exc:
                return InvestigateResult(ok=False, reason=str(exc))
            reason_str = FREEZE_REASON_TEMPLATE.format(
                sprint_id=self.sprint_id, hypothesis_id=hypothesis_id,
            )
            if registry is not None:
                registry.freeze(
                    path=module_path,
                    agent="reviewer",
                    reason=reason_str,
                    actor="reviewer",
                )
                freeze_applied = True
            self.current_hypothesis_id = hypothesis_id
            self.current_module_path = module_path

        elif event in {"confirmed", "abandon", "reached_3"}:
            # Unfreeze the module from the most recent hypothesis, if any.
            if (
                self.current_state in _FROZEN_STATES
                and self.current_module_path
                and registry is not None
            ):
                reason_str = FREEZE_REASON_TEMPLATE.format(
                    sprint_id=self.sprint_id, hypothesis_id=self.current_hypothesis_id,
                )
                registry.unfreeze(
                    path=self.current_module_path,
                    agent="reviewer",
                    reason=reason_str,
                    actor="reviewer",
                )
                unfreeze_applied = True

        elif event == "next_hypothesis_if_under_3":
            # Unfreeze old hypothesis; caller will re-declare + re-freeze via
            # module_validated next turn.
            if self.current_module_path and registry is not None:
                old_reason = FREEZE_REASON_TEMPLATE.format(
                    sprint_id=self.sprint_id, hypothesis_id=self.current_hypothesis_id,
                )
                registry.unfreeze(
                    path=self.current_module_path,
                    agent="reviewer",
                    reason=old_reason,
                    actor="reviewer",
                )
                unfreeze_applied = True
            self.hypothesis_count += 1  # count of declared attempts
            self.current_module_path = None
            self.current_hypothesis_id = None

        # -- Commit transition ------------------------------------------
        self.history.append(
            InvestigateTransition(
                from_state=self.current_state,
                to_state=next_state,
                event=event,
                ts=_now_iso(),
                turn=turn,
                hypothesis_id=hypothesis_id or self.current_hypothesis_id,
                module_path=module_path or self.current_module_path,
            )
        )
        self.current_state = next_state
        if next_state in _FINAL_STATES:
            self.completed_at = _now_iso()

        return InvestigateResult(
            ok=True,
            new_state=next_state,
            freeze_applied=freeze_applied,
            unfreeze_applied=unfreeze_applied,
        )

    # -- Persistence ----------------------------------------------------

    @staticmethod
    def _state_path(team: str, sprint_id: str) -> Path:
        validate_identifier(team, "team name")
        validate_identifier(sprint_id, "sprint id")
        root = get_data_dir() / "teams"
        skill_dir = ensure_within_root(
            root, team, "sprints", sprint_id, "skills", "investigate", "reviewer",
        )
        return skill_dir / "state.json"

    def save(self) -> Path:
        path = self._state_path(self.team, self.sprint_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_locked(path):
            atomic_write_text(path, self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, team: str, sprint_id: str) -> "InvestigateState":
        path = cls._state_path(team, sprint_id)
        with file_locked(path):
            raw = path.read_text(encoding="utf-8")
        return cls.model_validate_json(raw)
