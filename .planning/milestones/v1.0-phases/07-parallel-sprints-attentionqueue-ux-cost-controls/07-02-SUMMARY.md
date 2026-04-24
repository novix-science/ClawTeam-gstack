---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 02
subsystem: concurrency
tags:
  - asyncio-semaphore
  - rate-limiting
  - sprint-conductor-extension
  - sliding-window
  - dormancy-discipline
requires:
  - phase: 07-01
    provides: >-
      ConductorConfig (max_concurrent_sprints/max_tasks_per_agent/
      max_active_agents/acquire_timeout_seconds), SprintState.queue_status
      open-str field, RateLimitSaturated + DormancyTransition HarnessEvents,
      clawteam/rate_limit/ package marker
  - phase: 02
    provides: SprintConductor sync start_sprint (BC floor)
  - phase: 04
    provides: EventBus.emit + subscribe mechanics
provides:
  - RateLimitMonitor (60s sliding 429-bucket window, threshold=3 default)
  - SprintConductor.start_sprint_async (async sprint entry)
  - SprintConductor._sprint_sem / _active_agent_sem / _per_agent_sems (3 caps)
  - SprintConductor.dispatch_turn async context manager (per-agent + active-agent gate)
  - SprintConductor.active_agents() accessor (QUALITY-04)
  - SprintConductor.release_sprint_slot(sprint_id) idempotent release
  - SprintConductor._resolve_conductor_config helper (template lookup)
  - SprintConductor._emit_dormancy helper (DormancyTransition emission)
  - RateLimitSaturated auto-emit on threshold-cross (exactly-once per rearm cycle)
affects:
  - Plan 07-03 (AttentionQueue — may read active_agents() for dormant-agent work selection)
  - Plan 07-05 (CostTracker — may consult start_sprint_async queue_status for throttle coordination)
  - Plan 07-09 (10-sprint load test — exercises all 3 caps + rate-limit queuing)
  - Phase 5 skill handlers (may await dispatch_turn around agent-owned tool calls)
tech-stack:
  added: []  # No new external deps; uses stdlib asyncio + threading + deque
  patterns:
    - asyncio.Semaphore + asyncio.wait_for(timeout=...) for bounded acquire
    - "Dual-lock pattern: asyncio.Semaphore for coroutine fairness + threading.RLock for thread-safe state mutation (active_agents_set, rate-limit deque)"
    - Lazy-import in __init__ to break module-load cycles (ConductorConfig/RateLimitMonitor imported inside __init__ body)
    - Deque-based sliding window (append-now, popleft-until-cutoff) for O(1) amortized record + expire
    - "Context-manager dispatch_turn: async with ensures release on exception + DormancyTransition symmetry"
    - Rearm-after-expiry pattern (saturated flag auto-clears when window drains) — re-emits on next threshold cross
key-files:
  created:
    - clawteam/rate_limit/monitor.py
    - tests/rate_limit/__init__.py
    - tests/rate_limit/test_monitor.py
    - tests/sprint/__init__.py
    - tests/sprint/test_conductor_concurrency.py
  modified:
    - clawteam/rate_limit/__init__.py (re-export RateLimitMonitor)
    - clawteam/sprint/conductor.py (+147 LOC — 3 semaphores, async entry, dispatch_turn, active_agents, rate-limit monitor wiring)
key-decisions:
  - "RateLimitMonitor uses threshold-strict comparison (count > threshold, not >=) — matches plan behavior spec Test 2 (one 429 with threshold=3 is NOT saturated; threshold+1=4 IS)"
  - "Sprint semaphore acquire timeout failure writes queue_status='queued_capacity' then creates a sprint in non-acquired state — does not raise — so callers can branch on state.queue_status instead of catching TimeoutError"
  - "Rate-limit saturation ALSO creates a sprint with queue_status='rate_limit_saturated' (never attempts sem.acquire) — symmetric with queued_capacity path for downstream consumers"
  - "dispatch_turn acquires per-agent sem FIRST, then active-agent sem — per-agent is usually cheaper (no shared contention) and failure after active-agent acquire would need compensating release; ordering minimizes rollback surface"
  - "Per-agent semaphore dict built lazily at first dispatch_turn(role) — no upfront iteration over all 11 gstack roles; memory proportional to roles actually dispatched"
  - "_resolve_conductor_config falls back to ConductorConfig() defaults if TeamManager.get_team raises or template.conductor is None — conductor never crashes on missing/broken team config (defensive pattern from Phase 3 SprintConductor)"
  - "RateLimitMonitor self-heals in is_saturated() (clears _was_saturated when window drains) — caller never has to call a rearm() method; next threshold cross triggers fresh emission"
  - "Emit-on-threshold-cross (not emit-every-record) — RateLimitSaturated fires exactly once per un-saturated→saturated transition; re-fires only after window clears + re-crosses"
