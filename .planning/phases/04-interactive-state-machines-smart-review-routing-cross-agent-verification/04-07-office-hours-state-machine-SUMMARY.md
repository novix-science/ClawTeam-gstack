---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
plan: 07
subsystem: skills
tags: [pydantic, state-machine, office-hours, persistence, forcing-questions, file-locked, atomic-write]

# Dependency graph
requires:
  - phase: 02-sprint-engine
    provides: file_locked + atomic_write_text persistence primitives, SprintState convention
  - phase: 04 Plan 01
    provides: D-01/D-02/D-03 state-machine architecture decisions (pydantic transition table, per-role state.json path)
  - phase: 04 Plan 02
    provides: PLAN_PREP_NOTES fixture-shape + turn-budget conventions
provides:
  - OfficeHoursState pydantic transition-table class (start → 6 forcing Qs → summary_written with abandon escape hatch)
  - tests/fixtures/gstack_state_machines/office-hours.transitions.json (canonical transition graph, 13 transitions, turn_budget=13)
  - clawteam/templates/gstack/skills/ package scaffolding (catalogs Phase-4 D-01 state machines)
  - Per-turn handle(event, turn) contract for SprintConductor pm dispatch (Plan 04-10)
affects: [04-10 sprint-conductor dispatch, 04-08 design_consultation pattern, 04-09 investigate pattern]

# Tech tracking
tech-stack:
  added: []  # All imports reuse existing clawteam primitives (fileutil, paths, team.models)
  patterns:
    - "Pydantic transition-table state machine with Literal-enum states + events + in-code _TRANSITIONS dict as single source of truth"
    - "Golden fixture JSON drives test_transitions_match_fixture bijection test — editing transitions requires updating BOTH code and fixture"
    - "Per-role skill state persistence under <data>/teams/<team>/sprints/<id>/skills/<skill>/<role>/state.json via file_locked + atomic_write_text (Phase 2 convention extended to interactive skills)"

key-files:
  created:
    - clawteam/templates/gstack/skills/__init__.py
    - clawteam/templates/gstack/skills/office_hours/__init__.py
    - clawteam/templates/gstack/skills/office_hours/state.py
    - tests/fixtures/gstack_state_machines/office-hours.transitions.json
    - tests/test_office_hours_state_machine.py
  modified: []

key-decisions:
  - "OfficeHoursState extends BaseModel with OHState/OHEvent Literal types; _TRANSITIONS dict is single source of truth (13 transitions); golden fixture test asserts bijection so drift is impossible"
  - "abandon event is special-cased outside _TRANSITIONS — usable from any non-final state without exploding the transition table by 14 extra rows"
  - "pending_question_id pointer synced on every transition via _sync_pending_question_id so plugin/router consumers know which Q is live without walking history"
  - "Persistence path nested under skills/office-hours/pm/ per D-02 (skill + role keyed) so future /office-hours-architect or multi-role extensions land without colliding"
  - "TURN_BUDGET = 13 exported as module constant (not just a fixture field) so Plan 04-10 conductor can check budget without re-reading JSON"

patterns-established:
  - "Pattern: Transition-table state machine as pydantic BaseModel with in-code _TRANSITIONS dict + golden-fixture JSON bijection test"
  - "Pattern: handle(event, turn) returns StateTransitionResult(ok, reason, new_state) so callers can log + branch without try/except"
  - "Pattern: Per-skill state path resolver validates identifiers + clamps under teams root (T-04-22 path-traversal mitigation, inherited from SprintState)"
  - "Pattern: Turn-budget constant exported as TURN_BUDGET: int = 13 — monologue-collapse regression check (Pitfall 7) becomes a single-line assertion"

requirements-completed: [QUALITY-07]

# Metrics
duration: 5min
completed: 2026-04-21
---

# Phase 4 Plan 07: Office Hours State Machine Summary

**OfficeHoursState pydantic transition-table class shipping 13-turn forcing-question Socratic loop with file_locked + atomic JSON persistence, CORE-07 restart-survival round-trip, and golden-fixture bijection so in-code transitions and fixture JSON drift together.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-21T10:21:59Z
- **Completed:** 2026-04-21T10:26:59Z
- **Tasks:** 2 (1 scaffolding, 1 TDD-gated implementation)
- **Files created:** 5

## Accomplishments

- Shipped `OfficeHoursState` pydantic BaseModel at `clawteam/templates/gstack/skills/office_hours/state.py` (213 LOC, >= 100 LOC acceptance floor) with `current_state`, `history`, `handle(event, turn)`, `save()`, `load()` public API
- Canonical transition graph fixture at `tests/fixtures/gstack_state_machines/office-hours.transitions.json` (13 transitions, 6 forcing questions, turn_budget=13, final_states=[summary_written, abandoned]) — golden source of truth
- Package scaffolding at `clawteam/templates/gstack/skills/__init__.py` + `skills/office_hours/__init__.py` re-exporting the public API catalog
- 14/14 tests green in `tests/test_office_hours_state_machine.py` including the golden `test_transitions_match_fixture` bijection + CORE-07 `test_persistence_survives_simulated_restart` round-trip
- Fixture + code transitions are bijective: code→fixture and fixture→code sets are equal under (from, event, to) triples

## Task Commits

Each task was committed atomically:

1. **Task 1: Scaffolding + fixture JSON** — `575ce57` (feat)
2. **Task 2 RED: failing tests** — `6992211` (test)
3. **Task 2 GREEN: OfficeHoursState implementation** — `2928ab1` (feat)

**Plan metadata commit:** (this SUMMARY.md + STATE.md updates land in a subsequent `docs(04-07): complete office-hours-state-machine plan` commit)

## Files Created/Modified

