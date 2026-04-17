"""Sprint lifecycle state model and persistence (RFC 001 §4.4, D-01, D-05).

SprintState is a NEW pydantic v2 model independent of PhaseState:
- PhaseState describes one harness run (clawteam/harness/phases.py).
- SprintContract describes a sprint's scope definition (clawteam/harness/contracts.py).
- SprintState describes one sprint's runtime state (this module).

The three are composed, NOT coupled via inheritance (D-01). SprintState
persists under ~/.clawteam/teams/<team>/sprints/<sprint_id>/state.json
via the same file_locked + atomic-JSON machinery the rest of ClawTeam uses.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.paths import ensure_within_root, validate_identifier
from clawteam.team.models import get_data_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SprintState(BaseModel):
    """Runtime state of one sprint lifecycle instance.

    Required fields per RFC 001 §4.4. Defaults follow the ClawTeam convention:
    - ``sprint_id`` uses ``uuid.uuid4().hex[:8]`` (matches SprintContract.id).
    - ``created_at`` defaults to an ISO-8601 UTC timestamp.
    - ``auto_advance`` defaults to True (harness advances phases without
      human approval unless an explicit InteractionGate is in the way).
    """

    sprint_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    goal: str
    team: str
    current_phase: str
    phase_history: list[dict[str, str]] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    participants: list[str] = Field(default_factory=list)
    pending_question_ids: list[str] = Field(default_factory=list)
    auto_advance: bool = True
    workspace_branch: str = ""
    created_at: str = Field(default_factory=_now_iso)

    # ── Persistence ─────────────────────────────────────────────────

    @staticmethod
    def _state_path(team: str, sprint_id: str) -> Path:
        """Resolve the canonical state.json path for (team, sprint_id).

        Both identifiers are validated before being joined under the data
        dir, mirroring clawteam.team.snapshot._snapshots_root. Any escape
        attempt raises ValueError before any filesystem operation runs.
        """
        validate_identifier(team, "team name")
        validate_identifier(sprint_id, "sprint id")
        root = get_data_dir() / "teams"
        sprints_dir = ensure_within_root(root, team, "sprints", sprint_id)
        return sprints_dir / "state.json"

    def save(self, team: str) -> Path:
        """Write this SprintState atomically to the canonical path.

        Acquires the sidecar file lock for the duration of the write so
        concurrent writers serialize (last-write-wins, no corruption).
        Returns the written path.
        """
        path = self._state_path(team, self.sprint_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_locked(path):
            atomic_write_text(path, self.model_dump_json(indent=2))
        return path

    @classmethod
    def load(cls, team: str, sprint_id: str) -> SprintState:
        """Read the canonical state.json for (team, sprint_id).

        Acquires the sidecar file lock so a concurrent writer cannot hand
        us a partial payload (atomic_write_text already guarantees no
        torn writes; the lock adds serialization against in-flight saves).
        """
        path = cls._state_path(team, sprint_id)
        with file_locked(path):
            raw = path.read_text(encoding="utf-8")
        data: Any = json.loads(raw)
        return cls.model_validate(data)
