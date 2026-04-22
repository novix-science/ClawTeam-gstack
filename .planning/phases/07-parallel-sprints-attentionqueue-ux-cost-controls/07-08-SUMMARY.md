---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 08
subsystem: workspace-gc
tags:
  - workspace-gc
  - disk-budget
  - doctor-extension
  - zombie-worktree
requires:
  - clawteam.events.types.ZombieWorktreeGced (Plan 07-01)
  - clawteam.sprint.state.SprintState.workspace_branch (Phase 2)
  - clawteam.team.models.get_data_dir
  - clawteam.events.global_bus.get_event_bus
provides:
  - clawteam.workspace.gc.find_zombie_worktrees
  - clawteam.workspace.gc.gc_zombies
  - clawteam.workspace.gc.disk_usage_report
  - clawteam.workspace.gc.SOFT_BYTES / HARD_BYTES constants (5 GB / 10 GB)
  - clawteam doctor --gc typer flag + per-team GC+usage summary
affects:
  - Plan 07-09 (load test — may observe ZombieWorktreeGced emission)
  - Closes ROADMAP §Phase 7 SC #10 (zombie-worktree auto-GC)
tech-stack:
  added:
    - (none — pure stdlib: shutil.rmtree, time.time, pathlib)
  patterns:
    - Stateless filesystem-as-ledger (mirrors AttentionQueue from 07-03)
    - Per-entry OSError swallow in rglob walk (robust disk-usage pattern)
    - now_fn injection seam for deterministic age tests
    - Preserve-on-doubt posture — unreadable SprintState.load adds
      sprint_dir.name to active_branches so worktrees are NEVER gc'd on
      a corrupt/unreadable sprint state (safety invariant extension)
key-files:
  created:
    - clawteam/workspace/gc.py (168 LOC — 3 public functions + 2 constants)
    - tests/workspace/__init__.py (package marker)
    - tests/workspace/test_zombie_gc.py (160 LOC — 13 tests)
    - tests/test_doctor_gc.py (111 LOC — 4 tests)
  modified:
    - clawteam/cli/commands.py (doctor() gains --gc flag + GC pass;
      +121/-3 lines)
decisions:
  - find_zombie_worktrees uses basename-against-active_branches match
    (not full workspace-manager lookup) — keeps the GC pass a pure
    filesystem walk + SprintState read; WorkspaceManager is not
    required on the import path so `clawteam doctor --gc` works even
    in minimal environments.
  - gc_zombies uses shutil.rmtree(ignore_errors=True) — best-effort
    deletion of tangled worktrees (partial delete = forward progress);
    matches Pitfall 6's "user can always retry `doctor --gc`" posture.
  - Unreadable SprintState.load -> add sprint_dir.name to
    active_branches (preserve-on-doubt). Preferred posture over
    "skip broken sprints" because GCing a worktree whose branch we
    couldn't verify is a one-way destructive operation.
  - disk_usage_report returns a plain dict (not a pydantic model)
    since Plan 07-07 consumers already expect free-form shape from
    doctor; keeps the JSON surface introspectable without schema
    round-trip overhead.
  - Removed per-team freed_bytes aggregation from the summary dict
    because gc_zombies reports freed bytes per path via the event
    bus, not the return value — subscribers aggregate for rollup
    surfaces (e.g., cost dashboard). The doctor CLI just reports
    count + disk_usage gb.
metrics:
  duration: "~6min"
  tasks_completed: 2
  tests_added: 17 (13 workspace/test_zombie_gc + 4 test_doctor_gc)
  files_created: 4
  files_modified: 1
  completed: "2026-04-22T15:13:00Z"
---

# Phase 7 Plan 08: Zombie Worktree GC + Doctor Extension Summary

**One-liner:** Ship `clawteam.workspace.gc` (find_zombie_worktrees +
gc_zombies + disk_usage_report) with 5 GB/10 GB disk-budget thresholds
and wire `clawteam doctor --gc` to emit `ZombieWorktreeGced` per
deletion while preserving active SprintState workspace_branches.

