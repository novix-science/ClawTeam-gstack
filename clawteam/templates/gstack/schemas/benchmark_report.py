"""Benchmark (Core Web Vitals) artifact (SKILL-18, D-10).

Written by /benchmark skill (Plan 05-09). lighthouse fields may be None in
curl-fallback mode or when Lighthouse returns partial JSON (D-15 adversarial).
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BenchmarkReport(BaseModel):
    """Benchmark artifact. Written by /benchmark handler (SKILL-18)."""

    artifact_type: Literal["benchmark-report"]
    benchmark_status: Literal["clean", "regression"]
    lcp_ms: float | None = Field(default=None, ge=0.0)
    fid_ms: float | None = Field(default=None, ge=0.0)
    cls_score: float | None = Field(default=None, ge=0.0)
    ttfb_ms: float = Field(..., ge=0.0)
    dom_loaded_ms: float = Field(..., ge=0.0)
    regression_flags: list[str] = Field(default_factory=list)
    measured_with: Literal["lighthouse", "curl"] = "lighthouse"
    sprint_id: str
    created_at: str
    persona: str = "sre"
    step_label: str = "benchmark"
    done: bool = True