patterns-established:
  - "SprintConductor async-path-alongside-sync pattern: new start_sprint_async sits beside existing start_sprint; both reuse core state creation via shared call to sync start_sprint — BC preservation without code duplication"
  - "Sliding-window detector pattern (provider-agnostic): caller feeds events via record_*; detector exposes is_saturated() + recent_*_count() + event emission on threshold cross. Reusable for future detectors (e.g., error-rate, cost-spike)"
  - "Cross-lock discipline: asyncio.Semaphore guards coroutine ordering, threading.RLock guards shared mutable state — never hold both simultaneously (active_agents_set mutation inside async ctx manager body happens under threading.RLock only, semaphore already acquired)"
requirements-completed:
  - CORE-06
  - QUALITY-04

duration: 7min
completed: 2026-04-22
---

# Phase 7 Plan 07-02: Conductor Concurrency Summary

**`SprintConductor` gains 3 asyncio.Semaphore caps (sprint=10, per-agent=1, active-agent=6), `start_sprint_async` with rate-limit consultation, `dispatch_turn` async context manager, `active_agents()` accessor, and `RateLimitMonitor` with 60s sliding 429-bucket window + exactly-once event emission.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-22T12:55:09Z (fa7a8fe RED)
- **Completed:** 2026-04-22T13:02:18Z (b72ce71 GREEN)
- **Tasks:** 2 (both TDD)
- **Files modified:** 7 (3 new src, 4 new/modified test infra)

## Accomplishments

- `RateLimitMonitor` with 60-second sliding 429 bucket — threshold-strict saturation (count > 3), exactly-once `RateLimitSaturated` emission on threshold cross, self-healing rearm after window drain
- `SprintConductor.start_sprint_async` — consults `is_saturated()` first, then acquires `_sprint_sem` with `asyncio.wait_for(timeout=acquire_timeout_seconds)`; on saturation or timeout writes `SprintState.queue_status` and returns without blocking
- `SprintConductor.dispatch_turn(role, name)` async context manager — acquires per-agent + active-agent semaphores, registers agent in `_active_agents_set` under `threading.RLock`, emits `DormancyTransition` on both enter and exit
- `SprintConductor.active_agents()` accessor — returns sorted list of currently-active agent names (QUALITY-04 sensor)
- `_resolve_conductor_config` helper — layered lookup: team config → template → `ConductorConfig()` defaults (defensive never-crash)
- BC preserved: existing sync `start_sprint` path untouched; 35 pre-existing sprint tests still green (0 regressions)

## Task Commits

1. **Task 1 RED: RateLimitMonitor spec** — `fa7a8fe` (test)
2. **Task 1 GREEN: RateLimitMonitor 60s sliding window** — `e8660e7` (feat)
3. **Task 2 RED: SprintConductor concurrency spec** — `7beccbc` (test)
4. **Task 2 GREEN: 3-semaphore caps + async entry** — `b72ce71` (feat)

**Plan metadata commit:** this SUMMARY + STATE + ROADMAP update will land as `docs(07-02): complete conductor-concurrency plan`.

_TDD gates preserved per task: RED commit first (failing test), GREEN commit second (minimal implementation to pass). No REFACTOR commits needed — implementation was already minimal._

## Files Created/Modified

**Created:**

- `clawteam/rate_limit/monitor.py` (107 LOC) — `RateLimitMonitor` class with `record_429()`, `is_saturated()`, `recent_429_count()`, threadsafe via `threading.RLock`, event emission via injected `EventBus`
- `tests/rate_limit/__init__.py` — package marker
- `tests/rate_limit/test_monitor.py` (132 LOC, 8 tests) — fresh/one-429/threshold-cross/window-expiry/emit-on-cross/re-saturation/custom-knobs/thread-safe
- `tests/sprint/__init__.py` — package marker
- `tests/sprint/test_conductor_concurrency.py` (155 LOC, 8 tests) — sync BC / async happy / queued-capacity / rate-limit-saturated / empty-active / per-agent-serializes / active-agent-cap / dormancy-events

**Modified:**

- `clawteam/rate_limit/__init__.py` — re-exports `RateLimitMonitor`, `__all__ = ["RateLimitMonitor"]`
- `clawteam/sprint/conductor.py` (+147 LOC) — `__init__` accepts `conductor_config=` + `rate_limit_monitor=` kwargs; builds 3 semaphores + per-agent dict + active-agents set; adds `_resolve_conductor_config`, `start_sprint_async`, `release_sprint_slot`, `_get_agent_sem`, `dispatch_turn` (async ctx mgr), `active_agents`, `_emit_dormancy`

