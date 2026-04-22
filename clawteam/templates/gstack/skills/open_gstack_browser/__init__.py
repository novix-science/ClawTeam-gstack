"""/open-gstack-browser skill — headed Chromium for human UI interaction (SKILL-10).

Phase 6 Plan 06-06 Wave 2. Sibling of /browse (Plan 06-05 — one-shot
headless screenshot) and /setup-browser-cookies (Plan 06-07 — cookie-jar
wizard). Where /browse automates page capture for the agent, this skill
hands a live Chromium window to a human (designer / engineer / qa /
dx-lead) with the team's cookie jar pre-loaded so they can see the live
UI authenticated.
"""
from clawteam.templates.gstack.skills.open_gstack_browser.handler import (
    open_browser_handler,
)

__all__ = ["open_browser_handler"]
