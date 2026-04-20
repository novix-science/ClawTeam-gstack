---
phase: 03-gstack-team-template-methodology-port
plan: 07
type: execute
wave: 3
depends_on: [03-03, 03-04, 03-05, 03-06]
files_modified:
  - clawteam/plugins/gstack_sprint_plugin.py
  - tests/test_gstack_plugin.py
autonomous: true
requirements: [TEAM-04, SPRINT-06]
must_haves:
  truths:
    - "GstackSprintPlugin registers 7 phases (think, plan, build, review, test, ship, reflect) via contribute_phases() — Phase 1 PhaseRegistry substrate accepts the list verbatim"
    - "GstackSprintPlugin registers 6 pydantic evidence schemas (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro) via contribute_evidence_schemas() — Phase 2 EvidenceSchemaRegistry dispatches by artifact_type Literal discriminator"
    - "contribute_prompts(phase, role) resolves clawteam/templates/gstack/prompts/<role>.md for the 11 gstack roles; returns empty string for non-gstack roles (BC preserved)"
    - "on_register() subscribes a Reflect-phase handler that validates retro.md via Retro schema and writes <data_dir>/teams/<team_name>/_phase6_pending/<sprint_id>-retro.json per D-09 (feature_flag: phase6_learn_pending)"
    - "Plugin hook consumption is gated on template context: event handler no-ops for non-gstack teams; prompt resolver returns empty for non-gstack roles — so existing 6 templates spawn unchanged (CORE-03 + QUALITY-14)"
  artifacts:
    - path: "clawteam/plugins/gstack_sprint_plugin.py"
      provides: "GstackSprintPlugin(HarnessPlugin) — single cohesive ~250 LOC file mirroring ralph_loop_plugin.py convention"
      contains: "class GstackSprintPlugin(HarnessPlugin)"
    - path: "tests/test_gstack_plugin.py"
      provides: "Un-xfailed plugin tests: test_only_ceo_advances_phase, test_seven_phases_registered, test_six_schemas_registered, test_prompts_resolve_for_all_eleven_roles, test_reflect_phase_learn_stub_writes_placeholder, test_plugin_isolation_for_other_templates"
      contains: "test_reflect_phase_learn_stub_writes_placeholder"
  key_links:
    - from: "clawteam/plugins/gstack_sprint_plugin.py"
      to: "clawteam/templates/gstack/schemas/__init__.py"
      via: "from clawteam.templates.gstack.schemas import DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro"
      pattern: "from clawteam.templates.gstack.schemas import"
    - from: "clawteam/plugins/gstack_sprint_plugin.py"
      to: "clawteam/templates/gstack/prompts/<role>.md"
      via: "contribute_prompts(phase, role) reads PROMPTS_DIR / f'{role}.md' for the 11 gstack roles"
      pattern: "PROMPTS_DIR"
    - from: "clawteam/plugins/gstack_sprint_plugin.py::on_register"
      to: "<data_dir>/teams/<team>/_phase6_pending/<sprint_id>-retro.json"
      via: "Reflect-phase event handler + file_locked() from clawteam.fileutil"
      pattern: "_phase6_pending"
    - from: "clawteam/plugins/gstack_sprint_plugin.py"
      to: "clawteam/sprint/conductor.py::advance_phase(actor=)"
      via: "Plugin does NOT call conductor; plugin populates registries conductor reads; leader-role check is conductor-side (03-01 added actor param)"
      pattern: "leader_role"
---

<objective>
Ship `clawteam/plugins/gstack_sprint_plugin.py` as the single cohesive plugin file (~250 LOC target, mirroring `ralph_loop_plugin.py` per Pattern 2) that wires together every Phase 3 artifact into the Phase 1/2 substrate: PhaseRegistry gets the 7 gstack phases; EvidenceSchemaRegistry gets the 6 pydantic schemas from 03-03; per-role prompts from 03-05/03-06 resolve through `contribute_prompts`; Reflect-phase transitions emit `_phase6_pending/<sprint_id>-retro.json` per D-09. Un-xfail `tests/test_gstack_plugin.py`.

Purpose: this plan is where Phase 3 becomes alive. Before this plan lands, all the gstack-specific artifacts exist as inert files (schemas in `clawteam/templates/gstack/schemas/`, envelopes in `envelope_personas.py`, prompts in `prompts/<role>.md`) but nothing plugs them into the conductor. After this plan, a sprint running under the gstack template sees all 7 phases, all 6 schemas validate artifact frontmatter, per-role prompts resolve at runtime, and Reflect-phase completion writes the Phase 6 placeholder file.

**Delete invariant honored (D-07):** The plugin file lives in `clawteam/plugins/` but imports EXCLUSIVELY from `clawteam/templates/gstack/` (schemas + prompts + envelope_personas). Delete `clawteam/plugins/gstack_sprint_plugin.py` + `clawteam/templates/gstack.toml` + `clawteam/templates/gstack/` and the codebase still runs unchanged.

**Cross-template isolation (Pitfall 14 / QUALITY-14 — the one HIGH-severity threat in Phase 3):** The plugin is loaded globally (per `PluginManager.discover()` mechanics) but its hooks NO-OP for non-gstack templates. `contribute_prompts(phase, "tech-lead")` returns `""` because `tech-lead` is not a gstack role. `on_register`'s Reflect-phase handler filters on template name before writing to `_phase6_pending/`. `contribute_phases()` and `contribute_evidence_schemas()` populate the registries unconditionally — but other templates don't consume gstack phases (they declare their own phase set) and other templates don't emit gstack artifact types (no `artifact_type: "design-doc"` in software-dev artifacts). Cross-template regression test lands in 03-09 to verify each of the 6 existing templates spawns cleanly with GstackSprintPlugin loaded.

**SmartReviewRouter — deferred to Phase 4:** `contribute_review_routers()` uses the HarnessPlugin default (`return []`). Do NOT ship router logic here; Phase 4 fills it per Pitfall 7 partition (locked in CONTEXT.md phase boundary).

Output:
- 1 plugin file at `clawteam/plugins/gstack_sprint_plugin.py` (~250 LOC, 5 hook overrides)
- `tests/test_gstack_plugin.py` un-xfailed with 6 new active tests + cross-template isolation scaffold (full isolation regression in 03-09)
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md
@.planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md
@.planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md
@.planning/phases/03-gstack-team-template-methodology-port/03-VALIDATION.md
@.planning/phases/03-gstack-team-template-methodology-port/03-01-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-02-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-03-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-04-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-05-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-06-SUMMARY.md

