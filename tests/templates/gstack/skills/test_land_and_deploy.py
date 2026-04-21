"""Tests for /land-and-deploy skill (Plan 05-06, SKILL-15).

Covers:
- Precondition: ship-notes.md with ship_status='succeeded' must exist.
- CI wait: `gh pr checks --watch` happy + timeout paths.
- Deploy: vercel / netlify / fly / custom provider dispatch + URL extraction.
- Health probe: exponential backoff with deploy_verify_timeout_seconds deadline
  (Pitfall 3 defense — handler's own probe precedes EvidenceGate's 10 s HEAD).
- No [deploy] block → deploy.md with deploy_status='pending' + question artifact.
- Role gate: shipper only (T-05-06-06).
- Plugin registration: 4 skills registered total after this plan.
- Shell-injection defense: custom_deploy_cmd passed verbatim to argv
  (shell=False, T-05-06-01).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _make_completed(
    returncode: int = 0, stdout: str = "", stderr: str = "",
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["cmd"], returncode=returncode, stdout=stdout, stderr=stderr,
    )


@dataclass
class _DeployConfig:
    provider: str = "vercel"
    project: str = "my-app"
    custom_deploy_cmd: str = ""


@dataclass
class _CanaryConfig:
    ci_wait_timeout_seconds: int = 1800


@dataclass
class _Template:
    deploy: _DeployConfig | None = None
    canary: _CanaryConfig | None = None


@dataclass
class _Ctx:
    sprint_dir: Path
    workspace_dir: Path
    sprint_id: str = "sprint-001"
    template: _Template | None = None


def _write_ship_notes(
    sprint_dir: Path,
    *,
    ship_status: str = "succeeded",
    pr_url: str = "https://github.com/owner/repo/pull/42",
) -> Path:
    """Write a ship-notes.md with enough frontmatter for the handler's precondition."""
    sprint_dir.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        "artifact_type: 'ship-notes'\n"
        f"ship_status: '{ship_status}'\n"
        f"pr_url: '{pr_url}'\n"
        "---\n\n"
        "ship-notes body\n"
    )
    path = sprint_dir / "ship-notes.md"
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# Test 1: missing ship-notes.md → SkillPreconditionError
# ---------------------------------------------------------------------------


def test_precondition_missing_ship_notes(tmp_path):
    from clawteam.plugins.skill_errors import SkillPreconditionError
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    ctx = _Ctx(
        sprint_dir=tmp_path / "sprint",
        workspace_dir=tmp_path,
        template=_Template(deploy=_DeployConfig()),
    )
    (tmp_path / "sprint").mkdir()

    with pytest.raises(SkillPreconditionError) as exc:
        land_and_deploy_handler(ctx, role="shipper", args={})
    assert "Run /ship first" in exc.value.message


# ---------------------------------------------------------------------------
# Test 2: ship-notes.md exists but ship_status='failed' → SkillPreconditionError
# ---------------------------------------------------------------------------


def test_precondition_ship_failed(tmp_path):
    from clawteam.plugins.skill_errors import SkillPreconditionError
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir, ship_status="failed")

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(deploy=_DeployConfig()),
    )

    with pytest.raises(SkillPreconditionError) as exc:
        land_and_deploy_handler(ctx, role="shipper", args={})
    assert "ship_status" in exc.value.message


# ---------------------------------------------------------------------------
# Test 3: CI wait happy-path (gh returncode=0) → proceeds to deploy
# ---------------------------------------------------------------------------


def test_ci_wait_happy(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    calls: list[list[str]] = []

    def fake_invoke(command, **kwargs):
        calls.append(list(command))
        if command[0] == "git":
            return _make_completed(0, stdout="abc1234def5678\n")
        if command[0] == "gh":
            return _make_completed(0, stdout="All checks pass\n")
        if command[0] == "vercel":
            return _make_completed(
                0, stdout="https://my-app-abc123.vercel.app\n",
            )
        return _make_completed(0)

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(h, "_head_probe", lambda url, timeout=10.0: True)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(
            deploy=_DeployConfig(provider="vercel", project="my-app"),
            canary=_CanaryConfig(ci_wait_timeout_seconds=1800),
        ),
    )
    result = land_and_deploy_handler(ctx, role="shipper", args={})
    assert result["deploy_status"] == "succeeded"
    # gh pr checks --watch was invoked
    assert any(c[:3] == ["gh", "pr", "checks"] for c in calls)


