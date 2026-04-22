"""Attention digest — group questions by (sprint, tag, age bucket) (D-07, QUALITY-05).

Surface the ``--summary`` roll-up view: "4 sprints stalled >2h, 1 CRITICAL,
2 reversible auto-accept candidates". Plain-text; no TUI widgets.

The output is a list of cluster dicts — keeping it plain dict (not dataclass)
lets Plan 07-04's CLI serialize directly to JSON via ``--json`` without
custom encoders.
"""
from __future__ import annotations

from typing import Any

from clawteam.attention.queue import AttentionItem


def bucket_age(age_hours: float) -> str:
    """Return the D-07 age bucket label for an AttentionItem.

    Buckets: '<1h' | '1-2h' | '2-8h' | '>8h'. Boundaries are half-open
    on the right so age==1.0 is "1-2h", age==2.0 is "2-8h", age==8.0 is ">8h".
    """
    if age_hours < 1.0:
        return "<1h"
    if age_hours < 2.0:
        return "1-2h"
    if age_hours < 8.0:
        return "2-8h"
    return ">8h"


def build_digest(items: list[AttentionItem]) -> list[dict[str, Any]]:
    """Group items by (sprint_id, tag_cluster, age_bucket); sort clusters desc.

    Cluster schema::

        {
          'sprint_id': str,
          'tag': str,                 # first tag of items in cluster, or 'untagged'
          'age_bucket': str,          # bucket_age() result
          'count': int,
          'highest_priority': float,
          'representative_title': str,
          'reversibility_distribution': {'easy': int, 'medium': int, 'hard': int},
        }

    Ordering: sorted by ``highest_priority`` descending so the first cluster
    shown in a digest surface is the one the user should act on first.
    """
    if not items:
        return []

    clusters: dict[tuple[str, str, str], list[AttentionItem]] = {}
    for item in items:
        tag_cluster = item.tags[0] if item.tags else "untagged"
        key = (item.sprint_id, tag_cluster, bucket_age(item.age_hours))
        clusters.setdefault(key, []).append(item)

    def _rev_dist(cluster: list[AttentionItem]) -> dict[str, int]:
        dist = {"easy": 0, "medium": 0, "hard": 0}
        for it in cluster:
            if it.reversibility in dist:
                dist[it.reversibility] += 1
        return dist

    result: list[dict[str, Any]] = []
    for (sprint_id, tag, bucket), cluster in clusters.items():
        top = max(cluster, key=lambda i: i.priority_score)
        result.append(
            {
                "sprint_id": sprint_id,
                "tag": tag,
                "age_bucket": bucket,
                "count": len(cluster),
                "highest_priority": top.priority_score,
                "representative_title": top.title,
                "reversibility_distribution": _rev_dist(cluster),
            }
        )
    result.sort(key=lambda r: r["highest_priority"], reverse=True)
    return result


__all__ = ["build_digest", "bucket_age"]
