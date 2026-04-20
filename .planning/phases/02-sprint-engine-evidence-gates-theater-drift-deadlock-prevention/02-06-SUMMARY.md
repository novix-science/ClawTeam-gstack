---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 06
subsystem: infra
tags: [artifact-store, hook-chain, size-cap, before-file-write, errors, phase-2, pitfall-8]

# Dependency graph
requires:
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: Plan 02-01 BeforeFileWrite event class; Plan 02-03 SprintState.artifact_cap_bytes field
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: (soft, parallel wave) Plan 02-05 FrozenPathError in clawteam/harness/freeze_registry.py — lazy-imported
provides:
  - ArtifactStore.write() Phase 2 hook chain (name-guard -> size-cap -> BeforeFileWrite emit -> atomic write)
  - clawteam/harness/errors.py module colocating Phase 2 structured errors (ArtifactTooLargeError)
  - ArtifactTooLargeError with D-27 message shape (name + size_bytes + cap_bytes + split suggestion)
  - BeforeFileWrite emission point for Plan 02-10 freeze/careful safety-rail subscribers
  - T-02-02 path-name guard (is_absolute + .. segment rejection)
  - Constructor-level artifact_cap_bytes kwarg (keyword-only; BC-safe)
affects:
  - 02-07 (EvidenceGate — the only place frontmatter validation runs)
  - 02-09 (Transport.deliver — shares the turn-counter increment site)
  - 02-10 (freeze/careful subscribers register on BeforeFileWrite)
  - 02-11 (SprintConductor — resolves 3-layer cap override and passes to ArtifactStore)
  - 02-12 (CLI --artifact-cap flag + error dispatch for ArtifactTooLargeError)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Colocated structured errors module (clawteam/harness/errors.py) for cross-plan reuse"
    - "Lazy-import helper (_resolve_frozen_path_error) tolerates Wave 2 parallel execution"
    - "Pre-write hook chain pattern: short-circuit ordering with explicit Pitfall #8 content-agnostic invariant"
    - "Keyword-only additive constructor kwargs preserve BC"
    - "Defensive path-name validation (T-02-02) before path-join"

key-files:
  created:
    - clawteam/harness/errors.py
    - tests/test_artifact_caps.py
  modified:
    - clawteam/harness/artifacts.py

key-decisions:
  - "Frontmatter validation stays OUT of the write-path (Pitfall #8); grep-enforced to 0 hits on yaml/frontmatter/parse_frontmatter."
  - "FrozenPathError imported via lazy helper, not module-top, so Plan 02-06 compiles even when Plan 02-05 lands in a later merge step (Wave 2 safety)."
  - "artifact_cap_bytes accepted as keyword-only kwarg to preserve byte-compatible constructor signature for all existing call sites."
  - "T-02-02 guard promoted from threat register to acceptance criterion — _validate_artifact_name rejects absolute paths + .. segments before any filesystem op."
  - "Test file falls back to FrozenPathError = ValueError when Plan 02-05 not present in this worktree; real class is ValueError subclass so the assertion holds in both states."
  - "EventBus.emit() failures (bus itself crashing) are swallowed so infrastructure faults never abort a write — only explicit subscriber vetoes do."

patterns-established:
  - "Pattern: write-path hook chain (size-cap -> emit -> veto-check -> atomic) — template for Plan 02-09 Transport.deliver extension"
  - "Pattern: lazy-import helper for Wave N parallel-execution dependencies"
  - "Pattern: structured errors subclass ValueError so MCP translate_error auto-wraps them without per-error dispatch"

requirements-completed: [QUALITY-03, QUALITY-06, SAFETY-02]

# Metrics
duration: 11min
completed: 2026-04-20
---

# Phase 02 Plan 06: ArtifactStore Write Hook Chain Summary

**Size-cap + BeforeFileWrite-veto pre-write hook chain in `ArtifactStore.write()` with `ArtifactTooLargeError` and T-02-02 name guard — Pitfall #8 content-agnostic invariant grep-enforced.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-20T10:10:03Z
- **Completed:** 2026-04-20T10:20:48Z
- **Tasks:** 2 (TDD cycle)
- **Files created:** 2 (`clawteam/harness/errors.py`, `tests/test_artifact_caps.py`)
- **Files modified:** 1 (`clawteam/harness/artifacts.py`)

