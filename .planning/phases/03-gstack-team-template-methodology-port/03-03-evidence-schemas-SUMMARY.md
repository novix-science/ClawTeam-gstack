---
phase: 03-gstack-team-template-methodology-port
plan: 03
subsystem: evidence-schemas
tags: [gstack, pydantic, evidence-schemas, literal, discriminator, pitfall-8, stub-defeat]

# Dependency graph
requires:
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: ArtifactFrontmatterBase + EvidenceSchemaRegistry + parse_frontmatter (schemas dispatched by artifact_type discriminator at plugin-load time)
  - plan: 03-01
    provides: Wave 0 substrate acknowledgement (schemas go under clawteam/templates/gstack/ per D-07 delete-invariant)
provides:
  - clawteam/templates/gstack/__init__.py — gstack scope package marker (D-07 delete invariant)
  - clawteam/templates/gstack/schemas/__init__.py — barrel re-exporting all 6 schemas in one statement
  - clawteam/templates/gstack/schemas/design_doc.py — DesignDoc (artifact_type="design-doc") + Think-phase rubric
  - clawteam/templates/gstack/schemas/plan_doc.py — PlanDoc + PlanTask (artifact_type="plan-doc") + Plan-phase rubric
  - clawteam/templates/gstack/schemas/test_report.py — TestReport (artifact_type="test-report") + qa_mode Literal + EvidenceGate post-check support
  - clawteam/templates/gstack/schemas/review_report.py — ReviewReport (artifact_type="review-report") + SHA-PIN-DEFERRED review_sha (Pitfall 9)
  - clawteam/templates/gstack/schemas/ship_notes.py — ShipNotes (artifact_type="ship-notes") + deploy_url for HEAD-probe + ship_step Literal
  - clawteam/templates/gstack/schemas/retro.py — Retro (artifact_type="retro") + per-persona attribution (D-09)
  - 12 fixture markdown files under tests/fixtures/gstack_artifacts/ (6 valid + 6 stub-tbd)
  - 38 new tests in tests/test_evidence_schemas.py proving round-trip + stub rejection + barrel one-statement import contract
  - Pitfall 8 structural prevention layer (stub-defeating min_length + Literal[...] constraints)
affects: [03-07 GstackSprintPlugin.contribute_evidence_schemas (one-statement import of all 6), phase-02 EvidenceGate post-check dispatch]

# Tech tracking
tech-stack:
  added: []  # pydantic v2 + typing.Literal already in standard stack; zero new deps
  patterns:
    - "One-module-per-schema + barrel re-export (clawteam.templates.gstack.schemas.*) — 03-07 consumes in one import statement"
    - "artifact_type: Literal[<name>] on every schema — serves as EvidenceSchemaRegistry discriminator key"
    - "Stub-defeating constraints in 5 flavors: min_length on prose, Literal[...] on enums, list min_length on collections, pattern regex for hex-SHA shape, ge/le for bounded ints"
    - "One valid + one stub-tbd fixture per schema — stub fixtures prove rejection by construction at test collection time (cannot be silently skipped)"
    - "Quoted datetime strings in YAML fixtures — yaml.safe_load otherwise coerces ISO-8601 to datetime, breaking pydantic str fields"

key-files:
  created:
    - clawteam/templates/gstack/__init__.py
    - clawteam/templates/gstack/schemas/__init__.py
    - clawteam/templates/gstack/schemas/design_doc.py
    - clawteam/templates/gstack/schemas/plan_doc.py
    - clawteam/templates/gstack/schemas/test_report.py
    - clawteam/templates/gstack/schemas/review_report.py
    - clawteam/templates/gstack/schemas/ship_notes.py
    - clawteam/templates/gstack/schemas/retro.py
    - tests/fixtures/gstack_artifacts/design-doc-valid.md
    - tests/fixtures/gstack_artifacts/design-doc-stub-tbd.md
    - tests/fixtures/gstack_artifacts/plan-doc-valid.md
    - tests/fixtures/gstack_artifacts/plan-doc-stub-tbd.md
    - tests/fixtures/gstack_artifacts/test-report-valid.md
    - tests/fixtures/gstack_artifacts/test-report-stub-tbd.md
    - tests/fixtures/gstack_artifacts/review-report-valid.md
    - tests/fixtures/gstack_artifacts/review-report-stub-tbd.md
    - tests/fixtures/gstack_artifacts/ship-notes-valid.md
    - tests/fixtures/gstack_artifacts/ship-notes-stub-tbd.md
    - tests/fixtures/gstack_artifacts/retro-valid.md
    - tests/fixtures/gstack_artifacts/retro-stub-tbd.md
  modified:
    - tests/test_evidence_schemas.py  # +280 lines of round-trip + rejection + barrel tests

