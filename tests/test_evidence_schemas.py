"""Tests for clawteam.harness.evidence_schemas — EvidenceSchemaRegistry.

Plan 02-04: singleton registry populated at plugin-load time, keyed by artifact_type.
Mirrors clawteam.harness.phase_registry.PhaseRegistry (§02-CONTEXT lesson #3 —
FreezeRegistry / EvidenceSchemaRegistry both mirror PhaseRegistry shape).
"""

from __future__ import annotations

import sys

import pytest
from clawteam.harness.evidence_schemas import (
    ArtifactFrontmatterBase,
    get_schema,
    list_registered,
    register_schema,
    reset_registry,
)
from pydantic import Field, ValidationError


class DesignDocFixture(ArtifactFrontmatterBase):
    """Test-local subclass — Phase 3's GstackSprintPlugin ships the real one."""

    artifact_type: str = "design-doc"  # discriminator stable across instances
    sections: list[str] = Field(default_factory=list)


class PlanDocFixture(ArtifactFrontmatterBase):
    artifact_type: str = "plan-doc"


class RetroFixture(ArtifactFrontmatterBase):
    artifact_type: str = "retro"


def setup_function() -> None:
    reset_registry()


def teardown_function() -> None:
    reset_registry()


def test_artifact_frontmatter_base_fields() -> None:
    """Base class carries the five TurnEnvelope-shape fields (§02-CONTEXT lesson #2)."""
    env = ArtifactFrontmatterBase(
        persona="engineer",
        step_label="build:1/3",
        done=False,
        artifact_type="x",
        created_at="2026-04-17T00:00:00Z",
    )
    assert env.persona == "engineer"
    assert env.step_label == "build:1/3"
    assert env.done is False
    assert env.artifact_type == "x"
    assert env.created_at == "2026-04-17T00:00:00Z"


def test_artifact_frontmatter_base_rejects_missing_persona() -> None:
    """All five fields required — missing persona raises ValidationError."""
    with pytest.raises(ValidationError):
        ArtifactFrontmatterBase(  # type: ignore[call-arg]
            step_label="x",
            done=False,
            artifact_type="y",
            created_at="2026-04-17T00:00:00Z",
        )


def test_register_schema_adds_to_registry() -> None:
    """register_schema(name, cls) populates the registry; get_schema returns the class."""
    register_schema("design-doc", DesignDocFixture)
    assert get_schema("design-doc") is DesignDocFixture


def test_register_schema_rejects_duplicate_name() -> None:
    """Duplicate artifact_type name is fatal (mirrors PhaseRegistry D-03 collision rule)."""
    register_schema("design-doc", DesignDocFixture)
    with pytest.raises(ValueError) as exc_info:
        register_schema("design-doc", PlanDocFixture)
    msg = str(exc_info.value)
    assert "design-doc" in msg
    assert "Duplicate" in msg or "duplicate" in msg.lower()


def test_get_schema_returns_none_for_unregistered() -> None:
    """Pitfall #6: caller distinguishes 'unregistered' (None) from validation failure."""
    assert get_schema("no-such-type") is None


def test_reset_registry_clears_entries() -> None:
    """reset_registry() empties the registry — test isolation helper."""
    register_schema("design-doc", DesignDocFixture)
    reset_registry()
    assert get_schema("design-doc") is None


def test_list_registered_returns_all_registered_names() -> None:
    """list_registered() returns the registered artifact_type name set (diagnostics)."""
    register_schema("design-doc", DesignDocFixture)
    register_schema("plan-doc", PlanDocFixture)
    register_schema("retro", RetroFixture)
    names = list_registered()
    assert set(names) == {"design-doc", "plan-doc", "retro"}


def test_plugin_manager_integration_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """Plan 02-01's lazy-import guarded loop now resolves end-to-end.

    Proves the Wave-1 monkey-patched collision test (test_plugin_hooks.py) is
    no longer the only integration surface — the real ``evidence_schemas`` module
    now satisfies the plugin-manager's register_schema call.
    """
    # Ensure no pre-cached stub shadows the real module.
    monkeypatch.delitem(sys.modules, "clawteam.harness.evidence_schemas", raising=False)
    # Re-import so the plugin manager picks up the real module, not a monkey-patched stub.
    import importlib

    import clawteam.harness.evidence_schemas as real_es

    real_es = importlib.reload(real_es)
    real_es.reset_registry()

    from clawteam.plugins.base import HarnessPlugin
    from clawteam.plugins.manager import PluginManager

    class _TestPlugin(HarnessPlugin):
        name = "test-evidence-plugin"

        def on_register(self, ctx: object) -> None:  # required abstract method
            pass

        def contribute_evidence_schemas(self) -> dict[str, type]:
            return {"design-doc": DesignDocFixture}

    from clawteam.harness.phase_registry import reset_registry as reset_phase_registry

    reset_phase_registry()
    try:
        pm = PluginManager()
        pm._instantiate_and_register(_TestPlugin)
        assert real_es.get_schema("design-doc") is DesignDocFixture
    finally:
        real_es.reset_registry()
        reset_phase_registry()

