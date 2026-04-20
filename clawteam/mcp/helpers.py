"""Shared helpers for ClawTeam MCP tools."""

from __future__ import annotations

from enum import Enum
from typing import Any, TypeVar

from clawteam.team.costs import CostStore
from clawteam.team.mailbox import MailboxManager
from clawteam.team.manager import TeamManager
from clawteam.team.plan import PlanManager
from clawteam.team.tasks import TaskLockError, TaskStore

EnumT = TypeVar("EnumT", bound=Enum)


class MCPToolError(ValueError):
    """Structured tool error surfaced to MCP clients."""


def fail(message: str) -> None:
    raise MCPToolError(message)


def translate_error(exc: Exception) -> MCPToolError:
    """Wrap an arbitrary exception in MCPToolError for MCP-client delivery.

    Phase 2 (Plan 02-10, D-12) adds explicit branches for six error classes so
    MCP clients receive structured, remediation-carrying messages. All six
    subclass ValueError, so the generic fallback would already wrap them — the
    explicit branches exist for message clarity and future error-code dispatch.

    Imports for the Phase 2 error classes are guarded with ``try/except
    ImportError`` because three of them (AmbiguousSprintError,
    SprintNotFoundError, MissingTeamError) land in later plans; their absence
    must not break translate_error for earlier plans.
    """
    if isinstance(exc, MCPToolError):
        return exc
    if isinstance(exc, TaskLockError):
        return MCPToolError(str(exc))

    # Phase 2 explicit branches (Plan 02-10, D-12). Guarded imports let this
    # function work even before Plans 02-07 / 02-11 / 02-12 land their errors.
    # The N806 suppressions below apply because the fallback names are class
    # aliases (intentionally CapitalCamelCase), not local variables.
    try:
        from clawteam.harness.freeze_registry import FrozenPathError
    except ImportError:  # pragma: no cover — registry always present in Phase 2
        FrozenPathError = None  # type: ignore[assignment]  # noqa: N806
    try:
        from clawteam.team.envelope import MalformedEnvelopeError
    except ImportError:  # pragma: no cover
        MalformedEnvelopeError = None  # type: ignore[assignment]  # noqa: N806
    try:
        from clawteam.harness.errors import ArtifactTooLargeError
    except ImportError:  # pragma: no cover
        ArtifactTooLargeError = None  # type: ignore[assignment]  # noqa: N806
    try:
        from clawteam.sprint.conductor import (  # type: ignore[attr-defined]
            AmbiguousSprintError,
            MissingTeamError,
            SprintNotFoundError,
        )
    except ImportError:
        AmbiguousSprintError = SprintNotFoundError = MissingTeamError = None  # type: ignore[assignment]  # noqa: N806

    for cls in (
        FrozenPathError,
        MalformedEnvelopeError,
        ArtifactTooLargeError,
        AmbiguousSprintError,
        SprintNotFoundError,
        MissingTeamError,
    ):
        if cls is not None and isinstance(exc, cls):
            return MCPToolError(str(exc))

    if isinstance(exc, (ValueError, RuntimeError)):
        return MCPToolError(str(exc))
    return MCPToolError(f"Unexpected error: {exc}")


def to_payload(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "model_dump"):
        return to_payload(value.model_dump(by_alias=True, exclude_none=True))
    if isinstance(value, dict):
        return {key: to_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_payload(item) for item in value]
    return value


def coerce_enum(enum_cls: type[EnumT], value: str | None) -> EnumT | None:
    return enum_cls(value) if value else None


def require_team(team_name: str):
    team = TeamManager.get_team(team_name)
    if team is None:
        raise ValueError(f"Team '{team_name}' not found")
    return team


def team_mailbox(team_name: str) -> MailboxManager:
    require_team(team_name)
    return MailboxManager(team_name)


def task_store(team_name: str) -> TaskStore:
    require_team(team_name)
    return TaskStore(team_name)


def plan_manager(team_name: str) -> PlanManager:
    return PlanManager(team_name, team_mailbox(team_name))



def cost_store(team_name: str) -> CostStore:
    require_team(team_name)
    return CostStore(team_name)
