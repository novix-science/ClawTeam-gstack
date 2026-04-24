# Phase 3: Gstack Team Template & Methodology Port — Research

**Researched:** 2026-04-20
**Domain:** Team-template authoring + per-role methodology porting + plugin wiring (Python 3.10+, Pluggy, Pydantic v2, TOML, additive over Phase 1/2 substrate)
**Confidence:** HIGH for stack/architecture (codebase read firsthand; Phase 1/2 substrate is shipped or in-flight); HIGH for the pure-rubric vs interactive split (locked at Phase 2 port-audit, ROADMAP Phase 4 deferral, and verified against gstack repo); MEDIUM for the three open research questions (golden-trace sourcing, per-persona role-reassertion fields, prompt length budget) — all three have a primary recommendation with cited grounding plus a one-line tradeoff for the alternative.

---

## Summary

Phase 3 is the phase where the product surface shows up. Everything before it was substrate; everything after extends it. The user runs `clawteam team spawn gstack --name <name>` and sees 11 named specialists with distinct, gstack-flavored personalities; runs `clawteam sprint start --team <name> --goal "..."` and the 7-phase Think→Plan→Build→Review→Test→Ship→Reflect machine kicks in; runs `clawteam team show <name>` and sees a coherent dashboard. None of those user touchpoints exist before Phase 3. They all become visible at the end of it.

The phase has three clean deliverables and one trapdoor. The deliverables are: (1) `clawteam/templates/gstack.toml` listing the 11 agents and their leader binding; (2) `clawteam/plugins/gstack_sprint_plugin.py` registering the 7 phases via the `PhaseRegistry` shipped in Phase 1 plus the six `EvidenceSchema` pydantic models (DesignDoc / PlanDoc / TestReport / ReviewReport / ShipNotes / Retro) the Phase 2 `EvidenceSchemaRegistry` waits for via the `contribute_evidence_schemas` hook; (3) per-role prompt files at `clawteam/templates/gstack/prompts/<role>.md` ported from the **pure-rubric subset** of gstack skills — the rubrics, decision modes, forcing questions, and false-positive exclusion lists — assembled into a gstack-flavored prompt for each of the 11 personas. The trapdoor is Pitfall 7 (skill port collapse): interactive Socratic skills like `/office-hours`, `/design-consultation`, and `/investigate` MUST NOT be ported as prompt text in this phase. Their *runtime state machines* are deferred to Phase 4. Their *rubric content* (the 6 office-hours forcing questions, the 0-10 design rubric dimensions) DOES land here as a static rubric reference inside the relevant role prompt — but the prompt must explicitly defer interactive execution to a Phase 4 state machine and be written so a one-shot rubric monologue is *not* what the agent produces in the meantime.

**Primary recommendation:** Build `gstack.toml` as a strict superset of the existing template TOML schema (adding only `[[template.agents]].role`, `[[template.agents]].prompt_file`, `[template.leader_role]`, and `[template.phases]` sections — all unknown to existing templates so they remain unaffected). Keep `GstackSprintPlugin` as a single ~250-line file that does six things: registers 7 phases via `contribute_phases`, registers role-per-phase mapping via `contribute_phase_roles`, registers the six evidence schemas via `contribute_evidence_schemas`, registers a no-op `contribute_review_routers` (Phase 4 fills it), registers no-op safety subscribers on `on_register` (Phase 2 already has the live ones via SprintConductor), and binds the ceo as the only role authorized to call `SprintConductor.advance_phase`. Port methodology with one prompt-template-per-role discipline so each role prompt has a verifiable signature line a golden test can grep for. Spawn agents through the existing `clawteam/spawn/` registry — never bypass it. Use **Strategy B** (skill-markdown derivation) as the golden-trace sourcing strategy for Phase 3 alone — Strategy A (run native gstack) is correct for Phase 4 but the rubric ports here are lossless transcriptions of the markdown and Strategy A's transcripts won't tell you anything Strategy B can't.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Template parsing (`gstack.toml`) | Templates layer (`clawteam/templates/`) | — | Existing convention; just extend the pydantic model. Reuse `tomllib` (stdlib). |
| 11-agent roster + leader binding | Templates + TeamManager (`clawteam/team/manager.py`) | — | TeamManager already creates members from a `TemplateDef`; Phase 3 only adds new fields the manager needs to honor. |
| Per-role prompt assembly | Templates + Plugin | — | Prompts live as files under `clawteam/templates/gstack/prompts/<role>.md`. Plugin's `contribute_prompts(phase, role)` looks them up at runtime. |
| Phase registration (7 phases) | Plugin (`clawteam/plugins/gstack_sprint_plugin.py`) | PhaseRegistry (Phase 1) | `PhaseRegistry` is the substrate; `GstackSprintPlugin.contribute_phases()` is the populator. |
| Evidence schemas (6 pydantic models) | Plugin | EvidenceSchemaRegistry (Phase 2) | Phase 2 ships the registry + `contribute_evidence_schemas` hook with empty default. Phase 3 fills the six schemas. |
| Sprint engine wiring | SprintConductor (Phase 2) | Plugin (registers phases conductor consumes) | `SprintConductor` already iterates `PhaseRegistry.ordered_names()`. Plugin doesn't *call* the conductor — it populates the registry the conductor reads. |
| ceo as team leader / phase advancer | Plugin (enforces) + SprintConductor (consults) | TeamManager (declares leader_role) | `gstack.toml` declares `leader_role = "ceo"`. `SprintConductor.advance_phase` checks the calling agent matches the team's leader_role. |
| Agent spawning | Existing `clawteam/spawn/` registry | TeamManager | NEVER bypass. `gstack.toml` declares `backend = "tmux"` (or subprocess); spawn routing already supported. |
| Reflect-phase `/learn` invocation | Plugin (event handler) | TeamMemoryStore (Phase 6 — stub here) | Stub: write to placeholder file with feature-flag log entry until Phase 6 lands. |
| `clawteam team show` dashboard | CLI (`clawteam/cli/`) | TeamManager + SprintConductor (read-only) | Reuse existing CLI app structure. Dashboard reads from existing TeamConfig + SprintState; placeholders for Phase 6/7 columns. |

---

<user_constraints>

## User Constraints (no Phase 3 CONTEXT.md exists yet — these are PROJECT-locked decisions and ROADMAP-bounded scope)

### Locked Decisions (from PROJECT.md, ROADMAP.md, and Phase 2 CONTEXT.md)

