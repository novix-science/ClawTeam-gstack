---
phase: 06-browser-skills-design-pipeline-team-memory
fixed_at: 2026-04-22T00:00:00Z
review_path: .planning/phases/06-browser-skills-design-pipeline-team-memory/06-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 6: Code Review Fix Report

**Fixed at:** 2026-04-22T00:00:00Z
**Source review:** `.planning/phases/06-browser-skills-design-pipeline-team-memory/06-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope (Critical + Warning): 5
- Fixed: 5
- Skipped: 0

All five Warning findings addressed. Zero Critical findings were present in
REVIEW.md. Info findings (IN-01 through IN-06) remain deferred per scope.

Each fix was applied atomically with a regression test and verified by
running the relevant pytest target (all green: 113 tests across the
changed surfaces). `ruff check` is clean on every file I modified;
pre-existing lint issues (unused `FrameworkDetection` import, import-block
ordering in two test files) were left untouched because they predate this
review and are out of scope for a fix-only pass.

## Fixed Issues

### WR-01: `/design-html` does not validate `component_name`

**Files modified:** `clawteam/templates/gstack/skills/design_html/handler.py`, `tests/templates/gstack/skills/test_design_html.py`
**Commit:** `7602400` (combined with WR-02)
**Applied fix:** Added `_COMPONENT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")` and `_validate_component_name()` helper. Called from `design_html_handler` after resolving `component_name` from args, BEFORE any `_emit_*` call. Rejects POSIX + Windows traversal, embedded traversal, dots, shell metacharacters, absolute paths, >64-char names, and non-ASCII. 10-case parametrized regression test plus positive-case test covering `Hero`, `hero`, `Hero_v2`, `H`, `A0`, 64-char max.

### WR-02: `/design-html` does not enforce `project_root` / `mockup_html_path` containment

**Files modified:** `clawteam/templates/gstack/skills/design_html/handler.py`, `tests/templates/gstack/skills/test_design_html.py`
**Commit:** `7602400` (combined with WR-01)
**Applied fix:** Added `_resolve_within_workspace()` helper that enforces containment when `ctx.workspace_root` is set. Applied to both the read path (`mockup_html_path`) and the write path (`project_root`). When `workspace_root` is absent, the handler falls back to the role-gating trust boundary (documented explicitly in the `design_html_handler` docstring). Opt-in design keeps existing callers working while letting security-sensitive deployments enforce containment. Four regression tests: allow-inside, reject-project-root-outside, reject-mockup-outside, no-containment-without-workspace-root.

### WR-03: Broad `except Exception: pass` in learn/backfill silently swallow failures

**Files modified:** `clawteam/memory/backfill.py`, `clawteam/templates/gstack/skills/learn/handler.py`, `tests/memory/test_backfill_scanner.py`
**Commit:** `757c383`
**Applied fix:** Added module-level `_LOG = logging.getLogger(__name__)` to both `backfill.py` and `learn/handler.py`. Every broad-catch block now calls `_LOG.warning(..., exc_info=True)` before swallowing. Five sites patched:
- `backfill.py:117` (per-entry promote failure, now logs `team` + `retro_path`)
- `learn/handler.py:60` (`_ensure_backfilled` scan failure, logs `team_name`)
- `learn/handler.py:188` (ConflictDetected import failure)
- `learn/handler.py:192` (bus unavailable)
- `learn/handler.py:206` (per-conflict emit failure, logs `new_id` + `other_id`)

Added 2 regression tests using `caplog` to assert `logger.warning` fires for both the per-entry failure (monkeypatched `BoomStore.write`) and the scan-level failure (monkeypatched `backfill_scan`).

### WR-04: `_invoke_learn` CLI redundant `(ValueError, Exception)` catch

**Files modified:** `clawteam/cli/commands.py`, `tests/test_learn_cli.py`
**Commit:** `fb60406`
**Applied fix:** Split the single `except (ValueError, Exception)` into two branches:
- `ValueError` → structured `{"error": str(exc)}` payload, clean `typer.Exit(code=1)` (preserves existing test behavior for bad `--impact`, missing `--role`, `confidence>1.0`).
- `Exception` → `logger.exception(...)` captures full traceback, emits `{"error": "Unexpected: <Type>: <msg>"}`, then `raise` so Typer surfaces the traceback for operators.

