---
phase: 3
phase_name: Gstack Team Template & Methodology Port
phase_slug: gstack-team-template-methodology-port
gathered: 2026-04-20
status: Ready for planning
source: /gsd-discuss-phase
---

# Phase 3: Gstack Team Template & Methodology Port — Context

<domain>
## Phase Boundary

Ship the user-visible product surface for the gstack team template:
1. `clawteam/templates/gstack.toml` — 11-agent roster + leader binding + 7-phase declaration + memory layout, additive over the existing `TemplateDef` schema (existing 6 templates unaffected).
2. `clawteam/plugins/gstack_sprint_plugin.py` — single cohesive plugin (~250 LOC, mirrors `ralph_loop_plugin.py`) that registers 7 phases via `PhaseRegistry`, six pydantic evidence schemas via `contribute_evidence_schemas`, and binds ceo as the only role authorized to call `SprintConductor.advance_phase`.
3. `clawteam/templates/gstack/prompts/<role>.md` × 11 — per-role methodology prompts ported from the **pure-rubric subset** of upstream gstack skills, each with a grep-verifiable `SIGNATURE:` line.
4. `clawteam/templates/gstack/envelope_personas.py` — 11 pydantic subclasses of `TurnEnvelope` enforcing per-persona role-reassertion fields.
5. Reflect-phase event handler emitting a `_phase6_pending/<sprint-id>-retro.json` placeholder so SPRINT-06 is structurally satisfied with a Phase-6 backfill path.
6. `clawteam team show <name>` dashboard extension surfacing the 11-member roster + sprint progress + cost-rollup placeholders.

**Pure-rubric vs interactive split (Pitfall 7 partition — locked):** Rubric content for `/office-hours`, `/design-consultation`, `/investigate` lands here as static reference inside pm/designer/reviewer prompts WITH a grep-verifiable `INTERACTIVE-RUNTIME-DEFERRED:` meta-instruction line. The actual multi-turn state machines defer to Phase 4. SmartReviewRouter, reviewer decorrelation, cross-agent verification, always-human Ship gate → Phase 4. Tool-heavy skills (`/codex`, `/ship`, `/canary`, `/benchmark`, `/setup-deploy`, `/document-release`, `/land-and-deploy`) → Phase 5. Real `TeamMemoryStore` + `/learn` write path + browser pipeline + design-shotgun → Phase 6. `AttentionQueue` + cost dashboard → Phase 7.

**Delete invariant:** Removing `clawteam/plugins/gstack_sprint_plugin.py` + `clawteam/templates/gstack.toml` + `clawteam/templates/gstack/` must leave the rest of the codebase running unchanged. All gstack-specific content lives in those three locations.

</domain>

<decisions>
## Implementation Decisions

### Methodology depth per role (Area 1)

- **D-01:** **engineer** prompt = implementation-discipline rubric, ~1200 bytes. Required content (grep-verifiable):
  - "read-first-before-write" instruction (read the file being modified before any edit)
  - Atomic-commit discipline (one logical change per commit; commit messages reference plan task)
  - SHA-pin awareness at Build-phase start (record HEAD SHA into envelope; halt if reviewer reports mid-review thrash)
  - `engineer.diff_summary` envelope assertion required every Build-phase turn
  - "no fix without investigation" deferral instruction (engineer routes investigation to reviewer per `/investigate` iron-law)
  - Phase-5 tool-availability stub: "Until `/codex` and `/ship` land in Phase 5, perform implementation manually and emit a question to ceo when blocked on missing tools."
  - `SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1`
  **Why:** Engineer is one of 11 specialists from day 1. A pure stub would make engineer feel like a placeholder while pm/ceo/eng-mgr/designer/dx-lead/reviewer/qa/security all have substantive rubric content. The discipline content is canonical to gstack's Build phase even though no skill file owns it.

