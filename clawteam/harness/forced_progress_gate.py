"""forced_progress_gate — theater / no-progress detector (§02-CONTEXT D-14..D-17).

Composed into PhaseRunner._gates[phase] AFTER EvidenceGate, BEFORE InteractionGate
per §02-CONTEXT Integration Points. Reads SprintState.turn_counters and per-agent
artifact-bytes delta to detect agents emitting zero-progress turns.

Core invariants:

- D-14 (turn definition): one successful ``transport.deliver()`` OR one successful
  ``ArtifactStore.write()`` = one turn. Pitfall #2 dedup: a ``turn_id`` identifies
  the agent-authored turn across channels; counter increments only on first sighting
  of a new ``(agent, turn_id)`` pair.

- D-15 (progress definition): net-positive per-agent artifact-bytes delta since the
  previous snapshot OR a ``TaskCompleted`` event fired during the turn. Mailbox
  messages alone don't count.

- D-16 + Pitfall #16 (per-agent, not sprint-wide): specialists waiting for engineer
  are NOT theater. Counters, progress tracking, and triggers are strictly per-agent.
  One agent's artifact write NEVER resets another agent's no-progress counter.
  There is NO sprint-wide byte-summation path in this module — progress is computed
  per author-agent only.

- D-17 (escalation): 2 consecutive no-progress turns per agent → gate writes a
  multi-choice question at ``questions/<q_id>.md`` with choices
  ``A: keep waiting``, ``B: restart agent``, ``C: abort sprint``; emits
  ``ForcedProgressTriggered``; returns ``(False, reason)``.

Per-agent attribution sources from the per-artifact ``.meta.json`` sidecar written
by Plan 02-06 Task 2 — each entry records ``metadata["agent"]`` so the gate can sum
bytes STRICTLY per author-agent. Artifacts lacking an author-agent are ignored for
progress attribution.
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from clawteam.events.global_bus import get_event_bus
from clawteam.events.types import ForcedProgressTriggered, TaskCompleted
from clawteam.harness.phases import PhaseGate
from clawteam.sprint.qa import Choice, Question
from clawteam.team.models import get_data_dir

NO_PROGRESS_THRESHOLD = 2  # §02-CONTEXT D-16

# ── Module-level turn-id dedupe (Pitfall #2) ───────────────────────────────────
# Keyed by agent — each agent tracks the set of turn_ids already counted. Shared
# across the two hook sites (ArtifactStore.write + _pre_deliver_hooks) so the
# same turn_id reaching both sites counts ONCE. SprintConductor (Plan 02-11)
# clears this on sprint teardown via :func:`reset_turn_counter_state`.
_seen_turn_ids: dict[str, set[str]] = defaultdict(set)


def increment_turn_counter(state: Any, agent: str, turn_id: str = "") -> None:
    """Dedupe + increment ``state.turn_counters[agent]`` for a new turn.

    Pitfall #2: a turn is identified by ``(agent, turn_id)``. The same turn_id
    reaching both the ArtifactStore.write hook and the Transport.deliver hook
    counts exactly once. An empty ``turn_id`` is treated as "no dedupe available"
    and always increments — callers without an envelope-bearing turn_id are rare
    (non-gstack templates) and should never be asserted by the theater detector.
    """
    if not agent:
        return
    if turn_id and turn_id in _seen_turn_ids[agent]:
        return
    if turn_id:
        _seen_turn_ids[agent].add(turn_id)
    current = state.turn_counters.get(agent, 0)
    state.turn_counters[agent] = current + 1


def reset_turn_counter_state() -> None:
    """Clear the per-agent seen-turn-id map. Test helper + SprintConductor teardown."""
    _seen_turn_ids.clear()


class forced_progress_gate(PhaseGate):  # noqa: N801 — matches §02-CONTEXT D-17 spelling
    """Detect 2+ consecutive no-progress turns per agent; write a multi-choice question.

    The gate is stateful across calls within one sprint run: ``_last_progress_snapshot``
    remembers each agent's turn-counter value at the last observed progress event;
    ``_last_artifact_sizes`` caches per-agent bytes-seen for delta computation;
    ``_triggered_agents`` tracks which agents already have an outstanding question
    so the gate does not write duplicate questions on repeated checks.
    """

    def __init__(self) -> None:
        self._last_progress_snapshot: dict[str, int] = {}
        self._last_artifact_sizes: dict[str, int] = {}
        self._triggered_agents: set[str] = set()
        self._task_completed_agents: set[str] = set()

    def register(self) -> None:
        """Subscribe to TaskCompleted so we can reset counters on task completion."""
        get_event_bus().subscribe(TaskCompleted, self._on_task_completed)

    def _on_task_completed(self, event: TaskCompleted) -> None:
        owner = getattr(event, "owner", "") or ""
        if owner:
            self._task_completed_agents.add(owner)

    def check(self, state: Any) -> tuple[bool, str]:
        """Run the theater detector against ``state.turn_counters``.

        Returns ``(True, "")`` when no agent has crossed the 2-turn threshold
        (or when progress was observed for any would-be triggered agent).
        Returns ``(False, reason)`` on trigger; writes a multi-choice question
        file and emits ``ForcedProgressTriggered`` for the first triggered agent.
        """
        turn_counters = getattr(state, "turn_counters", None)
        if turn_counters is None:
            return True, ""

        # D-16 + Pitfall #16: STRICT per-agent attribution — no sprint-wide summation.
        per_agent_bytes = _compute_per_agent_artifact_bytes(state)

        triggered: list[str] = []
        for agent, counter in list(turn_counters.items()):
            last_snapshot = self._last_progress_snapshot.get(agent, 0)
            no_progress_turns = counter - last_snapshot

            # TaskCompleted reset — own-agent only (event.owner matched at subscribe).
            if agent in self._task_completed_agents:
                self._last_progress_snapshot[agent] = counter
                self._task_completed_agents.discard(agent)
                continue

            # Per-agent artifact-bytes delta — strictly this agent's writes. Another
            # agent's write does NOT count here (D-16 + Pitfall #16 invariant).
            this_agent_bytes = per_agent_bytes.get(agent, 0)
            last_bytes = self._last_artifact_sizes.get(agent, 0)
            if this_agent_bytes > last_bytes:
                self._last_progress_snapshot[agent] = counter
                self._last_artifact_sizes[agent] = this_agent_bytes
                continue

            if (
                no_progress_turns >= NO_PROGRESS_THRESHOLD
                and agent not in self._triggered_agents
            ):
                triggered.append(agent)

        if not triggered:
            return True, ""

        # Write a question for the FIRST triggered agent. Subsequent triggers
        # queue via repeat check() calls once the current question is answered.
        agent = triggered[0]
        question_id = self._write_question(state, agent)
        self._triggered_agents.add(agent)
        consecutive = turn_counters[agent] - self._last_progress_snapshot.get(agent, 0)
        try:
            get_event_bus().emit(
                ForcedProgressTriggered(
                    team_name=getattr(state, "team", ""),
                    agent=agent,
                    consecutive_no_progress=consecutive,
                    question_id=question_id,
                )
            )
        except Exception:
            pass
        return False, (
            f"forced_progress_gate triggered: agent {agent!r} has 2 consecutive "
            f"no-progress turns; question {question_id} written "
            f"(answer lifts suppression)."
        )

    def _write_question(self, state: Any, agent: str) -> str:
        team = getattr(state, "team", "") or ""
        sprint_id = getattr(state, "sprint_id", "") or ""
        phase = getattr(state, "current_phase", "") or ""
        sprint_dir = get_data_dir() / "teams" / team / "sprints" / sprint_id
        questions_dir = sprint_dir / "questions"
        questions_dir.mkdir(parents=True, exist_ok=True)

        q_id = uuid.uuid4().hex[:8]
        body = (
            f"Agent `{agent}` has produced 2 consecutive no-progress turns "
            f"in phase `{phase}`. Net artifact bytes: no delta.\n\n"
            f"Pick an action:\n"
        )
        question = Question(
            id=q_id,
            slug=f"forced-progress-{agent}",
            type="multi-choice",
            created_at=datetime.now(timezone.utc).isoformat(),
            sprint_id=sprint_id,
            phase=phase,
            author="forced_progress_gate",
            choices=[
                Choice(id="A", label="keep waiting — agent will ship next turn"),
                Choice(id="B", label="restart agent from clean state"),
                Choice(id="C", label="abort sprint"),
            ],
            body=body,
        )
        (questions_dir / f"{q_id}.md").write_text(
            question.to_markdown(),
            encoding="utf-8",
        )
        return q_id

    def clear_agent_trigger(self, agent: str) -> None:
        """Plan 02-11 Conductor hook: clear the per-agent trigger once a matching
        answer arrives. The counter snapshot refreshes on the next progress event.
        """
        self._triggered_agents.discard(agent)


def _compute_per_agent_artifact_bytes(state: Any) -> dict[str, int]:
    """Scan ``<sprint_dir>/artifacts/*.meta.json`` and sum bytes per author-agent.

    D-16 + Pitfall #16 invariant: no sprint-wide summation path — each artifact
    counts ONLY toward the agent whose ``metadata["agent"]`` is recorded on its
    sibling ``.meta.json`` (written by Plan 02-06 Task 2). Artifacts without an
    author-agent recorded are ignored for progress attribution. This preserves
    per-agent isolation: one agent's write never clears another agent's
    no-progress counter.
    """
    per_agent: defaultdict[str, int] = defaultdict(int)
    team = getattr(state, "team", "") or ""
    sprint_id = getattr(state, "sprint_id", "") or ""
    if not team or not sprint_id:
        return dict(per_agent)

    try:
        sprint_dir = get_data_dir() / "teams" / team / "sprints" / sprint_id
    except Exception:
        return dict(per_agent)

    artifacts_dir = sprint_dir / "artifacts"
    if not artifacts_dir.exists():
        return dict(per_agent)

    for meta_path in artifacts_dir.glob("*.meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        agent = str(meta.get("agent") or "")
        # Prefer recorded size_bytes; fall back to the artifact file's size on disk.
        size = int(meta.get("size_bytes") or 0)
        if size <= 0:
            artifact_name = meta_path.name[: -len(".meta.json")]
            artifact_path = artifacts_dir / artifact_name
            if artifact_path.is_file():
                try:
                    size = artifact_path.stat().st_size
                except OSError:
                    size = 0
        if not agent or size <= 0:
            continue
        per_agent[agent] += size

    return dict(per_agent)


# ── Plan 02-08 integration: routing-policy progress-signal populator seam ──────
# Plan 02-08 reserved a ``progressSignal`` key on ``recentEvents`` entries for
# Pitfall #3 mitigation. Callers (Plan 02-11 Conductor or the theater detector
# itself on TaskCompleted) flip this flag via ``DefaultRoutingPolicy._append_event``.
# The heavy lifting now lives in Plan 02-09's routing_policy change: the
# ``_append_event`` helper accepts ``progress_signal: bool = False`` and writes
# it onto the entry so ``_detect_cycle`` reads a populated key.
