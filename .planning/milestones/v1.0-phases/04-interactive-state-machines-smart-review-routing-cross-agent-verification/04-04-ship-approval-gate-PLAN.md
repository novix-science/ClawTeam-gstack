---
phase: 04
plan: 04
type: execute
wave: 1
depends_on: [01, 02]
files_modified:
  - clawteam/harness/ship_approval_gate.py
  - tests/test_ship_approval_gate.py
autonomous: true
requirements: [SPRINT-05]
must_haves:
  truths:
    - "ShipApprovalGate(InteractionGate) subclass exists at clawteam/harness/ship_approval_gate.py (NOT HumanApprovalGate — name-collision avoidance per PLAN_PREP_NOTES A9)."
    - "Gate blocks Ship advance when ship-approval.md artifact is missing."
    - "Gate blocks when ship-approval.md frontmatter lacks approved_by / approved_at / sha_at_approval fields."
    - "Gate blocks when sha_at_approval does not equal state.review_sha (if review_sha is set)."
    - "Gate ignores state.auto_advance=True (SPRINT-05 override semantic)."
    - "Gate check returns (True, '') when InteractionGate passes AND approval frontmatter present AND sha matches."
  artifacts:
    - path: "clawteam/harness/ship_approval_gate.py"
      provides: "Ship-phase gate subclassing InteractionGate with auto_advance override"
      contains: "class ShipApprovalGate(InteractionGate)"
      min_lines: 50
    - path: "tests/test_ship_approval_gate.py"
      provides: "Auto-advance override + missing/malformed/sha-mismatch approval tests"
      contains: "def test_ignores_auto_advance"
  key_links:
    - from: "clawteam/harness/ship_approval_gate.py"
      to: "clawteam/harness/interaction_gate.py"
      via: "super().check(state) delegates to InteractionGate Q&A pairing"
      pattern: "super().check"
    - from: "Plan 11 (GstackSprintPlugin.contribute_gates)"
      to: "ShipApprovalGate"
      via: "Plugin returns {'ship': [ShipApprovalGate()]}"
      pattern: "ShipApprovalGate()"
    - from: "Plan 12 (clawteam sprint approve CLI)"
      to: "ship-approval.md frontmatter schema"
      via: "CLI writes artifact with approved_by/approved_at/sha_at_approval keys this gate reads"
---

<objective>
Ship `ShipApprovalGate(InteractionGate)` at `clawteam/harness/ship_approval_gate.py` (name chosen per PLAN_PREP_NOTES A9 to avoid collision with the existing simple `HumanApprovalGate(PhaseGate)` in `clawteam/harness/phases.py:91`). Gate enforces SPRINT-05: Test→Ship advance requires both InteractionGate Q&A completion AND a signed `ship-approval.md` artifact with required frontmatter, regardless of `state.auto_advance`.

Purpose: SPRINT-05 is the production-blast-radius gate. `InteractionGate.auto_advance` escape hatch is exactly what must be bypassed. Subclassing inherits the question/answer plumbing while adding the explicit-approval requirement. Existing `force_interactive_phases=["ship"]` reservation in `SprintConductor.__init__` (already plumbed per A11) ensures the gate runs unconditionally.

Output: one new gate module + one test file. `InteractionGate` unchanged. The simple `HumanApprovalGate(PhaseGate)` at phases.py:91 remains untouched (different file, different name).
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
From clawteam/harness/interaction_gate.py (lines 49-99, existing):
```python
class InteractionGate(PhaseGate):
    def __init__(self, sprint_dir: Path | None = None) -> None:
        self._override_sprint_dir = sprint_dir

    def check(self, state: Any) -> tuple[bool, str]:
        # Returns (False, "Open questions: ...") when unanswered questions exist.
        # Returns (True, "") when no open questions or no sprint context.
```

