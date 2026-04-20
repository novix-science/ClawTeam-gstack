"""SprintConductor — per-team sprint-level loop owner (Plan 02-11, §02-CONTEXT D-22..D-29).

SprintConductor sits above PhaseRunner:

- PhaseRunner._gates[phase] holds the registered gates.
- SprintConductor.advance_phase(sprint_id) invokes the three-gate chain
  (EvidenceGate → forced_progress_gate → conditional InteractionGate) per
  §02-CONTEXT Integration Points and writes the outcome.
- SprintConductor.pause(sprint_id) / resume(sprint_id) handle durable-state
  checkpointing + event replay (CORE-07).

Pause/resume is a strict CORE-07 requirement: the checkpoint survives a full
orchestrator restart. See tests/test_sprint_conductor.py::test_resume_after_process_restart.

INT-06 auto_advance semantics (§02-CONTEXT D-23):

- auto_advance=True  → InteractionGate only when unanswered questions exist.
- auto_advance=False → InteractionGate on every transition.
- force_interactive_phases=["ship"] (Phase 4 reserved) → always insert
  InteractionGate regardless of auto_advance / pending questions.

Three-layer cap override (§02-CONTEXT D-29):

- CLI flag > CLAWTEAM_ARTIFACT_CAP_KB env > SprintState default.

Pitfall #8 invariant: register_safety_subscribers(bus) is called from
SprintConductor.__init__ ONLY — HarnessOrchestrator does NOT instantiate a
conductor, so existing Phase 0 templates keep their Before* events as no-ops
(SC#10 regression matrix 12/12 stays green).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from threading import RLock
from typing import TYPE_CHECKING

from clawteam.harness.freeze_registry import (
    register_safety_subscribers,
    set_careful_veto_mode,
)
from clawteam.sprint.state import (
    SprintState,
    load_sprint_state,
    save_sprint_state,
)
from clawteam.team.models import get_data_dir

if TYPE_CHECKING:  # pragma: no cover — type-check only
    from clawteam.events.bus import EventBus


# ── Error types ────────────────────────────────────────────────────────────


class AmbiguousSprintError(ValueError):
    """Raised when a sprint prefix matches multiple sprint ids (§02-CONTEXT D-25).

    Attributes:
        prefix: The ambiguous prefix that was queried.
        candidates: Sorted list of full sprint ids matching the prefix.
    """

    def __init__(self, prefix: str, candidates: list[str]):
        self.prefix = prefix
        self.candidates = sorted(candidates)
        super().__init__(
            f"Ambiguous sprint prefix {prefix!r}; candidates: {self.candidates}"
        )


class SprintNotFoundError(ValueError):
    """Raised when a sprint id or prefix matches no sprint under the team dir."""

    def __init__(self, identifier: str):
        self.identifier = identifier
        super().__init__(f"Sprint not found: {identifier!r}")


class MissingTeamError(ValueError):
    """Raised when SprintConductor is constructed without a team name (§02-CONTEXT D-24).

    CLI surface (Plan 02-12) enforces --team or $CLAWTEAM_TEAM; this error
    surfaces the same contract at the conductor level so non-CLI callers
    get the same invariant check.
    """

    def __init__(
        self, message: str = "Team name is required (--team or CLAWTEAM_TEAM env)"
    ):
        super().__init__(message)


# ── Default first-phase fallback ───────────────────────────────────────────

# 7-phase gstack order (PROJECT.md §Sprint model). Used when the PhaseRegistry
# is empty at conductor construction time (e.g., plugin hasn't loaded yet).
GSTACK_PHASE_ORDER: list[str] = [
    "think",
    "plan",
    "build",
    "review",
    "test",
    "ship",
    "reflect",
]

DEFAULT_FIRST_PHASE = "think"


# ── Cap env-var keys (§02-CONTEXT D-29 + identity._env multi-generation) ───

_ARTIFACT_CAP_ENV_KEYS: tuple[str, ...] = (
    "CLAWTEAM_ARTIFACT_CAP_KB",
    "OH_ARTIFACT_CAP_KB",
    "CLAUDE_CODE_ARTIFACT_CAP_KB",
)
_PHASE_CAP_ENV_KEYS: tuple[str, ...] = (
    "CLAWTEAM_PHASE_ARTIFACT_CAP_KB",
    "OH_PHASE_ARTIFACT_CAP_KB",
    "CLAUDE_CODE_PHASE_ARTIFACT_CAP_KB",
)


def _env_first(keys: tuple[str, ...], default: str = "") -> str:
    """Return the first non-empty env value from ``keys`` else ``default``.

    Mirrors ``clawteam.identity._env`` but accepts a tuple rather than
    hard-coded positional arguments so the cap-resolver can iterate over any
    number of generation-aliased env names.
    """
    for key in keys:
        val = os.environ.get(key)
        if val:
            return val
    return default


def _resolve_cap(
    cli_override: int | None,
    env_keys: tuple[str, ...],
    default_bytes: int,
) -> int:
    """Resolve the effective cap per §02-CONTEXT D-29 precedence: CLI > env > default.

    ``cli_override`` semantics: callers pass either bytes (>= 1024) or KB (< 1024).
    Callers from CLI layers typically pass KB; callers from tests often pass
    explicit bytes. The threshold disambiguates without forcing two overloads.
    """
    if cli_override is not None:
        return cli_override * 1024 if cli_override < 1024 else cli_override
    env_val = _env_first(env_keys)
    if env_val:
        try:
            return int(env_val) * 1024
        except ValueError:
            pass  # fall through to default on non-integer env value
    return default_bytes


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Gate chain composition ──────────────────────────────────────────────────


def _first_phase() -> str:
    """Return the first registered phase, or DEFAULT_FIRST_PHASE if registry empty."""
    try:
        from clawteam.harness.phase_registry import get_registry

        ordered = get_registry().ordered_names()
        if ordered:
            return ordered[0]
    except Exception:  # pragma: no cover — defensive
        pass
    return DEFAULT_FIRST_PHASE


def _next_phase(current: str) -> str | None:
    """Return the phase after ``current`` in the PhaseRegistry ordering.

    Falls back to the hardcoded 7-phase gstack order when the registry is
    empty or does not contain ``current``. Returns None when ``current`` is
    the last phase (sprint is complete — CORE-05).
    """
    try:
        from clawteam.harness.phase_registry import get_registry

        phases = get_registry().ordered_names()
        if current in phases:
            idx = phases.index(current)
            return phases[idx + 1] if idx + 1 < len(phases) else None
    except Exception:  # pragma: no cover — defensive
        pass
    # Fallback to hardcoded gstack order.
    if current in GSTACK_PHASE_ORDER:
        idx = GSTACK_PHASE_ORDER.index(current)
        return (
            GSTACK_PHASE_ORDER[idx + 1]
            if idx + 1 < len(GSTACK_PHASE_ORDER)
            else None
        )
    return None


# ── SprintConductor ─────────────────────────────────────────────────────────


class SprintConductor:
    """Per-team sprint-level loop owner.

    Phase 2 is single-sprint correctness. Ten-concurrent-sprint coverage is
    verified in Phase 7 (see §02-CONTEXT D-22).

    Construction contract:
        conductor = SprintConductor(
            team_name="my-team",
            force_interactive_phases=["ship"],  # Phase 4 reservation
            artifact_cap_bytes=100 * 1024,       # CLI override (Plan 02-12)
            phase_artifact_cap_bytes=1_000_000,  # CLI override
            bus=EventBus(),                      # tests inject; default is global
        )

    Safety-rail invariant (Pitfall #8): __init__ calls
    ``register_safety_subscribers(self.bus)`` so FreezeRegistry Before*
    subscribers activate ONLY for gstack sprints. Existing Phase 0 templates
    that do not instantiate SprintConductor keep their EventBus with zero
    safety subscribers; Before* events are no-ops for them.
    """

    def __init__(
        self,
        team_name: str,
        *,
        force_interactive_phases: list[str] | None = None,
        artifact_cap_bytes: int | None = None,
        phase_artifact_cap_bytes: int | None = None,
        bus: "EventBus | None" = None,
    ) -> None:
        if not team_name:
            raise MissingTeamError()
        self.team_name = team_name
        self.force_interactive_phases: list[str] = list(
            force_interactive_phases or []
        )
        self._lock = RLock()

        # Resolve event bus — default to global; tests inject their own.
        if bus is None:
            from clawteam.events.global_bus import get_event_bus

            bus = get_event_bus()
        self.bus = bus

        # Activate safety rails (Plan 02-10). Idempotent — safe to double-call
        # per T-02-17 mitigation (see freeze_registry._subscribers_registered).
        register_safety_subscribers(self.bus)

        # Three-layer cap override (§02-CONTEXT D-29).
        self._artifact_cap_override: int = _resolve_cap(
            cli_override=artifact_cap_bytes,
            env_keys=_ARTIFACT_CAP_ENV_KEYS,
            default_bytes=50 * 1024,
        )
        self._phase_cap_override: int = _resolve_cap(
            cli_override=phase_artifact_cap_bytes,
            env_keys=_PHASE_CAP_ENV_KEYS,
            default_bytes=500 * 1024,
        )

    # ─────────────────── lifecycle ───────────────────

    def start_sprint(
        self, goal: str, auto_advance: bool = True
    ) -> SprintState:
        """Create a new sprint: write state.json, emit PhaseTransition(None→first).

        Returns the newly created SprintState. The sprint_id is
        ``uuid.uuid4().hex[:8]`` matching SprintContract.id convention (D-25).
        """
        with self._lock:
            sprint_id = uuid.uuid4().hex[:8]
            first = _first_phase()
            state = SprintState(
                sprint_id=sprint_id,
                team=self.team_name,
                goal=goal,
                current_phase=first,
                auto_advance=auto_advance,
                workspace_branch="main",
                artifact_cap_bytes=self._artifact_cap_override,
                phase_artifact_cap_bytes=self._phase_cap_override,
                status="running",
                created_at=_now_iso(),
            )
            save_sprint_state(state)
            self._emit_phase_transition(from_phase="", to_phase=first, state=state)
            return state

    def advance_phase(
        self,
        sprint_id: str,
        actor: str = "",
    ) -> tuple[bool, str]:
        """Run the gate chain; on all-pass, flip current_phase; persist.

        Returns ``(True, "")`` when the advance succeeds (phase moved OR sprint
        completed because no next phase exists). Returns ``(False, reason)``
        when any gate blocks; reason is the first blocking gate's message.

        Phase 3 Wave 0 (Plan 03-01, D-10, Pattern 4): ``actor`` defaults to
        ``""`` so every existing Phase 2 caller is unaffected (gate chain runs
        as before). When the team's TeamConfig declares a non-empty
        ``leader_role`` AND ``actor`` is non-empty, advancement is rejected
        unless ``actor == leader_role``.

        Threat T-03-03 (elevation of privilege): the conductor trusts the
        caller-supplied ``actor``. Agent identity is asserted at spawn time
        (CLAWTEAM_AGENT / CLAWTEAM_ROLE env vars set by the spawn registry);
        Phase 4 SmartReviewRouter ships cross-agent verification.
        """
        with self._lock:
            state = self._load_by_id(sprint_id)

            # Phase 3 Wave 0 (Pattern 4): leader-role enforcement. Lazy-import
            # inside the method body (convention Pattern F) to avoid a
            # module-load cycle between conductor and TeamManager.
            if actor:
                from clawteam.team.manager import TeamManager

                tmpl = TeamManager.get_team(self.team_name)
                leader_role = getattr(tmpl, "leader_role", "") if tmpl else ""
                if leader_role and actor != leader_role:
                    return (
                        False,
                        f"actor {actor!r} not authorized; only "
                        f"{leader_role!r} can advance phases",
                    )

            gates = self._build_gate_chain(state)
            for gate in gates:
                ok, reason = gate.check(state)
                if not ok:
                    return False, reason

            # All gates passed — move to next phase (or mark completed).
            old_phase = state.current_phase
            nxt = _next_phase(old_phase)
            if nxt is None:
                state.status = "completed"
                save_sprint_state(state)
                return True, "sprint completed"
            state.current_phase = nxt
            state.phase_history.append(
                {"from": old_phase, "to": nxt, "at": _now_iso()}
            )
            save_sprint_state(state)
            self._emit_phase_transition(from_phase=old_phase, to_phase=nxt, state=state)
            return True, ""

    def pause(self, sprint_id: str) -> SprintState:
        """Write status='paused' to state.json; safe to call repeatedly (idempotent)."""
        with self._lock:
            state = self._load_by_id(sprint_id)
            state.status = "paused"
            save_sprint_state(state)
            return state

    def resume(self, sprint_id: str) -> SprintState:
        """Rehydrate SprintState; flip status back to 'running'; replay last PhaseTransition.

        CORE-07: survives a full orchestrator restart. The last phase_history
        entry is re-emitted on the conductor's bus so subscribers that were
        registered in the new process observe the transition. Also restores
        the module-level /careful veto flag via set_careful_veto_mode so the
        Phase 2 destructive-command rails arm again after a process boundary.
        """
        with self._lock:
            state = self._load_by_id(sprint_id)
            if state.status not in ("paused", "running", "completed"):
                raise ValueError(
                    f"Cannot resume sprint in status={state.status!r}"
                )
            state.status = "running"
            save_sprint_state(state)
            # Re-emit last phase transition from history (CORE-07).
            if state.phase_history:
                last = state.phase_history[-1]
                self._emit_phase_transition(
                    from_phase=str(last.get("from", "") or ""),
                    to_phase=str(last.get("to", "") or ""),
                    state=state,
                )
            # Restore /careful veto mode so destructive-command rails re-arm
            # after a process boundary (Plan 02-10 + Plan 02-11 D-22 handoff).
            set_careful_veto_mode(state.careful_enabled)
            return state

    # ─────────────────── queries ───────────────────

    def list_sprints(self) -> list[SprintState]:
        """Return all sprints for this conductor's team (sorted by sprint_id).

        Pitfall #9: strictly team-scoped — no cross-team scanning. Corrupted
        state.json files are silently skipped so one bad sprint cannot take
        down the listing.
        """
        sprints_dir = get_data_dir() / "teams" / self.team_name / "sprints"
        if not sprints_dir.exists():
            return []
        result: list[SprintState] = []
        for sprint_dir in sorted(sprints_dir.iterdir()):
            state_path = sprint_dir / "state.json"
            if not state_path.exists():
                continue
            try:
                result.append(load_sprint_state(self.team_name, sprint_dir.name))
            except Exception:
                continue  # skip corrupted / unreadable
        return result

    def resolve_sprint(self, id_or_prefix: str) -> SprintState:
        """Resolve a full id or unambiguous prefix to a SprintState (§02-CONTEXT D-25).

        Raises:
            SprintNotFoundError: no sprint id under this team starts with
                ``id_or_prefix``.
            AmbiguousSprintError: more than one sprint id matches the prefix.
        """
        sprints_dir = get_data_dir() / "teams" / self.team_name / "sprints"
        if not sprints_dir.exists():
            raise SprintNotFoundError(id_or_prefix)
        candidates = sorted(
            p.name for p in sprints_dir.iterdir()
            if p.is_dir() and p.name.startswith(id_or_prefix)
        )
        if not candidates:
            raise SprintNotFoundError(id_or_prefix)
        if len(candidates) > 1:
            raise AmbiguousSprintError(id_or_prefix, candidates)
        return load_sprint_state(self.team_name, candidates[0])

    # ─────────────────── CLI serialization helpers (Plan 02-12) ───────────────────

    def most_recent_artifact(self, state: SprintState) -> str:
        """Return the most-recently-added artifact name (empty string when none).

        Insertion order is preserved by Python dict (3.7+), so the last key
        is the most recent artifact. Phase 2 ships bounded artifact counts
        (per-file + per-phase caps in D-27/D-28), so the O(n) key-list walk
        is acceptable.
        """
        if not state.artifacts:
            return ""
        return list(state.artifacts.keys())[-1]

    def status_dict(self, state: SprintState) -> dict:
        """Shape consumed by ``clawteam sprint status`` (UX-03, §02-CONTEXT D-24).

        Excludes the full artifacts map to keep status payloads small — the
        ``most_recent_artifact`` field surfaces the only per-status artifact
        signal needed for the compact status view.
        """
        return {
            "sprint_id": state.sprint_id,
            "team": state.team,
            "current_phase": state.current_phase,
            "status": state.status,
            "participants": list(state.participants),
            "pending_questions_count": len(state.pending_question_ids),
            "most_recent_artifact": self.most_recent_artifact(state),
            "auto_advance": state.auto_advance,
        }

    def show_dict(self, state: SprintState) -> dict:
        """Shape consumed by ``clawteam sprint show`` (UX-05, §02-CONTEXT D-24).

        ``artifacts_list`` contains artifact NAMES only (sorted alphabetically)
        — bodies are intentionally excluded to keep the JSON payload bounded
        for UX-05 readability. Per-artifact body fetch is out of scope for
        Phase 2 CLI; a future phase may add ``clawteam sprint artifact <id>
        <name>`` to stream individual bodies.
        """
        return {
            "sprint_id": state.sprint_id,
            "team": state.team,
            "goal": state.goal,
            "current_phase": state.current_phase,
            "status": state.status,
            "participants": list(state.participants),
            "phase_history": list(state.phase_history),
            "artifacts_list": sorted(state.artifacts.keys()),
            "pending_question_ids": list(state.pending_question_ids),
            "auto_advance": state.auto_advance,
            "created_at": state.created_at,
            "workspace_branch": state.workspace_branch,
        }

    # ─────────────────── internals ───────────────────

    def _load_by_id(self, sprint_id: str) -> SprintState:
        """Load a sprint by full id first; on miss, try prefix resolution.

        Callers pass a full uuid[:8] in the happy path; CLI also routes
        partial prefixes through this path, so we fall back to
        :meth:`resolve_sprint` when the exact path does not exist.
        """
        try:
            return load_sprint_state(self.team_name, sprint_id)
        except FileNotFoundError:
            return self.resolve_sprint(sprint_id)

    def _build_gate_chain(self, state: SprintState) -> list:
        """Compose EvidenceGate → forced_progress_gate → (InteractionGate?).

        InteractionGate insertion logic per §02-CONTEXT D-23 + force_interactive_phases:

        - force_interactive_phases includes the current phase → always insert.
        - auto_advance=False → always insert.
        - auto_advance=True + pending_question_ids non-empty → insert.
        - auto_advance=True + no pending questions → skip.

        Gates are imported lazily so the conductor module loads cleanly even
        when optional sub-modules (evidence_gate, forced_progress_gate,
        interaction_gate) fail to import during partial-deploy scenarios.
        """
        from clawteam.harness.evidence_gate import EvidenceGate
        from clawteam.harness.forced_progress_gate import forced_progress_gate
        from clawteam.harness.interaction_gate import InteractionGate

        chain: list = []
        # EvidenceGate — Phase 2 ships a permissive default: the 4-check
        # protocol only applies to registered artifacts. With an empty
        # artifact_names list, the gate's super().check short-circuits to
        # True. Phase 3 GstackSprintPlugin populates the real artifact list.
        chain.append(EvidenceGate(artifact_names=list(state.artifacts.keys())))
        chain.append(forced_progress_gate())

        has_pending = bool(state.pending_question_ids)
        forced = state.current_phase in self.force_interactive_phases
        if forced or (not state.auto_advance) or has_pending:
            # InteractionGate pairs against the sprint dir; let it resolve
            # from the SprintState via its own _resolve_sprint_dir path.
            chain.append(InteractionGate())
        return chain

    def _emit_phase_transition(
        self, from_phase: str, to_phase: str, state: SprintState
    ) -> None:
        """Emit a PhaseTransition event on self.bus; never crash the sprint on failure."""
        try:
            from clawteam.events.types import PhaseTransition

            self.bus.emit(
                PhaseTransition(
                    team_name=self.team_name,
                    from_phase=from_phase,
                    to_phase=to_phase,
                    artifacts=list(state.artifacts.keys()),
                )
            )
        except Exception:  # pragma: no cover — emit must never crash the loop
            pass


__all__ = [
    "AmbiguousSprintError",
    "MissingTeamError",
    "SprintConductor",
    "SprintNotFoundError",
]
