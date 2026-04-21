"""Questionary-backed interactive wizard for /setup-deploy (SKILL-19).

Pure UI + validation module. Handler.py owns all filesystem side-effects —
keeping the wizard pure lets the tests feed canned answers without touching
disk.

Validation is the deepest defensive layer for D-15 adversarial input:

- ``validate_project_slug`` — accepts only ``[a-zA-Z0-9_-]+``. Rejects shell
  metachars, path separators, whitespace, and empty input. (T-05-05-01.)
- ``validate_custom_cmd`` — rejects any of ``; | & $ backtick < > \\ \\n``
  in the custom deploy command string. (T-05-05-02.)
"""

from __future__ import annotations

import re
from typing import Any

# Project slug: alphanumeric + _ and -.
_PROJECT_SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]+$")

# Shell metacharacter deny-list for custom_deploy_cmd. Defense-in-depth:
# the command is always invoked via invoke_native_cli (shell=False) so even
# if a char slips through, argv is not shell-interpreted. This validator is
# an up-front "fail loudly" guard so users see the problem at prompt time.
_SHELL_METACHARS = frozenset(
    (";", "|", "&", "`", "$", "<", ">", "\\", "\n")
)


def validate_project_slug(value: Any) -> bool:
    """Accept only ``[a-zA-Z0-9_-]+``; reject empty, None, and any metachar.

    Used both as a questionary ``validate=`` hook and as a direct handler
    guard so invalid values never reach the TOML write layer.
    """
    if not isinstance(value, str) or not value:
        return False
    return bool(_PROJECT_SLUG_RE.fullmatch(value))


def validate_custom_cmd(value: Any) -> bool:
    """Reject shell metachars in a custom deploy command.

    Empty string and ``None`` are accepted (the provider may not need a
    command — the handler's pydantic model separately enforces that
    ``provider == 'custom'`` pairs with a non-empty command).
    """
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    if value == "":
        return True
    return not any(ch in _SHELL_METACHARS for ch in value)


def _load_questionary() -> Any:
    """Lazy-import questionary (mirrors clawteam/cli/commands.py:173 pattern).

    Tests monkeypatch this function to return a mock object that implements
    ``.select`` / ``.text`` / ``.confirm``.
    """
    try:
        import questionary  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover — questionary is a hard dep
        raise RuntimeError(
            "questionary is required for /setup-deploy but is missing; "
            "install with: pip install 'questionary>=2.0.1,<3.0.0'"
        ) from exc
    return questionary


def run_wizard() -> dict[str, Any]:
    """Run the /setup-deploy wizard; return dict ready for ``DeployConfig(**r)``.

    Prompts in order:

    1. provider — ``select`` from ``{vercel, netlify, fly, custom}``.
    2. project — ``text`` validated via :func:`validate_project_slug`.
    3. custom_deploy_cmd — ``text`` shown ONLY when provider == ``custom``,
       validated via :func:`validate_custom_cmd`.

    Raises
    ------
    KeyboardInterrupt
        When the user cancels any prompt (questionary's ``.ask()`` returns
        ``None`` in that case). Surfacing it lets the dispatcher layer fall
        back to a clean "wizard aborted" path instead of writing garbage.
    """
    questionary = _load_questionary()

    provider = questionary.select(
        "Which deploy provider?",
        choices=["vercel", "netlify", "fly", "custom"],
    ).ask()
    if provider is None:
        raise KeyboardInterrupt

    project = questionary.text(
        "Project slug (alphanumeric + dash/underscore only):",
        validate=lambda s: validate_project_slug(s)
        or "Invalid: must match ^[a-zA-Z0-9_-]+$",
    ).ask()
    if project is None:
        raise KeyboardInterrupt

    custom_cmd = ""
    if provider == "custom":
        custom_cmd = questionary.text(
            "Custom deploy command (no shell metachars — "
            "; | & ` $ < > \\ newline):",
            validate=lambda s: validate_custom_cmd(s)
            or "Invalid: contains shell metachars",
        ).ask()
        if custom_cmd is None:
            raise KeyboardInterrupt

    return {
        "provider": provider,
        "project": project,
        "custom_deploy_cmd": custom_cmd,
    }


def confirm_overwrite() -> bool:
    """Yes/no prompt for idempotent re-run when a ``[deploy]`` block exists.

    Defaults to ``False`` so an accidental re-invoke does NOT clobber the
    current config. Tests monkeypatch this function directly to bypass the
    questionary round-trip.
    """
    questionary = _load_questionary()
    answer = questionary.confirm(
        "An existing [deploy] block was found. Overwrite it?",
        default=False,
    ).ask()
    return bool(answer)
