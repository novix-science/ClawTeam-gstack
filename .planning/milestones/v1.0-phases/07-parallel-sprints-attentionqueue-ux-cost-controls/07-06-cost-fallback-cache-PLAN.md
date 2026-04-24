---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 06
type: execute
wave: 4
depends_on: [07-05]
files_modified:
  - clawteam/cost/fallback.py
  - clawteam/cost/cache_tracker.py
  - clawteam/cost/__init__.py
  - tests/cost/test_fallback.py
  - tests/cost/test_cache_tracker.py
autonomous: true
requirements:
  - QUALITY-12
tags:
  - model-fallback-ladder
  - cache-hit-rate
  - event-subscriber

must_haves:
  truths:
    - "apply_fallback(model_pref, spend_percent, fallback_at_percent) is a pure function returning (effective_model, fallback_applied)"
    - "Fallback ladder: opus→sonnet, sonnet→haiku, haiku→haiku (D-11)"
    - "When spend_percent < fallback_at_percent, return (model_pref, False) unchanged"
    - "When spend_percent >= fallback_at_percent, return (downgraded_model, True)"
    - "CacheTracker subscribes to ClaudeApiResponse events; computes cache_hit_rate = cache_read / (cache_read + cache_creation) per team"
    - "cache_hit_rate returns 0.0 when no events observed (divide-by-zero safe)"
  artifacts:
    - path: clawteam/cost/fallback.py
      provides: "apply_fallback + FALLBACK_LADDER"
      contains: "def apply_fallback|FALLBACK_LADDER"
    - path: clawteam/cost/cache_tracker.py
      provides: "CacheTracker event subscriber"
      contains: "class CacheTracker"
  key_links:
    - from: clawteam/cost/fallback.py
      to: clawteam/cost/pricing.py
      via: "Fallback ladder uses the same tier names (opus/sonnet/haiku) as pricing.py"
      pattern: "opus|sonnet|haiku"
    - from: clawteam/cost/cache_tracker.py
      to: clawteam/events/types.py
      via: "CacheTracker subscribes to ClaudeApiResponse"
      pattern: "ClaudeApiResponse"
---

<objective>
Wave 4 part 2 — model fallback ladder policy (D-11) + cache hit rate tracker (D-12). Both small modules; both pure event subscribers / pure functions.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-05-cost-tracker-PLAN.md

<interfaces>
From clawteam/events/types.py (Plan 07-01):
```python
@dataclass class ClaudeApiResponse(HarnessEvent):
    agent: str = ""
    model: str = ""
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: apply_fallback ladder (D-11)</name>
  <files>
    clawteam/cost/fallback.py,
    tests/cost/test_fallback.py
  </files>
  <read_first>
    clawteam/cost/pricing.py (Plan 07-05 for tier names)
  </read_first>
  <behavior>
    - Test 1: `test_below_threshold_returns_original` — apply_fallback("claude-opus", 70.0, 80.0) == ("claude-opus", False).
    - Test 2: `test_at_threshold_applies_fallback` — apply_fallback("claude-opus", 80.0, 80.0) == ("claude-sonnet", True).
    - Test 3: `test_sonnet_downgrades_to_haiku` — apply_fallback("claude-sonnet", 90.0, 80.0) == ("claude-haiku", True).
    - Test 4: `test_haiku_stays_haiku` — apply_fallback("claude-haiku", 90.0, 80.0) == ("claude-haiku", True). (Fallback applied=True signifies the policy engaged even though no model change.)
    - Test 5: `test_resolves_aliases` — apply_fallback("claude-3-opus-20240229", 90.0, 80.0) returns ("claude-sonnet", True). (Alias → opus → sonnet.)
    - Test 6: `test_unknown_model_unchanged` — apply_fallback("gpt-4", 90.0, 80.0) == ("gpt-4", False). (Unknown tier — preserve input; no fallback applied.)
    - Test 7: `test_fallback_at_percent_100` — with threshold 100, spend=99 → no fallback; spend=100 → fallback.
    - Test 8: `test_zero_fallback_threshold_always_fallbacks` — apply_fallback("claude-opus", 0.0, 0.0) triggers fallback.
  </behavior>
  <action>
**1. `clawteam/cost/fallback.py` (NEW, ~70 LOC):**

```python
"""Model fallback ladder (D-11).

Pure function — caller passes current spend percent + configured fallback
threshold. Returns (effective_model, fallback_applied). Callers stamp
`model_fallback_applied: true` on agent envelopes when the second
element is True so reviewers see "this used sonnet not opus because budget".
"""
from __future__ import annotations

from typing import Optional

from clawteam.cost.pricing import ModelTier, resolve_tier

# Tier-to-tier downgrade map. Haiku terminates (cheapest available).
FALLBACK_LADDER: dict[ModelTier, ModelTier] = {
    "opus": "sonnet",
    "sonnet": "haiku",
    "haiku": "haiku",
}

