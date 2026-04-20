"""Tests for clawteam.harness.evidence_gate — 4-check protocol.

Plan 02-07: EvidenceGate extends ArtifactRequiredGate and validates content
(frontmatter + stub + post-check dispatch) in addition to presence.

Covers §02-CONTEXT D-01..D-05 + D-28 and §02-RESEARCH Pitfalls #4 / #6 / #10.

All 13 tests fail at RED with ``ModuleNotFoundError`` until Plan 02-07 Task 2
ships ``clawteam/harness/evidence_gate.py``.
"""

from __future__ import annotations

import subprocess
from urllib.error import URLError

import pytest

from clawteam.harness.evidence_gate import (
    EvidenceGate,  # noqa: F401 — import triggers ModuleNotFound at RED
)
from clawteam.harness.evidence_schemas import (
    ArtifactFrontmatterBase,
    register_schema,
    reset_registry,
)
from clawteam.sprint.state import SprintState

# ── Test-local schema fixtures (Phase 3 ships the real subclasses) ─────────


class DesignDocFixture(ArtifactFrontmatterBase):
    artifact_type: str = "design-doc"


class ReportTestFixture(ArtifactFrontmatterBase):
    artifact_type: str = "test-report"
    test_command: str = ""


class ShipNotesFixture(ArtifactFrontmatterBase):
    artifact_type: str = "ship-notes"
    deploy_url: str = ""


# ── Shared fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def hermetic(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_registry()
    yield tmp_path
    reset_registry()


def _state(hermetic, artifacts: dict[str, str]) -> SprintState:
    workspace = hermetic / "work"
    workspace.mkdir(parents=True, exist_ok=True)
    return SprintState(
        sprint_id="s1sprint",
        goal="x",
        team="team1",
        current_phase="plan",
        artifacts=artifacts,
        created_at="2026-04-17T00:00:00Z",
        workspace_branch=str(workspace),
    )


def _design_doc_artifact(body: str = "ok content " * 40) -> str:
    """Emit a well-formed design-doc artifact with ample body bytes and no stub markers."""
    return (
        "---\n"
        "persona: designer\n"
        "step_label: plan:1/1\n"
        "done: true\n"
        "artifact_type: design-doc\n"
        'created_at: "2026-04-17T00:00:00Z"\n'
        "---\n"
        f"{body}\n"
    )


# ── Layer 1: presence (§02-CONTEXT D-01 / inherited from ArtifactRequiredGate) ──


def test_presence_check_preserved(hermetic):
    """Missing artifact → same shape as ArtifactRequiredGate."""
    register_schema("design-doc", DesignDocFixture)
    gate = EvidenceGate(["design-doc.md"])
    state = _state(hermetic, artifacts={})
    ok, reason = gate.check(state)
    assert ok is False
    assert "design-doc.md" in reason
    assert "Missing" in reason


# ── Layer 2: frontmatter + schema (§02-CONTEXT D-02 / Pitfall #6) ─────────


def test_layer1_frontmatter_required_fields(hermetic):
    """Missing ``persona`` in frontmatter fails the schema-validation pass."""
    register_schema("design-doc", DesignDocFixture)
    artifact = (
        "---\n"
        "step_label: plan:1/1\n"
        "done: true\n"
        "artifact_type: design-doc\n"
        'created_at: "2026-04-17T00:00:00Z"\n'
        "---\n"
        "body content " * 40
    )
    gate = EvidenceGate(["design-doc.md"])
    state = _state(hermetic, artifacts={"design-doc.md": artifact})
    ok, reason = gate.check(state)
    assert ok is False
    assert "persona" in reason.lower()


def test_unregistered_artifact_type_error(hermetic):
    """Pitfall #6: unregistered artifact_type returns an explicit Phase 3 hint."""
    artifact = (
        "---\n"
        "persona: engineer\n"
        "step_label: plan:1/1\n"
        "done: true\n"
        "artifact_type: random-thing\n"
        'created_at: "2026-04-17T00:00:00Z"\n'
        "---\n"
        "body content " * 40
    )
    gate = EvidenceGate(["design-doc.md"])
    state = _state(hermetic, artifacts={"design-doc.md": artifact})
    ok, reason = gate.check(state)
    assert ok is False
    assert "random-thing" in reason
    assert "Phase 3 plugin must register" in reason


# ── Layer 3: stub detection (§02-CONTEXT D-03) ────────────────────────────


