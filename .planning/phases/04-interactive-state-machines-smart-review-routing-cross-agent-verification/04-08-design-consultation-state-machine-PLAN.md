---
phase: 04
plan: 08
type: execute
wave: 2
depends_on: [01, 02]
files_modified:
  - clawteam/templates/gstack/skills/design_consultation/__init__.py
  - clawteam/templates/gstack/skills/design_consultation/state.py
  - tests/fixtures/gstack_state_machines/design-consultation.transitions.json
  - tests/test_design_consultation_state_machine.py
autonomous: true
requirements: [QUALITY-07]
must_haves:
  truths:
    - "DesignConsultationState pydantic class exposes current_state, history, handle(event, turn), save(), load()."
    - "Transition table covers 7 rubric dimensions × (scoring + scored) pairs + write_summary."
    - "State persists at ~/.clawteam/teams/<team>/sprints/<sprint_id>/skills/design-consultation/designer/state.json."
    - "Turn budget = 15 (7 × (score + advance) + write_summary = 14+1; fixture authoritative)."
    - "In-code _TRANSITIONS matches fixture JSON bijectively."
    - "State survives full process restart via pydantic round-trip (CORE-07)."
  artifacts:
    - path: "clawteam/templates/gstack/skills/design_consultation/state.py"
      provides: "DesignConsultationState pydantic model + transition table"
      contains: "class DesignConsultationState(BaseModel)"
      min_lines: 100
    - path: "tests/fixtures/gstack_state_machines/design-consultation.transitions.json"
      provides: "Canonical 7-dimension transition graph fixture"
      contains: "\"dimensions\":"
    - path: "tests/test_design_consultation_state_machine.py"
      provides: "Transition-table + persistence + happy-path tests"
      contains: "def test_transitions_match_fixture"
  key_links:
    - from: "clawteam/templates/gstack/skills/design_consultation/state.py"
      to: "clawteam/fileutil.py"
      via: "file_locked + atomic_write_text persistence"
    - from: "fixture JSON"
      to: "_TRANSITIONS dict in state.py"
      via: "Bijective equality enforced by test_transitions_match_fixture"
---

<objective>
Ship the `/design-consultation` state machine as a pydantic transition-table class under `clawteam/templates/gstack/skills/design_consultation/state.py`. Each turn of the `designer` agent during Think/Plan phase loads state, calls `handle(event, turn)`, persists, and emits the next rubric score artifact. 7 rubric dimensions, one per turn. State survives full process restart.

Purpose: One of the three Phase-4 interactive state machines. Designer runs the `/plan-design-review` 7-dimension rubric as a per-dimension dialogue. The state machine prevents "monologue collapse" (one turn scores all 7 dimensions) per Pitfall 7.

Output: 1 state module, 1 fixture JSON, 1 test file. Depends only on Plan 01 (PLAN_PREP_NOTES) and Plan 07 scaffolding's `skills/__init__.py` being in place — but Plan 07/08/09 are parallel-safe because each owns its own subdir; skills/__init__.py is idempotent (any plan creates it).
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
From clawteam/sprint/state.py (lines 108-149 — persistence pattern):
```python
# Same save/load pattern OfficeHoursState uses.
```

From tests/fixtures/gstack_skills/plan-design-review.md (authoritative for the 7 dimensions, verbatim):
1. Information Architecture
2. Interaction State Coverage
3. User Journey & Emotional Arc
4. AI Slop Risk
5. Design System Alignment
6. Responsive & Accessibility
7. Unresolved Design Decisions

From 04-RESEARCH §Example 2 (design-consultation fixture):
- 15 transitions: start → pass1_scoring → scored → advance → pass2_scoring → ...
  → pass7_scoring → scored → write_summary → summary_written
