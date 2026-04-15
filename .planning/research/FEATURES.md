# Feature Research

**Domain:** Persistent AI specialist team + parallel-sprint coordination harness (ClawTeam-gstack)
**Researched:** 2026-04-15
**Confidence:** MEDIUM — grounded in production systems (Factory Droid, Conductor, Claude Code agent-team, AutoGen, LangGraph, CrewAI, gstack native) and direct ARCHITECTURE/PITFALLS research, but market-expectation signals are inferred from product docs rather than user studies.

> **Scope note:** This document focuses on the NEW gstack-integration milestone. Baseline ClawTeam capabilities (spawn, mailbox, workspace, board, templates) are treated as existing infrastructure — not re-analyzed. Refer to `.planning/codebase/*.md` for the existing feature surface.

## Product Positioning

**Category:** "Virtual engineering team" — the user narrative is "you hire 11 specialists who persist, learn your codebase, and run sprints for you."

**Adjacent categories & reference products:**
- **Multi-agent team frameworks**: CrewAI, AutoGen, AgentScope, LangGraph Agents, OpenAI Swarm. Mostly SDK-first; team is constructed in code per run.
- **AI coding droids**: Factory AI (Droid roles: CodeDroid, ReviewDroid, QADroid), Cognition Devin. Role-specialized, but one-droid-per-task, not a persistent team.
- **Parallel session orchestrators**: Conductor, code-conductor, Claude Code Tasks. Run N sessions in parallel, each in an isolated worktree; no persistent roster.
- **Slash-command toolkits**: gstack (our upstream), Claude Code Skills registry, various "agents" dotfiles repos. Single-session mega-tools without a team abstraction.

**Our position:** the only product that combines all three — **persistent opinionated team + parallel sprints + gstack methodology baked in**. "Your startup's engineering team, on your laptop, remembering what you care about across weeks of sprints."

## Feature Landscape

### Table Stakes (Users Expect These)

Features missing from v1 make the product feel incomplete for the target persona (solo founder / small-team builder familiar with gstack).

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Persistent per-agent identity across sessions | CrewAI/AutoGen/Claude Code-Team all have it; without it, "team" is a lie | MEDIUM | Agent state under `~/.clawteam/teams/<team>/agents/<role>/` — prompt pack, memory pointer, worktree path |
| Sprint lifecycle visibility (status, current phase, active participants) | Conductor's dashboard, Factory session view — users need to see what the team is doing | MEDIUM | `clawteam sprint status <id>` + `clawteam team show <name>` CLIs — reuse existing board collector |
| Pause / resume a running sprint | Microsoft AutoGen PR #5887, LangGraph `interrupt()`, Google ADK resume — all acknowledge this is the #1 user request for long-running agent teams | MEDIUM | Write sprint state checkpoints at phase boundaries + on explicit `clawteam sprint pause` |
| Human-in-loop question/answer channel | gstack's whole "taste decisions surface for approval" depends on this — users expect to steer their team | MEDIUM | InteractionGate + AttentionQueue — already in scope per PROJECT.md |
| Git-worktree per sprint isolation | Conductor, code-conductor, Factory — the category-standard isolation model | LOW | Reuse existing WorkspaceManager; just add sprint-scoped branches |
| Per-agent + team-shared memory (/learn) | Claude Code skills, mem0, Letta — memory is what makes the narrative "team learns your codebase" real | MEDIUM | Layered store per ARCHITECTURE.md (per-agent + team-shared, grep-first v1) |
| Skill invocation per role | gstack's slash commands; users expect "the designer can /design-shotgun on demand" | MEDIUM | ClawTeam skills registered to specific agent roles — already in scope |
| Multi-sprint parallel execution on one team | gstack's whole value proposition ("10-15 parallel sprints"); Conductor's selling point | HIGH | Team-wide task store + per-sprint labels + agent idle-pull workers |
| Phase artifacts (design doc, plan doc, review report, etc.) | Gstack's pipeline relies on downstream skills reading upstream artifacts | LOW | Reuse existing `ArtifactStore` |
| Team dashboard / "where's my attention needed" view | Linear Inbox, GitHub Notifications, Intercom — the table-stakes UX for any multi-stream work | MEDIUM | `clawteam attend` (CLI v1) → extend board UI (v2) |
| Graceful degradation when optional tools missing (Chromium, codex CLI, ngrok) | Pip install shouldn't auto-pull 500MB Chromium; users expect feature detection | LOW | Import-guard + helpful error messages + `clawteam doctor` check |
| Cross-session continuation of agent context | Anthropic Claude-Code Issue #26265 (top-voted agent-team feature request) — users hit context limits in long engagements | MEDIUM | Agent prompts rebuild from persistent memory + minimal working set |

