---
phase: 00-foundation-upstream-rfc
plan: 04
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_template_regression_matrix.py
  - .github/workflows/ci.yml
autonomous: true
requirements:
  - CORE-03
  - TEAM-06
  - QUALITY-14
tags: [regression, bc, templates, ci]

must_haves:
  truths:
    - "Every one of the 6 packaged templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) spawns cleanly via `clawteam launch <template>` through the existing Typer CLI."
    - "Each spawn records one or more RecordingBackend.calls with non-empty agent_name, non-empty command list, and correct team_name. No real subprocesses are started."
    - "The regression test completes in under 10 seconds wall time (target <5s; 6 parametrized cases with mocked backend)."
    - "CI picks up the new test file automatically via pytest's testpaths = ['tests'] configuration — no ci.yml edit is required, only verification."
  artifacts:
    - path: "tests/test_template_regression_matrix.py"
      provides: "Parametrized @pytest.mark.parametrize('template', TEMPLATE_NAMES) test that launches each packaged template through the CliRunner+RecordingBackend harness"
      contains: "TEMPLATE_NAMES"
      min_lines: 60
    - path: ".github/workflows/ci.yml"
      provides: "Existing CI workflow; verify-only (no edits needed — pytest auto-discovers new test files via testpaths)"
      contains: "pytest tests/"
  key_links:
    - from: "tests/test_template_regression_matrix.py"
      to: "clawteam/cli/commands.py::launch command"
      via: "CliRunner().invoke(app, ['launch', template, ...])"
      pattern: "runner\\.invoke\\(app, \\[\"launch\""
    - from: "tests/test_template_regression_matrix.py"
      to: "RecordingBackend (copied from test_spawn_cli.py:20-29)"
      via: "monkeypatch.setattr(\"clawteam.spawn.get_backend\", lambda _: backend)"
      pattern: "monkeypatch\\.setattr.*spawn\\.get_backend"
---

<objective>
Ship the backwards-compatibility regression matrix (QUALITY-14 + CORE-03 + TEAM-06): a single parametrized pytest file that exercises all 6 packaged templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) through the existing `clawteam launch <template>` CLI flow using a `RecordingBackend` mock. The matrix guarantees that any future Phase 1+ harness change (PhaseRegistry, SprintState, InteractionGate) does not accidentally break existing template launches.

Purpose: This is the safety-net that makes Phases 1-7 SAFE to land. Before Phase 1 introduces PhaseRegistry and new HarnessPlugin hooks, we must have a test that would FAIL if any template's launch path regresses. This plan lands that test.

