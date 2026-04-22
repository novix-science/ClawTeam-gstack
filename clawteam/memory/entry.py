"""MemoryEntry pydantic schema — the unit of the TeamMemoryStore JSONL.

See .planning/phases/06-browser-skills-design-pipeline-team-memory/06-RESEARCH.md
§Code Example 1 for schema rationale.

The schema enforces (at pydantic construction time):

* ``id`` matches ``mem-<team-slug>-<YYYYMMDD>-<6-hex>`` — lowercase hex only.
* ``scope`` / ``role`` coupling: ``scope="role"`` requires a non-empty role;
  ``scope="team"`` forbids any role attribute.
* ``tags`` are lowercase-alphanumeric + ``:_-`` only.
* ``confidence`` is in ``[0.0, 1.0]``.
* ``learned_from`` is one of ``{"user", "artifact", "self-inferred",
  "sprint-reflect"}``.
* ``op`` is one of ``{"write", "prune"}`` — tombstone records use ``"prune"``.
* ``tags`` max length 32; ``body`` max length 20 000 chars.

This is the append unit for the JSONL log — never mutated once written.
Deletions are modelled as ``op="prune"`` tombstone records that reference the
original id.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator

_ID_RE = re.compile(r"^mem-[a-zA-Z0-9_-]+-\d{8}-[a-f0-9]{6}$")
_TAG_RE = re.compile(r"^[a-z0-9][a-z0-9:_-]*$")


class MemoryEntry(BaseModel):
    """One memory entry. Append-only to JSONL."""

    # Immutable identity
    id: str = Field(
        ...,
        pattern=_ID_RE.pattern,
        description="mem-<team-slug>-<YYYYMMDD>-<6-hex>",
    )
    author: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="<role>@sprint-<id> or human@cli",
    )
    sprint_id: str = Field(default="", max_length=200)
    phase: str = Field(default="", max_length=100)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC; first 7 chars drive month-bucket selection.",
    )

    # Content
    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field(default="", max_length=20_000)
    tags: list[str] = Field(default_factory=list, max_length=32)

    # Provenance
    evidence: str = Field(
        default="",
        description="path:line | artifact ref | URL; empty => flagged (MEM-05)",
    )
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    learned_from: Literal["user", "artifact", "self-inferred", "sprint-reflect"] = (
        "artifact"
    )

    # Scoping
    scope: Literal["team", "role"] = "team"
    role: str | None = None

    # Op (write = new entry; prune = tombstone record suppressing another id)
    op: Literal["write", "prune"] = "write"

    @field_validator("role")
    @classmethod
    def _role_presence_matches_scope(cls, v, info):
        scope = info.data.get("scope")
        if scope == "role" and not v:
            raise ValueError("scope='role' requires non-empty role")
        if scope == "team" and v:
            raise ValueError("scope='team' forbids role attribute")
        return v

    @field_validator("tags")
    @classmethod
    def _tags_lowercase_alnum(cls, tags):
        for t in tags:
            if not _TAG_RE.fullmatch(t):
                raise ValueError(
                    f"invalid tag {t!r}: must match [a-z0-9][a-z0-9:_-]*"
                )
        return tags


__all__ = ["MemoryEntry"]
