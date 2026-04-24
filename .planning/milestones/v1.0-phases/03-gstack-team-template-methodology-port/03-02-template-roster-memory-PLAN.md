---
phase: 03-gstack-team-template-methodology-port
plan: 02
type: execute
wave: 1
depends_on: [03-01]
files_modified:
  - clawteam/templates/__init__.py
  - clawteam/templates/gstack.toml
  - clawteam/team/manager.py
autonomous: true
requirements: [TEAM-01, TEAM-02, TEAM-03, TEAM-05]
must_haves:
  truths:
    - "User can run `clawteam team spawn gstack --name <n>` (UX-01 form) and the existing template loader parses gstack.toml without error; the new `team spawn` Typer subcommand wraps the same internals as `clawteam launch` with the UX-01-locked argument names"
    - "Loaded template exposes 11 distinct agent roles (pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre)"
    - "Default model_profile resolves to `balanced` when --model-profile is unset (Pitfall 12 prevention)"
    - "TeamManager.create_team pre-creates 11 per-role memory directories under ~/.clawteam/teams/<name>/memory/<role>/"
    - "Existing 6 templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) continue to parse + spawn unchanged"
  artifacts:
    - path: "clawteam/templates/gstack.toml"
      provides: "11-agent roster + leader_role + 7-phase declaration + per-role model_profile + memory layout"
      contains: "leader_role = \"ceo\""
    - path: "clawteam/templates/__init__.py"
      provides: "TemplateDef + AgentDef extended with optional fields (role, prompt_file, model_profile, leader_role, phases, memory)"
      contains: "leader_role: str = \"\""
    - path: "clawteam/team/manager.py"
      provides: "TeamManager.create_team accepts roles= kwarg; pre-creates per-role memory dirs"
      contains: "memory"
  key_links:
    - from: "clawteam/templates/gstack.toml"
      to: "clawteam/templates/gstack/prompts/<role>.md"
      via: "prompt_file = \"gstack/prompts/<role>.md\" per agent row"
      pattern: "prompt_file.*gstack/prompts"
    - from: "clawteam/templates/__init__.py"
      to: "clawteam/team/models.py::TeamConfig.leader_role"
      via: "TemplateDef.leader_role flows into TeamConfig.leader_role at TeamManager.create_team"
      pattern: "leader_role"
    - from: "clawteam/team/manager.py::create_team"
      to: "~/.clawteam/teams/<name>/memory/<role>/"
      via: "ensure_within_root + mkdir(parents=True, exist_ok=True) per role"
      pattern: "memory.*mkdir"
---

<objective>
Ship the gstack template roster declaration and the per-role memory directory pre-creation. Extends `TemplateDef`/`AgentDef` pydantic models with optional fields (Pattern 1 strict-additive), authors `clawteam/templates/gstack.toml` as the 11-agent declaration (D-04), and extends `TeamManager.create_team` with per-role memory dir pre-creation (D-05).

Purpose: After this plan, `clawteam team spawn gstack --name foo` (UX-01) successfully parses the template and instantiates 11 spawn calls; per-role memory directories exist for Phase 6 to populate later; TeamConfig persists `template="gstack"` and `leader_role="ceo"` so 03-07's Reflect-handler can filter on template name. The per-role prompt files are NOT yet written (Wave 2's job) — `prompt_file` paths are declared but resolution is deferred to the plugin's `contribute_prompts` hook in Wave 3.

Output:
- gstack.toml — pure roster (no [[template.tasks]]; D-04)
- TemplateDef + AgentDef — additive optional fields (Pattern 1)
- TeamManager.create_team — per-role memory dir creation (D-05)
- 6 existing templates continue to parse + spawn (BC preserved)
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

<interfaces>
<!-- Contracts the executor will use, extracted verbatim from PATTERNS.md analog reads. -->

From clawteam/templates/__init__.py (existing AgentDef, TemplateDef — Wave 1 extends additively):
```python
class AgentDef(BaseModel):
    name: str
    type: str = "general-purpose"
    task: str = ""
    command: list[str] | None = None
    # Wave 1 ADDS: role, prompt_file, model_profile (all optional, default "")

class TemplateDef(BaseModel):
    name: str
    description: str = ""
    command: list[str] = ["claude"]
    backend: str = "tmux"
    leader: AgentDef
    agents: list[AgentDef] = []
    tasks: list[TaskDef] = []
    # Wave 1 ADDS: leader_role, phases, model_profile, memory (all optional)
```

