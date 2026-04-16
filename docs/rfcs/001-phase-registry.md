---
rfc: 001
title: PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate
status: Draft
authors: ClawTeam-gstack fork contributors
created: 2026-04-15
target-phase: Phase 1
---

# RFC 001: Plugin-Populated Phase Registry with Sprint State and Interactive Gates

## 1. Summary

This RFC proposes four additive primitives for the ClawTeam harness:

1. `PhaseRegistry`
2. `HarnessPlugin.contribute_phases()`
3. `InteractionGate`
4. `SprintState`

The goal is to let plugins introduce new lifecycle phases, persist sprint-level
state, and block phase transitions on explicit human response without changing
the semantics of existing templates or replacing the current open-string phase
model.

The proposal is intentionally narrow. It does not add gstack-specific business
logic to core, does not change the default phase list for existing templates,
and does not require new runtime dependencies beyond the packages already used
by ClawTeam core.

At a high level, the runtime model is:

```text
┌─────────────────────┐
│ Existing templates  │
│ software-dev, etc.  │
└──────────┬──────────┘
           │ no plugin phase contribution
           ▼
┌─────────────────────┐
│ DEFAULT_PHASES      │
│ discuss→plan→...    │
└─────────────────────┘

┌─────────────────────┐
│ Plugin-defined      │
│ template            │
│ e.g. gstack later   │
└──────────┬──────────┘
           │ contribute_phases()
           ▼
┌─────────────────────┐
│ PhaseRegistry       │
│ plugin-defined set  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ PhaseState.phases   │
│ plugin-defined flow │
└─────────────────────┘
```

The additive compatibility contract is:

1. `Phase` remains `str`.
2. `DEFAULT_PHASES` remains the fallback for templates that do not opt in.
3. `HarnessPlugin.contribute_phases()` defaults to an empty list.
4. `InteractionGate` is opt-in and only runs when a phase or sprint uses it.
5. `SprintState` is new persistence surface; existing harness state files stay
   valid.

## 2. Motivation

ClawTeam already models phases as open strings:

```python
Phase = str  # allow plugin extension without Enum rewrites
```

That choice is materially useful. It means the core system has already rejected
the assumption that the phase vocabulary must be closed. What is missing is the
registration path that turns that open type into a supported extension surface.

Today, plugins can contribute gates and prompts, but they cannot contribute the
phase list itself. Adding a new lifecycle phase therefore requires a core edit
to `DEFAULT_PHASES` or an equivalent override path inside the harness
orchestrator. That creates three problems.

First, it breaks the upstream compatibility objective. The gstack fork wants to
propose a general extension mechanism, not a one-off hard-coded seven-phase
workflow.

Second, it couples future templates to a single global phase vocabulary. A
research template, a hedge-fund template, and a sprint-oriented engineering
template do not need the same phase graph. They need a small shared contract and
room to specialize.

Third, it leaves interactive human checkpoints as ad hoc behavior. ClawTeam has
gates, but no built-in primitive for "wait until a human answers the written
question artifact". That pattern is central to the fork's product shape and is
also generally useful outside the fork.

The proposal therefore treats four pieces as a coherent substrate:

1. Phase contribution
2. Phase lookup
3. Persistent sprint context
4. Human-response gating

The intended result is not "gstack inside core". The intended result is "core
knows how to host alternative phase vocabularies safely".

## 3. Guide-Level Explanation

### 3.1. Mental Model

An operator using an existing template sees no behavior change. The template
still loads, still uses the current phase list, and still advances through the
current gates.

A plugin author targeting a new workflow gets one new hook:

```python
class GstackSprintPlugin(HarnessPlugin):
    def contribute_phases(self) -> list[Phase]:
        return [
            "think",
            "plan",
            "build",
            "review",
            "test",
            "ship",
            "reflect",
        ]
```

The harness loads plugins, asks each one for contributed phases, registers those
phases in `PhaseRegistry`, and then uses the registry output when constructing a
harness run or sprint run that opts into plugin-defined phases.

The control flow is:

