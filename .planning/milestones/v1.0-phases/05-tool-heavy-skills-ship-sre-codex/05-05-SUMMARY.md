---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 05
subsystem: skills
tags: [skill-setup-deploy, questionary-wizard, toml-edit, deploy-config, shell-injection-hardening, pydantic, atomic-write]

# Dependency graph
requires:
  - phase: 05-tool-heavy-skills-ship-sre-codex
    provides: "Plan 05-01 (SkillRegistration + SkillDispatcher + DeployConfig pydantic model + atomic_write_text primitive)"
  - phase: 05-tool-heavy-skills-ship-sre-codex
    provides: "Plan 05-02 (DeployNotes schema downstream — /land-and-deploy artifact in future plans)"
provides:
  - "/setup-deploy skill (SKILL-19): one-time SRE-driven wizard that writes a [deploy] block to gstack.toml"
  - "validate_project_slug + validate_custom_cmd shell-metachar deny-list (D-15 adversarial input mitigation)"
  - "_DEPLOY_BLOCK_RE negative-lookahead splice regex — reusable pattern for other [section]-rewrite handlers"
  - "Atomic + idempotent TOML block insert/replace via atomic_write_text; all non-[deploy] blocks preserved byte-identical"
affects:
  - 05-06 (/land-and-deploy — reads [deploy] block written here)
  - 05-07 (/canary — downstream of /land-and-deploy)
  - 05-09 (/setup-deploy adjacent CLI entry — if added later)

# Tech tracking
tech-stack:
  added: []  # questionary already present from Phase 3; tomllib stdlib; pydantic already present
  patterns:
    - "Pure-wizard / side-effect-handler split (wizard.py is UI-only, handler.py owns filesystem)"
    - "Lazy-import via module-local _load_questionary() so tests can monkeypatch without TTY"
    - "Deny-list validator + pydantic Literal + invoke_native_cli(shell=False) triple-layer injection defense"
    - "Regex-splice block rewrite preserves surrounding TOML blocks (no re-serialization)"
    - "tomllib round-trip assertion after render is a belt-and-suspenders correctness check"
    - "args['_skip_confirm'] test/CLI bypass flag — not in agent-facing contract"

key-files:
  created:
    - clawteam/templates/gstack/skills/setup_deploy/__init__.py
    - clawteam/templates/gstack/skills/setup_deploy/wizard.py
    - clawteam/templates/gstack/skills/setup_deploy/handler.py
    - tests/templates/gstack/skills/test_setup_deploy.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py

key-decisions:
  - "Validator deny-list for custom_deploy_cmd uses explicit shell-metachar set (; | & ` $ < > \\ newline) rather than allow-list regex — allow-list would reject legitimate flags like '--env=prod' which contain '='; deny-list is grep-able and keeps the prompt ergonomic."
  - "KeyboardInterrupt raised on questionary None return (Ctrl-C) instead of returning None/empty — dispatcher layer can catch the exception and render a clean 'wizard aborted' message without polluting the handler's return-type discriminator."
  - "_DEPLOY_BLOCK_RE uses negative-lookahead '(?!^\\[)' to bail at the next section header — avoids greedy matching that would swallow subsequent [section] blocks when [deploy] is not the final block."
  - "tomllib round-trip after render is a hard assertion (not just a warning). If the regex splice ever produces a malformed file we refuse to write instead of corrupting gstack.toml. Single-bug containment."
  - "args['_skip_confirm'] is an underscore-prefixed internal flag — signals 'not part of the agent-facing dispatch contract' so future agent-written invocations cannot accidentally pass it."

patterns-established:
  - "Pure-wizard vs side-effecting-handler separation — subsequent skills with interactive prompts follow the same split."
  - "Validator as module-public function (validate_project_slug / validate_custom_cmd) — exposed at package __init__ so tests and the handler's assertion path can both call it without importing private names."
  - "Regex-splice approach for idempotent [block]-level TOML edits — avoids full round-trip serialization which would reorder keys and strip comments."

requirements-completed: [SKILL-19]

# Metrics
duration: 20min
completed: 2026-04-21
---

# Phase 5 Plan 05: /setup-deploy Wizard Summary

**Questionary-backed SRE wizard that writes an idempotent, shell-injection-hardened `[deploy]` block to `gstack.toml` while leaving all other TOML blocks byte-identical.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-21T14:10:00Z
- **Completed:** 2026-04-21T14:30:48Z
- **Tasks:** 1 (TDD — RED then GREEN)
- **Files modified:** 4 (3 created + 1 edited)

## Accomplishments

