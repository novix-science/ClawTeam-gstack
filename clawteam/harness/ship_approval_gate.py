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
``ShipApprovalGate`` to avoid import ambiguity (§04-RESEARCH A9 / PLAN_PREP_NOTES A9).

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

        # parse_frontmatter returns ({}, raw) when no frontmatter block exists
        # (Pitfall #8 invariant — see clawteam/team/envelope.py:67). In that
        # case meta is empty and the required-field loop below rejects the
        # artifact with a "missing required field: approved_by" reason, which
        # still mentions the artifact name per test_malformed_frontmatter_blocks.
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
