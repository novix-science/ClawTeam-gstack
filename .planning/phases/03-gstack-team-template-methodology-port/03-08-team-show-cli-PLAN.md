---
phase: 03-gstack-team-template-methodology-port
plan: 08
type: execute
wave: 4
depends_on: [03-02, 03-07]
files_modified:
  - clawteam/cli/commands.py
  - tests/test_cli_commands.py
autonomous: true
requirements: [UX-07]
must_haves:
  truths:
    - "`clawteam team show <name>` Typer subcommand exists under the `team_app` subgroup (parallel to `team status` at commands.py:1611-1656)"
    - "Dashboard displays 4 sections: (1) member roster (all 11 gstack roles from TeamConfig), (2) active sprint progress with phase indicator, (3) memory highlights (count of <data_dir>/teams/<team>/_phase6_pending/ entries — placeholder until Phase 6), (4) cost/token rollup (placeholder until Phase 7 AttentionQueue + cost-dashboard)"
    - "Command supports `--json` flag for machine-readable output (consistent with existing `_output(data, _human)` pattern at commands.py:1656)"
    - "Command works for non-gstack teams: dashboard renders member roster + sprint progress; memory/cost placeholder rows show '-' or 'N/A' instead of gstack-specific counts (CORE-03 BC)"
    - "Command returns non-zero exit when team name not found (consistent with team status at line 1620)"
  artifacts:
    - path: "clawteam/cli/commands.py"
      provides: "team_show Typer command under team_app — reads TeamConfig + SprintState + _phase6_pending/ dir + composes rich.Table dashboard"
      contains: "@team_app.command(\"show\")"
    - path: "tests/test_cli_commands.py"
      provides: "test_team_show_gstack_dashboard + test_team_show_not_found + test_team_show_non_gstack_team + test_team_show_json_output"
      contains: "test_team_show_gstack_dashboard"
  key_links:
    - from: "clawteam/cli/commands.py::team_show"
      to: "clawteam/team/manager.py::TeamManager.get_team"
      via: "TeamConfig lookup (mirrors team_status at line 1618)"
      pattern: "TeamManager.get_team"
    - from: "clawteam/cli/commands.py::team_show"
      to: "<data_dir>/teams/<team>/_phase6_pending/"
      via: "`get_data_dir() / 'teams' / team / '_phase6_pending'` glob — reads placeholder count from 03-07's Reflect-phase writes"
      pattern: "_phase6_pending"
    - from: "clawteam/cli/commands.py::team_show"
      to: "clawteam/sprint/conductor.py::SprintState (or equivalent list_sprints helper)"
      via: "Active-sprint lookup for the progress row"
      pattern: "sprint"
---

<objective>
Ship the `clawteam team show <name>` Typer subcommand that renders the team dashboard per UX-07: member list (all 11 gstack roles when the team is gstack-templated, or whatever the team's TemplateDef declares for other templates), active sprint progress with phase indicator, memory highlights (most-recent `/learn` entries — Phase 3 ships a count-of-`_phase6_pending/` placeholder until Phase 6's real TeamMemoryStore lands), and per-agent token/cost rollup (placeholder values until Phase 7 full observability lands).

Purpose: this is the user-visible "dashboard payoff" of Phase 3. After `clawteam team spawn gstack --name myteam` (03-02) + `clawteam sprint start` (Phase 2), the user runs `clawteam team show myteam` and sees the team come alive — 11 specialists on the roster, current sprint at phase N/7, N memory entries queued for Phase 6 backfill, cost rollup stubbed.

**Scope discipline:** The command is a pure read + render — it does NOT modify state. It composes existing lookups (`TeamManager.get_team`, `_phase6_pending/` glob, sprint state reader) into a rich.Table layout mirroring `team status`'s `_output(data, _human)` pattern. Cross-template BC is preserved: non-gstack teams see the member roster and sprint progress; the memory/cost rows degrade gracefully to "N/A" or "-".

**Why this plan is small (~3 tasks):** The command is rendering-only. The heavy lifting (TeamConfig load, TemplateDef parse, sprint state, file-system scan for placeholders) is already substrate from Phase 1/2 + 03-02 + 03-07. This plan wires them together into one function.

**D-12 confirmation (from PATTERNS.md):** The `team show` subcommand does NOT exist in the pre-Phase-3 tree. `team status` at commands.py:1611-1656 is the structural analog. This plan creates `team_show` as a NEW command under the same `@team_app.command(...)` group.

