---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 01
subsystem: plugin-substrate
tags:
  - plugin-substrate
  - skill-hook
  - doctor
  - template-config
  - adapter-wrapper
  - pydantic
  - subprocess
  - scrub-env
  - shell-false

# Dependency graph
requires:
  - phase: 01-core-harness-extensions
    provides: HarnessPlugin base class + PluginManager aggregator pattern (contribute_gates, contribute_phases).
  - phase: 02-sprint-engine-and-preventions
    provides: contribute_evidence_schemas hook shape (mirrored for contribute_skills).
  - phase: 04-interactive-routing-verification
    provides: TemplateDef.review config + invoke_native_cli dependency on NativeCliAdapter.prepare_command.
provides:
  - SkillRegistration frozen dataclass + SkillError hierarchy + SkillDispatcher
  - HarnessPlugin.contribute_skills hook (default []) + PluginManager.get_plugin_skills aggregator
  - invoke_native_cli wrapper (shell=False + scrub_env default)
  - clawteam doctor detections for gh/lighthouse/vercel/netlify/flyctl with per-platform install hints
  - TemplateDef.ship/deploy/canary/benchmark optional pydantic sub-blocks
affects:
  - 05-02 (future waves implement actual skills)
  - 05-03 through 05-10 (all Phase 5 skill plans)

# Tech tracking
tech-stack:
  added:
    - pydantic Literal typing for DeployConfig.provider enum
  patterns:
    - "Frozen dataclass for plugin contribution types (mirrors contribute_verification_pairs immutable pairs)"
    - "Aggregator-with-duplicate-detection for plugin-scoped registries (ValueError on collision)"
    - "shell=False + scrub_env default + explicit-env opt-out for subprocess wrappers"
    - "Optional top-level TOML sub-blocks on TemplateDef (None default preserves BC)"

key-files:
  created:
    - clawteam/plugins/skill_registration.py
    - clawteam/plugins/skill_errors.py
    - clawteam/plugins/skill_dispatcher.py
    - clawteam/spawn/invoke.py
    - tests/test_skill_registration.py
    - tests/test_skill_errors.py
    - tests/test_skill_dispatcher.py
    - tests/test_plugin_manager_skills.py
    - tests/test_invoke_native_cli.py
    - tests/test_doctor_new_entries.py
    - tests/test_template_def_extensions.py
  modified:
    - clawteam/plugins/base.py
    - clawteam/plugins/manager.py
    - clawteam/cli/commands.py
    - clawteam/templates/__init__.py

key-decisions:
  - "SkillRegistration uses frozenset for roles (not list) — signals set semantics + hashability for future indexing"
  - "SkillError base carries skill/role/message; subclasses add structured fields (binary+install_hint on SkillUnavailable) so surface renderers avoid string parsing"
  - "Dispatcher raises SkillError with literal 'unknown skill' (not a subclass) so callers can match without isinstance checks on an undefined hierarchy"
  - "invoke_native_cli hard-codes shell=False (D-15, T-05-01-02); caller-supplied env bypasses scrub_env (explicit opt-out, not a required preprocessor)"
  - "[ship]/[deploy]/[canary]/[benchmark] sub-blocks live at TOP LEVEL of the TOML (NOT under [template]) per CONTEXT.md layout; matches the phrasing `[ship] coverage_threshold = 0.7`"
  - "DeployConfig.provider uses Literal['vercel','netlify','fly','custom'] — Pydantic enforces enum at parse time (T-05-01-07 Tampering mitigation)"
  - "Doctor install hints for new CLIs prefer package managers per platform: apt/brew/winget for gh, npm install -g for lighthouse/vercel/netlify, fly.io install script for flyctl"

patterns-established:
  - "Plugin contribution hook shape: base default returning [] or {}, PluginManager aggregator method named get_plugin_<noun>, ValueError on duplicate key"
  - "Skill invariants: frozen dataclass → manager aggregates with duplicate detection → dispatcher role-gates and tool-probes before handler"
  - "Subprocess wrappers in clawteam/spawn/ use NativeCliAdapter.prepare_command for argv shaping and layer env/timeout/shell=False on top"

