---
phase: 01-core-harness-extensions
plan: 02
subsystem: sprint
tags: [sprint-state, persistence, pydantic, file-lock, atomic-json, rfc-001, phase-1]

requires:
  - phase: 00-foundation-upstream-rfc
    provides: RFC 001 §4.4 normative SprintState spec; file_locked + atomic_write_text primitives; validate_identifier + ensure_within_root path helpers; pydantic v2 + pytest conventions
  - phase: 01-core-harness-extensions
    provides: (Plan 01-01 wave-1 sibling — no runtime dependency; SprintState is independent of PhaseRegistry)
provides:
  - SprintState pydantic v2 model at clawteam/sprint/state.py with all 11 RFC 001 §4.4 fields and documented defaults
  - save(team) instance method — atomic JSON write under file_locked() + atomic_write_text
  - load(team, sprint_id) classmethod — read under file_locked() returning a populated SprintState
  - _state_path(team, sprint_id) staticmethod — canonical path resolver with path-traversal rejection
  - clawteam/sprint/__init__.py package + re-export so `from clawteam.sprint import SprintState` works
  - Canonical sprint-dir layout materialized at save time: $CLAWTEAM_DATA_DIR/teams/<team>/sprints/<sprint_id>/state.json — anchor for Plan 01-03's questions/ and answers/ subdirs
affects:
  - 01-03 InteractionGate (reads SprintState.pending_question_ids; scans sibling questions/<id>.md and answers/<id>.md files under SprintState._state_path(...).parent)
  - 01-04 Question/Answer pydantic models (lives under same sprints/<id>/ dir materialized by save())
  - 01-05 HarnessOrchestrator sprint wiring (composes a SprintState when running under a sprint-producing plugin; SprintState stays orchestrator-agnostic)
  - Phase 2 sprint engine + evidence gates (state machine operates over SprintState; last-write-wins semantics baseline)
  - Phase 7 AttentionQueue (cross-sprint pending_question_ids aggregation reads SprintState.load per team/sprint)

tech-stack:
  added: []
  patterns:
    - Independent pydantic v2 model composed with PhaseState + SprintContract (D-01) — three parallel models, not an inheritance chain
    - Persistence pattern: file_locked() around atomic_write_text (save) and around read_text (load) — same primitives as SnapshotManager
    - Path validation order: validate_identifier FIRST on every caller-supplied segment, then ensure_within_root as belt-and-braces — mirrors clawteam.team.snapshot._snapshots_root
    - Static helper (_state_path) usable without instance construction — supports tests and future listing/deletion code without requiring a full SprintState

key-files:
  created:
    - clawteam/sprint/__init__.py
    - clawteam/sprint/state.py
    - tests/test_sprint_state.py
  modified: []

key-decisions:
  - D-01 applied — SprintState is a new independent pydantic model, not a subclass or replacement of PhaseState; three models (PhaseState, SprintContract, SprintState) compose for distinct concerns (harness run / sprint scope / sprint runtime)
  - D-05 applied — file_locked + atomic_write_text + validated path, last-write-wins; identical primitives to SnapshotManager, team/costs, config
  - sprint_id default_factory matches SprintContract.id convention (uuid.uuid4().hex[:8]) so a SprintState can freely reference a contract id
  - _state_path is a @staticmethod (not @classmethod) so the path can be computed without constructing a SprintState (tests + future list/delete code)
  - load() holds the file lock around read_text so it never reads during an in-flight save; atomic_write_text already guarantees non-torn writes, the lock adds serialization
  - Validation inside _state_path runs BEFORE mkdir, so a path-traversal attempt leaves zero filesystem residue

patterns-established:
  - SprintState.<op>(team, ...) — all persistence methods take team explicitly rather than reading it from self, mirroring the validate-at-boundary convention
  - Concurrent-writer invariant for sprint state: 8 threads × load/mutate/save cycle converges to one of the written markers with no stray *.tmp files

requirements-completed: [CORE-04, INT-01]

duration: 5min
completed: 2026-04-17
---

# Phase 01 Plan 02: SprintState Summary

**SprintState pydantic v2 model + save/load under file_locked atomic JSON at `$CLAWTEAM_DATA_DIR/teams/<team>/sprints/<sprint_id>/state.json`, with path-traversal rejection and 8-thread concurrent-writer last-write-wins verified**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-17T18:48:07+08:00 (worktree base reset; pre-commit ruff check)
- **Completed:** 2026-04-17T18:53:26+08:00 (GREEN commit landed)
- **Tasks:** 2 (TDD RED + GREEN)
- **Files created:** 3
- **Files modified:** 0

## Accomplishments

