---
phase: 00-foundation-upstream-rfc
plan: 06
subsystem: cli
tags: [cli, doctor, rich, bugfix, ux, gap-closure, tdd, regression]

# Dependency graph
requires:
  - phase: 00-foundation-upstream-rfc
    provides: "`clawteam doctor` command + `_DOCTOR_TOOLS` registry + `_doctor_install_hint` (from 00-02)"
provides:
  - "`clawteam doctor` human-readable output renders `[browser]` literally in the chromium install hint"
  - "Rich-markup-safe rendering pattern (`escape()` at the render layer) for all user-visible hint/path content in the doctor command"
  - "Regression test `test_doctor_human_output_preserves_browser_extra` + guardrail `test_doctor_json_install_hint_preserves_browser_extra_unescaped` locking both the fix and the JSON invariant"
affects: [doctor, cli-rendering, future-tools-with-bracketed-content, uat-phase-0]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "rich.markup.escape at the render layer (not at data-construction time) to embed arbitrary strings inside Rich markup spans"
    - "Lazy import inside closure for render-only utilities — matches doctor's existing lazy-import convention (shutil, importlib.util.find_spec)"

key-files:
  created: []
  modified:
    - "clawteam/cli/commands.py — `doctor::_human` closure wraps `info['path']` and `info['install_hint']` with `rich.markup.escape`"
    - "tests/test_doctor.py — two new flat test functions (human-literal regression + JSON-unchanged guardrail)"

key-decisions:
  - "Fix at the render layer with `rich.markup.escape`, not at data construction — keeps the JSON API surface unchanged and keeps the install-hint source strings canonical"
  - "Applied `escape(...)` to both the `found` branch's path rendering and the `missing` branch's install_hint — closes the class of bugs (any future filesystem path containing `[` would hit the same elision)"
  - "Lazy `from rich.markup import escape` inside the `_human` closure — matches the doctor command's existing lazy-import convention; keeps module-level import surface unchanged"
  - "Rejected `rich.Text` object alternative — would rewrite four lines where one `escape()` wrapper suffices, and would introduce a rendering pathway not used elsewhere in `commands.py`"
  - "Added JSON-guardrail test asserting the exact unescaped hint string — catches any future sloppy fix that mutates hint data at construction time"

patterns-established:
  - "Render-layer escaping for Rich markup: wrap any `f\"[tag]{user_content}[/tag]\"` content with `rich.markup.escape(user_content)` when the content may contain `[` (install hints, filesystem paths, tool labels, etc.)"
  - "TDD gap closure: one RED commit (failing regression test) + one GREEN commit (minimal production fix) — surgical bugfix scope, no refactor smuggled in"
  - "Belt-and-braces regression assertions: assert the positive literal (`clawteam[browser]` present) AND the negative misrendered form (`pip install 'clawteam' && ...` absent) — prevents the bug returning via a different misrendering"

requirements-completed: [UX-08]

# Metrics
duration: 2min
completed: 2026-04-16
---

# Phase 00 Plan 06: Doctor Rich-Markup Fix Summary

**`clawteam doctor` human-readable output now renders `clawteam[browser]` literally — fixed the Rich-markup elision bug by escaping `info['path']` and `info['install_hint']` at the render layer via `rich.markup.escape`, with a two-assertion regression test locking both the human and JSON paths.**

## Performance

- **Duration:** ~2 min (automated, surgical two-task TDD plan)
- **Started:** 2026-04-16T10:52:24Z
- **Completed:** 2026-04-16T10:53:59Z
- **Tasks:** 2 (both TDD: RED test + GREEN fix)
- **Files modified:** 2 (`clawteam/cli/commands.py`, `tests/test_doctor.py`)

## Accomplishments

- Closed Phase 0 UAT Gap 1 (test 2, severity major): `clawteam doctor` stdout now contains the literal substring `clawteam[browser]` when Chromium is missing.
- Root cause identified and fixed at the correct layer: Rich's markup parser was silently eliding `[browser]` inside `f"[dim]{hint}[/dim]"` because `[browser]` looks like an unknown markup tag. Fix is one-line `escape()` wrapper at the render call site, not a data mutation.
- Added two regression tests: positive (literal `clawteam[browser]` must appear in human stdout) + guardrail (JSON `install_hint` must equal the exact unescaped string, catching any future pre-escape-at-construction mistake).
- Defensively wrapped `info['path']` rendering as well — future tools whose `which` path contains `[` will not hit the same elision bug.
- Phase 0 ROADMAP success criterion #3 (per-OS install hints for missing optional tools) now holds end-to-end on both the human-readable and machine-readable output surfaces.

## Task Commits

Each task committed atomically (TDD gate sequence: RED → GREEN):

1. **Task 1: Add failing regression test (RED)** — `6dacb38` (test)
2. **Task 2: Escape install_hint via rich.markup.escape (GREEN)** — `a1e7a43` (fix)

**Plan metadata:** pending final SUMMARY commit (this file)

_TDD gate compliance: RED commit (`test(00-06): ...`) precedes GREEN commit (`fix(00-06): ...`); no REFACTOR needed (fix is already minimal)._

## Files Created/Modified

