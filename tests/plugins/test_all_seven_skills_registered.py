"""Coverage: all 7 SKILL-13..SKILL-19 requirements map to a plugin-registered skill.

Phase 5 Plan 05-10 Task 1 (Wave 5 — integration + adversarial matrix).

Five test bodies:
- ``test_all_seven_registered``: GstackSprintPlugin.contribute_skills() returns
  exactly the 7 expected names.
- ``test_role_bindings_match_requirements``: each skill's roles matches the
  REQUIREMENTS.md ownership table.
- ``test_plugin_manager_aggregates_without_duplicate_error``: round-trips the
  plugin through PluginManager + get_plugin_skills() without raising the
  duplicate-name ValueError.
- ``test_each_skill_has_handler``: every registration's handler is callable.
- ``test_requirement_coverage``: an explicit REQUIREMENT_MAP asserts every
  SKILL-13..19 id maps to a registered skill name.
"""
from __future__ import annotations

from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin


EXPECTED_SKILLS: dict[str, frozenset[str]] = {
    "/codex": frozenset({"engineer", "reviewer"}),
    "/ship": frozenset({"shipper"}),
    "/land-and-deploy": frozenset({"shipper"}),
    "/document-release": frozenset({"shipper"}),
    "/canary": frozenset({"sre"}),
    "/benchmark": frozenset({"sre"}),
    "/setup-deploy": frozenset({"sre"}),
}

# Explicit requirement → skill-name coverage map. Referenced by SKILL-19
# grep guard in acceptance criteria.
REQUIREMENT_MAP: dict[str, str] = {
    "SKILL-13": "/codex",
    "SKILL-14": "/ship",
    "SKILL-15": "/land-and-deploy",
    "SKILL-16": "/document-release",
    "SKILL-17": "/canary",
    "SKILL-18": "/benchmark",
    "SKILL-19": "/setup-deploy",
}


def test_all_seven_registered() -> None:
    plugin = GstackSprintPlugin()
    skills = plugin.contribute_skills()
    names = sorted(s.name for s in skills)
    assert names == sorted(EXPECTED_SKILLS.keys()), (
        f"expected 7 skills {sorted(EXPECTED_SKILLS.keys())}, got {names}"
    )


def test_role_bindings_match_requirements() -> None:
    plugin = GstackSprintPlugin()
    skills = {s.name: s for s in plugin.contribute_skills()}
    for name, expected_roles in EXPECTED_SKILLS.items():
        actual = skills[name].roles
        assert actual == expected_roles, (
            f"{name}: got {actual}, want {expected_roles}"
        )


def test_plugin_manager_aggregates_without_duplicate_error() -> None:
    """PluginManager round-trip must not raise the duplicate-name ValueError."""
    from clawteam.plugins.manager import PluginManager
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin as _Plugin

    manager = PluginManager()
    manager._instantiate_and_register(_Plugin)
    aggregated = manager.get_plugin_skills()
    assert len(aggregated) == 7
    assert set(aggregated.keys()) == set(EXPECTED_SKILLS.keys())


def test_each_skill_has_handler() -> None:
    plugin = GstackSprintPlugin()
    for s in plugin.contribute_skills():
        assert callable(s.handler), f"{s.name} handler not callable"


def test_requirement_coverage() -> None:
    """Every SKILL-13..SKILL-19 maps to a registered skill."""
    plugin = GstackSprintPlugin()
    registered = {s.name for s in plugin.contribute_skills()}
    for req_id, skill_name in REQUIREMENT_MAP.items():
        assert skill_name in registered, (
            f"{req_id} ({skill_name}) not registered"
        )