requirements-completed: []  # Substrate plan — enables SKILL-13..SKILL-19; those are marked complete by Wave 2-4 plans that ship the actual skill handlers.
requirements-enabled:
  - SKILL-13
  - SKILL-14
  - SKILL-15
  - SKILL-16
  - SKILL-17
  - SKILL-18
  - SKILL-19

# Metrics
duration: 35min
completed: 2026-04-21
---

# Phase 5 Plan 01: Wave 0 Substrate Summary

**Skill-dispatch substrate (SkillRegistration/SkillError/SkillDispatcher + contribute_skills hook), invoke_native_cli wrapper with shell=False + scrub_env default, clawteam doctor extended with gh/lighthouse/vercel/netlify/flyctl, and TemplateDef [ship]/[deploy]/[canary]/[benchmark] optional pydantic sub-blocks — zero skill implementations yet, all four foundation gaps from 05-RESEARCH closed.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-04-21T (plan-kickoff)
- **Completed:** 2026-04-21
- **Tasks:** 3
- **Files modified:** 15 (4 source edits, 4 new source modules, 7 new test modules)

## Accomplishments

- **Task 1 (skill substrate):** SkillRegistration frozen dataclass, SkillError hierarchy (SkillError/SkillUnavailable/SkillNotPermitted/SkillPreconditionError), SkillDispatcher with role gate + tool availability probe + unknown-skill error, HarnessPlugin.contribute_skills hook (empty-list default), PluginManager.get_plugin_skills aggregator with ValueError on duplicate name.
- **Task 2 (CLI substrate):** invoke_native_cli wraps NativeCliAdapter.prepare_command + subprocess.run with shell=False hard-coded, scrub_env(os.environ) as default env, caller-env override, TimeoutExpired propagation. Doctor gains 5 new CLI probes (gh, lighthouse, vercel, netlify, flyctl) with per-platform install hints (apt/brew, npm install -g, fly.io install script).
- **Task 3 (template substrate):** Four new pydantic configs — ShipConfig (coverage_threshold), DeployConfig (provider Literal enum + project + custom_deploy_cmd), CanaryConfig (window/poll/ci_wait timeouts), BenchmarkConfig (regression_threshold_ratio). _parse_toml reads top-level [ship]/[deploy]/[canary]/[benchmark] blocks; absent blocks map to None so gstack + 6 bundled templates parse unchanged.

## Task Commits

Each task followed the TDD RED/GREEN gate sequence:

1. **Task 1 RED:** `8c60a18` test(05-01): add failing tests for skill dispatch substrate
2. **Task 1 GREEN:** `6a956bd` feat(05-01): implement skill dispatch substrate (Task 1)
3. **Task 2 RED:** `6af0a31` test(05-01): add failing tests for invoke_native_cli + doctor extensions
4. **Task 2 GREEN:** `3330fee` feat(05-01): add invoke_native_cli wrapper + 5 doctor CLI entries (Task 2)
5. **Task 3 RED:** `92f24ea` test(05-01): add failing tests for TemplateDef [ship]/[deploy]/[canary]/[benchmark]
6. **Task 3 GREEN:** `c6d756d` feat(05-01): add TemplateDef [ship]/[deploy]/[canary]/[benchmark] sub-blocks (Task 3)

## TDD Gate Compliance

All three tasks used the `test(...)` → `feat(...)` cycle. No REFACTOR commits were needed (implementation passed cleanly on first GREEN pass). Tests were verified to fail at the correct point in each RED phase before implementation began (`ModuleNotFoundError`, `ImportError`, `F` on collection — consistent with fail-fast rule).

## Files Created/Modified

