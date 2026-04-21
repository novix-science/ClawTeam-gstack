"""Tests for Phase 4 Plan 05: plugin verification-pair + gate hooks.

This file pairs with ``clawteam/plugins/base.py`` and
``clawteam/plugins/manager.py`` extensions shipped in Plan 04-05:

- ``HarnessPlugin.contribute_verification_pairs``  (Task 1, §04-CONTEXT D-12)
- ``PluginManager.get_verification_pairs``          (Task 1, §04-CONTEXT D-12)
- ``HarnessPlugin.contribute_gates``                (Task 2, §04-CONTEXT D-13 — formalization)
- ``PluginManager.get_plugin_gates``                (Task 2, §04-CONTEXT D-13)

Tests that import ``VerificationPair`` tolerate Plan 04-03 not yet having
landed (wave-parallel execution, Plan 01-03 cross-wave parallelism pattern):
when the module is absent, the pair-specific tests skip rather than error.
"""

from __future__ import annotations

import pytest

from clawteam.plugins.base import HarnessPlugin
from clawteam.plugins.manager import PluginManager

# Plan 04-03 lands clawteam.harness.cross_agent_verification_gate (VerificationPair
# + CrossAgentVerificationGate). During Wave 1 parallel execution that module may
# not exist yet — tolerate its absence for the pair-specific tests only.
VerificationPair = pytest.importorskip(
    "clawteam.harness.cross_agent_verification_gate",
    reason="Plan 04-03 module not yet landed (Wave 1 parallel execution)",
).VerificationPair


# Module-level verifier used by test plugins (importable dotted path).
def _dummy_verifier_ok(src, tgt):  # pragma: no cover — only reached if test runs
    return True, ""


def _dummy_verifier_fail(src, tgt):  # pragma: no cover
    return False, "mismatch"


class _PluginA(HarnessPlugin):
    name = "plugin-a"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_verification_pairs(self):
        return [
            VerificationPair(
                phase="test",
                source_artifact="a.md",
                target_artifact="b.md",
                verifier_dotted_path=f"{__name__}._dummy_verifier_ok",
            ),
        ]


class _PluginB(HarnessPlugin):
    name = "plugin-b"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_verification_pairs(self):
        return [
            VerificationPair(
                phase="review",
                source_artifact="c.md",
                target_artifact="d.md",
                verifier_dotted_path=f"{__name__}._dummy_verifier_fail",
            ),
        ]


class _PluginBroken(HarnessPlugin):
    name = "plugin-broken"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_verification_pairs(self):
        return [
            VerificationPair(
                phase="test",
                source_artifact="x.md",
                target_artifact="y.md",
                verifier_dotted_path="clawteam.not_a_module.missing_fn",
            ),
        ]


class _PluginEmpty(HarnessPlugin):
    name = "plugin-empty"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx
    # does NOT override contribute_verification_pairs


# ── Task 1: contribute_verification_pairs tests ───────────────────────────


def test_contribute_verification_pairs_default_empty():
    p = _PluginEmpty()
    assert p.contribute_verification_pairs() == []


def test_contribute_verification_pairs_custom_returns_list():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginA)
    pairs = pm.get_verification_pairs()
    assert len(pairs) == 1
    pair, verifier = pairs[0]
    assert pair.phase == "test"
    assert pair.source_artifact == "a.md"
    assert pair.target_artifact == "b.md"
    assert callable(verifier)
    # Verifier is the module-level fn we declared.
    assert verifier is _dummy_verifier_ok


def test_unresolvable_dotted_path_skipped_with_log(caplog):
    pm = PluginManager()
    with caplog.at_level("WARNING"):
        pm._instantiate_and_register(_PluginBroken)
    pairs = pm.get_verification_pairs()
    assert pairs == []
    # A warning was logged naming the unresolvable path
    assert any(
        "not_a_module" in rec.message or "missing_fn" in rec.message
        for rec in caplog.records
    )


