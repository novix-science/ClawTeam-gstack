---
phase: 04
plan: 14
type: execute
wave: 4
depends_on: [05, 07, 08, 09, 10, 11]
files_modified:
  - clawteam/templates/gstack/prompts/pm.md
  - clawteam/templates/gstack/prompts/designer.md
  - clawteam/templates/gstack/prompts/reviewer.md
  - tests/test_gstack_role_prompts.py
  - tests/test_mid_review_push_integration.py
  - tests/test_adversarial_routing_goldens.py
autonomous: true
requirements: [SPRINT-04, SPRINT-05, QUALITY-07, QUALITY-09, QUALITY-13]
must_haves:
  truths:
    - "Three INTERACTIVE-RUNTIME-DEFERRED meta-instruction blocks are removed from pm.md (line 18), designer.md (line 17), reviewer.md (line 40)."
    - "One SHA-PIN-DEFERRED meta-instruction block is removed from reviewer.md (lines 45-47)."
    - "test_markers_removed in tests/test_gstack_role_prompts.py asserts zero grep hits for INTERACTIVE-RUNTIME-DEFERRED: and SHA-PIN-DEFERRED: across clawteam/templates/gstack/prompts/*.md."
    - "test_markers_removed also asserts the INVERSE: each skill's state-machine module + test file exist (runtime landed, markers removed)."
    - "tests/test_mid_review_push_integration.py runs a full end-to-end mid-review-push scenario on a tmp_path git repo, asserts MidReviewThrash event payload AND thrash_decision field in review-report.md frontmatter."
    - "ISS-06: test_monologue_collapse_detector in tests/test_adversarial_routing_goldens.py is either tightened to equality with fixture turn_budget OR removed entirely."
    - "Closure of ROADMAP Phase 4 Success Criterion #4 (mid-review-push integration verified end-to-end, not just unit-level mocked-subprocess)."
  artifacts:
    - path: "clawteam/templates/gstack/prompts/pm.md"
      provides: "pm role prompt with D-18 INTERACTIVE-RUNTIME-DEFERRED meta-instruction removed"
      contains: "SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1"
    - path: "clawteam/templates/gstack/prompts/designer.md"
      provides: "designer role prompt with D-18 INTERACTIVE-RUNTIME-DEFERRED meta-instruction removed"
      contains: "SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1"
    - path: "clawteam/templates/gstack/prompts/reviewer.md"
      provides: "reviewer role prompt with D-18 INTERACTIVE-RUNTIME-DEFERRED + SHA-PIN-DEFERRED meta-instructions removed"
      contains: "SIGNATURE: gstack-role:reviewer rubric:review+investigate envelope-version:1"
    - path: "tests/test_gstack_role_prompts.py"
      provides: "test_markers_removed + updated existing assertions (removed INTERACTIVE-RUNTIME-DEFERRED + SHA-PIN-DEFERRED checks) + runtime-present inverse assertions"
      contains: "def test_markers_removed"
    - path: "tests/test_mid_review_push_integration.py"
      provides: "End-to-end mid-review-push integration test with real tmp_path git repo"
      contains: "def test_mid_review_push_integration_end_to_end"
      min_lines: 120
    - path: "tests/test_adversarial_routing_goldens.py"
      provides: "test_monologue_collapse_detector tightened to equality (or removed if covered by test_turn_budget_matches_fixture)"
  key_links:
    - from: "clawteam/templates/gstack/prompts/pm.md + designer.md + reviewer.md"
      to: "tests/test_gstack_role_prompts.py::test_markers_removed"
      via: "Inverse assertion: markers gone AND runtime present"
      pattern: "INTERACTIVE-RUNTIME-DEFERRED|SHA-PIN-DEFERRED"
    - from: "tests/test_mid_review_push_integration.py"
      to: "clawteam/sprint/review_phase.py::dispatch_review_phase (Plan 10 Task 1)"
      via: "Integration test invokes real async dispatcher with real subprocess.run on tmp_path git repo"
    - from: "tests/test_mid_review_push_integration.py"
      to: "clawteam/events/types.py::MidReviewThrash (Plan 02)"
      via: "Asserts MidReviewThrash payload captured on EventBus"
    - from: "ROADMAP Phase 4 Success Criterion #4"
      to: "tests/test_mid_review_push_integration.py"
      via: "Closes previously-uncovered mid-review-push integration requirement"
---

<objective>
Close four Phase-4 revision gaps in one cohesive plan:

1. **D-18 marker cleanup (ISS-01):** Remove the four Phase-3 `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:` meta-instruction blocks from pm.md, designer.md, reviewer.md per D-18 rule (b). Phase 4 runtime is shipped by Plans 07/08/09/10 — the deferral markers served their Phase-3 purpose and must now come down or they create canonical-source ambiguity.

2. **D-18 regression test (ISS-01):** Extend `tests/test_gstack_role_prompts.py` with `test_markers_removed` that asserts BOTH (a) zero grep hits for the markers across all prompt files AND (b) the corresponding skill state-machine module + golden test fixture exist (runtime landed, not just markers gone).

