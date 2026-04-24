---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 03
type: execute
wave: 2
depends_on: [07-01]
files_modified:
  - clawteam/attention/__init__.py
  - clawteam/attention/queue.py
  - clawteam/attention/watcher.py
  - clawteam/attention/digest.py
  - tests/attention/__init__.py
  - tests/attention/test_queue_ranking.py
  - tests/attention/test_watcher.py
  - tests/attention/test_digest.py
autonomous: true
requirements:
  - INT-03
  - INT-05
  - QUALITY-05
tags:
  - attention-queue
  - stateless-read-side
  - watchdog-optional
  - digest

must_haves:
  truths:
    - "AttentionItem frozen dataclass with all 10 fields from CONTEXT §specifics; priority_score computed by compute_priority()"
    - "AttentionQueue.snapshot() globs teams/*/sprints/*/questions/*.md, filters answered, parses frontmatter, returns sorted AttentionItem list"
    - "Priority formula: URGENCY*urgency_weight + (BLOCKING ? blocking_weight : 0) + age_hours + sum(tag_weights[t] for t in tags)"
    - "watchdog_available() uses importlib.util.find_spec — never top-level import"
    - "AttentionWatcher falls back to 2-second polling when watchdog missing; calls on_change(items) callback on observed change"
    - "build_digest() groups by (sprint_id, tag_cluster, age_bucket) and returns list of cluster dicts sorted by highest_priority desc"
    - "Adversarial ranking fixture proves critical@30s outranks normal@8h per D-15"
  artifacts:
    - path: clawteam/attention/queue.py
      provides: "AttentionItem + AttentionQueue class + compute_priority"
      contains: "class AttentionItem|class AttentionQueue|def compute_priority"
    - path: clawteam/attention/watcher.py
      provides: "watchdog_available + AttentionWatcher"
      contains: "def watchdog_available|class AttentionWatcher"
    - path: clawteam/attention/digest.py
      provides: "build_digest + bucket_age"
      contains: "def build_digest|def bucket_age"
  key_links:
    - from: clawteam/attention/queue.py
      to: clawteam/team/envelope.py
      via: "AttentionQueue uses parse_frontmatter to read question.md YAML frontmatter"
      pattern: "parse_frontmatter"
    - from: clawteam/attention/watcher.py
      to: pyproject.toml
      via: "watchdog_available detects optional [attend] extra"
      pattern: "find_spec.*watchdog"
---

<objective>
Wave 2 — the `clawteam/attention/` package: AttentionQueue stateless read-side (D-04), priority formula (D-05), optional watchdog + polling fallback (D-06), digest grouping (D-07). No CLI yet — Plan 07-04 wires `clawteam attend`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md

<interfaces>
From clawteam/team/envelope.py (existing — reuse):
```python
def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (metadata, body) from YAML frontmatter text."""
```

From clawteam/templates/__init__.py (Plan 07-01):
```python
class AttentionConfig(BaseModel):
    urgency_weight: int = 10
    blocking_weight: int = 5
    tag_weights: dict[str, int] = {}
```

