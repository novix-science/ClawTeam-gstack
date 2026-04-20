---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 09
subsystem: harness
tags: [forced-progress-gate, theater-detector, turn-counter, progress-signal, pitfall-2, pitfall-3, pitfall-16, phase-2]

# Dependency graph
requires:
  - phase: 01-core-harness-extensions
    provides: SprintState (turn_counters field), Question/Answer qa.py helpers, PhaseGate base
  - phase: 02 (same wave 2)
    provides: ArtifactStore write() hook chain (Plan 02-06), _pre_deliver_hooks envelope validator (Plan 02-08), routing-policy cycle detector + progressSignal seam (Plan 02-08), SprintState Phase 2 fields (Plan 02-03), ForcedProgressTriggered + TaskCompleted events (Plan 02-01)
provides:
  - clawteam.harness.forced_progress_gate — theater / no-progress PhaseGate
  - increment_turn_counter + reset_turn_counter_state — turn-id dedupe helpers
  - clawteam.harness.theater_detector — re-export alias (flips Plan 02-08 skipif gate)
  - ArtifactStore(turn_counter_callback=…) — Plan 02-11 Conductor install seam (site #2)
  - transport.base.set_turn_counter_callback — Plan 02-11 Conductor install seam (site #1)
  - DefaultRoutingPolicy recentEvents entries carry progressSignal key
affects: [02-11 (SprintConductor owns callback install + TaskCompleted subscription), 02-13 (integration / regression), Phase 3 (role prompts can reason about theater-trip payloads), Phase 4 (/attend surfaces the multi-choice question)]

# Tech tracking
tech-stack:
  added: []  # zero new runtime deps — stdlib + existing pydantic + existing EventBus
  patterns:
    - "Module-level callback slot (transport.base._TURN_COUNTER_CALLBACK): SprintConductor-installed, cleared on teardown"
    - "Per-agent dedupe on (agent, turn_id) via module-level _seen_turn_ids — survives across transient Transport/ArtifactStore instances within one sprint"
    - "Per-artifact author-agent attribution via .meta.json sidecar (Plan 02-06 Task 2 producer, Plan 02-09 consumer)"
    - "Pitfall #3 seam pattern: reserve field in write path (Plan 02-08), populate in consumer plan (Plan 02-09) — no cross-plan coupling at import time"
    - "Re-export alias module to flip cross-plan skipif import gates (theater_detector.py → forced_progress_gate.py)"

key-files:
  created:
    - clawteam/harness/forced_progress_gate.py (271 lines — PhaseGate + helpers + question writer + per-agent bytes computer)
    - clawteam/harness/theater_detector.py (26 lines — re-export shim flipping Plan 02-08's skipif gate)
    - tests/test_forced_progress_gate.py (229 lines — 9 tests covering D-14..D-17 + Pitfall #2/#3/#16 invariants)
  modified:
    - clawteam/harness/artifacts.py (+25 lines — turn_counter_callback kwarg + end-of-hook-chain invocation gated on metadata.agent)
    - clawteam/transport/base.py (+52 lines — module-level callback slot + setter + _pre_deliver_hooks invocation on valid envelope + reset on sprint teardown)
    - clawteam/team/routing_policy.py (+12 lines — _append_event progress_signal kwarg + progressSignal key on every recentEvents entry)

key-decisions:
  - "Per-agent artifact-bytes attribution sources from .meta.json sidecar (not SprintState.artifacts) — keeps the gate read-only against file system state and avoids an in-memory byte tracker that would need to reset across sprint boundaries"
  - "turn_counter_callback on ArtifactStore is constructor-kwarg (not a module-level slot like transport.base) — ArtifactStore is instantiated per-harness so a per-instance slot is natural; Transport is used via module-level helpers (_pre_deliver_hooks) so a module-level slot matches the access pattern"
  - "increment_turn_counter dedupe is keyed on (agent, turn_id) — two agents with the same turn_id (extremely unlikely but possible under collision) still each increment their own counter; empty turn_id always increments (no fabricated dedupe)"
  - "TaskCompleted handler holds a _task_completed_agents set the gate drains on check() — avoids racing with the synchronous event bus while preserving the 'TaskCompleted resets counter' semantics"
  - "Emit ForcedProgressTriggered BEFORE returning (False, …) so observers can react before the gate caller sees the rejection — consistent with Plan 02-08 CycleDetected emit-before-return ordering (Pitfall #7 pattern)"
  - "Created clawteam/harness/theater_detector.py as a re-export alias — Plan 02-08's test skipif imports that exact name; avoids a cross-plan test edit and keeps the original plan file name (forced_progress_gate.py per §02-CONTEXT D-17) canonical"

patterns-established:
  - "Turn-counter callback seam: Plan 02-11 Conductor will call transport.base.set_turn_counter_callback(cb) + construct ArtifactStore(turn_counter_callback=cb) where cb = lambda agent, turn_id: increment_turn_counter(sprint_state, agent, turn_id); this is the sprint-scoped wiring contract"
  - "progressSignal is now a contractual key on every recentEvents entry (default False); future progress-source plans can set it on individual entries without schema drift"
  - "Per-agent isolation enforcement via .meta.json scan: any future cross-agent isolation check should source authorship from the sidecar, not from in-memory state"

requirements-completed: [QUALITY-11, QUALITY-02]

# Metrics
duration: ~45min
completed: 2026-04-20
---

# Phase 02 Plan 09: forced_progress_gate + Turn-Counter Wiring + progressSignal Population Summary

**Ship the theater detector: `forced_progress_gate` PhaseGate subclass reads SprintState.turn_counters and per-agent .meta.json byte delta to detect 2-consecutive-no-progress-turn agents, writes a multi-choice question file, emits ForcedProgressTriggered; wires the D-14 turn counter into ArtifactStore.write end-of-hook-chain + transport.base._pre_deliver_hooks valid-envelope exit (both sites dedupe by (agent, turn_id) via module-level _seen_turn_ids); populates Plan 02-08's reserved progressSignal field on every routing-policy recentEvents entry so Pitfall #3 protection is live end-to-end.**

## Performance

- **Duration:** ~45 min
- **Started:** 2026-04-20 (plan dispatch)
- **Completed:** 2026-04-20
- **Tasks:** 2 (TDD RED + TDD GREEN)
- **Files changed:** 6 (2 created, 3 modified in clawteam/, 1 new test file, 1 re-export shim)
- **Total LOC:** 609 additions / 6 deletions

## Accomplishments

- **Theater / no-progress detector shipped** — PhaseGate subclass with strict per-agent attribution and a 2-turn threshold; triggers multi-choice question (A: keep waiting, B: restart agent, C: abort sprint) written to `<sprint_dir>/questions/<id>.md` and a `ForcedProgressTriggered` event emit with the per-agent consecutive-no-progress count.
- **D-14 turn-counter wired at both hook sites** — `ArtifactStore.write()` end-of-chain (gated on `metadata["agent"]`) and `transport.base._pre_deliver_hooks` valid-envelope exit. Both go through the same `increment_turn_counter(state, agent, turn_id)` helper so Pitfall #2 dedupe is guaranteed across channels.
- **Pitfall #16 per-agent isolation proved** — `_compute_per_agent_artifact_bytes` sums bytes strictly per author-agent (sourcing authorship from the `.meta.json` sidecar written by Plan 02-06 Task 2); one agent's write NEVER resets another agent's no-progress counter. Test `test_per_agent_not_sprint_wide_isolation` explicitly asserts security's write does not rescue engineer from a 2-turn threshold.
- **Pitfall #3 progress-signal seam populated** — Plan 02-08 reserved the `progressSignal` key on `recentEvents` entries for cycle-detector bypass on legitimate iteration. Plan 02-09 now writes this key on every `_append_event` call (default False) so future progress-source paths can set `progress_signal=True` without schema drift.
- **Plan 02-08's previously-skipped Pitfall #3 test now runs green** — `tests/test_cycle_detector.py::test_progress_signal_breaks_cycle_streak_per_pitfall3` was `skipif`-gated on importability of `clawteam.harness.theater_detector`; the re-export shim flips the gate and the test passes on the first run.

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — failing tests for forced_progress_gate + turn-counter increment sites** — `f26a920` (test)
2. **Task 2: GREEN — implement forced_progress_gate + wire turn-counter + wire progressSignal** — `9403c4a` (feat)

## Files Created/Modified

### Created

- `clawteam/harness/forced_progress_gate.py` — 271 lines.
  - Lines 58-74: `increment_turn_counter(state, agent, turn_id="")` — module-level dedupe + increment helper; Pitfall #2 compliant (same `(agent, turn_id)` across deliver + write counts once).
  - Lines 77-79: `reset_turn_counter_state()` — SprintConductor teardown helper + test helper; clears `_seen_turn_ids`.
  - Lines 82-214: `class forced_progress_gate(PhaseGate)` — theater detector.
    - Lines 98-100: `register()` — subscribes to `TaskCompleted` so the gate absorbs task-completion events.
    - Lines 108-173: `check(state)` — core gate loop; per-agent attribution, TaskCompleted reset, byte-delta progress detection, 2-turn-threshold trigger, question-file write, `ForcedProgressTriggered` emit.
    - Lines 175-208: `_write_question(state, agent)` — writes `<sprint_dir>/questions/<uuid8>.md` as multi-choice Question with 3 choices using Plan 01-04 qa.py schema.
    - Lines 210-214: `clear_agent_trigger(agent)` — Plan 02-11 Conductor hook called on matching answer arrival.
  - Lines 217-264: `_compute_per_agent_artifact_bytes(state)` — `.meta.json` sidecar scan summing bytes strictly per author-agent.

- `clawteam/harness/theater_detector.py` — 26 lines; re-exports `forced_progress_gate`, `increment_turn_counter`, `reset_turn_counter_state`, `NO_PROGRESS_THRESHOLD` from the canonical module. Flips the `skipif` gate on `tests/test_cycle_detector.py::test_progress_signal_breaks_cycle_streak_per_pitfall3`.

- `tests/test_forced_progress_gate.py` — 229 lines; 9 tests:
  - `test_zero_turns_passes` — fresh SprintState, gate passes.
  - `test_one_noprogress_turn_passes` — 1 turn below threshold.
  - `test_two_consecutive_noprogress_turns_trigger_gate` — 2 turns trip gate with engineer name + "no-progress" phrase in reason.
  - `test_task_completed_event_resets_counter` — TaskCompleted absorbs and resets.
  - `test_net_positive_artifact_delta_counts_as_progress` — engineer wrote 100 bytes → gate passes.
  - `test_per_agent_not_sprint_wide_isolation` — security's write does NOT rescue engineer; gate still triggers on engineer (Pitfall #16 proof).
  - `test_turn_id_dedupe_artifactstore_and_transport_same_turn` — same turn_id across two sites increments counter ONCE (Pitfall #2 proof).
  - `test_gate_writes_question_file_on_trigger` — question file exists, parses as multi-choice with exactly 3 labeled choices.
  - `test_gate_emits_forced_progress_triggered_event` — event captured with agent, consecutive_no_progress=2, question_id.

### Modified

- `clawteam/harness/artifacts.py` — +25 lines.
  - `ArtifactStore.__init__`: added `turn_counter_callback: Callable[[str, str], None] | None = None` keyword-only kwarg (BC preserved — existing three-arg + `artifact_cap_bytes` kwarg call sites unchanged).
  - `ArtifactStore.write`: new Hook 4 at end of chain — invokes `self._turn_counter_callback(agent, turn_id)` when `metadata["agent"]` is set. Callback errors are swallowed (observation-only invariant).

- `clawteam/transport/base.py` — +52 lines.
  - Added `_TURN_COUNTER_CALLBACK: Callable[[str, str], None] | None = None` module-level slot.
  - Added `set_turn_counter_callback(cb)` setter for SprintConductor install/teardown.
  - Added `get_turn_counter_callback()` test helper.
  - Extended `_pre_deliver_hooks` valid-envelope exit path: after the drift-counter reset, invokes the callback with `(agent, turn_id)` where `turn_id` is extracted from the validated payload (preferring `turn_id`, falling back to `turnId`, then `msg.request_id`). Callback errors swallowed.
  - Extended `_reset_drift_counters()` to also clear `_TURN_COUNTER_CALLBACK` so a new sprint does not observe a stale hook.

- `clawteam/team/routing_policy.py` — +12 lines.
  - `_append_event` gained `progress_signal: bool = False` kwarg.
  - `_append_event` now writes `event["progressSignal"] = bool(progress_signal)` on every entry so readers of `recentEvents` can rely on the key being present.

## Set-Turn-Counter-Callback Seam Contract for Plan 02-11

Plan 02-11 (SprintConductor) owns the callback install. The contract:

```python
# sprint start:
def _make_turn_counter_cb(sprint_state):
    def cb(agent, turn_id):
        increment_turn_counter(sprint_state, agent, turn_id)
    return cb

cb = _make_turn_counter_cb(sprint_state)
transport.base.set_turn_counter_callback(cb)          # hook site #1 (deliver)
artifact_store = ArtifactStore(                       # hook site #2 (write)
    base_dir=...,
    team_name=...,
    harness_id=...,
    turn_counter_callback=cb,
)

# also: subscribe the gate to TaskCompleted
gate = forced_progress_gate()
gate.register()

# sprint stop / resume:
transport.base.set_turn_counter_callback(None)
transport.base._reset_drift_counters()  # already clears callback too (belt-and-braces)
reset_turn_counter_state()
```

The SprintConductor must ALSO register the gate's `TaskCompleted` subscription via `gate.register()` before the first `check()` call — otherwise TaskCompleted resets won't be observed. This is documented in the SprintConductor forward contract.

## Decisions Made

- **Per-agent byte attribution via `.meta.json` scan, not an in-memory tracker.** Rationale: keeps the gate stateless against file-system truth, avoids a reset-across-sprints bookkeeping burden, and mirrors the existing Plan 02-06 producer pattern. The scan is O(artifacts) per check, bounded by per-phase artifact count (50 KB × ~10 artifacts per agent max per D-27/D-28).
- **`ArtifactStore` callback is constructor-kwarg; `transport.base` callback is module-level slot.** Rationale: ArtifactStore is instantiated per-harness (natural per-instance hook); `_pre_deliver_hooks` is a module-level function (natural module-level hook).
- **turn_id dedupe is keyed on `(agent, turn_id)` not bare `turn_id`.** Rationale: two different agents with the same turn_id (under UUID collision or reuse) still each count their own turn; the dedupe prevents the single-agent double-count case that the two hook sites can produce.
- **`theater_detector.py` as a re-export shim, not the canonical module name.** Rationale: §02-CONTEXT D-17 names the gate `forced_progress_gate`. Plan 02-08's skipif gate imports `theater_detector` (different name). Shipping both names — canonical file + alias — avoids an after-the-fact rename in Plan 02-08's test while preserving the D-17 naming contract.
- **Emit `ForcedProgressTriggered` sync BEFORE returning `(False, …)`.** Rationale: matches Plan 02-08's `CycleDetected` emit-before-return ordering so downstream observers see state consistent with the gate's decision.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Created `clawteam/harness/theater_detector.py` re-export shim**
- **Found during:** Task 2 (GREEN — integration verification)
- **Issue:** The plan specifies the gate module name as `clawteam/harness/forced_progress_gate.py` (per §02-CONTEXT D-17). However, Plan 02-08's `tests/test_cycle_detector.py` gates its Pitfall #3 progress-signal test behind `importlib.import_module("clawteam.harness.theater_detector")`. Without a module at that exact path, the Plan 02-08 test stays skipped even after Plan 02-09 populates `progressSignal`. The plan's success criteria §6 requires "Plan 02-08's Pitfall #3 progress-signal test now runs green", so the import gate must flip.
- **Fix:** Shipped `clawteam/harness/theater_detector.py` as a thin re-export of `forced_progress_gate`, `increment_turn_counter`, `reset_turn_counter_state`, `NO_PROGRESS_THRESHOLD`. Canonical logic stays in `forced_progress_gate.py`; the alias file contains only imports + `__all__`.
- **Files modified:** `clawteam/harness/theater_detector.py` (created, 26 lines)
- **Verification:** `pytest tests/test_cycle_detector.py -q` → 7 passed (was 6 passed + 1 skipped before this plan).
- **Committed in:** `9403c4a` (Task 2 GREEN commit)

**2. [Rule 2 — Missing Critical] `_reset_drift_counters` now also clears the turn-counter callback**
- **Found during:** Task 2 (GREEN — transport wiring)
- **Issue:** The plan installs `_TURN_COUNTER_CALLBACK` via `set_turn_counter_callback` but the only documented teardown is "cleared on sprint stop" (Plan 02-11's responsibility). However, the existing `_reset_drift_counters()` function is also used by tests + SprintConductor on sprint start (per its docstring — "SprintConductor (Plan 02-11) calls this on sprint start/resume so a previous sprint's drift state does not leak across sprint boundaries"). Without also clearing the turn-counter callback there, a prior sprint's callback could survive into a new sprint's test run or into a resumed sprint that hasn't yet re-installed its own callback — causing counters to increment against the WRONG SprintState.
- **Fix:** Extended `_reset_drift_counters()` to also set `_TURN_COUNTER_CALLBACK = None` (belt-and-braces; Plan 02-11 will still call `set_turn_counter_callback(None)` explicitly, but the drift-counter reset path is a second safety net).
- **Files modified:** `clawteam/transport/base.py`
- **Verification:** `pytest tests/test_transport_envelope.py -q` → all pass (the reset helper is exercised by the auto-use fixture and the reset behaves correctly).
- **Committed in:** `9403c4a` (Task 2 GREEN commit)

**3. [Rule 3 — Blocking] `Question` constructor takes `body` kwarg, not `to_markdown(body=…)`**
- **Found during:** Task 2 (GREEN — question-writer implementation)
- **Issue:** The plan's code snippet writes `question.to_markdown(body=body)`. The actual `Question.to_markdown()` signature (from Plan 01-04 qa.py) takes no arguments — body is stored on the `Question` instance as a field and rendered from `self.body`. Calling `to_markdown(body=…)` would raise `TypeError`.
- **Fix:** Pass `body` at `Question(...)` construction, call `question.to_markdown()` with no args.
- **Files modified:** `clawteam/harness/forced_progress_gate.py` (`_write_question` method)
- **Verification:** `test_gate_writes_question_file_on_trigger` passes — question file parses back via `Question.from_markdown()` with matching `type="multi-choice"` + 3 choices + body.
- **Committed in:** `9403c4a` (Task 2 GREEN commit)

**4. [Rule 2 — Missing Critical] `_compute_per_agent_artifact_bytes` falls back to disk size when `metadata["size_bytes"]` is missing**
- **Found during:** Task 2 (GREEN — per-agent byte attribution)
- **Issue:** The plan's snippet reads `int(meta.get("size_bytes") or 0)`. However, Plan 02-06 Task 2's `.meta.json` writer records the metadata dict passed by the caller + a `written_at` timestamp — but callers (including existing non-sprint artifact writes) may omit `size_bytes`. Without a fallback, legitimate per-agent writes that lack `size_bytes` in metadata would be invisible to the gate's progress detector, causing false-positive theater triggers on real work.
- **Fix:** When `size_bytes` is missing or 0, fall back to `(artifacts_dir / artifact_name).stat().st_size`. The artifact file is guaranteed to exist at this point (it was written immediately before the `.meta.json` sidecar per the Plan 02-06 Hook 3 ordering).
- **Files modified:** `clawteam/harness/forced_progress_gate.py` (`_compute_per_agent_artifact_bytes`)
- **Verification:** `test_net_positive_artifact_delta_counts_as_progress` asserts the gate passes after a 100-byte write with explicit `size_bytes=100`; the fallback path is covered by future callers that may omit `size_bytes` (documented in the docstring).
- **Committed in:** `9403c4a` (Task 2 GREEN commit)

---

**Total deviations:** 4 auto-fixed (1 blocking cross-plan import gate, 1 missing teardown path, 1 blocking API mismatch, 1 missing-field fallback).
**Impact on plan:** All auto-fixes necessary for correctness — the gate would fail tests #3 (question-file API mismatch), leave Plan 02-08's skipif gated forever (shim), and produce false-positive triggers under missing `size_bytes` metadata (fallback). No scope creep.

## Issues Encountered

- **`ruff --fix` stripped an unused `Path` import from `forced_progress_gate.py`** — benign, caught by the post-edit hook reminder. The file continues to reference `Path` indirectly through `get_data_dir()` return type; no functional change.
- **The plan's code snippet for `_pre_deliver_hooks` implied extracting `turn_id` from a `TurnEnvelope` field not yet present on `TeamMessage`.** Resolved by extracting `turn_id` directly from the validated payload dict (preferring `turn_id`, then `turnId`, then `msg.request_id`) — matches Plan 02-08's existing `request_id`-based round-trip tracking.

## TDD Gate Compliance

Task sequence in git log:
1. `f26a920` — `test(02-09):` — RED gate ✓
2. `9403c4a` — `feat(02-09):` — GREEN gate ✓

No REFACTOR commit needed — the GREEN implementation is the shipping shape.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

Plan 02-09 completes Wave 3's theater-detector work. The forward contract for Plan 02-11 (SprintConductor) is documented above: install the turn-counter callback on sprint start + register the gate's `TaskCompleted` subscription + tear down on sprint stop. Plan 02-11 can now wire the 11-agent gstack sprint end-to-end with theater + drift + cycle + freeze all enforced.

**Plan 02-08's previously-skipped Pitfall #3 test is now green** — no further Plan 02-08 work needed.

**Threat model coverage:**
- T-02-22 (counter manipulation via crafted turn_id): accept — documented in plan threat model; defense via artifact-bytes delta check is live.
- T-02-23 (FP on shared-file writes): mitigated — `_compute_per_agent_artifact_bytes` sums strictly per author-agent; tested via `test_per_agent_not_sprint_wide_isolation`.
- Pitfall #3 (FP cycle on iteration): mitigated — `progressSignal` field populated on every `recentEvents` entry; cycle detector reads it; integration test green.
- Pitfall #16 (specialists flagged as theater): mitigated — counter is per-agent; gate reason names the specific stalled agent only.

## Self-Check: PASSED

**Files:**
- `clawteam/harness/forced_progress_gate.py` — FOUND (271 lines)
- `clawteam/harness/theater_detector.py` — FOUND (26 lines)
- `clawteam/harness/artifacts.py` — MODIFIED (turn_counter_callback wiring)
- `clawteam/transport/base.py` — MODIFIED (set_turn_counter_callback + _pre_deliver_hooks hook)
- `clawteam/team/routing_policy.py` — MODIFIED (progressSignal key on _append_event)
- `tests/test_forced_progress_gate.py` — FOUND (9 tests)

**Commits:**
- `f26a920` — FOUND in git log (RED)
- `9403c4a` — FOUND in git log (GREEN)

**Structural greps (all passed):**
- `class forced_progress_gate(PhaseGate):` = 1 ✓
- `NO_PROGRESS_THRESHOLD = 2 | consecutive_no_progress` = 2 ✓
- `sprint[-_]total` = 0 ✓ (no sprint-wide summation path)
- `_compute_per_agent_artifact_bytes` = 2 ✓ (def + call)
- `.meta.json` = 5 ✓
- `def increment_turn_counter | def reset_turn_counter_state` = 2 ✓
- `ForcedProgressTriggered` = 4 ✓
- `turn_counter_callback` in artifacts.py = 5 ✓
- `set_turn_counter_callback | _TURN_COUNTER_CALLBACK` in transport/base.py = 10 ✓
- `progressSignal | progress_signal` in routing_policy.py = 8 ✓
- `def test_` in tests/test_forced_progress_gate.py = 9 ✓
- 4 critical Pitfall tests named explicitly = 4 ✓

**Tests:**
- `tests/test_forced_progress_gate.py` — 9 passed
- `tests/test_cycle_detector.py` — 7 passed (including the previously-skipped Pitfall #3 test, now active)
- `tests/test_transport_envelope.py tests/test_artifact_caps.py` — all pass
- `tests/test_template_regression_matrix.py` — 12 passed
- `tests/test_sprint_state.py tests/test_interaction_gate.py tests/test_event_types_phase2.py` — peer green
- Full suite: **734 passed** in 107 s
- Ruff clean on all modified files

---
*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Completed: 2026-04-20*
