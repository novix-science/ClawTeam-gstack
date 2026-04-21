---
phase: 04
plan: 10
type: execute
wave: 3
depends_on: [01, 02, 05, 06]
files_modified:
  - clawteam/sprint/review_phase.py
  - clawteam/sprint/conductor.py
  - tests/test_review_phase_dispatch.py
autonomous: true
requirements: [SPRINT-04, SPRINT-05, QUALITY-07, QUALITY-09, QUALITY-13]
must_haves:
  truths:
    - "New file clawteam/sprint/review_phase.py exposes async def dispatch_review_phase(state, plugin_manager, bus)."
    - "SprintConductor gains a thin sync wrapper _dispatch_review_phase that pins review_sha and runs the async dispatcher."
    - "review_sha is set from `git rev-parse HEAD` at Review-phase entry if not already pinned."
    - "Routers contributed via plugin_manager.get_review_routers() are consulted; reviewer floor always included."
    - "Peer reviewers dispatched in parallel via asyncio.gather with isolated sub-conversations (no peer-draft sharing)."
    - "reviewer aggregator runs SEQUENTIALLY after gather completes."
    - "Post-turn hook compares HEAD to review_sha; on advance, emits MidReviewThrash event with diff delta."
    - "Agreement-rate computed after aggregation; > threshold emits SycophancyCascadeDetected event."
    - "Per-sprint-per-round scoping of sycophancy event (D-20)."
    - "REVISION (Task 3): SprintConductor._build_gate_chain unions CrossAgentVerificationGate instances (from plugin_manager.get_verification_pairs() filtered by phase) AND plugin-contributed gates (from plugin_manager.get_plugin_gates(phase)) — closes ISS-03 (ShipApprovalGate unreachable) + ISS-07 (CrossAgentVerificationGate unreachable)."
    - "REVISION: save_sprint_state module-level helper in clawteam/sprint/state.py exists and is the call site for state persistence (ISS-09)."
  artifacts:
    - path: "clawteam/sprint/review_phase.py"
      provides: "async dispatch_review_phase + agreement-rate helper + SHA-diff helpers"
      contains: "async def dispatch_review_phase"
      min_lines: 180
    - path: "clawteam/sprint/conductor.py"
      provides: "New _dispatch_review_phase method + review_sha pinning on Review-phase entry + Task 3 _build_gate_chain extension that wires plugin gates + CrossAgentVerificationGate"
      contains: "_dispatch_review_phase"
    - path: "tests/test_review_phase_dispatch.py"
      provides: "Parallel dispatch + SHA-pin + thrash event + sycophancy event + aggregation tests"
      contains: "def test_review_sha_pinned_on_entry"
  key_links:
    - from: "clawteam/sprint/review_phase.py"
      to: "clawteam/events/types.py::MidReviewThrash + SycophancyCascadeDetected"
      via: "bus.emit(MidReviewThrash(...))"
    - from: "clawteam/sprint/conductor.py::_dispatch_review_phase"
      to: "clawteam/sprint/review_phase.py::dispatch_review_phase"
      via: "asyncio.run(dispatch_review_phase(...))"
    - from: "clawteam/sprint/review_phase.py"
      to: "plugin_manager.get_review_routers()"
      via: "Iterate routers, union matches with floor"
    - from: "clawteam/sprint/conductor.py::_build_gate_chain (Task 3)"
      to: "clawteam/plugins/manager.py::PluginManager.get_plugin_gates + get_verification_pairs"
      via: "Union plugin-contributed gates + construct CrossAgentVerificationGate per phase (closes ISS-03 + ISS-07)"
---

<objective>
Ship the Review-phase orchestration: parallel peer-reviewer dispatch via `asyncio.gather`, sequential `reviewer` aggregator after peers complete, SHA-pinning at entry, mid-review-thrash detection on post-turn HEAD advance, and sycophancy-cascade alarm on agreement-rate threshold crossings. **Task 3 (REVISION)** additionally wires plugin-contributed gates (Plan 04-05 accessors) into `SprintConductor._build_gate_chain` so `ShipApprovalGate` (Plan 11) and `CrossAgentVerificationGate` (Plan 03 + Plan 11) actually execute in production — closes ISS-03 and ISS-07.

Purpose: The glue layer consuming all Wave 1 + 2 substrate. This is where the parallel reviewers actually run. Per research §Open Question 1, implemented as a new module `clawteam/sprint/review_phase.py` (keeps conductor.py under 700 LOC); SprintConductor gets a thin sync wrapper method `_dispatch_review_phase` that invokes `asyncio.run` on the async dispatcher and stores the resulting SHA.

Output: 1 new module + 1 conductor extension + 1 test file. Zero modifications to Wave 1 substrate or Wave 2 state machines.

**Scope note:** Plan 10 ships the *orchestration skeleton* + the SHA-pin + the event-emission wiring. The per-agent spawn path uses an injectable `spawn_reviewer_fn` callable (defaulting to a stub that returns a synthetic review artifact) so this plan is testable in isolation. Plan 11 ships `GstackSprintPlugin.contribute_review_routers` which plugs routers in via the plugin manager; the real spawn integration with existing agent-spawn machinery (Phase 2 spawn registry) remains the contract — Plan 10 provides the `spawn_reviewer_fn` seam and a default sync-bridge per PLAN_PREP_NOTES `## A-spawn`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-RESEARCH.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md

<interfaces>
From clawteam/sprint/state.py (after Plan 02):
```python
class SprintState(BaseModel):
    review_sha: str | None = None  # Plan 02 additive
    workspace_branch: str = ""
    artifacts: dict[str, str] = Field(default_factory=dict)
    team: str
    sprint_id: str
    # ...
```

From clawteam/sprint/conductor.py (existing):
```python
def advance_phase(self, sprint_id: str, actor: str = "") -> tuple[bool, str]:
    # line 304, existing — runs gate chain then flips current_phase.
def _build_gate_chain(self, state: SprintState) -> list:
    # line 517, existing.
def _emit_phase_transition(self, from_phase, to_phase, state) -> None:
    # line 551, existing.
```

From clawteam/plugins/manager.py (existing):
```python
# Existing accessor for contribute_review_routers is via phase_registry
# (see manager.py:150 — contribute_review_routers passed to get_registry().register)
# get_registry().get_review_routers() returns all registered routers.
```

From clawteam/events/types.py (after Plan 02):
```python
@dataclass
class MidReviewThrash(HarnessEvent):
    sprint_id: str = ""
    review_sha: str = ""
    new_sha: str = ""
    reviewer_roles_active: list[str] = field(default_factory=list)
    diff_paths_added: list[str] = field(default_factory=list)
    diff_paths_removed: list[str] = field(default_factory=list)

@dataclass
class SycophancyCascadeDetected(HarnessEvent):
    sprint_id: str = ""
    review_round: int = 0
    agreement_rate: float = 0.0
    threshold: float = 0.9
    reviewer_roles: list[str] = field(default_factory=list)
```

