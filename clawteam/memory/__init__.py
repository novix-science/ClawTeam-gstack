"""Team memory substrate — append-only JSONL store with provenance + decay.

Public API (Plan 06-02):

* :class:`MemoryEntry` — pydantic schema for one append-unit record.
* :class:`TeamMemoryStore` — per-team JSONL store with write / list / prune.

Additional surface (search, ranking, conflict detection, backfill) lands in
Plans 06-03 / 06-10 / 06-11 and imports these symbols.

The package lives at the top level (not under ``templates/gstack/``) because
the substrate is generic — a non-gstack template could instantiate
``TeamMemoryStore`` directly. Only the ``/learn`` skill surface is
gstack-specific.
"""

from __future__ import annotations

from clawteam.memory.entry import MemoryEntry
from clawteam.memory.store import TeamMemoryStore

__all__ = ["MemoryEntry", "TeamMemoryStore"]
