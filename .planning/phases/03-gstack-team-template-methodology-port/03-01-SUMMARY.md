---
phase: 03-gstack-team-template-methodology-port
plan: 01
subsystem: testing
tags: [gstack, fixtures, sprint-conductor, leader-role, pydantic, pytest-scaffold, nyquist]

# Dependency graph
requires:
  - phase: 01-core-harness-extensions
    provides: PhaseRegistry + EvidenceSchemaRegistry + HarnessPlugin ABC (substrate Wave 1-4 plugs into)
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: SprintConductor + TurnEnvelope + EvidenceGate (Wave 0 extends advance_phase; Wave 1 subclasses TurnEnvelope)
provides:
  - 11 upstream gstack skill markdown fixtures committed verbatim (Strategy B per D-08)
  - TeamConfig.leader_role optional field (Pattern 4 prerequisite for plugin leader-binding)
  - TeamConfig.template optional field (03-07 key_link prerequisite for per-template event-handler isolation)
  - SprintConductor.advance_phase(actor="") additive parameter with leader-role enforcement
  - 5 Wave-0 test scaffolds (35 discoverable test IDs) covering 16 REQ-IDs — Nyquist entry points for Waves 1-4
  - D-13 drift discovery: upstream counts are 6 / 7 / 22 (NOT 6 / 10 / 17 as plan expected)
affects: [03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08, phase-04 SmartReviewRouter]

# Tech tracking
tech-stack:
  added: []  # Wave 0 uses only existing substrate (pydantic, pytest, gh CLI)
  patterns:
    - "CONTENT-DRIFT-NOTE header convention (HTML-comment block above YAML frontmatter) for upstream-evolved fixtures"
    - "Additive optional-field extension on pydantic TeamConfig preserves BC for all 15+ construction sites"
    - "Lazy-import inside method body (Pattern F) — conductor imports TeamManager only when leader-role check fires"
    - "Scaffold-then-unskip Nyquist cadence — Wave 0 collects 35 skipped tests so Waves 1-4 inherit real test IDs"

key-files:
  created:
    - tests/fixtures/gstack_skills/office-hours.md
    - tests/fixtures/gstack_skills/plan-ceo-review.md
    - tests/fixtures/gstack_skills/plan-eng-review.md
    - tests/fixtures/gstack_skills/retro.md
    - tests/fixtures/gstack_skills/plan-design-review.md
    - tests/fixtures/gstack_skills/design-review.md
    - tests/fixtures/gstack_skills/plan-devex-review.md
    - tests/fixtures/gstack_skills/devex-review.md
    - tests/fixtures/gstack_skills/review.md
    - tests/fixtures/gstack_skills/qa-only.md
    - tests/fixtures/gstack_skills/cso.md
    - tests/test_gstack_template.py
    - tests/test_gstack_plugin.py
    - tests/test_gstack_role_prompts.py
    - tests/test_envelope_personas.py
    - tests/test_gstack_team_spawn.py
  modified:
    - clawteam/team/models.py (TeamConfig +leader_role +template)
    - clawteam/sprint/conductor.py (advance_phase +actor)
    - tests/test_sprint_conductor.py (+6 behavior tests)

key-decisions:
  - "Upstream gstack v2.0.0 SKILL.md fetched via `gh api repos/garrytan/gstack/contents/<skill>/SKILL.md` (public; no auth tokens transmitted — threat T-03-02 accepted)"
  - "CONTENT-DRIFT-NOTE HTML-comment headers added to office-hours.md, plan-design-review.md, cso.md — upstream has evolved beyond D-13 expectations; Wave 2 planners must consult drift notes before porting"
  - "TeamConfig.leader_role AND TeamConfig.template co-landed in Task 2 (sister fields; both flow from TemplateDef into TeamConfig at create_team time; both read by Phase 3 substrate)"
  - "advance_phase leader-role check uses lazy TeamManager import (Pattern F) to avoid module-load cycle between sprint.conductor and team.manager"
  - "Scaffolds use @pytest.mark.skip (not xfail) to keep suite boolean-green and surface unskip/unskip diffs cleanly in Wave 1+ PRs"

