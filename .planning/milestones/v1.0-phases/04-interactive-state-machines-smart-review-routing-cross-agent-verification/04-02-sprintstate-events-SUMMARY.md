---
phase: 04
plan: 02
subsystem: sprint-state + event-substrate
tags: [substrate, pydantic, dataclass, additive, tdd]
dependency_graph:
  requires: [Phase 1 SprintState, Phase 2 HarnessEvent dataclass convention, Phase 2 additive-field pattern]
  provides:
    - "clawteam.sprint.state.SprintState.review_sha: str | None"
    - "clawteam.events.types.MidReviewThrash dataclass"
    - "clawteam.events.types.SycophancyCascadeDetected dataclass"
  affects: []
tech_stack:
  added: []
  patterns: ["additive-pydantic-field (BC-safe)", "@dataclass(HarnessEvent) subclass", "TDD RED-GREEN"]
key_files:
  created:
    - tests/test_event_types_phase4.py
  modified:
    - clawteam/sprint/state.py
    - clawteam/events/types.py
    - tests/test_sprint_state.py
decisions:
  - "review_sha field is permissive str|None (no min_length). ReviewReport schema handles stricter SHA validation downstream — SprintState stays a plain data carrier."
  - "MidReviewThrash + SycophancyCascadeDetected placed at end-of-file after Phase 2 events. Ordering preserved for import stability."
  - "Both new event dataclasses use field(default_factory=list) for mutable defaults (T-04-06 mitigation)."
metrics:
  duration: "~7 minutes"
  completed: "2026-04-21"
  tasks_completed: 2
  commits: 4
  files_touched: 4
  new_tests: 10
---

# Phase 4 Plan 02: SprintState + Events Substrate Summary

## One-liner

Shipped two zero-consumer substrate additions — `SprintState.review_sha: str | None = None` (D-05) and two `@dataclass(HarnessEvent)` events `MidReviewThrash` (D-19) + `SycophancyCascadeDetected` (D-09/D-20) — via additive TDD with full BC for pre-Phase-4 state.json payloads.

## Completed Tasks

### Task 1: Add `review_sha` field to `SprintState` (TDD)

- **Files:** `clawteam/sprint/state.py`, `tests/test_sprint_state.py`
- **RED commit:** `e90d96a` — 4 failing tests asserting `AttributeError: 'SprintState' object has no attribute 'review_sha'`
- **GREEN commit:** `b71ce96` — additive pydantic field at `clawteam/sprint/state.py:108-122` (15 lines added)
- **Field shape:** `review_sha: str | None = Field(default=None, description=...)`
- **Line range added in `state.py`:** lines 108-122 (comment block + field declaration)

### Task 2: Add `MidReviewThrash` + `SycophancyCascadeDetected` (TDD)

- **Files:** `clawteam/events/types.py`, `tests/test_event_types_phase4.py` (new)
- **RED commit:** `9ad8ac4` — 6 failing tests, `ImportError: cannot import name 'MidReviewThrash'`
- **GREEN commit:** `b140c3f` — two `@dataclass` subclasses appended at `clawteam/events/types.py:281-323` (43 lines added)
- **Line ranges added in `types.py`:** lines 283-306 (MidReviewThrash) and lines 308-323 (SycophancyCascadeDetected)
- Both classes subclass `HarnessEvent`, inherit `team_name` and `timestamp`, use `field(default_factory=list)` for every mutable default (T-04-06 mitigation verified by `test_default_field_values`).

## Commits (chronological, newest last)

| SHA       | Type         | Message                                                                                |
| --------- | ------------ | -------------------------------------------------------------------------------------- |
| `e90d96a` | `test(04-02)` | add failing tests for SprintState.review_sha additive field                            |
| `b71ce96` | `feat(04-02)` | add SprintState.review_sha additive field                                              |
| `9ad8ac4` | `test(04-02)` | add failing tests for MidReviewThrash + SycophancyCascadeDetected                      |
| `b140c3f` | `feat(04-02)` | add MidReviewThrash + SycophancyCascadeDetected event dataclasses                      |

All four commits are scoped strictly to the four files in `files_modified`. No prompt files, no `conductor.py`, no `plugins/base.py` were touched.

## Files Modified

| Path                                | Change                                                                   | Lines added |
| ----------------------------------- | ------------------------------------------------------------------------ | ----------- |
| `clawteam/sprint/state.py`          | +1 additive pydantic field `review_sha` (after `careful_enabled`)        | +15         |
| `clawteam/events/types.py`          | +2 `@dataclass(HarnessEvent)` subclasses at EOF (after Phase 2 events)   | +43         |
| `tests/test_sprint_state.py`        | +4 round-trip / BC / default / full-SHA tests                            | +49         |
| `tests/test_event_types_phase4.py`  | new file: 6 construction/emit/default-value tests                        | +96 (new)   |

