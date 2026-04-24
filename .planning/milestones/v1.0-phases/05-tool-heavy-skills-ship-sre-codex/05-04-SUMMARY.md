---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 04
subsystem: skill-ship
tags: [skill-ship, github-cli, coverage-audit, bootstrap-tests, pipeline]
requirements: [SKILL-14]
dependencies:
  requires:
    - SKILL-13-substrate (from Plan 05-01: invoke_native_cli, SkillRegistration, SkillDispatcher, SkillUnavailable)
    - SKILL-14-substrate (from Plan 05-02: ShipNotes Phase-5 optional fields)
    - gstack.toml [ship] (from Plan 05-01: TemplateDef.ship.coverage_threshold)
  provides:
    - "/ship skill handler + 5-step pipeline (SKILL-14)"
    - "ship-notes.md writer (Phase-5 shape with ship_status / steps_completed / failure_step / pr_url / coverage)"
    - "language-aware test bootstrap (D-06 python + node smoke-test writers)"
  affects:
    - clawteam/plugins/gstack_sprint_plugin.py (contribute_skills now carries /ship alongside /codex + /setup-deploy)
tech-stack:
  added: []
  patterns:
    - "pure-function pipeline (D-05, Pitfall 4 enforcement — NO state.py, NO file_locked around pipeline state)"
    - "StepResult dataclass with success + details dict (merged into ship-notes.md)"
    - "argv-literal CLI invocation via invoke_native_cli (shell=False hard-coded; T-05-04-01 mitigation)"
    - ".get-chain coverage.json parsing (D-15 binary-file adversarial-safe; T-05-04-02 mitigation)"
    - "bootstrap-and-halt when no tests detected (D-06 question artifact emitter)"
key-files:
  created:
    - clawteam/templates/gstack/skills/ship/__init__.py
    - clawteam/templates/gstack/skills/ship/steps.py
    - clawteam/templates/gstack/skills/ship/handler.py
    - tests/test_ship_skill.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py
decisions:
  - "/ship is a linear pipeline, not a state machine — on failure user re-runs, doesn't resume (D-05 + Pitfall 4)."
  - "Bootstrap smoke test halts with success=False + bootstrapped=True so the handler writes ship-notes.md with failure_step=test; user fills in the real smoke test and re-runs /ship."
  - "Coverage threshold is a fraction 0..1 (not percent); gstack.toml [ship] coverage_threshold=0.7 means 70%; default 0.5."
  - "go/rust coverage integration is v1.x — Phase-5 audit_coverage returns success with coverage=None for those languages so /ship can still ship; python + node get real json parsing."
  - "Auto-invoke of /document-release deferred to Plan 05-07 — this plan leaves auto_invoked_skills=[] on success; Plan 05-07 appends the chain."
  - "Tests placed flat at tests/test_ship_skill.py (not tests/templates/gstack/skills/test_ship.py) — follows the established convention from Plan 05-02 decision."
  - "ship-notes.md preserves the Phase-3 required trio (deploy_url / ship_step / notes) by synthesizing them from Phase-5 context; deploy_url='<pending>' via the D-02 tool-availability stub when Phase-5 PR URL not yet available."
metrics:
  completed_at: 2026-04-21T22:40:00Z
  duration: ~35min
  tasks: 2
  files_created: 4
  files_modified: 1
  tests_added: 18
  loc_added: ~1176
  commits:
    - f3113d8 test(05-04): add failing tests for /ship skill (18 tests)
    - 0256693 feat(05-04): implement /ship 5 step functions (Task 1)
    - a991ea8 feat(05-04): ship_handler + plugin registration (Task 2)
---

# Phase 5 Plan 04: /ship skill (SKILL-14) Summary

5-step linear Build-to-Ship pipeline — `sync_main → run_tests → audit_coverage → push → open_pr` — with language-aware test bootstrapping (D-06), D-15 adversarial-safe coverage parsing, and always-written `ship-notes.md` artifact for both success and failure outcomes.

## What Shipped

Three new source files under `clawteam/templates/gstack/skills/ship/`:

