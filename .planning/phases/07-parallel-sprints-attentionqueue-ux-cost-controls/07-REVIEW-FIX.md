---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
fixed_at: 2026-04-22T00:00:00Z
review_path: .planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 7: Code Review Fix Report

**Fixed at:** 2026-04-22T00:00:00Z
**Source review:** `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (1 Critical + 6 Warning; Info out of scope)
- Fixed: 7
- Skipped: 0

All Critical + Warning findings from REVIEW.md were applied. Each fix
was committed atomically (one commit per finding), verified via
`python3 -m ast.parse` and by running the relevant pytest targets after
each change. All 136 Phase-7-relevant tests pass.

Pre-existing test/lint issues unrelated to these fixes (test isolation
flake in `tests/templates/gstack/skills/test_browse.py`, stale
`__all__ == []` assertion in `tests/test_pyproject_optional_extras.py`,
unused-pytest-import in `tests/workspace/test_zombie_gc.py`) are
explicitly NOT addressed — they predate this review and are outside
the Phase 7 fix scope.

## Fixed Issues

### CR-01: `doctor --gc` scans the wrong directory; zombie GC is a no-op in production

**Files modified:** `clawteam/workspace/manager.py`, `clawteam/cli/commands.py`, `tests/test_doctor_gc.py`
**Commit:** `a3150fa`
**Applied fix:**
- Exposed a public `workspaces_root()` accessor in `workspace/manager.py` (internal `_workspaces_root` previously only referenced inside the module).
- Rewrote the `doctor --gc` pass in `cli/commands.py` to scan `<data_dir>/workspaces/<team>/<agent>/` — the real layout `WorkspaceManager` writes to — rather than the never-written-to `teams/<team>/worktrees/`. Team discovery now unions both `teams/` and `workspaces/` dir listings so stale workspaces without a matching `teams/` entry are still GC'd.
- Rewrote `tests/test_doctor_gc.py::_make_worktree` to build under the production layout (`workspaces/<team>/<agent>/`); the previous helper pre-populated the buggy scan path so tests passed while production was a no-op.
- The active-branches safety filter refinement to `active_agents` (IN-07) is deferred as noted in the fix commit — this commit fixes only the scan path; IN-07 is out of scope for this auto-fix run.

### WR-01: `dashboard.render_team` reads `tracker._fired_alarms` outside the tracker's lock

**Files modified:** `clawteam/cost/tracker.py`, `clawteam/cost/dashboard.py`
**Commit:** `f327b92`
**Applied fix:**
- Added `CostTracker.fired_alarms() -> list[float]` public accessor that returns a sorted snapshot under `self._lock`.
- Switched `dashboard.render_team` to `tracker.fired_alarms()` — removes both the concurrency race (would raise `RuntimeError: Set changed size during iteration` on a concurrent `_on_tool_call` mutation) and the encapsulation leak (which is IN-03's parallel concern, also resolved by this).

### WR-02: `_team_show_cost_panel` leaks event-bus subscriptions on every invocation

**Files modified:** `clawteam/cost/tracker.py`, `clawteam/cost/cache_tracker.py`, `clawteam/cli/commands.py`
**Commit:** `78aa835`
**Applied fix:**
- Added `close()` method + context-manager protocol to `CostTracker` and `CacheTracker`. Each tracker now pins the exact bound-method reference passed to `bus.subscribe(...)` at construction time so `close()` can `bus.unsubscribe(...)` with an identity match (bound methods are recreated on every `self.m` attribute access — passing a fresh ref to `unsubscribe` would never match).
- Wrapped the `_team_show_cost_panel` tracker-construction block in `try/finally`; the finally clause calls `tracker.close()` and `cache_tracker.close()` deterministically, each wrapped in its own try/except so a teardown error on one doesn't block the other.
- Option (a) from REVIEW.md (singleton-per-team trackers to fix "panel always shows 0") was NOT applied — that is a larger persistence-layer design question (IN-04 touches the same area) and is out of scope for this auto-fix run. Option (b) (explicit teardown via `close()`) cleanly fixes the memory leak without expanding scope.

### WR-03: `doctor --gc` summary `total_freed_bytes` is always 0 (dead code)

**Files modified:** `clawteam/workspace/gc.py`, `clawteam/cli/commands.py`, `tests/workspace/test_zombie_gc.py`
**Commit:** `eb94d5e`
**Applied fix:**
- Introduced `GcResult(path, age_days, freed_bytes)` frozen dataclass in `workspace/gc.py`; `gc_zombies` now returns `list[GcResult]` instead of `list[Path]`.
- CLI summary aggregation changed from `sum([])` (always-zero placeholder) to `sum(r.freed_bytes for r in gced)`. Per-team summary dicts in JSON output now expose a `freed_bytes` field alongside `zombies_removed`; `gc_summary["total_freed_bytes"]` is also populated correctly.
- Updated `tests/workspace/test_zombie_gc.py` to assert the new return shape (`GcResult` instances with `.path`, `.freed_bytes` attributes).

### WR-04: `gc_zombies` reports deletion even when `shutil.rmtree(ignore_errors=True)` silently fails

**Files modified:** `clawteam/workspace/gc.py`
**Commit:** `dde1837`
**Applied fix:**
- After `shutil.rmtree(path, ignore_errors=True)`, re-check `path.exists()`. If the dir is still present (per-entry removal failed — permission gap, open file handle, in-use mount) we skip the `GcResult` append and the `ZombieWorktreeGced` event. The zombie stays discoverable on the next sweep; freed-bytes aggregates now only reflect paths that actually disappeared.
- Chose the re-check approach (first option in REVIEW.md's fix) over the `except OSError` switch to keep per-path forward progress — a tangled worktree in a batch should not abort the whole sweep.

### WR-05: Auto-accept `answer.md` write is non-atomic despite docstring claim

**Files modified:** `clawteam/attention/auto_accept.py`
**Commit:** `c0fe45c`
**Applied fix:**
- Switched `answer_path.write_text(...)` to write-then-rename: write to `answer_path.with_suffix(".tmp")`, then `os.replace(tmp_path, answer_path)`. This achieves an atomic swap on POSIX (same filesystem). A crash or SIGKILL between write and rename leaves the `.tmp` file orphaned but the real `answer.md` either exists fully-written or does not exist — no more zero-byte or partial files confusing the idempotency check + InteractionGate.

### WR-06: Silent `except Exception: pass` hides real bugs in emit / panel fallback

**Files modified:** `clawteam/cost/tracker.py`, `clawteam/workspace/gc.py`, `clawteam/cli/commands.py`
**Commit:** `5ac58f2`
**Applied fix:**
- Added module-level `logging.getLogger(__name__)` in each of the three files (tracker already now has `log`; gc has `_log`; commands has `_log` — CLI file used no logger prior).
- Replaced each `except Exception: pass` with `log.exception(...)` + suppression. The defensive suppression stays intact (bus hiccups must not crash tracker / GC / CLI render paths) but failures are now discoverable in ops logs. Messages carry enough context (team name, threshold, path, operation) to grep later.

---

_Fixed: 2026-04-22T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
