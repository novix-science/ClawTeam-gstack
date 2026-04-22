# ClawTeam-gstack

## What This Is

A fork of ClawTeam that integrates [gstack](https://github.com/garrytan/gstack) — Garry Tan's 30+ slash-command toolkit that turns Claude Code into a virtual engineering team — into ClawTeam's multi-agent harness as a first-class team template and sprint model. The product narrative: **one command spawns your own persistent 11-specialist team** (pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre) that runs gstack's Think → Plan → Build → Review → Test → Ship → Reflect sprint loop with file-backed state, phase gates, and artifacts. A single team can run multiple sprints in parallel, learning your codebase and taste over time.

## Core Value

**You hire a virtual engineering team, and over time they get better at working with you.** The team is the unit the user feels; sprints are the work the team takes on. If everything else ships and the team doesn't feel like a coordinated set of specialists with memory and opinions, the product has failed.

## Requirements

### Validated

<!-- Inferred from existing ClawTeam codebase (.planning/codebase/*.md). -->

- ✓ Typer CLI `clawteam` + `clawteam-mcp` server exposing domain ops as MCP tools — existing
- ✓ Harness orchestrator with `PhaseState`, `PhaseRunner`, `PhaseGate` machinery (artifact/approval/all-tasks gates) — existing
- ✓ Spawn backend registry: tmux / subprocess / wsh; per-CLI adapter with `PreparedCommand` normalization — existing
- ✓ Spawn support for 9 external AI CLIs (Claude, Codex, Gemini, Kimi, Qwen, OpenCode, OpenClaw, Nanobot, pi) — existing
- ✓ Per-team git worktree workspace manager with checkpoint/merge/conflict handling — existing
- ✓ File-backed transport + optional ZeroMQ transport; per-agent mailboxes + routing policy — existing
- ✓ Sync `EventBus` with priority subscriptions + async pool; plugin extension (`HarnessPlugin.contribute_gates` / `contribute_prompts`) — existing
- ✓ Team templates (TOML): software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room — existing
- ✓ File-locked atomic JSON/TOML persistence under `~/.clawteam/` (or `$CLAWTEAM_DATA_DIR`) — existing
- ✓ Docker/nanobot runtime bundling; keepalive recovery; identity propagation with `CLAWTEAM_* / OH_* / CLAUDE_CODE_*` multi-generation envs — existing
- ✓ `SprintConductor` + `clawteam sprint` CLI sub-app (start/status/show/list/pause/resume with `--json`); pause/resume survives process restart — Phase 2
- ✓ `EvidenceGate` 4-check protocol + `EvidenceSchemaRegistry` (plugin-populated pydantic schemas dispatched by `artifact_type`) — Phase 2
- ✓ `FreezeRegistry` + `/careful`, `/freeze`, `/guard`, `/unfreeze` safety-rail primitives wired via EventBus `BeforeToolCall` / `BeforeFileWrite` subscribers — Phase 2
- ✓ Transport-level cycle detector + `TurnEnvelope` structured-response protocol + `forced_progress_gate` (theater/no-progress detector) + artifact size caps (50 KB/file, 500 KB/phase) — Phase 2
- ✓ Phase 0 BC regression matrix (12/12 green) — Phase 2 primitives are opt-in; existing templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) unchanged

### Validated (v1.0 shipped 2026-04-22)

<!-- All v1 requirements delivered in milestone v1.0. See .planning/milestones/v1.0-REQUIREMENTS.md for full traceability. -->

**Team & agent roster:**
- ✓ 11-agent persistent team template `gstack.toml` — v1.0 Phase 3 (TEAM-01..05, SKILL-01..08)
- ✓ Long-lived agents across sprints with per-agent worktree desks + per-role memory — v1.0 Phase 3
- ✓ Team-shared `/learn` memory under `~/.clawteam/teams/<team>/memory/` with provenance + decay + human-gate — v1.0 Phase 6 (MEM-01..07)

**Sprint model:**
- ✓ 7-phase sprint state machine (Think → Plan → Build → Review → Test → Ship → Reflect) — v1.0 Phase 2+3
- ✓ `PhaseRegistry` + `SprintConductor` + `EvidenceGate` + `EvidenceSchemaRegistry` — v1.0 Phase 1+2
- ✓ `GstackSprintPlugin` wires 7 phases + per-phase evidence gates — v1.0 Phase 3 (SPRINT-06)
- ✓ Auto-advance with `--no-auto-advance` toggle for human approval per transition — v1.0 Phase 2
- ✓ Concurrent sprint support via `SprintConductor` 3-semaphore caps (10 sprints × 1 per-agent × 6 active) — v1.0 Phase 7 (CORE-06)

**Smart review routing + cross-agent verification:**
- ✓ `SmartReviewRouter` with SHA-pinned CODEOWNERS-style routing — v1.0 Phase 4 (SPRINT-03)
- ✓ Parallel reviewer decorrelation + sycophancy cascade detector + `CrossAgentVerificationGate` — v1.0 Phase 4 (SPRINT-04, QUALITY-07/09/13)
- ✓ Ship-phase human-approval gate ignoring `auto_advance` — v1.0 Phase 4 (SPRINT-05, SAFETY-05)

**Gstack skill port:**
- ✓ Methodology/rubrics baked into role prompts for 11 roles — v1.0 Phase 3
- ✓ Tool-heavy skills: `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy`, `/codex` — v1.0 Phase 5 (SKILL-13..19)
- ✓ Browser + design skills: `/browse`, `/open-gstack-browser`, `/setup-browser-cookies`, `/design-shotgun`, `/design-html` — v1.0 Phase 6 (SKILL-10..12)
- ✓ Safety-rail primitives: `/careful`, `/freeze`, `/guard`, `/unfreeze` — v1.0 Phase 2 (SAFETY-01..04)
- ✓ Interactive state-machine skills: `/office-hours`, `/design-consultation`, `/investigate` — v1.0 Phase 4

**Human interaction:**
- ✓ `InteractionGate` — v1.0 Phase 1 (INT-02)
- ✓ `AttentionQueue` + `clawteam attend` priority queue with `--summary` digest + `--auto-accept-reversible` + `pick` → `$EDITOR` — v1.0 Phase 7 (INT-03, INT-04)
- ✓ Per-sprint question/answer artifacts round-tripping through file-locked store — v1.0 Phase 7 (INT-05)

**Launch UX:**
- ✓ `clawteam team spawn gstack --name <team>` — v1.0 Phase 3 (UX-01)
- ✓ `clawteam sprint start / status / show / list / pause / resume` — v1.0 Phase 2 (UX-02..05, UX-09)
- ✓ `clawteam attend` / `clawteam attend pick` / `clawteam attend --summary` — v1.0 Phase 7 (UX-06)
- ✓ `clawteam team show <name>` with cost + memory + sprint panels — v1.0 Phase 3+7

**Observability + cost controls:**
- ✓ Rate-limit-aware scheduling with `RateLimitMonitor` 60s 429-window — v1.0 Phase 7 (QUALITY-04)
- ✓ Zombie worktree GC via `doctor --gc` with 5/10 GB disk budget — v1.0 Phase 7 (CORE-06)
- ⚠ Cost + cache observability — infrastructure + UI shipped, emit-path gap deferred to v1.x backlog 999.001 (QUALITY-12 partial)

### Active (v1.x candidates)

<!-- v1.x scope: fix observability emit-path gaps + UX polish from v1.0 UAT walkthrough. See .planning/backlog/ for detail. -->

**Observability emit-path wiring (critical, unblocks QUALITY-12):**
- [ ] 999.001 — Wire `ClaudeApiResponse` + `ToolCallCompleted` emit path from `claude` CLI stream-json output through `TmuxBackend` / `invoke_native_cli` to the event bus. Unblocks real cost + cache metrics in `clawteam team show`.

**attend CLI UX polish (surfaced in v1.0 UAT walkthrough):**
- [ ] 999.002 — `attend` "Urg" column currently shows `norm` for all questions regardless of frontmatter `urgency:` — map numeric values or display raw.
- [ ] 999.003 — `attend --summary` "Representative title" shows qid instead of first-H1-from-body — digest UX value depends on this.
- [ ] 999.004 — Sprint `state.json::pending_question_ids` not synced until `AttentionWatcher` runs — either auto-start watcher on `sprint start` or do one-shot reconciliation on `sprint status`.

**Real-environment dogfood (requires live API + tmux sessions):**
- [ ] Real 10-sprint 5-minute / 4 GB RAM load (ROADMAP SC #1)
- [ ] Live Anthropic 429 rate-limit handling + pause/resume (SC #9)
- [ ] >50% prompt-cache hit rate steady-state (SC #8 — depends on 999.001)
- [ ] Digest-mode UX quality at 20+ question scale (subjective)
- [ ] `attend → $EDITOR → answer → gate unblock` E2E round-trip with real `claude` agent in tmux

### Out of Scope

- **Multi-team Conductor UI** — reserved for v2. v1 supports spawning multiple teams via existing `clawteam team spawn`, but no cross-team dashboard. Reason: single-team story is already the product hook; multi-team complexity dilutes v1.
- **Quick-sprint heuristic** (auto-skipping phases for trivial changes) — v2. Reason: the 7-phase discipline is what makes the team narrative coherent; shortcuts risk reverting to "just a claude agent."
- **Pool/shared specialist profile** (sharing one designer across many teams) — v2. Reason: breaks the "my team" narrative.
- **Porting gstack's analytics dashboard** (gstack-analytics) — v2. Reason: ClawTeam's board can host sprint views; don't need parallel infra in v1.
- **Breaking compatibility with existing ClawTeam templates** (software-dev, hedge-fund, etc.) — explicitly excluded. Reason: gstack template ships alongside, not instead of, existing templates. Harness extensions are additive via `PhaseRegistry` not modifications to core `PhaseState`.
- **Auto-installing external tools** (Chromium for /browse, ngrok for /pair-agent, Codex CLI for /codex) — skills detect availability and fail gracefully. Reason: tool auto-install is a support nightmare; skills flag missing deps with clear setup instructions instead.
- **Porting gstack upstream to Garry Tan's repo** — not our call; this fork is ClawTeam-side integration. Reason: gstack is its own project.

## Context

**Upstream relationships:**
- **ClawTeam** (parent fork) — the multi-agent harness we're extending. Our gstack integration is built to be upstream-friendly: core primitives (Sprint, InteractionGate, AttentionQueue, PhaseRegistry) are generic; gstack-specific behavior lives in `GstackSprintPlugin` + `gstack.toml`. Intent: land the extensions upstream eventually so other templates (hedge-fund, research-paper) can adopt sprint-style workflows too.
- **gstack** (https://github.com/garrytan/gstack) — Garry Tan's Claude Code skill pack. We port the methodology (not the skill files), respecting the sprint structure (Think → Plan → Build → Review → Test → Ship → Reflect) and role mapping from the README.

**Why a team instead of one claude with slash commands:**
gstack native is "one Claude Code session + 30 slash commands." Powerful but single-threaded in personality — the same agent plays CEO, then engineer, then QA, then reviewer. Users we're targeting want "my team of specialists" — discrete personas with persistent memory, who learn your codebase and taste over sprints. Agent-team is the more attractive narrative for users and newcomers (the user's explicit product judgment), and it's the reason for bringing ClawTeam into the gstack world at all.

**Parallel sprints as force multiplier:**
gstack's author runs 10-15 parallel sprints (one Claude Code session each). Our equivalent: one team handling multiple sprint branches simultaneously. Team juggles work the way a real startup eng team does. `AttentionQueue` is how one human stays in the loop across N concurrent sprints.

**Key codebase assets we reuse:**
- `HarnessPlugin.contribute_gates / contribute_prompts` — the extension point for registering sprint phases + role prompts without core changes.
- `WorkspaceManager` (per-agent/per-sprint git worktrees) — already matches the "persistent desk + per-sprint branch" model.
- `file_locked()` atomic JSON persistence — used by `/learn` memory, sprint state, attention queue.
- Existing templates (`software-dev.toml`, `hedge-fund.toml`) — shape for `gstack.toml`.
- `NativeCliAdapter` multi-CLI support — engineer/reviewer can invoke `/codex` (external Codex CLI) through the same spawn infra used for the rest of the team.

## Constraints

- **Tech stack**: Python 3.10+ (existing ClawTeam minimum) — no bump in v1. Reason: spawn machinery, pydantic models, existing tests all assume 3.10. Any newer feature needed gets wrapped in compat.
- **Backwards compatibility**: Existing templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) must continue to work unchanged. Reason: ClawTeam's user base already depends on them; our fork is additive.
- **Upstream compatibility**: Harness-core changes ship as extensions (new classes, new plugin hooks), not edits to existing `PhaseState` or `HarnessOrchestrator` semantics. Reason: we intend to PR back; intrusive changes delay or block that.
- **Dependencies**: No new required runtime deps for core harness extensions. Optional deps (Chromium for /browse, ngrok for /pair-agent, codex CLI for /codex) gated by feature detection. Reason: keep `pip install` footprint minimal; gstack's own philosophy is zero-deps per skill output.
- **Persistence location**: All team/sprint state under `get_data_dir()` (default `~/.clawteam/`), never in-project. Reason: matches existing storage convention; avoids polluting user repos; `CLAWTEAM_DATA_DIR` already overrides.
- **Identity envs**: Preserve `CLAWTEAM_* / OH_* / CLAUDE_CODE_*` multi-generation aliases. Reason: existing agents running under older env naming keep working.
- **Process footprint**: A single "full team" sprint = 11 long-running CLI processes (one per agent). Budget: each agent should be idle-cheap (sleep-polling task queue) so 11 concurrent agents don't dominate a laptop. Reason: the narrative dies if users' machines melt.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 11-agent persistent team roster (pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre) | "You get a team of specialists" is the product narrative; persona split is more attractive to users than "1 Claude with superpowers" | — Pending |
| Split pm (YC Office Hours advisor) from ceo (scope owner + leader) | Two genuinely different personas in gstack — external coach vs internal decider; productive tension between them | — Pending |
| Team is persistent, sprint is transient work unit; single team runs multiple parallel sprints | Matches real engineering-team mental model; agents' per-role memory compounds across sprints | — Pending |
| Port gstack skills by nature (methodology → baked into prompts; tool-heavy → new ClawTeam skills; safety rails → harness primitives) | No runtime dependency on gstack being installed; prompts stay focused on methodology; tool-heavy logic reused across agents | — Pending |
| Extend `PhaseState` via a new `PhaseRegistry` plugin API (not hardcoded enum additions) | Upstream-friendly; lets other templates adopt sprint-style workflows; respects existing plugin extension pattern | — Pending |
| Review phase: parallel execution of 4 reviewer personas + reviewer aggregates | Fast fan-out matches swarm pattern; staff-eng is the natural cross-cutting synthesizer; keeps ceo focused on scope/phase-transition calls | — Pending |
| Helper workspaces: per-helper sub-worktree merged back by engineer | Aligns with existing `WorkspaceManager` + `workspace.merge` patterns; clean isolation and conflict detection | — Pending |
| Fork strategy: build upstream-compatible, land eventually | The swarm-harness is a reusable substrate; keeping it generic serves future templates, not just gstack | — Pending |
| Human interaction via `InteractionGate` + cross-sprint `AttentionQueue` | Scales from 1 sprint (feels like pair-programming) to 10 parallel sprints (feels like triaging a ticket queue) with one mental model | — Pending |
| `EvidenceGate` as subclass (not replacement) of `ArtifactRequiredGate` | Existing 6 templates keep their gate semantics unchanged; gstack opts into the 4-check protocol via plugin | ✓ Shipped Phase 2 |
| `FreezeRegistry` mirrors `PhaseRegistry` shape (module-level singleton + append-only JSONL audit) | Consistency over abstraction; same reset/isolation pattern works for tests | ✓ Shipped Phase 2 |
| `TurnEnvelope` as one pydantic model + two serialization surfaces (stdlib YAML frontmatter parser + JSON) | Integrity boundary at `Transport.deliver()`; `yaml.safe_load` only; `TeamMessage` envelope fields optional for BC with 15+ existing construction sites | ✓ Shipped Phase 2 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state (users, feedback, metrics)

---
*Last updated: 2026-04-22 after v1.0 milestone (8 phases, 78 plans, 80 REQs delivered, ~70.7k LOC; emit-path gap QUALITY-12 deferred to v1.x backlog 999.001).*
