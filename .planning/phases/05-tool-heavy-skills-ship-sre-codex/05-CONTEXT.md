---
phase: 5
phase_name: Tool-Heavy Skills (Ship, SRE, Codex)
phase_slug: tool-heavy-skills-ship-sre-codex
gathered: 2026-04-21
status: Ready for planning
source: /gsd-discuss-phase --auto (autonomous)
---

# Phase 5: Tool-Heavy Skills (Ship, SRE, Codex) — Context

<domain>
## Phase Boundary

Port the seven tool-heavy gstack skills that give engineer/shipper/sre/reviewer external-tool surfaces. Each skill is a real ClawTeam skill module (not prompt baking), bound to specific roles in `gstack.toml`, invocable via MCP tool call.

Deliverables:
1. **`/codex`** (engineer, reviewer) — shells out to OpenAI Codex CLI via `NativeCliAdapter` (at `clawteam/spawn/adapters.py`) for three modes: `review` (pass/fail gate), `adversarial` (red-team critique), `consultation` (open-ended). Writes `codex-review.md` artifact tagged with mode. On missing `codex` binary → emits `SkillUnavailable` with install hint `npm install -g @openai/codex`.
2. **`/ship`** (shipper) — Build-phase-complete sprint action: sync main → run tests (bootstrapping if missing) → audit coverage (threshold from `gstack.toml [ship]`) → push branch → open PR via `gh` CLI → writes `ship-notes.md` with PR URL. Auto-invokes `/document-release`.
3. **`/land-and-deploy`** (shipper) — merged-PR action: wait CI green → deploy via `gstack.toml [deploy]` target (or stub if `/setup-deploy` unrun) → verify production health → emits `deploy.md` with deploy URL. Ship-phase `EvidenceGate` validates deploy_url dereferences (HEAD 2xx/3xx) before Reflect.
4. **`/document-release`** (shipper) — diff-vs-docs cross-reference: walks `docs/`, `*.md` at root, detects stale references (removed exports, renamed files, changed signatures). Emits patch proposals; human-gated writes via `InteractionGate` for non-trivial changes.
5. **`/canary`** (sre) — post-deploy monitor: configurable window (default 5 min); polls deploy URL for HTTP errors, scrapes browser console for JS errors (via `clawteam[browser]` Playwright if installed, else HTTP-only), compares to pre-deploy baseline. Emits `canary-report.md` with regression flags.
6. **`/benchmark`** (sre) — Core Web Vitals + page-load baselines: before/after on every PR. Writes `benchmark-report.md` with threshold from `gstack.toml [benchmark]`. Regression threshold triggers reviewer attention (Phase 4 integration).
7. **`/setup-deploy`** (sre) — one-time wizard: interactive prompts via `questionary` (existing dep) → writes `[deploy]` block into `gstack.toml`. Idempotent on re-run (edits existing block). Supports vercel, netlify, fly.io, and `custom` (shell command) targets.

**Scope boundary (explicit exclusions):**
- Skill *discovery* by agents (already exists via `contribute_skills` hook from Phase 1). Phase 5 ships skill *implementations* at `clawteam/templates/gstack/skills/<skill>/`.
- Browser pipeline (Playwright install + `/browse`, `/design-shotgun`, `/design-html`) → Phase 6. `/canary` uses browser *if* available; degrades gracefully to HTTP-only otherwise.
- Cost dashboard consumption of canary/benchmark regression events → Phase 7.
- True CI wait-loop polling via cloud-specific hooks (Vercel/Netlify webhook) → v1.1. Phase 5 uses `gh pr checks --watch` which is sufficient.

**Delete invariant (extends Phase 3 + 4):** Removing `clawteam/templates/gstack/skills/{codex,ship,land_and_deploy,document_release,canary,benchmark,setup_deploy}/` + all `clawteam/templates/gstack/skills/__init__.py` skill-registration entries must leave the rest of the codebase running unchanged. Generic substrate additions (if any) live under `clawteam/skills/` and are opt-in via plugin contribution.

</domain>

<decisions>
## Implementation Decisions

### Skill framework & packaging (Area 1)

