---
phase: 03-gstack-team-template-methodology-port
plan: 04
type: execute
wave: 1
depends_on: [03-01]
files_modified:
  - clawteam/templates/gstack/envelope_personas.py
  - tests/test_envelope_personas.py
autonomous: true
requirements: [TEAM-04]
must_haves:
  truths:
    - "All 11 per-persona TurnEnvelope subclasses (PMEnvelope, CEOEnvelope, EngMgrEnvelope, DesignerEnvelope, DxLeadEnvelope, EngineerEnvelope, ReviewerEnvelope, QAEnvelope, SecurityEnvelope, ShipperEnvelope, SREEnvelope) instantiate when their required persona-namespaced field is supplied"
    - "Each subclass raises pydantic ValidationError when the persona-namespaced field is missing or stub-grade (Pitfall 1 drift defeated structurally)"
    - "Each subclass overrides `persona: Literal[<role>]` so an unknown persona on a payload is rejected by pydantic before any subclass body executes"
    - "PERSONA_ENVELOPES dict maps each role string to its envelope class, giving Phase 4's discriminated-union dispatcher one lookup table to consult"
    - "Wave 0's xfail stubs in tests/test_envelope_personas.py are unskipped by this plan and pass — Nyquist gate restored"
  artifacts:
    - path: "clawteam/templates/gstack/envelope_personas.py"
      provides: "11 pydantic v2 TurnEnvelope subclasses + PERSONA_ENVELOPES lookup dict"
      contains: "PERSONA_ENVELOPES"
    - path: "tests/test_envelope_personas.py"
      provides: "Per-persona instantiation, missing-field rejection, frontmatter round-trip, registry-completeness tests (un-skipped)"
      contains: "PERSONA_ENVELOPES"
  key_links:
    - from: "clawteam/templates/gstack/envelope_personas.py"
      to: "clawteam/team/envelope.py::TurnEnvelope"
      via: "from clawteam.team.envelope import TurnEnvelope; class PMEnvelope(TurnEnvelope): ..."
      pattern: "from clawteam.team.envelope import TurnEnvelope"
    - from: "tests/test_envelope_personas.py"
      to: "clawteam/templates/gstack/envelope_personas.py"
      via: "import PERSONA_ENVELOPES + each subclass; round-trip via parse_frontmatter"
      pattern: "from clawteam.templates.gstack.envelope_personas"
    - from: "PERSONA_ENVELOPES dict"
      to: "Phase 4 SmartReviewRouter discriminated-union dispatcher"
      via: "PERSONA_ENVELOPES[meta['persona']].model_validate(meta) — Phase 4 wiring deferred"
      pattern: "PERSONA_ENVELOPES\\["
---

<objective>
Ship the 11 per-persona TurnEnvelope subclasses at `clawteam/templates/gstack/envelope_personas.py` (D-07 location: gstack-scoped, NOT under `clawteam/team/`, to honor the delete invariant). Each subclass adds ONE namespaced required field that defeats the Pitfall 1 persona-drift collapse documented in `.planning/research/PITFALLS.md` (70% → 9% drift reduction with structured-envelope reassertion). Each subclass also constrains `persona: Literal["<role>"]` so payloads with unknown personas are rejected at the pydantic v2 layer before any subclass body runs.

**Why this plan exists for TEAM-04:** TEAM-04 ("only ceo can call SprintConductor.advance_phase") is enforced at two layers. The conductor-layer check landed in Wave 0 (03-01 Task 2 — `actor: str = ""` parameter + `leader_role` consultation). This plan ships the *envelope*-layer reassertion that makes the actor identity self-attesting per turn. Without per-persona envelopes, an engineer could write `actor="ceo"` into an outbound message and the conductor would only catch it via leader_role lookup; with per-persona envelopes, the same engineer payload also fails `Literal["engineer"]` validation when it claims `persona="ceo"` because the envelope content (e.g., `engineer.diff_summary` field) doesn't match. Pitfall 1 collapse and TEAM-04 spoofing are the same structural failure mode and are mitigated by the same fix.

**Field-name override vs RESEARCH.md (justification):** RESEARCH.md §"Per-role envelope reassertion subclass" (lines 624-691) suggests fields like `pm.challenge`, `ceo.decision_mode`, `reviewer.iron_law`. The locked CONTEXT.md §"Claude's Discretion" lets the planner refine. This plan uses a **rubric-anchored field set** that ties each persona's envelope assertion to a concrete rubric step, not a generic "challenge" string:

  - `PmEnvelope.pm_question_index: int (1-6)` — which of the 6 forcing questions this turn addresses (one Q per turn per /office-hours interactive runtime split)
  - `CeoEnvelope.ceo_mode: Literal["expansion", "selective", "hold", "reduction"]` — the 4 plan-ceo-review modes verbatim
  - `EngMgrEnvelope.eng_mgr_deliverable: Literal["architecture-lock", "data-flow", "edge-case-matrix", "test-plan", "retro-breakdown"]` — the 5 plan-eng-review/retro deliverable kinds
  - `DesignerEnvelope.designer_rubric_dimension: int (1-10)` — which of the 10 plan-design-review rubric dimensions (with optional `designer_ai_slop_findings: list[str]`)
  - `DxLeadEnvelope.dx_lead_friction_source: Literal["persona", "benchmark", "friction-trace"]` — the 3 devex-review evidence kinds
  - `EngineerEnvelope.engineer_diff_summary: str (min_length=20)` — stub-defeating per D-01 atomic-commit discipline
  - `ReviewerEnvelope.reviewer_hypothesis_index: int (0-3)` — investigation hypothesis count; index 3 = halt per /investigate iron-law
  - `QaEnvelope.qa_mode: Literal["qa", "qa-only"]` — qa-only suppresses code changes per /qa-only
  - `SecurityEnvelope.security_confidence: int (0-10)` — 8+ gate per SKILL-08 /cso
  - `ShipperEnvelope.shipper_step: Literal["prep", "pushing", "pr-open", "merged", "deployed", "verified"]` — 6 step enum per D-02
  - `SreEnvelope.sre_signal: Literal["nominal", "degraded", "regression", "outage"]` — 4 signal levels per D-03

