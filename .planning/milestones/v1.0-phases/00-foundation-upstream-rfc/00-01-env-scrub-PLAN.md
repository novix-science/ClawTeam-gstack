---
phase: 00-foundation-upstream-rfc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - clawteam/secrets.py
  - clawteam/events/hooks.py
  - tests/test_env_scrub.py
autonomous: true
requirements:
  - QUALITY-15
tags: [secrets, env-scrub, hooks, security]

must_haves:
  truths:
    - "Running any event hook whose environment contains API_KEY/TOKEN/SECRET/PASSWORD/BEARER/CREDENTIAL-shaped variables never surfaces those values to the spawned subprocess."
    - "scrub_env is importable as a pure function from clawteam.secrets and returns a redacted copy without mutating the input."
    - "The existing test_event_bus shell-hook test continues to pass (no BC regression on hook dispatch)."
  artifacts:
    - path: "clawteam/secrets.py"
      provides: "Pure deny-filter helper: _SECRET_KEY_RE regex constant, _REDACTED placeholder, scrub_env(Mapping[str, str]) -> dict[str, str]"
      contains: "def scrub_env"
      min_lines: 20
    - path: "clawteam/events/hooks.py"
      provides: "Scrubbed env snapshot at the sole documented leak site (line ~81)"
      contains: "from clawteam.secrets import scrub_env"
    - path: "tests/test_env_scrub.py"
      provides: "Unit coverage (class-grouped TestScrubEnv) + shell-hook integration test that a parent-env secret does not leak through"
      contains: "class TestScrubEnv"
      min_lines: 60
  key_links:
    - from: "clawteam/events/hooks.py::_make_shell_handler"
      to: "clawteam/secrets.py::scrub_env"
      via: "import + call on env dict before subprocess.run"
      pattern: "scrub_env\\(_env_snapshot\\(event\\)\\)"
    - from: "tests/test_env_scrub.py"
      to: "clawteam.events.bus.EventBus + HookManager"
      via: "fire WorkerExit event with shell hook that dumps env to a tmp file and assert secret not present"
      pattern: "bus\\.emit\\(WorkerExit"
---

