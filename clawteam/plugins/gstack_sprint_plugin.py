"""GstackSprintPlugin - Phase 3 product surface.

Registers the 7-phase gstack sprint (Think -> Plan -> Build -> Review -> Test -> Ship
-> Reflect) via PhaseRegistry, registers the 6 pydantic evidence schemas for the
gstack artifacts (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro)
via EvidenceSchemaRegistry, resolves per-role prompt files under
`clawteam/templates/gstack/prompts/<role>.md` via `contribute_prompts`, and
subscribes a Reflect-phase handler that writes a Phase 6 /learn placeholder.

Convention: single cohesive plugin file mirroring `ralph_loop_plugin.py`
(Pattern 2). All hooks gated on gstack-role / gstack-template context so loading
this plugin does NOT affect other templates (CORE-03 + QUALITY-14 backwards
compat; Pitfall 14 prevention).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from clawteam.plugins.base import HarnessPlugin
from clawteam.templates.gstack.schemas import (
    DesignDoc,
    PlanDoc,
    Retro,
    ReviewReport,
    ShipNotes,
    TestReport,
)

if TYPE_CHECKING:
    from clawteam.harness.context import HarnessContext


# Canonical gstack constants - referenced by tests + cross-template isolation.
GSTACK_PHASES: list[str] = [
    "think", "plan", "build", "review", "test", "ship", "reflect",
]

GSTACK_ROLES: list[str] = [
    "pm", "ceo", "eng-mgr", "designer", "dx-lead",
    "engineer", "reviewer", "qa", "security", "shipper", "sre",
]

# Prompt dir resolution (anchored at the package, not the CWD).
# clawteam/plugins/gstack_sprint_plugin.py -> clawteam/templates/gstack/prompts/
PROMPTS_DIR: Path = Path(__file__).parent.parent / "templates" / "gstack" / "prompts"


def _valid_role(role: str) -> bool:
    """Guard against path traversal + symlink escape via attacker-controlled role.

    Defense-in-depth second layer: most attacks fail the `role in GSTACK_ROLES`
    containment check first; this check makes the security intent grep-able and
    catches any future widening of GSTACK_ROLES that forgets to re-validate
    content.
    """
    return (
        isinstance(role, str)
        and role.isascii()
        and "/" not in role
        and "\\" not in role
        and ".." not in role
    )


class GstackSprintPlugin(HarnessPlugin):
    """Phase 3 plugin: wires gstack template into Phase 1/2 substrate."""

    name = "gstack-sprint"
    version = "0.1.0"
    description = (
        "7-phase gstack sprint: Think -> Plan -> Build -> Review -> Test -> Ship -> Reflect"
    )

    def __init__(self) -> None:
        self._ctx: HarnessContext | None = None
        # Cached (role) -> (mtime, content). Re-reads on file change (T-07-04).
        self._prompt_cache: dict[str, tuple[float, str]] = {}

    # -- Phase 1 / RFC 001 hooks ---------------------------------------

    def contribute_phases(self) -> list[str]:
        """Return the 7 gstack phases (D-04 + RESEARCH.md Pattern 1)."""
        return list(GSTACK_PHASES)

    # -- Phase 2 hooks -------------------------------------------------

    def contribute_evidence_schemas(self) -> dict[str, type]:
        """Register 6 pydantic schemas keyed by artifact_type Literal discriminator."""
        return {
            "design-doc": DesignDoc,
            "plan-doc": PlanDoc,
            "test-report": TestReport,
            "review-report": ReviewReport,
            "ship-notes": ShipNotes,
            "retro": Retro,
        }

    # -- Per-role prompt resolution (T-07-02 + T-07-04 mitigations) ----

    def contribute_prompts(self, phase: str, role: str) -> str:
        """Resolve clawteam/templates/gstack/prompts/<role>.md for gstack roles.

        Returns empty string for non-gstack roles so other templates' roles
        flow through undisturbed (CORE-03 + QUALITY-14 backwards compat).

        Caches per (role) with mtime invalidation so edits during dev loops
        are picked up without process restart (T-07-04 mitigation).
        """
        if role not in GSTACK_ROLES:
            return ""
        if not _valid_role(role):
            # Belt-and-suspenders: should be unreachable given containment
            # check above (GSTACK_ROLES is a frozen list of 11 kebab strings).
            return ""

        prompt_path = PROMPTS_DIR / f"{role}.md"
        if not prompt_path.is_file():
            # File missing - propagate empty so downstream sees the gap.
            # 03-09 integration test asserts all 11 files exist.
            return ""

        try:
            mtime = prompt_path.stat().st_mtime
        except OSError:
            return ""

        cached = self._prompt_cache.get(role)
        if cached is not None and cached[0] == mtime:
            return cached[1]

        try:
            content = prompt_path.read_text(encoding="utf-8")
        except OSError:
            return ""

        self._prompt_cache[role] = (mtime, content)
        return content

    # -- Event subscription (Phase 2 PhaseTransition) ------------------

    def on_register(self, ctx: HarnessContext) -> None:
        """Subscribe Reflect-phase handler for /learn stub write (D-09 + SPRINT-06).

        Imports the event type at call time so a missing Phase 2 event class
        does not break module import (ralph_loop_plugin convention).
        """
        try:
            from clawteam.events.types import PhaseTransition
        except ImportError:
            # Phase 2 event types not present - plugin is inert.
            self._ctx = ctx
            return

        self._ctx = ctx
        ctx.bus.subscribe(PhaseTransition, self._on_phase_transition, priority=-10)
