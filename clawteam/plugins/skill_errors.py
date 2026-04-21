"""Structured skill-dispatch errors (Phase 5 Wave 0 substrate, Plan 05-01 Task 1).

All skill-dispatch failures share a common :class:`SkillError` base so agent
surfaces can render a single structured error payload. Subclasses carry
enough structure for each failure mode to be rendered separately (install
hint for missing tool, role-list for permission failure, etc.).

See .planning/phases/05-tool-heavy-skills-ship-sre-codex/05-RESEARCH.md
§Code Example 8 and D-04 (skill-error contract).
"""

from __future__ import annotations


class SkillError(Exception):
    """Base for all skill-dispatch failures (agent-visible, structured).

    The default rendered form is ``[<skill>] (role=<role>) <message>`` so
    logs include the triggering skill/role without the caller having to
    format them.
    """

    def __init__(self, skill: str, role: str = "", message: str = "") -> None:
        self.skill = skill
        self.role = role
        self.message = message
        super().__init__(f"[{skill}] (role={role}) {message}")


class SkillUnavailable(SkillError):
    """Raised when a required external tool is missing (D-04).

    Carries ``binary`` and ``install_hint`` so the dispatcher surface can
    render a user-facing ``doctor``-style remediation message without
    string-parsing the message.
    """

    def __init__(
        self,
        skill: str,
        binary: str,
        install_hint: str,
        role: str = "",
    ) -> None:
        self.binary = binary
        self.install_hint = install_hint
        super().__init__(
            skill=skill,
            role=role,
            message=f"tool '{binary}' not available. Install: {install_hint}",
        )


class SkillNotPermitted(SkillError):
    """Raised when an agent role invokes a skill not in its SkillRegistration.roles."""


class SkillPreconditionError(SkillError):
    """Raised when a skill invariant isn't met (e.g. /land-and-deploy before /ship)."""