From clawteam/templates/software-dev.toml (TOML schema convention — exact-shape analog):
```toml
[template]
name = "software-dev"
description = "Software Development Team - multi-agent full-stack development with parallel workstreams"
command = ["claude"]
backend = "tmux"

[template.leader]
name = "tech-lead"
type = "tech-lead"
task = """..."""

[[template.agents]]
name = "backend-dev"
type = "backend-developer"
task = """..."""
```

From clawteam/team/manager.py::create_team (lines 77-112) — extension point for memory dir creation:
```python
@staticmethod
def create_team(name, leader_name, leader_id, description="", user="", leader_agent_type="leader") -> TeamConfig:
    # ... validation, config creation, _save_config, inbox dir, tasks dir
    # Wave 1 ADDS: optional roles= kwarg; per-role memory dir loop
    return config
```

From clawteam/paths.py (path-safety convention):
```python
ensure_within_root(root: Path, subpath: str) -> Path  # validates subpath stays under root
validate_identifier(value: str, name: str) -> str    # rejects path traversal in names
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend TemplateDef + AgentDef with optional fields (Pattern 1 strict-additive)</name>
  <files>clawteam/templates/__init__.py</files>
  <read_first>
    - clawteam/templates/__init__.py (lines 11-100 — current AgentDef, TemplateDef, _parse_toml)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 776-849 — exact extension snippet)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (Pattern 1 — strict additive extension)
    - clawteam/templates/software-dev.toml (existing TOML to confirm BC)
    - tests/test_templates.py (TestLoadBuiltinTemplate — assert all 6 existing templates still load)
  </read_first>
  <behavior>
    - Test 1: `AgentDef(name="x")` succeeds — all new fields default to ""
    - Test 2: `AgentDef(name="x", role="pm", prompt_file="gstack/prompts/pm.md", model_profile="opus")` succeeds with all fields populated
    - Test 3: `TemplateDef(name="x", leader=AgentDef(name="y"))` succeeds — leader_role defaults to "", phases to [], model_profile to {}, memory to {}
    - Test 4: All 6 existing templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) load via `load_template(name)` without error
    - Test 5: An existing template's `agent.role` resolves to "" (default; existing TOMLs don't set this field)
    - Test 6: `_parse_toml` reads `leader_role`, `phases`, `model_profile`, `memory` from the [template] block when present, defaulting to empty when absent
  </behavior>
  <action>
**File: `clawteam/templates/__init__.py`**

Locate the existing `AgentDef`, `TemplateDef`, and `_parse_toml` declarations (lines 24-100 per PATTERNS.md). Apply these EXACT additive extensions:

```python
class AgentDef(BaseModel):
    name: str
    type: str = "general-purpose"
    task: str = ""
    command: list[str] | None = None
    # NEW Phase 3 (D-06): semantic role identifier (e.g., "pm", "ceo")
    role: str = ""
    # NEW Phase 3 (D-06): template-relative path to prompt .md (e.g., "gstack/prompts/pm.md")
    prompt_file: str = ""
    # NEW Phase 3: per-agent model override; "" = inherit template default
    model_profile: str = ""


class TemplateDef(BaseModel):
    name: str
    description: str = ""
    command: list[str] = ["claude"]
    backend: str = "tmux"
    leader: AgentDef
    agents: list[AgentDef] = []
    tasks: list[TaskDef] = []
    # NEW Phase 3 (D-04, Pattern 4): role authorized to advance_phase; "" = no leader binding
    leader_role: str = ""
    # NEW Phase 3 (D-04): plugin-contributed phase order; [] = use registry only
    phases: list[str] = []
    # NEW Phase 3 (TEAM-05): per-role model assignments + "default" key
    model_profile: dict[str, str] = {}
    # NEW Phase 3 (D-05): {"root": "...", "per_role": True}
    memory: dict[str, str | bool] = {}
```

Then extend `_parse_toml` (currently around lines 75-100) to read the new fields:

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
        leader_role=tmpl.get("leader_role", ""),       # NEW
        phases=tmpl.get("phases", []),                  # NEW
        model_profile=tmpl.get("model_profile", {}),    # NEW
        memory=tmpl.get("memory", {}),                  # NEW
    )
```

