"""Phase 6 Wave 0 / Plan 06-01 Task 1 — playwright_available() feature detection.

Tests the invariants locked by D-02 (never top-level import playwright):
- Returns a plain bool (no import-time side effects).
- Monkeypatching `importlib.util.find_spec` to None yields False.
- Monkeypatching `find_spec` to a non-None ModuleSpec yields True.
- Importing ``clawteam.browser`` MUST NOT pull ``playwright`` into sys.modules.
"""

from __future__ import annotations

import importlib
import sys


def test_playwright_available_returns_bool():
    from clawteam.browser import playwright_available

    assert isinstance(playwright_available(), bool)


def test_unavailable_when_missing(monkeypatch):
    import clawteam.browser as browser_mod

    monkeypatch.setattr(browser_mod, "find_spec", lambda name: None)
    assert browser_mod.playwright_available() is False


def test_available_when_spec_found(monkeypatch):
    import clawteam.browser as browser_mod

    class _FakeSpec:
        name = "playwright"

    monkeypatch.setattr(browser_mod, "find_spec", lambda name: _FakeSpec())
    assert browser_mod.playwright_available() is True


def test_no_toplevel_import():
    """`import clawteam.browser` MUST NOT drag playwright into sys.modules.

    D-02 hard invariant — every Phase 6 browser skill routes its
    tool-availability probe through ``playwright_available`` so disabling
    Playwright at the ``find_spec`` layer disables it for all callers
    without anyone sneaking a top-level ``import playwright``.
    """
    # Evict any prior playwright binding so a stale leak from an unrelated
    # test module doesn't falsely satisfy the assertion.
    sys.modules.pop("playwright", None)
    sys.modules.pop("clawteam.browser", None)

    # Fresh import.
    import clawteam.browser  # noqa: F401

    # Re-reload is belt-and-braces: even if something above imported the
    # package transitively, reload() re-executes the module body — which is
    # what we're auditing.
    importlib.reload(sys.modules["clawteam.browser"])

    assert "playwright" not in sys.modules, (
        "clawteam.browser accidentally top-level-imported playwright; "
        "D-02 requires find_spec only"
    )
