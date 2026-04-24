---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 08
subsystem: skill-canary
tags:
  - skill-canary
  - post-deploy-monitor
  - regression-event
  - sre
  - playwright-lazy
  - deploy-regression-detected

# Dependency graph
requires:
  - phase: 05-01
    provides: SkillRegistration + SkillDispatcher + CanaryConfig template field
  - phase: 05-02
    provides: CanaryReport pydantic schema + DeployRegressionDetected HarnessEvent
  - phase: 05-06
    provides: /land-and-deploy writes deploy.md with deploy_url + provider
provides:
  - /canary skill sub-package (handler + poller) at clawteam/templates/gstack/skills/canary/
  - Post-deploy HTTP polling monitor with configurable window + poll interval
  - Regression evaluator (5xx>1% OR response>2x_baseline OR any JS console error)
  - DeployRegressionDetected emission on any regression flag
  - Pitfall 5 lazy-import defense for Playwright (AST-verified)
  - GstackSprintPlugin now registers 7 skills total
affects:
  - 05-09 (/benchmark writes baseline JSON consumed by /canary)
  - Phase 6 (browser scraping may extend _get_browser_errors)
  - Phase 7 (clawteam attend --summary will surface DeployRegressionDetected)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lazy-import defense: find_spec short-circuit + try/except ImportError + bare-except browser crash guard; AST test locks module-top import-free"
    - "Injectable http_fn + sleep_fn: tests never touch the wall clock; deadline uses time.monotonic for clock-adjustment safety"
    - "Literal grep-able flag strings: '5xx_rate>1%' / 'response_time>2x_baseline' / 'js_console_error' so downstream consumers do not depend on PollResult schema"
    - "PEP 562 __getattr__ in __init__.py to lazy-import handler so the package can be loaded before handler.py exists (enables Task 1 isolation)"

key-files:
  created:
    - clawteam/templates/gstack/skills/canary/__init__.py
    - clawteam/templates/gstack/skills/canary/poller.py
    - clawteam/templates/gstack/skills/canary/handler.py
    - tests/templates/gstack/skills/test_canary.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py

key-decisions:
  - "get_data_dir sourced from clawteam.team.models (canonical Phase 3 substrate) with paths.py/utils.py fallbacks for minimal test environments"
  - "Transport errors (URLError/HTTPError/TimeoutError/OSError) in _default_http_fn coerced to status 599; caller counts as 5xx so the poll loop never bubbles exceptions (T-05-08-01 DoS mitigation)"
  - "poll_window guarantees at least one HTTP sample before the monotonic deadline so short windows (D-15 adversarial) don't produce empty PollResult that the evaluator can't reason about"
  - "_render_canary_report_yaml reuses the hand-rolled YAML emitter shape from /ship + /land-and-deploy so Phase 5 skills stay consistent without a pyyaml dep"
  - "canary_handler's ctx.bus.emit is wrapped in try/except — regression events are advisory-only and must never fail the handler (T-05-08-02 philosophy extended to event surface)"
  - "Playwright import is GUARDED by find_spec('playwright') BEFORE the try/except ImportError so minimal-install environments never pay the ImportError cost (Pitfall 5)"
  - "__init__.py uses PEP 562 __getattr__ to lazy-load canary_handler so Task 1 could commit a green test suite before handler.py existed (avoids the Task-1-imports-handler coupling)"

patterns-established:
  - "AST-verified lazy-import pattern: tests/templates/gstack/skills/test_canary.py::test_handler_module_level_no_playwright_import walks ast.Import + ast.ImportFrom nodes at Module body level to assert no playwright reference — future editors cannot accidentally promote the import"
  - "Literal regression flag strings: downstream consumers grep on the literal string, not a type-checked enum, so the flag vocabulary is a grep-friendly API"
  - "Writer symmetry: _render_canary_report_yaml mirrors _render_deploy_notes_yaml + /ship's writer so the three Phase 5 artifact-writing skills share an emitter shape"

requirements-completed: [SKILL-17]

# Metrics
duration: 9min
completed: 2026-04-21
---

# Phase 5 Plan 08: /canary Skill Summary

**Post-deploy HTTP polling monitor (SKILL-17) — polls deploy_url every 15s for 300s window, flags 5xx>1% OR response>2x baseline OR JS console error, writes canary-report.md, emits DeployRegressionDetected event; Playwright is lazy-imported per Pitfall 5 with AST-verified defense.**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-21T14:50:48Z
- **Completed:** 2026-04-21T14:59:48Z
- **Tasks:** 2 (both TDD: RED + GREEN)
- **Files created:** 4 (3 source + 1 test)
- **Files modified:** 1 (plugin wiring)

## Accomplishments