**Critical:** preserve every other field, validator, and import in `clawteam/templates/__init__.py` verbatim — this is a strict-additive extension only.

**No new test file** — extend `tests/test_templates.py` with the 6 behavior tests above (or unskip the relevant ones in `tests/test_gstack_template.py` from Wave 0). Suite must stay green for all 6 existing templates.

Commit: `feat(03-02): extend TemplateDef + AgentDef with optional Phase 3 fields`
  </action>
  <verify>
    <automated>pytest tests/test_templates.py -x && python -c "from clawteam.templates import load_template; t = load_template('software-dev'); assert t.leader_role == '' and t.phases == [] and t.model_profile == {} and t.memory == {} and t.agents[0].role == ''"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -E '^\s*leader_role: str = ""' clawteam/templates/__init__.py` exits 0
    - `grep -E '^\s*phases: list\[str\] = \[\]' clawteam/templates/__init__.py` exits 0
    - `grep -E '^\s*model_profile: dict\[str, str\] = \{\}' clawteam/templates/__init__.py` exits 0
    - `grep -E '^\s*memory: dict\[str, str \| bool\] = \{\}' clawteam/templates/__init__.py` exits 0
    - `grep -E '^\s*role: str = ""' clawteam/templates/__init__.py` exits 0
    - `grep -E '^\s*prompt_file: str = ""' clawteam/templates/__init__.py` exits 0
    - `pytest tests/test_templates.py -x` exits 0 (all 6 existing templates load unchanged)
    - `pytest tests/test_template_regression_matrix.py -x` exits 0 (all 6 templates spawn unchanged)
    - `python -c "from clawteam.templates import load_template; t = load_template('software-dev'); assert t.leader_role == '' and t.phases == [] and t.model_profile == {} and t.memory == {}"` exits 0
  </acceptance_criteria>
  <done>TemplateDef + AgentDef carry the 7 new optional fields with empty defaults; all 6 existing templates load + spawn unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Author clawteam/templates/gstack.toml — 11-agent roster (D-04, D-06)</name>
  <files>clawteam/templates/gstack.toml</files>
  <read_first>
    - clawteam/templates/software-dev.toml (full file — exact-shape TOML analog)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 65-103 — gstack.toml Pattern Assignments section)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-04 contents specification)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 392-443 — gstack.toml verified shape)
    - tests/test_gstack_template.py (Wave 0 scaffold — exact assertions to satisfy)
  </read_first>
  <action>
Author `clawteam/templates/gstack.toml` with EXACTLY this structure (D-04: pure roster, NO `[[template.tasks]]` rows):

```toml
# clawteam/templates/gstack.toml
# Phase 3 plan 03-02 — 11-specialist persistent engineering team running 7-phase sprints.
# leader_role binding (D-04, Pattern 4): only ceo can advance_phase.
# No starter [[template.tasks]] rows (D-04): team waits for `clawteam sprint start`.

[template]
name = "gstack"
description = "11-specialist persistent engineering team running 7-phase sprints (Think/Plan/Build/Review/Test/Ship/Reflect)"
command = ["claude"]
backend = "tmux"
leader_role = "ceo"
phases = ["think", "plan", "build", "review", "test", "ship", "reflect"]

[template.model_profile]
# TEAM-05: balanced default (Pitfall 12 prevention — never default to quality).
# User overrides via: clawteam team spawn gstack --model-profile quality|budget
default = "balanced"
# Per-role assignments under balanced mode:
pm = "opus"          # strategic coach (challenges scope)
ceo = "opus"         # strategic decider + leader (advances phases)
eng-mgr = "sonnet"   # planning execution
designer = "sonnet"  # rubric + AI-slop detection
dx-lead = "sonnet"   # persona/TTHW/friction
engineer = "sonnet"  # implementation discipline
reviewer = "sonnet"  # iron-law root-cause
qa = "sonnet"        # bug-fix + regression loop
security = "sonnet"  # OWASP + STRIDE
shipper = "haiku"    # clerical: PR opening, deploy
sre = "haiku"        # clerical: monitoring, benchmarks

[template.memory]
# D-05: per-role memory dir layout. Pre-created by TeamManager.create_team
# at spawn time. Phase 6 fills with /learn entries.
root = "{data_dir}/teams/{team_name}/memory"
per_role = true

