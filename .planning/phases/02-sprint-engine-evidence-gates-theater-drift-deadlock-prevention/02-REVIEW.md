---
phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
reviewed: 2026-04-17T00:00:00Z
depth: standard
files_reviewed: 39
files_reviewed_list:
  - clawteam/cli/commands.py
  - clawteam/events/types.py
  - clawteam/harness/artifacts.py
  - clawteam/harness/contracts.py
  - clawteam/harness/errors.py
  - clawteam/harness/evidence_gate.py
  - clawteam/harness/evidence_schemas.py
  - clawteam/harness/forced_progress_gate.py
  - clawteam/harness/freeze_registry.py
  - clawteam/harness/theater_detector.py
  - clawteam/mcp/helpers.py
  - clawteam/mcp/server.py
  - clawteam/plugins/base.py
  - clawteam/plugins/manager.py
  - clawteam/sprint/__init__.py
  - clawteam/sprint/conductor.py
  - clawteam/sprint/state.py
  - clawteam/team/envelope.py
  - clawteam/team/models.py
  - clawteam/team/routing_policy.py
  - clawteam/transport/base.py
  - clawteam/transport/file.py
  - clawteam/workspace/manager.py
  - pyproject.toml
  - tests/test_artifact_caps.py
  - tests/test_before_events.py
  - tests/test_cycle_detector.py
  - tests/test_event_types_phase2.py
  - tests/test_evidence_schemas.py
  - tests/test_forced_progress_gate.py
  - tests/test_freeze_registry.py
  - tests/test_phase2_integration.py
  - tests/test_plugin_hooks.py
  - tests/test_safety_rails.py
  - tests/test_sprint_cli.py
  - tests/test_sprint_conductor.py
  - tests/test_transport_envelope.py
  - tests/test_turn_envelope.py
findings:
  critical: 1
  warning: 7
  info: 6
  total: 14
status: issues_found
---

# Phase 2: Code Review Report

**Reviewed:** 2026-04-17T00:00:00Z
**Depth:** standard
**Files Reviewed:** 39
**Status:** issues_found

## Summary

Phase 2 delivers a substantial sprint engine (SprintConductor, EvidenceGate 4-check, theater/drift/deadlock primitives, FreezeRegistry, envelope validation, cycle detector, `clawteam sprint` + `clawteam guard` CLI sub-apps) with strong TDD discipline — every `feat(02-XX)` commit has a matching RED `test(02-XX): add failing tests` commit landing first. Pydantic v2 usage is correct (`model_validate`, `model_dump_json`, `Field(default_factory=…)`, `Literal[…]` for the closed `status` state machine). The append-only `freeze_audit.jsonl` pattern correctly uses `open(..., "a")` (mirrors exit_journal), and the `freeze.json` path uses `file_locked + atomic_write_text`. Pitfall #5 data-dir exemption is enforced consistently. T-02-01 SSRF and T-02-18 stderr-leak are explicitly documented as accepted residuals (Phase 5 mitigation).

However, one Critical bug surfaces a real functional break (EvidenceGate passes a git branch name as `cwd` to subprocess), and several Warnings concern:

1. Module-level `_registry` singleton in `freeze_registry.py` silently ignores the `(team, sprint_id)` args after first call — a subsequent `get_freeze_registry("other-team", "x")` returns the prior team's registry, risking cross-sprint/team veto confusion.
2. `_seen_turn_ids` dedupe set in `forced_progress_gate.py` has no lock even though it's a shared module-level dict mutated from two separate hook sites (Transport.deliver + ArtifactStore.write) — contrast with `_COUNTER_LOCK` that protects `_MALFORMED_COUNTERS` in transport/base.py.
3. `SprintState.load/save` serialize pydantic with `model_dump_json()` whose default does NOT honor the `by_alias`/`exclude_none` conventions used elsewhere in the codebase — inconsistent with `TeamMessage` pattern and may drift when new aliased fields land.
4. `EvidenceGate._load_test_verify_cache` does not handle `json.JSONDecodeError`; a corrupted cache crashes the gate.

TDD discipline, pydantic correctness, and the append-only audit invariant are all good. The remaining items are hardening tasks that can be tracked into Phase 3.

## Critical Issues

### CR-01: EvidenceGate passes `workspace_branch` (a branch NAME) as subprocess `cwd`

