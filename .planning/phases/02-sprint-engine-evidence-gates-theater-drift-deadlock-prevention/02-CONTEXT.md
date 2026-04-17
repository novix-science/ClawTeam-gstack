# Phase 2: Sprint Engine, Evidence Gates & Theater/Drift/Deadlock Prevention - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Ship a single-sprint end-to-end runnable sprint engine layered on Phase 1's
`PhaseRegistry` + `SprintState` + `InteractionGate` primitives. Phase 2 lands:

1. `SprintConductor` — drives one team's N sprints, owns phase-transition
   dispatch, pause/resume, artifact store wiring.
2. `EvidenceGate` — extends `ArtifactRequiredGate`; validates artifact content
   (schema + stub detection + test rerun), not just presence.
3. Structured response envelope — `TeamMessage` gains `persona` / `step_label`
   / `done`; durable artifacts carry matching YAML frontmatter; validated at
   `transport.deliver()` and `ArtifactStore.write()`.
4. Theater / no-progress detector — per-agent turn counter, artifact-bytes +
   TaskCompleted definition of progress, `forced_progress_gate` blocks
   advance + inserts InteractionGate question.
5. Cycle detector — extends `DefaultRoutingPolicy`; detects A↔B round-trips
   on same topic-hash; breaks via InteractionGate + topic suppression.
6. Safety-rail primitives — `/careful`, `/freeze`, `/guard`, `/unfreeze` as
   harness-level `Before*` event vetoes + `FreezeRegistry` singleton with
   sprint-scoped persistence + `freeze_audit.jsonl`.
7. Artifact caps — per-file 50 KB hard reject, per-phase 500 KB via phase-level
   InteractionGate compaction; three-layer configurability.
8. Sprint CLI surface — `clawteam sprint start / status / show / list / pause
   / resume`, all with `--json` envelope.
9. `SprintConductor.force_interactive_phases` hook reserved for Phase 4's
   Ship-phase human-approval override.

**Out of scope (Phase 2 does NOT ship):**

- 11-agent gstack team, 7-phase `GstackSprintPlugin`, per-role methodology
  prompts — Phase 3.
- Interactive state machines (`/office-hours`, `/design-consultation`,
  `/investigate`), SmartReviewRouter, reviewer decorrelation — Phase 4.
- Tool-heavy skills (`/ship`, `/codex`, `/canary`, `/benchmark`, `/browse`,
  `/design-shotgun`), Team memory store with provenance + decay — Phase 5/6.
- AttentionQueue, cross-sprint digest, cost dashboards, concurrency caps —
  Phase 7.
- Helper-agent spawning (engineer sub-worktrees) — deferred to v1.x per
  FEATURES P2.

Phase 2 must keep the Phase 0 regression matrix
(`tests/test_template_regression_matrix.py`) green across all 6 packaged
templates. Every new primitive is additive; existing `ArtifactRequiredGate`,
`HumanApprovalGate`, `DefaultRoutingPolicy`, `TeamMessage`, `HarnessPlugin`
semantics remain unchanged. The gstack sprint engine is an opt-in plugin
surface; software-dev / hedge-fund / code-review / harness-default /
research-paper / strategy-room continue to use the old gate set.

</domain>

<decisions>
## Implementation Decisions

### EvidenceGate family (SPRINT-02, QUALITY-08, ROADMAP SC#2)

- **D-01:** `EvidenceGate` at `clawteam/harness/evidence_gate.py` subclasses
  the existing `ArtifactRequiredGate` (`harness/phases.py:64`). Base class
  still does presence check; `EvidenceGate.check()` additionally runs
  content validation on each required artifact. A `GstackSprintPlugin` in
  Phase 3 chooses `EvidenceGate`; existing templates keep using
  `ArtifactRequiredGate`.

- **D-02:** Per-artifact validation uses **pydantic frontmatter + required
  section checklist** (extends Phase 1 D-08 pattern). Each gstack artifact
  type (`DesignDoc`, `PlanDoc`, `TestReport`, `ReviewReport`, `ShipNotes`,
  `Retro`) has a pydantic model registered in a `EvidenceSchemaRegistry` +
  a list of required `##` section headers that must appear in the body.
  Plugins register new artifact schemas via the same contribute hook family
  as Phase 1; `GstackSprintPlugin` in Phase 3 registers the six gstack
  schemas.