- `clawteam/cli/commands.py` — `doctor::_human` closure: added lazy `from rich.markup import escape`; wrapped both `info['path']` and `info['install_hint']` with `escape(...)` in their respective `console.print` f-strings. 4 insertions / 2 deletions; surgical bugfix, no refactor.
- `tests/test_doctor.py` — appended two flat test functions after `test_doctor_install_hints_follow_platform_dispatch`:
  - `test_doctor_human_output_preserves_browser_extra` — asserts `'clawteam[browser]' in result.output` when Chromium missing; also asserts the misrendered `"pip install 'clawteam' && playwright install chromium"` is NOT present.
  - `test_doctor_json_install_hint_preserves_browser_extra_unescaped` — asserts the JSON `install_hint` for `chromium (Playwright)` equals the exact pre-escape string, catching mutation at the data layer.
  - 50 insertions, zero edits to the 4 pre-existing tests.

## Decisions Made

- **Fix layer: render, not data.** Wrapping `info['install_hint']` with `rich.markup.escape` in the render call is the canonical Rich idiom for embedding arbitrary strings inside a markup span. Pre-escaping at construction time would mutate the JSON API surface (a breaking change for any programmatic consumer). Escape-at-render preserves the hint string as-is everywhere except the one rendering pathway that needs the escape.
- **Apply `escape` to both `info['path']` and `info['install_hint']`.** The `install_hint` wrap is the actual UAT gap; the `info['path']` wrap is defense-in-depth for the same class of bug — filesystem paths with `[` in them would elide the same way today, and the cost is zero.
- **Lazy import inside closure.** `doctor` already imports `shutil` and `importlib.util.find_spec` lazily inside its body; adding `from rich.markup import escape` inside `_human` follows the same convention and keeps module-level import surface unchanged.
- **Reject `rich.Text` object alternative.** Would rewrite four render lines where a one-line `escape()` wrapper suffices, and would introduce a rendering pathway not used elsewhere in `commands.py`. Rejected for surgical-fix scope.
- **Two regression tests, not one.** The human test catches the present bug; the JSON test is a cheap guardrail catching a whole class of future bad fixes (any PR that pre-escapes hint data at construction would fail the JSON test). Both are flat `def test_*` functions matching the existing Style B throughout `tests/test_doctor.py`.

## Deviations from Plan

None — plan executed exactly as written.

Test assertions, monkeypatch shape, import style, and commit-message prefixes all followed the plan's `<action>` block verbatim. RED → GREEN sequence observed with TDD gate commits.

## Issues Encountered

None.

- Pre-flight baseline (before Task 1) reproduced the buggy state exactly as the UAT evidence described: `pip install 'clawteam' && playwright install chromium` rendered instead of the correct `pip install 'clawteam[browser]' && ...`.
- Task 1 test FAILED as expected (RED proof) with the precise `AssertionError: Rich markup elided [browser] from the chromium install hint` message.
- Task 2 edit made the Task 1 test pass without breaking any of the 4 pre-existing tests or any of the 63 BC-regression tests (test_cli_commands.py + test_env_scrub.py + test_template_regression_matrix.py).
- Live smoke `clawteam doctor` on the host prints `clawteam[browser]` literally.
- Live smoke `clawteam --json doctor` emits the exact unescaped `install_hint` string — JSON path unchanged.

## User Setup Required

None — no external service configuration required. This is a pure render-layer bugfix in an already-installed command.

## Next Phase Readiness

- Phase 0 UAT test 2 is now unblocked: next UAT re-run should flip it from `result: issue` to `result: pass` with evidence string `clawteam doctor stdout shows "pip install 'clawteam[browser]' && playwright install chromium" — Rich elision fixed via rich.markup.escape; JSON install_hint unchanged.`
- Phase 0 ROADMAP success criterion #3 is now fully satisfied across both human and JSON output surfaces.
- Pattern established for future doctor contributors: any `console.print(f"[...]{user_content}[/...]")` in this codebase should route `user_content` through `rich.markup.escape` if the content may contain `[`. The `info['path']` wrap in this plan demonstrates the general pattern for filesystem-path content.
- Requirement UX-08 (correct install hints on human-readable doctor output) satisfied; can be marked complete in REQUIREMENTS.md when the orchestrator runs `requirements mark-complete UX-08`.

## Self-Check: PASSED

- `clawteam/cli/commands.py` modified (escape wrapper added at lines 1214, 1221, 1226): FOUND
- `tests/test_doctor.py` appended with two new test functions (lines 90-137): FOUND
- Commit `6dacb38` (RED test): FOUND in `git log`
- Commit `a1e7a43` (GREEN fix): FOUND in `git log`
- All 6 tests in `tests/test_doctor.py` PASS: confirmed via pytest
- BC regression (tests/test_cli_commands.py + test_env_scrub.py + test_template_regression_matrix.py): 63 passed
- Ruff exit 0 on both modified files: confirmed
- Live `clawteam doctor` contains literal `clawteam[browser]`: confirmed
- Live `clawteam --json doctor` emits exact unescaped install_hint: confirmed

---
*Phase: 00-foundation-upstream-rfc*
*Completed: 2026-04-16*
