# Phase 1: Core Harness Extensions - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add three new harness primitives (`PhaseRegistry`, `SprintState`, `InteractionGate`)
and three new optional `HarnessPlugin` hooks (`contribute_phases`,
`contribute_phase_roles`, `contribute_review_routers`) with empty defaults. All
changes are purely additive to the existing harness surface — no edits to
`PhaseState`, `PhaseGate`, `HarnessOrchestrator`, or `HarnessPlugin`
semantics. Phase 0's template regression matrix (`tests/test_template_regression_matrix.py`)
must continue to pass unchanged across all 6 packaged templates.

New capabilities are out of scope here: sprint runner logic, evidence gates,
question/answer UX flow, AttentionQueue, cost dashboards — those all live in
Phase 2+.

</domain>

<decisions>
## Implementation Decisions

### Architecture & Layering

- **D-01:** `SprintState` is a NEW independent pydantic v2 model at
  `clawteam/sprint/state.py`. It does NOT replace, subclass, or extend
  `PhaseState`. Layering:
  - `PhaseState` (`harness/phases.py:39`, existing) — harness-run state
    (harness_id, current_phase, team_name, artifacts for a harness session)
  - `SprintContract` (`harness/contracts.py:25`, existing) — a sprint's definition
    (id, title, tasks, success_criteria, wave, depends_on, status)
  - `SprintState` (NEW) — a running sprint's runtime state (sprint_id,
    goal, team, current_phase, phase_history, artifacts, participants,
    pending_question_ids, auto_advance, workspace_branch, created_at)
  `SprintState.sprint_id` may reference a `SprintContract.id` when the sprint
  was spawned from a contract, but the two models are composed, not coupled
  via inheritance.

- **D-02:** `PhaseRegistry` at `clawteam/harness/phase_registry.py` is a pure
  in-memory registry — no disk persistence, no file locking. Plugins populate
  it during `HarnessPlugin.on_register(ctx)` by contributing phases via the
  new optional hooks. `HarnessOrchestrator.__init__(phases=None)` consults the
  registry and constructs `PhaseState.phases` from the plugin contributions.
  When no plugin contributes phases, falls back to `DEFAULT_PHASES` (current
  behavior preserved — required for Phase 0 regression matrix).

### Plugin Hook Contract

- **D-03:** Phase-name namespace is GLOBAL. Two plugins contributing the same
  phase name (including shadowing `DEFAULT_PHASES`) raise `ValueError` at
  registration time, not runtime. No plugin-name prefix / dotted namespace —
  `Phase = str` stays open (current convention at `harness/phases.py:20`).
  This matches ROADMAP SC#2 and follows the spirit of
  `PluginManager._loaded: dict[str, HarnessPlugin]` where plugin names are
  globally unique (`plugins/manager.py:17`).

- **D-04:** The three new optional hooks land on `HarnessPlugin` with empty
  defaults in `clawteam/plugins/base.py`, adjacent to the existing
  `contribute_gates()` and `contribute_prompts()`:
  - `contribute_phases() -> list[Phase]` → `[]`
  - `contribute_phase_roles() -> dict[str, str]` → `{}`
  - `contribute_review_routers() -> list[ReviewRouter]` → `[]`
    (`ReviewRouter` is forward-declared as a Protocol with a `match()` method
    per RFC 001 §4.3b — full interface deferred to Phase 4.)
  The existing `contribute_gates()` / `contribute_prompts()` behavior is
  unchanged. All new methods ship as base-class defaults so existing plugins
  (e.g., `RalphLoopPlugin`) remain valid without modification.

### SprintState Persistence

- **D-05:** `SprintState` persists via `file_locked()` atomic JSON at
  `~/.clawteam/teams/<team>/sprints/<sprint_id>/state.json`, mirroring the
  ClawTeam convention used by `SnapshotManager` (`team/snapshot.py`),
  `team/costs.py`, and `config.py`. `sprint_id` uses the repo's standard ID
  format: `uuid.uuid4().hex[:8]` (matching `SprintContract.id` at
  `contracts.py:28`). Last-write-wins under the file lock.

### InteractionGate & Question/Answer Schema

- **D-06:** `InteractionGate` at `clawteam/harness/interaction_gate.py`
  subclasses the existing abstract `PhaseGate` (`harness/phases.py:56`),
  alongside the existing `ArtifactRequiredGate` and `AllTasksCompleteGate`.
  `check()` returns `(False, "Open questions: N pending")` when any
  `sprint/<sprint_id>/questions/<id>.md` file lacks a sibling
  `sprint/<sprint_id>/answers/<id>.md`, else `(True, "")`.

