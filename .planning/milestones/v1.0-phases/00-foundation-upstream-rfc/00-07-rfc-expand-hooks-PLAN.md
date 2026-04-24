---
phase: 00-foundation-upstream-rfc
plan: 07
type: execute
wave: 3
depends_on: [00-05]
files_modified:
  - docs/rfcs/001-phase-registry.md
  - docs/rfcs/README.md
autonomous: true
gap_closure: true
requirements: []
tags: [docs, rfc, upstream, gap-closure, plugin-hooks]
closes_uat_gaps:
  - test: 6
    truth: "RFC 001 documents all three optional HarnessPlugin hooks (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`) with empty defaults"
    severity: major

must_haves:
  truths:
    - "`docs/rfcs/001-phase-registry.md` Section 4 specifies all three optional HarnessPlugin hooks: `contribute_phases()`, `contribute_phase_roles()`, `contribute_review_routers()` — each with its signature, its empty-collection default, its additive-only contract, and a plugin-use code example."
    - "The RFC title (H1) and the Section 1 Summary both name all three hooks (not just `contribute_phases`)."
    - "The Worked Example section demonstrates that `software-dev.toml` continues to spawn unchanged with all three hooks defaulting to empty — no template edit required for any of them."
    - "The `## Index` table in `docs/rfcs/README.md` reflects the expanded RFC title so a reader scanning the index sees all three hooks named."
    - "The additive-only compatibility guarantees in Section 4.7 cover all three hooks explicitly — none of them require existing plugins to implement new abstract methods."
    - "RFC frontmatter `title:` field is updated to match the new H1 so machine-readable metadata and human-readable title stay in sync."
  artifacts:
    - path: "docs/rfcs/001-phase-registry.md"
      provides: "Expanded RFC covering contribute_phases + contribute_phase_roles + contribute_review_routers (three hooks), plus PhaseRegistry + SprintState + InteractionGate; worked software-dev example shows all three hooks default to empty; additive-only contract explicit for each."
      contains: "contribute_phase_roles"
      min_lines: 750
    - path: "docs/rfcs/README.md"
      provides: "Index table row for RFC 001 with the expanded title (three hooks named)"
      contains: "contribute_review_routers"
  key_links:
    - from: "docs/rfcs/001-phase-registry.md §4.3"
      to: "`HarnessPlugin.contribute_phases() -> list[Phase]` (empty default)"
      via: "hook signature + default + additive contract + plugin example"
      pattern: "def contribute_phases"
    - from: "docs/rfcs/001-phase-registry.md §4.3a (new)"
      to: "`HarnessPlugin.contribute_phase_roles() -> dict[Phase, list[AgentRole]]` (empty default)"
      via: "hook signature + default + additive contract + plugin example"
      pattern: "def contribute_phase_roles"
    - from: "docs/rfcs/001-phase-registry.md §4.3b (new)"
      to: "`HarnessPlugin.contribute_review_routers() -> list[ReviewRouter]` (empty default)"
      via: "hook signature + default + additive contract + plugin example"
      pattern: "def contribute_review_routers"
    - from: "docs/rfcs/001-phase-registry.md §4.8 Worked Example"
      to: "software-dev.toml unchanged"
      via: "all three hooks default to empty; PhaseRegistry + role-map + router-list all empty; fallback to DEFAULT_PHASES / TOML-declared role list / existing review dispatch"
      pattern: "software-dev\\.toml"
---

<objective>
Expand `docs/rfcs/001-phase-registry.md` so it documents all three optional `HarnessPlugin` hooks named in ROADMAP Phase 0 success criterion #4 — `contribute_phases`, `contribute_phase_roles`, `contribute_review_routers` — each with its signature, empty default, additive-only contract, and a plugin-use example. Today the RFC only specifies `contribute_phases`; the other two hooks were deferred by Plan 05 as "later hook proposals" (see 00-05-SUMMARY.md). The Phase 0 acceptance criterion requires all three.

Purpose: Closes Gap 2 from the Phase 0 UAT (test 6, severity major) and satisfies ROADMAP Phase 0 success criterion #4 in full ("three optional `HarnessPlugin` hooks (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`) with empty defaults, the `PhaseRegistry` class shape, additive-only contract guarantees, and a worked example showing `software-dev.toml` continues to work unchanged"). Keeps the upstream RFC PR scope aligned with the phase's declared acceptance bar so the human owner can submit a complete proposal rather than a partial one.

Scope boundary: This is a DOCS-ONLY plan. Zero Python code changes. Four markdown edits:
1. RFC H1 title line — extend to name all three hooks.
2. RFC Section 1 Summary — extend the hook list from 1 → 3.
3. RFC Section 4 Reference-Level API — add §4.3a `contribute_phase_roles` and §4.3b `contribute_review_routers` subsections matching the existing §4.3 shape.
4. RFC Section 4.7 Compatibility Guarantees — explicitly cover all three hooks.
5. RFC Section 4.8 Worked Example — extend the software-dev trace to show all three hooks default to empty.
6. RFC Section 8 Unresolved Questions — prune/update entries that deferred these two hooks (Q5 currently asks "How should future upstream work define optional phase-role mapping" — now answered by §4.3a).
7. RFC frontmatter `title:` — sync with the new H1.
8. `docs/rfcs/README.md` index table — update the RFC 001 title cell.

