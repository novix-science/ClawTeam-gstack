"""Tests for clawteam.harness.phase_registry — plugin-populated phase registry."""

from __future__ import annotations

import pytest
from clawteam.harness.phase_registry import PhaseRegistry


def test_empty_registry_is_valid():
    """An unpopulated registry returns empty collections. Per RFC 001 §4.2 req 3."""
    r = PhaseRegistry()
    assert r.ordered_names() == []
    assert r.phase_roles() == {}
    assert r.review_routers() == []


def test_single_plugin_three_phases_registers_in_order():
    """Registration preserves insertion order. Per RFC 001 §4.2 req 1."""
    r = PhaseRegistry()
    r.register(
        "gstack",
        ["think", "plan", "ship"],
        {"think": ["pm"], "plan": ["pm", "ceo"], "ship": ["shipper"]},
        [],
    )
    assert r.ordered_names() == ["think", "plan", "ship"]
    assert r.phase_roles() == {
        "think": ["pm"],
        "plan": ["pm", "ceo"],
        "ship": ["shipper"],
    }
    assert r.review_routers() == []


def test_duplicate_phase_across_plugins_raises_value_error():
    """Duplicate phase name across plugins raises at registration time. Per RFC 001 §4.2 req 2 + D-03."""
    r = PhaseRegistry()
    r.register("p1", ["a", "b"], {}, [])
    with pytest.raises(ValueError, match="Duplicate phase"):
        r.register("p2", ["b", "c"], {}, [])
    # Failed registration MUST be fully rolled back — "c" must not leak into the registry.
    assert r.ordered_names() == ["a", "b"]


def test_phase_roles_for_unowned_phase_raises_value_error():
    """contribute_phase_roles() keys must be declared by the same plugin. Per RFC 001 §4.3a req 3."""
    r = PhaseRegistry()
    with pytest.raises(ValueError, match="phase role entry for phase 'b' not declared by plugin 'p1'"):
        r.register("p1", ["a"], {"b": ["designer"]}, [])
