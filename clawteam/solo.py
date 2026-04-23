"""Solo-UX: simplified top-level commands for one-person company usage.

The base CLI has ~28 commands because clawteam is a general-purpose multi-agent
harness. For a solo founder/developer, that's too many verbs to remember. This
module ships 4 top-level commands that wrap the full flow:

- ``clawteam go <goal>`` — create team + start sprint + launch agents (one-shot)
- ``clawteam status`` — single-pane dashboard (no tmux attach needed)
- ``clawteam answer`` — interactive pending-question picker + editor launch
- ``clawteam stop`` — clean shutdown of active team's tmux + data

All four read/write an ``active_team`` pointer at ``~/.clawteam/active_team``
so the user rarely has to pass ``--team``. For multi-team power use, the full
CLI surface (``team``, ``sprint``, ``launch``, ``attend``, ``inbox``, ...) is
unchanged and still available.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


# ---------------------------------------------------------------------------
# Terminal emulator detection (for `clawteam go --window`)
# ---------------------------------------------------------------------------

def _find_terminal_emulator() -> Optional[list[str]]:
    """Return an argv prefix for a detected terminal emulator + its exec flag.

    The returned list is everything needed before the command to run in the
    new window (e.g. ``["kitty", "-e"]``). Respects the user's ``$TERMINAL``
    env var first (an override/contract for unusual setups), else probes a
    short list of common Linux emulators via ``shutil.which``. Returns
    ``None`` if no known terminal is available — callers should fall back
    to a copy-paste command.
    """
    # Honor explicit override. Format: either just the binary name (we add
    # `-e` as the default exec flag) or "binary --exec-flag".
    override = os.environ.get("TERMINAL", "").strip()
    if override:
        parts = override.split()
        if shutil.which(parts[0]):
            # Most terminals use `-e` or `--` for "run this command".
            if len(parts) == 1:
                return [parts[0], "-e"]
            return parts

    # Probe order: modern GPU terminals first, then traditional X11 ones.
    # Each tuple is (binary, exec-arg).
    candidates = [
        ("kitty", "--"),          # kitty: `kitty -- cmd args`
        ("alacritty", "-e"),      # alacritty: `alacritty -e cmd args`
        ("wezterm", "start"),     # wezterm: `wezterm start -- cmd args`
        ("foot", "-e"),           # foot (wayland)
        ("ghostty", "-e"),        # ghostty
        ("gnome-terminal", "--"), # GNOME: `gnome-terminal -- cmd args`
        ("konsole", "-e"),        # KDE Plasma
        ("xfce4-terminal", "-e"), # XFCE
        ("terminator", "-e"),     # terminator
        ("xterm", "-e"),          # xterm (fallback — nearly always present)
    ]
    for binary, exec_flag in candidates:
        if shutil.which(binary):
            if binary == "wezterm":
                # wezterm wants `wezterm start -- cmd`
                return ["wezterm", "start", "--"]
            return [binary, exec_flag]
    return None


def _spawn_tmux_attach_window(team_name: str) -> str:
    """Launch a detached new-terminal-window that attaches to the team's tmux.

    Returns a status string for the caller to show (e.g. "opened in kitty"
    or a copy-paste fallback command).
    """
    session = f"clawteam-{team_name}"
    term = _find_terminal_emulator()
    if term is None:
        return (
            f"[dim]No known terminal emulator detected. Open a new window "
            f"and run:[/dim] [cyan]tmux attach -t {session}[/cyan]"
        )
    try:
        subprocess.Popen(
            term + ["tmux", "attach", "-t", session],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        return (
            f"[yellow]Failed to spawn {term[0]}: {exc}. Manually run:[/yellow] "
            f"[cyan]tmux attach -t {session}[/cyan]"
        )
    return f"[green]✓[/green] Opened new [bold]{term[0]}[/bold] window attached to tmux"


# ---------------------------------------------------------------------------
# Active-team pointer (~/.clawteam/active_team)
# ---------------------------------------------------------------------------

def _data_dir() -> Path:
    """Resolve the clawteam data dir (honors CLAWTEAM_DATA_DIR env)."""
    override = os.environ.get("CLAWTEAM_DATA_DIR", "")
    if override:
        return Path(override)
    return Path.home() / ".clawteam"


def _active_team_path() -> Path:
    return _data_dir() / "active_team"


def get_active_team() -> Optional[str]:
    """Return the currently-active team name, or None if unset."""
    p = _active_team_path()
    if not p.is_file():
        return None
    try:
        name = p.read_text(encoding="utf-8").strip()
        return name or None
    except OSError:
        return None


def set_active_team(team_name: str) -> None:
    """Set the active team pointer. Creates the data dir if needed."""
    p = _active_team_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(team_name, encoding="utf-8")


def clear_active_team() -> None:
    """Remove the active-team pointer."""
    p = _active_team_path()
    if p.is_file():
        p.unlink()


# ---------------------------------------------------------------------------
# `clawteam go` — one-shot create + start + launch
# ---------------------------------------------------------------------------

def cmd_go(
    goal: str = typer.Argument(..., help="What do you want the team to work on?"),
    name: Optional[str] = typer.Option(
        None, "--name", "-n",
        help="Team name (default: auto-generated like 'solo-abc123')",
    ),
    template: str = typer.Option(
        "gstack", "--template", "-t",
        help="Team template (default: gstack — 11-specialist team)",
    ),
    attach: bool = typer.Option(
        True, "--attach/--no-attach", "-a",
        help="After launch, enter the tmux session automatically (default). "
             "Uses a new terminal window when possible, falls back to "
             "attaching in the current shell. Pass --no-attach to keep "
             "your shell free.",
    ),
    window: bool = typer.Option(
        True, "--window/--no-window", "-w",
        help="When auto-attaching, prefer a NEW terminal window over the "
             "current shell (default). Falls back to current shell if no "
             "terminal emulator is detected or you're already inside tmux. "
             "No effect when --no-attach.",
    ),
    tile: bool = typer.Option(
        True, "--tile/--windows",
        help="Show all 11 agents as tiled panes in ONE window (default). "
             "Use --windows to keep them in separate tmux windows instead.",
    ),
) -> None:
    """Start working on a goal: create team + start sprint + launch agents."""
    import uuid
    from clawteam.team.manager import TeamManager

    team_name = name or f"solo-{uuid.uuid4().hex[:6]}"

    if TeamManager.team_exists(team_name):
        console.print(
            f"[yellow]Team '{team_name}' already exists.[/yellow] "
            f"Use [bold]clawteam stop[/bold] first to clean it up, or pass "
            f"[bold]--name OTHER[/bold] to create a second team."
        )
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]▶ Creating team '{team_name}'[/bold cyan] "
                  f"([dim]template: {template}[/dim])")

    # 1. Spawn team (skeleton + 11 roles)
    spawn_rc = subprocess.run(
        [sys.executable, "-m", "clawteam", "team", "spawn", template, "--name", team_name],
        capture_output=True, text=True,
    )
    if spawn_rc.returncode != 0:
        console.print(f"[red]Team spawn failed:[/red] {spawn_rc.stderr or spawn_rc.stdout}")
        raise typer.Exit(1)

    console.print(f"[bold cyan]▶ Starting sprint[/bold cyan] [dim]goal: {goal}[/dim]")

    # 2. Start sprint
    sprint_rc = subprocess.run(
        [sys.executable, "-m", "clawteam", "sprint", "start",
         "--team", team_name, "--goal", goal, "--no-auto-advance"],
        capture_output=True, text=True,
    )
    if sprint_rc.returncode != 0:
        console.print(f"[red]Sprint start failed:[/red] {sprint_rc.stderr or sprint_rc.stdout}")
        console.print(f"[dim]Team '{team_name}' created but no sprint started. "
                      f"Run [bold]clawteam stop[/bold] to clean up.[/dim]")
        raise typer.Exit(1)

    # Extract sprint id from output (format: "id: abc12345")
    sprint_id = ""
    for line in sprint_rc.stdout.splitlines():
        if line.strip().startswith("id:"):
            sprint_id = line.strip().split(":", 1)[1].strip()
            break

    console.print(f"[bold cyan]▶ Launching 11 agents[/bold cyan] "
                  f"[dim](tmux session: clawteam-{team_name})[/dim]")

    # 3. Launch agents. Run in the background so we can open a new-terminal
    # attach window as soon as the tmux session comes up (user sees agents
    # materialize live rather than staring at a blank terminal for 25s).
    launch_proc = subprocess.Popen(
        [sys.executable, "-m", "clawteam", "launch", template, "--team", team_name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )

    session = f"clawteam-{team_name}"
    # Resolve the attach strategy once. Auto-attach is the default (user
    # wants to land in tmux without a second command). Decision tree:
    #   --no-attach             → skip both
    #   --no-window             → always attach in current shell at the end
    #   --window + inside tmux  → "switch-client" inside tmux
    #   --window + detected emu → spawn new terminal window now
    #   --window + no emu       → fall back to current-shell attach at the end
    attach_mode = "none"
    spawned_window = False
    if attach:
        in_existing_tmux = bool(os.environ.get("TMUX"))
        if window and not in_existing_tmux:
            # Poll until tmux session exists, then spawn the detected
            # terminal emulator with `tmux attach`.
            import time as _time
            deadline = _time.monotonic() + 10.0
            while _time.monotonic() < deadline:
                if subprocess.run(
                    ["tmux", "has-session", "-t", session],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                ).returncode == 0:
                    term = _find_terminal_emulator()
                    if term is not None:
                        msg = _spawn_tmux_attach_window(team_name)
                        console.print(f"  {msg}")
                        spawned_window = True
                        attach_mode = "window"
                    break
                _time.sleep(0.2)
            # If no terminal detected / session never showed up, fall back
            # to attaching in the current shell at the end of launch.
            if not spawned_window:
                attach_mode = "current"
        elif in_existing_tmux:
            # Can't nest tmux; tell the user how to switch into the session
            # from within their existing tmux at the end.
            attach_mode = "nested"
        else:
            attach_mode = "current"

    # Wait for the background launch to finish.
    launch_stdout, launch_stderr = launch_proc.communicate()
    if launch_proc.returncode != 0:
        console.print(f"[red]Launch failed:[/red] {launch_stderr or launch_stdout}")
        raise typer.Exit(1)

    # Mark this team as active
    set_active_team(team_name)

    # Tile panes by default so the user sees all 11 agents on one screen
    # with per-pane index labels. Opt out with --windows.
    pane_map: list[tuple[int, str]] = []
    from clawteam.spawn.tmux_backend import TmuxBackend, read_pane_map
    if tile:
        TmuxBackend.tile_panes(team_name)
        # Read the pane → agent mapping captured during tiling. Claude's
        # TUI overwrites pane_title dynamically post-launch, so the stable
        # identifier is the pane index; we pair it with launch-order names
        # so the user can always tell which pane is which agent.
        pane_map = read_pane_map(team_name)
    else:
        # Non-tiled (separate windows) mode still benefits from mouse
        # support + pane-border labels, so enable those explicitly.
        TmuxBackend.enable_mouse(team_name)

    console.print()
    layout_line = (
        "11 panes in one tmux window (see pane-to-agent map below)"
        if tile
        else "11 separate tmux windows (Ctrl+b n to cycle)"
    )
    # Format the pane map as a compact inline roster.
    roster_line = ""
    if pane_map:
        roster_line = (
            "\n[bold]Panes:[/bold]   "
            + "  ".join(
                f"[yellow]{idx}[/yellow]=[cyan]{name}[/cyan]"
                for idx, name in pane_map
            )
        )
    console.print(Panel(
        f"[bold green]✓ Team '{team_name}' is live[/bold green]\n\n"
        f"[bold]Goal:[/bold]    {goal}\n"
        f"[bold]Sprint:[/bold]  {sprint_id or '(see clawteam status)'}\n"
        f"[bold]Agents:[/bold]  11 (ceo, pm, eng-mgr, designer, dx-lead, "
        f"engineer, reviewer, qa, security, shipper, sre)\n"
        f"[bold]Layout:[/bold]  {layout_line}"
        f"{roster_line}\n\n"
        f"[bold]Next:[/bold]\n"
        f"  [cyan]clawteam status[/cyan]          — dashboard (no tmux needed)\n"
        f"  [cyan]clawteam answer[/cyan]          — when agents ask you questions\n"
        f"  [cyan]clawteam stop[/cyan]            — shut everything down cleanly\n"
        f"  [cyan]tmux attach -t clawteam-{team_name}[/cyan]\n"
        f"     [dim]watch all 11 agents live "
        f"(Ctrl+b → arrow keys to move between panes, Ctrl+b d to detach)[/dim]",
        title="🚀 Team running",
        border_style="green",
    ))

    # Apply the attach_mode resolved earlier.
    if attach_mode == "current":
        console.print()
        console.print(f"[dim]Attaching in current shell... "
                      f"(Ctrl+b d to detach, your shell returns here)[/dim]")
        subprocess.run(["tmux", "attach", "-t", session])
    elif attach_mode == "nested":
        console.print()
        console.print(
            f"[yellow]You're inside an existing tmux session — can't nest.[/yellow]\n"
            f"Run this to switch the current tmux client to the new team:\n"
            f"  [cyan]tmux switch-client -t {session}[/cyan]"
        )


# ---------------------------------------------------------------------------
# `clawteam status` — single-pane dashboard
# ---------------------------------------------------------------------------

def cmd_status(
    team: Optional[str] = typer.Option(
        None, "--team", "-t",
        help="Team name (default: active team from `clawteam go`)",
    ),
) -> None:
    """Show a single-pane dashboard of the active team — no tmux attach needed."""
    from clawteam.team.manager import TeamManager

    t = team or get_active_team()
    if not t:
        console.print(
            "[yellow]No active team.[/yellow]\n"
            "Start one: [bold cyan]clawteam go \"your goal\"[/bold cyan]\n"
            "Or list all teams: [bold]clawteam team discover[/bold]"
        )
        raise typer.Exit(0)

    if not TeamManager.team_exists(t):
        console.print(
            f"[red]Team '{t}' not found.[/red] "
            f"The active-team pointer is stale — run "
            f"[bold]clawteam stop[/bold] to clear it."
        )
        raise typer.Exit(1)

    # Header
    members = TeamManager.list_members(t)
    console.print()
    console.print(f"[bold cyan]━━ {t} ━━[/bold cyan]  "
                  f"[dim]{len(members)} agents[/dim]")

    # Active sprint
    _render_active_sprint(t)

    # Pending questions (top 5)
    _render_pending_questions(t)

    # Cost + cache
    _render_cost_panel(t)

    # Tmux session indicator
    _render_tmux_indicator(t)

    console.print()
    console.print("[dim]Commands:  "
                  "[cyan]clawteam answer[/cyan] (pending Qs) · "
                  "[cyan]clawteam stop[/cyan] (shutdown) · "
                  f"[cyan]tmux attach -t clawteam-{t}[/cyan] (live view)[/dim]")
    console.print()


_SPRINT_PHASES = ("think", "plan", "build", "review", "test", "ship", "reflect")


def _render_active_sprint(team: str) -> None:
    """List all sprints for the team, highlighting active (running) ones.

    A team can run multiple sprints in parallel (Phase 7 SprintConductor
    allows up to 10 concurrent). Show the full sprint list so the user
    sees every in-flight workstream, not just the most recently touched one.
    Completed / paused sprints are dim; running ones render the phase bar.
    """
    import json
    from pathlib import Path

    sprints_dir = _data_dir() / "teams" / team / "sprints"
    if not sprints_dir.is_dir():
        console.print("  [dim]No sprints yet.[/dim]")
        return

    # Collect all sprints with their state + mtime for stable sort order.
    entries: list[tuple[float, dict]] = []
    for sprint_dir in sprints_dir.iterdir():
        state_file = sprint_dir / "state.json"
        if not state_file.is_file():
            continue
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            entries.append((state_file.stat().st_mtime, state))
        except (OSError, json.JSONDecodeError):
            continue

    if not entries:
        console.print("  [dim]No sprints yet.[/dim]")
        return

    # Sort newest first so active work is at the top.
    entries.sort(key=lambda kv: -kv[0])
    active = [s for _, s in entries if s.get("status") == "running"]
    other = [s for _, s in entries if s.get("status") != "running"]

    # Header line with active count
    count_line = f"{len(active)} active"
    if other:
        count_line += f" · {len(other)} inactive"
    console.print(f"\n[bold]Sprints:[/bold] [dim]({count_line})[/dim]")

    # Render each active sprint with its phase bar inline.
    for s in active:
        console.print(_format_sprint_line(s, running=True))
    # Compact line for non-active sprints (up to 3 shown, older ones summarized).
    if other:
        for s in other[:3]:
            console.print(_format_sprint_line(s, running=False))
        if len(other) > 3:
            console.print(f"  [dim]... +{len(other) - 3} older sprints[/dim]")


def _format_sprint_line(state: dict, running: bool) -> str:
    """Compose a single-line sprint summary for the status dashboard."""
    sprint_id = (state.get("sprint_id") or "?")[:8]
    goal = state.get("goal") or "(no goal)"
    phase = state.get("current_phase") or "?"
    status = state.get("status") or "?"
    queue = state.get("queue_status") or ""

    if running:
        if phase in _SPRINT_PHASES:
            idx = _SPRINT_PHASES.index(phase)
            bar = "█" * (idx + 1) + "░" * (len(_SPRINT_PHASES) - idx - 1)
            phase_str = f"[{bar}] [cyan]{phase}[/cyan] ({idx + 1}/7)"
        else:
            phase_str = f"[dim]{phase}[/dim]"
        marker = "[green]▶[/green]"
        q_suffix = f" [yellow]({queue})[/yellow]" if queue else ""
        return (
            f"  {marker} [bold]{sprint_id}[/bold]  {phase_str}  "
            f"[dim]—[/dim] {goal}{q_suffix}"
        )
    # Non-running sprint: compact, dim
    return (
        f"  [dim]·[/dim] [dim]{sprint_id}  {status:<9}  "
        f"{phase:<8} — {goal}[/dim]"
    )


def _render_pending_questions(team: str) -> None:
    """Show top 5 pending questions from this team's attention queue."""
    from pathlib import Path

    sprints_dir = _data_dir() / "teams" / team / "sprints"
    if not sprints_dir.is_dir():
        return

    pending: list[tuple[str, str, str]] = []  # (qid, sprint_id, title)
    for sprint_dir in sprints_dir.iterdir():
        questions_dir = sprint_dir / "questions"
        answers_dir = sprint_dir / "answers"
        if not questions_dir.is_dir():
            continue
        for q_file in questions_dir.glob("*.md"):
            qid = q_file.stem
            a_file = answers_dir / f"{qid}.md" if answers_dir.is_dir() else None
            if a_file and a_file.is_file():
                continue  # answered
            title = _extract_first_heading(q_file) or qid
            pending.append((qid, sprint_dir.name, title))

    if not pending:
        console.print("\n[bold]Questions:[/bold]  [dim]none pending ✓[/dim]")
        return

    console.print(f"\n[bold]Questions:[/bold]  [yellow]{len(pending)} pending[/yellow]")
    for qid, sprint_id, title in pending[:5]:
        console.print(f"  [dim]{qid}[/dim]  {title}")
    if len(pending) > 5:
        console.print(f"  [dim]... +{len(pending) - 5} more (clawteam answer)[/dim]")


