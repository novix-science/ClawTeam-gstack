"""OfficeHoursState — /office-hours multi-turn state machine (§04-CONTEXT D-01/D-02).

Per-question forcing-loop driven by pm in the Think phase. Transition table
mirrors the upstream gstack `/office-hours` v2.0.0 shape (6 forcing questions,
one per turn, no batched monologues — Pitfall 7 prevention).

Persistence: JSON under
  ~/.clawteam/teams/<team>/sprints/<sprint_id>/skills/office-hours/pm/state.json
via file_locked + atomic_write_text (§02-CONTEXT convention).

Per-turn contract (§04-CONTEXT D-03):
  1. SprintConductor loads the state at pm's turn boundary (Plan 04-10 dispatch).
  2. Plugin handler calls state.handle(event, turn=conductor_turn_counter).
  3. Plugin handler calls state.save() — persisted for next turn / full restart.
  4. No dedicated skill event loop.

The in-code _TRANSITIONS dict is the single source of truth; a golden test
asserts it matches tests/fixtures/gstack_state_machines/office-hours.transitions.json
exactly. Editing the transitions requires updating BOTH.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir


OHState = Literal[
    "start",
    "q1_asked", "q1_answered",    # Demand Reality
    "q2_asked", "q2_answered",    # Status Quo
    "q3_asked", "q3_answered",    # Desperate Specificity
    "q4_asked", "q4_answered",    # Narrowest Wedge
    "q5_asked", "q5_answered",    # Observation & Surprise
    "q6_asked", "q6_answered",    # Future-Fit
    "summary_written",
    "abandoned",
]

OHEvent = Literal[
    "begin", "answered", "advance", "write_summary", "abandon",
]

FORCING_QUESTIONS: list[dict[str, str]] = [
    {"id": "Q1", "name": "Demand Reality"},
    {"id": "Q2", "name": "Status Quo"},
    {"id": "Q3", "name": "Desperate Specificity"},
    {"id": "Q4", "name": "Narrowest Wedge"},
    {"id": "Q5", "name": "Observation & Surprise"},
    {"id": "Q6", "name": "Future-Fit"},
]

# Single source of truth for the transition table. Test
# tests/test_office_hours_state_machine.py::test_transitions_match_fixture
# asserts this dict round-trips through the fixture JSON bijectively.
_TRANSITIONS: dict[tuple[OHState, OHEvent], OHState] = {
    ("start",       "begin"):         "q1_asked",
    ("q1_asked",    "answered"):      "q1_answered",
    ("q1_answered", "advance"):       "q2_asked",
    ("q2_asked",    "answered"):      "q2_answered",
    ("q2_answered", "advance"):       "q3_asked",
    ("q3_asked",    "answered"):      "q3_answered",
    ("q3_answered", "advance"):       "q4_asked",
    ("q4_asked",    "answered"):      "q4_answered",
    ("q4_answered", "advance"):       "q5_asked",
    ("q5_asked",    "answered"):      "q5_answered",
    ("q5_answered", "advance"):       "q6_asked",
    ("q6_asked",    "answered"):      "q6_answered",
    ("q6_answered", "write_summary"): "summary_written",
}

_FINAL_STATES: tuple[OHState, ...] = ("summary_written", "abandoned")
TURN_BUDGET: int = 13  # 6 × (ask + answer) + write_summary. Matches fixture.


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Transition(BaseModel):
    """One state-machine transition for history log."""

    from_state: OHState
    to_state: OHState
    event: OHEvent
    ts: str
    turn: int


class StateTransitionResult(BaseModel):
    """Outcome of OfficeHoursState.handle()."""

    ok: bool
    reason: str = ""
    new_state: OHState | None = None


class OfficeHoursState(BaseModel):
    """Pydantic state machine for /office-hours (pm persona, Think phase).

    Public API:
      - Constructor: OfficeHoursState(team=..., sprint_id=...)
      - handle(event, turn) -> StateTransitionResult
      - save() -> Path
      - OfficeHoursState.load(team, sprint_id) -> OfficeHoursState
    """

    skill: Literal["office-hours"] = "office-hours"
    role: Literal["pm"] = "pm"
    team: str
    sprint_id: str
    current_state: OHState = "start"
    history: list[Transition] = Field(default_factory=list)
    pending_question_id: str | None = None
    completed_at: str | None = None

    # ── Public behavior ────────────────────────────────────────────────

    def handle(self, event: OHEvent, turn: int) -> StateTransitionResult:
        """Advance the state machine by one event.

        Returns a StateTransitionResult with ``ok=False`` (plus a ``reason``) when
        the current state is already final or the (state, event) pair is not in
        the transition table. On success, appends a Transition to ``history``,
        updates ``current_state`` + ``pending_question_id``, and — if the new
        state is terminal — stamps ``completed_at``.
        """
        if self.current_state in _FINAL_STATES:
            return StateTransitionResult(
                ok=False,
                reason=f"state machine already final: {self.current_state}",
            )

        if event == "abandon":
            next_state: OHState = "abandoned"
        else:
            key = (self.current_state, event)
            if key not in _TRANSITIONS:
                return StateTransitionResult(
                    ok=False,
                    reason=f"invalid transition {self.current_state} --{event}-->",
                )
            next_state = _TRANSITIONS[key]

        self.history.append(
            Transition(
                from_state=self.current_state,
                to_state=next_state,
                event=event,
                ts=_now_iso(),
                turn=turn,
            )
        )
        self.current_state = next_state
        if next_state in _FINAL_STATES:
            self.completed_at = _now_iso()
        # Maintain pending_question_id pointer so callers know which Q is live.
        self._sync_pending_question_id()
        return StateTransitionResult(ok=True, new_state=next_state)

    def _sync_pending_question_id(self) -> None:
        """Mirror the current _asked state into ``pending_question_id`` (``None`` otherwise)."""
        mapping = {
            "q1_asked": "Q1", "q2_asked": "Q2", "q3_asked": "Q3",
            "q4_asked": "Q4", "q5_asked": "Q5", "q6_asked": "Q6",
        }
        self.pending_question_id = mapping.get(self.current_state)

    # ── Persistence ────────────────────────────────────────────────────

    @staticmethod
    def _state_path(team: str, sprint_id: str) -> Path:
        """Resolve the canonical state.json path for (team, sprint_id).

        Path layout (§04-CONTEXT D-02):
          <data_dir>/teams/<team>/sprints/<sprint_id>/skills/office-hours/pm/state.json

        Both identifiers are validated via :func:`validate_identifier`; the
        joined path is clamped under the teams root by
        :func:`ensure_within_root`. Any escape attempt raises ``ValueError``
        before any filesystem operation runs (T-04-22 mitigation, mirroring
        ``SprintState._state_path``).
        """
        validate_identifier(team, "team name")
        validate_identifier(sprint_id, "sprint id")
        root = get_data_dir() / "teams"
        skill_dir = ensure_within_root(
            root, team, "sprints", sprint_id, "skills", "office-hours", "pm",
        )
        return skill_dir / "state.json"

    def save(self) -> Path:
        """Write this state atomically under the canonical path (file_locked)."""
        path = self._state_path(self.team, self.sprint_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_locked(path):
            atomic_write_text(path, self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, team: str, sprint_id: str) -> "OfficeHoursState":
        """Read + validate the canonical state.json for (team, sprint_id)."""
        path = cls._state_path(team, sprint_id)
        with file_locked(path):
            raw = path.read_text(encoding="utf-8")
        return cls.model_validate_json(raw)
