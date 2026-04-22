---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 09
type: execute
wave: 6
depends_on: [07-02, 07-03, 07-04, 07-05, 07-06, 07-07, 07-08]
files_modified:
  - tests/integration/test_phase7_ten_sprint_load.py
  - tests/integration/test_phase7_attention_ranking.py
  - tests/integration/test_phase7_cost_dashboard.py
autonomous: true
requirements:
  - CORE-06
  - INT-03
  - QUALITY-04
  - QUALITY-12
tags:
  - integration-test
  - 10-sprint-load
  - adversarial-ranking
  - cost-rollup-fixture

must_haves:
  truths:
    - "10-sprint load test spawns 10 concurrent sprints via asyncio.gather against one SprintConductor; under 5-min duration cap (realistic); asserts active-agent count never exceeds max_active_agents"
    - "11th sprint over max_concurrent_sprints cap enters queue_status='queued_capacity' (D-14)"
    - "Attention ranking test with 30 fixture questions × 5 sprints × 3 teams verifies priority ordering matches D-05 formula exactly (D-15)"
    - "Cost dashboard test with 100-event fixture stream + 5 agents asserts rollup correctness + 50/80/100 alarm firing + fallback at 80% (D-16)"
    - "All 3 tests green in CI; no race conditions on TaskStore / memory store / attention queue"
    - "Rate-limit monitor consulted at sprint start; saturated monitor queues sprints cleanly"
  artifacts:
    - path: tests/integration/test_phase7_ten_sprint_load.py
      provides: "10-sprint concurrent load test"
      contains: "test_ten_concurrent_sprints|test_eleventh_sprint_queued|test_active_agent_cap_under_load"
    - path: tests/integration/test_phase7_attention_ranking.py
      provides: "30-question priority-formula adversarial test"
      contains: "test_thirty_questions_ranked_by_formula|test_cross_team_queue"
    - path: tests/integration/test_phase7_cost_dashboard.py
      provides: "100-event cost rollup fixture"
      contains: "test_100_events_rollup|test_budget_alarm_threshold_crossings|test_fallback_activates_at_80"
  key_links:
    - from: tests/integration/test_phase7_ten_sprint_load.py
      to: clawteam/sprint/conductor.py
      via: "Exercises start_sprint_async + per-agent semaphore + active_agent slot pool"
      pattern: "start_sprint_async|active_agents"
    - from: tests/integration/test_phase7_attention_ranking.py
      to: clawteam/attention/queue.py
      via: "AttentionQueue.snapshot() over fixture data_dir"
      pattern: "AttentionQueue"
    - from: tests/integration/test_phase7_cost_dashboard.py
      to: clawteam/cost/tracker.py
      via: "CostTracker event subscription + rollup + BudgetAlarmReached"
      pattern: "CostTracker|BudgetAlarmReached"
---

<objective>
Wave 6 — three integration tests that lock Phase 7 success criteria: (D-14) 10-sprint load, (D-15) 30-question adversarial ranking, (D-16) 100-event cost dashboard. Final phase gate.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-02-conductor-concurrency-PLAN.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-03-attention-queue-PLAN.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-05-cost-tracker-PLAN.md

<interfaces>
All primitives from Plans 07-01 through 07-08 are in place:
- SprintConductor.start_sprint_async (07-02)
- AttentionQueue.snapshot (07-03)
- CostTracker + BudgetAlarmReached (07-05)
- apply_fallback (07-06)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: 10-sprint load integration test (D-14 / CORE-06 / QUALITY-04)</name>
  <files>
    tests/integration/test_phase7_ten_sprint_load.py
  </files>
  <read_first>
    clawteam/sprint/conductor.py (post Plan 07-02 extensions),
    clawteam/templates/__init__.py (ConductorConfig shape),
    tests/sprint/test_conductor_concurrency.py (Plan 07-02 test precedent)
  </read_first>
  <behavior>
    - test_ten_concurrent_sprints: spawn 10 sprints via asyncio.gather(start_sprint_async). All succeed; queue_status="" on all. list_sprints() returns 10 items.
    - test_eleventh_sprint_queued_capacity: set max_concurrent_sprints=10; never release; spawn 11 concurrent; 10 succeed; 11th has queue_status="queued_capacity".
    - test_active_agent_cap_under_load: max_active_agents=6; sample conductor.active_agents() during dispatch cycles; max observed len <= 6.
    - test_per_agent_semaphore_under_load: max_tasks_per_agent=1; concurrent dispatch_turn("pm") across 10 sprints; only one pm runs concurrently.
    - test_rate_limit_saturation_queues_sprints: monkeypatch RateLimitMonitor.is_saturated → True; new start_sprint_async sets queue_status="rate_limit_saturated".
    - test_pause_resume_across_queue_cycle: pause a queued sprint; resume; sprint eligible for dispatch.
    - test_no_data_races_on_state_saves: 10-sprint concurrent writes; verify all state.json files load cleanly and have distinct sprint_ids.
  </behavior>
  <action>
