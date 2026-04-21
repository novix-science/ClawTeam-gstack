"""Tests for clawteam.templates — loading, parsing, and variable substitution."""

import pytest

from clawteam.templates import (
    AgentDef,
    ReviewConfig,
    ReviewRule,
    TaskDef,
    TemplateDef,
    _SafeDict,
    list_templates,
    load_template,
    render_task,
)


class TestRenderTask:
    def test_basic_substitution(self):
        result = render_task("Analyze {goal} for {team_name}", goal="AAPL", team_name="alpha")
        assert result == "Analyze AAPL for alpha"

    def test_unknown_placeholders_kept(self):
        """Variables we don't provide should stay as {placeholder}."""
        result = render_task("Hello {name}, team is {team_name}", name="bob")
        assert result == "Hello bob, team is {team_name}"

    def test_no_variables(self):
        result = render_task("plain text with no placeholders")
        assert result == "plain text with no placeholders"

    def test_empty_string(self):
        assert render_task("") == ""

    def test_multiple_same_variable(self):
        result = render_task("{x} and {x}", x="foo")
        assert result == "foo and foo"


class TestSafeDict:
    def test_missing_key_returns_placeholder(self):
        d = _SafeDict(a="1")
        assert d["a"] == "1"
        # missing key wrapped back into braces
        assert "{missing}".format_map(d) == "{missing}"


class TestModels:
    def test_agent_def_defaults(self):
        a = AgentDef(name="worker")
        assert a.type == "general-purpose"
        assert a.task == ""
        assert a.command is None

    def test_task_def(self):
        t = TaskDef(subject="Build feature", description="details", owner="alice")
        assert t.subject == "Build feature"

    def test_template_def_defaults(self):
        leader = AgentDef(name="lead")
        t = TemplateDef(name="my-tmpl", leader=leader)
        assert t.description == ""
        assert t.command == ["claude"]
        assert t.backend == "tmux"
        assert t.agents == []
        assert t.tasks == []


class TestLoadBuiltinTemplate:
    def test_load_hedge_fund(self):
        tmpl = load_template("hedge-fund")
        assert tmpl.name == "hedge-fund"
        assert tmpl.leader.name == "portfolio-manager"
        assert len(tmpl.agents) > 0
        assert len(tmpl.tasks) > 0

    def test_leader_type(self):
        tmpl = load_template("hedge-fund")
        assert tmpl.leader.type == "portfolio-manager"

    def test_agents_have_tasks(self):
        tmpl = load_template("hedge-fund")
        for agent in tmpl.agents:
            assert agent.task != "", f"Agent '{agent.name}' has no task text"

    def test_task_owners_match_agents(self):
        tmpl = load_template("hedge-fund")
        agent_names = {tmpl.leader.name} | {a.name for a in tmpl.agents}
        for task in tmpl.tasks:
            if task.owner:
                assert task.owner in agent_names, f"Task owner '{task.owner}' not in agents"

    def test_load_strategy_room(self):
        tmpl = load_template("strategy-room")
        assert tmpl.name == "strategy-room"
        assert tmpl.leader.name == "strategy-lead"
        assert len(tmpl.agents) == 4
        assert len(tmpl.tasks) == 5

    def test_load_software_dev(self):
        tmpl = load_template("software-dev")
        assert tmpl.name == "software-dev"
        assert tmpl.leader.name == "tech-lead"
        assert len(tmpl.agents) == 4
        assert len(tmpl.tasks) == 5

    def test_software_dev_task_owners_match_agents(self):
        tmpl = load_template("software-dev")
        agent_names = {tmpl.leader.name} | {agent.name for agent in tmpl.agents}
        for task in tmpl.tasks:
            if task.owner:
                assert task.owner in agent_names

    def test_strategy_room_agent_names(self):
        tmpl = load_template("strategy-room")
        names = {agent.name for agent in tmpl.agents}
        assert names == {
            "systems-analyst",
            "delivery-planner",
            "risk-mapper",
            "decision-editor",
        }

    def test_strategy_room_task_owners_match_agents(self):
        tmpl = load_template("strategy-room")
        agent_names = {tmpl.leader.name} | {a.name for a in tmpl.agents}
        for task in tmpl.tasks:
            if task.owner:
                assert task.owner in agent_names, f"Task owner '{task.owner}' not in agents"

    def test_strategy_room_specialists_route_to_decision_editor(self):
        tmpl = load_template("strategy-room")
        for agent in tmpl.agents:
            if agent.name == "decision-editor":
                continue
            assert "decision-editor" in agent.task
            assert "strategy-lead" not in agent.task

    def test_strategy_room_decision_editor_routes_to_strategy_lead(self):
        tmpl = load_template("strategy-room")
        decision_editor = next(agent for agent in tmpl.agents if agent.name == "decision-editor")
        assert "strategy-lead" in decision_editor.task
        assert "Do not recommend the final path yourself" in decision_editor.task

    def test_strategy_room_leader_waits_for_decision_editor_memo(self):
        tmpl = load_template("strategy-room")
        assert "Wait for the decision-editor's strategy memo" in tmpl.leader.task
        assert "supporting specialist outputs" not in tmpl.leader.task


