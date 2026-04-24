---
status: complete
phase: 06-browser-skills-design-pipeline-team-memory
source:
  - 06-01-SUMMARY.md
  - 06-02-SUMMARY.md
  - 06-03-SUMMARY.md
  - 06-04-SUMMARY.md
  - 06-05-SUMMARY.md
  - 06-06-SUMMARY.md
  - 06-07-SUMMARY.md
  - 06-08-SUMMARY.md
  - 06-09-SUMMARY.md
  - 06-10-SUMMARY.md
  - 06-11-SUMMARY.md
verification_mode: pytest-auto-verified
verification_note: |
  Interactive UAT replaced with pytest auto-verify per user preference (same pattern as Phase 5).
  All 5 code-review warnings (WR-01..WR-05) fixed in /gsd-code-review-fix 6 before verification.
  Post-fix pytest sweep: 205 passed / 1 failure (test pollution, not a product bug — see Gaps).
started: "2026-04-22T15:14:05Z"
updated: "2026-04-22T15:14:05Z"
---

## Current Test

[testing complete]

## Tests

### 1. /browse skill navigates URL and returns screenshot
expected: |
  Run `/browse url=https://example.com` → artifact with dom_hash, http_status, screenshot PNG path.
  http(s) only allowed; file:/// and data: rejected.
result: pass
verified_by: tests/templates/gstack/skills/test_browse.py (9 of 10 tests green; 1 pre-existing test-pollution failure documented in Gaps)

### 2. /browse rejects unsafe URL schemes
expected: |
  Run `/browse url=file:///etc/passwd` → ValueError before browser launch. Also rejects `data:` and `javascript:`.
result: pass
verified_by: tests/templates/gstack/skills/test_browse.py (_ALLOWED_SCHEMES allow-list + _validate_url tests)

### 3. /open-gstack-browser launches headed browser with per-domain cookies
expected: |
  Run `/open-gstack-browser url=https://github.com hold_seconds=0` → headed Chromium loads,
  reads cookies from `<team>/browser/cookies/github.com.json`, navigates, closes, writes artifact.
result: pass
verified_by: tests/templates/gstack/skills/test_open_gstack_browser.py (7 tests — cookie loading + headed launch)

### 4. /setup-browser-cookies captures authenticated session via wizard
expected: |
  Run `/setup-browser-cookies` → questionary prompts domain → login_url → Proceed → headed
  browser → user authenticates → cookies persisted to `<team>/browser/cookies/<domain>.json` as JSON array.
result: pass
verified_by: tests/templates/gstack/skills/test_setup_browser_cookies.py (9 tests) + tests/browser/test_cookies.py (14 tests)

### 5. /setup-browser-cookies rejects path-traversal and non-DNS domains
expected: |
  Enter domain `../etc/passwd` → rejected with path-traversal error. Also rejects whitespace/leading dots.
result: pass
verified_by: tests/templates/gstack/skills/test_setup_browser_cookies.py (_validate_domain tests)

### 6. /design-shotgun generates HTML variants and captures designer's pick
expected: |
  `/design-shotgun action=generate` → writes 4 HTML variants to `<sprint>/design-board/variant-<N>/` + index.md.
  `/design-shotgun action=pick picked_variant=1` → writes taste MemoryEntry with scope=role, learned_from=user, confidence=0.9.
result: pass
verified_by: tests/templates/gstack/skills/test_design_shotgun.py (19 tests — state machine + MemoryEntry emission)

### 7. /design-html detects frontend framework and emits source (HARDENED POST-FIX)
expected: |
  With React in package.json → writes `<src>/Hero.jsx` with dangerouslySetInnerHTML.
  Svelte → Hero.svelte. Vue → Hero.vue. Plain → index.html triple.
  Component name and mockup path now validated against allow-list + containment root (WR-01/02 fix).
result: pass
verified_by: tests/templates/gstack/skills/test_design_html.py (29 tests post-fix — includes WR-01 regression for component_name path-traversal + WR-02 regression for containment root)

