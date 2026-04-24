---
phase: 4
phase_name: Interactive State Machines, Smart Review Routing & Cross-Agent Verification
phase_slug: interactive-state-machines-smart-review-routing-cross-agent-verification
researched: 2026-04-21
domain: Multi-turn state machines over an existing sprint conductor; CODEOWNERS-style diff routing; reviewer decorrelation via decorrelation prompts; cross-artifact verification gates; always-human ship gate
confidence: HIGH
status: Ready for planning
---

# Phase 4: Interactive State Machines, Smart Review Routing & Cross-Agent Verification — Research

## Summary

Phase 4 activates runtime surfaces that Phase 3 explicitly declared as deferred via `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:` meta-instructions in the pm/designer/reviewer role prompts. 80% of the substrate Phase 4 needs already exists: `ReviewRouter` Protocol + `contribute_review_routers` hook (Phase 1), `InteractionGate` + `FreezeRegistry` + `EvidenceSchemaRegistry` + `file_locked`/`atomic_write_text` persistence + EventBus + 11 per-persona envelopes + 6 pydantic artifact schemas (Phase 2/3), and `force_interactive_phases=["ship"]` reservation already wired into `SprintConductor.__init__` (verified at `clawteam/sprint/conductor.py:247`).

Seven concrete deliverables per CONTEXT §domain: (1) three state-machine classes persisting JSON under a per-skill sub-tree; (2) `GstackReviewRouter` reading `[[template.review.rules]]` from `gstack.toml`; (3) `prompts/review/<role>.md` decorrelation supplements emitted in parallel via `asyncio.gather`; (4) `CrossAgentVerificationGate(PhaseGate)` + two verifier fns + new plugin hook `contribute_verification_pairs`; (5) `HumanApprovalGate(InteractionGate)` overriding auto-advance for Ship; (6) `/investigate` auto-freeze wiring via the existing `FreezeRegistry.freeze/unfreeze` API; (7) `mid_review_thrash` + `sycophancy_cascade_detected` event emission on the existing synchronous EventBus.

**Primary recommendation:** Ship the substrate (state-machine base, `GstackReviewRouter`, `CrossAgentVerificationGate`, `HumanApprovalGate`, `contribute_verification_pairs` hook) as one tight Wave 1. Then land one state machine per plan in Wave 2 (three plans, one per skill). Wave 3 lands the Review-phase dispatch in `SprintConductor` (D-06/D-08) plus the two verifier functions. Wave 4 lands the `clawteam sprint approve` CLI + golden tests. D-18 prompt rewrite (remove `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:` lines) lands last so the new runtime is already proven before the markers come down.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**State machine persistence & structure (Area 1):**
- **D-01:** Per-skill state files at `~/.clawteam/teams/<team>/sprints/<id>/skills/<skill>/<role>/state.json`. Schema is a pydantic v2 model per skill (`OfficeHoursState`, `DesignConsultationState`, `InvestigateState`) under `clawteam/templates/gstack/skills/<skill>/state.py`. Persisted via `file_locked()` + `atomic_write_text`. SprintState is NOT inflated with skill session fields.
- **D-02:** State machines are implemented as pydantic-enum-driven transition tables, NOT asyncio coroutines. Each state machine class exposes `current_state: Literal[...]`, `history: list[Transition]`, and `handle(event: SkillEvent) -> StateTransitionResult`.
- **D-03:** State machines run on the same turn cadence as the enclosing phase. No dedicated "skill event loop". A turn = load state → process one envelope → advance state → persist → emit next artifact OR mark complete.

**SmartReviewRouter format & wiring (Area 2):**
- **D-04:** `[[template.review.rules]]` TOML array in `gstack.toml` — additive TemplateDef extension. Rule shape: `{ pattern = "glob", reviewers = ["role-name"], signal = "ui|api|crypto|security" }`. First-match WITH accumulation. `reviewer` floor always appended.
- **D-05:** SHA-pinning via `SprintState.review_sha` field — set at Review-phase entry via `subprocess.run(["git", "rev-parse", "HEAD"], ...)`. Router resolves diff paths as of `review_sha`. HEAD-advance mid-review emits `mid_review_thrash` on EventBus.
- **D-06:** `GstackReviewRouter` loads rules at plugin load, cached per team. Contributed via `GstackSprintPlugin.contribute_review_routers()`. Review-phase orchestration (new `clawteam/sprint/review_phase.py` or `_dispatch_review_phase` method on conductor) calls router, unions with always-reviewer floor.

**Reviewer decorrelation (Area 3):**
- **D-07:** Per-persona decorrelation prompts at `clawteam/templates/gstack/prompts/review/<role>.md` (× 4: reviewer, designer, security, dx-lead). `contribute_prompts(phase="review", role=<r>)` returns main + review/<role>.md appended supplement. 2 KB budget for decorrelation file (does NOT stack with 4 KB main budget).
- **D-08:** Parallel reviewers via `asyncio.gather` with isolated sub-conversations, no peer-draft visibility. `reviewer` role runs sequentially AFTER all peers complete, aggregates all reports into a single `review-report.md`.
- **D-09:** Agreement-rate > 90% triggers `sycophancy_cascade_detected` advisory event (not blocking). Threshold configurable via `[template.review] sycophancy_threshold = 0.9`.

**Cross-agent verification (Area 4):**
- **D-10:** `CrossAgentVerificationGate(PhaseGate)` at `clawteam/harness/cross_agent_verification_gate.py`. Constructor: `(phase, source_artifact, target_artifact, verifier: Callable)`. Mirrors `EvidenceGate` shape.
- **D-11:** Two initial verifier functions at `clawteam/templates/gstack/verifiers/`:
  - `verify_test_report_matches_engineer_output(test_report, engineer_diff_summary) -> (bool, reason)`
  - `verify_design_doc_covers_forcing_questions(design_doc, office_hours_answers) -> (bool, reason)`
- **D-12:** New optional `HarnessPlugin.contribute_verification_pairs()` hook returning `list[VerificationPair]`. Default `[]`. `PluginManager` wires into phase gate list at plugin load.

**Always-human Ship gate (Area 5):**
- **D-13:** `HumanApprovalGate(InteractionGate)` at `clawteam/harness/human_approval_gate.py`. Subclass requires `ship-approval.md` artifact WITH `approved_by` + `approved_at` + `sha_at_approval` frontmatter. `check()` delegates to `InteractionGate.check`, then checks approval artifact. Ignores `SprintState.auto_advance=True`.
- **D-14:** `clawteam sprint approve <id> --phase ship` CLI writes ship-approval.md with current git user + UTC + `SprintState.review_sha`. `--no-sign` + `--json` flags supported.

**/investigate auto-freeze (Area 6):**
- **D-15:** `InvestigateState.on_enter(module_path)` calls `FreezeRegistry.freeze(module_path, reason=f"investigate:{sprint_id}:{hypothesis_id}")`. `on_complete` / `on_abandon` unfreeze with matching reason.
- **D-16:** Module-path is hypothesis-provided, NOT auto-derived. First state (`hypothesis_declared`) requires reviewer to state module path explicitly. No regex-from-stack-trace.

**Verification stringency (Area 7):**
- **D-17:** Golden-trace fidelity = Strategy B+ (markdown fixtures WITH turn-count + transition-graph assertions). Fixtures at `tests/fixtures/gstack_state_machines/<skill>.transitions.json`. No Strategy A (sandbox-gstack) required.
- **D-18:** Role prompts are rewritten: `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:` lines are REMOVED. Golden tests assert BOTH (a) markers gone AND (b) corresponding skill state machine + test exist.

**Events (Area 8):**
- **D-19:** `mid_review_thrash` payload: `{sprint_id, review_sha, new_sha, reviewer_roles_active, diff_paths_added, diff_paths_removed}`. Emitted by post-turn hook in Review-phase dispatch.
- **D-20:** `sycophancy_cascade_detected` scoped per-sprint-per-round. Window = one Review phase. Re-running Review after gap closure opens new window.

### Claude's Discretion

- Concrete pydantic field names within `OfficeHoursState` / `DesignConsultationState` / `InvestigateState` — match fixture JSON keys verbatim.
- Internal structure of `prompts/review/<role>.md` decorrelation files (headings, ordering).
- Exact JSON payload key names for `mid_review_thrash` / `sycophancy_cascade_detected` events.
- Wave structure + parallelism of plans.
- Whether cross-agent verification ships as one plan or per-verifier.
- Whether `/investigate` state machine ships as one plan or splits declaration / freeze wiring / transition logic.
- Concrete `asyncio.gather` wiring shape (error propagation, cancellation on one failure, timeout policy).

### Deferred Ideas (OUT OF SCOPE)

- Tool-heavy skills (`/codex`, `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy`) → Phase 5.
- Real `TeamMemoryStore` + `/learn` write path → Phase 6.
- `AttentionQueue` + cost dashboard displaying Phase-4 events → Phase 7.
- Tool-integrated `/investigate` (git-bisect driver, flamegraph harness) → Phase 5/7.
- `/design-shotgun` + `/design-html` pipelines → Phase 6.
- Full NL diff classification for router (ML-based) → v1.1/v2.
- Reviewer "panel" with dynamic composition (N designers on UI-heavy diff) → v1.x.
- Promotion of `CrossAgentVerificationGate` / `HumanApprovalGate` upstream → only if a second template adopts.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SPRINT-03 | SmartReviewRouter selects Review-phase participants by diff content via rules in gstack.toml: UI → designer; public API → dx-lead; crypto/auth → security; always → reviewer | D-04 TOML rule shape + D-06 GstackReviewRouter consumer; Pattern 6 in `.planning/research/ARCHITECTURE.md:383` specifies CODEOWNERS-style globs (rules-first, deterministic) |
| SPRINT-04 | Review-phase agents run in parallel; reviewer runs last, synthesizes into single review-report.md; gate passes on aggregation, not individuals | D-08 asyncio.gather + isolated sub-conversations + synthesizer; ReviewReport schema at `clawteam/templates/gstack/schemas/review_report.py` already has `reviewer_persona` field populated by aggregator |
| SPRINT-05 | Ship phase always requires human approval via InteractionGate (ignores auto_advance: true). Production blast radius | D-13 HumanApprovalGate(InteractionGate) + D-14 `clawteam sprint approve` CLI; `force_interactive_phases` already plumbed at `clawteam/sprint/conductor.py:247-249` |
| SAFETY-05 | /investigate skill (reviewer role) auto-applies /freeze to module under investigation for duration | D-15/D-16 InvestigateState freeze/unfreeze hooks using existing `FreezeRegistry.freeze(path, reason=...)` API at `clawteam/harness/freeze_registry.py:149`; reason format `investigate:<sprint>:<hypothesis>` is greppable in `freeze_audit.jsonl` |
| QUALITY-07 | Gstack interactive skill state machines (/office-hours, /plan-design-review, /autoplan) ported as multi-turn state machines, not one-shot prompt bakings | D-01/D-02/D-03 per-skill pydantic state + transition-table + same turn cadence; fixtures already at `tests/fixtures/gstack_skills/{office-hours,plan-design-review,review}.md` (Phase 3 D-08) |
| QUALITY-09 | SmartReviewRouter pins to commit SHA — routing decision made on SHA that will be reviewed, not HEAD that might have moved | D-05 `SprintState.review_sha` additive field + mid_review_thrash event; `ReviewReport.review_sha` already exists as pydantic field at `clawteam/templates/gstack/schemas/review_report.py:32` (Phase 3) |
| QUALITY-13 | Reviewer decorrelation: parallel reviewers receive different system prompts optimized for persona; findings diverge rather than mirror | D-07 decorrelation prompts + D-08 prompt isolation + D-09 sycophancy_cascade_detected alarm; Pitfall 13 in `.planning/research/PITFALLS.md:441` names the specific mitigation |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Per-skill state machine (office-hours / design-consultation / investigate) | gstack-template runtime (`clawteam/templates/gstack/skills/<skill>/`) | SprintConductor turn loop (calls `handle(event)` per turn) | State is gstack-specific; delete `templates/gstack/` and everything still runs |
| Per-skill state.json persistence | OS filesystem via `file_locked` + `atomic_write_text` | `get_data_dir()/teams/<team>/sprints/<id>/skills/<skill>/<role>/` | Mirrors Phase 2 convention (freeze.json, state.json); no DB |
| Diff path extraction for routing | Git worktree (`subprocess.run(["git", "diff", "--name-only", <sha>..<sha>])`) | SprintConductor (holds `workspace_branch`) | No new git abstraction; reuse `WorkspaceManager` where it already exists |
| Rule-based diff→reviewer mapping | `GstackReviewRouter` (gstack-specific) | `ReviewRouter` Protocol (generic substrate at `clawteam/harness/review_router.py`) | Protocol is upstream-PR-shaped; concrete router is fork-local |
| Parallel reviewer execution | `asyncio.gather` in `_dispatch_review_phase` (conductor or new `review_phase.py`) | Existing per-agent spawn paths (Phase 2 semaphores still apply) | Parallel only at review dispatch; no change to agent spawn backend |
| Cross-artifact verification | `CrossAgentVerificationGate(PhaseGate)` (generic) | Two gstack verifier fns (gstack-specific) | Gate shape reusable; specific pair-ups are gstack-template decisions |
| Ship approval enforcement | `HumanApprovalGate(InteractionGate)` + CLI `clawteam sprint approve` | Existing `InteractionGate` question/answer plumbing + `force_interactive_phases=["ship"]` reservation | Inheritance composes; no override of core gate pipeline |
| /investigate freeze scope | `FreezeRegistry.freeze(path, reason)` (existing API) | `InvestigateState.on_enter/on_complete` hooks | Zero new persistence; reuse audit trail |
| `mid_review_thrash` + `sycophancy_cascade_detected` events | Existing `EventBus` at `clawteam/events/bus.py` | New `@dataclass` event types in `clawteam/events/types.py` | EventBus takes typed events (not string names — see A7 below); must subclass `HarnessEvent` |

