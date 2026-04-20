"""Tests for clawteam.sprint.state.SprintState — pydantic model + file_locked persistence."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path

import pytest
from pydantic import ValidationError

from clawteam.sprint.state import SprintState

HEX8 = re.compile(r"^[0-9a-f]{8}$")


def _setup_hermetic_fs(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))


def test_sprint_state_required_fields_and_defaults(monkeypatch, tmp_path):
    """Every RFC 001 §4.4 field exists with the documented default."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    s = SprintState(
        goal="ship dark mode",
        team="t1",
        current_phase="discuss",
        created_at="2026-04-16T00:00:00Z",
    )
    assert s.goal == "ship dark mode"
    assert s.team == "t1"
    assert s.current_phase == "discuss"
    assert HEX8.match(s.sprint_id), f"sprint_id {s.sprint_id!r} is not 8-char hex"
    assert s.phase_history == []
    assert s.artifacts == {}
    assert s.participants == []
    assert s.pending_question_ids == []
    assert s.auto_advance is True
    assert s.workspace_branch == ""
    assert s.created_at == "2026-04-16T00:00:00Z"


def test_sprint_state_sprint_id_default_is_8_char_hex(monkeypatch, tmp_path):
    """default_factory mirrors SprintContract.id — uuid4 hex truncated to 8 chars."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    a = SprintState(goal="a", team="t", current_phase="discuss", created_at="2026-04-16T00:00:00Z")
    b = SprintState(goal="b", team="t", current_phase="discuss", created_at="2026-04-16T00:00:00Z")
    assert HEX8.match(a.sprint_id)
    assert HEX8.match(b.sprint_id)
    assert a.sprint_id != b.sprint_id


def test_sprint_state_save_then_load_roundtrip(monkeypatch, tmp_path):
    """SprintState.save -> SprintState.load preserves every field."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    s = SprintState(
        goal="ship dark mode",
        team="myteam",
        current_phase="plan",
        created_at="2026-04-16T00:00:00Z",
        participants=["pm", "ceo", "engineer"],
        artifacts={"design-doc.md": "/tmp/d.md"},
        phase_history=[{"phase": "think", "completed_at": "2026-04-16T00:10:00Z"}],
        workspace_branch="sprint/dark-mode",
        auto_advance=False,
        pending_question_ids=["q1"],
    )
    s.save(team="myteam")
    state_path = tmp_path / "teams" / "myteam" / "sprints" / s.sprint_id / "state.json"
    assert state_path.exists()

    loaded = SprintState.load(team="myteam", sprint_id=s.sprint_id)
    assert loaded.model_dump() == s.model_dump()


def test_sprint_state_concurrent_writers_last_write_wins(monkeypatch, tmp_path):
    """Concurrent writers serialize under file_locked; no corruption, last write wins."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    base = SprintState(
        goal="initial",
        team="t-concurrent",
        current_phase="plan",
        created_at="2026-04-16T00:00:00Z",
    )
    base.save(team="t-concurrent")

    markers = [f"goal-from-thread-{i}" for i in range(8)]
    errors: list[BaseException] = []

    def writer(marker: str):
        try:
            loaded = SprintState.load(team="t-concurrent", sprint_id=base.sprint_id)
            loaded.goal = marker
            loaded.save(team="t-concurrent")
        except BaseException as exc:  # noqa: BLE001 — capture for main-thread assertion
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(m,)) for m in markers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent writers raised: {errors}"
    final = SprintState.load(team="t-concurrent", sprint_id=base.sprint_id)
    assert final.goal in markers, (
        f"final goal {final.goal!r} is not one of the thread markers — corruption suspected"
    )
    # Atomic writer must clean up its tempfiles — no stray *.tmp in the sprint dir.
    sprint_dir = tmp_path / "teams" / "t-concurrent" / "sprints" / base.sprint_id
    stray = list(sprint_dir.glob("*.tmp"))
    assert not stray, f"stray tempfiles left behind: {stray}"


def test_sprint_state_invalid_team_raises(monkeypatch, tmp_path):
    """Path-traversal attempts via `team` are rejected at save time — no filesystem side effect."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    s = SprintState(goal="x", team="t1", current_phase="discuss", created_at="2026-04-16T00:00:00Z")
    with pytest.raises(ValueError):
        s.save(team="../../etc")
    # Nothing should have been created outside the data dir.
    assert not (tmp_path.parent / "etc").exists()


