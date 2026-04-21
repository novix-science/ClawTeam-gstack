---
phase: 04
plan: 05
type: execute
wave: 1
depends_on: [01, 03]
files_modified:
  - clawteam/plugins/base.py
  - clawteam/plugins/manager.py
  - tests/test_plugins.py
autonomous: true
requirements: [SPRINT-04, SPRINT-05, QUALITY-13]
must_haves:
  truths:
    - "HarnessPlugin.contribute_verification_pairs() exists as an optional hook returning list[VerificationPair], default []."
    - "HarnessPlugin.contribute_gates() exists as an optional hook returning dict[str, list[PhaseGate]], default {} — REVISION: the base class hook declaration that Plan 11's GstackSprintPlugin overrides for ShipApprovalGate."
    - "PluginManager resolves each VerificationPair.verifier_dotted_path to a callable at plugin-load time."
    - "Resolved pairs are exposed via PluginManager.get_verification_pairs() for SprintConductor to consume."
    - "Plugin-contributed gates are aggregated per phase via PluginManager.get_plugin_gates(phase) for SprintConductor._build_gate_chain (Plan 10) to consume."
    - "Existing plugins (ralph_loop, gstack_sprint, code_review etc.) that don't override the hooks continue to work (default empty)."
    - "Import-time registration does not crash if a verifier_dotted_path is unresolvable (logged + skipped)."
  artifacts:
    - path: "clawteam/plugins/base.py"
      provides: "Optional contribute_verification_pairs + contribute_gates hooks on HarnessPlugin"
      contains: "def contribute_verification_pairs"
    - path: "clawteam/plugins/manager.py"
      provides: "Resolver that imports verifier_dotted_path + stashes (VerificationPair, callable) tuples; plugin gates aggregator"
      contains: "_verification_pairs"
    - path: "tests/test_plugins.py"
      provides: "Tests for hook defaults, custom plugins, dotted-path resolver, gate aggregator"
      contains: "def test_contribute_verification_pairs_default_empty"
  key_links:
    - from: "clawteam/plugins/base.py"
      to: "clawteam/harness/cross_agent_verification_gate.py (VerificationPair)"
      via: "contribute_verification_pairs return type is list[VerificationPair]"
      pattern: "list[VerificationPair]"
    - from: "clawteam/plugins/base.py"
      to: "clawteam/harness/phases.py (PhaseGate)"
      via: "contribute_gates return type is dict[str, list[PhaseGate]]"
      pattern: "dict[str, list[PhaseGate]]"
    - from: "clawteam/plugins/manager.py"
      to: "PluginManager consumers (SprintConductor._build_gate_chain in Plan 10)"
      via: "get_verification_pairs() + get_plugin_gates(phase) accessors"
    - from: "Plan 11 (GstackSprintPlugin)"
      to: "contribute_verification_pairs + contribute_gates"
      via: "Plugin overrides hooks to return gstack verifiers + ShipApprovalGate"
---

<objective>
Add TWO optional `HarnessPlugin` hooks (D-12 + D-13 wiring): `contribute_verification_pairs()` returning `list[VerificationPair]`, and `contribute_gates()` returning `dict[str, list[PhaseGate]]`. Extend `PluginManager._instantiate_and_register` to (a) resolve each `VerificationPair.verifier_dotted_path` to a callable at plugin-load time and stash the resolved (pair, callable) tuples in a registry accessor, and (b) aggregate plugin-contributed gates per-phase for `SprintConductor._build_gate_chain` (Plan 10) to consume when constructing the gate chain.

Purpose: This plan ships TWO plugin-hook edits in Phase 4. Both hooks mirror the existing optional pattern (`contribute_review_routers`, `contribute_evidence_schemas`) — empty default, resolved/aggregated at plugin-load, consumed by later substrate. Phase 3's 5 existing plugin hooks are not modified.

**REVISION NOTE (ISS-03 closure):** The original plan shipped only `contribute_verification_pairs`. Plan 11's `GstackSprintPlugin.contribute_gates` was orphaned because `HarnessPlugin` already had a placeholder `contribute_gates` in the base class BUT `PluginManager` never consumed it — so `ShipApprovalGate` was unreachable in production. Task 2 in this plan formalizes the hook signature AND adds `PluginManager.get_plugin_gates(phase)` so `SprintConductor._build_gate_chain` (Plan 10 Task 3) can union plugin gates into the chain.

