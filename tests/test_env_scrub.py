"""Tests for clawteam.secrets — env deny-filter scrubber (QUALITY-15)."""

import pytest

from clawteam.secrets import scrub_env


class TestScrubEnv:
    """scrub_env redacts values whose key matches the secret deny-pattern."""

    @pytest.mark.parametrize(
        "key",
        [
            "API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "SECRET_TOKEN",
            "MY_PASSWORD",
            "DB_PASSWORD",
            "BEARER_TOKEN",
            "CREDENTIAL_FILE",
            "GITHUB_TOKEN",
            "CLIENT_SECRET",
            "AWS_ACCESS_KEY_ID",
            "SSH_PRIVATE_KEY",
            "lower_case_secret",
            "MixedCaseToken",
        ],
    )
    def test_matching_keys_are_redacted(self, key):
        result = scrub_env({key: "sensitive-value", "SAFE": "ok"})
        assert result[key] == "[REDACTED]"
        assert result["SAFE"] == "ok"

    @pytest.mark.parametrize(
        "key",
        [
            "PATH",
            "HOME",
            "USER",
            "LANG",
            "LC_CTYPE",
            "CLAWTEAM_AGENT_NAME",
            "CLAWTEAM_DATA_DIR",
            "CLAWTEAM_TEAM_NAME",
            "OH_AGENT_NAME",
            "CLAUDE_CODE_AGENT_NAME",
            "ANTHROPIC_BASE_URL",
            "OPENAI_BASE_URL",
        ],
    )
    def test_non_matching_keys_are_untouched(self, key):
        result = scrub_env({key: "value"})
        assert result[key] == "value"

    def test_input_dict_is_not_mutated(self):
        env = {"API_KEY": "abc", "PATH": "/bin"}
        scrub_env(env)
        assert env == {"API_KEY": "abc", "PATH": "/bin"}

    def test_returns_dict_not_mapping(self):
        result = scrub_env({})
        assert isinstance(result, dict)

    def test_empty_env(self):
        assert scrub_env({}) == {}

    def test_redact_placeholder_value(self):
        result = scrub_env({"API_KEY": "sk-xxx"})
        assert result["API_KEY"] == "[REDACTED]"


def test_shell_hook_env_snapshot_redacts_parent_secrets(tmp_path, monkeypatch):
    """End-to-end: a parent-env API key must NOT reach the spawned shell hook."""
    from clawteam.events.bus import EventBus
    from clawteam.events.hooks import HookDef, HookManager
    from clawteam.events.types import WorkerExit

    monkeypatch.setenv("MY_API_KEY", "super-secret-value")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_should-not-leak")
    monkeypatch.setenv("DB_PASSWORD", "hunter2")

    dump = tmp_path / "env.dump"
    bus = EventBus()
    mgr = HookManager(bus)
    hook = HookDef(
        event="WorkerExit",
        action="shell",
        command=f'env > "{dump}"',
    )
    assert mgr.register_hook(hook) is True

    bus.emit(WorkerExit(team_name="t", agent_name="a"))

    content = dump.read_text()
    assert "super-secret-value" not in content
    assert "ghp_should-not-leak" not in content
    assert "hunter2" not in content
    assert "CLAWTEAM_EVENT_TYPE=WorkerExit" in content
    assert "CLAWTEAM_TEAM_NAME=t" in content
    assert "CLAWTEAM_AGENT_NAME=a" in content
