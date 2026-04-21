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
requirements: [SPRINT-04, QUALITY-13]
must_haves:
  truths:
    - "HarnessPlugin.contribute_verification_pairs() exists as an optional hook returning list[VerificationPair], default []."
    - "PluginManager resolves each VerificationPair.verifier_dotted_path to a callable at plugin-load time."
    - "Resolved pairs are exposed via PluginManager.get_verification_pairs() (or similar accessor) for SprintConductor to consume."
    - "Existing plugins (ralph_loop, gstack_sprint, code_review etc.) that don't override the hook continue to work (default empty)."
    - "Import-time registration does not crash if a verifier_dotted_path is unresolvable (logged + skipped)."
  artifacts:
    - path: "clawteam/plugins/base.py"
      provides: "Optional contribute_verification_pairs hook on HarnessPlugin"
      contains: "def contribute_verification_pairs"
    - path: "clawteam/plugins/manager.py"
      provides: "Resolver that imports verifier_dotted_path + stashes (VerificationPair, callable) tuples"
      contains: "_verification_pairs"
    - path: "tests/test_plugins.py"
      provides: "Tests for hook default [], custom plugin returning pairs, dotted-path resolver"
      contains: "def test_contribute_verification_pairs_default_empty"
  key_links:
    - from: "clawteam/plugins/base.py"
      to: "clawteam/harness/cross_agent_verification_gate.py (VerificationPair)"
      via: "contribute_verification_pairs return type is list[VerificationPair]"
      pattern: "list[VerificationPair]"
    - from: "clawteam/plugins/manager.py"
      to: "PluginManager consumers (SprintConductor._build_gate_chain later)"
      via: "get_verification_pairs() accessor"
    - from: "Plan 11 (GstackSprintPlugin)"
      to: "contribute_verification_pairs"
      via: "Plugin overrides hook to return the two gstack verifiers"
---

<objective>
Add the optional `HarnessPlugin.contribute_verification_pairs()` hook (D-12), extend `PluginManager._instantiate_and_register` to resolve each returned `VerificationPair.verifier_dotted_path` to a callable at plugin-load time, and stash the resolved (pair, callable) tuples in a registry accessor so `SprintConductor._build_gate_chain` (Plan 10) can instantiate `CrossAgentVerificationGate` instances in later phases.

Purpose: This is the ONLY plugin-hook edit in Phase 4. The hook mirrors the existing optional pattern (`contribute_review_routers`, `contribute_evidence_schemas`) — empty default, resolved at plugin-load, consumed by later substrate. Phase 3's 5 existing plugin hooks are not modified.

Output: 1 line added to base.py (method default), ~25 lines added to manager.py (resolver + accessor), 1 test file updated with 4 tests.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md

<interfaces>
From clawteam/plugins/base.py (lines 14-93, existing):
```python
class HarnessPlugin(ABC):
    name: str = ""
    version: str = "0.1.0"
    # ...
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
  <done>Optional hook landed; resolver + accessor tested; existing plugin tests unregressed</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Plugin-declared dotted path ↔ importlib resolver | Attacker plugin could name a dotted path that triggers module import side-effects |
| Plugin load sequence ↔ verification_pairs registry | Two plugins contributing same (phase, source, target) would create duplicate gates |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-14 | E (Elevation of privilege) | importlib.import_module on plugin-controlled string | accept | Plugins are already trusted (they register as HarnessPlugin subclasses); importing an attacker-controlled module is equivalent in risk to running attacker Python code, which the plugin mechanism already enables |
| T-04-15 | D (DoS) | Unresolvable path crashes plugin load | mitigate | try/except around import + getattr; log warning; continue. test_unresolvable_dotted_path_skipped_with_log enforces |
| T-04-16 | T (Tampering) | Duplicate (phase, source, target) triples across plugins | accept | Plan 10 deduplicates at gate-list construction time if required; Phase 4 scope is the hook + accessor, not deduplication policy |
</threat_model>

<verification>
Plan 05 integration checks:
- [ ] `pytest tests/test_plugins.py tests/test_gstack_plugin.py tests/test_orchestrator_phase_registry.py -x -q` passes
- [ ] `python3 -c "from clawteam.plugins.base import HarnessPlugin; p = HarnessPlugin.__subclasses__()[0](); assert p.contribute_verification_pairs() == []"` exits 0 (OR use an importable concrete subclass; alternatively smoke-check via `hasattr(HarnessPlugin, 'contribute_verification_pairs')`)
- [ ] `grep -c "contribute_verification_pairs" clawteam/plugins/base.py clawteam/plugins/manager.py tests/test_plugins.py` prints 3 files with matches
- [ ] Phase 3 GstackSprintPlugin still loads without overriding the new hook (confirmed by tests/test_gstack_plugin.py)
</verification>

<success_criteria>
Plan 05 ships when:
- [ ] `HarnessPlugin.contribute_verification_pairs()` method exists with empty default
- [ ] `PluginManager._instantiate_and_register` resolves dotted paths to callables
- [ ] `PluginManager.get_verification_pairs()` returns `list[tuple[VerificationPair, Callable]]`
- [ ] Unresolvable paths log a warning but do NOT crash plugin load
- [ ] 5 new tests pass; all Phase 1/2/3 plugin tests still pass
- [ ] Plan 11 can override `contribute_verification_pairs` on `GstackSprintPlugin` to return the two gstack pairs
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-05-plugin-verification-hook-SUMMARY.md` with:
- Line counts of added code in base.py + manager.py
- Test coverage summary
- Confirmation: no existing plugin hook signatures changed
</output>
