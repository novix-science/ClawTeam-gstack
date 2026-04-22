"""Tests for /document-release skill (Phase 5 Plan 05-07, SKILL-16).

Covers:
- Task 1 tests 1-6: pure helpers (walk_docs, extract_code_refs, emit_patches)
  — discovery, exclusions, empty inputs, cap + trailer.
- Task 2 tests 7-10: document_release_handler orchestration — happy path
  (patch file + summary), idempotent no-stale, gated large writes,
  plugin registration.

Additional ship-handler auto-invoke tests (tests 11-13) live in
``tests/test_ship_skill.py`` so the full 5-step ship pipeline continues to
share one test module (plan path ``tests/templates/gstack/skills/test_ship.py``
was aspirational — the repo convention is ``tests/test_ship_skill.py``).
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


# =========================================================================
# Task 1 — pure helpers
# =========================================================================


def test_walk_docs_finds_md_files(tmp_path):
    from clawteam.templates.gstack.skills.document_release.doc_walker import (
        walk_docs,
    )

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("# guide\n")
    (tmp_path / "docs" / "api.md").write_text("# api\n")
    (tmp_path / "README.md").write_text("# readme\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "not-a-doc.py").write_text("x = 1\n")

    result = walk_docs(tmp_path)
    assert result == [
        tmp_path / "README.md",
        tmp_path / "docs" / "api.md",
        tmp_path / "docs" / "guide.md",
    ]


def test_walk_docs_extracts_code_refs(tmp_path):
    from clawteam.templates.gstack.skills.document_release.doc_walker import (
        extract_code_refs,
    )

    md_content = (
        "# Guide\n\n"
        "See `src/foo.py` for the entry point.\n\n"
        "Call `bar` to do the thing.\n\n"
        "The `class Baz` type holds state.\n\n"
        "And we also `export function bar` from the module.\n"
    )
    refs = extract_code_refs(md_content)
    assert "src/foo.py" in refs
    assert "bar" in refs
    assert "Baz" in refs


def test_emit_patch_for_removed_file(tmp_path):
    from clawteam.templates.gstack.skills.document_release.patch_emitter import (
        emit_patches,
    )

    doc = tmp_path / "guide.md"
    doc.write_text(
        "# Guide\n\n"
        "See `src/oldmodule.py` for details.\n\n"
        "Unchanged line.\n"
    )
    patch = emit_patches(doc, {"src/oldmodule.py"})
    # Unified diff format — should reference the doc path + contain STALE marker
    assert patch != ""
    assert "src/oldmodule.py" in patch
    assert "STALE" in patch
    # Sanity: unified-diff header markers present
    assert "---" in patch
    assert "+++" in patch


def test_emit_patches_handles_empty(tmp_path):
    from clawteam.templates.gstack.skills.document_release.patch_emitter import (
        emit_patches,
    )

    doc = tmp_path / "guide.md"
    doc.write_text("# Guide\n\nSome content.\n")
    assert emit_patches(doc, set()) == ""


def test_walk_docs_respects_exclusions(tmp_path):
    from clawteam.templates.gstack.skills.document_release.doc_walker import (
        walk_docs,
    )

    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "bad.md").write_text("# bad\n")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "doc.md").write_text("# venv doc\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "real.md").write_text("# real\n")

    result = walk_docs(tmp_path)
    assert result == [tmp_path / "docs" / "real.md"]


def test_emit_patches_capped(tmp_path):
    from clawteam.templates.gstack.skills.document_release.patch_emitter import (
        emit_patches,
    )

    doc = tmp_path / "guide.md"
    # One line per ref so the matcher can find them.
    refs = {f"x_{i}" for i in range(100)}
    lines = [f"See `{ref}` here.\n" for ref in sorted(refs)]
    doc.write_text("# Guide\n\n" + "".join(lines))

    patch = emit_patches(doc, refs, max_patches=5)
    assert patch != ""
    assert "95 additional" in patch


# =========================================================================
# Task 2 — handler orchestration
# =========================================================================


@pytest.fixture()
def _dr_ctx(tmp_path):
    """A lightweight ctx with sprint_dir + workspace_dir."""
    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return SimpleNamespace(
        sprint_dir=sprint_dir,
        workspace_dir=workspace,
        sprint_id="sprint-001",
    )


def _install_fake_git_diff(
    monkeypatch, removed_paths: list[str], *, returncode: int = 0
):
    """Monkeypatch invoke_native_cli used by the handler to return fake git diff output."""
    import subprocess

    from clawteam.templates.gstack.skills.document_release import handler

    def fake_invoke(command, **kwargs):
        return subprocess.CompletedProcess(
            args=list(command),
            returncode=returncode,
            stdout="".join(p + "\n" for p in removed_paths),
            stderr="",
        )

    monkeypatch.setattr(handler, "invoke_native_cli", fake_invoke)


def test_document_release_handler_happy_path(_dr_ctx, monkeypatch):
    from clawteam.templates.gstack.skills.document_release import handler

    # Doc references the removed file. Put it INSIDE workspace_dir so walk_docs
    # picks it up (handler walks cwd = workspace_dir).
    docs_dir = _dr_ctx.workspace_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Guide\n\n"
        "See `src/oldmodule.py` for details.\n"
    )

    _install_fake_git_diff(monkeypatch, ["src/oldmodule.py"])

    out = handler.document_release_handler(_dr_ctx, role="shipper", args={})

    assert out["status"] == "ok"
    assert out["patches_emitted"] >= 1

    # docs-updates/<timestamp>.diff exists
    patch_files = list((_dr_ctx.sprint_dir / "docs-updates").glob("*.diff"))
    assert len(patch_files) == 1
    patch_body = patch_files[0].read_text()
    assert "src/oldmodule.py" in patch_body

    # document-release-summary.md exists with found_stale status
    summary = _dr_ctx.sprint_dir / "document-release-summary.md"
    assert summary.is_file()
    summary_body = summary.read_text()
    assert "found_stale" in summary_body

    # Non-destructive: docs/guide.md unchanged from our write
    guide_body = (docs_dir / "guide.md").read_text()
    assert "See `src/oldmodule.py` for details." in guide_body


def test_document_release_handler_idempotent_no_stale(_dr_ctx, monkeypatch):
    from clawteam.templates.gstack.skills.document_release import handler

    docs_dir = _dr_ctx.workspace_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text(
        "# Guide\n\nSee `src/current.py` for details.\n"
    )

    # Empty diff — nothing removed.
    _install_fake_git_diff(monkeypatch, [])

    out = handler.document_release_handler(_dr_ctx, role="shipper", args={})
    assert out["status"] == "ok"
    assert out["patches_emitted"] == 0

    # Summary says "no changes"
    summary_body = (_dr_ctx.sprint_dir / "document-release-summary.md").read_text()
    assert "no changes" in summary_body.lower() or "no_changes" in summary_body

    # No patch files emitted
    patch_dir = _dr_ctx.sprint_dir / "docs-updates"
    assert not patch_dir.exists() or not list(patch_dir.glob("*.diff"))


def test_document_release_handler_large_writes_gated(_dr_ctx, monkeypatch):
    from clawteam.templates.gstack.skills.document_release import handler

    docs_dir = _dr_ctx.workspace_dir / "docs"
    docs_dir.mkdir()
    # Build a doc with many stale refs so the emitted patch has >5 lines
    removed = [f"src/removed_{i}.py" for i in range(15)]
    body_lines = ["# Guide\n", "\n"]
    for ref in removed:
        body_lines.append(f"Reference to `{ref}` here.\n")
    (docs_dir / "guide.md").write_text("".join(body_lines))

    _install_fake_git_diff(monkeypatch, removed)

    handler.document_release_handler(_dr_ctx, role="shipper", args={})

    # questions/<N>.md written asking "Apply patch to"
    questions_dir = _dr_ctx.sprint_dir / "questions"
    assert questions_dir.is_dir()
    q_files = list(questions_dir.glob("*.md"))
    assert q_files, "expected at least one question artifact for a large diff"
    q_body = q_files[0].read_text()
    assert "Apply patch to" in q_body
    # Doc path (or its filename) must appear in the question
    assert "guide.md" in q_body

    # Patch file still emitted (human answers later)
    patch_files = list((_dr_ctx.sprint_dir / "docs-updates").glob("*.diff"))
    assert patch_files, "patch file should still be emitted alongside question"


def test_document_release_registered():
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    regs = GstackSprintPlugin().contribute_skills()
    names = {s.name for s in regs}
    assert "/document-release" in names

    dr_reg = next(s for s in regs if s.name == "/document-release")
    assert dr_reg.roles == frozenset({"shipper"})


# =========================================================================
# WR-04 regression: agent-controlled base/head args are validated BEFORE
# being spliced into a git diff argv. git itself parses leading-dash tokens
# (--exec=, --upload-pack=) as flags even in refspec position, so a minimal
# allow-list closes the argv-injection vector at the handler boundary.
# =========================================================================


def test_base_ref_leading_dash_rejected(_dr_ctx, monkeypatch):
    """Leading-dash base ref must ValueError BEFORE invoking git."""
    from clawteam.templates.gstack.skills.document_release import handler

    invoke_called = {"n": 0}

    def fake_invoke(command, **kwargs):  # noqa: ARG001
        invoke_called["n"] += 1
        import subprocess
        return subprocess.CompletedProcess(
            args=list(command), returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(handler, "invoke_native_cli", fake_invoke)

    with pytest.raises(ValueError, match="document-release.*base"):
        handler.document_release_handler(
            _dr_ctx, role="shipper",
            args={"base": "--exec=touch /tmp/pwned"},
        )
    # Critical: git was NEVER invoked with the malicious ref.
    assert invoke_called["n"] == 0


def test_head_ref_leading_dash_rejected(_dr_ctx, monkeypatch):
    """Leading-dash head ref must ValueError BEFORE invoking git."""
    from clawteam.templates.gstack.skills.document_release import handler

    invoke_called = {"n": 0}

    def fake_invoke(command, **kwargs):  # noqa: ARG001
        invoke_called["n"] += 1
        import subprocess
        return subprocess.CompletedProcess(
            args=list(command), returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(handler, "invoke_native_cli", fake_invoke)

    with pytest.raises(ValueError, match="document-release.*head"):
        handler.document_release_handler(
            _dr_ctx, role="shipper",
            args={"head": "--upload-pack=/bin/sh"},
        )
    assert invoke_called["n"] == 0


def test_ref_shell_metachar_rejected(_dr_ctx, monkeypatch):
    """Shell metachars (space / ; / $ / |) in a ref must ValueError."""
    from clawteam.templates.gstack.skills.document_release import handler

    def fake_invoke(command, **kwargs):  # noqa: ARG001
        import subprocess
        return subprocess.CompletedProcess(
            args=list(command), returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(handler, "invoke_native_cli", fake_invoke)

    for bad_ref in (
        "main; rm -rf /",
        "main && echo pwned",
        "main | cat",
        "main`id`",
        "main$(id)",
        "main with spaces",
        "",
    ):
        with pytest.raises(ValueError):
            handler.document_release_handler(
                _dr_ctx, role="shipper", args={"base": bad_ref},
            )


def test_normal_refs_pass_validation(_dr_ctx, monkeypatch):
    """Branch names, tags, SHAs, and HEAD~N must all pass validation."""
    from clawteam.templates.gstack.skills.document_release import handler

    docs_dir = _dr_ctx.workspace_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("# guide\n")

    invoked_refs: list[str] = []

    def fake_invoke(command, **kwargs):  # noqa: ARG001
        # Capture the refspec we were called with.
        import subprocess
        for arg in command:
            if ".." in arg and isinstance(arg, str) and arg.count("..") == 1:
                invoked_refs.append(arg)
        return subprocess.CompletedProcess(
            args=list(command), returncode=0, stdout="", stderr="",
        )

    monkeypatch.setattr(handler, "invoke_native_cli", fake_invoke)

    for base, head in (
        ("main", "HEAD"),
        ("feature/x", "HEAD~3"),
        ("v1.2.3", "v1.2.4"),
        ("abc1234", "def5678"),
        ("release/2026.04", "HEAD"),
        ("my_branch-name", "HEAD"),
    ):
        invoked_refs.clear()
        out = handler.document_release_handler(
            _dr_ctx, role="shipper", args={"base": base, "head": head},
        )
        # Handler completes without raising.
        assert out["status"] == "ok"
        # git diff was invoked with the intended refspec.
        assert invoked_refs == [f"{base}..{head}"]


def test_default_args_still_work(_dr_ctx, monkeypatch):
    """Default base='main' / head='HEAD' must remain valid."""
    from clawteam.templates.gstack.skills.document_release import handler

    _install_fake_git_diff(monkeypatch, [])
    out = handler.document_release_handler(_dr_ctx, role="shipper", args={})
    assert out["status"] == "ok"