key-decisions:
  - "Quoted datetime strings in YAML fixtures: yaml.safe_load coerces unquoted ISO-8601 (e.g. 2026-04-20T12:00:00Z) into a datetime.datetime object, which fails pydantic's str type validation on created_at. Fix: wrap all created_at values in double quotes. Caught immediately by test_valid_fixture_round_trips and resolved before Task 1 commit."
  - "task_id >=3 chars constraint forced fixture-id rename from t1/t2 to task-01/task-02. PlanTask.task_id has min_length=3 for Pitfall 8 stub-defeat (single-char IDs are classic placeholder gaming); fixture IDs bumped to match. The constraint stays; the fixture conforms."
  - "ReviewReport.review_sha enforces BOTH min_length=7 AND pattern='^[0-9a-f]+$'. Git short-SHA minimum is 7 chars, full SHA is 40 — any git-origin SHA will pass. Non-hex strings fail the regex; too-short hex strings fail min_length. Stub fixture uses 'xyz' to trigger both (length + pattern)."
  - "ShipNotes accepts literal '<pending>' as a valid deploy_url per D-02 Phase-5 tool-availability stub. The constraint is min_length=1 (rejects empty), not a URL pattern — so shipper can emit a placeholder while coordinating manually with ceo until Phase 5's /ship lands. Acceptance test: test_pending_deploy_url_accepted."
  - "Retro.personas min_length=2 defeats solo-ceo-post-mortem degenerate case (D-09 per-persona attribution requirement). Any real retro has at minimum the leader + one other contributor signing. Acceptance test: test_single_persona_rejected."
  - "Barrel __init__.py authored incrementally across 3 task commits (DesignDoc+PlanDoc in commit 1; +TestReport+ReviewReport in commit 2; +ShipNotes+Retro in commit 3). Each intermediate commit's barrel imports ONLY modules that exist in that commit — pytest collection never fails on un-created schemas."

patterns-established:
  - "Pattern: gstack-scoped schema package — all new gstack pydantic models live under clawteam/templates/gstack/schemas/; deletion of clawteam/templates/gstack/ removes all Phase 3 schema code without touching core harness (D-07 delete invariant honored)"
  - "Pattern: one-statement plugin import — from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro — consumed verbatim by 03-07 GstackSprintPlugin.contribute_evidence_schemas"
  - "Pattern: valid+stub fixture pairs per schema — 12 fixtures (6 valid + 6 stub-tbd) prove rejection behavior at test time; verifier cannot skip the stub rejection contract"
  - "Pattern: YAML fixture discipline — all datetime strings MUST be double-quoted (yaml.safe_load otherwise coerces to datetime); noted in deferred-items for downstream plan authors"

requirements-completed:
  - SPRINT-06   # Retro schema defines reflect-phase artifact shape that SprintConductor retro placeholder (D-09) round-trips against — pydantic structure now exists
  - TEAM-04     # Review/Ship/Retro schemas include reviewer_persona/personas fields that let conductor-layer identity check verify author persona matches claimed role

# Metrics
duration: ~10min (split across two agent sessions — prior session wrote Task 1 uncommitted; this session committed Task 1 + executed Tasks 2-3 end to end)
completed: 2026-04-21
---

# Phase 3 Plan 03-03: Evidence Schemas Summary

**6 pydantic v2 evidence schemas (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro) at `clawteam/templates/gstack/schemas/` with stub-defeating `min_length` + `Literal[...]` + hex-pattern + list-arity constraints + 12 fixture markdown files (6 valid + 6 stub-tbd) + 38 new tests proving round-trip and Pitfall 8 rejection behavior — ready for 03-07 plugin wiring via one-statement barrel import.**

## Performance