- /setup-deploy skill package (~280 LOC) — wizard.py + handler.py + __init__.py.
- 11 tests (happy-path x2, validator rejection x2, Ctrl-C x1, handler write-path x1, idempotent re-run x2, role-gate x1, pydantic-rejection x1, plugin-registration x1) — all green.
- Shell-injection defense triple-layer: up-front validator deny-list, pydantic `Literal[...]` enum on `provider`, subprocess invocation via `invoke_native_cli(shell=False)` (downstream in 05-06).
- Plugin `contribute_skills` now returns 3 skills — `/codex`, `/ship`, `/setup-deploy` (roles=`frozenset({'sre'})`).

## Task Commits

1. **Task 1 — TDD RED (tests):** `0b52021` — `test(05-05): add failing tests for /setup-deploy skill (11 tests)`
   - Commit unintentionally captured a parallel executor's `clawteam/templates/gstack/skills/codex/` staged files (Wave 2 three-way concurrent index write — see Deviations). Test content landed via sibling commit `0256693` / `f3113d8` in the final on-disk state.
2. **Task 1 — TDD GREEN (implementation):** `1f4e6e6` — `feat(05-05): implement /setup-deploy wizard + handler (SKILL-19)`
   - Adds wizard.py + handler.py + __init__.py for the `setup_deploy` sub-package.
   - Plugin registration lives in `a991ea8` (Plan 05-04's Task 2 commit) because Wave 2's three-way concurrent edit to `gstack_sprint_plugin.py` was serialized by whichever executor ran `git commit` first.

**Plan metadata:** (this commit — `docs(05-05): complete setup-deploy-wizard plan`)

_Note: single Task 1 with TDD = 2 code commits (RED + GREEN). Refactor commit omitted — no cleanup needed after GREEN passed._

## Files Created/Modified

- `clawteam/templates/gstack/skills/setup_deploy/__init__.py` — re-exports `setup_deploy_handler`, `run_wizard`, `validate_project_slug`, `validate_custom_cmd`.
- `clawteam/templates/gstack/skills/setup_deploy/wizard.py` — pure UI + validation (no filesystem). ~130 LOC. `_load_questionary` lazy-import + 3 questionary prompts (select/text/optional text) + 2 validators + `confirm_overwrite`.
- `clawteam/templates/gstack/skills/setup_deploy/handler.py` — filesystem side. ~150 LOC. `_find_gstack_toml` (3-tier lookup), `_DEPLOY_BLOCK_RE` negative-lookahead splice regex, `_insert_or_replace_block`, `atomic_write_text`, tomllib round-trip assertion.
- `tests/templates/gstack/skills/test_setup_deploy.py` — 11 tests (see Accomplishments for breakdown).
- `clawteam/plugins/gstack_sprint_plugin.py` — added `_setup_deploy_handler` import and `SkillRegistration(name="/setup-deploy", roles=frozenset({"sre"}), ...)` to `contribute_skills`.

## Decisions Made

- **Deny-list vs allow-list for `custom_deploy_cmd`:** went with deny-list of `{ ; | & ` $ < > \\ \n }` because allow-list regex would reject legitimate use-cases (e.g. `npm run deploy --env=prod` contains `=`; `./deploy.sh -v` contains `-`). Deny-list catches the specific shell-injection carriers without blocking ergonomic flags. Defense-in-depth: invocation path uses `shell=False` so even a bypassed metachar is argv-safe.
- **KeyboardInterrupt vs None-return on Ctrl-C:** raise `KeyboardInterrupt` from `run_wizard`. Dispatcher layer can catch and render "aborted" without leaking a sentinel value into the handler's return-type discriminator (`status ∈ {written, skipped}`).
- **Regex-splice over full TOML round-trip for writes:** preserves comments, blank lines, and key ordering in gstack.toml (T-05-05-03). Full round-trip via `tomllib.dumps` would reorder keys and drop comments — unacceptable for a config file humans edit.
- **tomllib round-trip as a hard post-render assertion:** a failed assertion raises `RuntimeError` and prevents `atomic_write_text` from running. Containment — a bug in `_render_block` or `_insert_or_replace_block` cannot corrupt the user's `gstack.toml`.
- **`args['_skip_confirm']` as an underscore-prefixed test/CLI seam:** agent-facing dispatch never passes it; tests and future `--force` CLI flag pass it explicitly. Signals "internal contract" without needing a separate code path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Wave 2 cross-executor index interference**
- **Found during:** Task 1 RED commit
- **Issue:** Plans 05-03 (/codex), 05-04 (/ship), and 05-05 (/setup-deploy) all ran in parallel against the same working tree. When I ran `git add tests/templates/gstack/skills/test_setup_deploy.py`, the parallel 05-03 executor had its `clawteam/templates/gstack/skills/codex/__init__.py` + `handler.py` staged in the shared index. My subsequent `git commit` swept them into my `test(05-05):` commit. The actual `test_setup_deploy.py` file was then captured by Plan 05-04's `feat(05-04): implement /ship 5 step functions` commit (`0256693`) via the same race. Net result: git hashes are shuffled but on-disk content is correct.
- **Fix:** Acknowledged as unavoidable Wave 2 parallel-execution artifact. Not rolled back — doing so would have destroyed 05-03's staged work. Plan 05-03's SUMMARY (`1d7dcec`) already documents the same cross-attribution symmetrically (`"parallel Plans 05-04 + 05-05 committed my staged files under their hashes"`).
- **Files affected (attribution-only — content correct):**
  - `tests/templates/gstack/skills/test_setup_deploy.py` — attributed to `0256693` (should have been in `0b52021`).
  - `clawteam/templates/gstack/skills/codex/__init__.py` + `handler.py` — attributed to `0b52021` (should have been in `05-03`'s own commit).
  - Plugin `contribute_skills` `/setup-deploy` registration — attributed to `a991ea8` (05-04's Task 2 commit) instead of my own feat commit.
- **Verification:** `git log --all --oneline -- tests/templates/gstack/skills/test_setup_deploy.py` traces the file; all 11 tests green; full `contribute_skills` returns `[/codex, /ship, /setup-deploy]` per plan verification §3.
- **Committed in:** n/a (attribution cross-wired; see commits above).

---

**Total deviations:** 1 auto-fixed (1 blocking — unavoidable concurrent-index race).
**Impact on plan:** Zero functional impact — all files correct on disk, all tests green, acceptance criteria met. Only git blame lines are shuffled.

## Issues Encountered

- **Pre-existing test cross-contamination** (already deferred by 05-01): `tests/test_evidence_schemas_phase5.py` + `tests/test_gstack_plugin.py` fail when run in the full suite due to `EvidenceSchemaRegistry` process-global state leaking between tests that register the same plugin twice. Unrelated to 05-05; each test module passes when run in isolation. Already tracked in `.planning/phases/05-tool-heavy-skills-ship-sre-codex/deferred-items.md`.
- **"3 skills registered" plan verification §3:** depended on 05-03 + 05-04 having landed by the time 05-05 ran. Both did land during my window (commits `a991ea8` + `1d7dcec`), so the assertion passes. If they had not landed, my `contribute_skills` change would still have registered `/setup-deploy` correctly — the aggregate count would just have been 1 or 2 instead of 3.

## Threat Flags

No new security surface introduced beyond what the plan's `<threat_model>` already enumerated. Mitigations applied per register:

| Threat ID | Mitigation landed |
|-----------|-------------------|
| T-05-05-01 | `validate_project_slug` full-match regex in wizard.py + test 3 |
| T-05-05-02 | `validate_custom_cmd` deny-list in wizard.py + test 4 + downstream `invoke_native_cli(shell=False)` in 05-06 |
| T-05-05-03 | `_DEPLOY_BLOCK_RE` splice + `atomic_write_text` + post-render `tomllib.loads` assertion + test 6/7 |
| T-05-05-04 | `SkillRegistration.roles=frozenset({'sre'})` + test 9 (engineer → SkillNotPermitted) |
| T-05-05-05 | `DeployConfig(**raw_cfg)` pydantic validation BEFORE write + test 10 |

## User Setup Required

None. `questionary` is already a hard clawteam dep; no external services or auth configured.

## Next Phase Readiness

- **Plan 05-06 (/land-and-deploy):** can now read `TemplateDef.deploy.provider` + `.project` + `.custom_deploy_cmd` to decide which provider CLI to invoke. The writer contract (this plan) and the reader contract (05-06) share the `DeployConfig` pydantic model so type-level invariants (provider enum, non-empty project) are enforced end-to-end.
- **Plan 05-07 (/canary):** indirectly enabled — `/canary` runs after `/land-and-deploy` which runs after `/setup-deploy` has been invoked at least once.

## Self-Check: PASSED

- [x] `clawteam/templates/gstack/skills/setup_deploy/__init__.py` exists
- [x] `clawteam/templates/gstack/skills/setup_deploy/wizard.py` exists
- [x] `clawteam/templates/gstack/skills/setup_deploy/handler.py` exists
- [x] `tests/templates/gstack/skills/test_setup_deploy.py` exists
- [x] `clawteam/plugins/gstack_sprint_plugin.py` contains `name="/setup-deploy"` registration
- [x] All 11 scoped tests green
- [x] `validate_project_slug('my-app') and not validate_project_slug('; rm')` returns True
- [x] `not validate_custom_cmd('./deploy.sh; rm') and validate_custom_cmd('./deploy.sh')` returns True
- [x] `GstackSprintPlugin().contribute_skills()` returns `/codex` + `/ship` + `/setup-deploy`
- [x] Commit `1f4e6e6` exists in git history (feat GREEN)
- [x] Commit `0b52021` exists in git history (test RED — cross-attribution acknowledged)

---
*Phase: 05-tool-heavy-skills-ship-sre-codex*
*Plan: 05*
*Completed: 2026-04-21*
