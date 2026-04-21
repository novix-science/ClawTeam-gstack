# Phase 04 Wave 0 — Plan Prep Notes

Evidence-backed resolutions for the five plan-prep verifications called out in
`04-RESEARCH.md` (A4 adjusted, A5 adjusted, A7 adjusted, A9 NEW, A11 NEW) plus
the glob-semantics and spawn-sync/async checks downstream plans depend on.

Written by: Phase 4 Wave 0 executor — Plan 04-01.

Consuming plans read the `Decisions Summary` table at the bottom verbatim;
each row names the downstream plan that must use the recorded decision.

---

## A-fnmatch: Glob engine selection

Empirical test — Python 3.14.4 (interpreter resolved in executor env; the
project targets `>=3.10`, so conclusions must hold on 3.10/3.11/3.12 as well
— `fnmatch` semantics are stable across those versions, and
`PurePosixPath.full_match` is Python 3.13+ only so it is NOT portable).

### Raw python3 output

```
== fnmatch.fnmatch (stdlib) ==
  'src/components/Button.tsx'                        vs 'src/components/**/*.tsx'      -> False
  'src/components/forms/Input.tsx'                   vs 'src/components/**/*.tsx'      -> True
  'src/auth/middleware.py'                           vs 'src/auth/**'                  -> True
  'src/auth/tokens/jwt.py'                           vs 'src/auth/**'                  -> True
  'app/api/users/route.ts'                           vs 'app/api/**'                   -> True
  'package.json'                                     vs 'package.json'                 -> True
  'lib/crypto/aes.py'                                vs '**/crypto/**'                 -> True
== PurePosixPath.match ==
  'src/components/Button.tsx'                        vs 'src/components/**/*.tsx'      -> False
  'src/components/forms/Input.tsx'                   vs 'src/components/**/*.tsx'      -> True
  'src/auth/middleware.py'                           vs 'src/auth/**'                  -> True
  'src/auth/tokens/jwt.py'                           vs 'src/auth/**'                  -> False
  'app/api/users/route.ts'                           vs 'app/api/**'                   -> False
  'package.json'                                     vs 'package.json'                 -> True
  'lib/crypto/aes.py'                                vs '**/crypto/**'                 -> True

== PurePosixPath.full_match (Python 3.13+ only — NOT portable) ==
  'src/components/Button.tsx'                        vs 'src/components/**/*.tsx'      -> True
  'src/components/forms/Input.tsx'                   vs 'src/components/**/*.tsx'      -> True
  'src/auth/middleware.py'                           vs 'src/auth/**'                  -> True
  'src/auth/tokens/jwt.py'                           vs 'src/auth/**'                  -> True
  'app/api/users/route.ts'                           vs 'app/api/**'                   -> True
  'package.json'                                     vs 'package.json'                 -> True
  'lib/crypto/aes.py'                                vs '**/crypto/**'                 -> True
```

### Findings

- `fnmatch.fnmatch`: fails test 1 (empty-middle `**` + required suffix). It maps
  `**` to `*` (a glob that does NOT cross `/`). When the pattern requires the
  `**` segment to span zero directories, it fails because `*` cannot match an
  empty string squished against a `/`.
- `PurePosixPath.match` (Python 3.10+ stable shape): fails tests 1, 4, 5. A
  trailing `**` in the pattern is interpreted as a single path segment, so it
  does not match multi-segment suffixes like `tokens/jwt.py` under
  `src/auth/**`.
- `PurePosixPath.full_match` (Python 3.13+): **passes all 7** with proper
  globstar semantics — but is NOT portable to the project's supported minimum
  (3.10).

### CHOSEN ENGINE: custom shim on top of `fnmatch`

Neither stdlib engine, at the portable baseline (Python 3.10+), covers the
required globstar semantics. Plan 06 MUST ship a shim.

**Import line (verbatim for Plan 06):**

```python
from fnmatch import fnmatch
```

**Matcher function (verbatim for Plan 06 — copy into
`clawteam/templates/gstack/review_router.py` OR wherever Plan 06 decides to
locate the router). Empirically verified against all 7 fixture cases + 4
additional edge cases (crypto-prefix, deep-nested crypto, bare `**` on
flat + nested paths) — all pass:**