# ---------------------------------------------------------------------------
# Test 4: CI wait TimeoutExpired → deploy.md written with deploy_status='failed'
# ---------------------------------------------------------------------------


def test_ci_wait_timeout(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    def fake_invoke(command, **kwargs):
        if command[0] == "git":
            return _make_completed(0, stdout="abc1234\n")
        if command[0] == "gh":
            raise subprocess.TimeoutExpired(cmd=command, timeout=1800)
        return _make_completed(0)

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(
            deploy=_DeployConfig(provider="vercel", project="my-app"),
            canary=_CanaryConfig(ci_wait_timeout_seconds=1800),
        ),
    )
    result = land_and_deploy_handler(ctx, role="shipper", args={})
    assert result["deploy_status"] == "failed"
    assert result["failure_step"] == "ci_timeout"

    # deploy.md must exist with failed status
    deploy_md = sprint_dir / "deploy.md"
    assert deploy_md.exists()
    text = deploy_md.read_text()
    assert "deploy_status: 'failed'" in text
    # URL should be 'pending' since we never got there
    assert "deploy_url: 'pending'" in text


# ---------------------------------------------------------------------------
# Test 5: deploy vercel happy → deploy.md with succeeded + URL extracted
# ---------------------------------------------------------------------------


def test_deploy_vercel_happy(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    deploy_calls: list[list[str]] = []

    def fake_invoke(command, **kwargs):
        deploy_calls.append(list(command))
        if command[0] == "git":
            return _make_completed(0, stdout="abc1234\n")
        if command[0] == "gh":
            return _make_completed(0)
        if command[0] == "vercel":
            return _make_completed(
                0, stdout="Deploying...\nhttps://my-app-abc123.vercel.app\n",
            )
        return _make_completed(0)

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(h, "_head_probe", lambda url, timeout=10.0: True)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(
            deploy=_DeployConfig(provider="vercel", project="my-app"),
            canary=_CanaryConfig(),
        ),
    )
    result = land_and_deploy_handler(ctx, role="shipper", args={})
    assert result["deploy_status"] == "succeeded"
    assert result["deploy_url"] == "https://my-app-abc123.vercel.app"
    # Verify the vercel command was exactly ["vercel", "deploy", "--prod", "--yes"]
    vercel_calls = [c for c in deploy_calls if c[0] == "vercel"]
    assert vercel_calls == [["vercel", "deploy", "--prod", "--yes"]]

    text = (sprint_dir / "deploy.md").read_text()
    assert "provider: 'vercel'" in text
    assert "deploy_status: 'succeeded'" in text


# ---------------------------------------------------------------------------
# Test 6: netlify happy
# ---------------------------------------------------------------------------


def test_deploy_netlify_happy(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    deploy_calls: list[list[str]] = []

    def fake_invoke(command, **kwargs):
        deploy_calls.append(list(command))
        if command[0] == "git":
            return _make_completed(0, stdout="deadbee\n")
        if command[0] == "gh":
            return _make_completed(0)
        if command[0] == "netlify":
            return _make_completed(
                0, stdout="Website URL: https://my-app.netlify.app\n",
            )
        return _make_completed(0)

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(h, "_head_probe", lambda url, timeout=10.0: True)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(
            deploy=_DeployConfig(provider="netlify", project="my-app"),
            canary=_CanaryConfig(),
        ),
    )
    result = land_and_deploy_handler(ctx, role="shipper", args={})
    assert result["deploy_status"] == "succeeded"
    assert result["deploy_url"] == "https://my-app.netlify.app"
    netlify_calls = [c for c in deploy_calls if c[0] == "netlify"]
    assert netlify_calls == [["netlify", "deploy", "--prod"]]


