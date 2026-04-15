# Architecture Research

**Domain:** Persistent-agent-team + parallel-sprint harness on top of ClawTeam
**Researched:** 2026-04-15
**Confidence:** HIGH (existing codebase read firsthand; external patterns verified against Context7-indexed docs and primary sources)

## Executive Orientation

ClawTeam's existing architecture is already 80% of the way to what this milestone needs. Three architectural facts shape every recommendation below:

1. **`Phase` and `AgentRole` are already open `str` types** (`clawteam/harness/phases.py` line 20, `clawteam/harness/roles.py` line 8) — **not enums**. `PhaseState.phases` is a configurable `list[str]`. There is no enum to extend. `PhaseRegistry` is therefore not a "new extension point to Phase"; it is a thin registry that **populates and validates** a plugin-provided list of phase names + per-phase gate bundles + per-phase role mapping. This is the single most important upstream-compatibility fact — it reduces the core patch to a registry class plus three `HarnessPlugin` hook additions.

2. **`HarnessContext` already gives plugins `bus`, `tasks`, `spawner`, `sessions`, `artifacts`, `config`** (`clawteam/harness/context.py`). The existing `HarnessPlugin.contribute_gates()` / `contribute_prompts()` hooks are **not** enough — they cover step 1's registry population, but cross-sprint concerns (AttentionQueue, team memory, smart review routing) need three additional hooks. The existing plugin base is the right shape; it just needs more faces.

3. **Per-team state is already file-locked, atomic-written, under `get_data_dir()`** (`clawteam/fileutil.py::file_locked`, `clawteam/team/models.py::get_data_dir`). Every new persistent component (AttentionQueue, TeamMemory, SprintState, active-sprint registry) reuses this primitive. No new storage abstraction; no DB; no embedded search index in v1.

The design below preserves those three facts rigorously so the ClawTeam-core delta stays PR-acceptable upstream.

## Standard Architecture

### System Overview (new components drawn, existing components labeled "EXISTING")

