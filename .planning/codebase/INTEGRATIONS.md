# External Integrations

**Analysis Date:** 2026-04-15

## APIs & External Services

ClawTeam is an orchestration layer; it does not itself call LLM APIs, but it wires spawned coding-agent CLIs to dozens of LLM providers through presets.

**LLM CLI runtimes (spawned as child processes, not called as HTTP clients):**
Detected in `clawteam/spawn/adapters.py` and `clawteam/spawn/tmux_backend.py`:
- `claude` (Anthropic Claude Code) — honors `--dangerously-skip-permissions`
- `codex` (OpenAI Codex CLI) — honors `--dangerously-bypass-approvals-and-sandbox`
- `gemini` (Google Gemini CLI) — honors `--yolo`
- `kimi` (Moonshot) — injects `-w <cwd>` and `--print -p <prompt>`
- `qwen` (Alibaba Qwen Code) — honors `--yolo`
- `opencode` — honors `--yolo`
- `nanobot` — wrapped with docker mount/env handling in `clawteam/spawn/adapters.py`
- `pi` — additional handling in `clawteam/spawn/subprocess_backend.py`

**LLM provider presets (`clawteam/spawn/presets.py`):**
- Anthropic official — `ANTHROPIC_API_KEY`
- OpenAI official (Codex) — `OPENAI_API_KEY`
- Google AI Studio (Gemini) — `GEMINI_API_KEY`
- Google Vertex AI — `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_CLOUD_LOCATION`, gcloud ADC
- Moonshot / Kimi — `MOONSHOT_API_KEY`, base URLs `https://api.moonshot.cn/anthropic` and `https://api.moonshot.cn/v1`
- DeepSeek — `DEEPSEEK_API_KEY`, `https://api.deepseek.com/anthropic`
- Zhipu GLM (CN/global) — `ZHIPU_API_KEY`, `https://open.bigmodel.cn/api/anthropic`, `https://api.z.ai/api/anthropic`
- Alibaba Bailian — `DASHSCOPE_API_KEY`, `https://dashscope.aliyuncs.com/apps/anthropic`, `https://coding.dashscope.aliyuncs.com/apps/anthropic`
- MiniMax (CN/global) — `MINIMAX_API_KEY`, `https://api.minimaxi.com/anthropic`, `https://api.minimax.io/anthropic`
- OpenRouter — `OPENROUTER_API_KEY`, `https://openrouter.ai/api` (and `/v1` for Codex)

**Model Context Protocol (MCP):**
- ClawTeam ships its own FastMCP server at `clawteam/mcp/server.py` (entry point `clawteam-mcp`)
- Tools registered via `clawteam/mcp/tools/` (`board.py`, `cost.py`, `mailbox.py`, `plan.py`, `task.py`, `team.py`, `workspace.py`)
- Uses `mcp.server.fastmcp.FastMCP` from the official `mcp` SDK

**Board web proxy (`clawteam/board/server.py`):**
- Allow-listed proxy hosts: `api.github.com`, `github.com`, `raw.githubusercontent.com`
- Used by the bundled dashboard (`clawteam/board/static/index.html`) served by a stdlib `ThreadingHTTPServer`

## Data Storage

**Databases:**
- None. No SQL/NoSQL client dependencies.

**File storage (primary):**
- Local filesystem rooted at `CLAWTEAM_DATA_DIR` or `~/.clawteam` (`clawteam/team/models.py:get_data_dir`)
- Per-team subtree: `teams/<team>/` containing `spawn_registry.json`, `peers/`, mailbox/board state
- Worktrees under `workspaces/` (`clawteam/workspace/manager.py`)
- Docker bootstrap under `runtime/docker/clawteam-bootstrap.sh` (`clawteam/spawn/cli_env.py`)
- Atomic writes via `clawteam/fileutil.py:atomic_write_text` with lockfiles (`file_locked`)

**Persistence layer:**
- JSON-on-disk stores via `clawteam/store/file.py` (base in `clawteam/store/base.py`)
- TOML team templates (`clawteam/templates/*.toml`) parsed with stdlib `tomllib` (or `tomli` on Py <3.11)

**Caching:**
- None beyond in-memory dict caches inside transports/backends.

## Authentication & Identity

**Agent identity:**
- `clawteam/identity.py` resolves identity from `CLAWTEAM_*` env vars with legacy aliases `OH_*` and `CLAUDE_CODE_*`
- Fields include agent name, id, team, role derived from environment

**LLM auth:**
- Passthrough only — presets declare which env var holds the credential (`AgentPreset.auth_env`) and forward it to the spawned CLI's process env
- No credential storage in-repo; secrets must be present in the user's shell environment

**User auth:**
- None. CLI assumes the local user owns the data directory.

## Monitoring & Observability

**Error tracking:**
- None. Errors surface via `rich` console output and Python `logging` (`clawteam/workspace/manager.py` uses `logging.getLogger(__name__)`).

**Logs / events:**
- Internal event bus in `clawteam/events/bus.py` and `clawteam/events/global_bus.py`
- Hook dispatch for user-configured shell/python hooks (`clawteam/events/hooks.py`, `HookDef` in `clawteam/config.py`)
- Board collector tails events for the dashboard (`clawteam/board/collector.py`)

