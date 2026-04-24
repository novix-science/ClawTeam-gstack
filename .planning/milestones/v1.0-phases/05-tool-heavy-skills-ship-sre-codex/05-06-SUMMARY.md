---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 06
subsystem: gstack.skills
tags:
  - skill-land-and-deploy
  - ci-wait
  - deploy-health-probe
  - pitfall-3-closure
  - pitfall-8-closure
requires:
  - clawteam.spawn.invoke.invoke_native_cli   # Plan 05-01 (shell=False wrapper)
  - clawteam.plugins.skill_registration.SkillRegistration
  - clawteam.plugins.skill_errors.SkillPreconditionError
  - clawteam.templates.gstack.schemas.deploy_notes.DeployNotes  # Plan 05-02
  - clawteam.fileutil.atomic_write_text
provides:
  - clawteam.templates.gstack.skills.land_and_deploy.handler.land_and_deploy_handler
  - SkillRegistration(name="/land-and-deploy", roles={"shipper"})
affects:
  - GstackSprintPlugin.contribute_skills  # now 4 registrations (codex, ship, setup-deploy, land-and-deploy)
tech_stack_added: []
tech_stack_patterns:
  - exponential-backoff health probe (1.5x growth, cap 15s, deadline-bounded)
  - hand-rolled YAML frontmatter emitter (pyyaml-free, mirrors /ship)
  - simple frontmatter parser (str/bool/null/inline-JSON values only)
  - provider-dispatch table via plain if/elif in _build_deploy_cmd
key_files:
  created:
    - clawteam/templates/gstack/skills/land_and_deploy/__init__.py
    - clawteam/templates/gstack/skills/land_and_deploy/handler.py
    - tests/templates/gstack/skills/test_land_and_deploy.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py
decisions:
  - "Handler always writes deploy.md — every failure path (precondition, CI timeout, deploy nonzero exit, health probe timeout) still produces a DeployNotes artifact with deploy_status in {failed, pending}. EvidenceGate downstream can then surface the outcome uniformly; no silent failures."
  - "Handler's own health probe precedes EvidenceGate's 10 s HEAD (Pitfall 3). Exponential backoff up to deploy_verify_timeout_seconds (default 120) absorbs CDN warm-up so the gate is not false-failed by slow DNS/SSL propagation."
  - "custom_deploy_cmd is run through shlex.split in POSIX mode AND invoke_native_cli hard-codes shell=False — two independent defenses mean even if the /setup-deploy wizard's deny-list fails open, shell metacharacters in custom commands stay as literal argv elements (T-05-06-01)."
  - "Frontmatter parser is hand-rolled (30 LOC) rather than a pyyaml dep; the only fields read from ship-notes.md are ship_status + pr_url, both simple scalars. Matches the repo-wide no-pyyaml convention used by /ship handler."
  - "Deploy URL extraction uses a generous regex (https?://[^\\s]+) against the first URL in stdout. Vercel, Netlify, and Fly all print their deploy URL on stdout as part of their success output; custom providers are expected to do the same."
metrics:
  duration_minutes: 25
  tasks_completed: 1
  files_created: 3
  files_modified: 1
  tests_added: 13
  completed_date: "2026-04-21"
---

# Phase 5 Plan 05-06: /land-and-deploy Summary

`/land-and-deploy` merged-PR deploy action implemented as a pure-function
4-phase pipeline (precondition → CI wait → provider deploy → health probe)
that always emits `deploy.md` per DeployNotes so downstream EvidenceGate
surfaces every failure mode.

## What shipped

- **`clawteam/templates/gstack/skills/land_and_deploy/handler.py`** — the
  `land_and_deploy_handler` entry point plus helpers: `_read_ship_notes`
  (precondition check), `_build_deploy_cmd` (provider dispatch),
  `_head_probe` + `_wait_for_health` (exponential-backoff health poll),
  `_extract_deploy_url`, `_write_deploy_notes` (atomic frontmatter emitter),
  `_emit_question_run_setup` (no-deploy-block question artifact).
- **`clawteam/templates/gstack/skills/land_and_deploy/__init__.py`** —
  re-exports the handler.
- **Plugin registration** — `GstackSprintPlugin.contribute_skills` now
  returns 4 `SkillRegistration`s. `/land-and-deploy` is gated
  `roles=frozenset({"shipper"})` and carries an install hint spanning
  `gh` + the four deploy backends.
