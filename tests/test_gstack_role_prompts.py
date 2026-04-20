"""Scaffold for Phase 3 Wave 0 (Plan 03-01 Task 3).

Tests currently skipped — Wave 2 (Plans 03-04 + 03-05) unskips as the 11
`clawteam/templates/gstack/prompts/<role>.md` files ship.

Covers: SKILL-01..SKILL-08 (golden grep tests against signature lines +
rubric content presence + `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:`
greppable strings) + D-14 prompt budget gate (≤4 KB per file, ≤3 KB average).

Cross-checks the ported prompt content against the verbatim upstream fixtures
committed in Task 1 under tests/fixtures/gstack_skills/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Path anchors — Wave 2 tests use these to grep both the ported prompt AND
# the upstream fixture (Strategy B per D-08).
PROMPTS_DIR = (
    Path(__file__).parent.parent / "clawteam" / "templates" / "gstack" / "prompts"
)
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "gstack_skills"


# One scaffold per role. Wave 2 unskips with verbatim content-presence
# assertions keyed off the D-13 fixtures (CONTENT-DRIFT-NOTE headers
# already encode the actual upstream counts: 6 forcing questions,
# 7 plan-design-review passes, 22 cso exclusions).


@pytest.mark.skip(reason="Wave 2: pm.md ships in 03-04-PLAN")
def test_pm_office_hours_rubric():
    """SKILL-01: pm.md contains all 6 forcing questions (Q1-Q6 names from
    office-hours.md CONTENT-DRIFT-NOTE) + challenge-framing +
    INTERACTIVE-RUNTIME-DEFERRED marker.
    """
    pass


@pytest.mark.skip(reason="Wave 2: ceo.md ships in 03-04-PLAN")
def test_ceo_plan_review_modes():
    """SKILL-02: ceo.md contains 4 decision modes (Expansion/Selective/Hold/Reduction)."""
    pass


@pytest.mark.skip(reason="Wave 2: eng-mgr.md ships in 03-04-PLAN")
def test_eng_mgr_plan_review_and_retro():
    """SKILL-03: eng-mgr.md contains arch-lock + data-flow + edge-case matrix
    + test-plan + retro-per-person headings.
    """
    pass


@pytest.mark.skip(reason="Wave 2: designer.md ships in 03-04-PLAN")
def test_designer_rubric():
    """SKILL-04: designer.md contains the 7 plan-design-review passes (upstream
    drift from D-13's stated 10 — see fixtures/gstack_skills/plan-design-review.md
    CONTENT-DRIFT-NOTE) + AI-slop checklist + INTERACTIVE-RUNTIME-DEFERRED
    marker for /design-consultation.
    """
    pass


@pytest.mark.skip(reason="Wave 2: dx-lead.md ships in 03-04-PLAN")
def test_dx_lead_devex_review():
    """SKILL-05: dx-lead.md contains the 3 personas + TTHW + friction tracing."""
    pass


@pytest.mark.skip(reason="Wave 2: reviewer.md ships in 03-04-PLAN")
def test_reviewer_review_and_investigate():
    """SKILL-06: reviewer.md contains iron-law + halt-after-3 + SHA-PIN-DEFERRED
    + INTERACTIVE-RUNTIME-DEFERRED for /investigate.
    """
    pass


@pytest.mark.skip(reason="Wave 2: qa.md ships in 03-04-PLAN")
def test_qa_qa_only():
    """SKILL-07: qa.md contains bug-fix + regression-loop + qa-only mode suppression."""
    pass


@pytest.mark.skip(reason="Wave 2: security.md ships in 03-04-PLAN")
def test_security_cso_full_rubric():
    """SKILL-08: security.md contains OWASP Top 10 + STRIDE + 22 false-positive
    exclusions (drift from D-13's stated 17 — see fixtures/gstack_skills/cso.md
    CONTENT-DRIFT-NOTE) + 8/10+ confidence gate.
    """
    pass


@pytest.mark.skip(reason="Wave 2: D-14 prompt budget gate")
def test_role_prompt_size_budget():
    """D-14: every prompt <= 4 KB; average <= 3 KB. Hard verification gate."""
    sizes = {p.name: p.stat().st_size for p in PROMPTS_DIR.glob("*.md")}
    assert len(sizes) == 11, f"expected 11 prompts, found {len(sizes)}: {sorted(sizes)}"
    for name, size in sizes.items():
        assert size <= 4096, f"{name} = {size} bytes (D-14 hard cap 4096)"
    avg = sum(sizes.values()) / len(sizes)
    assert avg <= 3072, f"average = {avg:.0f} bytes (D-14 soft cap 3072)"
