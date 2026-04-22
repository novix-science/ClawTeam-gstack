---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 02
type: execute
wave: 1
depends_on: [07-01]
files_modified:
  - clawteam/sprint/conductor.py
  - clawteam/rate_limit/__init__.py
  - clawteam/rate_limit/monitor.py
  - tests/rate_limit/__init__.py
  - tests/rate_limit/test_monitor.py
  - tests/sprint/test_conductor_concurrency.py
autonomous: true
requirements:
  - CORE-06
  - QUALITY-04
tags:
  - concurrency
  - asyncio-semaphore
  - rate-limiting
  - sprint-conductor-extension

must_haves:
  truths:
    - "SprintConductor gains three asyncio.Semaphore caps (sprint, per-agent, active-agent) loaded from ConductorConfig with defaults (10, 1, 6)"
    - "SprintConductor exposes an async start_sprint_async(goal) that consults RateLimitMonitor then acquires the sprint semaphore; on timeout or saturation writes queue_status to SprintState"
    - "Per-agent semaphore (default 1) enforced at dispatch_turn; test verifies sibling-sprint concurrent-pm blocked"
    - "Active-agent semaphore (default 6) + active_agents() accessor; DormancyTransition emitted on state change"
    - "RateLimitMonitor records 429 responses in a 60s sliding window; is_saturated() returns True when recent_429_count > threshold (3)"
    - "Existing sync start_sprint path untouched — Phase 2-6 tests pass without modification (BC preserved)"
  artifacts:
    - path: clawteam/rate_limit/monitor.py
      provides: "RateLimitMonitor class"
      contains: "class RateLimitMonitor"
    - path: clawteam/sprint/conductor.py
      provides: "SprintConductor concurrency extensions"
      contains: "start_sprint_async|_sprint_sem|_active_agent_sem|active_agents|_rate_limit_monitor"
  key_links:
    - from: clawteam/sprint/conductor.py
      to: clawteam/rate_limit/monitor.py
      via: "Conductor constructs RateLimitMonitor; calls is_saturated() in start_sprint_async"
      pattern: "RateLimitMonitor|is_saturated"
    - from: clawteam/sprint/conductor.py
      to: clawteam/sprint/state.py
      via: "SprintState.queue_status written on timeout or saturation"
      pattern: "queue_status"
---

<objective>
Wave 1 — add `asyncio.Semaphore(n)` caps to SprintConductor for sprints/per-agent/active-agents (D-01/02/03) + `RateLimitMonitor` (D-13) that conductor consults before acquiring the sprint semaphore. Existing sync start_sprint path stays in place for Phase 2-6 callers (BC).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-01-wave0-substrate-PLAN.md

<interfaces>
From clawteam/sprint/conductor.py (existing sync start_sprint at line 284):
```python
def start_sprint(self, goal: str, auto_advance: bool = True) -> SprintState:
    with self._lock:
        sprint_id = uuid.uuid4().hex[:8]
        first = _first_phase()
        state = SprintState(...)
        save_sprint_state(state)
        self._emit_phase_transition(...)
        return state
```

From clawteam/templates/__init__.py (Plan 07-01):
```python
class ConductorConfig(BaseModel):
    max_concurrent_sprints: int = 10
    max_tasks_per_agent: int = 1
    max_active_agents: int = 6
    acquire_timeout_seconds: float = 60.0
```