```text
┌──────────────┐
│ Plugin load  │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────┐
│ HarnessPlugin.contribute_phases()   │
│ returns [] or ["think", ...]        │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ PhaseRegistry.register(plugin, ...) │
│ rejects duplicate names             │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│ Harness creates phase list          │
│ plugin phases or DEFAULT_PHASES     │
└─────────────────────────────────────┘
```

### 3.2. Sprint State

`SprintState` is a new persisted model representing one sprint of work for one
team. Teams already exist as durable units. This proposal adds a durable work
unit that can survive restarts, pauses, and future CLI flows such as `start`,
`status`, `show`, `pause`, and `resume`.

The operator-facing mental model is:

```text
team/
└── sprints/
    └── <sprint-id>/
        ├── state.json
        ├── questions/
        │   └── 001.md
        └── answers/
            └── 001.md
```

When a phase needs human input, it writes a question artifact. `InteractionGate`
checks whether the matching answer artifact exists. If not, the phase remains
blocked and the system reports that there are open questions.

### 3.3. Worked Example Constraint

This RFC does not require changes to `clawteam/templates/software-dev.toml`. The
proposal is specifically designed so the existing template remains valid and
observably unchanged.

The reason is simple:

1. `software-dev.toml` does not need sprint-specific phases.
2. It does not ship a plugin that calls `contribute_phases()`.
3. The harness therefore falls back to `DEFAULT_PHASES`.
4. No new required fields are added to the template format.

The remainder of this RFC uses the `software-dev` template as the compatibility
baseline.

## 4. Reference-Level API

### 4.1. Scope

This section specifies the Phase 1 API surface only. It is normative for the
four primitives named in the summary. It does not attempt to define future
review routing hooks, sprint conductor APIs, or evidence-gate schemas.

### 4.2. `PhaseRegistry`

`PhaseRegistry` is a new in-memory registry module located at
`clawteam/harness/phase_registry.py`.

Responsibilities:

1. Accept phase contributions from plugins during plugin load.
2. Preserve registration order.
3. Reject duplicate phase names at registration time.
4. Provide a read-only ordered phase list for harness initialization.

Non-responsibilities:

1. Persist sprint state.
2. Evaluate gates.
3. Choose agent roles.
4. Interpret gstack semantics.

Suggested shape:

```python
from __future__ import annotations

from dataclasses import dataclass

from clawteam.harness.phases import Phase


@dataclass(frozen=True)
class RegisteredPhase:
    name: Phase
    plugin_name: str


class PhaseRegistry:
    def __init__(self) -> None:
        self._phases: list[RegisteredPhase] = []
        self._names: set[str] = set()

    def register(self, plugin_name: str, phases: list[Phase]) -> None:
        for phase in phases:
            if phase in self._names:
                raise ValueError(f"Duplicate phase registration: {phase}")
            self._phases.append(RegisteredPhase(name=phase, plugin_name=plugin_name))
            self._names.add(phase)

    def ordered_names(self) -> list[Phase]:
        return [entry.name for entry in self._phases]
```

Behavioral requirements:

1. Registration order is stable and deterministic within one process.
2. Name collision is fatal at registration time.
3. Empty registry is valid.
4. Empty registry implies fallback to `DEFAULT_PHASES`.

Expected initialization path:

```text
┌─────────────────────┐
│ Load plugin manager │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ For each plugin     │
│ call contribute_    │
│ phases()            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Register results    │
│ into PhaseRegistry  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Harness picks       │
│ registry names or   │
│ DEFAULT_PHASES      │
└─────────────────────┘
```

### 4.3. `HarnessPlugin.contribute_phases()`

`HarnessPlugin` gains a new optional hook:

```python
def contribute_phases(self) -> list[Phase]:
    return []
```

Requirements:

1. The default implementation returns an empty list.
2. Existing plugins are not required to implement the hook.
3. The hook is additive and side-effect free from the harness point of view.
4. The plugin manager calls it during registration, before harness execution.

The empty default matters because it makes the extension invisible to all
existing templates and plugins unless they explicitly opt in.

The intended relation to the current plugin base class is:

```text
┌────────────────────────────┐
│ HarnessPlugin              │
├────────────────────────────┤
│ on_register(ctx)           │
│ on_unregister()            │
│ contribute_gates()         │
│ contribute_prompts()       │
│ contribute_phases()  NEW   │
└────────────────────────────┘
```

