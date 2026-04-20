"""FastMCP server for ClawTeam."""

from __future__ import annotations

import inspect
from functools import wraps

from mcp.server.fastmcp import FastMCP

from clawteam.mcp.helpers import translate_error
from clawteam.mcp.tools import TOOL_FUNCTIONS

mcp = FastMCP("clawteam")


def _tool(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        # D-10: emit BeforeToolCall before any fn execution so /careful +
        # /freeze subscribers can veto. Subscribers are registered via
        # register_safety_subscribers(bus) from SprintConductor.__init__ only
        # under gstack sprints — existing templates have zero subscribers so
        # this emit is effectively a no-op for them (Pitfall #8 BC hinge).
        from clawteam.events.global_bus import get_event_bus
        from clawteam.events.types import BeforeToolCall
        from clawteam.identity import AgentIdentity

        identity = AgentIdentity.from_env()
        event = BeforeToolCall(
            team_name=identity.team_name or "",
            agent_name=identity.agent_name or "",
            tool_name=fn.__name__,
            args=dict(kwargs),  # positional args are rare under FastMCP
        )
        get_event_bus().emit(event)
        if event.veto:
            # Import inside the function so the import graph stays lazy and
            # we never pay the freeze_registry import cost on module load.
            from clawteam.harness.freeze_registry import FrozenPathError

            raise FrozenPathError(
                event.veto_reason or f"tool {fn.__name__} vetoed by safety rail"
            )

        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            raise translate_error(exc) from exc

    wrapped.__signature__ = inspect.signature(fn)
    return mcp.tool()(wrapped)


for tool_fn in TOOL_FUNCTIONS:
    _tool(tool_fn)


def main() -> None:
    mcp.run()