def test_sprint_state_invalid_sprint_id_raises(monkeypatch, tmp_path):
    """Path-traversal attempts via `sprint_id` are rejected at save time."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    s = SprintState(
        sprint_id="../../etc/passwd",
        goal="x",
        team="t1",
        current_phase="discuss",
        created_at="2026-04-16T00:00:00Z",
    )
    with pytest.raises(ValueError):
        s.save(team="t1")


def test_sprint_state_path_contains_both_team_and_sprint_id(monkeypatch, tmp_path):
    """_state_path composes team and sprint_id under the data dir."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    p = SprintState._state_path(team="alpha-team", sprint_id="abcd1234")
    suffix = str(Path("teams") / "alpha-team" / "sprints" / "abcd1234" / "state.json")
    assert str(p).endswith(suffix), f"path {p!s} does not end with {suffix!r}"


# ── Phase 2 additive-field tests (02-CONTEXT §D-14/D-15/D-16/D-21/D-27/D-28) ──
# Every new field has a default so Phase 1 state.json files rehydrate cleanly
# (pydantic v2 BC guarantee — 02-RESEARCH §Runtime State Inventory).


def test_sprint_state_turn_counters_defaults_to_empty_dict():
    """turn_counters default_factory=dict — per-agent theater detection counter (D-14)."""
    state = SprintState(
        goal="x",
        team="t",
        current_phase="think",
        created_at="2026-04-17T00:00:00Z",
    )
    assert state.turn_counters == {}
    assert isinstance(state.turn_counters, dict)


def test_sprint_state_artifact_cap_bytes_defaults_to_50kb():
    """artifact_cap_bytes default = 50 * 1024 = 51200 (D-27 per-file cap)."""
    state = SprintState(
        goal="x",
        team="t",
        current_phase="think",
        created_at="2026-04-17T00:00:00Z",
    )
    assert state.artifact_cap_bytes == 50 * 1024
    assert state.artifact_cap_bytes == 51200


def test_sprint_state_phase_artifact_cap_bytes_defaults_to_500kb():
    """phase_artifact_cap_bytes default = 500 * 1024 = 512000 (D-28 per-phase cap)."""
    state = SprintState(
        goal="x",
        team="t",
        current_phase="think",
        created_at="2026-04-17T00:00:00Z",
    )
    assert state.phase_artifact_cap_bytes == 500 * 1024
    assert state.phase_artifact_cap_bytes == 512000


def test_sprint_state_status_defaults_to_running():
    """status Literal['running','paused','completed'] defaults to 'running' (D-22 pause idempotency)."""
    state = SprintState(
        goal="x",
        team="t",
        current_phase="think",
        created_at="2026-04-17T00:00:00Z",
    )
    assert state.status == "running"
    for ok in ["running", "paused", "completed"]:
        assert (
            SprintState(
                goal="x",
                team="t",
                current_phase="think",
                created_at="2026-04-17T00:00:00Z",
                status=ok,
            ).status
            == ok
        )
    with pytest.raises(ValidationError):
        SprintState(
            goal="x",
            team="t",
            current_phase="think",
            created_at="2026-04-17T00:00:00Z",
            status="bogus",
        )


def test_sprint_state_suppressed_topics_defaults_to_empty_dict():
    """suppressed_topics default_factory=dict — cycle-detector suppression persistence (D-21)."""
    state = SprintState(
        goal="x",
        team="t",
        current_phase="think",
        created_at="2026-04-17T00:00:00Z",
    )
    assert state.suppressed_topics == {}
    assert isinstance(state.suppressed_topics, dict)