def test_layer2_stub_section_detected(hermetic):
    """A required ## section with body ≤ 100 bytes is a stub → fail."""
    register_schema("design-doc", DesignDocFixture)
    # Purpose body is short; Scope body is long. Required sections = ["Purpose", "Scope"].
    body = "## Purpose\ntiny\n## Scope\n" + ("ok content " * 40) + "\n"
    artifact = (
        "---\n"
        "persona: designer\n"
        "step_label: plan:1/1\n"
        "done: true\n"
        "artifact_type: design-doc\n"
        'created_at: "2026-04-17T00:00:00Z"\n'
        "---\n"
        f"{body}"
    )
    gate = EvidenceGate(
        ["design-doc.md"],
        required_sections={"design-doc.md": ["Purpose", "Scope"]},
    )
    state = _state(hermetic, artifacts={"design-doc.md": artifact})
    ok, reason = gate.check(state)
    assert ok is False
    assert "Purpose" in reason
    assert "stub" in reason.lower()


def test_layer3_blacklist_hit_tbd(hermetic):
    """Body containing the literal `TBD` fails with a line number."""
    register_schema("design-doc", DesignDocFixture)
    body = (
        "line one with enough content to avoid section-length failures later\n"
        "line two also sufficiently long to not trip length rules if any\n"
        "line three contains a TBD marker that should be rejected\n"
    )
    artifact = (
        "---\n"
        "persona: designer\n"
        "step_label: plan:1/1\n"
        "done: true\n"
        "artifact_type: design-doc\n"
        'created_at: "2026-04-17T00:00:00Z"\n'
        "---\n"
        f"{body}"
    )
    gate = EvidenceGate(["design-doc.md"])
    state = _state(hermetic, artifacts={"design-doc.md": artifact})
    ok, reason = gate.check(state)
    assert ok is False
    assert "TBD" in reason
    # Line number lookup (§02-CONTEXT D-03): the blacklist marker reason must
    # include the line where the token was found.
    assert any(str(n) in reason for n in (1, 2, 3, 4))


def test_layer3_blacklist_hit_todo_placeholder_lorem(hermetic):
    """Each of TODO / placeholder / Lorem ipsum also trips the blacklist."""
    register_schema("design-doc", DesignDocFixture)
    for marker in ("TODO", "placeholder", "Lorem ipsum"):
        body = "sufficient preamble text to survive any section-body floor\n"
        body += f"this body contains a {marker} token that should be rejected\n"
        artifact = (
            "---\n"
            "persona: designer\n"
            "step_label: plan:1/1\n"
            "done: true\n"
            "artifact_type: design-doc\n"
            'created_at: "2026-04-17T00:00:00Z"\n'
            "---\n"
            f"{body}"
        )
        gate = EvidenceGate(["design-doc.md"])
        state = _state(hermetic, artifacts={"design-doc.md": artifact})
        ok, reason = gate.check(state)
        assert ok is False, f"expected blacklist fail for marker={marker!r}"
        assert marker.split()[0].lower() in reason.lower(), (
            f"reason {reason!r} should name the blacklisted marker {marker!r}"
        )


# ── Layer 4a: test_command re-run + cache (§02-CONTEXT D-04 / Pitfall #4) ──


def _test_report_artifact(test_command: str = "pytest tests/foo.py -x") -> str:
    body = "ok content body " * 12 + "\n"
    return (
        "---\n"
        "persona: qa\n"
        "step_label: test:1/1\n"
        "done: true\n"
        "artifact_type: test-report\n"
        'created_at: "2026-04-17T00:00:00Z"\n'
        f"test_command: {test_command}\n"
        "---\n"
        f"{body}"
    )


def test_test_report_reruns_test_command(hermetic):
    """Gate runs subprocess with shell=False + cwd=workspace_branch + timeout=300."""
    register_schema("test-report", ReportTestFixture)

    calls: list[dict] = []

    def fake_runner(cmd, cwd, timeout):
        calls.append({"cmd": cmd, "cwd": cwd, "timeout": timeout})
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    gate = EvidenceGate(
        ["test-report.md"],
        subprocess_runner=fake_runner,
    )
    state = _state(hermetic, artifacts={"test-report.md": _test_report_artifact()})
    ok, reason = gate.check(state)
    assert ok, f"expected pass, got ({ok}, {reason!r})"
    assert len(calls) == 1
    assert calls[0]["cwd"] == state.workspace_branch
    assert calls[0]["timeout"] == 300
    # Pitfall #4: shell=False is enforced via default_runner; here we assert the
    # cmd was passed as a list (i.e. not a shell string).
    assert isinstance(calls[0]["cmd"], list)


