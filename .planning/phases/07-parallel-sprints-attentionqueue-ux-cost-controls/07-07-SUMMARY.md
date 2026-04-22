---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 07
subsystem: dashboard-team-show
tags:
  - dashboard
  - team-show-extension
  - cost-panel
  - tdd
requires:
  - clawteam.cost.tracker.CostTracker (Plan 07-05)
  - clawteam.cost.tracker.CostTracker.rollup_by_agent / rollup_by_sprint /
    rollup_team (Plan 07-05)
  - clawteam.cost.cache_tracker.CacheTracker (Plan 07-06)
  - clawteam.cost.cache_tracker.HEALTHY_THRESHOLD (Plan 07-06)
  - clawteam.events.global_bus.get_event_bus (existing)
  - clawteam.sprint.conductor.SprintConductor.active_agents (Plan 07-02)
  - clawteam.templates.CostConfig (Plan 07-01)
provides:
  - clawteam.cost.dashboard.render_team pure function (14-key dict)
  - clawteam.cost.dashboard.render_text pure one-liner formatter
  - clawteam.cli.commands._team_show_cost_panel helper
  - `clawteam team show <team>` cost panel (replaces pending_phase_7
    placeholder; ships cost / cache / alarms / active-agents rows)
affects:
  - No downstream plans in Phase 7; 07-08 (zombie GC) and 07-09 (load
    test) are independent. Cluster closes QUALITY-12 dashboard-rendering
    half and UX-06 observable-dashboard half.
tech-stack:
  added: []
  patterns:
    - "Pure-function dashboard render layer over the event-driven tracker
      accounting layer (Plans 07-05 / 07-06) — test-isolable, no state,
      no event subscriptions inside dashboard.py"
    - "Best-effort CLI helper pattern: _team_show_cost_panel wraps the
      whole pipeline in try/except and returns a neutral
      status='unavailable' shape on any failure so the command never
      crashes cross-template"
    - "Dashboard dict uses snake_case for new keys (cost_usd, per_agent,
      active_agents) — sibling to camelCase Phase 3 JSON contract keys
      (name, members, activeSprint) that UX-07 consumers already parse;
      the ``costRollup`` envelope key stays camelCase for BC"
    - "CostConfig lookup is best-effort: team template load failure
      preserves the default (budget=100, alarm=[50,80,100]) instead of
      failing the whole dashboard"
key-files:
  created:
    - clawteam/cost/dashboard.py
    - tests/cost/test_dashboard.py
    - tests/test_team_show_cost_panel.py
  modified:
    - clawteam/cost/__init__.py (re-exports render_team, render_text)
    - clawteam/cli/commands.py (new _team_show_cost_panel helper + live
      costRollup wiring + new human-render branch for Cost: / Cost by
      Agent / Budget alarms / Active agents rows)
    - tests/test_cli_commands.py (Phase 3 placeholder assertions updated
      to match Plan 07-07 cost panel contract)
key-decisions:
  - "render_team reads tracker._fired_alarms internal set (not a public
    getter) — matches the plan's <action> skeleton and avoids growing
    the tracker's public surface. Sorted before emission so JSON and
    rich consumers get order-stable output."
  - "render_text drops the 'Cost - ' prefix from the string itself so
    callers that already print 'Cost: ' (team_show human renderer) don't
    produce 'Cost: Cost - $0.00 / ...'. The string now starts with
    '$<cost>' directly. Dashboard tests locked substring assertions, so
    this is a style adjustment that preserves test contracts."
  - "CostConfig lookup via load_template is wrapped in inner try/except:
    a broken TOML on a team's template should not hide the cost panel —
    defaults still ship. Outer try/except around the whole helper fires
    if events bus / team manager / sprint conductor substrate fails."
  - "Active agents fetched via a best-effort SprintConductor probe
    scoped to the team — when the conductor can't initialize (no sprint
    state on disk, broken substrate), the actives list is empty and the
    dashboard still renders. Matches the _team_show_active_sprint
    pattern from Plan 03-08."
  - "BC: Phase 3 UX-07 tests that locked the pending_phase_7 placeholder
    literal were updated to assert the new {ok, unavailable} status and
    the dashboard-dict keys. This is a Rule 1 (inverted-assertion BC
    update) deviation — the plan's explicit goal is to replace the
    placeholder, so the Phase 3 tests were locking the wrong contract
    going forward. No production regression."
patterns-established:
  - "Dashboard render layer contract: pure function over tracker +
    cache_tracker instances. Callers supply the instances; render_team
    returns a dict. No event subscriptions, no state, no side effects.
    Future Phase 7.x layers (v1.1 cross-team dashboards) can reuse the
    same render_team shape."
  - "CLI best-effort helper pattern: every clawteam team show sub-panel
    (active sprint, memory, cost) wraps its pipeline in try/except and
    returns a neutral placeholder dict on failure. Dashboard never
    crashes cross-template."
