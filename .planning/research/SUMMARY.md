# Project Research Summary

**Project:** ClawTeam-gstack — hire-your-team + parallel-sprint harness
**Domain:** Persistent multi-agent AI engineering team + gstack skill-pack integration into ClawTeam
**Researched:** 2026-04-15
**Confidence:** HIGH (codebase read firsthand; external patterns cross-checked against Context7-indexed docs, primary research papers, and production post-mortems)

## Executive Summary

ClawTeam-gstack integrates Garry Tan's gstack methodology into ClawTeam as a first-class **team template + sprint model**: one `clawteam team spawn gstack` hires 11 persistent specialists (pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre) who run parallel Think->Plan->Build->Review->Test->Ship->Reflect sprints with file-backed state, phase gates, and layered team memory. The product bet is that a **persistent opinionated team with gstack methodology baked in + cross-sprint attention queue** is strictly more attractive than gstack-native (one Claude + 30 slash commands) or the adjacent "parallel runner" category (Conductor, Factory Droids). No competitor has the combination — persistent team x parallel sprints x structured phases x AttentionQueue x smart routing x team memory.

The good news from research: **ClawTeam's existing substrate is already ~80% of what we need**. `Phase` and `AgentRole` are already open `str` types (no enum to extend), `PhaseState.phases` is a configurable list, `HarnessPlugin` has the right extension shape, and `file_locked()` + `atomic_write_text()` + `get_data_dir()` cover all new persistence needs. The minimum-viable core delta is ~1500-2000 LOC of additive new modules (`sprint/`, `attention/`, `memory/`, `harness/phase_registry.py`, `harness/interaction_gate.py`) plus three optional `HarnessPlugin` methods. **Zero new required runtime deps**; one optional extra (`clawteam[browser]` -> Playwright) for the `/browse` family. All gstack-specific behavior lives inside a single `GstackSprintPlugin` + `gstack.toml`, keeping the core upstream-PR-acceptable.

The risks are real and mostly architectural, not LLM-quality. Berkeley MAST found **41.8% of multi-agent failures are Specification & System Design**, not model weakness — the 9 ship-blockers we uncovered (persona drift, deadlock, gate gaming, memory poisoning, theater, cost blowup, resource blowup, attention fatigue, backwards-compat regression) all need structural prevention baked into the *earliest* phases or they calcify. That shapes roadmap ordering: foundation (extension API + safety filters + upstream RFC) must land before the sprint engine; the sprint engine must ship with evidence-checking gates and protocol-enforced structured responses from day one, not retrofitted. Defer embeddings, vector memory, web UIs, and multi-team Conductor UI to v2 — they have clean upgrade paths already.

## Key Findings

### Recommended Stack

See `.planning/research/STACK.md` for full rationale.

Four of five domain questions can be answered on stdlib + existing deps (`pydantic v2`, `questionary`, `rich`, `typer`, `file_locked()`, `atomic_write_text()`). Budget: **zero new required deps**, **one new optional extra** (`clawteam[browser]`). Single SQLite/vector-DB dep aggressively deferred — `/learn` grep-first scales to 100s of entries; `sqlite-vec` (160 KB) is the pre-shaped v2 upgrade when needed.

**Core technologies (NEW additions only):**
- *(nothing required)* — AttentionQueue, TeamMemoryStore, InteractionGate, PhaseRegistry, SprintConductor all ride on stdlib + pydantic v2 + existing file-locked I/O
- `playwright >=1.58,<2` (optional, `clawteam[browser]` extra) — headless Chromium for `/browse`, `/design-shotgun`, `/design-html`, `/pair-agent` skills; Python 3.9-3.13 supported
- `patchright >=1.58.2,<2` (optional-of-optional, `clawteam[browser-stealth]`) — drop-in Playwright replacement for anti-bot sites; only shipped as a feature flag, never default

**Deliberately NOT added (v2 upgrade paths pre-shaped):**
- `sqlite-vec` — reserved for /learn memory v2 when grep stops scaling (~2-3K entries/team)
- `textual` — reserved for Multi-team Conductor UI v2
- `persist-queue` / `aiodiskqueue` / `chromadb` — rejected; violate the "everything under `~/.clawteam/` is grep-able markdown" design
- `pyppeteer` / `playwright-stealth` — superseded or scope-inappropriate
- `pyyaml` — skill frontmatters are flat KV; 15 LOC handcoded parser suffices

### Expected Features

See `.planning/research/FEATURES.md` for the full P1/P2/P3 matrix.

**v1 shape (the minimum that tells the "team is the product" narrative):**

Core infrastructure (enabling — nothing else ships without these):
- `PhaseRegistry` — plugin-populated phase list + gate bundles + role mapping
- `SprintState` + `SprintConductor` — per-team multi-sprint coordinator
- `InteractionGate` — editor-based markdown Q&A round-trip (questions/N.md <-> answers/N.md)
- `AttentionQueue` — cross-sprint priority-sorted pending questions, read-time projection
- `TeamMemoryStore` — layered (team-shared + per-agent) grep-first markdown store

Gstack product surface (the 11-agent team + sprint model):
- 11-agent `gstack.toml` template: pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre
- `GstackSprintPlugin` — registers 7 phases + per-phase EvidenceGates + per-role prompt contributions
- Methodology port (baked into role prompts): /office-hours, /plan-ceo-review, /plan-eng-review, /plan-design-review, /plan-devex-review, /retro, /design-consultation, /design-review, /devex-review, /review, /investigate, /qa, /qa-only, /cso
- `SmartReviewRouter` — CODEOWNERS-style path globs in `gstack.toml` (rules-first, not LLM-classified)

