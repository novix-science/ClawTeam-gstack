"""Phase 6 Plan 06-04 Task 2 — session.py tests.

Covers build_browser_context + open_headed_with_context factories.

D-02: ``build_browser_context`` reuses ``_import_sync_playwright`` from
the adapter module (single lazy-import seam for the whole package).
D-16: sync_playwright stubbed; zero real Chromium launches.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest


# ── Stub Playwright chain (minimal; mirrors test_adapter.py shape) ─────────


class _FakeContext:
    def __init__(self) -> None:
        self.added_cookies: list[dict[str, Any]] | None = None
        self.kwargs: dict[str, Any] = {}

    def add_cookies(self, cookies: list[dict[str, Any]]) -> None:
        self.added_cookies = list(cookies)


class _FakeBrowser:
    def __init__(self) -> None:
        self._context = _FakeContext()
        self.close_calls = 0
        self.new_context_kwargs: dict[str, Any] | None = None

    def new_context(self, **kwargs) -> _FakeContext:
        self.new_context_kwargs = dict(kwargs)
        self._context.kwargs = dict(kwargs)
        return self._context

    def close(self) -> None:
        self.close_calls += 1


class _FakeChromium:
    def __init__(self, browser: _FakeBrowser) -> None:
        self._browser = browser
        self.launch_kwargs: dict[str, Any] | None = None

    def launch(self, **kwargs) -> _FakeBrowser:
        self.launch_kwargs = dict(kwargs)
        return self._browser


class _FakePlaywright:
    def __init__(self, chromium: _FakeChromium) -> None:
        self.chromium = chromium


def _make_stub_sync_playwright():
    browser = _FakeBrowser()
    chromium = _FakeChromium(browser)
    pw = _FakePlaywright(chromium)

    @contextmanager
    def _cm():
        yield pw

    def factory():
        return _cm()

    factory._browser = browser
    factory._chromium = chromium
    factory._playwright = pw
    return factory


# ── Tests ──────────────────────────────────────────────────────────────────


def test_build_browser_context_headless(monkeypatch):
    from clawteam.browser import session

    sp = _make_stub_sync_playwright()
    monkeypatch.setattr(session, "playwright_available", lambda: True)
    monkeypatch.setattr(session, "_import_sync_playwright", lambda: sp)

    with session.build_browser_context(headless=True) as ctx:
        assert ctx is sp._browser._context

    assert sp._chromium.launch_kwargs == {"headless": True}


def test_build_browser_context_headed(monkeypatch):
    from clawteam.browser import session

    sp = _make_stub_sync_playwright()
    monkeypatch.setattr(session, "playwright_available", lambda: True)
    monkeypatch.setattr(session, "_import_sync_playwright", lambda: sp)

    with session.build_browser_context(headless=False) as _ctx:
        pass

    assert sp._chromium.launch_kwargs == {"headless": False}


def test_context_adds_cookies(monkeypatch):
    from clawteam.browser import session

    sp = _make_stub_sync_playwright()
    monkeypatch.setattr(session, "playwright_available", lambda: True)
    monkeypatch.setattr(session, "_import_sync_playwright", lambda: sp)

    cookies = [{"name": "sid", "value": "abc", "domain": "example.com", "path": "/"}]
    with session.build_browser_context(cookies=cookies) as ctx:
        assert ctx.added_cookies == cookies


def test_unavailable_raises_on_enter(monkeypatch):
    from clawteam.browser import session
    from clawteam.plugins.skill_errors import SkillUnavailable

    monkeypatch.setattr(session, "playwright_available", lambda: False)

    with pytest.raises(SkillUnavailable):
        with session.build_browser_context():
            pass


def test_close_on_exit(monkeypatch):
    from clawteam.browser import session

    sp = _make_stub_sync_playwright()
    monkeypatch.setattr(session, "playwright_available", lambda: True)
    monkeypatch.setattr(session, "_import_sync_playwright", lambda: sp)

    with session.build_browser_context() as _ctx:
        pass
    assert sp._browser.close_calls == 1


def test_open_headed_with_context_forces_headless_false(monkeypatch):
    from clawteam.browser import session

    sp = _make_stub_sync_playwright()
    monkeypatch.setattr(session, "playwright_available", lambda: True)
    monkeypatch.setattr(session, "_import_sync_playwright", lambda: sp)

    with session.open_headed_with_context() as _ctx:
        pass
    assert sp._chromium.launch_kwargs == {"headless": False}


def test_viewport_forwarded_to_new_context(monkeypatch):
    from clawteam.browser import session

    sp = _make_stub_sync_playwright()
    monkeypatch.setattr(session, "playwright_available", lambda: True)
    monkeypatch.setattr(session, "_import_sync_playwright", lambda: sp)

    with session.build_browser_context(viewport=(1280, 720)) as _ctx:
        pass
    assert sp._browser.new_context_kwargs == {
        "viewport": {"width": 1280, "height": 720}
    }
