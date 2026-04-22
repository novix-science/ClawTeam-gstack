"""AttentionQueue — cross-sprint stateless read-side priority queue (D-04/D-05).

Each snapshot() call globs teams/*/sprints/*/questions/*.md, filters out
those with sibling answers/*.md, parses frontmatter, computes priority,
sorts descending. Zero persisted state — the filesystem IS the ledger.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
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
        self._data_dir = Path(data_dir) if data_dir is not None else get_data_dir()
        self._urgency_weight = urgency_weight
        self._blocking_weight = blocking_weight
        self._tag_weights = dict(tag_weights or {})
        self._now_fn = now_fn

    @classmethod
    def for_current_user(cls) -> "AttentionQueue":
        """Construct with defaults from gstack.toml when available.

        Plan 07-04 wires team-scoped config loading; for now this returns
        a queue with CONTEXT default weights.
        """
        return cls()

    @property
    def data_dir(self) -> Path:
        return self._data_dir

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
        except Exception:  # pragma: no cover — defensive
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
        try:
            tags = tuple(str(t) for t in tags_raw)
        except TypeError:
            tags = ()
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
