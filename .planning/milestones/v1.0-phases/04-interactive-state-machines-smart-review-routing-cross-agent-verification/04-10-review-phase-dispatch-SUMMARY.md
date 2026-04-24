---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
plan: 10
subsystem: sprint-orchestration
tags: [asyncio, review-phase, sha-pin, event-bus, gate-chain, plugin-manager, cross-agent-verification, sycophancy]

requires:
  - phase: 02-sprint-engine-and-preventions
    provides: "SprintConductor + SprintState.review_sha + EventBus + gate chain composition"
  - phase: 02-sprint-engine-and-preventions
    provides: "save_sprint_state module-level helper (ISS-09 call-site contract)"
  - phase: 04-05
    provides: "PluginManager.get_plugin_gates + get_verification_pairs accessors"
  - phase: 04-03
    provides: "CrossAgentVerificationGate + VerificationPair pydantic model"
  - phase: 04-02
    provides: "MidReviewThrash + SycophancyCascadeDetected event dataclasses"
  - phase: 04-06
    provides: "GstackReviewRouter (consumed via plugin_manager.get_review_routers)"

provides:
  - "async def dispatch_review_phase — parallel peers + sequential reviewer + SHA-pin + events"
  - "SprintConductor._dispatch_review_phase sync wrapper (asyncio.run bridge per PLAN_PREP_NOTES A4)"
  - "SprintConductor ctor plugin_manager kwarg + self._plugin_manager storage"
  - "SprintConductor._build_gate_chain extension: unions plugin-contributed gates + CrossAgentVerificationGate per phase (closes ISS-03 + ISS-07)"
  - "_compute_agreement_rate severity-only math (RESEARCH Open Q3)"
  - "SHA-pin + diff-delta helpers mirroring evidence_gate subprocess pattern (T-04-31 mitigation)"

affects:
  - "Plan 04-11 GstackSprintPlugin — now its contribute_gates + contribute_verification_pairs hooks actually execute"
  - "Plan 04-13 adversarial routing golden tests (consumes dispatch_review_phase orchestrator)"
  - "Phase 5 spawn integration — default spawn_fn stub is the seam Phase 5 replaces"

tech-stack:
  added:
    - "asyncio.gather + return_exceptions=True for parallel reviewer dispatch"
  patterns:
    - "Pattern: async dispatcher in its own module + thin sync wrapper on conductor (keeps conductor <700 LOC)"
    - "Pattern: subprocess shell=False + 10s timeout mirrors evidence_gate (T-04-31 mitigation)"
    - "Pattern: injectable subprocess_runner + spawn_fn seams for test + Phase-5 integration"
    - "Pattern: router try/except-per-call with logged-skip (RFC 001 §4.3b req 4)"
    - "Pattern: plugin_manager accessor try/except with logged warning + fallback — gate chain must never crash"

key-files:
  created:
    - "clawteam/sprint/review_phase.py — async dispatch_review_phase + agreement-rate + SHA/diff helpers + default spawn stub"
    - "tests/test_review_phase_dispatch.py — 28 tests (20 Task 1 + 1 Task 2 + 6 Task 3 + 1 ISS-09)"
  modified:
    - "clawteam/sprint/conductor.py — +asyncio import, +plugin_manager ctor kwarg, +self._plugin_manager storage, +_dispatch_review_phase method, +_build_gate_chain plugin-union extension"

