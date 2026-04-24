---
phase: 06
plan: 11
subsystem: team-memory
tags: [memory, gate, conflict, backfill, MEM-06, QUALITY-10]
requires: [06-02, 06-03, 06-10, 03-09]
provides:
  - clawteam.memory.high_impact_gate.check_high_impact
  - clawteam.memory.high_impact_gate.stage_pending
  - clawteam.memory.conflict.detect_conflicts
  - clawteam.memory.conflict.ConflictMatch
  - clawteam.memory.backfill.backfill_scan
  - clawteam/templates/gstack/skills/learn/handler._ensure_backfilled
affects:
  - clawteam/templates/gstack/skills/learn/handler.py
  - .planning/REQUIREMENTS.md (MEM-06, QUALITY-10 → Complete)
tech-stack:
  added: []
  patterns:
    - "InteractionGate-consumable question artifact layout (memory-confirm-<id>.md)"
    - "Stdlib cosine-on-BoW similarity (math + re, no scikit-learn / numpy)"
    - "Per-process per-team idempotency sentinel (module-level set[str])"
    - "Best-effort non-blocking advisory events (ConflictDetected) via global bus"
key-files:
  created:
    - clawteam/memory/high_impact_gate.py
    - clawteam/memory/conflict.py
    - clawteam/memory/backfill.py
    - tests/memory/test_high_impact_gate.py
    - tests/memory/test_conflict_detection.py
    - tests/memory/test_backfill_scanner.py
  modified:
    - clawteam/memory/__init__.py
    - clawteam/templates/gstack/skills/learn/handler.py
    - .planning/REQUIREMENTS.md
decisions:
  - "Gate triggers on impact:high tag OR (scope=team AND any tag in {decisions, decisions:*, decisions-*}). Matches MEM-06 requirement wording + the /learn handler's auto-tagging behavior which appends impact:high when impact='high'."
  - "stage_pending writes pending JSONL under memory/<scope>/pending/<id>.jsonl AND (when sprint_id given) a memory-confirm-<id>.md question artifact under sprints/<sprint>/questions/. InteractionGate pairs by stem so this re-uses the existing answers/<id>.md convention without subclassing."
  - "Conflict detection is stdlib-only cosine over bag-of-words. Threshold 0.75 default (matches ConflictDetected event docstring reference to gstack.toml [memory] conflict_threshold). Tag-gated scan: only entries sharing at least one tag are compared."
  - "Conflict events are non-blocking (D-10). Handler emits after successful store.write; bus/event-type import failure is swallowed — conflict signal is advisory, write must never roll back."
  - "Backfill idempotency uses a .processed/<stem>.processed sentinel per retro file (NOT a single team-level sentinel). New retros written to _phase6_pending later are picked up automatically on next process start."
  - "Per-process per-team trigger: module-level _backfilled_teams: set[str] in the /learn handler. First invocation of any action for a team runs backfill_scan; subsequent calls are no-ops. Test helper clears the set for isolation."
  - "Malformed JSON under _phase6_pending is skipped silently without writing a sentinel — a later fix + rerun can still promote it. Bad data that survives parsing but fails MemoryEntry validation IS sentinel-guarded (would otherwise be promoted on every scan)."
metrics:
  duration: ~25min
  completed: 2026-04-22
---

# Phase 6 Plan 11: High-Impact Gate + Conflict Detection + Backfill Scanner Summary

## One-liner

Wired MEM-06 human-confirmation gate into /learn, shipped stdlib cosine-on-BoW conflict detection emitting advisory `ConflictDetected` events, and delivered the Phase 3 D-09 backfill scanner that promotes `_phase6_pending/*.json` retros to `memory/team/<YYYY-MM>.jsonl` idempotently — all three safety capabilities land as small modules under `clawteam/memory/` consumed by a single /learn handler edit.

## What shipped

**Three new modules under `clawteam/memory/`:**

1. **`high_impact_gate.py`** — `check_high_impact(entry) -> (bool, reason)` classifies writes requiring human confirmation. `stage_pending(entry, team, sprint_id, root)` writes `memory/<scope>/pending/<id>.jsonl` + optional `sprints/<id>/questions/memory-confirm-<id>.md` (InteractionGate-compatible by stem-pairing).

2. **`conflict.py`** — `detect_conflicts(new_entry, store, threshold=0.75)` returns list of `ConflictMatch(other_id, similarity, shared_tags)` frozen dataclasses. Tag-gated (shared ≥ 1 tag required) + cosine-on-BoW over bodies using stdlib `math` + `re`. `DEFAULT_CONFLICT_THRESHOLD = 0.75`.

