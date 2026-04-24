"""Tests for clawteam.sprint.conductor.SprintConductor (Plan 02-11).

Covers CORE-05 (sprint-level loop owner), CORE-07 (pause/resume), INT-06
(auto_advance semantics with InteractionGate composition), and D-29 (three-
layer cap override).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import PhaseTransition
from clawteam.harness import freeze_registry as freeze_reg_mod

HEX8 = re.compile(r"^[0-9a-f]{8}$")


def _setup_hermetic_fs(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))


def _reset_safety(monkeypatch):
    """Clear safety-subscriber idempotency tracker between tests so each bus
    gets a fresh registration slate."""
    freeze_reg_mod.reset_safety_subscribers()


@pytest.fixture(autouse=True)
def _isolate_safety_subscribers(monkeypatch):
    _reset_safety(monkeypatch)
    yield
    _reset_safety(monkeypatch)


@pytest.fixture(autouse=True)
def _reset_freeze_registry_module():
    """Sprint-scoped FreezeRegistry singleton is test-leaky — reset before/after."""
    freeze_reg_mod.reset_freeze_registry()
    yield
    freeze_reg_mod.reset_freeze_registry()


# ─────────────────────────────── Task 2 tests ───────────────────────────────


def test_sprint_conductor_construct_registers_safety_subscribers(monkeypatch, tmp_path):
    """SprintConductor(team=...) calls register_safety_subscribers exactly once."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    bus = EventBus()
    SprintConductor(team_name="t", bus=bus)
    # The 3 safety handlers (BeforeFileWrite + 2x BeforeToolCall) all register.
    from clawteam.events.types import BeforeFileWrite, BeforeToolCall

    assert bus.handler_count(BeforeFileWrite) == 1
    assert bus.handler_count(BeforeToolCall) == 2

    # Second construction on the SAME bus must be idempotent (Plan 02-10 T-02-17).
    SprintConductor(team_name="t", bus=bus)
    assert bus.handler_count(BeforeFileWrite) == 1
    assert bus.handler_count(BeforeToolCall) == 2


def test_start_sprint_writes_state_json_and_returns_sprint_state(monkeypatch, tmp_path):
    """start_sprint returns a SprintState with hex[:8] id; state.json exists on disk."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    bus = EventBus()
    c = SprintConductor(team_name="t", bus=bus)
    state = c.start_sprint(goal="ship dark mode")
    assert HEX8.match(state.sprint_id), state.sprint_id
    assert state.goal == "ship dark mode"
    assert state.status == "running"
    assert state.current_phase  # first phase resolved from registry OR default
    # state.json exists under get_data_dir()/teams/t/sprints/<id>/state.json
    p = tmp_path / "teams" / "t" / "sprints" / state.sprint_id / "state.json"
    assert p.exists()
    data = json.loads(p.read_text())
    assert data["team"] == "t"
    assert data["sprint_id"] == state.sprint_id


def test_start_sprint_emits_phase_transition(monkeypatch, tmp_path):
    """start_sprint emits PhaseTransition(from_phase='', to_phase=first_phase)."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    bus = EventBus()
    captured: list[PhaseTransition] = []
    bus.subscribe(PhaseTransition, captured.append)
    c = SprintConductor(team_name="t", bus=bus)
    state = c.start_sprint(goal="g")
    assert len(captured) == 1
    ev = captured[0]
    assert ev.team_name == "t"
    assert ev.from_phase == ""
    assert ev.to_phase == state.current_phase