def _extract_first_heading(path: Path) -> str:
    """Pull the first H1 line from a markdown file, stripped of ``# `` prefix."""
    try:
        with path.open(encoding="utf-8") as f:
            in_frontmatter = False
            for line in f:
                line = line.rstrip()
                if line == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if in_frontmatter:
                    continue
                if line.startswith("# "):
                    return line[2:].strip()
    except OSError:
        return ""
    return ""


def _render_cost_panel(team: str) -> None:
    """Cost panel removed post-v1.0 UAT 2026-04-22 — point user at Anthropic console."""
    console.print(
        f"\n[bold]Cost:[/bold]    [dim]not tracked locally — see "
        f"https://console.anthropic.com/settings/usage[/dim]"
    )


def _render_tmux_indicator(team: str) -> None:
    """Show whether the team's tmux session is alive + pane roster if tiled."""
    session = f"clawteam-{team}"
    check = subprocess.run(
        ["tmux", "has-session", "-t", session],
        capture_output=True,
    )
    if check.returncode == 0:
        # Count windows + panes in window 0 to distinguish tiled vs windows mode
        wins = subprocess.run(
            ["tmux", "list-windows", "-t", session, "-F", "#{window_name}"],
            capture_output=True, text=True,
        )
        win_count = len(wins.stdout.splitlines()) if wins.returncode == 0 else 0
        panes_w0 = subprocess.run(
            ["tmux", "list-panes", "-t", f"{session}:0"],
            capture_output=True, text=True,
        )
        pane_count = (
            len(panes_w0.stdout.strip().splitlines()) if panes_w0.returncode == 0 else 0
        )
        if pane_count > 1:
            layout_desc = f"{pane_count} panes tiled in window 0"
        else:
            layout_desc = f"{win_count} separate windows"
        console.print(f"\n[bold]Tmux:[/bold]    [green]●[/green] session live  "
                      f"[dim]({layout_desc})[/dim]")

        # Render pane-to-agent roster if we have one on disk.
        try:
            from clawteam.spawn.tmux_backend import read_pane_map
            pane_map = read_pane_map(team)
            if pane_map:
                roster = "  ".join(
                    f"[yellow]{idx}[/yellow]=[cyan]{name}[/cyan]"
                    for idx, name in pane_map
                )
                console.print(f"[bold]Panes:[/bold]   {roster}")
        except Exception:
            pass
    else:
        console.print(f"\n[bold]Tmux:[/bold]    [red]○[/red] no session  "
                      f"[dim](agents not running — `clawteam go` to start)[/dim]")


