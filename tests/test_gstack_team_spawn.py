"""Scaffold for Phase 3 Wave 0 (Plan 03-01 Task 3).

Tests currently skipped — Wave 4 (Plan 03-07) unskips as the end-to-end
`clawteam team spawn gstack --name <n>` UX-01 pipeline ships.

Covers: TEAM-03 (11 worktrees via WorkspaceManager), UX-01 (CLI end-to-end),
D-05 (per-role memory dirs pre-created idempotently at team spawn time).
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Wave 4: end-to-end spawn ships in 03-07-PLAN")
def test_eleven_worktrees_created(tmp_path, monkeypatch):
    """TEAM-03: spawning a gstack team calls WorkspaceManager.create_workspace
    exactly 11 times — one worktree/desk per agent.
    """
    pass


@pytest.mark.skip(reason="Wave 4: UX-01 end-to-end")
def test_team_spawn_gstack(tmp_path, monkeypatch):
    """UX-01: `clawteam team spawn gstack --name <n>` spawns 11 agents via
    the existing spawn registry (tmux/subprocess/wsh per backend declaration
    in gstack.toml).
    """
    pass


@pytest.mark.skip(reason="Wave 4: D-05 per-role memory dir pre-creation")
def test_per_role_memory_dirs_precreated(tmp_path, monkeypatch):
    """D-05: 11 memory dirs exist at
    ``<data_dir>/teams/<name>/memory/<role>/`` after `team spawn gstack`.

    Idempotent: re-running spawn doesn't raise even though the dirs exist.
    """
    pass
