---
phase: 01-core-harness-extensions
plan: 01
subsystem: harness
tags: [harness, plugin, phase-registry, review-router, protocol, rfc-001, phase-1]

requires:
  - phase: 00-foundation-upstream-rfc
    provides: RFC 001 normative spec (§4.2 PhaseRegistry, §4.3/§4.3a/§4.3b hooks, §4.6 integration contract); regression matrix test harness
provides:
  - PhaseRegistry (in-memory, plugin-populated) with RegisteredPhase dataclass + get_registry()/reset_registry() singleton accessors
  - ReviewRouter Protocol forward-declaration (Phase 1 locks hook point, Phase 4 RFC will finalize interface)
  - Three optional HarnessPlugin hooks with empty-collection defaults: contribute_phases, contribute_phase_roles, contribute_review_routers
  - PluginManager._instantiate_and_register wiring that funnels hook results into the global registry after on_register(ctx)
affects:
  - 01-02 SprintState (SprintState is the forward reference inside review_router.py; Plan 01-02 lands the real module)
  - 01-03 InteractionGate (reuses PhaseGate + artifact conventions set in Phase 0)
  - 01-04 Phase 1 plugin integration
  - 01-05 HarnessOrchestrator consumption of the registry (currently populated but not yet consulted)
  - Phase 3 gstack sprint plugin (this is the seam gstack.toml will register its 7 phases through)
  - Phase 4 Review-phase routing (full ReviewRouter interface + consumer wiring)

tech-stack:
  added: []
  patterns:
    - Module-level singleton with get_*/reset_* pair (mirrors clawteam.events.global_bus)
    - Transactional register() — validate all inputs before mutating any state (no partial writes on error)
    - Protocol forward-declaration with TYPE_CHECKING string annotation for not-yet-existing forward references (SprintState)
    - Additive plugin hooks as base-class methods with empty-collection defaults (follows contribute_gates/contribute_prompts pattern)
    - Lazy import inside method body to break module-load circular imports between harness and plugins packages

key-files:
  created:
    - clawteam/harness/phase_registry.py
    - clawteam/harness/review_router.py
    - tests/test_phase_registry.py
    - tests/test_plugin_hooks.py
  modified:
    - clawteam/plugins/base.py
    - clawteam/plugins/manager.py

key-decisions:
  - D-02 applied — PhaseRegistry is pure in-memory, no disk persistence
  - D-03 applied — duplicate phase names across plugins raise ValueError at registration time (not harness-run time)
  - D-04 applied — three new hooks ship with empty-collection defaults so Phase 0 plugins (RalphLoop, etc.) stay valid without modification
  - Registry-level unowned-phase-role validation (RFC 001 §4.3a req 3) enforced in register(), not in base-class hook, so all callers are protected uniformly
  - register() is transactional — validation is complete before any mutation so a failed second-plugin call leaves the registry byte-identical to its pre-call state

patterns-established:
  - Phase 1 plugin seam: PluginManager._instantiate_and_register → get_registry().register(plugin.name, plugin.contribute_phases(), plugin.contribute_phase_roles(), plugin.contribute_review_routers())
  - Test-only reset hook for module-level singletons (reset_registry()) to avoid cross-test state pollution, mirroring reset_event_bus()
  - Protocol + TYPE_CHECKING string annotations let a Phase 1 artifact reference a Phase 2 type (SprintState) without runtime coupling

requirements-completed: [CORE-01, CORE-02, INT-01]

duration: 5min
completed: 2026-04-17
---

# Phase 01 Plan 01: Core Harness Extensions — Plugin Phase Seam Summary

**PhaseRegistry + ReviewRouter Protocol + three optional HarnessPlugin hooks, wired through PluginManager.\_instantiate_and_register; Phase 0 regression matrix stays 12/12 and no existing plugin needs modification.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-17T10:36:35Z
- **Completed:** 2026-04-17T10:41:53Z
- **Tasks:** 2 (TDD: 1 RED + 1 GREEN, no refactor needed)
- **Files created:** 4 (2 production + 2 test)
- **Files modified:** 2

## Accomplishments

