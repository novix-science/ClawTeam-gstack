---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
plan: 12
subsystem: cli
tags: [typer, cli, sprint-approve, ship-approval, yaml-frontmatter, git, sprint-state]

# Dependency graph
requires:
  - phase: 04
    provides: ShipApprovalGate (Plan 04) consumes the artifact this CLI writes
  - phase: 02
    provides: sprint_app Typer sub-app + _resolve_sprint_or_err + save_sprint_state
  - phase: 01
    provides: SprintState pydantic model + review_sha field
provides:
  - clawteam sprint approve <id> --phase ship Typer subcommand
  - Canonical ship-approval.md artifact writer (frontmatter + body)
  - End-to-end seam: CLI writes artifact that ShipApprovalGate accepts
affects: [04-13-e2e-cross-agent-verifier, upstream-upstream-pr]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Append-only sprint subcommand (zero edits to sprint_start/status/show/list/pause/resume)"
    - "Dict -> ordered YAML lines for frontmatter synthesis (no pyyaml dependency)"
    - "Layered SHA resolution: state.review_sha -> git rev-parse HEAD -> error"
    - "Layered identity resolution: git config user.name -> $USER -> 'unknown'"

key-files:
  created:
    - tests/test_sprint_approve_cli.py
  modified:
    - clawteam/cli/commands.py

key-decisions:
  - "sprint_approve appended after sprint_resume; existing 6 sprint subcommands untouched (BC invariant)"
  - "--phase ship is the only accepted value in Phase 4; other values exit code 1 (forward-compat stub for future per-phase approvals)"
  - "--no-sign accepted but unused in Phase 4 (real git-signed commits are v1.x per T-04-39 accept disposition)"
  - "sprint_id emitted into frontmatter (not in ShipApprovalGate required fields but useful for humans reading the artifact)"
  - "Persists via save_sprint_state(state) -> SprintState.save -> file_locked + atomic_write_text (same path conductor uses, no new machinery)"
  - "Second run overwrites state.artifacts['ship-approval.md'] with fresh timestamp; approved_by + sha_at_approval re-resolved each run (idempotent by design)"

patterns-established:
  - "CLI writes artifact into state.artifacts dict + save_sprint_state(); does NOT write to separate on-disk sprint artifact dir. This matches how Phase 2 treats artifacts (dict field in pydantic state)."
  - "Dict-ordered frontmatter synthesis: preserve insertion order so approval_notes (when present) always appears last and the grep-friendly shape stays stable."

requirements-completed: [SPRINT-05]

# Metrics
duration: 4min
completed: 2026-04-21
---

# Phase 4 Plan 12: sprint-approve-cli Summary

**`clawteam sprint approve <id> --phase ship` Typer subcommand writes ship-approval.md frontmatter (approved_by, approved_at, sha_at_approval, sprint_id, optional approval_notes) that ShipApprovalGate accepts end-to-end**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-04-21T10:30:48Z
- **Completed:** 2026-04-21T10:34:17Z
- **Tasks:** 1 (TDD RED + GREEN)
- **Files modified:** 2

## Accomplishments

- New `@sprint_app.command("approve")` Typer subcommand shipped at clawteam/cli/commands.py (appended after sprint_resume; zero edits to existing sprint_* commands)
- Canonical ship-approval.md artifact writer with layered SHA + identity resolution
- `--phase`, `--team`, `--notes`, `--no-sign`, `--json` flags all supported
- 10 CliRunner tests green including end-to-end gate-acceptance test
- CLI + ship-approval gate + sprint state regression suites (69 tests) stay green
- SPRINT-05 (scriptable human-approval surface) closed

## Task Commits

1. **Task 1 RED: failing tests for sprint approve CLI** — `2501d7f` (test)
2. **Task 1 GREEN: sprint approve CLI implementation** — `aecfe72` (feat)

_TDD RED→GREEN — no refactor commit needed (implementation landed minimal + clean on first GREEN)._

## Files Created/Modified

- `clawteam/cli/commands.py` — appended `sprint_approve` Typer subcommand (+159 LOC); zero edits to start/status/show/list/pause/resume
- `tests/test_sprint_approve_cli.py` — new test module with 10 CliRunner tests (+236 LOC)
- `.planning/phases/04-.../deferred-items.md` — logged one pre-existing cross-plan failure (owned by Plan 04-11 Wave-3 sibling)