- turn_budget: 15
- initial_state: "start"
- final_states: ["summary_written", "abandoned"]
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create skills/design_consultation package + fixture JSON</name>
  <files>clawteam/templates/gstack/skills/design_consultation/__init__.py, tests/fixtures/gstack_state_machines/design-consultation.transitions.json</files>
  <read_first>
    - tests/fixtures/gstack_skills/plan-design-review.md (confirms 7-dimension ordering)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-RESEARCH.md (§Example 2 — design-consultation fixture verbatim)
  </read_first>
  <action>
If `clawteam/templates/gstack/skills/__init__.py` does not already exist from Plan 07, create it per that plan's Task 1 spec. If it exists, leave unchanged.

Create `clawteam/templates/gstack/skills/design_consultation/__init__.py`:
```python
"""/design-consultation multi-turn state machine (§04-CONTEXT D-01 — Plan 04-08)."""

from clawteam.templates.gstack.skills.design_consultation.state import (
    DesignConsultationState,
    DCEvent,
    DCState,
    DCTransition,
    DCStateTransitionResult,
)

__all__ = [
    "DesignConsultationState",
    "DCEvent",
    "DCState",
    "DCTransition",
    "DCStateTransitionResult",
]
```

Create `tests/fixtures/gstack_state_machines/design-consultation.transitions.json`:
```json
{
  "skill": "design-consultation",
  "role": "designer",
  "initial_state": "start",
  "final_states": ["summary_written", "abandoned"],
  "turn_budget": 15,
  "dimensions": [
    {"id": 1, "name": "Information Architecture"},
    {"id": 2, "name": "Interaction State Coverage"},
    {"id": 3, "name": "User Journey & Emotional Arc"},
    {"id": 4, "name": "AI Slop Risk"},
    {"id": 5, "name": "Design System Alignment"},
    {"id": 6, "name": "Responsive & Accessibility"},
    {"id": 7, "name": "Unresolved Design Decisions"}
  ],
  "transitions": [
    {"from": "start",         "event": "begin",         "to": "pass1_scoring"},
    {"from": "pass1_scoring", "event": "scored",        "to": "pass1_scored"},
    {"from": "pass1_scored",  "event": "advance",       "to": "pass2_scoring"},
    {"from": "pass2_scoring", "event": "scored",        "to": "pass2_scored"},
    {"from": "pass2_scored",  "event": "advance",       "to": "pass3_scoring"},
    {"from": "pass3_scoring", "event": "scored",        "to": "pass3_scored"},
    {"from": "pass3_scored",  "event": "advance",       "to": "pass4_scoring"},
    {"from": "pass4_scoring", "event": "scored",        "to": "pass4_scored"},
    {"from": "pass4_scored",  "event": "advance",       "to": "pass5_scoring"},
    {"from": "pass5_scoring", "event": "scored",        "to": "pass5_scored"},
    {"from": "pass5_scored",  "event": "advance",       "to": "pass6_scoring"},
    {"from": "pass6_scoring", "event": "scored",        "to": "pass6_scored"},
    {"from": "pass6_scored",  "event": "advance",       "to": "pass7_scoring"},
    {"from": "pass7_scoring", "event": "scored",        "to": "pass7_scored"},
    {"from": "pass7_scored",  "event": "write_summary", "to": "summary_written"}
  ],
  "abandon_event": "abandon"
}
```
  </action>
  <verify>
    <automated>python3 -c "import json; d = json.load(open('tests/fixtures/gstack_state_machines/design-consultation.transitions.json')); assert d['turn_budget'] == 15; assert len(d['transitions']) == 15; assert len(d['dimensions']) == 7; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - ls clawteam/templates/gstack/skills/design_consultation/__init__.py succeeds
    - ls tests/fixtures/gstack_state_machines/design-consultation.transitions.json succeeds
    - JSON parses with turn_budget==15, transitions length==15, dimensions length==7
  </acceptance_criteria>
  <done>Package scaffolding + fixture ready for Task 2</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement DesignConsultationState pydantic + transitions + save/load</name>
  <files>clawteam/templates/gstack/skills/design_consultation/state.py, tests/test_design_consultation_state_machine.py</files>
  <read_first>
    - clawteam/templates/gstack/skills/office_hours/state.py (Plan 07 reference shape — mirror structure)
    - tests/test_office_hours_state_machine.py (Plan 07 test pattern — mirror coverage)
    - tests/fixtures/gstack_state_machines/design-consultation.transitions.json (Task 1)
  </read_first>
  <behavior>
    - Test 1 (test_initial_state_is_start): Fresh state → current_state == "start", empty history.
    - Test 2 (test_transitions_match_fixture): In-code _TRANSITIONS bijectively equals fixture JSON transitions list.
    - Test 3 (test_turn_budget_matches_fixture): TURN_BUDGET == 15.
    - Test 4 (test_dimensions_match_fixture): In-code RUBRIC_DIMENSIONS list matches fixture JSON's dimensions list.
    - Test 5 (test_begin_transitions_to_pass1_scoring): handle("begin") → pass1_scoring.
    - Test 6 (test_invalid_transition_returns_error): handle("advance") from start → ok==False.
    - Test 7 (test_abandon_from_any_non_final): handle("abandon") at pass3_scoring → current_state == "abandoned".
    - Test 8 (test_full_happy_path): 7 scoring cycles + write_summary → final state == "summary_written", history length 15.
    - Test 9 (test_save_load_round_trip): save to tmp dir → load → equal state.
    - Test 10 (test_persistence_survives_simulated_restart): Save, drop reference, reload → full state restored with turn numbers.
    - Test 11 (test_pending_dimension_tracking): pending_dimension_id updates per phase (e.g., at pass3_scoring → dimension_id=3).
    - Test 12 (test_state_path_rejects_bad_identifiers): Path validation rejects traversal.
  </behavior>
  <action>
