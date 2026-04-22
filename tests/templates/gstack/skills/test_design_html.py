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


# ---------------------------------------------------------------------------
# WR-01 regression: component_name must be identifier-shaped.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_name",
    [
        "../../etc/passwd",        # POSIX traversal
        "..\\..\\conf",             # Windows traversal
        "Hero/../../evil",          # embedded traversal
        "Hero.jsx",                 # dot (would double-extension)
        "1Hero",                    # leading digit (not identifier-shaped)
        "Hero component",           # space
        "Hero;rm -rf /",            # shell metachar
        "/absolute/path",           # absolute path
        "a" * 65,                   # over 64-char limit
        "Héro",                     # non-ASCII
    ],
)
def test_handler_rejects_malicious_component_name(
    tmp_path: Path, bad_name: str
) -> None:
    project_root = tmp_path / "proj"
    sprint_dir = tmp_path / "sprint"
    _write_pkg_json(project_root, {"dependencies": {"react": "^18"}})
    mockup = _make_mockup(tmp_path / "fixtures" / "variant-1" / "index.html")

    ctx = _ctx(project_root, sprint_dir)
    with pytest.raises(ValueError, match="component_name"):
        design_html_handler(
            ctx,
            role="designer",
            args={
                "mockup_html_path": str(mockup),
                "component_name": bad_name,
            },
        )

    # No emission should have happened — filesystem stays clean except for
    # the designer's package.json we seeded.
    assert not (project_root / "src").exists()


def test_handler_accepts_valid_component_names(tmp_path: Path) -> None:
    """Lowercase, PascalCase, underscores, digits-not-leading all allowed."""
    for good_name in ("Hero", "hero", "Hero_v2", "H", "A0", "a" * 64):
        project_root = tmp_path / good_name / "proj"
        sprint_dir = tmp_path / good_name / "sprint"
        _write_pkg_json(project_root, {"dependencies": {"react": "^18"}})
        mockup = _make_mockup(
            tmp_path / good_name / "fixtures" / "index.html"
        )
        ctx = _ctx(project_root, sprint_dir)
        result = design_html_handler(
            ctx,
            role="designer",
            args={
                "mockup_html_path": str(mockup),
                "component_name": good_name,
            },
        )
        assert result["status"] == "emitted"
        assert (project_root / "src" / f"{good_name}.jsx").is_file()


# ---------------------------------------------------------------------------
# WR-02 regression: workspace_root containment (opt-in).
# ---------------------------------------------------------------------------


def test_handler_allows_paths_inside_workspace_root(tmp_path: Path) -> None:
    """When ctx.workspace_root is set, paths inside it must work."""
    workspace = tmp_path / "workspace"
    project_root = workspace / "proj"
    sprint_dir = workspace / "sprint"
    _write_pkg_json(project_root, {"dependencies": {"react": "^18"}})
    mockup = _make_mockup(workspace / "fixtures" / "variant-1" / "index.html")

    ctx = SimpleNamespace(
        project_root=str(project_root),
        sprint_dir=str(sprint_dir),
        sprint_id="sprint-0001",
        workspace_root=str(workspace),
    )
    result = design_html_handler(
        ctx,
        role="designer",
        args={
            "mockup_html_path": str(mockup),
            "component_name": "Hero",
        },
    )
    assert result["status"] == "emitted"


def test_handler_rejects_project_root_outside_workspace(tmp_path: Path) -> None:
    """project_root escaping ctx.workspace_root must raise ValueError."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_project = tmp_path / "outside_proj"
    mockup = _make_mockup(workspace / "fixtures" / "m.html")
    _write_pkg_json(outside_project, {"dependencies": {"react": "^18"}})

    ctx = SimpleNamespace(
        project_root=str(outside_project),
        sprint_dir=str(workspace / "sprint"),
        sprint_id="sprint-0001",
        workspace_root=str(workspace),
    )
    with pytest.raises(ValueError, match="project_root .* outside workspace_root"):
        design_html_handler(
            ctx,
            role="designer",
            args={
                "mockup_html_path": str(mockup),
                "component_name": "Hero",
            },
        )


def test_handler_rejects_mockup_path_outside_workspace(tmp_path: Path) -> None:
    """mockup_html_path escaping ctx.workspace_root must raise ValueError."""
    workspace = tmp_path / "workspace"
    project_root = workspace / "proj"
    _write_pkg_json(project_root, {"dependencies": {"react": "^18"}})
    # Mockup lives OUTSIDE the workspace — classic arbitrary-read attempt.
    outside_mockup = _make_mockup(tmp_path / "outside_data" / "secret.html")

    ctx = SimpleNamespace(
        project_root=str(project_root),
        sprint_dir=str(workspace / "sprint"),
        sprint_id="sprint-0001",
        workspace_root=str(workspace),
    )
    with pytest.raises(
        ValueError, match="mockup_html_path .* outside workspace_root"
    ):
        design_html_handler(
            ctx,
            role="designer",
            args={
                "mockup_html_path": str(outside_mockup),
                "component_name": "Hero",
            },
        )


def test_handler_without_workspace_root_no_containment(tmp_path: Path) -> None:
    """When ctx.workspace_root is absent, containment is opt-out (trust boundary)."""
    # Uses two unrelated directories — handler must still succeed because
    # callers without workspace_root rely on role gating (documented).
    project_root = tmp_path / "aaa" / "proj"
    sprint_dir = tmp_path / "bbb" / "sprint"
    _write_pkg_json(project_root, {"dependencies": {"react": "^18"}})
    mockup = _make_mockup(tmp_path / "ccc" / "m.html")
    ctx = _ctx(project_root, sprint_dir)  # no workspace_root
    result = design_html_handler(
        ctx,
        role="designer",
        args={
            "mockup_html_path": str(mockup),
            "component_name": "Hero",
        },
    )
    assert result["status"] == "emitted"
