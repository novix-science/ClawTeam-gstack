# ClawTeam-gstack Milestones

Historical record of shipped versions.

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
