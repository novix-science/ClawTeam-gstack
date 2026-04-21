"""Unit tests for clawteam/harness/cross_agent_verification_gate.py (Plan 04-03)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from clawteam.harness.cross_agent_verification_gate import (
    CrossAgentVerificationGate,
    VerificationPair,
)
from clawteam.harness.evidence_schemas import register_schema, reset_registry


class _FakeArtifactA(BaseModel):
    artifact_type: str = "fake-a"
    name: str = "a"


class _FakeArtifactB(BaseModel):
    artifact_type: str = "fake-b"
    count: int = 0


@pytest.fixture(autouse=True)
def _reset_schemas():
    """Isolate each test from the module-level EvidenceSchemaRegistry."""
    reset_registry()
    yield
    reset_registry()


def _register_test_schemas() -> None:
    register_schema("fake-a", _FakeArtifactA)
    register_schema("fake-b", _FakeArtifactB)


def _make_state(artifacts: dict[str, str]) -> Any:
    return SimpleNamespace(artifacts=artifacts)


_RAW_A = "---\nartifact_type: fake-a\nname: alpha\n---\n\nbody text here"
_RAW_B = "---\nartifact_type: fake-b\ncount: 5\n---\n\nbody text here"
_RAW_MALFORMED = "this is not markdown with frontmatter"
_RAW_BAD_SCHEMA = "---\nartifact_type: not-registered\n---\n\nbody"


def test_verifier_ok_returns_true():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier=lambda s, t: (True, "OK"),
    )
    state = _make_state({"a.md": _RAW_A, "b.md": _RAW_B})
    assert gate.check(state) == (True, "")


def test_verifier_fail_returns_false_with_reason():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier=lambda s, t: (False, "no overlap between a and b"),
    )
    state = _make_state({"a.md": _RAW_A, "b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    assert "no overlap" in reason


def test_missing_source_artifact_returns_false():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="missing.md",
        target_artifact="b.md",
        verifier=lambda s, t: (True, ""),
    )
    state = _make_state({"b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing" in reason
    assert "missing.md" in reason


def test_missing_target_artifact_returns_false():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="missing.md",
        verifier=lambda s, t: (True, ""),
    )
    state = _make_state({"a.md": _RAW_A})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing.md" in reason


def test_unregistered_schema_returns_false():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="x.md",
        target_artifact="b.md",
        verifier=lambda s, t: (True, ""),
    )
    state = _make_state({"x.md": _RAW_BAD_SCHEMA, "b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    assert "unregistered schema" in reason


def test_malformed_frontmatter_returns_false():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="bad.md",
        target_artifact="b.md",
        verifier=lambda s, t: (True, ""),
    )
    state = _make_state({"bad.md": _RAW_MALFORMED, "b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    # parse_frontmatter returns ({}, raw) when no frontmatter block present, so the
    # gate surfaces "missing artifact_type" — either form is acceptable; both include
    # the offending artifact name.
    assert "bad.md" in reason


def test_verifier_exception_returns_false():
    _register_test_schemas()

    def throwing(s, t):
        raise ValueError("verifier broke")

    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier=throwing,
    )
    state = _make_state({"a.md": _RAW_A, "b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    assert "ValueError" in reason
    assert "verifier broke" in reason


def test_verifier_receives_pydantic_models():
    _register_test_schemas()
    received: list = []

    def capture(s, t):
        received.append((s, t))
        return True, ""

    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier=capture,
    )
    state = _make_state({"a.md": _RAW_A, "b.md": _RAW_B})
    gate.check(state)
    src, tgt = received[0]
    assert isinstance(src, _FakeArtifactA)
    assert src.name == "alpha"
    assert isinstance(tgt, _FakeArtifactB)
    assert tgt.count == 5


def test_verification_pair_pydantic_model():
    pair = VerificationPair(
        phase="test",
        source_artifact="test-report.md",
        target_artifact="build-report.md",
        verifier_dotted_path=(
            "clawteam.templates.gstack.verifiers.test_report_matches_diff."
            "verify_test_report_matches_engineer_output"
        ),
    )
    assert pair.phase == "test"
    assert pair.source_artifact == "test-report.md"
    assert pair.verifier_dotted_path.startswith("clawteam.templates.gstack.verifiers.")


def test_verification_pair_rejects_empty_fields():
    with pytest.raises(Exception):  # noqa: B017 — pydantic ValidationError
        VerificationPair(
            phase="",  # empty not allowed
            source_artifact="a",
            target_artifact="b",
            verifier_dotted_path="x.y",
        )