**File:** `clawteam/harness/evidence_gate.py:248-253`
**Issue:** `_run_test_command` invokes the subprocess runner with `cwd=state.workspace_branch or "."`. But `SprintState.workspace_branch: str = ""` is a git **branch name** (e.g. `"main"`, `"clawteam/t/agent"`) — not a filesystem path. When `workspace_branch` is populated with a real branch name, the subprocess call will raise `FileNotFoundError: [Errno 2] No such file or directory: 'main'` and the test-command check fails with an error unrelated to the test result. When `workspace_branch == ""`, it falls back to `"."` (current working directory) which may not be the expected project root either.

This breaks the `test-report` post-check path end-to-end in any sprint that has set `workspace_branch`.

**Fix:** Use the sprint's actual working directory. Either introduce a `SprintState.workspace_path` field, or resolve the worktree path via `WorkspaceManager` / `get_data_dir()`. Short term:

```python
# clawteam/harness/evidence_gate.py
# Replace:
completed = self._subprocess_run(
    cmd_parts,
    cwd=state.workspace_branch or ".",
    timeout=TEST_COMMAND_TIMEOUT_SECONDS,
)
# With (example — needs a concrete path source decision):
cwd = getattr(state, "workspace_path", "") or str(Path.cwd())
completed = self._subprocess_run(
    cmd_parts,
    cwd=cwd,
    timeout=TEST_COMMAND_TIMEOUT_SECONDS,
)
```

And add a `workspace_path: str = ""` field to `SprintState` (or document the branch-name-is-cwd contract and add a test that fails when `workspace_branch` is a real branch name — the current tests never populate it, which is how this slipped through).

---

## Warnings

### WR-01: `get_freeze_registry()` singleton ignores requested `(team, sprint_id)` after first construction

**File:** `clawteam/harness/freeze_registry.py:204-219`
**Issue:** The module-level `_registry: FreezeRegistry | None = None` is only set on the first successful call. On subsequent calls with a DIFFERENT `(team, sprint_id)` the cached registry is returned silently:

```python
def get_freeze_registry(team=None, sprint_id=None):
    global _registry
    if _registry is None and team and sprint_id:
        _registry = FreezeRegistry(team, sprint_id)
    return _registry  # returns the OLD registry when team/sprint_id differ
```

In a long-running orchestrator that coordinates multiple sprints (the target for Phase 7 per §02-CONTEXT D-22), the second sprint's freeze/unfreeze subscribers consult the first sprint's registry. The freeze-registry's singleton shape is "per (team, sprint_id)" per the class docstring, but the accessor does not enforce it. Subscribers `_on_before_file_write` / `_on_before_tool_call` pass `None` through — but the cached wrong-sprint registry produces **wrong answers**, not pass-through.

**Fix:** Either (a) key the singleton on `(team, sprint_id)` so the accessor rebuilds on mismatch; (b) force callers to pass team+sprint on every access; or (c) at minimum, raise when args don't match the cached registry:

```python
_registry: FreezeRegistry | None = None
_registry_key: tuple[str, str] | None = None

def get_freeze_registry(team=None, sprint_id=None):
    global _registry, _registry_key
    requested = (team, sprint_id) if team and sprint_id else None
    if requested and _registry_key != requested:
        _registry = FreezeRegistry(team, sprint_id)
        _registry_key = requested
    return _registry
```

Document that concurrent multi-sprint use requires explicit `reset_freeze_registry()` between switches.

### WR-02: `_seen_turn_ids` dedupe map mutated without a lock

**File:** `clawteam/harness/forced_progress_gate.py:56-75`
**Issue:** `_seen_turn_ids: dict[str, set[str]] = defaultdict(set)` is mutated from TWO hook sites (Transport.deliver via `_pre_deliver_hooks` and ArtifactStore.write via `turn_counter_callback`) that can run on different threads, yet `increment_turn_counter` reads-then-writes without a lock:

```python
if turn_id and turn_id in _seen_turn_ids[agent]:
    return
if turn_id:
    _seen_turn_ids[agent].add(turn_id)
current = state.turn_counters.get(agent, 0)
state.turn_counters[agent] = current + 1
```

Two threads with the same `(agent, turn_id)` can both observe "not present" then both `.add()` then both increment — defeating the Pitfall #2 dedupe invariant. Contrast `clawteam/transport/base.py` which DOES guard the analogous module state with `_COUNTER_LOCK`.