class TestPhase3AdditiveFields:
    """Phase 3 Plan 03-02 Task 1 — strict-additive field extensions.

    Verifies that the 7 new optional fields land with empty defaults and that
    all 6 existing packaged templates continue to load unchanged.
    """

    def test_agent_def_new_fields_default_empty(self):
        a = AgentDef(name="worker")
        # Phase 3 (D-06) additive fields:
        assert a.role == ""
        assert a.prompt_file == ""
        assert a.model_profile == ""

    def test_agent_def_new_fields_populated(self):
        a = AgentDef(
            name="pm",
            role="pm",
            prompt_file="gstack/prompts/pm.md",
            model_profile="opus",
        )
        assert a.role == "pm"
        assert a.prompt_file == "gstack/prompts/pm.md"
        assert a.model_profile == "opus"

    def test_template_def_new_fields_default_empty(self):
        leader = AgentDef(name="lead")
        t = TemplateDef(name="my-tmpl", leader=leader)
        # Phase 3 (D-04 / D-05) additive fields:
        assert t.leader_role == ""
        assert t.phases == []
        assert t.model_profile == {}
        assert t.memory == {}

    @pytest.mark.parametrize(
        "template_name",
        [
            "software-dev",
            "hedge-fund",
            "code-review",
            "harness-default",
            "research-paper",
            "strategy-room",
        ],
    )
    def test_existing_template_loads_with_empty_phase3_defaults(self, template_name):
        """Pattern 1 BC: existing 6 templates parse and carry empty Phase 3 defaults."""
        tmpl = load_template(template_name)
        assert tmpl.leader_role == ""
        assert tmpl.phases == []
        assert tmpl.model_profile == {}
        assert tmpl.memory == {}
        # AgentDef.role defaults to "" for every agent in existing templates:
        for agent in [tmpl.leader, *tmpl.agents]:
            assert agent.role == ""
            assert agent.prompt_file == ""
            assert agent.model_profile == ""

    def test_parse_toml_reads_new_template_fields_when_present(
        self, tmp_path, monkeypatch
    ):
        """_parse_toml reads leader_role, phases, model_profile, memory from [template] block."""
        user_tpl_dir = tmp_path / ".clawteam" / "templates"
        user_tpl_dir.mkdir(parents=True)

        toml_content = """\
[template]
name = "phase3-additive-probe"
description = "Probes Phase 3 additive field parsing"
leader_role = "ceo"
phases = ["think", "plan"]

[template.model_profile]
default = "balanced"
pm = "opus"

[template.memory]
root = "{data_dir}/teams/{team_name}/memory"
per_role = true

[template.leader]
name = "ceo"
type = "strategic-leader"
role = "ceo"
prompt_file = "gstack/prompts/ceo.md"

[[template.agents]]
name = "pm"
type = "yc-advisor"
role = "pm"
prompt_file = "gstack/prompts/pm.md"
model_profile = "opus"
"""
        (user_tpl_dir / "phase3-additive-probe.toml").write_text(toml_content)

        import clawteam.templates as tmod
        monkeypatch.setattr(tmod, "_USER_DIR", user_tpl_dir)

        tmpl = load_template("phase3-additive-probe")
        assert tmpl.leader_role == "ceo"
        assert tmpl.phases == ["think", "plan"]
        assert tmpl.model_profile == {
            "default": "balanced",
            "pm": "opus",
        }
        assert tmpl.memory == {
            "root": "{data_dir}/teams/{team_name}/memory",
            "per_role": True,
        }
        assert tmpl.leader.role == "ceo"
        assert tmpl.leader.prompt_file == "gstack/prompts/ceo.md"
        assert tmpl.agents[0].role == "pm"
        assert tmpl.agents[0].prompt_file == "gstack/prompts/pm.md"
        assert tmpl.agents[0].model_profile == "opus"


