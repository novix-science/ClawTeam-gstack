"""Tests for clawteam.sprint.qa.Question/Answer + to_markdown/from_markdown round-trip."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from clawteam.sprint.qa import Answer, Question

# Plans 01-02 (SprintState) and 01-03 (InteractionGate) land on sibling worktrees
# in wave 2. The gate-compat integration test (the only place these imports are
# used) is skipped when those modules are absent so this file stays collectable
# in the 01-04 worktree pre-merge. After the orchestrator merges all wave-2
# branches the integration test runs unconditionally.
try:
    from clawteam.harness.interaction_gate import InteractionGate  # noqa: F401
    from clawteam.sprint.state import SprintState  # noqa: F401

    _GATE_COMPAT_READY = True
except ImportError:
    _GATE_COMPAT_READY = False

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "qa"
HEX8 = re.compile(r"^[0-9a-f]{8}$")


def _hermetic(monkeypatch, tmp_path):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))


def _minimal_freeform_kwargs(**overrides):
    base = dict(
        slug="example-question",
        type="freeform",
        created_at="2026-04-16T10:00:00Z",
        sprint_id="abcd1234",
        phase="plan",
        author="pm",
    )
    base.update(overrides)
    return base


def test_question_required_fields_and_default_id():
    """id default_factory produces an 8-char hex string."""
    q = Question(**_minimal_freeform_kwargs())
    assert HEX8.match(q.id), f"id {q.id!r} is not 8-char hex"
    assert q.slug == "example-question"
    assert q.type == "freeform"
    assert q.phase == "plan"
    assert q.author == "pm"
    assert q.body == ""  # empty body default


def test_question_type_literal_rejects_invalid():
    """An unknown type string raises ValidationError."""
    with pytest.raises((ValidationError, ValueError)):
        Question(**_minimal_freeform_kwargs(type="nonsense"))


def test_question_multi_choice_requires_choices():
    """multi-choice questions must declare at least one choice."""
    with pytest.raises((ValidationError, ValueError)):
        Question(**_minimal_freeform_kwargs(type="multi-choice"))


def test_question_freeform_rejects_choices():
    """freeform / confirm questions must not declare choices."""
    with pytest.raises((ValidationError, ValueError)):
        Question(
            **_minimal_freeform_kwargs(
                type="freeform",
                choices=[{"id": "A", "label": "x"}],
            ),
        )


def test_to_markdown_multi_choice_shape():
    """to_markdown emits the D-08 multi-choice schema with frontmatter + choices + body."""
    q = Question(
        id="a1b2c3d4",
        slug="post-layout-question",
        type="multi-choice",
        created_at="2026-04-16T10:30:00Z",
        sprint_id="00112233",
        phase="plan",
        author="designer",
        choices=[
            {"id": "A", "label": "Yes, user's avatar on every post"},
            {"id": "B", "label": "No, clean minimal list"},
        ],
        body="Should posts have avatars on every card?\n",
    )
    md = q.to_markdown()
    # Frontmatter fences.
    assert md.startswith("---\n")
    assert "\n---\n" in md[4:]  # closing fence after the opening fence
    # Scalar keys.
    for s in (
        "id: a1b2c3d4",
        "slug: post-layout-question",
        "type: multi-choice",
        "created_at: 2026-04-16T10:30:00Z",
        "sprint_id: 00112233",
        "phase: plan",
        "author: designer",
    ):
        assert s in md, f"missing `{s}` in:\n{md}"
    # Choices list.
    assert "choices:" in md
    assert "  - id: A" in md
    assert "    label: Yes, user's avatar on every post" in md
    assert "  - id: B" in md
    assert "    label: No, clean minimal list" in md
    # Body.
    assert "Should posts have avatars on every card?" in md


def test_to_markdown_freeform_shape():
    """freeform to_markdown has no `choices:` key."""
    q = Question(**_minimal_freeform_kwargs(id="ffffffff", body="What do we ship first?\n"))
    md = q.to_markdown()
    assert "type: freeform" in md
    assert "choices:" not in md  # freeform never serializes choices
    assert "What do we ship first?" in md


def test_from_markdown_parses_each_fixture():
    """Each fixture parses back into a Question/Answer with the expected field values."""
    multi = Question.from_markdown((FIXTURE_DIR / "question_multi_choice.md").read_text(encoding="utf-8"))
    assert multi.id == "a1b2c3d4"
    assert multi.slug == "post-layout-question"
    assert multi.type == "multi-choice"
    assert multi.sprint_id == "00112233"
    assert multi.phase == "plan"
    assert multi.author == "designer"
    assert len(multi.choices or []) == 2
    assert multi.choices[0].id == "A"
    assert multi.choices[0].label == "Yes, user's avatar on every post"
    assert multi.choices[1].id == "B"
    assert multi.choices[1].label == "No, clean minimal list"
    assert "Should posts have avatars" in multi.body

    free = Question.from_markdown((FIXTURE_DIR / "question_freeform.md").read_text(encoding="utf-8"))
    assert free.type == "freeform"
    assert free.choices is None or free.choices == []
    assert "single product outcome" in free.body

    confirm = Question.from_markdown((FIXTURE_DIR / "question_confirm.md").read_text(encoding="utf-8"))
    assert confirm.type == "confirm"
    assert confirm.author == "ceo"

    ans_multi = Answer.from_markdown((FIXTURE_DIR / "answer_multi_choice.md").read_text(encoding="utf-8"))
    assert ans_multi.question_id == "a1b2c3d4"
    assert ans_multi.choice == "A"

    ans_free = Answer.from_markdown((FIXTURE_DIR / "answer_freeform.md").read_text(encoding="utf-8"))
    assert ans_free.question_id == "bbbbbbbb"
    assert ans_free.choice is None


def test_round_trip_question_equals_original():
    """from_markdown(to_markdown(q)) == q for every fixture."""
    for fx in ("question_multi_choice.md", "question_freeform.md", "question_confirm.md"):
        parsed = Question.from_markdown((FIXTURE_DIR / fx).read_text(encoding="utf-8"))
        reparsed = Question.from_markdown(parsed.to_markdown())
        assert parsed.model_dump() == reparsed.model_dump(), f"round-trip lost info for {fx}"


def test_answer_round_trip_equality():
    """Answer round-trip preserves fields."""
    for fx in ("answer_multi_choice.md", "answer_freeform.md"):
        parsed = Answer.from_markdown((FIXTURE_DIR / fx).read_text(encoding="utf-8"))
        reparsed = Answer.from_markdown(parsed.to_markdown())
        assert parsed.model_dump() == reparsed.model_dump(), f"round-trip lost info for {fx}"


@pytest.mark.skipif(
    not _GATE_COMPAT_READY,
    reason="InteractionGate (Plan 01-03) + SprintState (Plan 01-02) not yet merged into this worktree",
)
def test_gate_detects_question_file_written_via_to_markdown(monkeypatch, tmp_path):
    """to_markdown output, written to <sprint_dir>/questions/<id>.md, triggers InteractionGate."""
    # Re-import inside the test so the skip decorator above is the only gate
    # (imports at module top are wrapped in try/except for wave-2 parallelism).
    from clawteam.harness.interaction_gate import InteractionGate
    from clawteam.sprint.state import SprintState

    _hermetic(monkeypatch, tmp_path)
    state = SprintState(
        goal="test gate-compat",
        team="t1",
        sprint_id="abcd1234",
        current_phase="plan",
        created_at="2026-04-16T00:00:00Z",
    )
    state.save(team="t1")

    q = Question(
        id="deadbeef",
        slug="gate-compat-check",
        type="freeform",
        created_at="2026-04-16T10:00:00Z",
        sprint_id="abcd1234",
        phase="plan",
        author="pm",
        body="Is this blocking?\n",
    )

    q_dir = tmp_path / "teams" / "t1" / "sprints" / "abcd1234" / "questions"
    q_dir.mkdir(parents=True, exist_ok=True)
    (q_dir / f"{q.id}.md").write_text(q.to_markdown(), encoding="utf-8")

    gate = InteractionGate()
    passed, reason = gate.check(state)
    assert passed is False
    assert "deadbeef" in reason