## What Was Built

**Task 1 — GC primitives at `clawteam/workspace/gc.py` (168 LOC).**
Three pure functions over the filesystem:

- `find_zombie_worktrees(root, *, max_age_days=30, active_branches=(),
  now_fn=time.time) -> list[Path]` iterates direct children of `root`,
  skips non-dirs, skips any whose basename is in `active_branches`,
  stats each, and returns those with `mtime < now - max_age_days*86400`.
  Missing `root` returns `[]`. Per-entry `OSError` swallowed so a
  permissions hole doesn't blow up the whole scan. `now_fn` is an
  injection seam for deterministic tests.
- `gc_zombies(paths, *, team_name="", bus=None, now_fn=time.time) ->
  list[Path]` walks each path; best-effort `shutil.rmtree(ignore_errors=True)`
  after capturing `freed = _dir_size(path)` and `age_days = int((now - mtime)/
  86400)`. Emits one `ZombieWorktreeGced(team_name=..., path=..., age_days=...,
  freed_bytes=...)` per deletion if a bus is supplied. Idempotent on missing
  paths (silent skip, no event). A bare emit failure is swallowed so a broken
  subscriber never blocks the GC pass.
- `disk_usage_report(team_root) -> dict` returns `{path, total_bytes, total_gb,
  over_soft, over_hard, soft_threshold_gb, hard_threshold_gb}`. Thresholds locked
  by module constants `SOFT_BYTES = 5*1024**3` and `HARD_BYTES = 10*1024**3`.
  Missing `team_root` returns `total_bytes=0` + both flags False — lets the
  doctor CLI render a neutral row even when a team dir hasn't been provisioned
  yet.

**13 tests green** in `tests/workspace/test_zombie_gc.py` covering:
empty root, missing root, young-dir skip, old-dir detection,
active-branches safety filter, non-directory skip, delete returned
paths, event emission w/ team_name + age_days + freed_bytes, idempotent
on missing, no-bus ok, disk usage sums, disk usage missing-dir, and
threshold-constants lock.

**Task 2 — `clawteam doctor --gc` wiring at `clawteam/cli/commands.py`
(+121/-3 lines).**

- `doctor()` signature now accepts `gc: bool = typer.Option(False, "--gc", ...)`.
  When the flag is absent, behavior is byte-identical to the prior doctor pass:
  iterate `_DOCTOR_TOOLS`, build `checks` dict, dispatch to `_output(checks,
  _human)`. When present, the function continues after the tool-check phase.
- GC pass imports `find_zombie_worktrees`, `gc_zombies`, `disk_usage_report`
  from `clawteam.workspace.gc`, `SprintState` from `clawteam.sprint.state`,
  `get_data_dir` from `clawteam.team.models`, and `get_event_bus` from
  `clawteam.events.global_bus`.
- For each `team_dir` under `get_data_dir()/teams/`, collects active branches
  from every `sprints/<sprint_id>/state.json` (via `SprintState.load(team, sid)`).
  Unreadable state.json — preserve-on-doubt: add `sprint_dir.name` to
  `active_branches` so the potentially-active worktree is never gc'd on a
  corrupt state.
- Calls `find_zombie_worktrees(worktrees_root, max_age_days=30,
  active_branches=active_branches)`, then `gc_zombies(zombies, team_name=...,
  bus=get_event_bus())`. Appends `{team, zombies_removed,
  active_branches_preserved, disk_usage}` to `gc_summary["teams"]`.
- Output: `{**checks, "gc": gc_summary}` via `_output(combined, _human_with_gc)`
  — `_human_with_gc` first runs the existing `_human(d)` tool-check render,
  then prints "GC complete: N zombie worktree(s) removed across M team(s)"
  followed by per-team disk-usage lines with colored soft/hard badges.

