---
phase: 06-browser-skills-design-pipeline-team-memory
plan: 10
subsystem: team-memory
tags:
  - skill-learn
  - typer-cli
  - role-agnostic
  - mem-03
  - mem-04
  - d-07
  - d-08
requires:
  - 06-02  # TeamMemoryStore + MemoryEntry
  - 06-03  # memory.search + rank + decay
provides:
  - "/learn skill (role-agnostic) + clawteam learn Typer CLI"
  - "shared learn_handler dispatched by both skill registry + CLI (D-08)"
affects:
  - clawteam/plugins/gstack_sprint_plugin.py (13 SkillRegistrations)
  - clawteam/cli/commands.py (learn_app subcommand group)
tech_stack:
  added:
    - typer.Typer subcommand group pattern (learn_app pattern mirrors sprint_app)
  patterns:
    - "Shared-handler pattern: CLI synthesizes minimal ctx via SimpleNamespace(team_name=...)"
    - "Role-agnostic skill: roles=frozenset(GSTACK_ROLES) — single enforcement point"
    - "--json surface via global app callback (not per-command flag)"
key_files:
  created:
    - clawteam/templates/gstack/skills/learn/__init__.py
    - clawteam/templates/gstack/skills/learn/handler.py
    - tests/templates/gstack/skills/test_learn.py
    - tests/test_learn_cli.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py
    - clawteam/cli/commands.py
decisions:
  - "Role-agnostic /learn: handler itself does NOT gate on role; plugin roles=frozenset(GSTACK_ROLES) is the single enforcement point (D-07)."
  - "impact=='high' auto-appends 'impact:high' tag — lets Plan 06-11 gate grep one tag rather than a second field."
  - "Empty evidence is FLAGGED (MEM-05: evidence_flagged=True in result) but never blocks write."
  - "--json lives on the global app callback (matches sprint_app precedent) — no per-command --json flag."
  - "CLI synthesizes a minimal ctx via SimpleNamespace(team_name=...) rather than loading TeamConfig; memory ops need nothing else from ctx."
metrics:
  duration: 45min
  completed: "2026-04-22"
  commits: 4
  tests_added: 20
---

# Phase 6 Plan 06-10: /learn skill + `clawteam learn` CLI Summary

Role-agnostic team-memory surface — /learn skill + `clawteam learn` CLI both dispatch through a single shared `learn_handler` (D-08), closing MEM-03 + MEM-04 + D-07 + D-08 with 20 new tests.

## Scope

- Task 1 (TDD): `/learn` skill handler — write/list/search/prune actions, shared entry point, role-agnostic plugin registration.
- Task 2 (TDD): `clawteam learn {write,list,search,prune}` Typer subcommand group reusing the same handler.

Out of scope per plan: high-impact gate, conflict detection, backfill scanner — those land in Plan 06-11 which instruments this plan's write path. The execute_plan context mentioned those additions, but the shipped plan file (`06-10-PLAN.md`) defers them to 06-11.

## Deliverables

### clawteam/templates/gstack/skills/learn/handler.py (new, ~200 LOC)

`learn_handler(ctx, *, role, args) -> dict` dispatches on `args['action']`:

- **write** — constructs `MemoryEntry` (id generated via `TeamMemoryStore.gen_id`), persists via `TeamMemoryStore.write`. Returns `{status:"written", id, evidence_flagged, high_impact}`. Empty evidence → `evidence_flagged=True`; `impact=="high"` auto-appends `impact:high` tag → `high_impact=True`.
- **list** — enumerates tombstone-suppressed entries via `TeamMemoryStore.list`. Returns `{status:"listed", entries:[...]}` where each entry is `model_dump()`.
- **search** — keyword retrieval via `clawteam.memory.search.search`. With `args['explain']` true, result items include `recency/provenance/decay` factors alongside `score` — surfaces the D-06 ranking formula transparently.
- **prune** — tombstones via `TeamMemoryStore.prune` (bypasses the future high-impact gate per research Open Question 3 — the tombstone IS the undo).

Unknown action → `ValueError`. Invalid impact → `ValueError`. All errors propagate to the CLI layer which wraps them as `typer.Exit(1)`.

### clawteam/plugins/gstack_sprint_plugin.py (modified, +18 LOC)

