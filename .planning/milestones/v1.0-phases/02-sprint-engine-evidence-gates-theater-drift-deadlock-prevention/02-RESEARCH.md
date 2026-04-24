# Phase 2: Sprint Engine, Evidence Gates & Theater/Drift/Deadlock Prevention — Research

**Researched:** 2026-04-17
**Domain:** Multi-agent sprint engine + safety primitives (Python stdlib + pydantic v2 + Typer, additive to existing ClawTeam substrate)
**Confidence:** HIGH for stack & internal patterns; MEDIUM for borrowed heuristics (circuit-breaker thresholds, theater detection signals); LOW for none (every finding either verified against codebase or cited to a specific source).

---

## Summary

Phase 2 sits on top of Phase 1's `PhaseRegistry` / `SprintState` / `InteractionGate` primitives and adds ten layered capabilities: a `SprintConductor`, an `EvidenceGate` family, a `TurnEnvelope` protocol (shared by `TeamMessage` + artifact frontmatter), a theater / no-progress detector, a transport-level cycle detector, safety-rail primitives (`/careful`, `/freeze`, `/guard`, `/unfreeze`), artifact caps, a `sprint` CLI sub-app, and a freeze audit log. The decisions in `02-CONTEXT.md` (D-01..D-29) fix the shape of all 10 capabilities; this research pass verifies the external patterns those decisions extend, selects concrete library choices, and pins version numbers.

Every decision in CONTEXT.md has a prior-art grounding: EvidenceGate maps cleanly onto the EviBound governance framework [CITED: arxiv.org/abs/2511.05524], the theater detector shares Paperclip issue #390's circuit-breaker design [CITED: github.com/paperclipai/paperclip/issues/390], the cycle detector re-uses the existing `DefaultRoutingPolicy.recentEvents` rolling window [VERIFIED: clawteam/team/routing_policy.py:271,384], and the envelope protocol mirrors LangGraph's `responseFormat` + structured-output conventions [CITED: docs.langchain.com/oss/javascript/langchain/agents]. The per-artifact pydantic v2 registry uses a discriminated-union pattern with `Literal` discriminator fields [VERIFIED: Context7 /websites/pydantic_dev_validation — discriminated unions], and artifact frontmatter round-trips through a single pydantic model [CITED: python-frontmatter 1.1.0 + pydantic integration patterns].

**Primary recommendation:** Build every new primitive as a pure additive module — no edits to `PhaseGate` / `ArtifactRequiredGate` / `HarnessOrchestrator` / `HarnessPlugin` — wired to existing seams through (a) the EventBus veto pattern, (b) pre-hook chains on `ArtifactStore.write()` and `Transport.deliver()`, and (c) a new `contribute_evidence_schemas` plugin hook mirroring the three Phase 1 hooks. Ship all new persistence under the existing `~/.clawteam/teams/<team>/sprints/<id>/` path convention via `file_locked()` + `atomic_write_text()`. Seven new event types (`BeforeToolCall`, `BeforeFileWrite`, `FreezeChange`, `MalformedEnvelope`, `DriftRegression`, `CycleDetected`, `ForcedProgressTriggered`, `ArtifactCapExceeded`) inherit from the existing `HarnessEvent` dataclass family [VERIFIED: clawteam/events/types.py:13-195].

---

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

**EvidenceGate family:**
- **D-01:** `EvidenceGate` at `clawteam/harness/evidence_gate.py` subclasses `ArtifactRequiredGate`. Base class still does presence check; `EvidenceGate.check()` runs content validation on required artifacts. Existing templates keep using `ArtifactRequiredGate`.
- **D-02:** Per-artifact validation uses pydantic frontmatter + required-section checklist. Each gstack artifact type (`DesignDoc`, `PlanDoc`, `TestReport`, `ReviewReport`, `ShipNotes`, `Retro`) has a pydantic model registered in `EvidenceSchemaRegistry` + a list of required `##` headers. Phase 3 `GstackSprintPlugin` registers the six schemas via a new `contribute_evidence_schemas` hook.
- **D-03:** Stub detection is 3-layer: (1) pydantic frontmatter non-empty; (2) each required `##` body ≤ 100 bytes = stub → fail; (3) regex blacklist `/\bTBD\b/i`, `/\bTODO\b/`, `/\bxxx+\b/i`, `/\bplaceholder\b/i`, `/Lorem ipsum/i` → fail with offending line.
- **D-04:** `test-report.md` gate synchronously runs `SuccessCriterion.test_command` via a content-hash cache persisted to `~/.clawteam/teams/<team>/sprints/<sprint_id>/test_verify_cache.json` (shape: `{artifact_hash, test_ids, last_run_at, last_exit_code}`). Cache hit = skip re-run. Updates `SuccessCriterion.verified` / `verified_at` / `verified_by="evidence_gate"`.
- **D-05:** `ship-notes.md` EvidenceGate validates `deploy_url` frontmatter field dereferences via HTTP HEAD → 2xx/3xx, 10s timeout. On failure, gate returns False with response body / timeout reason. Phase 5's `/ship` wires the URL; Phase 2 ships dereferencer + schema only.

**Response envelope:**
- **D-06:** `TeamMessage` adds three required fields: `persona: str`, `step_label: str`, `done: bool`. Existing fields unchanged; no default (required at write).
- **D-07:** Durable artifacts via `ArtifactStore.write()` carry YAML frontmatter with matching fields + `artifact_type` + `created_at`. Single `TurnEnvelope` pydantic model validates both surfaces.
- **D-08:** Validation at two hard-fail entry points: `transport/base.py::deliver()` (validates `TeamMessage.persona|step_label|done`) + `ArtifactStore.write()` (parses frontmatter through same `TurnEnvelope` model). Both raise `MalformedEnvelopeError`.
- **D-09:** Policy: first violation per agent = emit `MalformedEnvelope(agent, violation, turn_id)`, still deliver (warn mode); 8+ consecutive = emit `DriftRegression` + hard-reject subsequent until one valid envelope (counter resets). SC#4's "echo a peer's voice 8+ turns" drift detector = separate detector, same per-agent violation-window struct.

**Safety-rails:**
- **D-10:** Two new `Before*` events: `BeforeToolCall(agent_name, tool_name, args, veto)` (emitted by MCP server wrapper + CLI command interception); `BeforeFileWrite(agent_name, path, size_bytes, veto)` (emitted by `ArtifactStore.write()` + `workspace/manager.py` write paths). Handlers set `event.veto = True`.
- **D-11:** `FreezeRegistry` singleton at `clawteam/harness/freeze_registry.py`. Holds `dict[agent_name, set[Path]]` + sprint-scoped `frozen_globs: set[str]`. Persisted to `freeze.json` via `file_locked()` + `atomic_write_text`. EventBus handlers + WorkspaceManager + MCP `translate_error` consult `get_freeze_registry()`.
- **D-12:** Agent awareness via structured tool errors: veto → `FrozenPathError("<path> is /freeze-locked by <who>; unfreeze via /unfreeze <path>")`. MCP `translate_error` wraps it; CLI interception prints it; CLIs read response and self-correct. Runtime changes apply immediately — no restart.
- **D-13:** `FreezeChange(action, path, agent, reason, actor)` event. Append-only JSONL at `freeze_audit.jsonl` (mirrors `exit_journal.py`). Every `/freeze` / `/unfreeze` / `/guard` writes an entry. `/careful` = EventBus subscriber on `BeforeToolCall` with regex blacklist (`rm -rf`, `git reset --hard`, `git push --force`, `DROP TABLE`, `DELETE FROM .* WHERE`) — warns only by default; requires `--careful` sprint config to veto.

**Theater / no-progress:**
- **D-14:** "Turn" = one successful `transport.deliver()` OR one successful `ArtifactStore.write()` by a given agent. Counter lives on `SprintState.turn_counters: dict[agent_name, int]`. Increments at envelope-validation sites (D-08).
- **D-15:** "Progress" = (`sum(artifact.size_bytes for artifact in turn_delta_artifacts) > 0` since previous turn snapshot) OR `TaskCompleted` event fired during turn. Mailbox messages don't count.
- **D-16:** Escalation threshold = 2 consecutive no-progress turns per-agent. Per-agent (not sprint-wide) to avoid flagging specialists waiting for engineer/reviewer.
- **D-17:** `forced_progress_gate` at `clawteam/harness/forced_progress_gate.py` subclasses `PhaseGate`. On trigger: writes `questions/<q>.md` type=`multi-choice`, choices=`[A: keep waiting, B: restart agent, C: abort sprint]`. `InteractionGate` blocks advance. On answer: clear counter. Composed with `EvidenceGate` on every phase transition (`PhaseRunner._gates[phase]` grows by one).

**Cycle detector:**
- **D-18:** Cycle detection extends `DefaultRoutingPolicy.decide()` (`routing_policy.py:93+`). Before existing throttle, scan cross-pair `recentEvents` for round-trips. Reuses existing `routes[A→B]` / `routes[B→A]` state.
- **D-19:** "Topic" hash priority chain: (1) `RuntimeEnvelope.dedupe_key`, (2) `TeamMessage.request_id`, (3) `sha1(TeamMessage.content[:128])`.
- **D-20:** Window = last 20 entries in `recentEvents`. Threshold: A→B and B→A each show ≥ 3 entries with same topic-hash in same 20-message window → cycle.
- **D-21:** On trigger: emit `CycleDetected(pair, topic_hash, route_keys, window_size)`; suppress further A→B with same topic-hash (flag in `routes[route_key].suppressed_topics`); write `questions/<q>.md` type=`freeform`; human answer lifts suppression. AttentionQueue subscribes in Phase 7.

**Sprint engine & CLI:**
- **D-22:** `SprintConductor` at `clawteam/sprint/conductor.py`. Constructor accepts `team_name, *, force_interactive_phases: list[str] = [], artifact_cap_bytes=None, phase_artifact_cap_bytes=None`. Asyncio/threading-safe for one team; Phase 2 = single-sprint correctness. `force_interactive_phases` reserved; Phase 4 passes `["ship"]`.
- **D-23:** `auto_advance`: when `True` → `InteractionGate` inserted only if phase wrote unanswered questions; when `False` → `InteractionGate` on every transition. `force_interactive_phases` overrides both.
- **D-24:** Sprint CLI adds `clawteam sprint start|status|show|list|pause|resume`. Every sub-command honors existing global `--json` flag.
- **D-25:** Sprint addressability: `<id|prefix>` accepts full `uuid[:8]` OR unambiguous prefix. Ambiguous → `AmbiguousSprintError(prefix, candidates)`. No slug aliases.
- **D-26:** `--json` envelope: `{"ok": bool, "data": ..., "warnings": [], "error": null|{code,message}}` — uniform across every sprint command. MCP-parsable.

**Artifact caps:**
- **D-27:** Per-file cap = 50 KB default. Enforcement at `ArtifactStore.write()`: > cap → `ArtifactTooLargeError(artifact_name, size_bytes, cap_bytes, suggestion)`. Hard reject.
- **D-28:** Per-phase cap = 500 KB default (sum across artifacts under current phase). Overflow → `EvidenceGate` returns False on next check; writes `questions/artifact-compaction-<q>.md` type=`multi-choice`, choices=`[A: discard <list>, B: raise cap to <value>, C: split phase]`. InteractionGate unblocks on answer; `EvidenceGate` applies remedy.
- **D-29:** Three-layer cap override (highest wins): (1) `SprintState.artifact_cap_bytes` / `phase_artifact_cap_bytes`; (2) CLI flags `--artifact-cap <kb>` / `--phase-artifact-cap <kb>`; (3) env vars `CLAWTEAM_ARTIFACT_CAP_KB` / `CLAWTEAM_PHASE_ARTIFACT_CAP_KB` (via existing `_env` helper in `clawteam/identity.py`).

### Claude's Discretion

- Exact pydantic field names/aliases within the six gstack artifact schemas (D-02) — Phase 3 fills.
- Internal structure of `test_verify_cache.json` (D-04) — planner can add fields.
- Internal layout of `freeze.json` and `freeze_audit.jsonl` (D-11 / D-13).
- EvidenceGate compaction-question option-list wording (D-28).
- `asyncio.Lock` vs `threading.RLock` for `SprintConductor` (no concurrency requirement in Phase 2; Phase 7 verifies 10-concurrent).
- Test fixture layout.

### Deferred Ideas (OUT OF SCOPE)

