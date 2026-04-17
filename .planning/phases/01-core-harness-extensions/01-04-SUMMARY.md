---
phase: 01-core-harness-extensions
plan: 04
subsystem: sprint
tags: [question-answer, pydantic, frontmatter, markdown-schema, round-trip, stdlib-parser, phase-1, tdd, d-08]

# Dependency graph
requires:
  - phase: 01-core-harness-extensions
    provides: Plan 01-01 — PhaseRegistry + HarnessPlugin hooks (enables sprint subsystem registration in Phase 2)
  - phase: 01-core-harness-extensions
    provides: Plan 01-02 (wave-2 sibling) — SprintState pydantic model (gate-compat integration test imports; wrapped skipif in this worktree, runs after merge)
  - phase: 01-core-harness-extensions
    provides: Plan 01-03 (wave-2 sibling) — InteractionGate (gate-compat integration test imports; wrapped skipif in this worktree, runs after merge)
provides:
  - Question pydantic v2 model with Literal["multi-choice","freeform","confirm"] type and conditional-choices model validator
  - Answer pydantic v2 model mirroring Question's serialization surface
  - Choice pydantic v2 model — {id, label} record used only by multi-choice questions
  - Question.to_markdown() / Question.from_markdown() — D-08 round-trip with deterministic field order
  - Answer.to_markdown() / Answer.from_markdown() — same shape, answer-side keys
  - _parse_frontmatter stdlib-only YAML-frontmatter parser (re + str.splitlines, no pyyaml dep)
  - 5 canonical D-08 fixtures for downstream Phase 4 golden-trace tests
affects:
  - 01-05 (skills-memory) — consumes Question artifact path convention
  - 02-sprint-engine — SprintConductor writes/reads Question + Answer through these helpers (SPRINT-01 … SPRINT-06)
  - 04-interactive — /office-hours, /design-consultation, /investigate state machines serialize questions via Question.to_markdown()
  - 04-verification — gate-compat integration test post-merge proves InteractionGate + Question compose end-to-end

# Tech tracking
tech-stack:
  added: []  # zero new runtime deps — stdlib-only parser per PROJECT.md constraint
  patterns:
    - "Narrow-schema stdlib parser — avoid full-YAML dep by accepting only the D-08 shape (flat key:value + one nested choices list). Swap for pyyaml in Phase 4 if richer structure is needed, behind the same classmethod API."
    - "Deterministic to_markdown field order — enables Phase 4 golden-trace byte comparison"
    - "model_validator(mode='after') for cross-field invariants — type/choices interdependency"
    - "Parallel-wave test gating — @skipif(not _<CAPABILITY>_READY) for sibling-worktree dependencies; auto-activates at merge"

key-files:
  created:
    - clawteam/sprint/qa.py (224 lines — Question + Answer + Choice + stdlib-only _parse_frontmatter)
    - tests/test_sprint_qa.py (221 lines — 10 test functions; 9 active, 1 skip-gated for wave merge)
    - tests/fixtures/qa/question_multi_choice.md (canonical D-08 multi-choice fixture)
    - tests/fixtures/qa/question_freeform.md (canonical D-08 freeform fixture)
    - tests/fixtures/qa/question_confirm.md (canonical D-08 confirm fixture)
    - tests/fixtures/qa/answer_multi_choice.md (canonical D-08 multi-choice answer)
    - tests/fixtures/qa/answer_freeform.md (canonical D-08 freeform answer)
  modified: []

key-decisions:
  - "D-07 reaffirmed: 8-char hex id via uuid.uuid4().hex[:8] default_factory — matches SprintContract.id + SprintState.sprint_id conventions."
  - "D-08 reaffirmed: pydantic-backed YAML frontmatter + body prose; body preserved verbatim below the closing '---' fence."
  - "Stdlib-only parser is the right cost/risk trade — PROJECT.md's 'no new required runtime deps' rules out pyyaml, and the narrow D-08 shape never needs anchors/aliases/multi-line scalars in Phase 1. Swap point documented for Phase 4."
  - "model_validator rejects multi-choice w/o choices AND freeform/confirm with choices — pydantic raises at construction; no deferred validation path."
  - "Parallel-wave dependency resolution via try/except ImportError + @skipif — keeps this worktree's test file collectable pre-merge without sacrificing the end-to-end integration proof post-merge."

patterns-established:
  - "D-08 markdown-frontmatter serialization: deterministic field order, key order Question (id, slug, type, created_at, sprint_id, phase, author, choices) / Answer (question_id, answered_at, choice) for golden-trace stability."
  - "Threat-model-driven parser hardening: reject missing fences, non-key lines, unexpected indentation; raise ValueError with actionable reason; pydantic catches anything the parser lets through."
  - "YAML-CVE avoidance by construction: by refusing to depend on a full-YAML parser, we sidestep the entire yaml.unsafe_load CVE class (T-01-20 mitigation by design)."