<interfaces>
<!-- Contracts the executor consumes from Phase 1/2 substrate + 03-01..03-06 artifacts. -->

From clawteam/plugins/base.py::HarnessPlugin (ABC — the plugin subclasses this):
  - abstractmethod on_register(ctx: HarnessContext) -> None  (subscribe to events)
  - on_unregister() -> None  (default no-op)
  - contribute_gates() -> dict[str, list[PhaseGate]]  (default {})
  - contribute_prompts(phase: str, role: str) -> str  (default "")
  - contribute_phases() -> list[Phase]  (default [])
  - contribute_phase_roles() -> dict[Phase, list[str]]  (default {})
  - contribute_review_routers() -> list[ReviewRouter]  (default [] — 03-07 uses default; Phase 4 overrides)
  - contribute_evidence_schemas() -> dict[str, type]  (default {})
  - class attrs: name (str), version (str), description (str)

From clawteam/plugins/ralph_loop_plugin.py (Pattern 2 canonical analog — mirror shape):
  - Single-file plugin class
  - __init__ stores config knobs and ctx = None placeholder
  - on_register sets self._ctx = ctx and subscribes via ctx.bus.subscribe(EventType, handler, priority=-10)
  - Handler early-returns on guard conditions (self._ctx is None, missing task store, etc.)
  - Side-effects via ctx.spawner / ctx.tasks / ctx.artifacts / ctx.sessions

From clawteam/harness/phases.py::Phase (Phase 1 substrate):
  - Phase is `type Phase = str` (open str per CONTEXT.md; "phases" are just names)
  - No Phase() constructor — a phase IS a string (e.g., "think")
  - The 7 gstack phase strings: "think", "plan", "build", "review", "test", "ship", "reflect"

From clawteam/templates/gstack/schemas/__init__.py (03-03 barrel — import in one statement):
  - Module re-exports: DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro
  - Each has artifact_type: Literal[<key>] discriminator
  - Discriminator keys: "design-doc", "plan-doc", "test-report", "review-report", "ship-notes", "retro"

From clawteam/templates/gstack/envelope_personas.py (03-04):
  - 11 TurnEnvelope subclasses + PERSONA_ENVELOPES: dict[str, type[TurnEnvelope]]
  - Keys: "pm", "ceo", "eng-mgr", "designer", "dx-lead", "engineer", "reviewer", "qa", "security", "shipper", "sre"

From clawteam/templates/gstack/prompts/<role>.md (03-05 + 03-06):
  - 11 files, each with `SIGNATURE: gstack-role:<role> ...` line
  - File naming: kebab-case role name (eng-mgr.md, dx-lead.md, pm.md, etc.)

From clawteam/fileutil.py::file_locked (existing substrate):
  - Context manager: `with file_locked(path): ... write ...`
  - Used by on_register's Reflect-phase handler for atomic writes to `_phase6_pending/`

From clawteam/sprint/conductor.py::SprintConductor.advance_phase (03-01 added actor param):
  - Signature: advance_phase(self, sprint_id: str, actor: str = "") -> ...
  - Reads TeamConfig.leader_role (03-01 added field) and rejects when actor != leader_role
  - Plugin does NOT call conductor; conductor consults the registry plugin populated

From clawteam/events/types.py (Phase 2 substrate):
  - PhaseTransition event (expected event type for Reflect-phase subscription)
  - If the event name differs in the actual codebase (verify during Read pass), adapt subscribe call accordingly

GSTACK_ROLES canonical list (11 items; use EXACTLY this ordering):
  ["pm", "ceo", "eng-mgr", "designer", "dx-lead", "engineer", "reviewer", "qa", "security", "shipper", "sre"]

GSTACK_PHASES canonical list (7 items; use EXACTLY this ordering):
  ["think", "plan", "build", "review", "test", "ship", "reflect"]

Plugin class attributes (match convention):
  name = "gstack-sprint"
  version = "0.1.0"
  description = "7-phase gstack sprint: Think -> Plan -> Build -> Review -> Test -> Ship -> Reflect"

Prompt resolution + isolation convention:
  PROMPTS_DIR = Path(__file__).parent.parent / "templates" / "gstack" / "prompts"
  def contribute_prompts(self, phase: str, role: str) -> str:
      if role not in GSTACK_ROLES:
          return ""   # non-gstack role — BC for other templates
      prompt_path = PROMPTS_DIR / f"{role}.md"
      ...
  Role guard: `role in GSTACK_ROLES` AND path construction uses `.stem`-equivalent (`role` must pass `_valid_role(role)`: isinstance(str) and "/" not in role and ".." not in role and role.isascii())

Reflect-phase handler filter (cross-template isolation):
  def _on_phase_transition(self, event) -> None:
      if event.phase_target != "reflect":
          return
      team_template = self._get_team_template(event.team_name)  # via self._ctx.sessions or TeamConfig read
      if team_template != "gstack":
          return   # non-gstack team — BC for other templates
      ... validate retro.md via Retro schema, write _phase6_pending/ file
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Scaffold GstackSprintPlugin class + contribute_phases + contribute_evidence_schemas</name>
  <files>clawteam/plugins/gstack_sprint_plugin.py</files>
  <read_first>
    - clawteam/plugins/base.py (HarnessPlugin ABC — confirm hook signatures match 03-07's implementation; Pattern 2 class-attribute convention)
    - clawteam/plugins/ralph_loop_plugin.py (Pattern 2 canonical analog — module docstring / class attrs / __init__ / on_register / handler method layout)
    - clawteam/templates/gstack/schemas/__init__.py (03-03 barrel — confirm importable names: DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro)
    - clawteam/harness/phases.py (lines 19-29 — Phase is open str type; the 7 phases are strings not Phase() calls)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (Pattern 2 + Pattern 5 + Code Examples §GstackSprintPlugin registration shape)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-04 gstack.toml phases list — confirms the 7 phase names + ordering)
  </read_first>
  <action>
