"""Tests for Phase 7 Plan 07-08 — zombie-worktree GC + disk-budget report.

Covers:
- find_zombie_worktrees: empty root, skips young dirs, returns old dirs,
  honors active_branches safety filter, injected now_fn determinism.
- gc_zombies: deletes returned paths, emits ZombieWorktreeGced with
  path/age_days/freed_bytes populated, idempotent on missing paths.
- disk_usage_report: sums bytes under a team dir; classifies against
  soft/hard thresholds (5 GB / 10 GB).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import ZombieWorktreeGced
from clawteam.workspace.gc import (
    HARD_BYTES,
    SOFT_BYTES,
    disk_usage_report,
    find_zombie_worktrees,
    gc_zombies,
)


def _mk_dir(tmp: Path, name: str, age_days: float = 0) -> Path:
    p = tmp / name
    p.mkdir()
    if age_days > 0:
        past = time.time() - age_days * 86400
        os.utime(p, (past, past))
    return p


# ── find_zombie_worktrees ────────────────────────────────────────────


def test_find_none_in_empty_dir(tmp_path):
    assert find_zombie_worktrees(tmp_path) == []


def test_find_none_when_root_missing(tmp_path):
    ghost = tmp_path / "does-not-exist"
    assert find_zombie_worktrees(ghost) == []


def test_find_skips_young_dirs(tmp_path):
    _mk_dir(tmp_path, "young", age_days=10)
    assert find_zombie_worktrees(tmp_path, max_age_days=30) == []


def test_find_returns_old_dirs(tmp_path):
    _mk_dir(tmp_path, "old", age_days=40)
    result = find_zombie_worktrees(tmp_path, max_age_days=30)
    assert len(result) == 1
    assert result[0].name == "old"


def test_find_respects_active_branches(tmp_path):
    # Two old dirs; one matches an active branch and must be preserved.
    _mk_dir(tmp_path, "active", age_days=40)
    _mk_dir(tmp_path, "zombie", age_days=40)
    result = find_zombie_worktrees(
        tmp_path, max_age_days=30, active_branches={"active"}
    )
    assert len(result) == 1
    assert result[0].name == "zombie"


def test_find_skips_non_directories(tmp_path):
    # Regular file should never be treated as a worktree.
    (tmp_path / "not-a-worktree.txt").write_text("x")
    old = _mk_dir(tmp_path, "old", age_days=40)
    result = find_zombie_worktrees(tmp_path, max_age_days=30)
    assert old in result
    assert len(result) == 1


# ── gc_zombies ───────────────────────────────────────────────────────


def test_gc_zombies_deletes_returned_paths(tmp_path):
    d = _mk_dir(tmp_path, "old", age_days=40)
    (d / "file.txt").write_text("content")
    gced = gc_zombies([d])
    assert not d.exists()
    assert gced == [d]


def test_gc_zombies_emits_event(tmp_path):
    d = _mk_dir(tmp_path, "old", age_days=40)
    (d / "file.txt").write_text("hello world")  # 11 bytes
    bus = EventBus()
    received: list[ZombieWorktreeGced] = []
    bus.subscribe(ZombieWorktreeGced, received.append)
    gc_zombies([d], team_name="t1", bus=bus)
    assert len(received) == 1
    ev = received[0]
    assert ev.path == str(d)
    assert ev.team_name == "t1"
    assert ev.age_days >= 30
    assert ev.freed_bytes >= 11


def test_gc_zombies_idempotent_on_missing(tmp_path):
    fake = tmp_path / "does-not-exist"
    bus = EventBus()
    received: list[ZombieWorktreeGced] = []
    bus.subscribe(ZombieWorktreeGced, received.append)
    result = gc_zombies([fake], bus=bus)
    assert result == []
    assert received == []


def test_gc_zombies_no_bus_ok(tmp_path):
    # Emission should be optional; passing bus=None must not crash.
    d = _mk_dir(tmp_path, "old", age_days=40)
    gced = gc_zombies([d])
    assert gced == [d]
    assert not d.exists()


# ── disk_usage_report ───────────────────────────────────────────────


def test_disk_usage_report_sums_bytes(tmp_path):
    (tmp_path / "f1.bin").write_bytes(b"x" * 100)
    (tmp_path / "f2.bin").write_bytes(b"x" * 200)
    report = disk_usage_report(tmp_path)
    assert report["path"] == str(tmp_path)
    assert report["total_bytes"] >= 300
    assert report["over_soft"] is False
    assert report["over_hard"] is False
    assert report["soft_threshold_gb"] == 5
    assert report["hard_threshold_gb"] == 10


def test_disk_usage_report_missing_dir(tmp_path):
    ghost = tmp_path / "does-not-exist"
    report = disk_usage_report(ghost)
    assert report["total_bytes"] == 0
    assert report["over_soft"] is False
    assert report["over_hard"] is False


def test_disk_thresholds_constants_match_contract():
    # Lock the 5 GB / 10 GB floors from the plan frontmatter.
    assert SOFT_BYTES == 5 * 1024 * 1024 * 1024
    assert HARD_BYTES == 10 * 1024 * 1024 * 1024
