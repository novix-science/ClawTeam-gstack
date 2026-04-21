---
phase: 04
plan: 09
type: execute
wave: 2
depends_on: [01, 02]
files_modified:
  - clawteam/templates/gstack/skills/investigate/__init__.py
  - clawteam/templates/gstack/skills/investigate/state.py
  - tests/fixtures/gstack_state_machines/investigate.transitions.json
  - tests/test_investigate_state_machine.py
autonomous: true
requirements: [QUALITY-07, SAFETY-05]
must_haves:
  truths:
    - "InvestigateState pydantic class exposes current_state, history, handle(event, turn), save(), load()."
    - "State machine halts at reached_3 after 3 failed hypotheses (iron-law)."
    - "on_enter_hypothesis(module_path, hypothesis_id) calls FreezeRegistry.freeze with reason='investigate:<sprint>:<hypothesis>'."
    - "on_complete / on_abandon unfreeze matching reason string."
    - "Module path validation rejects glob-containing paths (no '**', '*', '?' in path) and paths outside workspace_branch root."
    - "freeze_audit.jsonl records investigate entries correlatable by reason prefix."
    - "State survives full process restart via pydantic round-trip (CORE-07)."
  artifacts:
    - path: "clawteam/templates/gstack/skills/investigate/state.py"
      provides: "InvestigateState pydantic + freeze wiring + path validation"
      contains: "class InvestigateState(BaseModel)"
      min_lines: 140
    - path: "tests/fixtures/gstack_state_machines/investigate.transitions.json"
      provides: "Canonical hypothesis transition graph with max_hypotheses=3"
      contains: "\"max_hypotheses\": 3"
    - path: "tests/test_investigate_state_machine.py"
      provides: "Transition + freeze + path-validation + iron-law halt tests"
      contains: "def test_freezes_on_enter"
  key_links:
    - from: "clawteam/templates/gstack/skills/investigate/state.py"
      to: "clawteam/harness/freeze_registry.py"
      via: "FreezeRegistry.freeze(module_path, agent='reviewer', reason='investigate:<sprint>:<hypothesis>', actor='reviewer')"
      pattern: "investigate:"
    - from: "clawteam/harness/freeze_registry.py::freeze_audit.jsonl"
      to: "Phase 7 operators"
      via: "grep for reason startswith('investigate:')"
---

<objective>
Ship the `/investigate` state machine with auto-freeze wiring per D-15/D-16/SAFETY-05. State machine persists under `~/.clawteam/teams/<team>/sprints/<sprint_id>/skills/investigate/reviewer/state.json`. On entry to `hypothesis_testing`, calls the existing `FreezeRegistry.freeze(module_path, reason=f"investigate:{sprint}:{hypothesis}")`. On complete/abandon, calls matching unfreeze. Halt-after-3 (iron-law) terminal state. Module path is reviewer-declared, validated against glob-containing strings (no auto-derive from stack-trace regex per D-16).

Purpose: One of the three Phase-4 state machines + the SAFETY-05 auto-freeze wiring. Reuses Phase 2's existing `FreezeRegistry.freeze/unfreeze` API unchanged — no new persistence. Reason string structured as `investigate:<sprint_id>:<hypothesis_id>` so `freeze_audit.jsonl` is grep-correlatable by Phase 7 operators.

Output: 1 state module + 1 fixture JSON + 1 test file. No modifications to FreezeRegistry or Phase 2 code.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-RESEARCH.md

<interfaces>
From clawteam/harness/freeze_registry.py (existing API — lines 149-171):
```python
def freeze(
    self,
    path: str | Path,
    *,
    agent: str,
    reason: str,
    actor: str,
) -> None:
    """Append a path to the frozen set; writes freeze_audit.jsonl entry."""

def unfreeze(
    self,
    path: str | Path,
    *,
    agent: str,
    reason: str,
    actor: str,
) -> None:
    """Release a frozen path; writes freeze_audit.jsonl entry."""
```

From 04-RESEARCH §Example 2 (investigate fixture):
- initial_state: "idle"
- final_states: ["resolved", "halted_after_3", "abandoned"]
- max_hypotheses: 3
- transitions include: idle → open_investigation → hypothesis_declared → module_validated (side_effect: freeze) → hypothesis_testing → {confirmed,disconfirmed,abandon} → ...

From D-16 rule:
- Reviewer MUST declare module path explicitly; no regex-from-stack-trace.
- State machine validates path: exists + is under workspace_branch root + contains no glob characters (**, *, ?).