Output:
- 1 new command function in `clawteam/cli/commands.py` (~80 LOC including `_human` renderer)
- `tests/test_cli_commands.py` extended with 4 new tests (happy-path dashboard render; not-found error; non-gstack team fallback; `--json` output shape)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md
@.planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md
@.planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md
@.planning/phases/03-gstack-team-template-methodology-port/03-VALIDATION.md
@.planning/phases/03-gstack-team-template-methodology-port/03-02-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-07-SUMMARY.md

<interfaces>
<!-- Contracts the executor consumes from the CLI layer + Phase 1/2 substrate + 03-02/03-07. -->

From clawteam/cli/commands.py::team_status (lines 1611-1656 — STRUCTURAL ANALOG — mirror this shape):
```python
@team_app.command("status")
def team_status(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show team status and members."""
    from clawteam.team.manager import TeamManager

    config = TeamManager.get_team(team)
    if not config:
        _output({"error": f"Team '{team}' not found"}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    data = {
        "name": config.name,
        ...
        "members": [m.model_dump(by_alias=True) for m in config.members],
    }

    def _human(d):
        console.print(f"\nTeam: [cyan]{d['name']}[/cyan]")
        ...
        table = Table(title="Members")
        ...

    _output(data, _human)
```

`team_show` mirrors this shape:
- Same `team: str = typer.Argument(...)` signature
- Same `TeamManager.get_team(team)` lookup + `typer.Exit(1)` on not-found
- Same `_output(data, _human)` dual-path (JSON + human) at the end
- Same `rich.Table` for each dashboard section

From clawteam/team/manager.py::TeamManager.get_team (used by team_status):
- `get_team(name: str) -> TeamConfig | None` (returns None when not found)
- TeamConfig carries: name, description, lead_agent_id, created_at, members list, and (after 03-02) `template: str`, `leader_role: str`

From TeamConfig.members (existing model — reused for the roster row):
- Each member has `.name`, `.agent_id`, `.agent_type`, `.joined_at` (the same fields team_status iterates)

From 03-07 plugin (active only for gstack teams):
- `<data_dir>/teams/<team>/_phase6_pending/<sprint_id>-retro.json` files written by Reflect-phase handler
- For team show, glob this dir and count files for the "memory highlights" placeholder row

From Phase 2 SprintState (clawteam/sprint/):
- Expected: a way to list sprints owned by a team (function name may vary — grep `clawteam/sprint/` for the equivalent during Task 1 read). If the public API is `SprintStore.list_for_team(team_name)` that returns list of SprintState objects, use that. If the API differs, adapt.
- Each SprintState has: sprint_id, current_phase, phase_index (N/M), goal, started_at

From clawteam/cli/commands.py module top (imports already present — reuse):
- `typer` (argument declarations)
- `console` (rich Console instance)
- `Table` from rich.table (for dashboard rows)
- `format_timestamp` (helper for `joined_at`, `started_at` rendering)
- `_output(data, human_fn)` (JSON-vs-human renderer)
- `team_app` (the Typer subgroup this command joins)

Cost-rollup placeholder (Phase 7 deferred per ROADMAP + deferred-to-Phase-7 list):
- Current: "Cost rollup: pending Phase 7 observability"
- Structured data: `{"cost_rollup": {"status": "pending_phase_7", "per_agent": [], "total_tokens": None, "total_usd": None}}`

Memory placeholder (Phase 6 deferred per ROADMAP):
- If team is gstack-templated: scan `get_data_dir() / "teams" / team / "_phase6_pending" / "*.json"` and count files
- For non-gstack teams: show "-" (N/A)
- Structured data: `{"memory": {"status": "pending_phase_6", "placeholder_entries": N}}`

JSON output shape (for `_output(data, ...)`):
```json
{
  "name": "acme",
  "template": "gstack",
  "leaderRole": "ceo",
  "members": [ ... 11 entries for gstack ... ],
  "activeSprint": {"sprintId": "...", "currentPhase": "build", "phaseIndex": "3/7", "goal": "..."} | null,
  "memory": {"status": "pending_phase_6", "placeholderEntries": 2},
  "costRollup": {"status": "pending_phase_7", "perAgent": [], "totalTokens": null, "totalUsd": null}
}
```

