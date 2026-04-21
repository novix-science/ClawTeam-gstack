"""8-fixture adversarial routing golden test (Plan 04-13 -- SPRINT-03).

Feeds each fixture diff's modified paths into GstackReviewRouter (constructed
from the loaded gstack.toml rules) and asserts the produced participants set
matches the oracle in expected_routing.json. Catches regressions like:

  * renamed UI file failing to pull designer;
  * whitespace-only README edit pulling anyone beyond the floor;
  * cross-cutting refactor producing the wrong union.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from clawteam.harness.gstack_review_router import GstackReviewRouter
from clawteam.templates import load_template


_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "review_routing"
_EXPECTED = json.loads((_FIXTURE_DIR / "expected_routing.json").read_text(encoding="utf-8"))


def _extract_paths_from_diff(diff_text: str) -> list[str]:
    """Extract modified+renamed paths from a unified git diff (handles a/ + b/ both)."""
    paths: set[str] = set()
    for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)", diff_text, re.MULTILINE):
        paths.add(m.group(1))
        paths.add(m.group(2))
    # Also handle rename from/to lines.
    for m in re.finditer(r"^rename from (\S+)", diff_text, re.MULTILINE):
        paths.add(m.group(1))
    for m in re.finditer(r"^rename to (\S+)", diff_text, re.MULTILINE):
        paths.add(m.group(1))
    return sorted(paths)


@pytest.fixture
def gstack_router() -> GstackReviewRouter:
    tmpl = load_template("gstack")
    return GstackReviewRouter(list(tmpl.review.rules))


@pytest.mark.parametrize("fixture_name,spec", list(_EXPECTED.items()))
def test_adversarial_diffs(fixture_name: str, spec: dict, gstack_router: GstackReviewRouter) -> None:
    """Each adversarial diff produces the expected participant set."""
    diff_path = _FIXTURE_DIR / f"{fixture_name}.diff"
    assert diff_path.exists(), f"missing fixture diff: {diff_path}"
    diff_text = diff_path.read_text(encoding="utf-8")
    extracted_paths = _extract_paths_from_diff(diff_text)

    # Sanity: expected_routing.json declares diff_files that should appear
    # in extracted_paths (subset check -- extraction may include a/+b/ both).
    for declared in spec["diff_files"]:
        assert declared in extracted_paths, (
            f"{fixture_name}: declared diff_file {declared!r} not in extracted paths {extracted_paths}"
        )

    state = SimpleNamespace(workspace_branch="", review_sha="")
    result = gstack_router.match(extracted_paths, state)
    assert sorted(result) == sorted(spec["expected_participants"]), (
        f"{fixture_name}: got {sorted(result)}, expected {sorted(spec['expected_participants'])} "
        f"(note: {spec.get('note', '--')})"
    )


def test_extract_paths_handles_renames() -> None:
    text = (
        "diff --git a/src/old.tsx b/src/new.tsx\n"
        "rename from src/old.tsx\n"
        "rename to src/new.tsx\n"
    )
    paths = _extract_paths_from_diff(text)
    assert "src/old.tsx" in paths
    assert "src/new.tsx" in paths


def test_extract_paths_handles_new_file() -> None:
    text = (
        "diff --git a/lib/newfile.py b/lib/newfile.py\n"
        "new file mode 100644\n"
    )
    paths = _extract_paths_from_diff(text)
    assert "lib/newfile.py" in paths


def test_all_expected_sets_contain_reviewer_floor() -> None:
    """Sanity: every adversarial case still includes reviewer floor."""
    for name, spec in _EXPECTED.items():
        assert "reviewer" in spec["expected_participants"], (
            f"{name} oracle missing reviewer floor"
        )


def test_fixture_count_is_8() -> None:
    assert len(_EXPECTED) == 8
    diff_files = list(_FIXTURE_DIR.glob("*.diff"))
    assert len(diff_files) == 8