Per PLAN_PREP_NOTES A-spawn: use the chosen sync-to-asyncio bridge pattern.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Implement dispatch_review_phase + helpers in clawteam/sprint/review_phase.py</name>
  <files>clawteam/sprint/review_phase.py, tests/test_review_phase_dispatch.py</files>
  <read_first>
    - clawteam/sprint/state.py (after Plan 02 — review_sha field + SprintState shape)
    - clawteam/events/types.py (after Plan 02 — event dataclasses)
    - clawteam/events/bus.py (EventBus emit signature)
    - clawteam/harness/evidence_gate.py (lines 85-103 — subprocess.run pattern to mirror)
    - clawteam/harness/review_router.py (Protocol)
    - clawteam/harness/phase_registry.py (get_review_routers accessor — find it)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md (A-spawn bridge pattern)
  </read_first>
  <behavior>
    - Test 1 (test_pin_review_sha_at_entry): Fresh state.review_sha=None → dispatch pins from `git rev-parse HEAD` (mocked subprocess); state.review_sha populated.
    - Test 2 (test_router_participants_unioned_with_floor): Two routers each return ["designer"] and ["dx-lead"]; participants = {reviewer, designer, dx-lead}.
    - Test 3 (test_reviewer_always_in_participants): No router matches → participants == {"reviewer"}.
    - Test 4 (test_peer_reviewers_run_in_parallel_before_aggregator): Inject a spawn_fn that records invocation order + sleeps; assert peers (designer/security/dx-lead) all start before reviewer starts (by timestamp).
    - Test 5 (test_reviewer_aggregator_sequential_after_peers): Reviewer invocation receives peer_reports in its context kwargs.
    - Test 6 (test_mid_review_thrash_emitted_when_head_advances): Mock `_current_head` to return different SHA post-gather; assert MidReviewThrash event is captured by bus subscriber with correct diff delta.
    - Test 7 (test_no_thrash_when_head_stable): Head same before + after → no MidReviewThrash emitted.
    - Test 8 (test_sycophancy_cascade_emitted_when_agreement_above_threshold): Stub peer_reports with 90% identical severity ratings → SycophancyCascadeDetected event emitted.
    - Test 9 (test_sycophancy_not_emitted_when_below_threshold): Divergent reports → no event.
    - Test 10 (test_agreement_rate_zero_when_no_findings): Empty reports → 0.0 rate; no event.
    - Test 11 (test_dispatch_returns_result_dict): Return value includes review_sha, participants, peer_reports, reviewer_report, agreement_rate keys.
    - Test 12 (test_router_exception_skipped_and_logged): One router raises → others still consulted; warning logged.
    - Test 13 (test_spawn_reviewer_exception_propagates_via_gather): With return_exceptions=True, one spawn failure doesn't crash gather; failed peer report is the Exception.
  </behavior>
  <action>
Create `clawteam/sprint/review_phase.py`:

```python
"""Review-phase orchestration: parallel peers + sequential aggregator + SHA-pin + events.

§04-CONTEXT D-05/D-06/D-08/D-09/D-19/D-20. Ships the Review-phase dispatcher
as a standalone module (Open Question 1 decision): keeps clawteam/sprint/conductor.py
under ~700 LOC and isolates review-phase testability.

Contract:
    state = SprintState(...)
    result = asyncio.run(dispatch_review_phase(state, plugin_manager, bus, spawn_fn))

Where ``spawn_fn(role, state, review_sha, peer_reports) -> dict`` is the
per-reviewer dispatcher. Default ``_default_spawn_fn`` is a stub that returns
a synthetic review-report.md dict; Phase 5+ integrations override with the
real agent-spawn path. See PLAN_PREP_NOTES A-spawn for the chosen bridge pattern.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Any, Awaitable, Callable

from clawteam.events.types import MidReviewThrash, SycophancyCascadeDetected
from clawteam.sprint.state import SprintState, save_sprint_state

_logger = logging.getLogger(__name__)

_FLOOR_REVIEWER_ROLE = "reviewer"
_GIT_TIMEOUT_SECONDS = 10

# spawn_fn signature: async callable returning a dict-shaped review report.
SpawnFn = Callable[..., Awaitable[dict]]


# ── Subprocess helpers (mirror evidence_gate.py shell=False pattern) ──


def _current_head(workspace: str, *, subprocess_runner: Callable = subprocess.run) -> str:
    if not workspace:
        return ""
    try:
        result = subprocess_runner(
            ["git", "rev-parse", "HEAD"],
            cwd=workspace,
            shell=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning("_current_head failed for %r: %s", workspace, exc)
        return ""
    return (result.stdout or "").strip()


def _diff_paths(
    workspace: str,
    base_sha: str,
    head_sha: str,
    *,
    subprocess_runner: Callable = subprocess.run,
) -> list[str]:
    if not workspace or not base_sha:
        return []
    try:
        result = subprocess_runner(
            ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"],
            cwd=workspace,
            shell=False,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning("_diff_paths failed: %s", exc)
        return []
    return [p for p in (result.stdout or "").splitlines() if p]


# ── Agreement-rate computation (D-09 — severity-only per RESEARCH Open Q3) ──


def _compute_agreement_rate(peer_reports: list[Any]) -> float:
    """(identical severity ratings) / (findings on most-verbose reviewer).

    RESEARCH Open Question 3 resolution: severity-only. Each peer_report
    is expected to be a dict with `findings: list[{severity: str}]`. Non-
    dict reports (exceptions from return_exceptions=True) contribute 0.
    """
    rated: list[list[str]] = []
    for rep in peer_reports:
        if not isinstance(rep, dict):
            continue
        findings = rep.get("findings") or []
        severities = [str(f.get("severity", "")) for f in findings if isinstance(f, dict)]
        rated.append(severities)

    if not rated:
        return 0.0
    max_len = max(len(s) for s in rated)
    if max_len == 0:
        return 0.0
    # Count positions where all peers share identical severity (intersection cardinality).
    # For each position i up to max_len, check if all lists have index i and same value.
    matched = 0
    for i in range(max_len):
        values = []
        for s in rated:
            if i < len(s):
                values.append(s[i])
        if len(values) == len(rated) and len(set(values)) == 1:
            matched += 1
    return matched / max_len


# ── Default spawn (stub — Phase 5 replaces with real spawn bridge) ───


async def _default_spawn_fn(role: str, state: SprintState, review_sha: str, peer_reports: list[Any] | None = None) -> dict:
    """Synthetic peer review — Phase 4 tests use this as a no-op.

    Real integration with agent spawn path lands in Phase 5 or follow-up.
    Returns a minimal review-report dict suitable for agreement-rate math.
    """
    await asyncio.sleep(0)  # cooperative yield
    return {
        "role": role,
        "sprint_id": state.sprint_id,
        "review_sha": review_sha,
        "findings": [],
    }


# ── Main dispatcher ──────────────────────────────────────────────────


async def dispatch_review_phase(
    state: SprintState,
    plugin_manager: Any,
    bus: Any,
    *,
    spawn_fn: SpawnFn | None = None,
    subprocess_runner: Callable = subprocess.run,
    sycophancy_threshold: float = 0.9,
) -> dict:
    """Orchestrate Review-phase parallel dispatch + events.

    Steps:
      1. Pin ``state.review_sha`` from ``git rev-parse HEAD`` (if unset).
      2. Compute diff paths as of ``review_sha`` + apply routers + reviewer floor.
      3. asyncio.gather peer reviewers (participants - {"reviewer"}).
      4. Post-turn thrash check: if HEAD advanced, emit MidReviewThrash.
      5. Run ``reviewer`` aggregator sequentially with peer_reports in context.
      6. Compute agreement rate; if > threshold, emit SycophancyCascadeDetected.
    Returns dict: {review_sha, participants, peer_reports, reviewer_report, agreement_rate}.
    """
    spawn_fn = spawn_fn or _default_spawn_fn
    workspace = state.workspace_branch or ""

    # 1. Pin review_sha.
    if not state.review_sha:
        head = _current_head(workspace, subprocess_runner=subprocess_runner)
        state.review_sha = head or ""
        try:
            save_sprint_state(state)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("save_sprint_state failed: %s", exc)
    review_sha = state.review_sha or ""

    # 2. Participants: routers union reviewer floor.
    diff_paths = _diff_paths(workspace, review_sha, review_sha, subprocess_runner=subprocess_runner)
    participants: set[str] = {_FLOOR_REVIEWER_ROLE}
    routers = _collect_routers(plugin_manager)
    for router in routers:
        try:
            matched = router.match(diff_paths, state)
            if matched:
                participants.update(matched)
        except Exception as exc:  # noqa: BLE001 — RFC 001 §4.3b req 4
            _logger.warning("Router %r raised during match: %s", type(router).__name__, exc)
            continue

    peer_roles = sorted(participants - {_FLOOR_REVIEWER_ROLE})

    # 3. Parallel peer dispatch.
    peer_results = await asyncio.gather(
        *[spawn_fn(r, state, review_sha) for r in peer_roles],
        return_exceptions=True,
    )

    # 4. Thrash check post-gather.
    new_head = _current_head(workspace, subprocess_runner=subprocess_runner)
    if new_head and review_sha and new_head != review_sha:
        new_diff = _diff_paths(workspace, review_sha, new_head, subprocess_runner=subprocess_runner)
        added = [p for p in new_diff if p not in diff_paths]
        removed = [p for p in diff_paths if p not in new_diff]
        try:
            bus.emit(MidReviewThrash(
                team_name=state.team,
                sprint_id=state.sprint_id,
                review_sha=review_sha,
                new_sha=new_head,
                reviewer_roles_active=peer_roles + [_FLOOR_REVIEWER_ROLE],
                diff_paths_added=added,
                diff_paths_removed=removed,
            ))
        except Exception as exc:  # noqa: BLE001
            _logger.warning("bus.emit MidReviewThrash failed: %s", exc)

    # 5. Reviewer aggregator runs sequentially with peer reports in context.
    reviewer_report = await spawn_fn(
        _FLOOR_REVIEWER_ROLE, state, review_sha, peer_reports=list(peer_results),
    )

    # 6. Agreement-rate alarm (D-09/D-20).
    agreement_rate = _compute_agreement_rate(peer_results)
    if agreement_rate > sycophancy_threshold:
        try:
            bus.emit(SycophancyCascadeDetected(
                team_name=state.team,
                sprint_id=state.sprint_id,
                review_round=len(state.phase_history),
                agreement_rate=agreement_rate,
                threshold=sycophancy_threshold,
                reviewer_roles=peer_roles,
            ))
        except Exception as exc:  # noqa: BLE001
            _logger.warning("bus.emit SycophancyCascadeDetected failed: %s", exc)

    return {
        "review_sha": review_sha,
        "participants": sorted(participants),
        "peer_reports": list(peer_results),
        "reviewer_report": reviewer_report,
        "agreement_rate": agreement_rate,
    }


def _collect_routers(plugin_manager: Any) -> list[Any]:
    """Best-effort extraction of ReviewRouter instances from the plugin manager.

    Tries multiple accessor paths so the dispatcher doesn't tightly couple
    to one plugin-manager API shape (phase_registry vs direct).
    """
    routers: list[Any] = []

    # 1. Try plugin_manager.get_review_routers() (if accessor exists).
    getter = getattr(plugin_manager, "get_review_routers", None)
    if callable(getter):
        try:
            rs = getter() or []
            routers.extend(rs)
            return routers
        except Exception:  # noqa: BLE001
            pass

    # 2. Try phase_registry.get_review_routers() via global.
    try:
        from clawteam.harness.phase_registry import get_registry
        reg = get_registry()
        accessor = getattr(reg, "get_review_routers", None)
        if callable(accessor):
            routers.extend(accessor() or [])
    except Exception:  # noqa: BLE001
        pass

    return routers
```

Create `tests/test_review_phase_dispatch.py`:

```python
"""Tests for clawteam/sprint/review_phase.py (Plan 04-10 — SPRINT-04/QUALITY-09/QUALITY-13)."""

from __future__ import annotations

import asyncio
import subprocess
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import MidReviewThrash, SycophancyCascadeDetected
from clawteam.sprint.review_phase import (
    _compute_agreement_rate,
    _current_head,
    _diff_paths,
    dispatch_review_phase,
)


def _state(tmp_path, team="t1", sprint_id="abc12345"):
    from clawteam.sprint.state import SprintState
    return SprintState(
        team=team,
        sprint_id=sprint_id,
        goal="g",
        current_phase="review",
        workspace_branch=str(tmp_path),
    )


def _mock_subprocess(head_sequence: list[str], diff_output: str = ""):
    """Return a subprocess.run mock that yields head_sequence on successive rev-parse calls."""
    calls = {"count": 0}

    def runner(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if len(cmd) >= 2 and cmd[1] == "rev-parse":
            idx = min(calls["count"], len(head_sequence) - 1)
            r.stdout = head_sequence[idx] + "\n"
            calls["count"] += 1
        elif len(cmd) >= 2 and cmd[1] == "diff":
            r.stdout = diff_output
        else:
            r.stdout = ""
        r.stderr = ""
        return r

    return runner


class _CapturingBus(EventBus):
    def __init__(self):
        super().__init__()
        self.captured_thrash: list[MidReviewThrash] = []
        self.captured_sycophancy: list[SycophancyCascadeDetected] = []
        self.subscribe(MidReviewThrash, lambda e: self.captured_thrash.append(e))
        self.subscribe(SycophancyCascadeDetected, lambda e: self.captured_sycophancy.append(e))


class _FakePluginManager:
    def __init__(self, routers: list[Any] | None = None):
        self._routers = routers or []

    def get_review_routers(self):
        return list(self._routers)


class _Router:
    def __init__(self, result):
        self._result = result

    def match(self, diff_paths, state):
        return list(self._result)


class _ThrowingRouter:
    def match(self, diff_paths, state):
        raise RuntimeError("boom")


# ── Agreement-rate helper ────────────────────────────────────────────

def test_agreement_rate_all_identical():
    peers = [
        {"findings": [{"severity": "blocker"}, {"severity": "major"}]},
        {"findings": [{"severity": "blocker"}, {"severity": "major"}]},
    ]
    assert _compute_agreement_rate(peers) == 1.0


def test_agreement_rate_none_identical():
    peers = [
        {"findings": [{"severity": "blocker"}]},
        {"findings": [{"severity": "minor"}]},
    ]
    assert _compute_agreement_rate(peers) == 0.0


def test_agreement_rate_partial():
    peers = [
        {"findings": [{"severity": "blocker"}, {"severity": "major"}]},
        {"findings": [{"severity": "blocker"}, {"severity": "minor"}]},
    ]
    assert _compute_agreement_rate(peers) == 0.5


def test_agreement_rate_empty():
    assert _compute_agreement_rate([]) == 0.0
    assert _compute_agreement_rate([{"findings": []}]) == 0.0


def test_agreement_rate_skips_exceptions():
    peers = [
        Exception("oops"),
        {"findings": [{"severity": "blocker"}]},
    ]
    # Only the dict contributes.
    assert _compute_agreement_rate(peers) == 1.0


# ── _current_head / _diff_paths ──────────────────────────────────────

def test_current_head_empty_workspace():
    assert _current_head("") == ""


def test_diff_paths_empty_when_no_sha():
    assert _diff_paths("/tmp", "", "abc") == []


# ── dispatch_review_phase main path ──────────────────────────────────

def test_review_sha_pinned_on_entry(tmp_path):
    state = _state(tmp_path)
    state.review_sha = None
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["a" * 40, "a" * 40], diff_output="")
    pm = _FakePluginManager()

    result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert state.review_sha == "a" * 40
    assert result["review_sha"] == "a" * 40


def test_reviewer_always_in_participants(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "b" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["b" * 40, "b" * 40])
    pm = _FakePluginManager([])
    result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert "reviewer" in result["participants"]


def test_router_participants_unioned_with_floor(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "c" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["c" * 40, "c" * 40])
    pm = _FakePluginManager([_Router(["designer"]), _Router(["dx-lead", "security"])])
    result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert set(result["participants"]) == {"reviewer", "designer", "dx-lead", "security"}


def test_peer_reviewers_run_in_parallel_before_aggregator(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "d" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["d" * 40, "d" * 40])
    pm = _FakePluginManager([_Router(["designer", "security"])])

    order: list[tuple[str, int]] = []

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        order.append((role, len(order)))
        await asyncio.sleep(0)  # cooperative yield
        return {"role": role, "findings": []}

    result = asyncio.run(dispatch_review_phase(state, pm, bus, spawn_fn=fake_spawn, subprocess_runner=runner))
    # Reviewer was called last.
    assert order[-1][0] == "reviewer"
    # Designer and security called before reviewer.
    roles_before_reviewer = [r for r, _ in order[:-1]]
    assert set(roles_before_reviewer) == {"designer", "security"}


def test_reviewer_aggregator_receives_peer_reports(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "e" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["e" * 40, "e" * 40])
    pm = _FakePluginManager([_Router(["designer"])])

    captured_kwargs: dict = {}

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        if role == "reviewer":
            captured_kwargs["peer_reports"] = peer_reports
        return {"role": role, "findings": []}

    asyncio.run(dispatch_review_phase(state, pm, bus, spawn_fn=fake_spawn, subprocess_runner=runner))
    assert "peer_reports" in captured_kwargs
    assert isinstance(captured_kwargs["peer_reports"], list)
    assert len(captured_kwargs["peer_reports"]) == 1  # designer


def test_mid_review_thrash_emitted_when_head_advances(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "f" * 40
    bus = _CapturingBus()
    # head_sequence: first rev-parse during pin = already set; post-gather rev-parse returns new SHA
    runner = _mock_subprocess(
        head_sequence=["g" * 40, "g" * 40],  # new HEAD returned by _current_head post-gather
        diff_output="src/new.py\n",
    )
    pm = _FakePluginManager()
    asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert len(bus.captured_thrash) == 1
    evt = bus.captured_thrash[0]
    assert evt.review_sha == "f" * 40
    assert evt.new_sha == "g" * 40
    assert evt.sprint_id == "abc12345"


def test_no_thrash_when_head_stable(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "h" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["h" * 40, "h" * 40])
    pm = _FakePluginManager()
    asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert bus.captured_thrash == []


def test_sycophancy_cascade_emitted_when_agreement_above_threshold(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "i" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["i" * 40, "i" * 40])
    pm = _FakePluginManager([_Router(["designer", "security", "dx-lead"])])

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        # All peer roles return identical findings
        return {"role": role, "findings": [{"severity": "blocker"}, {"severity": "major"}]}

    asyncio.run(dispatch_review_phase(
        state, pm, bus, spawn_fn=fake_spawn, subprocess_runner=runner, sycophancy_threshold=0.5,
    ))
    assert len(bus.captured_sycophancy) == 1
    evt = bus.captured_sycophancy[0]
    assert evt.agreement_rate == 1.0
    assert evt.threshold == 0.5


def test_sycophancy_not_emitted_when_below_threshold(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "j" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["j" * 40, "j" * 40])
    pm = _FakePluginManager([_Router(["designer", "security"])])

    counter = {"n": 0}

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        counter["n"] += 1
        return {"role": role, "findings": [{"severity": f"sev-{counter['n']}"}]}

    asyncio.run(dispatch_review_phase(state, pm, bus, spawn_fn=fake_spawn, subprocess_runner=runner))
    assert bus.captured_sycophancy == []


def test_router_exception_skipped_and_logged(tmp_path, caplog):
    state = _state(tmp_path)
    state.review_sha = "k" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["k" * 40, "k" * 40])
    pm = _FakePluginManager([_ThrowingRouter(), _Router(["designer"])])

    with caplog.at_level("WARNING"):
        result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))

    assert "designer" in result["participants"]
    assert any("raised during match" in r.message for r in caplog.records)


def test_spawn_exception_propagates_via_gather(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "l" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["l" * 40, "l" * 40])
    pm = _FakePluginManager([_Router(["designer", "security"])])

    async def flaky_spawn(role, state, review_sha, peer_reports=None):
        if role == "security":
            raise RuntimeError("spawn failed")
        return {"role": role, "findings": []}

    result = asyncio.run(dispatch_review_phase(state, pm, bus, spawn_fn=flaky_spawn, subprocess_runner=runner))
    # peer_reports include both the dict AND the exception (return_exceptions=True).
    assert len(result["peer_reports"]) == 2
    exception_items = [r for r in result["peer_reports"] if isinstance(r, Exception)]
    assert len(exception_items) == 1


def test_dispatch_returns_result_dict(tmp_path):
    state = _state(tmp_path)
    state.review_sha = "m" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["m" * 40, "m" * 40])
    pm = _FakePluginManager([])
    result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert set(result.keys()) == {"review_sha", "participants", "peer_reports", "reviewer_report", "agreement_rate"}
```
  </action>
  <verify>
    <automated>pytest tests/test_review_phase_dispatch.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "async def dispatch_review_phase" clawteam/sprint/review_phase.py
    - grep -q "MidReviewThrash" clawteam/sprint/review_phase.py
    - grep -q "SycophancyCascadeDetected" clawteam/sprint/review_phase.py
    - grep -q "_compute_agreement_rate" clawteam/sprint/review_phase.py
    - wc -l clawteam/sprint/review_phase.py returns >= 180
    - pytest tests/test_review_phase_dispatch.py -x -q exits 0 (18+ tests)
  </acceptance_criteria>
  <done>review_phase.py ships with parallel dispatch, SHA-pin, thrash event, sycophancy event, and aggregation logic</done>
