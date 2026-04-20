"""FreezeRegistry singleton — sprint-scoped path write-locks with file-locked JSON persistence + append-only audit JSONL.

§02-CONTEXT D-11 / D-12 / D-13. Structural twin of clawteam.harness.phase_registry.PhaseRegistry
(§02-CONTEXT specifics lesson #3). JSONL audit pattern mirrors clawteam.harness.exit_journal.

This module SHIPS the registry only. Plan 02-10 ships the EventBus subscribers that call
``is_frozen()`` on ``BeforeFileWrite`` / ``BeforeToolCall`` events and set ``event.veto = True``.

Invariants
----------
* **Pitfall #5 (HARD-LOCK):** ``is_frozen(path)`` returns ``(False, "")`` for any path
  under ``get_data_dir()``. Sprint-internal writes (``state.json``, ``freeze.json``,
  ``answers/``) must never be vetoed, otherwise ``clawteam sprint pause`` deadlocks
  writing its own checkpoint after a user types ``/freeze /``.

* **T-02-02 mitigation:** ``is_frozen`` canonicalizes both the stored path AND the
  query path via ``Path.resolve(strict=False)``. Symlinks resolve to real paths;
  ``..`` segments collapse. Relative-path bypass + symlink-into-frozen-dir bypass
  are both defeated.

* **SAFETY-04 audit:** Every ``freeze`` / ``unfreeze`` / ``freeze_glob`` call
  appends one JSON line to ``freeze_audit.jsonl`` in the sprint dir. Never
  rewrites; mirrors ``exit_journal.py::record_exit``.

* **QUALITY-06 persistence:** ``freeze.json`` is written via ``file_locked`` +
  ``atomic_write_text``. Concurrent writers serialize (last-write-wins); no
  torn writes; no stray ``.tmp`` files.
"""

from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.team.models import get_data_dir


class FrozenPathError(ValueError):
    """Raised when an agent write / tool-call is vetoed by FreezeRegistry.

    Subclasses ``ValueError`` so ``clawteam.mcp.helpers.translate_error`` auto-wraps
    it into an MCPToolError (§02-CONTEXT D-12). Message shape:

        "<path> is /freeze-locked by <who_froze>; unfreeze via /unfreeze <path>"
    """


def _canonicalize(path_str_or_path: str | Path) -> str:
    """Return the canonical absolute path string for freeze.json storage / comparison.

    Uses ``Path.resolve(strict=False)`` so the path is canonicalized even when it
    does not yet exist (which happens during freeze-before-create or freeze-for-dir
    patterns). ``strict=False`` prevents ``FileNotFoundError`` from aborting the
    freeze call — the invariant is "treat as if the path were to exist".
    """
    return str(Path(path_str_or_path).resolve(strict=False))


