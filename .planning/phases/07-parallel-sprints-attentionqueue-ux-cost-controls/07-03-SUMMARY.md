---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 03
subsystem: attention-queue
tags:
  - attention-queue
  - stateless-read-side
  - watchdog-optional
  - digest
  - wave-2
dependency-graph:
  requires:
    - 07-01 (Wave 0 substrate: clawteam/attention package marker + AttentionConfig sub-block)
    - clawteam/team/envelope.parse_frontmatter (Phase 2)
    - clawteam/team/models.get_data_dir (Phase 1)
  provides:
    - AttentionItem frozen dataclass (10 fields)
    - AttentionQueue stateless cross-sprint priority queue
    - compute_priority pure function (D-05 formula)
    - URGENCY_MAP constant (critical=3/high=2/normal=1/low=0)
    - watchdog_available() feature detector (D-06 no-top-level-import invariant)
    - AttentionWatcher + make_watcher factory (auto/polling/watchdog modes)
    - build_digest + bucket_age cluster roll-up (D-07)
  affects:
    - 07-04 (will wire `clawteam attend` CLI over AttentionQueue.snapshot + build_digest + make_watcher)
tech-stack:
  added: []
  patterns:
    - "Stateless read-side: filesystem IS the ledger — each snapshot() globs fresh"
    - "find_spec-only feature detection (matches Phase 6 playwright_available precedent)"
    - "Module-namespace lookup for monkeypatch testability (clawteam.attention.watcher.watchdog_available)"
    - "Plain-dict cluster output (JSON-friendly without custom encoders)"
    - "Diff-on-snapshot polling with round(age_hours, 3) digest to avoid drift-spam"
key-files:
  created:
    - path: clawteam/attention/queue.py
      description: "AttentionItem + AttentionQueue + compute_priority + URGENCY_MAP (184 LOC)"
    - path: clawteam/attention/watcher.py
      description: "watchdog_available + AttentionWatcher + make_watcher (173 LOC)"
    - path: clawteam/attention/digest.py
      description: "build_digest + bucket_age (84 LOC)"
    - path: tests/attention/__init__.py
      description: "Test package marker"
    - path: tests/attention/test_queue_ranking.py
      description: "10 ranking tests incl. D-15 adversarial fixture (156 LOC)"
    - path: tests/attention/test_watcher.py
      description: "7 watcher tests incl. no-top-level-import invariant (131 LOC)"
    - path: tests/attention/test_digest.py
      description: "9 cluster roll-up tests (127 LOC)"
  modified:
    - path: clawteam/attention/__init__.py
      description: "Re-export full public API (9 symbols) — was empty marker from 07-01"
decisions:
  - "Priority formula implemented as pure function compute_priority() — decouples from AttentionQueue so CLI and tests can compute scores without filesystem"
  - "URGENCY_MAP at module level (not hidden in AttentionQueue) — unknown urgency strings silently fall back to 'normal' via dict.get default"
  - "AttentionQueue.data_dir exposed as property — watcher needs the teams/ root for watchdog schedule() call"
  - "AttentionWatcher constructor resolves 'auto' mode via module-namespace lookup (import clawteam.attention.watcher as _self_mod) so monkeypatch.setattr on watchdog_available actually takes effect — bare call would bind the symbol at import time"
  - "Polling digest rounds age_hours to 0.001h (3.6 seconds) so drift doesn't re-fire callback every poll cycle"
  - "build_digest returns plain list[dict] not dataclass — 07-04 --json flag will serialize without custom encoders"
  - "Representative title = highest-priority item in cluster (not first encountered) — reflects the question the user should actually look at"
  - "bucket_age uses half-open right boundaries (< comparisons) so age==1.0 → '1-2h', age==2.0 → '2-8h', age==8.0 → '>8h'"
metrics:
  duration: 18min
  completed: 2026-04-22
  tasks: 3
  files: 8 created / 1 modified
  tests: 26 new (all green)
  loc: ~895 total (441 production / 414 test / 40 init)
  commits: 6 (3 RED + 3 GREEN, strict TDD gates preserved)
---

# Phase 7 Plan 07-03: AttentionQueue Package Summary

Wave 2 — cross-sprint stateless read-side priority queue at `clawteam/attention/`. Ships the substrate that Plan 07-04's `clawteam attend` CLI will surface.

## One-liner

