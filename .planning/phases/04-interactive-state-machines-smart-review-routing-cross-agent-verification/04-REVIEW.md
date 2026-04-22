---
phase: 04-interactive-state-machines-smart-review-routing-cross-agent-verification
reviewed: 2026-04-22T12:22:06Z
depth: standard
files_reviewed: 60
files_reviewed_list:
  - clawteam/cli/commands.py
  - clawteam/events/types.py
  - clawteam/harness/cross_agent_verification_gate.py
  - clawteam/harness/gstack_review_router.py
  - clawteam/harness/ship_approval_gate.py
  - clawteam/plugins/base.py
  - clawteam/plugins/gstack_sprint_plugin.py
  - clawteam/plugins/manager.py
  - clawteam/sprint/conductor.py
  - clawteam/sprint/review_phase.py
  - clawteam/sprint/state.py
  - clawteam/templates/__init__.py
  - clawteam/templates/gstack.toml
  - clawteam/templates/gstack/prompts/designer.md
  - clawteam/templates/gstack/prompts/pm.md
  - clawteam/templates/gstack/prompts/review/designer.md
  - clawteam/templates/gstack/prompts/review/dx-lead.md
  - clawteam/templates/gstack/prompts/review/reviewer.md
  - clawteam/templates/gstack/prompts/review/security.md
  - clawteam/templates/gstack/prompts/reviewer.md
  - clawteam/templates/gstack/skills/__init__.py
  - clawteam/templates/gstack/skills/design_consultation/__init__.py
  - clawteam/templates/gstack/skills/design_consultation/state.py
  - clawteam/templates/gstack/skills/investigate/__init__.py
  - clawteam/templates/gstack/skills/investigate/state.py
  - clawteam/templates/gstack/skills/office_hours/__init__.py
  - clawteam/templates/gstack/skills/office_hours/state.py
  - clawteam/templates/gstack/verifiers/__init__.py
  - clawteam/templates/gstack/verifiers/design_doc_covers_forcing_qs.py
  - clawteam/templates/gstack/verifiers/test_report_matches_diff.py
  - tests/fixtures/gstack_state_machines/design-consultation.transitions.json
  - tests/fixtures/gstack_state_machines/investigate.transitions.json
  - tests/fixtures/gstack_state_machines/office-hours.transitions.json
  - tests/fixtures/review_routing/auth_middleware_rewrite.diff
  - tests/fixtures/review_routing/cross_cutting_refactor.diff
  - tests/fixtures/review_routing/crypto_test_file.diff
  - tests/fixtures/review_routing/expected_routing.json
  - tests/fixtures/review_routing/generated_migration.diff
  - tests/fixtures/review_routing/mixed_ui_and_api.diff
  - tests/fixtures/review_routing/package_json_dep_bump.diff
  - tests/fixtures/review_routing/renamed_ui_component.diff
  - tests/fixtures/review_routing/whitespace_only.diff
  - tests/test_adversarial_routing.py
  - tests/test_cross_agent_verification_gate.py
  - tests/test_cross_agent_verifiers.py
  - tests/test_design_consultation_state_machine.py
  - tests/test_event_types_phase4.py
  - tests/test_gstack_plugin.py
  - tests/test_gstack_review_router.py
  - tests/test_gstack_role_prompts.py
  - tests/test_investigate_state_machine.py
  - tests/test_mid_review_push_integration.py
  - tests/test_office_hours_state_machine.py
  - tests/test_plugins.py
  - tests/test_review_phase_dispatch.py
  - tests/test_ship_approval_gate.py
  - tests/test_sprint_approve_cli.py
  - tests/test_sprint_state.py
  - tests/test_state_machine_goldens.py
  - tests/test_templates.py
findings:
  critical: 1
  warning: 2
  info: 5
  total: 8
status: issues_found
---

# Phase 4: Code Review Report

**Reviewed:** 2026-04-22T12:22:06Z
**Depth:** standard
**Files Reviewed:** 60
**Status:** issues_found

## Summary

