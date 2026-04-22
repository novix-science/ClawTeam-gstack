"""Phase 6 Wave 0 / Plan 06-01 Task 2 — MemoryWritePersisted + ConflictDetected +
MemoryBackfillComplete + clawteam.memory package marker.

Mirrors ``tests/test_event_types_phase5.py`` shape verbatim. Behaviors:

- All three events subclass HarnessEvent (isinstance checks).
- All three construct with only ``team_name`` kwarg (other fields default).
- EventBus.emit() round-trips each exact instance to the subscriber.
- All three are registered in ``_EVENT_TYPE_REGISTRY`` at module import so
  shell hooks can resolve them by name via ``resolve_event_type``.
- ``clawteam.memory`` is importable as a package (Wave 0 skeleton).
"""

from __future__ import annotations

from clawteam.events.bus import EventBus, resolve_event_type
from clawteam.events.types import (
    ConflictDetected,
    HarnessEvent,
    MemoryBackfillComplete,
    MemoryWritePersisted,
)


# ── isinstance checks ────────────────────────────────────────────────────


def test_memory_write_persisted_is_harness_event():
    evt = MemoryWritePersisted(team_name="t", entry_id="mem-x")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"
    assert evt.entry_id == "mem-x"
    assert "T" in evt.timestamp


def test_conflict_detected_is_harness_event():
    evt = ConflictDetected(team_name="t", new_entry_id="mem-x")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"
    assert evt.new_entry_id == "mem-x"
    assert "T" in evt.timestamp


def test_backfill_complete_is_harness_event():
    evt = MemoryBackfillComplete(team_name="t")
    assert isinstance(evt, HarnessEvent)
    assert evt.team_name == "t"
    assert "T" in evt.timestamp


# ── defaults ─────────────────────────────────────────────────────────────


def test_defaults():
    mwp = MemoryWritePersisted(team_name="t")
    assert mwp.entry_id == ""
    assert mwp.scope == ""
    assert mwp.role == ""
    assert mwp.tags == []
    assert mwp.high_impact is False

    cd = ConflictDetected(team_name="t")
    assert cd.new_entry_id == ""
    assert cd.conflicting_entry_id == ""
    assert cd.similarity == 0.0
    assert cd.shared_tags == []
    assert cd.scope == ""

    mbc = MemoryBackfillComplete(team_name="t")
    assert mbc.team == ""
    assert mbc.entries_promoted == 0
    assert mbc.entries_skipped_already_processed == 0


# ── EventBus round-trip ──────────────────────────────────────────────────


def test_emit_roundtrip_memory_write():
    bus = EventBus()
    captured: list[MemoryWritePersisted] = []
    bus.subscribe(MemoryWritePersisted, lambda ev: captured.append(ev))
    sent = MemoryWritePersisted(
        team_name="t",
        entry_id="mem-abc",
        scope="team",
        role="",
        tags=["pattern", "async"],
        high_impact=True,
    )
    bus.emit(sent)
    assert captured == [sent]
    assert captured[0] is sent


def test_emit_roundtrip_conflict():
    bus = EventBus()
    captured: list[ConflictDetected] = []
    bus.subscribe(ConflictDetected, lambda ev: captured.append(ev))
    sent = ConflictDetected(
        team_name="t",
        new_entry_id="mem-new",
        conflicting_entry_id="mem-old",
        similarity=0.82,
        shared_tags=["pattern"],
        scope="team",
    )
    bus.emit(sent)
    assert captured == [sent]
    assert captured[0] is sent


def test_emit_roundtrip_backfill():
    bus = EventBus()
    captured: list[MemoryBackfillComplete] = []
    bus.subscribe(MemoryBackfillComplete, lambda ev: captured.append(ev))
    sent = MemoryBackfillComplete(
        team_name="t",
        team="my-team",
        entries_promoted=3,
        entries_skipped_already_processed=1,
    )
    bus.emit(sent)
    assert captured == [sent]
    assert captured[0] is sent


# ── Registry visibility (late-import pattern, Phase 5 precedent) ─────────


def test_register_event_type_called_on_import():
    """All 3 new event classes resolvable by name after module import.

    Mirrors the Phase 5 precedent in ``tests/test_event_types_phase5.py``:
    clawteam.events.types must call ``register_event_type`` at module load
    for each new class so shell hooks can reference them by name.
    """
    assert resolve_event_type("MemoryWritePersisted") is MemoryWritePersisted
    assert resolve_event_type("ConflictDetected") is ConflictDetected
    assert resolve_event_type("MemoryBackfillComplete") is MemoryBackfillComplete


# ── clawteam.memory package marker ───────────────────────────────────────


def test_memory_package_imports():
    """Wave 0 skeleton: clawteam.memory importable as a package.

    Public API (MemoryEntry / TeamMemoryStore / rank / detect_conflict /
    backfill_scan) arrives in Plans 06-02, 06-03, 06-10, 06-11.
    """
    import clawteam.memory

    assert hasattr(clawteam.memory, "__path__"), (
        "clawteam.memory must be a package, not a module"
    )
    # __all__ is an empty list at Wave 0 (no re-exports yet).
    assert clawteam.memory.__all__ == []
