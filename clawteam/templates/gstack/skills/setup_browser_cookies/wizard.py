"""Pure questionary wizard for /setup-browser-cookies (SKILL-10 part 3).

Mirrors the Phase 5 ``setup_deploy/wizard.py`` split: this module owns
input prompts + validation only — no filesystem side effects. Tests
monkeypatch :func:`run_wizard` + :func:`confirm_overwrite` on the handler
module namespace so the full flow can be exercised without a TTY.

Validators:

- :func:`validate_domain` — DNS-ish identifier (alphanumeric + ``.`` +
  ``-``) with explicit path-traversal guards. Rejects empty, whitespace,
  non-string values, and strings whose first or last character is a
  separator. Matches the shape enforced by
  :func:`clawteam.browser.cookies._validate_domain` so an accepted
  wizard answer never gets rejected by the cookie-jar writer.
- :func:`validate_url` — http(s) only, non-empty.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# First and last character must be alphanumeric; middle may also contain
# ``.`` or ``-``. The explicit guards below catch path-traversal and
# whitespace BEFORE the regex so an ambiguous message never surfaces.
_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9.\-]*[a-zA-Z0-9])?$")


def validate_domain(value: Any) -> bool:
    """Return True iff *value* is a valid DNS-ish cookie domain.

    Layered fail-fast:
      1. Must be a non-empty ``str``.
      2. Rejects ``..`` / ``/`` / ``\\`` / whitespace (T-06-07-01).
      3. Full-match the DNS-ish regex.
    """
    if not isinstance(value, str) or not value:
        return False
    if ".." in value or "/" in value or "\\" in value or " " in value:
        return False
    return bool(_DOMAIN_RE.fullmatch(value))


def validate_url(value: Any) -> bool:
    """Return True iff *value* is a non-empty http(s) URL string."""
    if not isinstance(value, str) or not value:
        return False
    return value.startswith("http://") or value.startswith("https://")


def _load_questionary() -> Any:
    """Lazy-import questionary (mirrors clawteam/cli/commands.py:173 pattern).

    Tests monkeypatch :func:`run_wizard` + :func:`confirm_overwrite` at the
    handler-module level so this importer is not in their hot path — it
    exists so an out-of-the-box dev machine without questionary gets a
    clean actionable error instead of an obscure ImportError at module
    load time.
    """
    try:
        import questionary  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover — questionary is a hard dep
        raise RuntimeError(
            "questionary is required for /setup-browser-cookies but is missing; "
            "install with: pip install 'questionary>=2.0.1,<3.0.0'"
        ) from exc
    return questionary


def run_wizard() -> Optional[dict[str, Any]]:
    """Interactive cookie-capture wizard; returns answers dict or ``None`` on abort.

    Prompts in order:

    1. ``domain`` — text, validated via :func:`validate_domain`.
    2. ``login_url`` — text, defaults to ``https://<domain>/login``,
       validated via :func:`validate_url`.
    3. ``Proceed?`` — confirm gate before the headed browser launches;
       user is instructed to log in and return here before capture.

    Any prompt returning ``None`` (user pressed Ctrl-C) short-circuits
    the wizard and returns ``None``; the handler then writes a
    ``status=aborted`` artifact without touching the cookie jar.
    """
    questionary = _load_questionary()

    domain = questionary.text(
        "Target domain (e.g., staging.example.com):",
        validate=lambda v: "invalid domain" if not validate_domain(v) else True,
    ).ask()
    if domain is None:
        return None

    login_url = questionary.text(
        "Login URL to open in Chromium (https://...):",
        default=f"https://{domain}/login",
        validate=lambda v: "must be http/https URL" if not validate_url(v) else True,
    ).ask()
    if login_url is None:
        return None

    proceed = questionary.confirm(
        (
            "Chromium will open. Log in, then return here and press Enter "
            "to capture cookies. Proceed?"
        ),
        default=True,
    ).ask()
    if not proceed:
        return None

    return {"domain": domain, "login_url": login_url, "user_ready": True}


def confirm_overwrite(domain: str) -> bool:
    """Prompt before overwriting existing cookies for *domain*.

    Defaults to ``False`` so an accidental re-invoke does not clobber an
    authenticated session. The handler calls this only when
    :func:`clawteam.browser.cookies.load_cookies_for_domain` returns a
    non-empty list.
    """
    questionary = _load_questionary()
    return bool(
        questionary.confirm(
            f"Cookies already stored for {domain}. Overwrite?",
            default=False,
        ).ask()
    )


__all__ = ["validate_domain", "validate_url", "run_wizard", "confirm_overwrite"]
