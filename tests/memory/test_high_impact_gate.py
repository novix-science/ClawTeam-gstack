"""Tests for high-impact gate — Plan 06-11 Task 1 (MEM-06).

Covers:

* ``check_high_impact`` returns (True, reason) for ``impact:high`` tag and
  for team-scoped entries carrying a ``decisions`` tag; (False, "") for
  low-impact writes.
* ``stage_pending`` writes ``memory/<scope>/pending/<id>.jsonl`` atomically
  and emits ``sprints/<sprint_id>/questions/memory-confirm-<id>.md`` in the
  InteractionGate-consumable shape (T-06-11-01 mitigation).
* ``learn_handler`` stages instead of writing on high-impact; writes
  immediately on low-impact — confirming the gate is wired to the /learn
  write path (D-09, Phase 6 SC #6).

Six tests total per the plan's Task 1 acceptance criteria.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    """Redirect ~/.clawteam to tmp_path for every test (shared with 06-02)."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def ctx():
    return SimpleNamespace(team_name="testteam")


def _mk_entry(**overrides):
    """Construct a default MemoryEntry with overrides, matching the schema."""
    from clawteam.memory import MemoryEntry

    base: dict = dict(
        id="mem-testteam-20260421-abcdef",
        author="engineer@learn",
        title="some title",
        body="some body with evidence",
        tags=["pattern"],
        evidence="src/x.py:1",
        confidence=0.8,
        learned_from="artifact",
        scope="team",
        role=None,
    )
    base.update(overrides)
    return MemoryEntry(**base)


# ---------------------------------------------------------------------------
# 1. Impact:high tag triggers confirmation
# ---------------------------------------------------------------------------


def test_impact_high_tag_triggers_confirmation():
    from clawteam.memory.high_impact_gate import check_high_impact

    entry = _mk_entry(tags=["pattern", "impact:high"])
    requires, reason = check_high_impact(entry)
    assert requires is True
    assert "impact:high" in reason


# ---------------------------------------------------------------------------
# 2. Team-scope + decisions tag triggers confirmation
# ---------------------------------------------------------------------------


def test_decisions_scope_triggers_confirmation():
    from clawteam.memory.high_impact_gate import check_high_impact

    entry = _mk_entry(tags=["decisions", "adr"], scope="team")
    requires, reason = check_high_impact(entry)
    assert requires is True
    assert "decisions" in reason.lower()


# ---------------------------------------------------------------------------
# 3. Low-impact tags do NOT trigger confirmation
# ---------------------------------------------------------------------------


def test_low_impact_tag_no_confirmation():
    from clawteam.memory.high_impact_gate import check_high_impact

    entry = _mk_entry(tags=["pattern", "async"])
    requires, reason = check_high_impact(entry)
    assert requires is False
    assert reason == ""


# ---------------------------------------------------------------------------
# 4. stage_pending writes JSONL + question artifact at expected paths
# ---------------------------------------------------------------------------


def test_stage_pending_writes_jsonl_and_question(isolated_data_dir):
    from clawteam.memory.high_impact_gate import stage_pending

    entry = _mk_entry(
        id="mem-testteam-20260421-abcdef",
        tags=["impact:high", "pattern"],
        body="some critical body",
    )
    sprint_id = "sprint-01"
    pending_path = stage_pending(
        entry, team="testteam", sprint_id=sprint_id, root=isolated_data_dir,
    )

    # 1. Pending JSONL written under memory/<scope>/pending/<id>.jsonl.
    expected_pending = (
        isolated_data_dir
        / "teams" / "testteam" / "memory" / "team" / "pending"
        / f"{entry.id}.jsonl"
    )
    assert pending_path == expected_pending
    assert pending_path.is_file()
    line = pending_path.read_text(encoding="utf-8").rstrip("\n")
    payload = json.loads(line)
    assert payload["id"] == entry.id
    assert "impact:high" in payload["tags"]

    # 2. Question artifact written under sprints/<sprint>/questions/memory-confirm-<id>.md.
    expected_q = (
        isolated_data_dir
        / "teams" / "testteam" / "sprints" / sprint_id / "questions"
        / f"memory-confirm-{entry.id}.md"
    )
    assert expected_q.is_file()
    body = expected_q.read_text(encoding="utf-8")
    assert entry.id in body
    assert "high-impact" in body.lower() or "confirm" in body.lower()


# ---------------------------------------------------------------------------
# 5. learn_handler stages (does NOT write) on high-impact
# ---------------------------------------------------------------------------


def test_learn_handler_stages_instead_of_writing_on_high_impact(
    isolated_data_dir, ctx,
):
    from clawteam.memory import TeamMemoryStore
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    args = {
        "action": "write",
        "scope": "team",
        "title": "rewriting the auth model",
        "body": "we will switch to OAuth",
        "tags": ["pattern"],
        "evidence": "adr/auth.md:1",
        "confidence": 0.9,
        "learned_from": "artifact",
        "impact": "high",  # triggers impact:high tag -> gate fires
        "sprint_id": "sprint-01",
    }
    result = learn_handler(ctx, role="engineer", args=args)

    assert result["status"] == "pending_confirmation", result
    assert result.get("high_impact") is True
    # Pending path returned so callers can reference it.
    assert "pending_path" in result
    assert Path(result["pending_path"]).is_file()

    # Main store must NOT contain the entry yet.
    store = TeamMemoryStore("testteam")
    assert store.list(scope="team") == []


# ---------------------------------------------------------------------------
# 6. learn_handler writes immediately on low-impact
# ---------------------------------------------------------------------------


def test_learn_handler_writes_immediately_on_low_impact(
    isolated_data_dir, ctx,
):
    from clawteam.memory import TeamMemoryStore
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    args = {
        "action": "write",
        "scope": "team",
        "title": "small pattern",
        "body": "use x",
        "tags": ["pattern"],
        "evidence": "src/x.py:1",
        "confidence": 0.7,
        "learned_from": "artifact",
        "impact": "low",
    }
    result = learn_handler(ctx, role="engineer", args=args)
    assert result["status"] == "written"
    assert result.get("high_impact") is False

    store = TeamMemoryStore("testteam")
    entries = store.list(scope="team")
    assert len(entries) == 1
    assert entries[0].title == "small pattern"
