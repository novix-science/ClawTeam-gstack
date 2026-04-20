"""Tests for the three new optional HarnessPlugin hooks + PluginManager wiring."""

from __future__ import annotations

import sys
import types

import pytest

from clawteam.events.global_bus import get_event_bus  # noqa: F401 — ensure bus import works
from clawteam.harness.phase_registry import get_registry, reset_registry
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


# ── Phase 2 / Plan 02-01 hook: contribute_evidence_schemas ────────────


class _EvidenceSchemasPlugin(HarnessPlugin):
    """Plugin that contributes evidence schemas (Plan 02-01)."""

    name = "ev-schemas-test"

    _schemas: dict[str, type] = {}

    def on_register(self, ctx):
        pass

    def contribute_evidence_schemas(self):
        return dict(self._schemas)


def test_contribute_evidence_schemas_default_empty():
    """Default implementation returns {} — plugins opt-in by overriding."""
    assert _NoopPlugin().contribute_evidence_schemas() == {}


def test_evidence_schemas_hook_exists_on_base():
    """The hook must be declared on the base class as a callable returning {}."""
    assert hasattr(HarnessPlugin, "contribute_evidence_schemas")
    assert callable(HarnessPlugin.contribute_evidence_schemas)
    assert _NoopPlugin().contribute_evidence_schemas() == {}


def test_plugin_manager_loops_evidence_schemas_when_registry_missing(monkeypatch):
    """Wave-parallel safety: if clawteam.harness.evidence_schemas is absent, skip silently.

    Plan 02-04 lands the registry; Plan 02-01 ships the hook + a lazy-import
    guard that tolerates the missing module during wave-parallel execution
    (Plan 01-03 cross-wave parallelism pattern).
    """
    reset_registry()
    # Force-remove any accidentally-present registry module so the guard fires.
    monkeypatch.delitem(sys.modules, "clawteam.harness.evidence_schemas", raising=False)

    class _WithSchemas(_EvidenceSchemasPlugin):
        name = "ev-schemas-missing-registry"
        _schemas = {"foo": object}

    try:
        pm = PluginManager()
        # Must not raise even though evidence_schemas module is absent.
        pm._instantiate_and_register(_WithSchemas)
    finally:
        reset_registry()


def test_evidence_schema_collision_when_registry_present(monkeypatch):
    """When the registry IS present, duplicate schema keys across plugins
    raise ValueError with the offending schema name in the message."""
    reset_registry()

    seen: dict[str, type] = {}

    def fake_register(name: str, cls: type) -> None:
        if name in seen:
            raise ValueError(f"duplicate evidence schema: {name}")
        seen[name] = cls

    fake_mod = types.ModuleType("clawteam.harness.evidence_schemas")
    fake_mod.register_schema = fake_register  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "clawteam.harness.evidence_schemas", fake_mod)

    class _PluginA(_EvidenceSchemasPlugin):
        name = "ev-schemas-a"
        _schemas = {"design-doc": type}

    class _PluginB(_EvidenceSchemasPlugin):
        name = "ev-schemas-b"
        _schemas = {"design-doc": type}

    try:
        pm = PluginManager()
        pm._instantiate_and_register(_PluginA)
        with pytest.raises(ValueError, match="design-doc"):
            pm._instantiate_and_register(_PluginB)
    finally:
        reset_registry()
