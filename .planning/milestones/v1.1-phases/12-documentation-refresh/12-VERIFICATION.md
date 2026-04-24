---
phase: 12
status: passed
verified: 2026-04-24
---

# Verification

Phase 12 passes docs verification.

## Results

- README primary flow now surfaces `go`, `status`, `answer`, and `stop`.
- Advanced README flow now contains `team spawn`, `launch`, and `sprint start`.
- README no longer contains stale `spawn-team` references.
- Event-driven wake architecture doc exists and covers wake kinds, nudge, and extension guidance.

## Commands

```bash
rg -n "clawteam go|clawteam status|clawteam answer|clawteam stop|Advanced Manual Flow|team spawn gstack|sprint start" README.md
rg -n "wake_agent|wake:task|wake:inbox|wake:phase|nudge|Adding a New Wake Kind" docs/architecture/event-driven-wake.md
rg -n "spawn-team" README.md
```
