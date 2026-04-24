---
phase: 3
phase_name: Gstack Team Template & Methodology Port
phase_slug: gstack-team-template-methodology-port
mapped: 2026-04-20
status: Ready for planning
source: gsd-pattern-mapper
---

# Phase 3: Gstack Team Template & Methodology Port — Pattern Map

**Files analyzed:** 24 (12 NEW, 7 MODIFIED, 5 substrate verifications)
**Analogs found:** 22 / 24 (no in-repo analog: 11-role markdown prompts, gstack_skills WebFetch fixtures)

## File Classification

### NEW files

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `clawteam/templates/gstack.toml` | template-config (TOML) | declarative-config | `clawteam/templates/software-dev.toml` | exact-shape |
| `clawteam/templates/gstack/prompts/<role>.md` × 11 | prompt asset (markdown) | static-reference | none in repo (greenfield prose) | no-analog |
| `clawteam/templates/gstack/envelope_personas.py` | model (pydantic subclasses) | discriminated-union dispatch | `clawteam/team/envelope.py` (TurnEnvelope base) | role-match |
| `clawteam/templates/gstack/schemas/__init__.py` | barrel export | static-import | `clawteam/harness/evidence_schemas.py` (registry pattern) | role-adjacent |
| `clawteam/templates/gstack/schemas/design_doc.py` | model (pydantic) | structural-validation | `clawteam/harness/evidence_schemas.py::ArtifactFrontmatterBase` | exact-base |
| `clawteam/templates/gstack/schemas/plan_doc.py` | model (pydantic) | structural-validation | same as above | exact-base |
| `clawteam/templates/gstack/schemas/test_report.py` | model (pydantic) | structural-validation | same as above | exact-base |
| `clawteam/templates/gstack/schemas/review_report.py` | model (pydantic) | structural-validation | same as above | exact-base |
| `clawteam/templates/gstack/schemas/ship_notes.py` | model (pydantic) | structural-validation | same as above | exact-base |
| `clawteam/templates/gstack/schemas/retro.py` | model (pydantic) | structural-validation | same as above | exact-base |
| `clawteam/plugins/gstack_sprint_plugin.py` | plugin (HarnessPlugin subclass) | event-driven + registry-population | `clawteam/plugins/ralph_loop_plugin.py` | exact-shape |
| `tests/test_gstack_template.py` | unit test | TOML loader assertion | `tests/test_templates.py` | exact-shape |
| `tests/test_gstack_plugin.py` | unit + integration test | plugin registration assertion | `tests/test_plugin_hooks.py` | exact-shape |
| `tests/test_gstack_role_prompts.py` | golden grep test | content-presence assertion | `tests/test_evidence_schemas.py` (fixture-driven) | role-adjacent |
| `tests/test_envelope_personas.py` | unit test (pydantic) | discriminated-union round-trip | `tests/test_turn_envelope.py` | exact-shape |
| `tests/test_gstack_team_spawn.py` | integration test | `clawteam launch` full-flow | `tests/test_template_regression_matrix.py` | exact-shape |
| `tests/fixtures/gstack_skills/<skill>.md` × 11 | committed test fixture (markdown) | static reference | `tests/fixtures/qa/*.md` (markdown fixture layout) | role-match |
| `tests/fixtures/gstack_artifacts/` | committed test fixtures (markdown w/ frontmatter) | pydantic round-trip input | `tests/fixtures/qa/answer_freeform.md` (frontmatter shape) | role-match |

### MODIFIED files (extension-point identification)

| File | Modification | Extension Point Shape | Risk |
|------|--------------|------------------------|------|
| `clawteam/templates/__init__.py` | extend `TemplateDef` + `AgentDef` with optional fields (`role`, `prompt_file`, `phases`, `leader_role`, `model_profile`, `memory`) and extend `_parse_toml` to read them | additive pydantic fields w/ defaults; loader passthrough | low (verified `extra="ignore"` default behavior) |
| `clawteam/team/manager.py` | extend `create_team` with per-role memory-dir pre-creation step (D-05) | new keyword arg `roles: list[str] = []` + new `mkdir(parents=True, exist_ok=True)` block before return | low (additive; existing call sites unaffected) |
| `clawteam/sprint/conductor.py` | extend `advance_phase(self, sprint_id: str)` → `advance_phase(self, sprint_id: str, actor: str = "")` (D-10 verification confirmed: param absent in Phase 2) | add positional-or-keyword arg with empty-string default; insert leader-role check after `_load_by_id` | low (default empty preserves Phase 2 behavior) |
| `clawteam/cli/commands.py` | add `team_app.command("show")` returning rich dashboard (members + sprint progress + cost rollups + memory placeholders) | mirror existing `team_app.command("status")` shape (lines 1611-1656) | low (new command, no surface change) |
| `tests/test_template_regression_matrix.py` | extend `TEMPLATE_NAMES` list and add cross-isolation test asserting non-gstack templates do NOT load `GstackSprintPlugin` | additive parametrize entry + isolation test | none |
| `tests/test_evidence_schemas.py` | extend with 6 round-trip tests for the Phase 3 schemas (or new `tests/test_gstack_evidence_schemas.py`) | mirror existing `register_schema` / `get_schema` test pattern | none |
| `tests/test_cli_commands.py` | extend with `team show <name>` dashboard test | mirror `test_team_status_uses_configured_timezone` shape | none |

### Substrate to NOT modify (Phase 1/2 hook surface)

| File | Why Untouchable | Hook to Use Instead |
|------|----------------|---------------------|
| `clawteam/plugins/base.py` | `HarnessPlugin` ABC — Phase 1/2 hook contract | subclass via `HarnessPlugin` |
| `clawteam/harness/phases.py` + `phase_registry.py` | open-string Phase + global registry | populate via `contribute_phases()` |
| `clawteam/harness/evidence_schemas.py` | `EvidenceSchemaRegistry` populated by plugin manager | populate via `contribute_evidence_schemas()` |
| `clawteam/spawn/__init__.py` | spawn registry public API | route through `get_backend(name).spawn(...)` |
| `clawteam/workspace/manager.py` | WorkspaceManager — per-agent worktrees | call `create_workspace(team, agent, agent_id)` |

---

## Pattern Assignments

### NEW: `clawteam/templates/gstack.toml` (template-config)

**Analog:** `clawteam/templates/software-dev.toml`

**Top-block pattern** (`software-dev.toml` lines 1-6):
```toml
[template]
name = "software-dev"
description = "Software Development Team - multi-agent full-stack development with parallel workstreams"
command = ["claude"]
backend = "tmux"
```

**Leader pattern** (`software-dev.toml` lines 7-9, then prose body):
```toml
[template.leader]
name = "tech-lead"
type = "tech-lead"
task = """..."""
```

**Agent-row pattern** (`software-dev.toml` lines 35-39, repeats 4× there → 11× here):
```toml
[[template.agents]]
name = "backend-dev"
type = "backend-developer"
task = """..."""
```

**Tasks pattern** (`software-dev.toml` lines 110-128) — **OMITTED in gstack.toml per D-04** (no `[[template.tasks]]` rows; sprint-driven dispatch only).

**What differs in gstack.toml:**
1. Adds `leader_role = "ceo"` and `phases = ["think", "plan", "build", "review", "test", "ship", "reflect"]` to `[template]` block (these are NEW additive fields on `TemplateDef` per Pattern 1).
2. Adds `[template.model_profile]` block with per-role model assignment (e.g., `pm = "opus"`, `engineer = "sonnet"`, `shipper = "haiku"`) per RESEARCH.md §Code Examples lines 404-419.
3. Adds `[template.memory]` block: `root = "{data_dir}/teams/{team_name}/memory"`, `per_role = true` (D-05).
4. Each `[[template.agents]]` row adds `role = "<role>"` and `prompt_file = "gstack/prompts/<role>.md"` instead of inline `task = """..."""` prose (D-06).
5. No `[[template.tasks]]` rows (D-04 — gstack waits for `/sprint start`).