key-decisions:
  - "04-10 Task 1: dispatch_review_phase is module-level async in new file; thin sync wrapper on SprintConductor per PLAN_PREP_NOTES A4 decision. Conductor stays 686 LOC (<700 budget); review-phase orchestration testable in isolation."
  - "04-10 Task 1: _compute_agreement_rate skips Exception entries from return_exceptions=True gather (so one spawn failure does not drag the denominator down and mask a real cascade across surviving reviewers)."
  - "04-10 Task 1: _default_spawn_fn stub is the Phase-5 replacement seam. Real SpawnBackend bridge uses loop.run_in_executor(None, _spawn_reviewer_sync, ...) per PLAN_PREP_NOTES A-spawn — deferred to Phase 5 agent-spawn integration."
  - "04-10 Task 1: _collect_routers uses best-effort accessor cascade (plugin_manager.get_review_routers first, then phase_registry.review_routers fallback) so dispatcher doesn't couple to one plugin-manager API shape."
  - "04-10 Task 2: sync wrapper loads state inside self._lock but runs asyncio.run OUTSIDE the lock (prevents lock-held-across-await deadlock). resolved_pm uses getattr(self, '_plugin_manager', None) so the wrapper worked even before Task 3 committed the ctor update."
  - "04-10 Task 3: _build_gate_chain orders chain as EvidenceGate → forced_progress_gate → [CrossAgentVerificationGate(s) per phase] → [plugin gates per phase] → (InteractionGate?). Cross-verify precedes plugin gates because pairwise-consistency check fails earlier + gives clearer operator signal than plugin-specific gates."
  - "04-10 Task 3: both plugin_manager accessors wrapped in try/except with logged warning — if get_verification_pairs OR get_plugin_gates raises, gate chain still ships the standard 2 base gates (EvidenceGate + forced_progress_gate). Plan requires chain never crash on plugin-manager failure (T-04-17 DoS mitigation posture)."

patterns-established:
  - "Pattern: keep SprintConductor under 700 LOC by spinning per-phase orchestration into own module with thin sync wrapper method"
  - "Pattern: plugin-contributed gate discovery via accessor cascade in _build_gate_chain — plugin-manager is Optional, and each accessor is individually try/except'd so one broken plugin cannot break the whole chain"
  - "Pattern: severity-only agreement rate for sycophancy detection (RESEARCH Open Q3) — per-finding severity comparison, exceptions skipped"

requirements-completed: [SPRINT-04, QUALITY-07, QUALITY-09, QUALITY-13]

duration: 18min
completed: 2026-04-21
---

# Phase 4 Plan 10: Review-Phase Dispatch Summary

**async dispatch_review_phase orchestrates parallel peer reviewers via asyncio.gather with SHA-pin + mid-review-thrash + sycophancy-cascade event emission; SprintConductor gains plugin_manager kwarg and _build_gate_chain now unions plugin-contributed gates + CrossAgentVerificationGate instances per phase (closes ISS-03 + ISS-07).**

## Performance

- **Duration:** ~18 min
- **Started:** 2026-04-21T10:25:00Z (approx, session start after context load)
- **Completed:** 2026-04-21T10:43:07Z
- **Tasks:** 3 (Task 1 TDD feat, Task 2 feat, Task 3 TDD test+feat)
- **Files modified:** 3 (1 created, 2 modified — conductor.py Task 3 changes landed via commit 5902ede per note below)

## Accomplishments

- `clawteam/sprint/review_phase.py` (297 LOC, > 180 min requirement): async `dispatch_review_phase` orchestrates Review-phase parallel dispatch with review_sha pin at entry, mid-review HEAD-advance detection (emits `MidReviewThrash`), sycophancy cascade alarm on agreement-rate threshold crossings (emits `SycophancyCascadeDetected`), reviewer floor always included, router-contributed participants unioned with floor, router exceptions try/except'd per RFC 001 §4.3b req 4.
- `_compute_agreement_rate` (severity-only per RESEARCH Open Q3) skips exception entries so a single spawn failure does not mask real cascade.
- `SprintConductor._dispatch_review_phase(sprint_id, *, plugin_manager=None, bus=None, spawn_fn=None)` thin sync wrapper invokes `asyncio.run(dispatch_review_phase(...))` — preserves CORE-07 sync-persistence contract (async only inside dispatcher per PLAN_PREP_NOTES A4).
- `SprintConductor.__init__` gained optional `plugin_manager` kwarg + `self._plugin_manager` storage (backward-compatible: defaults None, Phase 2 callers unaffected).
- `SprintConductor._build_gate_chain` now unions (a) `CrossAgentVerificationGate` instances constructed from `plugin_manager.get_verification_pairs()` filtered by current_phase AND (b) plugin-contributed gates from `plugin_manager.get_plugin_gates(current_phase)` into the standard EvidenceGate → forced_progress_gate → InteractionGate chain. Both accessors try/except'd with logged warning fallback (T-04-17 DoS mitigation posture). **Closes ISS-03 (ShipApprovalGate unreachable) and ISS-07 (CrossAgentVerificationGate unreachable).**
- ISS-09 save_sprint_state module-level helper presence asserted via new test (was already satisfied by Phase 2 state.py:174).
- 28 tests green in `tests/test_review_phase_dispatch.py` (20 Task 1 + 1 Task 2 wrapper smoke + 6 Task 3 gate-chain + 1 ISS-09); Phase 2 `test_sprint_conductor.py` 27 tests stay green; plugin/CAV gate tests 32 green — 87 tests total in scoped regression.
- Conductor LOC 686 (< 700 budget).

