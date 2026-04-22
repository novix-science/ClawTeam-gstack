"""/setup-browser-cookies skill — one-time login wizard for per-domain cookies.

SKILL-10 part 3 of 3. Roles: engineer, qa, dx-lead.

Runs a questionary wizard to collect a target domain + login URL, opens
a headed Chromium window, waits for the user to authenticate, then
captures ``context.cookies()`` and persists them to the team's per-domain
cookie jar via :func:`clawteam.browser.cookies.save_cookies_for_domain`.
"""
from clawteam.templates.gstack.skills.setup_browser_cookies.handler import (
    setup_cookies_handler,
)

__all__ = ["setup_cookies_handler"]
