---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 07
type: execute
wave: 5
depends_on: [07-05, 07-06]
files_modified:
  - clawteam/cost/dashboard.py
  - clawteam/cli/commands.py
  - tests/cost/test_dashboard.py
  - tests/test_team_show_cost_panel.py
autonomous: true
requirements:
  - QUALITY-12
  - UX-06
tags:
  - dashboard
  - team-show-extension
  - cost-panel

must_haves:
  truths:
    - "dashboard.render_team(team, tracker, cache_tracker, conductor?) returns a structured dict with per_agent, per_sprint, totals, cache_hit_rate, budget, alarms_fired"
    - "clawteam team show replaces the 'pending Phase 7' placeholder with the real cost panel — rich table of per-agent + per-sprint breakdown"
    - "Budget bar shows spent / budget_usd + a colored threshold tick at 50/80/100%"
    - "active_agents count from SprintConductor.active_agents() also surfaces in team show (QUALITY-04 observable floor)"
    - "--json emits dashboard dict verbatim so callers can parse"
    - "Existing team show behavior for non-gstack / teams without a CostTracker stays unchanged (BC)"
  artifacts:
    - path: clawteam/cost/dashboard.py
      provides: "render_team + render_text helpers"
      contains: "def render_team|def render_text"
    - path: clawteam/cli/commands.py
      provides: "team_show extension with cost panel"
      contains: "costRollup.*status.*ok|_render_cost_panel"
  key_links:
    - from: clawteam/cli/commands.py
      to: clawteam/cost/dashboard.py
      via: "team_show calls dashboard.render_team when tracker available"
      pattern: "render_team|from clawteam.cost import"
    - from: clawteam/cli/commands.py
      to: clawteam/sprint/conductor.py
      via: "team_show calls conductor.active_agents() when conductor exists"
      pattern: "active_agents"
---

<objective>
Wave 5 — hook the cost dashboard into `clawteam team show`. Replace the "costRollup pending_phase_7" placeholder with the real panel. Include active-agent count (QUALITY-04 floor).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-05-cost-tracker-PLAN.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-06-cost-fallback-cache-PLAN.md

<interfaces>
Existing placeholder at clawteam/cli/commands.py line 1823-1828:
```python
"costRollup": {
    "status": "pending_phase_7",
    "perAgent": [],
    "totalTokens": None,
    "totalUsd": None,
},
```

From clawteam/cost (Plans 07-05/06):
```python
CostTracker.rollup_team() -> CostRollup
CostTracker.rollup_by_agent() -> dict[str, float]
CostTracker.rollup_by_sprint() -> dict[str, float]
CacheTracker.cache_hit_rate() -> float
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: dashboard.render_team structured dict</name>
  <files>
    clawteam/cost/dashboard.py,
    clawteam/cost/__init__.py,
    tests/cost/test_dashboard.py
  </files>
  <read_first>
    clawteam/cost/tracker.py (Plan 07-05),
    clawteam/cost/cache_tracker.py (Plan 07-06),
    clawteam/templates/__init__.py (CostConfig from Plan 07-01)
  </read_first>
  <behavior>
    - Test 1: `test_render_team_empty_tracker_shape` — fresh tracker + cache_tracker → returns dict with keys: team, status="ok", cost_usd=0, budget_usd, spend_percent=0, per_agent={}, per_sprint={}, cache_hit_rate=0, alarms_fired=[], active_agents=[].
    - Test 2: `test_render_team_with_spend` — emit events; dashboard reflects current spend + agent/sprint breakdown.
    - Test 3: `test_render_team_alarms_fired` — emit events crossing 50+80; rendered alarms_fired == [50, 80].
    - Test 4: `test_render_team_no_budget` — budget_usd=0 → spend_percent=0 always (no div-zero).
    - Test 5: `test_render_team_with_active_agents` — pass active_agents list → surfaces in result.
    - Test 6: `test_render_text_contains_team_name` — render_text returns a string containing team name + total USD.
  </behavior>
  <action>
**1. `clawteam/cost/dashboard.py` (NEW, ~140 LOC):**

```python
"""Cost dashboard rendering — consumed by clawteam team show (D-09).

Pure functions. Input: team name, CostTracker, CacheTracker, optional
active-agent list. Output: structured dict for JSON mode + text/rich
renderer for human mode.
"""
from __future__ import annotations

from typing import Any, Optional

from clawteam.cost.cache_tracker import CacheTracker, HEALTHY_THRESHOLD
from clawteam.cost.tracker import CostTracker


