---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - pyproject.toml
  - clawteam/attention/__init__.py
  - clawteam/cost/__init__.py
  - clawteam/rate_limit/__init__.py
  - clawteam/events/types.py
  - clawteam/sprint/state.py
  - clawteam/templates/__init__.py
  - tests/test_pyproject_optional_extras.py
  - tests/events/test_phase7_events.py
  - tests/templates/test_template_def_phase7_blocks.py
  - tests/sprint/test_sprint_state_queue_status.py
autonomous: true
requirements:
  - CORE-06
  - INT-05
  - QUALITY-04
  - QUALITY-12
tags:
  - substrate
  - pyproject-extra
  - event-registration
  - template-config
  - sprint-state-extension

must_haves:
  truths:
    - "pyproject.toml declares a new optional-extra 'attend = [\"watchdog>=3,<4\"]' and existing dev/p2p/browser extras are unchanged"
    - "Three new top-level packages exist with __init__.py: clawteam/attention, clawteam/cost, clawteam/rate_limit"
    - "Six new HarnessEvent dataclasses are registered via register_event_type: ToolCallCompleted, ClaudeApiResponse, BudgetAlarmReached, RateLimitSaturated, ZombieWorktreeGced, DormancyTransition"
    - "SprintState has a new queue_status: str field (default='') that round-trips via load/save without breaking existing state.json files"
    - "TemplateDef accepts [conductor], [attention], [cost] top-level TOML sub-blocks; all default to None so existing templates parse unchanged"
  artifacts:
    - path: clawteam/attention/__init__.py
      provides: "attention substrate package marker"
      contains: "__all__"
    - path: clawteam/cost/__init__.py
      provides: "cost substrate package marker"
      contains: "__all__"
    - path: clawteam/rate_limit/__init__.py
      provides: "rate_limit substrate package marker"
      contains: "__all__"
    - path: clawteam/events/types.py
      provides: "6 new event dataclasses registered"
      contains: "class ToolCallCompleted|class ClaudeApiResponse|class BudgetAlarmReached|class RateLimitSaturated|class ZombieWorktreeGced|class DormancyTransition"
    - path: clawteam/sprint/state.py
      provides: "queue_status additive field"
      contains: "queue_status"
    - path: clawteam/templates/__init__.py
      provides: "ConductorConfig + AttentionConfig + CostConfig pydantic sub-blocks"
      contains: "class ConductorConfig|class AttentionConfig|class CostConfig"
  key_links:
    - from: pyproject.toml
      to: clawteam/attention/watcher.py
      via: "attend extra pulls watchdog; watcher.py uses find_spec"
      pattern: "attend = |watchdog>="
    - from: clawteam/events/types.py
      to: clawteam/events/bus.py
      via: "register_event_type for 6 new events at module bottom"
      pattern: "register_event_type\\(ToolCallCompleted|register_event_type\\(BudgetAlarmReached"
    - from: clawteam/sprint/state.py
      to: clawteam/sprint/conductor.py
      via: "queue_status consumed by Plan 07-02 SprintConductor capacity gate"
      pattern: "queue_status"
---

<objective>
Wave 0 substrate — pyproject extra + 3 new top-level packages + 6 new events + SprintState.queue_status + TemplateDef sub-blocks. Zero business logic; pure substrate so Waves 1-5 build on a firm foundation. Covers plan-prep items A2, A4, A6 from CONTEXT.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md

<interfaces>
From clawteam/events/types.py (bottom — model Phase 6 Plan 06-01 Task 2 append at lines 371-433):
```python
# Late import block:
from clawteam.events.bus import register_event_type  # noqa: E402

register_event_type(DeployRegressionDetected)
register_event_type(WebVitalRegressionDetected)
register_event_type(MemoryWritePersisted)
register_event_type(ConflictDetected)
register_event_type(MemoryBackfillComplete)
```

