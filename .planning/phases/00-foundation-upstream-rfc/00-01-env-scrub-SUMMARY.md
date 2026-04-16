---
phase: 00-foundation-upstream-rfc
plan: 01
subsystem: security
tags: [secrets, hooks, env, testing]
requires: []
provides:
  - "Pure env deny-filter helper at clawteam/secrets.py"
  - "Hook env snapshot extraction with scrubbed shell env handoff"
  - "Unit + integration coverage proving parent secrets do not leak into hook subprocess env"
affects: [event-hooks, security-hardening]
tech-stack:
  added: []
  patterns:
    - "Module-level compiled deny regex + pure transform helper"
    - "Shell-hook env built via helper and scrubbed before subprocess.run"
key-files:
  created:
    - clawteam/secrets.py
  modified:
    - clawteam/events/hooks.py
    - tests/test_env_scrub.py
requirements-completed: [QUALITY-15]
duration: 20 min
completed: 2026-04-16
---

# Phase 00 Plan 01: Env Scrub Summary

Implemented secret-shaped env redaction for shell hooks by introducing `scrub_env`, extracting `_env_snapshot(event)` in hooks, and scrubbing the snapshot before `subprocess.run`.

## Task Commits

1. `58438b1` `test(00-01): add failing env scrub tests`
2. `c8ec95f` `feat(00-01): scrub shell hook env snapshots`

## Verification

- `python -m pytest tests/test_env_scrub.py -q` -> `31 passed`

## Notes

- Hook metadata env values (`CLAWTEAM_*`, `OH_*`) remain available because deny matching is key-based and does not match those names.
- No shared orchestrator files were modified for this plan.
