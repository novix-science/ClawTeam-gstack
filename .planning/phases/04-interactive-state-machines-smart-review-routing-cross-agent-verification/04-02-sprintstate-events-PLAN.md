---
phase: 04
plan: 02
type: execute
wave: 1
depends_on: [01]
files_modified:
  - clawteam/sprint/state.py
  - clawteam/events/types.py
  - tests/test_sprint_state.py
  - tests/test_event_types_phase4.py
autonomous: true
requirements: [QUALITY-09, QUALITY-13, SPRINT-04]
must_haves:
  truths:
    - "SprintState round-trips `review_sha: str | None = None` field through save/load without BC regression."
    - "clawteam.events.types exports MidReviewThrash and SycophancyCascadeDetected as @dataclass(HarnessEvent) subclasses."
    - "EventBus.emit(MidReviewThrash(team_name='t', sprint_id='s', ...)) returns a list without raising."
    - "Existing state.json files without review_sha load cleanly (None default)."
  artifacts:
    - path: "clawteam/sprint/state.py"
      provides: "SprintState.review_sha additive field"
      contains: "review_sha: str | None = None"
    - path: "clawteam/events/types.py"
      provides: "MidReviewThrash + SycophancyCascadeDetected event dataclasses"
      contains: "class MidReviewThrash(HarnessEvent)"
    - path: "tests/test_sprint_state.py"
      provides: "Round-trip + backwards-compat test for review_sha"
      contains: "def test_review_sha"
    - path: "tests/test_event_types_phase4.py"
      provides: "Construction + EventBus.emit smoke tests for both new event types"
      contains: "def test_mid_review_thrash_"
  key_links:
    - from: "clawteam/sprint/state.py"
      to: "clawteam/sprint/conductor.py (Plan 10)"
      via: "review_sha field read at Review-phase entry"
      pattern: "state.review_sha"
    - from: "clawteam/events/types.py"
      to: "clawteam/sprint/review_phase.py (Plan 10)"
      via: "Plan 10 imports MidReviewThrash + SycophancyCascadeDetected for emission"
      pattern: "from clawteam.events.types import MidReviewThrash, SycophancyCascadeDetected"
---

<objective>
Ship the two pieces of pure substrate that every Phase-4 orchestration piece depends on: (1) `SprintState.review_sha: str | None = None` additive pydantic field (D-05 foundation for SHA-pinning), and (2) two `@dataclass(HarnessEvent)` subclasses `MidReviewThrash` (D-19) and `SycophancyCascadeDetected` (D-09/D-20) in `clawteam/events/types.py`.

Purpose: These are zero-consumer substrate additions. No behavior changes until Plan 10 emits the events and Plan 04+11 read the field. Shipping them first gives Wave 1 substrate a stable target AND gives Wave 2 state machines + Wave 3 orchestration a `bus.emit(MidReviewThrash(...))` shape they can import without conditional feature-flag dances.