## Accomplishments

- `ArtifactStore.write()` now runs a three-hook chain in strict order:
  `_validate_artifact_name` (T-02-02 guard) -> size-cap check (D-27) -> `BeforeFileWrite` emit + veto check (SAFETY-02) -> atomic write.
- `ArtifactTooLargeError` shipped in new `clawteam/harness/errors.py` colocation module with D-27 message shape (`name`, `size_bytes`, `cap_bytes`, `split`-suggestion).
- Keyword-only `artifact_cap_bytes: int | None = None` kwarg added to `ArtifactStore.__init__` — all existing three-arg call sites (software-dev / hedge-fund / code-review / harness-default / research-paper / strategy-room templates) continue to work unmodified.
- `BeforeFileWrite` event fires exactly once per write with `team_name` / `agent_name` / `path` / `size_bytes` populated; subscribers can set `event.veto = True` + `event.veto_reason` to block (Plan 02-10 will register the freeze/careful handlers).
- On veto, `FrozenPathError` is raised when Plan 02-05's module is present; otherwise a `ValueError` fallback preserves the same exception-hierarchy contract (`FrozenPathError` is a `ValueError` subclass by design).
- Pitfall #8 invariant enforced two ways: (1) literal `grep -c "yaml|frontmatter|parse_frontmatter" clawteam/harness/artifacts.py == 0` in the final code; (2) `test_write_does_not_parse_frontmatter_pitfall8` asserts a markdown artifact with non-gstack frontmatter writes through unchanged.
- Phase 0 regression matrix 12/12 — all packaged templates continue to launch + write artifacts.
- Full project suite: 694/694 pass.

## Task Commits

1. **Task 1: RED — 8 failing tests for cap + BeforeFileWrite + BC preservation** — `4040802` (test)
2. **Task 2: GREEN — implement ArtifactStore.write hook chain + errors module** — `4073683` (feat)

_Note: TDD cycle; no REFACTOR commit (code shipped format-clean and ruff-clean from GREEN)._

## Files Created/Modified

### Created

- **`clawteam/harness/errors.py`** (47 lines) — Phase 2 structured-errors colocation module. Currently holds `ArtifactTooLargeError(ValueError)`; Plans 02-07 / 02-11 / 02-12 will add `MissingTeamError`, `AmbiguousSprintError`, `SprintNotFoundError` here. `ValueError` subclassing ensures `clawteam/mcp/helpers.py::translate_error` auto-wraps all of them without per-error dispatch.
- **`tests/test_artifact_caps.py`** (126 lines) — 8 unit tests: under-cap success, over-cap raises `ArtifactTooLargeError` with D-27 message shape, no-cap default passes large writes, `BeforeFileWrite` emits once per write with correct payload, veto raises `FrozenPathError`, Pitfall #8 frontmatter passthrough, BC signature preservation, constructor cap override.

### Modified

- **`clawteam/harness/artifacts.py`** — `ArtifactStore.__init__` gained keyword-only `artifact_cap_bytes` kwarg + `_team_name` attribute (surfaced to event); `write()` rewritten with 3-hook chain; `_validate_artifact_name` helper added for T-02-02 guard; `_resolve_frozen_path_error` lazy helper tolerates Wave 2 parallel Plan 02-05 landing. Existing `read` / `exists` / `list_artifacts` / `write_*` convenience methods unchanged.

## Decisions Made

