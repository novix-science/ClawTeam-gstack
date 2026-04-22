"""Generic browser substrate — feature detection + Playwright wrapper.

Phase 6 Plan 06-01 Wave 0 (feature detection) + Plan 06-04 Wave 1
substrate (adapter / session / cookies).

D-02 locks the rule: browser skill modules never top-level-import
``playwright``. All three Phase 6 browser skills (``/browse``,
``/open-gstack-browser``, ``/setup-browser-cookies``) plus the optional
``/design-shotgun`` screenshotter route their ``tool_available`` probes
through :func:`playwright_available`.

The lazy-import seam for the whole package sits at
:func:`clawteam.browser.adapter._import_sync_playwright` — re-exporting
``navigate_and_screenshot`` / ``action_script`` / ``build_browser_context``
from this ``__init__`` does NOT pull ``playwright`` into ``sys.modules``
because those functions call ``_import_sync_playwright()`` inside their
function bodies only.

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


# Re-exports — must come AFTER playwright_available is defined because
# ``adapter``/``session`` import ``playwright_available`` from this module.
from clawteam.browser.adapter import (  # noqa: E402
    action_script,
    navigate_and_screenshot,
)
from clawteam.browser.cookies import (  # noqa: E402
    cookies_dir,
    load_cookies_for_domain,
    save_cookies_for_domain,
)
from clawteam.browser.session import (  # noqa: E402
    build_browser_context,
    open_headed_with_context,
)


__all__ = [
    "playwright_available",
    "navigate_and_screenshot",
    "action_script",
    "build_browser_context",
    "open_headed_with_context",
    "cookies_dir",
    "save_cookies_for_domain",
    "load_cookies_for_domain",
]
