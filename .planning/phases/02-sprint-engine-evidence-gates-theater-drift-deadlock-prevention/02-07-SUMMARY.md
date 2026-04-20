---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 07
subsystem: clawteam.harness
tags: [evidence-gate, four-check-protocol, test-verify-cache, deploy-url-head, phase-2, tdd]
requirements: [SPRINT-02, QUALITY-08, QUALITY-03]
dependency_graph:
  requires:
    - "clawteam.harness.phases::ArtifactRequiredGate (base class)"
    - "clawteam.harness.evidence_schemas::get_schema (Plan 02-04)"
    - "clawteam.team.envelope::parse_frontmatter + MalformedEnvelopeError (Plan 02-02)"
    - "clawteam.fileutil::atomic_write_text + file_locked"
    - "clawteam.sprint.state::SprintState.phase_artifact_cap_bytes (Plan 02-03)"
    - "clawteam.team.models::get_data_dir"
  provides:
    - "clawteam.harness.evidence_gate::EvidenceGate (4-check protocol gate)"
    - "clawteam.harness.evidence_gate::detect_stub (3-layer stub detector)"
    - "clawteam.harness.evidence_gate::_default_head_check (stdlib HTTP HEAD)"
    - "clawteam.harness.evidence_gate::_default_subprocess_runner (shell=False)"
    - "test_verify_cache.json persistence protocol (sprint-scoped)"
  affects:
    - "Phase 3 GstackSprintPlugin: binds EvidenceGate to 7 phases + registers 6 artifact schemas + required_sections map"
    - "Phase 5 /ship: must wrap _default_head_check in an allowlist checker to mitigate residual T-02-01 SSRF"
    - "Plan 02-11 SprintConductor: writes compaction-question file on D-28 overflow"
tech_stack:
  added: []  # zero new required runtime deps (stdlib only)
  patterns:
    - "4-check protocol: presence → frontmatter+schema → stub → post-check dispatch"
    - "Injection seam: subprocess_runner + deploy_url_checker constructor params for test isolation + future allowlist wrapping"
    - "Content-hash cache: SHA256(artifact body) keyed under name:test_command; hit skips rerun when last_exit_code == 0"
key_files:
  created:
    - "clawteam/harness/evidence_gate.py (311 LOC)"
    - "tests/test_evidence_gate.py (380 LOC, 13 tests)"
  modified: []
decisions:
  - "Blacklist scan runs before section-floor scan in detect_stub — blacklist yields an actionable line number even when a section also fails; failing-fast with the more specific reason surfaces the higher-signal issue first"
  - "Cache key is 'name:test_command' rather than artifact_hash — artifact_hash is stored as entry.artifact_hash so edits to the test_command itself invalidate the cache independently of body changes"
  - "Test-fixture schema class renamed TestReportFixture → ReportTestFixture to avoid pytest auto-collecting it as a test class (had a constructor warning)"
  - "YAML frontmatter in tests quotes created_at string values — YAML 1.1 auto-parses bare ISO-8601 tokens as datetime objects, which would then fail pydantic's str validation downstream"
metrics:
  duration_minutes: 6
  completed: "2026-04-20"
  tests_added: 13
  loc_added: 691
---

# Phase 2 Plan 07: EvidenceGate 4-check protocol Summary

**One-liner:** EvidenceGate subclass of ArtifactRequiredGate running presence →
frontmatter+schema → stub detection → (test-report subprocess rerun with content-hash
cache) / (ship-notes deploy_url HEAD probe) / per-phase cap; 13 tests green.

## What Shipped

### `clawteam/harness/evidence_gate.py` (311 LOC, new)

- `class EvidenceGate(ArtifactRequiredGate)` — the gate class. Constructor
  accepts `artifact_names` (base class) plus three keyword-only params:
  `required_sections: dict[str, list[str]] | None`,
  `deploy_url_checker: Callable[[str, int], tuple[int, dict]] | None`,
  `subprocess_runner: Callable[..., subprocess.CompletedProcess] | None`.
  Defaults plug in stdlib implementations (see below).
