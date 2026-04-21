"""Phase 5 Plan 05-02 Task 2 — DeployRegressionDetected + WebVitalRegressionDetected.

Pure substrate addition: two new ``@dataclass(HarnessEvent)`` subclasses
registered at module import via :func:`clawteam.events.bus.register_event_type`.

Mirror of ``tests/test_event_types_phase4.py`` shape (MidReviewThrash +
SycophancyCascadeDetected precedent).

Behaviors:
- Both subclass HarnessEvent (isinstance check).
- Both construct with only ``team_name`` — all other fields have defaults.
- EventBus.emit() round-trips the exact instance to the subscriber.
- Both are registered in the ``_EVENT_TYPE_REGISTRY`` at import time (so
  shell hooks can resolve them by name via ``resolve_event_type``).
"""

from __future__ import annotations

from clawteam.events.bus import EventBus, resolve_event_type
from clawteam.events.types import (
    DeployRegressionDetected,
    HarnessEvent,
    WebVitalRegressionDetected,
)


def test_deploy_regression_is_harness_event():
    evt = DeployRegressionDetected(team_name="t", sprint_id="s1")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"
    assert evt.sprint_id == "s1"
    # Inherited timestamp populated.
    assert "T" in evt.timestamp


def test_web_vital_regression_is_harness_event():
    evt = WebVitalRegressionDetected(team_name="t", sprint_id="s1")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"
    assert evt.sprint_id == "s1"
    assert "T" in evt.timestamp


def test_deploy_regression_defaults():
    evt = DeployRegressionDetected(team_name="t")
    assert evt.sprint_id == ""
    assert evt.deploy_url == ""
    assert evt.regression_flags == []
    assert evt.http_2xx_count == 0
    assert evt.http_5xx_count == 0
    assert evt.avg_response_ms == 0.0
    assert evt.pre_deploy_avg_response_ms == 0.0


def test_web_vital_regression_defaults():
    evt = WebVitalRegressionDetected(team_name="t")
    assert evt.sprint_id == ""
    assert evt.deploy_url == ""
    assert evt.vital == ""
    assert evt.baseline_value == 0.0
    assert evt.observed_value == 0.0
    assert evt.ratio == 0.0


def test_emit_roundtrip_deploy():
    bus = EventBus()
    captured: list[DeployRegressionDetected] = []
    bus.subscribe(DeployRegressionDetected, lambda ev: captured.append(ev))
    sent = DeployRegressionDetected(
        team_name="t",
        sprint_id="s1",
        deploy_url="https://x",
        regression_flags=["5xx>1%"],
        http_5xx_count=12,
        avg_response_ms=450.0,
        pre_deploy_avg_response_ms=200.0,
    )
    bus.emit(sent)
    assert captured == [sent]
    # Exact-instance identity (list equality above checks dataclass eq; add
    # an identity check to prove no copy occurred).
    assert captured[0] is sent


def test_emit_roundtrip_web_vital():
    bus = EventBus()
    captured: list[WebVitalRegressionDetected] = []
    bus.subscribe(WebVitalRegressionDetected, lambda ev: captured.append(ev))
    sent = WebVitalRegressionDetected(
        team_name="t",
        sprint_id="s1",
        deploy_url="https://x",
        vital="lcp",
        baseline_value=1800.0,
        observed_value=3200.0,
        ratio=1.78,
    )
    bus.emit(sent)
    assert captured == [sent]
    assert captured[0] is sent


def test_register_event_type_called_on_import():
    """Both new event classes are resolvable by name after module import.

    clawteam.events.types must call ``register_event_type`` at module load time
    (mirror of Phase 4 MidReviewThrash / SycophancyCascadeDetected precedent).
    resolve_event_type() inspects the registry dict first; presence there
    proves the registration call executed at import.
    """
    assert resolve_event_type("DeployRegressionDetected") is DeployRegressionDetected
    assert resolve_event_type("WebVitalRegressionDetected") is WebVitalRegressionDetected