patterns-established:
  - "Pattern: `CONTENT-DRIFT-NOTE` HTML comment preceding YAML frontmatter in fixture files — encodes drift between plan assumptions and real upstream content without corrupting fixture verbatim content"
  - "Pattern: co-locating sister pydantic fields in one atomic commit when both flow from the same source (TemplateDef) into the same target (TeamConfig)"
  - "Pattern: Nyquist scaffolding cadence — Wave 0 commits skipped tests with verbatim expected counts in reasons; Wave N unskips by deleting the decorator"

requirements-completed:
  - TEAM-04   # advance_phase leader-role substrate ready for Wave 3 plugin
  - SPRINT-06 # Reflect scaffold test entry point ready (implementation Wave 3)
  - SKILL-01  # office-hours fixture + scaffold ready (port Wave 2)
  - SKILL-02  # plan-ceo-review fixture + scaffold ready (port Wave 2)
  - SKILL-03  # plan-eng-review + retro fixtures + scaffold ready (port Wave 2)
  - SKILL-04  # plan-design-review + design-review fixtures + scaffold ready (port Wave 2)
  - SKILL-05  # plan-devex-review + devex-review fixtures + scaffold ready (port Wave 2)
  - SKILL-06  # review fixture + scaffold ready (port Wave 2)
  - SKILL-07  # qa-only fixture + scaffold ready (port Wave 2)
  - SKILL-08  # cso fixture + scaffold ready (port Wave 2)
# NB: TEAM-01, TEAM-02, TEAM-03, TEAM-05, UX-01, UX-07 require downstream
# implementation (not completable by Wave 0 substrate prep). Wave 0 ships
# the test-scaffold entry points for those REQs; their frontmatter
# requirements field is inherited but left unchecked until Wave 1-4 ships.

# Metrics
duration: 12min
completed: 2026-04-20
---

# Phase 3 Plan 03-01: Wave 0 Substrate Prep Summary

**11 upstream gstack skill fixtures committed verbatim + SprintConductor.advance_phase(actor="") additive leader-role substrate + 5 pytest scaffolds (35 skipped test IDs) establishing Nyquist entry points for Waves 1-4.**

## Performance

- **Duration:** ~12 min (plus baseline + full-suite runs ~4 min each)
- **Started:** 2026-04-20T14:47:26Z (first commit adf6158)
- **Completed:** 2026-04-20T14:54:31Z (third commit f73e3dd)
- **Tasks:** 3 / 3
- **Files created:** 16 (11 fixtures + 5 test files)
- **Files modified:** 3 (conductor.py, models.py, test_sprint_conductor.py)
- **Test suite:** 813 pass baseline → 819 pass / 35 skipped / 0 fail after all tasks

## Accomplishments

- **Eliminated 5 unverified A1-A8 assumptions** before any implementation file lands (D-10 advance_phase actor param confirmed absent in Phase 2; Strategy B fixtures committed; TeamConfig extended additively; 5 test scaffolds collected).
- **Discovered D-13 content drift:** upstream gstack v2.0.0 has 6/7/22 (forcing questions / plan-design-review passes / cso exclusions), NOT 6/10/17 as plan assumed. Drift notes embedded in three fixture files so Wave 2 planners can re-scope designer.md (7 passes) and security.md (22 exclusions; may need D-14 budget uplift).
- **Produced 35 discoverable pytest test IDs** across 5 new files — every Wave 1+ task's `<automated>` verify block now points to a real (currently-skipped) test ID. Nyquist cadence established.
- **Phase 2 BC preserved:** `pytest tests/test_phase2_integration.py -x` → 4/4 pass; `pytest tests/test_sprint_conductor.py -x` → 27/27 pass (21 existing + 6 new); full suite → 819 pass / 35 skipped / 0 fail.

## Task Commits

Each task was committed atomically (per D-01 atomic-commit rule):

1. **Task 1: Fetch and commit 11 upstream gstack skill fixtures (D-08, D-13)** — `adf6158` (feat)
2. **Task 2: Add actor parameter to SprintConductor.advance_phase + leader_role/template to TeamConfig** — `5f67b2d` (feat) — atomic 3-file change (models.py, conductor.py, test_sprint_conductor.py)
3. **Task 3: Scaffold 5 Wave-0 test stubs (Nyquist)** — `f73e3dd` (test)

