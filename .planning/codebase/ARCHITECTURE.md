# Architecture

**Analysis Date:** 2026-04-15

## Pattern Overview

**Overall:** Modular, layered Python package exposing a Typer CLI and an MCP server over a shared domain core. The system is a **framework-agnostic multi-agent coordination harness**: it spawns external AI coding CLIs (Claude, Codex, Gemini, Kimi, Qwen, OpenCode, OpenClaw, Nanobot, pi) as team members and coordinates them through file-backed state, a pluggable transport, and an event bus.

**Key Characteristics:**
- **Adapter + Backend pattern** for spawning: one adapter normalizes per-CLI command syntax (`clawteam/spawn/adapters.py`), while interchangeable backends (tmux, subprocess, wsh) own process lifecycle.
- **Registry + factory** pattern for pluggable subsystems: spawn backends (`clawteam/spawn/__init__.py`), transports (`clawteam/transport/__init__.py`), event types (`clawteam/events/bus.py`), plugins (`clawteam/plugins/manager.py`).
- **Filesystem-backed state** under `~/.clawteam/` (overridable via `CLAWTEAM_DATA_DIR`). All persistence uses atomic writes + file locking (`clawteam/fileutil.py`) and validated path joining (`clawteam/paths.py::ensure_within_root`).
- **Event-driven harness**: `HarnessOrchestrator` drives phases (plan → execute → verify) through `PhaseGate`s; plugins subscribe on a central `EventBus`.
- **Two public surfaces**: a Typer CLI (`clawteam.cli.commands:app`) and an MCP (Model Context Protocol) server (`clawteam.mcp.server:main`) exposing the same domain operations as tools.

## Layers

**CLI / Entry Layer:**
- Purpose: Human-facing command surface and module entry point.
- Location: `clawteam/cli/commands.py`, `clawteam/__main__.py`
- Contains: Typer app, argument parsing, rich console output, JSON output toggle, data-dir override plumbing.
- Depends on: every domain layer (spawn, team, harness, workspace, events, store).
- Used by: end users and the `clawteam` console script declared in `pyproject.toml`.

**MCP Tool Layer:**
- Purpose: Expose domain operations as MCP tools for agent consumption.
- Location: `clawteam/mcp/server.py`, `clawteam/mcp/tools/` (board, cost, mailbox, plan, task, team, workspace), `clawteam/mcp/helpers.py`
- Pattern: Each tool module exports plain functions; `server.py` auto-registers them via `FastMCP.tool()` with a uniform `translate_error` wrapper.
- Used by: agents running inside the harness (via the `clawteam-mcp` console script).

**Harness Orchestration Layer:**
- Purpose: Plan-then-execute multi-agent workflow engine with phase gates.
- Location: `clawteam/harness/`
  - `orchestrator.py`: top-level controller (`HarnessOrchestrator`).
  - `phases.py`: `PhaseState`, `PhaseRunner`, `PhaseGate` subclasses (`ArtifactRequiredGate`, `AllTasksCompleteGate`, `HumanApprovalGate`).
  - `conductor.py`, `strategies.py`: execution strategies.
  - `contracts.py`, `contract_executor.py`: role contracts.
  - `roles.py`, `prompts.py`: default roles + prompt builders.
  - `artifacts.py`: per-run artifact store.
  - `context.py`, `context_recovery.py`: harness context + recovery.
  - `spawner.py`: harness-aware agent spawning.
  - `exit_journal.py`: agent exit records.
- Depends on: team, spawn, events, store.

**Team / Coordination Layer:**
- Purpose: Team lifecycle, membership, tasks, mailboxes, routing, costs.
- Location: `clawteam/team/`
  - `manager.py`: `TeamManager` (team CRUD, inbox provisioning).
  - `models.py`: Pydantic models (`TeamConfig`, `TeamMember`, enums, `get_data_dir`).
  - `mailbox.py`, `router.py`, `routing_policy.py`: message routing.
  - `tasks.py`, `plan.py`, `waiter.py`, `watcher.py`: task lifecycle & waits.
  - `costs.py`: per-agent token/cost accounting.
  - `lifecycle.py`, `snapshot.py`: team state transitions + snapshots.