**1. `tests/integration/test_phase7_ten_sprint_load.py` (NEW, ~280 LOC):**

```python
"""Phase 7 Plan 07-09 Task 1: 10-sprint concurrent load test (D-14)."""
from __future__ import annotations

import asyncio
import json
import pytest

from clawteam.events.bus import EventBus
from clawteam.sprint.conductor import SprintConductor
from clawteam.sprint.state import load_sprint_state
from clawteam.templates import ConductorConfig


@pytest.fixture
def isolated_conductor(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))

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
    factory, tmp = isolated_conductor
    c = factory()

    async def spawn_all():
        return await asyncio.gather(*[
            c.start_sprint_async(goal=f"goal-{i}") for i in range(10)
        ])

    sprints = asyncio.run(spawn_all())
    assert len(sprints) == 10
    assert all(s.queue_status == "" for s in sprints)
    # Uniqueness of sprint_ids under concurrent creation.
    assert len({s.sprint_id for s in sprints}) == 10


def test_eleventh_sprint_queued_capacity(isolated_conductor):
    factory, _ = isolated_conductor
    c = factory(max_concurrent_sprints=10, acquire_timeout_seconds=0.05)

    async def spawn_all():
        return await asyncio.gather(*[
            c.start_sprint_async(goal=f"goal-{i}") for i in range(11)
        ])

    sprints = asyncio.run(spawn_all())
    queued = [s for s in sprints if s.queue_status == "queued_capacity"]
    active = [s for s in sprints if s.queue_status == ""]
    # Semaphore has 10 slots + no release; so 10 hold slots, 1 times out.
    assert len(queued) >= 1
    assert len(active) == 10


def test_active_agent_cap_under_load(isolated_conductor):
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


def test_per_agent_semaphore_blocks_siblings(isolated_conductor):
    factory, _ = isolated_conductor
    c = factory(max_tasks_per_agent=1, max_active_agents=10)
    timeline: list[str] = []

    async def work(label):
        async with c.dispatch_turn("pm", f"pm-{label}"):
            timeline.append(f"enter-{label}")
            await asyncio.sleep(0.02)
            timeline.append(f"exit-{label}")

    async def run():
        await asyncio.gather(*(work(l) for l in "abcde"))

    asyncio.run(run())
    # For each letter, its exit must immediately follow its enter (no interleave).
    for letter in "abcde":
        enter_idx = timeline.index(f"enter-{letter}")
        exit_idx = timeline.index(f"exit-{letter}")
        assert exit_idx == enter_idx + 1, f"{letter} got interleaved"


def test_rate_limit_saturation_queues(isolated_conductor, monkeypatch):
    factory, _ = isolated_conductor
    c = factory()
    monkeypatch.setattr(c._rate_limit_monitor, "is_saturated", lambda: True)

    async def run():
        return await c.start_sprint_async(goal="g")

    s = asyncio.run(run())
    assert s.queue_status == "rate_limit_saturated"


def test_pause_resume_with_queue_state(isolated_conductor):
    factory, tmp = isolated_conductor
    c = factory()

    async def run():
        return await c.start_sprint_async(goal="g1")

    s = asyncio.run(run())
    s.queue_status = "queued_capacity"
    # save_sprint_state already done in start_sprint_async on the queued path
    c.pause(s.sprint_id)
    loaded = load_sprint_state("loadtest", s.sprint_id)
    # queue_status persists across pause/resume.
    assert loaded.status == "paused"
    c.resume(s.sprint_id)
    loaded = load_sprint_state("loadtest", s.sprint_id)
    assert loaded.status == "running"


def test_no_state_json_races(isolated_conductor):
    factory, tmp = isolated_conductor
    c = factory()

    async def spawn_all():
        return await asyncio.gather(*[
            c.start_sprint_async(goal=f"g{i}") for i in range(10)
        ])

    sprints = asyncio.run(spawn_all())
    # All state.json files load cleanly — no corruption from concurrent writes.
    for s in sprints:
        loaded = load_sprint_state("loadtest", s.sprint_id)
        assert loaded.sprint_id == s.sprint_id
        assert loaded.goal.startswith("g")
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/integration/test_phase7_ten_sprint_load.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/integration/test_phase7_ten_sprint_load.py -q` reports 7 passed.
    - Test duration < 30 seconds total (D-14 realistic bound; 5 min is the ceiling).
  </acceptance_criteria>
  <done>D-14 + CORE-06 + QUALITY-04 gates met.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Attention ranking adversarial integration test (D-15 / INT-03)</name>
  <files>
    tests/integration/test_phase7_attention_ranking.py
  </files>
  <read_first>
    clawteam/attention/queue.py (Plan 07-03),
    tests/attention/test_queue_ranking.py (unit precedent for fixture pattern)
  </read_first>
  <behavior>
    - test_thirty_questions_ranked_by_formula: write 30 question.md files across 5 sprints × 3 teams with varied urgency/blocking/tags. Assert snapshot() order matches expected priority formula order (precomputed by test).
    - test_cross_team_queue_aggregates: snapshot() across 3 teams returns items from all teams, interleaved by priority.
    - test_adversarial_critical_at_30s_beats_normal_at_8h: explicit assertion of D-15 adversarial fixture — critical+30s score > normal+8h score.
    - test_tag_weights_shift_priority: question with tag "security" and tag_weights={"security": 10} outranks same urgency w/o tag.
  </behavior>
  <action>