Output:
- New `tests/test_template_regression_matrix.py` — parametrized across 6 templates, RecordingBackend mock, STATE-only assertions (no prompt content — `tests/test_templates.py` already covers prompt semantics; this file covers the launch integration flow per RESEARCH.md Pitfall #6).
- Verification that `.github/workflows/ci.yml` auto-discovers the new test via `testpaths = ["tests"]`. No ci.yml edits needed (confirmed in context); if any edge case requires an edit we document and apply it.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/00-foundation-upstream-rfc/00-RESEARCH.md
@.planning/phases/00-foundation-upstream-rfc/00-PATTERNS.md
@.planning/codebase/TESTING.md
@.planning/codebase/CONVENTIONS.md
@tests/conftest.py
@tests/test_spawn_cli.py
@tests/test_templates.py
@.github/workflows/ci.yml
@clawteam/templates/harness-default.toml

<interfaces>
<!-- Exact patterns to copy from existing tests. -->

From tests/test_spawn_cli.py:20-29 (RecordingBackend — paste this class verbatim into the new file):
```python
class RecordingBackend:
    def __init__(self):
        self.calls = []

    def spawn(self, **kwargs):
        self.calls.append(kwargs)
        return f"Agent '{kwargs['agent_name']}' spawned"

    def list_running(self):
        return []
```

From tests/test_spawn_cli.py:53-68 (the canonical launch+RecordingBackend flow — shape for each parametrized case):
```python
def test_launch_cli_passes_skip_permissions_from_config(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["launch", "hedge-fund", "--team", "fund1", "--goal", "Analyze AAPL"],
        env={"CLAWTEAM_DATA_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0
    assert backend.calls
    assert all(call["skip_permissions"] is True for call in backend.calls)
```

From tests/conftest.py:10-19 (autouse isolated_data_dir fixture — active for ANY test in tests/):
```python
@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / ".clawteam"
    data_dir.mkdir()
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data_dir))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return data_dir
```

From pyproject.toml (test discovery auto-picks up new files):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```

From .github/workflows/ci.yml:32 (the existing CI test invocation that will run the new file automatically):
```yaml
- run: python -m pytest tests/ -v --tb=short
```

From clawteam/templates/ directory (the 6 packaged templates confirmed present):
```
code-review.toml
harness-default.toml
hedge-fund.toml
research-paper.toml
software-dev.toml
strategy-room.toml
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create tests/test_template_regression_matrix.py with parametrize-across-templates</name>
  <files>tests/test_template_regression_matrix.py</files>
  <behavior>
    - TEMPLATE_NAMES is a list-literal containing exactly the 6 packaged template stems: "software-dev", "hedge-fund", "code-review", "harness-default", "research-paper", "strategy-room".
    - A single @pytest.mark.parametrize("template", TEMPLATE_NAMES) produces 6 test cases.
    - Each case: mocks clawteam.spawn.get_backend to return a fresh RecordingBackend; invokes `app, ["launch", template, "--team", f"test-{template}", "--goal", "BC regression smoke"]` via CliRunner.
    - Each case asserts: exit_code == 0, backend.calls non-empty, every call has non-empty agent_name, every call has non-empty command list, every call's team_name == f"test-{template}".
    - No real subprocesses spawn; RecordingBackend captures all invocations.
    - File-module-scoped total wall time: < 10 seconds (mocked backend means no real process overhead).
  </behavior>
  <action>
    Create `tests/test_template_regression_matrix.py` as a new file. Use the flat top-level layout (no subdirs — TESTING.md §Test File Organization says "separate tests/ directory at repo root, flat layout").

    Full file content:

    ```python
    """Backwards-compatibility regression matrix — CORE-03, TEAM-06, QUALITY-14.

    Exercises every packaged template's ``clawteam launch <template>`` flow through
    a RecordingBackend mock. Ensures that Phase 1+ harness changes (PhaseRegistry,
    SprintState, InteractionGate, plugin hooks) never silently break existing
    templates' spawn/task-creation path.

    This is the STATE-level matrix (did launch exit cleanly, did agents get
    spawned, do their kwargs look right); prompt CONTENT assertions live in
    tests/test_templates.py and remain untouched.
    """

    from __future__ import annotations

    import pytest
    from typer.testing import CliRunner

    from clawteam.cli.commands import app


    # The 6 packaged templates shipped in clawteam/templates/*.toml.
    # If any template is added/removed, update this list AND tests/test_templates.py
    # (which enumerates template structure separately).
    TEMPLATE_NAMES: list[str] = [
        "software-dev",
        "hedge-fund",
        "code-review",
        "harness-default",
        "research-paper",
        "strategy-room",
    ]


    class RecordingBackend:
        """Spawn-backend double that captures invocations without forking processes.

        Verbatim copy of tests/test_spawn_cli.py:20-29 — do NOT import from that
        module (TESTING.md: "No shared fixtures directory — each test module
        defines its own factories close to where they are used").
        """

        def __init__(self) -> None:
            self.calls: list[dict] = []

        def spawn(self, **kwargs):
            self.calls.append(kwargs)
            return f"Agent '{kwargs['agent_name']}' spawned"

        def list_running(self):
            return []


    @pytest.mark.parametrize("template", TEMPLATE_NAMES)
    def test_template_launches_cleanly(template, monkeypatch, tmp_path):
        """Each packaged template must launch cleanly via `clawteam launch <template>`.

        BC guarantee for CORE-03 + TEAM-06 + QUALITY-14. Any future harness change
        that breaks this test has regressed an existing template's launch path and
        must be reverted or accompanied by an intentional template update.
        """
        # Redundant with conftest.py's isolated_data_dir autouse, but matches the
        # canonical idiom in tests/test_spawn_cli.py — keep for consistency.
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        backend = RecordingBackend()
        monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

        runner = CliRunner()
        team_name = f"bc-matrix-{template}"
        result = runner.invoke(
            app,
            [
                "launch",
                template,
                "--team",
                team_name,
                "--goal",
                "BC regression smoke goal",
            ],
            env={
                "HOME": str(tmp_path),
                "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
            },
        )

        assert result.exit_code == 0, (
            f"launch {template} failed (exit={result.exit_code}):\n{result.output}"
        )
        assert backend.calls, f"no agents spawned for {template}"

        for call in backend.calls:
            assert call.get("agent_name"), (
                f"{template}: empty agent_name in spawn call: {call!r}"
            )
            assert call.get("team_name") == team_name, (
                f"{template}: team_name mismatch: {call.get('team_name')!r} "
                f"vs expected {team_name!r}"
            )
            assert call.get("command"), (
                f"{template}: empty command list in spawn call: {call!r}"
            )
            # command must be a list[str], never a single string (per spawn.adapters contract)
            assert isinstance(call["command"], list), (
                f"{template}: command is not a list: {type(call['command'])!r}"
            )


    @pytest.mark.parametrize("template", TEMPLATE_NAMES)
    def test_template_spawn_calls_preserve_skip_permissions_flag(template, monkeypatch, tmp_path):
        """Every template must honour the skip_permissions config flag end-to-end.

        Existing tests in test_spawn_cli.py cover hedge-fund specifically; this
        parametrized variant ensures all 6 templates propagate the flag (guards
        against a template TOML that accidentally overrides it).
        """
        monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.chdir(tmp_path)

        backend = RecordingBackend()
        monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "launch",
                template,
                "--team",
                f"skip-perms-{template}",
                "--goal",
                "BC regression — skip_permissions propagation",
            ],
            env={
                "HOME": str(tmp_path),
                "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
            },
        )

        assert result.exit_code == 0, (
            f"launch {template} failed for skip_permissions test:\n{result.output}"
        )
        assert backend.calls
        # skip_permissions defaults to True in ClawTeamConfig; matches
        # tests/test_spawn_cli.py::test_launch_cli_passes_skip_permissions_from_config.
        assert all(call.get("skip_permissions") is True for call in backend.calls), (
            f"{template}: one or more spawn calls had skip_permissions != True: "
            f"{[(c.get('agent_name'), c.get('skip_permissions')) for c in backend.calls]}"
        )
    ```

    Critical rules (per PATTERNS.md §tests/test_template_regression_matrix.py):
    - Module docstring (mandatory per CONVENTIONS.md).
    - `from __future__ import annotations` at top (matches `test_spawn_cli.py:1`, `test_cli_commands.py:1`).
    - Import order: `__future__` → stdlib (`pytest`) → test-frameworks (`typer.testing`) → first-party (`clawteam.cli.commands`). Three groups, blank-line separated (ruff `I` rule).
    - `RecordingBackend` defined as a module-level class — verbatim copy from `test_spawn_cli.py:20-29`. Do NOT import it from that test module (TESTING.md: "No shared fixtures directory").
    - `TEMPLATE_NAMES` is module-level, list-literal with trailing comma (CONVENTIONS.md `N` rule on constants — ruff permits lowercase `list[str]` type annotation via `from __future__`).
    - Use `@pytest.mark.parametrize("template", TEMPLATE_NAMES)` decorator (matches `test_paths.py:13-25` style).
    - `monkeypatch.setenv("CLAWTEAM_DATA_DIR", ...)` + `monkeypatch.setenv("HOME", ...)` + `monkeypatch.chdir(tmp_path)` + `runner.invoke(..., env=...)` — the full canonical shape used by every template launch test in `test_spawn_cli.py:53-68, 309-341`. DO NOT try to optimize these away even though `isolated_data_dir` autouse does much of the same — PATTERNS.md explicitly says "follow the existing idiom, don't optimize it away".
    - `monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)` — the exact mock path used by all template/launch tests (12 occurrences in `test_spawn_cli.py`).
    - Plain `assert` with optional f-string reason (TESTING.md §Assertion style); never `unittest.TestCase`.
    - Style: flat `def test_*` functions at module scope (Style B per TESTING.md; matches `test_spawn_cli.py` which is ALL flat functions). Do NOT use a `class TestTemplateRegression:` wrapper — CLI-flavoured tests use flat style.

    What NOT to do:
    - Do NOT assert on prompt TEXT content. RESEARCH.md Pitfall #6: "`test_templates.py` already covers task-owner/task-text semantic correctness; duplicating here makes regression test fragile to intentional copy changes."
    - Do NOT use `pytest-xdist` or any new test-runner plugin (zero-new-required-deps constraint).
    - Do NOT spawn real processes; RecordingBackend covers the need without host-dependent tmux/subprocess flakiness.
    - Do NOT add Windows-specific skip markers — the current CI matrix is ubuntu+macos only per `.github/workflows/ci.yml:24`; Windows is deferred per RESEARCH.md A2.
    - Do NOT add a `conftest.py` entry for this file — autouse `isolated_data_dir` already covers sandboxing.
    - Do NOT parametrize across backends (tmux vs subprocess). The RecordingBackend mock replaces whatever `get_backend` returns; adding a `backend` parametrize axis would 12-case the matrix for zero additional coverage.

    Each template's actual agent count varies (software-dev: 5; hedge-fund: 5; code-review: 3; harness-default: 3; research-paper: 4; strategy-room: 5 — verified from tests/test_templates.py). The assertion `assert backend.calls` (non-empty) is deliberately loose; we don't pin a specific agent count because that's test_templates.py's concern.
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && ruff check tests/test_template_regression_matrix.py && pytest tests/test_template_regression_matrix.py -v --tb=short</automated>
  </verify>
  <done>
    `tests/test_template_regression_matrix.py` exists, ruff-clean, all 12 parametrized cases (6 templates × 2 tests) PASS. Total wall time <10s. No real subprocesses started. Every template's spawn calls populated with valid agent_name + team_name + command list.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Verify CI workflow picks up the new test file (no ci.yml edit expected)</name>
  <files>.github/workflows/ci.yml</files>
  <behavior>
    - `.github/workflows/ci.yml` line 32 runs `python -m pytest tests/ -v --tb=short` — which automatically discovers any `tests/test_*.py` file per pyproject.toml `testpaths = ["tests"]`.
    - Running the documented CI command locally matches the CI job structure (same pytest invocation, same dev install).
    - If any edge case shows the new test file is NOT picked up (very unlikely — pytest auto-discovery is standard), this task documents and applies the fix.
  </behavior>
  <action>
    ### Step 1 — Read .github/workflows/ci.yml and confirm discovery mechanism

    Open `.github/workflows/ci.yml`. Verify:
    - Line 32: `- run: python -m pytest tests/ -v --tb=short`
    - The `tests/` path argument means pytest will auto-discover every `tests/test_*.py` file matching the conftest.py's testpaths configuration.
    - No explicit test file allow-list exists in ci.yml. Good.

    ### Step 2 — Simulate a CI run locally

    Run the exact CI command (ensure dev deps are installed first):

    ```bash
    pip install -e ".[dev]"
    python -m pytest tests/ -v --tb=short 2>&1 | grep -E "test_template_regression_matrix|collected" | head
    ```

    Expected output includes:
    - `collected N items` where N reflects the full suite size + 12 new cases from this plan + tests from plans 00-01, 00-02, 00-03.
    - `tests/test_template_regression_matrix.py::test_template_launches_cleanly[software-dev] PASSED` (and 5 more, plus the 6 `skip_permissions` cases).

    If the new file is listed in collection → CI picks it up automatically. No ci.yml edit required.

    ### Step 3 — Outcome handling

    **Expected (99% case):** CI workflow auto-discovers the new file. No edit required.

    In this case, the deliverable for this task is a NO-OP documented commit: no changes to ci.yml itself. The verification step writes a confirmation note into the plan's SUMMARY.md at the output stage.

    **Unexpected (1% case):** If the local pytest invocation does NOT collect the new file (e.g., pyproject.toml was misconfigured, or the test file has a syntax error preventing collection):
    - Diagnose via `python -m pytest tests/test_template_regression_matrix.py --collect-only -q`.
    - Fix the underlying issue (likely ruff/syntax error reported in Task 1's verify).
    - Do NOT add an explicit file list to ci.yml — the auto-discovery mechanism is the RIGHT pattern for a project using `testpaths`; pinning a file list would harm future test additions.

    ### Step 4 — No actual ci.yml edit in the happy path

    The `files_modified` frontmatter lists `.github/workflows/ci.yml` for BLAST-RADIUS tracking (so Phase 1+ plans know this file was touched in verification). If no edit happens, this is documented in the SUMMARY.md. If a one-line fix ends up being needed, it's the minimum viable adjustment.

    Constraint: Do NOT add a new CI job, do NOT add a matrix axis (e.g., "bc-matrix-py3.10" as a separate job). The existing `test` job already runs on py3.10/3.11/3.12 × ubuntu/macos, which covers the regression matrix six ways already.
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && python -m pytest tests/test_template_regression_matrix.py --collect-only -q 2>&1 | grep -c "test_template" | awk '{ if ($1 >= 12) print "OK collected >=12 cases"; else print "FAIL collected " $1; exit ($1 >= 12 ? 0 : 1) }'</automated>
  </verify>
  <done>
    ci.yml confirmed to auto-discover the new test file via existing `pytest tests/` invocation. The test file is pytest-collected (collect-only shows ≥12 cases). Most likely no ci.yml edit required.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CI environment → test subprocesses | CI runner inherits an environment (GITHUB_TOKEN from the workflow context, repo secrets). The regression matrix tests run under the `isolated_data_dir` autouse fixture, which redirects `HOME` / `USERPROFILE` / `CLAWTEAM_DATA_DIR` to `tmp_path` but does NOT scrub the process env of real GITHUB_TOKEN. |
| test stdout/stderr → CI log | Pytest -v output surfaces test names, assertion messages, and (in tracebacks) env dict contents. Rogue tests could accidentally print env values to CI logs, which are preserved for 90 days per GitHub defaults. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-00-15 | Information Disclosure | regression test prints RecordingBackend.calls contents in failure path → CI log | mitigate | Task 1's assertion messages format `call.get('agent_name')`, `call.get('team_name')`, `call.get('command')` — they intentionally do NOT format `call.get('env')` (which could contain host env vars inherited by the spawn-prep flow). Assertion failures will therefore surface the minimum fields needed for debugging. If a future test author adds `call!r` dumping, they risk env exposure — mitigation is a comment in the file header explaining the discipline. |
| T-00-16 | Tampering | a malicious PR modifies TEMPLATE_NAMES to omit a template → regression matrix shrinks silently | accept | TEMPLATE_NAMES is visible in git diff; reviewers can spot omissions. This is a trust-on-first-use issue that affects every test list in the codebase (e.g., tests/test_templates.py has similar lists). Scope of Phase 0: document the maintenance expectation in the module docstring ("If any template is added/removed, update this list"). |
| T-00-17 | Denial of Service | regression matrix flakes under CI resource pressure → false negatives | accept | With `RecordingBackend` (no real processes), the test is deterministic O(template count × prompt assembly cost). Worst case observed in existing `test_spawn_cli.py` (which has similar pattern): <2s for ~20 launch cases. Our 12 cases targets <3s. Budget is well below the 10-minute job timeout. Flakiness risk is negligible. |
| T-00-18 | Spoofing | test writes to real ~/.clawteam/ because isolated_data_dir fixture failed to apply | mitigate | Task 1 re-asserts `monkeypatch.setenv("CLAWTEAM_DATA_DIR", ...)` inside each test body — belt-and-braces on top of the autouse fixture. RESEARCH.md Pitfall #1 documented this concern; the flat `tests/` layout + explicit monkeypatch + autouse is the defense-in-depth. |
</threat_model>

<verification>
Phase-level verification:

```bash
cd /home/jac/repos/ClawTeam-gstack
ruff check tests/test_template_regression_matrix.py
pytest tests/test_template_regression_matrix.py -v --tb=short
# Time the suite to confirm <10s target
time pytest tests/test_template_regression_matrix.py -q
# Full suite BC check — every existing test still passes
pytest tests/ -q --tb=short
```

Expected:
- ruff exit 0.
- 12 parametrized cases PASS: 6 `test_template_launches_cleanly` + 6 `test_template_spawn_calls_preserve_skip_permissions_flag`.
- Wall time: <10s (target; baseline on dev machine ~2-3s).
- Full suite continues to pass (no BC regression — this plan is purely additive).

CI discovery verification:
```bash
python -m pytest tests/ --collect-only -q | grep test_template_regression_matrix | wc -l
# Expect: >= 12
```

One-liner simulating the CI invocation:
```bash
python -m pytest tests/ -v --tb=short 2>&1 | tail -5
# Last 5 lines should show the pass count including the new 12 cases
```
</verification>

<success_criteria>
1. `tests/test_template_regression_matrix.py` exists as a new file with module docstring, TEMPLATE_NAMES list-literal enumerating all 6 packaged templates, RecordingBackend class definition, and two parametrized test functions.
2. `pytest tests/test_template_regression_matrix.py -v` exits 0 with 12 PASSED cases (6 templates × 2 tests).
3. Total wall time for the regression matrix test file is under 10 seconds.
4. No real processes are spawned — RecordingBackend replaces `clawteam.spawn.get_backend` via monkeypatch for every case.
5. `ruff check tests/test_template_regression_matrix.py` exits 0.
6. `.github/workflows/ci.yml` auto-discovers the new test file via the existing `pytest tests/` invocation — verified by `pytest --collect-only` showing the new file's cases.
7. No existing test in `tests/` regresses — running the full suite still PASSES.
8. Each test case verifies: exit_code == 0, backend.calls non-empty, every call has a non-empty agent_name + correct team_name + non-empty command list.
9. `skip_permissions` propagation test covers all 6 templates (not just hedge-fund).
10. Module docstring documents the expectation that TEMPLATE_NAMES must be updated when templates are added/removed.
</success_criteria>

<output>
After completion, create `.planning/phases/00-foundation-upstream-rfc/00-04-SUMMARY.md` following `@$HOME/.claude/get-shit-done/templates/summary.md`, documenting:
- The 6-template matrix (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) now has a BC regression safety net
- Wall-time measured: actual vs <10s target
- CI discovery: confirmed via `pytest --collect-only`
- Ci.yml edit status: likely NO EDIT NEEDED (auto-discovery via `testpaths`). If an edit happened, the one-line change is documented.
- Follow-on: Phase 1's PhaseRegistry/HarnessPlugin changes must run this suite GREEN before merge
- Deliberate scope boundaries: no prompt-content assertions (owned by test_templates.py), no backend parametrize axis (RecordingBackend obviates it), no Windows CI (deferred per A2)
</output>