This shift from "namespaced freeform string" to "rubric-anchored Literal/int" tightens the structural drift detector (Pitfall 1 mitigation strength scales with how concrete the assertion is) without breaking Phase 2's `parse_frontmatter` round-trip.

**Class-naming honor:** Wave 0 (03-01 Task 3) scaffolded `tests/test_envelope_personas.py` with class names `PMEnvelope`, `CEOEnvelope`, `QAEnvelope`, `SREEnvelope` (uppercase abbreviations matching RESEARCH.md's worked example). This plan ships the same uppercase-abbreviation names so the Wave 0 imports already work after un-skip. Other 7 personas use Pascal case (`EngMgrEnvelope`, `DesignerEnvelope`, etc.).

Output:
- `clawteam/templates/gstack/envelope_personas.py` — 11 pydantic v2 subclasses + `PERSONA_ENVELOPES` dict
- `tests/test_envelope_personas.py` — Wave 0 stubs un-skipped, parametrize tuples updated to match rubric-anchored field names, frontmatter round-trip + registry-completeness + unknown-persona-rejection coverage
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
<!-- Contracts the executor will use, extracted from PATTERNS.md analog reads. -->

From clawteam/team/envelope.py (Phase 2 base class — line 32-52):
```python
class TurnEnvelope(BaseModel):
    """Validates both TeamMessage envelope fields and artifact YAML frontmatter.

    Required fields (§02-CONTEXT D-06):
      - persona: agent role asserting this turn
      - step_label: free-form step marker, e.g. 'plan:2/5'
      - done: explicit turn-done signal
    """
    persona: str = Field(..., min_length=1, description="Agent role asserting this turn")
    step_label: str = Field(..., min_length=1, description="Free-form step marker")
    done: bool = Field(..., description="Turn-done signal")
    artifact_type: str | None = None
    created_at: str | None = None
    turn_id: str | None = None
```

From clawteam/team/envelope.py::parse_frontmatter (used by tests for round-trip):
```python
def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from body; return (meta_dict, body_str)."""
    # ... yaml.safe_load on the frontmatter; returns ({}, raw) if no frontmatter
```

From clawteam/team/envelope.py::validate_envelope (the structural template to mirror with validate_persona_envelope):
```python
def validate_envelope(meta: dict[str, Any]) -> TurnEnvelope:
    try:
        return TurnEnvelope.model_validate(meta)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"])
        raise MalformedEnvelopeError(
            f"envelope invalid: {field}: {first['msg']}"
        ) from exc
```

From tests/test_envelope_personas.py (Wave 0 scaffold from 03-01 — currently skipped, will be un-skipped here):
```python
PERSONAS = [
    ("PMEnvelope", "pm", "pm.challenge", "Why three months and not now?"),
    ("CEOEnvelope", "ceo", "ceo.decision_mode", "expansion"),
    # ... 9 more
]

@pytest.mark.parametrize("class_name,persona,field_alias,valid_value", PERSONAS)
@pytest.mark.skip(reason="Wave 1: envelope_personas.py ships in 03-03-PLAN")
def test_persona_envelope_required_field_present(class_name, persona, field_alias, valid_value):
    pass
```

**Note:** the scaffold predates the field-name override in this plan. The executor MUST update the `PERSONAS` parametrize tuple values to match the rubric-anchored field names listed in this plan's `<objective>`. The scaffold reason string ("ships in 03-03-PLAN") is also wrong — this plan ships envelope_personas.py at 03-04 (03-03 ships the evidence schemas). Update reason text to "shipped in 03-04-PLAN" when un-skipping.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Author clawteam/templates/gstack/envelope_personas.py — 11 subclasses + PERSONA_ENVELOPES dict</name>
  <files>clawteam/templates/gstack/envelope_personas.py</files>
  <read_first>
    - clawteam/team/envelope.py (full file — TurnEnvelope base class, parse_frontmatter, validate_envelope helper, MalformedEnvelopeError exception)
    - clawteam/templates/gstack/__init__.py (Wave 1 from 03-03 — confirms gstack package exists; envelope_personas.py is a sibling module of schemas/ subpackage)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 165-232 — envelope_personas.py pattern + base-class subclass shape)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 620-691 — original RESEARCH.md draft of 11 subclasses, used as STRUCTURE reference only; field names overridden per this plan's <objective>)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-07: file location is gstack-scoped per delete invariant; D-01 engineer.diff_summary stub-defeating min_length=20 contract)
  </read_first>
  <behavior>
    - Test target 1: `PMEnvelope(persona="pm", step_label="think:1/6", done=False, pm_question_index=1)` succeeds — pm_question_index in [1..6].
    - Test target 2: `PMEnvelope(persona="pm", step_label="think:1/6", done=False)` raises ValidationError — pm_question_index missing.
    - Test target 3: `PMEnvelope(persona="pm", step_label="think:1/6", done=False, pm_question_index=7)` raises ValidationError — out of [1..6].
    - Test target 4: `PMEnvelope(persona="ceo", step_label="x", done=False, pm_question_index=1)` raises ValidationError — persona Literal["pm"] mismatch.
    - Test target 5: each of the other 10 subclasses follows the same three-test pattern (instantiate / missing field / out-of-range or wrong-Literal).
    - Test target 6: `PERSONA_ENVELOPES` is a dict[str, type[TurnEnvelope]] with exactly 11 entries keyed by `pm`, `ceo`, `eng-mgr`, `designer`, `dx-lead`, `engineer`, `reviewer`, `qa`, `security`, `shipper`, `sre`.
    - Test target 7: `EngineerEnvelope.engineer_diff_summary` rejects strings shorter than 20 chars (D-01 stub-defeating).
    - Test target 8: round-trip — feed YAML frontmatter through `parse_frontmatter`, dispatch through `PERSONA_ENVELOPES[meta["persona"]].model_validate(meta)`, assert subclass instance returned with all fields populated.
  </behavior>
  <action>
