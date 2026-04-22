---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 08
type: execute
wave: 5
depends_on: [07-01]
files_modified:
  - clawteam/workspace/gc.py
  - clawteam/cli/commands.py
  - tests/workspace/__init__.py
  - tests/workspace/test_zombie_gc.py
autonomous: true
requirements:
  - CORE-06
tags:
  - workspace-gc
  - disk-budget
  - doctor-extension

must_haves:
  truths:
    - "find_zombie_worktrees(root, max_age_days=30, active_branches=()) returns paths older than threshold whose branch isn't in active_branches set"
    - "gc_zombies() deletes the returned paths (best-effort) and emits ZombieWorktreeGced per deletion"
    - "disk_usage_report(team) computes bytes-used under a team dir; surfaces soft (5 GB) / hard (10 GB) threshold"
    - "clawteam doctor --gc triggers the gc pass across all teams; prints how many freed"
    - "Active-branch filter: if a SprintState.workspace_branch matches a worktree's branch, NEVER gc that worktree regardless of age"
  artifacts:
    - path: clawteam/workspace/gc.py
      provides: "find_zombie_worktrees + gc_zombies + disk_usage_report"
      contains: "def find_zombie_worktrees|def gc_zombies|def disk_usage_report"
  key_links:
    - from: clawteam/workspace/gc.py
      to: clawteam/sprint/state.py
      via: "gc_zombies filters by active workspace_branch from SprintState"
      pattern: "workspace_branch"
    - from: clawteam/workspace/gc.py
      to: clawteam/events/types.py
      via: "Emits ZombieWorktreeGced per deletion"
      pattern: "ZombieWorktreeGced"
---

