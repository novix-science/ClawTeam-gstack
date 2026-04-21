"""/land-and-deploy handler (SKILL-15, Plan 05-06).

Entry point for the shipper's merged-PR deploy action. Runs a four-phase
pipeline and always produces a ``deploy.md`` artifact so EvidenceGate can
surface the outcome regardless of which step failed:

1. Precondition: read ``ship-notes.md`` frontmatter; require
   ``ship_status == 'succeeded'``. Raise
   :class:`~clawteam.plugins.skill_errors.SkillPreconditionError` with the
   hint ``Run /ship first`` when missing or failed (D-12).
2. CI wait: invoke ``gh pr checks --watch <pr_url>`` with
   ``ci_wait_timeout_seconds`` (default 1800) via
   :func:`clawteam.spawn.invoke.invoke_native_cli` (shell=False, T-05-06-01).
   On ``subprocess.TimeoutExpired`` or non-zero exit, write deploy.md with
   ``deploy_status='failed'`` and return.
3. Deploy: dispatch per ``gstack.toml [deploy].provider``:

   * ``vercel``   → ``["vercel", "deploy", "--prod", "--yes"]``
   * ``netlify``  → ``["netlify", "deploy", "--prod"]``
   * ``fly``      → ``["flyctl", "deploy", "--app", <project>]``
   * ``custom``   → ``shlex.split(custom_deploy_cmd)`` (shell-metachar safe
     because ``invoke_native_cli`` hard-codes ``shell=False``; T-05-06-01).

   When no ``[deploy]`` block is configured, write deploy.md with
   ``deploy_status='pending'`` + emit a question artifact prompting the user
   to run ``/setup-deploy`` first.
4. Health probe: extract the first ``https?://...`` URL from deploy stdout
   and HEAD-probe it with exponential backoff up to
   ``deploy_verify_timeout_seconds`` (default 120). This is Pitfall 3's
   mitigation — the handler's own poll precedes EvidenceGate's 10 s HEAD so
   slow-CDN warm-ups don't false-fail the gate (T-05-06-04).
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.fileutil import atomic_write_text
from clawteam.plugins.skill_errors import SkillPreconditionError
from clawteam.spawn.invoke import invoke_native_cli
from clawteam.templates.gstack.schemas.deploy_notes import DeployNotes

_DEFAULT_CI_WAIT: int = 1800  # seconds (30 min)
_DEFAULT_DEPLOY_VERIFY: int = 120  # seconds
_DEPLOY_CMD_TIMEOUT: int = 600  # seconds — outer timeout for deploy CLI itself
_GIT_SHA_TIMEOUT: int = 10

_URL_RE = re.compile(r"https?://[^\s]+")
_SUPPORTED_PROVIDERS: frozenset[str] = frozenset(
    {"vercel", "netlify", "fly", "custom"}
)


# ── Frontmatter helpers ────────────────────────────────────────────────────


def _parse_simple_frontmatter(text: str) -> dict[str, Any]:
    """Parse a ``---...---`` YAML block at the top of ``text``.

    Keeps parser minimal (no external PyYAML dep) — supports str/bool/null/
    inline JSON list+dict values. Matches the writer used here and by
    :mod:`clawteam.templates.gstack.skills.ship.handler` so round-trips
    preserve the handful of fields we need (``ship_status`` + ``pr_url``).
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm_block = text[3:end].lstrip("\n")
    out: dict[str, Any] = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        # Strip surrounding single or double quotes
        if (
            len(val) >= 2
            and val[0] == val[-1]
            and val[0] in ("'", '"')
        ):
            val = val[1:-1]
        # Type coercion
        if val == "true":
            out[key] = True
        elif val == "false":
            out[key] = False
        elif val == "null":
            out[key] = None
        elif val.startswith(("[", "{")):
            try:
                out[key] = json.loads(val)
            except json.JSONDecodeError:
                out[key] = val
        else:
            out[key] = val
    return out


