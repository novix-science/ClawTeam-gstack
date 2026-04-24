# Requirements — Milestone v1.1 Reliability

**Goal:** Close the three architectural gaps diagnosed during v1.0 UAT so that `clawteam go "build X"` reliably produces a working X through 11-agent coordination. Elevate clawteam from "infrastructure-complete, coordination-unverified" to "integration-tested end-to-end delivery."

**Source of scope:** 2026-04-23/24 diagnostic chat (root-cause analysis replacing whack-a-mole bug fixing) + v1.0 post-UAT todos/backlog.

---

## v1.1 Requirements

### RELI — Reliability / state-machine teeth

Block advance when phase work is genuinely incomplete, not just when gate code is broken.

- [ ] **RELI-01**: Phase artifact requirements registered per phase via `clawteam/templates/gstack/phase_contracts.py::PHASE_REQUIREMENTS` mapping phase name → list of required artifact types (e.g. `think → ["delegation.json"]`, `plan → ["architecture-lock.md"]`, `build → ["diff.patch"]`, `review → ["review-report.md"]`, `test → ["test-report.json"]`, `ship → ["ship-approval.md"]`, `reflect → ["retro.md"]`).
- [ ] **RELI-02**: `clawteam artifact write <team> <sprint> <artifact_type>` CLI command accepts artifact content from stdin, validates `artifact_type` against registered EvidenceSchemaRegistry, persists to `<data_dir>/teams/<team>/sprints/<sprint>/artifacts/<type>`, fires `ArtifactPersisted` event.
- [ ] **RELI-03**: `GstackSprintPlugin.contribute_phase_requirements()` wires PHASE_REQUIREMENTS into SprintConductor so `EvidenceGate` receives the current-phase artifact list (not the empty default).
- [ ] **RELI-04**: `sprint advance` gate-block response explicitly names the first missing artifact (e.g. `GATE_BLOCKED: missing artifact 'delegation.json' for phase 'think'`) so agents can self-correct.

### EVT — Event-driven coordination (close the feedback loop)

Make phase completion a push event, not something CEO has to deduce.

- [ ] **EVT-01**: `clawteam task update <id> --status completed` emits `TaskCompleted(team, sprint_id, owner, task_id)` event on the event bus.
- [ ] **EVT-02**: `clawteam/sprint/phase_completion_watcher.py::PhaseCompletionWatcher` subscribes to `TaskCompleted` events; when all tasks for the current phase have status=completed AND the phase's required artifacts exist, calls `wake_agent(team, leader_role, kind="phase")`.
- [ ] **EVT-03**: `clawteam/wake.py` gains a `"phase"` kind producing `[wake:phase] All {phase} phase work complete ({N} tasks done, {M} artifacts present). Run 'clawteam sprint advance <sprint_id> --team <team>' to advance.` injection text.
- [ ] **EVT-04**: Auto-register PhaseCompletionWatcher at team-launch time so every new team gets the feedback loop for free (no explicit opt-in).

### UX — attend UX polish (carried from v1.0 backlog)

Address the UAT-discovered UX bugs in attend / status so digest mode + dashboard are accurate.

- [ ] **UX-01** (was backlog 999.002): `attend` "Urg" column renders the numeric urgency from question frontmatter (1=low → 4=critical) via a level map, not a static "norm" label.
- [ ] **UX-02** (was backlog 999.003): `attend --summary` "Representative title" renders the first H1 heading from the question body, not the qid (qid is already in the separate id column).
- [ ] **UX-03** (was backlog 999.004): Sprint `state.json::pending_question_ids` stays in sync with filesystem. Either (a) auto-start `AttentionWatcher` on `sprint start` so the state is continuously reconciled, or (b) `sprint status` does a one-shot reconciliation at read time.

### TEST — End-to-end test coverage

One integration test becomes the regression shield that prevents the next 6 rounds of manual UAT bug discovery.

- [ ] **TEST-01**: `tests/integration/test_gstack_sprint_end_to_end.py` spawns a test team using the subprocess spawn backend (not tmux, for determinism), replaces the `claude` executable with a scripted mock whose responses match the expected 7-phase agent behavior, then runs a complete sprint start → reflect cycle. Assertions: 6 PhaseTransition events, 7 artifacts persisted, at least one wake received per agent, final sprint state = `completed`.

### DOC — Documentation refresh

The README + developer docs still describe the v1.0-era flow. Update to match current solo-UX + event-driven architecture.

- [ ] **DOC-01**: Top-level README updated: `clawteam go` / `clawteam status` / `clawteam answer` / `clawteam stop` are the primary flow; `team spawn` / `launch` / `sprint start` are power-user escape hatches (documented in a separate advanced section).
- [ ] **DOC-02**: New developer doc `docs/architecture/event-driven-wake.md` explaining wake:task / wake:inbox / wake:phase / nudge architecture, tmux hook wiring, and how to add a new wake kind.

---

## Deferred / Out of Scope for v1.1

**999.001 — cost observability emit path** deleted in commit `716c5a8` (the entire cost stack was removed post-v1.0 UAT because neither the upstream agent-self-report path nor the Phase 7 event-driven path worked under tmux + claude-CLI architecture). Cost tracking delegated to Anthropic console indefinitely. Not a v1.1 requirement.

**Gstack skill CLI wrappers** (`/ship`, `/canary`, `/benchmark`, etc. — 11 Python handlers that never got CLI wrappers or claude SKILL.md files). Deferred to v1.2. Rationale: solving this requires a design decision between "wrap as CLI subcommands" vs "inject as claude-code plugin-dir skills" — too scope-expanding for v1.1's reliability focus.

**Real multi-sprint load test** (HUMAN-UAT #1 from v1.0 — 10 concurrent sprints, 5-min wall clock, 4 GB RAM). Requires live API spend + instrumentation that doesn't exist yet. v1.2 candidate.

**Agent-to-agent verification gates in build phase** (beyond Phase 4's review-only verification). Current EvidenceGate verifies artifact presence, not artifact quality. Stretch goal for v1.2.

---

## Traceability

Filled by `/gsd-plan-phase` as each phase maps requirements. Draft mapping:

| REQ-ID | Phase | Status |
|--------|-------|--------|
| RELI-01 | Phase 8 | Pending |
| RELI-02 | Phase 8 | Pending |
| RELI-03 | Phase 8 | Pending |
| RELI-04 | Phase 8 | Pending |
| EVT-01  | Phase 9 | Pending |
| EVT-02  | Phase 9 | Pending |
| EVT-03  | Phase 9 | Pending |
| EVT-04  | Phase 9 | Pending |
| UX-01   | Phase 10 | Pending |
| UX-02   | Phase 10 | Pending |
| UX-03   | Phase 10 | Pending |
| TEST-01 | Phase 11 | Pending |
| DOC-01  | Phase 12 | Pending |
| DOC-02  | Phase 12 | Pending |

**Total:** 14 requirements mapped to 5 phases.