- `clawteam/templates/gstack/skills/__init__.py` — Package docstring cataloguing the three Phase-4 state machines (office_hours, design_consultation, investigate)
- `clawteam/templates/gstack/skills/office_hours/__init__.py` — Re-exports OfficeHoursState, OHEvent, OHState, StateTransitionResult, Transition
- `clawteam/templates/gstack/skills/office_hours/state.py` — 213 LOC: OHState/OHEvent Literal types, _TRANSITIONS dict (13 entries), FORCING_QUESTIONS list, TURN_BUDGET constant, OfficeHoursState BaseModel with handle/save/load + _state_path validator
- `tests/fixtures/gstack_state_machines/office-hours.transitions.json` — Golden transition graph (drives golden-fixture test, locks wire format for future regressions)
- `tests/test_office_hours_state_machine.py` — 14 pytest cases covering initial state, golden bijection, turn budget, final states, forcing questions, happy path 13-transition walk, invalid transition rejection, abandon escape, final-state lock, save/load round-trip, bad-identifier rejection, CORE-07 restart simulation, pending_question_id tracking

## Decisions Made

- **abandon event outside _TRANSITIONS** — Special-cased in `handle()` so the fixture stays a pure happy-path graph (13 entries, not 13 + 14 abandon edges) while still letting pm bail at any turn
- **pending_question_id as a synced field, not derived property** — Plugin + router consumers need the pointer on load without re-running a case statement; sync runs every transition via `_sync_pending_question_id`
- **Skill-keyed persistence path (`skills/office-hours/pm/state.json`)** — Matches D-02 layered keying so a future `/office-hours-architect` role (or parallel skill state) lands without colliding or requiring schema migration
- **TURN_BUDGET as module constant + fixture field** — Plan 04-10 conductor can gate by budget without re-loading JSON, and the golden test (`test_turn_budget_matches_fixture`) keeps code and fixture locked

## Deviations from Plan

None — plan executed exactly as written. The `OfficeHoursState` class, 13 transitions, turn budget 13, fixture shape, and all 11 named behavior tests (plus the 3 implicit golden-fixture checks and 1 bonus pending_question tracking test the plan sketched) landed verbatim against the plan's `<action>` block.

## Issues Encountered

- **gsd-sdk CLI not on PATH in this worktree** — Worked around by reading `.planning/STATE.md` directly and deferring state-bookkeeping calls (no blocker for plan execution, no plan-output impact). STATE.md will be hand-updated via the orchestrator's post-execution step; metrics in this SUMMARY are captured for the state-record-metric handler when it runs.
- **Full `pytest tests/` run reports 2 pre-existing flaky failures** (`test_gstack_plugin.py::test_six_evidence_schemas_registered` + `test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present`) only under a specific collection order. Both pass cleanly in isolation and are unrelated to this plan — likely triggered by `test_investigate_state_machine.py` collection-time import error (Plan 04-09 in-flight). Per SCOPE BOUNDARY: logged and out-of-scope for 04-07.

## Threat Flags

None — the plan's threat model covers T-04-21 (state.json tampering) and T-04-22 (path traversal), both mitigated in-code via file_locked + atomic_write_text and validate_identifier + ensure_within_root; T-04-23 (DoS via history growth) is accepted per turn_budget=13 cap. No new surface introduced.

## Next Phase Readiness

- `OfficeHoursState` is importable from `clawteam.templates.gstack.skills.office_hours` and ready for Plan 04-10 conductor wiring (per-turn `state.handle(event, turn=conductor_turn_counter)` + `state.save()`)
- Golden fixture pattern is proven and reusable — Plans 04-08 (design_consultation) and 04-09 (investigate) can clone the `tests/fixtures/gstack_state_machines/` + `_TRANSITIONS` dict + bijection-test shape
- TURN_BUDGET exported so Pitfall 7 monologue-collapse regression guards (e.g., "conductor rejects a single-turn envelope carrying all 6 answers") can assert against a module constant rather than a magic number

## Self-Check: PASSED

Verified files on disk:

- FOUND: clawteam/templates/gstack/skills/__init__.py
- FOUND: clawteam/templates/gstack/skills/office_hours/__init__.py
- FOUND: clawteam/templates/gstack/skills/office_hours/state.py
- FOUND: tests/fixtures/gstack_state_machines/office-hours.transitions.json
- FOUND: tests/test_office_hours_state_machine.py

Verified commits in git log:

- FOUND: 575ce57 feat(04-07): scaffold office-hours skill package + transition fixture
- FOUND: 6992211 test(04-07): add failing tests for OfficeHoursState state machine
- FOUND: 2928ab1 feat(04-07): implement OfficeHoursState pydantic transition-table state machine

Verified TDD gate sequence: `test(...)` RED commit (6992211) precedes `feat(...)` GREEN commit (2928ab1) — RED/GREEN gate compliant. No REFACTOR commit (not needed — implementation clean on first GREEN).

Verified acceptance criteria:

- `class OfficeHoursState(BaseModel)` present in state.py
- `_TRANSITIONS:` present in state.py
- `TURN_BUDGET: int = 13` present in state.py (stricter than grep pattern `TURN_BUDGET = 13`; annotation preserved)
- state.py is 213 LOC (>= 100 floor)
- `pytest tests/test_office_hours_state_machine.py -x -q` → 14 passed in 0.13s (exceeds 13 floor; bonus test_pending_question_id_tracking)
- `python3 -c "from clawteam.templates.gstack.skills.office_hours import OfficeHoursState, OHState, OHEvent"` → succeeds
- Fixture JSON: turn_budget==13, transitions length==13, forcing_questions length==6 (verified by Task 1 one-liner)

---
*Phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification*
*Completed: 2026-04-21*
