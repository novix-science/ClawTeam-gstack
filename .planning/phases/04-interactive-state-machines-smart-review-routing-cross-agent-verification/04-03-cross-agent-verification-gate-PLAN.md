---
phase: 04
plan: 03
type: execute
wave: 1
depends_on: [01]
files_modified:
  - clawteam/harness/cross_agent_verification_gate.py
  - tests/test_cross_agent_verification_gate.py
autonomous: true
requirements: [SPRINT-04, QUALITY-13]
must_haves:
  truths:
    - "CrossAgentVerificationGate(PhaseGate) subclass exists and imports cleanly."
    - "check(state) returns (True, '') when verifier returns ok; (False, reason) otherwise."
    - "Gate parses both source_artifact and target_artifact via EvidenceSchemaRegistry.parse_frontmatter without re-implementing YAML parsing."
    - "Verifier callable receives pydantic-validated schema instances (not raw dicts)."
    - "Missing either artifact returns (False, reason) without raising (defense-in-depth after EvidenceGate)."
  artifacts:
    - path: "clawteam/harness/cross_agent_verification_gate.py"
      provides: "Generic cross-artifact verification gate + VerificationPair pydantic model"
      contains: "class CrossAgentVerificationGate(PhaseGate)"
      min_lines: 60
    - path: "tests/test_cross_agent_verification_gate.py"
      provides: "Unit tests for gate construction, check(), and VerificationPair model"
      contains: "def test_verifier_ok"
  key_links:
    - from: "clawteam/harness/cross_agent_verification_gate.py"
      to: "clawteam/harness/evidence_schemas.py (EvidenceSchemaRegistry)"
      via: "get_schema() call to resolve artifact_type to pydantic class"
      pattern: "from clawteam.harness.evidence_schemas import get_schema"
    - from: "Plan 11 (GstackSprintPlugin.contribute_verification_pairs)"
      to: "VerificationPair pydantic model"
      via: "Plugin returns list[VerificationPair]"
---

<objective>
Ship the generic cross-artifact verification gate (D-10) and its plugin-contribution data model (D-12 `VerificationPair`). The gate mirrors `EvidenceGate`'s construction shape but, instead of a 4-layer per-artifact check, runs a user-supplied verifier fn across TWO artifacts loaded via the existing `EvidenceSchemaRegistry`.

Purpose: This is the generic substrate for cross-agent verification. It has zero gstack-specific logic; the two gstack verifier fns (qa↔engineer test-report + reviewer↔designer design-doc) ship in Plan 11, and the plugin hook that wires them in ships in Plan 05.

Output: one new module + one test file. No existing code touched.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md

<interfaces>
<!-- Substrate the gate consumes. All lines verified this session. -->

From clawteam/harness/phases.py (existing):
```python
class PhaseGate(ABC):
    @abstractmethod
    def check(self, state: PhaseState) -> tuple[bool, str]:
        """Return (passed, reason)."""
```

From clawteam/harness/evidence_schemas.py (existing):
```python
def get_schema(artifact_type: str) -> type[BaseModel] | None:
    """Resolve an artifact_type string (e.g., "test-report") to its registered pydantic class."""
```

From clawteam/team/envelope.py (existing):
```python
def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Parse a YAML frontmatter + markdown body. Raises MalformedEnvelopeError on failure."""
```

