"""RED-phase tests for clawteam.harness.forced_progress_gate (Plan 02-09).

Exercises the theater detector + turn-counter wiring + per-agent isolation invariants
from §02-CONTEXT D-14..D-17 and §02-RESEARCH Pitfall #2 (turn_id dedupe),
Pitfall #3 (progress signal in cycle detector), Pitfall #16 (per-agent, not
sprint-wide). These tests fail at RED because the module does not yet exist
and ArtifactStore/Transport do not yet wire the turn counter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from clawteam.events.global_bus import get_event_bus, reset_event_bus
from clawteam.sprint.state import SprintState


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    reset_event_bus()
    # Reset forced-progress module state if available (GREEN phase).
    try:
        from clawteam.harness.forced_progress_gate import reset_turn_counter_state

        reset_turn_counter_state()
    except ImportError:
        pass
    yield
    reset_event_bus()
    try:
        from clawteam.harness.forced_progress_gate import reset_turn_counter_state

        reset_turn_counter_state()
    except ImportError:
        pass


def _sprint_state(
    *,
    team: str = "t1",
    sprint_id: str = "abcd1234",
    current_phase: str = "build",
) -> SprintState:
    state = SprintState(
        goal="g",
        team=team,
        current_phase=current_phase,
        sprint_id=sprint_id,
        created_at="2026-04-20T00:00:00Z",
    )
    # Ensure on-disk sprint dir exists so the gate can write questions.
    state.save(team=team)
    return state


def test_zero_turns_passes():
    """Fresh SprintState (empty turn_counters): gate passes."""
    from clawteam.harness.forced_progress_gate import forced_progress_gate

    state = _sprint_state()
    gate = forced_progress_gate()
    passed, reason = gate.check(state)
    assert passed is True
    assert reason == ""


def test_one_noprogress_turn_passes():
    """Single no-progress turn (counter=1, no artifact delta): still below 2-turn threshold."""
    from clawteam.harness.forced_progress_gate import forced_progress_gate

    state = _sprint_state()
    state.turn_counters["engineer"] = 1
    gate = forced_progress_gate()
    passed, reason = gate.check(state)
    assert passed is True
    assert reason == ""


def test_two_consecutive_noprogress_turns_trigger_gate():
    """2 consecutive no-progress turns per agent trip the gate."""
    from clawteam.harness.forced_progress_gate import forced_progress_gate

    state = _sprint_state()
    state.turn_counters["engineer"] = 2  # 2 turns, no artifact delta.
    gate = forced_progress_gate()
    passed, reason = gate.check(state)
    assert passed is False
    assert "engineer" in reason
    assert "no-progress" in reason or "no progress" in reason


def test_task_completed_event_resets_counter():
    """TaskCompleted event from the agent resets the no-progress counter."""
    from clawteam.harness.forced_progress_gate import forced_progress_gate

    from clawteam.events.types import TaskCompleted

    state = _sprint_state()
    state.turn_counters["engineer"] = 2
    gate = forced_progress_gate()
    gate.register()  # subscribe to TaskCompleted

    # Emit TaskCompleted(owner="engineer") — gate should absorb it.
    get_event_bus().emit(TaskCompleted(team_name="t1", owner="engineer", task_id="T1"))

    passed, reason = gate.check(state)
    assert passed is True, f"gate should pass after TaskCompleted, got reason={reason!r}"
    assert reason == ""


def test_net_positive_artifact_delta_counts_as_progress(tmp_path):
    """Artifact bytes delta > 0 for the agent → gate passes (net progress)."""
    from clawteam.harness.forced_progress_gate import forced_progress_gate

    from clawteam.harness.artifacts import ArtifactStore

    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.turn_counters["engineer"] = 2  # 2 turns accumulated

    # Per-agent artifact bytes recorded via .meta.json sidecar.
    sprint_dir = Path(tmp_path) / "teams" / "t1" / "sprints" / "abcd1234"
    store = ArtifactStore(
        base_dir=tmp_path / "teams", team_name="t1", harness_id="sprints/abcd1234"
    )
    # Write 100 bytes attributed to engineer (Plan 02-06 records metadata.agent on .meta.json).
    store.write("spec.md", "x" * 100, metadata={"agent": "engineer", "size_bytes": 100})

    # Sanity: ArtifactStore uses base_dir/team_name/harness_id/artifacts; we assembled
    # harness_id = "sprints/abcd1234" which mimics the sprint path layout.
    _ = sprint_dir  # layout reference; actual check uses recursive glob below.
    all_meta = list(Path(tmp_path).rglob("*.meta.json"))
    assert len(all_meta) >= 1

    gate = forced_progress_gate()
    passed, reason = gate.check(state)
    assert passed is True, f"net-positive artifact delta should count as progress, reason={reason!r}"


def test_per_agent_not_sprint_wide_isolation(tmp_path):
    """D-16 + Pitfall #16: security's write does NOT reset engineer's no-progress counter."""
    from clawteam.harness.forced_progress_gate import forced_progress_gate

    from clawteam.harness.artifacts import ArtifactStore

    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.turn_counters["engineer"] = 2  # engineer has 2 no-progress turns
    state.turn_counters["security"] = 1  # security active but below threshold

    # security writes an artifact — must NOT count toward engineer's progress.
    store = ArtifactStore(
        base_dir=tmp_path / "teams", team_name="t1", harness_id="sprints/abcd1234"
    )
    store.write("security-review.md", "y" * 200, metadata={"agent": "security", "size_bytes": 200})

    gate = forced_progress_gate()
    passed, reason = gate.check(state)
    assert passed is False, "engineer's no-progress counter must not be reset by security's write"
    assert "engineer" in reason
    assert "security" not in reason or reason.count("engineer") >= 1