def render_team(
    team: str,
    tracker: CostTracker,
    cache_tracker: Optional[CacheTracker] = None,
    *,
    active_agents: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Return the structured dashboard dict for `clawteam team show`."""
    team_rollup = tracker.rollup_team()
    cost_usd = tracker.current_spend_usd()
    budget = tracker._budget_usd  # internal; tracker has no public getter
    spend_pct = tracker.spend_percent()
    cache_rate = cache_tracker.cache_hit_rate() if cache_tracker is not None else 0.0
    cache_healthy = cache_rate > HEALTHY_THRESHOLD
    return {
        "team": team,
        "status": "ok",
        "cost_usd": cost_usd,
        "budget_usd": budget,
        "spend_percent": spend_pct,
        "per_agent": tracker.rollup_by_agent(),
        "per_sprint": tracker.rollup_by_sprint(),
        "tokens_opus": team_rollup.tokens_opus,
        "tokens_sonnet": team_rollup.tokens_sonnet,
        "tokens_haiku": team_rollup.tokens_haiku,
        "cache_hit_rate": cache_rate,
        "cache_healthy": cache_healthy,
        "alarms_fired": sorted(tracker._fired_alarms),
        "active_agents": list(active_agents or []),
        "active_agent_count": len(active_agents or []),
    }


def render_text(data: dict[str, Any]) -> str:
    """Render a plain-text one-liner summary for team show's non-table rows."""
    pct = data.get("spend_percent", 0.0)
    cost = data.get("cost_usd", 0.0)
    budget = data.get("budget_usd", 0.0)
    if budget > 0:
        return (
            f"Cost — ${cost:.2f} / ${budget:.2f} ({pct:.0f}%) | "
            f"cache hit: {data.get('cache_hit_rate', 0)*100:.0f}% | "
            f"active agents: {data.get('active_agent_count', 0)}"
        )
    return (
        f"Cost — ${cost:.2f} (no budget) | "
        f"cache hit: {data.get('cache_hit_rate', 0)*100:.0f}% | "
        f"active agents: {data.get('active_agent_count', 0)}"
    )


__all__ = ["render_team", "render_text"]
```

**2. EDIT `clawteam/cost/__init__.py` — add dashboard exports:**

```python
from clawteam.cost.dashboard import render_team, render_text

__all__ = [
    "MODEL_PRICING", "calculate_cost_usd", "resolve_tier",
    "CostRollup", "CostTracker",
    "apply_fallback", "FALLBACK_LADDER",
    "CacheTracker", "HEALTHY_THRESHOLD",
    "render_team", "render_text",
]
```

**3. `tests/cost/test_dashboard.py` (~160 LOC):**

```python
import pytest
from clawteam.events.bus import EventBus
from clawteam.events.types import ClaudeApiResponse, ToolCallCompleted
from clawteam.cost.cache_tracker import CacheTracker
from clawteam.cost.dashboard import render_team, render_text
from clawteam.cost.tracker import CostTracker


def test_render_empty():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)
    ct = CacheTracker(team="t", bus=bus)
    d = render_team("t", t, ct)
    assert d["status"] == "ok"
    assert d["cost_usd"] == 0.0
    assert d["spend_percent"] == 0.0
    assert d["per_agent"] == {}
    assert d["per_sprint"] == {}
    assert d["cache_hit_rate"] == 0.0
    assert d["alarms_fired"] == []
    assert d["active_agents"] == []


def test_render_with_spend():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)
    ct = CacheTracker(team="t", bus=bus)
    bus.emit(ToolCallCompleted(team_name="t", agent="pm", sprint_id="s1", cost_usd=10.0))
    bus.emit(ToolCallCompleted(team_name="t", agent="ceo", sprint_id="s1", cost_usd=20.0))
    bus.emit(ClaudeApiResponse(team_name="t", cache_read_tokens=800, cache_creation_tokens=200))
    d = render_team("t", t, ct)
    assert d["cost_usd"] == pytest.approx(30.0)
    assert d["per_agent"] == {"pm": pytest.approx(10.0), "ceo": pytest.approx(20.0)}
    assert d["per_sprint"] == {"s1": pytest.approx(30.0)}
    assert d["cache_hit_rate"] == pytest.approx(0.8)
    assert d["cache_healthy"] is True


def test_render_alarms_fired():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0, alarm_percent=[50, 80, 100])
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=81.0))
    d = render_team("t", t, None)
    assert sorted(d["alarms_fired"]) == [50, 80]


def test_render_no_budget_safe():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=0.0)
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=50.0))
    d = render_team("t", t, None)
    assert d["spend_percent"] == 0.0
    assert d["cost_usd"] == 50.0


def test_render_active_agents_surface():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)
    d = render_team("t", t, None, active_agents=["pm", "ceo"])
    assert d["active_agents"] == ["pm", "ceo"]
    assert d["active_agent_count"] == 2


