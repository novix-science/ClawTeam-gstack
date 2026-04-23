"""Tests for the solo-UX top-level commands (clawteam go/status/answer/stop).

These exercise the active-team pointer logic + empty-state messaging. The
full `clawteam go` one-shot path (which spawns subprocess chains) is
covered by real-env verification — see commit bb18c8e for timings.
"""
from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app
from clawteam.solo import (
    clear_active_team,
    get_active_team,
    set_active_team,
)
from clawteam.team.manager import TeamManager


def _isolate(monkeypatch, tmp_path):
    """Point CLAWTEAM_DATA_DIR at a temp dir + chdir to avoid leak."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)


# ---------------------------------------------------------------------------
# Active-team pointer mechanics
# ---------------------------------------------------------------------------

def test_active_team_pointer_roundtrip(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    assert get_active_team() is None

    set_active_team("alpha")
    assert get_active_team() == "alpha"

    # Overwrite
    set_active_team("beta")
    assert get_active_team() == "beta"

    clear_active_team()
    assert get_active_team() is None


def test_active_team_honors_whitespace(monkeypatch, tmp_path):
    """A file with only whitespace should be treated as 'no active team'."""
    _isolate(monkeypatch, tmp_path)
    pointer = tmp_path / "active_team"
    pointer.write_text("   \n  \n", encoding="utf-8")
    assert get_active_team() is None


# ---------------------------------------------------------------------------
# Empty-state output for status / answer / stop
# ---------------------------------------------------------------------------

def test_status_empty_state_points_to_go(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["status"], env={"CLAWTEAM_DATA_DIR": str(tmp_path)})
    assert result.exit_code == 0
    assert "No active team" in result.output
    assert "clawteam go" in result.output


def test_answer_empty_state_points_to_go(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["answer"], env={"CLAWTEAM_DATA_DIR": str(tmp_path)})
    assert result.exit_code == 0
    assert "No active team" in result.output
    assert "clawteam go" in result.output


def test_stop_empty_state_is_noop(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    runner = CliRunner()
    result = runner.invoke(app, ["stop", "--force"], env={"CLAWTEAM_DATA_DIR": str(tmp_path)})
    assert result.exit_code == 0
    assert "No active team" in result.output
    assert "Nothing to stop" in result.output


def test_status_stale_pointer_reports_mismatch(monkeypatch, tmp_path):
    """If active_team points to a team that doesn't exist, surface clearly."""
    _isolate(monkeypatch, tmp_path)
    set_active_team("ghost-team-42")

    runner = CliRunner()
    result = runner.invoke(app, ["status"], env={"CLAWTEAM_DATA_DIR": str(tmp_path)})
    assert result.exit_code == 1
    assert "ghost-team-42" in result.output
    assert "stale" in result.output.lower() or "not found" in result.output.lower()


# ---------------------------------------------------------------------------
# Stop flow clears active pointer and invokes team cleanup
# ---------------------------------------------------------------------------

def test_stop_clears_active_pointer(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    TeamManager.create_team(
        name="my-team", leader_name="leader", leader_id="leader-id",
    )
    set_active_team("my-team")
    assert get_active_team() == "my-team"

    runner = CliRunner()
    result = runner.invoke(
        app, ["stop", "--force"],
        env={"CLAWTEAM_DATA_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert get_active_team() is None, "active pointer should be cleared after stop"
    assert "my-team" in result.output


def test_stop_with_team_flag_overrides_active(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    TeamManager.create_team(name="team-a", leader_name="a", leader_id="aid")
    TeamManager.create_team(name="team-b", leader_name="b", leader_id="bid")
    set_active_team("team-a")

    runner = CliRunner()
    result = runner.invoke(
        app, ["stop", "--team", "team-b", "--force"],
        env={"CLAWTEAM_DATA_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert "team-b" in result.output
    # team-a was not touched — active pointer unchanged
    assert get_active_team() == "team-a"


# ---------------------------------------------------------------------------
# Status dashboard renders core fields
# ---------------------------------------------------------------------------

def test_status_renders_team_name_and_agent_count(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    TeamManager.create_team(name="t1", leader_name="ceo", leader_id="ceo-id")
    TeamManager.add_member(team_name="t1", member_name="pm", agent_id="pm-id", agent_type="pm")
    TeamManager.add_member(team_name="t1", member_name="engineer", agent_id="eng-id", agent_type="engineer")
    set_active_team("t1")

    runner = CliRunner()
    result = runner.invoke(app, ["status"], env={"CLAWTEAM_DATA_DIR": str(tmp_path)})
    assert result.exit_code == 0
    # Team name surfaced
    assert "t1" in result.output
    # 3 agents (ceo + pm + engineer)
    assert "3 agents" in result.output
    # Cost tracking was removed post-v1.0 UAT — dashboard now points at
    # the Anthropic console for real spend data.
    assert "console.anthropic.com" in result.output
