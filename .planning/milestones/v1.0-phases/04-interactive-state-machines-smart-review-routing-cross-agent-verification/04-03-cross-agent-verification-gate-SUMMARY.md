---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
plan: 03
subsystem: harness
tags: [phase-gate, pydantic, cross-artifact-verification, plugin-contract, evidence-schema]

# Dependency graph
requires:
  - phase: 02-sprint-phases-evidence-gate
    provides: "EvidenceSchemaRegistry (get_schema/register_schema), parse_frontmatter, MalformedEnvelopeError, PhaseGate ABC"
  - phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
    provides: "Plan 01 substrate audit (no new runtime deps; pydantic + stdlib only)"
provides:
  - "CrossAgentVerificationGate(PhaseGate) — generic gate that runs a plugin-supplied verifier fn across TWO artifacts loaded via EvidenceSchemaRegistry"
  - "VerificationPair(BaseModel) — serializable plugin-contribution model (phase, source_artifact, target_artifact, verifier_dotted_path)"
  - "VerifierFn type alias — (source_model, target_model) -> (ok, reason) callable signature"
affects: [04-05-plugin-verification-hook, 04-11-gstack-plugin-extensions, 04-14-d18-cleanup-thrash-integration-gate-wiring]

# Tech tracking
tech-stack:
  added: []  # zero new runtime deps — pydantic + stdlib only
  patterns:
    - "Gate substrate mirrors EvidenceGate's parse-frontmatter → get_schema → model_validate shape (no YAML parsing re-implementation)"
    - "All failure modes surface as (False, reason) — gate never raises into the gate chain (defense-in-depth, T-04-07 mitigation)"
    - "Plugin contribution is a serializable pydantic model with dotted-path verifier (introspectable via clawteam doctor)"

key-files:
  created:
    - "clawteam/harness/cross_agent_verification_gate.py (162 LOC)"
    - "tests/test_cross_agent_verification_gate.py (201 LOC, 10 tests)"
  modified: []

key-decisions:
  - "VerificationPair stores verifier_dotted_path (str) instead of a Callable field — enables JSON serialization for introspection and keeps plugin manifests inspectable (clawteam doctor can dump the registered pairs without importing the verifier modules)."
  - "Gate is defensive about artifact presence even though EvidenceGate runs first in the chain: missing-artifact returns (False, 'cross-verify missing: <name>') — defense-in-depth so a mis-ordered plugin can't crash the gate chain."
  - "Verifier exceptions are caught with a broad `except Exception` and surfaced as (False, 'cross-verify exception: <Type>: <msg>') — matches EvidenceGate's pattern (T-04-07 disposition: mitigate) and keeps gate-chain execution deterministic."
  - "Test schemas in the test file subclass pydantic BaseModel directly (not ArtifactFrontmatterBase) — the registry's runtime signature only cares about pydantic protocol, so test fixtures stay minimal and don't need the five required fields of the production base."
  - "Added an autouse `reset_schemas` fixture (vs. the plan's original explicit _register_test_schemas pattern) — necessary so tests don't poison the module-level EvidenceSchemaRegistry across runs; mirrors the hermetic-fixture pattern in tests/test_evidence_gate.py."

patterns-established:
  - "CrossAgentVerificationGate failure-mode protocol: 5 documented failure modes, all returning (False, reason) with structured reason strings (operator-debuggable, never raise)"
  - "VerificationPair dotted-path pattern: plugins declare verifiers by dotted path so PluginManager resolves them at plugin-load time (Plan 05 will consume this contract)"

requirements-completed: [SPRINT-04, QUALITY-13]

# Metrics
duration: ~1 min (RED→GREEN, zero refactor commits needed)
completed: 2026-04-21
---

# Phase 04 Plan 03: Cross-Agent Verification Gate Summary

**Generic cross-artifact verification gate (D-10) + `VerificationPair` plugin-contribution pydantic model (D-12) — zero gstack-specific logic, 162 LOC, 10 passing tests, no existing code touched.**

## Performance

- **Duration:** ~1 min (TDD RED at 18:12:02 → GREEN at 18:12:59)
- **Started:** 2026-04-21T18:11:50+08:00
- **Completed:** 2026-04-21T18:13:00+08:00
- **Tasks:** 1 (TDD cycle with 2 commits)
- **Files created:** 2

## Accomplishments

