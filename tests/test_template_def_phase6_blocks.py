"""Tests for TemplateDef Phase 6 sub-blocks (Plan 06-01 Task 3).

Verifies [memory]/[design_shotgun]/[browser] optional top-level sub-blocks
on TemplateDef:

- BC: existing templates (gstack + 6 bundled) parse with all three new
  fields == None.
- Each block parses into its pydantic config with defaults applied.
- Invalid field values rejected at pydantic validation time.
- Phase 5 sub-blocks still work in presence of Phase 6 additions.

Mirrors ``tests/test_template_def_extensions.py`` shape verbatim.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from clawteam.templates import (
    BrowserConfig,
    DesignShotgunConfig,
    MemoryConfig,
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


def test_bc_gstack_parses_without_phase6_blocks():
    tmpl = _parse_toml(_TEMPLATES_DIR / "gstack.toml")
    assert isinstance(tmpl, TemplateDef)
    assert tmpl.memory is None
    assert tmpl.design_shotgun is None
    assert tmpl.browser is None


@pytest.mark.parametrize("name", PACKAGED_TEMPLATES)
def test_bc_packaged_template_parses(name: str):
    tmpl = load_template(name)
    assert tmpl.memory is None
    assert tmpl.design_shotgun is None
    assert tmpl.browser is None


# ── Helper ───────────────────────────────────────────────────────────────


def _write_base_template(tmp_path: Path, extra: str = "") -> Path:
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


# ── [memory] parsing ─────────────────────────────────────────────────────


def test_memory_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        "[memory]\nconflict_threshold = 0.8\nretention_pattern_days = 60\nretention_incident_days = 120",
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.memory, MemoryConfig)
    assert tmpl.memory.conflict_threshold == 0.8
    assert tmpl.memory.retention_pattern_days == 60
    assert tmpl.memory.retention_incident_days == 120


def test_memory_defaults(tmp_path):
    """Partial [memory] block — unset fields fall back to MemoryConfig defaults."""
    p = _write_base_template(tmp_path, "[memory]\nconflict_threshold = 0.5")
    tmpl = _parse_toml(p)
    assert tmpl.memory is not None
    assert tmpl.memory.conflict_threshold == 0.5
    assert tmpl.memory.retention_pattern_days == 90  # default
    assert tmpl.memory.retention_incident_days == 180  # default


def test_memory_threshold_range_validated(tmp_path):
    p = _write_base_template(tmp_path, "[memory]\nconflict_threshold = 1.5")
    with pytest.raises(ValidationError):
        _parse_toml(p)


# ── [design_shotgun] parsing ─────────────────────────────────────────────


def test_design_shotgun_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        '[design_shotgun]\nvariant_count = 6\nboard_format = "html"',
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.design_shotgun, DesignShotgunConfig)
    assert tmpl.design_shotgun.variant_count == 6
    assert tmpl.design_shotgun.board_format == "html"


def test_design_shotgun_variant_count_range(tmp_path):
    p_low = _write_base_template(tmp_path, "[design_shotgun]\nvariant_count = 0")
    with pytest.raises(ValidationError):
        _parse_toml(p_low)

    # Reuse tmp_path with a new filename for the upper-bound case.
    p_high = tmp_path / "test2.toml"
    p_high.write_text(
        """[template]
name = "test2"

[template.leader]
name = "lead"
type = "general-purpose"

[design_shotgun]
variant_count = 1000
"""
    )
    with pytest.raises(ValidationError):
        _parse_toml(p_high)


def test_design_shotgun_board_format_literal(tmp_path):
    p = _write_base_template(
        tmp_path,
        '[design_shotgun]\nboard_format = "pdf"',
    )
    with pytest.raises(ValidationError):
        _parse_toml(p)


# ── [browser] parsing ────────────────────────────────────────────────────


def test_browser_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        '[browser]\nheadless = false\ntimeout_seconds = 60\ncookies_dir = "custom/path"',
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.browser, BrowserConfig)
    assert tmpl.browser.headless is False
    assert tmpl.browser.timeout_seconds == 60
    assert tmpl.browser.cookies_dir == "custom/path"


def test_browser_defaults(tmp_path):
    p = _write_base_template(tmp_path, "[browser]\nheadless = true")
    tmpl = _parse_toml(p)
    assert tmpl.browser is not None
    assert tmpl.browser.headless is True
    assert tmpl.browser.timeout_seconds == 30  # default
    assert tmpl.browser.cookies_dir == ""  # default


# ── All three blocks together ────────────────────────────────────────────


def test_all_three_phase6_blocks_roundtrip(tmp_path):
    p = _write_base_template(
        tmp_path,
        """[memory]
conflict_threshold = 0.65
retention_pattern_days = 45

[design_shotgun]
variant_count = 8
board_format = "markdown"

[browser]
headless = false
timeout_seconds = 45
""",
    )
    tmpl = _parse_toml(p)
    assert tmpl.memory is not None
    assert tmpl.memory.conflict_threshold == 0.65
    assert tmpl.memory.retention_pattern_days == 45
    assert tmpl.memory.retention_incident_days == 180  # default preserved
    assert tmpl.design_shotgun is not None
    assert tmpl.design_shotgun.variant_count == 8
    assert tmpl.design_shotgun.board_format == "markdown"
    assert tmpl.browser is not None
    assert tmpl.browser.headless is False
    assert tmpl.browser.timeout_seconds == 45
    assert tmpl.browser.cookies_dir == ""


# ── Phase 5 cross-regression ─────────────────────────────────────────────


def test_phase5_blocks_still_work(tmp_path):
    """TOML with [ship] + [memory] — Phase 5 field unaffected by Phase 6 additions."""
    p = _write_base_template(
        tmp_path,
        """[ship]
coverage_threshold = 0.5

[memory]
""",
    )
    tmpl = _parse_toml(p)
    assert tmpl.ship is not None
    assert tmpl.ship.coverage_threshold == 0.5
    # Empty [memory] block uses all defaults.
    assert tmpl.memory is not None
    assert tmpl.memory.conflict_threshold == 0.75  # default
    assert tmpl.memory.retention_pattern_days == 90
    assert tmpl.memory.retention_incident_days == 180
