"""Playwright adapter — lazy-imported substrate for /browse and friends.

Phase 6 Plan 06-04 Wave 1 substrate (D-01/D-02/D-03, SKILL-10 dependency).

D-02 invariant: Playwright is imported ONLY inside function bodies of this
module. :func:`clawteam.browser.playwright_available` is the probe that
gates every entry point; the lazy import sits behind
:func:`_import_sync_playwright` so tests can monkeypatch it without ever
executing ``from playwright.sync_api import sync_playwright`` for real.

Pitfall 5 precedent (Phase 5 /canary handler line 28): this module mirrors
the same ``find_spec``-only top-level import surface, which makes
``import clawteam.browser.adapter`` on a machine without the browser extra
a zero-side-effect operation — no ModuleNotFoundError, no leak into
``sys.modules``.

Public API:
    :func:`navigate_and_screenshot` — one-shot navigate + PNG + DOM hash.
    :func:`action_script` — replay a small list of page actions (click,
    fill, screenshot, wait_for_selector) and return a result dict.

Both raise :class:`SkillUnavailable` when Playwright is not installed.
TimeoutErrors from ``page.goto`` propagate (never swallowed).
"""
from __future__ import annotations

import hashlib
from typing import Any

from clawteam.browser import playwright_available
from clawteam.plugins.skill_errors import SkillUnavailable

_INSTALL_HINT = (
    "pip install 'clawteam[browser]' && playwright install chromium"
)


def _import_sync_playwright():
    """Lazy import of ``playwright.sync_api.sync_playwright``.

    Separated as a private helper so tests can monkeypatch this single
    seam to return a stub factory without ever touching real Playwright.
    """
    from playwright.sync_api import sync_playwright  # noqa: PLC0415
    return sync_playwright


def _require_available() -> None:
    """Raise :class:`SkillUnavailable` when Playwright is not installed."""
    if not playwright_available():
        raise SkillUnavailable(
            skill="/browser",
            binary="playwright",
            install_hint=_INSTALL_HINT,
        )


def navigate_and_screenshot(
    url: str,
    *,
    headless: bool = True,
    timeout_seconds: int = 30,
    cookies: list[dict[str, Any]] | None = None,
) -> tuple[str, int, bytes]:
    """Navigate to *url*, capture PNG, return ``(dom_hash, http_status, png)``.

    - ``dom_hash``: sha256 hex digest of ``page.content()`` — a stable
      content fingerprint for drift detection.
    - ``http_status``: integer HTTP status of the main navigation response
      (0 if no response object). 4xx/5xx responses still return — the
      caller decides whether to treat them as failure.
    - ``png_bytes``: full-page PNG screenshot bytes.

    Raises:
        SkillUnavailable: Playwright is not installed.
        TimeoutError: page.goto exceeded ``timeout_seconds`` — never
            swallowed, always propagates so the caller can fall back.
    """
    _require_available()
    sync_playwright = _import_sync_playwright()
    timeout_ms = timeout_seconds * 1000

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context()
            if cookies:
                context.add_cookies(cookies)
            page = context.new_page()
            response = page.goto(url, timeout=timeout_ms)
            http_status = response.status if response is not None else 0
            content = page.content()
            screenshot_bytes = page.screenshot(full_page=True)
        finally:
            browser.close()

    dom_hash = hashlib.sha256(
        content.encode("utf-8", errors="replace")
    ).hexdigest()
    return dom_hash, http_status, screenshot_bytes


def action_script(
    url: str,
    actions: list[dict[str, Any]],
    *,
    headless: bool = True,
    timeout_seconds: int = 30,
    cookies: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute a small ordered action script against a page.

    Supported action shapes:
        ``{"type": "click",   "selector": "#btn"}``
        ``{"type": "fill",    "selector": "input[name=q]", "value": "hi"}``
        ``{"type": "screenshot"}`` — appended to ``result["screenshots"]``.
        ``{"type": "wait_for_selector", "selector": ".ready", "timeout": 10}``

    Returns a dict with ``url``, ``http_status``, ``screenshots`` (list of
    PNG bytes), and ``action_count`` (number of actions successfully
    executed).

    Raises:
        SkillUnavailable: Playwright is not installed.
        ValueError: Unknown action type.
    """
    _require_available()
    sync_playwright = _import_sync_playwright()
    timeout_ms = timeout_seconds * 1000

    result: dict[str, Any] = {
        "url": url,
        "http_status": 0,
        "screenshots": [],
        "action_count": 0,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context()
            if cookies:
                context.add_cookies(cookies)
            page = context.new_page()
            response = page.goto(url, timeout=timeout_ms)
            result["http_status"] = (
                response.status if response is not None else 0
            )
            for action in actions:
                atype = action.get("type", "")
                if atype == "click":
                    page.click(action["selector"])
                elif atype == "fill":
                    page.fill(action["selector"], action.get("value", ""))
                elif atype == "screenshot":
                    result["screenshots"].append(
                        page.screenshot(full_page=True)
                    )
                elif atype == "wait_for_selector":
                    page.wait_for_selector(
                        action["selector"],
                        timeout=action.get("timeout", 10) * 1000,
                    )
                else:
                    raise ValueError(f"unknown action type {atype!r}")
                result["action_count"] += 1
        finally:
            browser.close()

    return result


__all__ = ["navigate_and_screenshot", "action_script"]
