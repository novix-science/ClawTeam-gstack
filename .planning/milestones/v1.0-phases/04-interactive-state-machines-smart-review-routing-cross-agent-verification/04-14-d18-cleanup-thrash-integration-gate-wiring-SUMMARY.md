---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
plan: 14
subsystem: prompts+tests
tags: [d18-cleanup, deferral-markers, mid-review-thrash, integration-test, roadmap-sc4, thrash-decision, iss-06]

# Dependency graph
requires:
  - phase: 04
    provides: office-hours/design-consultation/investigate state machines (Plans 07/08/09)
  - phase: 04
    provides: dispatch_review_phase + MidReviewThrash (Plans 02 + 10)
  - phase: 04
    provides: reviewer/designer/security/dx-lead decorrelation prompt supplements (Plan 11)
  - phase: 04
    provides: test_turn_budget_matches_fixture equality constraint (Plan 13)
provides:
  - pm.md / designer.md / reviewer.md with D-18 deferral markers removed
  - test_markers_removed + test_markers_removed_and_runtime_present (inverse-assertion safety net)
  - tests/test_mid_review_push_integration.py (3 tests, closes ROADMAP Phase 4 Success Criterion #4)
affects: [upstream-pr-ready, phase-4-close]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inverse assertion pattern: test_markers_removed_and_runtime_present asserts BOTH (markers gone) AND (corresponding runtime module + fixture exist) -- prevents the 'markers removed but runtime didn't ship' failure mode"
    - "Real-subprocess integration test: tmp_path git init + two commits + REAL subprocess.run (no mock) exercises _current_head / _diff_paths shell=False + 10s timeout path end-to-end"
    - "Bus-observation thrash_decision routing: spawn_fn inspects bus.thrash_events before returning reviewer aggregator report; includes thrash_decision field only when a MidReviewThrash was captured during dispatch"

key-files:
  created:
    - tests/test_mid_review_push_integration.py
  modified:
    - clawteam/templates/gstack/prompts/pm.md
    - clawteam/templates/gstack/prompts/designer.md
    - clawteam/templates/gstack/prompts/reviewer.md
    - tests/test_gstack_role_prompts.py
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/deferred-items.md

key-decisions:
  - "pm.md heading simplified from '## /office-hours rubric (interactive runtime -- Phase 4)' to '## /office-hours rubric' -- the parenthetical deferral qualifier becomes noise once the runtime has shipped"
  - "reviewer.md SHA-PIN section title preserved but changed from 'SHA-PIN-DEFERRED' to 'SHA-pinning' -- same canonical content (record HEAD SHA, re-pin vs superseded) but no longer framed as a deferral"
  - "Task 3 ISS-06 is a no-op: test_monologue_collapse_detector was never shipped by Plan 13 (grep tests/ returns 0 matches); Plan 13's test_turn_budget_matches_fixture already uses strict equality, so the redundancy ISS-06 flagged cannot materialize. Skipping per plan's own pre-check guidance."
  - "Integration test uses hermetic CLAWTEAM_DATA_DIR pointing at tmp_path/clawteam-data AND a separate tmp_path/sprint-workspace as workspace_branch -- avoids state.json writes clobbering the real git repo under test"
  - "Reviewer report thrash_decision field populated by spawn_fn inspecting bus.thrash_events at call time -- respects the current dispatch_review_phase contract where spawn_fn has full bus access"

requirements-completed: [SPRINT-04, SPRINT-05, QUALITY-07, QUALITY-09, QUALITY-13]

# Metrics
duration: 10min
completed: 2026-04-21
---

# Phase 4 Plan 14: d18-cleanup-thrash-integration-gate-wiring Summary

**Four D-18 deferral markers (INTERACTIVE-RUNTIME-DEFERRED x3 + SHA-PIN-DEFERRED x1) removed from pm/designer/reviewer role prompts now that Phase 4's runtime has shipped (Plans 07/08/09/10); two inverse-assertion regression tests lock in the cleanup; a new tmp_path-based end-to-end mid-review-push integration test (3 tests, real git subprocess, no mocks) closes ROADMAP Phase 4 Success Criterion #4 by asserting the MidReviewThrash event payload AND the D-19 thrash_decision frontmatter field contract.**

## Performance

| Metric            | Value                                              |
|-------------------|----------------------------------------------------|
| Tasks             | 3 (Task 3 no-op per plan pre-check)                |
| Files created     | 1 (tests/test_mid_review_push_integration.py)     |
| Files modified    | 4 (3 prompts + test_gstack_role_prompts.py)       |
| Tests added       | 5 (2 role-prompt regressions + 3 integration)      |
| Assertions inverted | 4 (existing deferral-marker assertions)          |
| Duration          | 10min                                              |

## Scope

- **SPRINT-04 / SPRINT-05:** Review / Ship phase integration verified end-to-end for mid-review-push flow — closes the ROADMAP Phase 4 Success Criterion #4 coverage gap ("verified by a mid-review-push integration test").
- **QUALITY-07:** Interactive-runtime completeness audit: inverse-assertion test guarantees each skill's state-machine module + fixture exists whenever the corresponding deferral marker is absent — catches the "markers removed but runtime didn't ship" failure mode.
- **QUALITY-09 / QUALITY-13:** SHA-pin + reviewer decorrelation contract now documented as canonical (not deferral) in reviewer.md; D-19 thrash_decision frontmatter field enforced by the integration test.

## Task Breakdown

### Task 1 — Remove D-18 markers + invert tests + add runtime-present inverse assertion
- **Commits:** `dc474ba` (RED), `64a55a8` (GREEN)
- **Files:** pm.md, designer.md, reviewer.md, tests/test_gstack_role_prompts.py
- **Tests added:** 2 (`test_markers_removed`, `test_markers_removed_and_runtime_present`)
- **Tests updated:** 3 existing role-prompt tests — 4 deferral-marker assertions inverted from `in prompt` to `not in prompt`, docstrings updated with Plan 04-14 reference.
- **Verification:** `pytest tests/test_gstack_role_prompts.py -q` → 15 passed.

#### Line-number diff (before → after)

**pm.md** (2091 → 2054 bytes; 37 bytes saved):
```
Line 16-20 (before)                          Line 16-20 (after)
----------------------------------------     ----------------------------------------
## /office-hours rubric (interactive         ## /office-hours rubric
   runtime -- Phase 4)
                                             One forcing question per turn. Do NOT
INTERACTIVE-RUNTIME-DEFERRED:                enumerate all 6 in a single monologue
  /office-hours ships as a Phase 4           -- that is the lost-in-the-middle anti-
  multi-turn state machine. Until then:      pattern. Phase 4's state machine
  ONE forcing question per turn. Do NOT      enforces per-question advancement; this
  enumerate all 6 in a single monologue      prompt reinforces the discipline.
  -- that is the lost-in-the-middle
  anti-pattern.
```

**designer.md** (2531 → 2575 bytes; 44 bytes added — canonical runtime text slightly longer than the deferral note it replaces, within 4 KB budget):
```
Line 15-19 (before)                          Line 15-19 (after)
----------------------------------------     ----------------------------------------
## /plan-design-review rubric -- 7 Passes    ## /plan-design-review rubric -- 7 Passes
   (verbatim from upstream v2.0.0)              (verbatim from upstream v2.0.0)

INTERACTIVE-RUNTIME-DEFERRED:                Evaluate one pass per turn. Emit a 0-10
  /design-consultation per-dimension         score + rationale per pass. Phase 4's
  dialogue ships as a Phase 4 state          `/design-consultation` state machine
  machine. In Phase 3, evaluate one pass     iterates the 7 passes in a deterministic
  per turn and emit a 0-10 score +           transition order -- designer_rubric_
  rationale.                                 dimension 1..7 map to Pass 1..7.
```

**reviewer.md** (2227 → 2413 bytes; 186 bytes added — now carries canonical /investigate freeze/unfreeze + SmartReviewRouter thrash-decision contract, within 4 KB budget):
```
Line 38-51 (before)                          Line 38-51 (after)
----------------------------------------     ----------------------------------------
## /investigate runtime -- Phase 4           ## /investigate runtime

INTERACTIVE-RUNTIME-DEFERRED:                Emit hypotheses one per turn via
  /investigate per-hypothesis state          `reviewer_hypothesis_index`. On
  machine (plus auto-`/freeze` of            hypothesis declaration the state machine
  the module under investigation)            auto-freezes the module under
  ships in Phase 4. In Phase 3, emit         investigation via
  hypotheses one per turn via the            `FreezeRegistry.freeze(module_path,
  envelope index; Phase 4 will add the       reason="investigate:<sprint>:<hyp>")`.
  freeze/release lifecycle around them.      On hypothesis complete or abandon, the
                                             state machine unfreezes with a matching
## SHA-PIN-DEFERRED                          reason. Module path is hypothesis-
                                             provided (explicit), not auto-derived
SHA-PIN-DEFERRED: At review start,           from stack traces.
  record HEAD SHA in your turn context.
  If you detect HEAD has moved mid-          ## SHA-pinning
  review, mark your verdict "superseded"
  and stop. Real cross-agent SHA             At review start, record HEAD SHA in your
  verification ships in Phase 4              turn context via the SmartReviewRouter
  (SmartReviewRouter). Phase 3 records       review_sha field. If HEAD advances mid-
  the SHA manually; Phase 4 enforces         review, the harness emits a
  via the router.                            `mid_review_thrash` event; in your next
                                             turn you either re-pin to the new SHA
                                             or mark the prior review `superseded`
                                             (write `thrash_decision: re-pin` or
                                             `thrash_decision: superseded` into your
                                             review-report frontmatter).
```

**Grep-verified zero-hit count:**
```
$ grep -rE "INTERACTIVE-RUNTIME-DEFERRED:|SHA-PIN-DEFERRED:" clawteam/templates/gstack/prompts/
(no output; exit 1 -- 0 matches; baseline was 4)
```

### Task 2 — End-to-end mid-review-push integration test
- **Commit:** `8a02015`
- **File:** `tests/test_mid_review_push_integration.py` (329 LOC)
- **Tests added:** 3
  - `test_mid_review_push_integration_end_to_end` — real git init + baseline commit + dispatch + mid-dispatch commit injection → asserts MidReviewThrash event fires with `(review_sha=first_sha, new_sha=second_sha, diff_paths_added=["mid-review-change.txt"])` AND `reviewer_report["thrash_decision"] == "re-pin"`.
  - `test_mid_review_push_no_thrash_when_head_stable` — HEAD-stable control: no thrash event, no thrash_decision in reviewer report.
  - `test_mid_review_push_thrash_decision_field_enforced` — reviewer picks `superseded` variant; asserts the D-19 enum constraint `{re-pin, superseded}` holds both ways.
- **Verification:** `pytest tests/test_mid_review_push_integration.py -q` → 3 passed in 0.20s.
- **Plan 10 unregressed:** `pytest tests/test_review_phase_dispatch.py -q` → 28 passed.

### Task 3 — ISS-06 cleanup (no-op)
- **Commit:** none (nothing to change)
- **Justification:** `grep -rn test_monologue_collapse_detector tests/` returns 0 matches. Plan 13 (landed while this plan was in flight at commit `01aba4d`) never shipped the soft-bound monologue-collapse test — instead it shipped `test_turn_budget_matches_fixture` as a parametrized equality test across all 3 state machines (office-hours 13 / design-consultation 15 / investigate 12). The redundancy ISS-06 flagged cannot materialize. Plan Task 3 pre-check: "If no match (Plan 13 didn't ship the test yet), skip Task 3 entirely — ISS-06 is already resolved by virtue of the test not existing."

## Verification

```
$ grep -rE "INTERACTIVE-RUNTIME-DEFERRED:|SHA-PIN-DEFERRED:" clawteam/templates/gstack/prompts/
(0 matches — baseline 4)

$ pytest tests/test_gstack_role_prompts.py tests/test_mid_review_push_integration.py \
         tests/test_review_phase_dispatch.py tests/test_state_machine_goldens.py \
         tests/test_adversarial_routing.py -q
68 passed in 0.35s

$ wc -c clawteam/templates/gstack/prompts/pm.md \
        clawteam/templates/gstack/prompts/designer.md \
        clawteam/templates/gstack/prompts/reviewer.md
2054  pm.md
2575  designer.md
2413  reviewer.md
(all three < 4096 D-14 hard cap; average 2347 bytes < 3072 soft cap)

$ grep -c thrash_decision tests/test_mid_review_push_integration.py
20   (plan required >= 3; 20 covers all 3 test bodies)

$ wc -l tests/test_mid_review_push_integration.py
329  (plan required >= 120)
```

**ROADMAP Phase 4 Success Criterion #4 coverage:** CLOSED. `test_mid_review_push_integration_end_to_end` is the missing end-to-end verification that was explicitly called out in the SC — it exercises the full flow on a real git repo (not mocked subprocess) and asserts both the event payload and the D-19 frontmatter field in the reviewer's report.

## Success Criteria

- [x] 4 D-18 markers removed from pm.md (1), designer.md (1), reviewer.md (2)
- [x] `test_markers_removed` + `test_markers_removed_and_runtime_present` pass and enforce the inverse
- [x] 4 existing marker assertions inverted (pm, designer, reviewer × 2)
- [x] `tests/test_mid_review_push_integration.py` ships 3 tests, uses REAL git subprocess (no mock), asserts MidReviewThrash payload + thrash_decision field
- [x] ISS-06 redundant soft-bound test — resolved (never shipped; equality test is canonical)
- [x] ROADMAP Phase 4 Success Criterion #4 closed by `test_mid_review_push_integration_end_to_end`
- [x] No existing Phase 1/2/3 tests regress within the plan's scoped surface (68/68 plan-scoped tests green)
- [x] Plan 05 / 10 / 11 / 13 outputs untouched — this plan consumed their contracts verbatim

## Deviations from Plan

### Design decisions

**1. [Decision] Task 3 skipped per plan's own pre-check rule**
- **Found during:** Task 3 pre-check (`grep -rn test_monologue_collapse_detector tests/`)
- **Observation:** Zero matches. Plan 13 (which ran in parallel, landed at commit `01aba4d`) never shipped the soft-bound test — instead its `test_turn_budget_matches_fixture` parametrized over all 3 state machines with strict equality absorbs the ISS-06 mandate.
- **Action:** Skipped Task 3 per the plan's explicit guidance ("If no match (Plan 13 didn't ship the test yet), skip Task 3 entirely"). Documented in deferred-items.md 04-14 section.
- **Commits affected:** None.

