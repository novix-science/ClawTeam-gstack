---
phase: 4
phase_name: Interactive State Machines, Smart Review Routing & Cross-Agent Verification
phase_slug: interactive-state-machines-smart-review-routing-cross-agent-verification
gathered: 2026-04-21
status: Ready for planning
source: /gsd-discuss-phase --auto (autonomous)
---

# Phase 4: Interactive State Machines, Smart Review Routing & Cross-Agent Verification — Context

<domain>
## Phase Boundary

Activate the runtime surfaces the Phase-3 prompts *pointed at* via `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:` meta-lines, and land the review-phase substrate that keeps parallel reviewers honest. Seven concrete deliverables:

1. **Interactive skill state machines** — Multi-turn state machines for `/office-hours` (pm, per-question), `/design-consultation` (designer, per-dimension), `/investigate` (reviewer, per-hypothesis). Persisted per-skill under `~/.clawteam/teams/<team>/sprints/<id>/skills/<skill>/<role>/state.json` via `file_locked` + `atomic_write_text` (mirrors Phase 2 sprint-state convention).
2. **SmartReviewRouter** — Concrete `GstackReviewRouter` implementing the Phase-1-declared `ReviewRouter` Protocol (`clawteam/harness/review_router.py`); loads rules from `[[template.review.rules]]` in `gstack.toml` (additive TemplateDef extension); SHA-pinned at Review-phase entry; multi-signal path-glob matching; reviewer always participates.
3. **Reviewer decorrelation** — Per-persona decorrelation prompts at `clawteam/templates/gstack/prompts/review/<role>.md` (appended to the main role prompt by the plugin when participating in Review phase); `reviewer` synthesizes peers' reports into a single `review-report.md`; reviewers run in parallel via `asyncio.gather` with isolated sub-conversations (no peer-draft visibility until synthesis).
4. **Cross-agent verification gates** — New `CrossAgentVerificationGate(PhaseGate)` base class subscribes to Phase 2's `EvidenceSchemaRegistry` and runs a second-pass verifier across two peer artifacts (qa verifies engineer's `test-report.md` pytest hashes; reviewer verifies designer's `design-doc.md` answers all 6 forcing questions). Plugin-declared via the existing `contribute_evidence_schemas` hook, extended for verification pairs.
5. **Always-human Ship gate** — New `HumanApprovalGate(InteractionGate)` subclass blocks Test→Ship regardless of `auto_advance: true`; releases only when a signed `ship-approval.md` artifact exists OR user runs `clawteam sprint approve <id> --phase ship`. Attached to Ship phase by `GstackSprintPlugin.contribute_phases` (overrides the default InteractionGate auto-advance semantics for Ship).
6. **`/investigate` auto-freeze** — State machine's Investigate-start action calls `FreezeRegistry.freeze(<module_path>, reason="investigate:<sprint_id>")`; Investigate-complete / Investigate-abandon action calls `unfreeze` with matching reason. Reason field carries the sprint id so `freeze_audit.jsonl` lets operators correlate.
7. **Mid-review-thrash detection** — Review-phase enter records `review_sha = <HEAD>`; if sprint branch HEAD advances during an in-flight review, emits a `mid_review_thrash` event (reuses Phase 2 EventBus); reviewer agent chooses between extending review to new SHA or marking prior review `superseded` (decision written into the review report frontmatter).

**Scope boundary (explicit exclusions):**
- Tool-heavy skills (`/codex`, `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy`) → Phase 5.
- Real `TeamMemoryStore` + `/learn` write path → Phase 6.
- `AttentionQueue` cross-sprint priority queue + cost dashboard → Phase 7.
- Tool-integrated `/investigate` (e.g., shelling out to git-bisect, flamegraph harness) → Phase 5/7. Phase-4 `/investigate` is the state machine + freeze wiring only; hypotheses are text artifacts the reviewer writes.

**Delete invariant (extends Phase 3):** Removing `clawteam/templates/gstack.toml` + `clawteam/plugins/gstack_sprint_plugin.py` + `clawteam/templates/gstack/` + the new `clawteam/harness/cross_agent_verification_gate.py` + `clawteam/harness/human_approval_gate.py` + `clawteam/harness/gstack_review_router.py` must leave the rest of the codebase running unchanged. Every Phase 4 artifact is either inside `templates/gstack/` OR a gstack-specific harness module that existing templates never instantiate. The generic substrate (`CrossAgentVerificationGate`, `HumanApprovalGate`, and the `ReviewRouter` consumption point in the Review-phase orchestrator) is opt-in via plugin contribution — other templates inherit nothing.

</domain>

<decisions>
## Implementation Decisions

### State machine persistence & structure (Area 1)

