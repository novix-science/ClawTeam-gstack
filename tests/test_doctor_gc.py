"""Tests for Phase 7 Plan 07-08 — ``clawteam doctor --gc`` wiring.

Covers:
- The ``--gc`` flag is additive: plain ``clawteam doctor`` still exits 0
  and prints the existing tool checklist unchanged (BC lock).
- ``clawteam doctor --gc`` with no teams dir exits 0 with zero zombies.
- ``clawteam doctor --gc`` finds + deletes old worktrees under each team
  and reports the count.
- ``clawteam doctor --gc`` respects active SprintState workspace_branches
  — an old worktree whose basename matches an active sprint's branch is
  preserved (safety invariant from 07-RESEARCH §Pitfall 6).
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app


def _make_worktree(data_dir: Path, team: str, name: str, age_days: float = 0) -> Path:
    """Build a worktree at the REAL layout used by WorkspaceManager.

    ``WorkspaceManager._workspaces_root()`` creates per-agent worktrees
    at ``<data_dir>/workspaces/<team>/<agent>/``. The earlier test
    helper wrote to ``teams/<team>/worktrees/<name>/`` which the doctor
    GC pass never scans (CR-01); tests pre-CR-01-fix passed by mirroring
    the buggy scan path rather than the real production layout.
    """
    wt = data_dir / "workspaces" / team / name
    wt.mkdir(parents=True)
    (wt / "file.txt").write_text("content")
    if age_days > 0:
        past = time.time() - age_days * 86400
        # Apply AFTER populating — writing file.txt bumps parent mtime.
        os.utime(wt, (past, past))
    return wt


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    # Some modules cache get_data_dir results via clawteam.config.load_config;
    # override is via the env var which get_data_dir consults directly each
    # call. No further setup needed.
    return tmp_path


def test_doctor_no_gc_flag_preserves_old_behavior(isolated_data_dir):
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    # The existing checklist must still render.
    assert "chromium (Playwright)" in result.output or "chromium" in result.output


def test_doctor_gc_empty_teams(isolated_data_dir):
    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--gc"])
    assert result.exit_code == 0, result.output


def test_doctor_gc_finds_and_cleans(isolated_data_dir):
    runner = CliRunner()
    team_dir = isolated_data_dir / "teams" / "t1"
    team_dir.mkdir(parents=True)
    zombie = _make_worktree(isolated_data_dir, "t1", "old-branch", age_days=40)
    young = _make_worktree(isolated_data_dir, "t1", "fresh-branch", age_days=5)

    result = runner.invoke(app, ["--json", "doctor", "--gc"])
    assert result.exit_code == 0, result.output

    # --json output includes the full doctor dict plus gc summary.
    data = json.loads(result.stdout)
    # The plan contract exposes total_zombies / teams[] under a gc key
    # OR at the top level — accept either shape.
    gc_data = data.get("gc", data)
    assert gc_data.get("total_zombies", 0) == 1

    # Filesystem effects: old worktree gone, young one preserved.
    assert not zombie.exists()
    assert young.exists()


def test_doctor_gc_respects_active_sprints(isolated_data_dir):
    from clawteam.sprint.state import SprintState, save_sprint_state

    runner = CliRunner()
    team_dir = isolated_data_dir / "teams" / "t1"
    team_dir.mkdir(parents=True)

    # Two old worktrees — one matches an active SprintState branch.
    active_wt = _make_worktree(isolated_data_dir, "t1", "active-branch", age_days=40)
    zombie_wt = _make_worktree(isolated_data_dir, "t1", "zombie-branch", age_days=40)

    # Create SprintState pointing at active-branch. SprintState.save writes
    # to ~/.clawteam/teams/t1/sprints/<sprint_id>/state.json — CLAWTEAM_DATA_DIR
    # redirects the root into tmp_path.
    sprint = SprintState(
        sprint_id="aaaa1111",
        goal="keep me alive",
        team="t1",
        current_phase="think",
        workspace_branch="active-branch",
    )
    save_sprint_state(sprint)

    result = runner.invoke(app, ["doctor", "--gc"])
    assert result.exit_code == 0, result.output

    # Active branch preserved; zombie removed.
    assert active_wt.exists(), "active-sprint branch must NOT be gc'd"
    assert not zombie_wt.exists(), "unrelated old worktree SHOULD be gc'd"
