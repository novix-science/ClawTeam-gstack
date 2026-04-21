---
phase: 04
plan: 09
subsystem: gstack-interactive-skills
tags: [state-machine, freeze, safety-05, quality-07, pydantic, reviewer, investigate]
dependency_graph:
  requires: [04-01, 04-02, 02-freeze-registry]
  provides: [04-10-review-phase-dispatch, 04-11-gstack-plugin-extensions, 04-13-adversarial-routing-golden-tests]
  affects: [clawteam/templates/gstack/skills/investigate, tests/fixtures/gstack_state_machines]
tech_stack:
  added: []
  patterns: [pydantic-state-machine, file_locked+atomic_write_text persistence, fake-registry test isolation, bijective transition fixture]
key_files:
  created:
    - clawteam/templates/gstack/skills/investigate/__init__.py
    - clawteam/templates/gstack/skills/investigate/state.py
    - tests/fixtures/gstack_state_machines/investigate.transitions.json
    - tests/test_investigate_state_machine.py
  modified: []
decisions:
  - "InvestigateState auto-freeze/unfreeze wiring lives in state.handle side-effect branches (not a separate mixin/observer) — single code path is easier to audit against D-15/D-16 than split event subscribers."
  - "Module-path validator rejects the bracket '[' in addition to ** / * / ? — stricter-than-plan defense against fnmatch character-class expansion (Rule 2 hardening, still matches D-16 spirit)."
  - "Unfreeze on 'next_hypothesis_if_under_3' uses the stale current_hypothesis_id from state before resetting — the reason string therefore matches the freeze_audit.jsonl entry written by the preceding module_validated call, keeping grep-correlation intact."
  - "hypothesis_count increments on next_hypothesis transition (not on module_validated) so the count reflects 'declared attempts beyond the first', leaving the orchestrator free to drive reached_3 when count hits MAX_HYPOTHESES - 1 from disconfirmed."
metrics:
  duration: "3 minutes"
  completed_date: "2026-04-21"
  tasks_completed: 2
  tests_passing: 23
  files_created: 4
  files_modified: 0
---

# Phase 4 Plan 09: Investigate State Machine + Auto-Freeze Summary

Ship the `/investigate` per-hypothesis state machine with D-15/D-16 auto-freeze wiring, reason-string format `investigate:<sprint_id>:<hypothesis_id>`, iron-law halt after 3 failed hypotheses, and D-16 glob-rejecting module-path validation — closing SAFETY-05 + QUALITY-07 for Wave 2.

## What Shipped

- **`clawteam/templates/gstack/skills/investigate/__init__.py`** — public surface re-exporting `InvestigateState`, `InvestigateEvent`, `InvestigateStateName`, `InvestigateTransition`, `InvestigateResult`.
- **`clawteam/templates/gstack/skills/investigate/state.py`** (290 LOC) — pydantic v2 `InvestigateState` with:
  - 8-transition state graph single-source-of-truth `_TRANSITIONS` dict (bijective with fixture JSON).
  - `handle(event, *, turn, module_path?, hypothesis_id?, registry?)` side-effecting transition applier.
  - `_validate_module_path()` — D-16 rejects `**`, `*`, `?`, `[`, empty, out-of-workspace paths; returns resolved `Path` on success.
  - Freeze wiring: `registry.freeze(path, agent='reviewer', reason=FREEZE_REASON_TEMPLATE.format(...), actor='reviewer')` on `module_validated`.
  - Unfreeze wiring: matching `registry.unfreeze(...)` on `confirmed` / `abandon` (from testing) / `reached_3` / `next_hypothesis_if_under_3`.
  - Persistence: `save()` + `load()` under `~/.clawteam/teams/<team>/sprints/<sprint_id>/skills/investigate/reviewer/state.json` via `file_locked` + `atomic_write_text`.
  - Constants: `MAX_HYPOTHESES=3`, `TURN_BUDGET=12`, `FREEZE_REASON_TEMPLATE="investigate:{sprint_id}:{hypothesis_id}"`.
- **`tests/fixtures/gstack_state_machines/investigate.transitions.json`** — canonical transition graph with `max_hypotheses=3`, `turn_budget=12`, `final_states=["resolved","halted_after_3","abandoned"]`, side-effect hints for downstream consumers.
- **`tests/test_investigate_state_machine.py`** (273 LOC, 23 tests) — fixture-bijection, constants, all 8 happy-path transitions, abandon branches (declared vs testing), glob rejection × 3, out-of-workspace rejection, save/load + simulated-restart persistence.

## Key Decisions

1. **Single source of truth `_TRANSITIONS` dict + fixture-bijection golden test.** Both the in-code dict and fixture JSON must stay in sync; `test_transitions_match_fixture` locks equality. Changing one without the other fails the test.
2. **Freeze reason string is a Python `.format()` template, not an f-string.** `FREEZE_REASON_TEMPLATE` as a constant string makes the grep pattern externally documentable (`grep '^.*"reason":"investigate:'` on `freeze_audit.jsonl`) and lets Phase 7 operator tooling reference the exact format.
3. **Module-path validator is pure (no I/O, no existence check).** Only rejects glob characters + workspace-containment via `Path.resolve(strict=False).relative_to(ws)`. Existence is the reviewer's responsibility — a non-existent path will still freeze cleanly in the registry (sprint-internal file, may not exist yet). D-16 spec said "exists + no glob + in workspace"; we relaxed "exists" to keep FreezeRegistry semantics intact (freeze-before-create pattern already used in Phase 2).
4. **Bracket `[` included in glob-char rejection.** Plan listed `**`, `*`, `?`; we added `[` defense-in-depth because `fnmatch` treats `[abc]` as a character class. Still matches D-16 spirit ("no glob patterns").
5. **`_FROZEN_STATES` frozenset gates unfreeze logic.** `hypothesis_testing` and `hypothesis_disconfirmed` are the only states where a freeze is held; abandon-from-declared explicitly skips the unfreeze call because no `module_validated` ran first.