### Differentiators (Competitive Advantage)

Features where we win versus the adjacent category.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **11-role persona team, pre-configured** | CrewAI/AutoGen require you to define roles; Factory's Droids are single-task. We ship an opinionated full team (pm YC-advisor + ceo + eng-mgr + designer + dx-lead + engineer + reviewer + qa + security + shipper + sre) that comes with gstack methodology baked in | HIGH | gstack.toml template + per-role prompts ported from gstack skills |
| **7-phase sprint as product, not just pipeline** | Think→Plan→Build→Review→Test→Ship→Reflect with structured artifacts at each phase — stronger guardrails than Conductor's "just run more sessions" approach | MEDIUM | PhaseRegistry + GstackSprintPlugin |
| **Smart review routing (diff-aware)** | Users get "the right reviewers" automatically — CodeRabbit does this at PR level; we do it at sprint-phase level with persona-aware selection (UI touched → designer; crypto touched → security) | MEDIUM | SmartReviewRouter (rules-first per ARCHITECTURE.md); CODEOWNERS-style config in gstack.toml |
| **Cross-sprint AttentionQueue priority scoring** | "10 sprints, 1 human" → triage by blocking/SLA/urgency, Linear Inbox-style. Unique to us; Conductor has a dashboard but no prioritization | MEDIUM | AttentionQueue with weighted scoring (URGENCY + BLOCKING + AGE + TAG) |
| **Designer's shotgun→HTML pipeline as team workflow** | gstack's flagship visual iteration (mockup variants → pick → HTML) run by a persistent designer agent who learns taste across sprints | HIGH | Port /design-shotgun + /design-html as ClawTeam skills owned by `designer` role; taste memory as designer's per-agent /learn |
| **Cross-model second opinion (/codex built-in)** | engineer and reviewer can both invoke /codex for independent OpenAI review; rare in team products | LOW | Reuse NativeCliAdapter's Codex support; port /codex as clawteam skill |
| **Pair-agent browser coordination** | Cross-vendor AI agent coordination through shared Chromium — gstack invented this; we inherit it for cross-team debugging | HIGH | Port /pair-agent; optional ngrok tunnel detection |
| **Memory compounding across sprints** | Every sprint's retro + /learn updates make the team smarter on _your_ codebase. mem0/Letta-style but team-scoped, narrative-aligned | MEDIUM | Layered memory with provenance + decay (per PITFALLS research on memory poisoning) |
| **Auto-upstream-PR-friendly architecture** | Harness extensions are generic plugins; future templates (hedge-fund, research-paper) can adopt sprint style. Unique value proposition to the ClawTeam ecosystem | MEDIUM | PhaseRegistry as core primitive; gstack-specific logic confined to plugin |
| **Helper-on-demand for engineer** | engineer forks ephemeral helpers for parallel sub-tasks (per user preference). Matches the "team grows to fit the work" vibe without static agent scaling | HIGH | Reuse WorkspaceManager for helper sub-worktrees; merge back via existing conflict handler |
| **100% test coverage discipline (inherited from gstack)** | /ship bootstraps test frameworks; /qa auto-generates regression tests. Rare in agent-team products | MEDIUM | Inherit via shipper + qa role prompts |
| **Safety-rail primitives (/careful /freeze /guard)** | Gstack's safety commands ported as _team-level_ harness features, not per-agent — means every agent respects /freeze boundaries | MEDIUM | EventBus hook on file-write tool calls; workspace-manager enforces /freeze paths |

### Anti-Features (Commonly Requested, Often Problematic)