**File: `clawteam/plugins/gstack_sprint_plugin.py`** (target ~250 LOC total; Task 1 delivers ~80 LOC of the scaffold + the 2 stateless hooks):

```python
"""GstackSprintPlugin — Phase 3 product surface.

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
    DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro,
)

if TYPE_CHECKING:
    from clawteam.harness.context import HarnessContext


# Canonical gstack constants — referenced by tests + cross-template isolation.
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
    """Guard against path traversal + symlink escape via attacker-controlled role."""
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
        # Cached (role) -> (mtime, content). Re-reads on file change.
        self._prompt_cache: dict[str, tuple[float, str]] = {}

    # ── Phase 1 / RFC 001 hooks ──────────────────────────────────────

    def contribute_phases(self) -> list[str]:
        """Return the 7 gstack phases (D-04 + RESEARCH.md Pattern 1)."""
        return list(GSTACK_PHASES)

    # ── Phase 2 hooks ────────────────────────────────────────────────

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
```

**Critical details:**
- `GSTACK_PHASES` and `GSTACK_ROLES` are module-level constants (tests import them).
- `_valid_role` is a module-level helper (tested directly for path-traversal defense).
- `PROMPTS_DIR` resolves via `Path(__file__).parent.parent` — the repo-scoped prompts dir, NOT a user-controlled path.
- `contribute_evidence_schemas` imports from the 03-03 barrel in ONE statement per the key_link.
- `contribute_phases` returns `list[str]` because `Phase` is `type Phase = str` (open str per `clawteam/harness/phases.py:19-29` + CONTEXT.md Pattern 1) — NOT `Phase(name="think")`.

Atomic-commit discipline (D-01 self-applied): single commit `feat(03-07): scaffold GstackSprintPlugin with contribute_phases + contribute_evidence_schemas`.
  </action>
  <verify>
    <automated>python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin, GSTACK_PHASES, GSTACK_ROLES; p = GstackSprintPlugin(); assert p.contribute_phases() == ['think','plan','build','review','test','ship','reflect']; assert set(p.contribute_evidence_schemas().keys()) == {'design-doc','plan-doc','test-report','review-report','ship-notes','retro'}; assert len(GSTACK_ROLES) == 11"</automated>
  </verify>
  <acceptance_criteria>
    - File exists: `test -f clawteam/plugins/gstack_sprint_plugin.py`
    - Imports from 03-03 barrel: `grep -q 'from clawteam.templates.gstack.schemas import' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - GSTACK_PHASES constant: `grep -q 'GSTACK_PHASES' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - GSTACK_ROLES constant with 11 members: `python -c "from clawteam.plugins.gstack_sprint_plugin import GSTACK_ROLES; assert len(GSTACK_ROLES) == 11"` exits 0
    - contribute_phases returns ordered 7: `python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; assert GstackSprintPlugin().contribute_phases() == ['think','plan','build','review','test','ship','reflect']"` exits 0
    - contribute_evidence_schemas returns 6 discriminator keys: `python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; assert set(GstackSprintPlugin().contribute_evidence_schemas().keys()) == {'design-doc','plan-doc','test-report','review-report','ship-notes','retro'}"` exits 0
    - Plugin is a HarnessPlugin subclass: `python -c "from clawteam.plugins.base import HarnessPlugin; from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; assert issubclass(GstackSprintPlugin, HarnessPlugin)"` exits 0
    - `pytest tests/ -x` exits 0 (no regressions to Phase 1/2 tests)
  </acceptance_criteria>
  <done>Plugin scaffold + 2 stateless hooks (phases, schemas) live; imports resolve; no test regressions.</done>
</task>

<task type="auto">
  <name>Task 2: contribute_prompts — per-role prompt resolver with mtime cache + path guard</name>
  <files>clawteam/plugins/gstack_sprint_plugin.py</files>
  <read_first>
    - clawteam/plugins/gstack_sprint_plugin.py (Task 1 output — extend, don't rewrite)
    - clawteam/templates/gstack/prompts/pm.md (03-05 output — confirm SIGNATURE line exists)
    - clawteam/templates/gstack/prompts/engineer.md (03-06 output — confirm SIGNATURE line)
    - clawteam/plugins/base.py (contribute_prompts signature: `(self, phase: str, role: str) -> str`; default returns "")
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (T-07-02 threat mitigation — path-traversal guard requirements)
  </read_first>
  <action>
**Append these methods inside the `GstackSprintPlugin` class (after `contribute_evidence_schemas`):**

```python
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
            # Guard: role passed GSTACK_ROLES containment but somehow contains
            # traversal chars (should be unreachable; belt-and-suspenders).
            return ""

        prompt_path = PROMPTS_DIR / f"{role}.md"
        if not prompt_path.is_file():
            # File missing — propagate empty so downstream sees the gap.
            # 03-09 integration test asserts all 11 files exist.
            return ""

        try:
            mtime = prompt_path.stat().st_mtime
        except OSError:
            return ""

        cached = self._prompt_cache.get(role)
        if cached is not None and cached[0] == mtime:
            return cached[1]

        content = prompt_path.read_text(encoding="utf-8")
        self._prompt_cache[role] = (mtime, content)
        return content
```

**Critical details:**
- Role containment check BEFORE path construction: non-gstack roles return `""` immediately, never touching disk.
- `_valid_role` is defensive second-layer guard; path traversal via `role = "../etc/passwd"` first fails `role in GSTACK_ROLES`, but the explicit check makes the security intent grep-able in security audits.
- `PROMPTS_DIR` is computed at module import (Task 1), not re-computed per call — prevents TOCTOU via directory reparenting.
- Cache invalidation is mtime-based (per `stat()` on each call). `stat()` is ~1-10µs; cache hit avoids the much larger `read_text()` cost. On cache hit without file-change, serve cached content.
- On any OSError during stat (race with delete, FS corruption), return `""` rather than raise — plugin hooks MUST NOT bubble exceptions into the plugin manager (ralph_loop_plugin convention: guard + early-return).

Atomic-commit discipline: single commit `feat(03-07): add contribute_prompts with role guard + mtime cache`.
  </action>
  <verify>
    <automated>python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; p = GstackSprintPlugin(); assert p.contribute_prompts('plan', 'tech-lead') == '' ; assert p.contribute_prompts('plan', '../etc/passwd') == '' ; pm = p.contribute_prompts('plan', 'pm'); assert 'SIGNATURE: gstack-role:pm' in pm; assert len(p.contribute_prompts('build', 'engineer')) > 100"</automated>
  </verify>
  <acceptance_criteria>
    - Non-gstack role returns empty: `python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; assert GstackSprintPlugin().contribute_prompts('plan', 'tech-lead') == ''"` exits 0
    - Path-traversal role returns empty: `python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; assert GstackSprintPlugin().contribute_prompts('plan', '../etc/passwd') == ''"` exits 0
    - All 11 gstack roles resolve non-empty: `python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin, GSTACK_ROLES; p = GstackSprintPlugin(); missing = [r for r in GSTACK_ROLES if 'SIGNATURE: gstack-role:'+r not in p.contribute_prompts('plan', r)]; assert not missing, missing"` exits 0
    - Cache present: `grep -q '_prompt_cache' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - mtime-based invalidation: `grep -q 'st_mtime\|stat().st_mtime' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - `pytest tests/ -x` exits 0
  </acceptance_criteria>
  <done>contribute_prompts resolves 11 gstack roles, returns empty for non-gstack and traversal-attempt roles, caches with mtime invalidation.</done>
</task>

<task type="auto">
  <name>Task 3: on_register + Reflect-phase handler writing _phase6_pending/ placeholder</name>
  <files>clawteam/plugins/gstack_sprint_plugin.py</files>
  <read_first>
    - clawteam/plugins/gstack_sprint_plugin.py (Tasks 1-2 output — append on_register + handler; do NOT rewrite)
    - clawteam/plugins/ralph_loop_plugin.py (Pattern 2 canonical on_register shape — ctx.bus.subscribe(EventType, handler, priority=-10); guard self._ctx is None early-return in handler)
    - clawteam/events/types.py (find the PhaseTransition event type; if name differs adapt subscribe call)
    - clawteam/fileutil.py (lines 9, 56 — file_locked signature + usage)
    - clawteam/team/models.py (TeamConfig — how to look up the template name for a team; leader_role field shipped in 03-01 per PATTERNS.md)
    - clawteam/templates/gstack/schemas/retro.py (03-03 output — Retro schema signature for validation)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-09 _phase6_pending shape: full retro markdown body + persona attribution metadata + feature_flag: phase6_learn_pending)
  </read_first>
  <action>