def _read_ship_notes(sprint_dir: Path) -> dict[str, Any]:
    """Read ship-notes.md frontmatter; raise SkillPreconditionError when invalid.

    Precondition for /land-and-deploy (D-12): the same sprint_dir must contain
    a ship-notes.md with ``ship_status == 'succeeded'``. Any deviation — file
    missing, malformed frontmatter, or non-succeeded status — is a blocking
    precondition failure.
    """
    path = sprint_dir / "ship-notes.md"
    if not path.exists():
        raise SkillPreconditionError(
            skill="/land-and-deploy",
            role="shipper",
            message="Run /ship first (ship-notes.md not found)",
        )
    text = path.read_text(encoding="utf-8")
    fm = _parse_simple_frontmatter(text)
    if not fm:
        raise SkillPreconditionError(
            skill="/land-and-deploy",
            role="shipper",
            message=(
                "ship-notes.md has no frontmatter — Run /ship first "
                "to write a valid ship-notes.md"
            ),
        )
    status = fm.get("ship_status")
    if status != "succeeded":
        raise SkillPreconditionError(
            skill="/land-and-deploy",
            role="shipper",
            message=(
                f"ship-notes.md has ship_status={status!r}; "
                "Run /ship successfully first"
            ),
        )
    return fm


# ── Health-probe helpers ───────────────────────────────────────────────────


def _head_probe(url: str, timeout: float = 10.0) -> bool:
    """Return ``True`` iff a HEAD request to ``url`` returns a 2xx or 3xx status.

    All network exceptions (URLError / HTTPError / socket timeouts / OSError)
    are swallowed and reported as ``False``. Tests monkeypatch this helper
    to avoid real network traffic.
    """
    try:
        req = urllib.request.Request(url, method="HEAD")  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return 200 <= resp.status < 400
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return False


def _wait_for_health(url: str, max_seconds: int) -> bool:
    """Poll ``url`` with exponential backoff up to ``max_seconds``.

    Returns ``True`` on the first 2xx/3xx response, ``False`` when the
    deadline expires. Pitfall 3 closure: EvidenceGate's 10 s HEAD fires
    AFTER we have already confirmed health, avoiding false-fails on slow
    CDN warm-up.
    """
    if not url:
        return False
    deadline = time.monotonic() + max_seconds
    delay = 2.0
    # Try once up-front so tests with short timeouts still get at least one probe.
    if _head_probe(url):
        return True
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        sleep_for = min(delay, max(0.1, remaining))
        time.sleep(sleep_for)
        if _head_probe(url):
            return True
        delay = min(delay * 1.5, 15.0)
    return False


def _extract_deploy_url(stdout: str) -> str:
    """Return the first ``https?://...`` substring found in ``stdout``, else ''."""
    match = _URL_RE.search(stdout or "")
    return match.group(0) if match else ""


# ── Deploy-command builder ─────────────────────────────────────────────────


def _build_deploy_cmd(
    provider: str, project: str, custom_cmd: str,
) -> list[str]:
    """Return argv for the configured provider; empty list signals a config error.

    ``shlex.split`` runs in POSIX mode so shell metacharacters in
    ``custom_deploy_cmd`` become literal argv elements (T-05-06-01). This is
    a second-layer defense after the /setup-deploy wizard's deny-list; even
    if the wizard failed open, ``invoke_native_cli``'s hard-coded
    ``shell=False`` prevents shell interpretation.
    """
    if provider == "vercel":
        return ["vercel", "deploy", "--prod", "--yes"]
    if provider == "netlify":
        return ["netlify", "deploy", "--prod"]
    if provider == "fly":
        return ["flyctl", "deploy", "--app", project]
    if provider == "custom":
        return shlex.split(custom_cmd) if custom_cmd else []
    # Unknown provider → empty list; caller writes deploy_status='failed'.
    return []


# ── Git + question-artifact helpers ────────────────────────────────────────


def _current_commit_sha(cwd: Path) -> str:
    """Best-effort ``git rev-parse HEAD`` read; returns '' on any failure.

    The resulting SHA is stored in DeployNotes.commit_sha; on failure we
    fall back to a 7-char placeholder so the pydantic min_length=7 holds.
    """
    try:
        result = invoke_native_cli(
            ["git", "rev-parse", "HEAD"], cwd=cwd, timeout=_GIT_SHA_TIMEOUT,
        )
        if result.returncode == 0:
            return (result.stdout or "").strip()
    except Exception:  # noqa: BLE001 — best-effort
        pass
    return ""


