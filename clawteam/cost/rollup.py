"""CostRollup — frozen dataclass used by the cost dashboard (Plan 07-07).

Schema locked by 07-CONTEXT.md <specifics>: 9 fields keyed by
(team, sprint_id, agent) with token counts broken down per tier +
aggregate cost_usd + cache_hit_rate + a [period_start, period_end]
window. ``sprint_id=None`` and ``agent=None`` indicate a team-level
rollup (vs. per-sprint or per-agent slice).

``cache_hit_rate`` is populated by :mod:`clawteam.cost.cache_tracker`
(Plan 07-06); the rollup emitted directly by :class:`CostTracker`
carries ``0.0`` here — external callers merge the two sources.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CostRollup:
    team: str
    sprint_id: Optional[str]  # None = team-level rollup
    agent: Optional[str]  # None = non-agent-specific slice
    tokens_opus: int
    tokens_sonnet: int
    tokens_haiku: int
    cost_usd: float
    cache_hit_rate: float  # 0.0 when no ClaudeApiResponse events observed
    period_start: datetime
    period_end: datetime


__all__ = ["CostRollup"]
