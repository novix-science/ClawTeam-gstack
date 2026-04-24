---
status: diagnosed
phase: 00-foundation-upstream-rfc
source:
  - 00-01-env-scrub-SUMMARY.md
  - 00-02-doctor-cli-SUMMARY.md
  - 00-03-default-model-profile-SUMMARY.md
  - 00-04-template-regression-matrix-SUMMARY.md
  - 00-05-upstream-rfc-SUMMARY.md
started: 2026-04-16T10:22:50Z
updated: 2026-04-16T10:24:30Z
---

## Current Test

[testing complete]

## Tests

### 1. Env Scrub — Secrets Blocked from Hook Subprocess Env
expected: |
  `python -m pytest tests/test_env_scrub.py -q` passes (31 cases). Parent-process
  secrets (e.g. `OPENAI_API_KEY`, `GITHUB_TOKEN`, `DB_PASSWORD`) never appear in
  the scrubbed shell env handed to hook subprocesses, in /learn entries, or in
  event-log files. Hook metadata env keys (`CLAWTEAM_*`, `OH_*`) remain intact.
result: pass
evidence: "python -m pytest tests/test_env_scrub.py -q → 31 passed in 0.12s"

### 2. `clawteam doctor` — Human-Readable Diagnostic Report
expected: |
  Running `clawteam doctor` on this machine prints a per-tool report covering
  Playwright/Chromium, codex, ngrok, and watchdog. For any missing optional
  tool, the output includes the correct per-OS install hint
  (`pip install 'clawteam[browser]' && playwright install chromium`,
  `npm install -g @openai/codex`, platform-specific ngrok, `pip install watchdog`).
  The command exits 0 regardless of which tools are missing.
result: issue
reported: "Chromium install hint printed as `pip install 'clawteam' && playwright install chromium` — the `[browser]` extra is missing. Rich markup parser interprets `[browser]` as a tag and strips it."
severity: major
evidence: "clawteam doctor stdout shows 'pip install clawteam' (no [browser]); clawteam --json doctor install_hint field is correct"

### 3. `clawteam doctor --json` — Machine-Readable Output
expected: |
  Running `clawteam doctor --json` emits valid JSON containing one entry per
  check (playwright, codex, ngrok, watchdog) with `installed` and
  `install_hint` fields; the command exits 0.
result: pass
evidence: "clawteam --json doctor → valid JSON with found/path/kind/install_hint per tool; exit 0; chromium install_hint preserved as 'clawteam[browser]' in JSON path"

### 4. Default Model Profile — Balanced-by-Default Config Resolution
expected: |
  Loading a `ClawTeamConfig` with no `default_model_profile` set yields
  `"balanced"` (not `"quality"`). Setting the shell env var
  `CLAWTEAM_DEFAULT_MODEL_PROFILE=quality` before loading is ignored — the
  resolved config still returns `"balanced"`. Existing pre-change config files
  continue to load without error. Verified by `python -m pytest tests/test_config.py::TestDefaultModelProfile -v`.
result: pass
evidence: "python -m pytest tests/test_config.py::TestDefaultModelProfile -v → 7 passed (defaults, legacy load, env-ignore, roundtrip all covered)"

### 5. Template Regression Matrix — All Six Packaged Templates Launch
expected: |
  `python -m pytest tests/test_template_regression_matrix.py -v` passes all 12
  cases. `clawteam launch <template>` works via Typer CLI for each of
  `software-dev`, `hedge-fund`, `code-review`, `harness-default`,
  `research-paper`, and `strategy-room`. CI's existing
  `python -m pytest tests/ -v --tb=short` invocation auto-discovers the new
  module with no workflow edits.
result: pass
evidence: "python -m pytest tests/test_template_regression_matrix.py -v → 12 passed; all 6 templates launch cleanly + spawn-kwargs preserved"

### 6. Upstream RFC — PhaseRegistry / HarnessPlugin / SprintState / InteractionGate Documented
expected: |
  `docs/rfcs/README.md` exists as the RFC index with an entry for RFC 001.
  `docs/rfcs/001-phase-registry.md` exists and documents the `PhaseRegistry`
  class, the optional `HarnessPlugin.contribute_phases()` /
  `contribute_phase_roles()` / `contribute_review_routers()` hooks with empty
  defaults, `SprintState`, and `InteractionGate`. RFC contains additive-only
  contract guarantees and a worked `software-dev.toml` compatibility example
  showing no template changes required.
