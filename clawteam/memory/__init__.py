"""Team memory substrate — append-only JSONL store with provenance + decay.

Phase 6 Wave 0 (Plan 06-01 Task 2): this module is a package marker only.
Public API (``MemoryEntry``, ``TeamMemoryStore``, ``rank``,
``detect_conflict``, ``backfill_scan``) is added by Plans 06-02, 06-03,
06-10, 06-11.

The package lives at the top level (not under ``templates/gstack/``)
because the substrate is generic — a non-gstack template could
instantiate ``TeamMemoryStore`` directly. Only the ``/learn`` skill
surface is gstack-specific.
"""

from __future__ import annotations

__all__: list[str] = []
