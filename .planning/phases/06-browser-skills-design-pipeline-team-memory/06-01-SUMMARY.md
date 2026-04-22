---
phase: 06-browser-skills-design-pipeline-team-memory
plan: 01
subsystem: substrate
tags:
  - pyproject-optional-extra
  - feature-detection
  - event-registration
  - pydantic-subblocks
  - template-config

# Dependency graph
requires:
  - phase: 05-tool-heavy-skills-ship-sre-codex
    provides: "HarnessEvent late-import register_event_type pattern + TemplateDef optional top-level sub-block precedent ([ship]/[deploy]/[canary]/[benchmark])"
  - phase: 03-gstack-team-template-methodology-port
    provides: "TemplateDef strict-additive field convention + [template.memory] legacy TOML key (now routed to renamed memory_layout field)"
provides:
  - "[browser] optional pyproject extra (playwright>=1.58,<2)"
  - "clawteam.browser.playwright_available() feature-detection helper (D-02 no-top-level-import)"
  - "clawteam.memory package skeleton (public API fills in Plans 06-02/03/10/11)"
  - "3 new HarnessEvents registered on import: MemoryWritePersisted, ConflictDetected, MemoryBackfillComplete"
  - "3 new TemplateDef sub-block models: MemoryConfig, DesignShotgunConfig, BrowserConfig (all optional, default None)"
  - "Phase 3 TemplateDef.memory dict field renamed to .memory_layout (legacy [template.memory] TOML key preserved via _parse_toml fallback)"
affects:
  - 06-02 (TeamMemoryStore — consumes MemoryWritePersisted + ConflictDetected + MemoryConfig)
  - 06-03 (/learn skill — consumes MemoryBackfillComplete + MemoryConfig)
  - 06-04 (browser adapter — consumes playwright_available + BrowserConfig)
  - 06-05/06/07 (/browse, /open-gstack-browser, /setup-browser-cookies — consume BrowserConfig + playwright_available)
  - 06-08/09 (/design-shotgun + /design-html — consume DesignShotgunConfig)
  - 06-10/11 (integration + backfill — consumes all three events + MemoryConfig retention TTLs)

# Tech tracking
tech-stack:
  added:
    - "playwright>=1.58,<2 (declared as optional extra — not installed by this plan)"
  patterns:
    - "Feature-detection helper at package __init__ using importlib.util.find_spec (no top-level import of the optional dep)"
    - "Late-import register_event_type at module bottom to break bus<->types circular dependency (Phase 4/5 precedent, extended)"
    - "Pydantic Literal + Field(ge/le) for enum + range validation at TOML parse time"
    - "TemplateDef field rename with _parse_toml fallback on legacy TOML key for backward compatibility"

key-files:
  created:
    - "clawteam/browser/__init__.py — playwright_available() helper"
    - "clawteam/memory/__init__.py — Wave 0 package marker (empty __all__)"
    - "tests/browser/__init__.py — test package marker"
    - "tests/browser/test_feature_detection.py — 4 tests incl. D-02 no-top-level-import guard"
    - "tests/test_pyproject_optional_extras.py — 2 tests (browser extra present + dev/p2p unchanged)"
    - "tests/test_event_types_phase6.py — 9 tests mirroring Phase 5 precedent"
    - "tests/test_template_def_phase6_blocks.py — 17 tests incl. BC over 6 packaged templates + validation range/Literal enforcement"
  modified:
    - "pyproject.toml — append [browser] optional-dependency"
    - "clawteam/events/types.py — 3 new dataclass events + 3 register_event_type calls"
    - "clawteam/templates/__init__.py — 3 new pydantic sub-block models (MemoryConfig/DesignShotgunConfig/BrowserConfig), 3 new TemplateDef fields, _parse_toml reads top-level [memory]/[design_shotgun]/[browser]; Phase 3 `memory` dict field renamed to `memory_layout`"
    - "tests/test_gstack_template.py — updated test_memory_block_declared to use memory_layout"
    - "tests/test_templates.py — updated 3 assertions to use memory_layout and verify memory is None"

