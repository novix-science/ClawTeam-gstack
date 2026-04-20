"""RED phase tests for Phase 2 additive event dataclasses (Plan 02-01).

All 8 new event classes must inherit HarnessEvent, be @dataclass-decorated,
and match the field signatures in §02-PATTERNS.md §10 exactly.
"""

from __future__ import annotations

from dataclasses import is_dataclass

from clawteam.events.bus import EventBus
from clawteam.events.types import (
    ArtifactCapExceeded,
    BeforeFileWrite,
    BeforeToolCall,
    CycleDetected,
    DriftRegression,
    ForcedProgressTriggered,
    FreezeChange,
    HarnessEvent,
    MalformedEnvelope,
)

# ── Shape tests (one per class) ──────────────────────────────────────


def test_before_tool_call_shape():
    evt = BeforeToolCall()
    assert is_dataclass(evt)
    assert evt.agent_name == ""
    assert evt.tool_name == ""
    assert evt.args == {}
    assert evt.veto is False
    assert evt.veto_reason == ""


def test_before_file_write_shape():
    evt = BeforeFileWrite()
    assert is_dataclass(evt)
    assert evt.agent_name == ""
    assert evt.path == ""
    assert evt.size_bytes == 0
    assert evt.veto is False
    assert evt.veto_reason == ""


def test_before_tool_call_veto_roundtrip():
    evt = BeforeToolCall(
        team_name="t",
        agent_name="a",
        tool_name="write_file",
        args={"path": "/tmp/x"},
    )
    evt.veto = True
    evt.veto_reason = "blocked by /freeze"
    assert evt.veto is True
    assert evt.veto_reason == "blocked by /freeze"


def test_malformed_envelope_shape():
    evt = MalformedEnvelope()
    assert is_dataclass(evt)
    assert evt.agent == ""
    assert evt.violation == ""
    assert evt.turn_id == ""
    # MalformedEnvelope is a notification event — no veto field.
    assert not hasattr(evt, "veto")


def test_drift_regression_shape():
    evt = DriftRegression()
    assert is_dataclass(evt)
    assert evt.agent == ""
    assert evt.consecutive_count == 0
    assert evt.last_violation == ""


def test_freeze_change_shape():
    evt = FreezeChange()
    assert is_dataclass(evt)
    assert evt.action == ""
    assert evt.path == ""
    assert evt.agent == ""
    assert evt.reason == ""
    assert evt.actor == ""


def test_cycle_detected_shape():
    evt = CycleDetected()
    assert is_dataclass(evt)
    assert evt.pair == ("", "")
    assert evt.topic_hash == ""
    assert evt.route_keys == []
    assert evt.window_size == 20


def test_forced_progress_triggered_shape():
    evt = ForcedProgressTriggered()
    assert is_dataclass(evt)
    assert evt.agent == ""
    assert evt.consecutive_no_progress == 0
    assert evt.question_id == ""


def test_artifact_cap_exceeded_shape():
    evt = ArtifactCapExceeded()
    assert is_dataclass(evt)
    assert evt.artifact_name == ""
    assert evt.size_bytes == 0
    assert evt.cap_bytes == 0
    assert evt.scope == ""
    # scope accepts "file" or "phase"
    evt2 = ArtifactCapExceeded(scope="file")
    assert evt2.scope == "file"
    evt3 = ArtifactCapExceeded(scope="phase")
    assert evt3.scope == "phase"


# ── Inheritance invariant ────────────────────────────────────────────


def test_all_new_events_inherit_harness_event():
    classes = [
        BeforeToolCall,
        BeforeFileWrite,
        FreezeChange,
        MalformedEnvelope,
        DriftRegression,
        CycleDetected,
        ForcedProgressTriggered,
        ArtifactCapExceeded,
    ]
    for cls in classes:
        assert issubclass(cls, HarnessEvent), f"{cls.__name__} must subclass HarnessEvent"
        inst = cls()
        assert hasattr(inst, "team_name")
        assert hasattr(inst, "timestamp")
        assert inst.team_name == ""
        # timestamp default_factory produces an ISO string
        assert isinstance(inst.timestamp, str) and inst.timestamp != ""


# ── End-to-end veto through real EventBus ────────────────────────────


def test_event_bus_veto_roundtrip_before_file_write():
    """Mirror tests/test_event_bus.py::test_veto_pattern for BeforeFileWrite."""
    bus = EventBus()

    def veto_handler(e):
        e.veto = True
        e.veto_reason = "test-veto"

    bus.subscribe(BeforeFileWrite, veto_handler)
    event = BeforeFileWrite(
        team_name="t",
        agent_name="a",
        path="/tmp/x",
        size_bytes=100,
    )
    bus.emit(event)
    assert event.veto is True
    assert event.veto_reason == "test-veto"