---

### NEW: `clawteam/templates/gstack/prompts/<role>.md` × 11 (prompt asset)

**Analog:** none in repo (greenfield prose). Closest in-repo asset by structural shape: the inline `task = """..."""` prose blocks inside `clawteam/templates/software-dev.toml` lines 10-33 (leader task) — but those live inside TOML, not standalone .md files. The greenfield format is RESEARCH.md §Code Examples "Role prompt skeleton (pm.md)" lines 447-517.

**Skeleton pattern** (RESEARCH.md lines 447-517 — verbatim copy-target for planner):
```markdown
# pm — YC Office Hours Advisor

You are pm, the team's external coach. ...

## Persona contract
Every turn you take MUST emit a TurnEnvelope (Phase 2 D-06) with these required fields:
- `persona: "pm"` (verbatim — drift detector triggers if absent)
- `step_label: "<phase>:<your-step>"`
- `done: false` while you have more to say; `true` to hand back to ceo
- `pm.challenge: "<one-sentence skeptical challenge>"` (REQUIRED)

## /office-hours rubric (interactive runtime — Phase 4)

INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 state machine.
Until then, do not enumerate the rubric in one turn. ...

The six forcing questions (full text from upstream gstack /office-hours):
1. Why now? ...
2. ...

## Per-role envelope schema (Phase 2 TurnEnvelope subclass)

```python
class PMEnvelope(TurnEnvelope):
    persona: Literal["pm"]
    pm_challenge: str = Field(..., min_length=20, alias="pm.challenge")
```

SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1
```

**Grep-verifiable invariants per file** (RESEARCH.md §"Per-Role Prompt Content Map" rows 728-740):

| Role | Required greppable strings |
|------|----------------------------|
| pm | All 6 forcing questions verbatim; `INTERACTIVE-RUNTIME-DEFERRED:`; `SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1` |
| ceo | 4 mode names (`Expansion`, `Selective`, `Hold`, `Reduction`); `SIGNATURE: gstack-role:ceo rubric:plan-ceo-review envelope-version:1` |
| eng-mgr | `architecture-lock`, `data-flow`, `edge-case matrix`, `test-plan`, `retro` headings; `SIGNATURE: gstack-role:eng-mgr rubric:plan-eng-review+retro envelope-version:1` |
| designer | 10 dimension names; AI-slop checklist; `INTERACTIVE-RUNTIME-DEFERRED:`; `SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1` |
| dx-lead | 3 personas (novice/pro/power-user); `TTHW`; friction tracing; `SIGNATURE: gstack-role:dx-lead rubric:plan-devex-review+devex-review envelope-version:1` |
| engineer | `engineer.diff_summary`; `read-first-before-write`; `atomic-commit`; `SHA-PIN-DEFERRED:` (per D-01); `SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1` |
| reviewer | `iron-law`; `halt-after-3`; `SHA-PIN-DEFERRED:`; `INTERACTIVE-RUNTIME-DEFERRED:` (for /investigate); `SIGNATURE: gstack-role:reviewer rubric:review+investigate envelope-version:1` |
| qa | bug-fix + regression-test loop; `qa.mode`; `qa-only`; `SIGNATURE: gstack-role:qa rubric:qa+qa-only envelope-version:1` |
| security | OWASP Top 10 (10 names); STRIDE (6 names); 17 false-positive exclusions verbatim; `security.confidence >= 8`; `SIGNATURE: gstack-role:security rubric:cso envelope-version:1` |
| shipper | `shipper.step` enum literal; Phase 5 tool-availability stub; `SIGNATURE: gstack-role:shipper rubric:none envelope-version:1` |
| sre | `sre.signal` enum literal; Phase 5 tool-availability stub; `SIGNATURE: gstack-role:sre rubric:none envelope-version:1` |

**What differs from any analog:** No in-repo file is a per-role agent system prompt. The closest functional parallel is the inline `task = """..."""` prose blocks inside template TOMLs (`software-dev.toml` line 10 onward) — extract those as the *style* reference for tone (imperative, second-person "You are...", responsibility list) but the format is greenfield.

**Hard cap (D-14):** every file ≤ 4 KB; average ≤ 3 KB. Plan must include `wc -c clawteam/templates/gstack/prompts/*.md` measurement task.

---

### NEW: `clawteam/templates/gstack/envelope_personas.py` (per-persona pydantic)

**Analog:** `clawteam/team/envelope.py` (TurnEnvelope base class)

**Imports pattern** (`envelope.py` lines 14-22):
```python
from __future__ import annotations

import re
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError
```

**Base-class pattern to subclass** (`envelope.py` lines 32-52):
```python
class TurnEnvelope(BaseModel):
    """Validates both TeamMessage envelope fields and artifact YAML frontmatter.

    Required fields (§02-CONTEXT D-06):
      - persona: agent role asserting this turn
      - step_label: free-form step marker, e.g. 'plan:2/5'
      - done: explicit turn-done signal
    """

    persona: str = Field(..., min_length=1, description="Agent role asserting this turn")
    step_label: str = Field(..., min_length=1, description="Free-form step marker")
    done: bool = Field(..., description="Turn-done signal")
    artifact_type: str | None = None
    created_at: str | None = None
    turn_id: str | None = None
```

**Subclass pattern to copy 11×** (RESEARCH.md §"Per-role envelope reassertion subclass" lines 624-691, verbatim):
```python
from typing import Literal
from pydantic import Field
from clawteam.team.envelope import TurnEnvelope

class PMEnvelope(TurnEnvelope):
    persona: Literal["pm"]
    pm_challenge: str = Field(..., min_length=20, alias="pm.challenge")

class CEOEnvelope(TurnEnvelope):
    persona: Literal["ceo"]
    ceo_decision_mode: Literal[
        "expansion", "selective", "hold", "reduction", "deferred"
    ] = Field(..., alias="ceo.decision_mode")

# ... 9 more (EngMgrEnvelope, DesignerEnvelope, DxLeadEnvelope, EngineerEnvelope,
#     ReviewerEnvelope, QAEnvelope, SecurityEnvelope, ShipperEnvelope, SREEnvelope)
```

**What differs from analog:** Subclasses constrain `persona` to a `Literal` (becomes a pydantic v2 discriminator) and add ONE namespaced field per persona. Lives in `clawteam/templates/gstack/` — not `clawteam/team/` — to honor the delete-invariant per D-07.

**Discriminated-union dispatch (extension to Phase 2 `parse_frontmatter`):** Plan must add a `validate_persona_envelope(meta)` helper that selects the right subclass via `meta["persona"]` lookup. Existing `validate_envelope(meta)` (`envelope.py` lines 82-95) is the structural template:
```python
def validate_envelope(meta: dict[str, Any]) -> TurnEnvelope:
    try:
        return TurnEnvelope.model_validate(meta)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"])
        raise MalformedEnvelopeError(
            f"envelope invalid: {field}: {first['msg']}"
        ) from exc
```

---

### NEW: `clawteam/templates/gstack/schemas/__init__.py` + 6 schema files (pydantic models)

**Analog:** `clawteam/harness/evidence_schemas.py::ArtifactFrontmatterBase` (the base class to subclass, lines 39-59)

