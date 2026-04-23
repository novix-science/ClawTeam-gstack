"""Agent prompt builder — identity + task + context awareness.

Coordination knowledge (how to use the clawteam CLI) is provided
by the ClawTeam Skill, not duplicated here.
"""

from __future__ import annotations


def _build_context_block(team_name: str, agent_name: str, repo: str | None = None) -> str:
    """Build a context awareness block from the workspace context layer.

    Includes recent changes from teammates, file overlap warnings,
    and upstream dependency context. Returns empty string if context
    layer is unavailable or no relevant context exists.
    """
    try:
        from clawteam.workspace.context import inject_context
        ctx = inject_context(team_name, agent_name, repo)
        if ctx and "No cross-agent context" not in ctx:
            return ctx
    except Exception:
        pass
    return ""


def build_agent_prompt(
    agent_name: str,
    agent_id: str,
    agent_type: str,
    team_name: str,
    leader_name: str,
    task: str,
    user: str = "",
    workspace_dir: str = "",
    workspace_branch: str = "",
    isolated_workspace: bool = False,
    repo_path: str | None = None,
) -> str:
    """Build agent prompt: identity + task + context + coordination."""
    lines = [
        "## Identity\n",
        f"- Name: {agent_name}",
        f"- ID: {agent_id}",
    ]
    if user:
        lines.append(f"- User: {user}")
    lines.extend([
        f"- Type: {agent_type}",
        f"- Team: {team_name}",
        f"- Leader: {leader_name}",
    ])
    if workspace_dir:
        lines.extend([
            "",
            "## Workspace",
            f"- Working directory: {workspace_dir}",
        ])
        if isolated_workspace:
            lines.extend([
                f"- Branch: {workspace_branch}",
                "- This is an isolated git worktree. Your changes do not affect the main branch.",
            ])
        else:
            lines.append("- Work directly in this repository path unless told otherwise.")

    lines.extend([
        "",
        "## Task\n",
        task,
    ])

    # Inject cross-agent context awareness
    context_block = _build_context_block(team_name, agent_name, repo_path)
    if context_block:
        lines.extend([
            "",
            "## Context\n",
            context_block,
        ])

    lines.extend([
        "",
        "## Coordination Protocol (event-driven — do NOT poll)\n",
        "Work arrives via tmux-injected wake notifications:",
        "",
        "  - `[wake:task] New task assigned: ...`  → pull with `clawteam task "
        f"list {team_name} --owner {agent_name}`",
        "  - `[wake:inbox] New message ...`        → pull with `clawteam "
        f"inbox receive {team_name} --agent {agent_name}`",
        "  - `[nudge] Reminder: ...`               → your role/skill reminder",
        "",
        "Do **NOT** run `task list` or `inbox receive` speculatively in a "
        "loop — wait for a wake. The system pushes to you, you don't pull.",
        "",
        "When you pick up a task:",
        f"  - Start: `clawteam task update {team_name} <task-id> --status in_progress`",
        "  - Commit changes with git before marking completed",
        '  - `git add -A && git commit -m "Implement <task summary>"`',
        f"  - Finish: `clawteam task update {team_name} <task-id> --status completed`",
        "",
        "When you finish or are blocked, message the leader:",
        f'  - Done: `clawteam inbox send {team_name} {leader_name} "All tasks completed. <brief>"`',
        f'  - Blocked: `clawteam inbox send {team_name} {leader_name} "Need help: <desc>"`',
        "",
        "After acting on a wake, wait silently for the next wake. "
        "Don't exit the process — the harness keeps you alive for the "
        "next turn. Don't announce idleness — leader doesn't need it "
        "(the push-based wake system doesn't route by idle status).",
        "",
    ])
    return "\n".join(lines)
