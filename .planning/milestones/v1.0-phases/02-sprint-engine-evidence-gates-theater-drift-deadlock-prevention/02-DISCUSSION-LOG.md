# Phase 2: Sprint Engine, Evidence Gates & Theater/Drift/Deadlock Prevention - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 02-CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
**Areas discussed:** EvidenceGate validation, Response envelope, Safety-rail / freeze state, Theater / progress rule, Cycle detector design, auto_advance semantics, Artifact cap policy, Sprint CLI UX

---

## Opening exchange: user challenged generic gray-area list

On first round Claude presented 4 gray areas framed in the abstract (EvidenceGate schema, Safety-rail enforcement, Theater/progress rule, Response envelope shape). User pushed back:

> 这些像是原本 clawteam 责任范围内的事情, 即 swarm harness, clawteam 的 implementation 是什么

Claude re-scanned the codebase and found significant existing infrastructure:
- `EventBus` with `Before*` event + `veto=True` veto pattern (`events/bus.py:95`)
- `RuntimeEnvelope` with dedupe_key + recentEvents[:50] rolling window
- `TeamMessage` structured pydantic schema with many typed fields
- `RoleConfig` + system-prompt injection via `--append-system-prompt`
- `AgentIdle` / `HeartbeatTimeout` / `AfterTaskUpdate` / `TaskCompleted` events
- `list_zombie_agents` time-based staleness detection
- `ArtifactStore` + per-artifact `.meta.json` with `written_at`
- `SuccessCriterion.test_command` field defined but never executed anywhere
- File-locked + atomic_write_text infrastructure

This reshaped gray areas to surface only **genuinely missing** decisions, not already-settled patterns. Subsequent options were annotated with existing code references to ground the choice.

---

## EvidenceGate validation

### Test-report gate verification method

| Option | Description | Selected |
|--------|-------------|----------|
| Synchronous rerun (Recommended) | gate.check() synchronously runs SuccessCriterion.test_command or pytest on cited test IDs. Content-hash cache on test-report.md skips rerun when unchanged. 100% anti-forgery. | ✓ |
| Hash verify stored result | test runs offline; gate compares stored (test_ids, timestamp, pass/fail) hash. Fast but forgeable. | |
| Async background + cache | Background executor runs test_command; gate returns 'pending'. Decoupled but adds state machine. | |

**User's choice:** Synchronous rerun
**Notes:** ROADMAP SC#2 wording mandates "gate re-runs pytest on the cited test IDs". Content-hash cache mitigates the per-advance rerun cost without breaking the anti-forgery guarantee.

### Other artifacts schema validation

| Option | Description | Selected |
|--------|-------------|----------|
| pydantic frontmatter + required sections (Recommended) | Reuses Phase 1 D-08 Q/A frontmatter pattern. One pydantic model per artifact type + list of required ## section headers. Plugin-extensible. | ✓ |
| Regex/JSONSchema checklist | Loses pydantic model ergonomics (types, IDE completion, inheritance). | |
| Plugin-defined validator callable | Max flexibility, no uniformity. Plugins diverge; audit harder. | |

**User's choice:** pydantic frontmatter + required sections

### Stub / lazy content detection

| Option | Description | Selected |
|--------|-------------|----------|
| Keyword + min length + structure combined (Recommended) | 3 layers: (1) frontmatter required fields non-empty; (2) required section body ≤100 bytes = stub; (3) regex blacklist TBD/TODO/xxx+/placeholder/Lorem ipsum. | ✓ |
| Regex blacklist only | Misses empty/one-liner docs without TBD keywords. | |
| LLM-judged content quality | Accurate but introduces agent dependency inside a gate. Declined for Phase 2. | |

**User's choice:** Keyword + min length + structure combined

---

## Response envelope

### persona / step_label / done field placement

| Option | Description | Selected |
|--------|-------------|----------|
| TeamMessage fields + artifact frontmatter (Recommended) | TeamMessage adds 3 required fields. Durable artifacts (design-doc.md etc.) carry matching YAML frontmatter. Same pydantic model validates both surfaces. Messages + artifacts both attributable. | ✓ |
| Only add to TeamMessage | Artifacts lose attribution; downstream audit weaker. | |
| New TurnEnvelope standalone model | Wraps TeamMessage; all consumers need an adapter. Heavier serialization. | |

**User's choice:** TeamMessage fields + artifact frontmatter

### Compliance validation layer