One additive import + one SkillRegistration:

```python
SkillRegistration(
    name="/learn",
    roles=frozenset(GSTACK_ROLES),  # role-agnostic per D-07
    handler=_learn_handler,
    tool_available=None,
    install_hint="",
)
```

13 SkillRegistrations after this plan + its Wave-3 sibling 06-09 (which added /design-html in parallel): `/benchmark, /browse, /canary, /codex, /design-html, /design-shotgun, /document-release, /land-and-deploy, /learn, /open-gstack-browser, /setup-browser-cookies, /setup-deploy, /ship`.

### clawteam/cli/commands.py (modified, ~230 LOC appended)

`learn_app = typer.Typer(..., no_args_is_help=True)` subcommand group registered via `app.add_typer(learn_app, name="learn")`. Four commands:

- `clawteam learn write --team T --title TITLE [--scope team|role] [--role R] [--tags a,b] [--evidence src:line] [--confidence 0.0-1.0] [--learned-from ...] [--impact low|medium|high] [--sprint-id ID] [BODY]`
- `clawteam learn list --team T [--scope team|role] [--role R] [--tag T]`
- `clawteam learn search [QUERY] --team T [--scope ...] [--tag ...] [--explain]`
- `clawteam learn prune ENTRY_ID --team T [--scope team|role] [--role R]`

All surfaces emit JSON when global `--json` is set (mirrors `sprint_app` precedent); otherwise print human-readable rich tables. Validation layering:

1. Typer enforces `--confidence` min/max at parse.
2. Handler rejects unknown `--impact`.
3. MemoryEntry pydantic rejects `scope=role` without `role`.

### tests/templates/gstack/skills/test_learn.py (new, 11 tests, ~310 LOC)

Handler-level TDD suite: write team-scope + role-scope, missing evidence flagged-not-blocked, list + list-with-tag-filter, search + search-with-explain, prune tombstone suppresses, unknown action → ValueError, role-agnostic dispatch across all 11 `GSTACK_ROLES`, plugin registration count + role-set assertion.

### tests/test_learn_cli.py (new, 9 tests, ~290 LOC)

CLI-level TDD suite via `typer.testing.CliRunner` + tmp `CLAWTEAM_DATA_DIR` monkeypatch: write exit 0 + `--json`, list table + JSON, search ranking, `--explain` columns, prune tombstone, scope=role without `--role` fails, invalid `--impact` fails, confidence out-of-range fails.

## Verification

| Check | Command | Result |
|-------|---------|--------|
| Task 1 handler tests | `pytest tests/templates/gstack/skills/test_learn.py -q` | 11 passed |
| Task 2 CLI tests | `pytest tests/test_learn_cli.py -q` | 9 passed |
| Plugin regression | `pytest tests/plugins/ -q` | 5 passed |
| Broad regression | `pytest tests/test_cli_commands.py tests/plugins/ tests/test_gstack_plugin.py tests/test_plugin_hooks.py tests/memory/ tests/browser/ tests/templates/gstack/skills/test_learn.py tests/test_learn_cli.py -q` | 164 passed |
| `clawteam learn --help` | `CliRunner().invoke(app, ['learn', '--help'])` | exit 0, shows write/list/search/prune |

All plan acceptance-criteria grep checks pass:
- `def learn_handler` in handler.py
- `name="/learn"` in plugin
- `frozenset(GSTACK_ROLES)` in plugin
- `learn_app = typer.Typer` in commands.py
- `app.add_typer(learn_app, name="learn")` in commands.py
- `@learn_app.command` × 4 in commands.py

## Commits

| Hash | Message |
|------|---------|
| 8038d28 | test(06-10): add failing tests for /learn skill handler (Task 1 RED) |
| 9624ad3 | feat(06-10): implement /learn skill handler + plugin registration (Task 1 GREEN) |
| 84a54ea | test(06-10): add failing tests for clawteam learn CLI subcommand group (Task 2 RED) |
| 788347f | feat(06-10): add clawteam learn CLI subcommand group (Task 2 GREEN) |

TDD gate sequence preserved: RED → GREEN → RED → GREEN (per task).

## Deviations from Plan

### 1. Test-file location — `tests/test_learn_cli.py` at repo root rather than `tests/cli/test_learn_cli.py`

