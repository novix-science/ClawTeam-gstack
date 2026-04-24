---
phase: 03-gstack-team-template-methodology-port
plan: 08
subsystem: cli
tags: [typer, rich-table, dashboard, ux-07, team-show, gstack, phase6-placeholder, phase7-placeholder]

# Dependency graph
requires:
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: SprintConductor.list_sprints + SprintState model used by the active-sprint row
  - phase: 03-gstack-team-template-methodology-port (03-02)
    provides: TeamConfig.template + TeamConfig.leader_role fields + TemplateDef.phases; TeamManager.create_team roles/leader_role/template kwargs
  - phase: 03-gstack-team-template-methodology-port (03-07)
    provides: `_phase6_pending/<sprint-id>-retro.json` placeholder files written by GstackSprintPlugin Reflect handler — counted by the memory row
provides:
  - `clawteam team show <name>` Typer subcommand rendering 4-section team dashboard
  - Rich human layout + JSON contract for UX-09 machine-readable discipline
  - Cross-template BC: non-gstack teams see roster + sprint row; memory/cost rows degrade to N/A
  - Forward-compatible swap points for Phase 6 (`pending_phase_6` literal + `_phase6_pending` glob) and Phase 7 (`pending_phase_7` literal + `costRollup` dict)
affects: [phase-04-interactive-verification, phase-06-browser-memory, phase-07-cost-observability, 03-09-regression]

# Tech tracking
tech-stack:
  added: []  # reuses existing typer + rich.Table + TeamManager + SprintConductor
  patterns:
    - "Dashboard-as-composition: team_show is a pure read + render that composes TeamManager.get_team + SprintConductor.list_sprints + _phase6_pending glob into one rich.Table layout — no new state mutation surface"
    - "Placeholder-with-swap-point: Phase 6 + Phase 7 features surface as typed rows (pending_phase_6 / pending_phase_7) so future phases drop in structured data without breaking the JSON contract"
    - "Best-effort subsystem lookup: _team_show_active_sprint wraps SprintConductor.list_sprints in try/except so dashboard renders roster even if sprint machinery faults (UX-07 requires roster visibility as the floor)"

key-files:
  created: []
  modified:
    - "clawteam/cli/commands.py — team_show command (lines 1730-1864) + _team_show_active_sprint helper (lines 1664-1705) + _team_show_phases_for_template helper (lines 1707-1727); ~200 LOC added between team_status and team_spawn"
    - "tests/test_cli_commands.py — 4 new tests covering UX-07 dashboard render + not-found + non-gstack fallback + JSON shape; uses real TeamManager.create_team (not mocks) for end-to-end validation"

key-decisions:
  - "Member rendering uses TeamMember.name as the role chip: Phase 3 TemplateDef extended AgentDef with .role but team_spawn adds members via TeamManager.add_member which only carries name/user/agent_id/agent_type. Since gstack.toml sets each AgentDef.name to the role identifier (e.g. name=\"pm\", name=\"ceo\"), .name IS the role name on disk — no schema change needed for the dashboard"
  - "Phase order sourced from TemplateDef.phases, not hardcoded: _team_show_phases_for_template reads TeamConfig.template → load_template(tmpl).phases so a future non-gstack template with its own phase order (e.g. think/build/ship) gets correct N/M phase indexing automatically"
  - "Best-effort sprint lookup: SprintConductor import + list_sprints wrapped in try/except returning None. UX-07 contract is 'roster visible' as the floor; sprint row degrades to 'none — run sprint start' on any lookup failure so a broken sprint substrate never hides the 11-specialist dashboard"
  - "Memory row gated strictly on template == \"gstack\": non-gstack templates never wrote to _phase6_pending/ (03-07 Reflect filter), so scanning is pointless AND misleading — the N/A degrade keeps cross-template BC without leaking gstack-specific vocabulary into other templates' dashboards"
  - "JSON shape matches plan contract verbatim: data dict keys {name, template, leaderRole, createdAt, description, members, activeSprint, memory:{status,placeholderEntries}, costRollup:{status,perAgent,totalTokens,totalUsd}} — structured fields placeholderEntries/perAgent/totalTokens/totalUsd reserve the Phase 6 + Phase 7 upgrade surface so future phases populate without renaming keys"