**Fix:** Introduce a module-level `Lock` and wrap both reads and mutations:

```python
from threading import Lock
_seen_turn_ids_lock = Lock()

def increment_turn_counter(state, agent, turn_id=""):
    if not agent:
        return
    with _seen_turn_ids_lock:
        if turn_id and turn_id in _seen_turn_ids[agent]:
            return
        if turn_id:
            _seen_turn_ids[agent].add(turn_id)
        state.turn_counters[agent] = state.turn_counters.get(agent, 0) + 1
```

Note `state.turn_counters` is ALSO a shared dict; the lock should scope the counter write too.

### WR-03: `EvidenceGate._load_test_verify_cache` crashes on corrupt cache file

**File:** `clawteam/harness/evidence_gate.py:286-291`
**Issue:** If `test_verify_cache.json` is truncated or has invalid JSON (e.g. partial write from a process killed mid-flush, or manual edit), `json.loads(...)` raises `json.JSONDecodeError` which propagates to the gate caller and crashes `advance_phase`. Other similar paths in the codebase (e.g. `list_sprints` in `sprint/conductor.py:381`, `_load_registry` in `workspace/manager.py:34`) defensively catch and recover; this one does not.

**Fix:**

```python
def _load_test_verify_cache(self, state) -> dict:
    p = self._cache_path(state)
    if not p.exists():
        return {}
    try:
        with file_locked(p):
            return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Corrupt or unreadable cache — treat as empty; next save recreates.
        return {}
```

### WR-04: `SprintState.save` uses `model_dump_json(indent=2)` without `by_alias` / `exclude_none`

**File:** `clawteam/sprint/state.py:124-135`
**Issue:** Elsewhere in this codebase the persistence convention is `model_dump_json(by_alias=True)` or `to_payload(..., exclude_none=True)` (see `clawteam/team/models.py::TeamMessage` docstring "Uses exclude_none=True when serializing so only relevant fields appear"). `SprintState.save` serializes with bare `model_dump_json(indent=2)` which (a) does not emit field aliases (none are declared today on SprintState, but new aliased fields would silently persist under Python names), and (b) persists None/default values verbosely.

This isn't a bug today but it's inconsistent with the project convention documented by the `TeamMessage` model. A future field declared with `alias=...` would break round-trip on existing state.json files.

**Fix:** Pick the same convention used for TeamMessage persistence and apply consistently:

```python
atomic_write_text(
    path,
    self.model_dump_json(indent=2, by_alias=True, exclude_none=False),
)
```

(Keep `exclude_none=False` for SprintState because the closed-value fields like `current_phase` and `status` need to persist even with empty/default values.)

### WR-05: `DefaultRoutingPolicy.read_state` silently returns empty dict on JSON decode error, losing state

**File:** `clawteam/team/routing_policy.py:344-358`
**Issue:** When `runtime_state.json` exists but contains invalid JSON (partial write recovery, manual edit, disk corruption), `read_state` silently swallows the error and returns an empty state dict. The subsequent `_save_state(state)` then OVERWRITES the corrupt-but-possibly-salvageable file with the empty state — data loss. All per-route history (`lastInjectedAt`, `suppressedTopics`, `recentEvents`) is permanently erased.

```python
if path.exists():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {}  # <- silent overwrite on next save
```

**Fix:** Either rename the corrupt file to a `.corrupt` sidecar for operator recovery, or emit a structured event before falling back to empty state:

```python
except (json.JSONDecodeError, OSError) as exc:
    # Move corrupt file aside so next _save_state doesn't overwrite salvageable data.
    try:
        path.rename(path.with_suffix(f".corrupt.{int(time.time())}"))
    except OSError:
        pass
    data = {}
```

### WR-06: `_tool` wrapper in MCP server emits `BeforeToolCall` but does NOT deep-inspect args

**File:** `clawteam/mcp/server.py:17-48` and `clawteam/harness/freeze_registry.py:302-322`
**Issue:** `_on_before_tool_call` does a shallow scan of `event.args.values()`, matching only top-level string values that start with `/`. Nested args (e.g. `args={"file": {"path": "/frozen"}}` or `args={"paths": ["/frozen/a", "/frozen/b"]}`) bypass the veto. The docstring correctly acknowledges "out of scope (T-02-09)", but this creates a real path-based bypass for any MCP tool whose schema uses nested structures. Defense-in-depth at the `BeforeFileWrite` layer catches direct writes — but tool-call-based destructive ops that translate paths internally (e.g. a `copy_files({src: '/frozen/a', dst: ...})` tool) will still pass the `BeforeToolCall` veto.

