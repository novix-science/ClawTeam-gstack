"""/canary skill (SKILL-17, Plan 05-08).

Post-deploy monitor — polls deploy_url for a configurable window, tracks
HTTP 2xx/5xx counts + avg response time, optionally scrapes JS console
errors (lazy-imported Playwright per Pitfall 5), emits canary-report.md,
and emits DeployRegressionDetected when thresholds are breached.

Handler is lazy-loaded via PEP 562 ``__getattr__`` so importing this package
doesn't require handler.py to exist during Task-1 development; plugin
registration in gstack_sprint_plugin.py imports ``canary_handler`` directly
from ``clawteam.templates.gstack.skills.canary.handler``.
"""
from clawteam.templates.gstack.skills.canary.poller import (
    PollResult,
    baseline_path,
    evaluate_regression,
    load_baseline,
    poll_window,
)

__all__ = [
    "PollResult",
    "baseline_path",
    "canary_handler",
    "evaluate_regression",
    "load_baseline",
    "poll_window",
]


def __getattr__(name: str):  # pragma: no cover — import indirection only
    if name == "canary_handler":
        from clawteam.templates.gstack.skills.canary.handler import canary_handler
        return canary_handler
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
