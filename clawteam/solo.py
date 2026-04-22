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
        False, "--attach", "-a",
        help="After launch, attach to tmux session immediately",
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

    # 3. Launch agents
    launch_rc = subprocess.run(
        [sys.executable, "-m", "clawteam", "launch", template, "--team", team_name],
        capture_output=True, text=True,
    )
    if launch_rc.returncode != 0:
        console.print(f"[red]Launch failed:[/red] {launch_rc.stderr or launch_rc.stdout}")
        raise typer.Exit(1)

    # Mark this team as active
    set_active_team(team_name)

    console.print()
    console.print(Panel(
        f"[bold green]✓ Team '{team_name}' is live[/bold green]\n\n"
        f"[bold]Goal:[/bold]    {goal}\n"
        f"[bold]Sprint:[/bold]  {sprint_id or '(see clawteam status)'}\n"
        f"[bold]Agents:[/bold]  11 (ceo, pm, eng-mgr, designer, dx-lead, "
        f"engineer, reviewer, qa, security, shipper, sre)\n\n"
        f"[bold]Next:[/bold]\n"
        f"  [cyan]clawteam status[/cyan]          — see what's happening (no tmux needed)\n"
        f"  [cyan]clawteam answer[/cyan]          — when agents ask you questions\n"
        f"  [cyan]clawteam stop[/cyan]            — shut everything down cleanly\n"
        f"  [cyan]tmux attach -t clawteam-{team_name}[/cyan]\n"
        f"     [dim](power-user: watch agents live in tmux panes)[/dim]",
        title="🚀 Team running",
        border_style="green",
    ))

    if attach:
        console.print()
        console.print(f"[dim]Attaching to tmux session clawteam-{team_name}... "
                      f"(Ctrl+b d to detach)[/dim]")
        subprocess.run(["tmux", "attach", "-t", f"clawteam-{team_name}"])


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


def _render_active_sprint(team: str) -> None:
    """Show the most recent sprint's goal + phase + progress."""
    from pathlib import Path

    sprints_dir = _data_dir() / "teams" / team / "sprints"
    if not sprints_dir.is_dir():
        console.print("  [dim]No sprints yet.[/dim]")
        return

    # Find most recent sprint by mtime of state.json
    latest = None
    latest_mtime = 0.0
    for sprint_dir in sprints_dir.iterdir():
        state_file = sprint_dir / "state.json"
        if state_file.is_file():
            mtime = state_file.stat().st_mtime
            if mtime > latest_mtime:
                latest = state_file
                latest_mtime = mtime

    if not latest:
        console.print("  [dim]No active sprint.[/dim]")
        return

    import json
    try:
        state = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        console.print("  [dim]Sprint state unreadable.[/dim]")
        return

    phase = state.get("current_phase", "?")
    sprint_id = state.get("sprint_id", "?")
    goal = state.get("goal", "(no goal)")
    status = state.get("status", "?")

    phases = ["think", "plan", "build", "review", "test", "ship", "reflect"]
    phase_idx = phases.index(phase) if phase in phases else -1
    progress = ""
    if phase_idx >= 0:
        filled = "█" * (phase_idx + 1)
        empty = "░" * (len(phases) - phase_idx - 1)
        progress = f"[{filled}{empty}] {phase} ({phase_idx + 1}/7)"

    console.print(f"\n[bold]Sprint:[/bold]  {sprint_id[:8]}  [dim]{status}[/dim]")
    console.print(f"[bold]Goal:[/bold]    {goal}")
    if progress:
        console.print(f"[bold]Phase:[/bold]   {progress}")


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
    """Best-effort cost panel. Flags known v1.x emit-path gap."""
    try:
        from clawteam.cost.tracker import CostTracker
        # We can't easily retrieve the tracker without re-attaching to event bus,
        # but if the event emit path is unwired (999.001), value is always 0.
        # Show a line hinting at this rather than hiding it.
        console.print(f"\n[bold]Cost:[/bold]    $0.00 / $100.00  "
                      f"[dim]cache: 0% (emit path unwired — backlog 999.001)[/dim]")
    except ImportError:
        pass


def _render_tmux_indicator(team: str) -> None:
    """Show whether the team's tmux session is alive."""
    session = f"clawteam-{team}"
    check = subprocess.run(
        ["tmux", "has-session", "-t", session],
        capture_output=True,
    )
    if check.returncode == 0:
        # Count windows
        wins = subprocess.run(
            ["tmux", "list-windows", "-t", session, "-F", "#{window_name}"],
            capture_output=True, text=True,
        )
        win_count = len(wins.stdout.splitlines()) if wins.returncode == 0 else 0
        console.print(f"\n[bold]Tmux:[/bold]    [green]●[/green] session live  "
                      f"[dim]({win_count} agent windows)[/dim]")
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
