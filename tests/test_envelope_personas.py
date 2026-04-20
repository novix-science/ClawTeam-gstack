"""Scaffold for Phase 3 Wave 0 (Plan 03-01 Task 3).

Tests currently skipped — Wave 1 (Plan 03-03) unskips as the 11
per-persona `TurnEnvelope` subclasses at
`clawteam/templates/gstack/envelope_personas.py` ship.

Covers: D-07 per-persona envelope subclass per role — discriminated-union
dispatch via the `persona` field, one namespaced required reassertion
field per persona (e.g. `pm.challenge`, `ceo.decision_mode`).
"""

from __future__ import annotations

import pytest

# 11 per-persona entries (class_name, persona_tag, aliased_field, exemplar_value).
# Wave 1 populates these assertions verbatim against
# clawteam/templates/gstack/envelope_personas.py.
PERSONAS: list[tuple[str, str, str, object]] = [
    ("PMEnvelope", "pm", "pm.challenge", "Why three months and not now?"),
    ("CEOEnvelope", "ceo", "ceo.decision_mode", "expansion"),
    (
        "EngMgrEnvelope",
        "eng-mgr",
        "eng-mgr.architecture_lock",
        "use existing pydantic registry; no new abstraction",
    ),
    ("DesignerEnvelope", "designer", "designer.dimension", "typographic system"),
    ("DxLeadEnvelope", "dx-lead", "dx-lead.friction", "TTHW > 5min for new install"),
    (
        "EngineerEnvelope",
        "engineer",
        "engineer.diff_summary",
        "added auto_advance flag and tests",
    ),
    ("ReviewerEnvelope", "reviewer", "reviewer.iron_law", "investigated"),
    ("QAEnvelope", "qa", "qa.mode", "qa"),
    ("SecurityEnvelope", "security", "security.confidence", 9),
    ("ShipperEnvelope", "shipper", "shipper.step", "push"),
    ("SREEnvelope", "sre", "sre.signal", "nominal"),
]


@pytest.mark.parametrize("class_name,persona,field_alias,valid_value", PERSONAS)
@pytest.mark.skip(reason="Wave 1: envelope_personas.py ships in 03-03-PLAN")
def test_persona_envelope_required_field_present(
    class_name, persona, field_alias, valid_value
):
    """Each persona subclass must declare its namespaced reassertion field as
    required — constructing without it raises ValidationError.
    """
    pass


@pytest.mark.skip(reason="Wave 1: discriminated-union dispatch on persona")
def test_validate_persona_envelope_dispatches_on_persona():
    """Given a `persona` tag, the validation helper returns the correct subclass.
    (Discriminated union over 11 personas — Phase 2 D-06 extension point.)
    """
    pass