## Standard Stack

### Core (already in repo — Phase 4 uses, doesn't add)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | v2 (existing in pyproject.toml) | `OfficeHoursState`, `DesignConsultationState`, `InvestigateState`, `VerificationPair` models | Phase 2/3 already standardized on pydantic v2 with `Literal[...]` + `min_length` constraints for stub defeat |
| tomllib | stdlib (Python 3.11+) / `tomli` (3.10 fallback) | Parse `[[template.review.rules]]` in gstack.toml | `clawteam/templates/__init__.py:11-17` already uses this fallback pattern |
| asyncio | stdlib | `asyncio.gather` for parallel reviewer dispatch | D-08; `.planning/research/ARCHITECTURE.md:213-246` justified asyncio.Semaphore pool pattern |
| subprocess | stdlib | `git rev-parse HEAD` for SHA-pinning; `git diff --name-only <sha>` for path extraction | EvidenceGate `_run_test_command` already uses `subprocess.run` with `shell=False, timeout=...` at `clawteam/harness/evidence_gate.py:85-103` — mirror that pattern |
| file_locked / atomic_write_text | `clawteam.fileutil` (existing) | Per-skill state.json persistence | Phase 2 convention — mandated by project constraint (persistence under `get_data_dir()`, never direct `open().write()`) |
| PhaseGate base | `clawteam.harness.phases.PhaseGate` | `CrossAgentVerificationGate` inheritance | Existing abstract base; `check(state) -> tuple[bool, str]` contract |
| InteractionGate | `clawteam.harness.interaction_gate.InteractionGate` | `HumanApprovalGate` inheritance | `check(state)` already handles questions/answers pairing; subclass ADDs approval-artifact check |
| FreezeRegistry | `clawteam.harness.freeze_registry.FreezeRegistry` | /investigate auto-freeze | `freeze(path, *, agent, reason, actor)` + append-only `freeze_audit.jsonl` ready (lines 149-171) |
| EventBus | `clawteam.events.bus.EventBus` | Emit `mid_review_thrash`, `sycophancy_cascade_detected` | Synchronous; handlers called in priority order; `emit(event: HarnessEvent)` takes typed events |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typer | existing | `clawteam sprint approve` CLI subcommand | Existing sprint app at `clawteam/cli/commands.py:5321+` — add one `@sprint_app.command("approve")` |
| rich | existing | JSON / rich output for `approve` CLI | Matches existing `--json` envelope across sprint CLI |
| fnmatch | stdlib | Glob matching for `[[template.review.rules]]` patterns | Matches `FreezeRegistry.is_frozen` glob pattern at `clawteam/harness/freeze_registry.py:142-143` — consistent glob semantics |
| dataclasses | stdlib | New `HarnessEvent` subclasses (`MidReviewThrash`, `SycophancyCascadeDetected`) | `clawteam/events/types.py` uses `@dataclass` (line 13+) — follow that convention |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic-driven state machine (D-02) | `transitions` library / `python-statemachine` / `xstate-python` | External dep; Phase 3 proved "pydantic + Literal is enough" for envelope_personas.py. No new dep matches PROJECT.md constraint (zero new required runtime deps). |
| asyncio.gather for parallel reviewers | `ThreadPoolExecutor` (used by `EventBus.emit_async`) | Reviewers are external CLI processes spawned via existing spawn registry; asyncio is the standard idiom the research already endorses (`ARCHITECTURE.md:213`). Threads lose cancellation semantics. |
| Subprocess git | `pygit2` / `gitpython` | External deps; Phase 2 EvidenceGate already uses `subprocess.run` with security-hardened `shell=False`. Consistency wins. |
| `[[template.review.rules]]` TOML | JSON file under `templates/gstack/review.json` | TOML is already the template format; non-Python users tune routing without code edits per D-04. |
| Review-phase dispatch as NEW file `clawteam/sprint/review_phase.py` | Extend `SprintConductor` with `_dispatch_review_phase` method | Either is valid (discretion item). Recommendation: new file, `SprintConductor` imports + calls it. Keeps conductor under ~700 LOC. |

**Installation:** No new packages required. All standard stack is already present.

**Version verification:** N/A — no new deps.

## Architecture Patterns

### System Architecture Diagram

```
                             Review-phase ENTRY
                                      │
                                      ▼
                  ┌──────────────────────────────────────────┐
                  │  1. SprintConductor records review_sha   │
                  │     state.review_sha = git rev-parse HEAD│
                  │     save_sprint_state(state)             │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │  2. GstackReviewRouter.match(paths, state)│
                  │     - paths = git diff --name-only ^..sha │
                  │     - apply [[template.review.rules]]     │
                  │     - UNION with {reviewer} always-floor  │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │  3. _dispatch_review_phase spawns N       │
                  │     parallel tasks (asyncio.gather)       │
                  │  ┌───────┐  ┌──────────┐  ┌──────────┐   │
                  │  │designer│ │ security │  │ dx-lead  │   │
                  │  └───────┘  └──────────┘  └──────────┘   │
                  │   review/     review/      review/       │
                  │ designer.md  security.md  dx-lead.md     │
                  │  (decorrelated prompts appended)          │
                  └────────────────────┬─────────────────────┘
                                       │
                      Post-turn hook ──┤── compares HEAD to review_sha
                                       │   if drift: emit mid_review_thrash
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │  4. reviewer runs SEQUENTIALLY after all  │
                  │     peers complete; reads their reports   │
                  │     writes aggregated review-report.md    │
                  │     Agreement-rate computed here;         │
                  │     >0.9 → emit sycophancy_cascade_detected│
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │  5. CrossAgentVerificationGate runs       │
                  │     at Test-phase entry:                  │
                  │     - qa ↔ engineer test-report.md ↔ diff │
                  │     - reviewer ↔ designer design-doc ↔   │
                  │       office-hours answers (6 Qs)         │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │  6. HumanApprovalGate at Ship entry:      │
                  │     - InteractionGate.check (Q&A)         │
                  │     - AND ship-approval.md with           │
                  │       approved_by + approved_at +         │
                  │       sha_at_approval == review_sha       │
                  │     Ignores auto_advance=True             │
                  └──────────────────────────────────────────┘


  INTERACTIVE STATE MACHINES (parallel to the above flow)

  pm (Think phase): /office-hours
    ┌────────┐    ┌─────────────┐    ┌─────────────┐
    │ start  │───►│Q1 asked     │───►│Q1 answered  │─── ... ───►│summary_written│
    └────────┘    └─────────────┘    └─────────────┘            └─────────────┘
        Each turn: load state.json → handle(event) → persist → emit artifact
        File: get_data_dir()/teams/<t>/sprints/<s>/skills/office-hours/pm/state.json

  designer (Think/Plan phase): /design-consultation
    per-dimension: Pass1→Pass2→...→Pass7→summary

  reviewer (Review phase): /investigate  (nested inside main Review flow)
    hypothesis_declared → freeze(module) → hypothesis_testing →
      [confirmed | disconfirmed] → next hypothesis OR halt-after-3 →
      unfreeze(module)
```

### Recommended Project Structure

```
clawteam/
├── harness/
│   ├── cross_agent_verification_gate.py   # NEW (D-10)
│   ├── human_approval_gate.py             # NEW (D-13) — note: name-collision
│   │                                       #  with existing PhaseGate subclass
│   │                                       #  in harness/phases.py:91 — see
│   │                                       #  Runtime State Inventory below
│   ├── gstack_review_router.py            # NEW (D-06) — gstack-specific,
│   │                                       #  delete-invariant honored via
│   │                                       #  `gstack_` filename prefix
│   └── review_router.py                   # EXISTING — Protocol only
├── sprint/
│   ├── state.py                            # ADD: review_sha: str | None = None
│   ├── conductor.py                        # EXTEND: _dispatch_review_phase
│   └── review_phase.py                     # NEW (D-06/D-08, optional split)
├── events/
│   └── types.py                            # ADD: MidReviewThrash,
│                                           #  SycophancyCascadeDetected
│                                           #  @dataclass(HarnessEvent)
├── plugins/
│   ├── base.py                             # ADD: contribute_verification_pairs
│   │                                       #  optional hook, default []
│   ├── manager.py                          # EXTEND: wire hook into gate list
│   └── gstack_sprint_plugin.py             # EXTEND: contribute_review_routers,
│                                           #  contribute_verification_pairs
├── cli/
│   └── commands.py                         # ADD: @sprint_app.command("approve")
└── templates/
    ├── gstack.toml                          # ADD: [template.review] +
    │                                        #  [[template.review.rules]] rows
    └── gstack/
        ├── prompts/
        │   ├── pm.md                         # EDIT: remove INTERACTIVE-RUNTIME-DEFERRED
        │   ├── designer.md                   # EDIT: remove INTERACTIVE-RUNTIME-DEFERRED
        │   ├── reviewer.md                   # EDIT: remove INTERACTIVE-RUNTIME-DEFERRED +
        │   │                                   #  SHA-PIN-DEFERRED
        │   └── review/                        # NEW dir (D-07)
        │       ├── reviewer.md                # Decorrelation: staff-eng cross-cutting
        │       ├── designer.md                # Decorrelation: rubric-first
        │       ├── security.md                # Decorrelation: threat-model-first
        │       └── dx-lead.md                 # Decorrelation: friction-first
        ├── skills/                            # NEW dir (D-01)
        │   ├── office_hours/
        │   │   └── state.py                   # OfficeHoursState pydantic + transitions
        │   ├── design_consultation/
        │   │   └── state.py                   # DesignConsultationState
        │   └── investigate/
        │       └── state.py                   # InvestigateState
        └── verifiers/                         # NEW dir (D-11)
            ├── __init__.py
            ├── test_report_matches_diff.py     # verify_test_report_matches_engineer_output
            └── design_doc_covers_forcing_qs.py # verify_design_doc_covers_forcing_questions

tests/
├── fixtures/
│   ├── gstack_state_machines/                  # NEW dir (D-17)
│   │   ├── office-hours.transitions.json
│   │   ├── design-consultation.transitions.json
│   │   └── investigate.transitions.json
│   └── review_routing/                          # NEW dir (specifics)
│       ├── renamed_ui_component.diff
│       ├── crypto_test_file.diff
│       ├── whitespace_only.diff
│       ├── package_json_dep_bump.diff
│       ├── auth_middleware_rewrite.diff
│       ├── cross_cutting_refactor.diff
│       ├── mixed_ui_and_api.diff
│       └── generated_migration.diff
├── test_gstack_review_router.py                 # NEW — 8 adversarial diffs + rule table
├── test_gstack_state_machines.py                 # NEW — 3 state machines × transition-graph
├── test_cross_agent_verification.py              # NEW — 2 verifier fns + gate integration
├── test_human_approval_gate.py                   # NEW — auto_advance override
├── test_phase4_integration.py                    # NEW — end-to-end Review→Test→Ship flow
└── test_gstack_role_prompts.py                   # EXTEND — D-18 marker-gone assertions
```

