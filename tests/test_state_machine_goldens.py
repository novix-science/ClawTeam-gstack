"""Consolidated state-machine goldens (Plan 04-13 -- QUALITY-07 regression defense).

Cross-cuts Plan 07/08/09 per-skill tests: asserts each skill's in-code
_TRANSITIONS dict + TURN_BUDGET + _FINAL_STATES agree with the fixture JSON
under tests/fixtures/gstack_state_machines/. Useful for catching drift where
one edit touches the fixture without updating the code (or vice versa).

Per ISS-06 revision: the former soft-bound "monologue_collapse_detector" has
been removed in favor of strict equality between each skill's TURN_BUDGET
constant and the fixture's ``turn_budget`` field (see
``test_turn_budget_matches_fixture``). Strict equality catches the same
monologue-collapse regression surface (anyone shrinking the budget to "1"
to batch questions in a single turn) with a crisper failure mode.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest


_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gstack_state_machines"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


# Parametrize over (skill_name, fixture_filename, module_import_path).
# Each module exposes: _TRANSITIONS, TURN_BUDGET, _FINAL_STATES
STATE_MACHINES = [
    (
        "office-hours",
        "office-hours.transitions.json",
        "clawteam.templates.gstack.skills.office_hours.state",
    ),
    (
        "design-consultation",
        "design-consultation.transitions.json",
        "clawteam.templates.gstack.skills.design_consultation.state",
    ),
    (
        "investigate",
        "investigate.transitions.json",
        "clawteam.templates.gstack.skills.investigate.state",
    ),
]


@pytest.mark.parametrize("skill,fixture_name,module_path", STATE_MACHINES)
def test_transitions_match_fixture(skill: str, fixture_name: str, module_path: str) -> None:
    """In-code _TRANSITIONS must bijectively match the fixture's transitions."""
    mod = importlib.import_module(module_path)
    transitions = getattr(mod, "_TRANSITIONS")

    fx = _load_fixture(fixture_name)
    code_triples = {(k[0], k[1], v) for k, v in transitions.items()}
    fx_triples = {(t["from"], t["event"], t["to"]) for t in fx["transitions"]}

    assert code_triples == fx_triples, (
        f"[{skill}] transition drift\n"
        f"  only in code: {sorted(code_triples - fx_triples)}\n"
        f"  only in fixture: {sorted(fx_triples - code_triples)}"
    )


@pytest.mark.parametrize("skill,fixture_name,module_path", STATE_MACHINES)
def test_turn_budget_matches_fixture(skill: str, fixture_name: str, module_path: str) -> None:
    """Strict equality: TURN_BUDGET constant == fixture.turn_budget.

    Tightened per ISS-06: any shrinkage of the budget (the monologue-collapse
    regression vector) fails loudly at CI with the exact before/after values
    rather than relying on a soft lower bound that would silently drift.
    """
    mod = importlib.import_module(module_path)
    turn_budget = getattr(mod, "TURN_BUDGET")
    fx = _load_fixture(fixture_name)
    assert turn_budget == fx["turn_budget"], (
        f"[{skill}] TURN_BUDGET={turn_budget} != fixture={fx['turn_budget']}"
    )


@pytest.mark.parametrize("skill,fixture_name,module_path", STATE_MACHINES)
def test_final_states_match_fixture(skill: str, fixture_name: str, module_path: str) -> None:
    """In-code _FINAL_STATES must match fixture.final_states."""
    mod = importlib.import_module(module_path)
    final_states = getattr(mod, "_FINAL_STATES")
    fx = _load_fixture(fixture_name)
    assert set(final_states) == set(fx["final_states"]), (
        f"[{skill}] final_states={set(final_states)} vs fixture={set(fx['final_states'])}"
    )


def test_all_state_machines_covered() -> None:
    """Sanity: 3 state machines = 3 fixture files."""
    fixtures = list(_FIXTURE_DIR.glob("*.transitions.json"))
    assert len(fixtures) == 3, (
        f"Expected 3 state-machine fixtures, found: {sorted(f.name for f in fixtures)}"
    )
