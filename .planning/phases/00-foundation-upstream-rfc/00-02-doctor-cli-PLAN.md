---
phase: 00-foundation-upstream-rfc
plan: 02
type: execute
wave: 2
depends_on: [00-01]
files_modified:
  - clawteam/cli/commands.py
  - tests/test_doctor.py
autonomous: true
requirements:
  - UX-08
tags: [cli, doctor, tooling, ux]

must_haves:
  truths:
    - "Running `clawteam doctor` on a machine missing Chromium (Playwright), codex CLI, ngrok, and the watchdog Python package prints per-OS install hints for each missing tool and exits 0."
    - "Running `clawteam doctor` on a machine with every optional tool present prints an OK report and exits 0."
    - "Running `clawteam --json doctor` emits a parseable JSON object keyed by tool name with `found`, `path`, `install_hint` fields per tool plus a top-level `os` key."
    - "Install-hint selection follows the sys.platform triple-branch convention: sys.platform == 'darwin' → macOS hint; sys.platform == 'win32' → Windows hint; else → Linux hint."
  artifacts:
    - path: "clawteam/cli/commands.py"
      provides: "Top-level `@app.command('doctor')` subcommand with section-banner marker, _DOCTOR_TOOLS module-level tuple, _doctor_install_hint helper, rich + --json dual-format output"
      contains: "@app.command(\"doctor\")"
    - path: "tests/test_doctor.py"
      provides: "Style B flat test_* functions covering: found+missing matrix, --json mode, per-OS (darwin/win32/linux) install hint dispatch"
      contains: "def test_doctor"
      min_lines: 80
  key_links:
    - from: "clawteam/cli/commands.py::doctor"
      to: "shutil.which + importlib.util.find_spec"
      via: "probe each entry in _DOCTOR_TOOLS"
      pattern: "shutil\\.which|find_spec"
    - from: "clawteam/cli/commands.py::doctor"
      to: "clawteam/cli/commands.py::_output"
      via: "dual-format (rich + --json) render"
      pattern: "_output\\(checks, _human\\)"
---

<objective>
Implement `clawteam doctor` (UX-08): a top-level CLI subcommand that detects the four optional tools declared in the Phase 0 success criteria — Chromium/Playwright, codex CLI, ngrok, watchdog — and prints per-OS install hints for anything missing. The command mirrors `config_health` (commands.py:1080-1145) structure exactly: `checks: dict[...]` → inner `_human(d)` closure → `_output(checks, _human)` dual-format dispatch.

Purpose: Closes UX-08. First-run UX for users discovering ClawTeam; debugging aid for "why doesn't `/browse` work?"; CI smoke test primitive on fresh installs. Scopes install hints per detected package manager so users can copy-paste the correct command.

