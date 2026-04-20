---
phase: 03-gstack-team-template-methodology-port
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - clawteam/sprint/conductor.py
  - clawteam/team/models.py
  - tests/fixtures/gstack_skills/office-hours.md
  - tests/fixtures/gstack_skills/plan-ceo-review.md
  - tests/fixtures/gstack_skills/plan-eng-review.md
  - tests/fixtures/gstack_skills/retro.md
  - tests/fixtures/gstack_skills/plan-design-review.md
  - tests/fixtures/gstack_skills/design-review.md
  - tests/fixtures/gstack_skills/plan-devex-review.md
  - tests/fixtures/gstack_skills/devex-review.md
  - tests/fixtures/gstack_skills/review.md
  - tests/fixtures/gstack_skills/qa-only.md
  - tests/fixtures/gstack_skills/cso.md
  - tests/test_gstack_template.py
  - tests/test_gstack_plugin.py
  - tests/test_gstack_role_prompts.py
  - tests/test_envelope_personas.py
  - tests/test_gstack_team_spawn.py
autonomous: true
requirements: [TEAM-04, TEAM-01, TEAM-02, TEAM-03, TEAM-05, SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06, SKILL-07, SKILL-08, SPRINT-06, UX-01, UX-07]
must_haves:
  truths:
    - "All 11 upstream gstack skill markdown files are committed under tests/fixtures/gstack_skills/ for reproducible golden tests"
    - "SprintConductor.advance_phase accepts an optional actor parameter without breaking Phase 2 callers"
    - "TeamConfig pydantic model carries optional leader_role + template fields readable by SprintConductor and GstackSprintPlugin"
    - "All five new test files exist with skipped/xfail stubs so subsequent waves have automated verification per Nyquist"
  artifacts:
    - path: "tests/fixtures/gstack_skills/office-hours.md"
      provides: "Upstream /office-hours skill markdown for golden grep against pm.md"
      contains: "Why now?"
    - path: "tests/fixtures/gstack_skills/cso.md"
      provides: "Upstream /cso skill markdown for golden grep against security.md"
      contains: "false positive"
    - path: "clawteam/sprint/conductor.py"
      provides: "advance_phase(self, sprint_id: str, actor: str = '') with leader-role enforcement"
      contains: "actor: str = \"\""
    - path: "clawteam/team/models.py"
      provides: "TeamConfig.leader_role + TeamConfig.template optional fields"
      contains: "leader_role"
      contains_template: "template: str = \"\""
    - path: "tests/test_gstack_template.py"
      provides: "Test scaffold for TEAM-01/02/05 (xfail until Wave 1 ships)"
      contains: "test_parses_via_existing_loader"
    - path: "tests/test_gstack_plugin.py"
      provides: "Test scaffold for TEAM-04, SPRINT-06"
      contains: "test_only_ceo_advances_phase"
    - path: "tests/test_gstack_role_prompts.py"
      provides: "Test scaffold for SKILL-01..08 + D-14 budget gate"
      contains: "test_role_prompt_size_budget"
    - path: "tests/test_envelope_personas.py"
      provides: "Test scaffold for D-07 per-persona envelope subclasses"
      contains: "PMEnvelope"
    - path: "tests/test_gstack_team_spawn.py"
      provides: "Test scaffold for TEAM-03, UX-01"
      contains: "test_eleven_worktrees_created"
  key_links:
    - from: "clawteam/sprint/conductor.py"
      to: "TeamConfig.leader_role"
      via: "getattr(tmpl, 'leader_role', '') consulted in advance_phase"
      pattern: "leader_role"
    - from: "tests/test_gstack_role_prompts.py"
      to: "tests/fixtures/gstack_skills/"
      via: "Path(__file__).parent / 'fixtures' / 'gstack_skills'"
      pattern: "fixtures/gstack_skills"
---

<objective>
Wave 0 substrate prep: WebFetch the 11 upstream gstack skill markdown files into `tests/fixtures/gstack_skills/`, add the `actor: str = ""` parameter to `SprintConductor.advance_phase` (D-10 verified absent in Phase 2), add `leader_role: str = ""` to `TeamConfig`, and create the five new test files as skipped/xfail stubs so Waves 1-4 have automated verification per the Nyquist rule.

