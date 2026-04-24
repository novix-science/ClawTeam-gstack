---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 01
subsystem: events
tags: [events, plugin-hook, phase-2, evidence-schemas, dataclasses, veto-pattern]

requires:
  - phase: 01-core-harness-extensions
    provides: HarnessEvent base, EventBus veto pattern, HarnessPlugin.contribute_* hook convention, PluginManager._instantiate_and_register funnel
provides:
  - 8 additive event dataclasses on HarnessEvent (BeforeToolCall, BeforeFileWrite, FreezeChange, MalformedEnvelope, DriftRegression, CycleDetected, ForcedProgressTriggered, ArtifactCapExceeded)
  - contribute_evidence_schemas plugin hook (empty-dict default)
  - Plugin-loader loop that funnels schema contributions through a lazy-imported register_schema (Plan 02-04 lands the target)
affects: [02-02, 02-03, 02-04, 02-05, 02-06, 02-07, 02-08, 02-09, 02-10, 02-11, 02-12, 03-*]

tech-stack:
  added: []
  patterns:
    - "Veto-shape Before* events: veto: bool = False + veto_reason: str = '' (extends Phase 1 BeforeWorkerSpawn template)"
    - "Cross-wave lazy-import guard: `except (ModuleNotFoundError, ImportError)` tolerates modules that later waves deliver (Plan 01-03 pattern)"
    - "Notification events omit veto field — pure report shape matching PhaseTransition"

key-files:
  created:
    - tests/test_event_types_phase2.py
  modified:
    - clawteam/events/types.py
    - clawteam/plugins/base.py
    - clawteam/plugins/manager.py
    - tests/test_plugin_hooks.py

key-decisions:
  - "Widened lazy-import guard to catch both ModuleNotFoundError and ImportError because `from clawteam.harness import evidence_schemas` raises ImportError when the submodule is absent but the parent package exists — ModuleNotFoundError alone is insufficient"
  - "Left `clawteam/events/bus.py` unchanged: existing veto-loop at §86-101 already handles the new Before* events correctly (SC#10 invariant)"
  - "Used plain `dict` / `list` / `tuple` annotations (no `dict[str, Any]`) to stay consistent with existing HarnessEvent subclasses like `BeforeWorkerSpawn.command: list[str]`"

patterns-established:
  - "Phase 2 notification events are pure report-shape dataclasses (no veto field); only Before* events carry veto/veto_reason"
  - "Wave 1 plugin-loader hooks use lazy-import + broad import-error guard so later-wave modules can land without breaking Wave 1 stubs"

requirements-completed: [SPRINT-01, SAFETY-01, SAFETY-02, SAFETY-03, SAFETY-04, QUALITY-02, QUALITY-11]

duration: 8min
completed: 2026-04-20
---

# Phase 02 Plan 01: Phase-2 Event Surface + Evidence-Schema Plugin Hook Summary

**Eight additive HarnessEvent dataclasses (BeforeToolCall, BeforeFileWrite, FreezeChange, MalformedEnvelope, DriftRegression, CycleDetected, ForcedProgressTriggered, ArtifactCapExceeded) plus contribute_evidence_schemas plugin hook with lazy-import loader — unblocks all Phase 2 waves with zero runtime deps.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-20T09:55:00Z
- **Completed:** 2026-04-20T10:03:00Z
- **Tasks:** 2 (RED + GREEN)
- **Files modified:** 5 (3 source, 2 test; 1 test file new)

## Accomplishments

- 8 Phase-2 event dataclasses now exist in `clawteam/events/types.py` — every Phase 2 plan can import the event class it emits.
- `HarnessPlugin.contribute_evidence_schemas() -> dict[str, type]` hook declared with `{}` default on the base class — slots in beside Phase 1's `contribute_phases` / `contribute_phase_roles` / `contribute_review_routers`.
- `PluginManager._instantiate_and_register` now loops schemas through a lazy-imported `register_schema` guarded against absent modules — safe to merge alongside Plan 02-04's wave-peer.
- Phase 0 template regression matrix green (12/12); full test suite green (666/666).

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — failing tests for new events + hook** — `c253cd5` (test)
2. **Task 2: GREEN — add 8 dataclasses + hook + manager wiring** — `41c3ad9` (feat)

