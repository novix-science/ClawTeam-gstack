---
phase: 00-foundation-upstream-rfc
verified: 2026-04-16T19:05:00Z
status: human_needed
score: 5/5 must-haves verified (SC#4 split: doc-artifact PASS + upstream-submission HUMAN)
overrides_applied: 0
re_verification:
  previous_status: none (initial verification after Wave 3 gap-closure)
  previous_score: UAT recorded 4 pass / 2 issues / 1 blocked
  gaps_closed:
    - "Test 2 (doctor `[browser]` elision) — closed by plan 00-06 via rich.markup.escape"
    - "Test 6 (RFC missing two hooks) — closed by plan 00-07 via §4.3a and §4.3b additions"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Open `docs/rfcs/001-phase-registry.md` as a PR or discussion thread against `HKUDS/ClawTeam` upstream, tag a maintainer, and obtain at least one acknowledgement (Phase 0 Success Criterion #4, second clause)"
    expected: "PR or discussion URL recorded in ROADMAP.md Phase 0 section; maintainer ack timestamp noted"
    why_human: "GitHub PR creation against an external org requires authenticated human action and a maintainer reply is asynchronous — neither can be performed or polled by the verifier. The document artifact (both README.md + 001-phase-registry.md) is fully satisfied; only the upstream submission step remains."
---

# Phase 0: Foundation & Upstream RFC — Verification Report

**Phase Goal:** Lay down cheap-to-add-now, expensive-to-retrofit foundations (backwards-compat test matrix, env secret-scrubbing, default model profile, missing-tool detection) and get upstream buy-in on the plugin API shape before any core code lands.

**Verified:** 2026-04-16T19:05:00Z
**Status:** human_needed
**Re-verification:** Yes — initial verification performed AFTER Wave 3 gap-closure (plans 00-06, 00-07) completed on top of the original 5-plan Phase 0 scope.

## Goal Achievement

### Observable Truths (5 Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Full existing test suite passes against 6 packaged templates via `tests/test_template_regression_matrix.py` | VERIFIED | `.venv-sys/bin/python -m pytest tests/ -q` → 612 passed in 105s; template-matrix file has 12 parametrized cases (6 templates × 2 tests) via RecordingBackend mock |
| 2 | Spawn + event hooks never leak `*_TOKEN`/`*_KEY`/`*_SECRET`/`*PASSWORD*`-shaped env values | VERIFIED | `clawteam/events/hooks.py:96` calls `env = scrub_env(_env_snapshot(event))` before `subprocess.run`; 34 tests in `tests/test_env_scrub.py` including end-to-end shell-hook integration test seeding `MY_API_KEY`/`GITHUB_TOKEN`/`DB_PASSWORD` and asserting none appear in dumped subprocess env |
| 3 | `clawteam doctor` on a machine without optional tools prints per-OS install hints and exits 0 | VERIFIED | Live `clawteam doctor` run: exit 0; chromium missing hint shows `pip install 'clawteam[browser]' && playwright install chromium` literally (Rich elision fixed by plan 00-06); watchdog shows `pip install watchdog`; codex and ngrok detected green. 6 tests in `tests/test_doctor.py` all pass, including the two 00-06 regression guards |
| 4a | RFC document exists with three optional HarnessPlugin hooks, PhaseRegistry shape, additive-only guarantees, and a worked software-dev example | VERIFIED | `docs/rfcs/001-phase-registry.md`: 846 lines; all 8 numbered sections present; §4.3 (contribute_phases), §4.3a (contribute_phase_roles), §4.3b (contribute_review_routers) all with signatures, empty defaults, Requirements lists, ABC ASCII boxes, and plugin-use examples; §4.7 lists 8 compatibility guarantees; §4.8 worked example traces software-dev.toml showing all three hooks default to empty |
| 4b | RFC opened as PR/discussion against `HKUDS/ClawTeam` upstream with at least one maintainer acknowledgement | HUMAN NEEDED | `gh pr list --repo HKUDS/ClawTeam --search "RFC 001 phase-registry"` returned zero results; no upstream PR or discussion exists yet. The document artifact is ready; the external submission step requires human action and an asynchronous maintainer reply that cannot be verified programmatically. |
| 5 | `clawteam/templates/` scaffolding reads default `model_profile = "balanced"` when unset; rejects `quality` as silent default | VERIFIED | `clawteam/config.py:55` declares `default_model_profile: str = "balanced"`; `get_effective()` env_map at lines 106-124 deliberately omits `default_model_profile`; 7 `TestDefaultModelProfile` tests pass including `test_env_var_is_ignored_by_get_effective` which asserts `CLAWTEAM_DEFAULT_MODEL_PROFILE=quality` resolves to `('balanced', 'default')` |

**Score:** 5/5 truths verified at the phase level. SC#4 is split: the document artifact is fully satisfied (4a); only the upstream-submission clause (4b) is pending human action.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `clawteam/secrets.py` | Pure `scrub_env` helper with deny regex | VERIFIED | 25 lines; `_SECRET_KEY_RE` compiled regex (line 8-11); `_REDACTED = "[REDACTED]"`; `scrub_env(Mapping[str,str]) -> dict[str,str]` pure function (line 15); zero clawteam.* imports so it can be imported by `events/hooks.py` without cycles |
| `clawteam/events/hooks.py` | `scrub_env` wired at the leak site | VERIFIED | Line 16: `from clawteam.secrets import scrub_env`; line 78: `_env_snapshot(event)` helper extracted; line 96: `env = scrub_env(_env_snapshot(event))` called before `subprocess.run` |
| `clawteam/config.py` | `default_model_profile: str = "balanced"` field; no env_map entry | VERIFIED | Line 55: field declared with balanced default; lines 106-124: env_map explicitly omits `default_model_profile` with inline comment explaining "non-default model tiers must be an explicit CLI or config-file opt-in" |
| `clawteam/cli/commands.py` | `@app.command("doctor")` with `_DOCTOR_TOOLS` tuple, `_doctor_install_hint`, rich+json output, Rich-markup-safe render | VERIFIED | Lines 36-41: `_DOCTOR_TOOLS` tuple (4 tools); lines 44+: `_doctor_install_hint` helper with per-OS dispatch; lines 1191-1228: `@app.command("doctor")` registered; `_human` closure at line 1213 imports `rich.markup.escape` and wraps both `info['path']` and `info['install_hint']` (lines 1221, 1226) — Rich-markup-safe rendering |
| `tests/test_env_scrub.py` | Unit + integration coverage | VERIFIED | 101 lines; `TestScrubEnv` class with 6 test methods (14-key redaction parametrize + 12-key preservation parametrize + 4 direct); 1 end-to-end shell-hook integration test; 34 total cases |
| `tests/test_doctor.py` | Style B flat tests covering found/missing/json/per-OS/browser-extra | VERIFIED | 137 lines; 6 flat test functions: missing-hints, found-tools, json-shape, platform-dispatch, browser-extra-regression (plan 06), json-unescaped-guardrail (plan 06); all pass |
| `tests/test_config.py::TestDefaultModelProfile` | 7 tests covering default, BC load, env-ignore, roundtrip, scalar-keys | VERIFIED | 7 tests appended (lines 115-147); all pass; `test_env_var_is_ignored_by_get_effective` is the Pitfall #12 regression guard |
| `tests/test_template_regression_matrix.py` | Parametrized CliRunner+RecordingBackend matrix over 6 templates | VERIFIED | 122 lines; `TEMPLATE_NAMES` list has all 6 templates; 2 parametrized test functions producing 12 total cases; wall time 1.03s |
| `docs/rfcs/README.md` | RFC index with 001 entry, three hooks named in title cell | VERIFIED | 27 lines; preamble, process section, index table; line 27 names all three hooks: "three HarnessPlugin hooks (contribute_phases / contribute_phase_roles / contribute_review_routers)" |
| `docs/rfcs/001-phase-registry.md` | 8-section Rust-style RFC with three hooks, PhaseRegistry, SprintState, InteractionGate, worked example | VERIFIED | 846 lines (target ≥750); all 8 numbered H2 sections present; §4.3 + §4.3a + §4.3b cover the three hooks; §4.4 `SprintState`, §4.5 `InteractionGate`, §4.6 Integration Contract, §4.7 (8 compatibility guarantees), §4.8 worked example showing software-dev.toml unchanged |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `clawteam/events/hooks.py::_make_shell_handler` | `clawteam.secrets::scrub_env` | import + call on env before subprocess.run | WIRED | Line 16 imports; line 96 calls `scrub_env(_env_snapshot(event))` in the exact order — snapshot first, scrub second — per PATTERNS invariant |
| `clawteam/cli/commands.py::doctor::_human` | `rich.markup.escape` | lazy import + wrap install_hint | WIRED | Line 1214: lazy `from rich.markup import escape`; line 1221 wraps path; line 1226 wraps install_hint |
| `clawteam/cli/commands.py::doctor` | `shutil.which` + `importlib.util.find_spec` | probe each `_DOCTOR_TOOLS` entry | WIRED | Lines 1194-1195: lazy imports; lines 1198-1211: kind-dispatched probing loop |
| `clawteam/config.py::ClawTeamConfig.default_model_profile` | `get_effective` env_map | deliberately NOT wired (Pitfall #12 prevention) | WIRED (as designed) | Line 55 declares the field; lines 106-124 explicitly omit the key from env_map with inline comment; test `test_env_var_is_ignored_by_get_effective` guards against re-introduction |
| `tests/test_template_regression_matrix.py` | `clawteam/cli/commands.py::launch` | `CliRunner().invoke(app, ["launch", template, ...])` | WIRED | Line 54-68: CliRunner invocation; line 50: monkeypatch injects RecordingBackend |
| `docs/rfcs/001-phase-registry.md §4.8` | `clawteam/templates/software-dev.toml` | worked-example trace of launch with all three hooks defaulting to empty | WIRED | Worked example at line 685+ shows software-dev.toml launches unchanged; phase-role and review-router hooks both demonstrated as returning `{}` and `[]` respectively |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `doctor` command `checks` dict | tool detection results | `shutil.which` + `importlib.util.find_spec` against real host | Yes — on this host: codex + ngrok OK with real paths; chromium + watchdog missing with install hints populated | FLOWING |
| `scrub_env` redaction | env key→redacted value | `re.search` against input keys using compiled `_SECRET_KEY_RE` | Yes — 14 secret-shaped keys parametrize all redact to `[REDACTED]` | FLOWING |
| `get_effective("default_model_profile")` | resolved value + source | field on pydantic model + file fallback (env deliberately excluded) | Yes — returns `("balanced", "default")` with and without env var set | FLOWING |
| `_env_snapshot(event)` → shell hook subprocess env | scrubbed dict | `os.environ.copy()` + CLAWTEAM_*/OH_* event fields, then `scrub_env` | Yes — end-to-end integration test proves parent `MY_API_KEY`/`GITHUB_TOKEN`/`DB_PASSWORD` values do NOT appear in the spawned subprocess env dump while identity keys DO | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full phase-0 test set passes | `.venv-sys/bin/python -m pytest tests/test_env_scrub.py tests/test_doctor.py tests/test_config.py::TestDefaultModelProfile tests/test_template_regression_matrix.py -q` | `56 passed in 2.27s` | PASS |
| Full suite passes (no BC regression) | `.venv-sys/bin/python -m pytest tests/ -q --tb=no -x` | `612 passed, 2 warnings in 105.72s` | PASS |
| Live `clawteam doctor` prints the literal `clawteam[browser]` | `.venv-sys/bin/clawteam doctor` | Output line: `pip install 'clawteam[browser]' && playwright install chromium` — brackets rendered literally | PASS |
| Live `clawteam --json doctor` emits unescaped install_hint | `.venv-sys/bin/clawteam --json doctor` | chromium install_hint equals exact pre-escape string `pip install 'clawteam[browser]' && playwright install chromium` | PASS |
| Upstream PR / discussion exists for RFC 001 | `gh pr list --repo HKUDS/ClawTeam --search "RFC 001 phase-registry"` | No results | SKIP (routes to human verification — SC#4 second clause) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CORE-03 | 00-04 | Existing 6 templates continue to spawn/advance/pass tests with no template code changes | SATISFIED | `test_template_regression_matrix.py` 12 parametrized cases pass; full suite 612 passed with no template-authored code changes (plan 04 fixed a pre-existing TOML bug in `harness-default.toml` which is deliberately called out in its SUMMARY as a Rule-1 auto-fix) |
| TEAM-06 | 00-03 + 00-04 | Template is additive; `gstack.toml` is opt-in; no existing template changes | SATISFIED | `default_model_profile` scaffold is purely additive (legacy config.json files load unchanged with balanced default); regression matrix confirms no existing template broken |
| QUALITY-14 | 00-04 | Backwards-compatibility regression matrix exists in CI | SATISFIED | New `tests/test_template_regression_matrix.py` auto-discovered by CI's existing `pytest tests/` invocation; 12 cases over 6 templates |
| QUALITY-15 | 00-01 | Env deny-filter prevents secret-shaped values in logs/board/memory | SATISFIED | `scrub_env` helper + wiring at `events/hooks.py:96`; 34 tests including end-to-end shell-hook integration proving parent API_KEY/TOKEN/PASSWORD do not reach child subprocess env. Helper is reusable for Phase 6 /learn memory per SUMMARY note. |
| UX-08 | 00-02 + 00-06 | `clawteam doctor` detects missing tools + per-OS install hints | SATISFIED | Top-level `doctor` subcommand with `_DOCTOR_TOOLS` tuple, per-OS `_doctor_install_hint` dispatch, rich+json dual output, Rich-markup-safe rendering; live run on host confirms correct behavior including the `[browser]` extra literal |

No orphaned requirements: all 5 Phase-0 requirement IDs from ROADMAP are claimed by at least one plan's frontmatter `requirements:` field.

### Anti-Patterns Found

Scanned all phase-modified files (`clawteam/secrets.py`, `clawteam/events/hooks.py`, `clawteam/config.py`, `clawteam/cli/commands.py`, `tests/test_env_scrub.py`, `tests/test_doctor.py`, `tests/test_config.py`, `tests/test_template_regression_matrix.py`, `docs/rfcs/*.md`, `clawteam/templates/harness-default.toml`) for TODO/FIXME/placeholder/empty-implementation/hardcoded-empty/console-log-only patterns.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| (none) | — | — | — | — |

No blocker anti-patterns found. The `= ""` defaults in `clawteam/config.py` (data_dir, user, default_team, etc.) are pre-existing pydantic BaseModel defaults that are overwritten by `load_config()` or `get_effective()` fetch paths, not stubs that flow to user output. The `return []`/`return {}` patterns in the RFC document are specification of intended API defaults, not code stubs.

### Human Verification Required

**1. Upstream RFC Submission (SC#4 second clause)**

- **Test:** Open `docs/rfcs/001-phase-registry.md` (and ideally a link to `docs/rfcs/README.md`) as a pull request or GitHub discussion against `HKUDS/ClawTeam`, tag at least one repository maintainer, and record the PR/discussion URL plus the maintainer acknowledgement timestamp in ROADMAP.md's Phase 0 section.
- **Expected:** A live PR or discussion thread on `HKUDS/ClawTeam` referencing RFC 001 with at least one maintainer-authored comment acknowledging the proposal (even a "received, will review" counts per ROADMAP wording).
- **Why human:** GitHub PR creation against an external organization requires authenticated human action with appropriate permissions, and a maintainer reply is asynchronous — neither step can be performed or polled by the verifier. The document artifact is fully ready (846 lines, all three hooks specified, worked software-dev example present, mirror note in the file confirms it remains authoritative in the fork regardless of upstream merge timing).

### Gaps Summary

All gap-closure work from Wave 3 landed successfully:

- **Plan 00-06** (doctor Rich-markup fix) closed UAT Test 2: `clawteam doctor` now renders `clawteam[browser]` literally in the human output while preserving the unescaped hint in the JSON output. Two regression tests (`test_doctor_human_output_preserves_browser_extra`, `test_doctor_json_install_hint_preserves_browser_extra_unescaped`) lock the fix.

- **Plan 00-07** (RFC hook expansion) closed UAT Test 6: RFC 001 now documents all three `HarnessPlugin` hooks (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`) with signatures, empty-collection defaults, additive-only contracts, and plugin-use examples. §4.7 compatibility guarantees enumerate 8 items explicitly covering each hook. §4.8 worked example shows software-dev.toml unchanged with all three hooks returning empty collections. `docs/rfcs/README.md` index row syncs the title.

The only outstanding Phase-0 item is the upstream submission step for SC#4's second clause — a human-gated action that does not block internal verification but does block Phase-0 full closure per the roadmap's acceptance wording. The `status: human_needed` reflects this: all automated verification passes, and the phase can advance only after the human owner opens the upstream PR and records the maintainer ack.

---

_Verified: 2026-04-16T19:05:00Z_
_Verifier: Claude (gsd-verifier)_
