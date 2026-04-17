"""InteractionGate — a PhaseGate subclass blocking on unanswered questions.

Per RFC 001 §4.5 and context D-06. Presence-only check (no frontmatter
parsing; that is Plan 01-04's responsibility). The gate is reusable by
any template that writes the questions/<id>.md + answers/<id>.md layout;
it does not depend on gstack-specific semantics.

The gate accepts either a `SprintState` (Phase 1 harness path) or any
`PhaseState`/duck-typed state for reusability (RFC 001 §4.5 req 4 +
§8 open question 3). Only a `SprintState` triggers the sprint-directory
scan; a `PhaseState`-only caller receives `(True, "")` unchanged because
"no sprint context" means "no open questions to block on".

Because Plan 01-02 (which introduces `clawteam.sprint.state.SprintState`)
ships in the same Phase 1 wave as this plan, the `SprintState` import is
done lazily inside `_resolve_sprint_dir` so this module imports cleanly
in parallel-executor worktrees that don't yet have 01-02's changes merged
in. Once 01-02 lands on the target branch the isinstance narrowing
becomes effective automatically — no call-site changes needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from clawteam.harness.phases import PhaseGate, PhaseState
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir

_MAX_IDS_IN_REASON = 5


def _load_sprint_state_class() -> type | None:
    """Return the `SprintState` class if importable, else None.

    Lazy import so this module loads in environments where Plan 01-02's
    `clawteam.sprint.state` has not yet landed. Once 01-02 is merged,
    `isinstance(state, SprintState)` narrowing becomes effective without
    any change to this file.
    """
    try:
        from clawteam.sprint.state import SprintState  # noqa: WPS433
        return SprintState
    except ImportError:
        return None


class InteractionGate(PhaseGate):
    """Blocks phase advance while any question lacks a sibling answer.

    Per RFC 001 §4.5:
    - `check(state)` returns `(False, "Open questions: ...")` when any
      `<sprint_dir>/questions/<id>.md` file exists without a sibling
      `<sprint_dir>/answers/<id>.md` file.
    - `check(state)` returns `(True, "")` when every question has an
      answer sibling or when no sprint directory is resolvable.

    Pairing is done by filename stem only (e.g., `a1b2c3d4.md`). Body
    parsing is deferred to later gates (Plan 01-04 introduces the
    question/answer frontmatter schema).

    The gate can also be constructed with an explicit `sprint_dir` for
    testing and for templates that do not use SprintState.
    """

    def __init__(self, sprint_dir: Path | None = None) -> None:
        self._override_sprint_dir = sprint_dir

    # ── Public API ──────────────────────────────────────────────────

    def check(self, state: Any) -> tuple[bool, str]:
        """Return (passed, reason). See class docstring for semantics."""
        try:
            sprint_dir = self._resolve_sprint_dir(state)
        except ValueError as exc:
            # Path-traversal / symlink escape: fail closed with a bounded reason.
            return False, f"invalid sprint path: {exc}"

        if sprint_dir is None or not sprint_dir.is_dir():
            # No sprint context → no open questions to block on.
            return True, ""

        try:
            unanswered = self._scan(sprint_dir)
        except ValueError as exc:
            # Symlink inside questions/ or answers/ escaped — fail closed.
            return False, f"invalid sprint path: {exc}"

        if not unanswered:
            return True, ""

        listed = unanswered[:_MAX_IDS_IN_REASON]
        overflow = len(unanswered) - len(listed)
        reason = "Open questions: " + ", ".join(listed)
        if overflow > 0:
            reason += f" +{overflow} more"
        return False, reason

    # ── Internals ───────────────────────────────────────────────────

    def _resolve_sprint_dir(self, state: Any) -> Path | None:
        """Derive the sprint directory from the provided state.

        - Explicit `sprint_dir` override (constructor arg) wins.
        - `SprintState` → get_data_dir()/teams/<team>/sprints/<sprint_id>/
          with both identifiers validated + ensure_within_root.
        - `PhaseState` or anything else → None (no sprint context).
        """
        if self._override_sprint_dir is not None:
            # Resolve the override through the same traversal guard as SprintState paths.
            override = self._override_sprint_dir.resolve(strict=False)
            root = get_data_dir().resolve()
            try:
                override.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"sprint_dir escapes data dir: {override}") from exc
            return override

        sprint_state_cls = _load_sprint_state_class()
        if sprint_state_cls is not None and isinstance(state, sprint_state_cls):
            team = getattr(state, "team", None)
            sprint_id = getattr(state, "sprint_id", None)
            validate_identifier(team, "team name")
            validate_identifier(sprint_id, "sprint id")
            candidate = ensure_within_root(
                get_data_dir() / "teams",
                team,
                "sprints",
                sprint_id,
            )
            # Resolve to catch a malicious symlink inside the sprint path.
            resolved = candidate.resolve(strict=False)
            root = get_data_dir().resolve()
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"sprint dir escapes data dir: {resolved}") from exc
            return candidate

        # PhaseState or unknown state: no sprint context.
        if isinstance(state, PhaseState):
            return None
        return None

    @staticmethod
    def _scan(sprint_dir: Path) -> list[str]:
        """Return sorted unanswered question IDs (stems) under sprint_dir.

        Any symlinked questions/ or answers/ directory pointing outside the
        data dir is rejected here as a belt-and-braces check against a
        symlink created after `_resolve_sprint_dir` returned.
        """
        questions_dir = sprint_dir / "questions"
        answers_dir = sprint_dir / "answers"

        if not questions_dir.is_dir():
            return []

        # Defense-in-depth: resolve the questions_dir and reject if it escapes the
        # sprint_dir (blocks a symlinked questions/ -> /etc or similar).
        sprint_resolved = sprint_dir.resolve(strict=False)
        q_resolved = questions_dir.resolve(strict=False)
        try:
            q_resolved.relative_to(sprint_resolved)
        except ValueError as exc:
            raise ValueError(f"questions dir escapes sprint dir: {q_resolved}") from exc

        if answers_dir.exists():
            a_resolved = answers_dir.resolve(strict=False)
            try:
                a_resolved.relative_to(sprint_resolved)
            except ValueError as exc:
                raise ValueError(f"answers dir escapes sprint dir: {a_resolved}") from exc

        question_ids = sorted(p.stem for p in questions_dir.glob("*.md"))
        answer_ids = (
            {p.stem for p in answers_dir.glob("*.md")} if answers_dir.is_dir() else set()
        )
        return [qid for qid in question_ids if qid not in answer_ids]
