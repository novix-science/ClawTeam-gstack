# Phase 7: Parallel Sprints, AttentionQueue UX & Cost Controls — Research

**Researched:** 2026-04-22
**Domain:** Concurrency caps for `SprintConductor` + cross-sprint `AttentionQueue` UX + cost observability / model fallback ladder + rate-limit-aware scheduling
**Confidence:** HIGH on substrate (all primitives exist in Phases 0-6 code); MEDIUM on `tool_call_completed` event shape (must be defined fresh in Phase 7 Wave 0 — not yet in the codebase despite Phase 5 CONTEXT referencing it); HIGH on watchdog + questionary + rich precedent.
**Research flag:** MEDIUM — final milestone phase; attention-queue digest UX benefits from a quick iteration; prompt caching + rate-limit backoff have clear docs.

---

## Summary

Phase 7 ships three top-level packages on top of a now-mature 6-phase substrate: `clawteam/attention/` (queue + watcher + digest + CLI), `clawteam/cost/` (tracker + dashboard + fallback + cache_tracker), and `clawteam/rate_limit/` (monitor). Plus a surgical extension of `SprintConductor` to add three `asyncio.Semaphore` caps + a `queue_status` field on `SprintState` (both additively, extra="ignore" path already proven by Phase 2/4/6 pydantic extensions).

Three design choices drive safety: (1) **stateless read-side** for `AttentionQueue` — priority is a function of question.md frontmatter + mtime, so each `clawteam attend` invocation is a fresh filesystem glob with zero persistent queue state (same pattern `InteractionGate` uses); (2) **advisory-only** cost alarms + rate-limit monitor — emit `BudgetAlarmReached` / `RateLimitSaturated` events but never block sprint work without explicit user opt-in (defaults to graceful degradation via model fallback, not hard-fail); (3) **optional-extra `[attend]`** mirrors the `[browser]` pattern from Phase 6 — `watchdog` is lazy-imported via `find_spec`, falls back to 2-second polling without watchdog.

The most important implementation hazard: `tool_call_completed` is **referenced in Phase 5 CONTEXT but not yet defined as a `HarnessEvent` dataclass** (verified by grep — only prose references exist). Phase 7 Wave 0 MUST define it along with `ClaudeApiResponse`, `BudgetAlarmReached`, `RateLimitSaturated`, `ZombieWorktreeGced`, and `DormancyTransition`. Without these, the cost tracker has nothing to subscribe to.

**Primary recommendation:** Ship 9 plans across 6 waves. Wave 0 = substrate (events + pyproject extra + SprintState.queue_status + config blocks). Wave 1 = SprintConductor concurrency primitives (semaphores + rate-limit monitor consult). Wave 2 = AttentionQueue package (queue + watcher + digest). Wave 3 = `clawteam attend` CLI subcommand group. Wave 4 = cost package (tracker + dashboard + fallback + cache_tracker). Wave 5 = cost dashboard integration in `clawteam team show` + zombie worktree GC in `clawteam doctor`. Wave 6 = 10-sprint load-test integration test (D-14/15/16).

---

## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 through D-16 — do NOT revisit)

- **D-01** `SprintConductor.max_concurrent_sprints` via `asyncio.Semaphore(n)` (default 10, from `gstack.toml [conductor] max_concurrent_sprints`). Sprints over cap enter `queued` state on `SprintState.queue_status`. 60s grace timeout.
- **D-02** Per-agent `asyncio.Semaphore(max_tasks_per_agent)` (default 1) at `SprintConductor.dispatch_turn(agent_role, ...)`.
- **D-03** Active-agent slot pool `asyncio.Semaphore(max_active_agents)` (default 6). Observable via `conductor.active_agents() -> list[AgentRef]`.
- **D-04** `AttentionQueue` is pure-read-side — no persisted priority. Each `clawteam attend` invocation re-globs.
- **D-05** Priority formula: `score = URGENCY × 10 + BLOCKING × 5 + age_hours + explicit_tag_weight`. URGENCY from `{critical=3, high=2, normal=1, low=0}`. Weights configurable via `[attention]`.
- **D-06** `watchdog` optional-extra at `pyproject.toml [project.optional-dependencies] attend = ["watchdog>=3,<4"]`. Lazy detection via `clawteam/attention/watcher.py::watchdog_available()`. Polling fallback = 2s.
- **D-07** `--summary` digest groups by `(sprint_id, tag_cluster, age_bucket)` with age buckets `{<1h, 1-2h, >2h, >8h}`. Plain-text; no TUI.
- **D-08** `--auto-accept-reversible` applies only to `reversibility: easy` questions with 15-min preview TTL. Writes `answer.md` with `auto_accepted: true` + placeholder body.
- **D-09** `clawteam/cost/` new package: `tracker.py` (listens `tool_call_completed`), `dashboard.py` (rendering for `clawteam team show`), `fallback.py` (model-fallback policy applied at `NativeCliAdapter` / `invoke_native_cli`), `cache_tracker.py` (cache hit rate from `claude_api_response` events).
- **D-10** `gstack.toml [cost]` block: `budget_usd` (100.0), `fallback_at_percent` (80), `alarm_percent` ([50, 80, 100]). Alarms emitted via `BudgetAlarmReached` event.
- **D-11** Model fallback ladder at `clawteam/cost/fallback.py::apply_fallback(model_pref, budget_state) -> model`. Ladder: opus → sonnet → haiku → haiku. Envelope flag `model_fallback_applied: true` when downgrade occurs.
- **D-12** Cache hit rate = `cache_read / (cache_read + cache_creation)` per team. >50% considered healthy.
- **D-13** `clawteam/rate_limit/monitor.py::RateLimitMonitor` records 429 responses; buckets by minute; `is_saturated()` when `recent_429_count > threshold` (default 3/min). Conductor consults before acquiring concurrent-sprint semaphore.
- **D-14** Integration test `tests/integration/test_phase7_ten_sprint_load.py`: 10 concurrent sprints under 5-min cap + 4 GB RAM, mocked Claude API.
- **D-15** AttentionQueue ranking test with 30 fixture questions + 5 sprints + 3 teams. Adversarial fixture: critical@30s outranks normal@8h.
- **D-16** Cost dashboard test with fixture event stream (100 events, 5 agents). Asserts rollup + alarm firing + fallback activation.