The Phase 1 implementation plan will later introduce the actual Python hooks. This plan's job is purely to make the RFC match the phase's acceptance criterion.

Output:
- Modified `docs/rfcs/001-phase-registry.md` — expanded RFC covering all three hooks.
- Modified `docs/rfcs/README.md` — updated index row.
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
@.planning/phases/00-foundation-upstream-rfc/00-UAT.md
@.planning/phases/00-foundation-upstream-rfc/00-RESEARCH.md
@.planning/phases/00-foundation-upstream-rfc/00-05-upstream-rfc-PLAN.md
@.planning/phases/00-foundation-upstream-rfc/00-05-upstream-rfc-SUMMARY.md
@docs/rfcs/README.md
@docs/rfcs/001-phase-registry.md
@docs/transport-architecture.md
@clawteam/harness/phases.py
@clawteam/plugins/base.py
@clawteam/templates/software-dev.toml

<interfaces>
<!-- Current RFC shape to preserve + the plugin ABC surface the expanded RFC proposes to extend. -->

**Current RFC H1 title** (`docs/rfcs/001-phase-registry.md:10`):
```
# RFC 001: Plugin-Populated Phase Registry with Sprint State and Interactive Gates
```

**Current frontmatter `title:`** (line 3):
```
title: PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate
```

**Current RFC Section 1 Summary hook list** (lines 14-19):
```
This RFC proposes four additive primitives for the ClawTeam harness:

1. `PhaseRegistry`
2. `HarnessPlugin.contribute_phases()`
3. `InteractionGate`
4. `SprintState`
```

Note: "four primitives" = 1 class (`PhaseRegistry`) + 1 hook + 2 new types (`InteractionGate`, `SprintState`). After expansion the document describes 1 class + 3 hooks + 2 types; the enumeration style must adjust accordingly (either "six primitives" or a flat bullet list with three hooks grouped together).

**Current Section 4.3 shape** (lines 302-335 of the current RFC — the model to replicate for §4.3a and §4.3b):
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
```

The expanded subsections §4.3a and §4.3b must mirror this shape exactly: hook signature in a python fence, numbered Requirements list, "empty default matters because …" paragraph, updated ABC-relation ASCII box diagram, closing sentence. Preserves the tone of the existing document — neutral technical prose, numbered requirements, ASCII boxes.

**Current Section 4.7 Compatibility Guarantees** (lines 479-489):
```
### 4.7. Compatibility Guarantees

The proposal is additive-only under the following guarantees:

1. No existing template file must change.
2. No existing plugin must implement a new abstract method.
3. No existing phase name must be renamed.
4. Existing `Phase = str` remains valid.
5. Existing default phase execution remains the fallback when the registry is
   empty.
```

Must be extended so the guarantees explicitly cover phase-role contributions and review-router contributions, not just phase contributions.

**Current Section 4.8 Worked Example** (lines 491-534):
The before/after trace currently only mentions `PhaseRegistry` being empty. Must be extended to state that the phase-role map and the review-router list are ALSO empty for software-dev, and behavior falls back to the template's TOML-declared role list / existing review dispatch respectively.

**Current Section 8 Unresolved Questions** (lines 616-635):
- Q5 currently asks: "How should future upstream work define optional phase-role mapping without overloading this initial RFC?" — this is now answered by the new §4.3a. Rewrite Q5 to a different unresolved question OR delete Q5 and renumber Q6 → Q5.
- A new Q worth adding: "Should review-router precedence be deterministic by plugin load order or by an explicit priority hint?" — opens the conversation for Phase 4 without locking it in Phase 1.

**Existing plugin ABC** (`clawteam/plugins/base.py` — already referenced in the RFC):
```python
class HarnessPlugin(ABC):
    """Plugin contract: contribute gates/prompts to the harness lifecycle."""
    def contribute_gates(self, phase: Phase) -> list[PhaseGate]: ...
    def contribute_prompts(self, role: AgentRole) -> str | None: ...
```

The expanded RFC adds three optional methods, all with non-abstract default implementations returning empty collections. Method signatures (per ROADMAP Phase 1 success criterion 1):

```python
def contribute_phases(self) -> list[Phase]:
    return []

def contribute_phase_roles(self) -> dict[Phase, list[AgentRole]]:
    return {}

def contribute_review_routers(self) -> list[ReviewRouter]:
    return []