**Append these methods inside the `GstackSprintPlugin` class (after `contribute_prompts`):**

```python
    # ── Event subscription (Phase 2 PhaseTransition) ─────────────────

    def on_register(self, ctx: HarnessContext) -> None:
        """Subscribe Reflect-phase handler for /learn stub write (D-09 + SPRINT-06)."""
        # Import at call time so a missing event type doesn't break module import
        # (ralph_loop_plugin convention — imports inside on_register).
        try:
            from clawteam.events.types import PhaseTransition
        except ImportError:
            # Phase 2 event types not present — plugin is inert. Should not
            # happen in shipped tree but defends against partial installs.
            self._ctx = ctx
            return

        self._ctx = ctx
        ctx.bus.subscribe(PhaseTransition, self._on_phase_transition, priority=-10)

    def _on_phase_transition(self, event) -> None:
        """Reflect-phase entry: validate retro.md, write Phase 6 placeholder.

        Gated on template == 'gstack' so non-gstack sprints' Reflect phases
        (if any exist) don't trigger this write. Template resolution uses
        the HarnessContext-provided team lookup.
        """
        if self._ctx is None:
            return

        # Only react to Reflect-phase entries.
        target_phase = getattr(event, "phase_target", None) or getattr(event, "target", None)
        if target_phase != "reflect":
            return

        team_name = getattr(event, "team_name", None) or getattr(event, "team", None)
        sprint_id = getattr(event, "sprint_id", None)
        if not team_name or not sprint_id:
            return

        # Cross-template isolation: only act on gstack-template teams.
        template_name = self._resolve_team_template(team_name)
        if template_name != "gstack":
            return

        # Validate retro.md structurally via 03-03 Retro schema.
        retro_body, persona_attribution = self._load_and_validate_retro(team_name, sprint_id)
        if retro_body is None:
            # Retro missing or fails schema — Phase 2 EvidenceGate already
            # blocked phase advance. Handler is best-effort; don't raise.
            return

        # Compose + write the placeholder.
        self._write_phase6_pending(team_name, sprint_id, retro_body, persona_attribution)

    # ── Internals ────────────────────────────────────────────────────

    def _resolve_team_template(self, team_name: str) -> str:
        """Look up the team's template via TeamConfig. Returns "" on any failure."""
        if self._ctx is None:
            return ""
        try:
            from clawteam.team.models import get_team_config
            cfg = get_team_config(team_name)
            return getattr(cfg, "template", "") or ""
        except Exception:
            return ""

    def _load_and_validate_retro(
        self, team_name: str, sprint_id: str,
    ) -> tuple[str | None, list[str]]:
        """Load retro.md for (team, sprint) and round-trip through Retro schema.

        Returns (retro_body, personas) on success, (None, []) on any failure.
        """
        if self._ctx is None:
            return None, []
        try:
            from clawteam.team.envelope import parse_frontmatter
            from clawteam.team.models import get_data_dir
        except Exception:
            return None, []

        retro_path = (
            get_data_dir() / "teams" / team_name / "sprints" / sprint_id / "artifacts" / "retro.md"
        )
        if not retro_path.is_file():
            return None, []
        try:
            content = retro_path.read_text(encoding="utf-8")
            frontmatter, body = parse_frontmatter(content)
            retro = Retro(**frontmatter)
            return body, list(retro.personas)
        except Exception:
            return None, []

    def _write_phase6_pending(
        self,
        team_name: str,
        sprint_id: str,
        retro_body: str,
        personas: list[str],
    ) -> None:
        """Write <data_dir>/teams/<team>/_phase6_pending/<sprint>-retro.json.

        File shape (D-09):
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
            from clawteam.team.models import get_data_dir
            from clawteam.fileutil import file_locked
        except Exception:
            return

        # Path-traversal guard: team/sprint names must not escape the pending dir.
        if ("/" in team_name or ".." in team_name
                or "/" in sprint_id or ".." in sprint_id):
            return

        pending_dir = get_data_dir() / "teams" / team_name / "_phase6_pending"
        pending_dir.mkdir(parents=True, exist_ok=True)
        target = pending_dir / f"{sprint_id}-retro.json"

        import datetime
        payload = {
            "sprint_id": sprint_id,
            "team_name": team_name,
            "retro_body": retro_body,
            "personas": personas,
            "feature_flag": "phase6_learn_pending",
            "written_at": datetime.datetime.utcnow().isoformat() + "Z",
        }

        with file_locked(target):
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
```

