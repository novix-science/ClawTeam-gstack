"""Plan 07-06 Task 1 — model fallback ladder (D-11).

Pure function ``apply_fallback(model_pref, spend_percent, fallback_at_percent)``
returns ``(effective_model, fallback_applied)``. Ladder:
    opus   -> sonnet
    sonnet -> haiku
    haiku  -> haiku  (terminal — still flagged as "policy engaged")

Unknown tiers (e.g. ``gpt-4``) are returned unchanged with
``fallback_applied=False`` even when over-threshold — the policy has nothing
to downgrade to.
"""
from __future__ import annotations

from clawteam.cost.fallback import FALLBACK_LADDER, apply_fallback


def test_below_threshold_unchanged():
    assert apply_fallback("claude-opus", 70.0, 80.0) == ("claude-opus", False)


def test_at_threshold_applies():
    assert apply_fallback("claude-opus", 80.0, 80.0) == ("claude-sonnet", True)


def test_sonnet_to_haiku():
    assert apply_fallback("claude-sonnet", 90.0, 80.0) == ("claude-haiku", True)


def test_haiku_stays_haiku():
    # Fallback applied=True signifies the policy engaged even though no
    # model change — callers stamp model_fallback_applied=True on the
    # envelope regardless.
    assert apply_fallback("claude-haiku", 90.0, 80.0) == ("claude-haiku", True)


def test_resolves_aliases():
    # "claude-3-opus-20240229" resolves to opus tier -> sonnet downgrade.
    result, applied = apply_fallback("claude-3-opus-20240229", 90.0, 80.0)
    assert result == "claude-sonnet"
    assert applied is True


def test_unknown_model_unchanged():
    # gpt-4 has no tier -> preserve input; no fallback applied.
    assert apply_fallback("gpt-4", 90.0, 80.0) == ("gpt-4", False)


def test_empty_model():
    # Empty string has no tier -> unchanged.
    assert apply_fallback("", 90.0, 80.0) == ("", False)


def test_fallback_at_percent_100():
    # Just-below-100 stays at the original model; hitting 100 fallbacks.
    assert apply_fallback("claude-opus", 99.0, 100.0) == ("claude-opus", False)
    assert apply_fallback("claude-opus", 100.0, 100.0) == ("claude-sonnet", True)


def test_zero_threshold_always_fallback():
    # At 0% threshold -> any spend (including 0) triggers fallback.
    assert apply_fallback("claude-opus", 0.0, 0.0) == ("claude-sonnet", True)


def test_ladder_map_shape():
    assert FALLBACK_LADDER["opus"] == "sonnet"
    assert FALLBACK_LADDER["sonnet"] == "haiku"
    assert FALLBACK_LADDER["haiku"] == "haiku"