Output:
- Modified `clawteam/cli/commands.py` — new `@app.command("doctor")` top-level command (NOT a subcommand of `config` or `profile`; `profile doctor` already exists for claude-state repair at line 1035, that's a different surface) with its own section banner, `_DOCTOR_TOOLS` module-level tuple, `_doctor_install_hint` helper.
- New test file `tests/test_doctor.py` using Style B flat test_* functions (CLI testing consistently uses flat style in this codebase — see `test_cli_commands.py`).
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
@.planning/phases/00-foundation-upstream-rfc/00-01-PLAN.md
@.planning/codebase/CONVENTIONS.md
@.planning/codebase/TESTING.md
@clawteam/cli/commands.py
@clawteam/fileutil.py
@tests/test_cli_commands.py

<interfaces>
<!-- Existing CLI patterns the doctor subcommand must mirror exactly. -->

From clawteam/cli/commands.py (module-level imports and helpers already present — DO NOT re-import):
```python
import json
import os
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from clawteam import __version__

app = typer.Typer(...)
console = Console()

_json_output: bool = False
_data_dir: str | None = None

def _output(data: dict | list, human_fn=None):
    """Output data as JSON or human-readable."""
    if _json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif human_fn:
        human_fn(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
```

From clawteam/cli/commands.py:1080-1145 (primary analog — `config_health`):
```python
@config_app.command("health")
def config_health():
    """Health check for the data directory (shared directory diagnostics)."""
    import os
    import time as _time

    from clawteam.config import get_effective
    from clawteam.team.manager import TeamManager
    from clawteam.team.models import get_data_dir

    checks = {}
    # ... populate checks dict ...

    def _human(d):
        console.print(f"\nData Directory: [cyan]{d['data_dir']}[/cyan]  [dim]({d['data_dir_source']})[/dim]")
        console.print(f"  Exists:     {'[green]yes[/green]' if d['exists'] else '[red]no[/red]'}")
        # ... etc ...

    _output(checks, _human)
```

From clawteam/fileutil.py:22-25 (sys.platform triple-branch convention — this is the codebase standard, NOT platform.system()):
```python
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl
```

From tests/test_cli_commands.py (Style B flat test shape for CLI tests):
```python
from __future__ import annotations

from typer.testing import CliRunner
from clawteam.cli.commands import app

def test_config_cli_supports_all_keys_and_bool_values(tmp_path):
    runner = CliRunner()
    env = {"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")}
    result = runner.invoke(app, ["config", "set", "skip_permissions", "false"], env=env)
    assert result.exit_code == 0
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add doctor subcommand + _DOCTOR_TOOLS + _doctor_install_hint to commands.py</name>
  <files>clawteam/cli/commands.py</files>
  <behavior>
    - `@app.command("doctor")` registers a top-level `clawteam doctor` command (NOT a subcommand under config_app or profile_app).
    - Probes each entry in _DOCTOR_TOOLS: CLI tools via `shutil.which`; Python packages via `importlib.util.find_spec`.
    - Builds a `checks: dict[str, dict[str, object]]` keyed by tool name, with per-tool `{"found": bool, "path": str, "kind": "cli" | "python-pkg", "install_hint": str}`.
    - Emits rich-formatted human output via inner `_human(d)` closure OR JSON via `--json` flag — dispatched by `_output(checks, _human)`.
    - Prints "OK" in green for found tools, "missing" in yellow for absent, with install hint as dim text below each missing tool.
    - Exits 0 regardless of missing optional tools (per ROADMAP Phase 0 success criterion 3). Never raises typer.Exit(1) — doctor is informational.
    - sys.platform-based install hint dispatch: "darwin" → brew-style hints; "win32" → winget/choco hints; else (Linux) → apt-style hints.
  </behavior>
  <action>
    Modify `clawteam/cli/commands.py` to add a top-level `doctor` command. Decisions per PATTERNS.md:

    1. **Placement:** Add directly to `commands.py` (NOT a new `clawteam/cli/doctor.py` module). STRUCTURE.md §Where to Add New Code says "New CLI subcommand: Add a Typer command to `clawteam/cli/commands.py`". There's already one 4573-line convention to keep — follow it.

    2. **Command name collision check:** `profile doctor` already exists at line 1035 (a subcommand under `profile_app`, distinct namespace). Top-level `@app.command("doctor")` is unique — no collision because Typer routes by command path.

    3. **Section placement:** Insert AFTER the existing `config_health` block (ending at line 1145) and BEFORE the next `# ============` Team Commands banner (starting at line 1148). This keeps it adjacent to the other diagnostic-family commands.

    4. **NO `scrub_env` call needed** — doctor prints tool paths (`/usr/local/bin/codex`) and install hints, never prints env values. The threat-model-guidance entry ("doctor could accidentally leak env values") is a design constraint: the implementation MUST NOT `print(os.environ)` anywhere, MUST NOT include env values in checks dict. Verified in Task 2 tests.

    ### Step 1 — Add module-level `_DOCTOR_TOOLS` tuple

    Place at module level, AFTER existing `_json_output`/`_data_dir` private globals (around line 35-36, immediately before or after the `_version_callback` definition at line 38). Use the underscore-prefix UPPER_SNAKE convention for module-level private constants:

    ```python
    # Tools probed by `clawteam doctor`. CLI tools use shutil.which; Python
    # packages use importlib.util.find_spec. Install hints are dispatched
    # per-OS inside _doctor_install_hint().
    _DOCTOR_TOOLS: tuple[tuple[str, str, str], ...] = (
        # (display_name, kind, probe_target)
        ("chromium (Playwright)", "python-pkg", "playwright"),
        ("codex", "cli", "codex"),
        ("ngrok", "cli", "ngrok"),
        ("watchdog", "python-pkg", "watchdog"),
    )
    ```

    Tuple-of-tuples (immutable, module-level) matches the existing `_json_output: bool = False` / `_data_dir: str | None = None` declaration style. Kind values are literal strings "cli" or "python-pkg" — no enum needed for 2 cases.

    ### Step 2 — Add `_doctor_install_hint` helper

    Place at module level, immediately after `_DOCTOR_TOOLS`:

    ```python
    def _doctor_install_hint(tool: str, platform: str) -> str:
        """Return the per-OS install command for *tool*, dispatched by sys.platform.

        Follows the triple-branch convention (``sys.platform == "darwin"`` → macOS,
        ``"win32"`` → Windows, else → Linux). No package-manager sniffing — we
        surface the most common command per platform and rely on users to adapt
        to their distro if needed.
        """
        hints: dict[str, dict[str, str]] = {
            "chromium (Playwright)": {
                "darwin": "pip install 'clawteam[browser]' && playwright install chromium",
                "win32":  "pip install 'clawteam[browser]' && playwright install chromium",
                "linux":  "pip install 'clawteam[browser]' && playwright install chromium",
            },
            "codex": {
                "darwin": "brew install codex  # or: npm install -g @openai/codex",
                "win32":  "winget install OpenAI.Codex  # or: npm install -g @openai/codex",
                "linux":  "npm install -g @openai/codex",
            },
            "ngrok": {
                "darwin": "brew install ngrok",
                "win32":  "winget install Ngrok.Ngrok  # or: choco install ngrok",
                "linux":  "curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo 'deb https://ngrok-agent.s3.amazonaws.com buster main' | sudo tee /etc/apt/sources.list.d/ngrok.list && sudo apt update && sudo apt install ngrok",
            },
            "watchdog": {
                "darwin": "pip install watchdog",
                "win32":  "pip install watchdog",
                "linux":  "pip install watchdog",
            },
        }
        per_tool = hints.get(tool, {})
        if platform == "darwin":
            return per_tool.get("darwin", "")
        if platform == "win32":
            return per_tool.get("win32", "")
        return per_tool.get("linux", "")
    ```

    Rules:
    - Branch on `sys.platform == "win32" | "darwin"` with else fallback (matches `clawteam/fileutil.py:22-25` convention). Do NOT use `platform.system()`.
    - Nested `hints: dict[str, dict[str, str]]` literal with literal strings per OS per tool (matches RESEARCH.md "hand-coded per-OS hint strings" — 4 tools × 3 OSes = 12 strings, flat strings beat introducing a package-manager abstraction library).
    - Hint strings use the exact commands documented in ROADMAP.md success criterion 3 ("pip install 'clawteam[browser]' && playwright install chromium", "npm install -g @openai/codex", etc.).
    - Use `platform` parameter (not `sys.platform` directly) so tests can pass arbitrary values without monkeypatching `sys`.

    ### Step 3 — Add doctor subcommand

    Insert after line 1145 (end of `config_health`), before line 1148 (Team Commands banner). Use the mandatory 76-char banner (mirrors every section in commands.py, e.g. lines 170-172, 1148-1150):

    ```python
    # ============================================================================
    # Doctor Command
    # ============================================================================


    @app.command("doctor")
    def doctor():
        """Detect optional external tools and print per-OS install hints."""
        import shutil
        import sys
        from importlib.util import find_spec

        checks: dict[str, dict[str, object]] = {"os": sys.platform}
        for display_name, kind, target in _DOCTOR_TOOLS:
            if kind == "cli":
                found_path = shutil.which(target)
                checks[display_name] = {
                    "found": bool(found_path),
                    "path": found_path or "",
                    "kind": kind,
                    "install_hint": _doctor_install_hint(display_name, sys.platform) if not found_path else "",
                }
            else:  # python-pkg
                try:
                    spec = find_spec(target)
                except Exception:
                    spec = None
                checks[display_name] = {
                    "found": spec is not None,
                    "path": (spec.origin or "") if spec is not None else "",
                    "kind": kind,
                    "install_hint": _doctor_install_hint(display_name, sys.platform) if spec is None else "",
                }

        def _human(d: dict[str, object]) -> None:
            console.print(f"\n[bold]Optional tool check[/bold]  [dim](os: {d['os']})[/dim]\n")
            for tool, info in d.items():
                if tool == "os":
                    continue
                assert isinstance(info, dict)
                if info["found"]:
                    console.print(f"  [green]OK[/green]      {tool}  [dim]{info['path']}[/dim]")
                else:
                    console.print(f"  [yellow]missing[/yellow] {tool}")
                    hint = info["install_hint"]
                    if hint:
                        console.print(f"          [dim]install: {hint}[/dim]")
            console.print()

        _output(checks, _human)
    ```

    Critical rules (per PATTERNS.md §clawteam/cli/commands.py):
    - Lazy imports inside the function body (matches `config_health:1083-1088` lazy-imports `os`, `time as _time`).
    - `shutil.which` for CLI probing — matches `clawteam/board/gource.py:301`, `spawn/wsh_backend.py:195`, `spawn/tmux_backend.py:60` established pattern.
    - `importlib.util.find_spec` for Python package probing — safer than `import X` because it doesn't execute module init.
    - `try/except Exception` around `find_spec` because some broken packages raise during metadata lookup; treat as "missing".
    - Inner `_human(d)` closure that uses `console.print` with rich markup tags `[green]`, `[yellow]`, `[dim]`, `[bold]` (matches `config_health:1134-1145` and the rest of commands.py).
    - Final `_output(checks, _human)` dispatches `--json` vs human automatically via the module-level `_json_output` global.
    - The command returns None (not typer.Exit) — doctor is INFORMATIONAL, exit 0 always per ROADMAP success criterion 3.
    - The top-level "os" key inside checks is part of the JSON schema (tests assert it exists); the `_human` renderer skips it in the table via `if tool == "os": continue`.

    Do NOT:
    - Do NOT run `subprocess.run([target, "--version"], timeout=5)` to extract version strings. Per RESEARCH.md Pitfall #3, some CLIs (pi, kimi) hang on unknown `--version`. PATH presence (via `shutil.which`) is the primary signal; we record `path` for diagnostic purposes but skip version extraction entirely in v1. If a later phase wants version info, it can add that with explicit timeout safety.
    - Do NOT print os.environ values. The command never touches env variable values — only `sys.platform` (constant string) and tool paths (from shutil.which). This is the "check before print" discipline from the threat-model guidance.
    - Do NOT add a `--fix` flag. PROJECT.md out-of-scope table explicitly excludes "Auto-installing external tools".
    - Do NOT raise `typer.Exit(1)` for missing tools. Doctor is informational; exit 0 always.
    - Do NOT use `platform.system()` (codebase uses `sys.platform` everywhere; see `fileutil.py:22-25`, `store/file.py`, `transport/file.py`).

    After edits, run `ruff check clawteam/cli/commands.py` to verify import ordering (the lazy imports inside `doctor()` do not affect module-level `I` rules).
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && ruff check clawteam/cli/commands.py && python -c "from clawteam.cli.commands import app; from typer.testing import CliRunner; r = CliRunner().invoke(app, ['doctor']); assert r.exit_code == 0, r.output; print('doctor smoke OK')"</automated>
  </verify>
  <done>
    commands.py has `@app.command("doctor")` registered, `_DOCTOR_TOOLS` tuple and `_doctor_install_hint` helper at module level, passes ruff, `clawteam doctor` invocation via CliRunner exits 0 and produces non-empty output.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create tests/test_doctor.py with CLI + OS-branching coverage</name>
  <files>tests/test_doctor.py</files>
  <behavior>
    - test_doctor_reports_found_and_missing_tools: mocks shutil.which to return /path/to/codex for "codex" and None for others; mocks find_spec to return None; asserts exit 0, "codex" in output, "missing" in output, "install" in output.
    - test_doctor_exits_zero_when_all_optional_missing: mocks everything missing; asserts exit 0 (not 1).
    - test_doctor_json_mode_emits_parseable_output: invokes with ["--json", "doctor"]; json.loads the output; asserts presence of "os" key and dict entries per tool with "install_hint" fields.
    - test_doctor_emits_brew_hint_on_darwin: patches sys.platform to "darwin"; asserts "brew install" substring appears in output for ngrok or codex.
    - test_doctor_emits_winget_hint_on_win32: patches sys.platform to "win32"; asserts "winget" substring appears for ngrok or codex.
    - test_doctor_linux_hint_is_default: patches sys.platform to "linux"; asserts neither "brew install" nor "winget" appears (linux fallback path used).
    - test_doctor_never_leaks_env_values: sets MY_API_KEY=super-secret in env; asserts "super-secret" does NOT appear in output or JSON.
  </behavior>
  <action>
    Create `tests/test_doctor.py` using Style B (flat `def test_*` functions — matches `tests/test_cli_commands.py` which uses flat throughout, despite the codebase having both styles; CLI tests consistently use Style B per PATTERNS.md §tests/test_doctor.py).

    Full file content:

    ```python
    """Tests for `clawteam doctor` — optional tool detector (UX-08)."""

    from __future__ import annotations

    import json

    from typer.testing import CliRunner

    from clawteam.cli.commands import app


    def test_doctor_exits_zero_when_all_optional_missing(monkeypatch, tmp_path):
        """Missing optional tools must NOT cause non-zero exit (Phase 0 success criterion 3)."""
        monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda _name, path=None: None, raising=False)
        monkeypatch.setattr("clawteam.cli.commands.find_spec", lambda _name: None, raising=False)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["doctor"],
            env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
        )

        assert result.exit_code == 0, f"doctor must exit 0 on missing optionals: {result.output}"
        assert "missing" in result.output.lower()
        assert "install" in result.output.lower()


    def test_doctor_reports_found_and_missing_tools(monkeypatch, tmp_path):
        """Found tools render as OK; missing tools render with install hints."""
        def fake_which(name: str, path=None):
            return "/usr/local/bin/codex" if name == "codex" else None

        monkeypatch.setattr("clawteam.cli.commands.shutil.which", fake_which, raising=False)
        monkeypatch.setattr("clawteam.cli.commands.find_spec", lambda _name: None, raising=False)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["doctor"],
            env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
        )

        assert result.exit_code == 0
        assert "codex" in result.output
        assert "/usr/local/bin/codex" in result.output
        assert "ngrok" in result.output
        assert "chromium" in result.output.lower()
        assert "watchdog" in result.output


    def test_doctor_json_mode_emits_parseable_output(monkeypatch, tmp_path):
        """--json produces a JSON object with per-tool entries + top-level 'os' key."""
        monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda _name, path=None: None, raising=False)
        monkeypatch.setattr("clawteam.cli.commands.find_spec", lambda _name: None, raising=False)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["--json", "doctor"],
            env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert "os" in data
        # Each tool (excluding the "os" key) must have found/path/kind/install_hint
        tool_keys = [k for k in data.keys() if k != "os"]
        assert len(tool_keys) >= 4  # chromium, codex, ngrok, watchdog
        for tool in tool_keys:
            info = data[tool]
            assert isinstance(info, dict)
            assert "found" in info
            assert "path" in info
            assert "kind" in info
            assert "install_hint" in info
            # With everything mocked missing, every install_hint must be non-empty
            assert info["install_hint"], f"{tool}: empty install_hint when missing"


    def test_doctor_emits_brew_hint_on_darwin(monkeypatch, tmp_path):
        """macOS platform → brew install hint surfaces in output."""
        monkeypatch.setattr("clawteam.cli.commands.sys.platform", "darwin", raising=False)
        monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda _name, path=None: None, raising=False)
        monkeypatch.setattr("clawteam.cli.commands.find_spec", lambda _name: None, raising=False)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["doctor"],
            env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
        )

        assert result.exit_code == 0
        assert "brew install" in result.output


    def test_doctor_emits_winget_hint_on_win32(monkeypatch, tmp_path):
        """Windows platform → winget install hint surfaces in output."""
        monkeypatch.setattr("clawteam.cli.commands.sys.platform", "win32", raising=False)
        monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda _name, path=None: None, raising=False)
        monkeypatch.setattr("clawteam.cli.commands.find_spec", lambda _name: None, raising=False)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["doctor"],
            env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
        )

        assert result.exit_code == 0
        assert "winget" in result.output.lower()


    def test_doctor_linux_hint_is_default(monkeypatch, tmp_path):
        """Linux (any non-darwin non-win32 platform) → neither brew nor winget."""
        monkeypatch.setattr("clawteam.cli.commands.sys.platform", "linux", raising=False)
        monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda _name, path=None: None, raising=False)
        monkeypatch.setattr("clawteam.cli.commands.find_spec", lambda _name: None, raising=False)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["doctor"],
            env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
        )

        assert result.exit_code == 0
        assert "brew install" not in result.output
        assert "winget" not in result.output.lower()
        # Linux codex hint includes npm install
        assert "npm install" in result.output


    def test_doctor_never_leaks_env_values(monkeypatch, tmp_path):
        """doctor must never surface env var values in output (threat T-00-06)."""
        monkeypatch.setenv("MY_API_KEY", "super-secret-doctor-value")
        monkeypatch.setenv("DB_PASSWORD", "hunter2-doctor")
        monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda _name, path=None: None, raising=False)
        monkeypatch.setattr("clawteam.cli.commands.find_spec", lambda _name: None, raising=False)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["doctor"],
            env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
        )

        assert result.exit_code == 0
        assert "super-secret-doctor-value" not in result.output
        assert "hunter2-doctor" not in result.output


    def test_doctor_json_never_leaks_env_values(monkeypatch, tmp_path):
        """--json output must also not contain env values."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-json-leak-test")
        monkeypatch.setattr("clawteam.cli.commands.shutil.which", lambda _name, path=None: None, raising=False)
        monkeypatch.setattr("clawteam.cli.commands.find_spec", lambda _name: None, raising=False)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["--json", "doctor"],
            env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
                 "OPENAI_API_KEY": "sk-json-leak-test"},
        )

        assert result.exit_code == 0
        assert "sk-json-leak-test" not in result.output
        data = json.loads(result.output)
        assert "sk-json-leak-test" not in json.dumps(data)
    ```

    Critical rules (per PATTERNS.md §tests/test_doctor.py and TESTING.md):
    - Flat `def test_*` functions (Style B; `test_cli_commands.py` throughout).
    - Module docstring (one-line; mandatory per CONVENTIONS.md).
    - `from __future__ import annotations` optional; include to match `test_cli_commands.py:1`.
    - `monkeypatch.setattr("clawteam.cli.commands.shutil.which", ...)` — patch at the point of use (same style as `"clawteam.spawn.get_backend"` in `test_spawn_cli.py:39`).
    - `raising=False` on `monkeypatch.setattr` for patching module-level symbols that may not have been imported yet (belt-and-braces for `find_spec` which is lazy-imported inside the command body).
    - `runner.invoke(app, [...], env={...})` — always pass `env=` explicitly (TESTING.md §CLI Testing).
    - `json.loads(result.output)` — standard JSON assertion idiom (matches `test_cli_commands.py` patterns).
    - `isolated_data_dir` autouse is implicit (don't add a `conftest.py` entry here).
    - Do NOT test the actual production tool detection (real shutil.which against host) — we mock everything deterministically so tests are OS-agnostic (critical for CI matrix ubuntu+macos).

    Patching notes:
    - `sys.platform` — patch `clawteam.cli.commands.sys.platform`, NOT `sys.platform` directly, because `doctor()` lazy-imports `sys` inside the function body. The monkeypatch target must match the resolved attribute path at call time. If `raising=False` is specified, monkeypatch tolerates the attribute not existing at patch time (it'll exist by call time via the lazy import).
    - `find_spec` — the production code does `from importlib.util import find_spec` (lazy import inside doctor). We patch `clawteam.cli.commands.find_spec` so the test intercepts the name after the import has happened. If `raising=False` is set, test works whether `find_spec` has been imported yet or not (pytest handles either case).
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && ruff check tests/test_doctor.py && pytest tests/test_doctor.py -v</automated>
  </verify>
  <done>
    `tests/test_doctor.py` exists, ruff-clean, all 8 test functions pass. Specifically: exit code is 0 in every case, --json produces parseable output with expected keys, per-OS branching selects correct hints (brew/winget/apt-style), env values never appear in any output.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| host PATH / site-packages → doctor output | Doctor reports file paths discovered via shutil.which (e.g., `/usr/local/bin/codex`) and Python package origin paths. Attacker-controlled PATH could plant a malicious binary that doctor reports as "OK" — but doctor itself doesn't execute the binary, only reports its existence. |
| command stdout → user terminal / log capture | Rich-rendered output is consumed by users who may redirect to log files; content is assumed PII-safe because doctor never prints env values. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-00-06 | Information Disclosure | `clawteam/cli/commands.py::doctor` output | mitigate | The command never touches env variable values. Only `sys.platform` (constant string) and `shutil.which(target)` results (filesystem paths) enter the `checks` dict. Task 2 includes two assertive regression tests (`test_doctor_never_leaks_env_values`, `test_doctor_json_never_leaks_env_values`) that seed the parent env with fake secrets and assert they do NOT appear in the rendered output or JSON. |
| T-00-07 | Spoofing | attacker-controlled PATH plants a fake `codex` binary → doctor reports "OK" | accept | Doctor only checks PRESENCE (via `shutil.which`), not the binary's identity. Users own their PATH; a PATH-planting attack is a pre-existing host compromise outside ClawTeam's trust boundary. Doctor's role is UX, not endpoint integrity verification. |
| T-00-08 | Denial of Service | subprocess version extraction hangs on interactive CLIs (pi, kimi) | mitigate | DESIGN: Task 1 explicitly does NOT call `subprocess.run([target, "--version"], ...)`. We use `shutil.which` only — PATH lookup is O(PATHSEG) and does not execute the binary. RESEARCH.md Pitfall #3 warned about this; prevention is architectural (no subprocess in doctor v1). |
| T-00-09 | Tampering | importlib.util.find_spec returns a broken spec for a shadowed package name | accept | `try/except Exception` around `find_spec` treats any exception as "missing" — consistent with doctor's informational role. False-negative (package present but find_spec raises) is acceptable: user sees install hint they can try; worst case they discover the shadowing on their own. |
| T-00-10 | Information Disclosure | install-hint strings echo a remote URL (ngrok apt-key URL) to terminal → leak via screen-share | accept | Install hints are static strings; the ngrok hint contains a public URL (`ngrok-agent.s3.amazonaws.com`), not a secret. Documented publicly. Low risk. |
</threat_model>

<verification>
Phase-level verification:

```bash
cd /home/jac/repos/ClawTeam-gstack
ruff check clawteam/cli/commands.py tests/test_doctor.py
pytest tests/test_doctor.py -v --tb=short
# Sanity: real doctor invocation on host (codex/ngrok present per RESEARCH.md environment scan; playwright/watchdog absent)
python -m clawteam doctor
python -m clawteam --json doctor | python -c "import sys, json; print(json.load(sys.stdin).get('os'))"
```

Expected:
- ruff exit 0.
- All 8 test_doctor functions PASS.
- `python -m clawteam doctor` exits 0, prints an "Optional tool check" header, rows for chromium/codex/ngrok/watchdog, "install" hints for whichever are missing.
- `clawteam --json doctor` emits parseable JSON with `os` key reflecting host platform.

BC regression check:
```bash
pytest tests/test_cli_commands.py -q
```
Expected: existing CLI tests unchanged (doctor is purely additive; no existing commands modified).
</verification>

<success_criteria>
1. `clawteam/cli/commands.py` has new `@app.command("doctor")` subcommand with its own section banner, `_DOCTOR_TOOLS` module-level tuple, and `_doctor_install_hint(tool, platform)` helper.
2. Running `clawteam doctor` prints a rich-formatted report with per-tool OK/missing status, install hints under missing tools, and exits 0.
3. Running `clawteam --json doctor` emits parseable JSON containing an `os` key plus per-tool entries with `found`, `path`, `kind`, `install_hint` fields.
4. Per-OS install-hint dispatch is correct: darwin → brew, win32 → winget, else → Linux default (npm install for codex, apt-key for ngrok).
5. `tests/test_doctor.py` exists with 8 flat test_* functions covering missing/found matrix, --json, per-OS branching, and explicit env-leak regression tests.
6. `ruff check clawteam/cli/commands.py tests/test_doctor.py` exits 0.
7. Existing `tests/test_cli_commands.py` continues to pass (no BC regression; doctor is additive).
8. Doctor output on a host with seeded fake secrets in env does NOT contain any secret values (enforced by T-00-06 mitigation tests).
</success_criteria>

<output>
After completion, create `.planning/phases/00-foundation-upstream-rfc/00-02-SUMMARY.md` following `@$HOME/.claude/get-shit-done/templates/summary.md`, documenting:
- `_DOCTOR_TOOLS` entry format and how future phases extend it (Phase 6 might add sqlite-vec; Phase 7 might add additional SRE/observability tools — flat tuple-of-tuples makes this a 1-line extension)
- Decision: no version-extraction subprocess calls in v1 (Pitfall #3 avoided by design)
- Decision: no `--fix` flag (PROJECT.md out-of-scope)
- Decision: exit 0 always (informational; matches ROADMAP success criterion 3)
- `scrub_env` was NOT wired into doctor because doctor never touches env values by design; defense-in-depth comes from T-00-06 regression tests, not from a scrub call
</output>
