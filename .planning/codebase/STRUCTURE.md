# Codebase Structure

**Analysis Date:** 2026-04-15

## Directory Layout

```
ClawTeam-gstack/
├── clawteam/                 # Main Python package (framework-agnostic multi-agent harness)
│   ├── __init__.py           # Package version (`__version__ = "0.3.0"`)
│   ├── __main__.py           # `python -m clawteam` entry, delegates to CLI app
│   ├── config.py             # User config loader
│   ├── fileutil.py           # Atomic writes + file locking primitives
│   ├── identity.py           # AgentIdentity + CLAWTEAM_*/OH_*/CLAUDE_CODE_* env helpers
│   ├── paths.py              # Identifier validation + path traversal guard
│   ├── timefmt.py            # Timestamp formatting
│   ├── board/                # Activity board + Gource-style event renderer
│   ├── cli/                  # Typer CLI (user-facing)
│   ├── events/               # Sync EventBus + event type registry + hooks
│   ├── harness/              # Plan → execute → verify orchestration engine
│   ├── mcp/                  # FastMCP server + tool wrappers
│   ├── plugins/              # HarnessPlugin ABC + manager + example plugin
│   ├── spawn/                # CLI adapters + tmux/subprocess/wsh backends
│   ├── store/                # Generic filesystem KV / JSON store
│   ├── team/                 # Team lifecycle, models, mailbox, routing, costs
│   ├── templates/            # TOML harness templates (code-review, hedge-fund, etc.)
│   ├── transport/            # File + P2P (ZeroMQ) message transports
│   └── workspace/            # Per-agent git worktree manager
├── tests/                    # Flat pytest layout (one test_*.py per module)
├── docs/                     # Site assets + transport-architecture.md + skills docs
├── website/                  # Vite site (src/, index.html, vite.config.mjs)
├── skills/                   # Packaged skills (clawteam/, agents/, references/)
├── .agents/skills/           # Project-local agent skills (clawteam-dev, frontend-design)
├── .claude/                  # Claude Code project config
├── .github/workflows/        # CI workflows
├── .planning/                # GSD planning outputs (this file lives here)
├── assets/                   # Logos / images referenced by README
├── scripts/                  # Shell helpers (openclaw_worker.sh)
├── pyproject.toml            # Hatchling build + Typer/Pydantic/Rich/MCP deps
├── package.json              # Website tooling only
├── package-lock.json
├── skills-lock.json          # Lockfile for the skills/ bundle
├── README.md / README_CN.md / README_KR.md
├── ROADMAP.md
└── LICENSE
```

## Directory Purposes

**`clawteam/cli/`:**
- Purpose: Typer-based CLI entry point.
- Contains: `commands.py` (~4.6k LOC — the full command surface), `__init__.py`.
- Key files: `clawteam/cli/commands.py::app` (bound to console script `clawteam`).

**`clawteam/spawn/`:**
- Purpose: Launch and track external AI CLI processes.
- Key files:
  - `base.py` — `SpawnBackend` ABC.
  - `__init__.py` — backend registry + `get_backend()` factory.
  - `adapters.py` — `NativeCliAdapter`, `PreparedCommand`, per-CLI detectors.
  - `tmux_backend.py` (756 LOC) — primary interactive backend.
  - `subprocess_backend.py` (151 LOC) — headless backend.
  - `wsh_backend.py` (418 LOC) — Wave Terminal backend.
  - `cli_env.py` — clawteam binary resolution + Docker runtime bundling.
  - `command_validation.py` — normalization + docker-wrapping helpers.
  - `keepalive.py` — crash-restart shell wrappers + `build_resume_command`.
  - `registry.py` — per-team spawn registry with liveness checks.
  - `sessions.py`, `presets.py`, `profiles.py`, `prompt.py`, `wsh_rpc.py`.

**`clawteam/harness/`:**
- Purpose: Plan-then-execute workflow engine.
- Key files: `orchestrator.py` (top-level), `phases.py` (`PhaseRunner`, gates), `conductor.py`, `strategies.py`, `contracts.py`, `contract_executor.py`, `roles.py`, `prompts.py`, `artifacts.py`, `context.py`, `context_recovery.py`, `spawner.py`, `exit_journal.py`.

**`clawteam/team/`:**
- Purpose: Team/member/task/mailbox domain.
- Key files: `manager.py` (`TeamManager`), `models.py` (`TeamConfig`, `TeamMember`, enums, `get_data_dir`), `mailbox.py`, `router.py`, `routing_policy.py`, `costs.py`, `lifecycle.py`, `snapshot.py`, `plan.py`, `tasks.py`, `waiter.py`, `watcher.py`.

**`clawteam/mcp/`:**
- Purpose: Expose domain operations to agents via MCP.
- Key files: `server.py` (FastMCP auto-registration), `helpers.py` (`translate_error`), `tools/` (board, cost, mailbox, plan, task, team, workspace), `__main__.py`.

**`clawteam/events/`:**
- Purpose: In-process pub/sub.
- Key files: `bus.py` (`EventBus`, event type registry), `types.py` (event dataclasses), `hooks.py`, `global_bus.py`.

