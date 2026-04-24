---
phase: 04
plan: 07
type: execute
wave: 2
depends_on: [01, 02]
files_modified:
  - clawteam/templates/gstack/skills/__init__.py
  - clawteam/templates/gstack/skills/office_hours/__init__.py
  - clawteam/templates/gstack/skills/office_hours/state.py
  - tests/fixtures/gstack_state_machines/office-hours.transitions.json
  - tests/test_office_hours_state_machine.py
autonomous: true
requirements: [QUALITY-07]
must_haves:
  truths:
    - "OfficeHoursState pydantic class exposes current_state, history, handle(event, turn), save(), load()."
    - "Transition table covers 6 forcing-question pairs (ask + answer) + summary_written + abandoned terminals."
    - "State persists at ~/.clawteam/teams/<team>/sprints/<sprint_id>/skills/office-hours/pm/state.json via file_locked + atomic_write_text."
    - "Turn budget = 13 (6 × (ask + answer) + write_summary)."
    - "State machine's in-code _TRANSITIONS dict matches the fixture JSON transitions list exactly."
    - "State survives full process restart via pydantic round-trip (CORE-07 compatibility)."
  artifacts:
    - path: "clawteam/templates/gstack/skills/office_hours/state.py"
      provides: "OfficeHoursState pydantic model + transition table"
      contains: "class OfficeHoursState(BaseModel)"
      min_lines: 100
    - path: "tests/fixtures/gstack_state_machines/office-hours.transitions.json"
      provides: "Canonical transition graph fixture for golden tests"
      contains: "\"turn_budget\": 13"
    - path: "tests/test_office_hours_state_machine.py"
      provides: "Transition-table + persistence + round-trip tests"
      contains: "def test_transitions_match_fixture"
  key_links:
    - from: "clawteam/templates/gstack/skills/office_hours/state.py"
      to: "clawteam/fileutil.py (file_locked + atomic_write_text)"
      via: "Persistence follows Phase 2 SprintState convention"
    - from: "clawteam/templates/gstack/skills/office_hours/state.py"
      to: "clawteam/paths.py (validate_identifier + ensure_within_root)"
      via: "Path-traversal guard identical to SprintState._state_path"
    - from: "tests/fixtures/gstack_state_machines/office-hours.transitions.json"
      to: "test_transitions_match_fixture"
      via: "Fixture JSON keys map to _TRANSITIONS dict via exact equality"
---

<objective>
Ship the `/office-hours` state machine as a pydantic transition-table class under `clawteam/templates/gstack/skills/office_hours/state.py` per D-01/D-02/D-03. Each turn of the `pm` agent during the Think phase loads the state, calls `handle(event, turn)`, persists, and writes the next question artifact. State survives full process restart via JSON persistence (CORE-07).

Purpose: One of the three Phase-4 interactive state machines. Fixture-driven: `tests/fixtures/gstack_state_machines/office-hours.transitions.json` is the canonical transition graph; golden tests assert the class's in-code `_TRANSITIONS` matches the fixture exactly. Turn budget 13 (6 forcing questions × (ask + answer) + write_summary) catches monologue-collapse regression per Pitfall 7 warning signs.

Output: 1 skill package (3 init files), 1 state module, 1 fixture JSON, 1 test file. Zero modifications to existing code.
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
From clawteam/sprint/state.py (lines 108-149 — SprintState save/load pattern to mirror):
```python
@staticmethod
def _state_path(team: str, sprint_id: str) -> Path:
    validate_identifier(team, "team name")
    validate_identifier(sprint_id, "sprint id")
    root = get_data_dir() / "teams"
    sprints_dir = ensure_within_root(root, team, "sprints", sprint_id)
    return sprints_dir / "state.json"

def save(self, team: str) -> Path:
    path = self._state_path(team, self.sprint_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_locked(path):
        atomic_write_text(path, self.model_dump_json(indent=2))
    return path
```

From tests/fixtures/gstack_skills/office-hours.md (the 6 forcing questions, verbatim — summarized):
1. Demand Reality
2. Status Quo
3. Desperate Specificity
4. Narrowest Wedge
5. Observation & Surprise
6. Future-Fit

