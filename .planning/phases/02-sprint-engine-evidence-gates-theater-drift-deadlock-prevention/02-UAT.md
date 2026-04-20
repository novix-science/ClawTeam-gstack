---
status: testing
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
source:
  - 02-01-SUMMARY.md through 02-13-SUMMARY.md
started: 2026-04-20T13:20:00Z
updated: 2026-04-20T13:20:00Z
---

## Current Test

[testing in progress]

## Tests

### 1. Full pytest suite regression check — no cross-plan merge failures
expected: |
  Run: uv run python -m pytest -q --tb=short
  Expected: all tests pass (count higher than Phase 01's 651 baseline), no new failures.
result: [pending]

### 2. Phase 0 BC regression matrix — 12/12
expected: |
  Run: uv run python -m pytest tests/test_template_regression_matrix.py -v
  Expected: 12 passed (6 templates × 2 tests). Opt-in Phase 2 primitives must not break existing templates.
result: [pending]

### 3. Sprint CLI end-to-end: start / list / status / show / pause / resume
expected: |
  Sequence against a test team `p02-uat-sprint`:
    clawteam team spawn-team p02-uat-sprint --leader-type tech-lead
    SID=$(clawteam sprint start --team p02-uat-sprint --goal "UAT check" --json | python -c "import sys,json; print(json.load(sys.stdin)['sprint_id'])")
    clawteam sprint list p02-uat-sprint
    clawteam sprint status p02-uat-sprint $SID
    clawteam sprint show p02-uat-sprint $SID
    clawteam sprint pause p02-uat-sprint $SID
    clawteam sprint resume p02-uat-sprint $SID
    clawteam team cleanup p02-uat-sprint --force
  Expected: every command returns 0; list shows the sprint; pause/resume succeed without error.
result: [pending]

### 4. Sprint pause survives process boundary
expected: |
  After pausing (Test 3), the state file at ~/.clawteam/teams/p02-uat-sprint/sprints/<id>/state.json
  exists and contains current_phase + phase_history. Re-reading in a fresh Python process
  must produce the same SprintState content (no in-memory-only state).
result: [pending]

### 5. --json envelope on sprint commands
expected: |
  Run: clawteam sprint list <team> --json
  Expected: stdout parses as JSON; contains an envelope with sprints array.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps

[none yet]
