"""/codex skill — cross-model independent second opinion (SKILL-13).

Modes:
- review: pass/fail gate on a target (file, diff, branch).
- adversarial: red-team critique looking for failure modes.
- consultation: open-ended design/architecture question.

Dispatched via SkillDispatcher (roles={engineer, reviewer}).
"""
from clawteam.templates.gstack.skills.codex.handler import (
    codex_handler,
    invoke_codex,
    tool_available,
)

__all__ = ["codex_handler", "invoke_codex", "tool_available"]
