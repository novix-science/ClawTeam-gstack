---
phase: 04
plan: 04
subsystem: harness/ship-approval
tags: [sprint-05, ship-phase, human-gate, interaction-gate, d-13]
requires: [01, 02]
provides:
  - "ShipApprovalGate(InteractionGate) — always-human ship-phase gate"
  - "4-layer check protocol: InteractionGate + artifact presence + frontmatter fields + SHA match"
affects:
  - "Plan 04-11 (GstackSprintPlugin.contribute_gates will instantiate ShipApprovalGate)"
  - "Plan 04-12 (clawteam sprint approve CLI writes the frontmatter this gate reads)"
tech-stack:
  added: []
  patterns:
    - "Subclass InteractionGate + override check() via super() delegation"
    - "getattr(state, ..., default) defensive state access (works with SimpleNamespace + SprintState)"
    - "Distinct class name (ShipApprovalGate) to avoid collision with existing HumanApprovalGate(PhaseGate)"
key-files:
  created:
    - "clawteam/harness/ship_approval_gate.py (101 LOC)"
    - "tests/test_ship_approval_gate.py (178 LOC, 11 tests)"
  modified: []
decisions:
  - "ShipApprovalGate lives at new file clawteam/harness/ship_approval_gate.py (NOT phases.py) — preserves existing HumanApprovalGate(PhaseGate) at phases.py:91 untouched (PLAN_PREP_NOTES A9)"
  - "State access via getattr(state, attr, default) — gate works with both SprintState (production) and SimpleNamespace (tests) without coupling"
  - "parse_frontmatter's ({}, raw) Pitfall #8 behavior (no frontmatter block) folds into missing-required-field branch; test_malformed_frontmatter_blocks only asserts artifact name in reason (not specific error phrasing)"
metrics:
  duration: ~10min
  completed: "2026-04-21"
  tasks: 1
  tests: 11
  loc: 279
---

# Phase 4 Plan 4: ShipApprovalGate Summary

Ships `ShipApprovalGate(InteractionGate)` at `clawteam/harness/ship_approval_gate.py` — the SPRINT-05 production-blast-radius gate that enforces always-human ship approval regardless of `auto_advance`. 4-layer check protocol delegates to `InteractionGate.check` first, then verifies `ship-approval.md` presence, required frontmatter fields (`approved_by`/`approved_at`/`sha_at_approval`), and SHA-match against `state.review_sha`.

## Implementation

### File 1: `clawteam/harness/ship_approval_gate.py` (101 LOC)

Single class `ShipApprovalGate(InteractionGate)` with:
- Constructor: keyword-only `ship_approval_artifact` (default `"ship-approval.md"`) + `sprint_dir` (forwarded to parent).
- `check(state)` delegates to `super().check(state)` first (Layer 1), then reads `state.artifacts` defensively via `getattr`, parses frontmatter via `clawteam.team.envelope.parse_frontmatter`, validates required fields, and compares `sha_at_approval` to `state.review_sha` (Layer 4).
- `state.auto_advance` is intentionally NOT consulted — SPRINT-05 always-human override.
- Error reasons include CLI hint `clawteam sprint approve <sprint_id> --phase ship`.

### File 2: `tests/test_ship_approval_gate.py` (178 LOC, 11 tests)

Uses `SimpleNamespace` state fixture to avoid `SprintState` coupling. Coverage map:

| Test | D-13 Layer | What it proves |
|------|-----------|----------------|
| test_passes_when_interaction_ok_and_approval_valid | All 4 | Happy path end-to-end |
| test_blocks_when_approval_missing | 2 | ship-approval.md absent → blocked + CLI hint |
| test_blocks_when_approved_by_missing | 3 | Missing frontmatter field detected |
| test_blocks_when_approved_at_missing | 3 | Missing frontmatter field detected |
| test_blocks_when_sha_at_approval_missing | 3 | Missing frontmatter field detected |
| test_blocks_when_sha_mismatch | 4 | Post-approval HEAD advance rejected; reason mentions "re-approval" |
| test_passes_when_review_sha_unset | 4 (skip) | `review_sha=None` → Layer 4 skipped gracefully |
| test_ignores_auto_advance | SPRINT-05 | `auto_advance=True` + no approval still blocks |
| test_malformed_frontmatter_blocks | 3 (degraded) | Unparseable frontmatter still fails (via missing-field path or malformed path) |
| test_custom_artifact_name | 2 | Constructor kwarg `ship_approval_artifact` honored |
| test_inherits_from_interaction_gate | Contract | `issubclass(ShipApprovalGate, InteractionGate)` |