def test_multiple_plugins_verification_pairs_aggregated():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginA)
    pm._instantiate_and_register(_PluginB)
    pairs = pm.get_verification_pairs()
    assert len(pairs) == 2
    phases = sorted(p[0].phase for p in pairs)
    assert phases == ["review", "test"]


def test_empty_plugin_contributes_no_pairs():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginEmpty)
    assert pm.get_verification_pairs() == []


# ── Task 2: contribute_gates + get_plugin_gates tests ─────────────────────

from clawteam.harness.phases import PhaseGate


class _StubGateA(PhaseGate):
    name = "stub-gate-a"

    def check(self, state):
        return True, ""


class _StubGateB(PhaseGate):
    name = "stub-gate-b"

    def check(self, state):
        return True, ""


class _PluginGatesShip(HarnessPlugin):
    name = "plugin-gates-ship"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_gates(self):
        return {"ship": [_StubGateA()]}


class _PluginGatesTestAndShip(HarnessPlugin):
    name = "plugin-gates-test-and-ship"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_gates(self):
        return {"test": [_StubGateB()], "ship": [_StubGateA()]}


class _PluginGatesBroken(HarnessPlugin):
    name = "plugin-gates-broken"
    version = "0.1.0"

    def on_register(self, ctx):
        self._ctx = ctx

    def contribute_gates(self):
        raise RuntimeError("intentional test failure")


def test_contribute_gates_optional():
    """A plugin not overriding contribute_gates inherits empty-dict default."""
    p = _PluginEmpty()  # Task 1 helper — does NOT override contribute_gates
    assert p.contribute_gates() == {}


def test_contribute_gates_default_empty():
    """HarnessPlugin base-class contribute_gates returns {} (BC)."""
    assert HarnessPlugin.contribute_gates(_PluginEmpty()) == {}


def test_plugin_gates_collected_per_phase():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginGatesShip)
    pm._instantiate_and_register(_PluginGatesTestAndShip)
    ship_gates = pm.get_plugin_gates("ship")
    # Two plugins each contributed one gate to ship → 2 gates, load-order preserved.
    assert len(ship_gates) == 2
    assert isinstance(ship_gates[0], _StubGateA)  # plugin-gates-ship first
    assert isinstance(ship_gates[1], _StubGateA)  # plugin-gates-test-and-ship second


def test_plugin_gates_nonexistent_phase_returns_empty():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginGatesShip)
    assert pm.get_plugin_gates("unregistered-phase") == []


def test_plugin_gates_multiple_phases_segregated():
    pm = PluginManager()
    pm._instantiate_and_register(_PluginGatesTestAndShip)
    test_gates = pm.get_plugin_gates("test")
    ship_gates = pm.get_plugin_gates("ship")
    assert len(test_gates) == 1
    assert isinstance(test_gates[0], _StubGateB)
    assert len(ship_gates) == 1
    assert isinstance(ship_gates[0], _StubGateA)


def test_plugin_gates_existing_plugins_unaffected():
    """Phase 3 plugin (not overriding contribute_gates) contributes nothing."""
    pm = PluginManager()
    pm._instantiate_and_register(_PluginEmpty)
    for phase in ("think", "plan", "build", "review", "test", "ship", "reflect"):
        assert pm.get_plugin_gates(phase) == [], (
            f"_PluginEmpty leaked gates into phase {phase!r}"
        )


def test_plugin_gates_broken_return_skipped_with_log(caplog):
    pm = PluginManager()
    with caplog.at_level("WARNING"):
        pm._instantiate_and_register(_PluginGatesBroken)
        # Other plugins can still load after a broken one.
        pm._instantiate_and_register(_PluginGatesShip)
    # Ship still has the good plugin's gate despite the broken plugin.
    assert len(pm.get_plugin_gates("ship")) == 1
    assert any(
        "contribute_gates raised" in r.message for r in caplog.records
    )
