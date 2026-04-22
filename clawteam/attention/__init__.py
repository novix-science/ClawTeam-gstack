"""Attention substrate — cross-sprint AttentionQueue + watcher + digest.

Phase 7 Wave 0: package marker only. Public API (AttentionQueue,
AttentionItem, watchdog_available, build_digest) is added by Plans
07-03 and 07-04.

Lives at top level (not under templates/gstack/) because the substrate
is generic — a non-gstack template could read its own question/answer
artifact layout.
"""
from __future__ import annotations

__all__: list[str] = []
