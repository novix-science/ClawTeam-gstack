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

### Active

<!-- v1 scope: the gstack-as-team milestone. Hypotheses until shipped. -->

**Team & agent roster:**
- [ ] 11-agent persistent team template `gstack.toml` with roles: pm (YC office-hours advisor), ceo (scope owner + team leader), eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre
- [ ] Agents are long-lived: one `team spawn` = hire; agents persist across multiple sprints; each has own worktree "desk" + per-role memory
- [ ] Team-shared `/learn` memory under `~/.clawteam/teams/<team>/memory/` accumulated across sprints

**Sprint model:**
- [ ] First-class 7-phase sprint state machine: Think → Plan → Build → Review → Test → Ship → Reflect
- [ ] `PhaseRegistry` extension API — new phases registered as plugins, not hardcoded into core `PhaseState` enum (upstream-compatible)
- [ ] `GstackSprintPlugin` registers 7 phases + per-phase `ArtifactRequiredGate`s (design-doc, plan-doc, diff, review-report, test-report, ship-notes, retro)
- [ ] Auto-advance between phases by default; toggleable via config to require human approval per transition
- [ ] One team can run multiple sprints concurrently; team members juggle sprint assignments like a real team handles multiple PRs

**Smart review routing:**
- [ ] Review-phase participant selection driven by diff content: UI touched → designer joins; public API → dx-lead joins; auth/crypto → security joins
- [ ] Parallel reviewer execution during Review phase; `reviewer` (staff eng) synthesizes to a single aggregated review report

**Gstack skill port (full port, no runtime dependency on gstack installation):**
- [ ] Methodology/rubrics baked into role prompts: /office-hours (pm), /plan-ceo-review (ceo), /plan-eng-review + /retro (eng-mgr), /plan-design-review + /design-review + /design-consultation (designer), /plan-devex-review + /devex-review (dx-lead), /review + /investigate (reviewer), /qa + /qa-only (qa), /cso (security)
- [ ] Tool-heavy skills ported as ClawTeam skills owned by specific agents: /browse + /pair-agent + /open-gstack-browser + /setup-browser-cookies (engineer/qa/dx-lead), /design-shotgun + /design-html (designer), /codex (engineer/reviewer), /ship + /land-and-deploy + /document-release (shipper), /canary + /benchmark + /setup-deploy (sre), /learn (team-shared)
- [ ] Team-level safety rails as harness primitives: /careful (destructive-command warnings), /freeze (edit-lock to a path), /guard (both), /unfreeze, /autoplan (= the sprint phase transitions themselves)

**Human interaction:**
- [ ] `InteractionGate` — new `PhaseGate` subclass that blocks until a human answers questions written by phase agents
- [ ] `AttentionQueue` — cross-sprint pending-questions view; `clawteam attend` surfaces questions from any sprint, priority-sorted
- [ ] Per-sprint question artifacts: `sprint/<id>/questions/<N>.md` + `answers/<N>.md` round-tripping through existing file-locked store

**Launch UX:**
- [ ] `clawteam team spawn gstack --name <team-name>` — one-time hire
- [ ] `clawteam sprint start --team <name> --goal "..."` — dispatch work
- [ ] `clawteam sprint status / show / list` — per-team sprint visibility
- [ ] `clawteam attend` — human attention loop (answer pending questions)
- [ ] `clawteam team show <name>` — team dashboard (agents, active sprints, memory highlights)

**Workspace strategy:**
- [ ] Each of 11 agents: persistent worktree (agent's "desk") reused across sprints
- [ ] Each sprint: dedicated branch/worktree; engineer forks ephemeral helper agents with their own sub-worktrees, merged back via existing `WorkspaceManager.merge`

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
*Last updated: 2026-04-15 after initialization*
