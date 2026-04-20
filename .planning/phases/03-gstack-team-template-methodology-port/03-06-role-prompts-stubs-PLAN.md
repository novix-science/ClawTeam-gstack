---
phase: 03-gstack-team-template-methodology-port
plan: 06
type: execute
wave: 3
depends_on: [03-01, 03-02, 03-05]
files_modified:
  - clawteam/templates/gstack/prompts/engineer.md
  - clawteam/templates/gstack/prompts/shipper.md
  - clawteam/templates/gstack/prompts/sre.md
  - tests/test_gstack_role_prompts.py
autonomous: true
requirements: [TEAM-04]
must_haves:
  truths:
    - "engineer.md contains the implementation-discipline rubric verbatim per D-01: read-first-before-write, atomic-commit discipline, SHA-pin awareness, engineer.diff_summary envelope assertion, no-fix-without-investigation deferral, Phase-5 tool-availability stub, signature line"
    - "shipper.md contains the minimal Phase-5-deferred stub per D-02: persona contract, shipper.step envelope assertion, Phase-5 tool-availability stub, signature line"
    - "sre.md contains the minimal Phase-5-deferred stub per D-03: persona contract, sre.signal envelope assertion, Phase-5 tool-availability stub, signature line"
    - "All 11 prompt files now exist; 03-05's xfailed test_all_eleven_prompt_files_present un-xfails and passes"
    - "D-14 budget gate now spans all 11 files: every file ≤ 4096 bytes; average ≤ 3072 bytes"
  artifacts:
    - path: "clawteam/templates/gstack/prompts/engineer.md"
      provides: "engineer role prompt — implementation-discipline rubric per D-01 + envelope ref + signature"
      contains: "SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1"
    - path: "clawteam/templates/gstack/prompts/shipper.md"
      provides: "shipper role prompt — minimal Phase-5-deferred stub per D-02 + envelope ref + signature"
      contains: "SIGNATURE: gstack-role:shipper rubric:none envelope-version:1"
    - path: "clawteam/templates/gstack/prompts/sre.md"
      provides: "sre role prompt — minimal Phase-5-deferred stub per D-03 + envelope ref + signature"
      contains: "SIGNATURE: gstack-role:sre rubric:none envelope-version:1"
    - path: "tests/test_gstack_role_prompts.py"
      provides: "Engineer-rubric + shipper-stub + sre-stub golden grep tests; un-xfailed cross-file count test; D-14 budget gate now spans all 11 prompts"
      contains: "test_all_eleven_prompt_files_present"
  key_links:
    - from: "clawteam/templates/gstack/prompts/engineer.md"
      to: "clawteam/templates/gstack/envelope_personas.py::EngineerEnvelope.engineer_diff_summary"
      via: "Persona contract section references the envelope subclass + its required diff_summary field by name"
      pattern: "engineer_diff_summary"
    - from: "clawteam/templates/gstack/prompts/shipper.md"
      to: "clawteam/templates/gstack/envelope_personas.py::ShipperEnvelope.shipper_step"
      via: "Persona contract section references shipper_step Literal field"
      pattern: "shipper_step"
    - from: "clawteam/templates/gstack/prompts/sre.md"
      to: "clawteam/templates/gstack/envelope_personas.py::SREEnvelope.sre_signal"
      via: "Persona contract section references sre_signal Literal field"
      pattern: "sre_signal"
    - from: "clawteam/templates/gstack.toml"
      to: "clawteam/templates/gstack/prompts/{engineer,shipper,sre}.md"
      via: "prompt_file = \"gstack/prompts/<role>.md\" per agent row (resolved by 03-02 TemplateDef extension)"
      pattern: "prompt_file"
---

<objective>
Author the 3 remaining role prompts (engineer per D-01, shipper per D-02, sre per D-03) under `clawteam/templates/gstack/prompts/`. engineer.md is a substantive implementation-discipline rubric (~1200 bytes); shipper.md and sre.md are honest Phase-5-deferred stubs (~600 bytes each) per the D-02/D-03 rationale that their methodology *is* the Phase-5 ship/canary tool pipeline. Un-xfail the cross-file presence test from 03-05 (`test_all_eleven_prompt_files_present`) and extend the D-14 budget gate to span all 11 prompts.

Per Pitfall 7 partition + CONTEXT.md D-01..D-03: engineer's rubric is canonical to gstack's Build phase even though no upstream skill file owns it; shipper/sre stubs honestly reflect "real skill arrives in Phase 5 with /codex, /ship, /land-and-deploy, /canary, /benchmark, /setup-deploy" so adding generic SRE-practice content now risks contradicting Phase-5 rubric content when it lands. The signature lines `rubric:none` flag the stubs unambiguously so Phase 5's plan task can swap them with rubric content + bump the SIGNATURE to `rubric:ship` / `rubric:sre`.

