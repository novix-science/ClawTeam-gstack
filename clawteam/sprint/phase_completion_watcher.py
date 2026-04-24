"""Wake the leader when current-phase tasks and artifacts are complete."""

from __future__ import annotations

from clawteam.events.types import TaskCompleted
from clawteam.sprint.state import SprintState
from clawteam.team.models import TaskStatus
from clawteam.team.tasks import TaskStore
from clawteam.wake import wake_agent


class PhaseCompletionWatcher:
    """Subscribe to TaskCompleted and wake the leader when a phase is ready."""

    def __init__(self, team: str) -> None:
        self.team = team

    def register(self, bus) -> None:
        bus.subscribe(TaskCompleted, self._on_task_completed)

    def _on_task_completed(self, event: TaskCompleted) -> None:
        if event.team_name != self.team:
            return
        for state in self._running_sprints():
            if not self._phase_tasks_complete(state):
                continue
            missing = self._missing_artifacts(state)
            if missing:
                continue
            leader = self._leader_role()
            wake_agent(
                self.team,
                leader,
                kind="phase",
                preview=(
                    f"All {state.current_phase} phase work complete "
                    f"({len(self._phase_tasks(state))} tasks done, "
                    f"{len(self._required_artifacts(state))} artifacts present). "
                    f"Run 'clawteam sprint advance {state.sprint_id} --team {self.team}' "
                    "to advance."
                ),
                force=True,
            )

    def _running_sprints(self) -> list[SprintState]:
        try:
            from clawteam.sprint.state import load_sprint_state
            from clawteam.team.models import get_data_dir

            sprints_dir = get_data_dir() / "teams" / self.team / "sprints"
            if not sprints_dir.exists():
                return []
            return [
                s
                for s in (
                    load_sprint_state(self.team, p.name)
                    for p in sorted(sprints_dir.iterdir())
                    if p.is_dir() and (p / "state.json").exists()
                )
                if s.status == "running"
            ]
        except Exception:
            return []

    def _phase_tasks(self, state: SprintState):
        tasks = TaskStore(self.team).list_tasks()
        phase_tasks = [
            t
            for t in tasks
            if str(t.metadata.get("phase", "") or "") == state.current_phase
            or str(t.metadata.get("current_phase", "") or "") == state.current_phase
        ]
        return phase_tasks

    def _phase_tasks_complete(self, state: SprintState) -> bool:
        phase_tasks = self._phase_tasks(state)
        return bool(phase_tasks) and all(
            t.status == TaskStatus.completed for t in phase_tasks
        )

    def _required_artifacts(self, state: SprintState) -> list[str]:
        try:
            from clawteam.templates.gstack.phase_contracts import PHASE_REQUIREMENTS

            return list(PHASE_REQUIREMENTS.get(state.current_phase, []))
        except Exception:
            return []

    def _missing_artifacts(self, state: SprintState) -> list[str]:
        return [a for a in self._required_artifacts(state) if a not in state.artifacts]

    def _leader_role(self) -> str:
        try:
            from clawteam.team.manager import TeamManager

            cfg = TeamManager.get_team(self.team)
            return getattr(cfg, "leader_role", "") or "ceo"
        except Exception:
            return "ceo"


def register_phase_completion_watcher(team: str, bus) -> PhaseCompletionWatcher:
    watcher = PhaseCompletionWatcher(team)
    watcher.register(bus)
    return watcher
