"""Phase 5 Plan 05-02 Task 3 — GstackSprintPlugin.contribute_evidence_schemas extension.

Red-phase behaviors (per plan):
- Test 1: contribute_evidence_schemas returns EXACTLY 10 keys (6 Phase 3 + 4 Phase 5).
- Test 2: PluginManager registration flows all 10 into EvidenceSchemaRegistry
  without duplicate-key ValueError.
- Test 3-6: Registry-lookup round-trip for each of the four new schemas:
  name -> class -> construct + model_dump_json succeeds.
- Test 7: All 6 Phase 3 keys still register (non-regression guard).

Mirrors tests/test_gstack_plugin.py::test_six_evidence_schemas_registered shape.
"""

from __future__ import annotations

import pytest

from clawteam.harness.evidence_schemas import (
    get_schema,
    reset_registry as reset_schema_registry,
)
from clawteam.harness.phase_registry import reset_registry as reset_phase_registry


def setup_function() -> None:
    reset_phase_registry()
    reset_schema_registry()


def teardown_function() -> None:
    reset_phase_registry()
    reset_schema_registry()


_EXPECTED_TEN: set[str] = {
    "design-doc",
    "plan-doc",
    "test-report",
    "review-report",
    "ship-notes",
    "retro",
    # Phase 5 Plan 05-02:
    "deploy-notes",
    "canary-report",
    "benchmark-report",
    "codex-review",
}


def test_contribute_includes_four_new_keys():
    """contribute_evidence_schemas returns EXACTLY 10 keys — no extras, no missing."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    schemas = plugin.contribute_evidence_schemas()
    assert set(schemas.keys()) == _EXPECTED_TEN, (
        f"expected {_EXPECTED_TEN!r}, got {set(schemas.keys())!r}"
    )
    assert len(schemas) == 10


def test_schemas_registered_via_plugin_manager():
    """PluginManager.register flows all 10 keys into EvidenceSchemaRegistry."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager

    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)  # must not raise duplicate-key ValueError

    for name in _EXPECTED_TEN:
        assert get_schema(name) is not None, f"schema {name!r} missing from registry"


def _register_via_plugin_manager() -> None:
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager

    PluginManager()._instantiate_and_register(GstackSprintPlugin)


def test_deploy_notes_roundtrip_via_registry():
    from clawteam.templates.gstack.schemas import DeployNotes

    _register_via_plugin_manager()
    cls = get_schema("deploy-notes")
    assert cls is DeployNotes
    doc = cls(
        artifact_type="deploy-notes",
        deploy_status="succeeded",
        deploy_url="https://staging.clawteam.dev/sprint-001",
        provider="vercel",
        deployed_at="2026-04-21T12:00:00Z",
        commit_sha="abc1234",
        sprint_id="sprint-001",
        created_at="2026-04-21T12:00:00Z",
    )
    assert doc.model_dump_json()


def test_canary_report_roundtrip_via_registry():
    from clawteam.templates.gstack.schemas import CanaryReport

    _register_via_plugin_manager()
    cls = get_schema("canary-report")
    assert cls is CanaryReport
    doc = cls(
        artifact_type="canary-report",
        canary_status="clean",
        window_seconds=300,
        http_2xx_count=120,
        http_5xx_count=0,
        avg_response_ms=215.3,
        sprint_id="sprint-001",
        created_at="2026-04-21T12:00:00Z",
    )
    assert doc.model_dump_json()


def test_benchmark_report_roundtrip_via_registry():
    from clawteam.templates.gstack.schemas import BenchmarkReport

    _register_via_plugin_manager()
    cls = get_schema("benchmark-report")
    assert cls is BenchmarkReport
    doc = cls(
        artifact_type="benchmark-report",
        benchmark_status="clean",
        lcp_ms=1800.0,
        fid_ms=50.0,
        cls_score=0.05,
        ttfb_ms=200.0,
        dom_loaded_ms=1200.0,
        sprint_id="sprint-001",
        created_at="2026-04-21T12:00:00Z",
    )
    assert doc.model_dump_json()


def test_codex_review_roundtrip_via_registry():
    from clawteam.templates.gstack.schemas import CodexReview

    _register_via_plugin_manager()
    cls = get_schema("codex-review")
    assert cls is CodexReview
    doc = cls(
        artifact_type="codex-review",
        mode="review",
        target="src/foo.py",
        verdict="pass",
        summary="no issues found",
        sprint_id="sprint-001",
        created_at="2026-04-21T12:00:00Z",
    )
    assert doc.model_dump_json()


def test_phase3_keys_still_present():
    """Non-regression: all 6 Phase 3 keys register without duplicate errors."""
    _register_via_plugin_manager()
    for name in (
        "design-doc",
        "plan-doc",
        "test-report",
        "review-report",
        "ship-notes",
        "retro",
    ):
        assert get_schema(name) is not None, f"Phase 3 schema {name!r} regressed"
