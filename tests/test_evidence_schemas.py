"""Tests for clawteam.harness.evidence_schemas — EvidenceSchemaRegistry.

Plan 02-04: singleton registry populated at plugin-load time, keyed by artifact_type.
Mirrors clawteam.harness.phase_registry.PhaseRegistry (§02-CONTEXT lesson #3 —
FreezeRegistry / EvidenceSchemaRegistry both mirror PhaseRegistry shape).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest
from clawteam.harness.evidence_schemas import (
    ArtifactFrontmatterBase,
    get_schema,
    list_registered,
    register_schema,
    reset_registry,
)
from clawteam.team.envelope import parse_frontmatter
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


# ---------------------------------------------------------------------------
# Phase 3 Plan 03-03 — gstack evidence schemas (DesignDoc, PlanDoc, ...)
# ---------------------------------------------------------------------------
#
# The test classes below exercise the six concrete gstack pydantic schemas
# that Phase 3 adds under ``clawteam/templates/gstack/schemas/``. Each class
# owns two things:
#   1. A round-trip test against a ``*-valid.md`` fixture (schema instantiates).
#   2. A rejection test against a ``*-stub-tbd.md`` fixture (ValidationError
#      raised — Pitfall 8 defeat).
#
# Additional per-schema tests cover specific stub-defeating constraints
# (min_length on prose, Literal enums, list arity, hex SHA shape, etc.).
#
# Task 1 (this commit) ships DesignDoc + PlanDoc classes + barrel tests.
# Tasks 2-3 append TestReport / ReviewReport / ShipNotes / Retro classes.

GSTACK_FIXTURES = Path(__file__).parent / "fixtures" / "gstack_artifacts"


def _load_fixture_meta(name: str) -> dict[str, Any]:
    """Read a gstack fixture markdown file and return its parsed frontmatter.

    Guards against path traversal (T-03-12): the ``name`` argument MUST be a
    plain filename — no ``..`` segments, no absolute paths. Raises ValueError
    on violation. Callers pass fixture basenames like ``"design-doc-valid.md"``.
    """
    if ".." in name or "/" in name or name.startswith("."):
        raise ValueError(f"Unsafe fixture name: {name!r} (path traversal guard)")
    raw = (GSTACK_FIXTURES / name).read_text(encoding="utf-8")
    meta, _body = parse_frontmatter(raw)
    return meta


class TestDesignDocSchema:
    def test_valid_fixture_round_trips(self) -> None:
        from clawteam.templates.gstack.schemas import DesignDoc

        doc = DesignDoc(**_load_fixture_meta("design-doc-valid.md"))
        assert doc.artifact_type == "design-doc"
        assert doc.pm_verdict == "proceed"
        assert len(doc.forcing_questions_addressed) == 6

    def test_stub_fixture_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import DesignDoc

        with pytest.raises(ValidationError):
            DesignDoc(**_load_fixture_meta("design-doc-stub-tbd.md"))

    def test_short_problem_statement_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import DesignDoc

        meta = _load_fixture_meta("design-doc-valid.md")
        meta["problem_statement"] = "too short"
        with pytest.raises(ValidationError) as exc_info:
            DesignDoc(**meta)
        assert "problem_statement" in str(exc_info.value)

    def test_invalid_pm_verdict_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import DesignDoc

        meta = _load_fixture_meta("design-doc-valid.md")
        meta["pm_verdict"] = "maybe"
        with pytest.raises(ValidationError):
            DesignDoc(**meta)

    def test_short_forcing_questions_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import DesignDoc

        meta = _load_fixture_meta("design-doc-valid.md")
        meta["forcing_questions_addressed"] = [1, 2, 3]
        with pytest.raises(ValidationError):
            DesignDoc(**meta)


class TestPlanDocSchema:
    def test_valid_fixture_round_trips(self) -> None:
        from clawteam.templates.gstack.schemas import PlanDoc

        doc = PlanDoc(**_load_fixture_meta("plan-doc-valid.md"))
        assert doc.artifact_type == "plan-doc"
        assert len(doc.tasks) >= 1
        assert doc.plan_owner == "eng-mgr"

    def test_stub_fixture_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import PlanDoc

        with pytest.raises(ValidationError):
            PlanDoc(**_load_fixture_meta("plan-doc-stub-tbd.md"))


class TestGstackBarrelExports:
    def test_design_doc_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import DesignDoc as BarrelDesignDoc
        from clawteam.templates.gstack.schemas.design_doc import DesignDoc as ModuleDesignDoc

        assert BarrelDesignDoc is ModuleDesignDoc

    def test_plan_doc_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import PlanDoc as BarrelPlanDoc
        from clawteam.templates.gstack.schemas.plan_doc import PlanDoc as ModulePlanDoc

        assert BarrelPlanDoc is ModulePlanDoc

    def test_fixture_path_traversal_guarded(self) -> None:
        """T-03-12: _load_fixture_meta must reject ``..`` and absolute paths."""
        with pytest.raises(ValueError, match="Unsafe fixture name"):
            _load_fixture_meta("../../../etc/passwd")
        with pytest.raises(ValueError, match="Unsafe fixture name"):
            _load_fixture_meta("/etc/passwd")


# ---------------------------------------------------------------------------
# Phase 3 Plan 03-03 Task 2 — TestReport + ReviewReport schemas
# ---------------------------------------------------------------------------


class TestTestReportSchema:
    def test_valid_fixture_round_trips(self) -> None:
        from clawteam.templates.gstack.schemas import TestReport

        doc = TestReport(**_load_fixture_meta("test-report-valid.md"))
        assert doc.artifact_type == "test-report"
        assert doc.test_command.startswith("pytest")
        assert doc.passed >= 0
        assert doc.qa_mode == "qa"

    def test_stub_fixture_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import TestReport

        with pytest.raises(ValidationError):
            TestReport(**_load_fixture_meta("test-report-stub-tbd.md"))

    def test_empty_test_command_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import TestReport

        meta = _load_fixture_meta("test-report-valid.md")
        meta["test_command"] = ""
        with pytest.raises(ValidationError):
            TestReport(**meta)

    def test_short_output_excerpt_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import TestReport

        meta = _load_fixture_meta("test-report-valid.md")
        meta["output_excerpt"] = "too short"
        with pytest.raises(ValidationError):
            TestReport(**meta)

    def test_negative_passed_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import TestReport

        meta = _load_fixture_meta("test-report-valid.md")
        meta["passed"] = -1
        with pytest.raises(ValidationError):
            TestReport(**meta)


class TestReviewReportSchema:
    def test_valid_fixture_round_trips(self) -> None:
        from clawteam.templates.gstack.schemas import ReviewReport

        doc = ReviewReport(**_load_fixture_meta("review-report-valid.md"))
        assert doc.artifact_type == "review-report"
        assert len(doc.review_sha) >= 7
        assert doc.verdict in ("approved", "rejected", "needs-revision", "superseded")
        assert len(doc.findings) >= 1

    def test_stub_fixture_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import ReviewReport

        with pytest.raises(ValidationError):
            ReviewReport(**_load_fixture_meta("review-report-stub-tbd.md"))

    def test_short_review_sha_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import ReviewReport

        meta = _load_fixture_meta("review-report-valid.md")
        meta["review_sha"] = "abc"
        with pytest.raises(ValidationError):
            ReviewReport(**meta)

    def test_non_hex_review_sha_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import ReviewReport

        meta = _load_fixture_meta("review-report-valid.md")
        meta["review_sha"] = "notahexsha!"
        with pytest.raises(ValidationError):
            ReviewReport(**meta)

    def test_invalid_verdict_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import ReviewReport

        meta = _load_fixture_meta("review-report-valid.md")
        meta["verdict"] = "ship-it-anyway"
        with pytest.raises(ValidationError):
            ReviewReport(**meta)

    def test_empty_findings_rejected(self) -> None:
        from clawteam.templates.gstack.schemas import ReviewReport

        meta = _load_fixture_meta("review-report-valid.md")
        meta["findings"] = []
        with pytest.raises(ValidationError):
            ReviewReport(**meta)


class TestGstackBarrelExportsTask2:
    def test_test_report_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import TestReport as BarrelTestReport
        from clawteam.templates.gstack.schemas.test_report import (
            TestReport as ModuleTestReport,
        )

        assert BarrelTestReport is ModuleTestReport

    def test_review_report_importable_from_barrel(self) -> None:
        from clawteam.templates.gstack.schemas import ReviewReport as BarrelReviewReport
        from clawteam.templates.gstack.schemas.review_report import (
            ReviewReport as ModuleReviewReport,
        )

        assert BarrelReviewReport is ModuleReviewReport