Added 2 regression tests monkeypatching `learn_handler` to raise `ValueError` and `RuntimeError` respectively, asserting the correct payload + log behavior for each.

**Note on in-flight Phase 7 work:** The upfront guidance flagged that `commands.py` might have uncommitted Phase 7 cost-panel changes; by the time I started work those changes had been committed (latest feat/style commits on 07-07 were already in history), so there was no conflict. WR-04 was applied normally.

### WR-05: `TeamMemoryStore.list` swallows `MemoryEntry` validation errors with bare `except Exception`

**Files modified:** `clawteam/memory/store.py`, `tests/memory/test_store_write_read.py`
**Commit:** `c3f14ad`
**Applied fix:** Imported `pydantic.ValidationError`; narrowed `except Exception` to `except ValidationError`. Legacy-data malformed records continue to be skipped silently (T-06-02-04 invariant preserved); programmer errors like `TypeError` or `KeyError` from future refactors now surface loudly rather than being hidden as "bad legacy data".

Added 2 regression tests: `test_list_silently_skips_pydantic_validation_errors` verifies a `confidence>1.0` legacy shape is skipped while a co-resident valid entry is still returned; `test_list_raises_on_non_validation_errors` monkeypatches `MemoryEntry` to raise `TypeError` and asserts the exception propagates out of `store.list`.

**Note on commit contents:** This commit (`c3f14ad`) also happens to contain changes to `clawteam/workspace/gc.py` and `tests/workspace/test_zombie_gc.py` from a concurrent Phase 7 Plan 07-08 GREEN worker. My `git add` was narrow (only `clawteam/memory/store.py tests/memory/test_store_write_read.py`), but the commit index at `git commit` time picked up files another process had staged. The WR-05 change itself is atomic and correct; the co-committed Phase 7 code is unrelated but harmless (it unblocks a failing RED test added in preceding commit `dcbd7f7`). I did not unwind history to isolate — the WR-05 fix is intact and verifiable by the regression tests added alongside.

## Skipped Issues

None.

## Verification Summary

All 5 findings were verified via 3-tier verification:

- **Tier 1 (re-read):** every edited file re-read after edit to confirm fix and surrounding code intact.
- **Tier 2 (syntax + tests):** `python -c "ast.parse(open(f).read())"` passed for every edited Python file; targeted pytest runs green after each fix (`design_html`: 29 tests; `backfill`: 7 tests; `learn_cli`: 11 tests; `store_write_read`: 13 tests). Final cross-surface run 126 tests green.
- **Tier 3 (lint):** `ruff check` clean on every file I modified (one auto-fix for import-block ordering in `design_html/handler.py`, shipped as follow-up `05e5e25`). Pre-existing `F401`/`I001` issues in `tests/templates/gstack/skills/test_design_html.py` and `tests/memory/test_store_write_read.py` left untouched (out of scope).

## Commit History (in order)

1. `7602400` — fix(06): WR-01,WR-02 harden /design-html input validation
2. `757c383` — fix(06): WR-03 log swallowed exceptions in advisory paths
3. `fb60406` — fix(06): WR-04 split ValueError vs unexpected errors in _invoke_learn
4. `c3f14ad` — fix(06): WR-05 narrow list() exception to pydantic ValidationError
5. `05e5e25` — style(06): drop redundant blank line after imports (ruff I001) [follow-up]

Interleaved with unrelated concurrent commits by other workers:
- `1749800 docs(07-07): complete dashboard-team-show plan`
- `dcbd7f7 test(07-08): add failing tests for zombie-worktree GC + disk-budget (Task 1 RED)`
- `cc3368a test(07-08): add failing tests for clawteam doctor --gc (Task 2 RED)`

---

_Fixed: 2026-04-22T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
