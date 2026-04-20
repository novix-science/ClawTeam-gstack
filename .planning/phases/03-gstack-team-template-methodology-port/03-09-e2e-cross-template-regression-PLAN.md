---
phase: 03-gstack-team-template-methodology-port
plan: 09
type: execute
wave: 4
depends_on: [03-02, 03-07, 03-08]
files_modified:
  - tests/test_gstack_team_spawn.py
  - tests/test_template_regression_matrix.py
autonomous: true
requirements: [TEAM-03, UX-01]
must_haves:
  truths:
    - "End-to-end `clawteam team spawn gstack --name <n>` works: 11 agent worktrees created; TeamConfig persisted with template=gstack + leader_role=ceo (UX-01 + TEAM-03)"
    - "Each of 11 agents gets its own `WorkspaceManager.create_workspace` call — per-agent desk worktrees persist across sprints (TEAM-03)"
    - "GstackSprintPlugin is loaded globally (via PluginManager.discover) but its event handlers NO-OP for each of the 6 existing templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) — CORE-03 + QUALITY-14 + success-criterion-#2 backwards compat"
    - "Phase 0 regression matrix extended: each of 6 existing template spawns succeeds with GstackSprintPlugin loaded; existing test coverage for each template remains green"
    - "Delete invariant (D-07) verified: removing clawteam/plugins/gstack_sprint_plugin.py + clawteam/templates/gstack.toml + clawteam/templates/gstack/ leaves the rest of the codebase passing (strict deselection run in CI smoke — documented test pattern only, not run in this plan)"
  artifacts:
    - path: "tests/test_gstack_team_spawn.py"
      provides: "Un-xfailed: test_eleven_worktrees_created (TEAM-03); test_team_spawn_gstack_end_to_end (UX-01 integration)"
      contains: "test_team_spawn_gstack_end_to_end"
    - path: "tests/test_template_regression_matrix.py"
      provides: "Extended with 6 × cross-template isolation tests (one per existing template) asserting GstackSprintPlugin does not contaminate non-gstack spawns"
      contains: "test_software_dev_unaffected_by_gstack_plugin"
  key_links:
    - from: "tests/test_gstack_team_spawn.py::test_eleven_worktrees_created"
      to: "clawteam/workspace/manager.py::WorkspaceManager.create_workspace"
      via: "Integration assertion: 11 per-agent worktrees created under <data_dir>/teams/<team>/agents/<role>/"
      pattern: "create_workspace"
    - from: "tests/test_gstack_team_spawn.py::test_team_spawn_gstack_end_to_end"
      to: "clawteam team spawn gstack --name <n>"
      via: "Typer CliRunner driving the full spawn flow; asserts TeamConfig persisted with template=gstack + 11 members + leader_role=ceo"
      pattern: "clawteam team spawn gstack"
    - from: "tests/test_template_regression_matrix.py"
      to: "clawteam/plugins/gstack_sprint_plugin.py"
      via: "Loads GstackSprintPlugin then spawns each of the 6 existing templates; asserts non-gstack teams do NOT see gstack phases in PhaseRegistry scope, do NOT trigger Reflect-phase placeholder writes"
      pattern: "test_*_unaffected_by_gstack_plugin"
---

<objective>
Close out Phase 3 by (1) un-xfailing `tests/test_gstack_team_spawn.py` (03-01 Wave-0 scaffold) with real end-to-end assertions for TEAM-03 (11 per-agent worktrees) + UX-01 (`clawteam team spawn gstack --name <n>` works end-to-end); and (2) extending `tests/test_template_regression_matrix.py` (existing, pre-Phase-3) with 6 × cross-template isolation tests — one per existing template — that verify the Phase 0 regression matrix stays green with GstackSprintPlugin loaded.

