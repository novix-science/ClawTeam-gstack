# Phase 0: Foundation & Upstream RFC - Research

**Researched:** 2026-04-15
**Domain:** CI safety net, env secret-scrubbing, optional-tool detection, default-model-profile scaffolding, upstream RFC drafting — five additive-only deliverables inside an existing Python 3.10+ Typer/pytest/pydantic codebase.
**Confidence:** HIGH

## Summary

Phase 0 is five largely independent deliverables that need to land before any core harness code changes. None introduce new runtime dependencies, and none are allowed to alter existing template behavior. The phase is correctly scoped as "cheap-to-add-now, expensive-to-retrofit": each deliverable either catches regressions (BC matrix) or prevents bad first-user experiences (env scrub, doctor, model-profile default) that are much harder to unwind after a v1 release goes out.

The good news: every deliverable has precedent in the existing codebase. Template regression tests can extend `tests/test_spawn_cli.py`'s proven `RecordingBackend` pattern [VERIFIED: tests/test_spawn_cli.py:20-29, 309-341]. The env deny-filter has exactly one write-site of concern (`clawteam/events/hooks.py:81-89`) [VERIFIED: clawteam/events/hooks.py] plus three spawn-backend `os.environ.copy()` sites [VERIFIED: grep]. The `doctor` command slots into the existing `typer.Typer` + `rich.Table` + `--json` pattern used by every other CLI command [VERIFIED: clawteam/cli/commands.py:1-199]. The default model profile scaffolding attaches to the existing `ClawTeamConfig` + `AgentProfile` system [VERIFIED: clawteam/config.py]. The RFC is a single markdown file.

**Primary recommendation:** Ship the five deliverables as independent Plans (not a single monolith), executing them in an order where the slowest/most-ambiguous pieces (regression matrix + RFC) start first. Reuse existing test and CLI patterns verbatim; introduce zero new conventions. Keep the `_env()` modernization OUT of Phase 0 — treat env scrubbing as a wrapper/filter layer, not a refactor of the three-namespace lookup, to preserve backward compatibility.

## User Constraints (from CONTEXT.md)

No CONTEXT.md exists for Phase 0. Constraints are drawn from PROJECT.md, REQUIREMENTS.md, ROADMAP.md, and research/SUMMARY.md. Locked constraints binding this phase:

### Locked Decisions (project-wide)
- **Zero new required runtime dependencies** [CITED: PROJECT.md:103, STACK.md §Executive Recommendation]
- **Existing templates must not change behavior** — software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room must pass existing tests unchanged [CITED: PROJECT.md:101-102, REQUIREMENTS.md CORE-03]
- **Upstream-PR compatibility** — Phase 0 is part of the target upstream bundle; changes must be additive [CITED: ROADMAP.md:10]
- **`CLAWTEAM_*` canonical with `OH_*` and `CLAUDE_CODE_*` legacy aliases preserved** [CITED: PROJECT.md:105, codebase/ARCHITECTURE.md:122-123]
- **Default model_profile `balanced`** (never `quality`) — Pitfall #12 prevention [CITED: PROJECT.md Decision row 1; REQUIREMENTS.md TEAM-05; ROADMAP.md Phase 0 success criterion 5]
- **No auto-install of external tools** — `doctor` surfaces install commands, does not run them [CITED: PROJECT.md:77, REQUIREMENTS.md Out of Scope table]
- **Data stays under `get_data_dir()`** (default `~/.clawteam/`) [CITED: PROJECT.md:104]

### Claude's Discretion
- Test matrix structure (single parametrized file vs. per-template tests) — recommend below
- Deny-filter scope: deny-by-pattern only, vs. combined with scrubbing on read-path — recommend combined defense-in-depth below
- `doctor` output format details (single table vs. per-tool sections) — recommend per-tool sections with rich.Table summary
- Which specific models to hard-code in `balanced` default — **deferred to Phase 3**; Phase 0 only establishes the `model_profile` resolution path, not the Opus/Sonnet/Haiku assignment [ASSUMED]
- RFC target channel (GitHub issue/discussion/PR/markdown-only) — recommend PR-against-markdown below

### Deferred Ideas (OUT OF SCOPE for Phase 0)
- **`_env()` positional-overloading refactor** — CONCERNS.md documents this as fragile, and research/SUMMARY.md Gaps #6 flags it as an open Phase 0 question. Research recommendation: OUT of Phase 0. Scrubbing is a filter layer, not a rewrite of the existing three-namespace lookup [CITED: research/SUMMARY.md:332-334, codebase/CONCERNS.md:128-131]
- **Windows CI matrix parity** — SUMMARY.md Gaps #1 flags this as undecided. ROADMAP.md Phase 0 does not commit to Windows CI. Research recommendation below
- **Actual gstack.toml template** — ships in Phase 3, not Phase 0 (per REQUIREMENTS.md traceability table)
- **Model-profile-to-model-name mapping** — the Opus/Sonnet/Haiku-per-role logic ships in Phase 7 with cost observability (per QUALITY-12 → Phase 7)
- **Fixing `broad except Exception: pass` (124 sites)** — research/SUMMARY.md lists this as Phase 0 scope, but ROADMAP.md ships it as a follow-on; treat as "opportunistic fix if touched" not mandatory
- **Data-driven resume presets** — research/SUMMARY.md Phase 0 lists this, but ROADMAP.md Phase 0 explicitly omits it; defer to Phase 7 per Pitfall #16 mapping

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-03 | Existing templates keep working; no behavior change | §Regression Matrix; template tests already cover hedge-fund/software-dev/strategy-room |
| TEAM-06 | gstack.toml additive only; existing templates unchanged | §Default Model Profile; only the `model_profile` resolution path lands here |
| QUALITY-14 | BC regression matrix in CI for all 6 templates | §Regression Matrix; reuses `RecordingBackend` + Typer `CliRunner` pattern |
| QUALITY-15 | `_env()` helpers never leak secrets into logs/board/memory/artifacts | §Env Deny-Filter; wraps existing `hooks.py::_make_shell_handler` + 3 spawn `os.environ.copy()` sites |
| UX-08 | `clawteam doctor` detects missing optional tools per OS | §clawteam doctor; new top-level `doctor_app` Typer command |

## Project Constraints (from CLAUDE.md / AGENTS.md)

No `./CLAUDE.md` exists at repo root. No root-level `AGENTS.md`. Project conventions come from `.agents/skills/clawteam-dev/SKILL.md` and the codebase analyses:

- **Validation order:** `ruff check clawteam/ tests/` BEFORE `pytest tests/<target>.py -q` [CITED: .agents/skills/clawteam-dev/SKILL.md:76-78]
- **Targeted tests first:** prefer `pytest tests/<target>.py -q` over full-suite runs [CITED: .agents/skills/clawteam-dev/SKILL.md:Development Rules]
- **Prefer `clawteam` CLI over direct state-file edits** [CITED: .agents/skills/clawteam-dev/SKILL.md:129]
- **All tests use `isolated_data_dir` autouse fixture** which redirects `CLAWTEAM_DATA_DIR`, `HOME`, `USERPROFILE` to `tmp_path` [VERIFIED: tests/conftest.py:10-19]
- **No new conventions:** ruff-enforced import order, `from __future__ import annotations` per module, one-line module docstring, snake_case files, PascalCase classes with Enum suffix for predicates, typer.Exit(1) at CLI boundary only [CITED: codebase/CONVENTIONS.md §Naming Patterns through §Typing Conventions]

## Architectural Responsibility Map

Phase 0 is entirely a CLI-layer + test-layer phase — no harness/orchestrator/spawn-runtime/transport changes. Mapping each deliverable to its tier keeps plans from putting logic in the wrong place.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Template regression matrix | Test Layer (`tests/`) | CI Workflow (`.github/workflows/ci.yml`) | Tests must be fast enough for every PR; CI job just runs `pytest`. No new runtime code |
| Env deny-filter | Events Layer (`clawteam/events/hooks.py`) | Spawn Layer (`clawteam/spawn/subprocess_backend.py`, `tmux_backend.py`, `wsh_backend.py`) | The one write-site of record is `_make_shell_handler`; defense-in-depth adds a scrub helper reused by 3 spawn backends that do `os.environ.copy()`. The identity layer (`_env()`) remains unchanged |
| `clawteam doctor` CLI command | CLI Layer (`clawteam/cli/commands.py`) | Shared helper (`clawteam/doctor.py` NEW) | Follows the exact Typer sub-app pattern used by `config`, `template`, `team`, `hook`, `harness` sub-apps. OS detection is a helper module, not a backend |
| Default model profile resolution | Config Layer (`clawteam/config.py`) + Spawn Profiles (`clawteam/spawn/profiles.py`) | Template Layer (read field from TOML) | `ClawTeamConfig.default_profile` already exists; add a `default_model_profile: str = "balanced"` field and a resolver that prevents silent "quality" defaults. Scaffolding only — no gstack.toml yet |
| Upstream RFC | Docs Layer (`docs/rfcs/001-phase-registry.md` NEW) | None | Markdown file; no code surface |