key-decisions:
  - "[D-01] Phase 3 TemplateDef.memory dict renamed to memory_layout (Rule 3 deviation): field-name collision with new Phase 6 MemoryConfig sub-block. _parse_toml reads legacy [template.memory] TOML key for BC; no production code consumed the dict field, so the rename is test-only impact."
  - "[D-02] playwright_available() uses importlib.util.find_spec imported at module top (not sys.modules hack) so tests monkeypatch a single symbol on clawteam.browser to disable Playwright for all callers."
  - "[D-03] test_no_toplevel_import evicts both 'playwright' and 'clawteam.browser' from sys.modules before reimporting, then importlib.reload()s clawteam.browser — belt-and-braces audit that the module body never runs a top-level 'import playwright'."
  - "[D-04] MemoryConfig.conflict_threshold defaults to 0.75 (matches Plan 06-01 threat-model fixture); tests use 0.5 + 0.8 + 0.65 non-default values + boundary (1.5) to exercise ValidationError path."
  - "[D-05] DesignShotgunConfig.variant_count bounded [1, 32] — the upper cap prevents runaway token spend at /design-shotgun run time (not explicit in plan action block; inferred from pydantic Field(le=32))."
  - "[D-06] register_event_type late-import at module bottom follows the Phase 4/5 circular-import prevention precedent (bus.py imports HarnessEvent from types.py at top level)."

patterns-established:
  - "Optional-dep feature detection pattern: `from importlib.util import find_spec` at module top; helper returns `find_spec('<pkg>') is not None`. No `import <pkg>` anywhere in the module body. Skill modules route tool_available probes through this single helper."
  - "Field-rename BC pattern: rename the Python field but keep the original TOML key; _parse_toml reads the legacy key first, new key as fallback. Zero production churn if the field had no external consumers."

requirements-completed: []  # Plan 06-01 ships SUBSTRATE ONLY (zero skill implementations per plan objective); requirements MEM-01/MEM-02/SKILL-10/SKILL-11/SKILL-12/QUALITY-10 listed in plan frontmatter remain Pending in REQUIREMENTS.md until Plans 06-02/04/05/06/07/08/09 land actual /browse, /design-shotgun, /design-html, TeamMemoryStore, and /learn implementations.
requirements-substrate:  # Pre-requisites landed for these downstream requirements:
  - MEM-01-substrate  # clawteam.memory package + MemoryConfig retention TTLs
  - MEM-02-substrate  # MemoryWritePersisted + ConflictDetected + MemoryBackfillComplete events
  - SKILL-10-substrate  # [browser] pyproject extra + playwright_available() + BrowserConfig
  - SKILL-11-substrate  # DesignShotgunConfig (variant_count + board_format)
  - SKILL-12-substrate  # (no net-new surface; consumes Phase 3 template infra)
  - QUALITY-10-substrate  # MemoryConfig.conflict_threshold + ConflictDetected event

# Metrics
duration: 12min
completed: 2026-04-22
---

# Phase 6 Plan 01: Wave 0 Substrate Summary

**One pyproject [browser] optional extra, playwright_available() feature detector, 2 new top-level packages (clawteam.browser + clawteam.memory), 3 new HarnessEvents (MemoryWritePersisted + ConflictDetected + MemoryBackfillComplete) registered on import, and 3 new TemplateDef sub-block models (MemoryConfig + DesignShotgunConfig + BrowserConfig) — closes A1/A3/A7 plan-prep items for Phase 6 Waves 1-5.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-04-22T10:50:12Z
- **Completed:** 2026-04-22T11:02:00Z (approx)
- **Tasks:** 3 (all TDD — 6 commits total: RED + GREEN per task)
- **Files modified:** 10 (3 source + 7 tests, minus 2 pre-existing tests touched for Phase 3 field rename)

