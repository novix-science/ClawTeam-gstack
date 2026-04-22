"""Canary HTTP poller + regression evaluator (SKILL-17, Plan 05-08).

Pure helpers split out of the handler so tests can inject ``http_fn``/
``sleep_fn`` without wall-clock dependence. ``poll_window`` loops until the
monotonic deadline elapses, categorising each response as 2xx or 5xx (any
non-2xx/3xx status + network errors are treated as 5xx). ``evaluate_regression``
applies three independent threshold checks and returns the list of triggered
flag strings; non-empty list → canary_status='regression'.

The ``baseline_path`` + ``load_baseline`` helpers resolve the
``~/.clawteam/teams/<team>/baselines/<provider>.json`` file written by the
/benchmark skill (Plan 05-09). Absent or malformed baseline JSON is
swallowed (returns ``None``) so /canary runs unblocked in the common
first-sprint case where no baseline exists yet (D-10 / Plan 05-08).
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

# Import get_data_dir from the canonical clawteam.team.models location (same
# source used by the Phase 3+ sprint substrate). If that import surface ever
# moves, fall back to a couple of other conventional homes and finally to a
# pure ~/.clawteam placeholder so the poller remains importable in minimal
# test environments.
try:
    from clawteam.team.models import get_data_dir  # type: ignore
except ImportError:  # pragma: no cover — defensive only
    try:
        from clawteam.paths import get_data_dir  # type: ignore
    except ImportError:  # pragma: no cover
        try:
            from clawteam.utils import get_data_dir  # type: ignore
        except ImportError:  # pragma: no cover

            def get_data_dir() -> Path:  # type: ignore[misc]
                return Path.home() / ".clawteam"


@dataclass
class PollResult:
    """Structured result of a single ``poll_window`` invocation.

    ``response_times_ms`` holds one entry per HTTP call so the handler can
    later compute the arithmetic mean via :attr:`avg_response_ms` without
    carrying a running average alongside the counts (keeps the dataclass
    trivially copyable + serialisable for tests).
    """

    http_2xx_count: int = 0
    http_5xx_count: int = 0
    response_times_ms: list[float] = field(default_factory=list)
    js_console_errors: list[str] = field(default_factory=list)

    @property
    def avg_response_ms(self) -> float:
        if not self.response_times_ms:
            return 0.0
        return sum(self.response_times_ms) / len(self.response_times_ms)

    @property
    def total_requests(self) -> int:
        return self.http_2xx_count + self.http_5xx_count


def _default_http_fn(url: str) -> tuple[int, float]:
    """Single HTTP GET; returns (status_code, elapsed_ms).

    Transport errors (URLError / HTTPError / timeout / OS) are coerced to
    status 599 so the caller can treat them uniformly as 5xx without having
    to catch exceptions from the poll loop. Mirrors the defensive posture
    of evidence_gate._head_probe.
    """
    start = time.monotonic()
    try:
        req = urllib.request.Request(url, method="GET")  # noqa: S310
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            status = resp.status
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        status = 599
    elapsed_ms = (time.monotonic() - start) * 1000.0
    return status, elapsed_ms


def poll_window(
    url: str,
    *,
    window_seconds: float,
    poll_interval_seconds: float,
    http_fn: Optional[Callable[[str], tuple[int, float]]] = None,
    sleep_fn: Optional[Callable[[float], None]] = None,
) -> PollResult:
    """Poll ``url`` every ``poll_interval_seconds`` for up to ``window_seconds``.

    ``http_fn`` + ``sleep_fn`` are injectable so tests can run without
    wall-clock sleeps. The fake ``http_fn`` may raise to simulate transport
    errors — the caller counts these as 5xx. The deadline is monotonic so
    clock-adjustment can't break the loop (T-05-08-01).
    """
    fn_http: Callable[[str], tuple[int, float]] = http_fn or _default_http_fn
    fn_sleep: Callable[[float], None] = sleep_fn or time.sleep
    result = PollResult()
    deadline = time.monotonic() + max(0.0, float(window_seconds))
    # Guarantee at least one sample so short windows (adversarial D-15) don't
    # produce an empty PollResult that the evaluator can't reason about.
    first = True
    while first or time.monotonic() < deadline:
        first = False
        # T-05-08-01 invariant: /canary MUST NEVER fail its outer handler on
        # transport or user-supplied http_fn error. Catch broadly so that
        # mocks with side_effect=Exception("boom"), bare RuntimeError from a
        # user-injected fake, or any new urllib subclass still degrade to a
        # 599 "unknown transport error" sample. BaseException subclasses
        # (KeyboardInterrupt, SystemExit) still propagate so the poll loop
        # remains interruptible.
        try:
            status, elapsed_ms = fn_http(url)
        except Exception:  # noqa: BLE001 — any transport or user-fn failure = 5xx
            status, elapsed_ms = 599, 0.0
        result.response_times_ms.append(elapsed_ms)
        if 200 <= status < 400:
            result.http_2xx_count += 1
        else:
            result.http_5xx_count += 1
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        fn_sleep(min(float(poll_interval_seconds), remaining))
    return result


def evaluate_regression(
    result: PollResult,
    *,
    baseline_avg_ms: float = 0.0,
    threshold_5xx_rate: float = 0.01,
    response_time_multiplier: float = 2.0,
) -> list[str]:
    """Apply three threshold checks and return the list of triggered flags.

    Flag strings interpolate the configured thresholds so downstream consumers
    see the narrative that matches the runtime configuration (mirrors the
    benchmark handler's ``f"{vital}>{threshold_ratio}x_baseline"`` pattern —
    see Phase-5 REVIEW WR-03):

    * ``"5xx_rate>1%"`` — ``http_5xx_count / total > threshold_5xx_rate``.
      The literal ``1%`` reflects the default and is retained for parser
      backwards-compat; a future knob would parameterize this the same way.
    * ``f"response_time>{response_time_multiplier}x_baseline"`` — observed
      average exceeds ``multiplier * baseline_avg_ms``. Skipped when
      ``baseline_avg_ms <= 0`` (baseline missing). Pre-fix this string was
      hard-coded ``"response_time>2x_baseline"`` even when the multiplier
      was configured to a non-2.0 value.
    * ``"js_console_error"`` — any entry in ``result.js_console_errors``.
    """
    flags: list[str] = []
    total = result.total_requests
    if total > 0:
        rate = result.http_5xx_count / total
        if rate > threshold_5xx_rate:
            flags.append("5xx_rate>1%")
    if (
        baseline_avg_ms > 0
        and result.avg_response_ms > baseline_avg_ms * response_time_multiplier
    ):
        flags.append(f"response_time>{response_time_multiplier}x_baseline")
    if result.js_console_errors:
        flags.append("js_console_error")
    return flags


def baseline_path(team: str, provider: str) -> Path:
    """Return ``<data_dir>/teams/<team>/baselines/<provider>.json``.

    The /benchmark skill (Plan 05-09) writes this JSON on success; /canary
    reads it best-effort. Shape is intentionally loose (dict with at least
    ``avg_response_ms``) so /benchmark can evolve independently.
    """
    return get_data_dir() / "teams" / team / "baselines" / f"{provider}.json"


def load_baseline(team: str, provider: str) -> Optional[dict]:
    """Best-effort baseline read; returns ``None`` on missing OR malformed JSON.

    T-05-08-03 mitigation: a tampered baselines/<provider>.json must not crash
    the canary handler. We swallow JSONDecodeError + OSError and let the
    caller proceed with baseline_missing=True.
    """
    path = baseline_path(team, provider)
    if not path.exists():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            return loaded
        return None
    except (json.JSONDecodeError, OSError, ValueError):
        return None
