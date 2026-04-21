"""Tests for TemplateDef Phase 5 sub-blocks (Plan 05-01 Task 3).

Verifies [ship]/[deploy]/[canary]/[benchmark] optional sub-blocks on TemplateDef:
- BC: existing templates (gstack + 6 bundled) parse with all four fields == None.
- Each block parses into its pydantic config with defaults applied.
- Invalid provider literal rejected at parse time.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from clawteam.templates import (
    BenchmarkConfig,
    CanaryConfig,
    DeployConfig,
    ShipConfig,
    TemplateDef,
    _parse_toml,
    load_template,
)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "clawteam" / "templates"

PACKAGED_TEMPLATES = [
    "software-dev",
    "hedge-fund",
    "code-review",
    "harness-default",
    "research-paper",
    "strategy-room",
]


# ── BC tests ─────────────────────────────────────────────────────────────


def test_bc_gstack_parses_without_new_blocks():
    tmpl = _parse_toml(_TEMPLATES_DIR / "gstack.toml")
    assert isinstance(tmpl, TemplateDef)
    assert tmpl.ship is None
    assert tmpl.deploy is None
    assert tmpl.canary is None
    assert tmpl.benchmark is None


@pytest.mark.parametrize("name", PACKAGED_TEMPLATES)
def test_bc_packaged_template_parses(name: str):
    tmpl = load_template(name)
    assert tmpl.ship is None
    assert tmpl.deploy is None
    assert tmpl.canary is None
    assert tmpl.benchmark is None


# ── Sub-block parsing ────────────────────────────────────────────────────


def _write_base_template(tmp_path: Path, extra: str = "") -> Path:
    """Write a minimal valid TOML (name + leader) plus any extra top-level blocks."""
    content = """[template]
name = "test"

[template.leader]
name = "lead"
type = "general-purpose"
"""
    if extra:
        content += "\n" + extra + "\n"
    p = tmp_path / "test.toml"
    p.write_text(content)
    return p


def test_ship_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        "[ship]\ncoverage_threshold = 0.75",
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.ship, ShipConfig)
    assert tmpl.ship.coverage_threshold == 0.75


def test_ship_defaults_applied(tmp_path):
    # Empty [ship] block uses all defaults.
    p = _write_base_template(tmp_path, "[ship]")
    tmpl = _parse_toml(p)
    assert tmpl.ship is not None
    assert tmpl.ship.coverage_threshold == 0.5


def test_deploy_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        '[deploy]\nprovider = "vercel"\nproject = "my-app"',
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.deploy, DeployConfig)
    assert tmpl.deploy.provider == "vercel"
    assert tmpl.deploy.project == "my-app"
    assert tmpl.deploy.custom_deploy_cmd == ""


def test_deploy_custom_provider_requires_cmd(tmp_path):
    p = _write_base_template(
        tmp_path,
        '[deploy]\nprovider = "custom"\nproject = "x"',
    )
    tmpl = _parse_toml(p)
    # Schema level allows empty cmd; /setup-deploy wizard enforces at write time.
    assert tmpl.deploy is not None
    assert tmpl.deploy.provider == "custom"
    assert tmpl.deploy.custom_deploy_cmd == ""


def test_canary_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        "[canary]\nwindow_seconds = 600\npoll_interval_seconds = 30\nci_wait_timeout_seconds = 900",
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.canary, CanaryConfig)
    assert tmpl.canary.window_seconds == 600
    assert tmpl.canary.poll_interval_seconds == 30
    assert tmpl.canary.ci_wait_timeout_seconds == 900


def test_canary_defaults_applied(tmp_path):
    p = _write_base_template(tmp_path, "[canary]\nwindow_seconds = 400")
    tmpl = _parse_toml(p)
    assert tmpl.canary is not None
    assert tmpl.canary.window_seconds == 400
    assert tmpl.canary.poll_interval_seconds == 15
    assert tmpl.canary.ci_wait_timeout_seconds == 1800


def test_benchmark_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        "[benchmark]\nregression_threshold_ratio = 2.0",
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.benchmark, BenchmarkConfig)
    assert tmpl.benchmark.regression_threshold_ratio == 2.0


def test_deploy_invalid_provider_rejected(tmp_path):
    p = _write_base_template(
        tmp_path,
        '[deploy]\nprovider = "aws"\nproject = "x"',
    )
    with pytest.raises(ValidationError):
        _parse_toml(p)


def test_all_four_blocks_roundtrip(tmp_path):
    p = _write_base_template(
        tmp_path,
        """[ship]
coverage_threshold = 0.9

[deploy]
provider = "fly"
project = "my-fly-app"

[canary]
window_seconds = 777

[benchmark]
regression_threshold_ratio = 3.0
""",
    )
    tmpl = _parse_toml(p)
    assert tmpl.ship.coverage_threshold == 0.9
    assert tmpl.deploy.provider == "fly"
    assert tmpl.deploy.project == "my-fly-app"
    assert tmpl.canary.window_seconds == 777
    assert tmpl.canary.poll_interval_seconds == 15  # default still applied
    assert tmpl.benchmark.regression_threshold_ratio == 3.0


def test_absent_sub_blocks_default_none(tmp_path):
    p = _write_base_template(tmp_path)  # no extra blocks
    tmpl = _parse_toml(p)
    assert tmpl.ship is None
    assert tmpl.deploy is None
    assert tmpl.canary is None
    assert tmpl.benchmark is None