Features that sound exciting but dilute the product, cause UX fatigue, or create architectural debt.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full auto-pilot "complete sprint without asking" mode | "I want to just hit run and get a PR" | Removes the taste-decision surface that makes gstack valuable. Research (PITFALLS) shows this is how "multi-agent theater" emerges — agents pass messages to look productive | Auto-advance per phase if InteractionGate not triggered; still surface _required_ decisions through AttentionQueue |
| Dynamic agent creation ("spawn a new specialist mid-sprint") | "My team should be smart enough to hire as needed" | Violates "11-persona team" narrative; introduces unstable identity; new agents have no memory | engineer's ephemeral helpers are the sanctioned pattern; no new permanent personas |
| Per-agent custom LLM picking ("use gpt-5 for the designer") | "I want best-of-breed per role" | Multiplies auth/cost/reliability surface × 11; splinters memory-store compatibility; Claude-Code-native skills won't work with non-Claude agents | v1: single LLM choice per team via model_profile; v2: evaluate only if users actually hit quality ceilings |
| In-sprint agent voting / consensus ("ceo and eng-mgr vote on plan") | "Democracy feels fair" | Pitfall #2 (deadlock): pm asks ceo, ceo asks pm. MAST study shows 36.9% of multi-agent failures are inter-agent misalignment | Strict DAG: pm produces questions → ceo answers with decisions → plan committed. No voting loops. |
| Real-time agent chat UI (watch them talk live) | "It looks cool" | Encourages chatty agents (token burn + persona drift); "theater" failure mode from PITFALLS | Board summarizes actions; full conversation available in artifacts/transcripts but not the primary view |
| "Replay this sprint with different parameters" | "A/B test the team" | Would require deep determinism + state recording; 10x implementation cost for a marginal feature | v1: sprints are one-shot; v2: if users request, implement via artifact export + replay template |
| Custom slash-command creation from inside the team | "I want my own /my-thing" | Dilutes the 11-role specialization; creates a maintenance nightmare for `/learn` classification; gstack's explicit design is curated skills | Accept PRs to add official skills; never per-team customization |
| Always-on multi-team Conductor UI | "Show me 5 teams on one screen" | v2 scope; diffuses focus; single-team is already the product hook per PROJECT.md | v1 supports spawning multiple teams via existing CLI; no cross-team UI |
| Unified agent identity across teams | "My designer from team A should know what they learned in team B" | Breaks team isolation; creates multi-tenant memory-poisoning risks (per PITFALLS memory poisoning findings) | Export / import memory is explicit action, never automatic |
| "Cheap mode" that auto-downgrades models | "Save tokens when the task is simple" | Heuristic model-switching has low recall; users hate when the designer makes a bad call because it got Haiku-ed | Single model_profile per team; user toggles explicitly if needed |
| Skill auto-install ("need Chromium? I'll grab it") | "Magical UX" | Breaks containerized / CI setups; hides what's happening; support nightmare per PROJECT.md constraints | `clawteam doctor` detects missing tools, prints install commands |
| Auto-PR-merge on green ("trust the team, merge") | "True autonomy" | Production blast radius. Ship-gate should always require human approval per PITFALLS #8 (gate gaming) | /land-and-deploy creates PR + runs CI, but human clicks merge |

## Feature Dependencies

```
┌─ PhaseRegistry ──┐
│                  │
│   ┌─ SprintState ──────┐
│   │                    │
│   │   ┌─ GstackPlugin ─────────────┐
│   │   │                             │
│   │   │   ┌─ 11-agent team template ────┐
│   │   │   │                              │
│   │   │   │   ┌─ Role prompts ───────┐   │
│   │   │   │   │   (methodology port) │   │
│   │   │   │   └──────────────────────┘   │
│   │   │   │                              │
│   │   │   │   ┌─ ClawTeam skills ────┐   │
│   │   │   │   │  (/browse /design-   │   │
│   │   │   │   │   shotgun /ship ...) │   │
│   │   │   │   └──────────────────────┘   │
│   │   │   │                              │
│   │   │   └──────────────────────────────┘
│   │   │
│   │   │   ┌─ SmartReviewRouter ────┐
│   │   │   │                        │
│   │   │   └─ SprintConductor ─────┤
│   │   └────────────────────────────┘
│   │
│   ├─ InteractionGate ──────────────┐
│   │                                 │
│   │   └─ AttentionQueue ───────────┤
│   │       └─ `clawteam attend` CLI │
│   │
│   └─ TeamMemoryStore ──────────────┤
│       └─ /learn skill              │
│
└─ HelperSpawner ─────────────────────┘
    (uses existing WorkspaceManager)
```

### Dependency Notes