### Claude's Discretion

- Rich/typer layout of `clawteam attend` columns + colors.
- Pydantic field shapes for `AttentionItem`, `CostRollup`, `BudgetState`.
- Wave structure + plan count (this research recommends 9 plans / 6 waves).
- EventBus dataclass names for `BudgetAlarmReached`, `RateLimitSaturated`, `ZombieWorktreeGced`, `DormancyTransition`, `ToolCallCompleted`, `ClaudeApiResponse`.

### Deferred Ideas (OUT OF SCOPE — explicit)

- Multi-team Conductor UI / board panels → v2.
- Helper-spawning within engineer (sub-worktrees) → v1.x per FEATURES.md P2.
- Provider-specific deploy hooks replacing `gh pr checks --watch` → v1.1.
- ML-based attention priority (learned-from-user-behavior ranking) → v2.
- Cross-team cost pooling + chargeback dashboards → v2.

---

## Phase Requirements

| ID | Description | Research Support | Plan Coverage |
|----|-------------|------------------|--------------|
| CORE-06 | 10 concurrent sprints without race conditions | SprintConductor semaphore caps (D-01/02/03); 4 GB RAM budget load test (D-14) | 07-02 (semaphores), 07-09 (load test) |
| INT-03 | `AttentionQueue` priority-sorted cross-sprint queue | Stateless read-side glob (D-04); additive priority formula (D-05) | 07-03 (queue + watcher + digest), 07-09 (ranking test) |
| INT-04 | `clawteam attend` CLI prints top-N, opens `$EDITOR`, gate unblocks | Typer subcommand group (pattern matches Phase 6 `clawteam learn`); questionary picker | 07-04 (CLI) |
| INT-05 | `watchdog` optional refresh + 2s polling fallback | `attend` extra (D-06); mirrors Phase 6 `browser` extra pattern | 07-03 (watcher.py); 07-01 (pyproject) |
| QUALITY-04 | Active-agent slot pool N=6; dormancy | `asyncio.Semaphore(max_active_agents)` (D-03); `DormancyTransition` event | 07-02 (slot pool); 07-09 (agent-state sampling test) |
| QUALITY-05 | `clawteam attend --summary` digest view | Group by (sprint_id, tag_cluster, age_bucket) (D-07) | 07-03 (digest.py), 07-04 (`--summary` flag) |
| QUALITY-12 | Cost observability + model fallback + cache hit rate | `clawteam/cost/` substrate (D-09); apply_fallback (D-11); cache_tracker (D-12) | 07-05 (tracker + dashboard), 07-06 (fallback + cache_tracker), 07-07 (team show panel) |
| UX-06 | `clawteam attend` surfaces top-N + re-refresh | AttentionQueue.snapshot() + watcher (D-04/06) | 07-04 (CLI) |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `asyncio.Semaphore` caps + queue_status | Sprint substrate (SprintConductor + SprintState) | — | Phase 2 substrate extension; no new tier |
| RateLimitMonitor (429 tracking) | Rate-limit substrate (top-level) | EventBus | Generic; consulted by conductor before sprint-start |
| AttentionQueue snapshot | Attention substrate (top-level, pure read-side) | Filesystem (existing InteractionGate layout) | Generic; stateless glob over questions/ + answers/ |
| AttentionQueue watcher | Attention substrate | Optional watchdog extra | Feature-detected; polling fallback keeps zero-dep floor |
| `clawteam attend` CLI | CLI layer (`clawteam/cli/commands.py`) | Attention substrate + questionary + `$EDITOR` subprocess | Mirrors `clawteam learn`, `clawteam sprint approve` patterns |
| `clawteam/cost/tracker.py` | Cost substrate | EventBus (`tool_call_completed`) | Event-driven accounting; no polling |
| `clawteam/cost/dashboard.py` | Cost substrate | Existing `clawteam team show` | Rendering only; emits structured data for both JSON + rich |
| `clawteam/cost/fallback.py` | Cost substrate | `NativeCliAdapter` / `invoke_native_cli` | Policy applied at model-spawn sites (D-11) |
| `clawteam/cost/cache_tracker.py` | Cost substrate | EventBus (`claude_api_response`) | Listens for `cache_read_tokens` / `cache_creation_tokens` |
| Zombie-worktree GC | Workspace substrate (existing `clawteam/workspace/`) | `clawteam doctor --gc` entry | Pure fs walk + mtime check + disk-budget alarm |

---

## Standard Stack

### Core (no new required deps — enforces PROJECT.md "no new required runtime deps")

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic (existing) | >=2.0.0,<3.0.0 | `AttentionItem`, `CostRollup`, `BudgetState`, event dataclasses | Existing hard dep [VERIFIED: pyproject.toml] |
| `asyncio` (stdlib) | — | `Semaphore(n)` for 3 concurrency caps | Stdlib; Python 3.10+ baseline [VERIFIED: pyproject.toml requires-python] |
| `questionary` (existing) | >=2.0.1,<3.0.0 | `clawteam attend` interactive picker | Already in core deps; pattern matches Phase 5/6 wizards [VERIFIED: pyproject.toml] |
| `rich` (existing) | >=13,<15 | attend table + team-show cost panel | Already in core deps [VERIFIED: pyproject.toml] |
| `typer` (existing) | >=0.12,<1.0 | `clawteam attend` subcommand group | Already in core deps [VERIFIED: pyproject.toml] |
| `clawteam.events.bus.EventBus` + `register_event_type` | existing | 6 new event dataclasses | Phase 4/5/6 precedent — same registration pattern [VERIFIED: clawteam/events/bus.py:25-43] |
| `clawteam.fileutil.file_locked` + `atomic_write_text` | existing | SprintState saves; cost rollup cache | Already-proven concurrency primitive [VERIFIED: clawteam/fileutil.py] |