- `PhaseRegistry` class at `clawteam/harness/phase_registry.py` — in-memory, order-preserving, with transactional `register()` that validates unowned-role keys and duplicate phase names before any mutation. Exposes `get_registry()` + `reset_registry()` singletons.
- `ReviewRouter` Protocol at `clawteam/harness/review_router.py` — Phase 1 locks the `match(diff_paths, state) -> list[str]` hook point; full rule-file / SHA-pinning / decorrelation semantics explicitly deferred to a future Phase 4 RFC update. `SprintState` forward reference is TYPE_CHECKING-only and becomes a live import when Plan 01-02 lands.
- Three new optional `HarnessPlugin` hooks adjacent to `contribute_gates`/`contribute_prompts`: `contribute_phases`, `contribute_phase_roles`, `contribute_review_routers` — all with empty-collection defaults so every existing plugin stays valid without modification (RFC 001 §4.7 compatibility guarantee).
- `PluginManager._instantiate_and_register` now funnels the three hooks' return values into `get_registry().register(...)` after `plugin.on_register(ctx)` and before `self._loaded[...]` — one call site, atomic, failure propagates.
- Full test suite: 620 passed (8 new + 612 existing); regression matrix 12/12; ruff clean on all 6 touched files.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for PhaseRegistry + three HarnessPlugin hooks (RED)** — `8cdff8f` (test)
2. **Task 2: Implement PhaseRegistry + ReviewRouter Protocol + three hooks + PluginManager wiring (GREEN)** — `6c07c5a` (feat)

_Note: no refactor commit — the GREEN implementation landed cleanly with no post-pass cleanup needed._

## Files Created/Modified

### Created

- `clawteam/harness/phase_registry.py` (137 lines) — `PhaseRegistry` class, `RegisteredPhase` frozen dataclass, `_PluginContribution` internal snapshot dataclass, `get_registry()` + `reset_registry()` module singletons. Transactional `register()`. Duplicate-name and unowned-role validation raising `ValueError` with RFC-traceable messages.
- `clawteam/harness/review_router.py` (34 lines) — One-method `ReviewRouter` Protocol with Phase-4-deferred docstring. `SprintState` forward reference as TYPE_CHECKING-only string annotation.
- `tests/test_phase_registry.py` (48 lines) — 4 flat functions: `test_empty_registry_is_valid`, `test_single_plugin_three_phases_registers_in_order`, `test_duplicate_phase_across_plugins_raises_value_error` (explicitly asserts post-failure state equals pre-call state per T-01-01 mitigation), `test_phase_roles_for_unowned_phase_raises_value_error`.
- `tests/test_plugin_hooks.py` (56 lines) — 4 flat functions covering the three base-class empty defaults and the `PluginManager` → `get_registry().register(...)` wiring via a `_GstackLikePlugin` test fixture. Setup/teardown via `reset_registry()`.

### Modified

- `clawteam/plugins/base.py` — Added `TYPE_CHECKING` imports for `Phase` and `ReviewRouter`; appended three new optional methods after `contribute_prompts`. Zero changes to `on_register`, `on_unregister`, `contribute_gates`, `contribute_prompts`.
- `clawteam/plugins/manager.py` — Added 8 lines inside `_instantiate_and_register` (lazy `from clawteam.harness.phase_registry import get_registry` + `get_registry().register(...)` call with the four positional arguments). Zero changes to `discover`, `load_from_module`, `load_from_entry_point`, `load_all_from_config`, `_build_context`, `loaded_plugins`, `unload`.

## Decisions Made