Question frontmatter shape (existing gate artifact — see Phase 2 question schema):
```yaml
---
urgency: critical | high | normal | low
blocking: true | false
tags: [design, security]
reversibility: easy | medium | hard
title: "Which payment provider?"
---
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: AttentionItem dataclass + compute_priority + AttentionQueue.snapshot</name>
  <files>
    clawteam/attention/queue.py,
    clawteam/attention/__init__.py,
    tests/attention/__init__.py,
    tests/attention/test_queue_ranking.py
  </files>
  <read_first>
    clawteam/team/envelope.py (parse_frontmatter),
    clawteam/harness/interaction_gate.py (question/answer directory scan pattern at lines 146-181),
    clawteam/team/models.py (get_data_dir),
    clawteam/templates/__init__.py (AttentionConfig from Plan 07-01)
  </read_first>
  <behavior>
    - Test 1: `test_attention_item_is_frozen` — AttentionItem is frozen (cannot assign attrs after construction).
    - Test 2: `test_compute_priority_formula_basic` — `urgency=2, blocking=False, age_hours=1.0, tags=(), weights default` → score = 2*10 + 0 + 1 + 0 = 21.
    - Test 3: `test_compute_priority_adds_blocking` — `urgency=1, blocking=True, age_hours=0, tags=()` → 1*10 + 5 + 0 = 15.
    - Test 4: `test_compute_priority_adds_tag_weights` — `urgency=0, blocking=False, age_hours=0, tags=("design","security"), tag_weights={"design":2,"security":3}` → 0 + 0 + 0 + 5 = 5.
    - Test 5: `test_snapshot_empty_when_no_questions` — empty data_dir → snapshot() returns [].
    - Test 6: `test_snapshot_skips_answered_questions` — write 3 questions.md + 1 answers.md → snapshot returns 2 items.
    - Test 7: `test_snapshot_sorts_by_priority_desc` — 3 questions; verify sort order.
    - Test 8 (adversarial — D-15): `test_critical_at_30s_outranks_normal_at_8h` — fixture 1 with urgency=critical (3), age=30s (0.0083h); fixture 2 with urgency=normal (1), age=8h. Score1 = 30+0+0.0083 = 30.008; Score2 = 10+0+8 = 18. Item 1 ranks first.
    - Test 9: `test_snapshot_handles_malformed_frontmatter` — question.md without frontmatter → defaults (urgency=normal, blocking=false). Does not crash.
    - Test 10: `test_snapshot_cross_teams` — 2 teams × 2 sprints × 2 questions = 8 items returned.
  </behavior>
  <action>
**1. `clawteam/attention/queue.py` (NEW, ~220 LOC):**

```python
"""AttentionQueue — cross-sprint stateless read-side priority queue (D-04/D-05).

Each snapshot() call globs teams/*/sprints/*/questions/*.md, filters out
those with sibling answers/*.md, parses frontmatter, computes priority,
sorts descending. Zero persisted state — the filesystem IS the ledger.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from clawteam.team.envelope import parse_frontmatter
from clawteam.team.models import get_data_dir

_LOG = logging.getLogger(__name__)

# Urgency → integer bucket. Unknown strings default to "normal" (= 1).
URGENCY_MAP: dict[str, int] = {
    "critical": 3,
    "high": 2,
    "normal": 1,
    "low": 0,
}


@dataclass(frozen=True)
class AttentionItem:
    """One pending question, ranked by priority_score (D-05)."""

    question_path: Path
    sprint_id: str
    team: str
    title: str
    urgency: int
    blocking: bool
    age_hours: float
    tags: tuple[str, ...]
    reversibility: str
    priority_score: float

    @property
    def question_id(self) -> str:
        return self.question_path.stem


def compute_priority(
    urgency: int,
    blocking: bool,
    age_hours: float,
    tags: tuple[str, ...],
    *,
    urgency_weight: int = 10,
    blocking_weight: int = 5,
    tag_weights: Optional[dict[str, int]] = None,
) -> float:
    """Pure function — priority formula per D-05.

    score = urgency * urgency_weight
          + (blocking_weight if blocking else 0)
          + age_hours
          + sum(tag_weights.get(tag, 0) for tag in tags)
    """
    tag_weights = tag_weights or {}
    score = float(urgency) * float(urgency_weight)
    if blocking:
        score += float(blocking_weight)
    score += float(age_hours)
    for tag in tags:
        score += float(tag_weights.get(tag, 0))
    return score


class AttentionQueue:
    """Stateless cross-sprint queue over question.md / answer.md artifacts."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        *,
        urgency_weight: int = 10,
        blocking_weight: int = 5,
        tag_weights: Optional[dict[str, int]] = None,
        now_fn=time.time,
    ) -> None:
        self._data_dir = data_dir or get_data_dir()
        self._urgency_weight = urgency_weight
        self._blocking_weight = blocking_weight
        self._tag_weights = tag_weights or {}
        self._now_fn = now_fn

    @classmethod
    def for_current_user(cls) -> "AttentionQueue":
        """Construct with defaults from gstack.toml when available.

        Plan 07-04 wires team-scoped config loading; for now this returns
        a queue with CONTEXT default weights.
        """
        return cls()

    def snapshot(self, limit: Optional[int] = None) -> list[AttentionItem]:
        """Return unanswered questions across all teams, sorted by priority desc."""
        items: list[AttentionItem] = []
        teams_root = self._data_dir / "teams"
        if not teams_root.is_dir():
            return []
        for q_path in teams_root.glob("*/sprints/*/questions/*.md"):
            item = self._parse_question(q_path)
            if item is None:
                continue
            items.append(item)
        items.sort(key=lambda i: i.priority_score, reverse=True)
        if limit is not None:
            return items[:limit]
        return items

    def _parse_question(self, q_path: Path) -> Optional[AttentionItem]:
        """Build AttentionItem from one question.md path — returns None when skip."""
        # Skip if sibling answer exists: ../answers/<stem>.md
        answer_path = q_path.parent.parent / "answers" / q_path.name
        if answer_path.exists():
            return None
        # Derive team + sprint_id from path structure:
        # <data>/teams/<team>/sprints/<sprint_id>/questions/<qid>.md
        try:
            sprint_id = q_path.parent.parent.name
            team = q_path.parent.parent.parent.parent.name
        except Exception:
            return None
        try:
            raw = q_path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            meta, _body = parse_frontmatter(raw)
        except Exception:
            meta = {}
        urgency_str = str(meta.get("urgency", "normal")).lower()
        urgency = URGENCY_MAP.get(urgency_str, URGENCY_MAP["normal"])
        blocking = bool(meta.get("blocking", False))
        tags_raw = meta.get("tags", [])
        if isinstance(tags_raw, str):
            tags_raw = [tags_raw]
        tags = tuple(str(t) for t in tags_raw)
        reversibility = str(meta.get("reversibility", "medium")).lower()
        title = str(meta.get("title", q_path.stem))
        try:
            mtime = q_path.stat().st_mtime
        except OSError:
            mtime = self._now_fn()
        age_hours = max(0.0, (self._now_fn() - mtime) / 3600.0)
        score = compute_priority(
            urgency=urgency,
            blocking=blocking,
            age_hours=age_hours,
            tags=tags,
            urgency_weight=self._urgency_weight,
            blocking_weight=self._blocking_weight,
            tag_weights=self._tag_weights,
        )
        return AttentionItem(
            question_path=q_path,
            sprint_id=sprint_id,
            team=team,
            title=title,
            urgency=urgency,
            blocking=blocking,
            age_hours=age_hours,
            tags=tags,
            reversibility=reversibility,
            priority_score=score,
        )