3. **`backfill.py`** — `backfill_scan(team, root) -> int` walks `<root>/teams/<team>/_phase6_pending/*.json`, promotes each unprocessed retro JSON to a `MemoryEntry` (tags=[retro, phase-reflect], scope=team, learned_from=artifact) via `TeamMemoryStore.write`. Idempotent via `.processed/<stem>.processed` sentinel. Malformed / unreadable files are skipped without sentineling so fix-and-retry works. Bad data that survives JSON parse but fails `MemoryEntry` validation IS sentineled (prevents re-promotion loop).

**Wire-up at `clawteam/templates/gstack/skills/learn/handler.py`:**

- **Backfill trigger:** Module-level `_backfilled_teams: set[str]` + `_ensure_backfilled(team)` helper. Called at the top of every `learn_handler` invocation. First call per `(team, process)` runs `backfill_scan(team, root=get_data_dir())`; subsequent calls are no-ops. All exceptions swallowed — backfill never blocks `/learn`.
- **High-impact gate:** In `_do_write`, `check_high_impact(entry)` runs before `store.write`. If it returns `(True, reason)`, `stage_pending` writes the pending JSONL + question artifact and `_do_write` returns `{"status": "pending_confirmation", "id", "high_impact": True, "reason", "pending_path"}` WITHOUT calling `store.write`. Low-impact path is unchanged.
- **Conflict events:** After every successful `store.write`, `detect_conflicts(entry, store)` runs; matches are emitted as `ConflictDetected` events via the global bus (non-blocking, exceptions swallowed). Handler result includes `conflicts: [other_id, ...]` so the CLI can surface conflicts without replaying the scan.

## Tests (16 new, all green)

**`tests/memory/test_high_impact_gate.py`** (6):
1. `test_impact_high_tag_triggers_confirmation`
2. `test_decisions_scope_triggers_confirmation`
3. `test_low_impact_tag_no_confirmation`
4. `test_stage_pending_writes_jsonl_and_question`
5. `test_learn_handler_stages_instead_of_writing_on_high_impact`
6. `test_learn_handler_writes_immediately_on_low_impact`

**`tests/memory/test_conflict_detection.py`** (5):
1. `test_empty_tags_no_conflict`
2. `test_same_tag_similar_body_matches`
3. `test_same_tag_different_body_below_threshold_no_match`
4. `test_different_tags_never_match_even_if_body_similar`
5. `test_threshold_configurable`

**`tests/memory/test_backfill_scanner.py`** (5):
1. `test_scan_empty_pending_returns_zero`
2. `test_scan_promotes_json_to_retro_jsonl`
3. `test_scan_is_idempotent`
4. `test_scan_skips_malformed_json_without_crash`
5. `test_learn_handler_triggers_backfill_on_first_invocation`

**Verification:**
- `uv run pytest tests/memory/ tests/test_learn_cli.py tests/templates/gstack/skills/test_learn.py tests/plugins/` → 94/94 green
- `tests/test_event_types_phase6.py` → 9/9 green (`ConflictDetected` shape unchanged)
- Plugin still registers 13 skills (`/codex /ship /setup-deploy /land-and-deploy /document-release /canary /benchmark /browse /open-gstack-browser /setup-browser-cookies /design-shotgun /design-html /learn`).

## Dependencies satisfied

