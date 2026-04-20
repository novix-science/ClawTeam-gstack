---
phase: 03-gstack-team-template-methodology-port
plan: 03
type: execute
wave: 1
depends_on: [03-01]
files_modified:
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
  - tests/test_evidence_schemas.py
autonomous: true
requirements: [SPRINT-06, TEAM-04]
must_haves:
  truths:
    - "Six pydantic v2 schemas (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro) instantiate from valid fixture content and reject stub-grade content"
    - "Each schema declares `artifact_type: Literal[<name>]` so it can serve as a discriminator key in EvidenceSchemaRegistry"
    - "Stub-grade inputs (`TBD`, body < min_length, missing forcing-question count) raise ValidationError, defeating Pitfall 8 gate gaming"
    - "Schemas live under `clawteam/templates/gstack/schemas/` honoring D-07 delete invariant — removing the gstack/ tree leaves the rest of the codebase unaffected"
    - "Each schema is round-trip importable through the barrel `clawteam.templates.gstack.schemas` module so the plugin (03-07) can `from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc, ...` in one statement"
  artifacts:
    - path: "clawteam/templates/gstack/schemas/__init__.py"
      provides: "Barrel module re-exporting the 6 schemas"
      contains: "from clawteam.templates.gstack.schemas.design_doc import DesignDoc"
    - path: "clawteam/templates/gstack/schemas/design_doc.py"
      provides: "DesignDoc pydantic model with artifact_type Literal + min_length stub-defeating constraints"
      contains: "Literal[\"design-doc\"]"
    - path: "clawteam/templates/gstack/schemas/plan_doc.py"
      provides: "PlanDoc pydantic model"
      contains: "Literal[\"plan-doc\"]"
    - path: "clawteam/templates/gstack/schemas/test_report.py"
      provides: "TestReport pydantic model with test_command field for EvidenceGate post-check"
      contains: "test_command"
    - path: "clawteam/templates/gstack/schemas/review_report.py"
      provides: "ReviewReport pydantic model with review_sha for Pitfall 9 SHA-pinning lookahead"
      contains: "review_sha"
    - path: "clawteam/templates/gstack/schemas/ship_notes.py"
      provides: "ShipNotes pydantic model with deploy_url for EvidenceGate HEAD-probe"
      contains: "deploy_url"
    - path: "clawteam/templates/gstack/schemas/retro.py"
      provides: "Retro pydantic model with per-persona attribution"
      contains: "personas"
    - path: "tests/fixtures/gstack_artifacts/"
      provides: "12 fixture files (6 valid + 6 stub-grade) for schema round-trip + rejection tests"
      contains: "design-doc-valid.md"
  key_links:
    - from: "clawteam/templates/gstack/schemas/__init__.py"
      to: "clawteam/templates/gstack/schemas/<schema>.py"
      via: "from clawteam.templates.gstack.schemas.<module> import <Schema>"
      pattern: "from clawteam.templates.gstack.schemas"
    - from: "tests/test_evidence_schemas.py"
      to: "clawteam/templates/gstack/schemas/"
      via: "round-trip validation against fixture markdown bodies"
      pattern: "import.*gstack.schemas"
    - from: "clawteam/templates/gstack/schemas/<schema>.py"
      to: "clawteam.harness.evidence_schemas.EvidenceSchemaRegistry"
      via: "registered later by GstackSprintPlugin.contribute_evidence_schemas (03-07)"
      pattern: "artifact_type.*Literal"
---

<objective>
Define the six pydantic v2 evidence schemas (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro) under `clawteam/templates/gstack/schemas/` so the GstackSprintPlugin (03-07) can register them via `contribute_evidence_schemas` against Phase 2's `EvidenceSchemaRegistry`. Each schema enforces stub-defeating `min_length` and `Literal[...]` constraints (Pitfall 8 prevention) and uses `artifact_type: Literal[<name>]` as the discriminator key. Ships 12 round-trip fixture markdown files (6 valid + 6 stub-grade) that drive the round-trip + rejection tests in `tests/test_evidence_schemas.py`.

Purpose: After this plan, the schemas exist and round-trip cleanly, but they are NOT yet registered in the registry. Registration is the plugin's responsibility (03-07). This separation lets the schemas be defined + tested in parallel with 03-04 (envelopes) and 03-02 (template/roster), maximizing Wave 1 parallelism.

Output:
- `clawteam/templates/gstack/__init__.py` (empty package marker)
- `clawteam/templates/gstack/schemas/__init__.py` (barrel re-exports)
- 6 schema files (one per artifact type)
- 12 fixture markdown files (6 valid + 6 stub-grade)
- Extensions to `tests/test_evidence_schemas.py` covering 6 round-trip + 6 rejection scenarios (12 new tests minimum)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md
@.planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md
@.planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md
@.planning/phases/03-gstack-team-template-methodology-port/03-VALIDATION.md
@.planning/phases/03-gstack-team-template-methodology-port/03-01-SUMMARY.md

<interfaces>
<!-- Phase 2 base class — Phase 3 schemas inherit from BaseModel directly per RESEARCH.md sketch (each schema is self-contained, not a subclass of ArtifactFrontmatterBase). The artifact_type Literal makes each schema a discriminator-key candidate. -->

From clawteam/harness/evidence_schemas.py (Phase 2 — base class for reference; Phase 3 may inherit OR use BaseModel directly):
```python
class ArtifactFrontmatterBase(BaseModel):
    """Base pydantic model for durable-artifact YAML frontmatter."""
    persona: str
    step_label: str
    done: bool
    artifact_type: str
    created_at: str
```

