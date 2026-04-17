"""Harness orchestrator: coordinates plan-then-execute agent workflow."""

from __future__ import annotations

from pathlib import Path

from clawteam.harness.artifacts import ArtifactStore
from clawteam.harness.phase_registry import get_registry
from clawteam.harness.phases import (
    PLAN,
    VERIFY,
    AllTasksCompleteGate,
    ArtifactRequiredGate,
    HumanApprovalGate,
    PhaseRunner,
    PhaseState,
)
from clawteam.harness.roles import DEFAULT_ROLES
from clawteam.sprint.state import SprintState
from clawteam.team.models import get_data_dir


class HarnessOrchestrator:
    """Orchestrates a plan-then-execute harness run."""

    def __init__(
        self,
        team_name: str,
        goal: str = "",
        cli: str = "claude",
        agent_count: int = 3,
        phases: list[str] | None = None,
        phase_roles: dict[str, str] | None = None,
        human_gates: list[str] | None = None,
        sprint_state: SprintState | None = None,
    ) -> None:
        self.team_name = team_name
        self.goal = goal
        self.cli = cli
        self.agent_count = agent_count
        # Optional composition: when running under a sprint-producing plugin,
        # the orchestrator holds a SprintState alongside the run-level PhaseState
        # (D-01: SprintState and PhaseState are peers, not subclasses).
        self.sprint_state = sprint_state

        # Resolve phase list:
        # 1. Explicit non-empty arg wins (preserves every existing caller).
        # 2. Otherwise consult PhaseRegistry for plugin-contributed phases (RFC 001 §4.6).
        # 3. Otherwise fall back to DEFAULT_PHASES (preserves Phase 0 regression matrix).
        registered_phases: list[str] = []
        registered_phase_roles: dict[str, list[str]] = {}
        if not phases:
            registry = get_registry()
            registered_phases = registry.ordered_names()
            registered_phase_roles = registry.phase_roles()

        self.state = PhaseState(
            team_name=team_name,
            goal=goal,
            cli=cli,
            agent_count=agent_count,
        )
        if phases:
            self.state.phases = list(phases)
        elif registered_phases:
            self.state.phases = list(registered_phases)
            # Starting phase: first entry of the new phase list. Otherwise the
            # orchestrator would start on DISCUSS (the PhaseState default), which
            # may not be in the plugin's phase list — the first advance() would
            # fail with ValueError on phases.index(current_phase).
            self.state.current_phase = self.state.phases[0]
        # else: PhaseState's default already == list(DEFAULT_PHASES) — no action.

        # Merge phase_roles: plugin values win on overlap; DEFAULT_PHASE_ROLES
        # is preserved for phases the plugin did not map; caller's phase_roles
        # kwarg has the highest priority and is applied last.
        if registered_phase_roles:
            for phase_name, role_list in registered_phase_roles.items():
                if role_list:
                    # Phase 1 conservative choice: take the first role from the
                    # plugin's ordered list. Phase 3/4 will replace this with a
                    # multi-role merge when GstackSprintPlugin lands richer maps.
                    self.state.phase_roles[phase_name] = role_list[0]
        if phase_roles:
            self.state.phase_roles.update(phase_roles)

        self.runner = PhaseRunner(self.state)
        self.artifacts = ArtifactStore(
            self._harness_dir(), team_name, self.state.harness_id,
        )

        # Default gates — ONLY register when the resolved phase list actually
        # contains the phase name. This is the conditional form required for
        # plugin-populated phase lists that omit PLAN/VERIFY (a future
        # research-paper template might not have "plan" or "verify").
        if PLAN in self.state.phases:
            self.runner.register_gate(PLAN, ArtifactRequiredGate(["spec.md"]))
        if VERIFY in self.state.phases:
            self.runner.register_gate(VERIFY, AllTasksCompleteGate())

        # Human approval gates — registered only for phases in the resolved list.
        default_human_gates: list[str] = [PLAN] if PLAN in self.state.phases else []
        for phase in (human_gates if human_gates is not None else default_human_gates):
            if phase in self.state.phases:
                self.runner.register_gate(phase, HumanApprovalGate(phase))

    def _harness_dir(self) -> Path:
        return get_data_dir() / "harness"

    # ── Core operations ───────────────────────────────────────────────

    def start(self) -> str:
        """Start a new harness run. Returns harness_id."""
        self.runner.save(self._harness_dir())
        return self.state.harness_id

    def advance(self) -> str | None:
        """Try to advance to the next phase."""
        result = self.runner.advance()
        if result:
            self.runner.save(self._harness_dir())
        return result

    def status(self) -> dict:
        """Return current status."""
        can_advance, reason = self.runner.can_advance()
        return {
            "harness_id": self.state.harness_id,
            "team": self.team_name,
            "goal": self.state.goal,
            "phase": self.state.current_phase,
            "can_advance": can_advance,
            "gate_reason": reason,
            "artifacts": list(self.state.artifacts.keys()),
            "history": self.state.phase_history,
        }

    def register_artifact(self, name: str, path: str) -> None:
        """Register an artifact in the harness state."""
        self.state.artifacts[name] = path
        self.runner.save(self._harness_dir())

    def abort(self) -> None:
        """Abort the harness run."""
        self.state.phase_history.append({
            "phase": self.state.current_phase,
            "aborted_at": _now_iso(),
        })
        self.runner.save(self._harness_dir())

    # ── Role helpers ──────────────────────────────────────────────────

    def get_role_config(self, role: str):
        """Get the default RoleConfig for a given role."""
        return DEFAULT_ROLES.get(role)

    def get_role_for_phase(self, phase: str) -> str:
        """Get the role name for a given phase."""
        return self.state.phase_roles.get(phase, "")

    # ── Class methods for loading ─────────────────────────────────────

    @classmethod
    def load(cls, team_name: str, harness_id: str) -> HarnessOrchestrator | None:
        """Load an existing harness run."""
        base = get_data_dir() / "harness"
        state_path = base / team_name / harness_id / "state.json"
        if not state_path.is_file():
            return None
        runner = PhaseRunner.load(state_path)
        orch = cls.__new__(cls)
        orch.team_name = team_name
        orch.goal = runner.state.goal
        orch.cli = runner.state.cli
        orch.agent_count = runner.state.agent_count
        orch.state = runner.state
        orch.runner = runner
        orch.artifacts = ArtifactStore(base, team_name, harness_id)
        return orch

    @classmethod
    def find_latest(cls, team_name: str) -> HarnessOrchestrator | None:
        """Find the most recent harness run for a team."""
        base = get_data_dir() / "harness" / team_name
        if not base.is_dir():
            return None
        runs = sorted(base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        for run_dir in runs:
            state_path = run_dir / "state.json"
            if state_path.is_file():
                return cls.load(team_name, run_dir.name)
        return None


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
