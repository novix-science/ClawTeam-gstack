# Coding Conventions

**Analysis Date:** 2026-04-15

## Language & Tooling

- Python 3.10+ is the target (`pyproject.toml` `requires-python = ">=3.10"`, ruff `target-version = "py310"`).
- Linter / formatter: **ruff** (line length 100, ignore `E501`) configured in `pyproject.toml`.
- CI enforces `ruff check clawteam/ tests/` on every push/PR (`.github/workflows/ci.yml`).
- Type hints are used throughout but no separate static type checker (mypy/pyright) is wired in.

## Naming Patterns

**Modules / files:**
- `snake_case.py` — e.g. `clawteam/spawn/tmux_backend.py`, `clawteam/team/routing_policy.py`.
- Tests mirror source names with `test_` prefix: `tests/test_tmux_backend.py` is missing but `tests/test_wsh_backend.py` matches `clawteam/spawn/wsh_backend.py`.

**Packages:**
- All code under `clawteam/` single namespace. Subpackages group responsibility: `board/`, `cli/`, `events/`, `harness/`, `mcp/`, `plugins/`, `spawn/`, `store/`, `team/`, `templates/`, `transport/`, `workspace/`.

**Functions / variables:**
- `snake_case` for all functions and locals (`build_spawn_path`, `resolve_clawteam_executable` in `clawteam/spawn/cli_env.py`).
- Private helpers prefixed with single underscore (`_now_iso`, `_version_callback`, `_harness_dir`).
- Module-level private state also underscore-prefixed (`_json_output`, `_data_dir` in `clawteam/cli/commands.py:34`).

**Classes / types:**
- `PascalCase` (`NativeCliAdapter`, `PreparedCommand`, `HarnessOrchestrator`, `PhaseRunner`, `TaskWaiter`).
- Enums are `PascalCase` subclasses of `str, Enum` with lowercase members — see `clawteam/team/models.py:30` (`MemberStatus.active`, `TaskStatus.in_progress`).
- Predicates named `is_<thing>_command` (`is_claude_command`, `is_qwen_command`, `is_nanobot_command` in `clawteam/spawn/adapters.py`).
- Frozen dataclasses for value objects (`@dataclass(frozen=True) PreparedCommand`, `clawteam/spawn/adapters.py:22`).

**Constants:**
- Module-level `UPPER_SNAKE` for phase keys: `DISCUSS`, `PLAN`, `EXECUTE`, `VERIFY`, `SHIP`, `DEFAULT_PHASES`, `DEFAULT_PHASE_ROLES` in `clawteam/harness/phases.py:22-36`.
- Phase identifiers are typed `Phase = str` (open string alias, not Enum) to allow plugin extension (`clawteam/harness/phases.py:20`).

## Module Header

Every module starts with a one-line docstring summarising purpose, followed by `from __future__ import annotations`:

```python
"""Runtime adapters for agent-specific command preparation."""

from __future__ import annotations
```

See `clawteam/spawn/adapters.py:1`, `clawteam/cli/commands.py:1`, `clawteam/harness/orchestrator.py:1`.

## Import Organization

Ruff's isort rule (`I` in `[tool.ruff.lint] select = ["E", "F", "I", "N", "W"]`, `pyproject.toml`) enforces the order. A recent fix (`bc69bc0 Fix lint import order in spawn adapters`) moved imports in `clawteam/spawn/adapters.py` into canonical groups — this is the authoritative layout:

1. `from __future__ import annotations`
2. Blank line
3. Standard library (`import os`, `from dataclasses import dataclass`, `from pathlib import Path`)
4. Blank line
5. First-party `clawteam.*` imports
6. Multi-name imports from the same module are repeated `from X import (...)` blocks when grouping logically (see `clawteam/spawn/adapters.py:10-19`, which uses two `from clawteam.spawn.command_validation import (...)` blocks rather than one, to keep an alias-import separate — this was intentional).

**Path aliases:** None. All imports are fully qualified `clawteam.<subpackage>.<module>`. No relative imports observed in top-level modules.

## Data Modeling

- **Pydantic v2 `BaseModel`** for persisted state and messages: `PhaseState` (`clawteam/harness/phases.py:39`), task/team models in `clawteam/team/models.py`.
- Defaults via `Field(default_factory=...)` with lambdas for mutable defaults (`lambda: list(DEFAULT_PHASES)`).
- Timestamps are ISO-8601 UTC strings produced by a module-local `_now_iso()` helper (duplicated in both `clawteam/harness/phases.py:15` and `clawteam/team/models.py:26`).
- `str, Enum` subclasses for closed vocabularies (`TaskStatus`, `TaskPriority`, `MessageType`, `MemberStatus`).
- `@dataclass(frozen=True)` for stateless value objects that never need serialization (`PreparedCommand`).
- Abstract interfaces use `abc.ABC` + `@abstractmethod` (`PhaseGate` in `clawteam/harness/phases.py:56`).