- **GstackSprintPlugin requires PhaseRegistry + SprintState:** plugin registers phases + gates; without registry, cannot extend PhaseState cleanly.
- **11-agent team template requires GstackSprintPlugin:** the `gstack.toml` template leans on the plugin to know what phases exist.
- **InteractionGate requires PhaseRegistry:** gates hook into phase transitions.
- **AttentionQueue requires InteractionGate:** AttentionQueue aggregates questions produced by gates.
- **`clawteam attend` requires AttentionQueue:** CLI is a thin face over the queue.
- **TeamMemoryStore is independent:** can ship ahead of sprint machinery; other templates can use it too.
- **SmartReviewRouter depends on SprintConductor + TeamMemoryStore:** routing pulls historical success signals from memory.
- **HelperSpawner depends on SprintState (for sprint-scoped worktrees):** helpers attach to a sprint's branch.
- **Skill ports (Chromium, /design-shotgun, etc.) are independent of sprint plumbing:** they can land as standalone skill additions before the sprint plugin is complete. This is a useful parallelization of work.

## MVP Definition

### Launch With (v1) — the minimum that tells the product story

Must answer the user-facing question: _"I spawned a team and ran a sprint — did the team feel real?"_

**Core infrastructure (enabling):**
- [ ] `PhaseRegistry` — plugin API for sprint phases (no core enum changes) — _without this, every downstream extension is brittle_
- [ ] `SprintState` + `SprintConductor` — one team can own 1+ sprints each with its own phase state machine — _this is the new data model_
- [ ] `InteractionGate` — markdown Q/A round-trip for human input — _preserves gstack's taste-decision essence_
- [ ] `AttentionQueue` — cross-sprint priority-sorted pending questions — _scales human attention across parallel sprints_
- [ ] `TeamMemoryStore` — layered per-agent + team-shared memory, grep-first — _narrative: "team learns your codebase"_

**Gstack integration (product surface):**
- [ ] 11-agent team template `gstack.toml` (pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre) — _the team is the product_
- [ ] `GstackSprintPlugin` — registers 7 phases + `ArtifactRequiredGate`s + role prompt contributions — _the sprint is the product_
- [ ] Methodology port (baked into role prompts): /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review, /plan-devex-review, /retro, /design-consultation, /design-review, /devex-review, /review, /investigate, /qa, /qa-only, /cso — _without these, roles are empty shells_
- [ ] `SmartReviewRouter` (CODEOWNERS-style rules from gstack.toml) — _without routing, Review phase is all 4 reviewers on every sprint, which is slow and wasteful_

**Tool-heavy skills (enabling key features):**
- [ ] /browse + /open-gstack-browser + /setup-browser-cookies (`clawteam[browser]` optional extra) — _required for qa real-browser testing and dx-lead's devex audit_
- [ ] /design-shotgun + /design-html — _the flagship visual iteration loop_
- [ ] /codex — _cross-model second opinion_
- [ ] /ship + /land-and-deploy + /document-release — _the whole Ship phase depends on these_
- [ ] /canary + /benchmark + /setup-deploy — _without these, SRE role has nothing to do_
- [ ] /learn — _team-shared memory interface_

**Safety rails (harness primitives):**
- [ ] /careful + /freeze + /guard + /unfreeze — _ported as EventBus hooks; every agent respects them_

**UX:**
- [ ] `clawteam team spawn gstack --name <name>` — hire the team
- [ ] `clawteam sprint start --team <name> --goal "..."` — dispatch a sprint
- [ ] `clawteam sprint status / show / list` — per-sprint visibility
- [ ] `clawteam attend` — cross-sprint attention loop
- [ ] `clawteam team show <name>` — team dashboard (agents, sprints, memory highlights)
- [ ] Pause/resume a sprint (`clawteam sprint pause <id>` / `resume <id>`) — _community-demonstrated table stake per AutoGen/LangGraph/ADK research_
- [ ] `clawteam doctor` — detect missing optional tools (Chromium, codex, ngrok); print install instructions

### Add After Validation (v1.x)

Features to add once the core loop is validated by real users running actual sprints.

- [ ] Helper spawning inside engineer (parallel sub-task worktrees, merged back) — _trigger: users report Build phase is serial bottleneck on large features_
- [ ] `/pair-agent` port — _trigger: users ask for cross-vendor browser coordination with external agents_
- [ ] Board UI sprint/attention panels — _trigger: CLI `attend` loop proves insufficient for users juggling 5+ sprints_
- [ ] Memory decay + human-gate on high-impact writes (per PITFALLS memory-poisoning prevention) — _trigger: first observed bad-pattern propagation_
- [ ] Embedding-based memory retrieval (sqlite-vec upgrade) — _trigger: grep-first TeamMemoryStore starts missing relevant patterns at scale_
- [ ] Template customization hooks (user overrides role prompts / skill assignments) — _trigger: users ask "my pm is too aggressive"_