From clawteam/templates/__init__.py (Phase 6 Plan 06-01 Task 3 precedent for optional sub-blocks):
```python
memory_raw = raw.get("memory")
design_shotgun_raw = raw.get("design_shotgun")
browser_raw = raw.get("browser")
return TemplateDef(
    ...,
    memory=MemoryConfig(**memory_raw) if memory_raw is not None else None,
    ...
)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: pyproject.toml [attend] extra + 3 new package skeletons</name>
  <files>
    pyproject.toml,
    clawteam/attention/__init__.py,
    clawteam/cost/__init__.py,
    clawteam/rate_limit/__init__.py,
    tests/test_pyproject_optional_extras.py
  </files>
  <read_first>
    pyproject.toml (current [project.optional-dependencies] at lines 30-52),
    clawteam/browser/__init__.py (Phase 6 precedent for find_spec pattern)
  </read_first>
  <behavior>
    - Test (test_pyproject_optional_extras.py): extend existing test file; add `test_attend_extra_present` asserting `raw["project"]["optional-dependencies"]["attend"] == ["watchdog>=3,<4"]`.
    - Test: `test_existing_extras_unchanged_phase7` — dev/p2p/browser extras still present with SAME contents.
    - Test: `test_three_new_packages_importable` — `import clawteam.attention; import clawteam.cost; import clawteam.rate_limit` all succeed.
  </behavior>
  <action>
**1. `pyproject.toml` — APPEND after `browser = [...]` block (line 52):**

```toml
# Phase 7 Wave 0 (D-06): optional watchdog for AttentionQueue FS auto-refresh.
# Without watchdog, clawteam attend falls back to 2-second polling.
attend = [
    "watchdog>=3,<4",
]
```

Do NOT modify `dev`, `p2p`, or `browser` blocks.

**2. `clawteam/attention/__init__.py` (NEW FILE, ~15 LOC):**

```python
"""Attention substrate — cross-sprint AttentionQueue + watcher + digest.

Phase 7 Wave 0: package marker only. Public API (AttentionQueue,
AttentionItem, watchdog_available, build_digest) is added by Plans
07-03 and 07-04.

Lives at top level (not under templates/gstack/) because the substrate
is generic — a non-gstack template could read its own question/answer
artifact layout.
"""
from __future__ import annotations

__all__: list[str] = []
```

**3. `clawteam/cost/__init__.py` (NEW FILE, ~15 LOC):**

```python
"""Cost substrate — tracker + dashboard + fallback + cache_tracker.

Phase 7 Wave 0: package marker only. Public API lands in Plans 07-05,
07-06, 07-07.
"""
from __future__ import annotations

__all__: list[str] = []
```

**4. `clawteam/rate_limit/__init__.py` (NEW FILE, ~15 LOC):**

```python
"""Rate-limit substrate — 429-bucket monitor consulted by SprintConductor.

Phase 7 Wave 0: package marker only. RateLimitMonitor lands in Plan 07-02.
"""
from __future__ import annotations

__all__: list[str] = []
```

**5. Tests:** Extend `tests/test_pyproject_optional_extras.py` (already exists from Phase 6); APPEND the 3 test functions. Use `tomllib`/`tomli` fallback pattern already in the file.
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/test_pyproject_optional_extras.py -x -q && python -c "import clawteam.attention, clawteam.cost, clawteam.rate_limit; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q 'attend = \[' pyproject.toml` succeeds.
    - `grep -q 'watchdog>=3,<4' pyproject.toml` succeeds.
    - `ls clawteam/attention/__init__.py clawteam/cost/__init__.py clawteam/rate_limit/__init__.py` succeeds.
    - `pytest tests/test_pyproject_optional_extras.py -q` reports all green.
  </acceptance_criteria>
  <done>Three new packages importable; attend extra declared; Waves 1-5 can build on top.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Six new HarnessEvent dataclasses + register_event_type</name>
  <files>
    clawteam/events/types.py,
    tests/events/test_phase7_events.py
  </files>
  <read_first>
    clawteam/events/types.py (Phase 6 append at lines 371-434 — IDENTICAL shape),
    tests/events/test_phase6_events.py (test shape to mirror),
    .planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md (§Code Example 7)
  </read_first>
  <behavior>
    - Test 1-6: each of 6 events is an instance of HarnessEvent; constructs with only team_name kwarg (all other fields have defaults).
    - Test 7-12: emit round-trip via EventBus — subscribe, emit with realistic payload, assert handler received event with populated fields.
    - Test 13: `test_all_six_registered` — after `import clawteam.events.types`, `resolve_event_type("ToolCallCompleted")` returns the class (non-None) for all 6 event names.
    - Test 14: `test_phase6_events_still_registered` — MemoryWritePersisted/ConflictDetected/MemoryBackfillComplete STILL resolvable (no regression).
  </behavior>
  <action>
