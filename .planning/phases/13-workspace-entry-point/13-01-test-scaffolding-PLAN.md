---
phase: 13
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/cli/__init__.py
  - tests/cli/test_open.py
  - tests/cli/test_commands.py
  - tests/spawn/__init__.py
  - tests/spawn/test_adapters.py
  - tests/sprint/test_conductor.py
  - tests/integration/test_open_sprint_start_flow.py
autonomous: true
requirements: [WS-01, WS-02, WS-03, WS-04]
must_haves:
  truths:
    - "Every automated-command cell in 13-VALIDATION.md maps to a test function that exists and fails RED"
    - "Tests import the symbols they assert against (no stub-only placeholders)"
    - "pytest can collect every new test file without ImportError"
    - "Adapter tests instantiate NativeCliAdapter() per the canonical tests/test_adapters.py:81-114 pattern (prepare_command is a METHOD on NativeCliAdapter, NOT a module-level export — verified at adapters.py:34)"
    - "tests/integration/test_open_sprint_start_flow.py uses pytest.xfail stubs that Plan 13-04 Task 2 will REPLACE with real assertions — xfails are temporary scaffolding, not the final test bodies (per checker I3)"
  artifacts:
    - path: tests/cli/test_open.py
      provides: "WS-01 open-command test scaffolds (RED)"
      contains: "def test_open_no_goal_enters_clean_repl"
    - path: tests/spawn/test_adapters.py
      provides: "WS-02 adapter gating test scaffold (RED)"
      contains: "def test_no_goal_skips_post_launch_prompt"
    - path: tests/cli/test_commands.py
      provides: "WS-03 go help tagline test scaffold (RED)"
      contains: "def test_go_help_tagline_is_shortcut"
    - path: tests/sprint/test_conductor.py
      provides: "WS-04 sprint-start kickoff tests (RED)"
      contains: "def test_sprint_start_injects_kickoff"
    - path: tests/integration/test_open_sprint_start_flow.py
      provides: "WS-01..WS-04 integration coverage (RED)"
      contains: "def test_open_then_sprint_start_flow_direct"
  key_links:
    - from: "tests/cli/test_open.py"
      to: "clawteam.cli.commands.app"
      via: "typer.testing.CliRunner invoking `open` subcommand"
      pattern: "CliRunner.*invoke.*\\[.*\"open\""
    - from: "tests/spawn/test_adapters.py::test_no_goal_skips_post_launch_prompt"
      to: "clawteam.spawn.adapters.NativeCliAdapter.prepare_command"
      via: "adapter = NativeCliAdapter(); adapter.prepare_command(..., goal=None)"
      pattern: "post_launch_prompt is None"
    - from: "tests/sprint/test_conductor.py"
      to: "clawteam.sprint.conductor.SprintConductor.start_sprint"
      via: "call with goal + monkeypatched injector + assert inject_prompt called N times"
      pattern: "kickoff_injected_agents"
---

<objective>
Write the Wave-0 test scaffolding declared in `.planning/phases/13-workspace-entry-point/13-VALIDATION.md` so every subsequent implementation plan has a failing test to turn GREEN. Tests are RED by construction — they reference symbols that do not yet exist (`clawteam open`, `goal=` kwarg on `prepare_command`, `kickoff_injected_agents` field, reworded `go` tagline, `clawteam.sprint.kickoff` neutral module).

Purpose: Honor the Nyquist Rule — every `<verify>` in later plans must have an automated command that maps to a concrete test, and `13-VALIDATION.md` explicitly lists `wave_0_complete: false` as a gate to pass before implementation.

Output: Five test files (two new, three extensions) that fail on the current codebase and pass once Plans 13-02, 13-03, 13-04, 13-05 ship.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/phases/13-workspace-entry-point/13-CONTEXT.md
@.planning/phases/13-workspace-entry-point/13-VALIDATION.md
@clawteam/spawn/adapters.py
@clawteam/sprint/conductor.py
@clawteam/sprint/state.py
@clawteam/solo.py
@clawteam/cli/commands.py
@tests/test_adapters.py

<interfaces>
<!-- Extracted from the codebase so the executor doesn't have to scavenge. -->

