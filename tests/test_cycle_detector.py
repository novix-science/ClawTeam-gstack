"""RED-phase tests for Phase 2 cycle detector in DefaultRoutingPolicy (Plan 02-08).

Exercises the three cycle-detector invariants (§02-CONTEXT D-18..D-21 + Pitfall #3 + Pitfall #7):

  1. Cycle detection runs BEFORE existing throttle and reuses `recentEvents` (50-entry
     bounded window) rather than keeping a parallel tracker (specifics lesson #1).
  2. Topic-hash priority chain: RuntimeEnvelope.dedupe_key → payload.request_id →
     sha1(content[:128])[:16] (D-19).
  3. Window = last 20 entries in `recentEvents`; threshold = >=3 A->B and >=3 B->A with
     same topic-hash in same window -> emit CycleDetected + persist suppressed topic
     on `routes[route_key].suppressedTopics` (D-20, D-21).
  4. Pitfall #3: legitimate iteration (TaskCompleted emitting progressSignal flag on the
     recentEvents entry) breaks the cycle streak so the detector does not false-positive.
  5. Pitfall #7: sync emit — CycleDetected handler runs inside decide() return path with
     state already on disk so suppression is observable when handler fires.
"""

from __future__ import annotations

import hashlib
import importlib

import pytest

from clawteam.events.global_bus import get_event_bus, reset_event_bus
from clawteam.events.types import CycleDetected
from clawteam.team.routing_policy import DefaultRoutingPolicy, RuntimeEnvelope

# Gate the Pitfall #3 integration test on Plan 02-09 shipping the progress-signal
# populator. The hook point (routing_policy._detect_cycle reads
# `entry.get("progressSignal")`) ships in Plan 02-08, but the populator lives
# at the theater-detector site in Plan 02-09 (tests/test_theater_detector.py).
try:
    importlib.import_module("clawteam.harness.theater_detector")
    _PROGRESS_SIGNAL_READY = True
except ImportError:
    _PROGRESS_SIGNAL_READY = False


@pytest.fixture(autouse=True)
def _reset_bus_and_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    reset_event_bus()
    yield
    reset_event_bus()


def _prime_recent_events(
    policy: DefaultRoutingPolicy,
    *,
    entries: list[dict],
) -> None:
    """Seed the on-disk recentEvents list directly.

    Mirrors the shape `_append_event` writes so `_detect_cycle` iteration finds
    `routeKey` + `topicHash` + optional `progressSignal` keys on each entry.
    """
    state = policy.read_state()
    state["recentEvents"] = entries
    policy._save_state(state)


def test_no_cycle_on_single_message():
    """One A->B message with no priors must NOT trip the cycle detector."""
    policy = DefaultRoutingPolicy(team_name="demo")
    envelope = RuntimeEnvelope(
        source="engineer", target="reviewer", summary="init", dedupe_key="topic-1"
    )
    decision = policy.decide(envelope)
    assert decision.action != "suppress"
    assert decision.reason != "cycle_detected"


def test_three_roundtrips_trip_cycle():
    """3 A->B + 3 B->A in the last-20 window with matching topic hash -> suppress + emit."""
    policy = DefaultRoutingPolicy(team_name="demo")
    topic = "loop-topic"
    entries = []
    # Interleave 3 A->B then 3 B->A, all with matching topicHash.
    for _ in range(3):
        entries.append(
            {
                "timestamp": "2026-04-20T10:00:00+00:00",
                "routeKey": "engineer->reviewer",
                "topicHash": topic,
                "source": "engineer",
                "target": "reviewer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "loop",
                "pendingCount": 0,
            }
        )
        entries.append(
            {
                "timestamp": "2026-04-20T10:00:01+00:00",
                "routeKey": "reviewer->engineer",
                "topicHash": topic,
                "source": "reviewer",
                "target": "engineer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "loop",
                "pendingCount": 0,
            }
        )
    _prime_recent_events(policy, entries=entries)

    # Subscribe before decide() so we can prove the emit is sync.
    received: list[CycleDetected] = []
    get_event_bus().subscribe(CycleDetected, lambda e: received.append(e))

    envelope = RuntimeEnvelope(
        source="engineer",
        target="reviewer",
        summary="another loop",
        dedupe_key=topic,
    )
    decision = policy.decide(envelope)

    assert decision.action == "suppress"
    assert decision.reason == "cycle_detected"
    assert len(received) == 1
    assert received[0].pair == ("engineer", "reviewer")
    assert received[0].topic_hash == topic


