"""High-impact gate — MEM-06 (Plan 06-11 Task 1).

Two responsibilities:

* :func:`check_high_impact` — classify a :class:`MemoryEntry` as requiring
  human confirmation before persistence. Returns ``(requires, reason)``.
  Current policy (Phase 6 Success Criteria #6):

    - ``impact:high`` tag present — covers the /learn ``impact="high"`` path
      which auto-tags before gate dispatch (see
      ``templates/gstack/skills/learn/handler.py::_build_entry``).
    - ``scope == "team"`` AND any tag starts with ``"decisions"`` — matches
      the ``memory/team/decisions/`` convention (MEM-06 requirement text:
      *tagged ``impact:high`` OR under ``memory/team/decisions/``*).

* :func:`stage_pending` — persist the pending entry to
  ``<data_dir>/teams/<team>/memory/<scope>/pending/<id>.jsonl`` AND write
  an InteractionGate-consumable question artifact to
  ``<data_dir>/teams/<team>/sprints/<sprint_id>/questions/memory-confirm-<id>.md``.

The question artifact shape is pairable by
:class:`clawteam.harness.interaction_gate.InteractionGate` via stem
matching (``memory-confirm-<id>`` has no corresponding ``answers/`` file
until a human writes one). See Plan 04-04 HumanApprovalGate subclass
pattern — this re-uses the same file layout without subclassing
``InteractionGate`` (MEM-06 gate is advisory on the /learn path; the
sprint-phase InteractionGate enforcement applies uniformly to any open
question).

Tombstone bypass: :meth:`TeamMemoryStore.prune` deliberately does NOT
call :func:`check_high_impact` — tombstones ARE the undo (research Open
Question 3). The gate is only on fresh writes.
"""

from __future__ import annotations

from pathlib import Path

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.memory.entry import MemoryEntry

HIGH_IMPACT_TAG = "impact:high"


def check_high_impact(entry: MemoryEntry) -> tuple[bool, str]:
    """Return ``(requires_confirmation, reason)``.

    ``reason`` is an empty string when ``requires_confirmation`` is False.
    """
    if HIGH_IMPACT_TAG in entry.tags:
        return True, f"tagged {HIGH_IMPACT_TAG}"
    if entry.scope == "team" and any(
        t == "decisions" or t.startswith("decisions:") or t.startswith("decisions-")
        for t in entry.tags
    ):
        return True, "memory/team/decisions/ scope"
    return False, ""


def stage_pending(
    entry: MemoryEntry,
    *,
    team: str,
    sprint_id: str | None,
    root: Path,
) -> Path:
    """Stage *entry* to ``memory/<scope>/pending/<id>.jsonl`` + question artifact.

    Parameters
    ----------
    entry:
        The :class:`MemoryEntry` to stage — NOT yet persisted to the main
        JSONL bucket.
    team:
        Team name; resolved under ``root/teams/<team>/``. No
        cross-team paths are written.
    sprint_id:
        Optional sprint id. When present, a ``memory-confirm-<id>.md``
        question artifact is written under
        ``sprints/<sprint_id>/questions/``. When ``None`` the question
        artifact is skipped (valid for teams with no active sprint, e.g.
        retro-driven /learn outside a sprint).
    root:
        Data-directory root (typically ``get_data_dir()``).

    Returns
    -------
    Path
        Absolute path of the pending JSONL file — exposed so /learn can
        surface it in the handler result for callers that want to echo it.
    """
    scope_dir_name = entry.scope  # "team" or "role"
    pending_dir = (
        root / "teams" / team / "memory" / scope_dir_name / "pending"
    )
    pending_dir.mkdir(parents=True, exist_ok=True)
    pending_path = pending_dir / f"{entry.id}.jsonl"
    # JSONL: one record per line, trailing newline.
    payload = entry.model_dump_json() + "\n"
    with file_locked(pending_path):
        atomic_write_text(pending_path, payload)

    if sprint_id:
        questions_dir = (
            root / "teams" / team / "sprints" / sprint_id / "questions"
        )
        questions_dir.mkdir(parents=True, exist_ok=True)
        question_path = questions_dir / f"memory-confirm-{entry.id}.md"
        evidence_display = entry.evidence or "(none — MEM-05 flagged)"
        body_preview = entry.body[:300] + (
            "..." if len(entry.body) > 300 else ""
        )
        artifact_body = (
            f"# Memory write: high-impact confirmation required\n\n"
            f"**Entry id:** {entry.id}\n"
            f"**Scope:** {entry.scope}"
            + (f" (role={entry.role})" if entry.role else "")
            + "\n"
            f"**Tags:** {', '.join(entry.tags) if entry.tags else '(none)'}\n"
            f"**Author:** {entry.author}\n"
            f"**Evidence:** {evidence_display}\n"
            f"**Confidence:** {entry.confidence}\n\n"
            f"## Title\n\n{entry.title}\n\n"
            f"## Body preview\n\n> {body_preview}\n\n"
            f"## Options\n\n"
            f"1. **Confirm** — reply with `confirm` to promote "
            f"{pending_path.name} into the main JSONL store.\n"
            f"2. **Edit** — reply with proposed edits; Phase 7 applies them "
            f"before promotion.\n"
            f"3. **Reject** — reply with `reject` to delete the pending "
            f"record (no tombstone needed; write never happened).\n"
        )
        atomic_write_text(question_path, artifact_body)

    return pending_path


__all__ = [
    "HIGH_IMPACT_TAG",
    "check_high_impact",
    "stage_pending",
]