- **D-01:** **Each skill ships as its own sub-package** at `clawteam/templates/gstack/skills/<skill_name>/` with `__init__.py` (public API), `handler.py` (the skill implementation), optional `state.py` (if stateful — e.g., `/canary` per-window state), optional `prompts.md` (if the skill needs an LLM sub-invocation). Mirrors Phase 4's state-machine layout (skills/office_hours, skills/design_consultation, skills/investigate).
  **Why:** Consistent shape across Phase 4 + Phase 5 skills. `delete invariant` holds: rm the sub-dir + remove registration line, rest runs.

- **D-02:** **Skills register via existing `contribute_skills` hook** on `GstackSprintPlugin`. No new plugin hook. The plugin's `contribute_skills()` returns a list of `SkillRegistration(name="/codex", role="engineer|reviewer", handler=codex_handler)` per tool. Role binding is enforced at dispatch — an agent whose role is not in the registration's `role` list gets `SkillNotPermitted` error.
  **Why:** Phase 1/3 already wired `contribute_skills` + role-gating. Reusing honors the "additive hooks" convention.

### External-tool invocation (Area 2)

- **D-03:** **All external CLI tool calls go through `NativeCliAdapter` at `clawteam/spawn/adapters.py`** (existing, from Phase 0). Never `subprocess.run` directly in a skill handler. Uniform logging + failure mode + env injection.
  **Why:** Phase 0 D-02 scrub_env filter prevents leakage. Bypassing the adapter bypasses env scrubbing — a SAFETY issue. Adapter already handles timeout, stderr capture, exit-code normalization.

- **D-04:** **Missing-tool detection: each skill has a `tool_available() -> bool` helper** at the skill module level. On dispatch, if false, the handler returns a `SkillUnavailable` exception with a per-platform install hint (`clawteam doctor` content as the source of truth). The handler never partially executes. The missing-tool error INCLUDES the role + skill + binary name + install hint string.
  **Why:** UX-08 + Phase 0 D-04 doctor convention. Agents get a structured error they can pipe to user; tests assert the error shape deterministically.

### Ship pipeline (Area 3)

- **D-05:** **`/ship` is a 5-step orchestration, not a state machine.** Steps run sequentially (sync_main → run_tests → audit_coverage → push → open_pr). Each step is a pure function returning `StepResult(success: bool, details: dict)`. On any failure, `/ship` halts and emits `ship-notes.md` with `ship_status: failed`; human decides whether to retry (restart the skill). NOT a persisted-state multi-turn state machine because ship is linear and fast (≤3 min typical).
  **Why:** Ship is a transaction, not a dialog. Persisted state would add complexity without benefit — if the 5-step orchestration fails partway, the user fixes the blocker (failing test, coverage gap) and re-runs, not "resumes from step 3".

- **D-06:** **Test framework bootstrap** (`/ship` step 2, only if no test files detected): auto-detect project language (Python → pytest; JS/TS → vitest or jest per package.json signal; Go → built-in; Rust → built-in). Write ONE smoke test (`tests/test_smoke.py` or `tests/smoke.test.ts`) that imports the project entry point and asserts it loads. Writes it INSIDE the sprint's workspace_branch, not in main. Emits a question artifact asking user to flesh out the test before Ship can succeed.
  **Why:** Clear action > silent skip. "No tests found" is a common real-world state for greenfield projects; bootstrapping a tests dir + one smoke test + asking for more is a useful nudge, not overreach.

- **D-07:** **Coverage audit threshold reads from `gstack.toml [ship] coverage_threshold` (default 0.5 / 50%)** and uses `pytest-cov` / `c8` / `go test -cover` per language. Below threshold → fail ship step, write threshold details into `ship-notes.md` for reviewer. Above threshold → proceed. This is a configurable soft-gate; the `[ship]` block is additive to `TemplateDef`.
  **Why:** Different projects have different bars. Gate strength configurable; default permissive so a greenfield project isn't blocked at coverage 0.

### Deploy & monitoring (Area 4)

