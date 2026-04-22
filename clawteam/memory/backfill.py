"""Phase 3 D-09 → Phase 6 D-11 backfill scanner (Plan 06-11 Task 3).

The Reflect-phase handler in ``gstack_sprint_plugin._write_phase6_pending``
drops retro JSON into ``<data_dir>/teams/<team>/_phase6_pending/``. Those
files pre-date the Phase 6 /learn substrate and need promoting into the
proper ``memory/team/<YYYY-MM>.jsonl`` append log once the substrate is
live.

:func:`backfill_scan` is the promotion primitive:

* Walks every ``*.json`` under ``_phase6_pending/``.
* For each unprocessed entry, constructs a :class:`MemoryEntry`
  (``tags=["retro","phase-reflect"]``, ``scope="team"``,
  ``learned_from="artifact"``, ``confidence=0.8`` by default) and writes
  it via :meth:`TeamMemoryStore.write`.
* Marks each successfully-promoted file with a sibling
  ``.processed/<stem>.processed`` sentinel so re-runs are idempotent.
* Returns the count of NEW promotions for logging / event payload.

Malformed JSON is skipped silently — the scanner is best-effort so it
never blocks the /learn entry path. Exceptions from
:meth:`TeamMemoryStore.write` (bad identifier, paths outside data dir)
are also swallowed so a single poisoned file does not abort the scan.

:func:`backfill_scan` is invoked once-per-process-per-team by
``learn_handler`` via the module-level ``_backfilled_teams`` sentinel
(wire-up lives in ``templates/gstack/skills/learn/handler.py``).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from clawteam.memory.entry import MemoryEntry
from clawteam.memory.store import TeamMemoryStore

_PENDING_DIR_NAME = "_phase6_pending"
_SENTINEL_DIR_NAME = ".processed"


def _gen_retro_entry_id(store: TeamMemoryStore, stem: str) -> str:
    """Delegate id generation to the store so the mem-<team>-<YYYYMMDD>-<hex>
    pattern matches across the whole substrate. ``stem`` enriches the hash
    input so two retros written in the same second get distinct ids.
    """
    return store.gen_id(
        author=f"reflect@{stem}",
        title=f"retro-{stem}",
        tags=["retro", "phase-reflect"],
    )


def backfill_scan(*, team: str, root: Path) -> int:
    """Promote every unprocessed ``_phase6_pending/*.json`` to memory/team/.

    Returns count of entries newly promoted during this call (0 when the
    pending directory is absent or every file is sentineled).
    """
    pending_dir = root / "teams" / team / _PENDING_DIR_NAME
    if not pending_dir.exists():
        return 0

    sentinel_dir = pending_dir / _SENTINEL_DIR_NAME
    sentinel_dir.mkdir(exist_ok=True)

    store = TeamMemoryStore(team)

    promoted = 0
    for retro_path in sorted(pending_dir.glob("*.json")):
        sentinel = sentinel_dir / f"{retro_path.stem}.processed"
        if sentinel.exists():
            continue

        try:
            data = json.loads(retro_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # Malformed or unreadable — skip silently, do NOT sentinel (so
            # a later fix + rerun can still promote it).
            continue

        if not isinstance(data, dict):
            continue

        sprint_id = (
            data.get("sprint_id") or retro_path.stem.replace("-retro", "")
        )
        body = data.get("retro_body") or data.get("body") or ""
        if not body:
            # Fallback: serialize the payload so we always have SOMETHING
            # to record (MEM-05 flags empty evidence elsewhere).
            body = json.dumps(data, ensure_ascii=False)[:2000]

        timestamp = data.get("written_at") or datetime.now(
            timezone.utc
        ).isoformat()

        try:
            entry = MemoryEntry(
                id=_gen_retro_entry_id(store, retro_path.stem),
                author=f"reflect@{sprint_id}",
                sprint_id=str(sprint_id),
                phase="reflect",
                timestamp=timestamp,
                title=f"retro: {sprint_id}",
                body=body,
                tags=["retro", "phase-reflect"],
                evidence=f"_phase6_pending/{retro_path.name}",
                confidence=0.8,
                learned_from="artifact",
                scope="team",
                role=None,
                op="write",
            )
            store.write(entry)
        except Exception:
            # Bad data / path escape / validation error — skip + continue.
            continue

        sentinel.write_text("processed", encoding="utf-8")
        promoted += 1

    return promoted


__all__ = ["backfill_scan"]
