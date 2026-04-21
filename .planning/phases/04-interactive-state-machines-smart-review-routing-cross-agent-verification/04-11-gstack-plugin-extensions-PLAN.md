---
phase: 04
plan: 11
type: execute
wave: 3
depends_on: [03, 04, 05, 06]
files_modified:
  - clawteam/plugins/gstack_sprint_plugin.py
  - clawteam/templates/gstack/verifiers/__init__.py
  - clawteam/templates/gstack/verifiers/test_report_matches_diff.py
  - clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py
  - tests/test_gstack_plugin.py
  - tests/test_cross_agent_verifiers.py
autonomous: true
requirements: [SPRINT-03, SPRINT-04, SPRINT-05, QUALITY-13]
must_haves:
  truths:
    - "GstackSprintPlugin.contribute_review_routers returns [GstackReviewRouter(rules)] with rules from template.review.rules."
    - "GstackSprintPlugin.contribute_verification_pairs returns exactly 2 VerificationPair instances (qa↔engineer, reviewer↔designer)."
    - "GstackSprintPlugin.contribute_prompts extended: phase='review' AND role in {reviewer,designer,security,dx-lead} appends prompts/review/<role>.md to main prompt."
    - "GstackSprintPlugin.contribute_gates returns {'ship': [ShipApprovalGate()]} to enforce SPRINT-05."
    - "Two gstack verifier functions exist under clawteam/templates/gstack/verifiers/ and pass their unit tests."
    - "verify_test_report_matches_engineer_output returns (False, reason) when test_report references no file from engineer diff."
    - "verify_design_doc_covers_forcing_questions returns (False, reason) when design-doc lacks coverage of any of Q1..Q6."
  artifacts:
    - path: "clawteam/plugins/gstack_sprint_plugin.py"
      provides: "4 new hooks: contribute_review_routers, contribute_verification_pairs, contribute_gates, extended contribute_prompts"
      contains: "contribute_review_routers"
    - path: "clawteam/templates/gstack/verifiers/test_report_matches_diff.py"
      provides: "qa ↔ engineer verifier fn"
      contains: "def verify_test_report_matches_engineer_output"
    - path: "clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py"
      provides: "reviewer ↔ designer verifier fn"
      contains: "def verify_design_doc_covers_forcing_questions"
    - path: "tests/test_cross_agent_verifiers.py"
      provides: "Unit tests for both verifier fns"
      contains: "def test_qa_verifier_catches_mismatch"
    - path: "tests/test_gstack_plugin.py"
      provides: "Extended coverage for review_routers + verification_pairs + decorrelation prompts + ship gate contribution"
  key_links:
    - from: "GstackSprintPlugin.contribute_review_routers"
      to: "clawteam/harness/gstack_review_router.py::GstackReviewRouter"
      via: "Plugin loads template.review.rules and constructs router"
    - from: "GstackSprintPlugin.contribute_verification_pairs"
      to: "clawteam/harness/cross_agent_verification_gate.py::VerificationPair"
      via: "Returns 2 VerificationPair instances"
    - from: "GstackSprintPlugin.contribute_gates"
      to: "clawteam/harness/ship_approval_gate.py::ShipApprovalGate"
      via: "Returns {'ship': [ShipApprovalGate()]}"
    - from: "GstackSprintPlugin.contribute_prompts"
      to: "clawteam/templates/gstack/prompts/review/<role>.md"
      via: "Append supplement when phase=='review' and role in _DECORRELATION_ROLES"
---

<objective>
Extend `GstackSprintPlugin` with four additional Phase-4 hooks (no new plugin file — single cohesive plugin per Phase 3 D-04):
1. `contribute_review_routers` returns `[GstackReviewRouter(rules)]` loaded from the template.
2. `contribute_verification_pairs` returns 2 `VerificationPair` instances for qa↔engineer and reviewer↔designer cross-verification.
3. `contribute_gates` returns `{"ship": [ShipApprovalGate()]}` so the Ship phase inherits the always-human gate.
4. Extend existing `contribute_prompts` so `phase="review"` + role in `{reviewer, designer, security, dx-lead}` appends `prompts/review/<role>.md`.

Also ship the two gstack-specific verifier functions under `clawteam/templates/gstack/verifiers/` with unit tests.

