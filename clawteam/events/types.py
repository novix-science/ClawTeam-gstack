"""Event types for the ClawTeam event bus."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class HarnessEvent:
    """Base class for all harness events."""

    team_name: str = ""
    timestamp: str = field(default_factory=_now_iso)


# ── Worker lifecycle ──────────────────────────────────────────────────


@dataclass
class BeforeWorkerSpawn(HarnessEvent):
    """Fired before a worker agent is spawned. Set veto=True to cancel."""

    agent_name: str = ""
    agent_type: str = ""
    command: list[str] = field(default_factory=list)
    veto: bool = False


@dataclass
class AfterWorkerSpawn(HarnessEvent):
    """Fired after a worker agent has been successfully spawned."""

    agent_name: str = ""
    agent_id: str = ""
    backend: str = ""
    target: str = ""  # e.g. tmux target


@dataclass
class WorkerExit(HarnessEvent):
    """Fired when a worker process exits normally."""

    agent_name: str = ""
    exit_code: int | None = None
    abandoned_tasks: list[str] = field(default_factory=list)


@dataclass
class WorkerCrash(HarnessEvent):
    """Fired when a worker process crashes (SIGKILL, OOM, etc.)."""

    agent_name: str = ""
    error: str = ""


# ── Task lifecycle ────────────────────────────────────────────────────


@dataclass
class BeforeTaskCreate(HarnessEvent):
    """Fired before a task is created."""

    subject: str = ""
    owner: str = ""


@dataclass
class AfterTaskUpdate(HarnessEvent):
    """Fired after a task status changes."""

    task_id: str = ""
    old_status: str = ""
    new_status: str = ""
    owner: str = ""


@dataclass
class TaskCompleted(HarnessEvent):
    """Fired when a task transitions to completed."""

    task_id: str = ""
    owner: str = ""
    duration_seconds: float = 0.0


# ── Messaging ─────────────────────────────────────────────────────────


@dataclass
class BeforeInboxSend(HarnessEvent):
    """Fired before a message is sent."""

    from_agent: str = ""
    to: str = ""
    msg_type: str = ""


@dataclass
class AfterInboxReceive(HarnessEvent):
    """Fired after messages are consumed from an inbox."""

    agent_name: str = ""
    count: int = 0


# ── Workspace ─────────────────────────────────────────────────────────


@dataclass
class BeforeWorkspaceMerge(HarnessEvent):
    """Fired before a workspace merge."""

    agent_name: str = ""
    branch: str = ""


@dataclass
class AfterWorkspaceCleanup(HarnessEvent):
    """Fired after a workspace is cleaned up."""

    agent_name: str = ""


# ── Team lifecycle ────────────────────────────────────────────────────


@dataclass
class TeamLaunch(HarnessEvent):
    """Fired when a team is launched from a template."""

    template: str = ""
    agent_count: int = 0


@dataclass
class TeamShutdown(HarnessEvent):
    """Fired when a team is shut down and cleaned up."""

    pass


# ── Health ────────────────────────────────────────────────────────────


@dataclass
class AgentIdle(HarnessEvent):
    """Fired when an agent reports idle status."""

    agent_name: str = ""
    last_task: str = ""


@dataclass
class HeartbeatTimeout(HarnessEvent):
    """Fired when an agent's heartbeat times out."""

    agent_name: str = ""
    last_seen: str = ""


# ── Harness phases ────────────────────────────────────────────────────


@dataclass
class PhaseTransition(HarnessEvent):
    """Fired when the harness transitions between phases."""

    from_phase: str = ""
    to_phase: str = ""
    artifacts: list[str] = field(default_factory=list)


# ── Transport / Board ─────────────────────────────────────────────────


@dataclass
class TransportFallback(HarnessEvent):
    """Fired when a transport falls back to a secondary mechanism."""

    transport: str = ""
    fallback: str = ""
    reason: str = ""


@dataclass
class BoardAttach(HarnessEvent):
    """Fired when a user attaches to the board."""

    pass