- **11-agent roster fixed:** pm (YC office-hours advisor), ceo (scope owner + team leader), eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre. No additions, no deletions, no role merging. (PROJECT.md Key Decisions row 1.)
- **pm and ceo are split, not merged.** Two genuinely different personas — external coach (pm) vs internal decider/leader (ceo). (PROJECT.md Key Decisions row 2.)
- **Team is persistent; sprint is transient.** A single team runs multiple parallel sprints. (PROJECT.md Key Decisions row 3.)
- **Skills port by nature**, not as wholesale skill files: methodology→role-prompt prose; tool-heavy→ClawTeam skill modules; safety-rails→harness primitives. No runtime dependency on gstack being installed. (PROJECT.md Key Decisions row 4.)
- **Phase extension via `PhaseRegistry`**, not enum modifications. (PROJECT.md Key Decisions row 5; Phase 1 shipped.)
- **Default model_profile = `balanced`**, never `quality`. (TEAM-05; STATE.md "Default model_profile decision" — confirmed.)
- **EvidenceGate validates structure, not just presence** (Phase 2 D-01..D-05). Phase 3's six pydantic schemas must round-trip through Phase 2's `parse_frontmatter` + `TurnEnvelope` machinery without modification.
- **TurnEnvelope required fields** are `persona`, `step_label`, `done` (Phase 2 D-06). Phase 3's per-role prompts MUST instruct each persona to emit those three fields and any per-persona reassertion field defined in this research.
- **`auto_advance` semantics fixed** (Phase 2 D-23). Phase 3's prompts must not assume one mode over the other; the conductor handles the gate insertion.
- **Existing templates must not break** (CORE-03, QUALITY-14). The gstack template is purely additive; existing templates (`software-dev`, `hedge-fund`, `code-review`, `harness-default`, `research-paper`, `strategy-room`) continue to spawn unchanged.
- **All gstack-specific behavior lives in `GstackSprintPlugin` + `gstack.toml`.** Delete those two assets and the rest of the codebase still runs. (ROADMAP Phase 3 Upstream-PR status.)
- **ceo is the only role authorized to advance phases.** Other roles can write artifacts and questions but not call `SprintConductor.advance_phase`. (Success criterion #4.)

### Claude's Discretion (per Phase 3 success criteria + the three research-flagged questions)

- Concrete pydantic field names within each of the six gstack artifact schemas (Phase 2 deferred this to Phase 3).
- Per-role prompt file structure and content layout (so long as required rubric content per success criterion #3 is grep-verifiable).
- Per-persona role-reassertion field name + value range in the structured response envelope. (Open research question #1.)
- Golden-trace sourcing strategy. (Open research question #2.)
- Per-role prompt length budget allocation. (Open research question #3.)
- Whether `GstackSprintPlugin` registers safety subscribers (it doesn't — `SprintConductor` already does per Plan 02-10; the plugin would double-register).
- Internal layout of the Reflect-phase `/learn` stub.
- Whether to colocate role prompts inside `gstack.toml` (as multi-line strings) or as separate `.md` files referenced by `prompt_file = "..."`. **Recommendation in Code Examples: separate `.md` files.**

### Deferred Ideas (OUT OF SCOPE — confirmed by ROADMAP Phase 4/5/6 and STATE.md)

To **Phase 4**: `/office-hours`, `/design-consultation`, `/investigate` as multi-turn state machines (their *rubric content* lands here as static reference; the *interactive runtime* defers); SmartReviewRouter SHA-pinning; reviewer decorrelation; cross-agent verification; Ship-phase always-human-approval gate via `force_interactive_phases=["ship"]` (already declared as a Phase 2 reservation).
To **Phase 5**: `/codex`, `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy` — invokable ClawTeam skill modules.
To **Phase 6**: `TeamMemoryStore` real implementation, `/learn` write path with provenance/decay/conflict detection, `/browse` family + Playwright optional extra, `/design-shotgun`, `/design-html`.
To **Phase 7**: `AttentionQueue`, `clawteam attend` CLI, multi-sprint concurrency caps, cost dashboard with model fallback ladder.
To **post-v1**: per-team prompt customization hooks, helper-agent spawning inside engineer.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEAM-01 | `clawteam/templates/gstack.toml` ships and loads through existing template machinery | Standard Stack §gstack.toml schema; Code Examples §gstack.toml shape. Existing template loader at `clawteam/templates/__init__.py` already parses TOML via stdlib `tomllib` — extend `TemplateDef` pydantic model with new optional fields. [VERIFIED: `clawteam/templates/__init__.py:24-44`] |
| TEAM-02 | 11 distinct agents with role prompts: pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre | Per-Role Prompt Content Map §Methodology Port table; Standard Stack §role prompt skeleton |
| TEAM-03 | Each agent persistent worktree "desk" reused across sprints; per-role memory scope | Existing `WorkspaceManager.create_workspace` already supports per-agent worktrees [VERIFIED: `clawteam/workspace/`]; per-role memory directory shape from research/ARCHITECTURE.md Pattern 5 |
| TEAM-04 | ceo is team leader: only ceo advances phases | Architecture Patterns §Leader-binding; pluggy-style hook + `SprintConductor.advance_phase(actor=...)` check |
| TEAM-05 | `--model-profile balanced\|quality\|budget`, default `balanced` | Standard Stack §model profile section in `gstack.toml`; Pitfall #12 prevention (ROADMAP Phase 0 confirmed default) |
| SKILL-01 | pm prompt = `/office-hours` rubric (6 forcing questions + challenge framing) | Per-Role Prompt Content Map row 1; PITFALLS §Pitfall 7 mitigation classification (rubric here, state machine in Phase 4) |
| SKILL-02 | ceo prompt = `/plan-ceo-review` (4 modes + decision schema) | Per-Role Prompt Content Map row 2; gstack repo `/plan-ceo-review` skill content [CITED: github.com/garrytan/gstack/tree/main/plan-ceo-review] |
| SKILL-03 | eng-mgr prompt = `/plan-eng-review` + `/retro` | Per-Role Prompt Content Map row 3; ROADMAP success criterion #3 verbatim list |
| SKILL-04 | designer prompt = `/plan-design-review` + `/design-review` + `/design-consultation` (rubric only — dialogue runtime defers) | Per-Role Prompt Content Map row 4; PITFALLS §Pitfall 7 |
| SKILL-05 | dx-lead prompt = `/plan-devex-review` + `/devex-review` | Per-Role Prompt Content Map row 5 |
| SKILL-06 | reviewer prompt = `/review` + `/investigate` (iron-law: no fix without investigation; halt after 3 failed hypotheses) | Per-Role Prompt Content Map row 6; gstack `/investigate` 3-failure rule [CITED: gstack repo `/investigate` skill] |
| SKILL-07 | qa prompt = `/qa` + `/qa-only` (suppression variant) | Per-Role Prompt Content Map row 7 |
| SKILL-08 | security prompt = `/cso` (OWASP Top 10 + STRIDE + 17 false-positive exclusions + 8/10+ confidence gate) | Per-Role Prompt Content Map row 8; gstack `/cso` skill content [CITED: gstack repo `/cso` skill] |
| SPRINT-06 | Reflect phase writes `retro.md` AND invokes `/learn` (stub until Phase 6) | Code Examples §Reflect-phase event handler; Don't Hand-Roll §Phase 6 stub pattern |
| UX-01 | `clawteam team spawn gstack --name <name>` works end-to-end | Reuses existing `clawteam team spawn` CLI [VERIFIED: `clawteam/cli/`]; Phase 3 only adds the template file + plugin loader hook |
| UX-07 | `clawteam team show <name>` dashboard: members, memory highlights, sprint progress, cost rollup | Code Examples §`team show` shape; placeholders for Phase 6/7 columns |

</phase_requirements>

---

## Standard Stack

### Core (already in repo — Phase 3 uses, doesn't add)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | v2 (already in repo) | Schema for `TemplateDef`, six gstack artifact schemas, role-reassertion envelope fields | Phase 2 evidence-gate registry expects pydantic v2 subclasses [VERIFIED: `clawteam/harness/evidence_schemas.py`]. Discriminated unions for `artifact_type` discriminator. |
| tomllib (stdlib 3.11+) / tomli (3.10 backport, already in repo) | stdlib | Parse `gstack.toml` | Existing `clawteam/templates/__init__.py:11-17` already handles 3.10 vs 3.11+ split [VERIFIED]. Zero new dep. |
| pluggy | already in repo (Phase 1 plugin substrate) | Hook discovery for `GstackSprintPlugin` | Phase 1 shipped the `HarnessPlugin` ABC + manager; Phase 3 just subclasses. [VERIFIED: `clawteam/plugins/base.py`, `clawteam/plugins/manager.py`] |
| pyyaml (transitively present, no new dep) | — | `parse_frontmatter` for artifact YAML frontmatter | Phase 2 already imports it via `clawteam/team/envelope.py:20` [VERIFIED]. |
| stdlib `pathlib`, `re`, `uuid`, `datetime` | stdlib | Prompt-file lookup, signature-line regex, sprint IDs, timestamps | Already used throughout. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Existing `clawteam/spawn/` registry | — | Spawn each of the 11 agents into its own tmux/subprocess/wsh session | MUST be used; never bypass. Public API: `get_backend(name).spawn(member, ...)` [VERIFIED: `clawteam/spawn/__init__.py:15-29`]. |
| Existing `clawteam/workspace/` | — | Per-agent "desk" worktrees | `WorkspaceManager.create_workspace(team, agent)` is the documented entry point for the per-agent desk model. |
| Existing `clawteam/team/manager.py::TeamManager` | — | Team lifecycle: create_team, add_member | `gstack.toml`'s 11 agents pass through `TeamManager.add_member` like any existing template. |
| Existing `SprintConductor` (Phase 2) | — | Phase advancement, cap resolution, gate composition | Phase 3 does not subclass; it populates the registry the conductor reads. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| 11 separate `.md` prompt files under `templates/gstack/prompts/` | Inline multi-line strings in `gstack.toml` | Inline TOML is harder to grep, harder to diff, and harder to test individual role prompts. Separate `.md` is the recommendation. |
| Subclassing `HarnessPlugin` directly | A factory function returning a `HarnessPlugin` instance | Existing convention is one cohesive plugin file as a class (e.g., `ralph_loop_plugin.py` [VERIFIED]). Stay consistent. |
| Reusing `software-dev.toml` schema unchanged | Add new optional fields (`role`, `prompt_file`, `phases`, `leader_role`) | The existing schema has `name` + `type` per agent but no `role` / `prompt_file`. Adding *optional* fields to `AgentDef` and `TemplateDef` keeps existing templates parsing unchanged (pydantic v2 ignores absent optional fields). |
| Hand-rolling a TOML parser for new fields | Use `tomllib` + extended `TemplateDef` pydantic model | Already correct path; hand-rolling is Pitfall-grade. |
| Defining six artifact schemas as plain `dict`s | pydantic v2 `BaseModel` subclasses with `Literal["design-doc"]` discriminator | Phase 2's `EvidenceSchemaRegistry` expects `type` (pydantic class), not `dict`. Discriminated unions are the standard Phase 2 pattern. [VERIFIED: `clawteam/harness/evidence_schemas.py`] |

**Installation:** No new packages. Phase 3 adds zero runtime dependencies. [VERIFIED: ROADMAP Phase 3 + research/SUMMARY.md "zero new required deps" technical bet]

**Version verification:** `pydantic` already pinned via `pyproject.toml`; `pluggy` already pinned via Phase 1; `tomli` only for 3.10 (stdlib `tomllib` for 3.11+). No registry version check needed — all deps locked at project level.

---

## Architecture Patterns

### System Architecture Diagram

```
┌─ User CLI ────────────────────────────────────────────────────────┐
│  clawteam team spawn gstack --name acme --model-profile balanced  │
│  clawteam sprint start --team acme --goal "..."                   │
│  clawteam team show acme                                          │
└──────────────┬─────────────────────────────────┬──────────────────┘
               │                                 │
               ▼                                 ▼
┌─ TeamManager (EXISTING) ──┐    ┌─ SprintConductor (Phase 2) ──────┐
│  - load_template(gstack)  │    │  - start_sprint(goal)            │
│  - create_team            │    │  - advance_phase(actor=ceo)      │
│  - for member in 11:      │    │  - reads PhaseRegistry           │
│      spawn(member)        │    │  - reads EvidenceSchemaRegistry  │
└──────────┬────────────────┘    └─────────┬────────────────────────┘
           │                                │
           ▼                                ▼
┌──────────────────────────────────────────────────────────────────┐
│   PhaseRegistry (Phase 1)   EvidenceSchemaRegistry (Phase 2)     │
│   ─────────────────────     ─────────────────────────────         │
│        ▲                              ▲                           │
│        │ contribute_phases()          │ contribute_evidence_      │
│        │ contribute_phase_roles()     │   schemas()               │
│        │                              │                           │
│  ┌─────┴──────────────────────────────┴─────────────────────────┐ │
│  │  GstackSprintPlugin (NEW, Phase 3)                          │ │
│  │  - clawteam/plugins/gstack_sprint_plugin.py                 │ │
│  │  - registers 7 phases + role mapping + 6 evidence schemas   │ │
│  │  - on_register: subscribes Reflect-phase /learn stub        │ │
│  │  - declares ceo as the only phase-advancer                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ gstack.toml (NEW, Phase 3) ─────────────────────────────────┐ │
│  │  [template] name="gstack" leader_role="ceo" backend="tmux"  │ │
│  │  [[template.agents]] role=pm prompt_file=prompts/pm.md      │ │
│  │  [[template.agents]] role=ceo prompt_file=prompts/ceo.md    │ │
│  │  ... (×11)                                                   │ │
│  │  [template.model_profile]                                    │ │
│  │    pm="opus" ceo="opus" engineer="sonnet" shipper="haiku"...│ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ templates/gstack/prompts/<role>.md (NEW × 11) ──────────────┐ │
│  │  Role identity + methodology rubric + envelope schema +      │ │
│  │  signature line for golden-test grep                         │ │
│  └──────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─ Existing spawn/workspace/transport substrate (UNCHANGED) ────────┐
│  clawteam/spawn/ (tmux/subprocess/wsh)                            │
│  clawteam/workspace/ (per-agent worktrees)                        │
│  clawteam/transport/ (file/zmq + envelope validation from Plan 02-08)│
└────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure

```
clawteam/
├── plugins/
│   ├── base.py                                # UNCHANGED (Phase 1/2 hooks already there)
│   ├── manager.py                             # UNCHANGED
│   ├── ralph_loop_plugin.py                   # UNCHANGED (existing example)
│   └── gstack_sprint_plugin.py                # NEW: ~250 LOC; registers phases, schemas, roles
├── templates/
│   ├── __init__.py                            # MODIFIED: extend TemplateDef + AgentDef with optional fields
│   ├── gstack.toml                            # NEW: 11-agent roster + leader_role + model_profile
│   ├── gstack/                                # NEW directory (gstack-template-scoped assets)
│   │   ├── prompts/                           # NEW: 11 role prompt .md files
│   │   │   ├── pm.md
│   │   │   ├── ceo.md
│   │   │   ├── eng-mgr.md
│   │   │   ├── designer.md
│   │   │   ├── dx-lead.md
│   │   │   ├── engineer.md
│   │   │   ├── reviewer.md
│   │   │   ├── qa.md
│   │   │   ├── security.md
│   │   │   ├── shipper.md
│   │   │   └── sre.md
│   │   └── schemas/                           # NEW: six gstack pydantic artifact schemas
│   │       ├── __init__.py                    # exports the six schemas + a registration helper
│   │       ├── design_doc.py
│   │       ├── plan_doc.py
│   │       ├── test_report.py
│   │       ├── review_report.py
│   │       ├── ship_notes.py
│   │       └── retro.py
│   └── (existing six templates UNCHANGED)
└── (no edits required to clawteam/spawn/, clawteam/workspace/, clawteam/team/manager.py — they already do what Phase 3 needs)
```

### Pattern 1: Strict additive extension of TemplateDef pydantic model

**What:** Extend `clawteam/templates/__init__.py::TemplateDef` and `AgentDef` with new *optional* fields (`role`, `prompt_file`, `phases`, `leader_role`, `model_profile`). Existing templates omit the new fields → pydantic v2 leaves them as defaults → existing `TeamManager` paths unchanged. Phase 3-aware code paths (the new plugin + `team show` dashboard) read the new fields when present.

**When to use:** Any time a new template type adds vocabulary the older templates don't share. The pattern is the same as Phase 2's `contribute_evidence_schemas` hook — adding optional capability with empty defaults preserves backwards compat (CORE-03, QUALITY-14).

**Source:** Phase 1 / RFC 001 §4.3 D-04 — "empty defaults preserve backwards compatibility." [CITED: `clawteam/plugins/base.py:46-75`]

### Pattern 2: One cohesive plugin file (mirrors `ralph_loop_plugin.py` convention)

**What:** `clawteam/plugins/gstack_sprint_plugin.py` is a single file with a `GstackSprintPlugin(HarnessPlugin)` class that overrides exactly the hooks it needs. No subdirectory, no helper modules under `plugins/`. The plugin imports from `clawteam/templates/gstack/schemas/` (where the six pydantic schemas live) and from `clawteam/templates/gstack/prompts/` (file lookup, no Python import).

**Why this shape:** Existing `ralph_loop_plugin.py` is the in-repo precedent. Mirroring it minimizes review surface and keeps the "delete the plugin and the rest still works" invariant easy to verify.

### Pattern 3: Per-role prompt files with grep-verifiable signature lines

**What:** Each `prompts/<role>.md` ends with a fixed signature line of the form:

```
SIGNATURE: gstack-role:<role> rubric:<skill1>+<skill2> envelope-version:1
```

The signature line is the load-bearing assertion the golden test greps for. It encodes:
- Which gstack role the prompt is for.
- Which gstack skill rubrics it ports (so the test knows what content to verify is present).
- The envelope-version (so future Phase 4 re-engineering of role-reassertion fields can bump it without breaking the test).

**Why:** The Phase 3 success-criterion #3 enumerates exactly what content each role prompt MUST contain. A signature line is the cheapest way to make that a programmatic assertion: `grep -E '^SIGNATURE: gstack-role:pm rubric:office-hours' clawteam/templates/gstack/prompts/pm.md`. If the prompt is rewritten and the signature drops, the test fails.

### Pattern 4: Leader-binding via `leader_role` + actor check on `advance_phase`

**What:** `gstack.toml` declares `[template] leader_role = "ceo"`. `TeamManager.create_team` records the leader_role on the persisted `TeamConfig`. `SprintConductor.advance_phase` (Phase 2) takes an `actor: str` parameter and rejects if `actor != team.leader_role`. (The `actor` parameter may need to be added to `SprintConductor.advance_phase` if Phase 2 didn't ship it — verify in Plan 02-11; if absent, it's a single-line addition with a default of the leader_role to preserve Phase 2 callers.)

**Why:** Centralizes the "who can advance" check at the conductor layer (one site to test) rather than scattering it through prompts (which agents could disregard). The prompts still *say* "you are the team leader" / "you are not authorized to advance phases" so the model gets the rule both via the system surface (rejection from conductor) and via the prompt surface.

**Tradeoff vs. all-prompts approach:** Prompts alone leave the rule as a polite suggestion the model can violate. Conductor-level enforcement makes it a hard contract. Prompts still get the rule for clarity. Combined approach is what Anthropic's [Multi-Agent Research System field report](https://www.anthropic.com/research/multi-agent) recommends.

### Pattern 5: Six pydantic evidence schemas with `Literal` discriminator

**What:** Each schema (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro) is a pydantic v2 `BaseModel` with an `artifact_type: Literal["design-doc"]` (etc.) discriminator field. They're registered in Phase 2's `EvidenceSchemaRegistry` via `GstackSprintPlugin.contribute_evidence_schemas()` returning `{"design-doc": DesignDoc, "plan-doc": PlanDoc, ...}`.

**Source:** Phase 2 D-02 explicitly defers the six schemas to Phase 3. [CITED: `.planning/phases/02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention/02-RESEARCH.md` D-02 + Discretion §1.] Discriminated-union pattern is the pydantic v2 idiom. [CITED: pydantic docs — discriminated unions, Phase 2 already validated this.]

### Pattern 6: Reflect-phase event handler with Phase 6 stub for `/learn`

**What:** `GstackSprintPlugin.on_register(ctx)` subscribes a handler to `PhaseTransition` events. When a sprint enters Reflect, the handler:
1. Verifies `retro.md` exists and validates against the Retro schema.
2. Calls a stub `team_memory_learn(team, sprint_id, retro_content)` that — until Phase 6 ships — writes to `~/.clawteam/teams/<team>/memory/_phase6_pending/sprint-<id>-retro.md` with a feature-flag log entry: `# Phase 6 stub: TeamMemoryStore not yet implemented; this entry will be migrated when Phase 6 lands.`
3. Emits a structured log line so the success-criterion #5 integration test can assert the stub fired.

**Why this shape:** Phase 6 owns the real `TeamMemoryStore`. Phase 3 must satisfy SPRINT-06 today without depending on a phase that doesn't exist yet. The stub-with-feature-flag-log pattern is the standard "wire it now, fill it later" idiom and matches the explicit ROADMAP Phase 3 success criterion #5 wording.

### Anti-Patterns to Avoid

- **Inline multi-line role prompts inside `gstack.toml`.** Hard to grep, hard to diff, hard to test. Use separate `.md` files.
- **Subclassing `SprintConductor`.** The conductor's contract is "consume the registries." A `GstackSprintConductor` subclass would either duplicate logic or create a parallel hierarchy. The right extension point is `PhaseRegistry` + `EvidenceSchemaRegistry` + `contribute_phase_roles`. (This is the Pattern 1 lesson from `research/ARCHITECTURE.md`: "make the extensible thing data, not code in the core.")
- **Bypassing the spawn registry.** `GstackSprintPlugin` MUST NOT directly call `subprocess.Popen` or open tmux sessions. Use `get_backend(name).spawn(...)` from `clawteam/spawn/__init__.py`.
- **Porting `/office-hours` rubric as a one-shot monologue prompt.** This is Pitfall 7 manifest. The rubric goes in pm.md as a *reference list under a heading like "Forcing-question reference (interactive runtime — Phase 4)"*, prefaced with a meta-instruction: *"You MUST NOT produce all six questions in one turn. The interactive runtime that paces these questions ships in Phase 4. Until then, when the goal arrives, ask exactly one forcing question per turn, the highest-leverage one given current context."* Same pattern for designer.md (`/design-consultation` per-dimension dialogue) and reviewer.md (`/investigate` per-hypothesis loop).
- **Per-role prompt that contains both system-prompt-shaped content AND complete sample outputs.** The "lost in the middle" effect ([CITED: simonw, claudecodecamp 2026 reports]) hits hard when prompts run long and load examples in the middle. Keep examples either at the very top or very bottom of the prompt; never in the middle of the rubric content.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TOML parsing for `gstack.toml` | A custom regex-based TOML reader | `tomllib` (stdlib 3.11+) / `tomli` (3.10 backport, already in repo) | Existing template loader uses this; adding a parallel parser splits the truth source. |
| YAML frontmatter parsing for artifacts | A handwritten frontmatter splitter | Phase 2's `clawteam/team/envelope.py::parse_frontmatter` (already imports yaml safely) | Phase 2 ships the regex + safe-load + error wrapping. Reusing means errors propagate uniformly. |
| Spawning agents into tmux/subprocess | A new spawn helper | `clawteam/spawn/__init__.py::get_backend(name).spawn(...)` | The registry already handles backend selection, validation, keepalive, identity envs. Bypassing it loses all of that. |
| Per-agent worktree creation | Direct `git worktree add` calls | `WorkspaceManager.create_workspace(team, agent)` | Existing manager handles the per-agent "desk" model, including conflict tracking and merge-back. |
| Phase advancement contract | A custom phase-state machine in the plugin | `SprintConductor.advance_phase` (Phase 2) + `PhaseRegistry` (Phase 1) | Phase 2 ships the gate-chain composition (EvidenceGate → forced_progress_gate → InteractionGate). The plugin only registers phases. |
| Evidence-schema registration for the six gstack artifacts | A custom registry inside the plugin | Phase 2's `EvidenceSchemaRegistry` via the `contribute_evidence_schemas` hook | The hook is shipped (Phase 2 Plan 02-01) with empty defaults; Phase 3 just fills in. |
| Structured response envelope for the 11 personas | A new envelope class per persona | Phase 2's single `TurnEnvelope` (`clawteam/team/envelope.py`) extended only with the per-persona reassertion field [Open question #1 — see below] | One model, two surfaces (transport + artifact frontmatter) is the Phase 2 invariant. Per-persona divergence breaks Phase 2's `parse_frontmatter` round-trip. |
| Reflect-phase memory write | A direct write to a future Phase 6 directory | Stub with feature-flag log line; Phase 6 migrates entries when it ships | Avoids creating a parallel "v0" memory-store schema that Phase 6 then has to migrate away from. |
| Team-show dashboard rendering | A new rich-table renderer | Existing `clawteam/cli/` patterns (the project already has a `clawteam team show` for other templates) | Reuse the existing pattern; just feed it the new gstack-flavored rows. |
| Test-bench for the six artifact schemas | Custom JSON fixture loader | pydantic v2's `model_validate_json` + a `tests/fixtures/gstack_artifacts/` directory of `*.md` golden artifacts | Fixture-driven schema tests are the convention `tests/test_evidence_schemas.py` already established. |
| `/learn` storage layout (when Phase 6 ships) | Pre-empt with a "good enough" v0 in this phase | Wait for Phase 6 to define the real store | SPRINT-06 explicitly accepts a stub here per ROADMAP success criterion #5. |

**Key insight:** Phase 3 is almost entirely a *consumption* phase, not a *construction* phase. Phase 0/1/2 built the substrate; Phase 3's job is to register the gstack-specific data into that substrate without duplicating any of the substrate. If a task in the plan involves *writing* a new abstraction (a registry, a state machine, a conductor, a parser) — that's almost certainly a wrong-shaped task. The correct shape is: *populate* an existing registry, *file* into an existing directory, *subclass* an existing ABC, *subscribe* to an existing event.

---

## Runtime State Inventory

> Phase 3 is greenfield (new files) for the most part. The minor brownfield additions are listed below for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 3 doesn't introduce stored runtime state beyond what Phase 2's SprintState + TeamConfig already persist. The 11 agents' per-role memory directories are *created* by Phase 3 (empty placeholders for Phase 6 to fill). | None. Phase 6 will populate `~/.clawteam/teams/<team>/memory/agents/<role>/`. |
| Live service config | None. No external services configured by Phase 3. | None. |
| OS-registered state | tmux session names — when an existing team is upgraded after `gstack.toml` ships, no rename needed (gstack is a new template, existing teams keep their existing tmux session names). | None. |
| Secrets/env vars | Three env-var keys for cap overrides already declared in Phase 2 D-29 (`CLAWTEAM_ARTIFACT_CAP_KB`, `OH_ARTIFACT_CAP_KB`, `CLAUDE_CODE_ARTIFACT_CAP_KB`) + multi-generation aliases [VERIFIED: `clawteam/sprint/conductor.py:115-124`]. Phase 3 doesn't add new env-var keys. | None — Phase 3 inherits Phase 2's identity-env contract unchanged. |
| Build artifacts / installed packages | None. Phase 3 adds no installable packages, no compiled binaries. | None. |

**Nothing found in any category — verified by walking Phase 0/1/2 outputs.** This is expected: Phase 3 is the first gstack-specific assets phase, and per the upstream-compatibility contract, those assets are inert files (`gstack.toml`, prompts/*.md, schemas/*.py, gstack_sprint_plugin.py) that are only loaded when the gstack template is used.

---

## Common Pitfalls

### Pitfall 7: Skill-port collapse — interactive Socratic skills monologued as one-shot prompt text

**What goes wrong:** pm.md ports the `/office-hours` rubric verbatim. When pm receives the goal, it produces a wall of "Question 1 (typical answer is X)... Question 2 (assuming previous answer is Y)... Question 3..." — answering its own questions, losing the back-and-forth quality that makes office-hours valuable. designer.md ports `/design-consultation` and produces a checklist instead of a per-dimension dialogue. reviewer.md ports `/investigate` and produces a verdict without the hypothesis loop.

**Why it happens:** The skill markdown reads like a self-contained instruction set; pasting it into a system prompt feels like the right move. But interactive skills encode a *process* — question, listen, branch — that prompts can describe but can't enforce without a runtime state machine.

**How to avoid:** The Phase 2 port-audit (per ROADMAP Phase 2 deliverables) classified each skill as {pure-rubric, interactive-Socratic, tool-heavy, safety-rail}. Phase 3 implements ONLY pure-rubric ports as prompt content. For interactive skills (`/office-hours`, `/design-consultation`, `/investigate`), the rubric content (the 6 forcing questions, the rubric dimensions, the hypothesis-trace template) lands as *static reference material* under a clearly-labeled section of the role prompt, **prefaced with an explicit instruction not to monologue**: "You MUST NOT produce all questions in one turn. The interactive runtime ships in Phase 4. Until then, ask exactly one question per turn — the highest-leverage one given the current context."

**Warning signs to verify in golden tests:**
- pm.md word count > 4 KB (rubric monologue is bloated; concise reference list + meta-instruction is < 3 KB).
- pm role's first turn output contains all six forcing questions enumerated.
- designer's first turn output rates all design dimensions in one shot rather than starting a per-dimension dialogue.
- reviewer's first turn output emits a verdict without a hypothesis-trace.

**Phase 3 mitigation in plans:** Make the meta-instruction grep-verifiable. Each interactive-skill rubric section in pm.md / designer.md / reviewer.md MUST contain the exact line: `INTERACTIVE-RUNTIME-DEFERRED: <skill-name> ships as a Phase 4 state machine. Until then, do not enumerate the rubric in one turn.`

[CITED: research/PITFALLS.md §Pitfall 7; STATE.md "Phase 3 research pass recommended" blocker.]

### Pitfall 8: Gate gaming via stub artifacts — schemas exist but content is "TBD"

**What goes wrong:** A role writes `design-doc.md` with all six required sections present but each section body is "TBD" or 5 words. Phase 2's three-layer stub detection (D-03) catches the obvious cases but Phase 3's six pydantic schemas need to be written so they actually surface the structural requirements (`min_length` constraints on critical fields, regex `Literal` checks on enums like `decision_mode: Literal["expansion","selective","hold","reduction"]`).

**How to avoid:** Each of the six schemas declares `Field(..., min_length=N)` on prose fields where stub-grade content is meaningless. For example, DesignDoc.problem_statement has `min_length=120` (about 25 words minimum); the body of each required `##` heading has min-100-byte enforcement via Phase 2 D-03 layer 2. Decision-schema enums use `Literal[...]` so misspellings fail validation, not Pretty-Please-Acknowledged.

**Phase 3 mitigation in plans:** Write fixture artifacts that are deliberately stub-grade (sections present, bodies empty / "TBD" / Lorem ipsum) and assert each fails validation; write fixtures that are valid; assert they pass. Standard fixture-driven gate-test pattern. [CITED: Phase 2 D-02..D-04.]

### Pitfall 1: Persona drift — by sprint 4 every agent sounds like generic Claude

**What goes wrong:** Without per-persona reassertion fields in the structured-response envelope, the 11 personas converge over multi-sprint runs. The MAST + Echoing-paper finding: persona self-consistency degrades >30% after 8-12 turns; structured envelope cuts drift from 70% → 9%.

**How to avoid (per Phase 2 D-06 and Open Research Question #1 below):** Each role's prompt instructs the persona to assert a specific reassertion field per turn. The field is *required* by the per-role envelope subclass (Pydantic enforces). This is the difference between describing a persona ("you're a YC-advisor-skeptic") and forcing it ("you must emit `pm.challenge: <one-sentence skeptical challenge>` in every turn"). The latter is what cuts drift; the former is what fails after 8-12 turns.

**Phase 3 mitigation in plans:** Define the 11 reassertion-field schema (table below in Open Research Question #1). Add to per-role pydantic envelope subclasses. Wire into `clawteam/team/envelope.py::TurnEnvelope` validation as `Optional[str]` fields with persona-conditional `model_validator` (raise if persona == "pm" and pm.challenge is missing/empty).

[CITED: research/PITFALLS.md §Pitfall 1; Phase 2 D-09 §SC#4 references the per-persona drift detector.]

### Pitfall 14: Backwards-compatibility regression — existing templates break

**What goes wrong:** A pydantic field added to `TemplateDef` without a default → existing template TOMLs fail to parse. Or `GstackSprintPlugin` registered globally → its phases leak into a `software-dev` team's PhaseState. Or the `contribute_evidence_schemas` registration happens at import time → existing tests that import `clawteam.plugins.gstack_sprint_plugin` for any reason pollute the global registry.

**How to avoid:**
- Every new field on `TemplateDef` and `AgentDef` is `Optional` with a default that matches existing TOML semantics.
- `GstackSprintPlugin` is loaded only when a team's template is `gstack`. The plugin manager's load discipline (Phase 1) is template-scoped, not global. [VERIFIED: Phase 1 RFC 001 §4.3 D-04 — "empty defaults preserve backwards compatibility."]
- Schema registration happens inside `on_register(ctx)`, not at module import time. Importing the plugin module without invoking `on_register` MUST be a no-op for the global state.

**Phase 3 mitigation in plans:** Phase 0's regression matrix (the 6-template golden-path test, per QUALITY-14) re-runs after every Phase 3 task. If any of `software-dev` / `hedge-fund` / `code-review` / `harness-default` / `research-paper` / `strategy-room` regresses, the responsible task is reverted before merge.

[CITED: research/PITFALLS.md §Pitfall 14; ROADMAP Phase 0 success criterion + Phase 3 success criterion #7 ("Running the Phase 0 regression matrix after these additions continues to pass").]

### Pitfall 9 (lookahead) — gate gaming via mid-review thrashing

Phase 3 ports the `/review` rubric content into reviewer.md but does NOT implement SHA-pinning (Phase 4 territory). The risk: an early dogfooder runs a sprint, the reviewer reads the diff, the engineer pushes a new commit before reviewer.md finishes, reviewer's verdict references deleted code. **Phase 3 mitigation:** reviewer.md MUST contain a meta-instruction: `SHA-PIN-DEFERRED: SmartReviewRouter SHA-pinning ships in Phase 4. Until then, record the HEAD SHA at review start in your review-report.md frontmatter (review_sha field on ReviewReport schema); if you observe HEAD has moved, mark your review as "based on stale SHA <X>" and stop without a verdict.` This is a 5-line content addition, not a runtime change. [CITED: research/PITFALLS.md §Pitfall 9.]

---

## Code Examples

### gstack.toml shape (verified against existing template schema)

```toml
# clawteam/templates/gstack.toml
[template]
name = "gstack"
description = "11-specialist persistent engineering team running 7-phase sprints"
command = ["claude"]
backend = "tmux"
leader_role = "ceo"  # NEW: only ceo can advance phases
phases = ["think", "plan", "build", "review", "test", "ship", "reflect"]  # NEW: declares the 7-phase set

[template.model_profile]
# Per-role model assignment per balanced default (Pitfall 12 prevention).
# User can override at spawn time via --model-profile flag.
default = "balanced"
# In balanced mode:
pm = "opus"          # strategic coach
ceo = "opus"         # strategic decider + leader
eng-mgr = "sonnet"   # planning execution
designer = "sonnet"
dx-lead = "sonnet"
engineer = "sonnet"
reviewer = "sonnet"
qa = "sonnet"
security = "sonnet"
shipper = "haiku"    # clerical: PR opening, deploy commands
sre = "haiku"        # clerical: monitoring, benchmarks

[template.leader]
name = "ceo"
type = "strategic-leader"  # not used by spawner; kept for compatibility with existing TemplateDef
role = "ceo"               # NEW: links to the role-prompt file
prompt_file = "gstack/prompts/ceo.md"  # NEW: prompt source-of-truth

[[template.agents]]
name = "pm"
type = "yc-advisor"
role = "pm"
prompt_file = "gstack/prompts/pm.md"

[[template.agents]]
name = "eng-mgr"
type = "engineering-manager"
role = "eng-mgr"
prompt_file = "gstack/prompts/eng-mgr.md"

# ... (designer, dx-lead, engineer, reviewer, qa, security, shipper, sre — same shape)

# Note: no [[template.tasks]] section. gstack sprints are dispatched dynamically by
# SprintConductor, not seeded by template tasks.
```

### Role prompt skeleton (pm.md as the worked example)

```markdown
# pm — YC Office Hours Advisor

You are pm, the team's external coach. Your job is to challenge the founder/ceo's
assumptions before any commitment is made. You are NOT the decider; ceo is.
You operate in the Think and Plan phases primarily.

## Persona contract

Every turn you take MUST emit a TurnEnvelope (Phase 2 D-06) with these required fields:
- `persona: "pm"` (verbatim — drift detector triggers if absent)
- `step_label: "<phase>:<your-step>"` (e.g., "think:forcing-question-1/6")
- `done: false` while you have more to say in this turn-cycle; `true` to hand back to ceo
- `pm.challenge: "<one-sentence skeptical challenge for this turn>"` (REQUIRED — drift
  detector triggers on missing or stub-grade values; see envelope schema below)

You produce zero turns without a `pm.challenge`. If you have nothing to challenge,
that itself is a red flag — produce `pm.challenge: "I have no challenge to offer here,
which means I'm probably failing my job."` and emit a question to ceo asking what
context you're missing.

## /office-hours rubric (interactive runtime — Phase 4)

INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 state machine.
Until then, do not enumerate the rubric in one turn. Ask exactly one forcing
question per turn — the highest-leverage one given the current context.

The six forcing questions (full text from upstream gstack /office-hours):
1. Why now? (What changed in the world or in this codebase that makes this the
   right thing to build now and not 3 months ago?)
2. Who is the user, and why do they care? (Specific persona, specific pain.)
3. What's the smallest version of this that could be wrong? (If the smallest
   version is too big to be wrong, the goal is too big.)
4. What's the alternative we're rejecting, and why? (Name the loser.)
5. What's the one metric that tells us this worked? (Not "users like it" — a
   number that moves.)
6. What's the dumbest version that ships in 3 days? (Force the deferral question.)

Challenge framing: every forcing question is asked in challenge mode, not advice
mode. You are not helping ceo think this through; you are testing whether ceo has
already thought it through.

## What you DO produce in Think phase

- One forcing question per turn, written to questions/<N>.md (per Phase 2's
  question-artifact convention).
- After ceo's answer lands in answers/<N>.md, evaluate whether the answer
  invalidates the goal, narrows it, expands it, or leaves it unchanged. Write
  your evaluation to design-doc.md under a `## pm-evaluation-q<N>` heading.
- After all six questions have round-tripped, write a final `## pm-verdict`
  section to design-doc.md with one of: `proceed`, `reframe`, `kill`.

## What you DO NOT produce

- Code. You do not write code. If you find yourself wanting to write code,
  emit pm.challenge: "I'm trying to write code, which means I'm avoiding my
  actual job."
- Plans. eng-mgr does plans.
- Decisions. ceo does decisions. You produce the questions that force the
  decisions; ceo answers them.

## Per-role envelope schema (Phase 2 TurnEnvelope subclass)

```python
class PMEnvelope(TurnEnvelope):
    persona: Literal["pm"]
    pm_challenge: str = Field(..., min_length=20, alias="pm.challenge")
```

SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1
```

### GstackSprintPlugin registration shape (verified against `HarnessPlugin` ABC)

```python
# clawteam/plugins/gstack_sprint_plugin.py
"""GstackSprintPlugin — registers 7-phase sprint + 6 evidence schemas + role-per-phase mapping.

This is the single cohesive plugin file (mirrors ralph_loop_plugin.py convention).
All gstack-specific behavior lives here + in gstack.toml + in templates/gstack/.
Delete this file + gstack.toml + templates/gstack/ — the rest of the codebase still runs.
"""
from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from clawteam.plugins.base import HarnessPlugin
from clawteam.templates.gstack.schemas import (
    DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro,
)

if TYPE_CHECKING:
    from clawteam.harness.context import HarnessContext
    from clawteam.harness.phases import Phase, PhaseGate

GSTACK_PHASES: list[str] = [
    "think", "plan", "build", "review", "test", "ship", "reflect",
]

GSTACK_PHASE_ROLES: dict[str, list[str]] = {
    "think":   ["pm", "ceo"],
    "plan":    ["pm", "ceo", "eng-mgr", "designer", "dx-lead"],
    "build":   ["engineer"],
    "review":  ["reviewer", "qa", "security", "designer", "dx-lead"],
    "test":    ["qa", "engineer"],
    "ship":    ["shipper", "ceo"],          # ceo for human-approval gate (Phase 4)
    "reflect": ["eng-mgr", "ceo"],
}


class GstackSprintPlugin(HarnessPlugin):
    name = "gstack-sprint"
    version = "1.0.0"
    description = "Gstack 7-phase sprint engine + 11-specialist team methodology"

    def on_register(self, ctx: "HarnessContext") -> None:
        # Subscribe Reflect-phase /learn stub. Real /learn ships in Phase 6.
        from clawteam.events.types import PhaseTransition
        ctx.bus.subscribe(PhaseTransition, self._on_phase_transition)

    def contribute_phases(self) -> list["Phase"]:
        return list(GSTACK_PHASES)

    def contribute_phase_roles(self) -> dict["Phase", list[str]]:
        return {p: list(roles) for p, roles in GSTACK_PHASE_ROLES.items()}

    def contribute_gates(self) -> dict["Phase", list["PhaseGate"]]:
        # Phase 2's EvidenceGate is composed by SprintConductor against
        # EvidenceSchemaRegistry; this plugin doesn't register its own gates.
        # Returning {} is the correct contribution.
        return {}

    def contribute_evidence_schemas(self) -> dict[str, type]:
        return {
            "design-doc":    DesignDoc,
            "plan-doc":      PlanDoc,
            "test-report":   TestReport,
            "review-report": ReviewReport,
            "ship-notes":    ShipNotes,
            "retro":         Retro,
        }

    def contribute_prompts(self, phase: str, role: str) -> str:
        prompt_path = (
            Path(__file__).parent.parent
            / "templates" / "gstack" / "prompts" / f"{role}.md"
        )
        if not prompt_path.is_file():
            return ""
        return prompt_path.read_text(encoding="utf-8")

    def contribute_review_routers(self) -> list:
        # Phase 4 fills this. Empty here is the explicit Phase 3 contract.
        return []

    def _on_phase_transition(self, event) -> None:
        if event.to_phase != "reflect":
            return
        # Phase 6 stub: write to placeholder until TeamMemoryStore lands.
        from clawteam.team.models import get_data_dir
        stub_dir = (
            get_data_dir() / "teams" / event.team_name
            / "memory" / "_phase6_pending"
        )
        stub_dir.mkdir(parents=True, exist_ok=True)
        stub_path = stub_dir / f"sprint-{event.team_name}-retro.md"
        stub_path.write_text(
            "# Phase 6 stub: TeamMemoryStore not yet implemented\n"
            f"# Sprint {event.team_name} entered reflect at {event.from_phase}->reflect\n"
            "# This entry will be migrated when Phase 6 lands.\n",
            encoding="utf-8",
        )
```

### Per-role envelope reassertion subclass (the Phase 2 TurnEnvelope extension)

```python
# clawteam/team/envelope_personas.py — NEW Phase 3 file
from typing import Literal
from pydantic import Field
from clawteam.team.envelope import TurnEnvelope


class PMEnvelope(TurnEnvelope):
    persona: Literal["pm"]
    pm_challenge: str = Field(..., min_length=20, alias="pm.challenge")


class CEOEnvelope(TurnEnvelope):
    persona: Literal["ceo"]
    ceo_decision_mode: Literal[
        "expansion", "selective", "hold", "reduction", "deferred"
    ] = Field(..., alias="ceo.decision_mode")


class EngMgrEnvelope(TurnEnvelope):
    persona: Literal["eng-mgr"]
    eng_mgr_lock: str = Field(..., min_length=20, alias="eng-mgr.architecture_lock")


class DesignerEnvelope(TurnEnvelope):
    persona: Literal["designer"]
    designer_rubric_dimension: str = Field(..., min_length=3, alias="designer.dimension")


class DxLeadEnvelope(TurnEnvelope):
    persona: Literal["dx-lead"]
    dx_friction: str = Field(..., min_length=10, alias="dx-lead.friction")


class EngineerEnvelope(TurnEnvelope):
    persona: Literal["engineer"]
    engineer_diff_summary: str = Field(..., min_length=10, alias="engineer.diff_summary")


class ReviewerEnvelope(TurnEnvelope):
    persona: Literal["reviewer"]
    reviewer_iron_law: Literal[
        "investigated", "fixing-without-investigation", "halt-three-failures"
    ] = Field(..., alias="reviewer.iron_law")


class QAEnvelope(TurnEnvelope):
    persona: Literal["qa"]
    qa_mode: Literal["qa", "qa-only"] = Field(..., alias="qa.mode")


class SecurityEnvelope(TurnEnvelope):
    persona: Literal["security"]
    security_confidence: int = Field(..., ge=0, le=10, alias="security.confidence")


class ShipperEnvelope(TurnEnvelope):
    persona: Literal["shipper"]
    shipper_step: Literal[
        "sync", "test", "audit", "push", "pr", "merge", "deploy", "verify"
    ] = Field(..., alias="shipper.step")


class SREEnvelope(TurnEnvelope):
    persona: Literal["sre"]
    sre_signal: Literal[
        "console-error", "perf-regression", "deploy-health", "benchmark", "noop"
    ] = Field(..., alias="sre.signal")
```

### One of the six artifact schemas (DesignDoc as the worked example)

```python
# clawteam/templates/gstack/schemas/design_doc.py
from typing import Literal
from pydantic import BaseModel, Field


class DesignDoc(BaseModel):
    """Think-phase artifact. Written by pm + ceo collaboratively.

    Required ## headings (validated by Phase 2 D-03 layer 2):
      ## problem
      ## users
      ## constraints
      ## rationale
      ## pm-verdict   (one of: proceed | reframe | kill)
    """
    artifact_type: Literal["design-doc"]
    problem_statement: str = Field(..., min_length=120)
    users: str = Field(..., min_length=50)
    constraints: str = Field(..., min_length=50)
    rationale: str = Field(..., min_length=120)
    pm_verdict: Literal["proceed", "reframe", "kill"]
    forcing_questions_addressed: list[int] = Field(..., min_length=6, max_length=6)
    sprint_id: str
    created_at: str
```

---

## Per-Role Prompt Content Map (Methodology Port — the load-bearing table)

This table is the source-of-truth for the planner. Each row is a role + its rubric content + a grep-verifiable signature line. The success criterion #3 reads against this table.

| Role | Skill rubrics ported | Required prompt content (grep-verifiable) | Signature line |
|------|----------------------|-------------------------------------------|----------------|
| **pm** | `/office-hours` (rubric only — interactive runtime → Phase 4) | All 6 forcing questions verbatim; challenge-framing instruction; per-role envelope (`pm.challenge` required); INTERACTIVE-RUNTIME-DEFERRED meta-instruction | `SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1` |
| **ceo** | `/plan-ceo-review` | 4 modes (Expansion / Selective / Hold / Reduction) with one-line definitions; decision output schema (`ceo.decision_mode` enum); leader binding (`leader_role = "ceo"` reference); explicit "you are the only role authorized to call advance_phase" instruction | `SIGNATURE: gstack-role:ceo rubric:plan-ceo-review envelope-version:1` |
| **eng-mgr** | `/plan-eng-review` + `/retro` | Architecture-lock instruction; data-flow-diagram requirement (mermaid or ASCII); edge-case matrix template; test-plan template; retro per-person breakdown template | `SIGNATURE: gstack-role:eng-mgr rubric:plan-eng-review+retro envelope-version:1` |
| **designer** | `/plan-design-review` + `/design-review` (rubric only — interactive `/design-consultation` runtime → Phase 4) | 0-10 rubric with all dimensions enumerated (visual hierarchy / typographic system / color discipline / interaction polish / brand coherence / accessibility / responsive behavior / motion appropriateness / information density / overall taste); AI-slop detection checklist; per-dimension dialogue meta-instruction (one dimension per turn); design-system research prompt | `SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1` |
| **dx-lead** | `/plan-devex-review` + `/devex-review` | Persona exploration template (3 personas: novice / pro / power-user); TTHW (Time-to-Hello-World) benchmarking instruction; friction-tracing template (per-step friction score); competitive benchmark prompt | `SIGNATURE: gstack-role:dx-lead rubric:plan-devex-review+devex-review envelope-version:1` |
| **engineer** | (no skill rubric port — engineer is the implementation persona; rubric content is implicit in the Build phase contract) | Diff-summary requirement (`engineer.diff_summary`); reference to Phase 5 tool-heavy skills (`/codex`, `/ship` — to be invoked when those phases land); SHA-pin awareness (record HEAD SHA at Build start) | `SIGNATURE: gstack-role:engineer rubric:none envelope-version:1` |
| **reviewer** | `/review` + `/investigate` (rubric only — interactive `/investigate` runtime → Phase 4) | Production-bug detection checklist (CI-passing-but-prod-failing patterns); iron-law statement: "no fix without investigation"; halt-after-3-failed-hypotheses rule; SHA-PIN-DEFERRED meta-instruction (record review_sha; halt if HEAD moves) | `SIGNATURE: gstack-role:reviewer rubric:review+investigate envelope-version:1` |
| **qa** | `/qa` + `/qa-only` | Bug-fix + regression-test loop template; `/qa-only` mode suppression (set `qa.mode = "qa-only"` to disable code edits); test-runner output reference requirement | `SIGNATURE: gstack-role:qa rubric:qa+qa-only envelope-version:1` |
| **security** | `/cso` | OWASP Top 10 checklist verbatim; STRIDE threat-model checklist; 17 false-positive exclusions (full list — port from upstream gstack `/cso` skill); 8/10+ confidence gate (`security.confidence >= 8` required to escalate; otherwise log as informational) | `SIGNATURE: gstack-role:security rubric:cso envelope-version:1` |
| **shipper** | (no skill rubric port — Ship-phase tool-heavy skills `/ship`, `/land-and-deploy`, `/document-release` ship in Phase 5) | Step enum (`shipper.step` Literal); Phase 5 tool-availability stub: "Until /ship lands in Phase 5, write a ship-notes.md skeleton with deploy_url placeholder and emit a question to ceo about manual ship coordination." | `SIGNATURE: gstack-role:shipper rubric:none envelope-version:1` |
| **sre** | (no skill rubric port — SRE tool-heavy skills `/canary`, `/benchmark`, `/setup-deploy` ship in Phase 5) | Signal enum (`sre.signal` Literal); Phase 5 tool-availability stub: "Until /canary and /benchmark land in Phase 5, monitor manually and log canary-report.md / benchmark-report.md placeholders." | `SIGNATURE: gstack-role:sre rubric:none envelope-version:1` |

**Pure-rubric vs interactive split (the Pitfall 7 partition):**

| Skill | Lands in Phase 3 as... | Phase 4 ships... |
|-------|------------------------|------------------|
| `/office-hours` | pm.md rubric reference (6 forcing questions verbatim, challenge-framing) + INTERACTIVE-RUNTIME-DEFERRED meta-instruction | Multi-turn state machine (Q1 → wait → Q2 conditional, etc.) |
| `/plan-ceo-review` | ceo.md complete rubric port + decision schema | (already complete in Phase 3 — purely declarative) |
| `/plan-eng-review` | eng-mgr.md complete rubric port | (already complete) |
| `/retro` | eng-mgr.md complete rubric port | (already complete) |
| `/plan-design-review` | designer.md rubric port (0-10 dimensions, AI-slop detection) | (already complete) |
| `/design-review` | designer.md rubric port (atomic-commit + before/after screenshots) | (already complete) |
| `/design-consultation` | designer.md rubric reference (per-dimension template) + INTERACTIVE-RUNTIME-DEFERRED | Per-dimension dialogue state machine |
| `/plan-devex-review` | dx-lead.md complete rubric port | (already complete) |
| `/devex-review` | dx-lead.md complete rubric port | (already complete) |
| `/review` | reviewer.md complete rubric port | (already complete) |
| `/investigate` | reviewer.md rubric reference (hypothesis-trace template) + INTERACTIVE-RUNTIME-DEFERRED + freeze-auto-application meta-instruction | Per-hypothesis state machine + auto-`/freeze` |
| `/qa-only` | qa.md mode-suppression instruction | (already complete) |
| `/cso` | security.md complete rubric port (OWASP + STRIDE + 17 exclusions + 8/10+ gate) | (already complete) |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single mega-prompt with all skill content baked in | Per-role prompt files + per-persona reassertion fields enforced by pydantic | Phase 2 D-06..D-09 envelope decision | Drift cut from 70%→9% per Echoing-paper; required for v1 narrative |
| `ArtifactRequiredGate` (existence + non-empty) | `EvidenceGate` (pydantic schema + min-length per heading + regex stub blacklist) | Phase 2 D-01..D-05 | Prevents Pitfall 8 gate gaming |
| Prompts long, examples inline mid-prompt | Prompts ≤ ~3 KB per role; examples (if any) at top or bottom only | Lost-in-the-middle research, 2026 [CITED: simonw substack 2026; claudecodecamp 2026] | Sonnet 4.5 reliability drops sharply past ~400K context — keeping prompts compact preserves model attention |
| Plugins manage everything globally at import | Plugin loaded only when its template is selected; registries populated on `on_register` | Phase 1 RFC 001 §4.3 D-04 | Backwards-compat with 6 existing templates is preserved by construction |
| Hand-rolled artifact validators per artifact type | Six pydantic v2 BaseModels with `Literal` discriminator registered into single registry | Phase 2 D-02 | One hook (`contribute_evidence_schemas`) enables a future template to ship its own schemas |

**Deprecated/outdated:**

- One-shot prompt baking of interactive skills: deprecated by Pitfall 7 classification at Phase 2 port-audit. Replaced by rubric-as-reference + state-machine-defer pattern.
- Prompts > 4 KB per role: deprecated by lost-in-the-middle reliability data; replaced by ≤3 KB target + per-persona envelope assertion.
- Globally-loaded plugins: deprecated by Phase 1 RFC 001; replaced by template-scoped plugin loading.

---

## Three Open Research Questions — RESOLVED

### Open Question #1: Per-persona role-reassertion field schemas

**Recommendation:** Each of the 11 personas asserts a single per-persona field in every TurnEnvelope. The field name is namespaced (`pm.challenge`, `ceo.decision_mode`, `reviewer.iron_law`, etc.). The field is *required* (Pydantic raises if missing or stub-grade). The full table is in the Code Examples §Per-role envelope reassertion subclass section above. Eleven Pydantic subclasses of `TurnEnvelope` live in `clawteam/team/envelope_personas.py` (NEW Phase 3 file). Validation site: extend Phase 2's `parse_frontmatter` + `TurnEnvelope.model_validate` to *dispatch* on `persona` field via a `Discriminated Union` of the 11 subclasses.

**Confidence:** HIGH for the *shape* (one field per persona, namespaced); HIGH for pm/ceo/reviewer/security (those four personas have crisp rubric-driven assertion fields); MEDIUM for engineer/shipper/sre (those personas have weaker per-turn assertion content — the chosen fields work but discuss-phase may want to refine wording with the user).

**Tradeoff vs. multi-field reassertion (e.g., `pm.challenge` + `pm.framing` + `pm.followup`):** Multi-field is more expressive but multiplies the points of failure for envelope validation. Single-field is the Echoing-paper finding's minimum viable shape; expand to multi-field in Phase 4 if drift detector data shows single-field isn't enough. [CITED: research/PITFALLS.md §Pitfall 1 — "70%→9% with structured protocol" finding is established with single mandatory field.]

### Open Question #2: Golden-trace sourcing strategy for verifying ports are faithful

**Recommendation: Strategy B — derive expected shapes from the gstack skill markdown itself.**

For Phase 3 specifically (pure-rubric ports), Strategy B is correct because:
- The Phase 3 deliverable is a *transcription* of rubric content into role-prompt files. The fidelity question is "does pm.md contain all 6 forcing questions verbatim?" — this is a direct grep against the upstream gstack `/office-hours` skill markdown.
- Strategy A (run native gstack against a fixture repo) is correct for Phase 4's interactive state machines, where the validating signal is *interaction shape* (turn count, branching), not *content presence*.
- Strategy C (co-design with Garry Tan) is high-cost, high-coordination, and unnecessary for a transcription task.

**Implementation:** In Phase 3 plans, add a task `golden-trace-prep` that:
1. WebFetches each gstack skill markdown file (URLs documented in PROJECT.md Context section).
2. Stores them under `tests/fixtures/gstack_skills/<skill-name>.md` (committed to repo for reproducibility — these are public files).
3. The golden tests (per the Validation Architecture section below) grep both the upstream fixture and the Phase 3 role-prompt to assert content presence.

**Confidence:** HIGH for the Phase 3 strategy (B) — the rubric content is finite, public, and deterministic. **LOW** for whether Strategy A becomes necessary in Phase 4 — needs Phase 4's research pass to confirm. Phase 3 doesn't depend on that decision.

**Tradeoff vs. Strategy A in Phase 3:** Strategy A would require running native gstack (which we don't have a local checkout of) or using a third-party recorded transcript (which doesn't exist publicly). Strategy A's signal is *interaction shape*; Phase 3 doesn't ship interactive state machines, so the signal is irrelevant here.

[CITED: STATE.md "Phase 3 research pass recommended" + ROADMAP Phase 3 "Research flag" + research/SUMMARY.md Gaps to Address #2.]

### Open Question #3: Per-role prompt length budget

**Recommendation:** Target **≤3 KB per role prompt** (typical: 2-2.5 KB). Hard cap: 4 KB. Budget split:
- Role identity + persona contract: ~600 bytes
- Methodology rubric content (verbatim from upstream gstack skill): ~1500 bytes (varies; see per-role table below)
- Per-persona envelope schema reference: ~300 bytes
- Project-anchor reads (e.g., reference to gstack.toml or to Phase 2 D-06): ~200 bytes
- Signature line + boilerplate: ~100 bytes
- **Buffer for Phase 6 memory inclusions when they land:** ~300 bytes

**Why 3 KB:** Lost-in-the-middle effect [CITED: Tygart Media 2026 + simonw 2026]: prompts under ~2K tokens (~6 KB of English) attend uniformly across the prompt; prompts past ~10K tokens (~30 KB) start showing middle-attention drop. 3 KB sits firmly in the safe zone. Reliability data on Sonnet 4.5: drops to 0.56 correctness under hard-cap pressure; structured prompts reduce this. 11 prompts × 3 KB = 33 KB of stable role identity per session, well within the per-session prompt-cache budget (Anthropic's 90% cache-read discount applies for repeat reads of immutable prompts).

**Per-role specific budget allocation (rubric content sizes):**

| Role | Rubric content size budget | Reason |
|------|----------------------------|--------|
| pm | ~1200 bytes | 6 forcing questions × ~150 bytes + challenge-framing meta-instruction. INTERACTIVE-DEFERRED note. |
| ceo | ~1200 bytes | 4 mode definitions + decision schema + leader-binding paragraph |
| eng-mgr | ~1800 bytes | Architecture-lock + data-flow + edge-case matrix + test-plan + retro template (largest non-security rubric) |
| designer | ~1800 bytes | 10-dimension rubric (each ~120 bytes) + AI-slop checklist + per-dimension meta-instruction + INTERACTIVE-DEFERRED note |
| dx-lead | ~1500 bytes | Persona exploration + TTHW + friction tracing + competitive benchmark |
| engineer | ~600 bytes | Mostly persona contract + Phase 5 tool-availability note. No rubric port. |
| reviewer | ~1500 bytes | `/review` checklist + `/investigate` iron-law + halt-3 rule + SHA-PIN-DEFERRED + INTERACTIVE-DEFERRED for /investigate |
| qa | ~1000 bytes | Bug-fix + regression-test loop + qa-only mode suppression |
| security | ~2400 bytes | OWASP Top 10 (10 items × ~80 bytes) + STRIDE (6 items × ~70 bytes) + 17 false-positive exclusions (largest rubric — at the budget ceiling) |
| shipper | ~600 bytes | Step enum + Phase 5 tool-availability stub. No rubric port. |
| sre | ~600 bytes | Signal enum + Phase 5 tool-availability stub. No rubric port. |

**Confidence:** MEDIUM — the budget numbers are derived from public lost-in-the-middle research, not measured against this specific rubric content. Phase 3 plans should include a measurement task: after writing each role prompt, run `wc -c clawteam/templates/gstack/prompts/*.md` and assert all are ≤4 KB and the average is ≤3 KB.

**Tradeoff vs. larger prompts (5-8 KB):** More room for examples and elaboration. Trade is reliability — past ~6 KB the model starts under-attending the middle of the prompt, which for a per-persona prompt is exactly where the rubric content sits. Stay compact; defer elaboration to per-task prompts (which the conductor assembles on the fly per Phase 2 D-06).

[CITED: claudecodecamp 1M context window 2026; Tygart Media context-window explainer 2026; simonw substack on Claude 3.7 long-output behavior; Anthropic prompt-caching docs (cache-read = 10% cost).]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 2 ships `SprintConductor.advance_phase` with an `actor` parameter (or accepts a small additive change to add it) | Pattern 4 (Leader-binding) | If Phase 2 ships without the actor parameter, Phase 3 plan needs a 1-line addition to `SprintConductor.advance_phase(actor: str = leader_role)`. Low risk; verify in Plan 02-11 review during planning. |
| A2 | The `contribute_evidence_schemas` hook is wired through `PluginManager` to call `EvidenceSchemaRegistry.register` at plugin load (Phase 2 D-02 implies this but Plan 02-04/02-01 must confirm the wiring) | Pattern 5 (six pydantic schemas) | If wiring isn't complete, Phase 3 must add the wiring as a sub-task. Low risk; the hook exists in `clawteam/plugins/base.py:79-93` [VERIFIED] but the call-site path needs grep confirmation in plan-prep. |
| A3 | Existing `TemplateDef` pydantic model accepts new optional fields without breaking existing TOMLs (pydantic v2 default behavior) | Pattern 1 (Strict additive extension) | If pydantic v2 strict mode is configured (e.g., `model_config = ConfigDict(extra="forbid")`), new fields would break existing templates. [VERIFIED: `clawteam/templates/__init__.py:24-44` shows no strict mode config — pydantic default is `extra="ignore"`.] Low risk. |
| A4 | The `clawteam team show` CLI exists for other templates and accepts a member-list + dashboard-row format extensible via the existing rich/typer machinery | Architecture Map row 9 | If the existing `team show` CLI doesn't have a clean extension point, Phase 3 must add one. Moderate risk; verify existence and shape in plan-prep. Easy fix if absent. |
| A5 | The 17 false-positive exclusions for `/cso` are listed in the upstream gstack `/cso` skill file and can be ported verbatim | Per-Role Prompt Content Map row 8 | If the upstream content has fewer/different exclusions, the plan must adjust the security.md content. Verifiable via WebFetch in plan-prep. Low risk. |
| A6 | Strategy B (markdown-derived golden traces) is sufficient signal for the Phase 3 success criterion #3 verification | Open Question #2 | If discuss-phase reveals the user wants Strategy A's stronger signal (run native gstack against fixtures), the plan adds a task to set up a sandbox-gstack environment. Moderate risk. |
| A7 | The 3 KB per-role prompt budget is comfortably above the rubric content needs for all 11 roles | Open Question #3 | If security.md (the largest at 2.4 KB rubric) overruns the 3 KB total budget when including persona contract + envelope schema + signature, the plan adjusts the budget upward to 4 KB across all roles. Low risk; measurable. |
| A8 | The Reflect-phase Phase 6 stub (write to `_phase6_pending/`) is acceptable to discuss-phase as the SPRINT-06 fulfillment | Pattern 6 + ROADMAP success criterion #5 | If the user wants more (e.g., the stub should *also* emit a structured event for future Phase 6 migration), the plan adds an event emission. Low risk; ROADMAP success criterion #5 explicitly endorses the stub pattern. |

---

## Open Questions (RESOLVED 2026-04-20 by CONTEXT.md D-01..D-04, D-07 — seed block retained for traceability)

> All three questions below were load-bearing seeds for `/gsd-discuss-phase 3`. The phase's CONTEXT.md locked decisions for each. This section is preserved as historical context — downstream plans consult CONTEXT.md, not this block.

1. **Should the role prompt content for engineer/shipper/sre include any rubric port at all, or is "no rubric, just persona contract + Phase 5 deferral" the right shape?** — **RESOLVED by CONTEXT.md D-01/D-02/D-03:** engineer ships substantive implementation-discipline rubric (~1200B per D-01); shipper + sre ship honest Phase-5-deferred stubs (~600B each per D-02/D-03) with `rubric:none` SIGNATURE flag so Phase 5's plan task can identify + swap them.
   - What we know: Phase 5 owns the tool-heavy skills these roles will eventually invoke. Per ROADMAP, Phase 3's success criterion #3 doesn't enumerate prompt content for these three roles.
   - What's unclear: Whether the user wants more substantive content here (e.g., engineer should have an "implementation discipline" rubric similar to gstack's implicit Build-phase guidance).
   - Recommendation: ship minimal in Phase 3 (persona contract + envelope + Phase 5 deferral); revisit in Phase 5 when the tool-heavy skills land.

2. **Should `gstack.toml` include any starter `[[template.tasks]]` rows, or is the template purely a roster declaration with sprint dispatch entirely dynamic?**
   - What we know: Existing templates (software-dev) include starter tasks. gstack's product narrative is "team waits for you to start a sprint" — no starter tasks would match.
   - What's unclear: Whether a "welcome message" task per role helps onboarding.
   - Recommendation: ship without starter tasks; a starter "team is ready, await /sprint start" emission can be added by `TeamManager` post-spawn if needed.

3. **Should the per-role pydantic envelope subclasses live in `clawteam/team/envelope_personas.py` (alongside Phase 2's `envelope.py`) or under `clawteam/templates/gstack/envelope.py` (gstack-scoped)?**
   - What we know: Per-persona envelopes are gstack-specific; following the "delete the plugin and the rest still works" rule suggests they belong under `templates/gstack/`.
   - What's unclear: Whether discuss-phase wants future templates (hedge-fund-sprint) to reuse the per-persona pattern; if so, the file might belong under `clawteam/team/`.
   - Recommendation: place under `clawteam/templates/gstack/envelope_personas.py` for Phase 3 (gstack-scoped); promote to `clawteam/team/` if a second template adopts the pattern.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Whole project | ✓ (assumed — CI passes) | 3.10+ | — |
| pydantic v2 | TemplateDef extension, six artifact schemas, per-persona envelopes | ✓ (in pyproject.toml) | v2 | — |
| stdlib `tomllib` (3.11+) / `tomli` (3.10) | Parse gstack.toml | ✓ | stdlib + tomli backport | — |
| Existing `clawteam/spawn/` registry | Spawning the 11 agents | ✓ | — | — |
| Existing `WorkspaceManager` | Per-agent worktrees | ✓ | — | — |
| Existing `TeamManager` | Team lifecycle | ✓ | — | — |
| Existing `SprintConductor` (Phase 2) | Phase advancement | ✓ (in flight — Plan 02-11 complete per STATE.md) | — | — |
| Existing `EvidenceSchemaRegistry` (Phase 2) | Six artifact schema registration | ✓ (Plan 02-04 complete) | — | — |
| Existing `PhaseRegistry` (Phase 1) | Phase registration | ✓ (Phase 1 complete) | — | — |
| Existing `clawteam/cli/` Typer app | `team show` extension | ✓ | — | — |
| `pytest` | Golden tests + integration tests | ✓ (already in repo) | — | — |
| WebFetch (during plan-prep) for gstack skill markdown | Strategy B golden-trace fixtures | ✓ (Claude tool available) | — | If unavailable: human downloads markdown manually |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None — Phase 3 is fully self-contained on existing substrate.

---

## Validation Architecture

> Nyquist validation enabled per `.planning/config.json` (`workflow.nyquist_validation: true`).

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already in repo) |
| Config file | `pytest.ini` / `pyproject.toml` (existing) |
| Quick run command | `pytest tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py -x` |
| Full suite command | `pytest tests/ -x` (must remain green — Phase 0 regression matrix dependency) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEAM-01 | `gstack.toml` parses through existing template loader | unit | `pytest tests/test_gstack_template.py::test_parses_via_existing_loader -x` | ❌ Wave 0 |
| TEAM-02 | All 11 distinct agents present in loaded template | unit | `pytest tests/test_gstack_template.py::test_eleven_agents_with_distinct_roles -x` | ❌ Wave 0 |
| TEAM-03 | Each agent gets its own worktree desk via `WorkspaceManager` | integration | `pytest tests/test_gstack_team_spawn.py::test_eleven_worktrees_created -x` | ❌ Wave 0 |
| TEAM-04 | Only ceo can call `SprintConductor.advance_phase` (other actors rejected) | unit | `pytest tests/test_gstack_plugin.py::test_only_ceo_advances_phase -x` | ❌ Wave 0 |
| TEAM-05 | `--model-profile balanced` is default; `quality` and `budget` selectable | unit | `pytest tests/test_gstack_template.py::test_model_profile_defaults_to_balanced -x` | ❌ Wave 0 |
| SKILL-01 | pm.md contains all 6 forcing questions + challenge-framing + INTERACTIVE-DEFERRED | golden | `pytest tests/test_gstack_role_prompts.py::test_pm_office_hours_rubric -x` | ❌ Wave 0 |
| SKILL-02 | ceo.md contains 4 modes (Expansion/Selective/Hold/Reduction) + decision schema | golden | `pytest tests/test_gstack_role_prompts.py::test_ceo_plan_review_modes -x` | ❌ Wave 0 |
| SKILL-03 | eng-mgr.md contains arch-lock + data-flow + edge-case matrix + test-plan + retro per-person | golden | `pytest tests/test_gstack_role_prompts.py::test_eng_mgr_plan_review_and_retro -x` | ❌ Wave 0 |
| SKILL-04 | designer.md contains 0-10 rubric (10 dimensions) + AI-slop checklist + INTERACTIVE-DEFERRED for /design-consultation | golden | `pytest tests/test_gstack_role_prompts.py::test_designer_rubric -x` | ❌ Wave 0 |
| SKILL-05 | dx-lead.md contains personas + TTHW + friction tracing | golden | `pytest tests/test_gstack_role_prompts.py::test_dx_lead_devex_review -x` | ❌ Wave 0 |
| SKILL-06 | reviewer.md contains iron-law + halt-after-3 + SHA-PIN-DEFERRED + INTERACTIVE-DEFERRED for /investigate | golden | `pytest tests/test_gstack_role_prompts.py::test_reviewer_review_and_investigate -x` | ❌ Wave 0 |
| SKILL-07 | qa.md contains bug-fix + regression-loop + qa-only mode suppression | golden | `pytest tests/test_gstack_role_prompts.py::test_qa_qa_only -x` | ❌ Wave 0 |
| SKILL-08 | security.md contains OWASP Top 10 + STRIDE + 17 false-positive exclusions + 8/10+ confidence gate | golden | `pytest tests/test_gstack_role_prompts.py::test_security_cso_full_rubric -x` | ❌ Wave 0 |
| SKILL-09 (Phase 2 — verified here) | All 11 personas have working per-persona envelope subclass | unit | `pytest tests/test_envelope_personas.py -x` | ❌ Wave 0 |
| SPRINT-06 | Reflect phase invokes /learn stub; placeholder file written | integration | `pytest tests/test_gstack_plugin.py::test_reflect_phase_learn_stub_writes_placeholder -x` | ❌ Wave 0 |
| UX-01 | `clawteam team spawn gstack --name <n>` end-to-end | integration | `pytest tests/test_sprint_cli.py::test_team_spawn_gstack -x` | ❌ Wave 0 |
| UX-07 | `clawteam team show <n>` displays 11 members + sprint progress + cost rollup placeholders | integration | `pytest tests/test_cli_commands.py::test_team_show_gstack_dashboard -x` | ❌ Wave 0 |
| (Cross-template isolation — success criterion #2) | Spawning `software-dev` does NOT register gstack phases | regression | `pytest tests/test_template_regression_matrix.py::test_software_dev_unaffected_by_gstack_plugin -x` | ✓ EXTEND (file exists) |
| (Phase 0 regression matrix — success criterion #7) | All 6 existing templates spawn unchanged | regression | `pytest tests/test_template_regression_matrix.py -x` | ✓ EXTEND (file exists) |

### Sampling Rate

- **Per task commit:** `pytest tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py tests/test_envelope_personas.py -x` (~5 seconds expected)
- **Per wave merge:** `pytest tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py tests/test_envelope_personas.py tests/test_gstack_team_spawn.py tests/test_template_regression_matrix.py tests/test_evidence_schemas.py tests/test_sprint_conductor.py -x` (~30 seconds)
- **Phase gate:** `pytest tests/ -x` (full suite green before `/gsd-verify-work`)

### Wave 0 Gaps

- [ ] `tests/test_gstack_template.py` — covers TEAM-01, TEAM-02, TEAM-05
- [ ] `tests/test_gstack_plugin.py` — covers TEAM-04, SPRINT-06, plugin-load isolation
- [ ] `tests/test_gstack_role_prompts.py` — covers SKILL-01..SKILL-08 (golden grep-tests against signature lines + rubric content presence)
- [ ] `tests/test_envelope_personas.py` — covers SKILL-09 verification across all 11 personas
- [ ] `tests/test_gstack_team_spawn.py` — covers TEAM-03, UX-01 integration
- [ ] `tests/fixtures/gstack_skills/` directory with WebFetched skill markdown for grep cross-checking (per Strategy B)
- [ ] `tests/fixtures/gstack_artifacts/` directory with golden valid + stub-grade fixtures for the six EvidenceSchema models
- [ ] EXTEND `tests/test_template_regression_matrix.py` to assert spawning each of the 6 existing templates does NOT trigger `GstackSprintPlugin.on_register` (cross-template isolation success criterion #2)
- [ ] EXTEND `tests/test_evidence_schemas.py` (Phase 2 file) to validate the six new gstack schemas (Phase 2 has the registry; Phase 3 fills it)
- [ ] EXTEND `tests/test_cli_commands.py` (existing) for `team show` dashboard verification

---

## Sources

### Primary (HIGH confidence)

- `clawteam/templates/__init__.py` (lines 11-17, 24-44, 75-101) — TOML loader + TemplateDef pydantic model [VERIFIED]
- `clawteam/templates/software-dev.toml` (full file) — existing template TOML schema convention [VERIFIED]
- `clawteam/plugins/base.py` (lines 14-93) — HarnessPlugin ABC + Phase 1/2 hook surface [VERIFIED]
- `clawteam/plugins/manager.py` — plugin loader [VERIFIED]
- `clawteam/sprint/conductor.py` (lines 1-300) — SprintConductor implementation [VERIFIED]
- `clawteam/harness/phases.py` (lines 19-29, 39-104) — Phase as open str + PhaseGate ABC + DEFAULT_PHASES [VERIFIED]
- `clawteam/harness/evidence_gate.py`, `clawteam/harness/evidence_schemas.py` — Phase 2 schema registry [VERIFIED]
- `clawteam/team/envelope.py` (lines 1-80) — TurnEnvelope + parse_frontmatter [VERIFIED]
- `clawteam/team/manager.py` (lines 1-80) — TeamManager + create_team flow [VERIFIED]
- `clawteam/spawn/__init__.py` (lines 1-32) — spawn registry public API [VERIFIED]
- `.planning/PROJECT.md` — locked decisions, narrative [VERIFIED]
- `.planning/REQUIREMENTS.md` — TEAM-01..05, SKILL-01..09, SPRINT-06, UX-01, UX-07 verbatim [VERIFIED]
- `.planning/ROADMAP.md` (Phase 3 + Phase 4 + Phase 5 sections) — what is in/out of scope for Phase 3 [VERIFIED]
- `.planning/STATE.md` — Phase 3 research-flag blocker; default model_profile confirmed [VERIFIED]
- `.planning/research/SUMMARY.md` — Phase 3 research-flag rationale [VERIFIED]
- `.planning/research/ARCHITECTURE.md` (lines 1-300) — Pattern 1 (PhaseRegistry), Pattern 5 (TeamMemory layered), GstackSprintPlugin shape [VERIFIED]
- `.planning/research/PITFALLS.md` (Pitfalls 1, 7, 8, 9, 14) — drift / skill-port-collapse / gate gaming / SHA-pinning / backwards-compat preventions [VERIFIED]
- `.planning/research/FEATURES.md` Differentiators #1 + #2 — 11-role pre-configured team + 7-phase sprint as product [VERIFIED]
- `.planning/phases/02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention/02-RESEARCH.md` — Phase 2 D-01..D-29 user constraints feeding Phase 3 [VERIFIED]

### Secondary (MEDIUM confidence)

- gstack repository (https://github.com/garrytan/gstack) — skill list + per-skill summary via WebFetch [CITED]
- Anthropic docs on context windows + prompt caching [CITED via WebSearch — multiple 2026 articles]
- "Lost in the middle" reliability data for Sonnet 4.5 [CITED: claudecodecamp.com 2026, simonw.substack.com 2026, tygartmedia.com 2026]

### Tertiary (LOW confidence — flagged for plan-time validation)

- The exact 17 false-positive exclusions for `/cso` — port verbatim from upstream gstack `/cso` skill markdown during plan-prep WebFetch (Assumption A5)
- The exact 6 forcing questions of `/office-hours` — port verbatim during plan-prep (the wording above is paraphrased; the canonical version comes from upstream)
- Designer's exact 10 rubric dimensions — port verbatim from upstream `/plan-design-review`

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every dep is already in the repo; no new packages introduced. [VERIFIED firsthand reads]
- Architecture patterns: HIGH — every pattern grounds in either Phase 1/2 substrate (verified) or research/ARCHITECTURE.md Pattern 1/5/6 (verified)
- Per-Role Prompt Content Map: HIGH for the *structure* + *signature line discipline* + *which skills land where*; MEDIUM for verbatim rubric content (port-from-upstream task during plan-prep)
- Don't Hand-Roll: HIGH — every "use existing" pointer cites a verified file path
- Common Pitfalls: HIGH — Pitfalls 1, 7, 8, 9, 14 are well-grounded in research/PITFALLS.md
- Open research questions: HIGH for #1 (envelope shape grounded in Echoing-paper finding); HIGH for #2 (Strategy B is structurally correct for transcription tasks); MEDIUM for #3 (3 KB target is grounded in published context-window data but not measured against this specific content)

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (Phase 3 plan-time; refresh if Phase 4/5 research shifts the rubric-vs-state-machine partition)
