"""Tests for memory search + ranking (Plan 06-03 Task 2).

17 tests covering:
 - recency_weight (1 / (1 + days/30)) including edge cases
 - provenance_weight for all 5 learned_from buckets + evidence gating
 - rank() composite = recency × provenance × decay (D-06)
 - search() keyword matching on title + body (case-insensitive, grep-safe)
 - search() respects scope + tag + role filters
 - expired entries rank below fresh ones but are NEVER filtered (MEM-07 floor)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from clawteam.memory.decay import decay_factor
from clawteam.memory.entry import MemoryEntry
from clawteam.memory.search import (
    SearchResult,
    provenance_weight,
    rank,
    recency_weight,
    search,
)
from clawteam.memory.store import TeamMemoryStore


NOW = datetime(2026, 4, 22, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path, monkeypatch):
    """Fresh TeamMemoryStore rooted at tmp_path (cross-test isolation)."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return TeamMemoryStore("teamA")


def _make_entry(
    *,
    title: str,
    body: str = "",
    tags: list[str] | None = None,
    learned_from: str = "artifact",
    evidence: str = "",
    scope: str = "team",
    role: str | None = None,
    days_ago: float = 1,
    id_suffix: str = "abc123",
) -> MemoryEntry:
    ts = (NOW - timedelta(days=days_ago)).isoformat()
    return MemoryEntry(
        id=f"mem-teamA-20260422-{id_suffix}",
        author="engineer@sprint-1",
        title=title,
        body=body,
        tags=list(tags or ["pattern"]),
        learned_from=learned_from,
        evidence=evidence,
        scope=scope,
        role=role,
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# Test 1 — recency decays smoothly with age
# ---------------------------------------------------------------------------


def test_recency_weight_recent_high():
    fresh_ts = NOW.isoformat()
    thirty_ts = (NOW - timedelta(days=30)).isoformat()
    ninety_ts = (NOW - timedelta(days=90)).isoformat()

    assert recency_weight(fresh_ts, NOW) == pytest.approx(1.0, abs=0.01)
    assert recency_weight(thirty_ts, NOW) == pytest.approx(0.5, abs=0.01)
    assert recency_weight(ninety_ts, NOW) == pytest.approx(0.25, abs=0.01)


# ---------------------------------------------------------------------------
# Test 2 — recency never returns zero / negative
# ---------------------------------------------------------------------------


def test_recency_weight_clamped():
    ancient_ts = (NOW - timedelta(days=365 * 50)).isoformat()
    w = recency_weight(ancient_ts, NOW)
    assert w > 0.0
    assert w < 0.01  # very small but positive


# ---------------------------------------------------------------------------
# Test 3 — malformed timestamp defensively → 0.1
# ---------------------------------------------------------------------------


def test_recency_weight_malformed_ts():
    assert recency_weight("not-an-iso", NOW) == 0.1


# ---------------------------------------------------------------------------
# Test 4 — user + evidence → 2.0
# ---------------------------------------------------------------------------


def test_provenance_weight_user_with_evidence():
    e = _make_entry(
        title="user pattern",
        learned_from="user",
        evidence="src/x.py:12",
    )
    assert provenance_weight(e) == 2.0


# ---------------------------------------------------------------------------
# Test 5 — artifact + evidence → 1.0
# ---------------------------------------------------------------------------


def test_provenance_weight_artifact_with_evidence():
    e = _make_entry(
        title="artifact pattern",
        learned_from="artifact",
        evidence="docs/rfc.md",
    )
    assert provenance_weight(e) == 1.0


# ---------------------------------------------------------------------------
# Test 6 — artifact WITHOUT evidence → 0.6 (flagged per MEM-05, not zeroed)
# ---------------------------------------------------------------------------


def test_provenance_weight_artifact_no_evidence():
    e = _make_entry(
        title="unsourced artifact",
        learned_from="artifact",
        evidence="",
    )
    assert provenance_weight(e) == 0.6


# ---------------------------------------------------------------------------
# Test 7 — self-inferred → 0.3 (regardless of evidence)
# ---------------------------------------------------------------------------


def test_provenance_weight_self_inferred():
    e_no_ev = _make_entry(
        title="inference", learned_from="self-inferred", evidence=""
    )
    e_with_ev = _make_entry(
        title="inference", learned_from="self-inferred", evidence="src/x.py"
    )
    assert provenance_weight(e_no_ev) == 0.3
    assert provenance_weight(e_with_ev) == 0.3


# ---------------------------------------------------------------------------
# Test 8 — sprint-reflect backfill → 0.8
# ---------------------------------------------------------------------------


def test_provenance_weight_sprint_reflect():
    e = _make_entry(
        title="reflection", learned_from="sprint-reflect", evidence=""
    )
    assert provenance_weight(e) == 0.8


# ---------------------------------------------------------------------------
# Test 9 — rank() multiplies the three components
# ---------------------------------------------------------------------------


def test_rank_multiplies_three():
    e = _make_entry(
        title="composite",
        learned_from="user",
        evidence="src/x.py:1",
        tags=["pattern"],
        days_ago=30,
    )
    result = rank(e, NOW)
    expected_r = recency_weight(e.timestamp, NOW)
    expected_p = provenance_weight(e)
    expected_d = decay_factor(e, NOW)
    assert isinstance(result, SearchResult)
    assert result.recency == pytest.approx(expected_r)
    assert result.provenance == pytest.approx(expected_p)
    assert result.decay == pytest.approx(expected_d)
    assert result.score == pytest.approx(
        expected_r * expected_p * expected_d
    )


# ---------------------------------------------------------------------------
# Test 10 — keyword match on title only
# ---------------------------------------------------------------------------


def test_search_keyword_matches_title(store):
    store.write(
        _make_entry(title="async queue pattern", id_suffix="aaa001")
    )
    store.write(_make_entry(title="sync lock bug", id_suffix="aaa002"))
    results = search(store, "async")
    assert len(results) == 1
    assert results[0].entry.title == "async queue pattern"


# ---------------------------------------------------------------------------
# Test 11 — keyword match on body
# ---------------------------------------------------------------------------


def test_search_keyword_matches_body(store):
    store.write(
        _make_entry(
            title="queue", body="handle backpressure", id_suffix="bbb001"
        )
    )
    store.write(
        _make_entry(
            title="queue", body="handle retry logic", id_suffix="bbb002"
        )
    )
    results = search(store, "backpressure")
    assert len(results) == 1
    assert "backpressure" in results[0].entry.body


# ---------------------------------------------------------------------------
# Test 12 — case-insensitive matching
# ---------------------------------------------------------------------------


def test_search_case_insensitive(store):
    store.write(
        _make_entry(title="async queue pattern", id_suffix="ccc001")
    )
    results = search(store, "ASYNC")
    assert len(results) == 1


# ---------------------------------------------------------------------------
# Test 13 — higher rank (user+evidence) sorts before self-inferred
# ---------------------------------------------------------------------------


def test_search_orders_by_rank_desc(store):
    # Same body, same decay, different provenance → user+ev > self-inferred
    entry_a = _make_entry(
        title="thing",
        body="common body",
        learned_from="user",
        evidence="src/x.py:1",
        id_suffix="ddd001",
        days_ago=1,
    )
    entry_b = _make_entry(
        title="thing",
        body="common body",
        learned_from="self-inferred",
        evidence="",
        id_suffix="ddd002",
        days_ago=1,
    )
    store.write(entry_b)  # write B first to make sure order is not insertion-based
    store.write(entry_a)
    results = search(store, "common")
    assert len(results) == 2
    assert results[0].entry.id == entry_a.id
    assert results[1].entry.id == entry_b.id
    assert results[0].score > results[1].score


# ---------------------------------------------------------------------------
# Test 14 — tag filter narrows results
# ---------------------------------------------------------------------------


def test_search_respects_tag_filter(store):
    store.write(_make_entry(title="pat1", tags=["pattern"], id_suffix="eee001"))
    store.write(_make_entry(title="pat2", tags=["pattern"], id_suffix="eee002"))
    store.write(_make_entry(title="inc1", tags=["incident"], id_suffix="eee003"))
    results = search(store, "", tag="pattern")
    assert len(results) == 2
    assert all("pattern" in r.entry.tags for r in results)


# ---------------------------------------------------------------------------
# Test 15 — expired entries ranked last, never filtered out (MEM-07 floor)
# ---------------------------------------------------------------------------


def test_search_expired_ranks_below_unexpired(store):
    fresh = _make_entry(
        title="freshp",
        body="same body",
        tags=["pattern"],
        days_ago=30,
        id_suffix="fff001",
    )
    # 400 days old pattern is past 2x TTL (180), so decay = 0.05
    expired = _make_entry(
        title="oldp",
        body="same body",
        tags=["pattern"],
        days_ago=400,
        id_suffix="fff002",
    )
    store.write(fresh)
    store.write(expired)
    results = search(store, "same", now=NOW)
    assert len(results) == 2  # expired still present
    assert results[0].entry.id == fresh.id
    assert results[1].entry.id == expired.id


# ---------------------------------------------------------------------------
# Test 16 — role scope is isolated from team scope
# ---------------------------------------------------------------------------


def test_search_role_scope(store):
    team_entry = _make_entry(
        title="shared", scope="team", id_suffix="aa1001"
    )
    role_entry = _make_entry(
        title="designer-only",
        scope="role",
        role="designer",
        id_suffix="aa1002",
    )
    store.write(team_entry)
    store.write(role_entry)

    role_results = search(store, "", scope="role", role="designer")
    team_results = search(store, "", scope="team")

    assert len(role_results) == 1
    assert role_results[0].entry.id == role_entry.id

    assert len(team_results) == 1
    assert team_results[0].entry.id == team_entry.id


# ---------------------------------------------------------------------------
# Test 17 — empty query returns all entries (scope/tag-filtered)
# ---------------------------------------------------------------------------


def test_search_empty_query_returns_all(store):
    e1 = _make_entry(title="one", tags=["pattern"], id_suffix="bb1001")
    e2 = _make_entry(title="two", tags=["pattern"], id_suffix="bb1002")
    e3 = _make_entry(title="three", tags=["incident"], id_suffix="bb1003")
    store.write(e1)
    store.write(e2)
    store.write(e3)

    all_results = search(store, "")
    assert len(all_results) == 3
    # Results are ranked by score desc — just assert presence
    returned_ids = {r.entry.id for r in all_results}
    assert returned_ids == {e1.id, e2.id, e3.id}

    pattern_only = search(store, "", tag="pattern")
    assert {r.entry.id for r in pattern_only} == {e1.id, e2.id}
