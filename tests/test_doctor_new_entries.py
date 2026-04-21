"""Tests for Phase 5 Wave 0 doctor extensions (Plan 05-01 Task 2).

Verifies that clawteam doctor detects the five new Phase 5 CLIs:
gh, lighthouse, vercel, netlify, flyctl — with per-platform install hints.
"""

from __future__ import annotations

import pytest

from clawteam.cli.commands import _DOCTOR_TOOLS, _doctor_install_hint


def _tool_names() -> set[str]:
    return {display for display, _kind, _probe in _DOCTOR_TOOLS}


def test_doctor_includes_gh():
    assert "gh" in _tool_names()
    # Verify it is probed as a CLI, not a python package.
    entry = next(row for row in _DOCTOR_TOOLS if row[0] == "gh")
    assert entry[1] == "cli"
    assert entry[2] == "gh"


def test_doctor_includes_lighthouse():
    assert "lighthouse" in _tool_names()
    entry = next(row for row in _DOCTOR_TOOLS if row[0] == "lighthouse")
    assert entry[1] == "cli"


def test_doctor_includes_vercel():
    assert "vercel" in _tool_names()
    entry = next(row for row in _DOCTOR_TOOLS if row[0] == "vercel")
    assert entry[1] == "cli"


def test_doctor_includes_netlify():
    assert "netlify" in _tool_names()
    entry = next(row for row in _DOCTOR_TOOLS if row[0] == "netlify")
    assert entry[1] == "cli"


def test_doctor_includes_flyctl():
    assert "flyctl" in _tool_names()
    entry = next(row for row in _DOCTOR_TOOLS if row[0] == "flyctl")
    assert entry[1] == "cli"


@pytest.mark.parametrize(
    "tool",
    ["gh", "lighthouse", "vercel", "netlify", "flyctl"],
)
@pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
def test_install_hints_present(tool: str, platform: str):
    hint = _doctor_install_hint(tool, platform)
    assert hint, f"{tool}/{platform} hint should be non-empty"


def test_install_hints_contain_expected_keywords():
    assert "apt" in _doctor_install_hint("gh", "linux") or "gh" in _doctor_install_hint(
        "gh", "linux"
    )
    assert "npm install -g lighthouse" in _doctor_install_hint(
        "lighthouse", "linux"
    )
    assert "npm install -g vercel" in _doctor_install_hint("vercel", "darwin")
    assert "npm install -g netlify-cli" in _doctor_install_hint(
        "netlify", "win32"
    )
    flyctl_linux = _doctor_install_hint("flyctl", "linux")
    flyctl_darwin = _doctor_install_hint("flyctl", "darwin")
    assert "flyctl" in flyctl_linux or "fly.io" in flyctl_linux
    assert "flyctl" in flyctl_darwin or "fly.io" in flyctl_darwin


def test_doctor_preserves_original_tools():
    # BC: the four Phase <5 entries remain intact.
    names = _tool_names()
    assert "chromium (Playwright)" in names
    assert "codex" in names
    assert "ngrok" in names
    assert "watchdog" in names
