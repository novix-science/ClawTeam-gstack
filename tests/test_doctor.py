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


def test_doctor_human_output_preserves_browser_extra(monkeypatch):
    """Regression: Chromium install hint must render `clawteam[browser]` literally.

    Prior to the Rich-markup-escape fix, `console.print(f"[dim]{hint}[/dim]")`
    interpreted the literal substring `[browser]` inside the hint value
    `pip install 'clawteam[browser]' && playwright install chromium` as an
    unknown Rich markup tag and silently elided it — so users saw
    `pip install 'clawteam' && playwright install chromium` (wrong extra).
    Gap closure for UAT test 2 (severity: major).
    """
    runner = CliRunner()

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    # Positive assertion: the literal extras spec must survive rendering.
    assert "clawteam[browser]" in result.output, (
        "Rich markup elided `[browser]` from the chromium install hint; "
        f"stdout was:\n{result.output}"
    )
    # Belt-and-braces: the misrendered form must NOT appear.
    assert "pip install 'clawteam' && playwright install chromium" not in result.output


def test_doctor_json_install_hint_preserves_browser_extra_unescaped(monkeypatch):
    """The JSON path must emit the underlying hint WITHOUT backslash escapes.

    Guardrail: a sloppy fix that mutates the hint data (e.g. pre-escaping
    install_hint at construction time) would corrupt the JSON API surface.
    Fix must live in the rendering layer only.
    """
    runner = CliRunner()

    monkeypatch.setattr("shutil.which", lambda _name: None)
    monkeypatch.setattr("importlib.util.find_spec", lambda _name: None)

    result = runner.invoke(app, ["--json", "doctor"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    chromium_hint = payload["chromium (Playwright)"]["install_hint"]
    # Exact string — no backslash, no escape, no mutation.
    assert chromium_hint == (
        "pip install 'clawteam[browser]' && playwright install chromium"
    ), f"JSON install_hint was mutated: {chromium_hint!r}"
