"""/design-html handler (SKILL-12, Plan 06-09).

Reads a mockup HTML file (chosen variant from /design-shotgun), inspects the
project for a frontend framework, and emits a production-shape source file
at the framework's conventional source root. Ambiguous projects defer the
choice to the user via a ``questions/*.md`` artifact.

Handler contract (PLAN 06-09 behavior):

* ``args["mockup_html_path"]`` — path to the chosen variant's HTML. Missing
  file raises ``FileNotFoundError`` (T-06-09-01: normal validation surface).
* ``args["component_name"]`` — optional; defaults to ``"Hero"``.
* ``args["project_root"]`` — optional; falls back to ``ctx.project_root``
  then ``"."``.

Returns a dict with ``status`` in ``{"emitted", "awaiting_user"}``:

* ``emitted``: framework detected or plain fallback — wrote files; returns
  ``framework``, ``target_paths`` (list of str), ``artifact_path``.
* ``awaiting_user``: ambiguous package.json — wrote ``questions/design-html-
  framework-<hash>.md``; returns ``candidates``, ``question_path``,
  ``artifact_path``.

Invariants:

* Non-destructive on ambiguity: no framework source is written when a
  question.md is emitted (T-06-09 defence: never guess).
* Atomic writes throughout via :func:`clawteam.fileutil.atomic_write_text`.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.fileutil import atomic_write_text
from clawteam.templates.gstack.skills.design_html.framework_detect import (
    detect_framework,
)


# Default component name when caller omits it (designer convention — the
# chosen /design-shotgun variant is usually the hero component).
_DEFAULT_COMPONENT_NAME: str = "Hero"


def _mockup_digest(mockup_html: str) -> str:
    """SHA-256 hex digest (first 8 chars) — used in headers + question id.

    Not a security primitive — just a stable short label so repeat runs
    against the same mockup produce the same question filename (idempotent
    ambiguity resolution).
    """
    return hashlib.sha256(mockup_html.encode("utf-8")).hexdigest()[:8]


def _emit_react(src_dir: Path, component_name: str, mockup_html: str) -> Path:
    """Write ``<src_dir>/<component_name>.jsx`` and return its path.

    The emitted wrapper embeds the mockup HTML via ``dangerouslySetInnerHTML``
    as a first-pass skeleton — the designer is expected to refactor into
    idiomatic JSX after review. Per D-13 the goal is "compiles / renders
    without hand-editing", not "production ready".
    """
    target = src_dir / f"{component_name}.jsx"
    digest = _mockup_digest(mockup_html)
    content = (
        f"// Auto-emitted by /design-html ({component_name}.jsx)\n"
        f"// Source mockup digest: {digest}\n"
        "import React from 'react';\n\n"
        f"const MOCKUP_HTML = {mockup_html!r};\n\n"
        f"export default function {component_name}() {{\n"
        "  return (\n"
        "    <div dangerouslySetInnerHTML={{ __html: MOCKUP_HTML }} />\n"
        "  );\n"
        "}\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, content)
    return target


def _emit_svelte(src_dir: Path, component_name: str, mockup_html: str) -> Path:
    """Write ``<src_dir>/<component_name>.svelte`` and return its path."""
    target = src_dir / f"{component_name}.svelte"
    digest = _mockup_digest(mockup_html)
    content = (
        f"<!-- Auto-emitted by /design-html ({component_name}.svelte) -->\n"
        "<script>\n"
        f"  // Source mockup digest: {digest}\n"
        "</script>\n\n"
        f"{mockup_html}\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, content)
    return target


def _emit_vue(src_dir: Path, component_name: str, mockup_html: str) -> Path:
    """Write ``<src_dir>/<component_name>.vue`` and return its path."""
    target = src_dir / f"{component_name}.vue"
    digest = _mockup_digest(mockup_html)
    content = (
        f"<!-- Auto-emitted by /design-html ({component_name}.vue) -->\n"
        f"<!-- Source mockup digest: {digest} -->\n"
        "<template>\n"
        f"{mockup_html}\n"
        "</template>\n\n"
        "<script>\n"
        f"export default {{ name: {component_name!r} }};\n"
        "</script>\n"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, content)
    return target


def _emit_plain(project_root: Path, mockup_html: str) -> list[Path]:
    """Write the triple ``index.html`` + ``styles.css`` + ``app.js`` at project root.

    Plain-HTML fallback (no frontend framework detected). The mockup body
    lands in ``index.html`` as-is; ``styles.css`` and ``app.js`` are empty
    scaffolds the designer can fill in (Claude's discretion default per
    PLAN).
    """
    project_root.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []

    index = project_root / "index.html"
    atomic_write_text(index, mockup_html)
    paths.append(index)

    styles = project_root / "styles.css"
    atomic_write_text(styles, "/* Auto-emitted by /design-html */\n")
    paths.append(styles)

    app = project_root / "app.js"
    atomic_write_text(app, "// Auto-emitted by /design-html\n")
    paths.append(app)

    return paths


def _write_ambiguity_question(
    sprint_dir: Path,
    candidates: list[str],
    mockup_digest: str,
) -> Path:
    """Write ``<sprint_dir>/questions/design-html-framework-<digest>.md``.

    Body frontmatter matches the question-artifact shape used by
    ``/document-release`` (Phase 5 Plan 05-07 precedent) so downstream
    InteractionGate consumption is uniform.
    """
    questions_dir = sprint_dir / "questions"
    questions_dir.mkdir(parents=True, exist_ok=True)
    qid = f"design-html-framework-{mockup_digest}"
    sorted_candidates = sorted(candidates)
    bullets = "\n".join(f"- {c}" for c in sorted_candidates)
    body = (
        "---\n"
        f"question_id: {qid}\n"
        "priority: blocking\n"
        "origin_skill: /design-html\n"
        "---\n"
        "\n"
        "### Multiple frontend frameworks detected\n"
        "\n"
        "`package.json` references multiple frontend frameworks: "
        f"{', '.join(sorted_candidates)}.\n"
        "\n"
        "Which target should `/design-html` emit for?\n"
        "\n"
        f"{bullets}\n"
        "\n"
        f"Reply in `answers/{qid}.md` with a `choice: <framework>` field.\n"
    )
    q_path = questions_dir / f"{qid}.md"
    atomic_write_text(q_path, body)
    return q_path


def _write_note(
    sprint_dir: Path,
    *,
    status: str,
    framework: str,
    target_paths: list[str],
    role: str,
    sprint_id: str,
) -> Path:
    """Write ``<sprint_dir>/design-html-note.md`` summarising this invocation.

    Frontmatter keys chosen to match the loose envelope used by other
    pure-filesystem skills (no evidence-schema yet — the artifact is
    designer-facing, not gate-consumed).
    """
    sprint_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()
    lines = [
        "---",
        "artifact_type: design-html-note",
        f"status: {status!r}",
        f"framework: {framework!r}",
        f"target_paths: {target_paths!r}",
        f"sprint_id: {sprint_id!r}",
        f"created_at: {created_at!r}",
        f"persona: {role!r}",
        "step_label: design-html",
        "done: true",
        "---",
        "",
    ]
    note = sprint_dir / "design-html-note.md"
    atomic_write_text(note, "\n".join(lines) + "\n")
    return note


def design_html_handler(
    ctx: Any,
    *,
    role: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """Entry point for ``/design-html``.

    Raises
    ------
    FileNotFoundError
        If ``args["mockup_html_path"]`` does not resolve to an existing file
        (T-06-09-01 — caller passed a nonexistent / traversed path).
    """
    mockup_path = Path(args["mockup_html_path"])
    if not mockup_path.is_file():
        raise FileNotFoundError(f"mockup not found: {mockup_path}")
    mockup_html = mockup_path.read_text(encoding="utf-8")

    project_root = Path(
        args.get("project_root") or getattr(ctx, "project_root", ".")
    )
    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    sprint_id = getattr(ctx, "sprint_id", "")
    component_name = args.get("component_name") or _DEFAULT_COMPONENT_NAME

    detection = detect_framework(project_root)

    # Ambiguous — defer to user via question.md; emit NO framework source.
    if detection.ambiguous:
        digest = _mockup_digest(mockup_html)
        q_path = _write_ambiguity_question(
            sprint_dir, detection.candidates, digest,
        )
        note = _write_note(
            sprint_dir,
            status="awaiting_user",
            framework="",
            target_paths=[str(q_path)],
            role=role,
            sprint_id=sprint_id,
        )
        return {
            "status": "awaiting_user",
            "candidates": list(detection.candidates),
            "question_path": str(q_path),
            "artifact_path": str(note),
        }

    fw = detection.framework
    src_dir = (
        project_root / detection.source_root
        if detection.source_root
        else project_root
    )

    targets: list[Path] = []
    if fw == "react":
        targets.append(_emit_react(src_dir, component_name, mockup_html))
    elif fw == "svelte":
        targets.append(_emit_svelte(src_dir, component_name, mockup_html))
    elif fw == "vue":
        targets.append(_emit_vue(src_dir, component_name, mockup_html))
    else:
        # plain (or unknown label — guard belt-and-suspenders): emit triple.
        targets.extend(_emit_plain(project_root, mockup_html))
        fw = "plain"

    target_paths = [str(t) for t in targets]
    note = _write_note(
        sprint_dir,
        status="emitted",
        framework=fw,
        target_paths=target_paths,
        role=role,
        sprint_id=sprint_id,
    )
    return {
        "status": "emitted",
        "framework": fw,
        "target_paths": target_paths,
        "artifact_path": str(note),
    }


__all__ = ["design_html_handler"]
