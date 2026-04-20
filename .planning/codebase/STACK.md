# Technology Stack

**Analysis Date:** 2026-04-15

## Languages

**Primary:**
- Python >=3.10 (targets 3.10, 3.11, 3.12) — the `clawteam` CLI, MCP server, orchestration harness, spawn backends, transports, and team models live under `clawteam/`
- JavaScript (ES modules) / JSX — marketing/docs website under `website/` (`website/src/`, `website/vite.config.mjs`)

**Secondary:**
- Shell (POSIX sh) — docker bootstrap script emitted by `clawteam/spawn/cli_env.py` and `scripts/openclaw_worker.sh`
- HTML / static assets — `clawteam/board/static/index.html` (Web UI dashboard) and `docs/index.html` (GitHub Pages landing)

## Runtime

**Environment:**
- CPython 3.10+ for the CLI/library (`pyproject.toml` `requires-python = ">=3.10"`)
- Node.js with Vite 5 dev server for the website workspace (`package.json`)

**Package Manager:**
- Python: `hatchling` build backend, installable via `pip` (see `[build-system]` in `pyproject.toml`)
- JS: `npm` (lockfile `package-lock.json` present)

**Lockfiles:**
- `package-lock.json` present for the website workspace
- `skills-lock.json` pins project skill revisions
- No Python lockfile — dependencies pinned via ranges in `pyproject.toml`

## Frameworks

**Core (Python CLI):**
- `typer` >=0.12,<1.0 — CLI framework (entry point `clawteam.cli.commands:app` in `clawteam/cli/commands.py`)
- `pydantic` >=2.0,<3.0 — data models for config, team state, workspaces (`clawteam/config.py`, `clawteam/team/models.py`, `clawteam/workspace/models.py`)
- `rich` >=13.0,<15.0 — terminal rendering (used by CLI and `clawteam/board/renderer.py`)
- `questionary` >=2.0.1,<3.0 — interactive CLI prompts
- `mcp` >=1.0 — official Model Context Protocol SDK; exposes `FastMCP` server in `clawteam/mcp/server.py` and tools under `clawteam/mcp/tools/`

**Core (Website):**
- `react` ^18.3.1 + `react-dom` ^18.3.1 (`website/src/`)
- `vite` ^5.4.11 with `@vitejs/plugin-react` ^4.3.4 (`website/vite.config.mjs`)

**Testing:**
- `pytest` >=9.0,<10.0 — test runner (`tests/` directory, config in `pyproject.toml` `[tool.pytest.ini_options]`)
- No JS test harness configured

**Build / Dev:**
- `hatchling` — Python wheel/sdist build (`pyproject.toml` `[tool.hatch.build.targets.*]`)
- `ruff` >=0.1 — linting / import sorting (`[tool.ruff]` in `pyproject.toml`, `line-length = 100`, `target-version = "py310"`, selects `E,F,I,N,W`)
- `vite build` — website bundling

## Key Dependencies

**Critical (runtime):**
- `typer` — dispatches every user-facing CLI command in `clawteam/cli/commands.py`
- `pydantic` — schema for `AgentProfile`, `AgentPreset`, `ClawTeamConfig`, team/workspace models
- `mcp` (FastMCP) — serves the `clawteam-mcp` binary registered in `[project.scripts]`
- `rich` — board/TUI output and progress rendering

**Optional:**
- `pyzmq` >=25.0,<27.0 (extra `p2p`) — ZeroMQ PUSH/PULL transport in `clawteam/transport/p2p.py`
- `tomli` >=2.0 on Python <3.11 — TOML parsing fallback for team templates

**Dev-only:**
- `pytest` — test execution
- `ruff` — lint/format

## Configuration

**Environment:**
- `CLAWTEAM_DATA_DIR` — overrides default `~/.clawteam` data root (`clawteam/team/models.py:get_data_dir`)
- Agent auth secrets read from standard provider vars: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `MOONSHOT_API_KEY`, `DEEPSEEK_API_KEY`, `ZHIPU_API_KEY`, `DASHSCOPE_API_KEY`, `MINIMAX_API_KEY`, `OPENROUTER_API_KEY` (defined in `clawteam/spawn/presets.py`)
- Identity envs (`clawteam/identity.py`): `CLAWTEAM_*` primary, with legacy `OH_*` and `CLAUDE_CODE_*` aliases
- Docker runtime hints: `CLAWTEAM_DOCKER_HOST_WRAPPER`, `CLAWTEAM_DOCKER_SOURCE_ROOT` (`clawteam/spawn/cli_env.py`)

**Persistent config:**
- User config persisted via `clawteam/config.py` (`ClawTeamConfig` pydantic model, JSON-on-disk via `clawteam/fileutil.py:atomic_write_text`)
- Team templates shipped in `clawteam/templates/*.toml` (`code-review`, `harness-default`, `hedge-fund`, `research-paper`, `software-dev`, `strategy-room`)

**Build:**
- `pyproject.toml` — Python project + tooling config (hatch, ruff, pytest)
- `package.json` + `website/vite.config.mjs` — website build
- `skills-lock.json` — pinned ClawTeam skill set

## Platform Requirements

**Development:**
- POSIX-like environment (tmux, git, optional docker/podman, optional wsh for WaveTerminal)
- Python 3.10+ with `pip`
- Node 18+ (Vite 5) for website work

**Production:**
- CLI installed as the `clawteam` and `clawteam-mcp` scripts (`[project.scripts]` in `pyproject.toml`)
- Data directory writable at `$CLAWTEAM_DATA_DIR` or `~/.clawteam`
- Optional: `tmux`, `gource`, `docker`/`podman`, `wsh` (WaveTerminal/TideTerm) depending on spawn backend

---

*Stack analysis: 2026-04-15*