To **Phase 3**: six concrete `EvidenceSchema` pydantic models (Phase 2 ships registry only); `/careful` regex tuning; role-prompt reassertion of envelope fields.
To **Phase 4**: `SmartReviewRouter`; cross-agent verification gates; SHA-pinning thrash detection; Ship-phase `force_interactive_phases=["ship"]` wiring.
To **Phase 7**: `CycleDetected` + `ForcedProgressTriggered` → AttentionQueue digest; 10-concurrent sprint load test; cost observability.
To **post-v1**: LLM-based artifact content validator; sprint slug aliases; wall-clock cycle-detection window.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-05 | `SprintConductor` manages one team's N concurrent sprints | D-22 shape grounded in existing `HarnessOrchestrator` (`harness/orchestrator.py`); asyncio pattern from Temporal durable-event-replay precedent [CITED: temporal.io/blog/durable-distributed-asyncio-event-loop] |
| CORE-07 | Sprint pause / resume survives orchestrator restart | Event-sourcing / pause-resume pattern [CITED: m2-farzan/asyncio-pause-resume]; `SprintState` persistence path fixed by Phase 1 D-05 [VERIFIED: `~/.clawteam/teams/<team>/sprints/<id>/state.json`]; last-pending-event replay = standard durable-queue idiom |
| INT-06 | Auto-advance toggle | D-23: `InteractionGate` conditional insertion based on `sprint.auto_advance` + unanswered-question presence |
| SPRINT-01 | `GstackSprintPlugin` registers 7 phases (deferred to Phase 3) | Phase 2 ships the `contribute_evidence_schemas` hook shape [NEW HOOK — mirrors Phase 1's three hooks on `HarnessPlugin`] |
| SPRINT-02 | `EvidenceGate` per phase | D-01..D-05 grounded in EviBound dual-gate governance [CITED: arxiv.org/abs/2511.05524] — approval-gate + verification-gate pattern directly applicable |
| SKILL-09 | Structured response envelope on every turn | D-06..D-09: `TurnEnvelope` pydantic model, two enforcement points, drift/violation policy; mirrors LangGraph structured-response + ReAct persona patterns [CITED: langchain.com/oss/javascript/langchain/agents] |
| SAFETY-01 | `/careful` = destructive-command warning | D-13: EventBus subscriber on `BeforeToolCall` with regex blacklist |
| SAFETY-02 | `/freeze <path>` = write-lock outside frozen path | D-11 + D-12: `FreezeRegistry` singleton + `FrozenPathError` structured tool error |
| SAFETY-03 | `/guard` = `/careful` + `/freeze` composite | D-13: composes both via shared `FreezeRegistry` + `FreezeChange` event |
| SAFETY-04 | `/unfreeze` requires audit log | D-13: `freeze_audit.jsonl` append-only JSONL (mirrors `exit_journal.py` pattern [VERIFIED: `clawteam/harness/exit_journal.py:27-43`]) |
| QUALITY-01 | Structured envelope enforced on every agent turn | D-06..D-09 (same as SKILL-09); drift-regression policy caps at 8 consecutive violations |
| QUALITY-02 | Cycle detector breaks A↔B within N turns | D-18..D-21: extends `DefaultRoutingPolicy`; mirrors Paperclip issue #390 circuit-breaker pattern [CITED: github.com/paperclipai/paperclip/issues/390] |
| QUALITY-03 | Context window guard — artifact caps are the Phase 2 slice | D-27..D-29: 50 KB/500 KB defaults; compaction prompts via InteractionGate; mirrors Factory.ai / Kilocode two-phase compaction [CITED: factory.ai/news/compressing-context] |
| QUALITY-06 | Workspace hardening (file-lock retry, git index) | Uses existing `file_locked()` + `atomic_write_text` [VERIFIED: `clawteam/fileutil.py`]; new primitives reuse these |
| QUALITY-08 | EvidenceGate validates artifact structure, not just presence | D-02, D-03 layers (frontmatter + required sections + stub regex + test re-run) |
| QUALITY-11 | Progress-on-artifact rule; consecutive no-progress → human | D-14..D-17: forced_progress_gate; Paperclip #390 no-progress counter; 2-turn threshold explicitly per-agent (not sprint-wide) |
| UX-02 | `clawteam sprint start` | D-24 sub-app + D-25 ID prefix addressability |
| UX-03 | `clawteam sprint status <id>` | D-24 |
| UX-04 | `clawteam sprint list --team` | D-24 requires `--team` or `CLAWTEAM_TEAM` env |
| UX-05 | `clawteam sprint show <id>` | D-24 full phase_history + artifacts + Q/A |
| UX-09 | `--json` uniform envelope across all sprint commands | D-26 shape locks envelope |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

No `CLAUDE.md` found at the project root [VERIFIED: `Read` returned "file does not exist"]. Codebase-implicit constraints from `.planning/PROJECT.md` and existing conventions:

- **Backwards-compat preserved:** Phase 0 regression matrix (`tests/test_template_regression_matrix.py`, 12 cases across 6 templates) must stay green. Every Phase 2 change is additive; no existing gate / event / model semantics change.
- **Upstream-PR-friendly:** Phase 2 is part of the upstream bundle (Phases 0+1+2). No gstack-specific business logic in core substrate — all template-specific behavior ships via `GstackSprintPlugin` in Phase 3.
- **Additive-only plugin hooks:** New hooks land with empty-collection defaults (mirrors Phase 1 D-04 `contribute_phases/phase_roles/review_routers`).
- **No new required runtime deps:** Pydantic v2, Typer, rich, questionary are already declared [VERIFIED: `pyproject.toml` §dependencies]. Any optional dep (e.g., `requests` for HEAD dereferencing) ships as optional extra or uses stdlib `urllib.request`.
- **Python 3.10+ compatibility** [VERIFIED: `pyproject.toml` `requires-python = ">=3.10"`].
- **Identity env multi-generation preservation** [VERIFIED: `clawteam/identity.py::_env` reads `CLAWTEAM_* / OH_* / CLAUDE_CODE_*` prefixes]. New env vars (`CLAWTEAM_ARTIFACT_CAP_KB`, `CLAWTEAM_PHASE_ARTIFACT_CAP_KB`) go through same helper.
- **File-locked atomic JSON under `~/.clawteam/teams/<team>/...`** is the canonical persistence convention [VERIFIED: used by snapshots, costs, config, sprint_state from Phase 1].
- **Pydantic v2 + open `str` for enumerated values** — don't introduce `Enum` for `Phase` / `AgentRole` [VERIFIED: `clawteam/harness/phases.py:20`].

## Project Skills

Project skills in `.claude/skills/`:
- **`clawteam-dev`** (v0.2.0) — ClawTeam local dev bootstrap. Validation preference is `ruff check clawteam/ tests/` + `pytest tests/<target> -q` for targeted runs; `pytest tests/test_template_regression_matrix.py tests/test_event_bus.py tests/test_harness.py -q` for cross-module changes. [VERIFIED: `.claude/skills/clawteam-dev/SKILL.md`]
- **`frontend-design`** — present but not relevant to Phase 2 (Phase 6 territory).

Phase 2 planning / execution should follow the ClawTeam dev skill's validation preferences: one-test-file-per-primitive, targeted pytest runs per wave, full regression matrix only as gate on merge.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Phase-transition dispatch (CORE-05) | `clawteam/sprint/conductor.py` | `clawteam/harness/phases.py::PhaseRunner` | Conductor owns sprint-level loop; PhaseRunner owns single-phase gate evaluation. Conductor composes with PhaseRunner, doesn't replace [VERIFIED: PhaseRunner already exists at `phases.py:106-193`]. |
| Sprint pause/resume (CORE-07) | `clawteam/sprint/conductor.py` | `clawteam/sprint/state.py::SprintState` | State serialization belongs on the pydantic model; conductor owns the pause/resume protocol + event replay. |
| EvidenceGate content validation (QUALITY-08, SPRINT-02) | `clawteam/harness/evidence_gate.py` | `clawteam/harness/evidence_schemas.py` (registry) | Gate is phase-gate subclass. Schema registry is a separate module so Phase 3's `GstackSprintPlugin` can populate it without touching gate code. |
| Envelope validation (QUALITY-01, SKILL-09) | `clawteam/team/envelope.py` (new, `TurnEnvelope` model) | `clawteam/transport/base.py::deliver()` + `clawteam/harness/artifacts.py::write()` | Pydantic model centralizes validation; two transport/storage entry points are the enforcement surfaces. |
| Theater / forced_progress_gate (QUALITY-11) | `clawteam/harness/forced_progress_gate.py` | `clawteam/sprint/state.py` (counter state) | Gate subclass + counter field on SprintState; uses existing `TaskCompleted` event [VERIFIED: `events/types.py:83`]. |
| Cycle detection (QUALITY-02) | `clawteam/team/routing_policy.py::DefaultRoutingPolicy.decide()` | `clawteam/events/types.py::CycleDetected` | Extends existing per-pair state machine; no parallel tracker [VERIFIED: per `<specifics>` section of CONTEXT, lesson #1]. |
| Safety rails (SAFETY-01..04) | `clawteam/harness/freeze_registry.py` | `clawteam/events/types.py::{BeforeToolCall, BeforeFileWrite, FreezeChange}` | Registry singleton mirrors Phase 1 `PhaseRegistry` shape. EventBus veto is the interception mechanism [VERIFIED: `events/bus.py:86-101` documents `event.veto = True` pattern]. |
| Artifact caps (QUALITY-03 slice, SC#9) | `clawteam/harness/artifacts.py::ArtifactStore.write()` | `clawteam/harness/evidence_gate.py` (phase-level cap check) | Per-file cap = point-of-write; per-phase cap = gate check (so compaction prompt via InteractionGate). |
| Sprint CLI (UX-02..05, UX-09) | `clawteam/cli/commands.py` (sprint sub-app) | `clawteam/sprint/conductor.py` | Typer sub-app pattern; CLI dispatches into conductor methods. |
| MCP tool interception (SAFETY-01..04) | `clawteam/mcp/helpers.py::translate_error` | MCP `_tool` wrapper at `clawteam/mcp/server.py:_tool` | `BeforeToolCall` emitted inside `_tool` wrapper; `translate_error` already wraps exceptions [VERIFIED: `mcp/helpers.py:25`]. |

---

## Standard Stack

### Core (already in project — no new required deps)

| Library | Installed version | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| pydantic | 2.12.5 (available: 2.13.2) [VERIFIED: `pip index versions pydantic`] | `TurnEnvelope`, `EvidenceSchemaRegistry`, `SprintState` extensions, `ArtifactTooLargeError` detail | Already project core [VERIFIED: `pyproject.toml`]; v2 discriminated unions + `Literal` discriminators provide zero-cost per-artifact-type routing [Context7 /websites/pydantic_dev_validation] |
| typer | 0.24.1 available [VERIFIED] | `sprint` sub-app with `start|status|show|list|pause|resume` + uniform `--json` envelope | Already project core [VERIFIED: `pyproject.toml`]; `add_typer()` pattern is the canonical sub-app idiom [CITED: typer.tiangolo.com/tutorial/subcommands/single-file] |
| rich | 13+ | Human-readable sprint status output | Already project core |
| hashlib (stdlib) | — | `sha1(content[:128])` for topic-hash fallback (D-19), `sha256` for `test_verify_cache.json` artifact hash (D-04) | Stdlib; no new dep |
| urllib.request (stdlib) | — | HTTP HEAD dereference for `ship-notes.md` `deploy_url` (D-05) | Stdlib; no new dep |
| json (stdlib) | — | `freeze.json`, `test_verify_cache.json`, `freeze_audit.jsonl` serialization | Stdlib; existing pattern [VERIFIED: `harness/exit_journal.py`] |
| fcntl / msvcrt (stdlib) | — | Already used by `file_locked()` [VERIFIED: `fileutil.py:22-25`] | Stdlib |
| subprocess (stdlib) | — | Run `SuccessCriterion.test_command` (D-04) | Stdlib |

### Supporting (frontmatter parsing)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-frontmatter | 1.1.0 [VERIFIED: `pip index versions python-frontmatter`] | Parse YAML frontmatter at top of `.md` artifacts (D-07) | Recommended: adds a sixth dep but it's 150 LOC pure-Python, no transitive deps beyond `PyYAML`. Alternative: stdlib split-on-`---`-line + `yaml.safe_load` (PyYAML is already a questionary transitive dep). [CITED: python-frontmatter.readthedocs.io + github.com/eyeseast/python-frontmatter] |

**Recommendation:** use stdlib approach — split on `/^---\n/` boundary, `yaml.safe_load` the block, pass the rest of the file as content. Keeps the "no new required deps" constraint intact. Reference implementation pattern is ~30 lines; lives in `clawteam/team/envelope.py::parse_frontmatter()`.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic discriminated union for `EvidenceSchemaRegistry` | `dict[str, type[BaseModel]]` lookup | Discriminated union gives a single validator that picks the right sub-model at load time; dict requires an explicit dispatch step. Both work, but the union pattern scales better in Phase 3 when Phase 3's plugin adds six sub-models. Use the union. |
| `TurnEnvelope` as a shared pydantic model | Two separate schemas (one for `TeamMessage`, one for frontmatter) | Single model is explicitly required by CONTEXT specifics lesson #2: "don't diverge — any drift detection (SC#4) relies on same field set regardless of channel." |
| `python-frontmatter` library | `re.split(r'^---\s*$', raw, maxsplit=2, flags=re.M)` + `yaml.safe_load` | Stdlib path avoids one more pinned dep. `python-frontmatter` is a well-maintained package but 150 LOC buys us nothing we can't do in 30 LOC. |
| HTTP HEAD via `urllib.request` (stdlib) | `requests` library | `requests` is NOT in project deps. Stdlib `urllib.request.Request(url, method='HEAD')` works identically for the D-05 dereference check. |
| `asyncio.Lock` on `SprintConductor` | `threading.RLock` | No concurrency requirement in Phase 2 (10-sprint verified in Phase 7). Start with `threading.RLock` since the existing `EventBus` already uses `threading.RLock` [VERIFIED: `events/bus.py:51`] — consistent. |
| Directly editing `TeamMessage` to add envelope fields | Separate `TurnEnvelope` wrapping `TeamMessage` | CONTEXT D-06 explicitly requires the three fields on `TeamMessage` itself, not a wrapper. The model already accepts many optional fields [VERIFIED: `team/models.py:90-122`]; adding three required fields with defaults-via-settable-at-write is the natural extension. |

**Installation:** none required. Phase 2 adds zero new top-level deps.

**Version verification:**
```bash
pip index versions pydantic    # 2.12.5 installed, 2.13.2 available
pip index versions typer       # 0.24.1 available
pip index versions pytest      # 9.0.3 available
# python-frontmatter — NOT USED per recommendation; stdlib path instead
```

All Phase 2 code targets Python 3.10+ stdlib + pydantic 2.x APIs. Pydantic 2.11+ is required for the discriminated-union `Tag` syntax used by the `EvidenceSchemaRegistry` — installed version 2.12.5 is sufficient.

---

## Architecture Patterns

### System Architecture Diagram

```
                                   ┌───────────────────────────┐
                                   │  Phase 4 future wiring    │
                                   │  (SmartReviewRouter,      │
                                   │   cross-agent verify)     │
                                   └──────────────▲────────────┘
                                                  │ (Phase 4 extends here)
 CLI entry                                        │
 ───────                                          │
 clawteam sprint start/status/show/list/pause/resume  (D-22..D-26)
     │
     ▼
 ┌─────────────────────────────────────────────────────────────┐
 │  SprintConductor  (clawteam/sprint/conductor.py)             │
 │  - owns sprint loop for one team                             │
 │  - force_interactive_phases hook (Phase 4 will pass ["ship"])│
 │  - pause/resume via SprintState checkpoint + event replay    │
 └──────┬──────────────────────────────────────┬────────────────┘
        │                                       │
        │ per-transition advance                │ persistence
        ▼                                       ▼
 ┌──────────────────────────────┐   ┌────────────────────────────────┐
 │  PhaseRunner (existing)       │   │  SprintState  (Phase 1)         │
 │  _gates[phase] now includes:  │   │  + turn_counters                │
 │    1. EvidenceGate            │   │  + artifact_cap_bytes           │
 │    2. forced_progress_gate    │   │  + phase_artifact_cap_bytes     │
 │    3. InteractionGate (P1)    │   │  ~/.../sprints/<id>/state.json  │
 └──────┬────────────────────────┘   └────────────────────────────────┘
        │
        │ for each registered gate in order
        ▼
 ┌───────────────────────────────────────────────────────────────┐
 │  EvidenceGate (D-01..D-05)                                     │
 │  ├─ presence check (ArtifactRequiredGate base, reused)         │
 │  ├─ frontmatter parse → TurnEnvelope + EvidenceSchemaRegistry  │
 │  ├─ stub detection (D-03 3-layer)                              │
 │  ├─ test_command re-run via test_verify_cache.json (D-04)      │
 │  └─ deploy_url HEAD dereference (ship only, D-05)              │
 └───────┬───────────────────────────────────────────────────────┘
         │ returns False on any layer fail
         │                 ┌─────────────────────────────────────┐
         │                 │  forced_progress_gate (D-17)        │
         ├────────────────▶│  - consult SprintState.turn_counters│
         │                 │  - 2+ consecutive no-progress?      │
         │                 │  - write questions/<q>.md (D-17)    │
         │                 └──────┬──────────────────────────────┘
         │                        │
         │                        ▼
         │                 ┌─────────────────────────────────────┐
         │                 │  InteractionGate (Phase 1)          │
         │                 │  - questions/<id>.md unanswered?    │
         │                 └─────────────────────────────────────┘
         │                           ▲
         │                           │
         ▼                           │ question file writes
 ┌───────────────────────────────────┴──────────────────────────────┐
 │                      WRITE-PATH HOOK CHAIN                        │
 │                                                                    │
 │  ArtifactStore.write()                                             │
 │    ├─ size_bytes cap check  → ArtifactTooLargeError (D-27)         │
 │    ├─ parse frontmatter → TurnEnvelope pydantic                    │
 │    ├─ envelope validation → MalformedEnvelopeError on fail (D-08)  │
 │    ├─ FreezeRegistry consult → FrozenPathError on veto (D-11,12)   │
 │    ├─ phase-total cap check                                        │
 │    ├─ emit BeforeFileWrite (D-10) → EventBus veto check            │
 │    ├─ atomic_write_text                                            │
 │    ├─ increment SprintState.turn_counters[agent] (D-14)            │
 │    └─ turn-delta bytes → progress signal (D-15)                    │
 │                                                                    │
 │  Transport.deliver(recipient, data)                                │
 │    ├─ parse data → TeamMessage pydantic                            │
 │    ├─ envelope validation → MalformedEnvelopeError on fail (D-08)  │
 │    ├─ DefaultRoutingPolicy.decide() → cycle detector (D-18..D-21) │
 │    │     ├─ topic-hash priority chain (D-19)                       │
 │    │     ├─ scan recentEvents window = 20 (D-20)                   │
 │    │     └─ on cycle: emit CycleDetected + suppress + question     │
 │    ├─ emit BeforeInboxSend (existing)                              │
 │    └─ deliver + increment turn_counters[agent] (D-14)              │
 └────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────────┐
                    │  SAFETY RAILS (independent subsystem)           │
                    │                                                  │
                    │  FreezeRegistry singleton (D-11)                │
                    │    ~/.../sprints/<id>/freeze.json                │
                    │    dict[agent, set[Path]] + frozen_globs        │
                    │                                                  │
                    │  EventBus subscribers:                           │
                    │    BeforeToolCall  (D-10)  ← MCP + CLI           │
                    │      ├─ /careful: regex blacklist (warn/veto)    │
                    │      └─ FreezeRegistry path-check → veto         │
                    │    BeforeFileWrite (D-10)  ← ArtifactStore +     │
                    │                              WorkspaceManager    │
                    │      └─ FreezeRegistry path-check → veto         │
                    │                                                  │
                    │  FreezeChange events (D-13)                      │
                    │    → freeze_audit.jsonl (mirrors exit_journal)   │
                    └─────────────────────────────────────────────────┘
```

Data flows top-down through SprintConductor → PhaseRunner → gate chain. Cross-cutting safety-rails hook the two enforcement surfaces (write path + deliver path) through EventBus veto events. Every durable state write persists through `file_locked()` + `atomic_write_text` to the same sprint directory.

### Recommended Project Structure

```
clawteam/
├── sprint/                          # NEW MODULE (Phase 1 created state.py; Phase 2 adds conductor.py)
│   ├── __init__.py
│   ├── state.py                    # Phase 1; Phase 2 extends with turn_counters + cap fields
│   └── conductor.py                # NEW: SprintConductor (D-22)
├── harness/
│   ├── phases.py                   # EXISTING: PhaseRunner, ArtifactRequiredGate — no edits
│   ├── artifacts.py                # EDIT: ArtifactStore.write() hook chain (D-07..D-08, D-27)
│   ├── contracts.py                # EDIT: SuccessCriterion.verified fields written by EvidenceGate (D-04)
│   ├── evidence_gate.py            # NEW: EvidenceGate (D-01..D-05)
│   ├── evidence_schemas.py         # NEW: EvidenceSchemaRegistry + contribute_evidence_schemas hook
│   ├── forced_progress_gate.py     # NEW: forced_progress_gate (D-17)
│   ├── freeze_registry.py          # NEW: FreezeRegistry singleton (D-11..D-13)
│   └── interaction_gate.py         # Phase 1 — no edits
├── team/
│   ├── models.py                   # EDIT: TeamMessage + persona/step_label/done (D-06)
│   ├── envelope.py                 # NEW: TurnEnvelope pydantic + parse_frontmatter() helper (D-07..D-08)
│   └── routing_policy.py           # EDIT: DefaultRoutingPolicy.decide() + cycle detector (D-18..D-21)
├── events/
│   ├── types.py                    # EDIT: 8 new event dataclasses (D-10, D-13, D-09, D-21, etc.)
│   └── bus.py                      # NO EDITS — veto pattern already exists
├── transport/
│   └── base.py                     # EDIT: Transport.deliver() pre-deliver hook (D-08)
├── workspace/
│   └── manager.py                  # EDIT: emit BeforeFileWrite before git writes (D-10)
├── mcp/
│   ├── server.py                   # EDIT: _tool wrapper emits BeforeToolCall (D-10)
│   └── helpers.py                  # EDIT: translate_error handles FrozenPathError (D-12)
├── plugins/
│   └── base.py                     # EDIT: add contribute_evidence_schemas() -> {} default
└── cli/
    └── commands.py                 # EDIT: add sprint sub-app via typer.Typer() + add_typer() (D-24)

tests/
├── test_evidence_gate.py           # NEW — D-01..D-05, six stub-detection-layer cases
├── test_turn_envelope.py           # NEW — envelope parse round-trip, malformed raise
├── test_forced_progress_gate.py    # NEW — theater-simulation, 2-turn threshold, per-agent
├── test_cycle_detector.py          # NEW — A↔B round-trip, topic-hash priority chain
├── test_freeze_registry.py         # NEW — path veto, audit JSONL, runtime-apply
├── test_safety_rails.py            # NEW — /careful blacklist, /guard composite
├── test_artifact_caps.py           # NEW — per-file reject, per-phase compaction prompt
├── test_sprint_conductor.py        # NEW — phase-advance, pause/resume, force_interactive_phases
└── test_sprint_cli.py              # NEW — start/status/show/list/pause/resume + --json envelope
```

### Pattern 1: Pydantic discriminated-union artifact schema registry (D-02)

**What:** Each artifact type declares a pydantic model with a `Literal['design-doc'|'plan-doc'|...]` discriminator field. `EvidenceSchemaRegistry` exposes the union as `Annotated[Union[DesignDoc, PlanDoc, ...], Field(discriminator='artifact_type')]` so one `model_validate()` call routes to the correct sub-model.

**When to use:** When the phase gate needs to dispatch validation across N artifact types (one per phase) without a hand-rolled dispatch table.

**Example (Phase 2 scaffold; Phase 3 fills the six sub-models):**
```python
# clawteam/harness/evidence_schemas.py
from __future__ import annotations
from typing import Annotated, Literal, Union
from pydantic import BaseModel, Field

class ArtifactFrontmatterBase(BaseModel):
    persona: str
    step_label: str
    done: bool
    artifact_type: str
    created_at: str

class _Unknown(ArtifactFrontmatterBase):
    # Default fallback when no plugin has registered this artifact_type yet.
    artifact_type: Literal['unknown'] = 'unknown'

# Plugin-populated at on_register time. Phase 2 ships the empty-default shape;
# Phase 3's GstackSprintPlugin.contribute_evidence_schemas() adds the six concrete schemas.
_REGISTERED: dict[str, type[ArtifactFrontmatterBase]] = {}

def register_schema(name: str, cls: type[ArtifactFrontmatterBase]) -> None:
    if name in _REGISTERED:
        raise ValueError(f"Duplicate evidence-schema registration: {name}")
    _REGISTERED[name] = cls

def get_schema(artifact_type: str) -> type[ArtifactFrontmatterBase] | None:
    return _REGISTERED.get(artifact_type)
```
[Source: pattern derived from Pydantic v2 discriminated-union docs — Context7 /websites/pydantic_dev_validation]

### Pattern 2: EventBus Before* veto hook (D-10, D-12)

**What:** Emit a `Before*` event before any interceptable action; subscribers set `event.veto = True` to cancel; caller checks `event.veto` post-emit and raises the appropriate structured error. Already used by `BeforeWorkerSpawn`, `BeforeInboxSend`, `BeforeTaskCreate`, `BeforeWorkspaceMerge` [VERIFIED: `events/types.py:25-120`].

**When to use:** For any cross-cutting interception where a registry (like `FreezeRegistry`) needs to veto ordinary flow without monkey-patching the caller.

**Example (new Phase 2 event shape):**
```python
# clawteam/events/types.py
@dataclass
class BeforeFileWrite(HarnessEvent):
    agent_name: str = ""
    path: str = ""
    size_bytes: int = 0
    veto: bool = False
    veto_reason: str = ""

# Caller: clawteam/harness/artifacts.py::ArtifactStore.write
from clawteam.events.global_bus import get_event_bus
from clawteam.events.types import BeforeFileWrite

def write(self, name, content, metadata=None):
    event = BeforeFileWrite(
        team_name=self._team_name,
        agent_name=metadata.get('agent') if metadata else '',
        path=str(self._dir / name),
        size_bytes=len(content),
    )
    get_event_bus().emit(event)
    if event.veto:
        raise FrozenPathError(event.veto_reason or f"{name} is frozen")
    # … existing atomic write …

# Subscriber: clawteam/harness/freeze_registry.py
def _on_file_write(event: BeforeFileWrite):
    reg = get_freeze_registry()
    if reg.is_frozen(Path(event.path)):
        event.veto = True
        event.veto_reason = f"{event.path} is /freeze-locked"

get_event_bus().subscribe(BeforeFileWrite, _on_file_write, priority=10)
```
[Source: existing `events/bus.py:86-101` veto semantics + `test_event_bus.py::test_veto_pattern`]

### Pattern 3: EvidenceGate 4-check protocol (D-01..D-05, modelled on EviBound Phase 6)

**What:** Gate runs four sequential checks per required artifact; short-circuit on first failure with a structured reason.

**When to use:** Every gstack phase gate (ships in Phase 3 via plugin); Phase 2 ships the class + mechanism.

**Example:**
```python
# clawteam/harness/evidence_gate.py
class EvidenceGate(ArtifactRequiredGate):
    def check(self, state) -> tuple[bool, str]:
        # 1. Presence check (inherited from ArtifactRequiredGate)
        ok, reason = super().check(state)
        if not ok:
            return ok, reason

        # 2. Per-artifact schema + required-section validation
        for artifact_name in self.artifact_names:
            raw = state.artifacts.get(artifact_name, "")
            meta, body = parse_frontmatter(raw)
            schema_cls = get_schema(meta.get("artifact_type", ""))
            if schema_cls is None:
                return False, f"{artifact_name}: unknown artifact_type '{meta.get('artifact_type')}'"
            try:
                schema_cls.model_validate(meta)
            except ValidationError as exc:
                return False, f"{artifact_name}: frontmatter invalid: {exc.errors()[0]['msg']}"

            # 3. Stub detection (D-03 3-layer)
            stub_issue = detect_stub(body, required_sections=get_required_sections(artifact_name))
            if stub_issue:
                return False, f"{artifact_name}: {stub_issue}"

        # 4. Type-specific post-check (test-rerun for test-report.md; HTTP HEAD for ship-notes.md)
        for artifact_name in self.artifact_names:
            post_ok, post_reason = self._post_check(artifact_name, state)
            if not post_ok:
                return False, post_reason

        return True, ""
```
[Source: pattern adapted from EviBound §3 (4-check protocol) — CITED: arxiv.org/abs/2511.05524 §3]

### Pattern 4: Cycle detector over existing rolling window (D-18..D-21)

**What:** Extend `DefaultRoutingPolicy.decide()` to scan the existing `state['recentEvents']` (50-entry rolling window) for A→B and B→A round-trips with matching topic-hash.

**When to use:** Transport-level cycle breaking. Existing throttle logic in `DefaultRoutingPolicy` is unchanged; cycle check runs FIRST.

**Example:**
```python
# clawteam/team/routing_policy.py (addition to DefaultRoutingPolicy.decide)
def decide(self, envelope: RuntimeEnvelope, now=None) -> RouteDecision:
    now_dt = _ensure_datetime(now)
    state = self.read_state()

    # NEW: cycle detection BEFORE throttle
    cycle = self._detect_cycle(state, envelope)
    if cycle is not None:
        self._append_event(state, cycle.route_key, ..., action="cycle_suppressed", reason=cycle.reason, ...)
        self._save_state(state)
        get_event_bus().emit(CycleDetected(
            team_name=self.team_name,
            pair=(envelope.source, envelope.target),
            topic_hash=cycle.topic_hash,
            route_keys=cycle.route_keys,
            window_size=20,
        ))
        # … write questions/<q>.md …
        return RouteDecision(action="suppress", reason="cycle_detected", envelope=envelope, route_key=cycle.route_key)

    # EXISTING throttle / inject flow continues unchanged …

def _detect_cycle(self, state, envelope) -> CycleHit | None:
    topic = self._topic_hash(envelope)  # D-19 priority chain
    window = state["recentEvents"][-20:]  # D-20 window size
    route_a_b = self._route_key(envelope.source, envelope.target)
    route_b_a = self._route_key(envelope.target, envelope.source)
    count_ab = sum(1 for e in window if e["routeKey"] == route_a_b and self._event_topic(e) == topic)
    count_ba = sum(1 for e in window if e["routeKey"] == route_b_a and self._event_topic(e) == topic)
    if count_ab >= 3 and count_ba >= 3:
        return CycleHit(topic_hash=topic, route_keys=[route_a_b, route_b_a], route_key=route_a_b, reason="3+ round-trips in 20-msg window")
    return None

def _topic_hash(self, envelope: RuntimeEnvelope) -> str:
    # D-19 priority chain
    if envelope.dedupe_key:
        return envelope.dedupe_key
    # request_id from TeamMessage payload if present
    req_id = envelope.payload.get("request_id") or envelope.payload.get("requestId")
    if req_id:
        return req_id
    # fallback: sha1 of first 128 chars
    content = envelope.payload.get("content") or envelope.summary or ""
    return hashlib.sha1(content[:128].encode("utf-8")).hexdigest()[:16]
```
[Source: mirrors Paperclip issue #390 circuit-breaker design — CITED: github.com/paperclipai/paperclip/issues/390; implementation mapped to existing ClawTeam `recentEvents` state at `routing_policy.py:271`]

### Pattern 5: Typer sub-app with uniform JSON envelope (D-24, D-26, UX-09)

**What:** Create `sprint_app = typer.Typer()`, decorate subcommands on it, call `app.add_typer(sprint_app, name="sprint")` in `cli/commands.py`. Every subcommand returns via `_emit()` helper that honors the global `--json` flag [VERIFIED: `cli/commands.py:82-122` callback + `_output` helper].

**Example:**
```python
# clawteam/cli/commands.py (addition)
sprint_app = typer.Typer(name="sprint", help="Sprint lifecycle commands.", no_args_is_help=True)

@sprint_app.command("start")
def sprint_start(
    team: str = typer.Option(..., "--team", envvar="CLAWTEAM_TEAM"),
    goal: str = typer.Option(..., "--goal"),
    auto_advance: bool = typer.Option(False, "--auto-advance"),
    artifact_cap: int | None = typer.Option(None, "--artifact-cap", help="Per-file cap (KB)"),
    phase_artifact_cap: int | None = typer.Option(None, "--phase-artifact-cap", help="Per-phase cap (KB)"),
):
    try:
        conductor = SprintConductor(team_name=team, artifact_cap_bytes=artifact_cap * 1024 if artifact_cap else None, ...)
        state = conductor.start_sprint(goal=goal, auto_advance=auto_advance)
        _emit_ok({"id": state.sprint_id, "goal": state.goal, "current_phase": state.current_phase})
    except Exception as exc:
        _emit_err(code="SPRINT_START_FAILED", message=str(exc))

def _emit_ok(data):
    payload = {"ok": True, "data": data, "warnings": [], "error": None}
    if _json_output:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _render_human(data)

def _emit_err(code, message):
    payload = {"ok": False, "data": None, "warnings": [], "error": {"code": code, "message": message}}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    raise typer.Exit(1)

app.add_typer(sprint_app, name="sprint")
```
[Source: Typer docs on sub-app nesting — CITED: typer.tiangolo.com/tutorial/subcommands/nested-subcommands + existing pattern `cli/commands.py:22-82`]

### Pattern 6: Append-only JSONL audit log (D-13)

**What:** New freeze events open-append to a sidecar `.jsonl` file per sprint. Atomic single-`write()` call terminated by newline.

**When to use:** Every `/freeze`, `/unfreeze`, `/guard` invocation. Mirrors `FileExitJournal` pattern exactly [VERIFIED: `harness/exit_journal.py:27-43`].

**Example:**
```python
# clawteam/harness/freeze_registry.py
def _append_audit(entry: dict, sprint_dir: Path) -> None:
    audit_path = sprint_dir / "freeze_audit.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```
[Source: exact copy of `FileExitJournal.record_exit()` pattern]

### Anti-Patterns to Avoid

- **Parallel trackers for cycle detection.** CONTEXT `<specifics>` lesson #1: don't introduce a separate tracker next to `DefaultRoutingPolicy.recentEvents`. Extend the existing state machine.
- **Two pydantic models for envelope (one for message, one for frontmatter).** CONTEXT lesson #2: single `TurnEnvelope` model, two serialization surfaces. Field drift = drift-detection broken.
- **Enum for `artifact_type` field.** Codebase convention is open `str` for enumerated values [VERIFIED: `phases.py:19-20`, `team/models.py::MessageType` used Enum but that's legacy — new fields follow `str` + `Literal[...]` discriminator pattern].
- **Writing `test_verify_cache.json` through `open(path, 'w')` directly.** Must use `file_locked()` + `atomic_write_text` [VERIFIED: pattern from `team/snapshot.py:21`].
- **Emitting `CycleDetected` + immediately recursing into `decide()`.** Short-circuit return before the emit → recursion safety.
- **Catching `FrozenPathError` inside the EventBus subscriber.** Subscriber ONLY sets `event.veto = True`; caller raises the error. Matches existing `BeforeWorkspaceMerge` pattern.
- **`force_interactive_phases` list mutation post-construction.** Dataclass field; set at sprint-start; never mutated.
- **Inlining `forced_progress_gate` logic into `EvidenceGate`.** CONTEXT D-17 makes them separate gates composed in order (EvidenceGate → forced_progress_gate → InteractionGate). Separation keeps Phase 3's `GstackSprintPlugin` free to pick different gate combinations for different phases.
- **Running `test_command` subprocess synchronously without timeout.** D-04 specifies cache-hit skip + synchronous run; planner must add a configurable timeout (suggested default: 300s) to prevent gate hang on a runaway pytest.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-artifact schema dispatch | Hand-rolled `dict[type_name, validator]` map | Pydantic discriminated union with `Literal` field + `Annotated[Union[...], Field(discriminator=...)]` | Pydantic 2 generates one compiled validator; scales to six+ schema types without a custom dispatch layer [CITED: pydantic docs — discriminated unions] |
| YAML frontmatter parse | Hand-rolled scanner for `---` lines | stdlib `re.split` on `^---\s*$` + `yaml.safe_load` on the middle chunk | 30 lines; PyYAML already a transitive dep (questionary → `prompt_toolkit` does not pull it, but `pyproject.toml` inclusion is trivial if needed). Avoids adding `python-frontmatter` as a top-level dep. |
| File locking on `freeze.json` / `test_verify_cache.json` | Custom flock wrapper | Existing `clawteam.fileutil.file_locked()` + `atomic_write_text()` | Already cross-platform (fcntl + msvcrt); used by every other durable state file in the repo [VERIFIED: `fileutil.py`] |
| Sprint ID generation | Sequential counter + collision check | `uuid.uuid4().hex[:8]` (existing convention) | Convention already pinned by Phase 1 D-05 and by `SprintContract.id` [VERIFIED: `contracts.py:28`] — matches without extra infrastructure |
| Phase-transition event dispatch | Custom callback registry | Existing `EventBus` with `PhaseTransition` event (already fired in `PhaseRunner.advance()`) | [VERIFIED: `phases.py:148-157`] |
| Audit log rotation | Hand-rolled size-based rotation | Append-only JSONL; rotation deferred | Sprint lifetime is short (hours–days); single sprint audit file won't grow unbounded. Mirrors `exit_journal.py` design |
| HTTP HEAD for `deploy_url` dereferencing | Adding `requests` library | `urllib.request.Request(url, method='HEAD')` + 10s `urlopen(timeout=10)` | Stdlib; no new dep; sufficient for 2xx/3xx check |
| `SprintConductor` concurrency | Custom lock hierarchy | `threading.RLock` (consistent with existing EventBus lock) or `asyncio.Lock` | No concurrency requirement in Phase 2; Phase 7 verifies 10-concurrent. Start with `threading.RLock`. |
| Sub-command CLI plumbing | `argparse` add_subparsers | `typer.Typer()` + `app.add_typer(sub_app, name=...)` | Typer is already the project CLI framework [VERIFIED: `cli/commands.py:22`]; sub-app is one line |
| Structured MCP tool errors | New exception hierarchy | Extend existing `MCPToolError` (wrap in `translate_error`) | [VERIFIED: `mcp/helpers.py:17-32`] — `FrozenPathError`, `ArtifactTooLargeError`, `MalformedEnvelopeError`, `AmbiguousSprintError` all subclass `ValueError` so `translate_error` wraps them automatically |

**Key insight:** Phase 2 is an additive layer over already-correct ClawTeam primitives. Every "don't hand-roll" line reflects a ClawTeam-native pattern already in the codebase. The one genuinely new subsystem — `EvidenceSchemaRegistry` — uses a well-documented pydantic v2 pattern with concrete examples in the Pydantic docs.

---

## Common Pitfalls

### Pitfall 1: Envelope validation recursion / infinite-loop on error emission
**What goes wrong:** `MalformedEnvelope` event handler writes something to an artifact store, which triggers its own envelope validation, which fails, which emits another `MalformedEnvelope`…
**Why it happens:** The same enforcement hook chain runs for every write.
**How to avoid:** (1) `MalformedEnvelope` event is emitted synchronously via `emit()` not `emit_async()`, but handlers must NOT themselves trigger an `ArtifactStore.write()` or `transport.deliver()`. (2) The error event is logged to `~/.clawteam/teams/<team>/sprints/<id>/envelope_errors.jsonl` via a direct `file_locked()` write (bypassing the hook chain).
**Warning signs:** Test run hangs on the first malformed-envelope assertion; stack trace shows recursive frames.

### Pitfall 2: Turn counter double-increment on same agent action
**What goes wrong:** D-14 defines a turn as "one successful `deliver()` OR one successful `write()`". If an agent both delivers a TeamMessage AND writes an artifact as part of the same turn, the counter increments twice.
**Why it happens:** The two hooks are independent.
**How to avoid:** (1) Attach a `turn_id: str` to the `TurnEnvelope` (agent-generated, `uuid.uuid4().hex[:8]`). Counter increments only on first sighting of a new `turn_id` per agent. (2) Alternatively: counter increments on `deliver()` only when `message.done = True`, or `write()` only when `meta.done = True`. Planner picks — document in planning.
**Warning signs:** Theater detector fires on healthy agents after their first multi-artifact build step.

### Pitfall 3: Cycle detector flags designer↔engineer normal iteration as cycle
**What goes wrong:** Designer sends UI proposal A → engineer asks for change → designer sends proposal B → engineer rejects → … Three round-trips with the same topic (e.g., `request_id="ui-login-button"`) looks like a cycle but is normal iteration.
**Why it happens:** D-20's 3-round-trip threshold is low; D-19's topic-hash is stable precisely to enable thread-identity.
**How to avoid:** (1) Cycle detector counts round-trips **without progress signal** — if either turn produced a `TaskCompleted` event OR a net-positive artifact bytes delta, that breaks the cycle streak. (2) Surface the cycle to a human via InteractionGate (not auto-abort) — human can override with "legitimate iteration" answer, which lifts suppression for the remaining sprint.
**Warning signs:** Cycle alerts fire on every normal design iteration in Phase 3 dogfood.

### Pitfall 4: `test_command` executes `pytest` with full project config, blowing timeout
**What goes wrong:** D-04's `SuccessCriterion.test_command` is often "`pytest tests/test_X.py -v`" but the agent's CWD may be the sprint worktree, not the repo root. `pytest` discovers 500 tests instead of the 5 intended.
**Why it happens:** No pin on the test runner.
**How to avoid:** (1) Gate runs the command via `subprocess.run(cmd, cwd=workspace_branch_path, timeout=300, shell=False, env={...})` — explicit CWD from `SprintState.workspace_branch`. (2) Mandate `-x` flag in the recommended test-command template; fail-fast if missing. (3) Cache key includes the test_command string — changing the command invalidates the cache entry.
**Warning signs:** EvidenceGate check takes > 60s repeatedly; CI timeouts.

### Pitfall 5: `FrozenPathError` raised during sprint pause serialization
**What goes wrong:** `clawteam sprint pause` writes a checkpoint, which triggers `BeforeFileWrite`, which consults `FreezeRegistry`, which may veto if the checkpoint path is "frozen".
**Why it happens:** Pause-checkpoint path is under `~/.clawteam/teams/<team>/sprints/<id>/` which overlaps with the sprint's own state.
**How to avoid:** FreezeRegistry scope is **agent writes to the repo working directory + workspace branches**. The sprint state directory (`~/.clawteam/teams/<team>/sprints/<id>/`) is exempt — it's harness internals, not agent code. Document explicitly: `FreezeRegistry.is_frozen(path)` returns False for paths under `get_data_dir()/teams/`.
**Warning signs:** `clawteam sprint pause` fails with `FrozenPathError: ~/.clawteam/teams/foo/sprints/abc/state.json is /freeze-locked` after user issued `/freeze /`.

### Pitfall 6: Discriminated-union fallback schema silently swallows unknown artifact types
**What goes wrong:** Agent writes `artifact_type: random-new-thing`; `EvidenceSchemaRegistry.get_schema()` returns None; EvidenceGate fails with a generic "unknown artifact_type" but this shouldn't be silent.
**Why it happens:** Default behavior of `dict.get()`.
**How to avoid:** EvidenceGate explicitly distinguishes (a) "no schema registered for this artifact_type" (planner error — Phase 3 forgot to register) from (b) "schema present but validation failed". Case (a) returns `(False, f"Unregistered artifact_type '{x}'. Phase 3 plugin must register.")`. Case (b) returns `(False, f"Schema validation failed: {err}")`.
**Warning signs:** Phase 3 agents produce artifacts that pass gate on some test fixtures and fail on others with an opaque error.

### Pitfall 7: `emit_async` used for cycle detection event when suppression depends on sync state change
**What goes wrong:** `CycleDetected` event handler tries to read `routes[route_key].suppressed_topics`, but the synchronous `decide()` caller has already returned before the async handler fires. Suppression state is inconsistent.
**Why it happens:** Confusing the two `emit` paths in `events/bus.py`.
**How to avoid:** Use `emit()` (sync) for `CycleDetected` and `ForcedProgressTriggered` — they require in-flight state changes. Use `emit_async()` only for notifications that don't cause follow-on state changes (e.g., metrics).
**Warning signs:** Cycle fires but suppression doesn't stick; A→B gets re-injected.

### Pitfall 8: Regression matrix (Phase 0) breaks because `ArtifactStore.write()` gains a hook chain
**What goes wrong:** Existing templates construct `ArtifactStore.write(name, content)` without frontmatter. D-07's frontmatter check kicks in, rejects every existing-template write.
**Why it happens:** Phase 2 hook chain runs unconditionally.
**How to avoid:** Frontmatter validation is **scoped to `EvidenceGate` checking gstack artifacts** — NOT to every `ArtifactStore.write()` call. The write-path hook chain is: size cap → `BeforeFileWrite` event → FreezeRegistry veto → write. Frontmatter parsing happens at gate check time (pulling artifacts by name), not at write time. The CONTEXT D-08 "two entry points" refers to the envelope fields on the `TeamMessage` (always validated) and the frontmatter on files THAT claim to be sprint artifacts (only validated when `EvidenceGate.check()` consumes them). Existing templates don't run `EvidenceGate`; their writes pass through the hook chain untouched beyond size-cap check.
**Warning signs:** `test_template_regression_matrix.py` failures mentioning "frontmatter missing" on software-dev or hedge-fund templates.
> **This is the single most important invariant for Phase 2 upstream-PR viability.** Re-read CONTEXT D-01 ("existing templates keep using ArtifactRequiredGate") if the planner is tempted to collapse the write-path and gate-time validation into one hook.

### Pitfall 9: `clawteam sprint list` without `--team` hangs scanning all teams
**What goes wrong:** D-24 requires `--team` but a permissive implementation might default to scanning every team.
**Why it happens:** Ergonomic "helpful default".
**How to avoid:** Strict: `MissingTeamError(code="MISSING_TEAM", message="...")` when neither `--team` nor `$CLAWTEAM_TEAM` is set. Explicit per D-24.
**Warning signs:** Tests pass but users find `clawteam sprint list` slow (scanning hundreds of teams' sprint directories).

### Pitfall 10: `EvidenceGate` deploy-URL HEAD request in sandboxed test env
**What goes wrong:** D-05's HEAD dereference runs during `pytest`. CI machine has no internet / `deploy_url` points to `http://localhost:3000` which isn't running.
**Why it happens:** Gate check is environment-dependent.
**How to avoid:** Test infrastructure injects a `deploy_url_checker` dependency (callable) into `EvidenceGate` constructor. Default checker uses `urllib.request`; tests pass a fake. Production gate checker: retry once on connection error, then fail with retry-hint.
**Warning signs:** Tests fail in CI but pass locally; `pytest tests/test_evidence_gate.py` fails on every PR when offline.

---

## Runtime State Inventory

N/A — Phase 2 is a greenfield additive phase. No rename / refactor / migration; no prior string / collection / registration to update. The only "pre-existing runtime state" to note:

- `SuccessCriterion.test_command` [VERIFIED: `harness/contracts.py:19`] has existed since pre-gstack work and has NEVER been executed anywhere in code [VERIFIED: `Grep "test_command" clawteam/ → single definition, zero reads`]. Phase 2's `EvidenceGate` is the first executor. No migration needed; field is already pydantic-defaulted to `""`.
- `RuntimeEnvelope.dedupe_key` [VERIFIED: `team/routing_policy.py:63`] and `TeamMessage.request_id` [VERIFIED: `team/models.py:102`] already exist with optional defaults. The cycle detector (D-19) reads them; no model edit needed.
- `SprintState` fields `turn_counters`, `artifact_cap_bytes`, `phase_artifact_cap_bytes` are ADDITIONS to the Phase 1 pydantic model. Pydantic v2 handles backward-compat by defaulting missing-from-JSON fields (`turn_counters = {}`, caps = sentinel defaults). Phase 1 sprint-state JSON files rehydrate cleanly.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Everything | ✓ | confirmed by pyproject.toml | — |
| pydantic v2 (≥ 2.11) | `TurnEnvelope`, `EvidenceSchemaRegistry`, discriminated unions | ✓ | 2.12.5 installed | — |
| typer | `sprint` sub-app | ✓ | 0.24.1 available, project uses ≥0.12 | — |
| rich | Human-readable CLI output | ✓ | project core | — |
| pytest | Test rerun via `test_command` | ✓ | 9.0.3 installed | — |
| stdlib `urllib.request` | HTTP HEAD for `deploy_url` | ✓ | stdlib | — |
| stdlib `subprocess` | Running `test_command` | ✓ | stdlib | — |
| stdlib `hashlib` | topic-hash + artifact-hash | ✓ | stdlib | — |
| stdlib `fcntl` / `msvcrt` | `file_locked()` | ✓ | stdlib (per-platform) | — |
| git CLI | `WorkspaceManager` git operations | ✓ | project already requires | — |

**Missing dependencies with no fallback:** None. Phase 2 is self-contained inside existing project stack.

**Missing dependencies with fallback:** None — every new capability uses stdlib or existing deps.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 [VERIFIED: `pip index versions pytest`] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` with `testpaths = ["tests"]` [VERIFIED] |
| Quick run command | `pytest tests/test_<module>.py -q` |
| Full suite command | `pytest -q` |
| Regression gate | `pytest tests/test_template_regression_matrix.py -q` (Phase 0 must-stay-green) |
| Ruff check | `ruff check clawteam/ tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-05 | `SprintConductor` starts a sprint, dispatches phase-advance events | unit | `pytest tests/test_sprint_conductor.py::test_start_sprint -x` | ❌ Wave 0 |
| CORE-05 | Conductor composes with PhaseRunner (single-phase gate evaluation) | integration | `pytest tests/test_sprint_conductor.py::test_advance_through_gates -x` | ❌ Wave 0 |
| CORE-07 | `pause` writes checkpoint, `resume` rehydrates + replays last event | integration | `pytest tests/test_sprint_conductor.py::test_pause_resume_round_trip -x` | ❌ Wave 0 |
| CORE-07 | Survives full orchestrator restart (new process) | integration | `pytest tests/test_sprint_conductor.py::test_resume_after_process_restart -x` | ❌ Wave 0 |
| INT-06 | `auto_advance=True` without questions → InteractionGate not inserted | unit | `pytest tests/test_sprint_conductor.py::test_auto_advance_skips_interaction_gate -x` | ❌ Wave 0 |
| INT-06 | `auto_advance=False` → InteractionGate always inserted | unit | `pytest tests/test_sprint_conductor.py::test_auto_advance_false_always_prompts -x` | ❌ Wave 0 |
| SPRINT-01 | `contribute_evidence_schemas` hook defaults to `{}` | unit | `pytest tests/test_plugins.py::test_contribute_evidence_schemas_default_empty -x` | ❌ Wave 0 |
| SPRINT-01 | Duplicate schema name across plugins raises at registration | unit | `pytest tests/test_plugins.py::test_evidence_schema_collision -x` | ❌ Wave 0 |
| SPRINT-02 | EvidenceGate presence check (inherited behavior) | unit | `pytest tests/test_evidence_gate.py::test_presence_check_preserved -x` | ❌ Wave 0 |
| SPRINT-02 | EvidenceGate layer 1 (pydantic frontmatter) | unit | `pytest tests/test_evidence_gate.py::test_layer1_frontmatter_required_fields -x` | ❌ Wave 0 |
| SPRINT-02 | EvidenceGate layer 2 (section ≤ 100 bytes = stub) | unit | `pytest tests/test_evidence_gate.py::test_layer2_stub_section_detected -x` | ❌ Wave 0 |
| SPRINT-02 | EvidenceGate layer 3 (regex blacklist TBD/TODO/...) | unit | `pytest tests/test_evidence_gate.py::test_layer3_blacklist_hit -x` | ❌ Wave 0 |
| SPRINT-02 | `test-report.md` gate re-runs test_command synchronously | integration | `pytest tests/test_evidence_gate.py::test_test_report_reruns_command -x` | ❌ Wave 0 |
| SPRINT-02 | Cache hit skips re-run | integration | `pytest tests/test_evidence_gate.py::test_cache_hit_skips_rerun -x` | ❌ Wave 0 |
| SPRINT-02 | `ship-notes.md` deploy_url HEAD 2xx → pass | integration | `pytest tests/test_evidence_gate.py::test_ship_notes_deploy_url_ok -x` | ❌ Wave 0 |
| SKILL-09 | TurnEnvelope validates persona/step_label/done | unit | `pytest tests/test_turn_envelope.py::test_required_fields -x` | ❌ Wave 0 |
| SKILL-09 | MalformedEnvelopeError raised at deliver() on missing field | unit | `pytest tests/test_turn_envelope.py::test_deliver_rejects_malformed -x` | ❌ Wave 0 |
| SKILL-09 | ArtifactStore.write() parses frontmatter through same model | unit | `pytest tests/test_turn_envelope.py::test_artifact_frontmatter_round_trip -x` | ❌ Wave 0 |
| SAFETY-01 | `/careful` regex matches rm -rf / git reset --hard / DROP TABLE | unit | `pytest tests/test_safety_rails.py::test_careful_blacklist_matches -x` | ❌ Wave 0 |
| SAFETY-01 | `/careful` warn-only default; --careful config vetoes | unit | `pytest tests/test_safety_rails.py::test_careful_veto_gate -x` | ❌ Wave 0 |
| SAFETY-02 | `/freeze <path>` veto on BeforeFileWrite | unit | `pytest tests/test_freeze_registry.py::test_freeze_path_vetoes_write -x` | ❌ Wave 0 |
| SAFETY-02 | FrozenPathError message references unfreeze command | unit | `pytest tests/test_freeze_registry.py::test_frozen_path_error_message -x` | ❌ Wave 0 |
| SAFETY-03 | `/guard` = /freeze + /careful composite | integration | `pytest tests/test_safety_rails.py::test_guard_composite -x` | ❌ Wave 0 |
| SAFETY-04 | `/unfreeze` writes FreezeChange to audit JSONL | unit | `pytest tests/test_freeze_registry.py::test_unfreeze_writes_audit -x` | ❌ Wave 0 |
| SAFETY-04 | freeze.json rehydrates after pause/resume | integration | `pytest tests/test_freeze_registry.py::test_freeze_persists_across_resume -x` | ❌ Wave 0 |
| QUALITY-01 | 8 consecutive malformed envelopes → DriftRegression event | unit | `pytest tests/test_turn_envelope.py::test_drift_regression_at_8_consecutive -x` | ❌ Wave 0 |
| QUALITY-01 | 1 successful envelope resets counter | unit | `pytest tests/test_turn_envelope.py::test_counter_resets_on_valid -x` | ❌ Wave 0 |
| QUALITY-02 | A↔B round-trip 3+ times in 20-msg window → CycleDetected | unit | `pytest tests/test_cycle_detector.py::test_three_roundtrips_trip_cycle -x` | ❌ Wave 0 |
| QUALITY-02 | Topic-hash priority chain (dedupe_key → request_id → sha1) | unit | `pytest tests/test_cycle_detector.py::test_topic_hash_priority_chain -x` | ❌ Wave 0 |
| QUALITY-02 | Cycle suppression persists until human answer | integration | `pytest tests/test_cycle_detector.py::test_suppression_lifts_on_answer -x` | ❌ Wave 0 |
| QUALITY-03 | Per-file cap 50 KB → ArtifactTooLargeError | unit | `pytest tests/test_artifact_caps.py::test_per_file_cap -x` | ❌ Wave 0 |
| QUALITY-03 | Per-phase cap 500 KB → compaction question | integration | `pytest tests/test_artifact_caps.py::test_per_phase_cap_compaction -x` | ❌ Wave 0 |
| QUALITY-03 | Three-layer cap override (state/CLI/env) — highest wins | unit | `pytest tests/test_artifact_caps.py::test_three_layer_override -x` | ❌ Wave 0 |
| QUALITY-06 | File-lock retry on concurrent freeze.json writes | unit | `pytest tests/test_freeze_registry.py::test_concurrent_freeze_writes -x` | ❌ Wave 0 |
| QUALITY-08 | EvidenceGate all 4 check layers (same as SPRINT-02 tests) | — | covered above | — |
| QUALITY-11 | 2 consecutive no-progress turns per-agent → forced_progress_gate | unit | `pytest tests/test_forced_progress_gate.py::test_two_turn_threshold -x` | ❌ Wave 0 |
| QUALITY-11 | Per-agent (not sprint-wide) counter | unit | `pytest tests/test_forced_progress_gate.py::test_per_agent_isolation -x` | ❌ Wave 0 |
| QUALITY-11 | TaskCompleted resets counter | unit | `pytest tests/test_forced_progress_gate.py::test_task_completed_resets -x` | ❌ Wave 0 |
| UX-02 | `sprint start` creates state.json, returns {id,goal,current_phase} | integration | `pytest tests/test_sprint_cli.py::test_sprint_start -x` | ❌ Wave 0 |
| UX-03 | `sprint status <id>` shows phase/participants/questions/latest-artifact | integration | `pytest tests/test_sprint_cli.py::test_sprint_status -x` | ❌ Wave 0 |
| UX-04 | `sprint list --team` requires team flag else error | unit | `pytest tests/test_sprint_cli.py::test_sprint_list_requires_team -x` | ❌ Wave 0 |
| UX-05 | `sprint show <id>` full detail | integration | `pytest tests/test_sprint_cli.py::test_sprint_show -x` | ❌ Wave 0 |
| UX-09 | --json envelope uniform {ok,data,warnings,error} on success+error | unit | `pytest tests/test_sprint_cli.py::test_json_envelope_uniform -x` | ❌ Wave 0 |
| UX-09 | Sprint prefix resolution + AmbiguousSprintError | unit | `pytest tests/test_sprint_cli.py::test_prefix_resolution_ambiguous -x` | ❌ Wave 0 |
| BC | Phase 0 regression matrix still green | regression | `pytest tests/test_template_regression_matrix.py -q` | ✅ exists |

### Sampling Rate

- **Per task commit:** `pytest tests/<target_module>.py -q` (target = what the task touches; e.g., Plan 02-03 touches `tests/test_evidence_gate.py`).
- **Per wave merge:** `pytest tests/test_template_regression_matrix.py tests/test_event_bus.py tests/test_harness.py tests/test_runtime_routing.py -q` — Phase 0 regression + event infrastructure + routing (cycle detector's substrate).
- **Phase gate:** Full suite `pytest -q` + `ruff check clawteam/ tests/` green before `/gsd-verify-work`.

### Wave 0 Gaps

- [ ] `tests/test_sprint_conductor.py` — covers CORE-05, CORE-07, INT-06
- [ ] `tests/test_evidence_gate.py` — covers SPRINT-02, QUALITY-08
- [ ] `tests/test_turn_envelope.py` — covers SKILL-09, QUALITY-01
- [ ] `tests/test_freeze_registry.py` — covers SAFETY-02, SAFETY-04, QUALITY-06
- [ ] `tests/test_safety_rails.py` — covers SAFETY-01, SAFETY-03
- [ ] `tests/test_forced_progress_gate.py` — covers QUALITY-11
- [ ] `tests/test_cycle_detector.py` — covers QUALITY-02
- [ ] `tests/test_artifact_caps.py` — covers QUALITY-03
- [ ] `tests/test_sprint_cli.py` — covers UX-02, UX-03, UX-04, UX-05, UX-09
- [ ] `tests/test_plugins.py` — already exists (`test_registry.py`); add `contribute_evidence_schemas` fixture

Framework install: not needed — pytest 9.0.3 is installed; `[tool.pytest.ini_options]` already configured.

---

## Code Examples

### Example 1: `TurnEnvelope` pydantic model (D-06, D-07, D-08)

```python
# clawteam/team/envelope.py
from __future__ import annotations
import re
from typing import Any
import yaml
from pydantic import BaseModel, Field, ValidationError


class TurnEnvelope(BaseModel):
    """Single pydantic model validating both TeamMessage envelope fields and artifact frontmatter."""
    persona: str = Field(..., min_length=1, description="Agent role asserting this turn")
    step_label: str = Field(..., min_length=1, description="Free-form step marker, e.g. 'plan:2/5'")
    done: bool = Field(..., description="Turn-done signal")

    # Artifact-only fields (None for TeamMessage-only envelopes)
    artifact_type: str | None = None
    created_at: str | None = None
    turn_id: str | None = None  # uuid.uuid4().hex[:8] — for dedupe across deliver+write


class MalformedEnvelopeError(ValueError):
    """Raised by deliver() and ArtifactStore.write() on missing/invalid envelope fields."""


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into (frontmatter_dict, body_string).

    Returns ({}, raw) if no frontmatter block present.
    Raises MalformedEnvelopeError on malformed YAML.
    """
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise MalformedEnvelopeError(f"frontmatter YAML invalid: {exc}") from exc
    if not isinstance(meta, dict):
        raise MalformedEnvelopeError(f"frontmatter must be a mapping, got {type(meta).__name__}")
    return meta, m.group(2)


def validate_envelope(meta: dict[str, Any]) -> TurnEnvelope:
    """Validate a meta dict as a TurnEnvelope; raises MalformedEnvelopeError on failure."""
    try:
        return TurnEnvelope.model_validate(meta)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"])
        raise MalformedEnvelopeError(f"envelope invalid: {field}: {first['msg']}") from exc
```
[Source: pattern from pydantic v2 ValidationError handling — Context7 /websites/pydantic_dev_validation; frontmatter regex from python-frontmatter 1.1.0 reference implementation — CITED: github.com/eyeseast/python-frontmatter/blob/main/frontmatter/__init__.py]

### Example 2: `FreezeRegistry` singleton with atomic JSON persistence (D-11, D-13)

```python
# clawteam/harness/freeze_registry.py
from __future__ import annotations
import json
from pathlib import Path
from threading import RLock
from typing import Iterable

from clawteam.fileutil import file_locked, atomic_write_text
from clawteam.team.models import get_data_dir


class FreezeRegistry:
    def __init__(self, team_name: str, sprint_id: str):
        self._team = team_name
        self._sprint = sprint_id
        self._lock = RLock()
        self._frozen_paths: dict[str, set[str]] = {}  # agent → set[path-str]
        self._frozen_globs: set[str] = set()
        self._load()

    def _sprint_dir(self) -> Path:
        return get_data_dir() / "teams" / self._team / "sprints" / self._sprint

    def _freeze_path(self) -> Path:
        return self._sprint_dir() / "freeze.json"

    def _audit_path(self) -> Path:
        return self._sprint_dir() / "freeze_audit.jsonl"

    def _load(self) -> None:
        p = self._freeze_path()
        if not p.exists():
            return
        with file_locked(p):
            data = json.loads(p.read_text(encoding="utf-8"))
        self._frozen_paths = {k: set(v) for k, v in data.get("paths", {}).items()}
        self._frozen_globs = set(data.get("globs", []))

    def _save(self) -> None:
        p = self._freeze_path()
        payload = {
            "paths": {k: sorted(v) for k, v in self._frozen_paths.items()},
            "globs": sorted(self._frozen_globs),
        }
        with file_locked(p):
            atomic_write_text(p, json.dumps(payload, indent=2, ensure_ascii=False))

    def is_frozen(self, path: Path) -> tuple[bool, str]:
        """Returns (is_frozen, reason). Exempts paths under the ClawTeam data dir."""
        data_dir = get_data_dir()
        try:
            path.resolve().relative_to(data_dir.resolve())
            return False, ""  # sprint-internal writes are always allowed (Pitfall #5)
        except ValueError:
            pass
        path_str = str(path.resolve())
        with self._lock:
            for agent, paths in self._frozen_paths.items():
                for frozen in paths:
                    if path_str.startswith(frozen):
                        return True, f"path locked by {agent} via /freeze"
            import fnmatch
            for glob in self._frozen_globs:
                if fnmatch.fnmatch(path_str, glob):
                    return True, f"path matches frozen glob {glob}"
        return False, ""

    def freeze(self, path: str, *, agent: str, reason: str, actor: str) -> None:
        with self._lock:
            self._frozen_paths.setdefault(agent, set()).add(str(Path(path).resolve()))
            self._save()
        self._audit("freeze", path, agent, reason, actor)

    def unfreeze(self, path: str, *, agent: str, reason: str, actor: str) -> None:
        p = str(Path(path).resolve())
        with self._lock:
            if agent in self._frozen_paths:
                self._frozen_paths[agent].discard(p)
                self._save()
        self._audit("unfreeze", path, agent, reason, actor)

    def _audit(self, action: str, path: str, agent: str, reason: str, actor: str) -> None:
        from datetime import datetime, timezone
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "path": path,
            "agent": agent,
            "reason": reason,
            "actor": actor,
            "sprint_id": self._sprint,
        }
        ap = self._audit_path()
        ap.parent.mkdir(parents=True, exist_ok=True)
        with open(ap, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


_registry: FreezeRegistry | None = None

def get_freeze_registry(team: str | None = None, sprint_id: str | None = None) -> FreezeRegistry | None:
    """Module-level singleton accessor. Returns None if no sprint context is set."""
    global _registry
    if _registry is None and team and sprint_id:
        _registry = FreezeRegistry(team, sprint_id)
    return _registry


def reset_freeze_registry() -> None:
    """For testing."""
    global _registry
    _registry = None


class FrozenPathError(ValueError):
    """Raised when an agent write/tool-call is vetoed by FreezeRegistry."""
```
[Source: mirrors `harness/exit_journal.py` JSONL append pattern; `team/snapshot.py:21-36` atomic-JSON pattern; `events/bus.py:51` RLock convention]

### Example 3: Sprint CLI `start` command with uniform JSON envelope (D-24, D-26)

```python
# clawteam/cli/commands.py — additions
sprint_app = typer.Typer(name="sprint", help="Sprint lifecycle commands.", no_args_is_help=True)


def _emit_ok(data: dict, warnings: list[str] | None = None) -> None:
    payload = {"ok": True, "data": data, "warnings": warnings or [], "error": None}
    if _json_output:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _render_sprint(data)


def _emit_err(code: str, message: str) -> None:
    payload = {"ok": False, "data": None, "warnings": [], "error": {"code": code, "message": message}}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    raise typer.Exit(1)


@sprint_app.command("start")
def sprint_start(
    team: str = typer.Option(..., "--team", envvar="CLAWTEAM_TEAM"),
    goal: str = typer.Option(..., "--goal"),
    auto_advance: bool = typer.Option(False, "--auto-advance"),
    artifact_cap: int | None = typer.Option(None, "--artifact-cap", help="Per-file cap in KB."),
    phase_artifact_cap: int | None = typer.Option(None, "--phase-artifact-cap", help="Per-phase cap in KB."),
):
    from clawteam.sprint.conductor import SprintConductor
    try:
        conductor = SprintConductor(
            team_name=team,
            artifact_cap_bytes=(artifact_cap or 0) * 1024 or None,
            phase_artifact_cap_bytes=(phase_artifact_cap or 0) * 1024 or None,
        )
        state = conductor.start(goal=goal, auto_advance=auto_advance)
        _emit_ok({"id": state.sprint_id, "goal": state.goal, "current_phase": state.current_phase})
    except Exception as exc:
        _emit_err("SPRINT_START_FAILED", str(exc))


@sprint_app.command("status")
def sprint_status(
    id_or_prefix: str = typer.Argument(..., metavar="ID|PREFIX"),
    team: str | None = typer.Option(None, "--team", envvar="CLAWTEAM_TEAM"),
):
    from clawteam.sprint.conductor import SprintConductor, AmbiguousSprintError, SprintNotFoundError
    try:
        state = SprintConductor.load_by_prefix(id_or_prefix, team=team)
        _emit_ok({
            "id": state.sprint_id,
            "goal": state.goal,
            "current_phase": state.current_phase,
            "participants": state.participants,
            "pending_questions": len(state.pending_question_ids),
            "most_recent_artifact": max(state.artifacts.keys(), default=None),
        })
    except AmbiguousSprintError as exc:
        _emit_err("AMBIGUOUS_SPRINT", f"prefix matches: {', '.join(exc.candidates)}")
    except SprintNotFoundError as exc:
        _emit_err("SPRINT_NOT_FOUND", str(exc))


app.add_typer(sprint_app, name="sprint")
```
[Source: Typer sub-app pattern per typer.tiangolo.com/tutorial/subcommands/single-file; existing `cli/commands.py:82-122` callback pattern for `--json` / `_json_output`]

### Example 4: Cycle detector hooked into `DefaultRoutingPolicy.decide()` (D-18..D-21)

```python
# clawteam/team/routing_policy.py — addition (inside DefaultRoutingPolicy)

def decide(self, envelope: RuntimeEnvelope, now=None) -> RouteDecision:
    now_dt = _ensure_datetime(now)
    state = self.read_state()

    # Step 0 — cycle detection BEFORE throttle (D-18)
    cycle_hit = self._detect_cycle(state, envelope)
    if cycle_hit is not None:
        route_key_a_b = self._route_key(envelope.source, envelope.target)
        # Suppress further A→B on this topic
        route = state["routes"].setdefault(route_key_a_b, self._empty_route(envelope))
        route.setdefault("suppressedTopics", [])
        if cycle_hit.topic_hash not in route["suppressedTopics"]:
            route["suppressedTopics"].append(cycle_hit.topic_hash)
        self._append_event(state, route_key_a_b, route,
            action="cycle_suppressed", reason=cycle_hit.reason,
            summary=envelope.summary, timestamp=now_dt)
        self._save_state(state)
        try:
            from clawteam.events.global_bus import get_event_bus
            from clawteam.events.types import CycleDetected
            get_event_bus().emit(CycleDetected(
                team_name=self.team_name,
                pair=(envelope.source, envelope.target),
                topic_hash=cycle_hit.topic_hash,
                route_keys=cycle_hit.route_keys,
                window_size=20,
            ))
        except Exception:
            pass
        return RouteDecision(action="suppress", reason="cycle_detected",
            envelope=envelope, route_key=route_key_a_b)

    # Honor existing suppression
    route_key_a_b = self._route_key(envelope.source, envelope.target)
    existing_route = state["routes"].get(route_key_a_b, {})
    if self._topic_hash(envelope) in existing_route.get("suppressedTopics", []):
        return RouteDecision(action="suppress", reason="topic_previously_cycled",
            envelope=envelope, route_key=route_key_a_b)

    # EXISTING throttle logic continues unchanged below …

def _topic_hash(self, envelope: RuntimeEnvelope) -> str:
    """D-19 priority chain: dedupe_key > request_id > sha1(content[:128])."""
    import hashlib
    if envelope.dedupe_key:
        return envelope.dedupe_key
    req_id = envelope.payload.get("request_id") or envelope.payload.get("requestId")
    if req_id:
        return str(req_id)
    content = envelope.payload.get("content") or envelope.summary or ""
    return hashlib.sha1(content[:128].encode("utf-8")).hexdigest()[:16]

@dataclass
class _CycleHit:
    topic_hash: str
    route_keys: list[str]
    reason: str

def _detect_cycle(self, state: dict, envelope: RuntimeEnvelope) -> _CycleHit | None:
    """D-20: ≥3 A→B and ≥3 B→A in last 20 events with matching topic hash."""
    topic = self._topic_hash(envelope)
    window = state.get("recentEvents", [])[-20:]
    route_a_b = self._route_key(envelope.source, envelope.target)
    route_b_a = self._route_key(envelope.target, envelope.source)
    count_ab = sum(1 for e in window if e.get("routeKey") == route_a_b and e.get("topicHash") == topic)
    count_ba = sum(1 for e in window if e.get("routeKey") == route_b_a and e.get("topicHash") == topic)
    if count_ab >= 3 and count_ba >= 3:
        return _CycleHit(topic_hash=topic, route_keys=[route_a_b, route_b_a],
            reason=f"A↔B with topic {topic} repeated 3+ each in 20-msg window")
    return None

# Extend _append_event to write topicHash into the event record so the cycle scan above works:
# entry["topicHash"] = self._topic_hash(envelope)  # add this line
```
[Source: extends existing `DefaultRoutingPolicy` at `team/routing_policy.py:93-408`; cycle-detection algorithm mirrors Paperclip issue #390 — CITED: github.com/paperclipai/paperclip/issues/390]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Presence-only phase gates (`ArtifactRequiredGate`) | Evidence-bound gates with content + schema + replay validation (EviBound, Three Dots Labs) | 2025 (EviBound NeurIPS Oct 2025 [CITED: arxiv.org/abs/2511.05524]) | Phase 2 `EvidenceGate` adopts the 4-check protocol |
| Budget-only agent circuit breaker | Multi-signal circuit breaker (no-progress + consecutive-fail + token-velocity) | 2026-03 (Paperclip #390) | Phase 2's theater detector adopts no-progress signal; velocity/cost deferred to Phase 7 |
| One-shot ReAct prompt with freelance | Structured response envelope (persona / step / state) per turn | 2024-2025 (LangGraph `responseFormat`) [CITED: docs.langchain.com/oss/javascript/langchain/agents] | Phase 2 `TurnEnvelope` required fields enforced at deliver + write boundaries |
| Hand-rolled YAML frontmatter + separate body pydantic model | `python-frontmatter` + pydantic discriminated union | 2022+ | Phase 2 uses stdlib split + pydantic discriminator (no new top-level dep) |
| Per-tool allow/deny config hand-edited | Registry singleton + veto-event bus (contradictor/guardrail pattern) | 2024-2025 (OWASP MAS threat model v1.0, Fastio lock pattern) | Phase 2 `FreezeRegistry` + `BeforeToolCall`/`BeforeFileWrite` events |
| Single-phase context compaction at 85% window | Two-phase prune-then-compact (Kilocode/Factory.ai) [CITED: factory.ai/news/compressing-context] | 2025 | Phase 2 ships per-file + per-phase caps + InteractionGate compaction prompt; LLM-based compaction deferred |
| Mailbox presence as "progress" | Artifact bytes delta + TaskCompleted as "progress" | 2026 (ROADMAP SC#6) | Phase 2 D-15 explicitly excludes mailbox from progress signal |

**Deprecated / outdated:**

- **LangGraph one-shot prompts without structured response:** 2024 baseline ReAct with freelance completion; 2025 docs all recommend `responseFormat` / AgentBaseModel. Phase 2 aligns with the current recommendation [CITED: docs.langchain.com/oss/javascript/langchain/agents].
- **Hand-rolled cycle detectors with new state stores:** MAST paper documents this as a common failure mode [CITED: arxiv.org/abs/2503.13657 — Multi-Agent Systems Failure Taxonomy]. Phase 2 explicitly reuses `DefaultRoutingPolicy.recentEvents` per CONTEXT lesson #1.
- **STRIDE-only threat modeling for multi-agent systems:** 2025 consensus (OWASP MAS Threat Modeling Guide v1.0, arXiv 2508.09815) — STRIDE covers individual-agent threats but misses multi-step cross-agent attack chains. Phase 2's safety rails address cross-agent threats via registry + audit + structured errors.

---

## Security Domain

> ASVS v5.0 (released Global AppSec EU Barcelona 2025 [CITED: raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/...]) applies; `security_enforcement` is enabled by default per config. Phase 2 threat surface is agent-driven writes + tool calls + sprint-CLI input.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface added; MCP / CLI inherit project auth posture |
| V3 Session Management | no | No session; sprint state is stateless-JSON per call |
| V4 Access Control | yes | FreezeRegistry = path-based access-control on writes (read-side unchanged) |
| V5 Input Validation | yes | pydantic v2 strict validation on `TurnEnvelope`, `TeamMessage`, sprint CLI options [VERIFIED: pydantic docs — strict mode default in 2.x] |
| V6 Cryptography | no | No new crypto; `sha1(content[:128])` is topic identity, not integrity; `sha256` for cache-hit detection only |
| V7 Error Handling & Logging | yes | Structured errors (`FrozenPathError`, `MalformedEnvelopeError`, `ArtifactTooLargeError`, `AmbiguousSprintError`, `SprintNotFoundError`) surface machine-readable codes via `--json` envelope `error.code`; audit JSONL for freeze changes |
| V8 Data Protection | partial | `freeze_audit.jsonl` contains agent+path+reason+actor — no secrets; existing env-scrubber (Phase 0 QUALITY-15) covers broader exposure |
| V9 Communication | no | No new network-layer surface (HEAD request uses stdlib HTTPS if URL is `https://`) |
| V10 Malicious Code | yes | `/careful` blacklist prevents rm -rf / DROP TABLE / force-push execution; structured tool errors on freeze violations |
| V11 Business Logic | yes | Cycle detector prevents infinite A↔B chat loops; theater detector prevents agents from claiming work without progress |
| V12 Files & Resources | yes | Per-file + per-phase artifact caps; `ensure_within_root()` on all sprint path access [VERIFIED: `paths.py::ensure_within_root`] |
| V13 API & Web Service | partial | Sprint CLI `--json` envelope is a stable machine interface; MCP tool wrappers surface structured errors |
| V14 Configuration | yes | Three-layer cap override (state/CLI/env) is configuration-consistent; no hardcoded credentials |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed frontmatter bypasses envelope validation (agent writes `artifact_type: null`) | Tampering | Pydantic strict validation raises `MalformedEnvelopeError`; gate short-circuits |
| Path traversal via `/freeze ../../../etc/passwd` | Elevation of Privilege | `Path.resolve()` + `ensure_within_root()` on freeze/unfreeze inputs; reject symlink escapes |
| Destructive command through `subprocess` inside `test_command` | Malicious Code Execution | `/careful` regex blacklist subscribed to `BeforeToolCall`; `test_command` run in controlled subprocess with explicit CWD + timeout + no shell expansion (shell=False, pass as list) |
| Regex-only stub detection gamed via unicode lookalikes (fullwidth Latin forms of TBD/TODO, zero-width-space-inserted words) | Tampering / Bypass | Layered defense: (1) frontmatter required fields non-empty, (2) body ≤ 100 bytes = stub (catches whitespace games), (3) regex. All three layers must pass. Consider NFKC normalization + zero-width-char stripping before regex (Phase 3 tuning per CONTEXT Deferred). |
| Cycle suppression persists across unrelated sprint on same team | Information Disclosure / DoS | Suppression stored per-route-key in `runtime_state.json` which is already team-scoped [VERIFIED: `routing_policy.py:46-47`]; no cross-sprint leak because `SprintConductor` owns sprint scope not team scope |
| `BeforeToolCall` veto bypassed by direct subprocess from agent code | Spoofing | Covered by `/careful` scope: event fires inside MCP `_tool` wrapper and CLI interception; agents using their own subprocess outside ClawTeam machinery are outside threat model (documented as a non-goal) |
| Artifact cap override via env var elevation | Denial of Service prevention | Env var `CLAWTEAM_ARTIFACT_CAP_KB` is highest-priority (D-29); acceptable trade-off since the env var is user-set, not attacker-set; sandbox-safe pattern |
| Deploy-URL HEAD request to internal network (SSRF) | Information Disclosure | `ship-notes.md` deploy-URL dereference is a 2xx/3xx check with 10s timeout; in Phase 5 planning, add URL allowlist pattern (e.g., reject `localhost`, `169.254.*`, `10.*`). Phase 2 ships the HEAD check + schema; Phase 5's `/ship` wires the URL and must add SSRF allowlist. **Call-out to Phase 5 plan.** |
| Forgery of `persona` field (engineer claims to be reviewer) | Spoofing | Harness cross-references the `persona` field against the caller's registered role assignment (CONTEXT D-06: "must match the caller's registered role; harness verifies"). Violation → `MalformedEnvelope` event; 8-turn threshold → `DriftRegression`. |
| JSON CLI output injection (sprint goal contains `"}]}`) | Injection | `json.dumps()` handles escaping; no string concatenation with user input. All CLI output goes through `_emit_ok`/`_emit_err` which uses `json.dumps(payload)`. |

**Phase 5 follow-up:** SSRF allowlist for `deploy_url` — tracked explicitly; Phase 2 ships the hook, Phase 5 adds the list.

---

## Sources

### Primary (HIGH confidence)

**Codebase sources (VERIFIED via Read/Grep on this branch):**
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/phases.py` — Phase/PhaseState/PhaseGate/ArtifactRequiredGate/HumanApprovalGate/PhaseRunner definitions
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/artifacts.py` — ArtifactStore.write() current behavior (no hook chain yet)
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/contracts.py` — SuccessCriterion with unwired test_command field
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/exit_journal.py` — JSONL append-only audit pattern
- `/home/jac/repos/ClawTeam-gstack/clawteam/events/bus.py` — EventBus veto semantics (`event.veto = True`)
- `/home/jac/repos/ClawTeam-gstack/clawteam/events/types.py` — Before*/After* event family + veto convention
- `/home/jac/repos/ClawTeam-gstack/clawteam/team/models.py` — TeamMessage pydantic shape (line 90-122)
- `/home/jac/repos/ClawTeam-gstack/clawteam/team/routing_policy.py` — DefaultRoutingPolicy + RuntimeEnvelope + recentEvents rolling window
- `/home/jac/repos/ClawTeam-gstack/clawteam/fileutil.py` — file_locked() + atomic_write_text() primitives
- `/home/jac/repos/ClawTeam-gstack/clawteam/mcp/server.py` + `/home/jac/repos/ClawTeam-gstack/clawteam/mcp/helpers.py` — MCP tool wrapper + translate_error seam
- `/home/jac/repos/ClawTeam-gstack/clawteam/cli/commands.py` — existing Typer callback + `--json` global + `_output` helper
- `/home/jac/repos/ClawTeam-gstack/clawteam/workspace/manager.py` — WorkspaceManager write paths to hook with BeforeFileWrite
- `/home/jac/repos/ClawTeam-gstack/clawteam/plugins/base.py` — HarnessPlugin ABC + contribute_* hook convention
- `/home/jac/repos/ClawTeam-gstack/pyproject.toml` — project deps (pydantic>=2, typer>=0.12, rich, questionary, mcp>=1) + Python 3.10+
- `/home/jac/repos/ClawTeam-gstack/tests/test_event_bus.py:45-55` — documented veto test pattern

**Pydantic docs (via Context7 `/websites/pydantic_dev_validation`):**
- Discriminated unions with `Field(discriminator='type')` and `Literal[...]` values
- Pattern for tagged unions by field name
- `Annotated[Union[...], Field(discriminator=...)]` and `Tag` + `Discriminator` function
- ValidationError error-location format `{"loc": [...], "msg": "..."}`

**EviBound (arXiv 2511.05524, Nov 2025) — governance framework:**
- URL: https://arxiv.org/abs/2511.05524 / https://arxiv.org/html/2511.05524v1
- Acceptance contract schema (run_id + metrics + artifacts + status)
- Phase 6 verification 4-check protocol
- Rejection taxonomy (schema violations, missing artifacts, empty arrays, placeholder values, confidence threshold)
- Claims Ledger format for replay verification

**Paperclip AI issue #390 — circuit breaker design:**
- URL: https://github.com/paperclipai/paperclip/issues/390
- Three detection signals: no-progress / consecutive-fail / token-velocity
- Configuration schema (`maxConsecutiveNoProgress: 5`, `maxConsecutiveFailures: 3`, `tokenVelocityMultiplier: 3.0`)
- Reset mechanism on successful progress

### Secondary (MEDIUM confidence — WebSearch verified against official source)

- **MAST: Multi-Agent Systems Failure Taxonomy** — NeurIPS 2025 Datasets & Benchmarks spotlight (arXiv 2503.13657)
  - URL: https://arxiv.org/abs/2503.13657
  - 14 failure modes across system-design / inter-agent-misalignment / task-verification categories
- **Typer sub-app pattern** — https://typer.tiangolo.com/tutorial/subcommands/single-file/
- **Typer nested subcommands** — https://typer.tiangolo.com/tutorial/subcommands/nested-subcommands/
- **LangGraph structured response** — https://docs.langchain.com/oss/javascript/langchain/agents
- **Kilocode / Factory.ai two-phase compaction** — https://factory.ai/news/compressing-context
- **python-frontmatter library** — https://python-frontmatter.readthedocs.io/
- **OWASP ASVS v5.0** — https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0/5.0/OWASP_Application_Security_Verification_Standard_5.0.0_en.pdf
- **OWASP Multi-Agentic System Threat Modeling Guide v1.0** — https://genai.owasp.org/resource/multi-agentic-system-threat-modeling-guide-v1-0/
- **Extending OWASP MAS Threat Model** — https://arxiv.org/html/2508.09815v1
- **Temporal durable asyncio event loop** — https://temporal.io/blog/durable-distributed-asyncio-event-loop (for replay idiom)
- **asyncio pause/resume pattern** — https://github.com/m2-farzan/asyncio-pause-resume
- **Fastio multi-agent workspace lock pattern** — https://fast.io/resources/openclaw-multi-agent-workspaces/

### Tertiary (LOW confidence — WebSearch only, unverified)

- Nervegna Substack "Paperclip org chart" commentary — anecdotal
- Various MindStudio / Sterlites tutorial blogs — marketing content around Paperclip, not authoritative

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Running `test_command` via `subprocess.run(..., timeout=300)` is a safe default | Pitfall #4, Example/Pattern 3 | Phase 3 artifact with longer tests times out; planner must expose `timeout` field on `SuccessCriterion` or accept convention. Mitigation: make timeout configurable via `CLAWTEAM_TEST_TIMEOUT_SECONDS` env with 300s default. `[ASSUMED]` |
| A2 | `python-frontmatter` dep adds transitive pressure ClawTeam shouldn't take | Standard Stack recommendation | If stdlib parser turns out buggy on edge cases (CR/LF, BOM), planner reconsiders. Mitigation: reference implementation is python-frontmatter's own 150-LOC source. `[ASSUMED]` |
| A3 | stdlib `urllib.request` HEAD request is adequate (no `requests` retry logic) | Don't Hand-Roll table | If deploy-URL check needs redirects/retries beyond simple 2xx/3xx, might want `requests`. Mitigation: Phase 5 owns the URL wiring; Phase 2's check is intentionally a simple health probe. `[ASSUMED]` |
| A4 | `DefaultRoutingPolicy.recentEvents` 50-entry window is sufficient to hold the last 20 events scanned for cycle detection | Pattern 4 | If cycle detection window = 20 but rolling window = 50, still fine. If workloads push past 50 events quickly, may miss older cycles — but that's desired behavior (old cycles aren't relevant). `[VERIFIED]` not assumed: `routing_policy.py:16` confirms `_RECENT_EVENT_LIMIT = 50`. |
| A5 | `threading.RLock` is the simpler concurrency primitive for `SprintConductor` | Alternatives Considered | If Phase 7's load test requires `asyncio.Lock`, migration is straightforward (same API surface). Mitigation: CONTEXT Claude's-Discretion explicitly defers this choice. `[ASSUMED]` |
| A6 | Existing templates don't construct `EvidenceGate` and thus won't hit frontmatter-parse paths | Pitfall #8 | This is the upstream-PR viability hinge. If an existing template somehow registered `EvidenceGate`, regression breaks. Mitigation: Phase 2 doesn't export `EvidenceGate` from `clawteam/harness/__init__.py` without explicit opt-in via plugin. `[VERIFIED]` via CONTEXT D-01 and CANONICAL_REFS: "existing templates continue to use `ArtifactRequiredGate`". |
| A7 | Round-trip cycle threshold of 3 each (= 6 total) in 20-message window won't flag legitimate designer-engineer iteration | Pitfall #3 | If designer iterates more than 3 times on the same `request_id`, cycle fires. Mitigation: topic-hash priority chain (D-19) defaults to sha1(content[:128]) when `dedupe_key` / `request_id` absent — normal iteration produces different content, different hashes. Explicit thread-identity via `dedupe_key` is a Phase 4 /office-hours concern, not Phase 2's. `[ASSUMED]` |
| A8 | 100-byte per-required-`##`-section stub threshold (D-03 layer 2) is conservative enough not to false-positive real content | Pitfall #6 | If a legitimate section under a required header is actually ≤ 100 bytes (e.g., a terse success criterion), gate fires. Mitigation: CONTEXT makes this a stub signal; agent should write prose, not one-liner. Planner may surface this as a configurable per-schema field. `[ASSUMED]` |
| A9 | Agent CLIs (Claude, Codex, Gemini) will self-correct on `FrozenPathError` / `MalformedEnvelopeError` structured response | CONTEXT D-12 trust | If a CLI ignores the structured response, freeze may not take effect — but the next tool call will also veto, so infinite loop is impossible. Mitigation: CONTEXT requires safety-rail unit tests verify the error message contains the remediation command. `[ASSUMED]` |

**Non-empty table — user / discuss-phase should confirm:**
- **A1** (test-command timeout default) — planner may want user input on default value; 300s is the EviBound precedent.
- **A7** (cycle threshold) — validate during Phase 3 dogfood; tune per feedback.
- **A8** (stub byte threshold) — validate during Phase 3 dogfood.
- **A9** (CLI self-correction on structured error) — CONTEXT D-12 accepts this; safety-rail unit tests are the checkpoint.

---

## Open Questions (RESOLVED)

1. **Should `test_command` run with a hard `timeout` field on `SuccessCriterion`, or a global `CLAWTEAM_TEST_TIMEOUT_SECONDS` env?**
   - What we know: D-04 specifies synchronous run with cache; doesn't specify timeout.
   - What's unclear: whether timeout is per-criterion or global.
   - Recommendation: global env var with 300s default (EviBound precedent); planner may add per-criterion override in Phase 4.
   - **RESOLVED:** global env `CLAWTEAM_TEST_TIMEOUT_SECONDS` with 300s default; per-`SuccessCriterion` override field reserved for future (Phase 4).

2. **Should `forced_progress_gate` escalate at 2 turns (CONTEXT D-16) even if the agent is blocking on an unanswered InteractionGate question?**
   - What we know: D-16 = 2 consecutive per-agent no-progress.
   - What's unclear: if agent Q was asked and waiting for human, does the 2-turn no-progress counter fire before the human responds?
   - Recommendation: forced_progress_gate checks `SprintState.pending_question_ids` — if agent has pending questions authored by them, counter does NOT increment. Rationale: waiting-for-human is legitimate non-progress.
   - **RESOLVED:** do NOT increment the no-progress counter when the agent is legitimately blocked by its own `pending_question_ids` (ownership check). Waiting-for-human is legitimate non-progress and must not trigger the gate.

3. **Is the `/careful` regex blacklist active ONLY inside `BeforeToolCall` events, or does `ArtifactStore.write()` also scan artifact content for destructive-command-embedded strings?**
   - What we know: D-13 scopes `/careful` to BeforeToolCall (tool call interception).
   - What's unclear: if an agent writes `rm -rf /` into a `ship-notes.md` deploy script, is that tool call or file write?
   - Recommendation: per CONTEXT, `/careful` is tool-call scope. File contents are agent-authored — content-scanning is beyond Phase 2. Phase 5's `/ship` may add script-content scanning as a separate layer.
   - **RESOLVED:** tool-call scope only in Phase 2 (`BeforeToolCall` regex on args). Content-scanning artifact bodies for destructive strings is deferred to Phase 5 `/ship`.

4. **Does the Phase 2 `contribute_evidence_schemas` hook emit an empty `{}` default as documented, or does Phase 3 wire the schema registration in `GstackSprintPlugin.on_register()` directly?**
   - What we know: CONTEXT "Established Patterns" names the hook.
   - What's unclear: whether registration flow is hook-based (plugin manager calls the hook) or `on_register`-based (plugin populates registry itself).
   - Recommendation: hook-based (mirrors Phase 1's three hooks). Consistent. Plugin manager calls `plugin.contribute_evidence_schemas()` at load time, same loop as contribute_phases / phase_roles / review_routers.
   - **RESOLVED:** plugin-manager-calls-hook (Phase 1 three-hooks pattern) — NOT `on_register()`. Plugin manager loops `plugin.contribute_evidence_schemas()` at load time, same as `contribute_phases` / `phase_roles` / `review_routers`.

5. **Where does the `turn_id` field live when populating `TurnEnvelope` — is it generated by the harness or by the agent?**
   - What we know: D-14 turn counter; D-07 envelope shape.
   - What's unclear: the actual `turn_id` generator.
   - Recommendation: agent generates a `uuid.uuid4().hex[:8]` at the start of a turn and includes it in every deliver/write during that turn. Harness uses it to dedupe counter increments (Pitfall #2 mitigation). Document as a required field if Pitfall #2 mitigation is chosen.
   - **RESOLVED:** agent-generated at turn start (`uuid.uuid4().hex[:8]`) and included on every `deliver` / `write` during that turn. Harness dedupes counter increments by `(agent, turn_id)` — Pitfall #2 mitigation.

6. **Is the `SprintConductor.pause()` call idempotent — can it be called twice without corrupting the checkpoint?**
   - What we know: CORE-07 requires pause/resume.
   - What's unclear: double-pause semantics.
   - Recommendation: idempotent — `pause()` on an already-paused sprint is a no-op that logs a warning. `SprintState.status: Literal['running'|'paused'|'completed']` makes this explicit.
   - **RESOLVED:** idempotent. `SprintConductor.pause()` on an already-paused sprint is a no-op that logs a warning. `SprintState.status: Literal['running'|'paused'|'completed']` is the state guard.

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all libraries already in project, versions verified via `pip index versions`
- Architecture patterns: **HIGH** — every pattern grounded in a VERIFIED codebase location or a CITED official source
- Pitfalls: **MEDIUM-HIGH** — catalogued from EviBound precedent (4 pitfalls), MAST paper (3 pitfalls), Paperclip issue #390 (2 pitfalls), existing test_event_bus.py veto semantics (1 pitfall); "envelope recursion" (Pitfall #1) and "regression matrix" (Pitfall #8) are conservative from first-principles reasoning
- EvidenceGate 4-check protocol: **HIGH** — direct port from EviBound §3 with field mapping documented
- Cycle detector algorithm: **HIGH** — mirrors Paperclip #390 design; implementation mapped cleanly onto VERIFIED existing state machine at `routing_policy.py:271,384`
- Theater detector: **MEDIUM-HIGH** — Paperclip #390 is the precedent; per-agent (not sprint-wide) threshold is CONTEXT D-16's call; threshold value (2 turns) is conservative compared to Paperclip's proposed default 5
- Safety rails: **HIGH** — every element maps onto VERIFIED existing ClawTeam patterns (EventBus veto, exit_journal JSONL, FreezeRegistry ≈ PhaseRegistry shape)
- Sprint CLI: **HIGH** — Typer sub-app is the canonical pattern; `--json` envelope format is explicitly locked by D-26
- Artifact caps: **MEDIUM** — `50 KB` / `500 KB` defaults are reasonable (per Kilocode / Factory.ai compaction precedent) but untested against real Phase 3 gstack artifacts; tuning may be needed at dogfood
- Validation architecture: **HIGH** — test inventory fully enumerated; every REQ-ID has 1+ test mapped

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (30 days — stack is stable; prior-art papers are recent/canonical)

**Key claims that need user / discuss-phase confirmation:** A1 (test-command timeout default), A7 (cycle threshold tune), A8 (stub byte threshold tune), A9 (CLI self-correction assumption). Everything else is either VERIFIED against this branch or CITED to a specific external source.

---

*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Research completed: 2026-04-17*