**`clawteam/plugins/`:**
- Purpose: Extension framework.
- Key files: `base.py` (`HarnessPlugin` ABC), `manager.py` (discovery/loading), `ralph_loop_plugin.py` (example).

**`clawteam/transport/`:**
- Purpose: Message transport abstraction.
- Key files: `base.py` (`Transport` ABC), `file.py` (default), `p2p.py` (ZeroMQ, extra), `claimed.py`, `__init__.py` (factory).

**`clawteam/workspace/`:**
- Purpose: Per-agent git worktree management.
- Key files: `manager.py` (`get_workspace_manager`), `git.py`, `conflicts.py`, `context.py`, `models.py`.

**`clawteam/board/`:**
- Purpose: Live activity visualization.
- Key files: `server.py`, `collector.py`, `renderer.py`, `gource.py`, `static/` (HTML/JS/CSS).

**`clawteam/store/`:**
- Purpose: Generic JSON-file KV store used by higher layers.
- Key files: `base.py`, `file.py`.

**`clawteam/templates/`:**
- Purpose: Packaged harness recipes (TOML).
- Contents: `harness-default.toml`, `software-dev.toml`, `code-review.toml`, `research-paper.toml`, `hedge-fund.toml`, `strategy-room.toml`.

**`tests/`:**
- Purpose: Flat pytest suite — one `test_<module>.py` per feature area (e.g. `test_adapters.py`, `test_identity.py`, `test_spawn_backends.py`, `test_runtime_routing.py`, `test_mcp_tools.py`).
- Shared fixtures in `tests/conftest.py`.

**`docs/`:**
- Purpose: GitHub Pages site + additional architecture notes.
- Key files: `index.html`, `CNAME`, `transport-architecture.md`, `site-assets/`, `skills/clawteam/`.

**`website/`:**
- Purpose: Vite marketing site. Independent of the Python package (has its own `package.json`).

**`skills/` and `.agents/skills/`:**
- Purpose: Packaged and project-local agent skill bundles (SKILL.md + references).

**`scripts/`:**
- Purpose: Auxiliary shell helpers (currently `openclaw_worker.sh`).

## Key File Locations

**Entry Points:**
- `clawteam/cli/commands.py::app` — main CLI (console script `clawteam`).
- `clawteam/__main__.py` — `python -m clawteam`.
- `clawteam/mcp/server.py::main` — console script `clawteam-mcp`.
- `clawteam/mcp/__main__.py` — `python -m clawteam.mcp`.

**Configuration:**
- `pyproject.toml` — build, deps, scripts, ruff, pytest config.
- `clawteam/config.py` — user config loader.
- `~/.clawteam/config.toml` (runtime) — user config file.
- `clawteam/templates/*.toml` — harness recipes.
- `skills-lock.json` — skills bundle lockfile.

**Core Logic:**
- `clawteam/spawn/adapters.py` — per-CLI command preparation.
- `clawteam/spawn/tmux_backend.py` — primary spawn backend.
- `clawteam/spawn/registry.py` — agent liveness tracking.
- `clawteam/identity.py` — AgentIdentity + env fallback chain.
- `clawteam/harness/orchestrator.py` — harness top-level.
- `clawteam/harness/phases.py` — phase gates.
- `clawteam/team/manager.py` — team CRUD.
- `clawteam/team/models.py::get_data_dir` — data directory anchor.
- `clawteam/events/bus.py` — event bus.

**Testing:**
- `tests/conftest.py` — fixtures.
- `tests/test_adapters.py`, `tests/test_spawn_backends.py`, `tests/test_runtime_routing.py` — spawn layer coverage.
- `tests/test_identity.py` — identity env helper coverage.
- `tests/test_harness.py`, `tests/test_lifecycle.py` — harness coverage.
- `tests/test_mcp_server.py`, `tests/test_mcp_tools.py` — MCP surface.

## Naming Conventions

**Files:**
- Pattern: `snake_case.py`.
- Backends named `<name>_backend.py` (`tmux_backend.py`, `subprocess_backend.py`, `wsh_backend.py`).
- Tests mirror module names: `tests/test_<module>.py`.
- Plugins end with `_plugin.py` (`ralph_loop_plugin.py`).

**Directories:**
- Lowercase single-word domain names (`spawn`, `team`, `harness`, `events`, `transport`, `workspace`, `store`, `board`, `plugins`, `templates`, `mcp`, `cli`).

**Classes:**
- `PascalCase`. ABCs suffixed with their role (`SpawnBackend`, `Transport`, `HarnessPlugin`, `PhaseGate`).
- Concrete backends end with `Backend` (`TmuxBackend`, `SubprocessBackend`, `WshBackend`).
- Pydantic models use domain nouns (`TeamConfig`, `TeamMember`).

**Functions:**
- `snake_case`. Predicates prefixed with `is_` (`is_claude_command`, `is_nanobot_command`). Factories: `get_backend`, `get_transport`, `get_workspace_manager`. Builders: `build_spawn_path`, `build_docker_clawteam_runtime`, `build_keepalive_shell_command`.
- Private helpers: leading underscore (`_env`, `_pid_alive`, `_teams_root`).