No other plugin methods need semantic changes to support this RFC.

### 4.4. `SprintState`

`SprintState` is a new pydantic v2 model located at
`clawteam/sprint/state.py`.

Required fields:

1. `sprint_id`
2. `goal`
3. `team`
4. `current_phase`
5. `phase_history`
6. `artifacts`
7. `participants`
8. `pending_question_ids`
9. `auto_advance`
10. `workspace_branch`
11. `created_at`

Suggested shape:

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class SprintState(BaseModel):
    sprint_id: str
    goal: str
    team: str
    current_phase: str
    phase_history: list[dict[str, str]] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    participants: list[str] = Field(default_factory=list)
    pending_question_ids: list[str] = Field(default_factory=list)
    auto_advance: bool = True
    workspace_branch: str = ""
    created_at: str
```

Persistence requirements:

1. The model round-trips through existing atomic JSON persistence mechanisms.
2. The canonical file path is
   `~/.clawteam/teams/<team>/sprints/<id>/state.json`.
3. Writes use the existing `file_locked()` machinery rather than a new lock
   implementation.
4. Existing harness state files remain separate and unchanged.

`SprintState` deliberately describes sprint lifecycle state, not whole-team
configuration. Team configuration remains where it already lives.

### 4.5. `InteractionGate`

`InteractionGate` is a new `PhaseGate` subclass located at
`clawteam/harness/interaction_gate.py`.

Its job is to block phase advance while required questions remain unanswered.

Suggested behavioral contract:

```python
def check(self, state: SprintState | PhaseState) -> tuple[bool, str]:
    ...
```

Normative behavior:

1. If `questions/<N>.md` exists and `answers/<N>.md` does not exist, return
   `(False, "Open questions: <list>")`.
2. If every required answer exists, return `(True, "")`.
3. The gate does not parse human intent beyond presence checks in Phase 1.
4. The gate is reusable by any template or plugin that writes the same artifact
   layout.

Expected directory contract:

```text
sprints/<id>/
├── questions/
│   ├── 001.md
│   └── 002.md
└── answers/
    ├── 001.md
    └── 002.md
