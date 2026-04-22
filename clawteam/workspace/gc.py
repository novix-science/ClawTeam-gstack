"""Zombie-worktree auto-GC + disk-budget observability.

Phase 7 Plan 07-08 / ROADMAP §Phase 7 SC #10.

Safety invariant
----------------
NEVER delete a worktree whose branch matches an active
``SprintState.workspace_branch`` (07-RESEARCH §Pitfall 6). The
``find_zombie_worktrees`` ``active_branches`` parameter is the
enforcement surface. Callers that skip the filter bear the risk of
nuking in-flight work; the ``clawteam doctor --gc`` wiring in
``clawteam/cli/commands.py`` always populates it from the SprintState
store.

Surface
-------
- ``find_zombie_worktrees(root, *, max_age_days, active_branches, now_fn)``
  — returns direct-child dirs of ``root`` older than the threshold
  whose basename is NOT in ``active_branches``.
- ``gc_zombies(paths, *, team_name, bus, now_fn)`` — best-effort
  ``shutil.rmtree`` each path; emits one ``ZombieWorktreeGced`` per
  deletion if a bus is supplied. Idempotent on missing paths.
- ``disk_usage_report(team_root)`` — sums bytes under the team dir and
  classifies against the soft (5 GB) / hard (10 GB) thresholds
  documented in 07-CONTEXT.
"""

from __future__ import annotations

import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from clawteam.events.bus import EventBus
from clawteam.events.types import ZombieWorktreeGced


@dataclass(frozen=True)
class GcResult:
    """Per-path outcome from :func:`gc_zombies`.

    Surfaces the freed-bytes signal the CLI summary needs (WR-03). The
    per-event ``ZombieWorktreeGced.freed_bytes`` was already computed
    but previously never bubbled back to the caller — the CLI had to
    guess ``total_freed_bytes = sum([])`` which was hardcoded to zero.
    """

    path: Path
    age_days: int
    freed_bytes: int

# Per-team disk-budget thresholds (07-CONTEXT §Cluster A #4).
SOFT_BYTES = 5 * 1024 * 1024 * 1024
HARD_BYTES = 10 * 1024 * 1024 * 1024


def find_zombie_worktrees(
    root: Path,
    *,
    max_age_days: int = 30,
    active_branches: Iterable[str] = (),
    now_fn=time.time,
) -> list[Path]:
    """Return direct-child dirs of ``root`` older than ``max_age_days``.

    ``active_branches`` holds branch names (matched against directory
    basenames) that MUST be preserved regardless of age.

    Missing/unreadable ``root`` returns ``[]`` — callers treat the
    absence of a worktrees dir as "no zombies to gc". Files and
    symlinks at the top level are skipped; only real directories are
    considered worktrees.
    """
    if not root.is_dir():
        return []
    active = set(active_branches)
    cutoff = now_fn() - (max_age_days * 86400.0)
    zombies: list[Path] = []
    for child in root.iterdir():
        if not child.is_dir():
            continue
        if child.name in active:
            continue
        try:
            mtime = child.stat().st_mtime
        except OSError:
            # Permissions / vanished-between-listdir-and-stat; skip.
            continue
        if mtime < cutoff:
            zombies.append(child)
    return zombies


def _dir_size(path: Path) -> int:
    """Best-effort recursive byte count under ``path``.

    Swallows per-entry ``OSError`` so broken symlinks or permission
    gaps never blow up the whole walk.
    """
    total = 0
    if not path.exists():
        return 0
    for p in path.rglob("*"):
        try:
            if p.is_file():
                total += p.stat().st_size
        except OSError:
            continue
    return total


def gc_zombies(
    paths: Iterable[Path],
    *,
    team_name: str = "",
    bus: Optional[EventBus] = None,
    now_fn=time.time,
) -> list[GcResult]:
    """Delete each path; emit ``ZombieWorktreeGced`` if a bus is set.

    Returns a list of :class:`GcResult` — one entry per successfully
    removed path (WR-03: surfaces ``freed_bytes`` so the CLI summary
    total is meaningful).

    Idempotent on missing paths (silently skipped — no event, no
    :class:`GcResult`). Uses ``shutil.rmtree(ignore_errors=True)`` so a
    partial delete of a tangled worktree still makes forward progress.

    If ``shutil.rmtree`` leaves the directory behind (permission gaps,
    open file handles, in-use mounts), the path is NOT appended and no
    event fires (WR-04). Callers would otherwise not be able to
    distinguish a true delete from a silent partial failure — a GC
    subsystem whose primary contract is freeing disk must not lie
    about it. The zombie stays on disk and is discoverable on the next
    sweep; freed-bytes aggregates remain honest.
    """
    gced: list[GcResult] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            mtime = path.stat().st_mtime
            age_days = int((now_fn() - mtime) / 86400.0)
            freed = _dir_size(path)
            shutil.rmtree(path, ignore_errors=True)
        except OSError:
            continue
        # WR-04: ``ignore_errors=True`` silently returns on per-entry
        # rmtree failure. Re-check existence so we don't claim a delete
        # that did not actually happen.
        if path.exists():
            continue
        result = GcResult(path=path, age_days=age_days, freed_bytes=freed)
        gced.append(result)
        if bus is not None:
            try:
                bus.emit(
                    ZombieWorktreeGced(
                        team_name=team_name,
                        path=str(path),
                        age_days=age_days,
                        freed_bytes=freed,
                    )
                )
            except Exception:  # pragma: no cover — defensive; emit must never crash gc
                pass
    return gced


def disk_usage_report(team_root: Path) -> dict:
    """Return a disk-usage dict for ``team_root``.

    Fields
    ------
    - ``path``: string form of ``team_root`` for JSON round-trip.
    - ``total_bytes`` / ``total_gb``: disk consumption under the dir.
    - ``over_soft`` / ``over_hard``: booleans against module-level
      ``SOFT_BYTES`` (5 GB) / ``HARD_BYTES`` (10 GB) thresholds.
    - ``soft_threshold_gb`` / ``hard_threshold_gb``: human-readable
      threshold labels for the ``clawteam team show`` disk row.
    """
    total = _dir_size(team_root)
    return {
        "path": str(team_root),
        "total_bytes": total,
        "total_gb": round(total / (1024**3), 2),
        "over_soft": total > SOFT_BYTES,
        "over_hard": total > HARD_BYTES,
        "soft_threshold_gb": SOFT_BYTES // (1024**3),
        "hard_threshold_gb": HARD_BYTES // (1024**3),
    }


__all__ = [
    "find_zombie_worktrees",
    "gc_zombies",
    "disk_usage_report",
    "GcResult",
    "SOFT_BYTES",
    "HARD_BYTES",
]
