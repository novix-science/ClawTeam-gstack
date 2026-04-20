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

from pydantic import Field

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
    """designer asserts which 1-10 rubric dimension this turn evaluates.

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
    otherwise log as informational. The full 22 false-positive exclusions
    list lives in security.md (03-05) — see Wave 0 CONTENT-DRIFT-NOTE in
    tests/fixtures/gstack_skills/cso.md (upstream v2.0.0 count is 22, not
    the 17 originally sketched in D-13).
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