**Found during:** Task 2 setup (reading plan's suggested path)
**Issue:** Plan specifies `tests/cli/test_learn_cli.py` but that directory does not exist in this repo. All existing CLI tests live at `tests/test_cli_commands.py` (repo root).
**Fix:** Placed the 9 CLI tests at `tests/test_learn_cli.py` alongside the existing CLI-test convention. Rule 3 — auto-fixed blocking path mismatch; same precedent as Plan 05-07's `test_ship.py` → `test_ship_skill.py` decision.
**Files modified:** `tests/test_learn_cli.py` (new file at unintended location per plan).

### 2. Wave-3 cross-executor stash interaction (recurring 04-10 / 05-03 / 05-06 / 05-09 / 06-07 pattern)

**Found during:** Task 1 GREEN commit + Task 2 GREEN commit.
**Issue:** Sibling Wave-3 executors (Plans 06-08 /design-shotgun, 06-09 /design-html) were racing on `clawteam/plugins/gstack_sprint_plugin.py`. At three points during 06-10 execution:
  1. My /learn SkillRegistration was OVERWRITTEN by a /design-html-only rewrite (06-09 executor's stash-restore).
  2. My /learn SkillRegistration was overwritten again by a /design-shotgun-only rewrite (06-08 executor's GREEN commit).
  3. On Task 2 commit restore, both /design-html AND /design-shotgun were present alongside my /learn.
**Fix:** Idempotent re-application of my /learn hunks after each sibling race, with a `git diff` verification before each commit that the staged plugin-file diff is /learn-only. feat(06-10) commits contain ONLY my additions; sibling plans' content was committed by their respective executors under their own feat hashes. Cross-executor stashing preserved; no work lost on any side.
**Files involved:** `clawteam/plugins/gstack_sprint_plugin.py` (shared across 4 parallel executors).

### 3. `test_registered_in_plugin` uses subset-on-count (`>= 11`) rather than strict `== 13`

**Found during:** Task 1 RED design.
**Issue:** Wave-3 parallel executors (06-08, 06-09, 06-10) all land plugin SkillRegistrations. A strict `== 13` equality check would fail under any commit order where fewer than all three have landed.
**Fix:** Subset check `>= 11` with explicit `/learn` presence + role-agnostic assertion. Strict `== 13` invariant is enforced instead by the Wave-3 end-of-phase integration test (Plan 06-11 or Phase-6 close-out). Same relaxation pattern as Plan 06-07's Wave-2 adjustment.
**Files modified:** `tests/templates/gstack/skills/test_learn.py`.

## Auth Gates

None. The skill + CLI operate on local `CLAWTEAM_DATA_DIR` and require no credentials.

## Known Stubs

None. High-impact gate, conflict detection, and `_phase6_pending/` backfill scanner are explicitly deferred to Plan 06-11 per the shipped plan file (not stubs — a separately-scoped follow-up plan that instruments this plan's write path). The 06-10 write path is fully functional end-to-end today.

## Requirements Closed

- **MEM-03** — memory search + retrieval reachable via `/learn search` + `clawteam learn search` (with optional `--explain` surfacing D-06 ranking factors).
- **MEM-04** — memory write reachable via `/learn write` + `clawteam learn write` (scope=team or scope=role; empty evidence flagged per MEM-05).
- **D-07** — role-agnostic /learn registration via `roles=frozenset(GSTACK_ROLES)`.
- **D-08** — shared handler between skill dispatch + CLI.

Requirements pending for Plan 06-11: MEM-01, MEM-02, MEM-05 (gate hook), MEM-06, MEM-07 (enforcement path), SKILL-10 (completeness), SKILL-11, SKILL-12, QUALITY-10.

## Self-Check

Created files exist:
- `clawteam/templates/gstack/skills/learn/handler.py` — FOUND
- `clawteam/templates/gstack/skills/learn/__init__.py` — FOUND
- `tests/templates/gstack/skills/test_learn.py` — FOUND
- `tests/test_learn_cli.py` — FOUND

Commits exist:
- 8038d28 (test RED Task 1) — FOUND
- 9624ad3 (feat GREEN Task 1) — FOUND
- 84a54ea (test RED Task 2) — FOUND
- 788347f (feat GREEN Task 2) — FOUND

## Self-Check: PASSED