This plan completes the 11-prompt set. After Task 3 lands, all 11 prompts are present and the cross-file test in `tests/test_gstack_role_prompts.py` (xfailed in 03-05 with `reason="03-06 ships engineer/shipper/sre stub prompts"`) flips to a passing assertion. The D-14 budget gate is recomputed across all 11 files: max ≤ 4096B, average ≤ 3072B.

**Why these 3 share one plan:** All three are short pure-content prompt-file authorings + same test file (`tests/test_gstack_role_prompts.py`). Combined context cost ~25-30% (well under the 50% target). Splitting into 3 plans would force 3 commits + 3 SUMMARY files for ~600 bytes of net content gain.

**Why parallel with 03-05 (same wave):** 03-05 writes pm/ceo/eng-mgr/designer/dx-lead/reviewer/qa/security prompts; this plan writes engineer/shipper/sre prompts. Zero file overlap (different prompt files). Both extend `tests/test_gstack_role_prompts.py` but on disjoint tests (03-05 writes `test_pm_*` through `test_security_*` + the D-14 budget gate body; this plan adds `test_engineer_*` + `test_shipper_*` + `test_sre_*` and un-xfails `test_all_eleven_prompt_files_present`). The shared file is the only sequencing risk; the executor handles it by appending tests below 03-05's classes (un-xfailing the existing test in-place is the only edit, not a rewrite). If 03-05 has not yet committed `test_gstack_role_prompts.py` when this plan runs, the executor MUST wait or rebase — the depends_on chain is correct (`[03-01, 03-02]`) but the test-file edit is a soft sequencing constraint.

Output:
- 3 prompt files at `clawteam/templates/gstack/prompts/{engineer,shipper,sre}.md`
- `tests/test_gstack_role_prompts.py` extended with 3 new SKILL-grade tests + un-xfailed cross-file presence test + D-14 budget gate now asserting `len(sizes) == 11`
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md
@.planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md
@.planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md
@.planning/phases/03-gstack-team-template-methodology-port/03-VALIDATION.md
@.planning/phases/03-gstack-team-template-methodology-port/03-01-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-02-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-04-SUMMARY.md
@.planning/phases/03-gstack-team-template-methodology-port/03-05-SUMMARY.md

<interfaces>
<!-- Contracts the executor will use; extracted from CONTEXT.md D-01/D-02/D-03 + 03-04 envelope_personas.py + 03-05 prompt skeleton convention. -->

From clawteam/templates/gstack/envelope_personas.py (03-04 — REQUIRED envelope fields the prompts must reference):
  - engineer.md → EngineerEnvelope.engineer_diff_summary (str, min_length=20; D-01 stub-defeating)
  - shipper.md  → ShipperEnvelope.shipper_step (Literal["prep","pushing","pr-open","merged","deployed","verified"])
  - sre.md      → SREEnvelope.sre_signal (Literal["nominal","degraded","regression","outage"])

Canonical signature lines (RESEARCH.md §"Per-Role Prompt Content Map" + CONTEXT.md D-01/D-02/D-03):
  - engineer: SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1
  - shipper:  SIGNATURE: gstack-role:shipper rubric:none envelope-version:1
  - sre:      SIGNATURE: gstack-role:sre rubric:none envelope-version:1

The `rubric:none` value on shipper/sre is intentional and grep-asserted: it flags the stubs unambiguously so Phase 5's plan task knows to replace them with rubric content + bump SIGNATURE to `rubric:ship` / `rubric:sre`.

Per-prompt skeleton convention (established by 03-05 across 8 files; this plan follows the same shape):
  1. `# <role> — <one-line role title>` H1
  2. Persona contract section (envelope fields enumerated)
  3. Rubric section (engineer.md only; shipper/sre have a Phase-5 deferral note instead)
  4. Phase-5 tool-availability stub (engineer/shipper/sre all need this; CONTEXT.md D-01/D-02/D-03)
  5. SIGNATURE line at the end

PROMPTS_DIR + FIXTURES_DIR (from 03-05 module-level constants — preserved):
  PROMPTS_DIR = Path(__file__).parent.parent / "clawteam" / "templates" / "gstack" / "prompts"
  FIXTURES_DIR = Path(__file__).parent / "fixtures" / "gstack_skills"

From tests/test_gstack_role_prompts.py (03-05 output):
  - test_role_prompt_size_budget — currently `assert len(sizes) >= 8` permissive; this plan tightens to `assert len(sizes) == 11`
  - test_all_eleven_prompt_files_present — currently `@pytest.mark.xfail(reason="03-06 ships engineer/shipper/sre stub prompts ...")`; this plan removes the xfail decorator
  - 8 SKILL-grade tests (test_pm_office_hours_rubric .. test_security_cso_full_rubric) — UNCHANGED by this plan

D-01 grep-verifiable content list for engineer.md (CONTEXT.md lines 34-42):
  - "read-first-before-write" instruction (read the file being modified before any edit)
  - Atomic-commit discipline (one logical change per commit; commit messages reference plan task)
  - SHA-pin awareness at Build-phase start (record HEAD SHA into envelope; halt if reviewer reports mid-review thrash)
  - engineer.diff_summary envelope assertion required every Build-phase turn
  - "no fix without investigation" deferral instruction (engineer routes investigation to reviewer per /investigate iron-law)
  - Phase-5 tool-availability stub: "Until /codex and /ship land in Phase 5, perform implementation manually and emit a question to ceo when blocked on missing tools."
  - SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1