requirements:
  - QUALITY-12
  - UX-06
metrics:
  duration: "~5min"
  started: "2026-04-22T14:56:10Z"
  completed: "2026-04-22T15:01:31Z"
  tasks_completed: 2
  tests_added: 11 (7 dashboard + 4 team_show cost panel)
  tests_passing: 166 (scoped regression across cost/events/sprint/attention/rate_limit)
  files_created: 3
  files_modified: 3
---

# Phase 7 Plan 07: Dashboard team show cost panel Summary

**Wave 5 — replace the `costRollup: pending_phase_7` placeholder in
`clawteam team show <team>` with a live cost dashboard panel (per-agent
breakdown + budget bar + 50/80/100% alarms + cache hit rate +
active-agent count) driven by Plan 07-05 CostTracker + Plan 07-06
CacheTracker + Plan 07-02 SprintConductor.active_agents — closes
QUALITY-12 dashboard-rendering half and UX-06 observable-dashboard half.**

## What Was Built

**Task 1 — `clawteam/cost/dashboard.py` pure render functions (D-09).**
Two pure functions — no event subscriptions, no state:

- `render_team(team, tracker, cache_tracker=None, *, active_agents=None)`
  returns a 14-key dict suitable for `clawteam team show --json`:
  `team`, `status="ok"`, `cost_usd`, `budget_usd`, `spend_percent`,
  `per_agent`, `per_sprint`, `tokens_opus`, `tokens_sonnet`,
  `tokens_haiku`, `cache_hit_rate`, `cache_healthy`, `alarms_fired`
  (sorted ascending), `active_agents`, `active_agent_count`.
- `render_text(data)` returns a plain-text one-liner:
  `$<cost> / $<budget> (<pct>%) | cache hit: <X>% | active agents: <N>`
  with a no-budget variant when `budget_usd == 0`:
  `$<cost> (no budget) | cache hit: <X>% | active agents: <N>`.

`clawteam/cost/__init__.py` re-exports `render_team` and `render_text`.
**7/7 dashboard tests green.**

**Task 2 — `clawteam/cli/commands.py` team_show integration.**
New helper `_team_show_cost_panel(team)` above
`_team_show_phases_for_template`:

- Loads `CostConfig` from the team's template (defaults: budget=100,
  alarm=[50,80,100]).
- Wires fresh `CostTracker` + `CacheTracker` to the global EventBus.
- Best-effort fetch of `SprintConductor.active_agents()` for the team.
- Returns `render_team(team, tracker, cache_tracker,
  active_agents=...)`.
- Any failure returns a neutral `status='unavailable'` dict with all
  the same keys so JSON consumers never crash.

`team_show`'s `costRollup` key now calls the helper; the
`pending_phase_7` literal is removed entirely (acceptance grep
criterion). The `_human()` renderer now prints:

- `Cost: $<cost> / $<budget> (<pct>%) | cache hit: <X>% | active agents: <N>`
- A `Cost by Agent` rich Table (sorted desc by USD) when `per_agent`
  non-empty.
