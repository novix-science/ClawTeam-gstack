"""Per-team on-disk agent role cards: the single-source-of-truth doc an
agent can re-read when its working memory drifts.

Each agent gets a file at ``~/.clawteam/teams/<team>/agents/<role>/agent.md``
containing the methodology prompt (from
``clawteam/templates/gstack/prompts/<role>.md``) plus a role-specific
"Available commands" appendix.

When the tmux ``alert-silence`` hook fires (agent idle 45s), we inject a
ONE-LINE nudge that says "re-read your role card at <path>" instead of
repeating the full role rules. Tradeoffs vs. inlining the whole role
methodology in every nudge:

- ~90% fewer tokens per nudge (one path vs. 3-5 lines of methodology)
- Agent fetches on demand — no cost if it still remembers
- Single source of truth — edit agent.md once and all agents see it
- Uses the Read tool, which all claude-code agents naturally have
- Updatable during a live session: `echo "..." >> .../agent.md` and
  the next `[nudge]` re-directs the agent to the updated file

Copied from gstack/prompts/<role>.md at team-create time. Further
role-specific command appendix is built dynamically here so it stays
in sync with the real clawteam CLI surface.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    override = os.environ.get("CLAWTEAM_DATA_DIR", "")
    return Path(override) if override else Path.home() / ".clawteam"


def agent_card_path(team: str, agent: str) -> Path:
    """Canonical on-disk path for this agent's role card."""
    return _data_dir() / "teams" / team / "agents" / agent / "agent.md"


# ---------------------------------------------------------------------------
# Command appendix: per-role `clawteam` commands an agent typically needs
# ---------------------------------------------------------------------------

# Commands every agent can run (pulled into each role card's appendix).
_UNIVERSAL_CMDS = """\
- `clawteam task list {team} --owner {agent}` — fetch your tasks (pull on [wake:task])
- `clawteam task update {team} <id> --status in_progress|completed`
- `clawteam inbox receive {team} --agent {agent}` — pull messages (on [wake:inbox])
- `clawteam inbox send {team} <to> "<msg>"` — message a teammate
- `clawteam workspace checkpoint {team}` — commit WIP via git
"""

# Role-specific command blocks. Each value is appended after _UNIVERSAL_CMDS.
_ROLE_CMD_APPENDICES: dict[str, str] = {
    "ceo": """\

### ceo-specific
- `clawteam task create {team} "<subject>" --owner <role>` — **your main
  tool**. Decompose the goal into tasks and assign each to a specialist.
- `clawteam sprint status <sprint_id> --team {team}` — see current phase.
- `clawteam sprint resume <sprint_id> --team {team}` — advance phase after
  gate artifacts exist (you are the only role authorized to advance).

You DELEGATE, never implement. If you catch yourself about to open
Edit/Write/Bash on project files, STOP and `task create` instead.
""",
    "pm": """\

### pm-specific
- Emit ONE of the 6 forcing questions per turn (demand / status-quo /
  specificity / wedge / observation / future-fit). Challenge, don't advise.
- Hand back to ceo when all 6 answered (set `done: true` in envelope).
""",
    "eng-mgr": """\

### eng-mgr-specific
- Produce one of 5 deliverables per turn: architecture-lock, data-flow,
  edge-case-matrix, test-plan, retro-breakdown.
- Write deliverables as markdown files committed via git.
""",
    "designer": """\

### designer-specific
- Deliver visual spec / mocks / component inventory as markdown or
  generated HTML committed to the sprint workspace.
- `/design-shotgun` and `/design-html` handlers exist in the framework
  but have no CLI wrapper yet — produce inline mocks in your response.
""",
    "dx-lead": """\

### dx-lead-specific
- Focus on CLI ergonomics, docs, onboarding UX.
- Produce `/plan-devex-review` + `/devex-review` deliverables as markdown.
""",
    "engineer": """\

### engineer-specific
- Your output IS the implementation. Read files before editing them.
- Commit each logical chunk separately with clear messages.
- If a task is ambiguous, `clawteam inbox send {team} ceo "Need clarification on: ..."`
- `/codex` handler exists for OpenAI Codex second-opinion — currently no
  CLI wrapper, describe inline.
""",
    "reviewer": """\

### reviewer-specific
- Review against the architecture-lock artifact (eng-mgr's deliverable).
- Don't approve without reading it.
- Emit review envelope with verdict: approved / changes_requested / rejected.
""",
    "qa": """\

### qa-specific
- Execute the test-plan (eng-mgr's deliverable) + adversarial edge cases.
- Report bugs: `clawteam inbox send {team} engineer "Bug: <description>"`.
""",
    "security": """\

### security-specific
- Run STRIDE on anything touching auth, user data, or external input.
- Spoof / Tamper / Repudiate / InfoDisclose / DoS / Elevate.
- Gate ship: veto if critical threat unmitigated.
""",
    "shipper": """\

### shipper-specific
- Gate ship on ceo approval (look for `ship-approval.md` artifact).
- `/ship`, `/land-and-deploy`, `/document-release` handlers exist in
  the framework but have no CLI wrapper yet — describe ship plan
  inline + wait for ceo approval before acting.
""",
    "sre": """\

### sre-specific
- Canary / benchmark / deploy infrastructure.
- `/canary`, `/benchmark`, `/setup-deploy` handlers exist in framework
  but no CLI wrapper — describe inline.
""",
}