def test_window_bounded_to_20():
    """Matching events OLDER than the 20-entry tail must NOT count toward the streak."""
    policy = DefaultRoutingPolicy(team_name="demo")
    topic = "windowed-topic"

    # 20 filler entries with DIFFERENT routeKey/topic (these form the tail window).
    filler = [
        {
            "timestamp": "2026-04-20T10:00:00+00:00",
            "routeKey": "filler->other",
            "topicHash": "filler-topic",
            "source": "filler",
            "target": "other",
            "action": "pending",
            "reason": "inject_now",
            "summary": "f",
            "pendingCount": 0,
        }
        for _ in range(20)
    ]
    # Push 6 older round-trips BEFORE the filler — these should fall outside tail 20.
    older = []
    for _ in range(3):
        older.append(
            {
                "timestamp": "2026-04-20T09:00:00+00:00",
                "routeKey": "engineer->reviewer",
                "topicHash": topic,
                "source": "engineer",
                "target": "reviewer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "old",
                "pendingCount": 0,
            }
        )
        older.append(
            {
                "timestamp": "2026-04-20T09:00:01+00:00",
                "routeKey": "reviewer->engineer",
                "topicHash": topic,
                "source": "reviewer",
                "target": "engineer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "old",
                "pendingCount": 0,
            }
        )
    _prime_recent_events(policy, entries=older + filler)

    received: list[CycleDetected] = []
    get_event_bus().subscribe(CycleDetected, lambda e: received.append(e))

    envelope = RuntimeEnvelope(
        source="engineer",
        target="reviewer",
        summary="new message",
        dedupe_key=topic,
    )
    decision = policy.decide(envelope)
    assert decision.action != "suppress"
    assert received == []


def test_topic_hash_priority_chain():
    """Priority chain: dedupe_key -> payload.request_id -> sha1(content[:128])[:16]."""
    policy = DefaultRoutingPolicy(team_name="demo")

    # (a) dedupe_key wins.
    env_a = RuntimeEnvelope(
        source="engineer",
        target="reviewer",
        summary="x",
        dedupe_key="X",
        payload={"request_id": "Y", "content": "zzz"},
    )
    assert policy._topic_hash(env_a) == "X"

    # (b) no dedupe_key, request_id wins.
    env_b = RuntimeEnvelope(
        source="engineer",
        target="reviewer",
        summary="x",
        payload={"request_id": "Y", "content": "zzz"},
    )
    assert policy._topic_hash(env_b) == "Y"

    # (c) neither dedupe_key nor request_id — fall back to sha1(content[:128])[:16].
    content = "hello world from sprint"
    env_c = RuntimeEnvelope(
        source="engineer",
        target="reviewer",
        summary="x",
        payload={"content": content},
    )
    expected = hashlib.sha1(content[:128].encode("utf-8")).hexdigest()[:16]
    assert policy._topic_hash(env_c) == expected


def test_suppression_persists_in_route_state():
    """After cycle trips, routes[A->B].suppressedTopics holds the topic_hash.

    A subsequent message with the same topic_hash must be suppressed WITHOUT re-emitting
    CycleDetected (dedupe — reason is `cycle_suppressed_existing`, not `cycle_detected`).
    """
    policy = DefaultRoutingPolicy(team_name="demo")
    topic = "persist-topic"
    entries = []
    for _ in range(3):
        entries.append(
            {
                "timestamp": "2026-04-20T10:00:00+00:00",
                "routeKey": "engineer->reviewer",
                "topicHash": topic,
                "source": "engineer",
                "target": "reviewer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "loop",
                "pendingCount": 0,
            }
        )
        entries.append(
            {
                "timestamp": "2026-04-20T10:00:01+00:00",
                "routeKey": "reviewer->engineer",
                "topicHash": topic,
                "source": "reviewer",
                "target": "engineer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "loop",
                "pendingCount": 0,
            }
        )
    _prime_recent_events(policy, entries=entries)

    received: list[CycleDetected] = []
    get_event_bus().subscribe(CycleDetected, lambda e: received.append(e))

    envelope = RuntimeEnvelope(
        source="engineer", target="reviewer", summary="loop", dedupe_key=topic
    )
    first = policy.decide(envelope)
    assert first.action == "suppress"
    assert first.reason == "cycle_detected"
    assert len(received) == 1

    # Verify persisted suppressedTopics.
    state = policy.read_state()
    route = state["routes"]["engineer->reviewer"]
    assert topic in route["suppressedTopics"]

    # Second identical envelope must be suppressed via the persisted flag (no new emit).
    second = policy.decide(envelope)
    assert second.action == "suppress"
    assert second.reason == "cycle_suppressed_existing"
    assert len(received) == 1  # handler did NOT fire again