From clawteam/events/types.py (Plan 07-01):
```python
@dataclass class RateLimitSaturated(HarnessEvent): ...
@dataclass class DormancyTransition(HarnessEvent): ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: RateLimitMonitor with 60s sliding 429-bucket window</name>
  <files>
    clawteam/rate_limit/monitor.py,
    clawteam/rate_limit/__init__.py,
    tests/rate_limit/__init__.py,
    tests/rate_limit/test_monitor.py
  </files>
  <read_first>
    clawteam/events/bus.py (EventBus.emit shape),
    clawteam/events/types.py (RateLimitSaturated dataclass from Plan 07-01)
  </read_first>
  <behavior>
    - Test 1: `test_fresh_monitor_not_saturated` — new monitor; is_saturated() is False.
    - Test 2: `test_one_429_not_saturated` — record_429() once; is_saturated() still False (threshold=3).
    - Test 3: `test_threshold_plus_one_saturated` — record_429() four times; is_saturated() True.
    - Test 4: `test_window_expiry_un_saturates` — record 4×429 at t=0; at t=61 (fake clock); is_saturated() False.
    - Test 5: `test_emits_rate_limit_saturated_event_on_threshold_cross` — subscribe to bus; record 4×429; event emitted exactly once with recent_429_count=4.
    - Test 6: `test_re_saturation_after_expiry_re_emits` — record 4×429; advance clock past 60s; record another 4×429; event fires again.
    - Test 7: `test_custom_threshold_and_window` — monitor with threshold=5, window_seconds=30; verify.
    - Test 8: `test_thread_safe` — concurrent record_429() from 10 threads × 10 calls each; final count correct.
  </behavior>
  <action>
**1. `clawteam/rate_limit/monitor.py` (NEW, ~90 LOC):**

```python
"""RateLimitMonitor — 429-count-bucketed saturation detector (D-13).

Phase 7 substrate. Conductor consults is_saturated() at start_sprint_async
to decide whether to queue the sprint instead of launching immediately.

Detection is provider-agnostic — relies on caller invoking record_429()
on any 429 response. Does NOT parse X-RateLimit-Remaining headers (some
providers don't emit them). 60-second sliding window is a reasonable
default for Anthropic TPM buckets per research.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable

from clawteam.events.bus import EventBus
from clawteam.events.types import RateLimitSaturated


class RateLimitMonitor:
    """Slide a 60-second window of 429 timestamps; flag saturation.

    Thread-safe. Emits RateLimitSaturated exactly once per
    un-saturated → saturated transition. Re-emits if the window clears
    and another burst crosses the threshold.
    """

    def __init__(
        self,
        team_name: str = "",
        *,
        threshold: int = 3,
        window_seconds: int = 60,
        bus: EventBus | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._team = team_name
        self._threshold = threshold
        self._window = float(window_seconds)
        self._bus = bus
        self._clock = clock
        self._events: deque[float] = deque()
        self._lock = threading.RLock()
        self._was_saturated: bool = False

    def record_429(self) -> None:
        """Record one 429 response. Emits event on threshold cross."""
        with self._lock:
            now = self._clock()
            self._events.append(now)
            self._expire(now)
            is_now = len(self._events) > self._threshold
            if is_now and not self._was_saturated:
                self._was_saturated = True
                self._emit(len(self._events))
            elif not is_now and self._was_saturated:
                # Window cleared; rearm for next burst.
                self._was_saturated = False

    def is_saturated(self) -> bool:
        """Return True when >threshold 429s observed in the last window_seconds."""
        with self._lock:
            now = self._clock()
            self._expire(now)
            count = len(self._events)
            saturated = count > self._threshold
            # Self-heal: if previously saturated but window cleared, rearm.
            if not saturated and self._was_saturated:
                self._was_saturated = False
            return saturated

    def recent_429_count(self) -> int:
        with self._lock:
            now = self._clock()
            self._expire(now)
            return len(self._events)

    def _expire(self, now: float) -> None:
        cutoff = now - self._window
        while self._events and self._events[0] < cutoff:
            self._events.popleft()

    def _emit(self, count: int) -> None:
        if self._bus is None:
            return
        try:
            self._bus.emit(
                RateLimitSaturated(
                    team_name=self._team,
                    recent_429_count=count,
                    threshold=self._threshold,
                    window_seconds=int(self._window),
                )
            )
        except Exception:  # pragma: no cover — defensive
            pass


__all__ = ["RateLimitMonitor"]
```

**2. `clawteam/rate_limit/__init__.py` — EDIT from Plan 07-01 skeleton:**

```python
"""Rate-limit substrate — 429-bucket monitor consulted by SprintConductor.

