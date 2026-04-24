---
phase: 04
plan: 06
type: execute
wave: 1
depends_on: [01]
files_modified:
  - clawteam/templates/__init__.py
  - clawteam/harness/gstack_review_router.py
  - clawteam/templates/gstack.toml
  - clawteam/templates/gstack/prompts/review/reviewer.md
  - clawteam/templates/gstack/prompts/review/designer.md
  - clawteam/templates/gstack/prompts/review/security.md
  - clawteam/templates/gstack/prompts/review/dx-lead.md
  - tests/test_gstack_review_router.py
  - tests/test_templates.py
autonomous: true
requirements: [SPRINT-03, QUALITY-09, QUALITY-13]
must_haves:
  truths:
    - "TemplateDef additively grows a ReviewConfig field containing ReviewRule rows from `[[template.review.rules]]`."
    - "GstackReviewRouter.match(diff_paths, state) returns reviewers from matching rules, deduplicated + always including 'reviewer' floor."
    - "gstack.toml ships 6+ rule rows covering UI, crypto/auth, api, package.json signals."
    - "4 decorrelation prompt files exist under clawteam/templates/gstack/prompts/review/ each ≤ 2048 bytes."
    - "6 existing non-gstack templates continue to parse (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room) with no [template.review] block."
  artifacts:
    - path: "clawteam/templates/__init__.py"
      provides: "ReviewRule + ReviewConfig pydantic classes + extended _parse_toml"
      contains: "class ReviewRule(BaseModel)"
    - path: "clawteam/harness/gstack_review_router.py"
      provides: "GstackReviewRouter(ReviewRouter) with path-glob match + reviewer floor"
      contains: "class GstackReviewRouter"
      min_lines: 80
    - path: "clawteam/templates/gstack.toml"
      provides: "[template.review] + 6 [[template.review.rules]] rows"
      contains: "[[template.review.rules]]"
    - path: "clawteam/templates/gstack/prompts/review/reviewer.md"
      provides: "staff-eng-cross-cutting decorrelation anchor"
      contains: "staff-eng cross-cutting"
    - path: "clawteam/templates/gstack/prompts/review/designer.md"
      provides: "rubric-first decorrelation anchor"
      contains: "rubric-first"
    - path: "clawteam/templates/gstack/prompts/review/security.md"
      provides: "threat-model-first decorrelation anchor"
      contains: "threat-model-first"
    - path: "clawteam/templates/gstack/prompts/review/dx-lead.md"
      provides: "friction-first decorrelation anchor"
      contains: "friction-first"
  key_links:
    - from: "clawteam/templates/__init__.py (ReviewConfig)"
      to: "clawteam/harness/gstack_review_router.py (GstackReviewRouter)"
      via: "Router constructor accepts template.review rules"
    - from: "clawteam/harness/gstack_review_router.py"
      to: "clawteam/harness/review_router.py (ReviewRouter Protocol)"
      via: "match(diff_paths, state) signature matches Protocol"
    - from: "Plan 11 (GstackSprintPlugin)"
      to: "GstackReviewRouter"
      via: "contribute_review_routers() returns [GstackReviewRouter(...)]"
    - from: "Plan 11 (GstackSprintPlugin.contribute_prompts)"
      to: "prompts/review/<role>.md"
      via: "Phase=review + role in {reviewer, designer, security, dx-lead} appends decorrelation file"
---

<objective>
Ship the rules-first review router substrate and its decorrelation prompts:
- `TemplateDef` additively gains `ReviewRule` + `ReviewConfig` classes with `_parse_toml` extension (A5 adjusted — current parser silently drops `[[template.review.rules]]`).
- `clawteam/harness/gstack_review_router.py` implements `GstackReviewRouter` conforming to the Phase-1 `ReviewRouter` Protocol: path-glob matching over the declared rules, accumulation of all matching reviewers, mandatory "reviewer" floor appended.
- `clawteam/templates/gstack.toml` gains `[template.review]` header + 6+ `[[template.review.rules]]` rows covering UI/crypto/api/package signals.
- 4 decorrelation prompt files under `clawteam/templates/gstack/prompts/review/` × ≤2048 bytes each, anchored to the verbatim persona language from §04-CONTEXT specifics.

Purpose: SPRINT-03 (rule-based routing), QUALITY-09 (SHA-pinned consumer surface — Plan 10 wires the SHA), QUALITY-13 (per-persona decorrelation prompts). The 6 other templates that lack `[template.review]` must continue parsing unchanged (empty default = `ReviewConfig(rules=[])`).

Output: 2 new modules + 1 existing extended + 1 TOML file extended + 4 new prompt files + 2 test files.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md

