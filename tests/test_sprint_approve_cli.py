"""Tests for `clawteam sprint approve` CLI subcommand (Plan 04-12 — SPRINT-05)."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def setup_team_and_sprint(tmp_path, monkeypatch):
    """Create a team + sprint in isolated data dir; return (team, sprint_id)."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    from clawteam.sprint.state import SprintState, save_sprint_state

    # Create team directory structure mimicking clawteam team spawn output.
    team_dir = tmp_path / "teams" / "t1"
    team_dir.mkdir(parents=True)
    (team_dir / "config.json").write_text(
        json.dumps(
            {
                "name": "t1",
                "template": "gstack",
                "leader": "ceo",
                "members": [],
            }
        )
    )

    state = SprintState(
        team="t1",
        sprint_id="abc12345",
        goal="g",
        current_phase="ship",
        workspace_branch=str(tmp_path),
        review_sha="a1b2c3d4e5f6" + "0" * 28,
    )
    save_sprint_state(state)
    return ("t1", state.sprint_id)


def test_approve_writes_frontmatter(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team])
    assert result.exit_code == 0, result.output

    from clawteam.sprint.state import load_sprint_state

    loaded = load_sprint_state(team, sid)
    approval = loaded.artifacts.get("ship-approval.md", "")
    assert "artifact_type: ship_approval" in approval
    assert "approved_by:" in approval
    assert "approved_at:" in approval
    assert "sha_at_approval:" in approval


def test_approve_uses_state_review_sha(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team])
    assert result.exit_code == 0

    from clawteam.sprint.state import load_sprint_state

    loaded = load_sprint_state(team, sid)
    approval = loaded.artifacts["ship-approval.md"]
    assert "a1b2c3d4e5f6" in approval  # state.review_sha prefix


def test_approve_json_mode_prints_frontmatter(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(
        app, ["sprint", "approve", sid, "--team", team, "--json"]
    )
    assert result.exit_code == 0
    # stdout contains JSON with required fields
    # (other output may follow; find a JSON object containing status=approved).
    found = False
    for line in result.output.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            if data.get("status") == "approved":
                assert "approved_by" in data
                assert "approved_at" in data
                assert "sha_at_approval" in data
                found = True
                break
    assert found, f"No JSON envelope in output: {result.output!r}"


def test_approve_no_sign_flag_accepted(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(
        app, ["sprint", "approve", sid, "--team", team, "--no-sign"]
    )
    assert result.exit_code == 0

    from clawteam.sprint.state import load_sprint_state

    loaded = load_sprint_state(team, sid)
    assert "ship-approval.md" in loaded.artifacts


def test_approve_with_notes_flag(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(
        app,
        [
            "sprint",
            "approve",
            sid,
            "--team",
            team,
            "--notes",
            "LGTM by QA on 2026-04-21",
        ],
    )
    assert result.exit_code == 0

    from clawteam.sprint.state import load_sprint_state

    loaded = load_sprint_state(team, sid)
    approval = loaded.artifacts["ship-approval.md"]
    assert "approval_notes:" in approval
    assert "LGTM by QA" in approval


def test_approve_unsupported_phase_exits_nonzero(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(
        app,
        ["sprint", "approve", sid, "--team", team, "--phase", "build"],
    )
    assert result.exit_code != 0


def test_approve_sprint_not_found_exits_error(tmp_path, runner, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    team_dir = tmp_path / "teams" / "t1"
    team_dir.mkdir(parents=True)
    (team_dir / "config.json").write_text(
        json.dumps(
            {
                "name": "t1",
                "template": "gstack",
                "leader": "ceo",
                "members": [],
            }
        )
    )

    from clawteam.cli.commands import app

    result = runner.invoke(
        app, ["sprint", "approve", "nonexistent", "--team", "t1"]
    )
    assert result.exit_code != 0 or "not found" in (result.output or "").lower()


def test_approve_updates_artifact_on_second_run(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    r1 = runner.invoke(
        app, ["sprint", "approve", sid, "--team", team, "--notes", "first"]
    )
    assert r1.exit_code == 0
    from clawteam.sprint.state import load_sprint_state

    first = load_sprint_state(team, sid).artifacts["ship-approval.md"]

    # Second run updates the artifact.
    r2 = runner.invoke(
        app, ["sprint", "approve", sid, "--team", team, "--notes", "second"]
    )
    assert r2.exit_code == 0
    second = load_sprint_state(team, sid).artifacts["ship-approval.md"]

    # Body changed (notes content differs) but required fields still present.
    assert first != second
    assert "artifact_type: ship_approval" in second
    assert "second" in second


def test_approve_writes_sprint_id_in_frontmatter(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team])
    assert result.exit_code == 0

    from clawteam.sprint.state import load_sprint_state

    loaded = load_sprint_state(team, sid)
    approval = loaded.artifacts["ship-approval.md"]
    assert f"sprint_id: {sid}" in approval


def test_approval_artifact_passes_ship_approval_gate(
    setup_team_and_sprint, runner
):
    """End-to-end: written artifact satisfies ShipApprovalGate."""
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team])
    assert result.exit_code == 0

    from clawteam.harness.ship_approval_gate import ShipApprovalGate
    from clawteam.sprint.state import load_sprint_state

    state = load_sprint_state(team, sid)
    gate = ShipApprovalGate()
    ok, reason = gate.check(state)
    assert ok is True, f"Gate rejected: {reason}"
