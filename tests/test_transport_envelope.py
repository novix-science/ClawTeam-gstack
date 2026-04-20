"""RED-phase tests for Transport.deliver envelope-validation hook (Plan 02-08).

Exercises §02-CONTEXT D-08/D-09 + Pitfall #8 BC invariant:

  1. `_pre_deliver_hooks(data: bytes) -> TeamMessage` parses a JSON team-message
     payload and returns the hydrated TeamMessage.
  2. BC pass-through: messages carrying NONE of persona/step_label/done are delivered
     unchanged (existing template mailbox traffic unaffected).
  3. Partial envelope (any of the three fields present but not all) raises
     MalformedEnvelopeError.
  4. Full valid envelope is accepted without raising.
  5. 8 consecutive malformed envelopes from the same agent emit DriftRegression on the
     8th strike; a valid envelope in between resets the per-agent counter.
"""

from __future__ import annotations

import json

import pytest

from clawteam.events.global_bus import get_event_bus, reset_event_bus
from clawteam.events.types import DriftRegression, MalformedEnvelope
from clawteam.team.envelope import MalformedEnvelopeError
from clawteam.team.models import TeamMessage
from clawteam.transport.base import _pre_deliver_hooks, _reset_drift_counters


@pytest.fixture(autouse=True)
def _reset_state():
    reset_event_bus()
    _reset_drift_counters()
    yield
    reset_event_bus()
    _reset_drift_counters()


def _encode(msg_dict: dict) -> bytes:
    return json.dumps(msg_dict).encode("utf-8")


def _base_message(**overrides) -> dict:
    """Minimum valid TeamMessage JSON dict, with envelope fields omitted by default."""
    payload = {
        "type": "message",
        "from": "engineer",
        "to": "reviewer",
        "content": "hello",
    }
    payload.update(overrides)
    return payload


def test_pre_deliver_hooks_parses_bytes_to_team_message():
    """Plain JSON bytes -> TeamMessage via pydantic.model_validate."""
    data = _encode(_base_message())
    msg = _pre_deliver_hooks(data)
    assert isinstance(msg, TeamMessage)
    assert msg.from_agent == "engineer"
    assert msg.to == "reviewer"
    assert msg.content == "hello"


def test_pre_deliver_passes_message_without_envelope_fields():
    """BC invariant (Pitfall #8): no envelope fields -> pass-through, no raise."""
    data = _encode(_base_message())
    msg = _pre_deliver_hooks(data)
    assert msg.persona is None
    assert msg.step_label is None
    assert msg.done is None


def test_pre_deliver_raises_on_partial_envelope():
    """Any-of-three without all-three -> MalformedEnvelopeError."""
    # persona present but missing step_label + done.
    data = _encode(_base_message(persona="engineer"))
    with pytest.raises(MalformedEnvelopeError) as exc_info:
        _pre_deliver_hooks(data)
    # Error message must mention at least one missing envelope field.
    text = str(exc_info.value).lower()
    assert "step_label" in text or "done" in text or "envelope" in text


def test_pre_deliver_accepts_full_envelope():
    """Valid full envelope -> returns TeamMessage without raising."""
    data = _encode(
        _base_message(
            persona="engineer",
            stepLabel="plan:1/3",
            done=False,
        )
    )
    msg = _pre_deliver_hooks(data)
    assert msg.persona == "engineer"
    assert msg.step_label == "plan:1/3"
    assert msg.done is False


def test_consecutive_malformed_triggers_drift_regression():
    """8 consecutive partial envelopes from one agent -> DriftRegression on 8th."""
    drift_events: list[DriftRegression] = []
    malformed_events: list[MalformedEnvelope] = []
    bus = get_event_bus()
    bus.subscribe(DriftRegression, lambda e: drift_events.append(e))
    bus.subscribe(MalformedEnvelope, lambda e: malformed_events.append(e))

    partial = _encode(_base_message(persona="engineer"))

    # 7 malformed envelopes — no DriftRegression yet.
    for _ in range(7):
        with pytest.raises(MalformedEnvelopeError):
            _pre_deliver_hooks(partial)
    assert drift_events == []
    assert len(malformed_events) == 7

    # 8th strike -> DriftRegression emitted.
    with pytest.raises(MalformedEnvelopeError):
        _pre_deliver_hooks(partial)
    assert len(drift_events) == 1
    assert drift_events[0].agent == "engineer"
    assert drift_events[0].consecutive_count >= 8
    assert len(malformed_events) == 8

    # A valid envelope resets the counter — next partial must NOT immediately
    # trigger drift.
    valid = _encode(_base_message(persona="engineer", stepLabel="plan:1/3", done=True))
    _pre_deliver_hooks(valid)

    # One more malformed after reset — still only the original DriftRegression emit.
    with pytest.raises(MalformedEnvelopeError):
        _pre_deliver_hooks(partial)
    assert len(drift_events) == 1


def test_valid_envelope_resets_drift_counter():
    """5 malformed + 1 valid + 8 malformed -> DriftRegression fires at the second 8-streak."""
    drift_events: list[DriftRegression] = []
    get_event_bus().subscribe(DriftRegression, lambda e: drift_events.append(e))

    partial = _encode(_base_message(persona="engineer"))
    valid = _encode(_base_message(persona="engineer", stepLabel="plan:1/3", done=False))

    for _ in range(5):
        with pytest.raises(MalformedEnvelopeError):
            _pre_deliver_hooks(partial)
    assert drift_events == []

    # Valid envelope resets counter.
    _pre_deliver_hooks(valid)
    assert drift_events == []

    # Now 7 malformed — still no drift fires.
    for _ in range(7):
        with pytest.raises(MalformedEnvelopeError):
            _pre_deliver_hooks(partial)
    assert drift_events == []

    # 8th after reset — drift fires once.
    with pytest.raises(MalformedEnvelopeError):
        _pre_deliver_hooks(partial)
    assert len(drift_events) == 1
    assert drift_events[0].consecutive_count >= 8


# Per-agent drift-counter scoping (alice strikes do NOT accumulate onto bob's tally)
# is a correctness requirement (Rule 2 trust-boundary hardening) but not enumerated
# in the plan's 6-test acceptance contract; it is enforced by implementation review
# in the GREEN step and documented in the SUMMARY's "Deviations" section.