<interfaces>
From clawteam/harness/review_router.py (entire file — Protocol):
```python
class ReviewRouter(Protocol):
    def match(self, diff_paths: list[str], state: "SprintState") -> list[str]:
        """Return additional reviewer role names for this diff.
        Raising is skipped with logged warning (per RFC 001 §4.3b req 4).
        Empty list = no additional reviewers.
        """
```

From clawteam/templates/__init__.py (lines 48-130, existing — TemplateDef + _parse_toml):
```python
class TemplateDef(BaseModel):
    name: str
    description: str = ""
    command: list[str] = ["claude"]
    backend: str = "tmux"
    leader: AgentDef
    agents: list[AgentDef] = []
    tasks: list[TaskDef] = []
    leader_role: str = ""
    phases: list[str] = []
    model_profile: dict[str, str] = {}
    memory: dict[str, str | bool] = {}

def _parse_toml(path: Path) -> TemplateDef:
    # Only reads: name, description, command, backend, leader, agents, tasks,
    # leader_role, phases, model_profile, memory. [template.review] silently dropped.
```

From clawteam/harness/freeze_registry.py (existing — glob pattern reference):
```python
# Uses fnmatch for pattern matching. Phase 4 glob engine decision in PLAN_PREP_NOTES.md.
```

Per PLAN_PREP_NOTES.md `## A-fnmatch`: CHOSEN ENGINE + import line must be copied verbatim from that file.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend TemplateDef with ReviewRule/ReviewConfig + extend _parse_toml</name>
  <files>clawteam/templates/__init__.py, tests/test_templates.py</files>
  <read_first>
    - clawteam/templates/__init__.py (entire file, 187 lines)
    - tests/test_gstack_template.py (Phase 3 pattern for template tests)
    - tests/test_config.py (existing template-parsing tests; find `_parse_toml` coverage)
    - clawteam/templates/*.toml (6 non-gstack templates — confirm none declare [template.review])
  </read_first>
  <behavior>
    - Test 1 (test_review_config_default_empty): `TemplateDef(name="x", leader=...).review == ReviewConfig()` — empty rules list, threshold 0.9.
    - Test 2 (test_template_without_review_block_parses): Parse one of the 6 existing templates (e.g., `software-dev.toml`) → no exception; `template.review.rules == []`.
    - Test 3 (test_gstack_template_review_rules_count): Parse gstack.toml (after Task 3 adds rules) → `len(template.review.rules) >= 6`.
    - Test 4 (test_review_rule_fields_pydantic_validated): `ReviewRule(pattern="x", reviewers=["a"])` succeeds; `ReviewRule(pattern="x", reviewers=[])` acceptable; `ReviewRule(pattern="")` rejected (pattern min_length=1).
    - Test 5 (test_sycophancy_threshold_parsed): Template with `[template.review] sycophancy_threshold = 0.85` → `template.review.sycophancy_threshold == 0.85`.
  </behavior>
  <action>
**Edit 1: `clawteam/templates/__init__.py`**:

a) Add `ReviewRule` + `ReviewConfig` pydantic classes BEFORE `TemplateDef` (insert after existing `TaskDef` class around line 42):

```python
class ReviewRule(BaseModel):
    """One routing rule for SmartReviewRouter (§04-CONTEXT D-04).

    Evaluated by :class:`clawteam.harness.gstack_review_router.GstackReviewRouter`.
    ``pattern`` is a path glob (engine selected per PLAN_PREP_NOTES A-fnmatch);
    ``reviewers`` are role names to add when any diff path matches. First-match
    WITH accumulation: a path matching two rules unions both reviewers.
    """

    pattern: str = Field(..., min_length=1, description="Path glob (e.g. 'src/components/**/*.tsx').")
    reviewers: list[str] = Field(default_factory=list, description="Roles to add on match.")
    signal: str = Field(default="", description="Optional classification tag (ui|api|crypto|security).")


class ReviewConfig(BaseModel):
    """Review-phase configuration (§04-CONTEXT D-04 / D-09).

    Default empty; only gstack.toml ships rules. Other 6 bundled templates
    omit the [template.review] block entirely.
    """

    sycophancy_threshold: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Agreement-rate threshold for sycophancy_cascade_detected event (D-09/D-20).",
    )
    rules: list[ReviewRule] = Field(default_factory=list)
```

b) Extend `TemplateDef` — add one new field after `memory`:
```python
    # Phase 4 (Plan 04-06, §04-CONTEXT D-04): review-phase routing + decorrelation
    # config. Default empty ReviewConfig keeps existing 6 templates BC-safe.
    review: ReviewConfig = ReviewConfig()
