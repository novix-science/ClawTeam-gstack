"""Per-domain cookie persistence under ``<team>/browser/cookies/<domain>.json``.

Phase 6 Plan 06-04 Wave 1 substrate (D-03).

Cookies are stored as a JSON list matching Playwright's own
``context.cookies()`` return shape so ``save → load → add_cookies`` is
pass-through (no transformation layer). All writes flow through
:func:`clawteam.fileutil.file_locked` + :func:`~clawteam.fileutil.atomic_write_text`
so ``/setup-browser-cookies`` (Plan 06-07) stays idempotent on re-runs
and concurrent invocations can't produce a half-written file.

Domain identifiers MUST match a DNS-ish shape: alphanumeric characters,
dots, and dashes only. Path-traversal (``..``, ``/``, ``\\``) is
rejected before any filesystem operation (T-06-04-02).

Public API:
    :func:`cookies_dir` — resolve the cookies sub-directory under a team
    data dir.
    :func:`save_cookies_for_domain` — write a cookie list atomically.
    :func:`load_cookies_for_domain` — read a cookie list; empty on miss
    or malformed JSON (T-06-04-03).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from clawteam.fileutil import atomic_write_text, file_locked

# Domain: subdomain.domain.tld style — alphanumeric plus ``.`` + ``-``.
# Intentionally stricter than ``validate_identifier`` (which allows ``_``):
# cookie domains are DNS-ish so ``_`` has no place here. The first and
# last character must be alphanumeric; middle may also be ``.`` or ``-``.
_DOMAIN_RE = re.compile(r"^[a-zA-Z0-9](?:[a-zA-Z0-9.\-]*[a-zA-Z0-9])?$")


def _validate_domain(domain: str) -> None:
    """Reject non-DNS-ish or path-traversal domain strings.

    Layered check (fail-fast):
      1. Must be a non-empty string.
      2. No ``..`` / ``/`` / ``\\`` — path-traversal block (T-06-04-02).
      3. Full-match DNS regex.

    Raises:
        ValueError: any layer fails. The exception message includes the
            offending value so the caller can surface a remediation.
    """
    if not isinstance(domain, str) or not domain:
        raise ValueError("domain must be a non-empty string")
    if ".." in domain or "/" in domain or "\\" in domain:
        raise ValueError(
            f"domain {domain!r} contains path-traversal characters"
        )
    if not _DOMAIN_RE.fullmatch(domain):
        raise ValueError(
            f"domain {domain!r} is not a valid DNS-ish identifier"
        )


def cookies_dir(team_dir: Path) -> Path:
    """Return the cookies directory under *team_dir* (``<team>/browser/cookies``)."""
    return Path(team_dir) / "browser" / "cookies"


def _cookie_path(team_dir: Path, domain: str) -> Path:
    _validate_domain(domain)
    return cookies_dir(team_dir) / f"{domain}.json"


def save_cookies_for_domain(
    team_dir: Path,
    domain: str,
    cookies: list[dict[str, Any]],
) -> Path:
    """Write *cookies* for *domain* atomically under *team_dir*.

    Creates ``<team>/browser/cookies/`` on first call. Subsequent calls
    for the same domain overwrite the previous list atomically — there
    is no append semantics (Playwright's cookie store is
    domain-replace-oriented).

    Returns:
        The target path that was written.

    Raises:
        ValueError: *domain* is not a valid DNS-ish identifier.
    """
    target = _cookie_path(team_dir, domain)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(list(cookies), indent=2, ensure_ascii=False)
    with file_locked(target):
        atomic_write_text(target, payload)
    return target


def load_cookies_for_domain(
    team_dir: Path,
    domain: str,
) -> list[dict[str, Any]]:
    """Return saved cookies list for *domain*; empty list when missing.

    Malformed JSON on disk also returns ``[]`` (T-06-04-03 — a corrupt
    file must never crash the browser skill; the caller can re-run
    ``/setup-browser-cookies`` to rewrite it).

    Raises:
        ValueError: *domain* is not a valid DNS-ish identifier.
    """
    target = _cookie_path(team_dir, domain)
    if not target.is_file():
        return []
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(data, list):
        return []
    return data


__all__ = [
    "cookies_dir",
    "save_cookies_for_domain",
    "load_cookies_for_domain",
]
