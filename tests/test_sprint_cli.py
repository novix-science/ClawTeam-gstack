"""Tests for the `clawteam sprint` CLI sub-app (Plan 02-12).

Covers UX-02 (start), UX-03 (status), UX-04 (list), UX-05 (show), UX-09
(uniform JSON envelope), and the D-24/D-25/D-26 error-code contract.

All tests use a hermetic filesystem (``CLAWTEAM_DATA_DIR`` → tmp_path) and
scrub ``CLAWTEAM_TEAM`` + ``OH_TEAM`` so the host env cannot leak into a
"team is required" assertion.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture
def clean_env(tmp_path, monkeypatch):
    """Hermetic environment — no CLAWTEAM_TEAM leaking from host."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("CLAWTEAM_TEAM", raising=False)
    monkeypatch.delenv("OH_TEAM", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_TEAM", raising=False)
    # Reset freeze-registry + safety subscribers so each test starts clean.
    from clawteam.harness.freeze_registry import (
        reset_freeze_registry,
        reset_safety_subscribers,
    )

    reset_freeze_registry()
    reset_safety_subscribers()
    yield tmp_path
    reset_freeze_registry()
    reset_safety_subscribers()


def _load_app():
    """Import the Typer app fresh so the sprint sub-app is registered."""
    from clawteam.cli.commands import app

    return app


def _start_via_conductor(team: str, goal: str = "g") -> str:
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name=team)
    return c.start_sprint(goal=goal).sprint_id


def _last_json(output: str) -> dict:
    """Parse the last non-empty line of ``output`` as JSON.

    Typer's CliRunner may prepend help/diagnostic text when a command errors
    out via ``typer.Exit``; our error envelope always prints as the last
    line before exit.
    """
    for line in reversed(output.splitlines()):
        if line.strip():
            return json.loads(line) if line.strip().startswith("{") else json.loads(
                output
            )
    return json.loads(output)


def _parse_envelope(output: str) -> dict:
    """Parse a complete JSON envelope printed as a pretty-printed block.

    The envelope is printed via ``json.dumps(..., indent=2)`` which spans
    multiple lines; attempt whole-output parse first, then fall back to the
    last line.
    """
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        # Find the last complete top-level JSON object in the output.
        stripped = output.strip()
        # Walk backward to find the last '{' at column 0 that opens a valid obj.
        last_open = stripped.rfind("\n{")
        if last_open != -1:
            candidate = stripped[last_open + 1 :]
            return json.loads(candidate)
        return json.loads(stripped)


# ───────────────────────────── start ─────────────────────────────


def test_sprint_start_creates_sprint_and_returns_json_envelope(clean_env):
    app = _load_app()
    result = runner.invoke(
        app, ["--json", "sprint", "start", "--team", "t", "--goal", "ship dark mode"]
    )
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["ok"] is True
    assert payload["error"] is None
    assert set(payload["data"].keys()) >= {
        "id",
        "goal",
        "current_phase",
        "team",
        "auto_advance",
        "status",
    }
    assert payload["data"]["team"] == "t"
    assert payload["data"]["goal"] == "ship dark mode"