| Option | Description | Selected |
|--------|-------------|----------|
| transport deliver layer + artifact write layer (Recommended) | transport/base.py::deliver() rejects malformed TeamMessage fast-fail; ArtifactStore.write() rejects malformed frontmatter. Both entry points, no bypass. | ✓ |
| harness consume-time only | mailbox/receive lenient; drift alarm on consume. Violating messages still on disk. | |
| Both (redundant) | Write + consume both validate. Extra cost. | |

**User's choice:** transport deliver + artifact write (two entry points)

### Malformed envelope handling

| Option | Description | Selected |
|--------|-------------|----------|
| First warn + 8+ consecutive hard reject (Recommended) | First violation: MalformedEnvelope event + message delivered/warn. Same agent consecutive 8+ violations: DriftRegression + hard reject until agent produces one valid envelope. Aligned with SC#4's 8+ drift threshold. | ✓ |
| First-time hard reject | Phase 3 prompts must be perfect first try; flaky agents deadlock. | |
| Warn-only no reject | Safety guard value dilutes. | |

**User's choice:** First warn + 8+ consecutive hard reject

---

## Safety-rail / freeze state

### Freeze state storage

| Option | Description | Selected |
|--------|-------------|----------|
| FreezeRegistry singleton + file persistence (Recommended) | clawteam/harness/freeze_registry.py mirrors PhaseRegistry. Persisted to ~/.clawteam/teams/<team>/sprints/<id>/freeze.json. Sprint pause/resume restores state. Consistent with existing registry pattern. | ✓ |
| Mounted in WorkspaceManager | Workspace-only scope; DROP TABLE / API-call freezes unreachable. | |
| In-memory EventBus handler only | Sprint pause/resume loses freeze state — breaks CORE-07. | |

**User's choice:** FreezeRegistry singleton + file persistence

### Agent freeze awareness

| Option | Description | Selected |
|--------|-------------|----------|
| MCP tool + CLI structured error (Recommended) | translate_error wrapper + CLI interception raise FrozenPathError('<path> is /freeze-locked; unfreeze via /unfreeze <path>'). Claude/Codex/Gemini CLIs self-correct from error response. | ✓ |
| Spawn-time CLAWTEAM_FROZEN_PATHS env var | Static at spawn; runtime freeze changes don't propagate without restart. | |
| Runtime mailbox notification + error interception | More complex; depends on agent actively polling inbox. | |

**User's choice:** MCP tool + CLI structured error

### unfreeze audit log format

| Option | Description | Selected |
|--------|-------------|----------|
| FreezeChange event + dedicated JSONL (Recommended) | events/types.py::FreezeChange(action, path, agent, reason) + append-only freeze_audit.jsonl per sprint. Mirrors exit_journal pattern. Persistent, greppable. | ✓ |
| Event-only (board-dependent) | No subscriber = no audit. Value lost. | |
| Unified sprint event_log.jsonl | Centralized but audit needs filtering. | |

**User's choice:** FreezeChange event + dedicated JSONL

---

## Theater / progress rule

### Turn boundary

| Option | Description | Selected |
|--------|-------------|----------|
| One turn = TeamMessage deliver or artifact write (Recommended) | Observation: transport.deliver or ArtifactStore.write. Per-agent counter increments. Co-located with envelope-validation hook points. | ✓ |
| One turn = one MCP tool call | Finer granularity; pure reads count. Theater threshold becomes too noisy. | |
| Wall-clock 60s window | Decoupled from agent chattiness; brief idle periods count as empty. | |

**User's choice:** One turn = TeamMessage or artifact write

### Progress definition

| Option | Description | Selected |
|--------|-------------|----------|
| artifact bytes delta > 0 OR TaskCompleted (Recommended) | Net-positive artifact bytes (any delta > 0) OR TaskCompleted event fired this turn. Mailbox-only messages don't count. Matches ROADMAP SC#6 "artifact bytes". | ✓ |
| Above + message count ≥ 3 | Loose; flurry of chat messages games the gate. | |
| Above + unique file path changed | Strict; real iterative refactor on one file blocked. | |

**User's choice:** artifact bytes delta > 0 OR TaskCompleted

### Consecutive no-progress threshold

| Option | Description | Selected |
|--------|-------------|----------|
| 2 turns per-agent (Recommended) | Per-agent counter. Matches ROADMAP "two consecutive" wording. Specialists idle during other agents' work don't trigger. | ✓ |
| 2 turns sprint-wide | Whole-team idle trigger; misses the specific stuck agent. | |
| 3 turns per-agent (looser) | Tolerates flaky runs but diverges from ROADMAP. | |