- **D-07:** Question/answer file ID format follows the ClawTeam UUID
  convention: `questions/<id>.md` and `answers/<id>.md` where
  `id = uuid.uuid4().hex[:8]`. Human-facing slug lives in the question's
  YAML frontmatter (`slug:` field), NOT in the filename. Rationale:
  concurrent agents writing questions never race on sequential integers;
  filenames stay short and stable; AttentionQueue (Phase 7) can render a
  title from frontmatter.slug.

- **D-08:** Question/answer file schema is **pydantic-backed markdown with YAML
  frontmatter**. Shape:

  ```markdown
  ---
  id: a1b2c3d4
  slug: post-layout-question
  type: multi-choice       # multi-choice | freeform | confirm
  created_at: 2026-04-16T10:30:00Z
  sprint_id: 00112233
  phase: plan
  author: designer         # agent role that asked
  choices:                 # present only when type: multi-choice
    - id: A
      label: Yes, user's avatar on every post
    - id: B
      label: No, clean minimal list
  ---

  Should posts have avatars on every card?

  [Optional prose: context, references, what each choice implies.
  This is for the human reader. The parser ignores it.]
  ```

  Answer file mirrors structure:

  ```markdown
  ---
  question_id: a1b2c3d4
  answered_at: 2026-04-16T10:45:00Z
  choice: A                # present when question type is multi-choice
  ---

  [Optional human freeform follow-up — ignored by gate, available to agents.]
  ```

  Phase agents build `Question(...)` / `Answer(...)` pydantic models in memory,
  then call `.to_markdown()` to write the file. The gate parses frontmatter
  only (fast, deterministic). Body prose is human-facing context, never
  machine-required. Matches the ClawTeam pydantic-first convention
  (`SprintContract` + `PhaseState` both use pydantic v2) while keeping the
  human-editing surface gstack `/office-hours`-friendly.

### Claude's Discretion

- Exact pydantic field names inside the `Question` / `Answer` models (beyond
  the required set in D-08) — planner can add `priority`, `urgency`, `tags`
  if clear need emerges at Phase 4 `/office-hours` design time.
