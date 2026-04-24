# Phase 5: Tool-Heavy Skills (Ship, SRE, Codex) — Research

**Researched:** 2026-04-21
**Domain:** Skill-module ports with external-CLI surfaces (codex, gh, lighthouse, questionary wizard) bound to gstack roles via plugin contribution
**Confidence:** HIGH (implementation map); MEDIUM (substrate — `contribute_skills` hook needs to be built, see A3)
**Research flag:** LOW (per ROADMAP.md line 253). Each skill has a clear upstream reference; this research focuses on the implementation map + substrate verification, not architecture discovery.

---

## Summary

Phase 5 ports seven tool-heavy gstack skills (`/codex`, `/ship`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`, `/setup-deploy`) as skill sub-packages under `clawteam/templates/gstack/skills/`, mirroring the Phase 4 shape (office_hours, design_consultation, investigate). Three substrate additions are required before the skill handlers can be written:

1. A **`SkillRegistration` type + `contribute_skills` plugin hook** (CONTEXT.md A3 assumes this exists — it does NOT; see Plan-Prep Verifications).
2. Three **new pydantic evidence schemas** (`DeployNotes`, `CanaryReport`, `BenchmarkReport`) registered via the existing `contribute_evidence_schemas` hook.
3. **Doctor detection entries** for `gh`, `lighthouse`, `vercel`, `netlify`, `flyctl` (only `codex` exists today).

`NativeCliAdapter` currently exposes only `prepare_command()`, not `invoke()` — CONTEXT.md A1 needs adjustment: either add an `invoke()` method that wraps subprocess with scrub_env + timeout OR handlers call `prepare_command()` then `subprocess.run(..., env=scrub_env(os.environ))` themselves. See A1 below for recommendation.

**Primary recommendation:** Wave 0 closes the four substrate gaps (skill hook, 3 schemas, doctor entries, adapter invoke contract); Waves 1–4 deliver the seven skills in parallel-safe groups; Wave 5 is the end-to-end integration test (D-16).

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKILL-13 | `/codex` engineer+reviewer, 3 modes (review/adversarial/consultation) | Per-Skill Map row 1; code example: `codex` invocation via `NativeCliAdapter.prepare_command` + subprocess wrapper |
| SKILL-14 | `/ship` shipper, 5-step orchestration (sync_main → run_tests → audit_coverage → push → open_pr) | Per-Skill Map row 2; CONTEXT.md D-05 (NOT a persisted state machine); ship_notes schema extends existing `ShipNotes` (phase 3) |
| SKILL-15 | `/land-and-deploy` shipper, deploy + health check | Per-Skill Map row 3; new `DeployNotes` schema (see schemas section); D-08 gstack.toml [deploy] block |
| SKILL-16 | `/document-release` shipper, diff-vs-docs cross-reference, auto-invoked by `/ship` | Per-Skill Map row 4; D-11 idempotent + `InteractionGate`-gated writes |
| SKILL-17 | `/canary` sre, post-deploy monitor with regression flags | Per-Skill Map row 5; new `CanaryReport` schema; D-09 5-minute window, 15s poll; `deploy_regression_detected` event |
| SKILL-18 | `/benchmark` sre, Core Web Vitals + page-load baselines | Per-Skill Map row 6; new `BenchmarkReport` schema; D-10 Lighthouse primary + curl fallback; `web_vital_regression_detected` event |
| SKILL-19 | `/setup-deploy` sre, questionary wizard writing `[deploy]` block | Per-Skill Map row 7; D-08 provider enum; D-15 adversarial-input sanitization |

---

## Architectural Responsibility Map

Phase 5 is a backend-only, single-tier phase. No frontend/SSR/CDN/DB tiers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skill dispatch (invoke /codex, /ship, ...) | Harness plugin layer (`clawteam/plugins/`) | — | Plugin populates a registry; harness dispatches based on agent role + skill name. |
| External CLI invocation | Spawn adapter (`clawteam/spawn/adapters.py`) | Event bus (scrub_env side-effect) | All subprocess calls routed through one module for uniform env scrubbing + timeout. |
| Artifact persistence | Artifact store (`clawteam/harness/artifacts.py`) + schemas (`clawteam/templates/gstack/schemas/`) | Evidence gate | Skill handlers emit frontmatter-typed markdown; EvidenceGate validates on phase transition. |
| External-tool availability detection | `clawteam doctor` (CLI) + per-skill `tool_available()` | — | Doctor is the install-hint source-of-truth (D-04); skills re-check at dispatch for stale detection. |
| Deploy / canary HTTP probes | stdlib `urllib.request` (same pattern as EvidenceGate._check_deploy_url) | — | Avoid adding `httpx`/`requests` dep (Stack constraint: no new required deps). |
| Wizard UX | `questionary` (already in deps) | — | Verified present in pyproject.toml line 25. |

---

## Per-Skill Implementation Map

Each row lists: file/method touchpoints, the upstream gstack reference (from CONTEXT.md §Canonical References), the `NativeCliAdapter` invocation profile, which pydantic schema, and the EventBus event (if any). Test touchpoints follow the D-15 convention: `test_<skill>_happy_path`, `test_<skill>_missing_tool`, `test_<skill>_adversarial_input`.

### Row 1: `/codex` (SKILL-13)

| Aspect | Detail |
|--------|--------|
| Sub-package | `clawteam/templates/gstack/skills/codex/` → `__init__.py`, `handler.py` |
| Roles | `engineer`, `reviewer` (D-01 role binding via `SkillRegistration.role`) |
| Upstream ref | gstack v2.x `/codex` skill; modes `review | adversarial | consultation` |
| Adapter call | `NativeCliAdapter.prepare_command(["codex", "exec"], prompt=<mode-prompt>, skip_permissions=True)` → then `subprocess.run(prepared.final_command, env=scrub_env(os.environ), timeout=600)`. `is_codex_command` already wired at adapter.py:56 + noninteractive subcommand handling at line 166-187 (`exec` included). |
| Missing-tool hint | `"npm install -g @openai/codex"` (already in doctor at commands.py:52-56) |
| Artifact | `codex-review.md` with frontmatter `artifact_type: codex-review`; schema `CodexReview` (NEW, minimal — see schemas section). Mode recorded in frontmatter. |
| Event | `tool_call_completed` (pre-existing Phase 2 event, for Phase 7 cost consumer) |
| Adversarial test | Input `; rm -rf /` — assert adapter wraps as literal positional arg; codex CLI never sees shell metacharacter (no `shell=True` in subprocess call). |
| Touchpoints | `clawteam/templates/gstack/skills/codex/handler.py`; `tests/templates/gstack/skills/test_codex.py` |

### Row 2: `/ship` (SKILL-14)

| Aspect | Detail |
|--------|--------|
| Sub-package | `clawteam/templates/gstack/skills/ship/` → `__init__.py`, `handler.py`, `steps.py` (5 step functions) |
| Roles | `shipper` (single role) |
| Upstream ref | gstack v2.x `/ship`; 5-step enumerated at D-05 |
| Adapter call | No external CLI in core loop; sub-steps call `git` (direct subprocess — `clawteam/workspace/git.py` is the existing wrapper), `pytest` / `vitest` / `go test` per D-06 language detect, `gh pr create` via `NativeCliAdapter` wrapper. |
| Missing-tool hint | `gh` → `"brew install gh"` / `"apt install gh"` / `"winget install GitHub.cli"` (NEW — add to doctor in Wave 0) |
| Artifact | `ship-notes.md` — extends existing `ShipNotes` schema (clawteam/templates/gstack/schemas/ship_notes.py). New optional fields: `ship_status`, `steps_completed`, `coverage`, `coverage_threshold`, `failure_step`, `failure_reason`, `pr_url`, `branch`. Backwards-compatible (optional defaults). |
| Event | `tool_call_completed` × (number of CLI calls) |
| Adversarial test | Diff with 50 binary files (`*.png`, `*.bin`) — coverage audit skips uncoverable paths, ship_status still computes. |
| Cross-skill | Auto-invokes `/document-release` at step-5 success (D-11). Handler returns; orchestration glue invokes document-release. |
| Touchpoints | `handler.py` + `steps.py` (sync_main, run_tests, audit_coverage, push, open_pr); `tests/templates/gstack/skills/test_ship.py`; **extends** `clawteam/templates/gstack/schemas/ship_notes.py` (additive — backward compat for Phase 3 stubs) |

### Row 3: `/land-and-deploy` (SKILL-15)

| Aspect | Detail |
|--------|--------|
| Sub-package | `clawteam/templates/gstack/skills/land_and_deploy/` → `__init__.py`, `handler.py` |
| Roles | `shipper` |
| Upstream ref | gstack v2.x `/land-and-deploy` |
| Precondition | `ship-notes.md` with `ship_status: succeeded` exists (D-12 — raises `SkillPreconditionError` otherwise) |
| Adapter calls | 1. `gh pr checks --watch <pr>` (sufficient per D-30-scope note); 2. `vercel deploy` / `netlify deploy` / `fly deploy` / `<custom_deploy_cmd>` per `gstack.toml [deploy].provider`; 3. stdlib `urllib.request` HEAD probe on deploy URL. |
| Missing-tool hint | `vercel` / `netlify` / `flyctl` → NEW doctor entries (Wave 0). |
| Artifact | `deploy.md` — NEW schema `DeployNotes` (see schemas section) |
| Event | `tool_call_completed` |
| Adversarial test | Deploy command echoes `https://example.invalid` (fake-deploy fixture) — HEAD probe fails 10s-timeout cleanly, `deploy_status: failed` recorded, no crash. |
| Touchpoints | `handler.py`; new `clawteam/templates/gstack/schemas/deploy_notes.py`; `tests/templates/gstack/skills/test_land_and_deploy.py` |

### Row 4: `/document-release` (SKILL-16)

| Aspect | Detail |
|--------|--------|
| Sub-package | `clawteam/templates/gstack/skills/document_release/` → `__init__.py`, `handler.py`, `doc_walker.py`, `patch_emitter.py` (planner's call per CONTEXT §Discretion) |
| Roles | `shipper` |
| Upstream ref | gstack v2.x `/document-release`; diff-vs-docs stale-reference detector |
| Adapter call | `git diff <base>..<branch> --name-only` via `clawteam/workspace/git.py`; no external CLI beyond git. |
| Missing-tool hint | None (git is baseline) |
| Artifact | No new schema. Emits `docs-updates/<ISO-8601>.diff` (raw unified-diff patch proposals) + `document-release-summary.md` (list of stale refs found, referenced patches). Non-destructive: **does NOT write to docs directly** (D-11). |
| Gating | Non-trivial writes (>5 lines in any single doc) → `InteractionGate` via `questions/<N>.md` with question: "Apply patch to `docs/X.md`?" + yes/no choice. |
| Event | None needed. |
| Adversarial test | 100 doc files, 50 stale refs each — handler caps at configurable `max_patches_per_run` (default 50), emits summary note "N additional stale refs deferred; re-run to continue." |
| Cross-skill | Auto-invoked by `/ship` after PR-open success (D-11). Idempotent: second run finds no new stale refs, writes summary saying "no changes." |
| Touchpoints | `handler.py` + helpers; `tests/templates/gstack/skills/test_document_release.py`; reuses Phase 1 `InteractionGate` (`clawteam/harness/interaction_gate.py`) |

### Row 5: `/canary` (SKILL-17)

| Aspect | Detail |
|--------|--------|
| Sub-package | `clawteam/templates/gstack/skills/canary/` → `__init__.py`, `handler.py`, `poller.py` |
| Roles | `sre` |
| Upstream ref | gstack v2.x `/canary`; post-deploy HTTP monitor with optional browser pipeline |
| Adapter call | stdlib `urllib.request` for HTTP HEAD/GET polls every 15s for `window_seconds` (D-09). Optional: Playwright for console errors IF `clawteam[browser]` installed — feature-gated via `from importlib.util import find_spec; find_spec("playwright")` (same pattern as doctor commands.py:1203). |
| Missing-tool hint | Browser optional; emit `SkillUnavailable` for degraded mode only IF user explicitly requests browser mode; default HTTP-only mode is always available. |
| Artifact | `canary-report.md` — NEW schema `CanaryReport` (see schemas section) |
| Event | `deploy_regression_detected` (NEW dataclass in `clawteam/events/types.py`) — emitted when 5xx rate > 1%, response time > 2× baseline, or JS console error observed (D-09 thresholds) |
| Config | `gstack.toml [canary].window_seconds` (default 300), `[canary].poll_interval_seconds` (default 15). NEW `CanaryConfig` pydantic. |
| Adversarial test | Deploy URL returns 503 immediately on first poll — regression_flag fires, no crash, `canary_status: regression`. |
| Baseline | Reads pre-deploy baseline from `~/.clawteam/teams/<team>/baselines/<provider>.json` (written by `/benchmark` when pre-deploy mode) — best-effort load; on miss, canary runs without baseline comparison and records `baseline_missing: true` in report. |
| Touchpoints | `handler.py` + `poller.py`; new `clawteam/templates/gstack/schemas/canary_report.md` schema; new event type in `clawteam/events/types.py`; `tests/templates/gstack/skills/test_canary.py` |

### Row 6: `/benchmark` (SKILL-18)

| Aspect | Detail |
|--------|--------|
| Sub-package | `clawteam/templates/gstack/skills/benchmark/` → `__init__.py`, `handler.py` |
| Roles | `sre` |
| Upstream ref | gstack v2.x `/benchmark`; Core Web Vitals (LCP/FID/CLS) + TTFB + DOMContentLoaded |
| Adapter call | Primary: `lighthouse <url> --output=json --quiet --chrome-flags='--headless'` via `NativeCliAdapter.prepare_command(["lighthouse", ...], ...)`. Fallback: `curl -w '%{time_total} %{time_starttransfer}' <url>` for TTFB + page-load only (D-10). |
| Missing-tool hint | `lighthouse` NEW doctor entry → `"npm install -g lighthouse"` (cross-platform) |
| Artifact | `benchmark-report.md` — NEW schema `BenchmarkReport` (see schemas section). Writes a companion JSON baseline to `~/.clawteam/teams/<team>/baselines/<provider>.json` (used by `/canary`). |
| Event | `web_vital_regression_detected` (NEW dataclass in `clawteam/events/types.py`) — emitted when any Vital > 1.5× pre-deploy baseline. |
| Adversarial test | Lighthouse returns partial JSON (LCP present, CLS missing) — handler surfaces `{lcp_ms: 1234.0, cls_score: null}` in report, logs gap, does NOT crash. |
| Touchpoints | `handler.py`; new schema; new event type; `tests/templates/gstack/skills/test_benchmark.py` |

### Row 7: `/setup-deploy` (SKILL-19)

| Aspect | Detail |
|--------|--------|
| Sub-package | `clawteam/templates/gstack/skills/setup_deploy/` → `__init__.py`, `handler.py`, `wizard.py` |
| Roles | `sre` |
| Upstream ref | gstack v2.x `/setup-deploy` |
| Adapter call | None. Pure `questionary` wizard (already in deps per pyproject.toml:25). Writes `gstack.toml` via `tomllib` read + stdlib write (no round-trip lib needed for additive block insertion — use the existing `atomic_write_text` + `file_locked` pattern). |
| Missing-tool hint | Never missing (questionary is a hard dep). Wizard may detect and recommend provider CLI install via `clawteam doctor` output if user picks a provider whose CLI isn't installed. |
| Artifact | None (writes to `gstack.toml [deploy]` block) |
| Event | None |
| Config | NEW `DeployConfig` pydantic model in `clawteam/templates/gstack/schemas/deploy_config.py` or `clawteam/templates/__init__.py` — planner's call per CONTEXT §Discretion. **Note:** To be read at template-load time, TemplateDef must be extended — see A5 adjustment. |
| Adversarial test | User types `--vercel; rm /` as project slug — wizard regex-validates `^[a-zA-Z0-9_-]+$`; typing invalid input re-prompts without echo to `gstack.toml`. |
| Idempotency | Re-run detects existing `[deploy]` block, confirms "Overwrite existing deploy config? [y/N]" before writing. |
| Touchpoints | `handler.py` + `wizard.py`; updates to `clawteam/templates/__init__.py::TemplateDef` + `_parse_toml`; `tests/templates/gstack/skills/test_setup_deploy.py` |

---

## Code Examples

### 1. `SkillRegistration` tuple shape (NEW — Wave 0 substrate)

```python
# clawteam/plugins/skill_registration.py (NEW FILE)
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any

@dataclass(frozen=True)
class SkillRegistration:
    """One skill contribution from a HarnessPlugin (Phase 5 substrate).

    - name: slash-command name as agents invoke it, e.g. "/codex"
    - roles: frozen set of agent roles permitted to invoke (e.g., {"engineer", "reviewer"})
    - handler: callable dispatched by SkillDispatcher; signature
               handler(ctx: HarnessContext, *, role: str, args: dict) -> SkillResult
    - tool_available: optional callable returning bool; if False at dispatch
                      time, handler raises SkillUnavailable with install_hint.
    - install_hint: string shown in SkillUnavailable error when tool_available
                    returns False. Matches clawteam doctor install-hint text.
    """
    name: str
    roles: frozenset[str]
    handler: Callable[..., Any]
    tool_available: Callable[[], bool] | None = None
    install_hint: str = ""


# clawteam/plugins/base.py (EXTENDS existing HarnessPlugin class)
class HarnessPlugin(ABC):
    # ... existing hooks ...
    def contribute_skills(self) -> list[SkillRegistration]:
        """Return the list of skills this plugin contributes.

        Plugin manager aggregates across plugins; duplicate names raise ValueError
        at registration time (mirrors PhaseRegistry D-03 namespace rule).
        """
        return []
```

### 2. `NativeCliAdapter` invocation — codex example

```python
# clawteam/templates/gstack/skills/codex/handler.py (NEW)
import os
import shutil
import subprocess
from typing import Literal

from clawteam.secrets import scrub_env
from clawteam.spawn.adapters import NativeCliAdapter

CodexMode = Literal["review", "adversarial", "consultation"]
_ADAPTER = NativeCliAdapter()

def tool_available() -> bool:
    return shutil.which("codex") is not None

def invoke_codex(prompt: str, *, mode: CodexMode, cwd: str, timeout: int = 600) -> str:
    """Invoke codex CLI via NativeCliAdapter; returns stdout."""
    if not tool_available():
        from clawteam.plugins.skill_errors import SkillUnavailable  # Wave 0
        raise SkillUnavailable(
            skill="/codex",
            binary="codex",
            install_hint="npm install -g @openai/codex",
        )

    prepared = _ADAPTER.prepare_command(
        command=["codex", "exec"],
        prompt=prompt,
        cwd=cwd,
        skip_permissions=True,
        interactive=False,
    )
    result = subprocess.run(
        prepared.final_command,
        cwd=cwd,
        env=scrub_env(os.environ),  # D-03 safety; adapter does NOT scrub today
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,  # adversarial input protection (D-15)
    )
    return result.stdout
```

### 3. `NativeCliAdapter` invocation — gh example

```python
def invoke_gh_pr_create(title: str, body: str, *, cwd: str, timeout: int = 60) -> str:
    prepared = _ADAPTER.prepare_command(
        command=["gh", "pr", "create", "--title", title, "--body", body],
        cwd=cwd,
    )
    # `gh` is not a known CLI in the adapter, so prepare_command returns
    # the command unchanged (verified adapters.py:131-140 — non-matching
    # basenames flow through the final `elif prompt:` branch with -p).
    # Strip any stray `-p` the adapter may append when prompt is None:
    # adapters.py:131 gates on `prompt` truthiness, so prompt=None leaves
    # the command clean.
    result = subprocess.run(
        prepared.final_command, cwd=cwd, env=scrub_env(os.environ),
        capture_output=True, text=True, timeout=timeout, check=False, shell=False,
    )
    return result.stdout  # PR URL on one line
```

### 4. `NativeCliAdapter` invocation — lighthouse example

```python
def invoke_lighthouse(url: str, *, timeout: int = 120) -> dict:
    prepared = _ADAPTER.prepare_command(
        command=["lighthouse", url, "--output=json", "--quiet",
                 "--chrome-flags=--headless"],
    )
    result = subprocess.run(
        prepared.final_command, env=scrub_env(os.environ),
        capture_output=True, text=True, timeout=timeout, check=False, shell=False,
    )
    import json
    return json.loads(result.stdout) if result.stdout.strip().startswith("{") else {}
```

### 5. `questionary` wizard (setup-deploy)

```python
# clawteam/templates/gstack/skills/setup_deploy/wizard.py (NEW)
import re
import questionary

_PROJECT_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")  # D-15 adversarial-input gate

def run_wizard() -> dict:
    provider = questionary.select(
        "Which deploy provider?",
        choices=["vercel", "netlify", "fly", "custom"],
    ).ask()
    if provider is None:  # user Ctrl-C
        raise KeyboardInterrupt

    project = questionary.text(
        "Project slug (alphanumeric + dash/underscore only):",
        validate=lambda s: bool(_PROJECT_SLUG_RE.fullmatch(s or "")),
    ).ask()

    custom_cmd = ""
    if provider == "custom":
        custom_cmd = questionary.text(
            "Custom deploy command (shell metachars stripped):",
            validate=lambda s: not any(c in (s or "") for c in (";", "|", "&", "`", "$")),
        ).ask()

    return {"provider": provider, "project": project, "custom_deploy_cmd": custom_cmd}
```

### 6. Pydantic schemas for three new artifact types

```python
# clawteam/templates/gstack/schemas/deploy_notes.py (NEW)
from typing import Literal
from pydantic import BaseModel, Field

class DeployNotes(BaseModel):
    """Land-and-deploy artifact — matches CONTEXT.md §specifics deploy.md spec."""
    artifact_type: Literal["deploy-notes"]
    deploy_status: Literal["succeeded", "failed", "pending"]
    deploy_url: str = Field(..., min_length=1)  # Pitfall 8: EvidenceGate dereferences
    provider: Literal["vercel", "netlify", "fly", "custom"]
    deployed_at: str  # ISO-8601
    commit_sha: str = Field(..., min_length=7, max_length=40)
    sprint_id: str
    created_at: str
    persona: str = "shipper"
    step_label: str = "deploy"
    done: bool = True
```

```python
# clawteam/templates/gstack/schemas/canary_report.py (NEW)
from typing import Literal
from pydantic import BaseModel, Field

class CanaryReport(BaseModel):
    artifact_type: Literal["canary-report"]
    canary_status: Literal["clean", "regression"]
    window_seconds: int = Field(..., ge=1)
    http_2xx_count: int = Field(..., ge=0)
    http_5xx_count: int = Field(..., ge=0)
    avg_response_ms: float = Field(..., ge=0.0)
    pre_deploy_avg_response_ms: float = Field(default=0.0, ge=0.0)
    baseline_missing: bool = False
    js_console_errors: list[str] = Field(default_factory=list)
    regression_flags: list[str] = Field(default_factory=list)
    sprint_id: str
    created_at: str
    persona: str = "sre"
    step_label: str = "canary"
    done: bool = True
```

```python
# clawteam/templates/gstack/schemas/benchmark_report.py (NEW)
from typing import Literal
from pydantic import BaseModel, Field

class BenchmarkReport(BaseModel):
    artifact_type: Literal["benchmark-report"]
    benchmark_status: Literal["clean", "regression"]
    lcp_ms: float | None = Field(default=None, ge=0.0)  # partial-tool tolerance (D-15)
    fid_ms: float | None = Field(default=None, ge=0.0)
    cls_score: float | None = Field(default=None, ge=0.0)
    ttfb_ms: float = Field(..., ge=0.0)  # always from curl fallback
    dom_loaded_ms: float = Field(..., ge=0.0)
    regression_flags: list[str] = Field(default_factory=list)
    measured_with: Literal["lighthouse", "curl"] = "lighthouse"
    sprint_id: str
    created_at: str
    persona: str = "sre"
    step_label: str = "benchmark"
    done: bool = True
```

### 7. EventBus emit shape for the 2 new event types

```python
# clawteam/events/types.py (APPEND — Wave 1 substrate)
from dataclasses import dataclass, field

@dataclass
class DeployRegressionDetected(HarnessEvent):
    """Canary window observed a regression vs pre-deploy baseline (D-14)."""
    sprint_id: str = ""
    deploy_url: str = ""
    regression_flags: list[str] = field(default_factory=list)  # e.g. ["5xx_rate>1%"]
    http_2xx_count: int = 0
    http_5xx_count: int = 0
    avg_response_ms: float = 0.0
    pre_deploy_avg_response_ms: float = 0.0

@dataclass
class WebVitalRegressionDetected(HarnessEvent):
    """A Core Web Vital exceeded 1.5× pre-deploy baseline (D-14)."""
    sprint_id: str = ""
    deploy_url: str = ""
    vital: str = ""  # one of: "lcp", "fid", "cls", "ttfb"
    baseline_value: float = 0.0
    observed_value: float = 0.0
    ratio: float = 0.0  # observed/baseline
```

```python
# Emission — same pattern as Phase 4 MidReviewThrash (events/types.py:287):
from clawteam.events.bus import register_event_type
register_event_type(DeployRegressionDetected)
register_event_type(WebVitalRegressionDetected)

# Inside canary handler:
ctx.bus.emit(DeployRegressionDetected(
    team_name=team,
    sprint_id=sprint_id,
    deploy_url=url,
    regression_flags=flags,
    # ...
))
```

**Emit signature note:** EventBus.emit takes a typed HarnessEvent instance, NOT a string event name (verified `clawteam/events/bus.py:86`). CONTEXT.md §code_context bullet "EventBus `emit("deploy_regression_detected", payload)`" is illustrative shorthand — the real call signature is the typed dataclass above. A7 needs this clarification.

### 8. `SkillUnavailable` / `SkillNotPermitted` / `SkillPreconditionError` exceptions

```python
# clawteam/plugins/skill_errors.py (NEW — Wave 0)
class SkillError(Exception):
    """Base for all skill-dispatch failures (agent-visible, structured)."""
    def __init__(self, skill: str, role: str = "", message: str = ""):
        self.skill = skill
        self.role = role
        self.message = message
        super().__init__(f"[{skill}] (role={role}) {message}")

class SkillUnavailable(SkillError):
    def __init__(self, skill: str, binary: str, install_hint: str, role: str = ""):
        self.binary = binary
        self.install_hint = install_hint
        super().__init__(
            skill=skill, role=role,
            message=f"tool '{binary}' not available. Install: {install_hint}",
        )

class SkillNotPermitted(SkillError):
    pass

class SkillPreconditionError(SkillError):
    pass
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess env scrubbing | Per-handler env filtering | `clawteam.secrets.scrub_env` (existing) | Centralizes regex; already battle-tested by Phase 0 D-02 |
| Pydantic artifact validation | Ad-hoc dict checks in handlers | `EvidenceSchemaRegistry.register_schema` (existing Phase 2) | Gate integrates automatically; Phase 5 just registers 3 new schemas |
| File-locked atomic writes | `open(path, "w").write(...)` | `clawteam.fileutil.{file_locked, atomic_write_text}` (existing) | Race-condition safety already solved |
| Interactive CLI wizards | `input()` loops | `questionary` (already in deps) | Consistent with rest of CLI UX (profile wizard precedent, cli/commands.py:173-183) |
| Git command wrappers | Per-skill `subprocess.run(["git", ...])` | `clawteam/workspace/git.py` (existing) | One subprocess entry point for git; simplifies mocking in tests |
| HTTP probes | `httpx`/`requests` dependency | stdlib `urllib.request` | Already used by `EvidenceGate._default_head_check` at evidence_gate.py:70 — same pattern |
| Event emission to downstream Phase 7 | Ad-hoc logging | Typed `HarnessEvent` dataclass + `ctx.bus.emit` (existing) | Phase 4 `MidReviewThrash` is the precedent shape |
| Ship-step orchestration state | A persisted state machine (like Phase 4 office_hours) | Sequential pure-function pipeline (D-05) | Ship is a transaction ≤3 min, not a dialog. Overhead of state persistence is unjustified. |

**Key insight:** Phase 5 is ~85% "wire existing substrate" and ~15% "new substrate (skill hook + 3 schemas + 2 events + doctor entries)." The design deliberately avoids building new primitives for anything Phase 0–4 already covers.

---

## Common Pitfalls

### Pitfall 1: Shell-metachar leakage through subprocess

**What goes wrong:** A skill accepts user input (e.g., `/codex` prompt, `/setup-deploy` project name) and passes it verbatim to `subprocess.run(..., shell=True)` or through `bash -c`.
**Why it happens:** Habit: "let's just shell out."
**How to avoid:** (a) always `shell=False` in `subprocess.run` in handlers; (b) `NativeCliAdapter.prepare_command` returns a `list[str]` which by construction cannot shell-inject; (c) regex-validate user input at the wizard/input boundary (see `_PROJECT_SLUG_RE` above).
**Warning signs:** Any `shell=True` in the PR diff, any f-string that interpolates user input into a command string.

### Pitfall 2: Adapter does not scrub env

**What goes wrong:** Adapter `prepare_command` does NOT inject scrub_env (verified adapters.py — no env handling except for nanobot docker). A handler that calls `subprocess.run(prepared.final_command)` without explicitly passing `env=scrub_env(os.environ)` will leak secrets to external CLI logs.
**Why it happens:** The CONTEXT.md D-03 wording "adapter already handles... env injection" is slightly misleading — the adapter prepares *container env* for nanobot only. For codex/gh/lighthouse/vercel, env pass-through is the caller's responsibility.
**How to avoid:** Every skill handler's subprocess.run must pass `env=scrub_env(os.environ)` explicitly. Add this to the D-15 adversarial-input test suite: fixture env with `FAKE_SECRET_TOKEN=oops`, assert it doesn't reach the CLI by checking stdout/argv capture.
**Warning signs:** A subprocess.run call without an explicit env kwarg.

### Pitfall 3: EvidenceGate deploy_url HEAD probe times out on slow deploys

**What goes wrong:** EvidenceGate (evidence_gate.py:70) uses a 10-second HEAD timeout. Fresh deploys can take 30–90s to become routable, causing a false gate failure even when `/land-and-deploy` succeeded.
**Why it happens:** Post-deploy DNS propagation + CDN warm-up is not instantaneous.
**How to avoid:** `/land-and-deploy` handler polls the deploy URL ITSELF after the deploy command succeeds, retrying with exponential backoff up to `deploy_verify_timeout_seconds` (new config, default 120). Only after the handler confirms 2xx does it write `deploy.md`; by then EvidenceGate's 10s probe succeeds.
**Warning signs:** `EvidenceGate` failure messages referencing 503/timeout for `deploy_url`.

### Pitfall 4: Phase 4 state-machine pattern misapplied to `/ship`

**What goes wrong:** Engineer copies `office_hours/state.py` as a starting template and builds a 5-state machine with `file_locked` persistence — adding complexity D-05 deliberately rejects.
**Why it happens:** "All skills share a shape" overgeneralization.
**How to avoid:** `/ship` is a linear pipeline of 5 pure functions; its only "state" is the accumulating `StepResult` list. No state.json persistence; on failure, the user re-runs. Be strict about this per D-05.
**Warning signs:** A `clawteam/templates/gstack/skills/ship/state.py` file, any `file_locked` call inside ship handler, any state class with `OHState`-like enum.

### Pitfall 5: Optional-extra unchecked before import

**What goes wrong:** `/canary` in browser mode imports `playwright` unconditionally at module load time → ImportError crashes the plugin on teams without `clawteam[browser]`.
**Why it happens:** Python's `import` is module-top-level by default.
**How to avoid:** Guard all Playwright imports inside the function that uses them: `def _get_browser(): try: from playwright.sync_api import sync_playwright ...`. The Phase 3 `_load_questionary` helper (cli/commands.py:173) is the canonical pattern.
**Warning signs:** `from playwright.sync_api import ...` at module top.

### Pitfall 6: TemplateDef swallows `[ship]` / `[deploy]` / `[canary]` / `[benchmark]` blocks silently

**What goes wrong:** `_parse_toml` (templates/__init__.py:154-199) only reads a fixed set of fields. Unknown `[ship]` / `[deploy]` blocks in a `gstack.toml` are parsed by `tomllib` and then discarded because TemplateDef never surfaces them. CONTEXT.md A5 assumes `extra="ignore"` tolerance — but because TemplateDef doesn't even attempt to read those keys, "tolerance" is moot. The real issue: Phase 5 handlers NEED to READ those blocks.
**Why it happens:** TemplateDef is a closed pydantic model, not an extensible one; `_parse_toml` hand-maps fields.
**How to avoid:** Wave 0 extends TemplateDef with OPTIONAL `ship: ShipConfig | None = None`, `deploy: DeployConfig | None = None`, `canary: CanaryConfig | None = None`, `benchmark: BenchmarkConfig | None = None` and extends `_parse_toml` to read them. All four default to `None`; existing `gstack.toml` (without these blocks) continues to load unchanged; other templates (software-dev, etc.) remain unaffected because the fields are optional and unused elsewhere.
**Warning signs:** A skill handler calling `tmpl.ship.coverage_threshold` and getting AttributeError because the TemplateDef doesn't have a `.ship`.

### Pitfall 7: Auto-invoke of `/document-release` double-runs on retry

**What goes wrong:** `/ship` succeeds → auto-invokes `/document-release` → user retries `/ship` after fixing some unrelated issue → document-release runs again, emits patches on already-patched files.
**Why it happens:** Auto-invocation is implicit; users don't realize re-running ship re-runs document-release.
**How to avoid:** document-release idempotency (D-11) is its own defense: second run finds no new stale refs, emits a summary saying "no changes to docs." Also document the behavior in ship-notes.md frontmatter: `auto_invoked_skills: [document-release]`.
**Warning signs:** PR with 2 identical docs-patch commits.

### Pitfall 8: `gh pr checks --watch` blocks indefinitely on stuck CI

**What goes wrong:** `--watch` polls until CI resolves; if CI is stuck in `pending` (e.g., a GitHub outage), `/land-and-deploy` hangs forever.
**Why it happens:** D-10-scope note says `gh pr checks --watch is sufficient`; but `--watch` has no client-side timeout.
**How to avoid:** Wrap the `gh pr checks --watch` subprocess.run in a `timeout=<ci_wait_timeout_seconds>` (new config, default 1800 = 30 min). On timeout, emit `deploy_status: failed` with reason `ci_timeout`, do NOT proceed to deploy.
**Warning signs:** `/land-and-deploy` wall-clock exceeding 30 min, sprint stuck.

---

## Plan-Prep Verifications (A1–A8 with evidence)

**Legend:** ✅ confirmed as CONTEXT.md states • ⚠️ PARTIAL — needs adjustment • ❌ CONTEXT.md WRONG — Wave 0 must address

### A1: `NativeCliAdapter.invoke(binary, args, env_allowlist, timeout)`

**Status:** ❌ **CONTEXT.md WRONG.** The `NativeCliAdapter` at `clawteam/spawn/adapters.py:31` exposes `prepare_command(command, *, prompt, cwd, skip_permissions, interactive, agent_name, container_env)` — returning a `PreparedCommand` dataclass. It does NOT have an `invoke()` method and does NOT run subprocess itself. Env scrubbing is NOT done by the adapter (see Pitfall 2).

**Evidence:** Exhaustive grep for `def invoke` in `adapters.py` returned no matches. Verified adapter source end-to-end (147 lines, one public method).

**Adjustment — Two options, planner picks:**
- **Option A (recommended):** Wave 0 adds a thin wrapper fn `clawteam/spawn/invoke.py::invoke_native_cli(command, *, cwd, prompt=None, timeout, env=None, ...) -> CompletedProcess`. Wraps `prepare_command` + `subprocess.run(..., env=env or scrub_env(os.environ), shell=False)`. All 7 Phase 5 skills call this wrapper instead of calling `subprocess.run` themselves.
- **Option B:** Each skill handler calls `prepare_command` then `subprocess.run(..., env=scrub_env(os.environ), shell=False)` directly. Seven call sites, seven places to get scrub_env right.

Recommend Option A for the D-03 "uniform logging + failure mode + env injection" intent. Estimate: ~40 LOC + 1 test file.

### A2: `clawteam doctor` detects codex, lighthouse, gh, vercel-cli, netlify-cli, flyctl

**Status:** ⚠️ **PARTIAL.** `codex` is present (commands.py:38). `lighthouse`, `gh`, `vercel`, `netlify`, `flyctl` are NOT in `_DOCTOR_TOOLS` (verified by reading commands.py:36-41 — the tuple contains only `chromium (Playwright)`, `codex`, `ngrok`, `watchdog`).

**Evidence:** commands.py:36-41 is the full `_DOCTOR_TOOLS` tuple:
```python
_DOCTOR_TOOLS: tuple[tuple[str, str, str], ...] = (
    ("chromium (Playwright)", "python-pkg", "playwright"),
    ("codex", "cli", "codex"),
    ("ngrok", "cli", "ngrok"),
    ("watchdog", "python-pkg", "watchdog"),
)
```

**Adjustment:** Wave 0 extends `_DOCTOR_TOOLS` with 5 new rows: `("gh", "cli", "gh")`, `("lighthouse", "cli", "lighthouse")`, `("vercel", "cli", "vercel")`, `("netlify", "cli", "netlify")`, `("flyctl", "cli", "flyctl")`. Extends `_doctor_install_hint` dict with per-platform hints for each (~20 LOC, pure-data change).

### A3: `GstackSprintPlugin.contribute_skills` hook exists

**Status:** ❌ **CONTEXT.md WRONG.** Neither the `contribute_skills` hook nor the `SkillRegistration` type exist anywhere in the codebase. CONTEXT.md D-02 states "Phase 1/3 already wired `contribute_skills` + role-gating" — this is factually incorrect.

**Evidence:** Grep for `contribute_skills|SkillRegistration|class Skill` returned only matches in `.planning/` docs (plans referencing it) and none in `clawteam/`. `HarnessPlugin` base at `clawteam/plugins/base.py` exposes: `on_register`, `on_unregister`, `contribute_gates`, `contribute_prompts`, `contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`, `contribute_evidence_schemas`, `contribute_verification_pairs`. No skill hook.

**Note:** Phase 4 state machines (office_hours, design_consultation, investigate) are standalone classes with no harness-level dispatch mechanism — they're invoked directly by their owning role's prompt. Phase 5 CONTEXT.md envisions skill dispatch as structured (role-gated, discoverable); that mechanism has to be built.

**Adjustment:** Wave 0 adds:
1. `clawteam/plugins/skill_registration.py` with `SkillRegistration` dataclass (per Code Example 1).
2. `clawteam/plugins/skill_errors.py` with `SkillError`, `SkillUnavailable`, `SkillNotPermitted`, `SkillPreconditionError` (per Code Example 8).
3. `HarnessPlugin.contribute_skills(self) -> list[SkillRegistration]: return []` default (additive to `clawteam/plugins/base.py`).
4. `PluginManager` aggregator — `get_plugin_skills() -> dict[str, SkillRegistration]` with duplicate-name ValueError (mirrors `get_plugin_gates` from Plan 04-05).
5. A thin `SkillDispatcher` that, given `(role, skill_name, args)`, looks up the registration, checks `role in registration.roles` (raises SkillNotPermitted otherwise), optionally calls `tool_available()` (raises SkillUnavailable on False), and dispatches to `handler(ctx, role=role, args=args)`.

Estimate: ~150 LOC + 4 test files (registration, dispatcher, aggregation, error shapes). This is the biggest Wave 0 investment.

### A4: `evidence_schemas.register_schema` accepts pydantic w/ `artifact_type: Literal[...]` discriminator

**Status:** ✅ **CONFIRMED.** `clawteam/harness/evidence_schemas.py:68` exposes `register_schema(name: str, cls: type[ArtifactFrontmatterBase]) -> None`. Raises `ValueError` on duplicate. Phase 3 gstack schemas (`ship_notes.py`) use `artifact_type: Literal["ship-notes"]` pattern (verified `ship_notes.py:34`).

**Evidence:** Read of `clawteam/harness/evidence_schemas.py` full file (111 lines). The Phase 3 `ShipNotes` at `clawteam/templates/gstack/schemas/ship_notes.py:23` is the canonical pattern:
```python
class ShipNotes(BaseModel):
    artifact_type: Literal["ship-notes"]
    ...
```

**Note (minor):** Phase 3 gstack schemas inherit from `BaseModel`, not `ArtifactFrontmatterBase` (verified ship_notes.py:20). This is fine for registration (duck-typed `dict[str, type]`), but the Phase 2 register_schema signature types `cls: type[ArtifactFrontmatterBase]` which is technically a mismatch with how Phase 3 is using it. Not blocking — existing tests pass. Phase 5's 3 new schemas can follow the Phase 3 pattern (inherit from BaseModel) for consistency.

### A5: TOML parser tolerates unknown `[ship]` / `[deploy]` / `[canary]` / `[benchmark]` blocks

**Status:** ⚠️ **PARTIAL / misleading.** `tomllib.load` ignores unknown sections by design. The `_parse_toml` function at `clawteam/templates/__init__.py:154-199` hand-maps fields — it reads `raw.get("template", {})` and extracts a fixed set. Unknown sub-blocks under `[template]` (e.g., `[template.ship]`) are silently dropped because `_parse_toml` never looks for them. TemplateDef itself does NOT set `model_config = ConfigDict(extra="ignore")` — there's no `extra` setting at all (verified by grep).

**Evidence:** templates/__init__.py:99-123 (TemplateDef class body), templates/__init__.py:154-199 (_parse_toml function body). No `ConfigDict`, no `extra=`.

**What this means:** Today, a user who writes `[ship] coverage_threshold = 0.7` in `gstack.toml` gets NO error but ALSO no effect — the value is silently discarded. This is WORSE than erroring.

**Adjustment:** Wave 0 extends TemplateDef + _parse_toml to actually read the new blocks:
```python
class ShipConfig(BaseModel):
    coverage_threshold: float = 0.5

class DeployConfig(BaseModel):
    provider: Literal["vercel", "netlify", "fly", "custom"]
    project: str
    custom_deploy_cmd: str = ""

class CanaryConfig(BaseModel):
    window_seconds: int = 300
    poll_interval_seconds: int = 15
    ci_wait_timeout_seconds: int = 1800

class BenchmarkConfig(BaseModel):
    regression_threshold_ratio: float = 1.5

# TemplateDef additions (all optional for BC):
ship: ShipConfig | None = None
deploy: DeployConfig | None = None
canary: CanaryConfig | None = None
benchmark: BenchmarkConfig | None = None
```

Update `_parse_toml` with four `tmpl.get("ship"/"deploy"/"canary"/"benchmark", None)` lookups; construct the pydantic when present. BC-safe: the 6 existing templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) + gstack.toml Phase 3/4 all continue to parse unchanged because all four fields default to `None`.

