---
phase: 11
task: "11-01"
title: "Gstack subprocess lifecycle E2E"
status: complete
completed: 2026-04-24
---

# Summary

Added `tests/integration/test_gstack_sprint_end_to_end.py`.

The test:

- launches the gstack roster with `--backend subprocess` and a scripted `claude` executable mock;
- verifies all 11 expected agents are spawned;
- uses a fake `tmux` plus pane map to assert every agent receives at least one wake;
- starts a sprint, writes the seven required phase artifacts, advances through think -> reflect, and completes the sprint;
- captures cross-process `PhaseTransition` events through a shell hook and asserts the six non-initial transitions;
- asserts final sprint state is `completed` and final persisted artifacts are exactly the seven required artifacts.

## Verification

- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/integration/test_gstack_sprint_end_to_end.py -q`
- `UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/integration/test_gstack_sprint_end_to_end.py tests/attention/test_attend_cli.py tests/attention/test_digest.py tests/test_sprint_conductor.py -q`
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/integration/test_gstack_sprint_end_to_end.py`