# ---------------------------------------------------------------------------
# Card installation
# ---------------------------------------------------------------------------

def _read_base_prompt(prompt_file: str) -> Optional[str]:
    """Read ``clawteam/templates/<prompt_file>``, return None on failure.

    ``prompt_file`` values come from gstack.toml — e.g. ``gstack/prompts/ceo.md``.
    """
    if not prompt_file:
        return None
    try:
        from pathlib import Path as _Path
        import clawteam.templates as _templates_module
        templates_root = _Path(_templates_module.__file__).parent
        source = templates_root / prompt_file
        if not source.is_file():
            return None
        return source.read_text(encoding="utf-8")
    except OSError:
        return None


def install_agent_card(
    team: str,
    agent: str,
    prompt_file: str = "",
    leader_name: str = "",
) -> Optional[Path]:
    """Write ``~/.clawteam/teams/<team>/agents/<agent>/agent.md``.

    Combines the role's base methodology prompt (from
    ``clawteam/templates/<prompt_file>``) with a dynamically-generated
    "Available commands" appendix. Returns the installed path, or None
    if no prompt_file was provided (non-role-aware templates).

    Overwrites any existing card — intended to be called at team launch
    so the card reflects the current clawteam version.
    """
    if not prompt_file:
        return None
    base = _read_base_prompt(prompt_file)
    if base is None:
        return None

    # Build the commands appendix.
    universal = _UNIVERSAL_CMDS.format(team=team, agent=agent)
    role_specific = _ROLE_CMD_APPENDICES.get(agent, "").format(
        team=team, agent=agent,
    )
    # Use the actual resolved path (honors CLAWTEAM_DATA_DIR) rather than
    # hardcoding ~/.clawteam — otherwise the self-reference breaks when
    # users override the data directory.
    card_path = agent_card_path(team, agent)
    appendix = (
        f"\n\n---\n\n"
        f"## Available `clawteam` commands (your toolkit)\n\n"
        f"### Universal\n{universal}"
        f"{role_specific}\n"
        f"### When you drift\n"
        f"If you ever feel unsure of your role or what you should do next, "
        f"re-read this file: `cat {card_path}`\n"
    )

    # If this agent IS the leader (ceo in gstack), add a delegation-specific
    # header so it's impossible to miss.
    leader_note = ""
    if agent == leader_name == "ceo":
        leader_note = (
            "> **YOU ARE THE TEAM LEADER.** You DELEGATE. You never "
            "implement. When a goal arrives, your FIRST action is to "
            "decompose it and assign each piece via "
            "`clawteam task create <team> \"<subject>\" --owner <role>`.\n\n"
        )

    content = leader_note + base + appendix

    path = agent_card_path(team, agent)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError:
        return None
    return path