`git diff` for both source files shows **additions only** (0 deletions); existing Phase 1/2/3 fields and event classes are untouched.

## Test Results

```
pytest tests/test_sprint_state.py         → 24 passed   (20 existing + 4 new)
pytest tests/test_event_types_phase4.py   →  6 passed   (all new)
pytest tests/test_event_types_phase2.py   → 22 passed   (0 regressions)
pytest tests/test_event_bus.py            →  5 passed   (0 regressions)
pytest tests/test_sprint_conductor.py     → 27 passed   (0 regressions)
```

Full combined run: **84 passed, 0 failed, 0 errors** across `sprint_state + event_types_phase4 + event_types_phase2 + event_bus + sprint_conductor`.

## Acceptance Criteria (all met)

- [x] `grep -q "review_sha: str | None = Field" clawteam/sprint/state.py` → present at line 113
- [x] `grep -c "class MidReviewThrash\|class SycophancyCascadeDetected" clawteam/events/types.py` → **2**
- [x] `grep -c "review_sha:" clawteam/sprint/state.py` → **1** (exactly one new field declaration; the two other matches earlier are only in the docstring body)
- [x] All 10 new tests pass
- [x] Phase 2 regression suite stays green (22 + 27 + 5)

## Must-Haves (all satisfied)

- [x] `SprintState` round-trips `review_sha: str | None = None` through save/load (test_review_sha_round_trip)
- [x] `clawteam.events.types` exports `MidReviewThrash` and `SycophancyCascadeDetected` as `@dataclass(HarnessEvent)` subclasses
- [x] `EventBus.emit(MidReviewThrash(team_name='t', sprint_id='s', ...))` returns a list without raising (test_mid_review_thrash_emit_round_trip)
- [x] Existing state.json files without review_sha key load cleanly with None default (test_review_sha_backwards_compat)

## Deviations from Plan

**None.** Plan executed exactly as written. No Rule 1/2/3 auto-fixes required, no Rule 4 architectural decisions surfaced, no auth gates encountered.

**Note on test file existence:** The plan's Task 1 action said "Create `tests/test_sprint_state.py` IF it does not already exist … If it exists, APPEND the four tests." The file already exists (20 prior tests), so the four new tests were appended at EOF per plan instruction.

## Next-Wave Dependencies Satisfied

| Consumer plan | Import / read surface provided                                                        |
| ------------- | ------------------------------------------------------------------------------------- |
| Plan 04       | `state.review_sha` readable on load                                                   |
| Plan 10       | `state.review_sha` pin-point at Review-phase entry; `from clawteam.events.types import MidReviewThrash, SycophancyCascadeDetected` now resolves |
| Plan 11       | `state.review_sha` readable for cross-verifier diff scoping                           |
| Phase 7 (attend --summary) | `SycophancyCascadeDetected` type available for cross-sprint digest     |

All Wave 2 state machines and Wave 3 orchestrators can now import the event types without conditional feature-flag dances (objective achieved).

## Threat Flags

None. The three threats in `<threat_model>` (T-04-04 Tampering, T-04-05 Info-disclosure, T-04-06 DoS) are each `accept` or `mitigate`-satisfied:

- **T-04-04** (accept): `review_sha` is a plain string field — downstream `git rev-parse` in Plan 10 validates before trust.
- **T-04-05** (accept): `diff_paths_added/removed` contain workspace-relative paths already visible in `git log`; no PII.
- **T-04-06** (mitigate — **enforced**): Every mutable list default on the two new dataclasses uses `field(default_factory=list)`. `test_default_field_values` asserts fresh instances have empty separate lists (not shared references).

No new trust boundaries introduced beyond those listed in the plan.

## Known Stubs

None. This plan is pure substrate — the two events have no emitters and the field has no reader until Plan 10 wires them. This is explicitly by design per the plan objective: "zero-consumer substrate additions. No behavior changes until Plan 10 emits the events and Plan 04+11 read the field."

## Self-Check: PASSED

- [x] `clawteam/sprint/state.py` contains `review_sha: str | None = Field` at line 113
- [x] `clawteam/events/types.py` contains `class MidReviewThrash(HarnessEvent)` at line 287 and `class SycophancyCascadeDetected(HarnessEvent)` at line 308
- [x] `tests/test_event_types_phase4.py` exists (96 lines)
- [x] Commit `e90d96a` exists (test RED Task 1)
- [x] Commit `b71ce96` exists (feat GREEN Task 1)
- [x] Commit `9ad8ac4` exists (test RED Task 2)
- [x] Commit `b140c3f` exists (feat GREEN Task 2)
- [x] `pytest tests/test_sprint_state.py tests/test_event_types_phase4.py -q` → 30 passed