```python
from fnmatch import fnmatch


def _match_path(path: str, pattern: str) -> bool:
    """Router-path matching with true globstar (``**``) semantics.

    ``**`` matches zero or more path segments (including slashes). Portable
    across Python 3.10-3.12 (``PurePosixPath.full_match`` is 3.13+ only, so
    we cannot rely on it). Uses ``fnmatch`` on simpler segments after
    splitting on ``/**/``; falls back to single-segment ``fnmatch`` when no
    globstar is present.

    Returns True iff ``path`` matches ``pattern`` as a full-path match.
    """
    # Bare '**' matches any path.
    if pattern == "**":
        return True
    # No globstar → single-segment fnmatch (handles '*' and '?' only).
    if "**" not in pattern:
        return fnmatch(path, pattern)

    # Leading '**/' means "match anywhere in the tree". Check BEFORE the
    # trailing-'/**' branch so patterns like '**/crypto/**' recurse on the
    # suffix 'crypto/**' correctly.
    if pattern.startswith("**/"):
        suffix_pat = pattern[3:]
        # '**/' also matches zero leading segments — try the bare suffix.
        if _match_path(path, suffix_pat):
            return True
        parts = path.split("/")
        for i in range(1, len(parts)):
            if _match_path("/".join(parts[i:]), suffix_pat):
                return True
        return False

    # Trailing '/**' — prefix must match, then zero-or-more trailing segments.
    if pattern.endswith("/**"):
        prefix_pat = pattern[:-3]
        # Recurse so prefix can itself contain '**'.
        if _match_path(path, prefix_pat):
            return True
        prefix_clean = prefix_pat.rstrip("/")
        return path.startswith(prefix_clean + "/")

    # General case: split on '/**/' — at least one segment must exist on
    # each side of every globstar. Recurse on the tail.
    head, _, tail = pattern.partition("/**/")
    path_parts = path.split("/")
    for split_idx in range(1, len(path_parts)):
        left = "/".join(path_parts[:split_idx])
        right = "/".join(path_parts[split_idx:])
        if fnmatch(left, head) and _match_path(right, tail):
            return True
    return False
```

**Decision rationale:**

- Portable to `requires-python = ">=3.10"` (current pyproject).
- Handles all 7 test cases covered by the planner's fixture.
- ~30 LOC — fits Plan 06's complexity budget.
- Zero new runtime deps (PROJECT.md invariant).
- Exposed as a module-level private function `_match_path(path, pattern)`; the
  router calls it per-rule in `ReviewConfig.route(changed_files)`.

**Plan 06 consumption contract:**

- Import: `from fnmatch import fnmatch` at module top.
- Helper location: top-level private function in the router module.
- Call site: `if _match_path(path, rule.pattern):` inside the router's per-file
  loop.
- Test plan MUST cover the 7 cases above as a parametrized pytest; regression
  gate: `src/components/Button.tsx` vs `src/components/**/*.tsx` → True (this is
  the case that defeats raw `fnmatch`).

---

## A4 _dispatch_review_phase

### Grep output

```
$ grep -n '_dispatch_.*_phase\|def dispatch_review\|_dispatch_review' \
    clawteam/sprint/conductor.py clawteam/sprint/*.py 2>/dev/null
(zero matches — confirmed empty)
```

No `_dispatch_review_phase`, no `_dispatch_ship_phase`, no `dispatch_review`
function of any shape exists in `clawteam/sprint/*.py`. `04-CONTEXT.md:220`'s
reference to `clawteam/sprint/conductor.py::_dispatch_ship_phase` is forward-
looking research language, not a current callsite.

Current conductor architecture: `SprintConductor.advance_phase(sprint_id,
actor)` runs the gate chain (EvidenceGate → forced_progress_gate → conditional
InteractionGate). There is NO per-phase dispatcher hook today — phase-specific
agent orchestration (reviewer spawns, router routing, cross-agent verify)
does not exist in this codebase.

### DECISION

Plan 10 creates a NEW file `clawteam/sprint/review_phase.py` containing a
module-level coroutine:

```python
async def dispatch_review_phase(
    state: SprintState,
    plugin_manager: PluginManager,
    bus: EventBus,
) -> ReviewPhaseResult: ...
```

`SprintConductor` gets a thin synchronous wrapper method
`_dispatch_review_phase(self, state)` that invokes
`asyncio.run(dispatch_review_phase(state, ...))` from the synchronous
`advance_phase` call path, preserving CORE-07 plain-JSON persistence (the
outer conductor stays sync; async lives only inside the dispatcher).

