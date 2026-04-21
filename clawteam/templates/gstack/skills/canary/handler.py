"""/canary handler (SKILL-17, Plan 05-08, D-09).

Orchestration entry point for the post-deploy monitor. Four phases:

1. Read ``deploy.md`` frontmatter from ``ctx.sprint_dir`` to recover the
   ``deploy_url`` + ``provider`` written by /land-and-deploy. Missing file
   raises :class:`SkillPreconditionError` with the hint ``Run /land-and-deploy
   first`` so the agent surface can render a remediation message.
2. Load the pre-deploy baseline via
   :func:`clawteam.templates.gstack.skills.canary.poller.load_baseline`.
   Absent/malformed baselines are tolerated — ``baseline_missing=True`` is
   recorded in the report and the response-time flag is skipped (D-10).
3. Poll the deploy URL for ``window_seconds`` (default 300, overridable via
   ``ctx.template.canary`` or ``args``). Optional ``args['browser']=True``
   additionally lazy-imports Playwright inside :func:`_get_browser_errors`
   to scrape JS console errors (Pitfall 5 — Playwright is NEVER imported at
   module top level).
4. Run :func:`evaluate_regression` → write ``canary-report.md`` →
   emit :class:`DeployRegressionDetected` via ``ctx.bus.emit`` on any flag.

All paths always produce an artifact so EvidenceGate (upstream) can surface
the outcome regardless of which sub-step encountered trouble.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from clawteam.events.types import DeployRegressionDetected
from clawteam.fileutil import atomic_write_text
from clawteam.plugins.skill_errors import SkillPreconditionError
from clawteam.templates.gstack.schemas.canary_report import CanaryReport
from clawteam.templates.gstack.skills.canary.poller import (
    PollResult,
    evaluate_regression,
    load_baseline,
    poll_window,
)

_DEFAULT_WINDOW_SECONDS: int = 300
_DEFAULT_POLL_INTERVAL_SECONDS: int = 15


# ── Frontmatter helper (reuses /land-and-deploy shape without coupling) ────


def _read_deploy_notes(sprint_dir: Path) -> dict[str, Any]:
    """Parse ``deploy.md`` frontmatter; raise :class:`SkillPreconditionError` on error.

    Lightweight parser — we only need ``deploy_url`` + ``provider``, so we
    reimplement the ``---`` block reader rather than take a pyyaml dep.
    Mirrors the pattern in ``/land-and-deploy`` handler so both skills stay
    drift-safe if frontmatter writers evolve.
    """
    path = sprint_dir / "deploy.md"
    if not path.exists():
        raise SkillPreconditionError(
            skill="/canary",
            role="sre",
            message="Run /land-and-deploy first (deploy.md not found)",
        )
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise SkillPreconditionError(
            skill="/canary",
            role="sre",
            message="deploy.md has no frontmatter — Run /land-and-deploy first",
        )
    end = text.find("\n---", 3)
    if end == -1:
        raise SkillPreconditionError(
            skill="/canary",
            role="sre",
            message="deploy.md frontmatter unterminated — Run /land-and-deploy first",
        )
    fm: dict[str, Any] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        if not key:
            continue
        val = val.strip()
        # Strip surrounding single or double quotes.
        if (
            len(val) >= 2
            and val[0] == val[-1]
            and val[0] in ("'", '"')
        ):
            val = val[1:-1]
        fm[key] = val
    return fm


# ── Browser mode — lazy-imported Playwright (Pitfall 5 defense) ────────────


def _get_browser_errors(url: str) -> list[str]:
    """Lazy-import Playwright and scrape JS console errors from ``url``.

    Pitfall 5 / T-05-08-05: ``playwright`` is imported ONLY inside this
    function body. An AST-level test (test_handler_module_level_no_playwright_import)
    asserts no module-level import references playwright so a future editor
    cannot accidentally promote the import and break this defense.

    Returns ``[]`` in all failure modes — missing Playwright install, import
    error, navigation timeout, browser crash (T-05-08-02). Browser failures
    must NEVER fail the outer handler.
    """
    if find_spec("playwright") is None:
        return []
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ImportError:  # pragma: no cover — find_spec already covers this
        return []
    errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                page = browser.new_page()

                def _on_console(msg: Any) -> None:
                    try:
                        if getattr(msg, "type", "") == "error":
                            errors.append(str(getattr(msg, "text", "")))
                    except Exception:  # noqa: BLE001 — listener never fails
                        pass

                page.on("console", _on_console)
                page.goto(url, timeout=15000)
                page.wait_for_load_state("networkidle", timeout=10000)
            finally:
                browser.close()
    except Exception as exc:  # noqa: BLE001 — browser errors are non-fatal
        errors.append(f"<browser-error>: {type(exc).__name__}: {exc}")
    return errors


# ── Report writer ──────────────────────────────────────────────────────────


def _render_canary_report_yaml(schema: CanaryReport) -> str:
    """Serialize a :class:`CanaryReport` instance to ``---`` frontmatter text.

    Mirrors the hand-rolled YAML emitter used by /ship + /land-and-deploy
    so the Phase 5 skills stay consistent without a pyyaml dep.
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