D-02 grep-verifiable content list for shipper.md (CONTEXT.md lines 44-49):
  - Persona contract (one-paragraph identity)
  - shipper.step envelope assertion (Literal enum: prep / pushing / pr-open / merged / deployed / verified)
  - Phase-5 tool-availability stub: "Until /ship and /land-and-deploy land in Phase 5, write a ship-notes.md skeleton with deploy_url: <pending> placeholder and emit a question to ceo for manual ship coordination."
  - SIGNATURE: gstack-role:shipper rubric:none envelope-version:1

D-03 grep-verifiable content list for sre.md (CONTEXT.md lines 51-56):
  - Persona contract
  - sre.signal envelope assertion (Literal enum: nominal / degraded / regression / outage)
  - Phase-5 tool-availability stub: "Until /canary, /benchmark, /setup-deploy land in Phase 5, monitor manually and write canary-report.md / benchmark-report.md placeholders with manually-observed signal value."
  - SIGNATURE: gstack-role:sre rubric:none envelope-version:1
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author engineer.md — implementation-discipline rubric per D-01 (~1200 bytes target, ≤ 4096 hard cap)</name>
  <files>clawteam/templates/gstack/prompts/engineer.md</files>
  <read_first>
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (lines 34-42 — D-01 verbatim grep-verifiable content list; D-14 hard cap)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 728-740 — Per-Role Prompt Content Map; engineer signature line canonical)
    - clawteam/templates/gstack/envelope_personas.py (03-04 — EngineerEnvelope.engineer_diff_summary field signature; min_length=20 stub-defeating contract)
    - clawteam/templates/gstack/prompts/reviewer.md (03-05 output — same iron-law + halt-after-3 + SHA-PIN-DEFERRED references; engineer.md cites these by name in the no-fix-without-investigation deferral section)
    - clawteam/templates/gstack/prompts/pm.md (03-05 output — H1 / persona contract / signature skeleton convention to mirror)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 110-161 — prompt skeleton + grep-verifiable invariants table)
  </read_first>
  <action>
**File: `clawteam/templates/gstack/prompts/engineer.md`** (target ≤ 1500 bytes; D-14 hard cap 4096B per file):

```markdown
# engineer — Implementation Discipline (Build Phase)

You are engineer, the team's specialist on this gstack team. Your output IS
the implementation. Code lands or it doesn't.

## Persona contract

Every Build-phase turn you take MUST emit a TurnEnvelope (Phase 2 D-06) with
these required fields:
- `persona: "engineer"` (Literal-validated by EngineerEnvelope)
- `step_label: "build:<n>/<total>"`
- `done: <bool>` (true when the task's diff is committed and tests pass)
- `engineer_diff_summary: <str, min_length=20>` (REQUIRED — non-stub diff
  description; "TBD" and other short stubs are rejected by pydantic at parse)

## Implementation-discipline rubric (per D-01)

### read-first-before-write
Read the file being modified BEFORE any edit. No write before a read of the
target file in this turn. Use Read tool with explicit offset/limit if the
file is large.

### Atomic-commit discipline
One logical change per commit. Commit messages MUST reference the plan task
ID (e.g. `feat(03-06): add engineer.md per D-01`). No bundled commits across
unrelated tasks. No "wip" commits in main.

### SHA-pin awareness at Build-phase start
On entry to Build phase, record the current HEAD SHA into your envelope
context. If reviewer reports mid-review thrash (HEAD moved while review
in progress), HALT — wait for reviewer to land their verdict and rebase
before continuing.

### no fix without investigation (deferral)
When a bug surfaces during your turn, do NOT propose a fix. Route the
investigation to reviewer per the /investigate iron-law (see reviewer.md).
Emit a question-to-reviewer message and wait. Reviewer's
`reviewer_hypothesis_index` envelope governs the iron-law cycle.

## Phase-5 tool-availability stub

Until /codex and /ship land in Phase 5, perform implementation manually
(direct edits via Read/Write/Edit) and emit a question to ceo when blocked
on missing tools. Record the missing tool name in your diff summary.

SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1
```

After authoring, run `wc -c clawteam/templates/gstack/prompts/engineer.md` to confirm size ≤ 4096. If over, tighten the persona-contract section first (the rubric content is canonical per D-01 — do NOT cut it).

