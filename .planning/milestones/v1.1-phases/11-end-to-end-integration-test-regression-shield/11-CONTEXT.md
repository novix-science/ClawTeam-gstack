---
phase: 11
title: "End-to-End Integration Test (regression shield)"
status: complete
created: 2026-04-24
---

# Phase 11 Context

## Goal

Add one deterministic subprocess-backed integration test that exercises the full gstack sprint lifecycle and prevents another manual-UAT-only regression loop.

## Requirement Covered

- TEST-01: subprocess backend launch with a scripted `claude` mock, complete start-to-reflect lifecycle, six phase transitions, seven persisted artifacts, wake coverage, and final completed state.

## Implementation Notes

- The event bus is process-local, so the test observes subprocess `PhaseTransition` events through the supported shell-hook configuration path.
- The subprocess backend is exercised through `clawteam launch gstack --backend subprocess` with a fake `claude` executable on `PATH`.
- Wake assertions use a fake `tmux` executable plus a persisted pane map so `wake_agent()` follows the real lookup and `send-keys` flow without requiring a live tmux server.
