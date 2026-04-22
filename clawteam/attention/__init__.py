"""Attention substrate — cross-sprint AttentionQueue + watcher + digest.

Phase 7 Wave 2 public API (Plan 07-03): AttentionItem + AttentionQueue +
compute_priority + URGENCY_MAP. Watcher + digest land in Tasks 2/3 of
this plan and extend the __all__ list.

Lives at top level (not under templates/gstack/) because the substrate
is generic — a non-gstack template could read its own question/answer
artifact layout.
"""
from __future__ import annotations

from clawteam.attention.queue import (
    URGENCY_MAP,
    AttentionItem,
    AttentionQueue,
    compute_priority,
)

__all__ = [
    "AttentionItem",
    "AttentionQueue",
    "URGENCY_MAP",
    "compute_priority",
]
