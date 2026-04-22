"""Tests for /browse skill (Phase 6 Plan 06-05, SKILL-10).

Task 1 covers handler-level behaviors:
- Happy path: artifact write + screenshot file + return dict shape.
- Missing Playwright: SkillUnavailable raised by navigate_and_screenshot
  (handler delegates detection to adapter).
- URL scheme validation: file:// / javascript: / data: rejected BEFORE
  any browser launch.
- action_script dispatch path when ``args["actions"]`` is non-empty.
- Screenshot path recorded RELATIVE to sprint_dir (not absolute).

Task 2 covers plugin registration + dispatcher wiring:
- 8th SkillRegistration with name="/browse" + correct roles.
- Non-permitted role raises SkillNotPermitted.
- Unavailable (playwright_available=False) raises SkillUnavailable
  with install_hint containing "clawteam[browser]".
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_ctx(tmp_path, sprint_id: str = "s1"):
    """Minimal context — handler only consults sprint_dir + sprint_id."""
    return SimpleNamespace(sprint_dir=tmp_path, sprint_id=sprint_id)


def _parse_frontmatter(text: str) -> dict:
    """Tiny frontmatter parser matching the handler's hand-rolled emitter."""
    assert text.startswith("---\n"), f"no frontmatter: {text!r}"
    end = text.index("\n---\n", 4)
    fm_block = text[4:end]
    out: dict = {}
    for line in fm_block.splitlines():
        if not line.strip():
            continue
        key, _, val = line.partition(": ")
        val = val.strip()
        if val.startswith("'") and val.endswith("'"):
            val = val[1:-1]
        elif val == "true":
            val = True
        elif val == "false":
            val = False
        elif val.isdigit():
            val = int(val)
        out[key] = val
    return out


# ---------------------------------------------------------------------------
# Task 1 — handler behaviors
# ---------------------------------------------------------------------------


def test_happy_path(tmp_path, monkeypatch):
    """navigate_and_screenshot mock → artifact + screenshot + return dict."""
    import clawteam.templates.gstack.skills.browse.handler as h

    fake_hash = "a" * 64  # 64-hex
    fake_status = 200
    fake_png = b"PNGBYTES"

    monkeypatch.setattr(
        h,
        "navigate_and_screenshot",
        lambda url: (fake_hash, fake_status, fake_png),
    )

    ctx = _fake_ctx(tmp_path)
    result = h.browse_handler(
        ctx, role="engineer", args={"url": "https://example.com"}
    )

    # Return dict shape.
    assert "artifact_path" in result
    assert result["http_status"] == 200
    assert result["dom_hash"] == fake_hash
    assert result["action_count"] == 0
    assert result["screenshot_path"].endswith(".png")

    # Artifact file exists with correct frontmatter.
    artifact_path = Path(result["artifact_path"])
    assert artifact_path.exists()
    assert artifact_path.name == "browse-result.md"
    fm = _parse_frontmatter(artifact_path.read_text(encoding="utf-8"))
    assert fm["artifact_type"] == "browse-result"
    assert fm["http_status"] == 200
    assert fm["dom_hash"] == fake_hash
    assert fm["persona"] == "engineer"
    assert fm["done"] is True

    # Screenshot file co-located.
    screenshot_rel = result["screenshot_path"]
    assert screenshot_rel.startswith("browse-screenshot-")
    assert screenshot_rel.endswith(".png")
    screenshot_path = tmp_path / screenshot_rel
    assert screenshot_path.exists()
    assert screenshot_path.read_bytes() == fake_png


def test_missing_playwright(tmp_path, monkeypatch):
    """When navigate_and_screenshot raises SkillUnavailable, handler re-raises."""
    import clawteam.templates.gstack.skills.browse.handler as h
    from clawteam.plugins.skill_errors import SkillUnavailable

    def _raise(url):
        raise SkillUnavailable(
            skill="/browse",
            binary="playwright",
            install_hint="pip install 'clawteam[browser]' && playwright install chromium",
        )

    monkeypatch.setattr(h, "navigate_and_screenshot", _raise)

    ctx = _fake_ctx(tmp_path)
    with pytest.raises(SkillUnavailable) as excinfo:
        h.browse_handler(
            ctx, role="engineer", args={"url": "https://example.com"}
        )
    assert "playwright install chromium" in excinfo.value.install_hint


def _assert_scheme_rejected(tmp_path, monkeypatch, url: str) -> None:
    """Shared helper: validate URL is rejected BEFORE any browser launch."""
    import clawteam.templates.gstack.skills.browse.handler as h

    called: dict[str, bool] = {"navigate": False, "action": False}

    def _should_not_be_called(*args, **kwargs):
        called["navigate"] = True
        raise AssertionError("navigate_and_screenshot called despite invalid URL")

    def _action_should_not_be_called(*args, **kwargs):
        called["action"] = True
        raise AssertionError("action_script called despite invalid URL")

    monkeypatch.setattr(h, "navigate_and_screenshot", _should_not_be_called)
    monkeypatch.setattr(h, "action_script", _action_should_not_be_called)

    ctx = _fake_ctx(tmp_path)
    with pytest.raises(ValueError):
        h.browse_handler(ctx, role="engineer", args={"url": url})
    assert not called["navigate"]
    assert not called["action"]


def test_url_scheme_rejected_file(tmp_path, monkeypatch):
    _assert_scheme_rejected(tmp_path, monkeypatch, "file:///etc/passwd")


