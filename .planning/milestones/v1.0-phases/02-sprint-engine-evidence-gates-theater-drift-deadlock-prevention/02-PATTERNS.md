# Phase 2: Sprint Engine, Evidence Gates & Theater/Drift/Deadlock Prevention — Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** 26 (15 new + 11 modified)
**Analogs found:** 26 / 26 (every target has ≥ role-match analog in this branch)

---

## File Classification

### New files

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `clawteam/sprint/state.py` *(Phase 1, extended here)* | model | durable-state | `clawteam/harness/phases.py::PhaseState` | exact (pydantic v2 BaseModel over JSON on disk) |
| `clawteam/sprint/conductor.py` | conductor | request-response + event-driven | `clawteam/harness/orchestrator.py::HarnessOrchestrator` + `phases.py::PhaseRunner` | role-match (new abstraction; composes with existing) |
| `clawteam/harness/evidence_gate.py` | gate (subclass) | presence+content validation | `clawteam/harness/phases.py::ArtifactRequiredGate` (§64) | exact (explicit subclass per D-01) |
| `clawteam/harness/evidence_schemas.py` | registry + contribute hook | in-memory registration | `clawteam/harness/phase_registry.py::PhaseRegistry` | exact (singleton+registration shape) |
| `clawteam/harness/forced_progress_gate.py` | gate (subclass) | counter-driven + Q/A | `clawteam/harness/phases.py::PhaseGate` (§56) + Phase 1 `InteractionGate` | role-match (new gate using turn_counters) |
| `clawteam/harness/freeze_registry.py` | registry singleton | file-locked JSON + audit JSONL | `clawteam/harness/phase_registry.py` + `clawteam/harness/exit_journal.py` | exact (structural twin of PhaseRegistry per CONTEXT lesson #3) |
| `clawteam/team/envelope.py` | validator + parser | request-response | `clawteam/team/models.py::TeamMessage` + `clawteam/harness/contracts.py::SuccessCriterion` | role-match (new pydantic v2 model + stdlib YAML parse) |
| `tests/test_sprint_conductor.py` | test | unit + integration | `tests/test_harness.py` | exact |
| `tests/test_evidence_gate.py` | test | unit + integration | `tests/test_harness.py::test_artifact_required_gate` (if present) or nearest gate test | role-match |
| `tests/test_turn_envelope.py` | test | unit | `tests/test_team_models.py` | role-match |
| `tests/test_forced_progress_gate.py` | test | unit | `tests/test_harness.py` | role-match |
| `tests/test_cycle_detector.py` | test | unit + integration | `tests/test_runtime_routing.py` | exact (same `DefaultRoutingPolicy` substrate) |
| `tests/test_freeze_registry.py` | test | unit + integration | `tests/test_event_bus.py::test_veto_pattern` + JSONL tests | role-match |
| `tests/test_safety_rails.py` | test | unit | `tests/test_event_bus.py` | role-match |
| `tests/test_artifact_caps.py` | test | unit + integration | `tests/test_harness.py` | role-match |
| `tests/test_sprint_cli.py` | test | CLI surface | existing CLI tests using `typer.testing.CliRunner` | role-match |

### Modified files

| Modified File | Role | Data Flow | Change Class | Existing Shape To Preserve |
|---------------|------|-----------|--------------|----------------------------|
| `clawteam/team/models.py::TeamMessage` (§90-122) | model | request-response | add 3 required fields (D-06) | pydantic v2 `populate_by_name=True` + `Field(alias=...)` |
| `clawteam/harness/artifacts.py::ArtifactStore.write` (§22-31) | storage | file-I/O | pre-write hook chain (D-07, D-08, D-10, D-27) | `meta.json` sidecar pattern |
| `clawteam/harness/contracts.py::SuccessCriterion` (§19) | model | — | populate `verified`/`verified_at`/`verified_by` from `EvidenceGate` | untouched pydantic shape |
| `clawteam/events/types.py` (§1-195) | event dataclasses | — | add 8 new dataclasses inheriting `HarnessEvent` | `@dataclass` + `HarnessEvent` base + `veto: bool = False` on Before* |
| `clawteam/team/routing_policy.py::DefaultRoutingPolicy` (§93-408) | router | request-response | extend `decide()` with cycle detect (D-18..D-21); add `topicHash` to `_append_event` entries | `routes[route_key]` dict-of-dicts state + `recentEvents` rolling window (50) |
| `clawteam/transport/base.py::Transport.deliver` (§12) | transport | request-response | pre-deliver hook chain (D-08, D-14) | ABC contract unchanged |
| `clawteam/workspace/manager.py` | fs manager | file-I/O | emit `BeforeFileWrite` before git write paths (D-10) | existing `ensure_within_root` pattern |
| `clawteam/mcp/server.py::_tool` (§16-25) | MCP wrapper | request-response | emit `BeforeToolCall` inside `_tool` wrapper (D-10) | existing `translate_error` wrapping |
| `clawteam/mcp/helpers.py::translate_error` (§25-32) | error translator | — | add branches for `FrozenPathError`, `MalformedEnvelopeError`, `ArtifactTooLargeError`, `AmbiguousSprintError`, `SprintNotFoundError` (D-12) | all custom errors subclass `ValueError` so auto-wrap already works — add explicit branches only for clarity/message |
| `clawteam/plugins/base.py::HarnessPlugin` | plugin ABC | — | add `contribute_evidence_schemas() -> dict[str, type[ArtifactFrontmatterBase]]` with `return {}` default | three Phase 1 hook precedents at §46-75 |
| `clawteam/cli/commands.py` | CLI entry | CLI surface | add `sprint_app = typer.Typer()` sub-app + 6 subcommands (D-24..D-26) | 10+ existing sub-apps using `add_typer` pattern (§212, 297, 300, 1235, 1783, 1985, 2109, 2338, 2629, 2728) |

---

## Pattern Assignments

### 1. `clawteam/sprint/state.py` — extensions (model; durable-state)

**Analog:** `clawteam/harness/phases.py::PhaseState` (§39-53)

**Pydantic v2 state-model with JSON persistence** (`phases.py:39-53`):
```python
class PhaseState(BaseModel):
    """Persisted state of a harness run."""
    harness_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    team_name: str = ""
    current_phase: str = DISCUSS
    phases: list[str] = Field(default_factory=lambda: list(DEFAULT_PHASES))
    phase_roles: dict[str, str] = Field(default_factory=lambda: dict(DEFAULT_PHASE_ROLES))
    phase_history: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    # ...
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)
```

**How Phase 2 extends:** Add three additive fields with defaults so Phase 1 JSON files rehydrate cleanly (pitfall #8 safety — never remove fields, always default-with-sensible-value):
- `turn_counters: dict[str, int] = Field(default_factory=dict)` (D-14)
- `artifact_cap_bytes: int = 50 * 1024` (D-27/D-29)
- `phase_artifact_cap_bytes: int = 500 * 1024` (D-28/D-29)
- `status: Literal["running","paused","completed"] = "running"` (Pitfall #6 pause idempotency)
- `suppressed_topics: dict[str, list[str]] = Field(default_factory=dict)` *(already in `runtime_state.json`, but mirror onto state for visibility)*

**ID convention (reuse unchanged):** `uuid.uuid4().hex[:8]` (Phase 1 D-05; matches `SprintContract.id` at `contracts.py:28`, `TaskItem.id` at `models.py:129`).

---

### 2. `clawteam/sprint/conductor.py` — `SprintConductor` (new, composes with existing)

**Analog:** `clawteam/harness/phases.py::PhaseRunner` (§106-192) for per-phase advance; `clawteam/harness/orchestrator.py::HarnessOrchestrator` for the sprint-run loop (older model; Phase 2 conductor sits ABOVE it per CONTEXT "Integration Points").

**Gate evaluation loop to copy** (`phases.py:117-124`):
```python
def can_advance(self) -> tuple[bool, str]:
    gates = self._gates.get(self.state.current_phase, [])
    for gate in gates:
        ok, reason = gate.check(self.state)
        if not ok:
            return False, reason
    return True, ""
```
**Adapt for:** Conductor's advance loop runs `EvidenceGate` → `forced_progress_gate` → `InteractionGate` in order (composition order locked by CONTEXT "Integration Points" — `PhaseRunner._gates[phase]` grows by up to 3 entries per gstack phase).

**Phase transition + event emit idiom** (`phases.py:147-158`):
```python
try:
    from clawteam.events.global_bus import get_event_bus
    from clawteam.events.types import PhaseTransition
    get_event_bus().emit(PhaseTransition(
        team_name=self.state.team_name,
        from_phase=old_phase,
        to_phase=new_phase,
        artifacts=list(self.state.artifacts.keys()),
    ))
except Exception:
    pass
```
**Adapt for:** Conductor emits `PhaseTransition` (reuse existing event) after every gate-passing advance; never crashes on event-emit failure.

**Save/load persistence idiom** (`phases.py:177-192`):
```python
def save(self, base_dir: Path) -> Path:
    harness_dir = base_dir / self.state.team_name / self.state.harness_id
    harness_dir.mkdir(parents=True, exist_ok=True)
    state_path = harness_dir / "state.json"
    state_path.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")
    return state_path

@classmethod
def load(cls, state_path: Path) -> PhaseRunner:
    data = json.loads(state_path.read_text(encoding="utf-8"))
    state = PhaseState.model_validate(data)
    return cls(state)
```
**Adapt for:** `SprintConductor.pause()` = call `SprintState.save()` (uses `file_locked()` + `atomic_write_text` per Phase 1 D-05); `.resume()` = classmethod `load_by_prefix()`. Do NOT use raw `write_text` as above — per-Phase-1 convention use `atomic_write_text` (Pitfall #6 in research). Per D-25, accept sprint prefix; raise `AmbiguousSprintError` on collision.

**Concurrency pick:** Use `threading.RLock` (consistent with `EventBus._lock` at `bus.py:51`; research §Alternatives Considered confirms). `force_interactive_phases: list[str] = field(default_factory=list)` set at construction, never mutated (Anti-pattern in research).

---

### 3. `clawteam/harness/evidence_gate.py` — `EvidenceGate` (new; subclass)

**Analog:** `clawteam/harness/phases.py::ArtifactRequiredGate` (§64-74) — subclass per D-01.

**Exact base-class shape to extend** (`phases.py:64-74`):
```python
class ArtifactRequiredGate(PhaseGate):
    """Requires specific artifacts to exist."""

    def __init__(self, artifact_names: list[str]):
        self.artifact_names = artifact_names

    def check(self, state: PhaseState) -> tuple[bool, str]:
        missing = [n for n in self.artifact_names if n not in state.artifacts]
        if missing:
            return False, f"Missing artifacts: {', '.join(missing)}"
        return True, ""
```

**Copy constructor exactly; override `check`** with the 4-check protocol documented in research §Pattern 3. The existing `check` result `(bool, str)` is the wire shape — retain.

**Pydantic ValidationError → structured reason** (copy research Example 1 idiom):
```python
try:
    schema_cls.model_validate(meta)
except ValidationError as exc:
    first = exc.errors()[0]
    field = ".".join(str(p) for p in first["loc"])
    return False, f"{artifact_name}: frontmatter invalid: {field}: {first['msg']}"
```

**Post-check dispatch** (for `test-report.md` test-run, `ship-notes.md` HEAD dereference) uses a `_post_check(artifact_name, state) -> tuple[bool, str]` helper. Test-command runs via `subprocess.run(cmd, cwd=state.workspace_branch_path, timeout=300, shell=False)` with SHA256 cache lookup against `test_verify_cache.json` using `file_locked()` + `atomic_write_text`.

**Deploy URL checker injection** (Pitfall #10 — test-safe):
```python
def __init__(self, artifact_names: list[str], *, deploy_url_checker=None):
    super().__init__(artifact_names)
    self._deploy_url_checker = deploy_url_checker or _default_head_check  # stdlib urllib.request
```

---

### 4. `clawteam/harness/evidence_schemas.py` — `EvidenceSchemaRegistry` (new)

**Analog:** `clawteam/harness/phase_registry.py::PhaseRegistry` (structural twin, per CONTEXT lesson #3).

**Module-level singleton + register/get accessor idiom** — mirror Phase 1 exactly. The file uses the same `reset_registry()` test helper pattern (`phase_registry.py` comments reference `reset_registry()`).

**Discriminator base class** (from research §Pattern 1, Example in §Pattern 1):
```python
# clawteam/harness/evidence_schemas.py
class ArtifactFrontmatterBase(BaseModel):
    persona: str
    step_label: str
    done: bool
    artifact_type: str
    created_at: str

_REGISTERED: dict[str, type[ArtifactFrontmatterBase]] = {}

def register_schema(name: str, cls: type[ArtifactFrontmatterBase]) -> None:
    if name in _REGISTERED:
        raise ValueError(f"Duplicate evidence-schema registration: {name}")
    _REGISTERED[name] = cls

def get_schema(artifact_type: str) -> type[ArtifactFrontmatterBase] | None:
    return _REGISTERED.get(artifact_type)

def reset_registry() -> None:
    """For test isolation — call in setUp + tearDown of every test that registers."""
    _REGISTERED.clear()
```

**Phase 2 ships registry + empty default; Phase 3 `GstackSprintPlugin.contribute_evidence_schemas()` populates the six subclasses.** Plugin hook called by `clawteam/plugins/manager.py` at plugin load time (same loop as `contribute_phases` — plan should verify against existing manager impl).

---

### 5. `clawteam/harness/forced_progress_gate.py` — `forced_progress_gate` (new; subclass)

**Analog:** `clawteam/harness/phases.py::PhaseGate` ABC (§56-61) + Phase 1 `InteractionGate` (not yet shipped, but see `01-03-PLAN.md:28-34` — globs `sprint/<id>/questions/*.md`).

**Base-class shape** (`phases.py:56-61`):
```python
class PhaseGate(ABC):
    """Gate that must pass before a phase can advance."""

    @abstractmethod
    def check(self, state: PhaseState) -> tuple[bool, str]:
        """Return (passed, reason)."""
```

**Question-writing path convention** (locked by Phase 1 D-05/D-08):
- `sprint_dir = get_data_dir() / "teams" / team / "sprints" / sprint_id` *(path fixed by Phase 1)*
- `sprint_dir / "questions" / "<q_id>.md"` — question file
- `sprint_dir / "answers" / "<q_id>.md"` — answer file (written by human)

**On trigger semantics** (D-17): gate.check returns False, gate writes a `multi-choice` question file `[A: keep waiting, B: restart agent, C: abort sprint]`. The Phase 1 Q/A schema (`01-04-PLAN.md` / Phase 1 D-08) fixes markdown format — reuse the same `Question.to_markdown()` helper.

**Turn-counter consultation** (D-14, D-15, D-16):
- Counter: `state.turn_counters: dict[str, int]` (incremented by envelope hooks at `deliver()` + `ArtifactStore.write()`).
- Progress signal: net-positive artifact-bytes delta *since last turn snapshot* OR `TaskCompleted` event fired during the turn.
- Threshold: **2 consecutive no-progress turns per-agent** (NOT sprint-wide).
- **Pitfall #5 mitigation:** skip counter increment when the agent is blocking on a pending question they authored (`state.pending_question_ids` per Phase 1 D-08).

**Counter-reset on answer:** when `InteractionGate` sees the answer arrive, it calls back into gate state; forced_progress_gate clears the affected agent's counter.

---

### 6. `clawteam/harness/freeze_registry.py` — `FreezeRegistry` (new; singleton)

**Analog:** `clawteam/harness/phase_registry.py` shape + `clawteam/harness/exit_journal.py` JSONL pattern.

**JSONL append-only audit idiom** (`exit_journal.py:27-43`):
```python
def record_exit(
    self,
    agent_name: str,
    exit_code: int | None = None,
    abandoned_tasks: list[str] | None = None,
) -> None:
    self._path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "agent_name": agent_name,
        "exit_code": exit_code,
        "abandoned_tasks": abandoned_tasks or [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    # Append atomically (one write call, newline-terminated)
    with open(self._path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
```
**Adapt for:** `freeze_audit.jsonl` writes an entry `{ts, action, path, agent, reason, actor, sprint_id}` on every freeze/unfreeze/guard invocation (D-13). Copy the `"a"` append mode verbatim; never use `atomic_write_text` for append-only JSONL.

**File-locked JSON state** (`fileutil.py:55-83`):
```python
with file_locked(p):
    data = json.loads(p.read_text(encoding="utf-8"))
# ...
with file_locked(p):
    atomic_write_text(p, json.dumps(payload, indent=2, ensure_ascii=False))
```
**Adapt for:** `freeze.json` load/save (full research Example 2 at §871-990 already uses this idiom correctly).

**Singleton accessor** (copy Phase 1 `phase_registry.py` `get_registry()/reset_registry()` pair):
```python
_registry: FreezeRegistry | None = None

def get_freeze_registry(team: str | None = None, sprint_id: str | None = None) -> FreezeRegistry | None:
    global _registry
    if _registry is None and team and sprint_id:
        _registry = FreezeRegistry(team, sprint_id)
    return _registry

def reset_freeze_registry() -> None:
    global _registry
    _registry = None
```

**Pitfall #5 mitigation (HARD-LOCK):** `is_frozen(path)` returns `False, ""` for any path under `get_data_dir()` — sprint-internal writes (state.json, freeze.json, answers/) must never be vetoed by freeze. See research §Example 2, lines 922-928.

**FrozenPathError subclass of ValueError** (matches `MCPToolError` at `mcp/helpers.py:17` — auto-wrapped by `translate_error` at §30).

---

### 7. `clawteam/team/envelope.py` — `TurnEnvelope` + `parse_frontmatter` (new)

**Analog:** `clawteam/team/models.py::TeamMessage` (§90-122) pydantic shape + `clawteam/harness/contracts.py::SuccessCriterion` for simpler field shape.

**Pydantic v2 model shape** (copy research Example 1 at §823-833 verbatim):
```python
class TurnEnvelope(BaseModel):
    persona: str = Field(..., min_length=1, description="Agent role asserting this turn")
    step_label: str = Field(..., min_length=1, description="Free-form step marker")
    done: bool = Field(..., description="Turn-done signal")
    artifact_type: str | None = None
    created_at: str | None = None
    turn_id: str | None = None  # uuid.uuid4().hex[:8] for dedupe (Pitfall #2)
```

**Parse-frontmatter helper** (stdlib path — CONTEXT "Don't Hand-Roll" confirms no `python-frontmatter` dep):
```python
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)

def parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return {}, raw
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as exc:
        raise MalformedEnvelopeError(f"frontmatter YAML invalid: {exc}") from exc
    if not isinstance(meta, dict):
        raise MalformedEnvelopeError(f"frontmatter must be a mapping, got {type(meta).__name__}")
    return meta, m.group(2)
```

**Validation helper with structured error** (mirror research Example 1 §860-867):
```python
def validate_envelope(meta: dict) -> TurnEnvelope:
    try:
        return TurnEnvelope.model_validate(meta)
    except ValidationError as exc:
        first = exc.errors()[0]
        field = ".".join(str(p) for p in first["loc"])
        raise MalformedEnvelopeError(f"envelope invalid: {field}: {first['msg']}") from exc
```

**`MalformedEnvelopeError` subclass of `ValueError`** — consistent with `MCPToolError` at `mcp/helpers.py:17`. `translate_error` auto-wraps (Pitfall #1 precaution: error event handler must NOT call `deliver()` or `write()` recursively; log via direct `file_locked()` write only).

---

### 8. `clawteam/team/models.py::TeamMessage` — add fields (§90-122)

**Current shape to preserve** (`team/models.py:90-122`):
```python
class TeamMessage(BaseModel):
    model_config = {"populate_by_name": True}

    type: MessageType = MessageType.message
    from_agent: str = Field(alias="from", serialization_alias="from")
    to: str | None = None
    content: str | None = None
    request_id: str | None = Field(default=None, alias="requestId")
    # ... 15 other optional fields ...
    status: str | None = None
```

**Additive edit (D-06):** add three required fields at the bottom, consistent with the existing alias convention (`alias="camelCase"` if bridging JS callers):
```python
    persona: str = Field(..., min_length=1)
    step_label: str = Field(..., min_length=1, alias="stepLabel")
    done: bool = Field(...)
```

**BC-preservation:** All 15 existing optional fields keep their defaults. Only the three new fields are required — every existing TeamMessage construction site must be updated (the envelope validation fail-closed at `Transport.deliver()` is the enforcement point, per D-08). Grep for `TeamMessage(` across the codebase before planning this change to enumerate call sites.

---

### 9. `clawteam/harness/artifacts.py::ArtifactStore.write` — hook chain (§22-31)

**Current simple shape** (§22-31):
```python
def write(self, name: str, content: str, metadata: dict[str, Any] | None = None) -> Path:
    path = self._dir / name
    path.write_text(content, encoding="utf-8")
    if metadata:
        meta_path = self._dir / f"{name}.meta.json"
        meta_path.write_text(
            json.dumps({**metadata, "written_at": _now_iso()}, indent=2),
            encoding="utf-8",
        )
    return path
```

**Hook chain to add (D-07, D-08, D-10, D-27, D-14), in strict order** (from research §Architecture Diagram and §Integration Points):
1. **Size-cap check** → raise `ArtifactTooLargeError(name, len(content), cap, suggestion="split into <name>-part1.md etc. or raise cap via --artifact-cap")` if `len(content) > cap`.
2. **Emit `BeforeFileWrite`** event → check `event.veto`; raise `FrozenPathError(event.veto_reason)` if vetoed.
3. **Atomic write** via existing `path.write_text` (consider replacing with `atomic_write_text` for consistency).
4. **Increment `SprintState.turn_counters[agent]`** (D-14) — guarded by `turn_id` dedupe (Pitfall #2).

**Critical invariant (Pitfall #8 — the Phase 2 hinge for upstream PR):** Frontmatter validation is **NOT** in this hook chain. Frontmatter is parsed by `EvidenceGate.check()` at gate-time, not at write-time. Existing templates (software-dev, hedge-fund, research-paper, etc.) that call `write("spec.md", content)` without frontmatter must continue to pass. The `EvidenceGate` is opt-in via the Phase 3 `GstackSprintPlugin.on_register`; existing templates keep `ArtifactRequiredGate`.

---

### 10. `clawteam/events/types.py` — 8 new event dataclasses

**Analog:** existing event family at `events/types.py:24-195`.

**Before* event shape (copy verbatim; set `veto: bool = False`):**
```python
@dataclass
class BeforeWorkerSpawn(HarnessEvent):
    """Fired before a worker agent is spawned. Set veto=True to cancel."""
    agent_name: str = ""
    agent_type: str = ""
    command: list[str] = field(default_factory=list)
    veto: bool = False
```
(`events/types.py:24-31`)

**New Before* events (D-10):**
```python
@dataclass
class BeforeToolCall(HarnessEvent):
    """Fired before an MCP tool or intercepted CLI command runs. Set veto=True to cancel."""
    agent_name: str = ""
    tool_name: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    veto: bool = False
    veto_reason: str = ""

@dataclass
class BeforeFileWrite(HarnessEvent):
    """Fired before ArtifactStore.write or WorkspaceManager git-write. Set veto=True to cancel."""
    agent_name: str = ""
    path: str = ""
    size_bytes: int = 0
    veto: bool = False
    veto_reason: str = ""
```

**Notification/report events (follow `PhaseTransition` shape at §170-175; no veto field):**
```python
@dataclass
class MalformedEnvelope(HarnessEvent):
    agent: str = ""
    violation: str = ""
    turn_id: str = ""

@dataclass
class DriftRegression(HarnessEvent):
    agent: str = ""
    consecutive_count: int = 0
    last_violation: str = ""

@dataclass
class FreezeChange(HarnessEvent):
    action: str = ""  # "freeze" | "unfreeze"
    path: str = ""
    agent: str = ""
    reason: str = ""
    actor: str = ""

@dataclass
class CycleDetected(HarnessEvent):
    pair: tuple[str, str] = ("", "")
    topic_hash: str = ""
    route_keys: list[str] = field(default_factory=list)
    window_size: int = 20

@dataclass
class ForcedProgressTriggered(HarnessEvent):
    agent: str = ""
    consecutive_no_progress: int = 0
    question_id: str = ""

@dataclass
class ArtifactCapExceeded(HarnessEvent):
    artifact_name: str = ""
    size_bytes: int = 0
    cap_bytes: int = 0
    scope: str = ""  # "file" or "phase"
```

**No changes to `events/bus.py`** — veto loop at §86-101 already implements the pattern correctly.

---

### 11. `clawteam/team/routing_policy.py::DefaultRoutingPolicy.decide` — cycle detector

**Current structure to extend** (`routing_policy.py:100-156`):
The decide method reads state, sets up route, runs throttle check, emits the throttle event via `_append_event`, saves state, returns `RouteDecision`. Cycle detection MUST run **before** the throttle check (research Example 4 §1066-1096).

**Existing helper to reuse:** `_append_event(state, route_key, route, action, reason, summary, timestamp, error="")` at `routing_policy.py:384-408`. Cycle detector extends the event-append call with an extra `topicHash` field so the cycle scanner can read it.

**Route-key helper:** `_route_key(source, target) -> "source->target"` at `routing_policy.py:292-294`.

**Rolling-window constant:** `_RECENT_EVENT_LIMIT = 50` at `routing_policy.py:16`. Cycle scan window is last 20 (D-20) — `state["recentEvents"][-20:]` as research §Example 4 shows.

**Anti-pattern (research):** Don't introduce a parallel tracker. Every new state field lives under `routes[route_key]` — specifically `suppressedTopics: list[str]` on the route dict (mirrors existing `pendingEnvelopes`, `pendingCount` fields at §307-313).

**Emit discipline (Pitfall #7):** `CycleDetected` must use sync `emit()`, not `emit_async()` — the `suppressedTopics` state update is in-flight and must reach disk before `decide()` returns.

---

### 12. `clawteam/transport/base.py::Transport.deliver` — pre-deliver hook

**Current minimal ABC** (§12):
```python
@abstractmethod
def deliver(self, recipient: str, data: bytes) -> None:
    """Deliver message bytes to a recipient's inbox."""
```

**Pre-deliver hook chain to add** (D-08, D-14, plus cycle-detect consultation):
1. Parse `data` → `TeamMessage` via pydantic
2. `validate_envelope(...)` → raise `MalformedEnvelopeError` on fail
3. Consult `DefaultRoutingPolicy.decide()` — if action is `"suppress"` (cycle), short-circuit
4. Emit existing `BeforeInboxSend` (already at `events/types.py:94-100`)
5. Actual transport-specific deliver
6. Increment `SprintState.turn_counters[agent]` (guarded by `turn_id` per Pitfall #2)

**Note:** `deliver()` is abstract — the hook chain belongs in concrete transports (`file.py`, `claimed.py`, `p2p.py`) or in a helper called by each. Plan should prefer a helper function `_pre_deliver_hooks(recipient, data) -> TeamMessage` in `transport/base.py` that concrete transports call at the top of their override.

---

### 13. `clawteam/workspace/manager.py` — emit `BeforeFileWrite`

**Analog:** any existing write-path method on `WorkspaceManager`. Currently uses `ensure_within_root` guard (workspace/manager.py:12).

**Emit pattern** (copy from research §Pattern 2):
```python
from clawteam.events.global_bus import get_event_bus
from clawteam.events.types import BeforeFileWrite

# Before any path mutation (git write, checkpoint, merge):
event = BeforeFileWrite(
    team_name=self._team_name,
    agent_name=agent_name,
    path=str(target_path),
    size_bytes=0,  # or known size
)
get_event_bus().emit(event)
if event.veto:
    from clawteam.harness.freeze_registry import FrozenPathError
    raise FrozenPathError(event.veto_reason or f"{target_path} is frozen")
```
**Integration points to modify:** locate git-write / checkpoint / merge methods in `workspace/manager.py` and wrap each with this pre-emit. Planner should enumerate exact call sites (create_workspace, checkpoint, merge, cleanup) before writing the plan.

---

### 14. `clawteam/mcp/server.py::_tool` — emit `BeforeToolCall`

**Current shape** (§16-25):
```python
def _tool(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            raise translate_error(exc) from exc

    wrapped.__signature__ = inspect.signature(fn)
    return mcp.tool()(wrapped)
```

**Add pre-call emit** (before the `try` block):
```python
def _tool(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        # Emit BeforeToolCall for /careful + /freeze interception (D-10, D-13)
        from clawteam.events.global_bus import get_event_bus
        from clawteam.events.types import BeforeToolCall
        from clawteam.identity import AgentIdentity

        event = BeforeToolCall(
            team_name=AgentIdentity.from_env().team_name or "",
            agent_name=AgentIdentity.from_env().agent_name,
            tool_name=fn.__name__,
            args=kwargs,  # positional args rarely used in FastMCP
        )
        get_event_bus().emit(event)
        if event.veto:
            from clawteam.harness.freeze_registry import FrozenPathError
            raise FrozenPathError(event.veto_reason or f"tool {fn.__name__} vetoed")
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            raise translate_error(exc) from exc

    wrapped.__signature__ = inspect.signature(fn)
    return mcp.tool()(wrapped)
```

---

### 15. `clawteam/mcp/helpers.py::translate_error` — explicit branches (§25-32)

**Current shape:**
```python
def translate_error(exc: Exception) -> MCPToolError:
    if isinstance(exc, MCPToolError):
        return exc
    if isinstance(exc, TaskLockError):
        return MCPToolError(str(exc))
    if isinstance(exc, (ValueError, RuntimeError)):
        return MCPToolError(str(exc))
    return MCPToolError(f"Unexpected error: {exc}")
```

**Because all new errors subclass `ValueError`, they are auto-wrapped by the 4th branch.** Adding explicit branches is optional but improves message clarity and sets specific MCP error codes. If the plan chooses to add branches:
```python
    if isinstance(exc, FrozenPathError):
        return MCPToolError(str(exc))  # message already carries remediation per D-12
    if isinstance(exc, MalformedEnvelopeError):
        return MCPToolError(str(exc))
    # ...etc
```

---

### 16. `clawteam/plugins/base.py::HarnessPlugin` — new hook

**Analog:** three existing Phase 1 hooks at `plugins/base.py:46-75` — `contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`.

**Shape to copy** (`plugins/base.py:46-54`):
```python
def contribute_phases(self) -> list[Phase]:
    """Contribute lifecycle phase names to the PhaseRegistry.
    ...
    """
    return []
```

**Adapt for:**
```python
def contribute_evidence_schemas(self) -> dict[str, type[ArtifactFrontmatterBase]]:
    """Contribute artifact-frontmatter schemas to EvidenceSchemaRegistry.

    Keys are artifact_type strings (e.g., "design-doc", "plan-doc"); values are
    pydantic subclasses of ArtifactFrontmatterBase. Duplicate keys across plugins
    are fatal at registration time (mirrors PhaseRegistry D-03 namespace rule).
    Empty-dict default means the plugin registers no schemas.
    """
    return {}
```

**Plugin manager integration:** the Phase 1 `plugins/manager.py` already loops over plugins calling `contribute_phases()` etc. — add one more loop for `contribute_evidence_schemas()`, calling `evidence_schemas.register_schema(k, v)` for each entry.

---

### 17. `clawteam/cli/commands.py` — `sprint` sub-app

**Analog:** 10+ existing sub-apps at `cli/commands.py:212, 297, 300, 1235, 1783, 1985, 2109, 2338, 2629, 2728`.

**Sub-app declaration idiom** (§1235-1236):
```python
team_app = typer.Typer(help="Team management commands")
app.add_typer(team_app, name="team")
```

**Adapt for:**
```python
sprint_app = typer.Typer(help="Sprint lifecycle commands", no_args_is_help=True)
app.add_typer(sprint_app, name="sprint")
```

**Existing `--json` global flag** (§34, 88-90, 117-122):
```python
_json_output: bool = False
# ...
json_out: bool = typer.Option(False, "--json", help="Output JSON instead of human-readable text."),
# ...
def _output(data: dict | list, human_fn=None):
    if _json_output:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    elif human_fn:
        human_fn(data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
```

**Sprint-specific `_emit_ok` / `_emit_err` helpers** (research §Example 3 at §996-1011 — copy verbatim, enforces D-26 envelope shape):
```python
def _emit_ok(data: dict, warnings: list[str] | None = None) -> None:
    payload = {"ok": True, "data": data, "warnings": warnings or [], "error": None}
    if _json_output:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _render_sprint(data)

def _emit_err(code: str, message: str) -> None:
    payload = {"ok": False, "data": None, "warnings": [], "error": {"code": code, "message": message}}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    raise typer.Exit(1)
```

**Subcommand skeleton** (per D-24; copy research Example 3 §1013-1055 shape):
- `sprint start --team --goal [--auto-advance] [--artifact-cap KB] [--phase-artifact-cap KB]`
- `sprint status <id|prefix> [--team]`
- `sprint show <id|prefix> [--team]`
- `sprint list --team`  *(MUST raise `MissingTeamError` if `--team` and `$CLAWTEAM_TEAM` both absent — Pitfall #9)*
- `sprint pause <id|prefix> [--team]`
- `sprint resume <id|prefix> [--team]`

**Env var convention** for team: `envvar="CLAWTEAM_TEAM"` on `--team` option (Typer auto-reads).

**Cap env vars route through `identity._env`** (D-29). The existing helper accepts multi-gen keys:
```python
# In SprintConductor.__init__ or CLI start handler:
cap = (cli_flag or 0) * 1024
if cap == 0:
    env_kb = _env("CLAWTEAM_ARTIFACT_CAP_KB", "OH_ARTIFACT_CAP_KB", "CLAUDE_CODE_ARTIFACT_CAP_KB", "0")
    cap = int(env_kb) * 1024
final_cap = cap or state.artifact_cap_bytes  # highest layer wins
```

---

### 18. Test files

**Test fixture layout (flat `tests/`)** — matches existing convention: `tests/test_harness.py`, `tests/test_event_bus.py`, `tests/test_runtime_routing.py`, etc. No subdirectory.

**Fixture pattern for registries** (Phase 1 precedent, noted in `01-05-PLAN.md:155`):
```python
def setup_function():
    from clawteam.harness.evidence_schemas import reset_registry
    from clawteam.harness.freeze_registry import reset_freeze_registry
    reset_registry()
    reset_freeze_registry()

def teardown_function():
    reset_registry()
    reset_freeze_registry()
```

**CLI testing** — use `typer.testing.CliRunner` (check existing CLI tests for exact harness; pattern is standard Typer).

**EventBus test setup** (from `tests/test_event_bus.py:45-55`, referenced in research):
```python
bus = EventBus()
vetoed = []
bus.subscribe(BeforeFileWrite, lambda e: (e.__setattr__("veto", True), e.__setattr__("veto_reason", "test")))
event = BeforeFileWrite(team_name="t", path="/tmp/x", size_bytes=100)
bus.emit(event)
assert event.veto is True
```

---

## Shared Patterns (cross-cutting; apply to multiple files)

### Shared Pattern A: `uuid.uuid4().hex[:8]` for every new ID

**Source:** `clawteam/harness/phases.py:42` (`harness_id`), `clawteam/harness/contracts.py:28` (`SprintContract.id`), `clawteam/team/models.py:129` (`TaskItem.id`).

**Apply to:** `SprintState.sprint_id` (Phase 1), `Question.id`, `turn_id` (D-07), `question_id` in `forced_progress_gate` (D-17), any cycle-event `cycle_id` if introduced.

```python
import uuid
uuid.uuid4().hex[:8]
```

Never use incrementing counter + collision check. Never use longer/shorter slice (the 8-char convention is pinned across the codebase).

---

### Shared Pattern B: `file_locked()` + `atomic_write_text()` for durable JSON

**Source:** `clawteam/fileutil.py:28-83` + usage at `clawteam/team/snapshot.py:21-22, 181-183, 294-296`.

**Apply to:** `freeze.json`, `test_verify_cache.json`, sprint `state.json` (Phase 1), any new JSON file under `~/.clawteam/teams/<team>/sprints/<id>/`. Never use direct `path.write_text(json.dumps(...))` for durable state — concurrency invariant.

```python
from clawteam.fileutil import file_locked, atomic_write_text

with file_locked(p):
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    data["new_field"] = value
    atomic_write_text(p, json.dumps(data, indent=2, ensure_ascii=False))
```

**Do NOT use for JSONL appends** — `freeze_audit.jsonl` uses plain `open(path, "a")` per `exit_journal.py:42-43`.

---

### Shared Pattern C: Sprint directory path

**Source:** Phase 1 D-05 (locked).

**Path:** `get_data_dir() / "teams" / team_name / "sprints" / sprint_id`

**Apply to:** all new persistence (`freeze.json`, `freeze_audit.jsonl`, `test_verify_cache.json`, envelope-error log). Import from `clawteam.team.models`:

```python
from clawteam.team.models import get_data_dir

def _sprint_dir(team: str, sprint_id: str) -> Path:
    return get_data_dir() / "teams" / team / "sprints" / sprint_id
```

---

### Shared Pattern D: EventBus `Before*` event veto

**Source:** `clawteam/events/bus.py:86-101` + `tests/test_event_bus.py::test_veto_pattern` (referenced in research §Pattern 2).

**Apply to:** `BeforeToolCall`, `BeforeFileWrite` (D-10). Subscribers set `event.veto = True` and `event.veto_reason = "..."`; the caller checks `event.veto` after `emit()` returns and raises the structured error.

```python
event = BeforeFileWrite(team_name=..., path=..., size_bytes=...)
get_event_bus().emit(event)
if event.veto:
    raise FrozenPathError(event.veto_reason or "write vetoed")
```

**Anti-pattern (research):** Subscribers must NEVER raise `FrozenPathError` themselves — only set `event.veto = True`. The caller raises.

---

### Shared Pattern E: Subclass `ValueError` for structured errors

**Source:** `clawteam/mcp/helpers.py:17` (`MCPToolError(ValueError)`).

**Apply to:** `FrozenPathError`, `MalformedEnvelopeError`, `ArtifactTooLargeError`, `AmbiguousSprintError`, `SprintNotFoundError`, `MissingTeamError`.

```python
class FrozenPathError(ValueError):
    """Raised when an agent write/tool-call is vetoed by FreezeRegistry."""
```

**Benefit:** `translate_error` at `mcp/helpers.py:30` auto-wraps any `ValueError` subclass into `MCPToolError` for MCP responses — no explicit branches needed (though the plan may add them for message clarity).

---

### Shared Pattern F: Pydantic v2 `(bool, str)` gate-check return

**Source:** `clawteam/harness/phases.py::PhaseGate.check` (§60).

**Apply to:** `EvidenceGate.check`, `forced_progress_gate.check`, any new PhaseGate subclass.

```python
def check(self, state: PhaseState) -> tuple[bool, str]:
    # ...
    return True, ""   # or (False, "reason with sufficient detail for human")
```

Never raise from `check` — always return the tuple. Exceptions should be caught and converted to `(False, f"unexpected error: {exc}")`.

---

### Shared Pattern G: Multi-generation env var via `_env`

**Source:** `clawteam/identity.py:10-36`.

**Apply to:** every new env var the plan introduces (`CLAWTEAM_ARTIFACT_CAP_KB`, `CLAWTEAM_PHASE_ARTIFACT_CAP_KB`, `CLAWTEAM_TEST_TIMEOUT_SECONDS`).

```python
from clawteam.identity import _env

cap_kb = int(_env(
    "CLAWTEAM_ARTIFACT_CAP_KB",
    "OH_ARTIFACT_CAP_KB",
    "CLAUDE_CODE_ARTIFACT_CAP_KB",
    default="50",
) or "50")
```

**Never** read `os.environ[...]` directly for a ClawTeam-namespaced var.

---

### Shared Pattern H: `translate_error` auto-wrapping (MCP path)

**Source:** `clawteam/mcp/helpers.py:25-32`.

**Apply to:** All new errors are `ValueError` subclasses, so the MCP `_tool` wrapper catches + re-raises as `MCPToolError` automatically. Agents receive a structured response with the remediation hint (D-12: `"/unfreeze <path>"`).

**Anti-pattern:** Don't add a new exception hierarchy. Subclass `ValueError` (`MCPToolError`'s root) per §17 instead.

---

## No Analog Found

Every file has at least a role-match analog. The two files that come closest to "genuinely new pattern invention":

| File | Role | Closest Analog | Why It Still Matches |
|------|------|----------------|----------------------|
| `clawteam/sprint/conductor.py` | sprint-level loop owner | `harness/orchestrator.py` (older per-run model) + `harness/phases.py::PhaseRunner` (per-phase gate loop) | Composes the two existing models. New level of abstraction but every internal method (save/load, advance, event-emit) is a direct copy of existing idioms. |
| `clawteam/team/envelope.py::parse_frontmatter` | YAML frontmatter parser | No existing YAML/frontmatter parser in the codebase | **But** the stdlib regex + `yaml.safe_load` approach is 30 lines and the research explicitly chose it over adding `python-frontmatter` dep (research §Standard Stack recommendation). This is a genuinely new 30-line utility — not a new pattern, just a new stdlib helper. |

Both files are planner-straightforward (explicit recipes in research §Code Examples).

---

## Metadata

**Analog search scope:**
- `clawteam/harness/` (16 files) — gate + state + journal + registry patterns
- `clawteam/team/` — models, routing_policy, snapshot patterns
- `clawteam/events/` — bus + types veto pattern
- `clawteam/fileutil.py` — atomic write + file lock primitives
- `clawteam/identity.py` — multi-gen env helper
- `clawteam/mcp/` — tool wrapper + error translation
- `clawteam/cli/commands.py` — Typer sub-app pattern (10+ existing sub-apps)
- `clawteam/plugins/base.py` — plugin hook conventions
- `clawteam/transport/base.py` — ABC shape
- `clawteam/workspace/manager.py` — file-write integration points
- Phase 1 plans in `.planning/phases/01-core-harness-extensions/` for `SprintState` / `InteractionGate` / Q&A schema (Phase 1 not yet merged — plans are the spec)

**Files scanned:** 32 (clawteam/ subset) + 5 Phase 1 plan documents.

**Pattern extraction date:** 2026-04-17.

**Confidence:** HIGH — every pattern assignment has a concrete file:line citation in the current branch; no speculative analogs. The two "new invention" files (conductor, frontmatter parser) have documented recipes in RESEARCH.md §Code Examples that the planner can port verbatim.

---

*Phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention*
*Pattern mapping completed: 2026-04-17*
