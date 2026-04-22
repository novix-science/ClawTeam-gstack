"""Phase 3 Wave 1 (Plan 03-02 Task 2) - gstack.toml roster tests.

Covers TEAM-01, TEAM-02, TEAM-05 + D-04 (no starter tasks) + Pattern 4
leader_role field + 7-phase declaration.

Originally scaffolded under Plan 03-01 as skipped stubs. Wave 1 (Plan 03-02)
ships `gstack.toml` and extends `TemplateDef`, so all stubs are now active.
"""

from __future__ import annotations

from clawteam.templates import load_template


class TestLoadGstackTemplate:
    def test_parses_via_existing_loader(self):
        """TEAM-01: gstack.toml round-trips through the existing TemplateDef loader."""
        tmpl = load_template("gstack")
        assert tmpl.name == "gstack"

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

    def test_no_starter_tasks(self):
        """D-04: gstack.toml has NO [[template.tasks]] rows."""
        assert load_template("gstack").tasks == []

    def test_leader_role_field(self):
        """Pattern 4: gstack.toml declares leader_role='ceo' on [template] block."""
        assert load_template("gstack").leader_role == "ceo"

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

    def test_model_profile_defaults_to_balanced(self):
        """TEAM-05: model_profile.default == 'balanced'; 'quality'/'budget' selectable."""
        tmpl = load_template("gstack")
        assert tmpl.model_profile.get("default") == "balanced"

    def test_model_profile_per_role_assignments(self):
        """TEAM-05: hyphenated role keys (`eng-mgr`, `dx-lead`) round-trip quoted."""
        mp = load_template("gstack").model_profile
        assert mp.get("pm") == "opus"
        assert mp.get("ceo") == "opus"
        assert mp.get("eng-mgr") == "sonnet"
        assert mp.get("dx-lead") == "sonnet"
        assert mp.get("engineer") == "sonnet"
        assert mp.get("shipper") == "haiku"
        assert mp.get("sre") == "haiku"

    def test_memory_block_declared(self):
        """D-05: [template.memory] declares root + per_role for TeamManager pre-creation.

        Phase 6 (Plan 06-01 Task 3): the Phase 3 `memory` dict field was
        renamed to `memory_layout` to free up `memory` for the new
        Phase 6 MemoryConfig sub-block. The `[template.memory]` TOML key
        is preserved (legacy BC); _parse_toml reads it into the
        `memory_layout` field.
        """
        layout = load_template("gstack").memory_layout
        assert layout.get("root") == "{data_dir}/teams/{team_name}/memory"
        assert layout.get("per_role") is True

    def test_agents_reference_prompt_files(self):
        """D-06: every agent (leader + 10 specialists) declares prompt_file under gstack/prompts/."""
        tmpl = load_template("gstack")
        for agent in [tmpl.leader, *tmpl.agents]:
            assert agent.role, f"agent {agent.name!r} missing role"
            assert agent.prompt_file.startswith("gstack/prompts/"), (
                f"agent {agent.name!r} prompt_file={agent.prompt_file!r}"
            )
            assert agent.prompt_file.endswith(f"/{agent.role}.md"), (
                f"agent {agent.name!r} prompt_file/role mismatch"
            )
