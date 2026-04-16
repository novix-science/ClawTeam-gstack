---
phase: 00-foundation-upstream-rfc
plan: 03
subsystem: config
tags: [config, pydantic, model-profile, testing]
requires: []
provides:
  - "ClawTeamConfig.default_model_profile scaffolded with a balanced default"
  - "Regression coverage for backward-compatible config loading and env-ignore behavior"
affects: [phase-03-gstack-template, phase-07-cost-observability, config-resolution]
tech-stack:
  added: []
  patterns:
    - "Config schema fields can be added additively with pydantic defaults for backward compatibility"
    - "Model profile opt-in stays file/CLI only until later resolver phases"
key-files:
  created: []
  modified:
    - clawteam/config.py
    - tests/test_config.py
key-decisions:
  - "Kept default_model_profile out of get_effective env_map to prevent silent quality promotion from shell state."
  - "Left default_model_profile as a plain str without Literal validation; profile validation remains deferred to later resolver work."
patterns-established:
  - "Config resolution may intentionally diverge from adjacent fields when threat-model constraints require stricter precedence."
requirements-completed: [TEAM-06]
duration: 4 min
completed: 2026-04-16
---

# Phase 00 Plan 03: Default Model Profile Summary

**Balanced-by-default model profile scaffolding with backward-compatible config loading and an env-override regression guard**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-16T10:00:00Z
- **Completed:** 2026-04-16T10:04:07Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments

- Added `default_model_profile: str = "balanced"` next to `default_profile` on `ClawTeamConfig`.
- Documented and preserved the deliberate omission of `default_model_profile` from `get_effective()` env overrides.
- Appended a `TestDefaultModelProfile` suite covering defaults, model fields, backward-compatible loads, roundtrip persistence, and ignored env vars.

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: add failing default model profile tests** - `fc7d499` (`test`)
2. **Task 1 GREEN: implement default model profile scaffold** - `cdbe179` (`feat`)

**Plan metadata:** committed separately in the final docs commit for this plan.

## Files Created/Modified

- `clawteam/config.py` - Adds the `default_model_profile` field and explains why env overrides are intentionally unsupported for it.
- `tests/test_config.py` - Appends `TestDefaultModelProfile` coverage for the balanced default, backward compatibility, roundtrip behavior, and Pitfall #12 regression protection.

## Decisions Made

- Followed the objective, threat model, and success criteria rather than the stale task-body env-map instruction. The final implementation intentionally omits any `CLAWTEAM_DEFAULT_MODEL_PROFILE` resolution path.
- Kept the field type as `str` instead of introducing enum validation. Phase 0 only establishes the config resolution path; profile validation and model mapping remain future work.

## Deviations from Plan

None in shipped code. A stale instruction inside the task body said to add an env-map entry, but the objective, threat model, and success criteria superseded it and required the opposite behavior.

## Issues Encountered

- `ruff` was not available on the base PATH.
- `uv run ruff check clawteam/config.py tests/test_config.py` attempted to provision a local environment but failed fetching `pydantic-core` from PyPI after retries. `pytest tests/test_config.py -v --tb=short` and the Python smoke checks passed, so behavioral verification completed; lint could not be re-run due tool bootstrap/network failure rather than a reported lint error.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 can consume `default_model_profile` from config without breaking existing config files.
- The no-env-override guard is now covered by tests, reducing the risk of accidental cost-profile promotion in later resolver work.

## Known Stubs

None.

## Self-Check

PASSED

- Summary file exists at `.planning/phases/00-foundation-upstream-rfc/00-03-SUMMARY.md`.
- Verified task commits exist in git history: `fc7d499`, `cdbe179`.

---
*Phase: 00-foundation-upstream-rfc*
*Completed: 2026-04-16*