- `check(state)` (lines 163–199) runs the 4-check protocol per artifact in
  `artifact_names`; short-circuits on first failure with a structured reason
  string. After the per-artifact loop, a per-phase cap check uses
  `state.phase_artifact_cap_bytes` (falsy → skipped).
- `_post_check` (lines 203–211) dispatches per `artifact_type`:
  `test-report` → `_run_test_command`; `ship-notes` → `_check_deploy_url`;
  other types no-op → `(True, "")`.
- `_run_test_command` (lines 215–261): splits `meta["test_command"]` into a
  list, runs via injected runner with `cwd=state.workspace_branch or "."`
  and `timeout=TEST_COMMAND_TIMEOUT_SECONDS (300)`; `TimeoutExpired` →
  `(False, "test_command timed out after 300s")`; non-zero exit → stderr
  tail + exit code in reason. Every run persists to `test_verify_cache.json`.
- `_check_deploy_url` (lines 291–301): HEAD via injected checker with 10 s
  timeout. Any exception → `"deploy_url unreachable: <msg>"`. Non-2xx/3xx →
  `"deploy_url returned HTTP <status>"`.
- `detect_stub(body, required_sections)` (lines 105–135): blacklist-first
  (yields line number), then section-body floor of 100 bytes. Returns
  `None` on pass.
- `_default_head_check` (lines 69–82): `urllib.request.Request(url, method="HEAD")`
  + `urlopen(timeout=10)`. Returns `(status, headers_dict)`. Marked
  `# noqa: S310` — T-02-01 residual SSRF deliberately deferred to Phase 5.
- `_default_subprocess_runner` (lines 85–102): `subprocess.run(shell=False,
  timeout=..., capture_output=True, text=True)`. `# noqa: S603` documents
  the T-02-03 mitigation contract.

### `tests/test_evidence_gate.py` (380 LOC, 13 tests)

Coverage map (all tests green at GREEN commit `5e60816`):

| Test | Layer | What it proves |
|------|-------|----------------|
| `test_presence_check_preserved` | 1 | Inherited `ArtifactRequiredGate` shape is preserved: `(False, "Missing artifacts: <name>")` |
| `test_layer1_frontmatter_required_fields` | 2 | Missing `persona` → pydantic error surfaces with "persona" in reason |
| `test_unregistered_artifact_type_error` | 2 | Pitfall #6: unregistered `artifact_type` returns "Phase 3 plugin must register" |
| `test_layer2_stub_section_detected` | 3 | Required `## Purpose` section ≤ 100 bytes → stub reason names the section |
| `test_layer3_blacklist_hit_tbd` | 3 | `TBD` in body → fail with line number |
| `test_layer3_blacklist_hit_todo_placeholder_lorem` | 3 | TODO / placeholder / Lorem ipsum all trip blacklist |
| `test_test_report_reruns_test_command` | 4 | Runner called once with cwd=workspace_branch, timeout=300, cmd as list |
| `test_test_report_cache_hit_skips_rerun` | 4 | Second identical artifact hits cache (runner call count = 1); `test_verify_cache.json` on disk |
| `test_test_report_exit_1_fails_gate` | 4 | Exit=1 + stderr tail surface in reason |
| `test_test_report_timeout_fails_gate` | 4 | `TimeoutExpired` → "timed out after 300s" |
| `test_ship_notes_deploy_url_2xx_passes` | 4 | 200 response → gate passes |
| `test_ship_notes_deploy_url_non2xx_fails` | 4 | 404 → "deploy_url returned HTTP 404" |
| `test_ship_notes_deploy_url_default_checker_offline_safety` | 4 | Pitfall #10: URLError → "unreachable: connection refused" |

## Verification Evidence

### Primary test suite (Task 2 acceptance_criteria)

```
$ python -m pytest tests/test_evidence_gate.py tests/test_evidence_schemas.py \
  tests/test_turn_envelope.py tests/test_template_regression_matrix.py \
  tests/test_harness.py tests/test_artifact_caps.py -q
................................................................. (and more)
87 passed in 2.18s
```

- 13 / 13 in `test_evidence_gate.py` green.
- 12 / 12 in `test_template_regression_matrix.py` green (SC#10: EvidenceGate
  is opt-in; existing templates keep using `ArtifactRequiredGate`).
