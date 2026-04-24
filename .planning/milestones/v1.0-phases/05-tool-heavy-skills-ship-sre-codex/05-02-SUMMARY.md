---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 02
subsystem: evidence-schemas
tags:
  - pydantic-schemas
  - events
  - plugin-contribution
  - evidence-gate
  - harness-event
  - artifact-discriminator

# Dependency graph
requires:
  - phase: 02-sprint-engine-and-preventions
    provides: EvidenceSchemaRegistry (register_schema + get_schema) with duplicate-key ValueError + HarnessEvent base + EventBus.register_event_type pattern.
  - phase: 03-gstack-team-methodology-port
    provides: GstackSprintPlugin canonical 6-schema wiring (design-doc/plan-doc/test-report/review-report/ship-notes/retro) + Phase 3 ShipNotes shape (deploy_url/ship_step/pr_url/notes/sprint_id/created_at).
  - phase: 04-interactive-routing-verification
    provides: MidReviewThrash / SycophancyCascadeDetected HarnessEvent precedent at clawteam/events/types.py.
  - phase: 05-tool-heavy-skills-ship-sre-codex
    provides: Plan 05-01 wave-0 substrate (skill dispatch + TemplateDef sub-blocks) — 05-02 is the wave-1 artifact/event substrate riding on top.
provides:
  - 4 new pydantic evidence schemas (DeployNotes, CanaryReport, BenchmarkReport, CodexReview) registered via GstackSprintPlugin
  - ShipNotes Phase 5 optional fields (ship_status / steps_completed / coverage / coverage_threshold / failure_step / failure_reason / branch / auto_invoked_skills)
  - 2 new HarnessEvent dataclasses (DeployRegressionDetected, WebVitalRegressionDetected) auto-registered on import
  - GstackSprintPlugin.contribute_evidence_schemas extended from 6 to 10 keys
affects:
  - 05-03 (CodexReview used by /codex skill handler)
  - 05-04 (ShipNotes Phase 5 fields used by /ship handler)
  - 05-06 (DeployNotes used by /land-and-deploy handler)
  - 05-08 (CanaryReport + DeployRegressionDetected used by /canary handler)
  - 05-09 (BenchmarkReport + WebVitalRegressionDetected used by /benchmark handler)
  - 07-* (cross-sprint attend --summary aggregator consumes regression events)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Literal[] artifact_type discriminator (per-schema anchor for EvidenceGate dispatch)"
    - "Phase 5 optional-field strict-additive extension on ShipNotes preserves Phase 3 BC"
    - "register_event_type(NewEventClass) at module import via late import trick to break bus<->types circular dep"
    - "Dedicated Plan 05-02 section comment inside contribute_evidence_schemas to mark Phase 3 vs Phase 5 artifact boundary"

key-files:
  created:
    - clawteam/templates/gstack/schemas/deploy_notes.py
    - clawteam/templates/gstack/schemas/canary_report.py
    - clawteam/templates/gstack/schemas/benchmark_report.py
    - clawteam/templates/gstack/schemas/codex_review.py
    - tests/test_ship_notes_phase5_fields.py
    - tests/test_event_types_phase5.py
    - tests/test_evidence_schemas_phase5.py
  modified:
    - clawteam/templates/gstack/schemas/__init__.py
    - clawteam/templates/gstack/schemas/ship_notes.py
    - clawteam/events/types.py
    - clawteam/plugins/gstack_sprint_plugin.py
    - tests/test_gstack_plugin.py

