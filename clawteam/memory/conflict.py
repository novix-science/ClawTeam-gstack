"""Cosine-on-BoW conflict detection — QUALITY-10 (Plan 06-11 Task 2).

Non-blocking per D-10: the /learn write has already succeeded by the time
:func:`detect_conflicts` is consulted. Matching entries are emitted as
:class:`clawteam.events.types.ConflictDetected` events; subscribers
(Phase 7 cost/digest aggregator) surface them for human attention.

Algorithm:

* Tokenize by ``[A-Za-z0-9_]+`` → bag-of-words (multiset, case-folded).
* Only compare against entries sharing at least one tag with
  ``new_entry`` (the ``shared_tags`` bound matches the D-10 contract —
  "contradict on same tag"). This keeps the scan O(same-tag-entries)
  rather than O(all-entries).
* Cosine similarity over the bag-of-words counts. If ≥ ``threshold`` the
  pair emerges as a :class:`ConflictMatch`.

Stdlib only: ``math`` + ``re``. The threshold default (0.75) mirrors the
``gstack.toml [memory] conflict_threshold`` docstring in
:class:`clawteam.events.types.ConflictDetected`. No sentiment-opposition
layer in this plan — cosine-on-BoW is the minimal implementation that
closes Phase 6 Success Criteria #8.

The role argument to :meth:`TeamMemoryStore.list` is preserved so
role-scoped entries stay bucketed per-role (cross-role spill is handled
at the plugin/bus layer, not here).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from clawteam.memory.entry import MemoryEntry
from clawteam.memory.store import TeamMemoryStore

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

DEFAULT_CONFLICT_THRESHOLD: float = 0.75


def _bag_of_words(text: str) -> dict[str, int]:
    """Lowercase token-count bag. Empty text → empty dict (cosine → 0)."""
    bow: dict[str, int] = {}
    for tok in _TOKEN_RE.findall(text.lower()):
        bow[tok] = bow.get(tok, 0) + 1
    return bow


def _cosine(a: dict[str, int], b: dict[str, int]) -> float:
    """Cosine similarity over two bag-of-words dicts.

    Returns 0.0 when either bag is empty so callers never divide by zero.
    """
    if not a or not b:
        return 0.0
    keys = set(a) | set(b)
    dot = sum(a.get(k, 0) * b.get(k, 0) for k in keys)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass(frozen=True)
class ConflictMatch:
    """An existing entry that conflicts with the new entry (D-10)."""

    other_id: str
    similarity: float
    shared_tags: tuple[str, ...]


def detect_conflicts(
    new_entry: MemoryEntry,
    store: TeamMemoryStore,
    *,
    threshold: float = DEFAULT_CONFLICT_THRESHOLD,
) -> list[ConflictMatch]:
    """Return existing entries that conflict with *new_entry*.

    Rules:

    * *new_entry* with no tags → empty list (no tag anchor to scope the
      scan).
    * Candidates are drawn from the same scope/role as *new_entry* (via
      :meth:`TeamMemoryStore.list`) — role-scoped entries do NOT match
      across roles.
    * A candidate qualifies when it shares ≥ 1 tag with *new_entry* AND
      cosine(BoW(body), BoW(candidate.body)) ≥ ``threshold``.
    * Tombstoned entries are already suppressed by ``store.list`` — no
      extra filtering here.
    """
    if not new_entry.tags:
        return []

    new_bow = _bag_of_words(new_entry.body)
    matches: list[ConflictMatch] = []
    new_tags_set = set(new_entry.tags)
    for existing in store.list(scope=new_entry.scope, role=new_entry.role):
        if existing.id == new_entry.id:
            continue
        shared = new_tags_set & set(existing.tags)
        if not shared:
            continue
        sim = _cosine(new_bow, _bag_of_words(existing.body))
        if sim >= threshold:
            matches.append(
                ConflictMatch(
                    other_id=existing.id,
                    similarity=sim,
                    shared_tags=tuple(sorted(shared)),
                )
            )
    return matches


__all__ = [
    "ConflictMatch",
    "DEFAULT_CONFLICT_THRESHOLD",
    "detect_conflicts",
]
