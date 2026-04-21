"""Tests for /ship skill — 5-step pipeline (Phase 5 Plan 05-04, SKILL-14).

Covers:
- Task 1 tests 1-11: step functions (sync_main, run_tests, audit_coverage,
  push, open_pr) — language detection + bootstrap + coverage parse +
  gh availability.
- Task 2 tests 12-18: ship_handler orchestration — happy path, halt on
  first failure, coverage threshold resolution, role gating via dispatcher,
  plugin registration.
"""

from __future__ import annotations

import json
import subprocess
import types
from dataclasses import dataclass
from pathlib import Path

import pytest


# ─────────────────── shared helpers ──────────────────────────────────────

def _make_completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=["cmd"], returncode=returncode, stdout=stdout, stderr=stderr,
    )


@dataclass
class _ShipConfig:
    coverage_threshold: float = 0.5


@dataclass
class _TemplateWithShip:
    ship: _ShipConfig | None = None


@dataclass
class _Ctx:
    sprint_dir: Path
    workspace_dir: Path
    sprint_id: str = "sprint-001"
    branch: str = "feature/x"
    template: _TemplateWithShip | None = None


# ─────────────────── Task 1: step functions ──────────────────────────────


def test_sync_main_fast_forward(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    calls: list[list[str]] = []

    def fake_invoke(command, **kwargs):
        calls.append(list(command))
        return _make_completed(0, stdout="Already up to date.\n")

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    result = steps.sync_main(cwd=tmp_path, branch="feature/x")
    assert result.success is True
    assert result.details.get("synced_onto") == "main"
    # fetch then merge
    assert calls[0][:3] == ["git", "fetch", "origin"]
    assert calls[1][:2] == ["git", "merge"]


def test_sync_main_conflict(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    seq = iter([
        _make_completed(0),  # fetch succeeds
        _make_completed(1, stderr="CONFLICT (content): Merge conflict in foo.py\n"),
    ])

    def fake_invoke(command, **kwargs):
        return next(seq)

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    result = steps.sync_main(cwd=tmp_path, branch="feature/x")
    assert result.success is False
    assert result.details.get("conflict") is True


def test_run_tests_python_pytest(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_ok():\n    assert True\n")

    captured: list[list[str]] = []

    def fake_invoke(command, **kwargs):
        captured.append(list(command))
        return _make_completed(0, stdout="1 passed\n")

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir()
    result = steps.run_tests(cwd=tmp_path, sprint_dir=sprint_dir)
    assert result.success is True
    assert captured, "expected invoke_native_cli to be called"
    assert captured[0][0] == "pytest"


def test_run_tests_bootstrap_when_missing(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')
    # NO tests/ dir

    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir()

    invoked = []

    def fake_invoke(command, **kwargs):
        invoked.append(list(command))
        return _make_completed(0)

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    result = steps.run_tests(cwd=tmp_path, sprint_dir=sprint_dir)
    assert result.success is False
    assert result.details.get("bootstrapped") is True

    smoke = tmp_path / "tests" / "test_smoke.py"
    assert smoke.is_file()
    smoke_body = smoke.read_text()
    assert "smoke test" in smoke_body
    # must contain at least one module-level / function-level assertion
    assert "assert" in smoke_body

    q = sprint_dir / "questions" / "001_flesh_out_smoke_test.md"
    assert q.is_file()

    # bootstrap must NOT run pytest (we halt first)
    assert invoked == []


def test_run_tests_js_bootstrap(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    (tmp_path / "package.json").write_text(json.dumps({
        "name": "demo",
        "devDependencies": {"vitest": "^1.0.0"},
    }))
    # No tests / __tests__ / *.test.ts

    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir()

    monkeypatch.setattr(
        steps, "invoke_native_cli",
        lambda *a, **kw: _make_completed(0),
    )

    result = steps.run_tests(cwd=tmp_path, sprint_dir=sprint_dir)
    assert result.success is False
    assert result.details.get("bootstrapped") is True
    assert (tmp_path / "tests" / "smoke.test.ts").is_file()


def test_audit_coverage_above_threshold(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')

    def fake_invoke(command, **kwargs):
        # write coverage.json as side-effect
        (tmp_path / "coverage.json").write_text(json.dumps({
            "totals": {"percent_covered": 78.5},
            "files": {"src/app.py": {}},
        }))
        return _make_completed(0, stdout="78%\n")

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    result = steps.audit_coverage(cwd=tmp_path, threshold=0.5)
    assert result.success is True
    # round(0.785, 3) == 0.785
    assert result.details["coverage"] == pytest.approx(0.785)
    assert result.details["threshold"] == 0.5


def test_audit_coverage_below_threshold(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')

    def fake_invoke(command, **kwargs):
        (tmp_path / "coverage.json").write_text(json.dumps({
            "totals": {"percent_covered": 30.0},
        }))
        return _make_completed(0)

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    result = steps.audit_coverage(cwd=tmp_path, threshold=0.5)
    assert result.success is False
    assert result.details["coverage"] == pytest.approx(0.30)
    assert result.details["threshold"] == 0.5


def test_audit_coverage_binary_files_skipped_adversarial(tmp_path, monkeypatch):
    """D-15: coverage.json with binary-file `not_coverable` list must not crash parser."""
    from clawteam.templates.gstack.skills.ship import steps

    (tmp_path / "pyproject.toml").write_text('[project]\nname = "demo"\n')

    binary_entries = [f"assets/img_{i:03d}.bin" for i in range(50)]

    def fake_invoke(command, **kwargs):
        (tmp_path / "coverage.json").write_text(json.dumps({
            "totals": {"percent_covered": 72.0},
            "files": {"src/app.py": {"summary": {"percent_covered": 72.0}}},
            "not_coverable": binary_entries,
            "meta": {"version": "7.x"},
        }))
        return _make_completed(0)

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    result = steps.audit_coverage(cwd=tmp_path, threshold=0.5)
    # should not crash AND should extract percent_covered
    assert result.success is True
    assert result.details["coverage"] == pytest.approx(0.72)


def test_push_dispatch_invokes_git_push(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    captured: list[list[str]] = []

    def fake_invoke(command, **kwargs):
        captured.append(list(command))
        return _make_completed(0)

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    result = steps.push(cwd=tmp_path, branch="feature/x")
    assert result.success is True
    assert captured[0][:5] == ["git", "push", "-u", "origin", "feature/x"]


def test_open_pr_uses_gh_cli(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import steps

    monkeypatch.setattr(steps.shutil, "which", lambda name: "/usr/bin/gh" if name == "gh" else None)

    def fake_invoke(command, **kwargs):
        assert command[:3] == ["gh", "pr", "create"]
        return _make_completed(
            0,
            stdout="Creating pull request for feature/x into main in org/repo\n"
                   "https://github.com/org/repo/pull/42\n",
        )

    monkeypatch.setattr(steps, "invoke_native_cli", fake_invoke)

    result = steps.open_pr(cwd=tmp_path, title="Feat", body="body")
    assert result.success is True
    assert result.details.get("pr_url") == "https://github.com/org/repo/pull/42"


def test_open_pr_missing_gh(tmp_path, monkeypatch):
    from clawteam.plugins.skill_errors import SkillUnavailable
    from clawteam.templates.gstack.skills.ship import steps

    monkeypatch.setattr(steps.shutil, "which", lambda name: None)

    with pytest.raises(SkillUnavailable) as exc:
        steps.open_pr(cwd=tmp_path, title="T", body="B")
    assert "gh" in exc.value.install_hint.lower()


# ─────────────────── Task 2: handler orchestration ───────────────────────


def _fake_step_factory(success: bool, details: dict | None = None):
    """Return a function with the sync_main / run_tests / etc. signature."""
    from clawteam.templates.gstack.skills.ship.steps import StepResult

    def fake(*args, **kwargs):
        return StepResult(success=success, details=dict(details or {}))

    return fake


def _install_happy_path(monkeypatch, module):
    from clawteam.templates.gstack.skills.ship.steps import StepResult

    monkeypatch.setattr(module, "sync_main",
        lambda cwd, branch, **kw: StepResult(True, {"synced_onto": "main"}))
    monkeypatch.setattr(module, "run_tests",
        lambda cwd, sprint_dir, **kw: StepResult(True, {"language": "python", "exit_code": 0}))
    monkeypatch.setattr(module, "audit_coverage",
        lambda cwd, threshold, **kw: StepResult(
            True, {"coverage": 0.78, "threshold": threshold, "language": "python"}))
    monkeypatch.setattr(module, "push",
        lambda cwd, branch, **kw: StepResult(True, {"branch": branch}))
    monkeypatch.setattr(module, "open_pr",
        lambda cwd, title, body, **kw: StepResult(
            True, {"pr_url": "https://github.com/org/repo/pull/99"}))


def test_ship_handler_happy_path(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import handler

    monkeypatch.setattr(handler, "gh_available", lambda: True)
    _install_happy_path(monkeypatch, handler)

    sprint_dir = tmp_path / "sprint-001"
    sprint_dir.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    ctx = _Ctx(sprint_dir=sprint_dir, workspace_dir=workspace)

    out = handler.ship_handler(
        ctx, role="shipper",
        args={"title": "Feat X", "body": "body", "branch": "feature/x"},
    )
    assert out["ship_status"] == "succeeded"
    assert Path(out["artifact_path"]) == sprint_dir / "ship-notes.md"

    body = (sprint_dir / "ship-notes.md").read_text()
    assert "ship_status: 'succeeded'" in body
    # steps_completed list contains all 5 step names
    assert "sync" in body and "test" in body and "coverage" in body and "push" in body
    assert "pr" in body
    assert "https://github.com/org/repo/pull/99" in body


def test_ship_handler_halts_on_first_failure(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import handler
    from clawteam.templates.gstack.skills.ship.steps import StepResult

    monkeypatch.setattr(handler, "gh_available", lambda: True)

    call_counter = {"audit_coverage": 0, "push": 0, "open_pr": 0}

    monkeypatch.setattr(handler, "sync_main",
        lambda cwd, branch, **kw: StepResult(True, {"synced_onto": "main"}))
    monkeypatch.setattr(handler, "run_tests",
        lambda cwd, sprint_dir, **kw: StepResult(False, {"exit_code": 3}))

    def _audit(*a, **kw):
        call_counter["audit_coverage"] += 1
        return StepResult(True, {})
    def _push(*a, **kw):
        call_counter["push"] += 1
        return StepResult(True, {})
    def _open_pr(*a, **kw):
        call_counter["open_pr"] += 1
        return StepResult(True, {})

    monkeypatch.setattr(handler, "audit_coverage", _audit)
    monkeypatch.setattr(handler, "push", _push)
    monkeypatch.setattr(handler, "open_pr", _open_pr)

    sprint_dir = tmp_path / "sprint-001"
    sprint_dir.mkdir()
    ctx = _Ctx(sprint_dir=sprint_dir, workspace_dir=tmp_path)

    out = handler.ship_handler(
        ctx, role="shipper",
        args={"title": "t", "body": "b", "branch": "feature/x"},
    )
    assert out["ship_status"] == "failed"
    assert out["failure_step"] == "test"

    body = (sprint_dir / "ship-notes.md").read_text()
    assert "failure_step: 'test'" in body
    # downstream steps not invoked
    assert call_counter == {"audit_coverage": 0, "push": 0, "open_pr": 0}


def test_ship_handler_coverage_failure_halts(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import handler
    from clawteam.templates.gstack.skills.ship.steps import StepResult

    monkeypatch.setattr(handler, "gh_available", lambda: True)
    monkeypatch.setattr(handler, "sync_main",
        lambda cwd, branch, **kw: StepResult(True, {}))
    monkeypatch.setattr(handler, "run_tests",
        lambda cwd, sprint_dir, **kw: StepResult(True, {}))
    monkeypatch.setattr(handler, "audit_coverage",
        lambda cwd, threshold, **kw: StepResult(
            False, {"coverage": 0.30, "threshold": threshold, "language": "python"}))
    push_counter = {"n": 0}
    pr_counter = {"n": 0}
    def _push(*a, **kw):
        push_counter["n"] += 1
        return StepResult(True, {})
    def _open_pr(*a, **kw):
        pr_counter["n"] += 1
        return StepResult(True, {})
    monkeypatch.setattr(handler, "push", _push)
    monkeypatch.setattr(handler, "open_pr", _open_pr)

    sprint_dir = tmp_path / "sprint-001"
    sprint_dir.mkdir()
    ctx = _Ctx(sprint_dir=sprint_dir, workspace_dir=tmp_path)

    out = handler.ship_handler(ctx, role="shipper", args={"branch": "feature/x"})
    assert out["ship_status"] == "failed"
    assert out["failure_step"] == "coverage"

    body = (sprint_dir / "ship-notes.md").read_text()
    assert "failure_step: 'coverage'" in body
    assert "coverage: 0.3" in body
    assert "coverage_threshold: 0.5" in body
    assert push_counter["n"] == 0
    assert pr_counter["n"] == 0


def test_ship_handler_reads_threshold_from_template(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.ship import handler
    from clawteam.templates.gstack.skills.ship.steps import StepResult

    captured_threshold = {"value": None}

    monkeypatch.setattr(handler, "gh_available", lambda: True)
    monkeypatch.setattr(handler, "sync_main",
        lambda cwd, branch, **kw: StepResult(True, {}))
    monkeypatch.setattr(handler, "run_tests",
        lambda cwd, sprint_dir, **kw: StepResult(True, {}))

    def _audit(cwd, threshold, **kw):
        captured_threshold["value"] = threshold
        return StepResult(True, {"coverage": 0.9, "threshold": threshold})
    monkeypatch.setattr(handler, "audit_coverage", _audit)
    monkeypatch.setattr(handler, "push",
        lambda cwd, branch, **kw: StepResult(True, {}))
    monkeypatch.setattr(handler, "open_pr",
        lambda cwd, title, body, **kw: StepResult(
            True, {"pr_url": "https://example.com/pr/1"}))

    sprint_dir = tmp_path / "sprint-001"
    sprint_dir.mkdir()
    ctx = _Ctx(
        sprint_dir=sprint_dir, workspace_dir=tmp_path,
        template=_TemplateWithShip(ship=_ShipConfig(coverage_threshold=0.8)),
    )

    handler.ship_handler(ctx, role="shipper", args={"branch": "feature/x"})
    assert captured_threshold["value"] == 0.8


def test_ship_handler_role_gated(tmp_path, monkeypatch):
    """Dispatching /ship as engineer must raise SkillNotPermitted."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillNotPermitted

    plugin = GstackSprintPlugin()
    regs = {s.name: s for s in plugin.contribute_skills()}
    dispatcher = SkillDispatcher(regs)

    # ctx is irrelevant — role check fires before handler.
    with pytest.raises(SkillNotPermitted):
        dispatcher.dispatch(ctx=None, skill_name="/ship", role="engineer", args={})


def test_ship_registered_in_plugin():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    regs = GstackSprintPlugin().contribute_skills()
    names = sorted(s.name for s in regs)
    assert "/ship" in names

    ship_reg = next(s for s in regs if s.name == "/ship")
    assert ship_reg.roles == frozenset({"shipper"})


def test_gh_tool_available_detection(monkeypatch):
    from clawteam.templates.gstack.skills.ship import handler

    monkeypatch.setattr(handler.shutil, "which", lambda name: None)
    assert handler.gh_available() is False

    monkeypatch.setattr(handler.shutil, "which", lambda name: "/usr/bin/gh")
    assert handler.gh_available() is True
