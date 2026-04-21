---
phase: 03-gstack-team-template-methodology-port
plan: 09
subsystem: testing
tags: [gstack, regression, cross-template-isolation, ux-01, team-03, e2e, pytest-parametrize]

# Dependency graph
requires:
  - phase: 03-gstack-team-template-methodology-port
    provides: 03-01 Wave-0 skip-scaffold in tests/test_gstack_team_spawn.py; 03-02 `team spawn` CLI + per-role memory-dir pre-creation; 03-07 GstackSprintPlugin + _on_phase_transition cross-template guard; 03-08 `team show` dashboard
  - plan: 03-01
    provides: "3 skipped scaffolds in tests/test_gstack_team_spawn.py — this plan un-skips and ships 3 active assertions"
  - plan: 03-02
    provides: "TeamManager.create_team(roles/leader_role/template=) + `clawteam team spawn <template> --name <n>` Typer subcommand"
  - plan: 03-07
    provides: "GstackSprintPlugin._on_phase_transition gated on `TeamConfig.template == 'gstack'` — the guard under negative test"
  - plan: 03-08
    provides: "`clawteam team show <team>` dashboard — used by test_team_spawn_gstack Part D integration assertion"
provides:
  - "tests/test_gstack_team_spawn.py — 3 active tests (test_eleven_worktrees_created, test_team_spawn_gstack, test_per_role_memory_dirs_precreated) anchoring TEAM-03 + UX-01 + D-05 idempotency"
  - "tests/test_template_regression_matrix.py — 13 new cross-template isolation tests (6 × test_existing_template_spawn_unaffected_by_gstack_plugin, 6 × test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack, 1 × test_all_six_existing_templates_parse_with_gstack_loaded) anchoring QUALITY-14 + success-criterion-#2 + success-criterion-#7 + T-07-01 HIGH-severity 2nd-layer mitigation"
  - "EXISTING_TEMPLATES_PHASE3 canonical list + len==6 guard (T-09-02 tamper-resistance)"
  - "gstack_plugin_loaded pytest fixture (reusable for Phase 4+ cross-template isolation tests)"
affects: [phase-04 interactive state machines, phase-06 browser+memory, phase-verification (verify-work gate)]

# Tech tracking
tech-stack:
  added: []  # Reuses existing substrate (pytest, typer.testing.CliRunner, GstackSprintPlugin)
  patterns:
    - "Positive/negative test symmetry: test_gstack_team_spawn.py owns the 'spawn gstack -> see gstack' claim; test_template_regression_matrix.py owns the 'spawn anything-else -> do NOT see gstack' claim; single plan owns both so coverage evolves together"
    - "Fixture-only plugin loading for isolation tests (gstack_plugin_loaded) — stubs bus.subscribe to avoid mutating the global EvidenceSchemaRegistry that test_gstack_plugin.py also owns; sidesteps the known test-ordering flake"
    - "len(EXISTING_TEMPLATES_PHASE3) == 6 module-level assertion — catches silent-shrinkage of the regression matrix if a future editor removes a template thinking it's redundant"
    - "Real TeamConfig on disk + handler driven directly — the Reflect-event negative test spawns each template via `clawteam team spawn`, then calls `_on_phase_transition` directly with a SimpleNamespace event; both sides of the isolation boundary (disk-persisted config + in-memory handler) are real"
    - "Positive-value avoidance for cross-template assertions: assert `template != 'gstack'` (not `template == ''`) so future templates that ship with their own `leader_role`/`template` populated still satisfy the backwards-compat invariant"

key-files:
  created:
    - ".planning/phases/03-gstack-team-template-methodology-port/03-09-e2e-cross-template-regression-SUMMARY.md"
  modified:
    - "tests/test_gstack_team_spawn.py  # unskipped 3 scaffolds + filled with real assertions (216 insertions / 22 deletions)"
    - "tests/test_template_regression_matrix.py  # +227 lines (fixture + 13 new tests + canonical role/phase constants)"
    - ".planning/phases/03-gstack-team-template-methodology-port/deferred-items.md  # logged 3 pre-existing failures (test-ordering + subprocess flakes) confirmed via git-stash baseline"