Purpose: This is the gstack-specific glue that activates Wave 1 substrate (router, gate, verification hook) via plugin contribution. Existing Phase 3 plugin hooks (contribute_phases, contribute_evidence_schemas, etc.) are not modified.

Output: 1 plugin extended + 3 new verifier files + 2 test files updated.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md

<interfaces>
From clawteam/plugins/gstack_sprint_plugin.py (existing Phase 3 plugin — lines 68-140):
```python
class GstackSprintPlugin(HarnessPlugin):
    name = "gstack-sprint"
    GSTACK_ROLES = ["pm", "ceo", "eng-mgr", "designer", "dx-lead", "engineer",
                    "reviewer", "qa", "security", "shipper", "sre"]
    PROMPTS_DIR = Path(__file__).parent.parent / "templates" / "gstack" / "prompts"

    def contribute_phases(self) -> list[str]: ...  # 7 gstack phases
    def contribute_evidence_schemas(self) -> dict[str, type]: ...  # 6 schemas
    def contribute_prompts(self, phase: str, role: str) -> str:
        # Currently resolves prompts/<role>.md with mtime cache; returns "" for non-gstack roles.
    def on_register(self, ctx): ...
```

From clawteam/harness/gstack_review_router.py (Plan 06):
```python
class GstackReviewRouter:
    def __init__(self, rules: list[ReviewRule]) -> None: ...
    def match(self, diff_paths, state) -> list[str]: ...
```

From clawteam/harness/cross_agent_verification_gate.py (Plan 03):
```python
class VerificationPair(BaseModel):
    phase: str; source_artifact: str; target_artifact: str; verifier_dotted_path: str
```

From clawteam/harness/ship_approval_gate.py (Plan 04):
```python
class ShipApprovalGate(InteractionGate): ...
```

From clawteam/templates/__init__.py (after Plan 06):
```python
def load_template(name: str) -> TemplateDef:
    # TemplateDef has .review: ReviewConfig with .rules: list[ReviewRule]
```

From clawteam/templates/gstack/schemas/test_report.py + build_report.py (Phase 3):
```python
class TestReport(ArtifactFrontmatterBase):
    artifact_type: Literal["test-report"]
    test_command: str
    # ... other fields
```

From clawteam/templates/gstack/schemas/design_doc.py (Phase 3):
```python
class DesignDoc(ArtifactFrontmatterBase):
    artifact_type: Literal["design-doc"]
    forcing_questions_addressed: list[int]  # min_length=6, max_length=6 per Phase 3
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Ship two gstack verifier functions + unit tests</name>
  <files>clawteam/templates/gstack/verifiers/__init__.py, clawteam/templates/gstack/verifiers/test_report_matches_diff.py, clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py, tests/test_cross_agent_verifiers.py</files>
  <read_first>
    - clawteam/templates/gstack/schemas/test_report.py (field shape for TestReport)
    - clawteam/templates/gstack/schemas/design_doc.py (forcing_questions_addressed field)
    - clawteam/templates/gstack/schemas/__init__.py (re-exports)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-RESEARCH.md (§Pattern 4 + §Per-Decision Map D-11 for verifier contracts)
  </read_first>
  <behavior>
    - Test 1 (test_qa_verifier_passes_when_test_references_diff_file): TestReport.test_command references a file listed in engineer diff summary → (True, "").
    - Test 2 (test_qa_verifier_fails_when_no_overlap): test_command references only files NOT in engineer diff → (False, reason).
    - Test 3 (test_qa_verifier_empty_diff_returns_false): engineer_diff_summary is empty → (False, reason).
    - Test 4 (test_design_doc_verifier_passes_when_6_questions_covered): forcing_questions_addressed == [1,2,3,4,5,6] → (True, "").
    - Test 5 (test_design_doc_verifier_fails_on_missing_question): forcing_questions_addressed == [1,2,3,4,5] → (False, reason identifies missing).
    - Test 6 (test_design_doc_verifier_fails_on_duplicate): forcing_questions_addressed == [1,1,2,3,4,5] (6 values but duplicates) → (False, reason identifies non-unique coverage).
    - Test 7 (test_design_doc_verifier_fails_when_out_of_range): forcing_questions_addressed contains 0 or 7 → (False, reason).
  </behavior>
  <action>
Create `clawteam/templates/gstack/verifiers/__init__.py`:
```python
"""Gstack cross-agent verifier functions (§04-CONTEXT D-11 — Plan 04-11).

Called by CrossAgentVerificationGate (Plan 04-03) with pydantic-validated
artifact models. Plugin-registered via GstackSprintPlugin.contribute_verification_pairs
(Plan 04-11) as (VerificationPair, verifier_callable) tuples resolved at plugin load.
"""
```

Create `clawteam/templates/gstack/verifiers/test_report_matches_diff.py`:

```python
"""qa ↔ engineer cross-verifier: test-report must reference engineer's diff files.

§04-CONTEXT D-11. Defeats Pitfall 8 gate-gaming extension: qa cannot write
a test-report citing pytest output on files engineer never touched.

Contract:
    (ok, reason) = verify_test_report_matches_engineer_output(test_report, engineer_output)

Where ``test_report`` is a TestReport pydantic instance and
``engineer_output`` is a pydantic instance with a ``files_changed`` / ``diff_summary``
attribute listing paths engineer modified or added. The verifier checks that
at least one file name from engineer's diff appears in test_report.test_command
or test_report's files_tested field (if present).

If Phase 3's build-report / engineer output schema differs, the verifier
falls back gracefully (accesses via getattr with sensible defaults).
"""