## Files Created/Modified

### Fixtures (11 created via `gh api repos/garrytan/gstack/contents/<skill>/SKILL.md`)

All 11 files are canonical upstream `SKILL.md` content (v2.0.0), checked in (not gitignored):

- `tests/fixtures/gstack_skills/office-hours.md` — 116 KB; 6 forcing questions (Q1-Q6 Demand Reality/Status Quo/Desperate Specificity/Narrowest Wedge/Observation & Surprise/Future-Fit). CONTENT-DRIFT-NOTE header: legacy "Why now?" phrase absent in v2.0.0; concept maps to Q6.
- `tests/fixtures/gstack_skills/plan-ceo-review.md` — 128 KB; 4 decision modes (Expansion/Selective/Hold/Reduction).
- `tests/fixtures/gstack_skills/plan-eng-review.md` — 97 KB; arch-lock, data-flow, edge-case matrix, test-plan.
- `tests/fixtures/gstack_skills/retro.md` — 84 KB; per-person retro format.
- `tests/fixtures/gstack_skills/plan-design-review.md` — 106 KB; CONTENT-DRIFT-NOTE: **7** Pass 1-7 (Information Architecture, Interaction State Coverage, User Journey & Emotional Arc, AI Slop Risk, Design System Alignment, Responsive & Accessibility, Unresolved Design Decisions), not 10 as D-13 expected.
- `tests/fixtures/gstack_skills/design-review.md` — 101 KB; live-site visual audit rubric.
- `tests/fixtures/gstack_skills/plan-devex-review.md` — 106 KB; 3 personas (novice/pro/power-user) + TTHW.
- `tests/fixtures/gstack_skills/devex-review.md` — 69 KB; friction tracing.
- `tests/fixtures/gstack_skills/review.md` — 90 KB; iron-law, halt-after-3.
- `tests/fixtures/gstack_skills/qa-only.md` — 61 KB; bug-fix + regression-test loop.
- `tests/fixtures/gstack_skills/cso.md` — 80 KB; CONTENT-DRIFT-NOTE: **22** hard false-positive exclusions (full list in drift header) + 12 numbered precedents + 8/10 confidence gate. D-13 expected 17.

### Modified — substrate extensions

- `clawteam/team/models.py` — TeamConfig +`leader_role: str = Field(default="", alias="leaderRole")` +`template: str = Field(default="")`. Both default "" → all existing construction sites (15+) continue unchanged.
- `clawteam/sprint/conductor.py` — `advance_phase(self, sprint_id: str)` extended to `advance_phase(self, sprint_id: str, actor: str = "") -> (bool, str)`. When `actor` is non-empty AND `TeamConfig.leader_role` is non-empty, advancement rejected unless `actor == leader_role`. Lazy TeamManager import inside method body.
- `tests/test_sprint_conductor.py` — +6 behavior tests (+1 helper `_seed_team_with_leader_role`): default-actor BC, matching-actor allow, non-matching-actor reject, empty-leader-role ignore, TeamConfig default-empty, TeamConfig explicit-assignment.

### Created — 5 Wave-0 test scaffolds (35 test IDs, all `@pytest.mark.skip`'d)

- `tests/test_gstack_template.py` — 6 tests covering TEAM-01/02/05, D-04, Pattern 4 leader_role, 7-phase declaration. Unskipped by Wave 1 (Plan 03-02).
- `tests/test_gstack_plugin.py` — 5 tests covering TEAM-04 leader-role enforcement, SPRINT-06 Reflect placeholder, plugin-load isolation, 7-phase registration, evidence-schema contribution. Unskipped by Wave 3 (Plan 03-06).
- `tests/test_gstack_role_prompts.py` — 9 tests (SKILL-01..08 + D-14 budget gate) referencing `tests/fixtures/gstack_skills/` for cross-check. Unskipped by Wave 2 (Plans 03-04 + 03-05).
- `tests/test_envelope_personas.py` — 12 tests (11 parametrized persona entries + 1 dispatch test) covering D-07 per-persona TurnEnvelope subclass. Unskipped by Wave 1 (Plan 03-03).
- `tests/test_gstack_team_spawn.py` — 3 tests covering TEAM-03 (11 worktrees), UX-01 (`clawteam team spawn gstack --name <n>`), D-05 per-role memory dirs. Unskipped by Wave 4 (Plan 03-07).

