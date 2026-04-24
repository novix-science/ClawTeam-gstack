from __future__ import annotations

from typer.testing import CliRunner

from clawteam.cli.commands import app
from clawteam.events.bus import EventBus
from clawteam.events.types import TaskCompleted
from clawteam.sprint.phase_completion_watcher import PhaseCompletionWatcher
from clawteam.sprint.state import SprintState, save_sprint_state
from clawteam.store.file import FileTaskStore
from clawteam.team.manager import TeamManager
from clawteam.team.models import TaskStatus


def _setup_team(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    TeamManager.create_team(
        name="demo",
        leader_name="ceo",
        leader_id="ceo-id",
        roles=["ceo", "pm", "engineer"],
        leader_role="ceo",
        template="gstack",
    )


def test_phase_completion_watcher_wakes_leader_when_tasks_and_artifacts_complete(
    monkeypatch, tmp_path
):
    _setup_team(monkeypatch, tmp_path)
    state = SprintState(
        sprint_id="abc12345",
        goal="g",
        team="demo",
        current_phase="think",
        artifacts={"delegation.json": "---\nartifact_type: delegation\n---\n"},
    )
    save_sprint_state(state)
    store = FileTaskStore("demo")
    task = store.create("delegate", owner="pm", metadata={"phase": "think"})
    store.update(task.id, status=TaskStatus.completed)

    captured: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        "clawteam.sprint.phase_completion_watcher.wake_agent",
        lambda team, agent, kind, preview="", force=False: captured.append(
            (team, agent, kind, preview)
        )
        or True,
    )

    bus = EventBus()
    PhaseCompletionWatcher("demo").register(bus)
    bus.emit(TaskCompleted(team_name="demo", task_id=task.id, owner="pm"))

    assert captured == [
        (
            "demo",
            "ceo",
            "phase",
            "All think phase work complete (1 tasks done, 1 artifacts present). "
            "Run 'clawteam sprint advance abc12345 --team demo' to advance.",
        )
    ]


def test_phase_completion_watcher_does_not_wake_when_artifact_missing(
    monkeypatch, tmp_path
):
    _setup_team(monkeypatch, tmp_path)
    state = SprintState(
        sprint_id="abc12345",
        goal="g",
        team="demo",
        current_phase="think",
    )
    save_sprint_state(state)
    store = FileTaskStore("demo")
    task = store.create("delegate", owner="pm", metadata={"phase": "think"})
    store.update(task.id, status=TaskStatus.completed)

    captured: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        "clawteam.sprint.phase_completion_watcher.wake_agent",
        lambda team, agent, kind, preview="", force=False: captured.append(
            (team, agent, kind, preview)
        )
        or True,
    )

    bus = EventBus()
    PhaseCompletionWatcher("demo").register(bus)
    bus.emit(TaskCompleted(team_name="demo", task_id=task.id, owner="pm"))

    assert captured == []


def test_wake_agent_formats_phase_wake(monkeypatch, tmp_path):
    from clawteam import wake

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(wake, "_find_agent_pane", lambda team, agent: "%1")
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return type("Result", (), {"returncode": 0, "stdout": ""})()

    monkeypatch.setattr(wake.subprocess, "run", fake_run)

    assert wake.wake_agent("demo", "ceo", "phase", "All think phase work complete.", force=True)
    assert any("[wake:phase] All think phase work complete." in cmd for cmd in commands[0])


def test_task_update_cli_registers_phase_completion_watcher(monkeypatch, tmp_path):
    from clawteam.events.bus import EventBus
    from clawteam.events.global_bus import reset_event_bus

    _setup_team(monkeypatch, tmp_path)
    save_sprint_state(
        SprintState(
            sprint_id="abc12345",
            goal="g",
            team="demo",
            current_phase="think",
            artifacts={"delegation.json": "---\nartifact_type: delegation\n---\n"},
        )
    )
    task = FileTaskStore("demo").create("delegate", owner="pm", metadata={"phase": "think"})

    captured: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        "clawteam.sprint.phase_completion_watcher.wake_agent",
        lambda team, agent, kind, preview="", force=False: captured.append(
            (team, agent, kind, preview)
        )
        or True,
    )
    monkeypatch.setattr(EventBus, "emit_async", lambda self, event: self.emit(event))
    reset_event_bus()

    result = CliRunner().invoke(
        app,
        ["task", "update", "demo", task.id, "--status", "completed"],
        env={
            "HOME": str(tmp_path),
            "CLAWTEAM_DATA_DIR": str(tmp_path),
            "CLAWTEAM_AGENT_NAME": "pm",
        },
    )

    assert result.exit_code == 0, result.output
    assert captured and captured[0][0:3] == ("demo", "ceo", "phase")