### 8. /design-html surfaces ambiguous multi-framework as question
expected: |
  Both React + Svelte in package.json → writes `questions/design-html-framework-<digest>.md` with candidates; no source emitted.
result: pass
verified_by: tests/templates/gstack/skills/test_design_html.py (multi-framework ambiguity tests)

### 9. /learn write captures memory with tagging and evidence + high-impact gate
expected: |
  `/learn write --title=... --impact=high` → staged to `memory/<scope>/pending/` + InteractionGate question artifact.
  Normal-impact writes land directly in `memory/<scope>/<YYYY-MM>.jsonl`.
result: pass
verified_by: tests/memory/test_high_impact_gate.py (6 tests) + tests/memory/test_store_write_read.py (13 tests) + tests/templates/gstack/skills/test_learn.py (11 tests)

### 10. /learn search retrieves ranked memory with optional explanation
expected: |
  `/learn search "query" --explain` → results ranked by recency × provenance × decay, --explain shows component weights.
result: pass
verified_by: tests/memory/test_search_ranking.py (17 tests — D-06 ranking) + tests/memory/test_decay.py (11 tests) + tests/test_learn_cli.py (11 tests — CLI wiring)

### 11. /learn detects conflicts in memory entries
expected: |
  Write about "OAuth2 flow"; then about "OAuth2 single-sign-on" with same tags → ConflictDetected event
  emitted, returned in result (cosine-on-BoW, threshold 0.75). Does NOT block write.
result: pass
verified_by: tests/memory/test_conflict_detection.py (5 tests — BoW cosine + same-tag match + non-blocking)

### 12. /learn backfill scanner promotes Phase 3 retros to memory
expected: |
  Place JSON in `_phase6_pending/<stem>.json`; first `/learn list` invocation runs backfill_scan, promotes
  to `memory/team/retro/<YYYY-MM>.jsonl` idempotently via `.processed/<stem>.processed` sentinel.
result: pass
verified_by: tests/memory/test_backfill_scanner.py (7 tests post-fix — WR-03 regression added for logger.exception on swallowed error paths)

### 13. Cross-team memory isolation
expected: |
  Writes to team A's memory never appear in team B's list/search results.
result: pass
verified_by: tests/memory/test_cross_team_isolation.py (4 tests)

### 14. All 13 skills register + dispatch cleanly with role gating
expected: |
  GstackSprintPlugin().contribute_skills() returns 13 SkillRegistration objects (7 base + 3 browser + design-shotgun + design-html + learn).
  Wrong role raises SkillNotPermitted.
result: pass
verified_by: tests/plugins/test_all_seven_skills_registered.py (5 tests, despite the name — updated for 13 skills)

## Summary

total: 14
passed: 14
issues: 0
pending: 0
skipped: 0

pytest_totals:
  phase_6_scope_files: 19
  passed: 205
  failed: 1  # pre-existing test pollution, not a product bug
  skipped: 0
  after_fixes: true

## Gaps

- type: test_infrastructure
  severity: info
  test_file: tests/templates/gstack/skills/test_browse.py
  test_name: test_registered_in_plugin
  symptom: |
    Identity assertion `browse.tool_available is expected_probe` fails when other tests in the suite
    run before it. Both sides resolve to `clawteam.browser.playwright_available` but at different
    object ids because an earlier test monkeypatches the attribute. The plugin's import-time bound
    reference and the test's fresh `from clawteam.browser import playwright_available` end up pointing
    at different function objects.
  test_passes_in_isolation: true (verified via `.venv/bin/pytest tests/templates/gstack/skills/test_browse.py::test_registered_in_plugin`)
  fix_direction: |
    Replace identity check with name+module equality:
      assert browse.tool_available.__name__ == "playwright_available"
      assert browse.tool_available.__module__ == "clawteam.browser"
    Or teardown-reset the monkeypatch in the offending earlier test.
  out_of_scope_reason: pre-existing before this phase's fix pass; test-only change with no product impact