**Critical details:**
- Import inside `on_register` (ralph_loop_plugin convention): if `PhaseTransition` doesn't exist in `clawteam/events/types.py`, the plugin registers as inert rather than crashing module load.
- Event field extraction uses `getattr(event, "phase_target", None) or getattr(event, "target", None)` — defensive because the exact event shape may differ between what the planner sketched and what Phase 2 actually shipped. Both `phase_target` and `target` are common shapes.
- `_resolve_team_template` uses `get_team_config(team_name)` (standard TeamConfig loader) — if that function doesn't exist under that name, the executor must grep `clawteam/team/models.py` for the equivalent and adapt.
- `parse_frontmatter` is Phase 2's YAML splitter (verified at `clawteam/team/envelope.py`). Retro is pydantic-validated via `Retro(**frontmatter)` — stub-grade retros reject per 03-03 `test_stub_fixture_rejected`.
- Path-traversal guard in `_write_phase6_pending` (T-07-03 mitigation): rejects team/sprint names containing `/` or `..` BEFORE concatenation.
- `file_locked` (from `clawteam/fileutil.py` line 56) is the existing atomic-write primitive — NEVER hand-roll locking.
- `datetime.datetime.utcnow()` + `.isoformat() + "Z"` yields an RFC 3339 timestamp. (Python 3.12+ deprecates `utcnow()`; if the repo is on 3.12+, adapt to `datetime.now(datetime.UTC).isoformat()`.)

Atomic-commit discipline: single commit `feat(03-07): on_register Reflect-phase handler writes _phase6_pending/ placeholder per D-09`.
  </action>
  <verify>
    <automated>python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; p = GstackSprintPlugin(); assert hasattr(p, 'on_register') and hasattr(p, '_on_phase_transition') and hasattr(p, '_write_phase6_pending')"</automated>
  </verify>
  <acceptance_criteria>
    - on_register subscribes to PhaseTransition: `grep -q 'ctx.bus.subscribe(PhaseTransition' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - Reflect-phase filter present: `grep -q 'target_phase != "reflect"' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - Template-gstack filter present: `grep -q 'template_name != "gstack"' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - feature_flag literal present verbatim: `grep -q 'phase6_learn_pending' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - file_locked used: `grep -q 'file_locked' clawteam/plugins/gstack_sprint_plugin.py` exits 0
    - Path-traversal guard: `grep -q '\.\.\|"/" in' clawteam/plugins/gstack_sprint_plugin.py` exits 0 (rejects `..` and `/` in team/sprint names)
    - Plugin still ≤ 400 LOC: `[ $(wc -l < clawteam/plugins/gstack_sprint_plugin.py) -le 400 ]` exits 0
    - `pytest tests/ -x` exits 0
  </acceptance_criteria>
  <done>Plugin is complete: 5 hooks (phases, schemas, prompts, on_register, _on_phase_transition handler) + path-traversal guard + file_locked atomic write for the Phase 6 placeholder.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Un-xfail tests/test_gstack_plugin.py — 6 active tests covering all 5 hooks + cross-template scaffold</name>
  <files>tests/test_gstack_plugin.py</files>
  <read_first>
    - tests/test_gstack_plugin.py (03-01 output — xfailed stubs; keep test function names; remove xfail decorators; fill bodies)
    - clawteam/plugins/gstack_sprint_plugin.py (Tasks 1-3 output — import symbols + verify expected shape)
    - clawteam/sprint/conductor.py (03-01 extension — advance_phase(sprint_id, actor="") signature to test)
    - clawteam/templates/gstack/schemas/retro.py (03-03 — build valid Retro fixture dict for the Reflect-phase handler test)
    - clawteam/events/types.py (PhaseTransition event shape — if available, construct a real event for the handler test; otherwise use a SimpleNamespace stub)
    - tests/conftest.py (existing fixtures — tmp_path, clawteam_data_dir or equivalent for isolating `_phase6_pending/` writes)
  </read_first>
  <behavior>
    - Test 1 (test_seven_phases_registered): GstackSprintPlugin().contribute_phases() == ["think","plan","build","review","test","ship","reflect"] in order
    - Test 2 (test_six_schemas_registered): keys == {design-doc, plan-doc, test-report, review-report, ship-notes, retro}; values are the pydantic classes from the 03-03 barrel
    - Test 3 (test_prompts_resolve_for_all_eleven_roles): contribute_prompts("plan", role) for each role in GSTACK_ROLES returns string containing f"SIGNATURE: gstack-role:{role}"; non-gstack role returns ""
    - Test 4 (test_prompts_reject_path_traversal): contribute_prompts("plan", "../etc/passwd") returns ""; contribute_prompts("plan", "/abs/path") returns "" (T-07-02 mitigation)
    - Test 5 (test_only_ceo_advances_phase): uses conftest to set up a gstack-loaded sprint; calls advance_phase(sprint_id, actor="engineer") — expect rejection (raises or returns failure flag); calls advance_phase(sprint_id, actor="ceo") — expect success (uses the 03-01 leader_role check)
    - Test 6 (test_reflect_phase_learn_stub_writes_placeholder): constructs a PhaseTransition(target="reflect", team_name=..., sprint_id=...); monkeypatch get_data_dir -> tmp_path; drops a valid retro.md under sprints/<id>/artifacts/; constructs plugin + fake ctx; invokes _on_phase_transition(event); asserts tmp_path / "teams/<team>/_phase6_pending/<sprint>-retro.json" exists; asserts json content contains feature_flag = "phase6_learn_pending" + personas list + retro_body
    - Test 7 (test_plugin_inert_for_non_gstack_team): same fixture but team's TeamConfig.template = "software-dev"; assert NO file written under `_phase6_pending/` (cross-template isolation — T-07-01 HIGH mitigation)
  </behavior>
  <action>
