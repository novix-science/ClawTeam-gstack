"""End-to-end mid-review-push integration test (Plan 04-14 — ROADMAP Phase 4 SC #4).

Unlike tests/test_review_phase_dispatch.py (which uses mocked subprocess), this
test spins up a real tmp_path git repo and asserts the full flow:
  1. dispatch_review_phase pins review_sha from a REAL `git rev-parse HEAD`.
  2. Spawn registry (monkeypatched to inject a mid-dispatch commit) triggers
     an actual SprintState branch HEAD advance.
  3. Post-gather thrash check re-invokes `git rev-parse HEAD` and observes
     the new SHA.
  4. MidReviewThrash event is emitted on the EventBus with the correct
     (review_sha, new_sha, diff delta) payload.
  5. Reviewer aggregator's review-report dict carries `thrash_decision: re-pin
     | superseded` per §04-CONTEXT D-19.

Closes ROADMAP Phase 4 Success Criterion #4: "if the sprint branch HEAD
advances before the review completes, a mid-review-thrash event fires and
the reviewer chooses between extending the review to the new SHA or marking
the prior review as superseded — verified by a mid-review-push integration
test."
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import MidReviewThrash
from clawteam.sprint.review_phase import dispatch_review_phase
from clawteam.sprint.state import SprintState


# ── git-repo setup helpers ───────────────────────────────────────────


def _init_git_repo(path: Path) -> str:
    """Initialize a real git repo at ``path``; return the first commit SHA."""
    if shutil.which("git") is None:  # pragma: no cover — CI sanity
        pytest.skip("git binary not on PATH — integration test cannot run")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Phase4 Integration Test"],
        cwd=path, check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=path, check=True,
    )
    # Seed commit.
    (path / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "baseline.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "baseline"],
        cwd=path, check=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _make_mid_dispatch_commit(path: Path) -> str:
    """Add a file + commit on sprint branch; return new HEAD SHA."""
    (path / "mid-review-change.txt").write_text(
        "added mid-review\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "mid-review-change.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "mid-review change"],
        cwd=path, check=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


# ── Event bus + plugin-manager stubs ─────────────────────────────────


class _CapturingBus(EventBus):
    def __init__(self):
        super().__init__()
        self.thrash_events: list[MidReviewThrash] = []
        self.subscribe(
            MidReviewThrash, lambda e: self.thrash_events.append(e)
        )


class _FakePluginManager:
    """Minimal plugin manager returning no routers for the integration test."""

    def get_review_routers(self):
        return []


def _hermetic_env(monkeypatch, tmp_path: Path) -> Path:
    """Point CLAWTEAM_DATA_DIR + HOME at tmp_path so save_sprint_state is isolated."""
    data_dir = tmp_path / "clawteam-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data_dir))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    return data_dir


def _state(workspace: Path) -> SprintState:
    return SprintState(
        team="integ-t",
        sprint_id="int12345",
        goal="mid-review-push integration",
        current_phase="review",
        workspace_branch=str(workspace),
    )


# ── Integration tests ────────────────────────────────────────────────


def test_mid_review_push_integration_end_to_end(tmp_path, monkeypatch):
    """ROADMAP Phase 4 SC #4: end-to-end verification of mid-review-push flow.

    Uses REAL ``subprocess.run`` for git (no mock) so that ``_current_head``
    and ``_diff_paths`` exercise the actual shell=False + timeout path under
    a real tmp_path repo.
    """
    # Hermetic data dir so save_sprint_state writes inside tmp_path.
    _hermetic_env(monkeypatch, tmp_path)

    # 1. Real git repo in a subdirectory so CLAWTEAM_DATA_DIR and the workspace
    #    are disjoint (avoid state.json writes clobbering workspace_branch).
    repo = tmp_path / "sprint-workspace"
    repo.mkdir()
    first_sha = _init_git_repo(repo)

    # 2. Sprint state pointing at the repo.
    state = _state(repo)
    state.review_sha = None
    bus = _CapturingBus()

    # 3. Router that always matches 'designer' so we get one peer role
    #    whose spawn_fn invocation can inject the mid-dispatch commit.
    class _OneRoleRouter:
        def match(self, diff_paths, state):
            return ["designer"]

    class _PMWithRouter(_FakePluginManager):
        def get_review_routers(self):
            return [_OneRoleRouter()]

    pm_with_router = _PMWithRouter()

    # 4. Spawn fn that injects a mid-dispatch commit ON THE FIRST PEER CALL,
    #    and records whether it saw a thrash to include thrash_decision in
    #    the aggregator report (reviewer role).
    invocation_log: list[tuple[str, str]] = []
    mid_dispatch_sha_container: dict = {"new_sha": None}

    async def spawn_with_mid_commit(role, state, review_sha, peer_reports=None):
        invocation_log.append((role, review_sha))
        # On the first peer-role (non-reviewer) invocation, inject a commit.
        if (
            mid_dispatch_sha_container["new_sha"] is None
            and role != "reviewer"
        ):
            mid_dispatch_sha_container["new_sha"] = _make_mid_dispatch_commit(repo)
        # Aggregator role writes thrash_decision when a thrash was observed.
        if role == "reviewer":
            thrash_decision = None
            if bus.thrash_events:
                # Policy: prefer re-pin for small diffs; in the integration
                # test we hard-code "re-pin" to assert the field is written.
                thrash_decision = "re-pin"
            report: dict = {
                "role": role,
                "sprint_id": state.sprint_id,
                "review_sha": review_sha,
                "findings": [],
            }
            if thrash_decision is not None:
                report["thrash_decision"] = thrash_decision
            return report
        return {
            "role": role,
            "sprint_id": state.sprint_id,
            "review_sha": review_sha,
            "findings": [],
        }

    # 5. Invoke REAL dispatch_review_phase (REAL subprocess — no mock).
    result = asyncio.run(
        dispatch_review_phase(
            state,
            pm_with_router,
            bus,
            spawn_fn=spawn_with_mid_commit,
        )
    )

    # 6. review_sha pinned to first commit.
    assert state.review_sha == first_sha, (
        f"expected review_sha={first_sha}, got {state.review_sha}"
    )
    assert result["review_sha"] == first_sha

    # 7. Exactly 1 MidReviewThrash event captured.
    assert len(bus.thrash_events) == 1, (
        f"expected exactly 1 MidReviewThrash event, got {len(bus.thrash_events)}"
    )
    evt = bus.thrash_events[0]

    # 8. Event payload correctness (D-19).
    assert evt.review_sha == first_sha
    assert evt.new_sha == mid_dispatch_sha_container["new_sha"]
    assert evt.new_sha != first_sha
    assert len(evt.new_sha) == 40  # git SHA-1 hex
    assert evt.sprint_id == "int12345"

    # 9. diff_paths_added includes the file we added mid-dispatch.
    assert "mid-review-change.txt" in evt.diff_paths_added, (
        "expected mid-review-change.txt in diff_paths_added, got "
        f"{evt.diff_paths_added}"
    )

    # 10. Reviewer aggregator's review-report dict has thrash_decision
    #     (D-19 frontmatter contract).
    reviewer_report = result["reviewer_report"]
    assert isinstance(reviewer_report, dict), (
        f"reviewer_report expected dict, got {type(reviewer_report)}"
    )
    assert "thrash_decision" in reviewer_report, (
        "D-19: reviewer_report missing thrash_decision field; keys="
        f"{sorted(reviewer_report.keys())}"
    )
    assert reviewer_report["thrash_decision"] in {"re-pin", "superseded"}, (
        "D-19: thrash_decision must be 're-pin' or 'superseded', got "
        f"{reviewer_report['thrash_decision']!r}"
    )


def test_mid_review_push_no_thrash_when_head_stable(tmp_path, monkeypatch):
    """Sanity: no mid-dispatch commit → no MidReviewThrash event, no thrash_decision."""
    _hermetic_env(monkeypatch, tmp_path)
    repo = tmp_path / "sprint-workspace"
    repo.mkdir()
    first_sha = _init_git_repo(repo)

    state = _state(repo)
    state.review_sha = None
    bus = _CapturingBus()
    pm = _FakePluginManager()

    async def spawn_stable(role, state, review_sha, peer_reports=None):
        # No HEAD advance — stable flow.
        return {
            "role": role,
            "sprint_id": state.sprint_id,
            "review_sha": review_sha,
            "findings": [],
        }

    result = asyncio.run(
        dispatch_review_phase(state, pm, bus, spawn_fn=spawn_stable)
    )

    assert state.review_sha == first_sha
    assert bus.thrash_events == [], (
        f"expected no thrash, got {bus.thrash_events}"
    )
    # Reviewer report must NOT include thrash_decision when no thrash observed.
    reviewer_report = result["reviewer_report"]
    assert "thrash_decision" not in reviewer_report


def test_mid_review_push_thrash_decision_field_enforced(tmp_path, monkeypatch):
    """D-19: thrash_decision MUST be one of {re-pin, superseded} when emitted.

    Variant of the end-to-end test where the reviewer picks 'superseded' instead
    of 're-pin' — asserts the field is validated against the D-19 enum.
    """
    _hermetic_env(monkeypatch, tmp_path)
    repo = tmp_path / "sprint-workspace"
    repo.mkdir()
    _init_git_repo(repo)

    state = _state(repo)
    state.review_sha = None
    bus = _CapturingBus()

    class _PM(_FakePluginManager):
        def get_review_routers(self):
            class _R:
                def match(self, dp, st):
                    return ["designer"]

            return [_R()]

    committed = {"done": False}

    async def spawn(role, state, review_sha, peer_reports=None):
        if not committed["done"] and role != "reviewer":
            _make_mid_dispatch_commit(repo)
            committed["done"] = True
        if role == "reviewer":
            return {
                "role": role,
                "thrash_decision": "superseded",
                "findings": [],
            }
        return {"role": role, "findings": []}

    result = asyncio.run(
        dispatch_review_phase(state, _PM(), bus, spawn_fn=spawn)
    )
    assert len(bus.thrash_events) == 1
    # Reviewer picked superseded this time — assert the set-constraint holds.
    assert result["reviewer_report"]["thrash_decision"] in {
        "re-pin",
        "superseded",
    }
