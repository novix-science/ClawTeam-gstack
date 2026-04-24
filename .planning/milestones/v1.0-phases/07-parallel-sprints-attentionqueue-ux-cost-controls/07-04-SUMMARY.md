---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 04
subsystem: attend-cli
tags:
  - cli
  - typer-subcommand
  - editor-launch
  - auto-accept-reversible
  - wave-3
dependency-graph:
  requires:
    - 07-01 (Wave 0 substrate: clawteam/attention package marker + AttentionConfig)
    - 07-03 (AttentionQueue.snapshot, build_digest, AttentionItem frozen dataclass)
    - clawteam/cli/commands.py (existing typer pattern, _output helper, console)
  provides:
    - clawteam.attention.auto_accept.preview_auto_accept (eligibility filter)
    - clawteam.attention.auto_accept.apply_auto_accept (answer.md writer, TTL frontmatter)
    - clawteam.attention.auto_accept.DEFAULT_TTL_MINUTES (= 15)
    - clawteam attend typer subcommand group (registered via app.add_typer)
    - attend default invocation (top-N priority-ranked items + --json envelope)
    - attend --summary flag (build_digest dispatch with rich + JSON output)
    - attend --auto-accept-reversible flag (preview-only; --yes applies)
    - attend pick <qid> subcommand (EDITOR launch + answer-file presence check)
  affects:
    - 07-09 (10-sprint load test — may exercise attend CLI surface as smoke)
    - Future plans that surface pending-question counts in dashboards
tech-stack:
  added: []
  patterns:
    - "Preview/apply split for mutating operations — preview enumerates eligible,
       apply requires --yes to mutate (mirrors --auto-accept-reversible safety)"
    - "Layered snapshot limit — None for summary/auto-accept (full surface needed),
       clamp to top_n for default priority table"
    - "subprocess.run for EDITOR launch with shell=False (injection-safe); os.environ
       fallback to 'vi' matches POSIX tradition"
    - "Answer file path derived from question.parent.parent/answers/<qid>.md
       (matches InteractionGate + auto_accept + watcher shared convention)"
    - "Exit-code hierarchy: 1 = not found, 2 = ambiguous, 3 = editor missing"
key-files:
  created:
    - path: clawteam/attention/auto_accept.py
      description: "preview_auto_accept + apply_auto_accept + DEFAULT_TTL_MINUTES (94 LOC)"
    - path: tests/attention/test_auto_accept.py
      description: "8 auto_accept tests covering preview filter/sort + apply TTL/idempotent (117 LOC)"
    - path: tests/attention/test_attend_cli.py
      description: "8 CLI tests covering empty queue, top-N, --json, --summary, auto-accept preview/apply, pick editor/unknown-id (147 LOC)"
  modified:
    - path: clawteam/attention/__init__.py
      description: "Re-export 3 new auto_accept symbols alongside existing 9"
    - path: clawteam/cli/commands.py
      description: "+255 LOC — attend_app typer group + attend_root callback + pick subcommand + 2 rich renderers"
decisions:
  - "apply_auto_accept is the single-source-of-truth filter for reversibility=easy
     — preview_auto_accept surfaces what apply WILL write, never diverges. Non-easy
     items passed directly to apply (skipping preview) still land in skipped bucket."
  - "DEFAULT_TTL_MINUTES = 15 lives in auto_accept module (not hardcoded in CLI)
     so future plans adjusting the TTL have one file to touch."
  - "now_fn injection seam on apply_auto_accept so tests can verify TTL metadata
     without wall-clock coupling; production code uses timezone-aware UTC default."
  - "attend CLI uses AttentionQueue() directly (no .for_current_user()) — config
     loading stays a Wave-0 substrate concern; weights will plumb through once a
     future plan wires gstack.toml [attention] → AttentionQueue constructor."
  - "snapshot_limit = None when --summary or --auto-accept-reversible are set
     — digest groups the full surface; auto-accept previews every eligible item.
     Default path clamps to top_n (default 10) to keep the table readable."
  - "pick subcommand exits with distinct codes (1/2/3) for UNKNOWN / AMBIGUOUS /
     MISSING EDITOR so scripts can branch on failure mode (vs. generic exit 1)."
  - "--yes is both a short-flag (-y) and long-flag option to match standard CLI
     ergonomics; when --yes is set without --auto-accept-reversible it is a
     no-op (rather than an error) — future-proof if more confirm surfaces land."
  - "Answer-file write (Task 1 apply_auto_accept) uses Path.write_text directly
     (not file_locked+atomic_write_text) because answer.md is a one-shot per-qid
     artifact with no concurrent-writer scenario; idempotent existence check
     handles the double-apply case."