Create `clawteam/templates/gstack/skills/design_consultation/state.py`:

```python
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
TURN_BUDGET: int = 15


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

    # ── Persistence ────────────────────────────────────────────────────

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
```

Create `tests/test_design_consultation_state_machine.py`:

```python
"""Unit + fixture-driven tests for DesignConsultationState (Plan 04-08)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clawteam.templates.gstack.skills.design_consultation import (
    DesignConsultationState,
)
from clawteam.templates.gstack.skills.design_consultation.state import (
    RUBRIC_DIMENSIONS,
    TURN_BUDGET,
    _FINAL_STATES,
    _TRANSITIONS,
)


_FIXTURE_PATH = (
    Path(__file__).parent
    / "fixtures" / "gstack_state_machines" / "design-consultation.transitions.json"
)


@pytest.fixture
def fixture_dict() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _new_state(team="t", sprint_id="s1") -> DesignConsultationState:
    return DesignConsultationState(team=team, sprint_id=sprint_id)


def test_initial_state_is_start():
    s = _new_state()
    assert s.current_state == "start"
    assert s.history == []
    assert s.pending_dimension_id is None


def test_transitions_match_fixture(fixture_dict):
    code_triples = {(k[0], k[1], v) for k, v in _TRANSITIONS.items()}
    fixture_triples = {(t["from"], t["event"], t["to"]) for t in fixture_dict["transitions"]}
    assert code_triples == fixture_triples


def test_turn_budget_matches_fixture(fixture_dict):
    assert TURN_BUDGET == fixture_dict["turn_budget"]
    assert TURN_BUDGET == 15


def test_final_states_match_fixture(fixture_dict):
    assert set(_FINAL_STATES) == set(fixture_dict["final_states"])


def test_dimensions_match_fixture(fixture_dict):
    assert RUBRIC_DIMENSIONS == fixture_dict["dimensions"]


def test_begin_transitions_to_pass1_scoring():
    s = _new_state()
    res = s.handle("begin", turn=1)
    assert res.ok
    assert s.current_state == "pass1_scoring"
    assert s.pending_dimension_id == 1


def test_invalid_transition_returns_error():
    s = _new_state()
    res = s.handle("advance", turn=1)
    assert not res.ok
    assert "invalid" in res.reason


def test_abandon_from_any_non_final():
    s = _new_state()
    s.handle("begin", turn=1)
    s.handle("scored", turn=2)
    s.handle("advance", turn=3)
    res = s.handle("abandon", turn=4)
    assert res.ok
    assert s.current_state == "abandoned"


def test_full_happy_path():
    s = _new_state()
    turn = 0
    turn += 1; assert s.handle("begin", turn=turn).ok
    for p in range(1, 8):
        turn += 1; assert s.handle("scored", turn=turn).ok
        if p < 7:
            turn += 1; assert s.handle("advance", turn=turn).ok
    turn += 1; assert s.handle("write_summary", turn=turn).ok
    assert s.current_state == "summary_written"
    assert len(s.history) == TURN_BUDGET


def test_save_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    s = _new_state()
    s.handle("begin", turn=1)
    s.handle("scored", turn=2)
    s.save()
    loaded = DesignConsultationState.load("t", "s1")
    assert loaded.current_state == "pass1_scored"
    assert len(loaded.history) == 2


def test_persistence_survives_simulated_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    original = _new_state()
    original.handle("begin", turn=1)
    original.handle("scored", turn=2)
    original.handle("advance", turn=3)
    original.save()
    del original
    loaded = DesignConsultationState.load("t", "s1")
    assert loaded.current_state == "pass2_scoring"
    assert loaded.pending_dimension_id == 2
    assert [h.turn for h in loaded.history] == [1, 2, 3]


def test_pending_dimension_tracking():
    s = _new_state()
    s.handle("begin", turn=1)
    assert s.pending_dimension_id == 1
    s.handle("scored", turn=2)
    assert s.pending_dimension_id is None
    s.handle("advance", turn=3)
    assert s.pending_dimension_id == 2


def test_state_path_rejects_bad_identifiers():
    with pytest.raises(Exception):  # noqa: B017
        DesignConsultationState._state_path("../evil", "s1")
    with pytest.raises(Exception):
        DesignConsultationState._state_path("t", "")


def test_cannot_transition_from_final():
    s = _new_state()
    s.current_state = "summary_written"
    s.completed_at = _new_state().current_state  # whatever
    res = s.handle("scored", turn=100)
    assert not res.ok
    assert "final" in res.reason
```
  </action>
  <verify>
    <automated>pytest tests/test_design_consultation_state_machine.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class DesignConsultationState(BaseModel)" clawteam/templates/gstack/skills/design_consultation/state.py
    - grep -q "TURN_BUDGET = 15" clawteam/templates/gstack/skills/design_consultation/state.py
    - wc -l clawteam/templates/gstack/skills/design_consultation/state.py returns >= 100
    - pytest tests/test_design_consultation_state_machine.py -x -q exits 0 (14 tests pass)
  </acceptance_criteria>
  <done>DesignConsultationState ships; bijective with fixture; persistence verified</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

Same as Plan 07 (state.json persistence, path traversal, pydantic deserialization).

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-24 | T (Tampering) | state.json corruption | mitigate | file_locked + atomic_write_text |
| T-04-25 | E (Elevation of privilege) | Path traversal | mitigate | validate_identifier + ensure_within_root |
| T-04-26 | D (DoS) | Unbounded history | accept | Turn budget 15 caps normal flow |
</threat_model>

<verification>
- [ ] `pytest tests/test_design_consultation_state_machine.py -x -q` exits 0 (14/14)
- [ ] Golden: in-code `_TRANSITIONS` bijective with fixture JSON
- [ ] `python3 -c "from clawteam.templates.gstack.skills.design_consultation import DesignConsultationState"` exits 0
</verification>

<success_criteria>
- [ ] DesignConsultationState importable
- [ ] 15 transitions form bijective graph with fixture
- [ ] 7 rubric dimensions match fixture verbatim
- [ ] Persistence survives restart (CORE-07)
- [ ] 14 tests pass
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-08-design-consultation-state-machine-SUMMARY.md`.
</output>
