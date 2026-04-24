---
phase: 00-foundation-upstream-rfc
plan: 05
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/rfcs/README.md
  - docs/rfcs/001-phase-registry.md
autonomous: true
requirements: []
tags: [docs, rfc, upstream, phase-registry]

must_haves:
  truths:
    - "docs/rfcs/ directory exists at repo root and contains a subdirectory-level README plus the first RFC."
    - "001-phase-registry.md follows an 8-section Rust-style RFC template: Summary, Motivation, Guide-level explanation, Reference-level API, Drawbacks, Rationale and Alternatives, Prior art, Unresolved questions."
    - "The Reference-level API section specifies PhaseRegistry, HarnessPlugin.contribute_phases(), InteractionGate, SprintState — the four primitives Phase 1 lands."
    - "A worked example demonstrates that software-dev.toml continues to spawn unchanged with the proposed API (explicit CORE-03 guarantee)."
    - "RFC has a metadata block: status (Draft), authors, date (2026-04-15), target phase (Phase 1)."
    - "docs/rfcs/README.md is a minimal index document with a table of RFCs and their statuses."
  artifacts:
    - path: "docs/rfcs/README.md"
      provides: "RFC index page: short preamble + Markdown table listing each RFC (# / Title / Status)"
      min_lines: 15
    - path: "docs/rfcs/001-phase-registry.md"
      provides: "Rust-style 8-section RFC proposing PhaseRegistry + HarnessPlugin.contribute_phases + InteractionGate + SprintState with worked example and additive-only guarantees"
      contains: "PhaseRegistry"
      min_lines: 300
  key_links:
    - from: "docs/rfcs/001-phase-registry.md"
      to: "clawteam/plugins/base.py::HarnessPlugin"
      via: "proposes additive hook contribute_phases() with empty default"
      pattern: "def contribute_phases"
    - from: "docs/rfcs/001-phase-registry.md §Worked Example"
      to: "clawteam/templates/software-dev.toml"
      via: "trace of software-dev launch before/after RFC adoption — identical observable behavior"
      pattern: "software-dev\\.toml"
---

<objective>
Ship the upstream RFC that proposes the Phase 1 API surface (`PhaseRegistry` + `HarnessPlugin.contribute_phases()` + `InteractionGate` + `SprintState`) BEFORE Phase 1 code lands. ROADMAP Phase 0 success criterion 4 requires the RFC to exist with a worked example showing `software-dev.toml` unchanged. Tone mirrors the existing `docs/transport-architecture.md` (ASCII box diagrams, numbered sections, neutral technical prose).

Purpose: Closes the infrastructure deliverable in Phase 0 ("An upstream RFC document exists at `docs/rfcs/001-phase-registry.md` proposing the three optional `HarnessPlugin` hooks with empty defaults, the `PhaseRegistry` class shape, additive-only contract guarantees, and a worked example"). Establishes the RFC process for future ClawTeam fork proposals.

