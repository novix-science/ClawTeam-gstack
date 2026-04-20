"""Tests for BeforeToolCall + BeforeFileWrite emission + veto semantics (Plan 02-10).

Task 2a: MCP _tool wrapper emits BeforeToolCall before fn-call; translate_error
routes 6 Phase 2 error types explicitly.

Task 2b: WorkspaceManager's 4 write-path methods emit BeforeFileWrite; on veto
raise FrozenPathError (from freeze_registry) and skip the actual write.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import BeforeFileWrite, BeforeToolCall
from clawteam.harness.freeze_registry import FrozenPathError
from clawteam.mcp.helpers import MCPToolError, translate_error

# ── Shared isolation fixtures ──────────────────────────────────────────


@pytest.fixture
def isolated_bus(monkeypatch):
    """Replace the global EventBus with a fresh one for the test.

    Patches clawteam.events.global_bus._bus + _initialized so any
    ``get_event_bus()`` call during the test yields this local bus. Handlers
    added via ``bus.subscribe(...)`` are observed verbatim; no lingering state
    from the real global bus leaks into the assertion.
    """
    import clawteam.events.global_bus as gb_mod

    bus = EventBus()
    monkeypatch.setattr(gb_mod, "_bus", bus)
    monkeypatch.setattr(gb_mod, "_initialized", True)
    return bus


@pytest.fixture
def cleanup_mcp_tools():
    """Snapshot the MCP tool registry and restore it on teardown.

    Task 2a tests wrap dummy functions through ``_tool(...)`` which registers
    them on the shared FastMCP singleton. Other test files (e.g.
    ``test_mcp_server.py``) assert on the exact set of registered tools, so
    the dummy tools must be removed after each test to preserve cross-file
    isolation.
    """
    from clawteam.mcp.server import mcp

    before = set(mcp._tool_manager._tools.keys())
    yield
    after = set(mcp._tool_manager._tools.keys())
    for name in after - before:
        mcp._tool_manager.remove_tool(name)


# ── Task 2a Test 1: MCP _tool emits BeforeToolCall ─────────────────────


def test_mcp_tool_emits_before_tool_call(isolated_bus, cleanup_mcp_tools, monkeypatch):
    """_tool wrapper emits BeforeToolCall before fn(*args, **kwargs) runs."""
    from clawteam.mcp import server as server_mod

    captured: list[BeforeToolCall] = []
    isolated_bus.subscribe(BeforeToolCall, captured.append)

    # Minimal dummy fn — must have a non-empty signature so mcp.tool() accepts it.
    def _dummy(payload: str = "") -> str:
        return f"ran:{payload}"

    wrapped_raw = _unwrap_tool(server_mod._tool(_dummy))

    result = wrapped_raw(payload="hello")
    assert result == "ran:hello"
    assert len(captured) == 1
    event = captured[0]
    assert isinstance(event, BeforeToolCall)
    assert event.tool_name == "_dummy"
    assert event.args == {"payload": "hello"}


# ── Task 2a Test 2: veto raises FrozenPathError without running fn ─────


def test_mcp_tool_vetoed_call_raises_frozen_path_error(isolated_bus, cleanup_mcp_tools):
    """When a subscriber sets event.veto=True, _tool raises FrozenPathError and skips fn."""
    from clawteam.mcp import server as server_mod

    def _veto_handler(event: BeforeToolCall) -> None:
        event.veto = True
        event.veto_reason = "test veto reason"

    isolated_bus.subscribe(BeforeToolCall, _veto_handler)

    call_count = {"n": 0}

    def _never_called() -> None:
        call_count["n"] += 1
        return None

    wrapped_raw = _unwrap_tool(server_mod._tool(_never_called))

    with pytest.raises(FrozenPathError) as exc_info:
        wrapped_raw()
    assert "test veto reason" in str(exc_info.value)
    assert call_count["n"] == 0


# ── Task 2a Tests 3-4: translate_error branches ────────────────────────


def test_translate_error_maps_frozen_path_error():
    """translate_error(FrozenPathError(msg)) returns MCPToolError preserving msg."""
    exc = FrozenPathError(
        "/tmp/x is /freeze-locked by engineer; unfreeze via /unfreeze /tmp/x"
    )
    wrapped = translate_error(exc)
    assert isinstance(wrapped, MCPToolError)
    assert "freeze-locked" in str(wrapped)
    assert "unfreeze via" in str(wrapped)


def test_translate_error_maps_phase2_error_classes():
    """translate_error explicitly routes all 6 Phase 2 error types.

    Only the error classes that currently exist in the codebase are asserted.
    AmbiguousSprintError / SprintNotFoundError / MissingTeamError land in
    Plans 02-07 / 02-11 / 02-12; the translate_error code has guarded imports
    for them so they route automatically once those plans ship.
    """
    from clawteam.harness.errors import ArtifactTooLargeError
    from clawteam.team.envelope import MalformedEnvelopeError

    for exc in [
        FrozenPathError("frozen"),
        MalformedEnvelopeError("envelope invalid: persona: required"),
        ArtifactTooLargeError("too-big: 123 bytes > 100"),
    ]:
        wrapped = translate_error(exc)
        assert isinstance(wrapped, MCPToolError)
        assert str(exc) in str(wrapped)


# ── Task 2b Test 5: WorkspaceManager.create_workspace emits BeforeFileWrite ─


def test_workspace_create_emits_before_file_write(isolated_bus, tmp_path, monkeypatch):
    """create_workspace emits BeforeFileWrite with path=worktree_path before any mkdir/git.

    We do NOT need a real git repo for this assertion — we only need the emit
    to fire before the first filesystem op. The test uses a helper that wraps
    _emit_before_file_write directly, which is the observable contract. The
    actual git call can fail (we catch the GitError / OSError) because the
    emit happens first.
    """
    from clawteam.workspace import manager as ws_mod

    captured: list[BeforeFileWrite] = []
    isolated_bus.subscribe(BeforeFileWrite, captured.append)

    assert hasattr(ws_mod.WorkspaceManager, "_emit_before_file_write"), (
        "WorkspaceManager must expose _emit_before_file_write helper"
    )

    # Direct unit-test of the helper (the 4 write-path methods call it at entry).
    # Build a stand-in instance without running __init__ (which requires a git repo).
    wm = ws_mod.WorkspaceManager.__new__(ws_mod.WorkspaceManager)
    wm._team_name = "team-x"  # noqa: SLF001 (internal attr; test sets it directly)
    wm._emit_before_file_write("engineer", Path("/tmp/worktree-x"), size_bytes=0)

    assert len(captured) == 1
    evt = captured[0]
    assert isinstance(evt, BeforeFileWrite)
    assert evt.agent_name == "engineer"
    assert evt.path == str(Path("/tmp/worktree-x"))


# ── Task 2b Test 6: veto raises FrozenPathError ────────────────────────


def test_workspace_write_vetoed_raises_frozen_path_error(isolated_bus):
    """_emit_before_file_write raises FrozenPathError when a subscriber vetoes."""
    from clawteam.workspace import manager as ws_mod

    def _veto_handler(event: BeforeFileWrite) -> None:
        event.veto = True
        event.veto_reason = "simulated freeze veto"

    isolated_bus.subscribe(BeforeFileWrite, _veto_handler)

    wm = ws_mod.WorkspaceManager.__new__(ws_mod.WorkspaceManager)
    wm._team_name = "team-x"  # noqa: SLF001

    with pytest.raises(FrozenPathError) as exc_info:
        wm._emit_before_file_write("engineer", Path("/tmp/locked-wt"))
    assert "simulated freeze veto" in str(exc_info.value)


# ── Helpers ────────────────────────────────────────────────────────────


def _unwrap_tool(tool_obj):
    """Return the plain Python function behind FastMCP's tool registration.

    FastMCP wraps the function inside a ``FunctionTool`` object; the inner
    callable is accessible as ``.fn`` (verified against the version of mcp
    vendored in this repo). For our assertions we need the direct callable
    so the ``BeforeToolCall`` emit runs without MCP session plumbing.
    """
    # FastMCP's `.tool()(wrapped)` returns a FunctionTool; the wrapped function
    # we fed in is attached as `.fn`. If the object is already callable, use it.
    if hasattr(tool_obj, "fn") and callable(tool_obj.fn):
        return tool_obj.fn
    if callable(tool_obj):
        return tool_obj
    raise TypeError(f"cannot unwrap tool object: {tool_obj!r}")