requirements-completed:
  - INT-04
  - UX-06
  - QUALITY-05
metrics:
  duration: "~4min"
  completed: "2026-04-22T14:33:59Z"
  tasks: 2
  files_created: 3
  files_modified: 2
  tests_added: 16
  loc_delta: ~366 production / ~264 tests
---

# Phase 7 Plan 07-04: `clawteam attend` CLI Summary

Wave 3 — cross-sprint `clawteam attend` CLI subcommand group surfacing the
Plan 07-03 AttentionQueue substrate to the end user. Ships the three flavors
called out in CONTEXT D-07/D-08 plus the `pick` subcommand for
`$EDITOR`-based question answering.

## One-liner

`clawteam attend` typer subcommand: default top-N priority table + `--summary`
digest + `--auto-accept-reversible` preview-and-apply (reversibility=easy
only, 15-min TTL) + `pick <qid>` opening `$EDITOR` on the chosen question.md
with answer-file presence re-check on exit.

## What Was Built

### Task 1 — auto_accept helper (commits `4a29cdb` RED → `68d7c8d` GREEN)

- **`clawteam/attention/auto_accept.py`** (94 LOC):
  - `preview_auto_accept(items) -> list[AttentionItem]` — filters to
    `reversibility == "easy"` (D-08 lock), sorts `priority_score` descending.
    Pure function, zero filesystem I/O.
  - `apply_auto_accept(items, *, ttl_minutes=15, now_fn=None) -> dict`
    — writes `answer.md` for each eligible item under
    `<sprint>/answers/<qid>.md` (matches InteractionGate layout). Answer body
    carries YAML frontmatter `auto_accepted: true` + `auto_accepted_at: <iso>`
    + `ttl_minutes: 15` + `question_id: <qid>`. Non-easy items and items with
    pre-existing answer files land in the returned `skipped` list; never
    overwrites, never deletes.
  - `DEFAULT_TTL_MINUTES = 15` module constant.
- **`clawteam/attention/__init__.py`** — re-exports the 3 new symbols
  (`preview_auto_accept`, `apply_auto_accept`, `DEFAULT_TTL_MINUTES`) so
  `from clawteam.attention import apply_auto_accept` works.
- **8 auto_accept tests** (`tests/attention/test_auto_accept.py`, 117 LOC):
  preview easy-only filter, preview priority-desc sort, apply writes answer,
  apply TTL metadata, apply body placeholder, apply idempotent skip,
  apply returns applied/skipped dict, apply skips non-easy.

### Task 2 — `clawteam attend` typer subcommand group (commits `57685a2` RED → `0c4304b` GREEN)