<objective>
Implement the env deny-filter (Pitfall #17 ship-blocker) that prevents secret-shaped environment variables from leaking through ClawTeam's event/hook shell-handler pipeline. This plan creates a pure `scrub_env` helper at the codebase's flat top-level module layout (`clawteam/secrets.py`, NOT `clawteam/util/secrets.py` — the codebase has no `util/` subpackage), extracts the inline env-snapshot idiom from `clawteam/events/hooks.py:81-89` into a named helper, and wires the scrubber at the exact documented leak point.

Purpose: Closes QUALITY-15. Ships the Pitfall #17 preventive control before any other phase's write-site (Phase 6 memory, Phase 2 evidence-gate artifact writes) reuses the helper.

Output:
- New module `clawteam/secrets.py` with `scrub_env()` public API + module-level compiled regex constant.
- Modified `clawteam/events/hooks.py` — extract `_env_snapshot(event)` helper, call `scrub_env` on its return value inside `_make_shell_handler`.
- New test file `tests/test_env_scrub.py` with class-grouped unit tests (Style A, mirrors `test_identity.py::TestEnvHelpers`) + one end-to-end shell-hook integration test proving a parent-env API_KEY does not reach the spawned shell.
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
@.planning/codebase/CONVENTIONS.md
@.planning/codebase/TESTING.md
@clawteam/events/hooks.py
@clawteam/paths.py
@clawteam/identity.py
@tests/test_identity.py
@tests/test_event_bus.py

<interfaces>
<!-- Key types and patterns the executor will use. Extract-then-integrate — no codebase exploration needed. -->

From clawteam/paths.py (analog for module-level compiled regex + pure helper):
```python
"""Helpers for validating logical identifiers and constraining data paths."""

from __future__ import annotations

import re
from pathlib import Path

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_identifier(value: str, kind: str = "identifier", allow_empty: bool = False) -> str:
    """Validate a logical identifier used in filesystem-backed state."""
    ...
```

From clawteam/events/hooks.py — the current env-build block at lines 77-103 that this plan modifies:
```python
def _make_shell_handler(command: str):
    """Create a handler that runs a shell command with event data as env vars."""

    def handler(event: HarnessEvent) -> int | None:
        env = os.environ.copy()                                    # <-- leak site
        env["CLAWTEAM_EVENT_TYPE"] = type(event).__name__
        for key, value in asdict(event).items():
            env_key = f"CLAWTEAM_{key.upper()}"
            if isinstance(value, list):
                env[env_key] = ",".join(str(v) for v in value)
            else:
                env[env_key] = str(value) if value is not None else ""
            env[f"OH_{key.upper()}"] = env[env_key]
        try:
            result = subprocess.run(
                command,
                shell=True,
                env=env,
                capture_output=True,
                timeout=30,
            )
            return result.returncode
        except Exception as exc:
            print(f"[clawteam] hook error: {exc}", file=sys.stderr)
            return None

    return handler
```

From tests/test_identity.py::TestEnvHelpers (Style A test shape to mirror):
```python
class TestEnvHelpers:
    def test_env_reads_oh_first(self, monkeypatch):
        monkeypatch.setenv("CLAWTEAM_AGENT_NAME", "alpha")
        monkeypatch.setenv("CLAUDE_CODE_AGENT_NAME", "beta")
        assert _env("CLAWTEAM_AGENT_NAME", "CLAUDE_CODE_AGENT_NAME") == "alpha"
```

From tests/test_event_bus.py::TestHookManager::test_shell_hook (shell-hook assertion idiom — use the same tmp_path/marker trick):
```python
class TestHookManager:
    def test_shell_hook(self, tmp_path):
        from clawteam.events.hooks import HookDef, HookManager
        bus = EventBus()
        mgr = HookManager(bus)
        marker = tmp_path / "marker.txt"
        hook = HookDef(event="WorkerExit", action="shell", command=f"touch {marker}")
        assert mgr.register_hook(hook) is True
        bus.emit(WorkerExit(team_name="test"))
        assert marker.exists()
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create clawteam/secrets.py with scrub_env helper</name>
  <files>clawteam/secrets.py</files>
  <behavior>
    - scrub_env({"OPENAI_API_KEY": "sk-abc", "PATH": "/usr/bin"}) returns {"OPENAI_API_KEY": "[REDACTED]", "PATH": "/usr/bin"}
    - scrub_env({}) returns {}
    - Keys matching SECRET|TOKEN|KEY|PASSWORD|BEARER|CREDENTIAL|PASSWD|AUTH (case-insensitive) are redacted
    - Keys NOT matching (PATH, HOME, USER, CLAWTEAM_AGENT_NAME, LANG, CLAWTEAM_DATA_DIR, ANTHROPIC_BASE_URL) pass through untouched
    - Input dict is NEVER mutated; return is always a fresh dict (not Mapping)
    - Case-insensitive matching: "lower_case_secret" is still redacted
  </behavior>
  <action>
    Create `clawteam/secrets.py` (FLAT path at top level — the codebase has NO `util/` subpackage per PATTERNS.md; sibling modules are `clawteam/paths.py`, `clawteam/fileutil.py`, `clawteam/identity.py`, `clawteam/timefmt.py`).

    Module skeleton (follow CONVENTIONS.md §Module Header exactly — one-line docstring, blank line, `from __future__ import annotations`, blank line, stdlib imports, NO clawteam.* imports to keep this a leaf module so `hooks.py` can import without cycle):

    ```python
    """Deny-filter helpers for scrubbing secrets from env snapshots and logs."""

    from __future__ import annotations

    import re
    from typing import Mapping

    _SECRET_KEY_RE = re.compile(
        r"(SECRET|TOKEN|KEY|PASSWORD|BEARER|CREDENTIAL|PASSWD|AUTH)",
        re.IGNORECASE,
    )
    _REDACTED = "[REDACTED]"


    def scrub_env(env: Mapping[str, str]) -> dict[str, str]:
        """Return a copy of *env* with values redacted when the key matches the deny regex.

        Keys are tested with ``re.search`` (case-insensitive). Values are replaced with a
        fixed placeholder; no attempt is made to partial-redact tokens embedded inside
        longer strings — callers that need value-level scrubbing should wrap this helper.

        The input mapping is never mutated. The return type is ``dict`` (not ``Mapping``)
        so callers can subsequently set ``CLAWTEAM_*`` / ``OH_*`` keys on the result.
        """
        return {k: (_REDACTED if _SECRET_KEY_RE.search(k) else v) for k, v in env.items()}
    ```

    Rules enforced (per QUALITY-15 and PATTERNS.md):
    - FLAT layout: `clawteam/secrets.py`, NOT `clawteam/util/secrets.py` (matches `paths.py`, `fileutil.py`, `timefmt.py`, `identity.py` convention).
    - Module-level compiled regex constant `_SECRET_KEY_RE` (mirrors `paths.py:8` `_IDENTIFIER_RE`).
    - Upper-snake private constant names with underscore prefix.
    - Pure function — no `logging`, no `rich`, no I/O, no `typer.Exit` (library layer per CONVENTIONS.md §Error Handling).
    - Concrete `dict[str, str]` return type (not `Mapping`); built-in generics work because of `from __future__ import annotations`.
    - No `clawteam.*` imports. Stdlib only.

    Do NOT add value-level scanning (no `.*://.+:.+@.+` URL-embedded-secret pattern — A10 in RESEARCH.md flags this as low priority, no preset uses it; deferring keeps scope tight). Do NOT add an allow-list structure — the deny regex is a superset-match approach; the patterns chosen do not false-positive on canonical ClawTeam envs (`CLAWTEAM_AGENT_NAME`, `CLAWTEAM_DATA_DIR`, `ANTHROPIC_BASE_URL` do not contain KEY/TOKEN/SECRET/PASSWORD/BEARER/CREDENTIAL/PASSWD/AUTH substrings).

    Verify by eye: every regex token is uppercase (used with `re.IGNORECASE`); no trailing anchors that would require exact end-match.
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && ruff check clawteam/secrets.py && python -c "from clawteam.secrets import scrub_env; assert scrub_env({'API_KEY': 'x', 'PATH': '/bin'}) == {'API_KEY': '[REDACTED]', 'PATH': '/bin'}; assert scrub_env({}) == {}; print('OK')"</automated>
  </verify>
  <done>
    `clawteam/secrets.py` exists, passes ruff (E, F, I, N, W rules), `scrub_env` importable, basic smoke assertion inline succeeds.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extract _env_snapshot helper in hooks.py and wire scrub_env</name>
  <files>clawteam/events/hooks.py</files>
  <behavior>
    - _env_snapshot(event) returns a dict containing os.environ.copy() + CLAWTEAM_EVENT_TYPE + per-event-field CLAWTEAM_*/OH_* entries (i.e., same dict that the current inline block at lines 81-89 produces).
    - _make_shell_handler calls env = scrub_env(_env_snapshot(event)) before subprocess.run.
    - Canonical CLAWTEAM_* / OH_* identity envs STILL reach the subprocess (they do not match the deny regex).
    - API_KEY / TOKEN / SECRET / PASSWORD parent-env values do NOT reach the subprocess.
    - Existing test_event_bus.py::TestHookManager::test_shell_hook still passes (marker file still touched; no behavior regression on hook dispatch path).
  </behavior>
  <action>
    Modify `clawteam/events/hooks.py` to (a) extract the inline env-building block at lines 81-89 into a module-private `_env_snapshot(event: HarnessEvent) -> dict[str, str]` helper, and (b) wrap it with `scrub_env` inside `_make_shell_handler`.

    Step 1 — Add import at the top of the first-party imports block (keep the three-group ruff `I` order: `__future__`, stdlib, first-party):

    ```python
    from clawteam.secrets import scrub_env
    ```

    Insert this alphabetically among existing `from clawteam.events.bus import EventBus` / `from clawteam.events.types import HarnessEvent` imports. `clawteam.secrets` sorts before `clawteam.events.bus`.

    Step 2 — Insert new helper `_env_snapshot` ABOVE `_make_shell_handler` (ordering: helpers listed top-to-bottom from outermost usage, matching PATTERNS.md recommendation for helper placement in this file). Place it immediately above `_make_shell_handler` (current line 77) and below `_resolve_event_type` (current lines 71-74):

    ```python
    def _env_snapshot(event: HarnessEvent) -> dict[str, str]:
        """Build the env dict a shell hook receives: inherited env + CLAWTEAM_*/OH_* event fields."""
        env = os.environ.copy()
        env["CLAWTEAM_EVENT_TYPE"] = type(event).__name__
        for key, value in asdict(event).items():
            env_key = f"CLAWTEAM_{key.upper()}"
            if isinstance(value, list):
                env[env_key] = ",".join(str(v) for v in value)
            else:
                env[env_key] = str(value) if value is not None else ""
            env[f"OH_{key.upper()}"] = env[env_key]
        return env
    ```

    This is a verbatim extraction of the current inline block at lines 81-89 (plus the `env = os.environ.copy()` line and the `CLAWTEAM_EVENT_TYPE` assignment). Zero behavior change at this step.

    Step 3 — Replace the inline block inside `_make_shell_handler.handler` so the function body becomes:

    ```python
    def _make_shell_handler(command: str):
        """Create a handler that runs a shell command with event data as env vars."""

        def handler(event: HarnessEvent) -> int | None:
            env = scrub_env(_env_snapshot(event))
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    env=env,
                    capture_output=True,
                    timeout=30,
                )
                return result.returncode
            except Exception as exc:
                print(f"[clawteam] hook error: {exc}", file=sys.stderr)
                return None

        return handler
    ```

    The `try/except/subprocess.run` block remains unchanged — we only replace the env-build section.

    Critical correctness notes:
    - `scrub_env` runs AFTER `_env_snapshot` populates CLAWTEAM_EVENT_TYPE and CLAWTEAM_*/OH_* fields. This is correct: per PATTERNS.md, event field names like `team_name`, `agent_name`, `phase` do NOT match the deny regex, so those CLAWTEAM_*/OH_* keys pass through untouched. The ONLY keys redacted are the inherited `os.environ.copy()` ones that match the deny patterns.
    - DO NOT scrub BEFORE populating the CLAWTEAM_*/OH_* keys — that would be equivalent behavior here but breaks the "scrub at the boundary" invariant stated in PATTERNS.md.
    - DO NOT apply `scrub_env` to the spawn backends' `os.environ.copy()` sites (subprocess_backend.py, tmux_backend.py, wsh_backend.py). Child processes need real `ANTHROPIC_API_KEY` etc. Deferred per RESEARCH.md Open Question #2 and A10.

    After these edits, run `ruff check clawteam/events/hooks.py` — the file should still pass (import order preserved, no unused imports).
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && ruff check clawteam/events/hooks.py && pytest tests/test_event_bus.py -q</automated>
  </verify>
  <done>
    hooks.py imports `scrub_env`, has module-private `_env_snapshot` helper, `_make_shell_handler` uses `scrub_env(_env_snapshot(event))`. Existing `test_event_bus.py` passes unchanged (no BC regression on shell-hook dispatch).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create tests/test_env_scrub.py with unit + integration coverage</name>
  <files>tests/test_env_scrub.py</files>
  <behavior>
    - TestScrubEnv.test_matching_keys_are_redacted: every key in [API_KEY, OPENAI_API_KEY, SECRET_TOKEN, MY_PASSWORD, BEARER_TOKEN, CREDENTIAL_FILE, lower_case_secret, GITHUB_TOKEN, CLIENT_SECRET, AWS_ACCESS_KEY_ID, DB_PASSWORD] has its value redacted to "[REDACTED]".
    - TestScrubEnv.test_non_matching_keys_are_untouched: every key in [PATH, HOME, USER, LANG, CLAWTEAM_AGENT_NAME, CLAWTEAM_DATA_DIR, CLAWTEAM_TEAM_NAME, OH_AGENT_NAME, ANTHROPIC_BASE_URL, OPENAI_BASE_URL] passes through unchanged.
    - TestScrubEnv.test_input_dict_is_not_mutated: scrub_env({"API_KEY": "abc"}) does NOT mutate the input.
    - TestScrubEnv.test_returns_dict_not_mapping: return type is `dict` (mutable).
    - TestScrubEnv.test_empty_env: scrub_env({}) == {}.
    - test_shell_hook_env_snapshot_redacts_parent_secrets: When parent env has MY_API_KEY=super-secret and a WorkerExit triggers a shell hook that dumps env to a file, the dumped file does NOT contain "super-secret" but DOES contain CLAWTEAM_* identity values.
  </behavior>
  <action>
    Create `tests/test_env_scrub.py` following Style A (class-grouped, mirrors `tests/test_identity.py::TestEnvHelpers`). Use the `isolated_data_dir` autouse fixture from `tests/conftest.py:10-19` — which is active automatically for every test in `tests/`, so no extra fixture plumbing is needed.

    Full file content:

    ```python
    """Tests for clawteam.secrets — env deny-filter scrubber (QUALITY-15)."""

    import pytest

    from clawteam.secrets import scrub_env


    class TestScrubEnv:
        """scrub_env redacts values whose key matches the secret deny-pattern."""

        @pytest.mark.parametrize(
            "key",
            [
                "API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
                "SECRET_TOKEN",
                "MY_PASSWORD",
                "DB_PASSWORD",
                "BEARER_TOKEN",
                "CREDENTIAL_FILE",
                "GITHUB_TOKEN",
                "CLIENT_SECRET",
                "AWS_ACCESS_KEY_ID",
                "SSH_PRIVATE_KEY",
                "lower_case_secret",
                "MixedCaseToken",
            ],
        )
        def test_matching_keys_are_redacted(self, key):
            result = scrub_env({key: "sensitive-value", "SAFE": "ok"})
            assert result[key] == "[REDACTED]"
            assert result["SAFE"] == "ok"

        @pytest.mark.parametrize(
            "key",
            [
                "PATH",
                "HOME",
                "USER",
                "LANG",
                "LC_CTYPE",
                "CLAWTEAM_AGENT_NAME",
                "CLAWTEAM_DATA_DIR",
                "CLAWTEAM_TEAM_NAME",
                "OH_AGENT_NAME",
                "CLAUDE_CODE_AGENT_NAME",
                "ANTHROPIC_BASE_URL",
                "OPENAI_BASE_URL",
            ],
        )
        def test_non_matching_keys_are_untouched(self, key):
            result = scrub_env({key: "value"})
            assert result[key] == "value"

        def test_input_dict_is_not_mutated(self):
            env = {"API_KEY": "abc", "PATH": "/bin"}
            scrub_env(env)
            assert env == {"API_KEY": "abc", "PATH": "/bin"}

        def test_returns_dict_not_mapping(self):
            result = scrub_env({})
            assert isinstance(result, dict)

        def test_empty_env(self):
            assert scrub_env({}) == {}

        def test_redact_placeholder_value(self):
            result = scrub_env({"API_KEY": "sk-xxx"})
            assert result["API_KEY"] == "[REDACTED]"


    def test_shell_hook_env_snapshot_redacts_parent_secrets(tmp_path, monkeypatch):
        """End-to-end: a parent-env API key must NOT reach the spawned shell hook."""
        from clawteam.events.bus import EventBus
        from clawteam.events.hooks import HookDef, HookManager
        from clawteam.events.types import WorkerExit

        monkeypatch.setenv("MY_API_KEY", "super-secret-value")
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_should-not-leak")
        monkeypatch.setenv("DB_PASSWORD", "hunter2")

        dump = tmp_path / "env.dump"
        bus = EventBus()
        mgr = HookManager(bus)
        hook = HookDef(
            event="WorkerExit",
            action="shell",
            command=f'env > "{dump}"',
        )
        assert mgr.register_hook(hook) is True

        bus.emit(WorkerExit(team_name="t", agent_name="a"))

        content = dump.read_text()
        assert "super-secret-value" not in content
        assert "ghp_should-not-leak" not in content
        assert "hunter2" not in content
        # Identity envs still reach the subprocess
        assert "CLAWTEAM_EVENT_TYPE=WorkerExit" in content
        assert "CLAWTEAM_TEAM_NAME=t" in content
        assert "CLAWTEAM_AGENT_NAME=a" in content
    ```

    Rules (per PATTERNS.md §tests/test_env_scrub.py and TESTING.md):
    - Module docstring (one line, required per CONVENTIONS.md §Module Header).
    - NO `from __future__ import annotations` needed in test files (optional; existing test_identity.py does not have it — follow that precedent).
    - Class-grouped Style A for pure-helper unit tests (matches `test_identity.py::TestEnvHelpers`, `test_paths.py::TestValidateIdentifier`).
    - Flat `test_*` function for the shell-hook integration test (it does not fit the "pure helper" grouping).
    - `@pytest.mark.parametrize("key", [...])` with multi-line list + trailing comma (matches `test_paths.py:13-25`).
    - Plain `assert`, no `unittest.TestCase`.
    - `isolated_data_dir` autouse fixture is implicit (TESTING.md §Shared Fixtures); do not override or disable.
    - WorkerExit event import from `clawteam.events.types` matches existing `test_event_bus.py:10` usage.

    Do NOT add a test that extends the existing `test_event_bus.py::TestHookManager` class — keep the new integration test in the new file to preserve one-file-per-concern symmetry.

    Do NOT add a regression test asserting spawn backends still propagate `ANTHROPIC_API_KEY` to child processes — that's out of scope for this plan (spawn backends are not modified). Research Open Question #2 confirms: we do NOT apply scrub_env to spawn backends; if a future regression lands it would be caught by existing `test_spawn_cli.py:309-341` which already asserts on `KIMI_API_KEY` reaching `backend.calls[0]["env"]`.
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && ruff check tests/test_env_scrub.py && pytest tests/test_env_scrub.py -v</automated>
  </verify>
  <done>
    `tests/test_env_scrub.py` exists, ruff-clean, all TestScrubEnv parametrized cases pass, shell-hook integration test passes (dump file does not contain any of the three parent-env secrets; CLAWTEAM_* identity envs are present).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| parent process env → shell-hook subprocess | Inherited OS env variables cross a trust boundary when ClawTeam forks a shell hook. Secrets in the parent shell (user's exported API keys) leak to every hook command and its stdout capture. |
| shell-hook subprocess stdout → captured logs/transcripts | `subprocess.run(capture_output=True)` retains command output; if the hook shell echoes $OPENAI_API_KEY, it lands in `result.stdout` which future observability phases may persist. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-00-01 | Information Disclosure | `clawteam/events/hooks.py::_make_shell_handler` env dict | mitigate | Task 2 wraps the env dict with `scrub_env` before passing to `subprocess.run(env=...)`. Secret-shaped keys (regex KEY/TOKEN/SECRET/PASSWORD/BEARER/CREDENTIAL/PASSWD/AUTH, case-insensitive) have values replaced with `[REDACTED]` before the child can read them. Verified by Task 3's end-to-end shell-hook test. |
| T-00-02 | Information Disclosure | downstream memory / board / evidence-gate ingestion (Phase 2/6) | mitigate | `clawteam.secrets.scrub_env` is a reusable leaf-module helper with no `clawteam.*` imports, so future phases can call it at their write-sites (Phase 6 `/learn` memory per RESEARCH.md line 243). This plan exposes the helper; Phase 6 binds it. |
| T-00-03 | Information Disclosure | spawn backends (subprocess/tmux/wsh) `os.environ.copy()` → child process env | accept | Spawn-backend env dicts MUST retain real `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` etc. so child CLIs authenticate to providers. RESEARCH.md Open Question #2 + A10 confirm this is the deliberate boundary. Accepted risk: the child process is the legitimate consumer of the real secret; any leak from there is downstream (Phase 6 mitigates memory ingestion separately). |
| T-00-04 | Tampering | deny-filter regex bypass via unknown naming conventions (e.g., provider uses `FOO_AUTHN_STRING`) | accept | The current regex covers the 8 canonical substrings observed across the 9 CLI adapters in `clawteam/spawn/presets.py`. A provider using a non-matching name would leak until the regex is updated. Mitigation: Phase 0 lands the pattern list; future phases (Phase 2 observability, Phase 6 memory) can extend the pattern set via a single regex edit. Low likelihood (providers overwhelmingly use KEY/TOKEN/SECRET naming). |
| T-00-05 | Denial of Service | regex catastrophic backtracking on huge env values | accept | The regex matches against env-var *names* (key names are short; max seen ~40 chars), never against values. No nested quantifiers (`.*.*`), no alternation + quantifier combos. Safe by construction. |
</threat_model>

<verification>
Phase-level verification:

```bash
cd /home/jac/repos/ClawTeam-gstack
ruff check clawteam/secrets.py clawteam/events/hooks.py tests/test_env_scrub.py
pytest tests/test_env_scrub.py tests/test_event_bus.py -v --tb=short
```

Expected:
- ruff returns exit 0 (no lint violations in any modified/new file).
- test_env_scrub.py: all TestScrubEnv parametrized cases PASS; test_shell_hook_env_snapshot_redacts_parent_secrets PASSES.
- test_event_bus.py: all existing cases PASS (no BC regression on hook dispatch, shell-hook marker test still works).

Smoke check scrub_env from Python REPL:
```bash
python -c "from clawteam.secrets import scrub_env; d = scrub_env({'API_KEY': 'x', 'PATH': '/bin', 'CLAWTEAM_AGENT_NAME': 'alpha'}); assert d['API_KEY'] == '[REDACTED]' and d['PATH'] == '/bin' and d['CLAWTEAM_AGENT_NAME'] == 'alpha'; print('scrub_env smoke OK')"
```
</verification>

<success_criteria>
1. File `clawteam/secrets.py` exists, exports `scrub_env`, module-level `_SECRET_KEY_RE` compiled regex, `_REDACTED = "[REDACTED]"`. Passes ruff under the E/F/I/N/W rule set.
2. `clawteam/events/hooks.py` imports `scrub_env` from `clawteam.secrets`, contains module-private `_env_snapshot(event)` helper, `_make_shell_handler.handler` calls `env = scrub_env(_env_snapshot(event))` before `subprocess.run`.
3. `tests/test_env_scrub.py` exists with 2+ parametrized unit tests covering ~14 secret-shaped keys and ~12 non-secret keys, plus one end-to-end shell-hook integration test asserting three distinct parent-env secrets (API_KEY/TOKEN/PASSWORD shapes) do not leak through.
4. Existing `tests/test_event_bus.py` continues to pass unchanged (BC guarantee — hook dispatch path uncorrupted).
5. Running `ruff check clawteam/ tests/` (full codebase lint) exits 0 after all three tasks.
6. scrub_env smoke check from Python REPL returns the expected redacted-vs-preserved result.
</success_criteria>

<output>
After completion, create `.planning/phases/00-foundation-upstream-rfc/00-01-SUMMARY.md` following `@$HOME/.claude/get-shit-done/templates/summary.md`, documenting:
- scrub_env API surface + regex pattern list (for future Phase 2/6 consumers)
- The extract-then-scrub refactor of hooks.py (what was inline, what's now a helper)
- Follow-up hooks: Phase 2 (evidence-gate artifact writes), Phase 6 (memory ingestion) should reuse `scrub_env` at their respective write-sites
- Explicit non-change: spawn backends' `os.environ.copy()` sites UNMODIFIED (child processes need real secrets)
</output>
