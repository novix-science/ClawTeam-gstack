---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 03
subsystem: sprint-state
tags: [sprint-state, pydantic, additive-fields, phase-2, turn-counters, artifact-caps, backward-compatibility, tdd]

# Dependency graph
requires:
  - phase: 01-core-harness-extensions
    provides: "Phase 1 SprintState pydantic model (11 RFC 001 §4.4 fields + save/load under file_locked)"
provides:
  - "SprintState.turn_counters: dict[str, int] - per-agent theater detection counter (D-14)"
  - "SprintState.artifact_cap_bytes: int default 50*1024 - per-file hard cap (D-27)"
  - "SprintState.phase_artifact_cap_bytes: int default 500*1024 - per-phase sum cap (D-28)"
  - "SprintState.status: Literal['running','paused','completed'] - sprint lifecycle for pause/resume (D-22)"
  - "SprintState.suppressed_topics: dict[str, list[str]] - cycle-detector suppression persistence (D-21)"
  - "Phase 1 backward compatibility: model_validate on Phase-1-shaped JSON succeeds, new fields auto-default"
affects:
  - "02-06 ArtifactStore (reads artifact_cap_bytes / phase_artifact_cap_bytes)"
  - "02-08 DefaultRoutingPolicy (writes suppressed_topics)"
  - "02-09 ForcedProgressGate (reads turn_counters)"
  - "02-11 SprintConductor (flips status via pause/resume)"
  - "02-12 CLI cap overrides (three-layer override chain; state default is the lowest layer)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Additive pydantic v2 field extension preserving save/load invariants"
    - "Literal-typed status enum as single exception to open-str convention (closed state machine for pause/resume safety)"
    - "Default-backed BC: every new field has default so legacy JSON rehydrates via pydantic v2 model_validate"

key-files:
  created: []
  modified:
    - "clawteam/sprint/state.py (Phase 2 additive block at lines 54-97; +46 LOC, -1 LOC)"
    - "tests/test_sprint_state.py (+182 LOC; 7 existing tests preserved; 8 new Phase 2 tests appended)"

key-decisions:
  - "status is the ONE Literal-typed field in SprintState - closed 3-value state machine justifies divergence from open-str convention; rationale documented in field description"
  - "Phase 2 fields appended AFTER created_at (Phase 1's last field) to preserve RFC 001 §4.4 field order; save/load untouched"
  - "Every Phase 2 field has a default -> Phase 1 state.json files auto-rehydrate via pydantic v2's missing-field-fill behavior (no migration script needed)"

patterns-established:
  - "Phase 2 additive-block comment header cites CONTEXT decision IDs (D-14/D-15/D-16/D-21/D-27/D-28) so future readers can trace schema motivation"
  - "BC-critical invariant captured in a dedicated test (test_sprint_state_load_of_legacy_phase1_file_rehydrates_defaults) that writes legacy JSON directly then loads through the production path"

requirements-completed: [CORE-07, INT-06, QUALITY-03, QUALITY-11]

# Metrics
duration: 4min
completed: 2026-04-20
---

# Phase 2 Plan 03: SprintState Phase 2 Field Extensions Summary

**Five additive pydantic v2 fields on SprintState (turn_counters, artifact_cap_bytes, phase_artifact_cap_bytes, status Literal, suppressed_topics) with Phase 1 JSON rehydration preserved.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-20T09:56:36Z
- **Completed:** 2026-04-20T10:00:20Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 2

## Accomplishments

- `SprintState` extended with 5 additive Phase 2 fields at `clawteam/sprint/state.py` lines 54-97 (header comment cites CONTEXT D-IDs; each field has a `description=` string explaining its downstream consumer).
- Phase 1 BC preserved: new test `test_sprint_state_load_of_legacy_phase1_file_rehydrates_defaults` writes a raw Phase-1-shape JSON directly to `$CLAWTEAM_DATA_DIR/teams/.../sprints/.../state.json` and confirms `SprintState.load()` rehydrates with Phase 2 defaults auto-populated — no migration script needed.
- `status: Literal["running","paused","completed"]` — closed state machine, not open str. The one exception to the open-str convention, documented inline and in the RESEARCH §Pattern 1 rationale.
- Test count grew 7 -> 15; Phase 0 regression matrix 12/12; Phase 1 peer tests (sprint_qa, interaction_gate) 18/18 green.
- Unblocks Plans 02-06 (reads artifact_cap_bytes), 02-08 (writes suppressed_topics), 02-09 (reads turn_counters), 02-11 (flips status).

## Task Commits

Each task was committed atomically:

1. **Task 1: RED - add failing tests for 5 new SprintState fields + BC rehydration** — `66bc3fe` (test)
2. **Task 2: GREEN - add 5 Phase 2 additive fields to SprintState** — `c382a50` (feat)

**Plan metadata (this SUMMARY.md):** committed immediately after writing.

_Note: TDD plan — RED gate (test commit 66bc3fe) preceded GREEN gate (feat commit c382a50). No REFACTOR needed; fields were minimal and Phase-1-compatible on first pass._

## Files Created/Modified

- `clawteam/sprint/state.py` — Added `Literal` to typing import; added 5-field Phase 2 block at lines 54-97 (turn_counters, artifact_cap_bytes, phase_artifact_cap_bytes, status, suppressed_topics) with per-field `description=` strings citing CONTEXT decisions. Phase 1 fields, `_state_path`, `save`, `load` unchanged.
- `tests/test_sprint_state.py` — Added `json` and `pydantic.ValidationError` imports; appended 8 new test functions at bottom (6 unit tests for defaults + Literal constraint, 2 integration tests for roundtrip + legacy-JSON rehydration). Existing 7 Phase 1 tests preserved byte-identical.

