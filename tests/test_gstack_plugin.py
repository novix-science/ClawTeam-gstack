"""GstackSprintPlugin wiring tests (Phase 3 Plan 03-07).

Covers TEAM-04 (leader-role enforcement via ``advance_phase(actor=)``),
SPRINT-06 (Reflect-phase /learn placeholder), and cross-template isolation
(T-07-01 HIGH mitigation — gstack hooks fire ONLY for gstack teams).

All tests are active in 03-07 (Wave 0 scaffolded them as skipped stubs).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

# Phase-registry reset pattern mirrors tests/test_plugin_hooks.py — keeps the
# plugin-load registry isolated between tests. Evidence-schema registry also
# reset so `contribute_evidence_schemas` registrations don't collide with
# residue from other test modules that call PluginManager.
from clawteam.harness.evidence_schemas import reset_registry as reset_schema_registry
from clawteam.harness.phase_registry import reset_registry as reset_phase_registry


def setup_function() -> None:
    """Reset both registries before each test (Phase 1 RFC 001 §4.2 pattern)."""
    try:
        reset_phase_registry()
    except Exception:  # pragma: no cover — belt-and-suspenders
        pass
    try:
        reset_schema_registry()
    except Exception:  # pragma: no cover
        pass


def teardown_function() -> None:
    """Reset after each test so leaking registrations don't poison the next."""
    try:
        reset_phase_registry()
    except Exception:  # pragma: no cover
        pass
    try:
        reset_schema_registry()
    except Exception:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# Phase registration + schema registration (stateless hooks)
# ---------------------------------------------------------------------------


def test_seven_phases_registered():
    """contribute_phases returns the 7 gstack phases in canonical order."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    phases = plugin.contribute_phases()
    assert phases == ["think", "plan", "build", "review", "test", "ship", "reflect"], (
        f"expected 7 phases in canonical order, got {phases}"
    )


def test_seven_phases_registered_in_order():
    """Plugin registers all 7 gstack phases via PluginManager -> PhaseRegistry."""
    from clawteam.plugins.gstack_sprint_plugin import GSTACK_PHASES, GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager

    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)
    from clawteam.harness.phase_registry import get_registry

    assert get_registry().ordered_names() == GSTACK_PHASES


def test_six_schemas_registered():
    """contribute_evidence_schemas includes the 6 Phase 3 artifact discriminators.

    Phase 5 Plan 05-02 extended the dict to 10 keys (adds deploy-notes /
    canary-report / benchmark-report / codex-review); full 10-key surface
    tested in tests/test_evidence_schemas_phase5.py. This test guards the
    Phase 3 subset as a BC anchor.
    """
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.templates.gstack.schemas import (
        DesignDoc,
        PlanDoc,
        Retro,
        ReviewReport,
        ShipNotes,
        TestReport,
    )

    plugin = GstackSprintPlugin()
    schemas = plugin.contribute_evidence_schemas()
    phase3_expected = {
        "design-doc", "plan-doc", "test-report", "review-report", "ship-notes", "retro",
    }
    assert phase3_expected.issubset(set(schemas.keys()))
    assert schemas["design-doc"] is DesignDoc
    assert schemas["plan-doc"] is PlanDoc
    assert schemas["test-report"] is TestReport
    assert schemas["review-report"] is ReviewReport
    assert schemas["ship-notes"] is ShipNotes
    assert schemas["retro"] is Retro


def test_six_evidence_schemas_registered():
    """Plugin contributes all six gstack artifact schemas via Phase 2 registry."""
    from clawteam.harness.evidence_schemas import get_schema, reset_registry
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager

    reset_registry()
    PluginManager()._instantiate_and_register(GstackSprintPlugin)
    for name in [
        "design-doc",
        "plan-doc",
        "test-report",
        "review-report",
        "ship-notes",
        "retro",
    ]:
        assert get_schema(name) is not None


# ---------------------------------------------------------------------------
# contribute_prompts + path-traversal guard (T-07-02)
# ---------------------------------------------------------------------------


def test_prompts_resolve_for_all_eleven_roles():
    """All 11 gstack roles return prompt content with the SIGNATURE line."""
    from clawteam.plugins.gstack_sprint_plugin import GSTACK_ROLES, GstackSprintPlugin

    plugin = GstackSprintPlugin()
    assert len(GSTACK_ROLES) == 11
    for role in GSTACK_ROLES:
        content = plugin.contribute_prompts("plan", role)
        assert f"SIGNATURE: gstack-role:{role}" in content, (
            f"role {role!r} prompt missing SIGNATURE line; got {content[:200]!r}"
        )

    # Non-gstack role returns "" (BC for other templates)
    assert plugin.contribute_prompts("plan", "tech-lead") == ""
    assert plugin.contribute_prompts("plan", "researcher") == ""


def test_prompts_reject_path_traversal():
    """Path-traversal role payloads return "" without touching disk (T-07-02)."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    assert plugin.contribute_prompts("plan", "../etc/passwd") == ""
    assert plugin.contribute_prompts("plan", "..") == ""
    assert plugin.contribute_prompts("plan", "/abs/path") == ""
    assert plugin.contribute_prompts("plan", "pm/../ceo") == ""


