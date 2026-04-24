# ClawTeam-gstack Milestones

Historical record of shipped versions.

---

## v1.1 — Reliability (in progress)

**Started:** 2026-04-24
**Phases planned:** 5 (Phase 8-12) | **Requirements:** 14 | **Status:** Ready to plan Phase 8

### Why this milestone

v1.0 shipped a feature-complete 11-agent substrate but post-close UAT revealed that `clawteam go "build X"` doesn't reliably coordinate agents to produce a working X. Six rounds of whack-a-mole bug fixing after v1.0 close surfaced three architectural root causes that no individual patch could fix:

- **Class A — state machine has no teeth.** `EvidenceGate(artifact_names=[])` short-circuits to True because `gstack.toml` never registers artifact types per phase; every `sprint advance` passes regardless of whether any work happened.
- **Class B — feedback loop is open.** `clawteam task update --status completed` fires no event; CEO has no trigger to advance the phase and either idles or blindly tries `sprint advance` hoping for the best.
- **Class C — no end-to-end test.** 1740+ unit tests but zero integration tests spawning a real multi-agent sprint, so every regression hides until a human runs `clawteam go` by hand.

### Scope (14 REQs, 5 phases)

- **Phase 8 — Workflow Contract** (RELI-01..04): `PHASE_REQUIREMENTS` registry + `clawteam artifact write` CLI + wire into `EvidenceGate` + named-artifact error messages.
- **Phase 9 — Event-driven Coordination** (EVT-01..04): `TaskCompleted` emission + `PhaseCompletionWatcher` + `wake:phase` kind + auto-register at team-launch.
- **Phase 10 — UX polish** (UX-01..03): attend "Urg" column / attend --summary title / pending_question_ids sync.
- **Phase 11 — End-to-End Integration Test** (TEST-01): subprocess backend + scripted claude mock + 7-phase assertion suite.
- **Phase 12 — Documentation Refresh** (DOC-01..02): README solo-UX-first rewrite + `docs/architecture/event-driven-wake.md`.

### Out of scope