def _emit_question_run_setup(sprint_dir: Path) -> None:
    """Write a sprint-level blocking question prompting the user to run /setup-deploy."""
    q_dir = sprint_dir / "questions"
    q_dir.mkdir(parents=True, exist_ok=True)
    (q_dir / "001_run_setup_deploy.md").write_text(
        "---\n"
        "question_id: '001'\n"
        "priority: 'blocking'\n"
        "---\n\n"
        "### Run /setup-deploy\n\n"
        "gstack.toml has no [deploy] block. Please run /setup-deploy "
        "(sre role) to configure the deploy provider before re-running "
        "/land-and-deploy.\n",
        encoding="utf-8",
    )


# ── DeployNotes writer ─────────────────────────────────────────────────────


def _render_deploy_notes_yaml(schema: DeployNotes) -> str:
    """Serialize a :class:`DeployNotes` instance to ``---`` frontmatter text.

    Mirrors the hand-rolled YAML emitter in the /ship handler so the Phase 5
    skills stay consistent without a pyyaml dep.
    """
    data = schema.model_dump()
    lines: list[str] = ["---"]
    for key, val in data.items():
        if isinstance(val, bool):
            lines.append(f"{key}: {str(val).lower()}")
        elif isinstance(val, (list, dict)):
            lines.append(f"{key}: {json.dumps(val)}")
        elif val is None:
            lines.append(f"{key}: null")
        elif isinstance(val, str):
            lines.append(f"{key}: {val!r}")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines) + "\n"


def _write_deploy_notes(
    sprint_dir: Path,
    *,
    sprint_id: str,
    deploy_status: str,
    deploy_url: str,
    provider: str,
    commit_sha: str,
) -> Path:
    """Atomic-write ``<sprint_dir>/deploy.md`` with a validated DeployNotes block."""
    # Coerce provider to the Literal enum domain; unknown providers fall to 'custom'.
    coerced_provider = provider if provider in _SUPPORTED_PROVIDERS else "custom"
    # pydantic requires commit_sha min_length=7 + deploy_url min_length=1.
    if not commit_sha:
        commit_sha = "0000000"
    if not deploy_url:
        deploy_url = "pending"
    now_iso = datetime.now(timezone.utc).isoformat()
    schema = DeployNotes(
        artifact_type="deploy-notes",
        deploy_status=deploy_status,  # type: ignore[arg-type]
        deploy_url=deploy_url,
        provider=coerced_provider,  # type: ignore[arg-type]
        deployed_at=now_iso,
        commit_sha=commit_sha,
        sprint_id=sprint_id,
        created_at=now_iso,
    )
    sprint_dir.mkdir(parents=True, exist_ok=True)
    artifact = sprint_dir / "deploy.md"
    atomic_write_text(artifact, _render_deploy_notes_yaml(schema))
    return artifact


# ── Handler entry point ────────────────────────────────────────────────────


