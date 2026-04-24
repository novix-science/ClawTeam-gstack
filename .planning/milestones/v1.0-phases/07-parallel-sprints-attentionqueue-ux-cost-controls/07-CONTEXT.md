---
phase: 7
phase_name: Parallel Sprints, AttentionQueue UX & Cost Controls
phase_slug: parallel-sprints-attentionqueue-ux-cost-controls
gathered: 2026-04-22
status: Ready for planning
source: /gsd-discuss-phase --auto (autonomous)
---

# Phase 7: Parallel Sprints, AttentionQueue UX & Cost Controls — Context

<domain>
## Phase Boundary

Unlock the parallel-sprints force multiplier by landing the concurrency caps + attention UX + cost observability that keep 10-sprint runs from melting laptops or burning budgets. Three deliverable clusters:

### Cluster A — Concurrency + dormancy
1. **`SprintConductor` max_concurrent_sprints semaphore** — `asyncio.Semaphore(max_concurrent_sprints)` (default 10, configurable via `gstack.toml [conductor] max_concurrent_sprints`). Sprints beyond the cap enter `queued` state; auto-advance when capacity frees. Per-agent `asyncio.Semaphore(max_tasks_per_agent)` (default 1) serializes per-agent dispatch.
2. **Active-agent slot pool** — `asyncio.Semaphore(max_active_agents)` (default 6) caps concurrent running agents. Idle agents sleep-poll (no Claude keepalive burn). A Think-phase sprint with only pm + ceo active doesn't wake engineer/shipper/sre. QUALITY-04 floor: observable via `clawteam team show` active-agent count.
3. **Rate-limit-aware scheduling** — When Anthropic TPM saturates, new phase starts queue behind in-flight work instead of erroring. Pause/resume across rate-limit windows seamless. Detected via a tiny `RateLimitMonitor` that buckets Claude API responses (429 counts, X-RateLimit-Remaining header if present). Configurable retry backoff.
4. **Zombie worktree auto-GC** — Dead worktrees older than 30 days cleaned up at `clawteam doctor --gc` or sprint-spawn-time. Disk-budget alarm per team (default 5 GB soft, 10 GB hard) surfaces in dashboard.

### Cluster B — AttentionQueue + `clawteam attend`
5. **`AttentionQueue`** cross-sprint priority-sorted queue at `clawteam/attention/queue.py`. Priority formula: `URGENCY + BLOCKING + AGE_BOOST + EXPLICIT_TAG` (additive, configurable weights via `gstack.toml [attention]`). Reads question files across all teams' sprints; ranks; emits ordered list.
6. **`clawteam attend`** CLI — prints top-N pending questions; user picks → opens `$EDITOR` on the chosen question.md; on save, the corresponding InteractionGate unblocks. Default N = 10.
7. **`clawteam attend --summary`** digest view — rolls related questions into single decisions: "4 sprints stalled >2h, 1 CRITICAL, 2 reversible auto-accept candidates". Groups by sprint + age + tag cluster. QUALITY-05 floor.
8. **`clawteam attend --auto-accept-reversible`** — applies default-accept-with-TTL to questions flagged `reversibility: easy`. User previews what would auto-accept before confirming.
9. **`watchdog`-based auto-refresh** — With optional `watchdog` pkg installed, queue auto-refreshes on FS events when answer.md saved. Without watchdog → 2-second polling fallback. No hard dep.

### Cluster C — Cost dashboard
10. **`clawteam team show` cost panel** — per-agent token usage, per-sprint cost rollup with Opus/Sonnet/Haiku breakdown, cache hit rate, 50/80/100%-of-budget alarms. Budget configurable per team via `gstack.toml [cost] budget_usd`.
11. **Model fallback ladder** — when 80% budget reached, agent invocations prefer cached prompts + downgrade Opus → Sonnet → Haiku with flagged note in envelope's `model_fallback_applied: true`. Configurable via `[cost] fallback_at_percent = 80`.
12. **Prompt-cache observability** — Role prompts cached per session, team memory core per team, per-sprint artifacts per sprint. Cache hit rate > 50% on steady-state 10-sprint run (measured in load test). Surfaced as `cache_hit_rate: <float>` in dashboard.