- **D-08:** **`gstack.toml [deploy]` block schema:** `provider = "vercel|netlify|fly|custom"`, `project = "<project-slug>"`, `custom_deploy_cmd = "<cmd>"` (only for `custom`). Validated by pydantic `DeployConfig` model at template-load time. Absent block → `/ship` succeeds, `/land-and-deploy` emits `deploy.md` with `deploy_url: pending` + prompts user to run `/setup-deploy`.
  **Why:** Explicit provider enumeration > free-text shell; pydantic rejects typos early; graceful fallback for projects that don't auto-deploy.

- **D-09:** **`/canary` window default 5 minutes, configurable via `gstack.toml [canary] window_seconds`** (default 300). Polls deploy URL every 15s. Monitors: HTTP status (2xx count / 5xx count), response time, (optional) browser console errors if `clawteam[browser]` installed. Regression flag: 5xx rate > 1% OR response time > 2× pre-deploy baseline OR any JS console error.
  **Why:** 5 min catches most deploy-time regressions without blocking the team for hours. Thresholds are tuned for typical web apps; teams with stricter SLOs can tighten via config.

- **D-10:** **`/benchmark` uses Lighthouse CI** if installed (`lighthouse-ci` npm binary). Degrades to `curl -w` timing if Lighthouse missing. Writes Core Web Vitals (LCP, FID, CLS) + Time-to-First-Byte + DOMContentLoaded to `benchmark-report.md`. Threshold for regression alarm: any Vital > 1.5× pre-deploy baseline.
  **Why:** Lighthouse is industry-standard Web Vitals tool, zero-setup if team already uses it; HTTP-only fallback keeps the skill functional on bare servers.

### Cross-skill coordination (Area 5)

- **D-11:** **`/ship` auto-invokes `/document-release`** at the end of a successful ship run (after PR opens, before returning). `/document-release` is idempotent + non-destructive: emits patch proposals to `docs-updates/<timestamp>.diff`, never writes to docs directly without human approval via `InteractionGate`.
  **Why:** Cross-skill chaining is an explicit product value ("ship always updates docs") but writes remain human-gated per Phase 4 D-13 always-human-gate precedent.

- **D-12:** **`/land-and-deploy` must be preceded by `/ship` having succeeded on the same sprint.** Enforced by checking for `ship-notes.md` artifact with `ship_status: succeeded`. Missing → `SkillPreconditionError` with hint "Run `/ship` first".
  **Why:** Out-of-order invocation is a common user mistake; structured error > cryptic failure mid-deploy.

### Cost & observability (Area 6 — Phase 7 hand-off)

- **D-13:** **`/codex` token usage tracked via existing observability hooks** (emits `tool_call_completed` event with tokens/cost). Phase 7's cost dashboard consumes these events. Phase 5 just emits; no dashboard work.
  **Why:** Separation of concerns; Phase 5 ships skill implementations, Phase 7 ships the dashboard that reads them.

- **D-14:** **Canary + benchmark regressions emit `deploy_regression_detected` + `web_vital_regression_detected` events** on the EventBus (reuses Phase 2 machinery). Phase 4's SmartReviewRouter will eventually subscribe (Phase 4 shipped router + wiring; subscribers are plugin-local additions). For Phase 5, events are emitted and optionally logged; no downstream consumer required.
  **Why:** Structured events > free-text alerts. Future phases consume without Phase 5 churn.

### Verification stringency (Area 7)

- **D-15:** **Each skill has 3 tests MINIMUM:** `test_<skill>_happy_path`, `test_<skill>_missing_tool`, `test_<skill>_adversarial_input`. Adversarial examples:
  - `/codex`: pass input `; rm -rf /` — adapter must escape, codex CLI never sees the shell metachar.
  - `/ship`: diff with 50 files all binary — must still compute coverage (skip uncoverable).
  - `/canary`: deploy URL returns 503 immediately — regression flag fires, not a crash.
  - `/benchmark`: Lighthouse returns partial (one missing metric) — surface what's available, note gap.
  - `/setup-deploy`: user input `--vercel; rm /` in project name — sanitize (alnum+dash only).
  **Why:** SAFETY + correctness by construction. Phase 0 D-01 secret-scrubbing applied at adapter layer; skill-layer adversarial tests verify the *skill contract* (not just the adapter).