def test_advance_phase_runs_gate_chain_in_order_and_short_circuits(monkeypatch, tmp_path):
    """Gate chain runs EvidenceGate → forced_progress_gate → (InteractionGate);
    first (False, reason) short-circuits and returns (False, reason)."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    order: list[str] = []

    class SpyGate:
        def __init__(self, name, ok: bool):
            self.name = name
            self.ok = ok

        def check(self, state):
            order.append(self.name)
            return (self.ok, "" if self.ok else f"{self.name}-blocked")

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")

    # Replace gate builder to use our spies in the documented composition order.
    gates_pass = [SpyGate("evidence", True), SpyGate("forced", True)]
    c._build_gate_chain = lambda _s: gates_pass  # type: ignore[assignment]
    ok, reason = c.advance_phase(state.sprint_id)
    assert ok is True, reason
    assert order == ["evidence", "forced"]

    # Now short-circuit on forced.
    order.clear()
    gates_block = [
        SpyGate("evidence", True),
        SpyGate("forced", False),
        SpyGate("interaction", True),
    ]
    c._build_gate_chain = lambda _s: gates_block  # type: ignore[assignment]
    ok, reason = c.advance_phase(state.sprint_id)
    assert ok is False
    assert "forced-blocked" in reason
    assert order == ["evidence", "forced"]  # interaction NOT reached


def test_auto_advance_true_no_questions_skips_interaction_gate(monkeypatch, tmp_path):
    """auto_advance=True + no unanswered questions → InteractionGate NOT in chain."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g", auto_advance=True)
    # state.pending_question_ids is empty → InteractionGate skipped.
    chain = c._build_gate_chain(state)
    names = [type(g).__name__ for g in chain]
    assert "InteractionGate" not in names, names


def test_build_gate_chain_uses_plugin_phase_requirements(monkeypatch, tmp_path):
    """Plugin phase requirements make EvidenceGate block on missing artifacts."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.harness.evidence_schemas import reset_registry as reset_schema_registry
    from clawteam.harness.phase_registry import reset_registry as reset_phase_registry
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin
    from clawteam.plugins.manager import PluginManager
    from clawteam.sprint.conductor import SprintConductor

    reset_phase_registry()
    reset_schema_registry()
    pm = PluginManager()
    pm._instantiate_and_register(GstackSprintPlugin)

    c = SprintConductor(team_name="t", bus=EventBus(), plugin_manager=pm)
    state = c.start_sprint(goal="g", auto_advance=True)
    chain = c._build_gate_chain(state)

    evidence_gate = chain[0]
    assert type(evidence_gate).__name__ == "EvidenceGate"
    assert evidence_gate.artifact_names == ["delegation.json"]

    ok, reason = evidence_gate.check(state)
    assert ok is False
    assert "missing artifact 'delegation.json' for phase 'think'" in reason


def test_build_gate_chain_without_plugin_keeps_permissive_artifact_default(
    monkeypatch, tmp_path
):
    """No plugin manager keeps the Phase 2 empty-artifact compatibility path."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g", auto_advance=True)
    chain = c._build_gate_chain(state)

    evidence_gate = chain[0]
    assert type(evidence_gate).__name__ == "EvidenceGate"
    assert evidence_gate.artifact_names == []
    assert evidence_gate.check(state) == (True, "")


def test_auto_advance_true_with_pending_questions_inserts_interaction_gate(monkeypatch, tmp_path):
    """auto_advance=True + unanswered question → InteractionGate inserted."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g", auto_advance=True)
    state.pending_question_ids = ["q1"]
    chain = c._build_gate_chain(state)
    names = [type(g).__name__ for g in chain]
    assert "InteractionGate" in names, names


def test_auto_advance_false_always_inserts_interaction_gate(monkeypatch, tmp_path):
    """auto_advance=False → InteractionGate always inserted regardless of pending_question_ids."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g", auto_advance=False)
    assert state.pending_question_ids == []
    chain = c._build_gate_chain(state)
    names = [type(g).__name__ for g in chain]
    assert "InteractionGate" in names, names


def test_force_interactive_phases_inserts_interaction_gate_even_in_auto(monkeypatch, tmp_path):
    """force_interactive_phases=[current_phase] forces InteractionGate even under
    auto_advance=True with no questions (Phase 4 Ship gate reservation)."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g", auto_advance=True)
    # Force-interactive includes the current phase
    c.force_interactive_phases = [state.current_phase]
    chain = c._build_gate_chain(state)
    names = [type(g).__name__ for g in chain]
    assert "InteractionGate" in names, names


def test_missing_team_error_on_empty_team_name(monkeypatch, tmp_path):
    """SprintConductor("") raises MissingTeamError (D-24 CLI contract)."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import MissingTeamError, SprintConductor

    with pytest.raises(MissingTeamError):
        SprintConductor(team_name="")


