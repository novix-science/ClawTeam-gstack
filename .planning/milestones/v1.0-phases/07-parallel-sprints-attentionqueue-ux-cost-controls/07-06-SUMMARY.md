---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 06
subsystem: cost-fallback-cache
tags:
  - model-fallback-ladder
  - cache-hit-rate
  - event-subscriber
  - tdd
requires:
  - clawteam.cost.pricing.ModelTier (Plan 07-05)
  - clawteam.cost.pricing.resolve_tier (Plan 07-05)
  - clawteam.events.types.ClaudeApiResponse (Plan 07-01)
  - clawteam.events.bus.EventBus (Phase 2)
provides:
  - clawteam.cost.fallback.apply_fallback pure function (opus->sonnet->haiku)
  - clawteam.cost.fallback.FALLBACK_LADDER ladder map
  - clawteam.cost.fallback.TIER_TO_CANONICAL canonical-name map
  - clawteam.cost.cache_tracker.CacheTracker event subscriber (D-12)
  - clawteam.cost.cache_tracker.HEALTHY_THRESHOLD constant (0.5)
  - clawteam.cost public API now includes all 5 additions
affects:
  - Plan 07-07 (clawteam team show reads CacheTracker.cache_hit_rate
    to populate CostRollup.cache_hit_rate in the team panel)
  - Future NativeCliAdapter integration (out-of-scope for Phase 7 —
    apply_fallback is callable at spawn-time but no call-site wiring
    lands in this plan; policy-ready, caller-integration deferred)
tech-stack:
  added: []
  patterns:
    - "Pure-function policy module (Phase 7 D-11 fallback ladder): no state,
      no events emitted, 3-line evaluation — callers compose it at their
      decision points"
    - "Event-subscriber accumulator mirroring Plan 07-05 CostTracker shape:
      per-team filter via team_name; O(1) memory via running aggregates; no
      raw event list retained"
    - "Strict > threshold on is_healthy (0.5 break-even != healthy) matches
      Plan 07-05 tracker's strict crossing semantics for alarm fires"
    - "TIER_TO_CANONICAL separates the downgrade target (tier name) from the
      model string the spawn adapter consumes — callers needing a more
      specific model (e.g. claude-sonnet-20250101) wrap the canonical name"
key-files:
  created:
    - clawteam/cost/fallback.py
    - clawteam/cost/cache_tracker.py
    - tests/cost/test_fallback.py
    - tests/cost/test_cache_tracker.py
  modified:
    - clawteam/cost/__init__.py (re-exports apply_fallback, FALLBACK_LADDER,
      TIER_TO_CANONICAL, CacheTracker, HEALTHY_THRESHOLD)
key-decisions:
  - "Haiku -> haiku is a terminal transition that still returns
    fallback_applied=True so callers can stamp the envelope flag even when
    no concrete model change occurred (policy engaged != model changed)"
  - "Unknown tiers (gpt-4, empty string) return (model_pref, False) even
    when over-threshold — the policy has nothing to downgrade to, so the
    envelope flag stays off (no misleading 'fallback' mark)"
  - "apply_fallback does NOT consult CostTracker directly — caller passes
    spend_percent so the function is composable with per-sprint or
    per-user budgets, not only the team-level tracker spend"
  - "CacheTracker keeps O(1) running aggregates (no raw event list) so
    10-sprint load tests don't grow memory with event count (Pitfall 4)"
  - "is_healthy uses strict > (exactly 0.5 returns False): break-even is
    not sustained cache use; healthy means we're ahead of creation cost"
  - "Both modules subscribe or consume ClaudeApiResponse but do NOT emit
    any events — dashboard consumers pull cache_hit_rate at render time
    (Plan 07-07 wiring); keeps coupling one-directional"
patterns-established:
  - "Pure-function policy layer over pricing.resolve_tier — reusable shape
    for future budget policies (e.g. per-sprint caps, per-role prioritization)
    without any tracker-layer changes"
  - "Cross-team isolation by team_name filter in CacheTracker mirrors
    CostTracker pattern — multiple trackers share one bus"
