"""Phase 6 Plan 06-04 Task 3 — cookies.py tests.

Covers per-domain cookie jar at ``<team>/browser/cookies/<domain>.json``.

D-03 + T-06-04-02: path-traversal domains rejected via regex gate.
T-06-04-03: malformed JSON on load returns [] (never crashes).
Writes route through ``file_locked`` + ``atomic_write_text`` so
``/setup-browser-cookies`` is idempotent across re-runs.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest


# ── Tests ──────────────────────────────────────────────────────────────────


def test_save_and_load_roundtrip(tmp_path: Path):
    from clawteam.browser.cookies import (
        load_cookies_for_domain,
        save_cookies_for_domain,
    )

    cookies: list[dict[str, Any]] = [
        {
            "name": "sid",
            "value": "abc",
            "domain": "example.com",
            "path": "/",
            "expires": 1_700_000_000,
        }
    ]
    target = save_cookies_for_domain(tmp_path, "example.com", cookies)
    assert target == tmp_path / "browser" / "cookies" / "example.com.json"
    assert target.is_file()

    loaded = load_cookies_for_domain(tmp_path, "example.com")
    assert loaded == cookies


def test_save_rejects_path_traversal_domain(tmp_path: Path):
    from clawteam.browser.cookies import save_cookies_for_domain

    with pytest.raises(ValueError):
        save_cookies_for_domain(tmp_path, "../../etc", [])


def test_save_rejects_absolute_path(tmp_path: Path):
    from clawteam.browser.cookies import save_cookies_for_domain

    with pytest.raises(ValueError):
        save_cookies_for_domain(tmp_path, "/etc/passwd", [])


def test_save_rejects_backslash(tmp_path: Path):
    from clawteam.browser.cookies import save_cookies_for_domain

    with pytest.raises(ValueError):
        save_cookies_for_domain(tmp_path, "example\\..com", [])


def test_save_domain_with_subdomain(tmp_path: Path):
    from clawteam.browser.cookies import save_cookies_for_domain

    target = save_cookies_for_domain(tmp_path, "api.example.com", [])
    assert target.is_file()
    # Dashes also allowed
    target2 = save_cookies_for_domain(tmp_path, "my-api.example-site.co", [])
    assert target2.is_file()


def test_load_missing_returns_empty(tmp_path: Path):
    from clawteam.browser.cookies import load_cookies_for_domain

    result = load_cookies_for_domain(tmp_path, "nonexistent.com")
    assert result == []


def test_load_malformed_json_returns_empty(tmp_path: Path):
    """T-06-04-03: malformed JSON does not crash the loader."""
    from clawteam.browser.cookies import (
        cookies_dir,
        load_cookies_for_domain,
    )

    d = cookies_dir(tmp_path)
    d.mkdir(parents=True, exist_ok=True)
    (d / "bad.com.json").write_text("{not json[", encoding="utf-8")

    result = load_cookies_for_domain(tmp_path, "bad.com")
    assert result == []


def test_save_uses_file_locked(tmp_path: Path, monkeypatch):
    """Assert save routes the write through file_locked()."""
    from clawteam.browser import cookies as cookies_mod

    lock_calls: list[Path] = []
    orig_file_locked = cookies_mod.file_locked

    @contextmanager
    def _tracer(path: Path):
        lock_calls.append(Path(path))
        with orig_file_locked(path):
            yield

    monkeypatch.setattr(cookies_mod, "file_locked", _tracer)
    cookies_mod.save_cookies_for_domain(tmp_path, "example.com", [])
    assert len(lock_calls) == 1
    assert lock_calls[0] == tmp_path / "browser" / "cookies" / "example.com.json"


def test_save_uses_atomic_write_text(tmp_path: Path, monkeypatch):
    """Assert save routes the serialization through atomic_write_text()."""
    from clawteam.browser import cookies as cookies_mod

    awt_calls: list[tuple[Path, str]] = []
    orig_awt = cookies_mod.atomic_write_text

    def _tracer(path: Path, content: str, **kwargs):
        awt_calls.append((Path(path), content))
        orig_awt(path, content, **kwargs)

    monkeypatch.setattr(cookies_mod, "atomic_write_text", _tracer)
    cookies = [{"name": "sid", "value": "abc"}]
    cookies_mod.save_cookies_for_domain(tmp_path, "example.com", cookies)
    assert len(awt_calls) == 1
    path, content = awt_calls[0]
    assert path == tmp_path / "browser" / "cookies" / "example.com.json"
    # Content is valid JSON of the cookies list
    parsed = json.loads(content)
    assert parsed == cookies


def test_cookies_dir_is_created(tmp_path: Path):
    from clawteam.browser.cookies import save_cookies_for_domain

    cookies_path = tmp_path / "browser" / "cookies"
    assert not cookies_path.exists()
    save_cookies_for_domain(tmp_path, "example.com", [{"name": "a"}])
    assert cookies_path.is_dir()


def test_cookies_dir_helper(tmp_path: Path):
    from clawteam.browser.cookies import cookies_dir

    assert cookies_dir(tmp_path) == tmp_path / "browser" / "cookies"


def test_empty_domain_rejected(tmp_path: Path):
    from clawteam.browser.cookies import save_cookies_for_domain

    with pytest.raises(ValueError):
        save_cookies_for_domain(tmp_path, "", [])


def test_package_level_reexports():
    """__init__.py re-exports all three substrate modules' public API."""
    import clawteam.browser as pkg

    for name in (
        "playwright_available",
        "navigate_and_screenshot",
        "action_script",
        "build_browser_context",
        "open_headed_with_context",
        "cookies_dir",
        "save_cookies_for_domain",
        "load_cookies_for_domain",
    ):
        assert hasattr(pkg, name), f"clawteam.browser missing re-export: {name}"


def test_package_import_does_not_leak_playwright():
    """D-02 invariant — after re-exports land, `import clawteam.browser`
    still MUST NOT materialize ``playwright`` in ``sys.modules``.
    """
    import importlib
    import sys

    sys.modules.pop("playwright", None)
    sys.modules.pop("clawteam.browser", None)
    sys.modules.pop("clawteam.browser.adapter", None)
    sys.modules.pop("clawteam.browser.session", None)
    sys.modules.pop("clawteam.browser.cookies", None)

    import clawteam.browser  # noqa: F401
    importlib.reload(sys.modules["clawteam.browser"])
    assert "playwright" not in sys.modules, (
        "clawteam.browser package import leaked 'playwright' into sys.modules"
    )
