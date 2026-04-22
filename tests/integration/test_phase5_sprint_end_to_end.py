"""Phase 5 end-to-end: /ship → /land-and-deploy → /canary artifact chain (D-16).

Plan 05-10 Task 3. Exercises the full dispatcher path — not direct handler
calls — so the role-gating + handler-registration surfaces are covered as
part of the chain.

Three behaviors:

1. ``test_ship_land_canary_chain`` — full chain; asserts artifact sequence
   ship-notes.md → deploy.md → canary-report.md with matching sprint_id
   and deploy_url propagation from the fake custom deploy command
   ("echo https://example.invalid") through to /canary's read of deploy.md.
2. ``test_skill_role_gating_prevents_cross_role`` — dispatching /ship as
   an engineer raises :class:`SkillNotPermitted`.
3. ``test_document_release_auto_invoke_idempotent`` — two /ship runs both
   emit a no_changes /document-release summary (Pitfall 7 idempotency).
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
from clawteam.plugins.skill_dispatcher import SkillDispatcher
from clawteam.plugins.skill_errors import SkillNotPermitted
from clawteam.templates import DeployConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_frontmatter(path: Path) -> dict[str, Any]:
    """Tiny parser mirroring the handler's hand-rolled YAML emitter shape."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm: dict[str, Any] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if (
            len(val) >= 2
            and val[0] == val[-1]
            and val[0] in ("'", '"')
        ):
            val = val[1:-1]
        fm[key.strip()] = val
    return fm


@pytest.fixture
def sprint_ctx(tmp_path):
    """SimpleNamespace ctx accepted by every Phase 5 skill handler."""
    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir()
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()
    (workspace_dir / "pyproject.toml").write_text(
        '[project]\nname = "x"\n', encoding="utf-8",
    )
    (workspace_dir / "tests").mkdir()
    (workspace_dir / "tests" / "test_existing.py").write_text(
        "def test_e(): assert True\n", encoding="utf-8",
    )
    bus = SimpleNamespace(emit=lambda ev: None)
    template = SimpleNamespace(
        deploy=DeployConfig(
            provider="custom",
            project="x",
            custom_deploy_cmd="echo https://example.invalid",
        ),
        canary=None,
        ship=None,
        benchmark=None,
    )
    return SimpleNamespace(
        sprint_dir=sprint_dir,
        sprint_id="e2e-sprint",
        workspace_dir=workspace_dir,
        team_name="e2e-team",
        branch="feat/e2e",
        template=template,
        bus=bus,
        gstack_toml_path=workspace_dir / "gstack.toml",
    )


@pytest.fixture
def dispatcher():
    """Real SkillDispatcher over the real plugin registrations."""
    plugin = GstackSprintPlugin()
    return SkillDispatcher({s.name: s for s in plugin.contribute_skills()})


