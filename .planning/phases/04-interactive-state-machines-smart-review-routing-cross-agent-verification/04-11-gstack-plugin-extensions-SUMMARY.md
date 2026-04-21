---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
plan: 11
subsystem: plugins
tags: [gstack, plugin, review-router, verification-pair, ship-gate, decorrelation, pydantic, tdd]

# Dependency graph
requires:
  - phase: 03
    provides: GstackSprintPlugin Phase 3 substrate (contribute_phases, contribute_evidence_schemas, contribute_prompts, on_register)
  - phase: 04
    provides: GstackReviewRouter (Plan 04-06), VerificationPair + CrossAgentVerificationGate (Plan 04-03), ShipApprovalGate (Plan 04-04), PluginManager gate/pair aggregation (Plan 04-05), ReviewConfig on TemplateDef (Plan 04-06)
provides:
  - GstackSprintPlugin.contribute_review_routers returning [GstackReviewRouter(template.review.rules)]
  - GstackSprintPlugin.contribute_verification_pairs returning 2 VerificationPair instances (test + review phases)
  - GstackSprintPlugin.contribute_gates returning {"ship": [ShipApprovalGate()]}
  - Extended contribute_prompts with review-phase decorrelation supplement (4 roles × 1 file ≤ 2KB each)
  - 2 gstack cross-agent verifier functions (qa↔engineer, reviewer↔designer)
affects: [04-13 e2e regression, 04-10 review phase dispatcher, 05-* downstream skill plans]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pattern: Lazy-import inside plugin hook (resilience to wave-parallel module order) — reused from Phase 3 on_register"
    - "Pattern: frozenset[str] constants for membership-check invariants (_DECORRELATION_ROLES)"
    - "Pattern: Generalized mtime-invalidated cache via _load_prompt_file keyed by (cache_key) to share cache between base + supplement"
    - "Pattern: sentinel object() for getattr to distinguish 'attribute missing' from 'attribute = None' in verifier fallbacks"
    - "Pattern: getattr with tolerant attribute cascade (files_changed → diff_files → files_added → diff_summary) for schema variation resilience"

key-files:
  created:
    - clawteam/templates/gstack/verifiers/__init__.py
    - clawteam/templates/gstack/verifiers/test_report_matches_diff.py
    - clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py
    - tests/test_cross_agent_verifiers.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py
    - tests/test_gstack_plugin.py
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/deferred-items.md

key-decisions:
  - "Extended existing GstackSprintPlugin file in place (Phase 3 Pattern 2 — single cohesive plugin per D-04) rather than shipping a new Phase 4 plugin class"
  - "Verifier reason strings say 'references none' (plural subject form) — matched test spec"
  - "Sentinel pattern in design_doc verifier distinguishes missing attribute from None, giving different error paths (lacks field vs type/duplicate)"
  - "bool values rejected as non-integer in forcing-questions verifier despite bool ⊂ int in Python (semantic correctness — True is not a valid question id)"
  - "Path/basename/stem triple-match in qa verifier so 'pytest -k test_user' corpus matches 'a/b/test_user.py' diff entry (covers the test-selector case cleanly)"
  - "_load_prompt_file generalized as a private helper so base prompts and review supplements share identical mtime-invalidation semantics (T-07-04 mitigation consistency)"
  - "Lazy imports in contribute_review_routers / _verification_pairs / _gates keep plugin module-load resilient (if harness module missing, hook returns [] / {} instead of crashing)"

patterns-established:
  - "Pattern: Cache-key prefix ('base:' vs 'review:') lets the single _prompt_cache hold both base and supplement entries for the same role without collision"
  - "Pattern: Tolerant verifier attribute access (getattr with sentinel + type guard + cascade) — schema variations don't crash cross-agent gates"

requirements-completed: [SPRINT-03, SPRINT-04, SPRINT-05, QUALITY-13]

# Metrics
duration: 6min
completed: 2026-04-21
---

# Phase 4 Plan 11: gstack-plugin-extensions Summary

**GstackSprintPlugin gains 4 Phase-4 hooks (review router, 2 verification pairs, ship gate, review-phase decorrelation prompt supplement) + 2 gstack-specific cross-agent verifier functions with 12 unit tests.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-21T10:30:46Z
- **Completed:** 2026-04-21T10:36:30Z
- **Tasks:** 2 (both TDD)
- **Files modified:** 6 (3 created, 3 modified; including deferred-items.md update)

## Accomplishments

