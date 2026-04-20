"""Tests for clawteam.harness.freeze_registry — FreezeRegistry singleton.

Covers:
- freeze/unfreeze round-trip and persistence (freeze.json under sprint dir)
- is_frozen exact match, path-prefix match, data-dir exemption (Pitfall #5)
- Canonicalization / symlink defeat of path bypass (T-02-02)
- FrozenPathError message shape (§02-CONTEXT D-12)
- Append-only freeze_audit.jsonl (SAFETY-04, mirrors exit_journal.py)
- Pause/resume rehydration (SPRINT-02, QUALITY-06)
- 8-thread concurrent writer (file_locked serializes, no torn writes)
"""

from __future__ import annotations

import json
import sys
import threading
from pathlib import Path

import pytest
from clawteam.harness.freeze_registry import (
    FreezeRegistry,
    FrozenPathError,
    get_freeze_registry,
    reset_freeze_registry,
)


@pytest.fixture
def hermetic(tmp_path, monkeypatch):
    """Per-test hermetic filesystem layered on top of conftest's isolated_data_dir.

    The autouse conftest fixture sets CLAWTEAM_DATA_DIR to tmp_path/.clawteam.
    We override it to tmp_path directly so assertions on sprint paths can use
    `hermetic / "teams" / ...` without the nested .clawteam segment.
    """
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_freeze_registry()
    yield tmp_path
    reset_freeze_registry()


def _sprint_dir(base: Path, team: str, sprint: str) -> Path:
    return base / "teams" / team / "sprints" / sprint


def test_freeze_persists_to_freeze_json(hermetic):
    """freeze() writes the canonical path into freeze.json under paths[agent]."""
    reg = FreezeRegistry("team-x", "sprint-a")
    reg.freeze("/tmp/foo", agent="engineer", reason="investigation", actor="reviewer")

    fj = _sprint_dir(hermetic, "team-x", "sprint-a") / "freeze.json"
    assert fj.exists(), f"freeze.json not created at {fj}"
    data = json.loads(fj.read_text(encoding="utf-8"))
    assert "paths" in data
    assert "engineer" in data["paths"]
    # Canonical form should be /tmp/foo or /private/tmp/foo (macOS) — accept either.
    assert any(p.endswith("/tmp/foo") for p in data["paths"]["engineer"]), (
        f"expected /tmp/foo in engineer frozen paths; got {data['paths']['engineer']!r}"
    )


def test_unfreeze_removes_path(hermetic):
    """After unfreeze, is_frozen returns False for the path."""
    reg = FreezeRegistry("team-x", "sprint-a")
    reg.freeze("/tmp/to-remove", agent="engineer", reason="r", actor="actor")
    ok, _ = reg.is_frozen(Path("/tmp/to-remove"))
    assert ok is True

    reg.unfreeze("/tmp/to-remove", agent="engineer", reason="done", actor="actor")
    ok, _ = reg.is_frozen(Path("/tmp/to-remove"))
    assert ok is False


def test_is_frozen_returns_true_on_exact_match(hermetic):
    """freeze(/tmp/blocked); is_frozen(/tmp/blocked) -> (True, reason with engineer+/freeze)."""
    reg = FreezeRegistry("team-x", "sprint-a")
    reg.freeze("/tmp/blocked", agent="engineer", reason="review lock", actor="reviewer")

    ok, reason = reg.is_frozen(Path("/tmp/blocked"))
    assert ok is True
    assert "engineer" in reason
    assert "/freeze" in reason or "freeze-locked" in reason


def test_is_frozen_returns_true_on_path_prefix(hermetic):
    """A frozen directory should veto nested paths under it."""
    reg = FreezeRegistry("team-x", "sprint-a")
    reg.freeze("/tmp/locked_dir", agent="engineer", reason="dir lock", actor="reviewer")

    ok, reason = reg.is_frozen(Path("/tmp/locked_dir/nested/file.py"))
    assert ok is True, f"expected nested path vetoed; reason={reason!r}"


def test_is_frozen_returns_false_for_paths_under_data_dir(hermetic):
    """Pitfall #5: sprint-internal writes must never be vetoed, even after /freeze /."""
    reg = FreezeRegistry("team-x", "sprint-a")
    reg.freeze("/", agent="engineer", reason="lock everything", actor="reviewer")

    state_json = _sprint_dir(hermetic, "team-x", "sprint-a") / "state.json"
    state_json.parent.mkdir(parents=True, exist_ok=True)
    state_json.write_text("{}", encoding="utf-8")

    ok, reason = reg.is_frozen(state_json)
    assert ok is False, (
        f"sprint-internal path vetoed — breaks pause/resume (Pitfall #5). reason={reason!r}"
    )
    assert reason == ""


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="symlink creation requires admin on Windows CI runners",
)
def test_is_frozen_canonicalizes_relative_paths_and_symlinks(hermetic, tmp_path):
    """T-02-02 mitigation: symlink pointing into frozen dir is resolved and vetoed.

    Also exercises canonicalization: a relative form like `real/../real/file`
    must hash to the same canonical path as `real/file`.
    """
    real_dir = tmp_path / "real"
    real_dir.mkdir()
    real_file = real_dir / "locked.txt"
    real_file.write_text("x", encoding="utf-8")

    reg = FreezeRegistry("team-x", "sprint-a")
    reg.freeze(str(real_dir), agent="engineer", reason="lock real dir", actor="reviewer")

    # Symlink inside an otherwise-unfrozen dir points INTO the frozen dir.
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    symlink = outside_dir / "link"
    symlink.symlink_to(real_file)

    ok, reason = reg.is_frozen(symlink)
    assert ok is True, f"symlink bypass not defeated; reason={reason!r}"

    # Relative-path canonicalization: `real/../real/locked.txt` → `real/locked.txt`.
    tricky = Path(str(real_dir) + "/../real/locked.txt")
    ok2, _ = reg.is_frozen(tricky)
    assert ok2 is True, "relative-path canonicalization failed — .. segments not collapsed"