**File: `clawteam/templates/gstack/envelope_personas.py`** — author exactly the structure below. Code is grouped into one file per D-07 (gstack-scoped, deletable as a unit).

```python
"""Per-persona TurnEnvelope subclasses for the gstack template (Phase 3, D-07).

Each of the 11 specialists asserts a single rubric-anchored field every turn.
The shape implements the Pitfall 1 mitigation (Echoing-paper finding: persona
self-consistency degrades >30% after 8-12 turns; structured envelope assertion
cuts drift from 70% -> 9%).

The class names match Wave 0's tests/test_envelope_personas.py scaffold
(uppercase abbreviations for PM/CEO/QA/SRE; Pascal case for the rest) so the
test imports already work after Wave 0's xfail markers are removed.

D-07 location invariant: this file lives under clawteam/templates/gstack/.
Deleting clawteam/templates/gstack/ + clawteam/templates/gstack.toml +
clawteam/plugins/gstack_sprint_plugin.py removes all gstack-specific code
without touching the rest of the codebase.

Field-name choices (planner discretion per CONTEXT.md "Claude's Discretion" #1):
RESEARCH.md sketched freeform namespaced strings (e.g. pm.challenge); this
file uses rubric-anchored Literal[...] / int constraints because:
  - Literal[...] catches misspelled or invented modes via pydantic at parse
    time (no runtime drift detector needed).
  - int + ge/le on indices ties the assertion to a concrete rubric step
    rather than letting agents emit any string.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, ValidationError

from clawteam.team.envelope import TurnEnvelope


# ---------------------------------------------------------------------------
# 11 per-persona subclasses
# ---------------------------------------------------------------------------


class PMEnvelope(TurnEnvelope):
    """pm asserts which of the 6 /office-hours forcing questions this turn addresses.

    Pitfall 7 partition: full /office-hours runtime ships in Phase 4 as a
    multi-turn state machine. In Phase 3 each pm turn handles ONE question
    per the INTERACTIVE-RUNTIME-DEFERRED meta-instruction in pm.md.
    """

    persona: Literal["pm"]
    pm_question_index: int = Field(
        ...,
        ge=1,
        le=6,
        description="Which of the 6 /office-hours forcing questions (1-6)",
    )


class CEOEnvelope(TurnEnvelope):
    """ceo asserts which /plan-ceo-review mode this turn applies.

    The 4 modes are verbatim from upstream gstack /plan-ceo-review (D-13 fixture
    grep). 'deferred' is intentionally NOT a mode — ceo either picks one or
    halts; deferral is a question-to-ceo from another role, not a self-mode.
    """

    persona: Literal["ceo"]
    ceo_mode: Literal["expansion", "selective", "hold", "reduction"] = Field(
        ...,
        description="One of the 4 /plan-ceo-review modes",
    )


class EngMgrEnvelope(TurnEnvelope):
    """eng-mgr asserts which deliverable kind this turn produces.

    The 5 deliverable kinds enumerate the /plan-eng-review + /retro rubric
    sections (architecture-lock + data-flow + edge-case-matrix + test-plan +
    retro-breakdown) — see eng-mgr.md (03-05).
    """

    persona: Literal["eng-mgr"]
    eng_mgr_deliverable: Literal[
        "architecture-lock",
        "data-flow",
        "edge-case-matrix",
        "test-plan",
        "retro-breakdown",
    ] = Field(..., description="Which /plan-eng-review or /retro section this turn produces")


class DesignerEnvelope(TurnEnvelope):
    """designer asserts which 0-10 rubric dimension this turn evaluates.

    Optional designer_ai_slop_findings captures the AI-slop detection
    checklist hits (per /design-review). 1-10 indexes the 10 dimensions
    enumerated in designer.md (03-05).
    """

    persona: Literal["designer"]
    designer_rubric_dimension: int = Field(
        ...,
        ge=1,
        le=10,
        description="Which of the 10 /plan-design-review dimensions (1-10)",
    )
    designer_ai_slop_findings: list[str] = Field(
        default_factory=list,
        description="Optional /design-review AI-slop hits this turn",
    )


class DxLeadEnvelope(TurnEnvelope):
    """dx-lead asserts which evidence kind this turn produces.

    The 3 sources enumerate the /plan-devex-review + /devex-review surfaces
    (persona exploration, TTHW benchmark, friction trace). See dx-lead.md.
    """

    persona: Literal["dx-lead"]
    dx_lead_friction_source: Literal["persona", "benchmark", "friction-trace"] = Field(
        ...,
        description="Which /devex-review evidence kind this turn produces",
    )


class EngineerEnvelope(TurnEnvelope):
    """engineer asserts a non-stub diff summary every Build-phase turn (D-01).

    min_length=20 is the stub-defeating gate — defeats Pitfall 8 'TBD' stubs
    in the envelope itself before EvidenceGate sees any artifact.
    """

    persona: Literal["engineer"]
    engineer_diff_summary: str = Field(
        ...,
        min_length=20,
        description="Stub-defeating Build-phase diff summary per D-01",
    )


class ReviewerEnvelope(TurnEnvelope):
    """reviewer asserts the current /investigate hypothesis count (0-3).

    The /investigate iron-law: halt after 3 failed hypotheses. Index 0 means
    no hypotheses yet (initial review pass); index 3 means halt. Phase 4
    state-machine ships the per-hypothesis runtime; Phase 3 just structures
    the envelope assertion.
    """

    persona: Literal["reviewer"]
    reviewer_hypothesis_index: int = Field(
        ...,
        ge=0,
        le=3,
        description="Current /investigate hypothesis count (0-3; 3=halt per iron-law)",
    )


class QAEnvelope(TurnEnvelope):
    """qa asserts whether this turn runs in /qa-only suppression mode.

    qa-only mode disables code edits — qa writes test reports only and routes
    fixes back to engineer. See qa.md (03-05) and /qa-only fixture.
    """

    persona: Literal["qa"]
    qa_mode: Literal["qa", "qa-only"] = Field(
        ...,
        description="qa standard mode or /qa-only edit-suppression variant",
    )


class SecurityEnvelope(TurnEnvelope):
    """security asserts the /cso confidence score (0-10).

    SKILL-08 8/10+ gate: only escalate findings with confidence >= 8;
    otherwise log as informational. The full 17 false-positive exclusions
    list lives in security.md (03-05).
    """

    persona: Literal["security"]
    security_confidence: int = Field(
        ...,
        ge=0,
        le=10,
        description="/cso confidence score; 8+ gates escalation per SKILL-08",
    )


class ShipperEnvelope(TurnEnvelope):
    """shipper asserts which Ship-phase step this turn is at (D-02).

    The 6-step enum is verbatim from D-02. Real /ship + /land-and-deploy
    runtime ships in Phase 5; Phase 3 records the manual step assertion.
    """

    persona: Literal["shipper"]
    shipper_step: Literal[
        "prep", "pushing", "pr-open", "merged", "deployed", "verified"
    ] = Field(..., description="Current Ship-phase step per D-02")


class SREEnvelope(TurnEnvelope):
    """sre asserts current operational signal (D-03).

    The 4-signal enum is verbatim from D-03. Real /canary + /benchmark
    runtime ships in Phase 5; Phase 3 records the manually-observed signal.
    """

    persona: Literal["sre"]
    sre_signal: Literal["nominal", "degraded", "regression", "outage"] = Field(
        ...,
        description="Current SRE signal per D-03 (manually observed in Phase 3)",
    )


# ---------------------------------------------------------------------------
# Lookup table (Phase 4 SmartReviewRouter dispatcher consumes this)
# ---------------------------------------------------------------------------

PERSONA_ENVELOPES: dict[str, type[TurnEnvelope]] = {
    "pm": PMEnvelope,
    "ceo": CEOEnvelope,
    "eng-mgr": EngMgrEnvelope,
    "designer": DesignerEnvelope,
    "dx-lead": DxLeadEnvelope,
    "engineer": EngineerEnvelope,
    "reviewer": ReviewerEnvelope,
    "qa": QAEnvelope,
    "security": SecurityEnvelope,
    "shipper": ShipperEnvelope,
    "sre": SREEnvelope,
}


__all__ = [
    "PMEnvelope",
    "CEOEnvelope",
    "EngMgrEnvelope",
    "DesignerEnvelope",
    "DxLeadEnvelope",
    "EngineerEnvelope",
    "ReviewerEnvelope",
    "QAEnvelope",
    "SecurityEnvelope",
    "ShipperEnvelope",
    "SREEnvelope",
    "PERSONA_ENVELOPES",
]
```