Output: 1 line added to base.py for verification-pairs hook (gates hook already exists — we formalize docstring only), ~40 lines added to manager.py (verifier resolver + accessor + plugin-gate aggregator), test file updated with ~8 tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md

<interfaces>
From clawteam/plugins/base.py (existing, lines 14-93):
```python
class HarnessPlugin(ABC):
    name: str = ""
    version: str = "0.1.0"
    # ...
    def contribute_gates(self) -> dict[str, list[PhaseGate]]:
        """Contribute gates to specific phases. Returns {phase: [gates]}."""
        return {}  # <-- ALREADY EXISTS; this plan extends docstring + consumer wiring.
    def contribute_phases(self) -> list[Phase]: return []
    def contribute_phase_roles(self) -> dict[Phase, list[str]]: return {}
    def contribute_review_routers(self) -> list[ReviewRouter]: return []
    def contribute_evidence_schemas(self) -> dict[str, type]: return {}
    # Pattern: optional hooks with empty defaults preserve BC for existing plugins.
```

From clawteam/plugins/manager.py (lines 139-168, existing):
```python
def _instantiate_and_register(self, cls: type) -> HarnessPlugin:
    plugin = cls()
    ctx = self._build_context()
    plugin.on_register(ctx)
    # Populate phase registry with contributions.
    from clawteam.harness.phase_registry import get_registry
    get_registry().register(
        plugin.name,
        plugin.contribute_phases(),
        plugin.contribute_phase_roles(),
        plugin.contribute_review_routers(),
    )
    # Phase 2: funnel contribute_evidence_schemas into EvidenceSchemaRegistry.
    schemas = plugin.contribute_evidence_schemas() or {}
    if schemas:
        # ... register_schema calls ...
    self._loaded[plugin.name] = plugin
    return plugin
```

From clawteam/harness/cross_agent_verification_gate.py (Plan 03):
```python
class VerificationPair(BaseModel):
    phase: str
    source_artifact: str
    target_artifact: str
    verifier_dotted_path: str
```

From clawteam/harness/phases.py:
```python
class PhaseGate(ABC):
    def check(self, state) -> tuple[bool, str]: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add contribute_verification_pairs hook to HarnessPlugin + PluginManager resolver</name>
  <files>clawteam/plugins/base.py, clawteam/plugins/manager.py, tests/test_plugins.py</files>
  <read_first>
    - clawteam/plugins/base.py (entire file — study optional-hook convention)
    - clawteam/plugins/manager.py (entire file — study _instantiate_and_register + _loaded registry)
    - clawteam/harness/cross_agent_verification_gate.py (VerificationPair from Plan 03)
    - tests/test_plugins.py (existing — find patterns for mock plugins + manager init)
  </read_first>
  <behavior>
    - Test 1 (test_contribute_verification_pairs_default_empty): Instantiate a plugin subclass without overriding the hook → returns `[]`.
    - Test 2 (test_contribute_verification_pairs_custom_returns_list): Subclass overrides hook → returns the declared list; after manager registers, accessor returns the resolved (pair, callable) tuples.
    - Test 3 (test_unresolvable_dotted_path_skipped_with_log): Pair with `verifier_dotted_path="clawteam.not_a_module.missing"` does NOT crash plugin load; manager logs warning; resolved list omits that pair.
    - Test 4 (test_existing_plugins_unaffected): Load an existing plugin (gstack_sprint_plugin or a mock ralph_loop_plugin) → `get_verification_pairs()` returns empty list (or no entry for that plugin).
    - Test 5 (test_multiple_plugins_verification_pairs_aggregated): Two plugins each contributing 1 pair → accessor returns 2 pairs.
  </behavior>
  <action>
**Edit 1: `clawteam/plugins/base.py`** — append one method to `HarnessPlugin` class, after `contribute_evidence_schemas` (around line 93). Insertion:

```python
    # ── Phase 4 / Plan 04-05 hook ─────────────────────────────────────

    def contribute_verification_pairs(self) -> list["VerificationPair"]:
        """Contribute cross-agent verification pairs (§04-CONTEXT D-12).

        Returns a list of :class:`VerificationPair` describing which artifact
        pairs should be cross-verified at which phase by which verifier
        function (dotted-path indexed). ``PluginManager`` resolves each
        ``verifier_dotted_path`` to a callable at plugin-load time and wires
        them into the gate chain consumed by SprintConductor (Plan 04-10
        _dispatch_review_phase + Plan 04-11 GstackSprintPlugin).

        Empty-list default means the plugin contributes no cross-verification
        gates. Phase 4's GstackSprintPlugin returns two pairs:
          - test-report.md ↔ build-report.md  (qa verifies engineer's output)
          - design-doc.md  ↔ office-hours-answers  (reviewer verifies designer)

        Hook is optional; existing plugins (software-dev, hedge-fund, code-review,
        harness-default, research-paper, strategy-room, ralph-loop) inherit the
        empty-list default and are unaffected.
        """
        return []
