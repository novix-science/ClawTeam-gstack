---
phase: 11
task: "11-01"
title: "Gstack subprocess lifecycle E2E"
status: complete
created: 2026-04-24
---

# Plan

## Scope

Create `tests/integration/test_gstack_sprint_end_to_end.py` covering:

1. Launching a gstack team through the real subprocess backend.
2. Scripted `claude` and `tmux` mocks to avoid external CLI dependencies.
3. CLI-driven sprint start, artifact writes, and phase advances through the seven gstack phases.
4. Assertions for six non-initial `PhaseTransition` events, seven final artifacts, wake delivery to every agent role, and completed sprint state.

## Verification

- Run the new integration test directly.
- Run the new integration test with the Phase 10 focused regression set.
- Run Ruff on the new test file.