- **CrossAgentVerificationGate** ships as a concrete `PhaseGate` subclass that consumes TWO artifacts from `state.artifacts`, resolves each `artifact_type` via the Phase-2 `EvidenceSchemaRegistry`, feeds validated pydantic models to a plugin-supplied verifier fn, and returns `(ok, reason)` with five documented failure modes — all defensive, never raising.
- **VerificationPair(BaseModel)** defines the serializable plugin-contribution contract (phase / source_artifact / target_artifact / verifier_dotted_path) that Plan 05's `HarnessPlugin.contribute_verification_pairs` hook will return; enforces `min_length=1` on every field so empty plugin contributions fail loudly.
- **VerifierFn typed alias** documents the `(BaseModel, BaseModel) -> (bool, str)` callable signature, giving Plan 11's two concrete gstack verifiers (qa↔engineer test-report, reviewer↔designer design-doc) a shared structural type hint.
- **Zero regressions** — all 59 Phase 2 tests still pass (`tests/test_evidence_gate.py`, `tests/test_evidence_schemas.py`); the new module is additive.

## Task Commits

Each task was committed atomically per the TDD gate sequence:

1. **Task 1 RED — failing tests** — `d8a2ef9` (`test(04-03): add failing tests for CrossAgentVerificationGate`)
2. **Task 1 GREEN — implementation** — `39cccf4` (`feat(04-03): implement CrossAgentVerificationGate + VerificationPair`)

**Plan metadata:** (next commit — `docs(04-03): complete cross-agent-verification-gate plan`)

_Note: No refactor commit needed; the GREEN implementation was already clean._

## Files Created/Modified

- **`clawteam/harness/cross_agent_verification_gate.py`** (162 LOC) — new module. Contains `VerifierFn` type alias, `CrossAgentVerificationGate(PhaseGate)` with documented 5-failure-mode contract, and `VerificationPair(BaseModel)` with 4 required fields (`min_length=1`).
- **`tests/test_cross_agent_verification_gate.py`** (201 LOC) — 10 unit tests: verifier-ok, verifier-fail-with-reason, missing-source, missing-target, unregistered-schema, malformed-frontmatter, verifier-exception, verifier-receives-pydantic-models, VerificationPair round-trip, VerificationPair empty-field rejection. Uses an autouse fixture to reset the module-level `EvidenceSchemaRegistry` between tests.

## Decisions Made

1. **VerificationPair uses dotted-path strings for verifiers, not Callable fields** — keeps the plugin contract serializable for introspection (`clawteam doctor` can dump registered pairs without importing verifier modules).
2. **Gate is defensive about artifact presence** — `check()` re-verifies both artifacts are in `state.artifacts` before parsing, even though `EvidenceGate` should have caught a missing artifact earlier in the gate chain. This is defense-in-depth per §04-CONTEXT D-10; a mis-ordered plugin that drops `EvidenceGate` won't crash `CrossAgentVerificationGate`.
3. **All verifier exceptions are caught** (broad `except Exception`) and surfaced as structured `(False, reason)` strings including the exception type name — this is the T-04-07 mitigation from the plan's threat model and mirrors `EvidenceGate`'s pattern (accepted T-02-18).
4. **Test fixtures subclass `BaseModel` directly, not `ArtifactFrontmatterBase`** — the production registry's runtime behaviour only cares about pydantic protocol compliance, so the test file stays minimal and self-contained (no need to set the five required `persona/step_label/done/artifact_type/created_at` fields for every test).

## Deviations from Plan

**Minor — test file hardening (Rule 2: missing-critical functionality).**

The plan's original test file called `_register_test_schemas()` inside each test without resetting the module-level `EvidenceSchemaRegistry`. Because `register_schema("fake-a", ...)` raises `ValueError` on duplicate registration (see `clawteam/harness/evidence_schemas.py:78-82`), running the full test file would fail on test 2 with `"Duplicate evidence-schema registration: 'fake-a'"`.

- **Found during:** Task 1 RED (reading `register_schema` source)
- **Issue:** Tests would pass in isolation (pytest -k) but fail when the file ran as a unit.
- **Fix:** Added an autouse `_reset_schemas` pytest fixture that calls `reset_registry()` around every test. Mirrors the `hermetic` fixture pattern in `tests/test_evidence_gate.py:49-55`.
- **Files modified:** `tests/test_cross_agent_verification_gate.py` (fixture added to the Plan-specified scaffold)
- **Verification:** All 10 tests pass (`uv run pytest tests/test_cross_agent_verification_gate.py -x -q` → `10 passed in 0.12s`); tests stay green when reordered or re-run.
- **Committed in:** `d8a2ef9` (RED test commit — the fix landed in the initial test file rather than as a separate commit because RED should run-as-a-unit).

---

**Total deviations:** 1 (Rule 2 — test-isolation correctness).
**Impact on plan:** Zero scope creep. The fix is a test-file hardening that the plan's example code omitted; the production module `clawteam/harness/cross_agent_verification_gate.py` matches the plan byte-for-byte in structure and failure-mode semantics.

## Issues Encountered