## Accomplishments

- **Task 1:** `pyproject.toml` now declares `browser = ["playwright>=1.58,<2"]` optional extra; `clawteam.browser.playwright_available()` exported — D-02 invariant proven (import of clawteam.browser leaves `sys.modules` without `playwright`).
- **Task 2:** `clawteam.memory` package marker + 3 new HarnessEvents auto-registered; Phase 6 Waves 1/3/4 can import the types without touching the event bus.
- **Task 3:** `TemplateDef` carries all 7 phase-level sub-blocks (Phase 5's ship/deploy/canary/benchmark + Phase 6's memory/design_shotgun/browser); gstack + 6 packaged templates parse unchanged; pydantic Literal + ge/le constraints enforce threat-model invariants T-06-01-01..03 at parse time.

## Task Commits

Each task committed atomically in TDD RED → GREEN order:

1. **Task 1 RED (6 tests failing):** `6b0d018` — test(06-01): add failing tests for pyproject [browser] extra + playwright_available
2. **Task 1 GREEN (6/6 passing):** `71f435b` — feat(06-01): add [browser] optional extra + clawteam.browser.playwright_available()
3. **Task 2 RED (9 tests failing):** `603e2ba` — test(06-01): add failing tests for 3 Phase 6 events + clawteam.memory package
4. **Task 2 GREEN (9/9 passing):** `5a8b355` — feat(06-01): add 3 Phase 6 memory events + clawteam.memory package marker
5. **Task 3 RED (17 tests failing):** `4917837` — test(06-01): add failing tests for TemplateDef Phase 6 sub-blocks
6. **Task 3 GREEN (17/17 passing):** `2bf8adb` — feat(06-01): add [memory]+[design_shotgun]+[browser] TemplateDef sub-blocks

**Plan metadata commit:** (to follow) — docs(06-01): complete wave0 plan-prep

## Files Created/Modified

### Source (new)
- `clawteam/browser/__init__.py` — `playwright_available()` via `importlib.util.find_spec` (32 LOC); no top-level import of playwright
- `clawteam/memory/__init__.py` — Wave 0 package marker, `__all__ = []` (public API arrives in Plans 06-02/03/10/11)

### Source (modified)
- `pyproject.toml` — append `browser = ["playwright>=1.58,<2"]` below existing `p2p` extra (4 lines added; `dev` + `p2p` untouched)
- `clawteam/events/types.py` — append 3 dataclasses (MemoryWritePersisted/ConflictDetected/MemoryBackfillComplete) before the existing Phase 5 late-import block + 3 register_event_type calls after the existing ones
- `clawteam/templates/__init__.py` — 3 new pydantic models (MemoryConfig/DesignShotgunConfig/BrowserConfig) after BenchmarkConfig; 3 new TemplateDef fields; `_parse_toml` reads top-level `[memory]`/`[design_shotgun]`/`[browser]`; Phase 3 field `memory: dict` renamed to `memory_layout: dict` with legacy TOML-key fallback

### Tests (new)
- `tests/test_pyproject_optional_extras.py` (2 tests)
- `tests/browser/__init__.py` (empty package marker)
- `tests/browser/test_feature_detection.py` (4 tests)
- `tests/test_event_types_phase6.py` (9 tests — mirrors test_event_types_phase5.py shape)
- `tests/test_template_def_phase6_blocks.py` (17 tests — mirrors test_template_def_extensions.py shape)

### Tests (modified — Phase 3 field rename follow-through)
- `tests/test_gstack_template.py` — `test_memory_block_declared` now reads `tmpl.memory_layout` (was `tmpl.memory`); added docstring note pointing to the rename.
- `tests/test_templates.py` — 3 assertions updated: `assert t.memory_layout == {}` + `assert t.memory is None` for new MemoryConfig field.

## Decisions Made