## Task Commits

1. **Task 1: dispatch_review_phase + tests** - `a0d401d` (feat — fused test+impl per plan's single action block; TDD-shaped)
2. **Task 2: _dispatch_review_phase conductor wrapper** - `ff7519a` (feat)
3. **Task 3 RED: failing gate-chain plugin-union tests** - `8083b94` (test)
4. **Task 3 GREEN: _build_gate_chain plugin-union wiring** - **landed as part of `5902ede docs(04-12)`** (see "Issues Encountered" — cross-executor stash interaction; the conductor.py plugin-union extension IS committed and all tests green, just combined with a sibling executor's docs commit rather than its own `feat(04-10):` commit)

_Note: Plan 04-10 is wave-3 parallel with Plans 11 and 12. Sibling executors committed Plan 11 and 12 work during this session; one of those commits (`5902ede`) inadvertently included Task 3's conductor.py edits in its working-tree snapshot. Functional correctness is preserved (86 tests green); the gate-chain union, plugin_manager ctor kwarg, and CrossAgentVerificationGate construction are all in the tree at HEAD._

**Plan metadata:** (this SUMMARY.md — separate commit below)

## Files Created/Modified

- `clawteam/sprint/review_phase.py` (CREATED, 297 LOC) — async Review-phase dispatcher + agreement-rate + SHA/diff helpers + default spawn stub (Phase 5 replacement seam).
- `clawteam/sprint/conductor.py` (MODIFIED, +112 LOC net, total 686) — `import asyncio as _asyncio`; `plugin_manager` ctor kwarg + `self._plugin_manager` storage; new `_dispatch_review_phase` sync wrapper method; `_build_gate_chain` extended to union plugin-contributed gates + CrossAgentVerificationGate instances filtered by `pair.phase == state.current_phase`.
- `tests/test_review_phase_dispatch.py` (CREATED, 629 LOC, 28 tests) — Task 1 dispatch tests (20) + Task 2 conductor wrapper smoke (1) + Task 3 gate-chain plugin-union tests (6) + ISS-09 helper assertion (1).

## Decisions Made

All key decisions recorded in frontmatter `key-decisions`. Summary:

- **Module split** (PLAN_PREP_NOTES A4): async dispatcher lives in `clawteam/sprint/review_phase.py`; `SprintConductor` gets thin `_dispatch_review_phase` sync wrapper using `asyncio.run`. Keeps conductor under 700 LOC + isolates review-phase testability.
- **Agreement-rate math** (RESEARCH Open Q3): severity-only, skips Exception entries from `return_exceptions=True` gather so surviving-reviewer cascades are not masked by a single spawn failure.
- **Gate chain ordering**: EvidenceGate → forced_progress_gate → CrossAgentVerificationGate(s) → plugin gates → (InteractionGate?). CAV gates precede plugin gates because pairwise-consistency failures give clearer operator signal earlier in the chain.
- **Accessor cascade + try/except per accessor** for `_collect_routers` + `_build_gate_chain` plugin calls — gate chain must never crash on a broken plugin-manager accessor (T-04-17 DoS posture).

## Deviations from Plan

None from the deviation-rule perspective — the plan executed as written, no Rule 1/2/3 auto-fixes needed during implementation. One small BC belt-and-braces: Task 2's wrapper used `getattr(self, "_plugin_manager", None)` so it worked even before Task 3's ctor update landed (defensive, not a deviation).

**Total deviations:** 0 auto-fixed (plan specification was precise enough that no correctness/security/blocking fixes surfaced during execution).

## Issues Encountered

**Cross-executor stash interaction (wave-3 parallel):** Mid-way through Task 3 implementation, a sibling executor (Plan 04-12 docs) ran `git commit` with my un-committed conductor.py Task 3 changes in the working tree. Those changes were swept into commit `5902ede docs(04-12): complete sprint-approve-cli plan` along with Plan 12's legitimate STATE/REQUIREMENTS/ROADMAP/SUMMARY edits. Per the "NEVER run destructive git commands" rule I did NOT rewrite history; instead I restored my changes via `git checkout stash@{0} -- clawteam/sprint/conductor.py` before the sibling's commit wiped them. Result: functionally correct tree (all 28 Plan 04-10 tests + 27 Phase 2 BC + 32 plugin/CAV tests green), but Task 3's conductor.py changes are not in a pristine `feat(04-10):` commit — they're in `5902ede`. This is cosmetic not functional; future audits should grep `plugin_manager` across the wave-3 commit range to see the full Task 3 wiring.

**Pre-existing full-suite ordering flake** (`test_six_evidence_schemas_registered` + `test_evidence_schema_collision_when_registry_present`): confirmed by stash-bisection to predate Plan 04-10 work. Phase 3's `EvidenceSchemaRegistry` singleton is not reset between tests, so running the full suite after certain earlier tests leaves `design-doc` registered and the plugin-hook collision test fails on second-registration. Tests pass in isolation and in scoped module runs. Ownership stays with Plan 04-13 / test-isolation hygiene work.

## Self-Check: PASSED

- File `clawteam/sprint/review_phase.py` exists: FOUND (297 LOC)
- File `tests/test_review_phase_dispatch.py` exists: FOUND (629 LOC)
- File `clawteam/sprint/conductor.py` extended: FOUND (686 LOC, contains `plugin_manager=None`, `self._plugin_manager`, `_dispatch_review_phase`, `get_verification_pairs`, `get_plugin_gates`, `CrossAgentVerificationGate`)
- Commit `a0d401d` exists: FOUND (feat(04-10): implement dispatch_review_phase)
- Commit `ff7519a` exists: FOUND (feat(04-10): _dispatch_review_phase sync wrapper)
- Commit `8083b94` exists: FOUND (test(04-10): failing gate-chain plugin-union tests)
- Commit `5902ede` carries Task 3 conductor.py edits: FOUND (see Issues Encountered)
- All 13 acceptance-criteria greps pass: CONFIRMED.
- 28 Plan 04-10 tests green + 27 Phase 2 BC + 32 plugin/CAV: CONFIRMED (87 tests total scope).
- Conductor LOC 686 < 700 budget: CONFIRMED.

## Next Phase Readiness

- **Plan 04-11 (already shipped as sibling 39ede8f)**: `GstackSprintPlugin.contribute_gates({"ship": [ShipApprovalGate()]})` + `contribute_verification_pairs([test-report↔build-report, design-doc↔office-hours])` now actually execute in production — Task 3 wired the consumption side.
- **Plan 04-13 adversarial routing golden tests**: `dispatch_review_phase` + its `_compute_agreement_rate` are now the orchestrator goldens will exercise.
- **Phase 5 spawn integration**: `_default_spawn_fn` stub is the Phase 5 replacement seam. Real integration wraps synchronous `SpawnBackend.spawn(...)` with `loop.run_in_executor(None, _spawn_reviewer_sync, ...)` per PLAN_PREP_NOTES A-spawn.

---
*Phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification*
*Plan: 10 — review-phase-dispatch*
*Completed: 2026-04-21*
