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
            "SECRET_TOKEN",
            "MY_PASSWORD",
            "BEARER_TOKEN",
            "CREDENTIAL_FILE",
            "lower_case_secret",
        ],
    )
    def test_matching_keys_are_redacted(self, key):
        result = scrub_env({key: "sensitive-value", "SAFE": "ok"})
        assert result[key] == "[REDACTED]"
        assert result["SAFE"] == "ok"


def test_shell_hook_env_snapshot_redacts_parent_secrets(tmp_path, monkeypatch):
    """End-to-end: a parent-env API key must NOT reach the spawned shell hook."""
    from clawteam.events.bus import EventBus
    from clawteam.events.hooks import HookDef, HookManager
    from clawteam.events.types import WorkerExit

    monkeypatch.setenv("MY_API_KEY", "super-secret-value")

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
    assert "CLAWTEAM_EVENT_TYPE=WorkerExit" in content
