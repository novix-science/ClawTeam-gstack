# Phase 0: Foundation & Upstream RFC - Pattern Map

**Mapped:** 2026-04-15
**Files analyzed:** 8 (4 new source/test files, 2 modified source files, 2 new docs)
**Analogs found:** 8 / 8 (one new-ground file — the RFC README)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `clawteam/util/secrets.py` (new) | utility (pure helper, no I/O) | transform | `clawteam/paths.py` | exact (role+flow) |
| `clawteam/events/hooks.py` (modified) | service (hook registry + shell handler) | event-driven / transform | self (existing file — minimal additive change) | N/A |
| `clawteam/cli/commands.py` (modified — `doctor` subcommand) | CLI command | request-response | `clawteam/cli/commands.py::config_health` (lines 1080–1145) + `profile_doctor` (1035–1077) | exact |
| `clawteam/config.py` (modified — new field) | model (pydantic v2 BaseModel) | N/A (schema only) | self — one-line field add next to `default_profile` (config.py:54) | exact |
| `tests/test_template_regression_matrix.py` (new) | test (CLI-driven integration) | request-response | `tests/test_spawn_cli.py::test_launch_cli_applies_profile_to_template_agents` (309–341) + `test_paths.py` parametrize style (13–26) | exact |
| `tests/test_env_scrub.py` (new) | test (pure unit) | transform | `tests/test_identity.py::TestEnvHelpers` (6–35) | exact |
| `tests/test_doctor.py` (new) | test (CLI via CliRunner) | request-response | `tests/test_cli_commands.py::test_lifecycle_check_zombies_reports_clean_state` (437–449) + `test_config_cli_supports_all_keys_and_bool_values` (13–34) | exact |
| `docs/rfcs/001-phase-registry.md` (new) | documentation | N/A | `docs/transport-architecture.md` (markdown tone, box diagrams) | partial (tone only) |
| `docs/rfcs/README.md` (new) | documentation (index) | N/A | *no existing README under `docs/` — new ground* | **no analog** |

---

## Pattern Assignments

### `clawteam/util/secrets.py` (utility, transform)

> Note: `clawteam/util/` does not yet exist as a subpackage. The codebase uses **flat top-level helpers** at `clawteam/<name>.py` (see `paths.py`, `fileutil.py`, `timefmt.py`, `identity.py`). Planner should resolve this tension explicitly — the cleanest fit is to create `clawteam/util/__init__.py` + `clawteam/util/secrets.py` **only if** the planner wants to group future util modules, otherwise rename to `clawteam/secrets.py` to match the existing flat convention. Either way, the patterns below apply.

**Analogs:** `clawteam/paths.py` (whole file — 34 LOC, pure helper with module-level compiled regex) and `clawteam/identity.py::_env` (lines 10–36, for the "accept multiple inputs, return scrubbed output" shape).

**Module header + imports pattern** (copy from `clawteam/paths.py:1-7`):
```python
"""Deny-filter helpers for scrubbing secrets from env snapshots and logs."""

from __future__ import annotations

import re
from typing import Mapping
```
Rules: one-line module docstring (mandatory — see CONVENTIONS.md §Module Header); `from __future__ import annotations` always; stdlib-only imports; no `clawteam.*` imports (this must be a leaf module so `hooks.py` can depend on it without introducing a cycle).

**Module-level compiled regex constant pattern** (copy shape from `clawteam/paths.py:8`):
```python
_SECRET_KEY_RE = re.compile(
    r"(SECRET|TOKEN|KEY|PASSWORD|BEARER|CREDENTIAL|PASSWD|AUTH)",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"
```
Rules: underscore-prefixed module-level private constants; `UPPER_SNAKE` names; compile regex once at import time (mirrors `_IDENTIFIER_RE` at `paths.py:8`).

