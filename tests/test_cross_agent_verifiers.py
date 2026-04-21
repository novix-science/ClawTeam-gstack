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
