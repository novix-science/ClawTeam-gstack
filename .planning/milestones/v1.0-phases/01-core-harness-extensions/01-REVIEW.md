---
phase: 01-core-harness-extensions
reviewed: 2026-04-17T00:00:00Z
depth: standard
files_reviewed: 20
files_reviewed_list:
  - clawteam/harness/interaction_gate.py
  - clawteam/harness/orchestrator.py
  - clawteam/harness/phase_registry.py
  - clawteam/harness/review_router.py
  - clawteam/plugins/base.py
  - clawteam/plugins/manager.py
  - clawteam/sprint/__init__.py
  - clawteam/sprint/qa.py
  - clawteam/sprint/state.py
  - tests/fixtures/qa/answer_freeform.md
  - tests/fixtures/qa/answer_multi_choice.md
  - tests/fixtures/qa/question_confirm.md
  - tests/fixtures/qa/question_freeform.md
  - tests/fixtures/qa/question_multi_choice.md
  - tests/test_interaction_gate.py
  - tests/test_orchestrator_phase_registry.py
  - tests/test_phase_registry.py
  - tests/test_plugin_hooks.py
  - tests/test_sprint_qa.py
  - tests/test_sprint_state.py
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 20
**Status:** issues_found

## Summary

Phase 01 adds the plugin-facing extension surface that Phase 2+ will build on: `PhaseRegistry`, three new optional `HarnessPlugin` hooks, `SprintState` persistence (with `file_locked` + `atomic_write_text`), the Question/Answer markdown-frontmatter schema, `InteractionGate`, and `HarnessOrchestrator` wiring. The implementation is careful about path-traversal (both `SprintState.save` and `InteractionGate._resolve_sprint_dir` route through `validate_identifier` + `ensure_within_root`), the stdlib-only frontmatter parser is appropriately narrow, and the registry's duplicate-phase / role-subset validation matches RFC 001 §4.2–§4.3a.

Tests are thorough and include concurrency (8-thread race on `SprintState.save`), symlink-escape, and parser round-trip. No critical security issues were found.

The notable warnings cluster around two seams: (1) `HarnessOrchestrator.load()` does not restore the new `sprint_state` attribute, producing an attribute-access bug on the composition path introduced by this phase; (2) `PluginManager._instantiate_and_register` leaves partial plugin side effects behind when `PhaseRegistry.register()` raises after `on_register()` has already run. The remaining items are smaller quality concerns (silent `except Exception: pass` chains in plugin discovery, dead code in `InteractionGate._resolve_sprint_dir`, the conservative "first role wins" narrowing in orchestrator phase-role merging).

## Warnings

### WR-01: `HarnessOrchestrator.load()` does not restore `sprint_state`, causing `AttributeError` on the composition path

**File:** `clawteam/harness/orchestrator.py:163-179`
**Issue:** The `__init__` adds a new `self.sprint_state` attribute (line 44), but the alternative-construction path in `load()` manually sets `team_name`, `goal`, `cli`, `agent_count`, `state`, `runner`, `artifacts` via `cls.__new__(cls)` and never assigns `sprint_state`. Any caller that persists the orchestrator and later loads it will hit `AttributeError: 'HarnessOrchestrator' object has no attribute 'sprint_state'` on first access — including via `find_latest()` which calls `load()` internally. `SprintState` is not persisted to the harness `state.json` either, so even restoring it would require reading it from its own canonical path.

**Fix:**
```python
@classmethod
def load(cls, team_name: str, harness_id: str) -> HarnessOrchestrator | None:
    base = get_data_dir() / "harness"
    state_path = base / team_name / harness_id / "state.json"
    if not state_path.is_file():
        return None
    runner = PhaseRunner.load(state_path)
    orch = cls.__new__(cls)
    orch.team_name = team_name
    orch.goal = runner.state.goal
    orch.cli = runner.state.cli
    orch.agent_count = runner.state.agent_count
    orch.state = runner.state
    orch.runner = runner
    orch.artifacts = ArtifactStore(base, team_name, harness_id)
    orch.sprint_state = None  # minimum fix; future work may reload from SprintState.load() if a sprint_id is persisted in runner.state.artifacts
    return orch
```
A follow-up should persist the composed `sprint_id` on `PhaseState` (e.g., under `artifacts` or a new field) so `load()` can call `SprintState.load(team, sprint_id)` to re-hydrate. Add a regression test covering `HarnessOrchestrator.load(...).sprint_state is None` and (once sprint_id persistence lands) a successful re-hydration.

