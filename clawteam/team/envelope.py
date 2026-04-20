"""Turn envelope pydantic model + stdlib YAML frontmatter parser.

Shared contract for Phase 2's two envelope-enforcement sites:
  1. `clawteam.transport.base.Transport.deliver` — validates TeamMessage.persona /
     step_label / done on every deliver (Plan 02-08).
  2. `clawteam.harness.evidence_gate.EvidenceGate.check` — parses artifact YAML
     frontmatter into a TurnEnvelope instance (Plan 02-07).

Per CONTEXT §specifics lesson #2: "one pydantic model, two serialization surfaces".
Per RESEARCH §Standard Stack: stdlib-only parser to keep Phase 2 at zero new required
runtime deps (PyYAML is already transitively present via questionary's stack in the
project environment; verify with `pip show PyYAML`).
"""

from __future__ import annotations

import re
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class MalformedEnvelopeError(ValueError):
    """Raised by deliver() and ArtifactStore.write() on missing/invalid envelope fields.

    Subclasses ValueError so `clawteam.mcp.helpers.translate_error` auto-wraps it
    into an MCPToolError for agent-facing responses (§02-CONTEXT D-12).
    """


class TurnEnvelope(BaseModel):
    """Validates both TeamMessage envelope fields and artifact YAML frontmatter.

    Required fields (§02-CONTEXT D-06):
      - persona: agent role asserting this turn
      - step_label: free-form step marker, e.g. 'plan:2/5'
      - done: explicit turn-done signal (False = more output pending; True = handoff)

    Artifact-only optional fields (§02-CONTEXT D-07):
      - artifact_type: discriminator for EvidenceSchemaRegistry lookup (Plan 02-04)
      - created_at: ISO-8601 timestamp
      - turn_id: uuid.uuid4().hex[:8] for cross-channel dedupe (Pitfall #2 turn-counter)
    """

    persona: str = Field(..., min_length=1, description="Agent role asserting this turn")
    step_label: str = Field(..., min_length=1, description="Free-form step marker")
    done: bool = Field(..., description="Turn-done signal")
    artifact_type: str | None = None
    created_at: str | None = None
    turn_id: str | None = None


# Frontmatter regex — matches only the specific shape documented in §02-CONTEXT D-07.
# Anchors with \A..\Z so a partial match never succeeds; DOTALL so multi-line bodies flow.
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into (frontmatter_dict, body_string).

    Returns ({}, raw) when no frontmatter block is present — this is the Pitfall #8
    invariant: artifacts without frontmatter pass through untouched so existing
    templates' ArtifactStore.write() calls do NOT start failing once Phase 2 lands.

    Raises MalformedEnvelopeError on syntactically invalid YAML or non-mapping top-level.
    """
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise MalformedEnvelopeError(f"frontmatter YAML invalid: {exc}") from exc
    if not isinstance(meta, dict):
        raise MalformedEnvelopeError(
            f"frontmatter must be a mapping, got {type(meta).__name__}"
        )
    return meta, m.group(2)


def validate_envelope(meta: dict[str, Any]) -> TurnEnvelope:
    """Validate a meta dict against TurnEnvelope; raises MalformedEnvelopeError on failure.

    Error messages are shaped `"envelope invalid: <field.path>: <first-message>"`
    so Plans 02-07 / 02-08 can surface the specific field in gate-reason / MCP error.
    """
    try:
        return TurnEnvelope.model_validate(meta)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"])
        raise MalformedEnvelopeError(
            f"envelope invalid: {field}: {first['msg']}"
        ) from exc
