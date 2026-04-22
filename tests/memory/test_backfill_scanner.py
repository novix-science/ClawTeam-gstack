"""Tests for Phase 3 D-09 backfill scanner — Plan 06-11 Task 3 (D-11, QUALITY-10).

``backfill_scan(team, root)`` walks
``<root>/teams/<team>/_phase6_pending/*.json`` (written by the Reflect-phase
handler in ``gstack_sprint_plugin._write_phase6_pending``) and promotes
each retro payload to a :class:`MemoryEntry` persisted via
:meth:`TeamMemoryStore.write` — i.e. into
``memory/team/<YYYY-MM>.jsonl`` with ``tags=["retro", "phase-reflect"]``.

Idempotent via a ``.processed/<stem>.processed`` sentinel so re-invocation
promotes zero entries. First /learn invocation per-team triggers the scan
(sentinel: per-process ``set[str]``).

Five tests per the plan acceptance criteria:

1. Empty pending directory → 0 promotions.
2. Single valid retro JSON → promoted to memory/team JSONL with retro tags.
3. Second scan is a no-op (sentinel hit).
4. Malformed JSON does NOT crash the scan — skipped silently.
5. learn_handler triggers backfill on first invocation per team.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return tmp_path


def _write_pending_retro(
    root: Path, team: str, sprint_id: str, *, body: str = "retro body"
) -> Path:
    """Mirror ``_write_phase6_pending`` shape from gstack_sprint_plugin."""
    pending_dir = root / "teams" / team / "_phase6_pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    target = pending_dir / f"{sprint_id}-retro.json"
    payload = {
        "sprint_id": sprint_id,
        "team_name": team,
        "retro_body": body,
        "personas": ["eng-mgr", "engineer"],
        "feature_flag": "phase6_learn_pending",
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# 1. Empty pending dir → 0
# ---------------------------------------------------------------------------


def test_scan_empty_pending_returns_zero(isolated_data_dir):
    from clawteam.memory.backfill import backfill_scan

    assert backfill_scan(team="teamA", root=isolated_data_dir) == 0


# ---------------------------------------------------------------------------
# 2. Single retro JSON → promoted, retro tags set, bucketed
# ---------------------------------------------------------------------------


def test_scan_promotes_json_to_retro_jsonl(isolated_data_dir):
    from clawteam.memory import TeamMemoryStore
    from clawteam.memory.backfill import backfill_scan

    _write_pending_retro(
        isolated_data_dir, "teamA", "sprint-01", body="we learned X"
    )
    count = backfill_scan(team="teamA", root=isolated_data_dir)
    assert count == 1

    store = TeamMemoryStore("teamA")
    entries = store.list(scope="team")
    assert len(entries) == 1
    entry = entries[0]
    # Retro-specific shape:
    assert "retro" in entry.tags
    assert "phase-reflect" in entry.tags
    assert entry.scope == "team"
    # Body carries the retro payload body (or serialized fallback).
    assert "learned" in entry.body.lower() or "retro" in entry.body.lower()


# ---------------------------------------------------------------------------
# 3. Idempotent — second scan is a no-op
# ---------------------------------------------------------------------------


def test_scan_is_idempotent(isolated_data_dir):
    from clawteam.memory import TeamMemoryStore
    from clawteam.memory.backfill import backfill_scan

    _write_pending_retro(isolated_data_dir, "teamA", "sprint-01")

    first = backfill_scan(team="teamA", root=isolated_data_dir)
    second = backfill_scan(team="teamA", root=isolated_data_dir)
    assert first == 1
    assert second == 0

    # Only one entry in the store despite two scans.
    store = TeamMemoryStore("teamA")
    assert len(store.list(scope="team")) == 1

    # Sentinel file present.
    sentinel = (
        isolated_data_dir
        / "teams" / "teamA" / "_phase6_pending" / ".processed"
        / "sprint-01-retro.processed"
    )
    assert sentinel.is_file()


# ---------------------------------------------------------------------------
# 4. Malformed JSON — scan does not crash
# ---------------------------------------------------------------------------


def test_scan_skips_malformed_json_without_crash(isolated_data_dir):
    from clawteam.memory import TeamMemoryStore
    from clawteam.memory.backfill import backfill_scan

    # Write a valid retro + a malformed one — scanner should promote the
    # valid one and skip the malformed one without raising.
    _write_pending_retro(isolated_data_dir, "teamA", "sprint-valid")
    bad = (
        isolated_data_dir
        / "teams" / "teamA" / "_phase6_pending" / "sprint-bad-retro.json"
    )
    bad.write_text("{not valid json", encoding="utf-8")

    count = backfill_scan(team="teamA", root=isolated_data_dir)
    assert count == 1  # only the valid one promoted

    store = TeamMemoryStore("teamA")
    entries = store.list(scope="team")
    assert len(entries) == 1


# ---------------------------------------------------------------------------
# 5. learn_handler triggers backfill on first invocation per-team
# ---------------------------------------------------------------------------


def test_learn_handler_triggers_backfill_on_first_invocation(
    isolated_data_dir, monkeypatch,
):
    from clawteam.memory import TeamMemoryStore
    from clawteam.templates.gstack.skills.learn import handler as handler_mod

    # Reset the per-process sentinel so prior tests in this session don't
    # mask the first-invocation trigger.
    if hasattr(handler_mod, "_backfilled_teams"):
        handler_mod._backfilled_teams.clear()

    team = "teamBackfill"
    _write_pending_retro(isolated_data_dir, team, "sprint-xyz", body="retro A")

    ctx = SimpleNamespace(team_name=team)
    # A list call is the cheapest learn action that still exercises the
    # team-resolution path and backfill hook.
    handler_mod.learn_handler(
        ctx, role="engineer", args={"action": "list", "scope": "team"}
    )

    store = TeamMemoryStore(team)
    entries = store.list(scope="team")
    assert len(entries) == 1
    assert "retro" in entries[0].tags

    # Second invocation same team: no duplicate promotion.
    handler_mod.learn_handler(
        ctx, role="engineer", args={"action": "list", "scope": "team"}
    )
    assert len(store.list(scope="team")) == 1


# ---------------------------------------------------------------------------
# WR-03 regression: swallowed exceptions are logged (backfill_scan + learn).
# ---------------------------------------------------------------------------


def test_scan_logs_swallowed_entry_exception(isolated_data_dir, caplog):
    """A per-entry exception in store.write must be logged, not silent."""
    import logging

    from clawteam.memory.backfill import backfill_scan

    _write_pending_retro(isolated_data_dir, "teamC", "sprint-01")

    # Force a store.write failure mid-scan by monkey-patching write to raise
    # an unexpected error type. The scan must log + continue.
    import clawteam.memory.backfill as backfill_mod

    class BoomStore:
        def __init__(self, team):
            self.team_name = team

        def gen_id(self, **kw):
            return "mem-teamc-20260421-aaaaaa"

        def write(self, entry):
            raise RuntimeError("simulated write failure")

    orig_store_cls = backfill_mod.TeamMemoryStore
    backfill_mod.TeamMemoryStore = BoomStore  # type: ignore[misc]
    try:
        with caplog.at_level(logging.WARNING, logger="clawteam.memory.backfill"):
            count = backfill_scan(team="teamC", root=isolated_data_dir)
        assert count == 0  # nothing promoted
        # Log message must reference the team so operators can correlate.
        assert any(
            "swallowed exception" in rec.message
            and "teamC" in rec.message
            for rec in caplog.records
        ), [r.message for r in caplog.records]
    finally:
        backfill_mod.TeamMemoryStore = orig_store_cls  # type: ignore[misc]


def test_learn_handler_logs_when_backfill_raises(
    isolated_data_dir, monkeypatch, caplog,
):
    """backfill_scan exception inside _ensure_backfilled must be logged."""
    import logging

    from clawteam.templates.gstack.skills.learn import handler as handler_mod

    # Reset per-process sentinel so our patched scan runs.
    if hasattr(handler_mod, "_backfilled_teams"):
        handler_mod._backfilled_teams.clear()

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated scanner crash")

    monkeypatch.setattr(handler_mod, "backfill_scan", _boom)

    ctx = SimpleNamespace(team_name="teamLog")
    logger_name = "clawteam.templates.gstack.skills.learn.handler"
    with caplog.at_level(logging.WARNING, logger=logger_name):
        # Must NOT raise — /learn dispatch stays non-blocking.
        handler_mod.learn_handler(
            ctx, role="engineer", args={"action": "list", "scope": "team"}
        )
    assert any(
        "backfill_scan swallowed" in rec.message and "teamLog" in rec.message
        for rec in caplog.records
    ), [r.message for r in caplog.records]
