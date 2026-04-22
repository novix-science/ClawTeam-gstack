"""Model fallback ladder (Phase 7 D-11).

Pure function — caller passes current spend percent + configured fallback
threshold. Returns ``(effective_model, fallback_applied)``. Callers stamp
``model_fallback_applied: true`` on agent envelopes when the second
element is ``True`` so reviewers can see "this used sonnet not opus
because budget".

Ladder:

* ``opus``   -> ``sonnet``
* ``sonnet`` -> ``haiku``
* ``haiku``  -> ``haiku``  (terminal — cheapest available; ``fallback_applied``
  is still ``True`` so callers can distinguish "policy engaged" from
  "policy not engaged")

Unknown tiers (e.g. ``gpt-4``) are returned unchanged with
``fallback_applied=False`` — the policy has nothing to downgrade to, so
the envelope flag stays off.

**Scope boundary:** this module is pure policy. It does NOT read
``CostTracker.spend_percent()`` itself — the caller (NativeCliAdapter /
``invoke_native_cli`` at spawn time) is responsible for passing the
current spend percent + configured threshold. Keeping fallback stateless
makes the policy trivially testable and composable with alternative
budget sources (e.g. per-sprint budgets, user-level budgets) without any
schema change.
"""
from __future__ import annotations

from clawteam.cost.pricing import ModelTier, resolve_tier

# Tier-to-tier downgrade map. Haiku terminates (cheapest available).
FALLBACK_LADDER: dict[ModelTier, ModelTier] = {
    "opus": "sonnet",
    "sonnet": "haiku",
    "haiku": "haiku",
}

# Canonical model names to return after downgrade. Callers that need a
# more specific model string (e.g. ``claude-sonnet-20250101``) should map
# in a wrapper; the canonical values here are what the envelope records
# so reviewers can see the effective tier at a glance.
TIER_TO_CANONICAL: dict[ModelTier, str] = {
    "opus": "claude-opus",
    "sonnet": "claude-sonnet",
    "haiku": "claude-haiku",
}


def apply_fallback(
    model_pref: str,
    spend_percent: float,
    fallback_at_percent: float = 80.0,
) -> tuple[str, bool]:
    """Return ``(effective_model, fallback_applied)``.

    * When ``spend_percent < fallback_at_percent``: returns
      ``(model_pref, False)`` unchanged.
    * When ``spend_percent >= fallback_at_percent``: returns the
      downgraded model per :data:`FALLBACK_LADDER` + ``True``.
    * Unknown model strings (no matching tier in :func:`resolve_tier`)
      are returned unchanged with ``fallback_applied=False`` — the
      policy has nothing to downgrade to.

    Idempotent on haiku: ``apply_fallback("claude-haiku", 90.0, 80.0)``
    returns ``("claude-haiku", True)`` — the flag is ``True`` because
    the policy engaged (budget crossed), even though no model change
    was applied (haiku is already bottom of the ladder).
    """
    if spend_percent < fallback_at_percent:
        return model_pref, False
    tier = resolve_tier(model_pref)
    if tier is None:
        return model_pref, False
    downgraded_tier = FALLBACK_LADDER[tier]
    return TIER_TO_CANONICAL[downgraded_tier], True


__all__ = ["apply_fallback", "FALLBACK_LADDER", "TIER_TO_CANONICAL"]
