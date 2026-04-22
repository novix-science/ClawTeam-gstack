"""Tests for decay_factor + per-tag TTL (Plan 06-03 Task 1, D-06 / MEM-07).

11 tests covering:
 - pattern/incident/preference TTLs
 - within-TTL (1.0) vs within-2x (0.2) vs past-2x (0.05)
 - multi-tag MAX-TTL rule
 - unknown / empty tags default to 90 days
 - malformed + future timestamps (clock-skew defence)
 - MemoryConfig override
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from clawteam.memory.decay import decay_factor
from clawteam.memory.entry import MemoryEntry
from clawteam.templates import MemoryConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


NOW = datetime(2026, 4, 22, 12, 0, 0, tzinfo=timezone.utc)


def _entry(tags, *, days_ago: float) -> MemoryEntry:
    ts = (NOW - timedelta(days=days_ago)).isoformat()
    return MemoryEntry(
        id="mem-teamA-20260422-abc123",
        author="engineer@sprint-1",
        title="decay probe",
        tags=list(tags),
        learned_from="artifact",
        scope="team",
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# Test 1 — pattern tag inside 90-day TTL
# ---------------------------------------------------------------------------


def test_pattern_default_ttl():
    e = _entry(["pattern"], days_ago=30)
    assert decay_factor(e, NOW) == 1.0


# ---------------------------------------------------------------------------
# Test 2 — pattern past 90 days but within 180 (2x)
# ---------------------------------------------------------------------------


def test_pattern_expired_but_within_2x():
    e = _entry(["pattern"], days_ago=100)
    assert decay_factor(e, NOW) == 0.2


# ---------------------------------------------------------------------------
# Test 3 — pattern past 180 days (2x)
# ---------------------------------------------------------------------------


def test_pattern_deeply_expired():
    e = _entry(["pattern"], days_ago=200)
    assert decay_factor(e, NOW) == 0.05


# ---------------------------------------------------------------------------
# Test 4 — preference never expires
# ---------------------------------------------------------------------------


def test_preference_indefinite():
    e = _entry(["preference"], days_ago=365 * 10)
    assert decay_factor(e, NOW) == 1.0


# ---------------------------------------------------------------------------
# Test 5 — incident tag has 180-day TTL
# ---------------------------------------------------------------------------


def test_incident_180_days():
    fresh = _entry(["incident"], days_ago=100)
    half_expired = _entry(["incident"], days_ago=200)
    deep_expired = _entry(["incident"], days_ago=400)
    assert decay_factor(fresh, NOW) == 1.0
    assert decay_factor(half_expired, NOW) == 0.2
    assert decay_factor(deep_expired, NOW) == 0.05


# ---------------------------------------------------------------------------
# Test 6 — MAX TTL among multiple tags wins
# ---------------------------------------------------------------------------


def test_max_ttl_wins_when_multi_tag():
    e = _entry(["pattern", "preference"], days_ago=365 * 10)
    # preference = indefinite, so MAX wins → 1.0 even 10 years later
    assert decay_factor(e, NOW) == 1.0


# ---------------------------------------------------------------------------
# Test 7 — unknown tag falls back to 90-day default
# ---------------------------------------------------------------------------


def test_unknown_tag_default_90():
    e = _entry(["nonsense"], days_ago=95)
    assert decay_factor(e, NOW) == 0.2  # 95 > 90 → within 2x


# ---------------------------------------------------------------------------
# Test 8 — empty tags fall back to 90-day default
# ---------------------------------------------------------------------------


def test_empty_tags_default_90():
    e = _entry([], days_ago=100)
    assert decay_factor(e, NOW) == 0.2


# ---------------------------------------------------------------------------
# Test 9 — malformed timestamp → defensive 0.05 (never crash)
# ---------------------------------------------------------------------------


def test_malformed_timestamp_returns_low():
    e = MemoryEntry(
        id="mem-teamA-20260422-abc123",
        author="engineer@sprint-1",
        title="bad ts",
        tags=["pattern"],
        learned_from="artifact",
        scope="team",
    )
    # Tamper AFTER construction to bypass pydantic's auto-iso default.
    object.__setattr__(e, "timestamp", "not-an-iso")
    assert decay_factor(e, NOW) == 0.05


# ---------------------------------------------------------------------------
# Test 10 — future timestamp (clock skew) returns 1.0
# ---------------------------------------------------------------------------


def test_future_timestamp_returns_1():
    e = _entry(["pattern"], days_ago=-5)  # 5 days in the future
    assert decay_factor(e, NOW) == 1.0


# ---------------------------------------------------------------------------
# Test 11 — custom TTL via MemoryConfig
# ---------------------------------------------------------------------------


def test_custom_ttl_via_config():
    cfg = MemoryConfig(retention_pattern_days=30)
    e = _entry(["pattern"], days_ago=50)
    # 50 > 30 → past custom TTL, but within 2x (60) → 0.2
    assert decay_factor(e, NOW, memory_config=cfg) == 0.2