### Created
- `clawteam/plugins/skill_registration.py` — SkillRegistration frozen dataclass (name, roles as frozenset, handler, optional tool_available + install_hint).
- `clawteam/plugins/skill_errors.py` — SkillError hierarchy; SkillUnavailable carries binary + install_hint for surface rendering; SkillPreconditionError reserved for handlers (e.g., /land-and-deploy before /ship).
- `clawteam/plugins/skill_dispatcher.py` — SkillDispatcher.dispatch(ctx, *, skill_name, role, args=None) — role gate, tool_available probe, handler invoke.
- `clawteam/spawn/invoke.py` — invoke_native_cli() — single call site for Phase 5 skill handlers to shell out safely.
- `tests/test_skill_registration.py` — 4 tests (immutability, frozenset roles, defaults, optional fields).
- `tests/test_skill_errors.py` — 4 tests (message contents, hierarchy, base attrs, not-permitted fields).
- `tests/test_skill_dispatcher.py` — 6 tests (not-permitted, unavailable, success, unknown-skill, optional tool_available, default args).
- `tests/test_plugin_manager_skills.py` — 4 tests (default empty hook, aggregation, duplicate-name ValueError, empty plugin).
- `tests/test_invoke_native_cli.py` — 5 tests (shell=False, scrub_env default, timeout propagation, explicit env override, CompletedProcess return).
- `tests/test_doctor_new_entries.py` — 22 parametrized tests (5 tool entries × 3 platforms + keyword assertions + BC preservation).
- `tests/test_template_def_extensions.py` — 17 tests (BC for 7 templates + 4 block parsing + defaults + invalid-provider rejection + roundtrip).

### Modified
- `clawteam/plugins/base.py` — added `contribute_skills()` default hook on HarnessPlugin.
- `clawteam/plugins/manager.py` — added `get_plugin_skills()` aggregator with duplicate-name ValueError.
- `clawteam/cli/commands.py` — extended `_DOCTOR_TOOLS` tuple (+5 rows) and `_doctor_install_hint` per-platform dict (+5 entries).
- `clawteam/templates/__init__.py` — added ShipConfig/DeployConfig/CanaryConfig/BenchmarkConfig pydantic models; added four optional fields on TemplateDef; extended _parse_toml to read top-level [ship]/[deploy]/[canary]/[benchmark] blocks.

## Decisions Made

- **Roles as `frozenset`, not `list`:** `role in reg.roles` is a single hashed membership check, and frozenset is immutable under dataclass(frozen=True).
- **`SkillError` is concrete (not abstract):** the dispatcher raises a bare `SkillError` for unknown-skill so callers who only want to surface a generic "skill failed" can catch the base without matching on a subclass.
- **shell=False hard-coded in invoke_native_cli:** per threat model T-05-01-02 (Tampering of argv). Callers cannot opt out — if a skill needs shell semantics, it must compose argv explicitly.
- **scrub_env is default, not mandatory:** callers can pass `env={...}` to bypass the deny-filter when they legitimately need secrets reaching the subprocess (e.g., vercel auth). The wrapper documents this as explicit opt-out.
- **Top-level TOML sub-blocks, not nested under [template]:** matches CONTEXT.md examples and keeps lines short; pydantic still type-checks each block independently.
- **DeployConfig.custom_deploy_cmd accepts empty at schema level:** the /setup-deploy wizard (Wave 2+) enforces `provider=="custom" → custom_deploy_cmd != ""`; enforcing this at parse time would break the phased wizard UX where a user sets provider first then fills cmd.

## Deviations from Plan

None — all three tasks executed exactly as the PLAN.md `<action>` blocks specified. No Rule 1-4 deviations triggered; no architectural questions surfaced; no authentication gates.

Minor naming adjustment for test files: tests/ is flat (not nested under `tests/plugins/` etc.), so the plan's nested paths map to flat `tests/test_*.py` following the existing convention (observed from `tests/test_plugins.py`, `tests/test_doctor.py`, `tests/test_templates.py`). All acceptance criteria grep-patterns still match because they target source paths, not test paths.

### Requirements tracking note (not a code deviation)

The PLAN.md frontmatter lists `requirements: [SKILL-13..SKILL-19]` as completed by this plan. In fact, Plan 05-01 only ships the **substrate** that lets Waves 2-4 implement those skills. Per the `<objective>` explicitly stating "Zero skill implementations yet — those come in Waves 2-4", the REQUIREMENTS.md checkboxes for SKILL-13..SKILL-19 are left **unchecked** and will be marked complete by the individual Wave 2-4 plans that ship the corresponding skill handlers (05-03 /codex, 05-04 /ship, 05-05 /setup-deploy, 05-06 /land-and-deploy, 05-07 /document-release, 05-08 /canary, 05-09 /benchmark). This preserves honest traceability: REQUIREMENTS.md tracks user-visible skill functionality, not substrate enablement.

## Issues Encountered

### Pre-existing test-cross-contamination (out of scope)

