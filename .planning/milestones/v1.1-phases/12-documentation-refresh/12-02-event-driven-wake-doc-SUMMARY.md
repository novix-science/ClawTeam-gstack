---
phase: 12
task: "12-02"
title: "Event-driven wake architecture doc"
status: complete
completed: 2026-04-24
---

# Summary

Added `docs/architecture/event-driven-wake.md`.

The document explains:

- task, inbox, phase, and custom wake kinds;
- pane-map based tmux injection;
- wake debounce state;
- phase completion watcher behavior;
- nudge vs wake responsibilities;
- how to add a new wake kind.

## Verification

- `rg -n "wake_agent|wake:task|wake:inbox|wake:phase|nudge|Adding a New Wake Kind" docs/architecture/event-driven-wake.md`