### Optional Extra (single new optional dep — matches STACK.md directive)

| Extra | Package | Version | Purpose | Gating |
|-------|---------|---------|---------|--------|
| `clawteam[attend]` | `watchdog` | `>=3,<4` | FS-event auto-refresh for AttentionQueue (INT-05) | `attention/watcher.py::watchdog_available()` via `importlib.util.find_spec`; 2-second polling fallback [CITED: D-06] |

**Installation:**
```bash
pip install 'clawteam[attend]'  # watchdog is optional; without it, polling works
```

**Version verification:** watchdog 3.x is LTS as of late 2024; no 4.x exists on PyPI (as of training cutoff). [ASSUMED — should verify with `pip index versions watchdog` at Wave 0 plan-prep.]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `asyncio.Semaphore` (our choice) | `threading.BoundedSemaphore` | Conductor is already async-friendly; asyncio-native avoids thread/async mix |
| Stateless read-side queue | Persistent priority-queue on disk | Stateless avoids consistency bugs; O(questions) cost is acceptable at N≤100 questions |
| Additive priority formula | Multiplicative | Additive is debuggable via `--explain`; no weight-tuning nightmares |
| Event-driven cost tracker | Poll-based cost tracker | Polling burns CPU; events are O(1) on emit |
| `watchdog` optional | `watchdog` required | Optional matches Phase 6 `browser` pattern; preserves zero-new-required-deps invariant |

---

## System Architecture Diagram

```
                          ┌──────────────────────────────────────────┐
                          │  gstack.toml [conductor] / [attention]   │
                          │           / [cost]                       │
                          └───────────────┬──────────────────────────┘
                                          │ config load
                                          ▼
    ┌────────────────────────────────────────────────────────────────┐
    │                      SprintConductor                           │
    │                                                                │
    │  max_concurrent_sprints: Semaphore(10)  ← gate on start_sprint │
    │  max_tasks_per_agent:    Semaphore(1)   ← gate on dispatch     │
    │  max_active_agents:      Semaphore(6)   ← gate on agent turn   │
    │                                                                │
    │  consults RateLimitMonitor.is_saturated() BEFORE acquiring     │
    │  max_concurrent_sprints — if saturated, SprintState.queue_status│
    │  = "rate_limit_saturated"                                      │
    └──────────┬──────────────────────────────┬──────────────────────┘
               │                              │
   emits event │                  dispatches  │ agent turn
               ▼                              ▼
   ┌─────────────────────┐          ┌─────────────────────────┐
   │ RateLimitMonitor    │◀─────────│ NativeCliAdapter /      │
   │ (bucketed 429s)     │  429s    │ invoke_native_cli       │
   └─────────────────────┘          │                         │
                                    │ consults                │
                                    │ cost.fallback.          │
                                    │ apply_fallback(model)   │
                                    └─┬───────────────────────┘
                                      │ emits ToolCallCompleted
                                      │      + ClaudeApiResponse
                                      ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                       EventBus                               │
   └──────────────────────────────────────────────────────────────┘
        │                     │                        │
        ▼                     ▼                        ▼
  ┌────────────┐      ┌───────────────┐        ┌──────────────┐
  │ cost.      │      │ cost.         │        │ clawteam     │
  │ tracker    │      │ cache_tracker │        │ team show    │
  └─────┬──────┘      └───────┬───────┘        └──────────────┘
        │ emits BudgetAlarm   │ rollup                ▲
        │                     │                       │ reads
        ▼                     ▼                       │
       EventBus             CostRollup ────────────────┘
        │
        ▼  listens → logs → Phase 7 attend --summary surfaces

  ┌──────────────────────────────────────────────────────────────┐
  │                  AttentionQueue (stateless)                  │
  │                                                              │
  │   glob ~/.clawteam/teams/*/sprints/*/questions/*.md          │
  │     ↓                                                        │
  │   filter out those with sibling answers/*.md                 │
  │     ↓                                                        │
  │   parse frontmatter (urgency, blocking, tags, reversibility) │
  │     ↓                                                        │
  │   compute priority_score = URGENCY×10 + BLOCKING×5 +         │
  │                            age_hours + tag_weight            │
  │     ↓                                                        │
  │   sort desc → AttentionItem list                             │
  └──────────────────┬───────────────────────────────────────────┘
                     │
          snapshot() │                  watchdog events
                     ▼                  (optional)
            ┌─────────────────┐        ┌─────────────────┐
            │ clawteam attend │◀───────│ watcher.py      │
            │   (typer)       │        │ polling | FS    │
            └─────────────────┘        └─────────────────┘
                     │
                     ▼ on user pick
              $EDITOR on question.md
                     │
                     ▼ on save
           InteractionGate unblocks → sprint advances
```

### Data Flow — Happy Path (one sprint, one question answered)

1. `clawteam sprint start --goal "..."` → `SprintConductor.start_sprint()` acquires `max_concurrent_sprints` semaphore.
2. Sprint advances to Think phase; pm agent writes `questions/1.md` with frontmatter `urgency: high`.
3. `InteractionGate.check()` returns `(False, "Open questions: 1")` → sprint blocked.
4. User runs `clawteam attend` → `AttentionQueue.snapshot()` globs all teams/sprints/questions/, ranks, returns list.
5. User picks question → `$EDITOR` opens `questions/1.md` → user edits → saves `answers/1.md` (via CLI save hook).
6. Watcher fires FileModifiedEvent → CLI re-renders remaining queue; `InteractionGate.check()` returns `(True, "")`.
7. Conductor advances phase; emits `PhaseTransition`.

