"""Attention substrate — cross-sprint AttentionQueue + watcher + digest.

Phase 7 Wave 2 public API (Plan 07-03):
  - :class:`AttentionItem` + :class:`AttentionQueue` + :func:`compute_priority`
    + :data:`URGENCY_MAP` — stateless read-side priority queue (D-04/D-05).
  - :class:`AttentionWatcher` + :func:`make_watcher` + :func:`watchdog_available`
    — optional-extra auto-refresh with polling fallback (D-06).
  - :func:`build_digest` + :func:`bucket_age` — ``--summary`` cluster roll-up
    grouping by (sprint, tag, age bucket) (D-07, QUALITY-05).

Lives at top level (not under templates/gstack/) because the substrate
is generic — a non-gstack template could read its own question/answer
artifact layout.
"""
from __future__ import annotations

from clawteam.attention.auto_accept import (
    DEFAULT_TTL_MINUTES,
    apply_auto_accept,
    preview_auto_accept,
)
from clawteam.attention.digest import build_digest, bucket_age
from clawteam.attention.queue import (
    URGENCY_MAP,
    AttentionItem,
    AttentionQueue,
    compute_priority,
)
from clawteam.attention.watcher import (
    AttentionWatcher,
    make_watcher,
    watchdog_available,
)

__all__ = [
    "AttentionItem",
    "AttentionQueue",
    "AttentionWatcher",
    "DEFAULT_TTL_MINUTES",
    "URGENCY_MAP",
    "apply_auto_accept",
    "build_digest",
    "bucket_age",
    "compute_priority",
    "make_watcher",
    "preview_auto_accept",
    "watchdog_available",
]
