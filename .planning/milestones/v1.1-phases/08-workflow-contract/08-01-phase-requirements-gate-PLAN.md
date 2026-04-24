---
phase: 08-workflow-contract
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - clawteam/plugins/base.py
  - clawteam/plugins/manager.py
  - clawteam/plugins/gstack_sprint_plugin.py
  - clawteam/templates/gstack/phase_contracts.py
  - clawteam/sprint/conductor.py
  - clawteam/harness/evidence_gate.py
  - tests/test_gstack_plugin.py
  - tests/test_sprint_conductor.py
requirements:
  - RELI-01
  - RELI-03
  - RELI-04
must_haves:
  truths:
    - "GstackSprintPlugin contributes a phase -> required artifact mapping"
    - "PluginManager aggregates phase requirements defensively"
    - "SprintConductor EvidenceGate receives current-phase required artifacts when plugin_manager is present"
    - "Missing required artifact errors name the missing artifact and phase"
  artifacts:
    - path: clawteam/templates/gstack/phase_contracts.py
      provides: "PHASE_REQUIREMENTS"
      contains: "PHASE_REQUIREMENTS"
    - path: clawteam/sprint/conductor.py
      provides: "phase requirement wiring into _build_gate_chain"
      contains: "get_phase_requirements"
---

<objective>
Give gstack's sprint phases concrete artifact requirements and wire them into the existing EvidenceGate path without changing non-gstack behavior.
</objective>

<tasks>
- Add `HarnessPlugin.contribute_phase_requirements()` with empty default.
- Add `PluginManager.get_phase_requirements(phase)`.
- Add `clawteam/templates/gstack/phase_contracts.py::PHASE_REQUIREMENTS`.
- Return that mapping from `GstackSprintPlugin`.
- Update `SprintConductor._build_gate_chain()` to pass current-phase requirements into the first `EvidenceGate`.
- Improve missing-artifact reason text so it includes `missing artifact '<name>' for phase '<phase>'`.
- Add focused tests for plugin contribution, manager aggregation, conductor wiring, and no-plugin-manager backwards compatibility.
</tasks>