### Rationale

- Keeps `clawteam/sprint/conductor.py` under 700 LOC (currently 575).
- Review-phase orchestration (spawn 3 reviewers in parallel, collect verdicts,
  route per file, run cross-agent verify) is cohesive — belongs in its own
  module, not shoved into conductor.
- Wrapper method pattern keeps the conductor's public surface synchronous (no
  `async def advance_phase`); Phase 2's CORE-07 pause/resume semantics are
  preserved because `save_sprint_state` is a sync disk write that bookends the
  dispatch call.
- Plan 14 D-18 cleanup does NOT touch this file (no `DEFERRED` markers here).

### Plan 10 consumption contract

- New file: `clawteam/sprint/review_phase.py`
- New conductor method: `SprintConductor._dispatch_review_phase(self, state)`
- Call site in `advance_phase`: AFTER gate chain passes, BEFORE
  `save_sprint_state(state)`, only when `state.current_phase == "review"`.

---

## A5 TOML parser gap

### Grep output — currently parsed top-level `[template.*]` keys

```
$ grep -n "tmpl\.get\|raw\.get" clawteam/templates/__init__.py
104:    tmpl = raw.get("template", {})
107:    leader_data = tmpl.get("leader", {})
111:    agents = [AgentDef(**a) for a in tmpl.get("agents", [])]
114:    tasks = [TaskDef(**t) for t in tmpl.get("tasks", [])]
117:        name=tmpl.get("name", path.stem),
118:        description=tmpl.get("description", ""),
119:        command=tmpl.get("command", ["claude"]),
120:        backend=tmpl.get("backend", "tmux"),
126:        leader_role=tmpl.get("leader_role", ""),
127:        phases=tmpl.get("phases", []),
128:        model_profile=tmpl.get("model_profile", {}),
129:        memory=tmpl.get("memory", {}),
```

Currently parsed: `name`, `description`, `command`, `backend`, `leader`,
`agents`, `tasks`, `leader_role`, `phases`, `model_profile`, `memory`.

**CONFIRMED:** `[template.review]` is NOT parsed today. Unknown top-level
keys under `[template]` are silently dropped by `_parse_toml`. Plan 02 / Plan
06 MUST add `review_data = tmpl.get("review", {})` then parse nested review
rules.

### DECISION

Plan 06 (GstackReviewRouter) adds **in one atomic edit** to
`clawteam/templates/__init__.py`:

1. Two new pydantic models at module scope (after `TaskDef`):
   - `class ReviewRule(BaseModel)` — fields: `pattern: str`,
     `reviewers: list[str]`, and any rubric-anchored metadata Plan 06 needs.
   - `class ReviewConfig(BaseModel)` — fields: `rules: list[ReviewRule] = []`,
     `default_reviewers: list[str] = []`.
2. New field on `TemplateDef`: `review: ReviewConfig = ReviewConfig()`
   (Pattern 1 strict-additive — default empty preserves all 6 existing
   templates per the Phase 3 regression matrix).
3. Extension to `_parse_toml`:
   ```python
   review_data = tmpl.get("review", {})
   review = ReviewConfig(
       rules=[ReviewRule(**r) for r in review_data.get("rules", [])],
       default_reviewers=review_data.get("default_reviewers", []),
   )
   ```
   then pass `review=review` to `TemplateDef(...)`.

### Rationale

- One atomic edit: both schema + parser land together (Phase 3 Pattern 1
  convention). Downstream Plan 06 tests can then author a gstack.toml with
  `[template.review]` and exercise the router without a separate schema PR.
- `_parse_toml` already uses `.get(key, default)` for every top-level field, so
  the new `review` key extension follows the established pattern exactly.

### Plan 06 consumption contract

- File to edit: `clawteam/templates/__init__.py` (add 2 models + 1 field + 1
  parse block — ~25 LOC delta).
- Rubric fields in `ReviewRule` are Plan 06's choice; `pattern` + `reviewers`
  are the MINIMUM (§04-RESEARCH D-15 implied schema).

---

## A6 D-18 marker baseline

### Grep output