## Decisions Made

- **CONTENT-DRIFT-NOTE convention.** Plan predicate `grep -q 'Why now'` on office-hours.md would fail because upstream v2.0.0 has renamed the six forcing questions to Q1-Q6 (Demand Reality / Status Quo / Desperate Specificity / Narrowest Wedge / Observation & Surprise / Future-Fit); "Why now?" lives inside Q6 conceptually but not as a literal phrase. Per plan guidance "If any of these counts differs from the expected (6/10/17), record the actual count in the commit message and add a `# CONTENT-DRIFT-NOTE:` line at the top of the affected fixture file", I added an HTML-comment drift block above the frontmatter of three files. Actual counts: 6 / 7 / 22.
- **Co-located two sister fields (leader_role + template) in Task 2.** Both flow from `TemplateDef` → `TeamConfig` at `create_team` time; both are read by Phase 3 substrate (conductor for leader_role, plugin for template). Splitting them into separate commits would violate D-01 atomic-commit discipline for a single logical cohesion unit.
- **Used `@pytest.mark.skip` (not `xfail`) for scaffolds.** Skip keeps the suite's boolean-green accounting clean (813 → 819 passed, 35 skipped, 0 failed). XFail would turn scaffolds into `XFAIL` counts that tooling might mistake for green coverage. Wave 1+ unskips by deleting the decorator — single-line diff per test, easy PR review.
- **Fetched via `gh api` rather than `curl https://raw.githubusercontent.com/...`.** `gh` handles authentication for both private and public repos; garrytan/gstack is public so no token is transmitted (T-03-02 accept). `gh api` returns base64-encoded blobs which decode cleanly; `wc -c` reports byte counts from 61 KB (qa-only) to 128 KB (plan-ceo-review).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Critical] D-13 content-drift discovery + CONTENT-DRIFT-NOTE mitigation**
- **Found during:** Task 1 verify predicates
- **Issue:** Plan's acceptance-criterion predicate `grep -l 'Why now' tests/fixtures/gstack_skills/office-hours.md` would fail because upstream gstack v2.0.0 renamed the six forcing questions and dropped the literal "Why now?" phrasing. Similarly, plan-design-review.md has 7 passes not 10, and cso.md has 22 exclusions not 17.
- **Fix:** Per plan's explicit content-drift protocol ("If any of these counts differs from the expected (6/10/17), record the actual count in the commit message and add a `# CONTENT-DRIFT-NOTE:` line at the top of the affected fixture file"), I added HTML-comment CONTENT-DRIFT-NOTE blocks to three fixture files with the actual content enumerated verbatim:
  - `office-hours.md` — notes v2.0.0 Q1-Q6 names, confirms count still 6
  - `plan-design-review.md` — notes 7 passes (was 10), enumerates all 7 verbatim
  - `cso.md` — notes 22 exclusions (was 17), enumerates all 22 verbatim
- **Files modified:** 3 fixture files (drift notes in the header, fixture body verbatim)
- **Verification:** `grep -l "CONTENT-DRIFT-NOTE" tests/fixtures/gstack_skills/*.md` lists the 3 files; count-accurate commit message body captured the real numbers for Wave 2 planners.
- **Committed in:** `adf6158` (part of Task 1 commit)

