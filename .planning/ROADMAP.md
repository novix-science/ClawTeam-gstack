# Roadmap: ClawTeam-gstack

## Milestones

- ✅ **v1.0 — hire-your-team + parallel-sprint gstack integration** (Phases 0-7) — shipped 2026-04-22 — see `.planning/milestones/v1.0-ROADMAP.md`
- 🚧 **v1.1 — Reliability / integration-tested 11-agent delivery** (Phases 8-12) — started 2026-04-24 — see `.planning/REQUIREMENTS.md`

## v1.1 Goal

Close the three architectural gaps diagnosed during v1.0 UAT so `clawteam go "build X"` reliably produces a working X through 11-agent coordination:

- **Class A — state-machine teeth:** gates must block on genuine artifact absence, not just on broken gate code.
- **Class B — event-driven feedback loop:** phase completion becomes a push event, not something CEO has to deduce by polling.
- **Class C — end-to-end regression coverage:** one integration test replaces 6 rounds of manual UAT bug discovery.

## Phases

### v1.1 (Phases 8-12) — In Progress

- [ ] **Phase 8 — Workflow Contract (state-machine teeth)** — RELI-01, RELI-02, RELI-03, RELI-04
  - Wire `PHASE_REQUIREMENTS` artifact registry into `EvidenceGate` so advance-phase actually blocks on missing artifacts. Add `clawteam artifact write` CLI so agents have one uniform way to produce the required artifact.
  - Estimated plans: 2-3.
  - Unlocks: every phase now has concrete "done" signal; CEO's `sprint advance` can't succeed on empty work.

- [ ] **Phase 9 — Event-driven Coordination (close the feedback loop)** — EVT-01, EVT-02, EVT-03, EVT-04
  - Emit `TaskCompleted` from `clawteam task update --status completed`. Subscribe a `PhaseCompletionWatcher` that calls `wake_agent(kind="phase")` when all tasks+artifacts for a phase are done. Auto-register the watcher at team-launch time.
  - Estimated plans: 2-3.
  - Unlocks: CEO no longer idles or blindly advances — gets a push notification when the phase is actually complete.

- [ ] **Phase 10 — UX polish (attend / status sync)** — UX-01, UX-02, UX-03
  - Fix attend "Urg" column (render numeric urgency via level map). Fix attend --summary "Representative title" (render first H1 of body, not qid). Keep `sprint.pending_question_ids` in sync with filesystem (auto-start watcher or one-shot reconcile on read).
  - Estimated plans: 1-2.
  - Unlocks: digest mode + sprint status accurately reflect pending work.

- [ ] **Phase 11 — End-to-End Integration Test (regression shield)** — TEST-01
  - `tests/integration/test_gstack_sprint_end_to_end.py`: subprocess backend + scripted `claude` mock + assertions on 6 PhaseTransition events, 7 artifacts persisted, every agent wake-received, final state=completed.
  - Estimated plans: 1-2.
  - Unlocks: future prompt / role-card / gate edits regression-caught in CI instead of manual UAT.

- [ ] **Phase 12 — Documentation refresh** — DOC-01, DOC-02
  - README rewrite: `clawteam go / status / answer / stop` as primary flow; `team spawn / launch / sprint start` as power-user escape hatch. New `docs/architecture/event-driven-wake.md` explaining wake:task / wake:inbox / wake:phase / nudge architecture.
  - Estimated plans: 1.
  - Unlocks: docs match the v1.1 solo-UX + event-driven architecture rather than v1.0-era flow.

### ✅ v1.0 (Phases 0-7) — SHIPPED 2026-04-22

<details>
<summary>Expand to see v1.0 phase breakdown</summary>

- [x] Phase 0: Foundation & Upstream RFC (7/7 plans) — CORE-03, TEAM-06, QUALITY-14, QUALITY-15, UX-08
- [x] Phase 1: Core Harness Extensions (5/5 plans) — CORE-01, CORE-02, CORE-04, INT-01, INT-02
- [x] Phase 2: Sprint Engine, Evidence Gates & Theater/Drift/Deadlock Prevention (13/13 plans) — 21 REQs (CORE-05/07, INT-06, SPRINT-01/02, SKILL-09, SAFETY-01..04, QUALITY-01/02/03/06/08/11, UX-02..05/09)
- [x] Phase 3: Gstack Team Template & Methodology Port (9/9 plans) — 16 REQs (TEAM-01..05, SKILL-01..08, SPRINT-06, UX-01/07)
- [x] Phase 4: Interactive State Machines, Smart Review Routing & Cross-Agent Verification (14/14 plans) — SPRINT-03/04/05, SAFETY-05, QUALITY-07/09/13
- [x] Phase 5: Tool-Heavy Skills (Ship, SRE, Codex) (10/10 plans) — SKILL-13..19
- [x] Phase 6: Browser Skills, Design Pipeline & Team Memory (11/11 plans) — MEM-01..07, SKILL-10..12, QUALITY-10
- [x] Phase 7: Parallel Sprints, AttentionQueue UX & Cost Controls (9/9 plans) — CORE-06, INT-03, INT-04, INT-05, QUALITY-04, QUALITY-05, QUALITY-12 (later REMOVED post-UAT), UX-06

