"""Shared YAML scalar-quoting helper for Phase 5 hand-rolled frontmatter emitters.

The four Phase 5 Wave 1 handlers (``/ship``, ``/land-and-deploy``, ``/canary``,
``/benchmark``) each hand-roll a YAML-ish frontmatter emitter so the harness
stays pyyaml-free. Before this helper existed, each emitter serialized string
values via Python's :func:`repr`, which produces Python string literals — NOT
valid YAML. Embedded single quotes, newlines, or backslashes made the output
subtly wrong when parsed by a standards-compliant reader (e.g. PyYAML used by
downstream EvidenceGate consumers).

:func:`yaml_quote_string` produces a valid YAML 1.2 single-quoted scalar
(§7.4.2) in the common case, and JSON-encodes the value (a valid YAML flow
scalar) when the string contains a newline so multi-line payloads stay on one
frontmatter line while remaining round-trip-safe with both our hand-rolled
parser and any strict YAML reader.

The :mod:`clawteam.templates.gstack.skills.codex.handler` module ships the
same single-quote-doubling pattern inline; this helper extracts it so future
emitters (and the Phase 5 Wave 1 four) share exactly one implementation.
"""

from __future__ import annotations

import json


def yaml_quote_string(val: str) -> str:
    """Return ``val`` formatted as a safe YAML scalar.

    Rules
    -----
    * If ``val`` contains a newline or carriage return, the result is a
      JSON-encoded string (e.g. ``"a\\nb"``). A JSON string literal is a valid
      YAML flow scalar, so this stays on a single frontmatter line while
      round-tripping correctly through any YAML 1.2 reader.
    * Otherwise, the result is a YAML single-quoted scalar with embedded
      ``'`` characters doubled per YAML 1.2 §7.4.2 — e.g. ``it's`` becomes
      ``'it''s'``.

    Parameters
    ----------
    val:
        String value to quote. Must be a :class:`str`; pass non-strings
        through ``str()`` at the call site first (the emitters already do
        this implicitly — only ``isinstance(val, str)`` branches reach here).

    Returns
    -------
    str
        Quoted YAML scalar, ready to interpolate after ``"key: "``.
    """
    if "\n" in val or "\r" in val:
        # JSON string literal is a valid YAML flow scalar (double-quoted form).
        return json.dumps(val)
    escaped = val.replace("'", "''")
    return f"'{escaped}'"