def test_test_report_cache_hit_skips_rerun(hermetic):
    """Second invocation with identical artifact content skips subprocess."""
    register_schema("test-report", ReportTestFixture)
    calls: list[dict] = []

    def fake_runner(cmd, cwd, timeout):
        calls.append({"cmd": cmd, "cwd": cwd, "timeout": timeout})
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    gate = EvidenceGate(["test-report.md"], subprocess_runner=fake_runner)
    state = _state(hermetic, artifacts={"test-report.md": _test_report_artifact()})
    ok1, _ = gate.check(state)
    ok2, _ = gate.check(state)
    assert ok1 and ok2
    assert len(calls) == 1  # second call was cache-hit

    # Cache file lives under $CLAWTEAM_DATA_DIR/teams/<team>/sprints/<id>/
    cache_path = (
        hermetic / "teams" / state.team / "sprints" / state.sprint_id / "test_verify_cache.json"
    )
    assert cache_path.exists()


def test_test_report_exit_1_fails_gate(hermetic):
    """Non-zero exit code from runner → (False, reason with exit code)."""
    register_schema("test-report", ReportTestFixture)

    def fake_runner(cmd, cwd, timeout):
        return subprocess.CompletedProcess(
            args=cmd, returncode=1, stdout="", stderr="test failed\n"
        )

    gate = EvidenceGate(["test-report.md"], subprocess_runner=fake_runner)
    state = _state(hermetic, artifacts={"test-report.md": _test_report_artifact()})
    ok, reason = gate.check(state)
    assert ok is False
    assert "test-report.md" in reason
    assert "exited with code 1" in reason
    assert "test failed" in reason


def test_test_report_timeout_fails_gate(hermetic):
    """subprocess.TimeoutExpired from runner → (False, 'timed out after 300s')."""
    register_schema("test-report", ReportTestFixture)

    def fake_runner(cmd, cwd, timeout):
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    gate = EvidenceGate(["test-report.md"], subprocess_runner=fake_runner)
    state = _state(hermetic, artifacts={"test-report.md": _test_report_artifact()})
    ok, reason = gate.check(state)
    assert ok is False
    assert "test-report.md" in reason
    assert "timed out" in reason.lower()
    assert "300" in reason


# ── Layer 4b: deploy_url HEAD dereference (§02-CONTEXT D-05 / Pitfall #10) ──


def _ship_notes_artifact(deploy_url: str = "https://example.test/app") -> str:
    body = "ok content body " * 12 + "\n"
    return (
        "---\n"
        "persona: shipper\n"
        "step_label: ship:1/1\n"
        "done: true\n"
        "artifact_type: ship-notes\n"
        'created_at: "2026-04-17T00:00:00Z"\n'
        f"deploy_url: {deploy_url}\n"
        "---\n"
        f"{body}"
    )


def test_ship_notes_deploy_url_2xx_passes(hermetic):
    register_schema("ship-notes", ShipNotesFixture)

    def fake_checker(url, timeout):
        return 200, {"Content-Type": "text/html"}

    gate = EvidenceGate(["ship-notes.md"], deploy_url_checker=fake_checker)
    state = _state(hermetic, artifacts={"ship-notes.md": _ship_notes_artifact()})
    ok, reason = gate.check(state)
    assert ok, f"expected pass, got ({ok}, {reason!r})"


def test_ship_notes_deploy_url_non2xx_fails(hermetic):
    register_schema("ship-notes", ShipNotesFixture)

    def fake_checker(url, timeout):
        return 404, {}

    gate = EvidenceGate(["ship-notes.md"], deploy_url_checker=fake_checker)
    state = _state(hermetic, artifacts={"ship-notes.md": _ship_notes_artifact()})
    ok, reason = gate.check(state)
    assert ok is False
    assert "ship-notes.md" in reason
    assert "404" in reason


def test_ship_notes_deploy_url_default_checker_offline_safety(hermetic):
    """Pitfall #10: injected checker raising URLError surfaces as an unreachable reason."""
    register_schema("ship-notes", ShipNotesFixture)

    def fake_checker(url, timeout):
        raise URLError("connection refused")

    gate = EvidenceGate(["ship-notes.md"], deploy_url_checker=fake_checker)
    state = _state(hermetic, artifacts={"ship-notes.md": _ship_notes_artifact()})
    ok, reason = gate.check(state)
    assert ok is False
    assert "unreachable" in reason.lower()
    assert "connection refused" in reason