**Nothing in Phase 0 touches the harness, orchestrator, transport, workspace, mcp, or board layers.** Plans that propose changes to those layers should be rejected as scope creep.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=9.0,<10.0 | Regression test runner | Already required dev dep [VERIFIED: pyproject.toml:32] |
| typer | >=0.12,<1.0 | `clawteam doctor` subcommand | Every existing CLI command uses Typer sub-apps [VERIFIED: pyproject.toml:22] |
| rich | >=13.0,<15.0 | Doctor output tables | Project convention is `rich.Table` for all tabular CLI output [CITED: codebase/CONVENTIONS.md §Logging] |
| pydantic | >=2.0,<3.0 | Config field for default profile | `ClawTeamConfig` is pydantic; add one field [VERIFIED: clawteam/config.py:50-69] |
| stdlib `re` | — | Secret-shape regex matching | No new dep needed; patterns are straightforward [VERIFIED: research/STACK.md "zero new required deps" envelope] |
| stdlib `platform` + `sys.platform` | — | OS detection for doctor | Canonical Python 2026 approach; no new dep [VERIFIED: tests/test_spawn_backends.py imports `sys` directly] |
| stdlib `shutil.which` | — | Binary availability check for doctor | Already used in `tmux_backend` [VERIFIED: codebase/INTEGRATIONS.md §Tmux backend] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Typer `CliRunner` | via typer | Invoke CLI commands in tests | Established pattern across `tests/test_cli_commands.py`, `tests/test_spawn_cli.py` [VERIFIED: tests/test_spawn_cli.py:3] |
| MagicMock / hand-rolled `RecordingBackend` | stdlib | Mock spawn backend for regression tests | Proven pattern — `test_launch_cli_applies_profile_to_template_agents` already does this [VERIFIED: tests/test_spawn_cli.py:309-341] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib regex secret detection | `detect-secrets`, `gitleaks`, `trufflehog` | Would violate zero-dep constraint; they're designed for repo scanning, not runtime env filtering. Our scope is "filter 6 well-defined patterns at write-time," not "identify arbitrary secrets" [CITED: PROJECT.md:103 "no new required runtime deps"] |
| Custom doctor module | `environs`, `python-doctor` | No stdlib alternatives for "detect CLI X and print install command" exist as libraries. Every project rolls this: Flutter, Homebrew, pipx. Reinventing for our 5 tools is ~100 LOC [VERIFIED: WebSearch — no python-doctor library for this exact pattern] |
| Rust-style RFC process | Python PEP / MADR ADR | MADR (Markdown Any Decision Records) is too granular for a cross-cutting API proposal. Rust's 0000-template.md in `text/` is the right size for our use case [CITED: rust-lang.github.io/rfcs/0002-rfc-process.html] |

**Installation:**
```bash
# No new packages for Phase 0.
pip install -e '.[dev]'  # already the standard dev install
```

