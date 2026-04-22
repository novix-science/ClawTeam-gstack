"""Tests for /design-html framework detection + handler + plugin registration (Plan 06-09).

Covers SKILL-12 / D-13 per PLAN behavior (14 tests):

1-7: framework_detect.detect_framework() — react/svelte/vue, plain (no pkg, no dep),
     ambiguous (react + svelte), devDependencies scanning.
8-11: design_html_handler emission — react/svelte/vue/plain targets.
12: handler writes question.md on ambiguous detection (status=awaiting_user).
13: handler raises FileNotFoundError when mockup path missing.
14: plugin registration — /design-html present with roles={designer}.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from clawteam.templates.gstack.skills.design_html.framework_detect import (
    FrameworkDetection,
    detect_framework,
)
from clawteam.templates.gstack.skills.design_html.handler import (
    design_html_handler,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_pkg_json(project_root: Path, payload: dict[str, Any]) -> None:
    project_root.mkdir(parents=True, exist_ok=True)
    (project_root / "package.json").write_text(json.dumps(payload), encoding="utf-8")


def _make_mockup(path: Path, body: str = "<h1>Hello</h1>") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "<!doctype html><html><body>" + body + "</body></html>",
        encoding="utf-8",
    )
    return path


def _ctx(project_root: Path, sprint_dir: Path) -> Any:
    return SimpleNamespace(
        project_root=str(project_root),
        sprint_dir=str(sprint_dir),
        sprint_id="sprint-0001",
    )


# ---------------------------------------------------------------------------
# 1-7: detect_framework
# ---------------------------------------------------------------------------


def test_detect_react(tmp_path: Path) -> None:
    _write_pkg_json(tmp_path, {"dependencies": {"react": "^18.0.0"}})
    d = detect_framework(tmp_path)
    assert d.framework == "react"
    assert d.source_root == "src"
    assert d.ambiguous is False


def test_detect_svelte(tmp_path: Path) -> None:
    _write_pkg_json(tmp_path, {"dependencies": {"svelte": "^4.0.0"}})
    d = detect_framework(tmp_path)
    assert d.framework == "svelte"
    assert d.source_root == "src"
    assert d.ambiguous is False


def test_detect_vue(tmp_path: Path) -> None:
    _write_pkg_json(tmp_path, {"dependencies": {"vue": "^3.0.0"}})
    d = detect_framework(tmp_path)
    assert d.framework == "vue"
    assert d.source_root == "src"
    assert d.ambiguous is False


def test_detect_plain_no_package_json(tmp_path: Path) -> None:
    d = detect_framework(tmp_path)
    assert d.framework == "plain"
    assert d.source_root == ""
    assert d.ambiguous is False


def test_detect_plain_package_json_no_framework(tmp_path: Path) -> None:
    _write_pkg_json(tmp_path, {"dependencies": {"lodash": "^4.0.0"}})
    d = detect_framework(tmp_path)
    assert d.framework == "plain"
    assert d.ambiguous is False


def test_detect_ambiguous_react_and_svelte(tmp_path: Path) -> None:
    _write_pkg_json(
        tmp_path,
        {"dependencies": {"react": "^18", "svelte": "^4"}},
    )
    d = detect_framework(tmp_path)
    assert d.framework == ""
    assert d.ambiguous is True
    assert set(d.candidates) == {"react", "svelte"}


def test_detect_dev_deps_also_checked(tmp_path: Path) -> None:
    _write_pkg_json(tmp_path, {"devDependencies": {"react": "^18.0.0"}})
    d = detect_framework(tmp_path)
    assert d.framework == "react"


# ---------------------------------------------------------------------------
# 8-11: handler emission — one per framework.
# ---------------------------------------------------------------------------


def test_handler_react_emits_jsx(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    sprint_dir = tmp_path / "sprint"
    _write_pkg_json(project_root, {"dependencies": {"react": "^18"}})
    mockup = _make_mockup(tmp_path / "fixtures" / "variant-1" / "index.html")

    ctx = _ctx(project_root, sprint_dir)
    result = design_html_handler(
        ctx,
        role="designer",
        args={
            "mockup_html_path": str(mockup),
            "component_name": "Hero",
        },
    )

    assert result["status"] == "emitted"
    assert result["framework"] == "react"
    target = project_root / "src" / "Hero.jsx"
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert "export default function Hero" in content
    assert str(target) in result["target_paths"]


def test_handler_svelte_emits(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    sprint_dir = tmp_path / "sprint"
    _write_pkg_json(project_root, {"dependencies": {"svelte": "^4"}})
    mockup = _make_mockup(tmp_path / "fixtures" / "variant-1" / "index.html")

    ctx = _ctx(project_root, sprint_dir)
    result = design_html_handler(
        ctx,
        role="designer",
        args={
            "mockup_html_path": str(mockup),
            "component_name": "Hero",
        },
    )

    assert result["status"] == "emitted"
    assert result["framework"] == "svelte"
    target = project_root / "src" / "Hero.svelte"
    assert target.is_file()


def test_handler_vue_emits(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    sprint_dir = tmp_path / "sprint"
    _write_pkg_json(project_root, {"dependencies": {"vue": "^3"}})
    mockup = _make_mockup(tmp_path / "fixtures" / "variant-1" / "index.html")

    ctx = _ctx(project_root, sprint_dir)
    result = design_html_handler(
        ctx,
        role="designer",
        args={
            "mockup_html_path": str(mockup),
            "component_name": "Hero",
        },
    )

    assert result["status"] == "emitted"
    assert result["framework"] == "vue"
    target = project_root / "src" / "Hero.vue"
    assert target.is_file()
    # template block carries through original mockup html
    content = target.read_text(encoding="utf-8")
    assert "<template>" in content


def test_handler_plain_emits_triple(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)  # no package.json
    sprint_dir = tmp_path / "sprint"
    mockup = _make_mockup(tmp_path / "fixtures" / "variant-1" / "index.html")

    ctx = _ctx(project_root, sprint_dir)
    result = design_html_handler(
        ctx,
        role="designer",
        args={
            "mockup_html_path": str(mockup),
            "component_name": "Hero",
        },
    )

    assert result["status"] == "emitted"
    assert result["framework"] == "plain"
    assert (project_root / "index.html").is_file()
    assert (project_root / "styles.css").is_file()
    assert (project_root / "app.js").is_file()
    # sanity: all 3 paths reflected in result
    assert len(result["target_paths"]) == 3


# ---------------------------------------------------------------------------
# 12: ambiguity -> question.md + awaiting_user status.
# ---------------------------------------------------------------------------


def test_handler_ambiguous_writes_question(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    sprint_dir = tmp_path / "sprint"
    _write_pkg_json(
        project_root,
        {"dependencies": {"react": "^18", "svelte": "^4"}},
    )
    mockup = _make_mockup(tmp_path / "fixtures" / "variant-1" / "index.html")

    ctx = _ctx(project_root, sprint_dir)
    result = design_html_handler(
        ctx,
        role="designer",
        args={
            "mockup_html_path": str(mockup),
            "component_name": "Hero",
        },
    )

    assert result["status"] == "awaiting_user"
    assert set(result["candidates"]) == {"react", "svelte"}
    q_path = Path(result["question_path"])
    assert q_path.is_file()
    assert q_path.parent.name == "questions"
    body = q_path.read_text(encoding="utf-8")
    assert "react" in body and "svelte" in body
    # No framework emission when ambiguous
    assert not (project_root / "src" / "Hero.jsx").exists()
    assert not (project_root / "index.html").exists()


# ---------------------------------------------------------------------------
# 13: missing mockup path raises FileNotFoundError.
# ---------------------------------------------------------------------------


def test_handler_mockup_missing_raises(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)
    sprint_dir = tmp_path / "sprint"

    ctx = _ctx(project_root, sprint_dir)
    with pytest.raises(FileNotFoundError):
        design_html_handler(
            ctx,
            role="designer",
            args={
                "mockup_html_path": str(tmp_path / "does-not-exist.html"),
                "component_name": "Hero",
            },
        )


# ---------------------------------------------------------------------------
# 14: plugin registration — /design-html bound to designer.
# ---------------------------------------------------------------------------


def test_registered_in_plugin() -> None:
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    skills = {s.name: s for s in plugin.contribute_skills()}
    assert "/design-html" in skills
    reg = skills["/design-html"]
    assert reg.roles == frozenset({"designer"})
    assert callable(reg.handler)