- **D-01:** **Per-skill state files at `~/.clawteam/teams/<team>/sprints/<id>/skills/<skill>/<role>/state.json`.** Schema is a pydantic v2 model per skill (`OfficeHoursState`, `DesignConsultationState`, `InvestigateState`) under `clawteam/templates/gstack/skills/<skill>/state.py`. Persisted via `file_locked()` + `atomic_write_text` (the Phase 2 convention). SprintState is **not** inflated with skill session fields — those remain sprint-scoped sub-dirs.
  **Why:** Phase 2 already proved the `sprints/<id>/<sub>/` layout works under concurrent writes (questions/, answers/, artifacts/, freeze.json all live there). Extending SprintState with skill_sessions risks schema churn every time a new interactive skill ships. Per-skill pydantic models let each skill author own its schema, matching the "delete gstack plugin and the rest still works" invariant.

- **D-02:** **State machines are implemented as pydantic-enum-driven transition tables, not as asyncio coroutines.** Each state machine class exposes `current_state: Literal[...]`, `history: list[Transition]`, and `handle(event: SkillEvent) -> StateTransitionResult`. The plugin's skill handler loads state → calls `handle()` → persists → emits appropriate turn envelope.
  **Why:** Survives full `HarnessOrchestrator` restart via plain JSON persistence (CORE-07 compatibility). Coroutine-driven state machines bind to the event loop and lose state on restart. Transition-table style is also the canonical gstack skill shape (upstream `/office-hours` reads as a per-question table).

- **D-03:** **State machines run on the same turn cadence as the enclosing phase.** No dedicated "skill event loop". A `SprintConductor.advance_phase` turn for pm during Think phase with an active `/office-hours` session: load state, process one envelope of user input, advance state, persist, write next question artifact OR mark complete.
  **Why:** Reuses existing conductor dispatch machinery. No new concurrency primitive. Each turn is a discrete state-machine step — matches the gate + envelope + evidence pattern from Phase 2.

### SmartReviewRouter format & wiring (Area 2)

- **D-04:** **`[[template.review.rules]]` TOML array in `gstack.toml`** — additive extension to `TemplateDef`. Each rule is `{ pattern = "glob", reviewers = ["role-name"], signal = "ui|api|crypto|security" }`. Rules evaluated in declared order; first-match semantics WITH accumulation (a path matching both `src/components/*.tsx` and `src/auth/**` adds both designer AND security to the reviewer set). `reviewer` role is always appended unconditionally (SPRINT-03 floor + QUALITY-13 decorrelation anchor).
  **Why:** Matches Phase 3 D-06 grep-friendly + additive-TOML convention. Non-Python users can tune routing without code edits. The `signal` field is optional metadata carried through to the reviewer's frontmatter so panels can measure "how often does a crypto-signal diff catch a security bug" in post-hoc analysis.

- **D-05:** **SHA-pinning via `SprintState.review_sha` field** — set at Review-phase entry from `SprintState.workspace_branch` HEAD via `subprocess.run(["git", "rev-parse", "HEAD"], ...)`. The router's `match(diff_paths, state)` call resolves `diff_paths` from `git diff --name-only <review_sha>..<review_sha>` fixture list (i.e., the diff AS OF review_sha, not HEAD). If HEAD advances mid-review, Phase 2's post-turn hook emits a `mid_review_thrash(sprint_id, review_sha, new_sha, reviewer_role)` event on the EventBus; the active reviewer chooses in its next turn to either re-pin or supersede.
  **Why:** QUALITY-09 mandates SHA-pinning at routing decision time. Re-deriving the diff from `review_sha` each turn prevents silent-drift; explicit event on thrash lets reviewers react rather than receive stale inputs.

