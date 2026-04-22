"""Per-tag TTL + decay_factor (D-06, MEM-07).

Expired entries are NEVER auto-deleted (MEM-07); their decay_factor drops
to 0.2 (within 2x TTL) then 0.05 (past 2x TTL) so they rank below fresh
entries but remain discoverable. Clock-skew tolerance: future timestamps
return 1.0, not 0.05 (see test_future_timestamp_returns_1).

TTL table (days):

================  =====  ================================================
tag               TTL    notes
================  =====  ================================================
pattern           90     overridable via MemoryConfig.retention_pattern_days
preference        ~inf   effectively never expires (100 years)
incident          180    overridable via MemoryConfig.retention_incident_days
retro             365    sprint retrospective notes
decision          1825   architecture decisions (5 years)
<unknown>         90     default floor for any unrecognised tag
<empty>           90     default floor when tags list is empty
================  =====  ================================================

Multi-tag entries take the **maximum** TTL (e.g. a pattern+preference
entry is treated as preference — indefinite).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawteam.memory.entry import MemoryEntry
    from clawteam.templates import MemoryConfig


# Built-in per-tag TTLs. MemoryConfig can override pattern/incident via
# gstack.toml [memory] retention_*_days; preference stays indefinite.
_INDEFINITE_DAYS = 365 * 100  # effectively never expires

_DEFAULT_TTL_BY_TAG: dict[str, int] = {
    "pattern": 90,
    "preference": _INDEFINITE_DAYS,
    "incident": 180,
    "retro": 365,
    "decision": 365 * 5,
}

_DEFAULT_TTL_DAYS = 90


def _ttl_for_entry(
    entry: "MemoryEntry", config: "MemoryConfig | None" = None
) -> int:
    """Return the MAX TTL (days) among the entry's tags; default 90."""
    ttl_table = dict(_DEFAULT_TTL_BY_TAG)
    if config is not None:
        ttl_table["pattern"] = int(config.retention_pattern_days)
        ttl_table["incident"] = int(config.retention_incident_days)
    candidates = [ttl_table.get(t, _DEFAULT_TTL_DAYS) for t in entry.tags]
    if not candidates:
        return _DEFAULT_TTL_DAYS
    return max(candidates)


def decay_factor(
    entry: "MemoryEntry",
    now: datetime | None = None,
    *,
    memory_config: "MemoryConfig | None" = None,
) -> float:
    """Return 1.0 / 0.2 / 0.05 based on entry age vs per-tag TTL (D-06).

    Parameters
    ----------
    entry:
        The :class:`MemoryEntry` whose freshness we're scoring.
    now:
        Reference "now" (defaults to :func:`datetime.now` in UTC). Exposed for
        deterministic testing.
    memory_config:
        Optional :class:`MemoryConfig` that overrides pattern / incident TTLs.

    Returns
    -------
    float
        * ``1.0`` when the entry is within its TTL.
        * ``0.2`` when the entry is past its TTL but within ``2 × TTL``.
        * ``0.05`` when the entry is past ``2 × TTL``.
        * ``0.05`` defensively when the timestamp is malformed (never crashes).
        * ``1.0`` when the timestamp is in the future (clock-skew tolerance).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    try:
        then = datetime.fromisoformat(entry.timestamp)
    except ValueError:
        return 0.05
    days = (now - then).total_seconds() / 86400.0
    if days < 0:
        # Clock skew / future-dated entry — treat as fresh.
        return 1.0
    ttl = _ttl_for_entry(entry, memory_config)
    if days <= ttl:
        return 1.0
    if days <= 2 * ttl:
        return 0.2
    return 0.05


__all__ = ["decay_factor"]