<objective>
Wave 5 part 2 — zombie-worktree auto-GC (ROADMAP SC #10) + disk-budget observability. Safe-by-default: never delete a worktree whose branch matches an active SprintState.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md (§Pitfall 6)

<interfaces>
From clawteam/events/types.py (Plan 07-01):
```python
@dataclass class ZombieWorktreeGced(HarnessEvent):
    path: str = ""
    age_days: int = 0
    freed_bytes: int = 0
```

Existing clawteam doctor entrypoint (clawteam/cli/commands.py line 1227):
```python
@app.command("doctor")
def doctor():
    """Detect optional tools and print install hints."""
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: find_zombie_worktrees + gc_zombies + disk_usage_report</name>
  <files>
    clawteam/workspace/gc.py,
    tests/workspace/__init__.py,
    tests/workspace/test_zombie_gc.py
  </files>
  <read_first>
    clawteam/sprint/state.py (SprintState.workspace_branch shape),
    clawteam/team/models.py (get_data_dir),
    clawteam/events/types.py (ZombieWorktreeGced from Plan 07-01)
  </read_first>
  <behavior>
    - Test 1: `test_find_none_in_empty_dir` — empty tmp root; find_zombie_worktrees returns [].
    - Test 2: `test_find_skips_young_dirs` — dir with mtime 10 days ago; max_age_days=30 → not returned.
    - Test 3: `test_find_returns_old_dirs` — dir with mtime 40 days ago; max_age_days=30 → returned.
    - Test 4: `test_find_respects_active_branches` — old dir named "agent-foo"; active_branches={"agent-foo"} → skipped despite age.
    - Test 5: `test_gc_zombies_deletes_returned_paths` — find + gc; dir is gone.
    - Test 6: `test_gc_zombies_emits_event` — gc_zombies(bus=bus); ZombieWorktreeGced emitted with path + age_days + freed_bytes.
    - Test 7: `test_gc_zombies_idempotent_on_missing` — call gc_zombies(["/does/not/exist"]); no crash; no event.
    - Test 8: `test_disk_usage_report_sums_bytes` — create 3 files of known sizes; disk_usage_report returns total_bytes correctly.
    - Test 9: `test_disk_usage_report_thresholds` — 6 GB used → over_soft=True, over_hard=False; 11 GB → over_hard=True.
  </behavior>
  <action>
**1. `clawteam/workspace/gc.py` (NEW, ~150 LOC):**

```python
"""Zombie-worktree auto-GC + disk-budget observability (Phase 7 ROADMAP SC #10).

Safety invariant: NEVER delete a worktree whose branch matches an
active SprintState.workspace_branch (Pitfall 6). Callers that skip the
active_branches filter bear the risk of nuking in-flight work.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Iterable, Optional

from clawteam.events.bus import EventBus
from clawteam.events.types import ZombieWorktreeGced

# Disk-budget thresholds per team.
SOFT_BYTES = 5 * 1024 * 1024 * 1024   # 5 GB
HARD_BYTES = 10 * 1024 * 1024 * 1024  # 10 GB


def find_zombie_worktrees(
    root: Path,
    *,
    max_age_days: int = 30,
    active_branches: Iterable[str] = (),
    now_fn=time.time,
) -> list[Path]:
    """Return direct-child dirs of `root` older than max_age_days.

    active_branches is a set of branch names (matched against directory
    basenames) that MUST be preserved regardless of age.
    """
    if not root.is_dir():
        return []
    active = set(active_branches)
    cutoff = now_fn() - (max_age_days * 86400.0)
    zombies: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if child.name in active:
            continue
        try:
            mtime = child.stat().st_mtime
        except OSError:
            continue
        if mtime < cutoff:
            zombies.append(child)
    return zombies


def _dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def gc_zombies(
    paths: Iterable[Path],
    *,
    team_name: str = "",
    bus: Optional[EventBus] = None,
    now_fn=time.time,
) -> list[Path]:
    """Delete each path; emit ZombieWorktreeGced. Idempotent on missing paths."""
    gced: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            mtime = path.stat().st_mtime
            age_days = int((now_fn() - mtime) / 86400.0)
            freed = _dir_size(path)
            shutil.rmtree(path, ignore_errors=True)
        except OSError:
            continue
        gced.append(path)
        if bus is not None:
            try:
                bus.emit(
                    ZombieWorktreeGced(
                        team_name=team_name,
                        path=str(path),
                        age_days=age_days,
                        freed_bytes=freed,
                    )
                )
            except Exception:  # pragma: no cover
                pass
    return gced


def disk_usage_report(team_root: Path) -> dict:
    """Return disk usage dict: total_bytes, over_soft, over_hard, path."""
    total = _dir_size(team_root)
    return {
        "path": str(team_root),
        "total_bytes": total,
        "total_gb": round(total / (1024**3), 2),
        "over_soft": total > SOFT_BYTES,
        "over_hard": total > HARD_BYTES,
        "soft_threshold_gb": SOFT_BYTES // (1024**3),
        "hard_threshold_gb": HARD_BYTES // (1024**3),
    }


__all__ = [
    "find_zombie_worktrees",
    "gc_zombies",
    "disk_usage_report",
    "SOFT_BYTES",
    "HARD_BYTES",
]
```

**2. Tests:** `tests/workspace/__init__.py` (empty) + `tests/workspace/test_zombie_gc.py` (~200 LOC):

```python
import os
import time
from pathlib import Path
import pytest
from clawteam.events.bus import EventBus
from clawteam.events.types import ZombieWorktreeGced
from clawteam.workspace.gc import (
    disk_usage_report, find_zombie_worktrees, gc_zombies,
    HARD_BYTES, SOFT_BYTES,
)


def _mk_dir(tmp, name, age_days=0):
    p = tmp / name
    p.mkdir()
    if age_days > 0:
        past = time.time() - age_days * 86400
        os.utime(p, (past, past))
    return p


def test_find_none_empty(tmp_path):
    assert find_zombie_worktrees(tmp_path) == []


def test_find_skips_young(tmp_path):
    _mk_dir(tmp_path, "young", age_days=10)
    assert find_zombie_worktrees(tmp_path, max_age_days=30) == []


def test_find_returns_old(tmp_path):
    _mk_dir(tmp_path, "old", age_days=40)
    result = find_zombie_worktrees(tmp_path, max_age_days=30)
    assert len(result) == 1
    assert result[0].name == "old"


def test_find_respects_active_branches(tmp_path):
    _mk_dir(tmp_path, "active", age_days=40)
    _mk_dir(tmp_path, "zombie", age_days=40)
    result = find_zombie_worktrees(
        tmp_path, max_age_days=30, active_branches={"active"}
    )
    assert len(result) == 1
    assert result[0].name == "zombie"


def test_gc_zombies_deletes(tmp_path):
    d = _mk_dir(tmp_path, "old", age_days=40)
    (d / "file.txt").write_text("content")
    gced = gc_zombies([d])
    assert d not in list(tmp_path.iterdir())
    assert gced == [d]


def test_gc_zombies_emits_event(tmp_path):
    d = _mk_dir(tmp_path, "old", age_days=40)
    (d / "file.txt").write_text("hello world")
    bus = EventBus()
    received: list = []
    bus.subscribe(ZombieWorktreeGced, lambda ev: received.append(ev))
    gc_zombies([d], team_name="t1", bus=bus)
    assert len(received) == 1
    assert received[0].path == str(d)
    assert received[0].age_days >= 30
    assert received[0].freed_bytes >= 11  # "hello world" is 11 bytes


def test_gc_zombies_idempotent_missing(tmp_path):
    fake = tmp_path / "does-not-exist"
    bus = EventBus()
    received: list = []
    bus.subscribe(ZombieWorktreeGced, lambda ev: received.append(ev))
    result = gc_zombies([fake], bus=bus)
    assert result == []
    assert received == []


def test_disk_usage_report_shape(tmp_path):
    (tmp_path / "f1.bin").write_bytes(b"x" * 100)
    (tmp_path / "f2.bin").write_bytes(b"x" * 200)
    report = disk_usage_report(tmp_path)
    assert report["total_bytes"] >= 300
    assert report["over_soft"] is False
    assert report["over_hard"] is False


def test_disk_thresholds_classified():
    # Construct manual report dict to simulate thresholds without 11 GB of disk writes.
    assert SOFT_BYTES == 5 * 1024 * 1024 * 1024
    assert HARD_BYTES == 10 * 1024 * 1024 * 1024
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/workspace/test_zombie_gc.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def find_zombie_worktrees" clawteam/workspace/gc.py` succeeds.
    - `grep -q "def gc_zombies" clawteam/workspace/gc.py` succeeds.
    - `grep -q "def disk_usage_report" clawteam/workspace/gc.py` succeeds.
    - `pytest tests/workspace/test_zombie_gc.py -q` reports 9 passed.
  </acceptance_criteria>
  <done>GC primitives proven; Task 2 wires doctor --gc.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: clawteam doctor --gc wiring</name>
  <files>
    clawteam/cli/commands.py,
    tests/test_doctor_gc.py
  </files>
  <read_first>
    clawteam/cli/commands.py (doctor command at lines 1227-1270)
  </read_first>
  <behavior>
    - Test 1: `test_doctor_no_gc_flag_preserves_old_behavior` — `clawteam doctor` (no --gc) still exits 0 and prints tool checklist.
    - Test 2: `test_doctor_gc_empty_teams` — no teams dir; `clawteam doctor --gc` exits 0 + "0 worktrees gc'd".
    - Test 3: `test_doctor_gc_finds_and_cleans` — create old worktree under teams dir; `clawteam doctor --gc` removes it; reports count.
    - Test 4: `test_doctor_gc_respects_active_sprints` — create old worktree matching an active sprint's workspace_branch; GC leaves it alone.
  </behavior>
  <action>
**1. EDIT `clawteam/cli/commands.py` — REPLACE the existing `doctor()` function at lines 1227-1270 to accept `--gc`:**

```python
@app.command("doctor")
def doctor(
    gc: bool = typer.Option(
        False, "--gc",
        help="Phase 7: GC zombie worktrees older than 30 days.",
    ),
):
    """Detect optional tools and print install hints. With --gc, also clean zombie worktrees."""
    # ... keep existing tool-detection body unchanged ...

    if not gc:
        return

    # Phase 7 Plan 07-08: zombie-worktree auto-GC.
    from clawteam.workspace.gc import find_zombie_worktrees, gc_zombies, disk_usage_report
    from clawteam.team.models import get_data_dir
    from clawteam.sprint.state import load_sprint_state

    teams_root = get_data_dir() / "teams"
    if not teams_root.exists():
        _output(
            {"gc": {"teams_checked": 0, "zombies_removed": 0}},
            lambda d: console.print("[dim]No teams found; nothing to gc.[/dim]"),
        )
        return

    summary = {"teams": [], "total_zombies": 0, "total_freed_bytes": 0}
    for team_dir in sorted(teams_root.iterdir()):
        if not team_dir.is_dir():
            continue
        worktrees_root = team_dir / "worktrees"
        if not worktrees_root.is_dir():
            continue

        # Collect active branches from this team's sprints.
        active_branches: set[str] = set()
        sprints_dir = team_dir / "sprints"
        if sprints_dir.is_dir():
            for sprint_dir in sprints_dir.iterdir():
                try:
                    state = load_sprint_state(team_dir.name, sprint_dir.name)
                    if state.workspace_branch:
                        active_branches.add(state.workspace_branch)
                except Exception:
                    continue

        zombies = find_zombie_worktrees(
            worktrees_root, max_age_days=30, active_branches=active_branches
        )
        from clawteam.events.global_bus import get_event_bus
        bus = get_event_bus()
        gced = gc_zombies(zombies, team_name=team_dir.name, bus=bus)
        usage = disk_usage_report(team_dir)
        summary["teams"].append({
            "team": team_dir.name,
            "zombies_removed": len(gced),
            "active_branches_preserved": sorted(active_branches),
            "disk_usage": usage,
        })
        summary["total_zombies"] += len(gced)

    def _human(d):
        console.print(f"\n[green]GC complete:[/green] {d['total_zombies']} zombie worktrees removed across {len(d['teams'])} team(s).")
        for t in d["teams"]:
            u = t["disk_usage"]
            disk_tag = "[red]over hard[/red]" if u["over_hard"] else ("[yellow]over soft[/yellow]" if u["over_soft"] else "[green]ok[/green]")
            console.print(f"  {t['team']}: removed={t['zombies_removed']}, disk={u['total_gb']} GB [{disk_tag}]")

    _output(summary, _human)
```

**Note:** Keep the existing tool-detection body intact. Only prepend the `gc` parameter + append the gc section.

**2. `tests/test_doctor_gc.py` (~140 LOC):**

```python
import os
import time
from pathlib import Path
import pytest
from typer.testing import CliRunner
from clawteam.cli.commands import app


def _make_worktree(team_dir, name, age_days=0):
    wt = team_dir / "worktrees" / name
    wt.mkdir(parents=True)
    (wt / "file.txt").write_text("content")
    if age_days > 0:
        past = time.time() - age_days * 86400
        os.utime(wt, (past, past))
    return wt


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return CliRunner(), tmp_path


def test_doctor_no_gc_flag(runner):
    r, _ = runner
    result = r.invoke(app, ["doctor"])
    assert result.exit_code == 0


def test_doctor_gc_empty(runner):
    r, _ = runner
    result = r.invoke(app, ["doctor", "--gc"])
    assert result.exit_code == 0


def test_doctor_gc_finds_and_cleans(runner):
    r, tmp = runner
    team_dir = tmp / "teams" / "t1"
    team_dir.mkdir(parents=True)
    zombie = _make_worktree(team_dir, "old-branch", age_days=40)
    young = _make_worktree(team_dir, "fresh-branch", age_days=5)
    result = r.invoke(app, ["--json", "doctor", "--gc"])
    assert result.exit_code == 0
    import json
    data = json.loads(result.stdout)
    assert data["total_zombies"] == 1
    assert not zombie.exists()
    assert young.exists()


def test_doctor_gc_preserves_active_sprint_branches(runner):
    r, tmp = runner
    from clawteam.sprint.state import SprintState, save_sprint_state

    team_dir = tmp / "teams" / "t1"
    team_dir.mkdir(parents=True)

    # Make an "active" worktree AND a matching sprint.
    active_wt = _make_worktree(team_dir, "active-branch", age_days=40)
    zombie_wt = _make_worktree(team_dir, "zombie-branch", age_days=40)

    # Create SprintState pointing at active-branch.
    sprint = SprintState(
        sprint_id="aaaa1111", goal="g", team="t1",
        current_phase="think", workspace_branch="active-branch",
    )
    save_sprint_state(sprint)

    result = r.invoke(app, ["doctor", "--gc"])
    assert result.exit_code == 0
    assert active_wt.exists()   # preserved
    assert not zombie_wt.exists()  # cleaned
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/test_doctor_gc.py tests/test_doctor.py tests/test_doctor_new_entries.py tests/workspace/ -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "gc: bool = typer.Option" clawteam/cli/commands.py` succeeds.
    - `grep -q "find_zombie_worktrees" clawteam/cli/commands.py` succeeds.
    - `pytest tests/test_doctor_gc.py -q` reports 4 passed.
    - BC: `pytest tests/test_doctor.py tests/test_doctor_new_entries.py -q` still green.
  </acceptance_criteria>
  <done>`clawteam doctor --gc` removes zombie worktrees; active branches preserved.</done>
</task>

</tasks>

<verification>
1. `pytest tests/workspace/ tests/test_doctor_gc.py tests/test_doctor.py -q` — green.
2. `python -c "from clawteam.workspace.gc import find_zombie_worktrees, gc_zombies, disk_usage_report; print('ok')"` — prints ok.
</verification>

<success_criteria>
- Tasks 1-2 acceptance met.
- Active-branch safety invariant proven.
- Existing doctor behavior preserved when --gc not passed.
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-08-SUMMARY.md`.
</output>