Phase 7 Plan 07-02 adds RateLimitMonitor; conductor.start_sprint_async
consults is_saturated() before acquiring the concurrent-sprint semaphore.
"""
from __future__ import annotations

from clawteam.rate_limit.monitor import RateLimitMonitor

__all__ = ["RateLimitMonitor"]
```

**3. Tests:** `tests/rate_limit/test_monitor.py` (~180 LOC). Use a fake clock `FakeClock(now=0.0)` with `advance(seconds)` method; pass as `clock=` kwarg. For Test 5 subscribe a handler collector:

```python
def test_emits_rate_limit_saturated_event_on_threshold_cross():
    bus = EventBus()
    received: list = []
    bus.subscribe(RateLimitSaturated, lambda ev: received.append(ev))
    clock = FakeClock(0.0)
    monitor = RateLimitMonitor(team_name="t", bus=bus, clock=clock.now)
    for _ in range(4):
        monitor.record_429()
    assert monitor.is_saturated() is True
    assert len(received) == 1
    assert received[0].recent_429_count == 4
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/rate_limit/test_monitor.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "class RateLimitMonitor" clawteam/rate_limit/monitor.py` succeeds.
    - `pytest tests/rate_limit/test_monitor.py -q` reports 8 passed.
    - `python -c "from clawteam.rate_limit import RateLimitMonitor; print('ok')"` prints "ok".
  </acceptance_criteria>
  <done>Conductor can consult monitor; event emission proven; thread-safety proven.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: SprintConductor semaphore extension + start_sprint_async + active_agents() + dispatch_turn wrapper</name>
  <files>
    clawteam/sprint/conductor.py,
    tests/sprint/test_conductor_concurrency.py
  </files>
  <read_first>
    clawteam/sprint/conductor.py (full — esp. __init__ at lines 236-280 and start_sprint at lines 284-309),
    clawteam/rate_limit/monitor.py (Task 1 output),
    clawteam/templates/__init__.py (ConductorConfig from Plan 07-01),
    tests/test_sprint_conductor.py (existing BC tests to preserve)
  </read_first>
  <behavior>
    - Test 1 (BC): `test_start_sprint_sync_path_unchanged` — old sync start_sprint still works with no config passed.
    - Test 2: `test_start_sprint_async_happy_path` — one sprint → semaphore acquired, sprint runs, queue_status="".
    - Test 3: `test_eleventh_sprint_queued_capacity` — 10 sprints block sem; 11th times out after acquire_timeout_seconds=0.1 (test override); queue_status == "queued_capacity".
    - Test 4: `test_rate_limit_saturated_queues_sprint` — monkeypatch `is_saturated() -> True`; next start_sprint_async sets queue_status="rate_limit_saturated".
    - Test 5: `test_active_agents_accessor_starts_empty` — conductor.active_agents() returns empty list before any dispatch.
    - Test 6: `test_per_agent_semaphore_blocks_concurrent_pm` — dispatch_turn("pm") twice concurrently (different sprints); second call blocks until first releases.
    - Test 7: `test_active_agent_slot_cap` — max_active_agents=2; dispatch 3 agents concurrently; 3rd one waits.
    - Test 8: `test_dormancy_transition_emitted` — dispatch agent; release; assert DormancyTransition fires with from_state="active", to_state="dormant".
  </behavior>
  <action>
**1. `clawteam/sprint/conductor.py` — EDIT:**

a) Add import of ConductorConfig + RateLimitMonitor (near existing imports, lazy in __init__):

```python
# at top:
import asyncio as _asyncio
import contextlib

# inside __init__, after self._phase_cap_override resolution:
```

b) Extend `__init__` signature + body:

```python
    def __init__(
        self,
        team_name: str,
        *,
        force_interactive_phases: list[str] | None = None,
        artifact_cap_bytes: int | None = None,
        phase_artifact_cap_bytes: int | None = None,
        bus: "EventBus | None" = None,
        plugin_manager=None,
        conductor_config=None,  # Phase 7 Plan 07-02: ConductorConfig | None
        rate_limit_monitor=None,  # Phase 7 Plan 07-02: RateLimitMonitor | None (tests inject)
    ) -> None:
        # ... existing validation, _lock, bus init, plugin_manager, register_safety_subscribers ...
        # ... existing cap resolution ...

        # ── Phase 7 Plan 07-02: concurrency caps + rate-limit monitor ──
        from clawteam.templates import ConductorConfig
        from clawteam.rate_limit import RateLimitMonitor

        if conductor_config is None:
            # Try to pull from team template; fall back to defaults.
            conductor_config = self._resolve_conductor_config()
        self._conductor_config = conductor_config
        self._sprint_sem = _asyncio.Semaphore(conductor_config.max_concurrent_sprints)
        self._active_agent_sem = _asyncio.Semaphore(conductor_config.max_active_agents)
        self._per_agent_sems: dict[str, _asyncio.Semaphore] = {}
        self._active_agents_set: set[str] = set()
        self._active_agents_lock = threading.RLock()  # existing threading import already present
        self._rate_limit_monitor = rate_limit_monitor or RateLimitMonitor(
            team_name=team_name,
            bus=self.bus,
        )
```

c) Add `_resolve_conductor_config` helper:

```python
    def _resolve_conductor_config(self):
        """Load ConductorConfig from the team's template; default if missing."""
        from clawteam.templates import ConductorConfig
        try:
            from clawteam.team.manager import TeamManager
            from clawteam.templates import load_template
            cfg = TeamManager.get_team(self.team_name)
            if cfg and getattr(cfg, "template", ""):
                tmpl = load_template(cfg.template)
                if tmpl.conductor is not None:
                    return tmpl.conductor
        except Exception:  # pragma: no cover — defensive; fall through to defaults
            pass
        return ConductorConfig()