From clawteam/templates/gstack/schemas/design_doc.py (RESEARCH.md §Code Examples lines 696-720 — the worked example to copy):
```python
from typing import Literal
from pydantic import BaseModel, Field

class DesignDoc(BaseModel):
    """Think-phase artifact. Written by pm + ceo collaboratively."""
    artifact_type: Literal["design-doc"]
    problem_statement: str = Field(..., min_length=120)
    users: str = Field(..., min_length=50)
    constraints: str = Field(..., min_length=50)
    rationale: str = Field(..., min_length=120)
    pm_verdict: Literal["proceed", "reframe", "kill"]
    forcing_questions_addressed: list[int] = Field(..., min_length=6, max_length=6)
    sprint_id: str
    created_at: str
```

From tests/test_evidence_schemas.py (Phase 2 — round-trip + rejection patterns to extend):
```python
def setup_function() -> None:
    reset_registry()

def teardown_function() -> None:
    reset_registry()

def test_artifact_frontmatter_base_fields() -> None:
    env = ArtifactFrontmatterBase(
        persona="engineer", step_label="build:1/3", done=False,
        artifact_type="x", created_at="2026-04-17T00:00:00Z",
    )
    assert env.persona == "engineer"
```

From RESEARCH.md per-schema field shape sketch (CONTEXT.md "Claude's Discretion" §1 — planner refines):
- DesignDoc: above (verbatim)
- PlanDoc: tasks[], dependencies[], estimates[], plan_owner, sprint_id (per /plan-eng-review)
- TestReport: test_command (str, required for evidence_gate.py:16-18 dispatch), passed (int), failed (int), output_excerpt (str)
- ReviewReport: review_sha (str, ≥7 hex chars; Pitfall 9 SHA-PIN-DEFERRED), verdict Literal, hypothesis_traces (list[str])
- ShipNotes: deploy_url (str, required for evidence_gate.py:19-21 HEAD-probe), ship_step Literal
- Retro: personas (list[str]; per-persona attribution), what_worked, what_failed, key_lessons
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create gstack/ package + schemas package + DesignDoc + PlanDoc</name>
  <files>clawteam/templates/gstack/__init__.py, clawteam/templates/gstack/schemas/__init__.py, clawteam/templates/gstack/schemas/design_doc.py, clawteam/templates/gstack/schemas/plan_doc.py, tests/fixtures/gstack_artifacts/design-doc-valid.md, tests/fixtures/gstack_artifacts/design-doc-stub-tbd.md, tests/fixtures/gstack_artifacts/plan-doc-valid.md, tests/fixtures/gstack_artifacts/plan-doc-stub-tbd.md, tests/test_evidence_schemas.py</files>
  <read_first>
    - clawteam/harness/evidence_schemas.py (lines 1-90 — ArtifactFrontmatterBase + register_schema + get_schema; confirm reset_registry export name)
    - tests/test_evidence_schemas.py (Phase 2 — full file; identify import shape, setup/teardown pattern, extension append point)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 236-310 — schemas pattern + barrel __init__.py; lines 731-770 — fixture markdown layout)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 693-720 — DesignDoc verbatim worked example; line 305-309 — per-schema field shape sketch)
    - tests/fixtures/qa/answer_freeform.md (existing fixture markdown layout — frontmatter + body)
  </read_first>
  <behavior>
    - Test 1: `DesignDoc` instantiates with all required fields populated to valid lengths; assert `artifact_type == "design-doc"`.
    - Test 2: `DesignDoc` rejects `problem_statement` shorter than 120 chars (Pitfall 8 stub).
    - Test 3: `DesignDoc` rejects `forcing_questions_addressed` with fewer than 6 items.
    - Test 4: `DesignDoc` rejects `pm_verdict="invalid"` (Literal mismatch).
    - Test 5: `PlanDoc` instantiates with valid tasks/dependencies/estimates; rejects empty tasks list.
    - Test 6: `PlanDoc` rejects `artifact_type="plan"` (must be exactly `"plan-doc"`).
    - Test 7: `from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc` succeeds via barrel re-export.
  </behavior>
  <action>
**File 1 — `clawteam/templates/gstack/__init__.py`:** Empty package marker.

```python
"""gstack template scope (Phase 3): pydantic schemas, per-persona envelopes, prompts.

Delete this directory + clawteam/templates/gstack.toml + clawteam/plugins/gstack_sprint_plugin.py
and the rest of the codebase continues to run (D-07 delete invariant).
"""
```

**File 2 — `clawteam/templates/gstack/schemas/__init__.py`:** Barrel re-exports.

```python
"""Six pydantic evidence schemas for gstack 7-phase artifacts.

Registered into Phase 2's EvidenceSchemaRegistry by GstackSprintPlugin.contribute_evidence_schemas
(03-07-PLAN). Each schema's ``artifact_type: Literal[...]`` becomes the discriminator key.
"""
from clawteam.templates.gstack.schemas.design_doc import DesignDoc
from clawteam.templates.gstack.schemas.plan_doc import PlanDoc
from clawteam.templates.gstack.schemas.test_report import TestReport
from clawteam.templates.gstack.schemas.review_report import ReviewReport
from clawteam.templates.gstack.schemas.ship_notes import ShipNotes
from clawteam.templates.gstack.schemas.retro import Retro

__all__ = ["DesignDoc", "PlanDoc", "TestReport", "ReviewReport", "ShipNotes", "Retro"]
```

(Imports for files not yet created in this task will fail until Tasks 2-3 land. The barrel must be authored ALL AT ONCE in this task; the missing modules cause an `ImportError` at collection. **Resolution:** in Task 1, write the barrel with ONLY `DesignDoc` and `PlanDoc` imports + `__all__`. Tasks 2-3 will append their lines. Acceptance criterion below tests partial barrel after Task 1.)

Revised barrel for Task 1 ONLY (Tasks 2-3 will extend):

```python
"""Six pydantic evidence schemas for gstack 7-phase artifacts."""
from clawteam.templates.gstack.schemas.design_doc import DesignDoc
from clawteam.templates.gstack.schemas.plan_doc import PlanDoc

__all__ = ["DesignDoc", "PlanDoc"]
```

**File 3 — `clawteam/templates/gstack/schemas/design_doc.py`:** Copy RESEARCH.md verbatim:

```python
"""DesignDoc — Think-phase artifact written by pm + ceo collaboratively (D-04 phase 1)."""
from typing import Literal
from pydantic import BaseModel, Field


class DesignDoc(BaseModel):
    """Think-phase artifact. Written by pm + ceo collaboratively.

    Required ## headings (validated by Phase 2 D-03 layer 2):
      ## problem
      ## users
      ## constraints
      ## rationale
      ## pm-verdict   (one of: proceed | reframe | kill)
    """
    artifact_type: Literal["design-doc"]
    problem_statement: str = Field(..., min_length=120)
    users: str = Field(..., min_length=50)
    constraints: str = Field(..., min_length=50)
    rationale: str = Field(..., min_length=120)
    pm_verdict: Literal["proceed", "reframe", "kill"]
    forcing_questions_addressed: list[int] = Field(..., min_length=6, max_length=6)
    sprint_id: str
    created_at: str
```

**File 4 — `clawteam/templates/gstack/schemas/plan_doc.py`:** Per RESEARCH.md sketch line 305 ("task list + dependencies + estimates"):

```python
"""PlanDoc — Plan-phase artifact written by eng-mgr (per /plan-eng-review)."""
from typing import Literal
from pydantic import BaseModel, Field


class PlanTask(BaseModel):
    """One actionable task in the Plan-phase plan-doc."""
    task_id: str = Field(..., min_length=3)
    description: str = Field(..., min_length=20)
    owner_role: str = Field(..., min_length=2)
    depends_on: list[str] = Field(default_factory=list)
    estimated_context_pct: int = Field(..., ge=1, le=100)


class PlanDoc(BaseModel):
    """Plan-phase artifact. Written by eng-mgr after pm/ceo Think-phase verdict."""
    artifact_type: Literal["plan-doc"]
    architecture_lock: str = Field(..., min_length=120)
    tasks: list[PlanTask] = Field(..., min_length=1)
    edge_cases: list[str] = Field(..., min_length=3)
    test_plan: str = Field(..., min_length=80)
    plan_owner: str = Field(..., min_length=2)
    sprint_id: str
    created_at: str
```

**Files 5-8 — fixture markdown files.** Each uses YAML frontmatter + body. Pattern from `tests/fixtures/qa/answer_freeform.md` (frontmatter + body separator `---`).

`tests/fixtures/gstack_artifacts/design-doc-valid.md`:

```markdown
---
artifact_type: design-doc
problem_statement: "Founders bypass office-hours by skipping the 6 forcing questions and ship features that fail to retain because the why-now and the dumbest-version-3-day questions never get asked."
users: "Solo founders running ClawTeam who launch the gstack template for the first time."
constraints: "Must port verbatim upstream gstack rubric. Must not break existing 6 templates. Must ship within Phase 3 context budget."
rationale: "Without verbatim porting we lose the rubric content that makes office-hours valuable; without grep-tests we cannot prove the port is faithful; without per-persona envelopes the personas drift to generic Claude after sprint 4."
pm_verdict: proceed
forcing_questions_addressed: [1, 2, 3, 4, 5, 6]
sprint_id: sprint-001
created_at: 2026-04-20T12:00:00Z
---

# Design Doc body intentionally minimal — schema validates frontmatter, not body content.
```

`tests/fixtures/gstack_artifacts/design-doc-stub-tbd.md`:

```markdown
---
artifact_type: design-doc
problem_statement: TBD
users: TBD
constraints: TBD
rationale: TBD
pm_verdict: maybe
forcing_questions_addressed: [1]
sprint_id: ""
created_at: ""
---

# Stub. MUST FAIL DesignDoc validation (multiple Pitfall 8 violations).
```

`tests/fixtures/gstack_artifacts/plan-doc-valid.md`:

```markdown
---
artifact_type: plan-doc
architecture_lock: "Reuse Phase 2 EvidenceSchemaRegistry; no new abstraction. Reuse Phase 1 PhaseRegistry. Reuse Phase 0 TemplateDef pydantic loader. Wire 11-agent gstack template through existing spawn registry."
tasks:
  - task_id: t1
    description: "Author gstack.toml with 11 agents and ceo as leader."
    owner_role: pm
    depends_on: []
    estimated_context_pct: 15
  - task_id: t2
    description: "Implement six pydantic schemas for the 7-phase artifact types."
    owner_role: engineer
    depends_on: [t1]
    estimated_context_pct: 25
edge_cases:
  - "Existing 6 templates must continue to spawn unchanged"
  - "Plugin must not load for non-gstack templates"
  - "Path traversal in role names rejected by validate_identifier"
test_plan: "pytest tests/test_gstack_template.py + tests/test_evidence_schemas.py + tests/test_template_regression_matrix.py — all green before Phase 3 ships."
plan_owner: eng-mgr
sprint_id: sprint-001
created_at: 2026-04-20T13:00:00Z
---

# Plan-Doc body.
```

`tests/fixtures/gstack_artifacts/plan-doc-stub-tbd.md`:

```markdown
---
artifact_type: plan-doc
architecture_lock: TBD
tasks: []
edge_cases: []
test_plan: ""
plan_owner: ""
sprint_id: ""
created_at: ""
---

# Stub. MUST FAIL PlanDoc validation (empty tasks, short architecture_lock, etc.).
```

**File 9 — extend `tests/test_evidence_schemas.py`:** Append a new test class (do NOT replace existing tests). Use yaml frontmatter parsing via Phase 2's `parse_frontmatter` helper:

```python
# Append to tests/test_evidence_schemas.py — DO NOT remove existing tests.

from pathlib import Path
from pydantic import ValidationError
from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc
from clawteam.team.envelope import parse_frontmatter

GSTACK_FIXTURES = Path(__file__).parent / "fixtures" / "gstack_artifacts"


def _load_fixture_meta(name: str) -> dict:
    raw = (GSTACK_FIXTURES / name).read_text(encoding="utf-8")
    meta, _body = parse_frontmatter(raw)
    return meta


class TestDesignDocSchema:
    def test_valid_fixture_round_trips(self) -> None:
        doc = DesignDoc(**_load_fixture_meta("design-doc-valid.md"))
        assert doc.artifact_type == "design-doc"
        assert doc.pm_verdict == "proceed"
        assert len(doc.forcing_questions_addressed) == 6

    def test_stub_fixture_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DesignDoc(**_load_fixture_meta("design-doc-stub-tbd.md"))

    def test_short_problem_statement_rejected(self) -> None:
        meta = _load_fixture_meta("design-doc-valid.md")
        meta["problem_statement"] = "too short"
        with pytest.raises(ValidationError) as exc_info:
            DesignDoc(**meta)
        assert "problem_statement" in str(exc_info.value)

    def test_invalid_pm_verdict_rejected(self) -> None:
        meta = _load_fixture_meta("design-doc-valid.md")
        meta["pm_verdict"] = "maybe"
        with pytest.raises(ValidationError):
            DesignDoc(**meta)

    def test_short_forcing_questions_rejected(self) -> None:
        meta = _load_fixture_meta("design-doc-valid.md")
        meta["forcing_questions_addressed"] = [1, 2, 3]
        with pytest.raises(ValidationError):
            DesignDoc(**meta)


class TestPlanDocSchema:
    def test_valid_fixture_round_trips(self) -> None:
        doc = PlanDoc(**_load_fixture_meta("plan-doc-valid.md"))
        assert doc.artifact_type == "plan-doc"
        assert len(doc.tasks) >= 1
        assert doc.plan_owner == "eng-mgr"

    def test_stub_fixture_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PlanDoc(**_load_fixture_meta("plan-doc-stub-tbd.md"))


class TestGstackBarrelExports:
    def test_design_doc_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import DesignDoc as D
        assert D is DesignDoc

    def test_plan_doc_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import PlanDoc as P
        assert P is PlanDoc
```

