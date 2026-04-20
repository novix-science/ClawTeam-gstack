"""Scaffold for Phase 3 Wave 0 (Plan 03-01 Task 3).

Tests currently skipped — Wave 3 (Plan 03-06) unskips them as
`GstackSprintPlugin` ships.

Covers: TEAM-04 (leader-role enforcement via ``advance_phase(actor=)``),
SPRINT-06 (Reflect-phase `/learn` placeholder), cross-template isolation
(gstack hooks fire ONLY when gstack template is loaded).
"""

from __future__ import annotations

import pytest

# Phase-registry reset pattern mirrors tests/test_plugin_hooks.py — keeps the
# plugin-load registry isolated between scaffolded tests when they unskip.
from clawteam.harness.phase_registry import reset_registry as reset_phase_registry


def setup_function() -> None:
    """Reset the phase registry before each test (Phase 1 RFC 001 §4.2 pattern).

    Safe no-op when the registry is already empty.
    """
    try:
        reset_phase_registry()
    except Exception:  # pragma: no cover — belt-and-suspenders
        pass


def teardown_function() -> None:
    """Reset after each test so leaking phase registrations don't poison the next."""
    try:
        reset_phase_registry()
    except Exception:  # pragma: no cover
        pass


@pytest.mark.skip(reason="Wave 3: GstackSprintPlugin ships in 03-06-PLAN")
def test_seven_phases_registered_in_order():
    """Plugin registers all 7 gstack phases in canonical order via PhaseRegistry."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin, GSTACK_PHASES
    from clawteam.plugins.manager import PluginManager

    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)
    from clawteam.harness.phase_registry import get_registry

    assert get_registry().ordered_names() == GSTACK_PHASES


@pytest.mark.skip(reason="Wave 3: GstackSprintPlugin evidence-schema contribution")
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


@pytest.mark.skip(reason="Wave 3: TEAM-04 leader-role enforcement via advance_phase(actor=)")
def test_only_ceo_advances_phase(tmp_path):
    """TEAM-04: seed gstack team with leader_role='ceo'; engineer is rejected, ceo allowed.

    Substrate already shipped in Plan 03-01 Task 2
    (SprintConductor.advance_phase accepts actor=; TeamConfig.leader_role).
    """
    pass


@pytest.mark.skip(reason="Wave 3: SPRINT-06 Reflect-phase placeholder")
def test_reflect_phase_learn_stub_writes_placeholder(tmp_path):
    """SPRINT-06: emitting PhaseTransition(to_phase='reflect') writes
    `_phase6_pending/<sprint_id>-retro.json` under the team data dir.
    Phase 6 backfill scanner (deferred per D-09) consumes whatever's there.
    """
    pass


@pytest.mark.skip(reason="Wave 3: cross-template isolation (Pitfall 14 mitigation)")
def test_non_gstack_template_does_not_load_gstack_plugin():
    """Pitfall 14: spawning a non-gstack template must NOT trigger
    GstackSprintPlugin.on_register — the 6 existing templates stay unaffected.
    """
    pass