[template.leader]
name = "ceo"
type = "strategic-leader"
role = "ceo"
prompt_file = "gstack/prompts/ceo.md"

[[template.agents]]
name = "pm"
type = "yc-advisor"
role = "pm"
prompt_file = "gstack/prompts/pm.md"

[[template.agents]]
name = "eng-mgr"
type = "engineering-manager"
role = "eng-mgr"
prompt_file = "gstack/prompts/eng-mgr.md"

[[template.agents]]
name = "designer"
type = "designer"
role = "designer"
prompt_file = "gstack/prompts/designer.md"

[[template.agents]]
name = "dx-lead"
type = "developer-experience-lead"
role = "dx-lead"
prompt_file = "gstack/prompts/dx-lead.md"

[[template.agents]]
name = "engineer"
type = "engineer"
role = "engineer"
prompt_file = "gstack/prompts/engineer.md"

[[template.agents]]
name = "reviewer"
type = "staff-engineer-reviewer"
role = "reviewer"
prompt_file = "gstack/prompts/reviewer.md"

[[template.agents]]
name = "qa"
type = "qa"
role = "qa"
prompt_file = "gstack/prompts/qa.md"

[[template.agents]]
name = "security"
type = "security-officer"
role = "security"
prompt_file = "gstack/prompts/security.md"

[[template.agents]]
name = "shipper"
type = "shipper"
role = "shipper"
prompt_file = "gstack/prompts/shipper.md"

[[template.agents]]
name = "sre"
type = "site-reliability-engineer"
role = "sre"
prompt_file = "gstack/prompts/sre.md"

