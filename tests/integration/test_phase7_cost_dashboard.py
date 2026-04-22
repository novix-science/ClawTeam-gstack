"""Phase 7 Plan 07-09 Task 3: cost dashboard 100-event fixture (D-16 / QUALITY-12).

Locks QUALITY-12 floor: Phase 7 cost pipeline (CostTracker + apply_fallback
+ CacheTracker + render_team) must correctly aggregate a 100-event fixture
stream, fire 50/80/100% BudgetAlarmReached exactly once each, and expose
the rollup shape the Plan 07-07 ``clawteam team show`` dashboard reads.

Also pins the apply_fallback policy at the 80% threshold (D-11 opus →
sonnet → haiku ladder) and the cache_hit_rate accumulator (D-12).
"""
from __future__ import annotations

import pytest

from clawteam.cost.cache_tracker import CacheTracker
from clawteam.cost.dashboard import render_team
from clawteam.cost.fallback import apply_fallback
from clawteam.cost.tracker import CostTracker
from clawteam.events.bus import EventBus
from clawteam.events.types import (
    BudgetAlarmReached,
    ClaudeApiResponse,
    ToolCallCompleted,
)


def test_100_events_rollup():
    """D-16: 100 events across 5 agents — total and per-agent rollup match."""
    bus = EventBus()
    tracker = CostTracker(team="t", bus=bus, budget_usd=1000.0)
    agents = ["pm", "ceo", "engineer", "reviewer", "sre"]
    per_agent_expected: dict[str, float] = {a: 0.0 for a in agents}
    for i in range(100):
        agent = agents[i % 5]
        cost = 0.1 + (i * 0.01)  # Monotonically increasing per event.
        bus.emit(
            ToolCallCompleted(team_name="t", agent=agent, cost_usd=cost)
        )
        per_agent_expected[agent] += cost

    total_expected = sum(per_agent_expected.values())
    assert tracker.current_spend_usd() == pytest.approx(total_expected)
    observed = tracker.rollup_by_agent()
    assert set(observed.keys()) == set(agents)
    for a, v in per_agent_expected.items():
        assert observed[a] == pytest.approx(v)


def test_budget_alarm_threshold_crossings():
    """D-10 / D-16: BudgetAlarmReached fires exactly once at 50/80/100%."""
    bus = EventBus()
    CostTracker(
        team="t", bus=bus, budget_usd=100.0, alarm_percent=[50, 80, 100]
    )
    received: list[BudgetAlarmReached] = []
    bus.subscribe(BudgetAlarmReached, lambda ev: received.append(ev))

    # Cross 50 with single $51 event.
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=51.0))
    # Cross 80 (total = 81).
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=30.0))
    # Cross 100 (total = 105).
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=24.0))
    # Further events must NOT re-fire the alarm.
    for _ in range(10):
        bus.emit(ToolCallCompleted(team_name="t", cost_usd=10.0))

    percents = [int(ev.percent) for ev in received]
    assert percents == [50, 80, 100]
    assert len(received) == 3


def test_fallback_activates_at_80():
    """D-11: apply_fallback ladder engages at >=80%; no change below 80."""
    # Below threshold: unchanged.
    assert apply_fallback("claude-opus", 79.9, 80.0) == ("claude-opus", False)
    # At threshold: opus -> sonnet.
    assert apply_fallback("claude-opus", 80.0, 80.0) == ("claude-sonnet", True)
    # Above threshold: sonnet -> haiku.
    assert apply_fallback("claude-sonnet", 100.0, 80.0) == ("claude-haiku", True)


def test_dashboard_snapshot_at_each_threshold():
    """D-16: render_team reflects cost_usd + alarms_fired at each threshold crossing."""
    bus = EventBus()
    tracker = CostTracker(
        team="t", bus=bus, budget_usd=100.0, alarm_percent=[50, 80, 100]
    )
    cache = CacheTracker(team="t", bus=bus)

    # T=0: fresh tracker.
    snap0 = render_team("t", tracker, cache)
    assert snap0["cost_usd"] == 0.0
    assert snap0["alarms_fired"] == []

    # T=1: cross 50.
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=51.0))
    snap1 = render_team("t", tracker, cache)
    assert 50 in snap1["alarms_fired"]
    assert snap1["spend_percent"] == pytest.approx(51.0)

    # T=2: cross both 80 and 100.
    bus.emit(ToolCallCompleted(team_name="t", agent="ceo", cost_usd=60.0))
    snap2 = render_team("t", tracker, cache)
    assert sorted(snap2["alarms_fired"]) == [50, 80, 100]


def test_cache_hit_rate_tracked():
    """D-12: CacheTracker computes read / (read + creation); sub-0.5 is unhealthy."""
    bus = EventBus()
    cache = CacheTracker(team="t", bus=bus)

    for _ in range(5):
        bus.emit(
            ClaudeApiResponse(
                team_name="t", cache_read_tokens=800, cache_creation_tokens=200
            )
        )
    for _ in range(5):
        bus.emit(
            ClaudeApiResponse(team_name="t", cache_creation_tokens=1000)
        )

    # Reads = 5 * 800 = 4000; creation = 5 * 200 + 5 * 1000 = 6000.
    # Rate = 4000 / (4000 + 6000) = 0.4 — below 0.5 HEALTHY_THRESHOLD.
    assert cache.cache_hit_rate() == pytest.approx(0.4)
    assert cache.is_healthy() is False


def test_integrated_rollup_flow():
    """Full flow: CostTracker + CacheTracker + render_team interplay.

    Exercises:
    - Pricing backstop (cost_usd=0.0 triggers calculate_cost_usd fallback).
    - Per-agent + per-sprint rollup populated.
    - cache_hit_rate merged from CacheTracker at render time.
    - active_agents passthrough + count.
    """
    bus = EventBus()
    tracker = CostTracker(
        team="integ", bus=bus, budget_usd=50.0, alarm_percent=[50, 80, 100]
    )
    cache = CacheTracker(team="integ", bus=bus)

    for i, a in enumerate(["pm", "ceo", "engineer"]):
        bus.emit(
            ToolCallCompleted(
                team_name="integ",
                agent=a,
                sprint_id=f"s{i}",
                model="claude-sonnet",
                tokens_input=500_000,
                tokens_output=100_000,
                cost_usd=0.0,  # Trigger pricing backstop.
            )
        )
        bus.emit(
            ClaudeApiResponse(
                team_name="integ",
                cache_read_tokens=400_000,
                cache_creation_tokens=100_000,
            )
        )

    d = render_team("integ", tracker, cache, active_agents=["pm"])
    # Sonnet pricing: 500k in * $3/M = $1.50; 100k out * $15/M = $1.50
    # → $3.00 per event * 3 events = $9.00 total.
    assert d["cost_usd"] > 0.0
    # Cache: 3 * 400k read / (1.2M read + 300k creation) = 0.8.
    assert d["cache_hit_rate"] == pytest.approx(0.8)
    assert d["active_agent_count"] == 1
    assert len(d["per_agent"]) == 3
    assert len(d["per_sprint"]) == 3