- **D-02:** **shipper** prompt = minimal stub, ~600 bytes. Required content:
  - Persona contract (one-paragraph identity)
  - `shipper.step` envelope assertion (Literal enum: `prep` / `pushing` / `pr-open` / `merged` / `deployed` / `verified`)
  - Phase-5 tool-availability stub: "Until `/ship` and `/land-and-deploy` land in Phase 5, write a `ship-notes.md` skeleton with `deploy_url: <pending>` placeholder and emit a question to ceo for manual ship coordination."
  - `SIGNATURE: gstack-role:shipper rubric:none envelope-version:1`
  **Why:** Shipper's methodology IS the Phase-5 ship pipeline. Adding generic SRE-practice content risks contradicting `/ship` rubric content when Phase 5 lands. Stub honestly reflects "real skill arrives in Phase 5"; still produces a real artifact (skeleton ship-notes.md) so EvidenceGate has something to validate structurally.

- **D-03:** **sre** prompt = minimal stub, ~600 bytes. Required content:
  - Persona contract
  - `sre.signal` envelope assertion (Literal enum: `nominal` / `degraded` / `regression` / `outage`)
  - Phase-5 tool-availability stub: "Until `/canary`, `/benchmark`, `/setup-deploy` land in Phase 5, monitor manually and write `canary-report.md` / `benchmark-report.md` placeholders with manually-observed signal value."
  - `SIGNATURE: gstack-role:sre rubric:none envelope-version:1`
  **Why:** Same rationale as shipper. SRE methodology lives in the Phase-5 tool skills.

### gstack.toml content shape (Area 2)

- **D-04:** **gstack.toml is a pure roster declaration.** Contents:
  - `[template]` block: `name`, `display_name`, `description`, `leader_role = "ceo"`, `phases = ["think", "plan", "build", "review", "test", "ship", "reflect"]`, `model_profile = "balanced"`, `backend = "tmux"` (or whatever the existing default is — match other templates).
  - `[[template.agents]]` × 11: each with `role`, `display_name`, `prompt_file = "prompts/<role>.md"`, `model_profile` (inherits if absent).
  - `[template.memory]` block: `root = "{data_dir}/teams/{team_name}/memory"`, `per_role = true`.
  - **No** `[[template.tasks]]` rows. **No** welcome broadcasts. **No** per-role greeting tasks.
  **Why:** "Team waits for `/sprint start`" is the product narrative. After-spawn theater (welcome tasks, greeting messages) muddies the "team is dormant until you give it work" framing. `team show` displays "11 members ready, no active sprint — run `clawteam sprint start`" and that is the correct first-run UX.

- **D-05:** **TeamManager pre-creates the per-role memory directory tree at `team spawn` time.** All 11 directories (`~/.clawteam/teams/<name>/memory/<role>/`) created idempotently as part of the spawn lifecycle. Uses existing `WorkspaceManager` / `file_locked` machinery — no new persistence primitive.
  **Why:** Phase-6 `/learn` writes will run from N parallel sprints × 11 agents simultaneously. Pre-creation is race-free and costs 11 mkdir calls. Lazy-init defers a real concurrency problem to Phase 6 unnecessarily.

### Role prompt format + per-persona envelope location (Area 3)

- **D-06:** **Role prompts ship as separate `.md` files** under `clawteam/templates/gstack/prompts/<role>.md` (× 11). gstack.toml references them via `prompt_file = "prompts/<role>.md"` (path is template-relative, resolved by `TemplateDef` loader).
  **Why:** Grep-friendly — golden tests assert signature lines + rubric content presence with native grep, no TOML parsing. Phase 6's `/learn` memory inclusions append to the prompt at render time without TOML editing. 11 small files + 1 TOML > 1 huge TOML for prose authoring.

