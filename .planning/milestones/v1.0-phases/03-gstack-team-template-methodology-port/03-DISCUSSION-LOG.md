# Phase 3: Gstack Team Template & Methodology Port — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-20
**Phase:** 03-gstack-team-template-methodology-port
**Areas discussed:** Methodology depth (engineer/shipper/sre), gstack.toml shape, role-prompt format + envelope location, verification stringency

---

## Area Selection (entry gate)

User selected ALL 4 surfaced gray areas. Areas not surfaced (no real ambiguity left after research):
- Cross-template isolation test stringency — already locked by ROADMAP success criterion #2 + #7
- Pure-rubric vs interactive split — locked at Phase 2 port-audit (Pitfall 7)
- 11-agent roster composition — locked in PROJECT.md row 1
- Leader binding (ceo) — locked in PROJECT.md row 2 + ROADMAP success criterion #4
- Default model_profile (balanced) — locked in TEAM-05 + STATE.md

---

## Area 1: Methodology depth for tool-only roles (engineer / shipper / sre)

### Q1.1: engineer prompt depth

| Option | Description | Selected |
|--------|-------------|----------|
| Implementation-discipline rubric | ~1200 bytes; read-first, atomic commit, sha-pin awareness, diff_summary every Build turn, no-fix-without-investigation deferral. Engineer feels like a real specialist on day 1. Adds one rubric port to Phase 3 scope. | ✓ |
| Minimal (research recommendation) | ~600 bytes; persona + envelope + Phase-5 deferral stub. Cleaner Phase 3 scope but engineer prompt looks thin compared to other 8 specialists with substantive rubric content. | |
| Stub-only | Smallest possible. Honest about not-yet-built but hardest to defend the "team of 11 specialists" narrative for engineer. | |

**User's choice:** Implementation-discipline rubric (Recommended)
**Notes:** Aligns with PROJECT.md memory note: product narrative beats elegance. The "11 distinct specialists from day 1" framing requires engineer to feel substantive even before Phase 5 tools land.

### Q1.2: shipper + sre prompt depth

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal stubs | ~600 bytes each; persona + step/signal envelope + Phase-5 deferral + skeleton-artifact instruction + emit question to ceo. Honest stub that produces real artifacts for EvidenceGate. | ✓ |
| Expanded with checklist | ~1000 bytes each; generic SRE-practice content. Risk: contradicts Phase 5 `/canary` + `/ship` rubrics when they actually arrive. | |

**User's choice:** Minimal stubs (Recommended)
**Notes:** Methodology genuinely IS the Phase-5 tool skills for these two; adding speculative content invites Phase-5 contradiction.

---

## Area 2: gstack.toml content shape

### Q2.1: Pure roster vs onboarding theater

| Option | Description | Selected |
|--------|-------------|----------|
| Pure roster | Agents + leader + phases + model_profile + memory layout only. Zero starter tasks. `team show` shows "11 ready, no active sprint". Matches "team waits for you" narrative. | ✓ |
| Roster + 'team is ready' broadcast | Single TeamManager post-spawn step emits one welcome event so `team show` has timestamps. ~10 LOC, no schema change. | |
| Roster + per-role onboarding tasks | Each role gets a `/welcome` greeting task. Theatrical; adds task content to maintain. | |

**User's choice:** Pure roster (Recommended)
**Notes:** "Team waits for `/sprint start`" is clean product framing. Theater muddies it.

### Q2.2: Per-role memory directories

| Option | Description | Selected |
|--------|-------------|----------|
| Pre-create all 11 dirs at team spawn | TeamManager mkdirs the tree at spawn time. Race-free across N parallel sprints × 11 agents. 11 mkdir calls. | ✓ |
| Lazy-init on first /learn write | Phase 6 problem. Pushes a real concurrency concern to Phase 6 unnecessarily. | |

**User's choice:** Pre-create all 11 dirs at team spawn (Recommended)
**Notes:** Defensive against Phase-6 race conditions. Trivial cost now.

---