from __future__ import annotations

from typing import Any


def verify_test_report_matches_engineer_output(
    test_report: Any,
    engineer_output: Any,
) -> tuple[bool, str]:
    """Return (ok, reason)."""
    # Extract engineer diff file list (tolerant of schema variations).
    diff_files: list[str] = []
    for attr in ("files_changed", "diff_files", "files_added", "diff_summary"):
        val = getattr(engineer_output, attr, None)
        if val:
            if isinstance(val, list):
                diff_files.extend(str(p) for p in val)
            elif isinstance(val, str):
                diff_files.extend([line.strip() for line in val.splitlines() if line.strip()])

    if not diff_files:
        return False, (
            "cross-verify: engineer diff summary is empty; cannot confirm "
            "test-report references actual engineer changes"
        )

    # Extract test-report evidence (test_command + files_tested).
    test_command = str(getattr(test_report, "test_command", "") or "")
    files_tested = getattr(test_report, "files_tested", None) or []
    if not isinstance(files_tested, list):
        files_tested = []
    files_tested_str = [str(p) for p in files_tested]

    search_corpus = test_command + " " + " ".join(files_tested_str)

    # Any engineer diff file (or its basename) must appear in the corpus.
    for path in diff_files:
        basename = path.rsplit("/", 1)[-1]
        if path in search_corpus or basename in search_corpus:
            return True, ""

    return False, (
        f"cross-verify: test-report test_command ({test_command!r}) and "
        f"files_tested ({files_tested_str}) reference none of engineer's "
        f"{len(diff_files)} modified file(s): {diff_files[:5]}"
        f"{'...' if len(diff_files) > 5 else ''}"
    )
```

Create `clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py`:

```python
"""reviewer ↔ designer cross-verifier: design-doc covers all 6 /office-hours forcing Qs.

§04-CONTEXT D-11. Reviewer verifies designer's design-doc.md maps to all 6
pm/`/office-hours` forcing questions by presence check on question ids
(not prose matching). DesignDoc schema already enforces min_length=6/max_length=6
on forcing_questions_addressed (Phase 3 Plan 03-03); this verifier adds the
semantic "values are exactly [1..6]" check.

Contract:
    (ok, reason) = verify_design_doc_covers_forcing_questions(design_doc, office_hours_state)

Where ``design_doc`` is a DesignDoc pydantic instance and
``office_hours_state`` can be either an OfficeHoursState instance OR a
separate artifact (we use design_doc's forcing_questions_addressed list
directly; office_hours_state is passed for future extensions like
matching question wording). The verifier's current check is on design_doc
alone — it returns True iff forcing_questions_addressed == sorted({1,2,3,4,5,6}).
"""

from __future__ import annotations

from typing import Any


_EXPECTED_QUESTION_IDS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6})