- New `clawteam/sprint/` package with `SprintState` pydantic v2 model holding all 11 RFC 001 §4.4 fields (`sprint_id`, `goal`, `team`, `current_phase`, `phase_history`, `artifacts`, `participants`, `pending_question_ids`, `auto_advance`, `workspace_branch`, `created_at`)
- Persistence surface (`save` / `load` / `_state_path`) reuses existing `file_locked` + `atomic_write_text` + `validate_identifier` + `ensure_within_root` primitives — no new machinery introduced
- 7 new tests (`tests/test_sprint_state.py`) covering defaults, uniqueness of sprint_id default_factory, save/load roundtrip, 8-thread concurrent-writer last-write-wins, path-traversal rejection (team + sprint_id), and canonical-path shape
- Phase 0 regression matrix (12 cases) remains green; full suite: 627 passed

## Task Commits

Each task was committed atomically following the TDD gate sequence:

1. **Task 1 (RED): Write failing tests for SprintState** — `f72bdf5` (test)
2. **Task 2 (GREEN): Implement SprintState with file-locked atomic JSON persistence** — `1118455` (feat)

_Note: A `refactor` gate was not needed — the GREEN implementation is the minimal direct pydantic + persistence shape; no cleanup pass was warranted._

## Files Created/Modified

- `clawteam/sprint/__init__.py` — package entry; single re-export so `from clawteam.sprint import SprintState` works
- `clawteam/sprint/state.py` — `SprintState` pydantic v2 model + `save(team)` + `load(team, sprint_id)` + `_state_path(team, sprint_id)` (95 lines; meets `min_lines: 90`)
- `tests/test_sprint_state.py` — 7 tests exercising model shape + defaults + roundtrip + concurrency + path-traversal

## Decisions Made

- **D-01 applied** — SprintState is independent of `PhaseState` and `SprintContract`. Three models span three concerns (harness run / sprint scope / sprint runtime) and compose, not inherit.
- **D-05 applied** — persistence under `file_locked()` + `atomic_write_text` at `get_data_dir() / "teams" / <team> / "sprints" / <sprint_id> / "state.json"`. Last-write-wins under the lock is the explicit semantic (Phase 2 can layer stricter merge semantics on top).
- `_state_path` is a `@staticmethod` so callers can compute the canonical path without constructing a `SprintState` (e.g., the `test_sprint_state_path_contains_both_team_and_sprint_id` test and future list/delete helpers).
- `load` also holds the file lock — `atomic_write_text` already ensures no torn writes, but the lock gives readers serialization against in-flight writers.

## Deviations from Plan

None - plan executed exactly as written.

The plan included a pre-formatted test file and a pre-formatted implementation file; both landed byte-for-byte as specified. The only post-write adjustment was ruff's import-sort autofix on `tests/test_sprint_state.py` (added a blank line between third-party `pytest` and first-party `clawteam.sprint.state` once the first-party module existed at GREEN time). Ruff autofix is a formatting-only operation and is not treated as a deviation.

## Issues Encountered

None. TDD gates ran cleanly:

- RED: ruff passed (after auto-fix), test collection failed with the expected `ModuleNotFoundError: No module named 'clawteam.sprint'` for all 7 tests.
- GREEN: ruff passed across all three files, 7 tests passed, 12 regression-matrix cases passed, 8 Plan 01-01 tests passed, full suite 627 passed in ~110s.

## Verification Evidence