# Canonical model names to return after downgrade. Callers that need a
# more specific model string (e.g. claude-sonnet-20250101) should map in
# a wrapper.
TIER_TO_CANONICAL: dict[ModelTier, str] = {
    "opus": "claude-opus",
    "sonnet": "claude-sonnet",
    "haiku": "claude-haiku",
}


def apply_fallback(
    model_pref: str,
    spend_percent: float,
    fallback_at_percent: float = 80.0,
) -> tuple[str, bool]:
    """Return (effective_model, fallback_applied).

    When spend_percent < fallback_at_percent: returns (model_pref, False).
    When spend_percent >= fallback_at_percent: returns downgraded model
    per FALLBACK_LADDER + True. Unknown model strings (no matching tier)
    are returned unchanged with fallback_applied=False.
    """
    if spend_percent < fallback_at_percent:
        return model_pref, False
    tier = resolve_tier(model_pref)
    if tier is None:
        return model_pref, False
    downgraded_tier = FALLBACK_LADDER[tier]
    return TIER_TO_CANONICAL[downgraded_tier], True


__all__ = ["apply_fallback", "FALLBACK_LADDER", "TIER_TO_CANONICAL"]
```

**2. `tests/cost/test_fallback.py` (~100 LOC):**

```python
import pytest
from clawteam.cost.fallback import apply_fallback, FALLBACK_LADDER


def test_below_threshold_unchanged():
    assert apply_fallback("claude-opus", 70.0, 80.0) == ("claude-opus", False)


def test_at_threshold_applies():
    assert apply_fallback("claude-opus", 80.0, 80.0) == ("claude-sonnet", True)


def test_sonnet_to_haiku():
    assert apply_fallback("claude-sonnet", 90.0, 80.0) == ("claude-haiku", True)


def test_haiku_stays_haiku():
    assert apply_fallback("claude-haiku", 90.0, 80.0) == ("claude-haiku", True)


def test_resolves_aliases():
    # "claude-3-opus-20240229" resolves to opus tier → sonnet downgrade.
    result, applied = apply_fallback("claude-3-opus-20240229", 90.0, 80.0)
    assert result == "claude-sonnet"
    assert applied is True


def test_unknown_model_unchanged():
    assert apply_fallback("gpt-4", 90.0, 80.0) == ("gpt-4", False)


def test_empty_model():
    # Unknown/empty model — no tier → unchanged.
    assert apply_fallback("", 90.0, 80.0) == ("", False)


def test_zero_threshold_always_fallback():
    # At 0% budget → any spend triggers fallback.
    assert apply_fallback("claude-opus", 0.0, 0.0) == ("claude-sonnet", True)


def test_ladder_map_shape():
    assert FALLBACK_LADDER["opus"] == "sonnet"
    assert FALLBACK_LADDER["sonnet"] == "haiku"
    assert FALLBACK_LADDER["haiku"] == "haiku"
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/cost/test_fallback.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def apply_fallback" clawteam/cost/fallback.py` succeeds.
    - `grep -q "FALLBACK_LADDER" clawteam/cost/fallback.py` succeeds.
    - `pytest tests/cost/test_fallback.py -q` reports 9 passed.
  </acceptance_criteria>
  <done>Fallback ladder proven; callers can wire it at NativeCliAdapter call-sites (out-of-scope — documented for Phase 5.1).</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: CacheTracker (D-12)</name>
  <files>
    clawteam/cost/cache_tracker.py,
    clawteam/cost/__init__.py,
    tests/cost/test_cache_tracker.py
  </files>
  <read_first>
    clawteam/events/types.py (ClaudeApiResponse from Plan 07-01),
    clawteam/cost/tracker.py (pattern precedent from Plan 07-05)
  </read_first>
  <behavior>
    - Test 1: `test_fresh_tracker_zero_rate` — cache_hit_rate() == 0.0.
    - Test 2: `test_only_creation_events_zero_rate` — emit 3 events with cache_creation=1000, cache_read=0 → 0.0 rate.
    - Test 3: `test_only_read_events_one_rate` — emit events with cache_read=1000, cache_creation=0 → rate == 1.0.
    - Test 4: `test_mixed_rate_50` — one creation=1000, one read=1000 → rate == 0.5.
    - Test 5: `test_other_team_ignored` — events for different team don't affect this team's rate.
    - Test 6: `test_healthy_threshold_50` — `is_healthy()` returns True when rate > 0.5, False otherwise.
    - Test 7: `test_total_tokens_accessor` — total_cache_read + total_cache_creation exposed.
  </behavior>
  <action>
**1. `clawteam/cost/cache_tracker.py` (NEW, ~90 LOC):**