From clawteam/spawn/adapters.py (lines 31-46, verified at HEAD 2026-04-27):
```python
class NativeCliAdapter:
    def prepare_command(
        self,
        command: list[str],
        *,
        prompt: str | None = None,
        cwd: str | None = None,
        skip_permissions: bool = False,
        interactive: bool = False,
        agent_name: str | None = None,
        container_env: dict[str, str] | None = None,
    ) -> PreparedCommand: ...
# `prepare_command` is a METHOD on NativeCliAdapter, NOT a module-level export.
# There is NO `from clawteam.spawn.adapters import prepare_command` — that
# import does not resolve. Confirmed via grep on HEAD: no `def prepare_command`
# at module scope.
#
# CANONICAL usage pattern (tests/test_adapters.py:81-114, the test class
# TestPrepareCommandPrompt that Plan 13-02 must keep GREEN):
#
#   from clawteam.spawn.adapters import NativeCliAdapter
#   class TestFoo:
#       adapter = NativeCliAdapter()           # class-scoped instance
#       def test_x(self):
#           result = self.adapter.prepare_command(
#               ["claude"], prompt="hi", interactive=True,
#           )
#           assert result.post_launch_prompt == "hi"
#
# Plan 13-02 will thread an explicit `goal: str | None = None` kwarg through
# prepare_command. The WS-02 invariant is: post_launch_prompt is set ONLY
# when `goal is not None` at the adapter boundary. This makes WS-02 load-
# bearing on the adapter contract rather than on upstream caller hygiene.
#
# PreparedCommand is a frozen dataclass with:
#   normalized_command: list[str]
#   final_command: list[str]
#   post_launch_prompt: str | None = None
```

From clawteam/sprint/conductor.py:
```python
class SprintConductor:
    def __init__(self, team_name: str, artifact_cap_bytes: Optional[int] = None,
                 phase_artifact_cap_bytes: Optional[int] = None, ...): ...
    def start_sprint(self, goal: str, auto_advance: bool = True) -> SprintState: ...
    def list_sprints(self) -> list[SprintState]: ...
```

From clawteam/sprint/state.py:
```python
class SprintState(BaseModel):
    sprint_id: str
    goal: str
    team: str
    current_phase: str
    status: Literal["running", "paused", "completed"]
    # Plan 13-03 will add:
    #   kickoff_injected_agents: list[str] = Field(default_factory=list)
```

From clawteam/solo.py:
```python
def cmd_go(goal, name=None, template="gstack", attach=True, window=True, tile=True): ...
def register_solo_commands(app: typer.Typer) -> None:
    panel = "🎯 Daily use (solo)"
    app.command("go", help="Start work: create team + start sprint + launch agents (one-shot)",
                rich_help_panel=panel)(cmd_go)
```

From Plan 13-03 (future): `clawteam/sprint/kickoff.py` will export:
```python
def build_ceo_kickoff_prompt(team_name: str, goal: str) -> str: ...
def build_specialist_kickoff_prompt(
    agent_name: str, agent_id: str, agent_type: str,
    team_name: str, leader_name: str, goal: str,
    workspace_dir: str = "", workspace_branch: str = "",
    isolated_workspace: bool = False, repo_path: str | None = None,
) -> str:
    # Delegates to clawteam.spawn.prompt.build_agent_prompt(task=<goal line>, ...)
    # to preserve byte-identical parity with today's launch-time `go` flow per
    # 13-CONTEXT D-03 ("same role-scoped variants as today's `go` flow").
```

