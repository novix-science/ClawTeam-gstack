---
phase: 08-workflow-contract
plan: 02
type: execute
wave: 1
depends_on: [08-01]
files_modified:
  - clawteam/events/types.py
  - clawteam/cli/commands.py
  - tests/test_cli_commands.py
requirements:
  - RELI-02
must_haves:
  truths:
    - "clawteam artifact write <team> <sprint> <artifact_type> reads artifact body from stdin"
    - "artifact write validates frontmatter artifact_type through EvidenceSchemaRegistry"
    - "successful write updates SprintState.artifacts and emits ArtifactPersisted"
    - "invalid artifact_type exits non-zero without mutating state"
  artifacts:
    - path: clawteam/events/types.py
      provides: "ArtifactPersisted event"
      contains: "class ArtifactPersisted"
    - path: clawteam/cli/commands.py
      provides: "artifact write command"
      contains: "artifact_app"
---

<objective>
Give agents one uniform CLI path to persist sprint artifacts into the state path consumed by EvidenceGate.
</objective>

<tasks>
- Add `ArtifactPersisted` event type and register it.
- Add an `artifact` Typer sub-app with `write <team> <sprint> <artifact_type>`.
- Parse stdin artifact content with existing frontmatter parser.
- Validate CLI `artifact_type` matches frontmatter and is registered.
- Load the sprint by id/prefix, update `state.artifacts[artifact_name]`, save state, and emit the event.
- Add CLI tests for success, mismatched type, unregistered type, and missing sprint.
</tasks>
