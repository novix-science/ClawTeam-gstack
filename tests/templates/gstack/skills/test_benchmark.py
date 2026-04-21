"""Tests for /benchmark skill (Plan 05-09, SKILL-18).

Covers:
- Lighthouse happy path: lighthouse binary present + valid JSON → report has
  lcp_ms/fid_ms/cls_score/ttfb_ms populated; measured_with='lighthouse'.
- Curl fallback: lighthouse binary missing → curl -w timing used; lcp/fid/cls
  are None; ttfb_ms + dom_loaded_ms populated; measured_with='curl'.
- Partial lighthouse output (D-15): lighthouse returns only LCP → cls/fid None
  without crashing.
- JSON parse failure: lighthouse stdout is malformed → curl fallback kicks in.
- Pre-deploy baseline write: args['pre_deploy']=True → baseline JSON at
  baseline_path(team, provider) consumed by /canary.
- Regression detection: any vital > 1.5 * baseline → WebVitalRegressionDetected
  event emitted via ctx.bus + regression_flags populated.
- No-regression: ratio < 1.5x → no event, regression_flags=[].
- Precondition: deploy.md missing → SkillPreconditionError.
- Role gate: sre-only.
- Plugin registration: GstackSprintPlugin.contribute_skills() includes
  /benchmark with roles=frozenset({"sre"}).
- Threshold override from TemplateDef.benchmark.regression_threshold_ratio.
"""

from __future__ import annotations

import json
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
class _BenchmarkConfig:
    regression_threshold_ratio: float = 1.5


@dataclass
class _Template:
    benchmark: _BenchmarkConfig | None = None


@dataclass
class _Bus:
    emitted: list[Any] = field(default_factory=list)

    def emit(self, event: Any) -> None:
        self.emitted.append(event)


@dataclass
class _Ctx:
    sprint_dir: Path
    sprint_id: str = "sprint-001"
    team_name: str = "myteam"
    template: _Template | None = None
    bus: _Bus = field(default_factory=_Bus)


def _write_deploy_notes(
    sprint_dir: Path,
    *,
    deploy_url: str = "https://example.vercel.app",
    provider: str = "vercel",
) -> Path:
    sprint_dir.mkdir(parents=True, exist_ok=True)
    path = sprint_dir / "deploy.md"
    path.write_text(
        "---\n"
        f"deploy_url: '{deploy_url}'\n"
        f"provider: '{provider}'\n"
        "deploy_status: 'succeeded'\n"
        "---\n\n"
        "deploy notes body\n",
        encoding="utf-8",
    )
    return path


def _lighthouse_json_full() -> str:
    return json.dumps({
        "audits": {
            "largest-contentful-paint": {"numericValue": 1234.0},
            "cumulative-layout-shift": {"numericValue": 0.05},
            "max-potential-fid": {"numericValue": 80.0},
            "server-response-time": {"numericValue": 150.0},
        }
    })


def _lighthouse_json_partial_lcp_only() -> str:
    return json.dumps({
        "audits": {
            "largest-contentful-paint": {"numericValue": 1234.0},
        }
    })


def _read_report_fm(artifact_path: Path) -> dict[str, Any]:
    """Parse the YAML-ish frontmatter written by the handler."""
    text = artifact_path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"expected frontmatter, got: {text[:80]!r}"
    end = text.find("\n---", 4)
    assert end != -1
    fm: dict[str, Any] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        v = v.strip()
        if v in ("true", "false"):
            fm[k.strip()] = (v == "true")
            continue
        if v == "null":
            fm[k.strip()] = None
            continue
        if v.startswith("'") and v.endswith("'") and len(v) >= 2:
            fm[k.strip()] = v[1:-1]
            continue
        if v.startswith("[") or v.startswith("{"):
            try:
                fm[k.strip()] = json.loads(v)
                continue
            except json.JSONDecodeError:
                fm[k.strip()] = v
                continue
        # Try numeric
        try:
            if "." in v:
                fm[k.strip()] = float(v)
            else:
                fm[k.strip()] = int(v)
            continue
        except ValueError:
            pass
        fm[k.strip()] = v
    return fm


# ---------------------------------------------------------------------------
# Test 1: lighthouse happy path
# ---------------------------------------------------------------------------