**File: `tests/test_gstack_plugin.py`** — remove all `@pytest.mark.xfail` decorators from 03-01 stubs; fill each function body. Apply as in-place edits to preserve 03-01's imports / fixture setup.

**Edit 1: Remove xfail decorators globally.**

Every `@pytest.mark.xfail(reason="...")` decorator on a test function in this file must be removed. The test function signatures stay the same (03-01 chose the names).

**Edit 2: Fill in test bodies.**

```python
# ---------------------------------------------------------------------------
# Phase registration + schema registration (stateless hooks)
# ---------------------------------------------------------------------------


def test_seven_phases_registered():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    plugin = GstackSprintPlugin()
    phases = plugin.contribute_phases()
    assert phases == ["think", "plan", "build", "review", "test", "ship", "reflect"], (
        f"expected 7 phases in canonical order, got {phases}"
    )


def test_six_schemas_registered():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.templates.gstack.schemas import (
        DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro,
    )
    plugin = GstackSprintPlugin()
    schemas = plugin.contribute_evidence_schemas()
    assert set(schemas.keys()) == {
        "design-doc", "plan-doc", "test-report", "review-report", "ship-notes", "retro",
    }
    assert schemas["design-doc"] is DesignDoc
    assert schemas["plan-doc"] is PlanDoc
    assert schemas["test-report"] is TestReport
    assert schemas["review-report"] is ReviewReport
    assert schemas["ship-notes"] is ShipNotes
    assert schemas["retro"] is Retro


# ---------------------------------------------------------------------------
# contribute_prompts + path-traversal guard (T-07-02)
# ---------------------------------------------------------------------------


def test_prompts_resolve_for_all_eleven_roles():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin, GSTACK_ROLES
    plugin = GstackSprintPlugin()
    assert len(GSTACK_ROLES) == 11
    for role in GSTACK_ROLES:
        content = plugin.contribute_prompts("plan", role)
        assert f"SIGNATURE: gstack-role:{role}" in content, (
            f"role {role!r} prompt missing SIGNATURE line; got {content[:200]!r}"
        )

    # Non-gstack role returns "" (BC for other templates)
    assert plugin.contribute_prompts("plan", "tech-lead") == ""
    assert plugin.contribute_prompts("plan", "researcher") == ""


def test_prompts_reject_path_traversal():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    plugin = GstackSprintPlugin()
    # All traversal attempts must return "" without touching disk.
    assert plugin.contribute_prompts("plan", "../etc/passwd") == ""
    assert plugin.contribute_prompts("plan", "..") == ""
    assert plugin.contribute_prompts("plan", "/abs/path") == ""
    assert plugin.contribute_prompts("plan", "pm/../ceo") == ""


# ---------------------------------------------------------------------------
# Leader-role binding (03-01 advance_phase actor check; TEAM-04)
# ---------------------------------------------------------------------------


def test_only_ceo_advances_phase(tmp_path, monkeypatch):
    """Regression: non-ceo actor rejected; ceo accepted. Depends on 03-01 conductor extension."""
    from clawteam.sprint.conductor import SprintConductor
    # Setup a minimal gstack-loaded sprint context. This test assumes 03-01's
    # conductor extension honors TeamConfig.leader_role. If the test-fixture
    # shape differs, adapt to the conftest fixture 03-01 authored.
    import inspect
    sig = inspect.signature(SprintConductor.advance_phase)
    assert "actor" in sig.parameters, (
        "03-01 must have added `actor: str` parameter to advance_phase"
    )
    assert sig.parameters["actor"].default == "", (
        "03-01's `actor` parameter must default to empty string (preserves Phase 2 callers)"
    )


# ---------------------------------------------------------------------------
# Reflect-phase /learn stub (SPRINT-06 + D-09)
# ---------------------------------------------------------------------------


def test_reflect_phase_learn_stub_writes_placeholder(tmp_path, monkeypatch):
    """On Reflect-phase entry for a gstack team, plugin writes _phase6_pending/<sprint>-retro.json."""
    from types import SimpleNamespace
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    team_name = "acme"
    sprint_id = "sprint-001"

    # Redirect get_data_dir to tmp_path (no real ~/.clawteam writes)
    import clawteam.team.models as team_models
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)
    # Redirect team-template lookup to return "gstack"
    monkeypatch.setattr(
        team_models, "get_team_config",
        lambda name: SimpleNamespace(template="gstack", leader_role="ceo"),
        raising=False,
    )

    # Drop a valid retro.md under the expected path
    retro_path = tmp_path / "teams" / team_name / "sprints" / sprint_id / "artifacts" / "retro.md"
    retro_path.parent.mkdir(parents=True, exist_ok=True)
    retro_path.write_text(
        "---\n"
        "artifact_type: retro\n"
        "personas:\n  - eng-mgr\n  - ceo\n  - engineer\n"
        "what_worked:\n  - Structured sprint\n"
        "what_failed: []\n"
        "key_lessons:\n  - Ship the stub\n"
        "sprint_id: " + sprint_id + "\n"
        "created_at: '2026-04-20T12:00:00Z'\n"
        "---\n"
        "# Retro body.\n",
        encoding="utf-8",
    )

    # Build plugin + fake ctx + event; drive the handler directly
    plugin = GstackSprintPlugin()
    plugin._ctx = SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None))
    event = SimpleNamespace(
        phase_target="reflect",
        team_name=team_name,
        sprint_id=sprint_id,
    )
    plugin._on_phase_transition(event)

    # Assert placeholder file exists + contains expected fields
    import json
    placeholder = tmp_path / "teams" / team_name / "_phase6_pending" / f"{sprint_id}-retro.json"
    assert placeholder.is_file(), f"expected {placeholder} to exist"
    data = json.loads(placeholder.read_text(encoding="utf-8"))
    assert data["feature_flag"] == "phase6_learn_pending"
    assert data["sprint_id"] == sprint_id
    assert data["team_name"] == team_name
    assert "eng-mgr" in data["personas"]
    assert "Retro body" in data["retro_body"]


def test_plugin_inert_for_non_gstack_team(tmp_path, monkeypatch):
    """T-07-01 HIGH mitigation: non-gstack team's Reflect-phase MUST NOT trigger _phase6_pending write."""
    from types import SimpleNamespace
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    team_name = "mixed-team"
    sprint_id = "sprint-xyz"

    import clawteam.team.models as team_models
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)
    # Return a non-gstack template
    monkeypatch.setattr(
        team_models, "get_team_config",
        lambda name: SimpleNamespace(template="software-dev", leader_role=""),
        raising=False,
    )

    plugin = GstackSprintPlugin()
    plugin._ctx = SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None))
    event = SimpleNamespace(
        phase_target="reflect",
        team_name=team_name,
        sprint_id=sprint_id,
    )
    plugin._on_phase_transition(event)

    pending_dir = tmp_path / "teams" / team_name / "_phase6_pending"
    assert not pending_dir.exists() or not list(pending_dir.glob("*.json")), (
        "plugin MUST NOT write _phase6_pending/ for non-gstack templates (T-07-01)"
    )
```

