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
    turn += 1
    assert s.handle("begin", turn=turn).ok
    # 6 cycles of answered + (advance if not last)
    for q in range(1, 7):
        turn += 1
        assert s.handle("answered", turn=turn).ok
        if q < 6:
            turn += 1
            assert s.handle("advance", turn=turn).ok
    # write_summary
    turn += 1
    assert s.handle("write_summary", turn=turn).ok

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
