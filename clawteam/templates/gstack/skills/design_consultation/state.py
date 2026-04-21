"""DesignConsultationState — /design-consultation per-dimension state machine (§04-CONTEXT D-01).

Per-dimension rubric-scoring loop driven by designer in Think/Plan phases. 7
dimensions per the upstream `/plan-design-review` v2.0.0 rubric; one dimension
scored per turn (Pitfall 7 prevention — no "score all 7 in one turn" monologue).

Persistence: JSON under
  ~/.clawteam/teams/<team>/sprints/<sprint_id>/skills/design-consultation/designer/state.json
via file_locked + atomic_write_text.

Turn budget: 15 (7 × (score + advance) - 1 trailing advance + write_summary = 14 + 1).
Matches fixture JSON at tests/fixtures/gstack_state_machines/design-consultation.transitions.json.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir


DCState = Literal[
    "start",
    "pass1_scoring", "pass1_scored",
    "pass2_scoring", "pass2_scored",
    "pass3_scoring", "pass3_scored",
    "pass4_scoring", "pass4_scored",
    "pass5_scoring", "pass5_scored",
    "pass6_scoring", "pass6_scored",
    "pass7_scoring", "pass7_scored",
    "summary_written",
    "abandoned",
]

DCEvent = Literal["begin", "scored", "advance", "write_summary", "abandon"]


RUBRIC_DIMENSIONS: list[dict] = [
    {"id": 1, "name": "Information Architecture"},
    {"id": 2, "name": "Interaction State Coverage"},
    {"id": 3, "name": "User Journey & Emotional Arc"},
    {"id": 4, "name": "AI Slop Risk"},
    {"id": 5, "name": "Design System Alignment"},
    {"id": 6, "name": "Responsive & Accessibility"},
    {"id": 7, "name": "Unresolved Design Decisions"},
]


_TRANSITIONS: dict[tuple[DCState, DCEvent], DCState] = {
    ("start",         "begin"):         "pass1_scoring",
    ("pass1_scoring", "scored"):        "pass1_scored",
    ("pass1_scored",  "advance"):       "pass2_scoring",
    ("pass2_scoring", "scored"):        "pass2_scored",
    ("pass2_scored",  "advance"):       "pass3_scoring",
    ("pass3_scoring", "scored"):        "pass3_scored",
    ("pass3_scored",  "advance"):       "pass4_scoring",
    ("pass4_scoring", "scored"):        "pass4_scored",
    ("pass4_scored",  "advance"):       "pass5_scoring",
    ("pass5_scoring", "scored"):        "pass5_scored",
    ("pass5_scored",  "advance"):       "pass6_scoring",
    ("pass6_scoring", "scored"):        "pass6_scored",
    ("pass6_scored",  "advance"):       "pass7_scoring",
    ("pass7_scoring", "scored"):        "pass7_scored",
    ("pass7_scored",  "write_summary"): "summary_written",
}

_FINAL_STATES: tuple[DCState, ...] = ("summary_written", "abandoned")
TURN_BUDGET = 15


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DCTransition(BaseModel):
    from_state: DCState
    to_state: DCState
    event: DCEvent
    ts: str
    turn: int


class DCStateTransitionResult(BaseModel):
    ok: bool
    reason: str = ""
    new_state: DCState | None = None


class DesignConsultationState(BaseModel):
    """Pydantic state machine for /design-consultation (designer persona)."""

    skill: Literal["design-consultation"] = "design-consultation"
    role: Literal["designer"] = "designer"
    team: str
    sprint_id: str
    current_state: DCState = "start"
    history: list[DCTransition] = Field(default_factory=list)
    pending_dimension_id: int | None = None
    completed_at: str | None = None

    def handle(self, event: DCEvent, turn: int) -> DCStateTransitionResult:
        if self.current_state in _FINAL_STATES:
            return DCStateTransitionResult(
                ok=False,
                reason=f"state machine already final: {self.current_state}",
            )

        if event == "abandon":
            next_state: DCState = "abandoned"
        else:
            key = (self.current_state, event)
            if key not in _TRANSITIONS:
                return DCStateTransitionResult(
                    ok=False,
                    reason=f"invalid transition {self.current_state} --{event}-->",
                )
            next_state = _TRANSITIONS[key]

        self.history.append(
            DCTransition(
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
        self._sync_pending_dimension()
        return DCStateTransitionResult(ok=True, new_state=next_state)

    def _sync_pending_dimension(self) -> None:
        mapping = {
            "pass1_scoring": 1, "pass2_scoring": 2, "pass3_scoring": 3,
            "pass4_scoring": 4, "pass5_scoring": 5, "pass6_scoring": 6,
            "pass7_scoring": 7,
        }
        self.pending_dimension_id = mapping.get(self.current_state)

    # -- Persistence ---------------------------------------------------

    @staticmethod
    def _state_path(team: str, sprint_id: str) -> Path:
        validate_identifier(team, "team name")
        validate_identifier(sprint_id, "sprint id")
        root = get_data_dir() / "teams"
        skill_dir = ensure_within_root(
            root, team, "sprints", sprint_id, "skills", "design-consultation", "designer",
        )
        return skill_dir / "state.json"

    def save(self) -> Path:
        path = self._state_path(self.team, self.sprint_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_locked(path):
            atomic_write_text(path, self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, team: str, sprint_id: str) -> "DesignConsultationState":
        path = cls._state_path(team, sprint_id)
        with file_locked(path):
            raw = path.read_text(encoding="utf-8")
        return cls.model_validate_json(raw)
