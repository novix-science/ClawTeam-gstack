---
phase: 10
task: "10-01"
title: "Attend/status polish"
status: complete
completed: 2026-04-24
---

# Summary

Implemented Phase 10 UX polish:

- `clawteam attend` now renders urgency as numeric levels (`1` low through `4` critical) instead of static labels such as `norm`.
- Attention queue parsing now uses the first markdown H1 from the question body as the item title, falling back to frontmatter title or question id when no H1 exists.
- Sprint status/show payload generation now reconciles `pending_question_ids` against unanswered question files and persists corrections when state is stale.

## Files Changed

- `clawteam/attention/queue.py`
- `clawteam/cli/commands.py`
- `clawteam/sprint/conductor.py`
- `tests/attention/test_attend_cli.py`
- `tests/test_sprint_conductor.py`

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/attention/test_attend_cli.py tests/attention/test_digest.py tests/test_sprint_conductor.py -q`
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check clawteam/attention/queue.py clawteam/cli/commands.py clawteam/sprint/conductor.py tests/attention/test_attend_cli.py tests/test_sprint_conductor.py`
