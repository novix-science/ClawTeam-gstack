---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 11
subsystem: sprint
tags: [sprint-conductor, pause-resume, phase-advance, auto-advance, phase-2]
requirements_addressed: [CORE-05, CORE-07, INT-06]
dependencies:
  requires:
    - "Plan 01-02 — SprintState (pydantic v2 model + file_locked persistence)"
    - "Plan 02-03 — SprintState Phase 2 additive fields (turn_counters, caps, status, suppressed_topics)"
    - "Plan 02-07 — EvidenceGate (4-check protocol)"
    - "Plan 02-09 — forced_progress_gate (theater detector) + increment_turn_counter + reset_turn_counter_state"
    - "Plan 02-10 — register_safety_subscribers + set_careful_veto_mode"
    - "Phase 1 — InteractionGate (reused, not duplicated)"
  provides:
    - "clawteam.sprint.conductor.SprintConductor — per-team sprint loop owner"
    - "clawteam.sprint.conductor.AmbiguousSprintError / SprintNotFoundError / MissingTeamError"
    - "clawteam.sprint.state.save_sprint_state / load_sprint_state module helpers"
    - "SprintState.careful_enabled: bool = False field"
  affects:
    - "Plan 02-12 — sprint CLI sub-app (start/status/show/list/pause/resume) consumes SprintConductor"
    - "Phase 3 — GstackSprintPlugin will register per-phase EvidenceGate artifact lists via PhaseRunner"
    - "Phase 4 — Ship-phase human-approval gate consumes force_interactive_phases=['ship'] (SPRINT-05)"
tech-stack:
  added:
    - "No new runtime dependencies"
  patterns:
    - "Three-layer env precedence via tuple-based multi-generation key lookup (mirrors clawteam.identity._env)"
    - "Gate chain composition at call-site with lazy imports (avoids partial-deploy crash)"
    - "Idempotent safety-subscriber registration keyed on id(bus) (Pitfall #8 + T-02-17)"
key-files:
  created:
    - "clawteam/sprint/conductor.py (488 LOC)"
    - "tests/test_sprint_conductor.py (456 LOC, 17 tests)"
  modified:
    - "clawteam/sprint/state.py (+ careful_enabled field + save_sprint_state/load_sprint_state helpers)"
    - "clawteam/sprint/__init__.py (re-exports SprintConductor + errors + state helpers)"
    - "tests/test_sprint_state.py (+ 5 tests for careful_enabled + load/save helpers)"
decisions:
  - "Consolidated Task 3 implementation into Task 2's conductor.py because resume() without last-PhaseTransition replay + set_careful_veto_mode would violate CORE-07. Tests split per plan boundaries; code stayed cohesive."
  - "Used tuple-based _env_first helper rather than importing clawteam.identity._env because the latter hardcodes 2-3 positional keys; three-layer cap resolution needs N-key iteration."
  - "InteractionGate constructed with no args in _build_gate_chain — uses its own _resolve_sprint_dir to pair with the SprintState, matching Phase 1's gate contract (the gate accepts either an explicit sprint_dir override or resolves from the SprintState passed to check())."
  - "Conductor falls back to hardcoded gstack 7-phase order when PhaseRegistry is empty, so Phase 2 plans execute without needing Phase 3's GstackSprintPlugin loaded."
  - "_load_by_id tries exact load first then falls back to resolve_sprint for prefix support — keeps pause/resume fast-path O(1) while preserving CLI prefix UX."
metrics:
  duration: "~1.1 h"
  tests_added: 22  # 5 state tests + 17 conductor tests
  completed_date: "2026-04-20"
---

# Phase 02 Plan 11: Sprint Conductor (Pause/Resume + Gate Composition) Summary

SprintConductor — the sprint-level loop owner — composes Phase 2's new gates
(EvidenceGate, forced_progress_gate, InteractionGate) with Phase 1's SprintState +
PhaseRunner primitives into a per-team sprint engine that survives full orchestrator
restarts. Ships CORE-05, CORE-07, and INT-06 in one module.

## Objective Met

All three objectives from the plan are delivered:

- **CORE-05 — per-team sprint loop owner.** `SprintConductor(team_name=...)` owns
  one team's N sprints, enumerates them (`list_sprints`), resolves full ids or
  unambiguous prefixes (`resolve_sprint`), and dispatches phase-advance via the
  composed gate chain (`advance_phase`). Ten-concurrent-sprint correctness is
  Phase 7 scope; Phase 2 ships single-sprint correctness only.

