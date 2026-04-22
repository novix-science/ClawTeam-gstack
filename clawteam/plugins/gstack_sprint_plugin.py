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
from clawteam.plugins.skill_registration import SkillRegistration
from clawteam.templates.gstack.schemas import (
    BenchmarkReport,
    CanaryReport,
    CodexReview,
    DeployNotes,
    DesignDoc,
    PlanDoc,
    Retro,
    ReviewReport,
    ShipNotes,
    TestReport,
)
from clawteam.templates.gstack.skills.codex.handler import (
    codex_handler as _codex_handler,
    tool_available as _codex_tool_available,
)
from clawteam.templates.gstack.skills.ship.handler import (
    gh_available as _ship_gh_available,
    ship_handler as _ship_handler,
)
from clawteam.templates.gstack.skills.setup_deploy.handler import (
    setup_deploy_handler as _setup_deploy_handler,
)
from clawteam.templates.gstack.skills.land_and_deploy.handler import (
    land_and_deploy_handler as _land_and_deploy_handler,
)
from clawteam.templates.gstack.skills.document_release.handler import (
    document_release_handler as _document_release_handler,
)
from clawteam.templates.gstack.skills.benchmark.handler import (
    benchmark_handler as _benchmark_handler,
)
from clawteam.templates.gstack.skills.canary.handler import (
    canary_handler as _canary_handler,
)

# Phase 6 Plan 06-05: /browse skill (SKILL-10, engineer/qa/dx-lead).
# Playwright probe routed through clawteam.browser so this module never
# top-level-imports playwright itself (D-02 invariant). If Plans 06-06 /
# 06-07 executors also alias ``playwright_available``, Python dedupes —
# the module-level name resolves to the same function object.
from clawteam.browser import playwright_available as _playwright_available
from clawteam.templates.gstack.skills.browse.handler import (
    browse_handler as _browse_handler,
)

# Phase 6 Plan 06-06: /open-gstack-browser (SKILL-10, headed mode). Same
# lazy-Playwright invariant as /browse (D-02). Handler opens Chromium
# headed so a human (designer / engineer / qa / dx-lead) can interact
# with a URL pre-seeded with cookies from the team cookie jar.
from clawteam.templates.gstack.skills.open_gstack_browser.handler import (
    open_browser_handler as _open_browser_handler,
)

# Phase 6 Plan 06-07: /setup-browser-cookies (SKILL-10, wizard). Reuses
# the same ``_playwright_available`` probe imported above (D-02); Python
# dedupes the alias so co-registered Phase 6 plans share one import.
from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
    setup_cookies_handler as _setup_cookies_handler,
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