```

d) Add new methods:

```python
    # ── Phase 7 Plan 07-02: async concurrency entry points ──

    async def start_sprint_async(
        self, goal: str, auto_advance: bool = True
    ) -> SprintState:
        """Phase 7 async entrypoint — consults rate-limit + acquires sprint semaphore.

        On RateLimit saturation OR acquire timeout, writes queue_status to the
        newly-created SprintState and returns without holding the semaphore.
        Existing sync start_sprint() remains for Phase 2-6 callers (BC).
        """
        if self._rate_limit_monitor.is_saturated():
            state = self.start_sprint(goal, auto_advance=auto_advance)
            state.queue_status = "rate_limit_saturated"
            save_sprint_state(state)
            return state
        try:
            await _asyncio.wait_for(
                self._sprint_sem.acquire(),
                timeout=self._conductor_config.acquire_timeout_seconds,
            )
        except _asyncio.TimeoutError:
            state = self.start_sprint(goal, auto_advance=auto_advance)
            state.queue_status = "queued_capacity"
            save_sprint_state(state)
            return state
        try:
            return self.start_sprint(goal, auto_advance=auto_advance)
        except Exception:
            self._sprint_sem.release()
            raise

    def release_sprint_slot(self, sprint_id: str) -> None:
        """Release the sprint semaphore when a sprint reaches reflect-phase or is paused."""
        try:
            self._sprint_sem.release()
        except ValueError:
            pass  # idempotent — already released

    def _get_agent_sem(self, role: str) -> _asyncio.Semaphore:
        if role not in self._per_agent_sems:
            self._per_agent_sems[role] = _asyncio.Semaphore(
                self._conductor_config.max_tasks_per_agent
            )
        return self._per_agent_sems[role]

    @contextlib.asynccontextmanager
    async def dispatch_turn(self, agent_role: str, agent_name: str = ""):
        """Async context manager — acquires per-agent + active-agent slots.

        Usage:
            async with conductor.dispatch_turn("pm", "pm"):
                ... do agent work ...

        Emits DormancyTransition on enter (dormant→active) and exit (active→dormant).
        """
        per_agent = self._get_agent_sem(agent_role)
        await per_agent.acquire()
        await self._active_agent_sem.acquire()
        name = agent_name or agent_role
        with self._active_agents_lock:
            self._active_agents_set.add(name)
        self._emit_dormancy(name, agent_role, "dormant", "active")
        try:
            yield
        finally:
            with self._active_agents_lock:
                self._active_agents_set.discard(name)
            self._active_agent_sem.release()
            per_agent.release()
            self._emit_dormancy(name, agent_role, "active", "dormant")

    def active_agents(self) -> list[str]:
        """Return the list of currently-active agent names (QUALITY-04)."""
        with self._active_agents_lock:
            return sorted(self._active_agents_set)

    def _emit_dormancy(self, agent: str, role: str, from_state: str, to_state: str) -> None:
        try:
            from clawteam.events.types import DormancyTransition
            self.bus.emit(
                DormancyTransition(
                    team_name=self.team_name,
                    agent=agent,
                    role=role,
                    from_state=from_state,
                    to_state=to_state,
                )
            )
        except Exception:  # pragma: no cover
            pass
```

Note: the existing `_lock = RLock()` is already present. threading is already imported. Keep existing sync start_sprint untouched.

**2. `tests/sprint/test_conductor_concurrency.py` (NEW, ~240 LOC):**

```python
"""Phase 7 Plan 07-02: SprintConductor concurrency caps + rate-limit consult."""
import asyncio
import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import DormancyTransition, RateLimitSaturated
from clawteam.sprint.conductor import SprintConductor
from clawteam.rate_limit import RateLimitMonitor
from clawteam.templates import ConductorConfig


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return tmp_path


def _make_conductor(**overrides):
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
    )


def test_start_sprint_sync_path_unchanged(isolated):
    # BC: no conductor_config — defaults; sync path works.
    c = SprintConductor(team_name="t1")
    s = c.start_sprint(goal="g")
    assert s.goal == "g"
    assert s.queue_status == ""