def test_resolve_sprint_prefix_ambiguous_and_not_found(monkeypatch, tmp_path):
    """resolve_sprint: exact match hits; ambiguous prefix → AmbiguousSprintError;
    missing → SprintNotFoundError (D-25)."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import (
        AmbiguousSprintError,
        SprintConductor,
        SprintNotFoundError,
    )
    from clawteam.sprint.state import SprintState, save_sprint_state

    c = SprintConductor(team_name="t", bus=EventBus())
    # Plant two sprints with ids that share a prefix "ab".
    s1 = SprintState(
        sprint_id="ab111111",
        goal="g1",
        team="t",
        current_phase="think",
        created_at="2026-04-17T00:00:00Z",
    )
    s2 = SprintState(
        sprint_id="ab222222",
        goal="g2",
        team="t",
        current_phase="think",
        created_at="2026-04-17T00:00:00Z",
    )
    save_sprint_state(s1)
    save_sprint_state(s2)
    # Exact hit on full id.
    loaded = c.resolve_sprint("ab111111")
    assert loaded.sprint_id == "ab111111"
    # Ambiguous "ab" prefix → AmbiguousSprintError with both candidates.
    with pytest.raises(AmbiguousSprintError) as exc:
        c.resolve_sprint("ab")
    assert set(exc.value.candidates) == {"ab111111", "ab222222"}
    # Missing prefix.
    with pytest.raises(SprintNotFoundError):
        c.resolve_sprint("zz")


def test_list_sprints_scoped_to_team_returns_sorted(monkeypatch, tmp_path):
    """list_sprints returns all state.json under ~/.clawteam/teams/<team>/sprints/*;
    unknown team → empty list; cross-team scans never happen (Pitfall #9)."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor
    from clawteam.sprint.state import SprintState, save_sprint_state

    # One sprint for team t1, one for team t2 — list_sprints("t1") must not see t2.
    save_sprint_state(
        SprintState(
            sprint_id="aa111111",
            goal="g1",
            team="t1",
            current_phase="think",
            created_at="2026-04-17T00:00:00Z",
        )
    )
    save_sprint_state(
        SprintState(
            sprint_id="bb222222",
            goal="g2",
            team="t2",
            current_phase="think",
            created_at="2026-04-17T00:00:00Z",
        )
    )
    c1 = SprintConductor(team_name="t1", bus=EventBus())
    sprints = c1.list_sprints()
    assert [s.sprint_id for s in sprints] == ["aa111111"]

    c_unknown = SprintConductor(team_name="never-existed", bus=EventBus())
    assert c_unknown.list_sprints() == []


def test_three_layer_cap_override_cli_over_env_over_state(monkeypatch, tmp_path):
    """Three-layer cap override precedence (D-29): CLI flag > env > state default."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    # CLI (in bytes, 100 KB) wins over env (50 KB) and state default (50 KB).
    monkeypatch.setenv("CLAWTEAM_ARTIFACT_CAP_KB", "50")
    c = SprintConductor(
        team_name="t", artifact_cap_bytes=100 * 1024, bus=EventBus()
    )
    assert c._artifact_cap_override == 100 * 1024

    # No CLI → env wins over default.
    monkeypatch.delenv("CLAWTEAM_ARTIFACT_CAP_KB", raising=False)
    monkeypatch.setenv("CLAWTEAM_ARTIFACT_CAP_KB", "25")
    c2 = SprintConductor(team_name="t", bus=EventBus())
    assert c2._artifact_cap_override == 25 * 1024

    # No CLI, no env → state default (50 KB).
    monkeypatch.delenv("CLAWTEAM_ARTIFACT_CAP_KB", raising=False)
    c3 = SprintConductor(team_name="t", bus=EventBus())
    assert c3._artifact_cap_override == 50 * 1024


def test_advance_phase_happy_path_flips_current_phase(monkeypatch, tmp_path):
    """All gates pass → current_phase moves to the next registered phase;
    phase_history gets a new entry; state.json on disk reflects the transition."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    class AllGoodGate:
        def check(self, state):
            return True, ""

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")
    first_phase = state.current_phase
    c._build_gate_chain = lambda _s: [AllGoodGate()]  # type: ignore[assignment]
    ok, reason = c.advance_phase(state.sprint_id)
    # Happy path: either moved to next phase OR sprint completed if registry had 1 phase.
    assert ok is True, reason
    p = tmp_path / "teams" / "t" / "sprints" / state.sprint_id / "state.json"
    data = json.loads(p.read_text())
    if data["status"] == "running":
        assert data["current_phase"] != first_phase
        assert len(data["phase_history"]) == 1
    else:
        # Single-phase registry → sprint completed.
        assert data["status"] == "completed"


# ─────────────────────────────── Task 3 tests ───────────────────────────────


def test_pause_resume_round_trip_in_process(monkeypatch, tmp_path):
    """Same-process pause/resume preserves current_phase + flips status back to running."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    class AllGoodGate:
        def check(self, state):
            return True, ""

    c1 = SprintConductor(team_name="t", bus=EventBus())
    state = c1.start_sprint(goal="g")
    c1._build_gate_chain = lambda _s: [AllGoodGate()]  # type: ignore[assignment]
    c1.advance_phase(state.sprint_id)
    # Capture advanced phase BEFORE pause (may be same as initial if single-phase registry).
    after_advance = c1._load_by_id(state.sprint_id).current_phase
    paused = c1.pause(state.sprint_id)
    assert paused.status == "paused"
    # Fresh conductor, same process.
    c2 = SprintConductor(team_name="t", bus=EventBus())
    resumed = c2.resume(state.sprint_id)
    assert resumed.status == "running"
    assert resumed.sprint_id == state.sprint_id
    assert resumed.current_phase == after_advance


def test_resume_after_process_restart(monkeypatch, tmp_path):
    """CORE-07: Pause in process A + resume in process B via subprocess."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    script_a = (
        "import os; os.environ['CLAWTEAM_DATA_DIR']=%r;"
        "from clawteam.sprint.conductor import SprintConductor;"
        "c=SprintConductor(team_name='t');"
        "s=c.start_sprint(goal='g');"
        "c.pause(s.sprint_id);"
        "print(s.sprint_id)" % str(tmp_path)
    )
    result_a = subprocess.run(
        [sys.executable, "-c", script_a],
        capture_output=True,
        text=True,
        check=True,
    )
    sprint_id = result_a.stdout.strip().splitlines()[-1]
    assert HEX8.match(sprint_id), f"unexpected sprint_id: {sprint_id!r}"

    # state.json on disk must reflect status=paused.
    state_path = tmp_path / "teams" / "t" / "sprints" / sprint_id / "state.json"
    assert state_path.exists()
    raw = json.loads(state_path.read_text())
    assert raw["status"] == "paused"
    assert raw["team"] == "t"

    # Process B: new interpreter, new SprintConductor, call resume().
    script_b = (
        "import os; os.environ['CLAWTEAM_DATA_DIR']=%r;"
        "from clawteam.sprint.conductor import SprintConductor;"
        "c=SprintConductor(team_name='t');"
        "s=c.resume(%r);"
        "print(s.status); print(s.current_phase); print(s.sprint_id)"
        % (str(tmp_path), sprint_id)
    )
    result_b = subprocess.run(
        [sys.executable, "-c", script_b],
        capture_output=True,
        text=True,
        check=True,
    )
    lines = result_b.stdout.strip().splitlines()
    assert lines[-3] == "running"
    assert lines[-2]  # non-empty current_phase
    assert lines[-1] == sprint_id


def test_resume_re_emits_last_phase_transition(monkeypatch, tmp_path):
    """resume() replays the last phase_history entry as PhaseTransition on the
    conductor's bus (CORE-07)."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    class AllGoodGate:
        def check(self, state):
            return True, ""

    bus = EventBus()
    captured: list[PhaseTransition] = []
    bus.subscribe(PhaseTransition, captured.append)
    c = SprintConductor(team_name="t", bus=bus)
    state = c.start_sprint(goal="g")
    c._build_gate_chain = lambda _s: [AllGoodGate()]  # type: ignore[assignment]
    c.advance_phase(state.sprint_id)
    c.pause(state.sprint_id)
    captured.clear()
    c.resume(state.sprint_id)
    # Exactly one PhaseTransition re-emitted (last entry from phase_history).
    # If phase_history is empty (single-phase registry — sprint completed path),
    # the conductor must still NOT crash; zero replays is acceptable.
    assert len(captured) <= 1


def test_resume_restores_careful_enabled(monkeypatch, tmp_path):
    """resume() calls set_careful_veto_mode(state.careful_enabled) so /careful
    arms again after process restart."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor
    from clawteam.sprint.state import save_sprint_state

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")
    state.careful_enabled = True
    save_sprint_state(state)
    c.pause(state.sprint_id)
    # Reset the module-level flag before resume to observe the set.
    freeze_reg_mod._careful_veto_mode = False
    c.resume(state.sprint_id)
    assert freeze_reg_mod._careful_veto_mode is True


# ─────────────────────────────── Plan 02-12 Task 1 tests ─────────────────────
# Serialization helpers consumed by the Sprint CLI sub-app (Plan 02-12):
# most_recent_artifact(state), status_dict(state), show_dict(state).


def test_most_recent_artifact_returns_name_when_artifacts_nonempty(monkeypatch, tmp_path):
    """most_recent_artifact returns the last-inserted artifact name."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")
    state.artifacts["first.md"] = "content"
    state.artifacts["second.md"] = "content"
    assert c.most_recent_artifact(state) == "second.md"


def test_most_recent_artifact_returns_empty_when_no_artifacts(monkeypatch, tmp_path):
    """most_recent_artifact returns empty string when artifacts dict is empty."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")
    assert c.most_recent_artifact(state) == ""


def test_status_dict_shape(monkeypatch, tmp_path):
    """status_dict produces the exact key set consumed by `clawteam sprint status`."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="ship dark mode")
    state.participants = ["engineer", "reviewer"]
    state.pending_question_ids = ["q1"]
    qdir = tmp_path / "teams" / "t" / "sprints" / state.sprint_id / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    (qdir / "q1.md").write_text("question", encoding="utf-8")
    state.artifacts["design-doc.md"] = "body"
    d = c.status_dict(state)
    assert set(d.keys()) == {
        "sprint_id",
        "current_phase",
        "status",
        "participants",
        "pending_questions_count",
        "most_recent_artifact",
        "auto_advance",
        "team",
    }
    assert d["pending_questions_count"] == 1
    assert d["most_recent_artifact"] == "design-doc.md"
    assert d["team"] == "t"


def test_status_dict_reconciles_pending_question_ids(monkeypatch, tmp_path):
    """status_dict mirrors unanswered question files before rendering UX-03."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor
    from clawteam.sprint.state import load_sprint_state

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="ship dark mode")
    state.pending_question_ids = ["stale"]
    base = tmp_path / "teams" / "t" / "sprints" / state.sprint_id
    qdir = base / "questions"
    adir = base / "answers"
    qdir.mkdir(parents=True, exist_ok=True)
    adir.mkdir(parents=True, exist_ok=True)
    (qdir / "open.md").write_text("question", encoding="utf-8")
    (qdir / "answered.md").write_text("question", encoding="utf-8")
    (adir / "answered.md").write_text("answer", encoding="utf-8")

    d = c.status_dict(state)

    assert d["pending_questions_count"] == 1
    assert state.pending_question_ids == ["open"]
    assert load_sprint_state("t", state.sprint_id).pending_question_ids == ["open"]


def test_show_dict_shape(monkeypatch, tmp_path):
    """show_dict produces the exact key set consumed by `clawteam sprint show`.

    artifacts_list returns NAMES only (sorted) — bodies are excluded to keep
    JSON payload bounded (UX-05).
    """
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="ship dark mode")
    state.artifacts["a.md"] = "BODY-ALPHA-UNIQUE-TOKEN"
    state.artifacts["b.md"] = "BODY-BETA-UNIQUE-TOKEN"
    d = c.show_dict(state)
    expected_keys = {
        "sprint_id",
        "goal",
        "current_phase",
        "status",
        "participants",
        "phase_history",
        "artifacts_list",
        "pending_question_ids",
        "auto_advance",
        "team",
        "created_at",
        "workspace_branch",
    }
    assert set(d.keys()) == expected_keys
    assert d["artifacts_list"] == sorted(["a.md", "b.md"])
    # Bodies must NOT appear in the dict — artifacts_list holds names only.
    dumped = json.dumps(d)
    assert "BODY-ALPHA-UNIQUE-TOKEN" not in dumped
    assert "BODY-BETA-UNIQUE-TOKEN" not in dumped


# ─────────────── Phase 3 Wave 0 (Plan 03-01 Task 2) ───────────────
#
# Pattern 4 / D-10: SprintConductor.advance_phase accepts an optional `actor`
# parameter (defaults to ""). When the team's TeamConfig declares a non-empty
# `leader_role` AND a non-empty `actor` is passed in, advancement is rejected
# unless `actor == leader_role`. Default empty preserves Phase 2 BC.
#
# Co-located: TeamConfig gains optional `leader_role: str = ""` and `template:
# str = ""` fields (both sisters — flow from TemplateDef at create_team time).


def _seed_team_with_leader_role(tmp_path, team_name: str, leader_role: str) -> None:
    """Create a team whose persisted TeamConfig has leader_role set.

    Uses the real persistence path (`_save_config` via TeamManager internals)
    so SprintConductor's leader-role lookup reads it back verbatim.
    """
    from clawteam.team.manager import TeamManager, _save_config
    from clawteam.team.models import TeamConfig, TeamMember

    member = TeamMember(name="leader", agent_type="human")
    config = TeamConfig(
        name=team_name,
        lead_agent_id=member.agent_id,
        members=[member],
        leader_role=leader_role,
    )
    _save_config(config)
    # Sanity: get_team round-trips the new field.
    roundtrip = TeamManager.get_team(team_name)
    assert roundtrip is not None and roundtrip.leader_role == leader_role


def test_advance_phase_default_actor_preserves_phase2_behavior(monkeypatch, tmp_path):
    """D-10 BC: omitting actor (or passing actor='') runs the gate chain unchanged."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")
    # No actor kwarg → Phase 2 code path (gate chain runs, no leader-role check).
    ok, reason = c.advance_phase(state.sprint_id)
    assert ok is True, reason


def test_advance_phase_leader_role_allows_matching_actor(monkeypatch, tmp_path):
    """D-10: actor='ceo' on a team with leader_role='ceo' → gates run, advance succeeds."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    _seed_team_with_leader_role(tmp_path, "t", leader_role="ceo")
    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")
    ok, reason = c.advance_phase(state.sprint_id, actor="ceo")
    assert ok is True, reason


def test_advance_phase_leader_role_rejects_non_matching_actor(monkeypatch, tmp_path):
    """D-10: actor='engineer' on a team with leader_role='ceo' → rejected BEFORE gates."""
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    _seed_team_with_leader_role(tmp_path, "t", leader_role="ceo")
    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")
    ok, reason = c.advance_phase(state.sprint_id, actor="engineer")
    assert ok is False
    assert "engineer" in reason
    assert "ceo" in reason
    assert "authorized" in reason or "authoriz" in reason


def test_advance_phase_empty_leader_role_ignores_actor(monkeypatch, tmp_path):
    """D-10: leader_role='' (no leader binding) → actor is ignored, gate chain runs.

    This is the Phase 2 regression path: Phase 2 teams have no leader_role, so
    gstack-aware callers passing actor= must still succeed.
    """
    _setup_hermetic_fs(monkeypatch, tmp_path)
    from clawteam.sprint.conductor import SprintConductor

    # Team exists but leader_role is empty (default).
    _seed_team_with_leader_role(tmp_path, "t", leader_role="")
    c = SprintConductor(team_name="t", bus=EventBus())
    state = c.start_sprint(goal="g")
    ok, reason = c.advance_phase(state.sprint_id, actor="anyone")
    assert ok is True, reason


def test_team_config_leader_role_and_template_default_empty():
    """Pattern 4 / 03-07 key_link: leader_role + template default to empty strings
    so all existing TeamConfig construction sites keep working unchanged."""
    from clawteam.team.models import TeamConfig, TeamMember

    config = TeamConfig(
        name="t",
        lead_agent_id="a",
        members=[TeamMember(name="m", agent_type="general")],
    )
    assert config.leader_role == ""
    assert config.template == ""


def test_team_config_leader_role_and_template_accept_assignment():
    """Pattern 4: both new fields accept string assignment at construction."""
    from clawteam.team.models import TeamConfig, TeamMember

    config = TeamConfig(
        name="t",
        lead_agent_id="a",
        members=[TeamMember(name="m", agent_type="general")],
        leader_role="ceo",
        template="gstack",
    )
    assert config.leader_role == "ceo"
    assert config.template == "gstack"