- **D-06:** **`GstackReviewRouter` loads `[[template.review.rules]]` at plugin load** and caches the compiled rules per team. The router is contributed via `GstackSprintPlugin.contribute_review_routers()` (the Phase-1-declared hook). Review-phase orchestration (lives in Phase 4's `clawteam/sprint/review_phase.py` new file) calls `for router in plugin_manager.review_routers: router.match(diff, state)` and unions results with the always-reviewer floor.
  **Why:** Phase 1 already locked the `ReviewRouter` Protocol (`clawteam/harness/review_router.py`) and the `contribute_review_routers` hook. Phase 4 ships the consumer (the Review-phase dispatch path) and the concrete gstack router. No protocol churn.

### Reviewer decorrelation strategy (Area 3)

- **D-07:** **Per-persona decorrelation prompts live at `clawteam/templates/gstack/prompts/review/<role>.md`** (× 4 initially — reviewer, designer, security, dx-lead). The plugin's `contribute_prompts` hook, when phase="review" AND role=<reviewer_role>, returns `<role>.md` (main) + `review/<role>.md` (decorrelation supplement). Main prompt is unchanged; decorrelation is the appended rubric-anchor override.
  **Why:** Matches Phase 3 D-06 prompt-file pattern (grep-friendly, per-role .md files, 4 KB budget). Separate files keep the decorrelation rubric independently editable without risking main-prompt collateral. Future personas (e.g., `dba` added in v1.1) add one file, don't touch the rest.

- **D-08:** **Parallel reviewers run via `asyncio.gather`** in the Review-phase dispatch. Each reviewer's sub-conversation is isolated — no shared scratch, no peer-draft visibility, only the pinned-SHA diff + decorrelation-augmented prompt. The Phase-2 `SprintConductor` semaphore caps (`max_tasks_per_agent`) still apply; the gather body calls existing per-agent spawn paths. After all reviewers return, the `reviewer` (staff-eng) role runs sequentially with all peer reports in its context and writes the aggregated `review-report.md`.
  **Why:** QUALITY-13 requires diverge-not-mirror findings. Real concurrency + prompt isolation is the only way to get honest decorrelation; sequential-with-prompt-isolation leaks via residual conversation state. Aggregation happens AFTER all peers complete so the synthesizer has the complete set.

- **D-09:** **Agreement-rate > 90% on parallel reviewers triggers a `sycophancy_cascade_detected` event** on the EventBus. Computed as (# identical finding-severity ratings across reviewers) / (# total findings on the most-verbose reviewer's report). Threshold + window configurable via `[template.review]` `sycophancy_threshold = 0.9`. Event is advisory — does not block the phase; logs for humans to review in `clawteam attend --summary` (Phase 7 surfaces; Phase 4 emits the event).
  **Why:** PITFALLS #13 mitigation. Advisory-not-blocking because a high agreement rate can be legitimate (all reviewers unanimously see a critical bug). Logging lets operators audit patterns over time without false-positive noise in CI.

### Cross-agent verification gates (Area 4)

- **D-10:** **New `CrossAgentVerificationGate(PhaseGate)` at `clawteam/harness/cross_agent_verification_gate.py`.** Constructor: `(phase: str, source_artifact: str, target_artifact: str, verifier: Callable[[SourceArtifact, TargetArtifact], tuple[bool, str]])`. `check(state)` loads both artifacts via Phase 2's `EvidenceSchemaRegistry.parse`, runs `verifier`, returns `(bool, reason)`.
  **Why:** Mirrors `EvidenceGate` shape (same Phase 2 author). Reusable by non-gstack plugins that want cross-artifact gates. Verifier is a small pure function per pair — testable in isolation.

- **D-11:** **Two initial verifier functions ship in `clawteam/templates/gstack/verifiers/`:**
  - `verify_test_report_matches_engineer_output(test_report, engineer_diff_summary) -> (bool, reason)` — qa's pytest-output-hash assertions must reference at least one test file modified/added in engineer's diff.
  - `verify_design_doc_covers_forcing_questions(design_doc, office_hours_answers) -> (bool, reason)` — designer's design-doc must contain structured answers mapping to all 6 pm/`office-hours` forcing questions (presence check on question ids, not prose matching).
  **Why:** These are the two pair-ups SPRINT-04 + QUALITY-07 + QUALITY-13 cross-verification explicitly name. Additional verifiers can be added per skill in future phases without harness churn.

- **D-12:** **Verification gates are plugin-contributed via a new optional `HarnessPlugin.contribute_verification_pairs()` hook** that returns `list[VerificationPair]` (phase + source_artifact + target_artifact + verifier_fn path). `PluginManager` wires these into the phase's gate list at plugin load — same pattern as `contribute_phases` / `contribute_evidence_schemas`. Hook is optional, default `[]`, no existing plugin breaks.
  **Why:** Additive extension; keeps verification wiring out of the plugin's contribute_phases method (which should remain pure phase registration). Matches the one-hook-per-concern convention of Phase 1/2.

### Always-human Ship gate (Area 5)

- **D-13:** **New `HumanApprovalGate(InteractionGate)` at `clawteam/harness/human_approval_gate.py`.** Subclass of `InteractionGate` that ALSO requires a `ship-approval.md` artifact with `approved_by` + `approved_at` + `sha_at_approval` frontmatter fields. `check(state)`: first delegate to `InteractionGate.check` for standard question-answer pattern; THEN additionally check for `ship-approval.md` presence + field completeness; return `(False, ...)` if either check fails. Ignores `SprintState.auto_advance = True` (override semantic).
  **Why:** SPRINT-05 mandate (production blast radius = always human). InteractionGate's `auto_advance` escape hatch is exactly what this gate must bypass; subclassing cleanly inherits the question-answer plumbing while adding the explicit-approval requirement.

- **D-14:** **`clawteam sprint approve <id> --phase ship` CLI command writes the `ship-approval.md`** with current git user as `approved_by`, current UTC timestamp as `approved_at`, current `SprintState.review_sha` (or HEAD if unset) as `sha_at_approval`. If `--no-sign` is absent and git is configured for signing, signs the commit creating the approval artifact via `git commit -S`. JSON-mode flag (`--json`) prints the written frontmatter as JSON.
  **Why:** Gives humans a scriptable surface in addition to editing the artifact directly. Sha-at-approval is pinned so a post-approval HEAD advance triggers a re-approval requirement (the ship EvidenceGate sees `sha_at_approval != review_sha` and re-opens).

### `/investigate` auto-freeze (Area 6)

- **D-15:** **`InvestigateState.on_enter(module_path)` calls `FreezeRegistry.freeze(module_path, reason=f"investigate:{sprint_id}:{hypothesis_id}")`.** `on_complete` / `on_abandon` call `FreezeRegistry.unfreeze(module_path, reason=<matching>)`. Reason field carries sprint + hypothesis id so `freeze_audit.jsonl` is correlatable post-hoc.
  **Why:** Reuses Phase 2's freeze_registry API + audit trail directly. No new persistence. The reason string is structured (`investigate:<sprint>:<hypothesis>`) so operators can grep "all freezes attributable to investigate skill".

- **D-16:** **Module-path resolution is hypothesis-provided, not auto-derived.** `/investigate` skill's first state (`hypothesis_declared`) requires the reviewer to state a module path explicitly (e.g., `clawteam/sprint/conductor.py` or `src/auth/**/*.py`). No regex-from-stack-trace extraction — too fragile; one wrong wildcard freezes the whole tree. The skill validates the path exists + is within the sprint's workspace_branch root before freezing.
  **Why:** Explicit is better than implicit for safety-adjacent state. The reviewer declares scope; the state machine enforces the freeze. Matches PROJECT.md "pipe to human, never guess destructive scope".

### Verification stringency (Area 7)

- **D-17:** **Golden-trace fidelity = Strategy B+ (markdown-derived fixtures WITH turn-count + transition-graph assertions).** Implementation:
  1. Plan-prep task WebFetches upstream gstack `/office-hours`, `/plan-design-review`, `/investigate`, `/review` skill markdown (already committed per Phase 3 D-08 under `tests/fixtures/gstack_skills/`).
  2. Extended golden tests assert **(a)** turn-count per session (pm `/office-hours` = 6 + 1 summary; designer `/design-consultation` = 7 dimensions × 1 turn + 1 summary; reviewer `/investigate` = ≤ 3 hypothesis iterations per policy); **(b)** transition-graph shape matches the per-skill fixture JSON at `tests/fixtures/gstack_state_machines/<skill>.transitions.json`.
  3. **No Strategy A (sandbox-gstack) required.** Transition graphs are deterministic from the state-machine code; turn counts are fixed by the skill's design. Both assertions are cheap and deterministic.
  **Why:** Phase 3 D-08 locked Strategy B at the content layer; Phase 4's state-machine shape is similarly assertable without live runs. Transition-graph JSON fixtures are 10-50 lines each — trivial to hand-author and review, no WebFetch churn at test time.

- **D-18:** **Golden tests assert `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:` lines are either (a) still present in role prompts with an updated "Phase 4 runtime at `<path>`" suffix, OR (b) removed because Phase 4 now owns the runtime.** Chosen rule: **(b)** — Phase 4 is the runtime; the meta-instructions served their Phase-3 purpose of marking hand-off points. Role prompts re-written at plan time to remove the deferred markers; golden tests assert BOTH that the markers are gone AND that the corresponding skill state machine + test exist.
  **Why:** Clean state transition. Leaving both markers AND runtime creates ambiguity about which is canonical; golden-test enforcement that markers are gone ensures downstream confusion can't happen.

### Mid-review-thrash & sycophancy-cascade events (Area 8)

- **D-19:** **`mid_review_thrash` event payload:** `{sprint_id, review_sha, new_sha, reviewer_roles_active: [roles], diff_paths_added: [paths], diff_paths_removed: [paths]}`. Emitted by a post-turn hook in Review-phase dispatch that compares `SprintState.review_sha` to `git rev-parse HEAD` at turn boundary. Phase 7's `clawteam attend --summary` displays these; Phase 4 just emits + logs.
  **Why:** Payload gives reviewers the info they need to decide re-pin vs supersede. Phase 7's UX consumer doesn't dictate Phase 4's emission — the event is fully informative at wire-level.

- **D-20:** **`sycophancy_cascade_detected` event is computed per sprint per review round**, not globally. Window = one sprint's Review phase. Re-running Review phase after gap closure opens a new window (no carryover). Threshold default 0.9 is configurable via `gstack.toml [template.review] sycophancy_threshold`.
  **Why:** Scoping per-sprint-per-round prevents cumulative false positives from long-running teams. Per-round reset matches how reviewers actually load context (fresh each round).

### Claude's Discretion (planner picks; no need to ask user)

- Concrete pydantic field names within `OfficeHoursState`, `DesignConsultationState`, `InvestigateState`. State machines' transition tables are expressible by the planner from the fixture JSONs; field names match the fixture keys verbatim.
- Internal structure of `clawteam/templates/gstack/prompts/review/<role>.md` files — decorrelation rubric headings, ordering of persona-anchor / peer-visibility / synthesis-expectations. Main-prompt 4 KB budget (Phase 3 D-14) does NOT stack on review/<role>.md; decorrelation files get a separate 2 KB budget.
- Exact JSON payload key names for `mid_review_thrash` / `sycophancy_cascade_detected` events (D-19, D-20 sketch; planner may refine).
- Wave structure + parallelism of plans (planner determines from file dependencies).
- Whether to ship cross-agent verification as one plan (shared `CrossAgentVerificationGate` + both verifiers) or split per verifier.
- Whether `/investigate` state machine ships as one plan or splits declaration-vs-freeze-wiring-vs-transition-logic into two.
- Concrete `asyncio.gather` wiring shape (error propagation, cancellation on one failure, timeout policy) — standard Python patterns apply.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents (planner, plan-checker, executor) MUST read these before planning or implementing.**

### Phase 4 deliverable specifications (load-bearing)

- `.planning/ROADMAP.md` §"Phase 4: Interactive State Machines, Smart Review Routing & Cross-Agent Verification" (lines 182-213) — phase goal, 7 success criteria, requirements list (SPRINT-03/04/05, SAFETY-05, QUALITY-07/09/13), canonical refs.
- `.planning/REQUIREMENTS.md` §SPRINT/SAFETY/QUALITY — SPRINT-03, SPRINT-04, SPRINT-05, SAFETY-05, QUALITY-07, QUALITY-09, QUALITY-13 verbatim.

### Project-locked context

- `.planning/PROJECT.md` §"Key Decisions" row 6 (parallel reviewers + reviewer aggregates), Constraints (Python 3.10+, no new required runtime deps, persistence under `get_data_dir()`).

### Upstream Phase 3 substrate (what Phase 4 extends)

- `.planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md` — Phase 3 D-06 (role prompts as separate .md files), D-07 (envelope_personas.py location), D-14 (4 KB prompt budget); `/office-hours`, `/design-consultation`, `/investigate` deferred to Phase 4 per RESEARCH §Pure-Rubric vs Interactive split.
- `clawteam/templates/gstack/prompts/pm.md` (line 18 `INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 multi-turn`), `designer.md` (line 17 `/design-consultation per-dimension dialogue`), `reviewer.md` (line 40 `/investigate per-hypothesis state machine`, line 47 `SHA-PIN-DEFERRED: At review start, record HEAD SHA`).
- `clawteam/plugins/gstack_sprint_plugin.py` — Phase 3 plugin that Phase 4 extends with `contribute_review_routers` + `contribute_verification_pairs` implementations (NOT a new plugin file — same one cohesive plugin, per Phase 3 D-04).
- `clawteam/templates/gstack/envelope_personas.py` — Phase 3 per-persona envelope subclasses. Review decorrelation prompts emit into these envelopes (no new envelope code).

### Phase 1 substrate (protocol hooks Phase 4 consumes)

- `clawteam/harness/review_router.py` (entire file) — `ReviewRouter` Protocol declared by Phase 1 RFC 001 §4.3b. Phase 4 ships the first concrete implementation (`GstackReviewRouter`) and wires consumption in Review-phase orchestration.
- `clawteam/plugins/base.py` — `HarnessPlugin.contribute_review_routers()` hook declared by Phase 1; Phase 4 also ADDS new optional `contribute_verification_pairs()` (default empty list; no existing plugin breaks).
- `docs/rfcs/001-phase-registry.md` §4.3b — locked contract for ReviewRouter Protocol.

### Phase 2 substrate (gate + registry + persistence primitives Phase 4 reuses)

- `clawteam/harness/interaction_gate.py` — Phase 4's `HumanApprovalGate` subclasses this.
- `clawteam/harness/evidence_schemas.py` — Phase 4's cross-agent verification parses artifacts via this registry; does NOT modify it.
- `clawteam/harness/freeze_registry.py` — `/investigate` state machine calls `FreezeRegistry.freeze/unfreeze` unchanged (append-only `freeze_audit.jsonl` carries the investigate reason string).
- `clawteam/sprint/state.py` — Phase 4 ADDS one optional field: `review_sha: str | None = None`. Existing fields unchanged. Pydantic ignores extras so the additive change is backwards-compatible.
- `clawteam/sprint/conductor.py` — Phase 4 extends `SprintConductor` with Review-phase dispatch: runs router, gathers parallel reviewers, runs synthesizer. No schema changes.
- `clawteam/harness/forced_progress_gate.py` — referenced pattern for gate subclassing; Phase 4's `CrossAgentVerificationGate` follows similar shape.
- `.planning/phases/02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention/02-CONTEXT.md` — D-01..D-05 EvidenceGate shape, D-06 TurnEnvelope required fields, D-11..D-13 FreezeRegistry, D-23 auto_advance semantics Phase 4's HumanApprovalGate overrides.

### Upstream gstack source (WebFetch fixtures committed under tests/fixtures/gstack_skills/ per Phase 3 D-08)

- `tests/fixtures/gstack_skills/office-hours.md` — 6 forcing questions + per-question branching structure that drives the pm state-machine transition table.
- `tests/fixtures/gstack_skills/plan-design-review.md`, `design-review.md` — 7 rubric dimensions driving designer `/design-consultation` per-dimension transitions.
- `tests/fixtures/gstack_skills/review.md` — reviewer rubric + `/investigate` halt-after-3-failed-hypotheses policy.

### Research foundation

- `.planning/research/ARCHITECTURE.md` Pattern 6 (SmartReviewRouter rules-first routing + reviewer decorrelation).
- `.planning/research/PITFALLS.md` Pitfall 7 (interactive state machines — explicit ship-blocker this phase mitigates), Pitfall 9 (review routing SHA-pinning + multi-signal), Pitfall 13 (sycophancy cascade decorrelation); reinforces Pitfall 8 (gate gaming) via cross-agent verification.
- `.planning/research/SUMMARY.md` §Phase 3 research-flag rationale applies here (the HIGH research-flag work Phase 3 *partially* absorbed by landing pure-rubric content; Phase 4 absorbs the rest).

### Related Phase 3 verification fixtures (Phase 4 extends with state-machine transitions)

- `tests/fixtures/gstack_state_machines/` — **NEW directory Phase 4 creates.** Per-skill `*.transitions.json` fixtures (see D-17). Committed to repo for reproducibility; 10-50 lines per file.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets (Phase 4 uses, never reinvents)

- `clawteam/harness/interaction_gate.py` `InteractionGate` — `HumanApprovalGate` subclasses. Path-safety guarantees (canonicalization, data-dir exclusion) inherited.
- `clawteam/harness/freeze_registry.py` `FreezeRegistry` singleton with `file_locked` JSON persistence + `freeze_audit.jsonl` append-only — `/investigate` calls `freeze(reason=...)` / `unfreeze(reason=...)` unchanged.
- `clawteam/harness/evidence_schemas.py` `EvidenceSchemaRegistry` — cross-agent verification parses artifacts via registered pydantic schemas; does NOT register new schemas (those are Phase 3's 6 artifact types).
- `clawteam/harness/review_router.py` `ReviewRouter` Protocol — Phase 1 hook point. Phase 4 is the first concrete consumer.
- `clawteam/plugins/base.py` `HarnessPlugin` — extend with `contribute_verification_pairs` optional hook (default `[]`). Mirrors Phase 2's `contribute_evidence_schemas` addition.
- `clawteam/plugins/gstack_sprint_plugin.py` — extend with `contribute_review_routers` + `contribute_verification_pairs` methods. No new plugin file — single cohesive plugin per Phase 3 D-04.
- `clawteam/sprint/state.py` `SprintState` — additively add `review_sha: str | None = None` field. `atomic_write_text` + `file_locked` persistence unchanged.
- `clawteam/sprint/conductor.py` `SprintConductor` — Phase 4 extends Review-phase dispatch (new `_dispatch_review_phase` method that runs router → asyncio.gather reviewers → synthesizer). Think/Plan/Build/Test/Ship/Reflect dispatch paths unchanged.
- `clawteam/team/envelope.py` `TurnEnvelope` + Phase 3's 11 per-persona subclasses — emit augmented envelopes from state machines; no new envelope types.
- `clawteam/templates/gstack/prompts/` — add `review/<role>.md` files (× 4). Existing 11 main prompts UNCHANGED except Phase-3 meta-instruction lines removed (D-18).
- `clawteam/events/bus.py` (existing EventBus) — emit `mid_review_thrash` + `sycophancy_cascade_detected` events. No new event infrastructure.

### Established Patterns (constrain Phase 4 implementation)

- **Plugin hooks are optional + additive** — any new hook on `HarnessPlugin` (`contribute_verification_pairs`) defaults empty. Existing plugins break ZERO.
- **Per-agent .md prompt files** — Phase 3 D-06 pattern. Decorrelation files under `prompts/review/<role>.md` follow the same convention.
- **State persisted via `file_locked` + `atomic_write_text`** — never direct `open().write()`. Phase 2 lessons apply: concurrent writers serialize; last-write-wins; no torn writes.
- **Phase as open string** — `clawteam/harness/phases.py:19`. Phase 4's Review-phase dispatch doesn't modify the phase enum; it plugs into existing `review` phase name.
- **Single cohesive plugin file** — Phase 3 D-04 convention. `GstackSprintPlugin` extended, NOT split. New hook methods added to the existing plugin class.
- **Delete invariant maintained** — every new gstack-specific file lives inside `clawteam/templates/gstack/` OR is prefixed by `gstack_` (e.g., `gstack_review_router.py`). Generic harness additions (`cross_agent_verification_gate.py`, `human_approval_gate.py`) are used ONLY by plugins that opt-in via contribution hooks.
- **Additive TemplateDef extension** — `[[template.review.rules]]` adds an optional field with empty default. Existing 6 templates unaffected.
- **Persistence under `get_data_dir()`** — new per-skill state files under `<data_dir>/teams/<team>/sprints/<id>/skills/<skill>/<role>/state.json`. NEVER in-project.

### Integration Points

- `GstackSprintPlugin.contribute_review_routers()` → returns `[GstackReviewRouter(template=self.template)]`.
- `GstackSprintPlugin.contribute_verification_pairs()` → returns the 2 initial pairs (test-report ↔ engineer-diff, design-doc ↔ office-hours-answers).
- `GstackSprintPlugin.contribute_phases()` attaches `HumanApprovalGate` to the Ship phase's gate list (the same method already attaches other Phase 3 gates).
- `clawteam/sprint/conductor.py::_dispatch_review_phase` NEW method — calls `plugin_manager.review_routers` × `match(diff, state)`, unions with floor, `asyncio.gather`s per-reviewer tasks, then sequentially runs the synthesizer.
- `clawteam/sprint/conductor.py::_dispatch_ship_phase` — unchanged structurally; `HumanApprovalGate` sits in the phase's gate list and blocks the normal advance path.
- `clawteam/cli/sprint.py::approve` NEW subcommand — writes `ship-approval.md` via existing Typer + `file_locked` machinery.
- State machines load on turn entry via `GstackSprintPlugin.on_turn(role, phase, state)` (new hook path if needed; otherwise handled inside `contribute_prompts` + role handler).

</code_context>

<specifics>
## Specific Ideas

- **Decorrelation anchors, per persona (pin these in `prompts/review/<role>.md` verbatim):**
  - reviewer: "You are staff-eng cross-cutting. Focus on production-bug patterns, data integrity, and cross-module coupling. Ignore prose style."
  - security: "You are threat-model-first. Apply STRIPE + OWASP. Exclude the 22 `/cso` false-positives declared in your main prompt. Only flag findings with confidence ≥ 8/10."
  - designer: "You are rubric-first. Score against all 7 `/plan-design-review` dimensions. Flag AI-slop patterns (stock iconography, generic gradients, inconsistent spacing)."
  - dx-lead: "You are friction-first. Trace the TTHW (time-to-hello-world) of each user-facing change. Flag any API surface that adds steps without removing steps."

- **`ship-approval.md` frontmatter schema (canonical):**
  ```yaml
  artifact_type: ship_approval
  approved_by: <git-user-name>
  approved_at: <ISO-8601 UTC>
  sha_at_approval: <40-char git SHA>
  approval_notes: <freeform, optional>
  ```
  EvidenceGate on Ship phase validates `approved_by` non-empty, `approved_at` parseable ISO, `sha_at_approval` matches `SprintState.review_sha` (or HEAD at write time).

- **Per-skill state.json shape (sketch — planner refines):**
  ```json
  {
    "skill": "office-hours",
    "role": "pm",
    "sprint_id": "<id>",
    "current_state": "question_2_answered",
    "history": [
      {"from": "start", "to": "question_1_asked", "ts": "...", "turn": 3},
      ...
    ],
    "pending_question_id": "Q3",
    "completed_at": null
  }
  ```

- **`[[template.review.rules]]` TOML shape (canonical):**
  ```toml
  [template.review]
  sycophancy_threshold = 0.9

  [[template.review.rules]]
  pattern = "src/components/**/*.tsx"
  reviewers = ["designer"]
  signal = "ui"

  [[template.review.rules]]
  pattern = "src/auth/**"
  reviewers = ["security"]
  signal = "crypto"

  [[template.review.rules]]
  pattern = "**/crypto/**"
  reviewers = ["security"]
  signal = "crypto"

  [[template.review.rules]]
  pattern = "app/api/**"
  reviewers = ["dx-lead"]
  signal = "api"

  [[template.review.rules]]
  pattern = "package.json"
  reviewers = ["dx-lead"]
  signal = "api"
  ```

- **`tests/fixtures/gstack_state_machines/office-hours.transitions.json` (sketch):**
  ```json
  {
    "initial_state": "start",
    "final_states": ["summary_written", "abandoned"],
    "transitions": [
      {"from": "start", "event": "begin", "to": "question_1_asked"},
      {"from": "question_1_asked", "event": "answered", "to": "question_1_answered"},
      ...
    ],
    "turn_budget": 13
  }
  ```

- **Adversarial test diffs for SPRINT-03 routing (fixtures under `tests/fixtures/review_routing/`):**
  - `renamed_ui_component.diff` (renamed file — designer still pulled).
  - `crypto_test_file.diff` (test file that imports `crypto` — security pulled).
  - `whitespace_only.diff` (no reviewers beyond floor).
  - `package_json_dep_bump.diff` (dx-lead pulled).
  - `auth_middleware_rewrite.diff` (security pulled).
  - `cross_cutting_refactor.diff` (multiple rule matches — union of reviewers).
  - `mixed_ui_and_api.diff` (designer + dx-lead + reviewer-floor).
  - `generated_migration.diff` (reviewer-floor only).

</specifics>

<deferred>
## Deferred Ideas

### To Phase 5 (tool-heavy skills)
- `/codex` cross-model second opinion invocable by engineer/reviewer — Phase 5.
- `/ship`, `/land-and-deploy`, `/document-release` ship pipeline — Phase 5 (Phase 4's `HumanApprovalGate` is the gate; Phase 5 writes the shipper.md stub → production ship-notes.md).
- `/canary`, `/benchmark`, `/setup-deploy` SRE pipeline — Phase 5.
- Any tool-integrated form of `/investigate` (git-bisect driver, flamegraph harness, bin-search over known-good commits) — Phase 5 or v1.1.

### To Phase 6 (browser pipeline + design-shotgun + real /learn)
- Designer's `/design-shotgun` + `/design-html` state machines — Phase 6 (Phase 4's `/design-consultation` is the per-dimension consult, NOT the mockup pipeline).
- `TeamMemoryStore` real implementation replacing the Phase-3 `_phase6_pending/` placeholder — Phase 6.
- `/learn` skill backfill scanner.

### To Phase 7 (parallel sprints + cost + attention)
- `AttentionQueue` cross-sprint pending-questions + `clawteam attend` CLI + `--summary` digest view — Phase 7.
- Cost dashboard displaying `mid_review_thrash` + `sycophancy_cascade_detected` events in the team dashboard — Phase 7.
- Multi-sprint parallel reviewer semaphore tuning (Phase 4 uses Phase 2 per-agent caps; Phase 7 adds cross-sprint orchestration).

### To post-v1
- **Strategy A golden traces** (sandbox-gstack + recorded transcripts) — only revisit if Phase 4 state-machine fidelity proves insufficient. Current signal is Strategy B+ (markdown + transition graphs) is sufficient per D-17.
- **Full natural-language diff classification** for `SmartReviewRouter` (e.g., ML-based "this diff is architectural, pull eng-mgr"). Current Phase 4 is path-glob rule-based; ML classification is v1.1/v2.
- **Reviewer "panel" dynamic composition** (e.g., "spawn 3 designer instances on a UI-heavy diff for triangulation"). Phase 4 runs one reviewer per role; panel-size > 1 is v1.x.
- **Promotion of `CrossAgentVerificationGate` and `HumanApprovalGate` upstream** — currently ships in `clawteam/harness/` but used only via plugin opt-in. If a second template (hedge-fund) adopts cross-verification, the gate is already generic; nothing to promote. The gstack-specific `GstackReviewRouter` stays fork-local.
- **Human-language "why the reviewer's decorrelation is working" trust signals** in `team show` — measure divergence rate over time, surface as a Team Quality tile.

### Reviewed Todos (not folded)
None — `.planning/todos/pending/` is empty.

</deferred>

<plan_prep_verifications>
## Plan-Prep Verification Tasks (must run BEFORE main planning)

These are grep / measurement tasks the planner must include in a Wave-0 prep set so unverified assumptions don't compound into wrong plans:

| ID | Verification | Action if fails |
|----|--------------|-----------------|
| A1 | `clawteam/harness/review_router.py::ReviewRouter` Protocol method signature is `match(diff_paths, state) -> list[str]` | If signature drifted, planner updates GstackReviewRouter impl AND adds a 1-line harness-side adapter. |
| A2 | `clawteam/plugins/base.py::HarnessPlugin` currently lacks `contribute_verification_pairs` | Planner ADDs the optional hook (default `[]`); existing plugins unchanged. |
| A3 | `clawteam/sprint/state.py::SprintState` pydantic model uses `extra="ignore"` or `model_config = {"extra": "ignore"}` | If `extra="forbid"`, planner switches the config to ignore before adding `review_sha`. |
| A4 | `clawteam/sprint/conductor.py` has a Review-phase dispatch path that can be extended or replaced | If no Review dispatch exists, planner creates `_dispatch_review_phase` method; if exists, extends. |
| A5 | `clawteam/templates/gstack.toml` parser accepts unknown `[[template.review.rules]]` entries under pydantic `extra="ignore"` | Already verified Phase 3 D-04; re-confirm no regression since. |
| A6 | Phase 3's meta-instruction lines (`INTERACTIVE-RUNTIME-DEFERRED:`, `SHA-PIN-DEFERRED:`) grep-count in `clawteam/templates/gstack/prompts/*.md` — baseline before D-18 removal | Record baseline (should be 4 lines total); D-18 verification asserts count drops to 0 after Phase 4 landing. |
| A7 | `clawteam/events/bus.py` EventBus accepts arbitrary string event names with dict payloads | Already used by Phase 2 (cycle_detector, forced_progress); re-confirm `emit(name, payload)` is the API. |
| A8 | `SprintConductor.advance_phase` accepts an `actor` parameter (Phase 3 D-10 verified it existed or planner added) | Re-confirm — Phase 4 does not modify this; just uses it for Ship-phase `HumanApprovalGate` approval attribution. |

</plan_prep_verifications>

---

*Phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification*
*Context gathered: 2026-04-21 via /gsd-discuss-phase --auto (autonomous run)*
*Decisions: D-01 through D-20 (20 locked); plus 8 plan-prep verification tasks*
*Next: /gsd-plan-phase 4*