### Pattern 1: pydantic state machine with Literal transitions (D-02 elaboration)

**What:** Each state machine class has `current_state: Literal[...]`, a `handle(event: Literal[...]) -> StateTransitionResult` method that consults a frozen transition-table dict, and a `.save()`/`.load()` pair persisting via `file_locked` + `atomic_write_text`. No asyncio. Each "turn" of the enclosing phase invokes `.load()` → `.handle(event)` → `.save()`.

**When to use:** Every interactive Socratic skill (`/office-hours`, `/design-consultation`, `/investigate`). Does NOT apply to pure-rubric skills (already baked into prompts in Phase 3).

**Why this pattern:** Survives full `HarnessOrchestrator` restart per CORE-07. Transition-table style mirrors how the upstream gstack skill documents itself — 6 forcing questions in sequence = 6 transitions. Pydantic `Literal` catches misspellings at parse time. Fixtures at `tests/fixtures/gstack_state_machines/<skill>.transitions.json` declare the expected transition graph; tests assert the class's transition table matches the fixture (deterministic, no sandbox-gstack required).

**Example (sketch for OfficeHoursState):**

```python
# clawteam/templates/gstack/skills/office_hours/state.py
from __future__ import annotations
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir

OHState = Literal[
    "start",
    "q1_asked", "q1_answered",    # Demand Reality
    "q2_asked", "q2_answered",    # Status Quo
    "q3_asked", "q3_answered",    # Desperate Specificity
    "q4_asked", "q4_answered",    # Narrowest Wedge
    "q5_asked", "q5_answered",    # Observation & Surprise
    "q6_asked", "q6_answered",    # Future-Fit
    "summary_written",
    "abandoned",
]

OHEvent = Literal[
    "begin", "answered", "advance", "write_summary", "abandon",
]


class Transition(BaseModel):
    from_state: OHState
    to_state: OHState
    event: OHEvent
    ts: str
    turn: int


class OfficeHoursState(BaseModel):
    """Socratic /office-hours state machine (per-question progression).

    Per D-01/D-02: persisted as JSON under
    ~/.clawteam/teams/<t>/sprints/<s>/skills/office-hours/pm/state.json
    via file_locked + atomic_write_text.

    Per D-03: advance() is called once per pm turn in the Think phase;
    no dedicated event loop.
    """

    skill: Literal["office-hours"] = "office-hours"
    role: Literal["pm"] = "pm"
    sprint_id: str
    team: str
    current_state: OHState = "start"
    history: list[Transition] = Field(default_factory=list)
    pending_question_id: str | None = None  # e.g. "Q3"
    completed_at: str | None = None

    # Transition table — single source of truth + test fixture.
    _TRANSITIONS: dict[tuple[OHState, OHEvent], OHState] = {
        ("start", "begin"): "q1_asked",
        ("q1_asked", "answered"): "q1_answered",
        ("q1_answered", "advance"): "q2_asked",
        ("q2_asked", "answered"): "q2_answered",
        ("q2_answered", "advance"): "q3_asked",
        ("q3_asked", "answered"): "q3_answered",
        ("q3_answered", "advance"): "q4_asked",
        ("q4_asked", "answered"): "q4_answered",
        ("q4_answered", "advance"): "q5_asked",
        ("q5_asked", "answered"): "q5_answered",
        ("q5_answered", "advance"): "q6_asked",
        ("q6_asked", "answered"): "q6_answered",
        ("q6_answered", "write_summary"): "summary_written",
        # abandon can transition from any non-final state
    }

    def handle(self, event: OHEvent, turn: int) -> "StateTransitionResult":
        if event == "abandon":
            next_state: OHState = "abandoned"
        else:
            key = (self.current_state, event)
            if key not in self._TRANSITIONS:
                return StateTransitionResult(
                    ok=False,
                    reason=f"invalid transition {self.current_state} --{event}-->",
                )
            next_state = self._TRANSITIONS[key]
        self.history.append(Transition(
            from_state=self.current_state,
            to_state=next_state,
            event=event,
            ts=datetime.now(timezone.utc).isoformat(),
            turn=turn,
        ))
        self.current_state = next_state
        return StateTransitionResult(ok=True, reason="")

    @staticmethod
    def _state_path(team: str, sprint_id: str) -> Path:
        validate_identifier(team, "team name")
        validate_identifier(sprint_id, "sprint id")
        root = get_data_dir() / "teams"
        return ensure_within_root(
            root, team, "sprints", sprint_id, "skills", "office-hours", "pm",
        ) / "state.json"

    def save(self) -> Path:
        p = self._state_path(self.team, self.sprint_id)
        p.parent.mkdir(parents=True, exist_ok=True)
        with file_locked(p):
            atomic_write_text(p, self.model_dump_json(indent=2))
        return p

    @classmethod
    def load(cls, team: str, sprint_id: str) -> "OfficeHoursState":
        p = cls._state_path(team, sprint_id)
        with file_locked(p):
            return cls.model_validate_json(p.read_text(encoding="utf-8"))


class StateTransitionResult(BaseModel):
    ok: bool
    reason: str = ""
```

**Source:** Phase 2 `SprintState.save/load` pattern at `clawteam/sprint/state.py:124-149`; Phase 2 `FreezeRegistry._save` at `clawteam/harness/freeze_registry.py:106-114`.

### Pattern 2: Router rules in TOML with additive TemplateDef extension (D-04/D-06)

**What:** Add two new fields to `TemplateDef`:

```python
# clawteam/templates/__init__.py — additive extension
class ReviewRule(BaseModel):
    pattern: str
    reviewers: list[str]
    signal: str = ""


class ReviewConfig(BaseModel):
    sycophancy_threshold: float = 0.9
    rules: list[ReviewRule] = []


class TemplateDef(BaseModel):
    # ... existing fields unchanged ...
    review: ReviewConfig = ReviewConfig()  # default = empty rules, floor=0.9
```

And extend `_parse_toml` to read `[template.review]` + `[[template.review.rules]]`:

```python
# _parse_toml additive extension (after tasks parsing, around line 124)
review_data = tmpl.get("review", {})
rules_data = review_data.get("rules", [])
review = ReviewConfig(
    sycophancy_threshold=review_data.get("sycophancy_threshold", 0.9),
    rules=[ReviewRule(**r) for r in rules_data],
)
```

**When to use:** gstack.toml only — other 6 packaged templates don't declare `[template.review]`, default empty list preserves BC.

**Why this pattern:** Phase 3 Pattern 1 (strict additive extension) is proven — 12/12 regression tests stayed green when Phase 3 added 4 new TemplateDef fields. Same mechanism here. `fnmatch.fnmatch` semantics match the existing `FreezeRegistry.is_frozen` glob path at `clawteam/harness/freeze_registry.py:142-143`.

**Canonical TOML shape (from CONTEXT §specifics):**

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

[[template.review.rules]]
pattern = "**/*.css"
reviewers = ["designer"]
signal = "ui"
```

### Pattern 3: Decorrelation prompts as append supplement (D-07)

**What:** `GstackSprintPlugin.contribute_prompts` currently reads `prompts/<role>.md` unconditionally. Extend it so that when `phase == "review" AND role in {reviewer, designer, security, dx-lead}`, it ALSO reads `prompts/review/<role>.md` and appends it with a separator.

**When to use:** Review phase only. Other phases' prompts are unaffected.

**Why this pattern:** Matches Phase 3 D-06 pattern (grep-friendly per-role .md files). Separate files keep decorrelation rubric independently editable. Main prompt 4 KB budget (Phase 3 D-14) DOES NOT stack with 2 KB decorrelation file; independent gates.

**Example code extension:**

```python
# clawteam/plugins/gstack_sprint_plugin.py — extend contribute_prompts
_DECORRELATION_ROLES = {"reviewer", "designer", "security", "dx-lead"}

def contribute_prompts(self, phase: str, role: str) -> str:
    base = self._load_prompt(role)
    if not base:
        return ""
    if phase == "review" and role in _DECORRELATION_ROLES:
        supplement = self._load_decorrelation_prompt(role)
        if supplement:
            return base + "\n\n---\n\n<!-- REVIEW PHASE DECORRELATION -->\n\n" + supplement
    return base

def _load_decorrelation_prompt(self, role: str) -> str:
    if not _valid_role(role):
        return ""
    p = PROMPTS_DIR / "review" / f"{role}.md"
    # Same mtime cache pattern as _load_prompt.
    ...
```

### Pattern 4: Cross-agent verification gate (D-10)

**What:** `CrossAgentVerificationGate(PhaseGate)` mirrors `EvidenceGate`'s construction + `check()` shape, but loads TWO artifacts via `EvidenceSchemaRegistry.parse` and runs a verifier fn.

**When to use:** Test-phase entry (qa ↔ engineer test-report) and Review-phase entry (reviewer ↔ designer design-doc). Plugin-contributed via `contribute_verification_pairs`.

**Example code:**

```python
# clawteam/harness/cross_agent_verification_gate.py
from __future__ import annotations
from typing import Any, Callable
from pydantic import BaseModel

from clawteam.harness.evidence_schemas import get_schema
from clawteam.harness.phases import PhaseGate
from clawteam.team.envelope import parse_frontmatter


class CrossAgentVerificationGate(PhaseGate):
    """Gate that verifies one artifact against another (D-10).

    Both artifacts must already be present in state.artifacts (the presence
    check is EvidenceGate's job; this gate runs AFTER EvidenceGate).
    """

    def __init__(
        self,
        phase: str,
        source_artifact: str,
        target_artifact: str,
        verifier: Callable[[BaseModel, BaseModel], tuple[bool, str]],
    ) -> None:
        self.phase = phase
        self.source_artifact = source_artifact
        self.target_artifact = target_artifact
        self.verifier = verifier

    def check(self, state: Any) -> tuple[bool, str]:
        src_raw = state.artifacts.get(self.source_artifact, "")
        tgt_raw = state.artifacts.get(self.target_artifact, "")
        if not src_raw or not tgt_raw:
            # EvidenceGate already caught this, but defense-in-depth:
            return False, f"cross-verify missing: {self.source_artifact} or {self.target_artifact}"

        src_meta, _ = parse_frontmatter(src_raw)
        tgt_meta, _ = parse_frontmatter(tgt_raw)
        src_cls = get_schema(src_meta.get("artifact_type", ""))
        tgt_cls = get_schema(tgt_meta.get("artifact_type", ""))
        if src_cls is None or tgt_cls is None:
            return False, "cross-verify: unregistered schema"

        src = src_cls.model_validate(src_meta)
        tgt = tgt_cls.model_validate(tgt_meta)
        ok, reason = self.verifier(src, tgt)
        return ok, reason if not ok else ""


