"""Team template loader — load TOML templates for one-command team launch."""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel

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
    # Phase 3 (Plan 03-02, D-05): memory layout declaration, e.g.
    # {"root": "{data_dir}/teams/{team_name}/memory", "per_role": True}.
    # TeamManager.create_team consults this to pre-create per-role dirs.
    memory: dict[str, str | bool] = {}


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
        memory=tmpl.get("memory", {}),
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
