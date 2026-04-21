"""Synchronous skill dispatch entry point (Phase 5 Wave 0 substrate).

Given a mapping ``{skill_name: SkillRegistration}`` (typically produced by
:meth:`clawteam.plugins.manager.PluginManager.get_plugin_skills`),
:class:`SkillDispatcher` resolves a ``skill_name``, role-gates the call,
probes tool availability, and invokes the handler.

Open Question 1 (05-RESEARCH §Deferred): the agent-to-dispatcher wire-up
(MCP tool call or TurnEnvelope slash-command parser) is deferred to Phase 7.
For Phase 5 tests (and Wave 2+ skill implementations), ``dispatch()`` is
called directly.
"""

from __future__ import annotations

from typing import Any, Mapping

from clawteam.plugins.skill_errors import (
    SkillError,
    SkillNotPermitted,
    SkillUnavailable,
)
from clawteam.plugins.skill_registration import SkillRegistration


class SkillDispatcher:
    """Looks up a :class:`SkillRegistration` by name, checks role + tool, invokes handler."""

    def __init__(self, registrations: Mapping[str, SkillRegistration]) -> None:
        # Defensive copy: the dispatcher should not observe later mutations
        # to the registry passed at construction time.
        self._registrations: dict[str, SkillRegistration] = dict(registrations)

    def dispatch(
        self,
        ctx: Any,
        *,
        skill_name: str,
        role: str,
        args: dict[str, Any] | None = None,
    ) -> Any:
        """Role-gate, tool-probe, and invoke the handler for ``skill_name``.

        Raises
        ------
        SkillError
            When ``skill_name`` is not registered (message contains the
            literal string ``"unknown skill"`` so callers can discriminate
            without isinstance checks).
        SkillNotPermitted
            When ``role`` is not a member of ``registration.roles``.
        SkillUnavailable
            When ``registration.tool_available()`` returns ``False``.
        """
        reg = self._registrations.get(skill_name)
        if reg is None:
            raise SkillError(
                skill=skill_name,
                role=role,
                message=f"unknown skill {skill_name!r}",
            )
        if role not in reg.roles:
            raise SkillNotPermitted(
                skill=skill_name,
                role=role,
                message=(
                    f"role '{role}' not in permitted roles "
                    f"{sorted(reg.roles)}"
                ),
            )
        if reg.tool_available is not None and not reg.tool_available():
            # binary name defaults to the skill name with the leading '/' stripped;
            # that matches how clawteam doctor names the binary (codex, gh, etc.).
            raise SkillUnavailable(
                skill=skill_name,
                binary=skill_name.lstrip("/"),
                install_hint=reg.install_hint,
                role=role,
            )
        return reg.handler(ctx, role=role, args=dict(args or {}))