- **Duration:** ~10 min across two sessions (prior agent stream drafted Task 1 files uncommitted before timeout; this session verified + committed Task 1, then executed Tasks 2-3 end to end including auto-fixed YAML datetime bug)
- **Tasks:** 3 / 3
- **Files created:** 20 (8 .py + 12 .md fixtures)
- **Files modified:** 1 (tests/test_evidence_schemas.py, +280 lines)
- **Lines added:** ~427 LOC total (schemas ~260 + fixtures ~167)
- **Test count delta:** +38 tests in tests/test_evidence_schemas.py (8 pre-existing Phase 2 tests preserved; 46 total in file, all green)

## Accomplishments

- **6 pydantic v2 schemas shipped** under the D-07 gstack-scoped location (`clawteam/templates/gstack/schemas/`). Delete invariant honored: removing `clawteam/templates/gstack/` removes ALL Phase 3 pydantic-schema code without touching `clawteam/harness/` or any other directory.
- **Each schema declares `artifact_type: Literal[<name>]`** as the discriminator key for 03-07's `GstackSprintPlugin.contribute_evidence_schemas` — six `EvidenceSchemaRegistry.register(name, cls)` calls in the plugin's on_register hook will wire all six to Phase 2's registry.
- **Stub-defeating constraint catalog** (verified by 12 fixture pairs):
  | Schema | Constraint flavor(s) applied | Stub fixture triggers |
  |--------|------------------------------|-----------------------|
  | DesignDoc | min_length 120/50/50/120 on prose; Literal[3] on pm_verdict; list min_length=max_length=6 on forcing_questions_addressed | `TBD` prose + pm_verdict='maybe' + [1] instead of [1..6] |
  | PlanDoc | min_length 120/80 on prose; list min_length=1 on tasks; min_length=3 on edge_cases; nested PlanTask min_length/ge/le | `TBD` + empty tasks + empty edge_cases |
  | TestReport | min_length=5 on test_command; min_length=30 on output_excerpt; ge=0 on passed/failed; Literal[qa, qa-only] on qa_mode | empty test_command + `TBD` output_excerpt |
  | ReviewReport | min_length=7 + pattern='^[0-9a-f]+$' on review_sha; Literal[4] on verdict; list min_length=1 on findings; min_length=2 on reviewer_persona | 'xyz' (3-char, non-hex-beyond-prefix) + 'ship-it-anyway' (invalid Literal) + empty findings |
  | ShipNotes | min_length=1 on deploy_url; Literal[8] on ship_step; min_length=20 on notes | empty deploy_url + 'random' ship_step + `TBD` notes |
  | Retro | list min_length=2 on personas (defeats solo post-mortem); list min_length=1 on what_worked + key_lessons | empty personas + empty what_worked + empty key_lessons |
- **12 round-trip + rejection fixtures committed** under `tests/fixtures/gstack_artifacts/` — 6 valid (exercise happy path at pydantic validate time) + 6 stub-tbd (prove ValidationError raised by construction; Pitfall 8 defeat).
- **One-statement plugin-import contract satisfied** (`TestGstackBarrelComplete.test_one_statement_import_all_six`):
  ```python
  from clawteam.templates.gstack.schemas import (
      DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro,
  )
  ```
  03-07 consumes this in `GstackSprintPlugin.contribute_evidence_schemas` without any per-schema pathwork.
- **Path-traversal guard** (`_load_fixture_meta`) rejects `..`, `/`, and dotfile-prefix names — T-03-12 mitigation landed with Task 1.
- **YAML datetime coercion bug auto-fixed** (Rule 1): yaml.safe_load coerces unquoted ISO-8601 strings to datetime objects, which fails pydantic's `str` type validation. Fix: all `created_at` values in fixtures are now double-quoted. Caught immediately by Task 1's round-trip test, resolved before any Task 1 commit.
- **`task_id` >=3 constraint enforced** (Rule 1): PlanTask.task_id `min_length=3` rejected fixture IDs `t1`/`t2`. Fixed by renaming to `task-01`/`task-02`. Constraint stayed (Pitfall 8 defeats single-char placeholder gaming); fixture conformed.

## Task Commits