From clawteam/sprint/state.py (after Plan 02 lands):
```python
class SprintState(BaseModel):
    # ... existing fields ...
    auto_advance: bool = True
    review_sha: str | None = None  # Plan 02
    artifacts: dict[str, str] = Field(default_factory=dict)
    # Name "ship-approval.md" is the key; value is the raw markdown including frontmatter.
```

From clawteam/team/envelope.py (existing):
```python
def parse_frontmatter(raw: str) -> tuple[dict, str]:
    """Parse YAML frontmatter; raises MalformedEnvelopeError on failure."""
```

Canonical ship-approval.md frontmatter (from §04-CONTEXT specifics):
```yaml
artifact_type: ship_approval
approved_by: <git-user-name>
approved_at: <ISO-8601 UTC>
sha_at_approval: <40-char git SHA>
approval_notes: <freeform, optional>
```
Note: `artifact_type` value per CONTEXT is `ship_approval` (underscore) — do NOT change; ship-notes.md already exists as a separate artifact.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement ShipApprovalGate with InteractionGate subclassing + frontmatter validation</name>
  <files>clawteam/harness/ship_approval_gate.py, tests/test_ship_approval_gate.py</files>
  <read_first>
    - clawteam/harness/interaction_gate.py (entire file — understand _resolve_sprint_dir + _scan)
    - clawteam/harness/phases.py (lines 91-103 — confirm existing HumanApprovalGate shape; we do NOT touch it)
    - clawteam/sprint/state.py (confirm Plan 02 added review_sha field)
    - clawteam/team/envelope.py (parse_frontmatter signature)
    - tests/test_interaction_gate.py (pattern for gate tests with SprintState fixture)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md (A9 confirms ShipApprovalGate name choice)
  </read_first>
  <behavior>
    - Test 1 (test_passes_when_interaction_ok_and_approval_valid): No open questions + ship-approval.md with all fields + sha matches → (True, "").
    - Test 2 (test_blocks_when_interaction_gate_blocks): Unanswered question exists → (False, "Open questions: ...") — inherited from super().check.
    - Test 3 (test_blocks_when_approval_missing): No ship-approval.md in state.artifacts → (False, mentions "ship-approval.md missing" + CLI hint).
    - Test 4 (test_blocks_when_approved_by_missing): Artifact present but frontmatter lacks approved_by → (False, "missing required field: approved_by").
    - Test 5 (test_blocks_when_approved_at_missing): Same for approved_at.
    - Test 6 (test_blocks_when_sha_at_approval_missing): Same for sha_at_approval.
    - Test 7 (test_blocks_when_sha_mismatch): sha_at_approval != state.review_sha → (False, mentions "HEAD advanced" + "re-approval").
    - Test 8 (test_passes_when_review_sha_unset): state.review_sha is None → skip SHA check; approval still required.
    - Test 9 (test_ignores_auto_advance): state.auto_advance=True is irrelevant; gate still requires approval (approval missing → still blocked).
    - Test 10 (test_malformed_frontmatter_blocks): ship-approval.md has unparsable frontmatter → (False, mentions malformed).
    - Test 11 (test_artifact_type_mismatch_not_enforced_at_gate_layer): Even if frontmatter artifact_type is "wrong", gate passes as long as the three required fields are present (schema enforcement is EvidenceGate's job).
  </behavior>
  <action>
Create `clawteam/harness/ship_approval_gate.py`:

```python
"""ShipApprovalGate — InteractionGate subclass enforcing always-human ship approval.

§04-CONTEXT D-13 / §REQUIREMENTS SPRINT-05. Production-blast-radius rule:
the Test → Ship transition ALWAYS requires a human-signed ``ship-approval.md``
artifact, regardless of ``auto_advance``. ``force_interactive_phases=["ship"]``
is already reserved in SprintConductor (Phase 2 Plan 02-11 line 222/247);
GstackSprintPlugin's contribute_gates registers THIS gate on the "ship" phase
at plugin load (Plan 04-11).

Name note: the existing ``HumanApprovalGate(PhaseGate)`` at
``clawteam/harness/phases.py:91`` is a simpler artifact-presence gate used
by non-gstack templates. Phase 4 deliberately uses the distinct name
``ShipApprovalGate`` to avoid import ambiguity (§04-RESEARCH A9).

Gate protocol (layered):
  1. Delegate to ``InteractionGate.check(state)`` — no unanswered questions.
  2. Verify ``ship-approval.md`` artifact present in ``state.artifacts``.
  3. Verify frontmatter contains ``approved_by``, ``approved_at``,
     ``sha_at_approval`` (non-empty).
  4. If ``state.review_sha`` is set, verify ``sha_at_approval == review_sha``
     (rejects post-approval HEAD advance — forces re-approval).

``state.auto_advance`` is intentionally NOT consulted. A ship advance with
``auto_advance=True`` and no approval artifact must still block.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from clawteam.harness.interaction_gate import InteractionGate
from clawteam.team.envelope import MalformedEnvelopeError, parse_frontmatter


_DEFAULT_ARTIFACT_NAME = "ship-approval.md"
_REQUIRED_FIELDS = ("approved_by", "approved_at", "sha_at_approval")


class ShipApprovalGate(InteractionGate):
    """Ship-phase gate: InteractionGate + signed ``ship-approval.md`` artifact.

    Constructor:
        gate = ShipApprovalGate()  # uses ship-approval.md default
        gate = ShipApprovalGate(ship_approval_artifact="custom-approval.md")
    """

    def __init__(
        self,
        *,
        ship_approval_artifact: str = _DEFAULT_ARTIFACT_NAME,
        sprint_dir: Path | None = None,
    ) -> None:
        super().__init__(sprint_dir=sprint_dir)
        self._artifact_name = ship_approval_artifact

    def check(self, state: Any) -> tuple[bool, str]:
        # Layer 1: InteractionGate questions/answers (no pending open).
        ok, reason = super().check(state)
        if not ok:
            return ok, reason

        # Layer 2: ship-approval.md present.
        artifacts = getattr(state, "artifacts", {}) or {}
        raw = artifacts.get(self._artifact_name, "")
        if not raw:
            sprint_id = getattr(state, "sprint_id", "<sprint-id>")
            return False, (
                f"Ship blocked: {self._artifact_name} missing. "
                f"Run `clawteam sprint approve {sprint_id} --phase ship` "
                f"or write the artifact manually."
            )

        # Layer 3: frontmatter required fields.
        try:
            meta, _body = parse_frontmatter(raw)
        except MalformedEnvelopeError as exc:
            return False, f"{self._artifact_name} malformed frontmatter: {exc}"

        for key in _REQUIRED_FIELDS:
            value = meta.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                return False, f"{self._artifact_name} missing required field: {key}"

        # Layer 4: sha_at_approval matches state.review_sha (when set).
        expected_sha = getattr(state, "review_sha", None)
        if expected_sha:
            actual_sha = str(meta["sha_at_approval"])
            if actual_sha != expected_sha:
                return False, (
                    f"{self._artifact_name} sha_at_approval={actual_sha!r} "
                    f"does not match review_sha={expected_sha!r}. HEAD advanced "
                    f"after approval — re-approval required."
                )

        return True, ""
```

Create `tests/test_ship_approval_gate.py`:

```python
"""Unit tests for clawteam/harness/ship_approval_gate.py (Plan 04-04)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from clawteam.harness.ship_approval_gate import ShipApprovalGate


_GOOD_SHA = "a1b2c3d4e5f6" + "0" * 28  # 40 chars

_GOOD_APPROVAL = f"""---
artifact_type: ship_approval
approved_by: alice@example.com
approved_at: 2026-04-21T14:32:00+00:00
sha_at_approval: {_GOOD_SHA}
approval_notes: LGTM
---

# Ship approval
Approved.
"""

_APPROVAL_MISSING_APPROVED_BY = f"""---
artifact_type: ship_approval
approved_at: 2026-04-21T14:32:00+00:00
sha_at_approval: {_GOOD_SHA}
---
body
"""

_APPROVAL_MISSING_APPROVED_AT = f"""---
artifact_type: ship_approval
approved_by: alice
sha_at_approval: {_GOOD_SHA}
---
body
"""

_APPROVAL_MISSING_SHA = """---
artifact_type: ship_approval
approved_by: alice
approved_at: 2026-04-21T14:32:00+00:00
---
body
"""

_APPROVAL_BAD_SHA = """---
artifact_type: ship_approval
approved_by: alice
approved_at: 2026-04-21T14:32:00+00:00
sha_at_approval: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
---
body
"""

_APPROVAL_MALFORMED = "no frontmatter here at all"


def _make_state(
    *,
    artifacts: dict | None = None,
    auto_advance: bool = True,
    review_sha: str | None = None,
    sprint_id: str = "abc12345",
):
    return SimpleNamespace(
        artifacts=artifacts or {},
        auto_advance=auto_advance,
        review_sha=review_sha,
        sprint_id=sprint_id,
    )


def test_passes_when_interaction_ok_and_approval_valid():
    gate = ShipApprovalGate()
    state = _make_state(
        artifacts={"ship-approval.md": _GOOD_APPROVAL},
        auto_advance=True,
        review_sha=_GOOD_SHA,
    )
    assert gate.check(state) == (True, "")


def test_blocks_when_approval_missing():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={}, auto_advance=True)
    ok, reason = gate.check(state)
    assert ok is False
    assert "ship-approval.md missing" in reason
    assert "clawteam sprint approve" in reason  # CLI hint


def test_blocks_when_approved_by_missing():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={"ship-approval.md": _APPROVAL_MISSING_APPROVED_BY})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing required field: approved_by" in reason


def test_blocks_when_approved_at_missing():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={"ship-approval.md": _APPROVAL_MISSING_APPROVED_AT})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing required field: approved_at" in reason


def test_blocks_when_sha_at_approval_missing():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={"ship-approval.md": _APPROVAL_MISSING_SHA})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing required field: sha_at_approval" in reason


def test_blocks_when_sha_mismatch():
    gate = ShipApprovalGate()
    state = _make_state(
        artifacts={"ship-approval.md": _APPROVAL_BAD_SHA},
        review_sha=_GOOD_SHA,
    )
    ok, reason = gate.check(state)
    assert ok is False
    assert "HEAD advanced" in reason or "does not match" in reason
    assert "re-approval" in reason


def test_passes_when_review_sha_unset():
    gate = ShipApprovalGate()
    state = _make_state(
        artifacts={"ship-approval.md": _GOOD_APPROVAL},
        review_sha=None,
    )
    # review_sha unset → Layer 4 skipped; layers 1-3 all pass.
    assert gate.check(state) == (True, "")


def test_ignores_auto_advance():
    """SPRINT-05: auto_advance=True is irrelevant when approval missing."""
    gate = ShipApprovalGate()
    state = _make_state(artifacts={}, auto_advance=True)
    ok, reason = gate.check(state)
    assert ok is False
    assert "ship-approval.md missing" in reason
    # And with approval present + auto_advance=True: passes.
    state2 = _make_state(
        artifacts={"ship-approval.md": _GOOD_APPROVAL},
        auto_advance=True,
        review_sha=_GOOD_SHA,
    )
    assert gate.check(state2) == (True, "")


def test_malformed_frontmatter_blocks():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={"ship-approval.md": _APPROVAL_MALFORMED})
    ok, reason = gate.check(state)
    assert ok is False
    # Either malformed detection or "missing approved_by" depending on parse_frontmatter behavior.
    assert "ship-approval.md" in reason


def test_custom_artifact_name():
    gate = ShipApprovalGate(ship_approval_artifact="custom-ship-approval.md")
    state = _make_state(artifacts={"custom-ship-approval.md": _GOOD_APPROVAL}, review_sha=_GOOD_SHA)
    assert gate.check(state) == (True, "")


def test_inherits_from_interaction_gate():
    from clawteam.harness.interaction_gate import InteractionGate
    assert issubclass(ShipApprovalGate, InteractionGate)
```

**Do not touch** `clawteam/harness/phases.py` (the existing HumanApprovalGate stays). **Do not touch** `clawteam/harness/interaction_gate.py` (parent class unchanged).
  </action>
  <verify>
    <automated>pytest tests/test_ship_approval_gate.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class ShipApprovalGate(InteractionGate)" clawteam/harness/ship_approval_gate.py
    - wc -l clawteam/harness/ship_approval_gate.py returns >= 50
    - pytest tests/test_ship_approval_gate.py -x -q exits 0 (11 tests)
    - grep -c "class HumanApprovalGate" clawteam/harness/phases.py returns exactly 1 (unchanged)
    - grep -L "HumanApprovalGate" clawteam/harness/ship_approval_gate.py (file does NOT contain the collision name)
    - pytest tests/test_interaction_gate.py tests/test_harness.py -x -q passes (no Phase 1/2 regression)
  </acceptance_criteria>
  <done>ShipApprovalGate enforces D-13 contract; 11 unit tests pass; existing HumanApprovalGate + InteractionGate untouched</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ship-approval.md text ↔ gate parsing | Attacker-controlled artifact body could inject malformed YAML |
| SprintState.review_sha ↔ sha_at_approval comparison | Mismatch must be a hard fail (not a warning) to prevent skipped approvals |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-10 | E (Elevation of privilege) | auto_advance bypass | mitigate | Gate explicitly ignores state.auto_advance; test_ignores_auto_advance enforces |
| T-04-11 | T (Tampering) | ship-approval.md SHA rewrite | mitigate | Gate verifies sha_at_approval equals state.review_sha; mismatch blocks. Plan 12's CLI writes a fresh SHA each invocation |
| T-04-12 | I (Information disclosure) | Error reason content | accept | Reason strings include sprint_id + artifact name — already public context; no secrets |
| T-04-13 | R (Repudiation) | Approval attribution | accept | approved_by is self-declared; git-signed commit (Plan 12's --sign flag) is the authoritative chain; gate only checks presence |
</threat_model>

<verification>
Plan 04 integration checks:
- [ ] `pytest tests/test_ship_approval_gate.py -x -q` exits 0 (11/11)
- [ ] `pytest tests/test_interaction_gate.py -x -q` still green (parent class unchanged)
- [ ] `pytest tests/test_harness.py -x -q` still green (existing HumanApprovalGate unchanged)
- [ ] `grep -c "ShipApprovalGate" clawteam/harness/ship_approval_gate.py` returns 1 (single definition)
- [ ] `grep -c "HumanApprovalGate" clawteam/harness/` returns exactly the pre-existing count (2 — phases.py:91 + harness/__init__.py export)
</verification>

<success_criteria>
Plan 04 ships when:
- [ ] `ShipApprovalGate(InteractionGate)` implements the 4-layer check protocol per D-13
- [ ] Gate ignores `state.auto_advance=True`
- [ ] Gate reports actionable error reasons including CLI invocation hint
- [ ] All 11 tests pass
- [ ] Existing `HumanApprovalGate` in `phases.py` is untouched (confirmed by grep)
- [ ] Downstream Plan 11 can import via `from clawteam.harness.ship_approval_gate import ShipApprovalGate`
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-04-ship-approval-gate-SUMMARY.md` with:
- LOC count
- Test breakdown (which tests cover which D-13 layer)
- Confirmation: phases.py grep still shows one HumanApprovalGate
</output>
