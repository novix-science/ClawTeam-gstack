"""Phase 3 Plan 03-02 Task 3 - per-role memory dir pre-creation (D-05) +
new `clawteam team spawn` Typer subcommand (UX-01).

Verifies TeamManager.create_team accepts `roles=`, `leader_role=`, and
`template=` kwargs, persists them on TeamConfig, and pre-creates per-role
memory directories idempotently under `~/.clawteam/teams/<team>/memory/<role>/`.
Also covers the new Typer `team spawn <template> --name <n>` subcommand.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app
from clawteam.team.manager import TeamManager
from clawteam.team.models import get_data_dir


class TestCreateTeamMemoryDirs:
    def test_backward_compat_no_roles_kwarg(self, team_name):
        """Existing call sites (no `roles=`) still succeed - empty-default loop is a no-op."""
        cfg = TeamManager.create_team(
            name=team_name,
            leader_name="lead",
            leader_id="abc123",
        )
        assert cfg.name == team_name
        # No memory subdirs should be created when roles kwarg is omitted:
        memory_root = get_data_dir() / "teams" / team_name / "memory"
        # The directory itself may or may not exist; the key invariant is no
        # per-role children were created:
        if memory_root.exists():
            assert list(memory_root.iterdir()) == []

    def test_empty_roles_is_noop(self, team_name):
        cfg = TeamManager.create_team(
            name=team_name,
            leader_name="lead",
            leader_id="x",
            roles=[],
        )
        assert cfg.name == team_name
        memory_root = get_data_dir() / "teams" / team_name / "memory"
        if memory_root.exists():
            assert list(memory_root.iterdir()) == []

    def test_creates_per_role_memory_dirs(self, team_name):
        TeamManager.create_team(
            name=team_name,
            leader_name="lead",
            leader_id="x",
            roles=["pm", "ceo", "engineer"],
        )
        memory_root = get_data_dir() / "teams" / team_name / "memory"
        assert (memory_root / "pm").is_dir()
        assert (memory_root / "ceo").is_dir()
        assert (memory_root / "engineer").is_dir()

    def test_mkdir_is_idempotent(self, team_name):
        """Pre-populating one role dir then calling create_team with roles= must succeed."""
        memory_root = get_data_dir() / "teams" / team_name / "memory"
        # Pre-create one dir so create_team's mkdir has a collision to absorb:
        (memory_root / "pm").mkdir(parents=True, exist_ok=True)
        TeamManager.create_team(
            name=team_name,
            leader_name="lead",
            leader_id="x",
            roles=["pm", "ceo"],
        )
        assert (memory_root / "pm").is_dir()
        assert (memory_root / "ceo").is_dir()

    def test_path_traversal_rejected(self, team_name):
        """validate_identifier must reject `..` in role names before mkdir runs."""
        with pytest.raises(ValueError):
            TeamManager.create_team(
                name=team_name,
                leader_name="lead",
                leader_id="x",
                roles=["../etc/passwd"],
            )

    def test_persists_leader_role_and_template(self, team_name):
        TeamManager.create_team(
            name=team_name,
            leader_name="ceo",
            leader_id="leader-id-1",
            leader_role="ceo",
            template="gstack",
        )
        cfg = TeamManager.get_team(team_name)
        assert cfg is not None
        assert cfg.leader_role == "ceo"
        assert cfg.template == "gstack"


class TestTeamSpawnCommand:
    """UX-01: `clawteam team spawn gstack --name <n>` creates 11 memory dirs."""

    def test_spawn_gstack_creates_eleven_memory_dirs(self):
        runner = CliRunner()
        result = runner.invoke(app, ["team", "spawn", "gstack", "--name", "acme"])
        assert result.exit_code == 0, result.output
        memory_root = get_data_dir() / "teams" / "acme" / "memory"
        expected_roles = {
            "ceo", "pm", "eng-mgr", "designer", "dx-lead", "engineer",
            "reviewer", "qa", "security", "shipper", "sre",
        }
        for role in expected_roles:
            assert (memory_root / role).is_dir(), f"missing {role} memory dir"

    def test_spawn_gstack_persists_template_and_leader_role(self):
        runner = CliRunner()
        result = runner.invoke(app, ["team", "spawn", "gstack", "--name", "acme2"])
        assert result.exit_code == 0, result.output
        cfg = TeamManager.get_team("acme2")
        assert cfg is not None
        assert cfg.template == "gstack"
        assert cfg.leader_role == "ceo"

    def test_spawn_help_exposes_ux01_form(self):
        runner = CliRunner()
        result = runner.invoke(app, ["team", "spawn", "--help"])
        assert result.exit_code == 0
        # UX-01 positional + option names must appear:
        assert "template" in result.output.lower()
        assert "--name" in result.output

    def test_spawn_unknown_template_errors(self):
        runner = CliRunner()
        result = runner.invoke(app, ["team", "spawn", "nonexistent-xyz", "--name", "t"])
        assert result.exit_code == 1


class TestLaunchPassesRolesForGstack:
    """Existing `clawteam launch gstack` flow now routes roles into create_team."""

    def test_launch_gstack_creates_memory_dirs(self, monkeypatch, tmp_path):
        """End-to-end: `clawteam launch gstack --team <n>` creates 11 memory dirs."""

        class RecordingBackend:
            def __init__(self):
                self.calls = []

            def spawn(self, **kwargs):
                self.calls.append(kwargs)
                return f"Agent {kwargs['agent_name']} spawned"

            def list_running(self):
                return []

        backend = RecordingBackend()
        monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

        runner = CliRunner()
        result = runner.invoke(app, ["launch", "gstack", "--team", "launch-gstack-t"])
        assert result.exit_code == 0, result.output

        memory_root = get_data_dir() / "teams" / "launch-gstack-t" / "memory"
        for role in ["ceo", "pm", "engineer", "shipper", "sre"]:
            assert (memory_root / role).is_dir(), f"missing {role}"

        cfg = TeamManager.get_team("launch-gstack-t")
        assert cfg.template == "gstack"
        assert cfg.leader_role == "ceo"

    def test_launch_existing_template_unchanged(self, monkeypatch, tmp_path):
        """Existing templates (no role field on agents) produce no memory subdirs."""

        class RecordingBackend:
            def __init__(self):
                self.calls = []

            def spawn(self, **kwargs):
                self.calls.append(kwargs)
                return f"Agent {kwargs['agent_name']} spawned"

            def list_running(self):
                return []

        backend = RecordingBackend()
        monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

        runner = CliRunner()
        result = runner.invoke(
            app, ["launch", "software-dev", "--team", "bc-sd-t", "--goal", "x"]
        )
        assert result.exit_code == 0, result.output
        memory_root = get_data_dir() / "teams" / "bc-sd-t" / "memory"
        # Memory root should not exist, or if it does, it must be empty
        # (software-dev.toml declares no `role` on agents).
        if memory_root.exists():
            assert list(memory_root.iterdir()) == []
        cfg = TeamManager.get_team("bc-sd-t")
        assert cfg.template == ""  # existing templates don't pass template= yet
        assert cfg.leader_role == ""
