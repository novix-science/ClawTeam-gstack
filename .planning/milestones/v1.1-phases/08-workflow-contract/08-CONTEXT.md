# Phase 8: Workflow Contract (state-machine teeth) - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Mode:** Smart discuss defaults accepted in text-mode fallback

<domain>
## Phase Boundary

This phase makes gstack phase advancement depend on concrete artifact requirements. It delivers a phase-to-artifact contract, a uniform artifact write command, plugin wiring into the conductor gate chain, and clear missing-artifact errors from `sprint advance`.

Out of scope: event-driven phase wakeups, attend/status UX, the full end-to-end sprint regression, and documentation refresh. Those are covered by Phases 9-12.

</domain>

<decisions>
## Implementation Decisions

### Contract Shape
- Use a gstack-owned `PHASE_REQUIREMENTS` mapping in `clawteam/templates/gstack/phase_contracts.py`, keyed by canonical phase names such as `think`, `plan`, `build`, `review`, `test`, `ship`, and `reflect`.
- Store required artifact names as filenames because `EvidenceGate` and `SprintState.artifacts` already operate on artifact names such as `test-report.md` and `ship-approval.md`.
- Keep the contract additive and plugin-scoped; non-gstack templates must continue to receive the existing permissive `EvidenceGate(artifact_names=list(state.artifacts.keys()))` behavior.
- Treat the first missing required artifact as the user-facing gate reason so agents can correct one precise failure before retrying.

### Artifact Write Command
- Add a Typer CLI command under the existing `clawteam artifact` surface if present, or create an `artifact_app` subcommand group in `clawteam/cli/commands.py` following the repo's existing Typer composition style.
- Accept artifact content from stdin to avoid shell-quoting issues and to match agent-friendly write workflows.
- Validate `artifact_type` through the existing frontmatter parsing plus `EvidenceSchemaRegistry`; reject missing or unregistered types before persisting.
- Persist into the sprint artifact store by updating `SprintState.artifacts[name]` and saving `state.json`, matching the conductor/EvidenceGate read path.
- Emit `ArtifactPersisted` on the event bus after a successful write; if the event type does not exist yet, add it to `clawteam/events/types.py` and register it using the existing event registry pattern.

### Conductor Wiring
- Extend `HarnessPlugin` with an optional `contribute_phase_requirements()` hook returning a `{phase: [artifact_name]}` mapping, defaulting to `{}`.
- Implement the hook in `GstackSprintPlugin` by returning `PHASE_REQUIREMENTS`.
- Have `PluginManager` aggregate phase requirements defensively, mirroring existing `get_plugin_gates()` and `get_verification_pairs()` behavior.
- Update `SprintConductor._build_gate_chain()` so the first `EvidenceGate` receives requirements for `state.current_phase` when a plugin manager is available; otherwise retain the current fallback.

### Tests and Error Contract
- Add focused tests around `EvidenceGate` / `SprintConductor._build_gate_chain()` proving missing phase-required artifacts block advancement before forced-progress or interaction gates matter.
- Add CLI tests for successful artifact write, invalid artifact type, missing sprint/team, and event emission.
- Keep tests hermetic with temporary `CLAWTEAM_DATA_DIR`, injected event bus/plugin manager where possible, and existing flat `tests/test_*.py` conventions.
- Preserve existing behavior for non-gstack or no-plugin-manager paths with explicit backwards-compatibility tests.

### the agent's Discretion
- The exact CLI option names and helper function boundaries are at the agent's discretion, provided the public command matches `clawteam artifact write <team> <sprint> <artifact_type>` and remains consistent with existing CLI patterns.
- The implementation may introduce small helper modules if that keeps `commands.py` from absorbing all artifact persistence logic.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `clawteam/sprint/conductor.py::SprintConductor._build_gate_chain()` currently constructs `EvidenceGate(artifact_names=list(state.artifacts.keys()))`, which is the toothless behavior this phase must replace for gstack.
- `clawteam/harness/evidence_gate.py::EvidenceGate` already handles presence checks, frontmatter parsing, schema lookup, stub checks, test command reruns, deploy URL checks, and phase artifact cap checks.
- `clawteam/harness/evidence_schemas.py` exposes `get_schema()`, `register_schema()`, and `list_registered()` for artifact type validation.
- `clawteam/plugins/gstack_sprint_plugin.py` already contributes phases, evidence schemas, skills, verification pairs, and gates; it is the correct home for gstack phase requirements.
- `clawteam/events/types.py` and `clawteam/events/bus.py` already define and register event dataclasses.
- `clawteam/sprint/state.py` owns `SprintState`, `load_sprint_state()`, and `save_sprint_state()`.

### Established Patterns
- Use additive hooks on `HarnessPlugin` with default empty returns to preserve backwards compatibility.
- Plugin manager aggregation should catch plugin exceptions, log warnings, and continue.
- CLI commands raise `typer.Exit` at the boundary and keep persistence/domain logic in helpers where practical.
- Tests use temporary data dirs and direct object construction rather than real tmux or external CLI processes.

### Integration Points
- `SprintConductor.__init__(plugin_manager=...)` already stores `self._plugin_manager`, so no new constructor dependency is needed.
- `PluginManager` already registers gstack plugin contributions and exposes aggregation accessors consumed by the conductor.
- `EvidenceGate` reason strings are already surfaced by `SprintConductor.advance_phase()`, so a named missing artifact message can be produced by passing the correct requirement list or by a small `EvidenceGate` reason improvement.

</code_context>

<specifics>
## Specific Ideas

- The milestone success criterion explicitly wants `GATE_BLOCKED: missing artifact 'delegation.json' for phase 'think'`-style specificity. The exact prefix can follow existing CLI output, but the missing artifact and phase must be present.
- The phase contract examples are: `think -> delegation.json`, `plan -> architecture-lock.md`, `build -> diff.patch`, `review -> review-report.md`, `test -> test-report.json`, `ship -> ship-approval.md`, `reflect -> retro.md`.
- The implementation should not solve artifact quality beyond existing EvidenceGate checks; this phase is about making required artifacts non-empty and enforced.

</specifics>

<deferred>
## Deferred Ideas

- Event-driven leader wakeup when all phase work is complete belongs to Phase 9.
- Full sprint lifecycle regression belongs to Phase 11.
- Documentation of the new architecture belongs to Phase 12.

</deferred>
