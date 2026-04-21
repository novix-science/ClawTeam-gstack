"""Tests for SkillRegistration dataclass (Phase 5 Wave 0, Plan 05-01 Task 1).

Behavior contract (from PLAN.md):
- frozen dataclass (immutable — setting attrs raises FrozenInstanceError)
- roles is frozenset (not list/set)
- required fields: name, roles, handler
- optional fields: tool_available (callable|None), install_hint (str, default "")
"""

from __future__ import annotations

import dataclasses

import pytest

from clawteam.plugins.skill_registration import SkillRegistration


def test_skillregistration_immutable():
    reg = SkillRegistration(
        name="/codex",
        roles=frozenset({"engineer", "reviewer"}),
        handler=lambda **_: None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        reg.name = "/other"  # type: ignore[misc]


def test_roles_is_frozenset():
    reg = SkillRegistration(
        name="/codex",
        roles=frozenset({"engineer"}),
        handler=lambda **_: None,
    )
    assert isinstance(reg.roles, frozenset)


def test_defaults_applied():
    reg = SkillRegistration(
        name="/ship",
        roles=frozenset({"shipper"}),
        handler=lambda **_: None,
    )
    assert reg.tool_available is None
    assert reg.install_hint == ""


def test_optional_fields_roundtrip():
    probe = lambda: True  # noqa: E731
    reg = SkillRegistration(
        name="/land-and-deploy",
        roles=frozenset({"shipper"}),
        handler=lambda **_: None,
        tool_available=probe,
        install_hint="npm install -g vercel",
    )
    assert reg.tool_available is probe
    assert reg.install_hint == "npm install -g vercel"