def test_start_sprint_async_happy_path(isolated):
    c = _make_conductor()
    async def run():
        return await c.start_sprint_async(goal="g")
    s = asyncio.run(run())
    assert s.queue_status == ""


def test_over_cap_sprint_queued(isolated):
    c = _make_conductor(max_concurrent_sprints=1, acquire_timeout_seconds=0.05)
    async def run():
        s1 = await c.start_sprint_async(goal="g1")
        # 2nd sprint can't acquire (sem=1, not released); times out → queued
        s2 = await c.start_sprint_async(goal="g2")
        return s1, s2
    s1, s2 = asyncio.run(run())
    assert s1.queue_status == ""
    assert s2.queue_status == "queued_capacity"


def test_rate_limit_saturation_queues(isolated, monkeypatch):
    c = _make_conductor()
    monkeypatch.setattr(c._rate_limit_monitor, "is_saturated", lambda: True)
    async def run():
        return await c.start_sprint_async(goal="g")
    s = asyncio.run(run())
    assert s.queue_status == "rate_limit_saturated"


def test_active_agents_empty_initially(isolated):
    c = _make_conductor()
    assert c.active_agents() == []


def test_per_agent_semaphore_serializes(isolated):
    c = _make_conductor(max_tasks_per_agent=1, max_active_agents=4)
    results = []
    async def work(label):
        async with c.dispatch_turn("pm", f"pm-{label}"):
            results.append(f"enter-{label}")
            await asyncio.sleep(0.02)
            results.append(f"exit-{label}")
    async def run():
        await asyncio.gather(work("a"), work("b"))
    asyncio.run(run())
    # 'enter-a' → 'exit-a' → 'enter-b' → 'exit-b' OR the opposite order,
    # but NOT interleaved (per-agent semaphore serializes).
    assert results.index("exit-a") == results.index("enter-a") + 1 or \
           results.index("exit-b") == results.index("enter-b") + 1


def test_active_agent_cap(isolated):
    c = _make_conductor(max_active_agents=2, max_tasks_per_agent=1)
    concurrent_observed = []
    async def work(role):
        async with c.dispatch_turn(role, role):
            concurrent_observed.append(len(c.active_agents()))
            await asyncio.sleep(0.02)
    async def run():
        await asyncio.gather(work("pm"), work("ceo"), work("engineer"))
    asyncio.run(run())
    # Cap=2 so no observation exceeds 2.
    assert max(concurrent_observed) <= 2


def test_dormancy_events_emitted(isolated):
    c = _make_conductor()
    received = []
    c.bus.subscribe(DormancyTransition, lambda ev: received.append(ev))
    async def run():
        async with c.dispatch_turn("pm", "pm"):
            pass
    asyncio.run(run())
    assert len(received) == 2
    assert received[0].from_state == "dormant" and received[0].to_state == "active"
    assert received[1].from_state == "active" and received[1].to_state == "dormant"
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/sprint/test_conductor_concurrency.py tests/test_sprint_conductor.py tests/sprint/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "start_sprint_async" clawteam/sprint/conductor.py` succeeds.
    - `grep -q "active_agents" clawteam/sprint/conductor.py` succeeds.
    - `grep -q "_sprint_sem" clawteam/sprint/conductor.py` succeeds.
    - `grep -q "_rate_limit_monitor" clawteam/sprint/conductor.py` succeeds.
    - `pytest tests/sprint/test_conductor_concurrency.py -q` reports 8 passed.
    - BC: `pytest tests/test_sprint_conductor.py tests/sprint/ -q` still green.
  </acceptance_criteria>
  <done>All three semaphore caps live; async entry point consults rate-limit monitor; sync path BC preserved.</done>
</task>

</tasks>

<verification>
1. `pytest tests/rate_limit/ tests/sprint/test_conductor_concurrency.py tests/test_sprint_conductor.py tests/sprint/ -q` — all green.
2. `python -c "import asyncio; from clawteam.sprint.conductor import SprintConductor; from clawteam.templates import ConductorConfig; c = SprintConductor('t1', conductor_config=ConductorConfig()); print(c.active_agents())"` — prints `[]`.
</verification>

<success_criteria>
- Tasks 1-2 acceptance criteria met.
- 10-sprint load test (Plan 07-09) has the substrate it needs.
- Existing Phase 2-6 conductor tests all green (BC).
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-02-SUMMARY.md`.
</output>
