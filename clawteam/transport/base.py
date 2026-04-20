"""Abstract base class for message transport + Phase 2 envelope validation hook."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable
from threading import Lock
from typing import Any

from clawteam.team.envelope import MalformedEnvelopeError, TurnEnvelope
from clawteam.team.models import TeamMessage

# ── Phase 2: per-agent consecutive-malformed counter (§02-CONTEXT D-09) ──────────
#
# Module-level state so counters survive across transient Transport instances
# within one sprint runtime (file.py / p2p.py construct a fresh instance per
# operation in some paths). Cleared on sprint teardown by SprintConductor
# (Plan 02-11) via :func:`_reset_drift_counters`.
#
# Scoping contract (Rule 2 trust-boundary hardening, Plan 02-08 SUMMARY):
#   - Counter is keyed on TeamMessage.from_agent
#   - Threshold = 8 consecutive malformed envelopes -> emit DriftRegression
#   - Any valid envelope resets the per-agent counter to 0
_MALFORMED_COUNTERS: dict[str, int] = {}
_COUNTER_LOCK = Lock()
_DRIFT_THRESHOLD = 8  # §02-CONTEXT D-09

# ── Phase 2 Plan 02-09: turn-counter hook slot (§02-CONTEXT D-14) ────────────────
#
# Module-level callback slot so :func:`_pre_deliver_hooks` can notify
# SprintState.turn_counters on every successful envelope validation. The slot
# is set by :class:`SprintConductor` (Plan 02-11) on sprint start via
# :func:`set_turn_counter_callback` and cleared on sprint teardown. When unset,
# the deliver path is turn-counter-free (BC preserved for non-sprint traffic).
#
# Pitfall #2 dedup: the callback is expected to dedupe by ``(agent, turn_id)``
# so the same turn_id reaching both deliver + ArtifactStore.write counts once.
_TURN_COUNTER_CALLBACK: Callable[[str, str], None] | None = None


def set_turn_counter_callback(cb: Callable[[str, str], None] | None) -> None:
    """Install or clear the turn-counter callback. SprintConductor calls this on
    sprint start/stop so counters reset across sprint boundaries.
    """
    global _TURN_COUNTER_CALLBACK
    _TURN_COUNTER_CALLBACK = cb


def get_turn_counter_callback() -> Callable[[str, str], None] | None:
    """Test helper — inspect the currently-installed callback."""
    return _TURN_COUNTER_CALLBACK


def _pre_deliver_hooks(data: bytes | str) -> TeamMessage:
    """Phase 2 pre-deliver envelope validation + per-agent drift accounting.

    Called at the top of every concrete ``Transport.deliver`` override that carries
    TeamMessage JSON payloads (file.py, p2p.py). Returns the hydrated
    :class:`TeamMessage` on success so callers can reuse it without re-parsing.

    Pitfall #8 BC invariant: messages carrying NONE of persona/step_label/done
    pass through **without** envelope validation. Only messages carrying AT LEAST
    ONE of the three envelope fields are required to carry ALL THREE (valid
    envelope). This preserves the existing software-dev / hedge-fund / code-review
    / harness-default / research-paper / strategy-room templates while enforcing
    the envelope for gstack-sprint agent turns that opt in via their role prompt.

    On partial envelope:
      - increment per-agent counter
      - emit ``MalformedEnvelope`` (sync) so subscribers can surface it
      - on 8+ consecutive strikes emit ``DriftRegression`` (sync, additive)
      - raise :class:`MalformedEnvelopeError` (callers must stop delivery)

    Do NOT call :meth:`Transport.deliver` or :meth:`ArtifactStore.write` from a
    MalformedEnvelope / DriftRegression handler — that would recurse through this
    same hook. Event subscribers are expected to be observation-only per
    Pitfall #1.
    """
    raw = data.decode("utf-8") if isinstance(data, bytes) else data
    try:
        payload: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MalformedEnvelopeError(f"envelope invalid: json parse: {exc}") from exc

    try:
        msg = TeamMessage.model_validate(payload)
    except Exception as exc:
        # Any TeamMessage validation failure is surfaced as Malformed so callers
        # can route consistently. (The existing mailbox system already has its
        # own dead-letter path for broken payloads; this path only applies when
        # the bytes parse to JSON but fail model validation.)
        raise MalformedEnvelopeError(f"envelope invalid: model_validate: {exc}") from exc

    persona = msg.persona
    step_label = msg.step_label
    done = msg.done
    any_envelope = (
        persona is not None or step_label is not None or done is not None
    )
    if not any_envelope:
        # BC pass-through (Pitfall #8): existing template mailbox traffic.
        return msg

    agent = msg.from_agent or ""
    try:
        TurnEnvelope.model_validate(
            {
                "persona": persona or "",
                "step_label": step_label or "",
                "done": done if done is not None else None,
            }
        )
    except Exception as exc:
        # Increment BEFORE emitting so the MalformedEnvelope handler can inspect
        # the post-strike counter via shared module state if it wants to.
        with _COUNTER_LOCK:
            count = _MALFORMED_COUNTERS.get(agent, 0) + 1
            _MALFORMED_COUNTERS[agent] = count

        # Sync emit — Pitfall #7. Wrap in try/except so a bus-handler crash does
        # not mask the underlying envelope error; subscribers must not crash the
        # bus but we defensively swallow here too.
        try:
            from clawteam.events.global_bus import get_event_bus
            from clawteam.events.types import DriftRegression, MalformedEnvelope

            get_event_bus().emit(
                MalformedEnvelope(
                    agent=agent,
                    violation=str(exc),
                    turn_id=msg.request_id or "",
                )
            )
            if count >= _DRIFT_THRESHOLD:
                get_event_bus().emit(
                    DriftRegression(
                        agent=agent,
                        consecutive_count=count,
                        last_violation=str(exc),
                    )
                )
        except Exception:
            pass

        # Wrap non-MalformedEnvelopeError (e.g. pydantic ValidationError from
        # TurnEnvelope.model_validate) into MalformedEnvelopeError for the
        # consistent contract D-08 promises.
        if isinstance(exc, MalformedEnvelopeError):
            raise
        raise MalformedEnvelopeError(f"envelope invalid: {exc}") from exc

    # Valid envelope -> reset per-agent counter (§02-CONTEXT D-09 "counter resets
    # on success").
    with _COUNTER_LOCK:
        _MALFORMED_COUNTERS.pop(agent, None)

    # ── Plan 02-09 Hook: turn-counter increment on success (§02-CONTEXT D-14) ──
    # Invoked only for agent-authored turns (any_envelope == True here — we
    # already branched out for BC pass-through above). Turn-id dedup is the
    # callback's responsibility; we hand over best-effort (agent, turn_id)
    # extracted from the validated envelope fields.
    if _TURN_COUNTER_CALLBACK is not None and agent:
        turn_id = ""
        # TurnEnvelope.turn_id is optional; extract directly from the validated
        # payload dict when present. Fall back to TeamMessage.request_id (Plan
        # 02-08 round-trip dedupe anchor) when the envelope omits turn_id.
        if isinstance(payload, dict):
            turn_id = str(payload.get("turn_id") or payload.get("turnId") or "")
        if not turn_id:
            turn_id = str(getattr(msg, "request_id", "") or "")
        try:
            _TURN_COUNTER_CALLBACK(agent, turn_id)
        except Exception:
            # Observation-only hook — never propagate callback errors.
            pass
    return msg


def _reset_drift_counters() -> None:
    """Test + SprintConductor-teardown helper: clear the per-agent malformed counter.

    SprintConductor (Plan 02-11) calls this on sprint start/resume so a previous
    sprint's drift state does not leak across sprint boundaries. Also clears
    the Plan 02-09 turn-counter callback so a subsequent test / sprint does
    NOT observe a stale hook.
    """
    global _TURN_COUNTER_CALLBACK
    with _COUNTER_LOCK:
        _MALFORMED_COUNTERS.clear()
    _TURN_COUNTER_CALLBACK = None


class Transport(ABC):
    """Transport interface for delivering and fetching raw message bytes."""

    @abstractmethod
    def deliver(self, recipient: str, data: bytes) -> None:
        """Deliver message bytes to a recipient's inbox."""

    @abstractmethod
    def fetch(self, agent_name: str, limit: int = 10, consume: bool = True) -> list[bytes]:
        """Fetch opaque message bytes from a transport-specific inbox.

        Transports only move raw bytes. Higher-level callers such as
        ``MailboxManager.receive()`` are responsible for parsing those bytes
        into ``TeamMessage`` objects and deciding whether malformed payloads
        should be quarantined.
        """

    @abstractmethod
    def count(self, agent_name: str) -> int:
        """Return the number of pending messages."""

    @abstractmethod
    def list_recipients(self) -> list[str]:
        """List all known recipient names (for broadcast)."""

    def close(self) -> None:
        """Release resources. Default is no-op."""