def test_render_text_contains_summary():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=100.0)
    bus.emit(ToolCallCompleted(team_name="t", cost_usd=25.0))
    d = render_team("t", t, None, active_agents=["pm"])
    text = render_text(d)
    assert "25.00" in text
    assert "100.00" in text
    assert "active agents: 1" in text


def test_render_text_no_budget():
    bus = EventBus()
    t = CostTracker(team="t", bus=bus, budget_usd=0.0)
    text = render_text(render_team("t", t, None))
    assert "no budget" in text
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/cost/test_dashboard.py tests/cost/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def render_team" clawteam/cost/dashboard.py` succeeds.
    - `pytest tests/cost/test_dashboard.py -q` reports 7 passed.
    - BC: `pytest tests/cost/ -q` all green.
  </acceptance_criteria>
  <done>Dashboard render functions proven pure + deterministic; Task 2 wires into CLI.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: team_show cost panel integration + active-agent row</name>
  <files>
    clawteam/cli/commands.py,
    tests/test_team_show_cost_panel.py
  </files>
  <read_first>
    clawteam/cli/commands.py (team_show function at lines 1767-1900 — esp. cost placeholder at 1823-1828 and human renderer at 1896-1898),
    clawteam/cost/dashboard.py (Task 1 output),
    tests/test_cli_commands.py (existing team show test shape)
  </read_first>
  <behavior>
    - Test 1: `test_team_show_still_works_without_tracker` — team with no cost events; exit 0; cost panel shows $0.00 / $100.00 or "no budget".
    - Test 2: `test_team_show_with_cost_events` — emit ToolCallCompleted events; `clawteam team show <team> --json` includes real cost_usd and per_agent.
    - Test 3: `test_team_show_backward_compatible_shape` — JSON output STILL contains `name`, `members`, `activeSprint`, `memory` keys (BC for Phase 3 UX-07 consumers).
    - Test 4: `test_team_show_active_agents_row` — when conductor has active agents, JSON includes `costRollup.active_agents`.
  </behavior>
  <action>
**1. EDIT `clawteam/cli/commands.py` — modify `team_show` to use real dashboard:**

Locate the placeholder at lines 1823-1828. REPLACE with a dashboard call:

```python
    # Phase 7 Plan 07-07: real cost dashboard (replaces pending_phase_7 placeholder).
    cost_panel = _team_show_cost_panel(team)

    data = {
        "name": config.name,
        "template": template_name,
        "leaderRole": leader_role,
        "createdAt": config.created_at,
        "description": getattr(config, "description", "") or "",
        "members": [m.model_dump(by_alias=True) for m in config.members],
        "activeSprint": active_sprint,
        "memory": {
            "status": (
                "pending_phase_6"
                if template_name == "gstack"
                else "not_applicable"
            ),
            "placeholderEntries": memory_placeholder_count,
        },
        "costRollup": cost_panel,
    }
```

Then ADD a new helper `_team_show_cost_panel(team)` near the existing `_team_show_active_sprint` helper (around line 1700):

```python
def _team_show_cost_panel(team: str) -> dict:
    """Build the cost panel for `clawteam team show <team>` (Plan 07-07).

    Best-effort: any failure falls back to a neutral "unknown" shape so the
    command never crashes when cost substrate is absent (e.g., non-gstack
    template).
    """
    try:
        from clawteam.cost import CacheTracker, CostTracker, render_team
        from clawteam.events.global_bus import get_event_bus
        from clawteam.team.manager import TeamManager
        from clawteam.templates import load_template

        cfg = TeamManager.get_team(team)
        budget_usd = 100.0
        alarm_percent = [50.0, 80.0, 100.0]
        if cfg and getattr(cfg, "template", None):
            try:
                tmpl = load_template(cfg.template)
                if tmpl.cost is not None:
                    budget_usd = tmpl.cost.budget_usd
                    alarm_percent = list(tmpl.cost.alarm_percent)
            except Exception:
                pass

        bus = get_event_bus()
        tracker = CostTracker(team=team, bus=bus, budget_usd=budget_usd, alarm_percent=alarm_percent)
        cache_tracker = CacheTracker(team=team, bus=bus)

        # Best-effort: fetch active agents from the team's conductor.
        active = []
        try:
            from clawteam.sprint.conductor import SprintConductor
            conductor = SprintConductor(team_name=team)
            active = conductor.active_agents()
        except Exception:
            pass

        return render_team(team, tracker, cache_tracker, active_agents=active)
    except Exception:
        return {
            "status": "unavailable",
            "cost_usd": 0.0,
            "budget_usd": 0.0,
            "spend_percent": 0.0,
            "per_agent": {},
            "per_sprint": {},
            "cache_hit_rate": 0.0,
            "alarms_fired": [],
            "active_agents": [],
            "active_agent_count": 0,
        }
```