**User's choice:** 2 turns per-agent

### forced_progress_gate trigger action

| Option | Description | Selected |
|--------|-------------|----------|
| Block advance + InteractionGate question (Recommended) | gate.check returns False. Writes questions/<id>.md with choices [keep / restart / abort]. Human answer unblocks; counter clears. Reuses Phase 1 InteractionGate. | ✓ |
| Independent alarm event (non-blocking) | Theater agent with periodic artifact writes still slips through. | |
| Auto /freeze current agent + route to ceo | ceo doesn't exist until Phase 3. | |

**User's choice:** Block advance + InteractionGate question

---

## Cycle detector design

### Detector location

| Option | Description | Selected |
|--------|-------------|----------|
| Extend DefaultRoutingPolicy (Recommended) | Adds cycle check to decide() at team/routing_policy.py:100. Reuses routes[A→B] + routes[B→A] + recentEvents rolling window state already tracked. | ✓ |
| New CycleDetectorPolicy wrapping DefaultRoutingPolicy | Decorator; requires copying state-access boilerplate. | |
| Harness-level watcher subscribing to BeforeInboxSend | Most decoupled but rebuilds state tracking. | |

**User's choice:** Extend DefaultRoutingPolicy

### Topic hash strategy

| Option | Description | Selected |
|--------|-------------|----------|
| dedupe_key with thread_id extension (Recommended) | Priority: RuntimeEnvelope.dedupe_key → TeamMessage.request_id → sha1(content[:128]). 3-layer fallback reuses existing fields. | ✓ |
| Always sha1(content[:128]) | Same-subject paraphrasing breaks hash match; cycle missed. | |
| (message_type, subject) tuple | Subject extraction needs LLM or rules; unstable. | |

**User's choice:** dedupe_key with thread_id extension

### Window + threshold

| Option | Description | Selected |
|--------|-------------|----------|
| N=20 messages, 3 round-trips, cooldown after trigger (Recommended) | Last 20 of recentEvents window. Both A→B and B→A show ≥ 3 same-topic-hash → cycle. On trigger: InteractionGate + suppress same-topic A→B until answered. | ✓ |
| Wall-clock 10-minute window | Slow agents too lenient; fast agents too tight. Doesn't match message-count recentEvents shape. | |
| Per-sprint configurable | Premature — sprint-level config introduction too early. | |

**User's choice:** N=20 messages + 3 round-trips + cooldown

---

## auto_advance semantics

### auto_advance=True InteractionGate behavior

| Option | Description | Selected |
|--------|-------------|----------|
| InteractionGate inserted only when agent writes question (Recommended) | auto_advance=true: phase advances on its own if agents don't write questions.md; writing a question blocks until answered. Consistent with Phase 1 INT-06 + Phase 4 SPRINT-05 (Ship always human). | ✓ |
| Never insert InteractionGate | Scope decisions by agents get ignored — violates SPRINT-05 spirit. | |
| Always insert with default-accept TTL | Needs default + TTL fields on question model; Phase 2 too early. | |

**User's choice:** InteractionGate only when agent writes question

### Phase 4 Ship-phase override coordination

| Option | Description | Selected |
|--------|-------------|----------|
| SprintConductor accepts force_interactive_phases list (Recommended) | Constructor param force_interactive_phases: list[str] = []. Phases in list ignore auto_advance + force InteractionGate. Phase 2 default []. Phase 4 GstackSprintPlugin passes ['ship']. | ✓ |
| Hardcode ship in SprintConductor in Phase 2 | Couples generic engine to gstack naming — breaks upstream-PR separation. | |
| Defer all to Phase 4 | Phase 4 then changes SprintConductor public signature. | |

**User's choice:** force_interactive_phases list parameter

---

## Artifact cap policy

