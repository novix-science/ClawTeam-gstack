"""TeamMemoryStore — append-only JSONL team memory (D-04, D-05).

Public API:

- ``TeamMemoryStore(team_name)`` — per-team store instance.
- ``.write(entry)`` — append entry to its month bucket; returns entry.id.
- ``.list(scope, tag=None, role=None)`` — read entries under scope;
  tombstone-suppressed; tag-filtered when tag is given.
- ``.prune(entry_id, scope, role=None)`` — append tombstone record.
- ``.bucket_path(entry)`` — exposed for plan 06-11 high-impact staging.

Search + ranking + conflict detection + high-impact gate + backfill are
implemented in separate modules (plans 06-03, 06-11) that import this class.

Per-team isolation is enforced by ``validate_identifier`` at construction and
``ensure_within_root`` on every path-forming helper — paths that resolve
outside ``<data_dir>/teams/<team>/memory`` raise ``ValueError`` before any
filesystem access.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from clawteam.fileutil import file_locked
from clawteam.memory.entry import MemoryEntry
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir


class TeamMemoryStore:
    """Per-team append-only JSONL memory store (D-04)."""

    MEMORY_ROOT_NAME = "memory"

    def __init__(self, team_name: str) -> None:
        # Identifier validation rejects '/', '..', '\\' at construction — no
        # filesystem access happens before this gate.
        validate_identifier(team_name, "team name")
        self.team_name = team_name
        self._root = (
            get_data_dir() / "teams" / team_name / self.MEMORY_ROOT_NAME
        )

    # ── Path helpers ───────────────────────────────────────────────────

    def _team_dir(self) -> Path:
        return ensure_within_root(self._root, "team")

    def _role_dir(self, role: str) -> Path:
        validate_identifier(role, "role")
        return ensure_within_root(self._root, "agents", role)

    def bucket_path(self, entry: MemoryEntry) -> Path:
        """Resolve the JSONL bucket for an entry.

        Public for Plan 06-11 pending stager.
        """
        bucket_key = entry.timestamp[:7]  # YYYY-MM
        if not re.fullmatch(r"\d{4}-\d{2}", bucket_key):
            raise ValueError(
                f"invalid timestamp prefix for bucket: {bucket_key!r}"
            )
        if entry.scope == "team":
            return ensure_within_root(self._root, "team", f"{bucket_key}.jsonl")
        assert entry.role is not None  # guaranteed by MemoryEntry validator
        validate_identifier(entry.role, "role")
        return ensure_within_root(
            self._root, "agents", entry.role, f"{bucket_key}.jsonl"
        )

    # ── ID generation ──────────────────────────────────────────────────

    def gen_id(self, *, author: str, title: str, tags: Iterable[str]) -> str:
        """Generate a unique ``mem-<team>-<YYYYMMDD>-<6hex>`` id."""
        payload = (
            f"{author}|{title}|{','.join(sorted(tags))}|"
            f"{datetime.now(timezone.utc).isoformat()}"
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:6]
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        slug = re.sub(r"[^a-zA-Z0-9_-]", "", self.team_name)[:24] or "team"
        return f"mem-{slug}-{today}-{digest}"

    # ── Write + prune ──────────────────────────────────────────────────

    def write(self, entry: MemoryEntry) -> str:
        """Append entry to its month-bucketed JSONL (D-05). Returns ``entry.id``.

        Uses ``file_locked`` + ``open('a') + flush + fsync`` for crash-safety
        (A5 inlined — no dedicated atomic_append_line helper exists in
        fileutil.py today).
        """
        bucket = self.bucket_path(entry)
        bucket.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(entry.model_dump(), ensure_ascii=False) + "\n"
        with file_locked(bucket):
            with bucket.open("a", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except OSError:
                    # tmpfs / network fs / Windows quirks — best-effort.
                    pass
        return entry.id

    def prune(
        self,
        entry_id: str,
        *,
        scope: Literal["team", "role"] = "team",
        role: str | None = None,
        actor: str = "system@prune",
    ) -> None:
        """Append tombstone record; never mutate prior history (D-05).

        Tombstone BYPASSES the high-impact gate (research Open Question 3) —
        pruning is always immediate. Original entry still present in JSONL;
        :meth:`list` suppresses it via the tombstoned-id set.
        """
        tombstone = MemoryEntry(
            id=entry_id,
            author=actor,
            title=f"tombstone for {entry_id}",
            body="",
            tags=["tombstone"],
            evidence="",
            confidence=1.0,
            learned_from="user",
            scope=scope,
            role=role if scope == "role" else None,
            op="prune",
        )
        self.write(tombstone)

    # ── Read + list ────────────────────────────────────────────────────

    def _iter_jsonl(self, path: Path) -> list[dict]:
        if not path.is_file():
            return []
        out: list[dict] = []
        with path.open("r", encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    # Defensively skip malformed lines rather than crash the
                    # whole listing (T-06-02-04 mitigation).
                    continue
        return out

    def _scope_dir(
        self, scope: Literal["team", "role"], role: str | None
    ) -> Path:
        if scope == "team":
            return self._team_dir()
        if role is None:
            raise ValueError("scope='role' requires role argument")
        return self._role_dir(role)

    def list(
        self,
        scope: Literal["team", "role"] = "team",
        *,
        tag: str | None = None,
        role: str | None = None,
    ) -> list[MemoryEntry]:
        """Return tombstone-suppressed entries under *scope*, optionally tag-filtered."""
        scope_dir = self._scope_dir(scope, role)
        if not scope_dir.is_dir():
            return []

        tombstoned: set[str] = set()
        candidates: list[MemoryEntry] = []
        for bucket in sorted(scope_dir.glob("*.jsonl")):
            for raw in self._iter_jsonl(bucket):
                try:
                    entry = MemoryEntry(**raw)
                except Exception:
                    continue
                if entry.op == "prune":
                    tombstoned.add(entry.id)
                    continue
                if tag is not None and tag not in entry.tags:
                    continue
                candidates.append(entry)
        return [e for e in candidates if e.id not in tombstoned]


__all__ = ["TeamMemoryStore"]
