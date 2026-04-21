"""Tests for PluginManager.get_plugin_skills aggregator + HarnessPlugin.contribute_skills hook.

Phase 5 Wave 0, Plan 05-01 Task 1.

Behaviors:
- Two plugins contributing distinct skills aggregate to dict with both keys.
- Two plugins contributing a SkillRegistration with the same name raise ValueError.
- HarnessPlugin.contribute_skills default returns [].
"""

from __future__ import annotations

import pytest

from clawteam.plugins.base import HarnessPlugin
from clawteam.plugins.manager import PluginManager
from clawteam.plugins.skill_registration import SkillRegistration


class _PluginSkillsA(HarnessPlugin):
    name = "plugin-skills-a"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_skills(self):
        return [
            SkillRegistration(
                name="/codex",
                roles=frozenset({"engineer"}),
                handler=lambda ctx, role, args: "a",
            ),
        ]


class _PluginSkillsB(HarnessPlugin):
    name = "plugin-skills-b"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_skills(self):
        return [
            SkillRegistration(
                name="/ship",
                roles=frozenset({"shipper"}),
                handler=lambda ctx, role, args: "b",
            ),
        ]


class _PluginSkillsDuplicate(HarnessPlugin):
    name = "plugin-skills-dup"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_skills(self):
        return [
            SkillRegistration(
                name="/codex",  # same name as _PluginSkillsA
                roles=frozenset({"reviewer"}),
                handler=lambda ctx, role, args: "dup",
            ),
        ]


class _PluginSkillsEmpty(HarnessPlugin):
    name = "plugin-skills-empty"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx
    # does NOT override contribute_skills — should default to []


def test_default_hook_returns_empty():
    plugin = _PluginSkillsEmpty()
    assert plugin.contribute_skills() == []


def test_aggregator_collects_from_all_plugins():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginSkillsA)
    pm._instantiate_and_register(_PluginSkillsB)
    skills = pm.get_plugin_skills()
    assert set(skills.keys()) == {"/codex", "/ship"}
    assert skills["/codex"].roles == frozenset({"engineer"})
    assert skills["/ship"].roles == frozenset({"shipper"})


def test_aggregator_raises_on_duplicate_name():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginSkillsA)
    pm._instantiate_and_register(_PluginSkillsDuplicate)
    with pytest.raises(ValueError) as info:
        pm.get_plugin_skills()
    msg = str(info.value)
    assert "duplicate skill" in msg
    assert "/codex" in msg


def test_empty_plugin_contributes_no_skills():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginSkillsEmpty)
    assert pm.get_plugin_skills() == {}