def verify_design_doc_covers_forcing_questions(
    design_doc: Any,
    office_hours_state: Any,
) -> tuple[bool, str]:
    """Return (ok, reason)."""
    covered = getattr(design_doc, "forcing_questions_addressed", None)
    if covered is None:
        return False, (
            "cross-verify: design-doc frontmatter lacks forcing_questions_addressed field"
        )
    if not isinstance(covered, list):
        return False, (
            f"cross-verify: forcing_questions_addressed expected list, got {type(covered).__name__}"
        )

    covered_set = set()
    for v in covered:
        try:
            covered_set.add(int(v))
        except (ValueError, TypeError):
            return False, f"cross-verify: non-integer question id {v!r}"

    if len(covered) != len(covered_set):
        return False, (
            f"cross-verify: forcing_questions_addressed contains duplicates: {covered}"
        )

    if covered_set != _EXPECTED_QUESTION_IDS:
        missing = _EXPECTED_QUESTION_IDS - covered_set
        extra = covered_set - _EXPECTED_QUESTION_IDS
        parts = []
        if missing:
            parts.append(f"missing Q{sorted(missing)}")
        if extra:
            parts.append(f"out-of-range {sorted(extra)}")
        return False, (
            f"cross-verify: design-doc forcing_questions_addressed mismatch "
            f"expected [1..6]: {', '.join(parts)}"
        )

    return True, ""
```

Create `tests/test_cross_agent_verifiers.py`:

```python
"""Unit tests for gstack cross-agent verifier functions (Plan 04-11)."""

from __future__ import annotations

from types import SimpleNamespace

from clawteam.templates.gstack.verifiers.design_doc_covers_forcing_qs import (
    verify_design_doc_covers_forcing_questions,
)
from clawteam.templates.gstack.verifiers.test_report_matches_diff import (
    verify_test_report_matches_engineer_output,
)


# ── qa ↔ engineer verifier ────────────────────────────────────────────

def test_qa_verifier_passes_when_test_command_references_diff_file():
    test_report = SimpleNamespace(
        test_command="pytest tests/test_user.py::test_create -x",
        files_tested=["tests/test_user.py"],
    )
    engineer = SimpleNamespace(files_changed=["src/user.py", "tests/test_user.py"])
    ok, reason = verify_test_report_matches_engineer_output(test_report, engineer)
    assert ok is True
    assert reason == ""


def test_qa_verifier_passes_with_basename_match():
    test_report = SimpleNamespace(
        test_command="pytest -k test_user",
        files_tested=[],
    )
    engineer = SimpleNamespace(files_changed=["a/b/test_user.py"])
    # "test_user" basename appears in test_command
    ok, reason = verify_test_report_matches_engineer_output(test_report, engineer)
    assert ok is True


def test_qa_verifier_fails_when_no_overlap():
    test_report = SimpleNamespace(
        test_command="pytest tests/test_unrelated.py",
        files_tested=["tests/test_unrelated.py"],
    )
    engineer = SimpleNamespace(files_changed=["src/user.py", "src/account.py"])
    ok, reason = verify_test_report_matches_engineer_output(test_report, engineer)
    assert ok is False
    assert "references none" in reason


def test_qa_verifier_fails_when_engineer_diff_empty():
    test_report = SimpleNamespace(test_command="pytest", files_tested=[])
    engineer = SimpleNamespace(files_changed=[])
    ok, reason = verify_test_report_matches_engineer_output(test_report, engineer)
    assert ok is False
    assert "engineer diff summary is empty" in reason


def test_qa_verifier_tolerates_missing_attributes():
    """Schema variations: engineer_output with diff_summary string fallback."""
    test_report = SimpleNamespace(test_command="pytest src/u.py", files_tested=[])
    engineer = SimpleNamespace(diff_summary="src/u.py\nsrc/x.py")
    ok, reason = verify_test_report_matches_engineer_output(test_report, engineer)
    assert ok is True


# ── reviewer ↔ designer verifier ──────────────────────────────────────

def test_design_doc_verifier_passes_when_6_questions_covered():
    design = SimpleNamespace(forcing_questions_addressed=[1, 2, 3, 4, 5, 6])
    oh = SimpleNamespace()
    ok, reason = verify_design_doc_covers_forcing_questions(design, oh)
    assert ok is True
    assert reason == ""


def test_design_doc_verifier_fails_on_missing_question():
    design = SimpleNamespace(forcing_questions_addressed=[1, 2, 3, 4, 5])
    ok, reason = verify_design_doc_covers_forcing_questions(design, SimpleNamespace())
    assert ok is False
    assert "missing" in reason
    assert "6" in reason  # mentions Q6