**1. `clawteam/events/types.py` — APPEND 6 dataclasses BEFORE the `from clawteam.events.bus import register_event_type` late-import block at the bottom:**

```python
# ── Phase 7 Wave 0 / Plan 07-01: concurrency + cost + rate-limit events ─────


@dataclass
class ToolCallCompleted(HarnessEvent):
    """D-09: agent invoked a tool and it finished. Drives cost tracker rollup.

    Emitted by clawteam.spawn.invoke.invoke_native_cli AFTER subprocess.run
    returns. tokens_input/output are 0 when the wrapped CLI does not emit a
    parseable token count (e.g. gh, lighthouse); cost_usd is computed from
    the per-model pricing table in clawteam/cost/pricing.py (Plan 07-05).
    """

    agent: str = ""
    tool_name: str = ""
    sprint_id: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    model: str = ""
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    model_fallback_applied: bool = False


@dataclass
class ClaudeApiResponse(HarnessEvent):
    """D-12: Claude API response metadata for cache-hit-rate tracking."""

    agent: str = ""
    model: str = ""
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class BudgetAlarmReached(HarnessEvent):
    """D-10: current_spend / budget_usd crossed a configured threshold.

    Advisory — tracker (Plan 07-05) applies model fallback policy on
    crossing fallback_at_percent; clawteam team show surfaces the alarm
    as a colored banner per threshold.
    """

    percent: float = 0.0
    spent_usd: float = 0.0
    budget_usd: float = 0.0


@dataclass
class RateLimitSaturated(HarnessEvent):
    """D-13: 429 window exceeded threshold; new sprints get queue_status.

    Emitted by RateLimitMonitor (Plan 07-02) when recent_429_count > 3/min
    (default). SprintConductor consults is_saturated() before acquiring the
    concurrent-sprint semaphore.
    """

    recent_429_count: int = 0
    threshold: int = 3
    window_seconds: int = 60


@dataclass
class ZombieWorktreeGced(HarnessEvent):
    """ROADMAP §Phase 7 SC #10: dead worktree cleaned up by clawteam doctor --gc."""

    path: str = ""
    age_days: int = 0
    freed_bytes: int = 0


@dataclass
class DormancyTransition(HarnessEvent):
    """QUALITY-04: agent transitioned between active and dormant slots."""

    agent: str = ""
    role: str = ""
    from_state: str = ""  # "dormant" | "active"
    to_state: str = ""
```

Then at the bottom, APPEND 6 new register_event_type calls AFTER the existing Phase 6 block:

```python
# Phase 7 Wave 0 / Plan 07-01
register_event_type(ToolCallCompleted)
register_event_type(ClaudeApiResponse)
register_event_type(BudgetAlarmReached)
register_event_type(RateLimitSaturated)
register_event_type(ZombieWorktreeGced)
register_event_type(DormancyTransition)
```