**Version verification (sanity check):**
```bash
# Nothing new to verify — Phase 0 uses existing deps only.
python -c "import pytest, typer, rich, pydantic; print(pytest.__version__, typer.__version__)"
```

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Phase 0 Deliverables — all additive, no existing-code mutations   │
└─────────────────────────────────────────────────────────────────────┘

  ┌───────────────────────────────┐
  │ 1. Regression Matrix          │
  │                               │
  │ tests/test_template_          │──┐
  │      regression_matrix.py     │  │  pytest → CliRunner → RecordingBackend
  │                               │  │  (no real processes spawned)
  │ @pytest.mark.parametrize(     │  │
  │   "template",                 │  ▼
  │   ["software-dev","hedge-..."])│   ┌─────────────────────────┐
  │                               │   │ clawteam.cli.commands   │
  └───────────────────────────────┘   │ `launch` command        │
                                      └─────────────────────────┘
                                                │
                                                ▼
                                      ┌─────────────────────────┐
                                      │ load_template()         │
                                      │ TeamManager.create_team │
                                      │ TaskStore               │
                                      │ RecordingBackend.spawn  │
                                      └─────────────────────────┘
                                                │
                                                ▼
                                      assert behaviors match
                                      golden-path expectations

  ┌───────────────────────────────┐
  │ 2. Env Deny-Filter            │
  │                               │
  │ clawteam/util/secrets.py NEW  │    ┌────────────────────────────┐
  │ is_secret_key(name) → bool    │──▶ │ clawteam/events/hooks.py:81│
  │ scrub_env(env) → dict         │    │  env = scrub_env(          │
  │                               │    │         os.environ.copy()) │
  │ deny-pattern:                 │    └────────────────────────────┘
  │  *_KEY, *_TOKEN, *_SECRET,    │    ┌────────────────────────────┐
  │  *PASSWORD*, *BEARER*,        │──▶ │ clawteam/spawn/*_backend.py│
  │  *CREDENTIAL*, *ACCESS_KEY*,  │    │  (optional defense-in-depth)│
  │  SENTRY_DSN, DATABASE_URL w/@ │    └────────────────────────────┘
  │                               │    ┌────────────────────────────┐
  │ allow-list exceptions:        │──▶ │ future: board collector,   │
  │  CLAWTEAM_*, OH_*,            │    │  /learn ingestion — Phase  │
  │  CLAUDE_CODE_*, LANG, PATH,   │    │  6 reuses same helper      │
  │  ANTHROPIC_BASE_URL           │    └────────────────────────────┘
  └───────────────────────────────┘

  ┌───────────────────────────────┐
  │ 3. clawteam doctor            │
  │                               │
  │ clawteam/doctor.py NEW        │    ┌────────────────────────────┐
  │ DoctorReport pydantic model   │──▶ │ clawteam/cli/commands.py   │
  │ check_tool(name, hints) →     │    │ @app.command("doctor")     │
  │      ToolStatus               │    │ → rich.Table + --json      │
  │                               │    └────────────────────────────┘
  │ detect_os() →                 │
  │  linux-apt|linux-dnf|         │
  │  linux-pacman|macos|windows   │
  │                               │
  │ Tools checked:                │
  │  - chromium (via playwright)  │
  │  - codex CLI                  │
  │  - ngrok                      │
  │  - watchdog (py pkg)          │
  │  - gource                     │
  │  - tmux, git (required not    │
  │    optional — always report)  │
  └───────────────────────────────┘

  ┌───────────────────────────────┐
  │ 4. Default model_profile      │
  │                               │
  │ clawteam/config.py            │    ┌────────────────────────────┐
  │  ClawTeamConfig +=            │──▶ │ clawteam/spawn/profiles.py │
  │    default_model_profile:     │    │  resolve_model_profile()   │
  │    str = "balanced"           │    │  NEW helper                │
  │                               │    │  rejects silent "quality"  │
  │ clawteam/templates/__init__.py│    └────────────────────────────┘
  │  TemplateDef +=               │
  │    model_profile: str|None    │
  │    (None ⇒ falls back to      │
  │     config default ⇒          │
  │     "balanced")               │
  └───────────────────────────────┘

  ┌───────────────────────────────┐
  │ 5. Upstream RFC               │
  │                               │
  │ docs/rfcs/                    │    ┌────────────────────────────┐
  │   001-phase-registry.md NEW   │──▶ │ PR against upstream        │
  │                               │    │ ClawTeam repo              │
  │ Template: Rust 0000-template  │    │ (HKUDS/ClawTeam)           │
  │ shape, adapted:               │    │                            │
  │  - Summary                    │    │ Goal: ≥1 maintainer        │
  │  - Motivation                 │    │ acknowledgement before     │
  │  - Detailed design            │    │ Phase 1 code lands         │
  │    - PhaseRegistry shape      │    └────────────────────────────┘
  │    - HarnessPlugin hooks      │
  │    - SprintState model        │
  │    - InteractionGate          │
  │  - Drawbacks / Alternatives   │
  │  - Rollout / Compat           │
  │  - Unresolved questions       │
  │  - Worked example: software-  │
  │    dev.toml unchanged         │
  └───────────────────────────────┘
```

### Recommended Project Structure

All Phase 0 additions (new files only — zero edits outside the listed attach points):

```
clawteam/
├── util/
│   ├── __init__.py                      # NEW — package marker
│   └── secrets.py                       # NEW — is_secret_key(), scrub_env()
├── doctor.py                            # NEW — DoctorReport model + check functions
├── events/hooks.py                      # ATTACH: call scrub_env() at line ~81
├── spawn/
│   ├── subprocess_backend.py            # OPTIONAL ATTACH: scrub_env() at line ~38
│   ├── tmux_backend.py                  # OPTIONAL ATTACH: scrub_env() at line ~65
│   └── wsh_backend.py                   # OPTIONAL ATTACH: scrub_env() at line ~243
├── cli/
│   └── commands.py                      # ATTACH: @app.command("doctor") near line ~3864
├── config.py                            # ATTACH: ClawTeamConfig += default_model_profile
├── spawn/profiles.py                    # ATTACH: resolve_model_profile() helper
└── templates/__init__.py                # ATTACH: TemplateDef += model_profile field
docs/
└── rfcs/
    ├── README.md                        # NEW — short index, "what is an RFC here"
    └── 001-phase-registry.md            # NEW — the actual proposal
tests/
├── test_template_regression_matrix.py   # NEW — parametrized across 6 templates
├── test_secrets.py                      # NEW — is_secret_key() + scrub_env() unit tests
├── test_doctor.py                       # NEW — DoctorReport per-OS golden tests
├── test_config.py                       # EXTEND — test default_model_profile = "balanced"
└── test_templates.py                    # EXTEND — test TemplateDef model_profile field
.github/workflows/
└── ci.yml                               # ATTACH: no changes needed if test discovery is
                                         #   unchanged. Existing matrix covers all 3 py + 2 OS.
```

### Pattern 1: Parametrized Template Regression Matrix
**What:** Single test module that parametrizes across the 6 templates, driving each through the existing `launch` CLI with a `RecordingBackend` that captures spawn calls without running real processes.

**When to use:** Every existing template's spawn → task-creation → prompt-build path needs to be validated on every PR. Target runtime: <10s total (~1s per template).

**Example (proven pattern — adapted from tests/test_spawn_cli.py:309-341):**
```python
# Source: tests/test_spawn_cli.py:20-29, :309-341 (RecordingBackend + launch test)
import pytest
from typer.testing import CliRunner
from clawteam.cli.commands import app
from clawteam.team.manager import TeamManager
from clawteam.team.tasks import TaskStore

class RecordingBackend:
    def __init__(self): self.calls = []
    def spawn(self, **kwargs):
        self.calls.append(kwargs)
        return f"Agent '{kwargs['agent_name']}' spawned"
    def list_running(self): return []

EXISTING_TEMPLATES = [
    "software-dev",
    "hedge-fund",
    "code-review",
    "harness-default",
    "research-paper",
    "strategy-room",
]

@pytest.mark.parametrize("template_name", EXISTING_TEMPLATES)
def test_template_launches_cleanly(monkeypatch, tmp_path, template_name):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["launch", template_name, "--team", f"test-{template_name}",
         "--goal", "smoke-test goal", "--no-workspace"],
        env={"CLAWTEAM_DATA_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0, f"{template_name} launch failed: {result.output}"
    assert backend.calls, f"{template_name} spawned no agents"

    # Team + tasks exist
    team = TeamManager.get_team(f"test-{template_name}")
    assert team is not None
    # Every agent got a CLAWTEAM_TEAM_NAME env and a prompt
    for call in backend.calls:
        assert call["team_name"] == f"test-{template_name}"
        assert call["prompt"]  # non-empty
```

**Speed:** With `RecordingBackend`, no real spawn happens. Each parametrize-case creates a team (fast file I/O into `tmp_path`), loads TOML, and mock-spawns agents. Empirically `tests/test_spawn_cli.py` runs in <2s for its ~20 launch-based cases; 6 parametrize cases here target <3s total. [VERIFIED: pattern proven in tests/test_spawn_cli.py]

**Why `tmux` backend is NOT used in tests:** `RecordingBackend` replaces whatever backend name `get_backend` returns; this is already how existing tests handle it. No test runs real tmux. [VERIFIED: tests/test_spawn_cli.py:39 "`get_backend` replaced via monkeypatch"]

### Pattern 2: Deny-Pattern Env Scrubbing with Allow-List Exceptions
**What:** A pair of pure functions in `clawteam/util/secrets.py` that (a) answer "is this env var name secret-shaped?" and (b) return a scrubbed copy of an env dict with secrets replaced by a placeholder marker.

**When to use:** Any code path that copies, logs, persists, or broadcasts `os.environ` or an env dict derived from it — most critically `_make_shell_handler` in events/hooks.py, and optionally the three `os.environ.copy()` sites in spawn backends.

**Example (pattern):**
```python
# Source: ports well-established secret-shape regex → applied at write-time.
# See mazen160/secrets-patterns-db high-confidence generics [CITED]
# + codebase/CONCERNS.md "Secrets in env" recommendation.

import re
from typing import Mapping

_SECRET_NAME_PATTERNS = [
    re.compile(r".*_?KEY$"),         # API_KEY, APIKEY, OPENAI_API_KEY, _API_KEY
    re.compile(r".*_?TOKEN$"),       # GITHUB_TOKEN, AUTH_TOKEN
    re.compile(r".*_?SECRET.*"),     # CLIENT_SECRET, SECRET_ACCESS_KEY
    re.compile(r".*PASSWORD.*"),     # DB_PASSWORD, PASSWORD
    re.compile(r".*_?CREDENTIAL.*"), # AWS_CREDENTIAL, GOOGLE_APPLICATION_CREDENTIALS
    re.compile(r".*BEARER.*"),       # BEARER_TOKEN
    re.compile(r".*ACCESS_KEY.*"),   # AWS_ACCESS_KEY_ID, ACCESS_KEY
    re.compile(r".*_?DSN$"),         # SENTRY_DSN (often contains a secret)
    re.compile(r".*AUTH$"),          # X_AUTH, OPENAI_AUTH
    re.compile(r".*PRIVATE_KEY.*"),  # SSH_PRIVATE_KEY
    re.compile(r".*SESSION_KEY.*"),
]

# Names we deliberately keep even though they may match a pattern —
# adapter needs these to pass through to child CLIs.
_ALLOWLIST = frozenset({
    # Base URLs are not themselves secret; they configure endpoints
    "ANTHROPIC_BASE_URL", "OPENAI_BASE_URL",
    "KIMI_BASE_URL", "GOOGLE_GEMINI_BASE_URL",
    # Our own identity envs must propagate
    # (they don't match the secret patterns, but belt-and-braces)
})

SECRET_PLACEHOLDER = "***REDACTED***"


def is_secret_key(name: str) -> bool:
    """Return True if an env-var name looks like it holds a secret."""
    if name in _ALLOWLIST:
        return False
    upper = name.upper()
    return any(p.match(upper) for p in _SECRET_NAME_PATTERNS)


def scrub_env(env: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of env with secret-shaped values replaced by a placeholder.

    Keys are preserved (so downstream log shapes remain stable) but values
    for matching keys are replaced. This is destination-agnostic: callers
    decide when scrubbing is appropriate (logging, event payloads, memory
    ingestion — NOT child-process spawn, which needs the real secret).
    """
    return {
        k: (SECRET_PLACEHOLDER if is_secret_key(k) else v)
        for k, v in env.items()
    }
```

**Deny-pattern vs allow-list vs combined (research verdict):**
- Pure deny-pattern: safer default (closed-world) but can flag non-secrets (e.g., `ANTHROPIC_BASE_URL` contains `_KEY`-adjacent shape → not currently in the pattern set but worth the allowlist safety net).
- Pure allow-list: guaranteed nothing passes through that wasn't approved. Bad for a harness that forwards arbitrary provider API keys (`*_API_KEY` varies per provider), would require per-release maintenance.
- **Combined (recommended):** deny-by-pattern + explicit allowlist of non-secret fields that happen to match. Matches industry practice (gitleaks-style) [CITED: mazen160/secrets-patterns-db]. Pattern list has ~11 regex entries; allowlist is ~4 entries.

**Write-site vs read-site placement (research verdict):**
- Write-site (scrub before every potential exposure): defense-in-depth; catches secrets at every log/event/memory-ingestion point. Cost: call-site discipline; must remember to scrub in every new write point.
- Read-site (single chokepoint): one place to maintain. Cost: need every consumer to route through that chokepoint, which isn't how the existing code works (e.g., `os.environ.copy()` is used in four places directly).
- **Recommended (defense-in-depth, write-site-first):** scrub at `events/hooks.py:81` mandatorily (the single documented leak point per CONCERNS.md:83-87), and expose `scrub_env()` for any future write point. Do NOT scrub the spawn-backend env dicts because child processes legitimately need the real `ANTHROPIC_API_KEY` etc. Instead, add a unit-test assertion that the spawn backends' env dicts do propagate known API keys (regression guard against accidentally wiring scrub to the wrong place).

### Pattern 3: `clawteam doctor` Tool Detector
**What:** A top-level CLI command that enumerates a fixed set of optional tools, checks per-tool presence/version, detects OS, and prints per-OS install hints for missing tools.

**When to use:** First-run UX; debugging "why doesn't browse work?"; CI smoke test on fresh installs.

**Example:**
```python
# clawteam/doctor.py
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from importlib.util import find_spec

from pydantic import BaseModel


@dataclass(frozen=True)
class ToolCheck:
    name: str                       # e.g. "chromium"
    kind: str                       # "cli" | "python-pkg" | "browser"
    check_cmd: list[str] | None     # for --version; None for python-pkg
    python_module: str | None       # for python-pkg ("playwright", "watchdog")
    install_hints: dict[str, str]   # os-key → install command


class ToolStatus(BaseModel):
    name: str
    available: bool
    version: str = ""
    hint: str = ""
    required: bool = False


class DoctorReport(BaseModel):
    os: str  # "linux-apt" | "linux-pacman" | "linux-dnf" | "macos" | "windows" | "unknown"
    python_version: str
    tools: list[ToolStatus]
    missing_optional: int
    missing_required: int


def detect_os_flavor() -> str:
    """Return a platform identifier usable as a key into per-OS install hints."""
    if sys.platform == "darwin":
        return "macos"
    if sys.platform == "win32":
        return "windows"
    if sys.platform.startswith("linux"):
        # Distinguish package managers for install hints
        for pm in ("apt", "dnf", "pacman", "zypper"):
            if shutil.which(pm):
                return f"linux-{pm}"
        return "linux"
    return "unknown"


def check_cli(name: str, version_cmd: list[str]) -> tuple[bool, str]:
    """Check if a CLI is on PATH and grab its version string (best-effort)."""
    path = shutil.which(name)
    if not path:
        return False, ""
    try:
        out = subprocess.run(version_cmd, capture_output=True, timeout=5, text=True)
        return True, out.stdout.strip().splitlines()[0] if out.stdout else ""
    except Exception:
        return True, "(version check failed)"


def check_python_pkg(module: str) -> tuple[bool, str]:
    spec = find_spec(module)
    if spec is None:
        return False, ""
    try:
        import importlib
        mod = importlib.import_module(module)
        return True, getattr(mod, "__version__", "")
    except Exception:
        return True, ""


TOOL_CHECKS: list[ToolCheck] = [
    ToolCheck(
        name="chromium (via playwright)",
        kind="browser",
        check_cmd=None,
        python_module="playwright",
        install_hints={
            "linux-apt": "pip install 'clawteam[browser]' && playwright install chromium",
            "linux-dnf": "pip install 'clawteam[browser]' && playwright install chromium",
            "linux-pacman": "pip install 'clawteam[browser]' && playwright install chromium",
            "macos": "pip install 'clawteam[browser]' && playwright install chromium",
            "windows": "pip install 'clawteam[browser]' && playwright install chromium",
        },
    ),
    ToolCheck(
        name="codex",
        kind="cli",
        check_cmd=["codex", "--version"],
        python_module=None,
        install_hints={
            "linux-apt": "npm install -g @openai/codex  # or brew install codex",
            "linux-dnf": "npm install -g @openai/codex",
            "linux-pacman": "yay -S codex-cli  # or npm install -g @openai/codex",
            "macos": "brew install codex  # or npm install -g @openai/codex",
            "windows": "winget install OpenAI.Codex  # or npm install -g @openai/codex",
        },
    ),
    ToolCheck(
        name="ngrok",
        kind="cli",
        check_cmd=["ngrok", "version"],
        python_module=None,
        install_hints={
            "linux-apt": "curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | "
                         "sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null "
                         "&& echo 'deb https://ngrok-agent.s3.amazonaws.com buster main' "
                         "| sudo tee /etc/apt/sources.list.d/ngrok.list "
                         "&& sudo apt update && sudo apt install ngrok",
            "linux-dnf": "sudo dnf install ngrok",
            "linux-pacman": "yay -S ngrok",
            "macos": "brew install ngrok",
            "windows": "winget install Ngrok.Ngrok  # or choco install ngrok",
        },
    ),
    ToolCheck(
        name="watchdog (python)",
        kind="python-pkg",
        check_cmd=None,
        python_module="watchdog",
        install_hints={
            # Same on every OS — pure Python
            "_all": "pip install watchdog",
        },
    ),
    ToolCheck(
        name="gource",
        kind="cli",
        check_cmd=["gource", "--help"],
        python_module=None,
        install_hints={
            "linux-apt": "sudo apt install gource",
            "linux-dnf": "sudo dnf install gource",
            "linux-pacman": "sudo pacman -S gource",
            "macos": "brew install gource",
            "windows": "choco install gource",
        },
    ),
]
```

**`--fix` flag verdict: DO NOT SHIP.** PROJECT.md "Out of Scope" explicitly lists "Auto-installing external tools" as anti-feature. `doctor` prints commands; users copy-paste. [CITED: PROJECT.md:77, REQUIREMENTS.md Out of Scope table]

**Idempotence:** `doctor` reads-only; safe to run repeatedly. Exit code 0 if all required present (exit 0 even with missing optionals, per ROADMAP success criterion 3). [CITED: ROADMAP.md Phase 0 success criterion 3]

### Pattern 4: Default Model Profile Resolution
**What:** Add `default_model_profile` to `ClawTeamConfig`; add `model_profile` optional field to `TemplateDef`; add a resolver helper that rejects silent "quality" defaults.

**When to use:** Template loading when `gstack.toml` (Phase 3) reads its profile; Phase-3 spawn path reads resolved profile to pick per-role models.

**Example (attach point into existing config):**
```python
# clawteam/config.py — ATTACH to existing ClawTeamConfig
class ClawTeamConfig(BaseModel):
    # ... existing fields ...
    default_model_profile: str = "balanced"  # NEW — never "quality" by default
    # ...

# clawteam/spawn/profiles.py — NEW helper (adjacent to existing resolve_profile_name)
def resolve_model_profile(
    template_profile: str | None,
    cli_override: str | None = None,
) -> str:
    """Resolve effective model_profile with explicit opt-in for 'quality'.

    Priority:
    1. Explicit --model-profile CLI flag (if 'quality', OK because explicit)
    2. Template field (if 'quality', OK because template explicitly chose it)
    3. Config default_model_profile (defaults to 'balanced')
    4. Hard-coded 'balanced' fallback

    Never silently resolves to 'quality' — quality must be explicit.
    """
    if cli_override:
        return cli_override
    if template_profile:
        return template_profile
    from clawteam.config import load_config
    cfg = load_config()
    resolved = cfg.default_model_profile or "balanced"
    # Sanity — codified failure if config was tampered to silently "quality"
    # is actually fine because user did touch config. The silent-quality-rejection
    # is about NOT implicitly promoting to quality when nothing is set.
    return resolved
```

**Where to hard-code the profile → model mapping:** NOT HERE. Per REQUIREMENTS.md traceability, QUALITY-12 (cost observability with Opus/Sonnet/Haiku mapping) ships in Phase 7, not Phase 0. Phase 0 establishes the *resolution path* — that `balanced` is the default and never silently becomes `quality`. The actual `balanced = {ceo: Opus, engineer: Sonnet, shipper: Haiku, ...}` wiring ships in Phase 3's `gstack.toml` + Phase 7's model-fallback-ladder. [CITED: REQUIREMENTS.md traceability table]

### Pattern 5: Upstream RFC Document
**What:** A markdown file at `docs/rfcs/001-phase-registry.md` following Rust RFC 0000-template shape, proposing the Phase-1 API surface and its additive-only guarantees.

**When to use:** Phase 0 deliverable; reviewed by upstream ClawTeam maintainer(s) BEFORE Phase 1 code lands. [CITED: ROADMAP.md Phase 0 success criterion 4]

**Structure (adapted from [rust-lang/rfcs 0000-template.md](https://github.com/rust-lang/rfcs/blob/master/text/0000-template.md)):**

```markdown
---
rfc: 001
title: PhaseRegistry + 3 HarnessPlugin Hooks + SprintState + InteractionGate
status: Proposed
authors: [ClawTeam-gstack fork contributors]
created: 2026-04-15
target-phase: Phase 1 of gstack-integration roadmap
---

# Summary
One-paragraph motivation + outcome.

# Motivation
Why this change is needed; how it serves non-gstack templates too.

# Detailed Design
## PhaseRegistry
- class shape
- population via HarnessPlugin.contribute_phases()
- collision detection (ValueError at registration)

## HarnessPlugin hooks (3 new, all optional with empty defaults)
- `contribute_phases() -> list[Phase]`
- `contribute_phase_roles() -> dict[str, str]`
- `contribute_review_routers() -> list[ReviewRouter]`

## SprintState
- pydantic v2 model
- persistence path

## InteractionGate
- PhaseGate subclass

## Additive-only contract
- No mutations to existing `PhaseState` semantics
- `software-dev.toml` (etc.) work unchanged — worked example

# Drawbacks
Maintenance burden of 3 new hooks; possible misuse by plugin authors.

# Rationale and Alternatives
- Why not extend PhaseState directly? (breaks BC)
- Why not a new HarnessV2 orchestrator? (fork, not landable)

# Rollout
Phase 1 implementation plan; regression-matrix verification (Phase 0).

# Unresolved Questions
- Windows CI scope
- Which existing templates should opt into the new hooks (probably none in v1)

# Worked Example
Full trace: spawning `software-dev` before and after this RFC — no behavior change.
```

**Target channel (recommended):** PR against the upstream ClawTeam repo adding `docs/rfcs/001-phase-registry.md`. Rationale: PRs are how this codebase tracks changes (CI runs on PRs); maintainers can comment inline; the RFC lives in git history. Opening a GitHub Discussion instead would be weaker provenance.

**Where to find the maintainer:** `pyproject.toml` lists `HKUDS` + `jiabintang77@gmail.com` as author [VERIFIED: pyproject.toml:8-10]. `[project.urls]` points at `https://github.com/HKUDS/ClawTeam` [VERIFIED: pyproject.toml:43-46]. No CONTRIBUTING.md in the repo [VERIFIED: no such file in Glob]. Recommendation: open PR against `HKUDS/ClawTeam` main, tag maintainer, mirror the RFC under our fork's `docs/rfcs/` so Phase 1 can reference it regardless of upstream merge timing.

### Anti-Patterns to Avoid
- **Adding `pytest-xdist` or similar "speed up matrix" deps:** Violates zero-dep constraint. The 6-template matrix at ~500ms per template with RecordingBackend is already <3s serial.
- **Running real tmux or real subprocesses in regression matrix:** Would make CI flaky on macOS runners; tests that mock the backend do the same coverage job and run 100x faster. [CITED: codebase/TESTING.md:147 "What to mock: subprocess.Popen, shutil.which, external-process spawners"]
- **Putting scrub_env() into `identity.py`:** Makes it look like part of identity lookup. Scrubbing is a cross-cutting filter concern — put it in `util/secrets.py` and call from the (few) sites that need it.
- **`doctor` exit code 1 on missing optional tools:** ROADMAP success criterion 3 says exit 0. Save exit 1 for "missing a REQUIRED tool (tmux, git)".
- **Per-template regression test files:** Duplicates test boilerplate across 6 files. Parametrize.
- **Using `pyyaml` for RFC frontmatter:** STACK.md §4 established the "handcoded flat-kv parser" pattern; frontmatters are informational, not parsed by runtime code. The RFC markdown is read by humans and PR reviewers, not by code.
- **Writing the `_env()` modernization into Phase 0:** research/SUMMARY.md Gaps #6 explicitly leaves this open; CONCERNS.md:128-131 flags it as fragile but not urgent. Scope Phase 0 to scrubbing only; env-lookup refactor is separate tech debt.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret detection across hundreds of formats | Full secrets-patterns-db port (1600+ regexes) | Targeted 11-pattern name-regex list (KEY/TOKEN/SECRET/PASSWORD/BEARER/CREDENTIAL/ACCESS_KEY/DSN/AUTH/PRIVATE_KEY/SESSION_KEY) | We filter by env-var NAME not value; most "generic API key" regexes match value-shapes (base64, UUIDs) that cause massive false-positives. Name-shape matching is sufficient + lossless + zero-dep [CITED: mazen160/secrets-patterns-db README] |
| CLI test harness | Custom test runner for template launches | `typer.testing.CliRunner` + `monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: RecordingBackend())` | Established pattern, 20+ existing tests [VERIFIED: tests/test_spawn_cli.py, test_cli_commands.py] |
| OS detection | Custom `/etc/os-release` parser or `distro` dep | `sys.platform` + `shutil.which(<package-manager>)` | Our branching is coarse (apt/dnf/pacman/macos/windows); reading `/etc/os-release` doesn't help for install-command selection |
| RFC tooling | `adr-tools-python` dep | Plain markdown file in `docs/rfcs/` | MADR adds ceremony; Rust-style RFC is a single markdown file. Zero deps [CITED: martinfowler.com/bliki/ArchitectureDecisionRecord.html "lightweight markup, easily read and diffed"] |
| Multi-OS install command templates | Package-manager abstraction library (e.g., `package_manager` PyPI) | Hard-coded per-OS hint strings in TOOL_CHECKS list | We have 5 tools × 5 OS flavors = 25 hints. Flat literal strings beat introducing a library whose schema must be maintained |
| Version extraction across 5 CLIs | Parsed semver library | `stdout.strip().splitlines()[0]` | For a status report, "the version string as the tool printed it" is the right UX; parsing risks hiding info [CITED: flutter doctor pattern] |

**Key insight:** Every one of the 5 deliverables has "obvious library to reach for" traps. Phase 0's zero-dep constraint is not austerity theater — each library considered (`detect-secrets`, `distro`, `adr-tools-python`, `pytest-xdist`) would either duplicate stdlib or introduce its own maintenance surface for a feature that needs ~50 LOC.

## Common Pitfalls

### Pitfall 1: Regression matrix is flaky in CI because it reads real `~/.clawteam`
**What goes wrong:** A test hits real home directory because the `isolated_data_dir` fixture is accidentally not applied (e.g., test file lives outside `tests/` or defines its own conftest).
**Why it happens:** `isolated_data_dir` is `autouse=True` but only in `tests/conftest.py`; a parallel conftest in a subdir can shadow it. [VERIFIED: tests/conftest.py:10]
**How to avoid:** Keep the regression test in the top-level `tests/` directory. Don't add subdirs. The existing flat layout [CITED: codebase/STRUCTURE.md §tests] is itself the defense.
**Warning signs:** Test that passes locally but fails when `~/.clawteam` has unexpected content. Test that writes to `$HOME/something` instead of `tmp_path`.

### Pitfall 2: Env scrub blocks legitimate provider API keys from reaching child processes
**What goes wrong:** Someone applies `scrub_env()` to the env dict passed into `subprocess.Popen(env=...)`, and child `claude` process can't see `ANTHROPIC_API_KEY`.
**Why it happens:** Confusion about scrub scope — the filter is for *observability* surfaces (logs, event payloads, memory), not *runtime* env passing to children.
**How to avoid:** Document scrub_env() as "apply before logging/persisting/broadcasting; never before spawning a child process." Add a regression test that spawn backends still propagate `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` through `env` arg. (The existing `test_spawn_cli.py:159-160` test already guards this for the preset path — extend it.) [VERIFIED: tests/test_spawn_cli.py:149-160]
**Warning signs:** Child agent reports "no API key" after Phase 0; integration test for spawn regression starts failing unexpectedly.

### Pitfall 3: `clawteam doctor` hangs on `subprocess.run(["codex", "--version"])` because codex starts a REPL
**What goes wrong:** Some CLIs (kimi, pi) treat `--version` as unknown and fall through to interactive mode; subprocess hangs the doctor command indefinitely.
**Why it happens:** Not all CLIs have a clean `--version` flag.
**How to avoid:** Always use `timeout=5` on the subprocess call (already in the example pattern above). On timeout, report "(version check failed)" but still mark `available: true` — PATH presence is the primary signal. [VERIFIED: subprocess.run timeout pattern in clawteam/events/hooks.py:96-97]
**Warning signs:** `doctor` command takes >10s; CI job "doctor smoke" times out.

### Pitfall 4: Default `balanced` gets silently promoted to `quality` via config env var
**What goes wrong:** A stray `CLAWTEAM_DEFAULT_PROFILE=quality` in env causes spawns to use Quality tier; user never opted in; cost blows up.
**Why it happens:** `ClawTeamConfig.default_profile` already has env-var override plumbing via `get_effective()` [VERIFIED: clawteam/config.py:103-119]. If we add `default_model_profile` the same way, env var can silently override.
**How to avoid:** Keep `default_model_profile` OUT of the env-var map in `get_effective()`. Resolution order: CLI flag → template field → config file → hard-coded "balanced". No env-var shortcut. Document this constraint in the resolver's docstring. [CITED: ROADMAP.md Phase 0 success criterion 5: "must be explicitly opted into via --model-profile quality or config"]
**Warning signs:** Phase 7 (cost observability) surfaces "why are all my agents Opus?" complaints from users who never set `--model-profile quality`.

### Pitfall 5: RFC gets shipped but never reviewed because it's in our fork's `docs/rfcs/` only
**What goes wrong:** We write the RFC, commit to our fork, and the upstream maintainer never sees it. ROADMAP success criterion 4 specifically requires maintainer acknowledgement.
**Why it happens:** Forks commit freely; upstream doesn't auto-poll fork diffs.
**How to avoid:** Open a PR against upstream (HKUDS/ClawTeam) with just the RFC markdown. Keep a mirror in our fork at same path so Phase 1 can reference it regardless of merge status. Explicitly tag maintainer in PR body.
**Warning signs:** Upstream repo has no new issues/PRs 2 weeks after Phase 0 declares done.

### Pitfall 6: Regression matrix takes too long because it enumerates full template agents
**What goes wrong:** `hedge-fund.toml` defines 5 agents [VERIFIED: tests/test_templates.py:72-77]; if we assert on every spawn call sequentially with real prompt rendering, the test bloats.
**Why it happens:** Temptation to "test everything" per template.
**How to avoid:** The assertion is "did `launch` finish exit 0 and populate team, tasks, and N spawn calls?" not "do all the prompts contain the right substrings?" Detailed prompt assertions belong in `tests/test_templates.py` (which already covers them). [VERIFIED: tests/test_templates.py:129-146]
**Warning signs:** Test runtime exceeds 10s; test file grows >200 lines.

## Runtime State Inventory

Phase 0 is a pure additive-only phase (no renames, no data-layout changes, no string-replacement sweeps).

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — no persisted keys, collection names, or user_ids reference Phase 0 deliverables | None |
| Live service config | None — no external services configured via this phase | None |
| OS-registered state | None — no systemd/pm2/Task Scheduler tasks added or renamed | None |
| Secrets/env vars | `CLAWTEAM_DEFAULT_PROFILE` env var already exists in config.py env_map [VERIFIED: clawteam/config.py:107]; we intentionally do NOT add a new one (see Pitfall #4). No secret renames | None |
| Build artifacts | `pyproject.toml` unchanged. No new package entry points | None |

**Nothing found in category:** Verified by reading the five deliverables' attach points and confirming they all produce new files or additive fields. No grep-sweep of existing strings is required.

## Environment Availability

Phase 0 has no new external tool dependencies, but the `clawteam doctor` command itself needs to probe tools on the target machine. Verified on the research host (current machine):

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | All Phase 0 code | ✓ | 3.14.4 (host) | Required minimum 3.10 per pyproject [VERIFIED] |
| pytest 9+ | Regression matrix | ✓ | via dev extras | — |
| ruff | Lint | ✓ | via dev extras | — |
| tmux | Required for existing tmux backend (not Phase 0 itself, but the matrix exercises the `launch` CLI which reads `backend = "tmux"` from TOML) | ✓ | /usr/bin/tmux [VERIFIED: Bash probe] | Tests use RecordingBackend so actual tmux never executes — available but not invoked |
| git | Required for worktree tests (not Phase 0 regression matrix which uses `--no-workspace`) | ✓ | /usr/bin/git [VERIFIED: Bash probe] | — |
| playwright (py pkg) | `doctor` to probe for | ✗ | — | `doctor` reports missing + prints install hint; no fallback needed at test time |
| codex (CLI) | `doctor` to probe for | ✓ | /usr/bin/codex [VERIFIED: Bash probe] | — |
| ngrok (CLI) | `doctor` to probe for | ✓ | /usr/local/bin/ngrok [VERIFIED] | — |
| watchdog (py pkg) | `doctor` to probe for | ✗ | — | `doctor` reports; no runtime dep |
| gource (CLI) | `doctor` to probe for | ✗ | — | `doctor` reports; no runtime dep |

**Missing dependencies with no fallback:** None — Phase 0 is all test/doc/CLI additions; nothing blocks execution on the current host.

**Missing dependencies with fallback:** Three of the five `doctor`-probed tools are absent on the research host (playwright, watchdog, gource). This is NOT a Phase 0 blocker — it's the exact case `doctor` is designed to surface. Those tools ship in Phase 6 (browser) and Phase 7 (attend queue) plans.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest >=9.0,<10.0 [VERIFIED: pyproject.toml:32] |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` — `testpaths = ["tests"]` [VERIFIED] |
| Quick run command | `ruff check clawteam/ tests/ && pytest tests/test_template_regression_matrix.py -q` (example per deliverable) |
| Full suite command | `pytest tests/ -v --tb=short` [VERIFIED: .github/workflows/ci.yml:32] |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-03 | 6 existing templates launch cleanly with no behavior change | integration (mocked backend) | `pytest tests/test_template_regression_matrix.py -x -q` | ❌ Wave 0 |
| QUALITY-14 | Regression matrix runs on every CI push/PR | CI workflow | Existing `.github/workflows/ci.yml` "test" job matrix picks up new test file automatically | ✅ (ci.yml exists; new test file auto-discovered by `testpaths = ["tests"]`) |
| QUALITY-15 | `is_secret_key()` returns True for each of ~11 patterns; False for allowlist entries + canonical `CLAWTEAM_*` envs | unit | `pytest tests/test_secrets.py -x -q` | ❌ Wave 0 |
| QUALITY-15 | `scrub_env()` removes values for secret-shaped names, preserves others | unit | `pytest tests/test_secrets.py::test_scrub_env_preserves_non_secrets -x` | ❌ Wave 0 |
| QUALITY-15 | `hooks._make_shell_handler` env includes scrubbed values when run against fixture seeded with `OPENAI_API_KEY=sk-abc123` | integration | `pytest tests/test_hooks.py::test_shell_handler_env_is_scrubbed -x` | ❌ Wave 0 (new test; the existing tests/ has no test_hooks.py — spot-verified with `ls tests/`) |
| QUALITY-15 | Spawn backends still propagate legitimate `ANTHROPIC_API_KEY` to child process env | integration (regression guard) | `pytest tests/test_spawn_cli.py -k propagates_api_key -x` | EXTEND existing file |
| UX-08 | `clawteam doctor` prints per-OS install hints for missing optional tools | integration | `pytest tests/test_doctor.py -x -q` | ❌ Wave 0 |
| UX-08 | `clawteam doctor` exit code 0 when all required present (even with missing optionals) | integration | `pytest tests/test_doctor.py::test_doctor_exits_0_with_missing_optionals -x` | ❌ Wave 0 |
| UX-08 | `clawteam doctor --json` produces valid JSON with `tools[]` and `os` fields | integration | `pytest tests/test_doctor.py::test_doctor_json_output -x` | ❌ Wave 0 |
| TEAM-06 | `ClawTeamConfig.default_model_profile` defaults to `"balanced"` | unit | `pytest tests/test_config.py -k default_model_profile -x` | EXTEND existing file |
| TEAM-06 | `resolve_model_profile(None, None)` returns `"balanced"`, NOT `"quality"` | unit | `pytest tests/test_profiles.py::test_resolve_balanced_never_silently_quality -x` | EXTEND existing file |
| TEAM-06 | Template loading preserves `model_profile` field if present in TOML | unit | `pytest tests/test_templates.py -k model_profile -x` | EXTEND existing file |
| (RFC deliverable) | `docs/rfcs/001-phase-registry.md` exists with required sections | docs (grep) | `test -f docs/rfcs/001-phase-registry.md && grep -q '^# Detailed Design' docs/rfcs/001-phase-registry.md` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `ruff check clawteam/ tests/ && pytest tests/test_<target>.py -q` (per `.agents/skills/clawteam-dev/SKILL.md`)
- **Per wave merge:** `pytest tests/ -v --tb=short` (the CI job)
- **Phase gate:** Full suite green on all three Python versions × two OS per the existing CI matrix [VERIFIED: .github/workflows/ci.yml:22-32]

### Wave 0 Gaps
- [ ] `tests/test_template_regression_matrix.py` — covers CORE-03, QUALITY-14
- [ ] `tests/test_secrets.py` — covers QUALITY-15 unit path
- [ ] `tests/test_hooks.py` — covers QUALITY-15 integration path (new test file; `events/hooks.py` currently has no test coverage per Concerns "No timeout/failure-path tests" [VERIFIED: codebase/CONCERNS.md:188-191])
- [ ] `tests/test_doctor.py` — covers UX-08
- [ ] `clawteam/util/__init__.py` + `clawteam/util/secrets.py` — new module (no existing `util/` package)
- [ ] `clawteam/doctor.py` — new module
- [ ] `docs/rfcs/` directory + `docs/rfcs/README.md` + `docs/rfcs/001-phase-registry.md` — new
- [ ] Extend `tests/test_config.py` with `default_model_profile` assertion
- [ ] Extend `tests/test_profiles.py` with `resolve_model_profile` assertion
- [ ] Extend `tests/test_templates.py` with `model_profile` field assertion
- [ ] Extend `tests/test_spawn_cli.py` with an explicit "spawn backend env still contains `*_API_KEY` after scrub_env is active on hooks path" regression guard

## Security Domain

Phase 0's QUALITY-15 is itself a security deliverable. ASVS mapping:

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Phase 0) | — |
| V3 Session Management | no (Phase 0) | — |
| V4 Access Control | no (Phase 0) | — |
| V5 Input Validation | yes | `clawteam/paths.py::validate_identifier` already enforces `^[A-Za-z0-9._-]+$` on all team/agent names; Phase 0 uses team names only through this validator [VERIFIED: codebase/ARCHITECTURE.md:139] |
| V6 Cryptography | no (Phase 0) | Env scrubbing is redaction, not cryptography; no key material derived |
| V7 Error Handling | yes | `doctor` timeouts and subprocess failures must return a `ToolStatus` with `available=False` rather than raising, to avoid partial-report issues |
| V8 Data Protection | yes | The deny-filter IS the V8 control — prevents secret values from entering logs, transcripts, memory (Phase 6 downstream) |
| V10 Malicious Code | no (Phase 0) | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leakage via env → shell hook → subprocess stdout → captured log | Information Disclosure | `scrub_env()` at `hooks.py:81` (this phase's QUALITY-15) |
| Secret leakage via transcript → `/learn` memory ingestion | Information Disclosure | Defense-in-depth: same `scrub_env` helper reused by Phase 6 memory-write path [CITED: research/SUMMARY.md:242-243] |
| Doctor probes a malicious CLI that emits ANSI/control-char version string | Information Disclosure (fakery) | `capture_output=True` + first-line-only extraction + `timeout=5` means no pass-through of arbitrary bytes [CITED: pattern in `events/hooks.py:96`] |
| Untrusted `gstack.toml` with `model_profile: "quality"` set by user's existing config file gets silently applied | Elevation of Privilege (cost) | Resolver rejects silent config-file → quality promotion via explicit priority order; `get_effective()` env shortcut intentionally NOT added for `default_model_profile` (Pitfall #4) |
| Regression matrix discovers a template that imports a secret from env → fails in CI with secret in output | Information Disclosure | All test output goes through `isolated_data_dir` autouse; no real env propagation unless test explicitly opts in. The existing matrix (py 3.10/11/12 × ubuntu/macos) already runs hundreds of tests without this issue [VERIFIED: .github/workflows/ci.yml] |

## Code Examples

### Regression matrix test (adapted from tests/test_spawn_cli.py pattern)
```python
# Source: tests/test_spawn_cli.py:20-29, :309-341
# Adapted for parametrize across 6 templates

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app
from clawteam.team.manager import TeamManager

EXISTING_TEMPLATES = [
    "software-dev", "hedge-fund", "code-review",
    "harness-default", "research-paper", "strategy-room",
]


class RecordingBackend:
    def __init__(self):
        self.calls = []
    def spawn(self, **kwargs):
        self.calls.append(kwargs)
        return f"Agent '{kwargs['agent_name']}' spawned"
    def list_running(self):
        return []


@pytest.mark.parametrize("template_name", EXISTING_TEMPLATES)
def test_template_launches_end_to_end(monkeypatch, tmp_path, template_name):
    """Each existing template launches cleanly — no behavior change allowed."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["launch", template_name,
         "--team", f"test-{template_name}",
         "--goal", "BC regression smoke test",
         "--no-workspace"],
        env={"CLAWTEAM_DATA_DIR": str(tmp_path)},
    )

    assert result.exit_code == 0, (
        f"{template_name} launch failed: {result.output}"
    )
    assert backend.calls, f"{template_name} spawned zero agents"

    team = TeamManager.get_team(f"test-{template_name}")
    assert team is not None, f"{template_name} did not create team state"
    assert team.description  # templates all have descriptions

    for call in backend.calls:
        assert call["team_name"] == f"test-{template_name}"
        assert call["agent_name"]
        assert call["prompt"], (
            f"{template_name}:{call['agent_name']} got empty prompt"
        )
```

### Secret detection test
```python
# Source: new file tests/test_secrets.py

import pytest
from clawteam.util.secrets import SECRET_PLACEHOLDER, is_secret_key, scrub_env


class TestIsSecretKey:
    @pytest.mark.parametrize("name", [
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "API_KEY", "APIKEY",
        "GITHUB_TOKEN", "AUTH_TOKEN", "BEARER_TOKEN",
        "CLIENT_SECRET", "SECRET_ACCESS_KEY", "SECRET",
        "DB_PASSWORD", "PASSWORD", "MY_PASSWORD_VALUE",
        "GOOGLE_APPLICATION_CREDENTIALS", "AWS_CREDENTIAL",
        "SSH_PRIVATE_KEY", "SESSION_KEY",
        "AWS_ACCESS_KEY_ID", "ACCESS_KEY",
        "SENTRY_DSN",
    ])
    def test_detects_secret_shapes(self, name):
        assert is_secret_key(name) is True

    @pytest.mark.parametrize("name", [
        "CLAWTEAM_AGENT_NAME", "CLAWTEAM_DATA_DIR", "CLAWTEAM_USER",
        "OH_AGENT_NAME", "CLAUDE_CODE_AGENT_NAME",
        "PATH", "HOME", "USER", "LANG", "LC_CTYPE",
        "ANTHROPIC_BASE_URL", "OPENAI_BASE_URL",
        "ANTHROPIC_MODEL", "ANTHROPIC_DEFAULT_OPUS_MODEL",
    ])
    def test_does_not_flag_non_secrets(self, name):
        assert is_secret_key(name) is False


class TestScrubEnv:
    def test_redacts_api_keys(self):
        env = {"OPENAI_API_KEY": "sk-abc", "PATH": "/usr/bin"}
        result = scrub_env(env)
        assert result["OPENAI_API_KEY"] == SECRET_PLACEHOLDER
        assert result["PATH"] == "/usr/bin"

    def test_preserves_identity_envs(self):
        env = {
            "CLAWTEAM_AGENT_NAME": "alpha",
            "OH_AGENT_NAME": "alpha",
            "CLAUDE_CODE_AGENT_NAME": "alpha",
            "ANTHROPIC_API_KEY": "sk-secret",
        }
        result = scrub_env(env)
        assert result["CLAWTEAM_AGENT_NAME"] == "alpha"
        assert result["OH_AGENT_NAME"] == "alpha"
        assert result["CLAUDE_CODE_AGENT_NAME"] == "alpha"
        assert result["ANTHROPIC_API_KEY"] == SECRET_PLACEHOLDER

    def test_idempotent(self):
        env = {"OPENAI_API_KEY": "sk-abc"}
        once = scrub_env(env)
        twice = scrub_env(once)
        assert once == twice
```

### Hook-path integration test
```python
# Source: new file tests/test_hooks.py
# Verifies that hooks.py:81 applies scrub_env at the documented leak point.

import os

from clawteam.events.bus import EventBus
from clawteam.events.hooks import HookDef, HookManager
from clawteam.events.types import PhaseTransition


def test_shell_handler_env_does_not_leak_api_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-leak")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_should-not-leak")
    monkeypatch.setenv("DB_PASSWORD", "should-not-leak")

    captured_env_path = tmp_path / "captured.env"
    hook = HookDef(
        event="PhaseTransition",
        action="shell",
        # Dump the subprocess env to a file we can inspect
        command=f"env > {captured_env_path}",
        enabled=True,
    )
    bus = EventBus()
    mgr = HookManager(bus)
    assert mgr.register_hook(hook) is True

    bus.emit(PhaseTransition(
        team_name="t", from_phase="plan", to_phase="execute", artifacts=[],
    ))

    # Handler runs synchronously; file should be written
    content = captured_env_path.read_text()
    assert "sk-should-not-leak" not in content
    assert "ghp_should-not-leak" not in content
    assert "should-not-leak" not in content
    # Canonical CLAWTEAM_* envs still present (placeholder value is OK)
    assert "CLAWTEAM_EVENT_TYPE=PhaseTransition" in content
```

### Doctor test (OS-detection branching)
```python
# Source: new file tests/test_doctor.py

from typer.testing import CliRunner
from clawteam.cli.commands import app
from clawteam.doctor import detect_os_flavor


class TestDetectOs:
    def test_darwin(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "darwin")
        assert detect_os_flavor() == "macos"

    def test_win32(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")
        assert detect_os_flavor() == "windows"

    def test_linux_apt(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setattr("shutil.which", lambda c: "/usr/bin/apt" if c == "apt" else None)
        assert detect_os_flavor() == "linux-apt"


class TestDoctorCLI:
    def test_exits_0_with_missing_optionals(self, monkeypatch, tmp_path):
        # Force every optional tool to appear missing
        monkeypatch.setattr("shutil.which", lambda _: None)
        monkeypatch.setattr("importlib.util.find_spec", lambda _: None)

        runner = CliRunner()
        result = runner.invoke(app, ["doctor"],
                               env={"CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")})

        assert result.exit_code == 0
        assert "playwright" in result.output.lower() or "chromium" in result.output.lower()
        assert "install" in result.output.lower()

    def test_json_output_has_os_and_tools(self, monkeypatch, tmp_path):
        import json
        runner = CliRunner()
        result = runner.invoke(app, ["--json", "doctor"],
                               env={"CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "os" in data
        assert "tools" in data
        assert isinstance(data["tools"], list)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Host `~/.clawteam/` in test | `tests/conftest.py` autouse `isolated_data_dir` fixture | Established convention | Every test gets clean state; `HOME`+`USERPROFILE` also redirected. Phase 0 tests inherit this automatically [VERIFIED: tests/conftest.py:10-19] |
| Per-CLI adapter knowledge baked into each test | `RecordingBackend` replacing the backend registry | Established convention | Tests stay fast; no real processes. Phase 0 regression matrix uses same pattern [VERIFIED: tests/test_spawn_cli.py:20-29] |
| `pyyaml` for frontmatter | Handcoded flat-kv `---` parser | STACK.md §4 decision | Zero required deps. Phase 0 RFC frontmatter is human-read only, so even the parser isn't needed — it's informational |
| Secrets scanning via value-shape regex (detect-secrets-style) | Name-shape regex at write-site | CONCERNS.md §Security "Secrets in env" recommendation | Lossless, zero false-positives on API-key values. Fits our scope (env-var filter, not generic scanner) |
| Flutter-style `doctor --fix` auto-install | `doctor` prints hints only | PROJECT.md out-of-scope | Matches "don't ship support-nightmare auto-installers"; users stay in control [CITED: PROJECT.md:77] |
| Rust 0000-template.md RFC | Same shape (8 sections) | Rust-style is the community consensus for code-adjacent RFCs | MADR is for finer-grained decisions; Rust-style fits a cross-cutting API proposal [CITED: rust-lang/rfcs] |

**Deprecated/outdated:**
- `distro` (old Python distro-detection lib) — our OS flavor detection uses `sys.platform` + `shutil.which(<package-manager>)`, which is simpler and covers the 5 branches we need.
- `detect-secrets`, `trufflehog`, `gitleaks` — these are repo-scanning tools, wrong scope for runtime env filtering.
- `adr-tools-python` — heavyweight for a single RFC; we use plain markdown.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 0 does NOT need to ship the actual Opus/Sonnet/Haiku-per-role mapping — that's Phase 3/7 per REQUIREMENTS.md traceability | §Default Model Profile / §User Constraints | If Phase 0 must ship the full mapping, plans underscope the deliverable by ~1 plan-worth of work |
| A2 | Windows CI matrix is NOT a Phase 0 deliverable — ROADMAP.md Phase 0 doesn't explicitly include it (SUMMARY.md Gaps #1 calls it open) | §User Constraints (Deferred) | If Windows IS required v1, the regression matrix must expand to include `windows-latest` in `.github/workflows/ci.yml` matrix, and tmux-backend tests need graceful-skip on Windows |
| A3 | Upstream maintainer (HKUDS) is reachable via GitHub PR | §Pattern 5 | If maintainer is unresponsive, success criterion 4 ("≥1 maintainer ack") is blocked regardless of RFC quality — escalation path is "ship RFC in our fork's `docs/rfcs/` and document the attempt" |
| A4 | The `_env()` modernization is OUT of scope — scrubbing is a wrapper, not a refactor | §User Constraints (Deferred) | If scrubbing requires rewriting `_env()`, CONCERNS.md:128-131 tech debt lands earlier than ROADMAP expects |
| A5 | The existing `test_templates.py` coverage of template structure is sufficient — Phase 0 regression matrix tests the `launch` integration flow, not re-testing template parsing | §Pitfall 6 | If the regression matrix is expected to deep-assert every agent prompt, it bloats to ~400 LOC instead of ~80 LOC |
| A6 | The 11-pattern secret-name regex list matches actual secrets in the ClawTeam env surface. Real-world names we target: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GITHUB_TOKEN`, `DB_PASSWORD`, `AWS_ACCESS_KEY_ID`, `GOOGLE_APPLICATION_CREDENTIALS` — all covered | §Pattern 2 | If real-world env has secrets NOT matching these patterns (e.g., a provider uses `_AUTH_STR`), they pass through. Mitigation: the test matrix should include at least the 9 provider keys from `presets.py` [VERIFIED: clawteam/spawn/presets.py:72] + the research paper's canonical MINJA-class names |
| A7 | `doctor --fix` is not needed based on PROJECT.md out-of-scope list | §Pattern 3 | If plan reviewer asks for `--fix`, we push back with the PROJECT.md citation |
| A8 | 5 tools to probe is the right list: chromium, codex, ngrok, watchdog, gource. Derived from REQUIREMENTS.md UX-08 + ROADMAP.md success criterion 3 explicit list | §Pattern 3 | If Phase 6/7 adds a new optional dep (e.g., sqlite-vec), `doctor` needs to grow — the TOOL_CHECKS list is a flat config, so extending is 1-item trivial |
| A9 | RFC target channel is a PR against upstream `HKUDS/ClawTeam` (not a GitHub Discussion or Issue). No CONTRIBUTING.md defines the "right" channel [VERIFIED: no such file] | §Pattern 5 | If maintainer prefers Discussions, we open there; cost is just a copy-paste migration. Keep RFC content in our fork regardless |
| A10 | The scrub helper's allowlist of non-secret envs (ANTHROPIC_BASE_URL, OPENAI_BASE_URL, etc.) is correct. BASE_URL strings are not themselves secrets; they're endpoints | §Pattern 2 | If a provider embeds a credential in a BASE_URL (rare; e.g., `https://user:pass@api...`), that URL WOULD leak. Mitigation: add a secondary pattern `re.compile(r".*://.+:.+@.+")` to value-scrub those specifically — LOW priority since no preset in `presets.py` uses this form [VERIFIED] |
| A11 | `model_profile` as a string enum with 3 known values (`balanced`, `quality`, `budget`) per REQUIREMENTS.md TEAM-05. Phase 0 doesn't enforce the 3-value restriction at pydantic level; it just supplies the default | §Pattern 4 | If we enforce `Literal["balanced","quality","budget"]`, user-set "experimental" fails validation — leave it `str` and document the 3-value convention in docstring |

**User confirmation recommended before planning:**
- A1 (scope of Phase 0's model profile work — Phase 0 does only the resolution path, NOT the model mapping)
- A2 (Windows CI — research recommends deferring; confirm)

## Open Questions

1. **Should the regression matrix assert on the STATE after spawn (team + tasks + members) or also on the prompt content?**
   - What we know: `tests/test_templates.py:80-95` already covers prompt structure per-template; spawn-integration in `tests/test_spawn_cli.py:309-341` asserts on `backend.calls` metadata only.
   - What's unclear: Whether reviewers want the regression matrix to include prompt substring assertions (expensive, breaks when any template is touched intentionally) or to trust `test_templates.py`.
   - Recommendation: Regression matrix asserts STATE (team exists, agents added, tasks created, spawn calls recorded, prompts non-empty) only. Prompt CONTENT is covered by `test_templates.py`. Document this division in the matrix test file's docstring.

2. **Should `scrub_env()` be applied to the spawn backends' `os.environ.copy()` sites (defense-in-depth) or only at the one hooks.py write site?**
   - What we know: CONCERNS.md:83-87 calls out `hooks.py:80-88` as THE documented leak point. The three spawn-backend `os.environ.copy()` sites exist (subprocess_backend.py:38, tmux_backend.py:65, wsh_backend.py:243) but they intentionally forward secrets to child processes that need them.
   - What's unclear: Whether defense-in-depth belongs in Phase 0 or waits until Phase 6 memory ingestion.
   - Recommendation: Phase 0 adds `scrub_env()` to `hooks.py:81` as the mandatory fix AND exposes it as a reusable `clawteam/util/secrets.py` helper. Phase 6 reuses same helper. DO NOT apply to spawn backends — child processes need real secrets. Add a regression test that spawn backends still propagate known keys.

3. **Does Phase 0 need a `docs/rfcs/README.md` "what is an RFC" meta-doc or is a single RFC file enough?**
   - What we know: `docs/rfcs/` doesn't exist today. We'd be establishing the convention.
   - What's unclear: Whether upstream maintainers want an explicit RFC process document.
   - Recommendation: Ship a minimal `README.md` (~30 lines) explaining "RFCs in this fork target upstream; follow the template in 001-phase-registry.md". Low cost, high clarity for future RFC authors (Phase 1+ may draft follow-up RFCs).

4. **Should the regression matrix test BOTH `backend="tmux"` and `backend="subprocess"` per template?**
   - What we know: Each template's TOML has a `backend` field; `software-dev.toml:4` has `backend = "tmux"`, etc. The `launch` command accepts `--backend` override.
   - What's unclear: Whether BC includes "this template works under both backends."
   - Recommendation: Test with the template's declared backend only; use `--backend` override as a SECOND parametrize axis (i.e., 6 templates × 2 backends = 12 cases) only if reviewers push for it. With `RecordingBackend` replacing both, there's no real cost, but output gets noisy. Start with 6 cases; expand to 12 if a backend-specific regression is ever found.

5. **Which Python version is the "canonical" RFC review target for the worked example?**
   - What we know: CI matrix covers 3.10, 3.11, 3.12 [VERIFIED: ci.yml:25]. Dev host ran 3.14.4 [VERIFIED].
   - What's unclear: Whether the RFC's worked example code should use 3.10-compatible syntax (it should per pyproject floor).
   - Recommendation: Trivially — all `from __future__ import annotations` means PEP-604 unions and stdlib generics work on 3.10. Standard. No additional constraint.

6. **How does the env scrub interact with the current adapter pattern's whitelist of `*_API_KEY` / `*_BASE_URL` for child processes?**
   - What we know: `clawteam/spawn/adapters.py` already filters env for the docker `nanobot` path (`ensure_docker_env`); the adapter whitelists `*_API_KEY`, `*_BASE_URL`, etc. for child env passing. [VERIFIED: codebase/ARCHITECTURE.md:223-225]
   - What's unclear: Whether that adapter whitelist needs updating when we add scrubbing to `hooks.py`.
   - Recommendation: NO — the adapter whitelist is for "what to PASS to child", which is orthogonal to "what to REDACT from logs". The scrub helper lives in `util/secrets.py` and is NOT called from spawn backends. The two code paths stay independent. Document this in the docstring.

## Sources

### Primary (HIGH confidence)

**Codebase — verified firsthand via `Read`, `Grep`, `Bash`:**
- `pyproject.toml` (lines 1-72) — deps, ruff, pytest config, classifiers
- `.github/workflows/ci.yml` (lines 1-32) — existing CI matrix (3 py × 2 OS)
- `clawteam/identity.py` (all 103 lines) — `_env()` three-namespace logic, NOT modifying
- `clawteam/events/hooks.py` (all 116 lines) — THE secret-leak site at `_make_shell_handler:80-88`
- `clawteam/templates/__init__.py` (all 158 lines) — template loader structure
- `clawteam/templates/harness-default.toml`, `software-dev.toml`, `hedge-fund.toml` — template shapes
- `clawteam/config.py` (all 143 lines) — `ClawTeamConfig` extension point
- `clawteam/spawn/profiles.py` (all 183 lines) — `resolve_profile_name` pattern to mirror
- `clawteam/spawn/subprocess_backend.py` (all 152 lines) — `os.environ.copy()` site at line 38
- `clawteam/harness/phases.py` (all 193 lines) — `PhaseState`, `Phase = str` (NOT modifying)
- `clawteam/plugins/base.py` (all 42 lines) — `HarnessPlugin` shape (Phase 1 will extend)
- `clawteam/cli/commands.py` (lines 1-250, 1146-1220, 3864-4120) — Typer pattern, `launch` command, `team` sub-app
- `tests/conftest.py` (all 25 lines) — `isolated_data_dir` autouse
- `tests/test_spawn_cli.py` (lines 1-340) — `RecordingBackend` proven pattern
- `tests/test_cli_commands.py` (lines 1-150) — Typer CliRunner pattern
- `tests/test_identity.py` (all 140 lines) — env fixture pattern
- `tests/test_templates.py` (all 198 lines) — template-parse coverage already exists
- `tests/test_harness.py` (lines 1-100) — phase-state testing pattern
- `.agents/skills/clawteam-dev/SKILL.md` — validation order, prereqs, smoke tests
- `.planning/PROJECT.md` — constraints, out-of-scope, key decisions
- `.planning/REQUIREMENTS.md` — CORE-03, TEAM-06, QUALITY-14/15, UX-08 traceability
- `.planning/ROADMAP.md` (lines 1-200) — Phase 0 goal + success criteria
- `.planning/research/SUMMARY.md` — research rationale; Gaps to Address #1, #4, #6
- `.planning/research/STACK.md` — zero-new-required-deps envelope, recommended patterns
- `.planning/research/PITFALLS.md` (lines 174-613) — Pitfalls 12/14/17 ship-blockers + mapping
- `.planning/codebase/ARCHITECTURE.md` — layer model, data flows
- `.planning/codebase/CONCERNS.md` — hooks.py:80-88 leak, `_env()` fragility, 124 broad-except sites
- `.planning/codebase/STRUCTURE.md` — where-to-add-new-code rules
- `.planning/codebase/STACK.md` — existing deps baseline
- `.planning/codebase/TESTING.md` — pytest conventions, `CliRunner`, `monkeypatch`, mocking rules
- `.planning/codebase/CONVENTIONS.md` — naming, ruff, typing, error handling
- `.planning/codebase/INTEGRATIONS.md` — spawn runtimes, tmux/git requirements
- `.planning/config.json` — GSD config: nyquist_validation true, parallelization true, commit_docs true

**Current-machine probe (Bash):**
- `playwright: not installed`, `/usr/bin/codex`, `/usr/local/bin/ngrok`, `watchdog: not installed`, `gource: not installed`, `Python 3.14.4`, `/usr/bin/tmux`, `/usr/bin/git` — exact environment context for doctor testing

### Secondary (MEDIUM confidence, cross-verified)

- [rust-lang/rfcs 0000-template.md](https://github.com/rust-lang/rfcs/blob/master/text/0000-template.md) — RFC document structure
- [rust-lang/rfcs 0002-rfc-process.md](https://rust-lang.github.io/rfcs/0002-rfc-process.html) — RFC lifecycle, cross-referenced with Python PEP process
- [mazen160/secrets-patterns-db](https://github.com/mazen160/secrets-patterns-db) — secret-name regex confidence bands (metadata read only; actual regex set is in repo's `rules-stable.yml` file)
- [martinfowler.com/bliki/ArchitectureDecisionRecord](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html) — ADR best practices (rejected in favor of Rust-style RFC shape)
- [adr.github.io/madr](https://adr.github.io/madr/) — MADR ADR template (considered, rejected as too fine-grained for our scope)
- [GitGuardian: Detecting Secrets in Source Code](https://blog.gitguardian.com/secrets-in-source-code-episode-3-3-building-reliable-secrets-detection/) — name-shape vs value-shape detection trade-offs
- [PyPI pytest](https://pypi.org/project/pytest/) — confirms 9.0 series current; dev requirement aligned

### Tertiary (LOW confidence, flagged)

- WebSearch result on "flutter doctor / brew doctor Python implementation patterns" — no single Python library implements this; our 5-tool `doctor.py` is ~100 LOC handcoded, consistent with Flutter's approach per [flutter/flutter issue #18658](https://github.com/flutter/flutter/issues/18658). Confidence: MEDIUM on pattern (hand-rolled is standard); LOW on "the exact install command strings" — those are in our TOOL_CHECKS table and will need per-OS manual verification if the `doctor` test is strict.
- `ngrok` Linux install commands — retrieved from various 2026 install guides (Ubuntu/Fedora/Arch); best to cross-check each against official ngrok docs before the doctor plan lands. Confidence: LOW (2026 install commands change).
- `codex` install command — OpenAI's Codex CLI has both `npm` and package-manager paths; we list both in hints. Confidence: LOW (CLI is evolving).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Phase 0 adds no deps; everything listed is already in pyproject.toml [VERIFIED]
- Architecture patterns: HIGH — Parametrized test, deny-pattern scrub, Typer sub-app, config extension, markdown RFC — each has direct in-codebase precedent or a stable external pattern
- Pitfalls: HIGH — Pitfalls 1-6 derived from CONCERNS.md + research/PITFALLS.md + cross-referenced with ROADMAP success criteria
- Environment availability: HIGH — probed on research host; clearly documented what's present/absent
- Validation architecture: HIGH — builds on existing pytest + CliRunner + isolated_data_dir conventions; new test files auto-discovered by `testpaths = ["tests"]`
- Security domain: HIGH — QUALITY-15 is itself the security control; ASVS V5/V7/V8 mapping is direct
- Assumptions flagged: HIGH awareness — 11 assumptions logged with risk-if-wrong for each

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (30 days; stack is stable, Phase 0 deliverables should not drift during that window)

**Research order preference (bonus insight for planner):**
Following the question "which deliverable has the lightest blast radius and should ship first?" —
1. **First:** Env deny-filter (isolated `util/secrets.py` + 1 line in `hooks.py` + 1 test file). ~150 LOC total, self-contained, unblocks the Pitfall #17 ship-blocker concern.
2. **Second (parallel):** `clawteam doctor` (new `doctor.py` + 1 CLI command + 1 test file). ~250 LOC, no couplings.
3. **Third (parallel):** Default model profile scaffolding (3 small field additions + 1 resolver + test extensions). ~50 LOC, very low risk.
4. **Fourth:** Regression matrix (1 new test file, 1 CI discovery confirmation). ~80 LOC, trivially low risk but MUST land before Phase 1 code changes begin.
5. **Fifth (longest lead-time, parallel from day 1):** Upstream RFC — starts simultaneously with #1, takes calendar time for maintainer review, not LOC time for us.

Critical path: the RFC calendar-time wait (maintainer ack) is likely the longest single blocker. Everything else is 1-3 days of dev work. Plan fanout: 5 plans, parallel-executable, with RFC kicked off first.