class VerificationPair(BaseModel):
    """Plugin-contributed cross-verification pair."""
    phase: str
    source_artifact: str
    target_artifact: str
    verifier_dotted_path: str  # e.g. "clawteam.templates.gstack.verifiers.test_report_matches_diff.verify_test_report_matches_engineer_output"
```

**Source:** `clawteam/harness/evidence_gate.py:141-214` shape.

### Pattern 5: HumanApprovalGate overriding auto_advance (D-13)

**What:** Subclass `InteractionGate`; override `check()` to (a) run `InteractionGate.check` first, (b) THEN verify a `ship-approval.md` artifact is present with `approved_by`/`approved_at`/`sha_at_approval` frontmatter, (c) verify `sha_at_approval == state.review_sha` (or HEAD if unset).

**Critical name collision:** `clawteam/harness/phases.py:91` already defines `HumanApprovalGate(PhaseGate)` — a much simpler artifact-presence gate. Phase 4's new class MUST use a different name OR replace the existing one. Recommendation: **name the new class `ShipApprovalGate(InteractionGate)`** to avoid ambiguity, OR put the new gate in `clawteam/harness/human_approval_gate.py` and leave the old one as a deprecated shim. **Planner decision.**

**Example (pseudocode):**

```python
# clawteam/harness/human_approval_gate.py (or ship_approval_gate.py — decide at plan time)
from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

from clawteam.harness.interaction_gate import InteractionGate
from clawteam.team.envelope import parse_frontmatter
from clawteam.team.models import get_data_dir


class ShipApprovalGate(InteractionGate):
    """Ship-phase gate: InteractionGate + signed ship-approval.md artifact.

    Ignores auto_advance=True (D-13 override semantics).

    Contract:
      1. Delegate to InteractionGate.check(state) — answer all open questions.
      2. Then check ship-approval.md exists as artifact AND has required fields.
      3. Then check sha_at_approval matches state.review_sha (or HEAD if unset).
    """

    def __init__(self, *, ship_approval_artifact: str = "ship-approval.md") -> None:
        super().__init__()
        self._artifact_name = ship_approval_artifact

    def check(self, state: Any) -> tuple[bool, str]:
        # Layer 1: InteractionGate questions/answers (no pending open).
        ok, reason = super().check(state)
        if not ok:
            return ok, reason

        # Layer 2: ship-approval.md present with required frontmatter.
        raw = state.artifacts.get(self._artifact_name, "")
        if not raw:
            return False, (
                f"Ship blocked: {self._artifact_name} missing. "
                f"Run `clawteam sprint approve {state.sprint_id} --phase ship` "
                f"or write the artifact manually."
            )
        try:
            meta, _ = parse_frontmatter(raw)
        except Exception as exc:
            return False, f"ship-approval.md malformed frontmatter: {exc}"
        for field in ("approved_by", "approved_at", "sha_at_approval"):
            if not meta.get(field):
                return False, f"ship-approval.md missing required field: {field}"

        # Layer 3: sha_at_approval matches review_sha (if set).
        expected_sha = getattr(state, "review_sha", None)
        if expected_sha and meta["sha_at_approval"] != expected_sha:
            return False, (
                f"ship-approval.md sha_at_approval={meta['sha_at_approval']!r} "
                f"does not match review_sha={expected_sha!r}. HEAD advanced after "
                f"approval — re-approval required."
            )

        return True, ""
```

### Pattern 6: /investigate auto-freeze via existing FreezeRegistry (D-15/D-16)

**What:** `InvestigateState` has `on_enter(module_path)` and `on_complete()` / `on_abandon()` hooks that call the existing `FreezeRegistry.freeze(path, agent="reviewer", reason=f"investigate:{sprint_id}:{hypothesis_id}", actor="reviewer")` / `.unfreeze(...)`. Reason string is structured for grep-ability in `freeze_audit.jsonl`.

**When to use:** Every `/investigate` hypothesis iteration. The hypothesis_id increments (1, 2, 3) so `freeze_audit.jsonl` correlates each freeze/unfreeze pair.

**Source:** `clawteam/harness/freeze_registry.py:149-171` (existing API, unchanged).

**Path validation:** InvestigateState validates `module_path` exists AND is under the sprint's workspace_branch root BEFORE calling freeze (D-16 explicit-scope rule). No regex-from-stack-trace.

### Anti-Patterns to Avoid

- **Bake state machines into role prompts.** Phase 3 did this for pure-rubric skills (6 forcing questions as reference content) with `INTERACTIVE-RUNTIME-DEFERRED:` meta-instruction. Phase 4 REMOVES the meta-instruction (D-18) because the runtime now owns it. Leaving BOTH prompt rubric AND runtime creates ambiguity about which is canonical.
- **Pass `extra="forbid"` on SprintState.** A3 plan-prep task verified SprintState does not set `model_config={"extra": "forbid"}` so adding `review_sha` is additive. Verify in Wave 0 before touching state.py.
- **Use `EventBus.emit(name: str, payload: dict)`.** EventBus takes TYPED events (`emit(event: HarnessEvent)`); A7 requires new `@dataclass(HarnessEvent)` subclasses for `MidReviewThrash` and `SycophancyCascadeDetected`.
- **Write directly with `open().write()`.** Every persisted state.json MUST use `file_locked` + `atomic_write_text`. Mandated project constraint.
- **Auto-derive investigate module path from stack trace regex.** D-16 explicitly rejects this. Reviewer must state the path; one wrong wildcard freezes the whole tree.
- **Share peer-draft visibility between parallel reviewers.** D-08 requires isolated sub-conversations; the only residual conversation state leakage would defeat decorrelation.
- **Synchronize the reviewer aggregator with parallel reviewers.** D-08 requires reviewer runs SEQUENTIALLY AFTER `asyncio.gather` returns all peer reports. Running reviewer in the same gather would race on conversation context.
- **Add a third plugin (e.g., `clawteam/plugins/gstack_review_router_plugin.py`).** Phase 3 D-04 locked "single cohesive plugin file". Extend `GstackSprintPlugin` in place.

## Per-Decision Implementation Map

| Decision | Touchpoint | Method / Class / Fixture |
|----------|-----------|--------------------------|
| **D-01** State dir layout | `clawteam/templates/gstack/skills/{office_hours,design_consultation,investigate}/state.py` | new pydantic class per skill with `_state_path` using `get_data_dir() / teams / <t> / sprints / <s> / skills / <skill> / <role>` |
| **D-02** pydantic transition-table | Each state class | `current_state: Literal[...]`, `history: list[Transition]`, `handle(event) -> StateTransitionResult`, `_TRANSITIONS: dict[(state, event), state]` |
| **D-03** Same turn cadence | `SprintConductor` (existing) turn loop | No new loop. Each turn: `State.load()` → `state.handle(event, turn)` → `state.save()`. Called from within existing `advance_phase` / phase-dispatch path. |
| **D-04** `[[template.review.rules]]` TOML | `clawteam/templates/__init__.py` + `clawteam/templates/gstack.toml` | Add `ReviewRule` + `ReviewConfig` pydantic classes; extend `_parse_toml` (~line 124); add `[template.review]` + 6 `[[template.review.rules]]` to gstack.toml |
| **D-05** `SprintState.review_sha` | `clawteam/sprint/state.py` | Add `review_sha: str | None = None` field with description. A3 confirms no `extra="forbid"` so additive change is BC |
| **D-05** SHA-pinning at Review entry | `SprintConductor._dispatch_review_phase` (NEW) | `subprocess.run(["git", "rev-parse", "HEAD"], cwd=state.workspace_branch, shell=False, capture_output=True, text=True, timeout=10)` |
| **D-05** Mid-review-thrash post-turn hook | `_dispatch_review_phase` post-turn boundary | Compare `state.review_sha` to `git rev-parse HEAD`; if different, emit `MidReviewThrash` event |
| **D-06** `GstackReviewRouter` | `clawteam/harness/gstack_review_router.py` (NEW) | `class GstackReviewRouter: def match(diff_paths, state) -> list[str]` — iterates `template.review.rules`, unions matches, adds `"reviewer"` floor |
| **D-06** Plugin contributes router | `clawteam/plugins/gstack_sprint_plugin.py` | `def contribute_review_routers(self) -> list[ReviewRouter]: return [GstackReviewRouter(template=self._template)]` |
| **D-06** Review-phase consumer | `clawteam/sprint/conductor.py` or new `clawteam/sprint/review_phase.py` | `_dispatch_review_phase(state)`: call `plugin_manager.review_routers → match → union` |
| **D-07** Decorrelation prompts | `clawteam/templates/gstack/prompts/review/{reviewer,designer,security,dx-lead}.md` (NEW × 4) | Per-persona anchor text per CONTEXT §specifics; ≤ 2 KB each |
| **D-07** Plugin prompt resolution | `clawteam/plugins/gstack_sprint_plugin.py::contribute_prompts` | Extend: if `phase == "review"` and `role in _DECORRELATION_ROLES`, append `prompts/review/<role>.md` |
| **D-08** asyncio.gather dispatch | New `_dispatch_review_phase` method | `asyncio.gather(*[spawn_reviewer(role, state, review_sha) for role in participants])` |
| **D-08** Reviewer aggregator | `_dispatch_review_phase` post-gather | After `gather` returns, spawn reviewer (sequentially) with all peer reports in context; writes aggregated `review-report.md` |
| **D-09** Agreement-rate computation | `_dispatch_review_phase` post-aggregation | `agreement_rate = (identical finding-severity ratings) / (total findings on most-verbose)`; compare to `template.review.sycophancy_threshold` |
| **D-09** `sycophancy_cascade_detected` event | `clawteam/events/types.py` | NEW `@dataclass` class `SycophancyCascadeDetected(HarnessEvent)` with fields `sprint_id, review_round, agreement_rate, threshold, reviewer_roles` |
| **D-10** `CrossAgentVerificationGate` | `clawteam/harness/cross_agent_verification_gate.py` (NEW) | `class CrossAgentVerificationGate(PhaseGate)` mirrors EvidenceGate shape |
| **D-11** Verifier 1 (qa↔engineer) | `clawteam/templates/gstack/verifiers/test_report_matches_diff.py` (NEW) | `verify_test_report_matches_engineer_output(test_report: TestReport, engineer_build_report: BuildReport) -> (bool, str)` — checks `test_report.test_command` output references at least one file modified/added in engineer's diff summary |
| **D-11** Verifier 2 (reviewer↔designer) | `clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py` (NEW) | `verify_design_doc_covers_forcing_questions(design_doc: DesignDoc, office_hours_state: OfficeHoursState) -> (bool, str)` — checks `design_doc.forcing_questions_addressed` contains exactly [1,2,3,4,5,6] (DesignDoc schema already enforces 6 via `min_length=6, max_length=6`) |
| **D-12** `contribute_verification_pairs` hook | `clawteam/plugins/base.py` | Add `def contribute_verification_pairs(self) -> list[VerificationPair]: return []` (optional, default empty) |
| **D-12** Manager wiring | `clawteam/plugins/manager.py::_instantiate_and_register` | After `contribute_evidence_schemas`, iterate `contribute_verification_pairs` and stash in registry consumed by `SprintConductor._build_gate_chain` |
| **D-13** `ShipApprovalGate` | `clawteam/harness/human_approval_gate.py` (or `ship_approval_gate.py`) | `class ShipApprovalGate(InteractionGate): def check(state) -> tuple[bool, str]` — Pattern 5 pseudocode |
| **D-13** Plugin attaches gate | `GstackSprintPlugin.contribute_phases` or new `contribute_gates` | Register `ShipApprovalGate()` on phase "ship" |
| **D-13** Override auto_advance | Verified in `SprintConductor._build_gate_chain` | `force_interactive_phases` already handles this: `if state.current_phase in self.force_interactive_phases: # always insert InteractionGate` (line 544). Plugin adds "ship" at plugin-load time. |
| **D-14** `clawteam sprint approve` CLI | `clawteam/cli/commands.py` (near `@sprint_app.command("resume")` at line 5447) | `@sprint_app.command("approve") def approve(sprint_id, phase, no_sign, json_output): ...` — writes ship-approval.md via existing file_locked machinery |
| **D-15** InvestigateState freeze | `clawteam/templates/gstack/skills/investigate/state.py` | `on_enter_hypothesis(module_path, hypothesis_id)`: `FreezeRegistry.freeze(module_path, agent="reviewer", reason=f"investigate:{sprint_id}:{hypothesis_id}", actor="reviewer")` |
| **D-15** InvestigateState unfreeze | same | `on_complete_hypothesis` / `on_abandon_hypothesis`: matching `.unfreeze(...)` |
| **D-16** Module-path validation | InvestigateState | On transition into `hypothesis_declared`, validate `Path(module_path).resolve()` is under `Path(state.workspace_branch).resolve()`; raise if not |
| **D-17** Transition-graph fixtures | `tests/fixtures/gstack_state_machines/{office-hours,design-consultation,investigate}.transitions.json` (NEW × 3) | Canonical JSON per Code Examples below |
| **D-17** Turn-count + graph-shape tests | `tests/test_gstack_state_machines.py` (NEW) | Assert class's `_TRANSITIONS` dict serialized to JSON matches fixture |
| **D-18** Remove meta-instructions | `clawteam/templates/gstack/prompts/{pm,designer,reviewer}.md` | `pm.md`: remove line 18 `INTERACTIVE-RUNTIME-DEFERRED:`; `designer.md`: remove line 17; `reviewer.md`: remove lines 40, 47 |
| **D-18** Golden test for markers gone | `tests/test_gstack_role_prompts.py` | Extend existing tests: assert `"INTERACTIVE-RUNTIME-DEFERRED"` + `"SHA-PIN-DEFERRED"` not in pm/designer/reviewer prompts |
| **D-19** `mid_review_thrash` event | `clawteam/events/types.py` | NEW `@dataclass class MidReviewThrash(HarnessEvent): sprint_id, review_sha, new_sha, reviewer_roles_active, diff_paths_added, diff_paths_removed` |
| **D-19** Emission site | `_dispatch_review_phase` post-turn hook | `self.bus.emit(MidReviewThrash(...))` with payload computed from `git diff <review_sha>..<new_sha> --name-only` |
| **D-20** Sycophancy per-sprint-per-round scoping | `_dispatch_review_phase` agreement-rate state | Compute once per Review-phase dispatch; no persistence across re-runs of Review. |