- **CORE-07 — pause/resume across process restart.** `pause(sprint_id)` writes
  `status='paused'` atomically to state.json via `file_locked + atomic_write_text`.
  `resume(sprint_id)` rehydrates from disk, flips status back to `running`,
  re-emits the last `PhaseTransition` event from `phase_history[-1]`, and calls
  `set_careful_veto_mode(state.careful_enabled)` so the /careful destructive-command
  rail re-arms after a process boundary. Verified by
  `test_resume_after_process_restart` via two `subprocess.run` calls against
  `sys.executable`.

- **INT-06 — auto_advance semantics (D-23).** Four combinations tested end-to-end:
  - `auto_advance=True` + no unanswered questions → `InteractionGate` NOT inserted.
  - `auto_advance=True` + pending_question_ids non-empty → `InteractionGate` inserted.
  - `auto_advance=False` → `InteractionGate` ALWAYS inserted.
  - `force_interactive_phases=[current_phase]` → always insert regardless
    (Phase 4 ship-gate reservation).

## Tasks Completed

### Task 1 — SprintState careful_enabled field + load/save module helpers (TDD)

- **RED:** 5 failing tests added to `tests/test_sprint_state.py`
  covering the new field default, save/load round-trip, FileNotFoundError, Phase 1
  rehydration, and concurrent-writer file-lock safety.
- **GREEN:** `careful_enabled: bool = Field(default=False, ...)` added to
  `SprintState`. Module-level `save_sprint_state(state)` and
  `load_sprint_state(team, sprint_id)` delegate to the existing
  `SprintState.save(team)` / `SprintState.load(team, sprint_id)` class methods
  so the `file_locked` primitive is single-sourced.

### Task 2 — SprintConductor core (start / advance / pause / resume / list / resolve + error types)

- **RED:** 13 failing tests added to `tests/test_sprint_conductor.py` covering
  construction, safety-subscriber idempotency, state.json creation,
  PhaseTransition emit, gate chain ordering + short-circuit, four auto_advance
  combinations, MissingTeamError, prefix resolution, team-scoped listing, and
  three-layer cap override precedence.
- **GREEN:** `clawteam/sprint/conductor.py` (488 LOC) implements the full
  `SprintConductor` class with six public methods + three error types + module
  helpers `_env_first`, `_resolve_cap`, `_first_phase`, `_next_phase`.
  `clawteam/sprint/__init__.py` re-exports the public surface.

### Task 3 — Pause/resume survives full orchestrator restart (subprocess integration)

- **RED:** 4 failing tests added (in-process round trip, subprocess A → B restart,
  last PhaseTransition re-emit, careful_enabled restoration).
- **GREEN:** Implementation consolidated into Task 2's `conductor.py` — see
  Deviations. All 4 tests pass including the two-subprocess CORE-07 verification.

## Deviations from Plan

**Auto-fixed issues (Rules 1–3):**

1. **[Rule 2 — Plan/code consistency] SprintState field name is `team`, not `team_name`.**
   - **Found during:** Task 2 test authoring.
   - **Issue:** The plan's task stubs (line 418) construct SprintState with `team_name="t"`,
     but `clawteam/sprint/state.py` actually defines the field as `team: str` (from Plan 01-02).
     Using `team_name` at the SprintState level would fail pydantic validation.
   - **Fix:** Conductor's public API keeps `team_name` (matching plan contract + HarnessOrchestrator);
     internally it maps to `state.team` when constructing/loading SprintState.
   - **Files affected:** `clawteam/sprint/conductor.py` — `start_sprint` uses `team=self.team_name`.

2. **[Rule 2 — Plan/code consistency] PhaseRegistry method is `ordered_names()`, not `phases()`.**
   - **Found during:** Task 2 implementation.
   - **Issue:** Plan action block references `get_phase_registry().phases()` but actual API is
     `clawteam.harness.phase_registry.get_registry().ordered_names()`.
   - **Fix:** Conductor's `_first_phase` and `_next_phase` helpers call the real API.

3. **[Rule 2 — Plan/code consistency] InteractionGate signature is `(sprint_dir=None)`, not `(sprint_id=...)`.**
   - **Found during:** Task 2 gate-chain composition.
   - **Issue:** Plan action block constructs `InteractionGate(sprint_id=state.sprint_id)` but
     the Phase 1 gate's `__init__` accepts `sprint_dir: Path | None = None` and resolves the
     sprint directory from the `SprintState` passed to `check(state)`.
   - **Fix:** `_build_gate_chain` uses `InteractionGate()` with no args; the gate's
     `_resolve_sprint_dir` handles pairing against `state.team` + `state.sprint_id`.

4. **[Rule 2 — Cohesion] Task 3 implementation consolidated into Task 2's conductor.py.**
   - **Found during:** Task 3 scoping.
   - **Issue:** Task 3's `resume()` must re-emit the last PhaseTransition AND call
     `set_careful_veto_mode(state.careful_enabled)` to satisfy CORE-07. A `resume()`
     that shipped without those would immediately fail the Task 3 subprocess test,
     forcing a rewrite in Task 3. Splitting the skeleton across Task 2 and logic
     across Task 3 would have left the intermediate commit broken.
   - **Fix:** Implemented the full `resume()` in Task 2's `conductor.py` commit.
     Task 3 added only the 4 tests that verify the resume contract — the tests
     are what close CORE-07 formally.

