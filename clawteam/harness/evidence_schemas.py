"""Evidence-schema registry — plugin-populated frontmatter schemas keyed by artifact_type.

Structural twin of ``clawteam.harness.phase_registry.PhaseRegistry`` (§02-CONTEXT
lesson #3: ``FreezeRegistry`` mirrors ``PhaseRegistry``'s shape — the same
lesson applies here).

Phase 2 ships the registry + the ``ArtifactFrontmatterBase`` pydantic base class.
Phase 3's ``GstackSprintPlugin.contribute_evidence_schemas()`` will register the
six gstack artifact subclasses (``DesignDoc`` / ``PlanDoc`` / ``TestReport`` /
``ReviewReport`` / ``ShipNotes`` / ``Retro``). This module intentionally ships
no concrete subclasses — that is Phase 3 scope per §02-CONTEXT deferred items.

Consumers:
    * ``clawteam.plugins.manager._instantiate_and_register`` (Plan 02-01): calls
      :func:`register_schema` for each entry returned by
      ``HarnessPlugin.contribute_evidence_schemas``. Wave-1 shipped the call
      site behind a lazy ``ModuleNotFoundError`` guard; with this module in
      place the guarded path becomes live end-to-end.
    * ``clawteam.harness.evidence_gate.EvidenceGate.check`` (Plan 02-07): calls
      :func:`get_schema` with ``meta['artifact_type']`` to dispatch per-artifact
      pydantic validation.

Per §02-CONTEXT D-02 and D-03 + §02-RESEARCH Pitfall #6: an unregistered
``artifact_type`` returns ``None`` from :func:`get_schema` — the caller MUST
distinguish this from a pydantic validation failure. Plan 02-07's gate emits
``"Unregistered artifact_type 'x'. Phase 3 plugin must register."`` on ``None``.

Field shape of :class:`ArtifactFrontmatterBase` matches
``clawteam.team.envelope.TurnEnvelope`` deliberately (§02-CONTEXT lesson #2:
"one pydantic model, two serialization surfaces" — one surface is the
TeamMessage envelope; the other is durable-artifact YAML frontmatter).
"""

from __future__ import annotations

from pydantic import BaseModel


class ArtifactFrontmatterBase(BaseModel):
    """Base pydantic model for durable-artifact YAML frontmatter.

    All five fields are required — Plan 02-07's :class:`EvidenceGate` asserts
    they are populated before running the 4-check protocol; an agent that
    writes an artifact without these fields fails the gate with a structured
    error (no silent pass).

    Phase 3 concrete subclasses (``DesignDoc`` / ``PlanDoc`` / ``TestReport`` /
    ``ReviewReport`` / ``ShipNotes`` / ``Retro``) add artifact-specific required
    fields and section lists (e.g. ``DesignDoc.forcing_questions``,
    ``ShipNotes.deploy_url``). Those subclasses override ``artifact_type`` with
    a ``Literal[...]`` default so the value is stable across instances and
    usable as a pydantic v2 discriminator key in §02-RESEARCH Pattern 1.
    """

    persona: str
    step_label: str
    done: bool
    artifact_type: str
    created_at: str


# Module-level singleton dict; populated at plugin load time.
# Mirrors ``clawteam.harness.phase_registry._REGISTRY`` in lifecycle shape:
# tests call :func:`reset_registry` in setup / teardown to isolate runs.
_REGISTERED: dict[str, type[ArtifactFrontmatterBase]] = {}


def register_schema(name: str, cls: type[ArtifactFrontmatterBase]) -> None:
    """Register a pydantic subclass of :class:`ArtifactFrontmatterBase` under ``name``.

    Raises :class:`ValueError` on duplicate ``name`` — §02-CONTEXT D-03, parallel
    to ``PhaseRegistry``'s duplicate-phase rule (see
    ``clawteam/harness/phase_registry.py``). The collision message names both
    the existing and the attempted class so Phase 3's ``GstackSprintPlugin``
    debugging is trivial if two plugins accidentally double-register the same
    artifact_type.
    """
    if name in _REGISTERED:
        raise ValueError(
            f"Duplicate evidence-schema registration: {name!r} "
            f"(existing: {_REGISTERED[name].__name__}, new: {cls.__name__})"
        )
    _REGISTERED[name] = cls


def get_schema(artifact_type: str) -> type[ArtifactFrontmatterBase] | None:
    """Return the registered pydantic class for ``artifact_type``, or ``None``.

    ``None`` means "no plugin registered this artifact_type"; this is NOT the
    same as a pydantic ``ValidationError`` — the caller MUST distinguish the
    two cases per §02-RESEARCH Pitfall #6. Plan 02-07's
    :class:`~clawteam.harness.evidence_gate.EvidenceGate` surfaces these as
    different gate-reason strings for operator debuggability.
    """
    return _REGISTERED.get(artifact_type)


def list_registered() -> list[str]:
    """Return the sorted list of registered ``artifact_type`` names (diagnostics)."""
    return sorted(_REGISTERED.keys())


def reset_registry() -> None:
    """Clear all registered schemas — TEST-ONLY helper for isolation.

    Tests MUST call this in ``setup_function`` / ``teardown_function``; mirrors
    the ``clawteam.harness.phase_registry.reset_registry`` convention so a
    single habit covers both registries in the Phase 1 / Phase 2 harness code.
    """
    _REGISTERED.clear()