def test_sprint_state_rehydrates_from_phase1_json_without_new_fields():
    """BC invariant: pydantic v2 default-fills missing fields (RESEARCH Runtime State Inventory).

    Phase 1 state.json files on disk have only the 11 RFC 001 §4.4 fields. After Phase 2
    ships, model_validate(phase1_dict) MUST succeed and auto-populate Phase 2 defaults.
    """
    phase1_dict = {
        "sprint_id": "abc12345",
        "goal": "ship dark mode",
        "team": "gstack",
        "current_phase": "plan",
        "phase_history": [],
        "artifacts": {},
        "participants": ["engineer"],
        "pending_question_ids": [],
        "auto_advance": True,
        "workspace_branch": "feature/dark-mode",
        "created_at": "2026-04-16T10:00:00Z",
    }
    state = SprintState.model_validate(phase1_dict)
    assert state.turn_counters == {}
    assert state.artifact_cap_bytes == 50 * 1024
    assert state.phase_artifact_cap_bytes == 500 * 1024
    assert state.status == "running"
    assert state.suppressed_topics == {}
    # Phase 1 fields still round-trip identically.
    assert state.sprint_id == "abc12345"
    assert state.goal == "ship dark mode"
    assert state.workspace_branch == "feature/dark-mode"


def test_sprint_state_save_load_roundtrip_with_phase2_fields(monkeypatch, tmp_path):
    """save -> load preserves every Phase 2 field byte-equal."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    s = SprintState(
        goal="ship dark mode",
        team="team1",
        current_phase="plan",
        created_at="2026-04-16T00:00:00Z",
        turn_counters={"engineer": 3, "reviewer": 1},
        artifact_cap_bytes=100_000,
        phase_artifact_cap_bytes=1_000_000,
        status="paused",
        suppressed_topics={"engineer->reviewer": ["abc123"]},
    )
    s.save(team="team1")
    loaded = SprintState.load(team="team1", sprint_id=s.sprint_id)
    assert loaded.model_dump() == s.model_dump()
    # Explicit field checks for trace readability.
    assert loaded.turn_counters == {"engineer": 3, "reviewer": 1}
    assert loaded.artifact_cap_bytes == 100_000
    assert loaded.phase_artifact_cap_bytes == 1_000_000
    assert loaded.status == "paused"
    assert loaded.suppressed_topics == {"engineer->reviewer": ["abc123"]}


def test_sprint_state_load_of_legacy_phase1_file_rehydrates_defaults(monkeypatch, tmp_path):
    """A raw Phase-1-shape JSON file on disk loads through .load() with Phase 2 defaults applied.

    Mirrors RESEARCH §Runtime State Inventory: Phase 1 users upgrade cleanly without
    a migration script — pydantic v2 BC default-fills missing fields on model_validate.
    """
    _setup_hermetic_fs(monkeypatch, tmp_path)
    team = "legacy-team"
    sprint_id = "deadbeef"
    phase1_shape = {
        "sprint_id": sprint_id,
        "goal": "legacy goal",
        "team": team,
        "current_phase": "plan",
        "phase_history": [{"phase": "think", "completed_at": "2026-04-16T00:05:00Z"}],
        "artifacts": {"design-doc.md": "/tmp/d.md"},
        "participants": ["pm", "ceo"],
        "pending_question_ids": [],
        "auto_advance": True,
        "workspace_branch": "feature/legacy",
        "created_at": "2026-04-16T00:00:00Z",
    }
    # Write the legacy JSON directly (bypassing .save so no Phase 2 fields leak in).
    sprint_dir = tmp_path / "teams" / team / "sprints" / sprint_id
    sprint_dir.mkdir(parents=True, exist_ok=True)
    (sprint_dir / "state.json").write_text(json.dumps(phase1_shape, indent=2), encoding="utf-8")

    loaded = SprintState.load(team=team, sprint_id=sprint_id)
    # Phase 1 fields preserved.
    assert loaded.sprint_id == sprint_id
    assert loaded.goal == "legacy goal"
    assert loaded.workspace_branch == "feature/legacy"
    assert loaded.artifacts == {"design-doc.md": "/tmp/d.md"}
    # Phase 2 fields auto-defaulted.
    assert loaded.turn_counters == {}
    assert loaded.artifact_cap_bytes == 50 * 1024
    assert loaded.phase_artifact_cap_bytes == 500 * 1024
    assert loaded.status == "running"
    assert loaded.suppressed_topics == {}