**2. `tests/events/test_phase7_events.py` (NEW, ~120 LOC):** Mirror `tests/events/test_phase6_events.py` exact structure. Use `EventBus()` local instance per test so tests don't pollute global state. For test 13/14 use `from clawteam.events.bus import resolve_event_type; assert resolve_event_type("ToolCallCompleted") is not None`.
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/events/test_phase7_events.py tests/events/ -x -q && python -c "from clawteam.events.types import ToolCallCompleted, ClaudeApiResponse, BudgetAlarmReached, RateLimitSaturated, ZombieWorktreeGced, DormancyTransition; print('ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^class " clawteam/events/types.py` shows 6 more classes than before.
    - `grep -q "register_event_type(ToolCallCompleted)" clawteam/events/types.py` succeeds.
    - `grep -q "register_event_type(BudgetAlarmReached)" clawteam/events/types.py` succeeds.
    - `pytest tests/events/test_phase7_events.py -q` reports 14 passed.
    - BC: `pytest tests/events/ -q` still green.
  </acceptance_criteria>
  <done>6 events registered; Plans 07-02/05/06/09 can import these types and wire tracking.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: SprintState.queue_status additive field</name>
  <files>
    clawteam/sprint/state.py,
    tests/sprint/test_sprint_state_queue_status.py
  </files>
  <read_first>
    clawteam/sprint/state.py (existing fields lines 42-122 — especially review_sha at 113-121 for the additive-field precedent pattern)
  </read_first>
  <behavior>
    - Test 1: `test_default_empty` — SprintState(goal=..., team=..., current_phase=...).queue_status == "".
    - Test 2: `test_setter_accepts_values` — state.queue_status = "queued_capacity"; save; load; round-trip preserves.
    - Test 3: `test_legacy_state_json_loads` — write a state.json WITHOUT queue_status key; load via SprintState.load; assert queue_status == "" (default applied). Tests additive-field BC.
    - Test 4: `test_save_round_trip_preserves_all_phase2_fields` — assert turn_counters, artifact_cap_bytes, status, careful_enabled, review_sha still load correctly alongside new field.
  </behavior>
  <action>
**1. `clawteam/sprint/state.py` — INSERT `queue_status` field after `review_sha` (after line 121):**

```python
    # ── Phase 7 Wave 0 (§07-CONTEXT D-01) additive field ────────────
    queue_status: str = Field(
        default="",
        description=(
            "Phase 7 D-01: reason the sprint is in a queued state. Empty "
            "string '' = active / running (normal case). Non-empty values: "
            "'queued_capacity' (acquire on max_concurrent_sprints semaphore "
            "timed out after 60s — sprint waits for capacity), "
            "'rate_limit_saturated' (RateLimitMonitor.is_saturated() true at "
            "start_sprint — sprint waits for 429 window to clear). Cleared "
            "back to '' when conductor promotes sprint to active. Persisted "
            "so crash-recovery sees the queued sprint on resume."
        ),
    )