**Atomic-commit discipline (D-01):** Single commit `feat(03-03): add DesignDoc + PlanDoc gstack evidence schemas with stub-defeating constraints`.
  </action>
  <verify>
    <automated>pytest tests/test_evidence_schemas.py -k 'TestDesignDocSchema or TestPlanDocSchema or TestGstackBarrelExports' -x</automated>
  </verify>
  <acceptance_criteria>
    - `test -d clawteam/templates/gstack/schemas` exits 0
    - `python -c "from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc; assert DesignDoc.model_fields['artifact_type'].annotation.__args__ == ('design-doc',)"` exits 0
    - `python -c "from clawteam.templates.gstack.schemas.design_doc import DesignDoc; from pydantic import ValidationError; import pytest; \\\ntry: DesignDoc(artifact_type='design-doc', problem_statement='x'*119, users='y'*50, constraints='z'*50, rationale='w'*120, pm_verdict='proceed', forcing_questions_addressed=[1,2,3,4,5,6], sprint_id='s', created_at='c'); print('FAIL')\nexcept ValidationError: print('OK')" | grep -q OK` exits 0
    - `pytest tests/test_evidence_schemas.py -k 'TestDesignDocSchema or TestPlanDocSchema or TestGstackBarrelExports' -x` exits 0 (≥7 new tests pass)
    - `pytest tests/ -x` exits 0 (suite stays green; Phase 2 tests unaffected)
    - `ls tests/fixtures/gstack_artifacts/*.md | wc -l` outputs at least `4` (design-doc + plan-doc valid+stub pairs)
  </acceptance_criteria>
  <done>gstack package + schemas package + DesignDoc + PlanDoc + 4 fixtures + barrel re-exports + 7 round-trip/rejection tests all green; suite remains green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add TestReport + ReviewReport schemas + 4 fixtures</name>
  <files>clawteam/templates/gstack/schemas/__init__.py, clawteam/templates/gstack/schemas/test_report.py, clawteam/templates/gstack/schemas/review_report.py, tests/fixtures/gstack_artifacts/test-report-valid.md, tests/fixtures/gstack_artifacts/test-report-stub-tbd.md, tests/fixtures/gstack_artifacts/review-report-valid.md, tests/fixtures/gstack_artifacts/review-report-stub-tbd.md, tests/test_evidence_schemas.py</files>
  <read_first>
    - clawteam/harness/evidence_gate.py (lines 16-21 — confirm test_command + deploy_url field requirements for post-check dispatch)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 305-309 — per-schema sketch for TestReport + ReviewReport; line 384-386 — Pitfall 9 SHA-PIN-DEFERRED rationale for review_sha field)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (line 305-309 — per-schema field shape table)
    - clawteam/templates/gstack/schemas/__init__.py (Task 1's partial barrel — extend by appending lines)
    - tests/test_evidence_schemas.py (Task 1's appended TestDesignDocSchema — append TestTestReportSchema + TestReviewReportSchema after it)
  </read_first>
  <behavior>
    - Test 1: `TestReport` instantiates with valid `test_command` (e.g., `"pytest tests/ -x"`) + passed/failed counts + output_excerpt; assert `artifact_type == "test-report"`.
    - Test 2: `TestReport` rejects empty `test_command` (EvidenceGate post-check requires it).
    - Test 3: `TestReport` rejects `output_excerpt` shorter than 30 chars (stub-grade).
    - Test 4: `ReviewReport` instantiates with valid `review_sha` (≥7 hex chars), `verdict` Literal, `hypothesis_traces`; assert `artifact_type == "review-report"`.
    - Test 5: `ReviewReport` rejects `review_sha="abc"` (< 7 chars; SHA-PIN-DEFERRED requirement).
    - Test 6: `ReviewReport` rejects `verdict="ship-it-anyway"` (Literal mismatch — must be one of approved/rejected/needs-revision).
    - Test 7: Both schemas importable from barrel after Task 2 lands.
  </behavior>
  <action>
**File 1 — `clawteam/templates/gstack/schemas/test_report.py`:**

```python
"""TestReport — Test-phase artifact (per /qa rubric)."""
from typing import Literal
from pydantic import BaseModel, Field


class TestReport(BaseModel):
    """Test-phase artifact. Written by qa after Build-phase code lands.

    The ``test_command`` field is required because Phase 2's EvidenceGate
    post-check dispatches against it (verified at evidence_gate.py:16-18).
    """
    artifact_type: Literal["test-report"]
    test_command: str = Field(..., min_length=5)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    output_excerpt: str = Field(..., min_length=30)
    qa_mode: Literal["qa", "qa-only"] = "qa"
    sprint_id: str
    created_at: str
```

**File 2 — `clawteam/templates/gstack/schemas/review_report.py`:**

```python
"""ReviewReport — Review-phase artifact (per /review + /investigate)."""
from typing import Literal
from pydantic import BaseModel, Field


class ReviewReport(BaseModel):
    """Review-phase artifact. Written by reviewer (aggregating parallel reviewers in Phase 4).

    The ``review_sha`` field encodes the Pitfall 9 SHA-PIN-DEFERRED meta-instruction:
    reviewer records the HEAD SHA at review start; if HEAD moved mid-review, mark
    verdict='superseded' and stop. Real SmartReviewRouter SHA-pinning ships in Phase 4.
    """
    artifact_type: Literal["review-report"]
    review_sha: str = Field(..., min_length=7, pattern=r"^[0-9a-f]+$")
    verdict: Literal["approved", "rejected", "needs-revision", "superseded"]
    hypothesis_traces: list[str] = Field(default_factory=list)
    findings: list[str] = Field(..., min_length=1)
    reviewer_persona: str = Field(..., min_length=2)
    sprint_id: str
    created_at: str
```

**File 3 — extend `clawteam/templates/gstack/schemas/__init__.py`** (append, do not replace):

```python
"""Six pydantic evidence schemas for gstack 7-phase artifacts."""
from clawteam.templates.gstack.schemas.design_doc import DesignDoc
from clawteam.templates.gstack.schemas.plan_doc import PlanDoc
from clawteam.templates.gstack.schemas.test_report import TestReport
from clawteam.templates.gstack.schemas.review_report import ReviewReport

__all__ = ["DesignDoc", "PlanDoc", "TestReport", "ReviewReport"]
```

**Files 4-7 — fixture markdown files:**

`test-report-valid.md`:

```markdown
---
artifact_type: test-report
test_command: "pytest tests/test_gstack_role_prompts.py -x"
passed: 12
failed: 0
output_excerpt: "12 passed in 0.43s — all SKILL-01..SKILL-08 golden tests green; D-14 budget gate: max=3712B avg=2890B."
qa_mode: qa
sprint_id: sprint-001
created_at: 2026-04-20T14:00:00Z
---

# Test Report body.
```

`test-report-stub-tbd.md`:

```markdown
---
artifact_type: test-report
test_command: ""
passed: 0
failed: 0
output_excerpt: TBD
qa_mode: qa
sprint_id: ""
created_at: ""
---

# Stub. MUST FAIL.
```

`review-report-valid.md`:

```markdown
---
artifact_type: review-report
review_sha: "abc1234567890def1234567890abcdef12345678"
verdict: approved
hypothesis_traces:
  - "Hypothesized envelope drift after sprint 4; tested via fixture replay; confirmed structured envelope holds."
findings:
  - "All 11 per-persona envelopes round-trip correctly"
  - "D-14 budget gate enforced (max 3712B / avg 2890B)"
reviewer_persona: reviewer
sprint_id: sprint-001
created_at: 2026-04-20T15:00:00Z
---

# Review Report body.
```

`review-report-stub-tbd.md`:

```markdown
---
artifact_type: review-report
review_sha: "xyz"
verdict: ship-it-anyway
hypothesis_traces: []
findings: []
reviewer_persona: ""
sprint_id: ""
created_at: ""
---

# Stub. MUST FAIL (short SHA, non-hex SHA, invalid verdict, empty findings).
```

**File 8 — extend `tests/test_evidence_schemas.py`** (append after Task 1's classes):

```python
class TestTestReportSchema:
    def test_valid_fixture_round_trips(self) -> None:
        doc = TestReport(**_load_fixture_meta("test-report-valid.md"))
        assert doc.artifact_type == "test-report"
        assert doc.test_command.startswith("pytest")
        assert doc.passed >= 0

    def test_stub_fixture_rejected(self) -> None:
        with pytest.raises(ValidationError):
            TestReport(**_load_fixture_meta("test-report-stub-tbd.md"))

    def test_empty_test_command_rejected(self) -> None:
        meta = _load_fixture_meta("test-report-valid.md")
        meta["test_command"] = ""
        with pytest.raises(ValidationError):
            TestReport(**meta)


class TestReviewReportSchema:
    def test_valid_fixture_round_trips(self) -> None:
        doc = ReviewReport(**_load_fixture_meta("review-report-valid.md"))
        assert doc.artifact_type == "review-report"
        assert len(doc.review_sha) >= 7
        assert doc.verdict in ("approved", "rejected", "needs-revision", "superseded")

    def test_stub_fixture_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReviewReport(**_load_fixture_meta("review-report-stub-tbd.md"))

    def test_short_review_sha_rejected(self) -> None:
        meta = _load_fixture_meta("review-report-valid.md")
        meta["review_sha"] = "abc"
        with pytest.raises(ValidationError):
            ReviewReport(**meta)

    def test_non_hex_review_sha_rejected(self) -> None:
        meta = _load_fixture_meta("review-report-valid.md")
        meta["review_sha"] = "notahexsha!"
        with pytest.raises(ValidationError):
            ReviewReport(**meta)

    def test_invalid_verdict_rejected(self) -> None:
        meta = _load_fixture_meta("review-report-valid.md")
        meta["verdict"] = "ship-it-anyway"
        with pytest.raises(ValidationError):
            ReviewReport(**meta)
```

Add a barrel-import test:

```python
class TestGstackBarrelExportsTask2:
    def test_test_report_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import TestReport as T
        assert T is TestReport

    def test_review_report_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import ReviewReport as R
        assert R is ReviewReport
```

**Atomic-commit discipline (D-01):** Single commit `feat(03-03): add TestReport + ReviewReport schemas with SHA-pin + post-check constraints`.
  </action>
  <verify>
    <automated>pytest tests/test_evidence_schemas.py -k 'TestTestReportSchema or TestReviewReportSchema or TestGstackBarrelExportsTask2' -x</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from clawteam.templates.gstack.schemas import TestReport, ReviewReport; assert TestReport.model_fields['artifact_type'].annotation.__args__ == ('test-report',); assert ReviewReport.model_fields['review_sha'].metadata"` exits 0
    - `pytest tests/test_evidence_schemas.py -k 'TestReport or ReviewReport or BarrelExportsTask2' -x` exits 0 (≥9 new tests)
    - `pytest tests/ -x` exits 0
    - `ls tests/fixtures/gstack_artifacts/test-report-*.md tests/fixtures/gstack_artifacts/review-report-*.md | wc -l` outputs `4`
  </acceptance_criteria>
  <done>TestReport + ReviewReport schemas + 4 fixtures + 9 round-trip/rejection tests + barrel updated; suite green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Add ShipNotes + Retro schemas + 4 fixtures + barrel completion</name>
  <files>clawteam/templates/gstack/schemas/__init__.py, clawteam/templates/gstack/schemas/ship_notes.py, clawteam/templates/gstack/schemas/retro.py, tests/fixtures/gstack_artifacts/ship-notes-valid.md, tests/fixtures/gstack_artifacts/ship-notes-stub-tbd.md, tests/fixtures/gstack_artifacts/retro-valid.md, tests/fixtures/gstack_artifacts/retro-stub-tbd.md, tests/test_evidence_schemas.py</files>
  <read_first>
    - clawteam/harness/evidence_gate.py (lines 19-21 — confirm deploy_url is the field for HEAD-probe post-check dispatch)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 305-309 — per-schema sketch for ShipNotes + Retro; lines 87-92 — D-09 Retro placeholder shape with personas attribution)
    - clawteam/templates/gstack/schemas/__init__.py (Task 2's partial barrel — extend to all 6 schemas + finalize __all__)
    - tests/test_evidence_schemas.py (Tasks 1-2's classes — append TestShipNotesSchema + TestRetroSchema)
  </read_first>
  <behavior>
    - Test 1: `ShipNotes` instantiates with valid `deploy_url` + `ship_step` Literal; assert `artifact_type == "ship-notes"`.
    - Test 2: `ShipNotes` accepts `deploy_url="<pending>"` (D-02 stub permitted); rejects empty string.
    - Test 3: `ShipNotes` rejects `ship_step="random"` (Literal mismatch).
    - Test 4: `Retro` instantiates with `personas` (list of 2+ persona names), what_worked/what_failed/key_lessons; assert `artifact_type == "retro"`.
    - Test 5: `Retro` rejects empty `personas` list.
    - Test 6: `Retro` rejects `key_lessons` of length < 1.
    - Test 7: All 6 schemas importable from barrel after Task 3 lands.
  </behavior>
  <action>
**File 1 — `clawteam/templates/gstack/schemas/ship_notes.py`:**

```python
"""ShipNotes — Ship-phase artifact (per /ship + /land-and-deploy; runtime tools land in Phase 5)."""
from typing import Literal
from pydantic import BaseModel, Field


class ShipNotes(BaseModel):
    """Ship-phase artifact. Written by shipper (D-02 stub for Phase 3; real /ship in Phase 5).

    The ``deploy_url`` field is required because Phase 2's EvidenceGate post-check
    dispatches against it (verified at evidence_gate.py:19-21). For Phase 3, shipper
    may write the literal value ``"<pending>"`` to satisfy structural requirements
    when manually coordinating with ceo (per D-02 Phase-5 tool-availability stub).
    """
    artifact_type: Literal["ship-notes"]
    deploy_url: str = Field(..., min_length=1)
    ship_step: Literal["sync", "test", "audit", "push", "pr", "merge", "deploy", "verify"]
    pr_url: str = ""
    notes: str = Field(..., min_length=20)
    sprint_id: str
    created_at: str
```

**File 2 — `clawteam/templates/gstack/schemas/retro.py`:**

```python
"""Retro — Reflect-phase artifact (per /retro)."""
from typing import Literal
from pydantic import BaseModel, Field


class Retro(BaseModel):
    """Reflect-phase artifact. Written by eng-mgr after Ship completes.

    The ``personas`` list captures per-persona attribution per D-09:
    each persona contributing to the sprint signs their section of the retro.
    Phase 6's TeamMemoryStore reads this to attribute /learn entries.
    """
    artifact_type: Literal["retro"]
    personas: list[str] = Field(..., min_length=2)
    what_worked: list[str] = Field(..., min_length=1)
    what_failed: list[str] = Field(default_factory=list)
    key_lessons: list[str] = Field(..., min_length=1)
    sprint_id: str
    created_at: str
```

**File 3 — finalize `clawteam/templates/gstack/schemas/__init__.py`:**

```python
"""Six pydantic evidence schemas for gstack 7-phase artifacts.

Registered into Phase 2's EvidenceSchemaRegistry by GstackSprintPlugin.contribute_evidence_schemas
(03-07-PLAN). Each schema's ``artifact_type: Literal[...]`` becomes the discriminator key.
"""
from clawteam.templates.gstack.schemas.design_doc import DesignDoc
from clawteam.templates.gstack.schemas.plan_doc import PlanDoc
from clawteam.templates.gstack.schemas.test_report import TestReport
from clawteam.templates.gstack.schemas.review_report import ReviewReport
from clawteam.templates.gstack.schemas.ship_notes import ShipNotes
from clawteam.templates.gstack.schemas.retro import Retro

__all__ = ["DesignDoc", "PlanDoc", "TestReport", "ReviewReport", "ShipNotes", "Retro"]
```

**Files 4-7 — fixture markdown files:**

`ship-notes-valid.md`:

```markdown
---
artifact_type: ship-notes
deploy_url: "https://staging.clawteam.dev/sprint-001"
ship_step: deploy
pr_url: "https://github.com/clawteam/clawteam/pull/42"
notes: "Phase 3 substrate ship: 11 agents + plugin + 6 schemas. Verified manually per D-02 Phase 5 stub."
sprint_id: sprint-001
created_at: 2026-04-20T16:00:00Z
---

# Ship Notes body.
```

`ship-notes-stub-tbd.md`:

```markdown
---
artifact_type: ship-notes
deploy_url: ""
ship_step: random
pr_url: ""
notes: TBD
sprint_id: ""
created_at: ""
---

# Stub. MUST FAIL (empty deploy_url, invalid ship_step, short notes).
```

`retro-valid.md`:

```markdown
---
artifact_type: retro
personas:
  - eng-mgr
  - ceo
  - engineer
  - reviewer
what_worked:
  - "Phase 3 substrate prep wave 0 prevented the 5 unverified assumptions from compounding"
  - "Six pydantic schemas + 12 fixtures caught 3 stub-grade artifact attempts during dogfood"
what_failed:
  - "designer.md ran 200 bytes over budget on first draft; tightened during refactor"
key_lessons:
  - "Run wc -c on every prompt as the prompt is being written, not after"
  - "Always include a stub-grade fixture per schema — it catches Pitfall 8 by construction"
sprint_id: sprint-001
created_at: 2026-04-20T17:00:00Z
---

# Retro body.
```

`retro-stub-tbd.md`:

```markdown
---
artifact_type: retro
personas: []
what_worked: []
what_failed: []
key_lessons: []
sprint_id: ""
created_at: ""
---

# Stub. MUST FAIL (empty personas, empty what_worked, empty key_lessons).
```

**File 8 — extend `tests/test_evidence_schemas.py`** (append after Tasks 1-2):

```python
class TestShipNotesSchema:
    def test_valid_fixture_round_trips(self) -> None:
        doc = ShipNotes(**_load_fixture_meta("ship-notes-valid.md"))
        assert doc.artifact_type == "ship-notes"
        assert doc.ship_step == "deploy"

    def test_stub_fixture_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ShipNotes(**_load_fixture_meta("ship-notes-stub-tbd.md"))

    def test_pending_deploy_url_accepted(self) -> None:
        # D-02: Phase 3 shipper may write '<pending>' as a real value
        meta = _load_fixture_meta("ship-notes-valid.md")
        meta["deploy_url"] = "<pending>"
        doc = ShipNotes(**meta)
        assert doc.deploy_url == "<pending>"

    def test_empty_deploy_url_rejected(self) -> None:
        meta = _load_fixture_meta("ship-notes-valid.md")
        meta["deploy_url"] = ""
        with pytest.raises(ValidationError):
            ShipNotes(**meta)

    def test_invalid_ship_step_rejected(self) -> None:
        meta = _load_fixture_meta("ship-notes-valid.md")
        meta["ship_step"] = "random"
        with pytest.raises(ValidationError):
            ShipNotes(**meta)


class TestRetroSchema:
    def test_valid_fixture_round_trips(self) -> None:
        doc = Retro(**_load_fixture_meta("retro-valid.md"))
        assert doc.artifact_type == "retro"
        assert len(doc.personas) >= 2
        assert len(doc.what_worked) >= 1
        assert len(doc.key_lessons) >= 1

    def test_stub_fixture_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Retro(**_load_fixture_meta("retro-stub-tbd.md"))

    def test_empty_personas_rejected(self) -> None:
        meta = _load_fixture_meta("retro-valid.md")
        meta["personas"] = []
        with pytest.raises(ValidationError):
            Retro(**meta)

    def test_empty_key_lessons_rejected(self) -> None:
        meta = _load_fixture_meta("retro-valid.md")
        meta["key_lessons"] = []
        with pytest.raises(ValidationError):
            Retro(**meta)


class TestGstackBarrelComplete:
    def test_all_six_schemas_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import (
            DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro,
        )
        # Confirm each is a pydantic BaseModel subclass with the right discriminator
        from pydantic import BaseModel
        for cls, expected_type in [
            (DesignDoc, "design-doc"),
            (PlanDoc, "plan-doc"),
            (TestReport, "test-report"),
            (ReviewReport, "review-report"),
            (ShipNotes, "ship-notes"),
            (Retro, "retro"),
        ]:
            assert issubclass(cls, BaseModel)
            assert cls.model_fields["artifact_type"].annotation.__args__ == (expected_type,)

    def test_all_six_in___all__(self) -> None:
        from clawteam.templates.gstack import schemas as s
        assert set(s.__all__) == {
            "DesignDoc", "PlanDoc", "TestReport", "ReviewReport", "ShipNotes", "Retro",
        }
```

**Atomic-commit discipline (D-01):** Single commit `feat(03-03): complete six gstack evidence schemas (ShipNotes + Retro) + finalize barrel`.
  </action>
  <verify>
    <automated>pytest tests/test_evidence_schemas.py -k 'TestShipNotesSchema or TestRetroSchema or TestGstackBarrelComplete' -x && python -c "from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro; print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `python -c "from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro; print('OK')" | grep -q OK` exits 0
    - `python -c "from clawteam.templates.gstack import schemas; assert set(schemas.__all__) == {'DesignDoc','PlanDoc','TestReport','ReviewReport','ShipNotes','Retro'}"` exits 0
    - `pytest tests/test_evidence_schemas.py -k 'ShipNotes or Retro or BarrelComplete' -x` exits 0 (≥10 new tests)
    - `pytest tests/test_evidence_schemas.py -x` exits 0 (full file green — Tasks 1+2+3 combined ≥26 new gstack tests + Phase 2 originals)
    - `pytest tests/ -x` exits 0 (no regressions)
    - `ls tests/fixtures/gstack_artifacts/*.md | wc -l` outputs `12` (6 valid + 6 stub-grade)
    - `ls clawteam/templates/gstack/schemas/*.py | wc -l` outputs at least `7` (6 schemas + __init__.py)
  </acceptance_criteria>
  <done>All 6 gstack evidence schemas exist + round-trip + reject stubs + are importable from barrel; 12 fixtures committed; suite green; ready for plugin registration in 03-07.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Fixture markdown content -> pydantic schema validation | Fixtures are repo-committed (trusted by review); pydantic schemas validate strictly via `min_length` + `Literal[...]`. No eval, no shell-out. |
| Future agent-written artifact -> pydantic schema | An agent at runtime writes a markdown artifact whose frontmatter is parsed by `parse_frontmatter` then validated by the gstack schema. Stub-grade content (TBD, short bodies) is rejected by construction. |
| `review_sha` field -> ReviewReport validation | An agent could supply a synthetic SHA. Phase 4's SmartReviewRouter cross-verifies SHA against actual git HEAD; Phase 3 only enforces shape (≥7 hex chars). Documented limitation. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-10 | Tampering | Stub-grade artifact passes EvidenceGate (Pitfall 8 manifest) | mitigate | `min_length` constraints on every prose field (DesignDoc.problem_statement ≥ 120, Retro.what_worked ≥ 1 item, etc.); `Literal[...]` on every enum field (pm_verdict, ship_step, verdict, qa_mode); `min_length=6, max_length=6` on DesignDoc.forcing_questions_addressed (exact arity). 6 stub-grade fixtures + 6 rejection tests prove construction defeats stub gaming. |
| T-03-11 | Spoofing | A non-reviewer agent writes a ReviewReport with a forged `reviewer_persona` value (e.g., engineer claiming to be reviewer) | accept (Phase 4 closes) | Phase 3 enforces only structural validity. Phase 4's cross-agent verification (per ROADMAP Phase 4 SC#6) cross-checks `reviewer_persona` against the actor that wrote the file (via Phase 2's identity envs CLAWTEAM_AGENT/CLAWTEAM_ROLE). Phase 3 documents this limit in the schema docstring. |
| T-03-12 | Tampering | Path traversal via crafted fixture file name (e.g., `../../etc/passwd`) when reading `_load_fixture_meta(name)` | mitigate | `_load_fixture_meta` uses a fixed `GSTACK_FIXTURES = Path(__file__).parent / "fixtures" / "gstack_artifacts"` base; concatenation via `/` operator does not normalize `..`. Add explicit guard: `assert ".." not in name` in helper. (Acceptance criterion below tests this.) |
| T-03-13 | Information Disclosure | `output_excerpt` field on TestReport could capture secrets from test runs (API keys in pytest output) | accept (Phase 0 already mitigates) | Phase 0 SAFETY rails (`_env()` helpers — QUALITY-15) already deny-filter secret-shaped values from logs. TestReport's `output_excerpt` is bounded by min_length=30 (no max), but agents are instructed via Phase 2 envelope contract to redact secrets. Phase 6 adds memory-write provenance with secret-scrub when /learn lands. |
| T-03-14 | Denial of Service | Pathologically large `findings` list on ReviewReport could OOM during validation | accept | pydantic v2 lazily validates list contents; no max length set per RESEARCH.md sketch. Realistic agent output is < 50 items per artifact. If observed in practice, add `max_length=200` constraint as a follow-up. Documented in schema docstring as a known unbounded list. |

</threat_model>

<verification>
- All 6 gstack pydantic schemas exist + are importable from barrel: `python -c "from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro"` exits 0
- Each schema's `artifact_type` is a `Literal[<name>]`: model_fields inspection passes
- 6 valid fixtures round-trip cleanly: TestXxxSchema.test_valid_fixture_round_trips passes for all 6
- 6 stub-grade fixtures are rejected (Pitfall 8 mitigation): TestXxxSchema.test_stub_fixture_rejected passes for all 6
- Stub-defeating constraints enforced: short prose, invalid Literals, wrong arity, non-hex SHA all raise ValidationError
- Existing Phase 2 test_evidence_schemas.py tests unaffected: `pytest tests/test_evidence_schemas.py -x` green
- Full suite green: `pytest tests/ -x` exits 0
- Path safety: `_load_fixture_meta('../etc/passwd')` either raises or stays under fixtures/ (acceptance test)
- D-07 delete invariant preserved: `clawteam/templates/gstack/schemas/` lives entirely under the gstack-scoped tree
</verification>

<success_criteria>
- 6 schemas (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro) defined as pydantic v2 BaseModel subclasses with `artifact_type: Literal[...]` discriminators
- `min_length` + `Literal` constraints prevent Pitfall 8 stub gaming (verified by 6 stub-grade fixtures failing validation)
- 12 fixtures committed under `tests/fixtures/gstack_artifacts/` (6 valid + 6 stub-grade)
- Barrel re-export at `clawteam.templates.gstack.schemas` exposes all 6 + finalizes `__all__`
- ≥26 new tests added to `tests/test_evidence_schemas.py` (round-trip + rejection + barrel)
- Phase 2 EvidenceSchemaRegistry untouched (registration is the plugin's job in 03-07)
- Phase 0 BC matrix continues to pass (no regression to existing schemas or tests)
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-03-SUMMARY.md` covering:
- Six schema files (file:line of each artifact_type Literal)
- Fixture inventory (12 files, valid + stub split)
- Stub-defeating constraint catalog (which constraint catches which stub class)
- Test count delta in test_evidence_schemas.py
- Path-safety hardening notes for `_load_fixture_meta`
- Confirmation that 03-07 (plugin) can `from clawteam.templates.gstack.schemas import ...` in one statement
</output>
</content>
</invoke>