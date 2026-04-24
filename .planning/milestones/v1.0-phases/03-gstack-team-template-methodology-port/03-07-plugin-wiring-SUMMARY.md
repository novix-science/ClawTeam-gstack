---
phase: 03-gstack-team-template-methodology-port
plan: 07
subsystem: gstack-template
tags: [plugin, harness, phase-registry, evidence-schema, cross-template-isolation]
requirements: [TEAM-04, SPRINT-06]
dependency-graph:
  requires:
    - "clawteam/plugins/base.py (HarnessPlugin ABC — 5 hooks consumed)"
    - "clawteam/plugins/manager.py (PluginManager._instantiate_and_register)"
    - "clawteam/harness/phase_registry.py (PhaseRegistry — contribute_phases consumer)"
    - "clawteam/harness/evidence_schemas.py (EvidenceSchemaRegistry — contribute_evidence_schemas consumer)"
    - "clawteam/events/types.py::PhaseTransition (Phase 2 event for Reflect handler)"
    - "clawteam/templates/gstack/schemas/__init__.py (6 pydantic schemas from 03-03)"
    - "clawteam/templates/gstack/prompts/<role>.md × 11 (from 03-05 + 03-06)"
    - "clawteam/team/manager.py::_load_config (template lookup for isolation)"
    - "clawteam/team/envelope.py::parse_frontmatter (retro.md frontmatter split)"
    - "clawteam/fileutil.py::file_locked (atomic _phase6_pending/ write)"
    - "clawteam/sprint/state.py::load_sprint_state (fallback sprint_id resolution)"
  provides:
    - "clawteam/plugins/gstack_sprint_plugin.py::GstackSprintPlugin — single cohesive plugin"
    - "GSTACK_PHASES, GSTACK_ROLES, PROMPTS_DIR module-level constants"
    - "_phase6_pending/<sprint_id>-retro.json placeholder file (D-09 shape)"
  affects:
    - "03-08 team show CLI: can scan <data_dir>/teams/<team>/_phase6_pending/ for dashboard 'memory pending' column"
    - "03-09 cross-template regression: can assert GstackSprintPlugin().contribute_phases() AND 6 existing templates spawn unchanged"
    - "Phase 6 /learn: backfill scanner reads _phase6_pending/ directory"
tech-stack:
  added: []
  patterns:
    - "Pattern 2: single cohesive plugin file (~334 LOC, mirrors ralph_loop_plugin.py)"
    - "Pattern 4: leader-role binding — plugin populates registries conductor reads (no subclassing)"
    - "Pattern 5: 6 pydantic schemas keyed by artifact_type Literal discriminator"
    - "Pattern 6: Reflect-phase event handler + Phase 6 stub"
key-files:
  created:
    - "clawteam/plugins/gstack_sprint_plugin.py (334 LOC)"
  modified:
    - "tests/test_gstack_plugin.py (10 active tests, 319 LOC)"
decisions:
  - "Sprint_id is NOT on PhaseTransition today — plugin supports getattr(event, 'sprint_id', None) for future compat AND falls back to walking <data_dir>/teams/<team>/sprints/ for the one with current_phase=='reflect'."
  - "Template lookup uses clawteam.team.manager._load_config (lazy import) rather than a new public get_team_config function — avoids introducing API surface for internal plumbing."
  - "Two-layer path traversal defense: GSTACK_ROLES containment check + _valid_role() (defense-in-depth; grep-able security intent)."
  - "Evidence-schema + phase registries reset in BOTH setup AND teardown to avoid cross-test-module collision (some other test modules register 'design-doc' as a bare type sentinel)."
metrics:
  duration: ~45min
  completed: 2026-04-21
  tasks_completed: 4
  files_touched: 2
  commits: 4
  test_counts:
    before: "5 skipped"
    after: "10 passed"
---

# Phase 03 Plan 07: Plugin Wiring Summary

**GstackSprintPlugin — single cohesive 334 LOC plugin that wires the 7 gstack phases, 6 evidence schemas, 11 role prompts, and the Reflect-phase /learn placeholder into the Phase 1/2 substrate without affecting the 6 existing templates.**

