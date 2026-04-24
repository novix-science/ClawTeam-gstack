# Phase 4: Interactive State Machines, Smart Review Routing & Cross-Agent Verification — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in 04-CONTEXT.md — this log preserves the alternatives considered during the autonomous `/gsd-discuss-phase 4 --auto` run.

**Date:** 2026-04-21
**Phase:** 04-interactive-state-machines-smart-review-routing-cross-agent-verification
**Mode:** `--auto` (autonomous autonomous-mode, recommended options auto-selected)
**Areas discussed:** state-machine persistence, review-router format, reviewer-decorrelation strategy, cross-agent verification primitive, always-human ship gate, `/investigate` auto-freeze, verification stringency, thrash+cascade event semantics

---

## Area 1 — State machine persistence & structure

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Extend SprintState | Add `skill_sessions: dict[str, SkillSessionState]` to the existing SprintState pydantic model | |
| (b) Per-skill state files under `sprints/<id>/skills/<skill>/<role>/state.json` (recommended) | Mirrors Phase 2's questions/, answers/, freeze.json sprint-sub-dir convention; file_locked + atomic_write_text | ✓ |
| (c) Embed state in question/answer markdown frontmatter | Every turn amends the question.md frontmatter; state lives in the artifact | |

**Auto-selected:** (b). **Reason:** Avoids SprintState schema churn; each skill owns its own pydantic model; survives `HarnessOrchestrator` restart via plain JSON; matches Phase 2's proven sub-dir layout.

---

## Area 2 — SmartReviewRouter rule format & wiring

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `[[template.review.rules]]` TOML in gstack.toml (recommended) | Additive TemplateDef extension; grep-friendly; non-Python users can tune routing | ✓ |
| (b) Python policy plugin | Rules declared as code; more expressive but requires code change to edit | |
| (c) External YAML file | Separate policy file referenced from gstack.toml | |

**Auto-selected:** (a). **Reason:** Matches Phase 3 D-06 + D-04 convention (grep-friendly, additive TOML, no parsing); tuning without code edits.

---

## Area 3 — Reviewer decorrelation prompt strategy

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Separate `prompts/review/<role>.md` files, appended at Review-phase by plugin (recommended) | Decorrelation decoupled from main prompt; per-persona tunable | ✓ |
| (b) Inline `REVIEW-DECORRELATION:` section in existing role prompt | One-file-per-role; tighter coupling | |
| (c) Config-string constants in plugin Python | No markdown; fastest to load | |

**Auto-selected:** (a). **Reason:** Matches Phase 3 D-06 prompt-file pattern; preserves 4 KB main-prompt budget; main-prompt collateral-free.

---

## Area 4 — Cross-agent verification gate primitive

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `CrossAgentVerificationGate(PhaseGate)` base class + per-pair verifier functions (recommended) | Mirrors EvidenceGate shape; reusable; pure-function verifiers | ✓ |
| (b) Extend EvidenceGate with `cross_verify` hook | Keeps gate count low; risks EvidenceGate schema churn | |
| (c) Register as phase event subscribers | No gate; purely advisory; weaker enforcement | |

**Auto-selected:** (a). **Reason:** Cleanest subclass hierarchy; reusable by non-gstack plugins; verifier functions are trivially testable.

---

## Area 5 — Always-human Ship gate mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Config flag `force_interactive_phases=["ship"]` honored by SprintConductor | Minimal new code; gate lookup via config | |
| (b) Dedicated `HumanApprovalGate(InteractionGate)` subclass attached to Ship phase (recommended) | Explicit primitive; reusable for other blast-radius phases; clearer call chain | ✓ |

**Auto-selected:** (b). **Reason:** SPRINT-05 override semantics need to ignore `auto_advance: true`; subclassing InteractionGate inherits the question-answer plumbing cleanly; additional `ship-approval.md` check is a single `check()` method override.

---

## Area 6 — `/investigate` auto-freeze mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| (a) State machine's enter/exit actions call FreezeRegistry.freeze/unfreeze explicitly (recommended) | Explicit; audit trail correlatable via reason string; no magic | ✓ |
| (b) Decorator `@auto_freeze(path)` on skill handler | Less boilerplate; harder to debug when it doesn't unfreeze | |

**Auto-selected:** (a). **Reason:** Reuses Phase 2 freeze_registry API + audit JSONL directly; explicit > implicit for safety-adjacent state; reason string structured for grep.

---

## Area 7 — Golden-trace verification strategy

| Option | Description | Selected |
|--------|-------------|----------|
| (a) Pure JSON fixtures of transition graphs + turn counts | Deterministic; cheap | |
| (b) Strategy A live sandbox runs against native gstack | High fidelity; expensive in CI; non-deterministic | |
| (c) Strategy B+ (markdown-derived + transition-graph JSON fixtures + turn-count assertions) (recommended) | Extends Phase 3 D-08; adds state-machine shape assertions | ✓ |

**Auto-selected:** (c). **Reason:** Strategy B locked at Phase 3 D-08 for content; Strategy B+ adds turn-count + transition-graph shape for state machines; deterministic + cheap + CI-friendly.

---

## Area 8 — Parallel reviewer execution model

| Option | Description | Selected |
|--------|-------------|----------|
| (a) `asyncio.gather` with isolated per-reviewer sub-conversations (recommended) | Real concurrency; real decorrelation; respects SprintConductor semaphore caps | ✓ |
| (b) Sequential with prompt-isolation flag | Simpler; risks residual conversation-state leakage | |

**Auto-selected:** (a). **Reason:** QUALITY-13 requires diverge-not-mirror findings; only real parallelism + prompt isolation achieves honest decorrelation. Sequential-with-prompt-isolation leaks through conversation state.

---

## Claude's Discretion

- Pydantic field names inside state-machine models (derived by planner from fixture JSON keys)
- Decorrelation rubric heading ordering inside `prompts/review/<role>.md`
- JSON payload key names for `mid_review_thrash` / `sycophancy_cascade_detected` events (sketched in CONTEXT specifics)
- Wave structure + parallelism of plans (planner determines from file dependencies)
- Per-plan split vs merge (CrossAgentVerificationGate+verifiers together or separate; /investigate declaration vs freeze-wiring)

## Deferred Ideas

- Phase 5: `/codex`, `/ship`, `/canary`, `/benchmark`, `/setup-deploy`, tool-integrated `/investigate`
- Phase 6: `/design-shotgun`, `/design-html`, real `TeamMemoryStore`, `/learn` backfill
- Phase 7: `AttentionQueue`, cost dashboard consumption of thrash/cascade events
- Post-v1: Strategy A golden traces, ML-based diff classification, multi-instance reviewer panels

---

*Autonomous run: 2026-04-21T16:19:56+08:00*
*All 8 areas auto-selected on recommended options.*
