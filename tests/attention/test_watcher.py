"""Plan 07-03 Task 2 — AttentionWatcher polling fallback + watchdog_available (D-06)."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from clawteam.attention.queue import AttentionQueue
from clawteam.attention.watcher import (
    AttentionWatcher,
    make_watcher,
    watchdog_available,
)


def _write_question(data_dir: Path, qid: str = "q1") -> None:
    d = data_dir / "teams" / "t1" / "sprints" / "s1" / "questions"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{qid}.md").write_text(
        "---\nurgency: high\n---\nbody\n", encoding="utf-8"
    )


def test_watchdog_available_returns_bool() -> None:
    assert isinstance(watchdog_available(), bool)


def test_no_top_level_watchdog_import() -> None:
    """Importing watcher module must NOT pull watchdog into sys.modules (D-06)."""
    # Drop any lingering watcher reference so the test re-imports fresh.
    for mod_name in list(sys.modules.keys()):
        if mod_name.startswith("clawteam.attention.watcher"):
            del sys.modules[mod_name]
    # Snapshot pre-import watchdog presence.
    pre_loaded = "watchdog" in sys.modules
    import clawteam.attention.watcher  # noqa: F401

    if not pre_loaded:
        assert "watchdog" not in sys.modules, (
            "importing clawteam.attention.watcher pulled in watchdog at top level"
        )


def test_polling_watcher_fires_callback_on_change(tmp_path: Path) -> None:
    queue = AttentionQueue(data_dir=tmp_path)
    received: list[list] = []
    watcher = AttentionWatcher(
        queue,
        lambda items: received.append(list(items)),
        mode="polling",
        interval_seconds=0.05,
    )
    watcher.start()
    try:
        _write_question(tmp_path, "q1")
        time.sleep(0.25)
        _write_question(tmp_path, "q2")
        time.sleep(0.25)
    finally:
        watcher.stop()
    # Expect ≥2 observed item counts (0→1 or 1→2) from the change-diff stream.
    lens = [len(call) for call in received]
    assert received, "callback never fired"
    assert max(lens) >= 2


def test_polling_watcher_stops_cleanly(tmp_path: Path) -> None:
    queue = AttentionQueue(data_dir=tmp_path)
    received: list = []
    watcher = AttentionWatcher(
        queue,
        lambda items: received.append(items),
        mode="polling",
        interval_seconds=0.05,
    )
    watcher.start()
    time.sleep(0.1)
    watcher.stop()
    before_stop = len(received)
    time.sleep(0.3)  # post-stop; no new callbacks
    assert len(received) == before_stop


def test_factory_prefers_watchdog_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "clawteam.attention.watcher.watchdog_available", lambda: True
    )
    queue = AttentionQueue(data_dir=tmp_path)
    w = make_watcher(queue, lambda items: None)
    assert w.mode == "watchdog"


def test_factory_falls_back_to_polling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "clawteam.attention.watcher.watchdog_available", lambda: False
    )
    queue = AttentionQueue(data_dir=tmp_path)
    w = make_watcher(queue, lambda items: None)
    assert w.mode == "polling"


def test_polling_emits_on_answer_resolution(tmp_path: Path) -> None:
    """Writing a sibling answer should re-fire the callback with fewer items."""
    queue = AttentionQueue(data_dir=tmp_path)
    received: list[int] = []
    watcher = AttentionWatcher(
        queue,
        lambda items: received.append(len(items)),
        mode="polling",
        interval_seconds=0.05,
    )
    watcher.start()
    try:
        _write_question(tmp_path, "q1")
        time.sleep(0.2)
        # Now resolve q1 by writing an answer
        adir = tmp_path / "teams" / "t1" / "sprints" / "s1" / "answers"
        adir.mkdir(parents=True, exist_ok=True)
        (adir / "q1.md").write_text("answer\n", encoding="utf-8")
        time.sleep(0.25)
    finally:
        watcher.stop()
    # We should see at least one snapshot with 1 item, then one with 0.
    assert 1 in received or any(r >= 1 for r in received)
    assert 0 in received
