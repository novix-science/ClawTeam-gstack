"""Team template loader — load TOML templates for one-command team launch."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

# TOML support: built-in on 3.11+, conditional dependency on 3.10
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class AgentDef(BaseModel):
    name: str
    type: str = "general-purpose"
    task: str = ""
    command: list[str] | None = None
    # Phase 3 (Plan 03-02, D-06): semantic role identifier (e.g., "pm", "ceo").
    # Empty string for existing templates that don't use the role-driven prompt
    # resolution machinery; populated by gstack.toml + future role-aware templates.
    role: str = ""
    # Phase 3 (Plan 03-02, D-06): template-relative path to prompt .md
    # (e.g., "gstack/prompts/pm.md"). Resolved by the plugin's
    # contribute_prompts hook in Wave 3 (Plan 03-06).
    prompt_file: str = ""
    # Phase 3 (Plan 03-02): per-agent model override; "" means inherit the
    # template-level default from [template.model_profile].default.
    model_profile: str = ""


class TaskDef(BaseModel):
    subject: str
    description: str = ""
    owner: str = ""


# ---------------------------------------------------------------------------
# Phase 4 Plan 04-06 (§04-CONTEXT D-04 / A5): review-phase routing config.
# Declared here alongside TemplateDef so `_parse_toml` can populate
# `TemplateDef.review` atomically with the rest of the template shape.
# ---------------------------------------------------------------------------


class ReviewRule(BaseModel):
    """One routing rule for SmartReviewRouter (§04-CONTEXT D-04).

    Evaluated by :class:`clawteam.harness.gstack_review_router.GstackReviewRouter`.
    ``pattern`` is a path glob (engine selected per PLAN_PREP_NOTES A-fnmatch);
    ``reviewers`` are role names to add when any diff path matches. First-match
    WITH accumulation: a path matching two rules unions both reviewers.
    """

    pattern: str = Field(
        ...,
        min_length=1,
        description="Path glob (e.g. 'src/components/**/*.tsx').",
    )
    reviewers: list[str] = Field(
        default_factory=list,
        description="Roles to add on match.",
    )
    signal: str = Field(
        default="",
        description="Optional classification tag (ui|api|crypto|security).",
    )


class ReviewConfig(BaseModel):
    """Review-phase configuration (§04-CONTEXT D-04 / D-09).

    Default empty; only gstack.toml ships rules. The 6 other bundled
    templates omit the [template.review] block entirely and rehydrate to
    ``ReviewConfig(rules=[], sycophancy_threshold=0.9)``.
    """

    sycophancy_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description=(
            "Agreement-rate threshold for sycophancy_cascade_detected "
            "event (D-09/D-20)."
        ),
    )
    rules: list[ReviewRule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 5 Wave 0 (Plan 05-01 Task 3, A5): optional top-level sub-blocks on
# TemplateDef. All four fields default to None so existing templates parse
# unchanged (BC preservation for gstack.toml + 6 bundled templates).
# ---------------------------------------------------------------------------


class ShipConfig(BaseModel):
    """[ship] TOML block — /ship skill config (D-07, SKILL-14)."""

    coverage_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum test coverage ratio required before /ship advances.",
    )


class DeployConfig(BaseModel):
    """[deploy] TOML block — /land-and-deploy target (D-08, SKILL-15)."""

    provider: Literal["vercel", "netlify", "fly", "custom"] = Field(
        ...,
        description="Deploy backend; 'custom' requires custom_deploy_cmd.",
    )
    project: str = Field(..., min_length=1)
    custom_deploy_cmd: str = Field(
        default="",
        description=(
            "Shell command to run when provider == 'custom'. Empty string "
            "is allowed at schema level; /setup-deploy wizard enforces at "
            "write time."
        ),
    )


class CanaryConfig(BaseModel):
    """[canary] TOML block — /canary skill config (D-09, SKILL-17)."""

    window_seconds: int = Field(
        default=300, ge=1, description="Monitoring window after deploy."
    )
    poll_interval_seconds: int = Field(
        default=15, ge=1, description="Polling cadence during the window."
    )
    ci_wait_timeout_seconds: int = Field(
        default=1800,
        ge=1,
        description="Max time to wait for post-deploy CI checks.",
    )


class BenchmarkConfig(BaseModel):
    """[benchmark] TOML block — /benchmark skill config (D-10, SKILL-18)."""

    regression_threshold_ratio: float = Field(
        default=1.5,
        gt=0.0,
        description=(
            "New/baseline timing ratio above which /benchmark flags a "
            "regression (e.g. 1.5 = 50% slower)."
        ),
    )


# ---------------------------------------------------------------------------
# Phase 6 Wave 0 (Plan 06-01 Task 3, A7): optional top-level sub-blocks
# consumed by Phase 6 /learn (MemoryConfig), /design-shotgun
# (DesignShotgunConfig), and the 3 browser skills (BrowserConfig). All
# default to None so existing templates (gstack + 6 bundled) continue to
# parse unchanged.
# ---------------------------------------------------------------------------


class MemoryConfig(BaseModel):
    """[memory] TOML block — TeamMemoryStore tuning (D-06, D-10, MEM-07)."""

    conflict_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description=(
            "BoW cosine threshold above which /learn write flags a conflict "
            "(with sentiment-opposition secondary check). Advisory-only — "
            "the write is never blocked (D-10)."
        ),
    )
    retention_pattern_days: int = Field(
        default=90,
        ge=1,
        description=(
            "TTL for 'pattern' tagged entries before decay_factor drops to "
            "0.2 (MEM-07)."
        ),
    )
    retention_incident_days: int = Field(
        default=180,
        ge=1,
        description="TTL for 'incident' tagged entries (MEM-07).",
    )


class DesignShotgunConfig(BaseModel):
    """[design_shotgun] TOML block — /design-shotgun variant count + board format (D-12)."""

    variant_count: int = Field(
        default=4,
        ge=1,
        le=32,
        description="Number of variants to generate per shotgun iteration.",
    )
    board_format: Literal["html", "markdown"] = Field(
        default="html",
        description="Comparison-board rendering format.",
    )


class BrowserConfig(BaseModel):
    """[browser] TOML block — browser skill defaults (D-01, SKILL-10)."""

    headless: bool = Field(
        default=True,
        description="Whether /browse launches Chromium headless by default.",
    )
    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Default per-action timeout (navigate, click, fill).",
    )
    cookies_dir: str = Field(
        default="",
        description=(
            "Override cookies directory. Empty string = "
            "<data_dir>/teams/<team>/browser/cookies/."
        ),
    )


# ---------------------------------------------------------------------------
# Phase 7 Wave 0 (Plan 07-01 Task 4): concurrency + attention + cost sub-blocks.
# All default to None so existing 6 bundled templates + gstack.toml parse
# unchanged. gstack-opt-in users add e.g. [conductor] max_concurrent_sprints = 20
# to their gstack.toml to override defaults.
# ---------------------------------------------------------------------------


class ConductorConfig(BaseModel):
    """[conductor] TOML block — SprintConductor concurrency caps (D-01/02/03)."""

    max_concurrent_sprints: int = Field(
        default=10,
        ge=1,
        description=(
            "Cap on simultaneously-running sprints per team. Sprints over "
            "cap enter queue_status='queued_capacity'."
        ),
    )
    max_tasks_per_agent: int = Field(
        default=1,
        ge=1,
        description=(
            "Cap on concurrent task dispatches per agent role. Prevents "
            "accidentally-concurrent pm across sibling sprints."
        ),
    )
    max_active_agents: int = Field(
        default=6,
        ge=1,
        description=(
            "Cap on concurrent active agents. Agents over cap sleep-poll "
            "(no Claude keepalive burn)."
        ),
    )
    acquire_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        description=(
            "Grace period for acquiring max_concurrent_sprints before sprint "
            "enters queued state."
        ),
    )


class AttentionConfig(BaseModel):
    """[attention] TOML block — AttentionQueue priority weights (D-05)."""

    urgency_weight: int = Field(
        default=10,
        ge=0,
        description="Multiplier applied to URGENCY bucket (critical=3 .. low=0).",
    )
    blocking_weight: int = Field(
        default=5,
        ge=0,
        description="Added when question.md frontmatter has blocking=true.",
    )
    tag_weights: dict[str, int] = Field(
        default_factory=dict,
        description="Per-tag weight dict (e.g., design=2, security=3).",
    )


class CostConfig(BaseModel):
    """[cost] TOML block — budget + fallback + alarm thresholds (D-10)."""

    budget_usd: float = Field(
        default=100.0,
        ge=0.0,
        description=(
            "Per-team monthly budget. Set to 0 to disable budget tracking."
        ),
    )
    fallback_at_percent: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description=(
            "Percent-of-budget at which model_fallback_ladder kicks in "
            "(opus→sonnet→haiku)."
        ),
    )
    alarm_percent: list[float] = Field(
        default_factory=lambda: [50.0, 80.0, 100.0],
        description=(
            "Budget threshold list; emits BudgetAlarmReached on each crossing."
        ),
    )


class TemplateDef(BaseModel):
    name: str
    description: str = ""
    command: list[str] = ["claude"]
    backend: str = "tmux"
    leader: AgentDef
    agents: list[AgentDef] = []
    tasks: list[TaskDef] = []
    # Phase 3 (Plan 03-02, D-04 / Pattern 4): role authorized to advance_phase;
    # "" means no leader binding (Phase 2 behavior preserved for existing templates).
    leader_role: str = ""
    # Phase 3 (Plan 03-02, D-04): plugin-contributed phase order. Empty list
    # means consult the global PhaseRegistry only (Phase 1 default).
    phases: list[str] = []
    # Phase 3 (Plan 03-02, TEAM-05): per-role model assignments keyed by role,
    # with a reserved "default" key (Pitfall 12 prevention — never default to "quality").
    model_profile: dict[str, str] = {}
    # Phase 3 (Plan 03-02, D-05): per-role memory-directory layout
    # declaration, e.g. {"root": "{data_dir}/teams/{team_name}/memory",
    # "per_role": True}. TeamManager.create_team consults this to pre-create
    # per-role dirs. Renamed from `memory` to `memory_layout` in Plan 06-01
    # Task 3 to free up the `memory` name for the new MemoryConfig
    # sub-block (Rule 3 deviation — field-name collision).
    memory_layout: dict[str, str | bool] = {}
    # Phase 4 (Plan 04-06, §04-CONTEXT D-04): review-phase routing +
    # decorrelation config. Default empty ReviewConfig keeps the 6 existing
    # non-gstack templates BC-safe (they omit [template.review] entirely).
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    # Phase 5 Wave 0 (Plan 05-01 Task 3, A5): optional top-level sub-blocks
    # consumed by Phase 5 slash-skills. All default to None so existing
    # templates (gstack + 6 bundled) continue to parse unchanged.
    ship: ShipConfig | None = None
    deploy: DeployConfig | None = None
    canary: CanaryConfig | None = None
    benchmark: BenchmarkConfig | None = None
    # Phase 6 Wave 0 (Plan 06-01 Task 3, A7): optional top-level sub-blocks
    # consumed by Phase 6 /learn (memory), /design-shotgun, and the 3
    # browser skills. Default None so existing templates parse unchanged.
    memory: MemoryConfig | None = None
    design_shotgun: DesignShotgunConfig | None = None
    browser: BrowserConfig | None = None
    # Phase 7 Wave 0 (Plan 07-01 Task 4): concurrency + attention + cost
    # sub-blocks. Default None so existing templates parse unchanged.
    conductor: ConductorConfig | None = None
    attention: AttentionConfig | None = None
    cost: CostConfig | None = None


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_BUILTIN_DIR = Path(__file__).parent
_USER_DIR = Path.home() / ".clawteam" / "templates"


# ---------------------------------------------------------------------------
# Variable substitution helper
# ---------------------------------------------------------------------------

class _SafeDict(dict):
    """dict subclass that keeps unknown {placeholders} intact."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_task(task: str, **variables: str) -> str:
    """Replace {goal}, {team_name}, {agent_name} etc. in task text."""
    return task.format_map(_SafeDict(**variables))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _parse_toml(path: Path) -> TemplateDef:
    """Parse a TOML template file into a TemplateDef."""
    with open(path, "rb") as f:
        raw = tomllib.load(f)

    tmpl = raw.get("template", {})

    # Parse leader
    leader_data = tmpl.get("leader", {})
    leader = AgentDef(**leader_data)

    # Parse agents
    agents = [AgentDef(**a) for a in tmpl.get("agents", [])]

    # Parse tasks
    tasks = [TaskDef(**t) for t in tmpl.get("tasks", [])]

    # Phase 4 (Plan 04-06, §04-CONTEXT D-04 / A5): parse optional
    # [template.review] + [[template.review.rules]]. BC-safe: if no review
    # block is declared, ReviewConfig() defaults apply (empty rules,
    # sycophancy_threshold=0.9).
    review_tmpl = tmpl.get("review", {}) or {}
    raw_rules = review_tmpl.get("rules", []) or []
    review_config = ReviewConfig(
        sycophancy_threshold=float(review_tmpl.get("sycophancy_threshold", 0.9)),
        rules=[ReviewRule(**r) for r in raw_rules],
    )

    # Phase 5 Wave 0 (Plan 05-01 Task 3, A5): optional TOP-LEVEL sub-blocks
    # (NOT under [template]). Matches the §05-CONTEXT Specifics layout:
    #   [ship]        — /ship thresholds
    #   [deploy]      — /land-and-deploy target
    #   [canary]      — /canary monitoring window
    #   [benchmark]   — /benchmark regression threshold
    # Absent blocks map to None (BC-safe for gstack + 6 bundled templates).
    ship_raw = raw.get("ship")
    deploy_raw = raw.get("deploy")
    canary_raw = raw.get("canary")
    benchmark_raw = raw.get("benchmark")

    # Phase 6 Wave 0 (Plan 06-01 Task 3, A7): optional TOP-LEVEL sub-blocks
    # consumed by Phase 6 /learn ([memory] — TeamMemoryStore tuning),
    # /design-shotgun ([design_shotgun]), and the 3 browser skills
    # ([browser]). Absent blocks map to None (BC-safe for gstack + 6
    # bundled templates — none of which declare these blocks today).
    memory_raw = raw.get("memory")
    design_shotgun_raw = raw.get("design_shotgun")
    browser_raw = raw.get("browser")

    # Phase 7 Wave 0 (Plan 07-01 Task 4): optional TOP-LEVEL sub-blocks
    # consumed by SprintConductor concurrency caps ([conductor]),
    # AttentionQueue priority ([attention]), and cost tracker/fallback
    # ([cost]). Absent blocks map to None (BC-safe for gstack + 6 bundled
    # templates — none of which declare these blocks today).
    conductor_raw = raw.get("conductor")
    attention_raw = raw.get("attention")
    cost_raw = raw.get("cost")

    return TemplateDef(
        name=tmpl.get("name", path.stem),
        description=tmpl.get("description", ""),
        command=tmpl.get("command", ["claude"]),
        backend=tmpl.get("backend", "tmux"),
        leader=leader,
        agents=agents,
        tasks=tasks,
        # Phase 3 (Plan 03-02): strict-additive extensions. Each .get(...) uses
        # an empty default so existing templates parse with Phase 2 semantics.
        leader_role=tmpl.get("leader_role", ""),
        phases=tmpl.get("phases", []),
        model_profile=tmpl.get("model_profile", {}),
        # Plan 06-01 Task 3: field renamed `memory` -> `memory_layout`
        # to free up `memory` for MemoryConfig. gstack.toml still ships
        # `[template.memory]` (legacy TOML key), so read that key first
        # and fall back to `memory_layout` for future templates that
        # want to use the new spelling.
        memory_layout=tmpl.get("memory", tmpl.get("memory_layout", {})),
        # Phase 4 (Plan 04-06): review-phase config. Default empty when the
        # template declares no [template.review] block.
        review=review_config,
        # Phase 5 Wave 0 (Plan 05-01 Task 3): top-level optional sub-blocks.
        ship=ShipConfig(**ship_raw) if ship_raw is not None else None,
        deploy=DeployConfig(**deploy_raw) if deploy_raw is not None else None,
        canary=CanaryConfig(**canary_raw) if canary_raw is not None else None,
        benchmark=(
            BenchmarkConfig(**benchmark_raw) if benchmark_raw is not None else None
        ),
        # Phase 6 Wave 0 (Plan 06-01 Task 3): top-level optional sub-blocks.
        memory=MemoryConfig(**memory_raw) if memory_raw is not None else None,
        design_shotgun=(
            DesignShotgunConfig(**design_shotgun_raw)
            if design_shotgun_raw is not None
            else None
        ),
        browser=BrowserConfig(**browser_raw) if browser_raw is not None else None,
        # Phase 7 Wave 0 (Plan 07-01 Task 4): top-level optional sub-blocks.
        conductor=(
            ConductorConfig(**conductor_raw) if conductor_raw is not None else None
        ),
        attention=(
            AttentionConfig(**attention_raw) if attention_raw is not None else None
        ),
        cost=CostConfig(**cost_raw) if cost_raw is not None else None,
    )


