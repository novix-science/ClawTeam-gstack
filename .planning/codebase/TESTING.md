# Testing Patterns

**Analysis Date:** 2026-04-15

## Test Framework

**Runner:** `pytest` (`pytest>=9.0.0,<10.0.0`, declared in `pyproject.toml` under `[project.optional-dependencies] dev`).

**Config:** `pyproject.toml`
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
```
No custom markers, no plugins beyond stock pytest.

**Assertion style:** Plain `assert` statements — no `unittest.TestCase`, no external assertion library.

**Run commands** (from `.agents/skills/clawteam-dev/SKILL.md`):
```bash
ruff check clawteam/ tests/       # Lint first
pytest tests/<target_file>.py -q  # Single-module run (preferred)
pytest tests/ -v --tb=short       # Full suite (CI)
```

CI matrix runs on Python 3.10 / 3.11 / 3.12, Ubuntu + macOS (`.github/workflows/ci.yml`).

## Test File Organization

**Location:** Separate `tests/` directory at repo root — not co-located with source.

**Naming:** `tests/test_<module>.py`, one file per source module. Examples:
- `tests/test_adapters.py`    ↔ `clawteam/spawn/adapters.py`
- `tests/test_harness.py`     ↔ `clawteam/harness/*`
- `tests/test_spawn_backends.py` ↔ `clawteam/spawn/subprocess_backend.py` + `tmux_backend.py`
- `tests/test_waiter.py`      ↔ `clawteam/team/waiter.py`
- `tests/test_cli_commands.py`↔ `clawteam/cli/commands.py`

**Count:** 38 test modules, ~8,675 total lines. Largest: `tests/test_waiter.py` (387 lines).

**Package marker:** `tests/__init__.py` makes `tests` an importable package (empty file).

## Shared Fixtures — `tests/conftest.py`

Two fixtures, both critical:

```python
@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """Point CLAWTEAM_DATA_DIR at a temp dir so every test gets a clean slate."""
    data_dir = tmp_path / ".clawteam"
    data_dir.mkdir()
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(data_dir))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return data_dir

@pytest.fixture
def team_name():
    return "test-team"
```

**Key rule:** `isolated_data_dir` is `autouse=True`, so **no test ever touches the real `~/.clawteam`**. Both `HOME` and `USERPROFILE` are redirected so `config_path()` resolution is also isolated. Any new test automatically gets the clean slate — do not override.

## Test Structure

**Two styles coexist** — both are valid.

**Style A — class-grouped (`xUnit`-like):** Group related tests into `TestThing` classes with no base class; pytest discovers them automatically.

```python
# tests/test_adapters.py:19
class TestCLIDetection:
    """Each detector must accept full paths, bare names, and reject others."""

    def test_is_qwen_command(self):
        assert is_qwen_command(["qwen"])
        assert is_qwen_command(["/usr/local/bin/qwen"])
        assert not is_qwen_command(["claude"])

class TestPrepareCommandSkipPermissions:
    adapter = NativeCliAdapter()   # class-level shared instance

    def test_qwen_gets_yolo(self):
        result = self.adapter.prepare_command(["qwen"], skip_permissions=True)
        assert "--yolo" in result.final_command
```

Used by `tests/test_adapters.py`, `tests/test_harness.py`, `tests/test_config.py`, etc. (20 files have `class Test...`).

**Style B — flat functions:** Simple module-level `test_*` functions.

```python
# tests/test_spawn_backends.py:35
def test_subprocess_backend_prepends_current_clawteam_bin_to_path(monkeypatch, tmp_path):
    ...
```

Used by `tests/test_spawn_backends.py`, `tests/test_waiter.py`, `tests/test_cli_commands.py`.

## Mocking

**Framework:** `unittest.mock` (stdlib) — `MagicMock`, `patch`.
29 of 38 test files use `monkeypatch`, `MagicMock`, `unittest.mock`, or `tmp_path`.

**Patterns:**

1. **`monkeypatch.setenv` / `monkeypatch.setattr`** is the default for environment and attribute patching.
   ```python
   # tests/test_spawn_backends.py:36-53
   monkeypatch.setenv("PATH", "/usr/bin:/bin")
   monkeypatch.setattr(sys, "argv", [str(clawteam_bin)])
   monkeypatch.setattr("clawteam.spawn.subprocess_backend.subprocess.Popen", fake_popen)
   monkeypatch.setattr("clawteam.spawn.registry.register_agent", lambda **_: None)
   ```

2. **Capture dicts** record what a mocked function was called with, instead of using `Mock.call_args` — easier to assert against:
   ```python
   captured: dict[str, object] = {}
   def fake_popen(cmd, **kwargs):
       captured["cmd"] = cmd
       captured["env"] = kwargs["env"]
       return DummyProcess()
   ```

3. **Hand-rolled dummy classes** for small collaborators instead of `MagicMock`:
   ```python
   # tests/test_spawn_backends.py:27
   class DummyProcess:
       def __init__(self, pid: int = 4321):
           self.pid = pid
       def poll(self):
           return None
   ```

4. **`MagicMock` fixtures** for larger collaborators with several methods stubbed in one place:
   ```python
   # tests/test_waiter.py:27
   @pytest.fixture
   def mailbox():
       m = MagicMock()
       m.receive.return_value = []
       return m
   ```

5. **`unittest.mock.patch`** as a decorator/context for targeted module-level patching — imported as `from unittest.mock import patch` (`tests/test_adapters.py:5`).

**What to mock:** `subprocess.Popen`, `shutil.which`, external-process spawners, module-level registry writes, anything that hits the network / filesystem outside `tmp_path`, anything that reads real env vars.

**What NOT to mock:** Pydantic models, dataclasses, enums, pure helpers. Build them with real data via factory helpers:

```python
# tests/test_waiter.py:14
def _make_task(task_id="t1", status=TaskStatus.pending, owner="", subject="test task") -> TaskItem:
    return TaskItem(id=task_id, subject=subject, status=status, owner=owner)

def _make_message(from_agent="alice", content="hello") -> TeamMessage:
    return TeamMessage(**{"from": from_agent, "content": content})
```

## CLI Testing

Typer's `CliRunner` is the standard tool. Always pass `env=` explicitly so the command sees the redirected data dir:

```python
# tests/test_cli_commands.py:13
from typer.testing import CliRunner
from clawteam.cli.commands import app

def test_config_cli_supports_all_keys_and_bool_values(tmp_path):
    runner = CliRunner()
    env = {"HOME": str(tmp_path), "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam")}
    result = runner.invoke(app, ["config", "set", "skip_permissions", "false"], env=env)
    assert result.exit_code == 0
    assert load_config().skip_permissions is False
```

Assert on `result.exit_code` and `result.output`. Prefer round-tripping through the real config loader (`load_config()`) to confirm persistence, rather than parsing stdout.

## Fixtures & Factories

- Module-local factory helpers named with leading underscore: `_make_task`, `_make_message` (`tests/test_waiter.py:14-25`).
- No shared fixtures directory — each test module defines its own factories close to where they are used.
- `tmp_path` (stock pytest) is the universal filesystem fixture; combine with `monkeypatch.setenv` to redirect I/O.

## Coverage

- **No coverage threshold enforced.** `pytest-cov` is not installed. CI runs `pytest -v --tb=short` with no `--cov` flag.
- Coverage is implicit: one `test_<module>.py` per source module; PR reviewers check new code has a matching test file.

## Test Types

**Unit tests:** The vast majority. Each source module gets a focused test file, collaborators are mocked.

**Integration tests:** Co-located in the same `tests/` tree — e.g. `tests/test_inbox_routing.py`, `tests/test_runtime_routing.py`, `tests/test_lifecycle.py`. These instantiate real `TeamManager`, `MailboxManager`, etc., relying on the `isolated_data_dir` autouse fixture for sandboxing.

**E2E / smoke:** Not pytest-driven. Documented as manual flows in `.agents/skills/clawteam-dev/SKILL.md` — invoke the real `clawteam` CLI:
```bash
clawteam team spawn-team dev-smoke -d "Local smoke test" -n leader
clawteam task create dev-smoke "..."
clawteam spawn --team dev-smoke --agent-name worker1 --task "..."
clawteam board show dev-smoke
clawteam task wait dev-smoke --timeout 300 --poll-interval 5
```

## Common Patterns

**Pytest parametrization:** Used sparingly. Explicit assert-blocks over parametrization for readability in detector tests (`tests/test_adapters.py:22`).

**Error / exit-code testing:** Assert on `result.exit_code` and substring-match `result.output`:
```python
# tests/test_cli_commands.py:52
assert result.exit_code == 1
assert "No join request found with id 'missing-req'" in result.output
```

**Serialization roundtrip:** Pydantic models are tested by save → load → compare (`tests/test_harness.py:36`):
```python
def test_serialization_roundtrip(self, tmp_path):
    state = PhaseState(team_name="test-team", goal="test goal")
    runner = PhaseRunner(state)
    path = runner.save(tmp_path)
    loaded = PhaseRunner.load(path)
    assert loaded.state.team_name == "test-team"
    assert loaded.state.harness_id == state.harness_id
```

**Phase / state-machine testing:** Step the machine explicitly and assert on each transition (`tests/test_harness.py:47`):
```python
def test_advance_through_phases(self):
    runner = PhaseRunner(PhaseState(team_name="t"))
    assert runner.advance() == PLAN
    assert runner.advance() == EXECUTE
    assert runner.advance() == VERIFY
    assert runner.advance() == "ship"
    assert runner.advance() is None
```

**Gate testing:** Construct the gate, register on the runner, assert `(ok, reason)` from `can_advance()` before calling `advance()` to confirm it is blocked (`tests/test_harness.py:56`).

---

*Testing analysis: 2026-04-15*