def _write_canary_report(
    sprint_dir: Path,
    *,
    sprint_id: str,
    canary_status: str,
    window_seconds: int,
    result: PollResult,
    baseline_avg_ms: float,
    baseline_missing: bool,
    regression_flags: list[str],
) -> Path:
    """Validate + atomic-write ``<sprint_dir>/canary-report.md``."""
    schema = CanaryReport(
        artifact_type="canary-report",
        canary_status=canary_status,  # type: ignore[arg-type]
        window_seconds=max(1, int(window_seconds)),
        http_2xx_count=result.http_2xx_count,
        http_5xx_count=result.http_5xx_count,
        avg_response_ms=float(result.avg_response_ms),
        pre_deploy_avg_response_ms=float(baseline_avg_ms),
        baseline_missing=baseline_missing,
        js_console_errors=list(result.js_console_errors),
        regression_flags=list(regression_flags),
        sprint_id=sprint_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    sprint_dir.mkdir(parents=True, exist_ok=True)
    artifact = sprint_dir / "canary-report.md"
    atomic_write_text(artifact, _render_canary_report_yaml(schema))
    return artifact


# ── Handler entry point ────────────────────────────────────────────────────


def canary_handler(
    ctx: Any, *, role: str, args: dict[str, Any],
) -> dict[str, Any]:
    """Entry point registered via ``SkillRegistration(name='/canary', roles={'sre'})``.

    Parameters
    ----------
    ctx:
        Harness context. Optional attributes: ``sprint_dir``, ``sprint_id``,
        ``team_name``, ``template`` / ``tmpl`` (carries ``.canary`` cfg),
        ``bus`` (for event emission).
    role:
        Caller's role. Dispatcher enforces ``role == 'sre'`` before reaching
        here — the handler is still safe to call directly in tests.
    args:
        Optional overrides:

        * ``window_seconds`` (int): override
          ``ctx.template.canary.window_seconds`` (default 300).
        * ``poll_interval_seconds`` (int): override ``ctx.template.canary``
          value (default 15).
        * ``browser`` (bool): opt into Playwright JS-console scraping.
    """
    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    sprint_id = getattr(ctx, "sprint_id", "")
    team_name = getattr(ctx, "team_name", "default") or "default"

    # 1. Precondition — deploy.md with deploy_url/provider from /land-and-deploy.
    deploy_fm = _read_deploy_notes(sprint_dir)
    deploy_url = str(deploy_fm.get("deploy_url") or "")
    provider = str(deploy_fm.get("provider") or "custom")

    # 2. Resolve canary config (template -> defaults); args override both.
    tmpl = getattr(ctx, "template", None) or getattr(ctx, "tmpl", None)
    canary_cfg = getattr(tmpl, "canary", None) if tmpl is not None else None
    window_default = (
        int(getattr(canary_cfg, "window_seconds", _DEFAULT_WINDOW_SECONDS))
        if canary_cfg is not None
        else _DEFAULT_WINDOW_SECONDS
    )
    interval_default = (
        int(getattr(canary_cfg, "poll_interval_seconds", _DEFAULT_POLL_INTERVAL_SECONDS))
        if canary_cfg is not None
        else _DEFAULT_POLL_INTERVAL_SECONDS
    )
    window_seconds = int(args.get("window_seconds", window_default))
    poll_interval_seconds = int(
        args.get("poll_interval_seconds", interval_default)
    )

    # 3. Load pre-deploy baseline (best-effort; D-10).
    baseline = load_baseline(team_name, provider)
    baseline_missing = baseline is None
    baseline_avg_ms = (
        float(baseline.get("avg_response_ms", 0.0)) if baseline else 0.0
    )

    # 4. Poll deploy URL.
    result = poll_window(
        deploy_url,
        window_seconds=window_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )

    # 5. Optional browser mode — lazy-imported Playwright (Pitfall 5).
    if args.get("browser", False):
        result.js_console_errors.extend(_get_browser_errors(deploy_url))

    # 6. Evaluate regression flags + derive canary_status.
    flags = evaluate_regression(result, baseline_avg_ms=baseline_avg_ms)
    canary_status = "regression" if flags else "clean"

    # 7. Write canary-report.md.
    artifact = _write_canary_report(
        sprint_dir,
        sprint_id=sprint_id,
        canary_status=canary_status,
        window_seconds=window_seconds,
        result=result,
        baseline_avg_ms=baseline_avg_ms,
        baseline_missing=baseline_missing,
        regression_flags=flags,
    )

    # 8. Emit DeployRegressionDetected on any regression flag.
    if flags:
        bus = getattr(ctx, "bus", None)
        if bus is not None and hasattr(bus, "emit"):
            try:
                bus.emit(
                    DeployRegressionDetected(
                        team_name=team_name,
                        sprint_id=sprint_id,
                        deploy_url=deploy_url,
                        regression_flags=list(flags),
                        http_2xx_count=result.http_2xx_count,
                        http_5xx_count=result.http_5xx_count,
                        avg_response_ms=float(result.avg_response_ms),
                        pre_deploy_avg_response_ms=float(baseline_avg_ms),
                    )
                )
            except Exception:  # noqa: BLE001 — event emission is advisory
                pass

    return {
        "artifact_path": str(artifact),
        "canary_status": canary_status,
        "regression_flags": list(flags),
    }