# NOTE: no [[template.tasks]] rows. gstack sprints are dispatched dynamically
# by SprintConductor per /sprint start. Per D-04: "team waits for /sprint start".
```

**Critical contract notes:**
- Leader is `ceo` (D-04). Leader is rendered as `[template.leader]` (singular, like other templates) — NOT in `[[template.agents]]`. The 10 specialists in `[[template.agents]]` plus the 1 leader = 11 total agents (TEAM-02).
- All 11 prompt_file paths must point under `gstack/prompts/<role>.md` — Wave 2 plans (03-04, 03-05) author the actual files.
- Per-role names in `[template.model_profile]` use TOML's bare-key syntax. Note: TOML keys with hyphens (`eng-mgr`, `dx-lead`) are NOT valid bare keys — they MUST be quoted: `"eng-mgr" = "sonnet"`. Update the model_profile block accordingly.

Re-author the model_profile block with quoted hyphenated keys:

```toml
[template.model_profile]
default = "balanced"
pm = "opus"
ceo = "opus"
"eng-mgr" = "sonnet"
designer = "sonnet"
"dx-lead" = "sonnet"
engineer = "sonnet"
reviewer = "sonnet"
qa = "sonnet"
security = "sonnet"
shipper = "haiku"
sre = "haiku"
```

After authoring, unskip the relevant tests in `tests/test_gstack_template.py` (from Wave 0):
- `test_parses_via_existing_loader`
- `test_eleven_agents_with_distinct_roles`
- `test_no_starter_tasks`
- `test_leader_role_field`
- `test_phases_field`
- `test_model_profile_defaults_to_balanced`

Commit: `feat(03-02): add gstack.toml — 11-specialist roster + leader binding + 7-phase declaration`
  </action>
  <verify>
    <automated>pytest tests/test_gstack_template.py::TestLoadGstackTemplate -x</automated>
  </verify>
  <acceptance_criteria>
    - File exists: `test -f clawteam/templates/gstack.toml`
    - `python -c "from clawteam.templates import load_template; t = load_template('gstack'); assert t.name == 'gstack' and t.leader_role == 'ceo' and t.phases == ['think','plan','build','review','test','ship','reflect'] and t.tasks == []"` exits 0
    - `python -c "from clawteam.templates import load_template; t = load_template('gstack'); names = {t.leader.name} | {a.name for a in t.agents}; assert names == {'ceo','pm','eng-mgr','designer','dx-lead','engineer','reviewer','qa','security','shipper','sre'}"` exits 0
    - `python -c "from clawteam.templates import load_template; t = load_template('gstack'); assert t.model_profile.get('default') == 'balanced' and t.model_profile.get('engineer') == 'sonnet' and t.model_profile.get('shipper') == 'haiku'"` exits 0
    - `pytest tests/test_gstack_template.py::TestLoadGstackTemplate -x` exits 0 (6 unskipped tests pass)
    - `pytest tests/test_templates.py tests/test_template_regression_matrix.py -x` exits 0 (existing 6 templates unaffected)
    - `grep -c '\[\[template.agents\]\]' clawteam/templates/gstack.toml` outputs `10` (10 specialists + 1 leader = 11)
    - `grep -c '\[\[template.tasks\]\]' clawteam/templates/gstack.toml` outputs `0` (D-04: no starter tasks)
  </acceptance_criteria>
  <done>gstack.toml ships with 11 agents + ceo as leader + 7 phases declared + balanced default model profile + per-role memory layout; existing templates unaffected.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Extend TeamManager.create_team with per-role memory dir pre-creation (D-05)</name>
  <files>clawteam/team/manager.py, clawteam/cli/commands.py (launch flow — pass roles to create_team)</files>
  <read_first>
    - clawteam/team/manager.py (lines 60-115 — current create_team signature + body)
    - clawteam/paths.py (ensure_within_root, validate_identifier helpers)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 853-911 — exact extension snippet for create_team)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-05 rationale: race-free pre-creation; Phase 6 fills the dirs)
    - clawteam/cli/commands.py (the existing `clawteam launch` command body — find the call to TeamManager.create_team; the new `clawteam team spawn` Typer subcommand mirrors its internals)
    - clawteam/cli/commands.py (the `team_app` Typer subgroup at line 1611 — `team_status` is the structural analog for adding the new `team_spawn` command)
  </read_first>
  <behavior>
    - Test 1: `TeamManager.create_team(name="t", leader_name="l", leader_id="lid")` succeeds without `roles=` kwarg — backwards compat preserved
    - Test 2: `TeamManager.create_team(name="t", leader_name="l", leader_id="lid", roles=[])` succeeds — empty roles is a no-op
    - Test 3: `TeamManager.create_team(name="t", leader_name="l", leader_id="lid", roles=["pm","ceo","engineer"])` creates `~/.clawteam/teams/t/memory/{pm,ceo,engineer}/` (3 directories)
    - Test 4: Calling `create_team` twice with same `roles=` succeeds (idempotent — `mkdir(exist_ok=True)`)
    - Test 5: `roles=["../etc/passwd"]` raises ValueError via `validate_identifier` — path traversal rejected
    - Test 6: After `clawteam team spawn gstack --name foo` (NEW UX-01 command), `~/.clawteam/teams/foo/memory/{pm,ceo,eng-mgr,designer,dx-lead,engineer,reviewer,qa,security,shipper,sre}/` all exist (11 dirs); `TeamManager.get_team("foo").template == "gstack"` and `.leader_role == "ceo"`
    - Test 7: `clawteam team spawn gstack --name foo` and `clawteam launch gstack --team foo` produce identical TeamConfig state (the new subcommand is a thin wrapper around the same internals — no new persistence path)
  </behavior>
  <action>
**File 1 — `clawteam/team/manager.py`:** Locate `TeamManager.create_team` (lines 77-112 per PATTERNS.md). Apply this extension AFTER the existing `tasks_dir.mkdir(...)` line, BEFORE `return config`:

```python
@staticmethod
def create_team(
    name: str,
    leader_name: str,
    leader_id: str,
    description: str = "",
    user: str = "",
    leader_agent_type: str = "leader",
    roles: list[str] | None = None,        # NEW Phase 3 (D-05): per-role memory dir pre-creation
    leader_role: str = "",                 # NEW Phase 3 (Pattern 4): persists leader_role on TeamConfig
    template: str = "",                    # NEW Phase 3 (03-07 key_link): persists template name on TeamConfig
) -> TeamConfig:
    # ... existing validation (validate_identifier(name, ...), ...) UNCHANGED
    # ... existing _save_config UNCHANGED — but pass leader_role + template into TeamConfig kwargs:
    config = TeamConfig(
        name=name,
        description=description,
        lead_agent_id=leader_id,
        members=[leader],
        leader_role=leader_role,           # NEW: flows TemplateDef.leader_role into TeamConfig
        template=template,                 # NEW: flows TemplateDef.name into TeamConfig (03-07 _resolve_team_template reads this)
    )
    _save_config(config)
    # ... existing inbox/tasks dir mkdir UNCHANGED

    # NEW Phase 3 (D-05): pre-create per-role memory dirs idempotently.
    # Race-free: 11 mkdir calls during one-time spawn beats lazy-init under
    # N parallel sprints x 11 agents (Phase 6 will write here concurrently).
    if roles:
        from clawteam.paths import ensure_within_root, validate_identifier
        for role in roles:
            role_id = validate_identifier(role, "role name")
            memory_dir = ensure_within_root(_team_dir(name) / "memory", role_id)
            memory_dir.mkdir(parents=True, exist_ok=True)

    return config
