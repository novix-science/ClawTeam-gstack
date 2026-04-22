"""/browse handler (SKILL-10; Plan 06-05, D-01/D-02/D-16).

Thin UX over :mod:`clawteam.browser.adapter`. Writes a ``browse-result.md``
artifact with ``dom_hash`` + ``http_status`` frontmatter and co-locates a
``browse-screenshot-<hash8>.png`` file in the sprint directory.

D-02 invariant: Playwright is NEVER top-level-imported here. All browser
entry points come through :mod:`clawteam.browser`, which itself lazy-imports
``playwright.sync_api`` inside function bodies only. An accidental
``from playwright.sync_api import ...`` at the top of this module would
break the ``clawteam[browser]`` extra contract (Pitfall 5).

URL scheme allow-list: only ``http`` and ``https`` are accepted. ``file://``,
``javascript:``, ``data:`` and anything else raise :class:`ValueError`
BEFORE any browser launch so a hostile prompt can never cross the boundary
from "agent provides a string" to "Chromium opens a file URL". This is the
T-06-05-01 mitigation.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from clawteam.browser import action_script, navigate_and_screenshot
from clawteam.fileutil import atomic_write_text

_ALLOWED_SCHEMES: frozenset[str] = frozenset({"http", "https"})


def _validate_url(url: str) -> None:
    """Reject non-http(s) URLs BEFORE any browser launch (T-06-05-01).

    Empty/non-string inputs, unknown schemes, and scheme-only (no host) URLs
    all raise :class:`ValueError`. The allow-list intentionally forbids
    ``file://`` (local file read), ``javascript:`` (arbitrary JS execution),
    and ``data:`` (embedded payload) — these are the three most common
    attacker-controlled vectors when an agent forwards a user string directly
    to a headless browser.
    """
    if not isinstance(url, str) or not url:
        raise ValueError("url must be a non-empty string")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"url scheme {parsed.scheme!r} not allowed; only http(s) accepted"
        )
    if not parsed.netloc:
        raise ValueError(f"url {url!r} has no host")


def _format_fm_value(val: Any) -> str:
    """Render a single frontmatter value consistent with peer skills.

    Bools → ``true``/``false``. Strings → single-quoted (embedded apostrophes
    doubled per YAML). Ints → bare. Matches the hand-rolled emitter used by
    the Phase 5 /codex + /canary handlers so all gstack artifacts share a
    parseable shape without a pyyaml dep.
    """
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, str):
        escaped = val.replace("'", "''")
        return f"'{escaped}'"
    return str(val)


def _write_artifact(
    sprint_dir: Path,
    *,
    url: str,
    dom_hash: str,
    http_status: int,
    screenshot_rel_path: str,
    action_count: int,
    role: str,
    sprint_id: str,
) -> Path:
    """Atomic-write ``<sprint_dir>/browse-result.md`` with yaml frontmatter."""
    created_at = datetime.now(timezone.utc).isoformat()
    fields: list[tuple[str, Any]] = [
        ("artifact_type", "browse-result"),
        ("url", url),
        ("http_status", int(http_status)),
        ("dom_hash", dom_hash),
        ("screenshot_path", screenshot_rel_path),
        ("action_count", int(action_count)),
        ("sprint_id", sprint_id),
        ("created_at", created_at),
        ("persona", role),
        ("step_label", "browse"),
        ("done", True),
    ]
    lines = ["---"]
    for key, val in fields:
        lines.append(f"{key}: {_format_fm_value(val)}")
    lines.append("---")
    lines.append("")

    sprint_dir.mkdir(parents=True, exist_ok=True)
    artifact = sprint_dir / "browse-result.md"
    atomic_write_text(artifact, "\n".join(lines) + "\n")
    return artifact


def browse_handler(
    ctx: Any, *, role: str, args: dict[str, Any]
) -> dict[str, Any]:
    """Entry point invoked via :class:`SkillDispatcher`.

    Parameters
    ----------
    ctx:
        Harness context. Consumed attributes (all optional for robustness in
        direct-call tests): ``sprint_dir`` (Path), ``sprint_id`` (str).
    role:
        Caller's role. Dispatcher enforces ``role in {engineer,qa,dx-lead}``
        before reaching here; the value is recorded in the artifact as
        ``persona``.
    args:
        * ``url`` (str, required) — target page. Validated against the
          http/https allow-list BEFORE any browser launch.
        * ``actions`` (list[dict], optional) — when non-empty, delegates to
          :func:`clawteam.browser.action_script` instead of
          :func:`navigate_and_screenshot`.

    Returns
    -------
    dict
        ``{artifact_path, http_status, dom_hash, screenshot_path, action_count}``.

    Raises
    ------
    ValueError
        URL scheme not in the http(s) allow-list (T-06-05-01).
    SkillUnavailable
        Propagated from the adapter when Playwright is not installed.
    """
    url = args.get("url", "")
    _validate_url(url)
    actions = args.get("actions") or []

    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    sprint_dir.mkdir(parents=True, exist_ok=True)
    sprint_id = getattr(ctx, "sprint_id", "") or ""

    if actions:
        result = action_script(url, actions)
        # action_script doesn't guarantee a DOM hash; record "n/a" so the
        # artifact schema stays a fixed shape.
        dom_hash = "n/a"
        http_status = int(result.get("http_status", 0))
        screenshots = result.get("screenshots", []) or []
        png_bytes = screenshots[0] if screenshots else b""
        action_count = int(result.get("action_count", 0))
    else:
        dom_hash, http_status, png_bytes = navigate_and_screenshot(url)
        action_count = 0

    # Co-locate the screenshot with the artifact under a content-derived name
    # so repeated runs are idempotent-ish (same content ⇒ same filename).
    if png_bytes:
        digest = hashlib.sha256(png_bytes).hexdigest()[:8]
        screenshot_name = f"browse-screenshot-{digest}.png"
        (sprint_dir / screenshot_name).write_bytes(png_bytes)
        screenshot_rel = screenshot_name
    else:
        screenshot_rel = ""

    artifact = _write_artifact(
        sprint_dir,
        url=url,
        dom_hash=dom_hash,
        http_status=int(http_status),
        screenshot_rel_path=screenshot_rel,
        action_count=action_count,
        role=role,
        sprint_id=sprint_id,
    )

    return {
        "artifact_path": str(artifact),
        "http_status": int(http_status),
        "dom_hash": dom_hash,
        "screenshot_path": screenshot_rel,
        "action_count": action_count,
    }