### Auto-fixed Issues

None. All edits were exactly as scripted by the plan `<action>` blocks.

## Threat Flags

No new security-relevant surface introduced:

- **Task 1:** Canonical text rewrite inside role prompts (read by agents, no network/disk side effects in the harness runtime path).
- **Task 2:** New test file uses `subprocess.run` with shell=False, explicit cwd=tmp_path, fixed argv lists — matches T-04-31 mitigation pattern from clawteam.sprint.review_phase. tmp_path is pytest-isolated per the plan's threat register (T-04-50/T-04-51/T-04-52 dispositions unchanged).

## Deferred Issues

**Full-suite test-ordering flake at phase close (out-of-scope)**

- `tests/test_gstack_plugin.py::test_six_evidence_schemas_registered` and `tests/test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present` fail only when the full `pytest tests/` suite is run in alphabetical order; both pass in isolation and in scoped invocations.
- Confirmed pre-existing at the Plan 04-14 baseline (`0a411ef docs(04): capture phase plans`) via bisection (temporary clone + `git reset --hard`).
- Logged to `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/deferred-items.md` under the new **04-14 Observations** section. Carried forward as a Phase-4-close / Phase-5-infrastructure cleanup candidate; not caused by any Plan 14 change.

## Self-Check

All claims below verified against disk + git log after SUMMARY write.

- FOUND: clawteam/templates/gstack/prompts/pm.md (D-18 marker absent; signature preserved)
- FOUND: clawteam/templates/gstack/prompts/designer.md (D-18 marker absent; signature preserved)
- FOUND: clawteam/templates/gstack/prompts/reviewer.md (D-18 + SHA-PIN-DEFERRED absent; signature preserved)
- FOUND: tests/test_gstack_role_prompts.py (test_markers_removed + test_markers_removed_and_runtime_present)
- FOUND: tests/test_mid_review_push_integration.py (3 tests; uses real `subprocess.run`)
- FOUND: dc474ba (Task 1 RED commit)
- FOUND: 64a55a8 (Task 1 GREEN commit — marker removal)
- FOUND: 8a02015 (Task 2 integration-test commit)

## Self-Check: PASSED
