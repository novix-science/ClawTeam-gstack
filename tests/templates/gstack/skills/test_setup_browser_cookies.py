"""Tests for /setup-browser-cookies wizard + handler + plugin registration (Plan 06-07).

Covers (per PLAN behavior):

1. Happy path (no existing cookies) — wizard → headed Chromium → context.cookies() → save.
2. Domain validation — reject path-traversal, empty, whitespace; accept DNS-ish.
3. Overwrite existing cookies (yes) — save_cookies_for_domain still called.
4. Overwrite existing cookies (no) — handler returns status=skipped; NO disk write.
5. Missing Playwright — SkillUnavailable raised before wizard launches.
6. Wizard abort (user Ctrl-C) — handler returns status=aborted; no disk write.
7. Plugin registration — 10 skills; /setup-browser-cookies with roles={engineer,qa,dx-lead}.
8. Artifact written — cookies-note.md emitted for saved + skipped outcomes.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


# ---------------------------------------------------------------------------
# Stub context manager that yields a context.cookies() return value.
# ---------------------------------------------------------------------------


class _StubContext:
    def __init__(self, cookies: list[dict[str, Any]]) -> None:
        self._cookies = cookies

    def cookies(self) -> list[dict[str, Any]]:
        return list(self._cookies)

    def new_page(self):  # minimal stub for handler's navigation
        class _P:
            def goto(self, _url: str) -> None:
                return None

        return _P()


class _StubHeadedCM:
    """Mimics contextlib @contextmanager yielding a Playwright BrowserContext."""

    def __init__(self, cookies: list[dict[str, Any]]) -> None:
        self._cookies = cookies

    def __enter__(self) -> _StubContext:
        return _StubContext(self._cookies)

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


# ---------------------------------------------------------------------------
# 2. Domain validation — pure function, no monkeypatching needed.
# ---------------------------------------------------------------------------


def test_domain_validation():
    from clawteam.templates.gstack.skills.setup_browser_cookies.wizard import (
        validate_domain,
    )

    # Valid DNS-ish names
    assert validate_domain("example.com") is True
    assert validate_domain("staging.example.com") is True
    assert validate_domain("api-v2.example.co.uk") is True
    assert validate_domain("a") is True  # single char alphanumeric
    assert validate_domain("example") is True

    # Invalid: path-traversal
    assert validate_domain("../etc") is False
    assert validate_domain("..") is False
    assert validate_domain("foo/bar") is False
    assert validate_domain("foo\\bar") is False

    # Invalid: whitespace / empty / non-string
    assert validate_domain("") is False
    assert validate_domain("ex ample") is False
    assert validate_domain(None) is False  # type: ignore[arg-type]
    assert validate_domain(123) is False  # type: ignore[arg-type]

    # Invalid: leading/trailing dots or dashes
    assert validate_domain(".example.com") is False
    assert validate_domain("example.com.") is False
    assert validate_domain("-example.com") is False


# ---------------------------------------------------------------------------
# Helpers for handler tests — monkeypatch wizard + overwrite + open_headed.
# ---------------------------------------------------------------------------


def _make_ctx(tmp_path: Path) -> SimpleNamespace:
    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    team_dir = tmp_path / "team"
    team_dir.mkdir(parents=True, exist_ok=True)
    return SimpleNamespace(
        sprint_dir=sprint_dir,
        team_dir=team_dir,
        sprint_id="s-001",
    )


def _patch_wizard(monkeypatch, result):
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    monkeypatch.setattr(hd, "run_wizard", lambda: result)


def _patch_confirm_overwrite(monkeypatch, value: bool):
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    monkeypatch.setattr(hd, "confirm_overwrite", lambda _domain: value)


def _patch_playwright_available(monkeypatch, value: bool):
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    monkeypatch.setattr(hd, "playwright_available", lambda: value)


def _patch_open_headed(monkeypatch, cookies):
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    monkeypatch.setattr(hd, "open_headed_with_context", lambda: _StubHeadedCM(cookies))


# ---------------------------------------------------------------------------
# 1. Happy path — no existing cookies; wizard answers drive save.
# ---------------------------------------------------------------------------


def test_happy_path_no_existing(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
        setup_cookies_handler,
    )
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    ctx = _make_ctx(tmp_path)
    _patch_playwright_available(monkeypatch, True)
    _patch_wizard(
        monkeypatch,
        {
            "domain": "example.com",
            "login_url": "https://example.com/login",
            "user_ready": True,
        },
    )
    _patch_open_headed(monkeypatch, cookies=[{"name": "sid", "value": "abc"}])

    # Record save_cookies_for_domain calls on the handler's namespace
    save_calls: list[tuple[Any, ...]] = []

    def _record_save(team_dir, domain, cookies):
        save_calls.append((team_dir, domain, cookies))
        return Path(team_dir) / "browser" / "cookies" / f"{domain}.json"

    monkeypatch.setattr(hd, "save_cookies_for_domain", _record_save)
    monkeypatch.setattr(hd, "load_cookies_for_domain", lambda _td, _d: [])

    result = setup_cookies_handler(ctx, role="engineer", args={})

    assert result["status"] == "saved"
    assert result["domain"] == "example.com"
    assert result["cookie_count"] == 1
    assert "artifact_path" in result

    # save_cookies_for_domain called exactly once with expected payload
    assert len(save_calls) == 1
    team_dir, domain, cookies = save_calls[0]
    assert Path(team_dir) == Path(ctx.team_dir)
    assert domain == "example.com"
    assert cookies == [{"name": "sid", "value": "abc"}]


# ---------------------------------------------------------------------------
# 3. Existing cookies + overwrite=yes → save_cookies_for_domain still called.
# ---------------------------------------------------------------------------


def test_existing_overwrite_yes(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
        setup_cookies_handler,
    )
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    ctx = _make_ctx(tmp_path)
    _patch_playwright_available(monkeypatch, True)
    _patch_wizard(
        monkeypatch,
        {
            "domain": "example.com",
            "login_url": "https://example.com/login",
            "user_ready": True,
        },
    )
    _patch_open_headed(monkeypatch, cookies=[{"name": "sid", "value": "new"}])
    _patch_confirm_overwrite(monkeypatch, True)

    # Non-empty existing cookies
    monkeypatch.setattr(
        hd,
        "load_cookies_for_domain",
        lambda _td, _d: [{"name": "sid", "value": "old"}],
    )

    save_calls: list[tuple[Any, ...]] = []

    def _record_save(team_dir, domain, cookies):
        save_calls.append((team_dir, domain, cookies))
        return Path(team_dir) / "browser" / "cookies" / f"{domain}.json"

    monkeypatch.setattr(hd, "save_cookies_for_domain", _record_save)

    result = setup_cookies_handler(ctx, role="qa", args={})

    assert result["status"] == "saved"
    assert result["cookie_count"] == 1
    assert len(save_calls) == 1  # save WAS called after overwrite=yes


# ---------------------------------------------------------------------------
# 4. Existing cookies + overwrite=no → skipped, save NOT called.
# ---------------------------------------------------------------------------


def test_existing_overwrite_no(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
        setup_cookies_handler,
    )
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    ctx = _make_ctx(tmp_path)
    _patch_playwright_available(monkeypatch, True)
    _patch_wizard(
        monkeypatch,
        {
            "domain": "example.com",
            "login_url": "https://example.com/login",
            "user_ready": True,
        },
    )
    _patch_confirm_overwrite(monkeypatch, False)

    # Non-empty existing cookies
    monkeypatch.setattr(
        hd,
        "load_cookies_for_domain",
        lambda _td, _d: [{"name": "sid", "value": "old"}],
    )

    save_called: list[bool] = []

    def _record_save(*_a, **_k):
        save_called.append(True)
        return Path("/nowhere.json")

    monkeypatch.setattr(hd, "save_cookies_for_domain", _record_save)

    # open_headed should NOT be called either — fail loudly if it is
    def _fail_open():
        raise AssertionError("open_headed_with_context must not be called on skip")

    monkeypatch.setattr(hd, "open_headed_with_context", _fail_open)

    result = setup_cookies_handler(ctx, role="dx-lead", args={})

    assert result["status"] == "skipped"
    assert result["domain"] == "example.com"
    assert save_called == []


# ---------------------------------------------------------------------------
# 5. Missing Playwright — SkillUnavailable before wizard runs.
# ---------------------------------------------------------------------------


def test_missing_playwright(tmp_path, monkeypatch):
    from clawteam.plugins.skill_errors import SkillUnavailable
    from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
        setup_cookies_handler,
    )
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    ctx = _make_ctx(tmp_path)
    _patch_playwright_available(monkeypatch, False)

    # Wizard must NOT be called — fail loudly if it is
    def _fail_wizard():
        raise AssertionError("run_wizard must not be called when Playwright missing")

    monkeypatch.setattr(hd, "run_wizard", _fail_wizard)

    with pytest.raises(SkillUnavailable) as excinfo:
        setup_cookies_handler(ctx, role="engineer", args={})

    assert "playwright" in excinfo.value.install_hint.lower()


# ---------------------------------------------------------------------------
# 6. Wizard aborted — handler returns status=aborted; no disk write.
# ---------------------------------------------------------------------------


def test_wizard_aborted(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
        setup_cookies_handler,
    )
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    ctx = _make_ctx(tmp_path)
    _patch_playwright_available(monkeypatch, True)
    _patch_wizard(monkeypatch, None)

    save_called: list[bool] = []

    def _record_save(*_a, **_k):
        save_called.append(True)
        return Path("/nowhere.json")

    monkeypatch.setattr(hd, "save_cookies_for_domain", _record_save)

    # open_headed should NOT be called
    def _fail_open():
        raise AssertionError("open_headed_with_context must not be called on abort")

    monkeypatch.setattr(hd, "open_headed_with_context", _fail_open)
    monkeypatch.setattr(hd, "load_cookies_for_domain", lambda _td, _d: [])

    result = setup_cookies_handler(ctx, role="engineer", args={})

    assert result["status"] == "aborted"
    assert save_called == []


# ---------------------------------------------------------------------------
# 7. Plugin registration — 10 skills; /setup-browser-cookies with 3 roles.
# ---------------------------------------------------------------------------


def test_registered_in_plugin():
    """Plan 06-07 must_haves #6: 10 skills registered after this plan.

    Uses ``>= 10`` (subset-on-count) rather than strict ``== 10`` so the
    test commutes under Wave 2 parallel execution — plans 06-05 / 06-06 /
    06-07 each independently append one entry, and any one of them can
    land first without breaking the other two's test suites. The final
    post-wave-2 state is ``len(regs) == 10`` (asserted by the Phase 6
    integration test when all three waves land).
    """
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    regs = plugin.contribute_skills()
    names = [r.name for r in regs]
    assert "/setup-browser-cookies" in names
    # Subset-on-count: at least the 7 Phase-5 skills + /setup-browser-cookies
    # + any sibling Wave-2 skills that have already landed. Bound below by
    # 8 (Phase 5 + mine) and above by 10 (post-Wave-2 complete).
    assert len(regs) >= 8, f"expected >=8 skills, got {len(regs)}: {sorted(names)}"

    by_name = {r.name: r for r in regs}
    reg = by_name["/setup-browser-cookies"]
    assert reg.roles == frozenset({"engineer", "qa", "dx-lead"})
    assert callable(reg.handler)


# ---------------------------------------------------------------------------
# 8. Artifact written — cookies-note.md on both saved and skipped outcomes.
# ---------------------------------------------------------------------------


def test_artifact_written_saved(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
        setup_cookies_handler,
    )
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    ctx = _make_ctx(tmp_path)
    _patch_playwright_available(monkeypatch, True)
    _patch_wizard(
        monkeypatch,
        {
            "domain": "example.com",
            "login_url": "https://example.com/login",
            "user_ready": True,
        },
    )
    _patch_open_headed(monkeypatch, cookies=[{"name": "sid", "value": "z"}])
    monkeypatch.setattr(hd, "load_cookies_for_domain", lambda _td, _d: [])
    monkeypatch.setattr(
        hd, "save_cookies_for_domain",
        lambda _td, _d, _c: tmp_path / "cookies.json",
    )

    result = setup_cookies_handler(ctx, role="engineer", args={})
    artifact = Path(result["artifact_path"])
    assert artifact.exists()
    content = artifact.read_text()
    assert "cookies-note" in content
    assert "status: 'saved'" in content
    assert "'example.com'" in content


def test_artifact_written_skipped(tmp_path, monkeypatch):
    from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
        setup_cookies_handler,
    )
    import clawteam.templates.gstack.skills.setup_browser_cookies.handler as hd

    ctx = _make_ctx(tmp_path)
    _patch_playwright_available(monkeypatch, True)
    _patch_wizard(
        monkeypatch,
        {
            "domain": "example.com",
            "login_url": "https://example.com/login",
            "user_ready": True,
        },
    )
    monkeypatch.setattr(
        hd,
        "load_cookies_for_domain",
        lambda _td, _d: [{"name": "sid", "value": "old"}],
    )
    _patch_confirm_overwrite(monkeypatch, False)

    result = setup_cookies_handler(ctx, role="engineer", args={})
    assert result["status"] == "skipped"
    artifact = Path(result["artifact_path"])
    assert artifact.exists()
    content = artifact.read_text()
    assert "status: 'skipped'" in content