def test_url_scheme_rejected_javascript(tmp_path, monkeypatch):
    _assert_scheme_rejected(tmp_path, monkeypatch, "javascript:alert(1)")


def test_url_scheme_rejected_data(tmp_path, monkeypatch):
    _assert_scheme_rejected(
        tmp_path, monkeypatch, "data:text/html,<script>alert(1)</script>"
    )


def test_action_script_dispatch(tmp_path, monkeypatch):
    """Non-empty actions list → action_script path (not navigate_and_screenshot)."""
    import clawteam.templates.gstack.skills.browse.handler as h

    navigate_called = {"yes": False}

    def _navigate_should_not_be_called(url):
        navigate_called["yes"] = True
        raise AssertionError(
            "navigate_and_screenshot called even though actions provided"
        )

    fake_result = {
        "url": "https://x",
        "http_status": 200,
        "screenshots": [b"ACTIONPNG"],
        "action_count": 1,
    }

    monkeypatch.setattr(
        h, "navigate_and_screenshot", _navigate_should_not_be_called
    )
    monkeypatch.setattr(h, "action_script", lambda url, actions: fake_result)

    ctx = _fake_ctx(tmp_path)
    result = h.browse_handler(
        ctx,
        role="engineer",
        args={
            "url": "https://example.com",
            "actions": [{"type": "click", "selector": "#ok"}],
        },
    )
    assert not navigate_called["yes"]
    assert result["action_count"] == 1
    assert result["http_status"] == 200

    artifact = Path(result["artifact_path"])
    fm = _parse_frontmatter(artifact.read_text(encoding="utf-8"))
    assert fm["action_count"] == 1


def test_screenshot_path_relative_to_sprint_dir(tmp_path, monkeypatch):
    """screenshot_path in frontmatter is RELATIVE to sprint_dir (not absolute)."""
    import clawteam.templates.gstack.skills.browse.handler as h

    monkeypatch.setattr(
        h,
        "navigate_and_screenshot",
        lambda url: ("b" * 64, 200, b"SHOT"),
    )

    ctx = _fake_ctx(tmp_path)
    result = h.browse_handler(
        ctx, role="engineer", args={"url": "https://example.com"}
    )
    screenshot_rel = result["screenshot_path"]
    # Must be relative — no leading slash, no absolute path parts.
    assert not Path(screenshot_rel).is_absolute()
    assert "/" not in screenshot_rel  # co-located in sprint_dir, no subdir
    # Resolves to an existing file when joined to sprint_dir.
    assert (tmp_path / screenshot_rel).exists()

    # Frontmatter screenshot_path matches the same relative form.
    artifact = Path(result["artifact_path"])
    fm = _parse_frontmatter(artifact.read_text(encoding="utf-8"))
    assert fm["screenshot_path"] == screenshot_rel


# ---------------------------------------------------------------------------
# Task 2 — plugin registration + dispatcher wiring
# ---------------------------------------------------------------------------


def test_registered_in_plugin():
    """GstackSprintPlugin.contribute_skills contains exactly one /browse entry."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.browser import playwright_available as expected_probe

    regs = GstackSprintPlugin().contribute_skills()
    browse_regs = [r for r in regs if r.name == "/browse"]
    assert len(browse_regs) == 1

    browse = browse_regs[0]
    assert browse.roles == frozenset({"engineer", "qa", "dx-lead"})
    assert browse.tool_available is expected_probe
    assert "clawteam[browser]" in browse.install_hint


def test_designer_not_permitted(tmp_path, monkeypatch):
    """Dispatching /browse as designer raises SkillNotPermitted."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillNotPermitted

    plugin = GstackSprintPlugin()
    regs = {r.name: r for r in plugin.contribute_skills()}
    dispatcher = SkillDispatcher(regs)

    ctx = _fake_ctx(tmp_path)
    with pytest.raises(SkillNotPermitted):
        dispatcher.dispatch(
            ctx,
            skill_name="/browse",
            role="designer",
            args={"url": "https://example.com"},
        )


def test_unavailable_raises_via_dispatcher(tmp_path, monkeypatch):
    """playwright_available=False → SkillUnavailable with install_hint."""
    import clawteam.browser as browser_pkg
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillUnavailable

    # Force tool_available probe (which is browser_pkg.playwright_available)
    # to return False. The plugin captured the function object by reference at
    # module load, so we patch the function the plugin wired in.
    import clawteam.plugins.gstack_sprint_plugin as plugin_mod

    monkeypatch.setattr(
        plugin_mod, "_playwright_available", lambda: False, raising=False
    )
    # Rebuild plugin — fresh contribute_skills() re-reads the patched symbol.
    plugin = GstackSprintPlugin()
    regs = plugin.contribute_skills()
    # The SkillRegistration was built at contribute_skills() call time and
    # stored a reference to _playwright_available. Our monkeypatch above
    # rebinds the name in the plugin module so the fresh registrations built
    # here see the False-returning function.
    browse = next(r for r in regs if r.name == "/browse")
    assert browse.tool_available is not None
    assert browse.tool_available() is False

    dispatcher = SkillDispatcher({r.name: r for r in regs})
    ctx = _fake_ctx(tmp_path)
    with pytest.raises(SkillUnavailable) as excinfo:
        dispatcher.dispatch(
            ctx,
            skill_name="/browse",
            role="engineer",
            args={"url": "https://example.com"},
        )
    assert "clawteam[browser]" in excinfo.value.install_hint