- **D-07:** **Per-persona TurnEnvelope subclasses live at `clawteam/templates/gstack/envelope_personas.py`** (gstack-scoped, NOT alongside Phase 2's `clawteam/team/envelope.py`). The file declares 11 pydantic subclasses (PmEnvelope, CeoEnvelope, EngMgrEnvelope, DesignerEnvelope, DxLeadEnvelope, EngineerEnvelope, ReviewerEnvelope, QaEnvelope, SecurityEnvelope, ShipperEnvelope, SreEnvelope), each adding ONE namespaced required field per persona (per the table in RESEARCH.md §"Three Open Research Questions — Open Question #1"). Discriminated union resolution dispatches on `persona` field via the Phase-2 `parse_frontmatter` machinery — extension point declared in Phase 2 D-06 envelope shape.
  **Why:** Honors the "delete `gstack_sprint_plugin.py` + `gstack.toml` + `templates/gstack/` and the rest still runs" invariant. Per-persona envelopes are gstack-specific *today*; if a future template (hedge-fund-sprint, research-paper-sprint) adopts the same per-persona pattern, promote the file to `clawteam/team/envelope_personas.py` then — migration is a one-move git mv. Don't pre-promote on speculation.

### Verification stringency (Area 4)

- **D-08:** **Golden-trace fidelity = Strategy B (markdown-derived fixtures only).** Implementation:
  1. Plan task `golden-trace-prep` WebFetches each ported gstack skill markdown (`/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/retro`, `/plan-design-review`, `/design-review`, `/plan-devex-review`, `/devex-review`, `/review`, `/qa-only`, `/cso`) from upstream gstack repo.
  2. Stores them under `tests/fixtures/gstack_skills/<skill-name>.md` — committed to repo for reproducibility (these are public files).
  3. Golden tests in `tests/test_gstack_role_prompts.py` grep BOTH the upstream fixture AND the ported `clawteam/templates/gstack/prompts/<role>.md` for content presence (e.g., all 6 forcing questions present in pm.md AND in `gstack_skills/office-hours.md`).
  **Strategy A (run native gstack, record transcripts) is OUT of Phase 3 scope.** Phase 4 may need it for interactive state machine verification — that's Phase 4's research call, not Phase 3's.
  **Why:** Phase 3 ports are *transcriptions*; the fidelity question is "did all the rubric content land verbatim in the role prompt?" — directly grep-able. Strategy A's signal (interaction shape, turn count) is irrelevant to Phase 3 deliverables. Strategy B is cheap, deterministic, fully reproducible.

- **D-09:** **Reflect-phase `/learn` stub = minimal placeholder only.** GstackSprintPlugin's Reflect-phase event handler (subscribed via `on_register`) writes one file per sprint completion:
  - Path: `~/.clawteam/teams/<team_name>/_phase6_pending/<sprint_id>-retro.json`
  - Content: full retro markdown body + persona attribution metadata + `feature_flag: "phase6_learn_pending"` log line.
  - No `LearnPendingEvent` emission. No EventBus subscription work. No backfill scaffolding.
  - Phase 6 writes a one-time backfill scanner that walks `_phase6_pending/` directories on first `/learn` implementation startup.
  **Why:** ROADMAP-blessed minimum. Adding a structured event for Phase 6 migration is forward-compatibility scope that Phase 6 can absorb cheaply. Phase 3 stays focused on the substrate it actually owns.

### Plan-prep verification tasks (assumptions from RESEARCH.md to confirm at plan time)

These are NOT gray areas — they're grep/measurement tasks the planner must include in `golden-trace-prep` or equivalent prep wave:

- **D-10:** **A1 confirm:** `SprintConductor.advance_phase` accepts an `actor: str` parameter. Source: `clawteam/sprint/conductor.py`. If absent, planner adds a 1-line additive change to support `actor=leader_role` check. Low risk.
- **D-11:** **A2 confirm:** `contribute_evidence_schemas` hook is wired through `PluginManager` to call `EvidenceSchemaRegistry.register` at plugin load. Hook exists in `clawteam/plugins/base.py:79-93`; the call-site path needs grep confirmation in plan-prep.
- **D-12:** **A4 confirm:** `clawteam team show` CLI exists for other templates and accepts a member-list + dashboard-row format extensible via existing rich/typer machinery. Verify shape; if extension point is absent, planner adds one.
- **D-13:** **A5 verify:** WebFetch upstream gstack `/cso` skill markdown and extract the exact 17 false-positive exclusions. Port verbatim into `security.md`. Same for `/office-hours` (6 forcing questions verbatim) and `/plan-design-review` (10 rubric dimensions verbatim).
- **D-14:** **A7 measure:** After writing each role prompt, plan task runs `wc -c clawteam/templates/gstack/prompts/*.md` and asserts every file ≤ 4 KB and average ≤ 3 KB. Hard cap is verification gate.

### Claude's Discretion (planner picks; no need to ask user)

- Concrete pydantic field names within each of the six gstack artifact schemas (DesignDoc / PlanDoc / TestReport / ReviewReport / ShipNotes / Retro). RESEARCH.md provides a sketch — planner refines from upstream gstack artifacts.
- Internal markdown structure of each role prompt (headings, ordering of persona contract / rubric / envelope schema / signature line). The grep-verifiable content list per role is in RESEARCH.md §"Per-Role Prompt Content Map" — planner picks the layout.
- Exact wording of the `INTERACTIVE-RUNTIME-DEFERRED:` and `SHA-PIN-DEFERRED:` meta-instruction lines (must be greppable; exact prose is planner's call).
- Internal layout of the `_phase6_pending/<sprint_id>-retro.json` schema (free-form within "valid JSON, includes retro body + persona attribution + feature flag").
- Wave structure and parallelism of plans (planner determines from file dependencies).
- Whether to ship `team show` dashboard extension as one plan or split per dashboard column (members vs. memory placeholders vs. sprint progress vs. cost rollup).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (planner, plan-checker, executor) MUST read these before planning or implementing.**

### Phase 3 deliverable specifications (load-bearing)

- `.planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md` — Architecture patterns, Per-Role Prompt Content Map (the load-bearing rubric port table), Code Examples (gstack.toml shape, role prompt skeleton, GstackSprintPlugin registration shape, per-role envelope reassertion subclass, DesignDoc artifact schema), Validation Architecture (test framework + Phase Requirements → Test Map + Wave 0 gaps), three open-question resolutions, Assumptions Log A1–A8.
- `.planning/ROADMAP.md` §"Phase 3: Gstack Team Template & Methodology Port" (lines 148-179) — phase goal, success criteria 1–7, requirements list, canonical refs.
- `.planning/REQUIREMENTS.md` — TEAM-01..05, SKILL-01..08, SPRINT-06, UX-01, UX-07 verbatim.

### Project-locked context

- `.planning/PROJECT.md` §"Key Decisions" — 11-agent roster (row 1), pm/ceo split (row 2), team persistent / sprint transient (row 3), port-by-nature (row 4), PhaseRegistry plugin pattern (row 5), Constraints (Python 3.10+, no new required runtime deps, persistence under `get_data_dir()`).

### Substrate (what Phase 3 plugs into — verified shipped or in flight)

- `.planning/phases/01-core-harness-extensions/01-CONTEXT.md` — Phase 1 D-08 PhaseRegistry pattern, InteractionGate substrate.
- `.planning/phases/02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention/02-CONTEXT.md` — Phase 2 D-01..D-05 EvidenceGate, D-06 TurnEnvelope (persona/step_label/done required fields), D-23 auto_advance semantics.
- `clawteam/templates/__init__.py` (lines 11-17, 24-44, 75-101) — TOML loader + `TemplateDef` pydantic model. Phase 3 extends additively.
- `clawteam/templates/software-dev.toml` — existing template TOML schema convention. `gstack.toml` mirrors structure.
- `clawteam/plugins/base.py` (lines 14-93) — `HarnessPlugin` ABC + Phase 1/2 hook surface (`contribute_phases`, `contribute_evidence_schemas`, `contribute_prompts`, `on_register`).
- `clawteam/plugins/manager.py` — plugin loader (Phase 3 plugin loaded only when `gstack` template is selected).
- `clawteam/plugins/ralph_loop_plugin.py` — convention reference for `GstackSprintPlugin`'s shape (~250 LOC cohesive plugin).
- `clawteam/sprint/conductor.py` — SprintConductor (Phase 2). Phase 3 doesn't call it; populates the registry it reads.
- `clawteam/harness/phases.py` (lines 19-29, 39-104) — `Phase` as open str + `PhaseGate` ABC + `DEFAULT_PHASES`.
- `clawteam/harness/evidence_gate.py`, `clawteam/harness/evidence_schemas.py` — Phase 2 schema registry. Phase 3 fills with six pydantic models.
- `clawteam/team/envelope.py` (lines 1-80) — `TurnEnvelope` + `parse_frontmatter`. Phase 3 extends with 11 per-persona subclasses (in `clawteam/templates/gstack/envelope_personas.py` per D-07).
- `clawteam/team/manager.py` (lines 1-80) — TeamManager + `create_team` flow. Phase 3 extends with per-role memory dir pre-creation (D-05).
- `clawteam/spawn/__init__.py` (lines 1-32) — spawn registry public API. Phase 3 spawns through this — never bypass.
- `clawteam/cli/` — Typer app for `clawteam team show` extension (D-12 verification).

### Research foundation

- `.planning/research/SUMMARY.md` §Phase 3 — research-flag rationale, gaps to address.
- `.planning/research/ARCHITECTURE.md` Pattern 1 (PhaseRegistry plugin), Pattern 5 (TeamMemory layered), Pattern 6 (SmartReviewRouter — referenced for Phase 4 boundary), GstackSprintPlugin wiring shape.
- `.planning/research/PITFALLS.md` Pitfall 1 (drift — Echoing-paper 70%→9% structured protocol finding), Pitfall 7 (skill-port collapse — the partition this phase enforces), Pitfall 8 (gate gaming — pydantic structural validation prevents stubs), Pitfall 14 (backwards-compat — additive-only TemplateDef extension).
- `.planning/research/FEATURES.md` Differentiator #1 (11-role pre-configured team), #2 (7-phase sprint as product).
- `.planning/research/STACK.md` — standard stack (already in repo: pydantic v2, tomllib/tomli, pluggy).

### Upstream gstack source (WebFetch fixtures during plan-prep per D-08)

- https://github.com/garrytan/gstack — port `/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/retro`, `/plan-design-review`, `/design-review`, `/plan-devex-review`, `/devex-review`, `/review`, `/qa-only`, `/cso` skill markdown verbatim into `tests/fixtures/gstack_skills/<skill-name>.md`.

</canonical_refs>

<code_context>
## Existing Code Insights (from RESEARCH.md verified reads)

### Reusable Assets (Phase 3 uses, never reinvents)

- `clawteam/templates/__init__.py` `TemplateDef` pydantic model — extends with optional fields (`leader_role`, `prompt_file` per agent, `phases`, `memory`). Pydantic default is `extra="ignore"` (verified line 24-44) so existing 6 templates accept the schema unchanged.
- `clawteam/spawn/__init__.py` registry — spawning the 11 agents goes through this. Backend selection (`tmux` / `subprocess` / `wsh`) is declared in `gstack.toml` `backend = "tmux"`.
- `clawteam/workspace/WorkspaceManager` — per-agent worktrees ("desks") already supported. `team spawn gstack` calls existing `create_workspace` for each of 11 agents.
- `clawteam/team/manager.py` `TeamManager` — extend with per-role memory directory pre-creation step (D-05). No new persistence primitive needed.
- `clawteam/team/envelope.py` `TurnEnvelope` + `parse_frontmatter` — base class for the 11 per-persona subclasses. Discriminator: `persona` field.
- `clawteam/sprint/conductor.py` `SprintConductor` — Phase 3 plugin populates the `PhaseRegistry` and `EvidenceSchemaRegistry` it reads. No conductor edits.
- `clawteam/harness/evidence_schemas.py` `EvidenceSchemaRegistry` — Phase 3 calls `register()` 6 times via `contribute_evidence_schemas` hook (one per gstack artifact type).
- `clawteam/plugins/ralph_loop_plugin.py` — the canonical "single cohesive plugin file" convention. `GstackSprintPlugin` mirrors structure: ~250 LOC, all hooks in one file.
- `clawteam/cli/` Typer app — extend `team show` for the gstack dashboard (members + sprint progress + memory placeholders + cost rollup placeholders). D-12 verifies extension point shape.
- `tests/test_template_regression_matrix.py` (existing) — extend with cross-template isolation test asserting `software-dev` / `hedge-fund` / `code-review` / `harness-default` / `research-paper` / `strategy-room` spawns do NOT trigger `GstackSprintPlugin.on_register`.
- `tests/test_evidence_schemas.py` (Phase 2) — extend with the 6 gstack pydantic schema validations.
- `tests/test_cli_commands.py` (existing) — extend with `team show gstack` dashboard verification.

### Established Patterns (constrain Phase 3 implementation)

- **TemplateDef extension is additive only** — pydantic `extra="ignore"` default means new optional fields don't break existing templates. Phase 3 adds fields; never modifies existing field semantics.
- **Plugin loaded only when its template is selected** — Phase 1 RFC 001 §4.3 D-04. `GstackSprintPlugin` registers via pluggy; activation gated on `gstack` template selection. Existing 6 templates never see gstack content.
- **Phase as open string** — `clawteam/harness/phases.py:19-29`. Phase identifiers are strings, not enum values; `PhaseRegistry` accepts arbitrary phase names. The 7 gstack phases (`think`, `plan`, `build`, `review`, `test`, `ship`, `reflect`) are namespaced by plugin scope, not by changing core enum.
- **Spawning ALWAYS goes through `clawteam/spawn/` registry** — never bypass. `gstack.toml` declares `backend = "tmux"` (or matches existing default); spawn machinery handles routing.
- **Single cohesive plugin file** — convention from `ralph_loop_plugin.py`. All hooks for a feature live in one ~250 LOC file. `GstackSprintPlugin` follows this.
- **Persistence under `get_data_dir()`** — never in-project. PROJECT.md Constraints. `~/.clawteam/teams/<name>/` (or `$CLAWTEAM_DATA_DIR` override).
- **Atomic file-locked persistence** — `file_locked()` for any write to `~/.clawteam/`. The Reflect-phase `_phase6_pending/<sprint-id>-retro.json` writer uses this.
- **EvidenceGate validates structure (not just presence)** — Phase 2 D-01..D-05. The 6 gstack pydantic schemas must round-trip through Phase 2 `parse_frontmatter` + structural validation; stub-grade content fails the gate.

### Integration Points

- `gstack.toml` registered through existing `clawteam/templates/__init__.py` loader.
- `GstackSprintPlugin.contribute_phases()` populates `PhaseRegistry` (Phase 1).
- `GstackSprintPlugin.contribute_evidence_schemas()` populates `EvidenceSchemaRegistry` (Phase 2).
- `GstackSprintPlugin.contribute_prompts()` resolves `prompts/<role>.md` files at runtime per phase + role.
- `SprintConductor.advance_phase(actor=)` consults `template.leader_role` to enforce ceo-only advancement (D-10 confirms parameter exists or adds it).
- `TeamManager.create_team` extended with per-role memory directory pre-creation step (D-05).
- `clawteam team show <name>` Typer command extended with gstack dashboard rows.
- 11 per-persona envelope subclasses extend Phase 2 `TurnEnvelope` via discriminated union dispatched on `persona` field.
- Reflect-phase event handler subscribed via `on_register` writes `_phase6_pending/` placeholder.

</code_context>

<specifics>
## Specific Ideas

- **`SIGNATURE:` line format is canonical.** Every role prompt MUST contain a line of the form `SIGNATURE: gstack-role:<role> rubric:<skill-or-none> envelope-version:1`. Golden tests grep for this string. RESEARCH.md §"Per-Role Prompt Content Map" provides the per-role signature value.
- **`INTERACTIVE-RUNTIME-DEFERRED:` and `SHA-PIN-DEFERRED:` meta-instructions are canonical greppable strings.** They appear in pm.md (for /office-hours), designer.md (for /design-consultation), reviewer.md (for /investigate and SHA-pinning). Used by golden tests AND read by future Phase 4 state-machine implementations to find the deferred surface.
- **Role prompt budget is enforced as a verification gate.** D-14 measurement task asserts every prompt ≤ 4 KB and average ≤ 3 KB. Hard fail if exceeded.
- **`tests/fixtures/gstack_skills/` is committed to the repo** (not gitignored). Public upstream content; pin for reproducibility of golden tests across CI runs without re-WebFetching.
- **`_phase6_pending/<sprint_id>-retro.json` schema is intentionally loose** — JSON object with retro body + persona attribution + `feature_flag: "phase6_learn_pending"`. Phase 6's backfill scanner reads whatever's there.

</specifics>

<deferred>
## Deferred Ideas

### To Phase 4 (interactive state machines + smart routing)
- `/office-hours`, `/design-consultation`, `/investigate` as multi-turn state machines with per-Q/per-dimension/per-hypothesis progression.
- SmartReviewRouter SHA-pinned multi-signal routing (UI → designer; auth/crypto → security; api → dx-lead; reviewer always).
- Reviewer decorrelation prompts + parallel-execution → reviewer aggregation.
- Cross-agent verification (qa verifies engineer's test-report.md hashes; reviewer verifies designer's design-doc covers all 6 forcing-question answers).
- Always-human Ship-phase gate (`force_interactive_phases=["ship"]` per Phase 2 reservation).
- `/investigate` auto-applies `/freeze` to module under investigation, releases on completion.

### To Phase 5 (tool-heavy skills)
- `/codex` cross-model second opinion (engineer/reviewer).
- `/ship`, `/land-and-deploy`, `/document-release` ship pipeline (shipper).
- `/canary`, `/benchmark`, `/setup-deploy` SRE pipeline (sre).

### To Phase 6 (browser pipeline + design-shotgun + real /learn)
- `TeamMemoryStore` real implementation with provenance + decay + human gate on high-impact entries.
- `/learn` write path replacing the Phase-3 placeholder; backfill scanner walks `_phase6_pending/`.
- `/browse`, `/open-gstack-browser`, `/setup-browser-cookies`, `/design-shotgun`, `/design-html` via `clawteam[browser]` Playwright optional extra.

### To Phase 7 (parallel sprints + cost observability)
- `AttentionQueue` cross-sprint pending-questions view + `clawteam attend` CLI.
- Multi-sprint concurrency caps + cost dashboard with model fallback ladder + per-agent token rollup (replaces the Phase-3 dashboard placeholders).

### To post-v1
- Per-team prompt customization hooks (user-overridable role prompts beyond the gstack defaults).
- Helper-agent spawning inside engineer (engineer forks ephemeral helpers per gstack's parallel-Build pattern; v1 ships solo Build).
- Strategy A golden traces (sandbox-gstack + recorded transcripts) — only revisit if Phase 4 needs them and discuss-phase 4 raises the question.
- Promote `envelope_personas.py` from `clawteam/templates/gstack/` to `clawteam/team/` if a second template (hedge-fund-sprint) adopts the per-persona envelope pattern.
- `LearnPendingEvent` EventBus emission for forward-compatible Phase-6 migration (Phase 6 backfill scanner sufficient for now).

### Reviewed Todos (not folded)
None — `.planning/todos/pending/` is empty (verified via `gsd-tools list-todos`).

</deferred>

<plan_prep_verifications>
## Plan-Prep Verification Tasks (must run BEFORE main planning)

These map to Assumptions A1–A8 in RESEARCH.md. The planner should include them as a Wave-0 prep set so unverified assumptions don't compound into wrong plans:

| ID | Verification | Action if fails |
|----|--------------|-----------------|
| D-10 (A1) | `SprintConductor.advance_phase` accepts `actor: str` parameter | Planner adds 1-line additive change to `clawteam/sprint/conductor.py` |
| D-11 (A2) | `contribute_evidence_schemas` hook is wired through `PluginManager` to call `EvidenceSchemaRegistry.register` at plugin load | Planner adds wiring as sub-task in plugin plan |
| D-12 (A4) | `clawteam team show` Typer command has clean extension point for new dashboard rows | Planner adds extension point as sub-task |
| D-13 (A5) | Upstream gstack `/cso`, `/office-hours`, `/plan-design-review` markdown content WebFetched + 17 exclusions / 6 forcing questions / 10 dimensions counts confirmed | Planner adjusts security.md / pm.md / designer.md content to match actual upstream |
| D-14 (A7) | Verification gate: every `clawteam/templates/gstack/prompts/*.md` ≤ 4 KB; average ≤ 3 KB | Hard fail on Phase 3 verification if exceeded; plan must reduce content (e.g., move full /cso exclusions list to a referenced fixture file) |

Already resolved by this CONTEXT.md (no plan-prep task needed): A3 (TemplateDef accepts optional fields — verified via `extra="ignore"` default), A6 (Strategy B confirmed by D-08), A8 (Reflect placeholder shape confirmed by D-09).

</plan_prep_verifications>

---

*Phase: 03-gstack-team-template-methodology-port*
*Context gathered: 2026-04-20 via /gsd-discuss-phase*
*Decisions: D-01 through D-14 (14 locked); plus 5 plan-prep verification tasks (D-10..D-14 overlap)*
*Next: /gsd-plan-phase 3*