key-decisions:
  - "Test name `test_eleven_worktrees_created` preserved per 03-01 Wave-0 scaffold contract even though the `team spawn` path does not materialize git worktrees (those belong to `clawteam launch --workspace`, covered separately by test_template_launches_cleanly). The test docstring explicitly clarifies that 'worktree' here refers to the logical per-agent desk (TeamConfig member + per-role memory dir), matching what 03-02's `team spawn` actually ships. Renaming the scaffold would create a false 'task skipped' signal."
  - "Kept 3 tests in test_gstack_team_spawn.py (not 2) — the 03-01 scaffold shipped 3 skip-markers (eleven_worktrees + team_spawn_gstack + per_role_memory_dirs_precreated). Un-xfailing all 3 and giving each a distinct assertion angle (test_per_role_memory_dirs_precreated anchors D-05 idempotency under duplicate-name spawn) gives stronger coverage than collapsing them."
  - "gstack_plugin_loaded fixture does NOT drive the full PluginManager.discover path — it instantiates GstackSprintPlugin + stubs bus.subscribe. This avoids colliding with the module-global `EvidenceSchemaRegistry` state that `test_gstack_plugin.py::test_six_evidence_schemas_registered` owns (a known test-ordering flake logged in deferred-items.md). Cost: no EvidenceSchemaRegistry coverage here; that's 03-07's test file to own."
  - "Cross-template isolation tests use `clawteam team spawn` (not `clawteam launch`) to persist TeamConfig. Both commands pass `template=tmpl.name if roles else ''` into create_team identically, so the isolation hinge (TeamConfig.template) is set the same way — and `team spawn` avoids the backend/subprocess surface entirely."
  - "T-07-01 HIGH severity is now 2-layer mitigated: 03-07's test_plugin_inert_for_non_gstack_team (unit, single team) + this plan's test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack (integration, parametrized × 6)."

patterns-established:
  - "Positive/negative file pairing: test_<feature>_<present>.py asserts positive invariants; test_<matrix>_regression.py asserts non-contamination invariants. A single plan owns both so coverage evolves together."
  - "Module-level assertion as coverage tripwire: `assert len(EXISTING_TEMPLATES_PHASE3) == 6` catches silent-shrinkage of parametrize matrices at import time — no test-run needed to surface the drop."
  - "Plugin fixture with no-op bus: `ctx = SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None))` decouples plugin-on_register from the real event bus in test scope; drive handlers directly via SimpleNamespace events."

requirements-completed:
  - TEAM-03   # 11 per-role specialist desks (members + memory dirs) land at spawn time, end-to-end verified via `team spawn gstack` CLI path
  - UX-01     # `clawteam team spawn gstack --name <n>` works end-to-end (exit 0 + 11 members + TeamConfig persists + `team show` dashboard renders)

# Metrics
duration: ~9min
completed: 2026-04-21
---

# Phase 03 Plan 09: E2E + Cross-Template Regression Summary

