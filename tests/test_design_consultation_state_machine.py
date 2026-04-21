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
    turn += 1
    assert s.handle("begin", turn=turn).ok
    for p in range(1, 8):
        turn += 1
        assert s.handle("scored", turn=turn).ok
        if p < 7:
            turn += 1
            assert s.handle("advance", turn=turn).ok
    turn += 1
    assert s.handle("write_summary", turn=turn).ok
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
    res = s.handle("scored", turn=100)
    assert not res.ok
    assert "final" in res.reason