## Code Examples

### Example 1: `[[template.review.rules]]` TOML (D-04)

```toml
# clawteam/templates/gstack.toml — additive extension

[template.review]
sycophancy_threshold = 0.9

[[template.review.rules]]
pattern = "src/components/**/*.tsx"
reviewers = ["designer"]
signal = "ui"

[[template.review.rules]]
pattern = "**/*.css"
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

### Example 2: OfficeHoursState transition-graph fixture (D-17)

```json
// tests/fixtures/gstack_state_machines/office-hours.transitions.json
{
  "skill": "office-hours",
  "role": "pm",
  "initial_state": "start",
  "final_states": ["summary_written", "abandoned"],
  "turn_budget": 13,
  "transitions": [
    {"from": "start",       "event": "begin",         "to": "q1_asked"},
    {"from": "q1_asked",    "event": "answered",      "to": "q1_answered"},
    {"from": "q1_answered", "event": "advance",       "to": "q2_asked"},
    {"from": "q2_asked",    "event": "answered",      "to": "q2_answered"},
    {"from": "q2_answered", "event": "advance",       "to": "q3_asked"},
    {"from": "q3_asked",    "event": "answered",      "to": "q3_answered"},
    {"from": "q3_answered", "event": "advance",       "to": "q4_asked"},
    {"from": "q4_asked",    "event": "answered",      "to": "q4_answered"},
    {"from": "q4_answered", "event": "advance",       "to": "q5_asked"},
    {"from": "q5_asked",    "event": "answered",      "to": "q5_answered"},
    {"from": "q5_answered", "event": "advance",       "to": "q6_asked"},
    {"from": "q6_asked",    "event": "answered",      "to": "q6_answered"},
    {"from": "q6_answered", "event": "write_summary", "to": "summary_written"}
  ],
  "abandon_event": "abandon"
}
```

```json
// tests/fixtures/gstack_state_machines/design-consultation.transitions.json
{
  "skill": "design-consultation",
  "role": "designer",
  "initial_state": "start",
  "final_states": ["summary_written", "abandoned"],
  "turn_budget": 15,
  "dimensions": [
    "information-architecture",
    "interaction-state-coverage",
    "user-journey",
    "ai-slop-risk",
    "design-system-alignment",
    "responsive-accessibility",
    "unresolved-decisions"
  ],
  "transitions": [
    {"from": "start",       "event": "begin",         "to": "pass1_scoring"},
    {"from": "pass1_scoring","event": "scored",       "to": "pass1_scored"},
    {"from": "pass1_scored","event": "advance",       "to": "pass2_scoring"},
    {"from": "pass2_scoring","event": "scored",       "to": "pass2_scored"},
    {"from": "pass2_scored","event": "advance",       "to": "pass3_scoring"},
    {"from": "pass3_scoring","event": "scored",       "to": "pass3_scored"},
    {"from": "pass3_scored","event": "advance",       "to": "pass4_scoring"},
    {"from": "pass4_scoring","event": "scored",       "to": "pass4_scored"},
    {"from": "pass4_scored","event": "advance",       "to": "pass5_scoring"},
    {"from": "pass5_scoring","event": "scored",       "to": "pass5_scored"},
    {"from": "pass5_scored","event": "advance",       "to": "pass6_scoring"},
    {"from": "pass6_scoring","event": "scored",       "to": "pass6_scored"},
    {"from": "pass6_scored","event": "advance",       "to": "pass7_scoring"},
    {"from": "pass7_scoring","event": "scored",       "to": "pass7_scored"},
    {"from": "pass7_scored","event": "write_summary", "to": "summary_written"}
  ]
}
```

```json
// tests/fixtures/gstack_state_machines/investigate.transitions.json
{
  "skill": "investigate",
  "role": "reviewer",
  "initial_state": "idle",
  "final_states": ["resolved", "halted_after_3", "abandoned"],
  "turn_budget": 12,
  "max_hypotheses": 3,
  "transitions": [
    {"from": "idle",                "event": "open_investigation", "to": "hypothesis_declared"},
    {"from": "hypothesis_declared", "event": "module_validated",   "to": "hypothesis_testing",    "side_effect": "freeze_module"},
    {"from": "hypothesis_testing",  "event": "confirmed",          "to": "resolved",              "side_effect": "unfreeze_module"},
    {"from": "hypothesis_testing",  "event": "disconfirmed",       "to": "hypothesis_disconfirmed"},
    {"from": "hypothesis_disconfirmed","event": "next_hypothesis_if_under_3","to": "hypothesis_declared","side_effect": "unfreeze_module,then_new_freeze"},
    {"from": "hypothesis_disconfirmed","event": "reached_3",      "to": "halted_after_3",        "side_effect": "unfreeze_module"},
    {"from": "hypothesis_testing",  "event": "abandon",            "to": "abandoned",             "side_effect": "unfreeze_module"}
  ]
}
```

### Example 3: asyncio.gather shape for parallel reviewers (D-08)

```python
# clawteam/sprint/review_phase.py (NEW — discretion split; or inline in conductor)
from __future__ import annotations
import asyncio
import subprocess
from typing import Any

from clawteam.events.global_bus import get_event_bus
from clawteam.events.types import MidReviewThrash, SycophancyCascadeDetected
from clawteam.sprint.state import SprintState, save_sprint_state


async def _spawn_reviewer_task(role: str, state: SprintState, review_sha: str) -> dict:
    """Spawn ONE reviewer with isolated sub-conversation + decorrelation prompt.

    No peer-draft visibility. The reviewer's prompt is constructed from:
      prompts/<role>.md  +  prompts/review/<role>.md (decorrelation supplement)
      + pinned diff: git diff <review_sha>..<review_sha> --name-only
    Returns the reviewer's review artifact as dict.
    """
    # Real spawn goes through existing per-agent spawn paths; Phase 2
    # max_tasks_per_agent semaphores still apply.
    ...