5. **[Rule 2 — Identity helper shape] `clawteam.identity._env` hardcodes 2-3 positional keys.**
   - **Found during:** Three-layer cap override implementation.
   - **Issue:** The plan referenced `_env(CLAWTEAM_ARTIFACT_CAP_KB, OH_ARTIFACT_CAP_KB, CLAUDE_CODE_ARTIFACT_CAP_KB)` but
     `_env` has an overload-disambiguation path (second/third arg interpretation depends on
     whether the third starts with `OH_/CLAUDE_CODE_/CLAWTEAM_`) that is fragile for this
     use case.
   - **Fix:** Added a local `_env_first(keys: tuple[str, ...])` helper in conductor.py
     that iterates the tuple. Single-purpose, zero overload ambiguity. Preserves the
     `CLAWTEAM_* / OH_* / CLAUDE_CODE_*` multi-generation convention.

## Test Results

```
pytest tests/test_sprint_state.py tests/test_sprint_conductor.py -q
→ 37 passed (20 state + 17 conductor)

pytest tests/test_sprint_state.py tests/test_sprint_conductor.py tests/test_sprint_qa.py \
       tests/test_template_regression_matrix.py tests/test_harness.py \
       tests/test_evidence_gate.py tests/test_forced_progress_gate.py \
       tests/test_interaction_gate.py tests/test_freeze_registry.py -q
→ 133 passed (no regressions)

ruff check clawteam/sprint/ tests/test_sprint_conductor.py tests/test_sprint_state.py
→ All checks passed
```

## Commits

| Hash    | Type    | Description                                                                |
| ------- | ------- | -------------------------------------------------------------------------- |
| 0d9f4ae | test    | Add failing tests for careful_enabled + load/save helpers (Task 1 RED)     |
| 5ea5ef7 | feat    | Add careful_enabled field + module-level helpers to SprintState (Task 1 GREEN) |
| b1f5b93 | test    | Add failing tests for SprintConductor (Tasks 2 + 3 RED, 17 tests)          |
| 034ae39 | feat    | Implement SprintConductor + re-exports (Tasks 2 + 3 GREEN)                 |

## Verification Against `must_haves`