Tool-heavy skill ports (the features users *touch*):
- `/browse` + `/open-gstack-browser` + `/setup-browser-cookies` (clawteam[browser])
- `/design-shotgun` + `/design-html` (flagship visual iteration loop)
- `/codex` (cross-model second opinion via existing NativeCliAdapter)
- `/ship` + `/land-and-deploy` + `/document-release` (Ship phase)
- `/canary` + `/benchmark` + `/setup-deploy` (SRE role)
- `/learn` (team memory interface)

Safety rails (harness primitives, not per-agent skills):
- `/careful` + `/freeze` + `/guard` + `/unfreeze` via EventBus hooks on file-write tool calls

UX:
- `clawteam team spawn gstack --name <n>`, `clawteam sprint start/pause/resume/status/show/list`, `clawteam attend`, `clawteam team show`, `clawteam doctor` (optional-tool detection), `clawteam memory review/purge`

**Differentiators (what we uniquely win on):**
- 11-persona pre-configured team vs SDK-per-run (CrewAI/AutoGen) or single-droid (Factory)
- 7-phase sprint as product, not just pipeline — strongest guardrails in category
- Diff-aware smart review routing at sprint-phase level (not just PR level like CodeRabbit)
- AttentionQueue cross-sprint priority scoring — unique to us; Conductor has a dashboard but no prioritization
- Memory compounding across sprints with provenance + decay (mem0/Letta-style but team-scoped)
- Upstream-PR-friendly plugin architecture — future templates (hedge-fund sprint, research-paper sprint) can reuse `sprint/`, `attention/`, `memory/`

**Anti-features (loudly rejected, even if requested):**
- Full auto-pilot "never ask" mode — removes taste decisions; feeds theater failure mode
- Dynamic agent creation ("spawn new specialist mid-sprint") — violates team identity
- Per-agent model picking — auth/cost/memory surface x 11 splinters
- In-sprint voting/consensus — pitfall #2 deadlock shape
- Real-time agent chat UI — encourages chatty theater
- Auto-merge on green — blast radius violation of gate gaming pitfall
- Skill auto-install — PROJECT.md constraint; breaks containerized/CI setups

**Defer (v2+):**
- Helper spawning inside engineer (sub-worktrees) — P2, trigger when Build phase shows serial bottleneck
- `/pair-agent` cross-vendor browser coordination — P2
- Embedding-based memory retrieval (sqlite-vec) — P2, trigger when grep misses patterns at scale
- Multi-team Conductor UI — P3, explicit v2 per PROJECT.md
- Quick-sprint heuristic, pool/shared specialist, template customization hooks — P2/P3

### Architecture Approach

See `.planning/research/ARCHITECTURE.md` for the full 11-step build plan, data flows, and anti-patterns.

**Three architectural facts shape every decision:**
1. `Phase` / `AgentRole` are open `str` types already — `PhaseRegistry` is a *list populator*, not an enum extension
2. `HarnessContext` already gives plugins `bus/tasks/spawner/sessions/artifacts/config`; just need 3 new optional `HarnessPlugin` hooks
3. `file_locked()` + `atomic_write_text()` + `get_data_dir()` cover every persistent component

