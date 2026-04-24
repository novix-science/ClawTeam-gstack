---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 05
type: execute
wave: 4
depends_on: [07-01]
files_modified:
  - clawteam/cost/__init__.py
  - clawteam/cost/pricing.py
  - clawteam/cost/rollup.py
  - clawteam/cost/tracker.py
  - tests/cost/__init__.py
  - tests/cost/test_pricing.py
  - tests/cost/test_tracker.py
autonomous: true
requirements:
  - QUALITY-12
tags:
  - cost-tracking
  - event-subscriber
  - budget-alarm
  - pricing

must_haves:
  truths:
    - "clawteam/cost/pricing.py ships a hardcoded per-model USD/M-token table for opus/sonnet/haiku with input + output rates"
    - "CostRollup frozen dataclass with 9 fields matching CONTEXT §specifics schema"
    - "CostTracker subscribes to ToolCallCompleted events on construction; aggregates by (team, sprint, agent)"
    - "CostTracker fires BudgetAlarmReached on 50/80/100 threshold crossings exactly once each (no duplicates within run)"
    - "Model fallback NOT applied in tracker — only advisory alarm emission (fallback policy is Plan 07-06 fallback.py)"
    - "calculate_cost_usd(model, input_tokens, output_tokens) pure function with deterministic output"
  artifacts:
    - path: clawteam/cost/pricing.py
      provides: "Per-model pricing table + calculate_cost_usd"
      contains: "MODEL_PRICING|def calculate_cost_usd"
    - path: clawteam/cost/rollup.py
      provides: "CostRollup frozen dataclass"
      contains: "class CostRollup"
    - path: clawteam/cost/tracker.py
      provides: "CostTracker event-driven accumulator"
      contains: "class CostTracker"
  key_links:
    - from: clawteam/cost/tracker.py
      to: clawteam/events/types.py
      via: "CostTracker subscribes to ToolCallCompleted + emits BudgetAlarmReached"
      pattern: "ToolCallCompleted|BudgetAlarmReached"
    - from: clawteam/cost/tracker.py
      to: clawteam/cost/pricing.py
      via: "Tracker uses calculate_cost_usd when event cost_usd is 0.0"
      pattern: "calculate_cost_usd"
---

<objective>
Wave 4 part 1 — cost pricing table + CostRollup schema + CostTracker event subscriber. Accounting only; no rendering, no fallback (those are Plans 07-06 and 07-07).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md

<interfaces>
From clawteam/events/types.py (Plan 07-01):
```python
@dataclass class ToolCallCompleted(HarnessEvent):
    agent: str = ""
    tool_name: str = ""
    sprint_id: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    model: str = ""
    cost_usd: float = 0.0

@dataclass class BudgetAlarmReached(HarnessEvent):
    percent: float = 0.0
    spent_usd: float = 0.0
    budget_usd: float = 0.0
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pricing table + calculate_cost_usd</name>
  <files>
    clawteam/cost/pricing.py,
    tests/cost/__init__.py,
    tests/cost/test_pricing.py
  </files>
  <read_first>
    clawteam/cost/__init__.py (Plan 07-01 skeleton)
  </read_first>
  <behavior>
    - Test 1: `test_opus_pricing` — known table: opus input=$15/M, output=$75/M. calculate_cost_usd("claude-opus", 1_000_000, 1_000_000) == 90.0.
    - Test 2: `test_sonnet_pricing` — sonnet input=$3/M, output=$15/M. 1M in + 1M out == 18.0.
    - Test 3: `test_haiku_pricing` — haiku input=$0.25/M, output=$1.25/M. 1M in + 1M out == 1.5.
    - Test 4: `test_model_aliases` — "claude-3-opus", "opus", "claude-opus-4" all map to opus tier.
    - Test 5: `test_unknown_model_returns_zero` — "gpt-4" returns 0.0 (log warning).
    - Test 6: `test_zero_tokens_zero_cost`.
    - Test 7: `test_partial_token_counts` — 500 in + 1000 out for opus = 500*15e-6 + 1000*75e-6 = 0.0825.
  </behavior>
  <action>
**1. `clawteam/cost/pricing.py` (NEW, ~80 LOC):**

```python
"""Per-model pricing table (D-11 substrate).

Prices are per 1M tokens in USD. Source: Anthropic public pricing as of
2026-04 [ASSUMED — update via PR when pricing changes].

Aliases allow the tracker to accept arbitrary model strings (claude-3-opus,
claude-opus-4-7, opus-20250929) and resolve to a tier.
"""
from __future__ import annotations

