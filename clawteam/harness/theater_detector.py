"""Re-export shim — enables the Pitfall #3 progress-signal test in Plan 02-08.

``tests/test_cycle_detector.py::test_progress_signal_breaks_cycle_streak_per_pitfall3``
skips unless ``clawteam.harness.theater_detector`` is importable. Plan 02-09 ships
the theater detector at :mod:`clawteam.harness.forced_progress_gate` (§02-CONTEXT
D-17 naming), so this module is a thin re-export so the cross-plan import gate flips.

The canonical names live in :mod:`clawteam.harness.forced_progress_gate`; this
module is an alias and should not accumulate new logic.
"""

from __future__ import annotations

from clawteam.harness.forced_progress_gate import (
    NO_PROGRESS_THRESHOLD,
    forced_progress_gate,
    increment_turn_counter,
    reset_turn_counter_state,
)

__all__ = [
    "NO_PROGRESS_THRESHOLD",
    "forced_progress_gate",
    "increment_turn_counter",
    "reset_turn_counter_state",
]