- **`clawteam/cli/commands.py`** (+255 LOC appended after `learn_app` block):
  - `attend_app = typer.Typer(help="Cross-sprint attention queue")` +
    `app.add_typer(attend_app, name="attend")`.
  - `_render_attend_items_human(items)` — rich Table with columns
    `#` / `Priority` / `Urg` / `Team` / `Sprint` / `Age` / `Rev` / `Title`.
    Urgency labeled `CRIT` (bold red) / `HIGH` (yellow) / `norm` / `low`.
  - `_render_digest_human(digest)` — rich Table for `--summary` cluster output
    with columns `Sprint` / `Tag` / `Age` / `Count` / `Top priority` /
    `Representative title`.
  - `attend_root` callback (`invoke_without_command=True`): 4 options
    (`--top/-n`, `--summary`, `--auto-accept-reversible`, `--yes/-y`);
    dispatches to three branches:
    1. `auto_accept_reversible` → `preview_auto_accept` + optional
       `apply_auto_accept` on `--yes`.
    2. `summary` → `build_digest` over full snapshot.
    3. default → top-N snapshot into rich Table.
    All three emit structured data via `_output()` so the global
    `--json` flag emits a consistent JSON envelope (`items` /
    `digest` / `preview_count` + `applied` + `skipped`).
  - `attend_pick` subcommand — globs snapshot for `question_id`,
    disambiguates via `--team`, launches `subprocess.run([$EDITOR, path])`
    with `check=False`, re-checks answer file presence on exit. Exit codes:
    `1` no match, `2` ambiguous, `3` editor missing.
- **8 CLI tests** (`tests/attention/test_attend_cli.py`, 147 LOC) via typer
  `CliRunner`:
  1. Empty queue → "No pending" message + exit 0.
  2. `-n 2` with 3 questions → top 2 ranked, critical in output.
  3. `--json` envelope has `items` with `question_id` / `priority_score`.
  4. `--json --summary` envelope has `digest` list.
  5. `--auto-accept-reversible` without `--yes` writes no answer file.
  6. `--auto-accept-reversible --yes` writes answer only for easy items
     (never for hard items — Task 1 filter enforces this).
  7. `pick q1` invokes `$EDITOR` (captured subprocess.run arg) with
     `q1.md` path.
  8. `pick nonexistent` → exit code 1.

## Verification

Plan 07-04 scoped suite:
```
pytest tests/attention/test_auto_accept.py tests/attention/test_attend_cli.py -q
→ 16 passed
```

Full attention + CLI BC:
```
pytest tests/attention/ tests/test_cli_commands.py -q
→ 66 passed (42 attention + 24 CLI BC)
```

Phase 7 full scope (attention + rate_limit + sprint + CLI):
```
pytest tests/attention/ tests/test_cli_commands.py tests/rate_limit/ tests/sprint/ -q
→ 82 passed
```

Manual smoke:
```
$ CLAWTEAM_DATA_DIR=/tmp/empty clawteam attend
No pending attention items.
(exit 0)

$ clawteam attend --help  (via CliRunner)
# Shows: --summary, --auto-accept-reversible, --top/-n, --yes/-y
# Shows pick subcommand in the command list
```

## Acceptance Criteria

- [x] `grep -q "attend_app = typer.Typer" clawteam/cli/commands.py` — present
- [x] `grep -q 'app.add_typer(attend_app, name="attend")' clawteam/cli/commands.py` — present
- [x] `clawteam attend --help` shows `--summary` and `--auto-accept-reversible`
- [x] `grep -q "def preview_auto_accept" clawteam/attention/auto_accept.py` — present
- [x] `grep -q "def apply_auto_accept" clawteam/attention/auto_accept.py` — present
- [x] `pytest tests/attention/test_auto_accept.py -q` → 8 passed (6+ required)
- [x] `pytest tests/attention/test_attend_cli.py -q` → 8 passed
- [x] `pytest tests/test_cli_commands.py -q` → still green (zero BC regressions)
- [x] Safe-when-empty: "No pending attention items." message, exit 0

## Commits

**Task 1 (auto_accept helper):**

- `4a29cdb` test(07-04): add failing tests for auto_accept helper (Task 1 RED)
- `68d7c8d` feat(07-04): implement auto_accept preview + apply with TTL (Task 1 GREEN)

**Task 2 (attend CLI + pick subcommand):**