requirements:
  - QUALITY-12 (policy + cache-metric half; rendering half lands in 07-07)
metrics:
  duration: "~5min"
  started: "2026-04-22T14:48:06Z"
  completed: "2026-04-22T14:50:21Z"
  tasks_completed: 2
  tests_added: 21 (10 fallback + 11 cache_tracker)
  tests_passing: 42 (full tests/cost/ suite)
  files_created: 4
  files_modified: 1
---

# Phase 7 Plan 06: Cost Fallback + Cache Tracker Summary

**One-liner:** Wave 4 part 2 — model fallback ladder policy
(`apply_fallback` pure function: opus -> sonnet -> haiku, D-11) plus
`CacheTracker` event subscriber computing per-team cache hit rate from
`ClaudeApiResponse` events (D-12); both small, pure, and strictly
event-subscribed / stateless.

## What Was Built

**Task 1 — `clawteam/cost/fallback.py` + `FALLBACK_LADDER` (D-11).**
Pure function `apply_fallback(model_pref, spend_percent,
fallback_at_percent=80.0)` returning `(effective_model,
fallback_applied)`. Ladder: `opus -> sonnet`, `sonnet -> haiku`,
`haiku -> haiku` (terminal). Below-threshold spends return
`(model_pref, False)` unchanged. Over-threshold spends resolve the
tier via `clawteam.cost.pricing.resolve_tier`, consult
`FALLBACK_LADDER`, then map back to a canonical model string via
`TIER_TO_CANONICAL`. Unknown tiers (e.g. `gpt-4`, empty string) return
unchanged with `fallback_applied=False` — the policy has nothing to
downgrade to. Reuses Plan 07-05's alias-resolution so versioned model
strings (`claude-3-opus-20240229`) map correctly. **10/10 tests green.**

**Task 2 — `clawteam/cost/cache_tracker.py` + `HEALTHY_THRESHOLD` (D-12).**
`CacheTracker` per-team event subscriber — on construction with a bus,
registers a handler for `ClaudeApiResponse`; each event with matching
`team_name` increments running aggregates for `cache_read_tokens` and
`cache_creation_tokens`. `cache_hit_rate()` returns
`read / (read + creation)` with a divide-by-zero-safe `0.0` floor.
`is_healthy()` uses strict `>` against `HEALTHY_THRESHOLD = 0.5` —
exactly 0.5 is break-even, not healthy. Accessors
`total_cache_read()` and `total_cache_creation()` expose raw totals
for dashboard consumers. `clawteam/cost/__init__.py` re-exports the
5 new public names (`apply_fallback`, `FALLBACK_LADDER`,
`TIER_TO_CANONICAL`, `CacheTracker`, `HEALTHY_THRESHOLD`).
**11/11 tests green.**

## Verification

Plan 07-06 scoped suite:

```
uv run python -m pytest tests/cost/test_fallback.py tests/cost/test_cache_tracker.py -q
=> 21 passed
```

Full cost suite (07-05 + 07-06):

```
uv run python -m pytest tests/cost/ -q
=> 42 passed in 0.09s
```

BC regression (Phase 7 substrate + bus):

```
uv run python -m pytest tests/test_event_types_phase7.py tests/test_event_bus.py tests/cost/ -q
=> 73 passed in 0.70s
```

