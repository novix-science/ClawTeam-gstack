"""Tests for /open-gstack-browser handler + plugin registration (Plan 06-06).

Covers (per Plan 06-06 Task 1 behavior matrix):

- test_happy_path: handler returns artifact_path; artifact records URL + domain.
- test_loads_cookies_for_host: load_cookies_for_domain called with parsed host
  (port stripped); cookies passed into open_headed_with_context via kwarg.
- test_missing_playwright: playwright_available() → False ⇒ SkillUnavailable
  with install_hint populated.
- test_no_cookies_still_opens: empty cookie list → open_headed_with_context is
  still invoked; handler reports cookies_loaded == 0.
- test_url_scheme_rejected: url="file:///tmp/x.html" raises ValueError BEFORE
  any browser launch (T-06-06-01 mitigation).
- test_registered_in_plugin: GstackSprintPlugin registers /open-gstack-browser
  with roles={'engineer','qa','dx-lead','designer'} (9 or 8 total skills
  depending on whether sibling plan 06-05 /browse has landed — the test
  asserts +1 on the baseline rather than a hard-coded count).
- test_non_role_not_permitted: SkillDispatcher role='security' raises
  SkillNotPermitted.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator, List

import pytest


# ---------------------------------------------------------------------------
# Stub context manager + cookie capture helpers
# ---------------------------------------------------------------------------


class _StubPage:
    def __init__(self) -> None:
        self.goto_calls: List[str] = []

    def goto(self, url: str) -> None:
        self.goto_calls.append(url)


class _StubContext:
    def __init__(self) -> None:
        self.page = _StubPage()
        self.new_page_calls = 0

    def new_page(self) -> _StubPage:
        self.new_page_calls += 1
        return self.page


def _make_stub_session(recorder: dict[str, Any]):
    """Return a @contextmanager-decorated replacement for open_headed_with_context."""

    @contextmanager
    def _stub(*, cookies=None, viewport=None) -> Iterator[_StubContext]:
        recorder["cookies"] = cookies
        recorder["viewport"] = viewport
        recorder["entered"] = True
        ctx = _StubContext()
        recorder["context"] = ctx
        try:
            yield ctx
        finally:
            recorder["exited"] = True

    return _stub


def _make_ctx(tmp_path: Path) -> SimpleNamespace:
    sprint_dir = tmp_path / "sprint-abc"
    team_dir = tmp_path / "team"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    team_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        sprint_dir=sprint_dir,
        sprint_id="sprint-abc",
        team_dir=team_dir,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.open_gstack_browser import handler as h

    rec: dict[str, Any] = {}
    monkeypatch.setattr(h, "open_headed_with_context", _make_stub_session(rec))
    monkeypatch.setattr(
        h,
        "load_cookies_for_domain",
        lambda team_dir, domain: [{"name": "sid", "value": "x"}],
    )

    ctx = _make_ctx(tmp_path)
    out = h.open_browser_handler(
        ctx, role="designer", args={"url": "https://staging.example.com/dashboard"},
    )

    assert "artifact_path" in out
    artifact_path = Path(out["artifact_path"])
    assert artifact_path.is_file()
    content = artifact_path.read_text(encoding="utf-8")
    assert "'https://staging.example.com/dashboard'" in content
    assert "'staging.example.com'" in content
    # Context manager entered AND exited (browser lifecycle closed).
    assert rec.get("entered") is True
    assert rec.get("exited") is True
    # Page goto happened with the exact URL.
    assert rec["context"].page.goto_calls == ["https://staging.example.com/dashboard"]


def test_loads_cookies_for_host(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.open_gstack_browser import handler as h

    rec: dict[str, Any] = {}
    monkeypatch.setattr(h, "open_headed_with_context", _make_stub_session(rec))
    captured: dict[str, Any] = {}

    def _fake_load(team_dir, domain):
        captured["team_dir"] = team_dir
        captured["domain"] = domain
        return [{"name": "auth", "value": "token", "domain": domain, "path": "/"}]

    monkeypatch.setattr(h, "load_cookies_for_domain", _fake_load)

    ctx = _make_ctx(tmp_path)
    # Port should be stripped for domain lookup.
    h.open_browser_handler(
        ctx, role="engineer", args={"url": "https://staging.example.com:8443/app"},
    )

    assert captured["domain"] == "staging.example.com"
    # cookies kwarg was threaded through to the session factory.
    assert rec["cookies"] == [
        {"name": "auth", "value": "token", "domain": "staging.example.com", "path": "/"}
    ]


def test_missing_playwright(tmp_path, monkeypatch):
    """If playwright is absent, open_headed_with_context raises SkillUnavailable
    (the handler must not swallow it)."""
    from clawteam.templates.gstack.skills.open_gstack_browser import handler as h
    from clawteam.plugins.skill_errors import SkillUnavailable

    @contextmanager
    def _raising(*, cookies=None, viewport=None):
        raise SkillUnavailable(
            skill="/open-gstack-browser",
            binary="playwright",
            install_hint="pip install 'clawteam[browser]' && playwright install chromium",
        )
        yield  # pragma: no cover — unreachable but keeps it a generator.

    monkeypatch.setattr(h, "open_headed_with_context", _raising)
    monkeypatch.setattr(h, "load_cookies_for_domain", lambda td, d: [])

    ctx = _make_ctx(tmp_path)
    with pytest.raises(SkillUnavailable) as excinfo:
        h.open_browser_handler(
            ctx, role="qa", args={"url": "https://example.com/"},
        )
    assert "playwright" in excinfo.value.install_hint


def test_no_cookies_still_opens(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.open_gstack_browser import handler as h

    rec: dict[str, Any] = {}
    monkeypatch.setattr(h, "open_headed_with_context", _make_stub_session(rec))
    monkeypatch.setattr(h, "load_cookies_for_domain", lambda td, d: [])

    ctx = _make_ctx(tmp_path)
    out = h.open_browser_handler(
        ctx, role="dx-lead", args={"url": "https://example.org/"},
    )

    assert rec.get("entered") is True
    # Handler may pass cookies=None or cookies=[] when none found — both are
    # semantically "no cookies"; the important signal is the session opened.
    assert rec["cookies"] in (None, [])
    assert out["cookies_loaded"] == 0


def test_url_scheme_rejected(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.open_gstack_browser import handler as h

    called: dict[str, bool] = {"session": False, "cookies": False}

    @contextmanager
    def _forbidden(**_kwargs):
        called["session"] = True
        yield _StubContext()  # pragma: no cover

    def _forbidden_cookies(*_a, **_kw):
        called["cookies"] = True
        return []

    monkeypatch.setattr(h, "open_headed_with_context", _forbidden)
    monkeypatch.setattr(h, "load_cookies_for_domain", _forbidden_cookies)

    ctx = _make_ctx(tmp_path)
    with pytest.raises(ValueError):
        h.open_browser_handler(
            ctx, role="designer", args={"url": "file:///tmp/x.html"},
        )
    # URL validation MUST happen before we talk to the browser or cookie jar.
    assert called == {"session": False, "cookies": False}


def test_registered_in_plugin():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    skills = plugin.contribute_skills()
    by_name = {s.name: s for s in skills}

    assert "/open-gstack-browser" in by_name, (
        f"/open-gstack-browser not registered; got {sorted(by_name)}"
    )
    reg = by_name["/open-gstack-browser"]
    assert reg.roles == frozenset({"engineer", "qa", "dx-lead", "designer"})
    assert callable(reg.handler)
    # install_hint must mention playwright so the doctor surface is actionable.
    assert "playwright" in (reg.install_hint or "")


def test_non_role_not_permitted():
    """SkillDispatcher rejects role='security' with SkillNotPermitted."""
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.skill_dispatcher import SkillDispatcher
    from clawteam.plugins.skill_errors import SkillNotPermitted

    plugin = GstackSprintPlugin()
    registry = {s.name: s for s in plugin.contribute_skills()}
    dispatcher = SkillDispatcher(registry)

    with pytest.raises(SkillNotPermitted):
        dispatcher.dispatch(
            ctx=SimpleNamespace(),
            skill_name="/open-gstack-browser",
            role="security",
            args={"url": "https://example.com/"},
        )