Stateless AttentionQueue globbing teams/*/sprints/*/questions/*.md with D-05 priority formula (urgency×weight + blocking? + age_hours + tag_weights), optional-extra watchdog auto-refresh with polling fallback, and build_digest cluster roll-up grouping by (sprint, tag, age bucket).

## What Was Built

### Task 1 — AttentionItem + compute_priority + AttentionQueue (commits 6669ad5 RED → e2402b3 GREEN)

- **`AttentionItem`** (clawteam/attention/queue.py L29-47): Frozen dataclass with 10 fields (question_path / sprint_id / team / title / urgency / blocking / age_hours / tags / reversibility / priority_score) + `question_id` property derived from path stem.
- **`compute_priority(urgency, blocking, age_hours, tags, *, urgency_weight=10, blocking_weight=5, tag_weights=None)`** (L50-75): Pure function implementing D-05 formula. Decoupled from queue so CLI and tests can score without filesystem.
- **`URGENCY_MAP`** (L20-25): `{critical:3, high:2, normal:1, low:0}`. Unknown strings fall back to `normal` via `URGENCY_MAP.get(urgency_str, URGENCY_MAP["normal"])`.
- **`AttentionQueue`** (L78-183): Stateless cross-sprint queue.
  - `__init__` takes `data_dir` override + CONTEXT-default priority weights + `now_fn` injection seam for age-hours testing.
  - `snapshot(limit=None) -> list[AttentionItem]`: Globs `teams/*/sprints/*/questions/*.md`, skips those with sibling `answers/<qid>.md`, parses frontmatter via Phase 2 `parse_frontmatter`, computes priority, sorts descending.
  - `_parse_question`: Derives team + sprint_id from path structure. Handles missing frontmatter (returns defaults urgency=normal / blocking=False). Handles str-typed `tags` field (wraps as single-element list). Handles OSError on read/stat (skips cleanly).
  - `for_current_user()` class constructor reserved for Plan 07-04 gstack.toml wiring.
- **10 ranking tests** (tests/attention/test_queue_ranking.py) including **D-15 adversarial fixture** `test_critical_at_30s_outranks_normal_at_8h`: critical@30s scores ≈30.008 > normal@8h scores 18.0 — proves bug-for-bug correctness of the formula.

### Task 2 — AttentionWatcher + watchdog_available (commits f89b844 RED → 8901a80 GREEN)

- **`watchdog_available()`** (clawteam/attention/watcher.py L21-28): Uses `importlib.util.find_spec("watchdog")` — zero import-time side effects. Mirrors Phase 6 `playwright_available()` pattern exactly.
- **`AttentionWatcher`** (L31-145): Two modes — `'watchdog'` (low-latency FS events) or `'polling'` (interval-driven snapshot diff). `mode='auto'` resolves via module-namespace lookup so tests can `monkeypatch.setattr("clawteam.attention.watcher.watchdog_available", lambda: True/False)` and the constructor sees the patch.
  - Polling loop digests snapshots by `(path, round(age_hours, 3))` — identical snapshots don't re-fire the callback, but drift past ~3.6s does.
  - `start()` / `stop()` idempotent. `stop()` sets stop event, joins observer + thread with 2s timeout.
  - Callbacks that raise are logged and swallowed — one bad callback can't tank the watcher.
  - Watchdog branch imports `from watchdog.observers import Observer` ONLY inside `_start_watchdog()` — confirmed by `test_no_top_level_watchdog_import`.
- **`make_watcher(queue, on_change, *, interval_seconds=2.0)`** factory: Auto-picks watchdog if available; else polling.
- **7 watcher tests** including:
  - `test_no_top_level_watchdog_import` — D-06 invariant lock.
  - `test_polling_watcher_fires_callback_on_change` — writes 2 questions over ~0.5s with 0.05s poll interval; asserts max observed len ≥ 2.
  - `test_polling_emits_on_answer_resolution` — writes question then answer; asserts callback saw both the size=1 and size=0 snapshots.
  - `test_factory_prefers_watchdog_when_available` + `test_factory_falls_back_to_polling` — monkeypatch symmetric pair.

### Task 3 — build_digest + bucket_age (commits a04026f RED → 5c33eec GREEN)

- **`bucket_age(age_hours) -> str`** (clawteam/attention/digest.py L17-28): Half-open right boundaries — `<1h | 1-2h | 2-8h | >8h`. Tested at 8 boundary points (0.0, 0.999, 1.0, 1.9, 2.0, 7.9, 8.0, 100.0).
- **`build_digest(items) -> list[dict]`** (L31-80): Groups by `(sprint_id, tag_cluster, age_bucket)` tuple key where `tag_cluster = item.tags[0] if item.tags else "untagged"`. Each cluster dict contains:
  - `sprint_id`, `tag`, `age_bucket`, `count` (len of items in cluster)
  - `highest_priority` (max score in cluster) — drives top-level sort descending
  - `representative_title` (title of the highest-priority item — what the user should actually look at)
  - `reversibility_distribution` (`{'easy': N, 'medium': N, 'hard': N}` counts for the cluster)
- Empty input returns `[]` (not None) — caller-safe for JSON serialization.
- **`__init__.py` re-exports 9 public symbols** so `from clawteam.attention import AttentionQueue, build_digest, make_watcher, watchdog_available` works for Plan 07-04's CLI wiring.
- **9 digest tests** covering boundaries, empty, grouping by sprint+tag, sort-desc, age-bucket splits, untagged fallback, count + representative_title, reversibility distribution, and full schema shape.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] AttentionWatcher `auto` mode resolved watchdog_available at import time**
- **Found during:** Task 2 initial GREEN run.
- **Issue:** `test_factory_prefers_watchdog_when_available` failed with `assert 'polling' == 'watchdog'`. The constructor's direct call `mode = "watchdog" if watchdog_available() else "polling"` binds the module-level function reference at the first `from clawteam.attention.watcher import watchdog_available` time. Subsequent `monkeypatch.setattr("clawteam.attention.watcher.watchdog_available", lambda: True)` rebinds the module attribute but the constructor's closure still points to the original function.
- **Fix:** Inline `import clawteam.attention.watcher as _self_mod` inside `__init__` and `start()`, call `_self_mod.watchdog_available()`. This forces each call to go through the module namespace so monkeypatched symbols take effect.
- **Files modified:** clawteam/attention/watcher.py (two import sites).
- **Commit:** 8901a80 (folded into Task 2 GREEN — this is the pattern change that made the GREEN gate actually pass).

**No other deviations.** Plan executed essentially as written; all 3 task acceptance criteria met.

## Threat Flags

None — the attention substrate is pure read-side: no new network endpoints, no new auth paths, no new file-write surface (the question.md / answers/<qid>.md writers live in Phase 2 InteractionGate and earlier). Plan 07-04's CLI will be the first write point (`clawteam attend` exit codes + STDOUT only).

## Self-Check: PASSED

Verified:
- [x] `clawteam/attention/queue.py` exists (184 LOC, grep matches `class AttentionItem` / `def compute_priority` / `class AttentionQueue`)
- [x] `clawteam/attention/watcher.py` exists (173 LOC, grep matches `def watchdog_available` / `class AttentionWatcher`, no top-level `import watchdog`)
- [x] `clawteam/attention/digest.py` exists (84 LOC, grep matches `def build_digest` / `def bucket_age`)
- [x] `tests/attention/test_queue_ranking.py` exists (10 tests green)
- [x] `tests/attention/test_watcher.py` exists (7 tests green)
- [x] `tests/attention/test_digest.py` exists (9 tests green)
- [x] Commit 6669ad5 (Task 1 RED) present in `git log`
- [x] Commit e2402b3 (Task 1 GREEN) present in `git log`
- [x] Commit f89b844 (Task 2 RED) present in `git log`
- [x] Commit 8901a80 (Task 2 GREEN) present in `git log`
- [x] Commit a04026f (Task 3 RED) present in `git log`
- [x] Commit 5c33eec (Task 3 GREEN) present in `git log`
- [x] `pytest tests/attention/ -q` → 26 passed
- [x] `python -c "from clawteam.attention import AttentionQueue, build_digest, make_watcher, watchdog_available; print('ok')"` → ok
- [x] 70 Phase 7 tests (Waves 0-2) all green (attention + rate_limit + event_types_phase7 + template_def_phase7_blocks + sprint_state_queue_status)

## TDD Gate Compliance

All 3 tasks followed strict RED → GREEN cycle:

| Task | RED commit | GREEN commit | Delta |
|------|------------|--------------|-------|
| 1 (queue)   | 6669ad5 | e2402b3 | 10 tests → 10 pass |
| 2 (watcher) | f89b844 | 8901a80 | 7 tests → 7 pass   |
| 3 (digest)  | a04026f | 5c33eec | 9 tests → 9 pass   |

All RED commits verified to fail with `ModuleNotFoundError` (production file absent) before corresponding GREEN commit landed.

## Next

**07-04** (Wave 2 sibling — CLI):
- Wire `clawteam attend` Typer command over `AttentionQueue.snapshot()` + `build_digest()` + `make_watcher()`.
- Load `AttentionConfig` from `gstack.toml` (via TemplateDef sub-block landed in 07-01).
- Implement `AttentionQueue.for_current_user()` to pull priority weights from loaded config.
- Add `--summary` flag (call `build_digest`) and `--watch` flag (call `make_watcher`).