requirements-completed:
  - INT-01  # gate-compatible write path — Question.to_markdown produces files InteractionGate detects (post-merge integration test proves this)
  - INT-02  # question/answer markdown schema with choices + freeform + confirm variants

# Metrics
duration: 7min
completed: 2026-04-17
---

# Phase 01 Plan 04: Question/Answer Schema (D-08) Summary

**Landed the Question/Answer pydantic models + stdlib-only D-08 markdown-frontmatter round-trip that every Phase 4 interactive skill (office-hours, design-consultation, investigate) will serialize through.**

## Performance

- **Duration:** ~7 min
- **Started:** 2026-04-17T10:49:21Z
- **Completed:** 2026-04-17T10:56:02Z
- **Tasks:** 2/2 (Task 1 RED, Task 2 GREEN)
- **Files created:** 7 (1 module + 1 test file + 5 fixtures)
- **Files modified:** 0

## Accomplishments

### Task 1 — RED: tests + fixtures (commit `4c79298`)

- 5 D-08 fixture files under `tests/fixtures/qa/` — 3 question types (multi-choice, freeform, confirm) × 2 answer types (multi-choice, freeform). These are the canonical examples Phase 4 golden-trace tests and parser round-trip tests consume.
- 10 test functions in `tests/test_sprint_qa.py` covering: default-id field validation, type-literal rejection, multi-choice choices requirement, freeform/confirm choices rejection, to_markdown shape assertions (multi-choice + freeform), fixture parse, round-trip equality (questions), round-trip equality (answers), and InteractionGate compatibility.
- RED proof: `ModuleNotFoundError: clawteam.sprint.qa` at collection time.

### Task 2 — GREEN: implementation (commit `0faf56c`)

- `clawteam/sprint/qa.py` (224 lines) exports `Question`, `Answer`, `Choice` pydantic v2 models plus module-private `_parse_frontmatter` / `_strip_inline_comment` helpers.
- `Question` model validator enforces the type/choices interdependency: multi-choice requires ≥1 choice; freeform/confirm must not declare choices. Invalid combinations raise `ValueError` wrapped in pydantic `ValidationError`.
- `to_markdown()` emits deterministic field order for future golden-trace byte comparison. `from_markdown()` round-trips via `model_dump()` structural equality.
- Stdlib-only parser: `re` for inline-comment stripping + `str.splitlines` for line traversal. Accepts exactly the D-08 shape (flat key/value + one nested `choices:` list of `{id, label}` records); raises `ValueError("invalid question/answer frontmatter: …")` on any other shape.
- GREEN proof: 9/10 tests pass in this worktree; 1 integration test skipped pending wave-2 merge (see Deviations below). Full suite: 629 passed, 1 skipped, no regressions.
- Phase 0 regression matrix (`tests/test_template_regression_matrix.py`): 12/12 still green.

## Verification

- Ruff: `ruff check clawteam/sprint/qa.py tests/test_sprint_qa.py` → all checks passed.
- New tests: `pytest tests/test_sprint_qa.py -v` → 9 passed, 1 skipped (gate-compat integration, see below).
- Regression matrix: 12/12 passed.
- Full suite: 629 passed, 1 skipped, 2 warnings (pre-existing fork-deprecation warning in `test_task_store_locking.py`, unrelated).
- Structural acceptance-criteria greps:
  - `class Question(BaseModel)` → 1 ✓
  - `class Answer(BaseModel)` → 1 ✓
  - `class Choice(BaseModel)` → 1 ✓
  - `def to_markdown` → 2 ✓
  - `def from_markdown` → 2 ✓
  - `Literal["multi-choice"…"freeform"…"confirm"]` → 1 ✓
  - `import (yaml|pyyaml)` → 0 ✓ (stdlib-only)
  - `uuid.uuid4().hex[:8]` → 1 ✓ (D-07 id format)
- Round-trip smoke test via `python -c '...'` → "round-trip OK".

## Deviations from Plan

### [Rule 3 — Blocking issue] Parallel-wave test-collection guard for gate-compat integration test

- **Found during:** Task 1 RED verification, reconfirmed at Task 2 GREEN run.
- **Issue:** Plans 01-02 (SprintState) and 01-03 (InteractionGate) land on sibling wave-2 worktrees. At this worktree's base commit `c077d6e` neither `clawteam/sprint/state.py` nor `clawteam/harness/interaction_gate.py` exists. The plan's Task 1 test file imports both at module top, which caused the entire file to fail at collection with `ModuleNotFoundError: clawteam.harness.interaction_gate` — 9 pure-qa tests (which do NOT need 01-02/01-03 artifacts) could not run, defeating GREEN verification for my scope.
- **Fix:** Moved `InteractionGate` + `SprintState` imports into a `try/except ImportError` block setting a module-level `_GATE_COMPAT_READY` flag, and decorated the single cross-plan test `test_gate_detects_question_file_written_via_to_markdown` with `@pytest.mark.skipif(not _GATE_COMPAT_READY, reason="…")`. The test re-imports `InteractionGate` + `SprintState` inside its body so it only runs when both siblings are merged in.
- **Effect:** In this worktree: 9 passed, 1 skipped. After the orchestrator merges all wave-2 branches the skip auto-deactivates and the test runs, proving end-to-end composition of Plan 01-04 (Question schema) + Plan 01-03 (InteractionGate) + Plan 01-02 (SprintState).
- **Files modified:** `tests/test_sprint_qa.py`
- **Commit:** `0faf56c` (bundled with the feat commit)

