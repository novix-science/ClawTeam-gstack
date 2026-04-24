---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
plan: 02
subsystem: sprint-envelope
tags: [turn-envelope, team-message, pydantic, yaml-frontmatter, phase-2, stdlib-parser, pyyaml, bc-invariant]

# Dependency graph
requires:
  - phase: 01-core-harness-extensions
    provides: TeamMessage pydantic v2 model (15 optional fields + populate_by_name=True)
  - phase: 01-core-harness-extensions
    provides: clawteam/sprint/qa.py narrow-stdlib frontmatter parser (D-08) — reference implementation pattern
provides:
  - TurnEnvelope pydantic v2 model (3 required + 3 optional fields)
  - parse_frontmatter(raw) -> tuple[dict, str] stdlib+yaml.safe_load helper
  - validate_envelope(meta) -> TurnEnvelope with field-path-prefixed MalformedEnvelopeError
  - MalformedEnvelopeError (ValueError subclass for MCP translate_error auto-wrap)
  - TeamMessage extended with three OPTIONAL envelope fields (persona / step_label / done)
affects: [02-07-evidence-gate, 02-08-transport-deliver, 03-gstack-sprint-plugin]

# Tech tracking
tech-stack:
  added:
    - pyyaml>=6.0,<7.0 (dev optional dependency — NOT required runtime)
  patterns:
    - "One pydantic model, two serialization surfaces (TeamMessage envelope fields + artifact YAML frontmatter both validate through TurnEnvelope)"
    - "MalformedEnvelopeError subclasses ValueError so MCP translate_error auto-wraps (mirrors MCPToolError pattern in clawteam/mcp/helpers.py)"
    - "parse_frontmatter returns ({}, raw) on missing fence — Pitfall #8 BC invariant: artifacts without frontmatter pass through unmodified"
    - "yaml.safe_load only — T-02-04 YAML-injection mitigation (grep enforces yaml.unsafe_load/yaml.load( count == 0)"
    - "FRONTMATTER_RE anchored with \\A..\\Z + DOTALL — partial match never succeeds, multi-line bodies flow"

key-files:
  created:
    - clawteam/team/envelope.py
    - tests/test_turn_envelope.py
  modified:
    - clawteam/team/models.py
    - pyproject.toml

key-decisions:
  - "TurnEnvelope required fields (persona, step_label, done) vs TeamMessage optional mirror — enforcement scope deferred to Transport.deliver() (Plan 02-08) so 15+ existing TeamMessage construction sites keep working (Pitfall #8 BC invariant)"
  - "PyYAML placed in [project.optional-dependencies].dev instead of runtime [dependencies] — preserves PROJECT.md 'no new required runtime deps for core harness extensions' while unblocking envelope test execution"
  - "FRONTMATTER_RE uses \\A..\\Z + DOTALL anchors (not alternative stdlib line-scanning) so multi-line YAML bodies remain available for future Phase 3 schemas with nested lists"
  - "validate_envelope re-raises ValidationError as MalformedEnvelopeError with 'envelope invalid: <field.path>: <msg>' so Plans 02-07/02-08 can surface the specific field in gate-reason / MCP error strings (T-02-10 mitigation — uses pydantic's exc.errors()[0]['msg'], never the raw malformed value)"

patterns-established:
  - "Shared-contract module pattern: one pydantic model validates both a TeamMessage surface (Transport.deliver extracts fields) and a markdown-frontmatter surface (EvidenceGate calls parse_frontmatter first, then validate_envelope)"
  - "Error-hierarchy pattern: domain error subclasses ValueError so clawteam.mcp.helpers.translate_error auto-wraps to MCPToolError without new hierarchy branches"
  - "BC-preserving mirror fields pattern: when new required fields must exist on an enforcement boundary but shared model already has many callsites, add them as optional with None defaults on the shared model and enforce at the boundary (here: Transport.deliver, Plan 02-08)"

requirements-completed: [SKILL-09, QUALITY-01]

# Metrics
duration: 4min
completed: 2026-04-20
---

# Phase 02 Plan 02: Turn Envelope + Stdlib YAML Frontmatter Parser Summary