When running the full test suite (`pytest tests/ -q`), two tests fail due to process-global `evidence_schemas._registry` state leaking between test files:

- `tests/test_gstack_plugin.py::test_six_evidence_schemas_registered`
- `tests/test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present`

Both pass when run in isolation. The failures reproduce on the pre-plan HEAD (`ed8c32a`) and are unrelated to the changes in Plan 05-01 (this plan did not touch `evidence_schemas.py` or either test file). Logged to `.planning/phases/05-tool-heavy-skills-ship-sre-codex/deferred-items.md` for a future hygiene plan.

## User Setup Required

None — all substrate is pure Python; no external service configuration required.

## Known Stubs

None. All source modules introduced are real implementations with verified behavior. `contribute_skills()` returns `[]` by design (existing plugins do not yet contribute skills — Wave 2+ plans add those registrations).

## Next Phase Readiness

Wave 1+ plans can now:

- `from clawteam.plugins.skill_registration import SkillRegistration` and register skills via `GstackSprintPlugin.contribute_skills()`.
- `from clawteam.plugins.skill_dispatcher import SkillDispatcher` and dispatch from `GstackSprintPlugin` or wherever agent skill calls are routed.
- `from clawteam.spawn.invoke import invoke_native_cli` in skill handlers (codex/gh/lighthouse/vercel/netlify/flyctl wrappers) — shell=False + env scrubbing are automatic.
- `tmpl.ship.coverage_threshold`, `tmpl.deploy.provider`, `tmpl.canary.window_seconds`, `tmpl.benchmark.regression_threshold_ratio` when a template declares those blocks (guard on None first).
- `clawteam doctor` now prints install hints for all five new binaries on linux/darwin/win32.

No blockers for Wave 1.

## Self-Check: PASSED

Verified each source file exists and each commit hash resolves:

- FOUND: clawteam/plugins/skill_registration.py
- FOUND: clawteam/plugins/skill_errors.py
- FOUND: clawteam/plugins/skill_dispatcher.py
- FOUND: clawteam/spawn/invoke.py
- FOUND: tests/test_skill_registration.py
- FOUND: tests/test_skill_errors.py
- FOUND: tests/test_skill_dispatcher.py
- FOUND: tests/test_plugin_manager_skills.py
- FOUND: tests/test_invoke_native_cli.py
- FOUND: tests/test_doctor_new_entries.py
- FOUND: tests/test_template_def_extensions.py
- FOUND: commit 8c60a18 (Task 1 RED)
- FOUND: commit 6a956bd (Task 1 GREEN)
- FOUND: commit 6af0a31 (Task 2 RED)
- FOUND: commit 3330fee (Task 2 GREEN)
- FOUND: commit 92f24ea (Task 3 RED)
- FOUND: commit c6d756d (Task 3 GREEN)

All acceptance criteria verified:
- `grep -q "class SkillRegistration" clawteam/plugins/skill_registration.py` OK
- `grep -q "class SkillUnavailable" clawteam/plugins/skill_errors.py` OK
- `grep -q "class SkillDispatcher" clawteam/plugins/skill_dispatcher.py` OK
- `grep -q "def contribute_skills" clawteam/plugins/base.py` OK
- `grep -q "def get_plugin_skills" clawteam/plugins/manager.py` OK
- `grep -q "def invoke_native_cli" clawteam/spawn/invoke.py` OK
- `grep -q "shell=False" clawteam/spawn/invoke.py` OK
- `_DOCTOR_TOOLS` contains gh/lighthouse/vercel/netlify/flyctl rows (tests verify)
- `class ShipConfig|DeployConfig|CanaryConfig|BenchmarkConfig` all present in clawteam/templates/__init__.py

Test counts:
- Task 1 tests: 18 passed (4 SkillRegistration + 4 SkillErrors + 6 Dispatcher + 4 ManagerSkills)
- Task 2 tests: 27 passed (5 invoke_native_cli + 22 doctor_new_entries parametrized)
- Task 3 tests: 17 passed (template_def_extensions)
- Plan-scoped BC: 82 existing template + 115 doctor/cli/spawn + 42 plugin tests all still green.

---
*Phase: 05-tool-heavy-skills-ship-sre-codex*
*Completed: 2026-04-21*