- `57685a2` test(07-04): add failing tests for clawteam attend CLI (Task 2 RED)
- `0c4304b` feat(07-04): implement clawteam attend CLI + pick subcommand (Task 2 GREEN)

## Deviations from Plan

**None.** Plan executed exactly as written — both tasks, both RED→GREEN gates
preserved. Task 1 landed 8-of-8 tests green on first GREEN commit; Task 2
landed 8-of-8 tests green on first GREEN commit. No auto-fixes (Rules 1-3)
needed. No architectural questions (Rule 4) raised.

One minor scope elaboration logged in decisions above: the plan's action
block showed apply_auto_accept writing non-easy items to `skipped` while the
preview function filters them out. The apply-level filter is defensive (if a
caller bypasses preview and passes raw items, non-easy still cannot mutate
the filesystem) — test_apply_skips_non_easy locks this behavior.

## Interfaces for Downstream Plans

**Plan 07-09 (10-sprint load test):**

- Can smoke-test `clawteam attend` against a realistic multi-team workspace.
- `AttentionQueue.snapshot()` return shape + `apply_auto_accept` return dict
  are now stable public API.

**Future cost dashboard surfaces:**

- Can display pending-question counts by consuming `AttentionQueue.snapshot()`
  and counting per-team (same stateless-glob pattern used here).

## Known Stubs

**None** — every data path in this plan writes real bytes to real files
(answer.md for `--yes` apply) or reads real frontmatter (snapshot + preview).
The `AttentionQueue.for_current_user()` seam in Plan 07-03 remains a
no-op-class-method stub for a future plan to wire `gstack.toml [attention]`
into per-team weights, but this plan intentionally uses the default
constructor (documented in decisions).

## Threat Flags

None — the attend CLI is pure read-side + user-opted-in write-side:

- Default + `--summary` never mutate filesystem.
- `--auto-accept-reversible` without `--yes` previews only.
- `--auto-accept-reversible --yes` writes `answer.md` under paths derived
  from existing question.md locations (never writes outside `<data>/teams/`
  because the paths flow from `AttentionQueue.snapshot()` which already
  constrains to `teams_root.glob("*/sprints/*/questions/*.md")`).
- `pick` subcommand launches `$EDITOR` with `shell=False` (injection-safe)
  and only on a question.md path returned by the queue snapshot.

## Self-Check: PASSED

All frontmatter-declared deliverables verified on disk:

- `clawteam/attention/auto_accept.py` — FOUND (94 LOC)
- `clawteam/attention/__init__.py` — MODIFIED (re-exports 12 symbols, up from 9)
- `clawteam/cli/commands.py` — MODIFIED (+255 LOC, grep confirms attend_app)
- `tests/attention/test_auto_accept.py` — FOUND (8 tests pass)
- `tests/attention/test_attend_cli.py` — FOUND (8 tests pass)

All commits verified in git log:

- `4a29cdb` — FOUND (test Task 1 RED)
- `68d7c8d` — FOUND (feat Task 1 GREEN)
- `57685a2` — FOUND (test Task 2 RED)
- `0c4304b` — FOUND (feat Task 2 GREEN)

## TDD Gate Compliance

All 2 tasks followed strict RED → GREEN cycle:

| Task | RED commit | GREEN commit | Delta |
|------|------------|--------------|-------|
| 1 (auto_accept) | 4a29cdb | 68d7c8d | 8 tests → 8 pass |
| 2 (attend CLI)  | 57685a2 | 0c4304b | 8 tests → 8 pass |

RED gate confirmed for both tasks before corresponding GREEN commit landed:

- Task 1 RED: `ModuleNotFoundError: No module named 'clawteam.attention.auto_accept'`
- Task 2 RED: typer `SystemExit(2)` (subcommand 'attend' does not exist)

---

*Phase: 07-parallel-sprints-attentionqueue-ux-cost-controls*
*Completed: 2026-04-22*
