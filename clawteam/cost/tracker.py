"""CostTracker — event-driven cost aggregator (Phase 7 D-09, D-10).

Subscribes to :class:`~clawteam.events.types.ToolCallCompleted` on the
:class:`~clawteam.events.bus.EventBus`. Maintains in-memory aggregates
keyed by ``(team, sprint_id, agent)``. Emits
:class:`~clawteam.events.types.BudgetAlarmReached` on 50/80/100%
threshold crossings — exactly once per threshold per run (D-10 no
duplicates).

**Scope boundary:** The tracker does NOT apply model fallback — that is
Plan 07-06 :mod:`clawteam.cost.fallback` policy. Alarms here are
advisory-only; the fallback layer reads the alarm signal and downgrades
the next outgoing model call.

When an incoming :class:`ToolCallCompleted` arrives with
``cost_usd == 0.0`` (e.g. the Claude wrapper didn't supply a
pre-computed cost) the tracker falls back to
:func:`clawteam.cost.pricing.calculate_cost_usd` using the event's
``model`` / ``tokens_input`` / ``tokens_output`` trio.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timezone
from typing import Callable, Optional

from clawteam.cost.pricing import calculate_cost_usd, resolve_tier
from clawteam.cost.rollup import CostRollup
from clawteam.events.bus import EventBus
from clawteam.events.types import BudgetAlarmReached, ToolCallCompleted


class CostTracker:
    """Per-team cost aggregator driven by ``ToolCallCompleted`` events.

    :param team: Team name — the tracker ignores events with a different
        ``team_name`` so multiple trackers can share a single bus.
    :param budget_usd: Nominal monthly budget (from
        ``gstack.toml [cost] budget_usd``); alarms fire when the
        cumulative spend crosses a percentage threshold of this budget.
    :param alarm_percent: List of thresholds (default ``[50, 80, 100]``);
        each threshold fires at most once per tracker instance
        lifetime (no re-fire when spend drops and rises again).
    :param bus: The event bus — if ``None``, the tracker is created
        without a subscription (useful for unit tests that want to
        feed handlers directly).
    """

    def __init__(
        self,
        team: str,
        *,
        budget_usd: float = 100.0,
        alarm_percent: Optional[list[float]] = None,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._team = team
        self._budget_usd = float(budget_usd)
        self._alarm_percent = sorted(alarm_percent or [50.0, 80.0, 100.0])
        self._fired_alarms: set[float] = set()
        self._bus = bus
        self._lock = threading.RLock()
        # Aggregates.
        self._by_agent: dict[str, float] = defaultdict(float)
        self._by_sprint: dict[str, float] = defaultdict(float)
        self._by_agent_sprint: dict[tuple[str, str], float] = defaultdict(float)
        # Token counts by tier (sum of input + output).
        self._tokens_by_tier: dict[str, int] = defaultdict(int)
        self._total: float = 0.0
        self._period_start = datetime.now(timezone.utc)
        self._period_end = self._period_start
        # Store the exact bound-method reference we subscribed so
        # ``close()`` can call ``bus.unsubscribe`` with an identity match.
        # Bound methods are created fresh on every attribute access
        # (``self.m is self.m`` is False), so we must pin a single ref.
        self._handler: Optional[Callable[[ToolCallCompleted], None]] = None
        if bus is not None:
            self._handler = self._on_tool_call
            bus.subscribe(ToolCallCompleted, self._handler)

    # ── public API ─────────────────────────────────────────────────────

    @property
    def team(self) -> str:
        return self._team

    @property
    def budget_usd(self) -> float:
        return self._budget_usd

    def current_spend_usd(self) -> float:
        with self._lock:
            return self._total

    def spend_percent(self) -> float:
        if self._budget_usd <= 0:
            return 0.0
        return (self.current_spend_usd() / self._budget_usd) * 100.0

    def rollup_by_agent(self) -> dict[str, float]:
        """Return a copy of the per-agent cost_usd map."""
        with self._lock:
            return dict(self._by_agent)

    def rollup_by_sprint(self) -> dict[str, float]:
        """Return a copy of the per-sprint cost_usd map."""
        with self._lock:
            return dict(self._by_sprint)

    def rollup_by_agent_sprint(self) -> dict[tuple[str, str], float]:
        """Return a copy of the (agent, sprint_id) -> cost_usd map."""
        with self._lock:
            return dict(self._by_agent_sprint)

    def fired_alarms(self) -> list[float]:
        """Return a sorted snapshot of thresholds (%) already fired.

        Public accessor for :attr:`_fired_alarms`. Taken under the
        tracker lock so callers (e.g. the dashboard render layer) never
        observe a ``RuntimeError: Set changed size during iteration``
        race with the concurrent ``_on_tool_call`` mutator.
        """
        with self._lock:
            return sorted(self._fired_alarms)

    def close(self) -> None:
        """Unsubscribe this tracker's handler from the event bus.

        Deterministic teardown — callers that construct a tracker for a
        bounded scope (e.g. short-lived CLI invocations that build a
        fresh tracker per call) MUST call ``close()`` (or use the
        context-manager protocol) to avoid leaking one handler per
        invocation on the global event bus. In-process reruns (tests,
        long-lived daemons) would otherwise accumulate unbounded
        subscriptions, each receiving every future event forever.
        """
        if self._bus is not None and self._handler is not None:
            self._bus.unsubscribe(ToolCallCompleted, self._handler)
            self._handler = None

    def __enter__(self) -> "CostTracker":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def rollup_team(self) -> CostRollup:
        """Return a team-level :class:`CostRollup` snapshot."""
        with self._lock:
            return CostRollup(
                team=self._team,
                sprint_id=None,
                agent=None,
                tokens_opus=self._tokens_by_tier.get("opus", 0),
                tokens_sonnet=self._tokens_by_tier.get("sonnet", 0),
                tokens_haiku=self._tokens_by_tier.get("haiku", 0),
                cost_usd=self._total,
                cache_hit_rate=0.0,  # populated by cache_tracker (Plan 07-06)
                period_start=self._period_start,
                period_end=self._period_end,
            )

    # ── event handler ─────────────────────────────────────────────────

    def _on_tool_call(self, event: ToolCallCompleted) -> None:
        if event.team_name != self._team:
            return
        cost = float(event.cost_usd)
        if cost <= 0.0:
            # Backstop: compute from pricing table when caller didn't
            # supply cost_usd (e.g. gh / lighthouse wrappers that don't
            # know the model, or pricing was unavailable at emit time).
            cost = calculate_cost_usd(
                event.model, event.tokens_input, event.tokens_output
            )
        newly_fired: list[float] = []
        with self._lock:
            prev_total = self._total
            self._total += cost
            if event.agent:
                self._by_agent[event.agent] += cost
            if event.sprint_id:
                self._by_sprint[event.sprint_id] += cost
            if event.agent and event.sprint_id:
                self._by_agent_sprint[(event.agent, event.sprint_id)] += cost
            tier = resolve_tier(event.model)
            if tier is not None:
                self._tokens_by_tier[tier] += int(event.tokens_input) + int(
                    event.tokens_output
                )
            self._period_end = datetime.now(timezone.utc)
            if self._budget_usd > 0:
                prev_pct = (prev_total / self._budget_usd) * 100.0
                new_pct = (self._total / self._budget_usd) * 100.0
                for thresh in self._alarm_percent:
                    if thresh in self._fired_alarms:
                        continue
                    if new_pct >= thresh > prev_pct:
                        self._fired_alarms.add(thresh)
                        newly_fired.append(thresh)
        # Emit BudgetAlarmReached outside the lock so downstream
        # handlers that call back into the tracker don't re-enter.
        if self._bus is not None and newly_fired:
            spent_snapshot = self.current_spend_usd()
            for thresh in newly_fired:
                try:
                    self._bus.emit(
                        BudgetAlarmReached(
                            team_name=self._team,
                            percent=thresh,
                            spent_usd=spent_snapshot,
                            budget_usd=self._budget_usd,
                        )
                    )
                except Exception:  # pragma: no cover
                    # Emission failures must not crash the event handler;
                    # the bus already swallows handler exceptions, but we
                    # belt-and-brace in case ``emit`` itself fails (e.g.
                    # during shutdown).
                    pass


__all__ = ["CostTracker"]