**Base class to subclass** (`evidence_schemas.py` lines 39-59):
```python
from pydantic import BaseModel

class ArtifactFrontmatterBase(BaseModel):
    """Base pydantic model for durable-artifact YAML frontmatter.

    All five fields are required — Plan 02-07's :class:`EvidenceGate` asserts
    they are populated before running the 4-check protocol.

    Phase 3 concrete subclasses (DesignDoc / PlanDoc / TestReport /
    ReviewReport / ShipNotes / Retro) add artifact-specific required
    fields and section lists. Those subclasses override ``artifact_type`` with
    a ``Literal[...]`` default so the value is stable across instances and
    usable as a pydantic v2 discriminator key.
    """

    persona: str
    step_label: str
    done: bool
    artifact_type: str
    created_at: str
```

**Concrete subclass pattern (DesignDoc as worked example)** — RESEARCH.md §Code Examples lines 696-720 verbatim copy-target:
```python
# clawteam/templates/gstack/schemas/design_doc.py
from typing import Literal
from pydantic import BaseModel, Field

class DesignDoc(BaseModel):
    """Think-phase artifact. Written by pm + ceo collaboratively."""
    artifact_type: Literal["design-doc"]
    problem_statement: str = Field(..., min_length=120)
    users: str = Field(..., min_length=50)
    constraints: str = Field(..., min_length=50)
    rationale: str = Field(..., min_length=120)
    pm_verdict: Literal["proceed", "reframe", "kill"]
    forcing_questions_addressed: list[int] = Field(..., min_length=6, max_length=6)
    sprint_id: str
    created_at: str
```

**Stub-defeating constraints to apply (per Pitfall 8 / RESEARCH.md line 357):**
- `min_length=120` (≈25 words) on prose fields where stub content is meaningless.
- `Literal[...]` on enum fields so misspellings fail validation.
- `min_length=6, max_length=6` on the forcing_questions list (exact arity).

**Barrel `__init__.py` pattern** — pure re-exports for plugin import convenience:
```python
# clawteam/templates/gstack/schemas/__init__.py
from clawteam.templates.gstack.schemas.design_doc import DesignDoc
from clawteam.templates.gstack.schemas.plan_doc import PlanDoc
from clawteam.templates.gstack.schemas.test_report import TestReport
from clawteam.templates.gstack.schemas.review_report import ReviewReport
from clawteam.templates.gstack.schemas.ship_notes import ShipNotes
from clawteam.templates.gstack.schemas.retro import Retro

__all__ = ["DesignDoc", "PlanDoc", "TestReport", "ReviewReport", "ShipNotes", "Retro"]
```

**What differs from analog:** Phase 3 schemas inherit from `ArtifactFrontmatterBase` directly (or wrap with their own additional required fields per RESEARCH.md sketch). The `artifact_type` field becomes a `Literal[...]` to act as the discriminator for `EvidenceSchemaRegistry.get_schema()`.

**Per-schema field shape (planner refines from upstream gstack artifacts per CONTEXT.md "Claude's Discretion" §1):**
- `DesignDoc` — fields above (RESEARCH.md verbatim).
- `PlanDoc` — task list + dependencies + estimates; planner derives from `/plan-eng-review` rubric.
- `TestReport` — test_command (str, required for EvidenceGate post-check dispatch per `evidence_gate.py` line 16-18), pass/fail counts, output excerpt.
- `ReviewReport` — review_sha (per Pitfall 9 SHA-PIN-DEFERRED meta-instruction), verdict literal, hypothesis_traces list.
- `ShipNotes` — deploy_url (str, required for EvidenceGate post-check HEAD-probe per `evidence_gate.py` line 19-21), ship_step literal.
- `Retro` — per-persona attribution; retro body sections.

---

### NEW: `clawteam/plugins/gstack_sprint_plugin.py` (HarnessPlugin subclass)

**Analog:** `clawteam/plugins/ralph_loop_plugin.py` (canonical "single cohesive plugin file" reference per Pattern 2)

**File-header pattern** (`ralph_loop_plugin.py` lines 1-15):
```python
"""Ralph Loop plugin: re-spawn agents that exit before completing tasks.

Based on the Ralph technique (persistent iteration loops), adapted for
ClawTeam's multi-agent orchestration with role-scoped context recovery.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from clawteam.plugins.base import HarnessPlugin

if TYPE_CHECKING:
    from clawteam.harness.context import HarnessContext
```

**Class skeleton pattern** (`ralph_loop_plugin.py` lines 17-38):
```python
class RalphLoopPlugin(HarnessPlugin):
    """Re-spawn agents that exit before completing their tasks."""

    name = "ralph-loop"
    version = "0.1.0"
    description = "Re-spawn agents that exit before completing their tasks"

    def __init__(self, max_iterations: int = 5):
        self.max_iterations = max_iterations
        self._iterations: dict[str, int] = {}
        self._ctx: HarnessContext | None = None

    def on_register(self, ctx: HarnessContext) -> None:
        from clawteam.events.types import WorkerExit
        self._ctx = ctx
        ctx.bus.subscribe(WorkerExit, self._on_exit, priority=-10)
```

**Event handler pattern** (`ralph_loop_plugin.py` lines 40-79) — single private method subscribes once in `on_register`, persists `self._ctx`, references via late imports.

**GstackSprintPlugin shape to copy** — RESEARCH.md §Code Examples "GstackSprintPlugin registration shape" lines 521-619 verbatim copy-target:
```python
class GstackSprintPlugin(HarnessPlugin):
    name = "gstack-sprint"
    version = "1.0.0"
    description = "Gstack 7-phase sprint engine + 11-specialist team methodology"

    def on_register(self, ctx: "HarnessContext") -> None:
        from clawteam.events.types import PhaseTransition
        ctx.bus.subscribe(PhaseTransition, self._on_phase_transition)

    def contribute_phases(self) -> list["Phase"]:
        return ["think", "plan", "build", "review", "test", "ship", "reflect"]

    def contribute_phase_roles(self) -> dict["Phase", list[str]]:
        return {
            "think":   ["pm", "ceo"],
            "plan":    ["pm", "ceo", "eng-mgr", "designer", "dx-lead"],
            "build":   ["engineer"],
            "review":  ["reviewer", "qa", "security", "designer", "dx-lead"],
            "test":    ["qa", "engineer"],
            "ship":    ["shipper", "ceo"],
            "reflect": ["eng-mgr", "ceo"],
        }

    def contribute_evidence_schemas(self) -> dict[str, type]:
        from clawteam.templates.gstack.schemas import (
            DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro,
        )
        return {
            "design-doc":    DesignDoc,
            "plan-doc":      PlanDoc,
            "test-report":   TestReport,
            "review-report": ReviewReport,
            "ship-notes":    ShipNotes,
            "retro":         Retro,
        }

    def contribute_prompts(self, phase: str, role: str) -> str:
        from pathlib import Path
        prompt_path = (
            Path(__file__).parent.parent
            / "templates" / "gstack" / "prompts" / f"{role}.md"
        )
        return prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
```

**Reflect-phase placeholder writer (D-09)** — analog: `ralph_loop_plugin.py::_on_exit` for handler shape; analog for atomic write: `clawteam/fileutil.py::file_locked` + `atomic_write_text`.

```python
def _on_phase_transition(self, event) -> None:
    if event.to_phase != "reflect":
        return
    from clawteam.team.models import get_data_dir
    from clawteam.fileutil import atomic_write_text, file_locked
    import json

    stub_dir = (
        get_data_dir() / "teams" / event.team_name
        / "_phase6_pending"
    )
    stub_dir.mkdir(parents=True, exist_ok=True)
    stub_path = stub_dir / f"{event.sprint_id}-retro.json"
    payload = {
        "feature_flag": "phase6_learn_pending",
        "team": event.team_name,
        "sprint_id": event.sprint_id,
        "from_phase": event.from_phase,
        "to_phase": event.to_phase,
        "retro_body": "",   # filled by Reflect-phase agents before this fires
        "personas": [],
    }
    with file_locked(stub_path):
        atomic_write_text(stub_path, json.dumps(payload, indent=2))
```

