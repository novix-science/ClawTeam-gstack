---
phase: 12
task: "12-01"
title: "README primary flow"
status: complete
completed: 2026-04-24
---

# Summary

README Quick Start now documents the v1.1 solo UX first:

- `clawteam go "Build X"`
- `clawteam status`
- `clawteam answer`
- `clawteam stop`

The lower-level `team spawn`, `launch`, `sprint start`, and `spawn` commands are now presented as the advanced manual flow. The command reference also lists the solo commands before team/sprint primitives.

## Verification

- `rg -n "clawteam go|clawteam status|clawteam answer|clawteam stop|Advanced Manual Flow|team spawn gstack|sprint start" README.md`
- `rg -n "spawn-team" README.md`
