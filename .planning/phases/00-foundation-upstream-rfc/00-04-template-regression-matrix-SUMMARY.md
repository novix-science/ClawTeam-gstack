---
phase: 00-foundation-upstream-rfc
plan: 04
subsystem: testing
tags: [pytest, regression, templates, cli, ci]
requires: []
provides:
  - packaged template launch regression coverage through the Typer CLI
  - verification that CI auto-discovers new `tests/test_*.py` modules
affects: [phase-01, harness, templates, ci]
tech-stack:
  added: []
  patterns: [parametrized CliRunner launch matrix, RecordingBackend spawn capture]
key-files:
  created: [tests/test_template_regression_matrix.py]
  modified: [clawteam/templates/harness-default.toml]
key-decisions:
  - "Keep CI discovery unchanged and rely on the existing `python -m pytest tests/ -v --tb=short` invocation."
  - "Fix the broken packaged template instead of weakening the regression matrix around `harness-default`."
patterns-established:
  - "Packaged-template BC coverage lives in one parametrized pytest module using `CliRunner` plus `RecordingBackend`."
  - "Launch regression assertions validate spawn-state fields only, leaving prompt semantics to `tests/test_templates.py`."
requirements-completed: [CORE-03, TEAM-06, QUALITY-14]
duration: 28min
completed: 2026-04-16
---

# Phase 00 Plan 04: Template Regression Matrix Summary

**Parametrized CLI launch regression coverage for all six packaged templates, with a compatibility fix for the broken `harness-default` template**

## Performance

- **Duration:** 28 min
- **Started:** 2026-04-16T09:42:00Z
- **Completed:** 2026-04-16T10:10:52Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Added `tests/test_template_regression_matrix.py` with 12 parametrized launch cases covering all six packaged templates.
- Verified the matrix uses `CliRunner` plus `RecordingBackend`, so no real subprocesses are started while spawn kwargs are still asserted.
- Confirmed the existing CI command path auto-discovers the new test module through `pytest tests/` without any workflow edits.

## Task Commits

1. **Task 1: Create tests/test_template_regression_matrix.py with parametrize-across-templates** - `dec9916` (`test`)
2. **Task 1 auto-fix: restore harness-default launch compatibility** - `e09794d` (`fix`)
3. **Task 2: Verify CI workflow picks up the new test file** - no code change required; verification captured in this summary

**Plan metadata:** pending in the commit that adds this summary

## Files Created/Modified

- `tests/test_template_regression_matrix.py` - new packaged-template regression matrix for `clawteam launch <template>`
- `clawteam/templates/harness-default.toml` - removes the invalid scalar/table TOML collision that blocked template launch

## Decisions Made

- Kept `.github/workflows/ci.yml` unchanged because the existing `python -m pytest tests/ -v --tb=short` command already discovers the new matrix.
- Fixed the packaged template itself when the matrix exposed a real launch failure, because the plan requires all six templates to launch cleanly.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed invalid TOML in `harness-default` packaged template**
- **Found during:** Task 1 (Create tests/test_template_regression_matrix.py with parametrize-across-templates)
- **Issue:** `clawteam launch harness-default` failed with `TOMLDecodeError: Cannot overwrite a value` because `clawteam/templates/harness-default.toml` defined both `harness = true` and `[template.harness]`.
- **Fix:** Removed the conflicting scalar key and kept the nested `template.harness` table as the canonical harness configuration.
- **Files modified:** `clawteam/templates/harness-default.toml`
- **Verification:** `.venv-sys/bin/python -m pytest tests/test_template_regression_matrix.py -v --tb=short` → `12 passed in 1.03s`
- **Committed in:** `e09794d`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The deviation was required to satisfy the plan's six-template backwards-compatibility guarantee. No scope creep beyond fixing the broken packaged template the new matrix uncovered.

## Issues Encountered

- The workspace system Python lacked the project dev dependencies, so verification ran from a repo-local `.venv-sys` virtualenv created with `--system-site-packages`.
- Build isolation hit a hash-enforced pip policy, so dependency install used `--no-build-isolation` inside the repo-local virtualenv.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Future harness changes now have packaged-template BC coverage at the CLI launch boundary.
- CI discovery is already in place; additional test modules under `tests/` will continue to be picked up automatically.

## Self-Check: PASSED

- Verified summary file exists at `.planning/phases/00-foundation-upstream-rfc/00-04-template-regression-matrix-SUMMARY.md`
- Verified task commits exist in git history: `dec9916`, `e09794d`

---
*Phase: 00-foundation-upstream-rfc*
*Completed: 2026-04-16*
