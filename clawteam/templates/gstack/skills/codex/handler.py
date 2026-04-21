"""/codex skill handler (SKILL-13, D-01 sub-package shape).

Three modes — review (pass/fail gate), adversarial (red-team critique),
consultation (open-ended design Q) — dispatched through ``SkillDispatcher``
with ``roles={engineer, reviewer}``.

All external CLI invocation goes through :func:`invoke_native_cli` (Wave 0
wrapper) so env scrubbing + ``shell=False`` + timeout are enforced uniformly
(T-05-03-01 / T-05-03-02 mitigations). The handler itself never calls
``subprocess.run`` directly.

Output: ``codex-review.md`` atomic-written under the sprint directory with a
:class:`CodexReview`-conformant frontmatter block. ``verdict`` is a
pass/fail/n-a heuristic over the CLI's first line of stdout, and is always
``n/a`` for modes other than ``review``.
"""
from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from clawteam.fileutil import atomic_write_text
from clawteam.plugins.skill_errors import SkillUnavailable
from clawteam.spawn.invoke import invoke_native_cli
from clawteam.templates.gstack.schemas.codex_review import CodexReview

CodexMode = Literal["review", "adversarial", "consultation"]
_VALID_MODES: frozenset[str] = frozenset({"review", "adversarial", "consultation"})
_INSTALL_HINT: str = "npm install -g @openai/codex"
_CODEX_TIMEOUT: float = 600.0  # 10 min — codex can be slow on long files.


def tool_available() -> bool:
    """Return ``True`` iff the ``codex`` CLI is on ``PATH``.

    Used by :class:`SkillDispatcher` as the tool-availability probe — when
    ``False``, dispatch raises :class:`SkillUnavailable` BEFORE invoking the
    handler.
    """
    return shutil.which("codex") is not None


def invoke_codex(
    prompt: str,
    *,
    mode: CodexMode,
    cwd: str | Path,
    timeout: float = _CODEX_TIMEOUT,
) -> str:
    """Invoke the codex CLI via :func:`invoke_native_cli`; return stdout.

    Parameters
    ----------
    prompt:
        Full text sent to ``codex exec``. Passed through the ``prompt`` kwarg
        so ``NativeCliAdapter`` appends it as a SINGLE positional argument —
        never shell-interpolated (T-05-03-01).
    mode:
        Kept on the function signature for future mode-specific prompt
        prefixing; the current codex CLI has no mode flag, so this is only
        used by the caller to tag the output artifact.
    cwd:
        Working directory for the codex subprocess.
    timeout:
        Seconds; :class:`subprocess.TimeoutExpired` propagates unchanged.

    Raises
    ------
    SkillUnavailable
        When :func:`tool_available` returns ``False``.
    """
    if not tool_available():
        raise SkillUnavailable(
            skill="/codex",
            binary="codex",
            install_hint=_INSTALL_HINT,
        )
    # ``mode`` is intentionally unused as a CLI flag — codex CLI doesn't accept
    # one today; the mode is recorded in the artifact frontmatter.
    _ = mode
    result = invoke_native_cli(
        command=["codex", "exec"],
        prompt=prompt,
        cwd=cwd,
        timeout=timeout,
        skip_permissions=True,
        interactive=False,
    )
    return result.stdout


def _frontmatter_yaml(schema: CodexReview) -> str:
    """Serialize a :class:`CodexReview` as YAML frontmatter + empty body.

    Uses a hand-rolled emitter to avoid a pyyaml dependency (matches the
    Phase 3 / Phase 5 Wave 1 schema-emit convention). Strings are quoted with
    ``repr`` so embedded quotes/newlines are escaped in a Python-safe way that
    also parses as YAML (our frontmatter parser is likewise hand-rolled).
    """
    d = schema.model_dump()
    lines = ["---"]
    for key in (
        "artifact_type",
        "mode",
        "target",
        "verdict",
        "summary",
        "sprint_id",
        "created_at",
        "persona",
        "step_label",
        "done",
    ):
        val = d[key]
        if isinstance(val, bool):
            lines.append(f"{key}: {str(val).lower()}")
        elif isinstance(val, str):
            # Use single-quoted repr-style — parseable by our test frontmatter
            # reader and survives embedded punctuation.
            escaped = val.replace("'", "''")
            lines.append(f"{key}: '{escaped}'")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + "\n"


def _derive_verdict(mode: str, stdout: str) -> Literal["pass", "fail", "n/a"]:
    """Heuristic verdict for 'review' mode; 'n/a' for all other modes.

    Inspects the first non-empty line of ``stdout`` for common pass/fail
    markers. Adversarial/consultation modes always return ``"n/a"`` because
    their output is a critique/design-discussion rather than a gate verdict.
    """
    if mode != "review":
        return "n/a"
    first_line = ""
    for line in stdout.splitlines():
        if line.strip():
            first_line = line.strip().lower()
            break
    if any(kw in first_line for kw in ("lgtm", "pass", "approved", "approve")):
        return "pass"
    if any(kw in first_line for kw in ("fail", "reject", "block")):
        return "fail"
    return "n/a"


def codex_handler(ctx: Any, *, role: str, args: dict[str, Any]) -> dict[str, Any]:
    """Entry point invoked by :class:`SkillDispatcher`.

    Expected ``args`` keys:
        mode: one of ``"review" | "adversarial" | "consultation"`` (required)
        target: short label — file path, diff range, or prompt subject (required)
        prompt: full text sent to ``codex exec`` (required)

    ``ctx`` must expose:
        sprint_dir: Path — directory to write the artifact
        sprint_id: str

    Returns
    -------
    dict
        ``{"artifact_path": str, "mode": str, "stdout": str}``

    Raises
    ------
    ValueError
        When ``mode`` is not a valid :data:`CodexMode` or ``target`` is empty.
        Raised BEFORE invoking the CLI — cheap-fail for cheap-to-detect errors.
    SkillUnavailable
        When the codex binary is not on ``PATH``. Raised by
        :func:`invoke_codex` BEFORE any artifact is written so no stale
        ``codex-review.md`` appears in the sprint directory.
    """
    mode = args.get("mode")
    target = args.get("target", "")
    prompt = args.get("prompt", "")
    if mode not in _VALID_MODES:
        raise ValueError(
            f"codex: invalid mode {mode!r} (must be one of {sorted(_VALID_MODES)})"
        )
    if not target:
        raise ValueError("codex: 'target' arg is required")

    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))

    # invoke_codex raises SkillUnavailable if codex is missing — happens BEFORE
    # any file write, so no partial artifact is left behind (T-05-03-01 note).
    stdout = invoke_codex(prompt, mode=mode, cwd=sprint_dir)

    verdict = _derive_verdict(mode, stdout)
    # Keep summary bounded — first 500 chars of stdout. Trust-boundary note
    # (T-05-03-04 accept): summary contents are agent-display-only; downstream
    # gates do not execute stored markdown.
    summary = stdout.strip()[:500]

    created_at = datetime.now(timezone.utc).isoformat()
    schema = CodexReview(
        artifact_type="codex-review",
        mode=mode,
        target=target,
        verdict=verdict,
        summary=summary,
        sprint_id=getattr(ctx, "sprint_id", ""),
        created_at=created_at,
        persona=role,
    )

    sprint_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = sprint_dir / "codex-review.md"
    atomic_write_text(artifact_path, _frontmatter_yaml(schema))

    return {
        "artifact_path": str(artifact_path),
        "mode": mode,
        "stdout": stdout,
    }
