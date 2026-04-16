# Phase 1: Core Harness Extensions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 01-core-harness-extensions
**Areas discussed:** SprintState ↔ PhaseState, Q/A file schema, Plugin phase-name collision, Q/A ID format

---

## Initial Gray Area Presentation

Four gray areas presented via AskUserQuestion (multiSelect):

| Gray Area | User Selection |
|-----------|----------------|
| SprintState ↔ PhaseState 关系 | (deferred — see user pushback) |
| Question/Answer 文件 schema | (deferred — see user pushback) |
| Plugin phase-name 冲突规则 | (deferred — see user pushback) |
| Question/Answer 文件 ID 格式 | (deferred — see user pushback) |

**User response:** "clawteam 自己没有这些拍板吗?"
**Interpretation:** Check the codebase for existing conventions before asking
the user to pick. Three of four areas turned out to have implicit answers from
existing ClawTeam code; only the schema was genuinely open.

---

## Codebase Resolution Pass

| Gray Area | ClawTeam-Existing Convention | Decision |
|-----------|------------------------------|----------|
| SprintState ↔ PhaseState | `PhaseState` (harness/phases.py:39) covers harness-run state; `SprintContract` (harness/contracts.py:25) covers sprint definition. No runtime-sprint-state model yet. | D-01: SprintState is a NEW independent model (runtime layer), composed with SprintContract, parallel to PhaseState. Not subclass, not replacement. |
| Plugin phase-name collision | `PluginManager._loaded: dict[str, HarnessPlugin]` (plugins/manager.py:17) enforces plugin-name uniqueness; `contribute_gates()` returns additive `dict[phase, list[gate]]` (plugins/base.py:35). Phase-name layer has no existing contract. | D-03: Global phase-name namespace, ValueError at registration. No plugin-name prefix — `Phase = str` stays open. Matches SC#2 and PluginManager spirit. |
| Q/A file ID format | `harness_id = uuid.uuid4().hex[:12]` (phases.py:42), `sprint_id = uuid.uuid4().hex[:8]` (contracts.py:28). | D-07: `uuid.uuid4().hex[:8]` for question id, slug in frontmatter not filename. Matches ClawTeam convention, concurrent-safe. |

---

## Genuinely Open Area: Q/A File Schema

| Option | Description | Selected |
|--------|-------------|----------|
| A — Pure markdown convention | H3 per question + numbered choices; parser does best-effort regex. gstack `/office-hours` flavor. Agent writes format by prompt. | |
| B — Pydantic + YAML frontmatter + markdown body | Agent builds `Question(...)` model → `to_markdown()` → file with `---yaml---` frontmatter (id, type, choices) and prose body. Parser reads frontmatter strictly; body is human-only context. | ✓ |

**User's choice:** B — pydantic + markdown hybrid.
**Notes:** Matches existing ClawTeam pydantic-first convention (SprintContract, PhaseState, SprintContract). Phase 4 `/office-hours` state machines get a stable parse contract. Keeps body prose human-readable for gstack-style Q&A feel.

**Captured as D-08.**

## Claude's Discretion

Deferred to planner:
- Exact extra fields inside `Question` / `Answer` pydantic models beyond the required set in D-08 (priority, urgency, tags) — add only if Phase 4 /office-hours design needs them.
- Test fixture layout for schema parse test (SC#5).
- File location of `ReviewRouter` Protocol (`clawteam/harness/review_router.py` vs alongside `phase_registry.py`).

## Deferred Ideas

- `ReviewRouter` full interface — Phase 4 RFC update.
- Question priority/urgency/tags — Phase 4 if needed.
- Sprint CLI, evidence gates, cycle detector, artifact caps — Phase 2+.
- InteractionGate auto-escalation to AttentionQueue — Phase 7.
