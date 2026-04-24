---
phase: 10
task: "10-01"
title: "Attend/status polish"
status: complete
created: 2026-04-24
---

# Plan

## Scope

Implement the three Phase 10 UAT fixes in the narrowest production surfaces:

1. Render attend urgency as `1`, `2`, `3`, or `4` while preserving internal priority buckets.
2. Extract the first markdown H1 from question bodies and use it as `AttentionItem.title`.
3. Reconcile sprint `pending_question_ids` from `questions/*.md` minus `answers/*.md` before status/show serialization.

## Verification

- Add/adjust attend CLI regression tests for numeric urgency and H1 representative titles.
- Add sprint conductor regression coverage for read-side pending-question reconciliation and persistence.
- Run focused tests and Ruff on changed files.