**Scope boundary (explicit exclusions):**
- Multi-team Conductor UI / board panels → v2.
- Helper-spawning within engineer (sub-worktrees) → v1.x per FEATURES.md P2.
- Provider-specific deploy hooks replacing `gh pr checks --watch` → v1.1.
- ML-based attention priority (learned-from-user-behavior ranking) → v2.
- Cross-team cost pooling → v2.

**Delete invariant:** Phase 7 adds three top-level packages: `clawteam/attention/` (AttentionQueue + attend CLI), `clawteam/cost/` (dashboard + model fallback), `clawteam/rate_limit/` (monitor). All generic substrate. GstackSprintPlugin extends (not replaces) with semaphore caps + cost-event subscriptions. Removing the three packages + their plugin wiring lines leaves existing templates running unchanged.

</domain>

<decisions>
## Implementation Decisions

### Concurrency primitives (Area 1)

- **D-01:** **`SprintConductor.max_concurrent_sprints` via `asyncio.Semaphore`** initialized at conductor construction from `gstack.toml [conductor]` config (default 10). Sprints enter via `await conductor.start_sprint(sprint)` which acquires semaphore; release on sprint completion (reflect-phase exit) OR `/sprint pause`. Sprints failing to acquire within a grace period (default 60s timeout) enter `queued` state persisted to `SprintState.queue_status`.
  **Why:** Explicit semaphore > ad-hoc counter; asyncio-native; fair FIFO queueing; pause-resume compatible.

- **D-02:** **Per-agent semaphore at `asyncio.Semaphore(max_tasks_per_agent)` (default 1)** enforced at `SprintConductor.dispatch_turn(agent_role, ...)`. Prevents the same agent being invoked twice concurrently across sibling sprints (accidentally "concurrent pm" on same team). Per-role, per-team scoped.
  **Why:** Simple, deterministic; prevents the most common parallel-sprint footgun.

- **D-03:** **Active-agent slot pool at `asyncio.Semaphore(max_active_agents)` (default 6) in `SprintConductor`.** Agents not holding a slot are in `state=dormant`. Waking an agent acquires a slot; completing a turn releases. Observable via `conductor.active_agents() -> list[AgentRef]` and surfaced in `clawteam team show`.
  **Why:** QUALITY-04 floor. 6 is Claude's recommended default for 8 GB laptops per research/STACK.md.

### AttentionQueue (Area 2)

- **D-04:** **`AttentionQueue` is a pure-read-side computation over the filesystem.** No persisted priority state. On each `clawteam attend` invocation: glob `~/.clawteam/teams/*/sprints/*/questions/*.md` - skip those with sibling `answers/<N>.md`; compute priority per formula; return sorted list. Decision-free vs persistent queue because priority is a function of file metadata (mtime, frontmatter tags, etc.).
  **Why:** Stateless > stateful. No queue-consistency protocol needed; filesystem IS the ledger.

- **D-05:** **Priority formula:** `score = URGENCY × 10 + BLOCKING × 5 + age_hours + explicit_tag_weight`. URGENCY from frontmatter `urgency: {critical=3, high=2, normal=1, low=0}`; BLOCKING from `blocking: true|false`; age_hours = now - mtime of question.md; explicit_tag_weight from `gstack.toml [attention.tag_weights]` dict. Weights configurable via `[attention]` sub-block.
  **Why:** Additive > multiplicative (avoids weight tuning nightmares); integer bucketing visible in `--explain` mode; tag weights let teams bias on domain tags.