### Data Flow — Cost Rollup

1. Agent invocation via `invoke_native_cli()` → `apply_fallback(model_pref, budget_state)` checks `tracker.current_spend`.
2. If `< fallback_at_percent` (80%) → use `model_pref` (e.g., "claude-opus"); else → "claude-sonnet".
3. Claude API response parsed; emits `ToolCallCompleted(tokens_input, tokens_output, model, cost_usd)` + `ClaudeApiResponse(cache_read_tokens, cache_creation_tokens)`.
4. `tracker` aggregates per (team, sprint, agent) → `CostRollup`.
5. If `current_spend / budget_usd` crosses 50%/80%/100% threshold → emits `BudgetAlarmReached`.
6. `clawteam team show` calls `dashboard.render(team)` which returns `{per_agent, per_sprint, cache_hit_rate, budget_state}`.

---

## Architecture Patterns

### Pattern 1: Concurrency caps via asyncio.Semaphore (D-01/02/03)

**What:** Three semaphores at different scopes.
**When to use:** Any bounded-resource gate where overcommit melts laptops.
**Example:**
```python
# clawteam/sprint/conductor.py extension
import asyncio

class SprintConductor:
    def __init__(self, ..., config: ConductorConfig):
        self._sprint_sem = asyncio.Semaphore(config.max_concurrent_sprints)
        self._active_agent_sem = asyncio.Semaphore(config.max_active_agents)
        self._per_agent_sems: dict[str, asyncio.Semaphore] = {}

    def _get_agent_sem(self, role: str) -> asyncio.Semaphore:
        if role not in self._per_agent_sems:
            self._per_agent_sems[role] = asyncio.Semaphore(
                self._config.max_tasks_per_agent
            )
        return self._per_agent_sems[role]

    async def start_sprint_async(self, goal: str) -> SprintState:
        # Consult rate-limit monitor first
        if self._rate_limit_monitor.is_saturated():
            state = self.start_sprint(goal)  # reuse sync path
            state.queue_status = "rate_limit_saturated"
            save_sprint_state(state)
            return state
        try:
            await asyncio.wait_for(
                self._sprint_sem.acquire(),
                timeout=60.0,
            )
        except asyncio.TimeoutError:
            state = self.start_sprint(goal)
            state.queue_status = "queued_capacity"
            save_sprint_state(state)
            return state
        return self.start_sprint(goal)  # existing sync path runs once slot held
```

### Pattern 2: Stateless AttentionQueue over the filesystem (D-04)

**What:** No persisted queue state — each `snapshot()` re-globs.
**When to use:** Derived/computed data where the filesystem IS the source of truth.
**Example:**
```python
# clawteam/attention/queue.py
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import os

@dataclass(frozen=True)
class AttentionItem:
    question_path: Path
    sprint_id: str
    team: str
    title: str
    urgency: int
    blocking: bool
    age_hours: float
    tags: tuple[str, ...]
    reversibility: str  # "easy" | "medium" | "hard"
    priority_score: float

class AttentionQueue:
    def __init__(self, data_dir: Path, config: AttentionConfig):
        self._data_dir = data_dir
        self._config = config

    def snapshot(self) -> list[AttentionItem]:
        items = []
        for q_path in self._data_dir.glob("teams/*/sprints/*/questions/*.md"):
            if self._has_answer(q_path):
                continue
            item = self._parse_question(q_path)
            if item:
                items.append(item)
        items.sort(key=lambda i: i.priority_score, reverse=True)
        return items
```

### Pattern 3: Cost tracker as event subscriber (D-09)

**What:** Zero-polling, event-driven accounting.
**When to use:** Aggregation over discrete emission sites (API calls, tool invocations).
**Example:**
```python
# clawteam/cost/tracker.py
from clawteam.events.bus import EventBus
from clawteam.events.types import ToolCallCompleted, BudgetAlarmReached

class CostTracker:
    def __init__(self, team: str, budget_usd: float, alarm_percent: list[float], bus: EventBus):
        self._team = team
        self._budget_usd = budget_usd
        self._alarm_percent = sorted(alarm_percent)
        self._fired_alarms: set[float] = set()
        self._bus = bus
        self._by_agent: dict[str, float] = {}  # cost_usd by agent
        bus.subscribe(ToolCallCompleted, self._on_tool_call)

    def _on_tool_call(self, ev: ToolCallCompleted) -> None:
        if ev.team_name != self._team:
            return
        self._by_agent[ev.agent] = self._by_agent.get(ev.agent, 0.0) + ev.cost_usd
        spent_pct = (self.current_spend_usd() / self._budget_usd) * 100.0
        for thresh in self._alarm_percent:
            if thresh in self._fired_alarms:
                continue
            if spent_pct >= thresh:
                self._fired_alarms.add(thresh)
                self._bus.emit(BudgetAlarmReached(
                    team_name=self._team,
                    percent=thresh,
                    spent_usd=self.current_spend_usd(),
                    budget_usd=self._budget_usd,
                ))

    def current_spend_usd(self) -> float:
        return sum(self._by_agent.values())
```

### Pattern 4: Model fallback ladder (D-11)

**What:** Pure function applied at `NativeCliAdapter` call-site.
**Example:**
```python
# clawteam/cost/fallback.py
FALLBACK_LADDER = {
    "claude-opus": "claude-sonnet",
    "claude-sonnet": "claude-haiku",
    "claude-haiku": "claude-haiku",  # already bottom
}

def apply_fallback(model_pref: str, spent_pct: float, fallback_at: float) -> tuple[str, bool]:
    """Return (effective_model, fallback_applied)."""
    if spent_pct < fallback_at:
        return model_pref, False
    return FALLBACK_LADDER.get(model_pref, model_pref), True
```

