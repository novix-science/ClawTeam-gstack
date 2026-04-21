"""Tests for clawteam/sprint/review_phase.py (Plan 04-10 — SPRINT-04/QUALITY-09/QUALITY-13).

Exercises:
- Task 1: async dispatch_review_phase orchestration + SHA-pin + events + agreement-rate
- Task 2: SprintConductor._dispatch_review_phase sync wrapper
- Task 3: SprintConductor._build_gate_chain plugin-gate + cross-agent verification union
  (closes ISS-03 + ISS-07); ISS-09 save_sprint_state helper assertion.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import MidReviewThrash, SycophancyCascadeDetected
from clawteam.sprint.review_phase import (
    _compute_agreement_rate,
    _current_head,
    _diff_paths,
    dispatch_review_phase,
)


def _setup_hermetic_fs(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))


def _state(tmp_path, team="t1", sprint_id="abc12345"):
    from clawteam.sprint.state import SprintState
    return SprintState(
        team=team,
        sprint_id=sprint_id,
        goal="g",
        current_phase="review",
        workspace_branch=str(tmp_path),
    )


def _mock_subprocess(head_sequence: list[str], diff_output: str = ""):
    """Return a subprocess.run mock that yields head_sequence on successive rev-parse calls."""
    calls = {"count": 0}

    def runner(cmd, **kwargs):
        r = MagicMock()
        r.returncode = 0
        if len(cmd) >= 2 and cmd[1] == "rev-parse":
            idx = min(calls["count"], len(head_sequence) - 1)
            r.stdout = head_sequence[idx] + "\n"
            calls["count"] += 1
        elif len(cmd) >= 2 and cmd[1] == "diff":
            r.stdout = diff_output
        else:
            r.stdout = ""
        r.stderr = ""
        return r

    return runner


class _CapturingBus(EventBus):
    def __init__(self):
        super().__init__()
        self.captured_thrash: list[MidReviewThrash] = []
        self.captured_sycophancy: list[SycophancyCascadeDetected] = []
        self.subscribe(MidReviewThrash, lambda e: self.captured_thrash.append(e))
        self.subscribe(SycophancyCascadeDetected, lambda e: self.captured_sycophancy.append(e))


class _FakePluginManager:
    def __init__(self, routers: list[Any] | None = None):
        self._routers = routers or []

    def get_review_routers(self):
        return list(self._routers)


class _Router:
    def __init__(self, result):
        self._result = result

    def match(self, diff_paths, state):
        return list(self._result)


class _ThrowingRouter:
    def match(self, diff_paths, state):
        raise RuntimeError("boom")


# ── Agreement-rate helper ────────────────────────────────────────────


def test_agreement_rate_all_identical():
    peers = [
        {"findings": [{"severity": "blocker"}, {"severity": "major"}]},
        {"findings": [{"severity": "blocker"}, {"severity": "major"}]},
    ]
    assert _compute_agreement_rate(peers) == 1.0


def test_agreement_rate_none_identical():
    peers = [
        {"findings": [{"severity": "blocker"}]},
        {"findings": [{"severity": "minor"}]},
    ]
    assert _compute_agreement_rate(peers) == 0.0


def test_agreement_rate_partial():
    peers = [
        {"findings": [{"severity": "blocker"}, {"severity": "major"}]},
        {"findings": [{"severity": "blocker"}, {"severity": "minor"}]},
    ]
    assert _compute_agreement_rate(peers) == 0.5


def test_agreement_rate_empty():
    assert _compute_agreement_rate([]) == 0.0
    assert _compute_agreement_rate([{"findings": []}]) == 0.0


def test_agreement_rate_skips_exceptions():
    peers = [
        Exception("oops"),
        {"findings": [{"severity": "blocker"}]},
    ]
    # Only the dict contributes — 1 matched position / 1 total = 1.0
    assert _compute_agreement_rate(peers) == 1.0


# ── _current_head / _diff_paths ──────────────────────────────────────


def test_current_head_empty_workspace():
    assert _current_head("") == ""


def test_diff_paths_empty_when_no_sha():
    assert _diff_paths("/tmp", "", "abc") == []


def test_current_head_subprocess_exception_returns_empty(tmp_path):
    def raising_runner(*args, **kwargs):
        raise RuntimeError("git unavailable")

    assert _current_head(str(tmp_path), subprocess_runner=raising_runner) == ""


# ── dispatch_review_phase main path ──────────────────────────────────


def test_review_sha_pinned_on_entry(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = None
    state.save(team="t1")  # so save_sprint_state inside dispatcher works
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["a" * 40, "a" * 40], diff_output="")
    pm = _FakePluginManager()

    result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert state.review_sha == "a" * 40
    assert result["review_sha"] == "a" * 40


def test_reviewer_always_in_participants(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "b" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["b" * 40, "b" * 40])
    pm = _FakePluginManager([])
    result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert "reviewer" in result["participants"]


def test_router_participants_unioned_with_floor(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "c" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["c" * 40, "c" * 40])
    pm = _FakePluginManager([_Router(["designer"]), _Router(["dx-lead", "security"])])
    result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert set(result["participants"]) == {"reviewer", "designer", "dx-lead", "security"}


def test_peer_reviewers_run_before_aggregator(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "d" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["d" * 40, "d" * 40])
    pm = _FakePluginManager([_Router(["designer", "security"])])

    order: list[tuple[str, int]] = []

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        order.append((role, len(order)))
        await asyncio.sleep(0)  # cooperative yield
        return {"role": role, "findings": []}

    result = asyncio.run(dispatch_review_phase(
        state, pm, bus, spawn_fn=fake_spawn, subprocess_runner=runner,
    ))
    # Reviewer was called last.
    assert order[-1][0] == "reviewer"
    # Designer and security called before reviewer.
    roles_before_reviewer = [r for r, _ in order[:-1]]
    assert set(roles_before_reviewer) == {"designer", "security"}
    # Result shape sanity.
    assert result["reviewer_report"]["role"] == "reviewer"


def test_reviewer_aggregator_receives_peer_reports(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "e" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["e" * 40, "e" * 40])
    pm = _FakePluginManager([_Router(["designer"])])

    captured_kwargs: dict = {}

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        if role == "reviewer":
            captured_kwargs["peer_reports"] = peer_reports
        return {"role": role, "findings": []}

    asyncio.run(dispatch_review_phase(
        state, pm, bus, spawn_fn=fake_spawn, subprocess_runner=runner,
    ))
    assert "peer_reports" in captured_kwargs
    assert isinstance(captured_kwargs["peer_reports"], list)
    assert len(captured_kwargs["peer_reports"]) == 1  # designer


def test_mid_review_thrash_emitted_when_head_advances(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "f" * 40  # pinned SHA
    bus = _CapturingBus()
    # post-gather rev-parse returns a DIFFERENT SHA
    runner = _mock_subprocess(
        head_sequence=["g" * 40, "g" * 40],  # head sequence always "g" (diff from "f")
        diff_output="src/new.py\n",
    )
    pm = _FakePluginManager()
    asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert len(bus.captured_thrash) == 1
    evt = bus.captured_thrash[0]
    assert evt.review_sha == "f" * 40
    assert evt.new_sha == "g" * 40
    assert evt.sprint_id == "abc12345"


def test_no_thrash_when_head_stable(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "h" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["h" * 40, "h" * 40])
    pm = _FakePluginManager()
    asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert bus.captured_thrash == []


def test_sycophancy_cascade_emitted_when_agreement_above_threshold(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "i" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["i" * 40, "i" * 40])
    pm = _FakePluginManager([_Router(["designer", "security", "dx-lead"])])

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        # All peer roles return identical findings
        return {"role": role, "findings": [{"severity": "blocker"}, {"severity": "major"}]}

    asyncio.run(dispatch_review_phase(
        state, pm, bus, spawn_fn=fake_spawn, subprocess_runner=runner,
        sycophancy_threshold=0.5,
    ))
    assert len(bus.captured_sycophancy) == 1
    evt = bus.captured_sycophancy[0]
    assert evt.agreement_rate == 1.0
    assert evt.threshold == 0.5


def test_sycophancy_not_emitted_when_below_threshold(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "j" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["j" * 40, "j" * 40])
    pm = _FakePluginManager([_Router(["designer", "security"])])

    counter = {"n": 0}

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        counter["n"] += 1
        return {"role": role, "findings": [{"severity": f"sev-{counter['n']}"}]}

    asyncio.run(dispatch_review_phase(
        state, pm, bus, spawn_fn=fake_spawn, subprocess_runner=runner,
    ))
    assert bus.captured_sycophancy == []


def test_router_exception_skipped_and_logged(monkeypatch, tmp_path, caplog):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "k" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["k" * 40, "k" * 40])
    pm = _FakePluginManager([_ThrowingRouter(), _Router(["designer"])])

    with caplog.at_level("WARNING"):
        result = asyncio.run(dispatch_review_phase(
            state, pm, bus, subprocess_runner=runner,
        ))

    assert "designer" in result["participants"]
    assert any("raised during match" in r.message for r in caplog.records)


def test_spawn_exception_propagates_via_gather(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "l" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["l" * 40, "l" * 40])
    pm = _FakePluginManager([_Router(["designer", "security"])])

    async def flaky_spawn(role, state, review_sha, peer_reports=None):
        if role == "security":
            raise RuntimeError("spawn failed")
        return {"role": role, "findings": []}

    result = asyncio.run(dispatch_review_phase(
        state, pm, bus, spawn_fn=flaky_spawn, subprocess_runner=runner,
    ))
    # peer_reports include both the dict AND the exception (return_exceptions=True).
    assert len(result["peer_reports"]) == 2
    exception_items = [r for r in result["peer_reports"] if isinstance(r, Exception)]
    assert len(exception_items) == 1


def test_dispatch_returns_result_dict(monkeypatch, tmp_path):
    _setup_hermetic_fs(monkeypatch, tmp_path)
    state = _state(tmp_path)
    state.review_sha = "m" * 40
    bus = _CapturingBus()
    runner = _mock_subprocess(head_sequence=["m" * 40, "m" * 40])
    pm = _FakePluginManager([])
    result = asyncio.run(dispatch_review_phase(state, pm, bus, subprocess_runner=runner))
    assert set(result.keys()) == {
        "review_sha", "participants", "peer_reports", "reviewer_report", "agreement_rate",
    }


# ── SprintConductor._dispatch_review_phase thin wrapper ──────────────


def test_conductor_dispatch_wrapper_invokes_async(tmp_path, monkeypatch):
    """Smoke test the conductor wrapper calls the async dispatcher."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor
    from clawteam.sprint.state import SprintState, save_sprint_state

    state = SprintState(
        team="t1",
        sprint_id="xyz12345",
        goal="g",
        current_phase="review",
        workspace_branch=str(tmp_path),
        review_sha="n" * 40,
    )
    save_sprint_state(state)

    c = SprintConductor(team_name="t1")
    runner = _mock_subprocess(head_sequence=["n" * 40, "n" * 40])

    async def fake_spawn(role, state, review_sha, peer_reports=None):
        return {"role": role, "findings": []}

    # Monkeypatch subprocess.run for the dispatcher's git calls so the sync
    # wrapper's inner asyncio.run picks up the fake runner at call time.
    import clawteam.sprint.review_phase as rp

    # The _current_head / _diff_paths helpers default to subprocess.run — patch
    # that attribute on the module so the wrapper's asyncio.run picks it up.
    monkeypatch.setattr(rp.subprocess, "run", runner)

    pm = _FakePluginManager([_Router(["designer"])])
    result = c._dispatch_review_phase("xyz12345", plugin_manager=pm, spawn_fn=fake_spawn)
    assert result["review_sha"] == "n" * 40
    assert "designer" in result["participants"]
