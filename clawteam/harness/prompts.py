"""Harness-aware prompt construction for wrapped agents."""

from __future__ import annotations


def build_harness_system_prompt(team: str, agent_name: str) -> str:
    """Build a system prompt that gives an agent harness capabilities.

    This is injected via --append-system-prompt when using `clawteam run` or
    `clawteam harness`, so the agent automatically knows how to coordinate.
    """
    return f"""\
## ClawTeam Runtime (event-driven)

You are running inside ClawTeam, an agent orchestration framework.
Your identity: **{agent_name}** in team **{team}**.

### How work reaches you
You receive tmux-injected wake notifications as user messages:
- `[wake:task] New task assigned: "<subject>"` — pull with
  `clawteam task list {team} --owner {agent_name}`
- `[wake:inbox] New message. Preview: "<snippet>"` — pull with
  `clawteam inbox receive {team} --agent {agent_name}`
- `[nudge] Reminder: ...` — periodic role/skill reminder when idle

**Do not poll.** Do NOT loop `task list` / `inbox receive` speculatively.
The system pushes; you wait. Polling wastes API calls and adds latency.

### Available Commands (use when reacting to a wake)
- `clawteam task update {team} <id> --status in_progress|completed`
- `clawteam inbox send {team} <to> "<message>"` — message a teammate
- `clawteam workspace checkpoint {team}` — commit WIP
- `clawteam lifecycle idle {team}` — signal you've processed the current wake

### Protocol
1. Wait for a wake (task / inbox / nudge).
2. On wake, fetch details via the matching `clawteam` command.
3. Update task status → do the work → commit with git → mark completed.
4. Notify leader if done or blocked: `clawteam inbox send {team} <leader> "..."`
5. Signal `clawteam lifecycle idle {team}` and wait for the next wake.
6. The harness keeps you alive across wakes — don't exit.
"""


def build_wrapped_prompt(
    agent_name: str,
    goal: str,
    team: str,
) -> str:
    """Build the initial user prompt for a wrapped agent."""
    if not goal:
        return ""
    return f"""\
## Your Task

{goal}

---
You are agent **{agent_name}** in team **{team}**.

Work arrives via tmux-injected wake notifications (`[wake:task]`,
`[wake:inbox]`). **Do not poll** `task list` / `inbox receive` in a
loop — wait for a wake, then run the matching fetch command.

When the goal above is completed (or if you're blocked), send:
  `clawteam inbox send {team} leader "Completed: <summary>"`
"""
