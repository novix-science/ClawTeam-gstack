"""Memory search + ranking (D-06, MEM-03, MEM-05, MEM-07).

Grep-first retrieval: stdlib :func:`re.search` over JSONL entries enumerated
via :meth:`TeamMemoryStore.list`. Ranking formula per D-06 is fully
transparent — ``score = recency × provenance × decay`` — so users can debug
why an entry ranks low by eyeballing the three components via
``/learn search --explain`` (Plan 06-10).

Expired entries (``decay_factor < 1.0``) never drop to zero — they rank at
the bottom but remain discoverable (MEM-07 floor).

Provenance weights (D-06 + MEM-05):

===============================  ======
source                            weight
===============================  ======
user + evidence                    2.0
user, no evidence                  1.2
artifact + evidence                1.0
artifact, no evidence              0.6   (flagged per MEM-05, never zeroed)
sprint-reflect                     0.8
self-inferred                      0.3
===============================  ======

Recency weight:  ``1 / (1 + days_since / 30)`` — decays smoothly, never
negative, never zero. Malformed timestamps → ``0.1`` (defensive; matches
decay.py's defensive 0.05 floor).

Regex safety: the caller's ``query`` string is ``re.escape`` d so that user
input becomes a literal — no catastrophic-backtracking risk (T-06-03-01).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from clawteam.memory.decay import decay_factor

if TYPE_CHECKING:
    from clawteam.memory.entry import MemoryEntry
    from clawteam.memory.store import TeamMemoryStore
    from clawteam.templates import MemoryConfig


@dataclass(frozen=True)
class SearchResult:
    """One search hit with its composite score + the 3 factor components.

    The three components are kept around so ``/learn search --explain``
    (Plan 06-10) can show *why* an entry ranks low — e.g. a user can see
    that the entry is within TTL (decay=1.0), fresh (recency=0.95), but
    was self-inferred (provenance=0.3) and therefore ranks near the bottom
    despite being recent.
    """

    entry: "MemoryEntry"
    score: float
    recency: float
    provenance: float
    decay: float


def recency_weight(timestamp: str, now: datetime) -> float:
    """Recency factor = ``1 / (1 + days_since / 30)``.

    Fresh (0 days) → 1.0; 30 days → 0.5; 90 days → 0.25; 365 days → ~0.08.
    Malformed timestamps default to 0.1 (matches decay.py's defensive
    posture — never crash, just deprioritise).
    """
    try:
        then = datetime.fromisoformat(timestamp)
    except ValueError:
        return 0.1
    days = max(0.0, (now - then).total_seconds() / 86400.0)
    return 1.0 / (1.0 + days / 30.0)


def provenance_weight(entry: "MemoryEntry") -> float:
    """Provenance factor per D-06 + MEM-05.

    ================================  ======
    learned_from + evidence present    weight
    ================================  ======
    user + evidence                    2.0
    user, no evidence                  1.2
    artifact + evidence                1.0
    artifact, no evidence              0.6 (MEM-05: flagged, not zeroed)
    sprint-reflect                     0.8
    self-inferred                      0.3
    ================================  ======
    """
    has_evidence = bool(entry.evidence)
    if entry.learned_from == "user" and has_evidence:
        return 2.0
    if entry.learned_from == "user" and not has_evidence:
        # User claim without citation — still more trusted than an
        # un-cited artifact scrape, but less than a cited one.
        return 1.2
    if entry.learned_from == "artifact" and has_evidence:
        return 1.0
    if entry.learned_from == "artifact" and not has_evidence:
        return 0.6  # MEM-05: flagged, not zeroed
    if entry.learned_from == "sprint-reflect":
        return 0.8
    # self-inferred (catch-all)
    return 0.3


def rank(
    entry: "MemoryEntry",
    now: datetime | None = None,
    *,
    memory_config: "MemoryConfig | None" = None,
) -> SearchResult:
    """Return (entry, composite score, and 3 component factors).

    ``score = recency × provenance × decay`` (D-06). All three components
    are preserved on the :class:`SearchResult` for ``--explain`` output
    (Plan 06-10).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    r = recency_weight(entry.timestamp, now)
    p = provenance_weight(entry)
    d = decay_factor(entry, now, memory_config=memory_config)
    return SearchResult(
        entry=entry,
        score=r * p * d,
        recency=r,
        provenance=p,
        decay=d,
    )


def search(
    store: "TeamMemoryStore",
    query: str,
    *,
    scope: Literal["team", "role"] = "team",
    tag: str | None = None,
    role: str | None = None,
    memory_config: "MemoryConfig | None" = None,
    now: datetime | None = None,
) -> list[SearchResult]:
    """Grep-first keyword retrieval ranked by recency × provenance × decay.

    Parameters
    ----------
    store:
        The :class:`TeamMemoryStore` to enumerate. ``store.list`` is the
        sole disk read path — this function never touches JSONL files
        directly.
    query:
        Case-insensitive literal search term. Empty string → no keyword
        filter (scope + tag still apply). Regex metacharacters are escaped
        so the query is treated as a literal (T-06-03-01 mitigation).
    scope:
        ``"team"`` or ``"role"`` — passed through to ``store.list``.
    tag:
        Optional tag filter. When provided, only entries whose ``tags``
        list contains *tag* are returned.
    role:
        Required when ``scope == "role"``.
    memory_config:
        Optional :class:`MemoryConfig` override for decay TTLs.
    now:
        Reference "now" for deterministic testing. Defaults to
        :func:`datetime.now` in UTC.

    Returns
    -------
    list[SearchResult]
        Entries sorted by composite score **descending**. Expired entries
        rank last but are never filtered out (MEM-07 floor).
    """
    if now is None:
        now = datetime.now(timezone.utc)

    entries = store.list(scope=scope, tag=tag, role=role)

    if query:
        # Escape regex metachars — grep behavior, not a regex surface.
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        entries = [
            e
            for e in entries
            if pattern.search(e.title) or pattern.search(e.body)
        ]

    scored = [rank(e, now, memory_config=memory_config) for e in entries]
    scored.sort(key=lambda r: r.score, reverse=True)
    return scored


__all__ = [
    "SearchResult",
    "provenance_weight",
    "rank",
    "recency_weight",
    "search",
]
