"""Tests for the TurnEnvelope pydantic model + stdlib YAML frontmatter parser.

Covers Phase 2 Plan 02-02:
  - TurnEnvelope required/optional field shape (§02-CONTEXT D-06, D-07).
  - parse_frontmatter stdlib YAML round-trip + malformed-YAML rejection
    (Pitfall #8 BC invariant — missing fence returns ({}, raw) unmodified).
  - validate_envelope -> MalformedEnvelopeError field-path error shaping.
  - TeamMessage BC invariant (Pitfall #8): the three new envelope fields
    are OPTIONAL with None defaults so existing 15+ construction sites
    keep working. Enforcement happens at Transport.deliver() (Plan 02-08).
"""

from __future__ import annotations

import pytest
from clawteam.team.envelope import (
    MalformedEnvelopeError,
    TurnEnvelope,
    parse_frontmatter,
    validate_envelope,
)
from pydantic import ValidationError

from clawteam.team.models import TeamMessage


def test_turn_envelope_required_fields_present():
    env = TurnEnvelope(persona="engineer", step_label="build:1/3", done=False)
    assert env.persona == "engineer"
    assert env.step_label == "build:1/3"
    assert env.done is False


def test_turn_envelope_rejects_missing_persona():
    with pytest.raises(ValidationError) as exc_info:
        TurnEnvelope(step_label="x", done=False)  # type: ignore[call-arg]
    assert "persona" in str(exc_info.value).lower()


def test_turn_envelope_rejects_empty_persona():
    with pytest.raises(ValidationError):
        TurnEnvelope(persona="", step_label="x", done=False)


def test_turn_envelope_rejects_missing_step_label():
    with pytest.raises(ValidationError) as exc_info:
        TurnEnvelope(persona="engineer", done=False)  # type: ignore[call-arg]
    assert "step_label" in str(exc_info.value).lower()


def test_turn_envelope_rejects_missing_done():
    with pytest.raises(ValidationError) as exc_info:
        TurnEnvelope(persona="engineer", step_label="build:1/3")  # type: ignore[call-arg]
    assert "done" in str(exc_info.value).lower()


def test_turn_envelope_accepts_optional_artifact_fields():
    env = TurnEnvelope(
        persona="engineer",
        step_label="build:1/3",
        done=True,
        artifact_type="design-doc",
        created_at="2026-04-17T10:00:00Z",
        turn_id="a1b2c3d4",
    )
    dumped = env.model_dump()
    assert dumped["persona"] == "engineer"
    assert dumped["step_label"] == "build:1/3"
    assert dumped["done"] is True
    assert dumped["artifact_type"] == "design-doc"
    assert dumped["created_at"] == "2026-04-17T10:00:00Z"
    assert dumped["turn_id"] == "a1b2c3d4"


def test_parse_frontmatter_valid():
    raw = (
        "---\n"
        "persona: engineer\n"
        "step_label: build:1/3\n"
        "done: false\n"
        "---\n"
        "body text\n"
    )
    meta, body = parse_frontmatter(raw)
    assert meta == {"persona": "engineer", "step_label": "build:1/3", "done": False}
    assert body == "body text\n"


def test_parse_frontmatter_no_fence_returns_empty():
    meta, body = parse_frontmatter("no frontmatter here\n")
    assert meta == {}
    assert body == "no frontmatter here\n"


def test_parse_frontmatter_malformed_yaml_raises():
    with pytest.raises(MalformedEnvelopeError) as exc_info:
        parse_frontmatter("---\npersona: [\ninvalid: :\n---\nbody\n")
    msg = str(exc_info.value).lower()
    assert "yaml" in msg or "invalid" in msg


def test_validate_envelope_raises_malformed_envelope_error():
    with pytest.raises(MalformedEnvelopeError) as exc_info:
        validate_envelope({"persona": "", "step_label": "x", "done": True})
    assert "persona" in str(exc_info.value)


def test_team_message_accepts_construction_without_new_envelope_fields():
    msg = TeamMessage(from_agent="engineer", to="reviewer", content="hello")
    assert msg.persona is None
    assert msg.step_label is None
    assert msg.done is None


def test_team_message_accepts_construction_with_new_envelope_fields():
    msg = TeamMessage(
        from_agent="engineer",
        to="reviewer",
        content="hello",
        persona="engineer",
        step_label="build:1/3",
        done=False,
    )
    dumped = msg.model_dump(exclude_none=True)
    assert dumped["persona"] == "engineer"
    assert dumped["step_label"] == "build:1/3"
    assert dumped["done"] is False