- `test_evidence_schemas.py`, `test_turn_envelope.py`, `test_harness.py`,
  `test_artifact_caps.py` all green — integration-neighbor contracts intact.

### Structural greps (Task 2 acceptance_criteria — all pass)

| Grep | Required | Actual |
|------|----------|--------|
| `class EvidenceGate(ArtifactRequiredGate):` | == 1 | 1 |
| `def detect_stub / _run_test_command / _check_deploy_url / _load_.. / _save_.. / _post_check` | == 6 | 6 |
| `shell=False` | ≥ 1 | 5 (T-02-03) |
| `timeout=300` / `TEST_COMMAND_TIMEOUT_SECONDS` | ≥ 2 | 3 |
| `method="HEAD"` | ≥ 1 | 1 (D-05) |
| `DEPLOY_URL_HEAD_TIMEOUT_SECONDS` / `timeout=10` | ≥ 1 | 3 |
| blacklist markers (TBD / TODO / xxx / placeholder / Lorem ipsum) | ≥ 5 | 6 |
| `deploy_url_checker` / `subprocess_runner` | ≥ 2 | 8 |

### Ruff

`ruff check clawteam/harness/evidence_gate.py tests/test_evidence_gate.py` —
all checks passed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Fixture-class name collided with pytest auto-collection**

