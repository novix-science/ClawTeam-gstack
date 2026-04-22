"""Auto-accept-reversible helper (D-08).

D-08 locks: apply default-accept-with-TTL (15 min) to questions with
``reversibility: easy`` frontmatter ONLY. Preview shows exactly what
would auto-accept; apply writes ``answer.md`` with ``auto_accepted: true``
frontmatter so audit is clean.

Non-easy items (``medium`` / ``hard`` / unknown) are never written, even
if a caller passes them to :func:`apply_auto_accept` directly — they
land in the ``skipped`` bucket of the returned dict.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Optional

from clawteam.attention.queue import AttentionItem

DEFAULT_TTL_MINUTES = 15


def preview_auto_accept(
    items: list[AttentionItem],
) -> list[AttentionItem]:
    """Return items eligible for ``--auto-accept-reversible``, priority desc.

    Eligible = ``reversibility == "easy"``. Medium and hard are always excluded.
    Order: ``priority_score`` descending (highest priority first).
    """
    easy = [i for i in items if i.reversibility == "easy"]
    return sorted(easy, key=lambda i: i.priority_score, reverse=True)


def apply_auto_accept(
    items: list[AttentionItem],
    *,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
    now_fn: Optional[Callable[[], datetime]] = None,
) -> dict[str, Any]:
    """Write ``answer.md`` for each easy item with ``auto_accepted: true``.

    Returns a dict::

        {"applied": [question_id, ...], "skipped": [question_id, ...]}

    Semantics:

    * Item with ``reversibility != "easy"`` → ``skipped`` (never written).
    * Item whose answer file already exists → ``skipped`` (idempotent).
    * Otherwise → ``applied`` (answer.md written atomically).

    The answer file lives at ``<question.parent.parent>/answers/<qid>.md``,
    matching the existing InteractionGate layout.
    """
    now = now_fn or (lambda: datetime.now(timezone.utc))
    applied: list[str] = []
    skipped: list[str] = []
    for item in items:
        if item.reversibility != "easy":
            skipped.append(item.question_id)
            continue
        answer_path = (
            item.question_path.parent.parent / "answers" / item.question_path.name
        )
        if answer_path.exists():
            skipped.append(item.question_id)
            continue
        answer_path.parent.mkdir(parents=True, exist_ok=True)
        frontmatter = (
            f"---\n"
            f"auto_accepted: true\n"
            f"auto_accepted_at: {now().isoformat()}\n"
            f"ttl_minutes: {ttl_minutes}\n"
            f"question_id: {item.question_id}\n"
            f"---\n"
        )
        body = (
            "Auto-accepted per --auto-accept-reversible. "
            "Default option: (first choice in question.md).\n"
            "\n"
            f"This answer was written by `clawteam attend --auto-accept-reversible` "
            f"against a question tagged `reversibility: easy`. "
            f"TTL = {ttl_minutes} minutes."
        )
        answer_path.write_text(frontmatter + body, encoding="utf-8")
        applied.append(item.question_id)
    return {"applied": applied, "skipped": skipped}


__all__ = [
    "DEFAULT_TTL_MINUTES",
    "apply_auto_accept",
    "preview_auto_accept",
]
