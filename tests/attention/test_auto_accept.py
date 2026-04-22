"""Plan 07-04 Task 1 — auto_accept helper tests.

Covers D-08: `--auto-accept-reversible` applies ONLY to questions whose
frontmatter has `reversibility: easy`. Preview filters + sorts; apply
writes answer.md with `auto_accepted: true` frontmatter + TTL metadata;
idempotent (skips pre-existing answer files).
"""
from __future__ import annotations

from pathlib import Path

from clawteam.attention.auto_accept import (
    DEFAULT_TTL_MINUTES,
    apply_auto_accept,
    preview_auto_accept,
)
from clawteam.attention.queue import AttentionItem


def _mk_item(
    tmp_path: Path,
    qid: str = "q1",
    reversibility: str = "easy",
    score: float = 10.0,
) -> AttentionItem:
    """Build a realistic AttentionItem + on-disk question.md pair."""
    qdir = tmp_path / "teams" / "t" / "sprints" / "s" / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    qpath = qdir / f"{qid}.md"
    qpath.write_text("---\nurgency: high\n---\nbody\n")
    return AttentionItem(
        question_path=qpath,
        sprint_id="s",
        team="t",
        title=qid,
        urgency=2,
        blocking=False,
        age_hours=0.5,
        tags=(),
        reversibility=reversibility,
        priority_score=score,
    )


def test_preview_filters_easy_only(tmp_path: Path) -> None:
    items = [
        _mk_item(tmp_path, "a", "easy"),
        _mk_item(tmp_path, "b", "medium"),
        _mk_item(tmp_path, "c", "hard"),
    ]
    got = preview_auto_accept(items)
    assert {i.question_id for i in got} == {"a"}


def test_preview_preserves_priority_order(tmp_path: Path) -> None:
    items = [
        _mk_item(tmp_path, "lo", "easy", score=5.0),
        _mk_item(tmp_path, "hi", "easy", score=25.0),
        _mk_item(tmp_path, "mid", "easy", score=10.0),
    ]
    preview = preview_auto_accept(items)
    assert [i.question_id for i in preview] == ["hi", "mid", "lo"]


def test_apply_writes_answer_file(tmp_path: Path) -> None:
    item = _mk_item(tmp_path, "q1", "easy")
    result = apply_auto_accept([item])
    assert result["applied"] == ["q1"]
    assert result["skipped"] == []
    answer = item.question_path.parent.parent / "answers" / item.question_path.name
    assert answer.exists()
    txt = answer.read_text(encoding="utf-8")
    assert "auto_accepted: true" in txt


def test_apply_contains_ttl_metadata(tmp_path: Path) -> None:
    item = _mk_item(tmp_path, "q1", "easy")
    apply_auto_accept([item])
    answer = item.question_path.parent.parent / "answers" / item.question_path.name
    txt = answer.read_text(encoding="utf-8")
    assert "auto_accepted_at:" in txt
    assert f"ttl_minutes: {DEFAULT_TTL_MINUTES}" in txt


def test_apply_body_contains_placeholder(tmp_path: Path) -> None:
    item = _mk_item(tmp_path, "q1", "easy")
    apply_auto_accept([item])
    answer = item.question_path.parent.parent / "answers" / item.question_path.name
    assert "Auto-accepted per --auto-accept-reversible" in answer.read_text(
        encoding="utf-8"
    )


def test_apply_idempotent_skips_existing(tmp_path: Path) -> None:
    item = _mk_item(tmp_path, "q1", "easy")
    first = apply_auto_accept([item])
    assert first["applied"] == ["q1"]
    second = apply_auto_accept([item])
    assert second["applied"] == []
    assert second["skipped"] == ["q1"]


def test_apply_returns_applied_count(tmp_path: Path) -> None:
    item1 = _mk_item(tmp_path, "easy1", "easy")
    item2 = _mk_item(tmp_path, "easy2", "easy")
    result = apply_auto_accept([item1, item2])
    assert sorted(result["applied"]) == ["easy1", "easy2"]
    assert result["skipped"] == []


def test_apply_skips_non_easy(tmp_path: Path) -> None:
    easy = _mk_item(tmp_path, "easy1", "easy")
    hard = _mk_item(tmp_path, "hard1", "hard")
    medium = _mk_item(tmp_path, "med1", "medium")
    result = apply_auto_accept([easy, hard, medium])
    assert result["applied"] == ["easy1"]
    assert sorted(result["skipped"]) == ["hard1", "med1"]
