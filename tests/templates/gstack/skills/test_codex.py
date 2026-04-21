"""Tests for /codex skill (Phase 5 Plan 05-03, SKILL-13).

Covers three mandatory behaviors per plan D-15:

- Happy path: writes codex-review.md with correct frontmatter.
- Missing-tool: raises SkillUnavailable with install hint (no artifact).
- Adversarial shell metachar: prompt containing ``;rm -rf /`` reaches codex
  as a literal positional/prompt, NEVER spliced through a shell.

Tests 7-9 cover plugin-wiring (GstackSprintPlugin.contribute_skills) and
end-to-end dispatch via SkillDispatcher.
"""

from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_ctx(tmp_path, sprint_id: str = "s1"):
    """Minimal context: sprint_dir + sprint_id are all the handler needs."""
    return SimpleNamespace(sprint_dir=tmp_path, sprint_id=sprint_id)


def _parse_frontmatter(text: str) -> dict:
    """Tiny frontmatter parser — matches handler's hand-rolled emitter shape."""
    assert text.startswith("---\n"), f"no frontmatter: {text!r}"
    end = text.index("\n---\n", 4)
    fm_block = text[4:end]
    out: dict = {}
    for line in fm_block.splitlines():
        if not line.strip():
            continue
        key, _, val = line.partition(": ")
        val = val.strip()
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        elif val == "true":
            val = True
        elif val == "false":
            val = False
        out[key] = val
    return out


# ---------------------------------------------------------------------------
# Task 1: handler behaviors (6 tests)
# ---------------------------------------------------------------------------


def test_codex_happy_path(tmp_path, monkeypatch):
    """Happy path: writes codex-review.md with correct artifact_type/mode/target."""
    import clawteam.templates.gstack.skills.codex.handler as h

    monkeypatch.setattr(h.shutil, "which", lambda _b: "/usr/bin/codex")

    def fake_invoke(command, *, prompt=None, cwd=None, timeout=None, **kwargs):
        return subprocess.CompletedProcess(
            args=list(command), returncode=0, stdout="LGTM\n", stderr=""
        )

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)

    ctx = _fake_ctx(tmp_path)
    result = h.codex_handler(
        ctx,
        role="engineer",
        args={"mode": "review", "target": "src/x.py", "prompt": "review changes"},
    )

    # Return dict.
    assert "artifact_path" in result
    assert result["mode"] == "review"

    artifact = tmp_path / "codex-review.md"
    assert artifact.is_file()
    fm = _parse_frontmatter(artifact.read_text(encoding="utf-8"))
    assert fm["artifact_type"] == "codex-review"
    assert fm["mode"] == "review"
    assert fm["target"] == "src/x.py"


def test_codex_missing_tool(tmp_path, monkeypatch):
    """Missing codex binary → SkillUnavailable with install_hint; no artifact."""
    import clawteam.templates.gstack.skills.codex.handler as h
    from clawteam.plugins.skill_errors import SkillUnavailable

    monkeypatch.setattr(h.shutil, "which", lambda _b: None)

    ctx = _fake_ctx(tmp_path)
    with pytest.raises(SkillUnavailable) as info:
        h.codex_handler(
            ctx,
            role="engineer",
            args={"mode": "review", "target": "x", "prompt": "hi"},
        )
    assert info.value.install_hint == "npm install -g @openai/codex"
    assert info.value.binary == "codex"

    # No artifact should have been written.
    assert not (tmp_path / "codex-review.md").exists()


def test_codex_adversarial_shell_metachar(tmp_path, monkeypatch):
    """Shell metachar in prompt reaches codex as a literal; shell=False.

    D-15 adversarial-input protection. We verify:
    - captured `command` list is literally ``["codex", "exec"]`` (no splicing).
    - the malicious string flows as the ``prompt`` kwarg, not spliced into the argv.
    - kwargs never include ``shell=True`` (invoke_native_cli hard-codes False).
    """
    import clawteam.templates.gstack.skills.codex.handler as h

    captured: dict = {}

    monkeypatch.setattr(h.shutil, "which", lambda _b: "/usr/bin/codex")

    def fake_invoke(command, *, prompt=None, cwd=None, timeout=None, **kwargs):
        captured["command"] = list(command)
        captured["prompt"] = prompt
        captured["shell"] = kwargs.get("shell", "NOT-PASSED")
        return subprocess.CompletedProcess(
            args=list(command), returncode=0, stdout="analysis", stderr=""
        )

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)

    ctx = _fake_ctx(tmp_path)
    h.codex_handler(
        ctx,
        role="engineer",
        args={"mode": "review", "target": "x", "prompt": "; rm -rf /"},
    )

    # Argv is a literal 2-element list — NOT spliced with the malicious string.
    assert captured["command"] == ["codex", "exec"]
    # The malicious string reaches codex as the literal prompt argument, intact.
    assert captured["prompt"] == "; rm -rf /"
    # shell=True is never passed by the handler; invoke_native_cli hard-codes False.
    assert captured["shell"] in ("NOT-PASSED", False)


