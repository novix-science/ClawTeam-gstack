---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 01
subsystem: substrate
tags:
  - substrate
  - pyproject-extra
  - event-registration
  - template-config
  - sprint-state-extension
requires:
  - clawteam.events.bus.register_event_type
  - clawteam.sprint.state.SprintState (Phase 2/4)
  - clawteam.templates.TemplateDef (Phase 5/6 sub-block precedent)
provides:
  - clawteam.attention package marker (Wave 1/4 targets)
  - clawteam.cost package marker (Wave 3 targets)
  - clawteam.rate_limit package marker (Plan 07-02 target)
  - ToolCallCompleted / ClaudeApiResponse / BudgetAlarmReached /
    RateLimitSaturated / ZombieWorktreeGced / DormancyTransition events
  - SprintState.queue_status additive field
  - ConductorConfig / AttentionConfig / CostConfig pydantic models
  - TemplateDef.conductor / .attention / .cost optional fields
  - pyproject.toml [attend] optional-dependencies extra
affects:
  - Plan 07-02 (SprintConductor — consumes queue_status + ConductorConfig +
    RateLimitSaturated)
  - Plan 07-03 / 07-04 (AttentionQueue — lands in clawteam/attention/)
  - Plan 07-05 (CostTracker — emits ToolCallCompleted + BudgetAlarmReached;
    reads CostConfig)
  - Plan 07-06 (clawteam team show — surfaces BudgetAlarmReached banners)
  - Plan 07-09 (doctor --gc — emits ZombieWorktreeGced)
tech-stack:
  added:
    - watchdog>=3,<4 (optional, via [attend] extra)
  patterns:
    - Strict-additive pydantic field extension (Phase 5/6 precedent)
    - Open-str queue_status (not Literal) for future extensibility
    - Top-level TOML sub-block (NOT under [template]) — matches Phase 5/6
      [ship]/[memory]/[browser] precedent
    - register_event_type late-import block at module bottom
key-files:
  created:
    - clawteam/attention/__init__.py
    - clawteam/cost/__init__.py
    - clawteam/rate_limit/__init__.py
    - tests/test_event_types_phase7.py
    - tests/test_sprint_state_queue_status.py
    - tests/test_template_def_phase7_blocks.py
  modified:
    - pyproject.toml (APPEND [attend] extra)
    - clawteam/events/types.py (APPEND 6 dataclasses + 6 register calls)
    - clawteam/sprint/state.py (APPEND queue_status field)
    - clawteam/templates/__init__.py (APPEND 3 config models +
      3 TemplateDef fields + _parse_toml lookups)
    - tests/test_pyproject_optional_extras.py (APPEND 3 test functions)
decisions:
  - queue_status is open str (not Literal) — future queue reasons
    (e.g. 'queued_disk_budget') don't require schema migration
  - 6 new events placed before the late-import register_event_type block;
    calls appended AFTER existing Phase 6 block (additive pattern)
  - ConductorConfig/AttentionConfig/CostConfig at TOP LEVEL of TOML
    (raw.get) matching Phase 5/6 precedent — NOT under [template]
  - All 3 new TemplateDef fields default to None so 6 packaged templates +
    gstack.toml parse unchanged (parametrized BC test locks)
  - attention package lives at top level (not under templates/gstack/)
    because the substrate is generic — a non-gstack template could read
    its own question/answer artifact layout
metrics:
  duration: "~25min"
  tasks_completed: 4
  tests_added: 41 (5 pyproject + 14 events + 5 sprint-state + 17 template)
  files_created: 6
  files_modified: 5
  completed: "2026-04-22T20:35:00Z"
---

# Phase 7 Plan 01: Wave 0 Substrate Summary

**One-liner:** Lay the foundation for Phase 7 Waves 1–5 — new [attend] optional
extra, 3 new top-level packages (attention/cost/rate_limit), 6 new
HarnessEvent dataclasses, an additive SprintState.queue_status field, and 3
new optional TemplateDef sub-blocks ([conductor]/[attention]/[cost]).

## What Was Built

**Task 1 — pyproject [attend] extra + 3 new package skeletons.**
`pyproject.toml` gains an optional `attend = ["watchdog>=3,<4"]` extra (dev/p2p/
browser extras explicitly unchanged — parametrized regression locks). Three
new top-level packages (`clawteam/attention/`, `clawteam/cost/`,
`clawteam/rate_limit/`) ship with package markers and `__all__: list[str] = []`
so importing them has zero side effects. Waves 1–5 drop their public API in
each. **5 tests green.**

