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
from typing import Any, Literal

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

    # ── Phase 2 additive fields (§02-CONTEXT D-14/D-15/D-16/D-21/D-27/D-28) ──
    # Every field has a default so Phase 1 state.json files rehydrate cleanly
    # (pydantic v2 BC guarantee — 02-RESEARCH §Runtime State Inventory).
    turn_counters: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Per-agent turn count for theater detection (D-14); increments at "
            "Transport.deliver() and ArtifactStore.write() hook sites."
        ),
    )
    artifact_cap_bytes: int = Field(
        default=50 * 1024,
        description=(
            "Per-file hard cap (D-27); 50 KB default. Overridden by CLI flag "
            "(Plan 02-12) or CLAWTEAM_ARTIFACT_CAP_KB env (Plan 02-11). "
            "Highest layer wins."
        ),
    )
    phase_artifact_cap_bytes: int = Field(
        default=500 * 1024,
        description=(
            "Per-phase sum-of-artifacts cap (D-28); 500 KB default. Overflow "
            "triggers EvidenceGate compaction prompt (Plan 02-07)."
        ),
    )
    status: Literal["running", "paused", "completed"] = Field(
        default="running",
        description=(
            "Sprint lifecycle state (D-22 pause/resume idempotency). "
            "SprintConductor.pause() writes 'paused'; resume() restores 'running'; "
            "advance past Reflect writes 'completed'. Closed state machine — this is "
            "the one Literal field in SprintState (RESEARCH §Pattern 1 approves the "
            "exception to the open-str convention for pause/resume safety)."
        ),
    )
    suppressed_topics: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "Per-route-key suppressed topic-hashes (D-21 cycle-detector persistence). "
            "Key format: 'source->target' route key; value: list of topic hashes. "
            "Populated by DefaultRoutingPolicy.decide (Plan 02-08); cleared on "
            "human answer via InteractionGate."
        ),
    )
    careful_enabled: bool = Field(
        default=False,
        description=(
            "Whether /careful veto-mode is enabled for this sprint (Plan 02-11 D-22). "
            "SprintConductor.resume() calls set_careful_veto_mode(state.careful_enabled) "
            "so the careful blacklist re-arms after a process restart. Default False "
            "matches gstack-native /careful (warn-only) behavior."
        ),
    )

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


# ── Module-level convenience helpers (Plan 02-11 D-22) ───────────────────────
# Thin wrappers over SprintState.save / SprintState.load so SprintConductor and
# the CLI can import function-shaped helpers without importing the class
# directly. Both acquire the same file_locked lock the instance methods use, so
# concurrent writers between the two surfaces serialize through one lock file.


def save_sprint_state(state: SprintState) -> Path:
    """Write ``state`` atomically to ``state._state_path(state.team, state.sprint_id)``.

    Delegates to :meth:`SprintState.save` so the file_locked + atomic_write_text
    persistence path stays single-sourced. Returns the written path.
    """
    return state.save(team=state.team)


def load_sprint_state(team: str, sprint_id: str) -> SprintState:
    """Load the SprintState at ``team/sprint_id``.

    Raises :class:`FileNotFoundError` when the state.json does not exist (Plan
    02-11 D-22 contract — conductor distinguishes missing-sprint from prefix-
    ambiguous via the exception type). Delegates the happy-path read to
    :meth:`SprintState.load` so the file_locked primitive is shared.
    """
    path = SprintState._state_path(team, sprint_id)
    if not path.exists():
        raise FileNotFoundError(f"Sprint state not found: {path}")
    return SprintState.load(team=team, sprint_id=sprint_id)
