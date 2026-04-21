"""End-to-end `clawteam team spawn gstack --name <n>` integration tests.

Covers:

- **TEAM-03**: spawning a gstack team materializes 11 specialist members with
  per-role memory dirs pre-created at `<data_dir>/teams/<team>/memory/<role>/`
  (D-05 race-free pre-creation for Phase 6 `/learn` writes).
- **UX-01**: `clawteam team spawn gstack --name <n>` drives the full CLI
  pipeline end-to-end: template load -> TeamManager.create_team ->
  add_member x 10 -> TeamConfig persisted with `template="gstack"` +
  `leader_role="ceo"` -> `clawteam team show <n>` dashboard renders with
  all 11 roles.

Scope boundary: per-agent git-worktree creation belongs to `clawteam launch`
(which optionally calls WorkspaceManager.create_workspace under `--workspace`).
`team spawn` handles team/config/memory setup only. These tests anchor the
`team spawn` contract, not the `launch` workspace path (which is separately
covered by tests/test_template_regression_matrix.py::test_template_launches_cleanly
across all 7 templates). This matches the Phase 3 Plan 03-02 "team spawn vs
launch" boundary decision (see `.planning/phases/03.../03-02-*-SUMMARY.md`).
"""

from __future__ import annotations

from typer.testing import CliRunner


GSTACK_EXPECTED_ROLES = {
    "pm", "ceo", "eng-mgr", "designer", "dx-lead",
    "engineer", "reviewer", "qa", "security", "shipper", "sre",
}


def test_eleven_worktrees_created(isolated_data_dir):
    """TEAM-03: spawning a gstack team materializes 11 specialist desks.

    Each desk = (team member + per-role memory dir) pre-created at spawn time.
    The 03-02 TeamManager.create_team extension (D-05) pre-creates the memory
    subtree idempotently; the team_spawn Typer command adds the 10 specialists
    on top of the leader via TeamManager.add_member. This test anchors both
    halves.

    Named `test_eleven_worktrees_created` per Wave-0 scaffold (03-01) contract;
    the term "worktree" here refers to the logical per-agent workspace (config
    member + memory dir), not the git-worktree flavor that `clawteam launch
    --workspace` materializes. See the module docstring for the scope boundary.
    """
    from clawteam.cli.commands import app
    from clawteam.team.manager import TeamManager
    from clawteam.templates import load_template

    # gstack.toml declares 11 = 1 leader + 10 specialists (verified in
    # 03-02's tests/test_gstack_template.py::test_eleven_agents_with_distinct_roles).
    gstack_template = load_template("gstack")
    assert gstack_template.name == "gstack"
    assert 1 + len(gstack_template.agents) == 11, (
        f"gstack.toml must declare 11 total agents (1 leader + 10), got "
        f"{1 + len(gstack_template.agents)}"
    )

    # Drive the CLI: `clawteam team spawn gstack --name spawn-test`. This is
    # the exact UX-01 surface a user runs.
    runner = CliRunner()
    result = runner.invoke(
        app, ["team", "spawn", "gstack", "--name", "spawn-test"]
    )
    assert result.exit_code == 0, (
        f"team spawn gstack failed:\n"
        f"  exit={result.exit_code}\n"
        f"  stdout={result.output}\n"
        f"  exception={result.exception!r}"
    )

    # 1. All 11 role names appear as team members (leader + 10 specialists
    #    added via team_spawn's add_member loop — see 03-02 Rule-2 deviation).
    team_config = TeamManager.get_team("spawn-test")
    assert team_config is not None, "team config not persisted after spawn"
    member_names = {m.name for m in team_config.members}
    missing = GSTACK_EXPECTED_ROLES - member_names
    extra = member_names - GSTACK_EXPECTED_ROLES
    assert not missing, f"missing specialist members: {missing}"
    assert not extra, f"unexpected members beyond 11 gstack roles: {extra}"
    assert len(team_config.members) == 11, (
        f"expected 11 members, got {len(team_config.members)}"
    )

    # 2. Per-role memory dirs pre-created (D-05 + 03-02): one per role under
    #    `<data_dir>/teams/spawn-test/memory/<role>/`. This is the concrete
    #    per-agent "desk" on disk — separate from each member's inbox dir.
    memory_root = isolated_data_dir / "teams" / "spawn-test" / "memory"
    assert memory_root.is_dir(), (
        f"memory root not pre-created by TeamManager.create_team (D-05): "
        f"{memory_root}"
    )
    actual_role_dirs = {p.name for p in memory_root.iterdir() if p.is_dir()}
    missing_dirs = GSTACK_EXPECTED_ROLES - actual_role_dirs
    extra_dirs = actual_role_dirs - GSTACK_EXPECTED_ROLES
    assert not missing_dirs, (
        f"D-05 violation: missing per-role memory dirs: {missing_dirs}"
    )
    assert not extra_dirs, (
        f"D-05 violation: unexpected extra memory dirs: {extra_dirs}"
    )

    # 3. TeamConfig round-trips the 03-01 + 03-02 fields (template + leader_role)
    #    which downstream consumers (SprintConductor.advance_phase actor check;
    #    GstackSprintPlugin._on_phase_transition cross-template guard) rely on.
    assert getattr(team_config, "template", "") == "gstack", (
        f"TeamConfig.template should be 'gstack' after gstack spawn, got "
        f"{getattr(team_config, 'template', None)!r}"
    )
    assert getattr(team_config, "leader_role", "") == "ceo", (
        f"TeamConfig.leader_role should be 'ceo' after gstack spawn, got "
        f"{getattr(team_config, 'leader_role', None)!r}"
    )