```

c) Extend `_parse_toml` — after `memory=tmpl.get("memory", {})` (around line 129), add review parsing:
```python
    # Phase 4 (Plan 04-06): parse optional [template.review] + [[template.review.rules]].
    review_tmpl = tmpl.get("review", {}) or {}
    raw_rules = review_tmpl.get("rules", []) or []
    review_config = ReviewConfig(
        sycophancy_threshold=float(review_tmpl.get("sycophancy_threshold", 0.9)),
        rules=[ReviewRule(**r) for r in raw_rules],
    )
```

d) Add `review=review_config` to the `TemplateDef(...)` constructor call (inside `return TemplateDef(...)` at the end of `_parse_toml`):
```python
    return TemplateDef(
        # ... existing args unchanged ...
        memory=tmpl.get("memory", {}),
        review=review_config,
    )
```

**Edit 2: `tests/test_templates.py`** — APPEND tests (create file if needed; otherwise append). Import pattern:

```python
# Phase 4 Plan 06 tests: TemplateDef review-config extension (§04-CONTEXT D-04 / A5)

import pytest

from clawteam.templates import (
    AgentDef,
    ReviewConfig,
    ReviewRule,
    TemplateDef,
    load_template,
)


def test_review_config_default_empty():
    leader = AgentDef(name="x", role="x")
    t = TemplateDef(name="t", leader=leader)
    assert isinstance(t.review, ReviewConfig)
    assert t.review.rules == []
    assert t.review.sycophancy_threshold == 0.9


def test_software_dev_template_parses_without_review_block():
    t = load_template("software-dev")
    assert isinstance(t.review, ReviewConfig)
    assert t.review.rules == []


def test_code_review_template_parses_without_review_block():
    t = load_template("code-review")
    assert t.review.rules == []


def test_review_rule_pattern_required():
    with pytest.raises(Exception):  # noqa: B017 — pydantic ValidationError
        ReviewRule(pattern="", reviewers=["designer"])


def test_review_rule_reviewers_default_empty():
    r = ReviewRule(pattern="x")
    assert r.reviewers == []
    assert r.signal == ""


def test_review_config_sycophancy_threshold_range():
    with pytest.raises(Exception):  # noqa: B017
        ReviewConfig(sycophancy_threshold=1.5)
    with pytest.raises(Exception):
        ReviewConfig(sycophancy_threshold=-0.1)


def test_gstack_template_has_review_rules():
    """Gstack template ships with 6+ [[template.review.rules]] rows."""
    t = load_template("gstack")
    assert len(t.review.rules) >= 6
    # Floor check: rules must name at least one of the decorrelation roles.
    all_reviewers = {r for rule in t.review.rules for r in rule.reviewers}
    assert {"designer", "security", "dx-lead"}.issubset(all_reviewers)
```
  </action>
  <verify>
    <automated>pytest tests/test_templates.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class ReviewRule(BaseModel)" clawteam/templates/__init__.py
    - grep -q "class ReviewConfig(BaseModel)" clawteam/templates/__init__.py
    - grep -q 'review_tmpl = tmpl.get("review"' clawteam/templates/__init__.py
    - grep -q "review: ReviewConfig = ReviewConfig()" clawteam/templates/__init__.py
    - pytest tests/test_templates.py -x -q exits 0 (7 tests; test_gstack_template_has_review_rules will initially fail until Task 3 lands — acceptable intermediate state, run after Task 3)
    - pytest tests/test_gstack_template.py tests/test_config.py -x -q stays green
  </acceptance_criteria>
  <done>TemplateDef + _parse_toml extended; 6 existing templates still parse; ReviewConfig defaults preserve BC</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement GstackReviewRouter with glob match + reviewer floor</name>
  <files>clawteam/harness/gstack_review_router.py, tests/test_gstack_review_router.py</files>
  <read_first>
    - clawteam/harness/review_router.py (entire file — Protocol)
    - clawteam/templates/__init__.py (after Task 1 — ReviewRule / ReviewConfig)
    - clawteam/sprint/state.py (after Plan 02 — review_sha field)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md (CHOSEN ENGINE + function signature from `## A-fnmatch`)
    - clawteam/harness/freeze_registry.py (glob usage for consistency reference)
  </read_first>
  <behavior>
    - Test 1 (test_reviewer_always_participates): match(diff_paths=[], state=...) returns ["reviewer"] — floor applies even on empty diff.
    - Test 2 (test_ui_diff_pulls_designer): diff_paths=["src/components/Button.tsx"] matches rule {pattern="src/components/**/*.tsx", reviewers=["designer"]} → returns contains {"designer", "reviewer"}.
    - Test 3 (test_crypto_diff_pulls_security): diff_paths=["lib/crypto/aes.py"] → {"security", "reviewer"}.
    - Test 4 (test_api_and_package_pull_dx_lead): diff_paths=["app/api/users.ts", "package.json"] → {"dx-lead", "reviewer"}.
    - Test 5 (test_union_of_matches_accumulation): diff_paths=["src/components/X.tsx", "app/api/Y.ts"] → {"designer", "dx-lead", "reviewer"}.
    - Test 6 (test_no_match_floor_only): diff_paths=["README.md"] → {"reviewer"}.
    - Test 7 (test_deduplication): Two rules that both add "designer" on different patterns → no duplicate.
    - Test 8 (test_exception_in_pattern_match_skipped): A rule with an invalid glob pattern does NOT crash match(); logs warning (caplog).
    - Test 9 (test_no_duplicate_reviewer_if_rule_adds_it): Rule adds "reviewer" on match; result still contains "reviewer" exactly once.
    - Test 10 (test_match_returns_sorted_deterministic): Result is deterministic (sorted / stable) so golden tests don't flake.
  </behavior>
  <action>