- **Found during:** Task 2 GREEN test run.
- **Issue:** `class TestReportFixture(ArtifactFrontmatterBase)` triggered a
  pytest collection warning ("cannot collect test class 'TestReportFixture'
  because it has a __init__ constructor") because pytest auto-discovers
  `Test*` classes even when they are test-local fixtures.
- **Fix:** Renamed to `ReportTestFixture` (same semantic, not auto-collected).
- **Files modified:** `tests/test_evidence_gate.py`
- **Commit:** `5e60816` (bundled into GREEN)

**2. [Rule 1 — Bug] YAML 1.1 parsed bare ISO-8601 `created_at` as datetime, breaking pydantic `str` validation**

- **Found during:** Task 2 GREEN test run (`test_layer2_stub_section_detected`
  failed with a pydantic error "Input should be a valid string … input_type=datetime").
- **Issue:** The test frontmatter emitted `created_at: 2026-04-17T00:00:00Z`
  unquoted. YAML 1.1 (pyyaml default `safe_load`) auto-parses that as a
  `datetime` object, which then fails `ArtifactFrontmatterBase.created_at: str`
  validation — and the gate reports a schema error before ever reaching the
  Layer 3 stub-section assertion the test was trying to verify.
- **Fix:** Quoted `created_at: "2026-04-17T00:00:00Z"` in all 6 frontmatter
  blocks in the test file so the YAML parser keeps the value as a string.
  The production concern is documented — agents writing artifacts must
  quote ISO-8601 timestamps; Phase 3's `GstackSprintPlugin` artifact
  templates will need the same quoting discipline.
- **Files modified:** `tests/test_evidence_gate.py`
- **Commit:** `5e60816` (bundled into GREEN)
- **Forward note for Phase 3:** Consider either (a) teaching
  `ArtifactFrontmatterBase.created_at` to accept `datetime` and coerce, or
  (b) documenting the quote-required convention in the artifact-template
  generators so agents don't accidentally produce un-quoted timestamps.

No other deviations.

## Injection Seams — Forward Contracts

### `deploy_url_checker` — Phase 5 `/ship` allowlist wiring (T-02-01)

The `deploy_url_checker` constructor parameter is a typed `Callable` seam.
Phase 5's `/ship` skill MUST wrap `_default_head_check` in an allowlist
checker before constructing an `EvidenceGate`:

```python
def allowlist_checker(url: str, timeout: int) -> tuple[int, dict]:
    host = urlparse(url).hostname or ""
    if host not in user_approved_hosts:
        raise ValueError(f"deploy_url host {host!r} not in allowlist")
    return _default_head_check(url, timeout)

gate = EvidenceGate(["ship-notes.md"], deploy_url_checker=allowlist_checker)
```

Removing the seam or routing `_check_deploy_url` directly to the stdlib
probe would silently regress the T-02-01 mitigation. This is called out in
the module docstring (lines 25–32) so future refactors cannot quietly
drop the injection point.

### `subprocess_runner` — test isolation (T-02-03 verification)

Same contract shape. Tests inject a fake to avoid real command execution;
the default `_default_subprocess_runner` is the production runner. The
T-02-03 mitigation (shell=False + timeout + explicit cwd) lives entirely
inside `_default_subprocess_runner`; injected fakes in tests verify the
gate passes a list cmd + workspace cwd + 300 s timeout to the seam.

## `test_verify_cache.json` Schema (for Plan 02-11 recovery)

Path: `$CLAWTEAM_DATA_DIR/teams/<team>/sprints/<sprint_id>/test_verify_cache.json`

```jsonc
{
  "test-report.md:pytest tests/foo.py -x": {
    "artifact_hash": "<sha256 of artifact body>",
    "test_command": "pytest tests/foo.py -x",
    "last_run_at": "2026-04-20T10:32:18.123456+00:00",
    "last_exit_code": 0
  }
}
```

- **Key shape:** `"<artifact_name>:<test_command>"` — editing the command
  invalidates the entry even if the artifact body is byte-identical.
- **Cache-hit condition:** entry exists AND `artifact_hash` matches current
  artifact body SHA256 AND `last_exit_code == 0`. Any mismatch triggers
  a rerun (plan 02-11 Conductor pause/resume: cache survives pauses;
  resume re-runs only if artifacts changed during the pause).
- **Concurrency:** read + write both acquire `file_locked` before reading /
  writing; `atomic_write_text` ensures no torn writes.

## Residual Security Posture

- **T-02-01 (SSRF via `deploy_url`) remains HIGH** until Phase 5 ships the
  allowlist wrapper. The module docstring and `noqa: S310` comments make
  this explicit so future refactors don't silently drop the seam. Phase 5
  scope MUST include the allowlist wrapper; this is the ONLY path to
  mitigate the residual risk.
- **T-02-03 (test_command arbitrary shell exec)** mitigated inline:
  `shell=False` + `cmd_str.split()` (not `shlex.split`) + 300 s timeout +
  cwd pinned to `state.workspace_branch`.
- **T-02-18 / T-02-19 / T-02-20 accepted** per plan threat_model; no
  code-level mitigation in Phase 2.

## Forward Contract for Phase 3 `GstackSprintPlugin`

To bind `EvidenceGate` to the seven gstack phases, the plugin must:

1. `contribute_evidence_schemas()` — register pydantic subclasses for
   the six gstack artifact types (`design-doc`, `plan-doc`, `test-report`,
   `review-report`, `ship-notes`, `retro`).
2. `contribute_gates()` — for each phase, construct an `EvidenceGate` with:
   - `artifact_names=[<phase's artifact filename>]`
   - `required_sections={<artifact>: [<## section names>]}`
   - Leave `deploy_url_checker` + `subprocess_runner` at defaults (Phase 5
     wraps the first; tests override the second).
3. Confirm the existing templates' `ArtifactRequiredGate` registrations
   remain unchanged (Pitfall #8 BC invariant — verified by
   `test_template_regression_matrix.py`).

## Self-Check: PASSED

- [x] `clawteam/harness/evidence_gate.py` exists (311 LOC).
- [x] `tests/test_evidence_gate.py` exists (380 LOC, 13 tests).
- [x] Commit `db015e9` present on branch (RED).
- [x] Commit `5e60816` present on branch (GREEN).
- [x] All 13 evidence-gate tests pass.
- [x] Template regression matrix (SC#10) 12 / 12 pass.
- [x] Ruff clean.
- [x] Structural greps all satisfy acceptance criteria.

## TDD Gate Compliance

- **RED:** `db015e9` — `test(02-07): add failing tests for EvidenceGate …`
- **GREEN:** `5e60816` — `feat(02-07): EvidenceGate 4-check protocol + …`
- No REFACTOR commit — implementation passed acceptance on first GREEN run
  aside from the two test-setup bugs documented under Deviations, and those
  live in the test file, not the production code.
