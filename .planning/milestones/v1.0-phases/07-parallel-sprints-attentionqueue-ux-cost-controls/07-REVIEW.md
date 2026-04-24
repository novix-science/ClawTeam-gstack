---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
reviewed: 2026-04-23T00:00:00Z
depth: standard
iteration: 3
prior_review: .planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-REVIEW.iter2.md
prior_fix: .planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-REVIEW-FIX.iter2.md
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
  - clawteam/workspace/manager.py
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
verified_fix_commits:
  - a3150fa
  - f327b92
  - 78aa835
  - eb94d5e
  - dde1837
  - c0fe45c
  - 5ac58f2
findings:
  critical: 0
  warning: 0
  info: 2
  total: 2
status: clean
---

# Phase 7: Code Review Report (Iteration 3)

**Reviewed:** 2026-04-23T00:00:00Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** clean (no Critical or Warning findings)

## Summary

Re-review after the 7 Critical+Warning fixes from
`07-REVIEW.iter2.md` landed as atomic commits
(`a3150fa..5ac58f2`). Each fix was verified against the previously
flagged failure mode and the adjacent surface was spot-checked for
regressions introduced by the fix commits themselves. All 130
Phase-7-relevant tests pass (tests/workspace/,
tests/test_doctor_gc.py, tests/cost/, tests/attention/,
tests/test_team_show_cost_panel.py, tests/integration/test_phase7_*).

Net result: 1 Critical + 6 Warning -> 0 Critical + 0 Warning.
Two new Info-level observations about the fixes themselves (neither a
regression — both are low-severity trade-offs inherited from the
chosen fix approach). The original 7 Info items from iter2 are
unchanged and out of scope for this iteration.

## Verification of Prior Findings

### CR-01 (doctor --gc scans wrong directory) — RESOLVED (commit a3150fa)

- `clawteam/workspace/manager.py:26-37` adds public `workspaces_root()`
  accessor matching `_workspaces_root()`.
- `clawteam/cli/commands.py:1294,1297,1313-1316,1327` now scans
  `<data_dir>/workspaces/<team>/` (the real WorkspaceManager layout),
  unions team names from both `teams/` and `workspaces/`, and skips a
  team when its workspaces subdir doesn't exist.
- `tests/test_doctor_gc.py:27-43` rewrote `_make_worktree` to build
  under `workspaces/<team>/<name>/` — the real layout — so tests now
  exercise the shipped code path rather than a parallel universe.
- Verified: `test_doctor_gc_finds_and_cleans` creates a zombie under
  `workspaces/t1/old-branch/` and the GC pass finds it
  (total_zombies == 1, young worktree preserved).

### WR-01 (`dashboard.render_team` reads `_fired_alarms` outside lock) — RESOLVED (commit f327b92)

- `clawteam/cost/tracker.py:119-128` adds `fired_alarms()` public
  accessor that snapshots `_fired_alarms` under `self._lock`.
- `clawteam/cost/dashboard.py:67` switched from
  `sorted(tracker._fired_alarms)` to `tracker.fired_alarms()`.
- Both the concurrency race and the IN-03 encapsulation leak are
  addressed by the same change.

### WR-02 (tracker subscription leak in `_team_show_cost_panel`) — RESOLVED (commit 78aa835)

- `clawteam/cost/tracker.py:80-83,130-149` and
  `clawteam/cost/cache_tracker.py:56-59,96-112` pin the bound-method
  reference at construction, add `close()` that calls
  `bus.unsubscribe(...)` with an identity match, and add
  `__enter__`/`__exit__` for context-manager use.
- `clawteam/cli/commands.py:1899-1958` wraps tracker construction in
  `try/finally`; the `finally` calls `tracker.close()` and
  `cache_tracker.close()`, each in its own inner try/except so a
  teardown error on one doesn't block the other.
- Identity match works: `EventBus.unsubscribe` (bus.py:98) uses
  `s.handler is not handler`. The stored `self._handler` is the same
  object passed to `bus.subscribe`.