- **Cost observability rewire** — cost stack was DELETED post-v1.0-UAT (commit `716c5a8`); Anthropic console is the source of truth indefinitely.
- **Gstack skill CLI wrappers** (`/ship`, `/canary`, `/benchmark` etc.) — deferred to v1.2 pending CLI-subcommand vs claude-plugin-dir design decision.
- **Real multi-sprint load test** (HUMAN-UAT #1 from v1.0) — requires live API spend + instrumentation; v1.2 candidate.
- **Agent-to-agent artifact-quality verification** (beyond Phase 4's review-only verification) — v1.2 stretch.

Full scope: `.planning/REQUIREMENTS.md` + `.planning/ROADMAP.md`.

---

## v1.0 — hire-your-team + parallel-sprint gstack integration

**Shipped:** 2026-04-22
**Phases:** 8 (Phase 0-7) | **Plans:** 78 | **LOC:** ~70,767 Python
**Timeline:** 2026-04-15 → 2026-04-22 (8 days active development, ~450 commits on `gstack-integration`)

### What Shipped

1. **Foundation safety nets (Phase 0)** — 6-template backwards-compat regression matrix, env secret-scrubbing (no more `*_TOKEN` / `*_KEY` leakage), `clawteam doctor` cross-OS tool diagnosis, `balanced` default model profile (no silent Opus billing), upstream RFC 001 proposing `PhaseRegistry` + `HarnessPlugin` hooks.

2. **Core harness extensions (Phase 1)** — `PhaseRegistry` + `SprintState` (pydantic v2, file-locked atomic JSON persistence) + `InteractionGate` landed as additive plugin primitives with zero semantic changes to existing templates.

3. **Sprint engine + theater/drift/deadlock prevention (Phase 2)** — single-sprint Think→Ship loop with `EvidenceGate` (every phase needs evidence), cycle detector (breaks agent ping-pong), `sprint` CLI (start/status/show/list/pause/resume), safety-rail primitives (`freeze`/`unfreeze`/`guard`/`unguard`).

4. **gstack team template (Phase 3)** — `gstack.toml` ships the 11-agent roster (ceo/pm/eng-mgr/designer/dx-lead/engineer/reviewer/qa/security/shipper/sre) with per-role methodology prompts; `GstackSprintPlugin` wires it through `contribute_phases` + `contribute_skills`; first runnable Think→Ship sprint on real roster.

5. **Interactive skills + cross-agent verification (Phase 4)** — `/office-hours`, `/design-consultation`, `/investigate` as state machines; `SmartReviewRouter` with SHA-pinned CODEOWNERS-style routing; reviewer decorrelation (4 review-role prompts + sycophancy cascade guard); `CrossAgentVerificationGate`; Ship-phase human-approval gate (no self-approve AI).

6. **Tool-heavy skills (Phase 5)** — `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy`, `/codex` — 7 operational skills for shipper/sre/engineer with `gh`/`vercel`/`netlify`/`flyctl`/`lighthouse` integrations (all feature-detected via `doctor`).

7. **Browser + design + memory (Phase 6)** — `clawteam[browser]` extra gating Playwright; `/browse`, `/open-gstack-browser`, `/setup-browser-cookies`, `/design-shotgun` (mockup variant board), `/design-html` (React/Svelte/Vue-aware HTML); `/learn` memory store with provenance + decay + human-gate on high-impact entries.

8. **Parallel sprints + attention queue + cost controls (Phase 7)** — `SprintConductor` 3-semaphore concurrency (10 sprints × 1 per-agent × 6 active), `clawteam attend` priority-ranked queue with `--summary` digest mode + `--auto-accept-reversible` + `pick → $EDITOR` closure, `RateLimitMonitor` 60s 429-window scheduler, zombie worktree GC (5/10 GB disk budget), cost + cache tracking infrastructure.

### Known Deferred Items at Close

- **Phase 02 UAT:** 5 pending scenarios left in `testing` state (full pytest regression checks not completed interactively — covered by 02-VERIFICATION.md automated run instead).
- **Phase 04 UAT:** 4 skipped-interactive items (covered by automated test suites for design_consultation / investigate / cross_agent_verifiers / ship_approval).
- **Phase 07 HUMAN-UAT:** 5 empirical items deferred by user decision — real 10-sprint 5-min/4-GB load, live 429 handling, >50% cache hit steady-state, digest UX at 20+ question scale, `attend → $EDITOR` end-to-end (verified via fabricated walkthrough — real agent integration deferred).
- **QUALITY-12 emit-path gap (discovered at close):** Phase 7's `CostTracker` + `CacheTracker` subscribe to `ClaudeApiResponse` + `ToolCallCompleted` events that are never emitted under the tmux + claude-CLI spawn architecture. Infrastructure, UI, accounting, and alarm-crossing logic all ship; data source wiring deferred to v1.x backlog 999.001.
- **Backlog v1.x (999.001–004):** ClaudeApiResponse emit path, attend "Urg" column, digest "Representative title", AttentionWatcher sprint-state sync. All captured in `.planning/backlog/`.

### Retrospective Highlights

- **What worked:** Goal-backward phase planning with per-plan pre-commit TDD gates caught most bugs before merge. Cross-agent verification gates caught two sycophancy cascades in live review rounds. Phase 2's EvidenceGate prevented a "ship-before-test-complete" trap in Phase 5.
- **What was inefficient:** Phase-level VERIFICATION.md wasn't generated inline for Phases 4/5/6 — retroactive synthesis at milestone-close required 3 parallel verifier agents (fixable: auto-run verifier at phase close).
- **Pattern established:** `pytest-auto-verified` mode for UAT (skip interactive walkthroughs when pytest coverage is complete) landed in Phase 5 and was reused in Phase 6/7.
- **Surprise:** Phase 7's observability stack is internally complete but externally blind — the emit-path gap was only caught during post-milestone UAT walkthrough.

### Tag

`v1.0` — see `git show v1.0` or `cat .planning/milestones/v1.0-ROADMAP.md`.

---