```

Where `ReviewRouter` is a NEW type introduced by the RFC but not the focus of this plan — the RFC only needs to forward-declare its shape as "a routing rule that consumes sprint state and returns a list of agent roles to participate in a phase's review, keyed by file patterns in the diff" (matches ROADMAP Phase 4 success criterion 3). The concrete `ReviewRouter` interface will land in a future Phase 4 RFC; Phase 1's RFC only specifies the hook point.

`AgentRole` is already an open string type in the codebase (`clawteam/harness/roles.py` if it exists, otherwise referenced throughout plugins/base.py). Use `AgentRole` unqualified in the RFC; the reader's mental model is `AgentRole = str`.

**Current Index row** (`docs/rfcs/README.md:27`):
```
| [001](001-phase-registry.md) | PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate | Draft | Phase 1 |
```
After edit, the title cell must name all three hooks.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Expand RFC 001 to cover all three HarnessPlugin hooks</name>
  <files>docs/rfcs/001-phase-registry.md</files>
  <action>
    Edit `docs/rfcs/001-phase-registry.md` in seven surgical places. Preserve all existing content that is NOT called out for change — this is an expand, not a rewrite.

    Use the Edit tool for each change (read the file first to confirm current line content, then Edit). Preserve the file's existing tone: numbered sections, neutral technical prose, ASCII box diagrams, python code fences for API sketches.

    ### Edit 1 — Frontmatter `title:` field (currently line 3)

    FROM:
    ```yaml
    title: PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate
    ```
    TO:
    ```yaml
    title: PhaseRegistry + three HarnessPlugin hooks (contribute_phases / contribute_phase_roles / contribute_review_routers) + SprintState + InteractionGate
    ```

    ### Edit 2 — H1 title line (currently line 10)

    FROM:
    ```
    # RFC 001: Plugin-Populated Phase Registry with Sprint State and Interactive Gates
    ```
    TO:
    ```
    # RFC 001: Plugin-Populated Phase Registry, Three Optional HarnessPlugin Hooks, Sprint State, and Interactive Gates
    ```

    Rationale for the rename: mirrors the expanded Section 1 Summary so a reader opening the file sees the three-hook surface in the first paragraph.

    ### Edit 3 — Section 1 Summary hook list (currently lines 14-19)

    FROM:
    ```
    This RFC proposes four additive primitives for the ClawTeam harness:

    1. `PhaseRegistry`
    2. `HarnessPlugin.contribute_phases()`
    3. `InteractionGate`
    4. `SprintState`
    ```

    TO:
    ```
    This RFC proposes six additive primitives for the ClawTeam harness, grouped
    as one registry, three optional plugin hooks, and two new runtime types:

    1. `PhaseRegistry` — in-memory registry populated at plugin load.
    2. `HarnessPlugin.contribute_phases()` — optional hook, empty list default.
    3. `HarnessPlugin.contribute_phase_roles()` — optional hook, empty dict default.
    4. `HarnessPlugin.contribute_review_routers()` — optional hook, empty list default.
    5. `SprintState` — pydantic v2 model for sprint lifecycle persistence.
    6. `InteractionGate` — `PhaseGate` subclass that blocks on unanswered questions.

    Each of the three plugin hooks defaults to an empty collection, so existing
    plugins and existing templates continue to work without any edits. The three
    hooks are proposed together because they share one design invariant: plugin
    authors should be able to contribute phase vocabulary, phase-to-role
    assignments, and review routing rules through the same additive extension
    surface, not through three different mechanisms introduced in three
    different RFCs.
    ```

    ### Edit 4 — Also update the compatibility-contract list immediately below the summary (currently lines 64-71)

    The existing list reads:
    ```
    The additive compatibility contract is:

    1. `Phase` remains `str`.
    2. `DEFAULT_PHASES` remains the fallback for templates that do not opt in.
    3. `HarnessPlugin.contribute_phases()` defaults to an empty list.
    4. `InteractionGate` is opt-in and only runs when a phase or sprint uses it.
    5. `SprintState` is new persistence surface; existing harness state files stay
       valid.
    ```

    Extend to:
    ```
    The additive compatibility contract is:

    1. `Phase` remains `str`.
    2. `AgentRole` remains `str`.
    3. `DEFAULT_PHASES` remains the fallback for templates that do not opt in.
    4. `HarnessPlugin.contribute_phases()` defaults to an empty list.
    5. `HarnessPlugin.contribute_phase_roles()` defaults to an empty dict.
    6. `HarnessPlugin.contribute_review_routers()` defaults to an empty list.
    7. `InteractionGate` is opt-in and only runs when a phase or sprint uses it.
    8. `SprintState` is new persistence surface; existing harness state files stay
       valid.
    ```

    ### Edit 5 — Add two new subsections §4.3a and §4.3b after the existing §4.3

    The existing §4.3 ends at the line "No other plugin methods need semantic changes to support this RFC." — REPLACE that closing sentence with an updated closing that points forward to §4.3a and §4.3b, then insert the two new subsections before §4.4.

    Replace the current §4.3 closing sentence:
    ```
    No other plugin methods need semantic changes to support this RFC.
    ```

    With:
    ```
    Two sibling hooks follow below. They share the same additive shape: empty
    collection default, no abstract-method requirement, no side effects beyond
    populating a plugin-scoped registry at load time.
    ```

    Then, IMMEDIATELY after the current §4.3 block (and before the line `### 4.4. \`SprintState\``), insert two new subsections:

    ````markdown
    ### 4.3a. `HarnessPlugin.contribute_phase_roles()`

    `HarnessPlugin` gains a second new optional hook that maps each
    plugin-contributed phase to the list of agent roles expected to participate
    in that phase:

    ```python
    def contribute_phase_roles(self) -> dict[Phase, list[AgentRole]]:
        return {}
    ```

    Where `AgentRole` is the existing open-string role identifier (`AgentRole =
    str`), already used by `HarnessPlugin.contribute_prompts(role: AgentRole)`.

    Requirements:

    1. The default implementation returns an empty dict.
    2. Existing plugins are not required to implement the hook.
    3. Keys are phase names that the same plugin must also declare via
       `contribute_phases()` — phase-role entries for phases the plugin does not
       own are rejected at registration time with `ValueError`.
    4. Values are ordered role lists. The order is the template's default
       participant order for that phase; the harness or a later review router
       may narrow or expand the set per sprint context.
    5. Two plugins mapping the same phase name is already blocked by
       `PhaseRegistry`'s duplicate-name rule from §4.2, so phase-role conflicts
       cannot arise between plugins.

    The empty default matters because templates that declare their role list in
    TOML continue to work unchanged. The hook only activates when a plugin owns
    phases for which the TOML has no role list to consult.

    The intended relation to the current plugin base class is:

    ```text
    ┌────────────────────────────────────┐
    │ HarnessPlugin                      │
    ├────────────────────────────────────┤
    │ on_register(ctx)                   │
    │ on_unregister()                    │
    │ contribute_gates()                 │
    │ contribute_prompts()               │
    │ contribute_phases()           NEW  │
    │ contribute_phase_roles()      NEW  │
    └────────────────────────────────────┘
    ```

    Plugin-use example (gstack — illustrative, not normative for Phase 1):

    ```python
    class GstackSprintPlugin(HarnessPlugin):
        def contribute_phases(self) -> list[Phase]:
            return ["think", "plan", "build", "review", "test", "ship", "reflect"]

        def contribute_phase_roles(self) -> dict[Phase, list[AgentRole]]:
            return {
                "think":   ["pm", "ceo"],
                "plan":    ["pm", "ceo", "eng-mgr"],
                "build":   ["engineer", "designer"],
                "review":  ["reviewer", "designer", "security", "dx-lead"],
                "test":    ["qa", "engineer"],
                "ship":    ["shipper", "reviewer"],
                "reflect": ["eng-mgr"],
            }
    ```

    Empty-dict default behavior: when the hook returns `{}`, the harness does
    not alter the template's TOML-declared role list for any phase.

    ### 4.3b. `HarnessPlugin.contribute_review_routers()`

    `HarnessPlugin` gains a third new optional hook that contributes
    review-routing rules consulted at the Review phase to pick which agents
    participate given the diff under review:

    ```python
    def contribute_review_routers(self) -> list[ReviewRouter]:
        return []
    ```

    Where `ReviewRouter` is a new runtime type with the forward-declared shape:

    ```python
    from typing import Protocol


    class ReviewRouter(Protocol):
        """Rule that picks additional reviewer roles based on the diff.

        The full interface is specified by a future Phase 4 RFC. For Phase 1 the
        only observable contract is: routers are consulted in plugin load order
        during the Review phase and return an ordered list of `AgentRole`
        entries to append to the Review-phase participant set.
        """

        def match(self, diff_paths: list[str], state: SprintState) -> list[AgentRole]:
            ...
    ```

    Requirements:

    1. The default implementation returns an empty list.
    2. Existing plugins are not required to implement the hook.
    3. Returned routers are evaluated in plugin load order; the harness
       concatenates their `match()` results, deduplicates, and appends the
       result to the Review-phase participant list established by the template
       or by `contribute_phase_roles()`.
    4. A router that raises during `match()` is skipped with a logged warning;
       router exceptions do not block the Review phase.
    5. The full `ReviewRouter` interface (rule-file format, SHA-pinning
       semantics, multi-signal aggregation) is deferred to a future Phase 4 RFC;
       Phase 1 only locks the hook point.

    The empty default matters because no existing template currently uses
    review routing. Templates that want to ship review rules can migrate to
    this extension surface without breaking other templates.

    The intended relation to the current plugin base class is:

    ```text
    ┌────────────────────────────────────────┐
    │ HarnessPlugin                          │
    ├────────────────────────────────────────┤
    │ on_register(ctx)                       │
    │ on_unregister()                        │
    │ contribute_gates()                     │
    │ contribute_prompts()                   │
    │ contribute_phases()               NEW  │
    │ contribute_phase_roles()          NEW  │
    │ contribute_review_routers()       NEW  │
    └────────────────────────────────────────┘
    ```

    Plugin-use example (gstack — illustrative, not normative for Phase 1):

    ```python
    class UiChangeRouter:
        """Adds designer to Review when the diff touches UI paths."""

        def match(self, diff_paths, state):
            ui_hit = any(p.startswith("src/components/") and p.endswith(".tsx")
                         for p in diff_paths)
            return ["designer"] if ui_hit else []


    class SecurityRouter:
        """Adds security to Review when the diff touches auth or crypto."""

        def match(self, diff_paths, state):
            risky = any(p.startswith("src/auth/") or "/crypto/" in p
                        for p in diff_paths)
            return ["security"] if risky else []


    class GstackSprintPlugin(HarnessPlugin):
        def contribute_review_routers(self) -> list[ReviewRouter]:
            return [UiChangeRouter(), SecurityRouter()]
    ```

    Empty-list default behavior: when the hook returns `[]`, the Review phase's
    participant list is exactly the one produced by the template or by
    `contribute_phase_roles()`, unchanged from today's behavior.
    ````

    Important style rules for Edit 5:
    - The two new subsections use `### 4.3a.` and `### 4.3b.` numbering (not `### 4.4.` and `### 4.5.` — we must preserve existing §4.4 `SprintState` and §4.5 `InteractionGate` heading numbers so the rest of the document's cross-references and the verification grep patterns don't break).
    - Mirror §4.3's exact shape: python signature fence → numbered Requirements list → "empty default matters because …" paragraph → ASCII box of the plugin ABC → plugin-use example → closing "empty default behavior" one-liner.
    - Use the exact ASCII box-drawing characters that appear in §4.3 (`┌ ├ │ ─ ┤ └ ┘`) — same as elsewhere in the existing RFC. Width can differ per row if the longest cell name differs (the existing document has variable-width boxes; it's fine).
    - No marketing prose. No exclamation points. No emoji.
    - Two blank lines between the end of §4.3 and the start of §4.3a; two blank lines between §4.3a and §4.3b; two blank lines between §4.3b and the existing §4.4.

    ### Edit 6 — Extend Section 4.7 Compatibility Guarantees to cover all three hooks

    REPLACE the current §4.7 body (lines 479-489) with an expanded version:

    FROM:
    ```
    ### 4.7. Compatibility Guarantees

    The proposal is additive-only under the following guarantees:

    1. No existing template file must change.
    2. No existing plugin must implement a new abstract method.
    3. No existing phase name must be renamed.
    4. Existing `Phase = str` remains valid.
    5. Existing default phase execution remains the fallback when the registry is
       empty.
    ```

    TO:
    ```
    ### 4.7. Compatibility Guarantees

    The proposal is additive-only under the following guarantees:

    1. No existing template file must change.
    2. No existing plugin must implement a new abstract method. All three new
       hooks (`contribute_phases`, `contribute_phase_roles`,
       `contribute_review_routers`) ship with empty-collection defaults on the
       `HarnessPlugin` base class.
    3. No existing phase name must be renamed, and no existing role name must
       be renamed.
    4. Existing `Phase = str` and `AgentRole = str` remain valid; the new hooks
       reuse these open-string types without introducing enums.
    5. Existing default phase execution remains the fallback when the
       `PhaseRegistry` is empty.
    6. Existing template role assignments (declared in TOML) remain the
       fallback when `contribute_phase_roles()` returns an empty dict.
    7. Existing Review-phase participant selection remains unchanged when
       `contribute_review_routers()` returns an empty list — routers are
       consulted only to APPEND participants, never to remove them.
    8. The three hooks are independent: a plugin may implement one, two, or
       three of them. Implementing one does not require implementing the others.
    ```

    ### Edit 7 — Extend Section 4.8 Worked Example to mention all three hooks

    The current §4.8 "After (with RFC 001 landed)" trace mentions only the empty `PhaseRegistry`. Extend it so every reader can see that all three hooks default to empty for software-dev.

    In the existing "After" code block (around lines 515-521, the trace that currently reads):

    ```text
    software-dev.toml
      └─ no plugin phase contribution
         └─ PhaseRegistry is empty for this template
            └─ harness still uses DEFAULT_PHASES
    ```

    REPLACE with:

    ```text
    software-dev.toml
      ├─ no plugin phase contribution         → PhaseRegistry is empty
      ├─ no plugin phase-role contribution    → contribute_phase_roles() returns {}
      ├─ no plugin review-router contribution → contribute_review_routers() returns []
      └─ harness fallbacks:
           - phases         → DEFAULT_PHASES
           - role list      → template TOML (unchanged)
           - Review routers → none (Review participants set exactly by template)
    ```

    Then, immediately after the existing "Observable behavior stays the same:" enumerated list (current 5-item list ending at "does not incur `InteractionGate` unless a future plugin opts into it."), APPEND three more items so the list covers the two new hooks:

    Current list (preserve items 1-5 verbatim):
    ```
    1. The template still loads through the current template machinery.
    2. It still spawns the same agents.
    3. It still advances through the default phase sequence.
    4. It does not require `SprintState`.
    5. It does not incur `InteractionGate` unless a future plugin opts into it.
    ```

    Extend to 8 items:
    ```
    1. The template still loads through the current template machinery.
    2. It still spawns the same agents.
    3. It still advances through the default phase sequence.
    4. It does not require `SprintState`.
    5. It does not incur `InteractionGate` unless a future plugin opts into it.
    6. It uses its TOML-declared role assignments unchanged;
       `contribute_phase_roles()` returns `{}` and contributes nothing.
    7. Its Review phase uses its existing participant list unchanged;
       `contribute_review_routers()` returns `[]` and contributes no additional
       reviewers.
    8. No plugin owned by software-dev implements any of the three new hooks,
       so the three registration calls are no-ops at plugin load.
    ```

    ### Edit 8 — Update Section 8 Unresolved Questions

    Question 5 currently reads:
    ```
    5. How should future upstream work define optional phase-role mapping without
       overloading this initial RFC?
    ```

    This is now answered by §4.3a. REPLACE Q5 with a new unresolved question that opens the conversation for review-router precedence (a genuine open question not resolved by the three-hook expansion):

    REPLACE:
    ```
    5. How should future upstream work define optional phase-role mapping without
       overloading this initial RFC?
    ```

    WITH:
    ```
    5. Should `contribute_review_routers()` precedence be deterministic purely
       by plugin load order, or should routers carry an explicit `priority:
       int` hint so a later-loaded plugin can insert a router earlier in the
       evaluation chain? Recommendation: start with load-order (matches
       `PhaseRegistry`'s ordering rule from §4.2); add priority hints in a
       future Phase 4 RFC only if a concrete conflict emerges.
    ```

    Leave Q1, Q2, Q3, Q4, Q6 unchanged. The list remains 6 items.

    ### Verification after edits

    After all 8 edits, verify the file structure is still intact:

    ```bash
    cd /home/jac/repos/ClawTeam-gstack
    # All 8 section headings still present
    for section in "1\. Summary" "2\. Motivation" "3\. Guide-Level" "4\. Reference-Level" "5\. Drawbacks" "6\. Rationale and Alternatives" "7\. Prior Art" "8\. Unresolved Questions"; do
      grep -qE "^## $section" docs/rfcs/001-phase-registry.md || echo "MISSING SECTION: $section"
    done
    # All three hooks named in Section 4
    grep -qE "^### 4\.3\. " docs/rfcs/001-phase-registry.md && echo "§4.3 OK"
    grep -qE "^### 4\.3a\. " docs/rfcs/001-phase-registry.md && echo "§4.3a OK"
    grep -qE "^### 4\.3b\. " docs/rfcs/001-phase-registry.md && echo "§4.3b OK"
    # All three hook names appear as method signatures
    grep -c "def contribute_phases" docs/rfcs/001-phase-registry.md  # expect ≥3 (signature, plugin example, ABC references)
    grep -c "def contribute_phase_roles" docs/rfcs/001-phase-registry.md  # expect ≥2
    grep -c "def contribute_review_routers" docs/rfcs/001-phase-registry.md  # expect ≥2
    # H1 and frontmatter title name all three hooks
    grep -qE "^# RFC 001:" docs/rfcs/001-phase-registry.md && grep -q "contribute_phase_roles" docs/rfcs/001-phase-registry.md && grep -q "contribute_review_routers" docs/rfcs/001-phase-registry.md
    # Worked example still present and now mentions the three hooks
    grep -q "software-dev" docs/rfcs/001-phase-registry.md
    # Length sanity: the existing RFC is ~640 lines; adding two subsections
    # should push the total to ≥750 lines.
    wc -l docs/rfcs/001-phase-registry.md
    ```

    Rules:
    - Preserve every non-targeted paragraph and ASCII diagram verbatim. Scope of this plan is strictly additive.
    - Do NOT renumber sections other than the explicit §4.3a / §4.3b additions — §4.4 through §4.8 retain their current numbers.
    - Do NOT add new runtime requirements beyond what Phase 1 already needs. `ReviewRouter` is forward-declared as a Protocol, not fully specified — its concrete contract is a Phase 4 RFC concern.
    - Do NOT delete or paraphrase the existing §4.3. The original text must remain as the anchor that §4.3a and §4.3b mirror.
    - Keep the neutral technical prose tone. No "powerful", "elegant", "best-practice" adjectives.
    - Use the project's existing code-fence language tags: ` ```python ` for Python, ` ```text ` for ASCII trees, ` ```yaml ` for frontmatter, ` ```toml ` for TOML.

    Commit:
    ```bash
    git add docs/rfcs/001-phase-registry.md
    git commit -m "docs(00-07): expand RFC 001 to document contribute_phase_roles and contribute_review_routers hooks"
    ```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && grep -qE "^# RFC 001:" docs/rfcs/001-phase-registry.md && grep -qE "^### 4\.3\. " docs/rfcs/001-phase-registry.md && grep -qE "^### 4\.3a\. " docs/rfcs/001-phase-registry.md && grep -qE "^### 4\.3b\. " docs/rfcs/001-phase-registry.md && grep -q "def contribute_phase_roles" docs/rfcs/001-phase-registry.md && grep -q "def contribute_review_routers" docs/rfcs/001-phase-registry.md && grep -q "contribute_phase_roles" docs/rfcs/001-phase-registry.md && grep -q "contribute_review_routers" docs/rfcs/001-phase-registry.md && grep -qE "^## 1\. Summary" docs/rfcs/001-phase-registry.md && grep -qE "^## 4\. Reference-Level API" docs/rfcs/001-phase-registry.md && grep -qE "^## 8\. Unresolved Questions" docs/rfcs/001-phase-registry.md && grep -q "software-dev" docs/rfcs/001-phase-registry.md && grep -q "empty dict" docs/rfcs/001-phase-registry.md && grep -q "empty list" docs/rfcs/001-phase-registry.md && wc -l docs/rfcs/001-phase-registry.md | awk '{ if ($1 >= 750) print "OK len=" $1; else { print "FAIL len=" $1 " (expected >=750)"; exit 1 } }'</automated>
  </verify>
  <done>
    `docs/rfcs/001-phase-registry.md` has: (1) H1 + frontmatter title naming all three hooks; (2) Section 1 Summary enumerating six primitives with the three hooks grouped; (3) §4.3 unchanged, §4.3a and §4.3b added with signature + empty default + requirements list + ABC ASCII box + plugin-use example; (4) §4.7 Compatibility Guarantees expanded to 8 items covering each hook; (5) §4.8 Worked Example trace showing all three hooks default to empty for software-dev.toml, with the observable-behavior list extended from 5 to 8 items; (6) §8 Unresolved Questions Q5 rewritten to a genuine open question about review-router precedence. Length ≥750 lines. All 8 numbered sections intact. One atomic commit created.
  </done>
</task>

<task type="auto">
  <name>Task 2: Update docs/rfcs/README.md index to reflect the expanded RFC title</name>
  <files>docs/rfcs/README.md</files>
  <action>
    Edit `docs/rfcs/README.md` line 27 — the RFC 001 index row. Only the title cell changes; the link, status, and target-phase cells stay unchanged.

    FROM:
    ```
    | [001](001-phase-registry.md) | PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate | Draft | Phase 1 |
    ```

    TO:
    ```
    | [001](001-phase-registry.md) | PhaseRegistry + three HarnessPlugin hooks (contribute_phases / contribute_phase_roles / contribute_review_routers) + SprintState + InteractionGate | Draft | Phase 1 |
    ```

    Rules:
    - Only this row changes. The preamble (lines 1-21) stays identical — it talks about the RFC process in general, not about any specific hook list, so it remains accurate.
    - Link target (`001-phase-registry.md`) unchanged.
    - Status cell stays `Draft` — the status is about upstream submission, not about scope. The upstream PR is still unmerged, so the status is still Draft. (The human owner updates this to `Accepted` after maintainer ack per the process description on lines 9-18.)
    - Target Phase cell stays `Phase 1` — correct.
    - No other lines in README.md change.

    Commit:
    ```bash
    git add docs/rfcs/README.md
    git commit -m "docs(00-07): sync RFC index title with expanded RFC 001 (three hooks)"
    ```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && grep -q "contribute_phase_roles" docs/rfcs/README.md && grep -q "contribute_review_routers" docs/rfcs/README.md && grep -qE "^\| \[001\]\(001-phase-registry\.md\)" docs/rfcs/README.md && grep -qE "\| Draft \| Phase 1 \|" docs/rfcs/README.md && echo "README index OK"</automated>
  </verify>
  <done>
    `docs/rfcs/README.md` line 27 names all three hooks in the RFC 001 title cell. Preamble, process description, and the Draft/Phase 1 columns are unchanged. Commit created.
  </done>
</task>

</tasks>

<threat_model>
N/A — documentation only. No code changes in this plan; no trust boundaries crossed by Markdown edits. The RFC proposes security-adjacent primitives (`InteractionGate`, `contribute_review_routers`), but their threat analysis belongs to the Phase 1 / Phase 4 implementation plans that land them. This plan only aligns the RFC text with the phase's declared acceptance criterion.
</threat_model>

<verification>
Gap-closure verification (maps back to UAT test 6 directly):

```bash
cd /home/jac/repos/ClawTeam-gstack

# The UAT evidence command that failed before the fix — must now show ≥2 hits each
grep -c "contribute_phase_roles" docs/rfcs/001-phase-registry.md      # expect ≥2
grep -c "contribute_review_routers" docs/rfcs/001-phase-registry.md   # expect ≥2
grep -c "contribute_phases" docs/rfcs/001-phase-registry.md           # expect ≥3 (still named, plus new ABC-box references)

# All 8 numbered sections still present
for section in "1\. Summary" "2\. Motivation" "3\. Guide-Level" "4\. Reference-Level" "5\. Drawbacks" "6\. Rationale" "7\. Prior Art" "8\. Unresolved"; do
  grep -qE "^## $section" docs/rfcs/001-phase-registry.md || echo "MISSING: $section"
done

# §4.3, §4.3a, §4.3b all present in §4
grep -qE "^### 4\.3\. " docs/rfcs/001-phase-registry.md       && echo "§4.3 OK"
grep -qE "^### 4\.3a\. " docs/rfcs/001-phase-registry.md      && echo "§4.3a OK"
grep -qE "^### 4\.3b\. " docs/rfcs/001-phase-registry.md      && echo "§4.3b OK"

# Each of the three hooks has a method signature in a python fence
grep -qE "def contribute_phases\(self\) -> list\[Phase\]:" docs/rfcs/001-phase-registry.md
grep -qE "def contribute_phase_roles\(self\) -> dict\[Phase, list\[AgentRole\]\]:" docs/rfcs/001-phase-registry.md
grep -qE "def contribute_review_routers\(self\) -> list\[ReviewRouter\]:" docs/rfcs/001-phase-registry.md

# Worked example preserves the software-dev anchor
grep -q "software-dev" docs/rfcs/001-phase-registry.md

# Compatibility guarantees cover all three hooks explicitly
grep -q "contribute_phase_roles.*empty dict" docs/rfcs/001-phase-registry.md
grep -q "contribute_review_routers.*empty list" docs/rfcs/001-phase-registry.md

# Index table row reflects the expanded title
grep -q "contribute_phase_roles" docs/rfcs/README.md
grep -q "contribute_review_routers" docs/rfcs/README.md

# Length sanity
wc -l docs/rfcs/001-phase-registry.md
# Expect: ≥750 lines (was 637 per prior SUMMARY; +two subsections + expanded §4.7/§4.8 adds ~130-200 lines)

# BC regression — no code changed, nothing should have broken
.venv-sys/bin/python -m pytest tests/ -q --tb=no -x 2>&1 | tail -5
```

Expected:
- `contribute_phase_roles` grep → ≥2 hits (UAT evidence was 0 hits; gap closed).
- `contribute_review_routers` grep → ≥2 hits (UAT evidence was 0 hits; gap closed).
- All 8 numbered sections present.
- §4.3, §4.3a, §4.3b all present.
- Three method signatures visible in python fences.
- Worked example still anchors on software-dev.toml.
- README index row names all three hooks.
- File length ≥750 lines.
- All existing tests pass (this plan changes no Python).

UAT re-run expectation:
- Phase 0 UAT test 6 moves from `result: issue` to `result: pass`. Evidence string becomes: `grep contribute_(phase_roles|review_routers) docs/rfcs/001-phase-registry.md → ≥2 matches each; all three hooks specified with signature + empty default + additive contract + plugin example; software-dev.toml worked example covers all three hooks defaulting to empty.`
</verification>

<success_criteria>
1. `docs/rfcs/001-phase-registry.md` names all three hooks in its H1 title, in its frontmatter `title:` field, and in its Section 1 Summary bullet list.
2. Section 4 Reference-Level API contains §4.3 (`contribute_phases`), §4.3a (`contribute_phase_roles`), and §4.3b (`contribute_review_routers`) — each with a python method signature, a numbered Requirements list, an "empty default matters because …" paragraph, an updated HarnessPlugin ABC ASCII box, and a plugin-use example.
3. Section 4.7 Compatibility Guarantees enumerates 8 items (was 5) covering `contribute_phase_roles() → {}` and `contribute_review_routers() → []` explicitly.
4. Section 4.8 Worked Example's software-dev.toml trace shows all three hooks defaulting to empty, and the observable-behavior list extends from 5 to 8 items.
5. Section 8 Unresolved Questions Q5 is rewritten away from the now-answered "phase-role mapping" question and opens a new question about review-router precedence. The list remains 6 items.
6. Sections 1, 2, 3, 4, 5, 6, 7, 8 are all still present with their original numbers. §4.4 (`SprintState`), §4.5 (`InteractionGate`), §4.6 (Integration Contract), §4.7 (Compatibility Guarantees — now expanded), §4.8 (Worked Example — now expanded) retain their current section numbers.
7. `docs/rfcs/README.md` index table row for RFC 001 names all three hooks in its title cell; the link, Draft status, and Phase 1 target-phase cells are unchanged. The README preamble stays verbatim.
8. Automated verification grep commands all exit 0 (the UAT evidence command `grep contribute_(phase_roles|review_routers) docs/rfcs/001-phase-registry.md` now yields ≥2 matches each, vs 0 before).
9. File length: `docs/rfcs/001-phase-registry.md` ≥750 lines (was 637).
10. No Python code changes — BC regression: `.venv-sys/bin/python -m pytest tests/ -q` continues to pass unchanged.
11. Two atomic commits exist: one for the RFC expansion, one for the index sync, each scoped to `00-07` in its message prefix.
</success_criteria>

<output>
After completion, create `.planning/phases/00-foundation-upstream-rfc/00-07-rfc-expand-hooks-SUMMARY.md` following `@$HOME/.claude/get-shit-done/templates/summary.md`, documenting:
- Gap closed: Phase 0 UAT test 6 (severity major); ROADMAP Phase 0 success criterion #4 now fully satisfied (all three hooks named with empty defaults, additive-only contract, and a worked software-dev example showing unchanged behavior).
- What changed in the RFC: two new subsections (§4.3a `contribute_phase_roles`, §4.3b `contribute_review_routers`) mirroring the existing §4.3 shape; Section 1 Summary extended from 4 to 6 primitives; Section 4.7 Compatibility Guarantees extended from 5 to 8 items; Section 4.8 Worked Example extended to show all three hooks defaulting to empty for software-dev.toml; Section 8 Q5 rewritten to a genuine open question (review-router precedence) since the previous Q5 about "phase-role mapping" is now answered by §4.3a.
- What did NOT change: the RFC's tone, its numbered-section structure (still 8 sections), the existing §4.3 / §4.4 / §4.5 / §4.6 bodies, the Motivation and Drawbacks sections. This is a scope expansion aligned with the phase's declared acceptance bar, not a rewrite.
- `ReviewRouter` forward-declaration decision: typed as `Protocol` with a single `match()` method; the full interface (rule-file format, SHA-pinning semantics, multi-signal aggregation) is deferred to a future Phase 4 RFC. This matches Plan 05's original scope discipline — only Phase 1 primitives are specified normatively here.
- Out-of-band follow-up (still not this plan's responsibility): the human owner opens the upstream PR against HKUDS/ClawTeam with these two expanded files; obtains ≥1 maintainer acknowledgement before Phase 1 code lands per ROADMAP.md Phase 0 success criterion 4. The maintainer-ack status is tracked in ROADMAP, not in this plan's SUMMARY.
- Pattern established: gap-closure plans on documentation artifacts are surgical expansions matching the acceptance criterion verbatim, not rewrites. Future doc gaps should follow this add-subsection-mirroring-existing-shape pattern.
</output>
