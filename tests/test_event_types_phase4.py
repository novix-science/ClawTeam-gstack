"""Phase 4 event-type round-trip tests (Plan 04-02).

Pure substrate addition: MidReviewThrash (D-19) and SycophancyCascadeDetected
(D-09/D-20) @dataclass(HarnessEvent) subclasses. No behavior changes until
Plan 10 emits them; these tests pin the construction + emit/subscribe contract.
"""

from __future__ import annotations

from clawteam.events.bus import EventBus
from clawteam.events.types import (
    HarnessEvent,
    MidReviewThrash,
    SycophancyCascadeDetected,
)


def test_mid_review_thrash_construction():
    evt = MidReviewThrash(
        team_name="team-a",
        sprint_id="abc12345",
        review_sha="a" * 40,
        new_sha="b" * 40,
        reviewer_roles_active=["reviewer", "designer"],
        diff_paths_added=["src/new.py"],
        diff_paths_removed=["src/gone.py"],
    )
    assert evt.sprint_id == "abc12345"
    assert evt.review_sha == "a" * 40
    assert evt.new_sha == "b" * 40
    assert evt.reviewer_roles_active == ["reviewer", "designer"]
    assert evt.diff_paths_added == ["src/new.py"]
    assert evt.diff_paths_removed == ["src/gone.py"]
    assert isinstance(evt, HarnessEvent)
    # Inherited fields
    assert evt.team_name == "team-a"
    assert evt.timestamp  # ISO-8601 UTC string populated


def test_mid_review_thrash_emit_round_trip():
    bus = EventBus()
    captured: list[MidReviewThrash] = []
    bus.subscribe(MidReviewThrash, lambda e: captured.append(e))
    bus.emit(MidReviewThrash(team_name="t", sprint_id="s1", review_sha="a" * 40, new_sha="b" * 40))
    assert len(captured) == 1
    assert captured[0].sprint_id == "s1"


def test_sycophancy_cascade_construction():
    evt = SycophancyCascadeDetected(
        team_name="team-b",
        sprint_id="xyz98765",
        review_round=3,
        agreement_rate=0.95,
        threshold=0.9,
        reviewer_roles=["reviewer", "designer", "security", "dx-lead"],
    )
    assert evt.agreement_rate == 0.95
    assert evt.threshold == 0.9
    assert evt.review_round == 3
    assert evt.reviewer_roles == ["reviewer", "designer", "security", "dx-lead"]
    assert isinstance(evt, HarnessEvent)


def test_sycophancy_cascade_emit_round_trip():
    bus = EventBus()
    captured: list[SycophancyCascadeDetected] = []
    bus.subscribe(SycophancyCascadeDetected, lambda e: captured.append(e))
    bus.emit(SycophancyCascadeDetected(team_name="t", sprint_id="s", agreement_rate=0.92))
    assert len(captured) == 1
    assert captured[0].agreement_rate == 0.92


def test_timestamps_auto_populated():
    evt1 = MidReviewThrash(team_name="t")
    evt2 = SycophancyCascadeDetected(team_name="t")
    # Valid ISO-8601 UTC: "YYYY-MM-DDTHH:MM:SS.ffffff+00:00"
    assert "T" in evt1.timestamp
    assert "T" in evt2.timestamp


def test_default_field_values():
    evt = MidReviewThrash()
    assert evt.sprint_id == ""
    assert evt.review_sha == ""
    assert evt.new_sha == ""
    assert evt.reviewer_roles_active == []
    assert evt.diff_paths_added == []
    assert evt.diff_paths_removed == []

    evt2 = SycophancyCascadeDetected()
    assert evt2.sprint_id == ""
    assert evt2.review_round == 0
    assert evt2.agreement_rate == 0.0
    assert evt2.threshold == 0.9
    assert evt2.reviewer_roles == []