- **Field-name collision resolution (Rule 3 deviation).** Phase 3 shipped `TemplateDef.memory: dict[str, str | bool]` for TeamManager per-role dir pre-creation. Phase 6 Plan 06-01's plan action block collides on this name. Rename Phase 3 field → `memory_layout` (no production code consumed it; only 2 test files + one gstack.toml TOML key which stays intact via `_parse_toml` fallback `tmpl.get("memory", tmpl.get("memory_layout", {}))`).
- **`MemoryConfig.conflict_threshold` default = 0.75** per threat-model T-06-01-01 fixture; tests exercise 0.5, 0.65, 0.8, and boundary violation (1.5).
- **`DesignShotgunConfig.variant_count` upper bound = 32** (plan action block value); mitigates runaway token spend at /design-shotgun dispatch time.
- **`BrowserConfig.cookies_dir` default `""`** encodes "derive from `<data_dir>/teams/<team>/browser/cookies/`" — empty string is deliberately chosen so downstream Plan 06-07 can distinguish "template opted out" from "template override" without needing a sentinel.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Phase 3 `TemplateDef.memory` dict field collides with new Phase 6 `MemoryConfig` sub-block field name**
- **Found during:** Task 3 implementation (first `.venv/bin/pytest` run after editing `clawteam/templates/__init__.py`).
- **Issue:** The plan specifies `tmpl.memory.conflict_threshold` as the Phase 6 API (see plan `<acceptance_criteria>` grep pattern `memory: MemoryConfig`). But Phase 3 already declared `TemplateDef.memory: dict[str, str | bool]` read from `[template.memory]` for TeamManager per-role dir pre-creation (D-05, tests in `test_gstack_template.py::test_memory_block_declared` + `test_templates.py::test_parse_toml_reads_new_template_fields_when_present`). Second declaration silently shadows the first — gstack.toml load now fails pydantic validation against MemoryConfig because it's given `{"root": "...", "per_role": true}`.
- **Fix:** Renamed Phase 3 field `memory: dict` → `memory_layout: dict` at the class level. Updated `_parse_toml` to keep reading the *legacy* TOML key `[template.memory]` but assign into `memory_layout` (fallback chain: `tmpl.get("memory", tmpl.get("memory_layout", {}))`). This preserves BC for gstack.toml (TOML key unchanged) and all downstream TeamManager callers (no production code referenced `TemplateDef.memory` directly — confirmed via `grep -rn "\.memory\b" clawteam/`). Then updated 2 Phase 3 test files (4 assertions total) to reference `memory_layout`.
- **Files modified:** `clawteam/templates/__init__.py`, `tests/test_gstack_template.py`, `tests/test_templates.py`
- **Verification:** `pytest tests/test_template_def_phase6_blocks.py tests/test_templates.py tests/test_gstack_template.py tests/test_template_def_extensions.py tests/test_template_regression_matrix.py -q` → 116/116 green. Full suite (1388/1388 relevant tests + 3 skipped) remains green.
- **Committed in:** `2bf8adb` (Task 3 GREEN commit).

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking field-name collision).
**Impact on plan:** Deviation was necessary to complete Task 3's stated goal. The plan author missed the Phase 3 `memory` field during research (Phase 5 `<interfaces>` block cited only ship/deploy/canary/benchmark precedents, not the Phase 3 dict). Rename keeps the plan's intended public API (`tmpl.memory.conflict_threshold`) while preserving BC for the 6-months-old gstack.toml TOML layout. Impact on downstream plans (06-02..06-11): zero — they will read `tmpl.memory.*` (MemoryConfig) exactly as the plan specified, and TeamManager (if ever extended to read the old dict) now references `tmpl.memory_layout`.

## Issues Encountered

- Pre-existing 9-failure cross-contamination in `test_evidence_schemas_phase5` + `test_gstack_plugin` + `test_plugin_hooks` (process-global `_registry` state from `test_gstack_template.py`) — OUT OF SCOPE for this plan per Plan 05-10 deferred-items note. Verified: all 9 pass in isolation; same 9 fail under full-suite ordering regardless of my Plan 06-01 test additions.
- Background auto-commit `fc799be docs(06): capture phase research + plans` landed between the `/gsd-execute-phase` init and my first task commit; contains the Phase 6 plan files themselves (not mine). Unrelated to Plan 06-01 execution.

