"""Phase 6 Plan 06-04 Task 1 — adapter.py tests.

Covers navigate_and_screenshot + action_script primitives.

D-16: All Playwright surfaces fully monkeypatched — zero real Chromium
launches in CI. The stub chain (sync_playwright -> browser -> context -> page)
only implements the methods the adapter actually calls.

D-02: test_no_toplevel_playwright_import statically asserts that no
top-level ``import playwright`` / ``from playwright ...`` line exists in
clawteam/browser/adapter.py.
"""

from __future__ import annotations

import hashlib
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest


# ── Stub Playwright chain ──────────────────────────────────────────────────


class _FakeResponse:
    def __init__(self, status: int = 200) -> None:
        self.status = status


class _FakePage:
    def __init__(
        self,
        *,
        content_html: str = "<html>hi</html>",
        goto_status: int = 200,
        goto_raises: BaseException | None = None,
    ) -> None:
        self._content = content_html
        self._goto_status = goto_status
        self._goto_raises = goto_raises
        self.method_calls: list[tuple[str, tuple, dict]] = []

    def goto(self, url: str, timeout: int = 0):
        self.method_calls.append(("goto", (url,), {"timeout": timeout}))
        if self._goto_raises is not None:
            raise self._goto_raises
        return _FakeResponse(self._goto_status)

    def screenshot(self, full_page: bool = False) -> bytes:
        self.method_calls.append(("screenshot", (), {"full_page": full_page}))
        return b"\x89PNG\r\n\x1a\nFAKE"

    def content(self) -> str:
        self.method_calls.append(("content", (), {}))
        return self._content

    def click(self, selector: str) -> None:
        self.method_calls.append(("click", (selector,), {}))

    def fill(self, selector: str, value: str) -> None:
        self.method_calls.append(("fill", (selector, value), {}))

    def wait_for_selector(self, selector: str, timeout: int = 0) -> None:
        self.method_calls.append(
            ("wait_for_selector", (selector,), {"timeout": timeout})
        )


class _FakeContext:
    def __init__(self, page: _FakePage) -> None:
        self._page = page
        self.added_cookies: list[dict[str, Any]] | None = None

    def new_page(self) -> _FakePage:
        return self._page

    def add_cookies(self, cookies: list[dict[str, Any]]) -> None:
        self.added_cookies = list(cookies)


class _FakeBrowser:
    def __init__(self, context: _FakeContext) -> None:
        self._context = context
        self.close_calls = 0

    def new_context(self, **kwargs) -> _FakeContext:
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


def _make_stub_sync_playwright(page: _FakePage):
    """Build sync_playwright() stub that returns a context-manager chain."""
    context = _FakeContext(page)
    browser = _FakeBrowser(context)
    chromium = _FakeChromium(browser)
    playwright = _FakePlaywright(chromium)

    @contextmanager
    def _cm():
        yield playwright

    def sync_playwright_factory():
        return _cm()

    # Return closure + handles to inspect recorded state later.
    sync_playwright_factory._playwright = playwright
    sync_playwright_factory._browser = browser
    sync_playwright_factory._context = context
    sync_playwright_factory._chromium = chromium
    return sync_playwright_factory


# ── Tests ──────────────────────────────────────────────────────────────────


def test_navigate_happy_path(monkeypatch):
    from clawteam.browser import adapter

    page = _FakePage(content_html="<html><body>test</body></html>")
    sp = _make_stub_sync_playwright(page)
    monkeypatch.setattr(adapter, "playwright_available", lambda: True)
    monkeypatch.setattr(adapter, "_import_sync_playwright", lambda: sp)

    dom_hash, http_status, screenshot_bytes = adapter.navigate_and_screenshot(
        url="https://example.com"
    )

    assert isinstance(dom_hash, str)
    assert len(dom_hash) == 64
    assert re.fullmatch(r"[0-9a-f]{64}", dom_hash) is not None
    expected = hashlib.sha256(
        "<html><body>test</body></html>".encode("utf-8", errors="replace")
    ).hexdigest()
    assert dom_hash == expected
    assert http_status == 200
    assert isinstance(screenshot_bytes, bytes)
    assert len(screenshot_bytes) > 0
    # Browser was closed on exit (finally).
    assert sp._browser.close_calls == 1