**Visualization:**
- `gource` integration in `clawteam/board/gource.py` — shells out to the `gource` binary with a custom log derived from team events + git history
- Web dashboard served by `clawteam/board/server.py` (stdlib `http.server`)

## CI/CD & Deployment

**Hosting (docs/website):**
- GitHub Pages — `docs/CNAME`, `docs/index.html`
- Vite-built marketing site in `website/`

**CI pipeline:**
- No CI config committed at repo root (no `.github/workflows` observed in listing); project relies on local `pytest`/`ruff`.

## Environment Configuration

**Required env vars (by use case):**
- Running the CLI: none strictly required; `CLAWTEAM_DATA_DIR` optional override
- Spawning agents: at least one provider auth env (see preset list above) plus whatever the native CLI expects (e.g., `ANTHROPIC_API_KEY` for Claude Code)
- Docker-wrapped spawns: `CLAWTEAM_DOCKER_HOST_WRAPPER`, `CLAWTEAM_DOCKER_SOURCE_ROOT` (`clawteam/spawn/cli_env.py`)
- Anthropic-compatible presets set `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, and occasionally `CLAUDE_CODE_SUBAGENT_MODEL`, `API_TIMEOUT_MS`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`, `ENABLE_TOOL_SEARCH`

**Secrets location:**
- User shell environment / dotfiles only. No `.env` files committed; no secret loader in the code.

## Webhooks & Callbacks

**Incoming:**
- None. The only HTTP surface is the local-only board server (`clawteam/board/server.py`).

**Outgoing:**
- None from ClawTeam core. The board dashboard may `urllib`-proxy requests to the allow-listed GitHub hosts on behalf of the browser UI.

## Spawn Runtimes & Process Integrations

This is where the bulk of ClawTeam's "integration surface" lives.

**Tmux backend (`clawteam/spawn/tmux_backend.py`):**
- Requires `tmux` on PATH (`shutil.which("tmux")`)
- Creates one session per team named `clawteam-<team>` with one window per agent
- Used for visible, interactive agent panes
- Adapter-aware: dispatches via `NativeCliAdapter` to handle claude/codex/gemini/kimi/nanobot/opencode/pi/qwen quirks

**Subprocess backend (`clawteam/spawn/subprocess_backend.py`):**
- Headless `subprocess.Popen` spawns
- Used when tmux / wave terminals are unavailable
- Same adapter flow as tmux backend

**Wsh backend (`clawteam/spawn/wsh_backend.py`):**
- Integrates with WaveTerminal / TideTerm via the `wsh` CLI
- RPC layer in `clawteam/spawn/wsh_rpc.py` (`WshRpcClient`)
- Spawns agents into Wave blocks; polls block existence with timeouts

**Docker / Podman integration (`clawteam/spawn/command_validation.py`, `clawteam/spawn/cli_env.py`):**
- Recognizes `docker` and `podman` engines; enumerates docker CLI flags with/without values to parse wrapped commands
- `ensure_docker_workspace`, `ensure_docker_mount`, `ensure_docker_env` inject workspace, data-dir mount, and envs into `docker run` invocations
- `build_docker_clawteam_runtime` + `_ensure_docker_bootstrap_script` write a shell wrapper at `<data_dir>/runtime/docker/clawteam-bootstrap.sh` so containers can re-enter the `clawteam` CLI (using `CLAWTEAM_DOCKER_HOST_WRAPPER` or `CLAWTEAM_DOCKER_SOURCE_ROOT`)
- Specifically used to wrap `nanobot` spawns (`is_nanobot_command` branch in `clawteam/spawn/adapters.py`)

**Nanobot runtime:**
- Treated as a first-class native CLI runtime via the adapter layer
- When invoked under docker, the adapter injects workspace (`-w`), a bind mount for `CLAWTEAM_DATA_DIR`, and the docker clawteam runtime env/mounts so the containerized agent can call back into the CLI

**Keepalive & resume (`clawteam/spawn/keepalive.py`):**
- Wraps commands with shell keepalive loops and resume commands for long-running agents across all backends

**Git / worktree integration (`clawteam/workspace/git.py`, `clawteam/workspace/manager.py`):**
- Shells out to the system `git` binary
- Creates per-agent worktrees, checkpoints, merges, and cleans them up
- Used by Gource visualization to replay real file events

**ZeroMQ transport (`clawteam/transport/p2p.py`):**
- Optional `pyzmq` dependency (`p2p` extra)
- PUSH/PULL sockets with filesystem peer discovery via `peers/<agent>.json`
- Falls back to `FileTransport` (`clawteam/transport/file.py`) when peers are offline; `ClaimedMessage` (`clawteam/transport/claimed.py`) provides lease-based delivery

**Plugin system (`clawteam/plugins/`):**
- `base.py`, `manager.py` — plugin loading
- Ships `ralph_loop_plugin.py` as an example plugin

## Skills Integration

- Project uses ClawTeam "skills" resolved via `skills-lock.json` and surfaced under `skills/clawteam/` (with `SKILL.md`, `agents/`, `references/`)
- Additionally shadowed under `.claude/skills/clawteam` and `.agents/skills/clawteam` for IDE agent discovery

---

*Integration audit: 2026-04-15*
