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
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin, GSTACK_PHASES
    from clawteam.plugins.manager import PluginManager

    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)
    from clawteam.harness.phase_registry import get_registry

    assert get_registry().ordered_names() == GSTACK_PHASES


def test_six_schemas_registered():
    """contribute_evidence_schemas keys match the 6 artifact_type discriminators."""
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
    assert set(schemas.keys()) == {
        "design-doc", "plan-doc", "test-report", "review-report", "ship-notes", "retro",
    }
    assert schemas["design-doc"] is DesignDoc
    assert schemas["plan-doc"] is PlanDoc
    assert schemas["test-report"] is TestReport
    assert schemas["review-report"] is ReviewReport
    assert schemas["ship-notes"] is ShipNotes
    assert schemas["retro"] is Retro


def test_six_evidence_schemas_registered():
    """Plugin contributes all six gstack artifact schemas via Phase 2 registry."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager
    from clawteam.harness.evidence_schemas import get_schema, reset_registry

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
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin, GSTACK_ROLES

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


def test_non_gstack_template_does_not_load_gstack_plugin(tmp_path, monkeypatch):
    """Pitfall 14 cross-template: spawning non-gstack template doesn't trigger gstack hooks.

    03-09 ships the full 6-template regression; here we just verify that the
    event handler itself is no-op when the TeamConfig.template != 'gstack'.
    This is the core invariant QUALITY-14 + T-07-01 rest on.
    """
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    import clawteam.team.models as team_models
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