- **Ruff:** `ruff check clawteam/sprint/__init__.py clawteam/sprint/state.py tests/test_sprint_state.py` → All checks passed
- **Unit tests:** `pytest tests/test_sprint_state.py -v` → 7 passed
- **Phase 0 regression matrix:** `pytest tests/test_template_regression_matrix.py -v` → 12 passed (ROADMAP Phase 1 SC#6)
- **Plan 01-01 peer tests:** `pytest tests/test_phase_registry.py tests/test_plugin_hooks.py -v` → 8 passed
- **Full suite:** `pytest tests/ -q` → 627 passed, 0 failures
- **Structural greps:** all acceptance_criteria counts met (class SprintState=1, def save=1, def load=1, _state_path=3, file_locked=4, validate_identifier=3, ensure_within_root=2, atomic_write_text=3, uuid.uuid4().hex[:8]=2, re-export=1)
- **Smoke import:** `from clawteam.sprint import SprintState; SprintState(goal='x', team='t', current_phase='discuss', created_at='...')` → sprint_id matches `^[0-9a-f]{8}$`

## Threat Register Status

All mitigate-disposition entries in the plan's `<threat_model>` were implemented and verified:

- **T-01-06 (Tampering via path composition):** `validate_identifier` + `ensure_within_root` chain rejects `../../etc` on both `team` and `sprint_id`. Tests `test_sprint_state_invalid_team_raises` and `test_sprint_state_invalid_sprint_id_raises` confirm rejection happens before any filesystem write.
- **T-01-07 (DoS via torn write):** `file_locked()` + `atomic_write_text` (mkstemp → write → `os.replace`). `test_sprint_state_concurrent_writers_last_write_wins` exercises 8 concurrent writers, asserts the final file parses + matches one of the thread markers, and verifies no stray `.tmp` files remain.
- **T-01-10 (EoP via attacker-controlled load path):** `load()` runs through the same `_state_path` chain as `save()` — symmetric validation with no filesystem escape possible.
- T-01-08 and T-01-09 are `accept`-disposition (data disclosure matches existing `PhaseState` surface; last-write-wins is by design per D-05) — no implementation change required.

No new security-relevant surface was introduced beyond what the plan's threat model enumerates — no new network endpoints, no new auth paths, no schema changes at trust boundaries.

## TDD Gate Compliance

Plan frontmatter `type: execute` with two `tdd="true"` tasks. The gate sequence in git log is:

1. `test(01-02)` — `f72bdf5` (RED): tests added and fail at collection with `ModuleNotFoundError` for the not-yet-existing `clawteam.sprint` module.
2. `feat(01-02)` — `1118455` (GREEN): `clawteam/sprint/` package materialized; all 7 RED tests now pass.

Both gate commits present in git log; fail-fast rule was not triggered (no test passed unexpectedly at RED).

## Forward Contracts

- **For Plan 01-03 (`InteractionGate`):** `SprintState._state_path(team, sprint_id).parent` is the directory where `InteractionGate` scans `questions/*.md` and `answers/*.md`. Plan 01-03 introduces those subdirectories; they do NOT need to exist at save time for this plan (atomic_write_text only creates `state.json`'s parents).
- **For Plan 01-04 (Question/Answer models):** The `pending_question_ids` field is a flat `list[str]` of 8-char hex IDs per D-07. Plan 01-04 defines the Question/Answer pydantic models that those IDs reference; nothing about SprintState needs to change when those models land.
- **For Plan 01-05 (`HarnessOrchestrator` sprint wiring):** `SprintState` is orchestrator-agnostic — it does not import from `clawteam.harness`. Plan 01-05 will compose a `SprintState` when the orchestrator is running under a sprint-producing plugin.

## Deferred

- `clawteam sprint pause/resume` CLI → Phase 2
- Richer `phase_history` entry types with structured timestamps/artifact hashes → Phase 2 (RFC 001 §4.4 specifies `list[dict[str, str]]` for now)
- Sprint-level artifact caps + compaction → Phase 2
- Delete / list helpers on `SprintState` (not needed until Phase 2 CLI lands)
- `load()` exception translation (e.g., `SprintNotFound`) — caller currently sees `FileNotFoundError` from `path.read_text`; acceptable for Phase 1 since `file_locked()` does not open the target file

## User Setup Required

None - no external service configuration required.

## Next Plan Readiness

- Plan 01-03 can proceed: `InteractionGate` has a concrete `SprintState._state_path` contract to compute the question/answer scan directory.
- Plan 01-04 can proceed: `SprintState.pending_question_ids` is already the contract target.
- Plan 01-05 can proceed: `SprintState` is importable as `from clawteam.sprint import SprintState` and composes cleanly with `PhaseState`.

## Self-Check: PASSED

**Files:**
- FOUND: clawteam/sprint/__init__.py (5 lines)
- FOUND: clawteam/sprint/state.py (95 lines, ≥90 required)
- FOUND: tests/test_sprint_state.py (144 lines)

**Commits:**
- FOUND: f72bdf5 (RED: test)
- FOUND: 1118455 (GREEN: feat)

**Acceptance grep counts:**
- class SprintState: 1 ✓ (expected 1)
- def save: 1 ✓ (expected 1)
- def load: 1 ✓ (expected 1)
- _state_path: 3 ✓ (expected ≥3)
- file_locked: 4 ✓ (expected ≥2)
- validate_identifier: 3 ✓ (expected ≥2)
- ensure_within_root: 2 ✓ (expected ≥1)
- atomic_write_text: 3 ✓ (expected ≥1)
- uuid.uuid4().hex[:8]: 2 ✓ (expected ≥1)
- __init__ re-export: 1 ✓ (expected 1)

**Test counts:**
- SprintState tests: 7 passed ✓
- Regression matrix: 12 passed ✓ (ROADMAP Phase 1 SC#6)
- Plan 01-01 peer tests: 8 passed ✓
- Full suite: 627 passed, 0 failed ✓

---
*Phase: 01-core-harness-extensions*
*Plan: 02*
*Completed: 2026-04-17*