- `pytest` was not installed in the repo's `.venv/` — resolved by running via `uv run pytest` (the project uses `uv` for test execution; `pyproject.toml` declares pytest under `[project.optional-dependencies].dev`). No code change required.

## TDD Gate Compliance

- **RED gate:** `d8a2ef9` — `test(04-03): add failing tests for CrossAgentVerificationGate` (verified `ModuleNotFoundError` before implementation landed).
- **GREEN gate:** `39cccf4` — `feat(04-03): implement CrossAgentVerificationGate + VerificationPair` (10/10 tests green immediately).
- **REFACTOR gate:** Skipped — GREEN implementation was already clean (no duplication, clear names, docstrings complete). Documented here per TDD discipline.

## Verification Evidence

Running the plan's acceptance criteria end-to-end:

| Check | Command | Result |
|-------|---------|--------|
| Module imports cleanly | `python -c "from clawteam.harness.cross_agent_verification_gate import CrossAgentVerificationGate, VerificationPair, VerifierFn"` | Exit 0 |
| Class count | `grep -c "^class " clawteam/harness/cross_agent_verification_gate.py` | 2 |
| CrossAgentVerificationGate subclass | `grep -q "class CrossAgentVerificationGate(PhaseGate)"` | Match |
| VerificationPair subclass | `grep -q "class VerificationPair(BaseModel)"` | Match |
| VerifierFn alias | `grep -q "VerifierFn = Callable"` | Match |
| LOC ≥ 60 | `wc -l clawteam/harness/cross_agent_verification_gate.py` | 162 |
| New tests pass | `uv run pytest tests/test_cross_agent_verification_gate.py -x -q` | 10 passed |
| Phase 2 regression | `uv run pytest tests/test_evidence_gate.py tests/test_evidence_schemas.py -x -q` | 59 passed |
| No existing test files modified | `git status` before commit | only new files |

## Integration Smoke — Plan 05 / Plan 11 insertion points

**Plan 05 (`04-05-plugin-verification-hook`)** will extend `HarnessPlugin` with:

```python
def contribute_verification_pairs(self) -> list[VerificationPair]:
    return []  # default no-op
```

and extend `PluginManager._instantiate_and_register` to:
1. Collect `VerificationPair` instances from every plugin.
2. Resolve each `verifier_dotted_path` via `importlib.import_module` + `getattr` at plugin-load time.
3. Construct one `CrossAgentVerificationGate(phase=..., source_artifact=..., target_artifact=..., verifier=<resolved fn>)` per pair.
4. Attach the gate to the phase named by `pair.phase` in the phase registry, AFTER the `EvidenceGate` for that phase (§04-RESEARCH A6).

**Plan 11 (`04-11-gstack-plugin-extensions`)** will ship two verifiers and return them as `VerificationPair` instances from `GstackSprintPlugin.contribute_verification_pairs`:

| Verifier | Source artifact | Target artifact | Phase |
|----------|-----------------|-----------------|-------|
| `verify_test_report_matches_engineer_output` | `test-report.md` (qa) | `build-report.md` or `diff.md` (engineer) | `test` |
| `verify_review_matches_design_questions` | `review-report.md` (reviewer) | `design-doc.md` (designer) | `review` |

Both verifiers receive pydantic instances (the gate calls `schema_cls.model_validate(meta)` before dispatch), so Plan 11's verifier bodies stay strongly typed without re-parsing YAML.

## Next Phase Readiness

- ✅ Downstream **Plan 05** can `from clawteam.harness.cross_agent_verification_gate import VerificationPair` without circular-import risk (the module depends only on `phases.PhaseGate`, `evidence_schemas.get_schema`, and `team.envelope.parse_frontmatter` — all stable Phase 1/2 substrate).
- ✅ Downstream **Plan 11** can construct `CrossAgentVerificationGate` instances with gstack verifier fns and attach them to the test/review phases.
- ⚠️ Plan 05 must resolve `verifier_dotted_path` eagerly (at plugin load) so unresolvable verifiers fail fast; suggested `ImportError` → `MalformedEnvelopeError`-style operator-facing message.
- 🟢 No blockers for Wave 1 parallel plans (04-02, 04-04, 04-06) — this plan only adds new files.

## Self-Check: PASSED

- `clawteam/harness/cross_agent_verification_gate.py` exists (162 LOC)
- `tests/test_cross_agent_verification_gate.py` exists (201 LOC, 10 tests)
- Commit `d8a2ef9` present in `git log` (RED test commit)
- Commit `39cccf4` present in `git log` (GREEN feat commit)
- 10/10 new tests pass
- 59/59 Phase 2 regression tests pass
- No existing code touched (only additive new files in commit set)

---
*Phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification*
*Plan: 03-cross-agent-verification-gate*
*Completed: 2026-04-21*