Transition graph shape per 04-RESEARCH §Example 2:
- initial_state: "start"
- final_states: ["summary_written", "abandoned"]
- turn_budget: 13
- Transitions cover begin → q1_asked → answered → q1_answered → advance → q2_asked → ... → q6_answered → write_summary → summary_written
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create skills/office_hours package + transition fixture JSON</name>
  <files>clawteam/templates/gstack/skills/__init__.py, clawteam/templates/gstack/skills/office_hours/__init__.py, tests/fixtures/gstack_state_machines/office-hours.transitions.json</files>
  <read_first>
    - clawteam/templates/gstack/__init__.py (existing — verify empty or minimal)
    - clawteam/templates/gstack/schemas/__init__.py (Phase 3 pattern for schemas package)
    - tests/fixtures/gstack_skills/office-hours.md (confirms 6 forcing questions ordering)
  </read_first>
  <action>
Create `clawteam/templates/gstack/skills/__init__.py`:
```python
"""Gstack interactive skill state machines (§04-CONTEXT D-01).

Each subpackage hosts one Phase-4 interactive state machine:

- office_hours/ — pm's 6-forcing-question Socratic loop (Plan 04-07)
- design_consultation/ — designer's 7-dimension rubric dialogue (Plan 04-08)
- investigate/ — reviewer's per-hypothesis iron-law loop with auto-freeze (Plan 04-09)

State persists under ~/.clawteam/teams/<team>/sprints/<id>/skills/<skill>/<role>/state.json
via file_locked + atomic_write_text (Phase 2 convention).
"""
```

Create `clawteam/templates/gstack/skills/office_hours/__init__.py`:
```python
"""/office-hours multi-turn state machine (§04-CONTEXT D-01/D-02 — Plan 04-07)."""

from clawteam.templates.gstack.skills.office_hours.state import (
    OfficeHoursState,
    OHEvent,
    OHState,
    StateTransitionResult,
    Transition,
)

__all__ = [
    "OfficeHoursState",
    "OHEvent",
    "OHState",
    "StateTransitionResult",
    "Transition",
]
```