```python
"""CacheTracker — cache-hit-rate accumulator over ClaudeApiResponse events (D-12).

cache_hit_rate = cache_read_tokens / (cache_read_tokens + cache_creation_tokens)
per team. >50% is considered healthy per CONTEXT.

Listens on EventBus for ClaudeApiResponse events. Emits nothing itself —
dashboard consumers (Plan 07-07) pull via cache_hit_rate() at render time.
"""
from __future__ import annotations

import threading
from typing import Optional

from clawteam.events.bus import EventBus
from clawteam.events.types import ClaudeApiResponse

HEALTHY_THRESHOLD: float = 0.5


class CacheTracker:
    """Per-team cache-hit-rate aggregator."""

    def __init__(
        self,
        team: str,
        *,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._team = team
        self._lock = threading.RLock()
        self._total_read: int = 0
        self._total_creation: int = 0
        if bus is not None:
            bus.subscribe(ClaudeApiResponse, self._on_response)

    def cache_hit_rate(self) -> float:
        with self._lock:
            denom = self._total_read + self._total_creation
            if denom <= 0:
                return 0.0
            return self._total_read / denom

    def is_healthy(self) -> bool:
        """Return True when cache_hit_rate > HEALTHY_THRESHOLD (0.5)."""
        return self.cache_hit_rate() > HEALTHY_THRESHOLD

    def total_cache_read(self) -> int:
        with self._lock:
            return self._total_read

    def total_cache_creation(self) -> int:
        with self._lock:
            return self._total_creation

    def _on_response(self, event: ClaudeApiResponse) -> None:
        if event.team_name != self._team:
            return
        with self._lock:
            self._total_read += int(event.cache_read_tokens)
            self._total_creation += int(event.cache_creation_tokens)


__all__ = ["CacheTracker", "HEALTHY_THRESHOLD"]
```

**2. EDIT `clawteam/cost/__init__.py` — add exports:**

```python
from clawteam.cost.fallback import apply_fallback, FALLBACK_LADDER
from clawteam.cost.cache_tracker import CacheTracker, HEALTHY_THRESHOLD

__all__ = [
    "MODEL_PRICING", "calculate_cost_usd", "resolve_tier",
    "CostRollup", "CostTracker",
    "apply_fallback", "FALLBACK_LADDER",
    "CacheTracker", "HEALTHY_THRESHOLD",
]
```

**3. `tests/cost/test_cache_tracker.py` (~110 LOC):**

```python
import pytest
from clawteam.events.bus import EventBus
from clawteam.events.types import ClaudeApiResponse
from clawteam.cost.cache_tracker import CacheTracker, HEALTHY_THRESHOLD


def test_fresh_zero_rate():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    assert t.cache_hit_rate() == 0.0
    assert t.is_healthy() is False


def test_only_creation_zero_rate():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    for _ in range(3):
        bus.emit(ClaudeApiResponse(team_name="t", cache_creation_tokens=1000, cache_read_tokens=0))
    assert t.cache_hit_rate() == 0.0


def test_only_read_full_rate():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(ClaudeApiResponse(team_name="t", cache_read_tokens=1000, cache_creation_tokens=0))
    assert t.cache_hit_rate() == 1.0


def test_mixed_rate_50_percent():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(ClaudeApiResponse(team_name="t", cache_creation_tokens=1000))
    bus.emit(ClaudeApiResponse(team_name="t", cache_read_tokens=1000))
    assert t.cache_hit_rate() == 0.5


def test_other_team_ignored():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(ClaudeApiResponse(team_name="OTHER", cache_read_tokens=999))
    assert t.cache_hit_rate() == 0.0


def test_healthy_threshold():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(ClaudeApiResponse(team_name="t", cache_read_tokens=600, cache_creation_tokens=400))
    # Rate = 0.6 > 0.5 → healthy.
    assert t.is_healthy() is True

    bus2 = EventBus()
    t2 = CacheTracker(team="t", bus=bus2)
    bus2.emit(ClaudeApiResponse(team_name="t", cache_read_tokens=400, cache_creation_tokens=600))
    # Rate = 0.4 → unhealthy.
    assert t2.is_healthy() is False


def test_totals_accessors():
    bus = EventBus()
    t = CacheTracker(team="t", bus=bus)
    bus.emit(ClaudeApiResponse(team_name="t", cache_read_tokens=500, cache_creation_tokens=250))
    assert t.total_cache_read() == 500
    assert t.total_cache_creation() == 250


def test_healthy_threshold_constant():
    assert HEALTHY_THRESHOLD == 0.5
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/cost/test_cache_tracker.py tests/cost/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "class CacheTracker" clawteam/cost/cache_tracker.py` succeeds.
    - `pytest tests/cost/test_cache_tracker.py -q` reports 8 passed.
    - Full cost dir: `pytest tests/cost/ -q` reports all green.
  </acceptance_criteria>
  <done>Cache hit rate + fallback policy live; Plan 07-07 dashboard consumes both.</done>
</task>

</tasks>

<verification>
1. `pytest tests/cost/ -q` — all green.
2. `python -c "from clawteam.cost import apply_fallback, CacheTracker; print(apply_fallback('claude-opus', 90.0, 80.0))"` — prints `('claude-sonnet', True)`.
</verification>

<success_criteria>
- Tasks 1-2 acceptance met.
- Fallback ladder proven for all tier transitions.
- Cache hit rate math proven at 0%, 50%, 100%.
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-06-SUMMARY.md`.
</output>
