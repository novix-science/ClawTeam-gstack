---
phase: 5
slug: tool-heavy-skills-ship-sre-codex
status: verified
threats_open: 0
threats_total: 40
threats_closed: 40
asvs_level: 1
created: 2026-04-22
audited: 2026-04-22
---

# Phase 5 — Security

> Per-phase security contract covering the 10 plans in Phase 5 (Tool-Heavy
> Skills — Ship / SRE / Codex). Verifies the threat register declared in each
> plan's `<threat_model>` block against the landed implementation.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| agent → SkillDispatcher | untrusted: caller may supply any `skill_name`/`role`/`args` combo | (skill_name, role, args dict) |
| handler → subprocess | untrusted: argv + env flow to external CLIs (codex, gh, git, vercel, netlify, fly, curl, lighthouse, playwright) | argv list + env dict |
| template file (`gstack.toml`) → pydantic `TemplateDef` | untrusted: user-authored TOML | provider / coverage_threshold / custom_deploy_cmd / canary window etc. |
| skill handler → artifact file | untrusted intermediate — pydantic `ArtifactFrontmatterBase` is the gate | artifact frontmatter + body |
| external canary/benchmark poll result → regression event | untrusted network: deploy URL response, lighthouse JSON | status code, latency, LH score |
| agent prompt → codex subprocess argv | untrusted: agent may include arbitrary strings | prompt string |
| codex stdout → `CodexReview` summary field | untrusted: LLM-generated text | review summary |
| user terminal input → `gstack.toml` content | untrusted: user may type shell metachars | project slug, provider, custom_deploy_cmd |
| `gstack.toml` → `/land-and-deploy` argv | untrusted: `custom_deploy_cmd` reaches subprocess | argv list after `shlex.split` |
| `custom_deploy_cmd` → subprocess argv | untrusted (indirect, through TOML) | argv list |
| `gh` stdout (pr_url) → `gh pr checks` argv | untrusted: URL parsing | pr_url string |
| provider stdout → `deploy_url` extraction | untrusted: arbitrary text may contain URL-like strings | deploy_url string |
| user branch name → git / gh argv | untrusted: branch name may contain shell metachars | branch name |
| PR title/body → gh argv | untrusted | title + body strings |
| `coverage.json` → float parse | untrusted: file may be malformed | coverage floats |
| doc content → `extract_code_refs` regex | untrusted: adversarial docs may aim for regex catastrophic backtracking | markdown text |
| `git diff` stdout → `removed_paths` parsing | in-process trusted | diff text |
| `deploy.md` `deploy_url` → HTTP GET target | untrusted (user-controlled TOML indirectly) | URL |
| Baseline JSON → numeric comparison | untrusted: user filesystem | floats |
| `lighthouse` stdout → `json.loads` | untrusted: CLI output may be malformed | JSON text |
| test harness → user filesystem | untrusted: tests must NEVER write to real `~/.clawteam` or real git repo | tmp_path only |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-05-01-01 | Spoofing | `SkillDispatcher` role check | mitigate | `reg.roles` membership check → raises `SkillNotPermitted` | `clawteam/plugins/skill_dispatcher.py:62-68` | closed |
| T-05-01-02 | Tampering | `invoke_native_cli` argv | mitigate | `shell=False` hard-coded; `NativeCliAdapter.prepare_command` returns `list[str]` | `clawteam/spawn/invoke.py:88` | closed |
| T-05-01-03 | Information Disclosure | Env vars leaking to subprocess | mitigate | `env is None → scrub_env(os.environ)` default | `clawteam/spawn/invoke.py:79` | closed |
| T-05-01-04 | Information Disclosure | `DeployConfig` secrets in TOML | accept | `gstack.toml` is user-scoped; `DeployConfig` has no token fields; provider auth flows natively (`vercel login`, `gh auth login`). | accepted risk AR-05-01 | closed |
| T-05-01-05 | DoS | Dispatcher handler runaway | accept | Phase 5 skills set explicit `invoke_native_cli` timeouts; dispatcher is synchronous — runaway is per-skill concern. | accepted risk AR-05-02 | closed |
| T-05-01-06 | Tampering | Duplicate-name plugin skill injection | mitigate | `PluginManager.get_plugin_skills()` raises `ValueError` on duplicate name | `clawteam/plugins/manager.py:285-287` | closed |
| T-05-01-07 | Tampering | Pydantic `TemplateDef` accepts invalid provider | mitigate | `Literal["vercel","netlify","fly","custom"]` on `DeployConfig.provider` | `clawteam/templates/__init__.py:121` | closed |
| T-05-02-01 | Tampering | Malformed artifact bypasses `EvidenceGate` | mitigate | `Literal[...]` `artifact_type` discriminators + `Field(min_length=...)` / `ge=...` constraints on all 10 schemas | `clawteam/templates/gstack/schemas/*.py` (deploy_notes, ship_notes, design_doc, plan_doc, test_report, review_report, retro, canary_report, benchmark_report, codex_review) | closed |
| T-05-02-02 | Tampering | Duplicate schema key overwrites Phase 3 schema | mitigate | `register_schema` raises `ValueError` on duplicate name | `clawteam/harness/evidence_schemas.py:78-82` | closed |
| T-05-02-03 | Information Disclosure | Deploy URL or `commit_sha` carries secret | accept | `deploy_url` is public (HEAD probe by `EvidenceGate`); `commit_sha` is public git data. | accepted risk AR-05-03 | closed |
| T-05-02-04 | Tampering | Fake regression event injected into bus | accept | `EventBus.emit()` is in-process; no network surface. Only in-process callers (handlers) emit. | accepted risk AR-05-04 | closed |
| T-05-03-01 | Tampering | Shell metachars in codex prompt | mitigate | `invoke_native_cli` uses `shell=False`; prompt is a separate positional argv element | `clawteam/templates/gstack/skills/codex/handler.py:83` via `clawteam/spawn/invoke.py:88` | closed |
| T-05-03-02 | Information Disclosure | `FAKE_SECRET` / provider token in env reaches codex | mitigate | `invoke_native_cli` defaults to `env=scrub_env(os.environ)` | `clawteam/spawn/invoke.py:79` | closed |
| T-05-03-03 | Spoofing | Non-engineer/reviewer invokes `/codex` | mitigate | `SkillRegistration.roles=frozenset({"engineer","reviewer"})` | `clawteam/plugins/gstack_sprint_plugin.py:247` | closed |
| T-05-03-04 | Tampering | Codex stdout summary contains malicious markdown | accept | Summary stored as string; `EvidenceGate` does not execute content. Truncated to 500 chars. | accepted risk AR-05-05 | closed |
| T-05-04-01 | Tampering | `branch="feat; rm -rf /"` reaches git/gh argv | mitigate | `invoke_native_cli` `shell=False` + list argv — string is a literal argv element | `clawteam/templates/gstack/skills/ship/steps.py` (all git/gh calls) via `clawteam/spawn/invoke.py:88` | closed |
| T-05-04-02 | Tampering | Malformed `coverage.json` crashes audit | mitigate | `try/except (ValueError, OSError)` around `json.loads(cov_file.read_text())` + `.get` chain with defaults | `clawteam/templates/gstack/skills/ship/steps.py:235-237` | closed |
| T-05-04-03 | Information Disclosure | `GITHUB_TOKEN` leaks through gh stdout | accept | gh's own auth model; `scrub_env` filters `GITHUB_TOKEN` from env in `invoke_native_cli`; gh stdout is trusted to not leak its own token. | accepted risk AR-05-06 | closed |
| T-05-04-04 | DoS | `gh pr create` hangs indefinitely | mitigate | 60 s timeout on `open_pr`; `TimeoutExpired` propagates to handler which writes `ship-notes` with `failure_step=pr` | `clawteam/templates/gstack/skills/ship/steps.py:364` | closed |
| T-05-05-01 | Tampering | User types `; rm -rf /` as project slug | mitigate | `_PROJECT_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")` full-match validator | `clawteam/templates/gstack/skills/setup_deploy/wizard.py:21,40` | closed |
| T-05-05-02 | Tampering | User types shell metachar in `custom_deploy_cmd` | mitigate | `_SHELL_METACHARS` deny-list validator; downstream `invoke_native_cli(shell=False)` is belt-and-braces | `clawteam/templates/gstack/skills/setup_deploy/wizard.py:27` + downstream `clawteam/spawn/invoke.py:88` | closed |
| T-05-05-03 | Tampering | TOML write corrupts existing blocks | mitigate | `atomic_write_text` (Phase 2 primitive) + regex-based block insert/replace + post-render `tomllib.loads` round-trip assertion | `clawteam/templates/gstack/skills/setup_deploy/handler.py:147,157` | closed |
| T-05-05-04 | Spoofing | Non-sre role invokes `/setup-deploy` | mitigate | `SkillRegistration.roles=frozenset({"sre"})` | `clawteam/plugins/gstack_sprint_plugin.py:266` | closed |
| T-05-05-05 | Tampering | Malformed provider (e.g., `"aws"`) written to TOML | mitigate | `DeployConfig(**raw_cfg)` pydantic validates `Literal` BEFORE write | `clawteam/templates/gstack/skills/setup_deploy/handler.py:140` | closed |
| T-05-06-01 | Tampering | `shlex`-split `custom_deploy_cmd` with shell metachars | mitigate | `shlex.split` + `invoke_native_cli(shell=False)` — metachars become literal argv elements | `clawteam/templates/gstack/skills/land_and_deploy/handler.py:223,448` | closed |
| T-05-06-02 | Tampering | Malicious `ship-notes.md` with crafted `ship_status` | accept | `ship-notes.md` is written by `/ship` in same `sprint_dir` (same trust domain); attacker with sprint_dir write access has greater privileges already. | accepted risk AR-05-07 | closed |
| T-05-06-03 | DoS | `gh pr checks --watch` hangs forever | mitigate | `ci_wait_timeout_seconds` (default 1800) on `invoke_native_cli` call | `clawteam/templates/gstack/skills/land_and_deploy/handler.py:395-398` | closed |
| T-05-06-04 | DoS | Deploy URL 503-loops forever | mitigate | Exponential backoff with `deploy_verify_timeout_seconds` deadline | `clawteam/templates/gstack/skills/land_and_deploy/handler.py:154-200,484` | closed |
| T-05-06-05 | Information Disclosure | `VERCEL_TOKEN` / `NETLIFY_AUTH_TOKEN` in env leaks to stdout | mitigate | `scrub_env` via `invoke_native_cli`; both tokens on scrub_env's default deny pattern | `clawteam/spawn/invoke.py:79` + `clawteam/spawn/cli_env.py` (scrub_env) | closed |
| T-05-06-06 | Spoofing | Non-shipper role dispatches `/land-and-deploy` | mitigate | `SkillRegistration.roles=frozenset({"shipper"})` | `clawteam/plugins/gstack_sprint_plugin.py:274` | closed |
| T-05-07-01 | DoS | Regex catastrophic backtracking on crafted doc | mitigate | All patterns linear-time — `_INLINE_CODE_RE = r"`([^`\n]+)`"` is simple (no nested quantifiers) | `clawteam/templates/gstack/skills/document_release/doc_walker.py:28` | closed |
| T-05-07-02 | Spoofing | Non-shipper invokes `/document-release` | mitigate | `roles=frozenset({"shipper"})` | `clawteam/plugins/gstack_sprint_plugin.py:285` | closed |
| T-05-07-03 | Information Disclosure | Patch proposal contains secrets from leaked doc | accept | `docs/` is checked into git; any secrets there are a pre-existing repo hygiene issue, not this skill's concern. | accepted risk AR-05-08 | closed |
| T-05-07-04 | Tampering | `/document-release` failure fails `/ship` | mitigate | Try/except around auto-invoke in ship handler (auto-invoke chain) | `clawteam/templates/gstack/skills/document_release/handler.py:60-70` (+ ship handler auto-invoke guard) | closed |
| T-05-07-05 | DoS | Huge diff produces 1000s of patches crashing memory | mitigate | `max_patches_per_run` (default 50) cap + trailer note for `deferred` overflow | `clawteam/templates/gstack/skills/document_release/patch_emitter.py:26,54-55` | closed |
| T-05-08-01 | DoS | Polling loop wall-clock blocks handler | mitigate | `sleep_fn` injectable for tests; production sleeps bounded by `window_seconds` deadline | `clawteam/templates/gstack/skills/canary/poller.py:96,106,114` | closed |
| T-05-08-02 | DoS | Malicious `deploy_url` causes Playwright crash | mitigate | All browser errors caught + appended to `js_console_errors` as strings; handler continues | `clawteam/templates/gstack/skills/canary/handler.py:121-141` | closed |
| T-05-08-03 | Tampering | Malformed baseline.json crashes json parse | mitigate | `load_baseline` try/except → `None` on parse failure | `clawteam/templates/gstack/skills/canary/handler.py` (load_baseline) + `clawteam/templates/gstack/skills/benchmark/handler.py:105-110` | closed |
| T-05-08-04 | Spoofing | Non-SRE role dispatches `/canary` | mitigate | `roles=frozenset({"sre"})` | `clawteam/plugins/gstack_sprint_plugin.py:293` | closed |
| T-05-08-05 | Tampering | Top-level Playwright import crashes plugin on no-Playwright install | mitigate | AST-verified no top-level `playwright` import; import deferred inside handler body behind `find_spec("playwright")` gate | `clawteam/templates/gstack/skills/canary/handler.py:105-118` + `tests/templates/gstack/skills/test_canary.py::test_handler_module_level_no_playwright_import` | closed |
| T-05-09-01 | Tampering | Lighthouse stdout JSON injection | mitigate | `stdout.startswith("{")` pre-check + `try/except json.JSONDecodeError` before parse; empty dict on fail triggers curl fallback | `clawteam/templates/gstack/skills/benchmark/handler.py:188-192` | closed |
| T-05-09-02 | Information Disclosure | API tokens in env leak to lighthouse subprocess | mitigate | `invoke_native_cli` default `env=scrub_env` | `clawteam/spawn/invoke.py:79` | closed |
| T-05-09-03 | Tampering | Baseline JSON with crafted very-low values causes false-positive regressions | accept | User-owned baseline; if user writes their own baseline they accept the consequence. | accepted risk AR-05-09 | closed |
| T-05-09-04 | DoS | Lighthouse runs past timeout | mitigate | 180 s timeout on `invoke_native_cli` call | `clawteam/templates/gstack/skills/benchmark/handler.py:183` | closed |
| T-05-10-01 | Tampering | Test harness accidentally writes to real `~/.clawteam` | mitigate | All tests use `tmp_path`; `baseline_path` monkey-patched where needed | `tests/templates/gstack/skills/test_setup_deploy.py`, `tests/templates/gstack/skills/test_benchmark.py`, `tests/integration/test_phase5_sprint_end_to_end.py:63-141` | closed |
| T-05-10-02 | Tampering | Integration test mutates real git repo | mitigate | All tests use `tmp_path` workspace, not the real repo | `tests/integration/test_phase5_sprint_end_to_end.py:63-70` | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-05-01 | T-05-01-04 | `gstack.toml` is user-scoped config; `DeployConfig` deliberately has no token/key fields; provider auth happens via each provider's native auth flow (`vercel login`, `gh auth login`). User convention is to keep secrets out of TOML. | phase-author | 2026-04-22 |
| AR-05-02 | T-05-01-05 | `SkillDispatcher` is synchronous — a runaway handler is a per-skill concern, not a substrate concern. All Phase 5 skills set explicit `invoke_native_cli` timeouts (codex, ship steps, land_and_deploy, canary poller, benchmark). | phase-author | 2026-04-22 |
| AR-05-03 | T-05-02-03 | `deploy_url` is public (HEAD probed by `EvidenceGate`); `commit_sha` is public git metadata. No secret surface in either field. | phase-author | 2026-04-22 |
| AR-05-04 | T-05-02-04 | `EventBus.emit()` is in-process only; no network surface. Only in-process callers (handlers) can emit. Spoofing requires arbitrary code execution, which is a greater breach than the event-injection risk. | phase-author | 2026-04-22 |
| AR-05-05 | T-05-03-04 | Codex stdout is captured as a plain `summary` string in `CodexReview`. `EvidenceGate` does not execute content; it validates shape only. Summary truncated to 500 chars so even a pathological output cannot bloat the artifact. | phase-author | 2026-04-22 |
| AR-05-06 | T-05-04-03 | `GITHUB_TOKEN` is scrubbed from env by `scrub_env` before `invoke_native_cli` spawns `gh`. `gh` manages its own keychain auth. Any leak through gh's own stdout is a gh-upstream concern, not this skill's responsibility. | phase-author | 2026-04-22 |
| AR-05-07 | T-05-06-02 | `ship-notes.md` is written by `/ship` into the same `sprint_dir` that `/land-and-deploy` then reads. Both operate under the same user's filesystem privileges — any attacker able to forge `ship-notes.md` already has greater privileges than what fake `ship_status` can unlock. | phase-author | 2026-04-22 |
| AR-05-08 | T-05-07-03 | Documents under `docs/` are version-controlled alongside source. Any secrets accidentally checked into `docs/` are a pre-existing repo-hygiene issue that is orthogonal to `/document-release`'s patch proposal logic. | phase-author | 2026-04-22 |
| AR-05-09 | T-05-09-03 | Baseline JSON at `get_data_dir()/teams/<team>/baselines/<provider>.json` is owned and authored by the end user. If the user crafts artificially low baseline values, the false-positive regression is a self-inflicted consequence, not an attacker surface. | phase-author | 2026-04-22 |

---

## Unregistered Flags

The following `## Threat Flags` entries in Phase 5 summaries were reconciled against the threat register:

| Source Summary | Flag | Mapping |
|----------------|------|---------|
| 05-02-SUMMARY.md | pydantic `Literal[...]` discriminators + `Field(min_length=...)` / `ge=...` constraints | → T-05-02-01 (informational) |
| 05-02-SUMMARY.md | plugin duplicate-key `ValueError` non-regression | → T-05-02-02 (informational) |
| 05-05-SUMMARY.md | `validate_project_slug` regex landed | → T-05-05-01 (informational) |
| 05-05-SUMMARY.md | `validate_custom_cmd` deny-list landed + downstream `shell=False` | → T-05-05-02 (informational) |
| 05-05-SUMMARY.md | `atomic_write_text` + `tomllib.loads` round-trip | → T-05-05-03 (informational) |
| 05-05-SUMMARY.md | `SkillRegistration.roles={'sre'}` | → T-05-05-04 (informational) |
| 05-05-SUMMARY.md | `DeployConfig` pydantic validation before write | → T-05-05-05 (informational) |
| 05-09-SUMMARY.md | lighthouse stdout `startswith("{")` + JSONDecodeError guard | → T-05-09-01 (informational) |
| 05-09-SUMMARY.md | curl argv-only; `deploy_url` sprint-local + trusted | → T-05-09-02 (informational) |
| 05-09-SUMMARY.md | baseline JSON user-owned | → T-05-09-03 (informational) |
| 05-09-SUMMARY.md | Event emit wrapped in try/except | supplemental hardening for T-05-02-04 (informational) |

No flag was left unmapped.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-22 | 40 | 40 | 0 | /gsd-secure-phase (inline verification — Task-tool unavailable in background context) |

### Audit Methodology

Executed inline within the secure-phase workflow (user-directed "verify all open threats"; Task-tool based auditor spawn was unavailable in the background agent context). Each threat in the consolidated register was verified by:

- **mitigate** — `grep` confirmation of the declared mitigation pattern in cited files (see `Mitigation` column for file:line evidence).
- **accept** — entry added to the Accepted Risks Log (AR-05-01..AR-05-09).
- **transfer** — N/A this phase.

All 10 plans' threat-model blocks were parsed (`05-01-PLAN.md` through `05-10-PLAN.md`). All SUMMARY `## Threat Flags` sections (05-02, 05-05, 05-09) were reconciled into the Unregistered Flags table above.

### Coverage Breakdown

| Plan | Threats | Closed | Open | Notes |
|------|---------|--------|------|-------|
| 05-01 (Wave 0 substrate) | 7 | 7 | 0 | Dispatcher + invoke_native_cli + plugin manager + TemplateDef substrate |
| 05-02 (evidence schemas + events) | 4 | 4 | 0 | Pydantic discriminators + register_schema ValueError |
| 05-03 (/codex) | 4 | 4 | 0 | shell=False + scrub_env + role-gating |
| 05-04 (/ship) | 4 | 4 | 0 | argv-literal branches + json try/except + gh 60s timeout |
| 05-05 (/setup-deploy) | 5 | 5 | 0 | wizard regex/denylist + atomic_write_text + pydantic pre-write |
| 05-06 (/land-and-deploy) | 6 | 6 | 0 | shlex.split + CI/deploy timeouts + scrub_env + shipper role |
| 05-07 (/document-release) | 5 | 5 | 0 | linear regex + shipper role + max_patches cap + try/except auto-invoke |
| 05-08 (/canary) | 5 | 5 | 0 | sleep_fn injection + browser-error catch + baseline guard + SRE role + AST-verified deferred playwright import |
| 05-09 (/benchmark) | 4 | 4 | 0 | startswith + JSONDecodeError guard + scrub_env + 180s LH timeout |
| 05-10 (adversarial matrix / E2E) | 2 | 2 | 0 | tmp_path + monkeypatch isolation |
| **Total** | **40** | **40** | **0** | |

---

## Sign-Off

- [x] All 40 threats have a disposition (mitigate: 31 · accept: 9 · transfer: 0)
- [x] Accepted risks documented in Accepted Risks Log (AR-05-01..AR-05-09)
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-22