Create `tests/fixtures/gstack_state_machines/office-hours.transitions.json` (verbatim per 04-RESEARCH Example 2):
```json
{
  "skill": "office-hours",
  "role": "pm",
  "initial_state": "start",
  "final_states": ["summary_written", "abandoned"],
  "turn_budget": 13,
  "transitions": [
    {"from": "start",       "event": "begin",         "to": "q1_asked"},
    {"from": "q1_asked",    "event": "answered",      "to": "q1_answered"},
    {"from": "q1_answered", "event": "advance",       "to": "q2_asked"},
    {"from": "q2_asked",    "event": "answered",      "to": "q2_answered"},
    {"from": "q2_answered", "event": "advance",       "to": "q3_asked"},
    {"from": "q3_asked",    "event": "answered",      "to": "q3_answered"},
    {"from": "q3_answered", "event": "advance",       "to": "q4_asked"},
    {"from": "q4_asked",    "event": "answered",      "to": "q4_answered"},
    {"from": "q4_answered", "event": "advance",       "to": "q5_asked"},
    {"from": "q5_asked",    "event": "answered",      "to": "q5_answered"},
    {"from": "q5_answered", "event": "advance",       "to": "q6_asked"},
    {"from": "q6_asked",    "event": "answered",      "to": "q6_answered"},
    {"from": "q6_answered", "event": "write_summary", "to": "summary_written"}
  ],
  "abandon_event": "abandon",
  "forcing_questions": [
    {"id": "Q1", "name": "Demand Reality"},
    {"id": "Q2", "name": "Status Quo"},
    {"id": "Q3", "name": "Desperate Specificity"},
    {"id": "Q4", "name": "Narrowest Wedge"},
    {"id": "Q5", "name": "Observation & Surprise"},
    {"id": "Q6", "name": "Future-Fit"}
  ]
}
```
  </action>
  <verify>
    <automated>python3 -c "import json; d = json.load(open('tests/fixtures/gstack_state_machines/office-hours.transitions.json')); assert d['turn_budget'] == 13; assert len(d['transitions']) == 13; assert len(d['forcing_questions']) == 6; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - ls clawteam/templates/gstack/skills/__init__.py succeeds
    - ls clawteam/templates/gstack/skills/office_hours/__init__.py succeeds
    - ls tests/fixtures/gstack_state_machines/office-hours.transitions.json succeeds
    - `json.load` of the fixture succeeds + turn_budget==13 + transitions length==13 + forcing_questions length==6
    - `python3 -c "from clawteam.templates.gstack.skills import office_hours"` does not fail (will succeed once Task 2 lands state.py)
  </acceptance_criteria>
  <done>Package scaffolding + fixture JSON exist; parsable; consumed by Task 2 golden test</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement OfficeHoursState pydantic class + transitions + save/load</name>
  <files>clawteam/templates/gstack/skills/office_hours/state.py, tests/test_office_hours_state_machine.py</files>
  <read_first>
    - clawteam/sprint/state.py (SprintState save/load pattern)
    - clawteam/fileutil.py (file_locked + atomic_write_text signatures)
    - clawteam/paths.py (validate_identifier + ensure_within_root)
    - clawteam/team/models.py (get_data_dir)
    - tests/fixtures/gstack_state_machines/office-hours.transitions.json (created in Task 1)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-RESEARCH.md (§Pattern 1 + Example 2 — exact code sketch)
  </read_first>
  <behavior>
    - Test 1 (test_initial_state_is_start): Fresh OfficeHoursState has current_state == "start", empty history.
    - Test 2 (test_transitions_match_fixture): Iterate class's `_TRANSITIONS` dict + compare to fixture JSON's transitions list (bijective). Every fixture entry has a matching dict key; every dict key has a matching fixture entry.
    - Test 3 (test_begin_transitions_to_q1_asked): state.handle("begin", turn=1) → current_state == "q1_asked", history has 1 entry.
    - Test 4 (test_invalid_transition_returns_error): state.handle("advance", turn=1) from "start" → ok==False, reason mentions "invalid transition".
    - Test 5 (test_abandon_from_any_non_final): state at q3_asked → handle("abandon", turn=5) → current_state == "abandoned".
    - Test 6 (test_cannot_transition_from_final): state at "summary_written" → handle("answered", turn=100) → ok==False.
    - Test 7 (test_full_happy_path): begin → answered → advance × 6 loops → write_summary. Final state == "summary_written". History has 13 entries. Turn counter matches fixture turn_budget.
    - Test 8 (test_save_load_round_trip): state.save() → OfficeHoursState.load(team, sprint_id) → equal current_state + history.
    - Test 9 (test_state_path_rejects_bad_identifiers): _state_path raises on team="../evil" or sprint_id="".
    - Test 10 (test_persistence_survives_simulated_restart): Save state, delete all in-memory, reload via classmethod → all fields restored including history entries' turn numbers.
    - Test 11 (test_forcing_question_ids_match_fixture): 6 question IDs [Q1..Q6] match the fixture forcing_questions list.
  </behavior>
  <action>
Create `clawteam/templates/gstack/skills/office_hours/state.py`:

```python
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
        """Advance the state machine by one event."""
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
        mapping = {
            "q1_asked": "Q1", "q2_asked": "Q2", "q3_asked": "Q3",
            "q4_asked": "Q4", "q5_asked": "Q5", "q6_asked": "Q6",
        }
        self.pending_question_id = mapping.get(self.current_state)

    # ── Persistence ────────────────────────────────────────────────────

    @staticmethod
    def _state_path(team: str, sprint_id: str) -> Path:
        validate_identifier(team, "team name")
        validate_identifier(sprint_id, "sprint id")
        root = get_data_dir() / "teams"
        skill_dir = ensure_within_root(
            root, team, "sprints", sprint_id, "skills", "office-hours", "pm",
        )
        return skill_dir / "state.json"

    def save(self) -> Path:
        path = self._state_path(self.team, self.sprint_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_locked(path):
            atomic_write_text(path, self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, team: str, sprint_id: str) -> "OfficeHoursState":
        path = cls._state_path(team, sprint_id)
        with file_locked(path):
            raw = path.read_text(encoding="utf-8")
        return cls.model_validate_json(raw)
```

