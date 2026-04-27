# Roadmap: ClawTeam-gstack

## Milestones

- ✅ **v1.0 — hire-your-team + parallel-sprint gstack integration** (Phases 0-7) — shipped 2026-04-22 — see `.planning/milestones/v1.0-ROADMAP.md`
- ✅ **v1.1 — Reliability / integration-tested 11-agent delivery** (Phases 8-12) — shipped 2026-04-24 — see `.planning/milestones/v1.1-ROADMAP.md`
- 🚧 **v1.2 — Workspace Semantics** (Phases 13-15) — started 2026-04-24

## Phases

### 🚧 v1.2 (Phases 13-15) — ACTIVE

- [ ] **Phase 13: Workspace Entry Point** — `clawteam open` lands users in a live team with no goal; launch stops injecting kickoff prompts; `sprint start` owns the kickoff; `go` demoted to shortcut.
- [ ] **Phase 14: Session Continuity** — Agent `claude` session ids persist across re-opens; `clawteam open <existing-team>` resumes every pane's prior conversation; sprint kickoff arrives as continuation when the user has pre-chatted with CEO.
- [ ] **Phase 15: Quiet & Progressive Team** — Idle agents (no active sprint) do not poll or auto-wake; team launch shows progressive pane appearance in a single window instead of the 11-windows-then-tile flash.

### ✅ v1.1 (Phases 8-12) — SHIPPED 2026-04-24

<details>
<summary>Expand to see v1.1 phase breakdown</summary>

- [x] Phase 8: Workflow Contract (3/3 plans) — RELI-01..04
- [x] Phase 9: Event-driven Coordination (1/1 plan) — EVT-01..04
- [x] Phase 10: UX Polish (1/1 plan) — UX-01..03
- [x] Phase 11: End-to-End Integration Test (1/1 plan) — TEST-01
- [x] Phase 12: Documentation Refresh (2/2 plans) — DOC-01..02

Full detail: `.planning/milestones/v1.1-ROADMAP.md`
Audit: `.planning/v1.1-MILESTONE-AUDIT.md`
Archive requirements: `.planning/milestones/v1.1-REQUIREMENTS.md`

</details>

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

## Phase Details

### Phase 13: Workspace Entry Point
**Goal**: Users can open a team without committing to a goal; kickoff prompts move from launch-time to sprint-start time; `go` becomes a documented shortcut rather than the primary flow.
**Depends on**: Phase 12 (v1.1 closed — event-driven sprint loop is the surface this phase reshapes)
**Requirements**: WS-01, WS-02, WS-03, WS-04
**Success Criteria** (what must be TRUE):
  1. Running `clawteam open gstack -n foo` with no goal argument enters a team with 11 `claude` panes, and inspecting each pane shows a clean REPL with zero messages sent — no turn-1 tokens consumed.
  2. On a team that was opened without a goal, the user can run `clawteam sprint start foo --goal "build CSV CLI"` and the kickoff prompt arrives in every agent pane at that moment (not at launch).
  3. `clawteam go "build X"` still works end-to-end (creates team + starts sprint + launches panes with kickoff), but `clawteam go --help` and the README describe it as a shortcut for `open` + `sprint start`, not the primary flow.
  4. Launching a team via `clawteam launch gstack` (the underlying primitive) without `--goal` produces agents with no injected `post_launch_prompt`; `launch --goal X` still injects (backwards compatibility for in-flight callers).
  5. Phase VALIDATION.md exists at `.planning/phases/phase-13-VALIDATION.md` with Nyquist-style live-UAT steps exercising all four behaviors above.