```
┌──────────────────────────────── CLI / MCP Entry ────────────────────────────────┐
│  clawteam team spawn gstack    clawteam sprint start   clawteam attend         │
│  clawteam sprint status        clawteam sprint show    clawteam team show      │
│                                                                                  │
│  [EXISTING] clawteam/cli/commands.py   [EXISTING] clawteam/mcp/server.py       │
└──────────────┬────────────────────────────────────────────┬────────────────────┘
               │                                            │
               ▼                                            ▼
┌──────────────────────────────── Sprint Coordinator ─────────────────────────────┐
│                                                                                  │
│   ┌─────────────────────┐    ┌─────────────────────┐   ┌───────────────────┐    │
│   │  SprintConductor    │    │   AttentionQueue    │   │  TeamMemoryStore  │    │
│   │  (NEW, per-team)    │◄──►│   (NEW, per-team)   │   │  (NEW, per-team)  │    │
│   │  — tracks N active  │    │  — priority-sorted  │   │  — layered:       │    │
│   │    SprintState      │    │  open questions     │   │   per-agent +     │    │
│   │  — dispatches agent │    │  across all sprints │   │   team-shared     │    │
│   │    work via queue   │    │  — file-backed      │   │  — grep + index   │    │
│   └──────────┬──────────┘    └──────────┬──────────┘   └─────────┬─────────┘    │
│              │                           │                        │              │
│              ▼                           ▼                        ▼              │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │           PhaseRegistry (NEW)  —  a list populator + validator          │   │
│   │  - collects HarnessPlugin.contribute_phases() -> ordered phase names    │   │
│   │  - collects HarnessPlugin.contribute_gates() -> {phase: [gates]}        │   │
│   │  - collects phase_roles mapping                                         │   │
│   │  - hands result to PhaseRunner via HarnessOrchestrator                  │   │
│   └───────────────────────────────────┬─────────────────────────────────────┘   │
└────────────────────────────────────────┼────────────────────────────────────────┘
                                         ▼
┌─────────────────────────── EXISTING Harness Orchestration ──────────────────────┐
│  HarnessOrchestrator  ─────►  PhaseRunner  ─────►  [PhaseGate, PhaseGate, ...]  │
│  (EXISTING)                   (EXISTING)           (NEW: InteractionGate        │
│                                                     + SmartReviewerGate joins   │
│                                                     existing Artifact/AllTasks/ │
│                                                     HumanApproval gates)         │
│                                                                                  │
│  PhaseState.phases = [think, plan, build, review, test, ship, reflect]          │
│  (populated by PhaseRegistry from GstackSprintPlugin.contribute_phases())       │
└─────────────────────────────────────┬───────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────── EXISTING Core Substrate ────────────────────────────┐
│                                                                                  │
│   [EXISTING EventBus]    [EXISTING FileTransport / P2PTransport]                │
│   [EXISTING TaskStore]   [EXISTING SpawnRegistry + Backends: tmux/subp/wsh]     │
│   [EXISTING WorkspaceManager (git worktrees)]   [EXISTING ArtifactStore]        │
│   [EXISTING TeamManager / Mailbox / Router]     [EXISTING file_locked() I/O]    │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────── GstackSprintPlugin (NEW) ───────────────────────────┐
│   Single cohesive plugin file: clawteam/plugins/gstack_sprint_plugin.py         │
│                                                                                  │
│   contribute_phases()   -> ["think","plan","build","review","test",             │
│                             "ship","reflect"]                                    │
│   contribute_gates()    -> {think: [Q], plan: [Q, Artifact(plan.md)], ...}      │
│   contribute_prompts()  -> per-phase, per-role methodology text                 │
│   contribute_skills()   -> /browse, /design-shotgun, /codex, /ship, etc.       │
│   contribute_review_routers() -> diff-analysis rules (UI→designer, etc.)       │
│   contribute_memory_schema()  -> per-role learning slots                        │
│                                                                                  │
│   on_register(ctx) ⇒ registers EventBus subscriber for SprintPhaseTransition,   │
│                      wires SmartReviewRouter into Review phase, binds           │
│                      InteractionGate to every phase that has questions          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (new components only)

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **PhaseRegistry** | Collect phase lists + gate dictionaries + role mappings from all loaded `HarnessPlugin`s; validate no collisions; produce a frozen ordering passed to `PhaseRunner` | Pure in-memory object constructed by `PluginManager` at `HarnessOrchestrator.__init__`. ~100 LOC. Mirrors how `clawteam/spawn/__init__.py` already maintains a backend registry. |
| **SprintState** | Persisted per-sprint state: sprint_id, team, goal, branch, current_phase, phase_history, artifacts, assigned_agents, open_question_ids. Pydantic v2 model, mirrors `PhaseState` but scoped per-sprint rather than per-harness | Pydantic BaseModel written to `~/.clawteam/teams/<team>/sprints/<sprint_id>/state.json` via `file_locked`. Use `model_dump_json(by_alias=True)` per existing convention. |
| **SprintConductor** | Per-team singleton owning the set of active `SprintState` instances; advances each sprint through phases; dispatches agent work through existing `TaskStore`; publishes `SprintPhaseTransition` events | One class per team, persisted as `sprints/index.json`. Dispatch uses the existing `TaskStore` — the "team-wide task queue" model from asyncio worker-pool research (see Pattern 2 below). No new process; this is a logical coordinator invoked by CLI commands and plugin event handlers. |
| **InteractionGate** | New `PhaseGate` subclass: blocks advancement until at least one file matching `questions/*.md` has a corresponding `answers/*.md` sibling. Reuses existing `ArtifactRequiredGate` idiom | Subclass of `PhaseGate`; `check()` scans the per-sprint artifact store for unanswered questions. Zero new runtime deps. |
| **AttentionQueue** | Per-team cross-sprint view of open questions with priority-scored ordering; backed by `attention.json` under the team directory | Pure functional projection: reads each sprint's `questions/*.md` + `answers/*.md` and produces a sorted list. Cache is rebuildable on demand; no source of truth beyond the individual question files. |
| **TeamMemoryStore** | Layered memory (per-agent private + team-shared) persisted as namespaced markdown files; retrieval via grep initially, optional embedding later | Directory tree: `memory/team/*.md` (shared) + `memory/agents/<agent>/*.md` (private). Reads are grep-scoped; writes go through `/learn` skill that appends + deduplicates. |
| **SmartReviewRouter** | Analyzes diff of current sprint branch; maps changed paths to reviewer personas via glob rules; returns the subset of reviewer agents who should join Review phase | Pure rules engine (CODEOWNERS-style globs from plugin config); runs at Review phase entry; outputs `review_participants` artifact consumed by `PhaseRunner` to dispatch parallel reviewer tasks. |
| **HelperSpawner** | Lets `engineer` fork ephemeral helper agents with sub-worktrees; wraps existing `WorkspaceManager.create_workspace` + merge semantics | Thin façade over `WorkspaceManager` adding child-parent relationship tracking in the spawn registry. Helpers exit when their task completes and the workspace auto-merges. |

## Recommended Project Structure

Delta only — existing layout unchanged. New files additive:

```
clawteam/
├── harness/
│   ├── phase_registry.py           # NEW: ~100 LOC, registry class + validators
│   ├── interaction_gate.py         # NEW: InteractionGate PhaseGate subclass
│   └── phases.py                   # UNCHANGED (Phase already an open str)
├── plugins/
│   ├── base.py                     # MODIFIED: add 4 optional hooks (see below)
│   └── gstack_sprint_plugin.py     # NEW: single cohesive plugin file
├── sprint/                         # NEW directory
│   ├── __init__.py
│   ├── state.py                    # SprintState pydantic model
│   ├── conductor.py                # SprintConductor (per-team orchestrator)
│   ├── registry.py                 # Active-sprint registry (file-backed)
│   └── review_router.py            # SmartReviewRouter (glob-based rules)
├── attention/                      # NEW directory
│   ├── __init__.py
│   ├── queue.py                    # AttentionQueue (priority-sorted projection)
│   └── scorer.py                   # Priority scoring algorithm
├── memory/                         # NEW directory
│   ├── __init__.py
│   ├── store.py                    # TeamMemoryStore (layered, file-backed)
│   └── retriever.py                # Grep-based retrieval (embeddings = v2)
├── templates/
│   └── gstack.toml                 # NEW team template
└── cli/
    └── commands.py                 # MODIFIED: add sprint_app, attend_app Typer subcommands
```

### Structure Rationale

- **`harness/phase_registry.py`** lives in `harness/` because it's mechanically a harness-setup helper, not a sprint concept. Other templates (hedge-fund, research-paper) will want to use it eventually. Placing it outside of `sprint/` makes the upstream PR a cleaner "harness pluggability" change.
- **`sprint/` as new top-level directory** groups the sprint lifecycle cleanly so the GstackSprintPlugin has one natural home for its dependencies. Existing `harness/` stays about plan→execute→verify primitives; `sprint/` is the specific multi-sprint flavor.
- **`attention/` and `memory/`** are separate directories because they are cross-sprint concerns, not sprint-lifecycle concerns. Making them top-level signals "these are horizontals" — they serve Sprint, but could also serve future non-sprint templates.
- **`plugins/gstack_sprint_plugin.py`** as a single file mirrors the existing `ralph_loop_plugin.py` convention (one file = one plugin). The plugin imports from `sprint/`, `attention/`, `memory/` — those modules do the work; the plugin is just the wiring.
- **No `gstack/` package**: tempting but wrong. All gstack-specific behavior should live inside `GstackSprintPlugin` + `gstack.toml`. The directories above (`sprint/`, `attention/`, `memory/`) must remain generic substrate so other plugins/templates can reuse them. That's the upstream-compatibility north star.

## Architectural Patterns

### Pattern 1: Phase machine as plugin-populated list (not enum extension)

**What:** `PhaseRegistry` collects phase names + gate bundles from `HarnessPlugin.contribute_phases()` / `contribute_gates()` at `HarnessOrchestrator.__init__` time. The result is a frozen ordered list passed to `PhaseState.phases`. There is no central enum of phases, no `PhaseState` subclass per flavor, and no modification of existing gate registration — just a list composition.

**When to use:** Whenever the phase set depends on template/plugin choice rather than being hardcoded by the harness. This is the idiomatic answer for every analog we surveyed:

- **LangGraph** ([source](https://docs.langchain.com/oss/python/langgraph/overview)): graphs are built by adding string-named nodes to a `StateGraph` builder; nodes are not enum members. Plugins that contribute behavior contribute nodes.
- **Prefect Blocks** ([source](https://www.prefect.io/)): extensibility is by Python class subclassing + registration, not config-schema expansion.
- **Dagster Components** ([source](https://dagster.io/)): similarly, first-class building blocks are Python classes registered via entry points.
- **Kubernetes CRDs** ([source](https://dev.to/naveens16/beyond-yaml-building-kubernetes-operators-with-crds-and-the-reconciliation-loop-524d)): new kinds are defined as schema + reconciler pairs; the API server enforces schema but the core itself never learns about the kind. Our analog: `PhaseRegistry` is the API-server-like gatekeeper that validates structural conformance, and plugins contribute the "kinds" (phase names).

The common thread: the idiomatic pattern is to make the extensible thing **data, not code in the core**. ClawTeam already made this choice (Phase is `str`, `PhaseState.phases` is a list), so the milestone just needs to formalize the collection point.

**Trade-offs:**
- Pro: Zero core modifications beyond three new optional plugin hooks + a 100-LOC registry class. Maximum upstream PR acceptability.
- Pro: Other future plugins (hedge-fund-sprint, research-paper-sprint) can adopt the exact same mechanism.
- Pro: Phase name collisions detectable at registration time, not runtime.
- Con: Phase names become part of a plugin's public API — renaming "build" to "implement" in a future release is a breaking change for anyone reading sprint state from disk. Mitigation: document phase names as part of the plugin's contract.
- Con: No type-checker enforcement of phase name spelling. Mitigation: module-level constants inside each plugin (the same pattern `phases.py` already uses for the default set).

**Example:**

```python
# clawteam/harness/phase_registry.py (NEW)
from __future__ import annotations
from clawteam.harness.phases import PhaseGate
from clawteam.plugins.base import HarnessPlugin

class PhaseRegistry:
    def __init__(self) -> None:
        self._phases: list[str] = []
        self._gates: dict[str, list[PhaseGate]] = {}
        self._roles: dict[str, str] = {}

    def register_plugin(self, plugin: HarnessPlugin) -> None:
        # New optional hooks, all default to returning empty collections
        new_phases = plugin.contribute_phases() if hasattr(plugin, "contribute_phases") else []
        # Validate: no duplicates across plugins
        dup = set(self._phases) & set(new_phases)
        if dup:
            raise ValueError(f"Phase name collision between plugins: {dup}")
        self._phases.extend(new_phases)
        # Existing hook already returns {phase: [gates]}:
        for phase, gates in plugin.contribute_gates().items():
            self._gates.setdefault(phase, []).extend(gates)
        # New optional hook for roles per phase:
        if hasattr(plugin, "contribute_phase_roles"):
            self._roles.update(plugin.contribute_phase_roles())

    def phases(self) -> list[str]:
        return list(self._phases)
    def gates(self) -> dict[str, list[PhaseGate]]:
        return {p: list(g) for p, g in self._gates.items()}
    def roles(self) -> dict[str, str]:
        return dict(self._roles)
```

### Pattern 2: Team-wide task queue with per-sprint partitioning (Option B, strictly)

**What:** The existing `TaskStore` per team becomes the task queue. Each agent is a long-running CLI process (tmux pane / subprocess) that polls its inbox + the team `TaskStore` for work. Each task carries a `sprint_id` label. Agents don't wait on per-sprint inboxes; they wait on their own inbox, and the `SprintConductor` populates the inbox with tasks from whichever sprint currently needs that role.

**When to use:** For multi-sprint juggling on a single team. The question in the brief asked us to choose between (a) per-sprint asyncio tasks with agents waiting on per-sprint inboxes, (b) long-running agents pulling from team-wide queue, and (c) thread-per-sprint. The answer is **(b), emphatically**, for three independent reasons:

1. **Matches ClawTeam's existing process model.** Agents are already external CLI processes (Claude Code, Codex, etc.) — they are **not** asyncio tasks, they are OS processes with their own event loops. They already poll their mailbox via CLI commands (`clawteam inbox receive`). Pattern (a) would require restructuring agents as in-process coroutines; we don't own the agent loop. Pattern (c) adds threads we don't need.

2. **Research verdict.** Python asyncio guidance is unambiguous: the [producer-consumer pattern with a bounded pool of long-lived worker tasks consuming from a shared queue](https://docs.python.org/3/library/asyncio-queue.html) is the established idiom for this shape of problem. [Temporal's human-in-the-loop pattern](https://docs.temporal.io/ai-cookbook/human-in-the-loop-python) signals workflow instances by ID, not by per-instance blocked tasks. [asyncio.Semaphore pools](https://rednafi.com/python/limit-concurrency-with-semaphore/) are the recommended cap on concurrent work. The industry picks (b) when the work is bursty and the workers are expensive.

3. **Laptop budget.** 11 agents × 10 sprints is not 110 processes. Under (a) it would be 110 agent contexts, each polling; under (b) it's 11 long-running agents, each polling the same inbox path, with the conductor multiplexing up to 10 sprints' worth of task labels through those 11 inboxes. The process footprint is constant at 11 regardless of sprint count (`PROJECT.md` Constraints section explicitly calls this out: "Each agent should be idle-cheap (sleep-polling task queue) so 11 concurrent agents don't dominate a laptop").

**Concurrency caps:** `SprintConductor` uses an `asyncio.Semaphore(max_concurrent_sprints)` (default 10) to cap how many sprints can be "active" (dispatching work) simultaneously. Sprints beyond the cap sit in a `queued` state. This is a safety rail against a human accidentally starting 50 sprints. A second cap, `asyncio.Semaphore(max_tasks_per_agent)` (default 1), ensures the conductor doesn't flood an agent's inbox with work from multiple sprints at once — it serializes sprint-level task dispatches through each agent.

**Trade-offs:**
- Pro: No process footprint scaling with sprint count.
- Pro: Agent memory (see Pattern 5) accumulates across all sprints that agent participates in — that's the "team gets smarter over time" narrative.
- Pro: Natural priority-inversion handling: a high-priority sprint gets its task dispatched first when the agent is free.
- Con: An agent can only do one task at a time. A long Review on sprint 3 blocks Build on sprint 7 for the reviewer. Mitigation: per-role there are sometimes multiple agents (e.g., the four review personas) so the "reviewer" bottleneck is naturally load-balanced.
- Con: Sprint progress is asynchronous and not lockstep. A user running `clawteam sprint status` sees 10 sprints in 10 different phases; the conductor's job is to surface this coherently (per-sprint `status` shows that sprint; `sprint list` shows all).

**Example:**

```python
# clawteam/sprint/conductor.py (sketch)
import asyncio
from clawteam.sprint.state import SprintState
from clawteam.team.tasks import TaskStore  # EXISTING

class SprintConductor:
    def __init__(self, team_name: str, max_concurrent_sprints: int = 10):
        self.team_name = team_name
        self.tasks = TaskStore(team_name)  # existing team-wide queue
        self._sprint_cap = asyncio.Semaphore(max_concurrent_sprints)
        self._agent_cap: dict[str, asyncio.Semaphore] = {}  # per agent=semaphore(1)

    async def dispatch(self, sprint: SprintState) -> None:
        async with self._sprint_cap:
            role = self._role_for_phase(sprint.current_phase)
            agent = self._pick_agent(role)
            cap = self._agent_cap.setdefault(agent, asyncio.Semaphore(1))
            async with cap:
                # Write task to the shared TaskStore labeled with sprint_id
                self.tasks.create(
                    owner=agent,
                    subject=f"[{sprint.sprint_id}:{sprint.current_phase}] {sprint.goal}",
                    metadata={"sprint_id": sprint.sprint_id, "phase": sprint.current_phase},
                )
                # Agent picks it up via existing polling loop; conductor moves on
```

### Pattern 3: AttentionQueue as a priority-scored projection over per-sprint question files

**What:** The source of truth for a question is `sprint/<id>/questions/<N>.md` + (optionally) `sprint/<id>/answers/<N>.md`. AttentionQueue is a read-time projection: scan all sprints, find unanswered questions, sort by priority. Not a database; not a durable queue. Rebuildable from filesystem. Writes go through the question-file artifact, not the queue.

**Why this shape (from notification-system research):** [Linear's Triage](https://linear.app/docs/triage) and [SLA systems](https://linear.app/docs/sla) do exactly this — the issue is the source of truth; the inbox view is a filter/sort layer. [GitHub notifications](https://github.blog/2017-07-06-introducing-code-owners/) similarly: comments are the underlying data, the inbox is a projection. Avoid the mistake of creating a parallel durable queue that can drift from the source question files.

**Priority algorithm (synthesized from [weighted scoring](https://jexo.io/blog/how-to-create-prioritization-framework/), [SLA prioritization](https://linear.app/docs/sla), and [priority inbox](https://www.oreilly.com/library/view/machine-learning-for/9781449314835/ch04.html)):**

```
score = URGENCY + BLOCKING + AGE_BOOST + EXPLICIT_TAG
```

| Component | Formula | Rationale |
|-----------|---------|-----------|
| URGENCY | 100 if question author == ceo/pm (human-facing roles); 50 if eng-mgr/reviewer; 25 otherwise | Mirrors Linear's customer-weighted routing — questions from external-facing personas bubble up |
| BLOCKING | +200 if the question blocks phase advancement (i.e., is gating current phase), else 0 | Blocking questions must dominate non-blocking ones regardless of other factors |
| AGE_BOOST | min(60, hours_since_asked × 2) | Age prevents a non-blocking question from sitting forever; caps at 60 so blocking still wins |
| EXPLICIT_TAG | +150 if question file has `priority: urgent` in frontmatter, +50 if `priority: high`, 0 otherwise | Phase agents can flag "this one really matters" |

Sort descending, display top N in `clawteam attend`. Reason for additive (not multiplicative) scoring: all four dimensions independently contribute; multiplication would over-weight when any dimension is zero. This is the same rationale [Linear's SLA approach](https://linear.app/docs/sla) uses with the fire icon progressively intensifying (gray→yellow→orange→red) — additive, monotonic.

**Trade-offs:**
- Pro: No schema drift risk. The question file is the source of truth; the queue is always correct by reconstruction.
- Pro: Easy to debug — `ls sprints/*/questions/` gives you the state.
- Pro: Maps naturally to `/gsd-` style workflows the user already uses.
- Con: O(N_sprints × N_questions) scan on every `clawteam attend`. For 10 sprints × 10 open questions = 100 files — trivial. If it ever grows past 10,000, add a cache layer.
- Con: Priority scoring is heuristic; users will want to tune weights. Mitigation: weights live in `gstack.toml`; don't hardcode.

### Pattern 4: InteractionGate mechanics — editor-based (markdown round-trip), not CLI-blocking

**What:** When a phase agent writes `sprint/<id>/questions/N.md`, the `InteractionGate` for that phase fails with message "Open questions: sprint/<id>/questions/N.md". The human edits the file (or creates `answers/N.md` alongside), saves, and runs `clawteam sprint advance` (or the gate check happens on next `PhaseRunner.can_advance()` call automatically). No blocking RPC, no terminal prompt, no web UI required.

**Why editor-based:** We evaluated three options against the 1-to-10-parallel-sprint scale target:

| Pattern | 1 sprint | 5 sprints | 10 sprints | Notes |
|---------|---------|-----------|------------|-------|
| CLI-based prompt (blocks terminal) | Fine | Painful (10 open terminals?) | Unusable | Classic pair-programming feel but doesn't scale |
| Web UI | Fine | Fine | Fine | Infra burden; v1 non-goal per PROJECT.md |
| **Editor-based markdown files** | **Fine** | **Good** | **Good** | Scales naturally; the user already lives in their editor |

Editor-based wins because it matches the user's existing workflow: they're in VS Code / neovim / emacs anyway, editing code; answering a question is "open `questions/3.md`, write your answer, save." [LangGraph's interrupt pattern](https://docs.langchain.com/oss/python/langgraph/interrupts) does this internally (pause → resume with payload), but LangGraph ties this to graph execution; we don't need that because our "agent loop" is actually the external CLI process that naturally pauses while the phase gate is failed.

A file watcher (Python `watchdog`) is **optional, not required**: the gate check runs on demand via `PhaseRunner.can_advance()`. Adding `watchdog` as an optional dep would let `clawteam attend --watch` auto-advance sprints the moment a human saves an answer, but v1 can ship without it — `clawteam sprint advance` or periodic polling is enough.

**MCP elicitation note:** The [MCP protocol has a server-to-client elicitation flow](https://modelcontextprotocol.io/specification/draft/client/elicitation) designed for this exact pattern, but it's per-request and per-session. Our needs are cross-session (question can be answered days later by a different CLI invocation). The file-based pattern is strictly more durable.

**Example:**

```python
# clawteam/harness/interaction_gate.py (NEW)
from pathlib import Path
from clawteam.harness.phases import PhaseGate, PhaseState