class TestLoadTemplateNotFound:
    def test_missing_template_raises(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            load_template("this-does-not-exist-anywhere")


class TestUserTemplateOverride:
    def test_user_template_takes_priority(self, tmp_path, monkeypatch):
        """User templates in ~/.clawteam/templates/ override builtins."""
        user_tpl_dir = tmp_path / ".clawteam" / "templates"
        user_tpl_dir.mkdir(parents=True)

        toml_content = """\
[template]
name = "custom"
description = "User override"

[template.leader]
name = "my-leader"
type = "custom-leader"
"""
        (user_tpl_dir / "custom.toml").write_text(toml_content)

        # patch the module-level _USER_DIR
        import clawteam.templates as tmod

        monkeypatch.setattr(tmod, "_USER_DIR", user_tpl_dir)

        tmpl = load_template("custom")
        assert tmpl.name == "custom"
        assert tmpl.leader.name == "my-leader"
        assert tmpl.description == "User override"


class TestListTemplates:
    def test_list_includes_builtin(self):
        templates = list_templates()
        names = {t["name"] for t in templates}
        assert "hedge-fund" in names
        assert "strategy-room" in names
        assert "software-dev" in names

    def test_list_entry_format(self):
        templates = list_templates()
        for t in templates:
            assert "name" in t
            assert "description" in t
            assert "source" in t
            assert t["source"] in ("builtin", "user")


# ── Phase 4 Plan 04-06 tests: TemplateDef review-config extension ─────────
# Source: §04-CONTEXT D-04 / A5. Covers ReviewRule / ReviewConfig pydantic
# models, _parse_toml extension, BC preservation across 6 non-gstack
# templates, and the 6+ rule rows shipped by gstack.toml in Task 3.


class TestReviewConfigModels:
    def test_review_config_default_empty(self):
        leader = AgentDef(name="x", role="x")
        t = TemplateDef(name="t", leader=leader)
        assert isinstance(t.review, ReviewConfig)
        assert t.review.rules == []
        assert t.review.sycophancy_threshold == 0.9

    def test_review_rule_pattern_required(self):
        with pytest.raises(Exception):  # noqa: B017 — pydantic ValidationError
            ReviewRule(pattern="", reviewers=["designer"])

    def test_review_rule_reviewers_default_empty(self):
        r = ReviewRule(pattern="x")
        assert r.reviewers == []
        assert r.signal == ""

    def test_review_rule_fields_populated(self):
        r = ReviewRule(
            pattern="src/components/**/*.tsx",
            reviewers=["designer"],
            signal="ui",
        )
        assert r.pattern == "src/components/**/*.tsx"
        assert r.reviewers == ["designer"]
        assert r.signal == "ui"

    def test_review_config_sycophancy_threshold_range(self):
        with pytest.raises(Exception):  # noqa: B017
            ReviewConfig(sycophancy_threshold=1.5)
        with pytest.raises(Exception):  # noqa: B017
            ReviewConfig(sycophancy_threshold=-0.1)


class TestReviewConfigParsingBC:
    """BC: the 6 existing non-gstack templates declare no [template.review]
    block; they must parse without error and carry an empty ReviewConfig."""

    @pytest.mark.parametrize(
        "template_name",
        [
            "software-dev",
            "hedge-fund",
            "code-review",
            "harness-default",
            "research-paper",
            "strategy-room",
        ],
    )
    def test_existing_template_parses_without_review_block(self, template_name):
        t = load_template(template_name)
        assert isinstance(t.review, ReviewConfig)
        assert t.review.rules == []
        assert t.review.sycophancy_threshold == 0.9


class TestReviewConfigParsingExplicit:
    def test_parse_toml_reads_review_block(self, tmp_path, monkeypatch):
        user_tpl_dir = tmp_path / ".clawteam" / "templates"
        user_tpl_dir.mkdir(parents=True)

        toml_content = """\
[template]
name = "review-probe"
description = "Probes review-config parsing"

[template.leader]
name = "lead"
type = "x"
role = "lead"

[template.review]
sycophancy_threshold = 0.85

[[template.review.rules]]
pattern = "src/components/**/*.tsx"
reviewers = ["designer"]
signal = "ui"

[[template.review.rules]]
pattern = "**/crypto/**"
reviewers = ["security"]
signal = "crypto"
"""
        (user_tpl_dir / "review-probe.toml").write_text(toml_content)

        import clawteam.templates as tmod
        monkeypatch.setattr(tmod, "_USER_DIR", user_tpl_dir)

        tmpl = load_template("review-probe")
        assert tmpl.review.sycophancy_threshold == 0.85
        assert len(tmpl.review.rules) == 2
        assert tmpl.review.rules[0].pattern == "src/components/**/*.tsx"
        assert tmpl.review.rules[0].reviewers == ["designer"]
        assert tmpl.review.rules[0].signal == "ui"
        assert tmpl.review.rules[1].pattern == "**/crypto/**"
        assert tmpl.review.rules[1].reviewers == ["security"]
        assert tmpl.review.rules[1].signal == "crypto"


class TestGstackTemplateReview:
    """Gstack template ships with 6+ [[template.review.rules]] rows.

    This test hinges on Task 3 having extended gstack.toml; when running
    Task 1 TDD in isolation it will fail (acceptable intermediate state
    per <acceptance_criteria>). Re-checked in Task 3 verify block.
    """

    def test_gstack_template_has_review_rules(self):
        t = load_template("gstack")
        assert len(t.review.rules) >= 6
        # Floor check: rules must name at least one of the decorrelation
        # roles so the router has something to accumulate.
        all_reviewers = {r for rule in t.review.rules for r in rule.reviewers}
        assert {"designer", "security", "dx-lead"}.issubset(all_reviewers)
