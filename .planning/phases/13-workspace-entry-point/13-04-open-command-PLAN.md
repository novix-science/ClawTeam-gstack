---
phase: 13
plan: 04
type: execute
wave: 3
depends_on: [01, 02, 03]
files_modified:
  - clawteam/solo.py
  - clawteam/cli/commands.py
  - tests/integration/test_open_sprint_start_flow.py
autonomous: true
requirements: [WS-01]
must_haves:
  truths:
    - "`clawteam open [TEMPLATE]` is registered as a top-level typer command under the '🎯 Daily use (solo)' Rich help panel"
    - "`clawteam open gstack -n foo` (no --goal argument) creates team 'foo' from the gstack template, spawns 11 clean-REPL claude panes, and emits zero kickoff prompts"
    - "`clawteam open foo` on an existing team `foo` routes to the resume branch (re-attaches to the existing tmux session; does NOT re-spawn agents)"
    - "`clawteam open` with no args AND no active team prints an error mentioning 'specify a template' or '--name'"
    - "`clawteam open gstack -n foo` accepts the same --attach/--window/--tile flag symmetry as `clawteam go` with identical defaults (all True)"
    - "The integration tests in tests/integration/test_open_sprint_start_flow.py transition from xfail to GREEN — replaced with monkeypatched subprocess.Popen pattern from tests/integration/test_gstack_sprint_end_to_end.py (NOT a non-existent mock_claude fixture, per checker B2)"
    - "cmd_open NEVER passes a non-empty --goal to the launch subprocess — honors the contract at .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md (per checker W1 + W2 contract)"
  artifacts:
    - path: clawteam/solo.py
      provides: "cmd_open function — the `clawteam open` implementation"
      contains: "def cmd_open"
    - path: clawteam/solo.py
      provides: "register_solo_commands registers `open` under the Daily use panel"
      contains: "app.command(\n        \"open\""
    - path: tests/integration/test_open_sprint_start_flow.py
      provides: "Integration tests for open → sprint start flow (Plan 13-01 stubs filled in; uses monkeypatch.setattr('subprocess.Popen', ...) — NOT mock_claude fixture)"
      contains: "monkeypatch.setattr"
  key_links:
    - from: "clawteam/solo.py::cmd_open"
      to: "clawteam launch subcommand (via subprocess, passes NO --goal)"
      via: "subprocess to `clawteam launch <template> --team <name>` without --goal"
      pattern: "launch.*--team"
    - from: "clawteam/solo.py::cmd_open"
      to: "TeamManager.team_exists (resume branch)"
      via: "branch: team exists → skip spawn, go straight to tile+attach"
      pattern: "team_exists"
    - from: "clawteam/solo.py::register_solo_commands"
      to: "clawteam/cli/commands.py app (Typer instance)"
      via: "app.command registration"
      pattern: "app.command"
---

<objective>
Register a new top-level `clawteam open` command that lands the user in a live 11-agent team with NO goal required and NO kickoff injection. The command is WS-01's user-facing surface: "open the workspace, commit to a goal later via `clawteam sprint start`."

Per 13-CONTEXT decisions block:
- Full flag symmetry with `go`: `--attach / --window / --tile / --name / --template` with identical defaults (all True)
- Positional argument is TEMPLATE (`clawteam open [TEMPLATE]`) — mirrors `launch`, not `tmux attach`
- Team name supplied via `-n/--name`
- No args + no existing team → fail loud with "specify a template (new team) or a team name with `-n`"
- Template + existing team collide → team-name wins, resume branch
- Existing team → resume path (re-attach, do not re-spawn)
- New team → spawn path (create team + launch 11 agents with NO goal → clean REPL per Plan 13-02)

**Per checker W5:** The original Task 1 was ~270 LOC in one task — borderline for CLAUDE.md §2/§3 surgical-changes. Split into:
- Task 1a (~60 LOC): cmd_open registration + arg validation + resume branch via _open_resume_existing
- Task 1b (~120 LOC): create-new branch via _open_create_new + _resolve_attach_mode + _open_render_final_panel
- Task 2: integration tests using monkeypatched subprocess.Popen (per checker B2 — no mock_claude fixture exists)

**Per checker B2:** Task 2 uses `monkeypatch.setattr("subprocess.Popen", ...)` — NOT a `mock_claude` pytest fixture (verified absent via grep across tests/). The pattern matches what `tests/integration/test_gstack_sprint_end_to_end.py` does at the subprocess boundary.