class InteractionGate(PhaseGate):
    """Block advancement while unanswered questions exist in the sprint directory.

    Questions are sprint/<id>/questions/<N>.md. An answer is either:
      - a sibling file sprint/<id>/answers/<N>.md, OR
      - a line `answered: YYYY-MM-DD by <user>` in the question frontmatter.
    """
    def __init__(self, sprint_dir_provider):
        self._dir = sprint_dir_provider  # callable → Path

    def check(self, state: PhaseState) -> tuple[bool, str]:
        sprint_dir = self._dir(state)
        qdir = sprint_dir / "questions"
        adir = sprint_dir / "answers"
        if not qdir.is_dir():
            return True, ""
        open_q = []
        for q in sorted(qdir.glob("*.md")):
            n = q.stem
            if not (adir / f"{n}.md").is_file():
                # also accept inline `answered:` in frontmatter
                if "answered:" not in q.read_text(encoding="utf-8")[:500]:
                    open_q.append(str(q))
        if open_q:
            return False, f"Open questions: {', '.join(open_q)}"
        return True, ""
```

### Pattern 5: TeamMemory as layered grep-first store (per-agent private + team-shared)

**What:** Two-tier file hierarchy under `~/.clawteam/teams/<team>/memory/`:

```
memory/
├── team/                  # shared: every agent in this team can read
│   ├── codebase.md        # "user uses pnpm, not npm"
│   ├── taste.md           # "user prefers function-forward React, no classes"
│   └── conventions.md     # "all tests in tests/ not src/__tests__/"
└── agents/
    ├── ceo/
    │   └── decisions.md   # ceo-private: past scope calls
    ├── engineer/
    │   └── gotchas.md     # engineer-private: "this codebase uses esm but Jest is CJS"
    ├── reviewer/
    │   └── patterns.md    # reviewer-private: "user rejects mocks in integration tests"
    └── <other roles>/...