**TurnEnvelope pydantic v2 model + stdlib yaml.safe_load frontmatter parser + three optional envelope fields on TeamMessage — shared validation contract for Plan 02-07 (EvidenceGate) and Plan 02-08 (Transport.deliver).**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-20T09:56:18Z
- **Completed:** 2026-04-20T10:00:08Z
- **Tasks:** 2 (RED + GREEN — TDD flow)
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- Shipped `clawteam/team/envelope.py` (95 LOC) — the shared pydantic contract Plans 02-07 and 02-08 both validate through ("one pydantic model, two serialization surfaces").
- `TurnEnvelope` pydantic v2 model with exactly the fields §02-CONTEXT D-06/D-07 specifies: `persona` (required, min_length=1), `step_label` (required, min_length=1), `done` (required bool) + `artifact_type` / `created_at` / `turn_id` (optional).
- `parse_frontmatter(raw)` stdlib-only helper using `re.compile(r"\\A---\\s*\\n(.*?)\\n---\\s*\\n(.*)\\Z", re.DOTALL)` + `yaml.safe_load` — returns `({}, raw)` on missing fence (Pitfall #8 BC invariant), raises `MalformedEnvelopeError` on invalid YAML or non-mapping top level.
- `validate_envelope(meta)` re-raises pydantic `ValidationError` as `MalformedEnvelopeError` with field-path prefix (`"envelope invalid: persona: value error, String should have at least 1 character"` etc.).
- `MalformedEnvelopeError` subclasses `ValueError` — `clawteam.mcp.helpers.translate_error` auto-wraps to `MCPToolError` without touching hierarchy.
- `TeamMessage` gains three OPTIONAL envelope fields (`persona: str | None`, `step_label: str | None = Field(default=None, alias="stepLabel")`, `done: bool | None`) — all 15+ existing TeamMessage construction sites keep working.
- Tests: **12/12 new envelope tests pass**; **89/89 regression tests pass** (models, mailbox, waiter, runtime_routing, template_regression_matrix — SC#10 Phase 0 regression matrix still green, BC invariant held).

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — test_turn_envelope.py + TeamMessage-BC construction assertions** — `5697b58` (test)
2. **Task 2: GREEN — implement clawteam/team/envelope.py + extend TeamMessage with optional envelope fields** — `ed89289` (feat)

_TDD flow confirmed: test commit precedes feat commit; RED collection failed with ModuleNotFoundError before the feat commit shipped the module._

## Files Created/Modified

- **`clawteam/team/envelope.py`** (new, 95 LOC) — TurnEnvelope, parse_frontmatter, validate_envelope, MalformedEnvelopeError; the shared pydantic contract for Plans 02-07 and 02-08.
- **`tests/test_turn_envelope.py`** (new, 12 tests) — Covers TurnEnvelope required/optional fields, parse_frontmatter round-trip + no-fence BC + malformed-YAML rejection, validate_envelope field-path error shaping, and TeamMessage BC construction (with and without envelope fields).
- **`clawteam/team/models.py`** (modified) — Added `persona: str | None`, `step_label: str | None = Field(default=None, alias="stepLabel")`, `done: bool | None` at end of TeamMessage class body. Critical BC: all three have `None` defaults so existing construction sites do not raise.
- **`pyproject.toml`** (modified) — Added `pyyaml>=6.0,<7.0` to `[project.optional-dependencies].dev` (deviation, see below).

## Exact Signatures (forward contract for Plans 02-07 / 02-08)

```python
# clawteam/team/envelope.py

class MalformedEnvelopeError(ValueError):
    ...

class TurnEnvelope(BaseModel):
    persona: str = Field(..., min_length=1, description="Agent role asserting this turn")
    step_label: str = Field(..., min_length=1, description="Free-form step marker")
    done: bool = Field(..., description="Turn-done signal")
    artifact_type: str | None = None
    created_at: str | None = None
    turn_id: str | None = None

def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    ...  # returns ({}, raw) on missing fence; raises MalformedEnvelopeError on invalid YAML / non-mapping

def validate_envelope(meta: dict[str, Any]) -> TurnEnvelope:
    ...  # raises MalformedEnvelopeError("envelope invalid: <field.path>: <first-msg>")
```

```python
# clawteam/team/models.py (TeamMessage additions — all OPTIONAL with None defaults)

class TeamMessage(BaseModel):
    # ... existing 15 fields ...
    persona: str | None = None
    step_label: str | None = Field(default=None, alias="stepLabel")
    done: bool | None = None
```

## Decisions Made

- **Kept `import yaml` + `yaml.safe_load` (plan's preferred option) rather than a stdlib narrow parser.** Reason: Phase 3 schemas may use nested lists; the regex-anchored + `yaml.safe_load` path keeps the door open without another parser swap, while T-02-04 acceptance grep (`yaml.unsafe_load\|yaml.load(` count == 0) enforces the injection-safety invariant.
- **PyYAML placed in `[project.optional-dependencies].dev` not runtime `dependencies`.** Reason: PROJECT.md constraint "no new required runtime deps for core harness extensions". Production deployments that never import `clawteam.team.envelope` stay unaffected; tests and sprint-scope callsites (Plans 02-07/02-08, Phase 3 GstackSprintPlugin) install dev deps.
- **TeamMessage's three new fields are optional on the shared model; enforcement is scoped to `Transport.deliver()` (Plan 02-08).** Reason: 15+ existing construction sites in `team/mailbox.py`, `tests/*`, `harness/*` would all break if the fields were required on the shared model (Pitfall #8 / SC#10 Phase 0 regression matrix). The envelope invariant is asserted at the deliver boundary where the sprint-scope check lives.
- **`validate_envelope` error message format: `"envelope invalid: <field.path>: <first-msg>"`**. Reason: Plans 02-07 (gate-reason) and 02-08 (MCP error surface) both need to surface the specific invalid field to the agent; joining `exc.errors()[0]['loc']` with `.` gives the dotted path without leaking the raw malformed value (T-02-10 info-disclosure mitigation — pydantic guarantees `msg` is human-readable, not the raw value).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] PyYAML not installed in `.venv` site-packages**
- **Found during:** Task 2 (GREEN) — initial pytest run failed at collect time with `ModuleNotFoundError: No module named 'yaml'`.
- **Issue:** The plan's `<read_first>` note assumed PyYAML was "a transitive dep via questionary → prompt_toolkit chain" and advised `pip show PyYAML` to verify. The system Python did have PyYAML 6.0.3 installed, but the project's `.venv` (which pytest actually uses) did not. PyYAML is also not declared in `pyproject.toml` runtime deps.
- **Fix:** Added `"pyyaml>=6.0,<7.0"` to `[project.optional-dependencies].dev` in `pyproject.toml` (matches the plan's documented fallback option), then installed into the venv via `uv pip install --python /home/jac/repos/ClawTeam-gstack/.venv/bin/python "pyyaml>=6.0,<7.0"` (pyyaml 6.0.3).
- **Files modified:** `pyproject.toml`
- **Verification:** `/home/jac/repos/ClawTeam-gstack/.venv/bin/python -m pytest tests/test_turn_envelope.py -v` → 12/12 pass. `clawteam/team/envelope.py` still imports `yaml` at module top (plan's preferred shape); all `yaml.safe_load` / acceptance-grep criteria hold.
- **Committed in:** `ed89289` (Task 2 commit — bundled with feat since the dep-decl + envelope.py together are the atomic "env + module" change).

**2. [Rule 1 — Formatting] Ruff auto-reordered imports in `tests/test_turn_envelope.py`**
- **Found during:** Task 1 (RED) — `ruff check --fix` moved `from clawteam.team.envelope import (…)` to group before `from pydantic import …` per I-rule (isort-compatible).
- **Issue:** Not a bug — style normalization. Tests still import all 5 names and assert identically.
- **Fix:** Accepted ruff's re-ordering; did not revert.
- **Files modified:** `tests/test_turn_envelope.py`
- **Verification:** `ruff check` clean; all 12 tests pass.
- **Committed in:** `5697b58` (Task 1 commit — included the ruff-fixed shape).

---

**Total deviations:** 2 auto-fixed (1 blocking / dep declaration, 1 formatting).
**Impact on plan:** Both deviations were anticipated by the plan (§Task 2 `<action>` note on PyYAML fallback, §Task 1 `<action>` ruff-fix instruction). No scope creep; no architectural change.

## Issues Encountered

- **Worktree base commit mismatch** at startup: worktree was based on `bc69bc0` (an older commit from before this phase was fully staged); the required base was `782ab28`. Resolved via the mandatory `git reset --hard 782ab28...` step in the `<worktree_branch_check>` block; no data loss (worktree had only the stale branch-creation state from an earlier agent spawn).

## Threat Surface Compliance

All Plan 02-02 `<threat_model>` dispositions honored:

- **T-02-04 (YAML inject — mitigate):** `grep -c "yaml.unsafe_load\|yaml.load("` in `clawteam/team/envelope.py` returns 0; only `yaml.safe_load` is used.
- **T-02-09 (unbounded YAML — accept):** No size cap imposed in this plan; the 50 KB ArtifactStore.write cap (Plan 02-06) is the defense-in-depth bound.
- **T-02-10 (error-message info disclosure — mitigate):** `MalformedEnvelopeError` builds from pydantic's `exc.errors()[0]['msg']` (short human-readable sentence) + dot-joined `loc` path; the raw malformed value never appears in the error string. Verified by `test_validate_envelope_raises_malformed_envelope_error`.
- **T-02-01 (SSRF — accept):** No network activity in this plan; deferred to Plan 02-07 HEAD-dereferencer with 10s timeout + Phase 5 allowlist.

## TDD Gate Compliance

- **RED gate:** `5697b58` (`test(02-02): add failing tests ...`) — 12 tests fail at collection with `ModuleNotFoundError: No module named 'clawteam.team.envelope'`. Correct RED shape: not "test passes unexpectedly", but "imports the-module-not-yet-created".
- **GREEN gate:** `ed89289` (`feat(02-02): add TurnEnvelope + parse_frontmatter ...`) — all 12 tests pass; 89 regression tests still green.
- **REFACTOR gate:** Not applicable — the code as shipped from GREEN already matches the research §Example 1 shape verbatim; no cleanup commit needed.

Gate sequence visible in git log:
```
ed89289 feat(02-02): add TurnEnvelope + parse_frontmatter + optional envelope fields on TeamMessage
5697b58 test(02-02): add failing tests for TurnEnvelope + parse_frontmatter + TeamMessage envelope fields
```

## Acceptance Criteria Evidence

| Criterion | Result |
|---|---|
| `clawteam/team/envelope.py` ≥ 60 LOC | 95 LOC ✓ |
| `grep -c "class TurnEnvelope(BaseModel):"` == 1 | 1 ✓ |
| `grep -c "class MalformedEnvelopeError(ValueError):"` == 1 | 1 ✓ |
| `grep -c "def parse_frontmatter("` == 1 | 1 ✓ |
| `grep -c "def validate_envelope("` == 1 | 1 ✓ |
| `grep -c "yaml.safe_load"` ≥ 1 | 1 ✓ |
| `grep -c "yaml.unsafe_load\|yaml.load("` == 0 | 0 ✓ |
| `grep -c "persona: str \| None\|step_label: str \| None\|done: bool \| None"` (models.py) ≥ 3 | 3 ✓ |
| `grep -c "persona: str = Field(\.\.\.,"` (models.py — BC-guard) == 0 | 0 ✓ |
| `pytest tests/test_turn_envelope.py -q` → 12 passed | 12 ✓ |
| `pytest tests/test_models.py -q` → existing pass | all pass ✓ |
| `pytest tests/test_template_regression_matrix.py -q` → 12 passed (SC#10) | pass (bundled in 89 total) ✓ |
| `pytest tests/test_runtime_routing.py tests/test_waiter.py tests/test_mailbox.py -q` | all pass ✓ |
| Ruff clean on both modified files | `All checks passed!` ✓ |
| Commit messages start with `test(02-02):` / `feat(02-02):` | ✓ |

## Forward Contract (what downstream plans consume)

**Plan 02-07 (EvidenceGate):**
```python
from clawteam.team.envelope import parse_frontmatter, validate_envelope, MalformedEnvelopeError

meta, body = parse_frontmatter(raw_artifact)     # returns ({}, raw) on no-fence
envelope = validate_envelope(meta)               # raises MalformedEnvelopeError on invalid shape
# envelope.artifact_type → dispatch into EvidenceSchemaRegistry
```

**Plan 02-08 (Transport.deliver):**
```python
from clawteam.team.envelope import TurnEnvelope, MalformedEnvelopeError

# when sprint-scope is active:
TurnEnvelope.model_validate({
    "persona": message.persona,
    "step_label": message.step_label,
    "done": message.done,
})  # raises ValidationError → wrap into MalformedEnvelopeError at call site
```

## User Setup Required

None — PyYAML is installed via `uv pip install` into the project venv as a dev dep. Future fresh-clone users will pick it up via `uv sync --group dev` (or equivalent `pip install -e '.[dev]'`).

## Next Plan Readiness

- `TurnEnvelope`, `parse_frontmatter`, `validate_envelope`, `MalformedEnvelopeError` are shipped and importable.
- `TeamMessage.persona / step_label / done` exist as optional fields — Plan 02-08 can now extract them in `Transport.deliver()`.
- Phase 0 regression matrix green (12/12 bundled in the 89-test run).
- No blockers for Plans 02-03 through 02-13.

## Self-Check: PASSED

- [x] `clawteam/team/envelope.py` exists (95 LOC).
- [x] `tests/test_turn_envelope.py` exists (12 tests).
- [x] `clawteam/team/models.py` contains `persona: str | None`, `step_label: str | None = Field(default=None, alias="stepLabel")`, `done: bool | None` (optional — not required).
- [x] `pyproject.toml` contains `pyyaml>=6.0,<7.0` in `[project.optional-dependencies].dev`.
- [x] Commit `5697b58` exists in git log (RED / test).
- [x] Commit `ed89289` exists in git log (GREEN / feat).
- [x] 12/12 envelope tests pass.
- [x] 89/89 regression tests pass.

---
*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Plan: 02*
*Completed: 2026-04-20*
