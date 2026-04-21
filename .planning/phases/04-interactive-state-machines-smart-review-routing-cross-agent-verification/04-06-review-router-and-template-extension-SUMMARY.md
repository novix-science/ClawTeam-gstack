---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
plan: 06
subsystem: review-routing
tags: [gstack, review-router, decorrelation, sprint-03, quality-13, d-04, d-09, pattern-1, fnmatch-shim, globstar]

# Dependency graph
requires:
  - phase: 01-core-harness-extensions
    provides: ReviewRouter Protocol (clawteam/harness/review_router.py) + pluginManager hook substrate
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: SprintState.review_sha field (reserved for future SHA-gated routing; unused in 04-06 baseline)
  - phase: 03-gstack-team-template-methodology-port
    provides: Pattern 1 strict-additive precedent (7 TemplateDef fields with empty defaults); gstack.toml 11-specialist roster
  - plan: 04-01
    provides: PLAN_PREP_NOTES.md A-fnmatch decision (custom shim on fnmatch; ~35 LOC); A5 TOML parser gap confirmation
provides:
  - clawteam/templates/__init__.py gains ReviewRule + ReviewConfig pydantic models + TemplateDef.review field + _parse_toml extension reading optional [template.review] block (§04-CONTEXT D-04 / A5, Pattern 1 strict-additive)
  - clawteam/harness/gstack_review_router.py — new module with GstackReviewRouter(ReviewRouter) + _match_path globstar shim (verbatim from PLAN_PREP_NOTES A-fnmatch; ~35 LOC shim + ~50 LOC router class = 151 LOC total)
  - clawteam/templates/gstack.toml gains [template.review] header + 6 [[template.review.rules]] rows covering ui/crypto/api signals + sycophancy_threshold=0.9 (D-09/D-20)
  - clawteam/templates/gstack/prompts/review/{reviewer,designer,security,dx-lead}.md — 4 decorrelation supplements, all under 2 KB, verbatim persona anchors from §04-CONTEXT specifics