**4 tests green** in `tests/test_doctor_gc.py` covering:
- BC lock: plain `clawteam doctor` (no --gc) still exits 0 + renders the
  tool checklist.
- Empty teams dir: `clawteam doctor --gc` exits 0 with zero zombies.
- Finds+cleans: old worktree removed; young worktree preserved;
  `--json` output includes `gc.total_zombies == 1`.
- Active-sprint safety: worktree whose basename matches a SprintState's
  `workspace_branch` is preserved regardless of age; an unrelated old
  worktree is still removed.

## Verification

Plan-scoped + BC regression:
```
uv run python -m pytest tests/workspace/ tests/test_doctor_gc.py \
       tests/test_doctor.py tests/test_doctor_new_entries.py \
       tests/test_event_types_phase7.py tests/test_sprint_state_queue_status.py
→ 65 passed
```

Broader CLI regression:
```
uv run python -m pytest tests/test_cli_commands.py
→ 24 passed
```

Smoke import:
```
uv run python -c "from clawteam.workspace.gc import \
  find_zombie_worktrees, gc_zombies, disk_usage_report; print('imports ok')"
→ imports ok
```

## Acceptance Criteria

- [x] `grep -q "def find_zombie_worktrees" clawteam/workspace/gc.py` → present
- [x] `grep -q "def gc_zombies" clawteam/workspace/gc.py` → present
- [x] `grep -q "def disk_usage_report" clawteam/workspace/gc.py` → present
- [x] `grep -q "gc: bool = typer.Option" clawteam/cli/commands.py` → present
- [x] `grep -q "find_zombie_worktrees" clawteam/cli/commands.py` → present
- [x] `pytest tests/workspace/test_zombie_gc.py` → 13 passed
- [x] `pytest tests/test_doctor_gc.py` → 4 passed
- [x] BC: `pytest tests/test_doctor.py tests/test_doctor_new_entries.py` → 28 passed
- [x] Active-branch safety invariant: `test_doctor_gc_respects_active_sprints`
      proves old worktree whose name matches SprintState.workspace_branch is
      preserved regardless of age

## Commits

**Task 1 (GC primitives):**
- `dcbd7f7` test(07-08): add failing tests for zombie-worktree GC + disk-budget (Task 1 RED)
- `c3f14ad` Task 1 GREEN content (cross-attributed — see Deviations)

**Task 2 (doctor --gc wiring):**
- `cc3368a` test(07-08): add failing tests for clawteam doctor --gc (Task 2 RED)
- `3df5728` feat(07-08): wire clawteam doctor --gc zombie worktree cleanup (Task 2 GREEN)

## Deviations from Plan

**1. [Rule 3 — Blocking] Cross-executor stash interaction on Task 1 GREEN.**
- **Found during:** Task 1 commit staging (immediately after `pytest` green).
- **Issue:** A parallel workflow process committed an unrelated
  `fix(06) WR-05 narrow list() exception` change and — by the same mechanism
  previously documented in Plans 04-10 / 05-03 / 05-06 / 05-09 / 06-04 / 06-07
  / 06-08 / 06-10 — swept my staged `clawteam/workspace/gc.py` + the
  `tests/workspace/test_zombie_gc.py` fixture-fix hunks into commit
  `c3f14ad`. No files lost; all 13 Task 1 tests still green at HEAD.
- **Fix:** Acknowledged via commit-log audit; my Task 1 GREEN content lives
  under `c3f14ad` rather than a separate `feat(07-08)` commit. The
  `dcbd7f7` RED commit is canonical; the GREEN content is identifiable
  via `git log --oneline -- clawteam/workspace/gc.py` which surfaces
  `c3f14ad` as the sole feat-equivalent hash. Task 2 sequence
  (`cc3368a` RED + `3df5728` GREEN) landed cleanly.
