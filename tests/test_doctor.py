from __future__ import annotations

import json
from types import SimpleNamespace

from typer.testing import CliRunner

from clawteam.cli.commands import app


def test_doctor_reports_missing_tools_with_install_hints(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "missing" in result.output
    assert "chromium (Playwright)" in result.output
    assert "codex" in result.output
    assert "ngrok" in result.output
    assert "watchdog" in result.output


def test_doctor_reports_found_tools(monkeypatch):
    runner = CliRunner()

    def fake_which(name: str):
        return f"/usr/local/bin/{name}"

    monkeypatch.setattr("shutil.which", fake_which)
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: SimpleNamespace())

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "missing" not in result.output
    assert "OK" in result.output
    assert "/usr/local/bin/codex" in result.output
    assert "/usr/local/bin/ngrok" in result.output


def test_doctor_json_output_shape(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

    result = runner.invoke(app, ["--json", "doctor"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "os" in payload
    assert "platform" in payload["os"]
    for name in ("chromium (Playwright)", "codex", "ngrok", "watchdog"):
        assert name in payload
        assert set(payload[name]).issuperset({"found", "path", "install_hint"})


def test_doctor_install_hints_follow_platform_dispatch(monkeypatch):
    runner = CliRunner()

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

    monkeypatch.setattr("sys.platform", "darwin")
    darwin = runner.invoke(app, ["--json", "doctor"])
    assert darwin.exit_code == 0
    darwin_payload = json.loads(darwin.output)
    assert "brew install codex" in darwin_payload["codex"]["install_hint"]
    assert "brew install ngrok" in darwin_payload["ngrok"]["install_hint"]

    monkeypatch.setattr("sys.platform", "win32")
    win32 = runner.invoke(app, ["--json", "doctor"])
    assert win32.exit_code == 0
    win32_payload = json.loads(win32.output)
    assert "winget install OpenAI.Codex" in win32_payload["codex"]["install_hint"]
    assert "winget install Ngrok.Ngrok" in win32_payload["ngrok"]["install_hint"]

    monkeypatch.setattr("sys.platform", "linux")
    linux = runner.invoke(app, ["--json", "doctor"])
    assert linux.exit_code == 0
    linux_payload = json.loads(linux.output)
    assert "npm install -g @openai/codex" in linux_payload["codex"]["install_hint"]
    assert "apt install ngrok" in linux_payload["ngrok"]["install_hint"]