- `GstackSprintPlugin.contribute_review_routers` returns a single `GstackReviewRouter` constructed from `load_template("gstack").review.rules` (lazy-loaded, exception-safe).
- `GstackSprintPlugin.contribute_verification_pairs` returns exactly 2 `VerificationPair` instances with dotted paths that resolve to live callables at plugin-load time.
- `GstackSprintPlugin.contribute_gates` returns `{"ship": [ShipApprovalGate()]}` — enforces SPRINT-05 always-human ship gate.
- `GstackSprintPlugin.contribute_prompts` now appends `prompts/review/<role>.md` as a decorrelation supplement for `reviewer/designer/security/dx-lead` in the Review phase (D-07).
- 2 new verifier functions ship under `clawteam/templates/gstack/verifiers/`:
  - `verify_test_report_matches_engineer_output` (qa ↔ engineer cross-verifier, 5 tests)
  - `verify_design_doc_covers_forcing_questions` (reviewer ↔ designer cross-verifier, 7 tests)
- 12 verifier unit tests + 12 new plugin tests — all 22 tests in `test_gstack_plugin.py` (10 Phase 3 + 12 Phase 4) green.

## Task Commits

Each TDD task was committed atomically as test → feat pairs:

1. **Task 1: Verifier functions + unit tests**
   - `21f103d` (test) — 12 failing tests for both verifiers (RED gate)
   - `b76a30b` (feat) — verifier implementations (GREEN gate — 12/12 pass)
2. **Task 2: Extend GstackSprintPlugin with 4 new hooks**
   - `41407e4` (test) — 12 failing plugin tests for Phase 4 hooks (RED gate)
   - `39ede8f` (feat) — plugin extensions (GREEN gate — 22/22 pass in file)

**Plan metadata:** pending `docs(04-11): complete gstack-plugin-extensions plan` commit.

## Files Created/Modified

- `clawteam/templates/gstack/verifiers/__init__.py` — module docstring (§04-CONTEXT D-11 pointer)
- `clawteam/templates/gstack/verifiers/test_report_matches_diff.py` — `verify_test_report_matches_engineer_output` (85 LOC including docstring)
- `clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py` — `verify_design_doc_covers_forcing_questions` (79 LOC including docstring)
- `tests/test_cross_agent_verifiers.py` — 12 unit tests (NEW, 118 LOC)
- `clawteam/plugins/gstack_sprint_plugin.py` — added `_DECORRELATION_ROLES` + `_REVIEW_PROMPTS_SUBDIR` constants, extended `contribute_prompts`, added `_load_prompt_file` helper, added 3 new hooks (`contribute_review_routers`, `contribute_verification_pairs`, `contribute_gates`). No Phase 3 logic touched.
- `tests/test_gstack_plugin.py` — 12 new tests appended after the existing Phase 3 block (`test_non_gstack_template_does_not_load_gstack_plugin` kept at tail).
- `.planning/phases/.../deferred-items.md` — resolution note for 04-12 RED-flake entry; new 04-11 entry confirming pre-existing full-suite ordering flake is unrelated.

## Decisions Made

All listed in frontmatter `key-decisions`. Most notable:

- **Verifier message grammar aligned with test spec:** The plan prose said "reference none" but the test assertion asserted `"references none" in reason`. Fixed the message to read "references none" (subject-verb agreement with "test-report") so tests pass as specified.
- **Stem matching in qa verifier:** Added stem (basename sans extension) to the match corpus so `pytest -k test_user` matching `a/b/test_user.py` works robustly (the plan's original path+basename matching missed the stem-only test-selector case). This is a clean superset of the plan behavior — all original cases still pass.
- **bool-rejection in design-doc verifier:** Python's `bool ⊂ int` would otherwise classify `True/False` as valid question ids. Rejecting them as "non-integer" preserves semantic correctness (a question id cannot be True or False).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Verifier reason message aligned with test assertion**
- **Found during:** Task 1 GREEN gate (initial run of test_cross_agent_verifiers.py)
- **Issue:** Plan prose in Task 1 `<action>` block spelled the qa-verifier failure reason as "reference none" (verb without the subject agreement), but the test at `tests/test_cross_agent_verifiers.py:48` asserts `"references none" in reason` (matching the subject `test-report`). If shipped verbatim from the plan prose, the test would have failed.
- **Fix:** Restructured the reason string to lead with `"cross-verify: test-report (...) references none of engineer's ..."` — same information content, subject-verb agreement restored.
- **Files modified:** `clawteam/templates/gstack/verifiers/test_report_matches_diff.py`
- **Verification:** All 12 verifier tests pass (0.12 s).
- **Committed in:** `b76a30b` (Task 1 GREEN commit).

**2. [Rule 2 — Missing Critical] Added stem-based matching to qa verifier**
- **Found during:** Task 1 behavior audit (Test 2: `test_qa_verifier_passes_with_basename_match`)
- **Issue:** The test `pytest -k test_user` with diff `a/b/test_user.py` requires matching `test_user` (the test-name stem, no extension) against the test_command corpus. Plan's original match logic used only full path + basename; the basename `test_user.py` is not in `pytest -k test_user` so this test would have failed.
- **Fix:** Added `stem = basename.rsplit(".", 1)[0]` with `stem in search_corpus` as a third match predicate. Superset of original behavior — all prior matches still succeed.
- **Files modified:** `clawteam/templates/gstack/verifiers/test_report_matches_diff.py`
- **Verification:** Test 2 passes; no regression in Tests 1/3/4/5.
- **Committed in:** `b76a30b` (Task 1 GREEN commit).

**3. [Rule 2 — Missing Critical] Added `bool` rejection + sentinel-based missing-attribute detection in design-doc verifier**
- **Found during:** Task 1 behavior audit (Tests 10 / 11 / 12)
- **Issue:**
  - `getattr(..., default=None)` conflates "attribute missing" with "attribute explicitly None" — Test 10 (`test_design_doc_verifier_fails_on_missing_field`) expects the phrase `"lacks forcing_questions_addressed"` which only fires when attribute is truly missing.
  - `bool ⊂ int` in Python means `True` / `False` would be accepted as integer question ids by naive `int(v)` coercion. Semantically wrong.
- **Fix:**
  - Introduced a sentinel `_sentinel = object()` so `getattr(design_doc, "forcing_questions_addressed", _sentinel)` distinguishes missing-attribute (→ "lacks" path) from `None` (also → "lacks" path by design — missing or null are both missing in spirit) from the wrong-type / duplicate paths.
  - Added `isinstance(v, bool)` guard before `int(v)` coercion; booleans now report as `"non-integer question id"` matching Test 12's expectation pattern.
- **Files modified:** `clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py`
- **Verification:** All 7 design-doc tests pass.
- **Committed in:** `b76a30b` (Task 1 GREEN commit).

---

**Total deviations:** 3 auto-fixed (1 bug, 2 missing critical)
**Impact on plan:** All three are internal correctness refinements that make the verifiers match the behavior documented in the plan's `<behavior>` block and pass the plan's own tests verbatim. No scope creep; zero new files beyond those listed in `files_modified` frontmatter.

## Issues Encountered

- **Pre-existing full-suite test-ordering flake at `test_six_evidence_schemas_registered`** — Confirmed by stash-bisection that this flake reproduces WITHOUT Plan 04-11's changes. It is the same ordering flake noted in the 04-06 entry of `deferred-items.md`, owed to module-import-time schema registration double-firing when `tests/` is run in alphabetical collection order. Scope rule holds: out-of-scope for Plan 04-11; owner remains Plan 04-13 (e2e regression). Plan 04-11's scoped verification suite (71 tests across 6 files) is 100 % green. Documented at `deferred-items.md` under a new `## 04-11 Observations` section.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Plan 04-10 (review-phase dispatcher) can now consume the plugin's `contribute_review_routers` output via `PluginManager.get_plugin_gates("ship")` and `PluginManager.get_verification_pairs()` — both already landed and tested.
- Plan 04-13 (e2e regression) will exercise the full chain (ShipApprovalGate via plugin contribution → PluginManager aggregation → SprintConductor._build_gate_chain).
- Phase 5 tool-heavy-skills plans can import the verifier module directly to reuse the getattr-cascade pattern for their own cross-agent verifiers.

## Threat Flags

None — plan 04-11 introduces no new trust boundaries. The two verifier functions read only pydantic-validated artifact attributes via getattr; `contribute_review_routers` reuses the existing template-load path (T-07-01 HIGH mitigation from Phase 3 already in place); `contribute_gates` returns a singleton ShipApprovalGate() whose own threat model was landed in Plan 04-04.

## Self-Check: PASSED

Verified all created files exist and all claimed commit hashes are present in `git log`:

- `clawteam/templates/gstack/verifiers/__init__.py` — FOUND
- `clawteam/templates/gstack/verifiers/test_report_matches_diff.py` — FOUND
- `clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py` — FOUND
- `tests/test_cross_agent_verifiers.py` — FOUND
- Commit `21f103d` (test RED Task 1) — FOUND
- Commit `b76a30b` (feat GREEN Task 1) — FOUND
- Commit `41407e4` (test RED Task 2) — FOUND
- Commit `39ede8f` (feat GREEN Task 2) — FOUND

---
*Phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification*
*Completed: 2026-04-21*