</task>

<task type="auto">
  <name>Task 2: Wire _dispatch_review_phase thin wrapper on SprintConductor</name>
  <files>clawteam/sprint/conductor.py, tests/test_review_phase_dispatch.py</files>
  <read_first>
    - clawteam/sprint/conductor.py (entire file — find insertion point near _build_gate_chain at line 517)
    - clawteam/sprint/review_phase.py (Task 1)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md (A4 decision on new file + thin wrapper)
  </read_first>
  <action>
Edit `clawteam/sprint/conductor.py`:

Insert a new method `_dispatch_review_phase` on `SprintConductor`. Placement: BEFORE `_build_gate_chain` method (around line 517). Add import at top of file (near existing imports):

```python
# (Add near other imports — e.g., after `from clawteam.sprint.state import ...`)
import asyncio as _asyncio
```

Insert method:

```python
    def _dispatch_review_phase(
        self,
        sprint_id: str,
        *,
        plugin_manager=None,
        bus=None,
        spawn_fn=None,
    ) -> dict:
        """Run Review-phase orchestration: pin review_sha + parallel reviewers + events.

        §04-CONTEXT D-05/D-06/D-08. Thin sync wrapper over the async dispatcher
        in clawteam/sprint/review_phase.py (RESEARCH Open Question 1 decision —
        keeps conductor.py under ~700 LOC). Caller is the existing advance_phase
        turn hook OR a direct invocation from CLI/orchestrator.

        Safe to call whether or not ``plugin_manager`` / ``bus`` are supplied:
        defaults use the module-level plugin manager + global event bus.
        """
        from clawteam.sprint.review_phase import dispatch_review_phase

        with self._lock:
            state = self._load_by_id(sprint_id)

        # Use the conductor's existing bus if caller does not override.
        resolved_bus = bus if bus is not None else self.bus

        # Run the async dispatcher sync via asyncio.run.
        return _asyncio.run(
            dispatch_review_phase(
                state,
                plugin_manager,
                resolved_bus,
                spawn_fn=spawn_fn,
            )
        )
```

**Extend `tests/test_review_phase_dispatch.py`** with one smoke test verifying the conductor wrapper. Append:

```python
# ── SprintConductor._dispatch_review_phase thin wrapper ──────────────

def test_conductor_dispatch_wrapper_invokes_async(tmp_path, monkeypatch):
    """Smoke test the conductor wrapper calls the async dispatcher."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    from clawteam.sprint.conductor import SprintConductor
    from clawteam.sprint.state import SprintState, save_sprint_state

    state = SprintState(
        team="t1",
        sprint_id="xyz12345",
        goal="g",
        current_phase="review",
        workspace_branch=str(tmp_path),
        review_sha="n" * 40,
    )
    save_sprint_state(state)

    c = SprintConductor(team_name="t1")
    runner = _mock_subprocess(head_sequence=["n" * 40, "n" * 40])

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        return {"role": role, "findings": []}

    # Monkeypatch subprocess.run for the dispatcher's git calls.
    import clawteam.sprint.review_phase as rp
    monkeypatch.setattr(rp.subprocess, "run", runner)

    pm = _FakePluginManager([_Router(["designer"])])
    result = c._dispatch_review_phase("xyz12345", plugin_manager=pm, spawn_fn=fake_spawn)
    assert result["review_sha"] == "n" * 40
    assert "designer" in result["participants"]
```
  </action>
  <verify>
    <automated>pytest tests/test_review_phase_dispatch.py::test_conductor_dispatch_wrapper_invokes_async -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "def _dispatch_review_phase" clawteam/sprint/conductor.py
    - grep -q "asyncio" clawteam/sprint/conductor.py (module-level import for _asyncio shim)
    - pytest tests/test_sprint_conductor.py -x -q stays green (existing Phase 2 tests unaffected)
    - pytest tests/test_review_phase_dispatch.py::test_conductor_dispatch_wrapper_invokes_async exits 0
    - wc -l clawteam/sprint/conductor.py under 700 lines (keep conductor tractable per research open Q1)
  </acceptance_criteria>
  <done>SprintConductor exposes sync wrapper; conductor size stays under 700 LOC</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Union plugin-contributed gates + CrossAgentVerificationGate into SprintConductor._build_gate_chain (REVISION — closes ISS-03 + ISS-07)</name>
  <files>clawteam/sprint/conductor.py, tests/test_review_phase_dispatch.py</files>
  <read_first>
    - clawteam/sprint/conductor.py::_build_gate_chain (lines 517-549 — existing EvidenceGate → forced_progress_gate → InteractionGate composition)
    - clawteam/plugins/manager.py (after Plan 05 Task 2 — get_plugin_gates accessor) (after Plan 05 Task 1 — get_verification_pairs accessor)
    - clawteam/harness/cross_agent_verification_gate.py (Plan 03 — CrossAgentVerificationGate constructor signature)
    - clawteam/harness/ship_approval_gate.py (Plan 04 — ShipApprovalGate that appears via plugin gates)
  </read_first>
  <behavior>
    - Test 1 (test_build_gate_chain_includes_plugin_gates): Build a conductor with a PluginManager containing a plugin that contributes `{"ship": [ShipApprovalGate()]}`; advance a sprint to ship phase; `_build_gate_chain(state)` output contains a ShipApprovalGate instance after the standard gates.
    - Test 2 (test_build_gate_chain_includes_cross_agent_verification_gates): Build conductor with plugin_manager.get_verification_pairs() returning one pair for phase="test"; sprint in test phase → gate chain includes a CrossAgentVerificationGate constructed from that pair (phase/source/target/verifier match).
    - Test 3 (test_build_gate_chain_filters_verification_pairs_by_phase): Verification pairs for phase="review" are NOT included when sprint is in phase="test".
    - Test 4 (test_build_gate_chain_ordering): Gate chain order is: EvidenceGate → forced_progress_gate → [CrossAgentVerificationGate(s)] → [plugin gates] → [InteractionGate if applicable]. Assert sequence via isinstance checks.
    - Test 5 (test_build_gate_chain_no_plugin_gates_backward_compatible): SprintConductor with no plugin_manager (legacy path) produces the same gate chain as Phase 2. Tests the BC path — existing Phase 2 tests must not regress.
    - Test 6 (test_build_gate_chain_plugin_manager_exception_safe): plugin_manager whose get_plugin_gates raises → gate chain still ships the standard 3 gates; warning logged; sprint advance not crashed.
  </behavior>
  <action>