# ---------------------------------------------------------------------------
# `clawteam answer` — interactive question picker
# ---------------------------------------------------------------------------

def cmd_answer(
    team: Optional[str] = typer.Option(
        None, "--team", "-t",
        help="Team name (default: active team)",
    ),
) -> None:
    """List pending questions and open your $EDITOR to answer one."""
    from pathlib import Path

    t = team or get_active_team()
    if not t:
        console.print("[yellow]No active team.[/yellow] "
                      "Start one with [bold cyan]clawteam go \"your goal\"[/bold cyan].")
        raise typer.Exit(0)

    sprints_dir = _data_dir() / "teams" / t / "sprints"
    if not sprints_dir.is_dir():
        console.print(f"[dim]No sprints for team '{t}' — nothing to answer.[/dim]")
        raise typer.Exit(0)

    pending: list[tuple[Path, Path, str]] = []  # (q_path, a_path, title)
    for sprint_dir in sprints_dir.iterdir():
        questions_dir = sprint_dir / "questions"
        answers_dir = sprint_dir / "answers"
        if not questions_dir.is_dir():
            continue
        answers_dir.mkdir(exist_ok=True)
        for q_file in sorted(questions_dir.glob("*.md")):
            a_file = answers_dir / q_file.name
            if a_file.is_file():
                continue
            title = _extract_first_heading(q_file) or q_file.stem
            pending.append((q_file, a_file, title))

    if not pending:
        console.print(f"[green]✓ No pending questions for team '{t}'.[/green]")
        raise typer.Exit(0)

    # Show numbered list
    console.print(f"\n[bold]Pending questions for [cyan]{t}[/cyan]:[/bold]\n")
    for i, (q_path, _, title) in enumerate(pending, start=1):
        console.print(f"  [bold]{i}.[/bold]  {title}  [dim]({q_path.stem})[/dim]")

    console.print()
    try:
        choice = typer.prompt(
            "Pick one to answer (number, or 'q' to cancel)",
            default="q",
        )
    except (typer.Abort, KeyboardInterrupt):
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit(0)

    if choice.strip().lower() in ("q", "quit", "cancel", ""):
        console.print("[dim]Cancelled.[/dim]")
        raise typer.Exit(0)

    try:
        idx = int(choice.strip()) - 1
        q_path, a_path, title = pending[idx]
    except (ValueError, IndexError):
        console.print(f"[red]Invalid choice:[/red] {choice}")
        raise typer.Exit(1)

    editor = os.environ.get("EDITOR", "vi")
    console.print(f"\n[dim]Opening {q_path} in {editor} to read; "
                  f"write your answer to {a_path}...[/dim]")

    # Open the question in the editor. User reads, closes, then we check for answer file.
    rc = subprocess.run([editor, str(q_path)])
    if rc.returncode != 0:
        console.print(f"[yellow]Editor exited with code {rc.returncode}.[/yellow]")

    if not a_path.is_file():
        console.print(
            f"\n[yellow]No answer file found yet.[/yellow]\n"
            f"Write your answer to:\n  [cyan]{a_path}[/cyan]\n"
            f"Once the file exists, the InteractionGate will unblock on next evaluation."
        )
        # Also offer to open the answer path directly
        open_it = typer.confirm("Open the answer file in your editor now?", default=True)
        if open_it:
            a_path.write_text(
                f"# Answer to {q_path.stem}\n\n"
                f"(delete this placeholder and write your answer)\n",
                encoding="utf-8",
            )
            subprocess.run([editor, str(a_path)])
            if a_path.is_file() and a_path.stat().st_size > 0:
                console.print(f"[green]✓ Answer saved to {a_path.name}[/green]")
    else:
        console.print(f"[green]✓ Answer file exists: {a_path.name}[/green]")