- Option (a) from the original finding (singleton trackers so the
  panel shows historical spend) is explicitly NOT applied — that is
  the IN-04 "panel always shows 0" concern, which remains open.
  Option (b) (explicit teardown) is sufficient to close the
  memory-leak vector.

### WR-03 (doctor --gc `total_freed_bytes` always 0) — RESOLVED (commit eb94d5e)

- `clawteam/workspace/gc.py:43-55` introduces `GcResult(path,
  age_days, freed_bytes)` frozen dataclass.
- `gc_zombies` now returns `list[GcResult]` (line 123).
- `clawteam/cli/commands.py:1371` computes `team_freed =
  sum(r.freed_bytes for r in gced)`, and the per-team JSON dict
  includes `freed_bytes` alongside `zombies_removed`.
- `tests/workspace/test_zombie_gc.py:96-100,136` asserts the new
  shape.
- Verified: `gced[0].freed_bytes >= 7` for a 7-byte file.

### WR-04 (rmtree silent partial-failure false-positive) — RESOLVED (commit dde1837)

- `clawteam/workspace/gc.py:156-157` re-checks `path.exists()` after
  `shutil.rmtree(ignore_errors=True)` and skips the `GcResult` +
  `ZombieWorktreeGced` append when the dir is still present.
- The comment at lines 153-155 explicitly calls out the WR-04
  rationale.
- Chosen approach: re-check (not `except OSError`), preserving
  per-path forward progress — a tangled worktree in a batch does not
  abort the whole sweep.

### WR-05 (non-atomic `answer.md` write) — RESOLVED (commit c0fe45c)

- `clawteam/attention/auto_accept.py:93-95` switched to
  write-then-rename: writes to
  `answer_path.with_suffix(answer_path.suffix + ".tmp")`, then
  `os.replace(tmp_path, answer_path)`. `os.replace` is atomic on
  POSIX within the same filesystem.
- Answer files always end in `.md` (line 64 uses
  `item.question_path.name` which is `{qid}.md`), so the tmp suffix
  is always `.md.tmp` — no NULL-suffix edge case in production.
- Crash between write and rename leaves `.tmp` orphaned but
  `answer.md` is either fully present or absent — the idempotency
  check (`answer_path.exists()`) is now reliable.

### WR-06 (silent `except Exception: pass` in 3 sites) — RESOLVED (commit 5ac58f2)

- `clawteam/cost/tracker.py:34,219-232` adds module-level `log =
  logging.getLogger(__name__)` and replaces `pass` with
  `log.exception(...)` carrying team + threshold.
- `clawteam/workspace/gc.py:40,170-177` adds `_log` and replaces
  `pass` with `_log.exception(...)` carrying the path.
- `clawteam/cli/commands.py:23,1959-1965` — module-level `_log`
  already existed at line 23; the `_team_show_cost_panel` outer catch
  now calls `_log.exception("cost panel failed, falling back to
  'unavailable'")` before returning the neutral fallback dict.
- Defensive suppression retained in all three sites — the semantic
  fix is observability, not failing-loudly.

## Spot Checks for Regressions Introduced by Fix Commits

Scanned the fix-commit diffs for new classes of issues:

- **Identity-match subscription (78aa835):** Verified
  `EventBus.unsubscribe` uses `is not handler` semantics and tracker
  constructors pin a single bound-method ref. Calling `close()` a
  second time is a no-op (the `is not None` guard covers it).
- **`GcResult` `__all__` export (eb94d5e):** `GcResult` added to
  `__all__` in `workspace/gc.py:205-212`. External consumers can
  import it.
- **Atomic `answer.md` rename (c0fe45c):** `os.replace` performs
  atomic rename on both POSIX and NTFS. No platform regression.
- **`log.exception` level (5ac58f2):** Using the default
  `log.exception` (ERROR level) means these messages appear in most
  CLI harnesses. For defensive-fallback paths (bus emit failures
  during shutdown) this is the correct choice — operators running
  production need to see schema regressions, and debug-level would
  hide them.
