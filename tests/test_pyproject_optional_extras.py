"""Phase 6 Wave 0 / Plan 06-01 Task 1 — pyproject.toml [browser] optional extra.

Verifies:
- `[project.optional-dependencies].browser` is declared with `playwright>=1.58,<2`.
- The pre-existing `dev` and `p2p` extras are unchanged (length + entries).
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover — Python 3.10 fallback
    try:
        import tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]


_REPO_ROOT = Path(__file__).resolve().parent.parent
_PYPROJECT = _REPO_ROOT / "pyproject.toml"


def _load_pyproject() -> dict:
    with open(_PYPROJECT, "rb") as f:
        return tomllib.load(f)


def test_browser_extra_present():
    raw = _load_pyproject()
    extras = raw["project"]["optional-dependencies"]
    assert "browser" in extras, (
        "Plan 06-01 Task 1 requires [project.optional-dependencies].browser"
    )
    assert extras["browser"] == ["playwright>=1.58,<2"], (
        f"browser extra should be exactly ['playwright>=1.58,<2']; got {extras['browser']!r}"
    )


def test_existing_extras_unchanged():
    """`dev` + `p2p` extras must not shrink, grow, or reshape.

    Pins the pre-Plan-06-01 contents verbatim so a future editor touching
    this block gets a clear signal that they're modifying substrate.
    """
    raw = _load_pyproject()
    extras = raw["project"]["optional-dependencies"]

    # dev extra — 2 entries (pytest + ruff + pyyaml = 3 total; see pyproject)
    assert "dev" in extras
    dev = extras["dev"]
    assert len(dev) == 3, f"dev extra length changed: {dev!r}"
    joined = " ".join(dev)
    assert "pytest>=9.0.0" in joined
    assert "ruff>=0.1.0" in joined
    assert "pyyaml" in joined

    # p2p extra — single entry pyzmq
    assert "p2p" in extras
    p2p = extras["p2p"]
    assert len(p2p) == 1
    assert p2p[0].startswith("pyzmq>=25.0.0")


# ── Phase 7 Wave 0 / Plan 07-01 Task 1 ──────────────────────────────────


def test_attend_extra_present():
    """Phase 7 Wave 0: [attend] optional extra must declare watchdog>=3,<4."""
    raw = _load_pyproject()
    extras = raw["project"]["optional-dependencies"]
    assert "attend" in extras, (
        "Plan 07-01 Task 1 requires [project.optional-dependencies].attend"
    )
    assert extras["attend"] == ["watchdog>=3,<4"], (
        f"attend extra should be exactly ['watchdog>=3,<4']; got {extras['attend']!r}"
    )


def test_existing_extras_unchanged_phase7():
    """Plan 07-01 Task 1: pre-Phase-7 extras (dev/p2p/browser) must not reshape."""
    raw = _load_pyproject()
    extras = raw["project"]["optional-dependencies"]

    # dev
    assert "dev" in extras
    dev = extras["dev"]
    assert len(dev) == 3, f"dev extra length changed: {dev!r}"
    joined = " ".join(dev)
    assert "pytest>=9.0.0" in joined
    assert "ruff>=0.1.0" in joined
    assert "pyyaml" in joined

    # p2p
    assert "p2p" in extras
    p2p = extras["p2p"]
    assert len(p2p) == 1
    assert p2p[0].startswith("pyzmq>=25.0.0")

    # browser (Phase 6 substrate)
    assert "browser" in extras
    assert extras["browser"] == ["playwright>=1.58,<2"]


def test_three_new_packages_importable():
    """clawteam.attention importable (clawteam.cost + clawteam.rate_limit
    removed post-v1.0 UAT 2026-04-22)."""
    import clawteam.attention  # noqa: F401
    import clawteam.attention as _att

    assert hasattr(_att, "__path__"), "clawteam.attention must be a package"
    # Plan 07-03 populated the AttentionQueue API; __all__ is non-empty now.
    assert "AttentionItem" in _att.__all__
    assert "AttentionQueue" in _att.__all__
