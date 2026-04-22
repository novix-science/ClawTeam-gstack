"""Cost substrate — tracker + dashboard + fallback + cache_tracker.

Plan 07-05 shipped pricing + rollup + tracker.
Plan 07-06 (this plan) ships fallback + cache_tracker.
Plan 07-07 wires the dashboard into ``clawteam team show``.
"""
from __future__ import annotations

from clawteam.cost.cache_tracker import HEALTHY_THRESHOLD, CacheTracker
from clawteam.cost.dashboard import render_team, render_text
from clawteam.cost.fallback import (
    FALLBACK_LADDER,
    TIER_TO_CANONICAL,
    apply_fallback,
)
from clawteam.cost.pricing import (
    MODEL_PRICING,
    ModelTier,
    calculate_cost_usd,
    resolve_tier,
)
from clawteam.cost.rollup import CostRollup
from clawteam.cost.tracker import CostTracker

__all__ = [
    "MODEL_PRICING",
    "ModelTier",
    "calculate_cost_usd",
    "resolve_tier",
    "CostRollup",
    "CostTracker",
    # Plan 07-06 additions:
    "apply_fallback",
    "FALLBACK_LADDER",
    "TIER_TO_CANONICAL",
    "CacheTracker",
    "HEALTHY_THRESHOLD",
    # Plan 07-07 additions:
    "render_team",
    "render_text",
]
