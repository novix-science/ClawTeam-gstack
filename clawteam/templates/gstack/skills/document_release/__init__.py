"""/document-release skill (SKILL-16, Phase 5 Plan 05-07).

Diff-vs-docs cross-reference: walks `docs/` + root `*.md`, cross-references
against git diff, detects stale references (removed exports, renamed files,
changed signatures), and emits unified-diff patch proposals to
``docs-updates/<ISO-8601>.diff``.

NEVER writes docs directly. Non-trivial writes (>5 lines in any single doc
patch) are InteractionGate-gated via ``questions/docrel_*.md`` artifacts.
"""

from clawteam.templates.gstack.skills.document_release.doc_walker import (
    extract_code_refs,
    walk_docs,
)
from clawteam.templates.gstack.skills.document_release.patch_emitter import (
    emit_patches,
)

__all__ = [
    "document_release_handler",
    "extract_code_refs",
    "emit_patches",
    "walk_docs",
]


def __getattr__(name: str):
    """Lazy-import handler to avoid import-order cycles with /ship's
    auto-invoke path (``ship.handler`` imports ``document_release_handler``
    inside its try/except)."""
    if name == "document_release_handler":
        from clawteam.templates.gstack.skills.document_release.handler import (
            document_release_handler as _h,
        )
        return _h
    raise AttributeError(f"module 'document_release' has no attribute {name!r}")