def test_frozen_path_error_message_mentions_unfreeze(hermetic):
    """D-12: FrozenPathError is a ValueError subclass with a message mentioning /unfreeze.

    We construct the error from the registry's veto-reason string and assert
    the shape documented in §02-CONTEXT D-12:
        "<path> is /freeze-locked by <who>; unfreeze via /unfreeze <path>"
    """
    assert issubclass(FrozenPathError, ValueError)

    reg = FreezeRegistry("team-x", "sprint-a")
    reg.freeze("/tmp/whatever", agent="engineer", reason="r", actor="actor")
    ok, reason = reg.is_frozen(Path("/tmp/whatever"))
    assert ok is True

    err = FrozenPathError(reason)
    assert "/unfreeze" in err.args[0]
    assert "freeze-locked" in err.args[0]
    assert "engineer" in err.args[0]


def test_audit_jsonl_append_per_action(hermetic):
    """After 3 freezes + 2 unfreezes, freeze_audit.jsonl has 5 valid one-per-line JSON entries.

    Proves append-only (second freeze did NOT rewrite the first) + per-action
    schema {ts, action, path, agent, reason, actor, sprint_id}.
    """
    reg = FreezeRegistry("team-x", "sprint-a")
    reg.freeze("/tmp/a", agent="engineer", reason="r1", actor="reviewer")
    reg.freeze("/tmp/b", agent="engineer", reason="r2", actor="reviewer")
    reg.freeze("/tmp/c", agent="qa", reason="r3", actor="reviewer")
    reg.unfreeze("/tmp/a", agent="engineer", reason="done-a", actor="reviewer")
    reg.unfreeze("/tmp/b", agent="engineer", reason="done-b", actor="reviewer")

    audit_path = _sprint_dir(hermetic, "team-x", "sprint-a") / "freeze_audit.jsonl"
    assert audit_path.exists()
    lines = [ln for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 5, f"expected 5 entries, got {len(lines)}"

    required_keys = {"ts", "action", "path", "agent", "reason", "actor", "sprint_id"}
    for i, line in enumerate(lines):
        entry = json.loads(line)
        missing = required_keys - entry.keys()
        assert not missing, f"line {i} missing keys: {missing}"
        assert entry["sprint_id"] == "sprint-a"

    actions = [json.loads(ln)["action"] for ln in lines]
    assert actions == ["freeze", "freeze", "freeze", "unfreeze", "unfreeze"]


def test_freeze_persists_across_reset_and_rehydrate(hermetic):
    """freeze.json rehydrates the in-memory state — essential for sprint pause/resume.

    Exercises the get_freeze_registry / reset_freeze_registry singleton pair
    (Plan 02-11 uses this exact call shape when SprintConductor.resume() restores
    the registry from freeze.json on disk).
    """
    reg1 = get_freeze_registry("team-x", "sprint-a")
    assert reg1 is not None
    reg1.freeze("/tmp/x", agent="engineer", reason="persist", actor="reviewer")

    # Simulate process restart by dropping the singleton + re-instantiating via
    # the module-level accessor (triggers FreezeRegistry.__init__ -> _load).
    reset_freeze_registry()
    reg2 = get_freeze_registry("team-x", "sprint-a")
    assert reg2 is not None
    assert reg2 is not reg1, "singleton must be reconstructed after reset"
    ok, _ = reg2.is_frozen(Path("/tmp/x"))
    assert ok is True, "freeze.json did not rehydrate after reset — pause/resume broken"


def test_8_concurrent_writers_freeze_json_last_write_wins(hermetic):
    """file_locked serializes concurrent writers; no torn state, no stray tmp files.

    Mirrors tests/test_sprint_state.py::test_sprint_state_concurrent_writers_last_write_wins.
    """
    reg = FreezeRegistry("team-x", "sprint-a")
    errors: list[BaseException] = []

    def _worker(i: int) -> None:
        try:
            reg.freeze(f"/tmp/path-{i}", agent=f"a{i}", reason="r", actor="actor")
        except BaseException as exc:  # noqa: BLE001 — capture for main-thread assertion
            errors.append(exc)

    threads = [threading.Thread(target=_worker, args=(i,)) for i in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"concurrent writers raised: {errors}"

    fj = _sprint_dir(hermetic, "team-x", "sprint-a") / "freeze.json"
    assert fj.exists()
    data = json.loads(fj.read_text(encoding="utf-8"))
    # At least one agent's write must have survived (last-write-wins with per-agent keys).
    assert len(data.get("paths", {})) >= 1

    # Atomic writer must clean up tempfiles — no stray *.tmp in the sprint dir.
    stray = list(fj.parent.glob("*.tmp"))
    assert stray == [], f"stray tmpfiles left behind: {stray}"
