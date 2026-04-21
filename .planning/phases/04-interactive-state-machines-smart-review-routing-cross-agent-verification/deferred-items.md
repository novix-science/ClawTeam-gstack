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
