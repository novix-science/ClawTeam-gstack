"""Tests for TemplateDef Phase 7 sub-blocks (Plan 07-01 Task 4).

Verifies [conductor]/[attention]/[cost] optional top-level sub-blocks
on TemplateDef:

- BC: existing templates (gstack + 6 bundled) parse with all three new
  fields == None.
- Each block parses into its pydantic config with defaults applied.
- Invalid field values rejected at pydantic validation time.
- Phase 5 + Phase 6 sub-blocks still work in presence of Phase 7 additions.

Mirrors ``tests/test_template_def_phase6_blocks.py`` shape verbatim.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from clawteam.templates import (
    AttentionConfig,
    ConductorConfig,
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


def test_bc_gstack_parses_without_phase7_blocks():
    tmpl = _parse_toml(_TEMPLATES_DIR / "gstack.toml")
    assert isinstance(tmpl, TemplateDef)
    assert tmpl.conductor is None
    assert tmpl.attention is None


@pytest.mark.parametrize("name", PACKAGED_TEMPLATES)
def test_bc_packaged_template_parses(name: str):
    tmpl = load_template(name)
    assert tmpl.conductor is None
    assert tmpl.attention is None


# ── Helper ───────────────────────────────────────────────────────────────


def _write_base_template(tmp_path: Path, extra: str = "", filename: str = "test.toml") -> Path:
    content = """[template]
name = "test"

[template.leader]
name = "lead"
type = "general-purpose"
"""
    if extra:
        content += "\n" + extra + "\n"
    p = tmp_path / filename
    p.write_text(content)
    return p


# ── [conductor] parsing ──────────────────────────────────────────────────


def test_conductor_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        (
            "[conductor]\n"
            "max_concurrent_sprints = 20\n"
            "max_tasks_per_agent = 2\n"
            "max_active_agents = 8\n"
            "acquire_timeout_seconds = 120.0\n"
        ),
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.conductor, ConductorConfig)
    assert tmpl.conductor.max_concurrent_sprints == 20
    assert tmpl.conductor.max_tasks_per_agent == 2
    assert tmpl.conductor.max_active_agents == 8
    assert tmpl.conductor.acquire_timeout_seconds == 120.0


def test_conductor_defaults(tmp_path):
    """Partial [conductor] block — unset fields fall back to ConductorConfig defaults."""
    p = _write_base_template(tmp_path, "[conductor]\nmax_concurrent_sprints = 15")
    tmpl = _parse_toml(p)
    assert tmpl.conductor is not None
    assert tmpl.conductor.max_concurrent_sprints == 15
    assert tmpl.conductor.max_tasks_per_agent == 1  # default
    assert tmpl.conductor.max_active_agents == 6  # default
    assert tmpl.conductor.acquire_timeout_seconds == 60.0  # default


def test_conductor_max_concurrent_zero_rejected(tmp_path):
    p = _write_base_template(tmp_path, "[conductor]\nmax_concurrent_sprints = 0")
    with pytest.raises(ValidationError):
        _parse_toml(p)


# ── [attention] parsing ──────────────────────────────────────────────────


def test_attention_block_parsed(tmp_path):
    p = _write_base_template(
        tmp_path,
        (
            "[attention]\n"
            "urgency_weight = 15\n"
            "blocking_weight = 8\n"
            "[attention.tag_weights]\n"
            "design = 3\n"
            "security = 5\n"
        ),
    )
    tmpl = _parse_toml(p)
    assert isinstance(tmpl.attention, AttentionConfig)
    assert tmpl.attention.urgency_weight == 15
    assert tmpl.attention.blocking_weight == 8
    assert tmpl.attention.tag_weights == {"design": 3, "security": 5}


def test_attention_defaults(tmp_path):
    p = _write_base_template(tmp_path, "[attention]\nurgency_weight = 20")
    tmpl = _parse_toml(p)
    assert tmpl.attention is not None
    assert tmpl.attention.urgency_weight == 20
    assert tmpl.attention.blocking_weight == 5  # default
    assert tmpl.attention.tag_weights == {}  # default


# ── [cost] parsing ───────────────────────────────────────────────────────


# [cost] block + CostConfig removed post-v1.0 UAT 2026-04-22. The 3 prior
# tests (cost_block_parsed, cost_defaults, cost_fallback_at_percent_over_100_rejected)
# are deleted; cross-regression test below no longer touches cost.


# ── Phase 5 / Phase 6 cross-regression ──────────────────────────────────


def test_phase5_6_blocks_still_work_with_phase7(tmp_path):
    """TOML with [ship] + [memory] — Phase 5/6 sub-blocks coexist."""
    p = _write_base_template(
        tmp_path,
        (
            "[ship]\n"
            "coverage_threshold = 0.6\n"
            "\n"
            "[memory]\n"
            "conflict_threshold = 0.8\n"
        ),
    )
    tmpl = _parse_toml(p)
    assert tmpl.ship is not None
    assert tmpl.ship.coverage_threshold == 0.6
    assert tmpl.memory is not None
    assert tmpl.memory.conflict_threshold == 0.8
    # Phase 6 memory_layout (legacy dict field) unaffected.
    assert tmpl.memory_layout == {}
