"""/design-shotgun handler — multi-turn state machine orchestration (Plan 06-08).

Per-turn contract:

* Caller (SprintConductor + designer persona) passes an ``action`` in ``args``.
* Each action maps to a :class:`DSEvent` (or, for ``init``, to stateless
  config resolution without a transition).
* Handler loads ``<sprint_dir>/design-shotgun-state.json`` under
  ``file_locked``, runs ``state.advance(event, **kwargs)``, performs the
  side effects attached to that transition, saves the new state, writes a
  ``design-shotgun-note.md`` artifact capturing turn status, and returns a
  JSON-friendly dict.

Side effects by action:

* ``init``            — persist an INITIALIZED state with ``variant_count``
                        resolved from ``ctx.template.design_shotgun`` (default 4).
* ``generate``        — INITIALIZED → VARIANTS_GENERATING. If the call also
                        passes pre-rendered ``variants`` (test path), auto-fires
                        VARIANTS_READY and writes the board.
* ``variants_ready``  — VARIANTS_GENERATING → BOARD_RENDERED; writes the
                        comparison board (``design-board/variant-<N>/index.html``
                        + ``design-board/index.md`` catalog).
* ``publish``         — BOARD_RENDERED → USER_PICKING.
* ``pick``            — USER_PICKING → REFINING. Writes a taste-observation
                        :class:`MemoryEntry` to the designer's per-role memory
                        scope via :class:`TeamMemoryStore`.
* ``refine``          — REFINING → VARIANTS_GENERATING (loop; iteration += 1).
* ``converge``        — REFINING → CONVERGED (terminal).
* ``abandon``         — Any active state → ABANDONED (terminal).

All mutations flow through the pure :meth:`ShotgunState.advance` so illegal
transitions (e.g. ``pick`` from INITIALIZED) surface as ``ValueError``
directly — the handler does not swallow them.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.memory import MemoryEntry, TeamMemoryStore
from clawteam.templates.gstack.skills.design_shotgun.state import (
    DSEvent,
    DSState,
    ShotgunState,
    VariantFixture,
)


_DEFAULT_VARIANT_COUNT: int = 4


# ── Config resolution ──────────────────────────────────────────────────────


def _resolve_variant_count(ctx: Any) -> int:
    """Read ``template.design_shotgun.variant_count`` with a default of 4.

    The ``ctx`` object is duck-typed: tests ship a :class:`SimpleNamespace`
    with a ``template`` attribute; production dispatch wires a full
    :class:`HarnessContext`. Either shape works — we read via ``getattr``
    with defaults and bail out to ``_DEFAULT_VARIANT_COUNT`` on any miss.
    """
    tmpl = getattr(ctx, "template", None)
    if tmpl is None:
        return _DEFAULT_VARIANT_COUNT
    cfg = getattr(tmpl, "design_shotgun", None)
    if cfg is None:
        return _DEFAULT_VARIANT_COUNT
    try:
        return int(getattr(cfg, "variant_count", _DEFAULT_VARIANT_COUNT))
    except (TypeError, ValueError):
        return _DEFAULT_VARIANT_COUNT


# ── State persistence ──────────────────────────────────────────────────────


def _state_path(sprint_dir: Path) -> Path:
    return sprint_dir / "design-shotgun-state.json"


def _load_state(sprint_dir: Path) -> ShotgunState:
    path = _state_path(sprint_dir)
    if not path.is_file():
        return ShotgunState()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Malformed state: treat as fresh. Caller can /abandon if needed.
        return ShotgunState()
    try:
        return ShotgunState.from_json_dict(raw)
    except (ValueError, TypeError):
        return ShotgunState()


def _save_state(sprint_dir: Path, state: ShotgunState) -> None:
    path = _state_path(sprint_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state.to_json_dict(), indent=2)
    with file_locked(path):
        atomic_write_text(path, payload)


# ── Side effects ───────────────────────────────────────────────────────────


def _write_board(sprint_dir: Path, variants: list[VariantFixture]) -> Path:
    """Render the comparison board — per-variant HTML + catalog index.md.

    HTML content is authored by the designer agent (production) or loaded
    from ``tests/fixtures/design_shotgun/variant-<N>/index.html`` (tests).
    The handler only writes what the caller provided; it does not render.
    """
    board_dir = sprint_dir / "design-board"
    board_dir.mkdir(parents=True, exist_ok=True)

    lines: list[str] = ["# Design Shotgun Board", ""]
    for v in variants:
        variant_dir = board_dir / v.variant_id
        variant_dir.mkdir(parents=True, exist_ok=True)
        html_target = variant_dir / "index.html"
        if v.html_path:
            source = Path(v.html_path)
            if source.is_file():
                html_target.write_text(
                    source.read_text(encoding="utf-8"), encoding="utf-8",
                )
            else:
                html_target.write_text(
                    f"<!-- missing source: {v.html_path} -->\n"
                    f"<h1>{v.title}</h1>\n<p>{v.description}</p>\n",
                    encoding="utf-8",
                )
        else:
            # No source path — inline stub so the board is still well-formed.
            html_target.write_text(
                f"<!doctype html><html><body><h1>{v.title}</h1>"
                f"<p>{v.description}</p></body></html>\n",
                encoding="utf-8",
            )
        lines.append(f"## {v.title}")
        lines.append(f"- variant_id: {v.variant_id}")
        lines.append(f"- HTML: design-board/{v.variant_id}/index.html")
        lines.append(f"- {v.description}")
        lines.append("")

    index = board_dir / "index.md"
    atomic_write_text(index, "\n".join(lines) + "\n")
    return index


def _write_taste_memory(
    team_name: str,
    *,
    sprint_id: str,
    picked_variant_id: str,
    reason: str,
) -> str:
    """Write a designer-scoped taste-observation MemoryEntry and return its id.

    Provenance ``learned_from="user"`` because the user (not the agent)
    picked the variant — per D-06 this is the highest-weight provenance tier
    so the observation ranks strongly in future /learn search results.
    """
    store = TeamMemoryStore(team_name)
    entry_id = store.gen_id(
        author="designer@design-shotgun",
        title=f"picked {picked_variant_id}",
        tags=["design", "taste", "design-shotgun"],
    )
    entry = MemoryEntry(
        id=entry_id,
        author="designer@design-shotgun",
        sprint_id=sprint_id,
        phase="build",
        title=f"Taste observation: picked {picked_variant_id}",
        body=(
            f"User picked {picked_variant_id}"
            + (f" because: {reason}" if reason else ".")
        ),
        tags=["design", "taste", "design-shotgun"],
        evidence=f"design-board/{picked_variant_id}/index.html",
        confidence=0.9,
        learned_from="user",
        scope="role",
        role="designer",
    )
    store.write(entry)
    return entry_id


def _write_note(
    sprint_dir: Path,
    *,
    state: ShotgunState,
    status: str,
    memory_id: str = "",
) -> Path:
    """Write ``<sprint_dir>/design-shotgun-note.md`` capturing the turn outcome.

    Status string matches the caller's action so /reflect can grep one
    artifact file regardless of which action fired the turn.
    """
    created_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        "artifact_type: design-shotgun-note",
        f"status: {status!r}",
        f"state: {state.state.value!r}",
        f"iteration: {state.iteration}",
        f"variant_count: {state.variant_count}",
        f"picked_variant_id: {state.picked_variant_id!r}",
        f"pick_reason: {state.pick_reason!r}",
        f"sprint_id: {state.sprint_id!r}",
        f"memory_id: {memory_id!r}",
        f"created_at: {created_at!r}",
        "persona: designer",
        "step_label: design-shotgun",
        "done: true",
        "---",
        "",
        f"# Design Shotgun — {status}",
        "",
        f"State: `{state.state.value}` (iteration {state.iteration})",
        "",
    ]
    if state.picked_variant_id:
        lines.append(f"Picked: `{state.picked_variant_id}` — {state.pick_reason}")
        lines.append("")
    artifact = sprint_dir / "design-shotgun-note.md"
    atomic_write_text(artifact, "\n".join(lines) + "\n")
    return artifact


# ── Dispatch table ─────────────────────────────────────────────────────────


_ACTION_TO_EVENT: dict[str, DSEvent] = {
    "generate": DSEvent.GENERATE_REQUESTED,
    "variants_ready": DSEvent.VARIANTS_READY,
    "publish": DSEvent.BOARD_PUBLISHED,
    "pick": DSEvent.USER_PICKED,
    "refine": DSEvent.REFINE_REQUESTED,
    "converge": DSEvent.CONVERGE,
    "abandon": DSEvent.ABANDON,
}


def _coerce_variants(raw: Any) -> list[VariantFixture]:
    """Accept VariantFixture instances or dicts; return a normalised list."""
    if not raw:
        return []
    out: list[VariantFixture] = []
    for v in raw:
        if isinstance(v, VariantFixture):
            out.append(v)
        elif isinstance(v, dict):
            out.append(VariantFixture(**v))
        else:
            raise ValueError(
                f"variant must be VariantFixture or dict, got {type(v)!r}"
            )
    return out


# ── Entry point ────────────────────────────────────────────────────────────


def shotgun_handler(
    ctx: Any,
    *,
    role: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """/design-shotgun per-turn entry point.

    Required ``args`` key: ``action`` — one of ``init``, ``generate``,
    ``variants_ready``, ``publish``, ``pick``, ``refine``, ``converge``,
    ``abandon``. Additional keys depend on the action (``variants`` for
    generate/variants_ready; ``variant_id`` + ``reason`` for pick).

    Returns a dict with ``status`` + state snapshot fields. Writes a
    ``design-shotgun-note.md`` artifact to ``ctx.sprint_dir`` on every
    action so /reflect can surface the turn regardless of outcome.
    """
    sprint_dir = Path(getattr(ctx, "sprint_dir", Path.cwd()))
    sprint_id = getattr(ctx, "sprint_id", "") or ""
    team_name = getattr(ctx, "team_name", "") or "default"

    state = _load_state(sprint_dir)
    if not state.sprint_id:
        state = ShotgunState(
            state=state.state,
            sprint_id=sprint_id,
            variant_count=state.variant_count,
            variants=state.variants,
            picked_variant_id=state.picked_variant_id,
            pick_reason=state.pick_reason,
            iteration=state.iteration,
        )

    action = args.get("action", "init")

    # ── init: stateless config resolution, no transition ─────────────
    if action == "init":
        state = ShotgunState(
            state=state.state,
            sprint_id=sprint_id or state.sprint_id,
            variant_count=_resolve_variant_count(ctx),
            variants=state.variants,
            picked_variant_id=state.picked_variant_id,
            pick_reason=state.pick_reason,
            iteration=state.iteration,
        )
        _save_state(sprint_dir, state)
        note = _write_note(sprint_dir, state=state, status="init")
        return {
            "status": "initialized",
            "state": state.state.value,
            "iteration": state.iteration,
            "variant_count": state.variant_count,
            "picked_variant_id": state.picked_variant_id,
            "memory_id": "",
            "artifact_path": str(note),
        }

    # ── action → event (everything else) ─────────────────────────────
    event = _ACTION_TO_EVENT.get(action)
    if event is None:
        raise ValueError(f"unknown action {action!r}")

    advance_kwargs: dict[str, Any] = {}
    pre_rendered: list[VariantFixture] = []
    if action == "generate":
        # Allow caller to pass variants inline (test path). Handler then
        # auto-fires VARIANTS_READY so the board is written in one turn.
        pre_rendered = _coerce_variants(args.get("variants"))
    elif action == "variants_ready":
        advance_kwargs["variants"] = _coerce_variants(args.get("variants"))
    elif action == "pick":
        advance_kwargs["picked_variant_id"] = str(args.get("variant_id", ""))
        advance_kwargs["pick_reason"] = str(args.get("reason", ""))

    new_state = state.advance(event, **advance_kwargs)

    # ── Per-action side effects ──────────────────────────────────────
    memory_id = ""
    if action == "generate" and pre_rendered:
        # Auto-fire VARIANTS_READY with the pre-rendered batch.
        new_state = new_state.advance(DSEvent.VARIANTS_READY, variants=pre_rendered)
        _write_board(sprint_dir, new_state.variants)
    elif action == "variants_ready":
        _write_board(sprint_dir, new_state.variants)
    elif action == "pick":
        memory_id = _write_taste_memory(
            team_name,
            sprint_id=sprint_id,
            picked_variant_id=new_state.picked_variant_id,
            reason=new_state.pick_reason,
        )

    _save_state(sprint_dir, new_state)
    note = _write_note(
        sprint_dir, state=new_state, status=action, memory_id=memory_id,
    )
    return {
        "status": action,
        "state": new_state.state.value,
        "iteration": new_state.iteration,
        "variant_count": new_state.variant_count,
        "picked_variant_id": new_state.picked_variant_id,
        "memory_id": memory_id,
        "artifact_path": str(note),
    }


__all__ = ["shotgun_handler"]