__all__ = ["AttentionItem", "AttentionQueue", "compute_priority", "URGENCY_MAP"]
```

**2. `clawteam/attention/__init__.py` — EDIT from Plan 07-01 skeleton:**

```python
"""Attention substrate — AttentionQueue + watcher + digest.

Public API lands in Plans 07-03 (this plan) and 07-04.
"""
from __future__ import annotations

from clawteam.attention.queue import (
    AttentionItem,
    AttentionQueue,
    URGENCY_MAP,
    compute_priority,
)

__all__ = [
    "AttentionItem",
    "AttentionQueue",
    "URGENCY_MAP",
    "compute_priority",
]
```

**3. Tests:** `tests/attention/__init__.py` (empty) + `tests/attention/test_queue_ranking.py` (~230 LOC). Use monkeypatch CLAWTEAM_DATA_DIR = tmp_path. Write fixture question.md files with textwrap.dedent:

```python
import os
import time
from pathlib import Path
import pytest
from clawteam.attention.queue import AttentionItem, AttentionQueue, compute_priority


def _write_question(data_dir, team, sprint_id, qid, *, urgency="normal", blocking=False, tags=None, reversibility="medium", age_seconds=0):
    qdir = data_dir / "teams" / team / "sprints" / sprint_id / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    path = qdir / f"{qid}.md"
    tag_repr = "[" + ", ".join(tags or []) + "]"
    path.write_text(
        f"---\nurgency: {urgency}\nblocking: {str(blocking).lower()}\ntags: {tag_repr}\n"
        f"reversibility: {reversibility}\ntitle: {qid}\n---\nbody\n",
        encoding="utf-8",
    )
    if age_seconds > 0:
        old = time.time() - age_seconds
        os.utime(path, (old, old))
    return path