# ---------------------------------------------------------------------------
# Leader-role binding (03-01 advance_phase actor check; TEAM-04)
# ---------------------------------------------------------------------------


def test_only_ceo_advances_phase():
    """SprintConductor.advance_phase must accept actor= parameter (03-01 wiring).

    Signature regression test — deeper integration test ships in 03-09.
    """
    import inspect

    from clawteam.sprint.conductor import SprintConductor

    sig = inspect.signature(SprintConductor.advance_phase)
    assert "actor" in sig.parameters, (
        "03-01 must have added `actor: str` parameter to advance_phase"
    )
    assert sig.parameters["actor"].default == "", (
        "03-01's `actor` parameter must default to empty string (preserves Phase 2 callers)"
    )


# ---------------------------------------------------------------------------
# Reflect-phase /learn stub (SPRINT-06 + D-09)
# ---------------------------------------------------------------------------


def _write_valid_retro(tmp_path, team_name: str, sprint_id: str) -> None:
    """Drop a valid retro.md under the expected sprint artifacts dir."""
    retro_path = tmp_path / "teams" / team_name / "sprints" / sprint_id / "artifacts" / "retro.md"
    retro_path.parent.mkdir(parents=True, exist_ok=True)
    retro_path.write_text(
        "---\n"
        "artifact_type: retro\n"
        "personas:\n"
        "  - eng-mgr\n"
        "  - ceo\n"
        "  - engineer\n"
        "what_worked:\n"
        "  - Structured sprint\n"
        "what_failed:\n"
        "  - Nothing blocking\n"
        "key_lessons:\n"
        "  - Ship the stub first\n"
        f"sprint_id: '{sprint_id}'\n"
        "created_at: '2026-04-20T12:00:00Z'\n"
        "---\n"
        "# Retro body.\n"
        "\n"
        "Everything we learned.\n",
        encoding="utf-8",
    )


def test_reflect_phase_learn_stub_writes_placeholder(tmp_path, monkeypatch):
    """On Reflect-phase entry for a gstack team, plugin writes _phase6_pending/<sprint>-retro.json."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    team_name = "acme"
    sprint_id = "sprint001"

    # Redirect get_data_dir everywhere the plugin looks it up (the module-level
    # symbol is imported locally inside plugin internals so monkeypatch has to
    # target the original module).
    import clawteam.team.models as team_models
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)
    # Redirect team-template lookup via _load_config
    import clawteam.team.manager as team_manager
    monkeypatch.setattr(
        team_manager,
        "_load_config",
        lambda name: SimpleNamespace(template="gstack", leader_role="ceo"),
    )

    # Drop a valid retro.md
    _write_valid_retro(tmp_path, team_name, sprint_id)

    plugin = GstackSprintPlugin()
    plugin._ctx = SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None))

    # Pass sprint_id directly on the event (plugin supports this path) so the
    # handler doesn't need a full SprintState round-trip to find the sprint.
    event = SimpleNamespace(
        to_phase="reflect",
        team_name=team_name,
        sprint_id=sprint_id,
    )
    plugin._on_phase_transition(event)

    placeholder = tmp_path / "teams" / team_name / "_phase6_pending" / f"{sprint_id}-retro.json"
    assert placeholder.is_file(), f"expected {placeholder} to exist"
    data = json.loads(placeholder.read_text(encoding="utf-8"))
    assert data["feature_flag"] == "phase6_learn_pending"
    assert data["sprint_id"] == sprint_id
    assert data["team_name"] == team_name
    assert "eng-mgr" in data["personas"]
    assert "Retro body" in data["retro_body"]


def test_plugin_inert_for_non_gstack_team(tmp_path, monkeypatch):
    """T-07-01 HIGH mitigation: non-gstack team's Reflect phase MUST NOT write placeholder."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    team_name = "mixed-team"
    sprint_id = "sprintxyz"

    import clawteam.team.models as team_models
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)
    import clawteam.team.manager as team_manager
    monkeypatch.setattr(
        team_manager,
        "_load_config",
        lambda name: SimpleNamespace(template="software-dev", leader_role=""),
    )

    plugin = GstackSprintPlugin()
    plugin._ctx = SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None))
    event = SimpleNamespace(
        to_phase="reflect",
        team_name=team_name,
        sprint_id=sprint_id,
    )
    plugin._on_phase_transition(event)

    pending_dir = tmp_path / "teams" / team_name / "_phase6_pending"
    assert not pending_dir.exists() or not list(pending_dir.glob("*.json")), (
        "plugin MUST NOT write _phase6_pending/ for non-gstack templates (T-07-01)"
    )