def test_team_spawn_gstack(isolated_data_dir):
    """UX-01 + success-criterion #1: `clawteam team spawn gstack --name <n>`
    works end-to-end. Exit 0; stdout carries user-facing signal; downstream
    `clawteam team show` (shipped by 03-08) renders the dashboard with all
    11 roles.

    This is the positive half of the Phase 3 meta-claim "the product ships".
    The negative half ("nothing else breaks") is covered by
    tests/test_template_regression_matrix.py's cross-template isolation suite.
    """
    from clawteam.cli.commands import app
    from clawteam.team.manager import TeamManager

    runner = CliRunner()

    # Part A: spawn via the UX-01 CLI surface.
    spawn_result = runner.invoke(
        app, ["team", "spawn", "gstack", "--name", "gstack-e2e"]
    )
    assert spawn_result.exit_code == 0, (
        f"team spawn gstack failed:\n"
        f"  exit={spawn_result.exit_code}\n"
        f"  stdout={spawn_result.output}\n"
        f"  exception={spawn_result.exception!r}"
    )

    # User-facing success signal: team name + template name + agent count
    # surface in the human output stream (from team_spawn's _human renderer).
    assert "gstack-e2e" in spawn_result.output, (
        f"team name missing from spawn output:\n{spawn_result.output}"
    )
    assert "gstack" in spawn_result.output, (
        f"template name missing from spawn output:\n{spawn_result.output}"
    )
    assert "11" in spawn_result.output, (
        f"11-agent count missing from spawn output:\n{spawn_result.output}"
    )

    # Part B: all 11 per-role memory dirs on disk (redundant with Task 1
    # but covers the CLI-driven path end-to-end).
    memory_root = isolated_data_dir / "teams" / "gstack-e2e" / "memory"
    assert memory_root.is_dir(), (
        f"memory root missing after CLI spawn: {memory_root}"
    )
    role_dirs = {p.name for p in memory_root.iterdir() if p.is_dir()}
    assert role_dirs == GSTACK_EXPECTED_ROLES, (
        f"expected 11 gstack role memory dirs, got {role_dirs}"
    )

    # Part C: TeamConfig persists with template + leader_role + 11 members.
    cfg = TeamManager.get_team("gstack-e2e")
    assert cfg is not None
    assert len(cfg.members) == 11
    assert cfg.template == "gstack"
    assert cfg.leader_role == "ceo"

    # Part D: `clawteam team show gstack-e2e` (03-08 dashboard) renders all
    # 11 roles + the gstack template chip. This anchors the end-to-end
    # integration from CLI spawn -> TeamConfig -> dashboard render.
    show_result = runner.invoke(app, ["team", "show", "gstack-e2e"])
    assert show_result.exit_code == 0, (
        f"team show failed after spawn:\n"
        f"  exit={show_result.exit_code}\n"
        f"  stdout={show_result.output}\n"
        f"  exception={show_result.exception!r}"
    )
    assert "gstack" in show_result.output, (
        f"template name 'gstack' missing from dashboard:\n{show_result.output}"
    )
    # All 11 role names appear in the dashboard's Members table.
    for role in GSTACK_EXPECTED_ROLES:
        assert role in show_result.output, (
            f"role {role!r} missing from dashboard:\n{show_result.output}"
        )


def test_per_role_memory_dirs_precreated(isolated_data_dir):
    """D-05: 11 per-role memory dirs exist at
    ``<data_dir>/teams/<name>/memory/<role>/`` after `team spawn gstack`.

    Idempotent: re-running spawn against the same team name errors ("already
    exists") without creating duplicate memory entries or crashing. This
    guarantees Phase 6 /learn writes land in a deterministic pre-existing
    directory tree even under concurrent sprints.
    """
    from clawteam.cli.commands import app

    runner = CliRunner()

    # First spawn: creates the full memory tree.
    result = runner.invoke(
        app, ["team", "spawn", "gstack", "--name", "idempot-team"]
    )
    assert result.exit_code == 0, result.output

    memory_root = isolated_data_dir / "teams" / "idempot-team" / "memory"
    assert memory_root.is_dir()
    role_dirs = {p.name for p in memory_root.iterdir() if p.is_dir()}
    assert role_dirs == GSTACK_EXPECTED_ROLES

    # Second spawn against the same name: team_spawn should reject with
    # exit != 0 and a clear "already exists" error (TeamManager.create_team
    # raises ValueError; team_spawn maps this to typer.Exit(1)). The
    # pre-existing memory dirs must NOT be deleted or corrupted.
    result2 = runner.invoke(
        app, ["team", "spawn", "gstack", "--name", "idempot-team"]
    )
    assert result2.exit_code != 0, (
        f"team spawn should reject duplicate name, got exit=0:\n{result2.output}"
    )

    # Memory tree preserved — idempotent guarantee.
    role_dirs_after = {p.name for p in memory_root.iterdir() if p.is_dir()}
    assert role_dirs_after == GSTACK_EXPECTED_ROLES, (
        f"duplicate spawn corrupted memory tree: {role_dirs_after}"
    )