### Pattern 5: Watchdog optional detection (D-06)

**What:** `importlib.util.find_spec("watchdog")` — same as Phase 6 `playwright_available()`.
**Example:**
```python
# clawteam/attention/watcher.py
from importlib.util import find_spec

def watchdog_available() -> bool:
    return find_spec("watchdog") is not None
```

### Anti-Patterns to Avoid

- **Persisted priority queue:** Do NOT write a queue.json to disk. The filesystem glob + frontmatter parse IS the source of truth. Persisted queue would need consistency repair on crash.
- **Blocking on budget exhaustion:** Do NOT hard-fail at 100% budget — apply fallback ladder (opus → sonnet → haiku). Budget is advisory.
- **Polling in the cost tracker:** Events ONLY — polling burns CPU cross-sprint.
- **Cross-team cost pooling:** Teams are isolation boundaries. A cost rollup for team A never reads team B's events.
- **Hard-fail on rate-limit saturation:** Queue instead. 429 is transient.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| File-change watching | Custom inotify / FSEvents loop | `watchdog` (optional) + polling fallback | Cross-platform; maintained; already in our doctor |
| Priority queue | `heapq` with manual maintenance | `list.sort(key=)` on stateless snapshot | Stateless is simpler; N<100 questions realistic |
| Rich tables | Custom ANSI color + padding | `rich.table.Table` | Already in deps; consistent with other CLI |
| Picker UI | Custom prompt loop | `questionary.select(choices).ask()` | Already in deps; same as `clawteam learn` |
| Token cost math | Custom pricing tiers | Hardcoded per-model USD/M-token rates in `cost/pricing.py` | Anthropic pricing rarely changes; table is readable |
| Async semaphores | Thread lock with counters | `asyncio.Semaphore(n)` | Stdlib; fair FIFO; cancellation-safe |

**Key insight:** The only NEW runtime is `watchdog` as an optional extra. Everything else composes existing deps + stdlib.

---

## Runtime State Inventory

This phase adds new code and new events; no rename / refactor / migration.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `SprintState.queue_status` field added (additive, default `""`); existing state.json files load cleanly via pydantic extra=ignore path | None — additive field with default |
| Live service config | `gstack.toml [conductor]`, `[attention]`, `[cost]` sub-blocks (new) | Add to TemplateDef as optional sub-blocks — existing templates unchanged |
| OS-registered state | None | None — no OS registrations |
| Secrets/env vars | None new | None |
| Build artifacts / installed packages | Optional `watchdog` — user runs `pip install 'clawteam[attend]'` | None — user opt-in |

---

## Common Pitfalls

### Pitfall 1: Semaphore starvation under FIFO (D-01)
**What goes wrong:** Sprint #11 waits forever if sprints 1-10 never complete (e.g., all blocked on human answers).
**Why it happens:** asyncio.Semaphore is fair FIFO but doesn't preempt.
**How to avoid:** 60s grace timeout on acquire → fall back to `queue_status="queued_capacity"` + durable state.json write. `clawteam sprint list --team <name>` surfaces queued sprints. User can manually prioritize.
**Warning signs:** Sprints stuck in `queued_capacity` > 1h; surface in `clawteam attend --summary`.

### Pitfall 2: Rate-limit false-saturation from one noisy minute
**What goes wrong:** Short network blip → 3+ 429s in 60s → all new sprints queued indefinitely.
**Why it happens:** Single-minute bucket too tight.
**How to avoid:** Expire 429 records older than 60s. `is_saturated()` returns False once window clears. Re-check on each `start_sprint`.
**Warning signs:** `RateLimitSaturated` event fires frequently; sprints queue and dequeue within minutes.

### Pitfall 3: AttentionQueue frontmatter drift
**What goes wrong:** Agent writes question.md with `urgency: "high"` (string) instead of YAML-numeric. Priority formula breaks.
**Why it happens:** Schema drift between question writer and reader.
**How to avoid:** Parse via pydantic model; unknown urgency defaults to `normal` (= 1); log warning once per question. Existing `parse_frontmatter` from `clawteam.team.envelope` handles YAML properly.
**Warning signs:** Questions with `urgency=1` + title mentioning "critical"; user complains "my critical got lost."

### Pitfall 4: Cost tracker memory growth
**What goes wrong:** 10-sprint run × 1000 tool calls = 10K in-memory events.
**Why it happens:** Tracker keeps raw event list for detailed rollup.
**How to avoid:** Track aggregates per (team, sprint, agent) — NOT raw events. Event handler aggregates at emit time; memory is O(agents × sprints) not O(events).
**Warning signs:** `clawteam team show` latency > 200ms; RSS growth over steady-state.

### Pitfall 5: Fallback ladder unreliability
**What goes wrong:** User sets `fallback_at_percent = 80` but budget alarm fires late because cost events arrive out-of-order across sprints.
**Why it happens:** Events are in-process sync emission; if a sprint uses asyncio.run in a subprocess, events don't reach the tracker.
**How to avoid:** All agent spawns go through `invoke_native_cli` which runs in-process (no subprocess isolation of events). Document: "Phase 7 cost tracker covers in-process sprints only; cross-process aggregation deferred to v2."
**Warning signs:** `current_spend_usd()` returns lower than real Anthropic dashboard; alarms fire late.

### Pitfall 6: Zombie worktree GC deletes active work
**What goes wrong:** User leaves a worktree untouched for 31 days but resumes on day 32. GC already wiped it.
**Why it happens:** mtime-only age check.
**How to avoid:** Also check if the worktree's branch has an active sprint in SprintState (sprint.workspace_branch). If yes, skip GC regardless of age. User-visible banner: "1 zombie worktree found (age > 30 days) — run `clawteam doctor --gc` to delete."
**Warning signs:** User reports "my worktree vanished."