def test_navigate_raises_when_unavailable(monkeypatch):
    from clawteam.browser import adapter
    from clawteam.plugins.skill_errors import SkillUnavailable

    monkeypatch.setattr(adapter, "playwright_available", lambda: False)

    with pytest.raises(SkillUnavailable) as exc:
        adapter.navigate_and_screenshot(url="https://example.com")
    assert "playwright" in exc.value.install_hint.lower()


def test_navigate_timeout_propagates(monkeypatch):
    from clawteam.browser import adapter

    page = _FakePage(goto_raises=TimeoutError("timed out"))
    sp = _make_stub_sync_playwright(page)
    monkeypatch.setattr(adapter, "playwright_available", lambda: True)
    monkeypatch.setattr(adapter, "_import_sync_playwright", lambda: sp)

    with pytest.raises(TimeoutError):
        adapter.navigate_and_screenshot(url="https://example.com")
    # Browser still closed even on timeout (finally).
    assert sp._browser.close_calls == 1


def test_navigate_http_4xx_still_returns(monkeypatch):
    from clawteam.browser import adapter

    page = _FakePage(content_html="<html>404</html>", goto_status=404)
    sp = _make_stub_sync_playwright(page)
    monkeypatch.setattr(adapter, "playwright_available", lambda: True)
    monkeypatch.setattr(adapter, "_import_sync_playwright", lambda: sp)

    dom_hash, http_status, screenshot_bytes = adapter.navigate_and_screenshot(
        url="https://example.com/missing"
    )
    assert http_status == 404
    assert isinstance(dom_hash, str) and len(dom_hash) == 64
    assert isinstance(screenshot_bytes, bytes)


def test_action_script_executes(monkeypatch):
    from clawteam.browser import adapter

    page = _FakePage()
    sp = _make_stub_sync_playwright(page)
    monkeypatch.setattr(adapter, "playwright_available", lambda: True)
    monkeypatch.setattr(adapter, "_import_sync_playwright", lambda: sp)

    result = adapter.action_script(
        url="https://example.com",
        actions=[
            {"type": "click", "selector": "#btn"},
            {"type": "fill", "selector": "input", "value": "hi"},
            {"type": "screenshot"},
        ],
    )

    method_names = [c[0] for c in page.method_calls]
    # First 'goto' then click then fill then screenshot
    assert method_names[0] == "goto"
    click_idx = method_names.index("click")
    fill_idx = method_names.index("fill")
    screenshot_idx = method_names.index("screenshot")
    assert click_idx < fill_idx < screenshot_idx
    # Verify argument passing
    click_call = page.method_calls[click_idx]
    assert click_call[1] == ("#btn",)
    fill_call = page.method_calls[fill_idx]
    assert fill_call[1] == ("input", "hi")
    assert result["action_count"] == 3
    assert len(result["screenshots"]) == 1
    assert result["http_status"] == 200


def test_action_script_unknown_action_raises(monkeypatch):
    from clawteam.browser import adapter

    page = _FakePage()
    sp = _make_stub_sync_playwright(page)
    monkeypatch.setattr(adapter, "playwright_available", lambda: True)
    monkeypatch.setattr(adapter, "_import_sync_playwright", lambda: sp)

    with pytest.raises(ValueError) as exc:
        adapter.action_script(
            url="https://example.com",
            actions=[{"type": "teleport"}],
        )
    assert "teleport" in str(exc.value)


def test_no_toplevel_playwright_import():
    """D-02: adapter.py MUST NOT contain any top-level `import playwright` line."""
    adapter_path = (
        Path(__file__).resolve().parents[2]
        / "clawteam"
        / "browser"
        / "adapter.py"
    )
    assert adapter_path.is_file(), f"adapter.py missing at {adapter_path}"
    text = adapter_path.read_text(encoding="utf-8")
    # Any line that starts (trimmed) with 'import playwright' or 'from playwright'
    # is forbidden. Lazy imports live inside function bodies (indented).
    pattern = re.compile(r"^(?:import|from)\s+playwright\b", re.MULTILINE)
    matches = pattern.findall(text)
    assert not matches, (
        "adapter.py has top-level playwright import lines; D-02 requires "
        "lazy imports inside function bodies only."
    )