- **`steps.py`** (404 LOC) — `StepResult` dataclass + 5 pure-function step handlers:
  - `sync_main(cwd, branch)` — `git fetch origin main` + `git merge origin/main`; conflict returns `success=False, details={"conflict": True}`.
  - `run_tests(cwd, sprint_dir)` — language detect (python/node/go/rust/unknown) → bootstrap smoke test + emit blocking question artifact if no tests detected → halt with `bootstrapped=True`; else run `pytest -x` / `npx vitest run` / `go test ./...` / `cargo test`.
  - `audit_coverage(cwd, threshold)` — `pytest --cov --cov-report=json` for python, `npx c8 --reporter=json-summary ...` for node; `.get`-chain parser tolerates D-15 binary-file `not_coverable` lists without crashing.
  - `push(cwd, branch)` — `git push -u origin <branch>`.
  - `open_pr(cwd, title, body)` — `gh pr create ...`; missing `gh` → `SkillUnavailable` with install hint; PR URL extracted as last `http`-prefixed line of stdout.
- **`handler.py`** (265 LOC) — `ship_handler(ctx, role, args)` composes the 5 steps as a linear pipeline. On first-step failure, halts and writes `ship-notes.md` with `ship_status='failed'` + `failure_step=<name>`. On 5-step success, writes `ship_status='succeeded'` + PR URL + coverage. `_resolve_threshold(ctx)` reads `tmpl.ship.coverage_threshold` (default 0.5). `gh_available()` is the `SkillRegistration.tool_available` probe.
- **`__init__.py`** (17 LOC) — docstring only; sub-modules imported on demand so Task-1 step tests do not transitively import handler.py.

Plugin registration added to `clawteam/plugins/gstack_sprint_plugin.py`:

```python
SkillRegistration(
    name="/ship",
    roles=frozenset({"shipper"}),
    handler=_ship_handler,
    tool_available=_ship_gh_available,
    install_hint="apt install gh | brew install gh | winget install GitHub.cli",
),
```

Tests: `tests/test_ship_skill.py` (490 LOC, 18 tests) — 11 step-level tests (including D-15 adversarial coverage.json with 50 binary files) + 7 handler-orchestration tests (happy path, halt-on-first-failure, coverage-halt, template-threshold resolution, role gating via dispatcher, plugin-registration presence, `gh_available` detection).

## Verification Results

Automated verification from plan `<verify>` blocks — all green:

```
tests/test_ship_skill.py                   18 passed
tests/test_gstack_plugin.py                 6 passed (plugin still registers 10 schemas + /codex+/ship+/setup-deploy)
tests/test_plugin_manager_skills.py        10 passed (no duplicate-name collisions)
tests/test_skill_dispatcher.py             11 passed
tests/test_skill_registration.py           10 passed
tests/test_skill_errors.py                 11 passed
tests/test_ship_notes_phase5_fields.py      7 passed (BC locked)
```