@pytest.mark.skipif(
    not _PROGRESS_SIGNAL_READY,
    reason="progressSignal populator ships in Plan 02-09 theater detector",
)
def test_progress_signal_breaks_cycle_streak_per_pitfall3():
    """If any recentEvents entry carries `progressSignal: True`, the streak is broken.

    Pitfall #3 mitigation: legitimate iteration with shipped work (artifact_bytes_delta
    > 0) must NOT trigger false-positive cycle alert.
    """
    policy = DefaultRoutingPolicy(team_name="demo")
    topic = "progress-topic"
    entries = []
    for i in range(3):
        entries.append(
            {
                "timestamp": f"2026-04-20T10:00:{i:02d}+00:00",
                "routeKey": "engineer->reviewer",
                "topicHash": topic,
                "source": "engineer",
                "target": "reviewer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "iter",
                "pendingCount": 0,
                # First entry carries the progress signal — breaks the streak.
                "progressSignal": i == 0,
            }
        )
        entries.append(
            {
                "timestamp": f"2026-04-20T10:00:{i:02d}+00:00",
                "routeKey": "reviewer->engineer",
                "topicHash": topic,
                "source": "reviewer",
                "target": "engineer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "iter",
                "pendingCount": 0,
            }
        )
    _prime_recent_events(policy, entries=entries)

    received: list[CycleDetected] = []
    get_event_bus().subscribe(CycleDetected, lambda e: received.append(e))

    envelope = RuntimeEnvelope(
        source="engineer", target="reviewer", summary="iter", dedupe_key=topic
    )
    decision = policy.decide(envelope)
    assert decision.action != "suppress"
    assert received == []


def test_cycle_detected_emit_is_sync():
    """Handler appended during emit() — not after decide() returns (Pitfall #7 proof).

    The handler reads policy state at call time. If emit is synchronous, the handler
    observes `suppressedTopics` already persisted on disk; if async, it would not.
    """
    policy = DefaultRoutingPolicy(team_name="demo")
    topic = "sync-topic"
    entries = []
    for _ in range(3):
        entries.append(
            {
                "timestamp": "2026-04-20T10:00:00+00:00",
                "routeKey": "engineer->reviewer",
                "topicHash": topic,
                "source": "engineer",
                "target": "reviewer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "loop",
                "pendingCount": 0,
            }
        )
        entries.append(
            {
                "timestamp": "2026-04-20T10:00:01+00:00",
                "routeKey": "reviewer->engineer",
                "topicHash": topic,
                "source": "reviewer",
                "target": "engineer",
                "action": "pending",
                "reason": "inject_now",
                "summary": "loop",
                "pendingCount": 0,
            }
        )
    _prime_recent_events(policy, entries=entries)

    observed_on_disk: list[bool] = []

    def handler(_evt: CycleDetected) -> None:
        # Re-read state from disk at handler-call time. If emit is sync, the
        # suppressedTopics write preceded the emit so we see the topic_hash;
        # if async, the save might race.
        state = policy.read_state()
        route = state["routes"].get("engineer->reviewer", {})
        observed_on_disk.append(topic in route.get("suppressedTopics", []))

    get_event_bus().subscribe(CycleDetected, handler)

    envelope = RuntimeEnvelope(
        source="engineer", target="reviewer", summary="loop", dedupe_key=topic
    )
    decision = policy.decide(envelope)

    assert decision.action == "suppress"
    assert observed_on_disk == [True], (
        "CycleDetected handler must observe suppressedTopics on disk "
        "(proves sync emit + state-save ordering per Pitfall #7)"
    )