**Spawn Layer:**
- Purpose: Launch external CLI agents under a chosen process host.
- Location: `clawteam/spawn/`
  - `base.py`: `SpawnBackend` ABC with `spawn()` + `list_running()`.
  - `__init__.py`: backend registry + `get_backend("tmux"|"subprocess"|"wsh")`.
  - `adapters.py`: `NativeCliAdapter` and `is_*_command` detectors for each CLI family; produces `PreparedCommand` (`normalized_command`, `final_command`, `post_launch_prompt`).
  - `tmux_backend.py`, `subprocess_backend.py`, `wsh_backend.py`: concrete backends.
  - `cli_env.py`: locates the current `clawteam` binary (`resolve_clawteam_executable`), builds `PATH` for spawned children, and assembles Docker runtime bundles (`DockerClawteamRuntime`) for containerized `nanobot` launches.
  - `command_validation.py`: spawn command normalization, docker wrapper detection, `ensure_docker_*` helpers.
  - `keepalive.py`: builds shell wrappers that auto-resume a crashed CLI.
  - `registry.py`: persistent per-team JSON registry of spawned agents with liveness (`_tmux_pane_alive`, `_pid_alive`, `_wsh_block_alive`) and stop semantics.
  - `sessions.py`, `profiles.py`, `presets.py`, `prompt.py`, `wsh_rpc.py`.

**Transport Layer:**
- Purpose: Inter-agent message delivery.
- Location: `clawteam/transport/`
  - `base.py`: `Transport` ABC.
  - `file.py`: default file-backed transport.
  - `p2p.py`: optional ZeroMQ transport (extra `p2p`).
  - `claimed.py`: claim-tracking helpers.
  - `__init__.py`: `get_transport()` factory + registry.

**Events & Plugins Layer:**
- Purpose: Pub/sub event bus and extension points.
- Location: `clawteam/events/bus.py` (sync `EventBus` with priority subscriptions, async pool, event type registry), `clawteam/events/types.py`, `clawteam/events/hooks.py`, `clawteam/events/global_bus.py`.
- `clawteam/plugins/`: `HarnessPlugin` ABC (`base.py`), discovery/loading (`manager.py`), example (`ralph_loop_plugin.py`).

**Workspace Layer:**
- Purpose: Per-agent git worktree management.
- Location: `clawteam/workspace/manager.py` (`get_workspace_manager`, `cleanup_team`), `git.py`, `conflicts.py`, `context.py`, `models.py`.

**Board / Visualization Layer:**
- Purpose: Activity board + Gource-style event renderer.
- Location: `clawteam/board/` (`server.py`, `collector.py`, `renderer.py`, `gource.py`, `static/`).

**Store Layer:**
- Purpose: Generic filesystem KV / JSON store used by higher layers.
- Location: `clawteam/store/base.py`, `clawteam/store/file.py`.

**Shared Utilities:**
- `clawteam/identity.py`: `AgentIdentity` dataclass with `from_env` / `to_env`; central place for the `CLAWTEAM_*` → `OH_*` → `CLAUDE_CODE_*` env key fallback (`_env`, `_env_bool`).
- `clawteam/config.py`: user config loader (`~/.clawteam/config.toml`-style).
- `clawteam/paths.py`: identifier validation and root-confined path joins.
- `clawteam/fileutil.py`: atomic writes, file locking.
- `clawteam/timefmt.py`: timestamp formatting.

## Data Flow

**Spawning an agent (primary hot path):**

1. User invokes `clawteam spawn ...` → `clawteam/cli/commands.py` parses args.
2. `get_backend(name)` in `clawteam/spawn/__init__.py` returns a `TmuxBackend` / `SubprocessBackend` / `WshBackend`.
3. Backend calls `NativeCliAdapter.prepare_command()` (`clawteam/spawn/adapters.py`) which:
   - Normalizes the command via `normalize_spawn_command`.
   - Detects the CLI family (`is_claude_command`, `is_codex_command`, `is_nanobot_command`, etc.).
   - Appends family-specific flags (`--dangerously-skip-permissions`, `--yolo`, `-p`, `-w`, `--session`, `-m`).
   - For dockerized `nanobot`, injects workspace mount, data-dir mount, `DockerClawteamRuntime` mounts/env (`cli_env.build_docker_clawteam_runtime`), and API-key passthrough.
   - Returns a `PreparedCommand` with optional `post_launch_prompt` for interactive CLIs.