# ── Phase 2: Safety-rail Before* events (veto-shape; §02-CONTEXT D-10) ─────────


@dataclass
class BeforeToolCall(HarnessEvent):
    """Fired before an MCP tool or intercepted CLI command runs. Set veto=True to cancel."""

    agent_name: str = ""
    tool_name: str = ""
    args: dict = field(default_factory=dict)
    veto: bool = False
    veto_reason: str = ""


@dataclass
class BeforeFileWrite(HarnessEvent):
    """Fired before ArtifactStore.write or WorkspaceManager git-write. Set veto=True to cancel."""

    agent_name: str = ""
    path: str = ""
    size_bytes: int = 0
    veto: bool = False
    veto_reason: str = ""


# ── Phase 2: Freeze audit + envelope + theater + cycle + cap notifications ────


@dataclass
class FreezeChange(HarnessEvent):
    """Emitted on every /freeze, /unfreeze, /guard action (§02-CONTEXT D-13)."""

    action: str = ""  # "freeze" | "unfreeze"
    path: str = ""
    agent: str = ""
    reason: str = ""
    actor: str = ""


@dataclass
class MalformedEnvelope(HarnessEvent):
    """Emitted on first malformed TurnEnvelope per agent (§02-CONTEXT D-09 warn-mode)."""

    agent: str = ""
    violation: str = ""
    turn_id: str = ""


@dataclass
class DriftRegression(HarnessEvent):
    """Emitted after 8+ consecutive malformed envelopes per agent (§02-CONTEXT D-09)."""

    agent: str = ""
    consecutive_count: int = 0
    last_violation: str = ""


@dataclass
class CycleDetected(HarnessEvent):
    """Transport cycle detected via DefaultRoutingPolicy (§02-CONTEXT D-21)."""

    pair: tuple = ("", "")
    topic_hash: str = ""
    route_keys: list = field(default_factory=list)
    window_size: int = 20


@dataclass
class ForcedProgressTriggered(HarnessEvent):
    """Theater/no-progress gate fired (§02-CONTEXT D-17)."""

    agent: str = ""
    consecutive_no_progress: int = 0
    question_id: str = ""


@dataclass
class ArtifactCapExceeded(HarnessEvent):
    """Per-file or per-phase artifact cap hit (§02-CONTEXT D-27, D-28)."""

    artifact_name: str = ""
    size_bytes: int = 0
    cap_bytes: int = 0
    scope: str = ""  # "file" or "phase"


# ── Phase 4: Review-phase events (§04-CONTEXT D-09 / D-19 / D-20) ──────


@dataclass
class MidReviewThrash(HarnessEvent):
    """Emitted when sprint branch HEAD advances during an in-flight Review phase.

    §04-CONTEXT D-19 / Pitfall 9. Reviewers consume this event in their next
    turn to choose between re-pinning (extending review to ``new_sha``) or
    marking the prior review ``superseded``. Payload gives reviewers the
    diff-delta info they need to decide without shelling out to git.

    Emitted by ``dispatch_review_phase`` (Plan 10) at post-turn boundaries
    when ``git rev-parse HEAD != state.review_sha``.
    """

    sprint_id: str = ""
    review_sha: str = ""
    new_sha: str = ""
    reviewer_roles_active: list[str] = field(default_factory=list)
    diff_paths_added: list[str] = field(default_factory=list)
    diff_paths_removed: list[str] = field(default_factory=list)


@dataclass
class SycophancyCascadeDetected(HarnessEvent):
    """Emitted when parallel-reviewer agreement-rate crosses sycophancy_threshold.

    §04-CONTEXT D-09 / D-20 / Pitfall 13. Advisory only — does NOT block
    phase advance. ``review_round`` is scoped to a single Review-phase
    dispatch; re-running Review after gap closure opens a new window (D-20).

    Phase 7's ``clawteam attend --summary`` surfaces this event in the
    cross-sprint digest; Phase 4 only emits + logs.
    """

    sprint_id: str = ""
    review_round: int = 0
    agreement_rate: float = 0.0
    threshold: float = 0.9
    reviewer_roles: list[str] = field(default_factory=list)