import logging
from typing import Literal

_LOG = logging.getLogger(__name__)

ModelTier = Literal["opus", "sonnet", "haiku"]

# USD per 1M tokens (input, output)
MODEL_PRICING: dict[ModelTier, tuple[float, float]] = {
    "opus":   (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku":  (0.25, 1.25),
}


def resolve_tier(model: str) -> ModelTier | None:
    """Map a concrete model string (e.g., 'claude-3-opus-20240229') to a tier."""
    if not model:
        return None
    m = model.lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return None


def calculate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return USD cost of the invocation. Unknown model → 0.0 (logged)."""
    tier = resolve_tier(model)
    if tier is None:
        _LOG.debug("Unknown model for pricing: %r — returning 0.0", model)
        return 0.0
    in_rate, out_rate = MODEL_PRICING[tier]
    return (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate


__all__ = ["MODEL_PRICING", "calculate_cost_usd", "resolve_tier", "ModelTier"]
```

**2. `tests/cost/__init__.py` (empty file).**

**3. `tests/cost/test_pricing.py` (~80 LOC):**

```python
import pytest
from clawteam.cost.pricing import MODEL_PRICING, calculate_cost_usd, resolve_tier


def test_opus_pricing():
    # 1M in + 1M out = 15 + 75 = 90.
    assert calculate_cost_usd("claude-opus", 1_000_000, 1_000_000) == pytest.approx(90.0)


def test_sonnet_pricing():
    assert calculate_cost_usd("claude-sonnet", 1_000_000, 1_000_000) == pytest.approx(18.0)


def test_haiku_pricing():
    assert calculate_cost_usd("claude-haiku", 1_000_000, 1_000_000) == pytest.approx(1.5)


def test_model_aliases():
    for alias in ("claude-3-opus", "opus", "claude-opus-4-7", "claude-3-opus-20240229"):
        assert resolve_tier(alias) == "opus"
    for alias in ("claude-sonnet", "claude-3-sonnet"):
        assert resolve_tier(alias) == "sonnet"


def test_unknown_model_zero():
    assert calculate_cost_usd("gpt-4", 1_000_000, 1_000_000) == 0.0


def test_empty_model_zero():
    assert calculate_cost_usd("", 100, 100) == 0.0


def test_zero_tokens():
    assert calculate_cost_usd("claude-opus", 0, 0) == 0.0


def test_partial_tokens():
    # 500 in × $15/M + 1000 out × $75/M = 7500e-6 + 75000e-6 = 0.0825.
    assert calculate_cost_usd("claude-opus", 500, 1000) == pytest.approx(0.0825)
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/cost/test_pricing.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "MODEL_PRICING" clawteam/cost/pricing.py` succeeds.
    - `grep -q "def calculate_cost_usd" clawteam/cost/pricing.py` succeeds.
    - `pytest tests/cost/test_pricing.py -q` reports all green.
  </acceptance_criteria>
  <done>Pricing table lives; Task 2 tracker can compute cost when event cost_usd is 0.0.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: CostRollup schema + CostTracker event subscriber</name>
  <files>
    clawteam/cost/rollup.py,
    clawteam/cost/tracker.py,
    clawteam/cost/__init__.py,
    tests/cost/test_tracker.py
  </files>
  <read_first>
    clawteam/events/bus.py (EventBus shape),
    clawteam/events/types.py (ToolCallCompleted + BudgetAlarmReached from Plan 07-01),
    clawteam/cost/pricing.py (Task 1 output)
  </read_first>
  <behavior>
    - Test 1: `test_rollup_frozen` — CostRollup cannot be mutated after construction.
    - Test 2: `test_tracker_starts_at_zero` — `tracker.current_spend_usd() == 0.0`.
    - Test 3: `test_single_event_aggregated` — emit one ToolCallCompleted; tracker.current_spend_usd() updated.
    - Test 4: `test_other_team_events_ignored` — emit ToolCallCompleted with different team_name; no effect.
    - Test 5: `test_alarm_fires_at_each_threshold` — emit events totaling 51/81/100 USD of $100 budget; BudgetAlarmReached fires 3 times with correct percents.
    - Test 6: `test_alarm_not_duplicated_within_run` — further events past 100 do NOT re-fire.
    - Test 7: `test_rollup_by_agent` — 2 agents, 3 events; rollup_by_agent(sprint_id=None) returns dict keyed by agent with correct totals.
    - Test 8: `test_rollup_by_sprint` — 2 sprints; rollup_by_sprint() returns dict keyed by sprint_id.
    - Test 9: `test_tracker_uses_pricing_when_event_cost_zero` — event with cost_usd=0.0 + tokens_input=1M + model="claude-haiku" → tracker adds 0.25 (pricing-computed).
    - Test 10: `test_100_event_fixture` (D-16 precedent) — 100 events, 5 agents; verify final current_spend and per-agent breakdown.
  </behavior>
  <action>
**1. `clawteam/cost/rollup.py` (NEW, ~50 LOC):**

```python
"""CostRollup — frozen dataclass used by dashboard (Plan 07-07)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CostRollup:
    team: str
    sprint_id: Optional[str]  # None = team-level rollup
    agent: Optional[str]
    tokens_opus: int
    tokens_sonnet: int
    tokens_haiku: int
    cost_usd: float
    cache_hit_rate: float  # 0.0 when no Claude API events observed
    period_start: datetime
    period_end: datetime


__all__ = ["CostRollup"]
```

**2. `clawteam/cost/tracker.py` (NEW, ~220 LOC):**

```python
"""CostTracker — event-driven cost aggregator (D-09, D-10).

Subscribes to ToolCallCompleted on EventBus. Maintains in-memory
aggregates keyed by (team, sprint, agent). Emits BudgetAlarmReached
on threshold crossings. Does NOT apply model fallback — that is
Plan 07-06 fallback.py policy.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from clawteam.cost.pricing import calculate_cost_usd, resolve_tier
from clawteam.cost.rollup import CostRollup
from clawteam.events.bus import EventBus
from clawteam.events.types import BudgetAlarmReached, ToolCallCompleted


class CostTracker:
    """Per-team cost aggregator driven by ToolCallCompleted events."""

    def __init__(
        self,
        team: str,
        *,
        budget_usd: float = 100.0,
        alarm_percent: Optional[list[float]] = None,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._team = team
        self._budget_usd = float(budget_usd)
        self._alarm_percent = sorted(alarm_percent or [50.0, 80.0, 100.0])
        self._fired_alarms: set[float] = set()
        self._bus = bus
        self._lock = threading.RLock()
        # Aggregates: {agent: cost_usd}, {sprint_id: cost_usd}, {(agent,sprint): cost_usd}
        self._by_agent: dict[str, float] = defaultdict(float)
        self._by_sprint: dict[str, float] = defaultdict(float)
        self._by_agent_sprint: dict[tuple[str, str], float] = defaultdict(float)
        self._tokens_by_tier: dict[str, int] = defaultdict(int)  # tier → total (in+out)
        self._total: float = 0.0
        self._period_start = datetime.now(timezone.utc)
        self._period_end = self._period_start
        if bus is not None:
            bus.subscribe(ToolCallCompleted, self._on_tool_call)

    # ── public ─────────────────────────────────────────────────

    def current_spend_usd(self) -> float:
        with self._lock:
            return self._total

    def spend_percent(self) -> float:
        if self._budget_usd <= 0:
            return 0.0
        return (self.current_spend_usd() / self._budget_usd) * 100.0

    def rollup_by_agent(self) -> dict[str, float]:
        with self._lock:
            return dict(self._by_agent)

    def rollup_by_sprint(self) -> dict[str, float]:
        with self._lock:
            return dict(self._by_sprint)

    def rollup_team(self) -> CostRollup:
        with self._lock:
            return CostRollup(
                team=self._team,
                sprint_id=None,
                agent=None,
                tokens_opus=self._tokens_by_tier.get("opus", 0),
                tokens_sonnet=self._tokens_by_tier.get("sonnet", 0),
                tokens_haiku=self._tokens_by_tier.get("haiku", 0),
                cost_usd=self._total,
                cache_hit_rate=0.0,  # populated externally by cache_tracker (Plan 07-06)
                period_start=self._period_start,
                period_end=self._period_end,
            )

    # ── event handler ─────────────────────────────────────────

    def _on_tool_call(self, event: ToolCallCompleted) -> None:
        if event.team_name != self._team:
            return
        cost = float(event.cost_usd)
        if cost <= 0.0:
            # Backstop: compute from pricing table when caller didn't supply cost.
            cost = calculate_cost_usd(
                event.model, event.tokens_input, event.tokens_output
            )
        with self._lock:
            prev_total = self._total
            self._total += cost
            if event.agent:
                self._by_agent[event.agent] += cost
            if event.sprint_id:
                self._by_sprint[event.sprint_id] += cost
            if event.agent and event.sprint_id:
                self._by_agent_sprint[(event.agent, event.sprint_id)] += cost
            tier = resolve_tier(event.model)
            if tier is not None:
                self._tokens_by_tier[tier] += int(event.tokens_input) + int(event.tokens_output)
            self._period_end = datetime.now(timezone.utc)
            prev_pct = (prev_total / self._budget_usd * 100.0) if self._budget_usd > 0 else 0.0
            new_pct = (self._total / self._budget_usd * 100.0) if self._budget_usd > 0 else 0.0
            newly_fired: list[float] = []
            for thresh in self._alarm_percent:
                if thresh in self._fired_alarms:
                    continue
                if new_pct >= thresh > prev_pct or (new_pct >= thresh and prev_pct == 0 and thresh == 0):
                    self._fired_alarms.add(thresh)
                    newly_fired.append(thresh)
        # Emit outside lock.
        if self._bus is not None:
            for thresh in newly_fired:
                try:
                    self._bus.emit(
                        BudgetAlarmReached(
                            team_name=self._team,
                            percent=thresh,
                            spent_usd=self._total,
                            budget_usd=self._budget_usd,
                        )
                    )
                except Exception:  # pragma: no cover
                    pass


__all__ = ["CostTracker"]
```

**3. EDIT `clawteam/cost/__init__.py`:**

```python
"""Cost substrate — tracker + dashboard + fallback + cache_tracker.

Plan 07-05 ships pricing + rollup + tracker.
Plan 07-06 ships fallback + cache_tracker.
Plan 07-07 wires dashboard into clawteam team show.
"""
from __future__ import annotations

from clawteam.cost.pricing import MODEL_PRICING, calculate_cost_usd, resolve_tier
from clawteam.cost.rollup import CostRollup
from clawteam.cost.tracker import CostTracker

__all__ = [
    "MODEL_PRICING",
    "calculate_cost_usd",
    "resolve_tier",
    "CostRollup",
    "CostTracker",
]
```

**4. Tests:** `tests/cost/test_tracker.py` (~240 LOC):

```python
from dataclasses import fields as dc_fields
import pytest
from clawteam.events.bus import EventBus
from clawteam.events.types import BudgetAlarmReached, ToolCallCompleted
from clawteam.cost.rollup import CostRollup
from clawteam.cost.tracker import CostTracker


def test_rollup_frozen():
    from datetime import datetime, timezone
    r = CostRollup(
        team="t", sprint_id=None, agent=None, tokens_opus=0, tokens_sonnet=0,
        tokens_haiku=0, cost_usd=0.0, cache_hit_rate=0.0,
        period_start=datetime.now(timezone.utc), period_end=datetime.now(timezone.utc),
    )
    with pytest.raises(Exception):
        r.cost_usd = 1.0  # type: ignore[misc]


def test_tracker_starts_zero():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    assert t.current_spend_usd() == 0.0
    assert t.spend_percent() == 0.0


def test_single_event_aggregated():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", model="claude-opus",
                                tokens_input=1_000_000, tokens_output=0, cost_usd=15.0))
    assert t.current_spend_usd() == pytest.approx(15.0)
    assert t.rollup_by_agent() == {"pm": pytest.approx(15.0)}


def test_other_team_ignored():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    bus.emit(ToolCallCompleted(team_name="OTHER", agent="pm", model="claude-opus", cost_usd=50.0))
    assert t.current_spend_usd() == 0.0


def test_alarm_fires_at_each_threshold():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0, alarm_percent=[50, 80, 100])
    received: list = []
    bus.subscribe(BudgetAlarmReached, lambda ev: received.append(ev))
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=51.0))  # crosses 50
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=30.0))  # crosses 80 (total=81)
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=20.0))  # crosses 100
    percents = [ev.percent for ev in received]
    assert percents == [50, 80, 100]


def test_alarm_not_duplicated():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0, alarm_percent=[50])
    received: list = []
    bus.subscribe(BudgetAlarmReached, lambda ev: received.append(ev))
    for _ in range(5):
        bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=100.0))
    assert len(received) == 1


def test_rollup_by_agent():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=10.0))
    bus.emit(ToolCallCompleted(team_name="t", agent="ceo", cost_usd=20.0))
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=5.0))
    assert t.rollup_by_agent() == {"pm": pytest.approx(15.0), "ceo": pytest.approx(20.0)}


def test_rollup_by_sprint():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    bus.emit(ToolCallCompleted(team_name="t", sprint_id="s1", cost_usd=10.0))
    bus.emit(ToolCallCompleted(team_name="t", sprint_id="s2", cost_usd=25.0))
    assert t.rollup_by_sprint() == {"s1": pytest.approx(10.0), "s2": pytest.approx(25.0)}


def test_pricing_backstop_when_cost_zero():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    bus.emit(ToolCallCompleted(
        team_name="t", agent="pm", model="claude-haiku",
        tokens_input=1_000_000, tokens_output=0, cost_usd=0.0,
    ))
    # haiku input = $0.25/M × 1M = $0.25
    assert t.current_spend_usd() == pytest.approx(0.25)


def test_100_event_fixture():
    """D-16 precedent: 100 events × 5 agents; final rollup correctness."""
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=1000.0)
    agents = ["pm", "ceo", "engineer", "reviewer", "sre"]
    for i in range(100):
        bus.emit(ToolCallCompleted(
            team_name="t", agent=agents[i % 5], sprint_id=f"s{i % 3}",
            model="claude-sonnet", tokens_input=1000, tokens_output=500,
            cost_usd=0.0,  # backstop
        ))
    # Each event: sonnet 1000 in + 500 out = 1000*3e-6 + 500*15e-6 = 0.003 + 0.0075 = 0.0105.
    # Total = 100 × 0.0105 = 1.05.
    assert t.current_spend_usd() == pytest.approx(1.05, rel=1e-6)
    by_agent = t.rollup_by_agent()
    assert len(by_agent) == 5
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/cost/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "class CostTracker" clawteam/cost/tracker.py` succeeds.
    - `grep -q "class CostRollup" clawteam/cost/rollup.py` succeeds.
    - `pytest tests/cost/test_tracker.py -q` reports 10 passed.
  </acceptance_criteria>
  <done>Cost tracker subscribes to events, aggregates, fires alarms — all tested at 100-event scale.</done>
</task>

</tasks>

<verification>
1. `pytest tests/cost/ -q` — all green.
2. `python -c "from clawteam.cost import CostTracker, CostRollup, calculate_cost_usd; print('ok')"` — prints ok.
</verification>

<success_criteria>
- Tasks 1-2 acceptance met.
- Alarm-at-each-threshold + no-duplicate behavior proven.
- Pricing backstop proven for events missing cost_usd.
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-05-SUMMARY.md`.
</output>