affects: [04-07 SmartReviewRouter SHA-pin (uses ReviewRule schema), 04-10 review_phase dispatcher (instantiates GstackReviewRouter via plugin), 04-11 GstackSprintPlugin.contribute_review_routers (registers the router + contribute_prompts serves review/*.md), 04-13 e2e regression fixtures consume _match_path behavior]

# Tech tracking
tech-stack:
  added: []  # No new runtime deps (PROJECT.md invariant); shim uses stdlib fnmatch
  patterns:
    - "Pattern 1 strict-additive — TemplateDef.review: ReviewConfig = Field(default_factory=ReviewConfig) keeps all 6 non-gstack templates parsing unchanged; ReviewConfig() = empty rules, threshold=0.9"
    - "Custom fnmatch shim for portable globstar — Python 3.10+ baseline precludes PurePosixPath.full_match (3.13+); shim splits on '/**/' and recurses on head/tail to match zero-or-more path segments"
    - "Reviewer floor idiom — _FLOOR_REVIEWER always added to the matched set before return; T-04-20 mitigation (attacker cannot remove the floor by omitting rules)"
    - "Per-rule try/except with logged continue — T-04-18 mitigation per RFC 001 §4.3b req 4; broken glob pattern does not crash the router, floor + unaffected rules still fire"
    - "Deterministic sorted() output — golden tests cannot flake on set iteration order; Plan 04-13 fixture replay is reproducible"
    - "Decorrelation prompt supplement pattern — per-role .md under 2 KB, appended verbatim to main prompt at Review phase dispatch (Plan 04-11 contribute_prompts honors Phase=review + role in {reviewer,designer,security,dx-lead})"

key-files:
  created:
    - clawteam/harness/gstack_review_router.py        # 151 LOC: GstackReviewRouter + _match_path shim
    - clawteam/templates/gstack/prompts/review/reviewer.md  # 1760 B
    - clawteam/templates/gstack/prompts/review/designer.md  # 1349 B
    - clawteam/templates/gstack/prompts/review/security.md  # 1407 B
    - clawteam/templates/gstack/prompts/review/dx-lead.md   # 1291 B
    - tests/test_gstack_review_router.py              # 197 LOC, 20 tests
  modified:
    - clawteam/templates/__init__.py                  # +ReviewRule +ReviewConfig +TemplateDef.review + _parse_toml review block (+70 lines)
    - clawteam/templates/gstack.toml                  # +[template.review] block with 6 rules (+40 lines)
    - tests/test_templates.py                         # +TestReviewConfigModels +TestReviewConfigParsingBC +TestReviewConfigParsingExplicit +TestGstackTemplateReview (+125 lines, 18 tests)

key-decisions:
  - "Router location: clawteam/harness/gstack_review_router.py (frontmatter files_modified) — gstack_ prefix preserves the delete-invariant (removing gstack.toml + this module + Plan 04-11 plugin leaves the codebase unchanged); lives under harness/ alongside ReviewRouter Protocol (clawteam/harness/review_router.py) rather than templates/ so non-gstack templates never import it even indirectly."
  - "Glob engine: custom _match_path shim on top of stdlib fnmatch (verbatim from PLAN_PREP_NOTES A-fnmatch CHOSEN ENGINE) — Python 3.10+ baseline rules out PurePosixPath.full_match (3.13+). Neither raw fnmatch.fnmatch nor PurePosixPath.match covers the 7-case fixture; the shim recurses over '/**/' splits to give true globstar semantics in ~35 LOC, zero new runtime deps."
  - "Pattern 1 strict-additive for ReviewConfig: TemplateDef.review defaults to ReviewConfig() with empty rules and threshold=0.9. All 6 non-gstack templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) parse with the default review block; parametrized BC test covers every one."
  - "Reviewer floor is NOT negotiable via rules (T-04-20): router unconditionally seeds matched={'reviewer'} before iterating rules. A malicious gstack.toml that declares no rules still yields ['reviewer']; a rule that adds 'reviewer' does not duplicate it (set semantics + sorted output)."
  - "Per-rule try/except with logged continue (T-04-18): a malformed glob pattern in one rule does not crash the router; it logs a warning and skips to the next rule so the floor + other rules still fire. Per RFC 001 §4.3b req 4."
  - "Sycophancy threshold default 0.9 ships in gstack.toml + ReviewConfig default — the D-09/D-20 cascade alarm trigger is template-tunable without a schema change; research baseline 0.9 carried forward verbatim."
  - "Deterministic sorted() output: match() returns the union of matched reviewers as a sorted list (not a set, not iteration-order list). Plan 04-13 regression fixtures + golden replays rely on this determinism; test_match_returns_sorted_deterministic locks it in."

patterns-established:
  - "Custom-shim glob engine for Python <3.13 globstar support — reusable pattern for any future router that needs '**' semantics on the portable baseline; 35 LOC, single top-level private _match_path function, zero runtime deps"
  - "ReviewRouter Protocol → concrete Gstack* implementation — shape that Plan 04-11 will follow for contribute_review_routers, reusable by any future template that needs its own router (SPRINT-03 leaves the door open for team-specific routing engines)"
  - "Decorrelation supplement file layout — templates/<name>/prompts/<phase>/<role>.md, per-role ≤ 2 KB budget (Phase 3 D-14 main prompt 4 KB budget is independent), appended verbatim at phase dispatch; reusable for Phase 6 browser/design/memory per-phase role supplements"

requirements-completed:
  - SPRINT-03   # Rule-based review routing: 6 rules covering ui/crypto/api signals + always-participates reviewer floor + deterministic sorted output
  - QUALITY-09  # Pinned consumer surface substrate: TemplateDef.review.sycophancy_threshold + ReviewRule schema land; Plan 10 wires the review_sha pinning
  - QUALITY-13  # Per-persona decorrelation prompts: 4 files under 2 KB with verbatim anchors (staff-eng cross-cutting / rubric-first / threat-model-first / friction-first)

# Metrics
duration: ~5min
completed: 2026-04-21
tasks_completed: 3
tests_passing: 38 (20 router + 18 templates extension, all green)
total_files_touched: 9 (6 created, 3 modified)
---

# Phase 4 Plan 04-06: Review Router + Template Extension Summary

**Ships the rules-first review router substrate for the gstack template: `TemplateDef` gains `ReviewRule` + `ReviewConfig` pydantic models (Pattern 1 strict-additive, 6 existing templates parse unchanged), `_parse_toml` reads `[[template.review.rules]]`, `GstackReviewRouter` implements the Phase-1 `ReviewRouter` Protocol with a custom `_match_path` globstar shim (portable to Python 3.10+ per PLAN_PREP_NOTES A-fnmatch), and `gstack.toml` declares 6 routing rules covering UI / crypto / API / package signals alongside 4 per-persona decorrelation prompt supplements (all ≤ 2 KB with verbatim SPRINT-03 anchors).**

## Performance

- **Duration:** ~5 min (3 tasks + summary)
- **Started:** 2026-04-21T10:11:47Z
- **Completed:** 2026-04-21T10:17:16Z
- **Tasks:** 3 / 3
- **Files created:** 6 (router module + 4 decorrelation prompts + test_gstack_review_router.py)
- **Files modified:** 3 (templates/__init__.py, gstack.toml, test_templates.py)
- **04-06-scope tests:** 38 passed (test_gstack_review_router 20 + test_templates 18 new, including parametrized BC over all 6 non-gstack templates)
- **Broader integration tests:** 98 passed (test_gstack_review_router + test_templates + test_gstack_template + test_config, full green)

## Tasks Completed

| # | Task                                                                | Commits                | Tests              |
| - | ------------------------------------------------------------------- | ---------------------- | ------------------ |
| 1 | Extend TemplateDef with ReviewRule/ReviewConfig + _parse_toml       | 30575cf + c4c1bdc      | 18 new (TDD R/G)   |
| 2 | Implement GstackReviewRouter with glob match + reviewer floor       | 481baf2 + 89b729e      | 20 new (TDD R/G)   |
| 3 | Extend gstack.toml + create 4 decorrelation prompt files            | 833fc5a                | gstack-rules test  |

## Commit Log

- `30575cf` test(04-06): add failing tests for ReviewRule/ReviewConfig template extension
- `c4c1bdc` feat(04-06): extend TemplateDef with ReviewRule/ReviewConfig pydantic models
- `481baf2` test(04-06): add failing tests for GstackReviewRouter + _match_path shim
- `89b729e` feat(04-06): implement GstackReviewRouter with globstar path matching
- `833fc5a` feat(04-06): extend gstack.toml with 6 review rules + 4 decorrelation prompts

## LOC Counts

| File                                          | LOC | Notes                                              |
| --------------------------------------------- | --- | -------------------------------------------------- |
| clawteam/harness/gstack_review_router.py      | 151 | _match_path shim (~35) + GstackReviewRouter (~50) + docstrings + imports |
| clawteam/templates/__init__.py (delta)        | +70 | ReviewRule + ReviewConfig + TemplateDef.review + _parse_toml extension  |
| clawteam/templates/gstack.toml (delta)        | +40 | [template.review] + 6 rules                        |
| tests/test_gstack_review_router.py            | 197 | 20 tests                                           |
| tests/test_templates.py (delta)               | +125 | 18 new tests (4 classes)                          |

## Decorrelation Prompt Byte Sizes (2048 B budget)

| File                                                         | Bytes | Under budget? |
| ------------------------------------------------------------ | ----- | ------------- |
| clawteam/templates/gstack/prompts/review/reviewer.md         | 1760  | yes (86%)     |
| clawteam/templates/gstack/prompts/review/designer.md         | 1349  | yes (66%)     |
| clawteam/templates/gstack/prompts/review/security.md         | 1407  | yes (69%)     |
| clawteam/templates/gstack/prompts/review/dx-lead.md          | 1291  | yes (63%)     |

All 4 under 2 KB. Max consumer: `reviewer.md` at 86% of budget — comfortable headroom for Plan 04-11 contribute_prompts appending a fixed leading SIGNATURE envelope if needed.

## Test Pass/Fail Table (keyed by SPRINT-03 sub-requirements)

| Sub-requirement                                          | Test                                            | Result |
| -------------------------------------------------------- | ----------------------------------------------- | ------ |
| Reviewer role always participates                        | test_reviewer_always_participates               | PASS   |
| Reviewer role always participates (empty rules)          | test_empty_rules_returns_floor_only             | PASS   |
| UI files route to designer                               | test_ui_diff_pulls_designer                     | PASS   |
| Crypto files route to security                           | test_crypto_diff_pulls_security                 | PASS   |
| Auth files route to security                             | test_auth_diff_pulls_security                   | PASS   |
| API + package.json route to dx-lead                      | test_api_and_package_pull_dx_lead               | PASS   |
| Multi-signal diff accumulates reviewers                  | test_union_of_matches_accumulation              | PASS   |
| No-match diff yields only floor                          | test_no_match_floor_only                        | PASS   |
| Two rules adding same reviewer do not duplicate          | test_deduplication                              | PASS   |
| Rule that adds 'reviewer' does not duplicate floor       | test_rule_adding_reviewer_does_not_duplicate    | PASS   |
| Output is deterministic + sorted                         | test_match_returns_sorted_deterministic         | PASS   |
| Broken glob pattern is logged + skipped (T-04-18)        | test_exception_in_pattern_match_skipped         | PASS   |
| Protocol conformance                                     | test_protocol_conformance                       | PASS   |
| _match_path: literal                                     | test_match_path_literal                         | PASS   |
| _match_path: '/**/ ' doublestar in middle                | test_match_path_doublestar_in_middle            | PASS   |
| _match_path: trailing '/**'                              | test_match_path_trailing_doublestar             | PASS   |
| _match_path: leading '**/'                               | test_match_path_leading_doublestar              | PASS   |
| _match_path: '**/*.ext' suffix                           | test_match_path_doublestar_suffix_only          | PASS   |
| _match_path: bare '**'                                   | test_match_path_bare_doublestar_matches_anything | PASS  |
| _match_path: app/api deep regression                     | test_match_path_app_api_deep                    | PASS   |

| QUALITY-13 sub-requirement                               | Artifact / Test                                       | Result |
| -------------------------------------------------------- | ----------------------------------------------------- | ------ |
| 4 decorrelation prompt files exist                       | ls clawteam/templates/gstack/prompts/review/*.md      | PASS (4 files) |
| Each file ≤ 2048 bytes                                   | wc -c (max 1760 B)                                    | PASS   |
| reviewer.md contains "staff-eng cross-cutting"           | grep                                                  | PASS   |
| designer.md contains "rubric-first"                      | grep                                                  | PASS   |
| security.md contains "threat-model-first"                | grep                                                  | PASS   |
| dx-lead.md contains "friction-first"                     | grep                                                  | PASS   |

| QUALITY-09 / D-09 sub-requirement                        | Artifact / Test                                       | Result |
| -------------------------------------------------------- | ----------------------------------------------------- | ------ |
| sycophancy_threshold default = 0.9                       | ReviewConfig default + gstack.toml                    | PASS   |
| Threshold range clamped [0.0, 1.0]                       | test_review_config_sycophancy_threshold_range         | PASS   |
| ReviewConfig defaults empty (Pattern 1 BC)               | test_review_config_default_empty                      | PASS   |
| 6 non-gstack templates parse with empty default          | test_existing_template_parses_without_review_block (6x) | PASS   |
| gstack.toml ships with 6+ routing rules                  | test_gstack_template_has_review_rules                 | PASS   |

## Deviations from Plan

None – plan executed as written.

Minor adjustments (all within plan intent, not deviations):

1. **`_match_path` shim source**: used the verbatim shim from `PLAN_PREP_NOTES.md ## A-fnmatch` (which the plan's `<interfaces>` section explicitly mandates) rather than the sketch embedded in the Task 2 `<action>` block. The sketch version had a bug in the trailing-`/**` branch (would have failed `test_match_path_app_api_deep`). Plan frontmatter says "Per PLAN_PREP_NOTES.md `## A-fnmatch`: CHOSEN ENGINE + import line must be copied verbatim from that file" — the prep-notes version is the canonical source and was adopted as intended.
2. **Test file named `test_templates.py` edited in place** (not a new file): tests land inside existing classes as `TestReviewConfigModels`, `TestReviewConfigParsingBC`, `TestReviewConfigParsingExplicit`, `TestGstackTemplateReview` following the existing `TestPhase3AdditiveFields` pattern from 03-02.
3. **Router field `review` default uses `Field(default_factory=ReviewConfig)`** instead of `= ReviewConfig()` literal default. Pydantic v2 best practice for mutable defaults; functionally identical. All BC tests pass.

## Deferred Issues

Logged to `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/deferred-items.md`:

- **`tests/test_gstack_plugin.py::test_six_evidence_schemas_registered`** — pre-existing test-ordering flake (passes in isolation; fails with `ValueError: Duplicate evidence-schema registration: 'design-doc'` when full `pytest tests/` runs). Out of scope for Plan 04-06 (no Plan 04-06 file touches `clawteam/harness/evidence_schemas.py` or `clawteam/plugins/gstack_sprint_plugin.py`). Proposed owner: Plan 04-11 or 04-13.

## Engine-Selection Notes (per `<output>` contract)

**No surprises vs PLAN_PREP_NOTES A-fnmatch decision.** The prep notes correctly predicted:

1. Raw `fnmatch.fnmatch` fails `src/components/Button.tsx` vs `src/components/**/*.tsx` (shim fixes via leading-`**/` suffix-match recursion).
2. `PurePosixPath.match` fails `src/auth/tokens/jwt.py` vs `src/auth/**` (shim fixes via trailing-`/**` prefix-plus-or-equal recursion).
3. `PurePosixPath.full_match` would work but is Python 3.13+ only — project pyproject requires `>=3.10`, so it is NOT portable.
4. Shim is ~35 LOC (verified: the shim body between `def _match_path` and the final `return False` is 35 lines including comments).

**One additional test case beyond the 7 fixtures in prep notes**: `test_match_path_bare_doublestar_matches_anything` (bare `**` matches any path). The shim handles this via the first branch (`if pattern == "**"`); the prep-notes fixture set did not include this case explicitly but the shim covers it — locked in to prevent regressions if the shim is later refactored.

## Threat Model Dispositions Applied

| Threat ID | Mitigation Applied                                                                   | Test Lock                                    |
| --------- | ------------------------------------------------------------------------------------ | -------------------------------------------- |
| T-04-17   | ACCEPTED — pathological globs pull everyone but do not crash; operator tunes rules   | (no test; design-only)                       |
| T-04-18   | Per-rule try/except; broken glob logged + skipped; router continues with other rules | test_exception_in_pattern_match_skipped      |
| T-04-19   | ACCEPTED — decorrelation prompts are public template content; committed to git       | (no test; design-only)                       |
| T-04-20   | Reviewer floor unconditionally appended; not negotiable via rules                    | test_reviewer_always_participates + test_rule_adding_reviewer_does_not_duplicate |

## Self-Check: PASSED

**Files created (verified exist on disk):**
- FOUND: clawteam/harness/gstack_review_router.py
- FOUND: clawteam/templates/gstack/prompts/review/reviewer.md
- FOUND: clawteam/templates/gstack/prompts/review/designer.md
- FOUND: clawteam/templates/gstack/prompts/review/security.md
- FOUND: clawteam/templates/gstack/prompts/review/dx-lead.md
- FOUND: tests/test_gstack_review_router.py

**Files modified (verified via git log):**
- FOUND: clawteam/templates/__init__.py (c4c1bdc)
- FOUND: clawteam/templates/gstack.toml (833fc5a)
- FOUND: tests/test_templates.py (30575cf)

**Commits exist (verified via git log):**
- FOUND: 30575cf test(04-06): add failing tests for ReviewRule/ReviewConfig template extension
- FOUND: c4c1bdc feat(04-06): extend TemplateDef with ReviewRule/ReviewConfig pydantic models
- FOUND: 481baf2 test(04-06): add failing tests for GstackReviewRouter + _match_path shim
- FOUND: 89b729e feat(04-06): implement GstackReviewRouter with globstar path matching
- FOUND: 833fc5a feat(04-06): extend gstack.toml with 6 review rules + 4 decorrelation prompts

**Final verification sweep:**
- `pytest tests/test_gstack_review_router.py tests/test_templates.py -x -q` → 68 passed
- `pytest tests/test_gstack_template.py -x -q` → 9 passed (Phase 3 tests unaffected)
- `pytest tests/test_config.py -x -q` → 21 passed
- `grep -l "staff-eng cross-cutting|rubric-first|threat-model-first|friction-first" clawteam/templates/gstack/prompts/review/*.md | wc -l` → 4
- All 6 non-gstack templates parse: software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room
