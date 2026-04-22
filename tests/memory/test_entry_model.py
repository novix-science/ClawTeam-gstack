"""Tests for MemoryEntry pydantic schema (Plan 06-02 Task 1).

Ten tests covering id regex, scope/role coupling, tag regex, confidence range,
learned_from + op Literals, tag/body max length, and model_dump roundtrip.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from clawteam.memory.entry import MemoryEntry


# ---------------------------------------------------------------------------
# Test 1 — minimal valid instance
# ---------------------------------------------------------------------------


def test_minimal_valid():
    e = MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="engineer@sprint-1",
        title="t",
        tags=["pattern"],
        learned_from="artifact",
        scope="team",
    )
    assert e.id == "mem-myteam-20260421-abc123"
    assert e.scope == "team"
    assert e.role is None
    assert e.op == "write"
    # Defaults
    assert e.confidence == 0.7
    assert e.body == ""
    assert e.evidence == ""


# ---------------------------------------------------------------------------
# Test 2 — id pattern enforcement
# ---------------------------------------------------------------------------


def test_id_pattern_enforced():
    # Bad shape (no mem- prefix)
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="bad-id",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="artifact",
            scope="team",
        )
    # Uppercase hex rejected — lowercase hex only
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-ABCDEF",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="artifact",
            scope="team",
        )
    # Date portion not YYYYMMDD
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-2026Q1-abc123",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="artifact",
            scope="team",
        )


# ---------------------------------------------------------------------------
# Test 3 — scope/role coupling
# ---------------------------------------------------------------------------


def test_scope_role_coupling():
    # scope="role" with role=None → ValidationError
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="artifact",
            scope="role",
            role=None,
        )
    # scope="role" with role="designer" → valid
    e = MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="x@y",
        title="t",
        tags=["pattern"],
        learned_from="artifact",
        scope="role",
        role="designer",
    )
    assert e.role == "designer"
    # scope="team" with role="designer" → ValidationError
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="artifact",
            scope="team",
            role="designer",
        )


# ---------------------------------------------------------------------------
# Test 4 — tag regex
# ---------------------------------------------------------------------------


def _mk(tags: list[str]) -> MemoryEntry:
    return MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="x@y",
        title="t",
        tags=tags,
        learned_from="artifact",
        scope="team",
    )


def test_tag_regex():
    # Valid
    _mk(["pattern"])
    _mk(["impact:high"])
    _mk(["_internal"]) if False else None  # underscore after leading char
    # Spec says underscore allowed in body; leading underscore alone fails
    # since regex is [a-z0-9][a-z0-9:_-]* — first char must be a-z0-9. Per
    # plan behavior: "_internal valid (underscore allowed)" — but regex
    # requires leading alnum. Honor plan: underscore allowed but NOT as
    # leading char. Accept "a_internal" instead.
    _mk(["a_internal"])  # underscore allowed in body
    # Invalid: uppercase
    with pytest.raises(ValidationError):
        _mk(["Pattern"])
    # Invalid: invalid char
    with pytest.raises(ValidationError):
        _mk(["pattern!"])


# ---------------------------------------------------------------------------
# Test 5 — confidence range
# ---------------------------------------------------------------------------


def test_confidence_range():
    e = MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="x@y",
        title="t",
        tags=["pattern"],
        learned_from="artifact",
        scope="team",
        confidence=0.7,
    )
    assert e.confidence == 0.7
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="artifact",
            scope="team",
            confidence=-0.1,
        )
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="artifact",
            scope="team",
            confidence=1.5,
        )


# ---------------------------------------------------------------------------
# Test 6 — learned_from Literal
# ---------------------------------------------------------------------------


def test_learned_from_literal():
    for src in ("user", "artifact", "self-inferred", "sprint-reflect"):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from=src,
            scope="team",
        )
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="other",
            scope="team",
        )


# ---------------------------------------------------------------------------
# Test 7 — op Literal
# ---------------------------------------------------------------------------


def test_op_literal():
    e_default = MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="x@y",
        title="t",
        tags=["pattern"],
        learned_from="artifact",
        scope="team",
    )
    assert e_default.op == "write"
    MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="x@y",
        title="t",
        tags=["pattern"],
        learned_from="artifact",
        scope="team",
        op="prune",
    )
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            tags=["pattern"],
            learned_from="artifact",
            scope="team",
            op="delete",
        )


# ---------------------------------------------------------------------------
# Test 8 — tags max length
# ---------------------------------------------------------------------------


def test_tags_max_length():
    tags_32 = [f"t{i:02d}" for i in range(32)]
    MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="x@y",
        title="t",
        tags=tags_32,
        learned_from="artifact",
        scope="team",
    )
    tags_33 = [f"t{i:02d}" for i in range(33)]
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            tags=tags_33,
            learned_from="artifact",
            scope="team",
        )


# ---------------------------------------------------------------------------
# Test 9 — body max length
# ---------------------------------------------------------------------------


def test_body_max_length():
    MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="x@y",
        title="t",
        body="a" * 20_000,
        tags=["pattern"],
        learned_from="artifact",
        scope="team",
    )
    with pytest.raises(ValidationError):
        MemoryEntry(
            id="mem-myteam-20260421-abc123",
            author="x@y",
            title="t",
            body="a" * 20_001,
            tags=["pattern"],
            learned_from="artifact",
            scope="team",
        )


# ---------------------------------------------------------------------------
# Test 10 — model_dump roundtrip
# ---------------------------------------------------------------------------


def test_model_dump_roundtrip():
    original = MemoryEntry(
        id="mem-myteam-20260421-abc123",
        author="x@y",
        sprint_id="s-1",
        phase="build",
        title="Discovered retry pattern",
        body="retry idempotent with jitter",
        tags=["pattern", "retry"],
        evidence="src/http.py:42",
        confidence=0.9,
        learned_from="artifact",
        scope="team",
    )
    as_dict = original.model_dump()
    rebuilt = MemoryEntry(**as_dict)
    assert rebuilt == original
