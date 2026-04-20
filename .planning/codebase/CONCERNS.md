# Codebase Concerns

**Analysis Date:** 2026-04-15

## Tech Debt

**Oversized CLI module:**
- Issue: `clawteam/cli/commands.py` is 4,573 lines with Typer commands, helper functions, and business logic collocated. Makes change review, navigation, and targeted testing difficult.
- Files: `clawteam/cli/commands.py`
- Impact: High merge-conflict surface; new contributors struggle to locate command handlers; refactors risk regressions due to shared helper state.
- Fix approach: Split by command group (team, lifecycle, spawn, plan, template, board) into `clawteam/cli/commands/*.py` and keep `commands.py` as a Typer composition root.

**Legacy `OH_*` / `CLAUDE_CODE_*` env var aliases:**
- Issue: Identity layer reads three environment namespaces (`CLAWTEAM_*`, legacy `OH_*`, `CLAUDE_CODE_*`) with overloaded-positional-argument compatibility in `_env()`.
- Files: `clawteam/identity.py` (lines 10-45, 64-103), `clawteam/events/hooks.py:89`, `clawteam/team/watcher.py:102-108`, `clawteam/spawn/adapters.py`, `clawteam/spawn/presets.py`, `clawteam/spawn/tmux_backend.py`, `clawteam/cli/commands.py:1871`, `clawteam/workspace/manager.py`
- Impact: `_env()` uses a heuristic (prefix sniffing in line 26) to decide whether the 2nd positional arg is a legacy key or a default value, which is fragile and silently mis-routes inputs that don't match the expected prefix pattern. Every identity change must be propagated into two env names (`to_env` in `clawteam/identity.py:87-103`).
- Fix approach: Deprecate `OH_*` with a release-gated warning, freeze `CLAUDE_CODE_*` reads behind an explicit parameter (`legacy_key=`, `claude_code_key=`), and remove the positional-overloading branch in `_env()`.

**Legacy flat plan file layout:**
- Issue: Plan files used to live at `<data>/plans/<agent>-<id>.md`; new layout is `<data>/plans/<team>/<agent>-<id>.md`. Both code paths are still scanned on read and event-log sweeps must locate orphan legacy files.
- Files: `clawteam/team/plan.py:41-99`
- Impact: Every plan lookup pays the cost of extra directory walks; cleanup/GC must run `referenced_legacy_plan_paths()` to avoid deleting in-use legacy plans. Risk of divergence when a plan exists in both locations.
- Fix approach: One-shot migration CLI (`clawteam plan migrate-legacy`) that moves legacy plans into team dirs, then drop `_legacy_plan_path` and `_iter_plan_paths`' fallback after N releases.

**Docs / skills directory duplication:**
- Issue: `docs/skills/clawteam/` and top-level `skills/clawteam/` contain parallel copies of SKILL.md and references. Renamed from `openhands` to `clawteam` while keeping legacy aliases (21 files still mention openclaw/openhands/`OH_`).
- Files: `docs/skills/clawteam/SKILL.md`, `skills/clawteam/SKILL.md`, `docs/skills/clawteam/references/cli-reference.md`, `skills/clawteam/references/cli-reference.md`, `README.md`, `README_CN.md`, `README_KR.md`
- Impact: Docs drift between copies; the marketing site (`docs/`) and local skills index can emit different guidance to agents.
- Fix approach: Pick one canonical path (recommend `skills/clawteam/`) and make `docs/` a build artifact from `website/` or symlink/generated copy; add a CI check that diffs the two trees.

**Legacy worker script still references OpenClaw paths:**
- Issue: `scripts/openclaw_worker.sh` hardcodes `$HOME/.openclaw/.env` and `$HOME/.openclaw/workspace/.env` as env file locations; filename still uses the pre-rename brand.
- Files: `scripts/openclaw_worker.sh:21-38`
- Impact: Fresh installs under the `clawteam` name won't find env files; script is effectively a no-op on new data dirs. Confusing for users who greenfield-install.
- Fix approach: Rename to `scripts/clawteam_worker.sh`, read `CLAWTEAM_HOME` / `$HOME/.clawteam/.env` first with OpenClaw paths as fallback, and deprecate after one release.

## Known Bugs / Fragile Behavior

