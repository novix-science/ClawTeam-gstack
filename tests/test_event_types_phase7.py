"""Phase 7 Wave 0 / Plan 07-01 Task 2 — 6 new concurrency/cost/rate-limit events.

Mirrors ``tests/test_event_types_phase6.py`` shape verbatim. Behaviors:

- All 6 events subclass HarnessEvent (isinstance checks).
- All 6 construct with only ``team_name`` kwarg (other fields default).
- EventBus.emit() round-trips each exact instance to the subscriber.
- All 6 are registered in ``_EVENT_TYPE_REGISTRY`` at module import so
  shell hooks can resolve them by name via ``resolve_event_type``.
- Phase 6 events stay resolvable (BC — no regression).
"""

from __future__ import annotations

from clawteam.events.bus import EventBus, resolve_event_type
from clawteam.events.types import (
    BudgetAlarmReached,
    ClaudeApiResponse,
    ConflictDetected,  # Phase 6 regression check
    DormancyTransition,
    HarnessEvent,
    MemoryBackfillComplete,  # Phase 6 regression check
    MemoryWritePersisted,  # Phase 6 regression check
    RateLimitSaturated,
    ToolCallCompleted,
    ZombieWorktreeGced,
)


# ── isinstance checks (tests 1-6) ────────────────────────────────────────


def test_tool_call_completed_is_harness_event():
    evt = ToolCallCompleted(team_name="t")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"
    assert "T" in evt.timestamp


def test_claude_api_response_is_harness_event():
    evt = ClaudeApiResponse(team_name="t")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"


def test_budget_alarm_reached_is_harness_event():
    evt = BudgetAlarmReached(team_name="t")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"


def test_rate_limit_saturated_is_harness_event():
    evt = RateLimitSaturated(team_name="t")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"


def test_zombie_worktree_gced_is_harness_event():
    evt = ZombieWorktreeGced(team_name="t")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"


def test_dormancy_transition_is_harness_event():
    evt = DormancyTransition(team_name="t")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"


# ── defaults ─────────────────────────────────────────────────────────────


def test_defaults_populated():
    tcc = ToolCallCompleted(team_name="t")
    assert tcc.agent == ""
    assert tcc.tool_name == ""
    assert tcc.sprint_id == ""
    assert tcc.tokens_input == 0
    assert tcc.tokens_output == 0
    assert tcc.model == ""
    assert tcc.cost_usd == 0.0
    assert tcc.duration_ms == 0.0
    assert tcc.model_fallback_applied is False

    car = ClaudeApiResponse(team_name="t")
    assert car.agent == ""
    assert car.model == ""
    assert car.cache_read_tokens == 0
    assert car.cache_creation_tokens == 0
    assert car.input_tokens == 0
    assert car.output_tokens == 0

    bar = BudgetAlarmReached(team_name="t")
    assert bar.percent == 0.0
    assert bar.spent_usd == 0.0
    assert bar.budget_usd == 0.0

    rls = RateLimitSaturated(team_name="t")
    assert rls.recent_429_count == 0
    assert rls.threshold == 3
    assert rls.window_seconds == 60

    zwg = ZombieWorktreeGced(team_name="t")
    assert zwg.path == ""
    assert zwg.age_days == 0
    assert zwg.freed_bytes == 0

    dt = DormancyTransition(team_name="t")
    assert dt.agent == ""
    assert dt.role == ""
    assert dt.from_state == ""
    assert dt.to_state == ""


# ── EventBus round-trip (tests 7-12) ─────────────────────────────────────


def test_emit_roundtrip_tool_call_completed():
    bus = EventBus()
    captured: list[ToolCallCompleted] = []
    bus.subscribe(ToolCallCompleted, lambda ev: captured.append(ev))
    sent = ToolCallCompleted(
        team_name="t",
        agent="engineer",
        tool_name="bash",
        sprint_id="abc12345",
        tokens_input=1000,
        tokens_output=500,
        model="claude-sonnet-4",
        cost_usd=0.015,
        duration_ms=1234.5,
        model_fallback_applied=False,
    )
    bus.emit(sent)
    assert captured == [sent]
    assert captured[0] is sent


def test_emit_roundtrip_claude_api_response():
    bus = EventBus()
    captured: list[ClaudeApiResponse] = []
    bus.subscribe(ClaudeApiResponse, lambda ev: captured.append(ev))
    sent = ClaudeApiResponse(
        team_name="t",
        agent="pm",
        model="claude-opus-4",
        cache_read_tokens=2000,
        cache_creation_tokens=300,
        input_tokens=800,
        output_tokens=400,
    )
    bus.emit(sent)
    assert captured == [sent]


def test_emit_roundtrip_budget_alarm():
    bus = EventBus()
    captured: list[BudgetAlarmReached] = []
    bus.subscribe(BudgetAlarmReached, lambda ev: captured.append(ev))
    sent = BudgetAlarmReached(
        team_name="t",
        percent=80.0,
        spent_usd=80.0,
        budget_usd=100.0,
    )
    bus.emit(sent)
    assert captured == [sent]


def test_emit_roundtrip_rate_limit_saturated():
    bus = EventBus()
    captured: list[RateLimitSaturated] = []
    bus.subscribe(RateLimitSaturated, lambda ev: captured.append(ev))
    sent = RateLimitSaturated(
        team_name="t",
        recent_429_count=5,
        threshold=3,
        window_seconds=60,
    )
    bus.emit(sent)
    assert captured == [sent]


def test_emit_roundtrip_zombie_worktree_gced():
    bus = EventBus()
    captured: list[ZombieWorktreeGced] = []
    bus.subscribe(ZombieWorktreeGced, lambda ev: captured.append(ev))
    sent = ZombieWorktreeGced(
        team_name="t",
        path="/tmp/worktrees/dead",
        age_days=14,
        freed_bytes=1_048_576,
    )
    bus.emit(sent)
    assert captured == [sent]


def test_emit_roundtrip_dormancy_transition():
    bus = EventBus()
    captured: list[DormancyTransition] = []
    bus.subscribe(DormancyTransition, lambda ev: captured.append(ev))
    sent = DormancyTransition(
        team_name="t",
        agent="designer",
        role="designer",
        from_state="dormant",
        to_state="active",
    )
    bus.emit(sent)
    assert captured == [sent]


# ── Registry visibility (tests 13-14) ────────────────────────────────────


def test_all_six_registered():
    """All 6 new event classes resolvable by name after module import."""
    assert resolve_event_type("ToolCallCompleted") is ToolCallCompleted
    assert resolve_event_type("ClaudeApiResponse") is ClaudeApiResponse
    assert resolve_event_type("BudgetAlarmReached") is BudgetAlarmReached
    assert resolve_event_type("RateLimitSaturated") is RateLimitSaturated
    assert resolve_event_type("ZombieWorktreeGced") is ZombieWorktreeGced
    assert resolve_event_type("DormancyTransition") is DormancyTransition


def test_phase6_events_still_registered():
    """Regression: Phase 6 events still resolvable after Phase 7 additions."""
    assert resolve_event_type("MemoryWritePersisted") is MemoryWritePersisted
    assert resolve_event_type("ConflictDetected") is ConflictDetected
    assert resolve_event_type("MemoryBackfillComplete") is MemoryBackfillComplete
