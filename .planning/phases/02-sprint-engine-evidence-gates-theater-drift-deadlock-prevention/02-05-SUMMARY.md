---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 05
subsystem: safety-rails
tags: [freeze-registry, safety-rail, audit-jsonl, file-locked, phase-2, singleton, path-canonicalization, pitfall-5, t-02-02]

requires:
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: "clawteam.fileutil.file_locked + atomic_write_text (Plan 01-02); clawteam.team.models.get_data_dir (pre-existing); clawteam.harness.exit_journal.FileExitJournal (JSONL append template)"
provides:
  - "FreezeRegistry class — sprint-scoped path write-lock registry (structural twin of PhaseRegistry)"
  - "FrozenPathError — ValueError subclass with D-12 message shape"
  - "get_freeze_registry / reset_freeze_registry — module-level singleton accessors"
  - "freeze_audit.jsonl — append-only audit log mirroring exit_journal.py"
  - "Pitfall #5 exemption — is_frozen returns False for paths under get_data_dir()"
  - "T-02-02 mitigation — Path.resolve(strict=False) canonicalization on store + compare"
affects: [02-10 safety-rail-subscribers, 02-11 sprint-conductor-pause-resume, 02-12 cli-freeze-unfreeze, 03 gstack-methodology-prompts]

tech-stack:
  added: []
  patterns:
    - "registry-singleton: module-level _registry: T | None with get_/reset_ accessor pair (mirrors PhaseRegistry, EventBus)"
    - "file-locked JSON persistence + append-only JSONL audit log (file_locked + atomic_write_text for mutable state; raw open-append for audit trail)"
    - "path canonicalization via Path.resolve(strict=False) at both store and query sites to defeat symlink / .. segment bypass"
    - "sprint-internal exemption (Pitfall #5): safety-rails opt out of vetoing paths under get_data_dir() so sprint pause/resume never deadlocks"

key-files:
  created:
    - clawteam/harness/freeze_registry.py
    - tests/test_freeze_registry.py
  modified: []

key-decisions:
  - "freeze.json payload schema: {paths: {agent: [sorted path-list]}, globs: [sorted glob-list]}. Planner-owned per 02-CONTEXT §scope-for-planner — chose sorted arrays over sets so JSON is deterministic and diff-friendly."
  - "Canonical form stored in freeze.json (not the raw user-supplied string) so equality check cannot be tricked by relative-path variants; the is_frozen comparator resolves the query path through the same pipeline."
  - "freeze_audit.jsonl uses raw open(..., 'a') per exit_journal.py pattern, NOT atomic_write_text — append-only is the invariant (last-write-wins would lose audit history)."
  - "Pitfall #5 exemption is evaluated FIRST in is_frozen (before any path-match or glob-match) so the short-circuit is unmistakable and cheap."

patterns-established:
  - "Registry singleton + file-locked JSON pattern: FreezeRegistry + PhaseRegistry now share the same shape — a future Registry protocol can unify them (planned per 02-CONTEXT lesson #3)."
  - "Audit JSONL pattern: freeze_audit.jsonl joins exit-journal.jsonl as the second JSONL-append-only audit surface; consistent {ts, action, ...context} schema; mirrors the line-count invariant used in exit_journal tests."
  - "Safety-rail opt-out via data-dir exemption: any future veto path on harness-internal state SHOULD use relative_to(get_data_dir()) for the same self-lockout avoidance."

requirements-completed: [SAFETY-02, SAFETY-04, QUALITY-06]

duration: 20min
completed: 2026-04-20
---

# Phase 02 Plan 05: FreezeRegistry Safety-Rail Summary