def _write_answer(data_dir, team, sprint_id, qid):
    adir = data_dir / "teams" / team / "sprints" / sprint_id / "answers"
    adir.mkdir(parents=True, exist_ok=True)
    (adir / f"{qid}.md").write_text("answer\n", encoding="utf-8")


def test_attention_item_is_frozen(tmp_path):
    item = AttentionItem(
        question_path=tmp_path / "q.md", sprint_id="s", team="t", title="t",
        urgency=1, blocking=False, age_hours=0, tags=(), reversibility="medium",
        priority_score=0.0,
    )
    with pytest.raises((AttributeError, Exception)):
        item.title = "new"  # frozen


def test_compute_priority_basic():
    assert compute_priority(urgency=2, blocking=False, age_hours=1.0, tags=()) == 21.0


def test_compute_priority_blocking():
    assert compute_priority(urgency=1, blocking=True, age_hours=0.0, tags=()) == 15.0


def test_compute_priority_tag_weights():
    score = compute_priority(
        urgency=0, blocking=False, age_hours=0, tags=("design", "security"),
        tag_weights={"design": 2, "security": 3},
    )
    assert score == 5.0


def test_snapshot_empty(tmp_path):
    q = AttentionQueue(data_dir=tmp_path)
    assert q.snapshot() == []


def test_snapshot_skips_answered(tmp_path):
    _write_question(tmp_path, "t1", "s1", "q1")
    _write_question(tmp_path, "t1", "s1", "q2")
    _write_question(tmp_path, "t1", "s1", "q3")
    _write_answer(tmp_path, "t1", "s1", "q2")
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert len(items) == 2
    assert {i.question_id for i in items} == {"q1", "q3"}


def test_snapshot_sort_by_priority_desc(tmp_path):
    _write_question(tmp_path, "t1", "s1", "low", urgency="low")
    _write_question(tmp_path, "t1", "s1", "critical", urgency="critical")
    _write_question(tmp_path, "t1", "s1", "high", urgency="high")
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert [i.question_id for i in items] == ["critical", "high", "low"]


def test_adversarial_critical_at_30s_outranks_normal_at_8h(tmp_path):
    # D-15 adversarial fixture.
    _write_question(tmp_path, "t1", "s1", "crit", urgency="critical", age_seconds=30)
    _write_question(tmp_path, "t1", "s1", "norm", urgency="normal", age_seconds=8 * 3600)
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert items[0].question_id == "crit"
    # Confirm score math: crit = 3*10 + 30/3600 ≈ 30.008; norm = 1*10 + 8 = 18.
    assert items[0].priority_score > items[1].priority_score


def test_snapshot_handles_missing_frontmatter(tmp_path):
    qdir = tmp_path / "teams" / "t1" / "sprints" / "s1" / "questions"
    qdir.mkdir(parents=True)
    (qdir / "plain.md").write_text("just body, no frontmatter\n", encoding="utf-8")
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert len(items) == 1
    assert items[0].urgency == 1  # normal default
    assert items[0].blocking is False