```

And add TYPE_CHECKING import at the top of `clawteam/plugins/base.py` (inside the existing `if TYPE_CHECKING:` block around line 8-11):
```python
if TYPE_CHECKING:
    from clawteam.harness.context import HarnessContext
    from clawteam.harness.cross_agent_verification_gate import VerificationPair  # NEW
    from clawteam.harness.phases import Phase, PhaseGate
    from clawteam.harness.review_router import ReviewRouter
```

**Edit 2: `clawteam/plugins/manager.py`** — extend `_instantiate_and_register` (around line 139-168) to resolve verification pairs. Also add a registry field on `PluginManager` and a public accessor. Insertion points:

a) Add `_verification_pairs` initialization in `__init__` (grep for `def __init__` in manager.py — add after the existing `self._loaded = {}` line):
```python
        # Phase 4 Plan 05 additive: resolved (VerificationPair, callable) tuples.
        # Populated by _instantiate_and_register from plugin.contribute_verification_pairs.
        self._verification_pairs: list[tuple[Any, Any]] = []
```

b) Add imports at top of manager.py (inside `TYPE_CHECKING` block if present, otherwise regular top-of-file):
```python
import importlib
import logging
from typing import Any

_logger = logging.getLogger(__name__)
```

c) Extend `_instantiate_and_register` — after the existing `contribute_evidence_schemas` block, before `self._loaded[plugin.name] = plugin`:
```python
        # Phase 4 / Plan 04-05: resolve verification pairs.
        pairs = plugin.contribute_verification_pairs() or []
        for pair in pairs:
            try:
                module_path, _, attr = pair.verifier_dotted_path.rpartition(".")
                if not module_path or not attr:
                    raise ValueError(
                        f"invalid verifier_dotted_path {pair.verifier_dotted_path!r}"
                    )
                module = importlib.import_module(module_path)
                verifier = getattr(module, attr, None)
                if verifier is None or not callable(verifier):
                    raise AttributeError(
                        f"verifier {attr!r} in {module_path!r} not found or not callable"
                    )
                self._verification_pairs.append((pair, verifier))
            except Exception as exc:  # noqa: BLE001 — plugin load must not crash
                _logger.warning(
                    "Plugin %s: could not resolve verifier %s: %s",
                    plugin.name,
                    pair.verifier_dotted_path,
                    exc,
                )
                continue
```

d) Add public accessor:
```python
    def get_verification_pairs(self) -> list[tuple[Any, Any]]:
        """Return resolved [(VerificationPair, verifier_callable), ...] (§04-CONTEXT D-12).

        Consumed by SprintConductor._build_gate_chain (Plan 04-10) when
        constructing CrossAgentVerificationGate instances per phase.
        """
        return list(self._verification_pairs)
```

**Edit 3: `tests/test_plugins.py`** — APPEND the five tests below (do NOT modify existing tests). Create the file if it does not exist; otherwise append at end.

```python
# ── Phase 4 Plan 05: contribute_verification_pairs tests ─────────────────

