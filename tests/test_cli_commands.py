from __future__ import annotations

from typer.testing import CliRunner

from clawteam.cli.commands import app
from clawteam.config import ClawTeamConfig, load_config, save_config
from clawteam.team.mailbox import MailboxManager
from clawteam.team.manager import TeamManager
from clawteam.team.models import MessageType
from clawteam.team.routing_policy import DefaultRoutingPolicy, RuntimeEnvelope


def test_config_cli_supports_all_keys_and_bool_values(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    result = runner.invoke(app, ["config", "set", "skip_permissions", "false"], env=env)
    assert result.exit_code == 0
    assert load_config().skip_permissions is False

    result = runner.invoke(app, ["config", "set", "workspace", "never"], env=env)
    assert result.exit_code == 0
    assert load_config().workspace == "never"

    result = runner.invoke(app, ["config", "set", "default_profile", "gemini-main"], env=env)
    assert result.exit_code == 0
    assert load_config().default_profile == "gemini-main"

    result = runner.invoke(app, ["config", "get", "workspace"], env=env)
    assert result.exit_code == 0
    assert "workspace = never" in result.output


def test_team_approve_join_errors_when_request_missing(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        "CLAWTEAM_AGENT_ID": "leader001",
        "CLAWTEAM_AGENT_NAME": "leader",
    }

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    result = runner.invoke(app, ["team", "approve-join", "demo", "missing-req"], env=env)

    assert result.exit_code == 1
    assert "No join request found with id 'missing-req'" in result.output
    assert [member.name for member in TeamManager.list_members("demo")] == ["leader"]


def test_team_request_join_supports_no_wait_mode(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        "CLAWTEAM_AGENT_ID": "worker001",
        "CLAWTEAM_AGENT_NAME": "worker",
    }

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    result = runner.invoke(
        app,
        ["team", "request-join", "demo", "worker", "--no-wait"],
        env=env,
    )

    assert result.exit_code == 0
    assert "Join request sent" in result.output
    assert "join-status demo" in result.output


def test_team_request_join_timeout_returns_pending_instead_of_error(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        "CLAWTEAM_AGENT_ID": "worker001",
        "CLAWTEAM_AGENT_NAME": "worker",
    }

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    result = runner.invoke(
        app,
        ["team", "request-join", "demo", "worker", "--timeout", "0"],
        env=env,
    )

    assert result.exit_code == 0
    assert "Still pending." in result.output
    assert "join-status demo" in result.output


def test_inbox_send_reads_content_from_stdin_when_argument_missing(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        "CLAWTEAM_AGENT_ID": "worker001",
        "CLAWTEAM_AGENT_NAME": "worker",
    }

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    result = runner.invoke(
        app,
        ["inbox", "send", "demo", "leader"],
        env=env,
        input="HELLO FROM STDIN\n",
    )

    assert result.exit_code == 0
    messages = MailboxManager("demo").receive("leader")
    assert len(messages) == 1
    assert messages[0].content == "HELLO FROM STDIN"


def test_lifecycle_should_keepalive_stops_when_shutdown_approved(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )
    TeamManager.add_member("demo", "worker", agent_id="worker001", agent_type="codex")

    mailbox = MailboxManager("demo")
    mailbox.send(
        from_agent="leader",
        to="worker",
        msg_type=MessageType.shutdown_approved,
        request_id="req-1",
        content="worker shutting down.",
    )

    result = runner.invoke(
        app,
        ["lifecycle", "should-keepalive", "--team", "demo", "--agent", "worker"],
        env=env,
    )

    assert result.exit_code == 1



def test_team_join_status_reports_approval(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        "CLAWTEAM_AGENT_ID": "worker001",
        "CLAWTEAM_AGENT_NAME": "worker",
    }

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    mailbox = MailboxManager("demo")
    mailbox.send(
        from_agent="leader",
        to="_pending_worker",
        msg_type=MessageType.join_approved,
        request_id="join-abc123",
        assigned_name="worker",
        agent_id="worker001",
        team_name="demo",
    )

    result = runner.invoke(
        app,
        ["team", "join-status", "demo", "join-abc123", "--proposed-name", "worker"],
        env=env,
    )

    assert result.exit_code == 0
    assert "Approved!" in result.output


def test_task_cli_supports_priority_create_update_and_list(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    create_result = runner.invoke(
        app,
        ["task", "create", "demo", "important work", "--priority", "urgent", "--owner", "alice"],
        env=env,
    )
    assert create_result.exit_code == 0
    assert "Priority: urgent" in create_result.output

    list_result = runner.invoke(
        app,
        ["task", "list", "demo", "--priority", "urgent", "--sort-priority"],
        env=env,
    )
    assert list_result.exit_code == 0
    assert "urgent" in list_result.output
    assert "important work" in list_result.output

    task_id = create_result.output.split("Task created: ")[1].splitlines()[0].strip()
    update_result = runner.invoke(
        app,
        ["task", "update", "demo", task_id, "--priority", "low"],
        env=env,
    )
    assert update_result.exit_code == 0

    get_result = runner.invoke(
        app,
        ["task", "get", "demo", task_id],
        env=env,
    )
    assert get_result.exit_code == 0
    assert "Priority: low" in get_result.output


def test_task_cli_accepts_agent_alias_for_owner(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    create_result = runner.invoke(
        app,
        ["task", "create", "demo", "important work", "--agent", "alice"],
        env=env,
    )
    assert create_result.exit_code == 0
    task_id = create_result.output.split("Task created: ")[1].splitlines()[0].strip()

    update_result = runner.invoke(
        app,
        ["task", "update", "demo", task_id, "--agent", "bob"],
        env=env,
    )
    assert update_result.exit_code == 0

    list_result = runner.invoke(
        app,
        ["task", "list", "demo", "--agent", "bob"],
        env=env,
    )
    assert list_result.exit_code == 0
    assert "important work" in list_result.output


def test_task_cli_rejects_circular_dependencies(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    first = runner.invoke(app, ["task", "create", "demo", "first"], env=env)
    second = runner.invoke(
        app,
        ["task", "create", "demo", "second", "--blocked-by", first.output.split("Task created: ")[1].splitlines()[0].strip()],
        env=env,
    )

    assert first.exit_code == 0
    assert second.exit_code == 0

    first_id = first.output.split("Task created: ")[1].splitlines()[0].strip()
    second_id = second.output.split("Task created: ")[1].splitlines()[0].strip()
    result = runner.invoke(
        app,
        ["task", "update", "demo", first_id, "--add-blocked-by", second_id],
        env=env,
    )

    assert result.exit_code == 1
    assert "cannot contain cycles" in result.output


def test_team_status_uses_configured_timezone(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    save_config(ClawTeamConfig(timezone="Asia/Shanghai"))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    result = runner.invoke(app, ["team", "status", "demo"], env=env)

    assert result.exit_code == 0
    assert "CST" in result.output


def test_runtime_inject_cli_invokes_tmux_backend(monkeypatch, tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    captured = {}

    def fake_inject(self, team, agent_name, envelope):
        captured["team"] = team
        captured["agent"] = agent_name
        captured["envelope"] = envelope
        return True, "ok"

    monkeypatch.setattr("clawteam.spawn.tmux_backend.TmuxBackend.inject_runtime_message", fake_inject)

    result = runner.invoke(
        app,
        [
            "runtime",
            "inject",
            "demo",
            "worker",
            "--source",
            "leader",
            "--summary",
            "Auth module complete.",
            "--evidence",
            "12 tests passed",
            "--recommended-next-action",
            "Begin integration task T5.",
        ],
        env=env,
    )

    assert result.exit_code == 0
    assert captured["team"] == "demo"
    assert captured["agent"] == "worker"
    assert captured["envelope"].summary == "Auth module complete."
    assert captured["envelope"].evidence == ["12 tests passed"]
    assert captured["envelope"].recommended_next_action == "Begin integration task T5."


def test_runtime_state_cli_reports_pending_routes(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    policy = DefaultRoutingPolicy(team_name="demo", throttle_seconds=30)
    first = RuntimeEnvelope(source="leader", target="worker", summary="Initial update")
    first_decision = policy.decide(first)
    policy.record_dispatch_result(first_decision, success=True)
    policy.decide(RuntimeEnvelope(source="leader", target="worker", summary="Second update"))

    result = runner.invoke(app, ["runtime", "state", "demo"], env=env)

    assert result.exit_code == 0
    assert "leader -> worker" in result.output
    assert "pending=1" in result.output


def test_team_add_member_cli_adds_member_directly(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        "CLAWTEAM_AGENT_ID": "leader001",
        "CLAWTEAM_AGENT_NAME": "leader",
    }

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    result = runner.invoke(
        app,
        ["team", "add-member", "demo", "worker", "--agent-type", "coder"],
        env=env,
    )

    assert result.exit_code == 0
    members = TeamManager.list_members("demo")
    assert [member.name for member in members] == ["leader", "worker"]
    assert members[1].agent_type == "coder"


def test_board_update_cli_is_a_compatibility_alias(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    result = runner.invoke(app, ["board", "update", "demo", "--agent", "worker"], env=env)

    assert result.exit_code == 0
    assert "derived automatically" in result.output


def test_lifecycle_check_zombies_reports_clean_state(monkeypatch, tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    monkeypatch.setattr("clawteam.spawn.registry.list_zombie_agents", lambda team, max_hours=2.0: [])

    result = runner.invoke(app, ["lifecycle", "check-zombies", "--team", "demo"], env=env)

    assert result.exit_code == 0
    assert "No zombie agents detected" in result.output


def test_lifecycle_check_zombies_exits_nonzero_when_found(monkeypatch, tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    monkeypatch.setattr(
        "clawteam.spawn.registry.list_zombie_agents",
        lambda team, max_hours=2.0: [
            {
                "agent_name": "worker",
                "pid": 4321,
                "backend": "subprocess",
                "spawned_at": 0.0,
                "running_hours": 3.5,
            }
        ],
    )

    result = runner.invoke(app, ["lifecycle", "check-zombies", "--team", "demo"], env=env)

    assert result.exit_code == 1
    assert "zombie agent(s) detected" in result.output
    assert "worker" in result.output
    assert "process manager" in result.output


def test_runtime_watch_cli_uses_runtime_router(monkeypatch, tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        "CLAWTEAM_USER": "alice",
        "CLAWTEAM_AGENT_ID": "worker001",
        "CLAWTEAM_AGENT_NAME": "worker",
    }
    TeamManager.create_team(
        name="demo",
        leader_name="worker",
        leader_id="worker001",
        user="alice",
    )
    captured = {}

    def fake_watch(self):
        captured["agent"] = self.agent_name
        captured["runtime_router"] = self.runtime_router

    monkeypatch.setattr("clawteam.team.watcher.InboxWatcher.watch", fake_watch)

    result = runner.invoke(app, ["runtime", "watch", "demo"], env=env)

    assert result.exit_code == 0
    assert captured["agent"] == "alice_worker"
    assert captured["runtime_router"] is not None
    assert captured["runtime_router"].agent_name == "worker"


def test_run_cli_auto_creates_team_and_spawns_wrapped_agent(monkeypatch, tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    captured: dict[str, object] = {}

    class FakeBackend:
        def spawn(self, **kwargs):
            captured.update(kwargs)
            return "Agent spawned"

    monkeypatch.setattr("clawteam.spawn.get_backend", lambda name: FakeBackend())

    result = runner.invoke(
        app,
        ["run", "claude", "--team", "demo"],
        env=env,
    )

    assert result.exit_code == 0
    assert "Agent spawned" in result.output

    team = TeamManager.get_team("demo")
    assert team is not None
    assert len(team.members) == 1
    assert team.members[0].name.startswith("claude-")
    assert team.members[0].agent_type == "claude"
    assert team.lead_agent_id == team.members[0].agent_id
    assert captured["team_name"] == "demo"
    assert captured["agent_name"] == team.members[0].name
    assert captured["agent_id"] == team.members[0].agent_id


def test_run_cli_resume_reuses_existing_leader_and_session(monkeypatch, tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    captured: dict[str, object] = {}

    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
        leader_agent_type="claude",
    )

    class FakeBackend:
        def spawn(self, **kwargs):
            captured.update(kwargs)
            return "Agent spawned"

    class FakeSession:
        session_id = "sess-123"

    monkeypatch.setattr("clawteam.spawn.get_backend", lambda name: FakeBackend())
    monkeypatch.setattr(
        "clawteam.spawn.sessions.SessionStore.load",
        lambda self, agent_name: FakeSession() if agent_name == "leader" else None,
    )

    result = runner.invoke(
        app,
        ["run", "claude", "--team", "demo", "--resume"],
        env=env,
    )

    assert result.exit_code == 0
    assert "Resuming session: sess-123" in result.output
    assert captured["agent_name"] == "leader"
    assert captured["agent_id"] == "leader001"
    assert captured["command"] == ["claude", "--resume", "sess-123"]


# ---------------------------------------------------------------------------
# UX-07: `clawteam team show` dashboard (Phase 3 Plan 03-08)
# ---------------------------------------------------------------------------

_GSTACK_ROLES = [
    "pm", "ceo", "eng-mgr", "designer", "dx-lead",
    "engineer", "reviewer", "qa", "security", "shipper", "sre",
]


def _spawn_gstack_team_for_show(name: str = "myteam") -> None:
    """Helper: create a gstack-templated team with all 11 roles as members.

    Mirrors what `clawteam team spawn gstack --name <name>` does so
    `team show` has a realistic roster + template + leader_role on disk.
    """
    TeamManager.create_team(
        name=name,
        leader_name="ceo",
        leader_id="ceo-1",
        description="gstack test team",
        leader_agent_type="strategic-leader",
        roles=_GSTACK_ROLES,
        leader_role="ceo",
        template="gstack",
    )
    # ceo is the leader — add the other 10 specialists.
    for role in _GSTACK_ROLES:
        if role == "ceo":
            continue
        TeamManager.add_member(
            team_name=name,
            member_name=role,
            agent_id=f"{role}-1",
            agent_type="general-purpose",
        )


def test_team_show_gstack_dashboard_renders_11_roles_and_placeholders(tmp_path):
    """UX-07 happy path: gstack team surfaces 11 roles + Phase 6/7 placeholders."""
    runner = CliRunner()
    data_dir = tmp_path / ".clawteam"
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(data_dir),
    }

    _spawn_gstack_team_for_show("myteam")

    # Drop 2 `_phase6_pending/` placeholder files so the dashboard
    # memory row reports a non-zero count.
    pending = data_dir / "teams" / "myteam" / "_phase6_pending"
    pending.mkdir(parents=True)
    (pending / "sprint-001-retro.json").write_text(
        '{"feature_flag":"phase6_learn_pending"}'
    )
    (pending / "sprint-002-retro.json").write_text(
        '{"feature_flag":"phase6_learn_pending"}'
    )

    result = runner.invoke(app, ["team", "show", "myteam"], env=env)

    assert result.exit_code == 0, result.output
    # Header carries the template + leader chip.
    assert "Template:" in result.output
    assert "gstack" in result.output
    assert "leader:" in result.output
    assert "ceo" in result.output
    # All 11 gstack roles appear in the rendered roster.
    for role in _GSTACK_ROLES:
        assert role in result.output, f"role {role!r} missing from dashboard"
    # Memory placeholder: Phase 6 pending + count of 2.
    assert "Phase 6 pending" in result.output
    assert "2 entries" in result.output
    # Cost rollup panel (Phase 7 Plan 07-07): the old "pending Phase 7"
    # placeholder text is replaced by the live "Cost:" one-liner from
    # clawteam.cost.dashboard.render_text. Either variant of the panel is
    # acceptable depending on whether the cost substrate loads cleanly.
    assert ("Cost:" in result.output) or (
        "Cost: [dim]unavailable" in result.output
    )


def test_team_show_not_found_returns_exit_code_1(tmp_path):
    """Unknown team name returns typer.Exit(1) with human-readable error."""
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    result = runner.invoke(app, ["team", "show", "nonexistent"], env=env)

    assert result.exit_code == 1
    assert "not found" in result.output.lower()
    assert "nonexistent" in result.output


def test_team_show_non_gstack_team_shows_na_memory_row(tmp_path):
    """Non-gstack template renders roster; memory row shows N/A (CORE-03 BC)."""
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    # Create a non-gstack team: template="software-dev" triggers the N/A path.
    TeamManager.create_team(
        name="legacy-team",
        leader_name="lead",
        leader_id="lead-1",
        description="software-dev team",
        leader_agent_type="leader",
        roles=["lead", "eng"],
        leader_role="",
        template="software-dev",
    )
    TeamManager.add_member(
        team_name="legacy-team",
        member_name="eng",
        agent_id="eng-1",
        agent_type="general-purpose",
    )

    result = runner.invoke(app, ["team", "show", "legacy-team"], env=env)

    assert result.exit_code == 0, result.output
    assert "software-dev" in result.output
    # Memory row shows N/A for non-gstack templates.
    assert "N/A" in result.output
    # No gstack-specific placeholder chatter leaks into the output.
    assert "_phase6_pending" not in result.output
    assert "Phase 6 pending" not in result.output


def test_team_show_json_output_shape_matches_contract(tmp_path):
    """--json output shape: all documented keys present with correct statuses."""
    import json as _json

    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    _spawn_gstack_team_for_show("json-team")

    result = runner.invoke(app, ["--json", "team", "show", "json-team"], env=env)

    assert result.exit_code == 0, result.output
    # --json prints the whole dict as one JSON document; parse the full body.
    data = _json.loads(result.output)

    assert data["name"] == "json-team"
    assert data["template"] == "gstack"
    assert data["leaderRole"] == "ceo"
    assert isinstance(data["members"], list)
    assert len(data["members"]) == 11  # ceo + 10 specialists
    assert "activeSprint" in data  # None is OK — no sprint started
    assert data["memory"]["status"] == "pending_phase_6"
    assert data["memory"]["placeholderEntries"] == 0
    # Phase 7 Plan 07-07: the "pending_phase_7" placeholder is replaced by
    # a live dashboard dict from clawteam.cost.dashboard.render_team. Status
    # is "ok" on live render or "unavailable" on best-effort fallback;
    # either satisfies the contract that the placeholder is gone.
    cost_panel = data["costRollup"]
    assert cost_panel["status"] in {"ok", "unavailable"}
    assert cost_panel["status"] != "pending_phase_7"
    # Live dashboard dict keys replace the old perAgent/totalTokens/totalUsd
    # triple; new shape is cost_usd / per_agent / per_sprint / etc.
    assert "cost_usd" in cost_panel
    assert "per_agent" in cost_panel
    assert "active_agents" in cost_panel