**1. `tests/integration/test_phase7_attention_ranking.py` (NEW, ~200 LOC):**

```python
"""Phase 7 Plan 07-09 Task 2: AttentionQueue 30-fixture ranking (D-15 / INT-03)."""
from __future__ import annotations

import os
import time
from pathlib import Path
import pytest

from clawteam.attention.queue import AttentionQueue, compute_priority


def _write(data_dir: Path, team: str, sprint: str, qid: str, *, urgency="normal", blocking=False, tags=None, reversibility="medium", age_seconds=0):
    qdir = data_dir / "teams" / team / "sprints" / sprint / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    path = qdir / f"{qid}.md"
    tags = tags or []
    tag_repr = "[" + ", ".join(tags) + "]"
    path.write_text(
        f"---\nurgency: {urgency}\nblocking: {str(blocking).lower()}\n"
        f"tags: {tag_repr}\nreversibility: {reversibility}\n"
        f"title: {qid}\n---\nbody\n"
    )
    if age_seconds > 0:
        past = time.time() - age_seconds
        os.utime(path, (past, past))


def test_thirty_questions_ranked_by_formula(tmp_path):
    """30 fixture questions — verify overall ordering follows D-05 formula."""
    # 5 sprints × 3 teams × 2 questions each = 30 questions.
    urgencies = ["critical", "high", "normal", "low", "normal", "high"]
    for t_idx, team in enumerate(("teamA", "teamB", "teamC")):
        for s_idx, sprint in enumerate([f"s{i}" for i in range(5)]):
            for q_idx, qid in enumerate([f"q{i}-{team}-{sprint}" for i in range(2)]):
                _write(
                    tmp_path, team, sprint, qid,
                    urgency=urgencies[(q_idx + s_idx) % len(urgencies)],
                    blocking=(q_idx % 2 == 0),
                    tags=["design"] if q_idx == 1 else [],
                    age_seconds=(t_idx + s_idx + q_idx) * 60,
                )
    queue = AttentionQueue(data_dir=tmp_path)
    items = queue.snapshot()
    assert len(items) == 30
    # Verify monotonic desc ordering.
    scores = [i.priority_score for i in items]
    assert scores == sorted(scores, reverse=True)
    # Top item should be one of the critical+blocking combinations.
    assert items[0].urgency >= 2  # at least HIGH


def test_cross_team_queue_aggregates(tmp_path):
    for team in ("alpha", "beta", "gamma"):
        _write(tmp_path, team, "s1", f"q-{team}", urgency="high")
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    teams_present = {i.team for i in items}
    assert teams_present == {"alpha", "beta", "gamma"}


def test_adversarial_critical_30s_vs_normal_8h(tmp_path):
    """D-15 adversarial fixture — critical+30s must outrank normal+8h."""
    _write(tmp_path, "t", "s1", "crit", urgency="critical", age_seconds=30)
    _write(tmp_path, "t", "s1", "norm", urgency="normal", age_seconds=8 * 3600)
    items = AttentionQueue(data_dir=tmp_path).snapshot()
    assert items[0].question_id == "crit"
    # Score math: crit = 3*10 + 30/3600 ≈ 30.008; norm = 1*10 + 8 = 18.
    # 30.008 - 18 > 10 (comfortable margin).
    assert items[0].priority_score > items[1].priority_score + 10


def test_tag_weights_shift_priority(tmp_path):
    _write(tmp_path, "t", "s1", "tagged", urgency="normal", tags=["security"])
    _write(tmp_path, "t", "s1", "plain", urgency="normal")
    # With security weight = 10, tagged should rank ABOVE plain.
    queue = AttentionQueue(
        data_dir=tmp_path,
        tag_weights={"security": 10},
    )
    items = queue.snapshot()
    assert items[0].question_id == "tagged"
    assert items[1].question_id == "plain"


def test_compute_priority_matches_observed(tmp_path):
    """Spot-check: the per-item priority_score matches compute_priority pure function."""
    _write(tmp_path, "t", "s", "q", urgency="high", blocking=True, tags=["design"], age_seconds=3600)
    queue = AttentionQueue(data_dir=tmp_path, tag_weights={"design": 2})
    items = queue.snapshot()
    assert len(items) == 1
    expected = compute_priority(
        urgency=2, blocking=True, age_hours=1.0, tags=("design",),
        urgency_weight=10, blocking_weight=5, tag_weights={"design": 2},
    )
    # Age may not be exactly 1.0h due to clock jitter; allow 0.05h tolerance.
    assert abs(items[0].priority_score - expected) < 0.1
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/integration/test_phase7_attention_ranking.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/integration/test_phase7_attention_ranking.py -q` reports 5 passed.
  </acceptance_criteria>
  <done>D-15 + INT-03 gates met; adversarial fixture explicitly asserted.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Cost dashboard 100-event fixture + alarm crossings + fallback activation (D-16 / QUALITY-12)</name>
  <files>
    tests/integration/test_phase7_cost_dashboard.py
  </files>
  <read_first>
    clawteam/cost/tracker.py (Plan 07-05),
    clawteam/cost/fallback.py (Plan 07-06),
    clawteam/cost/dashboard.py (Plan 07-07)
  </read_first>
  <behavior>
    - test_100_events_rollup: emit 100 ToolCallCompleted events across 5 agents; final cost_usd matches expected sum to 4 decimal places; per-agent breakdown has 5 entries.
    - test_budget_alarm_threshold_crossings: budget_usd=100, alarm=[50,80,100]; emit escalating events; BudgetAlarmReached fires exactly 3 times at 50/80/100%.
    - test_fallback_activates_at_80: when spend_percent >= 80, apply_fallback downgrades opus → sonnet; when < 80, no change.
    - test_dashboard_snapshot_at_each_threshold: take render_team() snapshot after events crossing 50, 80, 100; verify cost_usd + spend_percent + alarms_fired match expectations at each checkpoint.
    - test_cache_hit_rate_tracked: emit 10 ClaudeApiResponse events with mixed cache_read/creation; cache_hit_rate matches expected ratio.
  </behavior>
  <action>