Integration smoke (exactly matches plan's <verification> block):

```
uv run python -c "from clawteam.cost import apply_fallback, CacheTracker; print(apply_fallback('claude-opus', 90.0, 80.0))"
=> ('claude-sonnet', True)
```

## Acceptance Criteria

- [x] `grep -q "def apply_fallback" clawteam/cost/fallback.py` succeeds
- [x] `grep -q "FALLBACK_LADDER" clawteam/cost/fallback.py` succeeds
- [x] `pytest tests/cost/test_fallback.py -q` reports 10 passed
  (plan said 9; this plan added 1 extra haiku-stays-haiku / ladder-shape
  assertion, tracked in Deviations below — all still acceptance-aligned)
- [x] `grep -q "class CacheTracker" clawteam/cost/cache_tracker.py` succeeds
- [x] `pytest tests/cost/test_cache_tracker.py -q` reports 11 passed
  (plan said 8; 3 extra tests added for init re-exports + strict 0.5
  threshold + explicit healthy/unhealthy split — additive only)
- [x] `pytest tests/cost/ -q` reports 42 passed (all green — 21 from
  07-05 preserved, 21 added by 07-06)
- [x] Phase 7 plan's verification smoke returns `('claude-sonnet', True)`

## Commits

Two tasks, strict TDD RED -> GREEN gates preserved:

**Task 1 — apply_fallback + FALLBACK_LADDER:**

- `a699a13` test(07-06): add failing test for fallback ladder (Task 1 RED)
- `9022c80` feat(07-06): implement model fallback ladder (Task 1 GREEN)

**Task 2 — CacheTracker event subscriber:**

- `b49e004` test(07-06): add failing tests for CacheTracker (Task 2 RED)
- `43b1f46` feat(07-06): implement CacheTracker event subscriber (Task 2 GREEN)

## Deviations from Plan

**1 minor additive deviation — extra tests (Rule 2: quality / coverage).**

The plan's <behavior> called for 8 cache-tracker tests and 8 fallback
tests; the implementation landed 11 cache and 10 fallback. The extras
are defensive coverage that tightens the acceptance contract, not
extension of scope:

- `test_fallback_at_percent_100` (split into two assertions — at 99
  and at 100) — locks the `>=` boundary.
- `test_empty_model` — locks the empty-string branch of `resolve_tier`.
- `test_ladder_map_shape` — locks the public `FALLBACK_LADDER` dict
  shape so downstream consumers can trust structure without a shape
  test on every caller.
- `test_healthy_threshold_strict_greater` — locks the strict `>`
  semantics (plan didn't specify strict vs. non-strict; strict is
  documented in decisions above as the chosen semantics).
- `test_healthy_threshold_above_50` / `test_healthy_threshold_below_50`
  — the plan bundled these as a single test; splitting them gives
  per-assertion failure messages for future regression triage.
- `test_cost_init_reexports` — locks the `clawteam.cost` public API
  surface (plan's acceptance criterion 2-B called for "full cost dir
  green" but did not explicitly test the `__init__.py` re-exports; one
  test captures the whole public surface).

No production code deviated from the plan's <action> block; both
modules match the plan's skeleton line-for-line apart from docstring
phrasing.

**Total production-code deviations:** 0.
**Test-coverage deviations (additive only):** 5 extra tests.
**Impact on plan:** None — all plan acceptance criteria met and exceeded.

## Issues Encountered

None.

## User Setup Required

None — no external service, no config file, no credential, no runtime
change. The two new modules are pure Python with zero new dependencies.

## Interfaces for Downstream Plans

**Plan 07-07 (clawteam team show cost panel):**
- Instantiate one `CacheTracker(team, bus=bus)` per team rendered in
  the dashboard; read `cache_hit_rate()` to populate
  `CostRollup.cache_hit_rate` at render time (Plan 07-05's tracker
  leaves this field at `0.0` by design — documented seam).
- Render a healthy/unhealthy indicator via `is_healthy()` —
  `HEALTHY_THRESHOLD` is public for banner-threshold alignment.
- Optionally call `apply_fallback(model_pref, tracker.spend_percent(),
  config.fallback_at_percent)` at dashboard render time to preview
  "this invocation would downgrade to <tier>" for user awareness —
  but the actual fallback policy wiring belongs at
  `invoke_native_cli` / `NativeCliAdapter` call-sites (out-of-scope
  for Phase 7 — documented for Phase 5.1 per research assumption A6).

**Future NativeCliAdapter integration (out-of-scope for Phase 7):**
- Call `apply_fallback(requested_model, tracker.spend_percent(),
  config.fallback_at_percent)` before spawn; pass the returned
  `effective_model` to the spawn command; stamp
  `ToolCallCompleted.model_fallback_applied = True` when the returned
  flag is True so reviewers can see the policy engaged.

## Known Stubs

**None.** Both modules ship in their intended final Phase 7 shape.
The `cache_hit_rate=0.0` default on `CostRollup` from Plan 07-05 is
not a stub — it is a documented seam that Plan 07-07 fills by calling
`CacheTracker.cache_hit_rate()` at render time and constructing a
fresh `CostRollup` with the live value.

## Self-Check: PASSED

Files created/modified verified on disk:

- `clawteam/cost/fallback.py` -> FOUND
- `clawteam/cost/cache_tracker.py` -> FOUND
- `clawteam/cost/__init__.py` -> MODIFIED (re-exports added)
- `tests/cost/test_fallback.py` -> FOUND
- `tests/cost/test_cache_tracker.py` -> FOUND

Commits verified in git log:

- `a699a13` (test 07-06 Task 1 RED) -> FOUND
- `9022c80` (feat 07-06 Task 1 GREEN) -> FOUND
- `b49e004` (test 07-06 Task 2 RED) -> FOUND
- `43b1f46` (feat 07-06 Task 2 GREEN) -> FOUND

Acceptance grep checks:

- `grep -q "def apply_fallback" clawteam/cost/fallback.py` -> OK
- `grep -q "FALLBACK_LADDER" clawteam/cost/fallback.py` -> OK
- `grep -q "class CacheTracker" clawteam/cost/cache_tracker.py` -> OK
- `grep -q "HEALTHY_THRESHOLD" clawteam/cost/cache_tracker.py` -> OK

Verification commands from plan:

- `pytest tests/cost/test_fallback.py -q` -> **10 passed** in 0.05s
- `pytest tests/cost/test_cache_tracker.py -q` -> **11 passed** in 0.05s
- `pytest tests/cost/ -q` -> **42 passed** in 0.09s
- `python -c "from clawteam.cost import apply_fallback, CacheTracker; print(apply_fallback('claude-opus', 90.0, 80.0))"`
  -> **`('claude-sonnet', True)`**

BC regression scope:

- `pytest tests/test_event_types_phase7.py tests/test_event_bus.py
  tests/cost/ -q` -> **73 passed** in 0.70s (Phase 7 substrate + bus
  + full cost suite unchanged).

## TDD Gate Compliance

Both tasks used TDD; RED commits preceded GREEN commits:

| Task | RED commit | GREEN commit | Gate pass |
|------|-----------|--------------|-----------|
| 1    | `a699a13` | `9022c80`    | OK        |
| 2    | `b49e004` | `43b1f46`    | OK        |

Each RED commit was confirmed by running pytest and observing a
`ModuleNotFoundError` at collection time (the imported module did not
yet exist) — this is a valid RED signal since the tests cannot pass
until the production module is authored. The GREEN commit in each
case ships the module that makes the import resolve + all tests pass.

## Next Plan Readiness

Plan 07-06 complete. Phase 7 has 3 plans remaining:

- **07-07** `clawteam team show` cost panel — consumes
  `CostTracker.rollup_team` + `CacheTracker.cache_hit_rate` +
  `BudgetAlarmReached` banners; both inputs now live.
- **07-08** `clawteam doctor --gc` zombie worktree cleanup — emits
  `ZombieWorktreeGced`; substrate landed in Plan 07-01.
- **07-09** 10-sprint integration load test (D-14/15/16) — asserts
  rollup correctness + alarm firing + fallback activation at 80% +
  cache-hit-rate > 50% on steady-state run.

All three cost-layer modules now exist
(`clawteam/cost/{pricing,rollup,tracker,fallback,cache_tracker}.py`);
Plan 07-07 wires them into the CLI rendering layer without needing
further substrate changes.

---
*Phase: 07-parallel-sprints-attentionqueue-ux-cost-controls*
*Plan: 06 (Wave 4 part 2 — cost fallback + cache tracker)*
*Completed: 2026-04-22*