Create `clawteam/harness/gstack_review_router.py`:

```python
"""GstackReviewRouter — concrete ReviewRouter implementation for the gstack template.

§04-CONTEXT D-04 / D-06 / §04-REQUIREMENTS SPRINT-03. Path-glob rules with
first-match-WITH-accumulation: a diff path matching N rules pulls in the
union of all their reviewer sets. The ``reviewer`` role is always appended
as the cross-cutting floor (QUALITY-13 decorrelation anchor).

Glob engine: {CHOSEN_ENGINE_FROM_PLAN_PREP} — see PLAN_PREP_NOTES A-fnmatch.

Delete invariant (§04-CONTEXT <domain>): file is prefixed ``gstack_`` so removing
``clawteam/templates/gstack.toml`` + this router + GstackSprintPlugin leaves the
rest of the codebase unchanged. Non-gstack templates never instantiate this class.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# ── Glob engine selection ─────────────────────────────────────────────
# Planner must verify via PLAN_PREP_NOTES.md `## A-fnmatch` which engine
# handles `**` doublestar correctly. Default below is the shim; switch to
# fnmatch.fnmatch OR PurePosixPath.match per PLAN_PREP_NOTES decision.

from pathlib import PurePosixPath

if TYPE_CHECKING:
    from clawteam.sprint.state import SprintState
    from clawteam.templates import ReviewRule

_logger = logging.getLogger(__name__)

_FLOOR_REVIEWER = "reviewer"


def _match_path(path: str, pattern: str) -> bool:
    """Glob match with `**` doublestar support.

    Implementation follows PLAN_PREP_NOTES.md A-fnmatch decision:
      - PurePosixPath.match handles `**` in Python 3.13+.
      - Fallback: split `**/` on pattern and prefix/suffix fnmatch.

    This function must return identical results for both engines on the
    fixture set in tests/fixtures/review_routing/*.diff (Plan 04-13).
    """
    # Primary: PurePosixPath.match (Python 3.13+ for **)
    try:
        if PurePosixPath(path).match(pattern):
            return True
    except (ValueError, NotImplementedError):
        pass

    # Fallback: fnmatch-based shim for `**`. Split pattern on "/**/" and
    # match head segment against the corresponding prefix + the remainder
    # as a recursive search.
    import fnmatch as _fnmatch

    if "**" not in pattern:
        return _fnmatch.fnmatch(path, pattern)

    # Pattern with "**": transform into regex-equivalent via split on "/**/"
    # into (head, tail); head must prefix-match the path, tail must suffix-match.
    # Degenerate cases:
    #   "**/foo"     -> tail = "foo", head = ""
    #   "foo/**"     -> head = "foo/", tail = ""
    #   "a/**/b"     -> head = "a/", tail = "/b"
    if pattern.startswith("**/"):
        tail = pattern[3:]
        # path must end with a segment matching tail
        segments = path.split("/")
        for i in range(len(segments)):
            candidate = "/".join(segments[i:])
            if _fnmatch.fnmatch(candidate, tail):
                return True
        return False
    if pattern.endswith("/**"):
        head = pattern[:-3]
        return path == head or path.startswith(head + "/")
    if "/**/" in pattern:
        head, tail = pattern.split("/**/", 1)
        if not path.startswith(head + "/") and path != head:
            return False
        # path suffix after head must suffix-match tail recursively
        suffix = path[len(head) + 1 :] if path.startswith(head + "/") else ""
        return _match_path(suffix, tail) if tail else True

    # Otherwise fall back to flat fnmatch
    return _fnmatch.fnmatch(path, pattern)


