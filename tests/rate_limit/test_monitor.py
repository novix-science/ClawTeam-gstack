"""Phase 7 Plan 07-02 Task 1: RateLimitMonitor — 60s sliding 429 window.

RED phase: monitor class does not yet exist; all eight tests MUST fail on
import or on behavior until the GREEN phase lands clawteam/rate_limit/monitor.py.

Sliding-window semantics under test (D-13):
- Fresh monitor → not saturated.
- Below-threshold 429 count → not saturated.
- Strictly greater than threshold in window → saturated.
- Window expiry → un-saturates.
- Emits RateLimitSaturated exactly once per rising edge.
- Re-emits after window clears and a fresh burst re-saturates.
- Custom threshold/window honored.
- Thread-safe under concurrent record_429().
"""
from __future__ import annotations

import threading

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import RateLimitSaturated
from clawteam.rate_limit import RateLimitMonitor


class FakeClock:
    """Monotonic fake clock for deterministic sliding-window tests."""

    def __init__(self, now: float = 0.0) -> None:
        self._now = float(now)

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += float(seconds)


def test_fresh_monitor_not_saturated():
    monitor = RateLimitMonitor()
    assert monitor.is_saturated() is False
    assert monitor.recent_429_count() == 0


def test_one_429_not_saturated():
    monitor = RateLimitMonitor()  # default threshold=3
    monitor.record_429()
    assert monitor.is_saturated() is False
    assert monitor.recent_429_count() == 1


def test_threshold_plus_one_saturated():
    monitor = RateLimitMonitor()  # default threshold=3
    for _ in range(4):
        monitor.record_429()
    assert monitor.is_saturated() is True
    assert monitor.recent_429_count() == 4


def test_window_expiry_un_saturates():
    clock = FakeClock(0.0)
    monitor = RateLimitMonitor(clock=clock.now)
    for _ in range(4):
        monitor.record_429()
    assert monitor.is_saturated() is True
    clock.advance(61.0)  # past default 60s window
    assert monitor.is_saturated() is False
    assert monitor.recent_429_count() == 0


def test_emits_rate_limit_saturated_event_on_threshold_cross():
    bus = EventBus()
    received: list[RateLimitSaturated] = []
    bus.subscribe(RateLimitSaturated, lambda ev: received.append(ev))
    clock = FakeClock(0.0)
    monitor = RateLimitMonitor(team_name="t", bus=bus, clock=clock.now)
    for _ in range(4):
        monitor.record_429()
    assert monitor.is_saturated() is True
    assert len(received) == 1
    ev = received[0]
    assert ev.recent_429_count == 4
    assert ev.threshold == 3
    assert ev.window_seconds == 60
    assert ev.team_name == "t"


def test_re_saturation_after_expiry_re_emits():
    bus = EventBus()
    received: list[RateLimitSaturated] = []
    bus.subscribe(RateLimitSaturated, lambda ev: received.append(ev))
    clock = FakeClock(0.0)
    monitor = RateLimitMonitor(team_name="t", bus=bus, clock=clock.now)
    for _ in range(4):
        monitor.record_429()
    assert len(received) == 1
    # Advance past window; old 429s age out — monitor rearms.
    clock.advance(61.0)
    # Fresh burst should cross the threshold again and fire a second event.
    for _ in range(4):
        monitor.record_429()
    assert monitor.is_saturated() is True
    assert len(received) == 2


def test_custom_threshold_and_window():
    clock = FakeClock(0.0)
    monitor = RateLimitMonitor(threshold=5, window_seconds=30, clock=clock.now)
    for _ in range(5):
        monitor.record_429()
    # Five records equals threshold (not strictly greater) → not saturated.
    assert monitor.is_saturated() is False
    monitor.record_429()
    assert monitor.is_saturated() is True
    clock.advance(31.0)  # past custom 30s window
    assert monitor.is_saturated() is False


def test_thread_safe():
    monitor = RateLimitMonitor(threshold=10_000, window_seconds=3600)

    def worker() -> None:
        for _ in range(10):
            monitor.record_429()

    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert monitor.recent_429_count() == 100