From tests/fixtures/gstack_skills/review.md (iron-law language — halt after 3 failed hypotheses).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create skills/investigate package + fixture JSON</name>
  <files>clawteam/templates/gstack/skills/investigate/__init__.py, tests/fixtures/gstack_state_machines/investigate.transitions.json</files>
  <read_first>
    - tests/fixtures/gstack_skills/review.md (iron-law halt-after-3 language)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-RESEARCH.md (§Example 2 — investigate fixture verbatim)
  </read_first>
  <action>
Create `clawteam/templates/gstack/skills/investigate/__init__.py`:
```python
"""/investigate multi-turn state machine with auto-freeze (§04-CONTEXT D-15/D-16 — Plan 04-09)."""

from clawteam.templates.gstack.skills.investigate.state import (
    InvestigateState,
    InvestigateEvent,
    InvestigateStateName,
    InvestigateTransition,
    InvestigateResult,
)

__all__ = [
    "InvestigateState",
    "InvestigateEvent",
    "InvestigateStateName",
    "InvestigateTransition",
    "InvestigateResult",
]
```

Create `tests/fixtures/gstack_state_machines/investigate.transitions.json`:
```json
{
  "skill": "investigate",
  "role": "reviewer",
  "initial_state": "idle",
  "final_states": ["resolved", "halted_after_3", "abandoned"],
  "turn_budget": 12,
  "max_hypotheses": 3,
  "transitions": [
    {"from": "idle",                    "event": "open_investigation",        "to": "hypothesis_declared"},
    {"from": "hypothesis_declared",     "event": "module_validated",          "to": "hypothesis_testing",        "side_effect": "freeze_module"},
    {"from": "hypothesis_testing",      "event": "confirmed",                 "to": "resolved",                  "side_effect": "unfreeze_module"},
    {"from": "hypothesis_testing",      "event": "disconfirmed",              "to": "hypothesis_disconfirmed"},
    {"from": "hypothesis_disconfirmed", "event": "next_hypothesis_if_under_3","to": "hypothesis_declared",       "side_effect": "unfreeze_module"},
    {"from": "hypothesis_disconfirmed", "event": "reached_3",                 "to": "halted_after_3",            "side_effect": "unfreeze_module"},
    {"from": "hypothesis_testing",      "event": "abandon",                   "to": "abandoned",                 "side_effect": "unfreeze_module"},
    {"from": "hypothesis_declared",     "event": "abandon",                   "to": "abandoned"}
  ],
  "freeze_reason_template": "investigate:{sprint_id}:{hypothesis_id}"
}
```
  </action>
  <verify>
    <automated>python3 -c "import json; d = json.load(open('tests/fixtures/gstack_state_machines/investigate.transitions.json')); assert d['max_hypotheses'] == 3; assert 'halted_after_3' in d['final_states']; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - ls clawteam/templates/gstack/skills/investigate/__init__.py succeeds
    - ls tests/fixtures/gstack_state_machines/investigate.transitions.json succeeds
    - JSON parses with max_hypotheses==3 and final_states contains "halted_after_3"
    - JSON freeze_reason_template == "investigate:{sprint_id}:{hypothesis_id}"
  </acceptance_criteria>
  <done>Package scaffolding + fixture ready for Task 2</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement InvestigateState with transitions, freeze wiring, path validation</name>
  <files>clawteam/templates/gstack/skills/investigate/state.py, tests/test_investigate_state_machine.py</files>
  <read_first>
    - clawteam/templates/gstack/skills/office_hours/state.py (Plan 07 reference shape)
    - clawteam/harness/freeze_registry.py (entire file — freeze/unfreeze API)
    - tests/test_freeze_registry.py (pattern for FreezeRegistry test setup)
    - tests/fixtures/gstack_state_machines/investigate.transitions.json (Task 1)
  </read_first>
  <behavior>
    - Test 1 (test_initial_state_is_idle): Fresh state → current_state == "idle", hypothesis_count == 0.
    - Test 2 (test_transitions_match_fixture): In-code _TRANSITIONS bijective with fixture JSON transitions (match on from+event+to).
    - Test 3 (test_max_hypotheses_is_3): Constant MAX_HYPOTHESES == 3; matches fixture.
    - Test 4 (test_open_investigation_transitions_to_hypothesis_declared): idle → open_investigation → hypothesis_declared.
    - Test 5 (test_module_validated_enters_testing_and_freezes): handle("module_validated", turn=N, module_path=VALID_PATH, sprint_id="s", hypothesis_id=1) calls FreezeRegistry.freeze with reason=="investigate:s:1"; state advances to hypothesis_testing.
    - Test 6 (test_confirmed_unfreezes_and_resolves): From hypothesis_testing, handle("confirmed") → state resolved; FreezeRegistry.unfreeze called with matching reason.
    - Test 7 (test_disconfirmed_goes_to_disconfirmed_state): From hypothesis_testing, handle("disconfirmed") → hypothesis_disconfirmed (no freeze change yet).
    - Test 8 (test_next_hypothesis_under_3_unfreezes_then_refreezes): After 1 disconfirmed, handle("next_hypothesis_if_under_3", module_path=NEW_VALID, hypothesis_id=2) → unfreeze old + freeze new; state back to hypothesis_declared; hypothesis_count increments.
    - Test 9 (test_reached_3_halts): After 3 disconfirmed cycles, handle("reached_3") → halted_after_3; unfreeze called.
    - Test 10 (test_abandon_from_testing_unfreezes): abandon from hypothesis_testing → abandoned + unfreeze.
    - Test 11 (test_abandon_from_declared_no_unfreeze): abandon from hypothesis_declared (before freeze) → abandoned; FreezeRegistry NOT called.
    - Test 12 (test_path_validation_rejects_glob): module_path="src/**/*.py" raises ValueError.
    - Test 13 (test_path_validation_rejects_wildcard): module_path containing "?" or "*" raises.
    - Test 14 (test_path_validation_rejects_outside_workspace): module_path absolute outside workspace_branch raises.
    - Test 15 (test_freeze_audit_reason_format): Mock FreezeRegistry to capture call; assert reason == "investigate:<sprint_id>:<hypothesis_id>" format.
    - Test 16 (test_save_load_round_trip): Save at hypothesis_testing, reload → full state + history restored.
    - Test 17 (test_persistence_survives_simulated_restart).
    - Test 18 (test_hypothesis_count_increments).
  </behavior>
  <action>