**Task 2 — Six new HarnessEvent dataclasses + register_event_type.**
`clawteam/events/types.py` gains `ToolCallCompleted` (D-09 cost tracker input),
`ClaudeApiResponse` (D-12 cache-hit metadata), `BudgetAlarmReached` (D-10
threshold crossing), `RateLimitSaturated` (D-13 429 backpressure),
`ZombieWorktreeGced` (SC #10 worktree GC), `DormancyTransition` (QUALITY-04
agent dormancy). All 6 are registered via `register_event_type` at module
bottom AFTER the Phase 6 block. Phase 6 events still resolvable (regression
lock). **14 tests green** (isinstance × 6 + defaults + emit round-trip × 6 +
registry visibility + Phase 6 BC).

**Task 3 — SprintState.queue_status additive field.**
`clawteam/sprint/state.py` gains `queue_status: str = Field(default="", ...)`.
Open `str` type (not Literal) keeps the field extensible for future queue
reasons without a schema migration. `""` = active/running; `'queued_capacity'`
= D-02 capacity timeout; `'rate_limit_saturated'` = D-13 429 backpressure.
Persists via the existing `file_locked` + `atomic_write_text` path unchanged.
**5 tests green** — default empty, round-trip for 2 non-empty values, legacy
state.json without `queue_status` key loads with default, coexistence with
all Phase 2/4 additive fields.

**Task 4 — TemplateDef [conductor]/[attention]/[cost] sub-blocks.**
`clawteam/templates/__init__.py` gains `ConductorConfig` (D-01/02/03 — sprint
concurrency caps), `AttentionConfig` (D-05 — AttentionQueue priority weights),
`CostConfig` (D-10 — budget + fallback ladder + alarm thresholds). All three
land as TOP-LEVEL TOML blocks (matching Phase 5/6 precedent — NOT under
`[template]`). `TemplateDef.conductor` / `.attention` / `.cost` default to
`None` so gstack.toml + all 6 packaged templates parse unchanged
(parametrized BC locks on all 6 names). `_parse_toml` appends 3 raw lookups +
3 kwarg passes after the Phase 6 block. **17 tests green** (1 gstack BC + 6
packaged BC + conductor block parsing + attention block parsing + cost block
parsing + validation rejections + Phase 5/6/7 coexistence).

## Verification

Plan 07-01 scoped suites:
```
pytest tests/test_pyproject_optional_extras.py tests/test_event_types_phase7.py \
       tests/test_sprint_state_queue_status.py tests/test_template_def_phase7_blocks.py
→ 41 passed
```

Backward-compatibility regression scope:
```
pytest tests/test_event_types_phase{2,4,5,6}.py tests/test_event_bus.py \
       tests/test_sprint_state.py tests/test_template_def_phase6_blocks.py \
       tests/test_template_def_extensions.py tests/test_template_regression_matrix.py \
       tests/test_templates.py
→ 180 passed
```

Integration smoke:
```
python -c "from clawteam.events.types import ToolCallCompleted, ClaudeApiResponse, \
BudgetAlarmReached, RateLimitSaturated, ZombieWorktreeGced, DormancyTransition; \
from clawteam.templates import ConductorConfig, AttentionConfig, CostConfig; \
import clawteam.attention, clawteam.cost, clawteam.rate_limit; print('imports ok')"
→ imports ok
```

## Acceptance Criteria

- [x] `grep -q 'attend = \[' pyproject.toml` → present
- [x] `grep -q 'watchdog>=3,<4' pyproject.toml` → present
- [x] `clawteam/{attention,cost,rate_limit}/__init__.py` exist
- [x] 6 new events registered + resolvable via `resolve_event_type`
- [x] Phase 6 events still resolvable (no regression)
- [x] `grep -q "queue_status: str" clawteam/sprint/state.py` → present
- [x] Legacy state.json (no queue_status key) loads with default `""`
- [x] `ConductorConfig` / `AttentionConfig` / `CostConfig` present
- [x] gstack.toml + 6 packaged templates parse with 3 new fields = None
- [x] All 4 task acceptance criteria met
- [x] 6 new events register on module import
- [x] 3 new top-level packages importable
- [x] Existing state.json files + template .toml files parse unchanged

## Commits

