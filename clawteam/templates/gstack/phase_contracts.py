"""Gstack phase artifact requirements."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

PHASE_REQUIREMENTS: dict[str, list[str]] = {
    "think": ["delegation.json"],
    "plan": ["architecture-lock.md"],
    "build": ["diff.patch"],
    "review": ["review-report.md"],
    "test": ["test-report.json"],
    "ship": ["ship-approval.md"],
    "reflect": ["retro.md"],
}

ARTIFACT_TYPE_TO_NAME: dict[str, str] = {
    "delegation": "delegation.json",
    "architecture-lock": "architecture-lock.md",
    "diff": "diff.patch",
    "review-report": "review-report.md",
    "test-report": "test-report.json",
    "ship_approval": "ship-approval.md",
    "retro": "retro.md",
}


class DelegationArtifact(BaseModel):
    """Think-phase delegation artifact."""

    artifact_type: Literal["delegation"]
    sprint_id: str
    delegated_roles: list[str] = Field(..., min_length=1)
    created_at: str


class ArchitectureLockArtifact(BaseModel):
    """Plan-phase architecture lock artifact."""

    artifact_type: Literal["architecture-lock"]
    sprint_id: str
    architecture_lock: str = Field(..., min_length=80)
    created_at: str


class DiffArtifact(BaseModel):
    """Build-phase diff artifact."""

    artifact_type: Literal["diff"]
    sprint_id: str
    files_changed: list[str] = Field(..., min_length=1)
    created_at: str


class ShipApprovalArtifact(BaseModel):
    """Ship-phase approval artifact."""

    artifact_type: Literal["ship_approval"]
    approved_by: str = Field(..., min_length=1)
    approved_at: str
    sha_at_approval: str = Field(..., min_length=7)
    sprint_id: str