The workspace-manager and ArtifactStore layers still protect file writes via `BeforeFileWrite`, so this is not a critical miss, but it is worth an explicit defense-in-depth audit for any MCP tool added in Phase 3+ that takes path-like args in nested structures.

**Fix:** Either document the shallow-scan contract prominently at the CLI/MCP docs surface, or generalize the scan to recurse one level:

```python
def _on_before_tool_call(event):
    reg = get_freeze_registry()
    if reg is None:
        return
    def _walk(v):
        if isinstance(v, str) and v.startswith("/"):
            yield v
        elif isinstance(v, dict):
            for sv in v.values():
                yield from _walk(sv)
        elif isinstance(v, (list, tuple)):
            for sv in v:
                yield from _walk(sv)
    for path_str in _walk(event.args or {}):
        frozen, reason = reg.is_frozen(path_str)
        if frozen:
            event.veto = True
            event.veto_reason = f"tool {event.tool_name}: {reason or f'{path_str} path frozen'}"
            return
```

### WR-07: `ArtifactStore.write` turn-counter callback fires with empty `turn_id` on every metadata write

**File:** `clawteam/harness/artifacts.py:175-184`
**Issue:** The callback is invoked whenever `metadata` is provided and contains a non-empty `agent`. `turn_id_attr` falls back to `""` when `metadata["turn_id"]` is absent. Per `increment_turn_counter` semantics, `turn_id=""` is treated as "no dedupe available and always increment" — so every non-sprint artifact write (hedge-fund, software-dev, etc., which do NOT set `metadata["turn_id"]`) that has `metadata["agent"]` will increment a counter against that agent.

The `SprintConductor` is the only site that wires this callback and it targets gstack sprints — so BC for non-sprint templates is preserved today because non-sprint ArtifactStores are constructed WITHOUT `turn_counter_callback`. But the design invariant "same turn_id reaching both ArtifactStore and Transport counts once" becomes fragile if anyone adds `metadata={"agent": ...}` to a gstack template without `turn_id`. Pitfall #2 explicitly calls the `(agent, turn_id)` pair the dedupe anchor.

**Fix:** Require `metadata["turn_id"]` when `agent` is present in gstack sprints, or teach the callback to skip when `turn_id == ""`:

```python
if self._turn_counter_callback is not None and metadata:
    agent_attr = str(metadata.get("agent", ""))
    turn_id_attr = str(metadata.get("turn_id", ""))
    if agent_attr and turn_id_attr:  # require BOTH for idempotency
        try:
            self._turn_counter_callback(agent_attr, turn_id_attr)
        except Exception:
            pass
```

Alternatively, document the "always-increment" semantics as intentional for agent-authored writes without envelope turn_ids.

---

## Info

### IN-01: T-02-01 SSRF residual — `deploy_url` HEAD probe hits arbitrary URLs

**File:** `clawteam/harness/evidence_gate.py:69-82, 301-311`
**Issue:** `_default_head_check` uses `urllib.request.urlopen` directly against the URL from artifact frontmatter. An adversarial agent setting `deploy_url: http://169.254.169.254/latest/meta-data/` (AWS IMDS) or `http://localhost:6379/` (Redis) will probe private-network services during `ship-notes` evaluation. This is explicitly documented as accepted residual (T-02-01) to be mitigated by an allowlist-checker in Phase 5.

**Fix (Phase 5 scope):** Wrap `_default_head_check` with an allowlist check:

```python
ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_HOSTS = {...}  # configured per-sprint

def _allowlisted_head_check(url, timeout):
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.scheme not in ALLOWED_SCHEMES or p.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"deploy_url host not allowlisted: {p.hostname}")
    if p.hostname and _is_private_ip(p.hostname):
        raise ValueError(f"deploy_url resolves to private IP: {p.hostname}")
    return _default_head_check(url, timeout)
```

### IN-02: T-02-18 residual — stderr tail may leak secrets in test-command error message