Output: 2 substrate edits + 2 test files. All Phase 1/2/3 existing tests stay green (additive extension pattern — proven by Phase 3's 4-field additive TemplateDef).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md

<interfaces>
<!-- Pin the exact shape planners and executors need. Extracted from Phase 2/3 Summaries + verified this session. -->

From clawteam/sprint/state.py (lines 32-106, existing):
```python
class SprintState(BaseModel):
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
    # Phase 2 additive fields: turn_counters, artifact_cap_bytes, phase_artifact_cap_bytes,
    # status, suppressed_topics, careful_enabled — all with defaults (BC preserved).
```
Plain `BaseModel` — no `model_config={"extra":"forbid"}`. Phase 4 adds `review_sha: str | None = None` additively.

From clawteam/events/types.py (lines 1-30, existing):
```python
from dataclasses import dataclass, field
from datetime import datetime, timezone

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class HarnessEvent:
    """Base class for all harness events."""
    team_name: str = ""
    timestamp: str = field(default_factory=_now_iso)
```

From clawteam/events/bus.py (line 86, existing):
```python
def emit(self, event: HarnessEvent) -> list[Any]:
    """Emit an event synchronously. Returns list of handler results."""
```
Accepts typed dataclass events (NOT `(name, payload)` tuples — per PLAN_PREP_NOTES A7).
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add review_sha field to SprintState</name>
  <files>clawteam/sprint/state.py, tests/test_sprint_state.py</files>
  <read_first>
    - clawteam/sprint/state.py (entire file — mirror the Phase 2 additive-field pattern)
    - clawteam/fileutil.py (atomic_write_text + file_locked — persistence unchanged)
    - tests/test_sprint_state.py (existing tests — verify none fail after additive field)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md (confirms A3: no extra='forbid')
  </read_first>
  <behavior>
    - Test 1 (test_review_sha_default_none): Fresh SprintState has `state.review_sha is None`.
    - Test 2 (test_review_sha_round_trip): `state.review_sha = "a1b2c3d4"; state.save(team="t") ; SprintState.load("t","sprint") ; loaded.review_sha == "a1b2c3d4"`.
    - Test 3 (test_review_sha_backwards_compat): Load a pre-Phase-4 state.json (raw JSON missing review_sha key) and verify `review_sha == None` (no ValidationError).
    - Test 4 (test_review_sha_long_sha): Accept full 40-char SHA unchanged (no min_length constraint on SprintState field — ReviewReport schema handles stricter validation).
  </behavior>
  <action>
In `clawteam/sprint/state.py`, append a new additive field to `SprintState` after the Phase 2 `careful_enabled` field (line ~106). Insertion point: just before `# ── Persistence ──` comment. Exact code:

```python
    # ── Phase 4 additive field (§04-CONTEXT D-05) ────────────────────
    # Pinned at Review-phase entry from git rev-parse HEAD; consumed by
    # GstackReviewRouter + _dispatch_review_phase (Plan 10). Defaults to
    # None so pre-Phase-4 state.json files load cleanly (pydantic v2 BC
    # guarantee — same mechanism Phase 2 used for artifact_cap_bytes et al.)
    review_sha: str | None = Field(
        default=None,
        description=(
            "Commit SHA captured at Review-phase entry (D-05). Used by "
            "GstackReviewRouter to pin diff_paths = git diff "
            "<review_sha>..<review_sha>. Mid-review HEAD advance emits "
            "MidReviewThrash event so reviewers can re-pin or supersede."
        ),
    )
```

Create `tests/test_sprint_state.py` IF it does not already exist (grep first — some test file covers SprintState today). If it exists, APPEND the four tests below inside the existing module. If it does not, create the module.

Required tests (exact names + assertions):
```python
def test_review_sha_default_none(tmp_path, monkeypatch):
    """D-05: fresh SprintState has review_sha == None."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    s = SprintState(goal="g", team="t1", current_phase="think")
    assert s.review_sha is None

def test_review_sha_round_trip(tmp_path, monkeypatch):
    """D-05: review_sha survives save/load."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    s = SprintState(goal="g", team="t1", current_phase="review",
                    review_sha="a1b2c3d4e5f6a1b2c3d4")
    s.save(team="t1")
    loaded = SprintState.load(team="t1", sprint_id=s.sprint_id)
    assert loaded.review_sha == "a1b2c3d4e5f6a1b2c3d4"

def test_review_sha_backwards_compat(tmp_path, monkeypatch):
    """Pre-Phase-4 state.json (missing review_sha key) loads without ValidationError."""
    import json
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    s = SprintState(goal="g", team="t1", current_phase="plan")
    path = s.save(team="t1")
    # Round-trip through raw JSON, stripping review_sha key to simulate pre-Phase-4.
    data = json.loads(path.read_text(encoding="utf-8"))
    data.pop("review_sha", None)
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = SprintState.load(team="t1", sprint_id=s.sprint_id)
    assert loaded.review_sha is None

def test_review_sha_accepts_full_sha(tmp_path, monkeypatch):
    """D-05: SprintState.review_sha is permissive; ReviewReport schema enforces stricter regex."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    full = "a" * 40
    s = SprintState(goal="g", team="t1", current_phase="review", review_sha=full)
    s.save(team="t1")
    loaded = SprintState.load(team="t1", sprint_id=s.sprint_id)
    assert loaded.review_sha == full
```

If `tests/test_sprint_state.py` does not exist, use this header imports block at top:
```python
from clawteam.sprint.state import SprintState
```

**Do NOT remove or modify any existing Phase 2 fields.** Confirm after edit: `git diff clawteam/sprint/state.py` shows a single added field block (no accidental deletions).
  </action>
  <verify>
    <automated>pytest tests/test_sprint_state.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "review_sha: str | None = Field" clawteam/sprint/state.py
    - pytest tests/test_sprint_state.py::test_review_sha_default_none exits 0
    - pytest tests/test_sprint_state.py::test_review_sha_round_trip exits 0
    - pytest tests/test_sprint_state.py::test_review_sha_backwards_compat exits 0
    - pytest tests/test_sprint_state.py::test_review_sha_accepts_full_sha exits 0
    - No pre-existing tests in tests/test_sprint_*.py regress (Phase 2 tests still pass)
  </acceptance_criteria>
  <done>SprintState gains one additive field; 4 new tests pass; existing Phase 2 SprintState tests unaffected</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add MidReviewThrash + SycophancyCascadeDetected event dataclasses</name>
  <files>clawteam/events/types.py, tests/test_event_types_phase4.py</files>
  <read_first>
    - clawteam/events/types.py (entire file — study @dataclass(HarnessEvent) subclass convention, lines 13-280)
    - clawteam/events/bus.py (lines 1-121 — confirm emit signature; note register_event_type hook at line 16 if custom events need it)
    - tests/test_event_types_phase2.py (pattern for event-type construction + bus.emit round-trip tests)
  </read_first>
  <behavior>
    - Test 1 (test_mid_review_thrash_construction): Construct MidReviewThrash with all fields; assert defaults + assignment work.
    - Test 2 (test_mid_review_thrash_emit_round_trip): Emit via EventBus to a subscribed handler; handler receives the typed event with all fields intact.
    - Test 3 (test_sycophancy_cascade_construction): Construct SycophancyCascadeDetected with agreement_rate=0.95, threshold=0.9; assert subclassing HarnessEvent (inherits team_name + timestamp).
    - Test 4 (test_sycophancy_cascade_emit_round_trip): Emit, capture via handler.
    - Test 5 (test_timestamps_auto_populated): Both event types default timestamp to a valid ISO-8601 UTC string.
  </behavior>
  <action>
Append to `clawteam/events/types.py` at end-of-file (after existing event types, before any sentinels):

```python
# ── Phase 4: Review-phase events (§04-CONTEXT D-09 / D-19 / D-20) ──────


@dataclass
class MidReviewThrash(HarnessEvent):
    """Emitted when sprint branch HEAD advances during an in-flight Review phase.

    §04-CONTEXT D-19 / Pitfall 9. Reviewers consume this event in their next
    turn to choose between re-pinning (extending review to ``new_sha``) or
    marking the prior review ``superseded``. Payload gives reviewers the
    diff-delta info they need to decide without shelling out to git.

    Emitted by ``dispatch_review_phase`` (Plan 10) at post-turn boundaries
    when ``git rev-parse HEAD != state.review_sha``.
    """

    sprint_id: str = ""
    review_sha: str = ""
    new_sha: str = ""
    reviewer_roles_active: list[str] = field(default_factory=list)
    diff_paths_added: list[str] = field(default_factory=list)
    diff_paths_removed: list[str] = field(default_factory=list)


@dataclass
class SycophancyCascadeDetected(HarnessEvent):
    """Emitted when parallel-reviewer agreement-rate crosses sycophancy_threshold.

    §04-CONTEXT D-09 / D-20 / Pitfall 13. Advisory only — does NOT block
    phase advance. ``review_round`` is scoped to a single Review-phase
    dispatch; re-running Review after gap closure opens a new window (D-20).

    Phase 7's ``clawteam attend --summary`` surfaces this event in the
    cross-sprint digest; Phase 4 only emits + logs.
    """

    sprint_id: str = ""
    review_round: int = 0
    agreement_rate: float = 0.0
    threshold: float = 0.9
    reviewer_roles: list[str] = field(default_factory=list)
```

**Ordering note:** Place these two dataclasses after the existing Phase 2/3 events (last event class in the current file — verify with `grep -n "^class " clawteam/events/types.py`). Do not re-order existing classes.

Create `tests/test_event_types_phase4.py`:

```python
"""Phase 4 event-type round-trip tests (Plan 04-02)."""

from clawteam.events.bus import EventBus
from clawteam.events.types import (
    HarnessEvent,
    MidReviewThrash,
    SycophancyCascadeDetected,
)


def test_mid_review_thrash_construction():
    evt = MidReviewThrash(
        team_name="team-a",
        sprint_id="abc12345",
        review_sha="a" * 40,
        new_sha="b" * 40,
        reviewer_roles_active=["reviewer", "designer"],
        diff_paths_added=["src/new.py"],
        diff_paths_removed=["src/gone.py"],
    )
    assert evt.sprint_id == "abc12345"
    assert evt.review_sha == "a" * 40
    assert evt.new_sha == "b" * 40
    assert evt.reviewer_roles_active == ["reviewer", "designer"]
    assert evt.diff_paths_added == ["src/new.py"]
    assert evt.diff_paths_removed == ["src/gone.py"]
    assert isinstance(evt, HarnessEvent)
    # Inherited fields
    assert evt.team_name == "team-a"
    assert evt.timestamp  # ISO-8601 UTC string populated


def test_mid_review_thrash_emit_round_trip():
    bus = EventBus()
    captured: list[MidReviewThrash] = []
    bus.subscribe(MidReviewThrash, lambda e: captured.append(e))
    bus.emit(MidReviewThrash(team_name="t", sprint_id="s1", review_sha="a" * 40, new_sha="b" * 40))
    assert len(captured) == 1
    assert captured[0].sprint_id == "s1"


def test_sycophancy_cascade_construction():
    evt = SycophancyCascadeDetected(
        team_name="team-b",
        sprint_id="xyz98765",
        review_round=3,
        agreement_rate=0.95,
        threshold=0.9,
        reviewer_roles=["reviewer", "designer", "security", "dx-lead"],
    )
    assert evt.agreement_rate == 0.95
    assert evt.threshold == 0.9
    assert evt.review_round == 3
    assert evt.reviewer_roles == ["reviewer", "designer", "security", "dx-lead"]
    assert isinstance(evt, HarnessEvent)


def test_sycophancy_cascade_emit_round_trip():
    bus = EventBus()
    captured: list[SycophancyCascadeDetected] = []
    bus.subscribe(SycophancyCascadeDetected, lambda e: captured.append(e))
    bus.emit(SycophancyCascadeDetected(team_name="t", sprint_id="s", agreement_rate=0.92))
    assert len(captured) == 1
    assert captured[0].agreement_rate == 0.92


def test_timestamps_auto_populated():
    evt1 = MidReviewThrash(team_name="t")
    evt2 = SycophancyCascadeDetected(team_name="t")
    # Valid ISO-8601 UTC: "YYYY-MM-DDTHH:MM:SS.ffffff+00:00"
    assert "T" in evt1.timestamp
    assert "T" in evt2.timestamp


def test_default_field_values():
    evt = MidReviewThrash()
    assert evt.sprint_id == ""
    assert evt.review_sha == ""
    assert evt.new_sha == ""
    assert evt.reviewer_roles_active == []
    assert evt.diff_paths_added == []
    assert evt.diff_paths_removed == []

    evt2 = SycophancyCascadeDetected()
    assert evt2.sprint_id == ""
    assert evt2.review_round == 0
    assert evt2.agreement_rate == 0.0
    assert evt2.threshold == 0.9
    assert evt2.reviewer_roles == []
```

**Do NOT modify existing Phase 2/3 event classes.** `git diff clawteam/events/types.py` should show ONLY additions at end-of-file.
  </action>
  <verify>
    <automated>pytest tests/test_event_types_phase4.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class MidReviewThrash(HarnessEvent)" clawteam/events/types.py
    - grep -q "class SycophancyCascadeDetected(HarnessEvent)" clawteam/events/types.py
    - pytest tests/test_event_types_phase4.py exits 0 (all 6 tests)
    - pytest tests/test_event_types_phase2.py -x -q passes (no Phase 2 regression)
    - No existing event class was renamed or had fields removed
  </acceptance_criteria>
  <done>Two Phase-4 event types are importable and emit/subscribe round-trips cleanly</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Pydantic schema ↔ persisted state.json | Malformed JSON could inject unexpected review_sha values |
| EventBus handlers ↔ event-type subclass invariants | Subclass that forgets `field(default_factory=list)` silently mutates shared state |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-04 | T (Tampering) | SprintState.review_sha | accept | review_sha is human-readable git SHA; downstream (Plan 10) validates via `git rev-parse` before trust; SprintState is a plain string field. |
| T-04-05 | I (Information disclosure) | MidReviewThrash.diff_paths_added/removed | accept | Paths are workspace-relative, already visible in git log; no PII |
| T-04-06 | D (DoS) | Event dataclass `field(default_factory=list)` mutable-default bug | mitigate | Use `field(default_factory=list)` NOT `= []`; test_default_field_values asserts separate event instances have independent lists |
</threat_model>

<verification>
Plan 02 integration checks:
- [ ] `pytest tests/test_sprint_state.py tests/test_event_types_phase4.py -x -q` returns exit code 0
- [ ] `pytest tests/test_sprint_state_phase2.py tests/test_event_types_phase2.py -x -q` still green (no Phase 2 regression)
- [ ] `pytest tests/test_sprint_conductor.py -x -q` still green (SprintState additive change cannot break conductor)
- [ ] `grep -c "class MidReviewThrash\|class SycophancyCascadeDetected" clawteam/events/types.py` == 2
- [ ] `grep -c "review_sha:" clawteam/sprint/state.py` == 1 (exactly one new field declaration)
</verification>

<success_criteria>
Plan 02 ships when:
- [ ] `SprintState.review_sha: str | None = None` field present in state.py with descriptive docstring
- [ ] `MidReviewThrash` + `SycophancyCascadeDetected` dataclasses defined in events/types.py after Phase 2/3 events
- [ ] 4 SprintState tests + 6 event-type tests pass
- [ ] No Phase 1/2/3 tests regress
- [ ] Downstream Plan 04/10/11 can `from clawteam.events.types import MidReviewThrash, SycophancyCascadeDetected` without error
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-02-sprintstate-events-SUMMARY.md` with:
- Exact line numbers added in state.py
- Exact line numbers added in types.py
- Test pass/fail counts
- Any unexpected regressions
</output>