def test_turn_id_dedupe_artifactstore_and_transport_same_turn(tmp_path):
    """Pitfall #2: same turn_id across deliver+write increments counter ONCE."""
    from clawteam.harness.forced_progress_gate import increment_turn_counter

    state = _sprint_state()
    # Simulate: ArtifactStore.write calls increment_turn_counter
    increment_turn_counter(state, "engineer", turn_id="abc12345")
    # Simulate: Transport.deliver calls increment_turn_counter for the same turn
    increment_turn_counter(state, "engineer", turn_id="abc12345")

    assert state.turn_counters["engineer"] == 1, (
        f"same turn_id must dedupe to 1 increment; got {state.turn_counters['engineer']}"
    )


def test_gate_writes_question_file_on_trigger(tmp_path):
    """On trigger: questions/<id>.md file written with multi-choice + 3 choices."""
    from clawteam.harness.forced_progress_gate import forced_progress_gate

    from clawteam.sprint.qa import Question

    state = _sprint_state(team="t1", sprint_id="abcd1234")
    state.turn_counters["engineer"] = 2
    gate = forced_progress_gate()

    passed, reason = gate.check(state)
    assert passed is False

    # Question file must exist in the sprint questions directory.
    questions_dir = Path(tmp_path) / "teams" / "t1" / "sprints" / "abcd1234" / "questions"
    files = list(questions_dir.glob("*.md"))
    assert len(files) == 1, f"expected 1 question file, got {len(files)}"

    raw = files[0].read_text(encoding="utf-8")
    q = Question.from_markdown(raw)
    assert q.type == "multi-choice"
    assert q.choices is not None
    assert len(q.choices) == 3
    labels = " ".join(c.label.lower() for c in q.choices)
    assert "keep waiting" in labels
    assert "restart agent" in labels
    assert "abort sprint" in labels


def test_gate_emits_forced_progress_triggered_event():
    """Gate emits ForcedProgressTriggered(agent, consecutive_no_progress, question_id)."""
    from clawteam.harness.forced_progress_gate import forced_progress_gate

    from clawteam.events.types import ForcedProgressTriggered

    state = _sprint_state()
    state.turn_counters["engineer"] = 2
    gate = forced_progress_gate()

    received: list[ForcedProgressTriggered] = []
    get_event_bus().subscribe(ForcedProgressTriggered, lambda e: received.append(e))

    passed, reason = gate.check(state)
    assert passed is False
    assert len(received) == 1
    evt = received[0]
    assert evt.agent == "engineer"
    assert evt.consecutive_no_progress == 2
    assert evt.question_id  # non-empty uuid8
