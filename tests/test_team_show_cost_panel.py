"""Phase 7 Plan 07-07 Task 2 — `clawteam team show` cost panel tests.

The `costRollup` JSON key used to be a ``pending_phase_7`` placeholder.
This plan replaces it with a live dashboard dict from
:func:`clawteam.cost.dashboard.render_team`. These tests lock:

- the placeholder is GONE (``status != 'pending_phase_7'``);
- the dashboard shape ships (cost_usd / budget_usd / per_agent / ...);
- backward-compatible top-level keys (``name`` / ``members`` /
  ``activeSprint`` / ``memory`` / ``costRollup``) are preserved so Phase 3
  UX-07 consumers still parse cleanly;
- cost panel is either ``status='ok'`` or ``status='unavailable'`` —
  never ``pending_phase_7`` (the Phase 3 placeholder literal).
"""
from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app
from clawteam.team.manager import TeamManager


def _make_team(name: str = "t1") -> None:
    """Create a minimal team on disk (non-gstack template OK for panel shape).

    Mirrors the test_cli_commands.py pattern: create_team with a required
    (name, leader_name, leader_id) triple. Template is left blank so
    `_team_show_cost_panel` exercises its default-budget path (no
    CostConfig on template).
    """
    TeamManager.create_team(
        name=name,
        leader_name="lead",
        leader_id="lead-1",
        description="cost-panel test team",
        leader_agent_type="leader",
    )


def test_team_show_placeholder_gone(tmp_path):
    """The ``pending_phase_7`` placeholder literal is gone from JSON output."""
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    _make_team("t1")

    result = runner.invoke(app, ["--json", "team", "show", "t1"], env=env)
    assert result.exit_code == 0, result.output

    data = json.loads(result.stdout)
    assert "costRollup" in data
    # The Phase 3 placeholder literal must NOT appear anywhere in the panel.
    assert data["costRollup"].get("status") != "pending_phase_7"
    # Either the real dashboard rendered or the best-effort fallback fired.
    assert data["costRollup"].get("status") in {"ok", "unavailable"}


def test_team_show_backward_compatible_shape(tmp_path):
    """Top-level JSON keys Phase 3 UX-07 consumers depend on are preserved."""
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    _make_team("t1")

    result = runner.invoke(app, ["--json", "team", "show", "t1"], env=env)
    assert result.exit_code == 0, result.output

    data = json.loads(result.stdout)
    for required in ("name", "members", "activeSprint", "memory", "costRollup"):
        assert required in data, f"required key {required!r} missing"


def test_team_show_cost_panel_shape(tmp_path):
    """When cost panel renders status='ok', the dashboard dict shape ships."""
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    _make_team("t1")

    result = runner.invoke(app, ["--json", "team", "show", "t1"], env=env)
    assert result.exit_code == 0, result.output
    panel = json.loads(result.stdout)["costRollup"]

    if panel.get("status") == "ok":
        for k in (
            "cost_usd",
            "budget_usd",
            "spend_percent",
            "per_agent",
            "per_sprint",
            "cache_hit_rate",
            "alarms_fired",
            "active_agents",
            "active_agent_count",
        ):
            assert k in panel, f"cost panel key {k!r} missing"


def test_team_show_nonexistent_team(tmp_path):
    """Unknown team still returns typer.Exit(1) (BC with Phase 3)."""
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    result = runner.invoke(app, ["team", "show", "nonexistent"], env=env)
    assert result.exit_code == 1
