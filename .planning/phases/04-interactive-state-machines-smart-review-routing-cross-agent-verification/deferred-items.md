# Phase 4 — Deferred Items (out-of-scope issues observed during plan execution)

Items logged here are out-of-scope for the executing plan per the GSD scope
boundary rule (only auto-fix issues DIRECTLY caused by the current task's
changes). Re-evaluate at Phase 4 close or defer to v1.x.

## 04-06 Observations

### Pre-existing test-ordering flake: test_six_evidence_schemas_registered

- **Test:** `tests/test_gstack_plugin.py::test_six_evidence_schemas_registered`
- **Symptom:** Passes in isolation; fails when run as part of `pytest tests/`
  with `ValueError: Duplicate evidence-schema registration: 'design-doc'`.
- **Scope:** Unrelated to Plan 04-06 changes — triggered by evidence-schema
  module import contamination across test modules (Phase 3 substrate).
- **Observed:** 2026-04-21 during Plan 04-06 post-implementation full-suite
  sanity check. Plan 04-06 test files (`test_gstack_review_router.py`,
  `test_templates.py`) pass in both isolation and full-suite order.
- **Proposed owner:** Plan 04-11 (GstackSprintPlugin integration) or a
  dedicated cleanup in Plan 04-13 (e2e regression). Fix likely needs a
  module-scope fixture that clears `_REGISTERED` between tests, or lazy
  registration inside a function body instead of module import time.

## 04-12 Observations

### ~~Pre-existing failure: test_contribute_review_routers_returns_gstack_router~~ (RESOLVED by 04-11 GREEN)

- **Test:** `tests/test_gstack_plugin.py::test_contribute_review_routers_returns_gstack_router`
- **Symptom:** Fails in isolation with `AssertionError` at test_gstack_plugin.py:305.
- **Scope:** Unrelated to Plan 04-12 changes. Introduced by Plan 04-11's RED
  commit (`41407e4 test(04-11): add failing tests for GstackSprintPlugin Phase 4 hooks`)
  and awaiting GREEN implementation by the Wave 3 sibling executor.
- **Observed:** 2026-04-21 during Plan 04-12 post-implementation broad regression.
  Plan 04-12 test files (`test_sprint_approve_cli.py`) pass 10/10; CLI/gate/state
  regression suites (69 tests) all pass.
- **Proposed owner:** Plan 04-11 (will land the matching GREEN implementation).
- **Resolution:** Plan 04-11 GREEN commit landed 2026-04-21. All 12 new
  Phase 4 plugin tests green in isolation (22/22 in test_gstack_plugin.py;
  71/71 in the plan's scoped verification suite — test_gstack_plugin.py +
  test_cross_agent_verifiers.py + test_gstack_template.py +
  test_orchestrator_phase_registry.py + test_plugins.py +
  test_cross_agent_verification_gate.py).

## 04-11 Observations

### Full-suite ordering flake persists (still out-of-scope; owned by 04-13)

- **Symptom:** `pytest tests/` (full suite, alphabetical collection order)
  still fails at `test_six_evidence_schemas_registered` with the same
  `Duplicate evidence-schema registration: 'design-doc'` error noted in the
  04-06 observation above.
- **Confirmed by bisection:** With Plan 04-11's plugin edits stashed, the
  same failure reproduces at the same assertion. Plan 04-11 introduces no
  new state-leak; the flake is pre-existing and inherited from Phase 3
  plugin substrate.
- **Scope decision (2026-04-21):** Remains out-of-scope per GSD scope
  boundary rule. Plan 04-11 scoped verification suite (71 tests) all green.
  Full-suite cleanup stays with Plan 04-13 (e2e regression) as originally
  proposed in the 04-06 entry above.

## 04-13 Observations

### Parallel-wave RED test from Plan 04-14 visible during 04-13 broad sanity

- **Test:** `tests/test_gstack_role_prompts.py::test_reviewer_review_and_investigate`
- **Symptom:** Asserts `INTERACTIVE-RUNTIME-DEFERRED` is NOT present in the
  reviewer role prompt; still present in the prompt because Plan 04-14's
  GREEN (marker removal) has not landed yet.
- **Scope:** Pre-existing commit from Plan 04-14's own TDD RED cycle
  (`dc474ba test(04-14): add failing D-18 marker removal + inverse runtime tests`),
  observed during 04-13 sanity sweep. Not caused by 04-13 fixtures/tests —
  both 04-13 test files (`test_adversarial_routing.py`,
  `test_state_machine_goldens.py`) pass in isolation and in the
  router+state-machine scoped suite (22/22).
- **Scope decision (2026-04-21):** Out-of-scope — Plan 04-14's own GREEN
  commit will resolve. Plan 04-13 ships green for its own 22 tests.
- **Proposed owner:** Plan 04-14 (will land the marker-removal + runtime-
  stub GREEN).
