# ClawTeam-gstack — Living Retrospective

## Milestone: v1.0 — hire-your-team + parallel-sprint gstack integration

**Shipped:** 2026-04-22
**Phases:** 8 (0-7) | **Plans:** 78 | **Timeline:** 2026-04-15 → 2026-04-22 (8 days active)
**Commits on gstack-integration:** ~450
**LOC:** ~70,767 Python

### What Was Built

- Foundation safety nets: 6-template BC regression matrix, env secret-scrubbing, `clawteam doctor` cross-OS tool diagnosis, `balanced` default model profile, upstream RFC 001.
- Core harness extensions: `PhaseRegistry` + `SprintState` (pydantic v2 file-locked) + `InteractionGate` as additive plugin primitives.
- Sprint engine + safety rails: Think→Ship loop with `EvidenceGate` + cycle detector + `sprint` CLI + `freeze`/`unfreeze`/`guard`/`unguard`.
- The 11-agent gstack team: `gstack.toml` roster with per-role methodology prompts + `GstackSprintPlugin`.
- Interactive + verification: `/office-hours`, `/design-consultation`, `/investigate` state machines; `SmartReviewRouter` with SHA-pinned routing; `CrossAgentVerificationGate`; Ship-phase human-approval gate.
- Operational skills: `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy`, `/codex`.
- Browser + design + memory: `clawteam[browser]` extra, `/browse`, `/design-shotgun`, `/design-html`, `/learn` with provenance + decay.
- Parallel sprints: `SprintConductor` 3-semaphore concurrency, `clawteam attend` priority queue, `RateLimitMonitor`, zombie worktree GC, cost tracking infrastructure.

### What Worked

- **Goal-backward phase planning** with per-plan pre-commit TDD gates caught most bugs before merge. 99%+ of plans landed with strict RED→GREEN sequence.
- **Cross-agent verification gates** (Phase 4 cross-agent) surfaced two sycophancy-cascade anti-patterns during live review rounds that would have otherwise shipped.
- **Phase 2's EvidenceGate** prevented a "ship-before-test-complete" trap in Phase 5 — the gate's `stub-detection` check refused a `TODO: add real deploy` placeholder.
- **pytest-auto-verified UAT mode** (established Phase 5, reused Phase 6/7) saved interactive-UAT time without losing coverage — when the pytest suite is dense, walkthroughs are redundant.
- **Parallel verifier-agent dispatch** at milestone-close produced Phase 4/5/6 VERIFICATION.md files in under 5 minutes total (3 concurrent agents).

### What Was Inefficient