# ---------------------------------------------------------------------------
# Test 7: fly happy
# ---------------------------------------------------------------------------


def test_deploy_fly_happy(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    deploy_calls: list[list[str]] = []

    def fake_invoke(command, **kwargs):
        deploy_calls.append(list(command))
        if command[0] == "git":
            return _make_completed(0, stdout="abc1234\n")
        if command[0] == "gh":
            return _make_completed(0)
        if command[0] == "flyctl":
            return _make_completed(
                0, stdout="deployed to https://my-app.fly.dev\n",
            )
        return _make_completed(0)

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(h, "_head_probe", lambda url, timeout=10.0: True)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(
            deploy=_DeployConfig(provider="fly", project="my-app"),
            canary=_CanaryConfig(),
        ),
    )
    result = land_and_deploy_handler(ctx, role="shipper", args={})
    assert result["deploy_status"] == "succeeded"
    assert result["deploy_url"] == "https://my-app.fly.dev"
    fly_calls = [c for c in deploy_calls if c[0] == "flyctl"]
    assert fly_calls == [["flyctl", "deploy", "--app", "my-app"]]


# ---------------------------------------------------------------------------
# Test 8: custom provider with backoff retries → eventually succeeds
# ---------------------------------------------------------------------------


def test_deploy_custom_happy(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    deploy_calls: list[list[str]] = []

    def fake_invoke(command, **kwargs):
        deploy_calls.append(list(command))
        if command[0] == "git":
            return _make_completed(0, stdout="abc1234\n")
        if command[0] == "gh":
            return _make_completed(0)
        if command[0] == "echo":
            return _make_completed(0, stdout="https://example.invalid\n")
        return _make_completed(0)

    # Probe fails twice, then succeeds.
    probe_counter = {"n": 0}

    def flaky_probe(url, timeout=10.0):
        probe_counter["n"] += 1
        return probe_counter["n"] >= 3

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(h, "_head_probe", flaky_probe)
    # Skip real sleeps to keep test fast
    monkeypatch.setattr(h.time, "sleep", lambda s: None)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(
            deploy=_DeployConfig(
                provider="custom",
                project="my-app",
                custom_deploy_cmd="echo https://example.invalid",
            ),
            canary=_CanaryConfig(),
        ),
    )
    result = land_and_deploy_handler(ctx, role="shipper", args={})
    assert result["deploy_status"] == "succeeded"
    assert result["deploy_url"] == "https://example.invalid"
    # Verify custom command was split via shlex: ["echo", "https://example.invalid"]
    echo_calls = [c for c in deploy_calls if c[0] == "echo"]
    assert echo_calls == [["echo", "https://example.invalid"]]


# ---------------------------------------------------------------------------
# Test 9: adversarial — deploy cmd succeeds, HEAD probe never 2xx, backoff
# deadline hits → deploy_status='failed', no crash (D-15, Pitfall 3).
# ---------------------------------------------------------------------------


def test_deploy_health_probe_timeout_adversarial(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    def fake_invoke(command, **kwargs):
        if command[0] == "git":
            return _make_completed(0, stdout="abc1234\n")
        if command[0] == "gh":
            return _make_completed(0)
        if command[0] == "vercel":
            return _make_completed(
                0, stdout="https://my-app.vercel.app\n",
            )
        return _make_completed(0)

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)
    # Probe NEVER succeeds.
    monkeypatch.setattr(h, "_head_probe", lambda url, timeout=10.0: False)
    monkeypatch.setattr(h.time, "sleep", lambda s: None)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(
            deploy=_DeployConfig(provider="vercel", project="my-app"),
            canary=_CanaryConfig(),
        ),
    )
    result = land_and_deploy_handler(
        ctx, role="shipper",
        args={"deploy_verify_timeout_seconds": 3},
    )
    assert result["deploy_status"] == "failed"
    # deploy.md must still exist + carry the unreachable URL so EvidenceGate can surface it
    text = (sprint_dir / "deploy.md").read_text()
    assert "deploy_status: 'failed'" in text
    assert "https://my-app.vercel.app" in text


