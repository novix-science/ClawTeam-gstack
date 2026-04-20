"""Six pydantic evidence schemas for gstack 7-phase artifacts.

Registered into Phase 2's EvidenceSchemaRegistry by GstackSprintPlugin.contribute_evidence_schemas
(03-07-PLAN). Each schema's ``artifact_type: Literal[...]`` becomes the discriminator key.

Task-1 ships DesignDoc + PlanDoc; Tasks 2-3 extend the barrel with TestReport, ReviewReport,
ShipNotes, Retro. The barrel is authored incrementally so each task's commit is self-consistent
and the pytest collection phase does not fail on un-created modules.
"""

from clawteam.templates.gstack.schemas.design_doc import DesignDoc
from clawteam.templates.gstack.schemas.plan_doc import PlanDoc

__all__ = ["DesignDoc", "PlanDoc"]
