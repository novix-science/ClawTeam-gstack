"""/ship entry point + 5-step orchestration (SKILL-14, D-05, Plan 05-04).

Pure-function pipeline: ``sync_main → run_tests → audit_coverage → push → open_pr``.
On first failure, halt and write ``ship-notes.md`` with ``failure_step``
populated. Does NOT auto-invoke ``/document-release`` here — that is Plan
05-07's wiring responsibility.

The step functions (:mod:`clawteam.templates.gstack.skills.ship.steps`) are
imported into this module namespace so tests can monkeypatch them per-test
without touching the real ``steps`` module's globals. Every handler-level
call site (``sync_main``, ``run_tests``, ...) resolves through the
module-level name here, giving tests a single uniform seam.
"""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.fileutil import atomic_write_text
from clawteam.plugins.skill_errors import SkillUnavailable
from clawteam.templates.gstack.schemas.ship_notes import ShipNotes
from clawteam.templates.gstack.skills._yaml_emit import yaml_quote_string
from clawteam.templates.gstack.skills.ship.steps import (
    StepResult,
    audit_coverage,
    open_pr,
    push,
    run_tests,
    sync_main,
)


_DEFAULT_COVERAGE_THRESHOLD: float = 0.5
_GH_INSTALL_HINT: str = (
    "apt install gh | brew install gh | winget install GitHub.cli"
)

_STEPS_COMPLETED_LABELS = {
    "sync": "sync",
    "test": "test",
    "coverage": "coverage",
    "push": "push",
    "pr": "pr",
}


def gh_available() -> bool:
    """Return True iff the ``gh`` CLI is on ``PATH`` (SkillRegistration probe)."""
    return shutil.which("gh") is not None


def _resolve_threshold(ctx: Any) -> float:
    """Read ``coverage_threshold`` from ``tmpl.ship.coverage_threshold``, else default.

    Accepts either ``ctx.template`` or ``ctx.tmpl`` for compatibility with the
    two naming conventions used elsewhere in the codebase (gstack tests +
    harness context).
    """
    tmpl = getattr(ctx, "template", None) or getattr(ctx, "tmpl", None)
    if tmpl is not None:
        ship_cfg = getattr(tmpl, "ship", None)
        if ship_cfg is not None:
            threshold = getattr(ship_cfg, "coverage_threshold", None)
            if threshold is not None:
                return float(threshold)
    return _DEFAULT_COVERAGE_THRESHOLD