```
$ grep -n "INTERACTIVE-RUNTIME-DEFERRED\|SHA-PIN-DEFERRED" \
    clawteam/templates/gstack/prompts/*.md
clawteam/templates/gstack/prompts/designer.md:17:INTERACTIVE-RUNTIME-DEFERRED: /design-consultation per-dimension dialogue
clawteam/templates/gstack/prompts/pm.md:18:INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 multi-turn
clawteam/templates/gstack/prompts/reviewer.md:40:INTERACTIVE-RUNTIME-DEFERRED: /investigate per-hypothesis state machine
clawteam/templates/gstack/prompts/reviewer.md:45:## SHA-PIN-DEFERRED
clawteam/templates/gstack/prompts/reviewer.md:47:SHA-PIN-DEFERRED: At review start, record HEAD SHA in your turn context.
```

**Count: 5 grep hits** across 3 files (pm.md, designer.md, reviewer.md).

- `pm.md:18` — `INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 multi-turn`
- `designer.md:17` — `INTERACTIVE-RUNTIME-DEFERRED: /design-consultation per-dimension dialogue`
- `reviewer.md:40` — `INTERACTIVE-RUNTIME-DEFERRED: /investigate per-hypothesis state machine`
- `reviewer.md:45` — `## SHA-PIN-DEFERRED` (H2 HEADING)
- `reviewer.md:47` — `SHA-PIN-DEFERRED: At review start, record HEAD SHA in your turn context.`

### DECISION

- Research said "4 lines"; the grep-greppable count is **5** because the H2
  heading `## SHA-PIN-DEFERRED` at `reviewer.md:45` matches the same grep
  regex as the narrative paragraphs.
- **D-18 cleanup target: grep count = 0.** Plan 14 removes ALL 5 markers,
  including the `## SHA-PIN-DEFERRED` H2 heading at `reviewer.md:45`.
