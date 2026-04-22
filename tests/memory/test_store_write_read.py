"""Tests for TeamMemoryStore write/list/prune (Plan 06-02 Task 2).

Eleven tests covering two-tier layout, roundtrip (team + role scopes), month
bucketing, serial-write lock correctness, file_locked invocation, tag filtering,
non-filtered listing, tombstone semantics, and gate-bypass for prune.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clawteam.memory import MemoryEntry, TeamMemoryStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect ~/.clawteam to tmp_path for the duration of the test."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    # clawteam.team.models.get_data_dir reads env first, then config.
    return tmp_path


def _mk_entry(
    *,
    team_id: str = "mem-myteam-20260421-aaaaaa",
    scope: str = "team",
    role: str | None = None,
    tags: list[str] | None = None,
    timestamp: str | None = None,
    op: str = "write",
) -> MemoryEntry:
    kwargs = dict(
        id=team_id,
        author="engineer@sprint-1",
        title="t",
        tags=tags if tags is not None else ["pattern"],
        learned_from="artifact",
        scope=scope,
    )
    if role is not None:
        kwargs["role"] = role
    if timestamp is not None:
        kwargs["timestamp"] = timestamp
    if op != "write":
        kwargs["op"] = op
    return MemoryEntry(**kwargs)


# ---------------------------------------------------------------------------
# Test 1 — two-tier layout lazy creation
# ---------------------------------------------------------------------------


def test_two_tier_layout(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    entry = _mk_entry(timestamp="2026-04-21T10:00:00+00:00")
    store.write(entry)
    root = isolated_data_dir / "teams" / "teamA" / "memory"
    assert root.is_dir(), f"expected memory root under {root}"
    assert (root / "team").is_dir()


# ---------------------------------------------------------------------------
# Test 2 — team scope write/read roundtrip
# ---------------------------------------------------------------------------


def test_write_read_roundtrip_team_scope(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    entry = _mk_entry(
        team_id="mem-teamA-20260421-bbbbbb",
        timestamp="2026-04-21T10:00:00+00:00",
    )
    store.write(entry)
    assert store.list(scope="team") == [entry]
    bucket = (
        isolated_data_dir
        / "teams"
        / "teamA"
        / "memory"
        / "team"
        / "2026-04.jsonl"
    )
    assert bucket.is_file()
    lines = bucket.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["id"] == "mem-teamA-20260421-bbbbbb"


# ---------------------------------------------------------------------------
# Test 3 — role scope write/read roundtrip
# ---------------------------------------------------------------------------


def test_write_read_roundtrip_role_scope(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    entry = _mk_entry(
        team_id="mem-teamA-20260421-cccccc",
        scope="role",
        role="designer",
        timestamp="2026-04-21T10:00:00+00:00",
    )
    store.write(entry)
    assert store.list(scope="role", role="designer") == [entry]
    bucket = (
        isolated_data_dir
        / "teams"
        / "teamA"
        / "memory"
        / "agents"
        / "designer"
        / "2026-04.jsonl"
    )
    assert bucket.is_file()


# ---------------------------------------------------------------------------
# Test 4 — month bucketing
# ---------------------------------------------------------------------------


def test_month_bucketing(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    e1 = _mk_entry(
        team_id="mem-teamA-20260115-000001",
        timestamp="2026-01-15T10:00:00+00:00",
    )
    e2 = _mk_entry(
        team_id="mem-teamA-20260421-000002",
        timestamp="2026-04-21T10:00:00+00:00",
    )
    e3 = _mk_entry(
        team_id="mem-teamA-20260502-000003",
        timestamp="2026-05-02T10:00:00+00:00",
    )
    store.write(e1)
    store.write(e2)
    store.write(e3)
    base = isolated_data_dir / "teams" / "teamA" / "memory" / "team"
    assert (base / "2026-01.jsonl").is_file()
    assert (base / "2026-04.jsonl").is_file()
    assert (base / "2026-05.jsonl").is_file()
    # Each file should have exactly one line, and the line's id must match.
    for fname, expected_id in (
        ("2026-01.jsonl", "mem-teamA-20260115-000001"),
        ("2026-04.jsonl", "mem-teamA-20260421-000002"),
        ("2026-05.jsonl", "mem-teamA-20260502-000003"),
    ):
        lines = (base / fname).read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["id"] == expected_id


# ---------------------------------------------------------------------------
# Test 5 — serial writes do not interleave
# ---------------------------------------------------------------------------


def test_concurrent_write_does_not_interleave(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    # 10 serial writes, same month bucket
    for i in range(10):
        e = _mk_entry(
            team_id=f"mem-teamA-20260421-{i:06x}",
            timestamp="2026-04-21T10:00:00+00:00",
        )
        store.write(e)
    bucket = (
        isolated_data_dir
        / "teams"
        / "teamA"
        / "memory"
        / "team"
        / "2026-04.jsonl"
    )
    lines = bucket.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 10
    # Each line must parse as valid JSON with the expected id.
    for i, line in enumerate(lines):
        parsed = json.loads(line)
        assert parsed["id"] == f"mem-teamA-20260421-{i:06x}"


# ---------------------------------------------------------------------------
# Test 6 — file_locked IS called with the bucket path
# ---------------------------------------------------------------------------


def test_file_locked_during_write(isolated_data_dir, monkeypatch):
    from clawteam.memory import store as store_mod

    called_with: list[Path] = []
    original = store_mod.file_locked

    def tracking(path):
        called_with.append(Path(path))
        return original(path)

    monkeypatch.setattr(store_mod, "file_locked", tracking)

    store = TeamMemoryStore("teamA")
    entry = _mk_entry(
        team_id="mem-teamA-20260421-aaaaaa",
        timestamp="2026-04-21T10:00:00+00:00",
    )
    store.write(entry)
    assert len(called_with) == 1
    expected_bucket = (
        isolated_data_dir
        / "teams"
        / "teamA"
        / "memory"
        / "team"
        / "2026-04.jsonl"
    )
    assert called_with[0] == expected_bucket


# ---------------------------------------------------------------------------
# Test 7 — list filters by tag
# ---------------------------------------------------------------------------


def test_list_filters_by_tag(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    e1 = _mk_entry(
        team_id="mem-teamA-20260421-111111",
        tags=["pattern", "async"],
        timestamp="2026-04-21T10:00:00+00:00",
    )
    e2 = _mk_entry(
        team_id="mem-teamA-20260421-222222",
        tags=["pattern"],
        timestamp="2026-04-21T10:00:00+00:00",
    )
    e3 = _mk_entry(
        team_id="mem-teamA-20260421-333333",
        tags=["incident"],
        timestamp="2026-04-21T10:00:00+00:00",
    )
    for e in (e1, e2, e3):
        store.write(e)
    pattern_hits = store.list(scope="team", tag="pattern")
    assert {h.id for h in pattern_hits} == {
        "mem-teamA-20260421-111111",
        "mem-teamA-20260421-222222",
    }
    incident_hits = store.list(scope="team", tag="incident")
    assert [h.id for h in incident_hits] == ["mem-teamA-20260421-333333"]


# ---------------------------------------------------------------------------
# Test 8 — list without tag returns all entries
# ---------------------------------------------------------------------------


def test_list_no_tag_returns_all(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    ids = [
        "mem-teamA-20260421-444444",
        "mem-teamA-20260421-555555",
        "mem-teamA-20260421-666666",
    ]
    for eid in ids:
        store.write(
            _mk_entry(team_id=eid, timestamp="2026-04-21T10:00:00+00:00")
        )
    all_hits = store.list(scope="team")
    assert {h.id for h in all_hits} == set(ids)


# ---------------------------------------------------------------------------
# Test 9 — prune appends tombstone
# ---------------------------------------------------------------------------


def test_prune_appends_tombstone(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    target_id = "mem-teamA-20260421-777777"
    store.write(
        _mk_entry(team_id=target_id, timestamp="2026-04-21T10:00:00+00:00")
    )
    store.prune(target_id, scope="team")
    bucket = (
        isolated_data_dir
        / "teams"
        / "teamA"
        / "memory"
        / "team"
        / "2026-04.jsonl"
    )
    lines = bucket.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    parsed0 = json.loads(lines[0])
    parsed1 = json.loads(lines[1])
    assert parsed0["op"] == "write"
    assert parsed0["id"] == target_id
    assert parsed1["op"] == "prune"
    assert parsed1["id"] == target_id


# ---------------------------------------------------------------------------
# Test 10 — list hides tombstoned entries
# ---------------------------------------------------------------------------


def test_list_hides_tombstoned(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    target_id = "mem-teamA-20260421-888888"
    store.write(
        _mk_entry(team_id=target_id, timestamp="2026-04-21T10:00:00+00:00")
    )
    store.prune(target_id, scope="team")
    assert store.list(scope="team") == []


# ---------------------------------------------------------------------------
# Test 11 — prune bypasses high-impact gate (always immediate)
# ---------------------------------------------------------------------------


def test_prune_tombstone_bypasses_high_impact(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    target_id = "mem-teamA-20260421-999999"
    # High-impact tag on original entry must NOT route prune through a gate.
    store.write(
        _mk_entry(
            team_id=target_id,
            tags=["pattern", "impact:high"],
            timestamp="2026-04-21T10:00:00+00:00",
        )
    )
    # Should return cleanly; no exception, no gate invocation.
    store.prune(target_id, scope="team")
    assert store.list(scope="team") == []