**What differs from `ralph_loop_plugin.py`:** GstackSprintPlugin overrides 5 hooks (`on_register`, `contribute_phases`, `contribute_phase_roles`, `contribute_evidence_schemas`, `contribute_prompts`) where Ralph overrides only `on_register`. Same convention, larger surface. Stays at ~250 LOC by deferring all rubric content to the .md files and all schema definitions to `templates/gstack/schemas/`.

**Plugin loaded only when `gstack` template is selected (Pitfall 14 mitigation)** — verified by `clawteam/plugins/manager.py:139-167` `_instantiate_and_register`; the plugin must NOT be loaded at import time for non-gstack templates. The discipline is: registration happens inside `on_register(ctx)`, not at module-import.

---

### NEW: `tests/test_gstack_template.py` (TOML loader unit tests)

**Analog:** `tests/test_templates.py` (full file, 197 lines)

**Test class pattern** (`test_templates.py` lines 67-103):
```python
class TestLoadBuiltinTemplate:
    def test_load_hedge_fund(self):
        tmpl = load_template("hedge-fund")
        assert tmpl.name == "hedge-fund"
        assert tmpl.leader.name == "portfolio-manager"
        assert len(tmpl.agents) > 0
        assert len(tmpl.tasks) > 0

    def test_load_software_dev(self):
        tmpl = load_template("software-dev")
        assert tmpl.name == "software-dev"
        assert tmpl.leader.name == "tech-lead"
        assert len(tmpl.agents) == 4
        assert len(tmpl.tasks) == 5
```

**Test pattern to copy for gstack** — adapt the above to:
```python
class TestLoadGstackTemplate:
    def test_parses_via_existing_loader(self):
        tmpl = load_template("gstack")
        assert tmpl.name == "gstack"

    def test_eleven_agents_with_distinct_roles(self):
        tmpl = load_template("gstack")
        # Leader + 10 specialists = 11 total
        all_names = {tmpl.leader.name} | {a.name for a in tmpl.agents}
        assert len(all_names) == 11
        expected = {"ceo", "pm", "eng-mgr", "designer", "dx-lead", "engineer",
                    "reviewer", "qa", "security", "shipper", "sre"}
        assert all_names == expected

    def test_no_starter_tasks(self):
        # D-04: gstack waits for /sprint start; no [[template.tasks]] rows
        assert load_template("gstack").tasks == []

    def test_leader_role_field(self):
        tmpl = load_template("gstack")
        assert tmpl.leader_role == "ceo"

    def test_phases_field(self):
        assert load_template("gstack").phases == [
            "think", "plan", "build", "review", "test", "ship", "reflect"
        ]

    def test_model_profile_defaults_to_balanced(self):
        # TEAM-05 verification
        ...
```