**Critical details:**
- Tests 1-4 run in-process with no fixtures — pure behavioral unit tests.
- Test 5 (`test_only_ceo_advances_phase`) validates 03-01's conductor extension SIGNATURE rather than driving a full sprint. A deeper integration test ships in 03-09 via `test_gstack_team_spawn.py`. This test's value is catching a reverted 03-01 signature.
- Tests 6-7 monkeypatch `get_data_dir` + `get_team_config` to isolate from `~/.clawteam/`. If 03-02 chose a different lookup function name, the executor MUST adapt using `raising=False` already present.
- `SimpleNamespace` fakes for event + ctx mirror ralph_loop_plugin's test style.

Atomic-commit discipline: single commit `test(03-07): un-xfail test_gstack_plugin.py with 6 active tests + cross-template isolation`.
  </action>
  <verify>
    <automated>pytest tests/test_gstack_plugin.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_gstack_plugin.py -x` exits 0 (all 6+ tests pass)
    - No remaining xfails: `grep -c '@pytest.mark.xfail' tests/test_gstack_plugin.py` outputs `0`
    - All 7 test functions present: `grep -c '^def test_' tests/test_gstack_plugin.py` outputs at least `6`
    - Handler test asserts feature_flag literal: `grep -q 'phase6_learn_pending' tests/test_gstack_plugin.py` exits 0
    - Cross-template isolation test present: `grep -q 'test_plugin_inert_for_non_gstack_team' tests/test_gstack_plugin.py` exits 0
    - Path-traversal test present: `grep -q 'test_prompts_reject_path_traversal' tests/test_gstack_plugin.py` exits 0
    - `pytest tests/ -x` exits 0 (full suite green)
  </acceptance_criteria>
  <done>tests/test_gstack_plugin.py active with 6-7 tests covering all 5 hooks + T-07-01 cross-template isolation + T-07-02 path-traversal guard.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Plugin load -> 6 other templates | GstackSprintPlugin registers into PhaseRegistry + EvidenceSchemaRegistry globally when loaded, but its event handler and prompt resolver NO-OP for non-gstack contexts. CORE-03 + QUALITY-14 BC is enforced at consumption, not registration. Verified by `test_plugin_inert_for_non_gstack_team` (this plan) + cross-template regression suite in 03-09. |
| Role name -> filesystem path | `contribute_prompts(phase, role)` receives `role` from caller (possibly attacker-controlled in adversarial scenarios). Two-layer guard: (1) `role in GSTACK_ROLES` containment check; (2) `_valid_role(role)` rejects `..`, `/`, `\\`, non-ASCII. Path construction via `PROMPTS_DIR / f"{role}.md"` is only reached after both guards pass. |
| Event payload -> filesystem write | `_on_phase_transition(event)` receives attacker-controllable `team_name` + `sprint_id` fields on the event. Handler rejects names containing `/` or `..` BEFORE concatenating to `get_data_dir() / "teams" / team_name / "_phase6_pending" / f"{sprint_id}-retro.json"`. `file_locked()` ensures atomic write (no partial file on concurrent Reflect entries). |
| Retro schema validation -> `_phase6_pending` write gate | The handler only writes the placeholder if `Retro(**frontmatter)` round-trips successfully. Stub-grade retro (empty personas, empty key_lessons) rejects per 03-03 constraint, so the `_phase6_pending/` entry for that sprint never appears — Phase 6 backfill sees an explicit "retro never finalized" state. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-07-01 | Tampering | **HIGH** — GstackSprintPlugin loaded for non-gstack template injects 7 phases + Reflect handler behavior into other templates (breaks CORE-03 + QUALITY-14) | **mitigate (security gate blocks on HIGH)** | Three-layer isolation: (1) `contribute_phases()` populates PhaseRegistry but other templates declare their own phase set in TOML and never iterate the gstack entries; (2) `contribute_prompts(phase, role)` returns empty for non-gstack roles (`role not in GSTACK_ROLES`); (3) `_on_phase_transition` filters on `template_name != "gstack"` before writing `_phase6_pending/`. Verified at 3 layers: `test_plugin_inert_for_non_gstack_team` in this plan + full 6-template cross-template regression in 03-09. HIGH severity justified by scope (all other templates) — three-layer defense is required for ASVS L1 pass. |
| T-07-02 | Tampering | Path traversal via attacker-controlled `role` argument to `contribute_prompts` (e.g., `role="../../etc/passwd"`) | mitigate | Two-layer guard: (1) `role in GSTACK_ROLES` containment check — GSTACK_ROLES is a module-level frozen list of 11 kebab-case strings; traversal payloads fail containment. (2) `_valid_role(role)` rejects strings containing `/`, `\\`, `..`, non-ASCII — belt-and-suspenders. `test_prompts_reject_path_traversal` (this plan) asserts 4 traversal payloads all return `""`. |
| T-07-03 | Tampering | Path traversal via attacker-controlled `team_name` or `sprint_id` in the PhaseTransition event payload (e.g., `team_name="../etc"`) | mitigate | `_write_phase6_pending` rejects `team_name` / `sprint_id` containing `/` or `..` BEFORE concatenation: `if ("/" in team_name or ".." in team_name or "/" in sprint_id or ".." in sprint_id): return`. Covered by handler acceptance criterion grep. Future hardening: adopt `WorkspaceManager.ensure_within_root()` when Phase 4 exposes it publicly; Phase 3 is defense-in-depth only. |
| T-07-04 | Tampering | Stale cached prompt served after the source file is edited (dev loop: edit prompt, reload doesn't pick up) | mitigate | mtime-based cache invalidation: every `contribute_prompts` call runs `prompt_path.stat().st_mtime`; cache hit is gated on matching mtime. `stat()` cost is ~1-10µs; negligible. No manual cache-reset API needed. |
| T-07-05 | Information Disclosure | Reflect-phase handler writes full retro markdown body to `_phase6_pending/<sprint>.json`; if retro contains secrets (API keys, tokens in lessons-learned) the JSON persists them | accept (Phase 6 closes) | Phase 3 writes the retro body verbatim as a placeholder. Phase 6's real `/learn` path implements secret-scrubbing before memory ingestion (per QUALITY-15 env deny-filter pattern). Between Phase 3 ship and Phase 6 ship, users are instructed (via retro.md prompt guidance in 03-05 eng-mgr.md) NOT to paste secrets into retros. Documented limitation in the plugin docstring. |
| T-07-06 | Denial of Service | Plugin module import fails (ImportError on a Phase 2 event type) and cascades to HarnessOrchestrator startup | mitigate | `on_register` uses a try/except around `from clawteam.events.types import PhaseTransition` and registers as inert on ImportError rather than raising. Plugin module-level imports (DesignDoc, PlanDoc, ... Retro) are from Phase 3's own `clawteam/templates/gstack/schemas/` barrel — if any fail to import, Phase 3 is broken by construction and the executor will fix at Task 1 verify. |

</threat_model>

<verification>
- Plugin file lives in correct location: `test -f clawteam/plugins/gstack_sprint_plugin.py`
- Plugin class name + HarnessPlugin subclass: `python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; from clawteam.plugins.base import HarnessPlugin; assert issubclass(GstackSprintPlugin, HarnessPlugin)"`
- 5 hooks implemented (phases, schemas, prompts, on_register, _on_phase_transition) — verified via `hasattr` checks in Task 4
- 7 phases in canonical order: `contribute_phases() == ["think","plan","build","review","test","ship","reflect"]`
- 6 schemas keyed by discriminator: keys == {design-doc, plan-doc, test-report, review-report, ship-notes, retro}
- 11 role prompts resolvable: all GSTACK_ROLES return non-empty `SIGNATURE: gstack-role:<role>` strings
- Non-gstack role returns empty: `contribute_prompts("plan", "tech-lead") == ""`
- Path-traversal blocked: 4 traversal payloads return empty
- Reflect-phase handler writes `_phase6_pending/<sprint>-retro.json` with `feature_flag: phase6_learn_pending`
- Cross-template isolation: non-gstack team's Reflect phase does NOT trigger `_phase6_pending` write (T-07-01)
- Delete invariant (D-07): `rm clawteam/plugins/gstack_sprint_plugin.py clawteam/templates/gstack.toml && rm -rf clawteam/templates/gstack/ && pytest tests/ -x --deselect tests/test_gstack_*.py --deselect tests/test_envelope_personas.py` still exits 0 (cross-template regression fully covers this in 03-09)
- Plugin file ≤ 400 LOC: `wc -l clawteam/plugins/gstack_sprint_plugin.py` outputs ≤ 400
- `pytest tests/ -x` exits 0
</verification>