```

**Why layered (not centralized, not fully distributed):** Converged research finding. [Letta/MemGPT](https://www.letta.com/blog/agent-memory) uses three tiers (core/recall/archival) but all per-agent; for a team, an additional shared tier is the architectural analog. [Multi-agent memory research](https://arxiv.org/html/2505.18279v1) and [MongoDB's blog on multi-agent memory engineering](https://www.mongodb.com/company/blog/technical/why-multi-agent-systems-need-memory-engineering) both conclude the **hybrid pattern** is the correct one: private memory for per-role context + shared memory for team-wide truth. Fully-centralized causes context bloat (every agent sees every other agent's notes); fully-distributed breaks "team gets smarter over time" because the CEO's past scope decision is invisible to the engineer.

**Retrieval — grep first, embeddings later:** v1 uses grep because:
1. [Letta benchmarked filesystem-based memory retrieval vs embeddings](https://www.letta.com/blog/benchmarking-ai-agent-memory) and found that for structured, human-written notes, grep + ranked snippets is competitive and simpler.
2. No new deps (`ripgrep` is already ubiquitous; Python's `re` is the fallback).
3. Claude Code's [native project memory](https://code.claude.com/docs/en/memory) and the [Learnings.md pattern](https://www.mindstudio.ai/blog/self-learning-claude-code-skill-learnings-md) both use plain markdown with header-based section structure, no embeddings.

The `/learn` skill (ported from gstack) is team-scoped: when any agent invokes `/learn <topic>: <fact>`, the skill appends to `memory/team/<topic>.md` (creating if absent) with a dedup check. When `reviewer` invokes `/learn reviewer: <pattern>`, it goes to `memory/agents/reviewer/<topic>.md`. The router is a simple rule: `/learn <role>:` prefix goes to private; anything else goes to shared.

**Read path at sprint start:**
```
1. Each agent's prompt is prefixed with:
   - `memory/team/*.md` summaries (shared context)
   - `memory/agents/<this_agent>/*.md` (private to them)
2. Agents can grep deeper with:
   `clawteam memory search <query> --team <team> --scope shared`