def test_lighthouse_happy_path(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    monkeypatch.setattr(
        bh.shutil, "which",
        lambda name: "/usr/bin/lighthouse" if name == "lighthouse" else None,
    )

    def fake_invoke(cmd, **kwargs):
        # Only lighthouse invoked on happy path.
        assert cmd[0] == "lighthouse"
        return _make_completed(stdout=_lighthouse_json_full())

    monkeypatch.setattr(bh, "invoke_native_cli", fake_invoke)
    # Make baseline lookups go to tmp_path so nothing pollutes $HOME.
    monkeypatch.setattr(bh, "baseline_path",
                        lambda team, provider: tmp_path / "baselines" / f"{provider}.json")
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))
    result = bh.benchmark_handler(ctx, role="sre", args={})

    assert result["benchmark_status"] == "clean"
    assert result["measured_with"] == "lighthouse"

    fm = _read_report_fm(sprint_dir / "benchmark-report.md")
    assert fm["measured_with"] == "lighthouse"
    assert fm["lcp_ms"] == 1234.0
    assert fm["fid_ms"] == 80.0
    assert fm["cls_score"] == 0.05
    assert fm["ttfb_ms"] == 150.0


# ---------------------------------------------------------------------------
# Test 2: lighthouse missing → curl fallback
# ---------------------------------------------------------------------------


def test_lighthouse_missing_falls_back_to_curl(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    def fake_which(name):
        if name == "lighthouse":
            return None
        if name == "curl":
            return "/usr/bin/curl"
        return None

    monkeypatch.setattr(bh.shutil, "which", fake_which)

    def fake_invoke(cmd, **kwargs):
        assert cmd[0] == "curl"
        # "%{time_total} %{time_starttransfer}" seconds → 0.450 0.120
        return _make_completed(stdout="0.450 0.120")

    monkeypatch.setattr(bh, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(bh, "baseline_path",
                        lambda team, provider: tmp_path / "baselines" / f"{provider}.json")
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))
    result = bh.benchmark_handler(ctx, role="sre", args={})

    assert result["measured_with"] == "curl"
    fm = _read_report_fm(sprint_dir / "benchmark-report.md")
    assert fm["measured_with"] == "curl"
    assert fm["ttfb_ms"] == 120.0
    assert fm["dom_loaded_ms"] == 450.0
    assert fm["lcp_ms"] is None
    assert fm["cls_score"] is None
    assert fm["fid_ms"] is None


# ---------------------------------------------------------------------------
# Test 3: partial lighthouse output (D-15 adversarial)
# ---------------------------------------------------------------------------


def test_lighthouse_partial_output_d15(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    def fake_which(name):
        if name == "lighthouse":
            return "/usr/bin/lighthouse"
        if name == "curl":
            return "/usr/bin/curl"
        return None

    monkeypatch.setattr(bh.shutil, "which", fake_which)

    call_log: list[str] = []

    def fake_invoke(cmd, **kwargs):
        call_log.append(cmd[0])
        if cmd[0] == "lighthouse":
            return _make_completed(stdout=_lighthouse_json_partial_lcp_only())
        if cmd[0] == "curl":
            return _make_completed(stdout="0.300 0.100")
        return _make_completed(returncode=1)

    monkeypatch.setattr(bh, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(bh, "baseline_path",
                        lambda team, provider: tmp_path / "baselines" / f"{provider}.json")
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))
    result = bh.benchmark_handler(ctx, role="sre", args={})

    # Primary measurement still succeeded (lighthouse returned parseable json).
    assert result["measured_with"] == "lighthouse"
    fm = _read_report_fm(sprint_dir / "benchmark-report.md")
    assert fm["lcp_ms"] == 1234.0
    assert fm["cls_score"] is None
    assert fm["fid_ms"] is None
    # ttfb/dom_loaded populated via curl fallback fill.
    assert fm["ttfb_ms"] == 100.0
    assert fm["dom_loaded_ms"] == 300.0
    # Both binaries were called.
    assert "lighthouse" in call_log
    assert "curl" in call_log


# ---------------------------------------------------------------------------
# Test 4: lighthouse JSON parse failure → curl fallback
# ---------------------------------------------------------------------------


def test_lighthouse_json_parse_failure(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    def fake_which(name):
        if name == "lighthouse":
            return "/usr/bin/lighthouse"
        if name == "curl":
            return "/usr/bin/curl"
        return None

    monkeypatch.setattr(bh.shutil, "which", fake_which)

    def fake_invoke(cmd, **kwargs):
        if cmd[0] == "lighthouse":
            return _make_completed(stdout="FAILED TO RUN")
        if cmd[0] == "curl":
            return _make_completed(stdout="0.200 0.080")
        return _make_completed(returncode=1)

    monkeypatch.setattr(bh, "invoke_native_cli", fake_invoke)
    monkeypatch.setattr(bh, "baseline_path",
                        lambda team, provider: tmp_path / "baselines" / f"{provider}.json")
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))
    result = bh.benchmark_handler(ctx, role="sre", args={})

    assert result["measured_with"] == "curl"
    fm = _read_report_fm(sprint_dir / "benchmark-report.md")
    assert fm["measured_with"] == "curl"
    assert fm["ttfb_ms"] == 80.0
    assert fm["dom_loaded_ms"] == 200.0


