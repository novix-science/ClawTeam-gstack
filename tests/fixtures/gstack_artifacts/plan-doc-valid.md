---
artifact_type: plan-doc
architecture_lock: "Reuse Phase 2 EvidenceSchemaRegistry; no new abstraction. Reuse Phase 1 PhaseRegistry. Reuse Phase 0 TemplateDef pydantic loader. Wire 11-agent gstack template through existing spawn registry."
tasks:
  - task_id: task-01
    description: "Author gstack.toml with 11 agents and ceo as leader."
    owner_role: pm
    depends_on: []
    estimated_context_pct: 15
  - task_id: task-02
    description: "Implement six pydantic schemas for the 7-phase artifact types."
    owner_role: engineer
    depends_on: [task-01]
    estimated_context_pct: 25
edge_cases:
  - "Existing 6 templates must continue to spawn unchanged"
  - "Plugin must not load for non-gstack templates"
  - "Path traversal in role names rejected by validate_identifier"
test_plan: "pytest tests/test_gstack_template.py + tests/test_evidence_schemas.py + tests/test_template_regression_matrix.py — all green before Phase 3 ships."
plan_owner: eng-mgr
sprint_id: sprint-001
created_at: "2026-04-20T13:00:00Z"
---

# Plan-Doc body.
