---
status: complete
phase: 05-tool-heavy-skills-ship-sre-codex
source:
  - 05-01-SUMMARY.md
  - 05-02-SUMMARY.md
  - 05-03-SUMMARY.md
  - 05-04-SUMMARY.md
  - 05-05-SUMMARY.md
  - 05-06-SUMMARY.md
  - 05-07-SUMMARY.md
  - 05-08-SUMMARY.md
  - 05-09-SUMMARY.md
  - 05-10-SUMMARY.md
verification_mode: pytest-auto-verified
verification_note: |
  Interactive UAT skipped by user preference. All tests auto-verified against pytest suite
  (239 passed / 3 skipped) after /gsd-code-review-fix 5 landed WR-01/02/03/04 fixes with
  8 new regression tests. Coverage citations below map each UAT item to the pytest file
  that exercises the user-observable behavior.
started: "2026-04-22T14:41:37Z"
updated: "2026-04-22T14:41:37Z"
---

## Current Test

[testing complete]

## Tests

### 1. Ship Skill End-to-End
expected: |
  Run `clawteam /ship --role=shipper` on a git branch with tests. Ship succeeds with 5-step completion
  (sync_main → run_tests → audit_coverage → push → open_pr). ship-notes.md has valid YAML frontmatter
  (ship_status, steps_completed, coverage, pr_url). No malformed quotes or escape sequences.
result: pass
verified_by: test_ship_skill.py (21 tests) + test_ship_notes_phase5_fields.py (4 tests) + test_yaml_emit.py (WR-01 regression — yaml_quote_string helper round-trip across ship handler)

### 2. Setup-Deploy Writes Idempotent TOML
expected: |
  Run `clawteam /setup-deploy --role=sre` with provider=vercel, project=my-app. gstack.toml [deploy] block
  written with provider/project/custom_deploy_cmd keys. Non-[deploy] blocks unchanged. Re-running overwrites
  idempotently without corruption.
result: pass
verified_by: test_setup_deploy.py (11 tests covering TOML block splice, idempotent rewrite, and wizard flow)

### 3. Land-and-Deploy YAML Frontmatter Valid
expected: |
  Run `clawteam /land-and-deploy --role=shipper` after /setup-deploy and /ship. deploy.md artifact has
  valid YAML frontmatter (deploy_status, deploy_url, provider, commit_sha, created_at, sprint_id).
  No quote escape errors.
result: pass
verified_by: test_land_and_deploy.py (13 tests) + test_yaml_emit.py (WR-01 regression across land-and-deploy emitter)

### 4. Canary HTTP Poller Handles Transport Errors
expected: |
  Run `clawteam /canary --role=sre` against a deploy_url that times out or returns 5xx. Poll loop continues
  for configured window (default 300s) without raising. canary-report.md written with canary_status=regression.
  Transport errors (incl. RuntimeError/ValueError from test-injected http_fn) coerced to status 599 and
  counted toward 5xx threshold. KeyboardInterrupt still propagates.
result: pass
verified_by: test_canary.py (26 tests — includes WR-02 regression: catches Exception broadly but lets BaseException escape; RuntimeError/ValueError coerce to 599, KeyboardInterrupt propagates)

### 5. Canary Flags Are Grep-Friendly Literals
expected: |
  Run `/canary` in three scenarios: (A) 2% 5xx rate → regression_flags contains "5xx_rate>1%";
  (B) response time 3× baseline with default multiplier → flags contain "response_time>2x_baseline";
  (C) custom multiplier=3.0 → flags contain "response_time>3.0x_baseline". All flags are exact string
  literals downstream tools can grep for.
result: pass
verified_by: test_canary.py (WR-03 regression — response_time flag f-string-interpolates configured multiplier; tests pin both default 2.0 and custom 3.0 narratives)

### 6. Document-Release Git Diff Safe Against Injection
expected: |
  /ship auto-invokes /document-release. With a crafted branch name containing shell metacharacters or
  git-option injection attempts (e.g. `--exec=...`, `--upload-pack=...`, leading dash, `\`rm -rf\``),
  git diff executes safely via invoke_native_cli (shell=False). No file deletion. docs-updates/
  contains valid unified-diff patch for legitimate refs.
result: pass
verified_by: test_document_release.py (15 tests — includes WR-04 regression: _validate_git_ref allow-list regex `^[A-Za-z0-9._/-]+$` + explicit leading-dash rejection; tests cover --exec=/--upload-pack= injection, shell metachars, and normal ref pass-through)

### 7. Benchmark YAML + Partial Lighthouse Fallback
expected: |
  Run `clawteam /benchmark --role=sre`. With partial Lighthouse JSON (missing lcp_ms/fid_ms/cls_score,
  present ttfb_ms/dom_loaded_ms), handler falls back to curl for missing vitals. benchmark-report.md
  frontmatter valid YAML with measured_with='lighthouse' and nulls for missing fields.
result: pass
verified_by: test_benchmark.py (12 tests) + test_yaml_emit.py (WR-01 regression across benchmark emitter)

### 8. Codex Skill Three Modes Emit Valid Artifacts
expected: |
  Run `/codex --role=engineer` in three modes (review, adversarial, consultation). Each mode writes
  codex-review.md with valid YAML frontmatter: artifact_type, mode (exact Literal), verdict
  (pass/fail/n/a per mode), summary (≤500 chars). Parseable without quote/escape errors.
result: pass
verified_by: test_codex.py (9 tests — exercises all three modes, verdict enforcement, summary truncation)

### 9. All Seven Skills Register + Dispatch Cleanly
expected: |
  GstackSprintPlugin().contribute_skills() returns SkillRegistration objects for codex, ship,
  setup-deploy, land-and-deploy, document-release, canary, benchmark. Each dispatches with correct
  role. Wrong role raises SkillNotPermitted. No duplicate names, no missing handlers.
result: pass
verified_by: test_skill_registration.py (4 tests) + test_gstack_plugin.py (22 tests — plugin contribute_skills() registration integrity, role gating via SkillDispatcher)

### 10. DeployRegressionDetected Event Emits Without Crashing
expected: |
  /canary emits DeployRegressionDetected via ctx.bus.emit (wrapped). Even if bus raises,
  canary-report.md still written with canary_status=regression + regression_flags. Event failure
  is advisory-only; handler never crashes on bus failure.
result: pass
verified_by: test_canary.py (event emission tests — bus failure isolated from artifact write path)

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0

pytest_totals:
  phase_5_files: 12
  passed: 239
  skipped: 3
  failed: 0

## Gaps

[none — 4 warnings from 05-REVIEW.md fixed in /gsd-code-review-fix 5 pass: WR-01 (yaml_quote_string helper), WR-02 (exception-handling), WR-03 (f-string flag), WR-04 (git ref validation). All landed with regression tests that would catch the original bugs.]