def load_template(name: str) -> TemplateDef:
    """Load a template by name.

    Search order: user templates (~/.clawteam/templates/) first,
    then built-in templates (clawteam/templates/).
    """
    filename = f"{name}.toml"

    # User templates take priority
    user_path = _USER_DIR / filename
    if user_path.is_file():
        return _parse_toml(user_path)

    # Built-in templates
    builtin_path = _BUILTIN_DIR / filename
    if builtin_path.is_file():
        return _parse_toml(builtin_path)

    raise FileNotFoundError(
        f"Template '{name}' not found. "
        f"Searched: {_USER_DIR}, {_BUILTIN_DIR}"
    )


def list_templates() -> list[dict[str, str]]:
    """List all available templates (user + builtin, user overrides builtin)."""
    seen: dict[str, dict[str, str]] = {}

    # Built-in templates first (can be overridden)
    if _BUILTIN_DIR.is_dir():
        for p in sorted(_BUILTIN_DIR.glob("*.toml")):
            try:
                tmpl = _parse_toml(p)
                seen[tmpl.name] = {
                    "name": tmpl.name,
                    "description": tmpl.description,
                    "source": "builtin",
                }
            except Exception:
                continue

    # User templates override
    if _USER_DIR.is_dir():
        for p in sorted(_USER_DIR.glob("*.toml")):
            try:
                tmpl = _parse_toml(p)
                seen[tmpl.name] = {
                    "name": tmpl.name,
                    "description": tmpl.description,
                    "source": "user",
                }
            except Exception:
                continue

    return list(seen.values())
