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

    Construction::

        gate = CrossAgentVerificationGate(
            phase="test",
            source_artifact="test-report.md",
            target_artifact="build-report.md",
            verifier=verify_test_report_matches_engineer_output,
        )

    ``check(state)`` contract (§04-CONTEXT D-10):
        1. Verify both artifacts present in ``state.artifacts``
           (defense-in-depth; EvidenceGate should have caught this).
        2. Parse frontmatter of each artifact via ``parse_frontmatter``.
        3. Resolve each ``artifact_type`` → pydantic schema via ``get_schema``.
        4. ``model_validate`` both frontmatter dicts.
        5. Invoke ``verifier(source_model, target_model)`` and return its
           result.

    Failure modes (all return (False, reason), never raise):
        * Missing artifact → ``"cross-verify missing: <name>"``
        * Malformed frontmatter → ``"<name>: <exception message>"``
        * Unregistered ``artifact_type`` → ``"cross-verify: unregistered schema <atype>"``
        * Schema validation error → ``"<name>: frontmatter invalid: <exc>"``
        * Verifier raises → ``"cross-verify exception: <ExceptionType>: <msg>"``
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

    def check(self, state: Any) -> tuple[bool, str]:  # type: ignore[override]
        artifacts = getattr(state, "artifacts", {}) or {}
        src_raw = artifacts.get(self.source_artifact, "")
        tgt_raw = artifacts.get(self.target_artifact, "")
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
    plugin-load time and constructs a :class:`CrossAgentVerificationGate`.

    Deliberately dotted-path-indexed (not a Callable field) so the pair is
    serializable for introspection (e.g., ``clawteam doctor`` dumps the
    registered pairs).
    """

    phase: str = Field(
        ...,
        min_length=1,
        description="Phase where gate runs (e.g., 'test', 'review').",
    )
    source_artifact: str = Field(
        ...,
        min_length=1,
        description="Primary artifact name (e.g., 'test-report.md').",
    )
    target_artifact: str = Field(
        ...,
        min_length=1,
        description="Peer artifact to verify against (e.g., 'build-report.md').",
    )
    verifier_dotted_path: str = Field(
        ...,
        min_length=1,
        description=(
            "Dotted path to verifier callable, e.g. "
            "'clawteam.templates.gstack.verifiers.test_report_matches_diff."
            "verify_test_report_matches_engineer_output'."
        ),
    )