Create `clawteam/templates/gstack/skills/investigate/state.py`:

```python
"""InvestigateState — /investigate per-hypothesis state machine with auto-freeze.

§04-CONTEXT D-15 / D-16 / §REQUIREMENTS SAFETY-05 / QUALITY-07. Per-hypothesis
iron-law loop: reviewer declares a module path → state validates + freezes the
path via FreezeRegistry (Phase 2) → reviewer tests hypothesis → on
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
    resolved = (ws / candidate).resolve(strict=False) if not candidate.is_absolute() else candidate.resolve(strict=False)

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

        # ── Side effects per transition ────────────────────────────────

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
            if self.current_state in _FROZEN_STATES and self.current_module_path and registry is not None:
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
            # Unfreeze old hypothesis; caller will re-declare + re-freeze via module_validated next turn.
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

        # ── Commit transition ──────────────────────────────────────────
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

    # ── Persistence ────────────────────────────────────────────────────

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
```

Create `tests/test_investigate_state_machine.py`:

```python
"""Unit + fixture-driven tests for InvestigateState (Plan 04-09 — SAFETY-05 + QUALITY-07)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clawteam.templates.gstack.skills.investigate import InvestigateState
from clawteam.templates.gstack.skills.investigate.state import (
    FREEZE_REASON_TEMPLATE,
    MAX_HYPOTHESES,
    _FINAL_STATES,
    _TRANSITIONS,
    _validate_module_path,
)


_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gstack_state_machines" / "investigate.transitions.json"


class _FakeRegistry:
    """Captures freeze/unfreeze calls for assertion."""

    def __init__(self):
        self.freezes: list[dict] = []
        self.unfreezes: list[dict] = []

    def freeze(self, *, path, agent, reason, actor):
        self.freezes.append({"path": str(path), "agent": agent, "reason": reason, "actor": actor})

    def unfreeze(self, *, path, agent, reason, actor):
        self.unfreezes.append({"path": str(path), "agent": agent, "reason": reason, "actor": actor})


@pytest.fixture
def fixture_dict() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _new_state(team="t", sprint_id="s1", workspace="/tmp/repo") -> InvestigateState:
    return InvestigateState(team=team, sprint_id=sprint_id, workspace_branch=workspace)


def test_initial_state_is_idle():
    s = _new_state()
    assert s.current_state == "idle"
    assert s.hypothesis_count == 0
    assert s.current_module_path is None
    assert s.current_hypothesis_id is None


def test_transitions_match_fixture(fixture_dict):
    code_triples = {(k[0], k[1], v) for k, v in _TRANSITIONS.items()}
    fixture_triples = {(t["from"], t["event"], t["to"]) for t in fixture_dict["transitions"]}
    assert code_triples == fixture_triples


def test_max_hypotheses_is_3(fixture_dict):
    assert MAX_HYPOTHESES == fixture_dict["max_hypotheses"]
    assert MAX_HYPOTHESES == 3


def test_final_states_match_fixture(fixture_dict):
    assert set(_FINAL_STATES) == set(fixture_dict["final_states"])


def test_freeze_reason_template_matches_fixture(fixture_dict):
    assert FREEZE_REASON_TEMPLATE == fixture_dict["freeze_reason_template"]


def test_open_investigation_transitions_to_hypothesis_declared():
    s = _new_state()
    reg = _FakeRegistry()
    res = s.handle("open_investigation", turn=1, registry=reg)
    assert res.ok
    assert s.current_state == "hypothesis_declared"
    assert reg.freezes == []  # no freeze yet


def test_module_validated_enters_testing_and_freezes(tmp_path):
    ws = tmp_path
    (ws / "src").mkdir()
    (ws / "src" / "module.py").write_text("x = 1")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()

    s.handle("open_investigation", turn=1, registry=reg)
    res = s.handle(
        "module_validated",
        turn=2,
        module_path="src/module.py",
        hypothesis_id=1,
        registry=reg,
    )
    assert res.ok
    assert s.current_state == "hypothesis_testing"
    assert res.freeze_applied is True
    assert len(reg.freezes) == 1
    assert reg.freezes[0]["reason"] == "investigate:s1:1"
    assert reg.freezes[0]["agent"] == "reviewer"
    assert reg.freezes[0]["actor"] == "reviewer"


def test_confirmed_unfreezes_and_resolves(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    res = s.handle("confirmed", turn=3, registry=reg)
    assert res.ok
    assert s.current_state == "resolved"
    assert res.unfreeze_applied is True
    assert len(reg.unfreezes) == 1
    assert reg.unfreezes[0]["reason"] == "investigate:s1:1"


def test_disconfirmed_goes_to_disconfirmed_state(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    res = s.handle("disconfirmed", turn=3, registry=reg)
    assert res.ok
    assert s.current_state == "hypothesis_disconfirmed"
    # No unfreeze yet on disconfirmed alone.
    assert res.unfreeze_applied is False


def test_next_hypothesis_under_3_unfreezes_old(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    (ws / "y.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    s.handle("disconfirmed", turn=3, registry=reg)
    res = s.handle("next_hypothesis_if_under_3", turn=4, registry=reg)
    assert res.ok
    assert s.current_state == "hypothesis_declared"
    assert res.unfreeze_applied is True
    assert reg.unfreezes[-1]["reason"] == "investigate:s1:1"


def test_reached_3_halts(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    s.handle("disconfirmed", turn=3, registry=reg)
    res = s.handle("reached_3", turn=4, registry=reg)
    assert res.ok
    assert s.current_state == "halted_after_3"
    assert res.unfreeze_applied is True


def test_abandon_from_testing_unfreezes(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    res = s.handle("abandon", turn=3, registry=reg)
    assert res.ok
    assert s.current_state == "abandoned"
    assert res.unfreeze_applied is True


def test_abandon_from_declared_no_unfreeze():
    s = _new_state()
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    res = s.handle("abandon", turn=2, registry=reg)
    assert res.ok
    assert s.current_state == "abandoned"
    assert res.unfreeze_applied is False
    assert reg.unfreezes == []


# ── Path validation (D-16) ────────────────────────────────────────────

def test_path_validation_rejects_doublestar(tmp_path):
    with pytest.raises(ValueError, match="glob"):
        _validate_module_path("src/**/*.py", str(tmp_path))


def test_path_validation_rejects_wildcard_single_star(tmp_path):
    with pytest.raises(ValueError, match="glob"):
        _validate_module_path("src/*.py", str(tmp_path))


def test_path_validation_rejects_question_mark(tmp_path):
    with pytest.raises(ValueError, match="glob"):
        _validate_module_path("src/a?.py", str(tmp_path))


def test_path_validation_rejects_outside_workspace(tmp_path):
    with pytest.raises(ValueError, match="outside workspace"):
        _validate_module_path("/etc/passwd", str(tmp_path))


def test_path_validation_rejects_empty():
    with pytest.raises(ValueError):
        _validate_module_path("", "/tmp/x")


def test_path_validation_accepts_valid(tmp_path):
    (tmp_path / "ok.py").write_text("")
    # Should not raise
    resolved = _validate_module_path("ok.py", str(tmp_path))
    assert resolved.name == "ok.py"


def test_module_validated_without_module_path_fails(tmp_path):
    s = _new_state(workspace=str(tmp_path))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    res = s.handle("module_validated", turn=2, registry=reg)
    assert not res.ok
    assert "requires module_path" in res.reason


def test_module_validated_rejects_glob_path(tmp_path):
    s = _new_state(workspace=str(tmp_path))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    res = s.handle("module_validated", turn=2, module_path="src/**/*.py", hypothesis_id=1, registry=reg)
    assert not res.ok
    assert "glob" in res.reason
    assert s.current_state == "hypothesis_declared"  # not advanced


# ── Persistence ───────────────────────────────────────────────────────

def test_save_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    ws = tmp_path / "ws"; ws.mkdir()
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    s.save()
    loaded = InvestigateState.load("t", "s1")
    assert loaded.current_state == "hypothesis_testing"
    assert loaded.current_module_path == "x.py"
    assert loaded.current_hypothesis_id == 1


def test_persistence_survives_simulated_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    ws = tmp_path / "ws"; ws.mkdir()
    (ws / "x.py").write_text("")
    orig = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    orig.handle("open_investigation", turn=1, registry=reg)
    orig.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    orig.save()
    del orig
    loaded = InvestigateState.load("t", "s1")
    assert loaded.current_state == "hypothesis_testing"
    assert [h.turn for h in loaded.history] == [1, 2]
```
  </action>
  <verify>
    <automated>pytest tests/test_investigate_state_machine.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class InvestigateState(BaseModel)" clawteam/templates/gstack/skills/investigate/state.py
    - grep -q "def _validate_module_path" clawteam/templates/gstack/skills/investigate/state.py
    - grep -q "FREEZE_REASON_TEMPLATE" clawteam/templates/gstack/skills/investigate/state.py
    - grep -q "MAX_HYPOTHESES: int = 3" clawteam/templates/gstack/skills/investigate/state.py
    - wc -l clawteam/templates/gstack/skills/investigate/state.py returns >= 140
    - pytest tests/test_investigate_state_machine.py -x -q exits 0 (20+ tests pass)
    - pytest tests/test_freeze_registry.py -x -q stays green (existing FreezeRegistry tests unaffected)
  </acceptance_criteria>
  <done>InvestigateState + freeze wiring + path validation ship; fixture bijective; SAFETY-05 enforced</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Reviewer-declared module_path ↔ FreezeRegistry | Glob or out-of-workspace path would freeze the wrong scope |