- **D-16:** **Integration test: end-to-end sprint with `/ship` + `/document-release` + `/land-and-deploy` + `/canary`** using a `tmp_path` git repo, fake CI (monkeypatched `gh pr checks`), fake deploy (custom_deploy_cmd = `echo "https://example.invalid"`). Asserts artifact chain: `ship-notes.md` → `deploy.md` → `canary-report.md` with `deploy_url` propagation + `ship_status` / `deploy_status` / `canary_status` all `succeeded` or coherent-failure variants.
  **Why:** Individual skill tests + 1 end-to-end integration = confidence that the skill chain composes correctly without per-skill regression coupling.

### Claude's Discretion (planner picks; no need to ask user)

- Exact pydantic field names inside `SkillRegistration`, `DeployConfig`, `CanaryConfig`, `BenchmarkConfig`.
- Internal splits of per-skill modules (single `handler.py` vs split `sync.py` / `push.py` / `pr.py`). Planner picks per skill's complexity.
- Wave structure + parallelism of plans — planner determines from file dependencies (skill implementations are largely independent; share only the `skills/__init__.py` registry file).
- Exact `questionary` prompt text for `/setup-deploy` — planner picks; idempotent-retry message copy is planner's call.
- Whether `/document-release` ships as one plan or splits doc-walker from patch-emitter.
- Whether `/canary` + `/benchmark` share a common "HTTP polling + report writer" substrate module.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 5 deliverable specifications (load-bearing)

- `.planning/ROADMAP.md` §"Phase 5: Tool-Heavy Skills (Ship, SRE, Codex)" (lines 229-256) — phase goal, 7 success criteria, requirements SKILL-13..19.
- `.planning/REQUIREMENTS.md` SKILL-13..19 verbatim (lines 86-92).

### Project-locked context

- `.planning/PROJECT.md` §"Key Decisions" — Python 3.10+, no new required runtime deps (optional codex/lighthouse/gh CLI detected at runtime), persistence under `get_data_dir()`.

### Phase 0/1/2/3/4 substrate (what Phase 5 plugs into)

- `clawteam/spawn/adapters.py::NativeCliAdapter` — ALL external CLI calls go through this. Phase 0 D-02 scrub_env prevents secret leakage.
- `clawteam/events/hooks.py` — `clawteam doctor` detection of codex/lighthouse/gh binaries; install-hint content is source-of-truth for Phase 5 missing-tool errors.
- `clawteam/plugins/gstack_sprint_plugin.py` — Phase 4 single cohesive plugin; Phase 5 extends with `contribute_skills()` returning 7 `SkillRegistration` tuples.
- `clawteam/plugins/base.py` — `HarnessPlugin.contribute_skills()` hook (declared in Phase 1).
- `clawteam/harness/interaction_gate.py` — `/document-release` non-trivial writes gated via this.
- `clawteam/harness/evidence_gate.py` — Ship-phase EvidenceGate already validates artifact structure; Phase 5 emits `ship-notes.md`, `deploy.md`, `canary-report.md`, `benchmark-report.md` conforming to existing schemas (+ new `DeployNotes`, `CanaryReport`, `BenchmarkReport` pydantic schemas this phase adds).
- `clawteam/harness/evidence_schemas.py` + `clawteam/templates/gstack/schemas/` — add 3 new pydantic schemas for Phase 5 artifacts (DeployNotes, CanaryReport, BenchmarkReport).
- `clawteam/templates/gstack/skills/` — Phase 4's state machines live here; Phase 5's tool skills go alongside.
- `clawteam/cli/commands.py` — Phase 4's `sprint approve`; Phase 5 adds no new top-level subcommands (skills are agent-invoked, not human-invoked at the CLI).

### Research foundation

- `.planning/research/ARCHITECTURE.md` §Pattern 7 (SkillRegistry + per-role binding).
- `.planning/research/PITFALLS.md` Pitfall 8 (gate gaming — `/ship` must emit a REAL deploy URL EvidenceGate can dereference).
- `.planning/research/STACK.md` — standard stack: pydantic v2 for schemas, questionary for `/setup-deploy`, NO new required deps (codex/lighthouse/gh detected optionally).
- `.planning/research/FEATURES.md` P1 list for each of the 7 skills.

