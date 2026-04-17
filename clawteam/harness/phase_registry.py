"""Plugin-populated phase registry (Phase 1, RFC 001 §4.2).

Plugins contribute phase names, phase-role maps, and review routers through
the three optional hooks on HarnessPlugin. This module is the collection
surface. It is pure in-memory — no disk persistence (D-02).

Phase-name namespace is global: duplicate names across plugins are fatal at
registration time, per RFC 001 §4.2 requirement 2 and context decision D-03.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from clawteam.harness.phases import Phase

if TYPE_CHECKING:
    from clawteam.harness.review_router import ReviewRouter


@dataclass(frozen=True)
class RegisteredPhase:
    """One phase entry produced by a plugin contribution."""

    name: Phase
    plugin_name: str


@dataclass
class _PluginContribution:
    """Aggregated contribution snapshot for one plugin — internal to the registry."""

    plugin_name: str
    phases: tuple[Phase, ...]
    phase_roles: dict[Phase, list[str]] = field(default_factory=dict)
    review_routers: tuple["ReviewRouter", ...] = ()


class PhaseRegistry:
    """In-memory registry accumulating plugin phase/role/router contributions.

    Responsibilities (per RFC 001 §4.2):
    1. Accept phase contributions from plugins during plugin load.
    2. Preserve registration order.
    3. Reject duplicate phase names at registration time.
    4. Provide a read-only ordered phase list for harness initialization.

    Non-responsibilities: persisting sprint state, evaluating gates,
    choosing agent roles, interpreting gstack semantics.
    """

    def __init__(self) -> None:
        self._phases: list[RegisteredPhase] = []
        self._names: set[str] = set()
        self._phase_roles: dict[Phase, list[str]] = {}
        self._review_routers: list[ReviewRouter] = []
        self._contributions: list[_PluginContribution] = []

    def register(
        self,
        plugin_name: str,
        phases: list[Phase],
        phase_roles: dict[Phase, list[str]],
        review_routers: list[ReviewRouter],
    ) -> None:
        """Atomically register one plugin's contributions.

        Rolls back fully on any error — partial state is never left behind.
        """
        # Validate phase-role keys are subset of this plugin's declared phases (RFC 001 §4.3a req 3).
        declared = set(phases)
        for role_key in phase_roles.keys():
            if role_key not in declared:
                raise ValueError(
                    f"phase role entry for phase {role_key!r} not declared by plugin {plugin_name!r}"
                )

        # Validate duplicate phase names against already-registered names (RFC 001 §4.2 req 2).
        for phase in phases:
            if phase in self._names:
                raise ValueError(
                    f"Duplicate phase registration: {phase!r} "
                    f"(attempted by plugin {plugin_name!r})"
                )

        # All-or-nothing: commit only after validation passes.
        for phase in phases:
            self._phases.append(RegisteredPhase(name=phase, plugin_name=plugin_name))
            self._names.add(phase)
        self._phase_roles.update(phase_roles)
        self._review_routers.extend(review_routers)
        self._contributions.append(
            _PluginContribution(
                plugin_name=plugin_name,
                phases=tuple(phases),
                phase_roles=dict(phase_roles),
                review_routers=tuple(review_routers),
            )
        )

    def ordered_names(self) -> list[Phase]:
        """Read-only ordered phase list for harness initialization."""
        return [entry.name for entry in self._phases]

    def phase_roles(self) -> dict[Phase, list[str]]:
        """Merged phase-role map across all contributing plugins."""
        return dict(self._phase_roles)

    def review_routers(self) -> list[ReviewRouter]:
        """Ordered review routers; plugin load order."""
        return list(self._review_routers)

    def contributions(self) -> list[_PluginContribution]:
        """Per-plugin contribution snapshots (debug/introspection)."""
        return list(self._contributions)


# ── Module-level singleton ──────────────────────────────────────────
# Mirrors clawteam.events.global_bus.get_event_bus().

_REGISTRY: PhaseRegistry | None = None


def get_registry() -> PhaseRegistry:
    """Return the process-global PhaseRegistry, lazily constructed."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PhaseRegistry()
    return _REGISTRY


def reset_registry() -> None:
    """Replace the global registry with a fresh instance. Test-only helper."""
    global _REGISTRY
    _REGISTRY = PhaseRegistry()
