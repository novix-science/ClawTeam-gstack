"""tmux-hook-driven per-turn nudge injector.

Claude agents drift over long sessions: CEO forgets it must delegate, pm
forgets the 6 forcing questions structure, shipper forgets to call
`clawteam ship` instead of `gh pr create`. This module provides a
periodic reminder that tmux fires via an ``alert-silence`` hook.

Wire-up:
    tmux set-option -t <session> monitor-silence 45   # 45s idle = likely waiting
    tmux set-hook -t <session> alert-silence \
        'run-shell -b "clawteam nudge #{pane_id}"'

The nudge command:
  1. Looks up pane_id → agent role via the persisted pane_map
  2. Checks debounce state (skip if nudged within the last 60s)
  3. Reads current sprint phase + goal
  4. Builds a role + phase-specific reminder with the concrete CLI
     commands / skills the agent can use right now
  5. Injects via ``tmux send-keys`` + Enter so claude processes it
     as a user turn
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import typer

# ---------------------------------------------------------------------------
# Debounce: skip re-injections within NUDGE_COOLDOWN_SECONDS
# ---------------------------------------------------------------------------
NUDGE_COOLDOWN_SECONDS = 60.0


def _data_dir() -> Path:
    override = os.environ.get("CLAWTEAM_DATA_DIR", "")
    return Path(override) if override else Path.home() / ".clawteam"


def _nudge_state_path(team: str, pane_id: str) -> Path:
    # pane_id is like "%13" — sanitize to "pct13" so it's safe as a filename
    safe = pane_id.replace("%", "pct").replace("/", "_")
    return _data_dir() / "teams" / team / "_nudge" / f"{safe}.ts"


def _recently_nudged(team: str, pane_id: str) -> bool:
    path = _nudge_state_path(team, pane_id)
    if not path.is_file():
        return False
    try:
        last = float(path.read_text().strip() or "0")
    except (OSError, ValueError):
        return False
    return (time.time() - last) < NUDGE_COOLDOWN_SECONDS


def _mark_nudged(team: str, pane_id: str) -> None:
    path = _nudge_state_path(team, pane_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{time.time()}\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Pane → agent lookup
# ---------------------------------------------------------------------------

def _session_of_pane(pane_id: str) -> Optional[str]:
    """Return the tmux session name that contains this pane, or None."""
    result = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane_id, "#{session_name}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _team_from_session(session: str) -> Optional[str]:
    """Extract team name from session string 'clawteam-<team>'."""
    prefix = "clawteam-"
    if session.startswith(prefix):
        return session[len(prefix):]
    return None


def _pane_index_of(pane_id: str) -> Optional[int]:
    result = subprocess.run(
        ["tmux", "display-message", "-p", "-t", pane_id, "#{pane_index}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def _agent_of_pane(team: str, pane_id: str) -> Optional[str]:
    """Look up agent role for this pane via the persisted pane_map + index."""
    idx = _pane_index_of(pane_id)
    if idx is None:
        return None
    try:
        from clawteam.spawn.tmux_backend import read_pane_map
        pane_map = read_pane_map(team)
    except ImportError:
        return None
    for i, name in pane_map:
        if i == idx:
            return name
    return None


# ---------------------------------------------------------------------------
# Sprint state (phase + goal) for contextual nudges
# ---------------------------------------------------------------------------

def _latest_sprint_state(team: str) -> dict:
    sprints_dir = _data_dir() / "teams" / team / "sprints"
    if not sprints_dir.is_dir():
        return {}
    latest = None
    latest_mtime = 0.0
    for sprint_dir in sprints_dir.iterdir():
        state_file = sprint_dir / "state.json"
        if state_file.is_file():
            m = state_file.stat().st_mtime
            if m > latest_mtime:
                latest = state_file
                latest_mtime = m
    if not latest:
        return {}
    try:
        return json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


# ---------------------------------------------------------------------------
# Role-specific nudge text
# ---------------------------------------------------------------------------

def _build_nudge_text(team: str, agent: str, state: dict) -> str:
    """Compose a short nudge that points at the role card on disk.

    Rather than repeating the full role methodology on every nudge
    (~3-5 lines, ~100 tokens), we inject a ONE-LINE pointer at the
    agent's ``agent.md`` file. Agents fetch on demand via the Read
    tool if they've drifted — otherwise they ignore the nudge.

    The card lives at
    ``~/.clawteam/teams/<team>/agents/<agent>/agent.md`` (installed at
    team launch time by clawteam.role_cards.install_agent_card). Its
    content is the role's methodology prompt + a role-specific
    `clawteam` command appendix; single source of truth for "who am
    I, what can I do".
    """
    from clawteam.role_cards import agent_card_path
    path = agent_card_path(team, agent)
    phase = state.get("current_phase", "")
    goal = state.get("goal", "")

    context_bits: list[str] = []
    if goal:
        context_bits.append(f"goal={goal}")
    if phase:
        context_bits.append(f"phase={phase}")
    context = f" ({' · '.join(context_bits)})" if context_bits else ""

    return (
        f"[nudge] Drifted from your role? Re-read `{path}` — it's your "
        f"role methodology + available `clawteam` commands in one file."
        f"{context}"
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def cmd_nudge(
    pane_id: str = typer.Argument(
        ..., help="tmux pane id (e.g. '%13') to inject a role reminder into",
    ),
    force: bool = typer.Option(
        False, "--force",
        help="Skip debounce — nudge even if we just nudged this pane",
    ),
) -> None:
    """Inject a role-specific reminder into the agent's claude pane.

    Designed to be called from a tmux ``alert-silence`` hook; also safe
    to invoke manually for testing. Exits silently on any error so a
    failing hook doesn't spam the user's tmux status line.
    """
    try:
        session = _session_of_pane(pane_id)
        if not session:
            raise typer.Exit(0)
        team = _team_from_session(session)
        if not team:
            raise typer.Exit(0)
        if not force and _recently_nudged(team, pane_id):
            raise typer.Exit(0)
        agent = _agent_of_pane(team, pane_id)
        if not agent:
            raise typer.Exit(0)
        state = _latest_sprint_state(team)
        text = _build_nudge_text(team, agent, state)
        # Inject via send-keys. Use literal mode ("-l") so special chars
        # in the nudge text don't get interpreted as keybindings. Follow
        # with Enter to submit.
        subprocess.run(
            ["tmux", "send-keys", "-t", pane_id, "-l", text],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", pane_id, "Enter"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        _mark_nudged(team, pane_id)
    except typer.Exit:
        raise
    except Exception:
        # Silent-fail: a noisy hook script drowns out the user.
        raise typer.Exit(0)


def register_nudge_command(app: typer.Typer) -> None:
    """Attach `clawteam nudge <pane_id>` as a top-level command."""
    app.command(
        "nudge",
        help="Inject a role-specific reminder into an agent pane (tmux hook target)",
    )(cmd_nudge)