| Path validation ↔ symlink resolution | Symlinked module_path could escape workspace |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-27 | E (Elevation of privilege) | Glob-containing module_path | mitigate | _validate_module_path rejects "**", "*", "?", "[" before FreezeRegistry call |
| T-04-28 | T (Tampering) | Module_path outside workspace | mitigate | resolved.relative_to(workspace) raises on escape |
| T-04-29 | I (Information disclosure) | freeze_audit.jsonl reason content | accept | Reason contains sprint_id + hypothesis_id — no secrets |
| T-04-30 | D (DoS) | Over-broad module_path (e.g., workspace root) | accept | Reviewer declares path intentionally; operator can `clawteam unfreeze` if mistake |
</threat_model>

<verification>
- [ ] `pytest tests/test_investigate_state_machine.py -x -q` exits 0 (20+ tests)
- [ ] `pytest tests/test_freeze_registry.py -x -q` green (existing Phase 2 tests unaffected)
- [ ] Golden: in-code `_TRANSITIONS` bijective with fixture JSON
- [ ] Freeze reason format = `investigate:<sprint>:<hypothesis>` (verified in test_module_validated_enters_testing_and_freezes)
</verification>

<success_criteria>
- [ ] InvestigateState importable
- [ ] 8 transitions form bijective graph with fixture
- [ ] Path validation blocks glob chars + out-of-workspace paths
- [ ] FreezeRegistry.freeze called with structured reason string on hypothesis_testing entry
- [ ] FreezeRegistry.unfreeze called matching reason on confirmed/abandon/reached_3/next_hypothesis
- [ ] State survives restart
- [ ] 20+ tests pass; FreezeRegistry existing tests unregressed
</success_criteria>

<output>
Create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-09-investigate-state-machine-freeze-SUMMARY.md`.
</output>
