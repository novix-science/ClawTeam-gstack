"""Subprocess-backed gstack sprint lifecycle regression test."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

AGENTS = [
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
]


def _run_cli(
    args: list[str],
    *,
    env: dict[str, str],
    input_text: str | None = None,
) -> str:
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "clawteam.cli.commands", *args],
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"clawteam {' '.join(args)} failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
    return result.stdout


def _wait_for_lines(path: Path, expected: int) -> list[str]:
    deadline = time.time() + 5
    while time.time() < deadline:
        if path.is_file():
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) >= expected:
                return lines
        time.sleep(0.05)
    return path.read_text(encoding="utf-8").splitlines() if path.is_file() else []


def _install_fake_bins(bin_dir: Path) -> None:
    claude = bin_dir / "claude"
    claude.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"$CLAWTEAM_AGENT_NAME\" >> \"$CLAUDE_LOG\"\n"
        "exit 42\n",
        encoding="utf-8",
    )
    claude.chmod(0o755)

    tmux = bin_dir / "tmux"
    tmux.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"has-session\" ]; then exit 0; fi\n"
        "if [ \"$1\" = \"list-panes\" ]; then cat \"$TMUX_PANES_FILE\"; exit 0; fi\n"
        "if [ \"$1\" = \"send-keys\" ]; then echo \"$*\" >> \"$WAKE_LOG\"; exit 0; fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    tmux.chmod(0o755)

    clawteam = bin_dir / "clawteam"
    clawteam.write_text(
        "#!/bin/sh\n"
        f"PYTHONPATH={Path.cwd()}${{PYTHONPATH:+:$PYTHONPATH}} "
        f"exec {sys.executable} -m clawteam.cli.commands \"$@\"\n",
        encoding="utf-8",
    )
    clawteam.chmod(0o755)


def _write_config(home: Path, event_log: Path) -> None:
    cfg_dir = home / ".clawteam"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    command = (
        f"{sys.executable} -c "
        "\"import os,pathlib;"
        "p=pathlib.Path(os.environ['EVENT_LOG']);"
        "p.parent.mkdir(parents=True, exist_ok=True);"
        "p.open('a', encoding='utf-8').write("
        "os.environ.get('CLAWTEAM_FROM_PHASE','') + '>' + "
        "os.environ.get('CLAWTEAM_TO_PHASE','') + '\\n')\""
    )
    (cfg_dir / "config.json").write_text(
        json.dumps(
            {
                "hooks": [
                    {
                        "event": "PhaseTransition",
                        "action": "shell",
                        "command": command,
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def _artifact(artifact_type: str, sprint_id: str) -> str:
    now = "2026-04-24T00:00:00Z"
    long_arch = (
        "The sprint keeps the existing conductor as the lifecycle owner while "
        "agents communicate through persisted artifacts and event-driven wakeups."
    )
    long_problem = (
        "This regression sprint verifies that a gstack team can launch with the "
        "subprocess backend, write artifacts for every phase, advance through "
        "the lifecycle, and finish with durable state that future changes can inspect."
    )
    if artifact_type == "delegation":
        return (
            "---\n"
            "artifact_type: delegation\n"
            f"sprint_id: {sprint_id}\n"
            "delegated_roles:\n"
            "  - engineer\n"
            "  - qa\n"
            f"created_at: \"{now}\"\n"
            "---\n\n"
            "# Delegation\n\nReal delegation details for the regression sprint.\n"
        )
    if artifact_type == "architecture-lock":
        return (
            "---\n"
            "artifact_type: architecture-lock\n"
            f"sprint_id: {sprint_id}\n"
            f"architecture_lock: \"{long_arch}\"\n"
            f"created_at: \"{now}\"\n"
            "---\n\n"
            "# Architecture Lock\n\nThe conductor remains the phase boundary owner.\n"
        )
    if artifact_type == "diff":
        return (
            "---\n"
            "artifact_type: diff\n"
            f"sprint_id: {sprint_id}\n"
            "files_changed:\n"
            "  - tests/integration/test_gstack_sprint_end_to_end.py\n"
            f"created_at: \"{now}\"\n"
            "---\n\n"
            "# Diff\n\nIntegration coverage changed for the sprint lifecycle.\n"
        )
    if artifact_type == "review-report":
        return (
            "---\n"
            "artifact_type: review-report\n"
            "review_sha: abcdef1\n"
            "verdict: approved\n"
            "findings:\n"
            "  - lifecycle regression coverage is coherent\n"
            "reviewer_persona: reviewer\n"
            f"sprint_id: {sprint_id}\n"
            f"created_at: \"{now}\"\n"
            "---\n\n"
            "# Review Report\n\nReview details are specific to lifecycle behavior.\n"
        )
    if artifact_type == "test-report":
        return (
            "---\n"
            "artifact_type: test-report\n"
            f"test_command: \"{sys.executable} -V tests/integration/test_gstack_sprint_end_to_end.py\"\n"
            "passed: 1\n"
            "failed: 0\n"
            "output_excerpt: \"Python version command completed successfully for lifecycle verification.\"\n"
            "qa_mode: qa\n"
            f"sprint_id: {sprint_id}\n"
            f"created_at: \"{now}\"\n"
            "---\n\n"
            "# Test Report\n\nQA exercised the subprocess lifecycle regression.\n"
        )
    if artifact_type == "ship_approval":
        return (
            "---\n"
            "artifact_type: ship_approval\n"
            "approved_by: ceo\n"
            f"approved_at: \"{now}\"\n"
            "sha_at_approval: abcdef1\n"
            f"sprint_id: {sprint_id}\n"
            "---\n\n"
            "# Ship Approval\n\nThe regression sprint is approved for completion.\n"
        )
    if artifact_type == "retro":
        return (
            "---\n"
            "artifact_type: retro\n"
            "personas:\n"
            "  - ceo\n"
            "  - engineer\n"
            "what_worked:\n"
            "  - subprocess lifecycle coverage is deterministic\n"
            "what_failed: []\n"
            "key_lessons:\n"
            "  - shell hooks are the right process boundary for event assertions\n"
            f"sprint_id: {sprint_id}\n"
            f"created_at: \"{now}\"\n"
            "---\n\n"
            "# Retro\n\nThe team captured concrete learning from this lifecycle run.\n"
        )
    if artifact_type == "design-doc":
        return (
            "---\n"
            "artifact_type: design-doc\n"
            f"problem_statement: \"{long_problem}\"\n"
            "users: \"Maintainers need a deterministic test that catches lifecycle regressions before manual UAT.\"\n"
            "constraints: \"The test must avoid real external CLIs while still using subprocess launch and wake surfaces.\"\n"
            f"rationale: \"{long_problem}\"\n"
            "pm_verdict: proceed\n"
            "forcing_questions_addressed: [1, 2, 3, 4, 5, 6]\n"
            f"sprint_id: {sprint_id}\n"
            f"created_at: \"{now}\"\n"
            "---\n\n"
            "# Design Doc\n\nAll office-hours forcing questions are covered.\n"
        )
    raise AssertionError(f"unknown artifact type {artifact_type}")


def _load_state(team: str, sprint_id: str):
    from clawteam.sprint.state import load_sprint_state

    return load_sprint_state(team, sprint_id)


def _save_state(state) -> None:
    from clawteam.sprint.state import save_sprint_state

    save_sprint_state(state)


def _set_artifact(team: str, sprint_id: str, name: str, body: str) -> None:
    state = _load_state(team, sprint_id)
    state.artifacts[name] = body
    _save_state(state)


def _drop_artifact(team: str, sprint_id: str, name: str) -> None:
    state = _load_state(team, sprint_id)
    state.artifacts.pop(name, None)
    _save_state(state)


def test_gstack_sprint_lifecycle_subprocess_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data_dir = tmp_path / "data"
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    workspace = tmp_path / "workspace"
    event_log = tmp_path / "events.log"
    wake_log = tmp_path / "wake.log"
    claude_log = tmp_path / "claude.log"
    panes_file = tmp_path / "panes.txt"
    team = "e2e-gstack"

    bin_dir.mkdir()
    workspace.mkdir()
    _install_fake_bins(bin_dir)
    _write_config(home, event_log)
    panes_file.write_text(
        "\n".join(f"{idx}:%{idx}" for idx in range(len(AGENTS))) + "\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "CLAWTEAM_DATA_DIR": str(data_dir),
            "EVENT_LOG": str(event_log),
            "WAKE_LOG": str(wake_log),
            "CLAUDE_LOG": str(claude_log),
            "TMUX_PANES_FILE": str(panes_file),
            "PATH": f"{bin_dir}{os.pathsep}{env.get('PATH', '')}",
            "PYTHONPATH": f"{Path.cwd()}{os.pathsep}{env.get('PYTHONPATH', '')}",
        }
    )
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    _run_cli(
        [
            "--json",
            "launch",
            "gstack",
            "--goal",
            "exercise the full lifecycle",
            "--backend",
            "subprocess",
            "--team-name",
            team,
            "--no-workspace",
        ],
        env=env,
    )
    claude_lines = _wait_for_lines(claude_log, len(AGENTS))
    assert set(claude_lines) == set(AGENTS)

    pane_map = data_dir / "teams" / team / "tmux_pane_map.json"
    pane_map.write_text(
        json.dumps({str(idx): agent for idx, agent in enumerate(AGENTS)}),
        encoding="utf-8",
    )
    for agent in AGENTS:
        _run_cli(
            ["task", "create", team, f"wake {agent}", "--owner", agent],
            env=env,
        )
    wake_lines = _wait_for_lines(wake_log, len(AGENTS) * 2)
    wake_text_lines = [line for line in wake_lines if "[wake:task]" in line]
    assert len(wake_text_lines) >= len(AGENTS)
    for agent in AGENTS:
        assert any(f"wake {agent}" in line for line in wake_text_lines)

    start = json.loads(
        _run_cli(
            [
                "--json",
                "sprint",
                "start",
                "--team",
                team,
                "--goal",
                "exercise the full lifecycle",
            ],
            env=env,
        )
    )
    sprint_id = start["data"]["id"]
    state = _load_state(team, sprint_id)
    state.workspace_branch = str(workspace)
    _save_state(state)

    for artifact_type in (
        "delegation",
        "architecture-lock",
        "diff",
        "review-report",
        "test-report",
        "ship_approval",
        "retro",
    ):
        _run_cli(
            ["artifact", "write", team, sprint_id, artifact_type],
            env=env,
            input_text=_artifact(artifact_type, sprint_id),
        )
        if artifact_type == "review-report":
            _set_artifact(
                team,
                sprint_id,
                "design-doc.md",
                _artifact("design-doc", sprint_id),
            )
            _set_artifact(
                team,
                sprint_id,
                "office-hours-answers.md",
                _artifact("design-doc", sprint_id),
            )
        if artifact_type == "test-report":
            _set_artifact(
                team,
                sprint_id,
                "test-report.md",
                _artifact("test-report", sprint_id),
            )
            _set_artifact(
                team,
                sprint_id,
                "build-report.md",
                _artifact("diff", sprint_id),
            )

        _run_cli(
            ["sprint", "advance", sprint_id, "--team", team, "--actor", "ceo"],
            env=env,
        )

        if artifact_type == "review-report":
            _drop_artifact(team, sprint_id, "design-doc.md")
            _drop_artifact(team, sprint_id, "office-hours-answers.md")
        if artifact_type == "test-report":
            _drop_artifact(team, sprint_id, "test-report.md")
            _drop_artifact(team, sprint_id, "build-report.md")

    final_state = _load_state(team, sprint_id)
    assert final_state.status == "completed"
    assert final_state.current_phase == "reflect"
    assert len(final_state.phase_history) == 6
    assert set(final_state.artifacts) == {
        "delegation.json",
        "architecture-lock.md",
        "diff.patch",
        "review-report.md",
        "test-report.json",
        "ship-approval.md",
        "retro.md",
    }

    events = event_log.read_text(encoding="utf-8").splitlines()
    non_initial = [line for line in events if not line.startswith(">")]
    assert non_initial == [
        "think>plan",
        "plan>build",
        "build>review",
        "review>test",
        "test>ship",
        "ship>reflect",
    ]

    artifact_files = sorted(
        p.name
        for p in (
            data_dir / "teams" / team / "sprints" / sprint_id / "artifacts"
        ).glob("*")
    )
    assert artifact_files == [
        "architecture-lock.md",
        "delegation.json",
        "diff.patch",
        "retro.md",
        "review-report.md",
        "ship-approval.md",
        "test-report.json",
    ]