# ── Phase 5 / Plan 05-02: canary + benchmark regression events ────────


@dataclass
class DeployRegressionDetected(HarnessEvent):
    """Canary observed a regression vs pre-deploy baseline (D-14, SKILL-17).

    Emitted by ``/canary`` handler (Plan 05-08) when any of:
      - 5xx rate > 1%
      - avg response time > 2 * ``pre_deploy_avg_response_ms``
      - any JS console error observed (browser mode)

    Advisory-only in Phase 5; Phase 7's ``clawteam attend --summary``
    surfaces the event in the cross-sprint digest so SRE can see rollback
    candidates without poking at each sprint directory.
    """

    sprint_id: str = ""
    deploy_url: str = ""
    regression_flags: list[str] = field(default_factory=list)
    http_2xx_count: int = 0
    http_5xx_count: int = 0
    avg_response_ms: float = 0.0
    pre_deploy_avg_response_ms: float = 0.0


@dataclass
class WebVitalRegressionDetected(HarnessEvent):
    """A Core Web Vital exceeded 1.5x pre-deploy baseline (D-14, SKILL-18).

    Emitted by ``/benchmark`` handler (Plan 05-09). ``vital`` is one of:
    ``"lcp"``, ``"fid"``, ``"cls"``, ``"ttfb"``, ``"dom_loaded"``.

    Advisory-only; mirrors :class:`DeployRegressionDetected` shape so
    Phase 7 aggregator can treat the two regression events uniformly.
    """

    sprint_id: str = ""
    deploy_url: str = ""
    vital: str = ""
    baseline_value: float = 0.0
    observed_value: float = 0.0
    ratio: float = 0.0


# ── Phase 6 Wave 0 / Plan 06-01: team memory substrate events ─────────


@dataclass
class MemoryWritePersisted(HarnessEvent):
    """A new MemoryEntry was appended to JSONL (D-04, MEM-02).

    Advisory — emitted on every committed write (both direct writes and
    promotions from ``memory/<scope>/pending/``). Phase 7 cost dashboard
    aggregates ``high_impact=True`` counts; Phase 6 only emits + logs.
    """

    entry_id: str = ""
    scope: str = ""  # "team" or "role"
    role: str = ""
    tags: list[str] = field(default_factory=list)
    high_impact: bool = False


@dataclass
class ConflictDetected(HarnessEvent):
    """Two entries contradict on same tag (D-10).

    Advisory-only — the write is NOT blocked (D-10 explicit). Emitted by
    ``TeamMemoryStore.write`` when the new entry's body cosine-similarity
    against an existing entry's body exceeds ``gstack.toml [memory]
    conflict_threshold`` (default 0.75) AND sentiment-opposition fires.
    """

    new_entry_id: str = ""
    conflicting_entry_id: str = ""
    similarity: float = 0.0
    shared_tags: list[str] = field(default_factory=list)
    scope: str = ""


@dataclass
class MemoryBackfillComplete(HarnessEvent):
    """Backfill scanner finished promoting _phase6_pending/ entries (D-11).

    First ``/learn`` invocation per team runs ``backfill_scan(team)``; this
    event fires once at end of scan with counts populated. Idempotent:
    re-runs fire with ``entries_promoted=0,
    entries_skipped_already_processed=<previous>``.
    """

    team: str = ""
    entries_promoted: int = 0
    entries_skipped_already_processed: int = 0


# Late import to avoid the clawteam.events.bus <-> clawteam.events.types
# circular dependency: bus.py imports HarnessEvent from this module at top
# level, so we MUST not import from bus.py until after HarnessEvent is
# defined. Placing this at the bottom keeps the module-load order safe.
from clawteam.events.bus import register_event_type  # noqa: E402

register_event_type(DeployRegressionDetected)
register_event_type(WebVitalRegressionDetected)
# Phase 6 Wave 0 / Plan 06-01
register_event_type(MemoryWritePersisted)
register_event_type(ConflictDetected)
register_event_type(MemoryBackfillComplete)