class GstackReviewRouter:
    """Concrete ReviewRouter for the gstack template.

    Constructor takes the compiled rule list (from ``TemplateDef.review.rules``
    loaded at plugin load time; see Plan 04-11 ``GstackSprintPlugin.contribute_review_routers``).

    ``match(diff_paths, state)`` returns the union of all matching rule.reviewers
    plus the mandatory ``"reviewer"`` floor. Deterministic order (sorted).
    Failure of any single rule (e.g., invalid glob) is caught + logged; the
    match continues with remaining rules.
    """

    def __init__(self, rules: list["ReviewRule"]) -> None:
        self._rules = list(rules)

    def match(self, diff_paths: list[str], state: "SprintState") -> list[str]:
        matched: set[str] = {_FLOOR_REVIEWER}
        for rule in self._rules:
            try:
                if self._rule_matches_any_path(rule, diff_paths):
                    matched.update(rule.reviewers)
            except Exception as exc:  # noqa: BLE001 — skip broken rule per RFC 001 §4.3b req 4
                _logger.warning(
                    "GstackReviewRouter: rule pattern=%r raised during match: %s",
                    rule.pattern,
                    exc,
                )
                continue
        return sorted(matched)

    @staticmethod
    def _rule_matches_any_path(rule: "ReviewRule", diff_paths: list[str]) -> bool:
        for p in diff_paths:
            if _match_path(p, rule.pattern):
                return True
        return False
```

Create `tests/test_gstack_review_router.py`:

```python
"""Unit tests for GstackReviewRouter (Plan 04-06 + SPRINT-03)."""

from __future__ import annotations

from types import SimpleNamespace

from clawteam.harness.gstack_review_router import GstackReviewRouter, _match_path
from clawteam.templates import ReviewRule


def _rules_canonical():
    return [
        ReviewRule(pattern="src/components/**/*.tsx", reviewers=["designer"], signal="ui"),
        ReviewRule(pattern="**/*.css",                reviewers=["designer"], signal="ui"),
        ReviewRule(pattern="src/auth/**",              reviewers=["security"], signal="crypto"),
        ReviewRule(pattern="**/crypto/**",             reviewers=["security"], signal="crypto"),
        ReviewRule(pattern="app/api/**",               reviewers=["dx-lead"], signal="api"),
        ReviewRule(pattern="package.json",             reviewers=["dx-lead"], signal="api"),
    ]


def _state():
    return SimpleNamespace(workspace_branch="/tmp/x", review_sha="deadbeef" * 5)


# ── _match_path semantics (foundation) ──────────────────────────────

def test_match_path_literal():
    assert _match_path("package.json", "package.json") is True
    assert _match_path("lib/package.json", "package.json") is False


def test_match_path_doublestar_in_middle():
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
    assert _match_path("src/cryptonot/a.ts", "**/crypto/**") is False


def test_match_path_doublestar_suffix_only():
    assert _match_path("a.css", "**/*.css") is True
    assert _match_path("lib/style.css", "**/*.css") is True
    assert _match_path("app/deep/nested/s.css", "**/*.css") is True


# ── Router match() contract ──────────────────────────────────────────

def test_reviewer_always_participates():
    r = GstackReviewRouter(_rules_canonical())
    assert r.match([], _state()) == ["reviewer"]


def test_ui_diff_pulls_designer():
    r = GstackReviewRouter(_rules_canonical())
    result = r.match(["src/components/Button.tsx"], _state())
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
    result = r.match(["app/api/users.ts", "package.json"], _state())
    assert set(result) == {"dx-lead", "reviewer"}


def test_union_of_matches_accumulation():
    r = GstackReviewRouter(_rules_canonical())
    result = r.match(["src/components/X.tsx", "app/api/Y.ts"], _state())
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
    """Broken glob pattern does not crash match(); logged + skipped."""
    rules = [
        ReviewRule(pattern="[invalid", reviewers=["broken"]),
        ReviewRule(pattern="**/*.tsx", reviewers=["designer"]),
    ]
    r = GstackReviewRouter(rules)
    with caplog.at_level("WARNING"):
        result = r.match(["src/Button.tsx"], _state())
    # Designer still pulled despite broken rule.
    assert "designer" in result
    assert "reviewer" in result


def test_rule_adding_reviewer_does_not_duplicate():
    rules = [ReviewRule(pattern="**/*.py", reviewers=["reviewer"])]
    r = GstackReviewRouter(rules)
    result = r.match(["a.py"], _state())
    assert result.count("reviewer") == 1


def test_match_returns_sorted_deterministic():
    r = GstackReviewRouter(_rules_canonical())
    result1 = r.match(["src/components/X.tsx", "app/api/Y.ts", "**/crypto/z.py"], _state())
    result2 = r.match(["src/components/X.tsx", "app/api/Y.ts", "**/crypto/z.py"], _state())
    assert result1 == result2  # deterministic
    assert result1 == sorted(result1)  # sorted


