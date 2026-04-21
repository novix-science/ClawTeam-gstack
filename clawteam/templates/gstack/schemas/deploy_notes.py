"""Land-and-deploy artifact schema (SKILL-15, CONTEXT §specifics).

Written by /land-and-deploy skill (Plan 05-06). EvidenceGate HEAD-probes the
deploy_url (Pitfall 8 gate-gaming prevention) before the Ship-phase transition
to Reflect.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DeployNotes(BaseModel):
    """Deploy artifact. Written by /land-and-deploy handler (SKILL-15)."""

    artifact_type: Literal["deploy-notes"]
    deploy_status: Literal["succeeded", "failed", "pending"]
    deploy_url: str = Field(..., min_length=1)
    provider: Literal["vercel", "netlify", "fly", "custom"]
    deployed_at: str  # ISO-8601
    commit_sha: str = Field(..., min_length=7, max_length=40)
    sprint_id: str
    created_at: str
    persona: str = "shipper"
    step_label: str = "deploy"
    done: bool = True