- Shipped `/canary` skill as a 2-file sub-package (handler + poller) at `clawteam/templates/gstack/skills/canary/` — 21 green tests covering happy path, 503 adversarial, network error, baseline-missing, browser-without-Playwright, module-level import AST check, sre role gating, template config flow-through, DeployRegressionDetected emission, and regression reporting
- **poller.py** `PollResult` dataclass + `poll_window` (injectable http_fn + sleep_fn, monotonic deadline, guaranteed first sample) + `evaluate_regression` (three independent threshold checks returning literal grep-able flags) + `baseline_path` / `load_baseline` (best-effort with malformed-JSON tolerance, T-05-08-03)
- **handler.py** `canary_handler` 4-phase orchestration: read deploy.md frontmatter → load baseline → poll window → evaluate regression → atomic-write canary-report.md → emit DeployRegressionDetected via `ctx.bus.emit` on any regression flag (all emission wrapped in try/except — advisory-only)
- **_get_browser_errors** lazy-imports Playwright *inside* the function body (Pitfall 5 / T-05-08-05 defense): `find_spec` short-circuit → try-except ImportError → try-except bare-browser-crash; test_handler_module_level_no_playwright_import walks the AST to prove no module-top playwright import exists
- **Plugin registration:** `GstackSprintPlugin.contribute_skills` now returns 7 `SkillRegistration` entries (added `/canary` with `roles=frozenset({'sre'})`, `handler=_canary_handler`, `tool_available=None` since stdlib urllib is baseline)

## Task Commits

Each task was committed atomically following the TDD RED → GREEN cycle:

1. **Task 1 RED: failing tests for poller + handler** — `c131014` (test)
2. **Task 1 GREEN: poller.py + canary sub-package** — `756e596` (feat)
3. **Task 2 GREEN: canary_handler + lazy Playwright + plugin registration** — `6c4b3d1` (feat — also re-applied the test harness fix for SkillDispatcher signature discovered during run)

_Task 2 had no separate RED commit because all Task-2 tests were written up-front in commit c131014; that commit already contains the Task-2 test suite (tests 12-21) which went from red to green once handler.py landed in 6c4b3d1._

**Plan metadata:** (this summary commit — `docs(05-08): complete canary-skill plan`)

## Files Created/Modified

- `clawteam/templates/gstack/skills/canary/__init__.py` — re-exports poller symbols eagerly; PEP 562 `__getattr__` lazy-loads `canary_handler` so the package can be loaded before handler.py exists (Task 1 isolation)
- `clawteam/templates/gstack/skills/canary/poller.py` — `PollResult` + `poll_window` + `evaluate_regression` + `baseline_path` + `load_baseline`; get_data_dir sourced from `clawteam.team.models`
- `clawteam/templates/gstack/skills/canary/handler.py` — `canary_handler` + `_read_deploy_notes` + `_get_browser_errors` (lazy Playwright) + `_render_canary_report_yaml` + `_write_canary_report`
- `tests/templates/gstack/skills/test_canary.py` — 21 tests (11 poller + 10 handler/plugin)
- `clawteam/plugins/gstack_sprint_plugin.py` — added `_canary_handler` import + `/canary` SkillRegistration; docstring extended with SKILL-17 entry

## Decisions Made

- **Lazy import of `get_data_dir`**: poller.py imports from `clawteam.team.models` first (canonical Phase 3 substrate) with fallbacks to `paths.py`, `utils.py`, and finally `Path.home() / ".clawteam"` so the poller remains importable in minimal test environments that may not have the full team substrate available.
- **Transport errors coerced to status 599 inside `_default_http_fn`**: callers count as 5xx, so the poll loop never has to catch exceptions and the test harness can inject a fake `http_fn` that raises `URLError` without breaking loop semantics (T-05-08-01).
- **Guaranteed first sample**: `poll_window` always makes at least one HTTP call before the monotonic deadline check so adversarial-short windows (D-15) produce a non-empty `PollResult` that `evaluate_regression` can reason about.
- **Literal regression flag strings**: Downstream consumers (Phase 7 aggregator, UI surfaces) grep on the literal string `"5xx_rate>1%"` / `"response_time>2x_baseline"` / `"js_console_error"` so the flag vocabulary is a grep-friendly API — no enum type to keep in sync across the stack.
- **PEP 562 `__getattr__` in `__init__.py`**: Lazy-load `canary_handler` so Task 1 could commit a green test suite *before* `handler.py` existed. Avoids the Task-1-imports-handler coupling and mirrors the same pattern used by `document_release/__init__.py` (per Plan 05-07 summary).
- **Bus emit wrapped in try/except**: Per T-05-08-02 philosophy extended to the event-surface layer, regression events are advisory-only and the handler must never fail because of a broken bus. The handler still returns `canary_status='regression'` + `regression_flags=[...]` so callers know to treat it as a regression even if the event surface is down.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `test_handler_role_gated` wrong SkillDispatcher signature**
- **Found during:** Task 2 GREEN verification run
- **Issue:** The plan's suggested test body constructed `SkillDispatcher([reg])` and called `dispatcher.dispatch("/canary", role="engineer", ctx=None, args={})` — but `SkillDispatcher.__init__` takes a `Mapping[str, SkillRegistration]` and `dispatch(ctx, *, skill_name, role, args)` keyword-only. The original test raised `TypeError: cannot convert dictionary update sequence element #0 to a sequence`.
- **Fix:** Rewrote the test to use `SkillDispatcher({"/canary": reg})` and `dispatcher.dispatch(None, skill_name="/canary", role="engineer", args={})`.
- **Files modified:** `tests/templates/gstack/skills/test_canary.py`
- **Verification:** Test now passes; still asserts `SkillNotPermitted` raised for `role='engineer'`.
- **Committed in:** `6c4b3d1` (Task 2 commit — rolled in alongside the handler landing)

