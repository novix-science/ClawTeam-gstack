"""RateLimitMonitor — 429-count-bucketed saturation detector (D-13).

Phase 7 substrate. Conductor consults is_saturated() at start_sprint_async
to decide whether to queue the sprint instead of launching immediately.

Detection is provider-agnostic — relies on caller invoking record_429()
on any 429 response. Does NOT parse X-RateLimit-Remaining headers (some
providers don't emit them). 60-second sliding window is a reasonable
default for Anthropic TPM buckets per research.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

from clawteam.events.bus import EventBus
from clawteam.events.types import RateLimitSaturated


class RateLimitMonitor:
    """Slide a fixed-seconds window of 429 timestamps; flag saturation.

    Thread-safe. Emits :class:`RateLimitSaturated` exactly once per
    un-saturated → saturated transition. Re-emits if the window clears
    and another burst crosses the threshold.

    Saturation semantics: strictly greater than ``threshold`` recent 429s
    (so default threshold=3 triggers on the 4th 429 within 60s).
    """

    def __init__(
        self,
        team_name: str = "",
        *,
        threshold: int = 3,
        window_seconds: int = 60,
        bus: EventBus | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._team = team_name
        self._threshold = int(threshold)
        self._window = float(window_seconds)
        self._bus = bus
        self._clock = clock
        self._events: deque[float] = deque()
        self._lock = threading.RLock()
        self._was_saturated: bool = False

    def record_429(self) -> None:
        """Record one 429 response. Emits an event on each rising edge."""
        with self._lock:
            now = self._clock()
            self._events.append(now)
            self._expire(now)
            is_now = len(self._events) > self._threshold
            if is_now and not self._was_saturated:
                self._was_saturated = True
                self._emit(len(self._events))
            elif not is_now and self._was_saturated:
                # Window cleared between records; rearm for next burst.
                self._was_saturated = False

    def is_saturated(self) -> bool:
        """Return True when >threshold 429s observed in the last window_seconds."""
        with self._lock:
            now = self._clock()
            self._expire(now)
            count = len(self._events)
            saturated = count > self._threshold
            # Self-heal: if previously saturated but window cleared, rearm.
            if not saturated and self._was_saturated:
                self._was_saturated = False
            return saturated

    def recent_429_count(self) -> int:
        """Return the number of 429s within the current sliding window."""
        with self._lock:
            now = self._clock()
            self._expire(now)
            return len(self._events)

    # ── internals ─────────────────────────────────────────────────────

    def _expire(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0] < cutoff:
            self._events.popleft()

    def _emit(self, count: int) -> None:
        if self._bus is None:
            return
        try:
            self._bus.emit(
                RateLimitSaturated(
                    team_name=self._team,
                    recent_429_count=count,
                    threshold=self._threshold,
                    window_seconds=int(self._window),
                )
            )
        except Exception:  # pragma: no cover — defensive; emit must never crash
            pass


__all__ = ["RateLimitMonitor"]