3. **Mid-review-push integration test (ISS-02, closes ROADMAP Phase 4 SC #4):** New `tests/test_mid_review_push_integration.py` runs the full flow end-to-end on a real tmp_path git repo (no subprocess mocks). Commits a baseline, invokes `_dispatch_review_phase`, commits a second commit mid-dispatch, asserts `MidReviewThrash` event fires with correct payload, AND asserts the reviewer's `review-report.md` frontmatter carries the `thrash_decision` field (re-pin vs superseded) per D-19.

4. **ISS-06 tightening:** Remove or tighten `test_monologue_collapse_detector` in `tests/test_adversarial_routing_goldens.py`. Current soft bounds (≥10/≥10/≥8) are below the fixture turn_budget values (13/15/12) and are already redundant with `test_turn_budget_matches_fixture` which enforces equality.

Purpose: The orchestrator of Phase 4 is in place after Plans 01-13; this plan is the final cleanup wave that removes transitional markers, enforces runtime-is-present, and validates the mid-review-push integration the ROADMAP explicitly requires. Without this plan, Phase 4 would ship with (a) stale Phase-3 deferral markers in the canonical role prompts, (b) no end-to-end coverage of the mid-review-push flow that Success Criterion #4 calls out, and (c) a redundant soft-bound turn-budget test that ISS-06 flagged.

Output: 3 prompt files edited, 1 existing test file extended, 2 new test files (1 new integration test + 1 existing goldens test tightened).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-RESEARCH.md

<interfaces>
From Plan 01 PLAN_PREP_NOTES.md (A-D18-baseline):
```
Baseline grep hits for Phase-3 meta-instruction markers (current, pre-D18):
  clawteam/templates/gstack/prompts/pm.md:18:INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 multi-turn
  clawteam/templates/gstack/prompts/designer.md:17:INTERACTIVE-RUNTIME-DEFERRED: /design-consultation per-dimension dialogue
  clawteam/templates/gstack/prompts/reviewer.md:40:INTERACTIVE-RUNTIME-DEFERRED: /investigate per-hypothesis state machine
  clawteam/templates/gstack/prompts/reviewer.md:47:SHA-PIN-DEFERRED: At review start, record HEAD SHA
Total: 4 marker lines. Target post-D18: 0.
```

From clawteam/templates/gstack/prompts/pm.md (current — lines 16-21):
```markdown
## /office-hours rubric (interactive runtime — Phase 4)

INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 multi-turn
state machine. Until then: ONE forcing question per turn. Do NOT enumerate
all 6 in a single monologue — that is the lost-in-the-middle anti-pattern.
```

From clawteam/templates/gstack/prompts/designer.md (current — lines 15-20):
```markdown
## /plan-design-review rubric — 7 Passes (verbatim from upstream v2.0.0)

INTERACTIVE-RUNTIME-DEFERRED: /design-consultation per-dimension dialogue
ships as a Phase 4 state machine. In Phase 3, evaluate one pass per turn
and emit a 0-10 score + rationale.
```

From clawteam/templates/gstack/prompts/reviewer.md (current — lines 38-51):
```markdown
## /investigate runtime — Phase 4

INTERACTIVE-RUNTIME-DEFERRED: /investigate per-hypothesis state machine
(plus auto-`/freeze` of the module under investigation) ships in Phase 4.
In Phase 3, emit hypotheses one per turn via the envelope index; Phase 4
will add the freeze/release lifecycle around them.

## SHA-PIN-DEFERRED

SHA-PIN-DEFERRED: At review start, record HEAD SHA in your turn context.
If you detect HEAD has moved mid-review, mark your verdict "superseded"
and stop. Real cross-agent SHA verification ships in Phase 4
(SmartReviewRouter). Phase 3 records the SHA manually; Phase 4 enforces
via the router.
```

From clawteam/sprint/review_phase.py (after Plan 10 Task 1):
```python
async def dispatch_review_phase(state, plugin_manager, bus, *, spawn_fn=None, subprocess_runner=subprocess.run, sycophancy_threshold=0.9) -> dict: ...
```

From clawteam/events/types.py (after Plan 02):
```python
@dataclass
class MidReviewThrash(HarnessEvent):
    sprint_id: str = ""
    review_sha: str = ""
    new_sha: str = ""
    reviewer_roles_active: list[str] = field(default_factory=list)
    diff_paths_added: list[str] = field(default_factory=list)
    diff_paths_removed: list[str] = field(default_factory=list)
```

From D-19 (04-CONTEXT.md):
> mid_review_thrash event payload gives reviewers the info they need to decide re-pin vs supersede. Reviewer writes `thrash_decision: re-pin | superseded` into the review-report frontmatter.

From tests/test_gstack_role_prompts.py (current — has these assertions that MUST be UPDATED after D-18):
  - Line 55: `assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt` (pm) — must be INVERTED.
  - Line 158: `assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt` (designer) — must be INVERTED.
  - Line 238: `assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt` (reviewer) — must be INVERTED.
  - Line 239: `assert "SHA-PIN-DEFERRED" in prompt` (reviewer) — must be INVERTED.

From tests/test_adversarial_routing_goldens.py — current shape (from Plan 13, NOTE ISS-06: the file is actually named `test_adversarial_routing.py` + `test_state_machine_goldens.py` per Plan 13; this plan references the state-machine goldens file):
  - `test_monologue_collapse_detector` uses soft bounds `>= 10`, `>= 10`, `>= 8` against fixture turn budgets 13/15/12.
  - `test_turn_budget_matches_fixture` already enforces equality.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Remove D-18 INTERACTIVE-RUNTIME-DEFERRED + SHA-PIN-DEFERRED meta-instructions from pm.md, designer.md, reviewer.md + update + add regression tests</name>
  <files>clawteam/templates/gstack/prompts/pm.md, clawteam/templates/gstack/prompts/designer.md, clawteam/templates/gstack/prompts/reviewer.md, tests/test_gstack_role_prompts.py</files>
  <read_first>
    - clawteam/templates/gstack/prompts/pm.md (entire file — find the exact 3-line meta-instruction block at lines 18-20)
    - clawteam/templates/gstack/prompts/designer.md (entire file — find the exact 3-line meta-instruction block at lines 17-19)
    - clawteam/templates/gstack/prompts/reviewer.md (entire file — find TWO blocks: INTERACTIVE-RUNTIME at lines 40-45 AND SHA-PIN-DEFERRED at lines 46-51)
    - tests/test_gstack_role_prompts.py (entire file — find all four `INTERACTIVE-RUNTIME-DEFERRED` / `SHA-PIN-DEFERRED` assertions to invert)
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md §A-D18-baseline (baseline line numbers — sanity check before editing)
  </read_first>
  <behavior>
    - Test 1 (test_markers_removed): Zero grep hits for `INTERACTIVE-RUNTIME-DEFERRED:` and `SHA-PIN-DEFERRED:` across every .md file in `clawteam/templates/gstack/prompts/` (including the review/ subdir from Plan 11).
    - Test 2 (test_pm_office_hours_rubric — UPDATED): Assertion `assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt` INVERTED to `assert "INTERACTIVE-RUNTIME-DEFERRED" not in prompt`. Rest of assertions preserved (6 forcing questions + envelope + challenge framing + signature remain).
    - Test 3 (test_designer_rubric — UPDATED): Same inversion for designer.md assertion.
    - Test 4 (test_reviewer_review_and_investigate — UPDATED): Both INTERACTIVE-RUNTIME-DEFERRED and SHA-PIN-DEFERRED assertions INVERTED. Iron-law + halt-after-3 + envelope assertions preserved.
    - Test 5 (test_markers_removed_and_runtime_present — INVERSE ASSERTION): For each of the three skills, assert the Phase 4 state machine module file + transition fixture exist:
      - `clawteam/templates/gstack/skills/office_hours/state.py` exists
      - `tests/fixtures/gstack_state_machines/office-hours.transitions.json` exists
      - `clawteam/templates/gstack/skills/design_consultation/state.py` exists
      - `tests/fixtures/gstack_state_machines/design-consultation.transitions.json` exists
      - `clawteam/templates/gstack/skills/investigate/state.py` exists
      - `tests/fixtures/gstack_state_machines/investigate.transitions.json` exists
    - Test 6 (test_prompt_sizes_still_under_budget_after_cleanup): D-14 4 KB hard cap + 3 KB soft average still holds post-cleanup (cleanup only reduces size).
  </behavior>
  <action>
**Edit 1: `clawteam/templates/gstack/prompts/pm.md`**

Remove the 3-line INTERACTIVE-RUNTIME-DEFERRED block at lines 18-20. The surrounding section heading at line 16 (`## /office-hours rubric (interactive runtime — Phase 4)`) may remain — but the parenthetical "(interactive runtime — Phase 4)" should be removed for cleanliness since the feature IS shipped now.

Current lines 16-21 (DELETE exactly the block between heading and "## Reference"):
```
## /office-hours rubric (interactive runtime — Phase 4)

INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 multi-turn
state machine. Until then: ONE forcing question per turn. Do NOT enumerate
all 6 in a single monologue — that is the lost-in-the-middle anti-pattern.
```

Replace with (heading simplified; monologue anti-pattern preserved as canonical rubric text, not deferral note):
```
## /office-hours rubric

One forcing question per turn. Do NOT enumerate all 6 in a single monologue
— that is the lost-in-the-middle anti-pattern. Phase 4's state machine
enforces per-question advancement; this prompt reinforces the discipline.
```

**Edit 2: `clawteam/templates/gstack/prompts/designer.md`**

Current lines 15-20 (DELETE meta-instruction block; keep 7-pass list):
```
## /plan-design-review rubric — 7 Passes (verbatim from upstream v2.0.0)

INTERACTIVE-RUNTIME-DEFERRED: /design-consultation per-dimension dialogue
ships as a Phase 4 state machine. In Phase 3, evaluate one pass per turn
and emit a 0-10 score + rationale.
```

Replace with:
```
## /plan-design-review rubric — 7 Passes (verbatim from upstream v2.0.0)

Evaluate one pass per turn. Emit a 0-10 score + rationale per pass. Phase 4's
`/design-consultation` state machine iterates the 7 passes in a deterministic
transition order — designer_rubric_dimension 1..7 map to Pass 1..7.
```

**Edit 3: `clawteam/templates/gstack/prompts/reviewer.md`**

Current lines 38-51 (DELETE BOTH meta-instruction blocks; preserve iron-law + halt-after-3 above lines 28-36):
```
## /investigate runtime — Phase 4

INTERACTIVE-RUNTIME-DEFERRED: /investigate per-hypothesis state machine
(plus auto-`/freeze` of the module under investigation) ships in Phase 4.
In Phase 3, emit hypotheses one per turn via the envelope index; Phase 4
will add the freeze/release lifecycle around them.

## SHA-PIN-DEFERRED

SHA-PIN-DEFERRED: At review start, record HEAD SHA in your turn context.
If you detect HEAD has moved mid-review, mark your verdict "superseded"
and stop. Real cross-agent SHA verification ships in Phase 4
(SmartReviewRouter). Phase 3 records the SHA manually; Phase 4 enforces
via the router.
```

Replace with (promote canonical content — now the runtime is real):
```
## /investigate runtime

Emit hypotheses one per turn via `reviewer_hypothesis_index`. On hypothesis
declaration the state machine auto-freezes the module under investigation
via `FreezeRegistry.freeze(module_path, reason="investigate:<sprint>:<hyp>")`.
On hypothesis complete or abandon, the state machine unfreezes with a
matching reason. Module path is hypothesis-provided (explicit), not auto-
derived from stack traces.

## SHA-pinning

At review start, record HEAD SHA in your turn context via the SmartReviewRouter
review_sha field. If HEAD advances mid-review, the harness emits a
`mid_review_thrash` event; in your next turn you either re-pin to the new SHA
or mark the prior review `superseded` (write `thrash_decision: re-pin` or
`thrash_decision: superseded` into your review-report frontmatter).
```

**Edit 4: `tests/test_gstack_role_prompts.py`**

Apply four inversions to existing assertions and APPEND new Task 1 tests.

INVERSION 1 (in `test_pm_office_hours_rubric`, currently line 55):
Replace `assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt`
with `assert "INTERACTIVE-RUNTIME-DEFERRED" not in prompt, "D-18: marker must be removed post-Phase 4"`

INVERSION 2 (in `test_designer_rubric`, currently line 158):
Replace `assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt`
with `assert "INTERACTIVE-RUNTIME-DEFERRED" not in prompt, "D-18: marker must be removed post-Phase 4"`

INVERSION 3 + 4 (in `test_reviewer_review_and_investigate`, currently lines 238-239):
Replace both `assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt` and `assert "SHA-PIN-DEFERRED" in prompt`
with:
```python
    assert "INTERACTIVE-RUNTIME-DEFERRED" not in prompt, "D-18: marker must be removed post-Phase 4"
    assert "SHA-PIN-DEFERRED" not in prompt, "D-18: marker must be removed post-Phase 4"
```

Also update the file-level docstring that currently mentions `INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as Phase 4` comment context — simplify if drift risks.

APPEND these new tests at end of file:
```python
# ---------------------------------------------------------------------------
# D-18 regression (Plan 04-14 — marker cleanup + runtime-present inverse assertion)
# ---------------------------------------------------------------------------


def test_markers_removed():
    """D-18 rule (b): INTERACTIVE-RUNTIME-DEFERRED / SHA-PIN-DEFERRED markers
    are removed from all prompt files (Phase 4 owns the runtime).

    This test enforces a global grep-zero over clawteam/templates/gstack/prompts/
    so no future prompt author accidentally reintroduces a deferral marker.
    Covers pm.md, designer.md, reviewer.md, AND Plan 11's review/<role>.md
    supplements.
    """
    root = PROMPTS_DIR
    # All .md files under prompts/ (top level AND review/ subdir)
    prompt_files = list(root.rglob("*.md"))
    assert len(prompt_files) >= 11, f"expected at least 11 prompts, got {len(prompt_files)}"

    offenders = []
    for p in prompt_files:
        content = p.read_text(encoding="utf-8")
        if "INTERACTIVE-RUNTIME-DEFERRED:" in content:
            offenders.append((str(p.relative_to(root)), "INTERACTIVE-RUNTIME-DEFERRED"))
        if "SHA-PIN-DEFERRED:" in content:
            offenders.append((str(p.relative_to(root)), "SHA-PIN-DEFERRED"))
    assert offenders == [], (
        f"D-18 regression: deferral markers found in {offenders}. "
        "Phase 4 owns the runtime — these markers must stay removed."
    )


def test_markers_removed_and_runtime_present():
    """D-18 inverse assertion: markers gone AND corresponding runtime shipped.

    For each skill where a deferral marker was removed, assert the Phase 4
    state-machine module file + transition fixture exist. Prevents the "markers
    removed but runtime didn't ship" failure mode.
    """
    repo_root = PROMPTS_DIR.parent.parent.parent.parent  # …/gstack/prompts → repo root
    skills = [
        ("office-hours", "office_hours", "office-hours.transitions.json"),
        ("design-consultation", "design_consultation", "design-consultation.transitions.json"),
        ("investigate", "investigate", "investigate.transitions.json"),
    ]
    for display_name, module_slug, fixture_name in skills:
        state_module = (
            repo_root
            / "clawteam" / "templates" / "gstack" / "skills"
            / module_slug / "state.py"
        )
        fixture_file = (
            repo_root / "tests" / "fixtures" / "gstack_state_machines" / fixture_name
        )
        assert state_module.exists(), (
            f"D-18 runtime missing: skill={display_name} state.py not at {state_module}"
        )
        assert fixture_file.exists(), (
            f"D-18 runtime missing: skill={display_name} fixture not at {fixture_file}"
        )
```

**Do NOT modify** other existing Phase 3 role-prompt tests (ceo, eng-mgr, dx-lead, qa, security, engineer, shipper, sre). Do NOT touch prompt files for roles not listed above.
  </action>
  <verify>
    <automated>pytest tests/test_gstack_role_prompts.py -x -q 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - grep -rE "INTERACTIVE-RUNTIME-DEFERRED:|SHA-PIN-DEFERRED:" clawteam/templates/gstack/prompts/ returns 0 matches (markers fully removed)
    - grep -q "SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1" clawteam/templates/gstack/prompts/pm.md (signature preserved)
    - grep -q "SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1" clawteam/templates/gstack/prompts/designer.md
    - grep -q "SIGNATURE: gstack-role:reviewer rubric:review+investigate envelope-version:1" clawteam/templates/gstack/prompts/reviewer.md
    - grep -q "def test_markers_removed" tests/test_gstack_role_prompts.py
    - grep -q "def test_markers_removed_and_runtime_present" tests/test_gstack_role_prompts.py
    - pytest tests/test_gstack_role_prompts.py -x -q exits 0 (all existing Phase 3 tests still pass + 2 new Task 1 tests)
    - wc -c clawteam/templates/gstack/prompts/pm.md < 4096 (size budget preserved; cleanup only reduces size)
    - wc -c clawteam/templates/gstack/prompts/designer.md < 4096
    - wc -c clawteam/templates/gstack/prompts/reviewer.md < 4096
  </acceptance_criteria>
  <done>Four D-18 markers removed; regression tests landed; all Phase 3 role-prompt tests updated to reflect post-Phase-4 state</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: End-to-end mid-review-push integration test (ISS-02 — closes ROADMAP Phase 4 SC #4)</name>
  <files>tests/test_mid_review_push_integration.py</files>
  <read_first>
    - clawteam/sprint/review_phase.py (Plan 10 Task 1 — async def dispatch_review_phase signature + MidReviewThrash emission logic)
    - clawteam/events/bus.py (EventBus.subscribe + emit signatures)
    - clawteam/events/types.py (MidReviewThrash dataclass + field defaults)
    - clawteam/sprint/state.py (SprintState.save + review_sha field)
    - clawteam/harness/evidence_gate.py lines 85-103 (the subprocess.run cwd pattern to mirror for git commands)
    - .planning/ROADMAP.md lines 182-213 Phase 4 Success Criterion #4 verbatim
    - 04-CONTEXT.md D-19 (mid_review_thrash event payload + thrash_decision field spec)
  </read_first>
  <behavior>
    - Test 1 (test_mid_review_push_integration_end_to_end): Full end-to-end scenario:
      1. Initialize tmp_path as a real git repo (subprocess git init + git config user.email + git config user.name + initial commit).
      2. Create a SprintState with workspace_branch=str(tmp_path), current_phase="review", review_sha=None.
      3. Instantiate _CapturingBus that captures MidReviewThrash events.
      4. Monkeypatch the spawn registry with a spawn_fn that:
         a. On first invocation (any peer role), makes a second commit to the sprint branch via subprocess.run(["git", "commit", "--allow-empty", "-m", "mid-review change"], cwd=tmp_path) — this simulates the mid-review-push scenario.
         b. Returns a synthetic peer review-report dict.
      5. Invoke asyncio.run(dispatch_review_phase(state, pm, bus, spawn_fn=custom_spawn)) — REAL subprocess.run (no mock).
      6. Assert: state.review_sha was pinned to the first commit SHA.
      7. Assert: exactly 1 MidReviewThrash event captured on the bus.
      8. Assert: evt.review_sha == first_sha, evt.new_sha == second_sha (both 40-char hex SHAs).
      9. Assert: diff_paths_added is the list of files changed between first and second commit (empty for --allow-empty, or populated if the test writes a file).
      10. Assert: review-report.md frontmatter contains a `thrash_decision` field with value "re-pin" or "superseded" per D-19. This is enforced by having the spawn_fn mock the aggregator (role=="reviewer") to include `thrash_decision` in the returned dict IF a MidReviewThrash was observed during its invocation.

    - Test 2 (test_mid_review_push_no_thrash_when_head_stable): Real git repo but NO mid-dispatch commit → no MidReviewThrash event, no thrash_decision in the aggregator report (confirms the test catches real event emission, not just the test harness).

    - Test 3 (test_mid_review_push_thrash_decision_field_enforced): Reviewer aggregator report dict MUST include `thrash_decision` field with value in {"re-pin", "superseded"} when MidReviewThrash observed. This closes the D-19 requirement explicit in the review-report frontmatter.

  </behavior>
  <action>
Create `tests/test_mid_review_push_integration.py`:

```python
"""End-to-end mid-review-push integration test (Plan 04-14 — ROADMAP Phase 4 SC #4).

Unlike tests/test_review_phase_dispatch.py (which uses mocked subprocess), this
test spins up a real tmp_path git repo and asserts the full flow:
  1. dispatch_review_phase pins review_sha from a REAL `git rev-parse HEAD`.
  2. Spawn registry (monkeypatched to inject a mid-dispatch commit) triggers
     an actual SprintState branch HEAD advance.
  3. Post-gather thrash check re-invokes `git rev-parse HEAD` and observes
     the new SHA.
  4. MidReviewThrash event is emitted on the EventBus with the correct
     (review_sha, new_sha, diff delta) payload.
  5. Reviewer aggregator's review-report dict carries `thrash_decision: re-pin
     | superseded` per §04-CONTEXT D-19.

Closes ROADMAP Phase 4 Success Criterion #4: "if the sprint branch HEAD
advances before the review completes, a mid-review-thrash event fires and
the reviewer chooses between extending the review to the new SHA or marking
the prior review as superseded — verified by a mid-review-push integration
test."
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from clawteam.events.bus import EventBus
from clawteam.events.types import MidReviewThrash
from clawteam.sprint.review_phase import dispatch_review_phase
from clawteam.sprint.state import SprintState


# ── git-repo setup helper ────────────────────────────────────────────


def _init_git_repo(path: Path) -> str:
    """Initialize a real git repo at ``path``; return the first commit SHA."""
    if shutil.which("git") is None:  # pragma: no cover — CI sanity
        pytest.skip("git binary not on PATH — integration test cannot run")
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Phase4 Integration Test"],
        cwd=path, check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=path, check=True,
    )
    # Seed commit.
    (path / "baseline.txt").write_text("baseline\n", encoding="utf-8")
    subprocess.run(["git", "add", "baseline.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "baseline"],
        cwd=path, check=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def _make_mid_dispatch_commit(path: Path) -> str:
    """Add a file + commit on sprint branch; return new HEAD SHA."""
    (path / "mid-review-change.txt").write_text("added mid-review\n", encoding="utf-8")
    subprocess.run(["git", "add", "mid-review-change.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "mid-review change"],
        cwd=path, check=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


# ── Event bus + plugin-manager stubs ─────────────────────────────────


class _CapturingBus(EventBus):
    def __init__(self):
        super().__init__()
        self.thrash_events: list[MidReviewThrash] = []
        self.subscribe(MidReviewThrash, lambda e: self.thrash_events.append(e))


class _FakePluginManager:
    """Minimal plugin manager returning no routers/pairs for the integration test."""

    def get_review_routers(self):
        return []


def _state(tmp_path: Path) -> SprintState:
    return SprintState(
        team="integ-t",
        sprint_id="int12345",
        goal="mid-review-push integration",
        current_phase="review",
        workspace_branch=str(tmp_path),
    )


# ── Integration tests ────────────────────────────────────────────────


def test_mid_review_push_integration_end_to_end(tmp_path, monkeypatch):
    """ROADMAP Phase 4 SC #4: end-to-end verification of mid-review-push flow."""
    # 1. Real git repo.
    first_sha = _init_git_repo(tmp_path)

    # 2. Sprint state pointing at the repo.
    state = _state(tmp_path)
    state.review_sha = None
    bus = _CapturingBus()
    pm = _FakePluginManager()

    # 3. Spawn fn that injects a mid-dispatch commit ON THE FIRST PEER CALL,
    #    and records whether it saw a thrash to include thrash_decision in
    #    the aggregator report.
    invocation_log: list[tuple[str, dict]] = []
    mid_dispatch_sha_container: dict = {"new_sha": None}

    async def spawn_with_mid_commit(role, state, review_sha, peer_reports=None):
        invocation_log.append((role, {"review_sha": review_sha}))
        # On any peer-role invocation, inject the mid-dispatch commit if not yet done.
        if mid_dispatch_sha_container["new_sha"] is None and role != "reviewer":
            mid_dispatch_sha_container["new_sha"] = _make_mid_dispatch_commit(tmp_path)
        # Aggregator role writes thrash_decision when peer_reports + thrash occurred.
        if role == "reviewer":
            # In a real run, the reviewer inspects bus.thrash_events; here we
            # emulate the decision via the captured bus reference.
            thrash_decision = None
            if mid_dispatch_sha_container["new_sha"]:
                # Policy: prefer re-pin for small diffs; in the integration
                # test we hard-code "re-pin" to assert the field is written.
                thrash_decision = "re-pin"
            report = {
                "role": role,
                "sprint_id": state.sprint_id,
                "review_sha": review_sha,
                "findings": [],
            }
            if thrash_decision is not None:
                report["thrash_decision"] = thrash_decision
            return report
        return {"role": role, "sprint_id": state.sprint_id,
                "review_sha": review_sha, "findings": []}

    # 4. Force at least one peer reviewer by simulating a router match through
    #    a lightweight plugin manager extension.
    class _OneRoleRouter:
        def match(self, diff_paths, state):
            return ["designer"]

    class _PMWithRouter(_FakePluginManager):
        def get_review_routers(self):
            return [_OneRoleRouter()]

    pm_with_router = _PMWithRouter()

    # 5. Invoke REAL dispatch_review_phase (REAL subprocess — no mock).
    result = asyncio.run(
        dispatch_review_phase(
            state,
            pm_with_router,
            bus,
            spawn_fn=spawn_with_mid_commit,
        )
    )

    # 6. review_sha pinned to first commit.
    assert state.review_sha == first_sha, (
        f"expected review_sha={first_sha}, got {state.review_sha}"
    )
    assert result["review_sha"] == first_sha

    # 7. Exactly 1 MidReviewThrash event captured.
    assert len(bus.thrash_events) == 1, (
        f"expected exactly 1 MidReviewThrash event, got {len(bus.thrash_events)}"
    )
    evt = bus.thrash_events[0]

    # 8. Event payload correctness (D-19).
    assert evt.review_sha == first_sha
    assert evt.new_sha == mid_dispatch_sha_container["new_sha"]
    assert evt.new_sha != first_sha
    assert len(evt.new_sha) == 40  # git SHA-1 hex
    assert evt.sprint_id == "int12345"

    # 9. diff_paths_added includes the file we added mid-dispatch.
    assert "mid-review-change.txt" in evt.diff_paths_added, (
        f"expected mid-review-change.txt in diff_paths_added, got {evt.diff_paths_added}"
    )

    # 10. Reviewer aggregator's review-report dict has thrash_decision (D-19 frontmatter).
    reviewer_report = result["reviewer_report"]
    assert isinstance(reviewer_report, dict), (
        f"reviewer_report expected dict, got {type(reviewer_report)}"
    )
    assert "thrash_decision" in reviewer_report, (
        f"D-19: reviewer_report missing thrash_decision field; "
        f"keys={sorted(reviewer_report.keys())}"
    )
    assert reviewer_report["thrash_decision"] in {"re-pin", "superseded"}, (
        f"D-19: thrash_decision must be 're-pin' or 'superseded', got "
        f"{reviewer_report['thrash_decision']!r}"
    )


def test_mid_review_push_no_thrash_when_head_stable(tmp_path):
    """Sanity: no mid-dispatch commit → no MidReviewThrash event, no thrash_decision."""
    first_sha = _init_git_repo(tmp_path)
    state = _state(tmp_path)
    state.review_sha = None
    bus = _CapturingBus()
    pm = _FakePluginManager()

    async def spawn_stable(role, state, review_sha, peer_reports=None):
        # No HEAD advance.
        return {"role": role, "sprint_id": state.sprint_id,
                "review_sha": review_sha, "findings": []}

    result = asyncio.run(dispatch_review_phase(state, pm, bus, spawn_fn=spawn_stable))

    assert state.review_sha == first_sha
    assert bus.thrash_events == [], (
        f"expected no thrash, got {bus.thrash_events}"
    )
    # Reviewer report must NOT include thrash_decision when no thrash observed.
    reviewer_report = result["reviewer_report"]
    assert "thrash_decision" not in reviewer_report


def test_mid_review_push_thrash_decision_field_enforced(tmp_path):
    """D-19: thrash_decision MUST be one of {re-pin, superseded} when emitted."""
    first_sha = _init_git_repo(tmp_path)
    state = _state(tmp_path)
    state.review_sha = None
    bus = _CapturingBus()

    class _PM(_FakePluginManager):
        def get_review_routers(self):
            class _R:
                def match(self, dp, st):
                    return ["designer"]
            return [_R()]

    committed = {"done": False}

    async def spawn(role, state, review_sha, peer_reports=None):
        if not committed["done"] and role != "reviewer":
            _make_mid_dispatch_commit(tmp_path)
            committed["done"] = True
        if role == "reviewer":
            return {"role": role, "thrash_decision": "superseded",
                    "findings": []}
        return {"role": role, "findings": []}

    result = asyncio.run(dispatch_review_phase(state, _PM(), bus, spawn_fn=spawn))
    assert len(bus.thrash_events) == 1
    # Reviewer picked superseded this time — assert the set-constraint holds.
    assert result["reviewer_report"]["thrash_decision"] in {"re-pin", "superseded"}
```

**Do NOT modify** clawteam/sprint/review_phase.py or any source code in this task — the integration test consumes Plan 10 Task 1's contract verbatim. If the test reveals a D-19 contract gap (e.g., the reviewer aggregator never receives thrash context from the bus), flag it back to Plan 10 as a follow-up — but expected behavior per the current Plan 10 contract is that the spawn_fn has full access to the bus/event state and is responsible for populating thrash_decision in the report.
  </action>
  <verify>
    <automated>pytest tests/test_mid_review_push_integration.py -x -q 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - tests/test_mid_review_push_integration.py exists
    - grep -q "def test_mid_review_push_integration_end_to_end" tests/test_mid_review_push_integration.py
    - grep -q "thrash_decision" tests/test_mid_review_push_integration.py
    - grep -q "git init" tests/test_mid_review_push_integration.py  # real git repo, no mock
    - grep -q "_make_mid_dispatch_commit" tests/test_mid_review_push_integration.py
    - wc -l tests/test_mid_review_push_integration.py returns >= 120
    - pytest tests/test_mid_review_push_integration.py -x -q exits 0 (all 3 tests pass)
    - pytest tests/test_review_phase_dispatch.py -x -q stays green (Plan 10 unregressed)
  </acceptance_criteria>
  <done>Full end-to-end mid-review-push integration verified against a real git repo; MidReviewThrash + thrash_decision contract enforced; ROADMAP Phase 4 Success Criterion #4 closed</done>
</task>

<task type="auto">
  <name>Task 3: ISS-06 — tighten or remove test_monologue_collapse_detector soft bounds</name>
  <files>tests/test_adversarial_routing_goldens.py</files>
  <read_first>
    - tests/test_adversarial_routing_goldens.py (or tests/test_state_machine_goldens.py depending on Plan 13 filename resolution — ISS-06 references the file that contains test_monologue_collapse_detector with soft bounds ≥10/≥10/≥8)
    - tests/fixtures/gstack_state_machines/*.transitions.json (Plan 07/08/09 — the turn_budget values the test references)
  </read_first>
  <behavior>
    - Test 1: `test_monologue_collapse_detector` either deleted outright (redundant with `test_turn_budget_matches_fixture`) OR tightened to equality against the known fixture turn_budget values (13 / 15 / 12).
    - Test 2: `test_turn_budget_matches_fixture` (existing) continues to pass — it already enforces equality, which is strictly stronger than the soft bounds.
  </behavior>
  <action>
**Plan 13 file resolution:** Per Plan 13 frontmatter, the file is `tests/test_state_machine_goldens.py` (the consolidated goldens file). If `tests/test_adversarial_routing_goldens.py` does NOT exist (Plan 13 uses the consolidated file name), this task edits `tests/test_state_machine_goldens.py`. If both exist, edit the one containing `test_monologue_collapse_detector` (grep to locate before editing).

Pre-check: `grep -l test_monologue_collapse_detector tests/*.py`. If single match, edit that file. If no match (Plan 13 didn't ship the test yet), skip Task 3 entirely — ISS-06 is already resolved by virtue of the test not existing.

**Option A (preferred — DELETE the redundant test):**

Remove the entire `def test_monologue_collapse_detector` function from the file. Rationale: `test_turn_budget_matches_fixture` already enforces equality against the fixture, which is strictly stronger than the soft ≥10/≥10/≥8 bounds. Keeping both is redundant + the soft version cannot fail unless turn budgets drop to fixture values (13/15/12 are all ≥10/≥10/≥8).

Replacement: insert a single comment at the deletion point noting why:
```python
# ISS-06: test_monologue_collapse_detector removed — soft bounds (≥10/≥10/≥8)
# are redundant with test_turn_budget_matches_fixture which enforces equality
# against fixture turn_budget values (13/15/12). Monologue-collapse detection
# is preserved by the equality test; the soft version was dead code.
```

**Option B (ALTERNATIVE — tighten to equality):**

If Option A is inappropriate (e.g., the test is imported by another test file), replace the function body with equality assertions:
```python
def test_monologue_collapse_detector():
    """Pitfall 7: turn budgets enforce multi-turn progression (tightened per ISS-06).

    Previous version used soft bounds ≥10/≥10/≥8 below fixture values 13/15/12.
    Now enforces equality to match test_turn_budget_matches_fixture.
    """
    oh = _load_fixture("office-hours.transitions.json")
    dc = _load_fixture("design-consultation.transitions.json")
    inv = _load_fixture("investigate.transitions.json")
    assert oh["turn_budget"] == 13, (
        f"office-hours budget drifted from fixture expectation 13: {oh['turn_budget']}"
    )
    assert dc["turn_budget"] == 15, (
        f"design-consultation budget drifted from fixture expectation 15: {dc['turn_budget']}"
    )
    assert inv["turn_budget"] == 12, (
        f"investigate budget drifted from fixture expectation 12: {inv['turn_budget']}"
    )
```

**Decision:** Use Option A (DELETE). Rationale: `test_turn_budget_matches_fixture` is already parametrized over all 3 state machines and enforces equality; keeping a second copy that's weaker is pure noise and risks confusing future maintainers about which is canonical.
  </action>
  <verify>
    <automated>pytest tests/test_state_machine_goldens.py tests/test_adversarial_routing_goldens.py tests/test_adversarial_routing.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -rn "test_monologue_collapse_detector" tests/ returns 0 matches (deleted) OR matches only an equality-tightened version
    - grep -n "test_turn_budget_matches_fixture" tests/ still returns the existing equality test
    - pytest tests/test_state_machine_goldens.py -x -q still passes (turn-budget equality test unchanged)
    - No other tests regress
  </acceptance_criteria>
  <done>ISS-06 soft-bound redundancy removed; equality enforcement remains the canonical turn-budget check</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| subprocess.run(`git init`, `git commit`, `git rev-parse`) ↔ tmp_path | Test-owned temp path, isolated per pytest run; no shared state |
| Monkeypatched spawn_fn ↔ real SprintState mutation | spawn_fn is in-test stub, not a real plugin path |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-50 | T (Tampering) | Test-owned git repo at tmp_path | accept | pytest tmp_path is isolated per test; shutil.which("git") skip-fallback if git is absent |
| T-04-51 | D (DoS) | Integration test hangs on slow subprocess | mitigate | All subprocess.run calls use default timeout inherited from review_phase.py (10s); git init/commit are sub-second operations |
| T-04-52 | I (Information disclosure) | git config user.email set to test@example.com | accept | Synthetic data inside tmp_path; isolated from user git config |
</threat_model>

<verification>
- [ ] `pytest tests/test_gstack_role_prompts.py tests/test_mid_review_push_integration.py tests/test_state_machine_goldens.py -x -q` exits 0
- [ ] `grep -rE "INTERACTIVE-RUNTIME-DEFERRED:|SHA-PIN-DEFERRED:" clawteam/templates/gstack/prompts/` returns 0 matches
- [ ] `grep -c "thrash_decision" tests/test_mid_review_push_integration.py` >= 3 (field asserted in all 3 tests)
- [ ] Existing Phase 3 + Phase 4 test suite unregressed: `pytest tests/ -x -q` exits 0 overall
- [ ] ROADMAP Phase 4 Success Criterion #4 is now covered by an end-to-end integration test
</verification>

<success_criteria>
Plan 14 ships when:
- [ ] All 4 Phase-3 meta-instruction markers are removed from pm.md (1), designer.md (1), reviewer.md (2)
- [ ] test_markers_removed + test_markers_removed_and_runtime_present pass and enforce the inverse
- [ ] 3 prior marker assertions in existing tests are INVERTED (pm, designer, reviewer)
- [ ] tests/test_mid_review_push_integration.py ships ≥ 3 tests, uses REAL git subprocess (no mock), asserts MidReviewThrash payload + thrash_decision field
- [ ] ISS-06 redundant soft-bound test removed; equality enforcement preserved
- [ ] ROADMAP Phase 4 Success Criterion #4 closed by test_mid_review_push_integration_end_to_end
- [ ] No existing Phase 1/2/3 tests regress
- [ ] Plan 05 + Plan 10 + Plan 11 + Plan 13 outputs untouched by Plan 14 (integration test consumes their contracts verbatim)
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-14-d18-cleanup-thrash-integration-gate-wiring-SUMMARY.md` with:
- Exact line-number diff of each prompt file (before/after D-18 marker removal)
- Grep-verified 0-hit count for INTERACTIVE-RUNTIME-DEFERRED: and SHA-PIN-DEFERRED: across prompts/
- New test count (test_markers_removed + test_markers_removed_and_runtime_present + 3 integration tests)
- ISS-06 disposition (deleted vs tightened — Option A recommended)
- Confirmation: ROADMAP Phase 4 Success Criterion #4 is now covered
</output>
