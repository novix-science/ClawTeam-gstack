"""Cost dashboard rendering — consumed by ``clawteam team show`` (D-09).

Pure functions. Input: team name, :class:`~clawteam.cost.tracker.CostTracker`,
:class:`~clawteam.cost.cache_tracker.CacheTracker`, optional active-agent list.
Output: a structured dict (suitable for JSON mode) plus a short ``render_text``
one-liner for human mode.

The dashboard layer does NOT subscribe to events or keep state — it only
reads from the tracker + cache-tracker instances supplied by the caller. This
keeps the rendering layer test-isolable from the event-driven accounting
layer (Plans 07-05 / 07-06) and lets Plan 07-07 CLI integration wire a fresh
tracker per ``clawteam team show`` invocation without event-ordering worries.
"""
from __future__ import annotations

from typing import Any, Optional

from clawteam.cost.cache_tracker import HEALTHY_THRESHOLD, CacheTracker
from clawteam.cost.tracker import CostTracker


def render_team(
    team: str,
    tracker: CostTracker,
    cache_tracker: Optional[CacheTracker] = None,
    *,
    active_agents: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Return the structured dashboard dict for ``clawteam team show``.

    :param team: Team name (used verbatim in the output dict ``team`` key).
    :param tracker: A :class:`CostTracker` — may be freshly constructed
        (empty) or populated via event emission prior to this call.
    :param cache_tracker: Optional :class:`CacheTracker` — when ``None``,
        ``cache_hit_rate`` defaults to ``0.0`` and ``cache_healthy`` to
        ``False``. Callers that don't need cache observability can omit.
    :param active_agents: Optional active-agent names from
        :meth:`SprintConductor.active_agents`. Empty/None -> empty list.

    Returns a 14-key dict with fields fully described in Plan 07-07
    ``must_haves.truths``. Notable fields:

    - ``status``: always ``"ok"`` for a live render; Plan 07-07 CLI wraps
      the call in try/except and may substitute ``"unavailable"``.
    - ``spend_percent``: 0.0 when ``budget_usd == 0`` (no div-zero).
    - ``alarms_fired``: sorted ascending list of threshold crossings
      already fired by the tracker (e.g. ``[50, 80]``).
    - ``cache_healthy``: True when ``cache_hit_rate > HEALTHY_THRESHOLD``
      (strict ``>``; break-even 0.5 is NOT healthy — matches Plan 07-06).
    """
    team_rollup = tracker.rollup_team()
    cost_usd = tracker.current_spend_usd()
    # ``CostTracker`` does not expose a public ``budget_usd`` getter via
    # property-less access; ``.budget_usd`` is a @property in 07-05 impl.
    budget = tracker.budget_usd
    spend_pct = tracker.spend_percent()
    cache_rate = (
        cache_tracker.cache_hit_rate() if cache_tracker is not None else 0.0
    )
    cache_healthy = cache_rate > HEALTHY_THRESHOLD
    actives = list(active_agents or [])
    # ``_fired_alarms`` is an internal set on the tracker; we sort the
    # snapshot here so downstream consumers can treat ``alarms_fired`` as
    # an order-stable list (JSON mode + rich rendering both need this).
    fired = sorted(tracker._fired_alarms)
    return {
        "team": team,
        "status": "ok",
        "cost_usd": cost_usd,
        "budget_usd": budget,
        "spend_percent": spend_pct,
        "per_agent": tracker.rollup_by_agent(),
        "per_sprint": tracker.rollup_by_sprint(),
        "tokens_opus": team_rollup.tokens_opus,
        "tokens_sonnet": team_rollup.tokens_sonnet,
        "tokens_haiku": team_rollup.tokens_haiku,
        "cache_hit_rate": cache_rate,
        "cache_healthy": cache_healthy,
        "alarms_fired": fired,
        "active_agents": actives,
        "active_agent_count": len(actives),
    }


def render_text(data: dict[str, Any]) -> str:
    """Render a plain-text one-liner summary for team show's non-table rows.

    Format (with budget):
        ``Cost - $<spent>.00 / $<budget>.00 (<pct>%) | cache hit: <X>% | active agents: <N>``

    Format (no budget):
        ``Cost - $<spent>.00 (no budget) | cache hit: <X>% | active agents: <N>``
    """
    pct = data.get("spend_percent", 0.0)
    cost = data.get("cost_usd", 0.0)
    budget = data.get("budget_usd", 0.0)
    cache_rate = data.get("cache_hit_rate", 0.0)
    active_count = data.get("active_agent_count", 0)
    if budget > 0:
        return (
            f"${cost:.2f} / ${budget:.2f} ({pct:.0f}%) | "
            f"cache hit: {cache_rate * 100:.0f}% | "
            f"active agents: {active_count}"
        )
    return (
        f"${cost:.2f} (no budget) | "
        f"cache hit: {cache_rate * 100:.0f}% | "
        f"active agents: {active_count}"
    )


__all__ = ["render_team", "render_text"]