key-decisions:
  - "DeployNotes.provider Literal enum is ['vercel','netlify','fly','custom'] — matches TemplateDef.deploy.provider from Plan 05-01 for type-level consistency across the deploy pipeline."
  - "BenchmarkReport lcp_ms/fid_ms/cls_score are Optional[float] (None allowed) to accommodate D-15 adversarial partial-Lighthouse-JSON and D-10 curl-fallback modes; ttfb_ms/dom_loaded_ms remain required (curl can always provide them)."
  - "CodexReview is the minimal shape per 05-RESEARCH §Wave 2 scope (artifact_type / mode / target / verdict / summary + sprint envelope fields). No reviewer roster / no structured findings — that ships in /codex Plan 05-03 if needed."
  - "ShipNotes Phase 5 fields are ALL optional with defaults so the Phase 3 shape (deploy_url / ship_step / notes / sprint_id / created_at) still validates unchanged. Phase 3 BC test in tests/test_gstack_plugin.py (test_six_schemas_registered) relaxed to issubset — full 10-key surface locked in tests/test_evidence_schemas_phase5.py."
  - "HarnessEvent dataclass field defaults follow MidReviewThrash precedent (empty string / 0.0 / empty list via field(default_factory=list)) so callers can pass only team_name kwarg at construct time."
  - "register_event_type() calls for DeployRegressionDetected + WebVitalRegressionDetected live at the bottom of clawteam/events/types.py after a late `from clawteam.events.bus import register_event_type` to avoid the bus<->types circular dep (same pattern Phase 4 established for MidReviewThrash)."
  - "Test files landed at tests/ top-level (test_event_types_phase5.py / test_evidence_schemas_phase5.py / test_ship_notes_phase5_fields.py) rather than plan-specified tests/events/ / tests/harness/ / tests/templates/gstack/schemas/ subdirs because the project's existing convention is a flat tests/ tree (test_event_types_phase2.py / test_event_types_phase4.py already exist at top level). Same test coverage, idiomatic path."

patterns-established:
  - "Wave 1 substrate plan shape: combine all per-skill schemas + events into one cohesive plugin edit so Waves 2-4 per-skill plans only touch handler code (not plugin / not types.py). Consolidation prevents contribute_evidence_schemas from being touched by every skill plan."
  - "Phase 5 optional ShipNotes fields additive pattern: new optional fields with None / empty-list defaults + unit test asserting Phase 3 minimal shape still validates (test_minimal_phase3_shape_still_valid). Template for future Ship-phase evolution."

requirements-completed: [SKILL-13, SKILL-14, SKILL-15, SKILL-17, SKILL-18]

# Metrics
duration: 80min
completed: 2026-04-21
---

# Phase 5 Plan 02: Wave-1 Artifact & Event Substrate Summary

**4 new pydantic evidence schemas (DeployNotes / CanaryReport / BenchmarkReport / CodexReview) registered via GstackSprintPlugin + ShipNotes Phase 5 optional fields + 2 HarnessEvent dataclasses (DeployRegressionDetected / WebVitalRegressionDetected) — all wire-up for Waves 2-4 skill handlers.**

## Performance

- **Duration:** ~80 min
- **Started:** 2026-04-21T20:50:07+08:00
- **Completed:** 2026-04-21T22:10:02+08:00
- **Tasks:** 3 (each TDD RED+GREEN)
- **Files created:** 7 (4 schemas + 3 test modules)
- **Files modified:** 5 (2 schema module wiring + 1 events module + 1 plugin + 1 BC-anchor test)

## Accomplishments

- **4 new pydantic evidence schemas** under `clawteam/templates/gstack/schemas/` — each with `artifact_type: Literal[...]` discriminator + stub-defeating `Field(min_length=...)` / `ge=...` constraints mirroring the Phase 3 pattern.
- **ShipNotes Phase 5 extension** — 8 new optional fields (ship_status / steps_completed / coverage / coverage_threshold / failure_step / failure_reason / branch / auto_invoked_skills) with backward-compatible defaults; Phase 3 callers unchanged.
- **2 new HarnessEvent dataclasses** in `clawteam/events/types.py` — auto-registered on module import via late-imported `register_event_type`, emit + subscribe round-trip through EventBus.
- **GstackSprintPlugin.contribute_evidence_schemas extended** from 6 keys to 10 keys; 18 new tests across 3 test modules; Phase 3 BC anchor test relaxed to issubset.
- **Zero skill handler code written** — handlers arrive in Waves 2-4 (Plans 05-03 through 05-09). This plan is pure substrate.

## Task Commits

Each task followed TDD RED → GREEN discipline:

### Task 1: Four new pydantic schemas + ShipNotes Phase 5 extension
1. **RED:** `63fcfe5` - test(05-02): add failing tests for ShipNotes Phase 5 field additions
2. **GREEN:** `ca7ab3d` - feat(05-02): add DeployNotes/CanaryReport/BenchmarkReport/CodexReview schemas + ShipNotes Phase 5 fields

### Task 2: Two new HarnessEvent dataclasses + EventBus registration
3. **RED:** `3d2bcee` - test(05-02): add failing tests for Phase 5 regression events
4. **GREEN:** `210a9f8` - feat(05-02): add DeployRegressionDetected + WebVitalRegressionDetected events