from clawteam.plugins.base import HarnessPlugin
from clawteam.plugins.manager import PluginManager
from clawteam.harness.cross_agent_verification_gate import VerificationPair


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

    def contribute_verification_pairs(self) -> list[VerificationPair]:
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

    def contribute_verification_pairs(self) -> list[VerificationPair]:
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

    def contribute_verification_pairs(self) -> list[VerificationPair]:
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
    assert any("not_a_module" in rec.message or "missing_fn" in rec.message for rec in caplog.records)


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
```

**Do not modify** existing hooks (contribute_phases, contribute_phase_roles, contribute_review_routers, contribute_evidence_schemas) or existing Phase 3 plugins.
  </action>
  <verify>
    <automated>pytest tests/test_plugins.py::test_contribute_verification_pairs_default_empty tests/test_plugins.py::test_contribute_verification_pairs_custom_returns_list tests/test_plugins.py::test_unresolvable_dotted_path_skipped_with_log tests/test_plugins.py::test_multiple_plugins_verification_pairs_aggregated tests/test_plugins.py::test_empty_plugin_contributes_no_pairs -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "def contribute_verification_pairs" clawteam/plugins/base.py
    - grep -q "_verification_pairs" clawteam/plugins/manager.py
    - grep -q "def get_verification_pairs" clawteam/plugins/manager.py
    - grep -q "importlib.import_module" clawteam/plugins/manager.py
    - pytest tests/test_plugins.py -x -q passes all 5 new tests + all existing Phase 1/2/3 plugin tests
    - pytest tests/test_gstack_plugin.py -x -q passes (Phase 3 plugin unaffected)
    - pytest tests/test_orchestrator_phase_registry.py -x -q passes (Phase 1 plugin hook unaffected)
  </acceptance_criteria>
  <done>Optional verification-pair hook landed; resolver + accessor tested; existing plugin tests unregressed</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Formalize contribute_gates hook on HarnessPlugin + PluginManager.get_plugin_gates aggregator (REVISION — closes ISS-03)</name>
  <files>clawteam/plugins/base.py, clawteam/plugins/manager.py, tests/test_plugins.py</files>
  <read_first>
    - clawteam/plugins/base.py (existing contribute_gates around line 36-38 — already declared but unwired)
    - clawteam/plugins/manager.py (after Task 1 edits — find _instantiate_and_register flow)
    - clawteam/harness/phases.py (PhaseGate ABC shape)
    - clawteam/harness/ship_approval_gate.py (Plan 04 — ShipApprovalGate subclass that consumers use)
    - clawteam/sprint/conductor.py::_build_gate_chain (the consumer in Plan 10 Task 3)
  </read_first>
  <behavior>
    - Test 1 (test_contribute_gates_optional): A plugin subclass that does NOT override contribute_gates returns `{}` by default (BC check).
    - Test 2 (test_contribute_gates_default_empty): Calling `HarnessPlugin.contribute_gates()` on a bare subclass yields `{}` (no phases declared).
    - Test 3 (test_plugin_gates_collected_per_phase): Two plugins each contribute one gate to phase "test" — `PluginManager.get_plugin_gates("test")` returns both gates in deterministic (plugin-load) order.
    - Test 4 (test_plugin_gates_nonexistent_phase_returns_empty): `get_plugin_gates("unregistered-phase")` returns `[]`.
    - Test 5 (test_plugin_gates_multiple_phases_segregated): One plugin contributes `{"ship": [g1], "test": [g2]}` — `get_plugin_gates("ship")` returns `[g1]`, `get_plugin_gates("test")` returns `[g2]`.
    - Test 6 (test_plugin_gates_existing_plugins_unaffected): Loading a Phase-3 plugin (gstack_sprint_plugin) that currently does not override contribute_gates yields empty dict for every phase (BC check — Plan 11 Task 2 will land the actual override).
    - Test 7 (test_plugin_gates_broken_return_skipped_with_log): Plugin whose contribute_gates raises is skipped with a warning; other plugins still contribute.
  </behavior>
  <action>
**Edit 1: `clawteam/plugins/base.py`** — the `contribute_gates` method ALREADY exists at line 36-38 with signature `def contribute_gates(self) -> dict[str, list[PhaseGate]]: return {}`. Expand its docstring so the contract is explicit. Replace the 3-line stub with:

```python
    def contribute_gates(self) -> dict[str, list[PhaseGate]]:
        """Contribute gates to specific phases (§04-CONTEXT D-13 — Plan 04-05 wiring).

        Returns a mapping of phase-name → list of :class:`PhaseGate` instances
        to append to that phase's gate chain. ``PluginManager`` aggregates
        plugin-contributed gates via :meth:`PluginManager.get_plugin_gates`
        (Phase 4 Plan 04-05); ``SprintConductor._build_gate_chain`` (Phase 4
        Plan 04-10 Task 3) unions those gates into the standard
        EvidenceGate → forced_progress_gate → InteractionGate chain so
        plugin-provided gates (e.g., Phase 4's ShipApprovalGate) actually
        execute.

        Empty-dict default means the plugin contributes no gates. Existing
        plugins (software-dev, hedge-fund, code-review, harness-default,
        research-paper, strategy-room, ralph-loop) inherit the empty default
        and are unaffected. Phase 4's GstackSprintPlugin overrides this in
        Plan 04-11 to return ``{"ship": [ShipApprovalGate()]}``.
        """
        return {}