- **D-03:** Stub / lazy-content detection is **3-layer**:
  1. Frontmatter required fields all non-empty (pydantic handles this).
  2. Each required `##` section's body ≤ 100 bytes (between two newlines) =
     stub → fail.
  3. Regex blacklist on artifact body: `/\bTBD\b/i`, `/\bTODO\b/`,
     `/\bxxx+\b/i`, `/\bplaceholder\b/i`, `/Lorem ipsum/i` → fail with
     offending line number.

- **D-04:** `test-report.md` gate runs `SuccessCriterion.test_command`
  (`harness/contracts.py:19`, currently defined but NEVER executed
  anywhere — confirmed via grep) **synchronously** during
  `EvidenceGate.check()`. Uses a content-hash cache on the
  `test-report.md` artifact: if the artifact hash is unchanged since the
  last successful rerun, skip re-execution. Cache entry shape:
  `{artifact_hash, test_ids, last_run_at, last_exit_code}`, persisted to
  `~/.clawteam/teams/<team>/sprints/<sprint_id>/test_verify_cache.json`
  via `file_locked()`. Test output hash + exit code + timestamp update
  `SuccessCriterion.verified` / `verified_at` / `verified_by="evidence_gate"`.

- **D-05:** `ship-notes.md` EvidenceGate validates (beyond D-02/D-03) that
  the `deploy_url` frontmatter field dereferences with HTTP HEAD →
  2xx/3xx, with a 10s timeout; on failure, gate returns False with the
  response body or timeout reason. Phase 5's `/ship` wires
  `clawteam.sre.canary`'s URL into this frontmatter. Phase 2 ships the
  dereferencer + the schema; actual deploy target is Phase 5.

### Response envelope (SC#4, QUALITY-01, SKILL-09)

