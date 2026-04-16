"""Deny-filter helpers for scrubbing secrets from env snapshots and logs."""

from __future__ import annotations

import re
from typing import Mapping

_SECRET_KEY_RE = re.compile(
    r"(SECRET|TOKEN|KEY|PASSWORD|BEARER|CREDENTIAL|PASSWD|AUTH)",
    re.IGNORECASE,
)
_REDACTED = "[REDACTED]"


def scrub_env(env: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of *env* with values redacted when the key matches the deny regex.

    Keys are tested with ``re.search`` (case-insensitive). Values are replaced with a
    fixed placeholder; no attempt is made to partial-redact tokens embedded inside
    longer strings — callers that need value-level scrubbing should wrap this helper.

    The input mapping is never mutated. The return type is ``dict`` (not ``Mapping``)
    so callers can subsequently set ``CLAWTEAM_*`` / ``OH_*`` keys on the result.
    """
    return {k: (_REDACTED if _SECRET_KEY_RE.search(k) else v) for k, v in env.items()}