## Area 3: Role-prompt file format + per-persona envelope location

### Q3.1: Role prompt file format

| Option | Description | Selected |
|--------|-------------|----------|
| Separate .md files | clawteam/templates/gstack/prompts/<role>.md × 11. Grep-friendly for golden tests. Phase 6 memory append-friendly. 11 small files + 1 TOML. | ✓ |
| Inlined multi-line TOML strings | All 11 prompts as triple-quoted strings inside gstack.toml. Single-file authoring but TOML isn't great for 2KB prose; golden grep tests would parse TOML first. | |

**User's choice:** Separate .md files (Recommended)
**Notes:** Native grep-ability is decisive for the golden-test strategy.

### Q3.2: Per-persona envelope subclass location

| Option | Description | Selected |
|--------|-------------|----------|
| clawteam/templates/gstack/envelope_personas.py | Gstack-scoped. Honors "delete plugin + gstack.toml + templates/gstack/ and rest still runs" invariant. Per-persona envelopes ARE gstack-specific today. Promote to clawteam/team/ when a second template adopts the pattern. | ✓ |
| clawteam/team/envelope_personas.py | Generic location alongside Phase 2 envelope.py. Future-proof but speculative. | |

**User's choice:** clawteam/templates/gstack/envelope_personas.py (Recommended)
**Notes:** Don't pre-promote on speculation. Migration is one git mv when needed.

---

## Area 4: Verification stringency

### Q4.1: Golden-trace fidelity strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Strategy B — markdown-derived | WebFetch upstream gstack skill markdown once; commit under tests/fixtures/gstack_skills/. Golden tests grep both fixture and ported role prompt. Cheap, deterministic, fully reproducible. | ✓ |
| Strategy B + Strategy A baseline | Same as B PLUS install gstack as dev-dep + record native transcripts. Front-loads Phase 4 signal source but adds gstack install/auth overhead. | |
| Strategy A only | Sandbox-gstack and record actual transcripts as ground truth. Highest fidelity but significant scope add to Phase 3. | |

**User's choice:** Strategy B (Recommended)
**Notes:** Phase 3 ports are transcriptions, not interaction shapes. Strategy A's signal is irrelevant to Phase 3 deliverables; reserve for Phase 4 decision if needed.

### Q4.2: Reflect-phase /learn stub shape

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal placeholder + structured event | Write _phase6_pending/<sprint-id>-retro.json AND emit LearnPendingEvent on EventBus. Tiny extra now, zero migration work in Phase 6. | |
| Minimal placeholder only | Just write the placeholder JSON. ROADMAP-blessed minimum. Phase 6 writes a one-time backfill scanner. | ✓ |

**User's choice:** Minimal placeholder only (research recommendation)
**Notes:** Forward-compatibility scope deferred to Phase 6. Keep Phase 3 focused on substrate it owns.

---

## Claude's Discretion (planner picks; not asked)

- Concrete pydantic field names for the 6 gstack artifact schemas
- Internal markdown structure of each role prompt
- Exact wording of `INTERACTIVE-RUNTIME-DEFERRED:` and `SHA-PIN-DEFERRED:` meta-instructions (must be greppable; exact prose is planner's call)
- Internal layout of `_phase6_pending/<sprint_id>-retro.json` schema
- Wave structure and parallelism of plans
- Whether to ship `team show` dashboard extension as one plan or split per dashboard column

---

## Deferred Ideas (captured during discussion or carried from research)

- Strategy A golden traces (sandbox-gstack + recorded transcripts) — only revisit if Phase 4 needs them
- LearnPendingEvent EventBus emission — Phase 6 backfill scanner sufficient
- Promote envelope_personas.py to clawteam/team/ if second template adopts per-persona pattern
- Per-role 'welcome' starter tasks — theater rejected
- 'Team is ready' post-spawn broadcast — theater rejected
- Generic SRE-practice content in shipper/sre prompts — defer to Phase 5 tool ports
- Per-team prompt customization hooks — post-v1
- Helper-agent spawning inside engineer — post-v1