**2. [Rule 2 - Missing Critical] Added `template` field to TeamConfig alongside `leader_role`**
- **Found during:** Task 2 planning — the PLAN explicitly calls this out as a co-landing requirement: `leader_role + template` are sister fields ("Both fields land in 03-01 Wave 0 because they are sister fields — both flow from TemplateDef into TeamConfig at create_team time").
- **Issue:** This is not strictly a deviation — the plan explicitly requires both. Documenting here because the original "must_haves" frontmatter only mentions `leader_role` on one artifact assertion line; the `template` field is introduced in the task action body but not in the top-level must_haves assertion (which the plan-checker caught in a revision).
- **Fix:** Added `template: str = Field(default="")` to `TeamConfig` alongside `leader_role`. Acceptance criteria verified via `python -c "from clawteam.team.models import TeamConfig; ..." → OK`.
- **Files modified:** `clawteam/team/models.py`
- **Verification:** 6/6 new tests pass including explicit `test_team_config_leader_role_and_template_default_empty` and `test_team_config_leader_role_and_template_accept_assignment`.
- **Committed in:** `5f67b2d` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 missing-critical content-correctness)
**Impact on plan:** Both auto-fixes improve plan fidelity. The CONTENT-DRIFT-NOTE discovery is load-bearing for Wave 2 — planners porting pm.md / designer.md / security.md must consult the drift headers before matching their ported-prompt content to the fixture content, and the D-14 budget gate for `security.md` may need an uplift given the 22-exclusion payload (5 extra exclusions = ~250-350 extra bytes beyond what the 17-exclusion budget assumed). No scope creep: both changes land squarely within Task 1 (fixtures) and Task 2 (TeamConfig) scope.

## Issues Encountered

- **None.** Baseline suite (813 passed) and final suite (819 passed / 35 skipped / 0 failed) both clean. All 27 `test_sprint_conductor.py` tests pass. Phase 2 regression preserved.

## D-13 Verbatim Content Captured for Wave 2

### The Six Forcing Questions (office-hours.md v2.0.0)

Matches the D-13 count of 6. Upstream names them:
- **Q1: Demand Reality** — "strongest evidence someone actually wants this — not 'is interested'..."
- **Q2: Status Quo** — "what are your users doing right now to solve this problem — even badly?"
- **Q3: Desperate Specificity** — "name the actual human who needs this most. What's their title?"
- **Q4: Narrowest Wedge** — "smallest possible version of this that someone would pay real money for"
- **Q5: Observation & Surprise** — "have you actually sat down and watched someone use this without helping them?"
- **Q6: Future-Fit** — "If the world looks meaningfully different in 3 years... does your product become more essential or less?"

Legacy "Why now?" phrase is absent; concept maps into Q6 (Future-Fit).

### Seven Plan-Design-Review Passes (plan-design-review.md v2.0.0 — DRIFT from D-13's 10)

- Pass 1: Information Architecture
- Pass 2: Interaction State Coverage
- Pass 3: User Journey & Emotional Arc
- Pass 4: AI Slop Risk
- Pass 5: Design System Alignment
- Pass 6: Responsive & Accessibility
- Pass 7: Unresolved Design Decisions

Plus: Design Hard Rules (7 hard-rejection patterns + 7 litmus checks), AI Slop Blacklist (11 patterns).

### Twenty-Two /cso Hard False-Positive Exclusions (cso.md v2.0.0 — DRIFT from D-13's 17)

1. DoS / resource exhaustion / rate limiting
2. Secrets on disk if otherwise secured
3. Memory / CPU / fd leaks
4. Non-security-critical input validation
5. GitHub Action workflow issues unless untrusted-input-triggerable
6. "Missing hardening" (absent best practices)
7. Race conditions / timing attacks
8. Outdated third-party libs (handled by Phase 3)
9. Memory-safety issues in memory-safe languages
10. Files only used as tests
11. Log spoofing
12. SSRF where attacker only controls path
13. User content in user-message position
14. Regex complexity on non-untrusted input
15. `*.md` files (SKILL.md exception for Phase 8)
16. Missing audit logs
17. Insecure randomness in non-security contexts
18. Git history secrets committed + removed in same initial-setup PR
19. Dependency CVEs with CVSS < 4.0
20. Docker issues in Dockerfile.dev / Dockerfile.local
21. CI/CD findings on archived / disabled workflows
22. Skill files that are part of gstack itself

Plus 12 numbered precedents and 8/10 confidence gate.

## User Setup Required

None — no external service configuration required. The `gh` CLI fetch in Task 1 is a one-time commit-then-done operation; subsequent CI runs read fixtures from disk (threat T-03-01 mitigation).

## TDD Gate Compliance

