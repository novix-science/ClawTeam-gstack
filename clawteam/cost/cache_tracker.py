"""CacheTracker — cache-hit-rate accumulator over ClaudeApiResponse events (D-12).

``cache_hit_rate = cache_read_tokens / (cache_read_tokens + cache_creation_tokens)``
per team. Above-50% is considered healthy per
``07-CONTEXT.md`` D-12.

Listens on :class:`~clawteam.events.bus.EventBus` for
:class:`~clawteam.events.types.ClaudeApiResponse` events. Emits nothing
itself — dashboard consumers (Plan 07-07 ``clawteam team show``) pull via
:meth:`CacheTracker.cache_hit_rate` at render time.

**Scope boundary:** the tracker keeps running aggregates of cache-read
and cache-creation token counts; it does NOT retain raw events (per
Pitfall 4 mitigation — memory is O(1) regardless of event count). A
separate instance per team — multiple trackers can share a single bus
because the ``team_name`` filter rejects cross-team events.
"""
from __future__ import annotations

import threading
from typing import Callable, Optional

from clawteam.events.bus import EventBus
from clawteam.events.types import ClaudeApiResponse

HEALTHY_THRESHOLD: float = 0.5


class CacheTracker:
    """Per-team cache-hit-rate aggregator.

    :param team: Team name — only events with matching ``team_name`` are
        counted, so multiple trackers can share a single bus without
        cross-talk.
    :param bus: Optional :class:`EventBus` — when supplied, the tracker
        subscribes to ``ClaudeApiResponse`` events on construction.
        Tests that want to feed the handler directly can pass ``None``
        and invoke :meth:`_on_response` manually.
    """

    def __init__(
        self,
        team: str,
        *,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._team = team
        self._lock = threading.RLock()
        self._total_read: int = 0
        self._total_creation: int = 0
        self._bus = bus
        # Pin the bound-method ref so ``close()`` can unsubscribe with
        # an identity match (bound methods are recreated on each
        # ``self.m`` access; passing a fresh one to ``unsubscribe``
        # would never match the stored subscription).
        self._handler: Optional[Callable[[ClaudeApiResponse], None]] = None
        if bus is not None:
            self._handler = self._on_response
            bus.subscribe(ClaudeApiResponse, self._handler)

    # ── public API ────────────────────────────────────────────────────

    @property
    def team(self) -> str:
        return self._team

    def cache_hit_rate(self) -> float:
        """Return current cache-hit-rate in ``[0.0, 1.0]``.

        Divide-by-zero safe: returns ``0.0`` when no events observed.
        """
        with self._lock:
            denom = self._total_read + self._total_creation
            if denom <= 0:
                return 0.0
            return self._total_read / denom

    def is_healthy(self) -> bool:
        """Return ``True`` when :meth:`cache_hit_rate` > :data:`HEALTHY_THRESHOLD`.

        Strict ``>`` (not ``>=``): exactly 0.5 is break-even, not
        sustained cache use.
        """
        return self.cache_hit_rate() > HEALTHY_THRESHOLD

    def total_cache_read(self) -> int:
        """Return cumulative ``cache_read_tokens`` observed for this team."""
        with self._lock:
            return self._total_read

    def total_cache_creation(self) -> int:
        """Return cumulative ``cache_creation_tokens`` observed for this team."""
        with self._lock:
            return self._total_creation

    def close(self) -> None:
        """Unsubscribe this tracker's handler from the event bus.

        Deterministic teardown — callers that construct a tracker for a
        bounded scope (e.g. short-lived CLI invocations) MUST call
        ``close()`` (or use the context-manager protocol) to avoid
        leaking one handler per invocation on the global event bus.
        """
        if self._bus is not None and self._handler is not None:
            self._bus.unsubscribe(ClaudeApiResponse, self._handler)
            self._handler = None

    def __enter__(self) -> "CacheTracker":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ── event handler ─────────────────────────────────────────────────

    def _on_response(self, event: ClaudeApiResponse) -> None:
        if event.team_name != self._team:
            return
        with self._lock:
            self._total_read += int(event.cache_read_tokens)
            self._total_creation += int(event.cache_creation_tokens)


__all__ = ["CacheTracker", "HEALTHY_THRESHOLD"]
