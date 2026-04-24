---
phase: 09-event-driven-coordination
plan: 01
type: execute
wave: 1
depends_on: [08-01]
requirements:
  - EVT-01
  - EVT-02
  - EVT-03
  - EVT-04
---

# Phase 9 Plan 01

Implement event-driven phase completion.

Tasks:
- Confirm `TaskCompleted` is emitted by `task update`.
- Add `PhaseCompletionWatcher`.
- Extend `wake_agent(kind="phase")`.
- Register the watcher in the `task update` CLI path before task update emits.
- Add tests for ready phase wake, missing artifact suppression, wake formatting, and CLI registration.
