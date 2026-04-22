"""Plan 07-03 Task 1 — AttentionQueue snapshot + priority ranking (D-04/D-05/D-15)."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest


from clawteam.attention.queue import (
    AttentionItem,
    AttentionQueue,
    compute_priority,
)


# ─────────────────────────── helpers ───────────────────────────


def _write_question(
    data_dir: Path,
    team: str,
    sprint_id: str,
    qid: str,
    *,
    urgency: str = "normal",
    blocking: bool = False,
    tags: list[str] | None = None,
    reversibility: str = "medium",
    age_seconds: float = 0,
) -> Path:
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


def _write_answer(data_dir: Path, team: str, sprint_id: str, qid: str) -> Path:
    adir = data_dir / "teams" / team / "sprints" / sprint_id / "answers"
    adir.mkdir(parents=True, exist_ok=True)
    path = adir / f"{qid}.md"
    path.write_text("answer\n", encoding="utf-8")
    return path


# ─────────────────────────── tests ───────────────────────────


def test_attention_item_is_frozen(tmp_path: Path) -> None:
    item = AttentionItem(
        question_path=tmp_path / "q.md",
        sprint_id="s",
        team="t",
        title="t",
        urgency=1,
        blocking=False,
        age_hours=0.0,
        tags=(),
        reversibility="medium",
        priority_score=0.0,
    )
    with pytest.raises((AttributeError, Exception)):
        item.title = "new"  # type: ignore[misc]


def test_compute_priority_formula_basic() -> None:
    # urgency=2, blocking=False, age=1h, tags=() → 2*10 + 0 + 1 + 0 = 21
    assert compute_priority(urgency=2, blocking=False, age_hours=1.0, tags=()) == 21.0


def test_compute_priority_adds_blocking() -> None:
    # urgency=1, blocking=True, age=0, tags=() → 1*10 + 5 + 0 + 0 = 15
    assert compute_priority(urgency=1, blocking=True, age_hours=0.0, tags=()) == 15.0


def test_compute_priority_adds_tag_weights() -> None:
    score = compute_priority(
        urgency=0,
        blocking=False,
        age_hours=0.0,
        tags=("design", "security"),
        tag_weights={"design": 2, "security": 3},
    )
    assert score == 5.0


def test_snapshot_empty_when_no_questions(tmp_path: Path) -> None:
    q = AttentionQueue(data_dir=tmp_path)
    assert q.snapshot() == []


def test_snapshot_skips_answered_questions(tmp_path: Path) -> None:
    _write_question(tmp_path, "t1", "s1", "q1")
    _write_question(tmp_path, "t1", "s1", "q2")
    _write_question(tmp_path, "t1", "s1", "q3")
    _write_answer(tmp_path, "t1", "s1", "q2")
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert len(items) == 2
    assert {i.question_id for i in items} == {"q1", "q3"}


def test_snapshot_sorts_by_priority_desc(tmp_path: Path) -> None:
    _write_question(tmp_path, "t1", "s1", "low", urgency="low")
    _write_question(tmp_path, "t1", "s1", "critical", urgency="critical")
    _write_question(tmp_path, "t1", "s1", "high", urgency="high")
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert [i.question_id for i in items] == ["critical", "high", "low"]


def test_critical_at_30s_outranks_normal_at_8h(tmp_path: Path) -> None:
    """D-15 adversarial fixture — must prove bug-for-bug correctness of formula."""
    _write_question(tmp_path, "t1", "s1", "crit", urgency="critical", age_seconds=30)
    _write_question(
        tmp_path, "t1", "s1", "norm", urgency="normal", age_seconds=8 * 3600
    )
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert items[0].question_id == "crit"
    # crit score ≈ 3*10 + 30/3600 ≈ 30.008; norm ≈ 1*10 + 8.0 = 18.0
    assert items[0].priority_score > items[1].priority_score
    assert items[0].priority_score > 30.0
    assert items[1].priority_score >= 18.0


def test_snapshot_handles_malformed_frontmatter(tmp_path: Path) -> None:
    qdir = tmp_path / "teams" / "t1" / "sprints" / "s1" / "questions"
    qdir.mkdir(parents=True)
    # No frontmatter at all → defaults (urgency=normal, blocking=False).
    (qdir / "plain.md").write_text("just body, no frontmatter\n", encoding="utf-8")
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert len(items) == 1
    assert items[0].urgency == 1  # normal
    assert items[0].blocking is False


def test_snapshot_cross_teams(tmp_path: Path) -> None:
    """2 teams × 2 sprints × 2 questions = 8 items."""
    for team in ("t1", "t2"):
        for sprint in ("sA", "sB"):
            for qid in ("q1", "q2"):
                _write_question(tmp_path, team, sprint, qid)
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert len(items) == 8
    teams = {i.team for i in items}
    sprints = {i.sprint_id for i in items}
    assert teams == {"t1", "t2"}
    assert sprints == {"sA", "sB"}
