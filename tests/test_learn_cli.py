"""Tests for ``clawteam learn {write,list,search,prune}`` CLI (Plan 06-10 Task 2).

9 tests:

1. ``test_learn_write_exit_zero``                — writes an entry; stdout contains id.
2. ``test_learn_write_json``                     — --json emits structured payload.
3. ``test_learn_list``                           — after a write, list prints table + JSON.
4. ``test_learn_search``                         — search returns results ordered by score.
5. ``test_learn_search_explain``                 — --explain includes recency/provenance/decay.
6. ``test_learn_prune``                          — prune tombstones entry; subsequent list empty.
7. ``test_learn_write_role_without_role_fails``  — scope=role without --role exits non-zero.
8. ``test_learn_write_invalid_impact``           — --impact xyz exits non-zero.
9. ``test_learn_write_confidence_out_of_range``  — confidence>1.0 exits non-zero.

All tests use ``typer.testing.CliRunner`` and monkeypatch CLAWTEAM_DATA_DIR
so on-disk writes are isolated to ``tmp_path``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def env(tmp_path: Path) -> dict[str, str]:
    return {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
    }


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _write_happy(runner: CliRunner, env: dict[str, str], *, json_out: bool = False) -> "object":
    from clawteam.cli.commands import app

    args = []
    if json_out:
        args.append("--json")
    args += [
        "learn", "write",
        "--team", "demo",
        "--scope", "team",
        "--title", "async patterns",
        "--tags", "pattern,async",
        "--evidence", "src/x.py:12",
        "--confidence", "0.9",
        "--learned-from", "artifact",
        "--impact", "low",
        "body text for the entry",
    ]
    return runner.invoke(app, args, env=env)


# ---------------------------------------------------------------------------
# 1. write — exit 0
# ---------------------------------------------------------------------------


def test_learn_write_exit_zero(runner, env):
    result = _write_happy(runner, env)
    assert result.exit_code == 0, result.output
    # Human output should reference the written id.
    assert "mem-demo-" in result.output


# ---------------------------------------------------------------------------
# 2. write --json — structured payload
# ---------------------------------------------------------------------------


def test_learn_write_json(runner, env):
    result = _write_happy(runner, env, json_out=True)
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "written"
    assert payload["id"].startswith("mem-demo-")
    assert payload["evidence_flagged"] is False


# ---------------------------------------------------------------------------
# 3. list — table + JSON surfaces after a write
# ---------------------------------------------------------------------------


def test_learn_list(runner, env):
    from clawteam.cli.commands import app

    write_res = _write_happy(runner, env, json_out=True)
    assert write_res.exit_code == 0

    list_res_json = runner.invoke(
        app, ["--json", "learn", "list", "--team", "demo", "--scope", "team"], env=env
    )
    assert list_res_json.exit_code == 0, list_res_json.output
    payload = json.loads(list_res_json.output)
    assert payload["status"] == "listed"
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["title"] == "async patterns"

    list_res_human = runner.invoke(
        app, ["learn", "list", "--team", "demo", "--scope", "team"], env=env
    )
    assert list_res_human.exit_code == 0, list_res_human.output
    # Human table should include the entry id somewhere.
    assert "mem-demo-" in list_res_human.output


# ---------------------------------------------------------------------------
# 4. search — returns hits
# ---------------------------------------------------------------------------


def test_learn_search(runner, env):
    from clawteam.cli.commands import app

    # Seed two entries — one matching "foo", one unrelated.
    r1 = runner.invoke(
        app,
        [
            "learn", "write",
            "--team", "demo", "--scope", "team",
            "--title", "foo bar baz", "--tags", "pattern",
            "--evidence", "src/a.py:1",
            "about foos",
        ],
        env=env,
    )
    assert r1.exit_code == 0, r1.output
    r2 = runner.invoke(
        app,
        [
            "learn", "write",
            "--team", "demo", "--scope", "team",
            "--title", "something else", "--tags", "pattern",
            "--evidence", "src/b.py:1",
            "unrelated",
        ],
        env=env,
    )
    assert r2.exit_code == 0, r2.output

    search_res = runner.invoke(
        app,
        ["--json", "learn", "search", "--team", "demo", "foo"],
        env=env,
    )
    assert search_res.exit_code == 0, search_res.output
    payload = json.loads(search_res.output)
    titles = [r["title"] for r in payload["results"]]
    assert titles == ["foo bar baz"]


# ---------------------------------------------------------------------------
# 5. search --explain — recency/provenance/decay columns
# ---------------------------------------------------------------------------


def test_learn_search_explain(runner, env):
    from clawteam.cli.commands import app

    write_res = _write_happy(runner, env, json_out=True)
    assert write_res.exit_code == 0

    res = runner.invoke(
        app,
        [
            "--json", "learn", "search",
            "--team", "demo",
            "--explain",
            "async",
        ],
        env=env,
    )
    assert res.exit_code == 0, res.output
    payload = json.loads(res.output)
    assert payload["results"], payload
    item = payload["results"][0]
    assert "recency" in item
    assert "provenance" in item
    assert "decay" in item


# ---------------------------------------------------------------------------
# 6. prune — tombstone suppresses entry
# ---------------------------------------------------------------------------


def test_learn_prune(runner, env):
    from clawteam.cli.commands import app

    write_res = _write_happy(runner, env, json_out=True)
    assert write_res.exit_code == 0
    entry_id = json.loads(write_res.output)["id"]

    prune_res = runner.invoke(
        app,
        ["--json", "learn", "prune", "--team", "demo", "--scope", "team", entry_id],
        env=env,
    )
    assert prune_res.exit_code == 0, prune_res.output
    prune_payload = json.loads(prune_res.output)
    assert prune_payload["status"] == "pruned"

    list_res = runner.invoke(
        app,
        ["--json", "learn", "list", "--team", "demo", "--scope", "team"],
        env=env,
    )
    assert list_res.exit_code == 0, list_res.output
    assert json.loads(list_res.output)["entries"] == []


# ---------------------------------------------------------------------------
# 7. scope=role without --role → non-zero exit
# ---------------------------------------------------------------------------


def test_learn_write_role_without_role_fails(runner, env):
    from clawteam.cli.commands import app

    res = runner.invoke(
        app,
        [
            "learn", "write",
            "--team", "demo",
            "--scope", "role",
            "--title", "T",
            "--tags", "pattern",
            "--evidence", "src/x.py:1",
            "body",
        ],
        env=env,
    )
    assert res.exit_code != 0, res.output


# ---------------------------------------------------------------------------
# 8. invalid --impact → non-zero
# ---------------------------------------------------------------------------


def test_learn_write_invalid_impact(runner, env):
    from clawteam.cli.commands import app

    res = runner.invoke(
        app,
        [
            "learn", "write",
            "--team", "demo", "--scope", "team",
            "--title", "T", "--tags", "pattern",
            "--evidence", "src/x.py:1",
            "--impact", "xyz",
            "body",
        ],
        env=env,
    )
    assert res.exit_code != 0, res.output


# ---------------------------------------------------------------------------
# 9. --confidence out of range → non-zero
# ---------------------------------------------------------------------------


def test_learn_write_confidence_out_of_range(runner, env):
    from clawteam.cli.commands import app

    res = runner.invoke(
        app,
        [
            "learn", "write",
            "--team", "demo", "--scope", "team",
            "--title", "T", "--tags", "pattern",
            "--evidence", "src/x.py:1",
            "--confidence", "1.5",
            "body",
        ],
        env=env,
    )
    assert res.exit_code != 0, res.output


# ---------------------------------------------------------------------------
# WR-04 regression: _invoke_learn splits ValueError (quiet) vs. unexpected
#                   programmer errors (logged + traceback preserved).
# ---------------------------------------------------------------------------


def test_invoke_learn_value_error_quiet_exit(
    runner, env, monkeypatch, caplog,
):
    """ValueError path: structured 'error' payload, exit 1, no traceback log."""
    import logging

    from clawteam.cli import commands as cmds
    from clawteam.templates.gstack.skills.learn import handler as learn_mod

    def _raise_ve(*a, **kw):
        raise ValueError("bad input from user")

    monkeypatch.setattr(learn_mod, "learn_handler", _raise_ve)
    # The CLI imports learn_handler lazily inside _invoke_learn — patch
    # the source module so the re-import picks up the replacement.

    with caplog.at_level(logging.ERROR, logger=cmds.__name__):
        res = runner.invoke(
            cmds.app,
            [
                "--json",
                "learn", "write",
                "--team", "demo", "--scope", "team",
                "--title", "T", "--tags", "pattern",
                "--evidence", "src/x.py:1",
                "body",
            ],
            env=env,
        )

    assert res.exit_code == 1, res.output
    payload = json.loads(res.output)
    assert payload == {"error": "bad input from user"}
    # ValueError path must NOT log the full traceback (it's expected).
    assert not any(
        rec.levelno >= logging.ERROR for rec in caplog.records
    ), [r.message for r in caplog.records]


def test_invoke_learn_unexpected_error_logs_traceback(
    runner, env, monkeypatch, caplog,
):
    """Non-ValueError path: logs traceback via logger.exception + re-raises."""
    import logging

    from clawteam.cli import commands as cmds
    from clawteam.templates.gstack.skills.learn import handler as learn_mod

    def _raise_runtime(*a, **kw):
        raise RuntimeError("boom: programmer error")

    monkeypatch.setattr(learn_mod, "learn_handler", _raise_runtime)

    with caplog.at_level(logging.ERROR, logger=cmds.__name__):
        res = runner.invoke(
            cmds.app,
            [
                "--json",
                "learn", "write",
                "--team", "demo", "--scope", "team",
                "--title", "T", "--tags", "pattern",
                "--evidence", "src/x.py:1",
                "body",
            ],
            env=env,
        )

    # Re-raise means the CLI exits non-zero (Typer converts the uncaught
    # exception to exit_code=1 and stashes .exception).
    assert res.exit_code != 0, res.output
    # Traceback logged at ERROR level via logger.exception.
    assert any(
        "unexpected error" in rec.message.lower()
        and rec.exc_info is not None
        for rec in caplog.records
    ), [
        (r.message, r.exc_info) for r in caplog.records
    ]