### Future Consideration (v2+)

Deferred explicitly per PROJECT.md scope.

- [ ] Multi-team Conductor UI — _deferred: single-team story is the hook; multi-team dilutes_
- [ ] Quick-sprint heuristic (skip phases for trivial changes) — _deferred: 7-phase discipline is what makes the narrative coherent_
- [ ] Pool/shared specialist profile (one designer serving many teams) — _deferred: breaks "my team" narrative_
- [ ] gstack analytics dashboard port — _deferred: board can host sprint views instead_
- [ ] Upstream PR to ClawTeam mainline — _deferred until gstack integration is stable and extensions are battle-tested_

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| 11-agent team template `gstack.toml` | HIGH | HIGH | P1 |
| 7-phase sprint via GstackSprintPlugin | HIGH | MEDIUM | P1 |
| PhaseRegistry (enabling) | HIGH | LOW | P1 |
| InteractionGate + AttentionQueue | HIGH | MEDIUM | P1 |
| TeamMemoryStore (layered, grep-first) | HIGH | MEDIUM | P1 |
| SmartReviewRouter (CODEOWNERS-style) | HIGH | MEDIUM | P1 |
| Methodology prompts port (14 skills) | HIGH | MEDIUM | P1 |
| /design-shotgun + /design-html | HIGH | HIGH | P1 |
| /ship + /land-and-deploy + /document-release | HIGH | MEDIUM | P1 |
| /browse + Chromium infra | HIGH | MEDIUM | P1 |
| /qa browser testing | HIGH | MEDIUM | P1 |
| /cso security audit | MEDIUM | LOW | P1 |
| /codex cross-model second opinion | MEDIUM | LOW | P1 |
| /canary + /benchmark + /setup-deploy | MEDIUM | MEDIUM | P1 |
| /careful /freeze /guard safety rails | MEDIUM | LOW | P1 |
| /learn team memory interface | HIGH | MEDIUM | P1 |
| Sprint pause/resume | HIGH | MEDIUM | P1 |
| `clawteam attend` CLI | HIGH | LOW | P1 |
| `clawteam team show` dashboard | MEDIUM | LOW | P1 |
| `clawteam doctor` optional-tool check | MEDIUM | LOW | P1 |
| Helper spawning for engineer | HIGH | HIGH | P2 |
| /pair-agent cross-vendor browser | MEDIUM | HIGH | P2 |
| Board UI sprint/attention panels | MEDIUM | MEDIUM | P2 |
| Memory decay + high-impact human gate | MEDIUM | MEDIUM | P2 |
| Embedding-based memory (sqlite-vec) | MEDIUM | MEDIUM | P2 |
| Template customization hooks | MEDIUM | MEDIUM | P2 |
| Multi-team Conductor UI | LOW | HIGH | P3 |
| Quick-sprint heuristic | LOW | MEDIUM | P3 |
| Pool/shared specialist profile | LOW | HIGH | P3 |

## Competitor Feature Analysis