# Phase 4 Plan 04-11 (§04-CONTEXT D-07): roles that receive a review-phase
# decorrelation supplement (prompts/review/<role>.md) appended to their base
# prompt. pm/ceo/eng-mgr/engineer/qa/shipper/sre are NOT in this set — they
# either are not review participants or do not need the staff-eng / rubric /
# threat-model / friction cross-cutting anchor.
_DECORRELATION_ROLES: frozenset[str] = frozenset(
    {"reviewer", "designer", "security", "dx-lead"}
)
_REVIEW_PROMPTS_SUBDIR: str = "review"


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
        """Register 10 pydantic schemas keyed by artifact_type Literal discriminator.

        Phase 3 Plan 03-07 shipped the 6 canonical gstack artifacts (design-doc /
        plan-doc / test-report / review-report / ship-notes / retro). Phase 5
        Plan 05-02 appends the 4 tool-heavy-skill artifacts (deploy-notes /
        canary-report / benchmark-report / codex-review) so Wave 2-4 skill
        handlers (Plans 05-03 through 05-09) can write typed evidence that
        passes through EvidenceGate without further plugin wiring.
        """
        return {
            "design-doc": DesignDoc,
            "plan-doc": PlanDoc,
            "test-report": TestReport,
            "review-report": ReviewReport,
            "ship-notes": ShipNotes,
            "retro": Retro,
            # Phase 5 Plan 05-02:
            "deploy-notes": DeployNotes,
            "canary-report": CanaryReport,
            "benchmark-report": BenchmarkReport,
            "codex-review": CodexReview,
        }

    # -- Phase 5 / Plan 05-03+ hooks (skill registrations) -------------

    def contribute_skills(self) -> list[SkillRegistration]:
        """Return the Phase 5 skill registrations contributed by gstack.

        Each Wave 2-4 plan appends exactly one new SkillRegistration to this
        list. Plan 05-03 lands /codex; subsequent plans add /ship,
        /land-and-deploy, /canary, /benchmark, /rollback, /sre-review.

        /codex — cross-model independent second opinion (SKILL-13).
            roles={engineer, reviewer}: engineer self-invokes for
            independent review; reviewer invokes for adversarial critique.
            install_hint mirrors what clawteam doctor prints.
        /ship — Build-phase-complete 5-step sprint action (SKILL-14, Plan 05-04).
            roles={shipper}: shipper-only — engineer / reviewer invoking
            gets SkillNotPermitted. install_hint matches doctor's gh entry.
        /setup-deploy — one-time deploy-config wizard (SKILL-19, Plan 05-05).
            roles={sre}: SRE-only. questionary is a hard dep (already in
            clawteam/cli) so no tool_available probe; install_hint empty.
        /land-and-deploy — merged-PR deploy action (SKILL-15, Plan 05-06).
            roles={shipper}: shipper-only. Provider-specific tool detection
            (vercel / netlify / flyctl / gh) happens inside the handler so
            the SkillRegistration has no static tool_available probe.
        /document-release — diff-vs-docs stale-ref detector (SKILL-16, Plan 05-07).
            roles={shipper}: shipper-only. Auto-invoked by /ship on success
            per D-11; pure-git baseline so no tool_available probe needed
            (git is always present in a ClawTeam checkout).
        /canary — post-deploy HTTP polling monitor (SKILL-17, Plan 05-08).
            roles={sre}: SRE-only. Polls deploy.md's deploy_url for window_seconds
            (default 300 from gstack.toml [canary]) and emits canary-report.md
            + DeployRegressionDetected when thresholds breached. Playwright is
            lazy-imported per Pitfall 5 so tool_available probe stays None
            (stdlib urllib is baseline; Playwright is optional browser mode).
        /benchmark — Core Web Vitals + page-load baselines (SKILL-18, Plan 05-09).
            roles={sre}: SRE-only. Lighthouse primary with curl -w fallback
            when the npm binary is missing (D-10). Writes benchmark-report.md
            and an optional pre-deploy baseline JSON (consumed by /canary).
            Emits WebVitalRegressionDetected when a vital exceeds
            regression_threshold_ratio * baseline (default 1.5×).
        """
        return [
            SkillRegistration(
                name="/codex",
                roles=frozenset({"engineer", "reviewer"}),
                handler=_codex_handler,
                tool_available=_codex_tool_available,
                install_hint="npm install -g @openai/codex",
            ),
            # Plan 05-04:
            SkillRegistration(
                name="/ship",
                roles=frozenset({"shipper"}),
                handler=_ship_handler,
                tool_available=_ship_gh_available,
                install_hint=(
                    "apt install gh | brew install gh | "
                    "winget install GitHub.cli"
                ),
            ),
            # Plan 05-05:
            SkillRegistration(
                name="/setup-deploy",
                roles=frozenset({"sre"}),
                handler=_setup_deploy_handler,
                tool_available=None,
                install_hint="",
            ),
            # Plan 05-06:
            SkillRegistration(
                name="/land-and-deploy",
                roles=frozenset({"shipper"}),
                handler=_land_and_deploy_handler,
                tool_available=None,  # provider detection is per-call in handler
                install_hint=(
                    "apt install gh | brew install gh  AND  "
                    "npm install -g <vercel|netlify>  OR  brew install flyctl"
                ),
            ),
            # Plan 05-07:
            SkillRegistration(
                name="/document-release",
                roles=frozenset({"shipper"}),
                handler=_document_release_handler,
                tool_available=None,  # git is baseline — no probe needed
                install_hint="",
            ),
            # Plan 05-08:
            SkillRegistration(
                name="/canary",
                roles=frozenset({"sre"}),
                handler=_canary_handler,
                tool_available=None,  # stdlib urllib baseline; Playwright lazy + optional
                install_hint="",
            ),
            # Plan 05-09:
            SkillRegistration(
                name="/benchmark",
                roles=frozenset({"sre"}),
                handler=_benchmark_handler,
                tool_available=None,  # lighthouse-or-curl fallback; never unavailable
                install_hint=(
                    "npm install -g lighthouse  "
                    "(optional — curl fallback measures ttfb/dom_loaded without it)"
                ),
            ),
            # Phase 6 Plan 06-05: /browse (SKILL-10, general-purpose headless).
            # Roles = {engineer, qa, dx-lead}: the three personas who invoke
            # URL + optional action-script navigation for debugging / QA /
            # DX exploration. Designer is intentionally NOT in this set —
            # designers use /open-gstack-browser (headed) instead (T-06-05-03).
            # URL allow-list (http/https only) sits inside browse_handler
            # BEFORE any browser launch (T-06-05-01); Playwright probe gates
            # dispatch with install_hint when absent.
            SkillRegistration(
                name="/browse",
                roles=frozenset({"engineer", "qa", "dx-lead"}),
                handler=_browse_handler,
                tool_available=_playwright_available,
                install_hint=(
                    "pip install 'clawteam[browser]' && "
                    "playwright install chromium"
                ),
            ),
            # Phase 6 Plan 06-06: /open-gstack-browser (SKILL-10, headed mode).
            # Roles = {engineer, qa, dx-lead, designer}: the four personas who
            # benefit from a pre-authenticated Chromium window — designer sees
            # the live UI, engineer debugs a running dev server, qa verifies
            # manually, dx-lead explores personas. Cookies loaded from the
            # per-domain jar populated by /setup-browser-cookies (Plan 06-07).
            # Playwright is optional; tool_available probe gates dispatch with
            # an install hint when absent (see SkillDispatcher:71-79).
            SkillRegistration(
                name="/open-gstack-browser",
                roles=frozenset({"engineer", "qa", "dx-lead", "designer"}),
                handler=_open_browser_handler,
                tool_available=_playwright_available,
                install_hint=(
                    "pip install 'clawteam[browser]' && "
                    "playwright install chromium"
                ),
            ),
            # Phase 6 Plan 06-07: /setup-browser-cookies (SKILL-10, wizard).
            # Roles = {engineer, qa, dx-lead}: the three personas who set up
            # per-domain authenticated session cookies for subsequent /browse
            # and /open-gstack-browser invocations. Questionary wizard runs
            # inside the handler; Playwright is optional and gated via the
            # shared probe — SkillUnavailable surfaces with an install hint
            # when absent (T-06-07-03 role check; T-06-07-01 domain validator
            # lives inside the wizard; T-06-07-02 on-disk plain-JSON cookies
            # accepted as user-machine-scoped by design — STACK.md).
            SkillRegistration(
                name="/setup-browser-cookies",
                roles=frozenset({"engineer", "qa", "dx-lead"}),
                handler=_setup_cookies_handler,
                tool_available=_playwright_available,
                install_hint=(
                    "pip install 'clawteam[browser]' && "
                    "playwright install chromium"
                ),
            ),
        ]

    # -- Per-role prompt resolution (T-07-02 + T-07-04 mitigations) ----

    def contribute_prompts(self, phase: str, role: str) -> str:
        """Resolve clawteam/templates/gstack/prompts/<role>.md for gstack roles.

        Returns empty string for non-gstack roles so other templates' roles
        flow through undisturbed (CORE-03 + QUALITY-14 backwards compat).

        Caches per (role) with mtime invalidation so edits during dev loops
        are picked up without process restart (T-07-04 mitigation).

        Phase 4 Plan 04-11 (§04-CONTEXT D-07): when ``phase == "review"``
        AND role is a decorrelation role (reviewer/designer/security/dx-lead),
        ALSO read clawteam/templates/gstack/prompts/review/<role>.md and
        append it as a supplement. Separator header marks the review-phase
        decorrelation boundary. Missing supplement file falls back gracefully
        to the base prompt (no supplement appended).
        """
        if role not in GSTACK_ROLES:
            return ""
        if not _valid_role(role):
            # Belt-and-suspenders: should be unreachable given containment
            # check above (GSTACK_ROLES is a frozen list of 11 kebab strings).
            return ""

        base = self._load_prompt_file(
            PROMPTS_DIR / f"{role}.md", cache_key=f"base:{role}"
        )
        if not base:
            return ""

        # Phase 4 Plan 04-11: decorrelation supplement for review phase.
        if phase == "review" and role in _DECORRELATION_ROLES:
            supplement_path = PROMPTS_DIR / _REVIEW_PROMPTS_SUBDIR / f"{role}.md"
            supplement = self._load_prompt_file(
                supplement_path, cache_key=f"review:{role}"
            )
            if supplement:
                return (
                    base
                    + "\n\n---\n\n"
                    + "<!-- PHASE 4 REVIEW DECORRELATION SUPPLEMENT -->\n\n"
                    + supplement
                )

        return base

    def _load_prompt_file(self, path: Path, *, cache_key: str) -> str:
        """Read a prompt file with mtime-invalidated caching.

        Generalization of the Phase 3 base-prompt cache so review-phase
        decorrelation supplements share the same mtime-invalidation semantics
        (T-07-04 mitigation). Returns "" on any failure — the plugin never
        raises from contribute_prompts.
        """
        if not path.is_file():
            return ""
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return ""
        cached = self._prompt_cache.get(cache_key)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return ""
        self._prompt_cache[cache_key] = (mtime, content)
        return content

    # ── Phase 4 / Plan 04-11 hooks ────────────────────────────────────

    def contribute_review_routers(self):  # type: ignore[override]
        """Return a GstackReviewRouter loaded from the gstack template's rules.

        §04-CONTEXT D-06 / SPRINT-03. Template is loaded lazily so this method
        is safe to call at plugin registration time regardless of template-load
        ordering. If the gstack template fails to load (unusual), returns empty.
        """
        try:
            from clawteam.harness.gstack_review_router import GstackReviewRouter
            from clawteam.templates import load_template
            tmpl = load_template("gstack")
            rules = list(tmpl.review.rules or [])
            return [GstackReviewRouter(rules)]
        except Exception:
            return []

    def contribute_verification_pairs(self):  # type: ignore[override]
        """Return the 2 gstack cross-verification pairs (§04-CONTEXT D-11).

        Pair 1 — Test phase:   test-report.md ↔ build-report.md   (qa verifies engineer)
        Pair 2 — Review phase: design-doc.md  ↔ office-hours-answers.md  (reviewer verifies designer)

        Verifier fns are resolved from dotted paths at plugin-load time by
        PluginManager._instantiate_and_register (Plan 04-05).
        """
        try:
            from clawteam.harness.cross_agent_verification_gate import VerificationPair
        except Exception:
            return []
        return [
            VerificationPair(
                phase="test",
                source_artifact="test-report.md",
                target_artifact="build-report.md",
                verifier_dotted_path=(
                    "clawteam.templates.gstack.verifiers.test_report_matches_diff."
                    "verify_test_report_matches_engineer_output"
                ),
            ),
            VerificationPair(
                phase="review",
                source_artifact="design-doc.md",
                target_artifact="office-hours-answers.md",
                verifier_dotted_path=(
                    "clawteam.templates.gstack.verifiers.design_doc_covers_forcing_qs."
                    "verify_design_doc_covers_forcing_questions"
                ),
            ),
        ]

    def contribute_gates(self):  # type: ignore[override]
        """Attach Phase 4 gates to phases (§04-CONTEXT D-13 — Plan 04-04 ShipApprovalGate).

        Extends the base-class default (empty dict). Returns a
        ``{phase -> [gates]}`` mapping; SprintConductor consumes via
        ``PluginManager.get_plugin_gates`` (Plan 04-05) + its
        ``_build_gate_chain`` extension (Plan 04-10 Task 3).
        """
        try:
            from clawteam.harness.ship_approval_gate import ShipApprovalGate
            return {"ship": [ShipApprovalGate()]}
        except Exception:
            return {}

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