```

Evaluation flow:

```text
┌──────────────────────┐
│ Phase wants advance  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ InteractionGate      │
│ scans questions/*    │
└──────────┬───────────┘
           │
      ┌────┴────┐
      │ answers │
      │ missing?│
      └────┬────┘
           │ yes
           ▼
┌──────────────────────┐
│ return False,        │
│ "Open questions:..." │
└──────────────────────┘

           │ no
           ▼
┌──────────────────────┐
│ return True, ""      │
└──────────────────────┘
```

### 4.6. Integration Contract

The four primitives are expected to compose as follows:

```text
┌────────────────────────────────────────────────────────────┐
│ Plugin registration                                       │
│  - contribute_phases()                                   │
│  - PhaseRegistry                                          │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│ Sprint execution                                           │
│  - SprintState tracks current phase                        │
│  - InteractionGate blocks on unanswered questions          │
└────────────────────────────────────────────────────────────┘
```

This composition is sufficient for Phase 1 without requiring broader core
changes.

### 4.7. Compatibility Guarantees

The proposal is additive-only under the following guarantees:

1. No existing template file must change.
2. No existing plugin must implement a new abstract method.
3. No existing phase name must be renamed.
4. Existing `Phase = str` remains valid.
5. Existing default phase execution remains the fallback when the registry is
   empty.

These guarantees are the primary acceptance condition for upstream review.

### 4.8. Worked Example: `software-dev.toml` Remains Unchanged

The compatibility baseline is the existing template header:

```toml
[template]
name = "software-dev"
description = "Software Development Team - multi-agent full-stack development with parallel workstreams"
command = ["claude"]
backend = "tmux"
```

Under this RFC, the file remains unchanged before and after Phase 1 core code
lands.

Before:

```text
software-dev.toml
  └─ no plugin phase contribution
     └─ harness uses DEFAULT_PHASES
```

After:

```text
software-dev.toml
  └─ no plugin phase contribution
     └─ PhaseRegistry is empty for this template
        └─ harness still uses DEFAULT_PHASES
```

Observable behavior stays the same:

1. The template still loads through the current template machinery.
2. It still spawns the same agents.
3. It still advances through the default phase sequence.
4. It does not require `SprintState`.
5. It does not incur `InteractionGate` unless a future plugin opts into it.

The worked example is important because it fixes the compatibility promise in
concrete terms: this RFC extends core without rewriting the default template
story.

## 5. Drawbacks

This RFC adds new surface area to the harness. Even when the defaults are empty,
new APIs have maintenance cost.

Specific drawbacks:

1. `PhaseRegistry` introduces one more initialization path that must remain
   deterministic.
2. Registration-time duplicate detection creates a new failure mode during
   plugin load.
3. `SprintState` adds a second persisted state concept beside the current
   harness state.
4. `InteractionGate` establishes a file-layout convention for questions and
   answers that later implementations should preserve.

There is also a documentation burden. Once core exposes these names, future
templates and plugins will rely on them. That is why this RFC is being written
before the implementation lands.

## 6. Rationale and Alternatives

### 6.1. Why Registry Instead of Hard-Coding More Defaults

Hard-coding more defaults solves the immediate fork use case but fails the
upstream objective. It also assumes all templates want one shared canonical
phase set. The existing open-string `Phase` type already points in the opposite
direction.

### 6.2. Why an Empty Hook Default

The hook must not be abstract. If `HarnessPlugin` gained an abstract
`contribute_phases()` method, every existing plugin would become invalid. The
empty list default is the minimal additive contract.

### 6.3. Why `SprintState` as a New Model

An alternative would be to overload `PhaseState` with sprint-specific fields.
That is less clear. `PhaseState` describes one harness run. `SprintState`
describes one sprint lifecycle instance. Separate models make the fork's future
CLI story and persistence story easier to evolve without reinterpreting the
existing file format.

### 6.4. Why File-Based `InteractionGate`

An alternative would be to block on queue state, inbox state, or event bus
state. The file-based design is chosen because it is inspectable, restart-safe,
and aligned with the repository's existing preference for file-backed durable
state. It also gives a human-readable artifact trail.

### 6.5. Why Presence Check in Phase 1

A stricter design could parse answer schemas immediately. This RFC does not
require that. Phase 1 only needs a reusable primitive that can say "there are
unanswered questions". Schema-level validation can be layered on later.

## 7. Prior Art

This RFC follows the extension style already present in ClawTeam:

1. Plugins already contribute gates.
2. Plugins already contribute prompts.
3. Phase names are already open strings rather than an enum.
4. Durable state is already stored through file-backed JSON and lock helpers.

It also follows the document style used by upstream architecture notes: numbered
sections, ASCII diagrams, and neutral technical prose rather than design-by-
assertion.

Outside this repository, the proposal is structurally similar to:

1. Registry-based extension points used by plugin systems that separate core
   orchestration from domain-specific workflow definitions.
2. RFC processes used by Rust and similar projects to lock API expectations
   before code lands.
3. File-backed workflow checkpoints used by tools that must survive process
   restart and human interruption.

The key point is not originality. The key point is that ClawTeam already has the
right partial abstractions; this RFC connects them into a stable extension path.

## 8. Unresolved Questions

This RFC intentionally leaves several questions open for later phases or later
RFCs.

1. Should future versions of `PhaseRegistry` register only names, or should they
   also carry metadata such as default gates and role hints?
2. Should the plugin manager maintain one global registry, or should the harness
   build a per-run registry scoped to the selected template?
3. Should `InteractionGate` operate on `SprintState` only, or should it accept
   `PhaseState` whenever the required question directory exists?
4. Should question and answer files be normalized to a formal frontmatter schema
   in Phase 1, or left as presence-based artifacts initially?
5. How should future upstream work define optional phase-role mapping without
   overloading this initial RFC?
6. What is the migration story, if any, for templates that eventually want both
   default phases and additional plugin phases rather than a full replacement
   list?

None of these open questions block the narrow Phase 1 substrate. They are
intentionally excluded so the initial upstream proposal stays additive, small,
and reviewable.