## Verification

All acceptance criteria pass:

| Criterion | Result |
|-----------|--------|
| `grep -q "class ShipApprovalGate(InteractionGate)" clawteam/harness/ship_approval_gate.py` | PASS (1 match) |
| `wc -l clawteam/harness/ship_approval_gate.py >= 50` | PASS (101 LOC) |
| `pytest tests/test_ship_approval_gate.py -x -q exits 0 (11 tests)` | PASS (11 passed, 0.11s) |
| `grep -c "class HumanApprovalGate" clawteam/harness/phases.py returns 1` | PASS (1 — unchanged) |
| `pytest tests/test_interaction_gate.py tests/test_harness.py -x -q` | PASS (42 passed) |
| `grep -c "ShipApprovalGate" clawteam/harness/ship_approval_gate.py returns 1` | PASS (1 class def) |

**HumanApprovalGate phases.py grep confirmation:** `grep -c "class HumanApprovalGate" clawteam/harness/phases.py` returns exactly **1** — the existing simple `HumanApprovalGate(PhaseGate)` at line 91 is untouched. The new `ShipApprovalGate` lives in a separate module.

**HumanApprovalGate references in harness/ package (source files only):**
- `clawteam/harness/phases.py`: 1 (class definition — unchanged)
- `clawteam/harness/__init__.py`: 2 (import + __all__ — unchanged)
- `clawteam/harness/orchestrator.py`: 2 (import + instantiation — unchanged)
- `clawteam/harness/ship_approval_gate.py`: 1 (docstring cross-reference only, no code-level usage)

No new collision introduced at the import/class-resolution layer.

## D-13 Contract Mapping

Layer 1 (InteractionGate Q&A) → `super().check(state)` delegation, line 63-66.
Layer 2 (artifact presence) → `getattr(state, "artifacts", {}).get("ship-approval.md")` check, lines 68-77.
Layer 3 (required fields) → iterate `_REQUIRED_FIELDS` tuple against parsed `meta`, lines 79-91.
Layer 4 (SHA match) → `getattr(state, "review_sha", None)` conditional compare, lines 93-101.

## Deviations from Plan

None — plan executed exactly as written. TDD flow (RED → GREEN) cleanly matched the plan's test-list; no REFACTOR needed (implementation was minimal and clean on first green).

## Threat Model Coverage

All mitigations from the plan's threat register are enforced by the tests:

| Threat ID | Disposition | Enforced by test |
|-----------|-------------|------------------|
| T-04-10 (auto_advance bypass) | mitigate | test_ignores_auto_advance |
| T-04-11 (SHA rewrite) | mitigate | test_blocks_when_sha_mismatch |
| T-04-12 (info disclosure) | accept | Reason strings reviewed: only sprint_id + artifact name — no secrets |
| T-04-13 (repudiation) | accept | Gate only checks presence of `approved_by`; signing is Plan 12's job |

## Downstream Unblocks

- Plan 04-11 (GstackSprintPlugin.contribute_gates) can now `from clawteam.harness.ship_approval_gate import ShipApprovalGate` and register `{"ship": [ShipApprovalGate()]}`.
- Plan 04-12 (`clawteam sprint approve` CLI) now has a concrete frontmatter schema to write (approved_by/approved_at/sha_at_approval).

## Self-Check: PASSED

- [x] `clawteam/harness/ship_approval_gate.py` exists (101 LOC)
- [x] `tests/test_ship_approval_gate.py` exists (178 LOC, 11 tests)
- [x] RED commit b89091d exists in git log
- [x] GREEN commit f958731 exists in git log
- [x] `class ShipApprovalGate(InteractionGate)` grep returns 1
- [x] `class HumanApprovalGate` in phases.py returns 1 (unchanged)
- [x] pytest 11/11 passing
- [x] Phase 1/2 regression: 42/42 passing
- [x] No files modified outside `files_modified` allowlist
- [x] `clawteam/harness/interaction_gate.py` untouched
- [x] `clawteam/harness/phases.py` untouched
- [x] `clawteam/sprint/conductor.py` untouched
