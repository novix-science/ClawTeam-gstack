"""Tests for /canary skill (Plan 05-08, SKILL-17).

Covers:
- Task 1 (poller.py pure helpers): poll_window with injectable http_fn +
  sleep_fn; regression evaluator across 5xx rate, response-time, JS console
  error flags; baseline path + load semantics (missing / malformed / valid).
- Task 2 (canary_handler + plugin registration): orchestration (read
  deploy.md -> poll -> evaluate -> emit + write report), DeployRegressionDetected
  emission, baseline-missing graceful path, browser lazy-import defense
  (Pitfall 5), role gating, plugin registration surface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Task 1 — poller.py pure helpers
# ---------------------------------------------------------------------------


def test_poll_window_happy_all_2xx():
    from clawteam.templates.gstack.skills.canary.poller import poll_window

    def fake_http(url: str) -> tuple[int, float]:
        return 200, 100.0

    result = poll_window(
        "https://example.com",
        window_seconds=2.0,
        poll_interval_seconds=0.5,
        http_fn=fake_http,
        sleep_fn=lambda s: None,  # noqa: ARG005
    )
    assert result.http_2xx_count >= 4
    assert result.http_5xx_count == 0
    # avg_response_ms ~= 100
    assert abs(result.avg_response_ms - 100.0) < 0.01


def test_poll_window_immediate_503():
    from clawteam.templates.gstack.skills.canary.poller import poll_window

    def fake_http(url: str) -> tuple[int, float]:
        return 503, 50.0

    result = poll_window(
        "https://example.com",
        window_seconds=1.0,
        poll_interval_seconds=0.25,
        http_fn=fake_http,
        sleep_fn=lambda s: None,  # noqa: ARG005
    )
    assert result.http_2xx_count == 0
    assert result.http_5xx_count >= 1


def test_poll_window_mixed():
    from clawteam.templates.gstack.skills.canary.poller import poll_window

    counter = {"n": 0}

    def fake_http(url: str) -> tuple[int, float]:
        counter["n"] += 1
        return (200, 80.0) if counter["n"] % 2 == 1 else (503, 80.0)

    result = poll_window(
        "https://example.com",
        window_seconds=1.0,
        poll_interval_seconds=0.25,
        http_fn=fake_http,
        sleep_fn=lambda s: None,  # noqa: ARG005
    )
    assert result.http_2xx_count >= 1
    assert result.http_5xx_count >= 1


def test_poll_window_network_error_counted_as_5xx():
    import urllib.error
    from clawteam.templates.gstack.skills.canary.poller import poll_window

    def fake_http(url: str) -> tuple[int, float]:
        raise urllib.error.URLError("boom")

    result = poll_window(
        "https://example.com",
        window_seconds=1.0,
        poll_interval_seconds=0.25,
        http_fn=fake_http,
        sleep_fn=lambda s: None,  # noqa: ARG005
    )
    assert result.http_2xx_count == 0
    assert result.http_5xx_count >= 1


def test_evaluate_regression_clean():
    from clawteam.templates.gstack.skills.canary.poller import (
        PollResult,
        evaluate_regression,
    )

    result = PollResult(
        http_2xx_count=100,
        http_5xx_count=0,
        response_times_ms=[200.0] * 100,
    )
    flags = evaluate_regression(
        result, baseline_avg_ms=250.0, threshold_5xx_rate=0.01,
    )
    assert flags == []


def test_evaluate_regression_5xx_rate():
    from clawteam.templates.gstack.skills.canary.poller import (
        PollResult,
        evaluate_regression,
    )

    result = PollResult(
        http_2xx_count=99,
        http_5xx_count=5,
        response_times_ms=[200.0] * 104,
    )
    flags = evaluate_regression(result, baseline_avg_ms=250.0)
    assert "5xx_rate>1%" in flags


def test_evaluate_regression_slow():
    from clawteam.templates.gstack.skills.canary.poller import (
        PollResult,
        evaluate_regression,
    )

    result = PollResult(
        http_2xx_count=100,
        http_5xx_count=0,
        response_times_ms=[600.0] * 100,
    )
    flags = evaluate_regression(result, baseline_avg_ms=250.0)
    assert "response_time>2x_baseline" in flags


def test_evaluate_regression_js_console_errors():
    from clawteam.templates.gstack.skills.canary.poller import (
        PollResult,
        evaluate_regression,
    )

    result = PollResult(
        http_2xx_count=10,
        http_5xx_count=0,
        response_times_ms=[100.0] * 10,
        js_console_errors=["Uncaught TypeError: x is undefined"],
    )
    flags = evaluate_regression(result, baseline_avg_ms=150.0)
    assert "js_console_error" in flags


def test_baseline_path_matches_convention(monkeypatch, tmp_path):
    # Patch the symbol inside the poller module (imported at module load).
    import clawteam.templates.gstack.skills.canary.poller as poller_mod

    monkeypatch.setattr(poller_mod, "get_data_dir", lambda: tmp_path)
    path = poller_mod.baseline_path(team="t", provider="vercel")
    assert path == tmp_path / "teams" / "t" / "baselines" / "vercel.json"


def test_load_baseline_missing(monkeypatch, tmp_path):
    import clawteam.templates.gstack.skills.canary.poller as poller_mod

    monkeypatch.setattr(poller_mod, "get_data_dir", lambda: tmp_path)
    assert poller_mod.load_baseline("t", "vercel") is None


def test_load_baseline_returns_dict(monkeypatch, tmp_path):
    import clawteam.templates.gstack.skills.canary.poller as poller_mod

    monkeypatch.setattr(poller_mod, "get_data_dir", lambda: tmp_path)
    baseline_dir = tmp_path / "teams" / "t" / "baselines"
    baseline_dir.mkdir(parents=True)
    (baseline_dir / "vercel.json").write_text(
        json.dumps({"avg_response_ms": 250.0})
    )
    loaded = poller_mod.load_baseline("t", "vercel")
    assert loaded == {"avg_response_ms": 250.0}


# ---------------------------------------------------------------------------
# Task 2 — canary_handler + plugin wiring
# ---------------------------------------------------------------------------


@dataclass
class _CanaryCfg:
    window_seconds: int = 300
    poll_interval_seconds: int = 15
    ci_wait_timeout_seconds: int = 1800


@dataclass
class _Template:
    canary: _CanaryCfg | None = field(default_factory=_CanaryCfg)


class _Bus:
    def __init__(self) -> None:
        self.emitted: list[Any] = []

    def emit(self, event: Any) -> None:
        self.emitted.append(event)


@dataclass
class _Ctx:
    sprint_dir: Path
    sprint_id: str = "sprint-001"
    team_name: str = "my-team"
    template: _Template | None = field(default_factory=_Template)
    bus: _Bus = field(default_factory=_Bus)


def _write_deploy_notes(
    sprint_dir: Path,
    *,
    deploy_url: str = "https://example.com",
    provider: str = "vercel",
) -> Path:
    """Write a minimal deploy.md that canary_handler's frontmatter parser accepts."""
    sprint_dir.mkdir(parents=True, exist_ok=True)
    path = sprint_dir / "deploy.md"
    path.write_text(
        "---\n"
        "artifact_type: 'deploy-notes'\n"
        f"deploy_url: '{deploy_url}'\n"
        f"provider: '{provider}'\n"
        "---\n\n"
        "body\n",
        encoding="utf-8",
    )
    return path


