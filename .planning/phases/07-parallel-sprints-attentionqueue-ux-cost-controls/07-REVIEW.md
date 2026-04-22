---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
reviewed: 2026-04-22T00:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - clawteam/attention/__init__.py
  - clawteam/attention/auto_accept.py
  - clawteam/cli/commands.py
  - clawteam/cost/__init__.py
  - clawteam/cost/cache_tracker.py
  - clawteam/cost/dashboard.py
  - clawteam/cost/fallback.py
  - clawteam/cost/pricing.py
  - clawteam/cost/rollup.py
  - clawteam/cost/tracker.py
  - clawteam/workspace/gc.py
  - tests/attention/test_attend_cli.py
  - tests/attention/test_auto_accept.py
  - tests/cost/__init__.py
  - tests/cost/test_cache_tracker.py
  - tests/cost/test_dashboard.py
  - tests/cost/test_fallback.py
  - tests/cost/test_pricing.py
  - tests/cost/test_tracker.py
  - tests/integration/test_phase7_attention_ranking.py
  - tests/integration/test_phase7_cost_dashboard.py
  - tests/integration/test_phase7_ten_sprint_load.py
  - tests/test_cli_commands.py
  - tests/test_doctor_gc.py
  - tests/test_team_show_cost_panel.py
  - tests/workspace/__init__.py
  - tests/workspace/test_zombie_gc.py
findings:
  critical: 1
  warning: 6
  info: 7
  total: 14
status: issues_found
---

# Phase 7: Code Review Report

**Reviewed:** 2026-04-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

## Summary

Phase 7 introduces the AttentionQueue CLI (`attend`), the cost substrate (CostTracker / CacheTracker / dashboard / fallback ladder), the auto-accept-reversible helper, and the `doctor --gc` zombie-worktree pass. The pure-function layers (pricing, fallback, rollup, dashboard) are well-structured and well-tested. Locking in the event-subscribed trackers is correct.

