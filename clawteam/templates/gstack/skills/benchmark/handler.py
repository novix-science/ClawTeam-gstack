"""/benchmark handler (SKILL-18, Plan 05-09, §05-CONTEXT D-10 + D-15).

Core Web Vitals + page-load baselines. Lighthouse is primary; when missing
OR when Lighthouse stdout fails JSON parse, handler degrades to curl -w
timing. Writes ``benchmark-report.md`` (:class:`BenchmarkReport` schema) and,
when ``args['pre_deploy']`` is set, a baseline JSON under
``<get_data_dir>/teams/<team>/baselines/<provider>.json`` that /canary
(Plan 05-08) reads for its regression comparison.

Regression detection is a simple ratio check: any vital whose
``observed / baseline`` exceeds ``regression_threshold_ratio`` (default 1.5,
configurable via TemplateDef.benchmark) triggers a
:class:`WebVitalRegressionDetected` event emitted through ``ctx.bus`` AND
a ``regression_flags`` entry on the written artifact.

Pitfall / threat notes
----------------------
* Lighthouse stdout passes through ``json.loads`` guarded by a leading ``{``
  check + ``try/except json.JSONDecodeError`` — malformed output is treated
  as a lighthouse miss and triggers curl fallback (T-05-09-01).
* ``invoke_native_cli`` is always called without an explicit ``env=`` dict so
  scrub_env runs by default, stripping secret-shaped keys before handing the
  child process (T-05-09-02).
* Lighthouse invocation is bounded by a 180 s timeout so a slow/stuck
  Chromium can't wedge the handler (T-05-09-04).
* ``canary.poller.baseline_path`` / ``load_baseline`` are imported LAZILY
  inside the helpers so this module is collectable even when the canary
  sibling package hasn't landed yet (Wave 4 cross-executor resilience).
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.events.types import WebVitalRegressionDetected
from clawteam.fileutil import atomic_write_text
from clawteam.plugins.skill_errors import SkillPreconditionError
from clawteam.spawn.invoke import invoke_native_cli
from clawteam.templates.gstack.schemas.benchmark_report import BenchmarkReport


# Defaults that ship here rather than via TemplateDef so direct handler
# invocation in tests / scripts works without a full TemplateDef present.
_DEFAULT_THRESHOLD_RATIO: float = 1.5
_LIGHTHOUSE_TIMEOUT: int = 180
_CURL_TIMEOUT: int = 30

# Vitals in stable iteration order — the event emitter loops over this to
# produce one WebVitalRegressionDetected per regressed vital.
_VITALS: tuple[str, ...] = (
    "lcp_ms", "fid_ms", "cls_score", "ttfb_ms", "dom_loaded_ms",
)

# Lighthouse audit-key → BenchmarkReport field name.
_LIGHTHOUSE_AUDIT_MAP: dict[str, str] = {
    "largest-contentful-paint": "lcp_ms",
    "max-potential-fid": "fid_ms",
    "cumulative-layout-shift": "cls_score",
    "server-response-time": "ttfb_ms",
}


# ── Lazy helpers (avoid hard module-level dep on canary sibling package) ───


def baseline_path(team: str, provider: str) -> Path:
    """Return the conventional path for the pre-deploy baseline JSON.

    Delegates to :func:`clawteam.templates.gstack.skills.canary.poller.baseline_path`
    when that module is importable (canary ships in Plan 05-08). When the
    canary sibling package hasn't landed yet (Wave 4 parallel execution), we
    fall back to the same on-disk convention using the data-dir helper
    directly. Tests monkeypatch this function symbol at module scope so the
    fallback's on-disk behaviour is never exercised by the test suite.
    """
    try:
        from clawteam.templates.gstack.skills.canary.poller import (  # noqa: WPS433
            baseline_path as _canary_baseline_path,
        )
        return _canary_baseline_path(team, provider)
    except ImportError:
        from clawteam.team.models import get_data_dir  # noqa: WPS433
        return get_data_dir() / "teams" / team / "baselines" / f"{provider}.json"


def load_baseline(team: str, provider: str) -> dict[str, float] | None:
    """Best-effort baseline load; returns ``None`` on missing or malformed JSON.

    Mirrors :func:`clawteam.templates.gstack.skills.canary.poller.load_baseline`
    so the two skills share a single on-disk convention. Lazy import for the
    same Wave-4 cross-executor reason as :func:`baseline_path`.
    """
    try:
        from clawteam.templates.gstack.skills.canary.poller import (  # noqa: WPS433
            load_baseline as _canary_load_baseline,
        )
        return _canary_load_baseline(team, provider)
    except ImportError:
        path = baseline_path(team, provider)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
            return None
        except (json.JSONDecodeError, OSError):
            return None


# ── deploy.md frontmatter parser (mirrors land_and_deploy pattern) ─────────


def _read_deploy_notes(sprint_dir: Path) -> dict[str, Any]:
    """Parse deploy.md frontmatter; raise SkillPreconditionError when missing.

    We intentionally re-implement a minimal parser here rather than importing
    land_and_deploy's ``_parse_simple_frontmatter`` so the two skills can
    evolve their error messages / key handling independently.
    """
    path = sprint_dir / "deploy.md"
    if not path.exists():
        raise SkillPreconditionError(
            skill="/benchmark",
            role="sre",
            message="Run /land-and-deploy first (deploy.md not found)",
        )
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise SkillPreconditionError(
            skill="/benchmark",
            role="sre",
            message="deploy.md has no frontmatter",
        )
    end = text.find("\n---", 3)
    if end == -1:
        raise SkillPreconditionError(
            skill="/benchmark",
            role="sre",
            message="deploy.md frontmatter unterminated",
        )
    fm: dict[str, Any] = {}
    for line in text[3:end].splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        val = val.strip()
        if (
            len(val) >= 2
            and val[0] == val[-1]
            and val[0] in ("'", '"')
        ):
            val = val[1:-1]
        fm[key.strip()] = val
    return fm


# ── Lighthouse + curl collection ───────────────────────────────────────────


def _lighthouse_available() -> bool:
    """Return True iff ``lighthouse`` is on PATH (shutil.which reachable)."""
    return shutil.which("lighthouse") is not None


def _run_lighthouse(url: str) -> dict[str, float | None]:
    """Invoke lighthouse; return partial vitals dict (missing keys → None).

    Returns ``{}`` (empty dict) on any failure — missing binary, non-JSON
    stdout, or a stdout that parses but has no ``audits`` key. The caller
    treats an empty return as "lighthouse missed" and falls back to curl.
    """
    try:
        result = invoke_native_cli(
            [
                "lighthouse", url,
                "--output=json", "--quiet",
                "--chrome-flags=--headless",
            ],
            timeout=_LIGHTHOUSE_TIMEOUT,
        )
    except Exception:  # noqa: BLE001 — any subprocess failure triggers fallback
        return {}
    stdout = (result.stdout or "").strip()
    if not stdout.startswith("{"):
        return {}
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    audits = data.get("audits", {}) if isinstance(data, dict) else {}
    if not isinstance(audits, dict):
        return {}

    vitals: dict[str, float | None] = {}
    for audit_key, field_name in _LIGHTHOUSE_AUDIT_MAP.items():
        audit = audits.get(audit_key)
        if not isinstance(audit, dict):
            vitals[field_name] = None
            continue
        raw = audit.get("numericValue")
        vitals[field_name] = float(raw) if isinstance(raw, (int, float)) else None
    return vitals


def _run_curl(url: str) -> dict[str, float | None]:
    """Invoke ``curl -w '%{time_total} %{time_starttransfer}'``; return ms dict.

    curl emits two space-separated seconds values; we convert to milliseconds.
    Returns ``{}`` on any parse failure so the caller can note the miss.
    """
    try:
        result = invoke_native_cli(
            [
                "curl", "-o", "/dev/null", "-s",
                "-w", "%{time_total} %{time_starttransfer}",
                url,
            ],
            timeout=_CURL_TIMEOUT,
        )
    except Exception:  # noqa: BLE001 — any subprocess failure triggers a miss
        return {}
    parts = (result.stdout or "").strip().split()
    if len(parts) < 2:
        return {}
    try:
        time_total_ms = float(parts[0]) * 1000.0
        time_starttransfer_ms = float(parts[1]) * 1000.0
    except ValueError:
        return {}
    return {
        "ttfb_ms": time_starttransfer_ms,
        "dom_loaded_ms": time_total_ms,
    }


def _collect_vitals(url: str) -> tuple[dict[str, float | None], str]:
    """Return ``(vitals, measured_with)`` tuple.

    Primary path: lighthouse. Fill missing ttfb/dom_loaded with a curl
    second pass so partial Lighthouse output (D-15) still yields populated
    transport-layer metrics.
    Fallback path: curl only (measured_with='curl').
    """
    if _lighthouse_available():
        vitals = _run_lighthouse(url)
        if vitals:
            # Fill missing ttfb_ms / dom_loaded_ms via curl if lighthouse was
            # partial (D-15 adversarial — e.g. only LCP present).
            if vitals.get("ttfb_ms") is None or vitals.get("dom_loaded_ms") is None:
                curl = _run_curl(url)
                if vitals.get("ttfb_ms") is None and curl.get("ttfb_ms") is not None:
                    vitals["ttfb_ms"] = curl["ttfb_ms"]
                if vitals.get("dom_loaded_ms") is None and curl.get("dom_loaded_ms") is not None:
                    vitals["dom_loaded_ms"] = curl["dom_loaded_ms"]
            return vitals, "lighthouse"
    # Fallback — curl only.
    curl_vitals: dict[str, float | None] = {
        "lcp_ms": None,
        "fid_ms": None,
        "cls_score": None,
    }
    curl_vitals.update(_run_curl(url))
    return curl_vitals, "curl"


# ── Regression evaluation ──────────────────────────────────────────────────


def _evaluate_regressions(
    current: dict[str, float | None],
    baseline: dict[str, float] | None,
    threshold_ratio: float,
) -> list[tuple[str, float, float, float]]:
    """Return a list of regressed vitals as ``(name, baseline, observed, ratio)``.

    Zero or missing baseline values for a given vital are skipped so a new
    deployment's first-ever benchmark does not trigger spurious regressions.
    """
    if not baseline:
        return []
    hits: list[tuple[str, float, float, float]] = []
    for field_name in _VITALS:
        observed = current.get(field_name)
        base_val = baseline.get(field_name)
        if observed is None or base_val is None:
            continue
        try:
            base_f = float(base_val)
        except (TypeError, ValueError):
            continue
        if base_f <= 0.0:
            continue
        ratio = float(observed) / base_f
        if ratio > threshold_ratio:
            short = field_name
            if short.endswith("_ms"):
                short = short[:-3]
            elif short.endswith("_score"):
                short = short[:-6]
            hits.append((short, base_f, float(observed), ratio))
    return hits


# ── Artifact + baseline writers ────────────────────────────────────────────


def _render_report_yaml(schema: BenchmarkReport) -> str:
    """Serialize a :class:`BenchmarkReport` to ``---`` frontmatter text.

    Mirrors the hand-rolled emitter in /ship + /land-and-deploy so Phase 5
    artifacts stay consistent without a pyyaml dep.
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