```

**Embeddings migration path (v2):** The structure already separates storage (files) from retrieval (grep). Adding an embedding index is additive — swap the retriever, keep the writer. We don't build it in v1 because the file-first design [Letta's own benchmarks](https://www.letta.com/blog/benchmarking-ai-agent-memory) show is adequate for most workloads.

**Trade-offs:**
- Pro: Zero new deps. Human-inspectable. Git-diffable.
- Pro: Supports the "hire your team" narrative — after 10 sprints, `memory/team/codebase.md` has 10 sprints' worth of learnings, fully legible.
- Con: Grep doesn't understand semantics — "auth code" won't match "authentication module" without explicit cross-refs. Mitigation: `/learn` skill prompts can include synonym tagging.
- Con: No automatic forgetting / decay. Over years, memory could get stale. Mitigation: periodic `/learn --reflect` skill that rewrites stale facts; v2 addition.

### Pattern 6: SmartReviewRouter — CODEOWNERS-style globs + optional LLM fallback (rules-first, strictly)

**What:** At Review phase entry, `SmartReviewRouter` runs `git diff` against the sprint branch, extracts changed file paths, and matches them against a rules table loaded from `gstack.toml`:

```toml
[template.review_routing]
# CODEOWNERS-syntax path globs → reviewer persona
"*.tsx" = "designer"
"*.css" = "designer"
"app/design-system/**" = "designer"
"app/api/**" = "dx-lead"
"src/auth/**" = "security"
"**/crypto/**" = "security"
"package.json" = "dx-lead"
".github/workflows/**" = "sre"
"infra/**" = "sre"
# Default: always include reviewer (staff eng); never skip
"*" = "reviewer"
```

**Why rules-first (from review-tool research):** [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners) is the canonical pattern: glob-match path → owner. [CodeRabbit's architecture](https://learnwithparam.com/blog/architecting-coderabbit-ai-agent-intelligence-layer) uses a **router → classifier → specialist** topology where the router is rule-based and cheap; LLM classification is reserved for ambiguous cases. [Graphite and PullApprove](https://www.pullapprove.com/codeowners/) extend CODEOWNERS with additional matcher types but stay rule-based at the core. Phabricator's Herald (the original "routing rules on diffs" tool) is also pure rules.

**The pattern conclusion: rules are deterministic, fast, debuggable, and correct 95% of the time for path-based routing.** LLM classification is correct >95% of the time but costs a model call per review and can hallucinate. Start rules-only; add optional LLM fallback for the "no rule matched" case later if needed.

**Parallel dispatch:** Once participants are selected (say: `[designer, security, reviewer]`), `SprintConductor` creates one task per participant in `TaskStore` with `owner=<persona>`. Each reviewer writes their review artifact to `sprint/<id>/reviews/<persona>.md`. A final gate on Review phase: `AllReviewsCompleteGate` (new, analogous to existing `AllTasksCompleteGate`). Once all reviews are in, the `reviewer` (staff eng) runs a synthesis task that writes `sprint/<id>/review-report.md` — the consumable artifact the next phase depends on.

**Trade-offs:**
- Pro: Deterministic; debuggable (`clawteam sprint review-plan <id>` prints which personas will join and why).
- Pro: Config-driven via `gstack.toml` — users tweak per-project without code changes.
- Pro: Matches existing CODEOWNERS mental model → zero learning curve.
- Con: Rules need occasional tuning for new directory layouts. Mitigation: default rules ship in template; users override.
- Con: Cross-cutting changes (e.g., a refactor touching auth + UI + API) will pull in 3+ reviewers. Mitigation: feature, not bug — that's exactly when you want multiple reviewers.

### Pattern 7: HelperSpawner — engineer-forked sub-worktrees as first-class WorkspaceManager children

**What:** `engineer` agent can invoke a new MCP tool `clawteam sprint spawn-helper <sprint_id> <helper_name>` that:
1. Creates a sub-worktree rooted at `<sprint_branch>` named `<sprint_branch>/helper/<helper_name>` via existing `WorkspaceManager.create_workspace()`.
2. Spawns a new agent CLI process in that worktree using existing `SpawnBackend`.
3. Registers the helper in `spawn_registry.json` with `parent_agent = engineer`.
4. When helper reports task complete, `WorkspaceManager.merge()` (existing) merges helper branch back into the sprint branch; helper process exits; registry cleaned up.

This is architecturally a thin wrapper — the existing `WorkspaceManager` already supports per-agent worktrees and merges; the spawn registry already tracks agents. The new bit is the parent-child relationship and the "ephemeral" lifecycle flag.

**Trade-offs:**
- Pro: Reuses all existing infra; no new workspace semantics.
- Pro: Matches gstack's "pair-agent" skill model — engineer can fork a helper with a narrow task.
- Con: Risk of helper proliferation (engineer spawns 100 helpers). Mitigation: cap at N helpers per engineer per sprint (`max_helpers_per_engineer` config, default 3).
- Con: Merge conflicts between helpers. Mitigation: existing `WorkspaceManager.conflicts` module; helpers serialized through merge queue.

## Data Flow

### Data flow 1: `clawteam team spawn gstack --name acme`

```
User CLI
   │
   ▼
TeamManager.create(template=gstack)          [EXISTING]
   │
   ▼ (reads clawteam/templates/gstack.toml, installs 11 members)
For each of 11 agents:
   - TeamManager.add_member(name, role)       [EXISTING]
   - WorkspaceManager.create_workspace()      [EXISTING, per-agent "desk" worktree]
   - Mailbox directory created                [EXISTING]
   │
   ▼
PluginManager.load(gstack_sprint_plugin)     [EXISTING, calls on_register]
   │
   ▼
Plugin.on_register(ctx):
   - ctx.bus.subscribe(SprintPhaseTransition, handler)
   - TeamMemoryStore.init(team)               [NEW; creates memory/ tree]
   - AttentionQueue.init(team)                [NEW; creates attention/ tree]
   │
   ▼
spawn agents in their worktrees              [EXISTING: TmuxBackend/SubprocessBackend]
   │
   ▼
Team is persistent; agents are long-running CLIs waiting on their mailboxes.
```

### Data flow 2: `clawteam sprint start --team acme --goal "add billing page"`

```
User CLI
   │
   ▼
SprintConductor.start_sprint(team, goal)     [NEW]
   │
   ▼
Create SprintState (sprint_id, goal, current_phase="think")
   ├─ WorkspaceManager.create_workspace for sprint branch    [EXISTING]
   ├─ Create sprint artifact directory: sprints/<id>/
   └─ Persist SprintState to sprints/<id>/state.json via file_locked  [EXISTING primitive]
   │
   ▼
PhaseRegistry.load_plugins() → phases, gates, roles        [NEW]
   │
   ▼
PhaseRunner initialized with:
   - phases = [think, plan, build, review, test, ship, reflect]
   - gates = {think: [InteractionGate], plan: [InteractionGate, ArtifactRequired(plan.md)], ...}
   - roles = {think: pm, plan: ceo, build: engineer, ...}
   │
   ▼
Dispatch first task:
   - SprintConductor.dispatch(sprint) acquires sprint_cap + agent_cap semaphores
   - TaskStore.create(owner=pm, subject=f"[sprint:{id}:think] {goal}")  [EXISTING]
   │
   ▼
pm agent's existing polling loop picks up task, begins Think phase.
```

### Data flow 3: Phase advance (auto-advance mode)

```
Agent (pm) completes their think task, writes sprint/<id>/design-doc.md
   │
   ▼ (agent runs: clawteam task update <id> --status completed)
TaskStore.update()                           [EXISTING]
   │
   ▼ (emits TaskCompleted event on EventBus)
Plugin subscriber: GstackSprintPlugin._on_task_completed
   │
   ▼