```

**Edit 2: `clawteam/plugins/manager.py`** — add a per-phase gate aggregator. Two additions:

a) Add `_plugin_gates` initialization in `__init__` (right after the Task 1 `_verification_pairs` line):
```python
        # Phase 4 Plan 05 additive: aggregated {phase: [PhaseGate, ...]} from
        # plugin.contribute_gates. Consumed by SprintConductor._build_gate_chain
        # (Plan 10 Task 3). Preserves plugin-load order per phase.
        self._plugin_gates: dict[str, list[Any]] = {}
```

b) Extend `_instantiate_and_register` — after the Task 1 verification-pairs block, still before `self._loaded[plugin.name] = plugin`:
```python
        # Phase 4 / Plan 04-05 Task 2: aggregate plugin-contributed gates per phase.
        try:
            gates_map = plugin.contribute_gates() or {}
        except Exception as exc:  # noqa: BLE001 — plugin load must not crash
            _logger.warning(
                "Plugin %s: contribute_gates raised: %s", plugin.name, exc
            )
            gates_map = {}
        for phase_name, gate_list in gates_map.items():
            if not isinstance(phase_name, str) or not phase_name:
                _logger.warning(
                    "Plugin %s: contribute_gates invalid phase key %r skipped",
                    plugin.name,
                    phase_name,
                )
                continue
            bucket = self._plugin_gates.setdefault(phase_name, [])
            for gate in (gate_list or []):
                bucket.append(gate)
```

c) Add public accessor after `get_verification_pairs`:
```python
    def get_plugin_gates(self, phase: str) -> list[Any]:
        """Return list of plugin-contributed gates for ``phase`` (§04-CONTEXT D-13).

        Consumed by SprintConductor._build_gate_chain (Plan 04-10 Task 3) so
        plugin-contributed gates (e.g., Phase 4's ShipApprovalGate attached to
        "ship") actually execute. Returns an empty list when no plugin contributed
        gates for this phase. Order preserves plugin-load order.
        """
        return list(self._plugin_gates.get(phase, []))
```

**Edit 3: `tests/test_plugins.py`** — APPEND these seven tests at end of file (do NOT modify existing tests or Task 1 tests):

```python
# ── Phase 4 Plan 05 Task 2: contribute_gates + get_plugin_gates tests ────

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
    assert any("contribute_gates raised" in r.message for r in caplog.records)