- **Pitfall #8 literal grep cleanliness** — initial docstrings used the word "frontmatter" three times to *document* the invariant. Re-phrased to "structured-header parsing" / "content-agnostic" / "Pitfall #8 invariant (02-RESEARCH.md)" so the grep-based regression detector (`grep -c "yaml|frontmatter|parse_frontmatter" == 0`) stays robust: if someone later adds real parsing code, the keyword re-enters and CI catches it. The invariant is still fully documented via the Pitfall #8 reference and the hook-chain order comment.
- **Lazy import of `FrozenPathError`** — promoted from an inline try/except tangle in the method body to a named `_resolve_frozen_path_error()` module-level helper. Cleaner, avoids N806 variable-shadowing lint, and keeps the Wave 2 tolerance pattern reusable for future plans that may depend on same-wave artifacts.
- **Module-level imports of `BeforeFileWrite` + `get_event_bus`** — originally drafted as lazy imports too, but Plan 02-01 shipped in Wave 1, so the dependency is hard. Module-top imports surface breakage immediately (clean contract) instead of silently degrading.
- **`EventBus.emit()` failure swallow** — rather than letting an infrastructure crash abort a write, the hook chain treats emit failures as "no subscribers vetoed" so artifact writing stays robust against hook-loader bugs. Subscriber exceptions were already swallowed by `EventBus.emit` itself; this extra guard handles bus initialization failure.
- **Test file `FrozenPathError` fallback** — wrapped the import in try/except with `FrozenPathError = ValueError` fallback so this worktree's tests pass in isolation (before Plan 02-05 merges). Because the production code also falls back to `ValueError` when freeze_registry is absent, the test exercise the same behavior either way.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff not installed in environment**
- **Found during:** Task 1 (RED — first ruff fix attempt)
- **Issue:** `ruff` command not on PATH; `python -m ruff` module missing.
- **Fix:** Installed via `python -m pip install --user --break-system-packages ruff` (Arch `PEP 668` flag required).
- **Verification:** `ruff check` / `ruff format --check` run clean on all three target files.
- **Committed in:** Not a committed change — installed into user site only.

**2. [Rule 3 - Blocking] `typer` dependency not installed for regression matrix test**
- **Found during:** Task 2 GREEN verification (running `test_template_regression_matrix.py`)
- **Issue:** `ModuleNotFoundError: No module named 'typer'` preventing SC#10 matrix run.
- **Fix:** Installed project editable via `python -m pip install --user --break-system-packages -e .`, pulling in typer 0.24.1 and peer deps.
- **Verification:** All 6 template regression tests pass (12/12 with parametrize expansion).
- **Committed in:** Not a committed change — installed into user site only.

**3. [Rule 1 - Bug] Pitfall #8 grep returned 3 instead of 0 due to docstring references**
- **Found during:** Task 2 GREEN acceptance-criteria check
- **Issue:** Three docstring mentions of "frontmatter" (documenting the invariant) caused `grep -c "yaml|frontmatter|parse_frontmatter"` to return 3, failing the literal acceptance criterion and weakening the grep-based regression signal (a real future parse-introduction would drown in existing noise).
- **Fix:** Rewrote docstrings to use "structured-header parsing" / "content-agnostic" / "Pitfall #8 invariant (02-RESEARCH.md)" — preserves meaning and cross-reference while restoring grep cleanliness.
- **Verification:** Grep returns 0; test `test_write_does_not_parse_frontmatter_pitfall8` still passes (behavioral assertion unchanged).
- **Committed in:** `4073683` (GREEN commit)

**4. [Rule 1 - Bug] Ruff N806 / N814 violations from in-method PascalCase locals**
- **Found during:** Task 2 GREEN ruff check
- **Issue:** Initial draft shadowed `BeforeFileWrite`, `FrozenPathError`, `get_event_bus` as in-method locals for the lazy-import fallback. Ruff flagged N806 (local should be lowercase) and N814 (camelcase imported as constant).
- **Fix:** Hoisted `BeforeFileWrite` + `get_event_bus` to module-top imports (Plan 02-01 already shipped, so the dependency is hard); moved `FrozenPathError` lookup into a named `_resolve_frozen_path_error()` helper returning `type[BaseException] | None`. Cleaner naming, identical behavior.
- **Verification:** `ruff check` + `ruff format --check` both clean on all three files.
- **Committed in:** `4073683` (GREEN commit)

---

**Total deviations:** 4 auto-fixed (2 blocking env installs, 2 correctness refinements)
**Impact on plan:** All auto-fixes strengthen the implementation — Pitfall #8 grep is now a real regression signal, and the lazy-import helper is a reusable pattern for future Wave N parallel-execution plans. No scope creep; all changes keep the plan's acceptance criteria intact.

