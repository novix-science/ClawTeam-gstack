"""Tests for Phase 2 safety-rail subscribers + /careful regex blacklist (Plan 02-10).

Covers Task 1 (EventBus subscribers) + Task 3 (clawteam guard CLI sub-app).

Subscribers register opt-in via ``register_safety_subscribers(bus)`` called by
``SprintConductor.__init__`` (Plan 02-11). Phase 0 regression templates never
call this function, so their EventBus has zero safety subscribers
(Pitfall #8 BC hinge — see ``tests/test_template_regression_matrix.py``).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app
from clawteam.events.bus import EventBus
from clawteam.events.types import (
    BeforeFileWrite,
    BeforeToolCall,
    FreezeChange,
)
from clawteam.harness.freeze_registry import (
    CAREFUL_BLACKLIST,
    FreezeRegistry,
    _on_before_file_write,
    _on_before_tool_call,
    _on_careful,
    get_freeze_registry,
    register_safety_subscribers,
    reset_freeze_registry,
    reset_safety_subscribers,
    set_careful_veto_mode,
)


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def hermetic(tmp_path, monkeypatch):
    """Per-test data dir + careful mode reset."""
    data_root = tmp_path / "data"
    data_root.mkdir()
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data_root))
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_freeze_registry()
    reset_safety_subscribers()
    yield data_root
    reset_freeze_registry()
    reset_safety_subscribers()


@pytest.fixture
def active_registry(hermetic):
    """Force-instantiate the singleton registry so subscribers have something to consult."""
    reg = FreezeRegistry("team-x", "sprint-a")
    # poke the module-level singleton so get_freeze_registry() returns this one
    import clawteam.harness.freeze_registry as fr_mod

    fr_mod._registry = reg
    yield reg


# ── Task 1 tests (1-8) ─────────────────────────────────────────────────


def test_register_safety_subscribers_registers_three_handlers(hermetic):
    """Test 1: register_safety_subscribers(bus) attaches 1 BeforeFileWrite + 2 BeforeToolCall."""
    bus = EventBus()
    register_safety_subscribers(bus)
    assert bus.handler_count(BeforeFileWrite) == 1
    assert bus.handler_count(BeforeToolCall) == 2


def test_on_before_file_write_vetoes_when_frozen(active_registry):
    """Test 2a: _on_before_file_write sets veto + reason when FreezeRegistry matches."""
    active_registry.freeze(
        "/tmp/locked.txt", agent="engineer", reason="risky", actor="user",
    )

    event = BeforeFileWrite(
        team_name="team-x", agent_name="engineer", path="/tmp/locked.txt", size_bytes=12,
    )
    _on_before_file_write(event)
    assert event.veto is True
    assert "locked.txt" in event.veto_reason
    assert "engineer" in event.veto_reason


def test_on_before_file_write_passes_through_when_not_frozen(active_registry):
    """Test 2b: _on_before_file_write leaves event.veto False when path is not frozen."""
    event = BeforeFileWrite(
        team_name="team-x", agent_name="engineer", path="/tmp/unrelated.txt",
    )
    _on_before_file_write(event)
    assert event.veto is False
    assert event.veto_reason == ""


def test_on_before_tool_call_vetoes_when_arg_is_frozen(active_registry):
    """Test 3: _on_before_tool_call scans args for frozen path and vetoes on match."""
    active_registry.freeze(
        "/tmp/locked-dir", agent="engineer", reason="locked", actor="user",
    )
    event = BeforeToolCall(
        team_name="team-x", agent_name="engineer",
        tool_name="fs_write",
        args={"path": "/tmp/locked-dir/foo.txt", "content": "hi"},
    )
    _on_before_tool_call(event)
    assert event.veto is True
    assert "fs_write" in event.veto_reason


def test_careful_blacklist_matches_five_destructive_patterns():
    """Test 4: CAREFUL_BLACKLIST regex matches each destructive shell pattern."""
    positives = [
        "rm -rf /",
        "rm -Rf /tmp/foo",
        "git reset --hard HEAD",
        "git push --force origin main",
        "DROP TABLE users;",
        "DELETE FROM users WHERE id=1",
    ]
    for cmd in positives:
        assert CAREFUL_BLACKLIST.search(cmd), f"expected pattern to match: {cmd!r}"

    # Sanity: benign commands don't match
    benign = ["ls -la", "git commit -m 'x'", "SELECT * FROM users"]
    for cmd in benign:
        assert not CAREFUL_BLACKLIST.search(cmd), f"unexpected match on benign input: {cmd!r}"


def test_careful_default_is_warn_only(hermetic):
    """Test 5: /careful blacklist match emits FreezeChange event but does NOT set veto."""
    from clawteam.events.global_bus import get_event_bus, reset_event_bus

    reset_event_bus()
    warnings: list[FreezeChange] = []
    get_event_bus().subscribe(FreezeChange, warnings.append)

    event = BeforeToolCall(
        team_name="t", agent_name="engineer", tool_name="shell",
        args={"cmd": "rm -rf /tmp/whatever"},
    )
    # warn mode: _careful_veto_mode is False by default
    _on_careful(event)
    assert event.veto is False, "warn mode must NOT veto"
    assert any(w.action == "careful-warn" for w in warnings), \
        f"expected careful-warn FreezeChange emitted; got {warnings!r}"

    reset_event_bus()


def test_careful_veto_mode_blocks_when_enabled(hermetic):
    """Test 6: set_careful_veto_mode(True) flips blacklist matches to vetoes."""
    set_careful_veto_mode(True)
    event = BeforeToolCall(
        team_name="t", agent_name="engineer", tool_name="shell",
        args={"cmd": "DROP TABLE users;"},
    )
    _on_careful(event)
    assert event.veto is True
    assert "/careful" in event.veto_reason
    assert "DROP TABLE" in event.veto_reason


def test_register_safety_subscribers_is_idempotent(hermetic):
    """Test 7: calling register twice does not double-register."""
    bus = EventBus()
    register_safety_subscribers(bus)
    register_safety_subscribers(bus)
    assert bus.handler_count(BeforeFileWrite) == 1
    assert bus.handler_count(BeforeToolCall) == 2


def test_data_dir_paths_never_vetoed_by_subscriber(hermetic, active_registry):
    """Test 8: Pitfall #5 — paths under get_data_dir() are never vetoed.

    Even if an agent has explicitly added such a path, is_frozen() exempts it
    and the subscriber must honor that exemption (defense in depth).
    """
    from clawteam.team.models import get_data_dir

    internal_path = get_data_dir() / "teams" / "team-x" / "sprints" / "sprint-a" / "state.json"
    internal_path.parent.mkdir(parents=True, exist_ok=True)
    # Try to freeze a path under data dir — is_frozen should still say False.
    active_registry.freeze(
        str(internal_path), agent="engineer", reason="accidental", actor="user",
    )
    event = BeforeFileWrite(
        team_name="team-x", agent_name="engineer", path=str(internal_path),
    )
    _on_before_file_write(event)
    assert event.veto is False, "data-dir paths must never be vetoed"


# ── Task 3 tests (CLI sub-app) ─────────────────────────────────────────


runner = CliRunner()


@pytest.fixture
def guard_env(tmp_path, monkeypatch):
    """Isolated env for guard CLI tests."""
    data = tmp_path / ".clawteam"
    data.mkdir()
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data))
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_freeze_registry()
    reset_safety_subscribers()
    yield {
        "HOME": str(tmp_path),
        "CLAWTEAM_DATA_DIR": str(data),
    }
    reset_freeze_registry()
    reset_safety_subscribers()


def _audit_path(data_dir: str, team: str, sprint: str) -> Path:
    return Path(data_dir) / "teams" / team / "sprints" / sprint / "freeze_audit.jsonl"


def test_guard_freeze_writes_audit(guard_env):
    """Test 1 (CLI): guard freeze writes freeze.json + audit JSONL + --json envelope."""
    result = runner.invoke(
        app,
        [
            "--json", "guard", "freeze",
            "--team", "T", "--sprint", "S",
            "--reason", "unit test",
            "/test/path",
        ],
        env=guard_env,
    )
    assert result.exit_code == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["action"] == "freeze"
    assert payload["data"]["path"] == "/test/path"

    audit = _audit_path(guard_env["CLAWTEAM_DATA_DIR"], "T", "S")
    assert audit.exists(), f"freeze_audit.jsonl missing at {audit}"
    entries = [json.loads(line) for line in audit.read_text().strip().splitlines()]
    assert any(e["action"] == "freeze" for e in entries)


def test_guard_unfreeze_writes_audit(guard_env):
    """Test 2 (CLI): guard unfreeze writes audit entry with action=unfreeze."""
    # Prime: freeze first so there's something to unfreeze.
    runner.invoke(
        app,
        ["--json", "guard", "freeze", "--team", "T", "--sprint", "S", "/test/p"],
        env=guard_env,
    )
    # Reset the singleton so the CLI constructs a fresh registry that rehydrates
    # from freeze.json (simulates the agent-reload path).
    reset_freeze_registry()
    result = runner.invoke(
        app,
        ["--json", "guard", "unfreeze", "--team", "T", "--sprint", "S", "/test/p"],
        env=guard_env,
    )
    assert result.exit_code == 0, f"stdout={result.stdout!r}"
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["action"] == "unfreeze"

    audit = _audit_path(guard_env["CLAWTEAM_DATA_DIR"], "T", "S")
    entries = [json.loads(line) for line in audit.read_text().strip().splitlines()]
    assert any(e["action"] == "unfreeze" for e in entries)


def test_guard_guard_is_composite(guard_env):
    """Test 3 (CLI): guard composite freezes path AND enables careful veto mode.

    careful_enabled persistence to SprintState is deferred to Plan 02-11 when
    load_sprint_state / save_sprint_state helpers land. This test asserts on
    the in-memory module-level flag only.
    """
    from clawteam.harness import freeze_registry as fr_mod

    result = runner.invoke(
        app,
        [
            "--json", "guard", "guard",
            "--team", "T", "--sprint", "S",
            "--reason", "composite",
            "/shared/area",
        ],
        env=guard_env,
    )
    assert result.exit_code == 0, f"stdout={result.stdout!r}"
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["action"] == "guard"
    assert payload["data"]["careful_enabled"] is True
    assert fr_mod._careful_veto_mode is True


def test_guard_unguard_resets(guard_env):
    """Test 4 (CLI): unguard clears careful veto mode + audits an unfreeze."""
    from clawteam.harness import freeze_registry as fr_mod

    # Prime via guard to set up state.
    runner.invoke(
        app,
        ["--json", "guard", "guard", "--team", "T", "--sprint", "S", "/x"],
        env=guard_env,
    )
    assert fr_mod._careful_veto_mode is True
    reset_freeze_registry()

    result = runner.invoke(
        app,
        ["--json", "guard", "unguard", "--team", "T", "--sprint", "S", "/x"],
        env=guard_env,
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["data"]["action"] == "unguard"
    assert payload["data"]["careful_enabled"] is False
    assert fr_mod._careful_veto_mode is False


def test_guard_freeze_json_envelope_shape(guard_env):
    """Test 5 (CLI): --json emits the canonical envelope (ok/data/warnings/error)."""
    result = runner.invoke(
        app,
        ["--json", "guard", "freeze", "--team", "T", "--sprint", "S", "/p"],
        env=guard_env,
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"ok", "data", "warnings", "error"}
    assert payload["ok"] is True
    assert payload["warnings"] == []
    assert payload["error"] is None


def test_guard_freeze_missing_team_emits_error_envelope(guard_env, monkeypatch):
    """Test 6 (CLI): missing --team (and no CLAWTEAM_TEAM env) raises structured error.

    Typer surfaces a missing-option error before our handler runs — the process
    exits with a non-zero status. When --team is not supplied and has no envvar
    fallback, the CLI emits a usage error on stderr. We accept either the
    structured envelope (if our handler runs) or a non-zero exit (if Typer
    short-circuits). The key invariant is: NO freeze is persisted.
    """
    # Strip any stray team env that may leak in.
    monkeypatch.delenv("CLAWTEAM_TEAM", raising=False)
    result = runner.invoke(
        app,
        ["--json", "guard", "freeze", "--sprint", "S", "/p"],
        env=guard_env,
    )
    assert result.exit_code != 0, "missing --team must not succeed"
    audit = _audit_path(guard_env["CLAWTEAM_DATA_DIR"], "T", "S")
    assert not audit.exists(), "no audit entry should be written on error"
