---
phase: 00-foundation-upstream-rfc
plan: 06
type: execute
wave: 3
depends_on: [00-02]
files_modified:
  - clawteam/cli/commands.py
  - tests/test_doctor.py
autonomous: true
gap_closure: true
requirements:
  - UX-08
tags: [cli, doctor, rich, bugfix, ux, gap-closure]
closes_uat_gaps:
  - test: 2
    truth: "`clawteam doctor` human-readable output prints the correct Chromium install hint including the `[browser]` extra"
    severity: major

must_haves:
  truths:
    - "Running `clawteam doctor` on a machine missing Chromium prints an install hint whose literal stdout contains the substring `clawteam[browser]` (the Playwright extra name is not silently elided by Rich's markup parser)."
    - "Every other install hint that contains a bracketed token (none ship today, but the fix is general) is preserved verbatim in the human-readable renderer — no tokens inside square brackets are ever consumed as Rich markup tags."
    - "`clawteam --json doctor` continues to emit the exact install_hint string unchanged (JSON path is already correct and must stay correct)."
    - "Regression test `test_doctor_human_output_preserves_browser_extra` in tests/test_doctor.py asserts the literal substring `clawteam[browser]` appears in the human-readable stdout when chromium is missing."
  artifacts:
    - path: "clawteam/cli/commands.py"
      provides: "doctor command's _human closure renders install_hint via rich.markup.escape() so brackets inside hint values never collide with Rich's markup parser"
      contains: "rich.markup.escape"
    - path: "tests/test_doctor.py"
      provides: "Regression test asserting the human-readable doctor output preserves `clawteam[browser]` literally; optionally a second assertion that the JSON install_hint still equals the unescaped original"
      contains: "clawteam[browser]"
  key_links:
    - from: "clawteam/cli/commands.py::doctor::_human"
      to: "rich.markup.escape"
      via: "escape install_hint before embedding in [dim]...[/dim] markup span"
      pattern: "markup\\.escape\\("
    - from: "tests/test_doctor.py::test_doctor_human_output_preserves_browser_extra"
      to: "CliRunner().invoke(app, ['doctor'])"
      via: "assert 'clawteam[browser]' in result.output when chromium missing"
      pattern: "clawteam\\[browser\\]"
---

<objective>
Fix a Rich-markup bug in `clawteam/cli/commands.py:1224` where the human-readable `clawteam doctor` output silently strips the `[browser]` token from the Chromium install hint. The hint value is `pip install 'clawteam[browser]' && playwright install chromium`; because the renderer uses `console.print(f"    [dim]{info['install_hint']}[/dim]")`, Rich interprets the literal `[browser]` substring as an unknown markup tag and elides it, so users see `pip install 'clawteam' && ...` (wrong extra) instead of the correct `pip install 'clawteam[browser]' && ...`.

Purpose: Closes Gap 1 from the Phase 0 UAT (test 2, severity major) and satisfies ROADMAP Phase 0 success criterion #3 ("Running `clawteam doctor` … prints per-OS install instructions for each missing optional tool … `pip install 'clawteam[browser]' && playwright install chromium`"). The JSON renderer path is already correct (verified by UAT test 3 = pass); this fix is isolated to the human-readable closure and ships with a regression test so the bug cannot silently reappear.

Scope boundary: ONE line changed in production code (the `console.print(...)` call on line 1224) plus ONE new regression test function in `tests/test_doctor.py`. No refactor of the doctor command, no changes to `_DOCTOR_TOOLS`, no changes to `_doctor_install_hint`, no changes to the JSON path, no changes to any other command. This is a surgical bugfix.

Output:
- Modified `clawteam/cli/commands.py` — the install-hint line in doctor's `_human` closure uses `rich.markup.escape` (imported at the top of the closure via lazy `from rich.markup import escape`, matching the lazy-import convention used throughout doctor).
- Modified `tests/test_doctor.py` — one new flat `def test_doctor_human_output_preserves_browser_extra(monkeypatch)` asserting the literal substring `clawteam[browser]` appears in the human stdout when chromium is missing. Optional second assertion: JSON install_hint is still the unescaped original.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/00-foundation-upstream-rfc/00-UAT.md
@.planning/phases/00-foundation-upstream-rfc/00-02-doctor-cli-PLAN.md
@.planning/phases/00-foundation-upstream-rfc/00-02-doctor-cli-SUMMARY.md
@clawteam/cli/commands.py
@tests/test_doctor.py