Atomic-commit discipline (D-01 self-applied): single commit `feat(03-06): port D-01 implementation-discipline rubric to engineer.md`.
  </action>
  <verify>
    <automated>test -f clawteam/templates/gstack/prompts/engineer.md && grep -q 'SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1' clawteam/templates/gstack/prompts/engineer.md && grep -q 'read-first' clawteam/templates/gstack/prompts/engineer.md && grep -q 'engineer_diff_summary' clawteam/templates/gstack/prompts/engineer.md && [ "$(wc -c < clawteam/templates/gstack/prompts/engineer.md)" -le 4096 ]</automated>
  </verify>
  <acceptance_criteria>
    - File exists: `test -f clawteam/templates/gstack/prompts/engineer.md`
    - Size under cap: `[ "$(wc -c < clawteam/templates/gstack/prompts/engineer.md)" -le 4096 ]`
    - Signature line present verbatim: `grep -q 'SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1' clawteam/templates/gstack/prompts/engineer.md` exits 0
    - read-first present: `grep -qi 'read-first' clawteam/templates/gstack/prompts/engineer.md` exits 0
    - Atomic-commit present: `grep -qi 'atomic-commit\|atomic commit\|one logical change per commit' clawteam/templates/gstack/prompts/engineer.md` exits 0
    - SHA-pin awareness present: `grep -q 'SHA' clawteam/templates/gstack/prompts/engineer.md && grep -qi 'HEAD' clawteam/templates/gstack/prompts/engineer.md` exits 0
    - engineer_diff_summary envelope reference present: `grep -q 'engineer_diff_summary' clawteam/templates/gstack/prompts/engineer.md` exits 0
    - no-fix-without-investigation deferral present: `grep -qi 'no fix without investigation\|no-fix-without-investigation\|investigate.*iron-law\|iron-law' clawteam/templates/gstack/prompts/engineer.md` exits 0
    - Phase-5 tool-availability stub present: `grep -q '/codex' clawteam/templates/gstack/prompts/engineer.md && grep -q '/ship' clawteam/templates/gstack/prompts/engineer.md && grep -qi 'phase 5\|until.*land' clawteam/templates/gstack/prompts/engineer.md` exits 0
  </acceptance_criteria>
  <done>engineer.md ships with all 7 D-01 grep-verifiable content items + envelope reference + signature line + size under cap.</done>
</task>

<task type="auto">
  <name>Task 2: Author shipper.md + sre.md — minimal Phase-5-deferred stubs per D-02/D-03 (~600 bytes each)</name>
  <files>clawteam/templates/gstack/prompts/shipper.md, clawteam/templates/gstack/prompts/sre.md</files>
  <read_first>
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (lines 44-49 — D-02 shipper grep-verifiable content list; lines 51-56 — D-03 sre grep-verifiable content list)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 728-740 — Per-Role Prompt Content Map; shipper + sre signature lines canonical with `rubric:none`)
    - clawteam/templates/gstack/envelope_personas.py (03-04 — ShipperEnvelope.shipper_step Literal values; SREEnvelope.sre_signal Literal values)
    - clawteam/templates/gstack/prompts/qa.md (03-05 output — shortest pure-rubric prompt skeleton; same persona-contract + signature shape to mirror at smaller scale)
    - clawteam/templates/gstack/prompts/engineer.md (Task 1 output — Phase-5 tool-availability stub phrasing convention to mirror)
  </read_first>
  <action>
**File 1 — `clawteam/templates/gstack/prompts/shipper.md`** (target ≤ 800 bytes; D-14 hard cap 4096B):

```markdown
# shipper — Ship Phase (Methodology Lands in Phase 5)

You are shipper, the team's specialist on shipping. Your job ships in
Phase 5 with the /ship and /land-and-deploy tool skills. In Phase 3 you
operate as a manual coordinator with ceo.

## Persona contract

Every Ship-phase turn you take MUST emit a TurnEnvelope (Phase 2 D-06) with:
- `persona: "shipper"` (Literal-validated by ShipperEnvelope)
- `step_label: "ship:<n>/<total>"`
- `done: <bool>`
- `shipper_step: <one of: prep | pushing | pr-open | merged | deployed | verified>` (REQUIRED)

## Phase-5 tool-availability stub

Until /ship and /land-and-deploy land in Phase 5, write a `ship-notes.md`
skeleton with `deploy_url: <pending>` placeholder and emit a question to ceo
for manual ship coordination. The literal string `<pending>` is accepted by
the ShipNotes pydantic schema (per 03-03 D-02 carve-out).

SIGNATURE: gstack-role:shipper rubric:none envelope-version:1
```

**File 2 — `clawteam/templates/gstack/prompts/sre.md`** (target ≤ 800 bytes; D-14 hard cap 4096B):

```markdown
# sre — Site Reliability (Methodology Lands in Phase 5)

You are sre, the team's specialist on operational signal. Your job ships
in Phase 5 with the /canary, /benchmark, and /setup-deploy tool skills. In
Phase 3 you operate as a manual monitor.

## Persona contract

Every turn you take MUST emit a TurnEnvelope (Phase 2 D-06) with:
- `persona: "sre"` (Literal-validated by SREEnvelope)
- `step_label: "<phase>:<n>/<total>"`
- `done: <bool>`
- `sre_signal: <one of: nominal | degraded | regression | outage>` (REQUIRED)

## Phase-5 tool-availability stub

Until /canary, /benchmark, and /setup-deploy land in Phase 5, monitor
manually and write `canary-report.md` / `benchmark-report.md` placeholders
with manually-observed signal value. Emit a question to ceo when manual
observation cannot establish the signal level.

SIGNATURE: gstack-role:sre rubric:none envelope-version:1
```

