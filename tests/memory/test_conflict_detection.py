"""Tests for cosine-on-BoW conflict detection — Plan 06-11 Task 2 (QUALITY-10).

``detect_conflicts(new_entry, store, threshold=0.75)`` returns a list of
:class:`ConflictMatch` for existing entries sharing at least one tag with
``new_entry`` whose bag-of-words cosine similarity ≥ threshold. The D-10
research note specifies NON-BLOCKING behavior: the caller (learn_handler)
emits :class:`ConflictDetected` via the bus but the write already
happened. These tests focus on the detection primitive only.

Five tests per the plan acceptance criteria:

1. ``test_empty_tags_no_conflict`` — a tagless new entry never conflicts.
2. ``test_same_tag_similar_body_matches`` — identical tag + near-identical
   body → one ConflictMatch above threshold.
3. ``test_same_tag_different_body_below_threshold_no_match`` — shared tag
   but low-similarity body → no match.
4. ``test_different_tags_never_match_even_if_body_similar`` — conflict gate
   is tag-bounded (D-10) even with identical bodies.
5. ``test_threshold_configurable`` — lowering threshold surfaces matches the
   default would have rejected.
"""

from __future__ import annotations

import pytest

from clawteam.memory import MemoryEntry, TeamMemoryStore


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return tmp_path


def _mk_entry(
    *,
    id_: str,
    tags: list[str],
    body: str,
    title: str = "title",
    scope: str = "team",
    role: str | None = None,
    timestamp: str | None = None,
) -> MemoryEntry:
    kwargs: dict = dict(
        id=id_,
        author="engineer@sprint-1",
        title=title,
        body=body,
        tags=tags,
        learned_from="artifact",
        scope=scope,
    )
    if role is not None:
        kwargs["role"] = role
    if timestamp is not None:
        kwargs["timestamp"] = timestamp
    return MemoryEntry(**kwargs)


# ---------------------------------------------------------------------------
# 1. Empty tags → no conflict
# ---------------------------------------------------------------------------


def test_empty_tags_no_conflict(isolated_data_dir):
    from clawteam.memory.conflict import detect_conflicts

    store = TeamMemoryStore("teamA")
    existing = _mk_entry(
        id_="mem-teamA-20260420-111111",
        tags=["pattern"],
        body="use asyncio gather for concurrent IO",
    )
    store.write(existing)

    new = _mk_entry(
        id_="mem-teamA-20260421-222222",
        tags=[],  # empty
        body="use asyncio gather for concurrent IO",
    )
    assert detect_conflicts(new, store) == []


# ---------------------------------------------------------------------------
# 2. Same tag + similar body → matches
# ---------------------------------------------------------------------------


def test_same_tag_similar_body_matches(isolated_data_dir):
    from clawteam.memory.conflict import ConflictMatch, detect_conflicts

    store = TeamMemoryStore("teamA")
    existing = _mk_entry(
        id_="mem-teamA-20260420-aaaaaa",
        tags=["pattern", "async"],
        body="use asyncio gather to run concurrent IO with high throughput",
    )
    store.write(existing)

    new = _mk_entry(
        id_="mem-teamA-20260421-bbbbbb",
        tags=["pattern"],
        body="use asyncio gather to run concurrent IO with high throughput and safety",
    )

    matches = detect_conflicts(new, store)
    assert len(matches) == 1
    m = matches[0]
    assert isinstance(m, ConflictMatch)
    assert m.other_id == existing.id
    assert m.similarity >= 0.75
    assert "pattern" in m.shared_tags


# ---------------------------------------------------------------------------
# 3. Same tag + different body → no match (below default threshold)
# ---------------------------------------------------------------------------


def test_same_tag_different_body_below_threshold_no_match(isolated_data_dir):
    from clawteam.memory.conflict import detect_conflicts

    store = TeamMemoryStore("teamA")
    existing = _mk_entry(
        id_="mem-teamA-20260420-cccccc",
        tags=["pattern"],
        body="fast fourier transform for frequency analysis",
    )
    store.write(existing)

    new = _mk_entry(
        id_="mem-teamA-20260421-dddddd",
        tags=["pattern"],
        body="bubble sort is quadratic and slow for large inputs",
    )
    assert detect_conflicts(new, store) == []


# ---------------------------------------------------------------------------
# 4. Different tags + identical body → never match (D-10 tag gate)
# ---------------------------------------------------------------------------


def test_different_tags_never_match_even_if_body_similar(isolated_data_dir):
    from clawteam.memory.conflict import detect_conflicts

    store = TeamMemoryStore("teamA")
    body = "use asyncio gather to run concurrent IO with high throughput"
    existing = _mk_entry(
        id_="mem-teamA-20260420-eeeeee",
        tags=["pattern"],
        body=body,
    )
    store.write(existing)

    new = _mk_entry(
        id_="mem-teamA-20260421-ffffff",
        tags=["incident"],  # DIFFERENT tag set
        body=body,  # identical body
    )
    assert detect_conflicts(new, store) == []


# ---------------------------------------------------------------------------
# 5. Threshold is configurable
# ---------------------------------------------------------------------------


def test_threshold_configurable(isolated_data_dir):
    from clawteam.memory.conflict import detect_conflicts

    store = TeamMemoryStore("teamA")
    existing = _mk_entry(
        id_="mem-teamA-20260420-aaaabb",
        tags=["pattern"],
        body="alpha beta gamma delta epsilon",
    )
    store.write(existing)

    # Deliberately low overlap — default threshold rejects, low threshold accepts.
    new = _mk_entry(
        id_="mem-teamA-20260421-aaaacc",
        tags=["pattern"],
        body="alpha zeta eta theta iota",
    )

    assert detect_conflicts(new, store) == []  # default 0.75
    matches = detect_conflicts(new, store, threshold=0.1)
    assert len(matches) == 1
    assert matches[0].similarity > 0.0
