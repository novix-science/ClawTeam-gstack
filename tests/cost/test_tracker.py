"""Plan 07-05 Task 2 — CostRollup schema + CostTracker event subscriber.

D-09 cost tracker: listens on EventBus ToolCallCompleted, aggregates per
(team, sprint, agent), emits BudgetAlarmReached on 50/80/100 threshold
crossings. Tracker does NOT apply model fallback — that is Plan 07-06
fallback.py. D-16 100-event fixture precedent.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from clawteam.cost.rollup import CostRollup
from clawteam.cost.tracker import CostTracker
from clawteam.events.bus import EventBus
from clawteam.events.types import BudgetAlarmReached, ToolCallCompleted


def test_rollup_frozen():
    r = CostRollup(
        team="t",
        sprint_id=None,
        agent=None,
        tokens_opus=0,
        tokens_sonnet=0,
        tokens_haiku=0,
        cost_usd=0.0,
        cache_hit_rate=0.0,
        period_start=datetime.now(timezone.utc),
        period_end=datetime.now(timezone.utc),
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
    bus.emit(
        ToolCallCompleted(
            team_name="t",
            agent="pm",
            model="claude-opus",
            tokens_input=1_000_000,
            tokens_output=0,
            cost_usd=15.0,
        )
    )
    assert t.current_spend_usd() == pytest.approx(15.0)
    assert t.rollup_by_agent() == {"pm": pytest.approx(15.0)}


def test_other_team_ignored():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    bus.emit(
        ToolCallCompleted(
            team_name="OTHER",
            agent="pm",
            model="claude-opus",
            cost_usd=50.0,
        )
    )
    assert t.current_spend_usd() == 0.0


def test_alarm_fires_at_each_threshold():
    bus = EventBus()
    t = CostTracker(
        team="t", bus=bus, budget_usd=100.0, alarm_percent=[50, 80, 100]
    )
    received: list[BudgetAlarmReached] = []
    bus.subscribe(BudgetAlarmReached, lambda ev: received.append(ev))
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=51.0))  # crosses 50
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=30.0))  # crosses 80 (total=81)
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=20.0))  # crosses 100 (total=101)
    percents = [ev.percent for ev in received]
    assert percents == [50, 80, 100]
    # All three carry the tracker's team name.
    assert all(ev.team_name == "t" for ev in received)
    assert all(ev.budget_usd == 100.0 for ev in received)


def test_alarm_not_duplicated():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0, alarm_percent=[50])
    received: list[BudgetAlarmReached] = []
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
    assert t.rollup_by_agent() == {
        "pm": pytest.approx(15.0),
        "ceo": pytest.approx(20.0),
    }


def test_rollup_by_sprint():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    bus.emit(ToolCallCompleted(team_name="t", sprint_id="s1", cost_usd=10.0))
    bus.emit(ToolCallCompleted(team_name="t", sprint_id="s2", cost_usd=25.0))
    assert t.rollup_by_sprint() == {
        "s1": pytest.approx(10.0),
        "s2": pytest.approx(25.0),
    }


def test_pricing_backstop_when_cost_zero():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    bus.emit(
        ToolCallCompleted(
            team_name="t",
            agent="pm",
            model="claude-haiku",
            tokens_input=1_000_000,
            tokens_output=0,
            cost_usd=0.0,
        )
    )
    # haiku input = $0.25/M * 1M = $0.25.
    assert t.current_spend_usd() == pytest.approx(0.25)


def test_100_event_fixture():
    """D-16 precedent: 100 events * 5 agents; final rollup correctness."""
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=1000.0)
    agents = ["pm", "ceo", "engineer", "reviewer", "sre"]
    for i in range(100):
        bus.emit(
            ToolCallCompleted(
                team_name="t",
                agent=agents[i % 5],
                sprint_id=f"s{i % 3}",
                model="claude-sonnet",
                tokens_input=1000,
                tokens_output=500,
                cost_usd=0.0,  # backstop
            )
        )
    # Each event: sonnet 1000 in + 500 out
    #   = 1000*3e-6 + 500*15e-6 = 0.003 + 0.0075 = 0.0105.
    # Total = 100 * 0.0105 = 1.05.
    assert t.current_spend_usd() == pytest.approx(1.05, rel=1e-6)
    by_agent = t.rollup_by_agent()
    assert len(by_agent) == 5
    # 20 events per agent; 20 * 0.0105 = 0.21.
    for agent in agents:
        assert by_agent[agent] == pytest.approx(0.21, rel=1e-6)


def test_rollup_team_snapshot():
    """rollup_team() returns a frozen CostRollup with tokens by tier."""
    bus = EventBus()
    t = CostTracker(team="t", bus=bus)
    bus.emit(
        ToolCallCompleted(
            team_name="t",
            agent="pm",
            model="claude-opus",
            tokens_input=1000,
            tokens_output=500,
            cost_usd=0.090,
        )
    )
    bus.emit(
        ToolCallCompleted(
            team_name="t",
            agent="engineer",
            model="claude-sonnet",
            tokens_input=2000,
            tokens_output=1000,
            cost_usd=0.021,
        )
    )
    r = t.rollup_team()
    assert r.team == "t"
    assert r.sprint_id is None
    assert r.agent is None
    assert r.tokens_opus == 1500  # 1000 + 500
    assert r.tokens_sonnet == 3000  # 2000 + 1000
    assert r.tokens_haiku == 0
    assert r.cost_usd == pytest.approx(0.111)
    assert r.cache_hit_rate == 0.0  # populated by cache_tracker (Plan 07-06)
