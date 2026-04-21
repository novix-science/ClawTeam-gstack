---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
plan: 13
subsystem: tests
tags: [golden-tests, review-routing, state-machine, fixtures, regression-defense, parametrized]

# Dependency graph
requires:
  - phase: 04
    provides: GstackReviewRouter (Plan 06) + gstack.toml review rules (Plan 06)
  - phase: 04
    provides: OfficeHoursState _TRANSITIONS/TURN_BUDGET/_FINAL_STATES (Plan 07)
  - phase: 04
    provides: DesignConsultationState _TRANSITIONS/TURN_BUDGET/_FINAL_STATES (Plan 08)
  - phase: 04
    provides: InvestigateState _TRANSITIONS/TURN_BUDGET/_FINAL_STATES (Plan 09)
provides:
  - 8 adversarial diff fixtures under tests/fixtures/review_routing/
  - expected_routing.json oracle (canonical participants per fixture)
  - tests/test_adversarial_routing.py (12 tests: 8 parametrized + 4 meta)
  - tests/test_state_machine_goldens.py (10 tests: 3x3 parametrized + 1 meta)
affects: [04-14-d18-markers-and-runtime-stubs, upstream-upstream-pr]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fixture-driven parametrized goldens: oracle JSON keys drive pytest.mark.parametrize IDs"
    - "Diff-header path extraction via regex over `diff --git a/ b/` + rename from/to lines"
    - "Strict equality (not soft-bound) between in-code TURN_BUDGET and fixture turn_budget -- catches monologue-collapse regression with a crisp failure mode (ISS-06 revision)"
    - "Bijective triple-set comparison (code -> fixture) for transition drift detection"

key-files:
  created:
    - tests/fixtures/review_routing/renamed_ui_component.diff
    - tests/fixtures/review_routing/crypto_test_file.diff
    - tests/fixtures/review_routing/whitespace_only.diff
    - tests/fixtures/review_routing/package_json_dep_bump.diff
    - tests/fixtures/review_routing/auth_middleware_rewrite.diff
    - tests/fixtures/review_routing/cross_cutting_refactor.diff
    - tests/fixtures/review_routing/mixed_ui_and_api.diff
    - tests/fixtures/review_routing/generated_migration.diff
    - tests/fixtures/review_routing/expected_routing.json
    - tests/test_adversarial_routing.py
    - tests/test_state_machine_goldens.py
  modified:
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/deferred-items.md

key-decisions:
  - "8 fixture keys in expected_routing.json use the exact set specified by the plan's must_haves.truths -- keys drive parametrize IDs, changing them is a breaking rename"
  - "ISS-06 tightening applied: soft-bound test_monologue_collapse_detector removed; replaced with strict equality in test_turn_budget_matches_fixture (parametrized over all 3 state machines)"
  - "Plan frontmatter names test files as test_adversarial_routing.py + test_state_machine_goldens.py -- authoritative over the plan's free-text 'test_adversarial_routing_goldens.py' mention"
  - "_extract_paths_from_diff treats a/ and b/ sides both as separate extracted paths (matches git diff --name-only behavior on renames -- the exact regression surface the renamed_ui_component fixture exercises)"
  - "gstack_router pytest fixture loads real gstack.toml rules via load_template('gstack') -- no mock rules; any change to gstack.toml that drops a rule immediately regresses here"

patterns-established:
  - "Oracle JSON + parametrized test file is the standard golden-test shape for route-like matching problems (diff paths -> participants)"
  - "Parametrize over a tuple (skill, fixture_file, module_path) -- 3 tests x 3 machines = 9 test IDs with one assertion each, superior diagnostics vs a single omnibus test"

requirements-completed: [SPRINT-03, QUALITY-07]

# Metrics
duration: 10min
completed: 2026-04-21
---

# Phase 4 Plan 13: adversarial-routing-golden-tests Summary

**8 adversarial diff fixtures + expected_routing.json oracle drive a 12-test parametrized regression suite over GstackReviewRouter; a separate 10-test consolidated golden harness asserts bijective agreement between the 3 interactive state-machine modules (_TRANSITIONS / TURN_BUDGET / _FINAL_STATES) and their fixture JSONs -- catches both routing drift (renamed UI loses designer, whitespace bleeds past floor) and transition-table drift (fixture changed without code, or vice versa) at CI time.**

## Performance

| Metric       | Value |
|--------------|-------|
| Tasks        | 3     |
| Files created| 11    |
| Files modified| 1    |
| Tests added  | 22 (12 routing + 10 state-machine) |
| Duration     | 10min |

## Scope

- **SPRINT-03:** "verified by a routing golden test over at least 8 fixture diffs including adversarial cases" -- delivered. 8 adversarial fixtures covering the §04-CONTEXT specifics set (renamed UI, crypto test file, whitespace-only, package.json dep bump, auth middleware rewrite, cross-cutting refactor, mixed UI+API, generated migration).
- **QUALITY-07:** "interactive skills must remain multi-turn; turn-budget assertions catch regression" -- delivered via `test_turn_budget_matches_fixture` parametrized across the 3 state machines with strict equality.

## Task Breakdown

### Task 1 -- 8 adversarial diff fixtures + expected_routing.json
- **Commit:** `ae0d900`
- **Files:** 9 new files under `tests/fixtures/review_routing/`
- **Verification:** 8 diff files present; `expected_routing.json` has exactly 8 keys matching the must_haves.truths set; every entry includes `"reviewer"` in `expected_participants` (floor invariant).