### Task 3: Wire 4 new schemas into GstackSprintPlugin
5. **RED:** `7aee97b` - test(05-02): add failing tests for GstackSprintPlugin 10-schema wiring
6. **GREEN:** `b6b1a9c` - feat(05-02): wire 4 Phase 5 schemas into GstackSprintPlugin (Task 3)

**Plan metadata commit:** (to be made after SUMMARY.md land)

## Files Created / Modified

### Schemas (clawteam/templates/gstack/schemas/)
- `deploy_notes.py` — **NEW** — DeployNotes pydantic schema for `/land-and-deploy` artifact (SKILL-15). `deploy_url ≥1 char`, `commit_sha ≥7 ≤40 chars`, `provider` is Literal['vercel','netlify','fly','custom'].
- `canary_report.py` — **NEW** — CanaryReport pydantic schema for `/canary` artifact (SKILL-17). Tracks http_2xx_count / http_5xx_count / avg_response_ms / pre_deploy_avg_response_ms / js_console_errors / regression_flags.
- `benchmark_report.py` — **NEW** — BenchmarkReport pydantic schema for `/benchmark` artifact (SKILL-18). Optional Lighthouse fields (lcp_ms / fid_ms / cls_score) accommodate D-15 adversarial partial-Lighthouse-JSON; ttfb_ms / dom_loaded_ms required.
- `codex_review.py` — **NEW** — CodexReview pydantic schema for `/codex` artifact (SKILL-13). Minimal shape per 05-RESEARCH — mode Literal['review','adversarial','consultation'] + verdict Literal['pass','fail','n/a'].
- `ship_notes.py` — **MODIFIED** — appended 8 Phase 5 optional fields (ship_status / steps_completed / coverage / coverage_threshold / failure_step / failure_reason / branch / auto_invoked_skills) after the Phase 3 required fields, all default to None / empty list so Phase 3 callers validate unchanged.
- `__init__.py` — **MODIFIED** — import + `__all__` entries for 4 new schemas, marked `# Phase 5 Plan 05-02:` section.

### Events (clawteam/events/)
- `types.py` — **MODIFIED** — appended DeployRegressionDetected + WebVitalRegressionDetected dataclasses after SycophancyCascadeDetected (Phase 4), plus matching `register_event_type(...)` calls at module bottom. Used existing late `from clawteam.events.bus import register_event_type` import (already present for Phase 4 events).

### Plugin wiring (clawteam/plugins/)
- `gstack_sprint_plugin.py` — **MODIFIED** — extended `contribute_evidence_schemas` return dict from 6 keys to 10 keys (added deploy-notes / canary-report / benchmark-report / codex-review rows); added 4 new imports from `clawteam.templates.gstack.schemas`; docstring calls out the Phase 3 → Phase 5 boundary.

### Tests (tests/)
- `test_ship_notes_phase5_fields.py` — **NEW** — 4 tests: Phase 3 minimal shape validates, Phase 5 fields optional + round-trip through model_dump, ship_status Literal enforced, coverage range validated.
- `test_event_types_phase5.py` — **NEW** — 7 tests: both events are HarnessEvent subclasses, default constructors work, EventBus.emit + subscribe round-trip, register_event_type fired on import.
- `test_evidence_schemas_phase5.py` — **NEW** — 7 tests: contribute_evidence_schemas returns exactly 10 keys, PluginManager registration flows all 10 without duplicate ValueError, per-schema round-trip via registry lookup, Phase 3 non-regression guard.
- `test_gstack_plugin.py` — **MODIFIED** — relaxed `test_six_schemas_registered` from exact equality to `issubset` check so it coexists with the new 10-key surface (full 10-key lock in tests/test_evidence_schemas_phase5.py). Docstring calls out the Phase 3 BC anchor role.

## Decisions Made

See frontmatter `key-decisions`. Highlights:

- **DeployNotes.provider enum matches TemplateDef.deploy.provider** (Literal['vercel','netlify','fly','custom']) so the deploy pipeline is type-level consistent from config to artifact.
- **BenchmarkReport Optional Core Web Vitals** — `lcp_ms`, `fid_ms`, `cls_score` are `float | None` to support both D-10 curl-fallback mode and D-15 adversarial partial-Lighthouse JSON. `ttfb_ms` + `dom_loaded_ms` stay required (curl always provides them).
- **CodexReview minimal shape** — per 05-RESEARCH §Wave 2 Plan 05-03 scope note. Deliberately no reviewer roster / no structured findings — /codex handler in Plan 05-03 can extend the schema additively if needed.
- **ShipNotes Phase 5 fields are ALL optional** — defaults chosen so Phase 3 tests pass unchanged. `test_minimal_phase3_shape_still_valid` explicitly locks this.
- **Test files at tests/ flat** — project convention already has test_event_types_phase2.py / test_event_types_phase4.py at the flat tests/ root; Plan's suggested tests/events/ / tests/harness/ / tests/templates/gstack/schemas/ subdirs would have been inconsistent.
- **BC-anchor test relaxed to issubset** — `tests/test_gstack_plugin.py::test_six_schemas_registered` used to assert exact 6-key equality. Relaxed to `phase3_expected.issubset(set(schemas.keys()))` so it passes with the 10-key dict; full 10-key surface asserted in the Phase-5-scoped test module.

## Deviations from Plan

None requiring Rule 1/2/3/4 escalation.

Minor path/naming adjustments (none material — same test coverage):

**1. [Conventional path] Test file locations use flat tests/ tree instead of tests/events/ + tests/harness/ + tests/templates/gstack/schemas/ subdirs**
- **Reason:** Project already has test_event_types_phase2.py and test_event_types_phase4.py at the flat tests/ root; the plan-suggested subdirs do not exist in this repository. Flat placement matches existing convention.
- **Result:** Test module names are `tests/test_event_types_phase5.py`, `tests/test_evidence_schemas_phase5.py`, `tests/test_ship_notes_phase5_fields.py`. All plan-scoped 18 tests present and passing.

