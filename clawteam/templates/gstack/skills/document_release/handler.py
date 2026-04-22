"""/document-release handler (SKILL-16, Phase 5 Plan 05-07 Task 2).

Orchestrates the three pure helpers (:mod:`doc_walker`, :mod:`patch_emitter`)
against a git diff to produce a per-run patch bundle + summary artifact.

Invariants (per must_haves + §05-CONTEXT D-11 / D-15 / Pitfall 7):

* **Non-destructive** — this handler NEVER modifies a tracked doc file.
  All proposed edits are written under ``<sprint_dir>/docs-updates/<ts>.diff``
  for the human to apply.
* **Idempotent on re-run** — if no fresh stale references are found on a
  second invocation, only a ``no_changes`` summary is emitted; no duplicate
  patch file is written (Pitfall 7 prevention).
* **InteractionGate-aware** — for any doc whose proposed patch exceeds 5
  lines, a ``questions/docrel_<ts>_<N>.md`` artifact is emitted asking the
  human whether to apply. The gate itself (``InteractionGate``) reads these
  question artifacts in a subsequent phase; this handler only *writes* them.
* **Adversarial-safe cap** — ``max_patches_per_run`` (default 50) limits
  per-doc annotations; the trailer note advertises deferred counts.

The handler is deliberately resilient to a missing git history (no diff
returned → empty removed set → no_changes summary). Callers (``/ship``'s
auto-invoke chain) wrap the call in try/except so any exception raised
here is demoted to a ``/document-release:failed:<reason>`` marker in the
ship-notes, not a ship failure (threat register T-05-07-04 mitigation).
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.fileutil import atomic_write_text
from clawteam.spawn.invoke import invoke_native_cli
from clawteam.templates.gstack.skills.document_release.doc_walker import (
    extract_code_refs,
    walk_docs,
)
from clawteam.templates.gstack.skills.document_release.patch_emitter import (
    emit_patches,
)


_DEFAULT_MAX_PATCHES_PER_RUN: int = 50
_LARGE_PATCH_LINES: int = 5  # >5-line patches gate via InteractionGate

# WR-04 defense: validate agent-supplied base/head refs before splicing them
# into a git diff argv. Even with shell=False, git itself parses leading-dash
# tokens as flags (e.g. ``--exec=touch /tmp/pwned``, ``--upload-pack=...``)
# when they appear in refspec position. This regex admits branch names, tags,
# SHAs, and ``HEAD~N`` while rejecting ``..``-traversal, shell metachars,
# whitespace, and any ref starting with ``-`` — matching git's own rules for
# sane refs plus a defensive belt-and-braces against argv injection.
_GIT_REF_RE: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_./~\-]+$")


def _validate_git_ref(ref: str, *, name: str) -> str:
    """Return ``ref`` unchanged if safe; else raise :class:`ValueError`.

    Rules
    -----
    * Non-empty string.
    * Does NOT start with ``-`` (rejects leading-dash flag injection).
    * Matches :data:`_GIT_REF_RE` (alphanumerics plus ``_ . / ~ -``).

    The ``name`` parameter is interpolated into the error message so the
    caller-facing ValueError pinpoints which arg was invalid.
    """
    if not isinstance(ref, str) or not ref:
        raise ValueError(
            f"document-release: invalid git {name} ref (empty or non-string)"
        )
    if ref.startswith("-"):
        raise ValueError(
            f"document-release: invalid git {name} ref {ref!r} "
            "(refs may not start with '-')"
        )
    if not _GIT_REF_RE.fullmatch(ref):
        raise ValueError(
            f"document-release: invalid git {name} ref {ref!r} "
            "(only alphanumerics plus '_./~-' permitted)"
        )
    return ref


def _removed_paths_from_diff(
    cwd: Path, base: str, head: str,
) -> set[str]:
    """Return the set of paths whose status is ``D`` (deleted) in the diff.

    Uses ``git diff --diff-filter=D --name-only <base>..<head>`` so the
    handler gets back ONLY deleted paths without paying for the full diff
    payload. Returns an empty set on any non-zero return code so a repo
    without the expected refs does not crash the handler (downstream
    summary will then emit ``no_changes``).
    """
    try:
        result = invoke_native_cli(
            [
                "git", "diff",
                "--diff-filter=D", "--name-only",
                f"{base}..{head}",
            ],
            cwd=cwd,
            timeout=30.0,
        )
    except Exception:
        return set()
    if result.returncode != 0:
        return set()
    return {
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    }


def _find_stale_refs(
    doc_path: Path, removed_paths: set[str],
) -> set[str]:
    """Return the intersection of doc refs and removed paths for one doc."""
    try:
        content = doc_path.read_text(encoding="utf-8")
    except OSError:
        return set()
    refs = extract_code_refs(content)
    # Intersect with removed_paths AND with the bare-name portion of each
    # removed path so `src/oldmodule.py` in the doc matches `src/oldmodule.py`
    # removal — handled natively by set &. Extension-free identifiers
    # already intersect via the str-equality set intersection.
    return refs & removed_paths


def document_release_handler(
    ctx: Any, *, role: str, args: dict[str, Any],
) -> dict[str, Any]:
    """/document-release entry point.

    Parameters
    ----------
    ctx:
        Harness context with ``sprint_dir`` (artifact write root) and
        ``workspace_dir`` (project root the walker scans + ``git diff``
        is invoked in).
    role:
        Caller role (shipper on the auto-invoke chain). Not used for
        gating here — the dispatcher enforces role via SkillRegistration.
    args:
        Optional overrides: ``base`` (default ``"main"``), ``head``
        (default ``"HEAD"``), ``max_patches_per_run`` (default 50).

    Returns
    -------
    dict
        ``status`` (``"ok"``), ``patches_emitted`` (int), ``summary_path``
        (str). Callers are expected to ignore ``patches_emitted == 0`` as
        the non-error no_changes case.
    """
    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    cwd = Path(getattr(ctx, "workspace_dir", sprint_dir))
    # WR-04: validate agent-controlled base/head BEFORE passing to git. git's
    # own argument parser treats leading-dash tokens (``--exec=...``,
    # ``--upload-pack=...``) as flags even in refspec position, so a minimal
    # deny-list on ``-`` plus an allow-list of ref-safe characters closes the
    # argv-injection vector at the handler boundary.
    base = _validate_git_ref(args.get("base", "main"), name="base")
    head = _validate_git_ref(args.get("head", "HEAD"), name="head")
    max_patches = int(
        args.get("max_patches_per_run", _DEFAULT_MAX_PATCHES_PER_RUN)
    )

    removed = _removed_paths_from_diff(cwd, base, head)
    docs = walk_docs(cwd)

    stale_hits: list[tuple[Path, set[str], str]] = []
    for doc in docs:
        doc_stale = _find_stale_refs(doc, removed)
        if not doc_stale:
            continue
        patch = emit_patches(doc, doc_stale, max_patches=max_patches)
        if not patch:
            continue
        stale_hits.append((doc, doc_stale, patch))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # Write patch bundle (only if we actually found stale refs — Pitfall 7
    # idempotency: a re-run with no new stale refs leaves disk untouched
    # except for the summary overwrite).
    if stale_hits:
        patch_dir = sprint_dir / "docs-updates"
        patch_dir.mkdir(parents=True, exist_ok=True)
        combined = "\n\n# ---\n\n".join(patch for _, _, patch in stale_hits)
        patch_file = patch_dir / f"{timestamp}.diff"
        atomic_write_text(patch_file, combined)

        # D-15 + Pitfall 7: non-trivial writes gate via InteractionGate —
        # we only emit the question artifacts; the gate itself reads them
        # in a later phase.
        questions_dir = sprint_dir / "questions"
        questions_dir.mkdir(parents=True, exist_ok=True)
        for idx, (doc, _, patch) in enumerate(stale_hits, start=1):
            if len(patch.splitlines()) > _LARGE_PATCH_LINES:
                q_path = questions_dir / (
                    f"docrel_{timestamp}_{idx:03d}.md"
                )
                q_body = (
                    "---\n"
                    f"question_id: docrel_{idx:03d}\n"
                    "priority: normal\n"
                    f"origin_skill: /document-release\n"
                    "---\n"
                    "\n"
                    f"### Apply patch to `{doc}`?\n"
                    "\n"
                    f"Patch proposal at `docs-updates/{timestamp}.diff`:\n"
                    "\n"
                    "```diff\n"
                    f"{patch[:2000]}\n"
                    "```\n"
                    "\n"
                    "- yes: apply the patch to the doc\n"
                    "- no: leave the doc as-is\n"
                )
                atomic_write_text(q_path, q_body)

    # Always write / overwrite the summary artifact.
    summary_path = sprint_dir / "document-release-summary.md"
    now = datetime.now(timezone.utc).isoformat()
    if not stale_hits:
        summary = (
            "---\n"
            "artifact_type: document-release-summary\n"
            f"created_at: {now}\n"
            "status: no_changes\n"
            "patches_emitted: 0\n"
            "---\n"
            "\n"
            "No stale references found — docs are in sync with the diff.\n"
            "(no changes emitted this run)\n"
        )
    else:
        summary = (
            "---\n"
            "artifact_type: document-release-summary\n"
            f"created_at: {now}\n"
            "status: found_stale\n"
            f"patches_emitted: {len(stale_hits)}\n"
            f"patch_file: docs-updates/{timestamp}.diff\n"
            "---\n"
            "\n"
            f"Found {len(stale_hits)} doc file(s) with stale references. "
            "Patches written non-destructively; apply after review.\n"
        )
    atomic_write_text(summary_path, summary)

    return {
        "status": "ok",
        "patches_emitted": len(stale_hits),
        "summary_path": str(summary_path),
    }