### Task 2 -- Parametrized adversarial routing golden test
- **Commit:** `e24b3ec`
- **File:** `tests/test_adversarial_routing.py`
- **Tests added:** 12 (8 parametrized `test_adversarial_diffs` + 2 path-extraction helper tests + 1 floor-sanity + 1 fixture-count).
- **Verification:** `pytest tests/test_adversarial_routing.py -x -q` -> 12 passed.
- **Oracle-driven parametrize:** `pytest.mark.parametrize("fixture_name,spec", list(_EXPECTED.items()))` surfaces each fixture as its own node ID (e.g., `test_adversarial_diffs[renamed_ui_component-spec0]`) for crisp CI failure attribution.

### Task 3 -- Consolidated state-machine golden tests
- **Commit:** `07fdc8e`
- **Files:** `tests/test_state_machine_goldens.py` + appended entry in `deferred-items.md`.
- **Tests added:** 10 (3 parametrized groups * 3 machines = 9 parametrized + 1 coverage meta-test).
- **Verification:** `pytest tests/test_state_machine_goldens.py -x -q` -> 10 passed.
- **ISS-06 tightening:** `test_turn_budget_matches_fixture` uses `turn_budget == fx["turn_budget"]` strict equality (not `>= N` soft-bound). Office-hours 13 / design-consultation 15 / investigate 12 all match fixture values exactly.

## Verification

```
uv run pytest tests/test_adversarial_routing.py tests/test_state_machine_goldens.py -x -q
  -> 22 passed in 0.17s

ls tests/fixtures/review_routing/*.diff | wc -l                    -> 8
ls tests/fixtures/gstack_state_machines/*.transitions.json | wc -l -> 3

uv run pytest tests/test_gstack_review_router.py \
              tests/test_office_hours_state_machine.py \
              tests/test_design_consultation_state_machine.py \
              tests/test_investigate_state_machine.py -q
  -> 71 passed in 0.22s (Plan 06/07/08/09 in-plan tests unaffected)
```

## Success Criteria

- [x] 8 adversarial routing fixtures drive a parametrized golden test
- [x] 3 state-machine fixtures drive a consolidated bijective golden test
- [x] 12 routing tests + 10 state-machine golden tests all pass
- [x] Catches regressions where rule edits forget to update fixtures (and vice versa)

## Deviations from Plan

### Design decisions applied under ISS-06 guidance

**1. [ISS-06 revision] Removed `test_monologue_collapse_detector`, strengthened `test_turn_budget_matches_fixture` to strict equality**
- **Context:** Plan comment block said "remove the soft-bound `test_monologue_collapse_detector` or tighten to equality against fixture turn_budget values -- your choice per the plan's updated guidance."
- **Decision:** Chose BOTH: (a) removed the soft-bound test entirely and (b) upgraded the remaining parametrized turn-budget test from the plan's literal `==` assertion (already equality) to a clarifying docstring that calls out the tightening, so future readers understand the regression surface this catches. Net: 10 state-machine goldens (was 11 as drafted in the plan) with a crisper failure mode.
- **Trade-off accepted:** Any deliberate bump to the fixture's turn_budget requires a matching bump to the code's `TURN_BUDGET` constant in the same commit (good -- catches monologue-collapse by construction).

### Auto-fixed Issues

None. All three tasks executed exactly as written except for the ISS-06 design decision documented above.

## Threat Flags

No new security-relevant surface introduced -- changes are strictly test fixtures + test modules that read, never write, external data.

## Deferred Issues

**Parallel-wave RED test from Plan 04-14 visible during broad sanity**

- `tests/test_gstack_role_prompts.py::test_reviewer_review_and_investigate` fails in the broad regression because it asserts the removal of `INTERACTIVE-RUNTIME-DEFERRED` markers that Plan 04-14 will remove in its GREEN phase.
- Confirmed via `git stash` bisection: failure persists with my changes stashed (introduced by 04-14 commit `dc474ba`).
- Out-of-scope per GSD scope-boundary rule. Logged to `deferred-items.md`; will self-resolve when Plan 04-14 lands its matching GREEN.
- Plan 04-13's own 22 tests all green in isolation and in the scoped router+state-machine suite (71/71).

## Self-Check

All claims below verified against disk + git log after SUMMARY write.

- FOUND: tests/fixtures/review_routing/renamed_ui_component.diff
- FOUND: tests/fixtures/review_routing/crypto_test_file.diff
- FOUND: tests/fixtures/review_routing/whitespace_only.diff
- FOUND: tests/fixtures/review_routing/package_json_dep_bump.diff
- FOUND: tests/fixtures/review_routing/auth_middleware_rewrite.diff
- FOUND: tests/fixtures/review_routing/cross_cutting_refactor.diff
- FOUND: tests/fixtures/review_routing/mixed_ui_and_api.diff
- FOUND: tests/fixtures/review_routing/generated_migration.diff
- FOUND: tests/fixtures/review_routing/expected_routing.json
- FOUND: tests/test_adversarial_routing.py
- FOUND: tests/test_state_machine_goldens.py
- FOUND: ae0d900 (Task 1 fixtures commit)
- FOUND: e24b3ec (Task 2 routing-test commit)
- FOUND: 07fdc8e (Task 3 state-machine-goldens commit)

## Self-Check: PASSED