**Sprint-scoped FreezeRegistry singleton with file-locked freeze.json + append-only freeze_audit.jsonl, path canonicalization (T-02-02), and sprint-internal exemption (Pitfall #5).**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-20T09:55Z
- **Completed:** 2026-04-20T10:15Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 2 (1 new implementation, 1 new test module)

## Accomplishments

- FreezeRegistry singleton lives at `clawteam/harness/freeze_registry.py` (225 LOC), mirrors the PhaseRegistry / EventBus singleton shape so a future `Registry` protocol can unify them.
- `freeze(path, agent, reason, actor)` and `unfreeze(path, agent, reason, actor)` persist to `freeze.json` via `file_locked` + `atomic_write_text`; 8 concurrent writers serialize cleanly with no torn state and no stray `.tmp` files.
- `is_frozen(path)` consults per-agent paths + sprint-scoped globs, canonicalizing both stored and query paths via `Path.resolve(strict=False)` so relative-path bypass and symlink-into-frozen-dir bypass are both defeated (T-02-02).
- `is_frozen` returns `(False, "")` unconditionally for any path under `get_data_dir()` — sprint-internal writes (state.json, freeze.json, answers/) are never vetoed, so `clawteam sprint pause` never deadlocks writing its own checkpoint after a user types `/freeze /` (Pitfall #5).
- `FrozenPathError` subclasses `ValueError` with the D-12 message shape: `"<path> is /freeze-locked by <who_froze>; unfreeze via /unfreeze <path>"`. MCP `translate_error` auto-wraps it into an MCPToolError.
- Every `freeze` / `unfreeze` / `freeze_glob` appends one JSON line to `freeze_audit.jsonl`, mirroring `exit_journal.py::record_exit` verbatim (SAFETY-04 audit invariant).
- Singleton accessors `get_freeze_registry(team, sprint_id)` + `reset_freeze_registry()` match the Phase 1 `phase_registry.get_registry / reset_registry` pair. Plan 02-11 uses the accessor shape to rehydrate on sprint resume.

## Task Commits

Each TDD gate was committed atomically:

1. **Task 1 (RED): failing tests for FreezeRegistry** — `e0c01e6` (test)
2. **Task 2 (GREEN): FreezeRegistry + FrozenPathError + freeze_audit.jsonl** — `268e423` (feat)

## Files Created/Modified

- `clawteam/harness/freeze_registry.py` — **created** (225 LOC). Defines `FrozenPathError` (line 42), `_canonicalize` helper (line 52), `FreezeRegistry` class (line 63) with `_sprint_dir`/`_freeze_path`/`_audit_path`/`_load`/`_save`/`is_frozen`/`freeze`/`unfreeze`/`freeze_glob`/`_audit` methods, plus module-level `_registry` + `get_freeze_registry` (line 199) + `reset_freeze_registry` (line 217).
- `tests/test_freeze_registry.py` — **created** (271 LOC). 10 tests covering persistence, path-prefix match, data-dir exemption, symlink + `..`-segment canonicalization, FrozenPathError message shape, JSONL append-only invariant (5 lines after 5 actions), pause/resume rehydration via singleton, 8-thread concurrent writer last-write-wins.

## Class + method line ranges (plan `<output>` requirement)

| Symbol | File | Lines |
|--------|------|-------|
| `FrozenPathError` | `clawteam/harness/freeze_registry.py` | 42-50 |
| `_canonicalize` | `clawteam/harness/freeze_registry.py` | 52-60 |
| `FreezeRegistry` class | `clawteam/harness/freeze_registry.py` | 63-192 |
| `FreezeRegistry.__init__` | `clawteam/harness/freeze_registry.py` | 71-78 |
| `FreezeRegistry._sprint_dir` / `_freeze_path` / `_audit_path` | `clawteam/harness/freeze_registry.py` | 81-89 |
| `FreezeRegistry._load` / `_save` | `clawteam/harness/freeze_registry.py` | 92-110 |
| `FreezeRegistry.is_frozen` | `clawteam/harness/freeze_registry.py` | 113-142 |
| `FreezeRegistry.freeze` | `clawteam/harness/freeze_registry.py` | 144-150 |
| `FreezeRegistry.unfreeze` | `clawteam/harness/freeze_registry.py` | 152-159 |
| `FreezeRegistry.freeze_glob` | `clawteam/harness/freeze_registry.py` | 161-165 |
| `FreezeRegistry._audit` | `clawteam/harness/freeze_registry.py` | 170-190 |
| `get_freeze_registry` | `clawteam/harness/freeze_registry.py` | 199-214 |
| `reset_freeze_registry` | `clawteam/harness/freeze_registry.py` | 217-225 |

## Decisions Made

- **freeze.json payload is `{paths: {agent: sorted-list}, globs: sorted-list}`** — chose sorted lists over sets for JSON determinism + diff-friendly on-disk representation. Scope-for-planner per 02-CONTEXT.
- **Canonical form is stored, not the raw argument** — eliminates the whole category of "freeze `/tmp/foo`, check `../tmp/foo`" bypass. The query path goes through the same `_canonicalize` pipeline before lookup.
- **Pitfall #5 exemption is evaluated before any path-match or glob-match** — short-circuits the check cheaply and makes the self-lockout avoidance unmistakable from reading the code.
- **`freeze_audit.jsonl` uses raw `open(..., "a")`, not `atomic_write_text`** — append-only is the audit invariant; `atomic_write_text` would rewrite the whole file on every action, destroying history. Mirrors `exit_journal.py` verbatim.
- **Singleton returns `None` when called without `(team, sprint_id)` and no prior registry exists** — safety-rail subscribers that fire outside a sprint treat `None` as "pass through" (no veto possible without a registry). This matches research §Example 2's contract exactly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Hermetic test fixture needed a dedicated work_root outside the data dir**
- **Found during:** Task 2 GREEN run (symlink test).
- **Issue:** The plan's proposed `hermetic` fixture set `CLAWTEAM_DATA_DIR=tmp_path`, which meant every path the symlink test created under `tmp_path` (the "real" frozen target and the symlink itself) was also under the data dir — so the Pitfall #5 exemption correctly returned `(False, "")` and masked the T-02-02 symlink-bypass check. The test could not simultaneously exercise "freeze a real path" AND "data-dir exemption" using the same tmp_path as both roots.
- **Fix:** Split `tmp_path` into two sibling sub-roots inside the fixture: `data/` (CLAWTEAM_DATA_DIR, covered by Pitfall #5 exemption) and `work/` (attacker-controlled scratch space outside the data dir, where symlink targets live). Added a companion `work_root` fixture used only by the canonicalization/symlink test.
- **Files modified:** `tests/test_freeze_registry.py` — `hermetic` fixture + new `work_root` fixture + symlink test.
- **Verification:** All 10 tests pass; both the Pitfall #5 test and the T-02-02 symlink test exercise real code paths.
- **Committed in:** `268e423` (GREEN commit, part of the task 2 cycle).

---

**Total deviations:** 1 auto-fixed (Rule 3 Blocking)
**Impact on plan:** The fix was isolated to the test fixture. Implementation matched the plan verbatim. No scope creep; both safety invariants (Pitfall #5 exemption AND T-02-02 symlink defeat) are now provably exercised.

## Issues Encountered

- Pre-existing missing `yaml` Python module on the CI runner prevents collection of `tests/test_turn_envelope.py`. Out of scope for this plan (Plan 02-02 artifact, unrelated file); logged as deferred for Phase 2 wave-3 triage. Did not affect the Plan 02-05 test surface (`test_freeze_registry.py`, `test_template_regression_matrix.py`, `test_sprint_state.py`, `test_interaction_gate.py`, `test_phase_registry.py`, `test_event_bus.py`, `test_event_types_phase2.py`, `test_orchestrator_phase_registry.py`, `test_plugin_hooks.py` — all green).

## Confirmation of Key Invariants (plan `<output>` requirement)

### Pitfall #5 exemption
Proven by `test_is_frozen_returns_false_for_paths_under_data_dir`:
1. Registry constructs under team=`team-x` sprint=`sprint-a`.
2. Agent issues a maximally aggressive `freeze("/")` covering the whole filesystem.
3. The conductor writes `state.json` inside the sprint dir.
4. `is_frozen(state_json)` returns `(False, "")` — `clawteam sprint pause` can always write its own checkpoint.

### T-02-02 symlink / canonicalization mitigation
Proven by `test_is_frozen_canonicalizes_relative_paths_and_symlinks`:
1. `freeze(real_dir)` stores the canonical path.
2. A symlink `outside/link` pointing to a file inside `real_dir` is constructed in an unfrozen location.
3. `is_frozen(symlink)` returns `(True, ...)` — symlink bypass defeated.
4. `is_frozen(real_dir/../real/locked.txt)` returns `(True, ...)` — relative-path `..` segment collapse defeated.

### JSONL append-only invariant (line count == N after N writes)
Proven by `test_audit_jsonl_append_per_action`:
1. 3 `freeze` + 2 `unfreeze` actions in sequence.
2. `freeze_audit.jsonl` has exactly 5 lines (not 10, not 4, not "last write wins" rewriting).
3. Each line parses as JSON with the full `{ts, action, path, agent, reason, actor, sprint_id}` schema.
4. Action order is preserved: `["freeze", "freeze", "freeze", "unfreeze", "unfreeze"]`.

### Concurrent writer serialization
Proven by `test_8_concurrent_writers_freeze_json_last_write_wins`:
1. 8 threads concurrently call `freeze` with distinct agent keys.
2. No errors raised; `freeze.json` exists and parses as valid JSON.
3. No stray `.tmp` files in the sprint dir (atomic_write_text cleanup invariant holds under contention).

## Forward Contracts (plan `<output>` requirement)

- **Plan 02-10** (safety-rail subscribers) will:
  - Import `FrozenPathError` from this module and raise it from `BeforeFileWrite` / `BeforeToolCall` subscribers that see `is_frozen(event.path) == (True, reason)`.
  - Use the reason string verbatim as the `FrozenPathError` message (already has the D-12 shape).
  - Pass `None` from `get_freeze_registry()` through without vetoing (harness running outside a sprint).
- **Plan 02-11** (SprintConductor pause/resume) will:
  - Call `get_freeze_registry(team, sprint_id)` on resume. Because the accessor instantiates a fresh `FreezeRegistry(team, sprint_id)` when the module-level singleton is `None`, the constructor's `_load()` rehydrates `freeze.json` from disk automatically — no extra wiring needed.
  - Call `reset_freeze_registry()` before switching to a different sprint (test case covered by `test_freeze_persists_across_reset_and_rehydrate`).
- **Plan 02-12** (CLI `/freeze /unfreeze` commands) will:
  - Call `get_freeze_registry().freeze(path, agent=<cli-arg>, reason=<cli-arg>, actor=<current-user>)`.
  - Surface the `actor` field in `freeze_audit.jsonl` so the audit trail shows who requested the lock.
- **Phase 3** (GstackSprintPlugin) will:
  - Register agents whose roles already bind to the `agent` field shape (pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre).

## User Setup Required

None — registry is fully internal to the harness.

## Next Plan Readiness

- FreezeRegistry state-holder is green, tested, and committed. Plan 02-10 can subscribe to the new events without any registry-side changes.
- Phase 0 regression matrix still green (12/12). Phase 1 peer tests green (sprint_state 15/15, interaction_gate 8/8, phase_registry 4/4).
- No blockers for subsequent Phase 2 waves.

## Self-Check: PASSED

Verified artifacts exist and commits are present in the worktree branch:
- `clawteam/harness/freeze_registry.py` — FOUND (225 LOC)
- `tests/test_freeze_registry.py` — FOUND (271 LOC, 10 test functions)
- Commit `e0c01e6` (test RED) — FOUND in `git log`
- Commit `268e423` (feat GREEN) — FOUND in `git log`
- `ruff check` — clean on both files
- `ruff format --check` — clean on both files
- 10/10 freeze_registry tests pass
- 12/12 template regression matrix tests pass
- Phase 1 peer tests: sprint_state 15/15, interaction_gate 8/8, phase_registry 4/4 — all pass

## TDD Gate Compliance

- ✅ RED gate: commit `e0c01e6` — `test(02-05): add failing tests for FreezeRegistry ...`, verified 10/10 tests failed with `ModuleNotFoundError: No module named 'clawteam.harness.freeze_registry'` before any implementation landed.
- ✅ GREEN gate: commit `268e423` — `feat(02-05): FreezeRegistry + FrozenPathError + freeze_audit.jsonl append-only audit`, verified all 10 tests pass.
- No REFACTOR gate needed (implementation landed clean, matched research §Example 2 + plan task 2 action verbatim with the Rule 3 test-fixture fix).

---
*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Plan: 05*
*Completed: 2026-04-20*