**Plans**: 5 plans
  - [ ] 13-01-test-scaffolding-PLAN.md — Wave 0 test scaffolding (RED tests for WS-01..04)
  - [ ] 13-02-adapter-gating-PLAN.md — Gate post_launch_prompt on goal presence (WS-02)
  - [ ] 13-03-sprint-start-kickoff-PLAN.md — sprint start owns kickoff injection, collision rejection, --retry-kickoff (WS-04)
  - [ ] 13-04-open-command-PLAN.md — register `clawteam open` with create/resume branching (WS-01)
  - [ ] 13-05-go-demotion-docs-PLAN.md — demote `go` tagline + README Primary Flow rewrite (WS-03)

### Phase 14: Session Continuity
**Goal**: Agent conversations survive terminal close / laptop reboot; opening a team again restores every pane's prior dialogue and lets a pre-sprint CEO chat flow directly into the kickoff.
**Depends on**: Phase 13 (requires `open` command and clean-REPL launch path to attach session-resume into)
**Requirements**: RELI-05, RELI-06, WS-05
**Success Criteria** (what must be TRUE):
  1. After `clawteam open gstack -n foo`, the file `~/.clawteam/teams/foo/sessions.json` exists and contains an entry per agent mapping agent name to a non-empty `claude` session id.
  2. Closing the tmux session, then running `clawteam open foo` again, restores the same 11-pane layout and each agent pane shows its prior conversation history (verified by typing in any pane — the agent responds with memory of earlier exchanges, not as a fresh session).
  3. Opening a team, chatting with the CEO pane for several turns in idle mode, then running `clawteam sprint start foo --goal "..."` results in the CEO receiving the kickoff message as the next turn of the existing dialogue (verified by asking CEO to recall prior conversation context — it does).
  4. v1.1 teams opened for the first time under v1.2 start fresh without error (forward-only migration — no retroactive `sessions.json` scan is attempted).
  5. Phase VALIDATION.md exists at `.planning/phases/phase-14-VALIDATION.md` documenting the close-terminal → reopen → resume-verified walkthrough.
**Plans**: TBD

### Phase 15: Quiet & Progressive Team
**Goal**: Idle teams stay quiet (no background polling, no auto-wake) and team launch feels progressive instead of flashing through 11 separate windows before merging.
**Depends on**: Phase 13 (idle mode depends on clean-REPL launch); Phase 14 (session-continuity wake semantics must already be stable before idle-mode suppression is layered on)
**Requirements**: RELI-07, UX-04
**Success Criteria** (what must be TRUE):
  1. On a team opened without an active sprint, observing any agent pane for 5 minutes shows zero unsolicited output — the pane only responds when the user types into it.
  2. Running `clawteam open gstack -n foo` with `--tile` shows panes appearing progressively inside a single tmux window (first agent creates the window, agents 2–11 split into it), and there is no visible "11 windows then merge" flash at the end.
  3. Starting a sprint on a previously idle team re-enables wake behavior cleanly — `TaskCompleted` / `PhaseCompletionWatcher` events fire and agents respond to them as they did in v1.1.
  4. Phase VALIDATION.md exists at `.planning/phases/phase-15-VALIDATION.md` covering the 5-minute quiet-pane observation and the single-window progressive-launch walkthrough.
**Plans**: TBD

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
| 8. Workflow Contract | v1.1 | 3/3 | Complete    | 2026-04-24 |
| 9. Event-driven Coordination | v1.1 | 1/1 | Complete    | 2026-04-24 |
| 10. UX Polish (attend / status) | v1.1 | 1/1 | Complete    | 2026-04-24 |
| 11. E2E Integration Test | v1.1 | 1/1 | Complete    | 2026-04-24 |
| 12. Documentation Refresh | v1.1 | 2/2 | Complete    | 2026-04-24 |
| 13. Workspace Entry Point | v1.2 | 0/5   | Planned     | — |
| 14. Session Continuity | v1.2 | 0/TBD | Not started | — |
| 15. Quiet & Progressive Team | v1.2 | 0/TBD | Not started | — |

---

*v1.2 Workspace Semantics active (started 2026-04-24). Roadmap drafted with 3 phases covering 9 REQs. Next: `/gsd-plan-phase 13`.*