### Per-file 50 KB enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| ArtifactStore.write hard reject + split suggestion (Recommended) | Over 50 KB → ArtifactTooLargeError with split suggestion. Consistent with transport-layer hard validation. Agent gets immediate actionable error. | ✓ |
| Soft warn + ArtifactCapExceeded event | Write succeeds; theater prevention (cap's original purpose) weakened. | |
| Auto-truncate tail + TRUNCATED marker | Silently drops agent output; same overrun on next turn. | |

**User's choice:** ArtifactStore.write hard reject + split suggestion

### Per-phase 500 KB enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| phase-level InteractionGate compaction question (Recommended) | Over 500 KB: gate writes questions/artifact-compaction-<q>.md with choices [discard / raise cap / split phase]. Reuses Phase 1 InteractionGate. Matches ROADMAP SC#9 "compaction hook or phase-level InteractionGate". | ✓ |
| eng-mgr auto-compaction turn | eng-mgr doesn't exist until Phase 3. | |
| Hard reject subsequent writes in phase | Sprint deadlocks with no recovery path. | |

**User's choice:** phase-level InteractionGate compaction question

### Configurability

| Option | Description | Selected |
|--------|-------------|----------|
| SprintState default + CLI --artifact-cap + CLAWTEAM_ARTIFACT_CAP_KB env (Recommended) | Three-layer override: SprintState field (50*1024 / 500*1024 default), CLI --artifact-cap KB, env var via _env() helper. Matches existing CLAWTEAM_* fallback convention. | ✓ |
| Global ~/.clawteam/config.toml | No per-sprint override; clunky for one-off tuning. | |
| Hardcode Phase 2 | One-off cap bumps need code change. | |

**User's choice:** SprintState + CLI + env

---

## Sprint CLI UX

### Sprint addressability

| Option | Description | Selected |
|--------|-------------|----------|
| uuid[:8] or prefix match, ambiguity raises error (Recommended) | `sprint status a1b2` matches full or prefix; ambiguous prefix → AmbiguousSprintError(candidates). Git short-sha style, consistent with uuid[:8] convention. | ✓ |
| Full uuid[:8] required | No prefix matching; copy-paste UX slightly worse. | |
| Slug aliases (goal-derived) | Collision suffix logic + list-display duplicates complicate. | |

**User's choice:** uuid[:8] or prefix match

### sprint list default scope

| Option | Description | Selected |
|--------|-------------|----------|
| Require --team or CLAWTEAM_TEAM env (Recommended) | `sprint list` without --team and without env → MissingTeamError. Consistent with `team show` / `task list` behavior. Phase 7 cross-team attend is separate command. | ✓ |
| Default list all teams | Inconsistent with other commands. | |
| Two modes (--team vs prompt) | Extra code path for marginal UX. | |

**User's choice:** Require --team or CLAWTEAM_TEAM

### --json output shape

| Option | Description | Selected |
|--------|-------------|----------|
| Wrapper envelope {ok, data, warnings, error} (Recommended) | All sprint commands: {ok, data, warnings, error}. Error form: {ok:false, error:{code, message}}. MCP tools parse without per-command logic. | ✓ |
| Flat data per command | Warnings / errors have nowhere to go; stderr split inconsistent. | |
| Each command custom envelope | Downstream parsing extra work. | |

**User's choice:** {ok, data, warnings, error} envelope

---

## Claude's Discretion

- Exact pydantic field names within the six gstack artifact schemas (Phase 3 fills the six schemas; Phase 2 ships the registry + base model)
- Internal structure of test_verify_cache.json (planner can add fields as useful)
- Internal layout of freeze.json and freeze_audit.jsonl (field names planner's pick)
- EvidenceGate compaction-question option-list wording (planner or Phase 3 agent prompts own the human-facing copy)
- `SprintConductor` concurrency primitive choice (asyncio.Lock vs threading.RLock — Phase 2 has no concurrency requirement; Phase 7 verifies 10-concurrent)
- Test fixture layout for Phase 2 tests (planner picks, consistent with existing flat tests/ layout)

## Deferred Ideas

### To Phase 3
- Six concrete EvidenceSchema pydantic models (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro) + required section lists
- `/careful` destructive-command blacklist tuning against real gstack usage
- Role-prompt reassertion of envelope fields (persona / step_label / done)

### To Phase 4
- Ship-phase force_interactive_phases=['ship'] wiring in GstackSprintPlugin
- SmartReviewRouter using the ReviewRouter Protocol forward-declared in Phase 1 RFC 001 §4.3b
- Cross-agent verification gates (qa verifies engineer's test-report hash; reviewer verifies designer's forcing-question coverage)
- Mid-review SHA-pinning thrash detection (QUALITY-09)

### To Phase 7
- CycleDetected event subscribed by AttentionQueue (digest view)
- ForcedProgressTriggered surfacing into attention digest
- 10-concurrent-sprint load test for SprintConductor (CORE-06)
- Cost observability, rate-limit-aware scheduling

### Longer-horizon
- LLM-based artifact content validator (declined at Phase 2 to avoid agent dependency inside a gate)
- Sprint slug aliases (declined — prefix matching covers UX)
- Wall-clock cycle detection window (declined — message-count window aligns with recentEvents)
