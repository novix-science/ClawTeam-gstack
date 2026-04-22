"""Tests for /design-shotgun skill (Plan 06-08, SKILL-11, D-12, D-14, D-17).

Tests 1-8 cover the state machine primitives (state.py) — enums, transition
table, ShotgunState dataclass, advance() purity, iteration-increment rule,
variant carrying, and ABANDON-from-any-active-state.

Tests 9-19 cover the handler (handler.py) — variant_count config resolution,
board rendering, memory write on pick, state.json round-trip, artifact note
emission, illegal-action propagation, and plugin registration.

All tests pure-Python; no real Chromium / filesystem escapes are exercised.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from clawteam.templates.gstack.skills.design_shotgun.state import (
    DSEvent,
    DSState,
    ShotgunState,
    TRANSITIONS,
    VariantFixture,
)


# ---------------------------------------------------------------------------
# Task 1 — state machine primitives (tests 1-8)
# ---------------------------------------------------------------------------


def test_initial_state() -> None:
    """Default ShotgunState → INITIALIZED / iteration=0 / empty variants."""
    s = ShotgunState()
    assert s.state == DSState.INITIALIZED
    assert s.iteration == 0
    assert s.variants == []


def test_legal_transition() -> None:
    """INITIALIZED + GENERATE_REQUESTED → VARIANTS_GENERATING."""
    s = ShotgunState()
    new = s.advance(DSEvent.GENERATE_REQUESTED)
    assert new.state == DSState.VARIANTS_GENERATING


def test_illegal_transition() -> None:
    """INITIALIZED + USER_PICKED is not in TRANSITIONS → ValueError."""
    s = ShotgunState()
    with pytest.raises(ValueError):
        s.advance(DSEvent.USER_PICKED)


def test_all_transitions_table() -> None:
    """For every (from_state, event) in TRANSITIONS, advance reaches to_state."""
    assert TRANSITIONS, "TRANSITIONS dict must be non-empty"
    for (from_state, event), to_state in TRANSITIONS.items():
        # iteration=1 so the REFINE_REQUESTED increment path is active where
        # relevant (keeps this parametric even for the refine loop entry).
        s = ShotgunState(state=from_state, iteration=1)
        new = s.advance(event)
        assert new.state == to_state, (
            f"({from_state.value}, {event.value}) → expected "
            f"{to_state.value}, got {new.state.value}"
        )


def test_advance_is_pure() -> None:
    """advance() returns a NEW ShotgunState; original is unchanged."""
    s = ShotgunState()
    new = s.advance(DSEvent.GENERATE_REQUESTED)
    assert s.state == DSState.INITIALIZED
    assert new is not s
    assert new.state == DSState.VARIANTS_GENERATING


def test_refine_loop_increments_iteration() -> None:
    """REFINING + REFINE_REQUESTED → VARIANTS_GENERATING + iteration+=1 (when iteration>=1)."""
    # First iteration loop: from REFINING with iteration=1 (user already
    # picked once and came back around) → iteration becomes 2.
    s = ShotgunState(state=DSState.REFINING, iteration=1)
    new = s.advance(DSEvent.REFINE_REQUESTED)
    assert new.state == DSState.VARIANTS_GENERATING
    assert new.iteration == 2

    # Initial INITIALIZED → VARIANTS_GENERATING must NOT bump iteration.
    s0 = ShotgunState(state=DSState.INITIALIZED, iteration=0)
    new0 = s0.advance(DSEvent.GENERATE_REQUESTED)
    assert new0.state == DSState.VARIANTS_GENERATING
    assert new0.iteration == 0


def test_variants_carried_forward() -> None:
    """VARIANTS_GENERATING + VARIANTS_READY with variants=[...] populates new state."""
    s = ShotgunState(state=DSState.VARIANTS_GENERATING)
    variants = [
        VariantFixture(
            variant_id=f"variant-{i}",
            title=f"V{i}",
            description=f"d{i}",
            html_path=f"p{i}.html",
        )
        for i in range(1, 5)
    ]
    new = s.advance(DSEvent.VARIANTS_READY, variants=variants)
    assert new.state == DSState.BOARD_RENDERED
    assert len(new.variants) == 4
    assert [v.variant_id for v in new.variants] == [
        "variant-1", "variant-2", "variant-3", "variant-4",
    ]


def test_abandon_from_any_state() -> None:
    """ABANDON is a legal transition from all 5 active states → ABANDONED."""
    active = [
        DSState.INITIALIZED,
        DSState.VARIANTS_GENERATING,
        DSState.BOARD_RENDERED,
        DSState.USER_PICKING,
        DSState.REFINING,
    ]
    for state in active:
        s = ShotgunState(state=state)
        new = s.advance(DSEvent.ABANDON)
        assert new.state == DSState.ABANDONED, (
            f"ABANDON from {state.value} should reach ABANDONED, got {new.state.value}"
        )


# ---------------------------------------------------------------------------
# Task 2 — handler tests (9-19). Shared helpers defined below.
# ---------------------------------------------------------------------------


def _make_ctx(
    tmp_path: Path,
    *,
    variant_count: int | None = None,
    team_name: str = "teamA",
    sprint_id: str = "s1",
) -> SimpleNamespace:
    """Build a minimal ctx stand-in that the handler accepts.

    When ``variant_count`` is None the template.design_shotgun attribute is
    None (matches the "no TOML block" path). Otherwise a DesignShotgunConfig
    instance is attached so the handler's config resolver reads it.
    """
    sprint_dir = tmp_path / "sprint"
    sprint_dir.mkdir(parents=True, exist_ok=True)

    template: SimpleNamespace
    if variant_count is None:
        template = SimpleNamespace(design_shotgun=None)
    else:
        template = SimpleNamespace(
            design_shotgun=SimpleNamespace(variant_count=variant_count),
        )
    return SimpleNamespace(
        sprint_dir=sprint_dir,
        sprint_id=sprint_id,
        team_name=team_name,
        template=template,
    )


_FIXTURES_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "design_shotgun"


def _fixture_variants() -> list[dict[str, str]]:
    """Load the 4 fixture variants shipped under tests/fixtures/design_shotgun/."""
    return [
        {
            "variant_id": f"variant-{i}",
            "title": f"Variant {i}",
            "description": f"Fixture variant {i}",
            "html_path": str(_FIXTURES_DIR / f"variant-{i}" / "index.html"),
        }
        for i in range(1, 5)
    ]


def test_init_action_variant_count_from_config(tmp_path) -> None:
    """ctx.template.design_shotgun.variant_count=6 → state.variant_count == 6."""
    from clawteam.templates.gstack.skills.design_shotgun.handler import (
        shotgun_handler,
    )

    ctx = _make_ctx(tmp_path, variant_count=6)
    result = shotgun_handler(ctx, role="designer", args={"action": "init"})
    assert result["status"] == "initialized"
    assert result["variant_count"] == 6


def test_init_default_when_no_config(tmp_path) -> None:
    """template.design_shotgun is None → variant_count defaults to 4."""
    from clawteam.templates.gstack.skills.design_shotgun.handler import (
        shotgun_handler,
    )

    ctx = _make_ctx(tmp_path, variant_count=None)
    result = shotgun_handler(ctx, role="designer", args={"action": "init"})
    assert result["variant_count"] == 4


def test_generate_writes_variant_files(tmp_path) -> None:
    """From INITIALIZED, action=generate + variants=[4 fixture dicts]:
    handler writes 4 variant HTML files + design-board/index.md → BOARD_RENDERED.
    """
    from clawteam.templates.gstack.skills.design_shotgun.handler import (
        shotgun_handler,
    )

    ctx = _make_ctx(tmp_path, variant_count=4)
    shotgun_handler(ctx, role="designer", args={"action": "init"})
    variants = _fixture_variants()
    result = shotgun_handler(
        ctx, role="designer", args={"action": "generate", "variants": variants},
    )
    assert result["state"] == DSState.BOARD_RENDERED.value

    sprint_dir = ctx.sprint_dir
    for i in range(1, 5):
        html = sprint_dir / "design-board" / f"variant-{i}" / "index.html"
        assert html.is_file(), f"missing variant-{i} HTML"
        assert "Variant" in html.read_text(encoding="utf-8")
    index = sprint_dir / "design-board" / "index.md"
    assert index.is_file()
    assert "variant-1" in index.read_text(encoding="utf-8")


def test_publish_advances_to_user_picking(tmp_path) -> None:
    """BOARD_RENDERED + action=publish → USER_PICKING."""
    from clawteam.templates.gstack.skills.design_shotgun.handler import (
        shotgun_handler,
    )

    ctx = _make_ctx(tmp_path, variant_count=4)
    shotgun_handler(ctx, role="designer", args={"action": "init"})
    shotgun_handler(
        ctx, role="designer",
        args={"action": "generate", "variants": _fixture_variants()},
    )
    result = shotgun_handler(ctx, role="designer", args={"action": "publish"})
    assert result["state"] == DSState.USER_PICKING.value


def test_pick_writes_memory_entry(tmp_path, monkeypatch) -> None:
    """USER_PICKING + action=pick → TeamMemoryStore.write called with a
    role-scoped designer entry whose evidence cites the picked variant.
    """
    import clawteam.templates.gstack.skills.design_shotgun.handler as hd

    ctx = _make_ctx(tmp_path, variant_count=4, team_name="teamA", sprint_id="s1")
    hd.shotgun_handler(ctx, role="designer", args={"action": "init"})
    hd.shotgun_handler(
        ctx, role="designer",
        args={"action": "generate", "variants": _fixture_variants()},
    )
    hd.shotgun_handler(ctx, role="designer", args={"action": "publish"})

    captured: list = []

    class _StubStore:
        def __init__(self, team_name: str) -> None:
            self.team_name = team_name

        def gen_id(self, *, author: str, title: str, tags):
            return "mem-teama-20260422-aa1001"

        def write(self, entry):
            captured.append(entry)
            return entry.id

    monkeypatch.setattr(hd, "TeamMemoryStore", _StubStore)

    result = hd.shotgun_handler(
        ctx, role="designer",
        args={
            "action": "pick",
            "variant_id": "variant-2",
            "reason": "clean typography",
        },
    )
    assert result["state"] == DSState.REFINING.value
    assert result["picked_variant_id"] == "variant-2"
    assert len(captured) == 1
    entry = captured[0]
    assert entry.scope == "role"
    assert entry.role == "designer"
    assert "design" in entry.tags
    assert "taste" in entry.tags
    assert "variant-2" in entry.evidence
    assert entry.learned_from == "user"


def test_refine_loops_back(tmp_path, monkeypatch) -> None:
    """REFINING + action=refine → VARIANTS_GENERATING; iteration incremented."""
    import clawteam.templates.gstack.skills.design_shotgun.handler as hd

    ctx = _make_ctx(tmp_path, variant_count=4)
    hd.shotgun_handler(ctx, role="designer", args={"action": "init"})
    hd.shotgun_handler(
        ctx, role="designer",
        args={"action": "generate", "variants": _fixture_variants()},
    )
    hd.shotgun_handler(ctx, role="designer", args={"action": "publish"})

    # Stub memory store so pick does not touch real home dir.
    class _StubStore:
        def __init__(self, _tn: str) -> None: ...
        def gen_id(self, **kw): return "mem-teama-20260422-aa1002"
        def write(self, entry): return entry.id
    monkeypatch.setattr(hd, "TeamMemoryStore", _StubStore)

    hd.shotgun_handler(
        ctx, role="designer",
        args={
            "action": "pick", "variant_id": "variant-3", "reason": "color",
        },
    )
    result = hd.shotgun_handler(ctx, role="designer", args={"action": "refine"})
    assert result["state"] == DSState.VARIANTS_GENERATING.value
    assert result["iteration"] == 2  # started at 0, bumped to 1 on first gen,
    # then bumped on refine from REFINING with iteration already 1.
    # (advance rule: +1 only on REFINE_REQUESTED-driven REFINING→VG with iter>=1.)


def test_converge_terminal(tmp_path, monkeypatch) -> None:
    """REFINING + action=converge → CONVERGED."""
    import clawteam.templates.gstack.skills.design_shotgun.handler as hd

    ctx = _make_ctx(tmp_path, variant_count=4)
    hd.shotgun_handler(ctx, role="designer", args={"action": "init"})
    hd.shotgun_handler(
        ctx, role="designer",
        args={"action": "generate", "variants": _fixture_variants()},
    )
    hd.shotgun_handler(ctx, role="designer", args={"action": "publish"})

    class _StubStore:
        def __init__(self, _tn: str) -> None: ...
        def gen_id(self, **kw): return "mem-teama-20260422-bb2001"
        def write(self, entry): return entry.id
    monkeypatch.setattr(hd, "TeamMemoryStore", _StubStore)

    hd.shotgun_handler(
        ctx, role="designer",
        args={"action": "pick", "variant_id": "variant-1", "reason": "clean"},
    )
    result = hd.shotgun_handler(ctx, role="designer", args={"action": "converge"})
    assert result["state"] == DSState.CONVERGED.value


def test_state_json_roundtrip(tmp_path) -> None:
    """to_json_dict → from_json_dict is identity on state + variants + iteration."""
    variants = [
        VariantFixture(
            variant_id=f"variant-{i}", title=f"V{i}",
            description=f"d{i}", html_path=f"p{i}.html",
        )
        for i in range(1, 5)
    ]
    original = ShotgunState(
        state=DSState.BOARD_RENDERED,
        sprint_id="s1",
        variant_count=4,
        variants=variants,
        picked_variant_id="variant-2",
        pick_reason="clean",
        iteration=2,
    )
    raw = original.to_json_dict()
    rebuilt = ShotgunState.from_json_dict(raw)
    assert rebuilt.state == original.state
    assert rebuilt.variant_count == original.variant_count
    assert rebuilt.iteration == original.iteration
    assert rebuilt.picked_variant_id == original.picked_variant_id
    assert [v.variant_id for v in rebuilt.variants] == [
        "variant-1", "variant-2", "variant-3", "variant-4",
    ]


def test_abandon_writes_artifact_status(tmp_path) -> None:
    """action=abandon → state=ABANDONED; design-shotgun-note.md status=abandoned."""
    from clawteam.templates.gstack.skills.design_shotgun.handler import (
        shotgun_handler,
    )

    ctx = _make_ctx(tmp_path, variant_count=4)
    shotgun_handler(ctx, role="designer", args={"action": "init"})
    result = shotgun_handler(ctx, role="designer", args={"action": "abandon"})
    assert result["state"] == DSState.ABANDONED.value

    note = ctx.sprint_dir / "design-shotgun-note.md"
    assert note.is_file()
    content = note.read_text(encoding="utf-8")
    assert "status: 'abandon'" in content
    assert "state: 'abandoned'" in content


def test_illegal_action_raises(tmp_path) -> None:
    """Invalid action for current state → ValueError propagates."""
    from clawteam.templates.gstack.skills.design_shotgun.handler import (
        shotgun_handler,
    )

    ctx = _make_ctx(tmp_path, variant_count=4)
    shotgun_handler(ctx, role="designer", args={"action": "init"})
    # From INITIALIZED, "pick" is illegal — DSEvent.USER_PICKED not a legal
    # transition from INITIALIZED.
    with pytest.raises(ValueError):
        shotgun_handler(
            ctx, role="designer",
            args={"action": "pick", "variant_id": "variant-1", "reason": "?"},
        )


def test_registered_in_plugin() -> None:
    """GstackSprintPlugin registers /design-shotgun for role=designer.

    Uses subset-on-count so this test commutes with parallel Wave 3 plans
    06-09 / 06-10 that each append their own SkillRegistration. Strict
    ``== 11`` is locked by the post-wave integration test.
    """
    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    regs = plugin.contribute_skills()
    names = [r.name for r in regs]
    assert "/design-shotgun" in names
    # Phase 5 (7) + Wave-2 browser triplet (3) + /design-shotgun = 11; siblings
    # may land before or after this plan, so we accept ≥ 9.
    assert len(regs) >= 9, f"expected ≥9 skills, got {len(regs)}: {sorted(names)}"

    by_name = {r.name: r for r in regs}
    reg = by_name["/design-shotgun"]
    assert reg.roles == frozenset({"designer"})
    assert callable(reg.handler)