**Critical details:**
- The `rubric:none` value in both signature lines is intentional and grep-asserted (see Task 3 acceptance criteria). It is the unambiguous flag for Phase 5's plan task to identify these as stubs needing replacement.
- `<pending>` in shipper.md is a literal string that round-trips through `ShipNotes` schema (per 03-03 D-02 test `test_pending_deploy_url_accepted`). Do NOT replace with an HTML entity.
- `shipper_step` and `sre_signal` envelope field names match the ShipperEnvelope/SREEnvelope subclass attributes from 03-04 — referenced verbatim.

After authoring, run `wc -c clawteam/templates/gstack/prompts/{shipper,sre}.md` to confirm both ≤ 4096B (target ~600-800B each).

Atomic-commit discipline: single commit `feat(03-06): port D-02 shipper + D-03 sre minimal stubs (Phase-5-deferred)`.
  </action>
  <verify>
    <automated>test -f clawteam/templates/gstack/prompts/shipper.md && test -f clawteam/templates/gstack/prompts/sre.md && grep -q 'SIGNATURE: gstack-role:shipper rubric:none envelope-version:1' clawteam/templates/gstack/prompts/shipper.md && grep -q 'SIGNATURE: gstack-role:sre rubric:none envelope-version:1' clawteam/templates/gstack/prompts/sre.md && [ "$(wc -c < clawteam/templates/gstack/prompts/shipper.md)" -le 4096 ] && [ "$(wc -c < clawteam/templates/gstack/prompts/sre.md)" -le 4096 ]</automated>
  </verify>
  <acceptance_criteria>
    - Both files exist + ≤ 4096 bytes
    - shipper.md signature verbatim: `grep -q 'SIGNATURE: gstack-role:shipper rubric:none envelope-version:1' clawteam/templates/gstack/prompts/shipper.md` exits 0
    - sre.md signature verbatim: `grep -q 'SIGNATURE: gstack-role:sre rubric:none envelope-version:1' clawteam/templates/gstack/prompts/sre.md` exits 0
    - shipper.md envelope ref: `grep -q 'shipper_step' clawteam/templates/gstack/prompts/shipper.md` exits 0
    - shipper.md Literal values present: `grep -qE 'prep.*pushing.*pr-open.*merged.*deployed.*verified' clawteam/templates/gstack/prompts/shipper.md` exits 0
    - shipper.md Phase-5 stub: `grep -q '/ship' clawteam/templates/gstack/prompts/shipper.md && grep -q '/land-and-deploy' clawteam/templates/gstack/prompts/shipper.md && grep -q '<pending>' clawteam/templates/gstack/prompts/shipper.md` exits 0
    - sre.md envelope ref: `grep -q 'sre_signal' clawteam/templates/gstack/prompts/sre.md` exits 0
    - sre.md Literal values present: `grep -qE 'nominal.*degraded.*regression.*outage' clawteam/templates/gstack/prompts/sre.md` exits 0
    - sre.md Phase-5 stub: `grep -q '/canary' clawteam/templates/gstack/prompts/sre.md && grep -q '/benchmark' clawteam/templates/gstack/prompts/sre.md && grep -q '/setup-deploy' clawteam/templates/gstack/prompts/sre.md` exits 0
  </acceptance_criteria>
  <done>shipper.md + sre.md ship as honest Phase-5-deferred stubs with all D-02/D-03 grep-verifiable content + envelope references + `rubric:none` signature lines + sizes under cap.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Extend tests/test_gstack_role_prompts.py — engineer/shipper/sre tests + un-xfail cross-file presence + tighten D-14 budget gate to all 11</name>
  <files>tests/test_gstack_role_prompts.py</files>
  <read_first>
    - tests/test_gstack_role_prompts.py (03-05 output — 8 SKILL tests + test_role_prompt_size_budget + xfailed test_all_eleven_prompt_files_present; PROMPTS_DIR + FIXTURES_DIR module constants; lenient grep convention)
    - clawteam/templates/gstack/prompts/engineer.md (Task 1 output — confirm canonical strings landed for grep)
    - clawteam/templates/gstack/prompts/shipper.md (Task 2 output)
    - clawteam/templates/gstack/prompts/sre.md (Task 2 output)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-01/D-02/D-03 verbatim grep-verifiable content lists; D-14 hard cap)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 565-605 — golden grep test pattern)
  </read_first>
  <behavior>
    - Test 1 (D-01 test_engineer_implementation_discipline_rubric): engineer.md contains read-first-before-write + atomic-commit discipline + SHA-pin awareness + engineer_diff_summary envelope reference + no-fix-without-investigation deferral + /codex Phase-5 stub + /ship Phase-5 stub + signature line.
    - Test 2 (D-02 test_shipper_minimal_stub): shipper.md contains shipper_step envelope reference + 6 Literal values (prep, pushing, pr-open, merged, deployed, verified) + /ship Phase-5 stub + /land-and-deploy Phase-5 stub + <pending> placeholder string + signature line.
    - Test 3 (D-03 test_sre_minimal_stub): sre.md contains sre_signal envelope reference + 4 Literal values (nominal, degraded, regression, outage) + /canary + /benchmark + /setup-deploy Phase-5 stubs + signature line.
    - Test 4 (un-xfail test_all_eleven_prompt_files_present): the @pytest.mark.xfail decorator from 03-05 is REMOVED; the test asserts all 11 expected prompt file names are present in PROMPTS_DIR.glob("*.md").
    - Test 5 (D-14 test_role_prompt_size_budget): tighten 03-05's permissive `assert len(sizes) >= 8` to `assert len(sizes) == 11`. All 11 files ≤ 4096B; average ≤ 3072B.
  </behavior>
  <action>