**Edit 1: `clawteam/sprint/conductor.py`** — modify `SprintConductor.__init__` to optionally accept a plugin_manager, and extend `_build_gate_chain` to union plugin-contributed gates + CrossAgentVerificationGate instances. Preserve existing behavior when plugin_manager is None (BC with Phase 2 callers).

a) Modify `__init__` signature — add `plugin_manager=None` keyword arg. Near the existing `bus: "EventBus | None" = None,` parameter (line ~242), append:
```python
        plugin_manager=None,
```

And add storage for it in __init__ body (right after `self.bus = bus` around line 257):
```python
        # Phase 4 Plan 04-10 Task 3: optional plugin_manager for gate-chain
        # aggregation. When None, _build_gate_chain falls back to the Phase 2
        # three-gate composition (BC — Phase 2 tests do NOT pass a plugin_manager).
        self._plugin_manager = plugin_manager
```

b) Extend `_build_gate_chain` (existing around line 517-549). REPLACE the existing body so it:
  1. Builds EvidenceGate + forced_progress_gate first (unchanged).
  2. Appends CrossAgentVerificationGate instances constructed from plugin_manager.get_verification_pairs() filtered to `pair.phase == state.current_phase`.
  3. Appends plugin gates from plugin_manager.get_plugin_gates(state.current_phase).
  4. Applies existing InteractionGate insertion logic (unchanged) AT THE END of the chain.

Full replacement of `_build_gate_chain`:

```python
    def _build_gate_chain(self, state: SprintState) -> list:
        """Compose EvidenceGate → forced_progress_gate → [plugin cross-verify + plugin gates] → (InteractionGate?).

        Phase 4 Plan 04-10 Task 3 (§04-CONTEXT D-10..D-13) extension:
        when ``self._plugin_manager`` is set, the chain ALSO includes:
          (a) CrossAgentVerificationGate instances from plugin_manager.get_verification_pairs()
              filtered to pair.phase == state.current_phase (Plan 04-05 Task 1 accessor).
          (b) Plugin-contributed gates from plugin_manager.get_plugin_gates(state.current_phase)
              (Plan 04-05 Task 2 accessor). This is how Phase 4's ShipApprovalGate
              (contributed by GstackSprintPlugin.contribute_gates in Plan 04-11)
              actually reaches production — previously unreachable per revision ISS-03.

        InteractionGate insertion (Phase 2 D-23 + force_interactive_phases) preserved
        verbatim and runs LAST in the chain.

        BC: when plugin_manager is None (legacy Phase 2 callers), the chain is
        identical to the Phase 2 three-gate composition. Phase 2 tests continue
        to pass without modification.
        """
        from clawteam.harness.evidence_gate import EvidenceGate
        from clawteam.harness.forced_progress_gate import forced_progress_gate
        from clawteam.harness.interaction_gate import InteractionGate

        chain: list = []
        chain.append(EvidenceGate(artifact_names=list(state.artifacts.keys())))
        chain.append(forced_progress_gate())

        # Phase 4 Plan 04-10 Task 3 — plugin contributions.
        if self._plugin_manager is not None:
            # Cross-agent verification gates (Plan 04-05 Task 1 accessor, Plan 04-03 gate).
            try:
                pairs = self._plugin_manager.get_verification_pairs() or []
            except Exception as exc:  # noqa: BLE001
                import logging as _lg
                _lg.getLogger(__name__).warning(
                    "plugin_manager.get_verification_pairs raised: %s", exc
                )
                pairs = []
            if pairs:
                from clawteam.harness.cross_agent_verification_gate import (
                    CrossAgentVerificationGate,
                )
                for pair, verifier in pairs:
                    if getattr(pair, "phase", None) != state.current_phase:
                        continue
                    try:
                        gate = CrossAgentVerificationGate(
                            phase=pair.phase,
                            source_artifact=pair.source_artifact,
                            target_artifact=pair.target_artifact,
                            verifier=verifier,
                        )
                        chain.append(gate)
                    except Exception as exc:  # noqa: BLE001
                        import logging as _lg
                        _lg.getLogger(__name__).warning(
                            "CrossAgentVerificationGate construction failed for %r: %s",
                            pair,
                            exc,
                        )

            # Plugin-contributed gates (Plan 04-05 Task 2 accessor).
            try:
                plugin_gates = self._plugin_manager.get_plugin_gates(state.current_phase) or []
            except Exception as exc:  # noqa: BLE001
                import logging as _lg
                _lg.getLogger(__name__).warning(
                    "plugin_manager.get_plugin_gates raised: %s", exc
                )
                plugin_gates = []
            chain.extend(plugin_gates)

        # InteractionGate (preserved verbatim from Phase 2 D-23 semantics).
        has_pending = bool(state.pending_question_ids)
        forced = state.current_phase in self.force_interactive_phases
        if forced or (not state.auto_advance) or has_pending:
            chain.append(InteractionGate())
        return chain
```

**Edit 2: `tests/test_review_phase_dispatch.py`** — APPEND these six tests (do NOT modify existing tests). The imports `_mock_subprocess`, `_CapturingBus`, `_FakePluginManager`, `_Router` from Task 1/2 are already at module scope; re-use them.