- [x] `SprintConductor at clawteam/sprint/conductor.py composes PhaseRunner + SprintState + EventBus` — class ships at the exact path.
- [x] Constructor signature matches the plan: `SprintConductor(team_name, *, force_interactive_phases=None, artifact_cap_bytes=None, phase_artifact_cap_bytes=None, bus=None)`.
- [x] `start_sprint(goal, auto_advance=True)` creates `uuid.uuid4().hex[:8]` id, writes state.json via `file_locked + atomic_write_text`, emits `PhaseTransition(from='', to=first_phase)`.
- [x] `advance_phase(sprint_id) → tuple[bool, str]` runs EvidenceGate → forced_progress_gate → InteractionGate in documented order; short-circuits on first `(False, reason)`.
- [x] `pause(sprint_id)` sets `status='paused'`; persists via `file_locked + atomic_write_text`.
- [x] `resume(sprint_id)` loads state.json via `file_locked`, verifies `status in ('paused','running')`, re-emits last PhaseTransition from `phase_history[-1]`, returns state.
- [x] `list_sprints()` scans `~/.clawteam/teams/<team>/sprints/*/state.json` — no cross-team scanning (Pitfall #9).
- [x] `resolve_sprint(id_or_prefix)` exact uuid[:8] match OR unambiguous prefix; `AmbiguousSprintError(prefix, candidates)`; `SprintNotFoundError` on no-match (D-25).
- [x] `SprintConductor.__init__` calls `register_safety_subscribers(bus)` — safety rails activate ONLY for gstack sprints (Pitfall #8 BC hinge).
- [x] Three-layer cap override: CLI flag > env var > state default; env reads via multi-generation key tuple per D-29.
- [x] Pause/resume survives full process restart — verified by `test_resume_after_process_restart` via two `subprocess.run` calls against `sys.executable`.
- [x] auto_advance=True + unanswered question → InteractionGate inserted; auto_advance=True + no questions → NOT inserted; auto_advance=False → always inserted; force_interactive_phases overrides both (D-23, INT-06).
- [x] Phase 0 regression matrix 12/12 stays green — `test_template_regression_matrix` still passes.

## Artifacts Conformance

| Path                              | Min LOC | Actual LOC | Contains                                           |
| --------------------------------- | ------- | ---------- | -------------------------------------------------- |
| `clawteam/sprint/conductor.py`    | 260     | 488        | `class SprintConductor:` + 3 error types + 6 methods |
| `clawteam/sprint/__init__.py`     | —       | 18         | Re-exports SprintConductor + errors + state helpers |
| `clawteam/sprint/state.py`        | —       | +39 lines  | `careful_enabled: bool = False` field + module helpers |
| `tests/test_sprint_conductor.py`  | 280     | 456        | 17 tests including `test_pause_resume_round_trip` + subprocess |

All minimum LOC targets exceeded. All required symbol/text presence checks pass.

## Key Links Verified

- `SprintConductor.__init__` → `register_safety_subscribers` (Plan 02-10) — conductor opts in; HarnessOrchestrator does not.
- `SprintConductor.advance_phase` → `EvidenceGate.check + forced_progress_gate.check + InteractionGate.check` — composed per CONTEXT Integration Points; short-circuits on first `(False, reason)`.
- `SprintConductor.pause` → `~/.clawteam/teams/<team>/sprints/<id>/state.json` — via `file_locked + atomic_write_text`.
- `SprintConductor.resume` → `clawteam/events/types.py::PhaseTransition` — replays last phase_history entry via `self.bus.emit(PhaseTransition(...))`.

## Threat Flags

None. All surface introduced by this plan is covered by the plan's existing STRIDE register:

- T-02-13 (state.json tamper) — accepted; user-owned path.
- T-02-14 (phase_history replay info leak) — accepted; artifact names only.
- T-02-15 (phase_history DoS) — accepted; forced_progress_gate bounds agent loops.
- Pitfall #5 (self-lockout via state.json freeze) — mitigated; FreezeRegistry exempts paths under `get_data_dir()`.
- Pitfall #9 (cross-team DoS scan) — mitigated; `list_sprints` is strictly team-scoped.
- T-02-17 (subscriber re-registration) — mitigated; `register_safety_subscribers` is idempotent via `id(bus)` tracker.

No new threat surface was introduced.

## Known Stubs

None. The Phase 2 ship of `SprintConductor._build_gate_chain` passes an **empty artifact
list** to `EvidenceGate` because Phase 2 does not wire phase-specific artifact schemas —
that is Phase 3 `GstackSprintPlugin` scope. This is NOT a stub: `EvidenceGate` ships in
Phase 2 as a working class; the per-phase artifact bindings are a separate plan.
Documented on the code path via the inline comment in `_build_gate_chain`.

## Follow-ups for Future Plans

- **Plan 02-12 (CLI sprint sub-app):** `clawteam sprint start/status/show/list/pause/resume`
  commands will instantiate `SprintConductor` per command and route CLI flags to the
  documented three-layer cap override.
- **Phase 3 (GstackSprintPlugin):** Will register per-phase `EvidenceGate` artifact lists
  + required_sections via `PhaseRunner.register_gate(phase, ...)`. The conductor already
  composes the gate chain at runtime, so no conductor-side changes are needed.
- **Phase 4 (Ship gate):** Will pass `force_interactive_phases=["ship"]` to the conductor
  constructor when the GstackSprintPlugin is loaded. The hook is already reserved.
- **Phase 7 (10-concurrent-sprint):** Will stress-test `list_sprints` + per-sprint
  FreezeRegistry isolation + concurrent advance_phase calls across sprints.

## Self-Check: PASSED

All claimed files exist:

- `clawteam/sprint/conductor.py` — FOUND
- `clawteam/sprint/state.py` — FOUND (modified)
- `clawteam/sprint/__init__.py` — FOUND (modified)
- `tests/test_sprint_conductor.py` — FOUND
- `tests/test_sprint_state.py` — FOUND (modified)

All claimed commits exist:

- 0d9f4ae — FOUND (test RED Task 1)
- 5ea5ef7 — FOUND (feat GREEN Task 1)
- b1f5b93 — FOUND (test RED Tasks 2 + 3)
- 034ae39 — FOUND (feat GREEN Tasks 2 + 3)

All claimed test counts verified: 20 state + 17 conductor = 37 plan-authored tests, 133
total green across the broader sprint/harness regression suite. Ruff clean.

## TDD Gate Compliance

Plan frontmatter declares `tdd_mode: true`. Both Task 1 and Tasks 2+3 followed the strict
RED → GREEN sequence:

- Task 1: `test(02-11)` commit 0d9f4ae (RED) preceded `feat(02-11)` commit 5ea5ef7 (GREEN).
- Tasks 2+3: `test(02-11)` commit b1f5b93 (RED) preceded `feat(02-11)` commit 034ae39 (GREEN).

No REFACTOR commits were needed — the initial GREEN implementations were clean and
ruff-compliant on first pass.