### Phase 4 precedent (close analog)

- `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md` D-01..D-02 (per-skill sub-package shape), D-15..D-16 (explicit path validation, safety).
- `clawteam/templates/gstack/skills/office_hours/state.py` — canonical skill-sub-package layout.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `clawteam/spawn/adapters.py::NativeCliAdapter` — external CLI invocation with env-scrubbing. ALL 7 skills use.
- `clawteam/events/hooks.py::scrub_env` — applied at adapter layer.
- `clawteam/templates/gstack/skills/` — 3 existing Phase 4 skills (office_hours, design_consultation, investigate) provide canonical shape.
- `clawteam/harness/evidence_gate.py` + `evidence_schemas.py` — schema registration pattern; Phase 5 adds 3 new schemas (DeployNotes, CanaryReport, BenchmarkReport).
- `clawteam/harness/interaction_gate.py` — human-gating for `/document-release` non-trivial writes.
- `clawteam/plugins/gstack_sprint_plugin.py` — extend with `contribute_skills()` returning 7 SkillRegistration tuples.
- `questionary` (already in stack) — `/setup-deploy` interactive wizard.
- `clawteam/cli/commands.py` — Typer app conventions.

### Established Patterns

- **Skill sub-package per skill** — Phase 4 precedent. Each skill is `clawteam/templates/gstack/skills/<name>/{__init__,handler[,state,prompts]}.py`.
- **NativeCliAdapter for all external CLI** — never direct subprocess.
- **Missing-tool detection at module level** — each skill's `tool_available()` helper; error includes install hint.
- **Artifact-typed pydantic schemas** — Phase 2 `EvidenceSchemaRegistry`; add 3 new schemas.
- **Events on EventBus** — Phase 2 machinery; Phase 5 emits 2 new event types (deploy_regression_detected, web_vital_regression_detected).
- **Role binding via plugin** — `SkillRegistration(name, role, handler)`.
- **File_locked + atomic_write_text** — all artifact writes.
- **Configurable via `gstack.toml` sub-blocks** — `[ship]`, `[deploy]`, `[canary]`, `[benchmark]` all additive pydantic models.

### Integration Points

- `GstackSprintPlugin.contribute_skills()` returns 7 SkillRegistration.
- `GstackSprintPlugin.contribute_evidence_schemas()` extends with 3 new pydantic schemas.
- `NativeCliAdapter.invoke(binary, args, env_allowlist=None)` — all 7 skills call.
- EventBus `emit("deploy_regression_detected", payload)` + `emit("web_vital_regression_detected", payload)` from `/canary` + `/benchmark`.

</code_context>

<specifics>
## Specific Ideas

- **`ship-notes.md` frontmatter schema extension:**
  ```yaml
  artifact_type: ship_notes
  ship_status: succeeded | failed | partial
  pr_url: <https-url>
  branch: <branch-name>
  coverage: <float 0.0-1.0>
  coverage_threshold: <float>
  steps_completed: [sync, test, coverage, push, pr]
  failure_step: <optional>
  failure_reason: <optional>
  ```

- **`deploy.md` schema:**
  ```yaml
  artifact_type: deploy_notes
  deploy_status: succeeded | failed | pending
  deploy_url: <https-url or "pending">
  provider: vercel | netlify | fly | custom
  deployed_at: <ISO-8601>
  commit_sha: <40-char>
  ```

- **`canary-report.md` schema:**
  ```yaml
  artifact_type: canary_report
  canary_status: clean | regression
  window_seconds: <int>
  http_2xx_count: <int>
  http_5xx_count: <int>
  avg_response_ms: <float>
  pre_deploy_avg_response_ms: <float>
  js_console_errors: [<str>]
  regression_flags: [<str>]
  ```

- **`benchmark-report.md` schema:**
  ```yaml
  artifact_type: benchmark_report
  benchmark_status: clean | regression
  lcp_ms: <float>
  fid_ms: <float>
  cls_score: <float>
  ttfb_ms: <float>
  dom_loaded_ms: <float>
  regression_flags: [<str>]
  ```