def test_sprint_start_without_team_flag_uses_env(clean_env, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_TEAM", "t")
    app = _load_app()
    result = runner.invoke(app, ["--json", "sprint", "start", "--goal", "g"])
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["ok"] is True
    assert payload["data"]["team"] == "t"


def test_sprint_start_without_any_team_raises_missing_team(clean_env):
    app = _load_app()
    result = runner.invoke(app, ["--json", "sprint", "start", "--goal", "g"])
    assert result.exit_code != 0
    payload = _parse_envelope(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "MISSING_TEAM"


# ───────────────────────────── status ─────────────────────────────


def test_sprint_status_with_full_id(clean_env):
    sid = _start_via_conductor("t")
    app = _load_app()
    result = runner.invoke(
        app, ["--json", "sprint", "status", sid, "--team", "t"]
    )
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["ok"] is True
    assert payload["data"]["sprint_id"] == sid
    assert payload["data"]["pending_questions_count"] == 0
    assert payload["data"]["most_recent_artifact"] == ""


def test_sprint_status_with_prefix(clean_env):
    sid = _start_via_conductor("t")
    app = _load_app()
    result = runner.invoke(
        app, ["--json", "sprint", "status", sid[:4], "--team", "t"]
    )
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["data"]["sprint_id"] == sid


def test_sprint_status_ambiguous_prefix_reports_candidates(clean_env, monkeypatch):
    """Force two sprints with the same first-4-char prefix by stubbing uuid4.

    Conductor calls ``uuid.uuid4().hex[:8]``, so our stub exposes ``hex`` as
    a string attribute whose first 8 chars form the forged sprint id.
    """
    import uuid as uuid_mod

    forged_ids = ["abcd1111ffffffff", "abcd2222ffffffff"]
    call_index = {"i": 0}
    real_uuid4 = uuid_mod.uuid4

    def fake_uuid4():
        i = call_index["i"]
        if i < len(forged_ids):
            call_index["i"] += 1
            return type("U", (), {"hex": forged_ids[i]})()
        return real_uuid4()

    monkeypatch.setattr(uuid_mod, "uuid4", fake_uuid4)
    sid1 = _start_via_conductor("t")
    sid2 = _start_via_conductor("t")
    assert sid1.startswith("abcd") and sid2.startswith("abcd")
    assert sid1 != sid2

    app = _load_app()
    result = runner.invoke(
        app, ["--json", "sprint", "status", "abcd", "--team", "t"]
    )
    assert result.exit_code != 0
    payload = _parse_envelope(result.output)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "AMBIGUOUS_SPRINT"
    msg = payload["error"]["message"]
    assert sid1 in msg and sid2 in msg


def test_sprint_status_not_found(clean_env):
    app = _load_app()
    result = runner.invoke(
        app, ["--json", "sprint", "status", "nosuchid", "--team", "t"]
    )
    assert result.exit_code != 0
    payload = _parse_envelope(result.output)
    assert payload["error"]["code"] == "SPRINT_NOT_FOUND"


# ───────────────────────────── show ─────────────────────────────


def test_sprint_show_full_state(clean_env):
    sid = _start_via_conductor("t", goal="ship it")
    app = _load_app()
    result = runner.invoke(app, ["--json", "sprint", "show", sid, "--team", "t"])
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["ok"] is True
    expected = {
        "sprint_id",
        "goal",
        "current_phase",
        "status",
        "participants",
        "phase_history",
        "artifacts_list",
        "pending_question_ids",
        "auto_advance",
        "team",
        "created_at",
        "workspace_branch",
    }
    assert expected.issubset(set(payload["data"].keys()))


# ───────────────────────────── list ─────────────────────────────


def test_sprint_list_requires_team(clean_env):
    app = _load_app()
    result = runner.invoke(app, ["--json", "sprint", "list"])
    assert result.exit_code != 0
    payload = _parse_envelope(result.output)
    assert payload["error"]["code"] == "MISSING_TEAM"


def test_sprint_list_returns_all_sprints_for_team(clean_env):
    sid1 = _start_via_conductor("t", goal="g1")
    sid2 = _start_via_conductor("t", goal="g2")
    sid3 = _start_via_conductor("t", goal="g3")
    app = _load_app()
    result = runner.invoke(app, ["--json", "sprint", "list", "--team", "t"])
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["ok"] is True
    returned_ids = {s["sprint_id"] for s in payload["data"]["sprints"]}
    assert returned_ids == {sid1, sid2, sid3}


# ───────────────────────────── pause / resume ─────────────────────


def test_sprint_pause_flips_status(clean_env):
    sid = _start_via_conductor("t")
    app = _load_app()
    result = runner.invoke(
        app, ["--json", "sprint", "pause", sid, "--team", "t"]
    )
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["data"]["status"] == "paused"
    # Verify state.json on disk.
    state_path = clean_env / "teams" / "t" / "sprints" / sid / "state.json"
    raw = json.loads(state_path.read_text())
    assert raw["status"] == "paused"


def test_sprint_resume_flips_status_back_to_running(clean_env):
    sid = _start_via_conductor("t")
    app = _load_app()
    runner.invoke(app, ["--json", "sprint", "pause", sid, "--team", "t"])
    result = runner.invoke(
        app, ["--json", "sprint", "resume", sid, "--team", "t"]
    )
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["data"]["status"] == "running"


# ───────────────────────────── cap + auto-advance flags ───────────


def test_sprint_start_respects_artifact_cap_flag(clean_env):
    app = _load_app()
    result = runner.invoke(
        app,
        [
            "--json",
            "sprint",
            "start",
            "--team",
            "t",
            "--goal",
            "g",
            "--artifact-cap",
            "100",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    sid = payload["data"]["id"]
    state_path = clean_env / "teams" / "t" / "sprints" / sid / "state.json"
    raw = json.loads(state_path.read_text())
    assert raw["artifact_cap_bytes"] == 100 * 1024


def test_sprint_start_respects_auto_advance_flag(clean_env):
    app = _load_app()
    result = runner.invoke(
        app,
        [
            "--json",
            "sprint",
            "start",
            "--team",
            "t",
            "--goal",
            "g",
            "--no-auto-advance",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = _parse_envelope(result.output)
    assert payload["data"]["auto_advance"] is False


# ───────────────────────────── envelope uniformity ────────────────


def test_json_envelope_shape_uniform_across_commands(clean_env):
    sid = _start_via_conductor("t")
    app = _load_app()
    commands = [
        ["--json", "sprint", "status", sid, "--team", "t"],
        ["--json", "sprint", "show", sid, "--team", "t"],
        ["--json", "sprint", "list", "--team", "t"],
        ["--json", "sprint", "pause", sid, "--team", "t"],
        ["--json", "sprint", "resume", sid, "--team", "t"],
    ]
    for cmd in commands:
        result = runner.invoke(app, cmd)
        assert result.exit_code == 0, f"cmd={cmd} output={result.output}"
        payload = _parse_envelope(result.output)
        assert set(payload.keys()) == {"ok", "data", "warnings", "error"}, (
            f"cmd={cmd} keys={set(payload.keys())}"
        )
        assert payload["ok"] is True
        assert payload["error"] is None