- **D-06:** `TeamMessage` (`team/models.py:90`) adds three new required
  fields, populated by every agent turn:
  - `persona: str` — the agent role asserting this turn (must match the
    caller's registered role; harness verifies).
  - `step_label: str` — free-form marker like `"plan:2/5"` or
    `"review:cross-cutting"`.
  - `done: bool` — explicit turn-done signal; `False` means the agent
    will emit more messages/artifacts on the current task; `True` means
    the agent is handing off or waiting.
  Existing fields (`content`, `summary`, `plan_file`, `feedback`, etc.)
  are unchanged; the three new fields are additive pydantic fields with
  no default (required at write time).

- **D-07:** Durable artifacts written via `ArtifactStore.write()`
  (`harness/artifacts.py:22`) carry a matching YAML frontmatter block at
  the top of the file:
  ```yaml
  ---
  persona: engineer
  step_label: build:1/3
  done: false
  artifact_type: design-doc   # or plan-doc, test-report, etc.
  created_at: 2026-04-17T...
  ---
  ```
  A single pydantic model (`TurnEnvelope`) validates both the
  `TeamMessage` fields and the frontmatter block — same schema, two
  serialization surfaces.

- **D-08:** Validation is enforced at **two entry points, both hard-fail**:
  - `transport/base.py::deliver()` validates `TeamMessage.persona` +
    `step_label` + `done` on every deliver; rejects with
    `MalformedEnvelopeError` on missing/invalid.
  - `ArtifactStore.write()` parses frontmatter and runs the same
    `TurnEnvelope` pydantic model; rejects with same error type on
    malformed or missing block.
  Both points are natural envelope checkpoints (they're also where
  per-turn counter increments happen, see D-14).

- **D-09:** Malformed-envelope policy:
  - **First violation per agent**: emit
    `events/types.py::MalformedEnvelope(agent, violation, turn_id)` event,
    still deliver / write (warn mode). Agent receives structured error in
    the MCP / CLI response.
  - **Consecutive 8+ violations by same agent**: emit `DriftRegression`
    event + subsequent messages / artifacts from this agent hard-reject
    until the agent successfully produces one valid envelope
    (counter resets on success).
  - SC#4's "echo a peer's voice for 8+ consecutive turns" drift detector
    is a separate detector (compares `persona` field against actual
    sender's role assignment, tracked on the same per-agent
    violation-window struct).

### Safety-rail primitives (SAFETY-01..04, SC#8)

- **D-10:** Two new `Before*` events in `events/types.py` following the
  existing `veto: bool` pattern (`BeforeWorkerSpawn` / `BeforeTaskCreate`
  / `BeforeInboxSend` / `BeforeWorkspaceMerge` at
  `events/types.py:25+`):
  - `BeforeToolCall(agent_name, tool_name, args, veto)` — emitted by the
    MCP server wrapper (`mcp/server.py::translate_error` seam) and the
    CLI command interception layer before any tool that could mutate
    state runs.
  - `BeforeFileWrite(agent_name, path, size_bytes, veto)` — emitted by
    `ArtifactStore.write()` and any `workspace/manager.py` write paths.
  Handlers set `event.veto = True` to cancel, per existing EventBus
  convention (`events/bus.py:95`).

- **D-11:** `FreezeRegistry` singleton at
  `clawteam/harness/freeze_registry.py` (structural twin of Phase 1's
  `PhaseRegistry`). Holds `dict[agent_name, set[Path]]` + sprint-scoped
  `frozen_globs: set[str]` for path patterns. Persisted to
  `~/.clawteam/teams/<team>/sprints/<sprint_id>/freeze.json` via
  `file_locked()` + `atomic_write_text` — sprint pause/resume (CORE-07)
  rehydrates this file. EventBus handlers for the two new `Before*`
  events + `WorkspaceManager` guard paths + MCP `translate_error`
  wrapper all consult `get_freeze_registry()`.

- **D-12:** Agent awareness is via **structured tool errors**, not
  pre-spawn env var or mailbox push:
  - When `BeforeToolCall` / `BeforeFileWrite` is vetoed by
    `FreezeRegistry`, the caller raises
    `FrozenPathError("<path> is /freeze-locked by <who_froze>; unfreeze via /unfreeze <path>")`.
  - MCP `translate_error` wraps it; CLI interception layer prints it;
    Claude/Codex/Gemini CLIs read the error response and self-correct
    on the next turn (tested by the safety-rail unit tests).
  Runtime freeze/unfreeze changes apply immediately — no restart needed.

- **D-13:** `/unfreeze` audit:
  - New event type `FreezeChange(action: "freeze"|"unfreeze", path, agent,
    reason, actor)` in `events/types.py`.
  - Dedicated append-only JSONL at
    `~/.clawteam/teams/<team>/sprints/<sprint_id>/freeze_audit.jsonl`
    (mirrors the `harness/exit_journal.py` pattern).
  - Every `/freeze` / `/unfreeze` / `/guard` invocation writes an entry
    with `{ts, action, path, agent, reason, actor, sprint_id}`.
  - `/careful` (destructive-command detector) lives as an EventBus
    subscriber on `BeforeToolCall` with a regex blacklist (`rm -rf`,
    `git reset --hard`, `git push --force`, `DROP TABLE`,
    `DELETE FROM .* WHERE`) that emits a warning event but does NOT
    veto by default; requires explicit `--careful` sprint config to
    veto (matches gstack native `/careful` semantics).

### Theater / no-progress rule (QUALITY-11, SC#6)

- **D-14:** "Turn" is operationally defined as **one successful
  `transport.deliver()` OR one successful `ArtifactStore.write()` by a
  given agent**. Turn counter state lives on `SprintState` as
  `turn_counters: dict[agent_name, int]` (pydantic field). Per-agent
  counter increments on each successful deliver or write; the two
  envelope-validation hook points (D-08) are exactly the turn-counting
  sites — one hook does both jobs.

- **D-15:** "Progress" is defined as either:
  - `sum(artifact.size_bytes for artifact in turn_delta_artifacts) > 0`
    since the previous turn snapshot — i.e., **any net-positive artifact
    bytes delta** counts, including small corrections (consciously
    loose; Phase 2 rejects the "micro-edit doesn't count" option to
    avoid false-positive escalations).
  - OR a `TaskCompleted` event fired during the turn
    (`events/types.py:83`, already exists).
  Mailbox messages by themselves don't count (chat ≠ progress, per
  ROADMAP SC#6 "artifact bytes").

- **D-16:** Escalation threshold: **2 consecutive no-progress turns
  per-agent, not sprint-wide**. Rationale: sprint-wide would flag
  specialist agents (security, designer) as theater while they wait for
  engineer/reviewer to ship; per-agent correctly targets the specific
  stalled worker.

- **D-17:** `forced_progress_gate` at
  `clawteam/harness/forced_progress_gate.py` subclasses `PhaseGate`.
  - On trigger: gate.check() returns False; gate writes
    `sprint/<id>/questions/<q>.md` using the Phase 1 D-08 Q/A schema,
    type = `multi-choice`, choices =
    `[A: "keep waiting — agent will ship next turn", B: "restart agent from clean state", C: "abort sprint"]`.
  - The existing `InteractionGate` then blocks advance until a matching
    `answers/<q>.md` arrives.
  - On answer: clear no-progress counter for the affected agent;
    forced_progress_gate passes on next check.
  - `forced_progress_gate` is composed with `EvidenceGate` on every
    phase transition (`PhaseRunner._gates[phase]` grows by one). Both
    gates must pass.

### Cycle detector (QUALITY-02, SC#5)

- **D-18:** Cycle detection lives in
  `clawteam/team/routing_policy.py::DefaultRoutingPolicy.decide()`
  (extending the existing implementation at lines 93+). Added check:
  before the existing throttle logic, scan the cross-pair recentEvents
  for round-trip cycles. `DefaultRoutingPolicy` already holds
  `routes[A→B]` and `routes[B→A]` with `recentEvents` rolling window
  state — reuse.

- **D-19:** "Topic" hash priority chain (first non-empty wins):
  1. `RuntimeEnvelope.dedupe_key` (already exists at
     `routing_policy.py:63`).
  2. `TeamMessage.request_id` (already exists at `team/models.py:102`).
  3. `sha1(TeamMessage.content[:128])` as last resort.
  Phase 4 interactive skills (`/office-hours` etc.) set `dedupe_key` or
  `request_id` explicitly for stable thread identity; Phase 2 works
  without requiring agents to cooperate.

- **D-20:** Window = last 20 entries in `recentEvents` (the existing
  rolling window tails at 50). Threshold: A→B and B→A each show ≥ 3
  entries with the same topic-hash within the same 20-message window →
  declare cycle.

- **D-21:** On cycle trigger:
  - Emit `events/types.py::CycleDetected(pair, topic_hash, route_keys, window_size)`.
  - Suppress further A→B messages with the same topic-hash until
    resolution (flag stored in `routes[route_key].suppressed_topics`).
  - Write `sprint/<id>/questions/<q>.md` via the Phase 1 schema; type =
    `freeform`, body describes the cycle + recent exchange summary;
    human answer lifts suppression (or the human manually rewrites the
    conversation scope).
  - AttentionQueue (Phase 7) subscribes to `CycleDetected` later; Phase
    2 uses only InteractionGate.

### Sprint engine & CLI (CORE-05, CORE-07, INT-06, UX-02..05, UX-09)

- **D-22:** `SprintConductor` at `clawteam/sprint/conductor.py`:
  - Constructor: `SprintConductor(team_name, *, force_interactive_phases: list[str] = [], artifact_cap_bytes: int | None = None, phase_artifact_cap_bytes: int | None = None)`.
  - Owns `asyncio`/`threading`-safe state for one team's sprints; Phase
    2 only handles single-sprint correctness (10-concurrent verified
    in Phase 7).
  - `force_interactive_phases` is a reserved hook: any phase name in
    this list forces insertion of `InteractionGate` on advance,
    ignoring `SprintState.auto_advance`. Phase 2 defaults to `[]`;
    Phase 4's `GstackSprintPlugin` passes `["ship"]` (SPRINT-05).

- **D-23:** `auto_advance` semantics (INT-06):
  - When `SprintState.auto_advance = True`: `InteractionGate` is
    **only** inserted on a transition when a phase agent has written
    one or more unanswered `sprint/<id>/questions/<q>.md` files during
    the phase. If no questions, phase advances automatically once
    `EvidenceGate` + `forced_progress_gate` + any other registered
    gates pass.
  - When `SprintState.auto_advance = False`: `InteractionGate` is
    inserted on every transition; human must write an approval
    `answers/<q>.md` (or an explicit `approve.md` sentinel) before
    advance.
  - `force_interactive_phases` overrides both modes for listed phases
    (Phase 4 Ship).

- **D-24:** Sprint CLI surface in `clawteam/cli/commands.py` adds a
  `sprint` sub-app:
  - `clawteam sprint start --team <name> --goal "..." [--auto-advance] [--artifact-cap <kb>] [--phase-artifact-cap <kb>]` — new sprint, prints `{id, goal, current_phase}`; requires `--team` or `$CLAWTEAM_TEAM`.
  - `clawteam sprint status <id|prefix>` — current phase + participants + pending-questions count + most-recent artifact name.
  - `clawteam sprint show <id|prefix>` — full phase_history + artifact list + question/answer list.
  - `clawteam sprint list` — requires `--team <name>` or `CLAWTEAM_TEAM` env; else `MissingTeamError`. No default scanning of all teams.
  - `clawteam sprint pause <id|prefix>` — persist checkpoint, release active gate waits.
  - `clawteam sprint resume <id|prefix>` — rehydrate `SprintState`, replay the last pending phase-transition event.
  Every sub-command honors the existing global `--json` flag.

- **D-25:** Sprint addressability: `<id|prefix>` accepts the full
  `uuid[:8]` id OR any unambiguous prefix. Ambiguous prefix → raise
  `AmbiguousSprintError(prefix, candidates: list[str])` listing the
  matches. No slug aliases (keeps the codebase consistent with
  `AgentIdentity`'s `uuid[:8]` convention and `SprintContract.id`).

- **D-26:** `--json` envelope shape is **uniform across every sprint
  command**:
  ```json
  {"ok": true, "data": {<command-specific>}, "warnings": [], "error": null}
  ```
  Error form:
  ```json
  {"ok": false, "data": null, "warnings": [], "error": {"code": "<MACHINE_CODE>", "message": "<human>"}}
  ```
  Matches the existing `clawteam` CLI `--json` pattern (MCP tools can
  parse without per-command logic).

### Artifact cap policy (SC#9)

- **D-27:** Per-file cap defaults to **50 KB** (SC#9). Enforcement at
  `ArtifactStore.write()`: if `len(content) > cap`, raise
  `ArtifactTooLargeError(artifact_name, size_bytes, cap_bytes, suggestion="split into <name>-part1.md etc. or raise cap via --artifact-cap")`.
  Hard reject; no soft-warn, no silent truncation.

- **D-28:** Per-phase cap defaults to **500 KB** (SC#9, summed across
  all artifacts registered under the current phase). On overflow, the
  `EvidenceGate` (NOT `ArtifactStore.write`) returns False on next
  check; gate writes a phase-level
  `sprint/<id>/questions/artifact-compaction-<q>.md`, type =
  `multi-choice`, choices =
  `[A: "discard artifacts: <pick list>", B: "raise cap to <value>", C: "split phase into sub-phases"]`.
  InteractionGate unblocks on `answers/<q>.md`; `EvidenceGate` applies
  the chosen remedy (deletes / updates cap / splits).

- **D-29:** Cap configurability (three-layer override, highest wins):
  1. `SprintState.artifact_cap_bytes` / `phase_artifact_cap_bytes`
     fields (persisted; default 50\*1024 / 500\*1024).
  2. `clawteam sprint start --artifact-cap <kb>` /
     `--phase-artifact-cap <kb>` CLI flags (writes into `SprintState`
     at creation time).
  3. `CLAWTEAM_ARTIFACT_CAP_KB` / `CLAWTEAM_PHASE_ARTIFACT_CAP_KB`
     environment variables (read via the existing `_env` helper in
     `clawteam/identity.py`, matches the `CLAWTEAM_* / OH_* /
     CLAUDE_CODE_*` multi-generation convention).

### Claude's Discretion

- Exact pydantic field names / aliases within the six gstack artifact
  schemas (D-02) — planner picks, consistent with Phase 1 D-08
  frontmatter convention.
- Internal structure of `test_verify_cache.json` (D-04) — planner can
  add fields (e.g., test framework version, last-stdout-hash) as useful.
- Internal layout of `freeze.json` and `freeze_audit.jsonl` (D-11 /
  D-13) — planner picks field names.
- EvidenceGate compaction-question option-list wording (D-28) — planner
  or Phase 3 agent prompt owns the human-facing copy.
- Whether `SprintConductor` uses `asyncio.Lock` or `threading.RLock`
  for its state — no concurrency requirement in Phase 2 (10-sprint
  concurrency verified in Phase 7); planner picks the simpler option
  that remains upgradeable.
- Test fixture layout for phase-2 tests — planner picks consistent with
  existing `tests/` flat layout and Phase 1's conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project & requirements layer

- `.planning/PROJECT.md` — constraints (backwards-compat, upstream-compat,
  additive-only, Python 3.10+, no new required runtime deps for core,
  identity env multi-generation preservation)
- `.planning/REQUIREMENTS.md` — Phase 2 closes 21 REQ-IDs: CORE-05, CORE-07,
  INT-06, SPRINT-01, SPRINT-02, SKILL-09, SAFETY-01, SAFETY-02, SAFETY-03,
  SAFETY-04, QUALITY-01, QUALITY-02, QUALITY-03, QUALITY-06, QUALITY-08,
  QUALITY-11, UX-02, UX-03, UX-04, UX-05, UX-09
- `.planning/ROADMAP.md §Phase 2` — 10 success criteria (full list); also
  §Phase 1 (SprintState/InteractionGate shipped) and §Phase 4 (Ship-phase
  always-human, smart router) for downstream wiring context
- `.planning/phases/01-core-harness-extensions/01-CONTEXT.md` — all 8
  Phase 1 decisions (D-01..D-08); critically D-05 (sprint_id = uuid[:8],
  persistence path) and D-06..D-08 (InteractionGate, Q/A schema)

### Upstream spec (ship artifact)

- `docs/rfcs/001-phase-registry.md` — Phase 1 RFC (normative for
  PhaseRegistry + SprintState + InteractionGate); §4.4 SprintState shape
  is the schema this phase extends with turn_counters and cap fields

### Existing ClawTeam code to follow (patterns, not edit targets except where noted)

- `clawteam/harness/phases.py` — `PhaseGate` (§56), `ArtifactRequiredGate`
  (§64), `HumanApprovalGate` (§91), `PhaseRunner.register_gate` (§113) —
  subclass + register patterns
- `clawteam/harness/contracts.py` — `SuccessCriterion.test_command` (§19),
  `verified` / `verified_at` / `verified_by` (§20-22) — the unwired
  field Phase 2 must connect
- `clawteam/harness/artifacts.py` — `ArtifactStore.write()` (§22-31) + meta.json
  pattern — envelope + cap + stub-detection checkpoint
- `clawteam/harness/exit_journal.py` — append-only JSONL pattern for
  audit logs (freeze_audit.jsonl mirrors this)
- `clawteam/events/bus.py` — `EventBus` (§42) with veto semantics on Before*
  events (§95: "caller must check event.veto"); Before*/After* event
  family is the safety-rail interception point
- `clawteam/events/types.py` — existing Before* + After* events (§25-163);
  new events (`BeforeToolCall`, `BeforeFileWrite`, `FreezeChange`,
  `MalformedEnvelope`, `DriftRegression`, `CycleDetected`,
  `ArtifactCapExceeded`, `ForcedProgressTriggered`) follow shape
- `clawteam/team/models.py::TeamMessage` (§90-122) — add envelope fields
  here; existing fields unchanged
- `clawteam/team/routing_policy.py::DefaultRoutingPolicy` (§50-156) —
  `RuntimeEnvelope.dedupe_key` (§63), `recentEvents` rolling window,
  throttling state — cycle detector extends this
- `clawteam/transport/base.py::Transport.deliver` — envelope validation
  entry point #1
- `clawteam/mcp/server.py` + `clawteam/mcp/helpers.py::translate_error` —
  MCP tool wrapping seam for BeforeToolCall + FrozenPathError
- `clawteam/workspace/manager.py` — WorkspaceManager write paths consult
  FreezeRegistry before git operations
- `clawteam/cli/commands.py` — Typer app; `sprint` sub-app extends this
- `clawteam/fileutil.py::file_locked` / `atomic_write_text` — all new
  JSON persistence uses these (freeze.json, test_verify_cache.json,
  freeze_audit.jsonl append writes)
- `clawteam/identity.py::_env` — env-var multi-generation fallback
  helper; `CLAWTEAM_ARTIFACT_CAP_KB` reads through this

### Phase 0 test gates (must stay green)

- `tests/test_template_regression_matrix.py` — 12 parametrized cases
  across all 6 packaged templates. Phase 2 cannot break any of these.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `ArtifactRequiredGate` (`harness/phases.py:64`) — structural analog for
  `EvidenceGate`: same constructor shape, `check(state) -> tuple[bool, str]`
  return, registered via `PhaseRunner.register_gate`.
- `PhaseGate` ABC (`harness/phases.py:56`) — new gates
  (`forced_progress_gate`, `EvidenceGate`) subclass this.
- `EventBus.emit() -> event.veto` pattern (`events/bus.py:95`) — the
  canonical cross-cutting hook for `/careful` / `/freeze` / `/guard` —
  zero new infrastructure required, just new event types.
- `RuntimeEnvelope` dataclass (`team/routing_policy.py:50-71`) with
  `dedupe_key`, `evidence`, `recommended_next_action` — cycle detector
  reads dedupe_key for topic identity; envelope for artifact attribution
  references evidence chain.
- `DefaultRoutingPolicy` (`team/routing_policy.py:93-156`) — existing
  per-pair `routes[route_key]` state + `recentEvents` rolling window +
  `_refresh_route` / `_append_event` / `_append_pending` helpers — cycle
  detector adds a check method and new event append.
- `TeamMessage` pydantic v2 (`team/models.py:90-122`) — already accepts
  optional plan/feedback/status/reason fields; adding persona /
  step_label / done is a natural extension.
- `file_locked()` + `atomic_write_text()` (`fileutil.py`,
  `team/snapshot.py:21`) — all new persistence (freeze.json,
  test_verify_cache.json, freeze_audit.jsonl, turn_counters inside
  SprintState) uses these.
- `exit_journal.py` append-only JSONL pattern — template for
  freeze_audit.jsonl.
- `uuid.uuid4().hex[:8]` id convention (`phases.py:42`, `contracts.py:28`)
  — reuse for all new ids (question id, turn_id, cycle_id).

### Established Patterns

- **Plugin contribute hooks with empty-collection defaults** — Phase 1
  added `contribute_phases`, `contribute_phase_roles`,
  `contribute_review_routers`. Phase 2 needs one more:
  `contribute_evidence_schemas() -> dict[str, EvidenceSchema]` with
  default `{}` — `GstackSprintPlugin` in Phase 3 uses this.
- **Before* events with `veto: bool`** — existing
  BeforeWorkerSpawn/BeforeTaskCreate/BeforeInboxSend/BeforeWorkspaceMerge
  are the shape; `BeforeToolCall` and `BeforeFileWrite` add two more.
- **Pydantic v2 models for durable state** — `SprintState` from Phase 1;
  Phase 2 extends with `turn_counters: dict[str, int]`,
  `artifact_cap_bytes`, `phase_artifact_cap_bytes`; never introduces
  `Enum` for string-enumerated values (Phase/AgentRole stay open `str`
  per `harness/phases.py:19-20`).
- **Typer `sub_app = typer.Typer()` sub-command pattern** already exists
  in `cli/commands.py` (team, task, mailbox, etc.); `sprint` follows.
- **`{ok, data, warnings, error}` JSON envelope** for CLI commands — the
  existing global `--json` convention; sprint commands align.
- **File-locked JSON under `~/.clawteam/teams/<team>/sprints/<id>/`** —
  Phase 1 pinned this path (D-05); Phase 2 colocates freeze.json,
  test_verify_cache.json, freeze_audit.jsonl here.

### Integration Points

- `PhaseRunner._gates[phase]` (`harness/phases.py:111`) grows by up to 3
  entries per gstack phase: `EvidenceGate(artifacts)` +
  `forced_progress_gate` + `InteractionGate`. Registration happens when
  `GstackSprintPlugin.on_register` runs (Phase 3); Phase 2 ships the
  gate classes + the composition order (`EvidenceGate` first,
  `forced_progress_gate` second, `InteractionGate` last — so advance
  blocks on the most actionable failure first).
- `ArtifactStore.write()` gains a pre-write hook chain: size-cap check
  → envelope validation → FreezeRegistry consult → size-cap phase-total
  check → atomic write. If any fails, write is rejected and the
  corresponding event (`ArtifactTooLargeError`,
  `MalformedEnvelopeError`, `FrozenPathError`) raises.
- `transport/base.py::Transport.deliver` gains a pre-deliver hook chain:
  envelope validation → cycle-detector consult → BeforeInboxSend event
  (existing) → actual deliver. Cycle suppression short-circuits here;
  existing throttle logic in `DefaultRoutingPolicy` is unchanged.
- `SprintConductor` sits above `PhaseRunner` — owns the sprint-level
  loop and surfaces the CLI commands. `HarnessOrchestrator` from
  `harness/orchestrator.py` is per-harness-run (older model);
  `SprintConductor` is per-team + per-sprint (new Phase 2 layer,
  composes with the orchestrator rather than replacing).

</code_context>

<specifics>
## Specific Ideas

**User correction pattern (2026-04-17, this session):** user pushed back
on the initial gray-area list with "这些像是原本 clawteam 责任范围内的事情, 即
swarm harness, clawteam 的 implementation 是什么" (these sound like
clawteam's swarm-harness responsibilities — what's already implemented?).
Triggered a full codebase scan that resolved an ambiguity in 6 of 8
original gray areas by following existing ClawTeam conventions rather
than re-litigating them.

**Key pattern lessons for downstream planning:**

1. **Build on the routing_policy state machine.** `DefaultRoutingPolicy`
   already carries per-pair `routes[route_key]` state with a
   `recentEvents` rolling window and throttling logic — cycle detection
   is an extension of this existing state machine, not a new
   infrastructure layer. Don't introduce parallel trackers.

2. **TurnEnvelope is one pydantic model, two serialization surfaces.**
   `TeamMessage` fields and artifact frontmatter both validate against
   the same model. Don't diverge — any drift detection (SC#4) relies on
   the same field set regardless of channel.

3. **FreezeRegistry mirrors PhaseRegistry's shape** — singleton +
   contributor hook + file-locked persistence with sprint-scoped path.
   Keeping the two registries structurally similar makes them easier to
   extend (a `Registry` protocol could eventually live as a shared
   substrate in `clawteam/harness/`).

4. **Test-command is already part of SuccessCriterion — Phase 2 wires
   it.** `SuccessCriterion.test_command` has existed as a field since
   before gstack work began. Phase 2's EvidenceGate is the first
   executor. The schema stays pydantic v2-compatible for Phase 0
   regression matrix.

5. **Two new events ≠ two new subsystems.** `BeforeToolCall` and
   `BeforeFileWrite` are additions to the existing event family with
   veto semantics — no new bus, no new priority scheme.

**Pattern lesson for Phase 3 (downstream):** the six gstack artifact
schemas (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro)
are declared in Phase 3's `GstackSprintPlugin` via the
`contribute_evidence_schemas` hook (new in this Phase 2). Phase 3 does
not write the validator — just the schemas + required-section lists.
Phase 2's EvidenceGate handles everything else.

**Pattern lesson for Phase 4 (downstream):** `SprintConductor`'s
`force_interactive_phases` parameter is the seam for Phase 4's Ship-phase
human-approval override (SPRINT-05). `GstackSprintPlugin` passes
`["ship"]`; no `SprintConductor` internal change needed.

</specifics>

<deferred>
## Deferred Ideas

**To Phase 3 (Gstack Team Template & Methodology Port):**
- Six concrete `EvidenceSchema` pydantic models (DesignDoc, PlanDoc,
  TestReport, ReviewReport, ShipNotes, Retro) with required section
  lists — Phase 2 ships the registry; Phase 3 fills the six schemas.
- `/careful` destructive-command blacklist regex tuning against real
  gstack usage patterns — Phase 2 ships the hook + a baseline list;
  Phase 3 / gstack.toml tunes per user feedback.
- Role-prompt reassertion of envelope fields (persona / step_label /
  done) — gstack role prompts will instruct each agent how to fill
  these. Phase 2 ships the schema + enforcement; Phase 3 ships the
  prompts.

**To Phase 4 (Interactive / Routing / Verification):**
- Ship-phase `force_interactive_phases=["ship"]` wiring in
  `GstackSprintPlugin` (SPRINT-05).
- SmartReviewRouter using the `ReviewRouter` Protocol forward-declared
  in Phase 1 RFC 001 §4.3b — Phase 2 doesn't touch routing beyond the
  cycle detector.
- Cross-agent verification gates (qa verifies engineer's test-report
  hash; reviewer verifies designer's forcing-question coverage) —
  Phase 4 extends `EvidenceGate` with cross-referencing.
- Mid-review SHA-pinning thrash detection (QUALITY-09) — Phase 4.

**To Phase 7 (Parallel Sprints):**
- `CycleDetected` event subscribed by AttentionQueue (digest view).
- `ForcedProgressTriggered` surfaces into the attention digest.
- 10-concurrent-sprint load test for `SprintConductor` (CORE-06).
- Cost observability, rate-limit-aware scheduling.

**Longer-horizon:**
- LLM-based artifact content validator as optional plugin (declined at
  Phase 2 to avoid introducing an agent dependency inside a gate).
- Sprint slug aliases (declined — prefix matching covers the UX win
  without slug-collision complexity).
- Wall-clock cycle detection window (declined — message-count window
  aligns with existing `recentEvents` shape).

</deferred>

---

*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Context gathered: 2026-04-17*
