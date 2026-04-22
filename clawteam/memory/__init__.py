"""Team memory substrate — append-only JSONL store with provenance + decay.

Public API:

* :class:`MemoryEntry` — pydantic schema for one append-unit record (06-02).
* :class:`TeamMemoryStore` — per-team JSONL store with write / list / prune
  (06-02).
* :func:`decay_factor` — per-tag TTL decay (D-06, 06-03).
* :func:`rank` + :func:`search` + :class:`SearchResult` — keyword retrieval
  ranked by ``recency × provenance × decay`` (D-06, 06-03).

Further surface (conflict detection, high-impact gate, backfill) lands in
Plan 06-11 and imports from these modules.

The package lives at the top level (not under ``templates/gstack/``) because
the substrate is generic — a non-gstack template could instantiate
``TeamMemoryStore`` directly. Only the ``/learn`` skill surface is
gstack-specific.
"""

from __future__ import annotations

from clawteam.memory.decay import decay_factor
from clawteam.memory.entry import MemoryEntry
from clawteam.memory.high_impact_gate import (
    HIGH_IMPACT_TAG,
    check_high_impact,
    stage_pending,
)
from clawteam.memory.search import SearchResult, rank, search
from clawteam.memory.store import TeamMemoryStore

__all__ = [
    "MemoryEntry",
    "TeamMemoryStore",
    "SearchResult",
    "decay_factor",
    "rank",
    "search",
    # Plan 06-11:
    "HIGH_IMPACT_TAG",
    "check_high_impact",
    "stage_pending",
]