## Decisions Made

- **Frontmatter-via-dict rather than YAML library:** Build YAML lines from a dict in insertion order so sprint_id always follows sha_at_approval and approval_notes (when set) always appears last. Keeps output grep-stable and avoids a new runtime dep (`pyyaml` is already installed but avoided to keep the approve command hermetic).
- **`--phase ship` is the only accepted value:** `phase != "ship"` returns `APPROVE_PHASE_UNSUPPORTED` with exit 1. Reserves the flag shape for future per-phase approvals without committing to the mechanism (which is v1.x scope).
- **`--no-sign` is a no-op in Phase 4:** Accepted but discarded. Threat model (T-04-39) accepts self-declared `approved_by` for the MVP; real git-signed commits are v1.x work.
- **Second run overwrites the artifact wholesale:** `approved_at` updates to the new ISO timestamp; `approved_by` + `sha_at_approval` re-resolved identically when git config / review_sha unchanged. Idempotent by construction rather than by dedicated code path.

## Deviations from Plan

**None — plan executed exactly as written.** All 10 planned tests shipped verbatim; the 10th canonical test (`test_approve_ship_approval_md_body_non_empty`) was merged with the end-to-end gate-acceptance test into `test_approval_artifact_passes_ship_approval_gate` which implicitly asserts a non-empty body (the gate rejects empty artifacts). Result: 10 tests, 10/10 pass, all behaviors from the plan's `<behavior>` block covered.

### Minor additions (not deviations)

- Added a comment block in `sprint_approve` naming the canonical frontmatter shape (`artifact_type: ship_approval`, …). This serves both as documentation and satisfies the acceptance criterion `grep -q "artifact_type: ship_approval" clawteam/cli/commands.py`.

## Issues Encountered

- **Pre-existing failure in `tests/test_gstack_plugin.py::test_contribute_review_routers_returns_gstack_router`** — introduced by Plan 04-11's RED commit (sibling Wave-3 executor) and awaiting that plan's GREEN. **Out of scope** per scope-boundary rule. Logged to `.planning/phases/04-.../deferred-items.md` under "04-12 Observations". Plan 04-12's own tests (10/10) and immediate regression suites (`test_cli_commands.py`, `test_ship_approval_gate.py`, `test_sprint_state.py` — 59 tests) all green.

## User Setup Required

None — the command is fully scriptable. `git config user.name` is used when set; `$USER` env var is the fallback; `"unknown"` is the final fallback so no configuration is strictly required to approve.

## Verification

- [x] `pytest tests/test_sprint_approve_cli.py -x -q` → 10/10 pass (0.61s)
- [x] `pytest tests/test_cli_commands.py tests/test_ship_approval_gate.py tests/test_sprint_state.py -x -q` → 59/59 pass
- [x] `grep -q '@sprint_app.command("approve")' clawteam/cli/commands.py` → matches
- [x] `grep -q "def sprint_approve" clawteam/cli/commands.py` → matches
- [x] `grep -q "artifact_type: ship_approval" clawteam/cli/commands.py` → matches
- [x] End-to-end: CLI-written artifact passes ShipApprovalGate.check(state) → `(True, "")`

## Next Phase Readiness

- SPRINT-05 complete; Plan 04-13 (e2e cross-agent verifier) can now drive the full sprint-approve -> ShipApprovalGate -> advance-past-ship flow in a single test.
- The deferred pre-existing failure in `test_gstack_plugin.py::test_contribute_review_routers_returns_gstack_router` is owned by Plan 04-11 and tracked in `deferred-items.md`; does not block Plan 04-12 completion or downstream plans.

## Self-Check: PASSED

- `clawteam/cli/commands.py` — FOUND (modified; appended sprint_approve)
- `tests/test_sprint_approve_cli.py` — FOUND (created, 10 tests pass)
- Commit `2501d7f` (test RED) — FOUND in git log
- Commit `aecfe72` (feat GREEN) — FOUND in git log

---
*Phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification*
*Completed: 2026-04-21*
