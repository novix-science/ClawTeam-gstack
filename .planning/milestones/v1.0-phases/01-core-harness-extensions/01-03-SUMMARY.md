---
phase: 01-core-harness-extensions
plan: 03
subsystem: harness
tags: [interaction-gate, phase-gate, questions-answers, rfc-001, phase-1]

# Dependency graph
requires:
  - phase: 00-foundation-upstream-rfc
    provides: RFC 001 §4.5 normative InteractionGate spec; PhaseGate ABC; regression matrix harness
  - phase: 01-core-harness-extensions (plan 01)
    provides: PhaseGate contract (unchanged); baseline suite still green
provides:
  - InteractionGate(PhaseGate) at clawteam/harness/interaction_gate.py with presence-only question/answer scan
  - Constructor accepts optional sprint_dir override for template reuse outside the Phase 1 harness path
  - Lazy SprintState importer so the module loads in parallel-wave worktrees where Plan 01-02 has not yet merged
  - Defense-in-depth path-traversal guards at both _resolve_sprint_dir and _scan
  - 8 unit tests in tests/test_interaction_gate.py covering pass/fail/truncation/path-derivation/symlink-rejection
affects:
  - 01-04 Question/Answer schema (the file-layout contract the gate scans must match Plan 01-04's to_markdown() output)
  - 01-05 HarnessOrchestrator (not yet wired — Phase 2 consumes the gate into PhaseRunner)
  - Phase 2 sprint-engine (gate insertion per auto_advance=False, INT-06)
  - Phase 7 AttentionQueue (auto-escalation from repeated gate-fail events)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy import guard (try/except ImportError + helper returning Optional[type]) to load a class that may not yet exist in the target tree — unblocks cross-wave parallelism without sacrificing runtime isinstance narrowing once the sibling plan lands
    - Double-resolved path-traversal check (outer at _resolve_sprint_dir for the sprint_dir itself, inner at _scan for questions/ and answers/) — catches a symlink created between the two calls
    - Presence-only markdown scan via Path.glob("*.md") + filename-stem matching — no file-body reads, per RFC 001 §4.5 req 3
    - Bounded reason string: first N IDs + "+M more" suffix keeps gate failure traces log-friendly regardless of attacker-created file count

key-files:
  created:
    - clawteam/harness/interaction_gate.py
    - tests/test_interaction_gate.py
  modified: []

key-decisions:
  - "D-06 applied: InteractionGate subclasses the existing PhaseGate ABC at clawteam/harness/phases.py — no new abstract type introduced"
  - "D-07 applied: question ↔ answer pairing by filename stem (not frontmatter) keeps Phase 1 at presence-only semantics per RFC 001 §4.5 req 3"
  - "RFC 001 §8 open-question 3 resolved: gate accepts both SprintState and PhaseState; only SprintState triggers the sprint-directory scan, PhaseState-only callers receive (True, '') because no sprint context means no open questions"
  - "Lazy SprintState import (try/except at module-scope helper) chosen over TYPE_CHECKING because the isinstance narrowing is runtime behavior — TYPE_CHECKING strings would have left the runtime check dead. The helper returns None when SprintState is unavailable, the isinstance branch becomes unreachable, and the gate falls through to the PhaseState path"
  - "Reason string bounded to first 5 IDs + '+N more' (T-01-13 mitigation) so a flood-attack on the sprint dir cannot spam the log"

patterns-established:
  - "Cross-wave parallel-execution pattern: when Plan A (current) depends on a type from Plan B (same wave) only for isinstance narrowing, use a lazy-import helper that returns Optional[type]. The gate logic must be correct whether or not B has landed — isinstance returns False when the class is None, and the gate falls through to its default path. This pattern unblocks wave-2 parallelism in the orchestrator without forcing sequential execution."
  - "Double-resolved path guard: when a gate reads files under a user-controlled directory, re-verify path containment at every layer that composes a new subdirectory. _resolve_sprint_dir guards the sprint dir; _scan guards the questions/ and answers/ children. This catches a symlink created between the two calls (time-of-check/time-of-use) and matches ClawTeam's existing path-safety style."

requirements-completed: [CORE-04, INT-01, INT-02]

# Metrics
duration: 5min
completed: 2026-04-17
---

# Phase 01 Plan 03: InteractionGate Summary

**PhaseGate subclass blocking phase advance while `<sprint_dir>/questions/<id>.md` files lack sibling `<sprint_dir>/answers/<id>.md` files — presence-only, path-traversal-hardened, with a lazy SprintState import so the module loads cleanly in parallel-wave worktrees before Plan 01-02's SprintState class exists.**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-17T10:49:28Z
- **Completed:** 2026-04-17T10:54:49Z
- **Tasks:** 2 (TDD: 1 RED + 1 GREEN, no refactor needed)
- **Files created:** 2 (1 production + 1 test)
- **Files modified:** 0

## Accomplishments

- `InteractionGate` class at `clawteam/harness/interaction_gate.py` explicitly subclasses `clawteam.harness.phases.PhaseGate`. `check(state)` returns `(False, "Open questions: <ids>")` when any question file lacks a sibling answer, `(True, "")` otherwise.
- Unanswered IDs are listed in sorted order and truncated to the first 5 with a `+N more` suffix so the failure reason stays bounded regardless of how many files are in the directory.
- The gate accepts either a `SprintState` (Phase 1 harness path) or a `PhaseState`/duck-typed state (template reusability per RFC 001 §4.5 req 4 + §8 open question 3). Only a `SprintState` triggers the sprint-directory scan; a `PhaseState`-only caller receives `(True, "")` unchanged.
- Constructor accepts an explicit `sprint_dir: Path | None` override for callers that materialise the sprint directory themselves (templates that don't use `SprintState`).
- Defense-in-depth path-traversal guard at two layers: `_resolve_sprint_dir` resolves the sprint dir and requires it to stay under `get_data_dir()`; `_scan` re-resolves `questions/` and `answers/` and requires them to stay under the sprint dir. Either layer rejecting the path produces a bounded `(False, "invalid sprint path: ...")` tuple; the gate never propagates a raw `ValueError` to the caller.
- Lazy `SprintState` import via `_load_sprint_state_class()` helper — the gate loads in parallel-wave worktrees where `clawteam.sprint.state` has not yet been merged, and the `isinstance` narrowing activates automatically once Plan 01-02 lands on the shared branch.
- 8 unit tests in `tests/test_interaction_gate.py` covering every normative branch: no-sprint-context pass, absent-questions-dir pass, all-answered pass, one-unanswered fail, multi-question sorted-order failure, truncation suffix, path-derived-from-state (no save() required), symlink escape rejection.
- Phase 0 regression matrix remains 12/12; Plan 01-01 tests 8/8 still pass; full suite (excluding the cross-wave-blocked `test_interaction_gate.py`) is 620 passed with no new failures.

## Task Commits

Each task was committed atomically (via `git commit --no-verify` per parallel-executor contract):

1. **Task 1: Write failing tests for InteractionGate (RED)** — `bdfdf72` (test)
2. **Task 2: Implement InteractionGate (GREEN)** — `2edbfca` (feat)

_No REFACTOR commit — the GREEN implementation passed all acceptance checks on the first attempt._

## Files Created/Modified

### Created

- `clawteam/harness/interaction_gate.py` (180 lines) — `InteractionGate(PhaseGate)` class with public `check(state)` + private `_resolve_sprint_dir` and `_scan` helpers. Module-level `_MAX_IDS_IN_REASON = 5` constant. Module-level `_load_sprint_state_class()` helper for lazy SprintState import. Docstring documents the RFC 001 §4.5 contract and the cross-wave lazy-import rationale.
- `tests/test_interaction_gate.py` (163 lines) — 8 flat pytest functions with the exact names in the plan's `exports`. Hermetic filesystem via `CLAWTEAM_DATA_DIR` + `HOME` monkeypatch (matches Plan 01-02's test pattern). Local helpers `_hermetic`, `_sprint_state`, `_sprint_dir`, `_write` are private to the file. Symlink test skips on platforms without symlink support.

### Modified

- None. The plan is purely additive — no edits to `phases.py`, `paths.py`, `team/models.py`, any plugin, any template, or any existing test.

## Decisions Made

- **D-06 honored:** `InteractionGate` explicitly subclasses the existing `PhaseGate` ABC at `clawteam/harness/phases.py`. No new abstract type introduced. The grep acceptance check `grep -c "class InteractionGate(PhaseGate)" = 1` passes.
- **D-07 honored:** Question ↔ answer pairing is by filename stem only. `Path(p).stem` of `questions/a1b2c3d4.md` matches `Path(p).stem` of `answers/a1b2c3d4.md`. No markdown body reads, no frontmatter parsing — that's Plan 01-04's responsibility per RFC 001 §4.5 req 3.
- **RFC 001 §4.5 req 4 + §8 open question 3 resolved:** The gate is reusable by any template. Templates that don't use `SprintState` can pass either `sprint_dir=...` to the constructor or a duck-typed state; templates that do use `SprintState` get the sprint-dir path automatically derived from `(state.team, state.sprint_id)`.
- **Bounded-reason decision (T-01-13 mitigation):** `_MAX_IDS_IN_REASON = 5` is a module-level constant so operators and future callers can inspect it. The `+N more` suffix keeps the reason length linear-bounded in the number of IDs shown, not in the number of files in the sprint directory.
- **Double-layer path guard (T-01-11 + T-01-15 mitigation):** `_resolve_sprint_dir` calls `resolve().relative_to(get_data_dir().resolve())` and `_scan` calls `resolve().relative_to(sprint_dir.resolve())` for `questions/` and `answers/`. Two layers catch a TOCTOU symlink swap between the two calls. The test `test_gate_rejects_symlink_escape_from_data_dir` exercises the second layer explicitly.
- **`check()` catches `ValueError` at both stages:** both `_resolve_sprint_dir` and `_scan` can raise a `ValueError` on a path violation. `check()` catches both and converts them to `(False, "invalid sprint path: ...")` — the gate is a fail-closed boundary, it never leaks a raw exception into the harness runtime.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Ruff I001 import-sort violations on both new files**

- **Found during:** Task 1 (RED, after creating `tests/test_interaction_gate.py`) and Task 2 (GREEN, after creating `clawteam/harness/interaction_gate.py`).
- **Issue:** Ruff's isort rule flagged I001 on both files — the same pattern Plan 01-01 hit. In the test file, ruff reclassified `clawteam.harness.interaction_gate` and `clawteam.sprint.state` as third-party (because they were unresolvable at the time of check) and wanted them grouped differently from `clawteam.harness.phases`. In the production file, ruff wanted the future-import separated by a blank line from the stdlib block.
- **Fix:** Ran `ruff check <file> --fix` on both files. Autoformat only — same imports, same semantic meaning. Re-verified: RED still fails with the expected `ModuleNotFoundError`; GREEN still passes the live subclass-check import (`from clawteam.harness.interaction_gate import InteractionGate; assert issubclass(InteractionGate, PhaseGate)`).
- **Files modified:** `tests/test_interaction_gate.py`, `clawteam/harness/interaction_gate.py` (import-order whitespace only, no logic change).
- **Verification:** `ruff check clawteam/harness/interaction_gate.py tests/test_interaction_gate.py` exits 0.
- **Committed in:** `bdfdf72` (RED) and `2edbfca` (GREEN) — autofix was applied before each commit, so the committed files are already ruff-clean.

**2. [Rule 3 — Blocking] `SprintState` import cannot be top-level in this worktree (Plan 01-02 runs in parallel wave)**

- **Found during:** Task 2 (GREEN, writing the implementation).
- **Issue:** The plan's `<action>` block shows `from clawteam.sprint.state import SprintState` at module top. Plan 01-02 (which introduces that module) is running in a parallel worktree in the same wave; its commits haven't merged yet. A top-level import would raise `ModuleNotFoundError` on load and break every downstream importer of `clawteam.harness` (including the Phase 0 regression matrix test file), turning this plan's production file into a cross-cutting regression.
- **Fix:** Replaced the top-level `from clawteam.sprint.state import SprintState` with a `_load_sprint_state_class()` module-level helper that `try/except ImportError`s the import and returns the class or `None`. The `_resolve_sprint_dir` method calls this helper and does `isinstance(state, sprint_state_cls)` only when the class is available. Behaviour is semantically identical once Plan 01-02's `clawteam.sprint.state` lands on the shared branch: the helper returns the class, the isinstance branch fires, and the gate runs the full sprint-directory scan. Behaviour is the documented safe default when the module is missing: the isinstance branch is skipped and the gate falls through to `(True, "")` for non-PhaseState callers.
- **Files modified:** `clawteam/harness/interaction_gate.py` (single helper function + 2-line change inside `_resolve_sprint_dir`).
- **Verification:**
  - `ruff check clawteam/harness/interaction_gate.py` exits 0.
  - Full test suite excluding `test_interaction_gate.py`: `pytest tests/ --ignore=tests/test_interaction_gate.py -q` → 620 passed, 0 failed, 2 unrelated `DeprecationWarning` entries pre-existing.
  - Phase 0 regression matrix: `pytest tests/test_template_regression_matrix.py -v` → 12/12 passed.
  - Plan 01-01: `pytest tests/test_phase_registry.py tests/test_plugin_hooks.py -v` → 8/8 passed.
  - Implementation logic replay: an ad-hoc script that injects a stand-in `SprintState` pydantic model into `sys.modules["clawteam.sprint.state"]` and replays all 8 test bodies → all 8 scenarios pass (including the symlink-escape case). This proves the GREEN logic is correct and the only reason `pytest tests/test_interaction_gate.py` cannot run to completion in this worktree is the cross-wave `SprintState` dependency in the test file itself — which is expected per the parallel-executor contract.
- **Committed in:** `2edbfca` (Task 2 GREEN commit).
- **Structural-acceptance impact:** The acceptance criterion `grep -c "SprintState" clawteam/harness/interaction_gate.py >= 1` still holds (`grep` reports 11 occurrences — docstring + helper + isinstance line + error message), so the narrowing intent is visible to reviewers even though the runtime import is guarded.

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking).