```

Use an open `str` type (not Literal) to keep the field extensible — future queue reasons (e.g., 'queued_disk_budget') don't require schema migration.

**2. `tests/sprint/test_sprint_state_queue_status.py` (NEW, ~90 LOC):**

```python
"""Phase 7 Wave 0 (Plan 07-01 Task 3): SprintState.queue_status additive field."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from clawteam.sprint.state import SprintState, load_sprint_state, save_sprint_state


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return tmp_path


def _make_state(team="t1", sprint_id="abcd1234") -> SprintState:
    return SprintState(
        sprint_id=sprint_id,
        goal="test",
        team=team,
        current_phase="think",
    )


def test_default_empty(isolated_data_dir):
    state = _make_state()
    assert state.queue_status == ""


def test_setter_round_trip(isolated_data_dir):
    state = _make_state()
    state.queue_status = "queued_capacity"
    save_sprint_state(state)
    loaded = load_sprint_state(state.team, state.sprint_id)
    assert loaded.queue_status == "queued_capacity"


def test_rate_limit_saturated_round_trip(isolated_data_dir):
    state = _make_state(sprint_id="rate0001")
    state.queue_status = "rate_limit_saturated"
    save_sprint_state(state)
    loaded = load_sprint_state(state.team, state.sprint_id)
    assert loaded.queue_status == "rate_limit_saturated"


def test_legacy_state_json_loads(isolated_data_dir, monkeypatch):
    """A state.json written BEFORE Phase 7 (no queue_status key) loads cleanly."""
    state = _make_state(sprint_id="legacy01")
    save_sprint_state(state)
    # Simulate legacy: rewrite file stripping queue_status.
    path = SprintState._state_path(state.team, state.sprint_id)
    data = json.loads(path.read_text())
    data.pop("queue_status", None)
    path.write_text(json.dumps(data, indent=2))
    # Load — queue_status field must default to "".
    loaded = load_sprint_state(state.team, state.sprint_id)
    assert loaded.queue_status == ""


def test_all_phase2_4_fields_coexist(isolated_data_dir):
    state = _make_state(sprint_id="coexist1")
    state.turn_counters = {"pm": 3}
    state.artifact_cap_bytes = 70_000
    state.status = "paused"
    state.careful_enabled = True
    state.review_sha = "deadbeefcafe"
    state.queue_status = "queued_capacity"
    save_sprint_state(state)
    loaded = load_sprint_state(state.team, state.sprint_id)
    assert loaded.turn_counters == {"pm": 3}
    assert loaded.artifact_cap_bytes == 70_000
    assert loaded.status == "paused"
    assert loaded.careful_enabled is True
    assert loaded.review_sha == "deadbeefcafe"
    assert loaded.queue_status == "queued_capacity"
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/sprint/test_sprint_state_queue_status.py tests/sprint/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "queue_status: str" clawteam/sprint/state.py` succeeds.
    - `pytest tests/sprint/test_sprint_state_queue_status.py -q` reports 5 passed.
    - BC: `pytest tests/sprint/ -q` still green (existing Phase 2 / Phase 4 sprint-state tests).
  </acceptance_criteria>
  <done>queue_status additive field lives; legacy state.json files load unchanged; Plan 07-02 can write/read the field.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: TemplateDef [conductor]/[attention]/[cost] sub-blocks</name>
  <files>
    clawteam/templates/__init__.py,
    tests/templates/test_template_def_phase7_blocks.py
  </files>
  <read_first>
    clawteam/templates/__init__.py (Phase 6 precedent at MemoryConfig/DesignShotgunConfig/BrowserConfig classes + _parse_toml pattern),
    tests/templates/test_template_def_phase6_blocks.py (test shape to mirror)
  </read_first>
  <behavior>
    - Test 1: existing gstack.toml loads cleanly; tmpl.conductor is None, tmpl.attention is None, tmpl.cost is None.
    - Test 2-7: 6 non-gstack templates parametrized — all 3 new fields are None.
    - Test 8: `[conductor] max_concurrent_sprints = 20` parses; field values round-trip; defaults apply to unset keys.
    - Test 9: `[conductor] max_concurrent_sprints = 0` raises ValidationError (ge=1).
    - Test 10: `[attention] urgency_weight = 15 blocking_weight = 8 tag_weights = {design=3, security=5}` parses.
    - Test 11: `[cost] budget_usd = 200 fallback_at_percent = 90 alarm_percent = [60, 90, 100]` parses.
    - Test 12: `[cost] fallback_at_percent = 110` raises ValidationError (le=100).
    - Test 13: Phase 5/6 blocks still work unchanged ([ship] + [memory] + [cost] coexist).
  </behavior>
  <action>
**1. `clawteam/templates/__init__.py` — APPEND 3 pydantic config classes after the Phase 6 `BrowserConfig` class:**

```python
# ---------------------------------------------------------------------------
# Phase 7 Wave 0 (Plan 07-01 Task 4): concurrency + attention + cost sub-blocks.
# All default to None so existing 6 bundled templates + gstack.toml parse
# unchanged. gstack-opt-in users add e.g. [conductor] max_concurrent_sprints = 20
# to their gstack.toml to override defaults.
# ---------------------------------------------------------------------------


class ConductorConfig(BaseModel):
    """[conductor] TOML block — SprintConductor concurrency caps (D-01/02/03)."""

    max_concurrent_sprints: int = Field(
        default=10,
        ge=1,
        description="Cap on simultaneously-running sprints per team. Sprints over cap enter queue_status='queued_capacity'.",
    )
    max_tasks_per_agent: int = Field(
        default=1,
        ge=1,
        description="Cap on concurrent task dispatches per agent role. Prevents accidentally-concurrent pm across sibling sprints.",
    )
    max_active_agents: int = Field(
        default=6,
        ge=1,
        description="Cap on concurrent active agents. Agents over cap sleep-poll (no Claude keepalive burn).",
    )
    acquire_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Grace period for acquiring max_concurrent_sprints before sprint enters queued state.",
    )


class AttentionConfig(BaseModel):
    """[attention] TOML block — AttentionQueue priority weights (D-05)."""

    urgency_weight: int = Field(
        default=10,
        ge=0,
        description="Multiplier applied to URGENCY bucket (critical=3 .. low=0).",
    )
    blocking_weight: int = Field(
        default=5,
        ge=0,
        description="Added when question.md frontmatter has blocking=true.",
    )
    tag_weights: dict[str, int] = Field(
        default_factory=dict,
        description="Per-tag weight dict (e.g., design=2, security=3).",
    )


class CostConfig(BaseModel):
    """[cost] TOML block — budget + fallback + alarm thresholds (D-10)."""

    budget_usd: float = Field(
        default=100.0,
        ge=0.0,
        description="Per-team monthly budget. Set to 0 to disable budget tracking.",
    )
    fallback_at_percent: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Percent-of-budget at which model_fallback_ladder kicks in (opus→sonnet→haiku).",
    )
    alarm_percent: list[float] = Field(
        default_factory=lambda: [50.0, 80.0, 100.0],
        description="Budget threshold list; emits BudgetAlarmReached on each crossing.",
    )
```

**2. EDIT `TemplateDef` class — append 3 new optional fields after `browser: BrowserConfig | None = None`:**

```python
    # Phase 7 Wave 0 (Plan 07-01 Task 4): concurrency + attention + cost sub-blocks.
    conductor: ConductorConfig | None = None
    attention: AttentionConfig | None = None
    cost: CostConfig | None = None
```

**3. EDIT `_parse_toml` — in the Phase 6 additive block, APPEND 3 new raw lookups + 3 kwarg passes:**

```python
    # Phase 7 Wave 0 (Plan 07-01): concurrency + attention + cost sub-blocks.
    conductor_raw = raw.get("conductor")
    attention_raw = raw.get("attention")
    cost_raw = raw.get("cost")

    return TemplateDef(
        # ... existing kwargs including memory/design_shotgun/browser ...
        conductor=ConductorConfig(**conductor_raw) if conductor_raw is not None else None,
        attention=AttentionConfig(**attention_raw) if attention_raw is not None else None,
        cost=CostConfig(**cost_raw) if cost_raw is not None else None,
    )
```

**4. `tests/templates/test_template_def_phase7_blocks.py` (NEW, ~200 LOC):** Mirror `tests/templates/test_template_def_phase6_blocks.py` exact structure. Parametrize BC tests over 6 non-gstack templates.

**Do NOT:** modify any existing .toml file. Do NOT touch gstack.toml (users opt-in by editing their local gstack.toml).
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/templates/test_template_def_phase7_blocks.py tests/templates/ tests/test_template_regression_matrix.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "class ConductorConfig" clawteam/templates/__init__.py` succeeds.
    - `grep -q "class AttentionConfig" clawteam/templates/__init__.py` succeeds.
    - `grep -q "class CostConfig" clawteam/templates/__init__.py` succeeds.
    - `grep -E "conductor:\s+ConductorConfig" clawteam/templates/__init__.py` matches.
    - `pytest tests/templates/test_template_def_phase7_blocks.py -q` reports 13 passed.
    - BC: `pytest tests/templates/ -q` still green; QUALITY-14 regression matrix unchanged.
  </acceptance_criteria>
  <done>TemplateDef carries 10 optional sub-blocks across Phase 3/4/5/6/7. Plans 07-02 through 07-07 read these config blocks when gstack teams opt in.</done>
</task>

</tasks>

<verification>
1. `pytest tests/test_pyproject_optional_extras.py tests/events/test_phase7_events.py tests/sprint/test_sprint_state_queue_status.py tests/templates/test_template_def_phase7_blocks.py -q` — all green.
2. BC: `pytest tests/events/ tests/sprint/ tests/templates/ tests/test_template_regression_matrix.py -q` — green.
3. `python -c "from clawteam.events.types import ToolCallCompleted, ClaudeApiResponse, BudgetAlarmReached, RateLimitSaturated, ZombieWorktreeGced, DormancyTransition; from clawteam.templates import ConductorConfig, AttentionConfig, CostConfig; import clawteam.attention, clawteam.cost, clawteam.rate_limit; print('imports ok')"` prints "imports ok".
</verification>

<success_criteria>
- All 4 task acceptance criteria met.
- Six new events register on module import.
- Three new top-level packages importable.
- `pip install 'clawteam[attend]'` (not executed) would pull watchdog.
- Existing state.json files + template .toml files parse unchanged.
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-01-SUMMARY.md`.
</output>
