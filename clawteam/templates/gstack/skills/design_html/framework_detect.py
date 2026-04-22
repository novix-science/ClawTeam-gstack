"""Framework detection from ``package.json`` (SKILL-12 / D-13).

Pure function — no I/O beyond reading ``<project_root>/package.json``. Returns
a :class:`FrameworkDetection` dataclass that the handler consumes to decide
which emission path to take.

Detection rules (D-13):

1. No ``package.json`` → ``framework="plain"`` (ambiguous=False).
2. Exactly one of ``{react, svelte, vue}`` in ``dependencies`` OR
   ``devDependencies`` → that framework, with ``source_root="src"``.
3. Two or more present → ``ambiguous=True`` with ``candidates`` populated;
   handler writes a ``question.md`` artifact rather than guessing.
4. None of ``{react, svelte, vue}`` present → ``framework="plain"``.

Malformed JSON / unreadable file is downgraded to the plain-HTML fallback
(threat register T-06-09-03 mitigation: info-disclosure-by-crash).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Detection order per D-13. Ordering only matters for the single-framework
# case (we return the first matching key); the multi-framework case surfaces
# every candidate for the user question.
_FRAMEWORK_KEYS: tuple[str, ...] = ("react", "svelte", "vue")


@dataclass
class FrameworkDetection:
    """Result of :func:`detect_framework`.

    Attributes
    ----------
    framework:
        One of ``"react"``, ``"svelte"``, ``"vue"``, ``"plain"``, or ``""``
        (empty when ``ambiguous=True``).
    source_root:
        Relative path (within project_root) where the handler should write
        the emitted source. ``"src"`` for detected frameworks; ``""`` for
        plain HTML (write at project root) or ambiguous (no write).
    ambiguous:
        ``True`` iff more than one of ``{react, svelte, vue}`` appears in
        the combined dependency set. Handler writes a question.md instead
        of emitting in this case.
    candidates:
        Populated only when ``ambiguous=True``; lists the detected
        framework names (unordered set cast to list for serialisability).
    """

    framework: str = ""
    source_root: str = ""
    ambiguous: bool = False
    candidates: list[str] = field(default_factory=list)


def _read_package_json(project_root: Path) -> dict | None:
    """Return parsed ``package.json`` dict, or ``None`` if missing / malformed.

    Any failure mode (absent file, unreadable, JSON decode error) returns
    ``None`` so the caller treats it as "no package.json → plain HTML".
    This is the T-06-09-03 mitigation — we never raise on malformed deps.
    """
    pkg = project_root / "package.json"
    if not pkg.is_file():
        return None
    try:
        parsed = json.loads(pkg.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _collect_all_deps(pkg: dict) -> set[str]:
    """Union of ``dependencies`` + ``devDependencies`` keys.

    Per D-13 both buckets count — a React dep in ``devDependencies`` still
    indicates the project's frontend framework (common for component-library
    repos where React is a peer / dev dep).
    """
    deps: set[str] = set()
    raw_deps = pkg.get("dependencies")
    if isinstance(raw_deps, dict):
        deps.update(raw_deps.keys())
    raw_dev = pkg.get("devDependencies")
    if isinstance(raw_dev, dict):
        deps.update(raw_dev.keys())
    return deps


def detect_framework(project_root: Path) -> FrameworkDetection:
    """Detect the frontend framework by inspecting ``package.json`` deps.

    Parameters
    ----------
    project_root:
        Filesystem path to the project root (the directory containing
        ``package.json``, if any).

    Returns
    -------
    FrameworkDetection
        See class docstring for fields. Always returns a concrete dataclass
        (never raises).
    """
    pkg = _read_package_json(project_root)
    if pkg is None:
        return FrameworkDetection(
            framework="plain", source_root="", ambiguous=False,
        )

    deps = _collect_all_deps(pkg)
    present = [k for k in _FRAMEWORK_KEYS if k in deps]

    if not present:
        return FrameworkDetection(
            framework="plain", source_root="", ambiguous=False,
        )
    if len(present) == 1:
        return FrameworkDetection(
            framework=present[0], source_root="src", ambiguous=False,
        )
    return FrameworkDetection(
        framework="",
        source_root="",
        ambiguous=True,
        candidates=list(present),
    )


__all__ = ["FrameworkDetection", "detect_framework"]
