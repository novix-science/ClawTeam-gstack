"""Canary post-deploy monitor artifact (SKILL-17, D-09).

Written by /canary skill (Plan 05-08). canary_status='regression' when any
regression_flag is set (5xx rate >1%, response time >2x baseline, or any JS
console error observed).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CanaryReport(BaseModel):
    """Canary artifact. Written by /canary handler (SKILL-17)."""

    artifact_type: Literal["canary-report"]
    canary_status: Literal["clean", "regression"]
    window_seconds: int = Field(..., ge=1)
    http_2xx_count: int = Field(..., ge=0)
    http_5xx_count: int = Field(..., ge=0)
    avg_response_ms: float = Field(..., ge=0.0)
    pre_deploy_avg_response_ms: float = Field(default=0.0, ge=0.0)
    baseline_missing: bool = False
    js_console_errors: list[str] = Field(default_factory=list)
    regression_flags: list[str] = Field(default_factory=list)
    sprint_id: str
    created_at: str
    persona: str = "sre"
    step_label: str = "canary"
    done: bool = True