PhaseRunner.can_advance()
   - Loops over gates for current phase
   - ArtifactRequired(design-doc.md) → pass  [EXISTING]
   - InteractionGate → scans questions/*.md vs answers/*.md [NEW]
     If unanswered Q exists: return (False, "Open questions: ...")
   │
   ▼ (if all gates pass)
PhaseRunner.advance()                        [EXISTING]
   - Emits PhaseTransition event              [EXISTING]
   - Saves SprintState via file_locked       [EXISTING]
   │
   ▼
Plugin subscriber on PhaseTransition: SprintConductor.dispatch() for new phase.
```

### Data flow 4: Human answers a question

```
Agent (designer) during Plan phase writes sprint/<id>/questions/3.md
  "? Should the billing page reuse checkout components, or build new?"
   │
   ▼
At phase advance check, InteractionGate fails:
   "Open questions: sprint/<id>/questions/3.md"
Phase stays in Plan. Conductor stops dispatching.
   │
   ▼
AttentionQueue scans all sprints:
   - finds sprint/<id>/questions/3.md has no sprint/<id>/answers/3.md
   - computes priority score (urgency=designer=25, age=0, no tag, blocking=200) = 225
   - adds to sorted output
   │
   ▼
User runs: clawteam attend
   - Prints top-N questions across all sprints, priority-descending
   - Shows full path for editor: `sprint/abc123/questions/3.md`
   │
   ▼
User opens file in editor, writes answer in-place or creates answers/3.md
   │
   ▼
Next PhaseRunner.can_advance() check: InteractionGate passes.
   │
   ▼
Phase advances; SprintConductor dispatches next phase's first task.
```

### Data flow 5: Smart review routing

```
Plan phase complete → Build phase runs → Build phase complete
   │
   ▼
PhaseRunner attempts advance to Review:
   - Triggers Review phase setup via plugin hook "on_phase_enter"
   │
   ▼
SmartReviewRouter.route(sprint):
   - Runs: git diff sprint_branch..HEAD --name-only [wrapped via workspace.git]
   - Loads review_routing rules from gstack.toml
   - For each changed path, matches globs bottom-to-top (last-match-wins like CODEOWNERS)
   - Returns: set(personas) = {designer, dx-lead, reviewer}  (e.g., touched tsx + api)
   │
   ▼
SprintConductor dispatches N parallel tasks:
   - TaskStore.create(owner=designer, subject=f"[sprint:{id}:review] review UI changes")
   - TaskStore.create(owner=dx-lead, subject=f"[sprint:{id}:review] review API changes")
   - TaskStore.create(owner=reviewer, subject=f"[sprint:{id}:review] synthesize review report")
   │
   ▼ (reviewer task depends on designer + dx-lead tasks via existing --blocked-by)
Parallel execution:
   - designer writes sprint/<id>/reviews/designer.md
   - dx-lead writes sprint/<id>/reviews/dx-lead.md
   │
   ▼ (on both complete, blocked-by clears)
reviewer synthesizes → sprint/<id>/review-report.md
   │
   ▼
AllReviewsCompleteGate passes; phase advances to Test.
```

### Data flow 6: Team memory write (shared scope)

```
Any agent in team acme invokes: clawteam memory learn --team acme --topic codebase "uses pnpm not npm"
   │
   ▼ (via new MCP tool memory_learn)
TeamMemoryStore.write(team, topic=codebase, fact="uses pnpm not npm", scope=shared)
   │
   ▼
Open: memory/team/codebase.md under file_locked        [EXISTING primitive]
   │
   ▼
Dedup check: does existing content contain this fact? (grep-based)
   - If yes: no-op
   - If no: append with timestamp + source agent name
   │
   ▼
atomic_write_text                                       [EXISTING]
   │
   ▼
Emit MemoryWritten event on EventBus (NEW event type; for board visualization)
```

### Data flow 7: Team memory read (sprint start)

```
SprintConductor starts new sprint for team acme
   │
   ▼
For each agent about to receive a task for this sprint:
   TeamMemoryStore.prompt_prefix(team=acme, agent=<role>)
     - Reads memory/team/*.md (shared, all agents)
     - Reads memory/agents/<role>/*.md (private to this role)
     - Concatenates with section headers
     - Truncates to max_memory_tokens (default 4000) by recency
   │
   ▼
Task dispatch includes prompt_prefix as the first block of the task body.
   │
   ▼
Agent receives task, sees team history + role-specific history in context.
```

### Data flow 8: Engineer forks a helper

```
engineer agent during Build phase needs to investigate a subproblem in parallel
   │
   ▼ (engineer invokes MCP tool: clawteam sprint spawn-helper)
HelperSpawner.spawn(sprint_id, helper_name="billing-sql-investigator", task="profile slow query")
   │
   ▼
WorkspaceManager.create_workspace(team, agent=helper_name, branch=<sprint_branch>/helper/<name>)
                                                                   [EXISTING]
   │
   ▼
SpawnBackend.spawn() the helper CLI in the sub-worktree              [EXISTING]
   │
   ▼
Register in spawn_registry.json with parent_agent=engineer, ephemeral=true
   │
   ▼
Helper runs, writes findings to sub-worktree, runs clawteam task update --status completed
   │
   ▼ (completion hook via event subscriber)
WorkspaceManager.merge(helper_branch → sprint_branch) with conflict resolution  [EXISTING]
   │
   ▼
Helper process exits; registry entry cleaned; engineer picks up merged changes.
```

## Build Order

**Justification:** Each step produces something runnable. Later steps depend on earlier ones. Steps 1–2 are pure core-harness changes (upstream PR candidates); steps 3–9 are plugin-and-above.

| Step | Component | Depends on | Runnable checkpoint |
|------|-----------|------------|---------------------|
| **1. PhaseRegistry + HarnessPlugin hook additions** | `clawteam/harness/phase_registry.py`, 3 new optional methods on `HarnessPlugin` (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`) | existing `HarnessPlugin`, `PhaseRunner` | `tests/test_phase_registry.py` — load two fake plugins, assert collision detection + ordering |
| **2. SprintState + file-backed persistence** | `clawteam/sprint/state.py`, `clawteam/sprint/registry.py` | existing `fileutil.file_locked`, `get_data_dir` | Load/save roundtrip test; `clawteam sprint list --team <t>` reads it |
| **3. InteractionGate** | `clawteam/harness/interaction_gate.py` | step 2 | Unit tests with fake question/answer files; gate fails iff unanswered Q exists |
| **4. AttentionQueue + scorer** | `clawteam/attention/queue.py`, `clawteam/attention/scorer.py` | steps 2, 3 | `clawteam attend --team <t>` prints correctly-sorted queue against synthetic sprints |
| **5. TeamMemoryStore + /learn skill** | `clawteam/memory/store.py`, `clawteam/memory/retriever.py`, new MCP tool `memory_learn`, new MCP tool `memory_search` | existing `file_locked` | Write via CLI, read via grep, confirm per-agent/shared separation |
| **6. SprintConductor (core, single sprint)** | `clawteam/sprint/conductor.py` | steps 1, 2, 4, 5; existing `TaskStore`, `EventBus` | `clawteam sprint start --goal "hello"` runs a single sprint end-to-end through Think→…→Reflect with auto-advance |
| **7. SmartReviewRouter** | `clawteam/sprint/review_router.py` | step 6; existing `workspace.git` | `clawteam sprint review-plan <id>` prints which reviewers the router would select for a given diff |
| **8. GstackSprintPlugin (the plugin itself)** | `clawteam/plugins/gstack_sprint_plugin.py`, `clawteam/templates/gstack.toml`, all gstack prompts/methodology ported into prompts | steps 1–7 | `clawteam team spawn gstack --name acme` creates the 11-agent team and `sprint start` runs a full Think→Ship sprint using ported methodology |
| **9. HelperSpawner** | `clawteam/sprint/helper_spawner.py`, new MCP tool `sprint_spawn_helper` | step 8; existing `WorkspaceManager.merge` | `engineer` agent forks a helper, helper completes, merge verified |
| **10. Multi-sprint juggling** | `SprintConductor` semaphore caps + active-sprint registry enhancements | steps 6, 8 | `sprint start` run 5 times in succession → 5 active sprints, all advancing via shared agents |
| **11. CLI polish: `attend`, `team show`, per-sprint `show`** | `clawteam/cli/commands.py` | steps 4, 6, 10 | Dashboard commands render correctly across multi-sprint team |

**Critical path:** Steps 1 → 2 → 3 → 6 → 8 → 10 is the minimum-viable thread for "one team running multiple sprints." Steps 4, 5, 7, 9, 11 are additive quality-of-life on that thread.

**Parallelization opportunities (if multi-agent development):**
- Steps 4, 5, 7 are independent of each other; can be built in parallel after step 2.
- Step 9 is independent of step 10; can be built in parallel.
- Step 11 is the last gluing step — do it after steps 4, 6, 10 land.

## Core Changes vs Gstack-Plugin-Only (Upstream PR Acceptability Split)

### Core changes (target for upstream PR)

These are the **absolute minimum** core diffs. Every one of them is additive (new file or new optional method); no existing behavior changes. Rationale in brackets.

| File | Change | PR framing |
|------|--------|------------|
| `clawteam/harness/phase_registry.py` | **NEW** — `PhaseRegistry` class, ~100 LOC | "Add plugin-populated phase registry so templates can ship their own phase sets" |
| `clawteam/plugins/base.py` | **MODIFIED** — add 3 new `HarnessPlugin` optional methods returning empty defaults: `contribute_phases() -> list[str]`, `contribute_phase_roles() -> dict[str, str]`, `contribute_review_routers() -> list[ReviewRouter]` | "Broaden HarnessPlugin hooks to support sprint-style templates; existing plugins unaffected" |
| `clawteam/harness/interaction_gate.py` | **NEW** — `InteractionGate` PhaseGate subclass, ~60 LOC | "Add InteractionGate — questions/answers round-trip via sprint artifact dir; complements existing HumanApprovalGate" |
| `clawteam/harness/orchestrator.py` | **MINIMAL MODIFICATION** — `__init__` optionally consults `PhaseRegistry` when `phases` arg is None; no change to default behavior | "HarnessOrchestrator: use PhaseRegistry when phases unset" |
| `clawteam/sprint/` (whole directory) | **NEW** — `state.py`, `conductor.py`, `registry.py`, `review_router.py` | "Add sprint/ module: generic multi-sprint coordination on top of HarnessOrchestrator; usable by any template that opts in" |
| `clawteam/attention/` (whole directory) | **NEW** — `queue.py`, `scorer.py` | "Add attention/ module: cross-sprint question queue; template-agnostic" |
| `clawteam/memory/` (whole directory) | **NEW** — `store.py`, `retriever.py` | "Add memory/ module: layered team/agent memory; template-agnostic" |
| `clawteam/cli/commands.py` | **MODIFIED** — new Typer subcommands `sprint`, `attend`, `memory`; no changes to existing commands | "Expose new modules via CLI" |
| `clawteam/mcp/tools/` | **NEW files** — `sprint.py`, `attention.py`, `memory.py` exported in `TOOL_FUNCTIONS` | "MCP tool surface for new modules" |

**Why these are upstream-acceptable:**
1. All module-level additions; no existing file (except `plugins/base.py` and `orchestrator.py`) gets non-trivial edits.
2. `plugins/base.py` additions are all optional methods with empty defaults — existing plugins (like `RalphLoopPlugin`) need zero changes.
3. Sprint/attention/memory modules are generic substrate. Other templates (hedge-fund, research-paper, strategy-room) could adopt them without depending on gstack.
4. Total LOC delta: ~1500-2000 lines of new code, ~50 lines of existing-file modifications. PR-sized.

### Gstack-plugin-only (does not touch core)

| File | Purpose |
|------|---------|
| `clawteam/plugins/gstack_sprint_plugin.py` | The entire gstack-specific logic: phase list, per-phase roles, per-phase gates wiring, prompt contributions, event handlers, skill registrations |
| `clawteam/templates/gstack.toml` | 11-agent roster, per-agent prompts, review_routing rules, memory schemas |
| Gstack-specific skills under `skills/gstack/` or embedded in prompts | /office-hours, /plan-ceo-review, /retro, /design-review, /review, /qa, /cso, /ship, /canary, /learn methodology |

**The test:** If `clawteam/plugins/gstack_sprint_plugin.py` is deleted and `gstack.toml` is removed, the rest of the codebase should compile, all existing tests should pass, and other templates should work unchanged. That's the upstream-compatibility contract.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **1 team, 1 sprint** | Stock — everything works out of the box |
| **1 team, 10 concurrent sprints** | Stock — semaphore cap at 10; `attend` queue at ~100 items; grep memory fast |
| **1 team, 100 concurrent sprints** | (v2 territory) — consider SQLite for SprintState index, keep files as source of truth; add pagination to `attend` |
| **10 teams, 10 sprints each (100 active)** | (v2 territory) — introduce optional embedded index for AttentionQueue; consider per-team subprocesses for isolation |
| **Enterprise (1000+)** | Not in scope. Would require DB, message bus other than filesystem, and pod-per-team deployment model |

### Scaling Priorities

1. **First bottleneck: AttentionQueue rebuild on every `clawteam attend`.** At 100+ active questions, the O(N) scan becomes noticeable. Fix: add in-memory cache keyed by `max(question_files_mtime)`. Invalidate only on file changes.
2. **Second bottleneck: Task dispatch serialization per agent.** With 11 agents juggling 10 sprints, one slow sprint can stall one agent's pipeline. Fix: increase `max_tasks_per_agent` semaphore to 2 (short interleaving). Trade-off: context switching cost in the agent.
3. **Third bottleneck: Grep over large memory files.** Once `memory/team/codebase.md` is 100KB+, grep gets slow-ish. Fix: move to headered markdown with per-section files; grep per-file, merge results. Still no embeddings needed.

## Anti-Patterns

### Anti-Pattern 1: Adding PhaseState subclasses per template

**What people do:** Create `SprintPhaseState(PhaseState)` with new fields for sprint_id, review_participants, etc.
**Why it's wrong:** Breaks serialization back-compat (existing state.json files can't deserialize the subclass). Forks the ecosystem — every template ends up with its own PhaseState variant. Contradicts the "open str" design already in place.
**Do this instead:** Keep `PhaseState` as the harness-level state. Store sprint-specific state in a **separate** `SprintState` model in `clawteam/sprint/state.py`. The `PhaseRunner` operates on `PhaseState`; the `SprintConductor` operates on `SprintState` + (for harness interop) a `PhaseState`. Cleanly separate concerns.

### Anti-Pattern 2: Thread-per-sprint or per-sprint asyncio task with agents waiting on per-sprint inboxes

**What people do:** Create one coroutine per sprint, each dispatching to agents tagged by sprint.
**Why it's wrong:** Multiplies process/context footprint with sprint count. Agents (external CLIs) can't wait on multiple inboxes without significant restructuring. Tested via [asyncio community practice](https://docs.python.org/3/library/asyncio-queue.html) and [Temporal's signal-based pattern](https://docs.temporal.io/ai-cookbook/human-in-the-loop-python) — neither uses this shape.
**Do this instead:** Team-wide `TaskStore`-as-queue + per-sprint labels on tasks (Pattern 2). Agent footprint stays constant.

### Anti-Pattern 3: Building a web UI for InteractionGate in v1

**What people do:** Stand up a Flask/FastAPI server with a question-answering dashboard.
**Why it's wrong:** Infra burden, auth concerns, doesn't match user workflow. Users already live in their editor. The file-based pattern is more durable (answer persists whether the server is running or not).
**Do this instead:** Editor-as-UI (Pattern 4). Optional: `watchdog`-based auto-advance in a `clawteam attend --watch` flag. Web UI is v2+ if ever.

### Anti-Pattern 4: Embedding-first memory retrieval

**What people do:** Bring in ChromaDB/pgvector/FAISS; build an embedding index for every memory write.
**Why it's wrong:** New deps. [Letta's benchmarks](https://www.letta.com/blog/benchmarking-ai-agent-memory) show filesystem+grep is competitive for structured notes. Embeddings are correct tool for unstructured prose, not the team's curated taste notes. Premature optimization.
**Do this instead:** Grep-first. Design the writer to produce grep-friendly output. Swap to embeddings in v2 if real workloads show retrieval failures.

### Anti-Pattern 5: LLM-classified review routing in v1

**What people do:** Use an LLM call to look at the diff and pick reviewers.
**Why it's wrong:** Non-deterministic. Costs a model call per review. Hallucinates personas. [CodeRabbit's architecture](https://learnwithparam.com/blog/architecting-coderabbit-ai-agent-intelligence-layer) uses rule-based routing + LLM only for the classifier inside the chosen reviewer's pass — not for routing itself.
**Do this instead:** CODEOWNERS-style globs (Pattern 6). Config-driven. Deterministic. Adds LLM fallback for "no rule matched" as a v2 enhancement.

### Anti-Pattern 6: Plugin mutates existing PhaseState / PhaseRunner internals

**What people do:** `gstack_sprint_plugin.py` reaches into `PhaseRunner._gates` and monkey-patches.
**Why it's wrong:** Breaks if `PhaseRunner` internals change. Makes upstream PR unacceptable (intrusive). Makes other plugins fragile.
**Do this instead:** All plugin contributions go through documented hooks on `HarnessPlugin` base class. If a hook doesn't exist for what you need, **add the hook to the base class** (step 1 of the build order) — don't reach in.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| External coding CLIs (Claude, Codex, etc.) | Existing spawn + adapter layer (`clawteam/spawn/`) | Zero change. Sprint agents are spawned identically to other ClawTeam agents. |
| `git` worktree | Existing `WorkspaceManager` | Zero change. Sprint branches and helper sub-worktrees use existing API. |
| `ripgrep` (optional) | Shell out from `TeamMemoryStore.retriever` | Fallback to Python `re` if absent. |
| `watchdog` (optional) | In `clawteam attend --watch` only | Optional dep; behavior degrades gracefully to manual polling. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI ↔ SprintConductor | Direct Python call (in-process) | `SprintConductor` is per-team singleton; CLI instantiates via `SprintConductor(team)` and calls methods |
| SprintConductor ↔ TaskStore | Direct Python call (existing TaskStore API) | Tasks carry `sprint_id` + `phase` metadata for disambiguation |
| SprintConductor ↔ EventBus | Subscribe/emit (existing pattern) | New event types: `SprintStarted`, `SprintPhaseTransition`, `ReviewRoutingComputed`, `QuestionOpened`, `QuestionAnswered`, `MemoryWritten` |
| Plugin ↔ PhaseRegistry | Registration-time dictionaries | Plugins declare phases/gates/roles; registry composes; runner uses composed result |
| AttentionQueue ↔ sprint directories | Read-only projection | Never writes; always scans on demand |
| TeamMemoryStore ↔ agents | Through new MCP tool `memory_learn` + `memory_search` | Agents see it as two MCP tools; infrastructure is file-backed store |
| InteractionGate ↔ sprint questions dir | Read-only check | Does not write; only reads file existence/content to compute gate state |

## Sources

### Primary — read firsthand from the ClawTeam codebase
- `/home/jac/repos/ClawTeam-gstack/.planning/PROJECT.md` — scope, constraints, key decisions
- `/home/jac/repos/ClawTeam-gstack/.planning/codebase/ARCHITECTURE.md` — existing layers, data flows, abstractions
- `/home/jac/repos/ClawTeam-gstack/.planning/codebase/STRUCTURE.md` — directory layout, naming conventions
- `/home/jac/repos/ClawTeam-gstack/.planning/codebase/INTEGRATIONS.md` — external surfaces, runtime deps
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/phases.py` — Phase is `str`, PhaseState.phases is configurable list
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/orchestrator.py` — HarnessOrchestrator shape
- `/home/jac/repos/ClawTeam-gstack/clawteam/plugins/base.py` — existing HarnessPlugin hooks
- `/home/jac/repos/ClawTeam-gstack/clawteam/plugins/manager.py` — plugin discovery/loading
- `/home/jac/repos/ClawTeam-gstack/clawteam/plugins/ralph_loop_plugin.py` — example plugin style
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/context.py` — HarnessContext surface
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/artifacts.py` — ArtifactStore API
- `/home/jac/repos/ClawTeam-gstack/clawteam/harness/roles.py` — AgentRole is `str`, roles are open
- `/home/jac/repos/ClawTeam-gstack/clawteam/events/bus.py` — sync EventBus with priority + async pool
- `/home/jac/repos/ClawTeam-gstack/clawteam/workspace/manager.py` — per-team worktree lifecycle

### Phase-machine-as-plugin patterns (Context7 + web research)
- [LangGraph: interrupt() + resume pattern](https://docs.langchain.com/oss/python/langgraph/interrupts) (Context7 authoritative)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangChain extensibility hooks & plugins](https://www.gocodeo.com/post/extensibility-in-ai-agent-frameworks-hooks-plugins-and-custom-logic)
- [Prefect workflow orchestration (Block system)](https://www.prefect.io/)
- [Prefect vs Dagster](https://dagster.io/vs/dagster-vs-prefect)
- [Kubernetes CRD + reconciler pattern](https://dev.to/naveens16/beyond-yaml-building-kubernetes-operators-with-crds-and-the-reconciliation-loop-524d)
- [kube.rs controller patterns](https://kube.rs/controllers/intro/)

### Concurrency model
- [Python asyncio.Queue docs](https://docs.python.org/3/library/asyncio-queue.html)
- [Temporal Python SDK human-in-the-loop](https://docs.temporal.io/ai-cookbook/human-in-the-loop-python)
- [Temporal long-running workflows](https://temporal.io/blog/very-long-running-workflows)
- [asyncio Semaphore patterns for bounded concurrency](https://rednafi.com/python/limit-concurrency-with-semaphore/)
- [Python Concurrency with asyncio (Manning, ch.12: queues)](https://livebook.manning.com/book/concurrency-in-python-with-asyncio/chapter-12)

### Priority scoring / notification inbox patterns
- [Linear Triage](https://linear.app/docs/triage) and [Linear SLA](https://linear.app/docs/sla) — customer-weighted + age-based priority
- [Priority Inbox algorithm (O'Reilly ML for Email)](https://www.oreilly.com/library/view/machine-learning-for/9781449314835/ch04.html)
- [Weighted scoring prioritization frameworks](https://jexo.io/blog/how-to-create-prioritization-framework/)
- [Ticket routing best practices 2026](https://www.articsledge.com/post/ticket-routing-software)

### Human-in-the-loop / InteractionGate
- [LangGraph interrupt() docs (Context7)](https://docs.langchain.com/oss/python/langgraph/interrupts)
- [Making human-in-the-loop easier with interrupt](https://blog.langchain.com/making-it-easier-to-build-human-in-the-loop-agents-with-interrupt/)
- [MCP elicitation spec](https://modelcontextprotocol.io/specification/draft/client/elicitation) — compared and rejected for cross-session use
- [Python watchdog library](https://pypi.org/project/watchdog/) — optional auto-advance support

### Review routing
- [GitHub CODEOWNERS docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [GitLab advanced CODEOWNERS](https://docs.gitlab.com/user/project/codeowners/advanced/)
- [PullApprove — smarter code ownership](https://www.pullapprove.com/codeowners/)
- [Architecting CodeRabbit's intelligence layer](https://learnwithparam.com/blog/architecting-coderabbit-ai-agent-intelligence-layer) — router → classifier → specialist topology
- [GitHub PR Review best practices 2026](https://dev.to/rahulxsingh/github-pr-review-best-practices-and-tools-2026-1p90)

### Persistent agent memory
- [Letta (MemGPT) memory tiers](https://docs.letta.com/concepts/memgpt/) — core/recall/archival layered memory
- [Letta agent memory blog](https://www.letta.com/blog/agent-memory)
- [Letta benchmarking agent memory (filesystem vs embeddings)](https://www.letta.com/blog/benchmarking-ai-agent-memory) — filesystem-first validated
- [Multi-agent memory survey (TechRxiv)](https://www.techrxiv.org/users/1007269/articles/1367390/master/file/data/LLM_MAS_Memory_Survey_preprint_/LLM_MAS_Memory_Survey_preprint_.pdf) — hybrid private+shared conclusion
- [Collaborative Memory: multi-user memory sharing](https://arxiv.org/html/2505.18279v1)
- [Why Multi-Agent Systems Need Memory Engineering (MongoDB)](https://www.mongodb.com/company/blog/technical/why-multi-agent-systems-need-memory-engineering)
- [Claude Code project memory docs](https://code.claude.com/docs/en/memory) — plain markdown pattern
- [Learnings.md pattern](https://www.mindstudio.ai/blog/self-learning-claude-code-skill-learnings-md)

---
*Architecture research for: persistent-agent-team + parallel-sprint harness on ClawTeam*
*Researched: 2026-04-15*
