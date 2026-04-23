"""Phase 7 Plan 07-09 Task 1: 10-sprint concurrent load test (D-14).

Locks CORE-06 floor: Phase 7 SprintConductor must survive 10 concurrent
sprints under asyncio.gather without:

- Corrupting state.json (D-14a).
- Exceeding max_active_agents cap (D-14c).
- Allowing same-role re-entry across sprints (D-02 per-agent semaphore).
- Duplicating sprint_ids (uuid4[:8] collision under concurrent writes).

Every test runs in <5 minutes (D-14 realistic bound; the 5-minute plan
ceiling is the outer safety net, not a per-test target).

Uses the :attr:`SprintConductor.start_sprint_async` entry point landed in
Plan 07-02 + the semaphore caps from ``ConductorConfig``.
"""
from __future__ import annotations

import asyncio

import pytest

from clawteam.sprint.conductor import SprintConductor
from clawteam.sprint.state import load_sprint_state
from clawteam.templates import ConductorConfig


@pytest.fixture
def isolated_conductor(tmp_path, monkeypatch):
    """Hermetic CLAWTEAM_DATA_DIR + factory for constructing conductors."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))

    def _factory(**overrides):
        cfg_kwargs = dict(
            max_concurrent_sprints=10,
            max_tasks_per_agent=1,
            max_active_agents=6,
            acquire_timeout_seconds=0.1,
        )
        cfg_kwargs.update(overrides)
        return SprintConductor(
            team_name="loadtest",
            conductor_config=ConductorConfig(**cfg_kwargs),
        )

    return _factory, tmp_path


def test_ten_concurrent_sprints(isolated_conductor):
    """D-14: 10 sprints via asyncio.gather all succeed with distinct ids."""
    factory, _ = isolated_conductor
    c = factory(max_concurrent_sprints=10, acquire_timeout_seconds=1.0)

    async def spawn_all():
        return await asyncio.gather(
            *[c.start_sprint_async(goal=f"goal-{i}") for i in range(10)]
        )

    sprints = asyncio.run(spawn_all())
    assert len(sprints) == 10
    # All 10 hold a slot — no queued_capacity.
    assert all(s.queue_status == "" for s in sprints)
    # sprint_id uniqueness under concurrent creation.
    assert len({s.sprint_id for s in sprints}) == 10


def test_eleventh_sprint_queued_capacity(isolated_conductor):
    """D-14: 11th concurrent sprint over max=10 cap → queue_status='queued_capacity'."""
    factory, _ = isolated_conductor
    c = factory(max_concurrent_sprints=10, acquire_timeout_seconds=0.05)

    async def spawn_all():
        return await asyncio.gather(
            *[c.start_sprint_async(goal=f"goal-{i}") for i in range(11)]
        )

    sprints = asyncio.run(spawn_all())
    queued = [s for s in sprints if s.queue_status == "queued_capacity"]
    active = [s for s in sprints if s.queue_status == ""]
    # 10 sprints acquire the semaphore; 11th times out.
    assert len(queued) >= 1
    assert len(active) == 10
    # Persisted state.json reflects the queued status (crash-recovery invariant).
    for s in queued:
        loaded = load_sprint_state("loadtest", s.sprint_id)
        assert loaded.queue_status == "queued_capacity"


def test_active_agent_cap_under_load(isolated_conductor):
    """D-14: active-agent count never exceeds max_active_agents."""
    factory, _ = isolated_conductor
    c = factory(max_active_agents=3, max_tasks_per_agent=1)
    observed_max = [0]

    async def work(role):
        async with c.dispatch_turn(role, role):
            observed_max[0] = max(observed_max[0], len(c.active_agents()))
            await asyncio.sleep(0.01)

    async def run():
        await asyncio.gather(*[work(f"r{i}") for i in range(6)])

    asyncio.run(run())
    assert observed_max[0] <= 3
    # Post-run: active set is empty.
    assert c.active_agents() == []


def test_per_agent_semaphore_blocks_siblings(isolated_conductor):
    """D-02: per-agent semaphore (=1) prevents same role running concurrently."""
    factory, _ = isolated_conductor
    c = factory(max_tasks_per_agent=1, max_active_agents=10)
    timeline: list[str] = []

    async def work(label):
        async with c.dispatch_turn("pm", f"pm-{label}"):
            timeline.append(f"enter-{label}")
            await asyncio.sleep(0.02)
            timeline.append(f"exit-{label}")

    async def run():
        await asyncio.gather(*(work(letter) for letter in "abcde"))

    asyncio.run(run())
    # For each letter, its exit must immediately follow its enter — no interleave.
    for letter in "abcde":
        enter_idx = timeline.index(f"enter-{letter}")
        exit_idx = timeline.index(f"exit-{letter}")
        assert exit_idx == enter_idx + 1, f"{letter} got interleaved: {timeline}"


# test_rate_limit_saturation_queues_sprints removed post-v1.0 UAT 2026-04-22
# — RateLimitMonitor had no production 429 emitter under the tmux +
# claude-CLI architecture and the entire rate_limit package was deleted.


def test_pause_resume_across_queue_cycle(isolated_conductor):
    """Pause a queued sprint; resume flips it back to 'running' (CORE-07)."""
    factory, _ = isolated_conductor
    c = factory()

    async def run():
        return await c.start_sprint_async(goal="g1")

    s = asyncio.run(run())
    c.pause(s.sprint_id)
    loaded = load_sprint_state("loadtest", s.sprint_id)
    assert loaded.status == "paused"
    c.resume(s.sprint_id)
    loaded = load_sprint_state("loadtest", s.sprint_id)
    assert loaded.status == "running"


def test_no_data_races_on_state_saves(isolated_conductor):
    """D-14b: 10 concurrent state.json writes produce 10 distinct, loadable sprints."""
    factory, _ = isolated_conductor
    c = factory(max_concurrent_sprints=10, acquire_timeout_seconds=1.0)

    async def spawn_all():
        return await asyncio.gather(
            *[c.start_sprint_async(goal=f"g{i}") for i in range(10)]
        )

    sprints = asyncio.run(spawn_all())
    # All state.json files load cleanly — no corruption from concurrent writes.
    for s in sprints:
        loaded = load_sprint_state("loadtest", s.sprint_id)
        assert loaded.sprint_id == s.sprint_id
        assert loaded.goal.startswith("g")
        assert loaded.team == "loadtest"
    # list_sprints discovers all 10 from the file-system side.
    listed = c.list_sprints()
    assert len(listed) == 10