- **D-02 honored:** The registry is a plain in-memory singleton. No file-lock, no disk path, no `~/.clawteam/` directory touched. Test-only `reset_registry()` documents the intent clearly.
- **D-03 honored:** Duplicate phase names across plugins raise `ValueError` immediately during `_instantiate_and_register`, not when the harness later consults the registry. Message includes both the phase name and the attempting plugin name so operators can identify the conflict from the traceback alone. No swallowing of the error in manager.py — it propagates so the plugin load fails loudly (accepts T-01-02 trade-off per threat register).
- **D-04 honored:** All three new hooks are non-abstract with empty-collection defaults. The existing `RalphLoopPlugin` (and any future plugin that does not care about Phase 1 extensions) imports and runs unchanged. `contribute_gates`/`contribute_prompts` signatures and bodies are untouched.
- **Transactional register() pattern:** Validation runs completely before any mutation. A failed second-plugin registration leaves the registry byte-identical to its pre-call state, which the regression test `test_duplicate_phase_across_plugins_raises_value_error` explicitly asserts (closes T-01-01).
- **Unowned-role validation lives in the registry, not the hook:** `PhaseRegistry.register()` enforces RFC 001 §4.3a req 3 so every registration path (current `PluginManager` + any future entry-point loader) gets the same check uniformly. The hook itself stays dumb (returns whatever the plugin author typed) — the registry is the contract enforcer.
- **Lazy import inside `_instantiate_and_register`:** `from clawteam.harness.phase_registry import get_registry` happens inside the method body, not at module top. This breaks the latent circular import `harness.phase_registry` ↔ `plugins.base` (which imports `Phase` from `harness.phases` only via TYPE_CHECKING but the registry depends on it at runtime). Closes T-01-05.
- **Forward reference pattern for not-yet-existing types:** `review_router.py` references `SprintState` via `TYPE_CHECKING` + string annotation. `SprintState` lands in Plan 01-02; this file compiles and runs today because the string is only resolved by static type checkers, not at runtime.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Ruff I001 import-sort violations in both test files**

- **Found during:** Task 1 (RED) — initial ruff check after writing test files
- **Issue:** Ruff's isort-style rule flagged I001 on both test files: `tests/test_phase_registry.py` had a blank line between `import pytest` and `from clawteam...` that the rule rejects; `tests/test_plugin_hooks.py` had the `get_event_bus` `noqa: F401` import placed before `phase_registry` but isort wanted it re-grouped.
- **Fix:** Ran `.venv-sys/bin/ruff check tests/test_phase_registry.py tests/test_plugin_hooks.py --fix` — autoformat normalised the import groups. Final content is semantically identical (same three imports, same `noqa: F401`). Re-verified RED: still `ModuleNotFoundError: clawteam.harness.phase_registry`.
- **Files modified:** `tests/test_phase_registry.py`, `tests/test_plugin_hooks.py` (import whitespace only, no test logic changed).
- **Verification:** `ruff check` exits 0. Pytest collection still fails with the expected `ModuleNotFoundError`.
- **Committed in:** `8cdff8f` (Task 1 RED commit — the autofix was applied before commit, so the committed files are already ruff-clean).

**2. [Rule 3 — Blocking] Plan's `cd /home/jac/repos/ClawTeam-gstack` command would bypass this worktree**

- **Found during:** Task 1 & 2 verify steps
- **Issue:** The plan's verify/automated blocks all start with `cd /home/jac/repos/ClawTeam-gstack` (the main repo root). Running from there would pick up the main checkout's `clawteam/` package, not the worktree's modified copy, so the tests would not be validating the changes this agent just made.
- **Fix:** Executed every verify command from the worktree directory (`/home/jac/repos/ClawTeam-gstack/.claude/worktrees/agent-a2f7e75c`) using the system `.venv-sys/bin/python` interpreter. Confirmed via `sys.path[0]=''` + `clawteam.harness.phases.__file__` that Python picks up the worktree's package (cwd shadows the `.venv-sys` editable install). Result: all test/lint/regression commands validated the changes actually made in this worktree.
- **Files modified:** None — this is an execution-environment fix, not a code fix.
- **Verification:** `python -c "import clawteam.harness.phases; print(clawteam.harness.phases.__file__)"` from worktree prints the worktree path.
- **Committed in:** N/A — execution-only change.

---

**Total deviations:** 2 auto-fixed (2 Rule 3 blocking — 1 lint fix, 1 cwd routing)
**Impact on plan:** Neither deviation changed code intent or test logic. Import whitespace normalization is aesthetic; cwd routing is the mandatory way to run verification inside a git worktree. No scope creep.

## Issues Encountered

- None. The plan was specified at implementation-precise granularity and the TDD loop completed cleanly on the first attempt. GREEN passed without a REFACTOR cycle.

## TDD Gate Compliance

This plan is `type: execute` with per-task `tdd="true"`. Gate sequence verified in `git log`:

1. RED gate — `test(01-01): add failing tests for PhaseRegistry + three HarnessPlugin hooks` at `8cdff8f` (pytest confirmed `ModuleNotFoundError: clawteam.harness.phase_registry` before Task 2).
2. GREEN gate — `feat(01-01): PhaseRegistry + ReviewRouter Protocol + three optional HarnessPlugin hooks` at `6c07c5a` (8 new tests + 612 pre-existing pass; regression matrix 12/12).

No REFACTOR commit created because the GREEN implementation landed cleanly and the verification checks all passed without cleanup. RFC 001 §4.7 compatibility guarantee is the most important acceptance criterion and it is green.

## Verification Evidence

- `ruff check clawteam/harness/phase_registry.py clawteam/harness/review_router.py clawteam/plugins/base.py clawteam/plugins/manager.py tests/test_phase_registry.py tests/test_plugin_hooks.py` → exit 0.
- `pytest tests/test_phase_registry.py tests/test_plugin_hooks.py -v` → 8 passed.
- `pytest tests/test_template_regression_matrix.py -v` → 12 passed (Phase 0 regression matrix green — RFC 001 §4.7 compatibility).
- `pytest tests/ -q` → 620 passed, 2 unrelated `DeprecationWarning` entries from `tests/test_task_store_locking.py` that predate this plan.
- Import-sanity: `from clawteam.harness.phase_registry import PhaseRegistry, get_registry, reset_registry, RegisteredPhase` + `from clawteam.harness.review_router import ReviewRouter` + `hasattr(HarnessPlugin, 'contribute_phases' | 'contribute_phase_roles' | 'contribute_review_routers')` all succeed.
- Structural greps (all expected counts met): `class PhaseRegistry` × 1, `def register` × 1, `raise ValueError` × 2 (duplicate + unowned-role), `_REGISTRY` × 7 (declaration + get + reset + internal uses), `class ReviewRouter` × 1, `def match` × 1, `Protocol` × 4, `def contribute_phases` × 1, `def contribute_phase_roles` × 1, `def contribute_review_routers` × 1, `def contribute_gates` × 1 (preserved), `def contribute_prompts` × 1 (preserved), `get_registry().register` × 1.

## User Setup Required

None — no external service configuration required. Pure-Python in-process changes.

## Next Phase Readiness

**Plan 01-02 (SprintState):** Ready to begin. The `review_router.py` `SprintState` forward reference becomes a live import when 01-02's `clawteam/sprint/state.py` lands. No interface renegotiation needed.

**Plan 01-03 (InteractionGate):** Ready. Subclasses the existing `PhaseGate` ABC — orthogonal to this plan.

**Plan 01-04 (Phase 1 plugin integration):** Ready. The `get_registry()` singleton is the consumption surface; plugins contribute via the three new hooks this plan shipped.

**Plan 01-05 (HarnessOrchestrator consumption):** Ready. `HarnessOrchestrator.__init__` can now consult `get_registry().ordered_names()` to seed `PhaseState.phases`. The registry is populated but unconsumed today — 01-05 is where the orchestrator starts reading it.

**Phase 0 compatibility:** Held green. 12/12 regression matrix cases pass unchanged. No edits to `PhaseState`, `PhaseGate`, `HarnessOrchestrator`, `DEFAULT_PHASES`, or any template.

**Known forward-looking contract for Phase 4:** `ReviewRouter.match(diff_paths, state) -> list[str]` is locked. Rule-file format, SHA-pinning, multi-signal aggregation, and decorrelation rules are explicitly deferred to the Phase 4 RFC update. No plugin consumes routers yet (accepts T-01-03 — elevation-of-privilege surface does not materialize until Phase 4 wires consumption).

## Self-Check: PASSED

- File `clawteam/harness/phase_registry.py` exists.
- File `clawteam/harness/review_router.py` exists.
- File `clawteam/plugins/base.py` modified (three new methods added).
- File `clawteam/plugins/manager.py` modified (registry funneling added).
- File `tests/test_phase_registry.py` exists with 4 tests.
- File `tests/test_plugin_hooks.py` exists with 4 tests.
- Commit `8cdff8f` (RED) present in `git log`.
- Commit `6c07c5a` (GREEN) present in `git log`.

---

_Phase: 01-core-harness-extensions_
_Plan: 01_
_Completed: 2026-04-17_