def test_design_doc_verifier_fails_on_duplicate():
    design = SimpleNamespace(forcing_questions_addressed=[1, 1, 2, 3, 4, 5])
    ok, reason = verify_design_doc_covers_forcing_questions(design, SimpleNamespace())
    assert ok is False
    assert "duplicate" in reason


def test_design_doc_verifier_fails_on_out_of_range():
    design = SimpleNamespace(forcing_questions_addressed=[1, 2, 3, 4, 5, 7])
    ok, reason = verify_design_doc_covers_forcing_questions(design, SimpleNamespace())
    assert ok is False
    assert "out-of-range" in reason or "mismatch" in reason


def test_design_doc_verifier_fails_on_missing_field():
    design = SimpleNamespace()  # no attribute
    ok, reason = verify_design_doc_covers_forcing_questions(design, SimpleNamespace())
    assert ok is False
    assert "lacks forcing_questions_addressed" in reason


def test_design_doc_verifier_fails_on_wrong_type():
    design = SimpleNamespace(forcing_questions_addressed="1,2,3,4,5,6")
    ok, reason = verify_design_doc_covers_forcing_questions(design, SimpleNamespace())
    assert ok is False
    assert "expected list" in reason


def test_design_doc_verifier_handles_non_integer_gracefully():
    design = SimpleNamespace(forcing_questions_addressed=[1, 2, 3, 4, 5, "six"])
    ok, reason = verify_design_doc_covers_forcing_questions(design, SimpleNamespace())
    assert ok is False
    assert "non-integer" in reason
```
  </action>
  <verify>
    <automated>pytest tests/test_cross_agent_verifiers.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - ls clawteam/templates/gstack/verifiers/__init__.py + test_report_matches_diff.py + design_doc_covers_forcing_qs.py succeed
    - grep -q "def verify_test_report_matches_engineer_output" clawteam/templates/gstack/verifiers/test_report_matches_diff.py
    - grep -q "def verify_design_doc_covers_forcing_questions" clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py
    - pytest tests/test_cross_agent_verifiers.py -x -q exits 0 (12 tests)
  </acceptance_criteria>
  <done>Two verifier fns ship with comprehensive unit coverage; ready for plugin registration</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend GstackSprintPlugin with 4 new hooks + decorrelation prompt supplement</name>
  <files>clawteam/plugins/gstack_sprint_plugin.py, tests/test_gstack_plugin.py</files>
  <read_first>
    - clawteam/plugins/gstack_sprint_plugin.py (entire file, 334 LOC — understand existing _load_prompt cache + GSTACK_ROLES)
    - clawteam/harness/gstack_review_router.py (Plan 06)
    - clawteam/harness/cross_agent_verification_gate.py (Plan 03 — VerificationPair)
    - clawteam/harness/ship_approval_gate.py (Plan 04)
    - clawteam/templates/__init__.py (load_template after Plan 06)
    - tests/test_gstack_plugin.py (existing Phase 3 plugin tests — append new Phase 4 tests alongside)
  </read_first>
  <behavior>
    - Test 1 (test_contribute_review_routers_returns_gstack_router): plugin load; contribute_review_routers returns a 1-element list containing a GstackReviewRouter; router.match on fixture diff returns expected participants.
    - Test 2 (test_contribute_verification_pairs_returns_2_pairs): contribute_verification_pairs returns exactly 2 VerificationPair instances with expected phases (test, review).
    - Test 3 (test_contribute_gates_attaches_ship_approval_gate): contribute_gates returns {"ship": [<ShipApprovalGate>]}.
    - Test 4 (test_review_prompts_append_decorrelation_supplement): contribute_prompts(phase="review", role="designer") returns base designer.md + separator + review/designer.md content.
    - Test 5 (test_review_prompts_no_supplement_for_non_decorrelation_role): contribute_prompts(phase="review", role="pm") returns only the base pm.md (no supplement — pm is not a decorrelation role).
    - Test 6 (test_non_review_phase_no_supplement): contribute_prompts(phase="think", role="designer") returns only base designer.md.
    - Test 7 (test_decorrelation_supplement_missing_file_falls_back): If review/designer.md were missing, returns base alone (graceful degradation).
    - Test 8 (test_verifier_dotted_paths_resolve): PluginManager loads GstackSprintPlugin + verification pairs resolve to actual callables (integration test using the manager from Plan 05).
    - Test 9 (test_decorrelation_file_budget): Each review/<role>.md ≤ 2048 bytes per D-07 budget.
  </behavior>
  <action>
Edit `clawteam/plugins/gstack_sprint_plugin.py`:

a) Add module-level constants and imports at the top (after existing imports):

```python
_DECORRELATION_ROLES: frozenset[str] = frozenset({"reviewer", "designer", "security", "dx-lead"})
_REVIEW_PROMPTS_SUBDIR: str = "review"
```

b) Extend `contribute_prompts` to append decorrelation supplements. Modify the existing `contribute_prompts` method (around line 103). Replace the method body — preserve the existing mtime cache logic for base prompt, add supplement loading AFTER base is resolved.

Replace the existing `contribute_prompts` with:

```python
    def contribute_prompts(self, phase: str, role: str) -> str:
        """Resolve clawteam/templates/gstack/prompts/<role>.md for gstack roles.

        Phase 4 Plan 04-11 extension (§04-CONTEXT D-07): when phase == "review"
        AND role is a decorrelation role (reviewer/designer/security/dx-lead),
        ALSO reads clawteam/templates/gstack/prompts/review/<role>.md and
        appends it as a supplement. Separator header marks the review-phase
        decorrelation boundary.
        """
        if role not in GSTACK_ROLES:
            return ""
        if not _valid_role(role):
            return ""

        base = self._load_prompt_file(PROMPTS_DIR / f"{role}.md", cache_key=f"base:{role}")
        if not base:
            return ""

        # Phase 4 Plan 04-11: decorrelation supplement for review phase.
        if phase == "review" and role in _DECORRELATION_ROLES:
            supplement_path = PROMPTS_DIR / _REVIEW_PROMPTS_SUBDIR / f"{role}.md"
            supplement = self._load_prompt_file(supplement_path, cache_key=f"review:{role}")
            if supplement:
                return (
                    base
                    + "\n\n---\n\n<!-- PHASE 4 REVIEW DECORRELATION SUPPLEMENT -->\n\n"
                    + supplement
                )

        return base

    def _load_prompt_file(self, path: "Path", *, cache_key: str) -> str:
        """Read a prompt file with mtime-invalidated caching (generalizes the
        existing base-prompt cache to support review/<role>.md supplements).
        """
        if not path.is_file():
            return ""
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return ""
        cached = self._prompt_cache.get(cache_key)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        self._prompt_cache[cache_key] = (mtime, content)
        return content