- **VERIFICATION.md wasn't produced inline** for Phases 4/5/6 — the execute-phase workflow assumes it runs but these phases landed without it, requiring retroactive synthesis at milestone-close. **Fix for v1.x:** wire auto-verification trigger into phase-close, not milestone-close.
- **ROADMAP.md drift** — the Progress table fell 5+ phases behind actual completion (said Phase 0-4 "Not started" while they'd shipped). Required bulk cleanup at milestone-close. **Fix:** auto-update Progress table on each `phase.complete` CLI call.
- **REQUIREMENTS.md traceability drift** — SKILL-10/SKILL-11 remained "Pending" after Phase 6 shipped them. **Fix:** auto-flip requirement status when SUMMARY frontmatter references them.
- **Emit-path gap discovered post-milestone** — Phase 7's CostTracker + CacheTracker subscribe to events never emitted under tmux+claude-CLI architecture. The infrastructure passed its own integration tests but provides no live data. **Root cause:** the Phase 7 verifier agent classified "Cache hit rate >50%" as `human_needed` (empirical) when it should have been `gaps_found` (unimplemented). **Fix for v1.x:** verifier checks must include "event emitter exists" when subscriber patterns are claimed validated.

### Patterns Established

- **Backlog entry format** under `.planning/backlog/v1.x-NNN-slug.md` with structured frontmatter (id / milestone / priority / category / origin). Surfaced in ROADMAP.md Backlog section.
- **Deferred Items** table in STATE.md at milestone-close captures open-artifact audit output with dispositions.
- **Post-milestone UAT walkthrough as final check** — the Phase 7 emit-path gap was only discovered via live walkthrough, not by any automated gate. **Establishing this as v1.x milestone-close step.**

### Key Lessons

1. **Infrastructure-complete ≠ functional.** A subscriber without an emitter is a memory-allocating ghost. Tests that instantiate a `CostTracker` and emit events directly pass, but the tracker never receives events in production. The Phase 7 verifier should have traced at least one production emit-site for every subscriber-based claim.
2. **Doc-sync drift compounds.** REQUIREMENTS.md fell out of sync by Phase 6; ROADMAP.md by Phase 4. Fixing both at milestone-close was feasible but expensive. The `phase.complete` CLI step should be atomic across ROADMAP + REQUIREMENTS.
3. **UAT walkthroughs catch what tests miss.** Three new v1.x backlog items (attend Urg column, digest title, watcher sync) surfaced in 20 minutes of live CLI usage — invisible to the pytest suite because they're UX defects, not behavior defects.
4. **`pytest-auto-verified` mode is sound**, but requires the test suite to lock user-observable behavior (not just internal function contracts). Phase 5's UAT mode was safer than Phase 4's because its tests exercised the actual CLI surfaces; Phase 4's cross-agent gate tests proved the class works but didn't prove the full Review-phase flow works end-to-end.

### Cost Observations

- Model mix (estimated, direct measurement blocked by 999.001 emit-path gap): majority sonnet-4.6 for executors, opus-4.7 for cross-phase synthesis + milestone audit.
- Sessions: ~10 active working sessions across 8 days.
- Notable: full-suite pytest at close takes ~2 minutes (1,835 tests); phase-scoped subsets run in <5 seconds, which is what the per-plan TDD gates use.

### Post-Close UAT Walkthrough — 5 Fixes In-Place (2026-04-22)

Immediately after `/gsd-complete-milestone` tagged v1.0, a live walkthrough surfaced 5 issues invisible to the 1,800+ automated test gates. Per user preference ("不用 bump version 去修 目前还在验收阶段"), these were committed in-place on `gstack-integration` without version bumps — folded into v1.0 UAT validation scope rather than creating v1.0.x patch tags.

| Commit | Severity | What was broken |
|--------|----------|-----------------|
| `4e1bd29` | blocker | `clawteam launch gstack` crashed under fish/elvish/nushell — tmux used login shell for bash-style launcher |
| `8090af7` | high | Agents spawned by `launch` had no role methodology — answered as generic Claude Code, not as "I'm ceo" |
| `c254315` | high | Documented flow `team spawn → launch` hard-failed with "Team already exists" |
| `bb18c8e` | high | Each agent spawn burned full 30s timeout in trust confirmer — 11-agent launch ~12 min → ~23s with early-exit |
| `a45ed53` | feat | Added 4 top-level solo-UX commands (go/status/answer/stop) — reduced 10-command happy path to 4 |
| (refactor) | trim | **Deleted Phase 7 cost + rate-limit observability stack** (−2514 LOC). Neither system 1 (agent self-report, unreliable honesty) nor system 2 (event-driven, no emitter under tmux + claude-CLI) worked for solo users. Cost tracking now delegates to Anthropic console. |

**Key process lesson:** milestone close should require a live walkthrough as its final gate, not just automated artifacts. All 5 of these issues would have been caught by running `clawteam launch gstack` on the target machine once before tagging v1.0.

Full index with repro commands + test coverage: `.planning/backlog/v1.0-post-uat-fixes.md`.

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 8 |
| Plans | 78 |
| LOC Python | 70,767 |
| Duration | 8 days active |
| REQs shipped | 80 (79 complete + 1 partial QUALITY-12) |
| Post-close backlog | 4 items (999.001-004) |
| Post-close in-place UAT fixes | 5 commits (4e1bd29, 8090af7, c254315, bb18c8e, a45ed53) + 1 refactor commit (cost/rate-limit stack deletion, −2514 LOC) |
| Pre-existing test-isolation failures at close | 9 (registry pollution) |
| Phases with retroactive VERIFICATION.md | 3 (Phases 4/5/6) |
| Live-walkthrough-surfaced blockers missed by automated gates | 4 blocker/high, 1 feature gap |

*Update this table as v1.x, v2.0+ ship.*
