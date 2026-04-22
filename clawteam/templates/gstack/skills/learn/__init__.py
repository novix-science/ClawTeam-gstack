"""/learn skill — role-agnostic memory write/read/search/prune (MEM-04, D-07).

The handler is role-agnostic: any :data:`GSTACK_ROLES` agent can invoke
``/learn`` to write, list, search, or prune team memory. Scope=team entries
land in ``<data>/teams/<team>/memory/team/YYYY-MM.jsonl``; scope=role
entries land in ``<data>/teams/<team>/memory/agents/<role>/YYYY-MM.jsonl``.

All mutation goes through :class:`TeamMemoryStore`; search is delegated to
:func:`clawteam.memory.search.search`. High-impact gating + conflict
detection + backfill instrumentation live in Plan 06-11 which wraps this
handler's write path.
"""
from clawteam.templates.gstack.skills.learn.handler import learn_handler

__all__ = ["learn_handler"]
