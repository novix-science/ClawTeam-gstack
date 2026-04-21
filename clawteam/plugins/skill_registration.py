"""Skill contribution type — Phase 5 substrate (Plan 05-01 Task 1).

Plugins contribute skills via :meth:`HarnessPlugin.contribute_skills` returning
a ``list[SkillRegistration]``. :meth:`PluginManager.get_plugin_skills` aggregates
them (and raises ``ValueError`` on duplicate ``name``).
:class:`clawteam.plugins.skill_dispatcher.SkillDispatcher` looks up by name,
role-gates, runs an optional tool-availability probe, and invokes the handler.

Design rationale (see .planning/phases/05-tool-heavy-skills-ship-sre-codex/05-RESEARCH.md
§Code Example 1 + §A3 adjustment):

- frozen=True makes registrations immutable so plugins cannot mutate another
  plugin's contributed skill at runtime.
- ``roles`` is a ``frozenset`` to signal set semantics (membership check in
  dispatcher) and to be hashable for future indexing.
- ``tool_available`` is optional — skills that always work (pure-Python
  handlers) can omit it; skills wrapping external CLIs (codex, gh, etc.)
  provide a probe so SkillDispatcher raises ``SkillUnavailable`` BEFORE
  invoking the handler when the binary is missing.
- ``install_hint`` mirrors the text surfaced by ``clawteam doctor`` so agents
  see the same remediation in both surfaces.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class SkillRegistration:
    """One skill contribution from a :class:`HarnessPlugin`.

    Attributes
    ----------
    name:
        Slash-command name as agents invoke it, e.g. ``"/codex"``.
    roles:
        Frozen set of agent roles permitted to invoke this skill. The
        dispatcher raises :class:`SkillNotPermitted` when a caller's role is
        not a member.
    handler:
        Callable invoked on successful dispatch. Signature is
        ``handler(ctx, *, role: str, args: dict) -> Any``; the return value
        flows back through :meth:`SkillDispatcher.dispatch`.
    tool_available:
        Optional no-arg callable returning ``bool``. When provided and
        returning ``False`` at dispatch time, :class:`SkillUnavailable` is
        raised with ``install_hint`` before the handler runs.
    install_hint:
        Text shown in :class:`SkillUnavailable` (should match the string
        ``clawteam doctor`` prints for the same binary).
    """

    name: str
    roles: frozenset[str]
    handler: Callable[..., Any]
    tool_available: Callable[[], bool] | None = None
    install_hint: str = ""