From clawteam/harness/evidence_gate.py (existing, lines 141-214 — pattern the new gate mirrors):
```python
class EvidenceGate(ArtifactRequiredGate):
    def check(self, state) -> tuple[bool, str]:
        ok, reason = super().check(state)  # presence check
        if not ok:
            return ok, reason
        for name in self.artifact_names:
            raw = state.artifacts.get(name, "")
            meta, body = parse_frontmatter(raw)
            atype = meta.get("artifact_type", "")
            schema_cls = get_schema(atype)
            schema_cls.model_validate(meta)
            # ... 4-layer protocol
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement CrossAgentVerificationGate + VerificationPair</name>
  <files>clawteam/harness/cross_agent_verification_gate.py, tests/test_cross_agent_verification_gate.py</files>
  <read_first>
    - clawteam/harness/evidence_gate.py (lines 141-214 — shape to mirror)
    - clawteam/harness/phases.py (PhaseGate ABC)
    - clawteam/harness/evidence_schemas.py (get_schema signature + register_schema for test setup)
    - clawteam/team/envelope.py (parse_frontmatter + MalformedEnvelopeError)
    - tests/test_evidence_gate.py (pattern for gate-level tests with mock state.artifacts)
  </read_first>
  <behavior>
    - Test 1 (test_verifier_ok_returns_true): Given both artifacts present + schema registered + verifier returns (True, "OK"), gate.check returns (True, "").
    - Test 2 (test_verifier_fail_returns_false_with_reason): Verifier returns (False, "no overlap") → gate returns (False, "no overlap").
    - Test 3 (test_missing_source_artifact_returns_false): state.artifacts lacks source_artifact → (False, reason mentions "missing").
    - Test 4 (test_missing_target_artifact_returns_false): state.artifacts lacks target_artifact → (False, reason mentions "missing").
    - Test 5 (test_unregistered_schema_returns_false): artifact_type not in registry → (False, "unregistered schema").
    - Test 6 (test_malformed_frontmatter_returns_false): Artifact body without YAML frontmatter → (False, message mentions frontmatter).
    - Test 7 (test_verifier_exception_returns_false): Verifier raises → gate catches, returns (False, reason with exception type).
    - Test 8 (test_verification_pair_pydantic_model): VerificationPair instances validate required fields (phase, source_artifact, target_artifact, verifier_dotted_path).
  </behavior>
  <action>
Create `clawteam/harness/cross_agent_verification_gate.py`:

```python
"""CrossAgentVerificationGate — cross-artifact verification gate (§04-CONTEXT D-10/D-12).

Generic substrate for Phase 4's cross-agent verification: one gate loads
TWO artifacts via EvidenceSchemaRegistry (Phase 2), runs a user-supplied
verifier function, and returns (True, "") or (False, reason).

Opt-in via plugin contribution (HarnessPlugin.contribute_verification_pairs,
Plan 05). Existing templates (software-dev, hedge-fund, etc.) neither
instantiate this gate nor the hook that creates it — delete-invariant
preserved (§04-CONTEXT <domain>).

Runs AFTER EvidenceGate in the gate chain (§04-RESEARCH A6): EvidenceGate
verifies presence + schema + stub + post-check per artifact; this gate
verifies pairwise consistency via the supplied verifier fn.
"""

from __future__ import annotations

from typing import Any, Callable

from pydantic import BaseModel, Field

from clawteam.harness.evidence_schemas import get_schema
from clawteam.harness.phases import PhaseGate
from clawteam.team.envelope import MalformedEnvelopeError, parse_frontmatter


# Verifier signature: (source_model, target_model) -> (ok, reason)
# Both models are pydantic BaseModel instances produced by
# EvidenceSchemaRegistry (Phase 2 artifact schemas).
VerifierFn = Callable[[BaseModel, BaseModel], tuple[bool, str]]


class CrossAgentVerificationGate(PhaseGate):
    """Gate that verifies one artifact against another via a plugin-supplied fn.

    Construction:
        gate = CrossAgentVerificationGate(
            phase="test",
            source_artifact="test-report.md",
            target_artifact="build-report.md",
            verifier=verify_test_report_matches_engineer_output,
        )

    ``check(state)`` contract (§04-CONTEXT D-10):
        1. Verify both artifacts present in state.artifacts (defense-in-depth;
           EvidenceGate should have caught this).
        2. Parse frontmatter of each artifact via ``parse_frontmatter``.
        3. Resolve each artifact_type → pydantic schema via ``get_schema``.
        4. ``model_validate`` both frontmatter dicts.
        5. Invoke ``verifier(source_model, target_model)`` and return its
           result.

    Failure modes (all return (False, reason), never raise):
        * Missing artifact → "cross-verify missing: <name>"
        * Malformed frontmatter → "<name>: <exception message>"
        * Unregistered artifact_type → "cross-verify: unregistered schema <atype>"
        * Schema validation error → "<name>: frontmatter invalid: <exc>"
        * Verifier raises → "cross-verify exception: <ExceptionType>: <msg>"
    """

    def __init__(
        self,
        *,
        phase: str,
        source_artifact: str,
        target_artifact: str,
        verifier: VerifierFn,
    ) -> None:
        self.phase = phase
        self.source_artifact = source_artifact
        self.target_artifact = target_artifact
        self.verifier = verifier

    def check(self, state: Any) -> tuple[bool, str]:
        src_raw = getattr(state, "artifacts", {}).get(self.source_artifact, "")
        tgt_raw = getattr(state, "artifacts", {}).get(self.target_artifact, "")
        if not src_raw:
            return False, f"cross-verify missing: {self.source_artifact}"
        if not tgt_raw:
            return False, f"cross-verify missing: {self.target_artifact}"

        src_model, reason = self._parse_artifact(self.source_artifact, src_raw)
        if src_model is None:
            return False, reason
        tgt_model, reason = self._parse_artifact(self.target_artifact, tgt_raw)
        if tgt_model is None:
            return False, reason

        try:
            ok, reason = self.verifier(src_model, tgt_model)
        except Exception as exc:  # noqa: BLE001 — catch to avoid gate chain crash
            return False, f"cross-verify exception: {type(exc).__name__}: {exc}"

        if not ok:
            return False, reason
        return True, ""

    # ── internals ──────────────────────────────────────────────────────

    def _parse_artifact(
        self, name: str, raw: str
    ) -> tuple[BaseModel | None, str]:
        try:
            meta, _body = parse_frontmatter(raw)
        except MalformedEnvelopeError as exc:
            return None, f"{name}: {exc}"

        atype = meta.get("artifact_type", "")
        if not atype:
            return None, f"{name}: frontmatter missing artifact_type"

        schema_cls = get_schema(atype)
        if schema_cls is None:
            return None, f"cross-verify: unregistered schema {atype!r}"

        try:
            model = schema_cls.model_validate(meta)
        except Exception as exc:  # noqa: BLE001 — pydantic ValidationError + friends
            return None, f"{name}: frontmatter invalid: {exc}"

        return model, ""


