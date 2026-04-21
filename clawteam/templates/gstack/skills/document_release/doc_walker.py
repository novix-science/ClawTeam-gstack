"""Doc file walker + code-reference extractor (SKILL-16, Plan 05-07 Task 1).

Pure helpers — no git, no filesystem side effects beyond read.

Design:

* :func:`walk_docs` rglobs ``*.md`` under a root and filters out common
  dependency / build / venv directories so a docs scan does not drown in
  third-party READMEs.
* :func:`extract_code_refs` parses inline-code spans (backtick) + common
  signature patterns (``def X`` / ``function X`` / ``class X`` /
  ``export function X``) and returns a set of the path-like or
  identifier-like tokens they contain.

Regex patterns are deliberately linear-time (no nested quantifiers) to
mitigate catastrophic-backtracking DoS on attacker-crafted doc content
(threat register T-05-07-01).
"""

from __future__ import annotations

import re
from pathlib import Path


# Inline backtick-quoted code spans — single line only (``[^`\n]+``).
# Linear-time: one negated char class, no nested quantifiers.
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")

# Path-like tokens: contain at least one "/" OR end in a known source extension.
# Matches are deliberately exact-anchored via fullmatch() (NOT via ^...$).
_PATH_LIKE_RE = re.compile(
    r"[A-Za-z0-9_./\-]+(?:\.py|\.ts|\.js|\.tsx|\.jsx|\.md|\.toml|\.json|\.rs|\.go)"
)

# Identifier-like tokens: snake/camel-case alphanumeric, min 2 chars.
_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+")

# Signature patterns — captures the identifier following def/function/class.
# Supports `def foo`, `function foo`, `class Foo`, `export function foo`.
_SIGNATURE_RE = re.compile(
    r"(?:export\s+)?(?:function|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)"
)

# Common build / dependency / virtualenv dirs to skip during the walk.
_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        "node_modules",
        ".venv",
        "venv",
        ".git",
        "__pycache__",
        "dist",
        "build",
        ".tox",
        ".pytest_cache",
    }
)


def walk_docs(root: Path) -> list[Path]:
    """Return a sorted list of ``*.md`` files under ``root``.

    Paths whose ancestry includes any of :data:`_EXCLUDED_DIRS` are skipped
    so a walk over a project that has vendored deps or a Python venv does
    not explode the result set.
    """
    results: list[Path] = []
    for path in root.rglob("*.md"):
        if any(part in _EXCLUDED_DIRS for part in path.parts):
            continue
        results.append(path)
    return sorted(results)


def extract_code_refs(md_content: str) -> set[str]:
    """Extract path-like and identifier-like tokens from a doc's content.

    Two sources are merged into the returned set:

    * inline backtick spans — split on whitespace so multi-word spans like
      ``class Baz`` and ``export function bar`` yield their payload tokens.
    * signature patterns — ``def X``/``function X``/``class X`` captures
      the identifier regardless of whether it appears inside a backtick
      span (so prose narrative about an API also contributes refs).
    """
    refs: set[str] = set()
    for match in _INLINE_CODE_RE.finditer(md_content):
        token = match.group(1).strip()
        # Fast path: entire span is a single path or identifier.
        if _PATH_LIKE_RE.fullmatch(token):
            refs.add(token)
            continue
        if _IDENT_RE.fullmatch(token):
            refs.add(token)
            continue
        # Multi-word span — split + check each whitespace-delimited piece.
        for piece in token.split():
            if _PATH_LIKE_RE.fullmatch(piece):
                refs.add(piece)
            elif _IDENT_RE.fullmatch(piece):
                # Skip the leading keyword (def/class/function/export)
                if piece in {"def", "class", "function", "export"}:
                    continue
                refs.add(piece)
    for match in _SIGNATURE_RE.finditer(md_content):
        refs.add(match.group(1))
    return refs
