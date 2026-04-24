## Out-of-scope test pollution (observed during 07-02)

These tests fail when the full suite runs in a single process but pass in
isolation. Pre-existing test-module-pollution — unrelated to Plan 07-02
scope (SprintConductor / RateLimitMonitor changes do not touch these
modules).

- tests/templates/gstack/skills/test_browse.py::test_registered_in_plugin
  (function-identity mismatch — `playwright_available` object reloaded)
- tests/test_evidence_schemas_phase5.py — 6 schema-registration tests
- tests/test_gstack_plugin.py::test_seven_phases_registered_in_order
- tests/test_gstack_plugin.py::test_six_evidence_schemas_registered
- tests/test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present

All 10 pass in isolation. Root cause likely a schema-registry fixture that
does not tear down cleanly between test modules. Filed for a future test-
harness hygiene plan.
