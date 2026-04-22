"""Browser session factory — headed/headless context with cookie injection.

Phase 6 Plan 06-04 Wave 1 substrate.

Wrapper around Playwright's ``sync_playwright`` + ``browser.new_context``
that:
    (a) gates on :func:`clawteam.browser.playwright_available` before any
        real import is attempted,
    (b) exposes a single ``with``-compatible context manager callers use
        to acquire a Playwright browser context,
    (c) ensures the underlying browser is closed on exit (even on error).

``/open-gstack-browser`` (Plan 06-06) uses :func:`open_headed_with_context`
to launch a human-visible Chromium pre-seeded with sprint-aware cookies.
``/browse`` (Plan 06-05) transitively consumes this module via
:mod:`clawteam.browser.adapter`.

D-02 invariant: reuses
:func:`clawteam.browser.adapter._import_sync_playwright` so the whole
package has a SINGLE lazy-import seam — monkeypatching it once disables
Playwright for all browser code.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

from clawteam.browser import playwright_available
from clawteam.browser.adapter import _import_sync_playwright
from clawteam.plugins.skill_errors import SkillUnavailable

_INSTALL_HINT = (
    "pip install 'clawteam[browser]' && playwright install chromium"
)


@contextmanager
def build_browser_context(
    *,
    headless: bool = True,
    cookies: list[dict[str, Any]] | None = None,
    viewport: tuple[int, int] | None = None,
) -> Iterator[Any]:
    """Yield a Playwright ``BrowserContext``; closes browser on exit.

    Args:
        headless: If True (default), Chromium runs headlessly. Set False
            for ``/open-gstack-browser`` human-visible flows.
        cookies: Optional list of Playwright-shaped cookie dicts to seed
            the context with. Pass the return value of
            :func:`clawteam.browser.cookies.load_cookies_for_domain` here.
        viewport: Optional ``(width, height)`` pair. When None, Playwright
            uses its default viewport (1280x720).

    Raises:
        SkillUnavailable: Playwright is not installed.
    """
    if not playwright_available():
        raise SkillUnavailable(
            skill="/open-gstack-browser",
            binary="playwright",
            install_hint=_INSTALL_HINT,
        )
    sync_playwright = _import_sync_playwright()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        try:
            context_kwargs: dict[str, Any] = {}
            if viewport is not None:
                w, h = viewport
                context_kwargs["viewport"] = {"width": w, "height": h}
            context = browser.new_context(**context_kwargs)
            if cookies:
                context.add_cookies(cookies)
            yield context
        finally:
            browser.close()


@contextmanager
def open_headed_with_context(
    *,
    cookies: list[dict[str, Any]] | None = None,
    viewport: tuple[int, int] | None = None,
) -> Iterator[Any]:
    """Convenience wrapper for ``/open-gstack-browser`` — ``headless=False``.

    Thin delegation to :func:`build_browser_context` so tests can target
    the generic factory and the headed-mode wrapper with the same stub.
    """
    with build_browser_context(
        headless=False, cookies=cookies, viewport=viewport,
    ) as ctx:
        yield ctx


__all__ = ["build_browser_context", "open_headed_with_context"]
