"""Per-persona TurnEnvelope subclass tests (Phase 3 plan 03-04).

Replaces the Wave 0 scaffold (skip stubs from 03-01-PLAN). Field names
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