def _write_report(
    sprint_dir: Path,
    *,
    sprint_id: str,
    vitals: dict[str, float | None],
    measured_with: str,
    benchmark_status: str,
    regression_flags: list[str],
) -> Path:
    """Atomic-write ``<sprint_dir>/benchmark-report.md``."""
    measured_with_final = measured_with if measured_with in ("lighthouse", "curl") else "curl"
    schema = BenchmarkReport(
        artifact_type="benchmark-report",
        benchmark_status=benchmark_status,  # type: ignore[arg-type]
        lcp_ms=vitals.get("lcp_ms"),
        fid_ms=vitals.get("fid_ms"),
        cls_score=vitals.get("cls_score"),
        ttfb_ms=float(vitals.get("ttfb_ms") or 0.0),
        dom_loaded_ms=float(vitals.get("dom_loaded_ms") or 0.0),
        regression_flags=regression_flags,
        measured_with=measured_with_final,  # type: ignore[arg-type]
        sprint_id=sprint_id,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    sprint_dir.mkdir(parents=True, exist_ok=True)
    artifact = sprint_dir / "benchmark-report.md"
    atomic_write_text(artifact, _render_report_yaml(schema))
    return artifact


def _write_baseline(
    team: str, provider: str, vitals: dict[str, float | None],
) -> Path:
    """Write the pre-deploy baseline JSON consumed by /canary.

    Always includes the full ``_VITALS`` key set (missing vitals → None so
    /canary can distinguish "no measurement" from "zero"), plus
    ``avg_response_ms`` which /canary uses for its response-time regression
    check.
    """
    path = baseline_path(team, provider)
    path.parent.mkdir(parents=True, exist_ok=True)
    ttfb = vitals.get("ttfb_ms") or 0.0
    dom = vitals.get("dom_loaded_ms") or 0.0
    if ttfb or dom:
        avg = (float(ttfb) + float(dom)) / 2.0
    else:
        avg = 0.0
    data: dict[str, float | None] = {key: vitals.get(key) for key in _VITALS}
    data["avg_response_ms"] = avg
    atomic_write_text(path, json.dumps(data, indent=2))
    return path


# ── Handler entry point ────────────────────────────────────────────────────


def benchmark_handler(
    ctx: Any, *, role: str, args: dict[str, Any],
) -> dict[str, Any]:
    """/benchmark entry point (sre role).

    Flow
    ----
    1. Read ``deploy.md`` frontmatter (deploy_url + provider).
    2. Collect vitals via lighthouse (primary) or curl (fallback).
    3. When ``args['pre_deploy']`` is truthy, write baseline JSON so a
       later /benchmark + /canary run can detect regressions.
    4. Otherwise, load an existing baseline (if any) and compare current
       vitals to detect regressions.
    5. Emit a :class:`WebVitalRegressionDetected` event per regressed vital.
    6. Write ``benchmark-report.md``.

    Parameters
    ----------
    ctx:
        Harness context. Read attributes (all optional): ``sprint_dir``,
        ``sprint_id``, ``team_name``, ``template`` / ``tmpl`` (carries
        ``.benchmark`` sub-config with ``regression_threshold_ratio``),
        ``bus`` (event emitter).
    role:
        Caller's role. Role gating is enforced upstream by
        :class:`SkillDispatcher`; direct handler calls in tests aren't gated.
    args:
        Optional overrides. Supported:

        * ``pre_deploy`` (bool): when true, write baseline JSON. Skip
          regression evaluation (comparing to a baseline you just wrote is
          useless).
        * ``team`` (str): team name for baseline path lookup. Falls back to
          ``ctx.team_name`` when omitted.
    """
    sprint_dir = Path(getattr(ctx, "sprint_dir", "."))
    sprint_id = getattr(ctx, "sprint_id", "")
    team_name = str(args.get("team") or getattr(ctx, "team_name", "default"))

    deploy_fm = _read_deploy_notes(sprint_dir)
    deploy_url = str(deploy_fm.get("deploy_url") or "")
    provider = str(deploy_fm.get("provider") or "custom")

    tmpl = getattr(ctx, "template", None) or getattr(ctx, "tmpl", None)
    bench_cfg = getattr(tmpl, "benchmark", None) if tmpl is not None else None
    if bench_cfg is not None:
        threshold_ratio = float(
            getattr(bench_cfg, "regression_threshold_ratio", _DEFAULT_THRESHOLD_RATIO)
        )
    else:
        threshold_ratio = _DEFAULT_THRESHOLD_RATIO

    # 2. Collect.
    vitals, measured_with = _collect_vitals(deploy_url)

    # 3. Pre-deploy baseline write (mutually exclusive with regression eval).
    is_pre_deploy = bool(args.get("pre_deploy", False))
    if is_pre_deploy:
        _write_baseline(team_name, provider, vitals)

    # 4. Regression evaluation.
    if is_pre_deploy:
        baseline = None
    else:
        baseline = load_baseline(team_name, provider)
    hits = _evaluate_regressions(vitals, baseline, threshold_ratio)
    regression_flags = [
        f"{vital}>{threshold_ratio}x_baseline" for vital, _, _, _ in hits
    ]
    benchmark_status = "regression" if regression_flags else "clean"

    # 5. Emit one event per regressed vital.
    bus = getattr(ctx, "bus", None)
    if bus is not None and hits:
        for vital_name, base_val, observed, ratio in hits:
            try:
                bus.emit(WebVitalRegressionDetected(
                    team_name=team_name,
                    sprint_id=sprint_id,
                    deploy_url=deploy_url,
                    vital=vital_name,
                    baseline_value=base_val,
                    observed_value=observed,
                    ratio=ratio,
                ))
            except Exception:  # noqa: BLE001 — event emission never fails the handler
                pass

    # 6. Write report.
    artifact = _write_report(
        sprint_dir,
        sprint_id=sprint_id,
        vitals=vitals,
        measured_with=measured_with,
        benchmark_status=benchmark_status,
        regression_flags=regression_flags,
    )
    return {
        "artifact_path": str(artifact),
        "benchmark_status": benchmark_status,
        "measured_with": measured_with,
        "regression_flags": regression_flags,
    }