# ---------------------------------------------------------------------------
# Test 10: no [deploy] block → deploy.md pending + question artifact emitted
# ---------------------------------------------------------------------------


def test_no_deploy_block_pending(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    def fake_invoke(command, **kwargs):
        if command[0] == "git":
            return _make_completed(0, stdout="abc1234\n")
        return _make_completed(0)

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(deploy=None, canary=_CanaryConfig()),
    )
    result = land_and_deploy_handler(ctx, role="shipper", args={})
    assert result["deploy_status"] == "pending"
    assert result.get("reason") == "no_deploy_block"

    text = (sprint_dir / "deploy.md").read_text()
    assert "deploy_status: 'pending'" in text
    assert "deploy_url: 'pending'" in text

    # Question artifact prompting /setup-deploy
    q_files = list((sprint_dir / "questions").iterdir())
    assert len(q_files) == 1
    assert "setup-deploy" in q_files[0].read_text().lower()


# ---------------------------------------------------------------------------
# Test 11: role-gated — engineer invoking /land-and-deploy → SkillNotPermitted
# ---------------------------------------------------------------------------


def test_role_gated():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillNotPermitted

    plugin = GstackSprintPlugin()
    regs = {s.name: s for s in plugin.contribute_skills()}
    assert "/land-and-deploy" in regs
    dispatcher = SkillDispatcher(regs)
    with pytest.raises(SkillNotPermitted):
        dispatcher.dispatch(
            ctx=None, skill_name="/land-and-deploy",
            role="engineer", args={},
        )


# ---------------------------------------------------------------------------
# Test 12: plugin registers 4 skills including /land-and-deploy
# ---------------------------------------------------------------------------


def test_registered_in_plugin():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    regs = GstackSprintPlugin().contribute_skills()
    names = {s.name for s in regs}
    assert names >= {"/codex", "/ship", "/setup-deploy", "/land-and-deploy"}

    land_reg = next(s for s in regs if s.name == "/land-and-deploy")
    assert land_reg.roles == frozenset({"shipper"})


# ---------------------------------------------------------------------------
# Test 13: shell-injection defense — custom_deploy_cmd with metachars
# stays as SEPARATE argv elements; shell=False at invoke layer prevents harm.
# ---------------------------------------------------------------------------


def test_shell_injection_via_custom_cmd_safe(tmp_path, monkeypatch):
    import clawteam.templates.gstack.skills.land_and_deploy.handler as h
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        land_and_deploy_handler,
    )

    sprint_dir = tmp_path / "sprint"
    _write_ship_notes(sprint_dir)

    captured: dict[str, Any] = {}

    def fake_invoke(command, **kwargs):
        if command[0] == "git":
            return _make_completed(0, stdout="abc1234\n")
        if command[0] == "gh":
            return _make_completed(0)
        if command[0] == "echo":
            # record the actual invocation
            captured["command"] = list(command)
            # stdout won't contain a URL; backoff will fail fast.
            return _make_completed(0, stdout="no url here\n")
        return _make_completed(0)

    monkeypatch.setattr(h, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(h, "_head_probe", lambda url, timeout=10.0: False)
    monkeypatch.setattr(h.time, "sleep", lambda s: None)

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        workspace_dir=tmp_path,
        template=_Template(
            deploy=_DeployConfig(
                provider="custom",
                project="proj",
                custom_deploy_cmd="echo foo; rm -rf /",
            ),
            canary=_CanaryConfig(),
        ),
    )
    # This must NOT raise and must NOT have run `rm` as a shell command.
    land_and_deploy_handler(
        ctx, role="shipper",
        args={"deploy_verify_timeout_seconds": 1},
    )

    # The semicolon and subsequent tokens must be ordinary argv strings, NOT
    # shell-separators. Split via shlex produces:
    #   ["echo", "foo;", "rm", "-rf", "/"]
    assert captured["command"] == ["echo", "foo;", "rm", "-rf", "/"]
