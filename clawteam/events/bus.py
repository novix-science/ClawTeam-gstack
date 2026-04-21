"""Synchronous publish-subscribe event bus for ClawTeam."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from clawteam.events.types import HarnessEvent

# ── Event type registry (plugins can register custom event types) ─────
#
# Deviation (Plan 05-02, Rule 3 — blocking): the previous top-level import
# ``from clawteam.events.types import HarnessEvent`` made ``types.py`` unable
# to call ``register_event_type`` at module load. Phase 5 Plan 05-02 requires
# the module-bottom registration calls (acceptance criteria + key_links
# frontmatter pattern). Deferring the runtime import into resolve_event_type
# + TYPE_CHECKING-gating the annotations breaks the cycle without changing
# any public API.

_EVENT_TYPE_REGISTRY: dict[str, type[HarnessEvent]] = {}


def register_event_type(cls: type[HarnessEvent]) -> None:
    """Register a custom event type so shell hooks can reference it by name."""
    _EVENT_TYPE_REGISTRY[cls.__name__] = cls


def resolve_event_type(name: str) -> type[HarnessEvent] | None:
    """Resolve an event class by name. Checks registry first, then types module."""
    if name in _EVENT_TYPE_REGISTRY:
        return _EVENT_TYPE_REGISTRY[name]
    # Lazy imports — types.py imports register_event_type from this module
    # at load time (Phase 5 Plan 05-02), so we cannot import HarnessEvent at
    # module top. types is guaranteed fully loaded by the time any caller
    # invokes resolve_event_type (all callers are post-init).
    from clawteam.events import types as _types
    from clawteam.events.types import HarnessEvent as _HarnessEvent
    cls = getattr(_types, name, None)
    if cls is not None and isinstance(cls, type) and issubclass(cls, _HarnessEvent):
        return cls
    return None

# ``HarnessEvent`` is TYPE_CHECKING-gated to break the types.py ↔ bus.py
# circular-import cycle (Plan 05-02). Use a string forward-ref so the
# assignment evaluates without a runtime resolution of HarnessEvent.
Handler = Callable[["HarnessEvent"], Any]


class _Subscription:
    __slots__ = ("handler", "priority")

    def __init__(self, handler: Handler, priority: int):
        self.handler = handler
        self.priority = priority


class EventBus:
    """Central event bus for ClawTeam.

    Handlers are called synchronously in priority order (lower = earlier).
    Use ``emit_async`` for fire-and-forget notifications.
    """

    def __init__(self) -> None:
        self._subscribers: dict[type, list[_Subscription]] = {}
        self._lock = threading.RLock()
        self._pool: ThreadPoolExecutor | None = None

    # ── subscribe / unsubscribe ───────────────────────────────────────

    def subscribe(
        self,
        event_type: type[HarnessEvent],
        handler: Handler,
        priority: int = 0,
    ) -> None:
        """Register *handler* for *event_type*.

        Handlers with lower ``priority`` values run first.
        """
        with self._lock:
            subs = self._subscribers.setdefault(event_type, [])
            subs.append(_Subscription(handler, priority))
            subs.sort(key=lambda s: s.priority)

    def unsubscribe(
        self,
        event_type: type[HarnessEvent],
        handler: Handler,
    ) -> None:
        """Remove a previously registered handler."""
        with self._lock:
            subs = self._subscribers.get(event_type)
            if subs:
                self._subscribers[event_type] = [
                    s for s in subs if s.handler is not handler
                ]

    # ── emit ──────────────────────────────────────────────────────────

    def emit(self, event: HarnessEvent) -> list[Any]:
        """Emit an event synchronously. Returns list of handler results.

        For ``Before*`` events, handlers can set ``event.veto = True``
        to signal cancellation (caller must check).
        """
        with self._lock:
            subs = list(self._subscribers.get(type(event), []))
        results: list[Any] = []
        for sub in subs:
            try:
                result = sub.handler(event)
                results.append(result)
            except Exception:
                pass  # handlers must not crash the bus
        return results

    def emit_async(self, event: HarnessEvent) -> None:
        """Emit an event in a background thread (fire-and-forget)."""
        if self._pool is None:
            self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="clawteam-events")
        self._pool.submit(self.emit, event)

    # ── introspection ─────────────────────────────────────────────────

    def handler_count(self, event_type: type[HarnessEvent] | None = None) -> int:
        """Return number of registered handlers, optionally filtered by type."""
        with self._lock:
            if event_type is not None:
                return len(self._subscribers.get(event_type, []))
            return sum(len(subs) for subs in self._subscribers.values())

    def clear(self) -> None:
        """Remove all subscribers."""
        with self._lock:
            self._subscribers.clear()