patterns-established:
  - "Pattern A (dashboard-as-composition): CLI commands that surface aggregate state compose existing read-side APIs rather than duplicate state; the team_show function demonstrates the 4-section pattern (header + roster table + contextual row + placeholder row) that can extend to future `clawteam sprint show`, `clawteam team cost` style commands"
  - "Pattern B (forward-compat placeholder literal): use a stable string literal (pending_phase_6, pending_phase_7) as the status discriminator so future phases flip one value and populate sibling fields without changing the JSON key shape — clients can feature-gate on the literal"

requirements-completed: [UX-07]

# Metrics
duration: ~20min
completed: 2026-04-21
---

# Phase 03 Plan 08: Team Show CLI — Summary

**Ships `clawteam team show <name>` Typer subcommand that renders a 4-section team dashboard (roster + active sprint + memory placeholder + cost rollup placeholder) per UX-07, with strict cross-template BC and Phase 6/7 swap points baked into the JSON contract.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-04-21T05:18:00Z
- **Completed:** 2026-04-21T05:38:00Z
- **Tasks:** 2 completed (both `type="auto"`, Task 2 TDD-flagged)
- **Files modified:** 2 (`clawteam/cli/commands.py`, `tests/test_cli_commands.py`)

## Accomplishments

- UX-07 shipped: `clawteam team show myteam` renders roster of all 11 gstack specialists, active sprint progress (N/7), Phase 6 pending count, and Phase 7 cost placeholder in one Rich-rendered dashboard
- Cross-template BC preserved: `clawteam team show legacy-team` (software-dev template) renders roster + memory = "N/A" without crashing or leaking gstack-specific vocabulary
- JSON contract locked: `clawteam --json team show ...` emits `{name, template, leaderRole, members, activeSprint, memory:{status,placeholderEntries}, costRollup:{status,perAgent,totalTokens,totalUsd}}` with stable `pending_phase_6`/`pending_phase_7` status literals as Phase 6/7 swap points
- 4 new tests in `tests/test_cli_commands.py` cover happy path + not-found + non-gstack fallback + JSON shape; all 24 `test_cli_commands.py` tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Author `team show` Typer command with dashboard composition** — `a13ec72` (feat)
2. **Task 2: Extend tests/test_cli_commands.py with 4 team_show tests** — `c89d78e` (test)

## Files Created/Modified

- `clawteam/cli/commands.py` — +208 lines between team_status (line 1656) and team_spawn (now line 1867). Added:
  - `_team_show_active_sprint(team)` helper (lines 1664-1705): best-effort sprint lookup via `SprintConductor.list_sprints`, returns `{sprintId, currentPhase, phaseIndex, goal, status}` dict or None on any failure
  - `_team_show_phases_for_template(team)` helper (lines 1707-1727): reads `TeamConfig.template` then `load_template(tmpl).phases` for N/M phase indexing; empty list on miss
  - `@team_app.command("show")` decorator + `def team_show(team)` (lines 1730-1864): TeamManager.get_team lookup → `typer.Exit(1)` on miss → compose data dict → `_human` renderer builds Rich header + roster table + sprint line + memory line + cost line → `_output(data, _human)` dual-path render
- `tests/test_cli_commands.py` — +162 lines:
  - `_GSTACK_ROLES` list + `_spawn_gstack_team_for_show()` helper (mirrors `team spawn gstack` semantics using real `TeamManager.create_team` + `add_member`)
  - `test_team_show_gstack_dashboard_renders_11_roles_and_placeholders` — happy path: 11 roles + Template/leader chip + "Phase 6 pending — 2 entries" + "Phase 7" cost stub
  - `test_team_show_not_found_returns_exit_code_1` — exit 1 + "not found" error message
  - `test_team_show_non_gstack_team_shows_na_memory_row` — CORE-03 BC: renders "software-dev" + "N/A" + no `_phase6_pending` leakage
  - `test_team_show_json_output_shape_matches_contract` — parses full stdout JSON; asserts all documented keys + `memory.status == "pending_phase_6"` + `costRollup.status == "pending_phase_7"` + 11-member roster