def test_handler_writes_canary_report(monkeypatch, tmp_path):
    from clawteam.templates.gstack.skills.canary import handler as handler_mod
    from clawteam.templates.gstack.skills.canary.poller import PollResult

    _write_deploy_notes(tmp_path)

    def fake_poll(url, *, window_seconds, poll_interval_seconds, **_kw):  # noqa: ARG001
        return PollResult(
            http_2xx_count=100,
            http_5xx_count=0,
            response_times_ms=[200.0] * 100,
        )

    monkeypatch.setattr(handler_mod, "poll_window", fake_poll)
    monkeypatch.setattr(handler_mod, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=tmp_path)
    out = handler_mod.canary_handler(ctx, role="sre", args={})
    assert out["canary_status"] == "clean"

    report_path = tmp_path / "canary-report.md"
    assert report_path.exists()
    body = report_path.read_text(encoding="utf-8")
    assert "canary_status: 'clean'" in body
    assert "http_2xx_count: 100" in body
    assert "http_5xx_count: 0" in body


def test_handler_regression_emits_event(monkeypatch, tmp_path):
    from clawteam.events.types import DeployRegressionDetected
    from clawteam.templates.gstack.skills.canary import handler as handler_mod
    from clawteam.templates.gstack.skills.canary.poller import PollResult

    _write_deploy_notes(tmp_path)

    def fake_poll(url, *, window_seconds, poll_interval_seconds, **_kw):  # noqa: ARG001
        return PollResult(
            http_2xx_count=95,
            http_5xx_count=10,
            response_times_ms=[150.0] * 105,
        )

    monkeypatch.setattr(handler_mod, "poll_window", fake_poll)
    monkeypatch.setattr(handler_mod, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=tmp_path)
    out = handler_mod.canary_handler(ctx, role="sre", args={})

    assert out["canary_status"] == "regression"
    assert "5xx_rate>1%" in out["regression_flags"]

    # Bus emitted exactly one DeployRegressionDetected with populated payload.
    events = [e for e in ctx.bus.emitted if isinstance(e, DeployRegressionDetected)]
    assert len(events) == 1
    ev = events[0]
    assert ev.sprint_id == "sprint-001"
    assert ev.deploy_url == "https://example.com"
    assert "5xx_rate>1%" in ev.regression_flags

    body = (tmp_path / "canary-report.md").read_text(encoding="utf-8")
    assert "canary_status: 'regression'" in body


