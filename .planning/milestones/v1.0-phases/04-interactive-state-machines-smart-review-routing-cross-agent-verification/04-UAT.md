---
status: partial
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
source:
  - 04-01-wave0-substrate-prep-SUMMARY.md
  - 04-02-sprintstate-events-SUMMARY.md
  - 04-03-cross-agent-verification-gate-SUMMARY.md
  - 04-04-ship-approval-gate-SUMMARY.md
  - 04-05-plugin-verification-hook-SUMMARY.md
  - 04-06-review-router-and-template-extension-SUMMARY.md
  - 04-07-office-hours-state-machine-SUMMARY.md
  - 04-08-design-consultation-state-machine-SUMMARY.md
  - 04-09-investigate-state-machine-freeze-SUMMARY.md
  - 04-10-review-phase-dispatch-SUMMARY.md
  - 04-11-gstack-plugin-extensions-SUMMARY.md
  - 04-12-sprint-approve-cli-SUMMARY.md
  - 04-13-adversarial-routing-golden-tests-SUMMARY.md
  - 04-14-d18-cleanup-thrash-integration-gate-wiring-SUMMARY.md
started: "2026-04-22T12:15:26Z"
updated: "2026-04-22T12:35:00Z"
---

## Current Test

[testing complete]

## Tests

### 1. Office Hours Multi-Turn State Machine Session
expected: |
  Run `/office-hours` as eng-lead on an active sprint. Interactive turn-by-turn prompts appear (not one-shot).
  State persists across /clear. Hard cap 13 turns.
result: pass

### 2. Design Consultation Rubric Scoring Flow
expected: |
  Run `/design-consultation` as designer. Each of 7 rubric dimensions (clarity, craft, etc.) appears on separate turns, max 15 turns total.
  Dimension state persists on reload (resume continues from last scored dimension).
result: skipped

### 3. Investigate State Machine with Module Freeze
expected: |
  Run `/investigate` as reviewer. Declare 3 candidate modules. Confirm FreezeRegistry freezes each on entry (reason tag `investigate:{sprint_id}:{hyp_id}`).
  Unfreeze fires on confirm / abandon / auto-halt after 3 failures.
result: skipped

### 4. Cross-Agent Verification Gate — Test-Engineer Report Match
expected: |
  Sprint with test-report.md + build-report.md. Verification gate rejects if test-report references no files from engineer's diff.
  Gate passes when `pytest -k <stem>` references match diff file stems.
result: pass

### 5. Cross-Agent Verification Gate — Design-Reviewer Forcing Q Coverage
expected: |
  design-doc.md declares `forcing_questions_addressed: [ids...]`; reviewer-report references same ids.
  Gate rejects if field missing or ids malformed (non-int / duplicate).
result: skipped

### 6. Ship-Phase Approval Gate with SHA-Pin
expected: |
  Run `clawteam sprint approve <id> --phase ship`. Writes ship-approval.md frontmatter with approver + SHA.
  Gate passes when approval SHA matches state.review_sha. Gate rejects if HEAD advanced post-approval (SHA drift).
result: skipped

### 7. Review Router Rule-Based Dispatch
expected: |
  Run review phase on a diff touching `src/ui/*`, `lib/crypto/*`, `api/*`, `package.json`.
  Reviewer always included (floor). Designer added for UI. Security added for crypto. DX-lead added for API+package.
result: pass
verified_by: test_review_phase_dispatch.py (35 tests, including CR-01 end-to-end regression with real GstackReviewRouter + real git repo) + test_gstack_review_router.py (20 tests)

### 8. Mid-Review SHA Advancement Detection (MidReviewThrash)
expected: |
  Start review phase, inject a commit mid-dispatch. MidReviewThrash event fires with old_sha, new_sha, diff_paths_added.
  reviewer_report.thrash_decision is populated with `re-pin` or `superseded`.
result: pass
verified_by: test_mid_review_push_integration.py (2 tests, real git commits) + test_event_types_phase4.py (4 tests, event payload shape)

### 9. Reviewer Decorrelation Prompts Append
expected: |
  For reviewer/designer/security/dx-lead roles in a review turn, role-specific decorrelation supplement
  (staff-eng cross-cutting / rubric-first / threat-model-first / friction-first) appears appended after the base prompt.
result: pass
verified_by: test_templates.py + test_gstack_plugin.py (prompt template loading with decorrelation supplements per role)

### 10. Sycophancy Cascade Alarm
expected: |
  Configure `sycophancy_threshold: 0.9` in gstack.toml. Run a review where reviewers agree >90%.
  SycophancyCascadeDetected event emits with agreement_rate ≥ threshold. Observable via sprint event log.
result: pass
verified_by: test_review_phase_dispatch.py (WR-01 regression — guards single-peer case; 3 tests for agreement_rate semantics)

### 11. Sprint Approve CLI — Error Paths
expected: |
  `clawteam sprint approve <wrong-id> --phase ship` errors cleanly (not stack trace). Invalid phase name errors cleanly.
  Approving already-approved sprint is idempotent or errors with clear message.
result: pass
verified_by: test_sprint_approve_cli.py (18 tests, including WR-02 regression for YAML escaping in --notes via yaml.safe_dump)

## Summary

total: 11
passed: 7
issues: 0
pending: 0
skipped: 4

## Gaps

[none yet]