```

c) Add four new hooks after `on_register`. Place them before any existing internal helpers (or at end of class — doesn't matter). Insertion:

```python
    # ── Phase 4 / Plan 04-11 hooks ────────────────────────────────────

    def contribute_review_routers(self):
        """Return a GstackReviewRouter loaded from the gstack template's rules.

        §04-CONTEXT D-06 / SPRINT-03. Template is loaded lazily so this method
        is safe to call at plugin registration time regardless of template-load
        ordering. If the gstack template fails to load (unusual), returns empty.
        """
        try:
            from clawteam.harness.gstack_review_router import GstackReviewRouter
            from clawteam.templates import load_template
            tmpl = load_template("gstack")
            rules = list(tmpl.review.rules or [])
            return [GstackReviewRouter(rules)]
        except Exception:
            return []

    def contribute_verification_pairs(self):
        """Return the 2 gstack cross-verification pairs (§04-CONTEXT D-11).

        Pair 1 — Test phase:   test-report.md  ↔ build-report.md  (qa verifies engineer)
        Pair 2 — Review phase: design-doc.md   ↔ office-hours     (reviewer verifies designer)

        Verifier fns are resolved from dotted paths at plugin-load time by
        PluginManager._instantiate_and_register (Plan 04-05).
        """
        from clawteam.harness.cross_agent_verification_gate import VerificationPair
        return [
            VerificationPair(
                phase="test",
                source_artifact="test-report.md",
                target_artifact="build-report.md",
                verifier_dotted_path=(
                    "clawteam.templates.gstack.verifiers.test_report_matches_diff."
                    "verify_test_report_matches_engineer_output"
                ),
            ),
            VerificationPair(
                phase="review",
                source_artifact="design-doc.md",
                target_artifact="office-hours-answers.md",
                verifier_dotted_path=(
                    "clawteam.templates.gstack.verifiers.design_doc_covers_forcing_qs."
                    "verify_design_doc_covers_forcing_questions"
                ),
            ),
        ]

    def contribute_gates(self):
        """Attach Phase 4 gates to phases (§04-CONTEXT D-13 — Plan 04-04 ShipApprovalGate).

        Extends the existing base-class default (empty dict). Returns a
        {phase -> [gates]} mapping; SprintConductor consumes via _build_gate_chain
        extension (or plugin manager wiring — see Plan 04-10 integration).
        """
        try:
            from clawteam.harness.ship_approval_gate import ShipApprovalGate
            return {"ship": [ShipApprovalGate()]}
        except Exception:
            return {}
