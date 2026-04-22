# Deferred Items — Phase 6

## 9 pre-existing test-ordering failures (out of scope for 06-03)

**Discovered during:** Plan 06-03 full-suite BC run (2026-04-22).

**Symptom:** 9 tests fail when `pytest tests/ --ignore=tests/browser` is
invoked; all 9 pass when run in isolation (e.g. `pytest
tests/test_gstack_plugin.py::test_seven_phases_registered_in_order`).
Failures reproduce WITH OR WITHOUT the Plan 06-03 changes — confirmed
by running the suite on the exact pre-06-03 commit (`98425bb`, baseline
test run 2026-04-22). This is a test-pollution / schema-registry double-
registration issue predating Phase 6.

**Failing tests:**
- tests/test_evidence_schemas_phase5.py::test_schemas_registered_via_plugin_manager
- tests/test_evidence_schemas_phase5.py::test_deploy_notes_roundtrip_via_registry
- tests/test_evidence_schemas_phase5.py::test_canary_report_roundtrip_via_registry
- tests/test_evidence_schemas_phase5.py::test_benchmark_report_roundtrip_via_registry
- tests/test_evidence_schemas_phase5.py::test_codex_review_roundtrip_via_registry
- tests/test_evidence_schemas_phase5.py::test_phase3_keys_still_present
- tests/test_gstack_plugin.py::test_seven_phases_registered_in_order
- tests/test_gstack_plugin.py::test_six_evidence_schemas_registered
- tests/test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present

**Out of scope for Plan 06-03** — this is a test harness / conftest
ordering bug unrelated to memory-search-rank. Logged for a future
housekeeping plan.