**Task 1 (pyproject [attend] + 3 packages):**
- `88c4bca` test(07-01): add failing tests for attend extra + 3 new packages (Task 1 RED)
- `b8e06f3` feat(07-01): add [attend] extra + 3 substrate packages (Task 1 GREEN)

**Task 2 (6 HarnessEvent dataclasses):**
- `f610a3c` test(07-01): add failing tests for 6 new Phase 7 events (Task 2 RED)
- `9b34c22` feat(07-01): register 6 new Phase 7 events (Task 2 GREEN)

**Task 3 (SprintState.queue_status):**
- `7ed0900` test(07-01): add failing tests for SprintState.queue_status (Task 3 RED)
- `b7732db` feat(07-01): add SprintState.queue_status additive field (Task 3 GREEN)

**Task 4 (TemplateDef Phase 7 sub-blocks):**
- `6249f02` test(07-01): add failing tests for TemplateDef Phase 7 sub-blocks (Task 4 RED)
- `3defade` feat(07-01): add TemplateDef [conductor]/[attention]/[cost] sub-blocks (Task 4 GREEN)

## Deviations from Plan

**None.** Plan executed exactly as written — all 4 tasks, all RED→GREEN gates
preserved. One minor elaboration tracked in decisions above: `attention` sub-
block in TOML uses `[attention.tag_weights]` subtable for the `dict[str, int]`
field (TOML syntax constraint — inline `{...}` dicts only support literal
values, not nested tables; subtable syntax is standard). Test exercises both
scalar fields and the subtable without needing any schema change.

## Interfaces for Downstream Plans

**Plan 07-02 (SprintConductor concurrency):**
- Reads `state.queue_status` + sets it to `'queued_capacity'` / `''`
- Reads `tmpl.conductor.max_concurrent_sprints` / `max_tasks_per_agent` /
  `max_active_agents` / `acquire_timeout_seconds`
- Consults `RateLimitMonitor.is_saturated()` then sets
  `queue_status='rate_limit_saturated'` if true
- Emits `RateLimitSaturated(...)` when 429 threshold crossed

**Plans 07-03 / 07-04 (AttentionQueue + watcher):**
- Drops code under `clawteam/attention/` (adds to `__all__`)
- Reads `tmpl.attention.urgency_weight` / `blocking_weight` / `tag_weights`
- Feature-detects `watchdog` via `find_spec` (same pattern as 06-01 browser)

**Plan 07-05 (CostTracker):**
- Drops code under `clawteam/cost/` (adds to `__all__`)
- Reads `tmpl.cost.budget_usd` / `fallback_at_percent` / `alarm_percent`
- Emits `ToolCallCompleted` from `invoke_native_cli` wrapper
- Emits `ClaudeApiResponse` (cache metrics) + `BudgetAlarmReached` on
  threshold crossings

**Plan 07-09 (doctor --gc):**
- Emits `ZombieWorktreeGced(path=..., age_days=..., freed_bytes=...)` per
  cleaned worktree

## Known Stubs

**None** — this is pure substrate; every file lands with its intended final
shape for Phase 7 Wave 0 and has no placeholder data paths. `__all__` lists
in the 3 new packages are intentionally empty (Waves 1–5 append).

## Self-Check: PASSED

- `clawteam/attention/__init__.py` → FOUND
- `clawteam/cost/__init__.py` → FOUND
- `clawteam/rate_limit/__init__.py` → FOUND
- `tests/test_event_types_phase7.py` → FOUND
- `tests/test_sprint_state_queue_status.py` → FOUND
- `tests/test_template_def_phase7_blocks.py` → FOUND
- commits `88c4bca` / `b8e06f3` / `f610a3c` / `9b34c22` / `7ed0900` /
  `b7732db` / `6249f02` / `3defade` → FOUND (8 commits, all in current branch)

## TDD Gate Compliance

All 4 tasks used TDD:

| Task | RED commit | GREEN commit | Gate pass |
|------|-----------|--------------|-----------|
| 1    | 88c4bca   | b8e06f3      | ✓         |
| 2    | f610a3c   | 9b34c22      | ✓         |
| 3    | 7ed0900   | b7732db      | ✓         |
| 4    | 6249f02   | 3defade      | ✓         |

Each RED commit confirmed by running `pytest` against the failing suite
before the GREEN implementation landed. Import-error failures (Tasks 2, 4)
count as RED gate signals — the tests cannot pass until the production code
exposes the missing names.
