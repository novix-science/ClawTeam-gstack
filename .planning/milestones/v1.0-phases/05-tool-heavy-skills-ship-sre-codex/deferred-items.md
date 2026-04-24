# Deferred Items — Phase 5 Discoveries

Pre-existing issues discovered during Phase 5 execution that are out of scope
for the current plan.

## From Plan 05-01 (Wave 0 substrate)

### Cross-test evidence-schema registry contamination

**Tests affected:**
- `tests/test_gstack_plugin.py::test_six_evidence_schemas_registered`
- `tests/test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present`

**Symptom:**
```
ValueError: Duplicate evidence-schema registration: 'design-doc' (existing: DesignDoc, new: type)
```

**Root cause:** `clawteam.harness.evidence_schemas._registry` is a **process-global**
dict. When the full test suite loads both `GstackSprintPlugin` and the helper
`_DummyPluginWithSchema` classes across different test files, the second
`register_schema` call for the same key raises. Running each file in isolation
passes.

**Why deferred:** Pre-existing on commit `ed8c32a` (before Plan 05-01 started).
Plan 05-01 did not touch `evidence_schemas.py` or the affected tests; the
`contribute_skills` hook added here uses a per-call aggregator, not a global
registry, so the pattern avoids this class of contamination.

**Proposed fix (future plan):** either (a) convert `_registry` to a
`collections.ChainMap` keyed by plugin to permit deduplicated multi-registration,
or (b) add an autouse `reset_evidence_registry` fixture so each test starts with
a clean slate. Likely candidate for Phase 5 Wave 4 "harness hygiene" plan.