### WR-02: `PluginManager._instantiate_and_register` leaks side effects when `PhaseRegistry.register()` raises

**File:** `clawteam/plugins/manager.py:139-153`
**Issue:** The ordering is:
1. `plugin.on_register(ctx)` — subscribes to `ctx.bus`, may register tasks/spawners/sessions.
2. `get_registry().register(...)` — raises `ValueError` on duplicate phase names (across plugins) or on `phase_roles` keys referencing phases not declared by the plugin.
3. `self._loaded[plugin.name] = plugin`.

If step 2 raises, the plugin has already run `on_register` — event-bus subscriptions and any other side effects are live — but the plugin is not in `self._loaded`, so `PluginManager.unload(name)` cannot clean up. The exception propagates uncaught. This is fragile in CI/tests where a duplicate-phase condition is possible (and the test suite in `test_plugin_hooks.py:48-56` already constructs a scenario where the registry can be in an unknown state if `reset_registry` is skipped).

**Fix:** Validate contributions *before* calling `on_register`, or wrap `on_register` in a try/except that calls `plugin.on_unregister()` on failure. Preferred is to gather hook output first:
```python
def _instantiate_and_register(self, cls: type) -> HarnessPlugin:
    plugin = cls()
    phases = plugin.contribute_phases()
    phase_roles = plugin.contribute_phase_roles()
    review_routers = plugin.contribute_review_routers()
    # Register with the phase registry FIRST — this validates duplicates before
    # any event-bus wiring happens in on_register.
    from clawteam.harness.phase_registry import get_registry
    get_registry().register(plugin.name, phases, phase_roles, review_routers)
    # Only now perform side-effectful registration.
    ctx = self._build_context()
    try:
        plugin.on_register(ctx)
    except Exception:
        # Best-effort rollback of registry contribution (needs a new
        # PhaseRegistry.unregister(plugin_name) helper — out of scope here
        # but worth a TODO).
        raise
    self._loaded[plugin.name] = plugin
    return plugin
```

### WR-03: `PluginManager.discover()` swallows every error with bare `except Exception: pass`

**File:** `clawteam/plugins/manager.py:38-39, 52-53, 70-71, 122-123`
**Issue:** Four `try ... except Exception: pass` blocks. If `plugin.json` is malformed JSON, an entry point raises during iteration, or `load_config()` fails with a parse error, the plugin simply vanishes from `discover()` output with no signal to operators. This is a non-trivial debugging hole for a discovery surface. `load_from_entry_point` has the same pattern (line 122).

**Fix:** At minimum, log the exception to stderr so the operator can see *why* a plugin is missing:
```python
try:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    ...
except Exception as exc:
    print(f"[clawteam] Skipping plugin manifest {manifest}: {exc}", file=sys.stderr)
```
Apply the same treatment to the three other handlers. Consider collecting errors into a returned `discover_errors: list[str]` for CLI surfacing.

### WR-04: `SprintState.load()` fails non-gracefully when state.json is missing