_Note: GREEN commit also includes the widened `ImportError` guard (Rule 1 auto-fix discovered during verification)._

## Files Created/Modified

### Event dataclasses (new, file line ranges)
- `clawteam/events/types.py:201-210` — `BeforeToolCall(HarnessEvent)` — agent_name, tool_name, args, veto, veto_reason
- `clawteam/events/types.py:212-221` — `BeforeFileWrite(HarnessEvent)` — agent_name, path, size_bytes, veto, veto_reason
- `clawteam/events/types.py:226-234` — `FreezeChange(HarnessEvent)` — action, path, agent, reason, actor
- `clawteam/events/types.py:237-243` — `MalformedEnvelope(HarnessEvent)` — agent, violation, turn_id
- `clawteam/events/types.py:246-252` — `DriftRegression(HarnessEvent)` — agent, consecutive_count, last_violation
- `clawteam/events/types.py:255-262` — `CycleDetected(HarnessEvent)` — pair (tuple), topic_hash, route_keys (list), window_size (default 20)
- `clawteam/events/types.py:265-271` — `ForcedProgressTriggered(HarnessEvent)` — agent, consecutive_no_progress, question_id
- `clawteam/events/types.py:274-280` — `ArtifactCapExceeded(HarnessEvent)` — artifact_name, size_bytes, cap_bytes, scope ("file"|"phase")

### Plugin hook (new method, line ranges)
- `clawteam/plugins/base.py:79-93` — `contribute_evidence_schemas(self) -> dict[str, type]` with `{}` default. Signature copy-pastable for Plan 02-04 test harness:
  ```python
  def contribute_evidence_schemas(self) -> dict[str, type]:
      """Contribute artifact-frontmatter schemas to EvidenceSchemaRegistry."""
      return {}
  ```

### Plugin manager wiring (new block, line ranges)
- `clawteam/plugins/manager.py:152-166` — lazy-import guard inside `_instantiate_and_register`:
  ```python
  schemas = plugin.contribute_evidence_schemas() or {}
  if schemas:
      try:
          from clawteam.harness import evidence_schemas as _es  # noqa: PLC0415
      except (ModuleNotFoundError, ImportError):
          _es = None  # type: ignore[assignment]
      if _es is not None:
          for schema_name, schema_cls in schemas.items():
              _es.register_schema(schema_name, schema_cls)
  ```

### Tests
- `tests/test_event_types_phase2.py` (new, 163 lines) — 11 test functions covering shape, veto roundtrip, inheritance invariant, and end-to-end EventBus veto for `BeforeFileWrite`.
- `tests/test_plugin_hooks.py` (extended, +88 lines) — 4 new tests: default-empty, hook-exists-on-base, missing-registry lazy-guard, collision semantics.

## Decisions Made

- **Widened lazy-import guard** from `ModuleNotFoundError` only to `(ModuleNotFoundError, ImportError)`. Python raises `ImportError` (not `ModuleNotFoundError`) when using `from pkg import submodule` where the submodule is absent but `pkg` exists — the plan's original guard was too narrow. Caught by Task 2 verification; Rule 1 fix.
- **No edits to `clawteam/events/bus.py`.** The existing veto loop at §86-101 already walks subscribers in priority order and tolerates any `HarnessEvent` subclass — SC#10 invariant from plan holds.
- **Plain `dict` / `list` / `tuple` annotations** (not `dict[str, Any]`) on new dataclass fields — matches the existing codebase style in `clawteam/events/types.py` (e.g., `BeforeWorkerSpawn.command: list[str]`), avoids importing `Any` for ephemeral data fields.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Widened lazy-import guard to catch `ImportError` as well as `ModuleNotFoundError`**
- **Found during:** Task 2 GREEN verification
- **Issue:** Plan specified `except ModuleNotFoundError` only. Python's `from clawteam.harness import evidence_schemas` raises `ImportError` (not `ModuleNotFoundError`) when the submodule is absent but the parent package exists — exactly the wave-1 scenario Plan 02-04 creates. Test `test_plugin_manager_loops_evidence_schemas_when_registry_missing` caught this.
- **Fix:** Changed `except ModuleNotFoundError:` to `except (ModuleNotFoundError, ImportError):` in `clawteam/plugins/manager.py:160`.
- **Files modified:** `clawteam/plugins/manager.py`
- **Verification:** `pytest tests/test_plugin_hooks.py::test_plugin_manager_loops_evidence_schemas_when_registry_missing -q` passes; full suite stays 666/666.
- **Committed in:** `41c3ad9` (rolled into the GREEN commit since it was a same-task correctness fix)