## JSON Output Shape (UX-09 contract)

```json
{
  "name": "str",
  "template": "str",                  // "" for teams created before 03-02
  "leaderRole": "str",                // "" if TeamConfig.leader_role unset
  "createdAt": "iso-8601 string",
  "description": "str",
  "members": [ /* TeamMember.model_dump(by_alias=True) */ ],
  "activeSprint": {                   // null when no non-completed sprint exists
    "sprintId": "str",
    "currentPhase": "str",
    "phaseIndex": "str (N/M or ?/M or empty)",
    "goal": "str",
    "status": "str"
  } | null,
  "memory": {
    "status": "pending_phase_6" | "not_applicable",
    "placeholderEntries": "int"
  },
  "costRollup": {
    "status": "pending_phase_7",
    "perAgent": [],
    "totalTokens": null,
    "totalUsd": null
  }
}
```

## Phase 6 Upgrade Path (TeamMemoryStore + real `/learn`)

Two well-defined swap points in `clawteam/cli/commands.py::team_show`:

1. **Memory glob swap (line ~1764-1767):** Replace
   ```python
   if template_name == "gstack":
       pending_dir = get_data_dir() / "teams" / team / "_phase6_pending"
       if pending_dir.is_dir():
           memory_placeholder_count = len(list(pending_dir.glob("*-retro.json")))
   ```
   with a call into `TeamMemoryStore(team).recent_entries(limit=N)` (or equivalent). Change the data dict to populate `memory["entries"]` with the retrieved highlights and flip `memory["status"]` from `"pending_phase_6"` to `"populated"` (or similar stable literal).

2. **Memory row renderer (line ~1849-1856):** Replace the "`Memory: Phase 6 pending — N entries in _phase6_pending/`" line with a Rich.Table rendering of the actual memory highlights (role column + summary column + provenance/timestamp column).

The 03-07 backfill scanner (Phase 6 backfill task) drains `_phase6_pending/` on first `/learn` write; after backfill, the glob naturally returns 0 and the placeholder row degrades cleanly during migration.

## Phase 7 Upgrade Path (AttentionQueue + cost dashboard)

Two swap points in `clawteam/cli/commands.py::team_show`:

1. **Cost rollup data shape (line ~1785-1791):** Replace the static
   ```python
   "costRollup": {
       "status": "pending_phase_7",
       "perAgent": [],
       "totalTokens": None,
       "totalUsd": None,
   }
   ```
   with a call into the Phase 7 cost accumulator (e.g. `CostTracker(team).rollup()`) that returns `{status: "populated", perAgent: [{role, tokens, usd}, ...], totalTokens, totalUsd}`. The existing JSON contract keys (`perAgent`, `totalTokens`, `totalUsd`) are already reserved — Phase 7 just populates them.

2. **Cost row renderer (line ~1859-1861):** Replace the "`Cost rollup: pending Phase 7 observability`" line with a Rich.Table rendering of per-agent tokens/USD + total row. The `costRollup.perAgent` array is already the right shape.

## 03-09 Handoff

Plan 03-09 (Wave 4 sibling — running in parallel) extends `tests/test_gstack_team_spawn.py` and `tests/test_template_regression_matrix.py` to cross-verify:

- Non-gstack teams reach the `team show` dashboard and render roster + sprint row + N/A memory row (CORE-03 cross-template isolation)
- The 4 new team_show tests here form the per-command correctness floor; 03-09's regression matrix covers the cross-template isolation floor
- No file overlap: 03-08 scope = `clawteam/cli/commands.py` + `tests/test_cli_commands.py`; 03-09 scope = `tests/test_gstack_team_spawn.py` + `tests/test_template_regression_matrix.py` (confirmed clean at merge time)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Plan's suggested `m.get("role", "") or m.get("name", "")` fallback for role column was wrong**

