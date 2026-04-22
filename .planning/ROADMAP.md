# Roadmap: ClawTeam-gstack (v1 — hire-your-team milestone)

## Overview

This roadmap delivers the gstack-as-team integration in eight phases, moving from foundation safety nets through the target upstream-PR core, then building the 11-agent team product surface on top, and finally unlocking parallel-sprint force-multiplier UX. Phases are ordered so every pitfall prevention ships with the feature it protects (evidence gates with the sprint engine, provenance with `/learn`, cost controls with parallel sprints), because retrofitting these preventions after adoption is painful per `research/PITFALLS.md`. Phases 0-2 are the target upstream PR bundle; Phase 3+ is gstack-specific fork content.

**Milestone:** v1.0 — "You hire a virtual engineering team, and over time they get better at working with you."
**Granularity:** fine (8-12 phases)
**Critical path:** Phase 0 -> Phase 1 -> Phase 2 -> Phase 3 (product surface exists) -> Phase 4 (product surface works end-to-end) -> Phase 7 (parallel sprints narrative)
**Upstream-PR scope:** Phases 0, 1, 2 (additive core substrate + plugin hooks; zero changes to existing template semantics)

## Phases

**Phase Numbering:**
- Integer phases (0-7): Planned milestone work
- Decimal phases (2.1, 3.1, ...): Urgent insertions (marked INSERTED) — created via `/gsd-insert-phase` if needed

- [ ] **Phase 0: Foundation & Upstream RFC** - Backwards-compat regression matrix, env secret-scrubbing, balanced model default, `clawteam doctor`, upstream RFC for extension API
- [ ] **Phase 1: Core Harness Extensions** - `PhaseRegistry`, `SprintState`, `InteractionGate`; target-upstream core with no semantic changes to existing templates
- [ ] **Phase 2: Sprint Engine, Evidence Gates & Theater/Drift/Deadlock Prevention** - Single-sprint end-to-end with EvidenceGates, cycle detector, structured-response envelope, safety-rail primitives, and sprint CLI (start/status/show/list/pause/resume)
- [ ] **Phase 3: Gstack Team Template & Methodology Port** - Ships `gstack.toml` (11 agents) + `GstackSprintPlugin` with per-role methodology prompts baked in; first runnable Think->Ship sprint on the real team roster
- [ ] **Phase 4: Interactive State Machines, Smart Review Routing & Cross-Agent Verification** - Interactive gstack skills (`/office-hours`, `/design-consultation`, `/investigate`) as state machines; SHA-pinned CODEOWNERS-style reviewer routing; parallel reviewer decorrelation; cross-agent verification gates; Ship-phase human-approval gate
- [x] **Phase 5: Tool-Heavy Skills (Ship, SRE, Codex)** - `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy`, `/codex` — the surfaces engineer/shipper/sre invoke at runtime — **COMPLETE 2026-04-22** (all 10 plans landed; SKILL-13..19 closed)
- [ ] **Phase 6: Browser Skills, Design Pipeline & Team Memory** - `clawteam[browser]` extra, `/browse`, `/design-shotgun`, `/design-html`, and `/learn` memory store with provenance + decay + human gate on high-impact entries
- [ ] **Phase 7: Parallel Sprints, AttentionQueue UX & Cost Controls** - `SprintConductor` concurrency caps, `clawteam attend` typed-priority queue with digest mode, cost dashboard, prompt caching, rate-limit-aware scheduling

## Phase Details

### Phase 0: Foundation & Upstream RFC

**Goal**: Lay down cheap-to-add-now, expensive-to-retrofit foundations (backwards-compat test matrix, env secret-scrubbing, default model profile, missing-tool detection) and get upstream buy-in on the plugin API shape before any core code lands.

**Depends on**: Nothing (first phase).

**Requirements**: CORE-03, TEAM-06, QUALITY-14, QUALITY-15, UX-08

