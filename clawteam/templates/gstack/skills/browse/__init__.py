"""/browse skill — general-purpose headless browser navigation (SKILL-10).

Roles: engineer, qa, dx-lead. Delegates to clawteam/browser/adapter.py
for Playwright work so the skill module itself never top-level-imports
playwright (D-02).
"""
from clawteam.templates.gstack.skills.browse.handler import browse_handler

__all__ = ["browse_handler"]
