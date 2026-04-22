"""Plan 07-05 Task 1 — per-model pricing table + calculate_cost_usd.

D-11 substrate: pure-function pricing used by CostTracker when
ToolCallCompleted events arrive with cost_usd=0.0.
"""
from __future__ import annotations

import pytest

from clawteam.cost.pricing import MODEL_PRICING, calculate_cost_usd, resolve_tier


def test_opus_pricing():
    # 1M in + 1M out = 15 + 75 = 90.
    assert calculate_cost_usd("claude-opus", 1_000_000, 1_000_000) == pytest.approx(90.0)


def test_sonnet_pricing():
    assert calculate_cost_usd("claude-sonnet", 1_000_000, 1_000_000) == pytest.approx(18.0)


def test_haiku_pricing():
    assert calculate_cost_usd("claude-haiku", 1_000_000, 1_000_000) == pytest.approx(1.5)


def test_model_aliases():
    for alias in ("claude-3-opus", "opus", "claude-opus-4-7", "claude-3-opus-20240229"):
        assert resolve_tier(alias) == "opus"
    for alias in ("claude-sonnet", "claude-3-sonnet"):
        assert resolve_tier(alias) == "sonnet"
    for alias in ("claude-haiku", "claude-3-haiku", "claude-haiku-20240307"):
        assert resolve_tier(alias) == "haiku"


def test_unknown_model_zero():
    assert calculate_cost_usd("gpt-4", 1_000_000, 1_000_000) == 0.0


def test_empty_model_zero():
    assert calculate_cost_usd("", 100, 100) == 0.0


def test_zero_tokens():
    assert calculate_cost_usd("claude-opus", 0, 0) == 0.0


def test_partial_tokens():
    # 500 in * $15/M + 1000 out * $75/M = 7500e-6 + 75000e-6 = 0.0825.
    assert calculate_cost_usd("claude-opus", 500, 1000) == pytest.approx(0.0825)


def test_pricing_table_shape():
    # Sanity check on the hardcoded table so a future edit that breaks
    # the schema (e.g. single float instead of tuple) is caught at test time.
    assert set(MODEL_PRICING.keys()) == {"opus", "sonnet", "haiku"}
    for tier, rates in MODEL_PRICING.items():
        assert isinstance(rates, tuple)
        assert len(rates) == 2
        assert all(isinstance(r, (int, float)) and r > 0 for r in rates)


def test_resolve_tier_unknown_returns_none():
    assert resolve_tier("gpt-4") is None
    assert resolve_tier("") is None
    assert resolve_tier("llama-3") is None
