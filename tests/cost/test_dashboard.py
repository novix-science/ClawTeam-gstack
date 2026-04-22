"""Dashboard render_team / render_text tests (Phase 7 Plan 07-07, Task 1).

Covers:
- Empty tracker shape (status='ok', zero spend, no alarms, no actives).
- With spend: cost_usd + per-agent + per-sprint + cache_hit_rate reflect events.
- Alarms fired: crossing 50 + 80 -> [50, 80] in sorted order.
- No-budget safe: spend_percent == 0.0 when budget_usd == 0 (no div-zero).
- Active agents surface from explicit list kwarg.
- render_text contains a substantive one-liner summary.
"""
from __future__ import annotations

import pytest

from clawteam.cost.cache_tracker import CacheTracker
from clawteam.cost.dashboard import render_team, render_text
from clawteam.cost.tracker import CostTracker
from clawteam.events.bus import EventBus
from clawteam.events.types import ClaudeApiResponse, ToolCallCompleted


def test_render_team_empty_tracker_shape():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)
    ct = CacheTracker(team="t", bus=bus)

    d = render_team("t", t, ct)

    assert d["team"] == "t"
    assert d["status"] == "ok"
    assert d["cost_usd"] == 0.0
    assert d["budget_usd"] == 100.0
    assert d["spend_percent"] == 0.0
    assert d["per_agent"] == {}
    assert d["per_sprint"] == {}
    assert d["cache_hit_rate"] == 0.0
    assert d["alarms_fired"] == []
    assert d["active_agents"] == []
    assert d["active_agent_count"] == 0


def test_render_team_with_spend():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)
    ct = CacheTracker(team="t", bus=bus)

    bus.emit(ToolCallCompleted(
        team_name="t", agent="pm", sprint_id="s1", cost_usd=10.0,
    ))
    bus.emit(ToolCallCompleted(
        team_name="t", agent="ceo", sprint_id="s1", cost_usd=20.0,
    ))
    bus.emit(ClaudeApiResponse(
        team_name="t", cache_read_tokens=800, cache_creation_tokens=200,
    ))

    d = render_team("t", t, ct)

    assert d["cost_usd"] == pytest.approx(30.0)
    assert d["per_agent"] == {"pm": pytest.approx(10.0), "ceo": pytest.approx(20.0)}
    assert d["per_sprint"] == {"s1": pytest.approx(30.0)}
    assert d["cache_hit_rate"] == pytest.approx(0.8)
    assert d["cache_healthy"] is True
    assert d["spend_percent"] == pytest.approx(30.0)


def test_render_team_alarms_fired():
    bus = EventBus()
    t = CostTracker(
        team="t", bus=bus, budget_usd=100.0, alarm_percent=[50, 80, 100],
    )
    # One event that crosses both 50 and 80 thresholds at once.
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=81.0))

    d = render_team("t", t, None)

    assert sorted(d["alarms_fired"]) == [50, 80]


def test_render_team_no_budget_safe():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=0.0)
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=50.0))

    d = render_team("t", t, None)

    assert d["spend_percent"] == 0.0
    assert d["cost_usd"] == pytest.approx(50.0)
    assert d["budget_usd"] == 0.0


def test_render_team_with_active_agents():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)

    d = render_team("t", t, None, active_agents=["pm", "ceo"])

    assert d["active_agents"] == ["pm", "ceo"]
    assert d["active_agent_count"] == 2


def test_render_text_contains_summary():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=25.0))

    d = render_team("t", t, None, active_agents=["pm"])
    text = render_text(d)

    assert "25.00" in text
    assert "100.00" in text
    assert "active agents: 1" in text


def test_render_text_no_budget():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=0.0)
    text = render_text(render_team("t", t, None))
    assert "no budget" in text