**2. EDIT the `_human(d)` inner function at lines 1896-1898 — REPLACE the Phase-7-pending one-liner:**

```python
        # Cost rollup panel (Phase 7 Plan 07-07)
        cost = d.get("costRollup", {})
        if cost.get("status") == "ok":
            from clawteam.cost.dashboard import render_text
            console.print(f"\nCost: {render_text(cost)}")
            per_agent = cost.get("per_agent", {})
            if per_agent:
                cost_table = Table(title="Cost by Agent")
                cost_table.add_column("Agent", style="cyan")
                cost_table.add_column("USD", justify="right", style="green")
                for a, usd in sorted(per_agent.items(), key=lambda kv: -kv[1]):
                    cost_table.add_row(a, f"${usd:.4f}")
                console.print(cost_table)
            alarms = cost.get("alarms_fired", [])
            if alarms:
                alarm_style = "red" if 100 in alarms else ("yellow" if 80 in alarms else "green")
                console.print(
                    f"[{alarm_style}]Budget alarms fired: "
                    + ", ".join(f"{int(p)}%" for p in alarms)
                    + f"[/{alarm_style}]"
                )
            actives = cost.get("active_agents", [])
            if actives:
                console.print(f"Active agents ({cost.get('active_agent_count', 0)}): " + ", ".join(actives))
        else:
            console.print("\nCost: [dim]unavailable[/dim]")
```

**3. `tests/test_team_show_cost_panel.py` (~150 LOC):**

```python
import json
from typer.testing import CliRunner

import pytest

from clawteam.cli.commands import app


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return CliRunner(), tmp_path


def _make_team(tmp_path, name="t1", template="software-dev"):
    # Minimal team config file; mirrors TeamManager.create_team persistence.
    from clawteam.team.manager import TeamManager
    from clawteam.templates import load_template
    try:
        tmpl = load_template(template)
    except Exception:
        tmpl = None
    cfg = TeamManager.create_team(name, members=[])
    # TeamConfig might auto-init template; not essential for this test.
    return cfg


def test_team_show_placeholder_gone(runner):
    r, tmp = runner
    _make_team(tmp)
    result = r.invoke(app, ["--json", "team", "show", "t1"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["costRollup"]["status"] in {"ok", "unavailable"}
    # Phase 7: "pending_phase_7" must NOT be present any more.
    assert data["costRollup"].get("status") != "pending_phase_7"


def test_team_show_backward_compatible_shape(runner):
    r, tmp = runner
    _make_team(tmp)
    result = r.invoke(app, ["--json", "team", "show", "t1"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    for required in ("name", "members", "activeSprint", "memory", "costRollup"):
        assert required in data


def test_team_show_cost_panel_shape(runner):
    r, tmp = runner
    _make_team(tmp)
    result = r.invoke(app, ["--json", "team", "show", "t1"])
    data = json.loads(result.stdout)
    panel = data["costRollup"]
    for k in ("cost_usd", "budget_usd", "spend_percent", "per_agent", "per_sprint", "cache_hit_rate", "alarms_fired", "active_agents"):
        assert k in panel


def test_team_show_nonexistent_team(runner):
    r, _ = runner
    result = r.invoke(app, ["team", "show", "nonexistent"])
    assert result.exit_code == 1
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/test_team_show_cost_panel.py tests/test_cli_commands.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "_team_show_cost_panel" clawteam/cli/commands.py` succeeds.
    - `grep -q "pending_phase_7" clawteam/cli/commands.py` returns NO matches (placeholder removed).
    - `pytest tests/test_team_show_cost_panel.py -q` reports 4 passed.
    - BC: `pytest tests/test_cli_commands.py -q` still green.
  </acceptance_criteria>
  <done>Cost panel live in team show; Phase 3 UX-07 consumers keep their JSON shape plus the new costRollup key.</done>
</task>

</tasks>

<verification>
1. `pytest tests/cost/ tests/test_team_show_cost_panel.py tests/test_cli_commands.py -q` — all green.
2. Manual smoke: `clawteam team show <any-team>` shows Cost row (not "pending Phase 7 observability").
</verification>

<success_criteria>
- Tasks 1-2 acceptance met.
- Cost panel replaces placeholder; QUALITY-12 observable floor hit.
- Active-agent count surfaces (QUALITY-04 floor).
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-07-SUMMARY.md`.
</output>