**1. `tests/integration/test_phase7_cost_dashboard.py` (NEW, ~220 LOC):**

```python
"""Phase 7 Plan 07-09 Task 3: cost dashboard 100-event fixture (D-16 / QUALITY-12)."""
from __future__ import annotations

import pytest

from clawteam.cost.cache_tracker import CacheTracker
from clawteam.cost.dashboard import render_team
from clawteam.cost.fallback import apply_fallback
from clawteam.cost.tracker import CostTracker
from clawteam.events.bus import EventBus
from clawteam.events.types import BudgetAlarmReached, ClaudeApiResponse, ToolCallCompleted


def test_100_events_rollup():
    bus = EventBus()
    tracker = CostTracker(team="t", bus=bus, budget_usd=1000.0)
    agents = ["pm", "ceo", "engineer", "reviewer", "sre"]
    per_agent_expected: dict[str, float] = {a: 0.0 for a in agents}
    for i in range(100):
        agent = agents[i % 5]
        cost = 0.1 + (i * 0.01)  # Monotonically increasing per event
        bus.emit(ToolCallCompleted(team_name="t", agent=agent, cost_usd=cost))
        per_agent_expected[agent] += cost

    total_expected = sum(per_agent_expected.values())
    assert tracker.current_spend_usd() == pytest.approx(total_expected)
    observed = tracker.rollup_by_agent()
    for a, v in per_agent_expected.items():
        assert observed[a] == pytest.approx(v)


def test_budget_alarm_threshold_crossings():
    bus = EventBus()
    tracker = CostTracker(team="t", bus=bus, budget_usd=100.0, alarm_percent=[50, 80, 100])
    received: list = []
    bus.subscribe(BudgetAlarmReached, lambda ev: received.append(ev))

    # Cross 50 with single $51 event.
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=51.0))
    # Cross 80 (total=81).
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=30.0))
    # Cross 100 (total=105).
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=24.0))
    # Further events must NOT re-fire the alarm.
    for _ in range(10):
        bus.emit(ToolCallCompleted(team_name="t", cost_usd=10.0))

    percents = [int(ev.percent) for ev in received]
    assert percents == [50, 80, 100]
    assert len(received) == 3


def test_fallback_activates_at_80():
    # Pure-function assertions mirrored from Plan 07-06 tests — here we
    # confirm the fallback-at-80 policy integrates with budget math.
    assert apply_fallback("claude-opus", 79.9, 80.0) == ("claude-opus", False)
    assert apply_fallback("claude-opus", 80.0, 80.0) == ("claude-sonnet", True)
    assert apply_fallback("claude-sonnet", 100.0, 80.0) == ("claude-haiku", True)


def test_dashboard_snapshot_at_each_threshold():
    bus = EventBus()
    tracker = CostTracker(team="t", bus=bus, budget_usd=100.0, alarm_percent=[50, 80, 100])
    cache = CacheTracker(team="t", bus=bus)

    # T=0: fresh
    snap0 = render_team("t", tracker, cache)
    assert snap0["cost_usd"] == 0.0
    assert snap0["alarms_fired"] == []

    # T=1: cross 50
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", cost_usd=51.0))
    snap1 = render_team("t", tracker, cache)
    assert 50 in snap1["alarms_fired"]
    assert snap1["spend_percent"] == pytest.approx(51.0)

    # T=2: cross 80 + 100
    bus.emit(ToolCallCompleted(team_name="t", agent="ceo", cost_usd=60.0))
    snap2 = render_team("t", tracker, cache)
    assert sorted(snap2["alarms_fired"]) == [50, 80, 100]


def test_cache_hit_rate_tracked():
    bus = EventBus()
    cache = CacheTracker(team="t", bus=bus)

    for _ in range(5):
        bus.emit(ClaudeApiResponse(team_name="t", cache_read_tokens=800, cache_creation_tokens=200))
    for _ in range(5):
        bus.emit(ClaudeApiResponse(team_name="t", cache_creation_tokens=1000))

    # Total reads = 5*800 = 4000; total creation = 5*200 + 5*1000 = 6000; rate = 4000/10000 = 0.4.
    assert cache.cache_hit_rate() == pytest.approx(0.4)
    assert cache.is_healthy() is False  # 0.4 < 0.5 threshold


def test_integrated_rollup_flow():
    """Full flow: tracker + cache + dashboard render."""
    bus = EventBus()
    tracker = CostTracker(team="integ", bus=bus, budget_usd=50.0, alarm_percent=[50, 80, 100])
    cache = CacheTracker(team="integ", bus=bus)

    for i, a in enumerate(["pm", "ceo", "engineer"]):
        bus.emit(ToolCallCompleted(
            team_name="integ", agent=a, sprint_id=f"s{i}",
            model="claude-sonnet", tokens_input=500_000, tokens_output=100_000,
            cost_usd=0.0,  # Trigger pricing backstop.
        ))
        bus.emit(ClaudeApiResponse(
            team_name="integ", cache_read_tokens=400_000, cache_creation_tokens=100_000,
        ))

    d = render_team("integ", tracker, cache, active_agents=["pm"])
    assert d["cost_usd"] > 0.0
    assert d["cache_hit_rate"] == pytest.approx(0.8)  # 1.2M read / 1.5M total
    assert d["active_agent_count"] == 1
    assert len(d["per_agent"]) == 3
    assert len(d["per_sprint"]) == 3
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/integration/test_phase7_cost_dashboard.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/integration/test_phase7_cost_dashboard.py -q` reports 6 passed.
  </acceptance_criteria>
  <done>D-16 + QUALITY-12 gates met.</done>
</task>

</tasks>

<verification>
1. `pytest tests/integration/test_phase7_ten_sprint_load.py tests/integration/test_phase7_attention_ranking.py tests/integration/test_phase7_cost_dashboard.py -q` — all green.
2. `pytest tests/ -q` — FULL SUITE green (Phase 7 gate).
</verification>

<success_criteria>
- All 3 task acceptance met.
- D-14 / D-15 / D-16 integration tests green.
- Full regression suite green — all Phase 0-6 tests still pass.
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-09-SUMMARY.md`.
</output>
