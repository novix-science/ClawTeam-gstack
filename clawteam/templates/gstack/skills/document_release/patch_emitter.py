"""Unified-diff patch emitter for stale doc references (SKILL-16, Plan 05-07).

Non-destructive: this module NEVER rewrites a doc on disk. It reads the
original doc, computes a candidate doc body with ``<!-- STALE: ... -->``
markers prepended to lines that mention refs that have been removed, and
returns the ``difflib.unified_diff`` representation as a string.

Adversarial-safety: caps the number of ref annotations applied per call at
``max_patches`` (default 50) so a pathological diff that removes thousands
of files does not produce a memory-blowing patch artifact (threat register
T-05-07-05). When refs exceed the cap, a trailer ``# NOTE: N additional
stale refs deferred`` line is appended so the summary can advertise re-run
semantics for completeness.
"""

from __future__ import annotations

import difflib
from pathlib import Path


def emit_patches(
    doc_path: Path,
    stale_refs: set[str],
    *,
    max_patches: int = 50,
) -> str:
    """Emit a unified-diff patch string for ``stale_refs`` in ``doc_path``.

    Parameters
    ----------
    doc_path:
        Existing markdown file to propose edits against.
    stale_refs:
        Identifiers / paths that appeared in the doc but were removed in
        the caller's diff context. Empty set → returns empty string.
    max_patches:
        Upper bound on the number of stale-ref annotations applied in a
        single call. When ``len(stale_refs) > max_patches`` a trailer note
        is appended advertising the deferred count.

    Returns
    -------
    str
        Unified-diff string (including ``---``/``+++`` file markers) when
        at least one annotation was applied; empty string otherwise.
    """
    if not stale_refs:
        return ""

    original_text = doc_path.read_text()
    original_lines = original_text.splitlines(keepends=True)

    deferred = max(0, len(stale_refs) - max_patches)
    sorted_refs = sorted(stale_refs)[:max_patches]

    new_lines = list(original_lines)
    changed = False
    for ref in sorted_refs:
        # Annotate the FIRST line that mentions this ref; a ref mentioned in
        # multiple lines gets one marker per call (subsequent re-runs will
        # find fresh lines if any still linger).
        for idx, line in enumerate(new_lines):
            if ref not in line:
                continue
            # Do not double-mark a line we already annotated in a previous
            # iteration of this same call.
            if line.lstrip().startswith("<!-- STALE:"):
                continue
            marker = (
                f"<!-- STALE: `{ref}` was removed/renamed in this PR -->\n"
            )
            new_lines[idx] = marker + line
            changed = True
            break

    if not changed:
        return ""

    diff = "".join(
        difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=str(doc_path),
            tofile=str(doc_path) + ".proposed",
            n=2,
        )
    )

    if deferred:
        diff += (
            f"\n# NOTE: {deferred} additional stale refs deferred; "
            "re-run /document-release to continue.\n"
        )
    return diff