## Decisions Made

See frontmatter `key-decisions` for all 8 decisions with rationale. Highlights:

- **Threshold-strict saturation** (`count > threshold`, not `>=`) — matches plan Test 2 exactly
- **Queue-status-over-exception** for sprint overflow — callers branch on `state.queue_status` string rather than catching `asyncio.TimeoutError`
- **Per-agent sem lazy init** — only roles actually dispatched consume memory
- **Emit-on-cross-only + self-healing rearm** — `RateLimitSaturated` fires exactly once per un-saturated→saturated transition

## Deviations from Plan

None — plan executed exactly as written. Task 1 landed 8-of-8 tests green on first GREEN commit; Task 2 landed 8-of-8 tests green on first GREEN commit. No auto-fixes (Rules 1-3) needed. No architectural questions (Rule 4) raised.

## Issues Encountered

None. Both TDD cycles (Task 1 RED→GREEN, Task 2 RED→GREEN) landed cleanly. No pytest flakiness, no cross-executor stash interactions (this was a serial-executed plan, not a parallel-wave plan).

## Verification Evidence

```bash
# Plan's <verification> block:
$ pytest tests/rate_limit/ tests/sprint/test_conductor_concurrency.py tests/test_sprint_conductor.py tests/sprint/ -q
...................................................                      [100%]
51 passed

# Plan's inline Python smoke:
$ python -c "import asyncio; from clawteam.sprint.conductor import SprintConductor; \
             from clawteam.templates import ConductorConfig; \
             c = SprintConductor('t1', conductor_config=ConductorConfig()); print(c.active_agents())"
[]

# Plan's rate-limit smoke:
$ python -c "from clawteam.rate_limit import RateLimitMonitor; print('ok')"
ok

# Grep-based acceptance (all hits present):
$ grep -c "start_sprint_async\|active_agents\|_sprint_sem\|_rate_limit_monitor" clawteam/sprint/conductor.py
17
$ grep -c "class RateLimitMonitor" clawteam/rate_limit/monitor.py
1
```

All 6 acceptance criteria (3 per task) pass. 16 new plan-scoped tests + 35 BC sprint tests = 51 total green.

## User Setup Required

None — no external service configuration required. Plan is pure-Python substrate.

## Next Phase Readiness

**Ready for:**

- Plan 07-03 (AttentionQueue) — can consult `conductor.active_agents()` to select dormant agents for batched work pickup
- Plan 07-05 (CostTracker) — can wire `invoke_native_cli` responses into `RateLimitMonitor.record_429()` via a new method on the tracker
- Plan 07-09 (10-sprint load test) — substrate is complete; load test can drive 10 parallel `start_sprint_async` calls and assert 11th queues with `queue_status='queued_capacity'`

**Known non-blockers (documented, not bugs):**

- `release_sprint_slot` is a no-op API surface — Phase 2-6 callers never invoke it; Plan 07-09 load test will exercise it as sprints reach reflect-phase. The idempotent `ValueError` swallow means double-release is harmless.
- `start_sprint_async` does NOT release the semaphore itself on completion — the sprint lifecycle owner (caller) is responsible for calling `release_sprint_slot(sprint_id)` when the sprint transitions out of active phases. This matches the plan's D-01 intent: "sprint slot held for sprint duration, released on reflect/pause".

## Self-Check: PASSED

All frontmatter-declared deliverables verified on disk:

- `clawteam/rate_limit/monitor.py` — FOUND (107 LOC)
- `clawteam/rate_limit/__init__.py` — FOUND (re-exports `RateLimitMonitor`)
- `tests/rate_limit/test_monitor.py` — FOUND (132 LOC, 8 tests pass)
- `tests/sprint/test_conductor_concurrency.py` — FOUND (155 LOC, 8 tests pass)
- `clawteam/sprint/conductor.py` — MODIFIED (+147 LOC, grep confirms `start_sprint_async`, `active_agents`, `_sprint_sem`, `_rate_limit_monitor`)

All commits verified in git log:

- `fa7a8fe` — FOUND (test Task 1 RED)
- `e8660e7` — FOUND (feat Task 1 GREEN)
- `7beccbc` — FOUND (test Task 2 RED)
- `b72ce71` — FOUND (feat Task 2 GREEN)

TDD gate compliance: PASSED — RED commit precedes GREEN commit for each of Task 1 and Task 2.

---

*Phase: 07-parallel-sprints-attentionqueue-ux-cost-controls*
*Completed: 2026-04-22*