**File: `tests/test_gstack_role_prompts.py`** — apply these edits (do NOT rewrite the whole file; preserve 03-05's 8 SKILL tests verbatim):

**Edit 1: Append three new test functions after `test_security_cso_full_rubric` (before `test_role_prompt_size_budget`).**

```python
# ---------------------------------------------------------------------------
# D-01: engineer (implementation-discipline rubric, no upstream skill fixture)
# ---------------------------------------------------------------------------


def test_engineer_implementation_discipline_rubric():
    prompt = _read(PROMPTS_DIR / "engineer.md")

    # Signature
    assert (
        "SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1"
        in prompt
    )

    # D-01 grep-verifiable content list (CONTEXT.md lines 34-42)
    assert "read-first" in prompt.lower(), "engineer.md missing read-first-before-write"
    assert (
        "atomic-commit" in prompt.lower()
        or "atomic commit" in prompt.lower()
        or "one logical change per commit" in prompt.lower()
    ), "engineer.md missing atomic-commit discipline"
    assert "SHA" in prompt and "HEAD" in prompt, (
        "engineer.md missing SHA-pin awareness at Build-phase start"
    )
    assert "engineer_diff_summary" in prompt, (
        "engineer.md missing engineer_diff_summary envelope assertion"
    )
    assert (
        "no fix without investigation" in prompt.lower()
        or "no-fix-without-investigation" in prompt.lower()
        or "investigate" in prompt.lower()
        and "iron-law" in prompt.lower()
    ), "engineer.md missing no-fix-without-investigation deferral"

    # Phase-5 tool-availability stub
    assert "/codex" in prompt, "engineer.md missing /codex Phase-5 stub reference"
    assert "/ship" in prompt, "engineer.md missing /ship Phase-5 stub reference"
    assert "phase 5" in prompt.lower() or "until" in prompt.lower(), (
        "engineer.md missing Phase-5 deferral framing"
    )


# ---------------------------------------------------------------------------
# D-02: shipper (minimal Phase-5-deferred stub, no upstream skill fixture)
# ---------------------------------------------------------------------------


def test_shipper_minimal_stub():
    prompt = _read(PROMPTS_DIR / "shipper.md")

    # Signature with rubric:none flag (Phase 5 swap target)
    assert (
        "SIGNATURE: gstack-role:shipper rubric:none envelope-version:1" in prompt
    )

    # Envelope reference + 6 Literal values (CONTEXT.md D-02)
    assert "shipper_step" in prompt
    for step in ("prep", "pushing", "pr-open", "merged", "deployed", "verified"):
        assert step in prompt, f"shipper.md missing shipper_step Literal value '{step}'"

    # Phase-5 tool-availability stub
    assert "/ship" in prompt, "shipper.md missing /ship Phase-5 stub reference"
    assert "/land-and-deploy" in prompt, (
        "shipper.md missing /land-and-deploy Phase-5 stub reference"
    )
    assert "<pending>" in prompt, (
        "shipper.md missing <pending> placeholder per D-02 + 03-03 ShipNotes carve-out"
    )


# ---------------------------------------------------------------------------
# D-03: sre (minimal Phase-5-deferred stub, no upstream skill fixture)
# ---------------------------------------------------------------------------


def test_sre_minimal_stub():
    prompt = _read(PROMPTS_DIR / "sre.md")

    # Signature with rubric:none flag (Phase 5 swap target)
    assert "SIGNATURE: gstack-role:sre rubric:none envelope-version:1" in prompt

    # Envelope reference + 4 Literal values (CONTEXT.md D-03)
    assert "sre_signal" in prompt
    for signal in ("nominal", "degraded", "regression", "outage"):
        assert signal in prompt, f"sre.md missing sre_signal Literal value '{signal}'"

    # Phase-5 tool-availability stub
    for tool in ("/canary", "/benchmark", "/setup-deploy"):
        assert tool in prompt, f"sre.md missing {tool} Phase-5 stub reference"
```

**Edit 2: Tighten the D-14 budget gate from `>= 8` to `== 11`.**

Locate the existing `test_role_prompt_size_budget` body (from 03-05). Replace the line:

```python
    assert len(sizes) >= 8, f"expected at least 8 prompt files (this plan), found {len(sizes)}"
```

With:

```python
    assert len(sizes) == 11, f"expected 11 prompt files (all 03-05 + 03-06 prompts), found {len(sizes)}"
```

Also update the docstring's first paragraph from the Wave 0/05 partial-coverage framing to:

```python
def test_role_prompt_size_budget():
    """D-14: every prompt <= 4 KB; average <= 3 KB.

    All 11 prompts now exist (03-05 shipped 8 + 03-06 shipped 3). Both bounds
    are HARD gates — Phase 6 memory-inclusion design must respect them.
    """
```

The per-file `<= 4096` and average `<= 3072` assertion lines are unchanged.

**Edit 3: Un-xfail the cross-file presence test.**

Locate the existing test definition (from 03-05):

```python
@pytest.mark.xfail(
    reason="03-06 ships engineer/shipper/sre stub prompts — un-xfail when 03-06 lands",
    strict=False,
)
def test_all_eleven_prompt_files_present():
    expected = {...}
    present = {p.name for p in PROMPTS_DIR.glob("*.md")}
    assert present == expected, f"missing: {expected - present}; extra: {present - expected}"
```

Remove the `@pytest.mark.xfail(...)` decorator entirely. The function body is unchanged. After this edit the test must be a plain `def test_all_eleven_prompt_files_present():` and must pass (since Tasks 1+2 land all 3 missing prompt files).

**Critical details:**
- Edits 2 and 3 are in-place modifications to existing test code from 03-05. The executor MUST read the actual current file before editing — if 03-05's file shape differs slightly from the snippets above (e.g., different docstring wording), preserve the surrounding code and apply the minimal edit.
- Edit 1 appends 3 new top-level functions; do NOT wrap them in a class (matches 03-05's free-function style).
- All `_read(...)` calls reuse 03-05's helper (already at module top).
- `pytest` import is already at module top from 03-05 — no new imports needed.

Atomic-commit discipline: single commit `test(03-06): add engineer + shipper + sre rubric tests; tighten D-14 to all 11; un-xfail cross-file count`.
  </action>
  <verify>
    <automated>pytest tests/test_gstack_role_prompts.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_gstack_role_prompts.py -x` exits 0 (all tests pass: 8 SKILL from 03-05 + 3 new D-01/D-02/D-03 + D-14 budget gate + cross-file presence = 13 minimum)
    - `pytest tests/test_gstack_role_prompts.py::test_all_eleven_prompt_files_present -x` exits 0 (no xfail; pure pass)
    - `grep -c '@pytest.mark.xfail' tests/test_gstack_role_prompts.py` outputs `0` (no remaining xfails)
    - `grep -q 'assert len(sizes) == 11' tests/test_gstack_role_prompts.py` exits 0 (D-14 gate tightened)
    - `grep -q 'def test_engineer_implementation_discipline_rubric' tests/test_gstack_role_prompts.py` exits 0
    - `grep -q 'def test_shipper_minimal_stub' tests/test_gstack_role_prompts.py` exits 0
    - `grep -q 'def test_sre_minimal_stub' tests/test_gstack_role_prompts.py` exits 0
    - `pytest tests/ -x` exits 0 (full suite stays green; no regressions to 03-05 tests or earlier waves)
    - `ls clawteam/templates/gstack/prompts/*.md | wc -l` outputs `11`
    - `wc -c clawteam/templates/gstack/prompts/*.md | awk 'NR<=11 && $1>4096 {print "OVER:", $0; exit 1}' && echo OK | grep -q OK` (no per-file >4096; alternative: rely on the budget test)
  </acceptance_criteria>
  <done>tests/test_gstack_role_prompts.py extended with 3 new D-01/D-02/D-03 tests; D-14 gate tightened to 11; cross-file presence test un-xfailed and passing; suite stays green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Phase-5 stub content -> Phase-5 plan task swap | shipper.md and sre.md ship with `rubric:none` SIGNATURE flags so Phase 5's plan author can grep for them, swap rubric content in, and bump SIGNATURE to `rubric:ship` / `rubric:sre`. The `rubric:none` flag IS the trust handoff — if Phase 5 forgets to swap, the flag is still grep-detectable in CI. |
| engineer.md rubric content -> agent runtime (Phase 4+) | engineer.md instructs the engineer agent to defer bug-fixing to reviewer (no-fix-without-investigation). If an attacker-edited engineer.md removed this deferral, the engineer agent could apply unverified fixes and bypass reviewer's iron-law. Mitigated by golden grep test asserting the deferral language remains present. |
| <pending> literal string in shipper.md -> ShipNotes pydantic schema | The `<pending>` placeholder is explicitly accepted by ShipNotes per 03-03's `test_pending_deploy_url_accepted` (D-02 carve-out). If schema validation tightens later (Phase 5 likely closes this carve-out), the shipper.md instruction becomes stale; Phase 5's swap MUST update both files together. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-01 | Denial of Service | engineer.md exceeds 4096B budget after future content additions (e.g., a Phase 4 plan author adds /investigate routing examples and pushes it over the cap) | mitigate | D-14 budget test (`test_role_prompt_size_budget`) is a HARD gate in CI: `assert size <= 4096` per file fails the suite immediately. The test runs on every PR. The 03-06 author also documents the per-file target (~1200B for engineer.md) in the file header so future editors see the budget signal before adding content. |
| T-06-02 | Tampering | shipper.md and sre.md stubs ported into Phase 5 verbatim, blocking real /ship + /canary content (i.e., Phase 5's plan author copies the stub content thinking it's the real rubric) | mitigate | The SIGNATURE line `rubric:none` flags the stubs unambiguously — Phase 5's plan task description includes a grep step (`grep -l 'rubric:none' clawteam/templates/gstack/prompts/`) to identify which prompts need rubric content. After Phase 5 swap: SIGNATURE bumps to `rubric:ship` (shipper) and `rubric:sre` (sre). The `rubric:none` value is grep-asserted in this plan's tests so an accidental removal during Phase 5 work is caught. |
| T-06-03 | Spoofing | engineer.md instruction "no fix without investigation" deleted by future editor; engineer agent then applies unverified fixes bypassing reviewer's iron-law | mitigate | Test 1 (`test_engineer_implementation_discipline_rubric`) grep-asserts the no-fix-without-investigation deferral language remains present. Phase 4's SmartReviewRouter is the runtime enforcement layer (cross-agent verification); engineer.md's text is the policy declaration. Both must be present for the iron-law to hold. |
| T-06-04 | Information Disclosure | engineer.md or shipper.md cargo-cult an example secret / API key from upstream documentation | accept | All 3 prompts in this plan are greenfield prose (D-01/D-02/D-03 specify content from CONTEXT.md, not from upstream skill markdown). No external content fetched — no risk of carrying upstream secrets. Pre-commit secret scanner (existing project tool) covers any future edits. |

</threat_model>

<verification>
- 3 prompt files exist + are git-tracked: `ls clawteam/templates/gstack/prompts/{engineer,shipper,sre}.md` exits 0
- All 11 prompt files now present: `ls clawteam/templates/gstack/prompts/*.md | wc -l` outputs `11`
- engineer.md signature verbatim: grep passes
- shipper.md signature verbatim with `rubric:none`: grep passes
- sre.md signature verbatim with `rubric:none`: grep passes
- D-01 7 grep-verifiable content items present in engineer.md
- D-02 4 grep-verifiable content items present in shipper.md
- D-03 4 grep-verifiable content items present in sre.md
- D-14 budget gate now spans 11 files: `assert len(sizes) == 11` passes; max ≤ 4096B; average ≤ 3072B
- Cross-file presence test un-xfailed and passing: `pytest tests/test_gstack_role_prompts.py::test_all_eleven_prompt_files_present` exits 0
- No remaining xfails in test_gstack_role_prompts.py: `grep -c '@pytest.mark.xfail' tests/test_gstack_role_prompts.py` outputs `0`
- Suite stays green: `pytest tests/ -x` exits 0
</verification>

<success_criteria>
- TEAM-04 envelope-layer enforcement extended to engineer/shipper/sre: each prompt now references its envelope subclass + required field by name (engineer_diff_summary / shipper_step / sre_signal), so persona-spoofing payloads are caught at the prompt-instruction level in addition to the envelope/conductor layers from 03-04 and 03-01
- D-01 honored: engineer.md ships full implementation-discipline rubric (~1200B target, 4096B hard cap)
- D-02 honored: shipper.md ships honest Phase-5-deferred stub with `rubric:none` SIGNATURE flag
- D-03 honored: sre.md ships honest Phase-5-deferred stub with `rubric:none` SIGNATURE flag
- D-14 budget gate now spans all 11 prompts: max ≤ 4096B per file, average ≤ 3072B
- Cross-file presence test un-xfailed: 11 prompts confirmed at every CI run
- Phase 5 swap path is grep-discoverable: `grep -l 'rubric:none' clawteam/templates/gstack/prompts/` returns exactly shipper.md and sre.md
- Suite stays green: `pytest tests/ -x` exits 0
- No new dependencies; all 3 files are pure markdown prose
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-06-SUMMARY.md` covering:
- Three prompt files created (file paths + byte sizes)
- D-01 / D-02 / D-03 content checklist (which grep-verifiable item landed where)
- D-14 budget recomputation: max byte size, average byte size, pass/fail
- Test count delta in tests/test_gstack_role_prompts.py (3 new + 2 edited; total ≥ 13 active tests)
- Confirmation that 03-07 plugin's `contribute_prompts` hook will resolve all 11 (role, prompt) pairs (no missing files)
- Phase-5 swap roadmap: which 2 prompts (shipper, sre) carry the `rubric:none` flag for Phase 5 to swap
</output>
</content>
</invoke>