One critical issue: the `doctor --gc` pass scans a directory that does not match where `WorkspaceManager` actually creates worktrees, so in production it will never find real zombies even though its own unit tests pass. Several warnings around concurrency (dashboard reads a tracker's private set outside its lock), resource lifecycle (fresh trackers subscribed on every `team show` call leak subscriptions on the global bus), and silent exception swallowing. Auto-accept writes answer.md non-atomically despite docstring claims.

Scope out-of-review note: This review did not re-audit the sprint conductor / semaphore / asyncio layers or the rate-limit monitor — only the files in the explicit list. Integration tests for those layers are present and thorough but were reviewed for assertion quality, not reviewed as source.

## Critical Issues

### CR-01: `doctor --gc` scans the wrong directory; zombie GC is a no-op in production

**File:** `clawteam/cli/commands.py:1304`
**Issue:** The doctor GC pass scans `team_dir / "worktrees"` (i.e., `~/.clawteam/teams/<name>/worktrees/*`) for zombies. However `WorkspaceManager._workspaces_root()` in `clawteam/workspace/manager.py:19-23` creates worktrees under `get_data_dir() / "workspaces" / <team_name> / <agent_name>/`. These are two disjoint path subtrees. The unit test in `tests/test_doctor_gc.py` manually pre-populates `team_dir / "worktrees" / <name>/` matching the GC scan path, so tests pass, but no real ClawTeam deployment ever writes there. Net effect: `clawteam doctor --gc` reports `total_zombies=0` on every production host regardless of actual disk state. Phase 7 SC #10 ("zombie-worktree auto-GC") is silently unmet.

**Fix:** Either (a) change the scan root to match `WorkspaceManager._workspaces_root() / team_name` and iterate per-agent subdirs as the zombie candidate set, or (b) add a wrapper that unions both locations. Example for (a):

```python
from clawteam.workspace.manager import _workspaces_root  # or a new public accessor

workspaces_root = _workspaces_root() / team_dir.name
if not workspaces_root.is_dir():
    continue
# find_zombie_worktrees now operates on the real layout.
zombies = find_zombie_worktrees(
    workspaces_root,
    max_age_days=30,
    active_branches=active_branches,
)
```

Also update `tests/test_doctor_gc.py` to build worktrees under the real `workspaces/<team>/<agent>/` path so the test actually exercises the shipped layout, not a parallel universe.

## Warnings

### WR-01: `dashboard.render_team` reads `tracker._fired_alarms` outside the tracker's lock

**File:** `clawteam/cost/dashboard.py:65`
**Issue:** `fired = sorted(tracker._fired_alarms)` iterates the tracker's internal `set[float]` without holding `tracker._lock`. Meanwhile, `CostTracker._on_tool_call` can mutate the same set under its own lock (`tracker.py:162 self._fired_alarms.add(thresh)`). Concurrent iteration during mutation raises `RuntimeError: Set changed size during iteration`. This is a low-probability race (requires an event to arrive mid-render) but realistic under Phase 7's event-driven load. Also violates encapsulation by reaching into a leading-underscore attribute.

**Fix:** Add a public accessor on `CostTracker` and call it under the lock:

```python
# In tracker.py
def fired_alarms(self) -> list[float]:
    with self._lock:
        return sorted(self._fired_alarms)

# In dashboard.py
fired = tracker.fired_alarms()
```

### WR-02: `_team_show_cost_panel` leaks event-bus subscriptions on every invocation

**File:** `clawteam/cli/commands.py:1893-1899`
**Issue:** Every `clawteam team show <team>` call constructs a fresh `CostTracker` and `CacheTracker` against the global event bus (`get_event_bus()`). Both constructors call `bus.subscribe(...)` (see `tracker.py:73-74`, `cache_tracker.py:51-52`). Nothing ever unsubscribes. In short-lived CLI invocations the process exits and the leak is moot, but any long-running consumer (test harness reusing the CLI app in-process, future daemon mode, server embedding) accumulates one tracker per call, each of which handles every future event forever — unbounded memory + handler-fanout growth.

Also: because the tracker is fresh every call, the cost panel will only ever reflect events emitted after the tracker was constructed in the current invocation. For a short-lived CLI, this is always zero. The docstring at `commands.py:2015` calls this a "real cost dashboard replaces the earlier Phase 3 placeholder" but the panel cannot display historical spend, so the behavior contradicts the docstring.

**Fix:** Either (a) make trackers singletons keyed on team and re-used across calls (constructed once at module init; persist state or rebuild from an event log), or (b) add explicit teardown: wrap the block in `try/finally` that calls `bus.unsubscribe(...)` on exit. Option (a) also fixes the "panel always shows 0" issue. Add a public `CostTracker.close()` / `__exit__` so subscribers can be released deterministically.

### WR-03: `doctor --gc` summary `total_freed_bytes` is always 0 (dead code)

**File:** `clawteam/cli/commands.py:1338-1346, 1356`
**Issue:** `team_freed = sum(<empty-list>)` evaluates to 0 unconditionally. The comment at `1339-1344` acknowledges the approach is broken (`"reconstruct via difference between pre/post is impractical"`). The `gc_summary["total_freed_bytes"]` field added to the JSON output is therefore always 0 — consumers get a number that looks like a telemetry signal but is meaningless. Worse, the per-path `freed_bytes` IS already computed by `gc_zombies` and attached to each `ZombieWorktreeGced` event (`gc.py:118, 130`); those values just aren't surfaced to the CLI.

**Fix:** Change `gc_zombies` to return a list of tuples `(path, freed_bytes)` (or a list of `GcResult` dataclasses), then sum the freed bytes in the CLI:

```python
# gc.py
from dataclasses import dataclass

@dataclass(frozen=True)
class GcResult:
    path: Path
    age_days: int
    freed_bytes: int

def gc_zombies(...) -> list[GcResult]:
    ...
    gced.append(GcResult(path=path, age_days=age_days, freed_bytes=freed))
    return gced

# commands.py
team_freed = sum(r.freed_bytes for r in gced)
gc_summary["teams"][-1]["freed_bytes"] = team_freed
gc_summary["total_freed_bytes"] += team_freed
```

### WR-04: `gc_zombies` reports deletion even when `shutil.rmtree(ignore_errors=True)` silently fails

**File:** `clawteam/workspace/gc.py:119-122`
**Issue:** `shutil.rmtree(path, ignore_errors=True)` will return silently if some entries could not be removed (permission gaps, open file handles on Windows, in-use bind mounts). The code then unconditionally appends `path` to the `gced` list and emits a `ZombieWorktreeGced` event. Callers (and event subscribers) cannot distinguish "truly deleted" from "partially deleted" or "not deleted at all but we lied." For a GC subsystem whose primary contract is freeing disk, the caller materially needs this signal.

**Fix:** Re-check after rmtree and branch:

```python
shutil.rmtree(path, ignore_errors=True)
if path.exists():
    # Partial failure — keep the zombie discoverable next sweep.
    continue
gced.append(path)
if bus is not None:
    bus.emit(ZombieWorktreeGced(...))
```

Alternatively, switch to `shutil.rmtree(path)` without `ignore_errors` and `except OSError` around it, logging per-path failures. The current swallow-and-claim-success pattern is the worst of both worlds.

### WR-05: Auto-accept `answer.md` write is non-atomic despite docstring claim

**File:** `clawteam/attention/auto_accept.py:85`, docstring at line 51
**Issue:** The docstring at `auto_accept.py:50-51` states "answer.md written atomically," but the actual write at line 85 is `answer_path.write_text(frontmatter + body, encoding="utf-8")`. `Path.write_text` opens, writes, and closes — a crash or SIGKILL between the open-truncate and close leaves a zero-byte or partial file on disk. A partial answer.md with only `---\n` would still cause `answer_path.exists()` to return True on the next `apply_auto_accept` call, so the idempotency check (`line 65-67`) now skips re-writing the correct content. InteractionGate could then unblock on a half-written answer containing no selection, effectively auto-accepting a blank default.

**Fix:** Write-then-rename to achieve atomic swap on POSIX:

```python
import os
tmp_path = answer_path.with_suffix(answer_path.suffix + ".tmp")
tmp_path.write_text(frontmatter + body, encoding="utf-8")
os.replace(tmp_path, answer_path)  # atomic on same filesystem
```

Or simply correct the docstring if atomic write is out-of-scope for the plan. The claim must match behavior either way.

### WR-06: Silent `except Exception: pass` hides real bugs in emit / panel fallback

**File:** `clawteam/cost/tracker.py:178-183`, `clawteam/workspace/gc.py:133-134`, `clawteam/cli/commands.py:1916`
**Issue:** All three sites use `except Exception: pass` with no logging:

- `tracker.py:178-183` — swallows any exception from `bus.emit(BudgetAlarmReached(...))`. The comment says "belt-and-brace" but a real bug (e.g., wrong field name after a schema change) would be swallowed and the 50% / 80% / 100% alarms would silently never fire.
- `gc.py:133-134` — swallows `bus.emit(ZombieWorktreeGced(...))` failures with zero trace.
- `commands.py:1916` — `_team_show_cost_panel`'s outer `try/except Exception` swallows every failure in the cost pipeline and returns a neutral "unavailable" dict. A real schema mismatch or Bus import failure is masked forever; users see "Cost: unavailable" and cannot debug.

**Fix:** Log the exception at `logging.WARNING` or `logging.ERROR` level before swallowing so operators can grep the log:

```python
import logging
log = logging.getLogger(__name__)
try:
    ...
except Exception:
    log.exception("cost panel failed, falling back to 'unavailable'")
    return { ... fallback dict ... }
```

Do not remove the fallback — it is defensive and correct — but make it observable.

## Info

### IN-01: `gc_zombies` can produce negative `age_days` under clock skew

**File:** `clawteam/workspace/gc.py:117`
**Issue:** `age_days = int((now_fn() - mtime) / 86400.0)` produces a negative integer if `mtime > now_fn()` (future-dated mtime from clock skew, fs mount with incorrect time, or a test harness that sets mtime ahead). `ZombieWorktreeGced.age_days` is declared as an `int` in the event schema, so consumers that assume non-negative will misreport. Also `int(...)` truncates toward zero, so 0.5 days → 0 (minor rounding concern).

**Fix:** Clamp to zero and use explicit flooring:

```python
import math
age_days = max(0, math.floor((now_fn() - mtime) / 86400.0))
```

### IN-02: `clawteam attend pick` does not shlex-split `$EDITOR`

**File:** `clawteam/cli/commands.py:6372-6374`
**Issue:** `subprocess.run([editor, str(item.question_path)])` treats `$EDITOR` as a single argv[0]. If the user sets `EDITOR="vim -u NONE"` (common pattern — git, nano, pager all accept this), the whole string is looked up as an executable named `"vim -u NONE"` and fails with `FileNotFoundError`. Not a security issue (no shell involved), but a UX regression vs. convention. No security concern either direction — `$EDITOR` is the user's own env var.

**Fix:** Split on shell rules:

```python
import shlex
editor_argv = shlex.split(editor)
subprocess.run([*editor_argv, str(item.question_path)], check=False)
```

### IN-03: `dashboard.render_team` accesses `tracker._fired_alarms` (leading underscore)

**File:** `clawteam/cost/dashboard.py:65`
**Issue:** Encapsulation leak — the dashboard module should not read a leading-underscore attribute of a separate module's class. Any future refactor to `_fired_alarms` (rename, data structure change, move to a separate registry) silently breaks the dashboard at runtime because Python does not enforce underscore privacy. See WR-01 for the concurrency angle; this info-level note is the clean-API angle.

**Fix:** Add `CostTracker.fired_alarms() -> list[float]` as a public accessor and use it. Same fix resolves both WR-01 and IN-03.

### IN-04: Cost panel docstring overstates behavior

**File:** `clawteam/cli/commands.py:2015-2019`
**Issue:** Comment says "real cost dashboard replaces the earlier Phase 3 placeholder" but because a fresh `CostTracker` is constructed per CLI invocation (WR-02), the panel only reflects events emitted during that single process lifetime. In a short-lived CLI, this is always empty. The cost panel is functionally still a placeholder for historical data until a persistence layer or cross-invocation event replay lands.

**Fix:** Either make the dashboard reflect historical spend (WR-02 fix), or update the comment to match current behavior: "live per-invocation cost dashboard; historical spend is deferred to a future phase."

### IN-05: `CostTracker.rollup_by_agent_sprint` and defaultdict mutation from reads

**File:** `clawteam/cost/tracker.py:65-67`
**Issue:** The three aggregate maps are `defaultdict(float)`. All writes happen under lock in `_on_tool_call`. Reads (`rollup_by_agent`, `rollup_by_sprint`, `rollup_by_agent_sprint`) wrap them in `dict(self._by_X)` under lock, so no defaultdict-mutation-from-read issue actually leaks out. No actionable bug, but the invariant relies on every internal read being routed through the public getters. If a future contributor adds an internal `self._by_agent[some_key]` read without the lock, a defaultdict would insert `some_key: 0.0` — unexpected state mutation from a read. Worth a comment.

**Fix:** Add a one-line comment above the defaultdict declarations reminding contributors that reads of these maps are mutation-equivalent (or replace with plain `dict` + explicit `.get(k, 0.0)` patterns at write sites).

### IN-06: Fallback `apply_fallback` idempotency-on-haiku flag may confuse downstream

**File:** `clawteam/cost/fallback.py:71-77`
**Issue:** `apply_fallback("claude-haiku", 90.0, 80.0)` returns `("claude-haiku", True)` — fallback_applied=True even though no model change occurred. Docstring and test `test_haiku_stays_haiku` make this explicit, but a consumer reading `model_fallback_applied: true` on an envelope will interpret it as "downgrade occurred" and may compute a false delta (e.g., dashboards that show "number of fallbacks" will inflate when the team is already pinned to haiku). Current tests lock the invariant, so this is intentional — just worth surfacing.

**Fix:** Consider adding a separate flag or a tri-state return (`("haiku", "engaged_no_change")`) if downstream consumers need to distinguish. Alternatively, document prominently in the envelope schema that `model_fallback_applied` means "policy engaged, may or may not have changed model."

### IN-07: `find_zombie_worktrees` active-branch match uses basename only

**File:** `clawteam/workspace/gc.py:68`, `clawteam/cli/commands.py:1328-1329`
**Issue:** The safety filter matches `child.name in active_branches`. The doctor feeds `active_branches` from `state.workspace_branch`. If `workspace_branch` ever contains a slash (e.g., `"sprint/abc123"` — git branch names commonly do) and the worktree directory is named `abc123` (common `git worktree add -b sprint/abc123 abc123` idiom), the membership test returns False and the active worktree is GC'd. The current fallback (`commands.py:1326`) also adds `sprint_dir.name` on SprintState load failure, which is the sprint_id, not the branch name — so the safety net only works if the worktree is also named after the sprint_id. Worth auditing once the real workspaces path is wired (see CR-01) because the directory-naming convention under `workspaces/<team>/<agent>/` is `<agent_name>`, not `<branch_name>`, which makes the active-branch filter wholly inapplicable in its current form.

**Fix:** After resolving CR-01 (scan correct directory), reconsider the safety predicate. If the real zombie-candidate set is `workspaces/<team>/<agent_name>/`, then the safety filter should be `active_agents` (from the live WorkspaceRegistry), not `active_branches`. This is the same "preserve in-flight work" intent but applied to the correct identifier.

---

_Reviewed: 2026-04-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