## Threat Flags

None. No new network endpoints, auth paths, file-access patterns, or schema changes at trust boundaries were introduced beyond what the plan's `<threat_model>` already enumerates (T-06-01-01..05, all mitigated or accepted).

## User Setup Required

None — Phase 6 Wave 0 substrate is build-time only.

The `[browser]` optional extra is *declared* but not *installed* by this plan. Downstream:
- `pip install 'clawteam[browser]'` will pull Playwright after this commit lands.
- `playwright install chromium` is a separate user action Plan 06-04's doctor row will document.

## Next Phase Readiness

**Ready for Plan 06-02 (TeamMemoryStore substrate):**
- `clawteam.memory` importable; Plan 06-02 can add `store.py`, `entry.py` under it.
- `MemoryWritePersisted` + `ConflictDetected` resolvable via `resolve_event_type("MemoryWritePersisted")` for shell-hook subscribers.
- `MemoryConfig(conflict_threshold, retention_pattern_days, retention_incident_days)` available for TeamMemoryStore constructor injection.

**Ready for Plan 06-04 (browser adapter):**
- `from clawteam.browser import playwright_available` importable.
- `BrowserConfig(headless, timeout_seconds, cookies_dir)` available to seed adapter defaults.

**Ready for Plan 06-08 (/design-shotgun):**
- `DesignShotgunConfig(variant_count, board_format)` with `Literal["html","markdown"]` + bounds enforced at parse time.

**Ready for Plan 06-10/11 (integration + backfill):**
- `MemoryBackfillComplete` event ready for `/learn` first-invocation backfill scan emit.

## Self-Check: PASSED

- [x] `clawteam/browser/__init__.py` — FOUND
- [x] `clawteam/memory/__init__.py` — FOUND
- [x] `tests/browser/__init__.py` — FOUND
- [x] `tests/browser/test_feature_detection.py` — FOUND
- [x] `tests/test_pyproject_optional_extras.py` — FOUND
- [x] `tests/test_event_types_phase6.py` — FOUND
- [x] `tests/test_template_def_phase6_blocks.py` — FOUND
- [x] `pyproject.toml` — MODIFIED (browser extra present)
- [x] `clawteam/events/types.py` — MODIFIED (3 new dataclasses + 3 register_event_type)
- [x] `clawteam/templates/__init__.py` — MODIFIED (3 new models + 3 new fields + memory_layout rename)
- [x] Commit `6b0d018` (Task 1 RED) — FOUND
- [x] Commit `71f435b` (Task 1 GREEN) — FOUND
- [x] Commit `603e2ba` (Task 2 RED) — FOUND
- [x] Commit `5a8b355` (Task 2 GREEN) — FOUND
- [x] Commit `4917837` (Task 3 RED) — FOUND
- [x] Commit `2bf8adb` (Task 3 GREEN) — FOUND

## TDD Gate Compliance

All 3 tasks were TDD (`tdd="true"` in plan frontmatter). Gate sequence verified per task:

- Task 1: `test(06-01)` 6b0d018 → `feat(06-01)` 71f435b (RED → GREEN, no REFACTOR needed)
- Task 2: `test(06-01)` 603e2ba → `feat(06-01)` 5a8b355 (RED → GREEN, no REFACTOR needed)
- Task 3: `test(06-01)` 4917837 → `feat(06-01)` 2bf8adb (RED → GREEN, no REFACTOR needed)

Each RED commit confirmed with `pytest -x -q` exiting non-zero before its matching GREEN commit; each GREEN commit took the tests green.

---
*Phase: 06-browser-skills-design-pipeline-team-memory*
*Completed: 2026-04-22*
