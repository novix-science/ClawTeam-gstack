---
phase: 00-foundation-upstream-rfc
plan: 02
subsystem: cli
tags: [doctor, diagnostics, ux, tooling]
requires: [00-01]
provides:
  - "Top-level `clawteam doctor` command with dual human/json output"
  - "Detection for Playwright, codex, ngrok, and watchdog"
  - "Per-OS install hints dispatched by sys.platform"
affects: [cli, onboarding, troubleshooting]
tech-stack:
  added: []
  patterns:
    - "checks dict + inner human formatter + shared _output dispatcher"
    - "CLI binary probes via shutil.which and python package probes via importlib.util.find_spec"
key-files:
  created:
    - tests/test_doctor.py
  modified:
    - clawteam/cli/commands.py
requirements-completed: [UX-08]
duration: 12 min
completed: 2026-04-16
---

# Phase 00 Plan 02: Doctor CLI Summary

Implemented top-level `clawteam doctor` diagnostics with missing-tool install guidance and JSON output support.

## Verification

- `.venv-sys/bin/python -m ruff check clawteam/cli/commands.py tests/test_doctor.py` -> pass
- `.venv-sys/bin/python -m pytest tests/test_doctor.py -q` -> `4 passed`

## Notes

- `doctor` is informational and exits `0` regardless of missing optional tools.
- Install hints follow the codebase platform convention: `darwin`, `win32`, else Linux.