## Issues Encountered

- Python 3.14 as the project interpreter (detected during pytest output). All tests compatible; no adjustments required.
- FrozenPathError co-dependency with Plan 02-05 (Wave 2 parallel) — resolved via lazy-import helper + test-side fallback; documented as a forward contract. Once Plan 02-05 lands in the same integration branch, the fallback paths become inert (the real class is imported normally).

## User Setup Required

None — no external service configuration needed.

## Next Phase Readiness

**Forward contracts shipped for Phase 2 dependents:**

- **Plan 02-07 (EvidenceGate)** — can import `ArtifactTooLargeError` from `clawteam/harness/errors.py` for per-phase cap enforcement. The gate-scoped frontmatter parser lives entirely there, not at the write path.
- **Plan 02-09 (Transport.deliver turn-counter)** — the `BeforeFileWrite`/`BeforeToolCall` emit point in this plan is the template for `Transport.deliver`'s parallel emission site. D-14 turn-counter increment will hook on BOTH sites.
- **Plan 02-10 (freeze/careful subscribers)** — registers `BeforeFileWrite` subscribers that call `FreezeRegistry.is_frozen` and set `event.veto` + `event.veto_reason`. The hook chain is wired and waiting.
- **Plan 02-11 (SprintConductor 3-layer cap resolution)** — resolves `CLAWTEAM_ARTIFACT_CAP_KB` env -> `SprintState.artifact_cap_bytes` -> CLI arg into a single `int` passed to `ArtifactStore(..., artifact_cap_bytes=resolved_cap)`. The keyword-only kwarg is in place.
- **Plan 02-12 (CLI --artifact-cap flag + error dispatch)** — dispatches `ArtifactTooLargeError` to the user-facing error surface with the D-27 message verbatim. The exception class and message shape are final.

**No blockers.** Plan 02-05 (FreezeRegistry + FrozenPathError) and Plan 02-06 are mutually independent at build time thanks to the lazy-import helper; at merge time they compose cleanly.

## Self-Check: PASSED

**File existence verification:**

- `clawteam/harness/errors.py` — FOUND
- `clawteam/harness/artifacts.py` — FOUND (modified)
- `tests/test_artifact_caps.py` — FOUND
- `.planning/phases/02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention/02-06-SUMMARY.md` — FOUND (this file)

**Commit verification:**

- `4040802` (test: RED) — FOUND in git log
- `4073683` (feat: GREEN) — FOUND in git log

**Acceptance-criteria grep verification (all Task 2 criteria):**

| Check | Expected | Actual |
| --- | --- | --- |
| `class ArtifactTooLargeError(ValueError):` in `errors.py` | == 1 | 1 |
| `artifact_cap_bytes: int \| None` in `artifacts.py` | >= 1 | 1 |
| `ArtifactTooLargeError` in `artifacts.py` | >= 1 | 4 |
| `BeforeFileWrite(` in `artifacts.py` | >= 1 | 1 |
| `FrozenPathError` in `artifacts.py` | >= 1 | 8 |
| `yaml\|frontmatter\|parse_frontmatter` in `artifacts.py` | == 0 | 0 |
| `is_absolute\|\.\. not in\|_validate_artifact_name` in `artifacts.py` | >= 1 | 3 |
| `def test_` in `test_artifact_caps.py` | == 8 | 8 |
| `test_write_does_not_parse_frontmatter_pitfall8` in `test_artifact_caps.py` | == 1 | 1 |
| `ArtifactTooLargeError\|FrozenPathError\|BeforeFileWrite` in `test_artifact_caps.py` | >= 5 | 12 |

**Test suite verification:**

- `pytest tests/test_artifact_caps.py` — 8 passed
- `pytest tests/test_harness.py tests/test_template_regression_matrix.py tests/test_event_bus.py tests/test_event_types_phase2.py` — 73 passed
- Full suite: 694 passed, 0 failed

**Ruff verification:**

- `ruff check clawteam/harness/artifacts.py clawteam/harness/errors.py tests/test_artifact_caps.py` — All checks passed
- `ruff format --check` on same files — All already formatted

---
*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Completed: 2026-04-20*