- **Commands.py logger name collision:** Module-level `_log =
  logging.getLogger(__name__)` at line 23 is re-imported and
  re-declared inside `_invoke_learn` at lines 5989-5993. The inner
  re-declaration is harmless (same name, same logger object) but
  untidy. Pre-existing, not introduced by this fix cycle.

## Info (New observations from fix commits)

### IN-08: `workspaces_root()` has a filesystem side-effect (directory creation)

**File:** `clawteam/workspace/manager.py:19-37`, called by
`clawteam/cli/commands.py:1297`
**Issue:** The public accessor `workspaces_root()` delegates to
`_workspaces_root()`, which unconditionally runs `p.mkdir(parents=True,
exist_ok=True)` on line 22. As a result, every `clawteam doctor --gc`
invocation on a fresh install (no workspaces yet) silently creates an
empty `<data_dir>/workspaces/` dir as a side effect of the scan. The
name `workspaces_root()` suggests a pure accessor; creating dirs from
a query is a mild surprise and makes the `workspaces_top.is_dir()`
guard at `commands.py:1313` effectively dead code (the dir was just
created).

Not a bug per se — mkdir is harmless on repeat — but the API contract
is muddled.

**Fix:** Split into two functions:

```python
def workspaces_root() -> Path:
    from clawteam.team.models import get_data_dir
    return get_data_dir() / "workspaces"  # pure

def ensure_workspaces_root() -> Path:
    p = workspaces_root()
    p.mkdir(parents=True, exist_ok=True)
    return p
```

Write-path methods (`create_workspace`, `_save_registry`,
`_registry_path`) call `ensure_workspaces_root()`; the doctor GC scan
and other read-only query sites call the pure `workspaces_root()`.
The `is_dir()` guard at `commands.py:1313` becomes meaningful again.

### IN-09: `_team_show_cost_panel` teardown has two nested `try/except: pass` shells

**File:** `clawteam/cli/commands.py:1944-1958`
**Issue:** The teardown block is:

```python
finally:
    try:
        tracker.close()
    except Exception:
        pass
    try:
        cache_tracker.close()
    except Exception:
        pass
```

Both inner `except: pass` blocks are silent swallows — the exact
pattern WR-06 flagged as a code-quality issue in three adjacent
sites in this same commit cycle. The defensive intent is correct (a
teardown error on tracker-A must not block tracker-B's teardown) but
the outer swallowed-exception was addressed with `log.exception(...)`
and these inner ones should follow the same pattern for consistency.

Note: under current bus.py (lines 94-99), `unsubscribe` cannot raise
— the method is a pure list-comprehension rebuild. So the try/except
shells are future-proofing only. Still, the WR-06 precedent says
"log before swallowing."

**Fix:** Match WR-06's pattern:

```python
finally:
    try:
        tracker.close()
    except Exception:
        _log.exception("tracker.close() failed during team-show teardown")
    try:
        cache_tracker.close()
    except Exception:
        _log.exception("cache_tracker.close() failed during team-show teardown")
```

Or remove the try/except entirely (current `close()` cannot raise)
and accept that a future bus regression would surface. Either choice
is better than silent swallow.

---

## Test Verification

All Phase-7 tests pass under the post-fix code:

```
tests/workspace/test_zombie_gc.py
tests/test_doctor_gc.py
tests/cost/
tests/attention/
tests/test_team_show_cost_panel.py
tests/integration/test_phase7_attention_ranking.py
tests/integration/test_phase7_cost_dashboard.py
tests/integration/test_phase7_ten_sprint_load.py
```

130 passed in 2.49s.

## Recommendation

Phase 7 is ready to close with 0 Critical + 0 Warning findings. The
two new Info items (IN-08, IN-09) are low-severity trade-offs
inherited from the chosen fix approach and can be addressed in a
follow-up tidy pass or deferred to a later phase. The 7 pre-existing
Info items (IN-01 through IN-07) from iter2 remain open and are
unchanged by this review.

---

_Reviewed: 2026-04-23T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 3 (re-review after iter2 fix cycle)_