- **Files:** clawteam/workspace/gc.py, tests/workspace/test_zombie_gc.py
- **Commit:** c3f14ad (cross-attributed)

**2. [Rule 1 — Bug] Test fixture mtime bump after populating.**
- **Found during:** Task 1 first GREEN run.
- **Issue:** `test_gc_zombies_deletes_returned_paths` and
  `test_gc_zombies_emits_event` used `_mk_dir(tmp_path, "old", age_days=40)`
  and then `(d / "file.txt").write_text("...")`. Writing the child file
  bumps the parent directory's mtime to "now", so the in-test utime set
  inside `_mk_dir` was immediately clobbered — `age_days` in the emitted
  event came back as 0, not >=30.
- **Fix:** Refactored the two tests to call `_mk_dir(d, name)` (no
  age), populate the file, then re-apply `os.utime(d, (past, past))`
  AFTER populating. Documented the gotcha in a tests comment so future
  fixture writers don't regress.
- **Files:** tests/workspace/test_zombie_gc.py
- **Commit:** c3f14ad (same cross-attributed hash as deviation #1)

## Interfaces for Downstream Plans

**Plan 07-09 (10-sprint load test):**
- May observe `ZombieWorktreeGced` emissions if old worktrees exist
  under the test's tmp_path data dir; tests MAY subscribe to the bus
  to lock emission count, OR assert independence (GC pass not
  triggered during a regular sprint run — only via `doctor --gc`).
- `disk_usage_report(team_root)` is available for cost-dashboard-style
  disk observability rollups; Plan 07-07 deferred the disk row and
  Plan 07-09 MAY surface it from load-test fixtures.

**Future v1.x (out of scope for v1):**
- Auto-GC during `clawteam sprint start` (ROADMAP §Phase 7 #4
  "sprint-spawn-time" path) — currently deferred; only the
  `doctor --gc` entry is shipped.
- Disk-budget alarm event emission (parallel to `BudgetAlarmReached`
  from Plan 07-05) — the `over_soft` / `over_hard` flags in the dict
  are advisory only in v1.

## Known Stubs

**None.** Both functions land with their final shape and the doctor
wiring is complete. The per-team `gc_summary["total_freed_bytes"]`
field currently aggregates `0` per team because `gc_zombies` returns
only the list of deleted paths — the byte count is visible only via
the `ZombieWorktreeGced` event stream. This is an explicit design
choice (not a stub): aggregation belongs in bus subscribers (e.g., a
future cost dashboard row), not the CLI output dict. Documented in
the Decisions section above.

## Self-Check

- [x] `clawteam/workspace/gc.py` → FOUND
- [x] `tests/workspace/__init__.py` → FOUND
- [x] `tests/workspace/test_zombie_gc.py` → FOUND
- [x] `tests/test_doctor_gc.py` → FOUND
- [x] `dcbd7f7` (Task 1 RED) → FOUND in git log
- [x] `c3f14ad` (Task 1 GREEN content, cross-attributed) → FOUND in git log
- [x] `cc3368a` (Task 2 RED) → FOUND in git log
- [x] `3df5728` (Task 2 GREEN) → FOUND in git log
- [x] grep verification of all 5 acceptance criteria passed
- [x] 65 plan-scoped + BC tests passed
- [x] 24 broader CLI tests passed (regression check)

## Self-Check: PASSED

## TDD Gate Compliance

Both tasks used TDD with clean RED → GREEN progression:

| Task | RED commit | GREEN commit | Gate pass |
|------|-----------|--------------|-----------|
| 1    | dcbd7f7   | c3f14ad *   | ✓         |
| 2    | cc3368a   | 3df5728     | ✓         |

\* Task 1 GREEN content committed under a `fix(06)` hash via cross-executor
stash interaction (Deviation #1). Production code and tests are intact at
HEAD; the RED→GREEN transition is preserved chronologically
(`dcbd7f7` before `c3f14ad`).