```python
# ── Plan 10 Task 3: _build_gate_chain plugin-gate wiring tests ────────

from clawteam.harness.phases import PhaseGate
from clawteam.sprint.state import SprintState


class _FakePluginMgrWithGates:
    """In-test plugin manager returning canned gate + verification-pair data."""

    def __init__(self, *, plugin_gates=None, verification_pairs=None, raise_gates=False, raise_pairs=False):
        self._plugin_gates = plugin_gates or {}
        self._verification_pairs = verification_pairs or []
        self._raise_gates = raise_gates
        self._raise_pairs = raise_pairs

    def get_plugin_gates(self, phase):
        if self._raise_gates:
            raise RuntimeError("plugin gates boom")
        return list(self._plugin_gates.get(phase, []))

    def get_verification_pairs(self):
        if self._raise_pairs:
            raise RuntimeError("verification pairs boom")
        return list(self._verification_pairs)


class _AlwaysPassGate(PhaseGate):
    name = "always-pass"

    def check(self, state):
        return True, ""


def _ship_state(tmp_path):
    return SprintState(
        team="t1",
        sprint_id="gc1234567",
        goal="g",
        current_phase="ship",
        workspace_branch=str(tmp_path),
    )


def _test_state(tmp_path):
    return SprintState(
        team="t1",
        sprint_id="gc7654321",
        goal="g",
        current_phase="test",
        workspace_branch=str(tmp_path),
    )


def test_build_gate_chain_includes_plugin_gates(tmp_path, monkeypatch):
    from clawteam.sprint.conductor import SprintConductor
    from clawteam.harness.ship_approval_gate import ShipApprovalGate

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    state = _ship_state(tmp_path)
    state.save(team="t1")

    pm = _FakePluginMgrWithGates(plugin_gates={"ship": [ShipApprovalGate()]})
    conductor = SprintConductor(team_name="t1", plugin_manager=pm)
    chain = conductor._build_gate_chain(state)
    assert any(isinstance(g, ShipApprovalGate) for g in chain), (
        f"ShipApprovalGate not in gate chain: {[type(g).__name__ for g in chain]}"
    )


def test_build_gate_chain_includes_cross_agent_verification_gates(tmp_path, monkeypatch):
    from clawteam.sprint.conductor import SprintConductor
    from clawteam.harness.cross_agent_verification_gate import (
        CrossAgentVerificationGate,
        VerificationPair,
    )

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    state = _test_state(tmp_path)
    state.save(team="t1")

    def dummy_verifier(src, tgt):
        return True, ""

    pair = VerificationPair(
        phase="test",
        source_artifact="test-report.md",
        target_artifact="build-report.md",
        verifier_dotted_path="irrelevant.for.this.test",
    )
    pm = _FakePluginMgrWithGates(verification_pairs=[(pair, dummy_verifier)])
    conductor = SprintConductor(team_name="t1", plugin_manager=pm)
    chain = conductor._build_gate_chain(state)
    cav_gates = [g for g in chain if isinstance(g, CrossAgentVerificationGate)]
    assert len(cav_gates) == 1, (
        f"Expected 1 CrossAgentVerificationGate in test phase, got {len(cav_gates)} "
        f"(chain={[type(g).__name__ for g in chain]})"
    )


def test_build_gate_chain_filters_verification_pairs_by_phase(tmp_path, monkeypatch):
    from clawteam.sprint.conductor import SprintConductor
    from clawteam.harness.cross_agent_verification_gate import (
        CrossAgentVerificationGate,
        VerificationPair,
    )

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    state = _test_state(tmp_path)  # phase="test"
    state.save(team="t1")

    def dummy(src, tgt):
        return True, ""

    # Pair targeted at review phase — must NOT appear in the test-phase chain.
    review_pair = VerificationPair(
        phase="review",
        source_artifact="design-doc.md",
        target_artifact="office-hours-answers.md",
        verifier_dotted_path="irrelevant",
    )
    pm = _FakePluginMgrWithGates(verification_pairs=[(review_pair, dummy)])
    conductor = SprintConductor(team_name="t1", plugin_manager=pm)
    chain = conductor._build_gate_chain(state)
    cav_gates = [g for g in chain if isinstance(g, CrossAgentVerificationGate)]
    assert cav_gates == [], (
        f"Review-phase pair leaked into test-phase chain: {cav_gates}"
    )


def test_build_gate_chain_ordering(tmp_path, monkeypatch):
    from clawteam.harness.cross_agent_verification_gate import (
        CrossAgentVerificationGate,
        VerificationPair,
    )
    from clawteam.harness.evidence_gate import EvidenceGate
    from clawteam.harness.interaction_gate import InteractionGate
    from clawteam.sprint.conductor import SprintConductor

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    state = _test_state(tmp_path)
    state.auto_advance = False  # force InteractionGate insertion
    state.save(team="t1")

    def dummy(src, tgt):
        return True, ""

    pair = VerificationPair(
        phase="test",
        source_artifact="a.md",
        target_artifact="b.md",
        verifier_dotted_path="irrelevant",
    )
    pm = _FakePluginMgrWithGates(
        verification_pairs=[(pair, dummy)],
        plugin_gates={"test": [_AlwaysPassGate()]},
    )
    conductor = SprintConductor(team_name="t1", plugin_manager=pm)
    chain = conductor._build_gate_chain(state)
    # Expected ordering: EvidenceGate first, CrossAgentVerificationGate middle,
    # plugin gate after, InteractionGate last.
    type_names = [type(g).__name__ for g in chain]
    assert type_names[0] == "EvidenceGate", f"EvidenceGate must be first: {type_names}"
    assert type_names[-1] == "InteractionGate", (
        f"InteractionGate must be last when forced: {type_names}"
    )
    # CrossAgentVerificationGate appears before plugin-contributed gate.
    cav_idx = next(i for i, n in enumerate(type_names) if n == "CrossAgentVerificationGate")
    plugin_idx = next(i for i, n in enumerate(type_names) if n == "_AlwaysPassGate")
    assert cav_idx < plugin_idx, (
        f"CrossAgentVerificationGate ({cav_idx}) must precede plugin gate ({plugin_idx}): {type_names}"
    )


def test_build_gate_chain_no_plugin_manager_backward_compatible(tmp_path, monkeypatch):
    """BC: SprintConductor without plugin_manager matches Phase 2 chain."""
    from clawteam.sprint.conductor import SprintConductor

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    state = _test_state(tmp_path)
    state.save(team="t1")

    conductor = SprintConductor(team_name="t1")  # no plugin_manager
    chain = conductor._build_gate_chain(state)
    # Phase 2 behaviour: EvidenceGate + forced_progress + maybe InteractionGate.
    type_names = [type(g).__name__ for g in chain]
    assert type_names[0] == "EvidenceGate"
    assert "CrossAgentVerificationGate" not in type_names
    # Phase 2 had 2 or 3 gates depending on auto_advance / pending questions.
    assert 2 <= len(chain) <= 3, f"BC chain size drift: {type_names}"


def test_build_gate_chain_plugin_manager_exception_safe(tmp_path, monkeypatch, caplog):
    """plugin_manager accessors raising should not crash gate-chain assembly."""
    from clawteam.sprint.conductor import SprintConductor

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    state = _test_state(tmp_path)
    state.save(team="t1")

    pm = _FakePluginMgrWithGates(raise_gates=True, raise_pairs=True)
    conductor = SprintConductor(team_name="t1", plugin_manager=pm)
    with caplog.at_level("WARNING"):
        chain = conductor._build_gate_chain(state)
    # Still have the two base gates (EvidenceGate + forced_progress_gate).
    type_names = [type(g).__name__ for g in chain]
    assert type_names[0] == "EvidenceGate"
    assert "forced_progress_gate" in type_names[1].lower() or type_names[1] != "EvidenceGate"
    # Both accessors raised — both warnings logged.
    msgs = " ".join(r.message for r in caplog.records)
    assert "get_plugin_gates raised" in msgs
    assert "get_verification_pairs raised" in msgs
```