- Plan 14's regression assertion: `grep -c
  "INTERACTIVE-RUNTIME-DEFERRED\|SHA-PIN-DEFERRED"
  clawteam/templates/gstack/prompts/*.md | awk -F: '{s+=$2} END{exit s}'`
  — expected total 0 after cleanup.

### Plan 14 consumption contract

- Target files + baseline line numbers (for pre-edit regression grep):
  - `clawteam/templates/gstack/prompts/pm.md:18`
  - `clawteam/templates/gstack/prompts/designer.md:17`
  - `clawteam/templates/gstack/prompts/reviewer.md:40`
  - `clawteam/templates/gstack/prompts/reviewer.md:45` (H2 header — also
    remove the empty paragraph around it to keep markdown well-formed)
  - `clawteam/templates/gstack/prompts/reviewer.md:47`
- Post-cleanup invariant: `grep -c "DEFERRED" clawteam/templates/gstack/prompts/*.md`
  over the two marker strings returns 0 across all files.
- Plan 14 SHOULD also replace the removed stub text with the Phase-4-delivered
  runtime behavior reference (e.g., "See `/office-hours` multi-turn state
  machine at `clawteam/sprint/review_phase.py`").

---

## A7 EventBus emit signature

### Grep output

```
$ grep -n "def emit\|HarnessEvent\|@dataclass" \
    clawteam/events/bus.py clawteam/events/types.py | head -20
clawteam/events/bus.py:9:from clawteam.events.types import HarnessEvent
clawteam/events/bus.py:13:_EVENT_TYPE_REGISTRY: dict[str, type[HarnessEvent]] = {}
clawteam/events/bus.py:16:def register_event_type(cls: type[HarnessEvent]) -> None:
clawteam/events/bus.py:21:def resolve_event_type(name: str) -> type[HarnessEvent] | None:
clawteam/events/bus.py:27:    cls is not None and isinstance(cls, type) and issubclass(cls, HarnessEvent):
clawteam/events/bus.py:31:Handler = Callable[[HarnessEvent], Any]
clawteam/events/bus.py:58:    event_type: type[HarnessEvent],
clawteam/events/bus.py:73:    event_type: type[HarnessEvent],
clawteam/events/bus.py:86:    def emit(self, event: HarnessEvent) -> list[Any]:
clawteam/events/bus.py:103:    def emit_async(self, event: HarnessEvent) -> None:
clawteam/events/bus.py:111:    def handler_count(self, event_type: type[HarnessEvent] | None = None) -> int:
clawteam/events/types.py:5:from dataclasses import dataclass, field
clawteam/events/types.py:13:@dataclass
clawteam/events/types.py:14:class HarnessEvent:
clawteam/events/types.py:24:@dataclass
clawteam/events/types.py:25:class BeforeWorkerSpawn(HarnessEvent):
clawteam/events/types.py:34:@dataclass
clawteam/events/types.py:35:class BeforeInboxSend(HarnessEvent):
```

**CONFIRMED:** `emit(self, event: HarnessEvent) -> list[Any]` — takes typed
dataclass event instances, NOT `(name, payload)` tuples. Dispatch uses
`type(event)` as the subscriber lookup key (bus.py:93). Existing event types
are all `@dataclass class FooEvent(HarnessEvent)` with typed fields and
defaults.

### DECISION

Plan 02 adds two new dataclasses at the tail of `clawteam/events/types.py`:

```python
@dataclass
class MidReviewThrash(HarnessEvent):
    """SmartReviewRouter detected mid-review SHA movement (§04-RESEARCH D-17)."""

    sprint_id: str = ""
    reviewer_agent: str = ""
    pinned_sha: str = ""
    observed_sha: str = ""
    file_path: str = ""


@dataclass
class SycophancyCascadeDetected(HarnessEvent):
    """Cross-agent verification detected unanimous positive bias (§04-RESEARCH D-18)."""

    sprint_id: str = ""
    reviewers: list[str] = field(default_factory=list)
    verdict_hashes: list[str] = field(default_factory=list)
    similarity_score: float = 0.0
```

Emission sites call:

```python
bus.emit(MidReviewThrash(
    team_name=state.team,
    sprint_id=state.sprint_id,
    reviewer_agent="reviewer-a",
    pinned_sha="abc1234",
    observed_sha="def5678",
    file_path="src/auth/jwt.py",
))
```

### Rationale

- Matches the existing `@dataclass + HarnessEvent` shape exactly (A7 rejected:
  no `(name, payload)` tuple form exists).
- All fields have defaults so callers can use kwargs-only construction (mirrors
  `PhaseTransition`, `BeforeFileWrite`, etc.).
- Subscribers registered via `bus.subscribe(MidReviewThrash, handler)` because
  dispatch keys on `type(event)`.

### Plan 02 consumption contract

- File to edit: `clawteam/events/types.py` (append 2 new dataclasses).
- Import sites: `from clawteam.events.types import MidReviewThrash,
  SycophancyCascadeDetected`.
- Subscriber registration: wherever Plan 02 / Plan 10 wires theater-drift
  subscribers (candidate: `clawteam/harness/theater_drift.py` or similar).

---

## A9 HumanApprovalGate name collision

### Grep output (filtered to clawteam/ + tests/ — docs excluded)

```
$ grep -rn 'HumanApprovalGate\|from clawteam.harness.phases import.*HumanApprovalGate\|phases\.HumanApprovalGate' \
    clawteam/ tests/ 2>/dev/null
clawteam/harness/orchestrator.py:14:    HumanApprovalGate,
clawteam/harness/orchestrator.py:105:    self.runner.register_gate(phase, HumanApprovalGate(phase))
clawteam/harness/phases.py:91:class HumanApprovalGate(PhaseGate):
clawteam/harness/__init__.py:12:    HumanApprovalGate,
clawteam/harness/__init__.py:29:    "ArtifactRequiredGate", "AllTasksCompleteGate", "HumanApprovalGate",
tests/test_harness.py:12:    HumanApprovalGate,
tests/test_harness.py:75:    runner.register_gate(DISCUSS, HumanApprovalGate("discuss"))
```

**Existing `HumanApprovalGate(PhaseGate)` at `clawteam/harness/phases.py:91`:**

```python
class HumanApprovalGate(PhaseGate):
    """Requires explicit human approval before advancing.

    Approval is stored as an artifact: approval-{phase_name}.json
    """

    def __init__(self, phase_name: str):
        self._artifact_name = f"approval-{phase_name}.json"

    def check(self, state: PhaseState) -> tuple[bool, str]:
        if self._artifact_name not in state.artifacts:
            return False, f"Human approval required: clawteam harness approve {state.team_name}"
        return True, ""
```

Consumers:
- `clawteam/harness/phases.py:91` — definition site.
- `clawteam/harness/__init__.py:12` — re-export.
- `clawteam/harness/__init__.py:29` — `__all__` listing.
- `clawteam/harness/orchestrator.py:14` + `:105` — registers the existing gate
  against Phase 1 generic harness phases.
- `tests/test_harness.py:12` + `:75` — existing test coverage.

### DECISION

Phase 4's new class is **named `ShipApprovalGate(InteractionGate)`** and lives
at **`clawteam/harness/ship_approval_gate.py`** (NEW file). The existing
`HumanApprovalGate(PhaseGate)` at `phases.py:91` is **left untouched**.

### Rationale

- **Zero BC risk:** no rename means all 5 existing callsites
  (orchestrator.py:14/105, __init__.py:12/29, test_harness.py:12/75) keep
  working unchanged; Phase 2 D-18 regression stays green.
- **Grep clarity:** `grep -rn 'ShipApprovalGate' clawteam/` surfaces ONLY
  Phase 4 touchpoints, no false positives from the old gate.
- **Semantic fit:** new gate overrides `auto_advance` + requires signed
  `ship-approval.md` artifact (D-13 contract) — semantically distinct from the
  existing "approval-{phase}.json present" check.
- Plan 04's `<must_haves>` already codify the name (`ShipApprovalGate` +
  file path `clawteam/harness/ship_approval_gate.py`).

### Plan 04 consumption contract

- New file: `clawteam/harness/ship_approval_gate.py` (NEW; ~80 LOC).
- New class: `class ShipApprovalGate(InteractionGate)` — subclasses the
  Phase 2 `InteractionGate`, NOT the legacy `HumanApprovalGate(PhaseGate)`.
- New test file: `tests/test_ship_approval_gate.py`.
- No edits to `clawteam/harness/phases.py`, `clawteam/harness/__init__.py`,
  `clawteam/harness/orchestrator.py`, or `tests/test_harness.py`.
- Post-edit regression: `grep -c "class HumanApprovalGate"
  clawteam/harness/phases.py` returns exactly 1 (unchanged).

---

## A11 force_interactive_phases plumbing

### Grep output (conductor + harness modules only)

```
$ grep -n 'force_interactive_phases' clawteam/sprint/conductor.py clawteam/harness/*.py 2>/dev/null
clawteam/sprint/conductor.py:19:- force_interactive_phases=["ship"] (Phase 4 reserved) → always insert
clawteam/sprint/conductor.py:222:            force_interactive_phases=["ship"],  # Phase 4 reservation
clawteam/sprint/conductor.py:239:        force_interactive_phases: list[str] | None = None,
clawteam/sprint/conductor.py:247:        self.force_interactive_phases: list[str] = list(
clawteam/sprint/conductor.py:248:            force_interactive_phases or []
clawteam/sprint/conductor.py:520:        InteractionGate insertion logic per §02-CONTEXT D-23 + force_interactive_phases:
clawteam/sprint/conductor.py:522:        - force_interactive_phases includes the current phase → always insert.
clawteam/sprint/conductor.py:544:        forced = state.current_phase in self.force_interactive_phases
```

**Confirmed lines:** 19 (docstring), 222 (docstring example), 239 (ctor
param), 247-248 (ctor assignment), 520/522 (_build_gate_chain docstring),
544 (runtime check that inserts InteractionGate unconditionally for the
listed phase). `clawteam/harness/*.py` contains ZERO references —
`force_interactive_phases` is a conductor-only concept, as expected.

Planner-expected lines 222/239/247/544 — all four present (239 replaces the
planner's expected 247 because the PLAN was written against earlier source;
the ctor-param line migrated by one line during a Phase 2 doc revision).

### DECISION

`ShipApprovalGate` does NOT modify `_build_gate_chain`. It plugs into the
gate list at `phase=ship` via `GstackSprintPlugin.contribute_gates` (existing
hook at `clawteam/harness/plugin/base.py`). `_build_gate_chain` already
inserts `InteractionGate` when `state.current_phase in
self.force_interactive_phases` (line 544), and `ShipApprovalGate` is an
`InteractionGate` subclass — so the Plan 04 subclass + Plan 11 plugin
registration is sufficient to wire it up. NO conductor edits required for
A11.

### Rationale

- Phase 2 reserved the hook precisely so Phase 4 lands without touching
  `SprintConductor`. Conductor stability is a Phase 2 invariant (see
  02-CONTEXT D-22).
- `GstackSprintPlugin.contribute_gates` already attaches other Phase 3 gates
  (per Phase 3 Plan 03-07 SUMMARY) — Phase 4 adds one more gate in the same
  list for phase="ship".

### Plan 04 + Plan 11 consumption contract

- Plan 04 ships `ShipApprovalGate(InteractionGate)` as a gate class only.
  It does NOT register itself.
- Plan 11 registers the gate via the plugin's `contribute_gates` hook,
  passing `"ship"` as the phase key. The plugin instantiation step adds
  `"ship"` to `SprintConductor.force_interactive_phases` (already done at
  conductor.py:222 for all gstack sprints).

---

## A-spawn asyncio bridge

### Grep output

```
$ ls clawteam/harness/ | grep -i spawn
spawner.py

$ grep -rn "class.*Spawn\|def spawn_agent\|async def spawn\|def spawn\b" \
    clawteam/harness/ clawteam/spawn/ clawteam/team/ clawteam/cli/commands.py 2>/dev/null
clawteam/harness/spawner.py:13:class PhaseRoleSpawner(SpawnStrategy):
clawteam/harness/strategies.py:9:class SpawnStrategy(ABC):
clawteam/spawn/base.py:8:class SpawnBackend(ABC):
clawteam/spawn/base.py:12:    def spawn(
clawteam/spawn/subprocess_backend.py:16:class SubprocessBackend(SpawnBackend):
clawteam/spawn/subprocess_backend.py:23:    def spawn(
clawteam/spawn/tmux_backend.py:34:class TmuxBackend(SpawnBackend):
clawteam/spawn/tmux_backend.py:45:    def spawn(
clawteam/spawn/wsh_backend.py:204:class WshBackend(SpawnBackend):
clawteam/spawn/wsh_backend.py:217:    def spawn(
clawteam/cli/commands.py:3390:def spawn_agent(
```

**Spawn API shape (from `clawteam/spawn/base.py:12`):**

```python
class SpawnBackend(ABC):
    @abstractmethod
    def spawn(
        self,
        command: list[str],
        agent_name: str,
        agent_id: str,
        agent_type: str,
        team_name: str,
        prompt: str | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        skip_permissions: bool = False,
        system_prompt: str | None = None,
        is_leader: bool = False,
        keepalive: bool = False,
    ) -> str:  # ← returns str (status message), fully synchronous
        ...
```

All three concrete backends (`SubprocessBackend`, `TmuxBackend`,
`WshBackend`) implement `def spawn(...) -> str` — **NOT** `async def
spawn(...)`. The spawn call path is synchronous: it blocks the caller until
the tmux/subprocess launch returns a status string.

The per-phase orchestrator (`PhaseRoleSpawner.spawn_for_phase` at
`clawteam/harness/spawner.py:20`) is also a regular `def`; it calls
`backend.spawn(...)` in a `for i in range(count)` loop.

### DECISION

Plan 10's `dispatch_review_phase` coroutine spawns reviewers in parallel via
`asyncio.gather` + `loop.run_in_executor(None, _spawn_reviewer_sync, ...)`:

```python
import asyncio
from clawteam.spawn import get_backend

async def dispatch_review_phase(state, plugin_manager, bus):
    loop = asyncio.get_running_loop()
    backend = get_backend(...)

    def _spawn_reviewer_sync(role: str, review_sha: str) -> str:
        # Wraps the synchronous backend.spawn + prompt build. Returns the
        # spawned reviewer's agent_name (or "" on failure).
        ...

    reviewer_roles = ["reviewer-a", "reviewer-b", "reviewer-c"]
    spawn_tasks = [
        loop.run_in_executor(None, _spawn_reviewer_sync, role, state.review_sha)
        for role in reviewer_roles
    ]
    reviewer_names = await asyncio.gather(*spawn_tasks)
    ...
```

### Rationale

- `backend.spawn(...)` is sync; blocking `asyncio.gather` on sync calls
  without an executor would serialize them (no parallelism).
- `loop.run_in_executor(None, ...)` uses the default thread pool — identical
  pattern used by `EventBus.emit_async` (`bus.py:103-107`), so the project
  already tolerates this concurrency shape.
- Keeps Plan 10 localized: no `async def spawn` refactor of the SpawnBackend
  ABC (which would be a Rule-4 architectural change affecting every
  backend).
- A3 research assumption ("spawn registry is coroutine-safe") is evidence-
  backed: the backends are all synchronous blocking calls over a subprocess
  or tmux shell — they hold no shared mutable state between spawns, so
  thread-pool concurrency is safe by construction. TeamManager.add_member is
  called from inside `PhaseRoleSpawner.spawn_for_phase` which itself mutates
  team state via `file_locked` (Phase 3 Plan 03-07 D-13) — the locking is
  thread-safe.

### Plan 10 consumption contract

- Function to wrap: `SpawnBackend.spawn(...)` (or
  `PhaseRoleSpawner.spawn_for_phase(...)` for role-aware spawning — Plan 10
  chooses).
- Bridge pattern: `loop.run_in_executor(None, _spawn_reviewer_sync, args...)`
  where `_spawn_reviewer_sync` is a top-level helper in
  `clawteam/sprint/review_phase.py` that performs the full sync spawn
  (TeamManager.add_member + backend.spawn + prompt build).
- Gather: `await asyncio.gather(*spawn_tasks)` to run all 3 reviewer spawns
  in parallel.

---

## Decisions Summary (consumed by downstream plans)

| Item | Decision | Consuming Plan |
|------|----------|----------------|
| Glob engine | `custom shim _match_path()` on top of stdlib `fnmatch` (portable to Python 3.10+; globstar via `/**/ ` split-and-recurse; full source in A-fnmatch section) | Plan 06 |
| Review-phase dispatch | NEW file `clawteam/sprint/review_phase.py` with `async def dispatch_review_phase(state, plugin_manager, bus)`; `SprintConductor._dispatch_review_phase(self, state)` thin sync wrapper invokes `asyncio.run(...)` | Plan 10 |
| Ship gate class name | `ShipApprovalGate(InteractionGate)` at `clawteam/harness/ship_approval_gate.py` — existing `HumanApprovalGate(PhaseGate)` at `phases.py:91` left untouched | Plan 04 |
| TOML parser edit | Plan 06 extends `_parse_toml` in `clawteam/templates/__init__.py` + adds `ReviewRule(BaseModel)` and `ReviewConfig(BaseModel)` + `TemplateDef.review: ReviewConfig = ReviewConfig()` in ONE atomic commit | Plan 06 |
| Event type shape | `@dataclass class MidReviewThrash(HarnessEvent)` + `@dataclass class SycophancyCascadeDetected(HarnessEvent)` appended to `clawteam/events/types.py`; emitted via `bus.emit(MidReviewThrash(...))` (typed dataclass, NOT name+payload) | Plan 02 |
| Spawn-asyncio bridge | `loop.run_in_executor(None, _spawn_reviewer_sync, role, review_sha)` around synchronous `SpawnBackend.spawn(...)` (all 3 backends — tmux/subprocess/wsh — are sync `def spawn() -> str`) | Plan 10 |
| D-18 baseline | 5 grep hits across pm/designer/reviewer prompts at `pm.md:18`, `designer.md:17`, `reviewer.md:40`, `reviewer.md:45` (H2 header), `reviewer.md:47` — Plan 14 target: 0 hits | Plan 14 |

---

## Surprises / plan-set revisions flagged

1. **Planner expected 4 D-18 marker lines; actual is 5** — the `## SHA-PIN-DEFERRED` H2 heading at `reviewer.md:45` was omitted from the research baseline. Plan 14 acceptance criteria amended to `grep count = 0` (not `≤ 1`).
2. **A11 line-number drift** — planner expected `force_interactive_phases` at conductor.py lines `222, 247, 544`. Actual: 19, 222, 239, 247-248, 520, 522, 544 (ctor-param line migrated from 247 → 239 during a Phase 2 docstring revision). All four structurally important lines still present; no plan-set change needed.
3. **Python version constraint forces shim path over `PurePosixPath.full_match`** — project's `requires-python = ">=3.10"` rules out the Python 3.13+ `full_match` API. The shim adds ~30 LOC to Plan 06 that would otherwise have been a 1-line stdlib call. No runtime behavior change, but Plan 06's test coverage must include the 7 fixture cases listed in A-fnmatch to lock globstar semantics.
4. **No existing `_dispatch_*_phase` method pattern** — A4 confirms the conductor has ZERO phase-specific dispatcher hooks today. Plan 10 is NOT extending a pattern; it is ESTABLISHING one. This may inform plan-set revision if other phases (e.g., ship, test) need similar dispatch hooks — Plan 10 should document the shape as a reusable seam.

---

*Generated 2026-04-21 by Plan 04-01 Wave 0 executor. Any downstream plan that grep-misses a decision in this file should re-run the relevant verification here rather than guess.*