Typer argument pattern:
- `team: str = typer.Argument(..., help="Team name")`
- NO `--json` option — the `_output(data, _human)` helper at commands.py detects JSON mode from a global flag (or from passed context); mirror `team_status` behavior verbatim.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author `team show` Typer command with dashboard composition</name>
  <files>clawteam/cli/commands.py</files>
  <read_first>
    - clawteam/cli/commands.py (lines 1611-1656 — team_status structural analog; lines 1659+ — team_snapshot for the next-command convention; top-of-file — imports + _output helper + team_app Typer subgroup; format_timestamp helper)
    - clawteam/team/manager.py (TeamManager.get_team signature; TeamConfig model fields — especially the 03-02-extended `template` + `leader_role` + `members`)
    - clawteam/team/models.py (TeamConfig fields; get_data_dir() location for `_phase6_pending/` path composition)
    - clawteam/sprint/ (find the SprintStore / list-sprints-for-team entry point — grep `list_for_team` or similar)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-04 gstack roster shape; D-09 _phase6_pending schema — feature_flag + retro_body + personas fields)
    - .planning/phases/03-gstack-team-template-methodology-port/03-07-plugin-wiring-PLAN.md (confirm _phase6_pending/<sprint>-retro.json naming pattern from 03-07 writer)
  </read_first>
  <action>
**File: `clawteam/cli/commands.py`** — insert the `team_show` command AFTER the `team_status` command (at approximately line 1657, between `team_status` and `team_snapshot`). Do NOT modify any existing command.

```python
@team_app.command("show")
def team_show(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show the team dashboard: roster + active sprint + memory + cost rollup.

    UX-07 dashboard. For gstack-templated teams, displays all 11 specialists
    and the Phase 6 /learn placeholder count. For other templates, the memory
    and cost rows show N/A (Phase 6/7 observability is gstack-first).
    """
    from clawteam.team.manager import TeamManager
    from clawteam.team.models import get_data_dir

    config = TeamManager.get_team(team)
    if not config:
        _output(
            {"error": f"Team '{team}' not found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    # Template + leader-role (03-02 extended TeamConfig with these optional fields).
    template_name = getattr(config, "template", "") or ""
    leader_role = getattr(config, "leader_role", "") or ""

    # Active sprint: best-effort lookup via Phase 2 SprintStore. Absent or
    # empty list renders the "no active sprint" row.
    active_sprint = _team_show_active_sprint(team)

    # Memory placeholder count: glob _phase6_pending/ for gstack teams.
    memory_placeholder_count = 0
    if template_name == "gstack":
        pending_dir = get_data_dir() / "teams" / team / "_phase6_pending"
        if pending_dir.is_dir():
            memory_placeholder_count = len(list(pending_dir.glob("*-retro.json")))

    data = {
        "name": config.name,
        "template": template_name,
        "leaderRole": leader_role,
        "createdAt": config.created_at,
        "description": getattr(config, "description", ""),
        "members": [m.model_dump(by_alias=True) for m in config.members],
        "activeSprint": active_sprint,
        "memory": {
            "status": "pending_phase_6" if template_name == "gstack" else "not_applicable",
            "placeholderEntries": memory_placeholder_count,
        },
        "costRollup": {
            "status": "pending_phase_7",
            "perAgent": [],
            "totalTokens": None,
            "totalUsd": None,
        },
    }

    def _human(d):
        # Header
        console.print(f"\nTeam: [cyan]{d['name']}[/cyan]")
        if d.get("description"):
            console.print(f"  {d['description']}")
        if d.get("template"):
            leader_chip = f" (leader: [magenta]{d['leaderRole']}[/magenta])" if d.get("leaderRole") else ""
            console.print(f"  Template: [green]{d['template']}[/green]{leader_chip}")
        console.print(f"  Created: {format_timestamp(d['createdAt'])}")

        # Member roster
        members_table = Table(title=f"Members ({len(d['members'])})")
        members_table.add_column("Role / Name", style="cyan")
        members_table.add_column("ID", style="dim")
        members_table.add_column("Type")
        members_table.add_column("Joined", style="dim")
        for m in d["members"]:
            members_table.add_row(
                m.get("role", "") or m.get("name", ""),
                m.get("agentId", ""),
                m.get("agentType", ""),
                format_timestamp(m.get("joinedAt")),
            )
        console.print(members_table)

        # Active sprint row
        sprint = d["activeSprint"]
        if sprint:
            console.print(
                f"\nActive sprint: [cyan]{sprint['sprintId']}[/cyan]"
                f" — phase [green]{sprint['currentPhase']}[/green]"
                f" ({sprint['phaseIndex']})"
            )
            if sprint.get("goal"):
                console.print(f"  Goal: {sprint['goal']}")
        else:
            console.print("\nActive sprint: [dim]none — run `clawteam sprint start`[/dim]")

        # Memory placeholder
        mem = d["memory"]
        if mem["status"] == "pending_phase_6":
            console.print(
                f"\nMemory: [yellow]Phase 6 pending[/yellow]"
                f" — {mem['placeholderEntries']} entries in _phase6_pending/"
            )
        else:
            console.print("\nMemory: [dim]N/A (non-gstack template)[/dim]")

        # Cost rollup placeholder
        console.print("Cost rollup: [dim]pending Phase 7 observability[/dim]")

    _output(data, _human)


def _team_show_active_sprint(team: str) -> dict | None:
    """Look up the active sprint for a team. Returns None if no active sprint.

    Best-effort — if the sprint-listing API is absent or raises, returns None
    so the dashboard can still render.
    """
    try:
        from clawteam.sprint import conductor  # or sprint.store — executor greps
        # The exact API may be `SprintStore.list_for_team(team)` or
        # `conductor.active_sprints_for(team)`. Executor: replace with the
        # correct call discovered during Read.
        store = getattr(conductor, "SprintStore", None)
        if store is None:
            return None
        sprints = store.list_for_team(team) if hasattr(store, "list_for_team") else []
        active = next((s for s in sprints if getattr(s, "is_active", True)), None)
        if active is None:
            return None
        phases = getattr(active, "phases", []) or []
        current = getattr(active, "current_phase", "")
        idx = phases.index(current) + 1 if current in phases else 0
        total = len(phases) or 7
        return {
            "sprintId": getattr(active, "sprint_id", ""),
            "currentPhase": current,
            "phaseIndex": f"{idx}/{total}",
            "goal": getattr(active, "goal", "") or "",
        }
    except Exception:
        return None
```

