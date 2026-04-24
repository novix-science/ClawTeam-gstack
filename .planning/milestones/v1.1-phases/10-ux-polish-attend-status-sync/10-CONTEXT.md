---
phase: 10
title: "UX Polish (attend / status sync)"
status: complete
created: 2026-04-24
---

# Phase 10 Context

## Goal

Fix attend and sprint-status polish issues discovered during UAT so pending work is represented accurately in digest and status views.

## Requirements Covered

- UX-01: `clawteam attend` shows numeric urgency levels from question frontmatter using the 1=low to 4=critical scale.
- UX-02: `clawteam attend --summary` uses the first H1 in the question body as the representative title.
- UX-03: sprint status/show read paths reconcile `pending_question_ids` with unanswered question files.

## Implementation Notes

- Keep existing priority math unchanged; the user-facing urgency display is a presentation mapping over the current internal buckets.
- Prefer one-shot reconciliation in sprint read-side helpers over a long-running watcher for this polish phase.
- Persist reconciled pending-question IDs only when the filesystem-derived set differs from state.
