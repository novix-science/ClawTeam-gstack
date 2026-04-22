"""Per-model pricing table (Phase 7 D-11 substrate).

Prices are per 1M tokens in USD. Source: Anthropic public pricing as of
2026-04 [ASSUMED — update via PR when pricing changes; tracked in
07-RESEARCH.md Assumption A5].

Aliases allow the tracker to accept arbitrary model strings
(``claude-3-opus``, ``claude-opus-4-7``, ``opus-20250929``) and resolve
them to one of three tiers: ``opus`` / ``sonnet`` / ``haiku``.

Used by :class:`clawteam.cost.tracker.CostTracker` as a backstop when a
:class:`~clawteam.events.types.ToolCallCompleted` event arrives with
``cost_usd == 0.0`` — the tracker falls back to this table by model name.
"""
from __future__ import annotations

import logging
from typing import Literal

_LOG = logging.getLogger(__name__)

ModelTier = Literal["opus", "sonnet", "haiku"]

# USD per 1M tokens (input_rate, output_rate).
#
# Anthropic public pricing, 2026-04:
#   opus:   $15 / $75
#   sonnet: $3  / $15
#   haiku:  $0.25 / $1.25
MODEL_PRICING: dict[ModelTier, tuple[float, float]] = {
    "opus":   (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku":  (0.25, 1.25),
}


def resolve_tier(model: str) -> ModelTier | None:
    """Map a concrete model string to one of the 3 tiers.

    Accepts any substring match (``claude-3-opus-20240229`` -> ``opus``).
    Returns ``None`` for empty strings or unknown models (e.g. ``gpt-4``).
    """
    if not model:
        return None
    m = model.lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return None


def calculate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return USD cost of the invocation.

    Unknown model -> ``0.0`` (logged at DEBUG so load tests don't spam).
    Zero tokens -> ``0.0`` regardless of model.
    """
    tier = resolve_tier(model)
    if tier is None:
        _LOG.debug("Unknown model for pricing: %r -- returning 0.0", model)
        return 0.0
    in_rate, out_rate = MODEL_PRICING[tier]
    return (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate


__all__ = ["MODEL_PRICING", "ModelTier", "calculate_cost_usd", "resolve_tier"]