**Critical details:**
- `TeamManager.get_team(team)` returns `TeamConfig | None` — guard exactly like `team_status` (line 1619-1621).
- `getattr(config, "template", "") or ""` defensively handles teams created BEFORE 03-02 landed (their TeamConfig won't have the `template` field; pydantic `extra="ignore"` gives an empty string via getattr default).
- Memory placeholder: only scan `_phase6_pending/` for gstack teams (per 03-07's filter — other templates NEVER write there).
- Sprint-listing helper is isolated in `_team_show_active_sprint` because the exact Phase 2 API name is uncertain at plan time. The helper's try/except ensures the dashboard renders even if sprint lookup fails — UX-07 requires the roster to be visible, not the sprint progress to be accurate.
- `_output(data, _human)` is the existing dual-path renderer — it respects `--json` via the global CLI flag the way `team_status` does. Do NOT add a new `--json` option to this command.
- Role field: 03-02 extended AgentDef with `role` (the 11 gstack role names); the table prefers `m.get("role")` then falls back to `m.get("name")` for non-gstack templates.

Atomic-commit discipline: single commit `feat(03-08): add clawteam team show dashboard command per UX-07`.
  </action>
  <verify>
    <automated>python -c "from clawteam.cli import commands; assert hasattr(commands, 'team_show'); assert hasattr(commands, '_team_show_active_sprint')"</automated>
  </verify>
  <acceptance_criteria>
    - Command registered under team_app: `grep -q '@team_app.command("show")' clawteam/cli/commands.py` exits 0
    - team_show function exists: `grep -q 'def team_show' clawteam/cli/commands.py` exits 0
    - Helper present: `grep -q 'def _team_show_active_sprint' clawteam/cli/commands.py` exits 0
    - TeamManager.get_team used for lookup: `grep -q 'TeamManager.get_team(team)' clawteam/cli/commands.py` exits 0
    - Not-found branch: `grep -q 'raise typer.Exit(1)' clawteam/cli/commands.py` exits 0 (pre-existing but team_show must reach this path too)
    - `_phase6_pending` dir scanned: `grep -q '_phase6_pending' clawteam/cli/commands.py` exits 0
    - Template-gstack gate on memory row: `grep -q 'template_name == "gstack"' clawteam/cli/commands.py` exits 0 (ensures non-gstack templates get N/A)
    - Cost rollup placeholder: `grep -q 'pending_phase_7' clawteam/cli/commands.py` exits 0
    - Uses _output(data, _human) pattern: `grep -q '_output(data, _human)' clawteam/cli/commands.py` exits 0
    - CLI help surfaces the command: `python -m clawteam team --help` stdout contains the literal word `show` (Typer auto-registers from the decorator)
    - `pytest tests/ -x` exits 0 (no regressions)
  </acceptance_criteria>
  <done>team_show command lives in commands.py between team_status and team_snapshot; TeamConfig loaded; _phase6_pending count surfaced; cost placeholder wired; dashboard renders via _human + JSON via _output.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend tests/test_cli_commands.py with 4 team_show tests covering dashboard render + not-found + non-gstack fallback + JSON</name>
  <files>tests/test_cli_commands.py</files>
  <read_first>
    - tests/test_cli_commands.py (existing file — identify the pattern used by existing team_status / team_snapshot tests; reuse the typer.testing.CliRunner fixture if present)
    - clawteam/cli/commands.py (Task 1 output — confirm team_show signature + JSON shape)
    - tests/conftest.py (existing team / tmp_path fixtures — reuse rather than create)
    - .planning/phases/03-gstack-team-template-methodology-port/03-02-SUMMARY.md (TeamConfig shape post-03-02 extension — template + leader_role fields; `role` per AgentDef)
  </read_first>
  <behavior>
    - Test 1 (test_team_show_gstack_dashboard): create a mock gstack team (monkeypatch TeamManager.get_team to return a TeamConfig with template="gstack", leader_role="ceo", 11 members with role=pm/ceo/...); drop 2 JSON files under tmp_path/teams/myteam/_phase6_pending/; invoke team show myteam via CliRunner; assert stdout contains "Template: gstack", "leader: ceo", all 11 role names, "Phase 6 pending — 2 entries", "pending Phase 7"
    - Test 2 (test_team_show_not_found): TeamManager.get_team returns None; assert exit code == 1; assert stderr/stdout contains "Team 'nonexistent' not found"
    - Test 3 (test_team_show_non_gstack_team): mock TeamConfig with template="software-dev", 2 members; assert stdout contains "Template: software-dev"; assert "Memory" row shows "N/A"; assert NO "_phase6_pending" literal and NO "11 entries" count in output
    - Test 4 (test_team_show_json_output): invoke with --json global flag (per whatever mechanism `_output` uses); assert parsed JSON has keys {name, template, leaderRole, members, activeSprint, memory, costRollup}; assert memory.status == "pending_phase_6" for gstack team; assert costRollup.status == "pending_phase_7"
  </behavior>
  <action>
**File: `tests/test_cli_commands.py`** — append 4 new test functions. If the existing file uses a class-based layout for team_* tests, match that class (e.g., append inside a `class TestTeamCommands` if present; otherwise ship as module-level functions).

```python
# ---------------------------------------------------------------------------
# UX-07: `clawteam team show` dashboard (03-08)
# ---------------------------------------------------------------------------


def test_team_show_gstack_dashboard(tmp_path, monkeypatch):
    """Happy path: gstack team renders roster + template + memory placeholder + cost stub."""
    from types import SimpleNamespace
    from typer.testing import CliRunner
    from clawteam.cli.commands import app
    import clawteam.team.models as team_models
    import clawteam.team.manager as team_manager

    # Mock 11-member gstack team
    gstack_roles = [
        "pm", "ceo", "eng-mgr", "designer", "dx-lead",
        "engineer", "reviewer", "qa", "security", "shipper", "sre",
    ]
    members = [
        SimpleNamespace(
            model_dump=lambda self=None, by_alias=False, _r=r: {
                "name": _r, "role": _r, "agentId": f"{_r}-1",
                "agentType": "general-purpose", "joinedAt": "2026-04-20T10:00:00Z",
            }
        )
        for r in gstack_roles
    ]
    config = SimpleNamespace(
        name="myteam",
        description="gstack test team",
        template="gstack",
        leader_role="ceo",
        lead_agent_id="ceo-1",
        created_at="2026-04-20T09:00:00Z",
        members=members,
    )
    monkeypatch.setattr(team_manager.TeamManager, "get_team", staticmethod(lambda name: config))
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)

    # Drop 2 placeholder files
    pending = tmp_path / "teams" / "myteam" / "_phase6_pending"
    pending.mkdir(parents=True)
    (pending / "sprint-001-retro.json").write_text('{"feature_flag":"phase6_learn_pending"}')
    (pending / "sprint-002-retro.json").write_text('{"feature_flag":"phase6_learn_pending"}')

    runner = CliRunner()
    result = runner.invoke(app, ["team", "show", "myteam"])

    assert result.exit_code == 0, result.output
    assert "Template:" in result.output and "gstack" in result.output
    assert "leader:" in result.output and "ceo" in result.output
    # All 11 roles present in roster
    for role in gstack_roles:
        assert role in result.output, f"role {role!r} missing from dashboard"
    # Memory placeholder count
    assert "Phase 6 pending" in result.output
    assert "2 entries" in result.output or "2\u00a0entries" in result.output
    # Cost rollup stub
    assert "Phase 7" in result.output


def test_team_show_not_found(monkeypatch):
    """Typer.Exit(1) on unknown team name with human-readable error."""
    from typer.testing import CliRunner
    from clawteam.cli.commands import app
    import clawteam.team.manager as team_manager

    monkeypatch.setattr(team_manager.TeamManager, "get_team", staticmethod(lambda name: None))

    runner = CliRunner()
    result = runner.invoke(app, ["team", "show", "nonexistent"])

    assert result.exit_code == 1
    assert "not found" in result.output.lower()
    assert "nonexistent" in result.output


def test_team_show_non_gstack_team(tmp_path, monkeypatch):
    """Non-gstack template renders roster but shows N/A for memory row."""
    from types import SimpleNamespace
    from typer.testing import CliRunner
    from clawteam.cli.commands import app
    import clawteam.team.manager as team_manager
    import clawteam.team.models as team_models

    members = [
        SimpleNamespace(
            model_dump=lambda self=None, by_alias=False, _n=n: {
                "name": _n, "role": "", "agentId": f"{_n}-1",
                "agentType": "general-purpose", "joinedAt": "2026-04-20T10:00:00Z",
            }
        )
        for n in ("lead", "eng")
    ]
    config = SimpleNamespace(
        name="legacy-team",
        description="software-dev team",
        template="software-dev",
        leader_role="",
        lead_agent_id="lead-1",
        created_at="2026-04-20T09:00:00Z",
        members=members,
    )
    monkeypatch.setattr(team_manager.TeamManager, "get_team", staticmethod(lambda name: config))
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(app, ["team", "show", "legacy-team"])

    assert result.exit_code == 0, result.output
    assert "software-dev" in result.output
    # Memory row shows N/A (non-gstack template)
    assert "N/A" in result.output or "n/a" in result.output.lower()
    # No gstack-specific placeholder chatter
    assert "_phase6_pending" not in result.output


def test_team_show_json_output(tmp_path, monkeypatch):
    """--json output shape: keys match the documented contract."""
    import json
    from types import SimpleNamespace
    from typer.testing import CliRunner
    from clawteam.cli.commands import app
    import clawteam.team.manager as team_manager
    import clawteam.team.models as team_models

    members = [
        SimpleNamespace(
            model_dump=lambda self=None, by_alias=False, _r=r: {
                "name": _r, "role": _r, "agentId": f"{_r}-1",
                "agentType": "general-purpose", "joinedAt": "2026-04-20T10:00:00Z",
            }
        )
        for r in ("pm", "ceo")
    ]
    config = SimpleNamespace(
        name="json-team",
        description="json test",
        template="gstack",
        leader_role="ceo",
        lead_agent_id="ceo-1",
        created_at="2026-04-20T09:00:00Z",
        members=members,
    )
    monkeypatch.setattr(team_manager.TeamManager, "get_team", staticmethod(lambda name: config))
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)

    runner = CliRunner()
    # Executor: the existing _output helper selects JSON via a global flag/env.
    # If the app uses --json as a root-level option: `app --json team show ...`.
    # If it uses CLAWTEAM_OUTPUT=json env: set via `env` kwarg. Adapt to match
    # whatever team_status does in its existing test.
    result = runner.invoke(app, ["--json", "team", "show", "json-team"])
    if result.exit_code != 0:
        # Fallback path if --json isn't a root option; try env var
        result = runner.invoke(app, ["team", "show", "json-team"], env={"CLAWTEAM_OUTPUT": "json"})

    assert result.exit_code == 0, result.output

    # Parse the last JSON-looking line (conventional _output behavior)
    json_lines = [ln for ln in result.output.splitlines() if ln.strip().startswith("{")]
    assert json_lines, f"no JSON line in output: {result.output!r}"
    data = json.loads(json_lines[-1])

    assert data["name"] == "json-team"
    assert data["template"] == "gstack"
    assert data["leaderRole"] == "ceo"
    assert isinstance(data["members"], list)
    assert "activeSprint" in data
    assert data["memory"]["status"] == "pending_phase_6"
    assert data["costRollup"]["status"] == "pending_phase_7"
```

**Critical details:**
- `CliRunner` is the standard Typer test harness. If `tests/test_cli_commands.py` already imports it at module top, reuse the existing instance; don't re-import.
- `SimpleNamespace`-based config mocks avoid depending on the exact pydantic TeamConfig class (03-02 adds fields; the SimpleNamespace approach degrades gracefully if the class shape drifts).
- Test 4 has a fallback path for `--json` flag discovery: the executor MUST adapt to match how `team_status`'s existing tests invoke the JSON mode. If neither path works, grep `_output(` at commands.py top for the real switch mechanism.
- `result.output` from CliRunner captures both stdout and stderr by default (conftest confirms this in existing tests).
- NO test here verifies the active-sprint row — that's a Phase 2 integration concern. `_team_show_active_sprint` returns None by default, which the human renderer degrades to "none — run sprint start" (asserted indirectly via exit_code == 0).

Atomic-commit discipline: single commit `test(03-08): add 4 team_show dashboard tests covering gstack render + not-found + non-gstack fallback + JSON shape`.
  </action>
  <verify>
    <automated>pytest tests/test_cli_commands.py -k 'team_show' -x</automated>
  </verify>
  <acceptance_criteria>
    - All 4 new tests pass: `pytest tests/test_cli_commands.py -k 'team_show' -x` exits 0
    - 4 test functions exist: `grep -c '^def test_team_show_' tests/test_cli_commands.py` outputs `4` (or ≥ 4 if inside a class — grep `    def test_team_show_` as class method)
    - gstack dashboard test: `grep -q 'def test_team_show_gstack_dashboard' tests/test_cli_commands.py` exits 0
    - not-found test: `grep -q 'def test_team_show_not_found' tests/test_cli_commands.py` exits 0
    - non-gstack fallback test: `grep -q 'def test_team_show_non_gstack_team' tests/test_cli_commands.py` exits 0
    - JSON shape test: `grep -q 'def test_team_show_json_output' tests/test_cli_commands.py` exits 0
    - JSON test asserts memory status: `grep -q 'pending_phase_6' tests/test_cli_commands.py` exits 0
    - JSON test asserts cost status: `grep -q 'pending_phase_7' tests/test_cli_commands.py` exits 0
    - `pytest tests/ -x` exits 0 (full suite green — no regressions to existing team_status / team_snapshot tests)
  </acceptance_criteria>
  <done>4 new team_show tests cover UX-07 happy path + error branch + non-gstack BC + JSON shape; suite stays green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Team name argument -> filesystem path | `team_show` receives `team: str` from Typer. `TeamManager.get_team(team)` + `get_data_dir() / "teams" / team / "_phase6_pending"` concatenation both run on this user input. BC from 03-07's `_write_phase6_pending` guard: team names containing `/` or `..` never had placeholder files written, so the glob simply returns empty — no traversal downstream. The 03-07 write guard IS the full mitigation for T-08-01; this command is read-only and doesn't amplify. |
| `_phase6_pending` dir glob -> dashboard output | Dashboard surfaces the COUNT of placeholder JSON files, not their contents. Even if an attacker somehow planted a crafted file in `_phase6_pending/` (e.g., by compromising `~/.clawteam/`), only the count reaches stdout — no secrets from the retro bodies leak through the dashboard. (Phase 6 when it reads the actual content will need its own scrubbing — documented in 03-07 T-07-05.) |
| TeamConfig.members -> Rich Table rendering | Member metadata (name, role, agentId, agentType) is user-provided at team-creation time. Rendering via `rich.Table` escapes markup by default; no format-string attacks. Phase 0 + Phase 2 test coverage already validates rich.Table for existing commands. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-08-01 | Tampering | Path traversal via team name (e.g., `clawteam team show "../"`) reading files outside the teams directory | mitigate (inherits 03-07) | `TeamManager.get_team(team)` returns None for non-existent teams (the lookup path itself is not vulnerable to traversal since it's keyed by name, not path). The `_phase6_pending` glob ONLY runs for `template_name == "gstack"` — and non-gstack teams can't reach this code. For gstack teams: `get_data_dir() / "teams" / team / "_phase6_pending"` is path-safe because 03-07's writer already rejected team names with `/` or `..` at write-time; the glob sees the directory that was (or wasn't) created. Read path adds no new surface. |
| T-08-02 | Information Disclosure | Team dashboard surfaces team description + member names + active sprint goal — could leak sensitive internal info if `--json` output is piped to a log aggregator | accept | Same disclosure surface as existing `team status` command (commands.py:1611-1656). Users with shell access already have filesystem access to TeamConfig — the CLI surface doesn't add disclosure. Phase 7 cost dashboard will add per-agent cost data; if that's sensitive a future plan adds a `--redact` flag. |
| T-08-03 | Denial of Service | Glob over `_phase6_pending/` on a team with millions of retro files blocks the CLI | mitigate | `list(pending_dir.glob("*-retro.json"))` materializes into memory. A realistic upper bound is 1 entry per Reflect-phase completion per sprint — a team running 10 sprints a day hits 3,650/year. `len(list(...))` on 3,650 entries is <10ms on commodity SSD. Phase 6 backfill drains `_phase6_pending/` on first /learn write, bounding the long-term count. If observed in the wild, switch to `sum(1 for _ in pending_dir.iterdir() if _.name.endswith('-retro.json'))` to avoid the intermediate list. |
| T-08-04 | Spoofing | A malicious template file declares `leader_role = "attacker"` to surface misleading info in the dashboard | accept | Templates are repo-committed (gstack.toml lives under `clawteam/templates/`, reviewed by CODEOWNERS). Users running non-default templates authored the template themselves or trust the distributor. No additional in-plan mitigation; Phase 0 supply-chain posture (QUALITY-14 regression matrix) covers the broader risk. |

</threat_model>

<verification>
- `clawteam team show <name>` command registered: `python -m clawteam team show --help` exits 0 and stdout contains "dashboard"
- Dashboard rendered for gstack team: test_team_show_gstack_dashboard asserts 11 roles + template + leader + memory count + cost stub
- Not-found returns exit 1: test_team_show_not_found asserts exit code + error message
- Non-gstack team falls back gracefully: test_team_show_non_gstack_team asserts "N/A" in memory row, no `_phase6_pending` references
- JSON shape matches contract: test_team_show_json_output asserts all documented keys (name, template, leaderRole, members, activeSprint, memory, costRollup) + memory.status == "pending_phase_6" + costRollup.status == "pending_phase_7"
- No regressions: `pytest tests/ -x` exits 0
- Command lives in correct location: inserted between team_status (line ~1656) and team_snapshot (line ~1659) — preserves alphabetical-ish ordering of the team_app subcommand group
- Cross-template BC: non-gstack teams reach the memory/cost rows with "N/A" / "pending" placeholders, never crash
</verification>

<success_criteria>
- UX-07 achieved: `clawteam team show myteam` displays member list + memory highlights (placeholder count) + active sprint progress + per-agent cost rollup (placeholder). All 11 gstack roles visible for gstack teams.
- Read-only command (no state modification) — safe to run at any time
- JSON mode supported via existing `_output` helper (consistent with UX-09 machine-readable discipline)
- Cross-template BC preserved: non-gstack teams see roster + sprint row; memory + cost rows show "N/A" / "pending" gracefully
- Phase 6 + Phase 7 upgrade paths clear: memory row wire-frame trivially swaps "Phase 6 pending — N entries" → actual memory retrieval; cost row swaps "Phase 7 pending" → per-agent token table (both already documented in 03-07's integration notes)
- `pytest tests/ -x` exits 0
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-08-SUMMARY.md` covering:
- `team_show` function location + LOC (lines [start]-[end] in commands.py)
- Dashboard sections (4 — roster, active sprint, memory, cost) + their data sources
- JSON output shape (key list with type per key)
- Confirmation that 03-09 (cross-template regression) will extend this test file's coverage by asserting non-gstack teams render the dashboard with "N/A" rows and no gstack-specific output
- Phase 6 upgrade path: exactly what to change when real /learn ships (the `pending_phase_6` literal + the _phase6_pending glob are the two swap points)
- Phase 7 upgrade path: exactly what to change when cost observability ships (`pending_phase_7` literal + costRollup dict shape)
</output>