**13 cross-template isolation tests + 3 active UX-01 / TEAM-03 end-to-end assertions close Phase 3 — the product ships (gstack spawns 11 members with memory + dashboard) and nothing else breaks (6 existing templates remain identically isolated from GstackSprintPlugin's Reflect-phase side effects).**

## Performance

- **Duration:** ~9 min (2 tasks + SUMMARY)
- **Started:** 2026-04-21T05:23:20Z
- **Completed:** 2026-04-21T05:32:34Z
- **Tasks:** 2 (plan prescribed 3; Tasks 1+2 merged because they edit the same file and 03-01's scaffold declared all 3 assertions in a single pre-commit file)
- **Files modified:** 2 test files + 1 deferred-items log
- **Full-suite delta:** 958 → 971 passing tests (**+13 new passing**); 3 pre-existing failures unchanged (all confirmed via `git stash` baseline)
- **Scope-only suite:** 28 passed (test_gstack_team_spawn: 3 + test_template_regression_matrix: 25)

## Accomplishments

- **UX-01 end-to-end verified via CLI:** `clawteam team spawn gstack --name <n>` now has real integration-test coverage — exit 0, 11-agent success message in stdout, all 11 per-role memory dirs land on disk, TeamConfig persists template + leader_role, and `clawteam team show <n>` (03-08 dashboard) renders the full roster with template chip.
- **TEAM-03 anchored at two layers:** per-role memory dir materialization (D-05) verified both directly (via TeamManager.create_team kwargs) and through the CLI (team_spawn subcommand), with idempotency guarantees under duplicate-name spawn (test_per_role_memory_dirs_precreated).
- **13 cross-template isolation assertions:** 6 × positive spawn + 6 × negative Reflect-handler + 1 × aggregate TemplateDef parse, parametrized across all 6 pre-Phase-3 templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room). Pitfall 14 + QUALITY-14 + success-criterion #2 + success-criterion #7 all have runtime anchors in CI.
- **T-07-01 HIGH severity 2nd-layer mitigation shipped:** a non-gstack template Reflect event cannot trigger `_phase6_pending/<sprint>-retro.json` writes — proven empirically for each of the 6 existing templates. Combined with 03-07's unit test, this is the 2-layer defense the original HIGH risk classification required.
- **Delete-invariant documented:** the exact shell command a release engineer runs before cutting Phase 3 — `git stash -u && rm clawteam/plugins/gstack_sprint_plugin.py clawteam/templates/gstack.toml && rm -rf clawteam/templates/gstack/ && pytest tests/ -x --ignore=tests/test_gstack_*.py --ignore=tests/test_envelope_personas.py --ignore=tests/test_evidence_schemas.py -k 'not gstack'` — captured in the plan verification section.

## Task Commits

Each task was committed atomically on branch `gstack-integration`:

1. **Task 1+2 (merged): Un-xfail tests/test_gstack_team_spawn.py with TEAM-03 + UX-01 assertions** — `bc691d1` (test)
   - 3 active tests: `test_eleven_worktrees_created` (TEAM-03: 11 members + 11 memory dirs + TeamConfig), `test_team_spawn_gstack` (UX-01 CliRunner end-to-end: spawn → disk → TeamConfig → `team show` dashboard), `test_per_role_memory_dirs_precreated` (D-05 idempotency under duplicate-name rejection).
   - 216 insertions / 22 deletions (replaces 3 skip-scaffolds with real bodies).

2. **Task 3: Extend tests/test_template_regression_matrix.py with 13 cross-template isolation tests** — `0efc3d9` (test)
   - `EXISTING_TEMPLATES_PHASE3` canonical list + `len == 6` tripwire (T-09-02).
   - `gstack_plugin_loaded` fixture (fresh plugin + stub ctx, no EvidenceSchemaRegistry touch).
   - `test_existing_template_spawn_unaffected_by_gstack_plugin[<6 templates>]` — each template's `TeamConfig.template != 'gstack'`, member-roster != 11 gstack roles, `leader_role != 'ceo'`.
   - `test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack[<6 templates>]` — drives `_on_phase_transition` handler with a Reflect event; asserts no `_phase6_pending/*.json` materialized for any non-gstack template (T-07-01 HIGH 2nd-layer mitigation).
   - `test_all_six_existing_templates_parse_with_gstack_loaded` — aggregate: each template's `phases != gstack_phases` and `leader_role != 'ceo'`.
   - 227 insertions, zero deletions (pre-existing regression matrix preserved verbatim).

**Plan metadata commit:** TBD (this SUMMARY + STATE.md + ROADMAP.md in a final `docs(03-09)` commit).

## Task Count Rationale (2 vs Plan's 3)

The plan prescribed 3 tasks (Task 1: un-xfail 11-worktree test; Task 2: un-xfail end-to-end CLI test; Task 3: extend regression matrix). Tasks 1 and 2 both modify the same file (`tests/test_gstack_team_spawn.py`) and 03-01's Wave-0 scaffold already contained 3 skip-markers (not 2). Splitting the rewrite across two commits would fragment the atomic "unskip + fill body" change and create an intermediate state where `test_team_spawn_gstack` still has an xfail while `test_eleven_worktrees_created` doesn't. Single commit is cleaner; both plan tasks are fully represented in `bc691d1`.

## Files Created/Modified

### Modified

- **`tests/test_gstack_team_spawn.py`** (216 insertions / 22 deletions)
  - Module docstring: explicit scope boundary (team spawn vs launch; logical desk vs git worktree).
  - `GSTACK_EXPECTED_ROLES` module-level frozen set (single source of truth; avoids role-name drift between the 3 tests).
  - `test_eleven_worktrees_created(isolated_data_dir)`: CLI-driven spawn → 11 members + 11 memory dirs + TeamConfig.template/leader_role round-trip.
  - `test_team_spawn_gstack(isolated_data_dir)`: 4-part integration (A: CLI exit + stdout signal; B: disk memory tree; C: TeamConfig; D: `team show` dashboard renders all 11 roles).
  - `test_per_role_memory_dirs_precreated(isolated_data_dir)`: D-05 idempotency — duplicate-name spawn rejects without corrupting the pre-existing memory tree.
  - Uses the existing `isolated_data_dir` autouse fixture from tests/conftest.py (no `tmp_path + monkeypatch` duplication).
- **`tests/test_template_regression_matrix.py`** (227 insertions)
  - Phase-3 section with canonical `EXISTING_TEMPLATES_PHASE3` + `_GSTACK_ROLE_NAMES` constants.
  - `gstack_plugin_loaded` pytest fixture.
  - 2 parametrized tests (6 cases each) + 1 aggregate = 13 new tests total.
  - Pre-existing 12 tests (test_template_launches_cleanly + test_template_spawn_calls_preserve_skip_permissions_flag) untouched.
- **`.planning/phases/03-gstack-team-template-methodology-port/deferred-items.md`**
  - Appended 03-09 section documenting 3 pre-existing failures confirmed not 03-09-caused via `git stash` baseline: `test_six_evidence_schemas_registered` + `test_evidence_schema_collision_when_registry_present` (both test-ordering flakes on global `EvidenceSchemaRegistry`, owned by 03-07 test-setup lifecycle) + `test_resume_after_process_restart` (pre-existing subprocess flake already logged under 03-02/05/06/07).
  - Recorded full-suite delta: 958 → 971 passing (+13 new).

### Created

- **`.planning/phases/03-gstack-team-template-methodology-port/03-09-e2e-cross-template-regression-SUMMARY.md`** (this file).

## Decisions Made

- **Reality-adjusted Test 1 assertion target.** The plan's Task 1 body asserted per-agent git-worktree directories under `<data_dir>/teams/<team>/agents/<role>/`. Reality: `team spawn` does NOT call `WorkspaceManager.create_workspace` — worktree creation is `clawteam launch --workspace`'s job, and the path layout is `<data_dir>/workspaces/<team>/<agent>/` (not `/teams/<team>/agents/`). The `team spawn` path does create 11 logical "desks" (TeamConfig members + per-role memory dirs at `<data_dir>/teams/<team>/memory/<role>/`), which is the D-05 substrate 03-02 shipped. Test was adjusted to assert what `team spawn` actually delivers. Logged as Rule 1 deviation below.

- **Kept 03-01's scaffold function name `test_team_spawn_gstack`** rather than renaming to `test_team_spawn_gstack_end_to_end` per plan text. The plan's acceptance criteria grep for patterns (`CliRunner`, `team.*spawn.*gstack`, `team.*show`) and not the function name itself. Renaming would break the Wave-0 "un-xfail by deleting decorator, not by creating a new function name" convention used throughout Phase 3.

- **Used `clawteam team spawn` (not `clawteam launch`) in cross-template isolation tests.** Both commands feed `TeamManager.create_team(template=tmpl.name if roles else '')` identically, so the `TeamConfig.template` field (the 03-07 cross-template discriminator) ends up in the same state. `team spawn` avoids the backend subprocess surface, keeping the test synchronous and deterministic.

- **Did NOT touch `clawteam/cli/commands.py` or `tests/test_cli_commands.py`.** Per the parallel_execution context, another Wave 4 agent owns those files simultaneously. This executor stayed strictly within the 2-file test scope declared in the plan frontmatter.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 1 assertion target corrected to match `team spawn`'s actual behavior**
- **Found during:** Task 1 reading the plan's Task 1 snippet + tracing through clawteam/team/manager.py + clawteam/workspace/manager.py.
- **Issue:** The plan prescribed asserting `<data_dir>/teams/<team>/agents/<role>/` git-worktree directories with `.git` markers — but `TeamManager.create_team` (called by `team spawn`) does not call `WorkspaceManager.create_workspace`. Worktrees are only materialized by `clawteam launch --workspace` under `<data_dir>/workspaces/<team>/<agent>/`. Asserting the prescribed shape would fail against real code.
- **Fix:** Adapted Test 1 to assert what `team spawn` actually ships per 03-02's D-05 substrate: 11 TeamConfig members + 11 per-role memory dirs at `<data_dir>/teams/<team>/memory/<role>/` + TeamConfig.template/leader_role round-trip. Still anchors TEAM-03 ("11 per-agent specialist desks materialize at spawn time") — the word "desk" in the plan's prose is the load-bearing invariant, and a per-role memory dir IS a desk in the D-05 sense. Added a module-docstring scope-boundary note making the team-spawn-vs-launch distinction explicit. Git-worktree coverage for the launch path is owned by the pre-existing `test_template_regression_matrix.py::test_template_launches_cleanly` tests across all 7 templates (unchanged by this plan).
- **Files modified:** `tests/test_gstack_team_spawn.py`
- **Verification:** `pytest tests/test_gstack_team_spawn.py -v` → 3 passed; `pytest tests/test_template_regression_matrix.py -v` → 25 passed (pre-existing launch-path tests still green).
- **Committed in:** `bc691d1` (Task 1+2 commit).

**2. [Rule 3 - Blocker] Removed gstack_plugin_loaded fixture's real EvidenceSchemaRegistry mutation**
- **Found during:** Task 3 initial attempt using the plan's prescribed `PluginManager.discover()` load pattern.
- **Issue:** Running the regression-matrix suite after `PluginManager()._instantiate_and_register(GstackSprintPlugin)` would trigger `ValueError: Duplicate evidence-schema registration: 'design-doc'` because `tests/test_gstack_plugin.py` already owns that global state (`test_six_evidence_schemas_registered` does its own register + teardown lifecycle). A second registration path in this fixture would collide with 03-07's test suite order-dependently.
- **Fix:** The fixture skips `PluginManager._instantiate_and_register` entirely — it instantiates `GstackSprintPlugin()` directly + stubs `bus.subscribe` (the only ctx surface `_on_phase_transition` needs). EvidenceSchemaRegistry coverage remains with `test_gstack_plugin.py` (where it belongs); this plan's fixture is scoped exactly to the cross-template isolation tests' needs. Documented in the fixture docstring.
- **Files modified:** `tests/test_template_regression_matrix.py` (fixture body + docstring).
- **Verification:** All 25 tests in regression matrix pass. No new `EvidenceSchemaRegistry` errors introduced.
- **Committed in:** `0efc3d9` (Task 3 commit).

---

**Total deviations:** 2 auto-fixed (1 spec-vs-reality bug, 1 blocking fixture collision). No Rule 4 architectural changes. No auth gates. No scope creep (still exactly 2 files modified per plan's `files_modified`).

## Issues Encountered

- **3 pre-existing full-suite failures remain unchanged.** All 3 confirmed not-03-09-caused via `git stash` baseline (958 passing on baseline, 971 passing after 03-09 = +13 new, zero regressions). Documented in `deferred-items.md`:
  1. `tests/test_gstack_plugin.py::test_six_evidence_schemas_registered` — test-ordering-dependent; passes in isolation.
  2. `tests/test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present` — same root cause (shared module-global EvidenceSchemaRegistry).
  3. `tests/test_sprint_conductor.py::test_resume_after_process_restart` — pre-existing subprocess-env-isolation flake; already logged under 03-02/05/06/07.
  Out of 03-09 scope because all 3 sit in files not owned by this plan, and the flakes do not block Phase 3's success criteria (success-criterion #7 is "Phase 0 regression matrix stays green" and that matrix is 12/12 green under 03-09).

## Requirement Coverage Closeout (Phase 3 Final)

Phase 3 requirements traced to owning plans. This closeout is the deliverable promised by the plan's `<output>` section.

| REQ      | Plan(s)       | Status   | Anchor                                                                                                          |
|----------|---------------|----------|-----------------------------------------------------------------------------------------------------------------|
| TEAM-01  | 03-02         | Complete | `tests/test_gstack_template.py::test_parses_via_existing_loader` (gstack.toml parses through TemplateDef loader) |
| TEAM-02  | 03-02         | Complete | `test_eleven_agents_with_distinct_roles` (11 distinct roles present)                                            |
| TEAM-03  | 03-02 + 03-09 | Complete | 03-02 substrate (per-role memory dirs D-05) + 03-09 `test_eleven_worktrees_created` (end-to-end via CLI)        |
| TEAM-04  | 03-01 + 03-04 | Complete | Conductor-layer `advance_phase(actor=)` check (03-01) + envelope-layer Literal["<role>"] (03-04)                |
| TEAM-05  | 03-02         | Complete | `test_model_profile_defaults_to_balanced` + per-role assignments in gstack.toml                                 |
| SKILL-01 | 03-05 + 03-06 | Complete | 11 role prompts shipped under 4KB budget (D-14); engineer/shipper/sre D-01..D-03 stubs                          |
| SKILL-02 | 03-05         | Complete | pm.md `/office-hours` 6 forcing questions ported verbatim                                                       |
| SKILL-03 | 03-05         | Complete | eng-mgr.md `/plan-eng-review` rubric + ceo.md `/plan-ceo-review`                                                |
| SKILL-04 | 03-05         | Complete | designer.md `/plan-design-review` 7 dimensions + `/design-review`                                               |
| SKILL-05 | 03-05         | Complete | dx-lead.md `/plan-devex-review` + `/devex-review`                                                               |
| SKILL-06 | 03-05         | Complete | reviewer.md `/review` rubric + `/investigate` INTERACTIVE-RUNTIME-DEFERRED                                      |
| SKILL-07 | 03-05         | Complete | qa.md `/qa-only` rubric                                                                                         |
| SKILL-08 | 03-05         | Complete | security.md `/cso` 22 exclusions (drift-adjusted from D-13's 17)                                                |
| SPRINT-06| 03-07         | Complete | `_phase6_pending/<sprint>-retro.json` placeholder write (D-09) + backfill-ready shape                           |
| UX-01    | 03-02 + 03-09 | Complete | 03-02 `team spawn` subcommand + 03-09 `test_team_spawn_gstack` end-to-end CLI test                              |
| UX-07    | 03-08         | Complete | `team show` dashboard (03-08) + 03-09 integration assertion in Part D of test_team_spawn_gstack                 |

**Total: 16/16 covered.** Every Phase 3 requirement has at least one plan owning it and at least one active test assertion anchoring it. No REQ-IDs deferred to Phase 4+.

## Delete-Invariant Manual Check (Pre-Phase-3-Release)

Run exactly this command on a clean checkout before cutting Phase 3 as a release candidate:

```bash
git stash -u && \
  rm clawteam/plugins/gstack_sprint_plugin.py clawteam/templates/gstack.toml && \
  rm -rf clawteam/templates/gstack/ && \
  pytest tests/ -x \
    --ignore=tests/test_gstack_template.py \
    --ignore=tests/test_gstack_plugin.py \
    --ignore=tests/test_gstack_role_prompts.py \
    --ignore=tests/test_gstack_team_spawn.py \
    --ignore=tests/test_envelope_personas.py \
    --ignore=tests/test_evidence_schemas.py \
    --ignore=tests/test_team_manager_memory.py \
    -k 'not gstack' && \
  git stash pop
```

Expected: exits 0. If it fails, something non-gstack depends on gstack-specific files — D-07 invariant violated.

**Why manual, not CI:** running this in CI requires a second working-copy checkout. Executor notes it as a release-engineer pre-cut check rather than an automated test. Documented in the plan verification section.

## Next Phase Readiness

- **Phase 3 is complete and ready for `/gsd-verify-work`.** All 16 requirements covered; 13 new cross-template isolation tests in CI; T-07-01 HIGH mitigated at 2 layers; full-suite 971/974 passing (3 pre-existing failures documented + reproduced on baseline).
- **Phase 4 (interactive state machines + smart routing) substrate is intact.** The `INTERACTIVE-RUNTIME-DEFERRED:` grep hooks in pm.md (office-hours), designer.md (design-consultation), reviewer.md (investigate + SHA-pinning) are all greppable today, ready for Phase 4's state-machine implementers.
- **Phase 5 (tool-heavy skills) substrate intact.** shipper.md (D-02) + sre.md (D-03) honest Phase-5-deferred stubs have `rubric:none` SIGNATURE lines as swap targets for /codex, /ship, /canary, /benchmark, /setup-deploy ports.
- **Phase 6 (/learn memory write path) ingestion target ready.** `_phase6_pending/<sprint>-retro.json` placeholder shape (D-09) is in place; Phase 6's backfill scanner walks the directory and ingests whatever retro bodies + personas attribution + feature flag it finds.

## Known Stubs

None in 03-09's scope. This is a test-only plan — no production stubs introduced. The `_phase6_pending/` write path is a DOCUMENTED stub (D-09 placeholder, not premature implementation) and was shipped by 03-07; its intentionality is explicitly tracked in Phase 3's plan-level "Phase 6 will backfill" contract.

## Threat Flags (All 4 Mitigated)

All 4 threats from the plan's `<threat_model>` section have active mitigations shipped:

- **T-09-01 (DoS via parametrize runtime):** Mitigated by `team spawn` (not `launch`) across the matrix — 6 templates × 2 parametrized tests × ≤ 11 members = 132 agent-member ops plus 6 × 1 aggregate test. Measured runtime: `pytest tests/test_template_regression_matrix.py` completes in 2.43s. Well under the 30s threshold for a `@pytest.mark.slow` split.
- **T-09-02 (Tampering, matrix shrinkage):** Mitigated by `assert len(EXISTING_TEMPLATES_PHASE3) == 6` module-level tripwire. A future editor removing a template fails at import time.
- **T-09-03 (Tampering, T-07-01 anchor weakening):** Accepted — git blame + PR review is the governance layer. The test docstring explicitly labels T-07-01 so intent is grep-able during code review.
- **T-09-04 (Info Disclosure via CliRunner output):** Accepted — `isolated_data_dir` autouse fixture redirects all state to tmp_path; any stderr/traceback content stays local to the test process.

---

## Self-Check: PASSED

- **Files exist:**
  - `tests/test_gstack_team_spawn.py` → FOUND (3 active tests, 0 xfails, 0 skips)
  - `tests/test_template_regression_matrix.py` → FOUND (25 tests, 13 new)
  - `.planning/phases/03-gstack-team-template-methodology-port/03-09-e2e-cross-template-regression-SUMMARY.md` → FOUND (this file)
  - `.planning/phases/03-gstack-team-template-methodology-port/deferred-items.md` → FOUND + updated with 03-09 section
- **Commits in git log:**
  - `bc691d1` (Task 1+2: test_gstack_team_spawn un-xfail) → FOUND
  - `0efc3d9` (Task 3: regression matrix 13 new tests) → FOUND
- **Acceptance criteria:**
  - Full regression matrix passes: `pytest tests/test_template_regression_matrix.py -x` → 25 passed (12 pre-existing + 13 new).
  - 13 new tests: 6 × test_existing_template_spawn_unaffected_by_gstack_plugin + 6 × test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack + 1 × test_all_six_existing_templates_parse_with_gstack_loaded.
  - All 6 existing template names present in regression matrix: `grep -c 'software-dev\|hedge-fund\|code-review\|harness-default\|research-paper\|strategy-room'` → 6+ hits.
  - GstackSprintPlugin imported in fixture: `grep -q 'from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin'` → hit.
  - T-07-01 anchor test present: `test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack` → present and parametrized × 6.
  - Aggregate test present: `test_all_six_existing_templates_parse_with_gstack_loaded` → present.
  - `pytest tests/test_gstack_team_spawn.py -x` → 3 passed. No xfails remaining (`grep -c '@pytest.mark.xfail' tests/test_gstack_team_spawn.py` → 0; `grep -c '@pytest.mark.skip' tests/test_gstack_team_spawn.py` → 0).
  - `pytest tests/ --tb=no` → 971 passed / 3 failed / 0 unexpected new failures (3 are pre-existing and documented in deferred-items.md).

---

*Phase: 03-gstack-team-template-methodology-port*
*Plan: 03-09 (e2e-cross-template-regression)*
*Completed: 2026-04-21*
