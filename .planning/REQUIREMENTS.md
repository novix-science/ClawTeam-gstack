# Requirements: ClawTeam-gstack

**Defined:** 2026-04-15
**Core Value:** You hire a virtual engineering team, and over time they get better at working with you.

## v1 Requirements

Requirements for the gstack-as-team milestone. Derived from `PROJECT.md` Active scope, `research/FEATURES.md` P1 list, and `research/PITFALLS.md` ship-blocker preventions. Each maps to a roadmap phase.

### Core Harness Extensions (CORE)

Generic, upstream-PR-friendly additions to ClawTeam's harness. No gstack-specific semantics.

- [ ] **CORE-01**: `PhaseRegistry` exists as a harness-level registry that plugins populate with `Phase` entries (name + position + optional default gates). `PhaseState.phases` accepts the registered phases at construction time without modifying the existing `Phase` str type.
- [ ] **CORE-02**: `HarnessPlugin.contribute_phases()` hook exists and is called by `plugins.manager` during plugin load; registered phases are visible to `HarnessOrchestrator`.
- [ ] **CORE-03**: Existing templates (`software-dev`, `hedge-fund`, `code-review`, `harness-default`, `research-paper`, `strategy-room`) continue to spawn, advance phases, and pass all existing tests with no code changes.
- [ ] **CORE-04**: `SprintState` exists as a pydantic model capturing: sprint id, goal, phase_state, owning team, workspace branch, artifacts, participants, pending-questions ids. Persisted via existing file-locked JSON machinery under `~/.clawteam/teams/<team>/sprints/<id>/state.json`.
- [ ] **CORE-05**: `SprintConductor` manages one team's N concurrent sprints — enumerates active sprints, dispatches phase-advance events, coordinates per-sprint artifact stores.
- [ ] **CORE-06**: One team can hold ≥10 concurrent sprints without race conditions on the team-level task store or memory store (verified by integration test).
- [ ] **CORE-07**: Sprint pause / resume: `clawteam sprint pause <id>` checkpoints state; `clawteam sprint resume <id>` rehydrates and re-emits the last pending gate event. Sprints survive a full `HarnessOrchestrator` restart.

### Human Interaction (INT)

Cross-sprint human-in-loop, preserving gstack's taste-decision essence.

- [ ] **INT-01**: `InteractionGate` exists as a `PhaseGate` subclass. Blocks phase transition until a companion `answers/<N>.md` is written for each `questions/<N>.md` artifact.
- [ ] **INT-02**: Phase agents write structured questions.md markdown (per-question H3 headings + numbered choices or freeform fields). Answers.md supports both selected-option and freeform reply per question.
- [ ] **INT-03**: `AttentionQueue` exists as a cross-sprint priority-sorted queue of pending questions. Priority formula is configurable; default combines URGENCY tag + BLOCKING flag + AGE (oldest floats up).
- [ ] **INT-04**: `clawteam attend` CLI: prints the top-N pending questions across all teams' sprints; opens the chosen question's markdown in `$EDITOR`; on save, gate unblocks. Works for 1 sprint and scales to ≥10 parallel sprints with the same command.
- [ ] **INT-05**: Question visibility: the attention queue auto-refreshes on `watchdog` filesystem events when the optional `watchdog` package is installed; falls back to polling on 2-second intervals otherwise. No hard dep.
- [ ] **INT-06**: Auto-advance toggle: per-sprint config `auto_advance: true|false` decides whether `InteractionGate` is inserted on every transition or only when a phase agent explicitly writes a question artifact.

### Memory (MEM)

Team-scoped, layered, grep-first; provenance + decay to prevent memory poisoning.