- A `Budget alarms fired: 50%, 80%, 100%` banner in green/yellow/red
  (picks the highest crossed threshold's color).
- `Active agents (<N>): <list>` when `active_agents` non-empty.
- Falls back to `Cost: [dim]unavailable[/dim]` when `status !=
  'ok'`.

**4/4 team_show cost-panel tests green;** 2 existing Phase 3 UX-07
tests updated to the new contract (Rule 1 deviation, inverted
assertions for placeholder replacement).

## Verification

Plan 07-07 scoped suite:

```
uv run python -m pytest tests/cost/test_dashboard.py
  tests/test_team_show_cost_panel.py -q
=> 11 passed
```

Plan 07-07 acceptance + full cost suite + CLI BC:

```
uv run python -m pytest tests/cost/ tests/test_team_show_cost_panel.py
  tests/test_cli_commands.py -q
=> 77 passed in 1.81s
```

Broader Phase 7 regression (cost + events + sprint + attention +
rate_limit):

```
uv run python -m pytest tests/cost/ tests/test_team_show_cost_panel.py
  tests/test_cli_commands.py tests/test_event_types_phase7.py
  tests/test_event_bus.py tests/sprint/ tests/attention/
  tests/rate_limit/ -q
=> 166 passed in 4.26s
```

Manual smoke (plan's verification step 2) — `clawteam team show
<any-team>`:

```
Team: smoke-team
  Created: 2026-04-22T15:00:53
                      Members (1)
(...)
Active sprint: none — run `clawteam sprint start`
Memory: N/A (non-gstack template)
Cost: $0.00 / $100.00 (0%) | cache hit: 0% | active agents: 0
```

The "Cost rollup: pending Phase 7 observability" placeholder line is
GONE — replaced by the live Cost: row.

## Acceptance Criteria

- [x] `grep -q "def render_team" clawteam/cost/dashboard.py` succeeds.
- [x] `pytest tests/cost/test_dashboard.py -q` reports 7 passed.
- [x] BC: `pytest tests/cost/ -q` all 49 green (42 previous + 7 new).
- [x] `grep -q "_team_show_cost_panel" clawteam/cli/commands.py`
      succeeds.
- [x] `grep -q "pending_phase_7" clawteam/cli/commands.py` returns NO
      matches (placeholder literal fully removed).
- [x] `pytest tests/test_team_show_cost_panel.py -q` reports 4 passed.
- [x] BC: `pytest tests/test_cli_commands.py -q` all 24 green
      (2 tests updated to new Plan 07-07 cost panel contract).

## Commits

Two tasks, strict TDD RED -> GREEN gates preserved on each:

**Task 1 — dashboard.render_team + render_text:**

- `1cea6a5` test(07-07): RED — 7 failing tests for dashboard.render_team
  + render_text (Task 1)
- `bc4839a` feat(07-07): GREEN — dashboard.render_team + render_text
  (Task 1)

**Task 2 — team_show cost panel integration:**

- `4c540c8` test(07-07): RED — failing test for team_show cost panel
  (Task 2)
- `7e693e8` feat(07-07): GREEN — team_show cost panel integration
  (Task 2)

**Polish:**

- `95baab2` style(07-07): drop redundant 'Cost - ' prefix from
  render_text output (cosmetic; prevents double-prefix when CLI human
  renderer already prints 'Cost: ').

## Deviations from Plan

**1 deviation — Rule 1 inverted BC assertions in
`tests/test_cli_commands.py`.**

Two Phase 3 (Plan 03-08) tests locked the `pending_phase_7` placeholder
literal + its triple of placeholder JSON fields (`perAgent: []`,
`totalTokens: None`, `totalUsd: None`). Plan 07-07's explicit mandate is
to replace the placeholder — the tests were locking the wrong contract
going forward. Updates:

- `test_team_show_gstack_dashboard_renders_11_roles_and_placeholders`:
  `assert "Phase 7" in result.output` -> `assert "Cost:" in result.output`
  (or the `[dim]unavailable[/dim]` fallback).
- `test_team_show_json_output_shape_matches_contract`: the four
  pending_phase_7 assertions replaced with `status in {ok,
  unavailable}`, `status != "pending_phase_7"`, plus dashboard-dict key
  checks (`cost_usd`, `per_agent`, `active_agents`).

**Found during:** Task 2 GREEN verification run.
**Issue:** Tests locked the placeholder Plan 07-07 removes.
**Fix:** Invert the assertions to match the new cost-panel contract.
**Files modified:** `tests/test_cli_commands.py`
**Commit:** `7e693e8` (same commit as the production change, keeps
test + code co-located).
**Rule:** Rule 1 — pre-existing test was locking a placeholder that the
current plan is chartered to replace. No production regression.

**Additive stylistic adjustment (not a deviation):**

- `render_text` now starts with `$<cost>` instead of `Cost - $<cost>` —
  the CLI human renderer already prints `Cost: ` before calling
  render_text, so the internal prefix was double-adding. Cosmetic only;
  test substring assertions (`25.00`, `100.00`, `active agents: 1`,
  `no budget`) all remain satisfied.

**Total production-code deviations:** 0.
**Total test-assertion deviations:** 2 (same commit as GREEN; inverted
assertions to match new contract).
**Impact on plan:** None — all plan acceptance criteria met.

## Issues Encountered

None — plan's `_make_team` fixture body used `TeamManager.create_team(name,
members=[])` which would have failed at runtime (the real signature
requires `leader_name` + `leader_id` positional args). The executor
spotted this at test-write time and used the canonical 3-arg form from
`tests/test_cli_commands.py::_spawn_gstack_team_for_show`.

## User Setup Required

None — no external service / credential / config file. The two new
public functions (`render_team` / `render_text`) are pure, and the new
`_team_show_cost_panel` helper degrades gracefully on any substrate
failure.

## Interfaces for Downstream Plans

**Plan 07-08 (clawteam doctor --gc zombie worktree cleanup):**
- No interface with this plan; 07-08 operates on the workspace layer,
  dashboard is unaffected.

**Plan 07-09 (10-sprint integration load test D-14/15/16):**
- Can assert that `clawteam team show --json <team>` after the fixture
  event stream reports `costRollup.alarms_fired == [50, 80, 100]` +
  `per_agent` / `per_sprint` rollup correctness. The test helper
  pattern used here (`_make_team` + `--json team show`) is re-usable.

**Future v1.1 work (out-of-scope for Phase 7):**
- Multi-team cost rollup dashboard (ROADMAP deferred) can reuse
  `render_team` by composing results across multiple tracker instances.
- Cache-hit-rate history trending can extend `CacheTracker` with a
  circular buffer; `render_team` would grow a new key in backward-
  compatible additive fashion.

## Known Stubs

**None.** The `status='unavailable'` fallback in `_team_show_cost_panel`
is documented best-effort behavior, not a stub: it preserves the
dashboard's "never crash cross-template" contract from Plan 03-08.
When cost substrate works (any gstack-templated team with
`[cost]` block in template), the panel renders live numbers.

## Self-Check: PASSED

Files created/modified verified on disk:

- `clawteam/cost/dashboard.py` -> FOUND
- `clawteam/cost/__init__.py` -> MODIFIED (2 new exports)
- `clawteam/cli/commands.py` -> MODIFIED (new helper + replaced
  placeholder + new _human branch)
- `tests/cost/test_dashboard.py` -> FOUND
- `tests/test_team_show_cost_panel.py` -> FOUND
- `tests/test_cli_commands.py` -> MODIFIED (BC updates)

Commits verified in git log:

- `1cea6a5` (test 07-07 Task 1 RED) -> FOUND
- `bc4839a` (feat 07-07 Task 1 GREEN) -> FOUND
- `4c540c8` (test 07-07 Task 2 RED) -> FOUND
- `7e693e8` (feat 07-07 Task 2 GREEN) -> FOUND
- `95baab2` (style 07-07 polish) -> FOUND

Acceptance grep checks:

- `grep -q "def render_team" clawteam/cost/dashboard.py` -> OK
- `grep -q "_team_show_cost_panel" clawteam/cli/commands.py` -> OK
- `grep -q "pending_phase_7" clawteam/cli/commands.py` -> NO MATCH (OK)

Verification commands from plan:

- `pytest tests/cost/test_dashboard.py -q` -> **7 passed** in 0.05s
- `pytest tests/test_team_show_cost_panel.py -q` -> **4 passed** in 0.38s
- `pytest tests/cost/ tests/test_team_show_cost_panel.py
  tests/test_cli_commands.py -q` -> **77 passed** in 1.81s

BC regression scope:

- `pytest tests/cost/ tests/test_team_show_cost_panel.py
  tests/test_cli_commands.py tests/test_event_types_phase7.py
  tests/test_event_bus.py tests/sprint/ tests/attention/
  tests/rate_limit/ -q` -> **166 passed** in 4.26s (all Phase 7
  substrate + CLI BC + events + sprint conductor + attention + rate-limit
  green).

Manual smoke from plan's verification step 2:

- `clawteam team show smoke-team` -> prints
  `Cost: $0.00 / $100.00 (0%) | cache hit: 0% | active agents: 0`
  (the old "Cost rollup: pending Phase 7 observability" line is GONE).

## TDD Gate Compliance

Both tasks used TDD; RED commits preceded GREEN commits:

| Task | RED commit | GREEN commit | Gate pass |
|------|-----------|--------------|-----------|
| 1    | `1cea6a5` | `bc4839a`    | OK        |
| 2    | `4c540c8` | `7e693e8`    | OK        |

Each RED commit was confirmed failing before the GREEN commit landed:

- Task 1 RED: `ModuleNotFoundError: No module named
  'clawteam.cost.dashboard'` at collection time (production module
  not yet authored; valid RED signal).
- Task 2 RED: `AssertionError: 'pending_phase_7' != 'pending_phase_7'`
  at runtime (test asserted the placeholder literal is gone; it still
  existed at the RED commit, so the test failed as intended).

Intervening commits between the RED and GREEN for Task 2
(`d1e55f6 docs(06): add code review report`,
`8b43732 docs(phase-06): add security threat verification`) are
from sibling executors completing Phase 6 housekeeping; they do not
touch any Phase 7 code and do not affect the RED -> GREEN gate
relationship.

## Next Plan Readiness

Plan 07-07 complete. Phase 7 has 2 plans remaining:

- **07-08** `clawteam doctor --gc` zombie worktree cleanup — emits
  `ZombieWorktreeGced` event. Substrate landed in Plan 07-01;
  independent of dashboard layer.
- **07-09** 10-sprint integration load test (D-14/15/16) — exercises
  full concurrency + attention + cost stack; can assert
  `clawteam team show --json <team>` contract locked here.

Phase 7 QUALITY-12 status: **fully closed**. 07-05 shipped accounting;
07-06 shipped policy + cache metric; 07-07 (this plan) shipped the
dashboard rendering + CLI integration so users can observe cost in
real time. UX-06 observable-dashboard half also closed.

---
*Phase: 07-parallel-sprints-attentionqueue-ux-cost-controls*
*Plan: 07 (Wave 5 — dashboard team show cost panel)*
*Completed: 2026-04-22*