- **13 tests** (`tests/templates/gstack/skills/test_land_and_deploy.py`)
  cover every behaviour from the plan's `<behavior>` table: precondition
  missing/failed, CI wait happy/timeout, vercel/netlify/fly/custom deploy
  happy paths, adversarial health-probe timeout (Pitfall 3 case),
  no-deploy-block pending path, role gate via SkillDispatcher, plugin
  registration, and shell-injection safety.

## Threat mitigations landed

| Threat ID   | Mitigation                                                                                   |
| ----------- | -------------------------------------------------------------------------------------------- |
| T-05-06-01  | `shlex.split` + `invoke_native_cli(shell=False)` (test_shell_injection_via_custom_cmd_safe)  |
| T-05-06-03  | 30-min timeout on `gh pr checks --watch`; TimeoutExpired → deploy_status=failed              |
| T-05-06-04  | Exponential-backoff health probe with deploy_verify_timeout_seconds deadline                 |
| T-05-06-05  | `invoke_native_cli` uses `scrub_env(os.environ)` by default — VERCEL/NETLIFY tokens scrubbed |
| T-05-06-06  | `SkillRegistration.roles = frozenset({"shipper"})` enforced by SkillDispatcher               |
| T-05-06-02  | Accepted (ship-notes.md writer is /ship in same trust domain)                                |

## Deviations from Plan

**None** on correctness or security. Three minor execution-time adjustments:

1. **[Rule 3 - Test ergonomics]** Added a local `from ... import
   land_and_deploy_handler` inside each test function. The test file's
   top-level imports didn't expose the handler name (only
   `SkillPreconditionError`), so the RED run failed with `NameError`
   before reaching the real assertion. Net effect: tests are explicit
   about what they exercise; no behavioural change.
   - Files modified: `tests/templates/gstack/skills/test_land_and_deploy.py`
   - Commit: `a364494`

2. **[Scope boundary]** An external editor pre-populated
   `clawteam/plugins/gstack_sprint_plugin.py` with Plan 05-07's
   `/document-release` registration (import + docstring + registration
   block) while Plan 05-06 was being executed. I scoped my commit to
   **only Plan 05-06 content**: stripped the 05-07 additions from the
   plugin file before `git add`, committed, then restored the 05-07
   additions in the working copy so the parallel Plan 05-07 executor
   can land them atomically with its own handler. No 05-07 files were
   staged or committed.

3. **[Rule 3 - Retry semantics]** `_wait_for_health` now probes once
   up-front BEFORE the first sleep so a caller passing a short
   `deploy_verify_timeout_seconds` (≤2s) still performs at least one
   probe. Without this, the adversarial test with `timeout=3` would
   have ambiguous semantics around whether a single probe was attempted.

## Authentication gates

None encountered. The handler's failure modes (gh timeout, deploy cmd
non-zero) are simulated via monkeypatch in tests; no real CLI auth was
required during execution.

## Acceptance criteria

| Criterion                                                                             | Status |
| ------------------------------------------------------------------------------------- | ------ |
| `grep -q "def land_and_deploy_handler" .../handler.py`                                | PASS   |
| `grep -q 'name="/land-and-deploy"' .../gstack_sprint_plugin.py`                       | PASS   |
| `grep -q 'frozenset({"shipper"})' .../gstack_sprint_plugin.py` ≥ 2 hits               | PASS (3 hits — /ship + /land-and-deploy + /document-release WIP) |
| `grep -q "shell=True" .../handler.py` returns no matches                              | PASS (0 hits) |
| `pytest tests/templates/gstack/skills/test_land_and_deploy.py -q` → 13 passed        | PASS   |
| BC: prior skill tests still green                                                     | PASS (74 passing across ship/skill-registration/plugin-manager tests) |

## Known Stubs

None. Every code path — including the pending / failed branches — writes
a fully-formed DeployNotes artifact with valid schema values.

## Self-Check: PASSED

- `clawteam/templates/gstack/skills/land_and_deploy/handler.py`: FOUND
- `clawteam/templates/gstack/skills/land_and_deploy/__init__.py`: FOUND
- `tests/templates/gstack/skills/test_land_and_deploy.py`: FOUND
- `.planning/phases/05-tool-heavy-skills-ship-sre-codex/05-06-SUMMARY.md`: FOUND
- Commit `fe6b89f` (RED): FOUND
- Commit `a364494` (GREEN): FOUND