# ---------------------------------------------------------------------------
# `clawteam stop` — clean shutdown
# ---------------------------------------------------------------------------

def cmd_stop(
    team: Optional[str] = typer.Option(
        None, "--team", "-t",
        help="Team to stop (default: active team)",
    ),
    keep_data: bool = typer.Option(
        False, "--keep-data",
        help="Kill tmux but keep ~/.clawteam/teams/<team>/ data for later inspection",
    ),
    force: bool = typer.Option(
        False, "--force", "-f",
        help="Skip the confirmation prompt",
    ),
) -> None:
    """Clean shutdown: kill tmux session + cleanup team data."""
    from clawteam.team.manager import TeamManager

    t = team or get_active_team()
    if not t:
        console.print("[yellow]No active team.[/yellow] Nothing to stop.")
        raise typer.Exit(0)

    if not force:
        action = "kill tmux + delete data" if not keep_data else "kill tmux (keep data)"
        confirmed = typer.confirm(
            f"Stop team '{t}' ({action})?",
            default=True,
        )
        if not confirmed:
            console.print("[dim]Cancelled.[/dim]")
            raise typer.Exit(0)

    session = f"clawteam-{t}"
    console.print(f"\n[bold cyan]▶ Killing tmux session {session}[/bold cyan]")
    kill_rc = subprocess.run(
        ["tmux", "kill-session", "-t", session],
        capture_output=True, text=True,
    )
    if kill_rc.returncode == 0:
        console.print(f"[green]  ✓[/green] tmux session killed")
    else:
        # Not fatal — session may already be gone
        console.print(f"[dim]  (no tmux session to kill)[/dim]")

    if not keep_data:
        console.print(f"[bold cyan]▶ Cleaning up team data[/bold cyan]")
        if TeamManager.team_exists(t):
            cleanup_rc = subprocess.run(
                [sys.executable, "-m", "clawteam", "team", "cleanup", t, "--force"],
                capture_output=True, text=True,
            )
            if cleanup_rc.returncode == 0:
                console.print(f"[green]  ✓[/green] team data removed")
            else:
                console.print(f"[yellow]  cleanup reported: "
                              f"{cleanup_rc.stderr or cleanup_rc.stdout}[/yellow]")

    # Clear active-team pointer if this was it
    if get_active_team() == t:
        clear_active_team()

    console.print(f"\n[bold green]✓ Team '{t}' stopped.[/bold green]")
    console.print("[dim]Start a new one with [cyan]clawteam go \"your goal\"[/cyan].[/dim]\n")


# ---------------------------------------------------------------------------
# Registration: attach the 4 commands to the main Typer app
# ---------------------------------------------------------------------------

def register_solo_commands(app: typer.Typer) -> None:
    """Attach `go`, `status`, `answer`, `stop` as top-level commands."""
    app.command("go", help="Start work: create team + start sprint + launch agents (one-shot)")(cmd_go)
    app.command("status", help="Dashboard: team state + sprint + questions + cost, no tmux needed")(cmd_status)
    app.command("answer", help="Interactively answer a pending question in your $EDITOR")(cmd_answer)
    app.command("stop", help="Clean shutdown: kill tmux + cleanup team data")(cmd_stop)
