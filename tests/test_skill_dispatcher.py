"""Tests for SkillDispatcher (Phase 5 Wave 0, Plan 05-01 Task 1).

Behaviors:
- dispatch() raises SkillNotPermitted when role not in registration.roles
- dispatch() calls tool_available() if present; raises SkillUnavailable with install_hint when False
- dispatch() forwards ctx/role/args to handler and returns result on success
- dispatch() raises SkillError with 'unknown skill' when skill_name not registered
"""

from __future__ import annotations

import pytest

from clawteam.plugins.skill_dispatcher import SkillDispatcher
from clawteam.plugins.skill_errors import (
    SkillError,
    SkillNotPermitted,
    SkillUnavailable,
)
from clawteam.plugins.skill_registration import SkillRegistration


def _make_dispatcher(*regs: SkillRegistration) -> SkillDispatcher:
    return SkillDispatcher({r.name: r for r in regs})


def test_dispatch_raises_not_permitted():
    reg = SkillRegistration(
        name="/codex",
        roles=frozenset({"engineer"}),
        handler=lambda ctx, role, args: "ok",
    )
    dispatcher = _make_dispatcher(reg)
    with pytest.raises(SkillNotPermitted) as info:
        dispatcher.dispatch(ctx=None, skill_name="/codex", role="shipper", args={})
    assert info.value.role == "shipper"
    assert info.value.skill == "/codex"


def test_dispatch_raises_unavailable():
    reg = SkillRegistration(
        name="/codex",
        roles=frozenset({"engineer"}),
        handler=lambda ctx, role, args: "never runs",
        tool_available=lambda: False,
        install_hint="npm install -g codex",
    )
    dispatcher = _make_dispatcher(reg)
    with pytest.raises(SkillUnavailable) as info:
        dispatcher.dispatch(ctx=None, skill_name="/codex", role="engineer", args={})
    assert info.value.install_hint == "npm install -g codex"
    assert info.value.binary == "codex"


def test_dispatch_success():
    captured: dict = {}

    def handler(ctx, *, role, args):
        captured["ctx"] = ctx
        captured["role"] = role
        captured["args"] = args
        return {"ok": True, "role": role}

    reg = SkillRegistration(
        name="/codex",
        roles=frozenset({"engineer"}),
        handler=handler,
        tool_available=lambda: True,
    )
    dispatcher = _make_dispatcher(reg)
    result = dispatcher.dispatch(
        ctx="my-ctx", skill_name="/codex", role="engineer", args={"k": 1}
    )
    assert result == {"ok": True, "role": "engineer"}
    assert captured["ctx"] == "my-ctx"
    assert captured["role"] == "engineer"
    assert captured["args"] == {"k": 1}


def test_dispatch_unknown_skill():
    dispatcher = _make_dispatcher()
    with pytest.raises(SkillError) as info:
        dispatcher.dispatch(ctx=None, skill_name="/missing", role="engineer", args={})
    assert "unknown skill" in str(info.value)


def test_dispatch_no_tool_available_callable_runs_handler():
    # When tool_available is None, handler runs without an availability probe.
    reg = SkillRegistration(
        name="/noop",
        roles=frozenset({"engineer"}),
        handler=lambda ctx, role, args: "ran",
    )
    dispatcher = _make_dispatcher(reg)
    assert dispatcher.dispatch(ctx=None, skill_name="/noop", role="engineer") == "ran"


def test_dispatch_args_defaults_to_empty_dict():
    observed: dict = {}

    def handler(ctx, *, role, args):
        observed["args"] = args
        return None

    reg = SkillRegistration(
        name="/x", roles=frozenset({"engineer"}), handler=handler
    )
    dispatcher = _make_dispatcher(reg)
    dispatcher.dispatch(ctx=None, skill_name="/x", role="engineer")
    assert observed["args"] == {}
