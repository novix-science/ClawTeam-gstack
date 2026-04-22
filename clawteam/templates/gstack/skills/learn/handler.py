"""/learn handler — role-agnostic memory ops (MEM-04, D-07, D-08).

Actions (dispatched via ``args['action']``):

* ``write``   — construct a :class:`MemoryEntry`, persist via
  :meth:`TeamMemoryStore.write`. Empty evidence is FLAGGED (MEM-05) but
  never blocked. High-impact entries (``impact=="high"`` OR tag-derived
  critical path) are marked in the result for the (Plan 06-11) gate to
  interpose. Returns ``{"status": "written", "id": <mem-id>,
  "evidence_flagged": bool, "high_impact": bool}``.
* ``list``    — enumerate entries under a scope (team or role), optional
  tag filter. Tombstoned ids are suppressed inside
  :meth:`TeamMemoryStore.list`. Returns ``{"status": "listed", "entries":
  [entry.model_dump(), ...]}``.
* ``search``  — keyword retrieval via :func:`clawteam.memory.search.search`
  ranked by recency × provenance × decay. When ``args['explain']`` is
  true, each result exposes its three component factors for Plan 06-10's
  ``--explain`` CLI flag. Returns ``{"status": "searched", "query": str,
  "results": [...]}``.
* ``prune``   — append a tombstone via :meth:`TeamMemoryStore.prune`.
  Bypasses the (future) high-impact gate per research Open Question 3;
  the tombstone IS the undo. Returns ``{"status": "pruned", "id": str}``.

The handler is ROLE-AGNOSTIC: :class:`SkillRegistration.roles` is
``frozenset(GSTACK_ROLES)`` at the plugin layer (D-07). This function
itself does not gate on ``role`` — the role parameter is only used to
derive the default ``author`` field when the caller does not supply one.
"""
from __future__ import annotations

from typing import Any

from clawteam.memory import MemoryEntry, TeamMemoryStore
from clawteam.memory.search import search as memory_search

_VALID_ACTIONS = frozenset({"write", "list", "search", "prune"})
_VALID_IMPACT = frozenset({"low", "medium", "high"})


def _resolve_team_name(ctx: Any) -> str:
    """Extract team name from ctx; default to ``"default"`` when absent."""
    return getattr(ctx, "team_name", "") or "default"


def _normalise_tags(raw: Any) -> list[str]:
    """Accept tags as list[str] or comma-separated string; return list[str]."""
    if raw is None:
        return []
    if isinstance(raw, str):
        return [t.strip() for t in raw.split(",") if t.strip()]
    return [str(t) for t in raw]


def _build_entry(
    store: TeamMemoryStore, *, role: str, args: dict[str, Any]
) -> MemoryEntry:
    """Construct a MemoryEntry from /learn args.

    Sets ``author`` to ``<role>@learn`` when the caller does not override;
    normalizes tags (string → list); appends ``impact:high`` to tags when
    ``impact == "high"`` so downstream readers (Plan 06-11 gate) can grep
    a single tag rather than also checking a separate impact field.
    """
    scope = args.get("scope", "team")
    entry_role = args.get("role") if scope == "role" else None
    author = args.get("author") or f"{role}@learn"

    title = args.get("title")
    if not title:
        raise ValueError("title is required for learn write")
    body = args.get("body", "") or ""

    tags = _normalise_tags(args.get("tags"))

    impact = args.get("impact", "medium")
    if impact not in _VALID_IMPACT:
        raise ValueError(
            f"invalid impact {impact!r}; must be one of {sorted(_VALID_IMPACT)}"
        )
    if impact == "high" and "impact:high" not in tags:
        tags.append("impact:high")

    evidence = args.get("evidence", "") or ""
    confidence = float(args.get("confidence", 0.7))
    learned_from = args.get("learned_from", "artifact")
    sprint_id = args.get("sprint_id", "") or ""
    phase = args.get("phase", "") or ""

    entry_id = store.gen_id(author=author, title=title, tags=tags)
    return MemoryEntry(
        id=entry_id,
        author=author,
        sprint_id=sprint_id,
        phase=phase,
        title=title,
        body=body,
        tags=tags,
        evidence=evidence,
        confidence=confidence,
        learned_from=learned_from,
        scope=scope,
        role=entry_role,
    )


def _do_write(
    store: TeamMemoryStore, *, role: str, args: dict[str, Any]
) -> dict[str, Any]:
    entry = _build_entry(store, role=role, args=args)
    entry_id = store.write(entry)
    return {
        "status": "written",
        "id": entry_id,
        "evidence_flagged": not bool(entry.evidence),
        "high_impact": "impact:high" in entry.tags,
    }


def _do_list(
    store: TeamMemoryStore, *, args: dict[str, Any]
) -> dict[str, Any]:
    scope = args.get("scope", "team")
    tag = args.get("tag")
    role_arg = args.get("role") if scope == "role" else None
    entries = store.list(scope=scope, tag=tag, role=role_arg)
    return {
        "status": "listed",
        "entries": [e.model_dump() for e in entries],
    }


def _do_search(
    store: TeamMemoryStore, *, args: dict[str, Any]
) -> dict[str, Any]:
    query = args.get("query", "") or ""
    scope = args.get("scope", "team")
    tag = args.get("tag")
    role_arg = args.get("role") if scope == "role" else None

    results = memory_search(store, query, scope=scope, tag=tag, role=role_arg)
    explain = bool(args.get("explain"))

    payload: list[dict[str, Any]] = []
    for r in results:
        item: dict[str, Any] = {
            "id": r.entry.id,
            "title": r.entry.title,
            "tags": list(r.entry.tags),
            "score": round(r.score, 4),
        }
        if explain:
            item["recency"] = round(r.recency, 4)
            item["provenance"] = round(r.provenance, 4)
            item["decay"] = round(r.decay, 4)
        payload.append(item)

    return {
        "status": "searched",
        "query": query,
        "results": payload,
    }


def _do_prune(
    store: TeamMemoryStore, *, args: dict[str, Any]
) -> dict[str, Any]:
    entry_id = args.get("id")
    if not entry_id:
        raise ValueError("prune requires 'id'")
    scope = args.get("scope", "team")
    role_arg = args.get("role") if scope == "role" else None
    store.prune(entry_id, scope=scope, role=role_arg)
    return {"status": "pruned", "id": entry_id}


def learn_handler(
    ctx: Any, *, role: str, args: dict[str, Any]
) -> dict[str, Any]:
    """/learn entry point invoked via :class:`SkillDispatcher`.

    Role-agnostic (D-07). The ``role`` parameter is passed through to the
    default ``author`` field but no role-gating happens here; the plugin
    layer's ``roles=frozenset(GSTACK_ROLES)`` is the single enforcement
    point.
    """
    if not isinstance(args, dict):
        raise ValueError("args must be a dict")
    action = args.get("action", "")
    if action not in _VALID_ACTIONS:
        raise ValueError(
            f"unknown action {action!r}; must be one of {sorted(_VALID_ACTIONS)}"
        )

    team_name = _resolve_team_name(ctx)
    store = TeamMemoryStore(team_name)

    if action == "write":
        return _do_write(store, role=role, args=args)
    if action == "list":
        return _do_list(store, args=args)
    if action == "search":
        return _do_search(store, args=args)
    if action == "prune":
        return _do_prune(store, args=args)

    # Unreachable — _VALID_ACTIONS is exhaustive.
    raise ValueError(f"unreachable action {action!r}")


__all__ = ["learn_handler"]
