"""GstackReviewRouter — concrete :class:`ReviewRouter` for the gstack template.

§04-CONTEXT D-04 / D-06 + §04-REQUIREMENTS SPRINT-03. Path-glob rules with
first-match-WITH-accumulation semantics: a diff path matching N rules pulls
in the union of all their reviewer sets. The ``reviewer`` role is ALWAYS
appended as the cross-cutting floor (QUALITY-13 decorrelation anchor).

Glob engine
-----------
Custom shim on top of stdlib :mod:`fnmatch` — see ``PLAN_PREP_NOTES.md
## A-fnmatch``. Neither raw :func:`fnmatch.fnmatch` nor
:meth:`pathlib.PurePosixPath.match` cover the full globstar semantics we
need on the supported Python baseline (``>=3.10``): ``PurePosixPath.full_match``
would suffice but is Python 3.13+ only. The shim is ~35 LOC, zero new runtime
deps, and covers all 7 fixture cases in the prep notes.

Delete invariant (§04-CONTEXT ``<domain>``)
-------------------------------------------
File is prefixed ``gstack_`` so removing
``clawteam/templates/gstack.toml`` + this router + GstackSprintPlugin (Plan
04-11) leaves the rest of the codebase unchanged. Non-gstack templates never
instantiate this class.
"""

from __future__ import annotations

import logging
from fnmatch import fnmatch
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawteam.sprint.state import SprintState
    from clawteam.templates import ReviewRule

_logger = logging.getLogger(__name__)

# Cross-cutting floor role — the "reviewer" persona always participates so
# the aggregated /review-report.md has a staff-eng anchor regardless of
# which per-signal rules fire. T-04-20 mitigation: this floor is NOT
# negotiable via `[[template.review.rules]]` — the router unconditionally
# appends it after rule accumulation.
_FLOOR_REVIEWER = "reviewer"


def _match_path(path: str, pattern: str) -> bool:
    """Router-path matching with true globstar (``**``) semantics.

    ``**`` matches zero or more path segments (including slashes). Portable
    across Python 3.10-3.12 (``PurePosixPath.full_match`` is 3.13+ only, so
    we cannot rely on it). Uses :func:`fnmatch.fnmatch` on simpler segments
    after splitting on ``/**/``; falls back to single-segment ``fnmatch``
    when no globstar is present.

    Returns True iff ``path`` matches ``pattern`` as a full-path match.

    Copied verbatim from ``PLAN_PREP_NOTES.md ## A-fnmatch``. Do not modify
    without re-running the 7-case fixture in the prep notes.
    """
    # Bare '**' matches any path.
    if pattern == "**":
        return True
    # No globstar → single-segment fnmatch (handles '*' and '?' only).
    if "**" not in pattern:
        return fnmatch(path, pattern)

    # Leading '**/' means "match anywhere in the tree". Check BEFORE the
    # trailing-'/**' branch so patterns like '**/crypto/**' recurse on the
    # suffix 'crypto/**' correctly.
    if pattern.startswith("**/"):
        suffix_pat = pattern[3:]
        # '**/' also matches zero leading segments — try the bare suffix.
        if _match_path(path, suffix_pat):
            return True
        parts = path.split("/")
        for i in range(1, len(parts)):
            if _match_path("/".join(parts[i:]), suffix_pat):
                return True
        return False

    # Trailing '/**' — prefix must match, then zero-or-more trailing segments.
    if pattern.endswith("/**"):
        prefix_pat = pattern[:-3]
        # Recurse so prefix can itself contain '**'.
        if _match_path(path, prefix_pat):
            return True
        prefix_clean = prefix_pat.rstrip("/")
        return path.startswith(prefix_clean + "/")

    # General case: split on '/**/' — at least one segment must exist on
    # each side of every globstar. Recurse on the tail.
    head, _, tail = pattern.partition("/**/")
    path_parts = path.split("/")
    for split_idx in range(1, len(path_parts)):
        left = "/".join(path_parts[:split_idx])
        right = "/".join(path_parts[split_idx:])
        if fnmatch(left, head) and _match_path(right, tail):
            return True
    return False


class GstackReviewRouter:
    """Concrete :class:`ReviewRouter` for the gstack template.

    Constructor takes the compiled rule list (from
    ``TemplateDef.review.rules`` loaded at plugin load time; see Plan 04-11
    ``GstackSprintPlugin.contribute_review_routers``).

    ``match(diff_paths, state)`` returns the union of all matching
    ``rule.reviewers`` plus the mandatory ``"reviewer"`` floor, sorted for
    deterministic downstream behavior (golden tests must not flake).
    Failure of any single rule (e.g., malformed glob) is caught + logged
    per RFC 001 §4.3b req 4; the match loop continues with remaining rules
    so the floor + unaffected rules still fire.
    """

    def __init__(self, rules: list["ReviewRule"]) -> None:
        # Defensive copy so callers cannot mutate the rule list after
        # construction and skew downstream match() results.
        self._rules = list(rules)

    def match(self, diff_paths: list[str], state: "SprintState") -> list[str]:
        """Return the sorted union of matching rule.reviewers + floor.

        ``state`` is intentionally unused in the Plan 04-06 baseline. Future
        plans (04-10 dispatcher, 04-13 regression suite) may consult e.g.
        ``state.review_sha`` for per-SHA rule gating; the Protocol
        signature reserves the argument so we do not need to break the
        Protocol to add that behavior later.
        """
        del state  # reserved for future SHA-gated routing logic
        matched: set[str] = {_FLOOR_REVIEWER}
        for rule in self._rules:
            try:
                if self._rule_matches_any_path(rule, diff_paths):
                    matched.update(rule.reviewers)
            except Exception as exc:  # noqa: BLE001 — RFC 001 §4.3b req 4
                _logger.warning(
                    "GstackReviewRouter: rule pattern=%r raised during match: %s",
                    rule.pattern,
                    exc,
                )
                continue
        return sorted(matched)

    @staticmethod
    def _rule_matches_any_path(rule: "ReviewRule", diff_paths: list[str]) -> bool:
        """True when any diff path matches this rule's pattern."""
        for p in diff_paths:
            if _match_path(p, rule.pattern):
                return True
        return False