def test_snapshot_cross_teams(tmp_path):
    for team in ("t1", "t2"):
        for sprint in ("sA", "sB"):
            for qid in ("q1", "q2"):
                _write_question(tmp_path, team, sprint, qid)
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert len(items) == 8
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/attention/test_queue_ranking.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "class AttentionItem" clawteam/attention/queue.py` succeeds.
    - `grep -q "def compute_priority" clawteam/attention/queue.py` succeeds.
    - `grep -q "class AttentionQueue" clawteam/attention/queue.py` succeeds.
    - `pytest tests/attention/test_queue_ranking.py -q` reports 10 passed.
  </acceptance_criteria>
  <done>AttentionQueue snapshot works; adversarial ranking fixture proves correctness; Plan 07-04 CLI can call snapshot().</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: watchdog_available + AttentionWatcher polling fallback</name>
  <files>
    clawteam/attention/watcher.py,
    tests/attention/test_watcher.py
  </files>
  <read_first>
    clawteam/browser/__init__.py (find_spec pattern from Phase 6 Plan 06-01),
    clawteam/attention/queue.py (Task 1 output)
  </read_first>
  <behavior>
    - Test 1: `test_watchdog_available_returns_bool` — always bool.
    - Test 2: `test_no_top_level_import` — after `import clawteam.attention.watcher`, sys.modules does NOT contain watchdog unless it was already loaded.
    - Test 3: `test_polling_watcher_fires_callback_on_change` — write a question; start AttentionWatcher(mode='polling', interval=0.05); write a 2nd question; wait 0.2s; assert callback fired with 2 items.
    - Test 4: `test_polling_watcher_stops_cleanly` — start; stop() → no new callbacks.
    - Test 5: `test_watcher_factory_prefers_watchdog_when_available` — monkeypatch watchdog_available → True; construct via make_watcher(); assert mode == "watchdog".
    - Test 6: `test_watcher_factory_falls_back_to_polling` — monkeypatch watchdog_available → False; make_watcher(); assert mode == "polling".
    - Test 7: `test_polling_debounces_repeated_checks` — write Q; wait 0.15s; write A; poll interval 0.05; callback fires at least twice (before+after).
  </behavior>
  <action>
**1. `clawteam/attention/watcher.py` (NEW, ~180 LOC):**

```python
"""AttentionWatcher — watchdog optional + 2-second polling fallback (D-06)."""
from __future__ import annotations

import threading
import time
from importlib.util import find_spec
from pathlib import Path
from typing import Callable, Optional

from clawteam.attention.queue import AttentionItem, AttentionQueue


def watchdog_available() -> bool:
    """Return True if the `watchdog` package is importable (D-06).

    Uses importlib.util.find_spec — zero import-time side effects. Mirrors
    the Phase 6 playwright_available() pattern exactly.
    """
    return find_spec("watchdog") is not None


class AttentionWatcher:
    """Fire a callback whenever the AttentionQueue state changes.

    Two modes:
    - 'watchdog': FS events via the optional watchdog package (low latency).
    - 'polling' : poll every interval_seconds (2.0 default) and diff snapshots.

    Both modes call on_change(items: list[AttentionItem]) synchronously from
    their internal thread. Callbacks should be fast or hand off to a queue.
    """

    def __init__(
        self,
        queue: AttentionQueue,
        on_change: Callable[[list[AttentionItem]], None],
        *,
        mode: str = "auto",  # "auto" | "polling" | "watchdog"
        interval_seconds: float = 2.0,
    ) -> None:
        self._queue = queue
        self._on_change = on_change
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._observer = None  # watchdog Observer when mode='watchdog'
        if mode == "auto":
            mode = "watchdog" if watchdog_available() else "polling"
        self.mode = mode

    def start(self) -> None:
        """Start watching. Idempotent — safe to call repeatedly."""
        if self._thread is not None and self._thread.is_alive():
            return
        if self.mode == "watchdog" and watchdog_available():
            self._start_watchdog()
        else:
            self._start_polling()

    def stop(self) -> None:
        """Stop watching. Blocks until worker exits."""
        self._stop_event.set()
        if self._observer is not None:
            try:
                self._observer.stop()
                self._observer.join(timeout=2.0)
            except Exception:
                pass
            self._observer = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ── internals ────────────────────────────────────────────────

    def _start_polling(self) -> None:
        last: Optional[tuple[str, ...]] = None

        def loop():
            nonlocal last
            while not self._stop_event.is_set():
                try:
                    items = self._queue.snapshot()
                    digest = tuple(sorted(
                        f"{i.question_path}:{i.age_hours:.4f}" for i in items
                    ))
                    if digest != last:
                        last = digest
                        try:
                            self._on_change(items)
                        except Exception:
                            pass
                except Exception:
                    pass
                self._stop_event.wait(self._interval)

        self._thread = threading.Thread(target=loop, daemon=True, name="attend-polling")
        self._thread.start()

    def _start_watchdog(self) -> None:
        try:
            from watchdog.observers import Observer  # type: ignore[import-not-found]
            from watchdog.events import FileSystemEventHandler  # type: ignore[import-not-found]
        except Exception:  # pragma: no cover — defensive
            self.mode = "polling"
            self._start_polling()
            return

        class _Handler(FileSystemEventHandler):
            def __init__(inner_self, outer: "AttentionWatcher"):
                inner_self.outer = outer

            def on_any_event(inner_self, event):
                try:
                    items = inner_self.outer._queue.snapshot()
                    inner_self.outer._on_change(items)
                except Exception:
                    pass

        self._observer = Observer()
        self._observer.schedule(
            _Handler(self), str(self._queue._data_dir / "teams"), recursive=True
        )
        self._observer.start()


