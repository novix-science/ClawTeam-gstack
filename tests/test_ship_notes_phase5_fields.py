"""Phase 5 Plan 05-02 Task 1 — ShipNotes Phase 5 field additions.

Red-phase behaviors (per plan):
- Test 1: Minimum Phase 3 construction still validates (backward compatibility).
- Test 2: All Phase 5 optional fields accepted + round-trip through model_dump.
- Test 3: ship_status Literal enforced (unknown value -> ValidationError).
- Test 4: coverage range [0.0, 1.0] enforced on both ends.

Phase 5 fields are all optional with backward-compatible defaults so Phase 3
callers pass validation unchanged (SKILL-14 D-05 failure accounting).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def _phase3_minimum() -> dict:
    """Minimum fields to construct a Phase 3 ShipNotes successfully."""
    return {
        "artifact_type": "ship-notes",
        "deploy_url": "https://staging.clawteam.dev/sprint-001",
        "ship_step": "deploy",
        "notes": "Phase 3 substrate ship: 11 agents + plugin + 6 schemas all verified.",
        "sprint_id": "sprint-001",
        "created_at": "2026-04-20T16:00:00Z",
    }


def test_minimal_phase3_shape_still_valid():
    """Phase 3 callers passing the minimum fields must still validate."""
    from clawteam.templates.gstack.schemas import ShipNotes

    doc = ShipNotes(**_phase3_minimum())
    assert doc.artifact_type == "ship-notes"
    assert doc.ship_step == "deploy"
    # Phase 5 additions default to None / empty collections (BC).
    assert doc.ship_status is None
    assert doc.steps_completed == []
    assert doc.coverage is None
    assert doc.coverage_threshold is None
    assert doc.failure_step is None
    assert doc.failure_reason is None
    assert doc.branch is None
    assert doc.auto_invoked_skills == []


def test_phase5_fields_optional():
    """Construct ShipNotes with all Phase 5 fields populated + round-trip."""
    from clawteam.templates.gstack.schemas import ShipNotes

    meta = _phase3_minimum()
    meta.update(
        ship_status="succeeded",
        steps_completed=["sync", "test"],
        coverage=0.78,
        coverage_threshold=0.5,
        pr_url="https://github.com/x/y/pull/1",
        branch="feat/x",
        auto_invoked_skills=["/test"],
    )
    doc = ShipNotes(**meta)
    assert doc.ship_status == "succeeded"
    assert doc.steps_completed == ["sync", "test"]
    assert doc.coverage == 0.78
    assert doc.coverage_threshold == 0.5
    assert doc.branch == "feat/x"
    assert doc.auto_invoked_skills == ["/test"]

    dumped = doc.model_dump()
    assert dumped["ship_status"] == "succeeded"
    assert dumped["coverage"] == 0.78
    assert dumped["branch"] == "feat/x"

    # Round-trip: dumped -> ShipNotes again.
    doc2 = ShipNotes(**dumped)
    assert doc2.ship_status == doc.ship_status
    assert doc2.steps_completed == doc.steps_completed


def test_ship_status_literal_enforced():
    """ship_status must be one of the three Literal values — reject otherwise."""
    from clawteam.templates.gstack.schemas import ShipNotes

    meta = _phase3_minimum()
    meta["ship_status"] = "unexpected"
    with pytest.raises(ValidationError):
        ShipNotes(**meta)

    # Spot-check each accepted value validates.
    for v in ("succeeded", "failed", "partial"):
        good = dict(meta)
        good["ship_status"] = v
        doc = ShipNotes(**good)
        assert doc.ship_status == v


def test_coverage_range():
    """coverage must be in [0.0, 1.0]."""
    from clawteam.templates.gstack.schemas import ShipNotes

    meta = _phase3_minimum()

    # Below range.
    meta["coverage"] = -0.1
    with pytest.raises(ValidationError):
        ShipNotes(**meta)

    # Above range.
    meta["coverage"] = 1.5
    with pytest.raises(ValidationError):
        ShipNotes(**meta)

    # Inside range.
    meta["coverage"] = 0.5
    doc = ShipNotes(**meta)
    assert doc.coverage == 0.5
