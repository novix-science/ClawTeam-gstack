"""/benchmark skill (SKILL-18, Plan 05-09).

Core Web Vitals + page-load baselines via Lighthouse primary, curl fallback.
Writes benchmark-report.md + optional pre-deploy baseline JSON (consumed by
/canary). Emits WebVitalRegressionDetected on vital > threshold_ratio *
baseline (default 1.5x).
"""
from clawteam.templates.gstack.skills.benchmark.handler import benchmark_handler

__all__ = ["benchmark_handler"]
