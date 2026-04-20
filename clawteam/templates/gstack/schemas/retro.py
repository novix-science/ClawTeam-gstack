"""Retro — Reflect-phase artifact (per upstream gstack /retro).

Captures the per-persona attribution + what-worked / what-failed / key-lessons
triple that the Reflect-phase eng-mgr persona synthesizes after Ship completes.
Per D-09, a Phase-3 event handler also writes a JSON placeholder under
``~/.clawteam/teams/<team>/_phase6_pending/<sprint_id>-retro.json`` so Phase 6's
backfill scanner can hydrate :class:`TeamMemoryStore` entries from the retro
body + persona-attribution metadata.

Stub-defeating constraints (Pitfall 8 prevention):
  - ``personas`` ≥2 — at minimum two personas must sign any retro (leader + one
    other); defeats "solo ceo post-mortem" degenerate case
  - ``what_worked`` ≥1 entry — real retros surface at least one positive
  - ``key_lessons`` ≥1 entry — the retro's actual purpose; empty means no learning
"""

from typing import Literal

from pydantic import BaseModel, Field


class Retro(BaseModel):
    """Reflect-phase artifact. Written by eng-mgr after Ship completes.

    The ``personas`` list captures per-persona attribution per D-09:
    each persona contributing to the sprint signs their section of the retro.
    Phase 6's ``TeamMemoryStore`` reads this to attribute ``/learn`` entries
    to the persona that surfaced each lesson (provenance for Pitfall 10 defeat).
    """

    artifact_type: Literal["retro"]
    personas: list[str] = Field(..., min_length=2)
    what_worked: list[str] = Field(..., min_length=1)
    what_failed: list[str] = Field(default_factory=list)
    key_lessons: list[str] = Field(..., min_length=1)
    sprint_id: str
    created_at: str
