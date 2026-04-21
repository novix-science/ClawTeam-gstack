"""Base class for ClawTeam plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from clawteam.plugins.skill_registration import SkillRegistration

if TYPE_CHECKING:
    from clawteam.harness.context import HarnessContext
    from clawteam.harness.cross_agent_verification_gate import VerificationPair
    from clawteam.harness.phases import Phase, PhaseGate
    from clawteam.harness.review_router import ReviewRouter


class HarnessPlugin(ABC):
    """Base class for all ClawTeam plugins.

    Plugins receive a HarnessContext that provides access to the full
    framework: event bus, task store, spawner, sessions, artifacts.
    """

    name: str = ""
    version: str = "0.1.0"
    description: str = ""

    @abstractmethod
    def on_register(self, ctx: HarnessContext) -> None:
        """Called when the plugin is loaded.

        Use ctx.bus to subscribe to events.
        Use ctx.tasks/spawner/sessions/artifacts to take actions.
        """

    def on_unregister(self) -> None:
        """Called when the plugin is unloaded."""

    def contribute_gates(self) -> dict[str, list[PhaseGate]]:
        """Contribute gates to specific phases (§04-CONTEXT D-13 — Plan 04-05 wiring).

        Returns a mapping of phase-name → list of :class:`PhaseGate` instances
        to append to that phase's gate chain. ``PluginManager`` aggregates
        plugin-contributed gates via :meth:`PluginManager.get_plugin_gates`
        (Phase 4 Plan 04-05); ``SprintConductor._build_gate_chain`` (Phase 4
        Plan 04-10 Task 3) unions those gates into the standard
        EvidenceGate → forced_progress_gate → InteractionGate chain so
        plugin-provided gates (e.g., Phase 4's ShipApprovalGate) actually
        execute.

        Empty-dict default means the plugin contributes no gates. Existing
        plugins (software-dev, hedge-fund, code-review, harness-default,
        research-paper, strategy-room, ralph-loop) inherit the empty default
        and are unaffected. Phase 4's GstackSprintPlugin overrides this in
        Plan 04-11 to return ``{"ship": [ShipApprovalGate()]}``.
        """
        return {}

    def contribute_prompts(self, phase: str, role: str) -> str:
        """Contribute additional prompt text for agents in the given phase/role."""
        return ""

    # ── Phase 1 / RFC 001 hooks (optional; empty defaults preserve BC) ──

    def contribute_phases(self) -> list[Phase]:
        """Contribute lifecycle phase names to the PhaseRegistry.

        Returns an ordered list of phase names this plugin owns. Duplicate
        names across plugins are fatal at registration time. Empty-list
        default means the plugin does not contribute phases; the harness
        falls back to DEFAULT_PHASES (RFC 001 §4.3, D-03, D-04).
        """
        return []

    def contribute_phase_roles(self) -> dict[Phase, list[str]]:
        """Contribute phase-to-role mappings.

        Keys must be phases this same plugin declared in contribute_phases();
        the registry raises ValueError otherwise (RFC 001 §4.3a req 3).
        Values are ordered role lists — default participant order for the
        phase. Empty-dict default means the template's TOML-declared role
        list is used unchanged (RFC 001 §4.3a, D-04).
        """
        return {}

    def contribute_review_routers(self) -> list[ReviewRouter]:
        """Contribute review-routing rules for the Review phase.

        Routers are consulted in plugin load order. Full interface deferred
        to a future Phase 4 RFC; this Phase 1 hook only locks the hook
        point. Empty-list default means no additional reviewers are appended
        by this plugin (RFC 001 §4.3b, D-04).
        """
        return []

    # ── Phase 2 / Plan 02-01 hook ────────────────────────────────────

    def contribute_evidence_schemas(self) -> dict[str, type]:
        """Contribute artifact-frontmatter schemas to EvidenceSchemaRegistry.

        Keys are artifact_type strings (e.g., "design-doc", "plan-doc"); values
        are pydantic subclasses of ArtifactFrontmatterBase (Plan 02-04).
        Duplicate keys across plugins are fatal at registration time (mirrors
        PhaseRegistry D-03 namespace rule). Empty-dict default means the
        plugin registers no schemas.

        Phase 2 ships the hook with this empty default; Phase 3's
        GstackSprintPlugin.contribute_evidence_schemas() returns the six
        gstack artifact schemas (DesignDoc, PlanDoc, TestReport, ReviewReport,
        ShipNotes, Retro).
        """
        return {}

    # ── Phase 4 / Plan 04-05 hook ─────────────────────────────────────

    def contribute_verification_pairs(self) -> list[VerificationPair]:
        """Contribute cross-agent verification pairs (§04-CONTEXT D-12).

        Returns a list of :class:`VerificationPair` describing which artifact
        pairs should be cross-verified at which phase by which verifier
        function (dotted-path indexed). ``PluginManager`` resolves each
        ``verifier_dotted_path`` to a callable at plugin-load time and wires
        them into the gate chain consumed by SprintConductor (Plan 04-10
        _dispatch_review_phase + Plan 04-11 GstackSprintPlugin).

        Empty-list default means the plugin contributes no cross-verification
        gates. Phase 4's GstackSprintPlugin returns two pairs:
          - test-report.md ↔ build-report.md  (qa verifies engineer's output)
          - design-doc.md  ↔ office-hours-answers  (reviewer verifies designer)

        Hook is optional; existing plugins (software-dev, hedge-fund, code-review,
        harness-default, research-paper, strategy-room, ralph-loop) inherit the
        empty-list default and are unaffected.
        """
        return []

    # ── Phase 5 / Plan 05-01 hook ─────────────────────────────────────

    def contribute_skills(self) -> list[SkillRegistration]:
        """Contribute slash-skill dispatch entries (§05-CONTEXT D-04).

        Returns a list of :class:`SkillRegistration` describing skills this
        plugin exposes to agents. :meth:`PluginManager.get_plugin_skills`
        aggregates across plugins and raises ``ValueError`` on duplicate
        ``name`` (mirrors the PhaseRegistry duplicate-name rule).

        Empty-list default means the plugin contributes no skills. Existing
        plugins (software-dev, hedge-fund, code-review, harness-default,
        research-paper, strategy-room, ralph-loop, and the current Phase 3
        GstackSprintPlugin) inherit the empty default and are unaffected.
        Wave 2+ plans register actual skills on GstackSprintPlugin.
        """
        return []