## Error Handling

**CLI layer (`clawteam/cli/commands.py`):**
- User-facing errors: print rich-formatted message, then `raise typer.Exit(1)`. Dozens of occurrences (`:126`, `:130`, `:166`, `:216`, `:245`, `:315`, `:438`, `:444`, `:465`, ...).
- When re-raising after catching, use explicit chaining: `raise typer.Exit(1) from exc` (`clawteam/cli/commands.py:144`).
- `raise typer.Exit()` (no code) for clean early exits like `--version` (`:41`).

**Library layer:**
- Raise `ValueError` for invalid arguments / missing domain entities (`clawteam/board/collector.py:40`, `clawteam/board/server.py:53-86`).
- Raise `RuntimeError` for unexpected runtime state (`clawteam/board/gource.py:246` "Live gource process missing stdin pipe").
- Library code **never** calls `typer.Exit` or `sys.exit` — keep that at the CLI boundary.

**Defensive fallbacks:**
- Silent degradation for environment-specific edge cases, documented with a comment. Example in `clawteam/spawn/adapters.py:49-55`: Claude CLI rejects `--dangerously-skip-permissions` as root; detect `os.getuid() == 0` and silently omit the flag so spawned agents can still start.

## Logging

- Standard library `logging` used sparingly — only in `clawteam/board/server.py` and `clawteam/workspace/manager.py`.
- Primary user-facing output uses `rich.console.Console` (instantiated once per module as `console = Console()`, see `clawteam/cli/commands.py:27`).
- Tables rendered via `rich.table.Table`.
- No structured logging / JSON logs; `--json` CLI flag switches human-readable output for machine-readable output at the command level.

## Function & Module Design

- Functions stay small and single-purpose; detectors (`is_claude_command`, `is_codex_command`, ...) are one-liners.
- Dependencies are passed explicitly as constructor args (`HarnessOrchestrator.__init__` takes everything it needs, `clawteam/harness/orchestrator.py:24-33`).
- Default argument values prefer `None` over mutable defaults; mutate conditionally inside the body (`if phases: self.state.phases = phases`).
- Keyword-only arguments enforced with `*,` for option-heavy APIs (`NativeCliAdapter.prepare_command`, `clawteam/spawn/adapters.py:36`).
- Heavy modules (`clawteam/cli/commands.py`) use typer sub-app composition rather than one monolithic file where possible; each subpackage owns its CLI wiring.

## Comments & Docstrings

- Module docstrings are mandatory and one-line (`"""Runtime adapters for agent-specific command preparation."""`).
- Class docstrings describe the abstraction (`"""Adapter for direct CLI runtimes such as claude, codex, gemini, kimi, nanobot, qwen, opencode."""`).
- Inline comments use `#` with a blank line above when introducing a section (`# ── Core operations ───────────────────────────────────────────────` style section banners in `clawteam/harness/orchestrator.py:66`).
- Non-obvious environment / platform workarounds get a short paragraph comment explaining *why*, not *what* (see root-detection comment cited above).

## Typing Conventions

- `from __future__ import annotations` everywhere — all type hints are strings at runtime, so PEP 604 unions (`str | None`) and built-in generics (`list[str]`, `dict[str, str]`) are used freely even while supporting Python 3.10.
- `Optional[X]` is used in `typer` signatures specifically (typer reads annotations at call time): `clawteam/cli/commands.py:53-57`.
- Return type annotations are expected on public APIs; `-> None` is written explicitly.

## Configuration & State

- Environment variable overrides respected throughout: `CLAWTEAM_DATA_DIR`, `CLAWTEAM_AGENT_ID`, `CLAWTEAM_AGENT_NAME` (see `clawteam/team/models.py:17` and `tests/conftest.py:14`).
- File-based state rooted at `~/.clawteam` (via `get_data_dir()` in `clawteam/team/models.py:15`), never hard-coded.
- Configuration loaded lazily to avoid circular imports (`from clawteam.config import load_config` inside `get_data_dir()`).

## Development Rules (from `.agents/skills/clawteam-dev/SKILL.md`)

- Prefer `clawteam` CLI commands over editing state files directly.
- Prefer targeted tests: `ruff check clawteam/ tests/` + `pytest tests/<target>.py -q`.
- Escalate to full harness / multi-module runs only when a change crosses spawn/runtime/workflow boundaries.
- Keep test teams small — one leader + one or two workers — until lower layers pass.

---

*Convention analysis: 2026-04-15*