```

If `_team_dir(name)` is not the existing helper, use whatever path-construction idiom `create_team` already uses for the inbox/tasks paths (likely `get_data_dir() / "teams" / name`).

**File 2 — `clawteam/cli/commands.py` (existing `clawteam launch` command):** Find the `clawteam launch` command body (look for `TeamManager.create_team(` call sites). When the loaded template is `gstack` (or any template with `leader_role` set), pass:

```python
TeamManager.create_team(
    name=team_name,
    leader_name=tmpl.leader.name,
    leader_id=leader_id,
    # ... existing kwargs UNCHANGED
    roles=[a.role for a in [tmpl.leader, *tmpl.agents] if a.role],  # NEW Phase 3
    leader_role=tmpl.leader_role,                                    # NEW Phase 3
    template=tmpl.name,                                              # NEW Phase 3 (03-07 key_link)
)
```

The `roles=[...]` filter (`if a.role`) skips agents from existing templates that don't set the `role` field (BC: empty `role` = no memory dir for that agent).

**File 3 — `clawteam/cli/commands.py` (NEW `clawteam team spawn` Typer subcommand for UX-01):** UX-01 locks the user-facing CLI form as `clawteam team spawn <template> --name <name>`. Plan-checker verified that this command does NOT exist in the current tree — the `team_app` subgroup at line 1611 has `status`/`spawn-team` but no `spawn` taking a template arg. Add the new subcommand mirroring `team_status`'s shape (line 1611-1656) and delegating internals to the same `launch` body via a shared helper.

Insert AFTER the existing `team_status` command (around line 1657, before `team_snapshot`):

```python
@team_app.command("spawn")
def team_spawn(
    template: str = typer.Argument(..., help="Template name (e.g., 'gstack', 'software-dev')"),
    name: str = typer.Option(..., "--name", "-n", help="Team name"),
    model_profile: str = typer.Option("", "--model-profile", help="Override model profile (balanced|quality|budget)"),
):
    """Spawn a team from a template (UX-01).

    Shipped in Phase 3 (03-02). Wraps the same internals as `clawteam launch`
    using the UX-01-locked argument names: `<template>` positional and `--name`.
    Equivalent invocations:
      clawteam team spawn gstack --name acme
      clawteam launch gstack --team acme
    """
    from clawteam.templates import load_template
    from clawteam.team.manager import TeamManager

    try:
        tmpl = load_template(template)
    except FileNotFoundError:
        _output(
            {"error": f"Template '{template}' not found"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)

    # Optional model_profile override (TEAM-05 — user can pick balanced|quality|budget)
    if model_profile:
        # Apply override by mutating the loaded TemplateDef before create_team consumes it.
        tmpl.model_profile = {**tmpl.model_profile, "default": model_profile}

    leader_id = f"{tmpl.leader.name}-{name}"  # mirror existing launch's leader-id convention
    config = TeamManager.create_team(
        name=name,
        leader_name=tmpl.leader.name,
        leader_id=leader_id,
        description=tmpl.description,
        leader_agent_type=tmpl.leader.type,
        roles=[a.role for a in [tmpl.leader, *tmpl.agents] if a.role],
        leader_role=tmpl.leader_role,
        template=tmpl.name,
    )

    data = {
        "name": config.name,
        "template": tmpl.name,
        "agentCount": 1 + len(tmpl.agents),
        "leaderRole": tmpl.leader_role,
    }

    def _human(d):
        console.print(
            f"\n[green]✓[/green] Spawned team [cyan]{d['name']}[/cyan]"
            f" from template [magenta]{d['template']}[/magenta]"
            f" — {d['agentCount']} agents"
            + (f" (leader: [magenta]{d['leaderRole']}[/magenta])" if d['leaderRole'] else "")
        )
        console.print(f"  Run [bold]clawteam team show {d['name']}[/bold] for the dashboard.")

    _output(data, _human)
```

**Critical details:**
- The new subcommand is a THIN WRAPPER. It does not duplicate `launch`'s logic — it composes the same `TeamManager.create_team` call. If `launch` later evolves (e.g., adds workspace flags), `team spawn` follows by re-calling the same helper.
- `_output(data, _human)` is the same dual-path renderer used elsewhere — JSON mode is supported automatically.
- Argument naming matches UX-01 verbatim: positional `<template>` + `--name <n>`. Existing `launch` (positional `<template>` + `--team <n>`) continues to work for backwards compat.
- If `launch` already has its own internal helper (e.g., `_spawn_team(tmpl, name, ...)`), refactor it into a module-level `_spawn_team_impl` and have BOTH `launch` and `team_spawn` call it. Otherwise, the inlined call above is acceptable for v1.

**Tests:** Add test cases to `tests/test_manager.py` (or create `tests/test_team_manager_memory.py` if cleaner) covering all 7 behaviors above. Add `tests/test_cli_commands.py::test_team_spawn_gstack_command` covering the new UX-01 surface (CliRunner invocation; assert exit 0; TeamConfig.template == "gstack" + leader_role == "ceo"). Use the autouse `isolated_data_dir` fixture from `tests/conftest.py`.

Commit: `feat(03-02): pre-create per-role memory dirs + add team spawn CLI subcommand for UX-01 (D-05 + 03-07 key_link)`
  </action>
  <verify>
    <automated>pytest tests/ -k 'create_team or memory_dir' -x && pytest tests/test_template_regression_matrix.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -E 'roles: list\[str\] \| None = None' clawteam/team/manager.py` exits 0
    - `grep -E 'leader_role: str = ""' clawteam/team/manager.py` exits 0
    - `grep -E 'memory_dir.mkdir\(parents=True, exist_ok=True\)' clawteam/team/manager.py` exits 0
    - `grep -E 'roles=\[a\.role' clawteam/cli/commands.py` exits 0
    - `grep -E 'template=tmpl\.name' clawteam/cli/commands.py` exits 0
    - `grep -E 'template: str = ""' clawteam/team/manager.py` exits 0
    - `grep -q '@team_app.command\("spawn"\)' clawteam/cli/commands.py` exits 0 (NEW UX-01 subcommand exists)
    - `python -m clawteam team spawn --help` stdout contains the literal `template` and `--name` (UX-01 form)
    - `python -c "import os, tempfile; os.environ['CLAWTEAM_DATA_DIR'] = tempfile.mkdtemp(); from clawteam.team.manager import TeamManager; TeamManager.create_team(name='t', leader_name='l', leader_id='lid', roles=['pm','ceo'], leader_role='ceo', template='gstack'); from clawteam.team.models import get_data_dir; cfg_path = get_data_dir() / 'teams' / 't' / 'config.json'; import json; cfg = json.loads(cfg_path.read_text()); assert cfg['template'] == 'gstack' and cfg['leader_role'] == 'ceo'; assert (get_data_dir() / 'teams' / 't' / 'memory' / 'pm').is_dir() and (get_data_dir() / 'teams' / 't' / 'memory' / 'ceo').is_dir()"` exits 0
    - `pytest tests/test_template_regression_matrix.py -x` exits 0 (existing templates unaffected — they don't pass `roles=`)
    - `pytest tests/ -k 'create_team or memory_dir' -x` exits 0 (6 behavior tests pass)
    - Path traversal test: `python -c "from clawteam.team.manager import TeamManager; TeamManager.create_team(name='t', leader_name='l', leader_id='lid', roles=['../etc/passwd'])"` exits with non-zero (ValueError from validate_identifier)
  </acceptance_criteria>
  <done>create_team accepts optional `roles=`, `leader_role=`, and `template=` kwargs; passes roles through with empty default; persists template name + leader_role on TeamConfig; new `clawteam team spawn <tmpl> --name <n>` Typer subcommand ships under `team_app` mirroring UX-01 verbatim; gstack spawn creates all 11 per-role memory dirs idempotently; existing templates BC-preserved.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `gstack.toml` content -> `tomllib.load` | Repo-trusted file (committed to git, reviewed in PR); reuses Phase 0 hardened TOML parser |
| User-supplied `--name <team>` -> filesystem path | Crosses trust boundary into `~/.clawteam/teams/<name>/`; mitigated by existing `validate_identifier` + `ensure_within_root` |
| User-supplied role names (from gstack.toml) -> per-role memory dir creation | Roles come from the committed gstack.toml (trusted), but the same code path is reachable by any future template; treated as untrusted at the filesystem boundary |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-03-05 | Tampering | `gstack.toml` parsed via `tomllib` | accept (Phase 0/1 already hardened) | Reuse existing safe `tomllib` loader (stdlib 3.11+) / `tomli` (3.10 backport). No `eval`. `extra="ignore"` default on pydantic models means malicious extra TOML keys are silently dropped, not executed. |
| T-03-06 | Tampering | Path traversal via crafted `roles=["../etc/passwd"]` | mitigate | `validate_identifier(role, "role name")` rejects path-traversal characters BEFORE `ensure_within_root` constructs the path. Both helpers are existing Phase 0/1 conventions (verified at `clawteam/team/manager.py:21,107,110` per PATTERNS.md Pattern B). Test 5 in Task 3 enforces this. |
| T-03-07 | Information Disclosure | Per-role memory dirs created with default umask might be world-readable | accept | Aligns with existing `~/.clawteam/teams/<name>/inboxes/` and `tasks/` directory permissions (Phase 0/1 convention). User's umask governs. No PII written by Phase 3 — Phase 6 owns memory write path and revisits permissions. |
| T-03-08 | Denial of Service | Repeated `clawteam launch gstack` calls would spam memory dir creation | accept | `mkdir(parents=True, exist_ok=True)` is idempotent (Test 4). The 11 mkdir calls during one-time spawn cost ~10ms total. No unbounded growth. |
| T-03-09 | Elevation of Privilege | Adding `leader_role` field to TemplateDef could let a malicious template grant itself "ceo" privileges that bypass conductor enforcement | mitigate | The `leader_role` field on its own grants nothing — `SprintConductor.advance_phase` enforces that the *caller's* `actor` matches `leader_role`. Caller identity comes from spawn-registry-set identity envs (CLAWTEAM_ROLE), not from user input. Documented in advance_phase docstring (Wave 0 Task 2). |

</threat_model>

<verification>
- gstack.toml parses + exposes 11 distinct agents: pytest tests/test_gstack_template.py passes
- Existing 6 templates unaffected: pytest tests/test_template_regression_matrix.py passes
- TemplateDef extended with 4 new optional fields (leader_role, phases, model_profile, memory): grep checks pass
- AgentDef extended with 3 new optional fields (role, prompt_file, model_profile): grep checks pass
- TeamManager.create_team accepts optional roles= + leader_role= kwargs: grep + behavior tests pass
- Per-role memory dirs created at launch time for gstack: integration test passes
- Path traversal rejected via validate_identifier: negative test passes
- Suite stays green: pytest tests/ -x exits 0
</verification>

<success_criteria>
- TEAM-01 satisfied: gstack.toml parses through existing template loader
- TEAM-02 satisfied: 11 distinct agents present in loaded template
- TEAM-03 satisfied (partial — full integration in 03-07 Wave 4): per-role memory dirs pre-created at launch
- TEAM-05 satisfied: model_profile defaults to "balanced"
- D-04 satisfied: no [[template.tasks]] in gstack.toml
- D-05 satisfied: TeamManager pre-creates per-role memory dirs
- Pattern 1 honored: all extensions are strict-additive with empty defaults; existing templates unaffected
- Phase 0 BC matrix continues to pass
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-02-SUMMARY.md` covering:
- TemplateDef + AgentDef extension (file:line of new fields)
- gstack.toml structure (11 agents, leader binding, no starter tasks)
- TeamManager.create_team extension (file:line of memory dir loop)
- BC verification: which existing templates were re-tested and the result
- Integration with Wave 0: the actor + leader_role plumbing now connects end-to-end (TemplateDef.leader_role -> TeamConfig.leader_role -> SprintConductor.advance_phase actor check)
</output>