### Pitfall 7: `--auto-accept-reversible` blast radius
**What goes wrong:** A `reversibility: easy` question actually has serious impact (e.g., renaming an API endpoint). Auto-accept fires; user notices 15 min later.
**Why it happens:** Reversibility tag is agent-assigned; trust-boundary issue.
**How to avoid:** 15-min TTL + preview phase lists every question that would auto-accept + requires explicit Ctrl-Y confirmation (not Enter). Log every auto-accept to `~/.clawteam/audit.log`.
**Warning signs:** User reports "auto-accepted something I didn't want." Mitigate via audit log + explicit preview.

---

## Code Examples

### Example 1: SprintState.queue_status additive field
```python
# clawteam/sprint/state.py — EDIT
class SprintState(BaseModel):
    # ... existing fields ...
    queue_status: str = Field(
        default="",
        description=(
            "Phase 7 D-01: reason sprint is in queued state. Empty string = "
            "active / running. Values: 'queued_capacity' (over max_concurrent_sprints), "
            "'rate_limit_saturated' (consumed by conductor's rate-limit monitor "
            "at start_sprint). Clears to '' when conductor promotes sprint to active."
        ),
    )
```

### Example 2: SprintConductor config block
```python
# clawteam/sprint/config.py (NEW)
from pydantic import BaseModel, Field

class ConductorConfig(BaseModel):
    max_concurrent_sprints: int = Field(default=10, ge=1)
    max_tasks_per_agent: int = Field(default=1, ge=1)
    max_active_agents: int = Field(default=6, ge=1)
    acquire_timeout_seconds: float = Field(default=60.0, gt=0)
```

### Example 3: Priority formula (D-05)
```python
# clawteam/attention/queue.py — priority computation
def compute_priority(
    urgency: int,
    blocking: bool,
    age_hours: float,
    tags: tuple[str, ...],
    config: AttentionConfig,
) -> float:
    score = urgency * config.urgency_weight
    if blocking:
        score += config.blocking_weight
    score += age_hours  # raw hours — caller normalizes if needed
    for tag in tags:
        score += config.tag_weights.get(tag, 0)
    return float(score)
```

### Example 4: Digest grouping (D-07)
```python
# clawteam/attention/digest.py
def bucket_age(age_hours: float) -> str:
    if age_hours < 1: return "<1h"
    if age_hours < 2: return "1-2h"
    if age_hours < 8: return "2-8h"
    return ">8h"

def build_digest(items: list[AttentionItem]) -> list[dict]:
    clusters: dict[tuple, list[AttentionItem]] = {}
    for item in items:
        cluster_key = item.tags[0] if item.tags else "untagged"
        key = (item.sprint_id, cluster_key, bucket_age(item.age_hours))
        clusters.setdefault(key, []).append(item)
    return [
        {
            "sprint_id": k[0],
            "tag": k[1],
            "age_bucket": k[2],
            "count": len(v),
            "highest_priority": max(i.priority_score for i in v),
            "representative_title": v[0].title,
        }
        for k, v in sorted(
            clusters.items(),
            key=lambda kv: -max(i.priority_score for i in kv[1]),
        )
    ]
```

### Example 5: `clawteam attend` CLI skeleton
```python
# clawteam/cli/commands.py — append
attend_app = typer.Typer(help="Cross-sprint attention queue (Phase 7)")
app.add_typer(attend_app, name="attend")

@attend_app.callback(invoke_without_command=True)
def attend_root(
    ctx: typer.Context,
    summary: bool = typer.Option(False, "--summary", help="Digest view"),
    auto_accept_reversible: bool = typer.Option(False, "--auto-accept-reversible"),
    top_n: int = typer.Option(10, "--top", "-n"),
):
    if ctx.invoked_subcommand is not None:
        return
    from clawteam.attention.queue import AttentionQueue
    queue = AttentionQueue.for_current_user()
    items = queue.snapshot()[:top_n]
    if summary:
        _render_digest(items)
    elif auto_accept_reversible:
        _preview_and_auto_accept(items)
    else:
        _render_table_and_pick(items)
```

### Example 6: CostRollup schema
```python
# clawteam/cost/rollup.py (NEW)
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class CostRollup:
    team: str
    sprint_id: str | None  # None = team-level
    agent: str | None
    tokens_opus: int
    tokens_sonnet: int
    tokens_haiku: int
    cost_usd: float
    cache_hit_rate: float
    period_start: datetime
    period_end: datetime
```

### Example 7: New event dataclasses (Wave 0)
```python
# clawteam/events/types.py — APPEND before the register_event_type block
@dataclass
class ToolCallCompleted(HarnessEvent):
    """Phase 7 D-09: agent invoked a tool and it finished."""
    agent: str = ""
    tool_name: str = ""
    sprint_id: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    model: str = ""
    cost_usd: float = 0.0
    duration_ms: float = 0.0
    model_fallback_applied: bool = False

@dataclass
class ClaudeApiResponse(HarnessEvent):
    """Phase 7 D-12: raw Claude API response metadata for cache tracking."""
    agent: str = ""
    model: str = ""
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

@dataclass
class BudgetAlarmReached(HarnessEvent):
    """Phase 7 D-10: current_spend / budget_usd crossed a threshold."""
    percent: float = 0.0
    spent_usd: float = 0.0
    budget_usd: float = 0.0

@dataclass
class RateLimitSaturated(HarnessEvent):
    """Phase 7 D-13: 429 window exceeded threshold; new sprints queued."""
    recent_429_count: int = 0
    threshold: int = 3
    window_seconds: int = 60

@dataclass
class ZombieWorktreeGced(HarnessEvent):
    """Phase 7 ROADMAP SC #10: dead worktree cleaned up."""
    path: str = ""
    age_days: int = 0
    freed_bytes: int = 0

@dataclass
class DormancyTransition(HarnessEvent):
    """Phase 7 QUALITY-04: agent transitioned between active and dormant."""
    agent: str = ""
    role: str = ""
    from_state: str = ""  # "dormant" | "active"
    to_state: str = ""
```

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | asyncio.Semaphore, native TOML in 3.11+ | ✓ | 3.10+ pinned | — |
| pydantic >=2 | All schemas | ✓ | Existing hard dep | — |
| typer >=0.12 | `clawteam attend` subcommand | ✓ | Existing hard dep | — |
| rich >=13 | Tables | ✓ | Existing hard dep | — |
| questionary >=2.0.1 | Picker UX | ✓ | Existing hard dep | — |
| watchdog >=3,<4 | FS auto-refresh | ✗ (optional) | — | 2-second polling loop |

