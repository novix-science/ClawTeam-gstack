"""Scaffold for Phase 3 Wave 0 (Plan 03-01 Task 3).

Tests currently skipped — Wave 1 (Plan 03-02) unskips them as `gstack.toml`
and the extended `TemplateDef` loader ship.

Covers: TEAM-01, TEAM-02, TEAM-05 + D-04 (no starter tasks) + Pattern 4
leader_role field + 7-phase declaration.
"""

from __future__ import annotations

import pytest

# NB: load_template is already available in Phase 2. The ``gstack`` argument
# will raise until Wave 1 ships the TOML — every test below is @pytest.mark.skip
# so collection succeeds without touching that code path.
from clawteam.templates import load_template  # noqa: F401  (import-only — scaffold)


class TestLoadGstackTemplate:
    """Wave 0 scaffold — unskipped by Wave 1 (Plan 03-02)."""

    @pytest.mark.skip(reason="Wave 1: gstack.toml ships in 03-02-PLAN")
    def test_parses_via_existing_loader(self):
        """TEAM-01: gstack.toml round-trips through the existing TemplateDef loader."""
        tmpl = load_template("gstack")
        assert tmpl.name == "gstack"

    @pytest.mark.skip(reason="Wave 1: gstack.toml ships in 03-02-PLAN")
    def test_eleven_agents_with_distinct_roles(self):
        """TEAM-02: all 11 specialist roles present, distinct, named as the 11-agent roster."""
        tmpl = load_template("gstack")
        all_names = {tmpl.leader.name} | {a.name for a in tmpl.agents}
        assert len(all_names) == 11
        expected = {
            "ceo",
            "pm",
            "eng-mgr",
            "designer",
            "dx-lead",
            "engineer",
            "reviewer",
            "qa",
            "security",
            "shipper",
            "sre",
        }
        assert all_names == expected

    @pytest.mark.skip(reason="Wave 1: D-04 no starter tasks — gstack waits for /sprint start")
    def test_no_starter_tasks(self):
        """D-04: gstack.toml has NO [[template.tasks]] rows."""
        assert load_template("gstack").tasks == []

    @pytest.mark.skip(reason="Wave 1: Pattern 4 leader_role")
    def test_leader_role_field(self):
        """Pattern 4: gstack.toml declares leader_role='ceo' on [template] block."""
        assert load_template("gstack").leader_role == "ceo"

    @pytest.mark.skip(reason="Wave 1: 7-phase declaration")
    def test_phases_field(self):
        """D-04: gstack.toml declares the 7 gstack phases verbatim, in order."""
        assert load_template("gstack").phases == [
            "think",
            "plan",
            "build",
            "review",
            "test",
            "ship",
            "reflect",
        ]

    @pytest.mark.skip(reason="Wave 1: TEAM-05 model profile default")
    def test_model_profile_defaults_to_balanced(self):
        """TEAM-05: model_profile.default == 'balanced'; 'quality'/'budget' selectable."""
        tmpl = load_template("gstack")
        assert tmpl.model_profile.get("default") == "balanced"