### [Minor, non-semantic] Parser partition variable naming

- **Found during:** Task 2 implementation.
- **Issue:** The plan's action-block source used `_, _, value = line.partition(":")` and then `if not _` to detect the missing separator. Reusing `_` as both a throwaway and a boolean anchor would trip linters and makes intent ambiguous.
- **Fix:** Renamed the separator captures to `sep` / `sep2` in the two nested parser loops. Semantics identical (`partition` returns `(head, separator, tail)` where `separator` is either `":"` or `""`). Outer `key, _, value = line.partition(":")` — where the middle is genuinely discarded — retained.
- **Files modified:** `clawteam/sprint/qa.py`
- **Commit:** `0faf56c`

### [Minor] Ruff import-order auto-fixes

- **Found during:** Both tasks — ruff flagged unsorted import blocks at first lint.
- **Fix:** Ran `ruff check --fix` on both `tests/test_sprint_qa.py` and `clawteam/sprint/qa.py`. Purely mechanical reorder; no semantic change.
- **Effect:** Final state: `All checks passed!` — no outstanding lint.

## Threat Flags

None. This plan's threat surface is fully captured in the plan's `<threat_model>` (T-01-16 through T-01-20). No new endpoints, auth paths, or filesystem surface were introduced beyond what the plan's mitigations cover. The stdlib-only parser is a mitigation-by-design for T-01-20 (YAML CVE class).

## Known Stubs

None. Both models are fully wired — `to_markdown` + `from_markdown` round-trip through every fixture. No placeholder UI, no hardcoded empty data flows, no "coming soon" paths. The deferred field set (`priority`, `urgency`, `tags`) is explicitly out of scope for Phase 1 per the plan; Phase 4 adds them if office-hours design requires.

## Forward Contracts

- **Phase 2 sprint engine (SPRINT-01 … SPRINT-06):** `SprintConductor` will write questions via `Question.to_markdown()` + existing `atomic_write_text`; read them back via `Question.from_markdown()`. No additional write-API is required from this plan; Plan 01-05 likewise leaves `InteractionGate` in presence-only mode.
- **Phase 4 interactive skills (/office-hours, /design-consultation, /investigate):** State machines consume `Question` + `Answer` types directly. The deterministic `to_markdown` field order is the golden-trace anchor for phase-transition tests.
- **Phase 4 richer schema:** If multi-line labels, nested dicts, or anchors become necessary, the stdlib parser is swapped for pyyaml (moved to optional-extra, not required dep) behind the same `from_markdown` classmethod. Call sites remain unchanged.
- **Orchestrator wave merge:** `tests/test_sprint_qa.py::test_gate_detects_question_file_written_via_to_markdown` auto-activates when Plans 01-02 and 01-03 land. The test proves INT-01 + INT-02 integration end-to-end.

## Key Risks Closed

- **T-01-20 (YAML parser CVE class):** Mitigation by design — narrow D-08 parser cannot execute the `!!python/object` or anchor/alias families of tags because those productions are not implemented. Phase 4's parser swap must keep the narrow-API surface or re-open this risk.
- **T-01-16 (malformed frontmatter crash):** Mitigation confirmed — parser raises `ValueError` with actionable reason on all invalid shapes (missing fences, unexpected indentation, non-key lines, missing separators). Pydantic layer catches any shape the parser lets through.

## Self-Check: PASSED

- File `clawteam/sprint/qa.py` — FOUND
- File `tests/test_sprint_qa.py` — FOUND
- File `tests/fixtures/qa/question_multi_choice.md` — FOUND
- File `tests/fixtures/qa/question_freeform.md` — FOUND
- File `tests/fixtures/qa/question_confirm.md` — FOUND
- File `tests/fixtures/qa/answer_multi_choice.md` — FOUND
- File `tests/fixtures/qa/answer_freeform.md` — FOUND
- Commit `4c79298` (test RED) — FOUND in `git log`
- Commit `0faf56c` (feat GREEN) — FOUND in `git log`

## TDD Gate Compliance

- RED gate: `4c79298` — `test(01-04): add failing tests + fixtures for Question/Answer markdown schema (D-08)` ✓
- GREEN gate: `0faf56c` — `feat(01-04): Question/Answer pydantic models + stdlib-only D-08 frontmatter round-trip` ✓ (after RED in history)
- REFACTOR gate: skipped — no cleanup needed; implementation was written cleanly the first time.

Gate sequence intact: RED → GREEN, TDD flow verified.
