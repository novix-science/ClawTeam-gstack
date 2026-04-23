"""Phase 7 Plan 07-02 Task 2: SprintConductor concurrency caps + rate-limit consult.

RED phase: start_sprint_async, active_agents(), dispatch_turn, _sprint_sem,
_rate_limit_monitor, conductor_config kwarg do not yet exist. GREEN phase
wires the three asyncio.Semaphore caps (sprint/per-agent/active-agent) and
the RateLimitMonitor consult in conductor.__init__ + start_sprint_async.

Test matrix (D-01/02/03 + QUALITY-04 + D-13 consult):
- BC: sync start_sprint unchanged with no config passed.
- Async happy path: semaphore acquired, queue_status empty.
- Over-cap: sprint_sem=1, second acquire times out → queue_status='queued_capacity'.
- Rate-limit saturated: is_saturated()=True at entry → queue_status='rate_limit_saturated'.
- active_agents() empty initially; populated mid-dispatch; emptied on exit.
- Per-agent semaphore serializes concurrent dispatch_turn of the same role.
- Active-agent semaphore caps total concurrent dispatches.
- DormancyTransition emitted on dispatch_turn enter/exit.
"""
from __future__ import annotations

import asyncio

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import DormancyTransition
# RateLimitMonitor import removed post-v1.0 UAT 2026-04-22 — no production
# 429 detection path existed under the tmux + claude-CLI architecture.
from clawteam.sprint.conductor import SprintConductor
from clawteam.templates import ConductorConfig


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    """Hermetic data dir and HOME for every test — mirrors tests/test_sprint_conductor.py."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _make_conductor(**overrides) -> SprintConductor:
    cfg_kwargs = dict(
        max_concurrent_sprints=2,
        max_tasks_per_agent=1,
        max_active_agents=2,
        acquire_timeout_seconds=0.1,
    )
    cfg_kwargs.update(overrides)
    return SprintConductor(
        team_name="t1",
        conductor_config=ConductorConfig(**cfg_kwargs),
        bus=EventBus(),
    )


def test_start_sprint_sync_path_unchanged():
    """BC: legacy callers can still instantiate without conductor_config."""
    c = SprintConductor(team_name="t1", bus=EventBus())
    s = c.start_sprint(goal="g")
    assert s.goal == "g"
    assert s.queue_status == ""


def test_start_sprint_async_happy_path():
    c = _make_conductor()

    async def run():
        return await c.start_sprint_async(goal="g")

    state = asyncio.run(run())
    assert state.queue_status == ""
    assert state.goal == "g"


def test_over_cap_sprint_queued():
    c = _make_conductor(max_concurrent_sprints=1, acquire_timeout_seconds=0.05)

    async def run():
        s1 = await c.start_sprint_async(goal="g1")
        # 2nd acquire cannot progress (sem=1 held by s1) → times out → queued.
        s2 = await c.start_sprint_async(goal="g2")
        return s1, s2

    s1, s2 = asyncio.run(run())
    assert s1.queue_status == ""
    assert s2.queue_status == "queued_capacity"


# test_rate_limit_saturation_queues removed post-v1.0 UAT 2026-04-22 —
# RateLimitMonitor had no production emitter and was deleted.


def test_active_agents_empty_initially():
    c = _make_conductor()
    assert c.active_agents() == []


def test_per_agent_semaphore_serializes():
    """Per-agent sem=1 — concurrent dispatch_turn('pm', ...) cannot overlap."""
    c = _make_conductor(max_tasks_per_agent=1, max_active_agents=4)
    events: list[str] = []

    async def work(label: str) -> None:
        async with c.dispatch_turn("pm", f"pm-{label}"):
            events.append(f"enter-{label}")
            await asyncio.sleep(0.02)
            events.append(f"exit-{label}")

    async def run():
        await asyncio.gather(work("a"), work("b"))

    asyncio.run(run())
    # Whichever runs first, its 'exit' must come before the other's 'enter'.
    assert events.index("exit-a") < events.index("enter-b") or \
           events.index("exit-b") < events.index("enter-a")


def test_active_agent_cap():
    """max_active_agents=2 — three concurrent dispatches never exceed 2 simultaneous."""
    c = _make_conductor(max_active_agents=2, max_tasks_per_agent=1)
    observed_peaks: list[int] = []

    async def work(role: str) -> None:
        async with c.dispatch_turn(role, role):
            observed_peaks.append(len(c.active_agents()))
            await asyncio.sleep(0.02)

    async def run():
        await asyncio.gather(work("pm"), work("ceo"), work("engineer"))

    asyncio.run(run())
    assert max(observed_peaks) <= 2
    # Post-exit: active set emptied.
    assert c.active_agents() == []


def test_dormancy_events_emitted():
    c = _make_conductor()
    received: list[DormancyTransition] = []
    c.bus.subscribe(DormancyTransition, lambda ev: received.append(ev))

    async def run():
        async with c.dispatch_turn("pm", "pm"):
            pass

    asyncio.run(run())
    assert len(received) == 2
    assert received[0].from_state == "dormant" and received[0].to_state == "active"
    assert received[1].from_state == "active" and received[1].to_state == "dormant"
    assert received[0].agent == "pm" and received[0].role == "pm"