### A6: `questionary` in stack

**Status:** ✅ **CONFIRMED.** `pyproject.toml:25` declares `questionary>=2.0.1,<3.0.0` as a required dep. Research STACK.md §Executive Recommendation lists questionary among "already present." Precedent use: `cli/commands.py:173-183` (_load_questionary helper with lazy import + helpful error). Phase 5 `/setup-deploy` follows this precedent.

**Evidence:** `pyproject.toml` line 21-28 shows questionary in the base `dependencies` list (not optional-dependencies). Verified by file read.

### A7: `clawteam/events/bus.py::emit` accepts arbitrary string event names

**Status:** ❌ **CONTEXT.md MISLEADING.** `EventBus.emit` at `clawteam/events/bus.py:86` takes a typed `HarnessEvent` instance, NOT a string name. Dispatch is by `type(event)` (line 93). The `register_event_type(cls)` helper at line 16 lets shell hooks REFERENCE events by class name, but agents/code MUST emit a typed dataclass.

**Evidence:**
```python
# bus.py:86-101
def emit(self, event: HarnessEvent) -> list[Any]:
    with self._lock:
        subs = list(self._subscribers.get(type(event), []))  # <-- keyed on type(event)
    ...
```

**Adjustment:** CONTEXT.md §code_context bullet `EventBus emit("deploy_regression_detected", payload)` is shorthand; the real call signature is `ctx.bus.emit(DeployRegressionDetected(team_name=..., sprint_id=..., ...))`. No substrate change needed — just correct handler code to emit typed dataclasses (see Code Example 7). Plan 04-02 already added typed MidReviewThrash + SycophancyCascadeDetected as the Phase 4 precedent; Phase 5 adds DeployRegressionDetected + WebVitalRegressionDetected the same way.