Full detail: `.planning/milestones/v1.0-ROADMAP.md`
Archive audit: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`
Archive requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`

Note: Post-UAT deletion of Phase 7 cost/rate-limit observability stack (2514 LOC removed 2026-04-22); cost tracking delegated to Anthropic console indefinitely. Documented in `.planning/backlog/v1.0-post-uat-fixes.md`.

</details>

## v1.1 Requirement → Phase Map

| REQ-ID | Phase | Category | Status |
|--------|-------|----------|--------|
| RELI-01 | 8 | Workflow contract | Pending |
| RELI-02 | 8 | Workflow contract | Pending |
| RELI-03 | 8 | Workflow contract | Pending |
| RELI-04 | 8 | Workflow contract | Pending |
| EVT-01  | 9 | Event-driven coord | Pending |
| EVT-02  | 9 | Event-driven coord | Pending |
| EVT-03  | 9 | Event-driven coord | Pending |
| EVT-04  | 9 | Event-driven coord | Pending |
| UX-01   | 10 | UX polish | Pending |
| UX-02   | 10 | UX polish | Pending |
| UX-03   | 10 | UX polish | Pending |
| TEST-01 | 11 | Regression shield | Pending |
| DOC-01  | 12 | Docs | Pending |
| DOC-02  | 12 | Docs | Pending |

**Total:** 14 requirements, 5 phases.

## Success Criteria (v1.1)

The milestone is complete when all five Phases pass `/gsd-verify-phase` AND:

1. `clawteam sprint advance` cannot succeed when the current phase's required artifact is missing — gate blocks with a named-artifact error message.
2. After the last task for a phase flips to `completed` and the artifact is on disk, the leader role (CEO) receives a `[wake:phase]` within 10 seconds without polling.
3. `tests/integration/test_gstack_sprint_end_to_end.py` runs to completion in CI (subprocess backend, scripted claude mock) asserting 6 PhaseTransition events, 7 artifacts persisted, final sprint state = `completed`.
4. `clawteam attend` and `clawteam attend --summary` render correct urgency + representative titles against a fixture of 20 diverse questions.
5. `README.md` front matter demonstrates the `clawteam go` flow as the primary user entry point; power-user commands are clearly marked as such.

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 0. Foundation & Upstream RFC | v1.0 | 7/7 | Complete | 2026-04-22 |
| 1. Core Harness Extensions | v1.0 | 5/5 | Complete | 2026-04-22 |
| 2. Sprint Engine + Safety Rails | v1.0 | 13/13 | Complete | 2026-04-22 |
| 3. Gstack Team & Methodology | v1.0 | 9/9 | Complete | 2026-04-22 |
| 4. Interactive / Routing / Verification | v1.0 | 14/14 | Complete | 2026-04-22 |
| 5. Tool-Heavy Skills | v1.0 | 10/10 | Complete | 2026-04-22 |
| 6. Browser / Design / Memory | v1.0 | 11/11 | Complete | 2026-04-22 |
| 7. Parallel Sprints / Attention / Cost | v1.0 | 9/9 | Complete | 2026-04-22 |
| 8. Workflow Contract | v1.1 | 0/TBD | Pending | — |
| 9. Event-driven Coordination | v1.1 | 0/TBD | Pending | — |
| 10. UX Polish (attend / status) | v1.1 | 0/TBD | Pending | — |
| 11. E2E Integration Test | v1.1 | 0/TBD | Pending | — |
| 12. Documentation Refresh | v1.1 | 0/TBD | Pending | — |

---

*v1.1 milestone initialized 2026-04-24 — run `/gsd-plan-phase 8` to begin execution (or `/gsd-discuss-phase 8` first if you want to lock design decisions before planning).*