**ISS-09 confirmation task:** Also add a 1-line acceptance test in this Task 3 block confirming that `save_sprint_state` module-level helper exists (it does — see `clawteam/sprint/state.py:159`). This test lives in the new code and fails loudly if a future refactor drops the helper:

```python
def test_save_sprint_state_helper_exists_iss09():
    """ISS-09: Plan 10 call sites use save_sprint_state(state). Helper must exist."""
    from clawteam.sprint.state import save_sprint_state
    assert callable(save_sprint_state)
```

Append this test to `tests/test_review_phase_dispatch.py` alongside the Task 3 tests.

**Do NOT modify** Phase 2 conductor tests; the BC test above confirms they keep passing.
  </action>
  <verify>
    <automated>pytest tests/test_review_phase_dispatch.py::test_build_gate_chain_includes_plugin_gates tests/test_review_phase_dispatch.py::test_build_gate_chain_includes_cross_agent_verification_gates tests/test_review_phase_dispatch.py::test_build_gate_chain_filters_verification_pairs_by_phase tests/test_review_phase_dispatch.py::test_build_gate_chain_ordering tests/test_review_phase_dispatch.py::test_build_gate_chain_no_plugin_manager_backward_compatible tests/test_review_phase_dispatch.py::test_build_gate_chain_plugin_manager_exception_safe tests/test_review_phase_dispatch.py::test_save_sprint_state_helper_exists_iss09 -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "plugin_manager=None" clawteam/sprint/conductor.py
    - grep -q "self._plugin_manager" clawteam/sprint/conductor.py
    - grep -q "get_plugin_gates" clawteam/sprint/conductor.py
    - grep -q "get_verification_pairs" clawteam/sprint/conductor.py
    - grep -q "CrossAgentVerificationGate" clawteam/sprint/conductor.py
    - grep -q "def save_sprint_state" clawteam/sprint/state.py  # ISS-09: helper exists
    - pytest tests/test_sprint_conductor.py -x -q stays green (Phase 2 BC — plugin_manager keyword has default None)
    - pytest tests/test_review_phase_dispatch.py -x -q exits 0 (all Task 1/2/3 tests + ISS-09 assertion)
    - wc -l clawteam/sprint/conductor.py stays under 700 (Task 3 adds ~40 LOC net)
  </acceptance_criteria>
  <done>Plugin-contributed gates + cross-agent verification gates reach the gate chain; ShipApprovalGate (Plan 11) and Phase 4 cross-verifiers are now production-reachable</done>
</task>
</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| subprocess.run(`git rev-parse`) ↔ workspace_branch | Workspace path is semi-trusted (from SprintState); shell=False neutralizes injection |
| Plugin-contributed routers ↔ match() | Router code is plugin-supplied |
| spawn_fn callable ↔ reviewer output | Stub default; Phase 5 integration replaces |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-31 | T (Tampering) | subprocess.run workspace | mitigate | shell=False + explicit cwd + 10s timeout; mirrors evidence_gate.py:85 pattern |
| T-04-32 | D (DoS) | asyncio.gather hangs on slow reviewer | mitigate | Semaphore caps from Phase 2 (max_tasks_per_agent) still apply via spawn_fn; future per-reviewer timeout is v1.x |
| T-04-33 | I (Information disclosure) | MidReviewThrash diff_paths_added/removed | accept | Paths are public git metadata |
| T-04-34 | E (Elevation of privilege) | Router raising masks participants | mitigate | try/except around each router; logged + skipped; floor "reviewer" guaranteed |
</threat_model>

<verification>
- [ ] `pytest tests/test_review_phase_dispatch.py -x -q` exits 0 (26 tests: 19 Task 1/2 + 7 Task 3)
- [ ] `pytest tests/test_sprint_conductor.py -x -q` stays green (BC — new plugin_manager kwarg defaults to None)
- [ ] `wc -l clawteam/sprint/conductor.py` < 700
- [ ] `grep -c "_dispatch_review_phase" clawteam/sprint/conductor.py` >= 1
- [ ] `grep -c "plugin_manager" clawteam/sprint/conductor.py` >= 3 (kwarg + storage + usage in _build_gate_chain)
- [ ] `grep -q "CrossAgentVerificationGate" clawteam/sprint/conductor.py` (Task 3 wiring)
- [ ] No existing Phase 1/2/3 tests regress
</verification>

<success_criteria>
- [ ] `dispatch_review_phase` async fn orchestrates parallel peers + sequential aggregator
- [ ] review_sha pinned at entry from `git rev-parse HEAD`
- [ ] MidReviewThrash emitted on HEAD advance post-gather
- [ ] SycophancyCascadeDetected emitted when agreement-rate > threshold
- [ ] SprintConductor._dispatch_review_phase thin wrapper exists
- [ ] 18+ review_phase tests + 1 conductor wrapper test + 7 Task 3 gate-chain tests pass (26+ total)
- [ ] Conductor stays under 700 LOC
- [ ] REVISION (Task 3): plugin_manager.get_plugin_gates + get_verification_pairs both consumed in _build_gate_chain
- [ ] REVISION (Task 3): ShipApprovalGate (Plan 11) and CrossAgentVerificationGate (Plan 03 + Plan 11) are now production-reachable (closes ISS-03 + ISS-07)
- [ ] ISS-09: save_sprint_state module-level helper asserted via new test
</success_criteria>

<output>
Create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-10-review-phase-dispatch-SUMMARY.md`.
</output>
