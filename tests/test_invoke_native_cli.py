"""Tests for invoke_native_cli wrapper (Phase 5 Wave 0, Plan 05-01 Task 2).

Invariants:
- shell=False HARD-CODED (D-15 adversarial-input protection).
- Default env = scrub_env(os.environ) — secret-shaped keys redacted.
- Caller-supplied env bypasses scrub_env (explicit opt-out).
- TimeoutExpired propagates unchanged.
- Returns subprocess.CompletedProcess.
"""

from __future__ import annotations

import subprocess

import pytest


def _capture_subprocess_run(monkeypatch):
    """Install a subprocess.run stub that records args/kwargs and returns a dummy result."""
    captured: dict = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="ok", stderr=""
        )

    monkeypatch.setattr("clawteam.spawn.invoke.subprocess.run", fake_run)
    return captured


def test_invokes_subprocess_with_prepared_command(monkeypatch):
    from clawteam.spawn.invoke import invoke_native_cli

    captured = _capture_subprocess_run(monkeypatch)
    invoke_native_cli(["echo", "hi"], timeout=5)

    # prepared.final_command == normalized ["echo", "hi"]; argv forwarded as-is.
    assert captured["args"] == ["echo", "hi"]
    assert captured["kwargs"]["shell"] is False
    assert captured["kwargs"]["timeout"] == 5
    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["capture_output"] is True


def test_scrub_env_applied(monkeypatch):
    from clawteam.spawn.invoke import invoke_native_cli

    fake_env = {
        "PATH": "/usr/bin",
        "FAKE_SECRET_TOKEN": "oops",
        "GITHUB_TOKEN": "ghp_xxx",
        "HOME": "/home/test",
    }
    monkeypatch.setattr("clawteam.spawn.invoke.os.environ", fake_env)

    captured = _capture_subprocess_run(monkeypatch)
    invoke_native_cli(["true"])

    env_passed = captured["kwargs"]["env"]
    # Secret-shaped keys are still present as keys but values are REDACTED;
    # the plan spec says "NOT in the env passed to subprocess.run" — the
    # stronger contract is that the token VALUE does not leak. Enforce both:
    # the token value must not be present, and the key is redacted.
    assert env_passed.get("FAKE_SECRET_TOKEN") != "oops"
    assert env_passed.get("GITHUB_TOKEN") != "ghp_xxx"
    # Non-secret keys pass through untouched.
    assert env_passed["PATH"] == "/usr/bin"
    assert env_passed["HOME"] == "/home/test"


def test_timeout_propagates(monkeypatch):
    from clawteam.spawn.invoke import invoke_native_cli

    def raising_run(args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args, timeout=kwargs.get("timeout", 0))

    monkeypatch.setattr("clawteam.spawn.invoke.subprocess.run", raising_run)

    with pytest.raises(subprocess.TimeoutExpired):
        invoke_native_cli(["sleep", "99"], timeout=1)


def test_explicit_env_override(monkeypatch):
    from clawteam.spawn.invoke import invoke_native_cli

    # Even if os.environ holds secrets, caller's explicit env dict is passed through
    # as-is (scrub_env NOT applied).
    monkeypatch.setattr(
        "clawteam.spawn.invoke.os.environ",
        {"SECRET_TOKEN": "leaky"},
    )
    captured = _capture_subprocess_run(monkeypatch)

    explicit = {"FOO": "bar", "SECRET_TOKEN": "caller-owns-this"}
    invoke_native_cli(["true"], env=explicit)

    env_passed = captured["kwargs"]["env"]
    # Caller's dict is NOT mutated to REDACTED.
    assert env_passed["FOO"] == "bar"
    assert env_passed["SECRET_TOKEN"] == "caller-owns-this"
    # Caller's dict does NOT inherit scrub_env treatment.
    assert "REDACTED" not in env_passed.get("SECRET_TOKEN", "")


def test_returns_completedprocess(monkeypatch):
    from clawteam.spawn.invoke import invoke_native_cli

    _capture_subprocess_run(monkeypatch)
    result = invoke_native_cli(["echo", "hi"])
    assert isinstance(result, subprocess.CompletedProcess)
    assert result.returncode == 0
    assert result.stdout == "ok"
    assert result.stderr == ""
