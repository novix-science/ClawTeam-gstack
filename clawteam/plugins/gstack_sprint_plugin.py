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

    def _on_phase_transition(self, event) -> None:
        """Reflect-phase entry: validate retro.md, write Phase 6 placeholder.

        Gated on template == 'gstack' so non-gstack sprints' Reflect phases
        (if any exist) don't trigger this write (T-07-01 HIGH mitigation).
        """
        if self._ctx is None:
            return

        # Only react to Reflect-phase entries.
        # PhaseTransition event ships `to_phase` (verified clawteam/events/types.py:170).
        # Tolerate alternate shapes defensively in case other emitters exist.
        to_phase = (
            getattr(event, "to_phase", None)
            or getattr(event, "phase_target", None)
            or getattr(event, "target", None)
        )
        if to_phase != "reflect":
            return

        team_name = (
            getattr(event, "team_name", None)
            or getattr(event, "team", None)
        )
        if not team_name:
            return

        # Cross-template isolation (T-07-01): only act on gstack-template teams.
        template_name = self._resolve_team_template(team_name)
        if template_name != "gstack":
            return

        # Sprint_id is not carried on PhaseTransition today (verified
        # clawteam/sprint/conductor.py:559). Support it when the emitter
        # adds it; fall back to scanning the team's sprints dir for the
        # one currently in reflect phase.
        sprint_id = getattr(event, "sprint_id", None) or self._find_reflecting_sprint(team_name)
        if not sprint_id:
            return

        # Validate retro.md structurally via 03-03 Retro schema.
        retro_body, personas = self._load_and_validate_retro(team_name, sprint_id)
        if retro_body is None:
            # Retro missing or fails schema - Phase 2 EvidenceGate already
            # blocked phase advance. Handler is best-effort; don't raise.
            return

        self._write_phase6_pending(team_name, sprint_id, retro_body, personas)

    # -- Internals -----------------------------------------------------

    def _resolve_team_template(self, team_name: str) -> str:
        """Look up TeamConfig.template for (team_name). Returns "" on any failure.

        Uses the existing _load_config helper in clawteam.team.manager which
        reads <data_dir>/teams/<team>/config.json and returns a TeamConfig
        (or None). Imported at call time to avoid module-load cycles.
        """
        try:
            from clawteam.team.manager import _load_config
            cfg = _load_config(team_name)
            if cfg is None:
                return ""
            return getattr(cfg, "template", "") or ""
        except Exception:
            return ""

    def _find_reflecting_sprint(self, team_name: str) -> str:
        """Walk the team's sprints dir, find the one whose current_phase == 'reflect'.

        Returns empty string if none found or on any error. Best-effort only.
        """
        try:
            from clawteam.team.models import get_data_dir
            from clawteam.sprint.state import load_sprint_state
        except Exception:
            return ""

        sprints_dir = get_data_dir() / "teams" / team_name / "sprints"
        if not sprints_dir.exists():
            return ""
        for sprint_dir in sorted(sprints_dir.iterdir()):
            if not sprint_dir.is_dir():
                continue
            try:
                state = load_sprint_state(team_name, sprint_dir.name)
            except Exception:
                continue
            if state.current_phase == "reflect":
                return state.sprint_id
        return ""

    def _load_and_validate_retro(
        self, team_name: str, sprint_id: str,
    ) -> tuple[str | None, list[str]]:
        """Load retro.md for (team, sprint) and round-trip through Retro schema.

        Returns (retro_body, personas) on success, (None, []) on any failure.
        """
        try:
            from clawteam.team.envelope import parse_frontmatter
            from clawteam.team.models import get_data_dir
        except Exception:
            return None, []

        retro_path = (
            get_data_dir() / "teams" / team_name / "sprints" / sprint_id
            / "artifacts" / "retro.md"
        )
        if not retro_path.is_file():
            return None, []
        try:
            content = retro_path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)
            retro = Retro(**frontmatter)
            personas = list(getattr(retro, "personas", []) or [])
            return body, personas
        except Exception:
            return None, []

    def _write_phase6_pending(
        self,
        team_name: str,
        sprint_id: str,
        retro_body: str,
        personas: list[str],
    ) -> None:
        """Write <data_dir>/teams/<team>/_phase6_pending/<sprint>-retro.json (D-09).

        Shape:
          {
            "sprint_id": "...",
            "team_name": "...",
            "retro_body": "<full markdown body>",
            "personas": ["eng-mgr", ...],
            "feature_flag": "phase6_learn_pending",
            "written_at": "<iso-utc>"
          }
        """
        try:
            from clawteam.fileutil import file_locked
            from clawteam.team.models import get_data_dir
        except Exception:
            return

        # Path-traversal guard (T-07-03): reject team/sprint names with
        # `/` or `..` BEFORE concatenation. Defense-in-depth; the conductor
        # upstream should also validate via clawteam.paths.validate_identifier.
        if (
            "/" in team_name
            or ".." in team_name
            or "/" in sprint_id
            or ".." in sprint_id
        ):
            return

        from datetime import datetime, timezone
        pending_dir = get_data_dir() / "teams" / team_name / "_phase6_pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        target = pending_dir / f"{sprint_id}-retro.json"

        payload = {
            "sprint_id": sprint_id,
            "team_name": team_name,
            "retro_body": retro_body,
            "personas": personas,
            "feature_flag": "phase6_learn_pending",
            "written_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            with file_locked(target):
                target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            return
