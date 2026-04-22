"""Generic browser substrate — feature detection for Playwright.

Phase 6 Plan 06-01 Wave 0 substrate.

D-02 locks the rule: skill modules never top-level-import ``playwright``.
All three Phase 6 browser skills (``/browse``, ``/open-gstack-browser``,
``/setup-browser-cookies``) plus the optional ``/design-shotgun``
screenshotter route ``tool_available`` probes through this single helper.

Tests monkeypatch :func:`importlib.util.find_spec` (imported into this
module at the top) so a single substitution disables Playwright for all
callers without hacking ``sys.modules``.
"""

from __future__ import annotations

from importlib.util import find_spec


def playwright_available() -> bool:
    """Return True if the ``playwright`` package is importable.

    Uses :func:`importlib.util.find_spec` — zero import-time side effects.
    Does NOT verify that Chromium itself is installed (a separate
    ``playwright install chromium`` step). Skills probe Chromium
    availability lazily at handler-call time via ``sync_playwright()``.
    """
    return find_spec("playwright") is not None


__all__ = ["playwright_available"]
