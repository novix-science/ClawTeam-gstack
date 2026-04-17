"""Tests for the three new optional HarnessPlugin hooks + PluginManager wiring."""

from __future__ import annotations

from clawteam.harness.phase_registry import get_registry, reset_registry

from clawteam.events.global_bus import get_event_bus  # noqa: F401 — ensure bus import works
from clawteam.plugins.base import HarnessPlugin
from clawteam.plugins.manager import PluginManager


class _NoopPlugin(HarnessPlugin):
    name = "noop-test"

    def on_register(self, ctx):  # required abstract method
        pass


class _GstackLikePlugin(HarnessPlugin):
    name = "gstack-like"

    def on_register(self, ctx):
        pass

    def contribute_phases(self):
        return ["alpha", "beta"]

    def contribute_phase_roles(self):
        return {"alpha": ["pm"]}


def test_base_class_default_returns_empty_phases():
    """Base-class default returns []. Per RFC 001 §4.3 req 1 + D-04."""
    assert _NoopPlugin().contribute_phases() == []


def test_base_class_default_returns_empty_phase_roles():
    """Base-class default returns {}. Per RFC 001 §4.3a req 1 + D-04."""
    assert _NoopPlugin().contribute_phase_roles() == {}


def test_base_class_default_returns_empty_review_routers():
    """Base-class default returns []. Per RFC 001 §4.3b req 1 + D-04."""
    assert _NoopPlugin().contribute_review_routers() == []


def test_plugin_manager_populates_registry_on_register():
    """PluginManager._instantiate_and_register funnels hook results into the global registry."""
    reset_registry()
    try:
        pm = PluginManager()
        pm._instantiate_and_register(_GstackLikePlugin)
        assert get_registry().ordered_names() == ["alpha", "beta"]
        assert get_registry().phase_roles() == {"alpha": ["pm"]}
    finally:
        reset_registry()
