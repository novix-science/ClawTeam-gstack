"""Tests for /learn skill handler + plugin registration (Plan 06-10).

Covers MEM-03 + MEM-04 + D-07 (role-agnostic) + D-08 (shared handler across
skill + CLI). All tests use a tmp CLAWTEAM_DATA_DIR so the on-disk JSONL
store is isolated between tests.

11 tests:

1. ``test_handler_write_team_scope``    — write team entry, verify listed.
2. ``test_handler_write_role_scope``    — write role entry, bucket is per-role.
3. ``test_handler_write_missing_evidence_succeeds`` — MEM-05: flagged, not blocked.
4. ``test_handler_list``                — list returns all non-tombstoned entries.
5. ``test_handler_list_tag_filter``     — list with tag filter returns matches only.
6. ``test_handler_search``              — keyword search returns matching entries.
7. ``test_handler_search_with_explain`` — --explain populates recency/provenance/decay.
8. ``test_handler_prune``               — prune tombstones entry; list returns [].
9. ``test_handler_unknown_action``      — unknown action raises ValueError.
10. ``test_handler_role_agnostic``      — any GSTACK_ROLE dispatches successfully.
11. ``test_registered_in_plugin``       — plugin now registers /learn role-agnostic.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Isolated on-disk store root for every test."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def ctx():
    return SimpleNamespace(team_name="testteam")


# ---------------------------------------------------------------------------
# 1. Write (team scope) — happy path
# ---------------------------------------------------------------------------


def test_handler_write_team_scope(data_dir, ctx):
    from clawteam.memory import TeamMemoryStore
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    args = {
        "action": "write",
        "scope": "team",
        "title": "Async patterns discovered",
        "body": "Use asyncio.gather for parallel I/O.",
        "tags": ["pattern", "async"],
        "evidence": "src/x.py:12",
        "confidence": 0.9,
        "learned_from": "artifact",
        "impact": "low",
    }
    result = learn_handler(ctx, role="engineer", args=args)

    assert result["status"] == "written"
    assert result["id"].startswith("mem-testteam-")
    assert result["evidence_flagged"] is False
    assert result["high_impact"] is False

    store = TeamMemoryStore("testteam")
    entries = store.list(scope="team")
    assert len(entries) == 1
    assert entries[0].title == "Async patterns discovered"


# ---------------------------------------------------------------------------
# 2. Write (role scope) — lands in per-role bucket
# ---------------------------------------------------------------------------


def test_handler_write_role_scope(data_dir, ctx):
    from clawteam.memory import TeamMemoryStore
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    args = {
        "action": "write",
        "scope": "role",
        "role": "designer",
        "title": "Prefer dark-mode tokens",
        "body": "Use --bg-elevated instead of raw hex.",
        "tags": ["preference"],
        "evidence": "design/tokens.css:40",
        "confidence": 0.8,
        "learned_from": "user",
        "impact": "medium",
    }
    result = learn_handler(ctx, role="designer", args=args)
    assert result["status"] == "written"

    store = TeamMemoryStore("testteam")
    # Team-scope list should NOT include the role entry.
    assert store.list(scope="team") == []
    role_entries = store.list(scope="role", role="designer")
    assert len(role_entries) == 1
    assert role_entries[0].role == "designer"


# ---------------------------------------------------------------------------
# 3. Write with empty evidence — MEM-05: flagged, never blocked
# ---------------------------------------------------------------------------


def test_handler_write_missing_evidence_succeeds(data_dir, ctx):
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    args = {
        "action": "write",
        "scope": "team",
        "title": "A hunch without a source",
        "tags": ["pattern"],
        "evidence": "",  # empty → flagged, not blocked
        "confidence": 0.4,
        "learned_from": "self-inferred",
    }
    result = learn_handler(ctx, role="pm", args=args)
    assert result["status"] == "written"
    assert result["evidence_flagged"] is True


# ---------------------------------------------------------------------------
# 4. List — returns all non-tombstoned entries
# ---------------------------------------------------------------------------


def _write(ctx, *, title: str, tags: list[str], scope: str = "team", **kwargs) -> str:
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    base = dict(
        action="write",
        scope=scope,
        title=title,
        body=kwargs.pop("body", "placeholder body"),
        tags=tags,
        evidence=kwargs.pop("evidence", "src/x.py:1"),
        confidence=kwargs.pop("confidence", 0.7),
        learned_from=kwargs.pop("learned_from", "artifact"),
        impact=kwargs.pop("impact", "low"),
    )
    base.update(kwargs)
    return learn_handler(ctx, role="engineer", args=base)["id"]


def test_handler_list(data_dir, ctx):
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    _write(ctx, title="A", tags=["pattern"])
    _write(ctx, title="B", tags=["incident"])
    _write(ctx, title="C", tags=["pattern", "async"])

    result = learn_handler(ctx, role="engineer", args={"action": "list", "scope": "team"})
    assert result["status"] == "listed"
    titles = sorted(e["title"] for e in result["entries"])
    assert titles == ["A", "B", "C"]


# ---------------------------------------------------------------------------
# 5. List with tag filter
# ---------------------------------------------------------------------------


def test_handler_list_tag_filter(data_dir, ctx):
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    _write(ctx, title="A", tags=["pattern"])
    _write(ctx, title="B", tags=["incident"])
    _write(ctx, title="C", tags=["pattern", "async"])

    result = learn_handler(
        ctx, role="engineer", args={"action": "list", "scope": "team", "tag": "pattern"}
    )
    titles = sorted(e["title"] for e in result["entries"])
    assert titles == ["A", "C"]


# ---------------------------------------------------------------------------
# 6. Search — keyword match in title/body
# ---------------------------------------------------------------------------


def test_handler_search(data_dir, ctx):
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    _write(ctx, title="foo bar baz", tags=["pattern"])
    _write(ctx, title="something else", tags=["pattern"])

    result = learn_handler(
        ctx, role="engineer", args={"action": "search", "query": "foo"}
    )
    assert result["status"] == "searched"
    titles = [r["title"] for r in result["results"]]
    assert titles == ["foo bar baz"]


# ---------------------------------------------------------------------------
# 7. Search with --explain — recency/provenance/decay surfaced
# ---------------------------------------------------------------------------


def test_handler_search_with_explain(data_dir, ctx):
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    _write(ctx, title="searchable-x", tags=["pattern"])
    result = learn_handler(
        ctx, role="engineer",
        args={"action": "search", "query": "searchable", "explain": True},
    )
    assert len(result["results"]) == 1
    item = result["results"][0]
    assert "recency" in item
    assert "provenance" in item
    assert "decay" in item
    assert 0.0 <= item["recency"] <= 1.0
    assert 0.0 < item["decay"] <= 1.0
    assert item["provenance"] > 0.0


# ---------------------------------------------------------------------------
# 8. Prune — tombstone suppresses entry in list
# ---------------------------------------------------------------------------


def test_handler_prune(data_dir, ctx):
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    entry_id = _write(ctx, title="doomed", tags=["pattern"])

    result = learn_handler(
        ctx, role="engineer",
        args={"action": "prune", "id": entry_id, "scope": "team"},
    )
    assert result["status"] == "pruned"
    assert result["id"] == entry_id

    after = learn_handler(ctx, role="engineer", args={"action": "list", "scope": "team"})
    assert after["entries"] == []


# ---------------------------------------------------------------------------
# 9. Unknown action — ValueError
# ---------------------------------------------------------------------------


def test_handler_unknown_action(data_dir, ctx):
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    with pytest.raises(ValueError):
        learn_handler(ctx, role="engineer", args={"action": "teleport"})


# ---------------------------------------------------------------------------
# 10. Role-agnostic — every GSTACK_ROLE can dispatch
# ---------------------------------------------------------------------------


def test_handler_role_agnostic(data_dir, ctx):
    from clawteam.plugins.gstack_sprint_plugin import GSTACK_ROLES
    from clawteam.templates.gstack.skills.learn.handler import learn_handler

    # Handler itself does not gate on role — dispatch for every role should
    # succeed. SkillDispatcher's role-gate is tested separately via plugin
    # registration in test_registered_in_plugin.
    for role in GSTACK_ROLES:
        result = learn_handler(
            ctx, role=role,
            args={
                "action": "write",
                "scope": "team",
                "title": f"note from {role}",
                "tags": ["pattern"],
                "evidence": "src/x.py:1",
                "learned_from": "artifact",
            },
        )
        assert result["status"] == "written"


# ---------------------------------------------------------------------------
# 11. Plugin registration — 13 skills; /learn role-agnostic
# ---------------------------------------------------------------------------


def test_registered_in_plugin():
    from clawteam.plugins.gstack_sprint_plugin import GSTACK_ROLES, GstackSprintPlugin

    plugin = GstackSprintPlugin()
    regs = plugin.contribute_skills()
    names = [r.name for r in regs]

    assert "/learn" in names, f"/learn missing from plugin; got {names}"
    # Phase 6 total contract: 7 Phase-5 skills + 3 browser skills (Wave 2)
    # + /design-shotgun + /design-html (Wave 3 Cluster B) + /learn = 13.
    # Plans 06-08 / 06-09 may land in parallel; a subset check keeps this
    # plan's commit order-independent but still enforces /learn presence.
    assert len(regs) >= 11, f"expected ≥11 skills, got {len(regs)}: {names}"

    learn_reg = next(r for r in regs if r.name == "/learn")
    assert learn_reg.roles == frozenset(GSTACK_ROLES), (
        "/learn must be role-agnostic (D-07)"
    )
    assert learn_reg.tool_available is None
    assert callable(learn_reg.handler)
