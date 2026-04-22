---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 05
subsystem: cost-tracking
tags:
  - cost-tracking
  - event-subscriber
  - budget-alarm
  - pricing
  - tdd
requires:
  - clawteam.events.types.ToolCallCompleted (Plan 07-01)
  - clawteam.events.types.BudgetAlarmReached (Plan 07-01)
  - clawteam.events.bus.EventBus (Phase 2)
provides:
  - clawteam.cost.pricing.MODEL_PRICING per-model USD/M-token table
  - clawteam.cost.pricing.calculate_cost_usd pure function
  - clawteam.cost.pricing.resolve_tier substring matcher
  - clawteam.cost.rollup.CostRollup frozen dataclass (9-field schema)
  - clawteam.cost.tracker.CostTracker event subscriber with 50/80/100
    threshold alarms
affects:
  - Plan 07-06 (fallback.py consumes tracker.spend_percent + reads
    BudgetAlarmReached; cache_tracker.py populates cache_hit_rate on
    CostRollup)
  - Plan 07-07 (clawteam team show cost panel reads rollup_team /
    rollup_by_agent / rollup_by_sprint)
  - Plan 07-09 (10-sprint load test asserts rollup correctness +
    3-threshold alarm firing per D-16)
tech-stack:
  added:
    - Hardcoded Anthropic 2026-04 pricing table
      (opus $15/$75, sonnet $3/$15, haiku $0.25/$1.25 per 1M)
  patterns:
    - Event-subscriber accountant (Phase 7 D-09 per-team aggregation)
    - Per-tracker fired_alarms set for exactly-once 50/80/100 emission
    - Strict (prev < thresh <= new) crossing semantics so re-emits don't
      fire when spend stays above threshold
    - Emit-outside-lock to avoid handler re-entry deadlocks
    - Pricing backstop when cost_usd=0.0 arrives (gh / lighthouse
      wrappers that don't supply pre-computed cost)
key-files:
  created:
    - clawteam/cost/pricing.py
    - clawteam/cost/rollup.py
    - clawteam/cost/tracker.py
    - tests/cost/__init__.py
    - tests/cost/test_pricing.py
    - tests/cost/test_tracker.py
  modified:
    - clawteam/cost/__init__.py (re-exports public API)
key-decisions:
  - "Pricing table is module-level dict[ModelTier, tuple[float, float]] — readable, easy PR target"
  - "resolve_tier uses substring match (not exact) so versioned model strings (claude-3-opus-20240229) map correctly"
  - "Tracker does NOT apply model fallback — advisory alarms only; Plan 07-06 fallback.py owns policy"
  - "Cost backstop via pricing activates when event.cost_usd <= 0.0 (not just == 0.0) so negative rounding accidents also trigger recompute"
  - "BudgetAlarmReached emitted outside RLock so handlers that re-enter tracker do not deadlock"
  - "Threshold crossing uses strict (prev < thresh <= new) — no duplicate fires when spend stays above"
  - "Tokens-by-tier histogram keyed by resolve_tier result; unknown models contribute to cost (via 0.0 backstop) but not to tier counts"
  - "rollup_team() cache_hit_rate hardcoded 0.0 — cache_tracker (Plan 07-06) merges real value externally"
patterns-established:
  - "Per-team event-driven aggregator: CostTracker filters by team_name so multiple trackers share one bus without cross-talk"
  - "Exactly-once alarm firing via _fired_alarms set — never re-fires across spend oscillation within a run"
  - "Pricing backstop pattern: event.cost_usd <= 0.0 triggers calculate_cost_usd(model, in, out) fallback"
requirements-completed:
  - QUALITY-12
duration: "~15min"
completed: 2026-04-22
---

# Phase 7 Plan 05: Cost Tracker Summary

**Per-model USD pricing table + frozen `CostRollup` schema + event-driven
`CostTracker` that subscribes to `ToolCallCompleted`, aggregates by
(team, sprint, agent), and emits `BudgetAlarmReached` at 50/80/100%
thresholds exactly once per run.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-22T14:34:00Z
- **Completed:** 2026-04-22T14:49:00Z
- **Tasks:** 2 (strict TDD RED → GREEN gates preserved on both)
- **Files created:** 6
- **Files modified:** 1

## Accomplishments

- `clawteam/cost/pricing.py` — hardcoded Anthropic 2026-04 per-model
  pricing (opus $15/$75, sonnet $3/$15, haiku $0.25/$1.25 per 1M tokens)
  + `resolve_tier` substring matcher + pure `calculate_cost_usd` with
  deterministic output.
- `clawteam/cost/rollup.py` — `CostRollup` frozen dataclass matching the
  9-field schema from 07-CONTEXT.md `<specifics>` (team, sprint_id,
  agent, tokens_opus/sonnet/haiku, cost_usd, cache_hit_rate,
  period_start/end). `sprint_id=None` + `agent=None` = team-level
  rollup.
- `clawteam/cost/tracker.py` — `CostTracker` per-team event-driven
  aggregator. Subscribes to `ToolCallCompleted` on construction; keeps
  three aggregation maps (by_agent / by_sprint / by_agent_sprint) plus a
  tokens-by-tier histogram; emits `BudgetAlarmReached` at configurable
  thresholds (default `[50, 80, 100]`), exactly once per threshold per
  run, with handler-safe emission outside the RLock.
- Pricing backstop: when `ToolCallCompleted.cost_usd <= 0.0`, the
  tracker falls back to `calculate_cost_usd(event.model,
  tokens_input, tokens_output)` so wrappers that don't supply
  pre-computed cost (gh / lighthouse) still contribute to rollup.
- 21 tests total (9 pricing + 12 tracker) all green; Phase 7 event / sprint
  / bus BC suite (55 tests) unchanged.

## Task Commits

1. **Task 1: Pricing table + calculate_cost_usd**
   - `b3ec96e` test(07-05): RED — 9 failing tests for pricing
   - `1a284a7` feat(07-05): GREEN — MODEL_PRICING + calculate_cost_usd +
     resolve_tier

2. **Task 2: CostRollup + CostTracker event subscriber**
   - `ad5f457` test(07-05): RED — 11 failing tests for rollup + tracker
   - `79ebd3e` feat(07-05): GREEN — CostRollup frozen dataclass +
     CostTracker event subscriber + __init__ re-exports

## Files Created/Modified

- `clawteam/cost/pricing.py` — hardcoded per-model pricing, resolve_tier
  substring matcher, calculate_cost_usd pure function.
- `clawteam/cost/rollup.py` — `CostRollup` frozen 9-field dataclass.
- `clawteam/cost/tracker.py` — `CostTracker` event subscriber with
  per-team filter + exactly-once alarm semantics.
- `clawteam/cost/__init__.py` — re-exports `MODEL_PRICING` /
  `calculate_cost_usd` / `resolve_tier` / `ModelTier` / `CostRollup` /
  `CostTracker`.
- `tests/cost/__init__.py` — package marker.
- `tests/cost/test_pricing.py` — 9 tests covering tier rates, aliases,
  unknown-model zero, partial tokens, empty input, table shape sanity,
  resolve_tier None cases.
- `tests/cost/test_tracker.py` — 12 tests covering rollup frozenness,
  zero-start tracker, single-event aggregation, cross-team isolation,
  3-threshold alarm firing with correct `percent` / `budget_usd` /
  `team_name`, no-duplicate alarms, per-agent rollup, per-sprint
  rollup, pricing backstop on `cost_usd=0.0`, D-16 100-event fixture
  (5 agents x 3 sprints x sonnet pricing = 1.05 total), and
  `rollup_team()` snapshot with tokens-by-tier breakdown.

## Decisions Made

See `key-decisions` frontmatter for the full list. Highlights:

- **Pricing backstop activates on `cost_usd <= 0.0`** (not just `== 0.0`)
  so negative rounding accidents also trigger recompute — defensive.
- **Threshold crossing uses strict `prev < thresh <= new`** — the
  `prev < thresh` clamp prevents false re-fires when spend stays above
  a threshold; the `<=` on the upper side ensures a single event that
  lands exactly on the threshold still fires.
- **Emission outside RLock** — `BudgetAlarmReached` handlers that
  re-enter the tracker (e.g. fallback.py consulting
  `spend_percent()`) would deadlock on a re-entrant lock hold; the
  tracker computes `newly_fired` inside the lock then emits outside.
- **Tokens-by-tier histogram keyed by `resolve_tier`** — unknown models
  still contribute to cost via the 0.0 backstop, but their tokens don't
  pollute the opus/sonnet/haiku breakdown on `rollup_team()`.

## Deviations from Plan

**None** — plan executed exactly as written. All 2 tasks, all RED → GREEN
gates preserved.

**Total deviations:** 0.
**Impact on plan:** None.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Interfaces for Downstream Plans

**Plan 07-06 (fallback.py + cache_tracker.py):**
- Reads `CostTracker.spend_percent()` + `current_spend_usd()` +
  `rollup_team().budget_usd` to decide opus → sonnet → haiku downgrade.
- Subscribes to `BudgetAlarmReached` for audit-log emission on each
  crossing (tracker emits the event; fallback consumes, does not emit).
- `cache_tracker.py` merges `cache_hit_rate` into `rollup_team()` snapshots
  via the `ClaudeApiResponse` event stream (tracker leaves the field at
  `0.0`).

**Plan 07-07 (clawteam team show cost panel):**
- Reads `CostTracker.rollup_team()` for the per-tier token breakdown
  column and budget-bar rendering.
- Reads `CostTracker.rollup_by_agent()` / `rollup_by_sprint()` for
  per-row slices.
- Watches `BudgetAlarmReached` for colored banner rendering at
  50/80/100% crossings.

**Plan 07-09 (10-sprint load test):**
- Instantiates one `CostTracker` per team; asserts D-16 fixture
  event stream produces correct rollup + exactly 3 `BudgetAlarmReached`
  emissions at thresholds [50, 80, 100].
- Asserts tracker memory does not grow with event count (aggregates
  only; no raw event list per D-04 pitfall mitigation).

## Known Stubs

**None** — pricing table + rollup dataclass + tracker subscriber all
ship in their intended final Phase 7 shape. `cache_hit_rate` on
`rollup_team()` is hardcoded `0.0` by design — Plan 07-06's
`cache_tracker.py` subscribes to `ClaudeApiResponse` and merges the
real value externally; this is not a stub, it is a documented seam.

## Self-Check: PASSED

Files created/modified verified on disk:

- `clawteam/cost/pricing.py` → FOUND
- `clawteam/cost/rollup.py` → FOUND
- `clawteam/cost/tracker.py` → FOUND
- `clawteam/cost/__init__.py` → MODIFIED (re-exports)
- `tests/cost/__init__.py` → FOUND
- `tests/cost/test_pricing.py` → FOUND
- `tests/cost/test_tracker.py` → FOUND

Commits verified in git log:

- `b3ec96e` (test 07-05 Task 1 RED) → FOUND
- `1a284a7` (feat 07-05 Task 1 GREEN) → FOUND
- `ad5f457` (test 07-05 Task 2 RED) → FOUND
- `79ebd3e` (feat 07-05 Task 2 GREEN) → FOUND

Acceptance grep checks:

- `grep -q "MODEL_PRICING" clawteam/cost/pricing.py` → OK
- `grep -q "def calculate_cost_usd" clawteam/cost/pricing.py` → OK
- `grep -q "class CostRollup" clawteam/cost/rollup.py` → OK
- `grep -q "class CostTracker" clawteam/cost/tracker.py` → OK

Verification command from plan:

- `pytest tests/cost/ -q` → **21 passed** in 0.07s.
- `python -c "from clawteam.cost import CostTracker, CostRollup,
  calculate_cost_usd; print('ok')"` → **ok**.

BC regression scope:

- `pytest tests/test_event_types_phase7.py tests/test_sprint_state.py
  tests/test_event_bus.py -q` → **55 passed** (Phase 7 substrate
  + prior events + bus unchanged).

## TDD Gate Compliance

Both tasks used TDD; RED commits preceded GREEN commits:

| Task | RED commit | GREEN commit | Gate pass |
|------|-----------|--------------|-----------|
| 1    | `b3ec96e` | `1a284a7`    | OK        |
| 2    | `ad5f457` | `79ebd3e`    | OK        |

Each RED commit was confirmed by running `pytest` and observing a
`ModuleNotFoundError` at collection time — this is a valid RED signal
(the test cannot pass because the production name doesn't exist yet;
the GREEN commit lands the module that makes the import succeed).

## Next Phase Readiness

Plan 07-05 (cost tracker) complete; Waves 4-5 remaining in Phase 7:

- **07-06** — `cost/fallback.py` (opus → sonnet → haiku ladder driven by
  tracker spend_percent) + `cost/cache_tracker.py` (ClaudeApiResponse
  subscriber populating cache_hit_rate).
- **07-07** — `clawteam team show` cost panel reading rollup_team /
  rollup_by_agent / rollup_by_sprint + 50/80/100 banner on
  BudgetAlarmReached.
- **07-08** — `clawteam doctor --gc` zombie worktree cleanup
  (emits ZombieWorktreeGced).
- **07-09** — 10-sprint integration load test (D-14/15/16).

All three new top-level Phase 7 packages (`attention/`, `cost/`,
`rate_limit/`) now have public APIs landing; `cost/` has 3 of its 4
modules in place (pricing + rollup + tracker) with fallback +
cache_tracker following in Plan 07-06.

---
*Phase: 07-parallel-sprints-attentionqueue-ux-cost-controls*
*Plan: 05 (Wave 4 part 1 — cost tracker)*
*Completed: 2026-04-22*