Create `tests/test_office_hours_state_machine.py`:

```python
"""Unit + fixture-driven tests for OfficeHoursState (Plan 04-07)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clawteam.templates.gstack.skills.office_hours import (
    OfficeHoursState,
    Transition,
)
from clawteam.templates.gstack.skills.office_hours.state import (
    FORCING_QUESTIONS,
    TURN_BUDGET,
    _FINAL_STATES,
    _TRANSITIONS,
)


_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gstack_state_machines" / "office-hours.transitions.json"


@pytest.fixture
def fixture_dict() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _new_state(team="t", sprint_id="s1") -> OfficeHoursState:
    return OfficeHoursState(team=team, sprint_id=sprint_id)


def test_initial_state_is_start():
    s = _new_state()
    assert s.current_state == "start"
    assert s.history == []
    assert s.pending_question_id is None
    assert s.completed_at is None


def test_transitions_match_fixture(fixture_dict):
    """Golden: in-code _TRANSITIONS matches fixture JSON transitions exactly."""
    # Build bijective sets of (from, event, to) triples.
    code_triples = {(k[0], k[1], v) for k, v in _TRANSITIONS.items()}
    fixture_triples = {(t["from"], t["event"], t["to"]) for t in fixture_dict["transitions"]}
    assert code_triples == fixture_triples, (
        f"code-vs-fixture mismatch\n"
        f"only in code: {code_triples - fixture_triples}\n"
        f"only in fixture: {fixture_triples - code_triples}"
    )


def test_turn_budget_matches_fixture(fixture_dict):
    assert TURN_BUDGET == fixture_dict["turn_budget"]
    assert TURN_BUDGET == 13


def test_final_states_match_fixture(fixture_dict):
    assert set(_FINAL_STATES) == set(fixture_dict["final_states"])


def test_forcing_question_ids_match_fixture(fixture_dict):
    assert FORCING_QUESTIONS == fixture_dict["forcing_questions"]


def test_begin_transitions_to_q1_asked():
    s = _new_state()
    res = s.handle("begin", turn=1)
    assert res.ok is True
    assert res.new_state == "q1_asked"
    assert s.current_state == "q1_asked"
    assert s.pending_question_id == "Q1"
    assert len(s.history) == 1


def test_invalid_transition_returns_error():
    s = _new_state()
    res = s.handle("advance", turn=1)  # start cannot advance
    assert res.ok is False
    assert "invalid transition" in res.reason
    assert s.current_state == "start"


def test_abandon_from_any_non_final():
    s = _new_state()
    s.handle("begin", turn=1)
    s.handle("answered", turn=2)
    s.handle("advance", turn=3)  # now q2_asked
    res = s.handle("abandon", turn=4)
    assert res.ok is True
    assert s.current_state == "abandoned"


def test_cannot_transition_from_final():
    s = _new_state()
    s.current_state = "summary_written"
    s.completed_at = "2026-04-21T12:00:00+00:00"
    res = s.handle("answered", turn=100)
    assert res.ok is False
    assert "final" in res.reason


def test_full_happy_path():
    s = _new_state()
    turn = 0
    # begin
    turn += 1; assert s.handle("begin", turn=turn).ok
    # 6 cycles of answered + (advance if not last)
    for q in range(1, 7):
        turn += 1; assert s.handle("answered", turn=turn).ok
        if q < 6:
            turn += 1; assert s.handle("advance", turn=turn).ok
    # write_summary
    turn += 1; assert s.handle("write_summary", turn=turn).ok

    assert s.current_state == "summary_written"
    assert len(s.history) == TURN_BUDGET  # exactly 13 transitions
    assert s.completed_at is not None


def test_save_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    s = _new_state()
    s.handle("begin", turn=1)
    s.handle("answered", turn=2)
    path = s.save()
    assert path.exists()

    loaded = OfficeHoursState.load("t", "s1")
    assert loaded.current_state == "q1_answered"
    assert len(loaded.history) == 2
    assert loaded.pending_question_id is None  # q1_answered has no pending Q


def test_state_path_rejects_bad_identifiers():
    with pytest.raises(Exception):  # noqa: B017 — validate_identifier raises
        OfficeHoursState._state_path("../evil", "s1")
    with pytest.raises(Exception):
        OfficeHoursState._state_path("t", "")


def test_persistence_survives_simulated_restart(tmp_path, monkeypatch):
    """CORE-07: save, reload in a fresh process simulates orchestrator restart."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    original = _new_state()
    original.handle("begin", turn=1)
    original.handle("answered", turn=2)
    original.handle("advance", turn=3)
    original.save()

    # Simulate restart: drop reference, load fresh.
    del original
    loaded = OfficeHoursState.load("t", "s1")
    assert loaded.current_state == "q2_asked"
    assert loaded.pending_question_id == "Q2"
    assert len(loaded.history) == 3
    # Turn numbers preserved.
    assert [h.turn for h in loaded.history] == [1, 2, 3]


def test_pending_question_id_tracking():
    s = _new_state()
    s.handle("begin", turn=1)
    assert s.pending_question_id == "Q1"
    s.handle("answered", turn=2)
    assert s.pending_question_id is None
    s.handle("advance", turn=3)
    assert s.pending_question_id == "Q2"
```
  </action>
  <verify>
    <automated>pytest tests/test_office_hours_state_machine.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class OfficeHoursState(BaseModel)" clawteam/templates/gstack/skills/office_hours/state.py
    - grep -q "_TRANSITIONS:" clawteam/templates/gstack/skills/office_hours/state.py
    - grep -q "TURN_BUDGET = 13" clawteam/templates/gstack/skills/office_hours/state.py
    - wc -l clawteam/templates/gstack/skills/office_hours/state.py returns >= 100
    - pytest tests/test_office_hours_state_machine.py -x -q exits 0 (13 tests pass)
    - `python3 -c "from clawteam.templates.gstack.skills.office_hours import OfficeHoursState, OHState, OHEvent"` exits 0
  </acceptance_criteria>
  <done>OfficeHoursState class + full test coverage; in-code transitions bijective with fixture JSON; CORE-07 persistence verified</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Persisted state.json ↔ pydantic model_validate_json | Malformed JSON could trigger parse error at restart |
