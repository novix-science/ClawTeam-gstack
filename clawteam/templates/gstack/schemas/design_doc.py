"""DesignDoc — Think-phase artifact written by pm + ceo collaboratively (D-04 phase 1).

Ported from upstream gstack /office-hours rubric (6 forcing questions) + gstack-native
design-doc artifact shape. The ``artifact_type: Literal["design-doc"]`` field is the
discriminator key for Phase 2's EvidenceSchemaRegistry — GstackSprintPlugin.contribute_evidence_schemas
(03-07) registers this class under that key.

Stub-defeating constraints (Pitfall 8 prevention):
  - ``problem_statement`` requires ≥120 chars (~25 words); defeats "TBD" + 5-word bodies
  - ``users`` / ``constraints`` require ≥50 chars each
  - ``rationale`` requires ≥120 chars
  - ``forcing_questions_addressed`` requires EXACTLY 6 items (matches /office-hours arity)
  - ``pm_verdict`` is a Literal enum — misspellings raise ValidationError
"""

from typing import Literal

from pydantic import BaseModel, Field


class DesignDoc(BaseModel):
    """Think-phase artifact. Written by pm + ceo collaboratively.

    Required ## headings (validated by Phase 2 D-03 layer 2 downstream):
      ## problem
      ## users
      ## constraints
      ## rationale
      ## pm-verdict   (one of: proceed | reframe | kill)
    """

    artifact_type: Literal["design-doc"]
    problem_statement: str = Field(..., min_length=120)
    users: str = Field(..., min_length=50)
    constraints: str = Field(..., min_length=50)
    rationale: str = Field(..., min_length=120)
    pm_verdict: Literal["proceed", "reframe", "kill"]
    forcing_questions_addressed: list[int] = Field(..., min_length=6, max_length=6)
    sprint_id: str
    created_at: str