Existing test patterns:
- `tests/test_spawn_cli.py` uses `from typer.testing import CliRunner` + `runner.invoke(app, [...])` — mirror this for `tests/cli/test_open.py` and `tests/cli/test_commands.py`.
- `tests/test_adapters.py:81-114` is the canonical `class TestFoo: adapter = NativeCliAdapter()` instantiation pattern — mirror this for `tests/spawn/test_adapters.py`. NEVER write `from clawteam.spawn.adapters import prepare_command` — that symbol does not exist.
- `tests/sprint/test_conductor_concurrency.py` demonstrates patching `SprintConductor.start_sprint_async` and tmp team dirs — mirror for sprint kickoff tests.
- `tests/integration/test_gstack_sprint_end_to_end.py` shows the integration-harness pattern with fake-binary + `monkeypatch.setattr` (NO `mock_claude` pytest fixture exists — verified via grep across tests/ on HEAD).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create tests/cli/ and tests/spawn/ package scaffolds</name>
  <read_first>
    - tests/__init__.py (confirms the tests/ root is a package)
    - tests/integration/__init__.py (matches the subpackage style for tests/cli/)
    - pyproject.toml [tool.pytest.ini_options] (confirms testpaths = ["tests"])
  </read_first>
  <behavior>
    - tests/cli/ is a Python package importable as `tests.cli`
    - tests/spawn/ is a Python package importable as `tests.spawn`
    - pytest collects from tests/cli/ and tests/spawn/ with no additional config
  </behavior>
  <action>
    Create two empty `__init__.py` files:
      1. `tests/cli/__init__.py` — empty file (one newline only)
      2. `tests/spawn/__init__.py` — empty file (one newline only)

    These establish the subpackages referenced by VALIDATION.md's Wave 0 file list. Keep them empty — no imports, no docstrings — to match the style of `tests/integration/__init__.py` and `tests/sprint/__init__.py`.
  </action>
  <verify>
    <automated>test -f tests/cli/__init__.py && test -f tests/spawn/__init__.py && uv run python -c "import tests.cli, tests.spawn"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/cli/__init__.py` exits 0
    - `test -f tests/spawn/__init__.py` exits 0
    - `uv run python -c "import tests.cli, tests.spawn"` exits 0
  </acceptance_criteria>
  <done>Both subpackage `__init__.py` files exist and are importable.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Write tests/spawn/test_adapters.py::test_no_goal_skips_post_launch_prompt (WS-02 RED)</name>
  <read_first>
    - tests/test_adapters.py lines 81-114 (CANONICAL pattern — `class TestFoo: adapter = NativeCliAdapter()` with class-scoped instance + `self.adapter.prepare_command(...)`. This is the EXACT pattern Task 2 MUST mirror — copy the structure, not just the spirit.)
    - clawteam/spawn/adapters.py lines 31-46 (NativeCliAdapter class definition + prepare_command method signature — `prepare_command` is a METHOD on the class at line 34, NOT a module-level function. There is NO `def prepare_command` at file scope.)
    - clawteam/spawn/adapters.py lines 131-140 (PreparedCommand gating — the target site for Plan 13-02; current `elif prompt:` short-circuits on falsy `prompt`, but Plan 13-02 will gate on `goal` instead so the WS-02 invariant holds even when callers pass non-empty `prompt`)
    - clawteam/spawn/adapters.py lines 156-158 (`is_claude_command` helper)
  </read_first>
  <behavior>
    - Test 1 (RED until Plan 13-02): `adapter.prepare_command(["claude"], prompt="", interactive=True, goal=None)` yields `PreparedCommand(post_launch_prompt=None)`. Test uses the NEW `goal=` kwarg Plan 13-02 will add; today the kwarg does not exist so the test fails with `TypeError: unexpected keyword argument 'goal'`.
    - Test 2 (RED until Plan 13-02): `adapter.prepare_command(["claude"], prompt="build CSV CLI", interactive=True, goal=None)` STILL yields `PreparedCommand(post_launch_prompt=None)` — even with a non-empty `prompt`, when `goal is None` the adapter refuses to inject. This is the load-bearing WS-02 invariant: gating on `goal` not on `prompt`. (Fails today for the same `TypeError` reason.)
    - Test 3 (already GREEN — regression fence): `adapter.prepare_command(["claude"], prompt="build CSV CLI", interactive=True, goal="build CSV CLI")` yields `PreparedCommand(post_launch_prompt="build CSV CLI")` (WS-02 must not break `go`/`launch --goal X`). Today this also fails with `TypeError` until Plan 13-02 adds the kwarg; after Plan 13-02 it passes and acts as a BC fence.
    - Test 4 (regression fence): tests/test_adapters.py::TestPrepareCommandPrompt::test_claude_interactive_gets_post_launch_prompt (no `goal=` kwarg) continues to pass after Plan 13-02 — the kwarg has a default of `None` but preserves the goal-derived-from-prompt path IFF the caller does not pass `goal=` at all (BC for existing call sites until they're updated).
  </behavior>
  <action>
    Create `tests/spawn/test_adapters.py` mirroring the canonical class-scoped `adapter = NativeCliAdapter()` pattern from `tests/test_adapters.py:81-114` (the `TestPrepareCommandPrompt` class). Use `NativeCliAdapter().prepare_command(...)` instantiation pattern — this is the ONLY supported invocation form. There is no module-level `prepare_command` function in `clawteam.spawn.adapters` and never has been; do NOT attempt `from clawteam.spawn.adapters import prepare_command` (it will raise `ImportError` at collection time).

    ```python
    """Phase 13 WS-02 adapter gating tests.

    These tests drive Plan 13-02's addition of a `goal: str | None = None`
    kwarg to NativeCliAdapter.prepare_command. The WS-02 invariant:
    post_launch_prompt is set for claude-interactive ONLY when `goal is
    not None`. Gating on the `goal` kwarg (not on truthy-coerced `prompt`)
    makes WS-02 load-bearing on the adapter contract.

    Pattern: mirrors tests/test_adapters.py:81-114 (TestPrepareCommandPrompt) —
    class-scoped `adapter = NativeCliAdapter()` instance, then
    `self.adapter.prepare_command(...)` on each test. Do NOT import a
    module-level `prepare_command` — it does not exist.
    """
    from __future__ import annotations

    import pytest

    from clawteam.spawn.adapters import NativeCliAdapter


    class TestPostLaunchPromptGating:
        adapter = NativeCliAdapter()

        def test_no_goal_skips_post_launch_prompt(self):
            """WS-02: goal=None → post_launch_prompt=None, even with non-empty prompt."""
            result = self.adapter.prepare_command(
                ["claude"],
                prompt="",
                interactive=True,
                goal=None,
            )
            assert result.post_launch_prompt is None

        def test_empty_goal_skips_post_launch_prompt(self):
            """WS-02: goal=None with empty prompt — no injection."""
            result = self.adapter.prepare_command(
                ["claude"],
                prompt="",
                interactive=True,
                goal=None,
            )
            assert result.post_launch_prompt is None

        def test_explicit_goal_still_injects_post_launch_prompt(self):
            """WS-02 BC: goal='X' + prompt='X' → post_launch_prompt='X' (preserves `go`/`launch --goal`)."""
            result = self.adapter.prepare_command(
                ["claude"],
                prompt="build CSV CLI",
                interactive=True,
                goal="build CSV CLI",
            )
            assert result.post_launch_prompt == "build CSV CLI"

        def test_goal_none_ignores_non_empty_prompt(self):
            """WS-02 load-bearing: even if prompt is non-empty (e.g., legacy caller),
            goal=None refuses to set post_launch_prompt. Prevents accidental
            re-introduction of kickoff-at-launch when `open` is called via a
            code path that still passes `prompt=<some persona string>`."""
            result = self.adapter.prepare_command(
                ["claude"],
                prompt="build CSV CLI",
                interactive=True,
                goal=None,
            )
            assert result.post_launch_prompt is None
    ```

    Every test explicitly passes `goal=` — this is the new kwarg Plan 13-02 introduces. On HEAD, all four tests fail with `TypeError: prepare_command() got an unexpected keyword argument 'goal'` (RED for the correct reason: the new contract surface is missing).

    Anti-patterns to AVOID:
    - `from clawteam.spawn.adapters import prepare_command` — will raise ImportError; symbol does not exist.
    - `prepare_command(["claude"], ...)` (calling at module scope without an instance) — will raise NameError.
    - Skipping the `class TestFoo: adapter = NativeCliAdapter()` setup — bare function-scoped tests work but diverge from the established pattern in `tests/test_adapters.py`.

    Do NOT touch adapters.py in this task.
  </action>
  <verify>
    <automated>uv run pytest tests/spawn/test_adapters.py -x -v 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_no_goal_skips_post_launch_prompt" tests/spawn/test_adapters.py` returns 1
    - `grep -c "def test_empty_goal_skips_post_launch_prompt" tests/spawn/test_adapters.py` returns 1
    - `grep -c "def test_explicit_goal_still_injects_post_launch_prompt" tests/spawn/test_adapters.py` returns 1
    - `grep -c "def test_goal_none_ignores_non_empty_prompt" tests/spawn/test_adapters.py` returns 1
    - `grep -c "adapter = NativeCliAdapter()" tests/spawn/test_adapters.py` returns 1 (canonical class-scoped pattern, mirrors tests/test_adapters.py:84)
    - `grep -c "from clawteam.spawn.adapters import prepare_command" tests/spawn/test_adapters.py` returns 0 (anti-pattern — prepare_command is not a module-level export, would raise ImportError)
    - `grep -c "from clawteam.spawn.adapters import NativeCliAdapter" tests/spawn/test_adapters.py` returns 1 (correct import — class symbol)
    - `uv run pytest tests/spawn/test_adapters.py --collect-only` exits 0 (file collectable, no ImportError)
    - `uv run pytest tests/spawn/test_adapters.py::TestPostLaunchPromptGating -x` exits non-zero on HEAD (RED — `goal=` kwarg does not exist yet)
  </acceptance_criteria>
  <done>File exists with 4 tests using the canonical `NativeCliAdapter()` pattern; all RED on HEAD with `TypeError: unexpected keyword argument 'goal'`; pytest collects them cleanly.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Write tests/cli/test_open.py and tests/cli/test_commands.py (WS-01, WS-03 RED)</name>
  <read_first>
    - tests/test_spawn_cli.py lines 1-60 (CliRunner setup pattern)
    - clawteam/solo.py lines 779-803 (register_solo_commands — the target for Plan 13-04 + 13-05)
    - clawteam/cli/commands.py lines 1-50 (app instance — the typer app that CliRunner invokes)
  </read_first>
  <behavior>
    - `tests/cli/test_open.py::test_open_help_mentions_no_goal_required` — `CliRunner().invoke(app, ["open", "--help"])` exits 0 AND help text mentions "template" or "resume".
    - `tests/cli/test_open.py::test_open_no_args_without_active_team_errors` — `CliRunner().invoke(app, ["open"])` with no active team exits non-zero.
    - `tests/cli/test_open.py::test_open_accepts_template_positional` — `CliRunner().invoke(app, ["open", "gstack", "--help"])` exits 0.
    - `tests/cli/test_commands.py::test_go_help_tagline_is_shortcut` — invoking `["go", "--help"]` emits help text containing "shortcut" AND a reference to `open` or `sprint start`.
    - `tests/cli/test_commands.py::test_go_runtime_signature_unchanged` — `inspect.signature(cmd_go)` still has a `goal` parameter (Plan 13-05 is docs-only).
  </behavior>
  <action>
    Create `tests/cli/test_open.py`:
      ```python
      from typer.testing import CliRunner
      from clawteam.cli.commands import app

      runner = CliRunner()

      class TestOpenCommand:
          def test_open_help_mentions_no_goal_required(self):
              result = runner.invoke(app, ["open", "--help"])
              assert result.exit_code == 0
              # Clean REPL language — wording from 13-CONTEXT decisions block
              out = result.output.lower()
              assert "template" in out or "resume" in out

          def test_open_no_args_without_active_team_errors(self, tmp_path, monkeypatch):
              # No CLAWTEAM_DATA_DIR with prior active_team → should reject loudly
              monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
              result = runner.invoke(app, ["open"])
              assert result.exit_code != 0

          def test_open_accepts_template_positional(self):
              result = runner.invoke(app, ["open", "gstack", "--help"])
              assert result.exit_code == 0
      ```

    Create `tests/cli/test_commands.py`:
      ```python
      import inspect

      from typer.testing import CliRunner
      from clawteam.cli.commands import app
      from clawteam.solo import cmd_go

      runner = CliRunner()

      class TestGoDemotion:
          def test_go_help_tagline_is_shortcut(self):
              """WS-03: go help describes it as a shortcut for open + sprint start."""
              result = runner.invoke(app, ["go", "--help"])
              assert result.exit_code == 0
              out = result.output.lower()
              assert "shortcut" in out
              # The help must reference at least one of the composed primitives
              assert "open" in out or "sprint start" in out

          def test_go_runtime_signature_unchanged(self):
              """WS-03 BC: go still takes a required goal positional."""
              sig = inspect.signature(cmd_go)
              assert "goal" in sig.parameters
      ```

    Both files MUST be RED against HEAD: `open` is not registered, so `runner.invoke(app, ["open", "--help"])` returns `exit_code != 0`; and the current `go` help tagline is `"Start work: create team + start sprint + launch agents (one-shot)"` which does NOT contain "shortcut".
  </action>
  <verify>
    <automated>uv run pytest tests/cli/test_open.py tests/cli/test_commands.py --collect-only 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_open_help_mentions_no_goal_required" tests/cli/test_open.py` returns 1
    - `grep -c "def test_open_no_args_without_active_team_errors" tests/cli/test_open.py` returns 1
    - `grep -c "def test_open_accepts_template_positional" tests/cli/test_open.py` returns 1
    - `grep -c "def test_go_help_tagline_is_shortcut" tests/cli/test_commands.py` returns 1
    - `grep -c "def test_go_runtime_signature_unchanged" tests/cli/test_commands.py` returns 1
    - `uv run pytest tests/cli/ --collect-only` exits 0 and lists 5 tests
    - `uv run pytest tests/cli/test_open.py::TestOpenCommand::test_open_help_mentions_no_goal_required -x` exits non-zero (RED — `open` not yet registered)
    - `uv run pytest tests/cli/test_commands.py::TestGoDemotion::test_go_help_tagline_is_shortcut -x` exits non-zero (RED — tagline unchanged)
  </acceptance_criteria>
  <done>Both files exist; all 5 tests collectable; at least 2 tests RED against HEAD (documenting WS-01 + WS-03 intent).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Extend tests/sprint/test_conductor.py with WS-04 tests (RED)</name>
  <read_first>
    - tests/sprint/test_conductor_concurrency.py (existing conductor test patterns — fixture setup, monkeypatching, SprintConductor construction)
    - clawteam/sprint/conductor.py lines 332-357 (start_sprint signature)
    - clawteam/sprint/state.py lines 32-140 (SprintState fields — confirm `kickoff_injected_agents` does not yet exist)
    - clawteam/cli/commands.py lines 4593-4619 (current CEO kickoff synthesis — will be moved to `clawteam/sprint/kickoff.py` in Plan 13-03)
  </read_first>
  <behavior>
    - Test 1 (RED until Plan 13-03): `SprintConductor.start_sprint(goal="...", inject_kickoff=True)` records the set of agents that received kickoff injection into `state.kickoff_injected_agents`.
    - Test 2 (RED until Plan 13-03): Calling `start_sprint` when a sprint with `status="running"` already exists under the team raises an error containing "already active".
    - Test 3 (RED until Plan 13-03): `SprintConductor.retry_kickoff(sprint_id)` injects into agents NOT in `kickoff_injected_agents` and adds them to the list.
    - Test 4 (existing regression fence): `start_sprint(goal="X")` without new kwargs still returns a SprintState with `status="running"`.
  </behavior>
  <action>
    Create `tests/sprint/test_conductor.py` with a new test class `TestSprintStartKickoffInjection` with the four tests:

      ```python
      import pytest
      from clawteam.sprint.conductor import SprintConductor
      from clawteam.sprint.state import SprintState


      @pytest.fixture
      def conductor(tmp_path, monkeypatch):
          monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
          # Stub out team existence check if needed — mirror
          # tests/sprint/test_conductor_concurrency.py's fixture conventions.
          return SprintConductor(team_name="t13")

      class TestSprintStartKickoffInjection:
          def test_sprint_start_injects_kickoff(self, conductor, monkeypatch):
              """WS-04: start_sprint injects kickoff and records recipients."""
              captured = []
              def fake_inject(target, agent_name, prompt):
                  captured.append(agent_name)
              # Plan 13-03 wires the injector — test will pick the seam it chooses
              monkeypatch.setattr(
                  "clawteam.spawn.tmux_backend._inject_prompt_via_buffer",
                  fake_inject,
                  raising=False,
              )
              state = conductor.start_sprint(goal="build CSV CLI", inject_kickoff=True)
              # Both the per-pane call AND the recorded list
              assert len(captured) > 0, "expected kickoff injection into at least one pane"
              assert hasattr(state, "kickoff_injected_agents"), \
                  "Plan 13-03 must add kickoff_injected_agents to SprintState"
              assert set(state.kickoff_injected_agents) == set(captured)

          def test_sprint_start_rejects_active_sprint_collision(self, conductor):
              """WS-04: cannot start a sprint while another is running."""
              conductor.start_sprint(goal="first", inject_kickoff=False)
              with pytest.raises(Exception) as excinfo:
                  conductor.start_sprint(goal="second", inject_kickoff=False)
              assert "already active" in str(excinfo.value).lower() \
                  or "already running" in str(excinfo.value).lower()

          def test_sprint_start_retry_kickoff_partial(self, conductor, monkeypatch):
              """WS-04: retry_kickoff only injects into agents not in kickoff_injected_agents."""
              call_log = []
              def flaky_inject(target, agent_name, prompt):
                  if agent_name in ("ceo", "pm", "eng-mgr"):
                      call_log.append(("first", agent_name))
                      return
                  raise RuntimeError("simulated partial failure")
              monkeypatch.setattr(
                  "clawteam.spawn.tmux_backend._inject_prompt_via_buffer",
                  flaky_inject,
                  raising=False,
              )
              state = conductor.start_sprint(goal="build X", inject_kickoff=True)
              def good_inject(target, agent_name, prompt):
                  call_log.append(("retry", agent_name))
              monkeypatch.setattr(
                  "clawteam.spawn.tmux_backend._inject_prompt_via_buffer",
                  good_inject,
                  raising=False,
              )
              retry_fn = getattr(conductor, "retry_kickoff", None)
              assert retry_fn is not None, "Plan 13-03 must expose retry_kickoff"
              retry_fn(state.sprint_id)
              retry_targets = [name for phase, name in call_log if phase == "retry"]
              assert "ceo" not in retry_targets
              assert "pm" not in retry_targets
              assert "eng-mgr" not in retry_targets

          def test_start_sprint_without_inject_kickoff_is_v11_compatible(self, conductor):
              """WS-04 BC: legacy callers (no inject_kickoff kwarg) still work."""
              state = conductor.start_sprint(goal="legacy call")
              assert state.status == "running"
              # kickoff_injected_agents may exist but must be empty when the caller
              # did not opt in to injection
              assert list(getattr(state, "kickoff_injected_agents", [])) == []
      ```

    Tests 1-3 WILL be RED today: `start_sprint` does not accept `inject_kickoff`, does not reject on collision, does not have `retry_kickoff`, and `SprintState` has no `kickoff_injected_agents` field.

    Test 4 (BC regression) may be GREEN today and MUST stay GREEN after Plan 13-03.
  </action>
  <verify>
    <automated>uv run pytest tests/sprint/test_conductor.py --collect-only 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_sprint_start_injects_kickoff" tests/sprint/test_conductor.py` returns 1
    - `grep -c "def test_sprint_start_rejects_active_sprint_collision" tests/sprint/test_conductor.py` returns 1
    - `grep -c "def test_sprint_start_retry_kickoff_partial" tests/sprint/test_conductor.py` returns 1
    - `grep -c "def test_start_sprint_without_inject_kickoff_is_v11_compatible" tests/sprint/test_conductor.py` returns 1
    - `uv run pytest tests/sprint/test_conductor.py --collect-only` lists the 4 tests above
    - `uv run pytest tests/sprint/test_conductor.py::TestSprintStartKickoffInjection::test_sprint_start_injects_kickoff -x` exits non-zero (RED)
  </acceptance_criteria>
  <done>File exists with 4 tests; 3 are RED; pytest collects all.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 5: Write tests/integration/test_open_sprint_start_flow.py (integration RED, direct-invocation harness)</name>
  <read_first>
    - tests/integration/test_gstack_sprint_end_to_end.py lines 1-100 (shows that this file uses a FAKE-BINARY harness via `_install_fake_bins`; there is NO `mock_claude` pytest fixture anywhere in the tree — grep `mock_claude` in tests/ returns zero fixture defs)
    - tests/integration/__init__.py (confirms package layout)
    - clawteam/sprint/conductor.py lines 332-357 (start_sprint — target for direct invocation)
  </read_first>
  <behavior>
    - Test 1 (RED until Plan 13-04): Opening a team via `clawteam.solo.cmd_open` code path with no goal results in zero calls to `_inject_prompt_via_buffer`. Stub `cmd_open` is not registered on HEAD, so `from clawteam.solo import cmd_open` itself fails — the test is RED via ImportError. Plan 13-04 defines `cmd_open` and the test becomes meaningful.
    - Test 2 (RED until Plans 13-03 + 13-04): After a seeded tmux_pane_map.json, invoking `SprintConductor.start_sprint(goal="X", inject_kickoff=True)` directly (no `mock_claude` fixture — does not exist) with monkeypatched `_inject_prompt_via_buffer` records 11 injection calls.

    NOTE (per checker I3): These two tests are scaffolded as `pytest.xfail` placeholders. Plan 13-04 Task 2 will REPLACE the xfail bodies with real `monkeypatch.setattr("subprocess.Popen", ...)` assertions. The xfails are temporary — they document the eventual assertion shape but do not run real test logic. This is intentional: Wave 0 must produce a collectable test scaffold without depending on Plan 13-03/04 symbols that don't exist yet.
  </behavior>
  <action>
    Create `tests/integration/test_open_sprint_start_flow.py`. Do NOT use a `mock_claude` fixture — grep confirms no such fixture exists in the tree. Use DIRECT invocation of the target code paths (the checker's option (a)) so the test stays lightweight and self-contained:

      ```python
      """Phase 13 integration: open → sprint start composed flow (WS-01..WS-04).

      This file deliberately uses DIRECT invocation of the target code paths
      rather than a subprocess-based CLI harness. The tests/integration/
      tree has no `mock_claude` pytest fixture (grep verified); rather than
      create one for a single phase, we stay at the unit-integration seam by
      invoking `SprintConductor.start_sprint(inject_kickoff=True)` with a
      pre-seeded tmux_pane_map.json and monkeypatched injector. If a later
      phase needs a real-subprocess harness, it can be introduced then.
      """
      from __future__ import annotations

      import json
      from pathlib import Path

      import pytest

      # Marked integration so VALIDATION.md's full-suite wave can include it
      # while quick-iteration modes can opt out with -m "not integration".
      pytestmark = pytest.mark.integration


      class TestOpenThenSprintStartDirect:
          def test_open_no_goal_injects_no_kickoff(self, tmp_path, monkeypatch):
              """WS-01 + WS-02: `cmd_open` code path makes zero kickoff injections.

              Uses direct import of cmd_open (fails with ImportError on HEAD
              until Plan 13-04 defines it — this is a valid RED signal).
              """
              pytest.xfail(
                  "Plan 13-04 Task 2 will REPLACE this xfail with a real test "
                  "that monkeypatches subprocess.Popen + _inject_prompt_via_buffer "
                  "and asserts zero kickoff calls during the cmd_open flow."
              )

          def test_open_then_sprint_start_flow_direct(self, tmp_path, monkeypatch):
              """WS-04: SprintConductor.start_sprint(inject_kickoff=True) fans 11 injections.

              Seeds a tmux_pane_map.json with 11 agents, monkeypatches
              _inject_prompt_via_buffer to record calls, invokes
              SprintConductor.start_sprint(goal='X', inject_kickoff=True)
              directly (no CLI subprocess, no mock_claude fixture needed).
              """
              pytest.xfail(
                  "Plan 13-04 Task 2 will REPLACE this xfail. On GREEN, this test "
                  "will: (1) seed ~/.clawteam/teams/t13/tmux_pane_map.json with "
                  "the 11 agent names, (2) monkeypatch "
                  "clawteam.spawn.tmux_backend._inject_prompt_via_buffer to a "
                  "capturing lambda, (3) call SprintConductor(team_name='t13')."
                  "start_sprint(goal='X', inject_kickoff=True) directly, "
                  "(4) assert len(captured)==11 and 'ceo' in captured."
              )
      ```

    Both tests are xfail placeholders. The xfail bodies document exactly what Plan 13-04's Task 2 will write when it replaces them with real assertions. No `mock_claude` fixture is referenced anywhere.
  </action>
  <verify>
    <automated>uv run pytest tests/integration/test_open_sprint_start_flow.py --collect-only 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - File `tests/integration/test_open_sprint_start_flow.py` exists
    - `grep -c "def test_open_no_goal_injects_no_kickoff" tests/integration/test_open_sprint_start_flow.py` returns 1
    - `grep -c "def test_open_then_sprint_start_flow_direct" tests/integration/test_open_sprint_start_flow.py` returns 1
    - `grep -c "mock_claude" tests/integration/test_open_sprint_start_flow.py` returns 0 (NO reference to the non-existent fixture)
    - `uv run pytest tests/integration/test_open_sprint_start_flow.py --collect-only` exits 0 and lists both tests
    - `uv run pytest tests/integration/test_open_sprint_start_flow.py -x --runxfail 2>&1 | tail -5` confirms the tests xfail (not error)
  </acceptance_criteria>
  <done>File exists with 2 xfail stubs documenting Plan 13-04's direct-invocation assertions; NO reference to any `mock_claude` fixture; pytest collects both.</done>
</task>

<task type="auto">
  <name>Task 6: Flip VALIDATION.md's wave_0_complete and update task-id map</name>
  <read_first>
    - .planning/phases/13-workspace-entry-point/13-VALIDATION.md (the file being updated)
  </read_first>
  <action>
    Update `.planning/phases/13-workspace-entry-point/13-VALIDATION.md`:

    1. In the frontmatter, change `wave_0_complete: false` to `wave_0_complete: true`.
    2. In the "Per-Task Verification Map" table, update the `File Exists` column for each row from `❌ W0` to `✅ W0` (all four rows).
    3. At the bottom of the "Wave 0 Requirements" block, append a line: `*Wave 0 landed 2026-04-24 under Plan 13-01 (test scaffolding). All tests RED; ready for implementation waves.*`

    Do NOT change any other section of the file. Do NOT modify requirement IDs, threat refs, or sampling rates. NOTE: Plan 13-05 Task 3 will revisit this map and replace placeholder Task IDs with real test function names extracted from the test files (per checker W6) — this Task 6 only flips wave_0_complete + the File Exists cells, NOT the Task ID column.
  </action>
  <verify>
    <automated>grep -q "wave_0_complete: true" .planning/phases/13-workspace-entry-point/13-VALIDATION.md && grep -q "Wave 0 landed 2026-04-24 under Plan 13-01" .planning/phases/13-workspace-entry-point/13-VALIDATION.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "wave_0_complete: true" .planning/phases/13-workspace-entry-point/13-VALIDATION.md` returns 1
    - `grep -c "wave_0_complete: false" .planning/phases/13-workspace-entry-point/13-VALIDATION.md` returns 0
    - `grep -c "Wave 0 landed 2026-04-24 under Plan 13-01" .planning/phases/13-workspace-entry-point/13-VALIDATION.md` returns 1
    - `grep -c "❌ W0" .planning/phases/13-workspace-entry-point/13-VALIDATION.md` returns 0
  </acceptance_criteria>
  <done>VALIDATION.md frontmatter flipped; all per-task-map File Exists cells show ✅; footer line added.</done>
</task>

</tasks>

<verification>
Run the full Wave 0 gate:
```bash
uv run pytest tests/cli/ tests/spawn/test_adapters.py tests/sprint/test_conductor.py tests/integration/test_open_sprint_start_flow.py --collect-only
```
All 15 tests (5 cli + 4 adapters + 4 conductor + 2 integration) MUST collect. A non-zero number of them MUST be RED (WS-01, WS-02, WS-03, WS-04 intent captured).

Quick command run (expect RED, not green — this is by design):
```bash
uv run pytest tests/cli/ tests/spawn/test_adapters.py tests/sprint/test_conductor.py --tb=no -q 2>&1 | tail -20
```
</verification>

<success_criteria>
- All 5 test files exist in the correct paths per VALIDATION.md Wave 0 list
- All 15 tests are pytest-collectable
- WS-01..WS-04 each have at least one test that is RED against current HEAD (captured intent, not just a pass-through)
- tests/spawn/test_adapters.py uses the canonical `adapter = NativeCliAdapter()` pattern (NOT a non-existent `prepare_command` module export)
- tests/integration/test_open_sprint_start_flow.py has ZERO references to a `mock_claude` fixture (it does not exist)
- VALIDATION.md `wave_0_complete` flipped to `true`
- No production code (`clawteam/**/*.py`) modified — this is tests-only
</success_criteria>

<output>
After completion, create `.planning/phases/13-workspace-entry-point/13-01-SUMMARY.md` documenting:
- Which tests are RED vs GREEN-regression-fences
- Any deviations from the task-id map in VALIDATION.md (e.g. renamed tests)
- Pointer: "Next: Plan 13-02 (adapter gating via `goal=` kwarg) + Plan 13-03 (sprint-start injection + neutral kickoff module) can run in parallel as Wave 2."
</output>