def test_handler_baseline_missing(monkeypatch, tmp_path):
    from clawteam.templates.gstack.skills.canary import handler as handler_mod
    from clawteam.templates.gstack.skills.canary.poller import PollResult

    _write_deploy_notes(tmp_path)

    def fake_poll(url, *, window_seconds, poll_interval_seconds, **_kw):  # noqa: ARG001
        return PollResult(
            http_2xx_count=10,
            http_5xx_count=0,
            response_times_ms=[120.0] * 10,
        )

    monkeypatch.setattr(handler_mod, "poll_window", fake_poll)
    monkeypatch.setattr(handler_mod, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=tmp_path)
    handler_mod.canary_handler(ctx, role="sre", args={})

    body = (tmp_path / "canary-report.md").read_text(encoding="utf-8")
    assert "baseline_missing: true" in body
    assert "pre_deploy_avg_response_ms: 0.0" in body


def test_handler_deploy_notes_missing(tmp_path):
    from clawteam.plugins.skill_errors import SkillPreconditionError
    from clawteam.templates.gstack.skills.canary import handler as handler_mod

    ctx = _Ctx(sprint_dir=tmp_path)
    with pytest.raises(SkillPreconditionError) as exc:
        handler_mod.canary_handler(ctx, role="sre", args={})
    assert "Run /land-and-deploy first" in str(exc.value)


def test_handler_browser_mode_without_playwright(monkeypatch, tmp_path):
    from clawteam.templates.gstack.skills.canary import handler as handler_mod
    from clawteam.templates.gstack.skills.canary.poller import PollResult

    _write_deploy_notes(tmp_path)

    def fake_poll(url, *, window_seconds, poll_interval_seconds, **_kw):  # noqa: ARG001
        return PollResult(
            http_2xx_count=10,
            http_5xx_count=0,
            response_times_ms=[100.0] * 10,
        )

    monkeypatch.setattr(handler_mod, "poll_window", fake_poll)
    monkeypatch.setattr(handler_mod, "load_baseline", lambda team, provider: None)
    # Force find_spec("playwright") -> None so _get_browser_errors falls through.
    monkeypatch.setattr(handler_mod, "find_spec", lambda name: None)

    ctx = _Ctx(sprint_dir=tmp_path)
    out = handler_mod.canary_handler(ctx, role="sre", args={"browser": True})

    # No crash; no js_console_error flag since Playwright wasn't available.
    assert "js_console_error" not in out["regression_flags"]


