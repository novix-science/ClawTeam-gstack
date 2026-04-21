"""Unit + fixture-driven tests for InvestigateState (Plan 04-09 — SAFETY-05 + QUALITY-07)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from clawteam.templates.gstack.skills.investigate import InvestigateState
from clawteam.templates.gstack.skills.investigate.state import (
    FREEZE_REASON_TEMPLATE,
    MAX_HYPOTHESES,
    _FINAL_STATES,
    _TRANSITIONS,
    _validate_module_path,
)


_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "gstack_state_machines" / "investigate.transitions.json"


class _FakeRegistry:
    """Captures freeze/unfreeze calls for assertion."""

    def __init__(self):
        self.freezes: list[dict] = []
        self.unfreezes: list[dict] = []

    def freeze(self, *, path, agent, reason, actor):
        self.freezes.append({"path": str(path), "agent": agent, "reason": reason, "actor": actor})

    def unfreeze(self, *, path, agent, reason, actor):
        self.unfreezes.append({"path": str(path), "agent": agent, "reason": reason, "actor": actor})


@pytest.fixture
def fixture_dict() -> dict:
    return json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))


def _new_state(team="t", sprint_id="s1", workspace="/tmp/repo") -> InvestigateState:
    return InvestigateState(team=team, sprint_id=sprint_id, workspace_branch=workspace)


def test_initial_state_is_idle():
    s = _new_state()
    assert s.current_state == "idle"
    assert s.hypothesis_count == 0
    assert s.current_module_path is None
    assert s.current_hypothesis_id is None


def test_transitions_match_fixture(fixture_dict):
    code_triples = {(k[0], k[1], v) for k, v in _TRANSITIONS.items()}
    fixture_triples = {(t["from"], t["event"], t["to"]) for t in fixture_dict["transitions"]}
    assert code_triples == fixture_triples


def test_max_hypotheses_is_3(fixture_dict):
    assert MAX_HYPOTHESES == fixture_dict["max_hypotheses"]
    assert MAX_HYPOTHESES == 3


def test_final_states_match_fixture(fixture_dict):
    assert set(_FINAL_STATES) == set(fixture_dict["final_states"])


def test_freeze_reason_template_matches_fixture(fixture_dict):
    assert FREEZE_REASON_TEMPLATE == fixture_dict["freeze_reason_template"]


def test_open_investigation_transitions_to_hypothesis_declared():
    s = _new_state()
    reg = _FakeRegistry()
    res = s.handle("open_investigation", turn=1, registry=reg)
    assert res.ok
    assert s.current_state == "hypothesis_declared"
    assert reg.freezes == []  # no freeze yet


def test_module_validated_enters_testing_and_freezes(tmp_path):
    ws = tmp_path
    (ws / "src").mkdir()
    (ws / "src" / "module.py").write_text("x = 1")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()

    s.handle("open_investigation", turn=1, registry=reg)
    res = s.handle(
        "module_validated",
        turn=2,
        module_path="src/module.py",
        hypothesis_id=1,
        registry=reg,
    )
    assert res.ok
    assert s.current_state == "hypothesis_testing"
    assert res.freeze_applied is True
    assert len(reg.freezes) == 1
    assert reg.freezes[0]["reason"] == "investigate:s1:1"
    assert reg.freezes[0]["agent"] == "reviewer"
    assert reg.freezes[0]["actor"] == "reviewer"


def test_confirmed_unfreezes_and_resolves(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    res = s.handle("confirmed", turn=3, registry=reg)
    assert res.ok
    assert s.current_state == "resolved"
    assert res.unfreeze_applied is True
    assert len(reg.unfreezes) == 1
    assert reg.unfreezes[0]["reason"] == "investigate:s1:1"


def test_disconfirmed_goes_to_disconfirmed_state(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    res = s.handle("disconfirmed", turn=3, registry=reg)
    assert res.ok
    assert s.current_state == "hypothesis_disconfirmed"
    # No unfreeze yet on disconfirmed alone.
    assert res.unfreeze_applied is False


def test_next_hypothesis_under_3_unfreezes_old(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    (ws / "y.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    s.handle("disconfirmed", turn=3, registry=reg)
    res = s.handle("next_hypothesis_if_under_3", turn=4, registry=reg)
    assert res.ok
    assert s.current_state == "hypothesis_declared"
    assert res.unfreeze_applied is True
    assert reg.unfreezes[-1]["reason"] == "investigate:s1:1"


def test_reached_3_halts(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    s.handle("disconfirmed", turn=3, registry=reg)
    res = s.handle("reached_3", turn=4, registry=reg)
    assert res.ok
    assert s.current_state == "halted_after_3"
    assert res.unfreeze_applied is True


def test_abandon_from_testing_unfreezes(tmp_path):
    ws = tmp_path
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    res = s.handle("abandon", turn=3, registry=reg)
    assert res.ok
    assert s.current_state == "abandoned"
    assert res.unfreeze_applied is True


def test_abandon_from_declared_no_unfreeze():
    s = _new_state()
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    res = s.handle("abandon", turn=2, registry=reg)
    assert res.ok
    assert s.current_state == "abandoned"
    assert res.unfreeze_applied is False
    assert reg.unfreezes == []


# -- Path validation (D-16) ---------------------------------------------

def test_path_validation_rejects_doublestar(tmp_path):
    with pytest.raises(ValueError, match="glob"):
        _validate_module_path("src/**/*.py", str(tmp_path))


def test_path_validation_rejects_wildcard_single_star(tmp_path):
    with pytest.raises(ValueError, match="glob"):
        _validate_module_path("src/*.py", str(tmp_path))


def test_path_validation_rejects_question_mark(tmp_path):
    with pytest.raises(ValueError, match="glob"):
        _validate_module_path("src/a?.py", str(tmp_path))


def test_path_validation_rejects_outside_workspace(tmp_path):
    with pytest.raises(ValueError, match="outside workspace"):
        _validate_module_path("/etc/passwd", str(tmp_path))


def test_path_validation_rejects_empty():
    with pytest.raises(ValueError):
        _validate_module_path("", "/tmp/x")


def test_path_validation_accepts_valid(tmp_path):
    (tmp_path / "ok.py").write_text("")
    # Should not raise
    resolved = _validate_module_path("ok.py", str(tmp_path))
    assert resolved.name == "ok.py"


def test_module_validated_without_module_path_fails(tmp_path):
    s = _new_state(workspace=str(tmp_path))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    res = s.handle("module_validated", turn=2, registry=reg)
    assert not res.ok
    assert "requires module_path" in res.reason


def test_module_validated_rejects_glob_path(tmp_path):
    s = _new_state(workspace=str(tmp_path))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    res = s.handle("module_validated", turn=2, module_path="src/**/*.py", hypothesis_id=1, registry=reg)
    assert not res.ok
    assert "glob" in res.reason
    assert s.current_state == "hypothesis_declared"  # not advanced


# -- Persistence --------------------------------------------------------

def test_save_load_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "x.py").write_text("")
    s = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    s.handle("open_investigation", turn=1, registry=reg)
    s.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    s.save()
    loaded = InvestigateState.load("t", "s1")
    assert loaded.current_state == "hypothesis_testing"
    assert loaded.current_module_path == "x.py"
    assert loaded.current_hypothesis_id == 1


def test_persistence_survives_simulated_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "x.py").write_text("")
    orig = _new_state(workspace=str(ws))
    reg = _FakeRegistry()
    orig.handle("open_investigation", turn=1, registry=reg)
    orig.handle("module_validated", turn=2, module_path="x.py", hypothesis_id=1, registry=reg)
    orig.save()
    del orig
    loaded = InvestigateState.load("t", "s1")
    assert loaded.current_state == "hypothesis_testing"
    assert [h.turn for h in loaded.history] == [1, 2]