**Shell-mode hook execution:**
- Symptoms: Event hooks run with `shell=True`, allowing any command characters in the configured hook string to be interpreted by `/bin/sh`.
- Files: `clawteam/events/hooks.py:91-98`, `clawteam/team/watcher.py:113-119`
- Trigger: A user or plugin-registered hook command containing metacharacters, or a malicious event payload injected into the environment (env vars are passed through but not quoted within the command string itself).
- Workaround: Document that hook commands must be trusted; prefer the Python callable path (`_resolve_python_callable`) for dynamic hooks.

**Keepalive resume heuristics are brand-matched:**
- Issue: `build_resume_command()` maps executable basenames (`claude`, `codex`, `gemini`, `kimi`, `qwen`, `opencode`, `pi`) to vendor-specific resume flags. Any CLI not in the list falls through to no-resume, and docker-wrapped `nanobot` is explicitly opted out.
- Files: `clawteam/spawn/keepalive.py:11-35`
- Impact: Third-party or forked CLIs silently lose keepalive even when `--keepalive` is enabled. Vendor renames (e.g., `claude` → `claude-code-next`) break resume without test coverage for new names.
- Fix approach: Make resume commands data-driven via `clawteam/spawn/presets.py` or a user-supplied `[resume]` block in agent profile TOML, so new CLIs can opt-in without source edits.

**Keepalive shell loop swallows exit-hook failures:**
- Issue: `build_keepalive_shell_command()` builds a POSIX `while true` loop that runs `lifecycle on-exit` after each iteration. If the `clawteam lifecycle on-exit` command itself fails (e.g., data dir unavailable), the loop continues and may burn resume attempts.
- Files: `clawteam/spawn/keepalive.py:38-76`
- Impact: Silent drift between agent's real lifecycle state and recorded state; possible infinite loop when `should-keepalive` is always zero due to missing shutdown message.
- Fix approach: Check `$?` of the exit_hook and break on non-zero; also cap iterations (e.g., `--keepalive-max-attempts`).

**Broad `except Exception: pass` in hot paths:**
- Issue: 124 `except Exception`/bare-except occurrences across 40 files; many silently swallow errors (e.g., `clawteam/events/global_bus.py:46`, `clawteam/workspace/context.py:301`, `clawteam/cli/commands.py:2900-2955`, `clawteam/team/plan.py:80`).
- Files: `clawteam/events/bus.py:100`, `clawteam/events/global_bus.py:46`, `clawteam/events/hooks.py:99-101`, `clawteam/cli/commands.py` (15 occurrences), `clawteam/harness/context_recovery.py`, `clawteam/workspace/manager.py`
- Impact: Loss of diagnosability; crashes surface as "nothing happened" and keepalive loops can mask real errors.
- Fix approach: Replace with typed excepts (`except OSError`, `except json.JSONDecodeError`), and route unexpected exceptions through `clawteam/events/global_bus.py` as a structured error event.

## Security Considerations

**`shell=True` subprocess invocations:**
- Risk: Arbitrary code execution if hook command strings or watcher commands come from untrusted config.
- Files: `clawteam/events/hooks.py:91-97`, `clawteam/team/watcher.py:113-119`
- Current mitigation: Commands are sourced from local TOML/config owned by the user; 30s timeout; stderr captured.
- Recommendations: Validate configured commands against an allowlist of binaries; support arg-list form (`shell=False`) as first-class; document threat model.

**Env-file loading in worker script:**
- Risk: `scripts/openclaw_worker.sh:28-38` uses `export "$line"` after a comment-strip; lines with embedded `$` or backticks are subject to word splitting and command substitution.
- Files: `scripts/openclaw_worker.sh:28-38`
- Current mitigation: `2>/dev/null || true` suppresses errors.
- Recommendations: Use `set -a; . "$ENV_FILE"; set +a` or a strict parser that does not invoke the shell on values.

**Docker/podman spawn allowlist:**
- Risk: `clawteam/spawn/command_validation.py` enumerates docker flags manually (`_DOCKER_FLAGS_WITH_VALUE`, lines 10-50). Missing flags (e.g., new `--gpus`, `--device-cgroup-rule=` forms) can cause image detection to parse the wrong token as the image name, potentially running an unintended container.
- Files: `clawteam/spawn/command_validation.py:9-120`
- Current mitigation: Hand-maintained list covering common flags.
- Recommendations: Shell out to `docker run --help` or pin to a curated subset and reject unknown flags with a clear error.

