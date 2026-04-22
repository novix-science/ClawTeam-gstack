"""Plan 07-04 Task 2 — ``clawteam attend`` CLI integration tests.

Covers INT-04 / UX-06 / QUALITY-05 user-facing surface:

* Default invocation prints top-N priority-ranked items; ``--json`` emits JSON.
* ``--summary`` renders cluster digest (build_digest roll-up).
* ``--auto-accept-reversible`` WITHOUT ``--yes`` previews only.
* ``--auto-accept-reversible --yes`` applies (writes answer.md for easy items).
* ``attend pick <qid>`` invokes ``$EDITOR`` on question.md; checks answer presence.
* Empty queue → "No pending" + exit code 0.
* Unknown question id → error + non-zero exit.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app


def _write_question(
    data_dir: Path,
    team: str,
    sprint: str,
    qid: str,
    **kwargs: str,
) -> Path:
    """Write a question.md with frontmatter. Returns the file path."""
    qdir = data_dir / "teams" / team / "sprints" / sprint / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    urgency = kwargs.get("urgency", "normal")
    reversibility = kwargs.get("reversibility", "medium")
    title = kwargs.get("title", qid)
    blocking = kwargs.get("blocking", "false")
    qpath = qdir / f"{qid}.md"
    qpath.write_text(
        f"---\n"
        f"urgency: {urgency}\n"
        f"blocking: {blocking}\n"
        f"tags: []\n"
        f"reversibility: {reversibility}\n"
        f"title: {title}\n"
        f"---\n"
        f"body\n"
    )
    return qpath


@pytest.fixture
def runner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """CliRunner + tmp_path routed via CLAWTEAM_DATA_DIR."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return CliRunner(), tmp_path


def test_attend_no_questions_exits_zero(runner):
    r, _ = runner
    result = r.invoke(app, ["attend"])
    assert result.exit_code == 0, result.stdout
    assert "No pending" in result.stdout


def test_attend_lists_top_n(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="low")
    _write_question(tmp, "t", "s", "q2", urgency="critical")
    _write_question(tmp, "t", "s", "q3", urgency="high")
    result = r.invoke(app, ["attend", "-n", "2"])
    assert result.exit_code == 0, result.stdout
    # Critical should be in the top 2 output (highest-priority wins).
    assert "q2" in result.stdout


def test_attend_json(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="high")
    result = r.invoke(app, ["--json", "attend"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert "items" in data
    assert data["items"][0]["question_id"] == "q1"
    assert "priority_score" in data["items"][0]
    assert "sprint_id" in data["items"][0]


def test_attend_summary(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="high")
    _write_question(tmp, "t", "s", "q2", urgency="normal")
    result = r.invoke(app, ["--json", "attend", "--summary"])
    assert result.exit_code == 0, result.stdout
    data = json.loads(result.stdout)
    assert "digest" in data
    assert isinstance(data["digest"], list)


def test_attend_auto_accept_preview_requires_confirm(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="normal", reversibility="easy")
    result = r.invoke(app, ["attend", "--auto-accept-reversible"])
    assert result.exit_code == 0, result.stdout
    # No --yes flag → preview only; no answer written.
    answer = tmp / "teams" / "t" / "sprints" / "s" / "answers" / "q1.md"
    assert not answer.exists()


def test_attend_auto_accept_with_yes_applies(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", reversibility="easy")
    _write_question(tmp, "t", "s", "q2", reversibility="hard")
    result = r.invoke(app, ["attend", "--auto-accept-reversible", "--yes"])
    assert result.exit_code == 0, result.stdout
    assert (tmp / "teams" / "t" / "sprints" / "s" / "answers" / "q1.md").exists()
    # Hard question NEVER auto-accepted even with --yes.
    assert not (tmp / "teams" / "t" / "sprints" / "s" / "answers" / "q2.md").exists()


def test_attend_pick_calls_editor(runner, monkeypatch: pytest.MonkeyPatch):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="high")
    captured: dict = {}

    def fake_run(cmd, check=False, **kw):  # noqa: ANN001
        captured["cmd"] = cmd

        class _R:
            returncode = 0

        return _R()

    monkeypatch.setenv("EDITOR", "my-ed")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = r.invoke(app, ["attend", "pick", "q1"])
    assert result.exit_code == 0, result.stdout
    assert "cmd" in captured, "subprocess.run was not called"
    assert captured["cmd"][0] == "my-ed"
    assert "q1.md" in str(captured["cmd"][1])


def test_attend_pick_unknown_id(runner):
    r, _ = runner
    result = r.invoke(app, ["attend", "pick", "nonexistent"])
    assert result.exit_code == 1