def make_watcher(
    queue: AttentionQueue,
    on_change: Callable[[list[AttentionItem]], None],
    *,
    interval_seconds: float = 2.0,
) -> AttentionWatcher:
    """Factory — auto-picks watchdog if available; else polling."""
    return AttentionWatcher(
        queue, on_change, mode="auto", interval_seconds=interval_seconds
    )


__all__ = ["AttentionWatcher", "make_watcher", "watchdog_available"]
```

**2. Tests:** `tests/attention/test_watcher.py` (~160 LOC). Use short poll interval (0.05s) + time.sleep (0.2s) — still deterministic on slow CI. Test 5/6 use monkeypatch on `clawteam.attention.watcher.watchdog_available`.

```python
import sys
import time
from clawteam.attention.queue import AttentionQueue
from clawteam.attention.watcher import (
    AttentionWatcher, make_watcher, watchdog_available,
)


def _write_question(data_dir, qid="q1"):
    d = data_dir / "teams" / "t1" / "sprints" / "s1" / "questions"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{qid}.md").write_text("---\nurgency: high\n---\nbody\n")


def test_watchdog_available_is_bool():
    assert isinstance(watchdog_available(), bool)


def test_polling_fires_callback_on_change(tmp_path):
    queue = AttentionQueue(data_dir=tmp_path)
    received: list = []
    watcher = AttentionWatcher(queue, lambda items: received.append(items), mode="polling", interval_seconds=0.05)
    watcher.start()
    try:
        _write_question(tmp_path, "q1")
        time.sleep(0.2)
        _write_question(tmp_path, "q2")
        time.sleep(0.2)
    finally:
        watcher.stop()
    # Expect ≥2 callback invocations capturing increasing item counts.
    lens = [len(call) for call in received]
    assert max(lens) >= 2


def test_polling_stops_cleanly(tmp_path):
    queue = AttentionQueue(data_dir=tmp_path)
    received: list = []
    watcher = AttentionWatcher(queue, lambda items: received.append(items), mode="polling", interval_seconds=0.05)
    watcher.start()
    time.sleep(0.1)
    watcher.stop()
    before_stop = len(received)
    time.sleep(0.2)  # post-stop; no new callbacks should fire
    assert len(received) == before_stop


def test_factory_prefers_watchdog_when_available(tmp_path, monkeypatch):
    monkeypatch.setattr("clawteam.attention.watcher.watchdog_available", lambda: True)
    queue = AttentionQueue(data_dir=tmp_path)
    w = make_watcher(queue, lambda items: None)
    assert w.mode == "watchdog"


