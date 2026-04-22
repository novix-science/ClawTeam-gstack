"""Plan 07-06 Task 2 — CacheTracker event subscriber (D-12).

``cache_hit_rate = cache_read / (cache_read + cache_creation)`` per team.
Above-50% threshold considered healthy. Listens on EventBus for
``ClaudeApiResponse`` events; emits nothing itself — dashboard consumers
pull via ``cache_hit_rate()`` at render time.
"""
from __future__ import annotations

from clawteam.cost.cache_tracker import HEALTHY_THRESHOLD, CacheTracker
from clawteam.events.bus import EventBus
from clawteam.events.types import ClaudeApiResponse


def test_fresh_zero_rate():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    assert t.cache_hit_rate() == 0.0
    assert t.is_healthy() is False


def test_only_creation_zero_rate():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    for _ in range(3):
        bus.emit(
            ClaudeApiResponse(
                team_name="t", cache_creation_tokens=1000, cache_read_tokens=0
            )
        )
    assert t.cache_hit_rate() == 0.0


def test_only_read_full_rate():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(
        ClaudeApiResponse(team_name="t", cache_read_tokens=1000, cache_creation_tokens=0)
    )
    assert t.cache_hit_rate() == 1.0


def test_mixed_rate_50_percent():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(ClaudeApiResponse(team_name="t", cache_creation_tokens=1000))
    bus.emit(ClaudeApiResponse(team_name="t", cache_read_tokens=1000))
    assert t.cache_hit_rate() == 0.5


def test_other_team_ignored():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(ClaudeApiResponse(team_name="OTHER", cache_read_tokens=999))
    assert t.cache_hit_rate() == 0.0


def test_healthy_threshold_above_50():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(
        ClaudeApiResponse(
            team_name="t", cache_read_tokens=600, cache_creation_tokens=400
        )
    )
    # Rate = 0.6 > 0.5 -> healthy.
    assert t.is_healthy() is True


def test_healthy_threshold_below_50():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(
        ClaudeApiResponse(
            team_name="t", cache_read_tokens=400, cache_creation_tokens=600
        )
    )
    # Rate = 0.4 < 0.5 -> unhealthy.
    assert t.is_healthy() is False


def test_totals_accessors():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(
        ClaudeApiResponse(
            team_name="t", cache_read_tokens=500, cache_creation_tokens=250
        )
    )
    assert t.total_cache_read() == 500
    assert t.total_cache_creation() == 250


def test_healthy_threshold_constant():
    assert HEALTHY_THRESHOLD == 0.5


def test_healthy_threshold_strict_greater():
    # Exactly 0.5 -> is_healthy() should be False (strict >, not >=);
    # "healthy" means sustained cache use beyond break-even.
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(
        ClaudeApiResponse(
            team_name="t", cache_read_tokens=500, cache_creation_tokens=500
        )
    )
    assert t.cache_hit_rate() == 0.5
    assert t.is_healthy() is False


def test_cost_init_reexports():
    # Plan 07-06 must add apply_fallback + CacheTracker to clawteam.cost
    # public API.
    from clawteam.cost import (
        CacheTracker as CT,
        FALLBACK_LADDER as FL,
        HEALTHY_THRESHOLD as HT,
        apply_fallback as af,
    )

    assert CT is CacheTracker
    assert FL["opus"] == "sonnet"
    assert HT == 0.5
    assert af("claude-opus", 90.0, 80.0) == ("claude-sonnet", True)
