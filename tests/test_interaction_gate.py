"""Tests for clawteam.harness.interaction_gate.InteractionGate."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from clawteam.harness.interaction_gate import InteractionGate
from clawteam.sprint.state import SprintState

from clawteam.harness.phases import PhaseState


def _hermetic(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))


def _sprint_state(team="t1", sprint_id=None, goal="g", current_phase="plan"):
    kwargs = {
        "goal": goal,
        "team": team,
        "current_phase": current_phase,
        "created_at": "2026-04-16T00:00:00Z",
    }
    if sprint_id is not None:
        kwargs["sprint_id"] = sprint_id
    return SprintState(**kwargs)


def _sprint_dir(tmp_path: Path, team: str, sprint_id: str) -> Path:
    d = tmp_path / "teams" / team / "sprints" / sprint_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write(p: Path, body: str = "question body\n") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_gate_passes_when_no_sprint_dir(monkeypatch, tmp_path):
    """PhaseState without sprint context: no questions to block on."""
    _hermetic(monkeypatch, tmp_path)
    gate = InteractionGate()
    passed, reason = gate.check(PhaseState(team_name="t1", current_phase="plan"))
    assert passed is True
    assert reason == ""


def test_gate_passes_when_questions_dir_absent(monkeypatch, tmp_path):
    """Sprint dir exists but no questions/ subdir: gate passes."""
    _hermetic(monkeypatch, tmp_path)
    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.save(team="t1")  # creates sprint dir + state.json, no questions/
    gate = InteractionGate()
    passed, reason = gate.check(state)
    assert passed is True
    assert reason == ""


def test_gate_passes_when_all_questions_answered(monkeypatch, tmp_path):
    """Every question has a sibling answer: gate passes."""
    _hermetic(monkeypatch, tmp_path)
    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.save(team="t1")
    d = _sprint_dir(tmp_path, "t1", "abcd1234")
    _write(d / "questions" / "a1b2c3d4.md", "Q body")
    _write(d / "answers" / "a1b2c3d4.md", "A body")

    gate = InteractionGate()
    passed, reason = gate.check(state)
    assert passed is True
    assert reason == ""


def test_gate_fails_when_one_question_unanswered(monkeypatch, tmp_path):
    """A single unanswered question blocks; reason starts with 'Open questions:'."""
    _hermetic(monkeypatch, tmp_path)
    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.save(team="t1")
    d = _sprint_dir(tmp_path, "t1", "abcd1234")
    _write(d / "questions" / "a1b2c3d4.md")

    gate = InteractionGate()
    passed, reason = gate.check(state)
    assert passed is False
    assert reason.startswith("Open questions: "), f"reason={reason!r}"
    assert "a1b2c3d4" in reason


def test_gate_fails_reason_lists_unanswered_ids_in_order(monkeypatch, tmp_path):
    """Only the unanswered IDs appear, in sorted order."""
    _hermetic(monkeypatch, tmp_path)
    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.save(team="t1")
    d = _sprint_dir(tmp_path, "t1", "abcd1234")
    _write(d / "questions" / "aa111111.md")
    _write(d / "questions" / "bb222222.md")
    _write(d / "questions" / "cc333333.md")
    _write(d / "answers" / "bb222222.md")

    gate = InteractionGate()
    passed, reason = gate.check(state)
    assert passed is False
    assert reason == "Open questions: aa111111, cc333333", f"reason={reason!r}"


def test_gate_reason_truncates_after_5_ids(monkeypatch, tmp_path):
    """More than 5 unanswered IDs: first 5 listed + '+N more' suffix."""
    _hermetic(monkeypatch, tmp_path)
    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.save(team="t1")
    d = _sprint_dir(tmp_path, "t1", "abcd1234")
    for i in range(7):
        _write(d / "questions" / f"q{i}.md")

    gate = InteractionGate()
    passed, reason = gate.check(state)
    assert passed is False
    assert reason == "Open questions: q0, q1, q2, q3, q4 +2 more", f"reason={reason!r}"


def test_gate_with_sprint_state_derives_path_correctly(monkeypatch, tmp_path):
    """Path is derived from (state.team, state.sprint_id) — save() not required."""
    _hermetic(monkeypatch, tmp_path)
    state = _sprint_state(team="myteam", sprint_id="0badbeef")
    # Explicitly DO NOT call save(). Create the questions dir by hand.
    d = _sprint_dir(tmp_path, "myteam", "0badbeef")
    _write(d / "questions" / "ffff0000.md")

    gate = InteractionGate()
    passed, reason = gate.check(state)
    assert passed is False
    assert "ffff0000" in reason


def test_gate_rejects_symlink_escape_from_data_dir(monkeypatch, tmp_path):
    """A symlink escaping the data dir either raises ValueError or returns a fail tuple."""
    _hermetic(monkeypatch, tmp_path)
    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.save(team="t1")
    d = _sprint_dir(tmp_path, "t1", "abcd1234")

    target = tmp_path.parent / "etc"
    target.mkdir(exist_ok=True)
    questions_dir = d / "questions"
    try:
        os.symlink(target, questions_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation not supported on this platform")

    gate = InteractionGate()
    try:
        passed, reason = gate.check(state)
    except ValueError as exc:
        # Acceptable mitigation: raise on escape.
        assert "invalid" in str(exc).lower() or "escape" in str(exc).lower()
    else:
        # Alternative acceptable mitigation: return a fail tuple.
        assert passed is False
        assert "invalid sprint path" in reason.lower() or "escape" in reason.lower()
