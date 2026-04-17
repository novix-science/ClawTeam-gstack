"""Tests for clawteam.sprint.state.SprintState — pydantic model + file_locked persistence."""

from __future__ import annotations

import re
import threading
from pathlib import Path

import pytest

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
