"""AttentionWatcher — watchdog optional + 2-second polling fallback (D-06).

D-06 invariants (test-locked):
  - ``watchdog_available()`` uses :func:`importlib.util.find_spec` only;
    importing this module must NOT pull watchdog into ``sys.modules``.
  - When watchdog is absent, :class:`AttentionWatcher` transparently falls
    back to ``interval_seconds`` polling (default 2.0s) and re-fires
    ``on_change`` only when the AttentionQueue snapshot actually differs.
"""
from __future__ import annotations

import logging
import threading
from importlib.util import find_spec
from typing import Callable, Optional

from clawteam.attention.queue import AttentionItem, AttentionQueue

_LOG = logging.getLogger(__name__)


def watchdog_available() -> bool:
    """Return True if the optional ``watchdog`` package is importable.

    Zero import-time side effects — mirrors the Phase 6
    :func:`clawteam.browser.playwright_available` pattern exactly so the
    optional [attend] extra stays optional at import time.
    """
    return find_spec("watchdog") is not None


class AttentionWatcher:
    """Fire a callback whenever the AttentionQueue state changes.

    Two modes:
      - ``'watchdog'``: FS events via the optional watchdog package (low latency).
      - ``'polling'`` : poll every ``interval_seconds`` and diff snapshots.

    Both modes call ``on_change(items: list[AttentionItem])`` synchronously
    from their internal thread. Callbacks should be fast or hand off to a
    queue — a slow callback will delay the next polling iteration.
    """

    def __init__(
        self,
        queue: AttentionQueue,
        on_change: Callable[[list[AttentionItem]], None],
        *,
        mode: str = "auto",  # "auto" | "polling" | "watchdog"
        interval_seconds: float = 2.0,
    ) -> None:
        self._queue = queue
        self._on_change = on_change
        self._interval = float(interval_seconds)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._observer = None  # watchdog Observer when mode='watchdog'
        if mode == "auto":
            # Look up via module to allow monkeypatching
            # clawteam.attention.watcher.watchdog_available in tests.
            import clawteam.attention.watcher as _self_mod

            mode = "watchdog" if _self_mod.watchdog_available() else "polling"
        self.mode = mode

    def start(self) -> None:
        """Start watching. Idempotent — safe to call repeatedly."""
        if self._thread is not None and self._thread.is_alive():
            return
        if self._observer is not None:
            return
        self._stop_event.clear()
        import clawteam.attention.watcher as _self_mod

        if self.mode == "watchdog" and _self_mod.watchdog_available():
            self._start_watchdog()
        else:
            self._start_polling()

    def stop(self) -> None:
        """Stop watching. Blocks until worker exits (2s timeout)."""
        self._stop_event.set()
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2.0)
            except Exception:  # pragma: no cover — defensive
                pass
            self._observer = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ── internals ────────────────────────────────────────────────

    def _start_polling(self) -> None:
        last: Optional[tuple[str, ...]] = None

        def loop() -> None:
            nonlocal last
            while not self._stop_event.is_set():
                try:
                    items = self._queue.snapshot()
                    # Digest by (path, mtime-bucket) so identical snapshots
                    # don't re-fire. Score shifts slightly each poll due to
                    # age_hours drift — round to 0.001h so we don't spam.
                    digest = tuple(
                        sorted(
                            f"{i.question_path}:{round(i.age_hours, 3)}"
                            for i in items
                        )
                    )
                    if digest != last:
                        last = digest
                        try:
                            self._on_change(items)
                        except Exception:
                            _LOG.exception(
                                "AttentionWatcher on_change raised; continuing"
                            )
                except Exception:
                    _LOG.exception("AttentionWatcher poll raised; continuing")
                self._stop_event.wait(self._interval)

        self._thread = threading.Thread(
            target=loop, daemon=True, name="attend-polling"
        )
        self._thread.start()

    def _start_watchdog(self) -> None:
        try:
            # Import ONLY here — keeps find_spec-only guarantee at module level.
            from watchdog.observers import Observer  # type: ignore[import-not-found]
            from watchdog.events import (  # type: ignore[import-not-found]
                FileSystemEventHandler,
            )
        except Exception:  # pragma: no cover — defensive
            self.mode = "polling"
            self._start_polling()
            return

        outer = self

        class _Handler(FileSystemEventHandler):
            def on_any_event(self, event) -> None:
                try:
                    items = outer._queue.snapshot()
                    outer._on_change(items)
                except Exception:
                    _LOG.exception(
                        "AttentionWatcher watchdog on_change raised; continuing"
                    )

        teams_dir = outer._queue.data_dir / "teams"
        teams_dir.mkdir(parents=True, exist_ok=True)
        self._observer = Observer()
        self._observer.schedule(_Handler(), str(teams_dir), recursive=True)
        self._observer.start()


def make_watcher(
    queue: AttentionQueue,
    on_change: Callable[[list[AttentionItem]], None],
    *,
    interval_seconds: float = 2.0,
) -> AttentionWatcher:
    """Factory — auto-picks watchdog if available; else polling."""
    return AttentionWatcher(
        queue, on_change, mode="auto", interval_seconds=interval_seconds
    )


__all__ = ["AttentionWatcher", "make_watcher", "watchdog_available"]
