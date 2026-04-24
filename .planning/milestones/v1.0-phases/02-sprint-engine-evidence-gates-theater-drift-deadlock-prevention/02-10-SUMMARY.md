---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 10
subsystem: safety-rails
tags: [safety-rails, careful, freeze, guard, unfreeze, mcp-interception, phase-2, tdd]

# Dependency graph
requires:
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: "BeforeToolCall / BeforeFileWrite events (02-01), FreezeRegistry singleton (02-05), ArtifactStore write-path hook chain (02-06)"
provides:
  - "register_safety_subscribers(bus) opt-in handler registration (called from SprintConductor in Plan 02-11)"
  - "_on_before_file_write / _on_before_tool_call / _on_careful subscribers"
  - "CAREFUL_BLACKLIST regex + set_careful_veto_mode(bool) warn/veto toggle"
  - "MCP _tool wrapper emits BeforeToolCall and raises FrozenPathError on veto"
  - "translate_error explicit branches for 6 Phase 2 error classes"
  - "WorkspaceManager._emit_before_file_write helper on all 4 write paths"
  - "clawteam guard CLI sub-app: freeze / unfreeze / guard / unguard with --json envelope"
affects: [02-11-sprint-conductor, 02-07-evidence-gate, 03-gstack-team, 04-interactive-routing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Opt-in EventBus subscriber registration (Pitfall #8 BC hinge — Phase 0 templates never subscribe)"
    - "Shallow arg-scan for frozen paths at BeforeToolCall (primary defense remains at BeforeFileWrite layer)"
    - "Guarded try/except ImportError for future error-class branches (AmbiguousSprintError, SprintNotFoundError, MissingTeamError land later)"
    - "CLI emit_ok / emit_err helpers enforce D-26 envelope shape"

key-files:
  created:
    - tests/test_safety_rails.py
    - tests/test_before_events.py
  modified:
    - clawteam/harness/freeze_registry.py
    - clawteam/mcp/server.py
    - clawteam/mcp/helpers.py
    - clawteam/workspace/manager.py
    - clawteam/cli/commands.py

key-decisions:
  - "/careful is warn-only by default; veto mode flipped by `clawteam guard guard` (SAFETY-03) via module-level _careful_veto_mode flag"
  - "Subscriber registration stays OPT-IN via register_safety_subscribers(bus) — SprintConductor.__init__ calls it; Phase 0 templates never do (Pitfall #8 BC invariant)"
  - "Shallow arg-scan at BeforeToolCall per T-02-09 disposition — structural defense is BeforeFileWrite at the filesystem layer"
  - "careful_enabled persistence on SprintState deferred to Plan 02-11 (load_sprint_state / save_sprint_state helpers) — guard CLI attempts best-effort persistence via try/except ImportError, falls back to in-memory flag only"
  - "translate_error adds 6 explicit isinstance branches for Phase 2 error classes (message clarity + future error-code dispatch); guarded imports prevent breakage before all 6 classes land"
  - "MCP tool registry cleanup fixture added to test_before_events.py to prevent cross-file test contamination with test_mcp_server.py's exact-set assertion"

patterns-established:
  - "Pattern: register_safety_subscribers(bus) — idempotent id(bus) tracker + explicit priority ordering (freeze check priority=10, /careful priority=20)"
  - "Pattern: Before* event emit then veto check at caller site (subscribers only SET veto, caller raises the structured error)"
  - "Pattern: _guard_emit_ok / _guard_emit_err mirrors the Plan 02-12 sprint CLI envelope helpers in advance"

requirements-completed: [SAFETY-01, SAFETY-02, SAFETY-03, SAFETY-04]

# Metrics
duration: ~50 min
completed: 2026-04-20
---

# Phase 02 Plan 10: Sprint Safety Rails (/careful, /freeze, /guard, /unfreeze) Summary

**EventBus-wired safety rails — FreezeRegistry subscribers veto BeforeFileWrite + BeforeToolCall on frozen paths; /careful regex blacklist warns (or vetoes under composite /guard); MCP _tool + WorkspaceManager + clawteam guard CLI fully intercepted with opt-in Pitfall #8 BC hinge.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-04-20T09:53:49Z (plan execution kickoff)
- **Completed:** 2026-04-20T10:43:52Z
- **Tasks:** 4 (Task 1 + Task 2a + Task 2b + Task 3)
- **Files modified:** 7 (5 clawteam/*.py, 2 tests/*.py)

## Accomplishments

- 3 EventBus subscribers (`_on_before_file_write`, `_on_before_tool_call`, `_on_careful`) land in `clawteam/harness/freeze_registry.py` with opt-in `register_safety_subscribers(bus)` registration; idempotent via `id(bus)` tracker.
- `CAREFUL_BLACKLIST` regex matches all 5 destructive shell patterns documented in D-13 (rm -rf, git reset --hard, git push --force, DROP TABLE, DELETE FROM ... WHERE); warn-only default + veto-mode toggle via `set_careful_veto_mode(bool)`.
- MCP `_tool` wrapper at `clawteam/mcp/server.py` emits `BeforeToolCall` via `AgentIdentity.from_env()` before every intercepted tool; raises `FrozenPathError` on veto and skips the wrapped function.
- `translate_error` at `clawteam/mcp/helpers.py` gains 6 explicit isinstance branches for Phase 2 error classes (3 shipped now + 3 guarded for Plans 02-07/02-11/02-12).
- `WorkspaceManager._emit_before_file_write` helper added and wired into all 4 git-write methods (`create_workspace`, `checkpoint`, `merge_workspace`, `cleanup_workspace`); on veto raises `FrozenPathError` before any filesystem op.
- `clawteam guard` sub-app lands with 4 commands (`freeze`, `unfreeze`, `guard`, `unguard`); each writes to `FreezeRegistry` and emits the D-26 `{ok, data, warnings, error}` JSON envelope; `guard guard` is the SAFETY-03 composite (freeze + enable /careful veto).
- 15 tests in `tests/test_safety_rails.py` + 6 tests in `tests/test_before_events.py` = **21 new tests** all pass.
- Phase 0 regression matrix stays green (12/12) because `SprintConductor` — the only caller of `register_safety_subscribers` — is not yet instantiated by existing templates.

## Task Commits

TDD gate sequence (RED → GREEN per task):

1. **Task 1 RED: safety rails + guard CLI failing tests** — `0f9576a` (test)
2. **Task 1 GREEN: safety-rail subscribers + /careful regex** — `9984adc` (feat)
3. **Task 2 RED: MCP BeforeToolCall + WorkspaceManager BeforeFileWrite failing tests** — `45f822e` (test)
4. **Task 2a GREEN: MCP _tool emit + translate_error 6 branches** — `ee3b165` (feat)
5. **Task 2b GREEN: WorkspaceManager emits BeforeFileWrite on 4 write paths** — `dcd195a` (feat)
6. **Task 3 GREEN: clawteam guard sub-app + ruff cleanup** — `8610260` (feat)

**Plan metadata:** Committed via final `docs(02-10): complete safety rails plan` below.

## Files Created/Modified

### Created

- `tests/test_safety_rails.py` — 15 tests (9 subscriber + 6 guard CLI) covering CAREFUL_BLACKLIST pattern matches, idempotent registration, Pitfall #5 data-dir exemption, and full CLI round-trip via `typer.testing.CliRunner`.
- `tests/test_before_events.py` — 6 tests covering MCP `_tool` emit + veto, `translate_error` routing, and WorkspaceManager `_emit_before_file_write` behavior; includes `cleanup_mcp_tools` fixture to prevent test contamination.

### Modified

- `clawteam/harness/freeze_registry.py` — +180 LOC: `CAREFUL_BLACKLIST` regex, 3 subscribers, `set_careful_veto_mode`, `register_safety_subscribers`, `reset_safety_subscribers`.
- `clawteam/mcp/server.py` — `_tool` wrapper gains BeforeToolCall emit + veto check; preserves existing `translate_error` path.
- `clawteam/mcp/helpers.py` — `translate_error` extended with 6 explicit branches + guarded imports for 3 not-yet-landed error classes.
- `clawteam/workspace/manager.py` — `_emit_before_file_write` helper + emit calls at the entry point of all 4 write-path methods (`create_workspace`, `checkpoint`, `merge_workspace`, `cleanup_workspace`).
- `clawteam/cli/commands.py` — `guard_app` Typer sub-app (+4 commands) + `_guard_emit_ok` / `_guard_emit_err` helpers + `_render_guard_human` for TTY output.

## Decisions Made

- **/careful warn-only default (D-13):** Matches gstack-native semantics — the blacklist is a friction hint, not a sandbox. Veto mode is opt-in via `clawteam guard guard` (SAFETY-03) or SprintState.careful_enabled (Plan 02-11).
- **Shallow arg-scan (T-02-09):** `_on_before_tool_call` scans `event.args.values()` one level deep. Deep recursion into nested structures is documented as out of scope; the primary defense is structural (BeforeFileWrite at the filesystem layer).
- **Opt-in subscriber registration (Pitfall #8):** `register_safety_subscribers(bus)` uses an `id(bus)` set tracker for idempotency; SprintConductor is the sole caller in Plan 02-11. Phase 0 templates keep their unsubscribed EventBus, so their BeforeToolCall/BeforeFileWrite emits reach zero handlers.
- **Best-effort SprintState persistence for careful_enabled:** The guard/unguard commands try `load_sprint_state`/`save_sprint_state` inside `try/except` blocks — those helpers land in Plan 02-11. Until then, the in-memory `_careful_veto_mode` flag is the sole source of truth.
- **`typer.Exit` re-raise in guard commands:** Without `except typer.Exit: raise` ahead of the generic `Exception` catch, the CLI's own exit mechanism would be swallowed by our error envelope path.
- **`cleanup_mcp_tools` fixture in tests:** Without it, Task 2a's dummy tool registrations leaked onto the FastMCP singleton and broke `test_mcp_server.py::test_server_registers_core_tools`'s exact-set assertion. Fixture snapshots the tool-registry keys on entry and removes any net-new tools on teardown.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test fixture collision with conftest.py autouse `isolated_data_dir`**

- **Found during:** Task 3 (first CLI test run)
- **Issue:** My `guard_env` fixture created `tmp_path/.clawteam`, but the autouse `isolated_data_dir` fixture in `tests/conftest.py` already creates that directory — `FileExistsError` blocked all 6 CLI tests.
- **Fix:** Changed `guard_env` to use `tmp_path/data` + `mkdir(exist_ok=True)` so it does not collide with any autouse fixture.
- **Files modified:** `tests/test_safety_rails.py`
- **Verification:** All 6 CLI tests passed after the change.
- **Committed in:** `8610260` (Task 3 commit; fix was applied before the test-green commit).

**2. [Rule 1 - Bug] Test cross-contamination: dummy MCP tool registrations leaking to test_mcp_server.py**

- **Found during:** Running the full regression after Task 3
- **Issue:** Task 2a's tests (`test_mcp_tool_emits_before_tool_call`, `test_mcp_tool_vetoed_call_raises_frozen_path_error`) wrap dummy functions via `server_mod._tool(...)`. The wrapping path calls `mcp.tool()(wrapped)` which registers on the shared FastMCP singleton. This made `test_mcp_server.py::test_server_registers_core_tools` (asserting the exact set of registered tools) fail when run together.
- **Fix:** Added a `cleanup_mcp_tools` pytest fixture that snapshots the registry on entry and calls `mcp._tool_manager.remove_tool(name)` for any net-new tools on teardown. Attached it to both Task 2a tests.
- **Files modified:** `tests/test_before_events.py`
- **Verification:** Full test suite (127 core + 724 full) now green with zero regression.
- **Committed in:** `8610260`.

**3. [Rule 2 - Missing Critical] `typer.Exit` not re-raised in guard command handlers**

- **Found during:** Task 3 implementation
- **Issue:** The generic `except Exception` in each guard command would have swallowed `typer.Exit` — which is what `_guard_emit_err` raises to terminate with exit code 1 after emitting the error envelope. Without re-raising `typer.Exit` first, the CLI would print TWO error envelopes (the one from `_guard_emit_err` and the one from the outer handler) and exit with the wrong code.
- **Fix:** Added `except typer.Exit: raise` ahead of the generic `except Exception: _guard_emit_err(...)` clause in all 4 guard commands.
- **Files modified:** `clawteam/cli/commands.py`
- **Verification:** CLI tests assert `result.exit_code == 0` on success and `!= 0` on missing --team; both pass.
- **Committed in:** `8610260`.

**4. [Rule 3 - Blocking] Ruff lint errors on guarded error-class imports (N806 false positives)**

- **Found during:** Plan verification step (`ruff check ...`)
- **Issue:** Ruff flagged 6 `N806` errors ("variable should be lowercase") on the fallback assignments `FrozenPathError = None`, etc. These are class-name aliases set when the class has not yet been imported; the lowercase rule does not apply.
- **Fix:** Added explanatory comment + `# noqa: N806` on each fallback line.
- **Files modified:** `clawteam/mcp/helpers.py`
- **Verification:** `ruff check` now reports "All checks passed!"
- **Committed in:** `8610260`.

---

**Total deviations:** 4 auto-fixed (1 Rule 1 bug, 1 Rule 2 missing-critical, 2 Rule 3 blocking).
**Impact on plan:** Every fix was necessary for correctness or for the plan's own verification step to pass. Zero scope creep; plan executed within the stated file list. No Rule 4 (architectural) escalations were triggered.

## Issues Encountered

- **SprintState.careful_enabled field** is referenced by the plan's Task 3 but is not yet defined (Plan 02-11 will add it along with `load_sprint_state` / `save_sprint_state` helpers). As the plan's NOTE explicitly permits, the guard CLI attempts best-effort persistence inside a `try/except` and falls back to the in-memory flag. No xfail marker was needed because the test asserts on the module-level `_careful_veto_mode` flag (authoritative until 02-11 lands).

## TDD Gate Compliance

Per-task RED/GREEN pairs confirmed in git log:

| Task | RED commit | GREEN commit | Status |
|------|-----------|--------------|--------|
| 1    | 0f9576a   | 9984adc      | Pass   |
| 2a   | 45f822e   | ee3b165      | Pass   |
| 2b   | (shared with Task 2a RED) | dcd195a | Pass |
| 3    | (shared with Task 1 RED — CLI tests landed in the same file) | 8610260 | Pass |

No REFACTOR commits were required; the GREEN implementations were already minimal.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **Plan 02-11 (SprintConductor)** can now call `register_safety_subscribers(bus)` from `SprintConductor.__init__` to activate the safety rails for gstack sprints. The guard CLI's `try/except` for `load_sprint_state` / `save_sprint_state` will seamlessly start persisting `careful_enabled` once 02-11's helpers land.
- **Plan 02-07 (EvidenceGate)** and **Plan 02-12 (sprint CLI)** will benefit from the `translate_error` branches — `AmbiguousSprintError` / `SprintNotFoundError` / `MissingTeamError` route automatically once those classes are defined.
- **Phase 3 (gstack team)** picks up these primitives: the `/freeze` / `/unfreeze` / `/guard` / `/unguard` slash-command surface becomes a real team-level primitive once the 11 agents have CLI access.

## Self-Check: PASSED

- [x] `.planning/phases/02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention/02-10-SUMMARY.md` exists (this file).
- [x] All task commits present in git log:
  - [x] 0f9576a `test(02-10): add failing tests for safety rails subscribers + guard CLI`
  - [x] 9984adc `feat(02-10): safety-rail subscribers + /careful regex blacklist`
  - [x] 45f822e `test(02-10): add failing tests for MCP BeforeToolCall + WorkspaceManager BeforeFileWrite`
  - [x] ee3b165 `feat(02-10): MCP _tool emits BeforeToolCall + translate_error routes 6 Phase 2 error types`
  - [x] dcd195a `feat(02-10): WorkspaceManager emits BeforeFileWrite before 4 git-path write sites`
  - [x] 8610260 `feat(02-10): clawteam guard sub-app (freeze/unfreeze/guard/unguard) + ruff cleanup`
- [x] All plan `<acceptance_criteria>` checks pass:
  - [x] `pytest tests/test_safety_rails.py -q` → 15 passed
  - [x] `pytest tests/test_before_events.py -q` → 6 passed
  - [x] `pytest tests/test_template_regression_matrix.py -q` → 12 passed (Phase 0 BC preserved)
  - [x] `grep -c CAREFUL_BLACKLIST clawteam/harness/freeze_registry.py` → 2 (≥ 1)
  - [x] `grep -c "def register_safety_subscribers" clawteam/harness/freeze_registry.py` → 1
  - [x] `grep -c "def _on_before_file_write|def _on_before_tool_call|def _on_careful" clawteam/harness/freeze_registry.py` → 3
  - [x] `grep -c set_careful_veto_mode clawteam/harness/freeze_registry.py` → 1 (≥ 1)
  - [x] `grep -c BeforeToolCall clawteam/mcp/server.py` → 3 (≥ 1)
  - [x] 6 Phase 2 error classes referenced in `clawteam/mcp/helpers.py` → 18 hits (≥ 6)
  - [x] `grep -c "guard_app = typer.Typer" clawteam/cli/commands.py` → 1
  - [x] `grep -c "@guard_app.command" clawteam/cli/commands.py` → 4
  - [x] `grep -c "_emit_before_file_write|BeforeFileWrite" clawteam/workspace/manager.py` → 12 (≥ 5)
  - [x] `python -c "from clawteam.harness.freeze_registry import CAREFUL_BLACKLIST..."` → prints `ok`
- [x] `ruff check` on all 7 modified/created files → "All checks passed!"
- [x] Full regression (excluding the 2 new files): `724 passed, 1 skipped`

---
*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Completed: 2026-04-20*