- **Found during:** Task 1 implementation read of `clawteam/team/models.py`
- **Issue:** The plan's member row renderer assumed `m.get("role")` would resolve to the role name, but `TeamMember` (the on-disk model) has no `role` field — only `AgentDef` (template-time) does. After `team spawn`, members are persisted via `TeamManager.add_member` which drops the `.role`. The fallback would always hit `m.get("name", "")`.
- **Fix:** Simplified the renderer to use `m.get("name", "")` directly (since gstack.toml sets each `AgentDef.name` to the role identifier — e.g. `name = "pm"`, `name = "ceo"` — so `.name` IS the role chip on disk). No schema change needed. All 11 roles still render correctly because the member `.name` values ARE the role strings.
- **Files modified:** `clawteam/cli/commands.py` (lines 1826-1833)
- **Commit:** `a13ec72`

**2. [Rule 3 — Blocking] Plan's `_team_show_active_sprint` used speculative `SprintStore.list_for_team(team)` API that doesn't exist**

- **Found during:** Task 1 read of `clawteam/sprint/conductor.py`
- **Issue:** The plan's helper guessed `SprintStore.list_for_team(team)` as the sprint-listing API, but the real API is `SprintConductor(team_name=team).list_sprints()` (verified at conductor.py:405).
- **Fix:** Rewrote the helper to instantiate `SprintConductor(team_name=team)` and call `list_sprints()`. Also added `_team_show_phases_for_template(team)` to read phase order from `TemplateDef.phases` (since `SprintState` carries `current_phase` but not the phase list — only the template knows the canonical phase order).
- **Files modified:** `clawteam/cli/commands.py` (lines 1664-1727)
- **Commit:** `a13ec72`

**3. [Rule 3 — Blocking] JSON test's `--json` fallback path was unnecessary**

- **Found during:** Task 2 smoke test
- **Issue:** Plan suggested a fallback (`env={"CLAWTEAM_OUTPUT": "json"}`) in case `--json` wasn't the root flag; actual verification showed `--json` IS the root callback option (commands.py:88) and works cleanly on `runner.invoke(app, ["--json", "team", "show", "..."])`.
- **Fix:** Simplified `test_team_show_json_output_shape_matches_contract` to use only the `--json` root flag; no fallback branch. Parses the FULL stdout as JSON (not a "last JSON-looking line" heuristic) since `--json` prints one complete document.
- **Files modified:** `tests/test_cli_commands.py` (lines 718-745)
- **Commit:** `c89d78e`

### Architectural Changes

None.

### Auth Gates

None.

## Known Stubs

None. The Phase 6 `pending_phase_6` and Phase 7 `pending_phase_7` literals in the data dict ARE intentional placeholders — the plan's explicit scope (UX-07 ships placeholders; Phase 6 fills memory; Phase 7 fills cost). Both are tracked in this SUMMARY (see Phase 6 + Phase 7 upgrade paths above) with exact line numbers for the future swap.

## Self-Check: PASSED

- `clawteam/cli/commands.py` contains `@team_app.command("show")` at line 1730: FOUND
- `clawteam/cli/commands.py` contains `def team_show` at line 1731: FOUND
- `clawteam/cli/commands.py` contains `def _team_show_active_sprint` at line 1664: FOUND
- `clawteam/cli/commands.py` contains `def _team_show_phases_for_template` at line 1707: FOUND
- `tests/test_cli_commands.py` contains 4 `def test_team_show_` functions: FOUND (lines 626, 666, 681, 718)
- `tests/test_cli_commands.py` contains `pending_phase_6` + `pending_phase_7` literals: FOUND (lines 742, 744)
- Commit `a13ec72`: FOUND (feat 03-08)
- Commit `c89d78e`: FOUND (test 03-08)
- `python -m clawteam team show --help` exits 0 and mentions "dashboard": FOUND
- `pytest tests/test_cli_commands.py -q` → 24 passed: FOUND
- `pytest tests/test_cli_commands.py -k 'team_show' -q` → 4 passed: FOUND