# ---------------------------------------------------------------------------
# Test 5: pre-deploy writes baseline JSON consumed by /canary
# ---------------------------------------------------------------------------


def test_pre_deploy_writes_baseline(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    monkeypatch.setattr(
        bh.shutil, "which",
        lambda name: "/usr/bin/lighthouse" if name == "lighthouse" else None,
    )
    monkeypatch.setattr(
        bh, "invoke_native_cli",
        lambda cmd, **kw: _make_completed(stdout=_lighthouse_json_full()),
    )

    baseline_file = tmp_path / "data" / "teams" / "myteam" / "baselines" / "vercel.json"
    monkeypatch.setattr(
        bh, "baseline_path",
        lambda team, provider: baseline_file if team == "myteam" else Path("/nope"),
    )
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))
    bh.benchmark_handler(ctx, role="sre", args={"pre_deploy": True, "team": "myteam"})

    assert baseline_file.exists()
    data = json.loads(baseline_file.read_text())
    assert "lcp_ms" in data
    assert "ttfb_ms" in data
    assert "avg_response_ms" in data
    assert data["lcp_ms"] == 1234.0


def test_not_pre_deploy_no_baseline_write(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    monkeypatch.setattr(
        bh.shutil, "which",
        lambda name: "/usr/bin/lighthouse" if name == "lighthouse" else None,
    )
    monkeypatch.setattr(
        bh, "invoke_native_cli",
        lambda cmd, **kw: _make_completed(stdout=_lighthouse_json_full()),
    )
    baseline_file = tmp_path / "data" / "teams" / "myteam" / "baselines" / "vercel.json"
    monkeypatch.setattr(bh, "baseline_path", lambda team, provider: baseline_file)
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: None)

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))
    bh.benchmark_handler(ctx, role="sre", args={"team": "myteam"})

    assert not baseline_file.exists(), "baseline must NOT be written when pre_deploy is False"


# ---------------------------------------------------------------------------
# Test 6: regression detected → event emitted
# ---------------------------------------------------------------------------


def test_regression_detects_and_emits(tmp_path, monkeypatch):
    from clawteam.events.types import WebVitalRegressionDetected
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    monkeypatch.setattr(
        bh.shutil, "which",
        lambda name: "/usr/bin/lighthouse" if name == "lighthouse" else None,
    )

    # Current run returns lcp_ms=2000 (2x baseline of 1000).
    stdout_2x = json.dumps({
        "audits": {
            "largest-contentful-paint": {"numericValue": 2000.0},
            "cumulative-layout-shift": {"numericValue": 0.05},
            "max-potential-fid": {"numericValue": 80.0},
            "server-response-time": {"numericValue": 150.0},
        }
    })
    monkeypatch.setattr(
        bh, "invoke_native_cli",
        lambda cmd, **kw: _make_completed(stdout=stdout_2x),
    )

    baseline_data = {
        "lcp_ms": 1000.0, "fid_ms": 80.0, "cls_score": 0.05,
        "ttfb_ms": 150.0, "dom_loaded_ms": 100.0,
        "avg_response_ms": 125.0,
    }
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: baseline_data)
    monkeypatch.setattr(
        bh, "baseline_path",
        lambda team, provider: tmp_path / "baselines" / f"{provider}.json",
    )

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))
    result = bh.benchmark_handler(ctx, role="sre", args={})

    assert result["benchmark_status"] == "regression"
    assert any("lcp" in flag for flag in result["regression_flags"])

    emitted = ctx.bus.emitted
    assert any(isinstance(e, WebVitalRegressionDetected) for e in emitted)
    lcp_evt = next(
        e for e in emitted if isinstance(e, WebVitalRegressionDetected) and e.vital == "lcp"
    )
    assert lcp_evt.baseline_value == 1000.0
    assert lcp_evt.observed_value == 2000.0
    assert lcp_evt.ratio == 2.0


# ---------------------------------------------------------------------------
# Test 7: no-regression → no event
# ---------------------------------------------------------------------------