<interfaces>
<!-- Existing code at the bug site and the escape API the fix uses. -->

Current buggy block in `clawteam/cli/commands.py` (lines 1213-1224 — doctor's `_human` closure):

```python
def _human(d):
    console.print(f"\nDoctor OS: [cyan]{d['os']['platform']}[/cyan]")
    for name, _, _ in _DOCTOR_TOOLS:
        info = d[name]
        if info["found"]:
            console.print(
                f"  {name}: [green]OK[/green]  [dim]{info['path'] or '(available)'}[/dim]"
            )
        else:
            console.print(f"  {name}: [yellow]missing[/yellow]")
            if info["install_hint"]:
                console.print(f"    [dim]{info['install_hint']}[/dim]")  # ← BUG: line 1224
```

The bug: `info['install_hint']` can contain `[browser]` (a literal chunk of a pip extras spec), which Rich parses as a markup tag inside the outer `[dim]...[/dim]` span. Rich silently drops unknown markup tags, so the rendered output shows `pip install 'clawteam' && playwright install chromium` instead of the correct `pip install 'clawteam[browser]' && playwright install chromium`.

The fix: escape the hint so Rich treats its brackets as literal text, not markup.

From rich.markup (Rich is already a project dependency — see commands.py:15 `from rich.console import Console`):

```python
from rich.markup import escape
# escape("pip install 'clawteam[browser]'") == "pip install 'clawteam\\[browser]'"
```

`rich.markup.escape` is the canonical way to embed arbitrary text inside a Rich markup string. It adds a single backslash before any `[` so Rich renders the literal bracket. The rendered terminal output has NO visible backslash — Rich consumes the escape.

Current _DOCTOR_TOOLS + install hint for chromium (unchanged, shown for reference — do NOT modify):

```python
# commands.py:36-41
_DOCTOR_TOOLS: tuple[tuple[str, str, str], ...] = (
    ("chromium (Playwright)", "python-pkg", "playwright"),
    ("codex", "cli", "codex"),
    ("ngrok", "cli", "ngrok"),
    ("watchdog", "python-pkg", "watchdog"),
)

# commands.py:47-51 (linux branch — applies to CI runner)
"chromium (Playwright)": {
    "darwin": "pip install 'clawteam[browser]' && playwright install chromium",
    "win32":  "pip install 'clawteam[browser]' && playwright install chromium",
    "linux":  "pip install 'clawteam[browser]' && playwright install chromium",
},
```

The hint STRING is correct. The renderer is what's broken. Fix the renderer, not the data.

Existing test shape at `tests/test_doctor.py` (Style B — flat test_* functions; monkeypatches at `shutil.which` and `importlib.util.find_spec` module paths; CliRunner invocation pattern):

```python
from __future__ import annotations

import json
from types import SimpleNamespace

from typer.testing import CliRunner

from clawteam.cli.commands import app


def test_doctor_reports_missing_tools_with_install_hints(monkeypatch):
    runner = CliRunner()
    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "missing" in result.output
    assert "chromium (Playwright)" in result.output
    ...
```

Reuse this exact style for the new regression test. Do NOT switch to class-based tests.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add regression test for literal `clawteam[browser]` in human-readable doctor output (RED)</name>
  <files>tests/test_doctor.py</files>
  <behavior>
    - New flat function `test_doctor_human_output_preserves_browser_extra(monkeypatch)` invokes `clawteam doctor` with all optional tools forced missing (same monkeypatch shape as the existing four tests) and asserts the literal substring `clawteam[browser]` appears in `result.output`.
    - Asserts `result.exit_code == 0` (doctor is informational — unchanged invariant).
    - Asserts the misrendered substring `pip install 'clawteam' && playwright install chromium` does NOT appear in the output (belt-and-braces against the Rich-elision regression returning).
    - New flat function `test_doctor_json_install_hint_preserves_browser_extra_unescaped(monkeypatch)` invokes `clawteam --json doctor`, parses JSON, and asserts the `install_hint` for `chromium (Playwright)` is the exact pre-escape string `pip install 'clawteam[browser]' && playwright install chromium` — confirming the JSON path does NOT get accidentally backslash-escaped by the fix (guardrail against a sloppy fix that mutates the underlying hint instead of just the rendering).
    - Before implementing Task 2, running `pytest tests/test_doctor.py::test_doctor_human_output_preserves_browser_extra -v` MUST FAIL with `AssertionError: 'clawteam[browser]' not in result.output` — this is the RED step that proves the test catches the bug.
  </behavior>
  <action>
    Append two flat test functions to the end of `tests/test_doctor.py`. Preserve the existing file's import block and Style B (flat `def test_*`) convention. Do NOT add a conftest entry; do NOT add fixtures; do NOT refactor existing tests.

    Add these two functions after `test_doctor_install_hints_follow_platform_dispatch` (line 88, end of file):

    ```python


    def test_doctor_human_output_preserves_browser_extra(monkeypatch):
        """Regression: Chromium install hint must render `clawteam[browser]` literally.

        Prior to the Rich-markup-escape fix, `console.print(f"[dim]{hint}[/dim]")`
        interpreted the literal substring `[browser]` inside the hint value
        `pip install 'clawteam[browser]' && playwright install chromium` as an
        unknown Rich markup tag and silently elided it — so users saw
        `pip install 'clawteam' && playwright install chromium` (wrong extra).
        Gap closure for UAT test 2 (severity: major).
        """
        runner = CliRunner()

        monkeypatch.setattr("shutil.which", lambda _name: None)
        monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

        result = runner.invoke(app, ["doctor"])

        assert result.exit_code == 0, result.output
        # Positive assertion: the literal extras spec must survive rendering.
        assert "clawteam[browser]" in result.output, (
            "Rich markup elided `[browser]` from the chromium install hint; "
            f"stdout was:\n{result.output}"
        )
        # Belt-and-braces: the misrendered form must NOT appear.
        assert "pip install 'clawteam' && playwright install chromium" not in result.output


    def test_doctor_json_install_hint_preserves_browser_extra_unescaped(monkeypatch):
        """The JSON path must emit the underlying hint WITHOUT backslash escapes.

        Guardrail: a sloppy fix that mutates the hint data (e.g. pre-escaping
        install_hint at construction time) would corrupt the JSON API surface.
        Fix must live in the rendering layer only.
        """
        runner = CliRunner()

        monkeypatch.setattr("shutil.which", lambda _name: None)
        monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

        result = runner.invoke(app, ["--json", "doctor"])

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        chromium_hint = payload["chromium (Playwright)"]["install_hint"]
        # Exact string — no backslash, no escape, no mutation.
        assert chromium_hint == (
            "pip install 'clawteam[browser]' && playwright install chromium"
        ), f"JSON install_hint was mutated: {chromium_hint!r}"
    ```

    Rules:
    - Flat `def test_*` — matches the rest of this file (Style B throughout tests/test_doctor.py).
    - `monkeypatch.setattr("shutil.which", ...)` and `monkeypatch.setattr("importlib.util.find_spec", ...)` — exactly the existing monkeypatch string targets in tests/test_doctor.py lines 14-15, 33-34, 48-49, 65-66. Do NOT switch to `clawteam.cli.commands.shutil.which` style; the current file uses the top-level module paths and the tests pass with that form on this codebase.
    - Use `CliRunner()` and `runner.invoke(app, ["doctor"])` — unchanged invocation shape.
    - Plain `assert` with a f-string diagnostic message on the key assertion (for fast debugging when the test fails).
    - Do NOT monkeypatch `sys.platform` — the default host platform (linux on CI) already uses the `linux` branch, whose chromium hint is identical to the darwin and win32 branches (all three contain `'clawteam[browser]'`). Test works on any platform.
    - Leave the 4 existing tests untouched.

    After appending, verify the RED state before moving to Task 2:

    ```bash
    .venv-sys/bin/python -m pytest tests/test_doctor.py::test_doctor_human_output_preserves_browser_extra -v
    ```

    Expected: FAILED with `AssertionError: Rich markup elided [browser] from the chromium install hint`. The second new test (`test_doctor_json_install_hint_preserves_browser_extra_unescaped`) should PASS already because the JSON path is already correct — running it now provides a baseline that the Task 2 fix must preserve.

    Commit the RED state:
    ```bash
    git add tests/test_doctor.py
    git commit -m "test(00-06): add failing regression for chromium install hint Rich-markup elision"
    ```
  </behavior>
  <action>
    See behavior block above for the exact test content. Apply to `tests/test_doctor.py`.

    Critical rules:
    - Append, do not edit, existing tests.
    - Preserve `from __future__ import annotations`, existing imports, and the `SimpleNamespace` import (used by `test_doctor_reports_found_tools`).
    - New functions go at the END of the file after `test_doctor_install_hints_follow_platform_dispatch`.
    - Two blank lines between top-level functions (PEP 8, already followed by the existing file).
    - After append, run ruff: `.venv-sys/bin/ruff check tests/test_doctor.py` — expect exit 0.
    - After append, run ONLY the new failing test to confirm RED — the others must continue to pass.

    Do NOT:
    - Do NOT add a class wrapper.
    - Do NOT add fixtures to conftest.py.
    - Do NOT change the existing tests' behavior, names, or assertions.
    - Do NOT widen the assertion to `"browser" in result.output` — that would pass even in the buggy state because `[browser]` contains the substring `browser` before Rich strips the brackets. The assertion MUST be the exact `clawteam[browser]` chunk so it genuinely catches the elision.
    - Do NOT skip the JSON guardrail test — it's the cheap insurance that catches a class of sloppy fixes (mutating hint data instead of rendering).
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && .venv-sys/bin/ruff check tests/test_doctor.py && .venv-sys/bin/python -m pytest tests/test_doctor.py::test_doctor_human_output_preserves_browser_extra -v 2>&1 | grep -q "FAILED" && .venv-sys/bin/python -m pytest tests/test_doctor.py::test_doctor_json_install_hint_preserves_browser_extra_unescaped -v 2>&1 | grep -q "PASSED" && echo "RED+baseline OK"</automated>
  </verify>
  <done>
    `tests/test_doctor.py` ends with two new flat test functions. Ruff exits 0. `test_doctor_human_output_preserves_browser_extra` FAILS with the expected assertion message (RED). `test_doctor_json_install_hint_preserves_browser_extra_unescaped` PASSES (JSON path already correct). Commit created for the RED state.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Escape install_hint via rich.markup.escape in doctor's human renderer (GREEN)</name>
  <files>clawteam/cli/commands.py</files>
  <behavior>
    - The `_human(d)` closure inside `doctor()` imports `escape` from `rich.markup` (lazy import inside the closure — matches the lazy-import convention already used by doctor for `shutil`, `sys`, `find_spec`).
    - The install-hint render call on (currently) line 1224 changes from `console.print(f"    [dim]{info['install_hint']}[/dim]")` to `console.print(f"    [dim]{escape(info['install_hint'])}[/dim]")`.
    - No other line in `doctor()` changes. No change to `_DOCTOR_TOOLS`. No change to `_doctor_install_hint`. No change to the checks-dict construction. No change to the JSON output path (which is `_output(checks, _human)` → the `_json_output` branch in `_output` prints raw JSON via `json.dumps` and never hits `_human`).
    - After the fix, running `pytest tests/test_doctor.py -v` shows all 6 tests passing (the original 4 + the 2 new ones from Task 1).
    - Running `.venv-sys/bin/clawteam doctor` on the host (chromium missing per the previous UAT) prints a line whose human-readable hint contains `clawteam[browser]` literally.
  </behavior>
  <action>
    Edit `clawteam/cli/commands.py`. The target is the `doctor` function's `_human` closure, currently spanning lines 1213-1224. Make exactly two changes:

    ### Change 1: Add lazy import of `escape` inside `_human`

    Between the closure's `def _human(d):` line and the first `console.print` line, add one import line. The closure currently looks like (lines 1213-1224):

    ```python
        def _human(d):
            console.print(f"\nDoctor OS: [cyan]{d['os']['platform']}[/cyan]")
            for name, _, _ in _DOCTOR_TOOLS:
                info = d[name]
                if info["found"]:
                    console.print(
                        f"  {name}: [green]OK[/green]  [dim]{info['path'] or '(available)'}[/dim]"
                    )
                else:
                    console.print(f"  {name}: [yellow]missing[/yellow]")
                    if info["install_hint"]:
                        console.print(f"    [dim]{info['install_hint']}[/dim]")
    ```

    After edit, it becomes:

    ```python
        def _human(d):
            from rich.markup import escape

            console.print(f"\nDoctor OS: [cyan]{d['os']['platform']}[/cyan]")
            for name, _, _ in _DOCTOR_TOOLS:
                info = d[name]
                if info["found"]:
                    console.print(
                        f"  {name}: [green]OK[/green]  [dim]{escape(info['path'] or '(available)')}[/dim]"
                    )
                else:
                    console.print(f"  {name}: [yellow]missing[/yellow]")
                    if info["install_hint"]:
                        console.print(f"    [dim]{escape(info['install_hint'])}[/dim]")
    ```

    Notes on the two edits:

    1. **`from rich.markup import escape`** — lazy import inside the closure matches the doctor command's existing lazy-import convention (line 1194-1195 already does `import shutil` / `from importlib.util import find_spec` lazily). Keeps module-level import surface unchanged. `rich` is already a direct dependency of ClawTeam (`from rich.console import Console` at line 15) — no new dep.

    2. **Two call sites wrapped with `escape(...)`**:
       - The `found` branch's path rendering (`info['path'] or '(available)'`) — also wrapped for defense-in-depth because `shutil.which` can in principle return any filesystem path, and a path containing `[` would hit the same elision bug. Today the only affected paths are CLI binaries (codex, ngrok, …) with ASCII-safe paths, but escaping costs nothing and closes the class of bugs.
       - The `missing` branch's `install_hint` rendering — the actual bug site per UAT test 2.

    ### What NOT to change

    - Do NOT touch the `_DOCTOR_TOOLS` tuple (line 36-41) — the data is correct.
    - Do NOT touch `_doctor_install_hint` (line 44-73) — the returned strings are correct; the bug was never in the data.
    - Do NOT touch the `checks: dict[...]` construction (lines 1197-1211) — the JSON payload is correct and UAT test 3 already passes.
    - Do NOT touch the `_output(checks, _human)` dispatch — the function router is correct.
    - Do NOT add a global `from rich.markup import escape` at module top. Keep the lazy-import-inside-closure convention that the rest of `doctor` uses. Top-level imports in commands.py are kept deliberately short per the file's own comments around line 1-35.
    - Do NOT refactor the f-string into a Rich `Text` object with explicit style. The one-line `escape()` wrapper is the minimum-disruption fix. Switching to `Text(…, style="dim")` is a viable alternative but would rewrite four lines where one suffices; reject it for this surgical fix.
    - Do NOT add a feature flag or toggle. The fix is always-on.

    ### Why escape, not Text

    `rich.markup.escape(s)` returns a string identical to `s` with each `[` replaced by `\[`. Rich's markup parser consumes the backslash and renders the literal bracket; the terminal output contains no visible backslash. This is Rich's canonical documented way to embed user-controlled text inside a markup string (see Rich docs § Escaping). The `Text` object alternative would require constructing a Text, setting style=dim, passing to console.print — three extra lines and a different rendering pathway that isn't used elsewhere in this codebase (every other rich render in commands.py uses f-string-plus-markup-tags).

    ### Running the GREEN proof

    After the edit, run the full test file:

    ```bash
    .venv-sys/bin/python -m pytest tests/test_doctor.py -v
    ```

    Expected: 6 passed (4 pre-existing + 2 added in Task 1). Specifically:
    - `test_doctor_reports_missing_tools_with_install_hints` — PASS (unchanged).
    - `test_doctor_reports_found_tools` — PASS (unchanged; note: the `OK` path's `(available)` sentinel is now run through `escape()`, but `(available)` has no brackets so output is identical).
    - `test_doctor_json_output_shape` — PASS (unchanged; JSON path never calls `_human`).
    - `test_doctor_install_hints_follow_platform_dispatch` — PASS (unchanged; tests raw JSON payload, not rendered output).
    - `test_doctor_human_output_preserves_browser_extra` — NOW PASSES (was RED in Task 1; GREEN after this fix).
    - `test_doctor_json_install_hint_preserves_browser_extra_unescaped` — PASS (baseline from Task 1; confirms fix did not mutate hint data).

    Run ruff:

    ```bash
    .venv-sys/bin/ruff check clawteam/cli/commands.py
    ```

    Expected: exit 0. The lazy import inside the closure does not trigger any `I` (import-sort) violations because the rule applies to module-level imports only.

    Manual sanity check (optional but recommended — the UAT command that originally surfaced the bug):

    ```bash
    .venv-sys/bin/clawteam doctor
    ```

    Expected: the human-readable output's Chromium line reads
    `pip install 'clawteam[browser]' && playwright install chromium` — brackets present.

    Commit the GREEN state:

    ```bash
    git add clawteam/cli/commands.py
    git commit -m "fix(00-06): escape install_hint via rich.markup.escape so '[browser]' renders literally"
    ```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && .venv-sys/bin/ruff check clawteam/cli/commands.py && .venv-sys/bin/python -m pytest tests/test_doctor.py -v && .venv-sys/bin/clawteam doctor | grep -q "clawteam\[browser\]" && .venv-sys/bin/clawteam --json doctor | .venv-sys/bin/python -c "import json,sys; h=json.load(sys.stdin)['chromium (Playwright)']['install_hint']; assert h == \"pip install 'clawteam[browser]' && playwright install chromium\", h; print('JSON unchanged OK')"</automated>
  </verify>
  <done>
    `clawteam/cli/commands.py` imports `escape` lazily inside the `_human` closure and wraps both `info['path']` and `info['install_hint']` with `escape(...)`. All 6 tests in tests/test_doctor.py pass. Ruff exits 0. Live `clawteam doctor` on the host prints `clawteam[browser]` literally in the human-readable chromium install hint. Live `clawteam --json doctor` continues to emit the unescaped hint. Two atomic commits exist (RED in Task 1, GREEN here).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `_doctor_install_hint()` return value → `rich.Console.print` markup parser | Static in-tree strings flow into a markup parser that interprets `[tag]` syntax. Today the only bracketed substring is `[browser]` (not a secret), but any future hint containing user-visible bracketed tokens hits the same elision pathway if unescaped. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-00-11 | Information Disclosure (inverted — *under*-disclosure) | `clawteam/cli/commands.py::doctor::_human` | mitigate | Wrapping `info['install_hint']` with `rich.markup.escape` restores full content fidelity. Wrapping `info['path']` with the same call closes the analogous future-proof path-rendering case (filesystem paths can in principle contain `[`). Regression test `test_doctor_human_output_preserves_browser_extra` asserts the fix does not regress. |
| T-00-12 | Tampering | hint-data mutation by a sloppy future fix | mitigate | Guardrail test `test_doctor_json_install_hint_preserves_browser_extra_unescaped` asserts the JSON payload's `install_hint` field equals the exact pre-escape string. Any future PR that pre-escapes hint data at construction time (wrong layer) fails this test. |
| T-00-13 | Denial of Service | malformed Rich markup crashes the renderer | accept | `rich.markup.escape` is documented to return a parseable string for any input. No known crash mode. Doctor is informational and exits 0 on all paths per ROADMAP criterion #3. |
</threat_model>

<verification>
Gap-closure verification (maps back to UAT test 2 directly):

```bash
cd /home/jac/repos/ClawTeam-gstack

# Ruff + full doctor test file
.venv-sys/bin/ruff check clawteam/cli/commands.py tests/test_doctor.py
.venv-sys/bin/python -m pytest tests/test_doctor.py -v

# Live smoke — the exact command the UAT ran
.venv-sys/bin/clawteam doctor
# Expected stdout line for chromium (Playwright): the missing-tool block shows
#   pip install 'clawteam[browser]' && playwright install chromium

# JSON path regression check
.venv-sys/bin/clawteam --json doctor | .venv-sys/bin/python -c "
import json, sys
d = json.load(sys.stdin)
assert d['chromium (Playwright)']['install_hint'] == \"pip install 'clawteam[browser]' && playwright install chromium\"
print('JSON unchanged OK')
"

# BC regression — every other test file still passes
.venv-sys/bin/python -m pytest tests/test_cli_commands.py tests/test_env_scrub.py tests/test_template_regression_matrix.py -q
```

Expected:
- Ruff exit 0 on both files.
- `pytest tests/test_doctor.py -v` → 6 passed.
- Live `clawteam doctor` contains the literal substring `clawteam[browser]` in the Chromium line.
- JSON path still emits the exact unescaped hint string.
- All other test files pass — fix is purely additive to `_human` closure.

UAT re-run expectation:
- Phase 0 UAT test 2 moves from `result: issue` to `result: pass`. Evidence string becomes: `clawteam doctor stdout shows "pip install 'clawteam[browser]' && playwright install chromium" — Rich elision fixed via rich.markup.escape; JSON install_hint unchanged.`
</verification>

<success_criteria>
1. `tests/test_doctor.py` contains two new flat test functions: `test_doctor_human_output_preserves_browser_extra` and `test_doctor_json_install_hint_preserves_browser_extra_unescaped`.
2. `clawteam/cli/commands.py::doctor::_human` imports `escape` from `rich.markup` (lazy, inside the closure) and wraps both `info['path']` and `info['install_hint']` with `escape(...)`.
3. `ruff check clawteam/cli/commands.py tests/test_doctor.py` exits 0.
4. `pytest tests/test_doctor.py -v` → all 6 tests pass (4 pre-existing + 2 new).
5. Live `clawteam doctor` invocation on the host (chromium missing) prints a line containing the literal substring `clawteam[browser]` — i.e. the `[browser]` extra is no longer elided.
6. `clawteam --json doctor` continues to emit an `install_hint` for `chromium (Playwright)` equal to the exact unescaped string `pip install 'clawteam[browser]' && playwright install chromium` — the JSON path is not accidentally mutated by the fix.
7. Phase 0 ROADMAP success criterion #3 now holds end-to-end: missing-tool install hints are correct on both the human-readable and machine-readable output surfaces.
8. BC regression: `pytest tests/test_cli_commands.py tests/test_env_scrub.py tests/test_template_regression_matrix.py -q` continues to pass.
9. Two atomic commits exist: RED (Task 1 test) and GREEN (Task 2 fix), each scoped to `00-06` in its message prefix.
</success_criteria>

<output>
After completion, create `.planning/phases/00-foundation-upstream-rfc/00-06-doctor-rich-markup-fix-SUMMARY.md` following `@$HOME/.claude/get-shit-done/templates/summary.md`, documenting:
- Root cause: Rich `console.print(f"[dim]{hint}[/dim]")` interprets bracketed substrings inside `hint` as markup tags; `[browser]` inside the chromium extras spec was silently elided.
- Fix: wrap user-visible content with `rich.markup.escape(...)` at the render layer; data strings unchanged. Applied to both `info['path']` and `info['install_hint']` in doctor's `_human` closure.
- Decision: escape-at-render over Text-object-with-style over pre-escape-at-construction. Rationale:
  - Escape-at-render is the one-line fix that matches Rich's documented idiom for embedding arbitrary text in markup strings.
  - Text objects would require rewriting four render lines and introduce a rendering pathway not used elsewhere in `clawteam/cli/commands.py`.
  - Pre-escape-at-construction would mutate the hint data, corrupting the JSON API surface — explicitly guarded against by `test_doctor_json_install_hint_preserves_browser_extra_unescaped`.
- Gap closed: Phase 0 UAT test 2 (severity major); ROADMAP Phase 0 success criterion #3 now fully satisfied.
- Pattern for future doctor contributors: any `console.print(f"[...]{user_content}[/...]")` in this codebase should route `user_content` through `rich.markup.escape` if the content may contain `[`. The fix's path-rendering change demonstrates the general pattern for future tools with filesystem-path content.
</output>
