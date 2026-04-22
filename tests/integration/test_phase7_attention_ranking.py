"""Phase 7 Plan 07-09 Task 2: AttentionQueue 30-fixture ranking (D-15 / INT-03).

Locks INT-03 floor: 30 fixture questions across 5 sprints x 3 teams — the
D-05 priority formula (urgency*weight + blocking? + age_hours + tag_weights)
must rank items in monotonically descending priority_score.

Adversarial fixture explicitly asserted: urgency=critical @ 30s outranks
urgency=normal @ 8h by a comfortable margin (critical*10 + 30/3600 ≈ 30.008
vs normal*10 + 8 = 18 — 12-point spread).

Exercises the already-shipped Plan 07-03 AttentionQueue package directly
(no CLI hop).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

from clawteam.attention.queue import AttentionQueue, compute_priority


def _write(
    data_dir: Path,
    team: str,
    sprint: str,
    qid: str,
    *,
    urgency: str = "normal",
    blocking: bool = False,
    tags: list[str] | None = None,
    reversibility: str = "medium",
    age_seconds: float = 0,
) -> Path:
    """Write a question.md fixture with the given frontmatter."""
    qdir = data_dir / "teams" / team / "sprints" / sprint / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    path = qdir / f"{qid}.md"
    tag_repr = "[" + ", ".join(tags or []) + "]"
    path.write_text(
        f"---\nurgency: {urgency}\nblocking: {str(blocking).lower()}\n"
        f"tags: {tag_repr}\nreversibility: {reversibility}\n"
        f"title: {qid}\n---\nbody\n",
        encoding="utf-8",
    )
    if age_seconds > 0:
        old = time.time() - age_seconds
        os.utime(path, (old, old))
    return path


def test_thirty_questions_ranked_by_formula(tmp_path):
    """D-15: 30 fixture questions across 5 sprints x 3 teams — monotonic score desc."""
    # 5 sprints x 3 teams x 2 questions each = 30 questions.
    urgencies = ["critical", "high", "normal", "low", "normal", "high"]
    for t_idx, team in enumerate(("teamA", "teamB", "teamC")):
        for s_idx, sprint in enumerate([f"s{i}" for i in range(5)]):
            for q_idx, qid in enumerate(
                [f"q{i}-{team}-{sprint}" for i in range(2)]
            ):
                _write(
                    tmp_path,
                    team,
                    sprint,
                    qid,
                    urgency=urgencies[(q_idx + s_idx) % len(urgencies)],
                    blocking=(q_idx % 2 == 0),
                    tags=["design"] if q_idx == 1 else [],
                    age_seconds=(t_idx + s_idx + q_idx) * 60,
                )
    queue = AttentionQueue(data_dir=tmp_path)
    items = queue.snapshot()
    assert len(items) == 30
    # Monotonically descending priority_score ordering.
    scores = [i.priority_score for i in items]
    assert scores == sorted(scores, reverse=True)
    # Top item should be one of the critical+blocking combinations
    # (at least high-urgency, urgency bucket >= 2).
    assert items[0].urgency >= 2


def test_cross_team_queue_aggregates(tmp_path):
    """Snapshot spans multiple teams, items interleaved by priority."""
    for team in ("alpha", "beta", "gamma"):
        _write(tmp_path, team, "s1", f"q-{team}", urgency="high")
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    teams_present = {i.team for i in items}
    assert teams_present == {"alpha", "beta", "gamma"}


def test_adversarial_critical_at_30s_beats_normal_at_8h(tmp_path):
    """D-15 adversarial fixture — critical@30s must outrank normal@8h.

    Formula math (default weights urgency=10, blocking=5):
      critical = 3*10 + 30/3600  ≈ 30.008
      normal   = 1*10 + 8         = 18.0
      Spread   ≈ 12 points — comfortable margin even under clock jitter.
    """
    _write(tmp_path, "t", "s1", "crit", urgency="critical", age_seconds=30)
    _write(tmp_path, "t", "s1", "norm", urgency="normal", age_seconds=8 * 3600)
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert items[0].question_id == "crit"
    # Spread exceeds 10-point safety margin.
    assert items[0].priority_score > items[1].priority_score + 10


def test_tag_weights_shift_priority(tmp_path):
    """With tag_weights={security:10}, a tagged-normal outranks plain-normal."""
    _write(tmp_path, "t", "s1", "tagged", urgency="normal", tags=["security"])
    _write(tmp_path, "t", "s1", "plain", urgency="normal")
    queue = AttentionQueue(
        data_dir=tmp_path,
        tag_weights={"security": 10},
    )
    items = queue.snapshot()
    assert items[0].question_id == "tagged"
    assert items[1].question_id == "plain"


def test_compute_priority_matches_observed(tmp_path):
    """Per-item priority_score matches the pure compute_priority function."""
    _write(
        tmp_path,
        "t",
        "s",
        "q",
        urgency="high",
        blocking=True,
        tags=["design"],
        age_seconds=3600,
    )
    queue = AttentionQueue(data_dir=tmp_path, tag_weights={"design": 2})
    items = queue.snapshot()
    assert len(items) == 1
    expected = compute_priority(
        urgency=2,
        blocking=True,
        age_hours=1.0,
        tags=("design",),
        urgency_weight=10,
        blocking_weight=5,
        tag_weights={"design": 2},
    )
    # Age may drift slightly under clock jitter; allow 0.1h tolerance.
    assert abs(items[0].priority_score - expected) < 0.1
