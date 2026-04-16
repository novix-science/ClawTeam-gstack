"""Backwards-compatibility regression matrix for packaged template launches.

Exercises every packaged template's ``clawteam launch <template>`` flow through
a RecordingBackend mock. This covers launch-path compatibility only; prompt and
task-content semantics stay covered by ``tests/test_templates.py``.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app

# If the packaged template set changes, keep this list aligned with
# tests/test_templates.py so structure and launch coverage move together.
TEMPLATE_NAMES: list[str] = [
    "software-dev",
    "hedge-fund",
    "code-review",
    "harness-default",
    "research-paper",
    "strategy-room",
]


class RecordingBackend:
    """Capture spawn calls without starting real subprocesses."""

    def __init__(self):
        self.calls = []

    def spawn(self, **kwargs):
        self.calls.append(kwargs)
        return f"Agent '{kwargs['agent_name']}' spawned"

    def list_running(self):
        return []


@pytest.mark.parametrize("template", TEMPLATE_NAMES)
def test_template_launches_cleanly(template, monkeypatch, tmp_path):
    """Each packaged template must launch cleanly through the CLI."""

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    team_name = f"bc-matrix-{template}"
    result = runner.invoke(
        app,
        [
            "launch",
            template,
            "--team",
            team_name,
            "--goal",
            "BC regression smoke goal",
        ],
        env={
            "HOME": str(tmp_path),
            "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        },
    )

    assert result.exit_code == 0, (
        f"launch {template} failed (exit={result.exit_code}):\n{result.output}"
    )
    assert backend.calls, f"no agents spawned for {template}"

    for call in backend.calls:
        assert call.get("agent_name"), f"{template}: empty agent_name in spawn call"
        assert call.get("team_name") == team_name, (
            f"{template}: team_name mismatch: {call.get('team_name')!r}"
        )
        assert call.get("command"), f"{template}: empty command list in spawn call"
        assert isinstance(call["command"], list), (
            f"{template}: command is not a list: {type(call['command'])!r}"
        )


@pytest.mark.parametrize("template", TEMPLATE_NAMES)
def test_template_spawn_calls_preserve_skip_permissions_flag(
    template, monkeypatch, tmp_path
):
    """Each packaged template should inherit the default skip_permissions flag."""

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "launch",
            template,
            "--team",
            f"skip-perms-{template}",
            "--goal",
            "BC regression - skip_permissions propagation",
        ],
        env={
            "HOME": str(tmp_path),
            "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        },
    )

    assert result.exit_code == 0, (
        f"launch {template} failed for skip_permissions test:\n{result.output}"
    )
    assert backend.calls
    assert all(call.get("skip_permissions") is True for call in backend.calls), (
        f"{template}: one or more spawn calls had skip_permissions != True"
    )