Purpose: Eliminate the five A1-A8 unverified assumptions before any implementation file is touched. Make every subsequent wave's `<verify>` block point to a real (currently-skipped) pytest.

Output:
- 11 upstream markdown fixtures committed (Strategy B per D-08)
- SprintConductor signature additively extended (D-10)
- TeamConfig extended with optional leader_role (Pattern 4 prerequisite) AND optional template field (03-07 Reflect-handler key_link prerequisite)
- 5 test files scaffolded with imports + skipped tests so green suite stays green
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

<interfaces>
<!-- Key contracts the executor needs. Extracted from PATTERNS.md analog reads. -->

From clawteam/sprint/conductor.py (Phase 2, line 304 — D-10 confirms actor absent):
```python
def advance_phase(self, sprint_id: str) -> tuple[bool, str]:
    """Phase 2 signature — Wave 0 extends with actor: str = '' (additive)."""
    with self._lock:
        state = self._load_by_id(sprint_id)
        gates = self._build_gate_chain(state)
        # ... gate evaluation, state mutation, persistence
```

From clawteam/team/models.py (TeamConfig pydantic model — extend additively):
```python
class TeamConfig(BaseModel):
    name: str
    description: str = ""
    lead_agent_id: str
    members: list[TeamMember] = []
    # NEW (Wave 0): leader_role: str = ""  per Pattern 4 prerequisite
```

From tests/conftest.py (autouse `isolated_data_dir` fixture):
```python
@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
    monkeypatch.setenv("HOME", str(tmp_path))
```

From tests/test_evidence_schemas.py (registry reset pattern):
```python
def setup_function() -> None:
    reset_registry()

def teardown_function() -> None:
    reset_registry()
```

Upstream gstack skill files to WebFetch (D-08, D-13):
- https://github.com/garrytan/gstack/blob/main/office-hours/SKILL.md  (or root file — try both paths)
- https://github.com/garrytan/gstack/blob/main/plan-ceo-review/SKILL.md
- https://github.com/garrytan/gstack/blob/main/plan-eng-review/SKILL.md
- https://github.com/garrytan/gstack/blob/main/retro/SKILL.md
- https://github.com/garrytan/gstack/blob/main/plan-design-review/SKILL.md
- https://github.com/garrytan/gstack/blob/main/design-review/SKILL.md
- https://github.com/garrytan/gstack/blob/main/plan-devex-review/SKILL.md
- https://github.com/garrytan/gstack/blob/main/devex-review/SKILL.md
- https://github.com/garrytan/gstack/blob/main/review/SKILL.md
- https://github.com/garrytan/gstack/blob/main/qa-only/SKILL.md
- https://github.com/garrytan/gstack/blob/main/cso/SKILL.md

If any URL returns 404, the executor must explore the gstack repo via `gh api repos/garrytan/gstack/contents/<skill-dir>` to discover the actual filename (could be `README.md`, `<skill>.md`, etc.) and re-fetch.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: WebFetch and commit 11 upstream gstack skill fixtures (D-08, D-13)</name>
  <files>tests/fixtures/gstack_skills/office-hours.md, tests/fixtures/gstack_skills/plan-ceo-review.md, tests/fixtures/gstack_skills/plan-eng-review.md, tests/fixtures/gstack_skills/retro.md, tests/fixtures/gstack_skills/plan-design-review.md, tests/fixtures/gstack_skills/design-review.md, tests/fixtures/gstack_skills/plan-devex-review.md, tests/fixtures/gstack_skills/devex-review.md, tests/fixtures/gstack_skills/review.md, tests/fixtures/gstack_skills/qa-only.md, tests/fixtures/gstack_skills/cso.md</files>
  <read_first>
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-08 Strategy B; D-13 verbatim 17 exclusions / 6 questions / 10 dimensions)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (No Analog Found section — fixture layout)
    - tests/fixtures/qa/answer_freeform.md (existing fixture format reference)
  </read_first>
  <action>