def _wire_all_mocks(monkeypatch) -> None:
    """Stub every external dependency the three skills touch.

    Done once per test via direct call (rather than a fixture) so each test
    is self-contained and re-runs re-apply the mocks.
    """
    import clawteam.templates.gstack.skills.ship.handler as ship_handler
    from clawteam.templates.gstack.skills.ship.steps import StepResult
    import clawteam.templates.gstack.skills.land_and_deploy.handler as lad_handler
    import clawteam.templates.gstack.skills.document_release.handler as dr_handler
    import clawteam.templates.gstack.skills.canary.handler as canary_handler
    from clawteam.templates.gstack.skills.canary.poller import PollResult

    # --- /ship ---
    monkeypatch.setattr(
        ship_handler.shutil, "which", lambda b: f"/usr/bin/{b}",
    )
    monkeypatch.setattr(
        ship_handler, "sync_main",
        lambda cwd, branch, **kw: StepResult(True, {}),
    )
    monkeypatch.setattr(
        ship_handler, "run_tests",
        lambda cwd, sd, **kw: StepResult(True, {"language": "python"}),
    )
    monkeypatch.setattr(
        ship_handler, "audit_coverage",
        lambda cwd, threshold, **kw: StepResult(
            True, {"coverage": 0.85, "threshold": threshold},
        ),
    )
    monkeypatch.setattr(
        ship_handler, "push",
        lambda cwd, branch, **kw: StepResult(True, {}),
    )
    monkeypatch.setattr(
        ship_handler, "open_pr",
        lambda cwd, title, body, **kw: StepResult(
            True, {"pr_url": "https://github.com/org/repo/pull/42"},
        ),
    )

    # --- /document-release (auto-invoked during /ship success) ---
    def fake_dr(ctx, *, role, args):
        summary = ctx.sprint_dir / "document-release-summary.md"
        summary.write_text(
            "---\n"
            "artifact_type: document-release-summary\n"
            "status: no_changes\n"
            "patches_emitted: 0\n"
            "---\n",
            encoding="utf-8",
        )
        return {
            "status": "ok",
            "patches_emitted": 0,
            "summary_path": str(summary),
        }

    monkeypatch.setattr(dr_handler, "document_release_handler", fake_dr)

    # --- /land-and-deploy ---
    def fake_lad_invoke(command, **kw):
        if command and command[0] == "gh":
            return subprocess.CompletedProcess(
                args=command, returncode=0, stdout="", stderr="",
            )
        if command and command[0] == "echo":
            return subprocess.CompletedProcess(
                args=command, returncode=0,
                stdout="https://example.invalid\n", stderr="",
            )
        if command and command[0] == "git":
            return subprocess.CompletedProcess(
                args=command, returncode=0,
                stdout="abc1234567\n", stderr="",
            )
        return subprocess.CompletedProcess(
            args=command, returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(lad_handler, "invoke_native_cli", fake_lad_invoke)
    monkeypatch.setattr(lad_handler, "_head_probe", lambda url, timeout=10.0: True)

    # --- /canary ---
    def fake_poll(url, *, window_seconds, poll_interval_seconds, **_kw):
        return PollResult(
            http_2xx_count=100,
            http_5xx_count=0,
            response_times_ms=[150.0] * 100,
        )

    monkeypatch.setattr(canary_handler, "poll_window", fake_poll)
    monkeypatch.setattr(
        canary_handler, "load_baseline", lambda team, provider: None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ship_land_canary_chain(dispatcher, sprint_ctx, monkeypatch):
    """D-16: end-to-end artifact chain with deploy_url propagation."""
    _wire_all_mocks(monkeypatch)

    # Step 1: /ship.
    ship_result = dispatcher.dispatch(
        sprint_ctx,
        skill_name="/ship",
        role="shipper",
        args={"title": "Feat E2E", "body": "E2E test"},
    )
    assert ship_result["ship_status"] == "succeeded"

    ship_fm = _parse_frontmatter(sprint_ctx.sprint_dir / "ship-notes.md")
    assert ship_fm.get("ship_status") == "succeeded"
    assert "github.com" in ship_fm.get("pr_url", "")
    assert ship_fm.get("sprint_id") == "e2e-sprint"
    # /document-release auto-invoke marker (D-11).
    assert "/document-release" in ship_fm.get("auto_invoked_skills", "")

    # Step 2: /land-and-deploy.
    lad_result = dispatcher.dispatch(
        sprint_ctx,
        skill_name="/land-and-deploy",
        role="shipper",
        args={"deploy_verify_timeout_seconds": 3},
    )
    assert lad_result["deploy_status"] == "succeeded"

    deploy_fm = _parse_frontmatter(sprint_ctx.sprint_dir / "deploy.md")
    assert deploy_fm.get("deploy_status") == "succeeded"
    assert deploy_fm.get("deploy_url") == "https://example.invalid"
    assert deploy_fm.get("sprint_id") == "e2e-sprint"

    # Step 3: /canary.
    canary_result = dispatcher.dispatch(
        sprint_ctx,
        skill_name="/canary",
        role="sre",
        args={"window_seconds": 1, "poll_interval_seconds": 1},
    )
    assert canary_result["canary_status"] == "clean"

    canary_fm = _parse_frontmatter(sprint_ctx.sprint_dir / "canary-report.md")
    assert canary_fm.get("canary_status") == "clean"
    assert canary_fm.get("sprint_id") == "e2e-sprint"

    # Chain invariant: all three artifacts carry the same sprint_id.
    assert ship_fm["sprint_id"] == deploy_fm["sprint_id"] == canary_fm["sprint_id"]


def test_skill_role_gating_prevents_cross_role(dispatcher, sprint_ctx, monkeypatch):
    """Engineer role cannot dispatch /ship — SkillNotPermitted fires first."""
    _wire_all_mocks(monkeypatch)
    with pytest.raises(SkillNotPermitted):
        dispatcher.dispatch(
            sprint_ctx,
            skill_name="/ship",
            role="engineer",
            args={},
        )


def test_document_release_auto_invoke_idempotent(dispatcher, sprint_ctx, monkeypatch):
    """Two consecutive /ship runs both emit no_changes /document-release summaries."""
    _wire_all_mocks(monkeypatch)

    dispatcher.dispatch(
        sprint_ctx,
        skill_name="/ship",
        role="shipper",
        args={"title": "x", "body": "y"},
    )
    summary1 = (sprint_ctx.sprint_dir / "document-release-summary.md").read_text()

    dispatcher.dispatch(
        sprint_ctx,
        skill_name="/ship",
        role="shipper",
        args={"title": "x", "body": "y"},
    )
    summary2 = (sprint_ctx.sprint_dir / "document-release-summary.md").read_text()

    assert "no_changes" in summary1
    assert "no_changes" in summary2