**Secrets in env:**
- Risk: Agent identity/config consumes 45 `password|secret|api_key`-mentioning sites across 6 files; costs are aggregated into snapshots and broadcast via events. Nothing redacts secret-looking env vars before they are logged via hook env pass-through.
- Files: `clawteam/events/hooks.py:80-88` (copies full `os.environ` into `CLAWTEAM_*` mirror vars), `clawteam/team/watcher.py:100-119`
- Current mitigation: None.
- Recommendations: Filter `os.environ` against a deny-pattern (`*_TOKEN`, `*_KEY`, `*_SECRET`, `*PASSWORD*`) before copying into the hook env.

## Performance Bottlenecks

**Linear event-log scan for legacy plans:**
- Problem: `referenced_legacy_plan_paths()` reads every `evt-*.json` under the team's events dir and JSON-parses it to answer "which legacy plan paths are still referenced?"
- Files: `clawteam/team/plan.py:65-99`
- Cause: No index of plan approval events; O(total_events) per call.
- Improvement path: Maintain a persisted index of `plan_approval_request` events, or stop needing this once legacy plans are migrated out (see tech debt above).

**File-based transport for high-frequency messaging:**
- Problem: `clawteam/transport/file.py` uses per-message files with filesystem locks; roadmap Phase 2 explicitly calls this out.
- Files: `clawteam/transport/file.py`, `clawteam/store/file.py`, `ROADMAP.md:15-80`
- Cause: Default transport is filesystem; no batching.
- Improvement path: Redis transport (already planned in `ROADMAP.md`).

**Large single-file modules slow import & reload:**
- Problem: `clawteam/cli/commands.py` (4,573 lines), `clawteam/spawn/tmux_backend.py` (756 lines), `clawteam/spawn/wsh_backend.py` (418 lines) all imported eagerly by Typer entrypoint.
- Files: `clawteam/cli/commands.py`, `clawteam/spawn/tmux_backend.py`
- Cause: No lazy subcommand loading.
- Improvement path: Typer's lazy sub-app pattern or `typer_plus` autodiscovery.

## Fragile Areas

**tmux backend (`clawteam/spawn/tmux_backend.py`):**
- Files: `clawteam/spawn/tmux_backend.py` (756 lines, many `subprocess.run` calls to `tmux`)
- Why fragile: Hard-coded tmux CLI sequences, order-sensitive session/window setup, and broad `subprocess.run` usage with `DEVNULL`-swallowed stderr (lines 165-216). No integration tests run a real tmux.
- Safe modification: Always pair changes with `tests/test_spawn_backends.py` additions; exercise `--dry-run`/echo mode when available.
- Test coverage: Unit tests mock tmux; end-to-end coverage relies on developers having tmux locally.

**Keepalive loop composition:**
- Files: `clawteam/spawn/keepalive.py`, `clawteam/spawn/subprocess_backend.py:112`, `clawteam/spawn/wsh_backend.py:307`, `clawteam/spawn/tmux_backend.py:148`
- Why fragile: Keepalive shell string is concatenated from three places; changing the loop variables (`__ct_cmd`, `__ct_status`) must stay in sync across three backends.
- Safe modification: Only edit `keepalive.py`; add regression tests asserting exact substring shape.
- Test coverage: `tests/test_spawn_backends.py` covers keepalive string generation but not real-shell execution.

**Context-recovery flow:**
- Files: `clawteam/harness/context_recovery.py` (subprocess call + 5 broad excepts)
- Why fragile: Recovers agent context by shelling out and catching `Exception` to fall through; any recovery failure is indistinguishable from "no recovery needed".
- Safe modification: Log which branch was taken before swallowing; add tests that inject subprocess failures.

**Identity `_env()` positional-arg overloading:**
- Files: `clawteam/identity.py:10-36`
- Why fragile: Semantics of the second positional argument change based on a prefix check (`OH_`, `CLAUDE_CODE_`, `CLAWTEAM_`). A new env-var namespace would silently be treated as a default value.
- Safe modification: Migrate all call sites to keyword-only args before adding namespaces.

## Scaling Limits

