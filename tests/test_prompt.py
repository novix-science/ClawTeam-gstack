"""Tests for clawteam.spawn.prompt — build_agent_prompt."""

from clawteam.spawn.prompt import build_agent_prompt


class TestBuildAgentPrompt:
    def test_basic_prompt_contains_identity(self):
        prompt = build_agent_prompt(
            agent_name="worker-1",
            agent_id="abc123",
            agent_type="coder",
            team_name="alpha",
            leader_name="leader",
            task="Implement feature X",
        )
        assert "worker-1" in prompt
        assert "abc123" in prompt
        assert "coder" in prompt
        assert "alpha" in prompt
        assert "leader" in prompt
        assert "Implement feature X" in prompt

    def test_prompt_contains_coordination_protocol(self):
        prompt = build_agent_prompt(
            agent_name="w", agent_id="id", agent_type="t",
            team_name="team", leader_name="lead", task="do stuff",
        )
        # Event-driven wake protocol (replaces the old polling loop).
        assert "[wake:task]" in prompt
        assert "[wake:inbox]" in prompt
        assert "Do **NOT**" in prompt or "do NOT" in prompt.lower()
        assert "clawteam task list" in prompt
        assert "clawteam task update" in prompt
        assert "git add -A && git commit" in prompt
        assert "clawteam inbox send" in prompt
        # Dead code paths removed post-v1.0 UAT 2026-04-22.
        assert "clawteam cost report" not in prompt
        assert "clawteam session save" not in prompt

    def test_prompt_includes_user_when_provided(self):
        prompt = build_agent_prompt(
            agent_name="w", agent_id="id", agent_type="t",
            team_name="team", leader_name="lead", task="task",
            user="alice",
        )
        assert "alice" in prompt

    def test_prompt_excludes_user_when_empty(self):
        prompt = build_agent_prompt(
            agent_name="w", agent_id="id", agent_type="t",
            team_name="team", leader_name="lead", task="task",
            user="",
        )
        assert "User:" not in prompt

    def test_prompt_includes_workspace_when_provided(self):
        prompt = build_agent_prompt(
            agent_name="w", agent_id="id", agent_type="t",
            team_name="team", leader_name="lead", task="task",
            workspace_dir="/tmp/ws", workspace_branch="feature-x",
            isolated_workspace=True,
        )
        assert "/tmp/ws" in prompt
        assert "feature-x" in prompt
        assert "Workspace" in prompt
        assert "isolated git worktree" in prompt

    def test_prompt_for_plain_repo_path_is_not_described_as_worktree(self):
        prompt = build_agent_prompt(
            agent_name="w", agent_id="id", agent_type="t",
            team_name="team", leader_name="lead", task="task",
            workspace_dir="/tmp/repo",
            isolated_workspace=False,
        )
        assert "/tmp/repo" in prompt
        assert "Work directly in this repository path" in prompt
        assert "isolated git worktree" not in prompt
        assert "Branch:" not in prompt

    def test_prompt_excludes_workspace_when_empty(self):
        prompt = build_agent_prompt(
            agent_name="w", agent_id="id", agent_type="t",
            team_name="team", leader_name="lead", task="task",
            workspace_dir="",
        )
        assert "Workspace" not in prompt

    def test_prompt_uses_team_and_leader_in_commands(self):
        prompt = build_agent_prompt(
            agent_name="dev", agent_id="id", agent_type="t",
            team_name="my-team", leader_name="boss", task="task",
        )
        assert "clawteam task list my-team --owner dev" in prompt
        assert "clawteam inbox send my-team boss" in prompt
        # `clawteam cost report` removed post-v1.0 UAT 2026-04-22.
        assert "clawteam cost report" not in prompt
        assert "commit" in prompt.lower()

    def test_prompt_describes_event_driven_wake_protocol(self):
        """Replaces the old Worker Loop Protocol test: event-driven, not polling."""
        prompt = build_agent_prompt(
            agent_name="dev", agent_id="id", agent_type="t",
            team_name="my-team", leader_name="boss", task="task",
        )
        # Wake notifications describe how work arrives.
        assert "[wake:task]" in prompt
        assert "[wake:inbox]" in prompt
        # Explicit "don't poll" guidance.
        assert "do NOT" in prompt or "Do **NOT**" in prompt
        # Commands still referenced for when agent reacts to a wake.
        assert "clawteam task list my-team --owner dev" in prompt
        assert "clawteam inbox receive my-team --agent dev" in prompt
        # Idle-between-wakes guidance.
        assert "clawteam lifecycle idle" in prompt
        assert "clawteam lifecycle idle my-team" in prompt