**2. [BC-anchor test relaxation] tests/test_gstack_plugin.py::test_six_schemas_registered moved from exact-equality to issubset check**
- **Rationale:** Plan called for the Phase-5 schema set to expand the dict from 6 to 10 keys. The existing Phase-3 BC test asserted exact 6-key equality; relaxing to `phase3_expected.issubset(...)` is the minimal change that lets both the Phase 3 non-regression intent and the Phase 5 expanded dict coexist. Full 10-key surface is asserted in `tests/test_evidence_schemas_phase5.py` (Plan 05-02 Task 3's own 7-test surface).

**Total deviations:** 0 auto-fixes needed. Plan executed as written.
**Impact:** None — substrate plan landed cleanly; all 3 Tasks' acceptance criteria met.

## Issues Encountered

### Pre-existing test isolation issue (already deferred in Plan 05-01)

When running the full tests/ tree alongside tests/test_evidence_schemas_phase5.py, 6 of the 7 new tests fail with `ValueError: Duplicate evidence-schema registration: 'design-doc'`. This is the **pre-existing test-cross-contamination issue logged in deferred-items.md for Plan 05-01** — `clawteam.harness.evidence_schemas._registry` is a process-global dict and other test modules don't reset it.

**Evidence this is pre-existing, not caused by 05-02:**
- Plan 05-02 tests all pass when run alone: `.venv/bin/pytest tests/test_evidence_schemas_phase5.py -q` → 7 passed.
- The test module's own setup_function / teardown_function calls `reset_schema_registry()` + `reset_phase_registry()` — isolation works for its own tests.
- Same failure mode documented on commit `ed8c32a` (before Plan 05-01 started) at `.planning/phases/05-tool-heavy-skills-ship-sre-codex/deferred-items.md`.

**Not fixed here:** Out of scope per Plan 05-02 (Rule on deviations — only auto-fix issues directly caused by the current plan's changes). Queued for the proposed Phase 5 Wave 4 "harness hygiene" plan as noted in deferred-items.md.

**Verification workaround:** Plan-scoped verification commands run isolated test files:
- `.venv/bin/pytest tests/test_evidence_schemas_phase5.py -q` → 7 passed ✓
- `.venv/bin/pytest tests/test_event_types_phase5.py -q` → 7 passed ✓
- `.venv/bin/pytest tests/test_ship_notes_phase5_fields.py -q` → 4 passed ✓
- `.venv/bin/pytest tests/test_gstack_plugin.py tests/test_plugins.py -q` → 34 passed ✓ (BC green)
- `.venv/bin/pytest tests/test_event_bus.py tests/test_event_types_phase2.py tests/test_event_types_phase4.py -q` → 33 passed ✓ (BC green)
- `.venv/bin/python -c "…; assert len(schemas) == 10; print('10 schemas OK')"` → `10 schemas OK` ✓

## Threat Flags

None. All new artifact schemas + events are in-process substrate with no new network surface. The pydantic `Literal[...]` discriminators + `Field(min_length=...)` / `ge=...` constraints are Task-1-level mitigations for T-05-02-01 (malformed artifact bypasses EvidenceGate) and the plugin's duplicate-key ValueError is the existing Phase 2 Task-3-level mitigation for T-05-02-02 (duplicate schema key). Threat register dispositions match.

## User Setup Required

None — no external service configuration required. The new schemas + events are pure in-process substrate consumed by Wave 2-4 skill handlers in later plans.

## Next Phase Readiness

- **Wave 2 (Plan 05-03 /codex)** ready to pick up CodexReview schema + write handler.
- **Wave 2 (Plan 05-04 /ship)** ready to pick up ShipNotes Phase 5 optional fields.
- **Wave 3 (Plan 05-06 /land-and-deploy)** ready to pick up DeployNotes schema.
- **Wave 4 (Plan 05-08 /canary)** ready to pick up CanaryReport schema + DeployRegressionDetected event.
- **Wave 4 (Plan 05-09 /benchmark)** ready to pick up BenchmarkReport schema + WebVitalRegressionDetected event.

No blockers. Phase 5 wave-1 substrate is complete; wave-2 can begin immediately.

## Self-Check: PASSED

**Files verified to exist on disk:**
- `clawteam/templates/gstack/schemas/deploy_notes.py` — FOUND (27 LOC, class DeployNotes)
- `clawteam/templates/gstack/schemas/canary_report.py` — FOUND (31 LOC, class CanaryReport)
- `clawteam/templates/gstack/schemas/benchmark_report.py` — FOUND (29 LOC, class BenchmarkReport)
- `clawteam/templates/gstack/schemas/codex_review.py` — FOUND (26 LOC, class CodexReview)
- `clawteam/templates/gstack/schemas/ship_notes.py` — FOUND (8 Phase 5 fields appended at line 49+)
- `clawteam/templates/gstack/schemas/__init__.py` — FOUND (4 Phase 5 imports + __all__ entries)
- `clawteam/events/types.py` — FOUND (DeployRegressionDetected @ line 330, WebVitalRegressionDetected @ line 353, register_event_type calls @ 377-378)
- `clawteam/plugins/gstack_sprint_plugin.py` — FOUND (4 Phase 5 schema imports + 4 dict entries)
- `tests/test_ship_notes_phase5_fields.py` — FOUND
- `tests/test_event_types_phase5.py` — FOUND
- `tests/test_evidence_schemas_phase5.py` — FOUND
- `tests/test_gstack_plugin.py` — FOUND (modified, issubset BC anchor)

**Commits verified to exist in git log:**
- `63fcfe5` — FOUND (test: Task 1 RED)
- `ca7ab3d` — FOUND (feat: Task 1 GREEN)
- `3d2bcee` — FOUND (test: Task 2 RED)
- `210a9f8` — FOUND (feat: Task 2 GREEN)
- `7aee97b` — FOUND (test: Task 3 RED)
- `b6b1a9c` — FOUND (feat: Task 3 GREEN)

**Verification commands run + passed:**
- `pytest tests/test_evidence_schemas_phase5.py tests/test_event_types_phase5.py tests/test_ship_notes_phase5_fields.py -q` → 18 passed ✓
- `python -c "… len(schemas) == 10 …"` → 10 schemas OK ✓

## TDD Gate Compliance

Plan 05-02 has `type: execute` (not plan-level `type: tdd`), but each of the 3 Tasks declares `tdd="true"`. Gate sequence validated:
- **Task 1:** RED commit `63fcfe5` (test) → GREEN commit `ca7ab3d` (feat) ✓
- **Task 2:** RED commit `3d2bcee` (test) → GREEN commit `210a9f8` (feat) ✓
- **Task 3:** RED commit `7aee97b` (test) → GREEN commit `b6b1a9c` (feat) ✓

All 3 tasks followed strict RED-then-GREEN TDD discipline. No REFACTOR commits needed (schemas + event dataclasses + dict-entry extension are all minimal additions).

---
*Phase: 05-tool-heavy-skills-ship-sre-codex*
*Plan: 02 (Wave 1 — schemas + events)*
*Completed: 2026-04-21*