**File:** `clawteam/harness/evidence_gate.py:266-270`
**Issue:** On non-zero exit, the last line of stderr is embedded in the gate reason string which surfaces through the MCP error envelope. If the failing test prints secrets to stderr (e.g. "connection refused to postgres://user:pass@host/db"), the reason string contains credentials. Documented and accepted for v1.

**Fix (future):** Redact known-secret patterns before embedding, or truncate to a fixed byte budget and mask anything matching `/[A-Za-z0-9]{20,}/`.

### IN-03: `subprocess_runner` boundary uses `str.split()` rather than `shlex.split`

**File:** `clawteam/harness/evidence_gate.py:247`
**Issue:** `cmd_parts = cmd_str.split()` works for simple commands but fails for commands with quoted arguments containing spaces (e.g. `pytest -k "test foo bar"`). The docstring explicitly argues this is STRICTER than `shlex.split` — which is true from a security standpoint (no shell-quote injection) — but artifact authors may legitimately need quoted args. Document this constraint clearly in the `ship-notes` / `test-report` artifact schemas or the agent prompts.

**Fix:** No code change required; document in Phase 3 `GstackSprintPlugin`'s test-report artifact schema description.

### IN-04: `WorkspaceManager._team_name` is instance-scoped mutable state set by each write path

**File:** `clawteam/workspace/manager.py:60, 116, 235, 258, 317`
**Issue:** `self._team_name` is set at the top of each write-path method (create/checkpoint/cleanup/merge) and read inside `_emit_before_file_write`. If a single `WorkspaceManager` instance is reused concurrently across teams (the spawner/harness layer may do this in a long-running process), the team_name read could be for a DIFFERENT team than the caller passed. Today each call sets the value first, so this is race-prone but not persistent-incorrect. Low risk because callers typically construct a fresh manager per call.

**Fix:** Thread the team_name through `_emit_before_file_write(team_name, agent_name, path, ...)` instead of stashing on `self`:

```python
def _emit_before_file_write(self, team_name: str, agent_name: str, ...):
    ...
    event = BeforeFileWrite(team_name=team_name, ...)
```

### IN-05: `freeze.json` load swallows all exceptions, masking corruption

**File:** `clawteam/harness/freeze_registry.py:97-104`
**Issue:** `_load` is wrapped implicitly — if `freeze.json` is malformed JSON, `json.loads` raises and the `FreezeRegistry` constructor crashes with a bare exception. Compared with WR-05 this is less bad (fails loudly instead of silently erasing), but it means a single corrupt `freeze.json` prevents sprint resume. Worth adding a clear error shape and fallback-to-empty path:

```python
def _load(self):
    p = self._freeze_path()
    if not p.exists():
        return
    try:
        with file_locked(p):
            data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"freeze.json at {p} is malformed JSON: {exc}. "
            f"Inspect and delete to recover (erases all active freezes)."
        ) from exc
    self._frozen_paths = {k: set(v) for k, v in data.get("paths", {}).items()}
    self._frozen_globs = set(data.get("globs", []))
```

### IN-06: `--artifact-cap 500` (KB) behaves differently than `artifact_cap_bytes=500` (bytes) due to < 1024 KB/bytes disambiguation

**File:** `clawteam/sprint/conductor.py:141-160`
**Issue:** `_resolve_cap` has a subtle contract: "cli_override < 1024 → treat as KB; >= 1024 → treat as bytes". Plan docstring documents this but the kwarg name is literally `artifact_cap_bytes`. A caller who passes `artifact_cap_bytes=100` (intending 100 bytes) gets `100 * 1024 = 102400` bytes. A caller who passes `artifact_cap_bytes=2000` gets 2000 bytes. This is a footgun for both test authors and direct library consumers.

**Fix:** Either (a) accept a distinct `artifact_cap_kb` kwarg that's multiplied; (b) require explicit bytes always and handle KB conversion at the CLI layer only; or (c) at minimum, rename the threshold constant + add a RuntimeWarning when the ambiguous path is hit:

```python
if cli_override is not None:
    if cli_override < 1024:
        import warnings
        warnings.warn(
            f"artifact_cap_bytes={cli_override} < 1024 is interpreted as KB "
            f"({cli_override * 1024} bytes). Pass >= 1024 for literal bytes.",
            stacklevel=2,
        )
        return cli_override * 1024
    return cli_override
```

---

_Reviewed: 2026-04-17T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