class FreezeRegistry:
    """Sprint-scoped registry of frozen paths + append-only audit log.

    One instance per ``(team, sprint_id)``. State persists in
    ``$CLAWTEAM_DATA_DIR/teams/<team>/sprints/<sprint>/freeze.json`` and every
    mutation is audited to ``freeze_audit.jsonl`` in the same directory.
    """

    def __init__(self, team_name: str, sprint_id: str) -> None:
        self._team = team_name
        self._sprint = sprint_id
        self._lock = RLock()
        self._frozen_paths: dict[str, set[str]] = {}  # agent -> set[canonical path]
        self._frozen_globs: set[str] = set()
        self._load()

    # ── Path helpers ─────────────────────────────────────────────────

    def _sprint_dir(self) -> Path:
        return get_data_dir() / "teams" / self._team / "sprints" / self._sprint

    def _freeze_path(self) -> Path:
        return self._sprint_dir() / "freeze.json"

    def _audit_path(self) -> Path:
        return self._sprint_dir() / "freeze_audit.jsonl"

    # ── Persistence ──────────────────────────────────────────────────

    def _load(self) -> None:
        p = self._freeze_path()
        if not p.exists():
            return
        with file_locked(p):
            data = json.loads(p.read_text(encoding="utf-8"))
        self._frozen_paths = {k: set(v) for k, v in data.get("paths", {}).items()}
        self._frozen_globs = set(data.get("globs", []))

    def _save(self) -> None:
        p = self._freeze_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "paths": {k: sorted(v) for k, v in self._frozen_paths.items()},
            "globs": sorted(self._frozen_globs),
        }
        with file_locked(p):
            atomic_write_text(p, json.dumps(payload, indent=2, ensure_ascii=False))

    # ── Query ────────────────────────────────────────────────────────

    def is_frozen(self, path: str | Path) -> tuple[bool, str]:
        """Return ``(is_frozen, reason)`` for ``path``.

        Pitfall #5 invariant: paths under ``get_data_dir()`` always return
        ``(False, "")``. T-02-02 mitigation: both stored and query paths are
        canonicalized via ``Path.resolve(strict=False)`` before comparison.
        """
        data_dir = get_data_dir().resolve(strict=False)
        resolved = Path(path).resolve(strict=False)
        try:
            resolved.relative_to(data_dir)
            return False, ""  # sprint-internal writes always allowed (Pitfall #5)
        except ValueError:
            pass

        path_str = str(resolved)
        with self._lock:
            for agent, paths in self._frozen_paths.items():
                for frozen in paths:
                    if path_str == frozen or path_str.startswith(frozen + "/"):
                        return True, (
                            f"{path_str} is /freeze-locked by {agent}; "
                            f"unfreeze via /unfreeze {frozen}"
                        )
            for glob in self._frozen_globs:
                if fnmatch.fnmatch(path_str, glob):
                    return True, f"{path_str} matches frozen glob {glob}"
        return False, ""

    # ── Mutations ────────────────────────────────────────────────────

    def freeze(self, path: str, *, agent: str, reason: str, actor: str) -> None:
        """Add ``path`` (canonicalized) to ``agent``'s frozen set. Persists + audits."""
        canonical = _canonicalize(path)
        with self._lock:
            self._frozen_paths.setdefault(agent, set()).add(canonical)
            self._save()
        self._audit("freeze", canonical, agent, reason, actor)

    def unfreeze(self, path: str, *, agent: str, reason: str, actor: str) -> None:
        """Remove ``path`` (canonicalized) from ``agent``'s frozen set. Persists + audits."""
        canonical = _canonicalize(path)
        with self._lock:
            if agent in self._frozen_paths:
                self._frozen_paths[agent].discard(canonical)
                self._save()
        self._audit("unfreeze", canonical, agent, reason, actor)

    def freeze_glob(self, pattern: str, *, actor: str, reason: str) -> None:
        """Add a fnmatch glob pattern to the sprint-scoped frozen-globs set."""
        with self._lock:
            self._frozen_globs.add(pattern)
            self._save()
        self._audit("freeze_glob", pattern, "*", reason, actor)

    # ── Audit ────────────────────────────────────────────────────────

    def _audit(self, action: str, path: str, agent: str, reason: str, actor: str) -> None:
        """Append one JSON entry to freeze_audit.jsonl (SAFETY-04).

        Mirrors ``clawteam.harness.exit_journal.FileExitJournal.record_exit`` verbatim:
        ``open(..., "a")`` + one ``json.dumps(entry) + "\\n"`` per call. Never use
        ``atomic_write_text`` for this file — the append-only invariant is the whole
        point (last-write-wins would lose audit history).
        """
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "path": path,
            "agent": agent,
            "reason": reason,
            "actor": actor,
            "sprint_id": self._sprint,
        }
        ap = self._audit_path()
        ap.parent.mkdir(parents=True, exist_ok=True)
        with open(ap, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Module-level singleton ──────────────────────────────────────────
# Mirrors clawteam.harness.phase_registry._REGISTRY + get_registry / reset_registry pair.

_registry: FreezeRegistry | None = None


def get_freeze_registry(
    team: str | None = None, sprint_id: str | None = None
) -> FreezeRegistry | None:
    """Module-level singleton accessor.

    Returns the current sprint-scoped registry, instantiating it lazily when called
    with ``team`` + ``sprint_id``. Returns ``None`` when no sprint context is set
    (harness running outside a sprint — safety-rail subscribers treat ``None`` as
    "pass through"; no veto possible without a registry).

    Plan 02-11 calls this on sprint resume to re-trigger ``_load()`` from disk.
    """
    global _registry
    if _registry is None and team and sprint_id:
        _registry = FreezeRegistry(team, sprint_id)
    return _registry


def reset_freeze_registry() -> None:
    """Clear the module-level singleton so the next ``get_freeze_registry`` constructs anew.

    Intended for tests and for sprint-switch scenarios where the conductor needs to
    rehydrate against a different ``(team, sprint_id)``. Safe to call when no
    registry is set.
    """
    global _registry
    _registry = None