## Decisions Made

- **Phase 2 fields appended after `created_at`** (Phase 1's last field) rather than interleaved — preserves RFC 001 §4.4 field order for JSON serialization stability and test readability.
- **`status` uses `Literal` (3-value enum), not open `str`** — pause/resume needs a closed state machine; open `str` would accept invalid transitions at model_validate. This is the single documented exception to the open-str convention (RESEARCH §Pattern 1 approves).
- **No migration script** — pydantic v2's model_validate auto-fills missing fields with their defaults; legacy Phase 1 state.json files on disk load cleanly without any migration pass (RESEARCH §Runtime State Inventory invariant).
- **Descriptions on every new field cite downstream consumers** — e.g., `turn_counters` description names `Transport.deliver()` + `ArtifactStore.write()` hook sites; `suppressed_topics` names `DefaultRoutingPolicy.decide` (Plan 02-08). This makes the schema self-documenting for the consumer plans in Waves 2-4.

## Deviations from Plan

None — plan executed exactly as written. Both tasks passed verification on first attempt:

- Task 1 RED: 8 new tests failed with `AttributeError: 'SprintState' object has no attribute 'turn_counters'` (expected), 7 existing tests still passing. Ruff clean. Committed as `66bc3fe`.
- Task 2 GREEN: 15/15 sprint_state tests pass; Phase 0 regression matrix 12/12; Phase 1 peer tests (sprint_qa + interaction_gate) 18/18 green. Ruff clean. Committed as `c382a50`.

No auto-fixes (Rules 1-3) needed; no architectural questions (Rule 4).

## Issues Encountered

- **System `pytest` uses Python 3.14** without `typer` installed, so `tests/test_template_regression_matrix.py` (which imports `typer.testing`) failed collection on direct invocation. Used repo venv pytest (`/home/jac/repos/ClawTeam-gstack/.venv/bin/pytest`) for the regression matrix run — 12/12 pass. This is an environment observation, not a test-code issue.

## Forward Contracts

For downstream Phase 2 plans that consume this schema:

| Consumer plan | Reads | Writes | Field |
|---|---|---|---|
| 02-06 ArtifactStore.write | ✓ | — | `artifact_cap_bytes` (per-file cap enforcement) |
| 02-07 EvidenceGate | ✓ | — | `phase_artifact_cap_bytes` (compaction trigger) |
| 02-08 DefaultRoutingPolicy.decide | ✓ | ✓ | `suppressed_topics` (cycle-detector persistence) |
| 02-08 Transport.deliver pre-deliver hook | — | ✓ | `turn_counters[agent] += 1` on successful turn |
| 02-06 ArtifactStore.write post-write hook | — | ✓ | `turn_counters[agent] += 1` on successful artifact |
| 02-09 ForcedProgressGate | ✓ | — | `turn_counters` (2-consecutive-no-progress detection) |
| 02-11 SprintConductor.pause / .resume | — | ✓ | `status` transitions ('running' -> 'paused' / 'paused' -> 'running') |
| 02-12 CLI `--artifact-cap-kb` | — | ✓ | `artifact_cap_bytes` via three-layer override (CLI > env > state default) |

## Known Stubs

None. The schema is complete for its scope; each field's consumers are assigned to downstream plans in the same phase.

## TDD Gate Compliance

- **RED gate (test commit):** `66bc3fe` — `test(02-03): add failing tests for SprintState Phase 2 field extensions + BC rehydration`
- **GREEN gate (feat commit):** `c382a50` — `feat(02-03): add 5 Phase 2 additive fields to SprintState ...`
- **REFACTOR gate:** not needed — fields were added in minimal final form; no cleanup pass required.

Gate sequence verified via `git log --oneline HEAD~2..HEAD`.

## User Setup Required

None — pure schema extension; no external services, no env vars, no user-facing changes. Existing sprint state.json files on disk continue to load correctly.

## Next Phase Readiness

- `SprintState` schema is ready for the Wave 2/3/4 consumers (Plans 02-06, 02-07, 02-08, 02-09, 02-11, 02-12).
- Phase 1 state.json files rehydrate cleanly — no migration / backfill needed.
- Tests provide regression guard for the BC invariant: any future change that breaks Phase 1 JSON compatibility will fail `test_sprint_state_load_of_legacy_phase1_file_rehydrates_defaults`.

## Self-Check: PASSED

- [x] `clawteam/sprint/state.py` exists with 5 new fields at lines 54-97: `FOUND`
- [x] `tests/test_sprint_state.py` has 15 `def test_` functions: `FOUND (15)`
- [x] Commit `66bc3fe` exists (RED gate): `FOUND`
- [x] Commit `c382a50` exists (GREEN gate): `FOUND`
- [x] Pytest: 15/15 sprint_state, 12/12 template regression, 18/18 Phase 1 peer — all green.
- [x] Ruff check + format: clean on both modified files.
- [x] No Phase 1 field deleted: all 11 RFC 001 §4.4 fields present (verified via `SprintState.model_fields.keys()` — 16 total = 11 + 5).

---
*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Completed: 2026-04-20*