**File:** `clawteam/sprint/state.py:83-95`
**Issue:** `load()` validates `team`/`sprint_id` through `_state_path`, acquires the file lock via `file_locked(path)`, then calls `path.read_text()`. If the sprint has never been saved, `read_text` raises `FileNotFoundError` — but the caller may expect `None` or a well-typed exception (the orchestrator's `load` path returns `None` on missing state). This inconsistency becomes relevant in Phase 2 when `find_latest`-style helpers are added for sprints.

**Fix:** Either add an explicit check and a typed exception, or wrap in a documented sentinel:
```python
@classmethod
def load(cls, team: str, sprint_id: str) -> SprintState:
    path = cls._state_path(team, sprint_id)
    if not path.is_file():
        raise FileNotFoundError(
            f"No sprint state at {path} (team={team!r}, sprint_id={sprint_id!r})"
        )
    with file_locked(path):
        raw = path.read_text(encoding="utf-8")
    return cls.model_validate(json.loads(raw))
```
Add a test: `with pytest.raises(FileNotFoundError): SprintState.load("t", "nonexistent")`.

## Info

### IN-01: Orchestrator silently narrows plugin multi-role lists to their first element

**File:** `clawteam/harness/orchestrator.py:77-83`
**Issue:** When a plugin contributes `contribute_phase_roles() = {"plan": ["pm", "ceo"]}`, the orchestrator assigns `self.state.phase_roles["plan"] = "pm"` — the `"ceo"` role is silently dropped. The inline comment ("Phase 1 conservative choice") acknowledges this as intentional, but there is no warning emitted and no test asserting the truncation behavior for multi-role lists. A plugin author writing `["pm", "ceo"]` today will likely expect both roles to participate and be surprised when only `pm` runs.

**Fix:** At minimum, emit a one-line stderr notice the first time truncation occurs, or add an assertion-style test so the behavior is pinned until Phase 3/4 lifts the restriction. Consider also raising a `warnings.warn` so callers can opt into strict mode.

### IN-02: `InteractionGate._resolve_sprint_dir` has a dead branch for `PhaseState`

**File:** `clawteam/harness/interaction_gate.py:141-144`
**Issue:**
```python
if isinstance(state, PhaseState):
    return None
return None
```
The explicit `PhaseState` branch and the fallthrough both return `None`. The branch is load-bearing only as documentation; it can be collapsed or commented as a deliberate no-op.

**Fix:** Either delete lines 142–143 or rewrite as a bare `return None` with a single comment:
```python
# PhaseState or any other state (non-sprint caller): no sprint context.
return None
```

### IN-03: `Question.to_markdown` body-normalization is correct but hard to read

**File:** `clawteam/sprint/qa.py:81-86` (and the mirrored block in `Answer.to_markdown` at 116-121)
**Issue:** The four-conditional body-normalization mixes boolean short-circuit with string mutation. Tracing verifies no bug (empty body → `"---\n"` suffix; non-empty body gets leading/trailing `\n` as needed), but the logic demands a pen-and-paper walk to confirm. Duplicated across two methods.

**Fix:** Extract a helper:
```python
def _render_body(body: str) -> str:
    """Return body guaranteed to start with one \\n and end with one \\n; '' for empty."""
    if not body:
        return "\n"
    if not body.startswith("\n"):
        body = "\n" + body
    if not body.endswith("\n"):
        body += "\n"
    return body
```
And call `return "\n".join(lines) + _render_body(self.body)` from both methods.

### IN-04: `_parse_frontmatter` list-terminator handles blank-line-before-dash ambiguously

**File:** `clawteam/sprint/qa.py:180`
**Issue:** Inside the choices block, `if sub.strip() == "" and (i + 1 < len(lines)) and not lines[i + 1].startswith("  "):` treats a blank line as an "end of list" *only when the next line is not indented*. If a user inserts a stray blank line between two `  - id:` entries, the parser silently ends the list at the blank line and returns fewer choices than written. The fixtures don't exercise this (they have no blank lines inside `choices:`), so this is latent.

**Fix:** Either explicitly reject blank lines inside a list block with `ValueError("blank line inside choices: not supported")` to match the schema's strictness, or skip blank lines consistently. The former matches the parser's "reject anything off-spec" philosophy.

### IN-05: `HarnessOrchestrator.abort()` does not advance state to a terminal marker

**File:** `clawteam/harness/orchestrator.py:143-149`
**Issue:** `abort()` appends a `{"phase": ..., "aborted_at": ...}` entry to `phase_history` and saves, but `state.current_phase` is unchanged. A subsequent `status()` will still report the phase as active; `can_advance()` will still run gate checks. Callers using `status()` as a liveness probe won't see an aborted-run signal.

**Fix:** Add an explicit marker, e.g.:
```python
def abort(self) -> None:
    self.state.phase_history.append({
        "phase": self.state.current_phase,
        "aborted_at": _now_iso(),
    })
    self.state.current_phase = "aborted"  # or set a new self.state.aborted = True field
    self.runner.save(self._harness_dir())
```
If adding a field, mirror it into `status()` output.

### IN-06: `HarnessOrchestrator.__init__` overwrites `current_phase` without refreshing `updated_at`

**File:** `clawteam/harness/orchestrator.py:65-71`
**Issue:** When the orchestrator resolves its phase list from the registry and sets `self.state.current_phase = self.state.phases[0]`, the `updated_at` timestamp (set via `default_factory` during `PhaseState(...)` construction) is not re-stamped, but conceptually the state just changed. This is cosmetic — the state was just constructed microseconds earlier — but it makes timestamp-based diffing on persisted state.json files slightly less precise.

**Fix:** Call `self.state.updated_at = _now_iso()` after the phase reassignment (and import `_now_iso` from `clawteam.harness.phases` rather than redefining at the bottom of the file). Alternatively, move the initial `updated_at` stamping into `start()` instead of `__init__`.

---

_Reviewed: 2026-04-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