Purpose: this is the plan where Phase 3's two meta-claims become verifiable assertions in CI:
- **"The product ships"** — a user runs `clawteam team spawn gstack --name acme` and sees 11 named specialists with persistent worktrees and all the substrate (prompts, envelopes, schemas, plugin) wired through.
- **"Nothing else breaks"** — each of software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room continues to spawn + advance phases + pass existing tests with GstackSprintPlugin loaded (Pitfall 14 + QUALITY-14 + success-criterion-#2 + success-criterion-#7 — the full backwards-compat contract).

**Why these two test files pair in one plan:** Both test the SAME claim from opposite directions. `test_gstack_team_spawn.py` verifies the positive: "spawn gstack, see gstack". `test_template_regression_matrix.py` verifies the negative: "spawn anything-else, do NOT see gstack". A single plan owning both keeps the symmetry and prevents drift between the positive and negative coverage.

**Delete-invariant spot-check (documented, not run):** The plan documents a `make check-delete-invariant` pattern (executor ships this as a shell-only check or a pytest conditional). The invariant is: `rm clawteam/plugins/gstack_sprint_plugin.py clawteam/templates/gstack.toml && rm -rf clawteam/templates/gstack/ && pytest tests/ -x --deselect tests/test_gstack_*.py --deselect tests/test_envelope_personas.py` still exits 0 — the rest of the codebase keeps running when all gstack-specific files are deleted. This invariant is documented in the verification section; running it in CI requires a second working-copy checkout, so the executor notes it as a manual pre-release check rather than an automated test.

**Active-sprint goal coverage:** Success-criterion #5 (Reflect-phase triggers `/learn` stub placeholder) is covered by 03-07's `test_reflect_phase_learn_stub_writes_placeholder` (unit-level handler test). This plan's e2e test does NOT re-test the Reflect-phase write path — that belongs to 03-07. The e2e test verifies up through UX-01 / TEAM-03, stopping at the point where 03-07's unit test takes over.

Output:
- `tests/test_gstack_team_spawn.py` de-xfailed with 2 active tests
- `tests/test_template_regression_matrix.py` extended with 6 × cross-template isolation tests + 1 aggregate regression test
- No new test infrastructure (reuse existing CliRunner, tmp_path, and the regression-matrix fixture from pre-Phase-3)
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
@.planning/phases/03-gstack-team-template-methodology-port/03-01-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-02-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-07-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-08-SUMMARY.md

<interfaces>
<!-- Contracts the executor consumes from the full Phase 3 stack + the existing regression matrix. -->

From tests/test_gstack_team_spawn.py (03-01 output — Wave-0 scaffold):
  - xfailed skeletons for test_eleven_worktrees_created + test_team_spawn_gstack_end_to_end
  - Module-level PROMPTS_DIR + FIXTURES_DIR constants (may not be needed for this file; prefer test-local paths)
  - Expected convention: typer.testing.CliRunner + tmp_path-isolated get_data_dir

From tests/test_template_regression_matrix.py (existing — pre-Phase-3):
  - Structure must be read during Task 3 Read pass; expected parametrized test over the 6 existing templates
  - Phase 0 QUALITY-14 invariant: spawning each template succeeds + existing template tests stay green
  - Likely signature: `@pytest.mark.parametrize("template", EXISTING_TEMPLATES)` — executor adapts if the file uses a different shape

6 existing templates (canonical list — CONTEXT.md §Cross-template isolation + ROADMAP Phase 0 + Phase 3 success criterion #7):
  ["software-dev", "hedge-fund", "code-review", "harness-default", "research-paper", "strategy-room"]

From clawteam/cli/commands.py (existing `team spawn` command — verify shape during Task 2 Read):
  - Entry point: `clawteam team spawn <template> --name <n>` (or equivalent — executor greps `@team_app.command("spawn")`)
  - Drives TemplateDef load + PluginManager plugin load + TeamManager.create_team + WorkspaceManager.create_workspace × N members

From clawteam/plugins/manager.py::PluginManager (Phase 1 substrate):
  - `discover()` lists installed plugins
  - Loading mechanism: entry points / config / local dirs (lines 20-80 per earlier Read)
  - GstackSprintPlugin registers globally when discovered; hooks no-op for non-gstack teams (03-07 consumption-layer isolation)

From clawteam/workspace/manager.py::WorkspaceManager.create_workspace (existing — used by TeamManager):
  - Creates per-agent worktree desk
  - Path: `<data_dir>/teams/<team>/agents/<role>/` (per RESEARCH.md + PATTERNS.md notes)

From clawteam/plugins/gstack_sprint_plugin.py (03-07 output):
  - GstackSprintPlugin() instance
  - GSTACK_ROLES = 11-element list
  - GSTACK_PHASES = 7-element list
  - `_on_phase_transition` filters `template_name != "gstack"` (the guard under test in cross-template isolation)
  - `_write_phase6_pending` (the side-effect under negative test — non-gstack templates MUST NOT trigger this)

6-template expected phase sets (from each template's TOML — executor verifies during Task 3 Read by running `TemplateDef` load on each):
  - Each existing template has its own phase list (NOT the 7 gstack phases)
  - None of them declare `template.phases = ["think", "plan", ...]`
  - Cross-template isolation test asserts this via: `spawn <template> -> scan TeamConfig.phases -> assert "think" not in phases OR gstack phases NOT in the iteration path`

Regression assertion shape (parametrize fixture):
  for each template in EXISTING_TEMPLATES:
    1. Load TemplateDef for <template>
    2. Run `clawteam team spawn <template> --name test-<template>` (or TeamManager.create_team directly)
    3. Assert TeamConfig.template == <template> (NOT "gstack")
    4. Assert TeamConfig.members have the template's expected roles (NOT gstack's 11)
    5. With GstackSprintPlugin loaded: emit a fake PhaseTransition(phase_target="reflect", team_name=...); assert NO file under <data_dir>/teams/<team>/_phase6_pending/
    6. Run the template's existing test file (if any) and assert exit 0 (OR reuse the pre-existing regression matrix invocation and assert it stays green with gstack plugin loaded)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Un-xfail tests/test_gstack_team_spawn.py — 11-worktree assertion for TEAM-03</name>
  <files>tests/test_gstack_team_spawn.py</files>
  <read_first>
    - tests/test_gstack_team_spawn.py (03-01 output — xfailed test_eleven_worktrees_created + test_team_spawn_gstack_end_to_end stubs; check for module-level constants / fixtures)
    - clawteam/team/manager.py (TeamManager.create_team signature — see how 03-02 extended it with memory-dir pre-creation per D-05)
    - clawteam/workspace/manager.py (WorkspaceManager.create_workspace signature + return shape — per-agent worktree path convention)
    - clawteam/templates/gstack.toml (03-02 output — 11 agent roster with role + prompt_file per row)
    - clawteam/templates/__init__.py (03-02 output — extended TemplateDef + AgentDef; confirm `role` + `prompt_file` field names)
    - tests/conftest.py (existing tmp_path or clawteam-data-dir fixture — reuse)
  </read_first>
  <behavior>
    - Test 1 (test_eleven_worktrees_created): invoke TeamManager.create_team with gstack TemplateDef; assert 11 worktree directories exist under `<tmp_path>/teams/<team>/agents/<role>/` — one per gstack role; assert each directory has a `.git` worktree marker (or whatever WorkspaceManager uses as the per-agent desk signature)
    - Test 2 (remove xfail if 03-01 shipped a placeholder body for test_team_spawn_gstack_end_to_end — this plan's Task 2 fills it with the real integration assertions)
    - The test must use tmp_path + monkeypatched get_data_dir — do NOT write to the user's real ~/.clawteam/
  </behavior>
  <action>
**File: `tests/test_gstack_team_spawn.py`** — remove the `@pytest.mark.xfail` decorator from `test_eleven_worktrees_created` and fill the body.

```python
def test_eleven_worktrees_created(tmp_path, monkeypatch):
    """TEAM-03: spawning a gstack team creates 11 per-agent worktree desks.

    Each desk is an isolated worktree (not a bare directory) so per-agent
    Git-tracked state persists across sprints. The underlying create_workspace
    call is unchanged from Phase 0; this test verifies the gstack template
    drives 11 calls — one per role.
    """
    import clawteam.team.models as team_models
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)

    from clawteam.team.manager import TeamManager
    from clawteam.templates import load_template

    gstack_template = load_template("gstack")
    assert gstack_template.name == "gstack"
    assert len(gstack_template.agents) == 11, (
        f"gstack.toml must declare 11 agents, got {len(gstack_template.agents)}"
    )

    # Create the team — this drives WorkspaceManager.create_workspace per agent
    team_config = TeamManager.create_team(
        name="spawn-test",
        template=gstack_template,
    )

    # Verify 11 worktree dirs exist, one per canonical role.
    expected_roles = {
        "pm", "ceo", "eng-mgr", "designer", "dx-lead",
        "engineer", "reviewer", "qa", "security", "shipper", "sre",
    }
    agents_root = tmp_path / "teams" / "spawn-test" / "agents"
    assert agents_root.is_dir(), f"agents root missing: {agents_root}"

    actual_roles = {p.name for p in agents_root.iterdir() if p.is_dir()}
    missing = expected_roles - actual_roles
    extra = actual_roles - expected_roles
    assert not missing, f"missing agent desks: {missing}"
    assert not extra, f"unexpected agent desks: {extra}"

    # Each desk should be Git-tracked (worktree or plain git repo — both acceptable)
    for role in expected_roles:
        desk = agents_root / role
        git_marker = desk / ".git"
        assert git_marker.exists(), f"{role}'s desk missing .git worktree marker: {desk}"

    # Per-role memory dirs pre-created (D-05 + 03-02)
    memory_root = tmp_path / "teams" / "spawn-test" / "memory"
    assert memory_root.is_dir(), "memory root not pre-created by TeamManager.create_team"
    for role in expected_roles:
        assert (memory_root / role).is_dir(), f"{role} memory dir not pre-created"

    # TeamConfig round-trips with template + leader_role from 03-02 extension
    assert getattr(team_config, "template", "") == "gstack"
    assert getattr(team_config, "leader_role", "") == "ceo"
```

**Critical details:**
- `load_template("gstack")` is the substrate function that reads `clawteam/templates/gstack.toml` and returns a `TemplateDef` (03-02's extension). If the actual function name differs, the executor greps `clawteam/templates/__init__.py` and adapts.
- `TeamManager.create_team(name=..., template=...)` mirrors existing callers (team_status's cousins in commands.py). 03-02 extended it with the per-role memory-dir pre-creation step (D-05) — this test exercises that.
- The `.git` worktree marker check is tolerant: either a worktree stub (file) or a real `.git` dir (subdirectory) is acceptable — both are valid Git layouts. The `Path.exists()` check covers both.
- Memory-dir assertion is a regression on 03-02 D-05 (per-role mkdir during create_team). If 03-02's implementation pre-creates under a different path layout, adapt.

Atomic-commit discipline: single commit `test(03-09): un-xfail test_eleven_worktrees_created with 11-desk + memory + TeamConfig assertions`.
  </action>
  <verify>
    <automated>pytest tests/test_gstack_team_spawn.py::test_eleven_worktrees_created -x</automated>
  </verify>
  <acceptance_criteria>
    - Test passes: `pytest tests/test_gstack_team_spawn.py::test_eleven_worktrees_created -x` exits 0
    - xfail removed: `grep -c '@pytest.mark.xfail' tests/test_gstack_team_spawn.py` outputs at most `0` (or `1` remaining for test_team_spawn_gstack_end_to_end before Task 2 un-xfails that too; Task 2's criteria take it to `0`)
    - 11 role assertions: `grep -q 'pm.*ceo.*eng-mgr' tests/test_gstack_team_spawn.py` exits 0
    - Memory-dir regression on 03-02 D-05: `grep -q 'memory_root' tests/test_gstack_team_spawn.py` exits 0
    - template round-trip: `grep -q 'team_config.*template.*gstack' tests/test_gstack_team_spawn.py` exits 0
    - `pytest tests/ -x` exits 0 (no regressions)
  </acceptance_criteria>
  <done>test_eleven_worktrees_created active; 11 desks + per-role memory dirs + TeamConfig template/leader_role round-trip verified; TEAM-03 + 03-02 D-05 anchored.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Un-xfail test_team_spawn_gstack_end_to_end — UX-01 CliRunner integration</name>
  <files>tests/test_gstack_team_spawn.py</files>
  <read_first>
    - tests/test_gstack_team_spawn.py (Task 1 output — append Test 2 below Test 1; do NOT duplicate fixtures)
    - clawteam/cli/commands.py (find `team spawn` command signature — typer.Argument for template + `--name <n>` option; confirm by grep `@team_app.command("spawn")`)
    - tests/test_cli_commands.py (existing team-spawn tests if present — reuse their CliRunner pattern)
  </read_first>
  <behavior>
    - Test runs `clawteam team spawn gstack --name gstack-e2e` via CliRunner with monkeypatched get_data_dir
    - Asserts exit_code == 0 (UX-01 success-criterion #1)
    - Asserts stdout mentions the team name + 11-agent count (user-facing signal that spawn worked)
    - Asserts that after spawn, `clawteam team show gstack-e2e` (03-08) renders the dashboard with 11 members and "Template: gstack"
    - Asserts 11 per-agent worktrees exist on disk (redundancy with Task 1 is intentional — catches regressions to the CLI wiring even if the direct-TeamManager path still works)
  </behavior>
  <action>
**Append to `tests/test_gstack_team_spawn.py`:**

```python
def test_team_spawn_gstack_end_to_end(tmp_path, monkeypatch):
    """UX-01 + success-criterion #1: `clawteam team spawn gstack --name <n>` works end-to-end.

    Exercises the full user path from CLI invocation -> template load -> 11
    worktree creations -> TeamConfig persistence -> dashboard render via team show.
    """
    import clawteam.team.models as team_models
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)

    from typer.testing import CliRunner
    from clawteam.cli.commands import app

    runner = CliRunner()

    # Part A: spawn
    spawn_result = runner.invoke(
        app, ["team", "spawn", "gstack", "--name", "gstack-e2e"]
    )
    assert spawn_result.exit_code == 0, (
        f"team spawn gstack failed:\nexit={spawn_result.exit_code}\nstdout={spawn_result.output}"
    )
    # User-facing signal: team name + 11-agent count somewhere in output
    assert "gstack-e2e" in spawn_result.output
    # Executor: some CLIs print "created team" / "spawned 11 agents" — adapt
    # the assertion to whatever the existing team spawn command outputs.
    # At minimum, exit_code 0 is the contract.

    # Part B: 11 worktrees on disk (redundant with Task 1's direct-API test
    # but covers the CLI-to-substrate wiring)
    agents_root = tmp_path / "teams" / "gstack-e2e" / "agents"
    assert agents_root.is_dir(), f"agents root missing after CLI spawn: {agents_root}"
    role_dirs = {p.name for p in agents_root.iterdir() if p.is_dir()}
    expected_roles = {
        "pm", "ceo", "eng-mgr", "designer", "dx-lead",
        "engineer", "reviewer", "qa", "security", "shipper", "sre",
    }
    assert role_dirs == expected_roles, (
        f"expected 11 gstack role desks, got {role_dirs}"
    )

    # Part C: team show renders the dashboard
    show_result = runner.invoke(app, ["team", "show", "gstack-e2e"])
    assert show_result.exit_code == 0, (
        f"team show failed after spawn:\n{show_result.output}"
    )
    assert "gstack" in show_result.output  # template name surfaced
    # All 11 roles in the dashboard output
    for role in expected_roles:
        assert role in show_result.output, f"role {role!r} missing from dashboard"
```

**Critical details:**
- Uses typer.testing.CliRunner — same harness as 03-08's test_team_show_*. If an existing fixture provides a pre-constructed CliRunner + monkeypatched data dir, reuse it.
- The `spawn_result.output` assertion is intentionally minimal ("gstack-e2e" in output) because different team-spawn commands produce different success messaging. Exit code 0 is the hard contract; the string check is a smoke signal.
- The 3-part structure (spawn → disk → dashboard render) exercises the integration surface end-to-end. If any of the 3 parts fails the test identifies which boundary broke.
- If the `team spawn` CLI doesn't accept `--name` as the agent-team name flag, grep the command definition and adapt (may be `--team-name` or positional).

Atomic-commit discipline: single commit `test(03-09): un-xfail test_team_spawn_gstack_end_to_end with CLI spawn + worktree + dashboard integration`.
  </action>
  <verify>
    <automated>pytest tests/test_gstack_team_spawn.py -x</automated>
  </verify>
  <acceptance_criteria>
    - Both tests pass: `pytest tests/test_gstack_team_spawn.py -x` exits 0 (2 tests minimum)
    - No remaining xfails: `grep -c '@pytest.mark.xfail' tests/test_gstack_team_spawn.py` outputs `0`
    - Two active test functions: `grep -c '^def test_' tests/test_gstack_team_spawn.py` outputs at least `2`
    - CLI-driven test: `grep -q 'CliRunner' tests/test_gstack_team_spawn.py` exits 0
    - Spawn invocation: `grep -q 'team.*spawn.*gstack' tests/test_gstack_team_spawn.py` exits 0
    - Dashboard integration: `grep -q 'team.*show' tests/test_gstack_team_spawn.py` exits 0
    - `pytest tests/ -x` exits 0 (full suite green)
  </acceptance_criteria>
  <done>test_team_spawn_gstack_end_to_end active; CLI → 11 worktrees → dashboard integration chain covered; UX-01 anchored end-to-end.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Extend tests/test_template_regression_matrix.py with 6 × cross-template isolation tests</name>
  <files>tests/test_template_regression_matrix.py</files>
  <read_first>
    - tests/test_template_regression_matrix.py (existing file — identify current parametrize shape; find EXISTING_TEMPLATES constant or literal list; match function-naming convention)
    - clawteam/plugins/gstack_sprint_plugin.py (03-07 output — GstackSprintPlugin + GSTACK_PHASES constant + _on_phase_transition for negative test)
    - clawteam/plugins/manager.py (PluginManager — discover + load mechanism; how to force gstack plugin to be loaded for this test suite)
    - clawteam/templates/software-dev.toml (one of 6 existing templates — confirm its phase list + role list to contrast against gstack's)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (success criterion #2 + #7 wording)
  </read_first>
  <behavior>
    - Parametrized over 6 existing templates: ("software-dev", "hedge-fund", "code-review", "harness-default", "research-paper", "strategy-room")
    - For each template: spawn it with GstackSprintPlugin loaded; assert the resulting TeamConfig has `template = <existing>` (NOT gstack); assert its member list does NOT contain the 11 gstack role names; assert emitting a fake PhaseTransition(target="reflect", team_name=<this template's team>) does NOT create a file under `_phase6_pending/` (03-07 T-07-01 consumption-layer isolation)
    - One aggregate test: `test_all_six_existing_templates_parse_with_gstack_loaded` — loads every template's TemplateDef with GstackSprintPlugin imported; asserts zero import errors + zero phase-registry conflicts
    - Preserve existing regression-matrix tests verbatim (do NOT edit them)
  </behavior>
  <action>
**File: `tests/test_template_regression_matrix.py`** — append new tests below whatever already exists. Do NOT edit existing test bodies.

```python
# ===========================================================================
# Phase 3 cross-template isolation (success criteria #2 + #7 + QUALITY-14)
# ===========================================================================
#
# These tests verify that loading GstackSprintPlugin (Phase 3) does NOT
# contaminate any of the 6 existing templates. Spawning each existing template
# must work identically to pre-Phase-3 — same phases, same roles, no Reflect-
# phase Phase-6-placeholder writes, no gstack-specific artifacts on disk.

import pytest

EXISTING_TEMPLATES_PHASE3 = [
    "software-dev",
    "hedge-fund",
    "code-review",
    "harness-default",
    "research-paper",
    "strategy-room",
]


@pytest.fixture
def gstack_plugin_loaded():
    """Load GstackSprintPlugin globally for the duration of the test.

    Mirrors the plugin-load mechanics PluginManager.discover() performs at
    startup. Tests under this fixture exercise the post-load state.
    """
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from types import SimpleNamespace
    plugin = GstackSprintPlugin()
    # Minimal fake ctx — bus.subscribe is a no-op for isolation tests since
    # we drive _on_phase_transition directly.
    ctx = SimpleNamespace(
        bus=SimpleNamespace(subscribe=lambda *a, **k: None),
    )
    plugin.on_register(ctx)
    yield plugin


@pytest.mark.parametrize("template", EXISTING_TEMPLATES_PHASE3)
def test_existing_template_spawns_unaffected_by_gstack_plugin(
    template, tmp_path, monkeypatch, gstack_plugin_loaded,
):
    """For each of the 6 existing templates: spawning it with GstackSprintPlugin
    loaded succeeds AND produces a TeamConfig with the template's own shape
    (NOT gstack's 11-role roster or 7-phase list).

    This is the Pitfall-14 + QUALITY-14 + success-criterion-#2 backwards-compat
    assertion, parametrized across all 6 pre-Phase-3 templates.
    """
    import clawteam.team.models as team_models
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)

    from clawteam.team.manager import TeamManager
    from clawteam.templates import load_template

    tmpl = load_template(template)
    assert tmpl.name == template

    team_config = TeamManager.create_team(name=f"test-{template}", template=tmpl)

    # 1. Template field round-trips as <template>, NOT "gstack".
    assert getattr(team_config, "template", template) == template, (
        f"TeamConfig.template for {template} got contaminated — got "
        f"{getattr(team_config, 'template', None)!r}, expected {template!r}"
    )

    # 2. Member list matches the template's declared roles, NOT gstack's 11.
    gstack_role_names = {
        "pm", "ceo", "eng-mgr", "designer", "dx-lead",
        "engineer", "reviewer", "qa", "security", "shipper", "sre",
    }
    member_roles = {
        getattr(m, "role", "") or getattr(m, "name", "")
        for m in team_config.members
    }
    overlap = gstack_role_names & member_roles
    # Some overlap is OK if a template legitimately has an "engineer" or "qa"
    # member by coincidence — the contract is that the overlap MUST NOT be all 11.
    assert overlap != gstack_role_names, (
        f"{template} somehow got all 11 gstack roles — plugin contamination"
    )


@pytest.mark.parametrize("template", EXISTING_TEMPLATES_PHASE3)
def test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack(
    template, tmp_path, monkeypatch, gstack_plugin_loaded,
):
    """T-07-01 HIGH severity mitigation anchor: emitting a Reflect-phase event
    for a non-gstack team MUST NOT trigger GstackSprintPlugin's placeholder
    write. This is the consumption-layer isolation that makes HIGH severity
    mitigable.
    """
    from types import SimpleNamespace
    import clawteam.team.models as team_models

    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)
    monkeypatch.setattr(
        team_models, "get_team_config",
        lambda name: SimpleNamespace(template=template, leader_role=""),
        raising=False,
    )

    team_name = f"regression-{template}"
    sprint_id = "sprint-xyz"

    event = SimpleNamespace(
        phase_target="reflect",
        team_name=team_name,
        sprint_id=sprint_id,
    )
    gstack_plugin_loaded._on_phase_transition(event)

    pending_dir = tmp_path / "teams" / team_name / "_phase6_pending"
    json_files = list(pending_dir.glob("*.json")) if pending_dir.exists() else []
    assert not json_files, (
        f"T-07-01 violation: non-gstack template {template!r} triggered "
        f"_phase6_pending write; found {[str(f) for f in json_files]}"
    )


def test_all_six_existing_templates_parse_with_gstack_loaded(gstack_plugin_loaded):
    """Success criterion #7: every existing template's TemplateDef loads
    cleanly with GstackSprintPlugin imported. No PhaseRegistry name conflicts,
    no import-time collisions.
    """
    from clawteam.templates import load_template

    for template in EXISTING_TEMPLATES_PHASE3:
        tmpl = load_template(template)
        assert tmpl.name == template
        # Each existing template has its own phases (may be empty if it uses
        # DEFAULT_PHASES). Phases should NOT be the 7 gstack phases.
        tmpl_phases = getattr(tmpl, "phases", []) or []
        # Exact match on all 7 gstack phases would be contamination.
        gstack_phases = ["think", "plan", "build", "review", "test", "ship", "reflect"]
        assert tmpl_phases != gstack_phases, (
            f"{template} phases list is identical to gstack's — contamination"
        )
```

**Critical details:**
- `gstack_plugin_loaded` fixture instantiates and on_register's the plugin with a stub ctx. This simulates the global-load state without going through PluginManager.discover — which would require more test infrastructure. The plugin's internal state (`_ctx`, `_prompt_cache`) is initialized correctly.
- The "member role overlap" check in Test 1 is deliberately lenient: if a non-gstack template legitimately has an "engineer" member, that's fine; only a WHOLE-SET match (all 11 gstack roles) is contamination.
- Test 2 is the critical T-07-01 HIGH-severity mitigation anchor. It MUST pass for all 6 templates or the security gate blocks.
- Test 3 catches phase-registry / import-time conflicts. The comparison is deliberately "exact match == contamination" rather than "any overlap == contamination" — templates may legitimately have some overlap with gstack phases (e.g., "plan" appears in several templates), so only identical-all-seven is fatal.
- The parametrize expansion produces 2 × 6 = 12 new test cases plus 1 aggregate = 13 new tests total.

Atomic-commit discipline: single commit `test(03-09): extend regression matrix with 6 × cross-template isolation tests (QUALITY-14 + success-criterion-#2 + T-07-01 anchor)`.
  </action>
  <verify>
    <automated>pytest tests/test_template_regression_matrix.py -x</automated>
  </verify>
  <acceptance_criteria>
    - Full regression matrix passes: `pytest tests/test_template_regression_matrix.py -x` exits 0
    - 13+ new tests (12 parametrized + 1 aggregate): `pytest tests/test_template_regression_matrix.py --collect-only -q | grep -c 'cross\|unaffected\|existing_template' | awk '$1 >= 12 {exit 0} $1 < 12 {exit 1}'` exits 0
    - All 6 template names present: `grep -c 'software-dev\|hedge-fund\|code-review\|harness-default\|research-paper\|strategy-room' tests/test_template_regression_matrix.py | awk '$1 >= 6 {exit 0} $1 < 6 {exit 1}'` exits 0
    - GstackSprintPlugin loaded in fixture: `grep -q 'from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin' tests/test_template_regression_matrix.py` exits 0
    - T-07-01 anchor test present: `grep -q 'test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack' tests/test_template_regression_matrix.py` exits 0
    - Aggregate test present: `grep -q 'test_all_six_existing_templates_parse_with_gstack_loaded' tests/test_template_regression_matrix.py` exits 0
    - `pytest tests/ -x` exits 0 (entire phase's test additions + pre-existing regression matrix all green)
  </acceptance_criteria>
  <done>Regression matrix extended with 6 × 2 parametrized isolation tests + 1 aggregate test; T-07-01 HIGH severity mitigated with runtime anchor; QUALITY-14 contract enforced in CI.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Test fixture -> production code | Tests exercise real code paths (TeamManager.create_team, load_template, PluginManager-equivalent load) with tmp_path isolation. No production state is touched; no network; no ~/.clawteam/ writes. |
| Parametrized test data -> test isolation | Each parametrized test case runs in its own tmp_path subtree (per pytest.fixture semantics) — no cross-test state bleed. Template names in EXISTING_TEMPLATES_PHASE3 are literals, not env-driven. |
| gstack_plugin_loaded fixture -> per-test state | Fixture constructs a fresh GstackSprintPlugin instance per test; no shared global state. The stub ctx's bus.subscribe is a no-op so the real event bus isn't polluted. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09-01 | Denial of Service | Parametrized regression matrix adds 12+ test cases; if each spawns 11 agent worktrees, pytest runtime grows | mitigate | Test 1 (`test_existing_template_spawns_unaffected_by_gstack_plugin`) spawns whatever the template declares (most existing templates are 2-4 agents — not 11). Test 2 drives the handler directly without spawning. Worst-case total: 6 × 4 agent worktrees = 24 worktree creations over the matrix — well under 10 seconds on commodity SSD. If runtime grows beyond 30s, split the spawn-heavy test into `@pytest.mark.slow` opt-in. |
| T-09-02 | Tampering | Future editor removes one of the 6 templates from EXISTING_TEMPLATES_PHASE3 list thinking it's redundant — success-criterion-#7 coverage silently shrinks | mitigate | The aggregate test `test_all_six_existing_templates_parse_with_gstack_loaded` iterates the list and asserts all 6 load. If someone removes a template from the list, the aggregate test's count shrinks — caught by `assert len(EXISTING_TEMPLATES_PHASE3) == 6` at module top (executor: add this assertion after the list definition). |
| T-09-03 | Tampering | Regression anchor test (`test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack`) edited to skip or weaken the assertion, silently re-opening T-07-01 | accept | CODEOWNERS review + the T-07-01 label in the test docstring both make the intent explicit. If someone removes the assertion, git blame surfaces the reviewer who approved. Phase 0 CI tripwire + change-log review is the governance layer, not a test-layer mitigation. |
| T-09-04 | Information Disclosure | Integration test output (CliRunner result.output) could contain stack traces or debug data from a real spawn | accept | Test runs in tmp_path; any disclosure is local. `result.output` is only asserted, never logged externally. Standard pytest capture behavior applies. |

</threat_model>

<verification>
- `pytest tests/test_gstack_team_spawn.py -x` exits 0 (2 active tests: test_eleven_worktrees_created + test_team_spawn_gstack_end_to_end)
- `pytest tests/test_template_regression_matrix.py -x` exits 0 (pre-existing tests + 13 new Phase-3 cross-template isolation tests)
- `pytest tests/ -x` exits 0 (full Phase-3 test suite green, no Phase 0/1/2 regressions)
- No xfails remain in any Phase-3 test file: `grep -rc '@pytest.mark.xfail' tests/test_gstack_*.py tests/test_envelope_personas.py | awk -F: '$2 != "0" {exit 1}'` exits 0
- 11 per-agent worktrees created for gstack team: asserted by test_eleven_worktrees_created
- CLI integration path green: `clawteam team spawn gstack --name <n>` → 11 worktrees → `clawteam team show <n>` dashboard (all 3 steps verified by test_team_spawn_gstack_end_to_end)
- T-07-01 HIGH mitigation anchored: test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack passes for all 6 existing templates
- Success criterion #2 (cross-template isolation): test_existing_template_spawns_unaffected_by_gstack_plugin passes for all 6
- Success criterion #7 (Phase 0 regression matrix stays green): test_all_six_existing_templates_parse_with_gstack_loaded + pre-existing matrix tests green
- Delete-invariant documented in VALIDATION.md + this plan; executor notes manual pre-release verification command:
  `git stash -u && rm clawteam/plugins/gstack_sprint_plugin.py clawteam/templates/gstack.toml && rm -rf clawteam/templates/gstack/ && pytest tests/ -x --ignore=tests/test_gstack_template.py --ignore=tests/test_gstack_plugin.py --ignore=tests/test_gstack_role_prompts.py --ignore=tests/test_envelope_personas.py --ignore=tests/test_gstack_team_spawn.py --ignore=tests/test_evidence_schemas.py -k 'not gstack' && git stash pop`
</verification>

<success_criteria>
- TEAM-03 anchored: 11 per-agent worktrees created per team spawn; memory dirs pre-created per 03-02 D-05; CLI path produces the same result as direct API path
- UX-01 anchored: `clawteam team spawn gstack --name <n>` works end-to-end; exit 0; 11 agents; dashboard renders
- Success criterion #2: cross-template isolation verified for all 6 existing templates (software-dev / hedge-fund / code-review / harness-default / research-paper / strategy-room)
- Success criterion #7: Phase 0 regression matrix stays green after all Phase 3 additions
- T-07-01 HIGH severity (from 03-07) is mitigated at 2 layers (unit test in 03-07 + integration test here) — security gate clears
- No remaining xfails in any Phase 3 test file — Phase 3 tests are all active assertions
- Delete invariant documented (manual pre-release check) — D-07 contract enforceable by a single shell command
- `pytest tests/ -x` exits 0 — full suite green, Phase 3 ships
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-09-SUMMARY.md` covering:
- tests/test_gstack_team_spawn.py: 2 active tests + what each anchors (TEAM-03, UX-01)
- tests/test_template_regression_matrix.py: N new test cases added + parametrize expansion count + aggregate test
- Execution-time impact: wall-clock for `pytest tests/` before Phase 3 start vs after (if available)
- T-07-01 HIGH → MITIGATED: 2-layer coverage (03-07 unit + 03-09 integration parametrized × 6)
- Requirement coverage closeout: TEAM-01..05, SKILL-01..08, SPRINT-06, UX-01, UX-07 — one-line per REQ-ID listing the plan that owns each, with a final "16/16 covered" line
- Delete-invariant manual check: the exact shell command a release engineer runs before cutting the Phase 3 release
- Phase 3 closeout readiness signal: ready for /gsd-verify-work → /gsd-execute-phase chain
</output>