Scope boundary: This plan is PURE MARKDOWN. Zero code changes. The maintainer-acknowledgement step (ROADMAP success criterion 4's "≥1 maintainer ack before Phase 1 code lands") is an out-of-band action the human owner performs after merging this plan. The plan's success criterion is that the RFC markdown EXISTS with the required shape; maintainer-ack tracking happens in ROADMAP itself.

Output:
- New `docs/rfcs/README.md` — minimal RFC index (table-style, borrowed from Rust RFCs / Python PEPs convention).
- New `docs/rfcs/001-phase-registry.md` — Rust-style 8-section RFC with all four Phase 1 primitives specified, worked example of software-dev, explicit additive-only guarantees.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/00-foundation-upstream-rfc/00-RESEARCH.md
@.planning/phases/00-foundation-upstream-rfc/00-PATTERNS.md
@docs/transport-architecture.md
@clawteam/harness/phases.py
@clawteam/plugins/base.py
@clawteam/templates/software-dev.toml

<interfaces>
<!-- Structural cues for the RFC — no code interfaces to extract, but these identifiers must be named correctly. -->

Phase 1 primitives the RFC proposes (per ROADMAP Phase 1 success criteria 1-5):
- PhaseRegistry: in-memory registry at `clawteam/harness/phase_registry.py`. Plugins populate it via HarnessPlugin.contribute_phases() hook. Name-collision raises ValueError at registration time.
- HarnessPlugin.contribute_phases() -> list[Phase]: new optional hook with empty-list default.
- SprintState: pydantic v2 model at `clawteam/sprint/state.py`. Fields: sprint_id, goal, team, current_phase, phase_history, artifacts, participants, pending_question_ids, auto_advance, workspace_branch, created_at. Round-trips through file_locked() atomic JSON.
- InteractionGate: PhaseGate subclass at `clawteam/harness/interaction_gate.py`. Returns (False, "Open questions: ...") when questions/N.md has no sibling answers/N.md.

From ROADMAP.md Phase 1 Requirements: CORE-01, CORE-02, CORE-04, INT-01, INT-02.

From clawteam/harness/phases.py:20 (the existing open-string Phase alias — preserve):
```python
Phase = str  # allow plugin extension without Enum rewrites
```

From clawteam/plugins/base.py (existing HarnessPlugin ABC that contribute_phases extends):
```python
class HarnessPlugin(ABC):
    """Plugin contract: contribute gates/prompts to the harness lifecycle."""
    def contribute_gates(self, phase: Phase) -> list[PhaseGate]: ...
    def contribute_prompts(self, role: AgentRole) -> str | None: ...
```

From clawteam/templates/software-dev.toml (the worked-example baseline):
```toml
name = "software-dev"
backend = "tmux"
description = "Software development swarm with PM + engineer + QA roles."
...
```

From docs/transport-architecture.md (tone reference — numbered H2s, ASCII box diagrams, neutral tech prose).
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create docs/rfcs/README.md index</name>
  <files>docs/rfcs/README.md</files>
  <action>
    Create `docs/rfcs/` directory and drop a minimal README.md index inside it.

    `docs/rfcs/README.md` content:

    ```markdown
    # RFCs

    Design proposals for upstream-bound changes to the ClawTeam harness. Each RFC
    targets a specific phase in the v1 gstack-integration roadmap and documents the
    additive-only contract that keeps existing templates (`software-dev.toml`,
    `hedge-fund.toml`, `code-review.toml`, `harness-default.toml`,
    `research-paper.toml`, `strategy-room.toml`) unchanged.

    ## Process

    1. **Draft**: Author writes an RFC using the Rust-style template (see RFC 001 as
       the canonical example).
    2. **Review**: RFC is opened as a PR against the upstream ClawTeam repo. The
       target outcome is at least one maintainer acknowledgement before the
       companion implementation PR lands.
    3. **Accepted**: status updated from `Draft` → `Accepted`; implementation PRs
       reference the RFC by number.
    4. **Rejected**: status updated to `Rejected` with rationale appended in the
       Unresolved Questions section.

    Mirror copy in this repo (`docs/rfcs/`) stays authoritative for the fork even if
    the upstream PR has not merged — implementation plans may reference the RFC
    number directly.

    ## Index

    | # | Title | Status | Target Phase |
    |---|-------|--------|--------------|
    | [001](001-phase-registry.md) | PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate | Draft | Phase 1 |
    ```

    Rules:
    - Markdown-only, no code.
    - Short preamble (5-10 lines) explaining the RFC purpose — borrowed from Rust RFC repo's README convention.
    - Table of RFCs with columns: `#` (numbered link), `Title` (what the RFC covers), `Status` (Draft/Accepted/Rejected), `Target Phase` (which roadmap phase consumes this RFC).
    - Link style: `[001](001-phase-registry.md)` — relative paths for sibling files.
    - No rich frontmatter (no YAML metadata block); README is a human-read index.
    - Do NOT list v2 speculative RFCs or TBD entries; the index only reflects files that exist.
  </action>
  <verify>
    <automated>test -f /home/jac/repos/ClawTeam-gstack/docs/rfcs/README.md && grep -q "001-phase-registry.md" /home/jac/repos/ClawTeam-gstack/docs/rfcs/README.md && grep -qi "draft" /home/jac/repos/ClawTeam-gstack/docs/rfcs/README.md && echo "README OK"</automated>
  </verify>
  <done>
    `docs/rfcs/README.md` exists with a process preamble and a table listing RFC 001 as Draft targeting Phase 1. Link to `001-phase-registry.md` is a valid relative reference.
  </done>
</task>

<task type="auto">
  <name>Task 2: Write docs/rfcs/001-phase-registry.md (8-section Rust-style RFC)</name>
  <files>docs/rfcs/001-phase-registry.md</files>
  <action>
    Create `docs/rfcs/001-phase-registry.md` with the full 8-section structure. Tone mirrors `docs/transport-architecture.md` (numbered H2 sections, neutral technical prose, ASCII box diagrams for architecture, no marketing language).

    Full file content:

    ```markdown
    ---
    rfc: 001
    title: PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate
    status: Draft
    authors: ClawTeam-gstack fork contributors
    created: 2026-04-15
    target-phase: Phase 1 of gstack-integration roadmap (v1)
    ---

    # RFC 001 — Plugin-Populated Phase Registry with Sprint State and Interactive Gates

    ## 1. Summary

    Add four additive primitives to the ClawTeam harness so plugin authors can
    contribute named lifecycle phases, persist sprint state, and block phase
    transitions on human interaction — without editing `PhaseState` enum members or
    changing existing template semantics. The four primitives are:

    - `PhaseRegistry` — an in-memory registry that plugins populate at load time.
    - `HarnessPlugin.contribute_phases()` — a new optional hook that returns a list
      of phase names the plugin wants to register. Default implementation returns
      an empty list, so existing plugins need no changes.
    - `SprintState` — a pydantic v2 model capturing per-sprint lifecycle state
      (id, goal, phase, artifacts, participants, pending questions) persisted under
      `~/.clawteam/teams/<team>/sprints/<id>/state.json` via the existing
      `file_locked()` atomic-JSON machinery.
    - `InteractionGate` — a `PhaseGate` subclass that blocks phase advance until
      every posted `questions/<N>.md` has a sibling `answers/<N>.md`.

    The four primitives are the substrate for the gstack 7-phase sprint model
    (Think → Plan → Build → Review → Test → Ship → Reflect) without requiring
    gstack-specific semantics in core. The existing six templates (`software-dev`,
    `hedge-fund`, `code-review`, `harness-default`, `research-paper`,
    `strategy-room`) are unaffected: they do not load plugins that call
    `contribute_phases()`, so `PhaseRegistry` stays empty for them and their phase
    lists come from the existing `DEFAULT_PHASES` constant.

    ## 2. Motivation

    ClawTeam currently hard-codes its phase vocabulary in `clawteam/harness/phases.py`:

    ```python
    Phase = str
    DEFAULT_PHASES: list[Phase] = [DISCUSS, PLAN, EXECUTE, VERIFY, SHIP]
    ```

    Plugins can already contribute **gates** (`HarnessPlugin.contribute_gates`) and
    **prompts** (`HarnessPlugin.contribute_prompts`), but they cannot contribute
    **phases**. Adding a seventh or eighth phase currently requires editing the
    `DEFAULT_PHASES` list in core — a non-additive change that breaks the upstream
    compatibility contract documented in `PROJECT.md` ("Harness-core changes ship
    as extensions … not edits to existing `PhaseState` or `HarnessOrchestrator`
    semantics.").

    The gstack integration needs a phase vocabulary disjoint from the default:
    `think → plan → build → review → test → ship → reflect`. Supporting this
    without compromising the existing templates requires a registry that plugins
    populate and that `HarnessOrchestrator` consults at construction time.

    Three secondary motivations:

    1. **Sprint-as-unit.** gstack treats a sprint as the unit of work a team takes
       on. Teams are persistent; sprints are transient. Persisting sprint state as
       a first-class model enables `clawteam sprint start | status | show | list |
       pause | resume` commands in Phase 2 and multiple concurrent sprints per
       team in Phase 7.

    2. **Human-in-the-loop without polling.** gstack's interactive skills
       (`/office-hours`, `/plan-ceo-review`, `/design-consultation`) rely on humans
       answering questions that agents pose. The `InteractionGate` primitive makes
       this a first-class harness concept rather than a skill-level hack.

    3. **Upstream-PR compatibility.** Phase 0 through Phase 2 of the roadmap are
       the target upstream bundle. Landing these four primitives upstream benefits
       every template, not just gstack — hedge-fund could contribute a
       `market-close` phase, research-paper could contribute a `peer-review`
       phase, etc.

    ## 3. Guide-level Explanation

    A plugin author who wants to add a new lifecycle phase writes a subclass of
    `HarnessPlugin` that returns the phase names from `contribute_phases()`:

    ```python
    class GstackSprintPlugin(HarnessPlugin):
        def contribute_phases(self) -> list[Phase]:
            return ["think", "plan", "build", "review", "test", "ship", "reflect"]
    ```

    When `HarnessOrchestrator` is constructed, it iterates over loaded plugins and
    collects their phase contributions into a `PhaseRegistry`. If the constructor
    is called with `phases=None`, it consults the registry; if called with an
    explicit list, it bypasses the registry (preserving existing behavior for
    templates that still pin their phase set in TOML).

    Phase-name collisions across plugins raise `ValueError` at registration time:

    ```python
    registry = PhaseRegistry()
    registry.register(phases=["think", "plan", "ship"], owner="GstackSprintPlugin")
    registry.register(phases=["plan"], owner="OtherPlugin")  # ValueError: 'plan' already registered by GstackSprintPlugin
    ```

    Sprint state is explicit and persistent. Starting a sprint creates a pydantic
    record:

    ```python
    SprintState(
        sprint_id="2026-04-16-dark-mode-toggle",
        goal="Add a dark-mode toggle to the settings page",
        team="my-gstack-team",
        current_phase="think",
        workspace_branch="sprint/dark-mode-toggle",
        auto_advance=True,
    )
    ```

    Persisted atomically at `~/.clawteam/teams/my-gstack-team/sprints/2026-04-16-dark-mode-toggle/state.json` via
    the existing `file_locked()` context manager from `clawteam/fileutil.py`.

    Blocking phase advance on a human answer:

    ```python
    # During the Plan phase, the CEO agent writes:
    #   sprints/<id>/questions/001.md  ("Reduce scope to toggle only, no theme preview?")
    # Phase advance is blocked by InteractionGate until a sibling file exists:
    #   sprints/<id>/answers/001.md   (human's reply)
    gate = InteractionGate(sprint_id="2026-04-16-dark-mode-toggle")
    ok, reason = gate.can_advance(state)
    # ok=False, reason="Open questions: 001.md"
    ```

    ## 4. Reference-level Explanation

    ### 4.1 PhaseRegistry

    Location: `clawteam/harness/phase_registry.py` (new file).

    ```python
    """In-memory registry of plugin-contributed phase names."""

    from __future__ import annotations

    from dataclasses import dataclass, field

    from clawteam.harness.phases import Phase


    @dataclass
    class PhaseRegistry:
        """Phase-name registry populated by HarnessPlugin.contribute_phases().

        Constructed empty; plugins call ``register`` once at load time. The
        ``HarnessOrchestrator`` consults the registry when ``phases=None`` is
        passed to its constructor.
        """

        _phases: list[Phase] = field(default_factory=list)
        _owners: dict[Phase, str] = field(default_factory=dict)

        def register(self, phases: list[Phase], owner: str) -> None:
            """Add *phases* under *owner*. Raises ValueError on collision."""
            for phase in phases:
                if phase in self._owners:
                    raise ValueError(
                        f"Phase {phase!r} already registered by {self._owners[phase]!r}"
                    )
                self._phases.append(phase)
                self._owners[phase] = owner

        @property
        def phases(self) -> list[Phase]:
            return list(self._phases)

        def is_empty(self) -> bool:
            return not self._phases
    ```

    ### 4.2 HarnessPlugin.contribute_phases()

    Location: `clawteam/plugins/base.py` (add new optional method to existing ABC).

    ```python
    from clawteam.harness.phases import Phase


    class HarnessPlugin(ABC):
        # ... existing contribute_gates, contribute_prompts ...

        def contribute_phases(self) -> list[Phase]:
            """Return phase names this plugin wants to register. Default: none."""
            return []
    ```

    Default implementation returns an empty list, so existing plugins
    (`RalphLoopPlugin`, any user plugin) need no changes.

    `clawteam/plugins/manager.py` iterates loaded plugins at startup and calls
    `contribute_phases()` on each, passing the result to a shared `PhaseRegistry`
    instance. Registration is one-shot per plugin; reloading plugins recreates the
    registry.

    ### 4.3 SprintState

    Location: `clawteam/sprint/state.py` (new subpackage).

    ```python
    """Pydantic model for sprint lifecycle state."""

    from __future__ import annotations

    from datetime import datetime

    from pydantic import BaseModel, Field

    from clawteam.harness.phases import Phase


    class SprintState(BaseModel):
        sprint_id: str
        goal: str
        team: str
        current_phase: Phase
        phase_history: list[str] = Field(default_factory=list)
        artifacts: list[str] = Field(default_factory=list)
        participants: list[str] = Field(default_factory=list)
        pending_question_ids: list[str] = Field(default_factory=list)
        auto_advance: bool = True
        workspace_branch: str = ""
        created_at: datetime = Field(default_factory=datetime.utcnow)
    ```

    Persistence: `~/.clawteam/teams/<team>/sprints/<sprint_id>/state.json`, written
    via `clawteam.fileutil.atomic_write_text` under a `file_locked()` guard on a
    sibling `.lock` file.

    Validation:
    - `sprint_id`, `team` validated through `clawteam.paths.validate_identifier`
      (reuses the existing filesystem-identifier regex `^[A-Za-z0-9._-]+$`).
    - `current_phase` is an arbitrary string; validation that it exists in the
      registry is the caller's concern (the model stays Phase-agnostic).

    ### 4.4 InteractionGate

    Location: `clawteam/harness/interaction_gate.py` (new file).

    ```python
    """PhaseGate that blocks advance until posted questions have answers."""

    from __future__ import annotations

    from pathlib import Path

    from clawteam.harness.phases import Phase, PhaseGate
    from clawteam.sprint.state import SprintState
    from clawteam.team.models import get_data_dir


    class InteractionGate(PhaseGate):
        def __init__(self, sprint_id: str, team: str) -> None:
            self._sprint_id = sprint_id
            self._team = team

        def can_advance(self, state: SprintState) -> tuple[bool, str]:
            questions_dir = (
                get_data_dir()
                / "teams" / self._team
                / "sprints" / self._sprint_id
                / "questions"
            )
            answers_dir = questions_dir.parent / "answers"
            if not questions_dir.exists():
                return True, ""
            open_questions = [
                q.name for q in questions_dir.glob("*.md")
                if not (answers_dir / q.name).exists()
            ]
            if open_questions:
                return False, f"Open questions: {', '.join(sorted(open_questions))}"
            return True, ""
    ```

    Pairing: plugins register `InteractionGate` on specific phases via
    `HarnessPlugin.contribute_gates(phase)`. gstack's Ship phase, for example,
    always installs an `InteractionGate` regardless of `auto_advance=True`
    (per REQUIREMENTS.md SPRINT-05 "Ship phase always requires human approval").

    ## 5. Drawbacks

    1. **Plugin authoring surface grows.** Three new primitives means three new
       documentation obligations and three new abstractions a newcomer must learn.
       Mitigation: the defaults are empty/opt-in; plugins that don't touch phases
       don't see any of this.

    2. **PhaseRegistry is global-ish state.** The registry is owned by
       `HarnessOrchestrator`, but plugins consult it indirectly. Tests that
       construct multiple orchestrators in the same process must isolate the
       registry. Mitigation: the orchestrator constructs its own registry
       instance; the registry is not a singleton.

    3. **SprintState proliferation.** If every template starts shipping sprints,
       `~/.clawteam/teams/<team>/sprints/` directories can grow unbounded.
       Mitigation: Phase 7 lands disk-budget alarms + zombie-sprint auto-GC
       (REQUIREMENTS.md QUALITY-04, QUALITY-05).

    4. **InteractionGate assumes file-based question/answer pairing.** Alternate
       transports (HTTP, WebSocket, board-UI) would need their own gate subclass.
       Mitigation: `PhaseGate` is already pluggable; `InteractionGate` is one of
       many possible implementations. The file-based version is the MVP.

    ## 6. Rationale and Alternatives

    **Why not extend `PhaseState` directly?** Adding members to the existing enum
    would break backward compatibility: every existing template's serialized
    `PhaseState.phases` list is the full `DEFAULT_PHASES` unless TOML overrides
    it. A `PhaseRegistry` lets plugins add vocabulary without touching the default
    enum.

    **Why not a new `HarnessV2` orchestrator?** Would fork the codebase into two
    parallel orchestrators, doubling maintenance. The registry approach preserves
    a single `HarnessOrchestrator` and adds optional contribution hooks.

    **Why a pydantic model instead of a TypedDict for SprintState?** pydantic v2
    is already the project standard (`clawteam/config.py`, `clawteam/team/models.py`,
    `clawteam/harness/phases.py::PhaseState` are all pydantic v2 `BaseModel`
    subclasses). Using it here keeps validation, JSON serialization, and schema
    evolution consistent with the rest of the codebase.

    **Why file-based question/answer pairing in InteractionGate?** Aligns with
    the existing `clawteam/fileutil.py::file_locked` / `atomic_write_text`
    machinery and avoids introducing a new transport for v1. The file-based
    approach is diff-friendly, offline-safe, and reviewable with `git log`.

    **Alternative: global singleton registry.** Rejected; test isolation is
    easier with per-orchestrator instances, and real deployments only construct
    one orchestrator per process.

    **Alternative: enum-based Phase type.** Rejected; the existing `Phase = str`
    alias in `clawteam/harness/phases.py:20` is already an intentional choice to
    allow plugin extension. Preserving it keeps the diff minimal.

    ## 7. Prior Art

    - **Python PEP process** — pure-Markdown proposals with a status field, authors,
      and numbered sections. Our template is a simplified Rust-RFC shape (no
      Final-Comment-Period ceremony, no bot automation) but the underlying idea is
      the same.
    - **Rust RFCs (rust-lang/rfcs)** — 0000-template.md is the direct template
      source. We omit the "Motivation" sub-bullets (Guide / Reference) that Rust
      RFCs separate and fold them into sections 3 and 4.
    - **Django DEPs** — precedent for a framework fork driving upstream changes
      through explicit proposals before code.
    - **Kubernetes KEPs** — per-feature granularity matches our per-phase
      granularity; KEPs inspired our "target phase" metadata field.

    ## 8. Unresolved Questions

    1. **Windows CI matrix parity.** Phase 0 does not commit to adding Windows to
       the CI test matrix. Should Phase 1's `PhaseRegistry` / `InteractionGate`
       tests explicitly skip on Windows until the matrix extends, or assume a
       future `windows-latest` runner will pick them up? Recommendation: write
       the tests platform-agnostically; defer the CI matrix decision to a future
       RFC.

    2. **SprintState schema evolution.** The initial schema is 11 fields. If
       subsequent phases add fields (e.g., `parent_sprint_id`, `cost_budget_usd`),
       pydantic v2's `model_validate` tolerates missing optional fields on load
       but breaks on rename. Recommendation: all additions are optional with
       defaults; renames require a migration script + version bump.

    3. **PhaseRegistry ordering semantics.** If two plugins register disjoint
       phase lists, the order of the final `PhaseRegistry.phases` is the load
       order of the plugins. Is this acceptable, or should phases carry explicit
       `position` hints? Recommendation: start with load-order; add position
       hints only if a concrete conflict emerges.

    4. **InteractionGate timeout semantics.** If a question sits unanswered for
       a long time, should the gate ever auto-release with a default answer?
       Recommendation: NO for v1 — gstack's explicit human-in-loop design is
       the product. Timeout behavior is a Phase 7 AttentionQueue concern.

    ## Worked Example: software-dev.toml unchanged

    The critical invariant is that the existing six templates continue to work
    UNCHANGED after this RFC lands. The trace below follows `software-dev.toml`
    through a spawn, showing that the proposed API adds nothing observable.

    ### Before (current code)

    ```text
    $ clawteam launch software-dev --team dev-smoke --goal "Smoke test"
    ├─ clawteam.cli.commands::launch
    │  └─ load_template("software-dev")
    │     ├─ reads clawteam/templates/software-dev.toml
    │     └─ returns TemplateDef(phases=None, ...)
    ├─ HarnessOrchestrator.__init__(..., phases=None)
    │  └─ self.state.phases = list(DEFAULT_PHASES)   # [DISCUSS, PLAN, EXECUTE, VERIFY, SHIP]
    ├─ For each agent in template:
    │  └─ spawn_backend.spawn(team="dev-smoke", agent_name=..., command=..., env=...)
    └─ exit 0
    ```

    ### After (with RFC 001 landed)

    ```text
    $ clawteam launch software-dev --team dev-smoke --goal "Smoke test"
    ├─ clawteam.cli.commands::launch
    │  └─ load_template("software-dev")
    │     ├─ reads clawteam/templates/software-dev.toml
    │     └─ returns TemplateDef(phases=None, ...)
    ├─ HarnessOrchestrator.__init__(..., phases=None, plugins=[])
    │  ├─ registry = PhaseRegistry()                  # NEW, but empty (no plugins)
    │  ├─ for plugin in []: registry.register(...)    # NEW, but no-op
    │  └─ self.state.phases = (
    │        registry.phases                           # NEW, but [] here
    │        or list(DEFAULT_PHASES)                   # fallback preserved
    │     )                                            # → [DISCUSS, PLAN, EXECUTE, VERIFY, SHIP]
    ├─ For each agent in template:
    │  └─ spawn_backend.spawn(team="dev-smoke", agent_name=..., command=..., env=...)
    └─ exit 0
    ```

    Differences:
    - `HarnessOrchestrator.__init__` now constructs a `PhaseRegistry` unconditionally.
      Cost: one dataclass instantiation. Observable behavior: none.
    - Plugin loop runs over `plugins=[]` (software-dev loads no plugins by default).
      Cost: zero iterations. Observable behavior: none.
    - `self.state.phases` becomes `registry.phases or list(DEFAULT_PHASES)`. With an
      empty registry, the fallback branch is taken and produces the exact same
      list as before. Observable behavior: none.

    The Phase 0 backwards-compatibility regression matrix
    (`tests/test_template_regression_matrix.py`, landed in plan 00-04) verifies
    this invariant by spawning every packaged template through `clawteam launch`
    and asserting exit 0 + non-empty spawn calls. That test must continue to pass
    after Phase 1 lands.

    ### Additive-only guarantees summary

    | Existing Contract | Phase 1 Behavior |
    |-------------------|------------------|
    | `clawteam launch <template>` produces the same exit code as before | Preserved — empty registry falls back to DEFAULT_PHASES |
    | `PhaseState.phases` shape for existing templates | Unchanged |
    | `HarnessPlugin` ABC — subclasses that only override `contribute_gates` / `contribute_prompts` | Unchanged — `contribute_phases` has an empty-list default |
    | Serialized harness state JSON format | Unchanged for existing templates (no sprint data written) |
    | Existing `PhaseGate` gates | Unchanged — `InteractionGate` is a NEW subclass, not a replacement |
    | File paths under `~/.clawteam/teams/<team>/` | NEW `sprints/` subdirectory, only created when a sprint is started |

    ---

    **Mirror**: This RFC is mirrored at `docs/rfcs/001-phase-registry.md` in the
    ClawTeam-gstack fork. Implementation plans reference the RFC number regardless
    of upstream merge status.

    **Maintainer acknowledgement**: Pending. (Target: open upstream PR against
    `HKUDS/ClawTeam` with just this markdown; obtain ≥1 maintainer ack before
    Phase 1 code lands, per ROADMAP.md Phase 0 success criterion 4.)
    ```

    Rules (per PATTERNS.md §docs/rfcs/001-phase-registry.md):
    - 8-section numbered structure matches orchestrator prompt: Summary, Motivation, Guide-level explanation, Reference-level API, Drawbacks, Rationale and Alternatives, Prior art, Unresolved questions.
    - YAML frontmatter block: rfc, title, status (Draft), authors, created (2026-04-15), target-phase. Non-parsed by runtime code; human-read only.
    - ASCII box diagrams in Worked Example section — tree-view is acceptable for this kind of trace (matches the project's multilingual doc style; not every diagram needs pure Unicode box-drawing characters).
    - Neutral technical prose — no marketing adjectives ("powerful", "best-in-class"), no exclamation points, no emoji.
    - Numbered H2 sections (`## 1. Summary`, `## 2. Motivation`, …) — matches `docs/transport-architecture.md` convention.
    - Code blocks use language-tagged fences (` ```python `, ` ```text `, ` ```toml `).
    - No actual code changes in this plan — the RFC is a markdown PROPOSAL. The Phase 1 plan will implement what this RFC specifies.
    - Mirror note at the end: establishes that this lives in the fork regardless of upstream merge timing (RESEARCH.md Pitfall #5 prevention).

    What NOT to do:
    - Do NOT use `pyyaml` or any tool to parse the frontmatter — it's informational.
    - Do NOT include MADR (Markdown Any Decision Records) formatting — RESEARCH.md explicitly rejects that in favor of Rust-style.
    - Do NOT embed clickable maintainer names / emails in the frontmatter — the upstream PR is the acknowledgement channel, not this file.
    - Do NOT commit placeholder links to unwritten future RFCs.
    - Do NOT duplicate the worked example tree trace in the index README; the README stays short.
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && test -f docs/rfcs/001-phase-registry.md && grep -qE "^# RFC 001" docs/rfcs/001-phase-registry.md && grep -qE "^## 1\. Summary" docs/rfcs/001-phase-registry.md && grep -qE "^## 2\. Motivation" docs/rfcs/001-phase-registry.md && grep -qE "^## 3\. Guide-level" docs/rfcs/001-phase-registry.md && grep -qE "^## 4\. Reference-level" docs/rfcs/001-phase-registry.md && grep -qE "^## 5\. Drawbacks" docs/rfcs/001-phase-registry.md && grep -qE "^## 6\. Rationale" docs/rfcs/001-phase-registry.md && grep -qE "^## 7\. Prior Art" docs/rfcs/001-phase-registry.md && grep -qE "^## 8\. Unresolved" docs/rfcs/001-phase-registry.md && grep -q "PhaseRegistry" docs/rfcs/001-phase-registry.md && grep -q "contribute_phases" docs/rfcs/001-phase-registry.md && grep -q "InteractionGate" docs/rfcs/001-phase-registry.md && grep -q "SprintState" docs/rfcs/001-phase-registry.md && grep -q "software-dev" docs/rfcs/001-phase-registry.md && wc -l docs/rfcs/001-phase-registry.md | awk '{ if ($1 >= 300) print "OK len=" $1; else print "FAIL len=" $1; exit ($1 >= 300 ? 0 : 1) }'</automated>
  </verify>
  <done>
    `docs/rfcs/001-phase-registry.md` exists with frontmatter (rfc=001, status=Draft, target-phase=Phase 1), all 8 numbered sections, named references to PhaseRegistry / contribute_phases / InteractionGate / SprintState, a worked example showing software-dev.toml unchanged, a "Mirror" closing note. Length ≥300 lines.
  </done>
</task>

</tasks>

<threat_model>
N/A — documentation only. No code changes in this plan; no trust boundaries crossed by Markdown files. The RFC proposes security-adjacent primitives (InteractionGate), but their threat analysis belongs to the Phase 1 implementation plan that lands them.

If future-proofing is needed: the only way an RFC document can itself be a threat is via typosquatting in the `Authors` field or a malicious link in the frontmatter. Both are caught by standard PR review. No active mitigation required in this plan.
</threat_model>

<verification>
Phase-level verification:

```bash
cd /home/jac/repos/ClawTeam-gstack
# Files exist
test -f docs/rfcs/README.md && test -f docs/rfcs/001-phase-registry.md && echo "Files OK"

# 8-section structure
for section in "1\. Summary" "2\. Motivation" "3\. Guide-level" "4\. Reference-level" "5\. Drawbacks" "6\. Rationale" "7\. Prior Art" "8\. Unresolved"; do
  grep -qE "^## $section" docs/rfcs/001-phase-registry.md || echo "MISSING: $section"
done
echo "Section structure verified"

# Required identifiers appear
for token in "PhaseRegistry" "contribute_phases" "InteractionGate" "SprintState" "software-dev" "HarnessPlugin" "Phase 1"; do
  grep -q "$token" docs/rfcs/001-phase-registry.md || echo "MISSING TOKEN: $token"
done

# Length sanity
wc -l docs/rfcs/001-phase-registry.md
# Expect: ≥300 lines (8 numbered sections + worked example + frontmatter)

# README index references the RFC
grep -q "001-phase-registry.md" docs/rfcs/README.md && echo "README index OK"
```

Expected:
- Both files exist.
- RFC contains all 8 numbered sections.
- All required identifiers (PhaseRegistry, contribute_phases, InteractionGate, SprintState, software-dev, HarnessPlugin, Phase 1) appear.
- Length ≥300 lines (8 sections + worked example + metadata cannot be under 300 lines if written properly).
- README.md links to 001-phase-registry.md.

Optional manual step (not a test gate — out-of-band):
- Open a PR against `HKUDS/ClawTeam` main branch containing these two files. Tag a maintainer. This is the action that satisfies ROADMAP.md Phase 0 success criterion 4's "≥1 maintainer acknowledgement" — but the ack itself is ASYNC and tracked in ROADMAP, not in this plan's success criteria.
</verification>

<success_criteria>
1. `docs/rfcs/` directory exists at repo root.
2. `docs/rfcs/README.md` exists as a minimal RFC index with a Markdown table listing RFC 001 as Draft targeting Phase 1.
3. `docs/rfcs/001-phase-registry.md` exists with YAML frontmatter (rfc=001, status=Draft, target-phase="Phase 1 of gstack-integration roadmap (v1)", created=2026-04-15).
4. RFC has all 8 numbered sections: Summary, Motivation, Guide-level Explanation, Reference-level Explanation, Drawbacks, Rationale and Alternatives, Prior Art, Unresolved Questions.
5. RFC names and specifies all four Phase 1 primitives: `PhaseRegistry`, `HarnessPlugin.contribute_phases()`, `SprintState`, `InteractionGate` — each with a code sketch in the Reference-level section.
6. RFC has a Worked Example section showing `software-dev.toml` unchanged before/after the RFC lands (explicit CORE-03 + QUALITY-14 guarantee).
7. RFC closes with a "Mirror" note establishing that this file lives in the fork regardless of upstream PR merge status (RESEARCH.md Pitfall #5 prevention).
8. No code changes in this plan — two markdown files only.
9. File length ≥300 lines for the RFC (8 sections + worked example + frontmatter cannot be meaningfully shorter).
10. Automated verification (all 8 sections present, all key identifiers present, length sanity check) exits 0.
</success_criteria>

<output>
After completion, create `.planning/phases/00-foundation-upstream-rfc/00-05-SUMMARY.md` following `@$HOME/.claude/get-shit-done/templates/summary.md`, documenting:
- docs/rfcs/ directory established with README index + RFC 001
- RFC 001 sections: summary of each of the 8 sections (1-line each)
- Phase 1 primitives specified: PhaseRegistry, HarnessPlugin.contribute_phases(), SprintState, InteractionGate
- Worked example demonstrates software-dev.toml unchanged (CORE-03 guarantee)
- **Out-of-band follow-up** (not this plan's responsibility): human owner to open upstream PR against HKUDS/ClawTeam tagging a maintainer; track the maintainer-ack status in ROADMAP.md Phase 0 success criterion 4
- RFC process scaffold established for future Phase 2+ RFCs (if any are needed)
</output>