**Major components (NEW only; all additive):**
1. **PhaseRegistry** — in-memory registry populated from `HarnessPlugin.contribute_phases() / contribute_gates() / contribute_phase_roles()`; validates no collisions; hands frozen phase order to `PhaseRunner`. ~100 LOC. Placed in `harness/` not `sprint/` so future non-sprint templates can reuse.
2. **SprintState + SprintConductor** — pydantic model persisted per-sprint + per-team orchestrator holding `asyncio.Semaphore(max_concurrent_sprints=10)` + per-agent `Semaphore(1)`; dispatches through existing team-wide `TaskStore` with `sprint_id` labels (NOT per-sprint asyncio tasks or thread-per-sprint — both lose to Pattern 2's long-lived-worker model).
3. **InteractionGate** — `PhaseGate` subclass; fails iff `sprint/<id>/questions/*.md` has no sibling `answers/*.md`; human edits files in their editor and runs `clawteam sprint advance`. **Editor-based, not CLI-blocking, not web UI** — scales naturally from 1 to 10 sprints.
4. **AttentionQueue** — priority-scored read-time projection over per-sprint question files (not a durable queue); score = URGENCY + BLOCKING + AGE + EXPLICIT_TAG, additive. Linear Triage + GitHub Notifications pattern.
5. **TeamMemoryStore** — layered hierarchy `memory/team/*.md` (shared) + `memory/agents/<role>/*.md` (private); grep-first retrieval (Letta benchmarks validate); `sqlite-vec` is the pre-shaped v2 upgrade path; writer is swap-preserving.
6. **SmartReviewRouter** — CODEOWNERS-style path-glob rules loaded from `gstack.toml`, runs at Review phase entry against the sprint's diff; parallel dispatches reviewer tasks; reviewer (staff eng) synthesizes to `review-report.md`. **Rules-first, strictly**; LLM fallback reserved for v2.
7. **HelperSpawner** — thin facade over existing `WorkspaceManager.create_workspace/merge`; engineer forks ephemeral sub-worktrees tracked with parent-child relation in spawn registry; capped at N helpers/engineer/sprint.
8. **GstackSprintPlugin** — one cohesive file that wires steps 1-7 for gstack specifically; owns `gstack.toml` roster + methodology prompt contributions + safety-rail EventBus subscribers. **All gstack-specific logic lives here** — if you delete it, the rest of the codebase still runs and existing templates are unaffected (that's the upstream-compatibility contract).

**Core vs plugin split (critical for upstream PR):**
- Core delta: `harness/phase_registry.py` (NEW), `harness/interaction_gate.py` (NEW), `plugins/base.py` (3 optional methods with empty defaults), `sprint/` (NEW dir), `attention/` (NEW dir), `memory/` (NEW dir), CLI/MCP subcommand additions. ~1500-2000 LOC. PR-sized.
- Plugin-only: `plugins/gstack_sprint_plugin.py` + `templates/gstack.toml` + methodology prompts. **No other template needs gstack to be installed.**

### Critical Pitfalls

See `.planning/research/PITFALLS.md` for all 17 (9 ship-blockers + 8 quality) + phase-mapped preventions + recovery strategies. Two headline numbers anchor the list:
- MAST (Berkeley arXiv 2503.13657, 200 traces across 7 frameworks): **41.8% of multi-agent failures are Specification & System Design**, not LLM quality
- Echoing/Identity-Drift paper: **persona self-consistency degrades >30% after 8-12 turns**; a structured-response protocol cuts it from 70% echoing to 9%

Top ship-blockers whose **preventions must be in v1 scope, not deferred**:

1. **Agent identity drift / "echoing"** (Pitfall 1) — after a few sprints every agent sounds like generic Claude, killing the "team of specialists" narrative. **Prevention (must ship v1):** protocol-level structured response envelopes with mandatory persona-reasserting fields (e.g. `pm.challenge`), role-prompt re-injection at each phase boundary, reviewer-disagreement alarm when <20% of parallel reviewers disagree (agreement is a red flag).
2. **Inter-agent deadlock** (Pitfall 2) — pm asks ceo, ceo asks pm; tokens burn forever. **Prevention (must ship v1):** per-phase turn budget + per-pair ping cap (3 round-trips max on same (A, B, topic) hash), cycle detector in transport, forced-progress gate requiring artifact growth per turn, explicit `{done: true}` termination signal in every role contract.
3. **Phase-gate gaming** (Pitfall 8) — `ArtifactRequiredGate` passes on "TBD" content; hallucinated review reports; fake test reports. **Prevention (must ship v1):** replace `ArtifactRequiredGate` with `EvidenceGate` family — design-doc requires named sections with min tokens; review reports must cite real diff line ranges; test reports must reference actual test-runner output hash (gate re-runs pytest); ship notes must reference a resolving deploy URL; cross-agent verification (qa verifies engineer's test-report).
4. **Parallel-sprint resource blowup** (Pitfall 4) — 11 agents x 10 sprints = 33 GB RAM; laptop melts; narrative dies. **Prevention (must ship v1):** active-agent budget (default 4 concurrent active); per-phase agent-slot pooling (Think = pm + ceo only; Build = engineer + helpers); `max_parallel_sprints: 3` default; idle agents sleep-poll (no Claude keepalive burn); rate-limit-aware scheduling.
5. **Human attention fatigue** (Pitfall 5) — `clawteam attend` becomes a dead inbox; 70 items, user stops opening it. **Prevention (must ship v1):** typed/structured questions (urgency + decision_cost_estimate + reversibility + recommended), question budget per sprint (default 3), default-accept with TTL for reversible recommendations, `--summary` digest mode rolling related questions into single decisions, abandonment detection in `team show`.
6. **Cost blowup** (Pitfall 12) — 11 agents x Opus x 10 sprints = $100-500/day/user. **Prevention (must ship v1):** Anthropic Advisor model tier mapping by default (Opus: ceo/pm strategic; Sonnet: engineer/reviewer/qa/security exec; Haiku: shipper/sre clerical); aggressive prompt caching (role prompts immutable per session; 90% discount); per-team budget dashboard with 50/80/100% alarms; dormancy discipline; model fallback ladder at rate-limit.
7. **Memory poisoning** (Pitfall 10) — sprint 3's bad decision gets locked in; sprint 10 doubles down. MINJA attack shows 95% injection success. **Prevention (must ship v1 if `/learn` ships):** provenance on every entry (`{learned_from: user|artifact|self-inferred}`), retrieval weighting by provenance, human gate on "architectural/convention" tagged entries, conflict detection on /learn-add, `clawteam memory review/purge` audit commands, isolated per-project + per-team + per-agent namespaces. **If these can't land in v1, scope down `/learn` to read-only team pre-loaded memory and defer write path to v2.**
8. **Multi-agent theater** (Pitfall 11) — 200 messages, 12 artifacts, 0 KB of real work. **Prevention (must ship v1):** progress-on-artifact rule (every turn writes bytes/structure or produces a concrete deliverable); role-specific output contracts (pm must produce a question or advice per turn); artifacts-as-state not messages-as-state (Cognition's argument); `artifact_delta_per_hour` as primary `sprint status` metric; `token_per_useful_byte` anomaly alarm.
9. **Backwards-compat regression** (Pitfall 14) — existing software-dev/hedge-fund/code-review/harness-default/research-paper/strategy-room templates break. **Prevention (must ship v1):** golden-path integration tests per existing template on every PR; new plugin hooks strictly additive with empty defaults; `PhaseRegistry` never mutates existing `PhaseState` semantics.

**Secret leakage (Pitfall 17) is Phase-0 foundation work.** CONCERNS.md already documents `hooks.py:80-88` copies full `os.environ` -> `/learn` could ingest secrets via transcripts. Deny-pattern env filter (`*TOKEN`, `*KEY`, `*SECRET`, `*PASSWORD*`) must land before any live team ships.

## Key Technical Bets

These are the opinionated choices that differentiate our approach. Each is backed by converging research.

1. **Zero new required deps.** AttentionQueue/TeamMemory/InteractionGate/PhaseRegistry all ride on stdlib + existing file-locked I/O. Browser is opt-in via `clawteam[browser]`. The `pip install clawteam` footprint does not grow.

2. **Grep-first team memory, embeddings in v2.** Letta's own benchmarks show filesystem+grep is competitive for structured agent notes; Claude Code's native memory uses plain markdown; `/learn` produces dozens-to-hundreds of entries per team, not thousands. `sqlite-vec` (160 KB, zero-infra) is the pre-shaped v2 upgrade when grep stops scaling.

3. **Rules-first smart review routing.** CODEOWNERS-style path globs in `gstack.toml` give deterministic, debuggable, zero-cost routing that's correct 95% of the time for path-based decisions. LLM-classified routing is reserved for "no rule matched" v2 fallback. CodeRabbit's architecture validates the pattern.

4. **Editor-based InteractionGate (not CLI-blocking, not web UI).** Questions are markdown files under `sprint/<id>/questions/N.md`; answers are sibling files. The user lives in their editor anyway. Scales naturally from 1 sprint to 10 because there's no terminal to block, no server to run. MCP elicitation is per-session (wrong for cross-session question-answering); LangGraph's interrupt is graph-execution-coupled (wrong for long-lived CLI agents). File-based is strictly more durable.

5. **Upstream-PR-friendly plugin architecture.** Core substrate (`sprint/`, `attention/`, `memory/`, `PhaseRegistry`) is generic; gstack-specific behavior confined to `GstackSprintPlugin` + `gstack.toml`. Future templates (hedge-fund-sprint, research-paper-sprint) can reuse the same substrate. The upstream PR is ~1500-2000 LOC of additive new modules + 3 optional plugin-hook additions — intentionally PR-sized.

6. **Protocol-over-prompt for persona stability.** Every agent turn must emit a structured response envelope with persona-reasserting required fields. Research-backed: cuts drift from 70% echoing -> 9%. The mandatory `pm.challenge` field literally forces the YC-advisor-skeptic persona forward each turn.

7. **Team-wide task queue with per-sprint labels (not per-sprint async tasks).** Agents are external long-lived CLI processes that poll their own inbox. Conductor multiplexes 10 sprints' tasks through 11 agents' inboxes. Process footprint stays constant at 11 regardless of sprint count. Python asyncio producer-consumer + Temporal's signal-by-ID + asyncio.Semaphore bounded concurrency all converge on this shape.

## Implications for Roadmap

Based on the 11-step build order from `ARCHITECTURE.md`, the pitfall-to-phase mapping from `PITFALLS.md`, and the P1 feature list from `FEATURES.md`, here's the suggested phase structure. Each phase bundles ARCHITECTURE build steps with their critical-path pitfall preventions so the prevention ships with the feature, not behind it.

### Phase 0: Foundation & RFC

**Rationale:** Upstream-compat, secret-scrubbing, and default model profile are cheap pre-reqs that get expensive if retrofitted. Upstream RFC buys maintainer buy-in before core changes land.
**Delivers:**
- Upstream RFC for `PhaseRegistry` + 3 new `HarnessPlugin` optional methods (additive-only contract)
- Env deny-pattern filter on `os.environ` -> `CLAWTEAM_*` mirror (Pitfall 17 ship-blocker preempted)
- Default "Balanced" model profile mapping in template scaffolding — Opus for ceo/pm, Sonnet for engineer/reviewer/qa/security, Haiku for shipper/sre clerical (Pitfall 12 prevention)
- Golden-path integration test matrix for 6 existing templates (Pitfall 14 regression prevention)
- Code-CONCERNS triage: fix `broad except Exception: pass` in `workspace/manager.py` and `events/hooks.py`; data-driven resume presets plan (Pitfall 16)
- Windows CI job addition for worktree-dependent code paths (preempts Pitfall 6 Issue #40164-class failures)

**Avoids:** Pitfalls 14, 15, 16, 17; partially 12.
**Uses:** Existing plumbing only.

### Phase 1: Core Harness Extensions (upstream-PR-ready core)

**Rationale:** `PhaseRegistry` + `InteractionGate` + `SprintState` are the base of everything downstream. `HarnessPlugin` hook additions must be in place before `GstackSprintPlugin` can register anything. These are the cleanest core-only changes and constitute the target upstream PR.
**Delivers:**
- ARCH build step 1: `clawteam/harness/phase_registry.py` + 3 new optional methods on `HarnessPlugin` with empty defaults (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`)
- ARCH build step 2: `clawteam/sprint/state.py` + `clawteam/sprint/registry.py` (SprintState pydantic model + file-locked persistence)
- ARCH build step 3: `clawteam/harness/interaction_gate.py` (PhaseGate subclass, ~60 LOC)
- Minimal `HarnessOrchestrator.__init__` modification — optionally consult PhaseRegistry when `phases` unset; zero change to default behavior
- Unit tests for registry collision detection, sprint state round-trip, interaction-gate question/answer scanning

**Avoids:** Pitfall 14 (all additive); foundation for 15.
**Research flag:** NONE. Standard plugin-registry patterns; codebase already makes the "open str" choice. Well-understood.
**Critical path:** Yes. Blocks every subsequent phase.

### Phase 2: Sprint Engine + Evidence Gates + Theater Prevention

**Rationale:** Single-sprint-running end-to-end is the first demonstrable team behavior. Evidence gates and theater prevention **must ship with the sprint engine**, not retrofitted, because once gates are trivially-gameable the downstream data is contaminated. Cycle detector belongs in the transport layer before multi-sprint exacerbates any loop.
**Delivers:**
- ARCH build step 6: `clawteam/sprint/conductor.py` (SprintConductor single-sprint mode; dispatches through existing TaskStore with sprint_id labels)
- `EvidenceGate` family replacing `ArtifactRequiredGate` for 7 phases (Pitfall 8 ship-blocker): structured-section validators on design-doc/plan-doc, diff-parseable check, review-citation validation, test-runner output-hash side-channel, deploy-URL dereference for ship notes
- Per-phase turn budget + per-pair ping budget + cycle detector in EventBus/transport (Pitfall 2 ship-blocker): hash (sender, recipient, topic) within rolling window -> circuit breaker
- Forced-progress gate: every turn extends artifact bytes/structure or escalates to InteractionGate (Pitfall 11 theater ship-blocker)
- Structured response envelope protocol for all agent turns — persona-reasserting required fields per role (Pitfall 1 persona-drift ship-blocker; reduces from 70% -> 9% echoing)
- Role-prompt re-injection at each phase boundary (Pitfall 1 mitigation)
- Artifact size caps per phase (Pitfall 3 mitigation: prevents unbounded context)
- `sprint status` surfaces `artifact_delta_per_hour` and `token_per_useful_byte` as primary metrics (Pitfall 11 observability)
- Initial methodology-port classification audit (Pitfall 7): each gstack skill tagged {pure-methodology, interactive-Socratic, tool-heavy, safety-rail}; Socratic skills slated for Phase 3 state-machine implementation, not prompt-only

**Avoids:** Pitfalls 1, 2, 8, 11 (all ship-blockers); partially 3, 7.
**Research flag:** MEDIUM. Evidence-gate design has well-documented patterns (Three Dots Labs' replay-verification, deterministic side-channels) but the specific EvidenceGate schema per artifact type benefits from a quick research pass. Cycle-detector implementation has the Paperclip #390 + Markaicode precedent; standard.
**Critical path:** Yes. Must precede Phase 3 multi-agent work or agents coordinate on a gameable substrate.

### Phase 3: Gstack Team Plugin + Methodology Port + Interactive State Machines + Smart Review Routing

**Rationale:** This is the phase where the product surface shows up. The plugin + template deliver the 11-agent team; methodology port makes roles feel real; interactive-skill state machines preserve gstack's Socratic quality; smart review routing delivers the diff-aware differentiator. These cluster because they share the `GstackSprintPlugin` file and the `gstack.toml` template.
**Delivers:**
- ARCH build step 7: `clawteam/sprint/review_router.py` — CODEOWNERS-style path-glob rules from `gstack.toml`; parallel reviewer dispatch; `review-report.md` synthesis by `reviewer` (staff eng)
- ARCH build step 8: `clawteam/plugins/gstack_sprint_plugin.py` + `clawteam/templates/gstack.toml` with 11-agent roster, per-role prompts, per-phase gate wiring, safety-rail EventBus subscribers
- Methodology port for pure-rubric skills (prompt-only): /plan-ceo-review, /plan-eng-review, /plan-design-review, /plan-devex-review, /retro, /design-review, /devex-review, /review, /qa-only, /cso
- Interactive skills as phase sub-state-machines (Pitfall 7): /office-hours, /design-consultation, /investigate — JSON scaffold state with required-field progression
- Golden-trace tests comparing ported skills against native gstack interaction shape (turn count, Q&A branches)
- SHA-pinned reviews (Pitfall 9): every review records diff SHA; mid-review push invalidates prior reviews with explicit reviewer choice
- Multi-signal routing (Pitfall 9): path regex + import/API signal + explicit `# @review:security` comment tokens; >= 2 signals before skipping a specialist
- Mandatory reviewer overlap + reviewer-summon rights with cooldown (Pitfall 9)
- Structured disagreement preservation -> escalates to InteractionGate rather than averaging (Pitfall 9 + Pitfall 13 sycophancy cascade)
- Reviewer decorrelation (Pitfall 13): reviewer isolation, varied temperatures, agreement-rate alarm on >90%
- Cross-agent verification gates (Pitfall 8): qa verifies engineer's test-report, reviewer verifies designer's design-doc
- `clawteam team spawn gstack` end-to-end -> running a full Think->Ship sprint on ported methodology
- Tool-heavy skill ports for Build/Ship/Test/SRE: /codex, /ship, /land-and-deploy, /document-release, /canary, /benchmark, /setup-deploy — implementation as ClawTeam skill modules (not prompt baking)
- Safety-rail harness primitives: /careful, /freeze, /guard, /unfreeze — EventBus hooks on file-write tool calls; workspace-manager enforces freeze paths

**Avoids:** Pitfalls 7, 9, 13; reinforces 8.
**Research flag:** HIGH. The methodology port has the biggest implementation risk-surface in the whole project — the Socratic/interactive skill state-machine design lacks established precedent. **Recommend `/gsd-research-phase` before implementing Phase 3.** Questions to answer during planning: what's the minimum state-machine schema per interactive skill? how do we source golden traces from native gstack for regression testing? what are the role-reassertion field requirements for each of the 11 personas? how does the SmartReviewRouter handle adversarial diffs (renamed files, test files with crypto usage)?
**Critical path:** Yes. Without it there's no product — Phase 1/2 alone is just scaffolding.

### Phase 4: Browser Skills + /design-shotgun -> /design-html + /learn Memory

**Rationale:** Once the sprint engine + team are demonstrable, the user-facing visual and memory features make the "team that learns your taste" narrative real. `/browse` family requires Playwright optional-extra; `/design-shotgun -> /design-html` is the flagship visual iteration; `/learn` with provenance + decay is the memory compounding story. Bundled because they all rely on the Phase-3 plugin surface being stable.
**Delivers:**
- `clawteam[browser]` optional extra with `playwright>=1.58,<2`; `clawteam doctor` detects Chromium + prints install instructions (Pitfall integration gotcha)
- /browse + /open-gstack-browser + /setup-browser-cookies skills
- /design-shotgun (mockup variant generator) + /design-html (pick -> HTML) pipeline — the flagship differentiator
- ARCH build step 4: `clawteam/attention/queue.py` + `clawteam/attention/scorer.py` — priority scoring (URGENCY + BLOCKING + AGE + EXPLICIT_TAG, additive)
- ARCH build step 5: `clawteam/memory/store.py` + `clawteam/memory/retriever.py` — layered team-shared + per-agent markdown hierarchy; grep-first retrieval; MCP tools `memory_learn` + `memory_search`
- `/learn` skill with provenance on every entry (`learned_from: {user|artifact|self-inferred}`) (Pitfall 10 ship-blocker defense)
- Retrieval weighting: user-grounded > artifact-grounded > self-inferred (Pitfall 10)
- Conflict detection on `/learn` add: retrieve similar, flag contradictions (Pitfall 10)
- Human gate via InteractionGate on "architectural/convention"-tagged entries (Pitfall 10)
- `clawteam memory review` + `clawteam memory purge` audit commands (Pitfall 10)
- Per-project/per-team/per-agent namespace isolation — no cross-team memory bleed (Pitfall 10 + security)
- Secret-scrubbing on transcript -> memory ingestion path (Pitfall 17 defense-in-depth on top of Phase 0 env filter)
- MemGPT-tiered memory design (Pitfall 3): in-prompt "core" <= 2KB per agent, grep-retrieved "archival", event-log "recall"
- Sprint artifact summarization at phase boundaries with bounded compaction cycles (Pitfall 3)

**Avoids:** Pitfalls 3, 10; reinforces 17.
**Research flag:** MEDIUM. Playwright Python API + persistent-context browser daemon has well-documented patterns (Microsoft's `playwright-python` Context7 library). Memory provenance + decay schema is less established — MINJA/MemoryGraft/SSGM papers describe the problem but concrete schema for a multi-agent team-shared store benefits from a planning research pass. **Consider `/gsd-research-phase` for the memory write-path if Pitfall 10 preventions feel under-specified.**
**Critical path:** Partially. `/learn` is v1 table-stakes per FEATURES.md; browser skills are differentiators. Could ship browser before memory if needed.

### Phase 5: Parallel Sprints + AttentionQueue UX + Cost & Resource Controls

**Rationale:** Parallel sprints is the force-multiplier value proposition, but it also exposes the nonlinear ship-blockers (attention fatigue, resource blowup, cost blowup). Ships last because it compounds earlier risks; must ship with all three prevention mechanisms fully designed.
**Delivers:**
- ARCH build step 10: `SprintConductor` `asyncio.Semaphore(max_concurrent_sprints=10)` + per-agent `Semaphore(1)` caps
- Active-agent budget (default 4 concurrent active) + per-phase agent-slot pooling (Think = pm + ceo; Plan = pm/ceo/eng-mgr/designer/dx-lead; Build = engineer + helpers; etc.) (Pitfall 4 ship-blocker)
- `max_parallel_sprints: 3` team default with soft/hard limits (Pitfall 4)
- Dormancy discipline: idle agents sleep-poll, keepalive loop paused (Pitfall 4 + 12)
- Rate-limit-aware scheduling: queue new phase starts when Anthropic TPM saturated (Pitfall 4 + 12)
- Data-driven resume presets (`clawteam/spawn/presets.py` TOML) + per-CLI regression matrix (Pitfall 16)
- ARCH build step 11: CLI polish — `clawteam attend` with typed-priority queue + `--summary` digest + `--auto-accept-reversible` (Pitfall 5 ship-blocker), `clawteam team show` with cost dashboard + per-agent current-action + abandonment detection + drift regression alarm (Pitfalls 5, 12, 1)
- Sprint pause/resume via state checkpoints (community-demonstrated table-stake per FEATURES.md AutoGen/LangGraph/ADK research)
- Per-team cost budget + dashboard: 50/80/100% alarms + hard cap with explicit override (Pitfall 12)
- Cost observability per phase/role/sprint — Opus/Sonnet/Haiku breakdown (Pitfall 12)
- Prompt-caching aggressively: role prompts cached per session, team memory core cached per team, per-sprint artifacts cached per sprint — 90% discount on repeat reads (Pitfall 12)
- Model fallback ladder: auto-downgrade on rate-limit/budget-near-cap with flagged note (Pitfall 12)
- Disk-budget alarm per team (default 5 GB, 80% warn) + zombie-worktree auto-GC (Pitfall 6)
- `clawteam doctor` command surface — detects missing Chromium, codex CLI, ngrok; prints install instructions

**Avoids:** Pitfalls 4, 5, 6, 12, 16; reinforces 1.
**Research flag:** MEDIUM. Anthropic prompt-caching API + rate-limit backoff has good docs (Anthropic + Portkey references in PITFALLS.md). Attention-queue typed-priority UX is established (Linear Triage + Slack Catch Up) but digest-mode presentation benefits from quick UX iteration with real users.
**Critical path:** No (single-sprint works without it) but a marketing ship-blocker for the "10 parallel sprints" narrative.

### Phase 6 (optional/v1.x): Helper Spawning + Polish

**Rationale:** Pure additive; only ships if user feedback from v1 shows Build-phase serial bottleneck. Clean to retrofit thanks to existing `WorkspaceManager.merge` primitives.
**Delivers:**
- ARCH build step 9: `clawteam/sprint/helper_spawner.py` + MCP tool `sprint_spawn_helper`
- `max_helpers_per_engineer` cap (default 3)
- Helper-history audit log (Pitfall 6 UX: "where did my change go?")
- Serialized shared-config edits via `dx-lead` (Pitfall 6): pyproject.toml/package.json edits route through a shared-file lock

**Avoids:** Reinforces Pitfall 6 hardening.
**Research flag:** LOW. Existing WorkspaceManager + spawn registry semantics are well-understood.
**Critical path:** No.

### Phase Ordering Rationale

- **Foundation -> extension API -> sprint engine -> team plugin -> user-facing polish -> scale** is a strict dependency chain. You cannot build the team plugin before the sprint engine; you cannot make the sprint engine solid before evidence gates + theater prevention; you cannot land gates + theater prevention without the `PhaseRegistry` extension point.
- **Preventions bundle with features in the same phase** where possible. Evidence gates ship with sprint engine (Phase 2) because letting gameable gates exist for even one sprint of real use means `/learn` memory gets contaminated. Structured-response protocol ships with sprint engine (Phase 2) because by Phase 3 there are 11 roles that need to respect it.
- **Memory features come after sprint engine + review routing** so provenance-tagging + conflict-detection preventions ship with `/learn`, not after.
- **Parallel sprints come last** because they compound every earlier risk (resource blowup + attention fatigue + cost blowup are all nonlinear in sprint count). Earlier phases demonstrate single-sprint value; Phase 5 is the multi-sprint force-multiplier.
- **Upstream-PR split aligns with phase boundaries.** The Phase-0-RFC -> Phase-1-core-extensions -> Phase-2-sprint-engine bundle is the target upstream PR. Phase 3+ are plugin-only changes that land in the fork first and could theoretically go upstream later if other templates adopt the sprint model.

### Research Flags

**Phases likely needing `/gsd-research-phase` before implementation:**
- **Phase 3 (Methodology port + Smart Review Routing):** HIGH-flag. Interactive-skill state-machine design lacks precedent; needs golden-trace sourcing strategy from native gstack; adversarial-diff handling for SmartReviewRouter; per-persona role-reassertion field schemas. **Recommend research pass before implementation.**
- **Phase 4 (/learn memory):** MEDIUM-flag if Pitfall 10 preventions feel under-specified at planning time. Memory-provenance schema + decay algorithm + conflict-detection retrieval pattern benefit from a targeted research pass. Could be absorbed into Phase 3 research if timing aligns.

**Phases with standard patterns (skip research):**
- **Phase 0 (Foundation):** Upstream RFC drafting, env deny-filter, CI matrix — all standard SDLC work.
- **Phase 1 (Core Extensions):** Plugin-registry patterns, pydantic models, PhaseGate subclassing — codebase conventions already established.
- **Phase 2 (Sprint Engine):** Cycle detector pattern (Paperclip #390 precedent), EvidenceGate design (Three Dots Labs verification pattern), structured-response envelope (Echoing paper protocol) — all have clear published patterns.
- **Phase 5 (Parallel Sprints):** Semaphore-bounded concurrency, prompt caching, Linear-Triage typed queue, disk GC — standard scaling engineering.
- **Phase 6 (Helpers):** Pure additive wrapper over existing WorkspaceManager.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new required deps is a conservative choice verified against codebase inspection; Playwright as optional extra is Context7-verified against `/microsoft/playwright-python`; v2 upgrade paths (sqlite-vec, Textual) are PyPI-verified. |
| Features | MEDIUM | P1 list grounded in 6 production reference systems (Factory, Conductor, Claude Code agent-team, AutoGen, LangGraph, CrewAI, gstack native) + direct ARCHITECTURE/PITFALLS research, but market-expectation signals are inferred from product docs rather than user studies. Table stakes are strongly validated (community-demonstrated, issue-tracker-verified); differentiator impact is hypothesis until launch. |
| Architecture | HIGH | Codebase read firsthand to confirm `Phase`/`AgentRole` are open `str`, plugin hooks are the right shape, `file_locked()` is production-ready. External patterns cross-checked against Context7-indexed docs (LangGraph, Temporal, Python asyncio) and primary sources (CODEOWNERS, Linear, Letta). Core vs plugin split is proven additive via the "delete-the-plugin" test. |
| Pitfalls | HIGH | Primary research papers (Berkeley MAST, MemGPT, Identity-Drift, Echoing, MINJA, MemoryGraft, Cognition's anti-multi-agent argument, Anthropic's counter-response) converge; production post-mortems (Three Dots Labs, Augment Code, Galileo) corroborate. Phase-mapping has direct evidence trails for each prevention. |

**Overall confidence:** HIGH for architecture + stack + pitfalls; MEDIUM for which features users will actually value most (will need v1 feedback to refine P2 ordering).

### Gaps to Address

Open questions that should be resolved before the roadmap is finalized:

1. **Windows support scope.** PROJECT.md doesn't explicitly scope Windows in or out. Pitfall 6 (Issue #40164) says Claude Code's worktree isolation silently falls back to non-worktree on Windows 11. We need to decide: (a) Windows is v1 supported and we ship the graceful-downgrade-with-warning path, (b) Windows is best-effort and we document limitations, or (c) Windows is v2. **Affects Phase 0 CI scope directly.** Recommend explicit decision before Phase 0 ships.

2. **Golden traces for native gstack behavior.** Phase 3's interactive-skill state machines are validated via "does our port match native gstack's interaction shape?" tests. But we don't yet have a source of those golden traces — native gstack doesn't publish fixture transcripts. Options: (a) run native gstack against a fixture repo and record transcripts, (b) derive expected shapes from the skill markdown itself, (c) co-design with Garry Tan. **Needs resolution during Phase 3 research.**

3. **Memory poisoning defense tradeoffs.** Pitfall 10 preventions (provenance + decay + human gate on architectural entries + conflict detection + per-scope isolation) are individually validated but collectively add UX friction. Open question: should `/learn` ship with all preventions v1 (heavier UX, safer), or ship stripped-down v1 (fewer frictions, more poisoning risk) and harden v1.x? The research inclination is "all preventions v1 or scope `/learn` to read-only," but a product call is warranted.

4. **Cost-control default aggressiveness.** Pitfall 12 preventions (Advisor model tiering, prompt caching, budget cap with hard limit) shape first-run UX. If we ship "Quality everywhere" as default, early users get sticker shock; if we ship "Balanced" default, strategic-agent quality on ceo/pm is reduced by default and a subset of sprints may underperform. Open question: what's the default `model_profile` in the shipped `gstack.toml`? Recommend "Balanced" default with clear `--quality` opt-in flag, but confirm.

5. **Safety-rail enforcement point.** Pitfall prevention: /careful /freeze /guard ship as "harness primitives via EventBus hooks on file-write tool calls." Open question: do hooks fire on the *agent's* file-write tool call only, or also on the *underlying process's* filesystem writes (e.g., a subprocess spawned by /ship that writes files)? Choice has implementation implications for the hook granularity. Likely needs a small PoC during Phase 3.

6. **Multi-generation identity env strategy finalization.** CONCERNS.md flags `_env()` as fragile (positional overloading; backward-compat aliases `CLAWTEAM_*/OH_*/CLAUDE_CODE_*` all in-play). Pitfall 17 prevention must extend to all three namespaces without regression. Open: is there scope in Phase 0 to modernize `_env()` away from positional overloading, or is that a separate tech-debt task scoped outside this milestone?

7. **`/pair-agent` priority.** Listed P2/v1.x per FEATURES.md, but it's one of gstack's genuine differentiators (cross-vendor AI agent coordination via shared Chromium). If a user demo would notably benefit from it, could be moved forward. Deferred pending concrete user demand signal.

## Sources

### Primary — codebase (HIGH confidence)
- `.planning/PROJECT.md` — product narrative, constraints, key decisions
- `.planning/codebase/ARCHITECTURE.md` — existing layers, data flows, abstractions
- `.planning/codebase/STACK.md` — baseline deps (pydantic v2, questionary, rich, typer, mcp, pyzmq)
- `.planning/codebase/STRUCTURE.md` — directory layout, naming conventions
- `.planning/codebase/INTEGRATIONS.md` — external surfaces, runtime deps
- `.planning/codebase/CONCERNS.md` — existing tech debt, fragile areas, test gaps
- `clawteam/harness/phases.py` — Phase is `str`, PhaseState.phases is configurable list
- `clawteam/harness/roles.py` — AgentRole is `str`, open
- `clawteam/plugins/base.py` — existing HarnessPlugin hooks
- `clawteam/fileutil.py` — file_locked + atomic_write_text primitives

### Primary — research papers (HIGH confidence)
- Cemri et al. "Why Do Multi-Agent LLM Systems Fail?" (MAST), arXiv 2503.13657 — 41.8%/36.9%/21.3% failure distribution across 200 traces
- Packer et al. "MemGPT: Towards LLMs as Operating Systems", arXiv 2310.08560 — tiered memory
- "Examining Identity Drift in Conversations of LLM Agents", arXiv 2412.00804 — 30% persona degradation after 8-12 turns
- "Echoing: Identity Failures when LLM Agents Talk to Each Other", OpenReview — 70% -> 9% with structured protocol
- MINJA, arXiv 2601.05504 — 95% memory injection success rate
- MemoryGraft, arXiv 2512.16962 — persistent memory compromise
- Governing Evolving Memory (SSGM), arXiv 2603.11768 — feedback-loop error accumulation

### Primary — framework docs (HIGH confidence, Context7-verified)
- `/microsoft/playwright-python` — Python binding, async API, persistent context
- `/asg017/sqlite-vec` — 160 KB vector extension, v2 upgrade path
- LangGraph docs — interrupt/resume pattern, StateGraph extensibility
- Letta/MemGPT docs — tiered memory benchmarks (filesystem+grep competitive with embeddings)
- Python asyncio docs — producer-consumer with bounded worker pool (Pattern 2 validation)
- Temporal Python SDK — human-in-the-loop signal-by-ID pattern
- Anthropic Multi-Agent Research System field report — the counter-response to Cognition

### Secondary — industry posts (MEDIUM confidence, cross-checked)
- Cognition Labs "Don't Build Multi-Agents" — context-engineering argument
- Three Dots Labs "Shipping an AI Agent that Lies to Production" — gate gaming
- Augment Code "Why Multi-Agent LLM Systems Fail" — theater failure mode
- MindStudio "Anthropic Advisor Strategy" — cost-tier mapping
- CodeRabbit intelligence layer architecture — router -> classifier -> specialist topology
- Linear Triage + SLA docs — typed-priority inbox pattern
- Review Fatigue article (Ravi Palwe, Medium Mar 2026) — HITL UX failure mode
- Claude Code Issues #11005, #28546, #40164 — worktree + lock bugs
- Conductor / code-conductor / Factory AI Droid docs — adjacent-product reference
- gstack README + BROWSER.md — upstream semantics we port

### Tertiary — validation-needed (LOW confidence, noted for planning)
- Specific market-expectation signals on feature priorities (inferred from product docs rather than user studies)
- Memory poisoning UX tradeoff (research says "add all preventions"; needs product decision)
- Native gstack golden-trace source for Phase 3 interactive-skill regression tests (not yet published)

---
*Research completed: 2026-04-15*
*Ready for roadmap: yes*
