"""Event-driven agent wake: push inbox/task notifications to panes, not poll.

Agents previously burned turns polling ``clawteam task list --owner X`` and
``clawteam inbox receive --agent X`` in a loop. That wastes API calls and
adds delivery latency (up to one poll interval). Event-driven delivery
reverses the flow: when a message is WRITTEN, the writer immediately wakes
the recipient's tmux pane via ``send-keys`` so claude processes the
arrival as a user turn.

Hooks points:
  - ``clawteam inbox send``  → ``wake_agent(team, to, "inbox", preview)``
  - ``clawteam inbox broadcast`` → wake each recipient
  - ``clawteam task create --owner X`` → ``wake_agent(team, X, "task", subject)``

Debounce:
  Wakes are debounced per (team, agent) with a 3-second window (much
  shorter than the periodic ``nudge`` hook's 60s because inbox delivery
  should feel real-time). A burst of N sends within 3s produces one wake
  with "N messages pending" — avoids send-keys spam when many tasks are
  created in quick succession during team orchestration.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Debounce state
# ---------------------------------------------------------------------------
WAKE_DEBOUNCE_SECONDS = 3.0


def _data_dir() -> Path:
    override = os.environ.get("CLAWTEAM_DATA_DIR", "")
    return Path(override) if override else Path.home() / ".clawteam"


def _wake_state_path(team: str, agent: str) -> Path:
    return _data_dir() / "teams" / team / "_wake" / f"{agent}.ts"


def _recently_waked(team: str, agent: str) -> bool:
    path = _wake_state_path(team, agent)
    if not path.is_file():
        return False
    try:
        last = float(path.read_text().strip() or "0")
    except (OSError, ValueError):
        return False
    return (time.time() - last) < WAKE_DEBOUNCE_SECONDS


def _mark_waked(team: str, agent: str) -> None:
    path = _wake_state_path(team, agent)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{time.time()}\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Pane lookup
# ---------------------------------------------------------------------------

def _find_agent_pane(team: str, agent: str) -> Optional[str]:
    """Return the tmux pane_id for ``agent`` in ``team``, or None.

    Looks up the pane_index from the persisted pane_map, then resolves to
    a stable pane_id via ``tmux list-panes`` in the current session.
    Returns None if no tmux session exists yet (the team was launched
    without tmux) or if pane lookup fails.
    """
    try:
        from clawteam.spawn.tmux_backend import read_pane_map
    except ImportError:
        return None

    pane_map = read_pane_map(team)
    if not pane_map:
        return None

    # Find the pane_index for this agent.
    target_idx: Optional[int] = None
    for idx, name in pane_map:
        if name == agent:
            target_idx = idx
            break
    if target_idx is None:
        return None

    session = f"clawteam-{team}"
    # Check session exists.
    check = subprocess.run(
        ["tmux", "has-session", "-t", session],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    if check.returncode != 0:
        return None

    # Resolve pane_index → pane_id.
    result = subprocess.run(
        ["tmux", "list-panes", "-t", f"{session}:0",
         "-F", "#{pane_index}:#{pane_id}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None

    for line in result.stdout.strip().splitlines():
        if ":" not in line:
            continue
        idx_str, pid = line.split(":", 1)
        try:
            if int(idx_str) == target_idx:
                return pid
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def wake_agent(
    team: str,
    agent: str,
    kind: str,
    preview: str = "",
    force: bool = False,
) -> bool:
    """Inject a wake-up notification into ``agent``'s tmux pane.

    :param team: Team name.
    :param agent: Recipient agent role (e.g. "engineer").
    :param kind: Wake kind: ``"inbox"``, ``"task"``, or ``"custom"``.
    :param preview: Short preview of the triggering event (first line of
        message, task subject, etc.) — included in the injected text so
        the agent can react without fetching.
    :param force: Skip debounce.
    :returns: True if the wake was injected, False if skipped (debounced,
        no pane, no tmux session, ...). Silent-fail: never raises.

    Safe to call from ``clawteam inbox send`` / ``clawteam task create``
    even when no tmux session exists yet (returns False).
    """
    try:
        if not force and _recently_waked(team, agent):
            return False

        pane_id = _find_agent_pane(team, agent)
        if pane_id is None:
            return False

        # Build the wake text. Keep it short + structured so the agent can
        # parse it quickly and decide whether to fetch details.
        if kind == "inbox":
            if preview:
                text = (
                    f"[wake:inbox] New message. Preview: "
                    f"{preview[:120]}... Run `clawteam inbox receive "
                    f"{team} --agent {agent}` to read."
                )
            else:
                text = (
                    f"[wake:inbox] New message. Run `clawteam inbox "
                    f"receive {team} --agent {agent}`."
                )
        elif kind == "task":
            if preview:
                text = (
                    f"[wake:task] New task assigned: \"{preview[:140]}\". "
                    f"Run `clawteam task list {team} --owner {agent}` to "
                    f"pick up the full record, then update status."
                )
            else:
                text = (
                    f"[wake:task] New task assigned. Run `clawteam task "
                    f"list {team} --owner {agent}`."
                )
        else:
            text = f"[wake:{kind}] {preview[:200]}" if preview else f"[wake:{kind}]"

        subprocess.run(
            ["tmux", "send-keys", "-t", pane_id, "-l", text],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["tmux", "send-keys", "-t", pane_id, "Enter"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        _mark_waked(team, agent)
        return True
    except Exception:
        return False
