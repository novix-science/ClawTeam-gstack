# Roadmap: ClawTeam-gstack

## Milestones

- ✅ **v1.0 — hire-your-team + parallel-sprint gstack integration** — Phases 0-7 (shipped 2026-04-22) — see `.planning/milestones/v1.0-ROADMAP.md`
- 📋 **v1.x — observability + UX polish** (planned) — wire `ClaudeApiResponse` emit path, attend UX fixes, attention-watcher sync — see `.planning/backlog/`

## Phases

<details>
<summary>✅ v1.0 (Phases 0-7) — SHIPPED 2026-04-22</summary>

- [x] Phase 0: Foundation & Upstream RFC (7/7 plans) — CORE-03, TEAM-06, QUALITY-14, QUALITY-15, UX-08
- [x] Phase 1: Core Harness Extensions (5/5 plans) — CORE-01, CORE-02, CORE-04, INT-01, INT-02
- [x] Phase 2: Sprint Engine, Evidence Gates & Theater/Drift/Deadlock Prevention (13/13 plans) — 21 REQs (CORE-05/07, INT-06, SPRINT-01/02, SKILL-09, SAFETY-01..04, QUALITY-01/02/03/06/08/11, UX-02..05/09)
- [x] Phase 3: Gstack Team Template & Methodology Port (9/9 plans) — 16 REQs (TEAM-01..05, SKILL-01..08, SPRINT-06, UX-01/07)
- [x] Phase 4: Interactive State Machines, Smart Review Routing & Cross-Agent Verification (14/14 plans) — SPRINT-03/04/05, SAFETY-05, QUALITY-07/09/13
- [x] Phase 5: Tool-Heavy Skills (Ship, SRE, Codex) (10/10 plans) — SKILL-13..19
- [x] Phase 6: Browser Skills, Design Pipeline & Team Memory (11/11 plans) — MEM-01..07, SKILL-10..12, QUALITY-10
- [x] Phase 7: Parallel Sprints, AttentionQueue UX & Cost Controls (9/9 plans) — CORE-06, INT-03, INT-04, INT-05, QUALITY-04, QUALITY-05, QUALITY-12 (partial — emit-path gap), UX-06

Full detail: `.planning/milestones/v1.0-ROADMAP.md`
Archive audit: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`
Archive requirements: `.planning/milestones/v1.0-REQUIREMENTS.md`

</details>

### 📋 v1.x (Planned — no phases yet)

Open the next milestone cycle via `/gsd-new-milestone`. Candidate work captured in `.planning/backlog/`:

- **999.001** — wire ClaudeApiResponse + ToolCallCompleted emit path from claude CLI stream-json (unblocks cost/cache live data)
- **999.002** — attend "Urg" column ignores frontmatter urgency field
- **999.003** — attend --summary "Representative title" shows qid instead of actual title
- **999.004** — sprint.pending_question_ids not synced until AttentionWatcher runs

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

---

*v1.0 archived 2026-04-22 — run `/gsd-new-milestone` to start v1.x.*