**Pure-function API pattern** (copy shape from `clawteam/paths.py::ensure_within_root`):
```python
def scrub_env(env: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of *env* with values redacted when the key matches the deny regex.

    Keys are tested with re.search (case-insensitive). Values are replaced with
    a fixed placeholder; no attempt is made to partial-redact tokens embedded
    inside longer strings — callers that need value-level scrubbing should
    wrap this helper.
    """
    return {k: (_REDACTED if _SECRET_KEY_RE.search(k) else v) for k, v in env.items()}
```
Rules: snake_case function name, concrete return type (`dict[str, str]`, not `Mapping`), one-line operational docstring that describes the contract and any intentional omissions (mirrors `paths.py:24-26`'s "reject escapes" docstring style).

**Error handling pattern:** Prefer `ValueError` for invalid input, but for this helper the only realistic failure mode is a non-string value inside `env`. Let it raise `TypeError` naturally through the dict comprehension rather than catching — library layer **never** calls `typer.Exit` or `sys.exit` (CONVENTIONS.md §Error Handling).

**What NOT to do:** Do not use `logging`, do not use `rich.Console`, do not mutate the input mapping, do not add I/O. This must stay a pure function so the hooks integration point can call it without side effects.

---

### `clawteam/events/hooks.py` (modified — invoke scrubber at env-write site)

> **Important clarification:** The research doc references a `_env_snapshot()` function, but **no such function exists yet** in `clawteam/events/hooks.py`. The actual "env snapshot write-site" is `_make_shell_handler` at **lines 77–103**, which builds the env dict handed to `subprocess.run(...)`. The planner should either (a) inline the scrubber call inside `_make_shell_handler` at line 89, or (b) extract an `_env_snapshot(event)` helper first and then call `scrub_env()` on its return value. Option (b) is cleaner and more testable.

**Analog:** self — minimal additive change. The existing env-build idiom at `hooks.py:81-89` is the canonical pattern:
```python
env = os.environ.copy()
env["CLAWTEAM_EVENT_TYPE"] = type(event).__name__
for key, value in asdict(event).items():
    env_key = f"CLAWTEAM_{key.upper()}"
    if isinstance(value, list):
        env[env_key] = ",".join(str(v) for v in value)
    else:
        env[env_key] = str(value) if value is not None else ""
    env[f"OH_{key.upper()}"] = env[env_key]
```

**Required change — extract-then-scrub pattern** (recommended):
1. Extract lines 81–89 into a new module-private helper `def _env_snapshot(event: HarnessEvent) -> dict[str, str]:` placed just above `_make_shell_handler` (ordering: helpers listed top-to-bottom from outermost usage).
2. In `_make_shell_handler`, replace the inline block with `env = scrub_env(_env_snapshot(event))`.
3. Add import at top: `from clawteam.util.secrets import scrub_env` (or `from clawteam.secrets import scrub_env` if the planner chose flat layout). Place in the first-party import group (CONVENTIONS.md §Import Organization).

**Why scrub here and not in the handler body?** The env dict is the handoff point between in-process state and an external shell process. CONVENTIONS.md §Defensive fallbacks calls for silent degradation at environment boundaries — this is the analogous boundary for secrets.

**Backward-compat note:** `os.environ.copy()` at line 81 inherits the full parent env, so the scrubber MUST operate on that post-copy dict before it's extended with `CLAWTEAM_*`/`OH_*` keys. Scrubbing BEFORE the loop is correct (the loop values come from `asdict(event)`, not from os.environ, and event field names like `team_name` / `agent_name` will not match the deny regex).

**Test-side observation:** Existing `test_event_bus.py::TestHookManager::test_shell_hook` (lines 104–118) uses a tmp_path marker-file trick — the scrubber test should piggyback on that pattern to verify a `SECRET_*` parent-env var does NOT reach the spawned shell.

---

### `clawteam/cli/commands.py` — new `doctor` subcommand (modified, CLI, request-response)

**Primary analog:** `config_health` at `clawteam/cli/commands.py:1080-1145` (health check with per-subsystem probes rendered as rich-formatted sections with `--json` override). **Secondary analog:** `profile_doctor` at `commands.py:1035-1077` (gives the command its name precedent).

**Placement decision** — the phase_context lists both "modified commands.py OR new subcommand module". Given the codebase's convention of keeping Typer wiring inside `commands.py` (STRUCTURE.md §Where to Add New Code: "New CLI subcommand: Add a Typer command to `clawteam/cli/commands.py`"), **add directly to `commands.py`** as a top-level `@app.command("doctor")`. Do not create a new `clawteam/cli/doctor.py` module — that would introduce a convention break for one command.

**Section banner pattern** (required — copy from `commands.py:3860-3862`):
```python
# ============================================================================
# Doctor Command
# ============================================================================

@app.command("doctor")
def doctor():
    """Check optional external tools and print per-OS install hints."""
```
Rules: 76-char banner lines with `====` (CONVENTIONS.md §Comments & Docstrings), one-line command docstring that reads as help text (Typer surfaces it via `--help`).

**Tool-probe body pattern** (copy from `config_health` at 1080–1128):
```python
import shutil
import sys

checks: dict[str, dict[str, object]] = {}

for tool_name, probe in _DOCTOR_TOOLS:
    found = shutil.which(probe)
    checks[tool_name] = {
        "found": bool(found),
        "path": found or "",
        "install_hint": _doctor_install_hint(tool_name, sys.platform),
    }
```
Rules: lazy imports inside the function body (same pattern as `config_health` at 1083–1088 lazy-imports `os` and `time`); use `shutil.which` to probe tools (established at `clawteam/board/gource.py:301`, `spawn/wsh_backend.py:195`, `spawn/tmux_backend.py:60`); assemble a plain `dict` of results; render with rich table + `--json` fallback via `_output()` (commands.py:77-84).

**Per-OS install-hint dispatch pattern** (follow `clawteam/fileutil.py:22-25` for the platform branch convention):
```python
if sys.platform == "darwin":
    return "brew install chromium"
elif sys.platform == "win32":
    return "winget install Chromium.Chromium"
else:  # Linux and friends
    return "apt install chromium-browser  # or: nix-env -iA nixpkgs.chromium"
```
Rules: branch on `sys.platform == "win32" | "darwin"` with an `else` fallback for Linux (the established triple-branch pattern seen in `fileutil.py`, `store/file.py`, `transport/file.py`, `team/snapshot.py`). **Do not** use `platform.system()` — `sys.platform` is the codebase standard.

**Tools to probe** (from phase_context): `chromium` or `google-chrome` (for Playwright), `codex`, `ngrok`, `watchdog` is a Python module — probe via `importlib.util.find_spec("watchdog")` not `shutil.which`. Store the tool list as a module-level constant tuple `_DOCTOR_TOOLS` (UPPER_SNAKE as an underscore-private module state, matching `_json_output` / `_data_dir` at `commands.py:34-35`).

**Output dual-format pattern** (mandatory — copy from `config_health:1134-1145`):
```python
def _human(d):
    console.print("\n[bold]Optional tool check:[/bold]\n")
    for tool, info in d.items():
        ok = "[green]OK[/green]" if info["found"] else "[yellow]missing[/yellow]"
        console.print(f"  {ok}  {tool}")
        if not info["found"]:
            console.print(f"       hint: [dim]{info['install_hint']}[/dim]")

_output(checks, _human)
```
Rules: define an inner `_human(d)` closure (mirrors every other command in `commands.py`); print using `console.print` (the module-level `Console()` at `commands.py:27`); use rich markup tags `[green]...[/green]` / `[yellow]...[/yellow]` / `[dim]...[/dim]` (consistent throughout commands.py); final call to `_output(data, _human)` which handles the `--json` mode automatically.

**Error handling:** Doctor is a read-only probe — no failure modes except ImportError from `importlib.util`, which should be swallowed (treat as "missing"). Do NOT `raise typer.Exit(1)` when tools are missing — exit 0 is intentional (doctor is informational, not a gate). This matches `config_health`, which never raises.

---

### `clawteam/config.py` — add `default_model_profile` field (modified, model, schema-only)

**Analog:** self — the file itself (`clawteam/config.py:50-69`). This is a one-line additive change to an existing pydantic v2 BaseModel.

**Field-add pattern** — insert immediately below `default_profile` at line 54 to keep related fields adjacent:
```python
class ClawTeamConfig(BaseModel):
    data_dir: str = ""
    user: str = ""
    default_team: str = ""
    default_profile: str = ""
    default_model_profile: str = "balanced"   # NEW — model tier preset (balanced | quality | budget)
    transport: str = ""
    ...
```
Rules: pydantic v2 `str` field with immediate default (matches all sibling scalar fields at 51–66); no `Field(default_factory=...)` — this is a simple scalar, not a mutable container; trailing line comment in the same style as existing ones (`"file" (default) — extensible for redis/sql later`, `"tmux" | "subprocess"`); default must be `"balanced"` per PROJECT.md Decision row 1 — NEVER `"quality"`. Canonical tier values are **balanced | quality | budget** per REQUIREMENTS.md TEAM-05 (NOT `cost` — the user-facing CLI flag is `--model-profile balanced|quality|budget`).

**Deliberate divergence from `default_profile` pattern — DO NOT add an env_map entry:**

Earlier drafts of this PATTERNS.md recommended adding `"default_model_profile": "CLAWTEAM_DEFAULT_MODEL_PROFILE"` to the `env_map` in `get_effective` for parity with `default_profile`. That recommendation is **superseded** by ROADMAP Phase 0 success criterion 5, which restricts opt-in to `--model-profile` CLI flag or config file — explicitly NOT env var. Wiring the env var in would enable the exact "silent quality promotion via exported shell" failure mode Pitfall #12 prevents.

```python
env_map = {
    ...
    "default_profile": "CLAWTEAM_DEFAULT_PROFILE",
    # NOTE: default_model_profile intentionally omitted — per ROADMAP criterion 5,
    # opt-in to non-default profile is CLI flag or config file only (Pitfall #12).
    "transport": "CLAWTEAM_TRANSPORT",
    ...
}
```
Rules: the `get_effective` docstring must explain why this key diverges from the pattern; Phase 0 plan 00-03 ships a regression test (`test_env_var_is_ignored_by_get_effective`) that asserts the env var has no effect, so any future re-introduction of the env_map entry breaks CI.

**What NOT to add yet:** Do not add validation (literal enum of `balanced | quality | budget`). PROJECT.md defers model-profile-to-model-name mapping to Phase 3/7. Phase 0 only establishes the resolution path — any string is accepted. This mirrors how `workspace: str = "auto"` accepts any string today without a Literal type.

**Backward-compat guarantee:** Because pydantic v2 fields with defaults are optional at deserialization, existing `~/.clawteam/config.json` files missing the `default_model_profile` key will load cleanly with the default `"balanced"`. The serialization roundtrip test at `test_config.py:38-44` should be extended to cover this.

---

### `tests/test_template_regression_matrix.py` (new — test, request-response)

**Primary analogs:** `tests/test_spawn_cli.py::test_launch_cli_applies_profile_to_template_agents` (lines 309–341, for the `RecordingBackend` + CliRunner + `launch` command pattern) + `tests/test_paths.py:13-26` (for the parametrize decorator style).

**Imports + fixture pattern** (copy from `test_spawn_cli.py:1-29`):
```python
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app


class RecordingBackend:
    def __init__(self):
        self.calls = []

    def spawn(self, **kwargs):
        self.calls.append(kwargs)
        return f"Agent '{kwargs['agent_name']}' spawned"

    def list_running(self):
        return []
```
Rules: top-of-file `from __future__ import annotations`; module-level `RecordingBackend` class (exact copy from `test_spawn_cli.py:20-29`, not imported — the existing one is intentionally module-local); no shared fixtures directory exists (TESTING.md §Fixtures & Factories) so duplicate the class.

**Parametrize-across-templates pattern** (combine `test_paths.py:13` decorator shape with `test_spawn_cli.py:309` body):
```python
TEMPLATE_NAMES = [
    "software-dev",
    "hedge-fund",
    "code-review",
    "harness-default",
    "research-paper",
    "strategy-room",
]


@pytest.mark.parametrize("template", TEMPLATE_NAMES)
def test_launch_template_spawns_all_agents_without_error(template, monkeypatch, tmp_path):
    """Every packaged template must launch cleanly via `clawteam launch <template>`."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["launch", template, "--team", f"t-{template}", "--goal", "regression smoke"],
        env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
    )

    assert result.exit_code == 0, f"launch {template} failed: {result.output}"
    assert backend.calls, f"no agents spawned for {template}"
```
Rules:
- `autouse=True` `isolated_data_dir` fixture from `conftest.py:10-19` is already active — redundant `monkeypatch.setenv("CLAWTEAM_DATA_DIR", ...)` is still required because of the established `test_spawn_cli.py` idiom (see lines 53–54 of that file); follow the existing idiom, don't optimize it away.
- `monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)` is the exact mock pattern used by all template/launch tests (`test_spawn_cli.py:39, 57, 147, 187, 225, 249, 328, 347, 440, 464, 493, 515`).
- `runner.invoke(app, [...], env={...})` — always pass `env=` explicitly even though the fixture sets os env (TESTING.md §CLI Testing).
- Assertion style: plain `assert` with optional f-string reason (TESTING.md §Test Framework §Assertion style).

**What to assert per template** (pick a minimum viable matrix — don't overspecify):
1. `result.exit_code == 0` — template parses and CLI exits cleanly.
2. `backend.calls` is non-empty — at least one agent was spawned.
3. `len(backend.calls) == 1 + len(template.agents)` — all expected agents spawn (leader + workers).
4. Every call's `command` attribute is a non-empty list.

Do NOT assert on rendered prompt text — that would couple regression-matrix to prompt copy changes and defeat the purpose. The `test_templates.py` module already covers task-owner/task-text semantic correctness.

**Ruff considerations:** The `TEMPLATE_NAMES` list-literal with trailing comma is idiomatic (`test_paths.py:16-24` uses the same shape). Imports must follow the three-group order (`__future__`, stdlib, first-party) per `pyproject.toml` `[tool.ruff.lint] select = ["I"]`.

---

### `tests/test_env_scrub.py` (new — test, transform)

**Primary analog:** `tests/test_identity.py::TestEnvHelpers` (lines 6–35, pure-function unit tests for env helpers) + `tests/test_paths.py::TestValidateIdentifier` (lines 10–62, parametrize for positive/negative cases).

**Module shape** (copy from `test_identity.py:1-5`):
```python
"""Tests for clawteam.util.secrets — env deny-filter scrubber."""

import pytest

from clawteam.util.secrets import scrub_env    # or: clawteam.secrets
```
Rules: module docstring describes target module (mirrors `test_identity.py:1`, `test_fileutil.py:1`); no `from __future__ import annotations` required in test files (it's optional per observed test files — `test_fileutil.py:3` has it, `test_identity.py` does not; follow whichever neighbor the planner picks).

**Class-grouped style — prefer it here** (mirrors `test_identity.py::TestEnvHelpers`):
```python
class TestScrubEnv:
    """scrub_env redacts values whose key matches the secret deny-pattern."""

    @pytest.mark.parametrize(
        "key",
        [
            "API_KEY",
            "OPENAI_API_KEY",
            "SECRET_TOKEN",
            "MY_PASSWORD",
            "BEARER_TOKEN",
            "CREDENTIAL_FILE",
            "LOWER_case_secret",        # case-insensitive
        ],
    )
    def test_matching_keys_are_redacted(self, key):
        result = scrub_env({key: "sensitive-value", "SAFE": "ok"})
        assert result[key] == "[REDACTED]"
        assert result["SAFE"] == "ok"

    def test_input_dict_is_not_mutated(self):
        env = {"API_KEY": "abc"}
        scrub_env(env)
        assert env == {"API_KEY": "abc"}   # no in-place mutation

    def test_returns_dict_not_mapping(self):
        # Callers rely on mutability of the return value.
        result = scrub_env({})
        assert isinstance(result, dict)

    def test_empty_env(self):
        assert scrub_env({}) == {}

    @pytest.mark.parametrize(
        "key",
        ["PATH", "HOME", "USER", "CLAWTEAM_AGENT_NAME", "LANG"],
    )
    def test_non_matching_keys_are_untouched(self, key):
        result = scrub_env({key: "value"})
        assert result[key] == "value"
```
Rules:
- `TestScrubEnv` class wrapping related cases (STYLE A from TESTING.md §Test Structure — matches `test_identity.py::TestEnvHelpers`, `test_paths.py::TestValidateIdentifier`).
- `@pytest.mark.parametrize("key", [...])` with multi-line list and trailing comma (copy shape from `test_paths.py:13-25`).
- Plain `assert`, no testcase base class.
- No mocking required — this is a pure function.

**Integration test piggyback:** Add ONE end-to-end test in the same file (or append to `test_event_bus.py::TestHookManager`) verifying a `SECRET_FOO` parent-env value does NOT leak through to a shell hook. Copy shape from `test_event_bus.py:104-118`:
```python
def test_shell_hook_env_snapshot_redacts_parent_secrets(tmp_path, monkeypatch):
    from clawteam.events.bus import EventBus
    from clawteam.events.hooks import HookDef, HookManager
    from clawteam.events.types import WorkerExit

    monkeypatch.setenv("MY_API_KEY", "super-secret")
    marker = tmp_path / "marker.txt"
    bus = EventBus()
    mgr = HookManager(bus)
    mgr.register_hook(
        HookDef(
            event="WorkerExit",
            action="shell",
            command=f'echo "${{MY_API_KEY}}" > {marker}',
        )
    )
    bus.emit(WorkerExit(team_name="t"))
    assert "super-secret" not in marker.read_text()
```

---

### `tests/test_doctor.py` (new — test, CLI request-response)

**Primary analogs:** `tests/test_cli_commands.py::test_lifecycle_check_zombies_reports_clean_state` (437–449, for the CliRunner + monkeypatch-to-fake-external-probe shape) + `test_cli_commands.py::test_config_cli_supports_all_keys_and_bool_values` (13–34, for the basic CliRunner env= shape).

**Imports + fixture pattern** (copy from `test_cli_commands.py:1-10`):
```python
from __future__ import annotations

from typer.testing import CliRunner

from clawteam.cli.commands import app
```

**Flat test-function style** — for CLI tests the codebase prefers flat `test_*` functions (Style B, see `test_cli_commands.py` entirely uses flat functions, not classes). Follow it:

```python
def test_doctor_reports_found_and_missing_tools(monkeypatch, tmp_path):
    """doctor exits 0 and lists each probed tool with OK/missing status."""
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }
    # shutil.which: claim codex is present, chromium is not
    real_which = __import__("shutil").which

    def fake_which(name: str, path: str | None = None):
        if name == "codex":
            return "/usr/local/bin/codex"
        return None

    monkeypatch.setattr("clawteam.cli.commands.shutil.which", fake_which)

    runner = CliRunner()
    result = runner.invoke(app, ["doctor"], env=env)

    assert result.exit_code == 0
    assert "codex" in result.output
    assert "chromium" in result.output
    assert "missing" in result.output   # at least one tool reports missing
```

**JSON-mode test** — mirror `test_cli_commands.py` JSON output checks:
```python
def test_doctor_json_mode_emits_parseable_output(monkeypatch, tmp_path):
    import json

    env = {"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")}
    monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda name, path=None: None)

    runner = CliRunner()
    result = runner.invoke(app, ["--json", "doctor"], env=env)

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)
    assert all("install_hint" in info for info in data.values())
```

**Per-OS hint test** — guarded by `sys.platform` monkeypatch, matches the conditional-platform idiom already in `test_spawn_backends.py`:
```python
def test_doctor_emits_brew_hint_on_darwin(monkeypatch, tmp_path):
    monkeypatch.setattr("clawteam.cli.commands.sys.platform", "darwin")
    monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda name, path=None: None)
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"], env={"HOME": str(tmp_path)})
    assert "brew install" in result.output
```

**Rules:**
- Flat `def test_*` functions, no Test class (CLI tests in this codebase consistently use Style B).
- `monkeypatch.setattr("clawteam.cli.commands.shutil.which", ...)` — patch the lookup at the point of use, not the source module (matches the `"clawteam.spawn.get_backend"` patching style in `test_spawn_cli.py:39`).
- Always pass `env=` to `runner.invoke` (TESTING.md §CLI Testing).
- Use `result.exit_code` + substring-match `result.output` (TESTING.md §Common Patterns).

---

### `docs/rfcs/001-phase-registry.md` (new — documentation)

**Analog:** `docs/transport-architecture.md` (tone, mixed EN/CN header style is acceptable — the codebase has multilingual docs). Also informed by `clawteam/templates/*.toml` structure, which uses a similar section-divider style.

**Structure to follow:**
```markdown
# RFC 001 — Phase Registry

**Status:** Draft
**Authors:** <names>
**Date:** 2026-04-15

## 1. Summary
<1-paragraph executive summary>

## 2. Motivation
<why this matters>

## 3. Proposed Design
<core design — include box diagrams using the ASCII-art style from docs/transport-architecture.md>

## 4. Alternatives Considered

## 5. Backward Compatibility

## 6. Open Questions
```
Rules: numbered H2 sections; bold-label metadata block at top (mirrors `transport-architecture.md:1-3` convention of header lines); ASCII box diagrams with `┌─┐└─┘│` when showing architecture (copy directly from `docs/transport-architecture.md`).

**No conventions exist** for `docs/rfcs/` specifically — this is new ground. Recommend the planner seed RFC-0001 with the structure above so future RFCs have a precedent.

---

### `docs/rfcs/README.md` (new — documentation index, **no analog**)

**No existing analog in the codebase.** Other READMEs (repo-root `README.md`, `README_CN.md`, `README_KR.md`) are high-level project documentation, not subdirectory indexes. The planner is breaking new ground here.

**Recommended minimal structure:**
```markdown
# RFCs

Design proposals for ClawTeam architecture changes. See RFC-0001 for the process template.

| # | Title | Status |
|---|-------|--------|
| [001](001-phase-registry.md) | Phase Registry | Draft |
```

**Rules:** Keep it short; table format for the RFC index is conventional outside this codebase (borrowed from Rust RFC repo, Python PEPs, etc.); no special project conventions apply.

---

## Shared Patterns

### Module Docstring + `from __future__ import annotations`
**Source:** CONVENTIONS.md §Module Header, every `clawteam/*.py` file (see `clawteam/paths.py:1-4`, `clawteam/fileutil.py:1-13`, `clawteam/config.py:1-3`).
**Apply to:** Every new `.py` file in this phase (secrets.py, test_env_scrub.py, test_doctor.py, test_template_regression_matrix.py).
```python
"""<one-line purpose>."""

from __future__ import annotations
```

### Import Organization (ruff `I`)
**Source:** `pyproject.toml:66-68` `select = ["E", "F", "I", "N", "W"]`; recent commit `bc69bc0 Fix lint import order in spawn adapters` establishes the canonical order.
**Apply to:** Every new `.py` file.
```
from __future__ import annotations    # always first, own block

<stdlib imports>                       # then a blank line
<blank>
<first-party clawteam.* imports>       # then a blank line
<blank>
<test-only typer.testing etc.>         # only in tests
```
No relative imports anywhere. No path aliases. Fully qualified `clawteam.<subpackage>.<module>`.

### Error Handling Layer Rule
**Source:** CONVENTIONS.md §Error Handling.
**Apply to:** `clawteam/util/secrets.py` (pure library — raise `ValueError`/`TypeError` only) vs. `clawteam/cli/commands.py::doctor` (CLI layer — may `raise typer.Exit(1)` for user-facing errors, but doctor specifically should return exit 0 since it's informational).
Library layer **never** calls `typer.Exit` or `sys.exit`. Only `commands.py` functions may.

### Dual-format CLI Output
**Source:** `clawteam/cli/commands.py:77-84` (`_output(data, human_fn)` helper), used by every non-trivial command in the module.
**Apply to:** `doctor` command — MUST define a local `_human(d)` closure and call `_output(checks, _human)` so `--json` mode works automatically via the existing `_json_output` global.

### Rich Console + Rich Table Rendering
**Source:** `clawteam/cli/commands.py:16-17, 27` — single module-level `Console()` instance at top of file.
**Apply to:** `doctor` command output. Use `console.print(...)` (not `print(...)`), use rich markup tags (`[green]`, `[yellow]`, `[red]`, `[dim]`, `[bold]`, `[cyan]`) for inline color.

### `isolated_data_dir` Autouse Fixture
**Source:** `tests/conftest.py:10-19` — `autouse=True` so every test automatically gets a clean `~/.clawteam`.
**Apply to:** All three new test files. Do not override; do not disable. Redundant `monkeypatch.setenv("CLAWTEAM_DATA_DIR", ...)` calls inside individual tests are the established idiom (see `test_spawn_cli.py:53-54`) — preserve them for consistency, don't refactor.

### Platform Branch Convention
**Source:** `clawteam/fileutil.py:22-25`, `clawteam/store/file.py`, `clawteam/transport/file.py`, `clawteam/team/snapshot.py`.
**Apply to:** `doctor` install-hint logic — use `sys.platform == "win32" | "darwin"` with an `else` branch for Linux. Do NOT use `platform.system()`.

### Pydantic v2 Additive Field Rule
**Source:** CONVENTIONS.md §Data Modeling + `clawteam/config.py:50-69`.
**Apply to:** `default_model_profile` field add. Defaults must be immediate (`= "balanced"`), not `Field(default_factory=...)` for scalars. Persisted JSON is loaded via `model_validate`, which already tolerates missing optional fields — no migration needed.

---

## Ruff Rules to Respect

From `pyproject.toml:62-68`:
- **Line length:** 100 (`E501` ignored, but keep reasonable)
- **target-version:** `py310` — use PEP 604 unions (`str | None`) and built-in generics (`list[str]`, `dict[str, str]`) freely. This is safe because every module has `from __future__ import annotations`.
- **Rules enabled:** `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `N` (pep8-naming), `W` (warnings).
- **`N` implications:**
  - Classes: `PascalCase` → `TestScrubEnv`, `RecordingBackend` (not `test_scrub_env`, `recording_backend`).
  - Functions: `snake_case` → `scrub_env`, `_env_snapshot`, `doctor` (not `scrubEnv`).
  - Module-level constants: `UPPER_SNAKE` → `_SECRET_KEY_RE`, `_REDACTED`, `_DOCTOR_TOOLS`, `TEMPLATE_NAMES` (private ones underscore-prefixed).
  - Test functions: `snake_case` → `test_matching_keys_are_redacted`.
- **`I` implications:** Canonical import grouping as described above.

---

## Test Fixture Reuse Summary

| New Test File | Reuse From | Pattern |
|---------------|------------|---------|
| `test_env_scrub.py` | `tests/conftest.py::isolated_data_dir` (autouse — free) | No manual fixture wiring needed for env scrubber unit tests. |
| `test_template_regression_matrix.py` | `tests/conftest.py::isolated_data_dir` (autouse), `RecordingBackend` class (copy from `test_spawn_cli.py:20-29`) | Paste `RecordingBackend` as module-level class; use `monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)` pattern. |
| `test_doctor.py` | `tests/conftest.py::isolated_data_dir`, `CliRunner` pattern from `test_cli_commands.py:1-10` | `monkeypatch.setattr("clawteam.cli.commands.shutil.which", ...)` to fake tool availability; `monkeypatch.setattr("clawteam.cli.commands.sys.platform", "darwin")` for OS-specific hint tests. |

**New fixtures to create:** None. The autouse `isolated_data_dir` + module-local `RecordingBackend` copy is sufficient. Do not add anything to `conftest.py` (TESTING.md §Fixtures & Factories: "No shared fixtures directory — each test module defines its own factories close to where they are used").

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `docs/rfcs/README.md` | docs index | No other subdirectory-level README exists in `docs/`. Planner is breaking new ground; recommend minimal table-style index (template provided above). |

The `clawteam/util/` package itself is also technically new ground — the codebase convention is flat top-level utility modules (`paths.py`, `fileutil.py`, `timefmt.py`). Planner should explicitly decide: flat `clawteam/secrets.py` (matches convention) vs. `clawteam/util/secrets.py` (introduces a new subpackage). **Strong recommendation: flat `clawteam/secrets.py`** — it matches every other pure-helper module in the repo and avoids inventing a one-file subpackage that invites further scope creep.

---

## Metadata

**Analog search scope:** `clawteam/` (all subpackages), `tests/` (flat), `docs/`, `pyproject.toml`.
**Files scanned:** ~20 source files + 8 test files + 2 doc files.
**Key authoritative references:**
- `clawteam/paths.py` (secrets.py structural analog)
- `clawteam/config.py:50-69` (pydantic field analog)
- `clawteam/cli/commands.py:1080-1145` (doctor/config_health analog)
- `clawteam/events/hooks.py:77-103` (env snapshot scrub site)
- `tests/test_spawn_cli.py:20-29, 309-341` (RecordingBackend + template matrix)
- `tests/test_identity.py:6-35` (unit-test-for-pure-helper shape)
- `tests/test_cli_commands.py:437-449` (CLI-test-with-external-probe shape)
- `pyproject.toml:62-68` (ruff config)
- `tests/conftest.py:10-19` (isolated_data_dir autouse)

**Pattern extraction date:** 2026-04-15
