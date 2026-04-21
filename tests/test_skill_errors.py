"""Tests for skill-dispatch error hierarchy (Phase 5 Wave 0, Plan 05-01 Task 1).

Behaviors:
- SkillError is a subclass of Exception
- SkillUnavailable, SkillNotPermitted, SkillPreconditionError subclass SkillError
- SkillUnavailable carries binary + install_hint attrs; str(exc) contains both
"""

from __future__ import annotations

from clawteam.plugins.skill_errors import (
    SkillError,
    SkillNotPermitted,
    SkillPreconditionError,
    SkillUnavailable,
)


def test_skillunavailable_message():
    exc = SkillUnavailable(
        skill="/codex",
        binary="codex",
        install_hint="npm install -g @openai/codex",
    )
    rendered = str(exc)
    assert "codex" in rendered
    assert "npm install -g @openai/codex" in rendered
    assert exc.binary == "codex"
    assert exc.install_hint == "npm install -g @openai/codex"
    assert exc.skill == "/codex"


def test_error_hierarchy():
    assert issubclass(SkillError, Exception)
    assert issubclass(SkillUnavailable, SkillError)
    assert issubclass(SkillNotPermitted, SkillError)
    assert issubclass(SkillPreconditionError, SkillError)


def test_skill_error_base_attrs():
    exc = SkillError(skill="/x", role="engineer", message="boom")
    assert exc.skill == "/x"
    assert exc.role == "engineer"
    assert exc.message == "boom"


def test_skill_not_permitted_fields():
    exc = SkillNotPermitted(
        skill="/codex",
        role="shipper",
        message="role 'shipper' not permitted",
    )
    assert exc.skill == "/codex"
    assert exc.role == "shipper"
    assert "shipper" in str(exc)
