"""TestReport — Test-phase artifact (per upstream gstack /qa and /qa-only rubrics).

Captures the test-command + pass/fail counts + output excerpt that Phase 2's
:class:`~clawteam.harness.evidence_gate.EvidenceGate` post-check dispatches against
(see ``clawteam/harness/evidence_gate.py`` lines 16-18). The ``test_command`` field
is load-bearing — EvidenceGate re-runs it via subprocess to verify qa is not gating
on a stale cache (Pitfall 8 defeat for runtime gaming).

Stub-defeating constraints (Pitfall 8 prevention):
  - ``test_command`` ≥5 chars — defeats empty or single-letter placeholders
  - ``output_excerpt`` ≥30 chars — forces qa to capture real command output
  - ``passed`` / ``failed`` non-negative ints — rejects negative/NaN gaming
  - ``qa_mode`` Literal enum — discriminates the two gstack QA modes
"""

from typing import Literal

from pydantic import BaseModel, Field


class TestReport(BaseModel):
    """Test-phase artifact. Written by qa after Build-phase code lands.

    The ``test_command`` field is required because Phase 2's EvidenceGate
    post-check dispatches against it (verified at evidence_gate.py:16-18).
    Agents cannot pass the gate with a hardcoded "all green" — EvidenceGate
    re-runs ``test_command`` and compares the live result.
    """

    artifact_type: Literal["test-report"]
    test_command: str = Field(..., min_length=5)
    passed: int = Field(..., ge=0)
    failed: int = Field(..., ge=0)
    output_excerpt: str = Field(..., min_length=30)
    qa_mode: Literal["qa", "qa-only"] = "qa"
    sprint_id: str
    created_at: str
