"""/design-html skill — production HTML emission with framework detection (SKILL-12).

Phase 6 Plan 06-09 (Cluster B — design pipeline).

The skill is invoked by the designer role after /design-shotgun converges on a
chosen mockup variant. It reads the variant HTML, detects the project frontend
framework from ``package.json`` (React / Svelte / Vue / plain), and emits a
single framework-appropriate source file (React → ``*.jsx``, Svelte → ``*.svelte``,
Vue → ``*.vue``) OR a plain-HTML triple (``index.html`` + ``styles.css`` + ``app.js``)
at the detected source root.

Ambiguous projects (multiple frontend frameworks in the same ``package.json``)
do not guess: the handler writes a ``questions/design-html-framework-*.md``
artifact asking the user which framework to target, and returns
``status="awaiting_user"``.
"""
from clawteam.templates.gstack.skills.design_html.framework_detect import (
    FrameworkDetection,
    detect_framework,
)
from clawteam.templates.gstack.skills.design_html.handler import (
    design_html_handler,
)

__all__ = [
    "FrameworkDetection",
    "detect_framework",
    "design_html_handler",
]