def test_codex_mode_validation(tmp_path, monkeypatch):
    """Invalid mode fails-fast BEFORE invoking the CLI (cheap-fail)."""
    import clawteam.templates.gstack.skills.codex.handler as h

    invoked: dict = {"called": False}

    def fake_invoke(*args, **kwargs):
        invoked["called"] = True
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(h.shutil, "which", lambda _b: "/usr/bin/codex")
    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)

    ctx = _fake_ctx(tmp_path)
    with pytest.raises((ValueError, Exception)) as info:
        h.codex_handler(
            ctx,
            role="engineer",
            args={"mode": "bogus", "target": "x", "prompt": "hi"},
        )
    # CLI must NOT have been invoked before mode validation rejected.
    assert invoked["called"] is False
    # Rejection message mentions the invalid mode or valid options.
    msg = str(info.value).lower()
    assert "bogus" in msg or "mode" in msg


def test_codex_writes_mode_in_frontmatter(tmp_path, monkeypatch):
    """Adversarial/consultation modes: mode recorded, verdict stays 'n/a'."""
    import clawteam.templates.gstack.skills.codex.handler as h

    monkeypatch.setattr(h.shutil, "which", lambda _b: "/usr/bin/codex")
    monkeypatch.setattr(
        h,
        "invoke_native_cli",
        lambda command, **kwargs: subprocess.CompletedProcess(
            args=list(command), returncode=0, stdout="critique notes", stderr=""
        ),
    )

    ctx = _fake_ctx(tmp_path)
    h.codex_handler(
        ctx,
        role="reviewer",
        args={"mode": "adversarial", "target": "feature-x", "prompt": "red-team it"},
    )

    fm = _parse_frontmatter((tmp_path / "codex-review.md").read_text(encoding="utf-8"))
    assert fm["mode"] == "adversarial"
    # Non-review modes always emit n/a verdict.
    assert fm["verdict"] == "n/a"


def test_tool_available_returns_bool(monkeypatch):
    """tool_available() is a no-arg callable that returns bool."""
    import clawteam.templates.gstack.skills.codex.handler as h

    monkeypatch.setattr(h.shutil, "which", lambda _b: None)
    assert h.tool_available() is False

    monkeypatch.setattr(h.shutil, "which", lambda _b: "/usr/bin/codex")
    assert h.tool_available() is True


# ---------------------------------------------------------------------------
# Task 2: plugin registration + dispatcher wiring (3 tests)
# ---------------------------------------------------------------------------


def test_contribute_skills_includes_codex():
    """GstackSprintPlugin.contribute_skills returns a /codex SkillRegistration."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.skill_registration import SkillRegistration

    regs = GstackSprintPlugin().contribute_skills()
    assert isinstance(regs, list)
    codex_regs = [r for r in regs if r.name == "/codex"]
    assert len(codex_regs) == 1, f"expected exactly one /codex registration; got {regs!r}"
    reg = codex_regs[0]
    assert isinstance(reg, SkillRegistration)
    assert reg.roles == frozenset({"engineer", "reviewer"})
    assert reg.install_hint == "npm install -g @openai/codex"
    # tool_available and handler both present + callable.
    assert callable(reg.handler)
    assert callable(reg.tool_available)


def test_codex_registration_dispatches_through_dispatcher():
    """SkillDispatcher role-gating: designer → SkillNotPermitted."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillNotPermitted

    # Reset registries so repeat runs of this test file are safe.
    try:
        from clawteam.harness.phase_registry import reset_registry as reset_phases
        reset_phases()
    except Exception:
        pass
    try:
        from clawteam.harness.evidence_schemas import reset_registry as reset_schemas
        reset_schemas()
    except Exception:
        pass

    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)
    dispatcher = SkillDispatcher(pm.get_plugin_skills())
    with pytest.raises(SkillNotPermitted):
        dispatcher.dispatch(
            ctx=None, skill_name="/codex", role="designer", args={}
        )


def test_codex_tool_available_integrated(monkeypatch):
    """End-to-end: missing codex → SkillUnavailable via dispatcher + plugin."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillUnavailable

    try:
        from clawteam.harness.phase_registry import reset_registry as reset_phases
        reset_phases()
    except Exception:
        pass
    try:
        from clawteam.harness.evidence_schemas import reset_registry as reset_schemas
        reset_schemas()
    except Exception:
        pass

    # shutil.which is looked up via the handler module's `shutil` binding.
    import clawteam.templates.gstack.skills.codex.handler as h
    monkeypatch.setattr(h.shutil, "which", lambda _b: None)

    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)
    dispatcher = SkillDispatcher(pm.get_plugin_skills())

    with pytest.raises(SkillUnavailable) as info:
        dispatcher.dispatch(
            ctx=None, skill_name="/codex", role="engineer", args={}
        )
    assert "npm install -g @openai/codex" in info.value.install_hint
