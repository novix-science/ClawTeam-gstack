---
phase: 03-gstack-team-template-methodology-port
plan: 05
subsystem: role-prompts
tags: [gstack, role-prompts, rubric, skill-01, skill-02, skill-03, skill-04, skill-05, skill-06, skill-07, skill-08, d-08, d-14]

# Dependency graph
requires:
  - phase: 01-core-harness-extensions
    provides: harness role prompt surface (prompt resolution via contribute_prompts, planned for 03-07)
  - plan: 03-01
    provides: 11 upstream gstack skill fixtures (tests/fixtures/gstack_skills/) — verbatim rubric source per D-08
  - plan: 03-01
    provides: tests/test_gstack_role_prompts.py Wave 0 scaffold (un-xfailed here for 8 ported roles)
provides:
  - clawteam/templates/gstack/prompts/pm.md (SKILL-01 — /office-hours startup-mode rubric)
  - clawteam/templates/gstack/prompts/ceo.md (SKILL-02 — /plan-ceo-review rubric)
  - clawteam/templates/gstack/prompts/eng-mgr.md (SKILL-03 — /plan-eng-review + /retro rubric)
  - clawteam/templates/gstack/prompts/designer.md (SKILL-04 — /plan-design-review + /design-review rubric)
  - clawteam/templates/gstack/prompts/dx-lead.md (SKILL-05 — /plan-devex-review + /devex-review rubric)
  - clawteam/templates/gstack/prompts/reviewer.md (SKILL-06 — /review + /investigate rubric)
  - clawteam/templates/gstack/prompts/qa.md (SKILL-07 — /qa-only rubric)
  - clawteam/templates/gstack/prompts/security.md (SKILL-08 — /cso rubric)
affects:
  - 03-06 (engineer/shipper/sre prompts complete the 11-role set and enable the D-14 budget gate to span all 11)
  - 03-07 GstackSprintPlugin.contribute_prompts resolver (consumes these 8 prompts + 3 from 03-06)

# Tech tracking
tech-stack:
  added: []  # markdown files only; zero code/runtime changes
  patterns:
    - "Strategy B (D-08): port rubric content verbatim from upstream gstack skill markdown fixtures rather than paraphrasing — preserves provenance + makes drift detection grep-visible"
    - "D-14 budget gate: per-file ≤ 4KB, average ≤ 3KB across all role prompts (8 × 2,206 bytes avg = well under gate; max 2,905 bytes on security.md under 4KB ceiling)"
    - "Grep-verifiable SIGNATURE: gstack-role:<role> rubric:<skills> envelope-version:1 trailer on each file for 03-07 plugin loader to assert provenance at load time"

key-files:
  created:
    - clawteam/templates/gstack/prompts/pm.md
    - clawteam/templates/gstack/prompts/ceo.md
    - clawteam/templates/gstack/prompts/eng-mgr.md
    - clawteam/templates/gstack/prompts/designer.md
    - clawteam/templates/gstack/prompts/dx-lead.md
    - clawteam/templates/gstack/prompts/reviewer.md
    - clawteam/templates/gstack/prompts/qa.md
    - clawteam/templates/gstack/prompts/security.md
  modified:
    - tests/test_gstack_role_prompts.py  # un-xfailed 8 ported-role tests (engineer/shipper/sre stay xfail pending 03-06)

key-decisions:
  - "Drift-adjusted verbatim porting (not paraphrasing and not literal copy-paste). Upstream /design-review was refreshed to 7 passes (not 10 in older doc); designer.md ships the current 7-pass list. /cso.md upstream carries 22 scanner exclusions (not 17 historically); security.md ships the current 22. Approach: fetch fixtures from Wave 0 and use present-day content as source of truth — drift is a feature not a bug."
  - "Markdown files only — zero new runtime code. All wiring happens in 03-07 plugin."
  - "engineer/shipper/sre deferred to 03-06. Those prompts ship as a substantive implementation-discipline rubric (engineer) + honest Phase-5-deferred stubs (shipper, sre) because their methodology IS the Phase 5 ship/canary tool pipeline (D-01, D-02, D-03)."

# Verification
verification:
  gated: D-14 byte budget
  result: PASS
  evidence: |
    pm.md       2091 bytes (SKILL-01)
    ceo.md      1966 bytes (SKILL-02)
    eng-mgr.md  2139 bytes (SKILL-03)
    designer.md 2531 bytes (SKILL-04)
    dx-lead.md  2076 bytes (SKILL-05)
    reviewer.md 2227 bytes (SKILL-06)
    qa.md       1710 bytes (SKILL-07)
    security.md 2905 bytes (SKILL-08)
    Total: 17,645 bytes / 8 files = 2,206 bytes avg (under 3KB avg gate)
    Max: 2,905 bytes (security.md, under 4KB per-file ceiling)

  signatures: |
    All 8 files end with grep-verifiable SIGNATURE: gstack-role:<role> rubric:<skills> envelope-version:1 line.
    Verified: grep -l '^SIGNATURE: gstack-role' clawteam/templates/gstack/prompts/*.md | wc -l → 8

  tests: |
    pytest tests/test_gstack_role_prompts.py → 9 passed, 1 xfailed (xfail expected: engineer/shipper/sre files not yet present, test spans all 11 roles)

commits:
  - "1ab9b49 feat(03-05): port /office-hours + /plan-ceo-review rubrics to pm.md + ceo.md (SKILL-01, SKILL-02)"
  - "8e5b5cc feat(03-05): port /plan-eng-review + /retro + /plan-design-review + /design-review rubrics to eng-mgr.md + designer.md (SKILL-03, SKILL-04)"
  - "900cc04 feat(03-05): port /plan-devex-review + /devex-review + /review + /investigate rubrics to dx-lead.md + reviewer.md (SKILL-05, SKILL-06)"
  - "a955587 feat(03-05): port /qa + /qa-only + /cso (OWASP + STRIDE + 22 exclusions) to qa.md + security.md (SKILL-07, SKILL-08)"
  - "3e0135a test(03-05): un-xfail role-prompt tests for 8 ported roles"

# Deviations
deviations:
  - issue: "Prior executor agent stream-timed-out twice before final SUMMARY.md commit"
    auto-fixed: true
    fix: "Finalization completed inline by orchestrator: verified all 8 prompts present and signature-compliant, verified tests pass, wrote this SUMMARY.md, updated STATE.md + ROADMAP.md + REQUIREMENTS.md, single docs commit."
    impact: none  # all plan deliverables shipped, just stitched together across sessions

---

# Summary

Shipped 8 of the 11 gstack role prompts (pm, ceo, eng-mgr, designer, dx-lead, reviewer, qa, security) as
pure-rubric markdown files under `clawteam/templates/gstack/prompts/`. Content ported verbatim (with drift
adjustments) from the 11 upstream gstack skill fixtures committed in 03-01. All 8 files pass the D-14
byte budget (avg 2,206 bytes / 2,905 max — under 3KB avg / 4KB per-file gates). All 8 end with
grep-verifiable `SIGNATURE: gstack-role:<role> rubric:<skills> envelope-version:1` trailers.
Wave 0 `tests/test_gstack_role_prompts.py` un-xfailed for these 8 roles — 9 passed locally.

engineer/shipper/sre prompts ship in 03-06. GstackSprintPlugin.contribute_prompts resolver ships in 03-07.

**Requirements closed:** SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06, SKILL-07, SKILL-08.
