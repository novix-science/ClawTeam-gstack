---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 12
subsystem: sprint-cli
tags: [sprint-cli, typer-sub-app, json-envelope, ux-02, ux-03, ux-04, ux-05, ux-09]
requires:
  - clawteam.sprint.conductor.SprintConductor (Plan 02-11)
  - clawteam.sprint.state.SprintState (Plan 02-03)
  - clawteam.cli.commands.app (existing global Typer)
  - clawteam.identity._env (env-fallback helper)
provides:
  - clawteam.cli.commands.sprint_app (Typer sub-app, 6 commands)
  - clawteam.sprint.conductor.SprintConductor.most_recent_artifact
  - clawteam.sprint.conductor.SprintConductor.status_dict
  - clawteam.sprint.conductor.SprintConductor.show_dict
  - clawteam.cli.commands._sprint_emit_ok (D-26 success envelope)
  - clawteam.cli.commands._sprint_emit_err (D-26 error envelope)
  - clawteam.cli.commands._resolve_team_arg (Pitfall #9 team guard)
  - clawteam.cli.commands._resolve_sprint_or_err (D-25 prefix resolver)
affects:
  - clawteam/cli/commands.py (additive: +283 LOC after guard_app block)
  - clawteam/sprint/conductor.py (additive: +54 LOC — 3 helpers)
tech_stack:
  added: []
  patterns:
    - Typer sub-app via app.add_typer(name='sprint')
    - Uniform JSON envelope {ok, data, warnings, error} per §02-CONTEXT D-26
    - Dispatch-only CLI: commands translate ValueError subclasses → machine codes
key_files:
  created:
    - tests/test_sprint_cli.py (358 LOC, 15 CliRunner tests)
  modified:
    - clawteam/cli/commands.py (4854 → 5158 LOC, +304 net including comments)
    - clawteam/sprint/conductor.py (489 → 544 LOC, +55)
    - tests/test_sprint_conductor.py (456 → 545 LOC, +89; 4 new tests)
decisions:
  - show_dict returns artifacts_list (names only, sorted) not artifacts (bodies) — UX-05 JSON payload stays bounded
  - Error-to-envelope translation lives in CLI layer (not conductor) — conductor stays pure domain
  - human renderer uses existing module-level rich `console` — no duplicate Console()
metrics:
  tasks_completed: 2
  commits:
    - af6b7d0: feat(02-12) add SprintConductor CLI serialization helpers
    - 60ad26e: feat(02-12) add clawteam sprint CLI sub-app with 6 commands
  tests_added: 19 (4 conductor helpers + 15 CLI)
  tests_total_pass: 68 (sprint_cli 15 + sprint_conductor 21 + cli_commands 20 + template_regression_matrix 12)
  duration: ~25 min
  completed: 2026-04-20
---

# Phase 2 Plan 12: Sprint CLI Sub-App Summary

`clawteam sprint` sub-app ships with 6 commands (start/status/show/list/pause/resume), uniform `{ok, data, warnings, error}` JSON envelope across every branch, and machine-code error translation — closing UX-02..05 + UX-09.

## What Shipped

### 1. `clawteam/sprint/conductor.py` — CLI serialization helpers (3 methods, +55 LOC)

Line ranges (conductor.py):

| Method | Lines |
|--------|-------|
| `SprintConductor.most_recent_artifact(state)` | 418–428 |
| `SprintConductor.status_dict(state)` | 430–446 |
| `SprintConductor.show_dict(state)` | 448–470 |

- `most_recent_artifact` returns the last-inserted artifact name (empty string when `state.artifacts` is empty). Insertion order preserved by Python dict (3.7+).
- `status_dict` produces the UX-03 compact status view with the exact key set the CLI writes: `{sprint_id, team, current_phase, status, participants, pending_questions_count, most_recent_artifact, auto_advance}`.
- `show_dict` produces the UX-05 detail view: `{sprint_id, team, goal, current_phase, status, participants, phase_history, artifacts_list, pending_question_ids, auto_advance, created_at, workspace_branch}`. `artifacts_list` is sorted NAMES only — bodies are excluded so the JSON payload stays bounded regardless of sprint age.

### 2. `clawteam/cli/commands.py` — Sprint sub-app (1 sub-app + 4 helpers + 6 commands, +304 LOC)

Line ranges (commands.py):

| Component | Lines |
|-----------|-------|
| `sprint_app = typer.Typer(...)` + `app.add_typer(...)` | 4875–4879 |
| `_sprint_emit_ok` | 4882–4894 |
| `_sprint_emit_err` | 4896–4911 |
| `_render_sprint_human` | 4913–4949 |
| `_resolve_team_arg` | 4951–4973 |
| `_resolve_sprint_or_err` | 4975–5007 |
| `@sprint_app.command("start")` / `sprint_start` | 5009–5058 |
| `@sprint_app.command("status")` / `sprint_status` | 5060–5073 |
| `@sprint_app.command("show")` / `sprint_show` | 5075–5088 |
| `@sprint_app.command("list")` / `sprint_list` | 5090–5111 |
| `@sprint_app.command("pause")` / `sprint_pause` | 5113–5133 |
| `@sprint_app.command("resume")` / `sprint_resume` | 5135–5154 |

The sub-app is registered AFTER the existing `guard_app` block (Plan 02-10) — zero edits to existing commands. The Plan 02-10 `clawteam guard` sub-app (lines 4670–4850) is preserved intact.

### 3. `tests/test_sprint_cli.py` — 15 CliRunner tests (358 LOC)

| # | Test | UX/D | Covers |
|---|------|------|--------|
| 1 | `test_sprint_start_creates_sprint_and_returns_json_envelope` | UX-02 / D-26 | happy path: flag + ok envelope |
| 2 | `test_sprint_start_without_team_flag_uses_env` | UX-02 / D-24 | `CLAWTEAM_TEAM` env fallback |
| 3 | `test_sprint_start_without_any_team_raises_missing_team` | Pitfall #9 | `MISSING_TEAM` error code |
| 4 | `test_sprint_status_with_full_id` | UX-03 / D-24 | status shape |
| 5 | `test_sprint_status_with_prefix` | UX-03 / D-25 | prefix resolution |
| 6 | `test_sprint_status_ambiguous_prefix_reports_candidates` | D-25 | `AMBIGUOUS_SPRINT` + candidates list |
| 7 | `test_sprint_status_not_found` | D-25 | `SPRINT_NOT_FOUND` |
| 8 | `test_sprint_show_full_state` | UX-05 / D-24 | full-state shape |
| 9 | `test_sprint_list_requires_team` | Pitfall #9 | list `MISSING_TEAM` |
| 10 | `test_sprint_list_returns_all_sprints_for_team` | UX-04 | list results |
| 11 | `test_sprint_pause_flips_status` | CORE-07 | pause persistence |
| 12 | `test_sprint_resume_flips_status_back_to_running` | CORE-07 | resume round-trip |
| 13 | `test_sprint_start_respects_artifact_cap_flag` | D-29 | CLI flag → `artifact_cap_bytes` (KB→bytes) |
| 14 | `test_sprint_start_respects_auto_advance_flag` | D-23 | `--no-auto-advance` honored |
| 15 | `test_json_envelope_shape_uniform_across_commands` | UX-09 / D-26 | 4-key envelope across all 6 commands |

### 4. `tests/test_sprint_conductor.py` — 4 helper tests appended (+89 LOC)

- `test_most_recent_artifact_returns_name_when_artifacts_nonempty`
- `test_most_recent_artifact_returns_empty_when_no_artifacts`
- `test_status_dict_shape` — asserts exact key set + counts
- `test_show_dict_shape` — asserts exact key set + artifact-body exclusion (uses unique tokens to avoid false positives)

## JSON Envelope Shape (D-26) — Confirmed Uniform

Success payload (every `ok=True` command):

```json
{
  "ok": true,
  "data": {...command-specific fields...},
  "warnings": [],
  "error": null
}
```

Error payload (every `ok=False` command, across all error branches):

```json
{
  "ok": false,
  "data": null,
  "warnings": [],
  "error": {"code": "MACHINE_CODE", "message": "human-readable text"}
}
```

Test 15 (`test_json_envelope_shape_uniform_across_commands`) asserts `set(payload.keys()) == {"ok", "data", "warnings", "error"}` across all 6 commands.

## Error Code Table

| Code | Exception Class | HTTP-Like Semantic | Trigger |
|------|-----------------|--------------------|---------|
| `MISSING_TEAM` | `MissingTeamError` | 400 Bad Request | `--team` flag + `CLAWTEAM_TEAM` env both absent |
| `AMBIGUOUS_SPRINT` | `AmbiguousSprintError` | 409 Conflict | Prefix matches >1 sprint; `message` embeds `candidates` list |
| `SPRINT_NOT_FOUND` | `SprintNotFoundError` | 404 Not Found | Prefix matches 0 sprints |
| `START_FAILED` | unhandled `Exception` | 500 Internal Error | `start_sprint` raises anything not caught above |
| `PAUSE_FAILED` | unhandled `Exception` | 500 Internal Error | `pause(sprint_id)` raises post-resolution |
| `RESUME_FAILED` | unhandled `Exception` | 500 Internal Error | `resume(sprint_id)` raises post-resolution |
| `IMPORT_FAILED` | `ImportError` | 500 Internal Error | Defensive — conductor module import fails (unreachable in practice) |

## BC Invariant (Pitfall #8) — Phase 0 Regression Matrix 12/12 Held

- `tests/test_template_regression_matrix.py`: **12/12 passing** after this plan.
- `tests/test_cli_commands.py`: **20/20 passing** (no existing test edits).
- Existing `guard_app` sub-app preserved — 5 decorator matches remain (`guard_app = typer.Typer` + 4 `@guard_app.command`).
- Every `add_typer(...)` call from Plan 02-10 and earlier sub-apps remains untouched.

## Deviations from Plan

### Deviations Applied

**1. [Rule 1 — Test fix] `state.team_name` → `state.team` in helper tests.**

The plan's proposed Task 1 helpers referenced `state.team_name`, but `SprintState` exposes the field as `team` (see `clawteam/sprint/state.py:44`). `SprintConductor.team_name` is the conductor-level attribute. Used `state.team` in both `status_dict` / `show_dict` bodies and the matching tests; `d["team"] == "t"` assertions pass identically (the conductor writes `team=self.team_name` at `start_sprint` time, so the round-trip preserves the value).

**2. [Rule 1 — Test fix] Artifact-body exclusion assertion.**

The plan's proposed `test_show_dict_shape` used single-character artifact bodies (`"x"` / `"y"`) and asserted substring-absence in `json.dumps(d)`. Single chars falsely collide with JSON punctuation (`"phase_history": [...]` contains `"y"`). Replaced bodies with unique tokens `BODY-ALPHA-UNIQUE-TOKEN` / `BODY-BETA-UNIQUE-TOKEN` so the assertion tests real exclusion. Implementation unchanged.

**3. [Rule 2 — Correctness] `typer.Exit` re-raise in exception handlers.**

In `sprint_start` / `sprint_pause` / `sprint_resume`, the broad `except Exception` catches would swallow `typer.Exit(1)` raised by inner `_sprint_emit_err` calls (defensive pattern already used by `guard_app` — see `commands.py:4725`). Added explicit `except typer.Exit: raise` before the generic catch so the error envelope propagates cleanly.

**4. [Rule 1 — Docstring fix] `_resolve_sprint_or_err` return annotation.**

Kept the mixed-tuple return annotation loose (`return c, state` on success, `return None, None` on unreachable fallback) since `typer.Exit` is raised via `_sprint_emit_err`; callers always check `if c is None or state is None` before dereferencing per the plan's own shape.

### No Other Deviations

The 15 CliRunner tests, 6 sub-commands, 4 helpers, 3 conductor serialization methods, and uniform envelope shape all landed exactly as specified in the `<must_haves>` and `<behavior>` blocks.

## Forward Contracts

### Phase 4 — `clawteam sprint approve <id> --phase ship`

The plan 02-12 sub-app is the natural home for an `approve` sub-command when Plan 04-XX wires human-gated phase transitions (`InteractionGate`-driven). Add via:

```python
@sprint_app.command("approve")
def sprint_approve(sprint_id, phase, team=...): ...
```

No changes to existing 6 commands needed; error codes `APPROVAL_FAILED` / `PHASE_MISMATCH` can slot into the same envelope.

### Phase 7 — `clawteam attend` (cross-sprint attention queue)

`attend` is a SIBLING top-level sub-app (e.g., `attend_app = typer.Typer(...)` + `app.add_typer(attend_app, name="attend")`) NOT a sub-command of `sprint`, because it aggregates across sprints team-wide and doesn't take a sprint id. The Pitfall #9 `--team` guard (via `_resolve_team_arg`) is reusable — factor that helper into `clawteam/cli/_sprint_helpers.py` when Phase 7 lands if duplication pressure shows up.

### Phase 3 — Future `SprintConductor.artifact_dict(state, name)`

A future `artifact_dict(state, name) → {name, body}` helper on `SprintConductor` pairs with a `clawteam sprint artifact <id> <name>` sub-command to stream individual artifact bodies on demand. Phase 2 deliberately excludes bodies from `show_dict` to keep JSON bounded; the Phase 3 plugin that registers gstack artifact names is the natural place to add the `artifact` sub-command.

## Threat Flags

None — the Plan 02-12 `<threat_model>` already registered all CLI-layer threats (T-02-24..T-02-27 + Pitfall #8/#9). Trust boundary inventory is complete; no new surface introduced beyond what the plan anticipated.

## Self-Check: PASSED

- [x] `clawteam/cli/commands.py` — modified, 5158 lines, 1 `sprint_app` declaration, 6 `@sprint_app.command` decorators, 4 helper functions present
- [x] `clawteam/sprint/conductor.py` — modified, 544 lines, 3 helper methods present (`most_recent_artifact` / `status_dict` / `show_dict`)
- [x] `tests/test_sprint_cli.py` — created, 358 lines, 15 tests pass
- [x] `tests/test_sprint_conductor.py` — modified, 545 lines, 21 tests pass (17 existing + 4 new)
- [x] Commit `af6b7d0` present: `git log --oneline | grep af6b7d0` → yes
- [x] Commit `60ad26e` present: `git log --oneline | grep 60ad26e` → yes
- [x] `python -c "from clawteam.cli.commands import sprint_app; print([c.name for c in sprint_app.registered_commands])"` → `['start', 'status', 'show', 'list', 'pause', 'resume']`
- [x] Existing `guard_app` preserved: `grep -c "guard_app = typer.Typer\|@guard_app.command" commands.py` → 5
- [x] Phase 0 regression matrix green: `pytest tests/test_template_regression_matrix.py` → 12/12
- [x] Ruff clean on all modified files
