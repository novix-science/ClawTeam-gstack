"""ShipNotes — Ship-phase artifact (per upstream gstack /ship + /land-and-deploy).

Runtime ship tools (``/ship``, ``/land-and-deploy``, ``/canary``, ``/benchmark``,
``/setup-deploy``, ``/document-release``) land in Phase 5. Phase 3 only defines
the pydantic shape so the shipper persona can write a structural placeholder
that satisfies Phase 2's :class:`~clawteam.harness.evidence_gate.EvidenceGate`
post-check (see ``clawteam/harness/evidence_gate.py`` lines 19-21 — ``deploy_url``
drives a HEAD-probe dispatch).

Stub-defeating constraints (Pitfall 8 prevention):
  - ``deploy_url`` ≥1 char (rejects empty string; the literal ``"<pending>"`` is
    accepted per D-02 Phase-5 tool-availability stub — shipper may emit a real
    placeholder string when manually coordinating with ceo)
  - ``ship_step`` Literal over the 8 upstream gstack ship-step enum values
  - ``notes`` ≥20 chars — forces shipper to write a real operator summary
"""

from typing import Literal

from pydantic import BaseModel, Field


class ShipNotes(BaseModel):
    """Ship-phase artifact. Written by shipper (D-02 stub for Phase 3; real /ship in Phase 5).

    The ``deploy_url`` field is required because Phase 2's EvidenceGate post-check
    dispatches against it (verified at evidence_gate.py:19-21). For Phase 3, shipper
    may write the literal value ``"<pending>"`` to satisfy structural requirements
    when manually coordinating with ceo (per D-02 Phase-5 tool-availability stub).
    Phase 5's ``/ship`` replaces the placeholder with the real deploy URL; Phase 2's
    HEAD-probe then verifies the URL is reachable.
    """

    artifact_type: Literal["ship-notes"]
    deploy_url: str = Field(..., min_length=1)
    ship_step: Literal[
        "sync", "test", "audit", "push", "pr", "merge", "deploy", "verify"
    ]
    pr_url: str = ""
    notes: str = Field(..., min_length=20)
    sprint_id: str
    created_at: str

    # ── Phase 5 Plan 05-02 additions (SKILL-14 D-05 failure accounting) ──
    # All fields optional with backward-compatible defaults so Phase 3 callers
    # continue to validate unchanged. The /ship handler (Plan 05-04) populates
    # these; EvidenceGate sees a Phase 3-shaped artifact when no Phase 5 data
    # is available.
    ship_status: Literal["succeeded", "failed", "partial"] | None = None
    steps_completed: list[str] = Field(default_factory=list)
    coverage: float | None = Field(default=None, ge=0.0, le=1.0)
    coverage_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    failure_step: str | None = None
    failure_reason: str | None = None
    branch: str | None = None
    auto_invoked_skills: list[str] = Field(default_factory=list)
