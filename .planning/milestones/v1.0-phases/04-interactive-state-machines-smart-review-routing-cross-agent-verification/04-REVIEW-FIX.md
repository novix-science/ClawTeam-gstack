---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
fixed_at: 2026-04-22T12:34:25Z
review_path: .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 4: Code Review Fix Report

**Fixed at:** 2026-04-22T12:34:25Z
**Source review:** `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (CR-01, WR-01, WR-02 — Info findings not in scope)
- Fixed: 3
- Skipped: 0

## Fixed Issues

### CR-01: Review-phase dispatcher computes empty diff, silently disabling all smart-review routing

**Files modified:** `clawteam/sprint/review_phase.py`, `tests/test_review_phase_dispatch.py`
**Commit:** `d63ceba`
**Applied fix:**

Root cause: `dispatch_review_phase` called `_diff_paths(workspace, review_sha, review_sha, ...)` — the same SHA on both sides of the range — which always evaluates to an empty list. Every `ReviewRouter` saw `diff_paths=[]`, matched no rules, and `participants` degraded to just the `reviewer` floor for every sprint.

Fix: introduced a `_merge_base(workspace, head_sha, ...)` helper that resolves a real "before" SHA by trying, in order:

1. `git merge-base main <head_sha>`
2. `git merge-base master <head_sha>`
3. `git rev-parse <head_sha>~1` (last-commit fallback)

`_merge_base` explicitly rejects a same-SHA result so this regression cannot return. Empty-string on total failure, which the dispatcher treats as "no diff paths available" and falls back to the reviewer floor.

Wired into the dispatcher at the participant-collection site:

```python
base_sha = _merge_base(workspace, review_sha, subprocess_runner=subprocess_runner)
diff_paths = _diff_paths(workspace, base_sha, review_sha, subprocess_runner=subprocess_runner)
```

**Regression tests added** (all would have caught the same-SHA bug):

- `test_dispatcher_routes_security_on_auth_diff_via_real_router` — touches `src/auth/middleware.py` in a real git repo, loads the real `GstackReviewRouter` via `load_template("gstack")`, and asserts `"security"` lands in `participants`.
- `test_dispatcher_routes_designer_on_ui_diff_via_real_router` — touches `src/components/Button.tsx`, asserts `"designer"` participates.
- `test_dispatcher_produces_nonempty_diff_paths_end_to_end` — touches `package.json`, asserts `"dx-lead"` participates (this is the canonical anti-regression; the assertion fails iff `diff_paths` was empty).
- `test_merge_base_returns_empty_when_workspace_missing`
- `test_merge_base_resolves_against_main_branch`

End-to-end verified: with real `subprocess.run` against a real `git init`'d workspace, the dispatcher observes non-empty `diff_paths` and the real `GstackReviewRouter` pulls the expected per-signal reviewers. All 35 tests in `tests/test_review_phase_dispatch.py` pass.

### WR-01: Agreement-rate returns 1.0 for single-peer reviewers, guaranteeing SycophancyCascadeDetected false-positives

**Files modified:** `clawteam/sprint/review_phase.py`, `tests/test_review_phase_dispatch.py`
**Commit:** `b9874d4`
**Applied fix:**

Added a `len(rated) < 2` guard in `_compute_agreement_rate` so solo-peer dispatches return 0.0 instead of 1.0:

```python
if len(rated) < 2:
    return 0.0
```

A cascade requires agreement *between* reviewers — it is undefined with <2 peers. Before the guard, a solo `designer` peer with any findings yielded `rate=1.0 > 0.9 threshold` and emitted `SycophancyCascadeDetected` on every single-peer dispatch, which would have spammed Phase 7's `clawteam attend --summary`.

**Test adjustments:**
- Updated `test_agreement_rate_skips_exceptions` to the new semantics: the solo-survivor case (one Exception + one dict) now correctly returns 0.0.
- Added `test_agreement_rate_single_peer_returns_zero` — direct regression for the bug.
- Added `test_agreement_rate_all_exceptions_returns_zero` — two spawn failures yield 0 (no survivors, no cascade possible).

All 7 agreement-rate unit tests pass.

### WR-02: `sprint approve --notes` writes user text into YAML frontmatter without escaping

**Files modified:** `clawteam/cli/commands.py`, `tests/test_sprint_approve_cli.py`
**Commit:** `a9fee34`
**Applied fix:**

Replaced the hand-rolled `f"{key}: {value}"` loop with `yaml.safe_dump(...)`, which quotes and escapes every scalar correctly. PyYAML is already a ClawTeam transitive dependency (see `clawteam/team/envelope.py`), so no new dep is introduced.

```python
import yaml

frontmatter_yaml = yaml.safe_dump(
    frontmatter,
    sort_keys=False,
    allow_unicode=True,
    default_flow_style=False,
)
yaml_lines = ["---", frontmatter_yaml.rstrip("\n"), "---", ""]
```

The body still carries a free-form markdown copy of the note (prefixed by a blank-line separator so it cannot be absorbed into the preceding paragraph). The frontmatter copy is the machine-parsed source of truth; `ShipApprovalGate.check` continues to work because it already routes through `parse_frontmatter` (`yaml.safe_load`).

**Regression tests added** (7 parametrized round-trip cases + 1 end-to-end gate test):

`test_approve_notes_with_yaml_metacharacters_round_trip[...]` covers:
- newline + colon
- colon at top level
- `#` (YAML comment character)
- `---` (frontmatter delimiter)
- leading whitespace
- mixed single + double quotes
- tab-only

Each parameterization writes the artifact, re-parses via `parse_frontmatter`, and asserts `meta["approval_notes"] == note` exactly (byte-for-byte round-trip) while confirming the other required fields remain intact.

`test_approve_notes_with_metacharacters_passes_ship_approval_gate` is the end-to-end check: it writes a note containing `"line1: colon\nline2\n---\nnot-frontmatter"` and asserts `ShipApprovalGate().check(state)` returns `(True, "")`. Before the fix, the `---` inside the note would truncate the frontmatter and the gate would reject the artifact.

All 18 tests in `tests/test_sprint_approve_cli.py` pass.

## Skipped Issues

None — all three in-scope findings were fixed and verified.

## Verification Notes

- **Per-file syntax check:** `python -c "import ast; ast.parse(...)"` clean on all four modified files.
- **Targeted unit tests:** 35/35 pass in `test_review_phase_dispatch.py`; 18/18 pass in `test_sprint_approve_cli.py`.
- **Related suite pass:** 106/106 pass across `test_review_phase_dispatch.py`, `test_sprint_approve_cli.py`, `test_gstack_review_router.py`, `test_ship_approval_gate.py`, `test_gstack_plugin.py`.
- **Ruff:** no new warnings introduced by any fix (pre-existing warnings in `test_review_phase_dispatch.py` predate this iteration — confirmed by stash+check).
- **Full-suite delta:** baseline = 10 failed / 1546 passed; post-fix = 10 failed / 1561 passed. The 10 failures are all pre-existing test-ordering / plugin-registration race conditions unrelated to Phase 4 code (`test_evidence_schemas_phase5.py`, `test_gstack_plugin.py::test_seven_phases_registered_in_order`, etc.), confirmed by running each failing file in isolation (all pass) and by re-running the baseline at `7ba5c26` (same 10 failures). No collateral damage introduced.

---

_Fixed: 2026-04-22T12:34:25Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