Plugin roster cross-check (from plan's `<verification>` block 2):

```
$ python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; \
             print(sorted(s.name for s in GstackSprintPlugin().contribute_skills()))"
['/codex', '/setup-deploy', '/ship']
```

Acceptance criteria (all satisfied):

- `grep -q "def sync_main|def run_tests|def audit_coverage|def push|def open_pr" clawteam/templates/gstack/skills/ship/steps.py` — 5/5 matches.
- `grep -q "def ship_handler" clawteam/templates/gstack/skills/ship/handler.py` — found.
- `grep -q 'name="/ship"' clawteam/plugins/gstack_sprint_plugin.py` — found.
- `grep -q 'frozenset({"shipper"})' clawteam/plugins/gstack_sprint_plugin.py` — found.
- `test ! -f clawteam/templates/gstack/skills/ship/state.py` — true (Pitfall 4 enforced).
- `grep -q "shell=True" clawteam/templates/gstack/skills/ship/` — 0 matches.

## Deviations from Plan

**Cross-executor interleave (Waves 2 parallel — Plans 03/05 sibling executors)**

1. **[Rule 3 — Blocking] Test file path moved to flat `tests/test_ship_skill.py`.**
   Plan specified `tests/templates/gstack/skills/test_ship.py`. Existing repo convention (set by Plan 05-02 STATE.md decision) places tests flat at `tests/`. Following established convention; test passes all coverage regardless of path.

2. **[Rule 3 — Blocking] Plugin edit landed in one snapshot with sibling edits.**
   Plan 05-03 (/codex) and Plan 05-05 (/setup-deploy) sibling executors co-edited `gstack_sprint_plugin.py` during this plan's Task 2 write. The resulting commit `a991ea8` carries all three `contribute_skills` entries (/codex + /ship + /setup-deploy) in one diff. This mirrors the Plan 04-10 Task 3 interleave pattern documented in STATE.md. My `/ship` `SkillRegistration` is preserved verbatim inside the returned list; sibling executors' entries are adjacent but independently functional.

3. **[Rule 2 — Missing critical functionality] ShipNotes Phase-3 required-field synthesis in handler.**
   `ShipNotes` inherits Phase-3 required fields (`deploy_url`, `ship_step`, `notes ≥20 chars`) that the plan's sample `_write_ship_notes` did NOT populate — writing plain Phase-5 fields would trigger pydantic validation failure. Added explicit synthesis: `deploy_url = pr_url or "<pending>"` (D-02 stub), `ship_step = failure_step or "pr"` mapped into the Phase-3 Literal enum, and `notes = f"ship_status=...; steps_completed=...; branch=..."` which is always ≥20 chars in practice. This is a correctness requirement (without it, the happy-path test writes a schema-invalid artifact).

No architectural decisions required (Rule 4 not triggered).

## Threat Model Status

All four threats in the plan's `<threat_model>` are mitigated:

| Threat | Mitigation in code |
|--------|-------------------|
| T-05-04-01 (branch name shell metachars) | All `steps.py` + `handler.py` call sites use `invoke_native_cli` which hard-codes `shell=False`; branch names flow as argv-literal elements. Verified via `grep "shell=True" clawteam/templates/gstack/skills/ship/` → 0 matches. |
| T-05-04-02 (malformed coverage.json) | `_parse_python_coverage` uses `.get` chain + try/except around `json.loads` + `float()` conversion; test `test_audit_coverage_binary_files_skipped_adversarial` locks this behavior. |
| T-05-04-03 (GITHUB_TOKEN disclosure) | Accepted per plan — gh's own auth model owns token handling; `scrub_env` in `invoke_native_cli` prevents pre-call leak. |
| T-05-04-04 (gh hang) | `open_pr` sets `timeout=60.0`; `subprocess.TimeoutExpired` propagates through `invoke_native_cli` unchanged. |

No new threat surfaces introduced beyond what the plan enumerated.

## Known Stubs

None. No hardcoded empty values or placeholder text that would misrepresent behavior. The `<pending>` literal in `deploy_url` is documented in the ShipNotes schema (D-02 Phase-5 tool-availability stub) and is intentional — Plan 05-06 `/land-and-deploy` replaces it with the real deploy URL.

## Deferred

- **/document-release auto-invoke** — deferred to Plan 05-07. The handler leaves `auto_invoked_skills=[]` on success; Plan 05-07 wires the chain.
- **go/rust coverage integration** — deferred to v1.x. `audit_coverage` returns `success=True` with `coverage=None` for those languages so /ship doesn't block on absent parsing.
- **jest-vs-vitest detection for JS test runner** — deferred to v1.x. `run_tests` hard-codes `npx vitest run` for node; `package.json` parsing for jest is a v1.x polish.

## Self-Check: PASSED

Files verified on disk:
- `clawteam/templates/gstack/skills/ship/__init__.py` — FOUND
- `clawteam/templates/gstack/skills/ship/steps.py` — FOUND
- `clawteam/templates/gstack/skills/ship/handler.py` — FOUND
- `tests/test_ship_skill.py` — FOUND
- `clawteam/plugins/gstack_sprint_plugin.py` modified — FOUND (contains `name="/ship"` + `frozenset({"shipper"})`)

Commits verified in git log:
- `f3113d8` test(05-04): add failing tests for /ship skill (18 tests) — FOUND
- `0256693` feat(05-04): implement /ship 5 step functions (Task 1) — FOUND
- `a991ea8` feat(05-04): ship_handler + plugin registration (Task 2) — FOUND