def test_handler_module_level_no_playwright_import():
    """Pitfall 5 defense — ast-verify that handler.py never imports playwright at module top."""
    import ast
    src = Path("clawteam/templates/gstack/skills/canary/handler.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(src)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            assert "playwright" not in (node.module or ""), (
                f"Module-level ImportFrom references playwright: {node.module}"
            )
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "playwright" not in alias.name, (
                    f"Module-level Import references playwright: {alias.name}"
                )


def test_handler_role_gated():
    """/canary is role-gated to sre via the dispatcher — engineer invocation is denied."""
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillNotPermitted
    from clawteam.plugins.skill_registration import SkillRegistration
    from clawteam.templates.gstack.skills.canary.handler import canary_handler

    reg = SkillRegistration(
        name="/canary",
        roles=frozenset({"sre"}),
        handler=canary_handler,
        tool_available=None,
        install_hint="",
    )
    dispatcher = SkillDispatcher([reg])
    with pytest.raises(SkillNotPermitted):
        dispatcher.dispatch("/canary", role="engineer", ctx=None, args={})


def test_registered_in_plugin():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    skills = plugin.contribute_skills()
    matches = [s for s in skills if s.name == "/canary"]
    assert len(matches) == 1
    assert matches[0].roles == frozenset({"sre"})


def test_handler_uses_canary_config_from_template(monkeypatch, tmp_path):
    from clawteam.templates.gstack.skills.canary import handler as handler_mod
    from clawteam.templates.gstack.skills.canary.poller import PollResult

    _write_deploy_notes(tmp_path)

    seen: dict[str, Any] = {}

    def fake_poll(url, *, window_seconds, poll_interval_seconds, **_kw):  # noqa: ARG001
        seen["window_seconds"] = window_seconds
        seen["poll_interval_seconds"] = poll_interval_seconds
        return PollResult(
            http_2xx_count=2,
            http_5xx_count=0,
            response_times_ms=[100.0, 100.0],
        )

    monkeypatch.setattr(handler_mod, "poll_window", fake_poll)
    monkeypatch.setattr(handler_mod, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=tmp_path, template=_Template(canary=_CanaryCfg(
        window_seconds=30, poll_interval_seconds=5, ci_wait_timeout_seconds=60,
    )))
    handler_mod.canary_handler(ctx, role="sre", args={})

    assert seen["window_seconds"] == 30
    assert seen["poll_interval_seconds"] == 5


def test_503_immediately_adversarial(monkeypatch, tmp_path):
    """D-15 case: mock returns all 5xx over short window; report still written without crash."""
    from clawteam.templates.gstack.skills.canary import handler as handler_mod
    from clawteam.templates.gstack.skills.canary.poller import PollResult

    _write_deploy_notes(tmp_path)

    def fake_poll(url, *, window_seconds, poll_interval_seconds, **_kw):  # noqa: ARG001
        return PollResult(
            http_2xx_count=0,
            http_5xx_count=4,
            response_times_ms=[50.0] * 4,
        )

    monkeypatch.setattr(handler_mod, "poll_window", fake_poll)
    monkeypatch.setattr(handler_mod, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=tmp_path, template=_Template(canary=_CanaryCfg(
        window_seconds=1, poll_interval_seconds=1, ci_wait_timeout_seconds=1,
    )))
    out = handler_mod.canary_handler(ctx, role="sre", args={})

    assert out["canary_status"] == "regression"
    assert "5xx_rate>1%" in out["regression_flags"]
    body = (tmp_path / "canary-report.md").read_text(encoding="utf-8")
    assert "canary_status: 'regression'" in body