4. Backend builds the child environment: `AgentIdentity.to_env()` (from `clawteam/identity.py`) + `CLAWTEAM_DATA_DIR`, `CLAWTEAM_WORKSPACE_DIR`, `PATH` augmented by `cli_env.build_spawn_path`.
5. Backend launches the process (tmux window / subprocess / wsh block) optionally wrapped in a keepalive shell from `clawteam/spawn/keepalive.py`.
6. `clawteam/spawn/registry.py::register_agent` writes `~/.clawteam/teams/<team>/spawn_registry.json` (atomic + locked) with backend, tmux target / block id / pid.

**Liveness & recovery:**
- `registry.is_agent_alive()` dispatches per backend: `_tmux_pane_alive` (checks `pane_dead` + shell fallback), `_pid_alive` (POSIX `kill 0` / Windows `OpenProcess`), `_wsh_block_alive` (queries `wsh blocks list --json`).
- Zombie detection via `list_zombie_agents(team, max_hours)`.

**Identity propagation:**
- `AgentIdentity.from_env()` reads `CLAWTEAM_*` first, then legacy `OH_*`, then `CLAUDE_CODE_*`, via `_env()` with flexible signatures (preserves backward compatibility for existing callers).
- `AgentIdentity.to_env()` exports both `CLAWTEAM_*` and `OH_*` aliases so downstream agents of either generation see the same identity.

**Harness run:**
1. `HarnessOrchestrator(team, goal, cli, agent_count, phases, phase_roles, human_gates)` constructs `PhaseState` + `PhaseRunner` and registers default gates (`ArtifactRequiredGate(["spec.md"])` on PLAN, `AllTasksCompleteGate()` on VERIFY, `HumanApprovalGate` per configured phase).
2. `start()` persists state under `~/.clawteam/harness/<team>/<harness_id>/state.json`.
3. `advance()` asks the runner if gates pass; on success moves to next phase and re-saves.
4. Artifacts registered via `register_artifact` update state; `ArtifactStore` owns on-disk files.
5. `load()` / `find_latest()` rehydrate a previous run for resumption.

**Messaging:**
- `get_transport(name, team)` returns a `FileTransport` (default) or `P2PTransport` (if `pyzmq` installed + configured).
- `clawteam/team/mailbox.py` + `router.py` + `routing_policy.py` put messages into per-member inbox directories created by `TeamManager.add_member`.

**State Management:**
- No long-lived in-memory state for agents; all shared state is on disk under `get_data_dir()` (`~/.clawteam` by default).
- All team-scoped paths go through `ensure_within_root(_teams_root(), validate_identifier(team))` to block path traversal.
- Concurrency protected by `file_locked()` context managers around JSON load/merge/save.

## Key Abstractions

**`SpawnBackend` (ABC):**
- Purpose: Abstract process host for an agent CLI.
- Location: `clawteam/spawn/base.py`
- Implementations: `TmuxBackend` (`clawteam/spawn/tmux_backend.py`), `SubprocessBackend` (`clawteam/spawn/subprocess_backend.py`), `WshBackend` (`clawteam/spawn/wsh_backend.py`).
- Pattern: Registry-based factory (`get_backend`); third parties call `register_backend`.

**`NativeCliAdapter` + `PreparedCommand`:**
- Purpose: Translate a raw CLI invocation into a runnable command tailored to the target AI CLI.
- Location: `clawteam/spawn/adapters.py`
- Pattern: Strategy-by-detection — `is_<family>_command` predicates gate per-family argument synthesis.

**`AgentIdentity`:**
- Purpose: Stable identity across spawn boundaries with multi-generation env compatibility.
- Location: `clawteam/identity.py`
- Pattern: Frozen-ish dataclass + dual-direction env marshalling (`from_env` / `to_env`).

**`Transport` (ABC):**
- Purpose: Message delivery interface.
- Location: `clawteam/transport/base.py`
- Implementations: `FileTransport`, `P2PTransport`.

