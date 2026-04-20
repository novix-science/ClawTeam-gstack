"""ReviewReport — Review-phase artifact (per upstream gstack /review + /investigate).

Captures the SHA-pinned review verdict + findings + hypothesis traces that the
Review-phase reviewer persona emits. The ``review_sha`` field encodes the
Pitfall 9 SHA-PIN-DEFERRED meta-instruction — reviewer records HEAD SHA at
review-start; if HEAD moved mid-review, verdict is 'superseded' and the reviewer
stops. Real ``SmartReviewRouter`` SHA-pinning with cross-agent verification ships
in Phase 4; Phase 3 only enforces the structural shape of the field.

Stub-defeating constraints (Pitfall 8 prevention):
  - ``review_sha`` ≥7 hex chars (git short-SHA minimum) via regex ``^[0-9a-f]+$``
  - ``verdict`` Literal over {approved, rejected, needs-revision, superseded}
  - ``findings`` list ≥1 entry — reviewer must enumerate at least one finding
  - ``reviewer_persona`` ≥2 chars — rejects empty string from spoofing attempts
"""

from typing import Literal

from pydantic import BaseModel, Field


class ReviewReport(BaseModel):
    """Review-phase artifact. Written by reviewer (aggregating parallel reviewers in Phase 4).

    The ``review_sha`` field encodes the Pitfall 9 SHA-PIN-DEFERRED meta-instruction:
    reviewer records the HEAD SHA at review start; if HEAD moved mid-review, mark
    ``verdict='superseded'`` and stop. Real SmartReviewRouter SHA-pinning with
    cross-agent verification ships in Phase 4 (per 03-CONTEXT §deferred).
    """

    artifact_type: Literal["review-report"]
    review_sha: str = Field(..., min_length=7, pattern=r"^[0-9a-f]+$")
    verdict: Literal["approved", "rejected", "needs-revision", "superseded"]
    hypothesis_traces: list[str] = Field(default_factory=list)
    findings: list[str] = Field(..., min_length=1)
    reviewer_persona: str = Field(..., min_length=2)
    sprint_id: str
    created_at: str
