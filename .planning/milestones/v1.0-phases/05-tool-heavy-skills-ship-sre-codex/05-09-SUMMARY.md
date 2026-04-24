---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 09
subsystem: skills
tags:
  - skill-benchmark
  - lighthouse
  - core-web-vitals
  - web-vital-regression
  - sre-role
requirements_completed:
  - SKILL-18
dependency_graph:
  requires:
    - 05-01  # SkillRegistration substrate + invoke_native_cli
    - 05-02  # BenchmarkReport schema + WebVitalRegressionDetected event
    - 05-06  # deploy.md writer + _read_deploy_notes pattern
  provides:
    - /benchmark skill handler + plugin registration
    - baseline JSON at baseline_path(team, provider) consumed by /canary
  affects:
    - clawteam/plugins/gstack_sprint_plugin.py (adds /benchmark SkillRegistration)
tech_stack:
  added:
    - npm lighthouse (optional — shutil.which detection + curl fallback)
  patterns:
    - hand-rolled YAML frontmatter emitter (mirrors /ship + /land-and-deploy)
    - lazy sibling-package import for Wave-4 cross-executor resilience
    - invoke_native_cli wrapper for every subprocess call
key_files:
  created:
    - clawteam/templates/gstack/skills/benchmark/__init__.py
    - clawteam/templates/gstack/skills/benchmark/handler.py
    - tests/templates/gstack/skills/test_benchmark.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py  # +/benchmark SkillRegistration
decisions:
  - "Lazy-import baseline_path + load_baseline from canary.poller inside the helpers (not at module top) so the benchmark module collects even when the canary sibling package hasn't landed yet — Wave-4 cross-executor resilience against Plan 05-08 running in parallel."
  - "Tests monkeypatch bh.baseline_path + bh.load_baseline at module scope so no on-disk baseline write ever escapes tmp_path — eliminates dependency on get_data_dir / $HOME pollution."
  - "Partial Lighthouse output (D-15 adversarial) triggers a SECONDARY curl pass to fill missing ttfb_ms + dom_loaded_ms transport metrics while keeping measured_with='lighthouse' for the vitals lighthouse did return. lcp/fid/cls stay None when lighthouse omitted them — never substituted from curl (curl can't measure them)."
  - "Regression events are emitted one-per-vital inside a try/except so a broken event bus can never fail the handler — matches ralph_loop convention."
  - "baseline JSON shape mirrors what /canary (Plan 05-08) reads: lcp_ms/fid_ms/cls_score/ttfb_ms/dom_loaded_ms (nullable) + avg_response_ms = (ttfb + dom_loaded) / 2 when either is non-zero."
  - "Short vital names emitted to the event (lcp/fid/cls/ttfb/dom_loaded) strip the _ms / _score suffixes — matches the WebVitalRegressionDetected schema's free-form `vital: str` field + Phase 7 aggregator convention documented in events/types.py."
metrics:
  duration: 25min
  completed: 2026-04-21T15:10:00Z
  tasks: 1
  files: 3
  tests_added: 12
  tests_passing: 12
---

# Phase 5 Plan 09: /benchmark Skill Summary

Lighthouse-primary / curl-fallback Core Web Vitals collector with pre-deploy
baseline persistence and regression event emission — closes SKILL-18.

## One-liner

/benchmark runs Lighthouse for LCP/FID/CLS/TTFB; when the npm binary is missing
or returns malformed JSON, degrades to curl -w timing; writes benchmark-report.md
and an optional pre-deploy baseline JSON consumed by /canary; emits
WebVitalRegressionDetected per vital whose observed > 1.5× baseline.

## What shipped

**clawteam/templates/gstack/skills/benchmark/__init__.py** (8 LOC) — re-exports
`benchmark_handler` for the plugin registration site.

**clawteam/templates/gstack/skills/benchmark/handler.py** (~330 LOC) —
full handler with:

- `_lighthouse_available` — `shutil.which("lighthouse")` probe.
- `_run_lighthouse` — 180 s-bounded `invoke_native_cli` call with
  `startswith("{")` + `try/except json.JSONDecodeError` guards before
  `json.loads` (T-05-09-01 tampering mitigation); maps
  `largest-contentful-paint / max-potential-fid / cumulative-layout-shift /
  server-response-time` audits onto `lcp_ms / fid_ms / cls_score / ttfb_ms`.
- `_run_curl` — parses `%{time_total} %{time_starttransfer}` stdout into
  `dom_loaded_ms / ttfb_ms` (seconds × 1000).
- `_collect_vitals` — lighthouse primary; curl fallback on missing binary OR
  parse failure; secondary-curl fill for partial Lighthouse output (D-15).
- `_evaluate_regressions` — per-vital ratio check against
  `regression_threshold_ratio` (default 1.5, configurable via
  `TemplateDef.benchmark.regression_threshold_ratio`). Skips vitals with
  missing or zero baselines so first-ever benchmark doesn't false-trigger.
- `_write_report` + `_render_report_yaml` — hand-rolled frontmatter emitter
  (BenchmarkReport pydantic validation before write).
- `_write_baseline` — writes JSON with full `_VITALS` key set + computed
  `avg_response_ms` consumed by /canary's regression evaluator.
- `baseline_path` + `load_baseline` — thin lazy wrappers around
  `canary.poller` for Wave-4 cross-executor resilience.