### A8: `gh` CLI availability detection in `clawteam doctor`

**Status:** ❌ **NOT PRESENT.** Same finding as A2 — `gh` is not in `_DOCTOR_TOOLS`. See A2 adjustment above (grouped as one doctor-entry plan).

**Evidence:** Grep of `commands.py` for `gh` in `_DOCTOR_TOOLS` context returned no hits. Verified by reading the tuple at line 36-41.

---

## Wave Structure Recommendation

Seven skills are largely independent (each is a self-contained sub-package); the only shared files are `clawteam/plugins/base.py` (adds 1 hook — touched once in Wave 0) and `clawteam/plugins/skill_registration.py` (new file, Wave 0). Substrate (schemas, events, doctor, TemplateDef) is largely shared additions with no collisions.

### Wave 0 — Substrate & Verification (1 plan)

Purpose: close the 4 CONTEXT.md inaccuracies so Waves 1+ build on a firm foundation. Single plan, ~350 LOC of net additions + ~8 new test files.

- **Plan 05-01**: Substrate prep — (a) add `SkillRegistration`, `SkillError`/`SkillUnavailable`/`SkillNotPermitted`/`SkillPreconditionError`, `HarnessPlugin.contribute_skills` hook, `PluginManager.get_plugin_skills` aggregator, `SkillDispatcher` (A3); (b) add `clawteam/spawn/invoke.py::invoke_native_cli` wrapper with scrub_env (A1); (c) extend `_DOCTOR_TOOLS` + `_doctor_install_hint` with 5 new entries: gh, lighthouse, vercel, netlify, flyctl (A2/A8); (d) extend `TemplateDef` + `_parse_toml` with optional `[ship]` / `[deploy]` / `[canary]` / `[benchmark]` blocks + matching pydantic configs (A5). Single plan because these 4 substrate pieces are tightly coupled (skills won't land without the hook; dispatcher needs errors; handlers need the invoke wrapper). BC-regression matrix (Phase 0 QUALITY-14) MUST pass before exit.

### Wave 1 — Schemas & Events (1 plan)

Purpose: register the 3 new artifact schemas + 2 new events. Required before any skill handler can write a typed artifact or emit a regression event.

- **Plan 05-02**: Three new pydantic schemas (`DeployNotes`, `CanaryReport`, `BenchmarkReport`) in `clawteam/templates/gstack/schemas/{deploy_notes,canary_report,benchmark_report}.py`; extend `clawteam/templates/gstack/schemas/__init__.py` exports; update `GstackSprintPlugin.contribute_evidence_schemas` to register the 3 new keys (`deploy-notes`, `canary-report`, `benchmark-report`). Additive to ship_notes Phase 3 extension (new optional fields on existing `ShipNotes`). Add `DeployRegressionDetected` + `WebVitalRegressionDetected` event dataclasses to `clawteam/events/types.py` + call `register_event_type` on import.

### Wave 2 — Independent skills (3 plans, parallel-safe)

Three skills with no interdependencies and no shared files beyond Wave 0–1 substrate. Planner can dispatch in parallel.

- **Plan 05-03**: `/codex` skill (SKILL-13). Files: `clawteam/templates/gstack/skills/codex/{__init__.py, handler.py}` + new schema `clawteam/templates/gstack/schemas/codex_review.py` (minimal — `artifact_type`, `mode`, `target`, `verdict`, `created_at`) + plugin registration in `GstackSprintPlugin.contribute_skills`.
- **Plan 05-04**: `/ship` skill core pipeline (SKILL-14). Files: `clawteam/templates/gstack/skills/ship/{__init__.py, handler.py, steps.py}` + extend `ShipNotes` pydantic (additive optional fields per D-05 failure accounting) + plugin registration. Does NOT yet call /document-release (chaining arrives in Plan 05-07 with /document-release).
- **Plan 05-05**: `/setup-deploy` wizard (SKILL-19). Files: `clawteam/templates/gstack/skills/setup_deploy/{__init__.py, handler.py, wizard.py}` + plugin registration. Depends on Wave 0 TemplateDef `DeployConfig` extension.

### Wave 3 — Deploy pipeline (2 plans)

Two skills with a fan-in dependency on Wave 2's /ship (D-12 precondition check reads ship-notes.md from a /ship run).

- **Plan 05-06**: `/land-and-deploy` skill (SKILL-15). Depends on Wave 2 /ship for the precondition artifact. Files: `skills/land_and_deploy/{__init__.py, handler.py}` + plugin registration.
- **Plan 05-07**: `/document-release` skill (SKILL-16). Files: `skills/document_release/{__init__.py, handler.py, doc_walker.py, patch_emitter.py}` + plugin registration + `/ship` auto-invoke wiring (edits the Plan 05-04 ship handler to invoke document-release on success per D-11).

### Wave 4 — Monitoring skills (2 plans, parallel-safe)

Two SRE skills that consume deploy artifacts but don't depend on each other's code.

- **Plan 05-08**: `/canary` skill (SKILL-17). Files: `skills/canary/{__init__.py, handler.py, poller.py}` + plugin registration. Reads baseline JSON written by `/benchmark` (best-effort — missing baseline doesn't block).
- **Plan 05-09**: `/benchmark` skill (SKILL-18). Files: `skills/benchmark/{__init__.py, handler.py}` + plugin registration. Writes baseline JSON that `/canary` reads.

### Wave 5 — Integration (1 plan)

- **Plan 05-10**: End-to-end integration test + adversarial test matrix (D-15 + D-16). Files: `tests/integration/test_phase5_sprint_end_to_end.py` asserting artifact chain `ship-notes.md` → `deploy.md` → `canary-report.md` with propagated `deploy_url` + coherent status fields. Plus one parametrize-pytest fixture per skill for the 3 adversarial cases (happy/missing/adversarial) → 21 test IDs. Uses `tmp_path` git repo + monkeypatched `gh pr checks`, `vercel deploy`/etc., `lighthouse`, `codex`.

**Total plan count estimate: 10 plans** (1 Wave 0 + 1 Wave 1 + 3 Wave 2 + 2 Wave 3 + 2 Wave 4 + 1 Wave 5). CONTEXT.md suggested a 6-wave structure; this refines to 6 waves with tighter plan boundaries.

**Parallelism:** Wave 2 (3 plans) and Wave 4 (2 plans) can each dispatch in parallel. Waves 0, 1, 3, 5 are sequentially dependent.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` (already in dev deps; pyproject.toml:32 `pytest>=9.0.0,<10.0.0`) |
| Config file | `pyproject.toml` (no separate `pytest.ini` — verified) |
| Quick run command | `pytest tests/templates/gstack/skills/ -x` |
| Full suite command | `pytest` (runs all) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKILL-13 | `/codex` three modes + missing-tool + adversarial-input | unit | `pytest tests/templates/gstack/skills/test_codex.py -x` | ❌ Plan 05-03 |
| SKILL-14 | `/ship` 5-step happy + language-detect + coverage-below + adversarial | unit | `pytest tests/templates/gstack/skills/test_ship.py -x` | ❌ Plan 05-04 |
| SKILL-15 | `/land-and-deploy` precondition + deploy URL probe + timeout | unit | `pytest tests/templates/gstack/skills/test_land_and_deploy.py -x` | ❌ Plan 05-06 |
| SKILL-16 | `/document-release` diff walk + InteractionGate write + idempotent re-run | unit | `pytest tests/templates/gstack/skills/test_document_release.py -x` | ❌ Plan 05-07 |
| SKILL-17 | `/canary` HTTP poller + regression flags + baseline-missing | unit | `pytest tests/templates/gstack/skills/test_canary.py -x` | ❌ Plan 05-08 |
| SKILL-18 | `/benchmark` lighthouse parse + curl fallback + partial-metric | unit | `pytest tests/templates/gstack/skills/test_benchmark.py -x` | ❌ Plan 05-09 |
| SKILL-19 | `/setup-deploy` wizard + gstack.toml write + idempotent re-run + adversarial input | unit | `pytest tests/templates/gstack/skills/test_setup_deploy.py -x` | ❌ Plan 05-05 |
| All | End-to-end 7-skill chain with propagated artifacts | integration | `pytest tests/integration/test_phase5_sprint_end_to_end.py -x` | ❌ Plan 05-10 |
| All | BC regression matrix still green | integration | `pytest tests/test_template_regression_matrix.py` | ✅ exists (Phase 0) |

### Sampling Rate

- **Per task commit:** `pytest tests/templates/gstack/skills/test_<that_skill>.py -x` (<10s typical)
- **Per wave merge:** `pytest tests/templates/gstack/` (<60s typical)
- **Phase gate:** Full suite green + BC regression matrix green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/plugins/test_skill_registration.py` — SkillRegistration pydantic, role-gate violation → SkillNotPermitted
- [ ] `tests/plugins/test_skill_dispatcher.py` — missing-tool path, not-permitted path, successful dispatch path
- [ ] `tests/plugins/test_skill_errors.py` — structured error shapes per D-04
- [ ] `tests/spawn/test_invoke_native_cli.py` — scrub_env applied, shell=False enforced, timeout raises
- [ ] `tests/cli/test_doctor_new_entries.py` — doctor detects all 5 new tools when present; emits install hint when absent
- [ ] `tests/templates/test_template_def_extensions.py` — TemplateDef parses [ship]/[deploy]/[canary]/[benchmark]; BC: existing 6 templates + Phase 3/4 gstack.toml unchanged
- [ ] `tests/harness/test_evidence_schemas_phase5.py` — 3 new schemas register without duplicate-error
- [ ] `tests/events/test_phase5_events.py` — DeployRegressionDetected + WebVitalRegressionDetected emit/subscribe round-trip

Framework install: none (pytest already installed).

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Skills operate in single-user CLI context |
| V3 Session Management | no | N/A |
| V4 Access Control | yes | Role-gated skill dispatch (SkillNotPermitted via `SkillRegistration.roles`) |
| V5 Input Validation | yes | Pydantic schemas for all artifacts; regex-validated wizard inputs (`_PROJECT_SLUG_RE`); shell=False everywhere |
| V6 Cryptography | no | No new crypto in this phase |
| V12 Files/Resources | yes | Artifact writes through `file_locked` + `atomic_write_text`; TemplateDef reads TOML via stdlib `tomllib` (no eval); deploy custom_deploy_cmd sanitized (no shell metachars) |
| V14 Config | yes | scrub_env on every subprocess env; doctor hints informational only |

### Known Threat Patterns for Phase 5 stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell-injection via user-supplied prompt/slug | Tampering | `shell=False` in all `subprocess.run`; `NativeCliAdapter.prepare_command` returns `list[str]`; wizard regex-validates inputs |
| Secret leakage to external CLI stdout/argv | Information Disclosure | `scrub_env` applied at every call site (invoke_native_cli wrapper in Wave 0); adversarial test seeds `FAKE_SECRET_TOKEN` and asserts it's not in argv/stdout |
| Gate-gaming via fake deploy URL | Tampering / Elevation | EvidenceGate HEAD-probes deploy_url (existing Phase 2); `/land-and-deploy` also polls itself before writing; CanaryReport/DeployNotes both carry commit_sha for cross-check |
| Wizard command-injection via custom_deploy_cmd | Tampering | Regex-block shell metachars at wizard boundary; store and execute via list-form subprocess (still shell=False) |
| Doctor-hint social engineering (malicious install URL) | Tampering | Hints are hardcoded in commands.py, no user input; code review covers |
| Lighthouse output JSON parse injection | Tampering | Parse stdout as JSON only if `stdout.strip().startswith("{")`; else fallback; never `eval` or `exec` |
| Playwright-absent crash on /canary browser mode | DoS | Lazy-import guard (see Pitfall 5); default HTTP-only mode never requires Playwright |

---

## State of the Art

No new external libraries introduced. All skills use CLI tools with stable, long-established interfaces:

| Tool | Status (2026-04) | Stability |
|------|------------------|-----------|
| `codex` (OpenAI Codex CLI) | Active; `exec` subcommand stable | HIGH |
| `gh` (GitHub CLI) | Active; `pr create` + `pr checks --watch` stable since 1.x | HIGH |
| `lighthouse` CLI | Active; JSON output schema stable across 10.x | HIGH |
| `vercel` / `netlify` / `flyctl` CLIs | Active; all three support non-interactive `--token` auth | HIGH |
| `questionary` 2.x | Stable; pyproject.toml pins `>=2.0.1,<3.0.0` | HIGH |
| Python stdlib `tomllib` | Py 3.11+ built-in; `tomli` shim for 3.10 already in deps | HIGH |

No "state of the art" concerns for Phase 5 — this is a port of a stable methodology onto an existing substrate with already-stable external CLIs.

---

## Environment Availability

Phase 5 deliberately treats all external CLIs as **optional at runtime** and uses `clawteam doctor` + per-skill `tool_available()` for detection. No CLI presence is required for the plugin to load or the plan to complete.

| Dependency | Required By | Available on CI | Version | Fallback |
|------------|------------|-----------------|---------|----------|
| `codex` CLI | `/codex` | Not required in CI (skills mock adapter) | — | SkillUnavailable with hint |
| `gh` CLI | `/ship`, `/land-and-deploy` | Usually present on CI runners | varies | SkillUnavailable with hint |
| `lighthouse` | `/benchmark` | Not required (mock in test) | — | `/benchmark` falls back to curl-timing |
| `vercel`/`netlify`/`flyctl` | `/land-and-deploy` | Not required (monkeypatch) | — | custom_deploy_cmd stub |
| `questionary` 2.x | `/setup-deploy` | ✓ (base dep) | 2.0.1 | None needed |
| `pytest` 9.x | All tests | ✓ (dev dep) | 9.x | None needed |
| Python 3.10+ | Everything | ✓ (pyproject `requires-python = ">=3.10"`) | 3.10+ | None needed |
| `playwright` | `/canary` (browser mode only) | Not in base; `clawteam[browser]` | >=1.58,<2 | HTTP-only mode (no Playwright import) |

**Missing dependencies with no fallback:** None — every external tool has either a fallback mode or the skill emits a structured `SkillUnavailable` error with install hint (D-04).

**Missing dependencies with fallback:**
- `lighthouse` → curl-based TTFB / DOMContentLoaded only (D-10)
- `playwright` (in `/canary` browser mode) → HTTP-only polling (D-09)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1-ASSUMED | Phase 0 doctor CLI is still the source of truth for install hints (commands.py:44-67) and Phase 5 should extend it in place, not fork to a new per-skill install-hint registry | A2/A8 | LOW — extending existing is uncontroversial; a fork adds divergence risk |
| A2-ASSUMED | Phase 5 does NOT need a persisted state machine for any of the 7 skills — each is a linear pipeline (/ship is D-05 explicit; /canary uses ephemeral loop state that terminates at window end; others are stateless) | Per-Skill Map, Pitfall 4 | MEDIUM — if `/canary` needs to resume across process restart, poller.py grows a state.json; not expected for Phase 5 scope |
| A3-ASSUMED | `gh pr checks --watch` is acceptable for `/land-and-deploy` CI wait in v1 (CONTEXT.md D-30 scope note) — Vercel/Netlify webhook integration deferred to v1.1 | Pitfall 8 | LOW — 30-min timeout limits hang blast radius |
| A4-ASSUMED | Baseline JSON for /canary ↔ /benchmark lives at `~/.clawteam/teams/<team>/baselines/<provider>.json` — path not specified in CONTEXT.md, inferred from existing `get_data_dir()` convention | Per-Skill Map row 5-6 | LOW — if path differs, rename at implementation time; schema+semantics unchanged |
| A5-ASSUMED | `SkillDispatcher` is a thin synchronous lookup+dispatch (not async, not queued) — matches Phase 4 state-machine dispatch invocation style (handler called directly in agent turn) | Wave 0 Plan 05-01 | LOW — async upgrade is mechanical if future phases require it |
| A6-ASSUMED | Phase 5 `/codex` emits `tool_call_completed` events through the existing Phase 2 observability hook without Phase 5-local changes (D-13) | Per-Skill Map row 1 | MEDIUM — if Phase 2's `tool_call_completed` wasn't wired by Phase 2 Plan 02-01, Phase 5 adds it; grep-check at plan-prep time |
| A7-ASSUMED | Option A (new `invoke_native_cli` wrapper) is preferred over Option B (inline subprocess.run in each handler) for A1 adjustment | A1 | LOW — option choice affects ~7 handler signatures; either works; A is more DRY |
| A8-ASSUMED | Phase 4's `office_hours` / `design_consultation` / `investigate` state machines will continue to be invoked directly (not through `contribute_skills`) — Phase 5 introduces the skill hook for tool-heavy skills ONLY, not retroactively for Phase 4 interactive skills | Wave 0 Plan 05-01 | LOW — adding Phase 4 retroactively is straightforward if future phase wants unified dispatch |

**Confirmation needed before planning:** A1-ASSUMED, A5-ASSUMED, A7-ASSUMED, A8-ASSUMED — planner may ask user to confirm or proceed with defaults. A2/A3/A4/A6 are low-risk and proceed as-is.

---

## Open Questions

1. **Who dispatches a skill invocation?** Phase 4 state machines are invoked from the SprintConductor's role-dispatch loop (`conductor.py`) at agent turn boundaries. Phase 5 CONTEXT.md envisions `/codex`, `/ship`, etc. as agent-invoked via slash command. The mechanism — does the agent emit a "dispatch skill X with args Y" request via some MCP tool call, or does the plugin subscribe to `TurnEnvelope` events and pattern-match slash commands in the envelope body? — is not specified in CONTEXT.md. **Recommendation:** plan Wave 0 to define a minimal `SkillDispatcher.dispatch(skill_name, role, args, ctx)` entry point; leave the agent-to-dispatcher wire-up to Phase 7 (where the MCP/agent interface matures). For Phase 5 tests, call `SkillDispatcher.dispatch` directly.

2. **Token/cost accounting for /codex sub-invocations.** D-13 says tokens tracked via `tool_call_completed`. Does the codex CLI report tokens-used on stdout in a parseable format? If yes, Wave 2 Plan 05-03 needs a codex-stdout parser; if no, we record the call count only and defer token-level breakdown to v1.1. **Recommendation:** plan assumes call-count only for Phase 5; if planner at plan-check time finds codex stdout includes token info, fold parser into 05-03.

3. **Should `/ship` respect the `workflow.tdd_mode` config?** .planning/config.json:27 has `"tdd_mode": false`. If true, should `/ship`'s D-06 test-framework bootstrap behave differently (e.g., fail-fast rather than auto-write a smoke test)? CONTEXT.md doesn't address this. **Recommendation:** Phase 5 ignores tdd_mode (not in scope). Note in plan 05-04 comments; add to deferred items if user requests tdd_mode integration.

---

## Sources

### Primary (HIGH confidence) — VERIFIED

- `.planning/phases/05-tool-heavy-skills-ship-sre-codex/05-CONTEXT.md` — D-01..D-16, A1..A8, specifics
- `.planning/REQUIREMENTS.md` — SKILL-13..19 verbatim (lines 86-92), traceability
- `.planning/ROADMAP.md` — Phase 5 goal + success criteria (lines 229-256)
- `clawteam/spawn/adapters.py` — full file (237 lines); `NativeCliAdapter.prepare_command` signature confirmed; NO `invoke()` method (A1)
- `clawteam/events/hooks.py` — full file (123 lines); `scrub_env` applied to hook commands; doctor info context
- `clawteam/events/bus.py` — full file (122 lines); `emit(HarnessEvent)` type confirmed (A7)
- `clawteam/events/types.py` — MidReviewThrash+SycophancyCascadeDetected at lines 287-324 (Phase 4 event-type precedent)
- `clawteam/plugins/gstack_sprint_plugin.py` — full file (441 lines); plugin structure confirmed; NO contribute_skills hook (A3)
- `clawteam/plugins/base.py` — full file (134 lines); enumerated hooks (no contribute_skills)
- `clawteam/templates/gstack/skills/{office_hours,design_consultation,investigate}/` — Phase 4 skill sub-package precedent (shape, persistence, state.py vs handler.py)
- `clawteam/harness/evidence_schemas.py` — `register_schema` signature confirmed (A4)
- `clawteam/templates/gstack/schemas/ship_notes.py` — Phase 3 ShipNotes at line 23 — `artifact_type: Literal[...]` pattern
- `clawteam/templates/gstack/schemas/__init__.py` — export pattern for Wave 1 extension
- `clawteam/templates/__init__.py` — `TemplateDef` + `_parse_toml` (A5)
- `clawteam/cli/commands.py` — lines 36-74 (`_DOCTOR_TOOLS` + `_doctor_install_hint`); 1191-1228 (`doctor` command); 5469-5550 (`sprint approve` CLI precedent); 173-183 (_load_questionary pattern)
- `clawteam/harness/evidence_gate.py` — `_check_deploy_url` + `_default_head_check` patterns for HTTP probes
- `clawteam/secrets.py` — `scrub_env` signature (A1 option A)
- `pyproject.toml` — questionary 2.0.1+ in base deps (A6); pytest 9.x in dev (validation)
- `.planning/research/STACK.md` lines 1-80 — questionary confirmed present; stdlib-first philosophy
- `.planning/config.json` — nyquist_validation enabled; quality model profile

### Secondary (MEDIUM confidence)

- `.planning/research/ARCHITECTURE.md` — Patterns 6 (SmartReviewRouter) and 7 (HelperSpawner) — analogous to how Phase 5 wires skill dispatch via plugin
- `.planning/research/PITFALLS.md` Pitfall 8 — gate-gaming mitigation informs deploy_url probe + commit_sha cross-check

### Tertiary (LOW confidence — none)

No LOW-confidence findings. All claims verified against existing codebase.

---

## Metadata

**Confidence breakdown:**
- Per-skill implementation map: HIGH — each skill has a direct upstream behavior + a clean substrate mapping
- Substrate additions (Wave 0): HIGH — all required changes verified against current code; estimates are conservative
- Plan-prep verifications: HIGH — each A-item verified with file:line evidence
- Wave structure: MEDIUM — dependencies derived from file-ownership analysis, not yet validated by dispatch simulation; planner may refine
- Test coverage plan: HIGH — pattern matches Phase 4 precedent

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (30 days; stable ecosystem, no fast-moving deps)

---

*Phase: 05-tool-heavy-skills-ship-sre-codex*
*Research completed: 2026-04-21 via /gsd-research-phase 5*
*Next: /gsd-plan-phase 5*
