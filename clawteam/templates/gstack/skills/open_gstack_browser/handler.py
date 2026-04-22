"""/open-gstack-browser handler (SKILL-10, D-03 browser cookies path).

Opens Chromium in HEADED mode (``headless=False``) pre-seeded with
cookies from the team's cookie jar for the URL's host. Intended for
HUMAN interaction — the handler is invoked by a designer/engineer/qa/
dx-lead to see the live UI authenticated.

Phase 6 simplification
----------------------
``sync_playwright`` keeps the Chromium process alive only for the
duration of its ``with`` block. A proper "keep it open until the user
closes the window" loop is a Phase 7 concern (the matching
/close-gstack-browser skill will orchestrate that). For Phase 6 we:

  1. Validate the URL (http/https only — file://, javascript:, data:
     are rejected before any browser launch — T-06-06-01).
  2. Load cookies for the URL's host from the team cookie jar
     (``<team>/browser/cookies/<domain>.json`` via
     :func:`clawteam.browser.load_cookies_for_domain`). A missing
     cookie file is NOT an error — the jar is only populated after
     /setup-browser-cookies runs (Plan 06-07).
  3. Launch headed Chromium via
     :func:`clawteam.browser.open_headed_with_context` with the cookies
     injected into the Playwright BrowserContext.
  4. Navigate to the URL, optionally hold the window for
     ``hold_seconds`` (default 0 so tests don't block), then exit the
     context manager (which closes the browser).
  5. Write an ``open-browser-note.md`` stub artifact with the URL,
     domain, status, and a sprint-aware frontmatter so Phase 2
     EvidenceGate sees completion.

D-02 invariant: this module does NOT top-level-import ``playwright``.
All Playwright access funnels through
:func:`clawteam.browser.open_headed_with_context`, which itself
lazy-imports via :func:`clawteam.browser.adapter._import_sync_playwright`.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from clawteam.browser import load_cookies_for_domain, open_headed_with_context
from clawteam.fileutil import atomic_write_text

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def _validate_url(url: str) -> tuple[str, str]:
    """Return ``(url, domain)`` when *url* is a safe http/https URL.

    ``domain`` is the ``netloc`` with any port stripped so it can be
    used as a filesystem identifier in the cookie jar.

    Raises
    ------
    ValueError
        Non-string / empty / non-http(s) scheme / no host.
    """
    if not isinstance(url, str) or not url:
        raise ValueError("url must be a non-empty string")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"url scheme {parsed.scheme!r} not allowed (http/https only)"
        )
    host = parsed.netloc
    if not host:
        raise ValueError(f"url {url!r} has no host")
    # Strip port — cookie jar keys on domain only.
    domain = host.split(":")[0]
    if not domain:
        raise ValueError(f"url {url!r} has no host")
    return url, domain


def _write_note(
    sprint_dir: Path,
    *,
    url: str,
    domain: str,
    role: str,
    sprint_id: str,
    status: str,
) -> Path:
    """Write a minimal ``open-browser-note.md`` stub into *sprint_dir*.

    Frontmatter-only artifact (no body) — just enough for EvidenceGate
    to register the step as done. Phase 7 may expand this into a richer
    interaction log.
    """
    created_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        "artifact_type: open-browser-note",
        f"url: {url!r}",
        f"domain: {domain!r}",
        f"status: {status!r}",
        f"sprint_id: {sprint_id!r}",
        f"created_at: {created_at!r}",
        f"persona: {role!r}",
        "step_label: open-browser",
        "done: true",
        "---",
        "",
    ]
    artifact = sprint_dir / "open-browser-note.md"
    atomic_write_text(artifact, "\n".join(lines) + "\n")
    return artifact


def open_browser_handler(
    ctx: Any, *, role: str, args: dict[str, Any],
) -> dict[str, Any]:
    """Launch headed Chromium + inject cookies + navigate + write note artifact.

    Args
    ----
    ctx:
        Object exposing ``sprint_dir`` (Path), ``sprint_id`` (str), and
        ``team_dir`` (Path to ``<data_dir>/teams/<team>/``). All looked
        up via ``getattr`` with permissive fallbacks so tests can use a
        SimpleNamespace.
    role:
        Invoking role; written into the artifact frontmatter for
        traceability. Dispatcher guarantees role ∈ {engineer, qa,
        dx-lead, designer}; the handler does not re-validate.
    args:
        - ``url`` (str, required): http/https URL to open.
        - ``hold_seconds`` (int, default 0): Time to keep the browser
          window open before the sync_playwright context manager exits.
          Kept at 0 by default so tests don't actually block; Phase 7
          will replace with a proper "hold until /close-gstack-browser"
          loop.

    Returns
    -------
    dict
        ``artifact_path``, ``url``, ``domain``, ``cookies_loaded``
        (count of cookies injected), ``close_hint``.

    Raises
    ------
    ValueError
        On URL scheme/host validation failure (T-06-06-01).
    SkillUnavailable
        Propagated from :func:`open_headed_with_context` when Playwright
        is missing.
    """
    url_raw = args.get("url", "")
    url, domain = _validate_url(url_raw)
    hold_seconds = max(0, int(args.get("hold_seconds", 0) or 0))

    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    sprint_id = getattr(ctx, "sprint_id", "")
    team_dir = Path(getattr(ctx, "team_dir", sprint_dir))

    cookies = load_cookies_for_domain(team_dir, domain)
    sprint_dir.mkdir(parents=True, exist_ok=True)

    # Pass ``cookies=None`` when the jar is empty so the session factory
    # doesn't bother calling ``context.add_cookies([])`` — see 06-04's
    # build_browser_context contract. The session factory treats None
    # and [] equivalently, but None expresses "no cookies" more clearly
    # in logs.
    cookies_kwarg = cookies if cookies else None
    with open_headed_with_context(cookies=cookies_kwarg) as context:
        page = context.new_page()
        page.goto(url)
        if hold_seconds > 0:
            time.sleep(hold_seconds)

    artifact = _write_note(
        sprint_dir,
        url=url,
        domain=domain,
        role=role,
        sprint_id=sprint_id,
        status="opened",
    )
    return {
        "artifact_path": str(artifact),
        "url": url,
        "domain": domain,
        "cookies_loaded": len(cookies),
        "close_hint": (
            "Browser closed automatically after hold_seconds elapsed "
            "(Phase 7 will add /close-gstack-browser for persistent windows)"
        ),
    }


__all__ = ["open_browser_handler"]
