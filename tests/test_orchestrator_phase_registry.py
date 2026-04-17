"""Tests for HarnessOrchestrator ↔ PhaseRegistry integration (RFC 001 §4.6, D-02)."""

from __future__ import annotations

from clawteam.harness.orchestrator import HarnessOrchestrator
from clawteam.harness.phase_registry import get_registry, reset_registry
from clawteam.harness.phases import DEFAULT_PHASE_ROLES, DEFAULT_PHASES
from clawteam.sprint.state import SprintState


def _hermetic(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))


def test_orchestrator_consumes_registry_phases_when_phases_is_none(monkeypatch, tmp_path):
    """Plugin-registered phases flow into PhaseState.phases when phases=None."""
    _hermetic(monkeypatch, tmp_path)
    reset_registry()
    try:
        get_registry().register(
            "test-plugin",
            ["alpha", "beta", "gamma"],
            {"alpha": ["pm"], "beta": ["engineer"]},
            [],
        )
        orch = HarnessOrchestrator(team_name="t", phases=None)
        assert orch.state.phases == ["alpha", "beta", "gamma"]
    finally:
        reset_registry()


def test_orchestrator_falls_back_to_default_phases_when_registry_empty(monkeypatch, tmp_path):
    """Empty registry + phases=None → DEFAULT_PHASES (Phase 0 BC guarantee)."""
    _hermetic(monkeypatch, tmp_path)
    reset_registry()
    try:
        orch = HarnessOrchestrator(team_name="t", phases=None)
        assert orch.state.phases == list(DEFAULT_PHASES)
    finally:
        reset_registry()


def test_orchestrator_explicit_phases_argument_wins_over_registry(monkeypatch, tmp_path):
    """Explicit phases arg takes precedence over any registry contribution."""
    _hermetic(monkeypatch, tmp_path)
    reset_registry()
    try:
        get_registry().register("p", ["from-registry"], {}, [])
        orch = HarnessOrchestrator(team_name="t", phases=["caller", "supplied"])
        assert orch.state.phases == ["caller", "supplied"]
        assert "from-registry" not in orch.state.phases
    finally:
        reset_registry()


def test_orchestrator_merges_phase_roles_plugin_wins_on_overlap(monkeypatch, tmp_path):
    """Plugin phase_roles merge into DEFAULT_PHASE_ROLES, plugin values win on overlap."""
    _hermetic(monkeypatch, tmp_path)
    reset_registry()
    try:
        get_registry().register(
            "p",
            ["discuss", "plan", "alpha"],
            {"discuss": ["custom-pm"], "alpha": ["designer"]},
            [],
        )
        orch = HarnessOrchestrator(team_name="t", phases=None)
        assert orch.state.phase_roles["discuss"] == "custom-pm"
        assert orch.state.phase_roles["alpha"] == "designer"
        # Phase the plugin did not override → DEFAULT_PHASE_ROLES preserved.
        # "plan" is in the plugin's phases list but NOT in its phase_roles map
        # → fall through to DEFAULT_PHASE_ROLES, which maps plan → "planner".
        assert orch.state.phase_roles.get("plan") == DEFAULT_PHASE_ROLES["plan"]
    finally:
        reset_registry()


def test_orchestrator_accepts_optional_sprint_state(monkeypatch, tmp_path):
    """SprintState composes onto the orchestrator; PhaseState.team_name is NOT overwritten."""
    _hermetic(monkeypatch, tmp_path)
    reset_registry()
    try:
        sprint_state = SprintState(
            goal="x",
            team="t1",
            sprint_id="abcd1234",
            current_phase="plan",
            created_at="2026-04-16T00:00:00Z",
        )
        orch = HarnessOrchestrator(team_name="t1", sprint_state=sprint_state)
        assert orch.sprint_state is sprint_state
        assert orch.sprint_state.sprint_id == "abcd1234"
        assert orch.state.team_name == "t1"  # composition, not merge

        # Default: no sprint state composed.
        orch2 = HarnessOrchestrator(team_name="t2")
        assert orch2.sprint_state is None
    finally:
        reset_registry()


def test_orchestrator_does_not_force_plan_gate_when_phase_list_lacks_plan(monkeypatch, tmp_path):
    """When the resolved phase list has no 'plan', the PLAN ArtifactRequiredGate is NOT registered."""
    _hermetic(monkeypatch, tmp_path)
    reset_registry()
    try:
        get_registry().register("p", ["alpha", "beta"], {}, [])
        orch = HarnessOrchestrator(team_name="t", phases=None)
        # The orchestrator starts at phases[0] == "alpha". No gates should block advance.
        passed, reason = orch.runner.can_advance()
        assert passed is True, f"unexpected gate-block reason: {reason!r}"
    finally:
        reset_registry()
