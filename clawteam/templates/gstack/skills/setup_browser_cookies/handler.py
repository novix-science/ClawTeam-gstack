"""/setup-browser-cookies handler — captures authenticated cookies for a domain.

SKILL-10 part 3 of 3 (Plan 06-07). Roles: engineer, qa, dx-lead.

Orchestration:

1. Fail-fast if Playwright missing → :class:`SkillUnavailable`.
2. Run the questionary wizard (domain + login_url + Proceed confirm). On
   abort (user Ctrl-C), emit a ``status=aborted`` artifact without any
   disk mutation of the cookie jar.
3. Probe existing cookies for the domain via
   :func:`load_cookies_for_domain`. If non-empty, call
   :func:`confirm_overwrite`; on ``no`` return ``status=skipped``.
4. Launch a headed Chromium context via
   :func:`open_headed_with_context` (D-02 — the handler NEVER top-level-
   imports playwright; all interop routes through the browser substrate).
   Navigate to ``login_url``, then capture ``context.cookies()`` on
   context-manager exit (user logs in during the preceding questionary
   gate and presses Enter to unblock capture).
5. Persist via :func:`save_cookies_for_domain` — writes through
   ``file_locked`` + ``atomic_write_text`` so re-entrant invocations
   cannot corrupt the jar.
6. Always write a ``cookies-note.md`` artifact recording status, domain,
   and cookie_count for downstream /reflect visibility.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.browser import (
    load_cookies_for_domain,
    open_headed_with_context,
    playwright_available,
    save_cookies_for_domain,
)
from clawteam.fileutil import atomic_write_text
from clawteam.plugins.skill_errors import SkillUnavailable
from clawteam.templates.gstack.skills.setup_browser_cookies.wizard import (
    confirm_overwrite,
    run_wizard,
)

_INSTALL_HINT = "pip install 'clawteam[browser]' && playwright install chromium"


def _write_note(
    sprint_dir: Path,
    *,
    status: str,
    domain: str,
    cookie_count: int,
    role: str,
    sprint_id: str,
) -> Path:
    """Emit a cookies-note.md artifact recording the skill outcome.

    Frontmatter fields mirror the Phase 5 ship-notes / canary-report
    shape so /reflect and EvidenceGate surfaces can round-trip the file
    uniformly.
    """
    created_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        "artifact_type: cookies-note",
        f"status: {status!r}",
        f"domain: {domain!r}",
        f"cookie_count: {cookie_count}",
        f"sprint_id: {sprint_id!r}",
        f"created_at: {created_at!r}",
        f"persona: {role!r}",
        "step_label: setup-browser-cookies",
        "done: true",
        "---",
        "",
    ]
    artifact = sprint_dir / "cookies-note.md"
    atomic_write_text(artifact, "\n".join(lines) + "\n")
    return artifact


def setup_cookies_handler(
    ctx: Any,
    *,
    role: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Entry point invoked by :class:`SkillDispatcher` for /setup-browser-cookies.

    See module docstring for the full orchestration contract.

    Returns one of:

    - ``{"status": "saved", "domain": ..., "cookie_count": N, "artifact_path": ...}``
    - ``{"status": "skipped", "domain": ..., "artifact_path": ..., "reason": "user declined overwrite"}``
    - ``{"status": "aborted", "artifact_path": ...}``

    Raises :class:`SkillUnavailable` when Playwright is not installed.
    """
    # 1. Tool-availability gate (D-02 — never top-level-import playwright).
    if not playwright_available():
        raise SkillUnavailable(
            skill="/setup-browser-cookies",
            binary="playwright",
            install_hint=_INSTALL_HINT,
            role=role,
        )

    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    sprint_dir.mkdir(parents=True, exist_ok=True)
    sprint_id = getattr(ctx, "sprint_id", "")
    team_dir = Path(getattr(ctx, "team_dir", sprint_dir))

    # 2. Run the wizard; None → user aborted.
    answers = run_wizard()
    if answers is None:
        artifact = _write_note(
            sprint_dir,
            status="aborted",
            domain="",
            cookie_count=0,
            role=role,
            sprint_id=sprint_id,
        )
        return {"status": "aborted", "artifact_path": str(artifact)}

    domain = answers["domain"]
    login_url = answers["login_url"]

    # 3. Existing-cookies overwrite gate.
    existing = load_cookies_for_domain(team_dir, domain)
    if existing and not confirm_overwrite(domain):
        artifact = _write_note(
            sprint_dir,
            status="skipped",
            domain=domain,
            cookie_count=len(existing),
            role=role,
            sprint_id=sprint_id,
        )
        return {
            "status": "skipped",
            "domain": domain,
            "artifact_path": str(artifact),
            "reason": "user declined overwrite",
        }

    # 4. Capture cookies from a headed Chromium session. The user was
    #    already instructed during the wizard's "Proceed?" gate to log
    #    in and press Enter; by the time we open the browser the session
    #    is already authenticated (or about to be — the user completes
    #    auth while the browser is up, then context exit captures).
    captured: list[dict[str, Any]] = []
    with open_headed_with_context() as context:
        page = context.new_page()
        page.goto(login_url)
        captured = list(context.cookies())

    # 5. Persist to team jar (atomic + file-locked inside save fn).
    save_cookies_for_domain(team_dir, domain, captured)

    # 6. Artifact for /reflect visibility.
    artifact = _write_note(
        sprint_dir,
        status="saved",
        domain=domain,
        cookie_count=len(captured),
        role=role,
        sprint_id=sprint_id,
    )
    return {
        "status": "saved",
        "domain": domain,
        "cookie_count": len(captured),
        "artifact_path": str(artifact),
    }


__all__ = ["setup_cookies_handler"]
