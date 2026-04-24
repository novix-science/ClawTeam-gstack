---
phase: 12
task: "12-02"
title: "Event-driven wake architecture doc"
status: complete
created: 2026-04-24
---

# Plan

Create `docs/architecture/event-driven-wake.md` covering:

1. `wake_agent()` and the task/inbox/phase/custom wake kinds.
2. tmux pane-map lookup and `send-keys` injection.
3. wake debounce files and best-effort behavior.
4. `PhaseCompletionWatcher` task/artifact checks.
5. nudge architecture and the tmux `alert-silence` hook.
6. Steps for adding a new wake kind.

## Verification

- Grep the doc for wake kinds, nudge, and extension guidance.