- **`/setup-deploy` wizard flow:**
  1. "Which deploy provider?" → vercel | netlify | fly | custom
  2. "Project slug / app name?" → alnum+dash validation
  3. (if custom) "Custom deploy command?" → sanitize shell metachars
  4. Write `[deploy]` block to `gstack.toml` atomic-update (preserve other blocks)
  5. Prompt: "Run test deploy now to verify? [y/N]"

- **Adversarial-input test matrix (per D-15):** cover shell-injection, resource exhaustion (huge diff), partial-tool-output parsing, missing binary. Encoded as parametrize pytest fixtures.

</specifics>

<deferred>
## Deferred Ideas

### To Phase 6 (browser pipeline + design-shotgun + /learn)
- `clawteam[browser]` Playwright optional extra → Phase 6. `/canary` *uses* browser if available (degrades gracefully if not).
- `/browse`, `/open-gstack-browser`, `/setup-browser-cookies`, `/design-shotgun`, `/design-html` → Phase 6.
- Real `TeamMemoryStore` + `/learn` → Phase 6 (Phase 5 skill events are logged but not persisted to memory store).

### To Phase 7 (parallel sprints + cost dashboard)
- Cost dashboard consumption of `tool_call_completed`, `deploy_regression_detected`, `web_vital_regression_detected` events — Phase 7.
- Multi-sprint orchestration of `/ship` (e.g., "10 PRs parallel, each with its own canary") — Phase 7 concurrency caps.

### To v1.1
- Provider-specific deploy hooks (Vercel webhook, Netlify build hook) replacing `gh pr checks --watch` polling — v1.1. Phase 5 polling is sufficient.
- `/codex` additional modes (e.g., `synthesis` — combine multiple codex opinions) — v1.x.
- Custom Web Vitals thresholds per page (e.g., dashboard vs marketing) — v1.x.

### Reviewed Todos (not folded)
None — `.planning/todos/pending/` is empty.

</deferred>

<plan_prep_verifications>
## Plan-Prep Verification Tasks (must run BEFORE main planning)

| ID | Verification | Action if fails |
|----|--------------|-----------------|
| A1 | `clawteam/spawn/adapters.py::NativeCliAdapter.invoke` accepts (binary, args, env_allowlist, timeout) kwargs | If signature drifted, planner adds missing kwarg via 1-line additive change. |
| A2 | `clawteam doctor` detection functions exist for: codex, lighthouse, gh, vercel-cli, netlify-cli, flyctl | If missing, planner adds detection entries to doctor in a Wave-0 plan. |
| A3 | `clawteam/plugins/gstack_sprint_plugin.py::contribute_skills` hook exists (returns list) | Phase 3 D-07: should exist; re-confirm. If missing, planner adds via additive change. |
| A4 | `clawteam/harness/evidence_schemas.py::register_schema` accepts a pydantic model with `artifact_type: Literal[...]` discriminator | Phase 2 D-01..D-05: should exist; re-confirm. Phase 5 adds 3 new schemas via this API. |
| A5 | `gstack.toml` TOML parser tolerates unknown `[ship]`, `[deploy]`, `[canary]`, `[benchmark]` sub-blocks (pydantic `extra="ignore"` on `TemplateDef`) | Phase 3 D-04: confirmed; re-verify after Phase 4 additions. |
| A6 | `questionary` is in the stack | `.planning/research/STACK.md` confirms; verify via `python -c "import questionary"`. |
| A7 | `clawteam/events/bus.py::emit` accepts arbitrary string event names | Phase 4 Plan 02 already verified; re-confirm. |
| A8 | `gh` CLI availability detection already in `clawteam doctor` | Likely from Phase 0; re-verify. |

</plan_prep_verifications>

---

*Phase: 05-tool-heavy-skills-ship-sre-codex*
*Context gathered: 2026-04-21 via /gsd-discuss-phase --auto (autonomous run)*
*Decisions: D-01 through D-16 (16 locked); plus 8 plan-prep verification tasks*
*Next: /gsd-plan-phase 5*