result: issue
reported: "RFC 001 only documents contribute_phases(); contribute_phase_roles() and contribute_review_routers() — named in Phase 0 Success Criterion #4 — are not specified. Implementer SUMMARY notes this was a deliberate scope reduction; the acceptance criterion requires all three."
severity: major
evidence: "grep contribute_(phase_roles|review_routers) docs/rfcs/001-phase-registry.md → 0 matches; contribute_phases matched 11 times"

### 7. Upstream RFC — Opened Against Upstream with Maintainer Acknowledgement
expected: |
  RFC 001 has been opened as a PR or discussion thread against the upstream
  ClawTeam repository (not just committed to this fork) and has received at
  least one maintainer acknowledgement — satisfying Phase 0 Success Criterion
  #4. If this upstream submission has not happened yet, the test is blocked
  pending that action.
result: blocked
blocked_by: upstream-submission
reason: "RFC committed only to fork (origin: novix-science/ClawTeam-gstack). upstream remote exists (HKUDS/ClawTeam) but no PR or discussion has been opened and no maintainer acknowledgement is on record. Requires human action to submit upstream."

## Summary

total: 7
passed: 4
issues: 2
pending: 0
skipped: 0
blocked: 1

## Gaps

- truth: "`clawteam doctor` human-readable output prints the correct Chromium install hint including the `[browser]` extra"
  status: failed
  reason: "User reported: Chromium install hint printed as `pip install 'clawteam' && playwright install chromium` — the `[browser]` extra is missing. Rich markup parser interprets `[browser]` as a tag and strips it."
  severity: major
  test: 2
  root_cause: "clawteam/cli/commands.py:1224 wraps the install_hint string in `[dim]...[/dim]` Rich markup. The install_hint value `pip install 'clawteam[browser]' && playwright install chromium` contains the literal substring `[browser]`, which Rich interprets as an unknown markup tag and silently elides. The JSON output path bypasses Rich, so `install_hint` is correct there."
  artifacts:
    - path: "clawteam/cli/commands.py"
      line: 1224
      issue: "Rich console.print uses `[dim]{install_hint}[/dim]` — bracketed content inside install_hint is parsed as markup"
  missing:
    - "Escape the install_hint before embedding in Rich markup (e.g. `rich.markup.escape(hint)` or pass as a `Text` object with style='dim')"
    - "Add a regression test asserting the human-readable doctor output contains the literal substring `'clawteam[browser]'` when chromium is missing"
  debug_session: ""

- truth: "RFC 001 documents all three optional HarnessPlugin hooks (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`) with empty defaults"
  status: failed
  reason: "User reported: RFC 001 only documents contribute_phases(); contribute_phase_roles() and contribute_review_routers() — named in Phase 0 Success Criterion #4 — are not specified."
  severity: major
  test: 6
  root_cause: "During Plan 00-05 execution, the implementer scoped the RFC to four primitives (`PhaseRegistry`, `contribute_phases`, `SprintState`, `InteractionGate`). The Phase 0 acceptance criterion names three hooks (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`) with empty defaults, the additive-only contract, and a worked `software-dev.toml` compatibility example. The other two hooks were deferred as 'later hook proposals' per SUMMARY.md, creating a gap against the criterion."
  artifacts:
    - path: "docs/rfcs/001-phase-registry.md"
      issue: "Section 4 (API Surface) covers contribute_phases() only; no section for contribute_phase_roles() or contribute_review_routers()"
  missing:
    - "Add Section 4.x for `HarnessPlugin.contribute_phase_roles()` specifying signature, empty default, additive-only contract, and plugin-use example"
    - "Add Section 4.x for `HarnessPlugin.contribute_review_routers()` specifying signature, empty default, additive-only contract, and plugin-use example"
    - "Update Section 1 (Summary) and the RFC title to reflect all three hooks"
    - "Update the `software-dev.toml` worked example to show all three hooks default to empty and the template's phase/role/router behavior is unchanged"
  debug_session: ""