```

**Do not modify** existing hooks, existing Phase 3 plugins, or Task 1's tests/additions.
  </action>
  <verify>
    <automated>pytest tests/test_plugins.py::test_contribute_gates_optional tests/test_plugins.py::test_contribute_gates_default_empty tests/test_plugins.py::test_plugin_gates_collected_per_phase tests/test_plugins.py::test_plugin_gates_nonexistent_phase_returns_empty tests/test_plugins.py::test_plugin_gates_multiple_phases_segregated tests/test_plugins.py::test_plugin_gates_existing_plugins_unaffected tests/test_plugins.py::test_plugin_gates_broken_return_skipped_with_log -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "Plan 04-05 wiring" clawteam/plugins/base.py  # expanded docstring present
    - grep -q "_plugin_gates" clawteam/plugins/manager.py
    - grep -q "def get_plugin_gates" clawteam/plugins/manager.py
    - grep -q "contribute_gates raised" clawteam/plugins/manager.py  # logging on failure
    - pytest tests/test_plugins.py -x -q passes all 7 new tests + all Task 1 tests + all existing Phase 1/2/3 plugin tests
    - pytest tests/test_gstack_plugin.py -x -q passes (Phase 3 plugin unaffected; Plan 11's contribute_gates override lands in a later plan wave)
  </acceptance_criteria>
  <done>contribute_gates hook formalized on HarnessPlugin; PluginManager.get_plugin_gates aggregator wired; consumer contract ready for SprintConductor._build_gate_chain (Plan 10 Task 3)</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Plugin-declared dotted path ↔ importlib resolver | Attacker plugin could name a dotted path that triggers module import side-effects |
| Plugin load sequence ↔ verification_pairs registry | Two plugins contributing same (phase, source, target) would create duplicate gates |
| Plugin-declared gate instance ↔ gate chain consumer | Attacker plugin could register a gate that always returns (False, ...) to DoS a phase |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-14 | E (Elevation of privilege) | importlib.import_module on plugin-controlled string | accept | Plugins are already trusted (they register as HarnessPlugin subclasses); importing an attacker-controlled module is equivalent in risk to running attacker Python code, which the plugin mechanism already enables |
| T-04-15 | D (DoS) | Unresolvable path crashes plugin load | mitigate | try/except around import + getattr; log warning; continue. test_unresolvable_dotted_path_skipped_with_log enforces |
| T-04-16 | T (Tampering) | Duplicate (phase, source, target) triples across plugins | accept | Plan 10 deduplicates at gate-list construction time if required; Phase 4 scope is the hook + accessor, not deduplication policy |
| T-04-17 | D (DoS) | contribute_gates raising crashes plugin load | mitigate | try/except around contribute_gates call; log warning; continue loading other plugins. test_plugin_gates_broken_return_skipped_with_log enforces |
| T-04-18 | T (Tampering) | Malicious plugin registers an always-fail gate | accept | Plugins are trusted; if an agent loads a hostile plugin, it already has Python code-execution equivalence |
</threat_model>

<verification>
Plan 05 integration checks:
- [ ] `pytest tests/test_plugins.py tests/test_gstack_plugin.py tests/test_orchestrator_phase_registry.py -x -q` passes
- [ ] `python3 -c "from clawteam.plugins.base import HarnessPlugin; assert hasattr(HarnessPlugin, 'contribute_verification_pairs'); assert hasattr(HarnessPlugin, 'contribute_gates')"` exits 0
- [ ] `grep -c "contribute_verification_pairs" clawteam/plugins/base.py clawteam/plugins/manager.py tests/test_plugins.py` prints 3 files with matches
- [ ] `grep -c "get_plugin_gates" clawteam/plugins/manager.py tests/test_plugins.py` prints 2 files with matches
- [ ] Phase 3 GstackSprintPlugin still loads without overriding either new hook (confirmed by tests/test_gstack_plugin.py)
</verification>

<success_criteria>
Plan 05 ships when:
- [ ] `HarnessPlugin.contribute_verification_pairs()` method exists with empty default
- [ ] `HarnessPlugin.contribute_gates()` method has expanded docstring referencing Plan 04-05 wiring + Plan 04-10 consumer
- [ ] `PluginManager._instantiate_and_register` resolves dotted paths to callables AND aggregates plugin gates per phase
- [ ] `PluginManager.get_verification_pairs()` returns `list[tuple[VerificationPair, Callable]]`
- [ ] `PluginManager.get_plugin_gates(phase)` returns `list[PhaseGate]` (plugin-load order preserved)
- [ ] Unresolvable verifier paths log a warning but do NOT crash plugin load
- [ ] `contribute_gates` raising logs a warning but does NOT crash plugin load
- [ ] 5 Task 1 tests + 7 Task 2 tests pass; all Phase 1/2/3 plugin tests still pass
- [ ] Plan 11 can override `contribute_verification_pairs` on `GstackSprintPlugin` to return the two gstack pairs
- [ ] Plan 11 can override `contribute_gates` on `GstackSprintPlugin` to return `{"ship": [ShipApprovalGate()]}`
- [ ] Plan 10 Task 3 can call `plugin_manager.get_plugin_gates(phase)` in `_build_gate_chain` to union plugin gates into the chain
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-05-plugin-verification-hook-SUMMARY.md` with:
- Line counts of added code in base.py + manager.py
- Test coverage summary (Task 1: 5 tests; Task 2: 7 tests)
- Confirmation: no existing plugin hook signatures changed
- Confirmation: both hooks ready for Plan 10 + Plan 11 consumers
</output>