For each of the 11 upstream gstack skills, discover the canonical SKILL.md (or equivalent) file in https://github.com/garrytan/gstack and store the verbatim content under `tests/fixtures/gstack_skills/<skill-name>.md`.

**Discovery procedure (per skill):**
1. Try `gh api repos/garrytan/gstack/contents/<skill-name> --jq '.[].name'` to list files in the skill directory.
2. Identify the canonical markdown file (typically `SKILL.md`, `README.md`, or `<skill-name>.md`).
3. Fetch raw content: `gh api repos/garrytan/gstack/contents/<skill-name>/SKILL.md --jq '.content' | base64 -d > tests/fixtures/gstack_skills/<skill-name>.md` (substitute the actual filename discovered in step 2).
4. If the gh CLI is unavailable or the repo is private/moved, fall back to WebFetch on `https://raw.githubusercontent.com/garrytan/gstack/main/<skill-name>/SKILL.md` (substitute discovered filename).

**The 11 skill names (exact directory names to discover):**
office-hours, plan-ceo-review, plan-eng-review, retro, plan-design-review, design-review, plan-devex-review, devex-review, review, qa-only, cso

**Mandatory verbatim content checks (D-13 — extract these counts during fetch and record in commit message body):**
- `office-hours.md` MUST contain 6 forcing questions. Look for question-shaped lines (interrogative, numbered or bulleted). Note the verbatim text of each in the commit message body so Wave 2 can grep them.
- `plan-design-review.md` MUST contain 10 rubric dimensions. Extract the verbatim dimension names.
- `cso.md` MUST contain 17 false-positive exclusions. Extract the verbatim list.

If any of these counts differs from the expected (6 / 10 / 17), record the actual count in the commit message and add a `# CONTENT-DRIFT-NOTE:` line at the top of the affected fixture file so Wave 2 knows to adjust prompt content (per CONTEXT.md D-13 "If absent: planner adjusts security.md / pm.md / designer.md content to match actual upstream").

