"""Unit tests for GstackReviewRouter (Plan 04-06 + SPRINT-03).

Covers:
- ``_match_path`` globstar semantics (7 fixture cases from PLAN_PREP_NOTES
  ``A-fnmatch``).
- ``GstackReviewRouter.match`` contract: reviewer floor, per-signal routing,
  accumulation, deduplication, exception tolerance, determinism, Protocol
  conformance.
"""

from __future__ import annotations

from types import SimpleNamespace

from clawteam.harness.gstack_review_router import GstackReviewRouter, _match_path
from clawteam.templates import ReviewRule


def _rules_canonical():
    return [
        ReviewRule(pattern="src/components/**/*.tsx", reviewers=["designer"], signal="ui"),
        ReviewRule(pattern="**/*.css",                reviewers=["designer"], signal="ui"),
        ReviewRule(pattern="src/auth/**",             reviewers=["security"], signal="crypto"),
        ReviewRule(pattern="**/crypto/**",            reviewers=["security"], signal="crypto"),
        ReviewRule(pattern="app/api/**",              reviewers=["dx-lead"],  signal="api"),
        ReviewRule(pattern="package.json",            reviewers=["dx-lead"],  signal="api"),
    ]


def _state():
    return SimpleNamespace(
        workspace_branch="/tmp/x",
        review_sha="deadbeef" * 5,
        current_phase="review",
    )


# ── _match_path semantics (foundation) ──────────────────────────────────


def test_match_path_literal():
    assert _match_path("package.json", "package.json") is True
    assert _match_path("lib/package.json", "package.json") is False


def test_match_path_doublestar_in_middle():
    """Canonical globstar spanning zero-or-more path segments."""
    assert _match_path("src/components/Button.tsx", "src/components/**/*.tsx") is True
    assert _match_path("src/components/forms/Input.tsx", "src/components/**/*.tsx") is True
    assert _match_path("src/other/Button.tsx", "src/components/**/*.tsx") is False


def test_match_path_trailing_doublestar():
    assert _match_path("src/auth/middleware.py", "src/auth/**") is True
    assert _match_path("src/auth/tokens/jwt.py", "src/auth/**") is True
    assert _match_path("src/authn.py", "src/auth/**") is False


def test_match_path_leading_doublestar():
    assert _match_path("lib/crypto/aes.py", "**/crypto/**") is True
    assert _match_path("app/crypto/keys.ts", "**/crypto/**") is True
    # Prefix collision — 'cryptonot' is a distinct segment, must NOT match.
    assert _match_path("src/cryptonot/a.ts", "**/crypto/**") is False


def test_match_path_doublestar_suffix_only():
    assert _match_path("a.css", "**/*.css") is True
    assert _match_path("lib/style.css", "**/*.css") is True
    assert _match_path("app/deep/nested/s.css", "**/*.css") is True


def test_match_path_bare_doublestar_matches_anything():
    assert _match_path("a", "**") is True
    assert _match_path("a/b/c", "**") is True
    assert _match_path("", "**") is True


def test_match_path_app_api_deep():
    """Regression: app/api/users/route.ts vs app/api/** — must match."""
    assert _match_path("app/api/users/route.ts", "app/api/**") is True
    assert _match_path("app/api/users.ts", "app/api/**") is True


# ── Router match() contract ──────────────────────────────────────────────


def test_reviewer_always_participates():
    r = GstackReviewRouter(_rules_canonical())
    # Empty diff still pulls the reviewer floor.
    assert r.match([], _state()) == ["reviewer"]


def test_ui_diff_pulls_designer():
    r = GstackReviewRouter(_rules_canonical())
    result = r.match(["src/components/forms/Button.tsx"], _state())
    assert set(result) == {"designer", "reviewer"}


def test_crypto_diff_pulls_security():
    r = GstackReviewRouter(_rules_canonical())
    result = r.match(["lib/crypto/aes.py"], _state())
    assert set(result) == {"security", "reviewer"}


def test_auth_diff_pulls_security():
    r = GstackReviewRouter(_rules_canonical())
    result = r.match(["src/auth/middleware.py"], _state())
    assert set(result) == {"security", "reviewer"}


def test_api_and_package_pull_dx_lead():
    r = GstackReviewRouter(_rules_canonical())
    result = r.match(["app/api/users/route.ts", "package.json"], _state())
    assert set(result) == {"dx-lead", "reviewer"}


def test_union_of_matches_accumulation():
    r = GstackReviewRouter(_rules_canonical())
    result = r.match(
        ["src/components/forms/X.tsx", "app/api/Y.ts"],
        _state(),
    )
    assert set(result) == {"designer", "dx-lead", "reviewer"}


def test_no_match_floor_only():
    r = GstackReviewRouter(_rules_canonical())
    result = r.match(["README.md", "docs/guide.md"], _state())
    assert result == ["reviewer"]


def test_deduplication():
    rules = [
        ReviewRule(pattern="**/*.tsx", reviewers=["designer"]),
        ReviewRule(pattern="src/**", reviewers=["designer"]),
    ]
    r = GstackReviewRouter(rules)
    result = r.match(["src/components/Button.tsx"], _state())
    assert result.count("designer") == 1


def test_exception_in_pattern_match_skipped(caplog):
    """Broken glob pattern does not crash match(); logged + skipped.

    Mitigates T-04-18 (tampering via broken glob). Router must continue
    matching remaining rules so the reviewer floor + unaffected rules
    still fire.
    """
    rules = [
        # Pydantic rejects pattern="" but not all malformed patterns.
        # Force a runtime-broken rule by passing a mangled pattern that
        # confuses fnmatch on Python 3.10+ character-class parsing:
        ReviewRule(pattern="[invalid", reviewers=["broken"]),
        ReviewRule(pattern="**/*.tsx", reviewers=["designer"]),
    ]
    r = GstackReviewRouter(rules)
    with caplog.at_level("WARNING"):
        result = r.match(["src/Button.tsx"], _state())
    # Designer still pulled despite broken rule; floor reviewer present.
    assert "designer" in result
    assert "reviewer" in result


def test_rule_adding_reviewer_does_not_duplicate():
    rules = [ReviewRule(pattern="**/*.py", reviewers=["reviewer"])]
    r = GstackReviewRouter(rules)
    result = r.match(["a.py"], _state())
    assert result.count("reviewer") == 1


def test_match_returns_sorted_deterministic():
    r = GstackReviewRouter(_rules_canonical())
    result1 = r.match(
        ["src/components/forms/X.tsx", "app/api/Y.ts", "lib/crypto/z.py"],
        _state(),
    )
    result2 = r.match(
        ["src/components/forms/X.tsx", "app/api/Y.ts", "lib/crypto/z.py"],
        _state(),
    )
    assert result1 == result2  # deterministic
    assert result1 == sorted(result1)  # sorted


def test_empty_rules_returns_floor_only():
    r = GstackReviewRouter([])
    assert r.match(["anything.py"], _state()) == ["reviewer"]


def test_protocol_conformance():
    from clawteam.harness.review_router import ReviewRouter  # noqa: F401

    r = GstackReviewRouter([])
    # Structural type check: exists match() method matching Protocol.
    assert callable(r.match)
    result = r.match([], _state())
    assert isinstance(result, list)
