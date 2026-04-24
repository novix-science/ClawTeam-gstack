---
created: 2026-04-24T11:27:07Z
title: Workflow contract 3-in-1 refactor (artifacts + events + integration test)
area: sprint-conductor
files:
  - clawteam/sprint/conductor.py
  - clawteam/templates/gstack/phase_contracts.py (new)
  - clawteam/harness/evidence_gate.py
  - clawteam/events/types.py
  - tests/integration/test_gstack_sprint_end_to_end.py (new)
---

## Problem

Post-v1.0 UAT revealed that bug-fixing was whack-a-mole: every manual
test session surfaced new symptoms (CEO not delegating, sprint stuck in
`think`, agents polling, skills not invokable, etc.). Chat dialogue on
2026-04-23 diagnosed three architectural root causes that together
explain the remaining ~60% of un-fixed bugs:

**Class A — State machine has no teeth.**
`SprintConductor.advance_phase` runs the gate chain, but gstack.toml
never registers any artifact_types. `EvidenceGate(artifact_names=[])`
short-circuits to True. Result: every phase-advance passes, CEO has no
concrete signal of "phase done," and the 7-phase progression is
nominal only.

**Class B — Feedback loop is open.**
When an agent runs `clawteam task update <id> --status completed`,
nothing fires a `TaskCompleted` event. The conductor has no subscriber
to detect "all tasks for phase X are done → wake CEO to advance."
CEO is told in its role card to advance, but has no trigger; it
either idles indefinitely or blindly calls `sprint advance` hoping
for the best.

**Class C — No end-to-end test.**
pytest has 1,740+ unit tests (single function → output), but zero
integration tests that spawn a real multi-agent sprint and assert
"CEO delegates → agents complete → phase advances → sprint reaches
ship." Every regression has to be caught by human manual testing.

Bugs already fixed by prior commits that would have been caught by a
hypothetical integration test:
  - bb18c8e  spawn trust confirmer burning 30s per agent
  - 8090af7  launch not injecting role prompt into system_prompt
  - c254315  team spawn → launch failing with "Team already exists"
  - 40c326f  CEO self-implementing instead of delegating
  - 0c3aa2e  agents polling instead of receiving wakes
  - bd5b26d  sprint advance missing from CLI

All six are instances of "the happy path from goal → shipped code was
never exercised end-to-end."

## Solution

Three-in-one refactor landing together as one commit wave:

### 1. PHASE_REQUIREMENTS artifact registry (Class A)

Create `clawteam/templates/gstack/phase_contracts.py`:
```python
PHASE_REQUIREMENTS = {
    "think":   ["delegation.json"],
    "plan":    ["architecture-lock.md"],
    "build":   ["diff.patch"],
    "review":  ["review-report.md"],
    "test":    ["test-report.json"],
    "ship":    ["ship-approval.md"],
    "reflect": ["retro.md"],
}
```

- Wire `GstackSprintPlugin.contribute_phase_requirements()` so conductor
  passes the right list to `EvidenceGate` per phase
- Add `clawteam artifact write <team> <sprint> <type>` CLI so agents
  have a uniform way to produce the required artifact
- Agents' role cards get a line: "Phase X requires artifact Y. Write
  it via `clawteam artifact write`."

### 2. TaskCompleted → PhaseCompletionWatcher (Class B)

- Emit `TaskCompleted(team, sprint_id, owner, task_id)` from
  `task_update` CLI when status flips to `completed`
- New `clawteam/sprint/phase_completion_watcher.py` subscribes:
  - On TaskCompleted, check if all tasks with status=completed for
    current phase match the expected contributors
  - If yes, fire `wake_agent(team, leader_role, kind="phase")` →
    "[wake:phase] All tasks for {phase} completed. Run
    `clawteam sprint advance` when artifact is written."
- Wire watcher to the session's event bus at team-spawn time
- Add third wake kind to `clawteam/wake.py` (the infrastructure is there)

### 3. End-to-end integration test (Class C)

`tests/integration/test_gstack_sprint_end_to_end.py`:
- Spawn a test team (file backend, no tmux) — use `subprocess` backend
  for deterministic test behavior
- Mock `claude` CLI with a scripted-response harness: reads agent name
  + system prompt + user prompt, returns canned output matching the
  expected agent behavior (CEO delegates, designer produces mock spec,
  engineer commits stub code, etc.)
- Assert sequence: think → plan → build → review → test → ship → reflect
- Assert side effects: 7 PhaseTransition events emitted, 7 artifacts
  persisted, 6 sprint advances, all 11 agents received at least one wake

Estimated size:
  phase_contracts.py            ~40 LOC
  EvidenceGate wiring           ~20 LOC
  artifact write CLI            ~60 LOC
  TaskCompleted emit            ~10 LOC
  PhaseCompletionWatcher        ~120 LOC
  wake.py phase kind            ~20 LOC
  role card updates             ~30 LOC (per role)
  integration test              ~250 LOC
  ───────────────────────────────────
  Total                         ~550 LOC

Risk: medium. Mock claude behavior needs to faithfully simulate agent
prompt comprehension, which is the hard part. Start with CEO-only mock
to verify the delegation path, then expand.

Future-proofing: once the integration test exists, any new prompt
change / role card edit / gate addition can be regression-tested in
CI instead of being caught by a user manually running `clawteam go`.

## Links

- Chat context: 2026-04-23 session — see git log between commits
  bd5b26d (sprint advance CLI) and today
- Related: .planning/backlog/v1.0-post-uat-fixes.md (6 post-close fixes
  all instances of the same class-C gap)
- Related: .planning/RETROSPECTIVE.md — "What Was Inefficient" lesson
  about missing E2E coverage