def test_protocol_conformance():
    from clawteam.harness.review_router import ReviewRouter
    r = GstackReviewRouter([])
    # Structural type check: exists match() method matching Protocol.
    assert callable(r.match)
    # match signature accepts diff_paths + state
    result = r.match([], _state())
    assert isinstance(result, list)
```
  </action>
  <verify>
    <automated>pytest tests/test_gstack_review_router.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q "class GstackReviewRouter" clawteam/harness/gstack_review_router.py
    - grep -q "def match.*diff_paths.*state" clawteam/harness/gstack_review_router.py
    - grep -q "_FLOOR_REVIEWER" clawteam/harness/gstack_review_router.py
    - wc -l clawteam/harness/gstack_review_router.py returns >= 80
    - pytest tests/test_gstack_review_router.py -x -q exits 0 with all match + glob tests passing
  </acceptance_criteria>
  <done>GstackReviewRouter + _match_path glob engine ship; 15+ tests pass including exception-handling + dedup + floor</done>
</task>

<task type="auto">
  <name>Task 3: Extend gstack.toml with [template.review] + 6 rules; create 4 decorrelation prompt files</name>
  <files>clawteam/templates/gstack.toml, clawteam/templates/gstack/prompts/review/reviewer.md, clawteam/templates/gstack/prompts/review/designer.md, clawteam/templates/gstack/prompts/review/security.md, clawteam/templates/gstack/prompts/review/dx-lead.md</files>
  <read_first>
    - clawteam/templates/gstack.toml (entire file — do NOT disturb existing [template.*] sections)
    - clawteam/templates/gstack/prompts/pm.md (reference for SIGNATURE trailer convention)
    - clawteam/templates/gstack/prompts/designer.md (reference for persona language)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md (§specifics decorrelation anchors verbatim)
  </read_first>
  <action>
**Append** to `clawteam/templates/gstack.toml` (do NOT modify existing [template], [template.model_profile], [template.memory], [template.leader], [[template.agents]] sections). Insertion at end of file:

```toml

# ── Phase 4 (Plan 04-06, §04-CONTEXT D-04): review-phase routing rules.
# Consumed by clawteam.harness.gstack_review_router.GstackReviewRouter at
# plugin load. `reviewer` role ALWAYS participates (SPRINT-03 floor);
# matching rules accumulate additional reviewers per path glob.

[template.review]
# §04-CONTEXT D-09 / D-20: agreement-rate threshold for the sycophancy
# cascade alarm. Default 0.9 per research; tune if teams see cascades fire
# on legitimate unanimous verdicts.
sycophancy_threshold = 0.9

[[template.review.rules]]
pattern = "src/components/**/*.tsx"
reviewers = ["designer"]
signal = "ui"

[[template.review.rules]]
pattern = "**/*.css"
reviewers = ["designer"]
signal = "ui"

[[template.review.rules]]
pattern = "src/auth/**"
reviewers = ["security"]
signal = "crypto"

[[template.review.rules]]
pattern = "**/crypto/**"
reviewers = ["security"]
signal = "crypto"

[[template.review.rules]]
pattern = "app/api/**"
reviewers = ["dx-lead"]
signal = "api"

[[template.review.rules]]
pattern = "package.json"
reviewers = ["dx-lead"]
signal = "api"
```

**Create 4 decorrelation prompt files.** Each ≤ 2048 bytes. Use the verbatim anchors from §04-CONTEXT specifics.

`clawteam/templates/gstack/prompts/review/reviewer.md`:
```markdown
# reviewer — Review-phase decorrelation supplement

<!-- Phase 4 Plan 04-06. Appended to prompts/reviewer.md when the Review-phase
     dispatcher (Plan 04-10) spawns this persona. Main prompt 4 KB budget
     (Phase 3 D-14) is independent; this decorrelation supplement has a
     separate 2 KB budget. -->

## Decorrelation anchor

You are staff-eng cross-cutting. Focus on production-bug patterns, data
integrity, and cross-module coupling. Ignore prose style. Do NOT defer to
peer reviewers — write your own finding first, then aggregate peers.

## Ordering

1. Load the pinned diff at review_sha (provided by the dispatcher).
2. Re-examine the CI-passes-but-prod-fails patterns from your main /review
   rubric (race conditions, env var leaks, timezone assumptions, unbounded
   retries, silent exception swallowing, N+1 queries, unindexed lookups,
   null/empty-list handling).
3. Emit findings one hypothesis per turn via `reviewer_hypothesis_index`.
4. Only after all peer reviewers (designer/security/dx-lead) complete, read
   their reports and synthesize the aggregated `review-report.md` with
   your findings PLUS their findings, tagged by persona.

