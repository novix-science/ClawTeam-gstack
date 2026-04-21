"""Codex-review artifact (SKILL-13).

Written by /codex skill (Plan 05-03). ``mode`` tags which of the three modes
(review|adversarial|consultation) produced the review; ``verdict`` is pass/fail
only for mode='review'; for adversarial/consultation, verdict='n/a'.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CodexReview(BaseModel):
    """Codex review artifact. Written by /codex handler (SKILL-13)."""

    artifact_type: Literal["codex-review"]
    mode: Literal["review", "adversarial", "consultation"]
    target: str = Field(..., min_length=1)  # file, branch, or prompt summary
    verdict: Literal["pass", "fail", "n/a"] = "n/a"
    summary: str = ""
    sprint_id: str
    created_at: str
    persona: str = "engineer"  # or reviewer; handler stamps actual invoker
    step_label: str = "codex"
    done: bool = True
