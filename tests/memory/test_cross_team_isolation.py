"""Cross-team isolation tests for TeamMemoryStore (Plan 06-02 Task 2, D-15).

Four tests ensuring:
  - teamA cannot read teamB entries.
  - team_name="../otherteam" rejected at construction.
  - role="../../etc/passwd" rejected at list time.
  - role="/etc/passwd" (absolute) rejected at list time.
"""

from __future__ import annotations

import pytest

from clawteam.memory import MemoryEntry, TeamMemoryStore


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------------------
# Test 12 — teamA cannot read teamB entries
# ---------------------------------------------------------------------------


def test_team_a_cannot_read_team_b(isolated_data_dir):
    store_a = TeamMemoryStore("teamA")
    store_b = TeamMemoryStore("teamB")
    entry_a = MemoryEntry(
        id="mem-teamA-20260421-aaaaaa",
        author="engineer@sprint-1",
        title="A note",
        tags=["pattern"],
        learned_from="artifact",
        scope="team",
        timestamp="2026-04-21T10:00:00+00:00",
    )
    entry_b = MemoryEntry(
        id="mem-teamB-20260421-bbbbbb",
        author="engineer@sprint-1",
        title="B note",
        tags=["pattern"],
        learned_from="artifact",
        scope="team",
        timestamp="2026-04-21T10:00:00+00:00",
    )
    store_a.write(entry_a)
    store_b.write(entry_b)
    a_hits = store_a.list(scope="team")
    b_hits = store_b.list(scope="team")
    assert {h.id for h in a_hits} == {"mem-teamA-20260421-aaaaaa"}
    assert {h.id for h in b_hits} == {"mem-teamB-20260421-bbbbbb"}


# ---------------------------------------------------------------------------
# Test 13 — team_name path-traversal rejected at construction
# ---------------------------------------------------------------------------


def test_path_traversal_team_name_rejected(isolated_data_dir):
    with pytest.raises(ValueError):
        TeamMemoryStore("../otherteam")


# ---------------------------------------------------------------------------
# Test 14 — role path traversal rejected at list
# ---------------------------------------------------------------------------


def test_path_traversal_role_rejected(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    with pytest.raises(ValueError):
        store.list(scope="role", role="../../etc/passwd")


# ---------------------------------------------------------------------------
# Test 15 — absolute role path rejected
# ---------------------------------------------------------------------------


def test_absolute_role_path_rejected(isolated_data_dir):
    store = TeamMemoryStore("teamA")
    with pytest.raises(ValueError):
        store.list(scope="role", role="/etc/passwd")
