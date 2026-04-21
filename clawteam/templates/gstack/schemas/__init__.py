"""Ten pydantic evidence schemas for gstack 7-phase artifacts.

Registered into Phase 2's EvidenceSchemaRegistry by GstackSprintPlugin.contribute_evidence_schemas
(03-07 + 05-02 wiring). Each schema's ``artifact_type: Literal[...]`` becomes the discriminator key.

One-statement import contract:
    from clawteam.templates.gstack.schemas import (
        DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro,
        # Phase 5 Plan 05-02:
        DeployNotes, CanaryReport, BenchmarkReport, CodexReview,
    )
"""

from clawteam.templates.gstack.schemas.benchmark_report import BenchmarkReport
from clawteam.templates.gstack.schemas.canary_report import CanaryReport
from clawteam.templates.gstack.schemas.codex_review import CodexReview
from clawteam.templates.gstack.schemas.deploy_notes import DeployNotes
from clawteam.templates.gstack.schemas.design_doc import DesignDoc
from clawteam.templates.gstack.schemas.plan_doc import PlanDoc
from clawteam.templates.gstack.schemas.retro import Retro
from clawteam.templates.gstack.schemas.review_report import ReviewReport
from clawteam.templates.gstack.schemas.ship_notes import ShipNotes
from clawteam.templates.gstack.schemas.test_report import TestReport

__all__ = [
    "DesignDoc",
    "PlanDoc",
    "TestReport",
    "ReviewReport",
    "ShipNotes",
    "Retro",
    # Phase 5 Plan 05-02:
    "DeployNotes",
    "CanaryReport",
    "BenchmarkReport",
    "CodexReview",
]