**Success Criteria** (what must be TRUE):
  1. Running the full existing test suite against `software-dev`, `hedge-fund`, `code-review`, `harness-default`, `research-paper`, and `strategy-room` templates continues to pass on CI with no code changes to those templates — verified by a new `tests/test_template_regression_matrix.py` that spawns and advances each template through its existing phase sequence.
  2. Running `clawteam team spawn software-dev --name foo` followed by any command that emits event hooks never leaks `*_TOKEN`, `*_KEY`, `*_SECRET`, `*PASSWORD*`-shaped environment values into `/learn` entries, board views, or event-log files — verified by a secret-scrubbing unit test on `clawteam/events/hooks.py::_env_snapshot()` with a fixture env that seeds `OPENAI_API_KEY`/`GITHUB_TOKEN`/`DB_PASSWORD` and asserts none appear in the mirrored `CLAWTEAM_*` env dict, mailbox payloads, or artifact writes.
  3. Running `clawteam doctor` on a machine without Chromium, Codex CLI, ngrok, or watchdog prints per-OS install instructions for each missing optional tool (`pip install 'clawteam[browser]' && playwright install chromium`, `npm install -g @openai/codex`, platform-specific ngrok) and exits 0; on a fully-provisioned machine prints a green report of what's detected.
  4. An RFC document exists at `docs/rfcs/001-phase-registry.md` proposing the three optional `HarnessPlugin` hooks (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`) with empty defaults, the `PhaseRegistry` class shape, additive-only contract guarantees, and a worked example showing `software-dev.toml` continues to work unchanged. (Upstream submission + maintainer ack is deferred to v1 post-ship per Deferred Items UP-01 — the RFC lives in the fork first.)
  5. `clawteam/templates/` scaffolding used by `gstack.toml` (which lands in Phase 3) reads a default `model_profile = "balanced"` when unset, and the template-loading code path rejects `quality` as a silent default (must be explicitly opted into via `--model-profile quality` or config) — verified by a template-loading unit test that asserts an unspecified profile resolves to `balanced`, not `quality`.

**Canonical refs**:
- research/PITFALLS.md Pitfalls 14 (BC regression), 15 (upstream API drift), 17 (secret leakage), 12 (cost blowup default)
- codebase/CONCERNS.md "Secrets in env" (`clawteam/events/hooks.py:80-88`)
- research/SUMMARY.md Phase 0 section + Gaps to Address #1 (Windows scope) and #4 (default aggressiveness)
- research/STACK.md "No new required deps" envelope

**Upstream-PR status**: Part of target upstream bundle. RFC + regression matrix are prerequisites that benefit every template, not just gstack.

**Plans**: 5 plans

Plans:
- [ ] 00-01-PLAN.md — Env deny-filter: scrub_env helper + hooks.py wiring + unit/integration tests (QUALITY-15)
- [ ] 00-02-PLAN.md — clawteam doctor CLI subcommand with per-OS install hints for Chromium/codex/ngrok/watchdog (UX-08)
- [ ] 00-03-PLAN.md — Default model_profile scaffold field on ClawTeamConfig (TEAM-06 + Pitfall #12)
- [ ] 00-04-PLAN.md — BC regression matrix: parametrized pytest over 6 packaged templates (CORE-03, TEAM-06, QUALITY-14)
- [ ] 00-05-PLAN.md — Upstream RFC 001 (PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate)

---

### Phase 1: Core Harness Extensions

**Goal**: Add the three new harness primitives (`PhaseRegistry`, `SprintState`, `InteractionGate`) and the three optional `HarnessPlugin` hooks with empty defaults, landing the cleanest possible upstream-PR-ready core changes.

**Depends on**: Phase 0 (regression matrix must exist before we modify harness surface).

**Requirements**: CORE-01, CORE-02, CORE-04, INT-01, INT-02

**Success Criteria** (what must be TRUE):
  1. `PhaseRegistry` exists at `clawteam/harness/phase_registry.py` as a pure in-memory registry that plugins populate via the new optional `HarnessPlugin.contribute_phases()` / `contribute_gates()` / `contribute_phase_roles()` hooks; calling `HarnessOrchestrator.__init__` with `phases=None` consults the registry and constructs `PhaseState.phases` from the plugin contributions — verified by a unit test that registers a test plugin contributing three phases and asserts `PhaseState.phases == [...plugin_phases]`.
  2. Phase-name collisions across plugins raise `ValueError` at registration time (not runtime) — verified by a test that registers two test plugins with overlapping phase names and asserts the exception.
  3. `SprintState` exists at `clawteam/sprint/state.py` as a pydantic v2 model with required fields (`sprint_id`, `goal`, `team`, `current_phase`, `phase_history`, `artifacts`, `participants`, `pending_question_ids`, `auto_advance`, `workspace_branch`, `created_at`) that round-trips through `file_locked()` atomic JSON persistence under `~/.clawteam/teams/<team>/sprints/<id>/state.json` — verified by a write-then-read test and a concurrent-writer test that confirms last-write-wins with no corruption.
  4. `InteractionGate` exists at `clawteam/harness/interaction_gate.py` as a `PhaseGate` subclass that returns `(False, "Open questions: ...")` when `sprint/<id>/questions/N.md` has no sibling `answers/N.md` and returns `(True, "")` otherwise — verified by a unit test that creates one question file, asserts gate fails, creates the answer file, asserts gate passes.
  5. Phase agents can write structured question markdown files with H3 per-question headings + numbered choices (or freeform fields), and human answer files support selecting an option or providing freeform reply — verified by a schema-parsing test over fixture question/answer pairs.
  6. Running the Phase 0 regression matrix after these additions continues to pass — every existing template spawns + advances + passes its existing tests with no new failures.

**Canonical refs**:
- research/ARCHITECTURE.md Pattern 1 (Phase machine as plugin-populated list) + Pattern 4 (InteractionGate mechanics)
- research/SUMMARY.md Phase 1 section
- research/PITFALLS.md Pitfall 14 (BC regression reinforced) + Pitfall 15 (additive-only contract)

**Upstream-PR status**: Core of the target upstream bundle. No gstack-specific logic lands here; this is the pluggability delta.

**Research flag**: NONE. Codebase already chose "open `str`" for `Phase`/`AgentRole`; plugin-registry patterns are well-established.

**Plans**: 5 plans

Plans:
- [x] 01-01-PLAN.md — PhaseRegistry + ReviewRouter Protocol + three optional HarnessPlugin hooks (CORE-01, CORE-02, INT-01)
- [x] 01-02-PLAN.md — SprintState pydantic model + file-locked atomic JSON persistence (CORE-04, INT-01)
- [x] 01-03-PLAN.md — InteractionGate subclass blocking on unanswered question files (CORE-04, INT-01, INT-02)
- [x] 01-04-PLAN.md — Question/Answer pydantic models + D-08 stdlib-only frontmatter round-trip (INT-01, INT-02)
- [x] 01-05-PLAN.md — HarnessOrchestrator consults PhaseRegistry + optional SprintState composition + BC regression guard (CORE-01, CORE-02)

---

### Phase 2: Sprint Engine, Evidence Gates & Theater/Drift/Deadlock Prevention

**Goal**: Land a single-sprint end-to-end runnable sprint engine that ships with evidence-checking gates, a cycle detector, the structured-response envelope protocol, artifact size caps, safety-rail primitives, and the sprint CLI (start/status/show/list/pause/resume) — because letting gameable gates, drift-prone messages, or deadlock-prone transports exist for even one demo means downstream data is contaminated.

**Depends on**: Phase 1 (requires `PhaseRegistry`, `SprintState`, `InteractionGate`).

**Requirements**: CORE-05, CORE-07, INT-06, SPRINT-01, SPRINT-02, SKILL-09, SAFETY-01, SAFETY-02, SAFETY-03, SAFETY-04, QUALITY-01, QUALITY-02, QUALITY-03, QUALITY-06, QUALITY-08, QUALITY-11, UX-02, UX-03, UX-04, UX-05, UX-09

**Success Criteria** (what must be TRUE):
  1. User can run `clawteam sprint start --team <name> --goal "add a dark-mode toggle"` against any team (existing or Phase-3 gstack) whose plugin contributes 7 phases, and a sprint record appears under `~/.clawteam/teams/<name>/sprints/<id>/state.json`; `clawteam sprint status <id>` shows current phase, assigned participants, pending-question count, and most-recent artifact; `clawteam sprint show <id>` prints full phase history; `clawteam sprint list --team <name>` lists all sprints with phase + status; every command also supports `--json` for machine-readable output.
  2. Attempting to advance from Think -> Plan by writing an empty `design-doc.md` is blocked by `EvidenceGate`: the gate validates that the doc contains all required sections (forcing questions, scope boundaries, success criteria) with non-stub content — verified by a replay test where a "TBD"-filled design-doc fails the gate and an evidence-full one passes. Test reports must reference a real test-runner output hash (gate re-runs pytest on the cited test IDs); ship notes must parse as structured markdown with a deploy URL field; review reports must cite real diff line ranges.
  3. Pausing a running sprint with `clawteam sprint pause <id>` writes a checkpoint that survives a full `HarnessOrchestrator` restart; running `clawteam sprint resume <id>` rehydrates `SprintState` and re-emits the last pending phase-transition event, returning the sprint to its pre-pause gate state — verified by an integration test that kills and restarts the orchestrator mid-sprint.
  4. Every agent turn across every role emits a structured response envelope with persona-identity header, step label, output-schema-conforming body, and explicit `{done: true|false}` termination signal — verified by a protocol-conformance test harness that rejects malformed envelopes. An agent attempting to echo a peer's voice for 8+ consecutive turns triggers a drift-regression alarm event on the EventBus.
  5. A synthetic back-and-forth loop between two agents on the same `(sender, recipient, topic)` hash exceeding 3 round-trips within a rolling window trips the transport-level cycle detector, breaks the cycle by escalating the topic to the AttentionQueue (Phase 7) or an `InteractionGate` (immediate), and emits an `agent_deadlock_detected` event — verified by a cycle-injection test.
  6. An agent turn that produces zero new artifact bytes and zero new AttentionQueue entries counts as a no-progress turn; two consecutive no-progress turns escalate to human via the `forced_progress_gate` — verified by a theater-simulation test where an agent merely echoes previous messages and the gate fires.
  7. Running `clawteam sprint status <id>` surfaces `artifact_delta_per_hour` and `token_per_useful_byte` as primary metrics; anomaly thresholds (e.g., tokens/byte > 100x rolling average) emit alarm events.
  8. `/careful`, `/freeze <path>`, `/guard`, `/unfreeze` are registered as harness-level primitives via `EventBus` hooks on file-write tool calls; an agent attempting `rm -rf /` receives a blocked-tool-call event with a destructive-command warning before execution; an agent attempting to write outside a `/freeze`-locked path receives a workspace-manager error — verified by safety-rail unit tests against `clawteam/workspace/manager.py`.
  9. Artifact writes per phase are capped by a configurable size budget (default 50 KB per artifact, 500 KB per phase); exceeding the cap triggers a compaction hook or a phase-level InteractionGate asking "prune what?" — verified by a size-cap stress test.
  10. Running the Phase 0 regression matrix after these additions continues to pass — existing templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) spawn + advance + pass their existing tests unchanged.

**Canonical refs**:
- research/ARCHITECTURE.md Pattern 2 (team-wide task queue) + EvidenceGate family
- research/PITFALLS.md Pitfalls 1 (persona drift), 2 (deadlock), 8 (gate gaming), 11 (theater) — all ship-blockers mitigated here; partial coverage of 3 (context exhaustion) via artifact caps and 6 (workspace conflicts) via hardening
- research/SUMMARY.md Phase 2 section
- codebase/ARCHITECTURE.md `PhaseRunner`, `ArtifactStore`, `EventBus` primitives

**Upstream-PR status**: Included in target upstream bundle. `EvidenceGate` supersedes (not replaces) `ArtifactRequiredGate`; existing templates continue to use the old gate; gstack opts into the new one via plugin choice.

**Research flag**: MEDIUM. EvidenceGate schemas per artifact type benefit from a quick research pass at plan time — well-documented patterns exist (Three Dots Labs replay-verification, deterministic side-channels) but the per-artifact schema detail is worth sharpening. Cycle-detector implementation has published precedent (Paperclip #390).

**Plans**: 13 plans

Plans:
- [x] 02-01-PLAN.md — 8 Phase 2 event dataclasses + contribute_evidence_schemas plugin hook (SPRINT-01, SAFETY-01..04, QUALITY-02, QUALITY-11)
- [x] 02-02-PLAN.md — TurnEnvelope pydantic + stdlib YAML frontmatter parser + TeamMessage optional envelope fields (SKILL-09, QUALITY-01)
- [x] 02-03-PLAN.md — SprintState additive fields: turn_counters + artifact caps + status Literal + suppressed_topics (CORE-07, INT-06, QUALITY-03, QUALITY-11)
- [x] 02-04-PLAN.md — EvidenceSchemaRegistry singleton + ArtifactFrontmatterBase pydantic v2 base (SPRINT-01, SPRINT-02, QUALITY-08)
- [x] 02-05-PLAN.md — FreezeRegistry singleton + FrozenPathError + append-only freeze_audit.jsonl (SAFETY-02, SAFETY-04, QUALITY-06)
- [x] 02-06-PLAN.md — ArtifactStore.write hook chain: size cap + BeforeFileWrite emit + ArtifactTooLargeError (QUALITY-03, QUALITY-06, SAFETY-02)
- [x] 02-07-PLAN.md — EvidenceGate 4-check protocol + test_verify_cache + deploy_url HEAD probe (SPRINT-02, QUALITY-08, QUALITY-03)
- [x] 02-08-PLAN.md — Cycle detector in DefaultRoutingPolicy + envelope validation hook in Transport.deliver (QUALITY-01, QUALITY-02, SKILL-09)
- [x] 02-09-PLAN.md — forced_progress_gate + turn_counter dedupe wiring + progressSignal field (QUALITY-11, QUALITY-02)
- [x] 02-10-PLAN.md — Safety-rail EventBus subscribers + MCP _tool BeforeToolCall + WorkspaceManager BeforeFileWrite + clawteam guard CLI sub-app (SAFETY-01..04)
- [x] 02-11-PLAN.md — SprintConductor: start/advance/pause/resume/list/resolve + three-layer cap override (CORE-05, CORE-07, INT-06)
- [x] 02-12-PLAN.md — clawteam sprint CLI sub-app: start/status/show/list/pause/resume with uniform --json envelope (UX-02, UX-03, UX-04, UX-05, UX-09)
- [x] 02-13-PLAN.md — Phase 0 regression matrix hard-green gate + Phase 2 end-to-end integration + REQ-ID traceability audit + human-verify ship checkpoint (all 21 REQs)

---

### Phase 3: Gstack Team Template & Methodology Port

**Goal**: Ship the actual product surface — `gstack.toml` with 11 agents, `GstackSprintPlugin` wiring them to the 7-phase sprint engine, and per-role methodology prompts ported from the pure-rubric gstack skills (`/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/retro`, `/plan-design-review`, `/design-review`, `/plan-devex-review`, `/devex-review`, `/review`, `/qa-only`, `/cso`) — so a user can run one `clawteam team spawn gstack --name <name>` and immediately see a coherent 11-specialist team with methodology baked into every role prompt.

**Depends on**: Phase 2 (requires sprint engine, evidence gates, structured-response envelope, safety-rail primitives).

**Requirements**: TEAM-01, TEAM-02, TEAM-03, TEAM-04, TEAM-05, SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06, SKILL-07, SKILL-08, SPRINT-06, UX-01, UX-07

**Success Criteria** (what must be TRUE):
  1. User can run `clawteam team spawn gstack --name myteam --model-profile balanced` and `clawteam team show myteam` shows exactly 11 agents — pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre — each with its own persistent worktree "desk" under `~/.clawteam/teams/myteam/agents/<role>/` and a distinct role-prompt file; each agent spawned via the existing `clawteam/spawn/` backend registry.
  2. `GstackSprintPlugin` registers 7 phases (Think -> Plan -> Build -> Review -> Test -> Ship -> Reflect) via `PhaseRegistry` when the plugin is loaded; these phases appear only for the `gstack` template, and spawning any existing template (`software-dev`, etc.) continues to use its original phase set with no gstack phase leakage — verified by a cross-template isolation test.
  3. Each of the 11 role prompts contains the per-role methodology port, verified by a golden-prompt test against fixtures: pm prompt includes all 6 office-hours forcing questions and the challenge-framing instruction; ceo prompt includes the 4 plan-ceo-review modes (Expansion/Selective/Hold/Reduction) with decision output schema; eng-mgr prompt includes architecture lock + data-flow diagrams + edge-case matrix + test-plan + per-person retro breakdown; designer prompt includes the 0-10 rubric + AI-slop detection checklist + interactive-per-dimension instruction + design-system research prompt; dx-lead prompt includes persona exploration + TTHW benchmarking + friction tracing; reviewer prompt includes production-bug detection + iron-law root-cause (no fix without investigation; halt after 3 failed hypotheses); qa prompt includes bug-fix + regression-test loop with `/qa-only` suppression variant; security prompt includes OWASP Top 10 + STRIDE checklist + 17 false-positive exclusions + 8/10+ confidence gate.
  4. ceo is configured as the team leader in `gstack.toml`: only ceo can call `SprintConductor.advance_phase()`; ceo's role prompt explicitly owns scope decisions + phase-transition calls + consulting human via InteractionGate on scope cuts.
  5. A sprint completing the Reflect phase triggers the eng-mgr role to write `retro.md` AND invoke `/learn` against the team-shared memory store (Phase 6 implementation); until Phase 6 ships, the `/learn` call is a stub that writes to a placeholder file with a feature-flag log entry — verified by a sprint-completion integration test.
  6. `clawteam team show myteam` displays a dashboard: member list (all 11 roles + current status), memory highlights (most-recent `/learn` entries, placeholder until Phase 6), active sprint progress bars with phase indicator, and a per-agent token/cost rollup (placeholder values until Phase 7 full observability lands).
  7. Running the Phase 0 regression matrix after these additions continues to pass — no existing template is affected by `gstack.toml` shipping or `GstackSprintPlugin` being importable (but not loaded for other templates).

**Canonical refs**:
- research/ARCHITECTURE.md Pattern 5 (TeamMemory layered) + GstackSprintPlugin wiring
- research/FEATURES.md Differentiators #1 (11-role pre-configured team) + #2 (7-phase sprint as product)
- research/PITFALLS.md Pitfall 7 (skill port collapse — classified at Phase 2 port-audit; rubric-pure skills land here, interactive skills deferred to Phase 4)
- PROJECT.md Key Decisions row 1 (11-agent roster) + row 3 (team is persistent, sprint is transient)

**Upstream-PR status**: Fork-only. This is the first phase with gstack-specific content. Everything here lives in `GstackSprintPlugin` + `gstack.toml`; delete those two assets and the rest of the codebase continues to run.

**Research flag**: HIGH (partial — the interactive-skill subset is deferred to Phase 4). Per `research/SUMMARY.md` Phase 3 section and Gaps to Address #2: "We don't yet have a source of native gstack golden traces. Options: (a) run native gstack against a fixture repo and record transcripts, (b) derive expected shapes from the skill markdown itself, (c) co-design with Garry Tan." **Recommend running `/gsd-research-phase 3` before implementation** to settle: per-persona role-reassertion field schemas for the structured-response envelope; golden-trace sourcing strategy; per-role prompt length budget.

**Plans**: TBD

Plans:
- [x] 03-01: TBD (outlined during `/gsd-plan-phase 3`)

---

### Phase 4: Interactive State Machines, Smart Review Routing & Cross-Agent Verification

**Goal**: Port the interactive/Socratic gstack skills (`/office-hours`, `/design-consultation`, `/investigate`) as proper multi-turn state machines (not one-shot prompt bakings); ship `SmartReviewRouter` with SHA-pinned multi-signal routing; enforce reviewer decorrelation and cross-agent verification; wire the Ship-phase human-approval gate — because these are the "HIGH research-flag" slices per `research/SUMMARY.md` and they collectively determine whether the Review/Investigate/Ship loops feel real or feel like generic Claude pretending.

**Depends on**: Phase 3 (requires 11-agent team + methodology prompts + plugin surface).

**Requirements**: SPRINT-03, SPRINT-04, SPRINT-05, SAFETY-05, QUALITY-07, QUALITY-09, QUALITY-13

**Success Criteria** (what must be TRUE):
  1. `/office-hours` runs as a multi-turn state machine owned by pm — issuing the 6 forcing questions one at a time (not batched), persisting per-question state between turns, and preserving per-question interactivity across agent restarts — verified by a golden-trace comparison against a fixture transcript of native gstack `/office-hours` showing matching turn count and Q&A branch structure.
  2. `/design-consultation` and `/investigate` similarly run as state machines with per-dimension (design) or per-hypothesis (investigate) progression; `/investigate` auto-applies `/freeze` to the module under investigation for the duration of the investigation and releases on completion.
  3. Entering the Review phase on a sprint whose diff touches UI files (e.g., `src/components/*.tsx`) automatically pulls the designer agent into the review participants; touching `src/auth/` or `**/crypto/**` automatically pulls security; touching `app/api/**` or `package.json` pulls dx-lead; reviewer (staff eng) always participates — verified by a routing golden test over at least 8 fixture diffs including adversarial cases (renamed files, test files that import crypto, no-op whitespace-only diffs).
  4. Every reviewer participant records the diff SHA being reviewed in its report frontmatter; if the sprint branch HEAD advances before the review completes, a mid-review-thrash event fires and the reviewer chooses between extending the review to the new SHA or marking the prior review as superseded — verified by a mid-review-push integration test.
  5. Parallel reviewers receive distinct decorrelated system prompts (reviewer=staff-eng-cross-cutting, security=threat-model-first, designer=rubric-first, dx-lead=friction-first) and run without access to peer drafts until the synthesis step; `reviewer` (staff eng) aggregates into a single `review-report.md`; the aggregated report passes the phase gate, not individual reports; agreement-rate > 90% across parallel reviewers triggers a sycophancy-cascade alarm event — verified by a decorrelation test measuring disagreement rate across a fixture panel.
  6. Cross-agent verification gates are wired: qa must verify engineer's `test-report.md` references real pytest output hashes; reviewer must verify designer's `design-doc.md` covers all 6 forcing-question answers — verified by cross-verification integration tests on fixture artifacts.
  7. Advancing from Test -> Ship is blocked by an `InteractionGate` subclass that ignores any `auto_advance: true` team config (production blast radius); the human must explicitly edit a `ship-approval.md` artifact or run `clawteam sprint approve <id> --phase ship`, regardless of other config — verified by an auto-advance-override test.

**Canonical refs**:
- research/ARCHITECTURE.md Pattern 6 (SmartReviewRouter rules-first) + reviewer-decorrelation notes
- research/PITFALLS.md Pitfalls 7 (interactive state machines), 9 (review routing SHA-pinning + multi-signal), 13 (sycophancy cascade decorrelation); reinforces 8 (gate gaming) via cross-agent verification; SPRINT-05 forces the always-human ship approval
- research/SUMMARY.md Phase 3 research-flag recommendation applies to this phase's state-machine work
- PROJECT.md Key Decisions row 6 (parallel reviewers + reviewer aggregates)

**Upstream-PR status**: Fork-only. `SmartReviewRouter` is generic substrate (could upstream eventually), but the per-persona decorrelation prompts and the specific rule config live in `gstack.toml`.

**Research flag**: HIGH. Depends on the Phase 3 research pass having settled: golden-trace sourcing; per-persona role-reassertion field schema; adversarial-diff handling rules. Re-run `/gsd-research-phase 4` if Phase 3's research outputs don't sufficiently cover the state-machine schema per interactive skill.

**Plans**: 14 plans

Plans:
- [ ] 04-01-PLAN.md — Wave 0 prep: resolve research plan-prep verifications (A4/A5/A7/A9 + fnmatch glob + spawn bridge + D-18 baseline)
- [ ] 04-02-PLAN.md — SprintState.review_sha field + MidReviewThrash + SycophancyCascadeDetected event types
- [ ] 04-03-PLAN.md — CrossAgentVerificationGate base class + VerificationPair pydantic model
- [ ] 04-04-PLAN.md — ShipApprovalGate (HumanApprovalGate variant — SPRINT-05 always-human)
- [ ] 04-05-PLAN.md — HarnessPlugin.contribute_verification_pairs + contribute_gates hooks + PluginManager accessors (revised: Task 2 adds contribute_gates wiring)
- [x] 04-06-PLAN.md — GstackReviewRouter + [[template.review.rules]] TOML extension (completed 2026-04-21)
- [ ] 04-07-PLAN.md — OfficeHoursState machine (pm / /office-hours)
- [ ] 04-08-PLAN.md — DesignConsultationState machine (designer / /design-consultation)
- [ ] 04-09-PLAN.md — InvestigateState machine (reviewer / /investigate) + FreezeRegistry wiring
- [x] 04-10-PLAN.md — Review-phase dispatch: parallel reviewers + SHA-pin + thrash + sycophancy events (revised: Task 3 wires plugin gates + CrossAgentVerificationGate into _build_gate_chain) (completed 2026-04-21)
- [ ] 04-11-PLAN.md — GstackSprintPlugin extensions: contribute_review_routers + contribute_verification_pairs + contribute_gates + decorrelation prompts
- [x] 04-12-PLAN.md — clawteam sprint approve CLI subcommand (writes ship-approval.md) (completed 2026-04-21)
- [x] 04-13-PLAN.md — Adversarial routing golden tests (8 fixture diffs) + consolidated state-machine goldens (completed 2026-04-21)
- [x] 04-14-PLAN.md — REVISION: D-18 marker cleanup + mid-review-push integration (closes SC #4) + ISS-06 test tightening (completed 2026-04-21)

---

### Phase 5: Tool-Heavy Skills (Ship, SRE, Codex)

**Goal**: Port the tool-heavy gstack skills that give engineer/shipper/sre/reviewer actual external-tool surfaces: `/codex` cross-model second opinion, `/ship` + `/land-and-deploy` + `/document-release` ship pipeline, `/canary` + `/benchmark` + `/setup-deploy` SRE pipeline. These are invokable ClawTeam skill modules (not prompt baking), binding to specific roles declared in `gstack.toml`.

**Depends on**: Phase 3 (requires 11-agent team + plugin surface so skills can bind to roles); Phase 4 optional for human-gated Ship (SPRINT-05 already in place).

**Requirements**: SKILL-13, SKILL-14, SKILL-15, SKILL-16, SKILL-17, SKILL-18, SKILL-19

**Success Criteria** (what must be TRUE):
  1. `engineer` or `reviewer` can invoke `/codex` through the existing `NativeCliAdapter` to get an independent OpenAI Codex CLI opinion in three modes (review/adversarial/consultation); the result lands as a `codex-review.md` artifact tagged with the mode; when the `codex` CLI binary is missing, the skill emits a setup hint ("install codex: `npm install -g @openai/codex`") and returns a structured `SkillUnavailable` error instead of crashing — verified by a skill-invocation test with and without the `codex` binary present.
  2. `shipper` invoking `/ship` on a Build-phase-complete sprint runs: sync main, run tests (bootstrapping a test framework if none exists on the branch), audit coverage against a configurable threshold, push the branch, open a PR — producing `ship-notes.md` with a PR URL; auto-invokes `/document-release` to cross-reference the diff against doc files and update stale ones.
  3. `shipper` invoking `/land-and-deploy` on a merged PR waits for CI green, deploys via the `gstack.toml`-configured deploy target (or a stub if `/setup-deploy` hasn't been run), verifies production health, and emits a `deploy.md` artifact referencing the deploy URL — the Ship-phase EvidenceGate validates this deploy URL dereferences (HEAD request returns 2xx or 3xx) before allowing Reflect to start.
  4. `sre` invoking `/canary` on a freshly deployed build runs the post-deploy monitoring loop (console errors, perf regressions against a baseline) for a configurable window and emits `canary-report.md` with regression flags.
  5. `sre` invoking `/benchmark` runs Core Web Vitals + page-load baselines against before/after deploys on every PR; results land in `benchmark-report.md` with a regression threshold configured in `gstack.toml`.
  6. `sre` invoking `/setup-deploy` on a greenfield project runs the one-time deployment configuration wizard and writes the result to `gstack.toml`'s `[deploy]` block — idempotent on re-run.
  7. All six skills have per-skill tests covering happy-path, missing-tool, and adversarial-input cases; skill invocation through MCP tool call completes round-trip with structured responses.

**Canonical refs**:
- research/FEATURES.md P1 list for `/codex`, `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy`
- research/SUMMARY.md Phase 3 section "Tool-heavy skill ports for Build/Ship/Test/SRE" — grouped here as its own phase in fine granularity
- research/PITFALLS.md Pitfall 8 (gate gaming) — `/ship` must emit a real deploy URL for EvidenceGate to dereference

**Upstream-PR status**: Fork-only. Tool-heavy skills are gstack-specific; they bind to `gstack.toml` role assignments.

**Research flag**: LOW. Each skill has a clear gstack-native behavior reference; porting is implementation work, not new design.

**Plans**: 10 plans

Plans:
- [x] 05-01-PLAN.md — Wave 0 substrate: SkillRegistration + SkillDispatcher + contribute_skills hook + invoke_native_cli wrapper + 5 doctor entries + TemplateDef [ship]/[deploy]/[canary]/[benchmark] blocks — completed 2026-04-21 (see 05-01-SUMMARY.md)
- [x] 05-02-PLAN.md — Wave 1 schemas + events: DeployNotes + CanaryReport + BenchmarkReport + CodexReview pydantic schemas + ShipNotes Phase 5 extension + 2 HarnessEvent dataclasses (DeployRegressionDetected, WebVitalRegressionDetected) — completed 2026-04-21 (see 05-02-SUMMARY.md; 18 new tests; 80min; 3 tasks TDD-disciplined)
- [x] 05-03-PLAN.md — Wave 2 /codex skill (SKILL-13): engineer/reviewer, 3 modes, adversarial-input safety via shell=False + list argv — completed 2026-04-21 (see 05-03-SUMMARY.md; 9 tests; 25min)
- [x] 05-04-PLAN.md — Wave 2 /ship skill (SKILL-14): shipper, 5-step pipeline (sync_main → run_tests → audit_coverage → push → open_pr) + test bootstrap on missing tests — completed 2026-04-21 (see 05-04-SUMMARY.md)
- [x] 05-05-PLAN.md — Wave 2 /setup-deploy wizard (SKILL-19): sre, questionary-backed interactive wizard with shell-metachar input validation + idempotent gstack.toml [deploy] block write — completed 2026-04-21 (see 05-05-SUMMARY.md; 11 tests; 20min; 1 task TDD-disciplined)
- [x] 05-06-PLAN.md — Wave 3 /land-and-deploy (SKILL-15): shipper, CI wait + provider deploy (vercel/netlify/fly/custom) + health probe with exponential backoff — completed 2026-04-21 (see 05-06-SUMMARY.md; 13 new tests; 25min; 1 task TDD-disciplined)
- [x] 05-07-PLAN.md — Wave 3 /document-release (SKILL-16) + /ship auto-invoke wiring: shipper, diff-vs-docs stale-ref detector with InteractionGate human-gate for non-trivial writes — completed 2026-04-21 (see 05-07-SUMMARY.md)
- [x] 05-08-PLAN.md — Wave 4 /canary skill (SKILL-17): sre, HTTP polling + regression evaluation + DeployRegressionDetected event emit + Playwright lazy-import — completed 2026-04-21 (see 05-08-SUMMARY.md)
- [x] 05-09-PLAN.md — Wave 4 /benchmark skill (SKILL-18): sre, Lighthouse primary + curl fallback + baseline JSON write + WebVitalRegressionDetected event emit — completed 2026-04-21 (see 05-09-SUMMARY.md; 12 tests; 25min)
- [x] 05-10-PLAN.md — Wave 5 integration: end-to-end /ship→/land-and-deploy→/canary artifact chain + 21-ID D-15 adversarial matrix + 7-skill registration coverage assertion — completed 2026-04-22 (see 05-10-SUMMARY.md; 29 tests; 30min; 4 tasks)

---

### Phase 6: Browser Skills, Design Pipeline & Team Memory

**Goal**: Deliver the two biggest user-facing differentiators that make the "team that learns your taste" narrative real: the browser pipeline (`/browse`, `/open-gstack-browser`, `/setup-browser-cookies`, `/design-shotgun`, `/design-html`) via a `clawteam[browser]` optional extra (Playwright), and the layered `/learn` team memory store with provenance + decay + human gate on high-impact entries.

**Depends on**: Phase 3 (per-role skill binding + designer owning `/design-shotgun`, `/design-html`); Phase 4 (InteractionGate needed for high-impact memory human gate via QUALITY-10).

**Requirements**: MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07, SKILL-10, SKILL-11, SKILL-12, QUALITY-10

**Success Criteria** (what must be TRUE):
  1. `pip install 'clawteam[browser]' && playwright install chromium` installs `playwright>=1.58,<2`; on a machine without the extra, `designer`/`engineer`/`qa`/`dx-lead` invoking `/browse` or `/open-gstack-browser` or `/setup-browser-cookies` receives a structured `SkillUnavailable` error with the exact install commands — verified by feature-detection test with and without the extra.
  2. `designer` invoking `/design-shotgun` generates multiple mockup variants (configurable count, default 4), renders them to a comparison board as screenshots/HTML, and supports iterative refinement; the skill writes to the designer's per-agent `/learn` memory scope a taste-observation entry per iteration citing which variant the user picked and why.
  3. `designer` invoking `/design-html` takes a chosen mockup and emits production HTML following the Pretext pattern, auto-detecting the project's framework (React/Svelte/Vue/plain HTML) from `package.json` + import analysis.
  4. `TeamMemoryStore` exists under `~/.clawteam/teams/<team>/memory/` with two tiers: `memory/team/` (shared) and `memory/agents/<role>/` (private); writes are append-only JSONL with per-entry frontmatter containing `id`, `author`, `sprint_id`, `phase`, `timestamp`, `tags`, `evidence` (path:line or artifact ref), `confidence`, and `learned_from` (one of `user|artifact|self-inferred`).
  5. `clawteam memory search <query> [--tag foo] [--scope shared|role]` retrieves entries via grep-first keyword + tag match, ranked by recency × provenance-weight (user-grounded > artifact-grounded > self-inferred); entries without evidence citation are flagged and ranked below evidence-bearing ones, not blocked — verified by a retrieval ranking test.
  6. Writing a memory entry tagged `impact:high` or to `memory/team/decisions/` triggers an `InteractionGate`-backed human confirmation flow (a `memory-confirm-<id>.md` question file lands in the current sprint's questions dir); the entry is staged, not committed, until the human answers — verified by a high-impact-write integration test.
  7. Memory entries inherit a per-tag TTL (patterns: 90 days; preferences: indefinite; incidents: 180 days); expired entries rank below unexpired on retrieval but are never auto-deleted — verified by a decay-ranking test.
  8. Adding a new entry that contradicts an existing one (same tag, opposite assertion) triggers a conflict-detection event; the writer sees "conflicts with memory/team/X.md entry Y" and must resolve via an explicit `/learn --resolve` invocation — verified by a conflict-injection test.
  9. `clawteam memory review` lists recent entries with provenance flags; `clawteam memory purge <id>` audits and removes an entry, writing a purge-event to the team event log — both commands support `--json`.
  10. Per-team namespace isolation: no agent on team A can read `memory/team/` or `memory/agents/*` entries from team B — verified by a cross-team isolation test.

**Canonical refs**:
- research/STACK.md "Playwright as optional extra" + "grep-first team memory, embeddings in v2"
- research/ARCHITECTURE.md Pattern 5 (TeamMemory layered) + `/learn` skill rules
- research/PITFALLS.md Pitfall 10 (memory poisoning — ship-blocker if `/learn` ships with write path) — all preventions from this pitfall land here; Pitfall 3 (context exhaustion) partially mitigated via MemGPT-tiered memory design
- research/SUMMARY.md Phase 4 section + Gaps to Address #3 (memory poisoning defense tradeoffs)

**Upstream-PR status**: Fork-only. Browser skills are gstack-specific. `TeamMemoryStore` is generic substrate and could upstream eventually under `clawteam/memory/`, but the `/learn` UX is currently gstack-scoped.

**Research flag**: MEDIUM. Memory provenance + decay schema benefits from a planning pass per `research/SUMMARY.md` — MINJA/MemoryGraft/SSGM papers describe the problem but concrete schema choice needs a product decision. Browser skills use well-documented Playwright patterns. **Consider `/gsd-research-phase 6` if the memory write-path preventions feel under-specified at plan time.**

**Plans**: 10 (outlined via `/gsd-plan-phase 6`; Wave 0 substrate landed 2026-04-22)

Plans:
- [x] 06-01: Wave 0 substrate — pyproject [browser] extra + playwright_available() + 3 new HarnessEvents + MemoryConfig/DesignShotgunConfig/BrowserConfig TemplateDef sub-blocks (MEM-01/02, SKILL-10/11/12, QUALITY-10 substrate) — **COMPLETE 2026-04-22**
- [x] 06-02: Wave 1 memory substrate — MemoryEntry pydantic + TeamMemoryStore write/list/prune + cross-team isolation (MEM-01, MEM-02, D-04, D-05, D-15) — **COMPLETE 2026-04-22**
- [x] 06-03: Wave 1 memory search + ranking + decay — decay_factor (per-tag TTL, MEM-07 floor) + rank (recency × provenance × decay) + search (grep-safe keyword) (MEM-03, MEM-05, MEM-07, D-06) — **COMPLETE 2026-04-22**
- [x] 06-04: Wave 1 browser substrate — Playwright adapter + session factory + per-domain cookies store (SKILL-10 substrate, D-02 no-leak invariant) — **COMPLETE 2026-04-22**
- [x] 06-05: Wave 2 /browse skill (SKILL-10, headless URL+actions) — **COMPLETE 2026-04-22**
- [x] 06-06: Wave 2 /open-gstack-browser (SKILL-10, headed Chromium with cookies) — **COMPLETE 2026-04-22**
- [x] 06-07: Wave 2 /setup-browser-cookies (SKILL-10, questionary wizard) — **COMPLETE 2026-04-22**
- [x] 06-08: Wave 3 /design-shotgun (SKILL-11, multi-turn state machine + taste-memory write) — **COMPLETE 2026-04-22**
- [x] 06-09: Wave 3 /design-html (SKILL-12, framework detection + source emission) — **COMPLETE 2026-04-22**
- [x] 06-10: Wave 3 /learn skill + clawteam learn CLI (shared handler per D-08) — **COMPLETE 2026-04-22** (high-impact gate + conflict detection + backfill scanner deferred to Plan 06-11)

**UI hint**: yes

---

### Phase 7: Parallel Sprints, AttentionQueue UX & Cost Controls

**Goal**: Unlock the parallel-sprints force multiplier by landing `SprintConductor` concurrency caps, dormancy discipline, rate-limit-aware scheduling, `clawteam attend` with typed-priority queue + digest mode + `--auto-accept-reversible`, the team cost dashboard with 50/80/100% alarms and model fallback ladder, and sprint pause/resume at scale — because parallel sprints compound every earlier risk (resource blowup + attention fatigue + cost blowup are all nonlinear in sprint count).

**Depends on**: Phase 3 (team + plugin needed to exercise multi-sprint); Phase 4 (routing + cross-agent verification needed under load); Phase 6 (memory + `/learn` present under the load test). Safe to plan in parallel with Phase 5 if capacity allows.

**Requirements**: CORE-06, INT-03, INT-04, INT-05, QUALITY-04, QUALITY-05, QUALITY-12, UX-06

**Success Criteria** (what must be TRUE):
  1. One `gstack` team can hold 10 concurrent sprints; running `clawteam sprint list --team <name>` shows all 10 with their individual phase states; no race conditions on the team-level TaskStore, memory store, or attention queue — verified by a 10-sprint load-test integration test under a 5-minute duration cap and a 4 GB RAM budget.
  2. `SprintConductor` caps concurrent active sprints via `asyncio.Semaphore(max_concurrent_sprints)` (default 10, user-configurable per team); sprints beyond the cap sit in a `queued` state and auto-advance when capacity frees; an `asyncio.Semaphore(max_tasks_per_agent)` (default 1) serializes per-agent dispatch — verified by an over-cap test that asserts the 11th sprint enters `queued`.
  3. Active-agent slot pool caps concurrent active agents at N (default 6); idle agents sleep-poll (no Claude keepalive burn); a Think phase with only pm + ceo active doesn't wake engineer/shipper/sre — verified by an agent-state-sampling test over a 10-sprint run showing active-agent count never exceeds the cap.
  4. Running `clawteam attend` surfaces the top-N pending questions across all of the user's teams and sprints, priority-sorted by `URGENCY + BLOCKING + AGE_BOOST + EXPLICIT_TAG` (additive); the CLI opens the chosen question in `$EDITOR`; on save, the gate unblocks and the next priority question is offered — verified by a 10-sprint attention-queue test.
  5. `clawteam attend --summary` shows the digest view ("4 sprints stalled >2h, 1 CRITICAL, 2 reversible auto-accept candidates") rolling related questions into single decisions; `clawteam attend --auto-accept-reversible` applies default-accept-with-TTL to questions flagged `reversibility: easy`.
  6. With the optional `watchdog` package installed, the attention queue auto-refreshes on filesystem events the moment an answer file is saved; without `watchdog`, the queue falls back to a 2-second polling interval — verified by a watchdog-with/without test.
  7. `clawteam team show <name>` displays a cost dashboard: per-agent token usage, per-sprint cost rollup with Opus/Sonnet/Haiku breakdown, cache hit rate, and 50/80/100%-of-budget alarms; when 80% of the configured budget is reached, further agent invocations prefer cached prompts and downgrade to the model fallback ladder (Opus -> Sonnet -> Haiku) with a flagged note per invocation — verified by a budget-exhaustion test.
  8. Role prompts are cached per session (90% discount on repeat reads), team memory core is cached per team, per-sprint artifacts are cached per sprint; cache hit rate > 50% on a steady-state 10-sprint run — measured in the load test.
  9. Rate-limit-aware scheduling: when Anthropic TPM is saturated, new phase starts queue behind in-flight work instead of erroring; pause/resume across rate-limit windows is seamless — verified by a mock-rate-limiter test.
  10. Disk-budget alarm per team (default 5 GB soft, 10 GB hard) + zombie-worktree auto-GC cleans up dead worktrees older than 30 days — verified by a disk-budget-stress test.

**Canonical refs**:
- research/ARCHITECTURE.md Pattern 2 (team-wide task queue + semaphore caps) + Pattern 3 (AttentionQueue priority scoring)
- research/PITFALLS.md Pitfalls 4 (resource blowup), 5 (attention fatigue), 12 (cost blowup), 16 (resume brittleness); reinforces 1 (drift regression alarm in `team show`)
- research/SUMMARY.md Phase 5 section + Gaps to Address #4 (cost-control default aggressiveness)
- research/STACK.md "questionary + rich — already in ClawTeam" for `attend` UX

**Upstream-PR status**: Fork-only. `SprintConductor` and `AttentionQueue` are generic substrates (could upstream eventually under `clawteam/sprint/` and `clawteam/attention/`), but their defaults and policies are gstack-tuned for now.

**Research flag**: MEDIUM. Anthropic prompt-caching + rate-limit backoff have clear docs; attention-queue digest-mode UX benefits from a quick iteration with real users (post-Phase 3 dogfooding).

**Plans**: 9 plans

Plans:
- [x] 07-01-wave0-substrate: pyproject [attend] + attention/cost/rate_limit packages + 6 events + SprintState.queue_status + TemplateDef sub-blocks
- [x] 07-02-conductor-concurrency: SprintConductor semaphores + queue_status gate + RateLimitMonitor — completed 2026-04-22 (see 07-02-SUMMARY.md)
- [x] 07-03-attention-queue: AttentionQueue + AttentionItem + priority scoring — completed 2026-04-22 (see 07-03-SUMMARY.md)
- [x] 07-04-attend-cli: clawteam attend + watchdog auto-refresh + digest mode — completed 2026-04-22 (see 07-04-SUMMARY.md)
- [x] 07-05-cost-tracker: CostTracker + invoke wrapper hooks + BudgetAlarm emission — completed 2026-04-22 (see 07-05-SUMMARY.md)
- [x] 07-06-cost-fallback-cache: model fallback ladder + cache tracker — completed 2026-04-22 (see 07-06-SUMMARY.md)
- [x] 07-07-dashboard-team-show: cost dashboard in clawteam team show — completed 2026-04-22 (see 07-07-SUMMARY.md)
- [ ] 07-08-zombie-worktree-gc: doctor --gc + disk-budget alarms
- [ ] 07-09-integration-ten-sprint-load: 10-sprint load test

**UI hint**: yes

---

## Progress

**Execution Order:**
Phases execute in numeric order: 0 -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7. Any urgent insertion becomes a decimal phase (e.g., 2.1) and slots in between integer phases. Phase 5 and Phase 6 have independent dependencies on Phase 3; if capacity permits, they may be planned in parallel (`parallelization: true` per config), but final sequencing is per `/gsd-plan-phase` output.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 0. Foundation & Upstream RFC | 0/TBD | Not started | - |
| 1. Core Harness Extensions | 0/5 | Not started | - |
| 2. Sprint Engine & Theater/Drift/Deadlock Prevention | 0/13 | Not started | - |
| 3. Gstack Team Template & Methodology Port | 0/TBD | Not started | - |
| 4. Interactive State Machines, Review Routing & Verification | 0/TBD | Not started | - |
| 5. Tool-Heavy Skills (Ship, SRE, Codex) | 0/TBD | Not started | - |
| 6. Browser Skills, Design Pipeline & Team Memory | 8/10 | In Progress (Wave 3) | - |
| 7. Parallel Sprints, AttentionQueue UX & Cost Controls | 6/9 | In Progress (Wave 4 complete — cost tracker + fallback + cache tracker live) | - |

## Critical Path

The minimum sequence that delivers a demonstrable end-to-end v1 product:

```
0 (foundation)
 -> 1 (core extensions)
 -> 2 (single-sprint engine with evidence + theater prevention)
 -> 3 (gstack team + methodology — product surface exists)
 -> 4 (interactive skills + routing + ship-gate — product surface works end-to-end)
 -> 7 (parallel sprints — the marketing hook: "run 10 sprints on one team")
```

Phases 5 (tool-heavy skills) and 6 (browser + memory) are critical-path-adjacent: without Phase 5, `shipper` and `sre` have no external-tool hooks and the Ship-phase EvidenceGate can't dereference a real deploy URL. Without Phase 6, the "team learns your taste" narrative (memory) + flagship visual iteration (`/design-shotgun`) are missing. Both are required for v1.0 shipping; only the parallel-sprints marketing narrative (Phase 7) gates on the concurrency + cost work.

## Coverage

Every v1 requirement from `.planning/REQUIREMENTS.md` maps to exactly one phase. Full traceability is maintained in `REQUIREMENTS.md § Traceability`.

| Phase | Requirements Mapped |
|-------|---------------------|
| 0 | CORE-03, TEAM-06, QUALITY-14, QUALITY-15, UX-08 (5) |
| 1 | CORE-01, CORE-02, CORE-04, INT-01, INT-02 (5) |
| 2 | CORE-05, CORE-07, INT-06, SPRINT-01, SPRINT-02, SKILL-09, SAFETY-01, SAFETY-02, SAFETY-03, SAFETY-04, QUALITY-01, QUALITY-02, QUALITY-03, QUALITY-06, QUALITY-08, QUALITY-11, UX-02, UX-03, UX-04, UX-05, UX-09 (21) |
| 3 | TEAM-01, TEAM-02, TEAM-03, TEAM-04, TEAM-05, SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06, SKILL-07, SKILL-08, SPRINT-06, UX-01, UX-07 (16) |
| 4 | SPRINT-03, SPRINT-04, SPRINT-05, SAFETY-05, QUALITY-07, QUALITY-09, QUALITY-13 (7) |
| 5 | SKILL-13, SKILL-14, SKILL-15, SKILL-16, SKILL-17, SKILL-18, SKILL-19 (7) |
| 6 | MEM-01, MEM-02, MEM-03, MEM-04, MEM-05, MEM-06, MEM-07, SKILL-10, SKILL-11, SKILL-12, QUALITY-10 (11) |
| 7 | CORE-06, INT-03, INT-04, INT-05, QUALITY-04, QUALITY-05, QUALITY-12, UX-06 (8) |

**Total mapped:** 80 / 80 v1 requirements (100%). No orphaned requirements. No duplicates.

---

*Roadmap created: 2026-04-15*
*Granularity: fine*
*Milestone: v1.0 (hire-your-team + parallel-sprint gstack integration)*