**Missing dependencies with no fallback:** None — phase is code-only.
**Missing dependencies with fallback:** `watchdog` via `clawteam[attend]` optional extra.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Unlimited concurrent sprints | `asyncio.Semaphore(max_concurrent_sprints)` | Phase 7 D-01 | Laptops no longer melt at 10+ sprints |
| Single-sprint attention (questions in one dir) | Cross-sprint `AttentionQueue` | Phase 7 D-04 | 10-sprint workloads tractable |
| No cost visibility (placeholder in team show) | Event-driven cost tracker + dashboard panel | Phase 7 D-09 | Budget alarms at 50/80/100% |
| Hard-fail at rate-limit | Rate-limit-aware scheduling (queue instead of error) | Phase 7 D-13 | Seamless pause across TPM windows |

**Deprecated/outdated:**
- `clawteam team show cost rollup: pending_phase_7` placeholder (lines 1823-1828 in commands.py) — replaced by Phase 7 dashboard.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest >=9.0.0,<10.0.0` (existing, dev extra) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest tests/integration/test_phase7_ten_sprint_load.py tests/attention/ tests/cost/ tests/rate_limit/ -q` |
| Full suite command | `pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-06 | 10 concurrent sprints, no races | integration | `pytest tests/integration/test_phase7_ten_sprint_load.py::test_ten_concurrent_sprints -x` | ❌ Wave 6 |
| INT-03 | Priority ranking correctness | unit | `pytest tests/attention/test_queue_ranking.py -x` | ❌ Wave 2 / Wave 6 |
| INT-04 | `clawteam attend` CLI opens editor | integration | `pytest tests/attention/test_attend_cli.py -x` | ❌ Wave 3 |
| INT-05 | Watchdog w/ & w/out | integration | `pytest tests/attention/test_watcher.py -x` | ❌ Wave 2 |
| QUALITY-04 | Active-agent slot pool cap | integration | `pytest tests/integration/test_phase7_ten_sprint_load.py::test_active_agent_cap -x` | ❌ Wave 6 |
| QUALITY-05 | Digest view groups questions | unit | `pytest tests/attention/test_digest.py -x` | ❌ Wave 2 |
| QUALITY-12 | Cost rollup + alarms + fallback | unit | `pytest tests/cost/ -x` | ❌ Wave 4 / Wave 6 |
| UX-06 | Attend surfaces top-N | unit+integration | `pytest tests/attention/test_attend_cli.py::test_top_n -x` | ❌ Wave 3 |

### Sampling Rate
- **Per task commit:** `pytest tests/<modified-module>/ -x -q`
- **Per wave merge:** `pytest tests/attention/ tests/cost/ tests/rate_limit/ tests/integration/test_phase7_ten_sprint_load.py -q`
- **Phase gate:** Full suite green (`pytest tests/ -q`).

### Wave 0 Gaps
- [ ] `tests/attention/` — new directory; needs `conftest.py` and `__init__.py` (Wave 2)
- [ ] `tests/cost/` — new directory; needs same (Wave 4)
- [ ] `tests/rate_limit/` — new directory (Wave 1)
- [ ] `tests/events/test_phase7_events.py` — mirror `test_phase6_events.py` shape (Wave 0 / Plan 07-01)
- [ ] `tests/integration/test_phase7_ten_sprint_load.py` — Wave 6

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | N/A — local CLI only |
| V3 Session Management | no | N/A |
| V4 Access Control | yes | team-scoped reads (AttentionQueue) — path-traversal rejected via existing `ensure_within_root` |
| V5 Input Validation | yes | pydantic on config blocks + frontmatter parsing via `parse_frontmatter` |
| V6 Cryptography | no | N/A |
| V8 Data Protection | yes | no token values logged in cost events (use counts + pre-computed USD) |
| V11 Business Logic | yes | Fallback ladder avoids hard-fail; `--auto-accept-reversible` requires explicit confirm |

### Known Threat Patterns for Phase 7 stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious symlinks inside questions/ or answers/ | Tampering | Reuse existing `ensure_within_root` / `resolve().relative_to(data_dir)` check already in InteractionGate |
| Cost-event injection (spoofed BudgetAlarmReached) | Spoofing | EventBus is in-process only; no external subscribers |
| `--auto-accept-reversible` misuse (agent-flagged `reversibility: easy` on a high-impact question) | Tampering | 15-min TTL preview + explicit confirm + audit log |
| Watchdog observer path traversal | Tampering | Observer scoped to `get_data_dir()/teams/` — symlinks outside rejected by walker |
| Denial-of-Service via question-flood (1000s of questions writing lag) | DoS | Per-team cap: attend snapshot limits to 200 items; beyond that, `--summary` only |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `tool_call_completed` event is NOT yet defined | Stack §Events + D-09 | Phase 7 Wave 0 MUST add it. Risk: Wave 0 misses this and Wave 4 tracker has nothing to subscribe to. [VERIFIED via grep — no `ToolCallCompleted` class exists] |
| A2 | `SprintConductor.start_sprint` is currently sync | Pattern 1 | Phase 7 adds `start_sprint_async` wrapper; keeps sync path BC. [VERIFIED via read of conductor.py:284-309] |
| A3 | `watchdog` 3.x is current on PyPI with no 4.x | Optional Extra | Wave 0 plan-prep must verify with `pip index versions watchdog`. [ASSUMED from training data] |
| A4 | `SprintState` supports additive field via pydantic BaseModel (no `extra="ignore"` config — pydantic 2 ignores unknown by default on model_validate? actually strict default) | Runtime State Inventory | Wave 0 adds with a default; existing state.json files load cleanly — verified via load path. [ASSUMED — must verify] |
| A5 | Anthropic per-model pricing rarely changes | Cost pricing table | Phase 7 ships a hardcoded table (opus=$15/M-in, $75/M-out; sonnet=$3/$15; haiku=$0.25/$1.25 — current as of 2026-04 [ASSUMED]). Risk: pricing changes mid-life; keep as `cost/pricing.py` for cheap updates |
| A6 | `NativeCliAdapter` accepts a `model` parameter or can accept one additively (A5 from CONTEXT) | Pattern 4 | Wave 0 plan-prep grep. [ASSUMED per CONTEXT D-11 — implementation detail verified at plan-prep] |
| A7 | `questionary` + `rich` available (CONTEXT A6) | Stack | [VERIFIED via pyproject.toml] |
| A8 | `clawteam doctor` already detects watchdog (CONTEXT A3) | Stack | [VERIFIED — line 40 of clawteam/cli/commands.py: `("watchdog", "python-pkg", "watchdog")`] |

---

## Open Questions

1. **Should cost events include rate-limit backoff time?**
   - What we know: RateLimitMonitor tracks 429s for sprint-start scheduling.
   - What's unclear: Whether cost dashboard should surface "X seconds waiting for rate-limit" as a first-class metric.
   - Recommendation: Defer to v1.1. Wave 4 tracks cost; rate-limit wait time is logged via `RateLimitSaturated` event count but not summed into rollup.

2. **Cross-process event propagation for out-of-band agent spawns?**
   - What we know: EventBus is in-process sync.
   - What's unclear: Phase 5 `/codex` runs as subprocess — does it emit `ToolCallCompleted` correctly?
   - Recommendation: Wave 4 Plan task verifies via subprocess test. If broken, invoker parses codex stdout token counts and emits the event from the PARENT process after wait().

3. **Disk-budget alarm shape (ROADMAP SC #10 5 GB soft, 10 GB hard)?**
   - What we know: CONTEXT mentions it but no D-tag locks a schema.
   - What's unclear: Whether soft/hard thresholds are emitted events or just log warnings.
   - Recommendation: Match the cost alarm pattern — emit `DiskBudgetAlarmReached` (new event) on each threshold crossing; user-facing via `clawteam doctor` + `clawteam team show` disk row.

---

## Project Constraints (no CLAUDE.md — use PROJECT.md)

- Python 3.10+; no new required runtime deps.
- Persistence under `get_data_dir()` (= `~/.clawteam/` default).
- QUALITY-14: every existing template still spawns after Phase 7 changes. Phase 7 adds no new required deps; all concurrency caps default to 10/1/6 (permissive).
- QUALITY-15: env deny-filter — no secret-shaped values in logs/events. Cost events never carry API-key material; only token counts + model name.
- Pitfall 14: register_event_type calls are idempotent; re-import of events/types.py doesn't double-register.

---

## Sources

### Primary (HIGH confidence)
- `clawteam/sprint/conductor.py` — SprintConductor with sync start_sprint [VERIFIED read]
- `clawteam/sprint/state.py` — SprintState pydantic with Literal status [VERIFIED read]
- `clawteam/events/bus.py` + `clawteam/events/types.py` — EventBus + register_event_type pattern [VERIFIED read]
- `clawteam/harness/interaction_gate.py` — questions/answers dir layout [VERIFIED read]
- `clawteam/spawn/invoke.py` — NativeCliAdapter wrapper (Phase 5) [VERIFIED read]
- `clawteam/cli/commands.py` — typer subcommand pattern, existing cost_app, team_show placeholder [VERIFIED read of relevant sections]
- `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md` — D-01 through D-16 [VERIFIED read]
- `.planning/REQUIREMENTS.md` — 8 phase requirements [VERIFIED read]
- `pyproject.toml` — optional-extras pattern, existing deps [VERIFIED read]

### Secondary (MEDIUM confidence)
- `.planning/phases/06-browser-skills-design-pipeline-team-memory/06-01-PLAN.md` — plan format precedent [VERIFIED read]
- `.planning/ROADMAP.md §Phase 7` — 10 success criteria [VERIFIED read]

### Tertiary (LOW confidence)
- Anthropic per-model pricing table for `cost/pricing.py` — [ASSUMED from training; verify at plan-prep]
- watchdog 3.x being current — [ASSUMED from training]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all substrate exists and is well-documented in Phases 0-6.
- Architecture: HIGH — stateless read-side + event-driven substrate are both proven Phase 2/4 patterns.
- Pitfalls: MEDIUM — parallel-sprint races are the hardest to test; integration test (Plan 07-09) exercises them.

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (stable substrate; minor risk from cost-pricing drift)

---

*Phase: 07-parallel-sprints-attentionqueue-ux-cost-controls*
*Research date: 2026-04-22 (researcher+planner combined run)*
*Next: 9 PLAN.md files in same directory; execution can begin at Plan 07-01.*