Plan 03-01 frontmatter declares `type: execute` (not `type: tdd`) but Task 2 declares `tdd="true"`. For Task 2:
- **RED gate:** Tests were written first; `pytest tests/test_sprint_conductor.py -k leader_role` failed with `AttributeError: 'TeamConfig' object has no attribute 'leader_role'` — RED achieved.
- **GREEN gate:** After adding `leader_role`/`template` to `TeamConfig` and extending `advance_phase`, all 6 new tests pass. GREEN achieved.
- **Single-commit discipline:** Per the plan's explicit direction ("Commit File 1 + File 2 + tests as a SINGLE atomic commit"), the RED and GREEN states were combined in one commit `5f67b2d`. This is a plan-directed departure from the normal RED/GREEN split and is documented as such.

## Threat Flags

None. All surface introduced in this plan (fixtures, test scaffolds, 2 pydantic fields, 1 lazy import + 1 conditional leader-role check) is enumerated in the plan's `<threat_model>` (T-03-01 tampering, T-03-02 info disclosure, T-03-03 elevation of privilege, T-03-04 DoS via broken scaffold imports). All four threats have documented dispositions and mitigations already active.

## Known Stubs

5 test files shipped with skip decorators — this is the intended Wave-0 Nyquist pattern, not unreachable stub code. Each `@pytest.mark.skip(reason="Wave N: ...")` encodes the wave that will unskip the test. The scaffolds do not block downstream waves because their skip reasons are self-describing.

## Next Phase Readiness

- **Wave 1 (Plans 03-02, 03-03):** Ready to start. Substrate is in place: `gstack.toml` loader will read existing `TemplateDef` pydantic model (additive `extra="ignore"` default); per-persona envelope subclasses can subclass Phase 2's `TurnEnvelope` cleanly; `tests/test_gstack_template.py` + `tests/test_envelope_personas.py` unskip with one-line diff per test.
- **Wave 2 (Plans 03-04, 03-05):** Ready to start. 11 fixture files committed with drift notes; D-13 verbatim content enumerated here. Planners of 03-04 should consult the three CONTENT-DRIFT-NOTE headers BEFORE drafting pm.md / designer.md / security.md content. D-14 budget gate for `security.md` may need soft uplift to accommodate 22-exclusion payload (+5 exclusions over D-13 assumption = +250-350 bytes).
- **Wave 3 (Plan 03-06):** Ready to start. `SprintConductor.advance_phase(actor=)` substrate ready; `GstackSprintPlugin` unskips `test_only_ceo_advances_phase` and `test_reflect_phase_learn_stub_writes_placeholder`.
- **Wave 4 (Plans 03-07, 03-08):** Ready to start. `test_gstack_team_spawn.py` scaffold + `TeamConfig.template` field wiring ready for `_on_phase_transition` template-layer isolation.

---

## Self-Check: PASSED

- `tests/fixtures/gstack_skills/office-hours.md` FOUND
- `tests/fixtures/gstack_skills/plan-ceo-review.md` FOUND
- `tests/fixtures/gstack_skills/plan-eng-review.md` FOUND
- `tests/fixtures/gstack_skills/retro.md` FOUND
- `tests/fixtures/gstack_skills/plan-design-review.md` FOUND
- `tests/fixtures/gstack_skills/design-review.md` FOUND
- `tests/fixtures/gstack_skills/plan-devex-review.md` FOUND
- `tests/fixtures/gstack_skills/devex-review.md` FOUND
- `tests/fixtures/gstack_skills/review.md` FOUND
- `tests/fixtures/gstack_skills/qa-only.md` FOUND
- `tests/fixtures/gstack_skills/cso.md` FOUND
- `tests/test_gstack_template.py` FOUND
- `tests/test_gstack_plugin.py` FOUND
- `tests/test_gstack_role_prompts.py` FOUND
- `tests/test_envelope_personas.py` FOUND
- `tests/test_gstack_team_spawn.py` FOUND
- Commit `adf6158` FOUND in git log
- Commit `5f67b2d` FOUND in git log
- Commit `f73e3dd` FOUND in git log
- `pytest tests/ -x` → 819 passed, 35 skipped, 0 failed

---

*Phase: 03-gstack-team-template-methodology-port*
*Plan: 03-01 (Wave 0 substrate prep)*
*Completed: 2026-04-20*