- Test fixture layout for the question-schema parse test (SC#5) — planner
  picks a shape consistent with the existing `tests/` layout.
- Whether `ReviewRouter` Protocol definition lives in
  `clawteam/harness/review_router.py` or alongside `phase_registry.py` —
  minor file-organization call; planner picks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project spec layer

- `.planning/PROJECT.md` — project constraints (backwards-compat, upstream-compat,
  additive-only harness changes)
- `.planning/REQUIREMENTS.md` — CORE-01, CORE-02, CORE-04, INT-01, INT-02 (the
  5 REQ-IDs Phase 1 closes)
- `.planning/ROADMAP.md` §Phase 1 — 6 success criteria; §Phase 0 §Deferred Items
  for upstream-PR context

### RFC / design layer (ship artifact)

- `docs/rfcs/001-phase-registry.md` — normative API spec for `PhaseRegistry`,
  three hooks, `SprintState`, `InteractionGate`. §4.3/§4.3a/§4.3b hook
  signatures; §4.4 SprintState shape; §4.5 InteractionGate mechanics;
  §4.6 integration contract; §4.7 compatibility guarantees; §4.8 worked
  software-dev.toml example
- `docs/rfcs/README.md` — RFC index

### Existing ClawTeam code to follow (patterns, not edit targets)

- `clawteam/harness/phases.py` — `PhaseState` (§39), `PhaseGate` (§56),
  `ArtifactRequiredGate` (§64), `AllTasksCompleteGate` (§77), `Phase = str`
  convention (§20), `DEFAULT_PHASES` (§28), `DEFAULT_PHASE_ROLES` (§30)
- `clawteam/harness/contracts.py` — `SprintContract` (§25) for sprint-id
  convention; `SuccessCriterion` (§15) for pydantic shape
- `clawteam/plugins/base.py` — `HarnessPlugin` ABC; `contribute_gates()`
  (§35), `contribute_prompts()` (§39) as the additive-hook pattern to mirror
- `clawteam/plugins/manager.py` — `PluginManager._loaded` (§17) and
  `_instantiate_and_register` (§139) for registration wiring
- `clawteam/team/snapshot.py` — `atomic_write_text`, `SnapshotMeta` pattern
  for file-locked atomic JSON
- `clawteam/fileutil.py` — `file_locked()` helper (required for SC#3
  concurrent-writer test)

### Phase 0 test gates (must stay green)

- `tests/test_template_regression_matrix.py` — 12 parametrized cases covering
  all 6 packaged templates. Phase 1 ships only if these still pass.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `PhaseGate` abstract base (`harness/phases.py:56`) — `InteractionGate`
  subclasses this; same `check(state) -> tuple[bool, str]` signature.
- `ArtifactRequiredGate` (`harness/phases.py:64`) — closest structural analog
  for `InteractionGate`; same shape (store a list of required items, check
  presence in state, return tuple).
- `PluginManager._instantiate_and_register` (`plugins/manager.py:139`) — the
  seam where `PhaseRegistry` gets populated during plugin load. No edits
  needed if `on_register` is the hook point.
- `file_locked()` (`fileutil.py`) — the atomic-persistence primitive;
  `SprintState` write path + concurrent-writer test depend on it.
- `atomic_write_text` + `SnapshotMeta` pattern (`team/snapshot.py:21`,
  `team/snapshot.py:36`) — template for writing the sprint state file.
- `uuid.uuid4().hex[:N]` id-generation convention (`phases.py:42`,
  `contracts.py:28`) — reuse for `sprint_id` and question `id`.

### Established Patterns

- **Pydantic v2 + open `str` for enumerated values** — don't introduce
  `Enum` for `Phase`/`AgentRole`; the codebase deliberately uses `str` to
  stay plugin-extensible (`phases.py:19-20`).
- **Additive plugin hooks as base-class methods with empty defaults** —
  `contribute_gates()` returns `{}`, `contribute_prompts()` returns `""`;
  three new hooks follow the same shape (`plugins/base.py:35`, `:39`).
- **`dict[str, X]` for name-scoped registration with last-write-wins** —
  `PluginManager._loaded`, `PhaseState.phase_roles`, `artifacts`. But
  `PhaseRegistry` is stricter (raise on collision) because phase names are
  a behavior contract, not a lookup convenience.
- **File-locked atomic JSON under `~/.clawteam/teams/<team>/...`** — used by
  snapshots, costs, config; `SprintState` follows.

### Integration Points

- `HarnessOrchestrator.__init__` (`harness/orchestrator.py:24`) — receives
  `phases=None` and consults `PhaseRegistry` to populate `PhaseState.phases`.
  Existing callers that pass an explicit phase list keep working unchanged
  (required for Phase 0 regression matrix).
- `HarnessPlugin.on_register(ctx)` — plugins populate `PhaseRegistry` here.
  `ctx` (`HarnessContext`) may need a `registry` attribute; planner decides
  whether to add it to `HarnessContext` or expose `PhaseRegistry` as a
  module-global singleton. Either is consistent with the codebase.
- `PhaseGate` check invocation is already threaded through `PhaseRunner`;
  `InteractionGate` slots in with no runner changes.

</code_context>

<specifics>
## Specific Ideas

**User correction during discuss-phase** (2026-04-16): when presenting 4 gray
areas, user pushed back with "clawteam 自己没有这些拍板吗?" This triggered a
re-scan of the codebase, which resolved 3 of 4 areas by following existing
ClawTeam conventions (layering, ID format, collision spirit). Only the
question/answer schema (D-08) was genuinely open — user picked pydantic +
markdown hybrid over pure-markdown-convention.

**Pattern lesson for downstream planning:** `SprintState` is a new runtime
sibling, NOT a replacement for `PhaseState`. Plans must preserve the existing
`PhaseState` fields and add `SprintState` as a separate concern. Integration
at the `HarnessOrchestrator` level is through composition (orchestrator holds
an optional `SprintState` when running under a sprint-producing plugin), not
state-model merging.

**Pattern lesson for Phase 4:** the Q/A markdown format (D-08) is the
interface that `/office-hours` state machines, `/design-consultation`,
`/investigate`, and `AttentionQueue` all build on. Lock it now so Phase 4
planner has a stable contract.

</specifics>

<deferred>
## Deferred Ideas

- **`ReviewRouter` full interface** — forward-declared as Protocol with
  `match()` in Phase 1 RFC; full signature (SHA-pinning, multi-signal
  aggregation, decorrelation rules) lands in Phase 4's RFC update.
- **Question `priority`/`urgency`/`tags` fields** — planner may add to
  `Question` pydantic model if Phase 4 `/office-hours` design clearly needs
  them. Not required for Phase 1 base schema.
- **Sprint-level artifact cap (50 KB / 500 KB) and compaction hook** —
  Phase 2 ROADMAP SC#9.
- **Cycle detector, theater-prevention gate, structured response envelope** —
  Phase 2.
- **Sprint CLI (`clawteam sprint start/status/show/list/pause/resume`)** —
  Phase 2 (SC#1 of Phase 2).
- **`InteractionGate` auto-escalation into `AttentionQueue`** — Phase 7 (the
  queue itself doesn't exist yet).

</deferred>

---

*Phase: 01-core-harness-extensions*
*Context gathered: 2026-04-16*
