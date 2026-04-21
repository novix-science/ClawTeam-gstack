"""Native CLI invocation wrapper (Phase 5 Wave 0 substrate, §05-RESEARCH §A1).

:class:`clawteam.spawn.adapters.NativeCliAdapter` exposes only
:meth:`~NativeCliAdapter.prepare_command` — it does NOT run ``subprocess``
nor scrub env vars. This module provides the missing :func:`invoke_native_cli`
wrapper so Phase 5 skill handlers (``/codex``, ``/ship``, ``/land-and-deploy``,
``/canary``, ``/benchmark``, ``/rollback``, ``/sre-review``) have ONE call
site with uniform guarantees:

- ``shell=False`` is HARD-CODED (D-15, T-05-01-02 adversarial-input protection).
- Default ``env`` is :func:`clawteam.secrets.scrub_env` applied to
  ``os.environ`` so secret-shaped keys cannot leak into spawned CLIs
  (T-05-01-03).
- ``TimeoutExpired`` / ``CalledProcessError`` / ``FileNotFoundError``
  propagate unchanged; the wrapper does NOT swallow exceptions.

Callers who need to pass an explicit env dict (e.g. provider auth tokens that
must reach the subprocess) supply ``env=<dict>``; the wrapper then uses that
dict verbatim — scrub_env is the default, not a required preprocessor.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

from clawteam.secrets import scrub_env
from clawteam.spawn.adapters import NativeCliAdapter

_ADAPTER = NativeCliAdapter()


def invoke_native_cli(
    command: Sequence[str],
    *,
    cwd: str | Path | None = None,
    prompt: str | None = None,
    timeout: float = 120.0,
    env: Mapping[str, str] | None = None,
    skip_permissions: bool = False,
    interactive: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Prepare a command via :class:`NativeCliAdapter` and run it with safe defaults.

    Parameters
    ----------
    command:
        Argv sequence, e.g. ``["gh", "pr", "list", "--json", "number"]``.
    cwd:
        Working directory for the subprocess. ``None`` inherits the caller's cwd.
    prompt:
        Optional prompt passed through :meth:`NativeCliAdapter.prepare_command`
        (relevant for codex/claude/kimi — Phase 5 skill handlers generally
        leave this ``None``).
    timeout:
        Seconds; raises :class:`subprocess.TimeoutExpired` when exceeded.
    env:
        When provided, used verbatim as the subprocess env (scrub_env NOT
        applied). When ``None`` (the default), ``scrub_env(os.environ)`` is
        used so secret-shaped keys do not leak.
    skip_permissions, interactive:
        Forwarded to :meth:`NativeCliAdapter.prepare_command`.

    Returns
    -------
    subprocess.CompletedProcess[str]
        ``stdout``/``stderr`` are strings (``text=True``);
        ``returncode`` reflects the child exit (``check=False``).
    """
    prepared = _ADAPTER.prepare_command(
        list(command),
        prompt=prompt,
        cwd=str(cwd) if cwd is not None else None,
        skip_permissions=skip_permissions,
        interactive=interactive,
    )
    effective_env = dict(env) if env is not None else scrub_env(os.environ)
    return subprocess.run(
        prepared.final_command,
        cwd=str(cwd) if cwd is not None else None,
        env=effective_env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        shell=False,
    )