```

d) Append **new tests** to `tests/test_gstack_plugin.py`:

```python
# ── Phase 4 Plan 11 — plugin extensions ─────────────────────────────

import pytest

from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin


def _fresh_plugin() -> GstackSprintPlugin:
    # Existing test helpers may provide HarnessContext; reuse if present.
    plugin = GstackSprintPlugin()
    # Minimal on_register call to initialize _ctx + _prompt_cache.
    from types import SimpleNamespace
    plugin.on_register(SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None)))
    return plugin


def test_contribute_review_routers_returns_gstack_router():
    from clawteam.harness.gstack_review_router import GstackReviewRouter
    plugin = _fresh_plugin()
    routers = plugin.contribute_review_routers()
    assert len(routers) == 1
    assert isinstance(routers[0], GstackReviewRouter)


def test_contribute_review_routers_router_loads_real_gstack_rules():
    plugin = _fresh_plugin()
    router = plugin.contribute_review_routers()[0]
    # Smoke: match a UI file pulls designer + reviewer floor.
    from types import SimpleNamespace
    state = SimpleNamespace(workspace_branch="", review_sha="")
    result = router.match(["src/components/Button.tsx"], state)
    assert "reviewer" in result
    assert "designer" in result


def test_contribute_verification_pairs_returns_2_pairs():
    plugin = _fresh_plugin()
    pairs = plugin.contribute_verification_pairs()
    assert len(pairs) == 2
    phases = sorted(p.phase for p in pairs)
    assert phases == ["review", "test"]


def test_contribute_verification_pairs_qa_engineer_pair():
    plugin = _fresh_plugin()
    pairs = plugin.contribute_verification_pairs()
    qa_pair = next(p for p in pairs if p.phase == "test")
    assert qa_pair.source_artifact == "test-report.md"
    assert qa_pair.target_artifact == "build-report.md"
    assert "verify_test_report_matches_engineer_output" in qa_pair.verifier_dotted_path


def test_contribute_verification_pairs_reviewer_designer_pair():
    plugin = _fresh_plugin()
    pairs = plugin.contribute_verification_pairs()
    rev_pair = next(p for p in pairs if p.phase == "review")
    assert rev_pair.source_artifact == "design-doc.md"
    assert "verify_design_doc_covers_forcing_questions" in rev_pair.verifier_dotted_path


def test_contribute_gates_attaches_ship_approval_gate():
    from clawteam.harness.ship_approval_gate import ShipApprovalGate
    plugin = _fresh_plugin()
    gates = plugin.contribute_gates()
    assert "ship" in gates
    assert any(isinstance(g, ShipApprovalGate) for g in gates["ship"])


def test_review_prompts_append_decorrelation_supplement():
    plugin = _fresh_plugin()
    supplemented = plugin.contribute_prompts(phase="review", role="designer")
    # Should contain both base + supplement markers.
    assert "rubric-first" in supplemented  # from review/designer.md
    # Should also contain base designer content (SIGNATURE trailer).
    assert "gstack-role:designer" in supplemented


def test_review_prompts_no_supplement_for_non_decorrelation_role():
    plugin = _fresh_plugin()
    result = plugin.contribute_prompts(phase="review", role="pm")
    # pm is not a decorrelation role — supplement not appended.
    assert "PHASE 4 REVIEW DECORRELATION SUPPLEMENT" not in result


def test_non_review_phase_no_supplement():
    plugin = _fresh_plugin()
    result = plugin.contribute_prompts(phase="think", role="designer")
    # Base only.
    assert "PHASE 4 REVIEW DECORRELATION SUPPLEMENT" not in result