- **MEM-06**: impact:high-tagged writes AND writes under memory/team/decisions/* stage to pending and emit an InteractionGate question artifact. Marked `[x]` in REQUIREMENTS.md.
- **QUALITY-10**: Conflict detection (cosine-on-BoW + same-tag match) emits ConflictDetected event without blocking the write. Reflect-phase backfill scanner walks `_phase6_pending/*.json` → `memory/team/retros/` idempotently via `.processed` sentinel. Marked `[x]` in REQUIREMENTS.md.
- **Phase 6 Success Criteria #6** (impact:high triggers human confirmation) — closed.
- **Phase 6 Success Criteria #8** (conflict detection emits event) — closed.
- **D-09 / D-10 / D-11** — realized in code.

## Commits

| Task | Kind       | Commit    | Message                                                                                       |
| ---- | ---------- | --------- | --------------------------------------------------------------------------------------------- |
| 1    | test (RED) | `c1757c9` | `test(06-11): add failing tests for high-impact gate + stage_pending`                         |
| 1    | feat (GREEN)| `57d16a6` | `feat(06-11): high-impact gate + stage_pending + /learn wiring`                               |
| 2    | test (RED) | `15e311b` | `test(06-11): add failing tests for cosine-on-BoW conflict detection`                         |
| 2    | feat (GREEN)| `22f7ed8` | `feat(06-11): cosine-on-BoW conflict detection + ConflictDetected emission`                   |
| 3    | test (RED) | `9c8845d` | `test(06-11): add failing tests for _phase6_pending backfill scanner`                         |
| 3    | feat (GREEN)| `20be219` | `feat(06-11): _phase6_pending backfill scanner + first-invocation trigger`                    |

## Deviations from Plan

### Rule 3 — Blocking fixes

**1. [Rule 3 - Blocking] `TeamMemoryStore` constructor signature mismatch**
- **Found during:** Task 3 (plan spec wrote `TeamMemoryStore(team=team, data_dir=root)`)
- **Issue:** Actual store signature is `TeamMemoryStore(team_name)` — reads data dir via `get_data_dir()` env/config only. Plan's kwargs would crash.
- **Fix:** `backfill_scan` takes `root: Path` as a separate argument (used only for locating `_phase6_pending/`), but constructs `TeamMemoryStore(team)` and relies on the env-driven `get_data_dir()` already pointed at `root` by the caller (`_ensure_backfilled` passes `get_data_dir()`; tests set `CLAWTEAM_DATA_DIR` to `tmp_path`). The handler wire-up therefore keeps the `root` param for path-only use but the store writes land in the correct isolated location.
- **Files modified:** `clawteam/memory/backfill.py`, `clawteam/templates/gstack/skills/learn/handler.py`
- **Commit:** `20be219`

### Rule 2 — Missing critical functionality auto-added

**2. [Rule 2 - Hardening] `stage_pending` preview truncation + evidence-empty display**
- **Found during:** Task 1
- **Issue:** Plan snippet had a raw `entry.body[:300]...` that would render literal "..." even when the body was shorter than 300 chars, and no handling for empty evidence (MEM-05 flagged case).
- **Fix:** Conditional ellipsis (`"..." if len(body) > 300 else ""`) and explicit `"(none — MEM-05 flagged)"` display when evidence is empty. Also surface role + confidence on the question artifact so the reviewer has enough context to Confirm / Edit / Reject without re-reading the pending JSONL.
- **Commit:** `57d16a6`

**3. [Rule 2 - Robustness] Non-blocking event emission hardened**
- **Found during:** Task 2
- **Issue:** Plan snippet had a raw `event_bus.emit(ConflictDetected(...))` with no try/except. The `learn_handler` write path must NEVER raise just because the bus is unavailable (e.g., in CLI test harnesses where hooks aren't loaded).
- **Fix:** Dedicated `_emit_conflict_events` helper that lazy-imports `get_event_bus` + `ConflictDetected`, swallows all exceptions. Consistent with existing plugin pattern (`on_register` in `gstack_sprint_plugin.py`).
- **Commit:** `22f7ed8`

### Out-of-scope items

No out-of-scope issues found during execution. Pre-existing learn/CLI test suite (20 tests) + plugin registration tests (5 tests) + Phase 6 event tests (9 tests) all stayed green without modification.

## Authentication gates

None — pure in-process Python work.

## Known Stubs

None. All three new modules ship their full functionality; no placeholder / TODO / FIXME content in added files. Grep-verified:

```
$ grep -nE "TODO|FIXME|placeholder|coming soon" clawteam/memory/high_impact_gate.py clawteam/memory/conflict.py clawteam/memory/backfill.py
(no output)
```

## Threat Flags

None. The new modules consume existing trust boundaries (TeamMemoryStore's `ensure_within_root` + `validate_identifier` guards apply transitively to stage_pending / backfill promotion paths). No new network endpoints, auth paths, or schema changes at trust boundaries.

## Self-Check: PASSED

**Files exist:**
- `clawteam/memory/high_impact_gate.py` ✓
- `clawteam/memory/conflict.py` ✓
- `clawteam/memory/backfill.py` ✓
- `tests/memory/test_high_impact_gate.py` ✓
- `tests/memory/test_conflict_detection.py` ✓
- `tests/memory/test_backfill_scanner.py` ✓

**Commits in git log:**
- `c1757c9` ✓ (Task 1 RED)
- `57d16a6` ✓ (Task 1 GREEN)
- `15e311b` ✓ (Task 2 RED)
- `22f7ed8` ✓ (Task 2 GREEN)
- `9c8845d` ✓ (Task 3 RED)
- `20be219` ✓ (Task 3 GREEN)

**Tests:** 16/16 new tests pass; 94/94 memory+learn+plugin tests green; 9/9 Phase 6 event-type tests green.

**REQUIREMENTS.md updated:** MEM-06 + QUALITY-10 checkboxes and traceability rows now `[x] Complete`.

## TDD Gate Compliance

- Task 1: RED `c1757c9` → GREEN `57d16a6` ✓
- Task 2: RED `15e311b` → GREEN `22f7ed8` ✓
- Task 3: RED `9c8845d` → GREEN `20be219` ✓

All three tasks followed the RED→GREEN cycle with test-commit preceding implementation-commit.