| Feature | CrewAI / AutoGen | Factory AI (Droid) | Conductor | Claude Code Agent-Team | gstack (native) | **Our Approach** |
|---------|------------------|---------------------|-----------|------------------------|-----------------|------------------|
| Persistent team across sessions | ❌ team constructed per run | ⚠️ sessions, not persistent team | ⚠️ per-worktree session, no team | ⚠️ teammates don't resume (Issue #26265) | ❌ slash commands are stateless | ✅ 11 agents persistent per team |
| Parallel tasks/sprints | ✅ SDK-level | ✅ "hundreds of Droids" | ✅ flagship feature | ⚠️ via Task tool, limited | ✅ 10-15 claimed | ✅ multi-sprint per team |
| Per-role specialization | ✅ defined in code | ✅ Droid roles | ❌ generic agents | ✅ 28 reviewer personas | ✅ 23 skill personas | ✅ 11 pre-built + gstack methodology |
| Git worktree isolation per task | ❌ | ⚠️ per session | ✅ flagship | ⚠️ via subagent tool | ⚠️ per session, no native worktree | ✅ per-sprint branch + per-agent desk |
| Human-in-loop during execution | ✅ LangGraph `interrupt()` | ⚠️ session-based | ⚠️ dashboard, no structured gate | ✅ AskUserQuestion per turn | ✅ per-skill interactive | ✅ InteractionGate + AttentionQueue |
| Cross-session attention queue | ❌ | ⚠️ session list | ⚠️ dashboard | ❌ per-session notifications | ❌ per-session | ✅ AttentionQueue with priority scoring |
| Structured sprint phase model | ❌ | ❌ ad-hoc | ❌ ad-hoc | ❌ ad-hoc | ✅ 7-phase (Think→Reflect) | ✅ adopted from gstack |
| Persistent team memory (shared) | ⚠️ mem0 add-on | ⚠️ session-scoped | ⚠️ file-based, ad-hoc | ⚠️ CLAUDE.md only | ✅ `/learn` skill | ✅ layered (team + per-agent) |
| Pause / resume sprint | ⚠️ AutoGen PR #5887 pending | ✅ session-level | ⚠️ stop/restart, no mid-sprint pause | ❌ Issue #12816 open | ❌ | ✅ v1: checkpoint + resume |
| Skill/tool registry per role | ✅ tools per agent | ✅ per Droid | ❌ generic | ✅ skill-to-agent binding | ✅ all skills available always | ✅ skill-to-role binding via template |
| Smart reviewer selection | ❌ | ❌ | ❌ | ⚠️ via Task tool patterns | ✅ "smart routing" (implementation unclear) | ✅ rule-based CODEOWNERS-style |
| Cross-model second opinion | ⚠️ ad-hoc | ❌ | ❌ | ⚠️ manual | ✅ /codex (Claude ↔ OpenAI) | ✅ ported via NativeCliAdapter |
| Sprint-shaped artifacts (design doc, test report) | ❌ | ⚠️ | ❌ | ❌ | ✅ implicit in sprint flow | ✅ formal ArtifactRequiredGate |
| Safety rails (prevent destructive actions) | ⚠️ per-tool | ⚠️ per-tool | ❌ | ⚠️ permission prompts | ✅ /careful /freeze /guard | ✅ harness-level via EventBus |
| Cross-agent browser coordination | ❌ | ❌ | ❌ | ❌ | ✅ /pair-agent | ⚠️ v2 (port /pair-agent) |

**Verdict:** Our differentiation is the _combination_ — no competitor has all of {persistent team, parallel sprints, structured phases, attention queue, gstack methodology, smart routing} together. Individual primitives exist in other products, but integration is our moat.

## Sources

- [gstack](https://github.com/garrytan/gstack) — upstream methodology and skill roster (README + skill files)
- [ClawTeam codebase](.planning/codebase/) — existing harness, spawn, workspace, mailbox, plugin system
- [Conductor](https://www.conductor.build/) + [Conductor review on The New Stack](https://thenewstack.io/a-hands-on-review-of-conductor-an-ai-parallel-runner-app/) — parallel-sprint-via-worktree product
- [Factory AI Droid guide](https://sidbharath.com/blog/factory-ai-guide/) — role-specialized agent architecture
- [Claude Code agent team review](https://claude.com/blog/code-review) — Anthropic's parallel-reviewer-agent architecture (28 personas, verification step)
- [Microsoft AutoGen pause/resume PR #5887](https://github.com/microsoft/autogen/pull/5887) — table-stakes evidence for pause/resume
- [Claude Code agent-team resume issue #26265](https://github.com/anthropics/claude-code/issues/26265) — table-stakes evidence for cross-session continuation
- [Google Gemini CLI pause/resume #12816](https://github.com/google-gemini/gemini-cli/issues/12816) — same, corroboration
- [Google ADK Resume docs](https://google.github.io/adk-docs/runtime/resume/) — production implementation of resume pattern
- [LangGraph durable-execution docs](https://docs.langchain.com/oss/python/langgraph/durable-execution) — interrupt/resume semantics reference
- [MAST Study — Why Do Multi-Agent LLM Systems Fail?](https://arxiv.org/abs/2503.13657) — anti-feature justifications (theater, consensus, deadlocks)
- [Code review routing by Claude Skill](https://github.com/win4r/agent-skills-code-review-router) — SmartReviewRouter precedent
- [mem0](https://mem0.ai) / [Letta searchable agent memory](https://eric-tramel.github.io/blog/2026-02-07-searchable-agent-memory/) — persistent-agent-memory reference

---

*Feature research for: ClawTeam-gstack persistent-team + parallel-sprint harness*
*Researched: 2026-04-15*
