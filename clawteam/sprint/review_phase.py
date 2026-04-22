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
real agent-spawn path. See PLAN_PREP_NOTES A-spawn for the chosen bridge pattern
(``loop.run_in_executor(None, _spawn_reviewer_sync, ...)`` around the synchronous
``SpawnBackend.spawn(...)`` call when a real spawn hook is supplied).
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
    """Return ``git rev-parse HEAD`` for ``workspace`` or empty string on any error.

    Mirrors clawteam.harness.evidence_gate._default_subprocess_runner: shell=False,
    explicit cwd, 10s timeout, no shell interpretation. T-04-31 mitigation.
    """
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
    """Return the list of paths changed between ``base_sha`` and ``head_sha``.

    Empty list on any error (T-04-31 shell=False mitigation — same as _current_head).
    """
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
    is expected to be a dict with ``findings: list[{severity: str}]``. Non-
    dict reports (exceptions from ``return_exceptions=True``) contribute 0
    — they are skipped rather than dragging the denominator down, so a
    single spawn failure does not mask a real sycophancy cascade across
    the surviving reviewers.
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
    # WR-04-01 (04-REVIEW): a sycophancy cascade requires AGREEMENT between
    # reviewers — by definition you cannot have a cascade with a single peer
    # because there is nothing to agree against. Before this guard, a solo
    # peer with any findings yielded rate=1.0 and spammed
    # SycophancyCascadeDetected on every dispatch.
    if len(rated) < 2:
        return 0.0
    max_len = max(len(s) for s in rated)
    if max_len == 0:
        return 0.0
    # Count positions where all surviving peers share identical severity.
    matched = 0
    for i in range(max_len):
        values: list[str] = []
        for s in rated:
            if i < len(s):
                values.append(s[i])
        if len(values) == len(rated) and len(set(values)) == 1:
            matched += 1
    return matched / max_len


# ── Default spawn (stub — Phase 5 replaces with real spawn bridge) ───


async def _default_spawn_fn(
    role: str,
    state: SprintState,
    review_sha: str,
    peer_reports: list[Any] | None = None,
) -> dict:
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

    # 2. Try phase_registry.review_routers() via global.
    try:
        from clawteam.harness.phase_registry import get_registry
        reg = get_registry()
        accessor = getattr(reg, "review_routers", None) or getattr(reg, "get_review_routers", None)
        if callable(accessor):
            routers.extend(accessor() or [])
    except Exception:  # noqa: BLE001
        pass

    return routers


__all__ = [
    "dispatch_review_phase",
    "_compute_agreement_rate",
    "_current_head",
    "_diff_paths",
    "_default_spawn_fn",
]