**Environment variables:**
- Canonical: `CLAWTEAM_*` (`CLAWTEAM_AGENT_ID`, `CLAWTEAM_TEAM_NAME`, `CLAWTEAM_DATA_DIR`, `CLAWTEAM_WORKSPACE_DIR`, `CLAWTEAM_USER`, `CLAWTEAM_TRANSPORT`, `CLAWTEAM_BIN`).
- Legacy accepted (via `identity._env`): `OH_*`, `CLAUDE_CODE_*`.

**Identifiers (team/member names):**
- Regex `^[A-Za-z0-9._-]+$` enforced by `clawteam/paths.py::validate_identifier`.

## Where to Add New Code

**New spawn backend:**
- Implementation: `clawteam/spawn/<name>_backend.py` subclassing `SpawnBackend` (`clawteam/spawn/base.py`).
- Wiring: add an elif branch in `clawteam/spawn/__init__.py::get_backend` or call `register_backend()` from a plugin.
- Tests: `tests/test_spawn_backends.py` (extend) or a dedicated `tests/test_<name>_backend.py`.

**Support a new AI CLI (adapter):**
- Add an `is_<cli>_command` predicate in `clawteam/spawn/adapters.py`.
- Add a branch inside `NativeCliAdapter.prepare_command` for CLI-specific flags.
- Add to `is_interactive_cli` if the CLI is interactive.
- Tests: `tests/test_adapters.py`.

**New CLI subcommand:**
- Add a Typer command to `clawteam/cli/commands.py` (guard global state with `_json_output` / `_data_dir`).
- Tests: `tests/test_cli_commands.py` or `tests/test_spawn_cli.py`.

**New MCP tool:**
- Implementation: a plain function in the right `clawteam/mcp/tools/<area>.py` module.
- Export it in `clawteam/mcp/tools/__init__.py::TOOL_FUNCTIONS` so `server.py` auto-registers it.
- Tests: `tests/test_mcp_tools.py`.

**New harness phase/gate:**
- Gate: subclass `PhaseGate` in `clawteam/harness/phases.py` or register from a plugin (`HarnessPlugin.contribute_gates`).
- Role/prompt: extend `clawteam/harness/roles.py` or `prompts.py`.

**New plugin:**
- Implementation: `clawteam/plugins/<name>_plugin.py` subclassing `HarnessPlugin` (`clawteam/plugins/base.py`).
- Wiring: loaded through `clawteam/plugins/manager.py`.

**New transport:**
- Implementation: `clawteam/transport/<name>.py` subclassing `Transport` (`clawteam/transport/base.py`).
- Wiring: branch in `clawteam/transport/__init__.py::get_transport` or `register_transport()` from a plugin.

**New team/task model field:**
- Edit the Pydantic model in `clawteam/team/models.py`. Persisted data is JSON via `model_dump_json(by_alias=True)` so prefer additive/optional fields for backward compatibility.

**New env var:**
- Canonical name is `CLAWTEAM_<PURPOSE>`. If replacing an `OH_*` or `CLAUDE_CODE_*` var, route the lookup through `clawteam/identity.py::_env` or `_env_bool` for fallback.

**Shared utility / path helper:**
- Filesystem-safe joins: use `clawteam/paths.py::ensure_within_root` rooted at `get_data_dir()` (`clawteam/team/models.py`).
- Atomic writes / locks: `clawteam/fileutil.py::atomic_write_text`, `file_locked`.

**New harness template:**
- Drop a TOML file into `clawteam/templates/` following the shape of `harness-default.toml`.

## Special Directories

**`~/.clawteam/` (runtime, not in repo):**
- Purpose: Default data directory. Set via `CLAWTEAM_DATA_DIR` to override.
- Subdirs (created on demand by `get_data_dir()` consumers):
  - `teams/<team>/config.json` — team state.
  - `teams/<team>/spawn_registry.json` — live agent registry.
  - `teams/<team>/inboxes/<user>_<name>/` — per-member mailboxes.
  - `tasks/<team>/` — task store.
  - `costs/<team>/` — cost accounting.
  - `sessions/<team>/` — session state.
  - `harness/<team>/<harness_id>/state.json` — harness runs.
  - `runtime/docker/clawteam-bootstrap.sh` — Docker nanobot bootstrap script.

**`.planning/`:**
- Purpose: GSD workflow outputs (codebase maps, phase plans).
- Generated: Yes (by `/gsd-*` commands).
- Committed: Varies by workflow; currently tracked.

**`clawteam/templates/`:**
- Purpose: Declarative harness recipes distributed with the package.
- Packaged: Yes (via `pyproject.toml` hatch wheel target).

**`website/`:**
- Purpose: Standalone Vite site — not imported by the Python package.
- Has independent `package.json` and build.

**`tests/`:**
- Layout: Flat (no subdirectories). One test file per domain module.

---

*Structure analysis: 2026-04-15*