Phase 4 ships the interactive state-machine substrate (office-hours, design-consultation, investigate), the smart review router (`GstackReviewRouter` + gstack.toml rules), cross-agent verification (`CrossAgentVerificationGate` + two verifier fns), the ship-approval gate and `clawteam sprint approve` CLI, and the review-phase dispatcher that ties them together. The code is well-documented, consistently defensive (broad excepts are noqa'd with documented reasons), and paths/identifiers go through the shared `validate_identifier` + `ensure_within_root` clamps — the T-04-22 path-traversal posture is solid across the three new state machines and the ship-approval flow.

The standout finding is a logic bug in the review-phase dispatcher that silently defeats the whole smart-review-routing feature: `dispatch_review_phase` computes the diff with `<review_sha>..<review_sha>` (same SHA on both sides), which `git diff` always evaluates to an empty list. Routers therefore see `diff_paths=[]` and never match any rules, so only the `reviewer` floor ever participates regardless of what touched UI/crypto/API. The test suite masks this because every dispatcher test uses a `_Router` mock that ignores `diff_paths` and returns a hardcoded list, and the integration test never exercises the real `GstackReviewRouter` through the dispatcher.

Two warnings flag real runtime issues: (a) the sycophancy-cascade agreement-rate math returns 1.0 for a single peer reviewer with any findings, so solo-reviewer dispatches always emit a SycophancyCascadeDetected event, and (b) the `sprint approve --notes` path interpolates user text into YAML frontmatter without escaping, so a note containing a newline, colon, or `---` corrupts the artifact. The info items are mostly documentation/consistency drift.

No security-critical findings (hardcoded secrets, shell=True, eval/exec, path traversal, injection). The subprocess calls in `review_phase.py` and `commands.py:sprint_approve` use `shell=False` with explicit cwd + timeout per the T-04-31 pattern.

## Critical Issues

### CR-01: Review-phase dispatcher computes empty diff, silently disabling all smart-review routing

**File:** `clawteam/sprint/review_phase.py:192`
**Issue:** `dispatch_review_phase` calls `_diff_paths(workspace, review_sha, review_sha, ...)` with the same SHA on both sides of the diff range. `_diff_paths` then runs `git diff --name-only <sha>..<sha>`, which always returns an empty list because there are zero commits in the range `A..A`. Every router then sees `diff_paths=[]` and matches nothing; `participants` degrades to just the `"reviewer"` floor for every sprint, regardless of what files the sprint touched. The entire SmartReviewRouter / `gstack.toml` rule set (ui, crypto, api, package.json routing) ships dead in production. Existing tests miss this because `tests/test_review_phase_dispatch.py` uses a `_Router` stub (`_Router.match` at line 86-87) that ignores `diff_paths` and returns hardcoded roles, so the dispatcher integration path is never actually tested against a real router.

The intended semantics (per `04-CONTEXT.md` D-05/D-06 and the router docstring's "diff_paths = git diff <review_sha>..<review_sha>" comment) is almost certainly to diff the review SHA against the sprint's merge-base / parent branch (e.g. `main..review_sha`), not `review_sha..review_sha`.

**Fix:**
```python
# Option A: diff against the sprint's base branch. Resolve the base with
# `git merge-base main <review_sha>` or from a new `state.base_sha` field.
base_sha = _merge_base(workspace, review_sha, subprocess_runner=subprocess_runner)
diff_paths = _diff_paths(workspace, base_sha, review_sha,
                         subprocess_runner=subprocess_runner)

# Option B (cheaper, wider scope — diff the full working-tree touch-list):
# git diff --name-only HEAD~1..<review_sha>  OR  git show --name-only <review_sha>
# if "last commit" is the intended scope.

# Minimum fix: add a base_sha resolver, ban the same-SHA call, and add a
# test that drives the real GstackReviewRouter end-to-end through
# dispatch_review_phase so this regression cannot return.
```
Also add an integration test in `tests/test_review_phase_dispatch.py` that uses the real `GstackReviewRouter` (load `gstack.toml` rules via `load_template`) and asserts that diff paths like `src/auth/middleware.py` actually pull `security` into `participants`.

## Warnings

### WR-01: Agreement-rate returns 1.0 for single-peer reviewers, guaranteeing SycophancyCascadeDetected false-positives

**File:** `clawteam/sprint/review_phase.py:97-129`
**Issue:** `_compute_agreement_rate` returns `matched / max_len` with no guard on `len(rated) < 2`. For a solo peer reviewer with any non-empty findings list, `rated = [["high"]]`, `max_len = 1`, the loop sees `len(values) == len(rated) == 1` and `len(set(values)) == 1`, so `matched = 1` and the rate is `1.0`. That's `> sycophancy_threshold` (default 0.9) every time, so `dispatch_review_phase` emits `SycophancyCascadeDetected` on line 240-247 for every single-peer dispatch. A cascade requires *agreement between reviewers* — by definition you cannot have a cascade with one reviewer. This will spam the cross-sprint digest (Phase 7's `clawteam attend --summary` surfaces the event per the `SycophancyCascadeDetected` docstring).

**Fix:**
```python
def _compute_agreement_rate(peer_reports: list[Any]) -> float:
    rated: list[list[str]] = []
    for rep in peer_reports:
        if not isinstance(rep, dict):
            continue
        findings = rep.get("findings") or []
        severities = [str(f.get("severity", "")) for f in findings if isinstance(f, dict)]
        rated.append(severities)

    # A cascade requires at least two reviewers to agree. With <2 surviving
    # peers the concept is undefined — return 0.0 so the alarm never fires.
    if len(rated) < 2:
        return 0.0
    max_len = max(len(s) for s in rated)
    if max_len == 0:
        return 0.0
    matched = 0
    for i in range(max_len):
        values: list[str] = []
        for s in rated:
            if i < len(s):
                values.append(s[i])
        if len(values) == len(rated) and len(set(values)) == 1:
            matched += 1
    return matched / max_len
```

### WR-02: `sprint approve --notes` writes user text into YAML frontmatter without escaping

**File:** `clawteam/cli/commands.py:5616-5633`
**Issue:** When `--notes` is provided, the CLI inserts the value directly into the frontmatter via `yaml_lines.append(f"{key}: {value}")` (line 5621) and again as an open-text body line (line 5632). YAML/frontmatter is sensitive to newlines, leading/trailing whitespace, colons, `---`, `#`, and quoting edge cases. A note containing any of these corrupts the artifact and causes `ShipApprovalGate.check` to fail with `"ship-approval.md malformed frontmatter: ..."` or, worse, changes the parsed structure silently (e.g. a newline-embedded note absorbs the next key into its value). Test coverage (`tests/test_sprint_approve_cli.py::test_approve_with_notes_flag`) only exercises the plain-ASCII case `"LGTM by QA on 2026-04-21"`.

**Fix:**
```python
import json  # already imported
# ...
if notes:
    # Escape notes as a JSON string — YAML accepts JSON-quoted scalars and
    # this handles newlines, colons, backslashes, and the `---` sequence.
    frontmatter["approval_notes"] = notes  # dict value, OK
# ...
yaml_lines = ["---"]
for key, value in frontmatter.items():
    if isinstance(value, str) and ("\n" in value or ":" in value or value.startswith("---")):
        yaml_lines.append(f"{key}: {json.dumps(value)}")
    else:
        yaml_lines.append(f"{key}: {value}")
yaml_lines.append("---")
```
Better: use `yaml.safe_dump(frontmatter)` (pyyaml is already a ClawTeam dependency) so every field goes through a real YAML serializer. Also extend `test_approve_with_notes_flag` to cover notes with embedded newline, colon, and `---`.

## Info

### IN-01: `MidReviewThrash` and `SycophancyCascadeDetected` not registered via `register_event_type`

**File:** `clawteam/events/types.py:286-323, 428-433`
**Issue:** The Phase 5 events (`DeployRegressionDetected`, `WebVitalRegressionDetected`) and Phase 6 events (`MemoryWritePersisted`, `ConflictDetected`, `MemoryBackfillComplete`) are explicitly registered via `register_event_type(...)` at the bottom of the module (lines 428-433) so shell hooks can reference them by name (per the module-level comment at bus.py:13-20). The Phase 4 events `MidReviewThrash` and `SycophancyCascadeDetected` are defined but not registered. The event resolver in `bus.py:30-43` has a fallback (`getattr(_types, name, None)`) so `resolve_event_type("MidReviewThrash")` still works, but the pattern is inconsistent and the module-bottom list silently drifts out of sync with the class definitions.
**Fix:** Append two lines at `clawteam/events/types.py:433`:
```python
# Phase 4
register_event_type(MidReviewThrash)
register_event_type(SycophancyCascadeDetected)
```

### IN-02: `--no-sign` CLI flag is accepted-but-unused; `_ = no_sign` workaround

**File:** `clawteam/cli/commands.py:5521-5525, 5645-5647`
**Issue:** `sprint_approve` accepts `--no-sign` but the comment explicitly notes it's a no-op until v1.x (T-04-39). The `_ = no_sign` line at 5647 only exists to silence the unused-variable lint; users who pass `--no-sign` get silent acceptance instead of a clear "flag reserved for v1.x" signal. Either hide the flag from the CLI until it does something, or emit a debug-level log line so operators know it was observed-and-ignored.
**Fix:** Remove the flag from the Typer signature until it is implemented, or:
```python
if no_sign:
    _logger.debug("--no-sign accepted but is a no-op in Phase 4 (T-04-39)")
```

### IN-03: Dead accessor path in `_collect_routers` — `PluginManager` has no `get_review_routers`

**File:** `clawteam/sprint/review_phase.py:260-288`
**Issue:** `_collect_routers` tries `plugin_manager.get_review_routers()` first (lines 268-276), then falls back to `phase_registry.review_routers()`. Grepping `clawteam/plugins/manager.py` shows `PluginManager` exposes `get_verification_pairs`, `get_plugin_gates`, `get_plugin_skills`, `loaded_plugins`, `unload` — but not `get_review_routers`. The first branch is unreachable; only the `phase_registry` fallback fires in production. This is not a bug (the cascade is defensive by design), but the "try plugin_manager first" comment is now stale and will confuse future readers.
**Fix:** Either add `PluginManager.get_review_routers(self) -> list[ReviewRouter]: return get_registry().review_routers()` so the primary path is live and the phase_registry fallback becomes the defensive branch, or drop the first branch and document that routers come from `phase_registry` exclusively.

### IN-04: `SprintConductor._dispatch_review_phase` has vestigial `getattr` defensiveness

**File:** `clawteam/sprint/conductor.py:552-555`
**Issue:** The `getattr(self, "_plugin_manager", None)` fallback on line 555 is documented as a guard for "before Task 3's ctor update lands". Task 3 did land (ctor at line 244 + `self._plugin_manager = plugin_manager` at line 264 are both present), so `self._plugin_manager` is always defined. The `getattr` adds a micro-overhead + noise; a plain `self._plugin_manager` is clearer.
**Fix:**
```python
resolved_pm = plugin_manager if plugin_manager is not None else self._plugin_manager
```

### IN-05: `sprint_approve` uses bare `print(json.dumps(...))` instead of `_sprint_emit_ok`

**File:** `clawteam/cli/commands.py:5650-5661`
**Issue:** The JSON-output branch uses `print(json.dumps({"status": "approved", **frontmatter}))` directly instead of the `_sprint_emit_ok(...)` helper used by every other sprint subcommand (see `sprint_resume` at line 5502). This breaks the global `--json` app-callback pattern that `_sprint_emit_ok` implements and means the approve command's JSON output is inconsistent with `sprint status` / `sprint show` / `sprint pause` / `sprint resume`.
**Fix:** Call `_sprint_emit_ok({"status": "approved", **frontmatter})` and remove the `--json` per-command flag (the global `--json` callback handles the shape already, same as the other sprint subcommands).

---

_Reviewed: 2026-04-22T12:22:06Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