def test_review_prompts_all_decorrelation_roles_have_supplements():
    plugin = _fresh_plugin()
    for role in ("reviewer", "designer", "security", "dx-lead"):
        r = plugin.contribute_prompts(phase="review", role=role)
        assert "PHASE 4 REVIEW DECORRELATION SUPPLEMENT" in r, (
            f"role={role} missing supplement"
        )


def test_decorrelation_file_budget_under_2kb():
    """D-07: each prompts/review/<role>.md ≤ 2048 bytes."""
    from pathlib import Path
    prompts_dir = Path("clawteam/templates/gstack/prompts/review")
    for role in ("reviewer", "designer", "security", "dx-lead"):
        size = (prompts_dir / f"{role}.md").stat().st_size
        assert size <= 2048, f"review/{role}.md is {size} bytes (budget 2048)"


def test_verifier_dotted_paths_importable():
    """Every VerificationPair.verifier_dotted_path resolves to a callable."""
    import importlib
    plugin = _fresh_plugin()
    for pair in plugin.contribute_verification_pairs():
        module_path, _, attr = pair.verifier_dotted_path.rpartition(".")
        module = importlib.import_module(module_path)
        verifier = getattr(module, attr, None)
        assert callable(verifier), f"{pair.verifier_dotted_path} not importable"
```

**Do NOT modify** existing Phase 3 contribute_phases / contribute_evidence_schemas / on_register / _on_phase_transition logic.
  </action>
  <verify>
    <automated>pytest tests/test_gstack_plugin.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "def contribute_review_routers" clawteam/plugins/gstack_sprint_plugin.py
    - grep -q "def contribute_verification_pairs" clawteam/plugins/gstack_sprint_plugin.py
    - grep -q "def contribute_gates" clawteam/plugins/gstack_sprint_plugin.py
    - grep -q "_DECORRELATION_ROLES" clawteam/plugins/gstack_sprint_plugin.py
    - grep -q "PHASE 4 REVIEW DECORRELATION SUPPLEMENT" clawteam/plugins/gstack_sprint_plugin.py
    - pytest tests/test_gstack_plugin.py -x -q exits 0 (all existing Phase 3 tests + 12 new Phase 4 tests)
    - pytest tests/test_gstack_template.py tests/test_orchestrator_phase_registry.py tests/test_plugins.py -x -q stays green
  </acceptance_criteria>
  <done>4 plugin hooks land; decorrelation supplement wiring + all existing Phase 3 tests still pass</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

Verifiers consume pydantic-validated artifacts; schemas already enforced in Plan 03/Plan 11 Task 1 verifier-level validation.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-35 | T (Tampering) | Verifier fn reads pydantic attributes via getattr | mitigate | getattr fallback to defaults; never raise on missing optional attrs |
| T-04-36 | I (Information disclosure) | Verifier reason string leaks file paths | accept | Paths are artifact content; already public |
| T-04-37 | E (Elevation of privilege) | Plugin's load_template("gstack") cross-template leak | mitigate | Template scope bounded by `template == "gstack"` guard pattern proven in Phase 3 (T-07-01 HIGH mitigation) |
</threat_model>

<verification>
- [ ] `pytest tests/test_gstack_plugin.py tests/test_cross_agent_verifiers.py -x -q` exits 0
- [ ] `pytest tests/test_gstack_template.py tests/test_orchestrator_phase_registry.py tests/test_plugins.py tests/test_cross_agent_verification_gate.py -x -q` stays green
- [ ] `python3 -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; p = GstackSprintPlugin(); from types import SimpleNamespace; p.on_register(SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None))); pairs = p.contribute_verification_pairs(); assert len(pairs) == 2"` exits 0
- [ ] All 4 decorrelation supplements ≤ 2048 bytes
</verification>

<success_criteria>
- [ ] GstackSprintPlugin exposes contribute_review_routers, contribute_verification_pairs, contribute_gates, extended contribute_prompts
- [ ] 2 verifier fns land + 12 verifier tests pass
- [ ] Decorrelation supplements appended only in Review phase for 4 personas
- [ ] All existing Phase 3 plugin tests unregressed
- [ ] Verifier dotted paths resolve at runtime
</success_criteria>

<output>
Create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-11-gstack-plugin-extensions-SUMMARY.md`.
</output>