**Files are checked in (NOT gitignored)** per D-13: "committed to repo for reproducibility — these are public files."
  </action>
  <verify>
    <automated>test -d tests/fixtures/gstack_skills && ls tests/fixtures/gstack_skills/*.md | wc -l | grep -q '^11$' && grep -q 'Why now' tests/fixtures/gstack_skills/office-hours.md && grep -ic 'false positive' tests/fixtures/gstack_skills/cso.md | awk '$1 >= 1'</automated>
  </verify>
  <acceptance_criteria>
    - `ls tests/fixtures/gstack_skills/*.md | wc -l` outputs `11`
    - `grep -l 'Why now' tests/fixtures/gstack_skills/office-hours.md` exits 0
    - `grep -c -i 'false positive' tests/fixtures/gstack_skills/cso.md` outputs a number `>= 1` (the upstream phrasing — exact count of exclusions extracted into commit message)
    - `git ls-files tests/fixtures/gstack_skills/` lists all 11 .md files (NOT gitignored)
    - Commit message body lists: (a) the verbatim 6 forcing questions from office-hours.md, (b) the verbatim 10 rubric dimensions from plan-design-review.md, (c) the verbatim 17 (or actual N) false-positive exclusions from cso.md, OR a `# CONTENT-DRIFT-NOTE:` line is present in the affected fixture file
  </acceptance_criteria>
  <done>11 fixture .md files exist + are git-tracked; D-13 counts (6/10/17 or documented drift) are captured for Wave 2 use.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add actor parameter to SprintConductor.advance_phase + leader_role to TeamConfig (D-10, Pattern 4)</name>
  <files>clawteam/sprint/conductor.py, clawteam/team/models.py, tests/test_sprint_conductor.py (extend if exists, else add)</files>
  <read_first>
    - clawteam/sprint/conductor.py (lines 290-340 — current advance_phase signature and body)
    - clawteam/team/models.py (current TeamConfig pydantic model)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 914-952 — exact extension snippet)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-10 outcome: param absent in Phase 2 — additive 1-line change)
    - tests/test_sprint_conductor.py or tests/test_phase2_integration.py (Phase 2 callers — confirm none pass actor=)
  </read_first>
  <behavior>
    - Test 1: Calling `advance_phase(sprint_id, actor="")` (or omitted) preserves existing Phase 2 behavior — gate chain runs as before.
    - Test 2: Calling `advance_phase(sprint_id, actor="ceo")` on a team with `leader_role="ceo"` succeeds (gate chain runs).
    - Test 3: Calling `advance_phase(sprint_id, actor="engineer")` on a team with `leader_role="ceo"` returns `(False, "actor 'engineer' not authorized; only 'ceo' can advance phases")`.
    - Test 4: Calling `advance_phase(sprint_id, actor="anyone")` on a team with `leader_role=""` (no leader binding) preserves Phase 2 behavior — actor is ignored.
    - Test 5: `TeamConfig(name="x", lead_agent_id="y", members=[]).leader_role == ""` — default empty preserves BC.
    - Test 6: `TeamConfig(name="x", lead_agent_id="y", members=[], leader_role="ceo").leader_role == "ceo"` — field accepts assignment.
  </behavior>
  <action>
**File 1 — `clawteam/team/models.py`:** Locate the `TeamConfig(BaseModel)` declaration. Add TWO optional fields after `members`:

```python
class TeamConfig(BaseModel):
    name: str
    description: str = ""
    lead_agent_id: str
    members: list[TeamMember] = []
    leader_role: str = ""  # NEW Phase 3 (Pattern 4): role authorized to advance_phase; "" = no leader binding
    template: str = ""     # NEW Phase 3 (03-07 key_link): template name (e.g. "gstack"); enables consumption-layer isolation in plugin event handlers
    # ... preserve all other existing fields verbatim
```

**Why both fields land in 03-01 Wave 0:** They are sister fields — both flow from `TemplateDef` into `TeamConfig` at `create_team` time, and both are read by Phase 3 substrate (conductor consults `leader_role`; `GstackSprintPlugin._on_phase_transition` consults `template`). Adding them together preserves the atomic-commit discipline and lets 03-02 wire both in one CLI patch (`leader_role=tmpl.leader_role, template=tmpl.name`).

**File 2 — `clawteam/sprint/conductor.py`:** Locate the `advance_phase(self, sprint_id: str)` method (currently at line 304 per PATTERNS.md verification). Apply this exact extension:

```python
def advance_phase(
    self,
    sprint_id: str,
    actor: str = "",
) -> tuple[bool, str]:
    """Run the gate chain; on all-pass, flip current_phase; persist.

    Phase 3 D-10: ``actor`` defaults to "" so existing Phase 2 callers are
    unaffected. When the team's TeamConfig declares ``leader_role`` and
    ``actor`` is non-empty, advance is rejected unless ``actor == leader_role``.
    """
    with self._lock:
        state = self._load_by_id(sprint_id)

        # NEW Phase 3 (Pattern 4): leader-role enforcement
        if actor:
            from clawteam.team.manager import TeamManager
            tmpl = TeamManager.get_team(self.team_name)
            leader_role = getattr(tmpl, "leader_role", "") if tmpl else ""
            if leader_role and actor != leader_role:
                return False, f"actor {actor!r} not authorized; only {leader_role!r} can advance phases"

        # ... rest of existing method body UNCHANGED (gates = self._build_gate_chain(state); etc.)
```

The lazy import inside the method body is intentional (Pattern F — lazy-import inside method bodies).

**File 3 — Tests:** Either extend `tests/test_sprint_conductor.py` (if exists) or create a new test module covering the 6 behaviors above. Use the standard hermetic-env pattern from `tests/conftest.py`'s `isolated_data_dir` autouse fixture. Use `TeamManager.create_team(...)` to seed a team with `leader_role="ceo"` (set the field on the persisted TeamConfig directly via `_save_config`).

**Atomic-commit discipline:** Commit File 1 + File 2 + tests as a SINGLE atomic commit titled `feat(03-01): add actor parameter to SprintConductor.advance_phase + leader_role to TeamConfig`. Per D-01 atomic-commit rule: all three files form one logical change.
  </action>
  <verify>
    <automated>pytest tests/test_sprint_conductor.py -x 2>/dev/null || pytest tests/ -k 'advance_phase' -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -E 'def advance_phase\(\s*self,\s*sprint_id: str,\s*actor: str = ""' clawteam/sprint/conductor.py` exits 0
    - `grep -E '^\s*leader_role: str = ""' clawteam/team/models.py` exits 0
    - `grep -E '^\s*template: str = ""' clawteam/team/models.py` exits 0
    - `python -c "from clawteam.team.models import TeamConfig; c = TeamConfig(name='t', lead_agent_id='a', members=[]); assert c.leader_role == '' and c.template == ''; c2 = TeamConfig(name='t', lead_agent_id='a', members=[], leader_role='ceo', template='gstack'); assert c2.leader_role == 'ceo' and c2.template == 'gstack'"` exits 0
    - `pytest tests/ -k 'advance_phase' -x` exits 0 (all 6 behavior tests pass)
    - `pytest tests/test_phase2_integration.py -x` exits 0 (Phase 2 regression preserved — actor="" default doesn't break callers)
  </acceptance_criteria>
  <done>SprintConductor.advance_phase accepts optional actor; TeamConfig has optional leader_role; all Phase 2 callers continue to pass; new behavior tests green.</done>
</task>

<task type="auto">
  <name>Task 3: Scaffold 5 new test files with skipped/xfail stubs (Nyquist Wave 0)</name>
  <files>tests/test_gstack_template.py, tests/test_gstack_plugin.py, tests/test_gstack_role_prompts.py, tests/test_envelope_personas.py, tests/test_gstack_team_spawn.py</files>
  <read_first>
    - tests/conftest.py (isolated_data_dir autouse fixture)
    - tests/test_templates.py (analog for test_gstack_template.py — TestLoadGstackTemplate class shape)
    - tests/test_plugin_hooks.py (analog for test_gstack_plugin.py — registry reset + plugin instantiation pattern)
    - tests/test_evidence_schemas.py (analog for test_gstack_role_prompts.py + setup_function/teardown_function pattern)
    - tests/test_turn_envelope.py (analog for test_envelope_personas.py — required-field rejection + frontmatter round-trip pattern)
    - tests/test_template_regression_matrix.py (analog for test_gstack_team_spawn.py — RecordingBackend + CliRunner.invoke pattern)
    - .planning/phases/03-gstack-team-template-methodology-port/03-VALIDATION.md (per-task verification map — exact pytest test IDs)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 439-705 — exact test patterns to copy)
  </read_first>
  <action>
Create five new test files. Each test starts with `pytest.skip("Wave N implementation pending — scaffold from Wave 0 plan 03-01")` (or `@pytest.mark.xfail(reason=...)`) so the suite stays green but the test IDs are real and discoverable. Subsequent waves remove the skip.

**File 1 — `tests/test_gstack_template.py`** (covers TEAM-01, TEAM-02, TEAM-05; gets unskipped by Wave 1):

```python
"""Wave 0 scaffold per 03-01-PLAN. Tests unskipped by Wave 1 (03-02-PLAN)."""
import pytest
from clawteam.templates import load_template

class TestLoadGstackTemplate:
    @pytest.mark.skip(reason="Wave 1: gstack.toml ships in 03-02-PLAN")
    def test_parses_via_existing_loader(self):
        tmpl = load_template("gstack")
        assert tmpl.name == "gstack"

    @pytest.mark.skip(reason="Wave 1")
    def test_eleven_agents_with_distinct_roles(self):
        tmpl = load_template("gstack")
        all_names = {tmpl.leader.name} | {a.name for a in tmpl.agents}
        assert len(all_names) == 11
        expected = {"ceo", "pm", "eng-mgr", "designer", "dx-lead", "engineer",
                    "reviewer", "qa", "security", "shipper", "sre"}
        assert all_names == expected

    @pytest.mark.skip(reason="Wave 1")
    def test_no_starter_tasks(self):
        # D-04: gstack waits for /sprint start
        assert load_template("gstack").tasks == []

    @pytest.mark.skip(reason="Wave 1")
    def test_leader_role_field(self):
        assert load_template("gstack").leader_role == "ceo"

    @pytest.mark.skip(reason="Wave 1")
    def test_phases_field(self):
        assert load_template("gstack").phases == [
            "think", "plan", "build", "review", "test", "ship", "reflect"
        ]

    @pytest.mark.skip(reason="Wave 1: TEAM-05")
    def test_model_profile_defaults_to_balanced(self):
        tmpl = load_template("gstack")
        assert tmpl.model_profile.get("default") == "balanced"
```

**File 2 — `tests/test_gstack_plugin.py`** (covers TEAM-04, SPRINT-06, plugin-load isolation; unskipped by Wave 3):

```python
"""Wave 0 scaffold per 03-01-PLAN. Unskipped by Wave 3 (03-06-PLAN)."""
import pytest
from clawteam.harness.phase_registry import reset_registry as reset_phase_registry

def setup_function():
    try:
        reset_phase_registry()
    except Exception:
        pass

def teardown_function():
    try:
        reset_phase_registry()
    except Exception:
        pass

@pytest.mark.skip(reason="Wave 3: GstackSprintPlugin ships in 03-06-PLAN")
def test_seven_phases_registered_in_order():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin, GSTACK_PHASES
    from clawteam.plugins.manager import PluginManager
    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)
    from clawteam.harness.phase_registry import get_registry
    assert get_registry().ordered_names() == GSTACK_PHASES

@pytest.mark.skip(reason="Wave 3")
def test_six_evidence_schemas_registered():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager
    from clawteam.harness.evidence_schemas import get_schema, reset_registry
    reset_registry()
    PluginManager()._instantiate_and_register(GstackSprintPlugin)
    for name in ["design-doc", "plan-doc", "test-report", "review-report", "ship-notes", "retro"]:
        assert get_schema(name) is not None

@pytest.mark.skip(reason="Wave 3: TEAM-04 leader-role enforcement")
def test_only_ceo_advances_phase(tmp_path):
    # Seed gstack team with leader_role="ceo"; assert engineer rejected, ceo allowed
    pass

@pytest.mark.skip(reason="Wave 3: SPRINT-06 Reflect-phase placeholder")
def test_reflect_phase_learn_stub_writes_placeholder(tmp_path):
    # Emit PhaseTransition(to_phase="reflect"); assert _phase6_pending/<sprint_id>-retro.json exists
    pass
```

**File 3 — `tests/test_gstack_role_prompts.py`** (covers SKILL-01..08 + D-14 budget gate; unskipped by Wave 2):

```python
"""Wave 0 scaffold per 03-01-PLAN. Unskipped by Wave 2 (03-04, 03-05-PLAN)."""
from pathlib import Path
import pytest

PROMPTS_DIR = Path(__file__).parent.parent / "clawteam" / "templates" / "gstack" / "prompts"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "gstack_skills"

# One scaffold per role — Wave 2 unskips with verbatim content from D-13 fixtures
@pytest.mark.skip(reason="Wave 2: pm.md ships in 03-04-PLAN")
def test_pm_office_hours_rubric():
    pass

@pytest.mark.skip(reason="Wave 2")
def test_ceo_plan_review_modes():
    pass

@pytest.mark.skip(reason="Wave 2")
def test_eng_mgr_plan_review_and_retro():
    pass

@pytest.mark.skip(reason="Wave 2")
def test_designer_rubric():
    pass

@pytest.mark.skip(reason="Wave 2")
def test_dx_lead_devex_review():
    pass

@pytest.mark.skip(reason="Wave 2")
def test_reviewer_review_and_investigate():
    pass

@pytest.mark.skip(reason="Wave 2")
def test_qa_qa_only():
    pass

@pytest.mark.skip(reason="Wave 2")
def test_security_cso_full_rubric():
    pass

@pytest.mark.skip(reason="Wave 2: D-14 prompt budget gate")
def test_role_prompt_size_budget():
    """D-14: every prompt <= 4 KB; average <= 3 KB."""
    sizes = {p.name: p.stat().st_size for p in PROMPTS_DIR.glob("*.md")}
    assert len(sizes) == 11, f"expected 11 prompts, found {len(sizes)}"
    for name, size in sizes.items():
        assert size <= 4096, f"{name} = {size} bytes (cap 4096)"
    avg = sum(sizes.values()) / len(sizes)
    assert avg <= 3072, f"average = {avg:.0f} bytes (cap 3072)"
```

**File 4 — `tests/test_envelope_personas.py`** (covers D-07 per-persona envelope subclasses; unskipped by Wave 1):

```python
"""Wave 0 scaffold per 03-01-PLAN. Unskipped by Wave 1 (03-03-PLAN)."""
import pytest
from pydantic import ValidationError

PERSONAS = [
    ("PMEnvelope", "pm", "pm.challenge", "Why three months and not now?"),
    ("CEOEnvelope", "ceo", "ceo.decision_mode", "expansion"),
    ("EngMgrEnvelope", "eng-mgr", "eng-mgr.architecture_lock", "use existing pydantic registry; no new abstraction"),
    ("DesignerEnvelope", "designer", "designer.dimension", "typographic system"),
    ("DxLeadEnvelope", "dx-lead", "dx-lead.friction", "TTHW > 5min for new install"),
    ("EngineerEnvelope", "engineer", "engineer.diff_summary", "added auto_advance flag and tests"),
    ("ReviewerEnvelope", "reviewer", "reviewer.iron_law", "investigated"),
    ("QAEnvelope", "qa", "qa.mode", "qa"),
    ("SecurityEnvelope", "security", "security.confidence", 9),
    ("ShipperEnvelope", "shipper", "shipper.step", "push"),
    ("SREEnvelope", "sre", "sre.signal", "nominal"),
]

@pytest.mark.parametrize("class_name,persona,field_alias,valid_value", PERSONAS)
@pytest.mark.skip(reason="Wave 1: envelope_personas.py ships in 03-03-PLAN")
def test_persona_envelope_required_field_present(class_name, persona, field_alias, valid_value):
    pass

@pytest.mark.skip(reason="Wave 1: discriminated-union dispatch")
def test_validate_persona_envelope_dispatches_on_persona():
    pass
```

**File 5 — `tests/test_gstack_team_spawn.py`** (covers TEAM-03, UX-01 integration; unskipped by Wave 4):

```python
"""Wave 0 scaffold per 03-01-PLAN. Unskipped by Wave 4 (03-07-PLAN)."""
import pytest

@pytest.mark.skip(reason="Wave 4: end-to-end spawn ships in 03-07-PLAN")
def test_eleven_worktrees_created(tmp_path, monkeypatch):
    """TEAM-03: WorkspaceManager.create_workspace called 11 times for gstack."""
    pass

@pytest.mark.skip(reason="Wave 4: UX-01 end-to-end")
def test_team_spawn_gstack(tmp_path, monkeypatch):
    """UX-01: clawteam team spawn gstack --name <name> spawns 11 agents."""
    pass

@pytest.mark.skip(reason="Wave 4: D-05 per-role memory dir pre-creation")
def test_per_role_memory_dirs_precreated(tmp_path, monkeypatch):
    """D-05: 11 memory dirs exist at ~/.clawteam/teams/<name>/memory/<role>/."""
    pass
```

**Atomic-commit discipline (D-01):** Commit all 5 files as ONE atomic commit titled `test(03-01): scaffold Wave 0 test stubs for gstack template/plugin/prompts/personas/spawn`.
  </action>
  <verify>
    <automated>pytest tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py tests/test_envelope_personas.py tests/test_gstack_team_spawn.py --collect-only -q 2>&1 | grep -E 'test (collected|skipped)' && pytest tests/ -x 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py tests/test_envelope_personas.py tests/test_gstack_team_spawn.py --collect-only -q` collects at least 25 test IDs total (6 + 4 + 9 + 12 + 3 = 34 minimum)
    - `pytest tests/ -x` exits 0 (suite stays green; all new tests skip; no failures)
    - `grep -l 'pytest.mark.skip' tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py tests/test_envelope_personas.py tests/test_gstack_team_spawn.py` lists all 5 files
    - All 5 files import only modules that exist (no `ImportError` on collection — confirmed by `--collect-only` exiting 0)
  </acceptance_criteria>
  <done>5 test files exist with skipped stubs; full suite stays green; all test IDs from VALIDATION.md "Per-Task Verification Map" are discoverable so subsequent waves can directly unskip them.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| WebFetch -> committed fixtures | External markdown content fetched once and stored under `tests/fixtures/gstack_skills/`; subsequent CI runs read from disk only (no re-fetch) |
| Test scaffolds -> import surface | Test files import from `clawteam.*` and `pydantic` only; no eval, no shell-out, no network |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-01 | Tampering | WebFetched gstack skill markdown content (could be poisoned upstream and silently mis-port the rubrics) | mitigate | Fixtures committed to git ONCE in this plan (D-13) — never re-fetched in CI. Wave 2 grep tests assert verbatim content presence; if upstream drifts and someone re-runs the fetch, the diff is human-reviewable in PR. The commit message body records the verbatim 6 questions / 10 dimensions / 17 exclusions as a fingerprint. |
| T-03-02 | Information Disclosure | WebFetch leaks credentials in shell history when using `gh api` | accept | Repo `garrytan/gstack` is public; `gh api` reads only public content; no auth tokens transmitted. If `gh` is unauthenticated, falls back to public `raw.githubusercontent.com` URL. |
| T-03-03 | Elevation of Privilege | New `actor` parameter on `advance_phase` could be spoofed by a misbehaving plugin or test fixture passing `actor="ceo"` from a non-ceo agent context | accept (Phase 4 closes) | Phase 3 enforces only at the conductor layer; the agent caller's identity is asserted by the spawn-time identity envs (CLAWTEAM_AGENT, CLAWTEAM_ROLE) which are only set by the spawn registry. Phase 4's SmartReviewRouter ships the cross-agent verification that closes the gap. Documented in the docstring for advance_phase. |
| T-03-04 | Denial of Service | Test scaffolds with broken imports could crash the whole suite | mitigate | All scaffolded tests use `pytest.mark.skip`; imports are lightweight (top-of-file imports kept to stdlib + already-tested modules). `pytest --collect-only` validates imports succeed before any test runs (acceptance criterion). |

</threat_model>

<verification>
- All 11 fixture files exist + are git-tracked: `ls tests/fixtures/gstack_skills/*.md | wc -l` outputs 11
- `SprintConductor.advance_phase` signature includes `actor: str = ""`: grep passes
- `TeamConfig.leader_role` field exists with empty default: python -c roundtrip passes
- All 5 new test files exist with skipped/xfail stubs: pytest --collect-only succeeds
- Phase 2 regression preserved: `pytest tests/test_phase2_integration.py -x` exits 0
- Full suite stays green: `pytest tests/ -x` exits 0
- D-13 verbatim counts captured in commit message body OR `# CONTENT-DRIFT-NOTE:` line in fixtures
</verification>

<success_criteria>
- 11 upstream gstack skill markdown fixtures committed (Strategy B per D-08)
- `SprintConductor.advance_phase(actor: str = "")` ships with leader-role check (D-10)
- `TeamConfig.leader_role: str = ""` ships (Pattern 4 prerequisite)
- 5 new test files scaffolded with skipped stubs covering 16 REQ-IDs (Nyquist)
- D-13 verbatim content (6 questions / 10 dimensions / 17 exclusions) recorded in commit message body so Wave 2 has the source-of-truth strings
- Phase 2 regression preserved: `pytest tests/ -x` exits 0
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-01-SUMMARY.md` covering:
- Fixture WebFetch results (URL paths used, exact filenames discovered, content drift notes if any)
- D-13 verbatim extracts (6 forcing questions, 10 design rubric dimensions, 17 false-positive exclusions) — used by Wave 2
- SprintConductor + TeamConfig changes (file:line)
- Test scaffold inventory (5 files, N test IDs collected)
- Suite status: `pytest tests/ -x` outcome
</output>
