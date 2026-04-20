"""PlanDoc — Plan-phase artifact written by eng-mgr (per /plan-eng-review).

Captures the architecture-lock + task list + dependencies + estimates output of
the Plan phase, per upstream gstack /plan-eng-review rubric. The Plan phase's
eng-mgr persona composes this from pm/ceo Think-phase inputs.

Stub-defeating constraints (Pitfall 8 prevention):
  - ``architecture_lock`` ≥120 chars (must describe the locked architectural choices)
  - ``tasks`` list must have ≥1 element (each PlanTask has its own stub defenses)
  - ``edge_cases`` requires ≥3 entries (forces eng-mgr to enumerate real cases)
  - ``test_plan`` ≥80 chars
  - PlanTask.description ≥20 chars and estimated_context_pct ∈ [1, 100]
"""

from typing import Literal

from pydantic import BaseModel, Field


class PlanTask(BaseModel):
    """One actionable task in the Plan-phase plan-doc."""

    task_id: str = Field(..., min_length=3)
    description: str = Field(..., min_length=20)
    owner_role: str = Field(..., min_length=2)
    depends_on: list[str] = Field(default_factory=list)
    estimated_context_pct: int = Field(..., ge=1, le=100)


class PlanDoc(BaseModel):
    """Plan-phase artifact. Written by eng-mgr after pm/ceo Think-phase verdict."""

    artifact_type: Literal["plan-doc"]
    architecture_lock: str = Field(..., min_length=120)
    tasks: list[PlanTask] = Field(..., min_length=1)
    edge_cases: list[str] = Field(..., min_length=3)
    test_plan: str = Field(..., min_length=80)
    plan_owner: str = Field(..., min_length=2)
    sprint_id: str
    created_at: str