**Per checker I1:** Task 1a + 1b only depend on [01, 02] (test scaffolding + adapter gating); only Task 2 depends on [01, 02, 03] (integration tests need conductor's inject_kickoff). The plan as a whole declares depends_on [01, 02, 03] for safety (most-conservative wave), but the per-task dependency picture is documented in the task headers.

Purpose: WS-01 complete. Once this ships, the user can type `clawteam open gstack -n foo` and land in 11 clean REPLs.

Output: New `cmd_open` function in solo.py + registration under the Daily use panel + integration tests using monkeypatched subprocess.Popen.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/phases/13-workspace-entry-point/13-CONTEXT.md
@.planning/phases/13-workspace-entry-point/13-VALIDATION.md
@.planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md
@clawteam/solo.py
@clawteam/cli/commands.py
@clawteam/spawn/tmux_backend.py
@tests/cli/test_open.py
@tests/integration/test_open_sprint_start_flow.py
@tests/integration/test_gstack_sprint_end_to_end.py

<interfaces>
<!-- cmd_go signature (solo.py:158-187) — the template to mirror MINUS the goal arg: -->
```python
def cmd_go(
    goal: str = typer.Argument(..., help="What do you want the team to work on?"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Team name ..."),
    template: str = typer.Option("gstack", "--template", "-t", help="Team template ..."),
    attach: bool = typer.Option(True, "--attach/--no-attach", "-a", help="..."),
    window: bool = typer.Option(True, "--window/--no-window", "-w", help="..."),
    tile: bool = typer.Option(True, "--tile/--windows", help="..."),
) -> None:
    """Start working on a goal: create team + start sprint + launch agents."""
```

<!-- cmd_go body (solo.py:188-359) — the three-step sequence to decompose for `open`: -->
<!-- Step 1 (lines 205-212): subprocess `clawteam team spawn <template> --name <team>` -->
<!-- Step 2 (lines 214-233): subprocess `clawteam sprint start --team <team> --goal <goal>` -->
<!-- Step 3 (lines 235-305): subprocess `clawteam launch <template> --team <team>` + tmux attach orchestration + tile_panes + set_active_team + render final panel -->

<!-- Team existence check (solo.py:194-200): -->
```python
if TeamManager.team_exists(team_name):
    console.print(f"[yellow]Team '{team_name}' already exists.[/yellow] ...")
    raise typer.Exit(1)
# For Plan 13-04: the NEW cmd_open BRANCHES here instead of exiting —
# existing team → resume (skip spawn + launch, just tile + attach);
# new team → create + launch (skip sprint start — that's now WS-04's job).
```

<!-- register_solo_commands (solo.py:779-803): -->
```python
def register_solo_commands(app: typer.Typer) -> None:
    panel = "🎯 Daily use (solo)"
    app.command("go", help="Start work: ...", rich_help_panel=panel)(cmd_go)
    app.command("status", ..., rich_help_panel=panel)(cmd_status)
    app.command("answer", ..., rich_help_panel=panel)(cmd_answer)
    app.command("stop", ..., rich_help_panel=panel)(cmd_stop)
    # Plan 13-04 inserts:
    #   app.command("open", help="Open a team without committing to a goal ...",
    #               rich_help_panel=panel)(cmd_open)
```

<!-- The `launch` subcommand invoked as subprocess (cli/commands.py:4406): -->
<!-- clawteam launch <template> --team <team>  [with NO --goal to trigger WS-02 clean-REPL path] -->

<!-- subprocess.Popen mocking pattern from tests/integration/test_gstack_sprint_end_to_end.py: -->
<!-- The existing E2E test uses _install_fake_bins to lay a fake claude / tmux binary in PATH. -->
<!-- For Plan 13-04 Task 2, the lighter-weight pattern is monkeypatch.setattr("subprocess.Popen", ...) -->
<!-- because we only need to (a) verify argv shape and (b) assert _inject_prompt_via_buffer is/isn't called. -->
<!-- We do NOT need a real subprocess. -->

<!-- Verified: NO mock_claude pytest fixture exists. -->
<!-- $ grep -rn "mock_claude" tests/ → 0 hits (other than the planning docs that warn against it). -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1a: Register cmd_open + arg validation + resume branch (~60 LOC, depends on 01+02)</name>
  <read_first>
    - clawteam/solo.py lines 155-361 (full cmd_go body — the reference implementation; only the resume-branch parts apply here)
    - clawteam/solo.py lines 39-109 (terminal-emulator helpers — reused as-is)
    - clawteam/solo.py lines 125-151 (active-team pointer helpers — reused as-is)
    - clawteam/solo.py lines 779-803 (register_solo_commands — the registration target)
    - .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md (W1 contract: cmd_open MUST NOT propagate --goal — applies to Task 1b's create branch, but read here for context)
  </read_first>
  <behavior>
    - `cmd_open(template=None, name=None, attach=True, window=True, tile=True)` is registered as a top-level command under the Daily use panel
    - Arg validation: if `name is None AND template is None` → error and exit 1 with the message about specifying a template or `-n`
    - If `name is None AND template is provided` → generate auto team name (`f"solo-{uuid.uuid4().hex[:6]}"` per cmd_go:192) and pass through to create branch (Task 1b)
    - If `name is provided AND TeamManager.team_exists(name)` → resume path: call `_open_resume_existing(name, attach=attach, window=window, tile=tile)` and return
    - If `name is provided AND team does NOT exist AND no template` → error and exit 1 with helpful message
    - `_open_resume_existing` exists, probes tmux session via `tmux has-session`, sets active team pointer, tiles panes, prints resumed panel — does NOT subprocess `team spawn` or `launch`
    - All three flag defaults (`attach=True`, `window=True`, `tile=True`) match cmd_go exactly
    - cmd_go is NOT modified
  </behavior>
  <action>
    Add the following to `clawteam/solo.py`. After `cmd_go` ends (around line 360 — just before the `# ─── cmd_status` comment), insert:

    ```python
    # ---------------------------------------------------------------------------
    # `clawteam open` — create-or-resume a team without committing to a goal (WS-01)
    # ---------------------------------------------------------------------------

    def cmd_open(
        template: Optional[str] = typer.Argument(
            None,
            help="Team template (e.g., gstack). Required for new teams; "
                 "ignored when resuming an existing team by --name.",
        ),
        name: Optional[str] = typer.Option(
            None, "--name", "-n",
            help="Team name. If the team already exists, resume it. "
                 "If not, create a new team from the given template. "
                 "Default: auto-generated like 'solo-abc123' (new team).",
        ),
        attach: bool = typer.Option(
            True, "--attach/--no-attach", "-a",
            help="After launch/resume, enter the tmux session automatically. "
                 "Pass --no-attach to keep your shell free.",
        ),
        window: bool = typer.Option(
            True, "--window/--no-window", "-w",
            help="When auto-attaching, prefer a NEW terminal window over "
                 "the current shell (default).",
        ),
        tile: bool = typer.Option(
            True, "--tile/--windows",
            help="Show all agents as tiled panes in ONE window (default). "
                 "Use --windows to keep them in separate tmux windows instead.",
        ),
    ) -> None:
        """Open a team (create or resume) — no goal required (WS-01).

        Workflow-style entry point: land in 11 live claude REPLs, chat with
        the CEO agent to shape your idea, then commit via
        `clawteam sprint start <team> --goal "..."`.

        cmd_open NEVER propagates a goal to the launch subprocess — that's
        WS-04's job (clawteam sprint start). See
        .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md
        for the full contract.
        """
        import uuid
        from clawteam.team.manager import TeamManager

        # ── Arg validation (13-CONTEXT: "No args + no existing team → fail loud") ──
        if not name and not template:
            console.print(
                "[red]Specify a template for a new team (e.g. "
                "[bold]clawteam open gstack -n my-team[/bold]) "
                "or a team name with [bold]-n/--name[/bold] to resume.[/red]"
            )
            raise typer.Exit(1)

        # ── Resolve name + resume-vs-create decision ──
        if name and TeamManager.team_exists(name):
            # Resume branch — team exists, skip spawn + launch.
            # (13-CONTEXT: "Template and existing team name collide → team-name wins, resume existing")
            _open_resume_existing(name, attach=attach, window=window, tile=tile)
            return

        team_name = name or f"solo-{uuid.uuid4().hex[:6]}"

        if not template:
            console.print(
                f"[red]Team '{team_name}' does not exist. To create it, "
                f"specify a template: [bold]clawteam open gstack -n {team_name}[/bold][/red]"
            )
            raise typer.Exit(1)

        _open_create_new(
            team_name=team_name,
            template=template,
            attach=attach,
            window=window,
            tile=tile,
        )


    def _open_resume_existing(
        team_name: str, *, attach: bool, window: bool, tile: bool
    ) -> None:
        """Resume path: team already exists; tile + attach, no spawn."""
        from clawteam.spawn.tmux_backend import TmuxBackend, read_pane_map

        console.print(
            f"\n[bold cyan]▶ Resuming team '{team_name}'[/bold cyan] "
            f"[dim](team already exists; skipping spawn + launch)[/dim]"
        )

        session = f"clawteam-{team_name}"
        # Probe tmux session — if it's gone (e.g., terminal closed), the
        # resume is limited: we can set the active-team pointer but can't
        # resurrect the panes. Phase 14 handles session continuity; for
        # Phase 13 we print a helpful message.
        has_session = subprocess.run(
            ["tmux", "has-session", "-t", session],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        ).returncode == 0
        if not has_session:
            console.print(
                f"[yellow]Team '{team_name}' exists on disk, but its tmux "
                f"session '{session}' is not running. "
                f"Phase 14 (session continuity) will restore this; for now, "
                f"run [bold]clawteam stop {team_name}[/bold] and "
                f"[bold]clawteam open gstack -n {team_name}[/bold] "
                f"to re-create.[/yellow]"
            )
            raise typer.Exit(1)

        pane_map: list[tuple[int, str]] = []
        if tile:
            TmuxBackend.tile_panes(team_name)
            pane_map = read_pane_map(team_name)

        set_active_team(team_name)

        _open_render_final_panel(
            team_name=team_name, template="(resumed)", pane_map=pane_map,
            tile=tile, attach=attach, window=window, resumed=True,
        )
    ```

    Then update `register_solo_commands` (solo.py:779-803) to add `open` under the Daily use panel. Insert AFTER the `"go"` registration:

    ```python
    def register_solo_commands(app: typer.Typer) -> None:
        """Attach `go`, `open`, `status`, `answer`, `stop` as top-level commands."""
        panel = "🎯 Daily use (solo)"
        app.command(
            "go",
            help="Start work: create team + start sprint + launch agents (one-shot)",
            rich_help_panel=panel,
        )(cmd_go)
        app.command(
            "open",
            help="Open a team — create or resume without committing to a goal (WS-01)",
            rich_help_panel=panel,
        )(cmd_open)
        app.command(
            "status",
            help="Dashboard: team + sprints + questions + tmux state",
            rich_help_panel=panel,
        )(cmd_status)
        app.command(
            "answer",
            help="Pick a pending question and write your answer in $EDITOR",
            rich_help_panel=panel,
        )(cmd_answer)
        app.command(
            "stop",
            help="Clean shutdown: kill tmux + cleanup team data",
            rich_help_panel=panel,
        )(cmd_stop)
    ```

    NOTE: `_open_create_new` and `_open_render_final_panel` are referenced here but defined in Task 1b. Task 1a's `cmd_open` body forwards to `_open_create_new` for the new-team path; pytest-collection of cmd_open at the end of Task 1a will succeed because Python only resolves these names at call time — but Task 1a's tests that exercise the create branch will fail with `NameError`. Task 1a's tests focus on (a) registration + help text + arg validation and (b) the resume branch path. The create branch is exercised in Task 1b.

    **Do NOT modify `cmd_go`** — demotion (help tagline rewording) is Plan 13-05.

    **Do NOT modify `cli/commands.py`** — `register_solo_commands` already runs at commands.py:41 and will pick up the new registration automatically.
  </action>
  <verify>
    <automated>uv run pytest tests/cli/test_open.py -x -v 2>&1 | tail -20 && uv run clawteam open --help 2>&1 | head -30</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def cmd_open" clawteam/solo.py` returns 1
    - `grep -c "def _open_resume_existing" clawteam/solo.py` returns 1
    - `grep -c "app.command(\n        \"open\"" clawteam/solo.py` returns 1 (registration present)
    - `uv run clawteam open --help` exits 0 AND help text contains "create or resume"
    - `uv run clawteam --help 2>&1 | grep -E 'open'` prints the `open` entry under the Daily use panel
    - `uv run pytest tests/cli/test_open.py::TestOpenCommand::test_open_help_mentions_no_goal_required -x` exits 0
    - `uv run pytest tests/cli/test_open.py::TestOpenCommand::test_open_no_args_without_active_team_errors -x` exits 0
    - `uv run pytest tests/cli/test_open.py::TestOpenCommand::test_open_accepts_template_positional -x` exits 0
    - `uv run pytest tests/cli/test_commands.py::TestGoDemotion::test_go_runtime_signature_unchanged -x` exits 0 (cmd_go untouched)
  </acceptance_criteria>
  <done>cmd_open is registered with the correct signature; resume branch + arg validation work; all 3 Plan 13-01 open-help tests GREEN; cmd_go untouched.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 1b: Implement create-new branch + attach orchestration + final panel renderer (~120 LOC, depends on 01+02)</name>
  <read_first>
    - clawteam/solo.py (Task 1a's additions — cmd_open + _open_resume_existing must exist)
    - clawteam/solo.py lines 235-359 (cmd_go's create + launch + attach orchestration — the reference implementation for _open_create_new)
    - clawteam/solo.py lines 254-285 (cmd_go's attach-mode resolver — the reference for _resolve_attach_mode)
    - .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md (W1 contract — load-bearing for Task 1b: the launch subprocess MUST NOT pass --goal)
    - clawteam/cli/commands.py lines 4406-4409 (launch_team's --goal Option default of "" — confirms that omitting --goal in subprocess argv resolves to goal="" downstream → goal=None at adapter)
  </read_first>
  <behavior>
    - `_open_create_new` exists and:
      - Subprocesses `clawteam team spawn <template> --name <team>` (same as cmd_go step 1)
      - Subprocesses `clawteam launch <template> --team <team>` WITHOUT `--goal` (per 13-02-CONTRACT-cmd_open.md — the load-bearing piece for WS-02)
      - Resolves attach mode via `_resolve_attach_mode`
      - Sets active team + tiles panes + renders final panel
    - `_resolve_attach_mode` mirrors cmd_go:254-285's logic exactly
    - `_open_render_final_panel` prints the "🚀 Team running" or "🚀 Team resumed" panel + handles attach_mode={current, nested, none, window}
    - The launch subprocess argv NEVER contains `"--goal"` (asserted via grep in acceptance criteria)
  </behavior>
  <action>
    Append to `clawteam/solo.py` AFTER Task 1a's additions (so `cmd_open` and `_open_resume_existing` are already defined above):

    ```python
    def _open_create_new(
        team_name: str,
        template: str,
        *,
        attach: bool, window: bool, tile: bool,
    ) -> None:
        """Create path: spawn team + launch agents with NO goal (WS-01 clean REPL).

        Honors .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md:
        the launch subprocess argv MUST NOT contain --goal. Plan 13-02's adapter
        gate then guarantees post_launch_prompt=None → 11 clean REPLs.
        """
        from clawteam.spawn.tmux_backend import TmuxBackend, read_pane_map
        from clawteam.team.manager import TeamManager

        console.print(
            f"\n[bold cyan]▶ Creating team '{team_name}'[/bold cyan] "
            f"[dim](template: {template}, no goal — clean REPL)[/dim]"
        )

        # 1. Spawn team (skeleton + 11 roles). Same as cmd_go step 1.
        spawn_rc = subprocess.run(
            [sys.executable, "-m", "clawteam", "team", "spawn", template, "--name", team_name],
            capture_output=True, text=True,
        )
        if spawn_rc.returncode != 0:
            console.print(f"[red]Team spawn failed:[/red] {spawn_rc.stderr or spawn_rc.stdout}")
            raise typer.Exit(1)

        console.print(
            f"[bold cyan]▶ Launching 11 agents[/bold cyan] "
            f"[dim](no kickoff — agents boot as clean claude REPLs)[/dim]"
        )

        # 2. Launch agents WITHOUT --goal. The adapter-level gate from
        # Plan 13-02 ensures post_launch_prompt stays None, producing
        # clean REPLs per WS-02. CRITICAL: the argv must NOT contain
        # "--goal" — the contract is documented in
        # .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md.
        launch_proc = subprocess.Popen(
            [sys.executable, "-m", "clawteam", "launch", template, "--team", team_name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

        session = f"clawteam-{team_name}"
        attach_mode = _resolve_attach_mode(
            session=session, attach=attach, window=window, team_name=team_name
        )
        spawned_window = attach_mode == "window"

        launch_stdout, launch_stderr = launch_proc.communicate()
        if launch_proc.returncode != 0:
            console.print(f"[red]Launch failed:[/red] {launch_stderr or launch_stdout}")
            raise typer.Exit(1)

        set_active_team(team_name)

        pane_map: list[tuple[int, str]] = []
        if tile:
            TmuxBackend.tile_panes(team_name)
            pane_map = read_pane_map(team_name)

        _open_render_final_panel(
            team_name=team_name, template=template, pane_map=pane_map,
            tile=tile, attach=attach, window=window, resumed=False,
            attach_mode=attach_mode,
        )


    def _resolve_attach_mode(
        *, session: str, attach: bool, window: bool, team_name: str
    ) -> str:
        """Mirror cmd_go's attach-mode resolver (lines 254-285) for cmd_open."""
        import time as _time
        if not attach:
            return "none"
        in_existing_tmux = bool(os.environ.get("TMUX"))
        if window and not in_existing_tmux:
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
                        return "window"
                    break
                _time.sleep(0.2)
            return "current"
        if in_existing_tmux:
            return "nested"
        return "current"


    def _open_render_final_panel(
        *,
        team_name: str,
        template: str,
        pane_map: list[tuple[int, str]],
        tile: bool,
        attach: bool,
        window: bool,
        resumed: bool,
        attach_mode: str = "none",
    ) -> None:
        """Print the final 'Team running' panel (mirror of cmd_go:313-345)."""
        from rich.panel import Panel

        session = f"clawteam-{team_name}"
        layout_line = "tiled (one window, 11 panes)" if tile else "separate windows"
        roster_line = ""
        if pane_map:
            roster = "\n".join(f"    pane {idx}: {name}" for idx, name in pane_map)
            roster_line = f"\n[bold]Roster:[/bold]\n{roster}"

        title = "🚀 Team resumed" if resumed else "🚀 Team running (clean REPL — no goal set)"
        next_steps = (
            f"[bold]Next:[/bold]\n"
            f"  [cyan]clawteam sprint start {team_name} --goal \"...\"[/cyan]  "
            f"— commit to a goal & kick off the sprint\n"
            f"  [cyan]clawteam status[/cyan]          — dashboard\n"
            f"  [cyan]clawteam stop[/cyan]            — shut everything down\n"
            f"  [cyan]tmux attach -t {session}[/cyan]  — watch all 11 agents live"
        )
        console.print(Panel(
            f"[bold]Team:[/bold]    {team_name}\n"
            f"[bold]Template:[/bold] {template}\n"
            f"[bold]Goal:[/bold]    [dim]none yet — use `sprint start` when ready[/dim]\n"
            f"[bold]Agents:[/bold]  11 (ceo, pm, eng-mgr, designer, dx-lead, "
            f"engineer, reviewer, qa, security, shipper, sre)\n"
            f"[bold]Layout:[/bold]  {layout_line}"
            f"{roster_line}\n\n"
            f"{next_steps}",
            title=title,
            border_style="green",
        ))

        if attach_mode == "current":
            console.print()
            console.print(
                "[dim]Attaching in current shell... "
                "(Ctrl+b d to detach, your shell returns here)[/dim]"
            )
            subprocess.run(["tmux", "attach", "-t", session])
        elif attach_mode == "nested":
            console.print()
            console.print(
                f"[yellow]You're inside an existing tmux session — can't nest.[/yellow]\n"
                f"Run this to switch the current tmux client to the new team:\n"
                f"  [cyan]tmux switch-client -t {session}[/cyan]"
            )
    ```

    **Contract verification step (per 13-02-CONTRACT-cmd_open.md):**

    After writing, verify the launch subprocess argv NEVER contains `"--goal"`:

    ```bash
    grep -nA5 "subprocess.Popen" clawteam/solo.py | grep -v "#" | grep -c "\\-\\-goal"
    # MUST return 0 — cmd_open's launch invocation has zero --goal occurrences.
    ```

    Do NOT modify cmd_go. Do NOT modify cli/commands.py.
  </action>
  <verify>
    <automated>uv run pytest tests/cli/test_open.py -x -v 2>&1 | tail -10 && grep -nA5 "subprocess.Popen" clawteam/solo.py | grep -v "#" | grep -c "\\-\\-goal"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def _open_create_new" clawteam/solo.py` returns 1
    - `grep -c "def _resolve_attach_mode" clawteam/solo.py` returns 1
    - `grep -c "def _open_render_final_panel" clawteam/solo.py` returns 1
    - `grep -nA5 "subprocess.Popen" clawteam/solo.py | grep -v "#" | grep -c "\\-\\-goal"` returns 0 (W1 contract: NO --goal in launch argv from cmd_open code path)
    - `uv run pytest tests/cli/test_open.py -x` exits 0 (all 3 Plan 13-01 open tests GREEN)
    - cmd_go behavior + signature unchanged (Plan 13-05's job)
  </acceptance_criteria>
  <done>Create branch + attach + render helpers exist; launch subprocess argv has zero --goal occurrences (contract honored); all Plan 13-01 open tests GREEN.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Convert integration test xfails to real assertions via monkeypatched subprocess.Popen (B2 fix, depends on 01+02+03)</name>
  <read_first>
    - tests/integration/test_open_sprint_start_flow.py (Plan 13-01 xfail stubs)
    - tests/integration/test_gstack_sprint_end_to_end.py (existing fake-binary harness; this is the canonical pattern at the subprocess boundary — there is NO `mock_claude` pytest fixture, and grep across tests/ confirms it. Use `monkeypatch.setattr("subprocess.Popen", ...)` instead.)
    - clawteam/sprint/conductor.py (start_sprint(inject_kickoff=True) — Task 2 invokes this directly to verify 11-pane fan-out)
    - clawteam/spawn/tmux_backend.py lines 255-261 (the _inject_prompt_via_buffer seam to monkeypatch)
  </read_first>
  <behavior>
    - `test_open_no_goal_injects_no_kickoff` — invokes `cmd_open` with monkeypatched subprocess.Popen (so the real `clawteam launch` subprocess never spawns) and monkeypatched `_inject_prompt_via_buffer` (so we count injection calls). Asserts: launch was called, BUT zero kickoff injections happened.
    - `test_open_then_sprint_start_flow_with_seeded_panes` — pre-seeds tmux_pane_map.json with 11 agents, monkeypatches the tmux/subprocess boundary, calls `cmd_open` then `SprintConductor.start_sprint(inject_kickoff=True)`, asserts 11 injection calls happened on the second invocation.
    - Verifies the cmd_open contract: the captured launch argv NEVER contains `"--goal"`.
  </behavior>
  <action>
    Replace the two xfail stubs in `tests/integration/test_open_sprint_start_flow.py` with REAL test bodies using `monkeypatch.setattr("subprocess.Popen", ...)`. NO `mock_claude` fixture is referenced — that fixture does not exist.

    ```python
    """Phase 13 integration: open → sprint start composed flow (WS-01..WS-04).

    These tests use monkeypatched subprocess.Popen and monkeypatched
    _inject_prompt_via_buffer to exercise cmd_open and
    SprintConductor.start_sprint(inject_kickoff=True) WITHOUT spawning
    real subprocesses or requiring a real claude binary. The pattern
    matches tests/integration/test_gstack_sprint_end_to_end.py at the
    subprocess boundary (that file uses _install_fake_bins; here we use
    monkeypatch which is lighter and doesn't write to PATH).

    There is NO `mock_claude` pytest fixture — grep across tests/ confirms
    this. Tests reference subprocess.Popen directly via monkeypatch.
    """
    from __future__ import annotations

    import json
    import subprocess
    from pathlib import Path
    from typing import Any
    from unittest.mock import MagicMock

    import pytest
    from typer.testing import CliRunner

    from clawteam.cli.commands import app

    pytestmark = pytest.mark.integration

    runner = CliRunner()


    def _make_fake_popen(captured_argvs: list[list[str]]):
        """Return a MagicMock-style replacement for subprocess.Popen that
        records argv and yields a fake process with returncode=0."""
        def _fake(args, *pargs, **kwargs):
            captured_argvs.append(list(args))
            proc = MagicMock()
            proc.returncode = 0
            proc.communicate.return_value = ("", "")
            proc.wait.return_value = 0
            return proc
        return _fake


    def _make_fake_run(captured_argvs: list[list[str]]):
        """Return a replacement for subprocess.run that records argv and
        returns a fake CompletedProcess with returncode=0."""
        def _fake(args, *pargs, **kwargs):
            captured_argvs.append(list(args))
            cp = MagicMock()
            cp.returncode = 0
            cp.stdout = ""
            cp.stderr = ""
            return cp
        return _fake


    class TestOpenThenSprintStart:
        def test_open_no_goal_injects_no_kickoff(self, tmp_path, monkeypatch):
            """WS-01 + WS-02 + W1 contract: cmd_open emits zero kickoff injections
            AND the launch subprocess argv NEVER contains --goal."""
            monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))

            captured_popen_argvs: list[list[str]] = []
            captured_run_argvs: list[list[str]] = []
            injection_calls: list[str] = []

            # Monkeypatch the subprocess boundary so cmd_open's launch /
            # team-spawn invocations don't actually run real binaries.
            monkeypatch.setattr(
                subprocess, "Popen", _make_fake_popen(captured_popen_argvs)
            )
            monkeypatch.setattr(
                subprocess, "run", _make_fake_run(captured_run_argvs)
            )

            # Monkeypatch the kickoff-injection primitive so we can count calls.
            monkeypatch.setattr(
                "clawteam.spawn.tmux_backend._inject_prompt_via_buffer",
                lambda target, agent_name, prompt: injection_calls.append(agent_name),
                raising=False,
            )

            # Stub TeamManager.team_exists → False so cmd_open takes the create branch.
            monkeypatch.setattr(
                "clawteam.team.manager.TeamManager.team_exists",
                staticmethod(lambda name: False),
                raising=True,
            )

            # Run cmd_open with --no-attach so the test doesn't hang on tmux.
            result = runner.invoke(
                app, ["open", "gstack", "-n", "t13a", "--no-attach", "--no-tile"]
            )
            assert result.exit_code == 0, result.output

            # WS-02: zero kickoff injections during the open flow.
            assert injection_calls == [], (
                f"WS-02 violation: open injected {injection_calls} — "
                f"expected zero injections (clean REPL)"
            )

            # W1 contract: the launch subprocess argv MUST NOT contain --goal.
            launch_argvs = [
                argv for argv in (captured_popen_argvs + captured_run_argvs)
                if any("launch" in str(a) for a in argv)
            ]
            assert launch_argvs, "expected at least one `clawteam launch` invocation"
            for argv in launch_argvs:
                assert "--goal" not in argv, (
                    f"W1 contract violation: cmd_open passed --goal to launch "
                    f"(argv: {argv}). See "
                    f".planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md"
                )

        def test_open_then_sprint_start_flow_with_seeded_panes(
            self, tmp_path, monkeypatch
        ):
            """WS-01 + WS-04: open → sprint start fans kickoff to 11 panes.

            Uses monkeypatched subprocess.Popen to simulate cmd_open's launch,
            seeds tmux_pane_map.json with 11 agents, then invokes
            SprintConductor.start_sprint(inject_kickoff=True) DIRECTLY
            (bypassing the CLI) to verify 11 injection calls. This stays at
            the unit-integration seam — no real subprocesses, no
            mock_claude fixture (it doesn't exist).
            """
            monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))

            captured_popen_argvs: list[list[str]] = []
            captured_run_argvs: list[list[str]] = []
            injection_calls: list[str] = []

            monkeypatch.setattr(
                subprocess, "Popen", _make_fake_popen(captured_popen_argvs)
            )
            monkeypatch.setattr(
                subprocess, "run", _make_fake_run(captured_run_argvs)
            )
            monkeypatch.setattr(
                "clawteam.spawn.tmux_backend._inject_prompt_via_buffer",
                lambda target, agent_name, prompt: injection_calls.append(agent_name),
                raising=False,
            )

            # First, take the create branch.
            monkeypatch.setattr(
                "clawteam.team.manager.TeamManager.team_exists",
                staticmethod(lambda name: False),
                raising=True,
            )
            result_open = runner.invoke(
                app, ["open", "gstack", "-n", "t13b", "--no-attach", "--no-tile"]
            )
            assert result_open.exit_code == 0, result_open.output
            assert injection_calls == [], "open must not inject"

            # Now seed tmux_pane_map.json with 11 agents and invoke the
            # conductor directly (bypassing the sprint start CLI to avoid
            # the team-existence guard which the fake subprocess didn't
            # actually create).
            agents = [
                "ceo", "pm", "eng-mgr", "designer", "dx-lead",
                "engineer", "reviewer", "qa", "security", "shipper", "sre",
            ]
            team_dir = tmp_path / "teams" / "t13b"
            team_dir.mkdir(parents=True, exist_ok=True)
            (team_dir / "tmux_pane_map.json").write_text(
                json.dumps([[idx, name] for idx, name in enumerate(agents)])
            )

            # Stub team_exists → True so the conductor accepts the team.
            monkeypatch.setattr(
                "clawteam.team.manager.TeamManager.team_exists",
                staticmethod(lambda name: True),
                raising=True,
            )
            # Stub list_members so build_specialist_kickoff_prompt has data
            # (the conductor falls back to empty agent_id/agent_type if missing,
            # but explicit stubs make the test deterministic).
            from clawteam.team.manager import TeamMember
            members = [
                TeamMember(name=n, agent_id=f"id-{n}", agent_type="claude")
                for n in agents
            ]
            monkeypatch.setattr(
                "clawteam.team.manager.TeamManager.list_members",
                staticmethod(lambda name: members),
                raising=True,
            )

            from clawteam.sprint.conductor import SprintConductor
            conductor = SprintConductor(team_name="t13b")
            state = conductor.start_sprint(
                goal="test goal", inject_kickoff=True
            )

            assert len(injection_calls) == 11, (
                f"WS-04 violation: sprint start injected {len(injection_calls)} "
                f"panes — expected 11 (one per agent)"
            )
            assert "ceo" in injection_calls
            assert set(state.kickoff_injected_agents) == set(agents)
    ```

    Notes:
    - `subprocess.Popen` and `subprocess.run` are monkeypatched at the `subprocess` module scope; cmd_open imports subprocess as `import subprocess` so the patch is visible at call time.
    - The `TeamMember` import path may differ — verify against `clawteam/team/manager.py` (the dataclass / NamedTuple name). If it's named differently, adjust accordingly.
    - The test file MUST NOT mention `mock_claude` anywhere.
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_open_sprint_start_flow.py -x -v 2>&1 | tail -20 && grep -c "mock_claude" tests/integration/test_open_sprint_start_flow.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "pytest.xfail" tests/integration/test_open_sprint_start_flow.py` returns 0 (xfails removed)
    - `grep -c "mock_claude" tests/integration/test_open_sprint_start_flow.py` returns 0 (NO reference to non-existent fixture; B2 fix)
    - `grep -c "monkeypatch.setattr(\\s*subprocess" tests/integration/test_open_sprint_start_flow.py` returns ≥ 2 (Popen + run patched)
    - `grep -c "injection_calls" tests/integration/test_open_sprint_start_flow.py` returns ≥ 4
    - `grep -c "\\-\\-goal" tests/integration/test_open_sprint_start_flow.py` returns ≥ 1 (contract assertion)
    - `uv run pytest tests/integration/test_open_sprint_start_flow.py -x` exits 0
  </acceptance_criteria>
  <done>Integration tests use monkeypatched subprocess.Popen (per B2); zero references to mock_claude fixture; W1 contract assertion present; both tests GREEN.</done>
</task>

<task type="auto">
  <name>Task 3: Full-suite regression gate for Wave 3</name>
  <read_first>
    - .planning/phases/13-workspace-entry-point/13-VALIDATION.md
  </read_first>
  <action>
    Run:
    ```bash
    uv run pytest tests/ --ignore=tests/integration/test_phase7_ten_sprint_load.py --tb=no -q 2>&1 | tail -20
    ```

    Expected state after Plan 13-04 lands:
    - tests/cli/test_open.py — GREEN (3 tests)
    - tests/integration/test_open_sprint_start_flow.py — GREEN (2 tests)
    - tests/cli/test_commands.py::test_go_help_tagline_is_shortcut — still RED (Plan 13-05)
    - tests/cli/test_commands.py::test_go_runtime_signature_unchanged — GREEN
    - Everything else — GREEN

    Total expected RED = 1 (the `go` tagline test, owned by Plan 13-05).
  </action>
  <verify>
    <automated>uv run pytest tests/ --ignore=tests/integration/test_phase7_ten_sprint_load.py --tb=no -q 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - Full-suite final line shows exactly 1 failure (tests/cli/test_commands.py::TestGoDemotion::test_go_help_tagline_is_shortcut)
    - Zero NEW failures outside tests/cli/test_commands.py
    - xfails/skips unchanged from Wave 2
  </acceptance_criteria>
  <done>Wave 3 regression gate passes; only the Plan 13-05 tagline RED remains.</done>
</task>

</tasks>

<verification>
```bash
# Plan 13-04 scoped gate:
uv run pytest tests/cli/test_open.py tests/integration/test_open_sprint_start_flow.py -x

# Manual smoke:
uv run clawteam open --help
uv run clawteam --help | grep -A2 "Daily use"

# W1 contract (cmd_open does not propagate --goal):
grep -nA5 "subprocess.Popen" clawteam/solo.py | grep -v "#" | grep -c "\\-\\-goal"  # MUST be 0
```
</verification>

<success_criteria>
- `clawteam open` is a registered top-level command with --attach/--window/--tile/--name/--template flag symmetry
- `clawteam open gstack -n foo` (new team) creates the team and launches 11 clean-REPL panes with zero injections
- `clawteam open foo` (existing team) takes the resume branch and does NOT re-spawn
- `clawteam open` (no args, no active team) rejects loudly
- All Plan 13-01 test_open.py tests GREEN
- Integration tests use monkeypatched subprocess.Popen (per B2 fix); NO mock_claude reference
- W1 contract honored: `grep -nA5 "subprocess.Popen" clawteam/solo.py | grep -c "\\-\\-goal"` returns 0
- cmd_go behavior and signature are BYTE-IDENTICAL to HEAD (Plan 13-05's job)
- One expected RED remains: test_go_help_tagline_is_shortcut
</success_criteria>

<output>
After completion, create `.planning/phases/13-workspace-entry-point/13-04-SUMMARY.md` documenting:
- Task 1a deliverables: cmd_open + _open_resume_existing + register_solo_commands edit (~60 LOC)
- Task 1b deliverables: _open_create_new + _resolve_attach_mode + _open_render_final_panel (~120 LOC)
- Task 2 deliverables: integration tests using monkeypatched subprocess.Popen + W1 contract assertion
- Confirmation that the W1 contract (no --goal in cmd_open's launch argv) is verified by acceptance criterion AND by the integration test
- Pointer for Plan 13-05: "`clawteam open` is live; now demote `go` (help tagline + README) to make `open` + `sprint start` the documented primary flow"
</output>