- [ ] **MEM-01**: `TeamMemoryStore` exists under `~/.clawteam/teams/<team>/memory/` with two-tier layout: `memory/team/` (shared) + `memory/agents/<role>/` (per-role private).
- [ ] **MEM-02**: Writes are append-only JSONL entries with frontmatter: id, author (agent id), sprint id, phase, timestamp, tags, evidence citation (path:line or artifact ref), confidence level.
- [ ] **MEM-03**: Reads support grep-first retrieval by tag + keyword; keyword match ranked by recency-weighted score.
- [ ] **MEM-04**: `/learn` skill exposes `learn write <scope> <title>`, `learn list <scope> [--tag]`, `learn search <query>`, `learn prune <id>`. Agents call via existing skill machinery; human calls via `clawteam` CLI.
- [ ] **MEM-05**: Provenance tracking: every memory entry cites evidence; entries without evidence get a lower retrieval rank (not blocked — flagged).
- [ ] **MEM-06**: High-impact writes (tagged `impact:high` or under `memory/team/decisions/`) require human confirmation through `InteractionGate` before commit. Prevents memory poisoning (PITFALLS #10).
- [ ] **MEM-07**: Memory decay: entries inherit a TTL from their tag (e.g., `pattern` 90 days, `preference` indefinite, `incident` 180 days). Expired entries rank below unexpired on retrieval; not auto-deleted.

### Team Roster & Template (TEAM)

The 11-persona team that ships as `gstack.toml`.

- [x] **TEAM-01**: `clawteam/templates/gstack.toml` ships and loads through existing template machinery.
- [x] **TEAM-02**: Template defines 11 persistent agents with distinct role prompts: pm (YC Office Hours advisor), ceo (scope owner + team leader), eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre.
- [x] **TEAM-03**: Each agent is spawned with its own worktree ("desk") reused across sprints; per-role memory scope.
- [x] **TEAM-04**: ceo is the team leader responsible for: advancing sprint phases, routing sprint work, consulting human via `InteractionGate` on scope decisions.
- [x] **TEAM-05**: Template supports model_profile selection via `clawteam team spawn gstack --model-profile balanced|quality|budget`; default is `balanced` (Pitfall #12 cost-blowup prevention — never default to `quality`).
- [ ] **TEAM-06**: Template is additive: existing templates unchanged; `gstack.toml` is an opt-in choice.

### Sprint Plugin (SPRINT)

The `GstackSprintPlugin` registering the 7-phase sprint.

- [ ] **SPRINT-01**: `GstackSprintPlugin` registers 7 phases via `PhaseRegistry`: Think → Plan → Build → Review → Test → Ship → Reflect. Phases appear only when the plugin is loaded; other templates are not affected.
- [ ] **SPRINT-02**: Each phase ships with an `EvidenceGate` (extension of `ArtifactRequiredGate`) that checks for both presence AND structural validity of the phase's artifact: design-doc.md (Think), plan-doc.md (Plan), diff+patch-notes.md (Build), review-report.md (Review), test-report.md (Test), ship-notes.md (Ship), retro.md (Reflect). Prevents gate gaming (PITFALLS #8).
- [ ] **SPRINT-03**: `SmartReviewRouter` selects Review-phase participants by diff content via rule config in `gstack.toml`: UI touched → designer; public API → dx-lead; crypto/auth → security; always → reviewer.
- [x] **SPRINT-04**: Review phase agents run in parallel; `reviewer` agent runs last, synthesizes parallel reports into a single `review-report.md` aggregation. Gate passes on aggregation, not individual reports.
- [x] **SPRINT-05**: Ship phase always requires human approval via `InteractionGate` (ignores `auto_advance: true`). Reason: production blast radius.
- [x] **SPRINT-06**: Reflect phase writes retro.md AND invokes `/learn` to capture sprint-level patterns to team-shared memory.

### Gstack Skill Ports (SKILL)

Methodology as role prompts (baked-in) + tool-heavy skills as invokable ClawTeam skills.

**Baked into role prompts (14 skills):**
- [x] **SKILL-01**: pm role prompt implements /office-hours — 6 forcing questions with challenge-framing instruction.
- [x] **SKILL-02**: ceo role prompt implements /plan-ceo-review — 4 modes (Expansion, Selective, Hold, Reduction) with decision output schema.
- [x] **SKILL-03**: eng-mgr role prompt implements /plan-eng-review + /retro — architecture lock, data-flow diagrams, edge-case matrix, test plan; retro has per-person breakdowns.
- [x] **SKILL-04**: designer role prompt implements /plan-design-review + /design-review + /design-consultation — 0-10 rubric, AI-slop detection, interactive-per-dimension feedback, design-system research.
- [x] **SKILL-05**: dx-lead role prompt implements /plan-devex-review + /devex-review — persona exploration, TTHW benchmarking, friction tracing.
- [x] **SKILL-06**: reviewer role prompt implements /review + /investigate — production-bug detection + iron-law root-cause methodology (no fix without investigation; halt after 3 failed hypotheses).
- [x] **SKILL-07**: qa role prompt implements /qa + /qa-only — browser-backed testing, bug-fix + regression-test loop; `/qa-only` variant suppresses code changes.
- [x] **SKILL-08**: security role prompt implements /cso — OWASP Top 10 + STRIDE checklist, 17 false-positive exclusions, 8/10+ confidence gate.
- [ ] **SKILL-09**: All role prompts use a structured response envelope (per PITFALLS #1 persona-drift prevention): persona-identity header, step label, output schema, no-freelance rule.

**Invokable ClawTeam skills (tool-heavy):**
- [ ] **SKILL-10**: `/browse` + `/open-gstack-browser` + `/setup-browser-cookies` — real-Chromium browser via Playwright (optional `clawteam[browser]` extra). Owned by engineer, qa, dx-lead. Feature-detected; useful error on missing dep.
- [ ] **SKILL-11**: `/design-shotgun` — mockup variant generation + comparison board + iterative refinement with taste memory under designer's per-agent memory.
- [ ] **SKILL-12**: `/design-html` — Pretext-pattern production HTML generation with framework detection (React/Svelte/Vue).
- [ ] **SKILL-13**: `/codex` — independent OpenAI Codex CLI second opinion via existing `NativeCliAdapter`. Three modes: review (pass/fail gate), adversarial, consultation.
- [ ] **SKILL-14**: `/ship` — sync main + run tests + audit coverage + push + open PR. Bootstraps a test framework if none exists.
- [ ] **SKILL-15**: `/land-and-deploy` — merge PR + wait for CI + deploy + verify production health. Human-gated.
- [ ] **SKILL-16**: `/document-release` — cross-reference diff against all doc files, update stale ones. Auto-invoked by `/ship`.
- [ ] **SKILL-17**: `/canary` — post-deploy monitoring loop (console errors, perf regressions).
- [ ] **SKILL-18**: `/benchmark` — Core Web Vitals + page load baselines with before/after on every PR.
- [ ] **SKILL-19**: `/setup-deploy` — one-time deployment configuration wizard.

### Safety Rails (SAFETY)

Ported gstack guardrails as harness primitives, not per-agent skills.

- [ ] **SAFETY-01**: `/careful` — EventBus hook warns before destructive commands (rm -rf, DROP TABLE, force-push, git reset --hard). Applies to every agent in the team.
- [ ] **SAFETY-02**: `/freeze <path>` — WorkspaceManager enforces write-lock to paths outside the frozen path. Agents attempting writes receive an error (blocked at tool-call level, not after the fact).
- [ ] **SAFETY-03**: `/guard` — composite of `/careful` + `/freeze`.
- [ ] **SAFETY-04**: `/unfreeze` — release write-lock; requires audit log entry.
- [x] **SAFETY-05
**: `/investigate` skill (reviewer role) auto-applies `/freeze` to the module under investigation for the duration of the investigation.

### Quality / Pitfall Prevention (QUALITY)

Ship-blocker preventions from `PITFALLS.md`. Every one is a v1 requirement because retrofitting is painful.

- [ ] **QUALITY-01**: Structured response envelope enforced on every agent turn (drift prevention per PITFALLS #1).
- [ ] **QUALITY-02**: Cycle detector in transport: if agents A → B → A within N turns, break cycle, escalate to human via `AttentionQueue` (deadlock prevention per PITFALLS #2).
- [ ] **QUALITY-03**: Context window guard: agent prompts assembled from {role prompt + relevant memory + minimal working artifacts} ≤ configurable token budget. Excess memory spilled to retrieval, not inlined (context exhaustion prevention per PITFALLS #3).
- [ ] **QUALITY-04**: Active-agent slot pool: harness caps concurrent active agents at N (default 6). Idle agents dormant. Prevents resource blowup on laptops (PITFALLS #4).
- [ ] **QUALITY-05**: `AttentionQueue` auto-digest: questions grouped by sprint + age; Catch-Up digest view surfaces "4 sprints stalled >2h, 1 CRITICAL" — prevents attention fatigue (PITFALLS #5).
- [ ] **QUALITY-06**: Workspace hardening: file-lock retry with exponential backoff; `git index` corruption detection + auto-recovery; per-agent worktree integrity check on resume (PITFALLS #6).
- [x] **QUALITY-07
**: Gstack interactive skill state-machines: `/office-hours`, `/plan-design-review`, `/autoplan` ported as multi-turn state machines (not one-shot prompt bakings) that preserve the per-question interactivity (PITFALLS #7).
- [ ] **QUALITY-08**: `EvidenceGate` validates artifact structure (not just presence) — e.g., design-doc.md must contain all 6 forcing-question answers; test-report.md must cite actual test run output (PITFALLS #8).
- [x] **QUALITY-09**: `SmartReviewRouter` pins to a commit SHA — routing decision is made on the SHA that will be reviewed, not the HEAD that might have moved (PITFALLS #9 thrashing prevention).
- [ ] **QUALITY-10**: Memory provenance + decay + human gate on high-impact (covered by MEM-05, MEM-06, MEM-07) (PITFALLS #10).
- [ ] **QUALITY-11**: Progress-on-artifact rule: an agent's turn is "progress" only if it produced new artifact content or an AttentionQueue entry. Consecutive no-progress turns trigger human escalation (theater prevention per PITFALLS #11).
- [ ] **QUALITY-12**: Cost observability: `clawteam team show` displays per-agent token usage and estimated cost; sprint-level cost rollups. Advisor pattern reserves expensive model calls for critical gates. Cache hit rate surfaced (PITFALLS #12).
- [x] **QUALITY-13**: Reviewer decorrelation: parallel reviewers receive different system prompts optimized for their persona (reviewer=staff-eng-cross-cutting, security=threat-model-first, designer=rubric-first, dx-lead=friction-first) so their findings diverge rather than mirror each other (PITFALLS #13).
- [ ] **QUALITY-14**: Backwards-compatibility regression matrix in CI: every existing template (software-dev, hedge-fund, etc.) spawns + runs + passes existing tests after every gstack-related change (PITFALLS #14).
- [ ] **QUALITY-15**: Env deny-filter: `_env()` helpers never surface secret-shaped values (API keys, tokens) into logs, board views, or memory (PITFALLS #17).

### User Experience (UX)

CLI and dashboard surfaces.

- [x] **UX-01**: `clawteam team spawn gstack --name <name>` hires a new 11-agent team.
- [ ] **UX-02**: `clawteam sprint start --team <name> --goal "..."` dispatches a new sprint onto an existing team.
- [ ] **UX-03**: `clawteam sprint status <id>` shows current phase, active participants, pending-questions count, recent artifacts.
- [ ] **UX-04**: `clawteam sprint list --team <name>` lists all sprints with phase + status.
- [ ] **UX-05**: `clawteam sprint show <id>` displays full sprint detail: participants, phase history, artifacts, memory writes.
- [ ] **UX-06**: `clawteam attend` surfaces the top-N pending questions across sprints; user answers, queue re-refreshes.
- [x] **UX-07**: `clawteam team show <name>` displays team dashboard: member list + memory highlights + active sprint progress bars + cost/token rollup.
- [ ] **UX-08**: `clawteam doctor` detects missing optional tools (Chromium, codex CLI, ngrok, watchdog) and prints install instructions per detected OS.
- [ ] **UX-09**: All user-facing CLI commands support `--json` for machine-readable output (consistent with existing `clawteam` pattern).

## v2 Requirements

Deferred to post-v1 release. Tracked but not in current roadmap.

### Advanced Multi-Team (MULTI)

- **MULTI-01**: Multi-team Conductor UI — cross-team dashboard showing all user's teams at once
- **MULTI-02**: Cross-team memory export/import (explicit user action, never automatic)

### Board / Web UI (BOARD)

- **BOARD-01**: Sprint dashboard panel in the existing clawteam board web UI
- **BOARD-02**: Pending-questions panel with in-browser answer flow
- **BOARD-03**: Attention-queue visualization (Kanban-style)

### Advanced Memory (MEM-V2)

- **MEM-V2-01**: Embedding-based retrieval via sqlite-vec (upgrade path from v1 grep-first)
- **MEM-V2-02**: Cross-sprint pattern extraction (eng-mgr retro auto-generates team-level patterns)

### Extended Skill Surface (SKILL-V2)

- **SKILL-V2-01**: `/pair-agent` cross-vendor browser coordination via ngrok
- **SKILL-V2-02**: Template customization hooks (user overrides role prompts / skill assignments)
- **SKILL-V2-03**: Helper spawning for engineer (ephemeral sub-worktrees for parallel Build sub-tasks)

### Upstream (UP)

- **UP-01**: Land Phase 0 + Phase 1 + Phase 2 changes as a PR to ClawTeam mainline

## Out of Scope

Explicit exclusions to prevent scope creep. Anti-features from `research/FEATURES.md` belong here.

| Feature | Reason |
|---------|--------|
| Full auto-pilot sprint (no human touchpoints) | Dilutes gstack's taste-decision value; creates "multi-agent theater" per MAST study |
| Dynamic agent creation mid-sprint | Violates 11-persona narrative; new agents have no memory |
| Per-agent custom LLM picking | Multiplies auth/cost/reliability surface by 11; not needed for v1 |
| Agent voting / consensus loops | Deadlock risk (PITFALLS #2); strict DAG (pm → ceo) only |
| Real-time agent chat UI | Encourages chatty agents (token burn + drift) |
| Replay sprint with different parameters | Requires deep determinism; 10x cost for marginal feature |
| User-defined slash commands in-team | Dilutes specialization; memory-classification nightmare |
| Always-on multi-team Conductor UI (v1) | v2 scope per PROJECT.md; single-team is the hook |
| Unified identity across teams | Breaks team isolation; memory poisoning risk |
| Auto-downgrade model mode | Low-recall heuristic; users hate silent quality degradation |
| Auto-install Chromium / ngrok / codex | `clawteam doctor` surfaces install commands instead |
| Auto-PR-merge on green CI | Production blast radius; human approval required |
| Quick-sprint heuristic (skip phases) | Dilutes team narrative; 7-phase discipline is the product |
| Pool/shared specialist across teams | Breaks "my team" narrative |
| gstack-analytics dashboard port | board can host sprint views |

## Traceability

Which phase covers which requirement. Finalized during roadmap creation (see `.planning/ROADMAP.md`).

Roadmap is 8 phases (granularity: fine): 0 Foundation, 1 Core Extensions, 2 Sprint Engine + Preventions, 3 Team & Methodology, 4 Interactive/Routing/Verification, 5 Tool-Heavy Skills, 6 Browser/Design/Memory, 7 Parallel Sprints + Cost.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CORE-01 | Phase 1 | Pending |
| CORE-02 | Phase 1 | Pending |
| CORE-03 | Phase 0 | Pending |
| CORE-04 | Phase 1 | Pending |
| CORE-05 | Phase 2 | Pending |
| CORE-06 | Phase 7 | Pending |
| CORE-07 | Phase 2 | Pending |
| INT-01 | Phase 1 | Pending |
| INT-02 | Phase 1 | Pending |
| INT-03 | Phase 7 | Pending |
| INT-04 | Phase 7 | Pending |
| INT-05 | Phase 7 | Pending |
| INT-06 | Phase 2 | Pending |
| MEM-01 | Phase 6 | Pending |
| MEM-02 | Phase 6 | Pending |
| MEM-03 | Phase 6 | Pending |
| MEM-04 | Phase 6 | Pending |
| MEM-05 | Phase 6 | Pending |
| MEM-06 | Phase 6 | Pending |
| MEM-07 | Phase 6 | Pending |
| TEAM-01 | Phase 3 | Complete |
| TEAM-02 | Phase 3 | Complete |
| TEAM-03 | Phase 3 | Complete |
| TEAM-04 | Phase 3 | Complete |
| TEAM-05 | Phase 3 | Complete |
| TEAM-06 | Phase 0 | Pending |
| SPRINT-01 | Phase 2 | Pending |
| SPRINT-02 | Phase 2 | Pending |
| SPRINT-03 | Phase 4 | Partial (04-06: router + rules shipped; 04-10 wires dispatch; 04-11: plugin contribute_review_routers glue shipped) |
| SPRINT-04 | Phase 4 | Complete |
| SPRINT-05 | Phase 4 | Complete |
| SPRINT-06 | Phase 3 | Complete |
| SKILL-01 | Phase 3 | Complete |
| SKILL-02 | Phase 3 | Complete |
| SKILL-03 | Phase 3 | Complete |
| SKILL-04 | Phase 3 | Complete |
| SKILL-05 | Phase 3 | Complete |
| SKILL-06 | Phase 3 | Complete |
| SKILL-07 | Phase 3 | Complete |
| SKILL-08 | Phase 3 | Complete |
| SKILL-09 | Phase 2 | Pending |
| SKILL-10 | Phase 6 | Pending |
| SKILL-11 | Phase 6 | Pending |
| SKILL-12 | Phase 6 | Pending |
| SKILL-13 | Phase 5 | Pending |
| SKILL-14 | Phase 5 | Pending |
| SKILL-15 | Phase 5 | Pending |
| SKILL-16 | Phase 5 | Pending |
| SKILL-17 | Phase 5 | Pending |
| SKILL-18 | Phase 5 | Pending |
| SKILL-19 | Phase 5 | Pending |
| SAFETY-01 | Phase 2 | Pending |
| SAFETY-02 | Phase 2 | Pending |
| SAFETY-03 | Phase 2 | Pending |
| SAFETY-04 | Phase 2 | Pending |
| SAFETY-05 | Phase 4 | Pending |
| QUALITY-01 | Phase 2 | Pending |
| QUALITY-02 | Phase 2 | Pending |
| QUALITY-03 | Phase 2 | Pending |
| QUALITY-04 | Phase 7 | Pending |
| QUALITY-05 | Phase 7 | Pending |
| QUALITY-06 | Phase 2 | Pending |
| QUALITY-07 | Phase 4 | Complete |
| QUALITY-08 | Phase 2 | Pending |
| QUALITY-09 | Phase 4 | Complete (04-06: schema substrate; 04-10: SHA pinning + mid-review thrash event) |
| QUALITY-10 | Phase 6 | Pending |
| QUALITY-11 | Phase 2 | Pending |
| QUALITY-12 | Phase 7 | Pending |
| QUALITY-13 | Phase 4 | Complete (04-06: 4 decorrelation prompts; 04-11: plugin appends via review-phase supplement hook) |
| QUALITY-14 | Phase 0 | Pending |
| QUALITY-15 | Phase 0 | Pending |
| UX-01 | Phase 3 | Complete |
| UX-02 | Phase 2 | Pending |
| UX-03 | Phase 2 | Pending |
| UX-04 | Phase 2 | Pending |
| UX-05 | Phase 2 | Pending |
| UX-06 | Phase 7 | Pending |
| UX-07 | Phase 3 | Complete |
| UX-08 | Phase 0 | Pending |
| UX-09 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 80 total (CORE 7 + INT 6 + MEM 7 + TEAM 6 + SPRINT 6 + SKILL 19 + SAFETY 5 + QUALITY 15 + UX 9)
- Mapped to phases: 80
- Unmapped: 0

**Per-phase counts:**
- Phase 0: 5 (CORE-03, TEAM-06, QUALITY-14, QUALITY-15, UX-08)
- Phase 1: 5 (CORE-01, CORE-02, CORE-04, INT-01, INT-02)
- Phase 2: 21 (CORE-05, CORE-07, INT-06, SPRINT-01/02, SKILL-09, SAFETY-01..04, QUALITY-01/02/03/06/08/11, UX-02/03/04/05/09)
- Phase 3: 16 (TEAM-01..05, SKILL-01..08, SPRINT-06, UX-01, UX-07)
- Phase 4: 7 (SPRINT-03/04/05, SAFETY-05, QUALITY-07/09/13)
- Phase 5: 7 (SKILL-13..19)
- Phase 6: 11 (MEM-01..07, SKILL-10..12, QUALITY-10)
- Phase 7: 8 (CORE-06, INT-03..05, QUALITY-04/05/12, UX-06)

---
*Requirements defined: 2026-04-15*
*Last updated: 2026-04-15 after roadmap traceability finalization (8 phases, fine granularity)*