**What differs:** `test_eleven_agents_with_distinct_roles` (vs `test_load_software_dev`'s `len(...) == 4`); new fields (`leader_role`, `phases`, `model_profile`, `memory`) require new assertions; `tasks == []` is the inversion of every existing template test.

---

### NEW: `tests/test_gstack_plugin.py` (plugin registration + Reflect handler)

**Analog:** `tests/test_plugin_hooks.py` (145 lines)

**Test fixture pattern** (`test_plugin_hooks.py` lines 23-60):
```python
class _GstackLikePlugin(HarnessPlugin):
    name = "gstack-like"

    def on_register(self, ctx):
        pass

    def contribute_phases(self):
        return ["alpha", "beta"]

    def contribute_phase_roles(self):
        return {"alpha": ["pm"]}


def test_plugin_manager_populates_registry_on_register():
    reset_registry()
    try:
        pm = PluginManager()
        pm._instantiate_and_register(_GstackLikePlugin)
        assert get_registry().ordered_names() == ["alpha", "beta"]
        assert get_registry().phase_roles() == {"alpha": ["pm"]}
    finally:
        reset_registry()
```

**Tests to copy for GstackSprintPlugin:**
1. `test_seven_phases_registered_in_order` — assert `get_registry().ordered_names() == GSTACK_PHASES`.
2. `test_phase_roles_complete` — assert phase_roles dict matches the 7×N expected mapping.
3. `test_six_evidence_schemas_registered` — instantiate plugin, call `_instantiate_and_register`, then `evidence_schemas.get_schema("design-doc")` returns `DesignDoc`, etc.
4. `test_only_ceo_advances_phase` (TEAM-04) — instantiate `SprintConductor`, call `advance_phase(sprint_id, actor="engineer")`, expect rejection; `actor="ceo"` succeeds.
5. `test_reflect_phase_learn_stub_writes_placeholder` (SPRINT-06) — emit `PhaseTransition(to_phase="reflect")`, assert `~/.clawteam/teams/<name>/_phase6_pending/<sprint_id>-retro.json` exists with `feature_flag: "phase6_learn_pending"`.

**Setup/teardown reset pattern** (`test_evidence_schemas.py` lines 38-43):
```python
def setup_function() -> None:
    reset_registry()

def teardown_function() -> None:
    reset_registry()
```

**What differs:** Tests instantiate the real `GstackSprintPlugin`, not a fake. Must reset both `phase_registry` AND `evidence_schemas` registries between tests.

---

### NEW: `tests/test_gstack_role_prompts.py` (golden grep tests)

**Analog:** `tests/test_evidence_schemas.py` (fixture-driven base test pattern, but no in-repo grep test exists). Closest parallel for "assert presence in committed file" is `tests/test_templates.py` lines 130-146 (assertion against template task content via Python `in` checks).

**Greppable-presence pattern** (`test_templates.py` lines 130-146):
```python
def test_strategy_room_specialists_route_to_decision_editor(self):
    tmpl = load_template("strategy-room")
    for agent in tmpl.agents:
        if agent.name == "decision-editor":
            continue
        assert "decision-editor" in agent.task
        assert "strategy-lead" not in agent.task
```

**Copy-target pattern for golden grep tests** — read both upstream fixture and ported prompt, assert content substrings:
```python
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "clawteam" / "templates" / "gstack" / "prompts"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "gstack_skills"

def test_pm_office_hours_rubric():
    upstream = (FIXTURES_DIR / "office-hours.md").read_text()
    ported   = (PROMPTS_DIR / "pm.md").read_text()

    # SIGNATURE line is the load-bearing assertion
    assert "SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1" in ported

    # INTERACTIVE-DEFERRED meta-instruction (Pitfall 7)
    assert "INTERACTIVE-RUNTIME-DEFERRED:" in ported

    # All 6 forcing questions present in BOTH
    for question_marker in ["Why now?", "Who is the user", "smallest version",
                            "alternative we're rejecting", "one metric",
                            "dumbest version"]:
        assert question_marker in upstream
        assert question_marker in ported

def test_security_cso_seventeen_exclusions():
    upstream = (FIXTURES_DIR / "cso.md").read_text()
    ported   = (PROMPTS_DIR / "security.md").read_text()
    assert "SIGNATURE: gstack-role:security rubric:cso envelope-version:1" in ported
    # 17 false-positive exclusions verbatim per D-13
    ...

def test_role_prompt_size_budget():
    """D-14: every prompt ≤ 4 KB; average ≤ 3 KB."""
    sizes = {p.name: p.stat().st_size for p in PROMPTS_DIR.glob("*.md")}
    for name, size in sizes.items():
        assert size <= 4096, f"{name} = {size} bytes (cap 4096)"
    avg = sum(sizes.values()) / len(sizes)
    assert avg <= 3072, f"average = {avg} bytes (cap 3072)"
```

**What differs:** Golden tests grep the real ported file AND the upstream fixture. The "Per-Role Prompt Content Map" rows in RESEARCH.md lines 728-740 are the source-of-truth list per role.

---

### NEW: `tests/test_envelope_personas.py` (per-persona pydantic tests)

**Analog:** `tests/test_turn_envelope.py` (127 lines, full file)

**Required-field rejection pattern** (`test_turn_envelope.py` lines 27-54):
```python
def test_turn_envelope_required_fields_present():
    env = TurnEnvelope(persona="engineer", step_label="build:1/3", done=False)
    assert env.persona == "engineer"
    assert env.step_label == "build:1/3"
    assert env.done is False

def test_turn_envelope_rejects_missing_persona():
    with pytest.raises(ValidationError) as exc_info:
        TurnEnvelope(step_label="x", done=False)  # type: ignore[call-arg]
    assert "persona" in str(exc_info.value).lower()
```

**Frontmatter round-trip pattern** (`test_turn_envelope.py` lines 75-87):
```python
def test_parse_frontmatter_valid():
    raw = (
        "---\n"
        "persona: engineer\n"
        "step_label: build:1/3\n"
        "done: false\n"
        "---\n"
        "body text\n"
    )
    meta, body = parse_frontmatter(raw)
    assert meta == {"persona": "engineer", "step_label": "build:1/3", "done": False}
    assert body == "body text\n"
```

**Tests to add for envelope_personas.py:**
1. Per-subclass instantiation success (e.g., `PMEnvelope(persona="pm", step_label="think:1/6", done=False, **{"pm.challenge": "Why three months?"})` succeeds).
2. Per-subclass rejection when persona-mandated field missing (e.g., `PMEnvelope` without `pm.challenge` raises ValidationError).
3. Discriminated-union dispatch: pass `meta` with `persona: "ceo"` → returns `CEOEnvelope` instance; pass `persona: "pm"` → returns `PMEnvelope`.
4. Stub-grade rejection: `pm_challenge="x"` (under min_length=20) raises ValidationError.
5. Alias resolution: `pm.challenge` (alias) and `pm_challenge` (Python name) both populate the field.

**What differs:** 11 personas means 11× the test surface. Use `@pytest.mark.parametrize` with a list of `(SubclassType, required_field_name, valid_value, stub_value)` tuples to keep test count manageable.

---

### NEW: `tests/test_gstack_team_spawn.py` (integration test)

**Analog:** `tests/test_template_regression_matrix.py` (full file, 123 lines)

**RecordingBackend pattern** (`test_template_regression_matrix.py` lines 27-39):
```python
class RecordingBackend:
    """Capture spawn calls without starting real subprocesses."""

    def __init__(self):
        self.calls = []

    def spawn(self, **kwargs):
        self.calls.append(kwargs)
        return f"Agent '{kwargs['agent_name']}' spawned"

    def list_running(self):
        return []
```

**Launch-flow assertion pattern** (`test_template_regression_matrix.py` lines 42-83):
```python
def test_template_launches_cleanly(template, monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    team_name = f"bc-matrix-{template}"
    result = runner.invoke(
        app,
        ["launch", template, "--team", team_name, "--goal", "BC regression smoke goal"],
        env={"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")},
    )

    assert result.exit_code == 0
    assert backend.calls

    for call in backend.calls:
        assert call.get("agent_name")
        assert call.get("team_name") == team_name
```

**Tests to add:**
1. `test_eleven_worktrees_created` (TEAM-03) — invoke `clawteam launch gstack --workspace`, assert WorkspaceManager.create_workspace called 11×.
2. `test_team_spawn_gstack` (UX-01) — full end-to-end via `clawteam launch gstack --team <name>`; assert 11 agents in `backend.calls`; assert per-role memory dirs exist at `~/.clawteam/teams/<name>/memory/<role>/` (D-05).
3. `test_software_dev_unaffected_by_gstack_plugin` (cross-template isolation) — launch `software-dev`, assert `evidence_schemas.list_registered() == []` (no gstack schemas registered).

**What differs:** 11-agent assertion (vs 4-5 in existing templates); per-role memory directory verification (D-05); model_profile inheritance verification (TEAM-05).

---

### NEW: `tests/fixtures/gstack_skills/<skill>.md` × 11 (committed WebFetch fixtures)

**Analog:** `tests/fixtures/qa/answer_freeform.md` (markdown fixture committed for test reproducibility)

**Layout pattern** (`tests/fixtures/qa/answer_freeform.md`, 6 lines):
```markdown
---
question_id: bbbbbbbb
answered_at: 2026-04-16T10:50:00Z
---

Reduce sprint scope to the toggle + persistence only. Defer the animation.
```

**What to copy:** the `tests/fixtures/<topic>/<file>.md` directory layout. Each file is plain markdown checked into git for reproducibility.

**What differs:** No frontmatter needed — these are public upstream gstack skill markdown files fetched verbatim via WebFetch in the Wave-0 `golden-trace-prep` task per D-08. Files to fetch (D-13):
- `office-hours.md`, `plan-ceo-review.md`, `plan-eng-review.md`, `retro.md`, `plan-design-review.md`, `design-review.md`, `plan-devex-review.md`, `devex-review.md`, `review.md`, `qa-only.md`, `cso.md`

Total: 11 files. They are NOT gitignored (D-13 explicitly: "committed to repo for reproducibility").

---

### NEW: `tests/fixtures/gstack_artifacts/` (pydantic round-trip fixtures)

**Analog:** `tests/fixtures/qa/*.md` (frontmatter shape) + `tests/test_evidence_schemas.py` (round-trip pattern)

**Frontmatter pattern** (`tests/fixtures/qa/answer_freeform.md`):
```markdown
---
question_id: bbbbbbbb
answered_at: 2026-04-16T10:50:00Z
---

<body>
```

**Round-trip test pattern** (`test_evidence_schemas.py` lines 46-71):
```python
def test_artifact_frontmatter_base_fields() -> None:
    env = ArtifactFrontmatterBase(
        persona="engineer",
        step_label="build:1/3",
        done=False,
        artifact_type="x",
        created_at="2026-04-17T00:00:00Z",
    )
    assert env.persona == "engineer"
    ...

def test_artifact_frontmatter_base_rejects_missing_persona() -> None:
    with pytest.raises(ValidationError):
        ArtifactFrontmatterBase(
            step_label="x", done=False, artifact_type="y", created_at="..."
        )
```

**Files to populate (per CONTEXT.md "Specific Ideas"):**
- `tests/fixtures/gstack_artifacts/design-doc-valid.md` — passes DesignDoc validation.
- `tests/fixtures/gstack_artifacts/design-doc-stub-tbd.md` — sections present, body "TBD" → MUST FAIL EvidenceGate stub detection (per Pitfall 8 mitigation in RESEARCH.md line 359).
- Same valid+stub pair for plan-doc, test-report, review-report, ship-notes, retro = 12 files total.

**What differs from `qa/` fixtures:** gstack_artifacts files use full TurnEnvelope + artifact_type frontmatter (5 fields minimum) instead of qa-fixture's 2-field frontmatter.

---

## Modification Patterns (existing files)

### MOD: `clawteam/templates/__init__.py` — extend TemplateDef + AgentDef

**Current `AgentDef`** (lines 24-28):
```python
class AgentDef(BaseModel):
    name: str
    type: str = "general-purpose"
    task: str = ""
    command: list[str] | None = None
```

**Current `TemplateDef`** (lines 37-44):
```python
class TemplateDef(BaseModel):
    name: str
    description: str = ""
    command: list[str] = ["claude"]
    backend: str = "tmux"
    leader: AgentDef
    agents: list[AgentDef] = []
    tasks: list[TaskDef] = []
```

**Extension to apply (Pattern 1 — strict additive)** — insert these optional fields with defaults:
```python
class AgentDef(BaseModel):
    name: str
    type: str = "general-purpose"
    task: str = ""
    command: list[str] | None = None
    role: str = ""                           # NEW (D-06): semantic role identifier
    prompt_file: str = ""                    # NEW (D-06): template-relative path to prompt .md
    model_profile: str = ""                  # NEW: per-agent model override; "" = inherit template default

class TemplateDef(BaseModel):
    name: str
    description: str = ""
    command: list[str] = ["claude"]
    backend: str = "tmux"
    leader: AgentDef
    agents: list[AgentDef] = []
    tasks: list[TaskDef] = []
    leader_role: str = ""                    # NEW (D-04, Pattern 4): role authorized to advance_phase
    phases: list[str] = []                   # NEW (D-04): plugin-contributed phase order; [] = use registry
    model_profile: dict[str, str] = {}       # NEW: per-role model assignments (e.g., {"pm": "opus"})
    memory: dict[str, str | bool] = {}       # NEW (D-05): {"root": "...", "per_role": True}
```

**Extension to `_parse_toml`** (current lines 75-100) — add reads for the new fields:
```python
def _parse_toml(path: Path) -> TemplateDef:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    tmpl = raw.get("template", {})
    leader_data = tmpl.get("leader", {})
    leader = AgentDef(**leader_data)
    agents = [AgentDef(**a) for a in tmpl.get("agents", [])]
    tasks = [TaskDef(**t) for t in tmpl.get("tasks", [])]
    return TemplateDef(
        name=tmpl.get("name", path.stem),
        description=tmpl.get("description", ""),
        command=tmpl.get("command", ["claude"]),
        backend=tmpl.get("backend", "tmux"),
        leader=leader,
        agents=agents,
        tasks=tasks,
        leader_role=tmpl.get("leader_role", ""),                     # NEW
        phases=tmpl.get("phases", []),                                # NEW
        model_profile=tmpl.get("model_profile", {}),                  # NEW
        memory=tmpl.get("memory", {}),                                # NEW
    )
```

**What differs / risk:** All new fields have defaults matching existing-template behavior (empty string / empty list / empty dict). Pydantic's `extra="ignore"` default (verified in CONTEXT.md A3) means existing 6 templates still parse. Zero breaking change.

---

### MOD: `clawteam/team/manager.py` — extend create_team with per-role memory dir creation

**Current `create_team`** (lines 77-112):
```python
@staticmethod
def create_team(
    name: str,
    leader_name: str,
    leader_id: str,
    description: str = "",
    user: str = "",
    leader_agent_type: str = "leader",
) -> TeamConfig:
    validate_identifier(name, "team name")
    validate_identifier(leader_name, "leader name")
    validate_identifier(user, "user name", allow_empty=True)
    if _config_path(name).exists():
        raise ValueError(f"Team '{name}' already exists")

    leader = TeamMember(
        name=leader_name,
        user=user,
        agent_id=leader_id,
        agent_type=leader_agent_type,
    )
    config = TeamConfig(
        name=name,
        description=description,
        lead_agent_id=leader_id,
        members=[leader],
    )
    _save_config(config)
    # Create inboxes dir and leader inbox
    inbox_name = TeamManager.inbox_name_for(leader)
    inbox = ensure_within_root(_team_dir(name) / "inboxes", inbox_name)
    inbox.mkdir(parents=True, exist_ok=True)
    # Create tasks dir
    tasks_dir = ensure_within_root(get_data_dir() / "tasks", name)
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return config
```

**Extension point:** After the existing `tasks_dir.mkdir(...)` call (line 111), before `return config`, insert per-role memory directory creation. The existing pattern uses `ensure_within_root` + `mkdir(parents=True, exist_ok=True)` — mirror it.

```python
# NEW (D-05): pre-create per-role memory dirs idempotently.
# Race-free: 11 mkdir calls during one-time spawn beats lazy-init under N parallel sprints × 11 agents.
roles: list[str] = kwargs.get("roles", [])  # planner picks: kwarg, list[AgentDef], or template object
for role in roles:
    role_id = validate_identifier(role, "role name")
    memory_dir = ensure_within_root(_team_dir(name) / "memory", role_id)
    memory_dir.mkdir(parents=True, exist_ok=True)
return config
```

**What differs / risk:** Adds one new kwarg with empty-list default → all existing call sites unaffected (the loop is a no-op when `roles=[]`). The `clawteam launch` flow (`commands.py` line 4058) is the new caller that passes the 11 gstack roles.

**Idempotency:** `mkdir(parents=True, exist_ok=True)` is the canonical idempotent dir-create idiom in this codebase (verified at `manager.py:108`, `:111`).

---

### MOD: `clawteam/sprint/conductor.py` — add `actor` parameter to advance_phase

**D-10 verification result:** Phase 2's `advance_phase(self, sprint_id: str)` (lines 304-332) does NOT accept an `actor` parameter. Phase 3 must add it.

**Current signature** (line 304):
```python
def advance_phase(self, sprint_id: str) -> tuple[bool, str]:
```

**Extension to apply (Pattern 4 — Leader-binding via actor check):**
```python
def advance_phase(
    self,
    sprint_id: str,
    actor: str = "",
) -> tuple[bool, str]:
    """Run the gate chain; on all-pass, flip current_phase; persist.

    Phase 3 D-10: ``actor`` defaults to "" so existing Phase 2 callers are
    unaffected. When the team's TemplateDef declares ``leader_role`` and
    ``actor`` is non-empty, advance is rejected unless ``actor == leader_role``.
    """
    with self._lock:
        state = self._load_by_id(sprint_id)

        # NEW (Pattern 4): leader-role enforcement
        if actor:
            from clawteam.team.manager import TeamManager
            tmpl = TeamManager.get_team(self.team_name)
            # Future: TeamConfig.leader_role added by separate plan task
            leader_role = getattr(tmpl, "leader_role", "") if tmpl else ""
            if leader_role and actor != leader_role:
                return False, f"actor {actor!r} not authorized; only {leader_role!r} can advance phases"

        gates = self._build_gate_chain(state)
        # ... rest unchanged
```

**What differs / risk:** Default empty-string preserves Phase 2 callers (`test_sprint_cli.py` etc.) where `actor` is unspecified. Only gstack-aware callers pass `actor=` explicitly. Plan should also extend `TeamConfig` (in `clawteam/team/models.py`) with an optional `leader_role: str = ""` field so the conductor can read it.

---

### MOD: `clawteam/cli/commands.py` — add `team show` dashboard

**D-12 verification result:** `team status` exists (`commands.py` lines 1611-1656) — it's the closest analog. There is no existing `team show` subcommand.

**Existing `team_status` skeleton** (`commands.py` lines 1611-1656):
```python
@team_app.command("status")
def team_status(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show team status and members."""
    from clawteam.team.manager import TeamManager

    config = TeamManager.get_team(team)
    if not config:
        _output({"error": f"Team '{team}' not found"}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    data = {
        "name": config.name,
        "description": config.description,
        "leadAgentId": config.lead_agent_id,
        "createdAt": config.created_at,
        "members": [m.model_dump(by_alias=True) for m in config.members],
    }

    def _human(d):
        console.print(f"\nTeam: [cyan]{d['name']}[/cyan]")
        if d['description']:
            console.print(f"  {d['description']}")
        console.print(f"  Created: {format_timestamp(d['createdAt'])}")
        table = Table(title="Members")
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Type")
        table.add_column("Joined", style="dim")
        for m in d["members"]:
            table.add_row(m.get("name", ""), m.get("agentId", ""), m.get("agentType", ""), format_timestamp(m.get("joinedAt")))
        console.print(table)

    _output(data, _human)
```

**Extension to apply:** Add a sibling `team show` command using the same shape, but enrich the data dict with sprint progress (read from `SprintConductor.list_sprints`), cost rollup placeholders (return `{"prompt_tokens": "—", "completion_tokens": "—"}` for now), memory dir presence (per D-05). Follow the `_output(data, _human)` two-surface pattern.

```python
@team_app.command("show")
def team_show(
    team: str = typer.Argument(..., help="Team name"),
):
    """Show team dashboard: members + active sprint + memory + cost rollup."""
    from clawteam.team.manager import TeamManager
    from clawteam.team.models import get_data_dir
    from clawteam.sprint.conductor import SprintConductor

    config = TeamManager.get_team(team)
    if not config:
        _output({"error": f"Team '{team}' not found"}, lambda d: console.print(f"[red]{d['error']}[/red]"))
        raise typer.Exit(1)

    # Sprint progress
    sprints = SprintConductor(team_name=team).list_sprints()
    active = [s for s in sprints if s.status == "running"]

    # Memory dir presence (D-05)
    memory_root = get_data_dir() / "teams" / team / "memory"
    memory_dirs = sorted([p.name for p in memory_root.iterdir()]) if memory_root.exists() else []

    data = {
        "name": config.name,
        "members": [m.model_dump(by_alias=True) for m in config.members],
        "active_sprint": (active[0].sprint_id if active else None),
        "phase": (active[0].current_phase if active else None),
        "memory_roles": memory_dirs,
        "cost_rollup": {"prompt_tokens": "—", "completion_tokens": "—"},  # Phase 7
    }

    def _human(d):
        # rich.Table for members, sprint progress row, etc.
        ...

    _output(data, _human)
```

**What differs / risk:** New command, no surface change. Reuses `_output`, `Table`, `format_timestamp`, `_team_dir` patterns already in this file. CONTEXT.md "Claude's Discretion" says planner can split this into one plan or per-column plans.

---

### MOD: `tests/test_template_regression_matrix.py` — add gstack to TEMPLATE_NAMES + cross-isolation test

**Current `TEMPLATE_NAMES`** (lines 17-24):
```python
TEMPLATE_NAMES: list[str] = [
    "software-dev",
    "hedge-fund",
    "code-review",
    "harness-default",
    "research-paper",
    "strategy-room",
]
```

**Extension:** Add `"gstack"` entry → all 7 templates now run through the parametrized `test_template_launches_cleanly` and `test_template_spawn_calls_preserve_skip_permissions_flag` matrix.

**Cross-template isolation test to add (Pitfall 14 mitigation):**
```python
@pytest.mark.parametrize("template", [
    "software-dev", "hedge-fund", "code-review",
    "harness-default", "research-paper", "strategy-room",
])
def test_non_gstack_templates_do_not_register_gstack_schemas(template, tmp_path, monkeypatch):
    """SC#7: non-gstack templates leave EvidenceSchemaRegistry empty."""
    from clawteam.harness.evidence_schemas import list_registered, reset_registry
    reset_registry()
    # Launch the non-gstack template via CliRunner...
    assert "design-doc" not in list_registered()
    assert "plan-doc" not in list_registered()
```

---

### MOD: `tests/test_evidence_schemas.py` — add 6 gstack schema round-trip tests

**Current registry-test pattern** (lines 73-107):
```python
def test_register_schema_adds_to_registry() -> None:
    register_schema("design-doc", DesignDocFixture)
    assert get_schema("design-doc") is DesignDocFixture

def test_register_schema_rejects_duplicate_name() -> None:
    register_schema("design-doc", DesignDocFixture)
    with pytest.raises(ValueError) as exc_info:
        register_schema("design-doc", PlanDocFixture)
    msg = str(exc_info.value)
    assert "design-doc" in msg
```

**Extension (option A: extend in place):** Add 6 round-trip tests using the real Phase 3 schemas:
```python
from clawteam.templates.gstack.schemas import (
    DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro
)

def test_design_doc_passes_with_full_content():
    doc = DesignDoc(
        artifact_type="design-doc",
        problem_statement="x" * 120,  # min_length=120
        users="y" * 50,
        constraints="z" * 50,
        rationale="w" * 120,
        pm_verdict="proceed",
        forcing_questions_addressed=[1, 2, 3, 4, 5, 6],
        sprint_id="abc12345",
        created_at="2026-04-20T00:00:00Z",
    )
    assert doc.artifact_type == "design-doc"

def test_design_doc_rejects_short_problem_statement():
    with pytest.raises(ValidationError):
        DesignDoc(
            artifact_type="design-doc",
            problem_statement="too short",  # < 120 chars (Pitfall 8)
            ...
        )
```

**Option B (recommended, cleaner):** Create new file `tests/test_gstack_evidence_schemas.py` mirroring `test_evidence_schemas.py` shape.

---

### MOD: `tests/test_cli_commands.py` — add team show dashboard test

**Current test pattern** (lines 309-326):
```python
def test_team_status_uses_configured_timezone(tmp_path):
    runner = CliRunner()
    env = {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }

    save_config(ClawTeamConfig(timezone="Asia/Shanghai"))
    TeamManager.create_team(
        name="demo",
        leader_name="leader",
        leader_id="leader001",
    )

    result = runner.invoke(app, ["team", "status", "demo"], env=env)

    assert result.exit_code == 0
    assert "CST" in result.output
```

**Extension to add:**
```python
def test_team_show_gstack_dashboard(tmp_path, monkeypatch):
    """UX-07: team show displays 11 members + sprint progress + memory + cost rollup."""
    runner = CliRunner()
    env = {"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")}

    # Launch gstack via existing path
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: RecordingBackend())
    runner.invoke(app, ["launch", "gstack", "--team", "demo", "--goal", "g"], env=env)

    result = runner.invoke(app, ["team", "show", "demo"], env=env)
    assert result.exit_code == 0
    # Assert 11 members + memory placeholders + sprint progress rendered
    assert "11" in result.output  # member count or roster size
    for role in ["pm", "ceo", "engineer", "shipper"]:
        assert role in result.output
```

---

## Shared Patterns (cross-cutting)

### Pattern A: Atomic file-locked persistence

**Source:** `clawteam/fileutil.py` lines 28-83 (`atomic_write_text`, `file_locked`)
**Apply to:** `gstack_sprint_plugin.py::_on_phase_transition` (Reflect placeholder writer); any future write to `~/.clawteam/teams/<name>/`.

```python
from clawteam.fileutil import atomic_write_text, file_locked

with file_locked(stub_path):
    atomic_write_text(stub_path, json.dumps(payload, indent=2))
```

**Why:** Phase 6 will run N parallel sprints × 11 agents writing to `_phase6_pending/` simultaneously (per CONTEXT.md D-05 rationale). Atomic + locked is the only race-safe write idiom in this codebase.

---

### Pattern B: Path safety via `ensure_within_root` + `validate_identifier`

**Source:** `clawteam/paths.py` (`ensure_within_root`, `validate_identifier`); usage at `clawteam/team/manager.py` lines 21, 107, 110
**Apply to:** all new write paths under `~/.clawteam/teams/<name>/` — the per-role memory dir creation in `TeamManager.create_team` extension; the `_phase6_pending/` placeholder writer; the `team show` dashboard's memory-dir read.

```python
from clawteam.paths import ensure_within_root, validate_identifier

memory_dir = ensure_within_root(_team_dir(name) / "memory", validate_identifier(role, "role name"))
memory_dir.mkdir(parents=True, exist_ok=True)
```

**Why:** Existing convention; prevents path traversal in user-supplied identifiers. NEVER concatenate paths directly.

---

### Pattern C: Test isolation via `reset_registry` setup/teardown

**Source:** `tests/test_evidence_schemas.py` lines 38-43; `tests/test_plugin_hooks.py` lines 53-60
**Apply to:** all new plugin/registry tests in Phase 3.

```python
def setup_function() -> None:
    reset_registry()

def teardown_function() -> None:
    reset_registry()
```

For tests touching multiple registries:
```python
from clawteam.harness.phase_registry import reset_registry as reset_phase_registry
from clawteam.harness.evidence_schemas import reset_registry as reset_evidence_registry

def setup_function():
    reset_phase_registry()
    reset_evidence_registry()
```

**Why:** Module-level singletons (`_REGISTRY`, `_REGISTERED`) leak across tests without explicit reset. Convention is consistent across all Phase 1/2 registry tests.

---

### Pattern D: Hermetic test environment via monkeypatch

**Source:** `tests/conftest.py` lines 10-19 (`isolated_data_dir` autouse fixture); `tests/test_sprint_cli.py` lines 21-39 (`clean_env` fixture)
**Apply to:** all new integration tests that touch `~/.clawteam/`.

```python
@pytest.fixture
def clean_env(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CLAWTEAM_TEAM", raising=False)
    monkeypatch.delenv("OH_TEAM", raising=False)
    # Reset freeze + safety subscribers per test
    from clawteam.harness.freeze_registry import reset_freeze_registry, reset_safety_subscribers
    reset_freeze_registry()
    reset_safety_subscribers()
    yield tmp_path
    reset_freeze_registry()
    reset_safety_subscribers()
```

**Why:** Tests must never touch the real `~/.clawteam`. The `conftest.py` autouse fixture handles `CLAWTEAM_DATA_DIR` + `HOME` redirection globally; sprint/plugin tests add registry resets on top.

---

### Pattern E: Output two-surface (`_output(data, _human)`)

**Source:** `clawteam/cli/commands.py` lines 1620, 1631-1654 (`team status`); pattern repeats throughout `commands.py`
**Apply to:** the new `team show` command and any other CLI extensions.

```python
data = {...}
def _human(d):
    console.print(...)
_output(data, _human)
```

**Why:** Every CLI command supports `--json` and human-readable surfaces via the same dispatch helper. `_output` is a module-level helper that picks based on the global `_json_output` flag set in the `main` callback.

---

### Pattern F: Lazy-import inside method bodies

**Source:** ubiquitous — e.g., `clawteam/plugins/manager.py` lines 145, 159; `clawteam/sprint/conductor.py` lines 173, 191; `clawteam/plugins/ralph_loop_plugin.py` line 36
**Apply to:** all `gstack_sprint_plugin.py` cross-module imports.

```python
def on_register(self, ctx: HarnessContext) -> None:
    from clawteam.events.types import PhaseTransition  # lazy
    ctx.bus.subscribe(PhaseTransition, self._on_phase_transition)
```

**Why:** Phase 1/2 use lazy imports inside methods (not at module top) to (a) tolerate wave-parallel module landings, (b) avoid circular imports, (c) speed cold-start. The `TYPE_CHECKING` block at module top covers type annotations only.

---

## No Analog Found

| File | Role | Data Flow | Reason / Closest Reference |
|------|------|-----------|----------------------------|
| `clawteam/templates/gstack/prompts/<role>.md` × 11 | prompt asset | static-reference | No standalone agent system-prompt files exist in repo. Closest is the inline `task = """..."""` prose blocks in template TOMLs (`software-dev.toml` line 10) — use as tone reference only. Format is greenfield; copy from RESEARCH.md §"Role prompt skeleton" lines 447-517. |
| `tests/fixtures/gstack_skills/<skill>.md` × 11 | committed test fixture | WebFetched static markdown | No existing in-repo fixture is a WebFetched upstream-content mirror. Closest layout: `tests/fixtures/qa/*.md`. Content is greenfield (public upstream gstack markdown — fetch verbatim per D-13). |

---

## Phase Invariant Verification (delete-test)

**Per CONTEXT.md §domain "Delete invariant":** Removing these three locations must leave the rest of the codebase running unchanged:
1. `clawteam/plugins/gstack_sprint_plugin.py`
2. `clawteam/templates/gstack.toml`
3. `clawteam/templates/gstack/` (entire subtree)

**How patterns above honor the invariant:**

| Pattern | Honors invariant by... |
|---------|------------------------|
| Per-persona envelope subclasses live at `clawteam/templates/gstack/envelope_personas.py` (not `clawteam/team/`) | All 11 subclasses removed when directory is deleted (D-07) |
| Six pydantic schemas live at `clawteam/templates/gstack/schemas/` | All 6 schemas removed when directory is deleted |
| Plugin registers schemas inside `on_register(ctx)`, not at module-import time (Pitfall 14) | Importing `clawteam.plugins.gstack_sprint_plugin` for any reason is a no-op for global state |
| `TemplateDef`/`AgentDef` extension fields all have empty defaults | Existing 6 templates parse identically without gstack present |
| `advance_phase(actor="")` defaults to no enforcement | Phase 2 callers unaffected when `leader_role` is absent on the team |

**Verification test to add (planner-owned):**
```python
def test_delete_invariant_substrate_still_runs(tmp_path, monkeypatch):
    """Simulate the three-location deletion — assert non-gstack templates still launch."""
    # Skip if gstack files are absent (in real delete-invariant audit).
    # Otherwise: launch each of the 6 non-gstack templates; assert exit 0.
    ...
```

---

## Metadata

**Analog search scope:**
- `clawteam/templates/` (8 files: 7 TOMLs + `__init__.py`)
- `clawteam/plugins/` (4 files: `base.py`, `manager.py`, `ralph_loop_plugin.py`, `__init__.py`)
- `clawteam/team/` (`envelope.py`, `manager.py`, `models.py`)
- `clawteam/sprint/` (`conductor.py`)
- `clawteam/harness/` (`evidence_schemas.py`, `evidence_gate.py`, `phases.py`, `phase_registry.py`)
- `clawteam/cli/commands.py` (5,158 lines — Grep + targeted Read)
- `clawteam/spawn/__init__.py`
- `clawteam/workspace/manager.py`
- `clawteam/fileutil.py`
- `tests/` (8 files: `conftest.py`, `test_templates.py`, `test_template_regression_matrix.py`, `test_turn_envelope.py`, `test_plugin_hooks.py`, `test_evidence_schemas.py`, `test_cli_commands.py`, `test_sprint_cli.py`)
- `tests/fixtures/qa/`

**Files scanned:** ≈40 files across 11 directories.
**Pattern extraction date:** 2026-04-20

**Key patterns identified:**
1. **Strict additive pydantic extension with empty defaults** is the established backwards-compat idiom (Pattern 1; verified via `evidence="ignore"` default + Phase 1/2 hook bases).
2. **Single cohesive plugin file overriding only needed hooks** is the in-repo convention (`ralph_loop_plugin.py` is the canonical reference).
3. **Module-level singleton registry + `reset_registry()` test helper** is the lifecycle pattern shared by `phase_registry`, `evidence_schemas`, `freeze_registry`.
4. **Lazy imports inside method bodies + `TYPE_CHECKING` block at module top** is the universal cross-module reference pattern.
5. **`_output(data, _human)` two-surface dispatch** is the universal CLI output convention.
6. **`ensure_within_root` + `validate_identifier`** is the universal path-safety convention for `~/.clawteam/teams/<name>/` writes.
7. **Atomic-write + file-lock** (`atomic_write_text` + `file_locked`) is the universal multi-process write idiom.
8. **`isolated_data_dir` autouse fixture + `reset_*_registry()` per-test** is the universal test isolation idiom.