def test_factory_falls_back_to_polling(tmp_path, monkeypatch):
    monkeypatch.setattr("clawteam.attention.watcher.watchdog_available", lambda: False)
    queue = AttentionQueue(data_dir=tmp_path)
    w = make_watcher(queue, lambda items: None)
    assert w.mode == "polling"
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/attention/test_watcher.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def watchdog_available" clawteam/attention/watcher.py` succeeds.
    - `grep -q "class AttentionWatcher" clawteam/attention/watcher.py` succeeds.
    - `grep -q "^import watchdog\|^from watchdog" clawteam/attention/watcher.py` returns NO matches at top-level (only inside _start_watchdog).
    - `pytest tests/attention/test_watcher.py -q` reports green.
  </acceptance_criteria>
  <done>Watcher works with and without watchdog; 2-second polling fallback confirmed.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: build_digest + bucket_age (QUALITY-05)</name>
  <files>
    clawteam/attention/digest.py,
    tests/attention/test_digest.py
  </files>
  <read_first>
    clawteam/attention/queue.py (AttentionItem shape)
  </read_first>
  <behavior>
    - Test 1: `test_bucket_age_boundaries` — 0.5h → "<1h"; 1.5h → "1-2h"; 4h → "2-8h"; 12h → ">8h".
    - Test 2: `test_digest_empty` — build_digest([]) == [].
    - Test 3: `test_digest_groups_by_sprint_and_tag` — 3 items same sprint, 2 same tag → one cluster of 2 + one of 1.
    - Test 4: `test_digest_sorts_by_highest_priority_desc` — 2 clusters; high-score cluster first.
    - Test 5: `test_digest_bucket_age_separates_clusters` — same sprint+tag, ages 0.5h + 4h → 2 clusters.
    - Test 6: `test_digest_untagged_cluster` — item with tags=() → cluster tag == "untagged".
    - Test 7: `test_digest_counts_and_representative_title` — cluster dict has `count` + `representative_title` fields.
  </behavior>
  <action>
**1. `clawteam/attention/digest.py` (NEW, ~90 LOC):**

```python
"""Attention digest — group questions by (sprint, tag, age bucket) for --summary (D-07).

QUALITY-05: surface "4 sprints stalled >2h, 1 CRITICAL, 2 reversible
auto-accept candidates" roll-up view. Plain-text; no TUI widgets.
"""
from __future__ import annotations

from typing import Any

from clawteam.attention.queue import AttentionItem


def bucket_age(age_hours: float) -> str:
    """Return D-07 age bucket: '<1h' | '1-2h' | '2-8h' | '>8h'."""
    if age_hours < 1.0:
        return "<1h"
    if age_hours < 2.0:
        return "1-2h"
    if age_hours < 8.0:
        return "2-8h"
    return ">8h"


def build_digest(items: list[AttentionItem]) -> list[dict[str, Any]]:
    """Group items by (sprint_id, tag_cluster, age_bucket); sort clusters desc.

    Cluster schema:
        {
          'sprint_id': str,
          'tag': str,                 # first tag of representative item, or 'untagged'
          'age_bucket': str,          # bucket_age() result
          'count': int,
          'highest_priority': float,
          'representative_title': str,
          'reversibility_distribution': {'easy': int, 'medium': int, 'hard': int},
        }
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

    result = []
    for (sprint_id, tag, bucket), cluster in clusters.items():
        top = max(cluster, key=lambda i: i.priority_score)
        result.append({
            "sprint_id": sprint_id,
            "tag": tag,
            "age_bucket": bucket,
            "count": len(cluster),
            "highest_priority": top.priority_score,
            "representative_title": top.title,
            "reversibility_distribution": _rev_dist(cluster),
        })
    result.sort(key=lambda r: r["highest_priority"], reverse=True)
    return result


__all__ = ["build_digest", "bucket_age"]
```

**2. EDIT `clawteam/attention/__init__.py` — add new exports:**

```python
from clawteam.attention.digest import build_digest, bucket_age
from clawteam.attention.watcher import (
    AttentionWatcher, make_watcher, watchdog_available,
)

__all__ = [
    "AttentionItem", "AttentionQueue", "URGENCY_MAP", "compute_priority",
    "build_digest", "bucket_age",
    "AttentionWatcher", "make_watcher", "watchdog_available",
]
```

**3. `tests/attention/test_digest.py` (~130 LOC):**

