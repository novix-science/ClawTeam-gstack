"""Per-role prompt golden grep tests (Phase 3 plan 03-05).

Replaces the Wave 0 scaffold (skip stubs from 03-01-PLAN). Asserts:
- Each of the 8 pure-rubric prompts contains its canonical greppable strings
- Each prompt's signature line is present verbatim
- Cross-check: canonical strings present in BOTH the upstream fixture AND the
  ported prompt (drift detection — if upstream changes and we re-fetch, the
  test will catch the drift)
- D-14 budget gate: every prompt <= 4096 bytes; average <= 3072 bytes
- Cross-file: all 11 prompt files present (xfails when 03-06's 3 stubs are missing)

Drift notes recorded in Wave 0 fixtures are honored here:
- office-hours.md: 6 forcing questions with Q1-Q6 names (matches D-13 count)
- plan-design-review.md: 7 passes upstream (drift from D-13's stated 10)
- cso.md: 22 false-positive exclusions upstream (drift from D-13's stated 17)
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Path anchors — Wave 2 tests grep both the ported prompt AND the upstream
# fixture (Strategy B per D-08).
PROMPTS_DIR = (
    Path(__file__).parent.parent / "clawteam" / "templates" / "gstack" / "prompts"
)
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "gstack_skills"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# SKILL-01: pm
# ---------------------------------------------------------------------------


def test_pm_office_hours_rubric():
    """SKILL-01: pm.md contains all 6 forcing questions (Q1-Q6 names from
    office-hours.md CONTENT-DRIFT-NOTE) + challenge-framing +
    INTERACTIVE-RUNTIME-DEFERRED marker.
    """
    prompt = _read(PROMPTS_DIR / "pm.md")
    fixture = _read(FIXTURES_DIR / "office-hours.md")

    # Signature (canonical — exact match)
    assert (
        "SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1" in prompt
    )

    # Pitfall 7 partition
    assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt

    # Envelope reference (PMEnvelope.pm_question_index)
    assert "pm_question_index" in prompt

    # Challenge-framing instruction
    assert "challenge" in prompt.lower()

    # Canonical Q1-Q6 names per office-hours fixture CONTENT-DRIFT-NOTE
    for q_name in (
        "Demand Reality",
        "Status Quo",
        "Desperate Specificity",
        "Narrowest Wedge",
        "Observation",
        "Future-Fit",
    ):
        assert q_name in prompt, f"pm.md missing Q-name '{q_name}'"
        assert q_name in fixture, (
            f"office-hours.md fixture missing Q-name '{q_name}' "
            "— drift requires updating test + pm.md together"
        )

    # At least 6 numbered forcing-question lines
    pm_questions = [
        line
        for line in prompt.splitlines()
        if line.strip()[:2] in {f"{i}." for i in range(1, 10)}
    ]
    assert len(pm_questions) >= 6, (
        f"pm.md has fewer than 6 numbered forcing questions: {len(pm_questions)}"
    )


# ---------------------------------------------------------------------------
# SKILL-02: ceo
# ---------------------------------------------------------------------------


def test_ceo_plan_review_modes():
    """SKILL-02: ceo.md contains 4 decision modes (Expansion/Selective/Hold/Reduction)."""
    prompt = _read(PROMPTS_DIR / "ceo.md")
    fixture = _read(FIXTURES_DIR / "plan-ceo-review.md")

    assert (
        "SIGNATURE: gstack-role:ceo rubric:plan-ceo-review envelope-version:1"
        in prompt
    )

    for mode in ("Expansion", "Selective", "Hold", "Reduction"):
        assert mode in prompt, f"ceo.md missing mode '{mode}'"
        # Upstream fixture uses UPPERCASE variants (SCOPE EXPANSION etc.)
        assert mode.lower() in fixture.lower(), (
            f"plan-ceo-review.md fixture missing mode '{mode}' (case-insensitive)"
        )

    assert "ceo_mode" in prompt  # envelope reference
    assert "advance_phase" in prompt  # TEAM-04 leader-only reminder


# ---------------------------------------------------------------------------
# SKILL-03: eng-mgr
# ---------------------------------------------------------------------------


def test_eng_mgr_plan_review_and_retro():
    """SKILL-03: eng-mgr.md contains arch-lock + data-flow + edge-case matrix
    + test-plan + retro-per-person headings.
    """
    prompt = _read(PROMPTS_DIR / "eng-mgr.md")

    assert (
        "SIGNATURE: gstack-role:eng-mgr rubric:plan-eng-review+retro "
        "envelope-version:1" in prompt
    )
    for piece in ("architecture-lock", "data-flow", "test-plan", "retro"):
        assert piece in prompt, f"eng-mgr.md missing rubric piece '{piece}'"
    # Edge-case matrix may use "edge-case-matrix" or "edge-case matrix"
    assert "edge-case" in prompt.lower(), "eng-mgr.md missing edge-case rubric piece"
    assert "eng_mgr_deliverable" in prompt  # envelope reference
    # Cross-fixture presence
    assert (FIXTURES_DIR / "plan-eng-review.md").exists()
    assert (FIXTURES_DIR / "retro.md").exists()


# ---------------------------------------------------------------------------
# SKILL-04: designer (7 passes, drift-adjusted from D-13 expected 10)
# ---------------------------------------------------------------------------


def test_designer_rubric():
    """SKILL-04: designer.md contains the 7 plan-design-review passes
    (upstream drift from D-13's stated 10 — see fixtures/gstack_skills/
    plan-design-review.md CONTENT-DRIFT-NOTE) + AI-slop checklist +
    INTERACTIVE-RUNTIME-DEFERRED marker for /design-consultation.
    """
    prompt = _read(PROMPTS_DIR / "designer.md")
    fixture = _read(FIXTURES_DIR / "plan-design-review.md")

    assert (
        "SIGNATURE: gstack-role:designer "
        "rubric:plan-design-review+design-review envelope-version:1" in prompt
    )
    assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt
    assert "designer_rubric_dimension" in prompt  # envelope reference

    # 7 numbered passes (drift-adjusted per plan-design-review.md
    # CONTENT-DRIFT-NOTE — upstream ships Pass 1-7, not the D-13-expected 10).
    nums = [
        line
        for line in prompt.splitlines()
        if line.strip().split(".")[0].isdigit()
        and 1 <= int(line.strip().split(".")[0]) <= 10
    ]
    assert len(nums) >= 7, (
        f"designer.md has fewer than 7 numbered passes: {len(nums)}"
    )

    # Canonical pass names from the fixture's CONTENT-DRIFT-NOTE
    for pass_name in (
        "Information Architecture",
        "Interaction State",
        "User Journey",
        "AI Slop",
        "Design System",
        "Responsive",
        "Unresolved Design",
    ):
        assert pass_name in prompt, f"designer.md missing pass '{pass_name}'"
        assert pass_name in fixture, (
            f"plan-design-review.md fixture missing pass '{pass_name}'"
        )

    # AI-slop checklist marker (case-insensitive)
    assert (
        "AI-slop" in prompt
        or "ai-slop" in prompt.lower()
        or "AI Slop" in prompt
    )


# ---------------------------------------------------------------------------
# SKILL-05: dx-lead
# ---------------------------------------------------------------------------


def test_dx_lead_devex_review():
    """SKILL-05: dx-lead.md contains the 3 personas + TTHW + friction tracing."""
    prompt = _read(PROMPTS_DIR / "dx-lead.md")

    assert (
        "SIGNATURE: gstack-role:dx-lead rubric:plan-devex-review+devex-review "
        "envelope-version:1" in prompt
    )
    for persona in ("novice", "pro", "power-user"):
        assert persona in prompt, f"dx-lead.md missing persona '{persona}'"
    assert (
        "TTHW" in prompt
        or "Time-to-Hello-World" in prompt
        or "Time-To-Hello-World" in prompt
    )
    assert "friction" in prompt.lower()
    assert "dx_lead_friction_source" in prompt  # envelope reference


# ---------------------------------------------------------------------------
# SKILL-06: reviewer
# ---------------------------------------------------------------------------


def test_reviewer_review_and_investigate():
    """SKILL-06: reviewer.md contains iron-law + halt-after-3 + SHA-PIN-DEFERRED
    + INTERACTIVE-RUNTIME-DEFERRED for /investigate.
    """
    prompt = _read(PROMPTS_DIR / "reviewer.md")

    assert (
        "SIGNATURE: gstack-role:reviewer rubric:review+investigate "
        "envelope-version:1" in prompt
    )
    assert "iron-law" in prompt.lower() or "iron law" in prompt.lower()
    assert "halt" in prompt.lower()
    assert "3" in prompt  # halt-after-3 reference
    assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt
    assert "SHA-PIN-DEFERRED" in prompt
    assert "reviewer_hypothesis_index" in prompt  # envelope reference


# ---------------------------------------------------------------------------
# SKILL-07: qa
# ---------------------------------------------------------------------------


def test_qa_qa_only():
    """SKILL-07: qa.md contains bug-fix + regression-loop + qa-only mode suppression."""
    prompt = _read(PROMPTS_DIR / "qa.md")

    assert "SIGNATURE: gstack-role:qa rubric:qa+qa-only envelope-version:1" in prompt
    assert "qa-only" in prompt
    assert "regression" in prompt.lower()
    assert "bug" in prompt.lower()  # bug-fix loop
    assert "qa_mode" in prompt  # envelope reference


# ---------------------------------------------------------------------------
# SKILL-08: security (the largest port — 22 exclusions verbatim,
# drift-adjusted from D-13's expected 17)
# ---------------------------------------------------------------------------


def test_security_cso_full_rubric():
    """SKILL-08: security.md contains OWASP Top 10 + STRIDE + 22 false-positive
    exclusions (drift from D-13's stated 17 — see fixtures/gstack_skills/cso.md
    CONTENT-DRIFT-NOTE) + 8/10+ confidence gate.
    """
    prompt = _read(PROMPTS_DIR / "security.md")
    fixture = _read(FIXTURES_DIR / "cso.md")

    assert (
        "SIGNATURE: gstack-role:security rubric:cso envelope-version:1" in prompt
    )
    assert "OWASP" in prompt
    assert "STRIDE" in prompt
    assert "security_confidence" in prompt  # envelope reference

    # 8+ confidence gate (D-13 / SKILL-08)
    assert "8" in prompt and (
        "confidence" in prompt.lower() or "escalat" in prompt.lower()
    )

    # OWASP Top 10: at least 10 numbered lines visible (1-10 at start of line)
    owasp_lines = [
        line
        for line in prompt.splitlines()
        if line.strip().split(".")[0].isdigit()
        and 1 <= int(line.strip().split(".")[0]) <= 10
    ]
    assert len(owasp_lines) >= 10, (
        f"security.md has fewer than 10 OWASP entries: {len(owasp_lines)}"
    )

    # 22 false-positive exclusions (drift-adjusted from D-13 expected 17 per
    # cso.md CONTENT-DRIFT-NOTE): total numbered lines >= 32 (10 OWASP + 22).
    all_numbered = [
        line
        for line in prompt.splitlines()
        if line.strip().split(".")[0].isdigit()
    ]
    assert len(all_numbered) >= 32, (
        f"security.md numbered-list count {len(all_numbered)} < 32 "
        "(10 OWASP + 22 exclusions per cso.md CONTENT-DRIFT-NOTE). "
        "If upstream cso.md drifts to a different exclusion count, "
        "update this assertion to (10 + actual N)."
    )

    # Cross-fixture: cso.md fixture also references the canonical phrases
    assert "OWASP" in fixture
    assert (
        "false positive" in fixture.lower() or "false-positive" in fixture.lower()
    )


# ---------------------------------------------------------------------------
# D-01: engineer (implementation-discipline rubric, no upstream skill fixture)
# ---------------------------------------------------------------------------


def test_engineer_implementation_discipline_rubric():
    """D-01: engineer.md ships the canonical implementation-discipline rubric.

    No upstream gstack skill file owns this content — it is canonical to
    gstack's Build phase per CONTEXT.md D-01. Grep-verifiable content list:
    read-first-before-write, atomic-commit, SHA-pin awareness,
    engineer_diff_summary envelope assertion, no-fix-without-investigation
    deferral (routes to reviewer iron-law), Phase-5 /codex + /ship stub.
    """
    prompt = _read(PROMPTS_DIR / "engineer.md")

    # Signature
    assert (
        "SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1"
        in prompt
    )

    # D-01 grep-verifiable content list (CONTEXT.md lines 34-42)
    assert "read-first" in prompt.lower(), "engineer.md missing read-first-before-write"
    assert (
        "atomic-commit" in prompt.lower()
        or "atomic commit" in prompt.lower()
        or "one logical change per commit" in prompt.lower()
    ), "engineer.md missing atomic-commit discipline"
    assert "SHA" in prompt and "HEAD" in prompt, (
        "engineer.md missing SHA-pin awareness at Build-phase start"
    )
    assert "engineer_diff_summary" in prompt, (
        "engineer.md missing engineer_diff_summary envelope assertion"
    )
    assert (
        "no fix without investigation" in prompt.lower()
        or "no-fix-without-investigation" in prompt.lower()
        or ("investigate" in prompt.lower() and "iron-law" in prompt.lower())
    ), "engineer.md missing no-fix-without-investigation deferral"

    # Phase-5 tool-availability stub
    assert "/codex" in prompt, "engineer.md missing /codex Phase-5 stub reference"
    assert "/ship" in prompt, "engineer.md missing /ship Phase-5 stub reference"
    assert "phase 5" in prompt.lower() or "until" in prompt.lower(), (
        "engineer.md missing Phase-5 deferral framing"
    )


# ---------------------------------------------------------------------------
# D-02: shipper (minimal Phase-5-deferred stub, no upstream skill fixture)
# ---------------------------------------------------------------------------


def test_shipper_minimal_stub():
    """D-02: shipper.md ships an honest Phase-5-deferred stub.

    The SIGNATURE's `rubric:none` flag is intentional and grep-asserted — it
    is the unambiguous marker Phase 5's plan task uses to identify this file
    as a stub needing replacement with /ship + /land-and-deploy rubric content.
    """
    prompt = _read(PROMPTS_DIR / "shipper.md")

    # Signature with rubric:none flag (Phase 5 swap target)
    assert (
        "SIGNATURE: gstack-role:shipper rubric:none envelope-version:1" in prompt
    )

    # Envelope reference + 6 Literal values (CONTEXT.md D-02)
    assert "shipper_step" in prompt
    for step in ("prep", "pushing", "pr-open", "merged", "deployed", "verified"):
        assert step in prompt, f"shipper.md missing shipper_step Literal value '{step}'"

    # Phase-5 tool-availability stub
    assert "/ship" in prompt, "shipper.md missing /ship Phase-5 stub reference"
    assert "/land-and-deploy" in prompt, (
        "shipper.md missing /land-and-deploy Phase-5 stub reference"
    )
    assert "<pending>" in prompt, (
        "shipper.md missing <pending> placeholder per D-02 + 03-03 ShipNotes carve-out"
    )


# ---------------------------------------------------------------------------
# D-03: sre (minimal Phase-5-deferred stub, no upstream skill fixture)
# ---------------------------------------------------------------------------


def test_sre_minimal_stub():
    """D-03: sre.md ships an honest Phase-5-deferred stub.

    The SIGNATURE's `rubric:none` flag is intentional and grep-asserted — it
    is the unambiguous marker Phase 5's plan task uses to identify this file
    as a stub needing replacement with /canary + /benchmark + /setup-deploy
    rubric content.
    """
    prompt = _read(PROMPTS_DIR / "sre.md")

    # Signature with rubric:none flag (Phase 5 swap target)
    assert "SIGNATURE: gstack-role:sre rubric:none envelope-version:1" in prompt

    # Envelope reference + 4 Literal values (CONTEXT.md D-03)
    assert "sre_signal" in prompt
    for signal in ("nominal", "degraded", "regression", "outage"):
        assert signal in prompt, f"sre.md missing sre_signal Literal value '{signal}'"

    # Phase-5 tool-availability stub
    for tool in ("/canary", "/benchmark", "/setup-deploy"):
        assert tool in prompt, f"sre.md missing {tool} Phase-5 stub reference"


# ---------------------------------------------------------------------------
# D-14 budget gate (spans all 11 prompts after 03-06)
# ---------------------------------------------------------------------------


def test_role_prompt_size_budget():
    """D-14: every prompt <= 4 KB; average <= 3 KB.

    All 11 prompts now exist (03-05 shipped 8 + 03-06 shipped 3). Both bounds
    are HARD gates — Phase 6 memory-inclusion design must respect them.
    """
    sizes = {p.name: p.stat().st_size for p in PROMPTS_DIR.glob("*.md")}
    assert len(sizes) == 11, (
        f"expected 11 prompt files (all 03-05 + 03-06 prompts), found {len(sizes)}: "
        f"{sorted(sizes)}"
    )
    for name, size in sizes.items():
        assert size <= 4096, f"{name} = {size} bytes (D-14 hard cap 4096)"
    avg = sum(sizes.values()) / len(sizes)
    assert avg <= 3072, f"average = {avg:.0f} bytes (D-14 soft cap 3072)"


# ---------------------------------------------------------------------------
# Cross-file: all 11 prompt files present (un-xfailed after 03-06)
# ---------------------------------------------------------------------------


def test_all_eleven_prompt_files_present():
    expected = {
        "pm.md",
        "ceo.md",
        "eng-mgr.md",
        "designer.md",
        "dx-lead.md",
        "engineer.md",
        "reviewer.md",
        "qa.md",
        "security.md",
        "shipper.md",
        "sre.md",
    }
    present = {p.name for p in PROMPTS_DIR.glob("*.md")}
    assert present == expected, (
        f"missing: {expected - present}; extra: {present - expected}"
    )