# ---------------------------------------------------------------------------
# Phase 4 Plan 11 — plugin extensions (contribute_review_routers,
# contribute_verification_pairs, contribute_gates, decorrelation supplement)
# ---------------------------------------------------------------------------


def _fresh_plugin():
    """Fresh GstackSprintPlugin with minimal ctx wiring for Phase 4 tests."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    plugin.on_register(
        SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None))
    )
    return plugin


def test_contribute_review_routers_returns_gstack_router():
    from clawteam.harness.gstack_review_router import GstackReviewRouter

    plugin = _fresh_plugin()
    routers = plugin.contribute_review_routers()
    assert len(routers) == 1
    assert isinstance(routers[0], GstackReviewRouter)


def test_contribute_review_routers_router_loads_real_gstack_rules():
    plugin = _fresh_plugin()
    router = plugin.contribute_review_routers()[0]
    # Smoke: match a UI file pulls designer + reviewer floor.
    state = SimpleNamespace(workspace_branch="", review_sha="")
    result = router.match(["src/components/Button.tsx"], state)
    assert "reviewer" in result
    assert "designer" in result


def test_contribute_verification_pairs_returns_2_pairs():
    plugin = _fresh_plugin()
    pairs = plugin.contribute_verification_pairs()
    assert len(pairs) == 2
    phases = sorted(p.phase for p in pairs)
    assert phases == ["review", "test"]


def test_contribute_verification_pairs_qa_engineer_pair():
    plugin = _fresh_plugin()
    pairs = plugin.contribute_verification_pairs()
    qa_pair = next(p for p in pairs if p.phase == "test")
    assert qa_pair.source_artifact == "test-report.md"
    assert qa_pair.target_artifact == "build-report.md"
    assert "verify_test_report_matches_engineer_output" in qa_pair.verifier_dotted_path


def test_contribute_verification_pairs_reviewer_designer_pair():
    plugin = _fresh_plugin()
    pairs = plugin.contribute_verification_pairs()
    rev_pair = next(p for p in pairs if p.phase == "review")
    assert rev_pair.source_artifact == "design-doc.md"
    assert "verify_design_doc_covers_forcing_questions" in rev_pair.verifier_dotted_path


def test_contribute_gates_attaches_ship_approval_gate():
    from clawteam.harness.ship_approval_gate import ShipApprovalGate

    plugin = _fresh_plugin()
    gates = plugin.contribute_gates()
    assert "ship" in gates
    assert any(isinstance(g, ShipApprovalGate) for g in gates["ship"])


def test_contribute_phase_requirements_declares_artifact_contract():
    plugin = _fresh_plugin()
    requirements = plugin.contribute_phase_requirements()

    assert requirements["think"] == ["delegation.json"]
    assert requirements["plan"] == ["architecture-lock.md"]
    assert requirements["build"] == ["diff.patch"]
    assert requirements["review"] == ["review-report.md"]
    assert requirements["test"] == ["test-report.json"]
    assert requirements["ship"] == ["ship-approval.md"]
    assert requirements["reflect"] == ["retro.md"]


def test_plugin_manager_aggregates_phase_requirements():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager

    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)

    assert pm.get_phase_requirements("think") == ["delegation.json"]
    assert pm.get_phase_requirements("ship") == ["ship-approval.md"]
    assert pm.get_phase_requirements("unknown") == []


def test_phase_contract_artifact_schemas_registered():
    from clawteam.harness.evidence_schemas import get_schema
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager

    PluginManager()._instantiate_and_register(GstackSprintPlugin)

    assert get_schema("delegation") is not None
    assert get_schema("architecture-lock") is not None
    assert get_schema("diff") is not None
    assert get_schema("ship_approval") is not None


def test_review_prompts_append_decorrelation_supplement():
    plugin = _fresh_plugin()
    supplemented = plugin.contribute_prompts(phase="review", role="designer")
    # Should contain both base + supplement markers.
    assert "rubric-first" in supplemented  # from review/designer.md
    # Should also contain base designer content (SIGNATURE trailer).
    assert "gstack-role:designer" in supplemented


def test_review_prompts_no_supplement_for_non_decorrelation_role():
    plugin = _fresh_plugin()
    result = plugin.contribute_prompts(phase="review", role="pm")
    # pm is not a decorrelation role — supplement not appended.
    assert "PHASE 4 REVIEW DECORRELATION SUPPLEMENT" not in result


def test_non_review_phase_no_supplement():
    plugin = _fresh_plugin()
    result = plugin.contribute_prompts(phase="think", role="designer")
    # Base only.
    assert "PHASE 4 REVIEW DECORRELATION SUPPLEMENT" not in result


def test_review_prompts_all_decorrelation_roles_have_supplements():
    plugin = _fresh_plugin()
    for role in ("reviewer", "designer", "security", "dx-lead"):
        r = plugin.contribute_prompts(phase="review", role=role)
        assert "PHASE 4 REVIEW DECORRELATION SUPPLEMENT" in r, (
            f"role={role} missing supplement"
        )


def test_decorrelation_file_budget_under_2kb():
    """D-07: each prompts/review/<role>.md ≤ 2048 bytes."""
    from pathlib import Path

    prompts_dir = (
        Path(__file__).resolve().parent.parent
        / "clawteam"
        / "templates"
        / "gstack"
        / "prompts"
        / "review"
    )
    for role in ("reviewer", "designer", "security", "dx-lead"):
        size = (prompts_dir / f"{role}.md").stat().st_size
        assert size <= 2048, f"review/{role}.md is {size} bytes (budget 2048)"


def test_verifier_dotted_paths_importable():
    """Every VerificationPair.verifier_dotted_path resolves to a callable."""
    import importlib

    plugin = _fresh_plugin()
    for pair in plugin.contribute_verification_pairs():
        module_path, _, attr = pair.verifier_dotted_path.rpartition(".")
        module = importlib.import_module(module_path)
        verifier = getattr(module, attr, None)
        assert callable(verifier), f"{pair.verifier_dotted_path} not importable"


def test_non_gstack_template_does_not_load_gstack_plugin(tmp_path, monkeypatch):
    """Pitfall 14 cross-template: spawning non-gstack template doesn't trigger gstack hooks.

    03-09 ships the full 6-template regression; here we just verify that the
    event handler itself is no-op when the TeamConfig.template != 'gstack'.
    This is the core invariant QUALITY-14 + T-07-01 rest on.
    """
    import clawteam.team.models as team_models
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    monkeypatch.setattr(team_models, "get_data_dir", lambda: tmp_path)
    import clawteam.team.manager as team_manager

    # Exercise all 6 existing template names; none should trigger the write.
    for template_name in [
        "software-dev", "hedge-fund", "code-review",
        "harness-default", "research-paper", "strategy-room",
    ]:
        monkeypatch.setattr(
            team_manager,
            "_load_config",
            lambda name, _tn=template_name: SimpleNamespace(
                template=_tn, leader_role=""
            ),
        )
        plugin = GstackSprintPlugin()
        plugin._ctx = SimpleNamespace(bus=SimpleNamespace(subscribe=lambda *a, **k: None))
        event = SimpleNamespace(
            to_phase="reflect",
            team_name=f"team-{template_name}",
            sprint_id="sprintzzz",
        )
        plugin._on_phase_transition(event)
        pending = tmp_path / "teams" / f"team-{template_name}" / "_phase6_pending"
        assert not pending.exists() or not list(pending.glob("*.json")), (
            f"plugin wrote placeholder for template={template_name} — Pitfall 14 regression"
        )