## What Shipped

### `clawteam/plugins/gstack_sprint_plugin.py` (334 LOC)

Single cohesive plugin file mirroring `ralph_loop_plugin.py` (Pattern 2). All hooks gated on gstack-role / gstack-template context so loading this plugin does NOT affect the 6 existing templates (CORE-03 + QUALITY-14; Pitfall 14 prevention).

**5 HarnessPlugin hooks implemented:**

| Hook                         | Signature                                            | Purpose                                                                         |
| ---------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------- |
| `contribute_phases`          | `() -> list[str]`                                    | Returns `GSTACK_PHASES` (7 ordered phase strings)                               |
| `contribute_evidence_schemas`| `() -> dict[str, type]`                              | Returns 6 pydantic schemas keyed by `artifact_type` Literal discriminator       |
| `contribute_prompts`         | `(phase: str, role: str) -> str`                     | Resolves `prompts/<role>.md` for 11 gstack roles; `""` for non-gstack roles     |
| `on_register`                | `(ctx: HarnessContext) -> None`                      | Subscribes `_on_phase_transition` to `PhaseTransition` at priority -10          |
| `contribute_review_routers`  | inherits default `return []`                         | Deferred to Phase 4 per Pitfall 7 boundary                                      |

**Helper + handler methods:**

- `_valid_role(role)` — module-level path-traversal guard (rejects `/`, `\`, `..`, non-ASCII).
- `_on_phase_transition(event)` — filters `to_phase == "reflect"` AND `template == "gstack"` before acting.
- `_resolve_team_template(team_name)` — loads `TeamConfig` via `clawteam.team.manager._load_config` and returns `.template` string (or `""` on failure).
- `_find_reflecting_sprint(team_name)` — walks `<data_dir>/teams/<team>/sprints/` and returns `sprint_id` of the one with `current_phase == "reflect"` (fallback when event lacks `sprint_id`).
- `_load_and_validate_retro(team_name, sprint_id)` — round-trips `artifacts/retro.md` frontmatter through the `Retro` pydantic schema; returns `(body, personas)` or `(None, [])`.
- `_write_phase6_pending(team_name, sprint_id, retro_body, personas)` — atomic `file_locked()` write of the D-09 JSON placeholder.

### `tests/test_gstack_plugin.py` (319 LOC, 10 passing)

All Wave 0 `@pytest.mark.skip` decorators removed; test bodies filled in. Both registries reset in setup/teardown.

| Test                                                            | Coverage                                                                |
| --------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `test_seven_phases_registered`                                  | `contribute_phases()` order                                             |
| `test_seven_phases_registered_in_order`                         | Full `PluginManager._instantiate_and_register` -> `PhaseRegistry`       |
| `test_six_schemas_registered`                                   | `contribute_evidence_schemas` keys + identity                           |
| `test_six_evidence_schemas_registered`                          | Full `PluginManager` -> `EvidenceSchemaRegistry` round-trip             |
| `test_prompts_resolve_for_all_eleven_roles`                     | All 11 `SIGNATURE: gstack-role:<role>` lines present                    |
| `test_prompts_reject_path_traversal`                            | 4 traversal payloads return `""` (T-07-02)                              |
| `test_only_ceo_advances_phase`                                  | `advance_phase(actor="")` signature regression (TEAM-04 from 03-01)     |
| `test_reflect_phase_learn_stub_writes_placeholder`              | Full `_phase6_pending/<sprint>-retro.json` round-trip (SPRINT-06)       |
| `test_plugin_inert_for_non_gstack_team`                         | T-07-01 HIGH: `template="software-dev"` does NOT write placeholder      |
| `test_non_gstack_template_does_not_load_gstack_plugin`          | Pitfall 14 scaffold: 6 existing templates all no-op                     |

## T-07-01 HIGH Mitigation: Three-Layer Cross-Template Isolation

The plugin loads globally when discovered by `PluginManager`, but each consumption layer enforces gstack-only scope. Verified by these tests:

| Layer                  | Mechanism                                              | Test                                                             |
| ---------------------- | ------------------------------------------------------ | ---------------------------------------------------------------- |
| 1. Phase registration  | Other templates declare their own phase set; never iterate gstack phases | `test_seven_phases_registered_in_order` + cross-template scaffold in 03-09 |
| 2. Prompt resolution   | `role not in GSTACK_ROLES` returns `""` immediately    | `test_prompts_resolve_for_all_eleven_roles` (non-gstack branch)  |
| 3. Event handler       | `template_name != "gstack"` early-return before write  | `test_plugin_inert_for_non_gstack_team` + `test_non_gstack_template_does_not_load_gstack_plugin` |

## Reflect-Phase Output Shape (D-09)

Example `<data_dir>/teams/acme/_phase6_pending/sprint001-retro.json`:

```json
{
  "sprint_id": "sprint001",
  "team_name": "acme",
  "retro_body": "# Retro body.\n\nEverything we learned.\n",
  "personas": ["eng-mgr", "ceo", "engineer"],
  "feature_flag": "phase6_learn_pending",
  "written_at": "2026-04-21T05:30:00+00:00"
}
```

Fields verified by `test_reflect_phase_learn_stub_writes_placeholder`. The body is the full markdown retro minus frontmatter; personas come from `Retro.personas` after pydantic validation (stub-grade retros fail the schema and never reach the placeholder).

## Phase Boundary Confirmations

- **03-08 (team show CLI):** Dashboard can `glob(<data_dir>/teams/<team>/_phase6_pending/*.json)` to surface a "Memory pending" column. File shape is stable (JSON, keyed on `sprint_id`).
- **03-09 (cross-template regression):** Can assert `GstackSprintPlugin().contribute_phases() == GSTACK_PHASES` AND spawn each of the 6 existing templates with the plugin loaded — `test_non_gstack_template_does_not_load_gstack_plugin` is the 03-07-scoped scaffold for that 03-09 regression.
- **Phase 4 SmartReviewRouter:** Plugin uses `HarnessPlugin.contribute_review_routers`'s default (`return []`). Phase 4 adds router logic.
- **Phase 6 /learn:** Backfill scanner walks `_phase6_pending/` directories on first `/learn` startup (D-09); file shape frozen here.

## Deviations from Plan

**None — plan executed as written.**

The plan specified `getattr(event, "phase_target", None) or getattr(event, "target", None)` for phase extraction; actual `PhaseTransition` event (verified `clawteam/events/types.py:170`) uses `to_phase`. Plugin accepts all three shapes defensively; tests use `to_phase` (the canonical shape). This is the type of harmless drift the plan's `<interfaces>` block anticipated ("If the event name differs in the actual codebase (verify during Read pass), adapt subscribe call accordingly") — not a true deviation.

## Deferred Issues

- **Pre-existing `tests/test_sprint_conductor.py::test_resume_after_process_restart` subprocess failure** — discovered during targeted regression check; unrelated to 03-07 scope. Logged in `.planning/phases/03-gstack-team-template-methodology-port/deferred-items.md`.

## Commits

- `c5bf890` feat(03-07): scaffold GstackSprintPlugin with contribute_phases + contribute_evidence_schemas
- `7704030` feat(03-07): add contribute_prompts with role guard + mtime cache
- `6e7f1e5` feat(03-07): on_register Reflect-phase handler writes _phase6_pending/ placeholder per D-09
- `444bf1c` test(03-07): un-skip test_gstack_plugin.py with 10 active tests + cross-template isolation

## Self-Check: PASSED

- File `clawteam/plugins/gstack_sprint_plugin.py` exists (334 LOC, under 400 LOC cap)
- File `tests/test_gstack_plugin.py` active (10 passing tests, 0 skipped, 0 xfailed)
- All 4 commit hashes found in `git log --oneline`
- Targeted regression (149 tests across 6 test modules) passes
- Plugin imports resolve; `GstackSprintPlugin` is a `HarnessPlugin` subclass