<success_criteria>
- TEAM-04 plugin-layer enforcement: GstackSprintPlugin wires `contribute_evidence_schemas` (Retro schema round-trip on Reflect entry blocks stub-grade retros) + `on_register` (PhaseTransition subscription), completing the 3-layer leader-binding (conductor actor check from 03-01 + envelope persona Literal from 03-04 + plugin-scoped Reflect validation here)
- SPRINT-06 Reflect-phase /learn stub: plugin writes `<data_dir>/teams/<team>/_phase6_pending/<sprint_id>-retro.json` with `feature_flag: phase6_learn_pending` per D-09; validates retro.md via Retro schema first (stub retros never reach the placeholder file)
- Pattern 2 honored: single cohesive plugin file, ~250 LOC, mirrors ralph_loop_plugin.py structure
- Pattern 4 honored: leader-binding via `leader_role` + conductor-side `actor` check (03-01 sibling plan); plugin does NOT subclass SprintConductor
- Pattern 5 honored: 6 pydantic schemas registered via `contribute_evidence_schemas` keyed by `artifact_type: Literal[<key>]` discriminator
- Pattern 6 honored: Reflect-phase event handler + Phase 6 stub (feature_flag log line + placeholder file)
- D-07 delete invariant honored: plugin imports EXCLUSIVELY from `clawteam/templates/gstack/` (schemas + prompts + envelopes); the rest of the plugin body uses only substrate from `clawteam/plugins/base`, `clawteam/events`, `clawteam/fileutil`, `clawteam/team/models`, `clawteam/team/envelope` — all shipped or extended in Phase 1/2
- T-07-01 HIGH severity mitigated via 3-layer isolation (consumption-layer filters) — verified by dedicated test + cross-template regression in 03-09
- T-07-02..T-07-04 MEDIUM severities mitigated in-plan via guards + mtime cache
- Plugin activation mechanism: loaded via `PluginManager.discover()` (global config) but hooks no-op for non-gstack contexts. Scope: one plugin, 11 roles, 7 phases, 6 schemas.
- `pytest tests/ -x` exits 0 — no Phase 1/2 regressions
- SmartReviewRouter deferred to Phase 4 (contribute_review_routers() uses HarnessPlugin default `return []`)
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-07-SUMMARY.md` covering:
- Plugin file path + final LOC count
- 5 hooks implemented (name, signature, 1-line purpose) + 1 helper (`_resolve_team_template`) + 1 handler (`_on_phase_transition`) + 1 writer (`_write_phase6_pending`)
- T-07-01 HIGH mitigation verification: which test proves consumption-layer isolation for each of the 3 layers (registration / prompts / event handler)
- Reflect-phase output shape: example `_phase6_pending/<sprint>-retro.json` contents (field by field)
- Confirmation that 03-08 (team show CLI) can read `_phase6_pending/` directory to surface the "memory pending" dashboard column
- Confirmation that 03-09 (cross-template regression) can assert `GstackSprintPlugin().contribute_phases()` AND non-gstack templates' spawns still succeed with the plugin loaded (covers success criterion #2 + QUALITY-14)
</output>
