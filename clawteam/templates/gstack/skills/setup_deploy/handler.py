"""/setup-deploy handler — writes ``[deploy]`` block into ``gstack.toml``.

The handler is the filesystem side of the /setup-deploy skill:

1. Resolve gstack.toml (``ctx.gstack_toml_path`` override preferred).
2. If an existing ``[deploy]`` block is present, call
   :func:`confirm_overwrite` — on ``no`` return with ``status="skipped"``
   and do NOT touch disk.
3. Run the wizard, collect answers, validate through ``DeployConfig``
   (pydantic — raises :class:`pydantic.ValidationError` on invalid
   provider/project; T-05-05-05).
4. Render the ``[deploy]`` block and splice into the existing content via
   a regex-based in-place replace (or append with blank-line separator
   when no block exists). All other TOML blocks are left byte-identical
   (T-05-05-03).
5. Atomically write the result (``atomic_write_text`` from Phase 2).
6. Round-trip the new content through ``tomllib.loads`` as a belt-and-
   suspenders guard against malformed output.

Tests monkeypatch :func:`run_wizard` + :func:`confirm_overwrite` so the
handler can be exercised without a TTY.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:  # pragma: no cover — clawteam supports 3.10+
    try:
        import tomllib  # type: ignore[import-not-found]
    except ModuleNotFoundError:
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]

from clawteam.fileutil import atomic_write_text
from clawteam.templates import DeployConfig
from clawteam.templates.gstack.skills.setup_deploy.wizard import (
    confirm_overwrite,
    run_wizard,
)

# Match the entire ``[deploy]`` block:
#
#   ^\[deploy\]\s*\n           header line
#   (?:(?!^\[).*\n?)*          any number of non-section lines
#
# The negative lookahead ``(?!^\[)`` bails as soon as the next section
# header starts, so we never devour subsequent blocks. ``(?ms)`` = multiline
# + dot-all so ``^`` matches line starts and ``.`` crosses newlines within
# matched lines.
_DEPLOY_BLOCK_RE = re.compile(
    r"(?ms)^\[deploy\]\s*\n(?:(?!^\[).*\n?)*",
)


def _find_gstack_toml(ctx: Any) -> Path:
    """Resolve the target ``gstack.toml`` path.

    Preference order:

    1. ``ctx.gstack_toml_path`` — explicit override (tests + CLI flag path).
    2. ``<ctx.workspace_dir>/gstack.toml`` — conventional workspace location.
    3. ``<ctx.workspace_dir>/clawteam/templates/gstack.toml`` — repo-root
       fallback when run from the clawteam checkout itself.
    """
    explicit = getattr(ctx, "gstack_toml_path", None)
    if explicit is not None:
        return Path(explicit)
    workspace = Path(getattr(ctx, "workspace_dir", "."))
    candidate = workspace / "gstack.toml"
    if candidate.exists():
        return candidate
    return workspace / "clawteam" / "templates" / "gstack.toml"


def _block_exists(content: str) -> bool:
    return bool(_DEPLOY_BLOCK_RE.search(content))


def _render_block(cfg: DeployConfig) -> str:
    """Render a validated :class:`DeployConfig` as a ``[deploy]`` TOML block."""
    lines = [
        "[deploy]",
        f'provider = "{cfg.provider}"',
        f'project = "{cfg.project}"',
    ]
    if cfg.custom_deploy_cmd:
        lines.append(f'custom_deploy_cmd = "{cfg.custom_deploy_cmd}"')
    return "\n".join(lines) + "\n"


def _insert_or_replace_block(content: str, new_block: str) -> str:
    """Replace existing ``[deploy]`` block in place, or append with separator.

    Appending uses a single blank-line separator (``\\n\\n``) when the source
    does not already end in a newline, otherwise just ``\\n``. The goal is to
    keep the surrounding content byte-identical (T-05-05-03).
    """
    if _block_exists(content):
        return _DEPLOY_BLOCK_RE.sub(new_block, content, count=1)
    sep = "\n" if content.endswith("\n") else "\n\n"
    return content + sep + new_block


def setup_deploy_handler(
    ctx: Any,
    *,
    role: str,
    args: dict[str, Any],
) -> dict[str, Any]:
    """/setup-deploy entry point — dispatched via :class:`SkillDispatcher`.

    ``args["_skip_confirm"]`` (bool, default False) bypasses the
    :func:`confirm_overwrite` prompt. This flag is used by tests and by a
    future ``clawteam setup-deploy --force`` CLI path; the normal
    agent-facing dispatch never sets it.
    """
    toml_path = _find_gstack_toml(ctx)
    if not toml_path.exists():
        raise FileNotFoundError(f"gstack.toml not found at {toml_path}")

    existing_content = toml_path.read_text(encoding="utf-8")
    skip_confirm = bool(args.get("_skip_confirm", False))

    if _block_exists(existing_content) and not skip_confirm:
        if not confirm_overwrite():
            return {
                "status": "skipped",
                "reason": "user declined overwrite",
                "gstack_toml": str(toml_path),
            }

    raw_cfg = run_wizard()
    # pydantic rejects invalid provider / empty project BEFORE we write — so
    # a bad wizard return leaves the file untouched (T-05-05-05).
    cfg = DeployConfig(**raw_cfg)

    new_block = _render_block(cfg)
    new_content = _insert_or_replace_block(existing_content, new_block)

    # Belt-and-suspenders: confirm the result parses before persisting.
    try:
        parsed = tomllib.loads(new_content)
    except tomllib.TOMLDecodeError as exc:
        raise RuntimeError(
            f"setup-deploy produced invalid TOML; refusing to write: {exc}"
        ) from exc
    assert parsed.get("deploy", {}).get("provider") == cfg.provider, (
        "rendered [deploy] block round-tripped to a different provider — "
        "indicates a bug in _render_block"
    )

    atomic_write_text(toml_path, new_content)

    return {
        "status": "written",
        "provider": cfg.provider,
        "project": cfg.project,
        "gstack_toml": str(toml_path),
    }