| Team/sprint_id identifiers ↔ path construction | Directory traversal via bad identifier |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-21 | T (Tampering) | state.json corruption | mitigate | file_locked + atomic_write_text prevent torn writes; pydantic model_validate_json rejects malformed; Phase 2 proved the pattern |
| T-04-22 | E (Elevation of privilege) | Path traversal via team name | mitigate | validate_identifier + ensure_within_root (reuse from sprint/state.py) |
| T-04-23 | D (DoS) | Unbounded history growth | accept | Turn budget 13 caps normal flow; abandoned terminals prevent unbounded loops |
</threat_model>

<verification>
Plan 07 integration checks:
- [ ] `pytest tests/test_office_hours_state_machine.py -x -q` exits 0 with 13/13
- [ ] Golden: in-code `_TRANSITIONS` bijectively matches fixture JSON (test_transitions_match_fixture)
- [ ] `grep -c "class OfficeHoursState" clawteam/templates/gstack/skills/office_hours/state.py` == 1
- [ ] Fixture JSON is valid: `python3 -c "import json; d = json.load(open('tests/fixtures/gstack_state_machines/office-hours.transitions.json')); assert d['turn_budget'] == 13; assert len(d['transitions']) == 13"`
- [ ] No existing Phase 2/3 tests regress
</verification>

<success_criteria>
Plan 07 ships when:
- [ ] OfficeHoursState is importable from `clawteam.templates.gstack.skills.office_hours`
- [ ] 13 transitions (6 × ask+answer + write_summary) form the bijective graph
- [ ] Turn budget 13 matches fixture
- [ ] Persistence uses file_locked + atomic_write_text per Phase 2 convention
- [ ] State survives simulated restart (CORE-07)
- [ ] Golden fixture test passes so changes require updating BOTH code and fixture
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-07-office-hours-state-machine-SUMMARY.md` with:
- LOC count of state.py
- 13/13 test result
- Confirmation: fixture + code transitions are bijective
</output>