**`HarnessPlugin` (ABC):**
- Purpose: Extension point for custom gates, prompts, event handlers.
- Location: `clawteam/plugins/base.py`
- Contract: `on_register(ctx)`, `on_unregister()`, `contribute_gates()`, `contribute_prompts(phase, role)`.

**`EventBus`:**
- Purpose: In-process synchronous pub/sub with priority and optional async dispatch.
- Location: `clawteam/events/bus.py`
- Registry: `register_event_type` / `resolve_event_type` for shell-hook name resolution.

**`PhaseGate`:**
- Purpose: Declarative advancement precondition.
- Location: `clawteam/harness/phases.py`
- Built-ins: `ArtifactRequiredGate`, `AllTasksCompleteGate`, `HumanApprovalGate`.

**`TeamConfig` / `TeamMember`:**
- Purpose: Pydantic v2 models for durable team state.
- Location: `clawteam/team/models.py`

## Entry Points

**`clawteam` CLI:**
- Location: `clawteam/cli/commands.py` (Typer app bound as `clawteam` in `pyproject.toml::project.scripts`).
- Triggers: console script or `python -m clawteam` via `clawteam/__main__.py`.
- Responsibilities: parse global options (`--json`, `--data-dir`, `--transport`), dispatch to subcommands (spawn, team, task, mailbox, harness, board, workspace, cost, plan).

**`clawteam-mcp` server:**
- Location: `clawteam/mcp/server.py::main` (also bound as console script).
- Triggers: launched by an agent CLI configured to connect to a local MCP server.
- Responsibilities: expose `clawteam/mcp/tools/*` as MCP tools through `FastMCP`.

**MCP `__main__`:**
- Location: `clawteam/mcp/__main__.py` (allows `python -m clawteam.mcp`).

**Plugin entry:**
- Plugins register themselves on harness startup via `clawteam/plugins/manager.py` and receive a `HarnessContext`.

## Error Handling

**Strategy:** Fail-fast on user input, permissive on filesystem/process edges, translate domain errors to MCP errors at the tool boundary.

**Patterns:**
- `paths.validate_identifier` raises `ValueError` with a specific message; callers let it bubble.
- `paths.ensure_within_root` raises `ValueError` on traversal attempts.
- JSON store loads swallow `JSONDecodeError` / `OSError` and return empty dicts (`clawteam/spawn/registry.py::_load`).
- Subprocess calls that probe state (`_tmux_pane_alive`, `_wsh_block_alive`) use `capture_output=True` and return `False` on non-zero.
- MCP server wraps each tool with `translate_error` (`clawteam/mcp/server.py`) so domain exceptions surface as MCP protocol errors.
- Adapter code guards environment-specific quirks (e.g. skipping `--dangerously-skip-permissions` when `os.getuid() == 0`, rewriting `TERM=dumb`).

## Cross-Cutting Concerns

**Logging:**
- `rich.Console` for user-facing CLI output (`clawteam/cli/commands.py`).
- No structured logger; diagnostic output is printed directly or discarded via `subprocess.DEVNULL`.

**Validation:**
- Pydantic v2 models for all persisted team / task / message payloads (`clawteam/team/models.py`).
- Identifier regex `^[A-Za-z0-9._-]+$` (`clawteam/paths.py`).

**Authentication / Secrets:**
- No in-tree auth. Provider API keys are passed through the spawned child's environment (adapter whitelists `*_API_KEY`, `*_BASE_URL`, `*_API_BASE`, `GOOGLE_CLOUD_PROJECT` for Docker `nanobot`).
- `CLAWTEAM_*` env vars are canonical; `OH_*` and `CLAUDE_CODE_*` are accepted for backward compatibility through `identity._env`.

**Concurrency:**
- File lock (`fileutil.file_locked`) around every shared JSON mutation.
- `EventBus` uses `threading.RLock` + `ThreadPoolExecutor` for async dispatch.

**Data directory:**
- Single source of truth: `clawteam.team.models.get_data_dir()` → `$CLAWTEAM_DATA_DIR` → config.data_dir → `~/.clawteam`.

---

*Architecture analysis: 2026-04-15*