## What you do NOT do here

- Do NOT score the design rubric (designer's job).
- Do NOT trace threat models (security's job).
- Do NOT measure TTHW (dx-lead's job).
- Do NOT rewrite findings that clearly belong to another persona; just
  surface them to the synthesis.

## Sycophancy discipline

If you find yourself echoing a peer's finding, STOP. Re-read the diff and
state YOUR finding first. If you genuinely agree after independent
review, say so in the aggregation with evidence — but do not mirror-echo.

SIGNATURE: gstack-role:reviewer rubric:review-decorrelation envelope-version:1
```

`clawteam/templates/gstack/prompts/review/designer.md`:
```markdown
# designer — Review-phase decorrelation supplement

<!-- Phase 4 Plan 04-06. Appended to prompts/designer.md in Review phase. -->

## Decorrelation anchor

You are rubric-first. Score against ALL 7 `/plan-design-review` dimensions
(information architecture, interaction state coverage, user journey, AI-slop
risk, design system alignment, responsive/accessibility, unresolved
decisions). Flag AI-slop patterns aggressively: stock iconography, generic
gradients, inconsistent spacing, placeholder lorem-ipsum shapes, emoji-as-
primary-icon, stock-photo hero images, mid-gray-only palette, system-font
fallback without brand font.

## Ordering

1. Load the pinned diff. Identify UI files (`src/components/**/*.tsx`,
   `**/*.css`, storybook/.stories.tsx).
2. Emit scores one pass per turn via `designer_rubric_dimension`.
3. Do NOT reference peer reviewer drafts — they have not run yet (they run
   in parallel with you on their own anchors).
4. End with pass/fail verdict per the 0-10 gate (fail < 7 on any dimension).

## What you do NOT do here

- Do NOT raise security findings (security's job).
- Do NOT raise API-friction findings (dx-lead's job).
- Do NOT propose fixes — that is engineer's follow-up sprint. State the
  issue + preferred design pattern.

SIGNATURE: gstack-role:designer rubric:review-decorrelation envelope-version:1
```

`clawteam/templates/gstack/prompts/review/security.md`:
```markdown
# security — Review-phase decorrelation supplement

<!-- Phase 4 Plan 04-06. Appended to prompts/security.md in Review phase. -->

## Decorrelation anchor

You are threat-model-first. Apply STRIDE + OWASP Top 10. Exclude the 22
`/cso` false-positives declared in your main prompt (they remain out-of-
scope here). Only flag findings with confidence ≥ 8/10.

## Ordering

1. Load the pinned diff. Identify security-relevant files (`src/auth/**`,
   `**/crypto/**`, files importing `crypto`, `hashlib`, `jwt`, `bcrypt`).
2. Run STRIDE per touched surface (spoofing, tampering, repudiation,
   information disclosure, denial of service, elevation of privilege).
3. Cross-reference OWASP Top 10 (injection, auth, sensitive-data exposure,
   XXE, broken access control, mis-config, XSS, deserialization, known-
   vulnerable components, insufficient logging).
4. Emit findings via `security_confidence`. Findings < 8/10 go to the
   advisory register, not the blocker register.

## What you do NOT do here

- Do NOT score design rubric (designer's job).
- Do NOT raise TTHW friction (dx-lead's job).
- Do NOT raise generic code-quality findings (reviewer's job).

## False-positive exclusions (verbatim from main /cso prompt)

Keep the 22 exclusions from your main prompt in mind — do not repeat
findings already filtered there.

SIGNATURE: gstack-role:security rubric:review-decorrelation envelope-version:1
```

`clawteam/templates/gstack/prompts/review/dx-lead.md`:
```markdown
# dx-lead — Review-phase decorrelation supplement

<!-- Phase 4 Plan 04-06. Appended to prompts/dx-lead.md in Review phase. -->

## Decorrelation anchor

You are friction-first. Trace the TTHW (time-to-hello-world) of each user-
facing change. Flag any API surface that adds steps without removing steps.
Your audience is the developer who will integrate against this diff
tomorrow.

## Ordering

1. Load the pinned diff. Identify API surface (`app/api/**`, public Python
   modules, exported TypeScript, changes to `package.json` dependencies).
2. For each public-surface change, time-box a TTHW walk: "from zero repo
   knowledge, what is the shortest path to hello-world on this change?"
3. Flag: added required fields, removed optional fields, renamed
   functions without deprecation shim, new env-var requirements without
   `clawteam doctor` / `.env.example` entries, new peer dependencies.
4. Emit findings via `dx_friction_index` (0 = none, 1-3 = minor, 4-5 =
   blocker).

## What you do NOT do here

- Do NOT score design rubric.
- Do NOT raise security findings.
- Do NOT propose architecture changes (eng-mgr's job in plan phase).
- Limit scope to the DIFF — do NOT audit the whole repo's DX.

SIGNATURE: gstack-role:dx-lead rubric:review-decorrelation envelope-version:1
```

**Budget check:** After writing, verify each file ≤ 2048 bytes via `wc -c`.
  </action>
  <verify>
    <automated>wc -c clawteam/templates/gstack/prompts/review/reviewer.md clawteam/templates/gstack/prompts/review/designer.md clawteam/templates/gstack/prompts/review/security.md clawteam/templates/gstack/prompts/review/dx-lead.md | awk 'NR<=4 { if ($1 > 2048) { exit 1 } } END { print "all under 2KB" }'</automated>
  </verify>
  <acceptance_criteria>
    - ls clawteam/templates/gstack/prompts/review/reviewer.md succeeds
    - ls clawteam/templates/gstack/prompts/review/designer.md succeeds
    - ls clawteam/templates/gstack/prompts/review/security.md succeeds
    - ls clawteam/templates/gstack/prompts/review/dx-lead.md succeeds
    - Each file ≤ 2048 bytes (wc -c)
    - grep "staff-eng cross-cutting" clawteam/templates/gstack/prompts/review/reviewer.md succeeds
    - grep "rubric-first" clawteam/templates/gstack/prompts/review/designer.md succeeds
    - grep "threat-model-first" clawteam/templates/gstack/prompts/review/security.md succeeds
    - grep "friction-first" clawteam/templates/gstack/prompts/review/dx-lead.md succeeds
    - grep -c "\[\[template.review.rules\]\]" clawteam/templates/gstack.toml == 6
    - grep "sycophancy_threshold = 0.9" clawteam/templates/gstack.toml succeeds
    - pytest tests/test_templates.py::test_gstack_template_has_review_rules -x exits 0 (now populated)
  </acceptance_criteria>
  <done>gstack.toml has 6 routing rules; 4 decorrelation prompts exist under 2 KB each; all contain verbatim persona anchors</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| TOML-declared glob patterns ↔ router execution | Attacker-controlled gstack.toml could declare glob that forever matches → everyone pulled into review |
| Decorrelation prompt content ↔ agent behavior | Prompt supplements are appended verbatim to role prompts; malformed markdown won't crash but could confuse parser |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-17 | D (DoS) | Over-broad glob (`**`) | accept | Template is opt-in; pathological globs pull everyone but don't crash; operator tunes in their own team |
| T-04-18 | T (Tampering) | Broken glob pattern | mitigate | Try/except around each rule match in router; logged + skipped. test_exception_in_pattern_match_skipped enforces |
| T-04-19 | I (Information disclosure) | Decorrelation prompt content | accept | Prompts are public template content; committed to git |
| T-04-20 | E (Elevation of privilege) | Attacker adds rule that pulls no reviewers | mitigate | `reviewer` floor is not negotiable via rules; router unconditionally appends |
</threat_model>

<verification>
Plan 06 integration checks:
- [ ] `pytest tests/test_gstack_review_router.py tests/test_templates.py -x -q` exits 0
- [ ] `pytest tests/test_gstack_template.py -x -q` passes (Phase 3 template-shape tests unaffected)
- [ ] All 6 non-gstack templates still parse: `python3 -c "from clawteam.templates import load_template; [load_template(t) for t in ['software-dev','hedge-fund','code-review','harness-default','research-paper','strategy-room']]"` exits 0
- [ ] `grep -l "staff-eng cross-cutting\|rubric-first\|threat-model-first\|friction-first" clawteam/templates/gstack/prompts/review/*.md | wc -l` == 4
</verification>

<success_criteria>
Plan 06 ships when:
- [ ] `TemplateDef.review: ReviewConfig` field lands with default empty
- [ ] `_parse_toml` reads `[[template.review.rules]]` rows into pydantic instances
- [ ] `GstackReviewRouter` conforms to `ReviewRouter` Protocol; 15+ tests pass
- [ ] `_match_path` handles `**` doublestar correctly (both engines verified)
- [ ] `gstack.toml` ships with 6 routing rules + `sycophancy_threshold = 0.9`
- [ ] 4 decorrelation prompts exist, each ≤ 2048 bytes, each anchored with verbatim persona language
- [ ] 6 non-gstack templates still parse unchanged
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-06-review-router-and-template-extension-SUMMARY.md` with:
- LOC counts (router + template extension)
- Decorrelation prompt byte sizes (must all ≤ 2048)
- Test pass/fail table keyed by SPRINT-03 sub-requirement
- Any engine-selection surprises vs PLAN_PREP_NOTES A-fnmatch decision
</output>
