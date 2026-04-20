"""Phase 2 structured errors — all subclass ValueError for MCP translate_error auto-wrap.

This module colocates Phase 2 error types so gate/CLI/Conductor code can import from
one place. Note: FrozenPathError lives in ``clawteam/harness/freeze_registry.py`` per
Plan 02-05 (colocated with the registry that raises it); MalformedEnvelopeError lives
in ``clawteam/team/envelope.py`` per Plan 02-02 (colocated with the model that
validates). Future plans (02-07, 02-11, 02-12) add AmbiguousSprintError,
SprintNotFoundError, MissingTeamError here as they land.

Every error in this module is a ``ValueError`` subclass so that
``clawteam/mcp/helpers.py::translate_error`` automatically wraps them into
structured MCP error envelopes without per-error dispatch code.
"""

from __future__ import annotations


class ArtifactTooLargeError(ValueError):
    """Raised by ``ArtifactStore.write()`` when content exceeds the per-file cap.

    Reference: §02-CONTEXT D-27 (per-file artifact cap) and SC#9.

    Message shape (see ``ArtifactStore.write`` in ``clawteam/harness/artifacts.py``):

        {name}: {size_bytes} bytes exceeds per-file cap of {cap_bytes} bytes.
        Suggestion: split into {name_stem}-part1{ext} etc. or raise cap via
        --artifact-cap

    The structured message includes ``artifact_name``, ``size_bytes``, ``cap_bytes``,
    and a concrete remediation suggestion so agents and humans see exactly what to
    do (§02-CONTEXT D-27 shape). Plan 02-12's CLI error dispatch displays the
    message verbatim; translate_error surfaces it through MCP as a structured
    ``artifact_too_large`` envelope.
    """