def _current_head(workspace: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace or ".",
        shell=False,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return (result.stdout or "").strip()


def _diff_paths(workspace: str, base_sha: str, head_sha: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"],
        cwd=workspace or ".",
        shell=False,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return [p for p in (result.stdout or "").splitlines() if p]


async def dispatch_review_phase(
    state: SprintState,
    plugin_manager: Any,
    bus: Any = None,
) -> dict:
    """Orchestrate parallel reviewers + reviewer aggregator (D-06/D-08/D-19)."""
    bus = bus or get_event_bus()
    workspace = state.workspace_branch or ""

    # 1. Pin review_sha at entry (D-05).
    if not state.review_sha:
        state.review_sha = _current_head(workspace)
        save_sprint_state(state)
    review_sha = state.review_sha

    # 2. Resolve participants via routers + floor (D-06).
    diff_paths = _diff_paths(workspace, review_sha, review_sha)  # as-of review_sha
    participants: set[str] = {"reviewer"}  # floor
    for router in plugin_manager.review_routers:
        try:
            participants.update(router.match(diff_paths, state))
        except Exception:
            # RFC 001 §4.3b req 4: skip with logged warning.
            continue

    # 3. Parallel peer reviewers (all except reviewer aggregator) — D-08.
    peer_roles = sorted(participants - {"reviewer"})
    peer_reports = await asyncio.gather(
        *[_spawn_reviewer_task(r, state, review_sha) for r in peer_roles],
        return_exceptions=True,
    )
    # Post-turn thrash detection (D-19).
    new_head = _current_head(workspace)
    if new_head and new_head != review_sha:
        new_diff_paths = _diff_paths(workspace, review_sha, new_head)
        added = [p for p in new_diff_paths if p not in diff_paths]
        removed = [p for p in diff_paths if p not in new_diff_paths]
        bus.emit(MidReviewThrash(
            team_name=state.team,
            sprint_id=state.sprint_id,
            review_sha=review_sha,
            new_sha=new_head,
            reviewer_roles_active=peer_roles + ["reviewer"],
            diff_paths_added=added,
            diff_paths_removed=removed,
        ))

    # 4. Reviewer aggregator runs AFTER peers complete (D-08 — no parallel).
    reviewer_report = await _spawn_reviewer_task(
        "reviewer", state, review_sha,
    )  # receives peer_reports via prompt context

    # 5. Agreement-rate alarm (D-09/D-20).
    agreement_rate = _compute_agreement_rate(peer_reports)
    threshold = _sycophancy_threshold(plugin_manager)
    if agreement_rate > threshold:
        bus.emit(SycophancyCascadeDetected(
            team_name=state.team,
            sprint_id=state.sprint_id,
            review_round=len(state.phase_history),
            agreement_rate=agreement_rate,
            threshold=threshold,
            reviewer_roles=peer_roles,
        ))

    return {
        "review_sha": review_sha,
        "participants": sorted(participants),
        "peer_reports": peer_reports,
        "reviewer_report": reviewer_report,
        "agreement_rate": agreement_rate,
    }
```

### Example 4: `ship-approval.md` canonical frontmatter (D-14)

```markdown
---
artifact_type: ship-approval
approved_by: jac@example.com
approved_at: 2026-04-21T14:32:00Z
sha_at_approval: a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
approval_notes: |
  Human verified: tests green, QA signed off, canary plan confirmed.
sprint_id: abc12345
---

# Ship approval

Approved by jac for sprint abc12345 (commit a1b2c3d4).
```

### Example 5: New event types for `clawteam/events/types.py`

```python
# ── Phase 4: Review-phase events ──────────────────────────────────────

@dataclass
class MidReviewThrash(HarnessEvent):
    """Emitted when sprint branch HEAD advances during an in-flight review (D-19).

    Reviewers consume this event in their next turn to choose between
    re-pinning (extending review to new_sha) or marking prior review
    'superseded'.
    """
    sprint_id: str = ""
    review_sha: str = ""
    new_sha: str = ""
    reviewer_roles_active: list[str] = field(default_factory=list)
    diff_paths_added: list[str] = field(default_factory=list)
    diff_paths_removed: list[str] = field(default_factory=list)


@dataclass
class SycophancyCascadeDetected(HarnessEvent):
    """Emitted when parallel-reviewer agreement-rate crosses sycophancy_threshold (D-09/D-20).

    Advisory only — does NOT block the phase. Logged for operators via
    Phase 7's `clawteam attend --summary`.
    """
    sprint_id: str = ""
    review_round: int = 0
    agreement_rate: float = 0.0
    threshold: float = 0.9
    reviewer_roles: list[str] = field(default_factory=list)
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Glob-matching `src/components/**/*.tsx` to paths | Custom regex engine | `fnmatch.fnmatch` (stdlib) | Consistent with `clawteam/harness/freeze_registry.py:142-143` glob semantics; matches user expectation from CODEOWNERS mental model |
| Per-skill state persistence | Custom JSON atomic-write code | `clawteam.fileutil.file_locked` + `atomic_write_text` | Phase 2 lessons: concurrent writers serialize; no torn writes; no stray `.tmp` files |
| SHA extraction | Parse `.git/HEAD` manually | `subprocess.run(["git", "rev-parse", "HEAD"], shell=False, timeout=10)` | EvidenceGate already uses `subprocess.run` this way (evidence_gate.py:85); attacker-controlled env neutralized via `shell=False`; no git binary bundling |
| State-machine persistence on restart | asyncio coroutines + Condition variables | pydantic v2 `model_dump_json` / `model_validate_json` | D-02 rationale; CORE-07 requires survival of full orchestrator restart |
| Plugin-registry wiring | Custom plugin-load hook | `PluginManager._instantiate_and_register` (existing) | Same path already wires `contribute_phases`, `contribute_evidence_schemas`; one more hook follows identical pattern |
| Multi-choice decorrelation | `random.choice` on prompt variants | Per-persona hand-authored decorrelation file | Decorrelation must be deterministic + grep-able for reproducibility of golden tests |
| Gate composition | New gate-registry mechanism | Existing `SprintConductor._build_gate_chain` | Already composes EvidenceGate + forced_progress_gate + InteractionGate (lines 517-549). Phase 4 plugs new gates into the same chain. |
| Git diff path extraction | Parse `git status --porcelain` | `git diff --name-only <sha>..<sha>` | Standard git shape; matches `.planning/research/ARCHITECTURE.md:566` data flow |

**Key insight:** Every Phase 4 building block has a Phase 1/2/3 parent with the same shape — state persistence mirrors SprintState.save/load, router Protocol was declared in Phase 1, gate subclassing mirrors EvidenceGate extending ArtifactRequiredGate, verifier fns mirror the `detect_stub` free-fn shape in evidence_gate.py. The primary risk is not inventing new primitives; it is using the existing ones consistently.

## Runtime State Inventory

Phase 4 is primarily additive (new files, new fields). One pre-existing name collision + a handful of stale artifacts to inventory.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `freeze.json` per sprint (FreezeRegistry) — /investigate will write entries with `agent="reviewer", reason="investigate:<s>:<h>"` | None — existing file accommodates new reason strings naturally. No data migration. |
| Stored data | `freeze_audit.jsonl` — append-only — /investigate entries grep-able with `jq '.reason | startswith("investigate:")'` | None — append-only by design. |
| Stored data | `state.json` per sprint (SprintState) — Phase 4 adds `review_sha: str \| None = None` field | Code edit only — pydantic v2 BC: existing state.json files missing `review_sha` load as `None`. Verified: existing SprintState uses plain `BaseModel` (no `extra="forbid"`) per A3. |
| Stored data | Per-skill state.json under `sprints/<id>/skills/<skill>/<role>/state.json` | NEW — no migration (no pre-existing data). |
| Live service config | None. All Phase 4 config is in-repo (gstack.toml, role prompts). | None. |
| OS-registered state | None. No OS-level registrations. | None. |
| Secrets / env vars | None introduced or modified. Existing `CLAWTEAM_ARTIFACT_CAP_KB` etc. unchanged. | None. |
| Build artifacts | None. Pure Python additions; no compiled artifacts. | None. |
| **Class name collision** | `HumanApprovalGate(PhaseGate)` at `clawteam/harness/phases.py:91` (existing, pre-Phase-4) vs. Phase 4's planned `HumanApprovalGate(InteractionGate)` per D-13 | **Planner decision:** Either (a) rename Phase 4's new class to `ShipApprovalGate(InteractionGate)` and place it at `clawteam/harness/ship_approval_gate.py` (recommended — zero BC risk, grep-finds `ShipApprovalGate` surface all Phase 4 touchpoints), OR (b) delete the existing `HumanApprovalGate` since no existing template references it (verified via grep; only used in `harness/__init__.py` export + `tests/test_harness.py` + internal import at `harness/orchestrator.py`). Option (a) is safer. |
| **Prompt meta-instructions** | 4 lines across pm.md, designer.md, reviewer.md x 2 (A6 baseline = 4 lines) | Code edit (D-18) — remove all 4 lines at end of Phase 4 landing. |
| **Existing review-phase artifacts** | `review-report.md` already has a pydantic schema at `clawteam/templates/gstack/schemas/review_report.py` with `review_sha: str = Field(..., min_length=7, pattern=r"^[0-9a-f]+$")` | None — schema already Phase-4-ready. No change. |

**Nothing found in the "live service config" or "secrets/env vars" categories:** verified by grepping `clawteam/` for `[template.review]`, `sycophancy_threshold`, and `review_sha` — no existing references beyond the review_report.py schema.

## Common Pitfalls

### Pitfall 1: Interactive-skill collapse (Pitfall 7 from research/PITFALLS.md)

**What goes wrong:** Agent monologues all 6 forcing questions in one turn instead of asking one at a time.
**Why it happens:** Role prompt describes the *process*; nothing *enforces* one-question-per-turn.
**How to avoid:** D-01/D-02 state machine makes the progression structural. `handle(event)` can only advance one transition per call. `pending_question_id` field locks the current question until the corresponding `answered` event arrives.
**Warning signs:** State file shows `current_state=q1_asked` and a single turn produced Q1 through Q6 text. Golden test D-17 checks `turn_budget=13` (not 1) to catch monologue collapse.

### Pitfall 2: Reviewer echoing cascade (Pitfall 13)

**What goes wrong:** All 4 parallel reviewers produce the same "looks good to me" cluster because they share a base model and RLHF sycophancy compounds.
**Why it happens:** Same model + similar prompts → similar outputs. If peer-draft visibility ever leaks, the effect amplifies (reviewer N+1 reads reviewer N's draft → agrees).
**How to avoid:** (a) decorrelation prompts per-persona (D-07) anchor each reviewer to a distinct rubric (staff-eng vs threat-model vs design-rubric vs friction-trace); (b) D-08 prohibits peer-draft visibility — each reviewer's sub-conversation is isolated; (c) D-09 `sycophancy_cascade_detected` event surfaces agreement rate > 90% even when decorrelation worked structurally.
**Warning signs:** All 4 reviewer reports cite identical file ranges. Aggregated review contains no "designer disagrees with dx-lead" language. Event log shows `sycophancy_cascade_detected` firing every sprint.

### Pitfall 3: Mid-review diff thrashing (Pitfall 9)

**What goes wrong:** engineer force-pushes during reviewer's in-flight analysis; reviewer's verdict now references deleted hunks.
**Why it happens:** No SHA snapshotting → race between review start and review end.
**How to avoid:** D-05 pins `state.review_sha` at Review entry; D-19 `mid_review_thrash` event fires on HEAD advance; reviewer chooses re-pin vs supersede in next turn.
**Warning signs:** Review report with `verdict: superseded` — confirms the mechanism worked.

### Pitfall 4: Investigate freeze-locks the whole tree

**What goes wrong:** Reviewer declares module path `**` or `src/**`; FreezeRegistry freezes everything; no one can write.
**Why it happens:** Auto-derivation from stack trace regex guesses too broadly.
**How to avoid:** D-16 explicit-scope rule — reviewer declares the path; state machine validates it exists + is under workspace_branch root before calling `freeze`. No regex guessing.
**Warning signs:** `freeze_audit.jsonl` entries with `reason="investigate:..."` and `path` containing `/**`. Add a D-16 unit test: InvestigateState rejects glob-containing paths.

### Pitfall 5: Ship auto-advance bypass

**What goes wrong:** User sets `auto_advance=true` for speed; Ship phase advances without human approval; wrong code ships to production.
**Why it happens:** `InteractionGate` has an `auto_advance=true` escape hatch.
**How to avoid:** D-13 `HumanApprovalGate`/`ShipApprovalGate` IGNORES auto_advance; additionally requires signed ship-approval.md. Plumbed via existing `force_interactive_phases=["ship"]` at `clawteam/sprint/conductor.py:247` (line confirms reservation).
**Warning signs:** Any green sprint with `status=completed` and no `ship-approval.md` in artifacts — the gate failed open.

### Pitfall 6: Evidence-gate gaming via unverified cross-references (Pitfall 8 extended)

**What goes wrong:** engineer writes test-report.md claiming tests passed on files they never modified; qa's test-report citation is hallucinated.
**Why it happens:** EvidenceGate validates schema + presence but not cross-reference.
**How to avoid:** D-10/D-11 `CrossAgentVerificationGate` runs the verifier fn that checks test_report's `test_command` output references at least one file from engineer's diff.
**Warning signs:** Cross-verify gate returns `False` with reason "no test references engineer's diff" — confirms catch.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest>=9.0.0,<10.0.0 (verified at `pyproject.toml:32`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` with `testpaths = ["tests"]` (line 79-80) |
| Quick run command | `pytest tests/test_gstack_review_router.py tests/test_gstack_state_machines.py tests/test_human_approval_gate.py -x -q` |
| Full suite command | `pytest tests/ -q` (972 tests baseline from Phase 3 verification) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| SPRINT-03 | Router pulls designer on UI diff (`src/components/**/*.tsx`) | unit | `pytest tests/test_gstack_review_router.py::test_ui_diff_pulls_designer -x` | ❌ Wave 0 |
| SPRINT-03 | Router pulls security on crypto diff (`**/crypto/**`) | unit | `pytest tests/test_gstack_review_router.py::test_crypto_diff_pulls_security -x` | ❌ Wave 0 |
| SPRINT-03 | Router pulls dx-lead on api/package diff | unit | `pytest tests/test_gstack_review_router.py::test_api_and_package_pull_dx_lead -x` | ❌ Wave 0 |
| SPRINT-03 | Router always includes `reviewer` floor | unit | `pytest tests/test_gstack_review_router.py::test_reviewer_always_participates -x` | ❌ Wave 0 |
| SPRINT-03 | 8 adversarial diffs golden test | unit | `pytest tests/test_gstack_review_router.py::test_adversarial_diffs -x` (parametrized over 8 fixtures) | ❌ Wave 0 |
| SPRINT-04 | asyncio.gather dispatches peers in parallel | unit | `pytest tests/test_sprint_conductor.py::test_dispatch_review_phase_parallel -x` | ❌ Wave 0 |
| SPRINT-04 | Reviewer aggregator runs sequentially AFTER peers | unit | `pytest tests/test_sprint_conductor.py::test_reviewer_aggregator_sequential -x` | ❌ Wave 0 |
| SPRINT-04 | Aggregated review-report.md passes phase gate (not individuals) | unit | `pytest tests/test_gstack_plugin.py::test_review_gate_on_aggregate -x` | ❌ Wave 0 |
| SPRINT-05 | Ship phase ignores auto_advance=true | unit | `pytest tests/test_human_approval_gate.py::test_ignores_auto_advance -x` | ❌ Wave 0 |
| SPRINT-05 | ship-approval.md missing blocks advance | unit | `pytest tests/test_human_approval_gate.py::test_no_approval_blocks -x` | ❌ Wave 0 |
| SPRINT-05 | `clawteam sprint approve` writes signed approval | integration | `pytest tests/test_sprint_cli.py::test_approve_command -x` | ❌ Wave 0 |
| SAFETY-05 | /investigate freezes declared module | unit | `pytest tests/test_gstack_state_machines.py::test_investigate_freezes_on_enter -x` | ❌ Wave 0 |
| SAFETY-05 | /investigate unfreezes on complete | unit | `pytest tests/test_gstack_state_machines.py::test_investigate_unfreezes_on_complete -x` | ❌ Wave 0 |
| SAFETY-05 | Investigate rejects glob-containing paths | unit | `pytest tests/test_gstack_state_machines.py::test_investigate_rejects_glob_paths -x` | ❌ Wave 0 |
| SAFETY-05 | freeze_audit.jsonl records `investigate:<sprint>:<hypothesis>` reason | integration | `pytest tests/test_freeze_registry.py::test_investigate_audit_entry -x` | ❌ Wave 0 |
| QUALITY-07 | OfficeHoursState transition table matches fixture | unit | `pytest tests/test_gstack_state_machines.py::test_office_hours_transitions -x` | ❌ Wave 0 |
| QUALITY-07 | OfficeHours state persists across restart | integration | `pytest tests/test_gstack_state_machines.py::test_office_hours_round_trip -x` | ❌ Wave 0 |
| QUALITY-07 | DesignConsultation state machine 7 dimensions | unit | `pytest tests/test_gstack_state_machines.py::test_design_consultation_transitions -x` | ❌ Wave 0 |
| QUALITY-07 | Investigate state machine halts after 3 hypotheses | unit | `pytest tests/test_gstack_state_machines.py::test_investigate_halt_after_3 -x` | ❌ Wave 0 |
| QUALITY-07 | pm.md no longer contains `INTERACTIVE-RUNTIME-DEFERRED:` | unit | `pytest tests/test_gstack_role_prompts.py::test_markers_removed -x` | ❌ Wave 0 |
| QUALITY-09 | review_sha pinned at Review entry via `git rev-parse HEAD` | unit | `pytest tests/test_sprint_conductor.py::test_review_sha_pinned_on_entry -x` | ❌ Wave 0 |
| QUALITY-09 | Mid-review thrash emits MidReviewThrash event | integration | `pytest tests/test_phase4_integration.py::test_mid_review_thrash_emits -x` | ❌ Wave 0 |
| QUALITY-09 | SprintState round-trips review_sha field | unit | `pytest tests/test_sprint_state.py::test_review_sha_persists -x` | ❌ Wave 0 |
| QUALITY-13 | Each reviewer loads a distinct decorrelation prompt | unit | `pytest tests/test_gstack_plugin.py::test_review_prompts_decorrelated -x` | ❌ Wave 0 |
| QUALITY-13 | Parallel reviewers run with no peer-draft visibility | unit | `pytest tests/test_sprint_conductor.py::test_reviewer_isolation -x` | ❌ Wave 0 |
| QUALITY-13 | Agreement-rate > 0.9 emits SycophancyCascadeDetected | unit | `pytest tests/test_sprint_conductor.py::test_sycophancy_event_emits -x` | ❌ Wave 0 |
| QUALITY-13 | Cross-verify (qa↔engineer) catches mismatched test_command | unit | `pytest tests/test_cross_agent_verification.py::test_qa_verifier_catches_mismatch -x` | ❌ Wave 0 |
| QUALITY-13 | Cross-verify (reviewer↔designer) catches missing forcing questions | unit | `pytest tests/test_cross_agent_verification.py::test_design_doc_verifier_catches_missing_qs -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_gstack_review_router.py tests/test_gstack_state_machines.py tests/test_human_approval_gate.py tests/test_cross_agent_verification.py -x -q` (< 30 s)
- **Per wave merge:** `pytest tests/test_gstack_plugin.py tests/test_sprint_conductor.py tests/test_sprint_state.py tests/test_freeze_registry.py tests/test_gstack_role_prompts.py tests/test_phase4_integration.py -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`: `pytest tests/ -q` (1000+ tests including new Phase 4 additions)

### Wave 0 Gaps

- [ ] `tests/test_gstack_review_router.py` — covers SPRINT-03 + QUALITY-09 routing concerns
- [ ] `tests/test_gstack_state_machines.py` — covers QUALITY-07 (3 state machines) + SAFETY-05
- [ ] `tests/test_cross_agent_verification.py` — covers QUALITY-13 cross-verification + SPRINT-04
- [ ] `tests/test_human_approval_gate.py` — covers SPRINT-05
- [ ] `tests/test_phase4_integration.py` — covers end-to-end Review→Test→Ship + QUALITY-09 thrash
- [ ] `tests/fixtures/gstack_state_machines/*.transitions.json` × 3 — covers QUALITY-07 / D-17
- [ ] `tests/fixtures/review_routing/*.diff` × 8 — covers SPRINT-03 adversarial set
- [ ] Extensions to existing files:
  - `tests/test_gstack_plugin.py` — `test_review_prompts_decorrelated`, `test_contribute_review_routers`, `test_contribute_verification_pairs`
  - `tests/test_sprint_conductor.py` — `test_dispatch_review_phase_*`, `test_review_sha_pinned_on_entry`, `test_reviewer_isolation`, `test_sycophancy_event_emits`
  - `tests/test_sprint_state.py` — `test_review_sha_persists`, `test_review_sha_default_none`
  - `tests/test_freeze_registry.py` — `test_investigate_audit_entry`
  - `tests/test_sprint_cli.py` — `test_approve_command`
  - `tests/test_gstack_role_prompts.py` — `test_markers_removed`
  - `tests/test_event_types_phase2.py` → rename to `test_event_types.py` OR add Phase 4 dataclass tests adjacent

## Plan-Prep Verifications

Status after reading cited files this session:

| ID | Assumption | Status | Evidence |
|----|-----------|--------|----------|
| **A1** | `ReviewRouter.match(diff_paths: list[str], state: SprintState) -> list[str]` signature is correct | ✅ CONFIRMED | `clawteam/harness/review_router.py:27` — exact signature `def match(self, diff_paths: list[str], state: "SprintState") -> list[str]:`. No adapter needed. |
| **A2** | `HarnessPlugin` currently LACKS `contribute_verification_pairs` | ✅ CONFIRMED | Grep `clawteam/plugins/base.py`: no match. Hook does not exist; Phase 4 adds it. Existing plugins default to empty via ABC default. |
| **A3** | `SprintState` pydantic model uses `extra="ignore"` (allows adding `review_sha` field additively) | ✅ CONFIRMED | `clawteam/sprint/state.py:32` — plain `class SprintState(BaseModel):` with no `model_config`. pydantic v2 default `extra` behavior allows adding new fields with defaults; BC preserved. Adding `review_sha: str \| None = None` requires no migration. |
| **A4** | `SprintConductor` has Review-phase dispatch path that can be extended | ⚠️ ADJUSTED | `clawteam/sprint/conductor.py` has generic `advance_phase` but NO phase-specific dispatch. `_build_gate_chain` (line 517) composes gates per phase but no dedicated `_dispatch_review_phase` method exists. **Planner must CREATE `_dispatch_review_phase` method (or new `clawteam/sprint/review_phase.py` module).** Current `advance_phase` just runs gates and flips `current_phase`; Phase 4 needs a method that spawns parallel reviewers when entering Review. |
| **A5** | gstack.toml parser accepts unknown `[[template.review.rules]]` entries under pydantic `extra="ignore"` | ⚠️ ADJUSTED | `clawteam/templates/__init__.py::_parse_toml` only reads specific keys (`name`, `description`, `command`, `backend`, `leader`, `agents`, `tasks`, `leader_role`, `phases`, `model_profile`, `memory`). Unknown keys are **silently dropped at parse time**. For `[[template.review.rules]]` to be read, `_parse_toml` MUST be extended to call `tmpl.get("review", {})` and parse the nested list. Planner includes this as a sub-task in the TemplateDef-extension plan. |
| **A6** | `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:` grep-count baseline in prompts | ✅ CONFIRMED | Grep output in this session: **4 lines** total — `pm.md:18`, `designer.md:17`, `reviewer.md:40`, `reviewer.md:47` (SHA-PIN-DEFERRED). D-18 removal asserts count drops to 0. |
| **A7** | EventBus accepts arbitrary string event names with dict payloads via `emit(name, payload)` | ❌ REJECTED — ADJUSTED | `clawteam/events/bus.py:86` — `emit(self, event: HarnessEvent) -> list[Any]`. API takes a **typed event object**, NOT a `(name, payload)` tuple. **Planner must add** `@dataclass class MidReviewThrash(HarnessEvent):` and `@dataclass class SycophancyCascadeDetected(HarnessEvent):` to `clawteam/events/types.py`. Sites emit `bus.emit(MidReviewThrash(...))`. |
| **A8** | `SprintConductor.advance_phase` accepts `actor: str` parameter | ✅ CONFIRMED | `clawteam/sprint/conductor.py:304-308` — `def advance_phase(self, sprint_id: str, actor: str = "") -> tuple[bool, str]:`. Phase 3 D-10 already landed. Phase 4 uses unchanged for Ship-approval attribution (optional). |

**Additional verifications surfaced during this research pass (NEW — not in CONTEXT plan-prep list):**

| ID | Verification | Evidence | Risk if Wrong |
|----|--------------|----------|---------------|
| **A9 (NEW)** | `HumanApprovalGate(PhaseGate)` already exists at `clawteam/harness/phases.py:91` as a simple artifact-presence gate | ✅ CONFIRMED via grep (12 files reference the name) | Name collision. Planner must rename Phase 4's new class (recommend `ShipApprovalGate`) OR accept BC-risk of replacing the existing simple gate. |
| **A10 (NEW)** | `ReviewReport.review_sha` pydantic field already exists at `clawteam/templates/gstack/schemas/review_report.py:32` with `min_length=7, pattern=r"^[0-9a-f]+$"` | ✅ CONFIRMED | Zero additional schema work for Phase 4's review-report.md SHA enforcement — the constraint is already there (Phase 3 Pitfall-9 SHA-PIN-DEFERRED schema-level enforcement). |
| **A11 (NEW)** | `force_interactive_phases=["ship"]` is already plumbed into `SprintConductor._build_gate_chain` | ✅ CONFIRMED at `clawteam/sprint/conductor.py:247, 544` | ShipApprovalGate plugs into existing machinery; no conductor edit needed beyond the gate registration via `contribute_gates`. |
| **A12 (NEW)** | No dedicated `investigate.md` fixture exists in `tests/fixtures/gstack_skills/` — /investigate content is merged into `review.md` | ✅ CONFIRMED via `ls tests/fixtures/gstack_skills/` | The "halt after 3 hypotheses" + "iron-law" language in Phase 3 `reviewer.md` is synthesized reviewer-prompt content, not verbatim from upstream fixture. Planner's golden test for InvestigateState checks the state-machine fixture JSON, not a .md reference. Safe. |

## Assumptions Log

Items tagged `[ASSUMED]` in this research. Planner should verify or accept at plan time:

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `asyncio.gather(*[...], return_exceptions=True)` is the correct shape for parallel reviewer dispatch (per CONTEXT "Claude's Discretion" #7) | Code Examples §Example 3 | [ASSUMED] If error propagation is stricter (e.g., cancel-all-on-first-fail), planner may switch to `asyncio.TaskGroup` (Python 3.11+). Effect: one reviewer crash takes down whole review. Project is Python 3.10+ so TaskGroup would make 3.10 fail. Recommendation: stay with `gather(..., return_exceptions=True)`. |
| A2 | Agreement-rate formula `(identical severity ratings) / (findings on most-verbose)` per D-09 is the correct computation | Per-Decision Map (D-09) | [ASSUMED] No citation in upstream gstack for this exact formula — D-09 invented it for Phase 4. If formula produces false-positives (e.g., reviewers unanimous on one legit critical bug), threshold tuning absorbs it. Advisory-only event mitigates impact. |
| A3 | `asyncio.gather` can invoke existing per-agent spawn paths without refactoring them to async | Pattern 3 / Example 3 | [ASSUMED] The existing spawn registry returns agent processes; `asyncio.run_in_executor` may be required to bridge sync spawn + async gather. Planner verifies at Wave-0 prep by grepping `clawteam/harness/spawner.py` for coroutine-safety. If spawn is blocking sync, wrap in `loop.run_in_executor(...)`. |
| A4 | `fnmatch.fnmatch` handles `**` (doublestar) recursive glob | Pattern 2 / Don't Hand-Roll | [ASSUMED] `fnmatch` actually treats `**` as a literal match, NOT recursive. **Correction at plan time:** use `pathlib.PurePath.match` OR the `wcmatch` package OR custom path-walker with `**` expansion. Planner verifies: quick test `fnmatch.fnmatch("src/a/b/c.tsx", "src/**/*.tsx")`. If false, use `PurePosixPath("src/a/b/c.tsx").match("src/**/*.tsx")` which Python 3.13 supports for `**`, or split pattern on `**` and check prefix. |
| A5 | "INTERACTIVE-RUNTIME-DEFERRED:" / "SHA-PIN-DEFERRED:" baseline count is exactly 4 lines | Plan-Prep A6 | ✅ Verified via grep in this session. |
| A6 | `CrossAgentVerificationGate` runs AFTER `EvidenceGate` in the phase's gate chain (EvidenceGate verifies presence + schema first) | Pattern 4 | [ASSUMED] Gate ordering in `_build_gate_chain` is `EvidenceGate → forced_progress_gate → InteractionGate` (line 540-549). Phase 4 inserts CrossAgentVerificationGate AFTER EvidenceGate. Planner confirms insertion point. |
| A7 | ReviewConfig default `sycophancy_threshold=0.9` is acceptable across all teams | D-09 / Pattern 2 | [ASSUMED] CONTEXT D-09 specifies default 0.9 but allows override via `[template.review] sycophancy_threshold`. Safe default. |
| A8 | `approved_by` field in ship-approval.md may be any string (not restricted to git identity) | Example 4 | [ASSUMED] CONTEXT D-14 says `clawteam sprint approve` uses "current git user" — assumes git user is available. Planner handles `.gitconfig`-missing case via fallback to `$USER` or explicit `--approver` flag. |

## Open Questions (RESOLVED)

1. **Split vs single-file for Review-phase orchestration.** CONTEXT "Claude's Discretion" #5 defers to planner. Recommendation: NEW `clawteam/sprint/review_phase.py` (contains `dispatch_review_phase` async fn); `SprintConductor` imports + invokes. Rationale: keeps conductor under ~700 LOC; test isolation easier. Alternative (extend conductor): simpler dependency graph but bloats conductor past 800 LOC with phase-specific orchestration code — violates single-responsibility convention Phase 2 established.

2. **Test file for MidReviewThrash + SycophancyCascadeDetected dataclasses.** Existing `tests/test_event_types_phase2.py` tests Phase 2 events. Options: (a) extend that file with Phase 4 dataclass tests; (b) rename to `tests/test_event_types.py` and partition by phase inside; (c) new `tests/test_event_types_phase4.py`. Planner picks; low impact.

3. **Agreement-rate computation scope.** D-09 defines `(identical severity ratings) / (findings on most-verbose reviewer)`. Does "identical severity" mean exact-match of severity enum (blocker/critical/major/minor) or severity+location+message triple? Planner specifies at plan-task time. Recommendation: **severity-only** — measures cascade pattern without over-fitting to prose matches; simpler to compute + test.

4. **Ship-approval artifact in `state.artifacts` vs filesystem.** Existing sprint artifacts are stored in `SprintState.artifacts` (dict). `ship-approval.md` should live there for EvidenceGate integration. `clawteam sprint approve` writes it; `ArtifactStore.write` path populates the dict. Planner verifies the existing write path idempotently adds to `state.artifacts`.

5. **`git rev-parse HEAD` in non-git workspace.** If `state.workspace_branch == ""` or the directory isn't a git repo, `subprocess.run(...)` returns non-zero. Planner decides: (a) raise to caller (fail review-phase entry), (b) log warning + use empty `review_sha` (routing still works via diff_paths default). Recommendation: fail fast — review without SHA-pinning defeats QUALITY-09.

6. **What constitutes "one turn" for state machine advancement (D-03)?** The phrase "same turn cadence as the enclosing phase" is from D-03. In `SprintConductor`, a "turn" is a successful `ArtifactStore.write()` or `Transport.deliver()` (Phase 2 D-14). Planner clarifies: `OfficeHoursState.handle(event)` fires once per pm ArtifactStore.write in Think phase. Every other turn type is a no-op for the state machine.

7. **Decorrelation prompt budget enforcement.** D-07 says 2 KB per decorrelation file. Should there be an automated budget gate like Phase 3 D-14's `wc -c` check, or hand-audit only? Recommendation: add to `tests/test_gstack_role_prompts.py` as an assertion: every `prompts/review/*.md` ≤ 2048 bytes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| git | SHA-pinning + diff extraction | ✓ (Phase 2 EvidenceGate already uses `subprocess.run` for git ops) | system git | — |
| Python 3.10+ | asyncio.gather, pydantic v2 | ✓ (pyproject.toml declares `requires-python`) | 3.10+ | — |
| pytest 9.x | Tests | ✓ | 9.0.0+ | — |
| tomllib (3.11) / tomli (3.10) | gstack.toml parse | ✓ (already in clawteam/templates/__init__.py) | stdlib / fallback | — |

**Missing dependencies with no fallback:** None. All required infrastructure is present.

**Missing dependencies with fallback:** None.

## Sources

### Primary (HIGH confidence)

- `clawteam/harness/review_router.py` — ReviewRouter Protocol signature verified verbatim
- `clawteam/harness/interaction_gate.py` — InteractionGate.check contract verified
- `clawteam/harness/freeze_registry.py` — FreezeRegistry.freeze/unfreeze API + audit JSONL shape verified
- `clawteam/harness/evidence_schemas.py` — EvidenceSchemaRegistry + ArtifactFrontmatterBase verified
- `clawteam/harness/evidence_gate.py` — EvidenceGate 4-check protocol + subprocess.run pattern verified
- `clawteam/harness/phases.py` — PhaseGate ABC + existing HumanApprovalGate collision verified (line 91)
- `clawteam/sprint/state.py` — SprintState.save/load + plain BaseModel (no extra="forbid") verified
- `clawteam/sprint/conductor.py` — SprintConductor.advance_phase actor param (line 304), _build_gate_chain (line 517), force_interactive_phases plumbing (lines 247, 544) verified
- `clawteam/plugins/base.py` — HarnessPlugin hooks (contribute_phases, contribute_evidence_schemas, contribute_review_routers) + contribute_verification_pairs absence verified
- `clawteam/plugins/manager.py` — _instantiate_and_register path (lines 139-168) verified
- `clawteam/plugins/gstack_sprint_plugin.py` — Phase 3 plugin shape + 5 contributed hooks verified
- `clawteam/templates/__init__.py` — TemplateDef + _parse_toml key-list (lines 99-130) verified; A5 adjustment sourced here
- `clawteam/templates/gstack.toml` — current Phase 3 template content verified (115 lines)
- `clawteam/templates/gstack/prompts/{pm,designer,reviewer}.md` — INTERACTIVE-RUNTIME-DEFERRED / SHA-PIN-DEFERRED lines verified
- `clawteam/templates/gstack/envelope_personas.py` — 11 per-persona envelope subclasses verified
- `clawteam/templates/gstack/schemas/review_report.py` — review_sha pydantic field already present (A10)
- `clawteam/events/bus.py` — EventBus.emit(event: HarnessEvent) signature verified (line 86); A7 rejected based on this
- `clawteam/events/types.py` — HarnessEvent dataclass base + Phase 2/3 event types verified
- `clawteam/team/envelope.py` — parse_frontmatter + TurnEnvelope verified
- `tests/fixtures/gstack_skills/office-hours.md` — 6 forcing questions verbatim verified
- `tests/fixtures/gstack_skills/plan-design-review.md` — 7 passes verified verbatim (lines 1416, 1458-1582)
- `tests/fixtures/gstack_skills/review.md` — /investigate iron-law content NOT verbatim (A12 finding)
- `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md` — D-01..D-20 locked decisions + A1-A8 plan-prep verifications
- `.planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md` — D-06/D-07/D-08/D-14 foundations Phase 4 builds on
- `.planning/phases/02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention/02-CONTEXT.md` — D-23 auto_advance semantics + gate chain composition
- `.planning/phases/01-core-harness-extensions/01-CONTEXT.md` — D-04 contribute_review_routers hook origin
- `.planning/research/ARCHITECTURE.md` Pattern 6 (lines 383-415) — CODEOWNERS-style globs + parallel dispatch rationale
- `.planning/research/ARCHITECTURE.md` §"Multi-sprint concurrency" (lines 209-246) — asyncio.Semaphore pattern verification
- `.planning/research/PITFALLS.md` Pitfall 7 (interactive skills), 8 (gate gaming), 9 (SHA-pinning), 13 (sycophancy) — prevention rationale
- `.planning/REQUIREMENTS.md` SPRINT-03/04/05, SAFETY-05, QUALITY-07/09/13 — verbatim requirement text

### Secondary (MEDIUM confidence)

- `pyproject.toml:32, 79-80` — pytest version + testpaths; Python version requirement inferred from stdlib usage
- `.planning/config.json` — workflow.nyquist_validation enabled (Validation Architecture section included)

### Tertiary (LOW confidence — flagged for validation)

- `asyncio.gather` error propagation semantics in CPython 3.10 when task exceptions are raised before cancellation — if strict cancel-all semantics are needed, planner re-verifies pattern.
- `fnmatch.fnmatch` doublestar `**` behavior — A4 `[ASSUMED]` flag; quick verification required before implementing router glob match.
- Agreement-rate formula interpretation — A2 `[ASSUMED]`; no upstream citation.

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all dependencies verified in-repo; zero new runtime deps
- Architecture: **HIGH** — all 6 patterns anchor to existing Phase 1/2/3 code read firsthand
- Per-decision map: **HIGH** — each touchpoint verified against actual file paths + line numbers
- Pitfalls: **HIGH** — sourced from `.planning/research/PITFALLS.md` with Phase 4 specifics added
- Plan-prep verifications: **HIGH** for A1/A2/A3/A6/A8 (verified this session); A4/A5/A7 ADJUSTED with evidence; A9-A12 NEW surfaced this session
- Code examples: **MEDIUM-HIGH** — pydantic class sketch, asyncio.gather shape, ship-approval frontmatter, event types all anchored to existing patterns; implementation details (exact field names, exact transitions) flagged for planner-refinement per CONTEXT "Claude's Discretion"

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (30 days — substrate is stable; no external docs to drift against)

---

*Phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification*
*Research gathered: 2026-04-21 via /gsd-research-phase (integrated)*
*Next: /gsd-plan-phase 4*