class VerificationPair(BaseModel):
    """Plugin-contributed cross-verification pair (§04-CONTEXT D-12).

    Returned by ``HarnessPlugin.contribute_verification_pairs`` (Plan 05).
    ``PluginManager`` resolves ``verifier_dotted_path`` to a callable at
    plugin-load time and constructs a ``CrossAgentVerificationGate``.

    Deliberately dotted-path-indexed (not a Callable field) so the pair is
    serializable for introspection (e.g., ``clawteam doctor`` dumps the
    registered pairs).
    """

    phase: str = Field(..., min_length=1, description="Phase where gate runs (e.g., 'test', 'review').")
    source_artifact: str = Field(..., min_length=1, description="Primary artifact name (e.g., 'test-report.md').")
    target_artifact: str = Field(..., min_length=1, description="Peer artifact to verify against (e.g., 'build-report.md').")
    verifier_dotted_path: str = Field(
        ...,
        min_length=1,
        description=(
            "Dotted path to verifier callable, e.g. "
            "'clawteam.templates.gstack.verifiers.test_report_matches_diff.verify_test_report_matches_engineer_output'."
        ),
    )
```

Create `tests/test_cross_agent_verification_gate.py`:

```python
"""Unit tests for clawteam/harness/cross_agent_verification_gate.py (Plan 04-03)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel, Field

from clawteam.harness.cross_agent_verification_gate import (
    CrossAgentVerificationGate,
    VerificationPair,
)
from clawteam.harness.evidence_schemas import register_schema


class _FakeArtifactA(BaseModel):
    artifact_type: str = "fake-a"
    name: str = "a"


class _FakeArtifactB(BaseModel):
    artifact_type: str = "fake-b"
    count: int = 0


def _register_test_schemas():
    register_schema("fake-a", _FakeArtifactA)
    register_schema("fake-b", _FakeArtifactB)


def _make_state(artifacts: dict[str, str]) -> Any:
    return SimpleNamespace(artifacts=artifacts)


_RAW_A = "---\nartifact_type: fake-a\nname: alpha\n---\n\nbody text here"
_RAW_B = "---\nartifact_type: fake-b\ncount: 5\n---\n\nbody text here"
_RAW_MALFORMED = "this is not markdown with frontmatter"
_RAW_BAD_SCHEMA = "---\nartifact_type: not-registered\n---\n\nbody"


def test_verifier_ok_returns_true():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier=lambda s, t: (True, "OK"),
    )
    state = _make_state({"a.md": _RAW_A, "b.md": _RAW_B})
    assert gate.check(state) == (True, "")


def test_verifier_fail_returns_false_with_reason():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier=lambda s, t: (False, "no overlap between a and b"),
    )
    state = _make_state({"a.md": _RAW_A, "b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    assert "no overlap" in reason


def test_missing_source_artifact_returns_false():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="missing.md",
        target_artifact="b.md",
        verifier=lambda s, t: (True, ""),
    )
    state = _make_state({"b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing" in reason
    assert "missing.md" in reason


def test_missing_target_artifact_returns_false():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="missing.md",
        verifier=lambda s, t: (True, ""),
    )
    state = _make_state({"a.md": _RAW_A})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing.md" in reason


def test_unregistered_schema_returns_false():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="x.md",
        target_artifact="b.md",
        verifier=lambda s, t: (True, ""),
    )
    state = _make_state({"x.md": _RAW_BAD_SCHEMA, "b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    assert "unregistered schema" in reason


def test_malformed_frontmatter_returns_false():
    _register_test_schemas()
    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="bad.md",
        target_artifact="b.md",
        verifier=lambda s, t: (True, ""),
    )
    state = _make_state({"bad.md": _RAW_MALFORMED, "b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    # MalformedEnvelopeError string or "missing artifact_type" depending on parser behavior
    assert "bad.md" in reason


def test_verifier_exception_returns_false():
    _register_test_schemas()

    def throwing(s, t):
        raise ValueError("verifier broke")

    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier=throwing,
    )
    state = _make_state({"a.md": _RAW_A, "b.md": _RAW_B})
    ok, reason = gate.check(state)
    assert ok is False
    assert "ValueError" in reason
    assert "verifier broke" in reason


def test_verifier_receives_pydantic_models():
    _register_test_schemas()
    received: list = []

    def capture(s, t):
        received.append((s, t))
        return True, ""

    gate = CrossAgentVerificationGate(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier=capture,
    )
    state = _make_state({"a.md": _RAW_A, "b.md": _RAW_B})
    gate.check(state)
    src, tgt = received[0]
    assert isinstance(src, _FakeArtifactA)
    assert src.name == "alpha"
    assert isinstance(tgt, _FakeArtifactB)
    assert tgt.count == 5


def test_verification_pair_pydantic_model():
    pair = VerificationPair(
        phase="test",
        source_artifact="test-report.md",
        target_artifact="build-report.md",
        verifier_dotted_path="clawteam.templates.gstack.verifiers.test_report_matches_diff.verify_test_report_matches_engineer_output",
    )
    assert pair.phase == "test"
    assert pair.source_artifact == "test-report.md"
    assert pair.verifier_dotted_path.startswith("clawteam.templates.gstack.verifiers.")


def test_verification_pair_rejects_empty_fields():
    with pytest.raises(Exception):  # noqa: B017 — pydantic ValidationError
        VerificationPair(
            phase="",  # empty not allowed
            source_artifact="a",
            target_artifact="b",
            verifier_dotted_path="x.y",
        )
```

**Do not modify any other file.** Grep after edit: `ls clawteam/harness/cross_agent_verification_gate.py` succeeds; no other file in the commit set.
  </action>
  <verify>
    <automated>pytest tests/test_cross_agent_verification_gate.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class CrossAgentVerificationGate(PhaseGate)" clawteam/harness/cross_agent_verification_gate.py
    - grep -q "class VerificationPair(BaseModel)" clawteam/harness/cross_agent_verification_gate.py
    - grep -q "VerifierFn = Callable" clawteam/harness/cross_agent_verification_gate.py
    - wc -l clawteam/harness/cross_agent_verification_gate.py returns >= 60
    - pytest tests/test_cross_agent_verification_gate.py -x -q exits 0 (10 tests)
    - No existing test files modified
  </acceptance_criteria>
  <done>Generic cross-agent verification gate + VerificationPair model land; 10 unit tests pass; no existing code touched</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Plugin-supplied verifier ↔ gate execution | Verifier is user code; must not crash the phase gate chain |
| Artifact raw text ↔ pydantic validation | Malformed frontmatter is untrusted input |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-07 | T (Tampering) | Verifier fn | mitigate | Catch all exceptions; never crash gate chain; return (False, reason) with exception type in reason for operator debugging |
| T-04-08 | D (DoS) | Long verifier execution | accept | Verifiers are pure Python fns over pydantic models (no I/O); user code can still block but Phase 4 scope is the gate substrate, not verifier sandbox. Future: add `verifier_timeout_seconds` to VerificationPair if hangs observed. |
| T-04-09 | I (Information disclosure) | Error reason leakage | accept | Exception messages may leak internal path info; already acceptable pattern in EvidenceGate (evidence_gate.py:270); matches T-02-18 accepted threat |
</threat_model>

<verification>
Plan 03 integration checks:
- [ ] `pytest tests/test_cross_agent_verification_gate.py -x -q` returns 0 with 10/10 tests passing
- [ ] `pytest tests/test_evidence_gate.py tests/test_evidence_schemas.py -x -q` still green (no Phase 2 regression)
- [ ] `python3 -c "from clawteam.harness.cross_agent_verification_gate import CrossAgentVerificationGate, VerificationPair, VerifierFn"` exits 0
- [ ] `grep -c "class " clawteam/harness/cross_agent_verification_gate.py` == 2 (CrossAgentVerificationGate + VerificationPair)
</verification>

<success_criteria>
Plan 03 ships when:
- [ ] New module `clawteam/harness/cross_agent_verification_gate.py` is importable
- [ ] `CrossAgentVerificationGate(PhaseGate)` handles all 8 failure modes without raising
- [ ] `VerificationPair(BaseModel)` validates required fields
- [ ] 10 unit tests cover ok, fail, missing-source, missing-target, unregistered schema, malformed frontmatter, verifier exception, pydantic model round-trip, empty-field rejection, verifier-receives-models
- [ ] Downstream Plan 05 can import `VerificationPair` without circular-import error
- [ ] Downstream Plan 11 can construct the gate with the gstack verifier fns
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-03-cross-agent-verification-gate-SUMMARY.md` with:
- LOC count of new module
- Test pass/fail breakdown
- Integration smoke: the gate chain insertion point Plan 11 will target
</output>
