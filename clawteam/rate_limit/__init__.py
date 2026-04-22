"""Rate-limit substrate — 429-bucket monitor consulted by SprintConductor.

Phase 7 Plan 07-02 adds :class:`RateLimitMonitor`; conductor.start_sprint_async
consults ``is_saturated()`` before acquiring the concurrent-sprint semaphore.
"""
from __future__ import annotations

from clawteam.rate_limit.monitor import RateLimitMonitor

__all__ = ["RateLimitMonitor"]
