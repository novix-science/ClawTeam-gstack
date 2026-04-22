"""Phase 7 Wave 0 (Plan 07-01 Task 3): SprintState.queue_status additive field.

Tests:
- Default empty string.
- Round-trip via save/load preserves non-empty values.
- Rate-limit-saturated value round-trips.
- Legacy state.json without queue_status key loads with default "".
- Phase-2/Phase-4 fields coexist with queue_status.
"""
from __future__ import annotations

import json

import pytest

from clawteam.sprint.state import SprintState, load_sprint_state, save_sprint_state


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _make_state(team: str = "t1", sprint_id: str = "abcd1234") -> SprintState:
    return SprintState(
        sprint_id=sprint_id,
        goal="test",
        team=team,
        current_phase="think",
    )


def test_default_empty(isolated_data_dir):
    state = _make_state()
    assert state.queue_status == ""


def test_setter_round_trip(isolated_data_dir):
    state = _make_state()
    state.queue_status = "queued_capacity"
    save_sprint_state(state)
    loaded = load_sprint_state(state.team, state.sprint_id)
    assert loaded.queue_status == "queued_capacity"


def test_rate_limit_saturated_round_trip(isolated_data_dir):
    state = _make_state(sprint_id="rate0001")
    state.queue_status = "rate_limit_saturated"
    save_sprint_state(state)
    loaded = load_sprint_state(state.team, state.sprint_id)
    assert loaded.queue_status == "rate_limit_saturated"


def test_legacy_state_json_loads(isolated_data_dir):
    """A state.json written BEFORE Phase 7 (no queue_status key) loads cleanly."""
    state = _make_state(sprint_id="legacy01")
    save_sprint_state(state)
    # Simulate legacy: rewrite file stripping queue_status.
    path = SprintState._state_path(state.team, state.sprint_id)
    data = json.loads(path.read_text())
    data.pop("queue_status", None)
    path.write_text(json.dumps(data, indent=2))
    # Load — queue_status field must default to "".
    loaded = load_sprint_state(state.team, state.sprint_id)
    assert loaded.queue_status == ""


def test_all_phase2_4_fields_coexist(isolated_data_dir):
    state = _make_state(sprint_id="coexist1")
    state.turn_counters = {"pm": 3}
    state.artifact_cap_bytes = 70_000
    state.status = "paused"
    state.careful_enabled = True
    state.review_sha = "deadbeefcafe"
    state.queue_status = "queued_capacity"
    save_sprint_state(state)
    loaded = load_sprint_state(state.team, state.sprint_id)
    assert loaded.turn_counters == {"pm": 3}
    assert loaded.artifact_cap_bytes == 70_000
    assert loaded.status == "paused"
    assert loaded.careful_enabled is True
    assert loaded.review_sha == "deadbeefcafe"
    assert loaded.queue_status == "queued_capacity"