- **D-06:** **`watchdog` optional-extra** at `pyproject.toml [project.optional-dependencies] attend = ["watchdog>=3,<4"]`. `clawteam/attention/watcher.py::watchdog_available()` detects. With watchdog: `clawteam attend` spawns observer on all sprint dirs, updates queue on `FileModifiedEvent`. Without: 2-second polling loop.
  **Why:** INT-05 requirement; optional-extra pattern matches browser[] from Phase 6.

- **D-07:** **`--summary` digest groups questions by `(sprint_id, tag_cluster, age_bucket)`** where tag_cluster is the first shared tag across questions and age_bucket is one of `{<1h, 1-2h, >2h, >8h}`. Digest output shows cluster count + representative title + single "open all" or "answer first" action. Plain-text; no TUI.
  **Why:** QUALITY-05 floor; simple grouping reveals "my 4 stalled-sprints all need same designer decision" patterns.

- **D-08:** **`--auto-accept-reversible` applies to questions with `reversibility: easy` frontmatter ONLY.** Preview phase lists what would auto-accept + auto-accept TTL (default 15 min — enough time for user to Ctrl-C if they disagree). On confirm, writes `answer.md` with `auto_accepted: true` frontmatter + placeholder body "Auto-accepted per --auto-accept-reversible. Default option: `<first option>`."
  **Why:** INT-03 sub-requirement; `reversibility: easy` is the existing question frontmatter field from Phase 2 question schema.

### Cost dashboard + model fallback (Area 3)

- **D-09:** **`clawteam/cost/` new package** — generic substrate. `tracker.py` listens on EventBus `tool_call_completed` event (already emitted by Phase 5 `/codex`), aggregates per-team per-sprint per-agent token counts. `dashboard.py` computes rollups for `clawteam team show` extension. `fallback.py` applies model-fallback-ladder policy to outgoing Claude API calls.
  **Why:** Separation: tracker = accounting; dashboard = rendering; fallback = policy. Test-isolable.

- **D-10:** **Budget config:** `gstack.toml [cost]` block with `budget_usd: float` (default $100/month per team), `fallback_at_percent: float` (default 80), `alarm_percent: list[float]` (default [50, 80, 100]). When tracker.current_spend crosses any alarm threshold, emits `budget_alarm_reached` event.
  **Why:** Explicit thresholds > silent drift. Alarms emitted not enforced — lets teams decide policy.

- **D-11:** **Model fallback ladder at `clawteam/cost/fallback.py::apply_fallback(model_pref, budget_state) -> model`.** If `budget_state.spend_percent < fallback_at_percent` → return `model_pref`. Else → downgrade ladder: opus→sonnet, sonnet→haiku, haiku→haiku. Called by `NativeCliAdapter` / spawn adapters where Claude API model is specified. The agent's envelope includes `model_fallback_applied: true` when downgrade occurred.
  **Why:** Graceful degradation > hard-fail at budget limit. Envelope metadata lets reviewers see "this review used Sonnet not Opus because budget".

- **D-12:** **Cache hit rate tracking:** `clawteam/cost/cache_tracker.py` listens on `claude_api_response` events for `cache_read_tokens` + `cache_creation_tokens`. Computes `cache_hit_rate = cache_read / (cache_read + cache_creation)` per team. Displayed in dashboard. Above-50% threshold considered healthy.
  **Why:** Anthropic prompt-caching API exposes these token counts directly; tracking is arithmetic, not ML.

### Rate limiting (Area 4)

- **D-13:** **`clawteam/rate_limit/monitor.py::RateLimitMonitor`** — records 429 responses from Claude API; buckets by minute; when `recent_429_count > threshold` (default 3/min) signals saturation. Sprint conductor's `start_sprint()` consults `monitor.is_saturated()` before acquiring the concurrent-sprint semaphore; if saturated, queues the sprint with `queue_reason: rate_limit_saturated` frontmatter.
  **Why:** 429-count-based detection is universal; doesn't require reading Anthropic-specific headers.