def _render_ship_notes_yaml(schema: ShipNotes) -> str:
    """Emit a deterministic YAML frontmatter block for a :class:`ShipNotes`.

    Uses a hand-rolled serializer (same pattern as the codex handler) so the
    harness has no pyyaml dependency. Covered types:

    - ``bool``                      → ``true``/``false``
    - ``list`` / ``dict``           → JSON-literal (round-trips through json.loads)
    - ``None``                      → ``null``
    - ``str``                       → YAML single-quoted scalar (embedded ``'``
      doubled per YAML 1.2 §7.4.2; newlines fall back to JSON-encoded form)
      via :func:`yaml_quote_string` — see Phase-5 REVIEW WR-01.
    - all other (int / float)        → ``str()``
    """
    import json as _json

    d = schema.model_dump()
    lines: list[str] = ["---"]
    for key, val in d.items():
        if isinstance(val, bool):
            lines.append(f"{key}: {str(val).lower()}")
        elif isinstance(val, (list, dict)):
            lines.append(f"{key}: {_json.dumps(val)}")
        elif val is None:
            lines.append(f"{key}: null")
        elif isinstance(val, str):
            lines.append(f"{key}: {yaml_quote_string(val)}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + "\n"


def _write_ship_notes(
    sprint_dir: Path,
    *,
    sprint_id: str,
    ship_status: str,
    steps_completed: list[str],
    coverage: float | None,
    coverage_threshold: float | None,
    failure_step: str | None,
    failure_reason: str | None,
    pr_url: str | None,
    branch: str | None,
    auto_invoked_skills: list[str],
) -> Path:
    """Atomic-write ``<sprint_dir>/ship-notes.md`` with a :class:`ShipNotes` block.

    The required Phase-3 fields (``deploy_url`` + ``ship_step`` + ``notes``)
    are populated from Phase-5 context so the schema validates without
    requiring the caller to think about them: ``deploy_url="<pending>"`` is
    the D-02 Phase-5 tool-availability stub; ``ship_step`` is mapped from
    the failed step (``pr`` if succeeded); ``notes`` is a synthesized one-
    line summary of the outcome.
    """
    created_at = datetime.now(timezone.utc).isoformat()
    # Map Phase-5 failure_step (or "pr" on success) to the Phase-3 ship_step
    # Literal enum. pytest/pipeline step labels already match the enum.
    ship_step_for_schema = failure_step or "pr"
    if ship_step_for_schema not in {
        "sync", "test", "audit", "push", "pr", "merge", "deploy", "verify",
    }:
        ship_step_for_schema = "pr"
    # synthesize a ≥20 char notes payload so Phase-3 min_length holds.
    notes_summary = (
        f"ship_status={ship_status}; steps_completed={steps_completed}; "
        f"branch={branch}"
    )
    if len(notes_summary) < 20:
        notes_summary = notes_summary + " — Phase 5 /ship pipeline"

    schema = ShipNotes(
        artifact_type="ship-notes",
        sprint_id=sprint_id,
        created_at=created_at,
        deploy_url=pr_url or "<pending>",
        ship_step=ship_step_for_schema,
        pr_url=pr_url or "",
        notes=notes_summary,
        ship_status=ship_status,  # type: ignore[arg-type]
        steps_completed=steps_completed,
        coverage=coverage,
        coverage_threshold=coverage_threshold,
        failure_step=failure_step,
        failure_reason=failure_reason,
        branch=branch,
        auto_invoked_skills=auto_invoked_skills,
    )
    sprint_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = sprint_dir / "ship-notes.md"
    atomic_write_text(artifact_path, _render_ship_notes_yaml(schema))
    return artifact_path


def ship_handler(
    ctx: Any, *, role: str, args: dict[str, Any],
) -> dict[str, Any]:
    """/ship entry point (SKILL-14, shipper role only).

    Returns a dict with at least ``ship_status`` + ``artifact_path``; on
    success also ``pr_url`` + ``coverage``.
    """
    if not gh_available():
        raise SkillUnavailable(
            skill="/ship",
            binary="gh",
            install_hint=_GH_INSTALL_HINT,
            role=role,
        )

    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    sprint_id = getattr(ctx, "sprint_id", "")
    cwd = Path(getattr(ctx, "workspace_dir", sprint_dir))
    branch = args.get("branch") or getattr(ctx, "branch", "HEAD")
    title = args.get("title") or f"Ship: {sprint_id}"
    body = args.get("body", "")

    steps_completed: list[str] = []
    coverage: float | None = None
    coverage_threshold = _resolve_threshold(ctx)

    def _fail(step: str, result: StepResult, cov: float | None) -> dict[str, Any]:
        artifact = _write_ship_notes(
            sprint_dir,
            sprint_id=sprint_id,
            ship_status="failed",
            steps_completed=list(steps_completed),
            coverage=cov,
            coverage_threshold=coverage_threshold,
            failure_step=step,
            failure_reason=str(result.details),
            pr_url=None,
            branch=branch,
            auto_invoked_skills=[],
        )
        return {
            "artifact_path": str(artifact),
            "ship_status": "failed",
            "failure_step": step,
            "failure_reason": str(result.details),
        }

    # Step 1: sync_main
    sync_result = sync_main(cwd, branch)
    if not sync_result.success:
        return _fail("sync", sync_result, None)
    steps_completed.append("sync")

    # Step 2: run_tests
    tests_result = run_tests(cwd, sprint_dir)
    if not tests_result.success:
        return _fail("test", tests_result, None)
    steps_completed.append("test")

    # Step 3: audit_coverage
    cov_result = audit_coverage(cwd, coverage_threshold)
    coverage = cov_result.details.get("coverage")
    if not cov_result.success:
        return _fail("coverage", cov_result, coverage)
    steps_completed.append("coverage")

    # Step 4: push
    push_result = push(cwd, branch)
    if not push_result.success:
        return _fail("push", push_result, coverage)
    steps_completed.append("push")

    # Step 5: open_pr
    pr_result = open_pr(cwd, title, body)
    if not pr_result.success:
        return _fail("pr", pr_result, coverage)
    pr_url = pr_result.details.get("pr_url")
    steps_completed.append("pr")

    # All 5 steps succeeded — Plan 05-07 D-11: auto-invoke /document-release.
    # Failure of /document-release MUST NOT fail /ship: the try/except demotes
    # any exception to a ``/document-release:failed:<reason>`` marker in the
    # ship-notes. Import is inside the try/except so a missing
    # document_release sub-package (extremely unlikely post-05-07) also
    # degrades gracefully.
    auto_invoked: list[str] = []
    try:
        from clawteam.templates.gstack.skills.document_release import (
            handler as _dr_mod,
        )
        _dr_mod.document_release_handler(ctx, role=role, args={})
        auto_invoked.append("/document-release")
    except Exception as exc:  # noqa: BLE001 — deliberate: never fail /ship
        auto_invoked.append(f"/document-release:failed:{exc}")

    artifact = _write_ship_notes(
        sprint_dir,
        sprint_id=sprint_id,
        ship_status="succeeded",
        steps_completed=list(steps_completed),
        coverage=coverage,
        coverage_threshold=coverage_threshold,
        failure_step=None,
        failure_reason=None,
        pr_url=pr_url,
        branch=branch,
        auto_invoked_skills=auto_invoked,
    )
    return {
        "artifact_path": str(artifact),
        "ship_status": "succeeded",
        "pr_url": pr_url,
        "coverage": coverage,
    }