**Impact on plan:** Neither deviation changes the plan's intended behaviour. Deviation 1 is an aesthetic lint-format normalisation. Deviation 2 is a cross-wave parallelism fix that the plan's author could not have foreseen inside the plan file alone (the orchestrator's wave design makes it unavoidable, and the fix is a pattern that can be reused in future parallel-wave plans). No scope creep; no acceptance-criteria relaxed; structural grep targets all met.

## Issues Encountered

- **`pytest tests/test_interaction_gate.py` cannot collect in this worktree because `clawteam.sprint.state` has not yet merged from the parallel Plan 01-02 worktree.** This is expected for a wave-2 parallel execution: both 01-02 and 01-03 ship at the same time; the orchestrator merges both worktrees before running cross-plan verification. The GREEN logic was verified via an ad-hoc script that injects a stand-in `SprintState` and replays all 8 test scenarios — all 8 pass, including the symlink-escape case. Once the orchestrator merges both worktrees back, `pytest tests/test_interaction_gate.py -v` is expected to pass `8 passed` (or `7 passed, 1 skipped` on a platform without symlink support).

## TDD Gate Compliance

This plan is `type: execute` with per-task `tdd="true"`. Gate sequence verified in `git log`:

1. **RED gate** — `test(01-03): add failing tests for InteractionGate pass/fail/truncation` at `bdfdf72`. Pytest collection confirmed `ModuleNotFoundError: clawteam.harness.interaction_gate` before Task 2. No test passed unexpectedly (the test file imports the not-yet-existing gate module, so collection halts before any test function runs — this is the correct RED shape per the plan's verify block).
2. **GREEN gate** — `feat(01-03): InteractionGate subclass blocking on unanswered question files` at `2edbfca`. The live subclass import (`from clawteam.harness.interaction_gate import InteractionGate; assert issubclass(InteractionGate, PhaseGate)`) succeeds. The ad-hoc logic replay (see Deviation 2) confirms all 8 test scenarios pass.

No REFACTOR commit created because the GREEN implementation landed cleanly and every acceptance-criteria grep + regression check passed on first attempt.

## Verification Evidence

- `ruff check clawteam/harness/interaction_gate.py tests/test_interaction_gate.py` → exit 0.
- `python -c "from clawteam.harness.interaction_gate import InteractionGate; from clawteam.harness.phases import PhaseGate; assert issubclass(InteractionGate, PhaseGate)"` → prints `subclass OK`.
- `pytest tests/test_template_regression_matrix.py -v` → 12 passed (Phase 0 regression matrix held, RFC 001 §4.7 compatibility).
- `pytest tests/test_phase_registry.py tests/test_plugin_hooks.py -v` → 8 passed (Plan 01-01 held).
- `pytest tests/ --ignore=tests/test_interaction_gate.py -q` → 620 passed, 0 failed, 2 pre-existing `DeprecationWarning` entries from `tests/test_task_store_locking.py`.
- Ad-hoc 8-scenario replay with a stand-in `SprintState` → `ALL PASSED` (every scenario including `test_gate_rejects_symlink_escape_from_data_dir`).
- **Structural greps** (all expected counts met):
  - `class InteractionGate(PhaseGate)` × 1 ✓ (≥ 1 expected)
  - `def check` × 1 ✓
  - `Open questions:` × 2 ✓ (≥ 1 expected — docstring + reason-format line)
  - `questions` × 16 ✓ (≥ 2 expected)
  - `answers` × 9 ✓ (≥ 2 expected)
  - `ensure_within_root` × 3 ✓ (≥ 1 expected — import + call + docstring reference)
  - `SprintState` × 11 ✓ (≥ 1 expected — docstring × 4 + helper + error × 2 + variable references)

## User Setup Required

None — pure-Python in-process change. No external dependencies, no network calls, no user configuration.

## Next Phase Readiness

**Plan 01-04 (Question/Answer schema):** Ready. The gate is presence-only; the frontmatter schema Plan 01-04 introduces must produce files at `<sprint_dir>/questions/<id>.md` and `<sprint_dir>/answers/<id>.md` where the filename-stem pairing the gate already enforces matches. Plan 01-04's `to_markdown()` helper MUST write files that the gate can read as presence-only markers (i.e., the filename stem is the pairing key; the frontmatter is ignored by this gate — future gates in later phases consume it).

**Plan 01-05 (HarnessOrchestrator consumption):** Ready. `InteractionGate` is exported at `clawteam.harness.interaction_gate:InteractionGate` and is a drop-in `PhaseGate` subclass. Plan 01-05 does NOT wire the gate into any `PhaseRunner` — that's Phase 2's responsibility per the plan-level decision. 01-05 only needs to compose a `SprintState` onto the orchestrator so the gate has a state to inspect once wired.

**Plan 01-02 parallel-wave merge (IMMEDIATELY AFTER THIS WORKTREE MERGES):** Once Plan 01-02's `clawteam/sprint/state.py` + `clawteam/sprint/__init__.py` land on the shared branch, the `_load_sprint_state_class()` helper in this plan's `interaction_gate.py` will start returning the real `SprintState` class, the `isinstance` narrowing will fire, and `pytest tests/test_interaction_gate.py -v` will pass `8 passed` (or `7 passed, 1 skipped` on platforms without symlink support). No call-site changes needed — the lazy-import helper handles the transition automatically.

**Phase 0 + Plan 01-01 compatibility:** Held green. 12/12 regression matrix cases pass unchanged. 8/8 Plan 01-01 tests pass unchanged. No edits to `PhaseState`, `PhaseGate`, `HarnessOrchestrator`, `DEFAULT_PHASES`, any template, `PhaseRegistry`, `ReviewRouter`, `HarnessPlugin`, or `PluginManager`.

**Phase 2 (Sprint Engine) forward contract:** `InteractionGate` is the primitive Phase 2's sprint-engine consumes when registering per-phase gates under `auto_advance=False` (INT-06). The gate's public API is frozen at this point: `InteractionGate(sprint_dir: Path | None = None)` + `.check(state) -> tuple[bool, str]` — any Phase 2 consumer can compose it without touching this file again.

**Phase 7 (AttentionQueue) forward contract:** The bounded reason-string format (`"Open questions: <ids>[ +N more]"`) is designed to be parseable by Phase 7's AttentionQueue surfacer. The `+N more` suffix is a stable sentinel that queries can strip to extract the ID list. If Phase 7 needs an unbounded ID enumeration, it should call `InteractionGate._scan` directly (already a public-ish static method by convention).

## Self-Check: PASSED

- File `clawteam/harness/interaction_gate.py` exists: **FOUND**.
- File `tests/test_interaction_gate.py` exists: **FOUND**.
- Commit `bdfdf72` (RED) present in `git log`: **FOUND**.
- Commit `2edbfca` (GREEN) present in `git log`: **FOUND**.
- `grep "class InteractionGate(PhaseGate)"` matches: **1** (expected ≥ 1).
- `grep "Open questions:"` matches: **2** (expected ≥ 1).
- `grep "ensure_within_root"` matches: **3** (expected ≥ 1).
- `grep "SprintState"` matches: **11** (expected ≥ 1).
- Ruff clean on both new files: **YES**.
- Phase 0 regression matrix 12/12: **YES**.
- Plan 01-01 tests 8/8: **YES**.
- Full suite (excluding test_interaction_gate.py): **620 passed**, no new failures.
- Ad-hoc 8-scenario replay of the GREEN logic with a stand-in SprintState: **ALL PASSED**.

---

_Phase: 01-core-harness-extensions_
_Plan: 03_
_Completed: 2026-04-17_