```python
from pathlib import Path
from clawteam.attention.queue import AttentionItem
from clawteam.attention.digest import build_digest, bucket_age


def _item(sprint_id="s1", qid="q", tags=(), age_hours=0.5, score=10.0, reversibility="medium"):
    return AttentionItem(
        question_path=Path(f"/tmp/{qid}.md"), sprint_id=sprint_id, team="t",
        title=qid, urgency=1, blocking=False, age_hours=age_hours, tags=tags,
        reversibility=reversibility, priority_score=score,
    )


def test_bucket_age_boundaries():
    assert bucket_age(0.0) == "<1h"
    assert bucket_age(0.999) == "<1h"
    assert bucket_age(1.0) == "1-2h"
    assert bucket_age(1.9) == "1-2h"
    assert bucket_age(2.0) == "2-8h"
    assert bucket_age(7.9) == "2-8h"
    assert bucket_age(8.0) == ">8h"
    assert bucket_age(100.0) == ">8h"


def test_digest_empty():
    assert build_digest([]) == []


def test_digest_groups_by_sprint_and_tag():
    items = [
        _item(qid="a", tags=("design",)),
        _item(qid="b", tags=("design",)),
        _item(qid="c", tags=("security",)),
    ]
    clusters = build_digest(items)
    # 2 clusters: (s1, design, <1h) count=2; (s1, security, <1h) count=1.
    counts = sorted(c["count"] for c in clusters)
    assert counts == [1, 2]


def test_digest_sorts_by_priority_desc():
    items = [
        _item(qid="low", tags=("a",), score=5.0),
        _item(qid="high", tags=("b",), score=25.0),
    ]
    clusters = build_digest(items)
    assert clusters[0]["tag"] == "b"
    assert clusters[1]["tag"] == "a"


def test_digest_bucket_splits_by_age():
    items = [
        _item(qid="a", tags=("x",), age_hours=0.2),  # <1h
        _item(qid="b", tags=("x",), age_hours=4.0),  # 2-8h
    ]
    clusters = build_digest(items)
    assert len(clusters) == 2
    buckets = sorted(c["age_bucket"] for c in clusters)
    assert buckets == ["2-8h", "<1h"]


def test_digest_untagged():
    items = [_item(qid="plain", tags=())]
    clusters = build_digest(items)
    assert clusters[0]["tag"] == "untagged"


def test_digest_reversibility_distribution():
    items = [
        _item(qid="a", reversibility="easy", tags=("x",)),
        _item(qid="b", reversibility="hard", tags=("x",)),
        _item(qid="c", reversibility="easy", tags=("x",)),
    ]
    clusters = build_digest(items)
    assert len(clusters) == 1
    dist = clusters[0]["reversibility_distribution"]
    assert dist["easy"] == 2 and dist["hard"] == 1 and dist["medium"] == 0


def test_digest_schema_fields():
    items = [_item(qid="x", tags=("design",))]
    clusters = build_digest(items)
    assert set(clusters[0].keys()) >= {
        "sprint_id", "tag", "age_bucket", "count",
        "highest_priority", "representative_title", "reversibility_distribution",
    }
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/attention/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def build_digest" clawteam/attention/digest.py` succeeds.
    - `grep -q "def bucket_age" clawteam/attention/digest.py` succeeds.
    - `pytest tests/attention/test_digest.py -q` reports 7 passed.
    - Full attention dir: `pytest tests/attention/ -q` reports all green.
  </acceptance_criteria>
  <done>Digest grouping works; ready for Plan 07-04 `--summary` flag wiring.</done>
</task>

</tasks>

<verification>
1. `pytest tests/attention/ -q` — all green.
2. `python -c "from clawteam.attention import AttentionQueue, build_digest, make_watcher, watchdog_available; print('ok')"` — prints ok.
</verification>

<success_criteria>
- All 3 task acceptance criteria met.
- D-15 adversarial fixture (critical@30s > normal@8h) proven in test.
- Polling fallback proven without watchdog installed.
- Digest grouping proven for (sprint, tag, age bucket) clusters.
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-03-SUMMARY.md`.
</output>