def land_and_deploy_handler(
    ctx: Any, *, role: str, args: dict[str, Any],
) -> dict[str, Any]:
    """Entry point registered via :class:`SkillRegistration(name='/land-and-deploy')`.

    Parameters
    ----------
    ctx:
        Harness context. Read attributes (all optional): ``sprint_dir``,
        ``sprint_id``, ``workspace_dir``, ``template`` / ``tmpl`` (carries
        ``.deploy`` + ``.canary`` sub-configs).
    role:
        Caller's role. Role gating is enforced upstream by
        :class:`SkillDispatcher`; the handler is still safe to call directly
        in tests.
    args:
        Optional overrides. Supported:

        * ``deploy_verify_timeout_seconds`` (int): HEAD-probe deadline
          override (default 120).
    """
    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    sprint_id = getattr(ctx, "sprint_id", "")
    cwd = Path(getattr(ctx, "workspace_dir", sprint_dir))

    # 1. Precondition — ship-notes.md with ship_status='succeeded'.
    ship_fm = _read_ship_notes(sprint_dir)
    pr_url = str(ship_fm.get("pr_url") or "")

    tmpl = getattr(ctx, "template", None) or getattr(ctx, "tmpl", None)
    deploy_cfg = getattr(tmpl, "deploy", None) if tmpl is not None else None
    canary_cfg = getattr(tmpl, "canary", None) if tmpl is not None else None
    ci_timeout = int(
        getattr(canary_cfg, "ci_wait_timeout_seconds", _DEFAULT_CI_WAIT)
        if canary_cfg is not None
        else _DEFAULT_CI_WAIT
    )
    verify_timeout = int(
        args.get("deploy_verify_timeout_seconds", _DEFAULT_DEPLOY_VERIFY)
    )
    commit_sha = _current_commit_sha(cwd)

    # 2. No [deploy] block → pending + question artifact.
    if deploy_cfg is None:
        _emit_question_run_setup(sprint_dir)
        artifact = _write_deploy_notes(
            sprint_dir,
            sprint_id=sprint_id,
            deploy_status="pending",
            deploy_url="pending",
            provider="custom",
            commit_sha=commit_sha,
        )
        return {
            "artifact_path": str(artifact),
            "deploy_status": "pending",
            "reason": "no_deploy_block",
        }

    provider = getattr(deploy_cfg, "provider", "custom")
    project = getattr(deploy_cfg, "project", "")
    custom_cmd = getattr(deploy_cfg, "custom_deploy_cmd", "") or ""

    # 3. CI wait — gh pr checks --watch with configured timeout (T-05-06-03).
    if pr_url:
        try:
            ci_result = invoke_native_cli(
                ["gh", "pr", "checks", "--watch", pr_url],
                cwd=cwd,
                timeout=ci_timeout,
            )
            if ci_result.returncode != 0:
                artifact = _write_deploy_notes(
                    sprint_dir,
                    sprint_id=sprint_id,
                    deploy_status="failed",
                    deploy_url="pending",
                    provider=provider,
                    commit_sha=commit_sha,
                )
                return {
                    "artifact_path": str(artifact),
                    "deploy_status": "failed",
                    "failure_step": "ci",
                    "exit_code": ci_result.returncode,
                }
        except subprocess.TimeoutExpired:
            artifact = _write_deploy_notes(
                sprint_dir,
                sprint_id=sprint_id,
                deploy_status="failed",
                deploy_url="pending",
                provider=provider,
                commit_sha=commit_sha,
            )
            return {
                "artifact_path": str(artifact),
                "deploy_status": "failed",
                "failure_step": "ci_timeout",
            }

    # 4. Deploy — dispatch per provider.
    deploy_cmd = _build_deploy_cmd(provider, project, custom_cmd)
    if not deploy_cmd:
        artifact = _write_deploy_notes(
            sprint_dir,
            sprint_id=sprint_id,
            deploy_status="failed",
            deploy_url="pending",
            provider=provider,
            commit_sha=commit_sha,
        )
        return {
            "artifact_path": str(artifact),
            "deploy_status": "failed",
            "failure_step": "deploy_cmd_empty",
        }
    try:
        deploy_result = invoke_native_cli(
            deploy_cmd, cwd=cwd, timeout=_DEPLOY_CMD_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        artifact = _write_deploy_notes(
            sprint_dir,
            sprint_id=sprint_id,
            deploy_status="failed",
            deploy_url="pending",
            provider=provider,
            commit_sha=commit_sha,
        )
        return {
            "artifact_path": str(artifact),
            "deploy_status": "failed",
            "failure_step": "deploy_timeout",
        }

    if deploy_result.returncode != 0:
        artifact = _write_deploy_notes(
            sprint_dir,
            sprint_id=sprint_id,
            deploy_status="failed",
            deploy_url="pending",
            provider=provider,
            commit_sha=commit_sha,
        )
        return {
            "artifact_path": str(artifact),
            "deploy_status": "failed",
            "failure_step": "deploy",
            "exit_code": deploy_result.returncode,
        }

    deploy_url = _extract_deploy_url(deploy_result.stdout or "")

    # 5. Health probe — exponential backoff with deadline (T-05-06-04).
    healthy = _wait_for_health(deploy_url, verify_timeout)
    status = "succeeded" if healthy else "failed"
    artifact = _write_deploy_notes(
        sprint_dir,
        sprint_id=sprint_id,
        deploy_status=status,
        deploy_url=deploy_url or "pending",
        provider=provider,
        commit_sha=commit_sha,
    )
    return {
        "artifact_path": str(artifact),
        "deploy_status": status,
        "deploy_url": deploy_url,
    }
