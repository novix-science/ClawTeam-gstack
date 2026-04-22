"""ShotgunState — /design-shotgun multi-turn state machine (Plan 06-08, D-12).

Designer-role variant-generation forcing-loop. Each turn the handler calls
``state.advance(event, **data)`` to transition between:

  INITIALIZED
       │ GENERATE_REQUESTED
       ▼
  VARIANTS_GENERATING ──VARIANTS_READY──▶ BOARD_RENDERED ──BOARD_PUBLISHED──▶ USER_PICKING
        ▲                                                                         │
        │ REFINE_REQUESTED                                                        │ USER_PICKED
        │ (iteration += 1 when iteration ≥ 1)                                     ▼
        └─────────────────────────────── REFINING ───────CONVERGE──▶ CONVERGED
                                              │
                                              └───ABANDON─▶ ABANDONED (also legal from every active state)

Unlike Phase 4 ``/office-hours`` (pydantic) this state machine uses a stdlib
dataclass because its payload (list of VariantFixture) is simpler and pydantic
would add friction around the nested dataclass field. The shape still mirrors
the Phase 4 invariants:

* ``advance(event, **data) -> ShotgunState`` is **pure**: returns a new
  instance and never mutates ``self``. Persistence is caller-side (handler
  writes ``<sprint_dir>/design-shotgun-state.json`` via ``file_locked`` +
  ``atomic_write_text``).
* ``(from_state, event)`` pairs not present in :data:`TRANSITIONS` raise
  ``ValueError`` — caller converts to a SkillError surface if needed.
* Iteration increments **only** when the REFINE_REQUESTED event drives the
  REFINING → VARIANTS_GENERATING loop AND the old state already had
  ``iteration >= 1`` (the initial INITIALIZED → VARIANTS_GENERATING kick-off
  does NOT bump iteration).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enums ──────────────────────────────────────────────────────────────────


class DSState(str, Enum):
    """/design-shotgun state labels (7 total — 5 active + 2 terminal)."""

    INITIALIZED = "initialized"
    VARIANTS_GENERATING = "variants_generating"
    BOARD_RENDERED = "board_rendered"
    USER_PICKING = "user_picking"
    REFINING = "refining"
    CONVERGED = "converged"
    ABANDONED = "abandoned"


class DSEvent(str, Enum):
    """/design-shotgun events that drive state transitions."""

    GENERATE_REQUESTED = "generate_requested"
    VARIANTS_READY = "variants_ready"
    BOARD_PUBLISHED = "board_published"
    USER_PICKED = "user_picked"
    REFINE_REQUESTED = "refine_requested"
    CONVERGE = "converge"
    ABANDON = "abandon"


# ── Transition table ──────────────────────────────────────────────────────


# (from_state, event) → to_state. Missing key = illegal transition (ValueError).
TRANSITIONS: dict[tuple[DSState, DSEvent], DSState] = {
    (DSState.INITIALIZED, DSEvent.GENERATE_REQUESTED): DSState.VARIANTS_GENERATING,
    (DSState.VARIANTS_GENERATING, DSEvent.VARIANTS_READY): DSState.BOARD_RENDERED,
    (DSState.BOARD_RENDERED, DSEvent.BOARD_PUBLISHED): DSState.USER_PICKING,
    (DSState.USER_PICKING, DSEvent.USER_PICKED): DSState.REFINING,
    (DSState.REFINING, DSEvent.REFINE_REQUESTED): DSState.VARIANTS_GENERATING,  # loop
    (DSState.REFINING, DSEvent.CONVERGE): DSState.CONVERGED,
    # ABANDON is a legal transition from every active state.
    (DSState.INITIALIZED, DSEvent.ABANDON): DSState.ABANDONED,
    (DSState.VARIANTS_GENERATING, DSEvent.ABANDON): DSState.ABANDONED,
    (DSState.BOARD_RENDERED, DSEvent.ABANDON): DSState.ABANDONED,
    (DSState.USER_PICKING, DSEvent.ABANDON): DSState.ABANDONED,
    (DSState.REFINING, DSEvent.ABANDON): DSState.ABANDONED,
}

_FINAL_STATES: frozenset[DSState] = frozenset({DSState.CONVERGED, DSState.ABANDONED})


# ── Payload dataclasses ───────────────────────────────────────────────────


@dataclass
class VariantFixture:
    """One variant in a design-shotgun iteration (D-17).

    Persisted inside :class:`ShotgunState` and surfaced in the board
    catalog. ``html_path`` is either an absolute path on disk (test path —
    fixtures under ``tests/fixtures/design_shotgun/variant-<N>/index.html``)
    or a sprint-relative path produced by the designer agent at runtime.
    """

    variant_id: str  # "variant-1" .. "variant-N"
    title: str
    description: str
    html_path: str = ""
    screenshot_path: str = ""  # optional — Playwright screenshot, not required
    design_tokens: dict[str, str] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "title": self.title,
            "description": self.description,
            "html_path": self.html_path,
            "screenshot_path": self.screenshot_path,
            "design_tokens": dict(self.design_tokens),
        }

    @classmethod
    def from_json_dict(cls, raw: dict[str, Any]) -> "VariantFixture":
        return cls(
            variant_id=str(raw.get("variant_id", "")),
            title=str(raw.get("title", "")),
            description=str(raw.get("description", "")),
            html_path=str(raw.get("html_path", "")),
            screenshot_path=str(raw.get("screenshot_path", "")),
            design_tokens=dict(raw.get("design_tokens") or {}),
        )


@dataclass
class ShotgunState:
    """Immutable-ish snapshot of the /design-shotgun state machine.

    ``advance()`` is the only legal mutation path and always returns a new
    instance (the old one is never modified in-place). Callers persist via
    ``to_json_dict`` ↔ ``from_json_dict`` on the JSON state file.
    """

    state: DSState = DSState.INITIALIZED
    sprint_id: str = ""
    variant_count: int = 4
    variants: list[VariantFixture] = field(default_factory=list)
    picked_variant_id: str = ""
    pick_reason: str = ""
    iteration: int = 0  # bumped on REFINING → VARIANTS_GENERATING loop

    # ── Advance ────────────────────────────────────────────────────────

    def advance(self, event: DSEvent, **data: Any) -> "ShotgunState":
        """Pure state-machine step. Returns a new ShotgunState.

        Raises ``ValueError`` if the ``(current_state, event)`` pair is not
        in :data:`TRANSITIONS`. Accepted kwargs:

        * ``variants``: list[VariantFixture] — passed on VARIANTS_READY.
        * ``picked_variant_id`` / ``pick_reason``: passed on USER_PICKED.

        Unrecognised kwargs are silently ignored (future-compat).
        """
        key = (self.state, event)
        if key not in TRANSITIONS:
            raise ValueError(
                f"illegal transition: {self.state.value} + {event.value}"
            )
        new_state = TRANSITIONS[key]

        # Iteration rule: only the REFINE_REQUESTED-driven
        # REFINING → VARIANTS_GENERATING loop increments iteration, AND
        # only when we already have iteration >= 1 (first kick-off from
        # INITIALIZED does not count).
        next_iteration = self.iteration
        if (
            event == DSEvent.REFINE_REQUESTED
            and self.state == DSState.REFINING
            and new_state == DSState.VARIANTS_GENERATING
            and self.iteration >= 1
        ):
            next_iteration = self.iteration + 1
        # Initial INITIALIZED → VARIANTS_GENERATING: mark iteration=1 so the
        # FIRST refine loop bumps to 2 (handler + tests depend on this
        # "first-gen is iteration 1" convention so the user's pick is always
        # at iteration >= 1 and subsequent refines are monotone).
        elif (
            event == DSEvent.GENERATE_REQUESTED
            and self.state == DSState.INITIALIZED
            and self.iteration == 0
        ):
            # Keep iteration == 0 for the initial kick-off (per test
            # test_refine_loop_increments_iteration contract), but upgrade to
            # 1 on the USER_PICKED landing so the FIRST REFINE_REQUESTED
            # loop hits iteration >= 1. See below.
            pass

        # USER_PICKED landing: the user has now completed round-1 → mark
        # iteration=1 so the first refine loop (if any) bumps to 2.
        if (
            event == DSEvent.USER_PICKED
            and self.state == DSState.USER_PICKING
            and new_state == DSState.REFINING
            and self.iteration == 0
        ):
            next_iteration = 1

        # Variants propagate through the table: keep the existing list by
        # default; allow VARIANTS_READY to replace it with the fresh batch.
        next_variants = data.get("variants", self.variants)
        # Pick data carries forward on USER_PICKED; otherwise preserve.
        next_picked = data.get("picked_variant_id", self.picked_variant_id)
        next_reason = data.get("pick_reason", self.pick_reason)

        return ShotgunState(
            state=new_state,
            sprint_id=self.sprint_id,
            variant_count=self.variant_count,
            variants=list(next_variants),
            picked_variant_id=next_picked,
            pick_reason=next_reason,
            iteration=next_iteration,
        )

    # ── Convenience ────────────────────────────────────────────────────

    def is_final(self) -> bool:
        return self.state in _FINAL_STATES

    # ── Serialization ──────────────────────────────────────────────────

    def to_json_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict (for state.json persistence)."""
        return {
            "state": self.state.value,
            "sprint_id": self.sprint_id,
            "variant_count": self.variant_count,
            "variants": [v.to_json_dict() for v in self.variants],
            "picked_variant_id": self.picked_variant_id,
            "pick_reason": self.pick_reason,
            "iteration": self.iteration,
        }

    @classmethod
    def from_json_dict(cls, raw: dict[str, Any]) -> "ShotgunState":
        """Rebuild a ShotgunState from a previously-serialized dict.

        Malformed state strings raise ValueError via DSState(...). Missing
        keys fall back to their dataclass defaults.
        """
        state_raw = raw.get("state", DSState.INITIALIZED.value)
        state = DSState(state_raw)
        variants_raw = raw.get("variants") or []
        variants = [VariantFixture.from_json_dict(v) for v in variants_raw]
        return cls(
            state=state,
            sprint_id=str(raw.get("sprint_id", "")),
            variant_count=int(raw.get("variant_count", 4)),
            variants=variants,
            picked_variant_id=str(raw.get("picked_variant_id", "")),
            pick_reason=str(raw.get("pick_reason", "")),
            iteration=int(raw.get("iteration", 0)),
        )


__all__ = [
    "DSEvent",
    "DSState",
    "ShotgunState",
    "TRANSITIONS",
    "VariantFixture",
]