**2. [Rule 3 - Blocking] Cross-executor stash from parallel Plan 05-09 rewrote `contribute_skills`**
- **Found during:** Task 2 GREEN plugin-registration verification
- **Issue:** Recurrence of the documented cross-executor stash pattern (Plan 04-10 Task 3 / Plan 05-03 / Plan 05-06): parallel Plan 05-09 executor committed `_benchmark_handler` import + `/benchmark` `SkillRegistration` on top of my in-progress edits, which overwrote my `/canary` registration and `_canary_handler` import. `test_registered_in_plugin` failed with `len(matches) == 0`.
- **Fix:** Re-inserted the `_canary_handler` import (after the `_benchmark_handler` import) and the `/canary` `SkillRegistration` (between `/document-release` and `/benchmark`) preserving the "Plan 05-08" / "Plan 05-09" comment ordering. Docstring extended with the `/canary` entry.
- **Files modified:** `clawteam/plugins/gstack_sprint_plugin.py`
- **Verification:** `test_registered_in_plugin` + full 129-test skill/plugin/events regression suite both green.
- **Committed in:** `6c4b3d1` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug fix in test harness, 1 cross-executor stash resolution).
**Impact on plan:** No scope change. Both fixes were discovered + applied in-cycle during Task 2 GREEN; final plugin surface matches the plan's specification exactly (7 skills: /codex + /ship + /setup-deploy + /land-and-deploy + /document-release + /canary + /benchmark).

## Issues Encountered

- **Parallel-wave stash pattern (4th recurrence)**: Plan 05-09 executed in parallel and its `contribute_skills` return-statement edit overwrote my in-progress /canary entry. Now a reliably-reproducible pattern — future wave-parallel plans should expect to re-apply plugin registrations during post-test verification. Mitigation strategies (worktree isolation, incremental-edit per-skill pattern) remain deferred.

## Acceptance Criteria

All plan acceptance criteria verified:

- `grep -q "def poll_window" clawteam/templates/gstack/skills/canary/poller.py` → **PASS**
- `grep -q "def evaluate_regression" clawteam/templates/gstack/skills/canary/poller.py` → **PASS**
- `grep -q "def baseline_path" clawteam/templates/gstack/skills/canary/poller.py` → **PASS**
- `grep -E "^(from playwright|import playwright)" clawteam/templates/gstack/skills/canary/poller.py` → **PASS (empty)**
- `grep -q "def canary_handler" clawteam/templates/gstack/skills/canary/handler.py` → **PASS**
- `grep -q 'name="/canary"' clawteam/plugins/gstack_sprint_plugin.py` → **PASS**
- `grep -q "DeployRegressionDetected" clawteam/templates/gstack/skills/canary/handler.py` → **PASS (4 matches)**
- `grep -E "^(from playwright|import playwright)" clawteam/templates/gstack/skills/canary/handler.py` → **PASS (empty; AST test redundantly locks this)**
- 21/21 canary tests pass
- 161/161 tests pass across canary + skill + plugin + events Phase 5 regression scope

## User Setup Required

None — `/canary` is stdlib-urllib baseline with no required external tools. Playwright is optional (lazy-imported when `args['browser']=True`) and gracefully degrades to empty browser-errors list when not installed.

## Next Phase Readiness

- **SKILL-17 closed.** `/canary` is registered and invokable via the `SkillDispatcher` for any agent with role=sre.
- **Plan 05-09 (/benchmark) parallel sibling** — already landed in the concurrent wave. The baseline-JSON contract at `~/.clawteam/teams/<team>/baselines/<provider>.json` with `avg_response_ms` key is now consumed by /canary's `load_baseline`.
- **Phase 7 aggregator** — `DeployRegressionDetected` event is registered on the bus (via Plan 05-02); the future `clawteam attend --summary` digest will treat it uniformly with `WebVitalRegressionDetected`.
- **Plugin surface**: Wave 4 of Phase 5 is now 7 skills deep. Remaining Phase 5 plans (05-10 /rollback, 05-11 /sre-review per ROADMAP) will additively append.

## Self-Check: PASSED

- `clawteam/templates/gstack/skills/canary/__init__.py` — **FOUND**
- `clawteam/templates/gstack/skills/canary/poller.py` — **FOUND**
- `clawteam/templates/gstack/skills/canary/handler.py` — **FOUND**
- `tests/templates/gstack/skills/test_canary.py` — **FOUND**
- Commit `c131014` (test RED) — **FOUND in git log**
- Commit `756e596` (Task 1 feat) — **FOUND in git log**
- Commit `6c4b3d1` (Task 2 feat) — **FOUND in git log**

---
*Phase: 05-tool-heavy-skills-ship-sre-codex*
*Completed: 2026-04-21*