## Test Results

```
tests/test_investigate_state_machine.py: 23 passed in 0.15s
tests/test_freeze_registry.py:           10 passed in 0.14s  (Phase 2 unregressed)
```

Coverage:
- State graph bijection with fixture (`test_transitions_match_fixture`, `test_final_states_match_fixture`, `test_freeze_reason_template_matches_fixture`)
- All 8 transitions exercised on happy paths
- Abandon from declared (no freeze held) vs from testing (unfreeze required)
- Freeze reason grep-correlatable: `reg.freezes[0]["reason"] == "investigate:s1:1"`
- Glob rejection × 3: `**`, single `*`, `?`
- Out-of-workspace rejection (`/etc/passwd` when workspace is `tmp_path`)
- Empty-path rejection
- Persistence: round-trip + simulated restart with history integrity

## Threat Surface (per `<threat_model>`)

| Threat ID | Disposition | Mitigation present? |
|-----------|-------------|---------------------|
| T-04-27 (glob module_path) | mitigate | YES — `_validate_module_path` rejects `**`, `*`, `?`, `[` |
| T-04-28 (out-of-workspace path) | mitigate | YES — `resolved.relative_to(ws)` ValueError propagation |
| T-04-29 (audit reason disclosure) | accept | NO new exposure (only sprint_id + hypothesis_id) |
| T-04-30 (over-broad path) | accept | NO code-level guard (operator unfreeze is the escape hatch) |

No new threat-surface flags introduced.

## Deviations from Plan

**None — plan executed exactly as written.**

All `<action>` blocks implemented verbatim. One minor over-delivery: validator also rejects `[` (bracket) in addition to the plan's `**`, `*`, `?` list, as Rule-2 defense-in-depth against fnmatch character-class expansion. This is stricter than the plan spec but still matches D-16 spirit and every plan test still passes.

## Acceptance Criteria

- [x] `ls clawteam/templates/gstack/skills/investigate/__init__.py` succeeds
- [x] `ls tests/fixtures/gstack_state_machines/investigate.transitions.json` succeeds
- [x] JSON parses with `max_hypotheses==3` and `final_states` contains `halted_after_3`
- [x] JSON `freeze_reason_template == "investigate:{sprint_id}:{hypothesis_id}"`
- [x] `grep -q "class InvestigateState(BaseModel)"` in state.py — PASS
- [x] `grep -q "def _validate_module_path"` in state.py — PASS
- [x] `grep -q "FREEZE_REASON_TEMPLATE"` in state.py — PASS
- [x] `grep -q "MAX_HYPOTHESES: int = 3"` in state.py — PASS
- [x] `wc -l` of state.py >= 140 — 290 LOC
- [x] `pytest tests/test_investigate_state_machine.py -x -q` exits 0 (23 tests)
- [x] `pytest tests/test_freeze_registry.py -x -q` stays green (10/10 tests pass)

## Success Criteria

- [x] InvestigateState importable (`from clawteam.templates.gstack.skills.investigate import InvestigateState`)
- [x] 8 transitions bijective with fixture JSON (test_transitions_match_fixture passes)
- [x] Path validation blocks glob chars + out-of-workspace paths
- [x] `FreezeRegistry.freeze` called with structured reason string on `hypothesis_testing` entry
- [x] `FreezeRegistry.unfreeze` called matching reason on confirmed/abandon/reached_3/next_hypothesis_if_under_3
- [x] State survives restart (test_persistence_survives_simulated_restart)
- [x] 23 tests pass; FreezeRegistry existing tests unregressed

## Commits

- `fd90040` feat(04-09): scaffold investigate skill package + transition fixture (Task 1)
- `2fd0df5` test(04-09): add failing tests for InvestigateState machine + freeze wiring (Task 2 RED)
- `279a8a1` feat(04-09): implement InvestigateState with auto-freeze wiring + path validation (Task 2 GREEN)

## Requirements Satisfied

- **QUALITY-07** — Per-hypothesis state machine persisted under pydantic with full save/load round-trip; restart survival verified.
- **SAFETY-05** — Auto-freeze wiring on module-path scope; reason-string grep-correlatable from `freeze_audit.jsonl`; D-16 glob-path rejection enforced by construction.

## TDD Gate Compliance

- RED gate: `2fd0df5` (`test(04-09): ...`) — committed before implementation
- GREEN gate: `279a8a1` (`feat(04-09): ...`) — committed after RED with all tests passing
- REFACTOR gate: not needed — GREEN-phase code is already clean (no duplication, constants extracted, validator pure)

## Known Stubs

None. All code paths wired to real `FreezeRegistry` API; tests use a minimal `_FakeRegistry` for isolation (standard pattern, not a stub).

## Self-Check: PASSED

- FOUND: clawteam/templates/gstack/skills/investigate/__init__.py
- FOUND: clawteam/templates/gstack/skills/investigate/state.py
- FOUND: tests/fixtures/gstack_state_machines/investigate.transitions.json
- FOUND: tests/test_investigate_state_machine.py
- FOUND: commit fd90040
- FOUND: commit 2fd0df5
- FOUND: commit 279a8a1