**Single-host filesystem coordination:**
- Current capacity: All team state in `~/.clawteam/`; all agents must run on one machine.
- Limit: No cross-host coordination; filesystem lock contention for active teams.
- Scaling path: `ROADMAP.md` Phase 2 (Redis transport) + Phase 3 (store abstraction).

**Event file fan-out:**
- Current capacity: One JSON file per event (`evt-*.json`) under `<data>/teams/<team>/events/`.
- Limit: Directory size grows unbounded; `team/plan.py` and snapshot code glob the directory.
- Scaling path: Roll events into append-only logs or SQLite (store abstraction in roadmap).

## Dependencies at Risk

**`mcp>=1.0.0` unpinned upper bound:**
- Risk: No upper bound on MCP SDK; breaking changes would silently propagate.
- Files: `pyproject.toml:30`
- Impact: MCP server/tool modules (`clawteam/mcp/`) could break on `pip install --upgrade`.
- Migration plan: Pin `mcp>=1.0.0,<2.0.0`.

**Optional `pyzmq` for P2P transport:**
- Risk: `clawteam/transport/p2p.py` imports pyzmq conditionally; no tests in default CI.
- Files: `clawteam/transport/p2p.py`, `pyproject.toml` extras `[p2p]`.
- Impact: P2P transport may be broken at runtime and not caught by CI.
- Migration plan: Add an opt-in CI job with `pip install -e .[p2p]` that runs `tests/test_adapters.py` / a P2P smoke test.

## Missing Critical Features

**No migration command for renamed data dirs:**
- Problem: After the openclaw→clawteam rename (commit 189b4ff), there is no CLI to migrate `~/.openclaw/` → `~/.clawteam/`.
- Blocks: Clean deprecation of legacy env names and legacy plan paths.

**No structured logging / observability:**
- Problem: Errors are printed to stderr or swallowed by broad excepts; no JSON log stream.
- Blocks: Production debugging of keepalive/lifecycle flows; correlating agent crashes with event bus state.

**Lifecycle `should-keepalive` only checks `shutdown_approved`:**
- Problem: `clawteam/cli/commands.py:2916-2935` returns exit 1 only if a `shutdown_approved` message exists; any other reason to stop (user Ctrl-C, OOM kill) still triggers resume on clean exit.
- Blocks: Graceful opt-out from keepalive loops without explicit shutdown approval.

## Test Coverage Gaps

**Shell-command generation paths:**
- What's not tested: `build_keepalive_shell_command()` output is not executed end-to-end; `scripts/openclaw_worker.sh` has no tests.
- Files: `clawteam/spawn/keepalive.py`, `scripts/openclaw_worker.sh`
- Risk: Quoting bugs (spaces in team/agent names, UTF-8) surface only in production.
- Priority: High.

**Docker/podman command validation:**
- What's not tested: New docker flags added to `_DOCKER_FLAGS_WITH_VALUE` are covered by unit tests, but image-index detection for mixed `--flag=value` and positional args is not fuzzed.
- Files: `clawteam/spawn/command_validation.py`, `tests/test_spawn_cli.py`
- Risk: A crafted docker command could be misparsed and run an unintended image.
- Priority: High (security-adjacent).

**Hook subprocess execution:**
- What's not tested: `clawteam/events/hooks.py:80-103` (subprocess with shell=True) has no timeout/failure-path tests.
- Files: `clawteam/events/hooks.py`
- Risk: Hook timeouts or non-zero exits may be silently dropped.
- Priority: Medium.

**Legacy env-var fallback matrix:**
- What's not tested: `tests/test_identity.py` covers the primary path; the overloaded-positional-arg branch in `_env()` (line 26-29) and three-way precedence `CLAWTEAM_* > OH_* > CLAUDE_CODE_*` are not exhaustively parameterized.
- Files: `clawteam/identity.py`, `tests/test_identity.py`
- Risk: Deprecation later will break silently for users still on `OH_*`.
- Priority: Medium.

**tmux backend:**
- What's not tested: No live-tmux integration test; all tmux CLI invocations are mocked.
- Files: `clawteam/spawn/tmux_backend.py`, `tests/test_spawn_backends.py`
- Risk: Real-tmux regressions ship undetected.
- Priority: Medium.

---

*Concerns audit: 2026-04-15*
