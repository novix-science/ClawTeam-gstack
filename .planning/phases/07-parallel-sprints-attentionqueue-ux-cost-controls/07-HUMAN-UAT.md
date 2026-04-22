---
status: partial
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
source: [07-VERIFICATION.md]
started: 2026-04-22T16:18:12Z
updated: 2026-04-22T16:18:12Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. 10-sprint load under realistic 5-minute duration cap and 4 GB RAM budget (ROADMAP SC #1)
expected: Real gstack team spawns 10 concurrent sprints via SprintConductor; memory + TaskStore + attention queue see no race conditions under steady-state 5-minute run; RSS stays under 4 GB
result: [pending]

### 2. Rate-limit-aware scheduling end-to-end with actual Anthropic TPM saturation (ROADMAP SC #9)
expected: When Anthropic TPM is saturated in a real run, new phase starts queue behind in-flight work instead of erroring; pause/resume across rate-limit windows is seamless
result: [pending]

### 3. Cache hit rate >50% on steady-state 10-sprint run (ROADMAP SC #8)
expected: Role prompts cached per session (90% discount on repeat reads), team memory core cached per team, per-sprint artifacts cached per sprint; cache hit rate > 50% measured in load test
result: [pending]

### 4. Digest-mode UX quality at real-user scale
expected: `clawteam attend --summary` surfaces useful "X sprints stalled >2h" narrative; human finds the digest actionable and not overwhelming at real 10+ sprint scale
result: [pending]

### 5. Attend CLI workflow end-to-end — open editor, write answer, queue re-refreshes
expected: User runs `clawteam attend`, picks a question, $EDITOR opens, user writes answer, saves, gate unblocks
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