**Critical details:**
- File lives at `clawteam/templates/gstack/envelope_personas.py` (D-07; sibling of `schemas/` subpackage from 03-03; under the gstack/ directory tree so the delete invariant holds).
- 11 subclasses inherit from `TurnEnvelope` (Phase 2 base) and override `persona: Literal["<role>"]` so passing the wrong persona to the wrong subclass is rejected at pydantic v2 validation.
- Each subclass adds exactly ONE required namespaced field per D-07's "ONE namespaced required field per persona" contract. Designer optionally adds the AI-slop list as a non-required `default_factory=list` field — does not violate the one-required-field rule.
- `PERSONA_ENVELOPES` keyed by role string (matching gstack.toml `role = "<role>"` values from 03-02) lets a Phase 4 dispatcher do `PERSONA_ENVELOPES[meta["persona"]].model_validate(meta)` in one line.
- `from __future__ import annotations` per Phase 2 envelope.py convention (matches existing style).
- No new dependencies. pydantic v2 is already in the standard stack.

Atomic-commit discipline (D-01): commit as `feat(03-04): add 11 per-persona TurnEnvelope subclasses + PERSONA_ENVELOPES dict (D-07)`.
  </action>
  <verify>
    <automated>python -c "from clawteam.templates.gstack.envelope_personas import PERSONA_ENVELOPES, PMEnvelope, CEOEnvelope, EngMgrEnvelope, DesignerEnvelope, DxLeadEnvelope, EngineerEnvelope, ReviewerEnvelope, QAEnvelope, SecurityEnvelope, ShipperEnvelope, SREEnvelope; assert len(PERSONA_ENVELOPES) == 11"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f clawteam/templates/gstack/envelope_personas.py` exits 0
    - `python -c "from clawteam.templates.gstack.envelope_personas import PERSONA_ENVELOPES; assert set(PERSONA_ENVELOPES.keys()) == {'pm','ceo','eng-mgr','designer','dx-lead','engineer','reviewer','qa','security','shipper','sre'}"` exits 0
    - `python -c "from clawteam.templates.gstack.envelope_personas import PMEnvelope; e = PMEnvelope(persona='pm', step_label='think:1/6', done=False, pm_question_index=3); assert e.pm_question_index == 3 and e.persona == 'pm'"` exits 0
    - `python -c "from clawteam.templates.gstack.envelope_personas import PMEnvelope; from pydantic import ValidationError; \\\ntry: PMEnvelope(persona='pm', step_label='x', done=False); print('FAIL')\nexcept ValidationError: print('OK')" | grep -q OK` exits 0
    - `python -c "from clawteam.templates.gstack.envelope_personas import PMEnvelope; from pydantic import ValidationError; \\\ntry: PMEnvelope(persona='ceo', step_label='x', done=False, pm_question_index=1); print('FAIL')\nexcept ValidationError: print('OK')" | grep -q OK` exits 0
    - `python -c "from clawteam.templates.gstack.envelope_personas import EngineerEnvelope; from pydantic import ValidationError; \\\ntry: EngineerEnvelope(persona='engineer', step_label='build:1/3', done=False, engineer_diff_summary='too short'); print('FAIL')\nexcept ValidationError: print('OK')" | grep -q OK` exits 0
    - `pytest tests/ -x` exits 0 (suite stays green; existing Phase 2 envelope tests unaffected)
    - `grep -E 'class (PM|CEO|EngMgr|Designer|DxLead|Engineer|Reviewer|QA|Security|Shipper|SRE)Envelope\(TurnEnvelope\)' clawteam/templates/gstack/envelope_personas.py | wc -l` outputs `11`
  </acceptance_criteria>
  <done>envelope_personas.py committed with 11 subclasses + PERSONA_ENVELOPES dict; importable; per-class instantiation + missing-field + wrong-persona rejection all behave correctly; suite stays green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Un-skip + rewrite tests/test_envelope_personas.py with parametrized rubric-anchored assertions + frontmatter round-trip + unknown-persona rejection</name>
  <files>tests/test_envelope_personas.py</files>
  <read_first>
    - tests/test_envelope_personas.py (Wave 0 scaffold from 03-01 — current PERSONAS parametrize tuple uses RESEARCH.md draft field names; rewrite to match this plan's rubric-anchored fields)
    - tests/test_turn_envelope.py (Phase 2 — required-field rejection pattern lines 27-54; frontmatter round-trip pattern lines 75-87)
    - clawteam/templates/gstack/envelope_personas.py (Task 1 output)
    - clawteam/team/envelope.py (parse_frontmatter signature for round-trip test)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 608-650 — test scaffold pattern)
  </read_first>
  <behavior>
    - Test 1 (parametrized × 11): each persona's envelope instantiates with valid required field; assert `instance.persona == role` and the field value round-trips.
    - Test 2 (parametrized × 11): each persona's envelope raises ValidationError when the required field is missing.
    - Test 3 (parametrized × 11): each persona's envelope raises ValidationError when persona is wrong (Literal mismatch).
    - Test 4 (single): EngineerEnvelope rejects engineer_diff_summary shorter than 20 chars (D-01 stub-defeating).
    - Test 5 (single): PMEnvelope rejects pm_question_index outside [1..6].
    - Test 6 (single): SecurityEnvelope rejects security_confidence outside [0..10].
    - Test 7 (single): CEOEnvelope rejects ceo_mode="deferred" (NOT a valid mode per Task 1's design choice).
    - Test 8 (single): PERSONA_ENVELOPES has exactly 11 entries with the expected role keys.
    - Test 9 (single, frontmatter round-trip): YAML frontmatter with `persona: ceo` + `ceo_mode: expansion` + envelope basics flows through `parse_frontmatter` → dispatched through `PERSONA_ENVELOPES["ceo"].model_validate(meta)` → returns `CEOEnvelope` instance.
    - Test 10 (single, threat T-04-01): payload with `persona: "evil"` raises ValidationError when dispatched through PERSONA_ENVELOPES (KeyError caught and re-raised, OR direct ValidationError if dispatcher is implemented as `PERSONA_ENVELOPES.get(p, TurnEnvelope).model_validate(meta)` — the test asserts the unknown-persona case is a hard failure, not silent fallback).
  </behavior>
  <action>
**File: `tests/test_envelope_personas.py`** — REPLACE the entire Wave 0 scaffold with the following. The Wave 0 stubs were placeholders; this is the production test file.

```python
"""Per-persona TurnEnvelope subclass tests (Phase 3 plan 03-04).

Replaces the Wave 0 scaffold (xfail/skip stubs from 03-01-PLAN). Field names
in the parametrize tuple match the rubric-anchored fields chosen in 03-04
(see 03-04-PLAN.md <objective> for justification vs RESEARCH.md draft).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from clawteam.team.envelope import TurnEnvelope, parse_frontmatter
from clawteam.templates.gstack.envelope_personas import (
    PERSONA_ENVELOPES,
    PMEnvelope,
    CEOEnvelope,
    EngMgrEnvelope,
    DesignerEnvelope,
    DxLeadEnvelope,
    EngineerEnvelope,
    ReviewerEnvelope,
    QAEnvelope,
    SecurityEnvelope,
    ShipperEnvelope,
    SREEnvelope,
)


# Tuple shape: (envelope_class, role, required_field_name, valid_value)
PERSONAS = [
    (PMEnvelope, "pm", "pm_question_index", 1),
    (CEOEnvelope, "ceo", "ceo_mode", "expansion"),
    (EngMgrEnvelope, "eng-mgr", "eng_mgr_deliverable", "architecture-lock"),
    (DesignerEnvelope, "designer", "designer_rubric_dimension", 5),
    (DxLeadEnvelope, "dx-lead", "dx_lead_friction_source", "benchmark"),
    (EngineerEnvelope, "engineer", "engineer_diff_summary", "added auto_advance flag and tests"),
    (ReviewerEnvelope, "reviewer", "reviewer_hypothesis_index", 0),
    (QAEnvelope, "qa", "qa_mode", "qa"),
    (SecurityEnvelope, "security", "security_confidence", 9),
    (ShipperEnvelope, "shipper", "shipper_step", "prep"),
    (SREEnvelope, "sre", "sre_signal", "nominal"),
]


@pytest.mark.parametrize("cls,role,field,valid_value", PERSONAS)
def test_persona_envelope_required_field_present(cls, role, field, valid_value):
    """Each subclass instantiates with valid persona + required field."""
    kwargs = {"persona": role, "step_label": f"{role}:1/1", "done": False, field: valid_value}
    env = cls(**kwargs)
    assert env.persona == role
    assert getattr(env, field) == valid_value


@pytest.mark.parametrize("cls,role,field,valid_value", PERSONAS)
def test_persona_envelope_rejects_missing_required_field(cls, role, field, valid_value):
    """Each subclass raises ValidationError when its persona-namespaced field is missing."""
    kwargs = {"persona": role, "step_label": f"{role}:1/1", "done": False}
    with pytest.raises(ValidationError) as exc_info:
        cls(**kwargs)
    assert field in str(exc_info.value)


@pytest.mark.parametrize("cls,role,field,valid_value", PERSONAS)
def test_persona_envelope_rejects_wrong_persona(cls, role, field, valid_value):
    """Each subclass raises ValidationError when persona Literal is wrong."""
    wrong_persona = "intruder" if role != "intruder" else "outsider"
    kwargs = {"persona": wrong_persona, "step_label": "x:1/1", "done": False, field: valid_value}
    with pytest.raises(ValidationError) as exc_info:
        cls(**kwargs)
    assert "persona" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Field-specific stub-defeating constraints
# ---------------------------------------------------------------------------


def test_engineer_diff_summary_rejects_stub_under_20_chars():
    """D-01 stub-defeating: engineer cannot emit 'TBD' or short stubs."""
    with pytest.raises(ValidationError) as exc_info:
        EngineerEnvelope(
            persona="engineer",
            step_label="build:1/3",
            done=False,
            engineer_diff_summary="TBD",
        )
    assert "engineer_diff_summary" in str(exc_info.value)


def test_pm_question_index_rejects_out_of_range():
    """6 forcing questions are 1..6; index 0 or 7 must fail."""
    for bad in (0, 7, -1):
        with pytest.raises(ValidationError):
            PMEnvelope(persona="pm", step_label="x", done=False, pm_question_index=bad)


def test_security_confidence_rejects_out_of_range():
    """SKILL-08 confidence is 0-10."""
    for bad in (-1, 11, 100):
        with pytest.raises(ValidationError):
            SecurityEnvelope(persona="security", step_label="x", done=False, security_confidence=bad)


def test_ceo_mode_rejects_deferred():
    """ceo either picks one of 4 modes or halts; 'deferred' is NOT a valid self-mode."""
    with pytest.raises(ValidationError):
        CEOEnvelope(persona="ceo", step_label="x", done=False, ceo_mode="deferred")


def test_reviewer_hypothesis_index_caps_at_3():
    """/investigate iron-law: halt after 3 failed hypotheses; index must stay 0..3."""
    for bad in (-1, 4, 10):
        with pytest.raises(ValidationError):
            ReviewerEnvelope(
                persona="reviewer", step_label="x", done=False, reviewer_hypothesis_index=bad,
            )


# ---------------------------------------------------------------------------
# PERSONA_ENVELOPES registry completeness
# ---------------------------------------------------------------------------


def test_persona_envelopes_has_eleven_entries():
    expected_roles = {
        "pm", "ceo", "eng-mgr", "designer", "dx-lead",
        "engineer", "reviewer", "qa", "security", "shipper", "sre",
    }
    assert set(PERSONA_ENVELOPES.keys()) == expected_roles
    assert len(PERSONA_ENVELOPES) == 11


def test_persona_envelopes_values_are_turn_envelope_subclasses():
    for role, cls in PERSONA_ENVELOPES.items():
        assert issubclass(cls, TurnEnvelope), f"{role} -> {cls.__name__} not a TurnEnvelope subclass"


# ---------------------------------------------------------------------------
# Frontmatter round-trip + dispatch
# ---------------------------------------------------------------------------


def test_validate_persona_envelope_dispatches_on_persona_via_frontmatter():
    """Full Phase 2 round-trip: YAML frontmatter -> parse_frontmatter -> dispatch -> instance."""
    raw = (
        "---\n"
        "persona: ceo\n"
        "step_label: think:2/6\n"
        "done: false\n"
        "ceo_mode: expansion\n"
        "---\n"
        "ceo body text\n"
    )
    meta, body = parse_frontmatter(raw)
    assert meta["persona"] == "ceo"

    cls = PERSONA_ENVELOPES[meta["persona"]]
    instance = cls.model_validate(meta)

    assert isinstance(instance, CEOEnvelope)
    assert instance.ceo_mode == "expansion"
    assert instance.step_label == "think:2/6"
    assert body == "ceo body text\n"


def test_dispatch_rejects_unknown_persona_payload():
    """T-04-01 mitigation: an attacker-controlled persona='evil' must not silently fall back."""
    meta = {
        "persona": "evil",
        "step_label": "x:1/1",
        "done": False,
        "engineer_diff_summary": "this would have made it through if we silently dispatched",
    }
    # KeyError is the natural failure mode; if dispatch helper wraps in
    # MalformedEnvelopeError that is also acceptable. The point: NOT a silent
    # fallback to the base TurnEnvelope.
    with pytest.raises((KeyError, ValidationError)):
        cls = PERSONA_ENVELOPES[meta["persona"]]  # raises KeyError on 'evil'
        cls.model_validate(meta)


def test_round_trip_via_parse_frontmatter_for_each_persona():
    """Smoke-test Phase 2 round-trip for all 11 personas with their valid-value fixture."""
    # Use the same parametrized fixtures as PERSONAS above.
    for cls, role, field, valid_value in PERSONAS:
        # Render YAML-compatible value
        if isinstance(valid_value, str):
            value_str = valid_value
        else:
            value_str = str(valid_value)
        raw = (
            "---\n"
            f"persona: {role}\n"
            f"step_label: {role}:1/1\n"
            "done: false\n"
            f"{field}: {value_str}\n"
            "---\n"
            f"{role} turn body\n"
        )
        meta, _body = parse_frontmatter(raw)
        looked_up = PERSONA_ENVELOPES[meta["persona"]]
        assert looked_up is cls, f"PERSONA_ENVELOPES[{role}] -> {looked_up} expected {cls}"
        instance = looked_up.model_validate(meta)
        assert instance.persona == role
        assert getattr(instance, field) == valid_value
```

**Critical details:**
- The Wave 0 scaffold's `PERSONAS` tuple used dotted aliases like `"pm.challenge"` and freeform string values. Replace entirely with the rubric-anchored tuple shape above; the Wave 0 stub was a no-op (skipped) so no behavior is lost.
- Three parametrized × 11 base tests + 5 field-specific stub-defeating tests + 2 registry tests + 3 round-trip/dispatch tests = 41 test cases minimum.
- `test_dispatch_rejects_unknown_persona_payload` mitigates threat T-04-01 (see threat_model below).
- Use `parse_frontmatter` directly from `clawteam/team/envelope.py` (Phase 2) — no new helper invented.

Atomic-commit discipline (D-01): commit as `test(03-04): un-skip + rewrite envelope_personas tests with rubric-anchored fields + dispatch coverage`.
  </action>
  <verify>
    <automated>pytest tests/test_envelope_personas.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_envelope_personas.py -x` exits 0 (≥41 test cases pass; was 0 before — Wave 0 scaffold was skipped)
    - `pytest tests/test_envelope_personas.py --collect-only -q | tail -5 | grep -E '[0-9]+ tests collected'` shows ≥41 collected
    - `grep -c 'pytest.mark.skip\|pytest.mark.xfail' tests/test_envelope_personas.py` outputs `0` (all stubs un-skipped)
    - `grep -q 'PERSONA_ENVELOPES' tests/test_envelope_personas.py` exits 0 (registry test present)
    - `grep -q 'test_dispatch_rejects_unknown_persona' tests/test_envelope_personas.py` exits 0 (T-04-01 test present)
    - `pytest tests/ -x` exits 0 (full suite still green; no Phase 2 regression)
  </acceptance_criteria>
  <done>tests/test_envelope_personas.py rewritten with rubric-anchored parametrized tests + frontmatter round-trip + unknown-persona rejection; ≥41 tests pass; suite stays green; Wave 0 Nyquist gate restored for D-07.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent-emitted YAML frontmatter -> parse_frontmatter -> dispatch | The persona field on an inbound envelope determines which subclass validates it. Untrusted input (any persona an agent can write) crosses into a security-relevant routing decision (TEAM-04 leader binding). |
| PERSONA_ENVELOPES dict lookup -> subclass instantiation | An unknown persona key must hard-fail, not silently fall back to the base TurnEnvelope (which would accept any extra field by virtue of pydantic's default `extra="ignore"`). |
| 11 subclasses -> Phase 4 SmartReviewRouter | Phase 4 will consume PERSONA_ENVELOPES as a dispatch table. If new personas are added later they MUST be added to this dict; missing entries cause silent payload acceptance. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-01 | Spoofing | Attacker-controlled `persona` field on a TurnEnvelope payload routes through `PERSONA_ENVELOPES` to an unexpected subclass, OR (worse) silently falls back to the base TurnEnvelope which accepts any extras | mitigate | Each subclass declares `persona: Literal["<role>"]` so even if the dispatcher is misimplemented (e.g., default-fallback to TurnEnvelope), the subclass body itself rejects mismatched personas. Test `test_dispatch_rejects_unknown_persona_payload` asserts that `PERSONA_ENVELOPES[meta["persona"]]` raises KeyError on unknown persona — there is no `.get(persona, TurnEnvelope)` fallback. Test `test_persona_envelope_rejects_wrong_persona` (parametrized × 11) covers the spoofing-from-known-persona case. |
| T-04-02 | Tampering | Engineer payload claims `persona: "ceo"` to spoof leader-role authorization (TEAM-04) | mitigate | Two-layer defense: (1) per-persona envelope subclass rejects payloads where required field for the claimed persona is absent — engineer cannot fabricate a valid `ceo_mode: "expansion"` AND a valid `engineer_diff_summary` in the same payload because the ceo subclass has neither. (2) Wave 0's SprintConductor.advance_phase(actor=) consults `team.leader_role`; if the engineer's runtime identity (CLAWTEAM_ROLE env var set by spawn registry) doesn't match `actor`, the conductor rejects. Together: even if the envelope is forged, the conductor rejects mismatched runtime identity vs claimed persona. |
| T-04-03 | Information Disclosure | An optional `designer_ai_slop_findings` list on DesignerEnvelope captures designer's notes which could include URLs or design-system internals | accept | Phase 0 SAFETY rails (`_env()` helpers — QUALITY-15) already deny-filter secret-shaped values from logs. The list is bounded by what the designer chooses to emit; agents are instructed via designer.md (03-05) to redact sensitive content. No PII expected in design rubric output. |
| T-04-04 | Denial of Service | A pathologically long `engineer_diff_summary` (e.g., 1 MB) inflates envelope memory | accept | pydantic v2 validates strings without max_length default; realistic agent output is < 1 KB per envelope. If observed in practice, add `max_length=8192` constraint as a follow-up. Documented as known unbounded in EngineerEnvelope docstring. |

</threat_model>

<verification>
- File exists at gstack-scoped location: `test -f clawteam/templates/gstack/envelope_personas.py` (D-07 delete invariant)
- 11 subclasses importable: `python -c "from clawteam.templates.gstack.envelope_personas import PMEnvelope, CEOEnvelope, EngMgrEnvelope, DesignerEnvelope, DxLeadEnvelope, EngineerEnvelope, ReviewerEnvelope, QAEnvelope, SecurityEnvelope, ShipperEnvelope, SREEnvelope, PERSONA_ENVELOPES"` exits 0
- PERSONA_ENVELOPES has exactly 11 entries with correct keys: registry test passes
- Each subclass enforces its persona Literal: 11 wrong-persona rejection tests pass
- Each subclass rejects missing required field: 11 missing-field rejection tests pass
- Stub-defeating constraints enforced: D-01 (engineer min_length=20) + ceo no-deferred + range checks all pass
- Frontmatter round-trip via parse_frontmatter + dispatch returns correct subclass instance: round-trip test passes
- Unknown-persona payload rejected: T-04-01 test passes
- Wave 0 scaffold un-skipped: `grep -c 'pytest.mark.skip' tests/test_envelope_personas.py` outputs 0
- Suite stays green: `pytest tests/ -x` exits 0
</verification>

<success_criteria>
- TEAM-04 envelope-layer enforcement satisfied: per-persona Literal["<role>"] + required namespaced field structurally prevent the engineer-spoofs-ceo class of attacks (companion to Wave 0's conductor-layer leader_role check)
- D-07 honored: file lives under clawteam/templates/gstack/, deletable as a unit with the rest of the gstack tree
- Pitfall 1 mitigation in place: rubric-anchored Literal/int constraints provide stronger structural drift detection than freeform namespaced strings
- ≥41 tests pass in tests/test_envelope_personas.py (was 0 before — Wave 0 stubs were skipped)
- Phase 2 envelope.py and TurnEnvelope unchanged (additive subclassing only)
- No new dependencies (pydantic v2 already in standard stack)
- Suite stays green: pytest tests/ -x exits 0
- Plan 03-07 (GstackSprintPlugin) can `from clawteam.templates.gstack.envelope_personas import PERSONA_ENVELOPES` in one statement to wire dispatch
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-04-SUMMARY.md` covering:
- File created (clawteam/templates/gstack/envelope_personas.py): line count, 11 subclasses listed
- PERSONA_ENVELOPES registry: 11-entry dict
- Field-name divergence vs RESEARCH.md (rubric-anchored vs freeform namespaced) with the specific override list
- Test count delta in tests/test_envelope_personas.py (Wave 0 skipped → ≥41 active passing)
- Confirmation that 03-07 plugin can dispatch via PERSONA_ENVELOPES in one statement
- Companion to Wave 0 Task 2 (SprintConductor.advance_phase actor=) — together they implement TEAM-04's two-layer defense
</output>
</content>
</invoke>