| Task | Commit | Files |
|------|--------|-------|
| 1. DesignDoc + PlanDoc + gstack package + schemas package + barrel (partial) + 4 fixtures + 10 tests | `9489bc2` | 9 files |
| 2. TestReport + ReviewReport + barrel extend + 4 fixtures + 11 tests | `d47a798` | 8 files |
| 3. ShipNotes + Retro + barrel finalize + 4 fixtures + 15 tests (incl. one-statement import contract) | `c60a69d` | 8 files |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] YAML datetime coercion in fixtures**
- **Found during:** Task 1 (very first `pytest` run after initial fixture writes — prior agent session)
- **Issue:** `created_at: 2026-04-20T12:00:00Z` (unquoted) parsed by `yaml.safe_load` as `datetime.datetime(2026, 4, 20, tzinfo=UTC)`, fails pydantic `str` type validation on DesignDoc.created_at
- **Fix:** Wrapped all 6 `created_at` fixture values in double-quotes (e.g., `"2026-04-20T12:00:00Z"`) so YAML preserves them as strings
- **Files modified:** 6 `*-valid.md` fixtures (design-doc, plan-doc, test-report, review-report, ship-notes, retro — all valid fixtures; stub fixtures already had empty strings)
- **Commit:** Rolled into Task 1 commit `9489bc2`

**2. [Rule 1 - Bug] PlanTask.task_id too short in plan-doc-valid fixture**
- **Found during:** Task 1 (after datetime fix, next pytest run)
- **Issue:** Fixture used `task_id: t1` / `t2` (2 chars); PlanTask schema enforces `task_id: str = Field(..., min_length=3)` per Pitfall 8 defeat of single-char placeholder gaming
- **Fix:** Renamed fixture IDs to `task-01` / `task-02` to satisfy min_length=3; schema constraint unchanged (it is correct; fixture was wrong)
- **Files modified:** tests/fixtures/gstack_artifacts/plan-doc-valid.md
- **Commit:** Rolled into Task 1 commit `9489bc2`

### Out-of-scope Observations

- `tests/test_sprint_conductor.py::test_resume_after_process_restart` is a pre-existing subprocess-based flake (fails identically on `git stash` baseline). Already logged in `deferred-items.md` by plan 03-02. Not caused by or affected by 03-03.

## Test Results

**Scope suite (test_evidence_schemas.py):** 46 passed (8 pre-existing Phase 2 + 38 new for 03-03)

**Broader scope (schemas-adjacent files):** 190 passed across:
- tests/test_evidence_schemas.py (46)
- tests/test_envelope_personas.py + tests/test_team_manager_memory.py + tests/test_turn_envelope.py + tests/test_evidence_gate.py + tests/test_plugin_hooks.py + tests/test_template_regression_matrix.py + tests/test_gstack_template.py + tests/test_templates.py (144)

**Phase 2 regression check:** All 6 existing templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) still pass `test_template_regression_matrix.py` unchanged (D-07 delete-invariant + Pattern 1 strict-additive extension preserved).

## Integration Contract (for 03-07 GstackSprintPlugin)

When 03-07 writes `GstackSprintPlugin.contribute_evidence_schemas`, it can import all six schemas in one statement:

```python
from clawteam.templates.gstack.schemas import (
    DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro,
)

class GstackSprintPlugin(HarnessPlugin):
    def contribute_evidence_schemas(self) -> dict[str, type]:
        return {
            "design-doc": DesignDoc,
            "plan-doc": PlanDoc,
            "test-report": TestReport,
            "review-report": ReviewReport,
            "ship-notes": ShipNotes,
            "retro": Retro,
        }
```

The plugin manager's `_instantiate_and_register` (Plan 02-01) will call `register_schema(name, cls)` for each entry, populating Phase 2's `EvidenceSchemaRegistry`. `EvidenceGate.check` at runtime dispatches via `get_schema(meta['artifact_type'])` — pydantic `ValidationError` on stub-grade artifacts lands structurally.

## Known Stubs

None. All six schemas are fully populated pydantic models; all 12 fixtures have real content (valid fixtures exercise happy path; stub-tbd fixtures deliberately contain stub-grade content to PROVE rejection is enforced). The stub-tbd fixtures are intentional test inputs — not unintended placeholders.

## Self-Check: PASSED

- All 20 created files exist at their documented paths (verified via ls)
- All 3 task commits present in git log (9489bc2, d47a798, c60a69d)
- 46/46 tests pass in tests/test_evidence_schemas.py
- Barrel one-statement import confirmed via python -c
- `__all__` equality confirmed via python -c
- 12 fixtures present (6 valid + 6 stub-tbd)
- 7 .py files in schemas/ (6 schemas + __init__.py)
- Phase 2 regression matrix still green