**2. [Documentation note — not a code deviation] `veto: bool = False` occurrence count**
- **Plan acceptance criterion:** `grep -c "veto: bool = False" clawteam/events/types.py >= 6 (existing 4 + new 2)`.
- **Actual codebase:** only 1 existing `veto: bool = False` (`BeforeWorkerSpawn` at §31). New plan adds 2 (`BeforeToolCall`, `BeforeFileWrite`). Actual count: **3**, not ≥6.
- **Resolution:** The criterion's "existing 4" count was incorrect vs. the actual repository state. All 8 new classes and both veto fields are present exactly as specified in §02-PATTERNS.md §10. No code change needed; noting here for audit trail.

---

**Total deviations:** 1 code auto-fix (Rule 1 - bug in plan's lazy-import guard) + 1 documentation-only note (incorrect plan grep count)
**Impact on plan:** Both benign. The lazy-import fix was essential for the cross-wave parallelism contract; without it, any wave-1 plugin contributing schemas would crash when Plan 02-04 is absent.

## Issues Encountered

- None beyond the `ImportError` vs `ModuleNotFoundError` nuance documented above.

## User Setup Required

None — plan is pure additive Python code, no external services.

## Forward Contracts for Downstream Plans

| Event class | Consumed by | Emit site (target plan) |
|---|---|---|
| `BeforeToolCall` | `_tool` MCP wrapper + `/careful`-style interceptors | 02-06 (MCP hook chain) |
| `BeforeFileWrite` | `ArtifactStore.write`, `WorkspaceManager` git-write paths, `/freeze` guard | 02-06 (artifacts hook chain), 02-05 (freeze audit) |
| `FreezeChange` | `freeze_audit.jsonl` append-only writer | 02-05 (freeze audit JSONL) |
| `MalformedEnvelope` | envelope validator first-time warn path | 02-03 (envelope validator) |
| `DriftRegression` | envelope validator escalation path (≥8 consecutive) | 02-03 (envelope validator) |
| `CycleDetected` | `DefaultRoutingPolicy.decide` cycle detector | 02-08 (routing cycle detector) |
| `ForcedProgressTriggered` | theater/no-progress phase gate | 02-09 (theater gate) |
| `ArtifactCapExceeded` | per-file and per-phase artifact caps | 02-10 (artifact caps) |

Plugin-hook contract:
- `HarnessPlugin.contribute_evidence_schemas()` consumed by Plan 02-04's `EvidenceSchemaRegistry.register_schema(name, cls)` and by Phase 3's `GstackSprintPlugin` (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro).

## Phase 0 Regression Invariant

- `pytest tests/test_template_regression_matrix.py -q` → **12 passed** (SC#10 held).
- Full suite: **666 passed, 2 warnings in 108.10s** (warnings are pre-existing fork() deprecation notices in `test_task_store_locking.py`, unrelated to this plan).

## Self-Check: PASSED

Verified before commit:
- `clawteam/events/types.py` contains 8 new `class … (HarnessEvent):` entries (grep count: 8 of 8 expected).
- `clawteam/plugins/base.py` contains exactly 1 `def contribute_evidence_schemas` (expected: 1).
- `clawteam/plugins/manager.py` contains 2 `contribute_evidence_schemas` occurrences (comment + call) and 1 `ModuleNotFoundError` guard (expected: ≥1 each).
- Commit `c253cd5` exists (RED) and `41c3ad9` exists (GREEN) in `git log --oneline`.
- All test files listed in `files_modified` exist on disk.

## Next Phase Readiness

- **All Wave 2+ Phase 2 plans unblocked** — every event class they emit now importable.
- **Plan 02-04** can land `clawteam/harness/evidence_schemas.py::register_schema` any time; the plugin loader will activate automatically once the module is importable.
- **No blockers** for parallel execution of Waves 2–4.

---
*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Completed: 2026-04-20*