**clawteam/plugins/gstack_sprint_plugin.py** — appends
`SkillRegistration(name='/benchmark', roles=frozenset({'sre'}),
handler=_benchmark_handler, tool_available=None,
install_hint='npm install -g lighthouse ...')` to `contribute_skills()`.

**tests/templates/gstack/skills/test_benchmark.py** (~460 LOC, 12 tests) —
all 12 green on first GREEN run.

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/templates/gstack/skills/test_benchmark.py -q` | **12 passed** |
| `pytest tests/test_gstack_plugin.py tests/test_plugin_manager_skills.py tests/test_event_types_phase5.py tests/test_evidence_schemas_phase5.py tests/test_ship_skill.py tests/templates/gstack/skills/test_{codex,setup_deploy,land_and_deploy,document_release}.py -q` | **104 passed** |
| Plan verification #2: `GstackSprintPlugin().contribute_skills()` names | `['/benchmark', '/canary', '/codex', '/document-release', '/land-and-deploy', '/setup-deploy', '/ship']` — 7 skills |
| `grep "def benchmark_handler" clawteam/templates/gstack/skills/benchmark/handler.py` | match |
| `grep 'name="/benchmark"' clawteam/plugins/gstack_sprint_plugin.py` | match |
| `grep "WebVitalRegressionDetected" clawteam/templates/gstack/skills/benchmark/handler.py` | match |

All acceptance criteria met; Phase 5 Wave 4 parallel-execution target (7-skill
plugin surface) reached in concert with Plan 05-08 (/canary).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Lazy-import canary.poller helpers**

- **Found during:** Task 1 implementation (before RED tests ran).
- **Issue:** Plan specifies `from clawteam.templates.gstack.skills.canary.poller
  import baseline_path, load_baseline` at module top. Plan 05-08 (which
  lands canary.poller) runs in parallel in Wave 4, so at the moment the
  benchmark module first imports there is no guarantee canary.poller
  exists — module import would fail on ImportError.
- **Fix:** Wrapped `baseline_path` + `load_baseline` in thin module-level
  functions with a `try: from canary.poller import ... except ImportError:`
  fallback that delegates to `clawteam.team.models.get_data_dir`. Tests
  monkeypatch `bh.baseline_path` + `bh.load_baseline` directly so the
  fallback path is exercised by the test suite shape, and the real
  delegation path takes over the moment Plan 05-08 commits poller.py.
- **Files modified:** `clawteam/templates/gstack/skills/benchmark/handler.py`
  (see `baseline_path` + `load_baseline` helpers near the top).
- **Commit:** 76394e8.

### Wave-4 Cross-Executor Stash Interaction

Same pattern documented for 04-10 Task 3 + 05-03 + 05-06 recurred here.
Plan 05-08's parallel executor pre-populated the working copy of
`clawteam/plugins/gstack_sprint_plugin.py` with its own `/canary`
SkillRegistration + import during my Task 1 implementation. Resolved
symmetric to 05-06's fix:

- Before staging, extracted a 05-09-only plugin variant (keeping only
  the `/benchmark` import + registration + docstring hunk, reverting
  the `/canary` hunks that belong to Plan 05-08).
- Staged ONLY `clawteam/templates/gstack/skills/benchmark/*` + the
  trimmed `gstack_sprint_plugin.py` diff + my tests.
- After commit, Plan 05-08's executor's WIP re-applied its `/canary`
  hunks to the working tree (they are still uncommitted at my plan's
  completion — 05-08 will commit them atomically with its Task 2).

No 05-08 files committed under any feat(05-09) hash; `git blame`
on the final plugin shows:

- Lines `from clawteam.templates.gstack.skills.benchmark.handler import ...`
  + `SkillRegistration(name="/benchmark", ...)` hunk → 76394e8 (this plan).
- Lines `from clawteam.templates.gstack.skills.canary.handler import ...`
  + `SkillRegistration(name="/canary", ...)` → Plan 05-08's commit when it
  lands.

## Threat Flags

None beyond the plan's existing `<threat_model>` coverage. New surface:

- `invoke_native_cli(["lighthouse", url, ...])` — stdout JSON parse guarded
  by `startswith("{")` + `try/except json.JSONDecodeError` (T-05-09-01).
- `invoke_native_cli(["curl", "-o", "/dev/null", "-s", "-w", ...])` —
  argv-only (shell=False); `url` comes from deploy.md frontmatter which
  is sprint-local + trusted.
- baseline JSON at `get_data_dir()/teams/<team>/baselines/<provider>.json`
  is owned by the end user; Plan documents T-05-09-03 "accept" posture.
- Event emit wrapped in try/except so a malicious bus implementation
  cannot fail the handler.

## Known Stubs

None — handler is production-capable. When lighthouse is unavailable the
curl fallback writes a report with `measured_with='curl'` and the Web
Vitals fields `lcp_ms / fid_ms / cls_score` set to `null`; this is the
designed contract (D-10 + BenchmarkReport schema's Optional[float]), not
a stub.

## Self-Check

Files created:

- `clawteam/templates/gstack/skills/benchmark/__init__.py` — **FOUND**
- `clawteam/templates/gstack/skills/benchmark/handler.py` — **FOUND**
- `tests/templates/gstack/skills/test_benchmark.py` — **FOUND**

Commits:

- `c179184` (test 05-09) — **FOUND in git log**
- `76394e8` (feat 05-09) — **FOUND in git log**

## Self-Check: PASSED
