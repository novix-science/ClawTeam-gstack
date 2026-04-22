"""Plan 07-03 Task 3 — build_digest + bucket_age cluster roll-up (D-07, QUALITY-05)."""
from __future__ import annotations

from pathlib import Path

from clawteam.attention.digest import build_digest, bucket_age
from clawteam.attention.queue import AttentionItem


def _item(
    *,
    sprint_id: str = "s1",
    qid: str = "q",
    tags: tuple[str, ...] = (),
    age_hours: float = 0.5,
    score: float = 10.0,
    reversibility: str = "medium",
) -> AttentionItem:
    return AttentionItem(
        question_path=Path(f"/tmp/{qid}.md"),
        sprint_id=sprint_id,
        team="t",
        title=qid,
        urgency=1,
        blocking=False,
        age_hours=age_hours,
        tags=tags,
        reversibility=reversibility,
        priority_score=score,
    )


def test_bucket_age_boundaries() -> None:
    assert bucket_age(0.0) == "<1h"
    assert bucket_age(0.999) == "<1h"
    assert bucket_age(1.0) == "1-2h"
    assert bucket_age(1.9) == "1-2h"
    assert bucket_age(2.0) == "2-8h"
    assert bucket_age(7.9) == "2-8h"
    assert bucket_age(8.0) == ">8h"
    assert bucket_age(100.0) == ">8h"


def test_digest_empty() -> None:
    assert build_digest([]) == []


def test_digest_groups_by_sprint_and_tag() -> None:
    items = [
        _item(qid="a", tags=("design",)),
        _item(qid="b", tags=("design",)),
        _item(qid="c", tags=("security",)),
    ]
    clusters = build_digest(items)
    # Two clusters — one count=2 (design), one count=1 (security).
    counts = sorted(c["count"] for c in clusters)
    assert counts == [1, 2]
    tags = {c["tag"] for c in clusters}
    assert tags == {"design", "security"}


def test_digest_sorts_by_highest_priority_desc() -> None:
    items = [
        _item(qid="low", tags=("a",), score=5.0),
        _item(qid="high", tags=("b",), score=25.0),
    ]
    clusters = build_digest(items)
    assert clusters[0]["tag"] == "b"
    assert clusters[0]["highest_priority"] == 25.0
    assert clusters[1]["tag"] == "a"


def test_digest_bucket_age_separates_clusters() -> None:
    items = [
        _item(qid="a", tags=("x",), age_hours=0.2),  # <1h
        _item(qid="b", tags=("x",), age_hours=4.0),  # 2-8h
    ]
    clusters = build_digest(items)
    assert len(clusters) == 2
    buckets = sorted(c["age_bucket"] for c in clusters)
    assert buckets == ["2-8h", "<1h"]


def test_digest_untagged_cluster() -> None:
    clusters = build_digest([_item(qid="plain", tags=())])
    assert clusters[0]["tag"] == "untagged"


def test_digest_counts_and_representative_title() -> None:
    items = [
        _item(qid="low-q", tags=("x",), score=5.0),
        _item(qid="high-q", tags=("x",), score=15.0),
    ]
    clusters = build_digest(items)
    assert len(clusters) == 1
    cluster = clusters[0]
    assert cluster["count"] == 2
    # Representative = highest-priority item's title.
    assert cluster["representative_title"] == "high-q"
    assert cluster["highest_priority"] == 15.0


def test_digest_reversibility_distribution() -> None:
    items = [
        _item(qid="a", reversibility="easy", tags=("x",)),
        _item(qid="b", reversibility="hard", tags=("x",)),
        _item(qid="c", reversibility="easy", tags=("x",)),
    ]
    clusters = build_digest(items)
    assert len(clusters) == 1
    dist = clusters[0]["reversibility_distribution"]
    assert dist["easy"] == 2
    assert dist["hard"] == 1
    assert dist["medium"] == 0


def test_digest_schema_fields() -> None:
    clusters = build_digest([_item(qid="x", tags=("design",))])
    assert set(clusters[0].keys()) >= {
        "sprint_id",
        "tag",
        "age_bucket",
        "count",
        "highest_priority",
        "representative_title",
        "reversibility_distribution",
    }