### Verification stringency (Area 5)

- **D-14:** **Integration test for 10 concurrent sprints** (`tests/integration/test_phase7_ten_sprint_load.py`): spawn 10 sprints on one team under 5-minute duration cap + 4 GB RAM budget. Asserts (a) all 10 reach reflect-phase completion (b) no race conditions on TaskStore/memory (c) active-agent count never exceeds 6 cap (d) avg cost per sprint < $10 (using mocked Claude API returning fixed token counts).
  **Why:** CORE-06 floor. Mocked Claude API keeps test deterministic + fast.

- **D-15:** **AttentionQueue ranking test** with 30 fixture questions across 5 sprints + 3 teams. Asserts ordering matches priority formula exactly. Adversarial fixture: question with `urgency: critical` + `age: 30s` outranks `urgency: normal` + `age: 8h` (critical tag's 10× weight beats 8-hour age by 2-point margin).
  **Why:** Formula correctness is easy to miss; adversarial fixture prevents drift.

- **D-16:** **Cost dashboard test** with fixture event stream (100 tool_call_completed events across 5 agents). Asserts rollup correctness + 50/80/100 alarm firing + model fallback activation at 80%.
  **Why:** Arithmetic-only correctness — easy to verify, easy to regress.

### Claude's Discretion (planner picks; no need to ask user)

- Concrete rich/typer layout of `clawteam attend` CLI (column widths, color thresholds).
- Pydantic field names inside `AttentionItem`, `CostRollup`, `BudgetState`.
- Wave structure + plan count — planner decides from file dependencies (3 new top-level packages ≈ independent).
- EventBus dataclass names for `budget_alarm_reached`, `rate_limit_saturated`, `zombie_worktree_gced`.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/ROADMAP.md` §Phase 7 (lines 319-345) — phase goal, 10 success criteria, requirements CORE-06, INT-03..05, QUALITY-04/05/12, UX-06.
- `.planning/REQUIREMENTS.md` — above verbatim.
- `.planning/PROJECT.md` — Python 3.10+, no new required deps (watchdog optional), persistence under `get_data_dir()`.

### Phase 2 substrate Phase 7 reuses
- `clawteam/sprint/conductor.py::SprintConductor` — Phase 7 extends with semaphore caps + rate-limit consult.
- `clawteam/harness/interaction_gate.py` — AttentionQueue reads question.md / answer.md pairs from existing gate artifacts.
- `clawteam/events/bus.py` — Phase 7 emits 4 new event types (budget_alarm_reached, rate_limit_saturated, zombie_worktree_gced, dormancy_transition).

### Phase 5 + 6 precedent
- `clawteam/spawn/invoke.py` — Phase 7's cost fallback wraps this.
- `clawteam/cli/commands.py` — `clawteam team show` extends with cost panel; `clawteam attend` new subcommand group.
- `clawteam/memory/store.py` — memory event listeners for cost rollups (Phase 7 consumes memory_write_persisted).

### Research foundation
- `.planning/research/ARCHITECTURE.md` Pattern 2 (team-wide task queue + semaphore caps) + Pattern 3 (AttentionQueue priority scoring).
- `.planning/research/PITFALLS.md` Pitfalls 4 (resource blowup), 5 (attention fatigue), 12 (cost blowup), 16 (resume brittleness).
- `.planning/research/STACK.md` `questionary + rich` (for attend UX), `watchdog` optional.

</canonical_refs>

<code_context>
### Reusable Assets
- `clawteam/sprint/conductor.py` — extend with semaphore + rate-limit gates.
- `clawteam/cli/commands.py` — add `attend` subcommand + `team show` cost panel.
- `clawteam/events/bus.py` + `types.py` — add 4 event dataclasses.
- `clawteam/plugins/gstack_sprint_plugin.py` — subscribe cost tracker to events.
- `questionary` + `rich` — already-present deps for `attend` UX.

### New Top-Level Packages
- `clawteam/attention/` — queue.py, watcher.py, digest.py.
- `clawteam/cost/` — tracker.py, dashboard.py, fallback.py, cache_tracker.py.
- `clawteam/rate_limit/` — monitor.py.

### Established Patterns (from Phases 2-6)
- Semaphore-based concurrency (Phase 2 forced_progress_gate precedent).
- Optional-extras pattern (Phase 6 `browser`; Phase 7 adds `attend`).
- EventBus dataclass emission (Phase 4 MidReviewThrash precedent).
- Typer subcommand group for CLI (Phase 5 sprint approve, Phase 6 learn precedent).
- Stateless read-side over filesystem (Phase 2 questions/answers gate precedent).
- `gstack.toml` additive sub-blocks pattern (Phase 5-6 established).

### Integration Points
- `SprintConductor.start_sprint` acquires semaphore; releases on reflect-phase exit.
- `SprintConductor.dispatch_turn` acquires per-agent + active-agent slot semaphores.
- `NativeCliAdapter` / `invoke_native_cli` consults `cost.fallback.apply_fallback` when model specified.
- `clawteam team show` reads `cost.dashboard.render()`.
- `clawteam attend` reads `attention.queue.AttentionQueue.snapshot()`.

</code_context>

<specifics>
- **AttentionItem schema:**
  ```python
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
    reversibility: str  # easy | medium | hard
    priority_score: float
  ```

- **CostRollup schema:**
  ```python
  @dataclass(frozen=True)
  class CostRollup:
    team: str
    sprint_id: str | None  # None = team-level rollup
    agent: str | None
    tokens_opus: int
    tokens_sonnet: int
    tokens_haiku: int
    cost_usd: float
    cache_hit_rate: float
    period_start: datetime
    period_end: datetime
  ```

- **`gstack.toml` additions:**
  ```toml
  [conductor]
  max_concurrent_sprints = 10
  max_tasks_per_agent = 1
  max_active_agents = 6

  [attention]
  urgency_weight = 10
  blocking_weight = 5
  tag_weights = { design = 2, security = 3, cost = 1 }

  [cost]
  budget_usd = 100.0
  fallback_at_percent = 80
  alarm_percent = [50, 80, 100]
  ```

</specifics>

<deferred>
### To v1.1
- Multi-team Conductor UI / board panels.
- Helper-spawning within engineer (sub-worktrees).
- ML-based attention priority (learned from user behavior).
- Cross-team cost pooling + chargeback dashboards.
- Provider-specific deploy hooks.

</deferred>

<plan_prep_verifications>
| ID | Verification | Action if fails |
|----|--------------|-----------------|
| A1 | `clawteam/sprint/conductor.py::SprintConductor.start_sprint` async-aware (has `async def` entry) | If sync, Phase 7 adds async wrapper layer. |
| A2 | EventBus `tool_call_completed` event is emitted by Phase 5 `/codex` + other tool skills | Phase 5 D-13; verify. |
| A3 | `clawteam doctor` detects `watchdog` optionally | Phase 0 D-04 promised; verify. |
| A4 | `SprintState.queue_status` field exists or can be additively added (extra="ignore") | Phase 4 D-23 confirmed extra="ignore"; verify no regression. |
| A5 | `NativeCliAdapter` currently accepts a `model` parameter or can be extended additively | Phase 5 D-03 shipped adapter; verify. |
| A6 | `questionary` + `rich` present in deps | STACK.md confirms; re-verify. |

</plan_prep_verifications>

---

*Phase: 07-parallel-sprints-attentionqueue-ux-cost-controls*
*Context gathered: 2026-04-22 via /gsd-discuss-phase --auto (autonomous)*
*Decisions: D-01 through D-16; plus 6 plan-prep verifications*
*Next: /gsd-plan-phase 7*