def test_no_regression_no_emit(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    monkeypatch.setattr(
        bh.shutil, "which",
        lambda name: "/usr/bin/lighthouse" if name == "lighthouse" else None,
    )

    # lcp 1200 vs baseline 1000 → ratio 1.2 < 1.5
    stdout_mild = json.dumps({
        "audits": {
            "largest-contentful-paint": {"numericValue": 1200.0},
            "cumulative-layout-shift": {"numericValue": 0.05},
            "max-potential-fid": {"numericValue": 80.0},
            "server-response-time": {"numericValue": 150.0},
        }
    })
    monkeypatch.setattr(
        bh, "invoke_native_cli",
        lambda cmd, **kw: _make_completed(stdout=stdout_mild),
    )
    baseline_data = {
        "lcp_ms": 1000.0, "fid_ms": 80.0, "cls_score": 0.05,
        "ttfb_ms": 150.0, "dom_loaded_ms": 100.0,
    }
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: baseline_data)
    monkeypatch.setattr(
        bh, "baseline_path",
        lambda team, provider: tmp_path / "baselines" / f"{provider}.json",
    )

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))
    result = bh.benchmark_handler(ctx, role="sre", args={})

    assert result["benchmark_status"] == "clean"
    assert result["regression_flags"] == []
    assert ctx.bus.emitted == []


# ---------------------------------------------------------------------------
# Test 8: deploy.md missing → SkillPreconditionError
# ---------------------------------------------------------------------------


def test_deploy_notes_missing(tmp_path):
    from clawteam.plugins.skill_errors import SkillPreconditionError
    from clawteam.templates.gstack.skills.benchmark.handler import benchmark_handler

    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir()

    ctx = _Ctx(sprint_dir=sprint_dir, template=_Template(benchmark=_BenchmarkConfig()))

    with pytest.raises(SkillPreconditionError) as exc:
        benchmark_handler(ctx, role="sre", args={})
    assert "/land-and-deploy" in exc.value.message or "deploy.md" in exc.value.message


# ---------------------------------------------------------------------------
# Test 9: role gate — only sre may invoke /benchmark via the dispatcher
# ---------------------------------------------------------------------------


def test_role_gated_via_dispatcher(tmp_path):
    """Direct handler call is NOT gated (tests call it directly), but the
    plugin's SkillRegistration pins roles={'sre'} so the dispatcher layer
    raises SkillNotPermitted for other roles. We verify the registration shape.
    """
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    regs = {r.name: r for r in plugin.contribute_skills()}
    assert "/benchmark" in regs
    assert regs["/benchmark"].roles == frozenset({"sre"})


# ---------------------------------------------------------------------------
# Test 10: plugin registration — /benchmark appears in contribute_skills
# ---------------------------------------------------------------------------


def test_registered_in_plugin():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    names = sorted(s.name for s in GstackSprintPlugin().contribute_skills())
    assert "/benchmark" in names


# ---------------------------------------------------------------------------
# Test 11: regression threshold override from TemplateDef.benchmark
# ---------------------------------------------------------------------------


def test_regression_threshold_from_template(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.benchmark import handler as bh

    sprint_dir = tmp_path / "sprint"
    _write_deploy_notes(sprint_dir)

    monkeypatch.setattr(
        bh.shutil, "which",
        lambda name: "/usr/bin/lighthouse" if name == "lighthouse" else None,
    )

    # observed lcp 1700 vs baseline 1000 → ratio 1.7x
    # Default threshold 1.5 → regression. With threshold_ratio=2.0 → NO regression.
    stdout_17x = json.dumps({
        "audits": {
            "largest-contentful-paint": {"numericValue": 1700.0},
            "cumulative-layout-shift": {"numericValue": 0.05},
            "max-potential-fid": {"numericValue": 80.0},
            "server-response-time": {"numericValue": 150.0},
        }
    })
    monkeypatch.setattr(
        bh, "invoke_native_cli",
        lambda cmd, **kw: _make_completed(stdout=stdout_17x),
    )
    baseline_data = {
        "lcp_ms": 1000.0, "fid_ms": 80.0, "cls_score": 0.05,
        "ttfb_ms": 150.0, "dom_loaded_ms": 100.0,
    }
    monkeypatch.setattr(bh, "load_baseline", lambda team, provider: baseline_data)
    monkeypatch.setattr(
        bh, "baseline_path",
        lambda team, provider: tmp_path / "baselines" / f"{provider}.json",
    )

    ctx = _Ctx(
        sprint_dir=sprint_dir,
        template=_Template(benchmark=_BenchmarkConfig(regression_threshold_ratio=2.0)),
    )
    result = bh.benchmark_handler(ctx, role="sre", args={})

    assert result["benchmark_status"] == "clean", (
        "template threshold 2.0 must suppress regression for 1.7x observation"
    )
    assert result["regression_flags"] == []
    assert ctx.bus.emitted == []
