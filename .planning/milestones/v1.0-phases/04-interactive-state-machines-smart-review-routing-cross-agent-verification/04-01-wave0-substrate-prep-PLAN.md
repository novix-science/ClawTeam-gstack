---
phase: 04
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md
autonomous: true
requirements: [SPRINT-03, QUALITY-07, QUALITY-09, QUALITY-13]
must_haves:
  truths:
    - "Planner-assumed fnmatch.fnmatch doublestar behavior is verified (pick PurePosixPath.match if fnmatch fails)."
    - "ShipApprovalGate name collision with existing HumanApprovalGate(PhaseGate) is non-breaking (rename path chosen)."
    - "D-18 baseline marker count is confirmed exactly 4 lines at known locations."
    - "Spawn registry coroutine-safety (A3 assumption) is evidence-backed before Plan 10 implements asyncio.gather."
    - "A4 gap acknowledged: _dispatch_review_phase does NOT exist in conductor.py; Plan 10 creates it."
  artifacts:
    - path: ".planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md"
      provides: "Evidence-backed answers to A4/A5/A7/A9 + glob semantics + spawn sync-vs-async"
      contains: "## A4 _dispatch_review_phase"
  key_links:
    - from: "Plan 04 (ShipApprovalGate)"
      to: "PLAN_PREP_NOTES.md"
      via: "Uses chosen class name + file path"
    - from: "Plan 06 (GstackReviewRouter)"
      to: "PLAN_PREP_NOTES.md"
      via: "Uses chosen glob engine (fnmatch vs PurePosixPath.match)"
    - from: "Plan 10 (_dispatch_review_phase)"
      to: "PLAN_PREP_NOTES.md"
      via: "Uses chosen spawn-to-asyncio bridge pattern"
    - from: "Plan 14 (D-18 cleanup)"
      to: "PLAN_PREP_NOTES.md"
      via: "Uses baseline line-number map for grep assertions"
---

<objective>
Resolve the five research plan-prep verifications (A4 adjusted, A5 adjusted, A7 adjusted, A9 NEW, plus A3-gathered glob semantics) BEFORE substrate plans run, so downstream plans use evidence-backed implementation paths rather than re-guessing. Concrete output: one markdown notes file under the phase dir recording findings, chosen resolutions, and a 4-line baseline of Phase-3 meta-instruction locations for D-18 regression.

Purpose: Wave 0 is cheap insurance. Five small grep-and-script verifications cost ~15 context minutes combined but prevent Wave 1/2 plans from contradicting runtime reality (e.g., `fnmatch.fnmatch("src/a/b/c.tsx", "src/**/*.tsx")` being False would break router plan 06 if discovered at implementation time).

Output: `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md` with six sections (A4, A5, A7+A9, A-fnmatch, A-spawn, A-D18-baseline) plus a decision summary consumed verbatim by later plans.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-RESEARCH.md

<interfaces>
<!-- Key existing files Wave 0 will read (not modify). Evidence pins future plans. -->

From clawteam/sprint/conductor.py (575 LOC):
- def advance_phase(self, sprint_id: str, actor: str = "") -> tuple[bool, str]  # line 304
- def _build_gate_chain(self, state: SprintState) -> list  # line 517 — composes EvidenceGate → forced_progress_gate → InteractionGate
- force_interactive_phases=["ship"]  # lines 222, 247, 544 — already reserved for Phase 4
- NO _dispatch_review_phase method exists — Plan 10 MUST create it (A4 adjusted)

From clawteam/templates/__init__.py (187 LOC):
- _parse_toml reads keys: name, description, command, backend, leader, agents, tasks, leader_role, phases, model_profile, memory
- Unknown keys silently dropped — Plan 02/06 MUST add review_data parsing (A5 adjusted)

From clawteam/events/bus.py (121 LOC):
- emit(self, event: HarnessEvent) -> list[Any]  # line 86 — accepts typed dataclass events, NOT (name, payload) tuples (A7 rejected/adjusted)

From clawteam/harness/phases.py:91:
- class HumanApprovalGate(PhaseGate)  # EXISTING simple artifact-presence gate; name collides with Phase-4 planned class (A9 NEW)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Verify glob-matching engine for router patterns</name>
  <files>.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md</files>
  <read_first>
    - clawteam/harness/freeze_registry.py (lines 1-50 — existing fnmatch usage context)
  </read_first>
  <action>
Run a short Python snippet via `python3 -c` to empirically verify whether `fnmatch.fnmatch` handles doublestar `**` as recursive or literal. Also check `pathlib.PurePosixPath.match` as fallback. Record the chosen engine in PLAN_PREP_NOTES.md.

Exact commands to run:
```bash
python3 -c "
import fnmatch
from pathlib import PurePosixPath
tests = [
    ('src/components/Button.tsx',        'src/components/**/*.tsx'),
    ('src/components/forms/Input.tsx',   'src/components/**/*.tsx'),
    ('src/auth/middleware.py',            'src/auth/**'),
    ('src/auth/tokens/jwt.py',            'src/auth/**'),
    ('app/api/users/route.ts',            'app/api/**'),
    ('package.json',                      'package.json'),
    ('lib/crypto/aes.py',                 '**/crypto/**'),
]
print('== fnmatch.fnmatch (stdlib) ==')
for path, pat in tests:
    print(f'  {path!r:50s} vs {pat!r:30s} -> {fnmatch.fnmatch(path, pat)}')
print('== PurePosixPath.match ==')
for path, pat in tests:
    try:
        ok = PurePosixPath(path).match(pat)
    except Exception as e:
        ok = f'ERROR: {e}'
    print(f'  {path!r:50s} vs {pat!r:30s} -> {ok}')
"
```

Expected finding per RESEARCH A4 [ASSUMED]: `fnmatch.fnmatch` does NOT treat `**` as recursive; `PurePosixPath.match` in Python 3.13+ does.

In `PLAN_PREP_NOTES.md` under `## A-fnmatch: Glob engine selection`, record:
- Raw output of both engines
- CHOSEN ENGINE: one of `fnmatch` / `PurePosixPath.match` / `custom`
- Rationale

If BOTH engines fail some cases, write a `_match_path(path: str, pattern: str) -> bool` shim that: (a) if `**` in pattern, split on `/**/` and check prefix + suffix match via fnmatch on simpler segments, (b) fall back to fnmatch. Record the shim code verbatim so Plan 06 copies it.

Document for Plan 06: the function signature of the chosen matcher and the import line.
  </action>
  <verify>
    <automated>grep -q "CHOSEN ENGINE:" .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md</automated>
  </verify>
  <acceptance_criteria>
    - grep 'CHOSEN ENGINE:' .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md prints one match
    - Section ## A-fnmatch contains the raw python3 output (7 test cases × 2 engines)
    - Section records concrete matcher import line (e.g., `from fnmatch import fnmatch` OR `from pathlib import PurePosixPath`)
    - If shim needed, the shim function body is included verbatim in the section
  </acceptance_criteria>
  <done>PLAN_PREP_NOTES.md contains complete A-fnmatch section with raw empirical evidence + chosen engine name</done>
</task>

<task type="auto">
  <name>Task 2: Confirm A4 (no _dispatch_review_phase) + A11 (force_interactive_phases) + A9 (name collision)</name>
  <files>.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md</files>
  <read_first>
    - clawteam/sprint/conductor.py (entire file — scanning for phase-specific dispatch methods)
    - clawteam/harness/phases.py (line 91, HumanApprovalGate class)
  </read_first>
  <action>
Run three greps and record results:

```bash
# A4 confirmation: no _dispatch_*_phase methods exist today
grep -n '_dispatch_.*_phase\|def dispatch_review\|_dispatch_review' clawteam/sprint/conductor.py clawteam/sprint/*.py 2>/dev/null
# Expected: zero hits. Confirms Plan 10 must CREATE the method/file.

# A9 confirmation: existing HumanApprovalGate users
grep -rn 'HumanApprovalGate\|from clawteam.harness.phases import.*HumanApprovalGate\|phases\.HumanApprovalGate' clawteam/ tests/ 2>/dev/null

# A11 confirmation: force_interactive_phases plumbing
grep -n 'force_interactive_phases' clawteam/sprint/conductor.py clawteam/harness/*.py 2>/dev/null
```

In PLAN_PREP_NOTES.md under `## A4 _dispatch_review_phase`, record:
- Grep output (expect empty)
- DECISION: "Plan 10 creates new file `clawteam/sprint/review_phase.py` with top-level `async def dispatch_review_phase(state, plugin_manager, bus)` + SprintConductor gets a thin `_dispatch_review_phase(self, state)` wrapper that invokes `asyncio.run(dispatch_review_phase(...))` (preserves CORE-07 plain-JSON persistence)."
- Rationale: keeps conductor under 700 LOC.

Under `## A9 HumanApprovalGate name collision`, record:
- List of files importing `HumanApprovalGate`
- DECISION: "Phase 4 class is named `ShipApprovalGate` and lives at `clawteam/harness/ship_approval_gate.py`. Existing `HumanApprovalGate(PhaseGate)` at phases.py:91 is left untouched."
- Rationale: zero BC risk; grep-finds `ShipApprovalGate` surfaces all Phase-4 touchpoints cleanly.

Under `## A11 force_interactive_phases plumbing`, record:
- Exact line numbers where `force_interactive_phases` is referenced (expect 222, 239, 247, 544)
- DECISION: "ShipApprovalGate does not modify _build_gate_chain; it plugs into the gate list at phase=ship via `GstackSprintPlugin.contribute_gates` (existing hook at base.py:36). _build_gate_chain already inserts InteractionGate when `state.current_phase in self.force_interactive_phases`, and ShipApprovalGate is an InteractionGate subclass — Plan 04 subclass + Plan 11 plugin registration is sufficient."
  </action>
  <verify>
    <automated>grep -q "^## A4 " .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md && grep -q "^## A9 " .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md && grep -q "^## A11 " .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md</automated>
  </verify>
  <acceptance_criteria>
    - PLAN_PREP_NOTES.md has sections "## A4 _dispatch_review_phase", "## A9 HumanApprovalGate name collision", "## A11 force_interactive_phases plumbing"
    - Each section contains grep output
    - Each section has a DECISION: line with one sentence of rationale
    - A9 section explicitly names "ShipApprovalGate" and the file path "clawteam/harness/ship_approval_gate.py"
    - A4 section explicitly states the chosen file "clawteam/sprint/review_phase.py"
  </acceptance_criteria>
  <done>Three grep-verified decisions written to PLAN_PREP_NOTES.md</done>
</task>

<task type="auto">
  <name>Task 3: A5 TOML parser extension scope + A7 event-type shape confirmation + A-spawn sync-bridge + D-18 baseline</name>
  <files>.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md</files>
  <read_first>
    - clawteam/templates/__init__.py (entire file — _parse_toml at lines 99-130)
    - clawteam/events/bus.py (entire file — emit signature)
    - clawteam/events/types.py (lines 1-30 — HarnessEvent dataclass base)
    - clawteam/harness/spawner.py OR clawteam/harness/spawn_registry.py (whichever exists — look for coroutine-safety markers)
    - clawteam/templates/gstack/prompts/pm.md (line 18)
    - clawteam/templates/gstack/prompts/designer.md (line 17)
    - clawteam/templates/gstack/prompts/reviewer.md (lines 40, 45, 47)
  </read_first>
  <action>
Combined section for three substrate confirmations + D-18 baseline.

**A5 TOML parser extension scope:**
```bash
grep -n "tmpl\.get\|raw\.get" clawteam/templates/__init__.py
```
Record in `## A5 TOML parser gap`:
- List of currently-parsed top-level keys (expect: name, description, command, backend, leader, agents, tasks, leader_role, phases, model_profile, memory)
- CONFIRMED: `[template.review]` is not parsed today; Plan 02/06 must add `review_data = tmpl.get("review", {})` then parse nested rules.
- DECISION: "Plan 06 (GstackReviewRouter) adds `ReviewRule(BaseModel)` + `ReviewConfig(BaseModel)` classes to `clawteam/templates/__init__.py` AND extends `_parse_toml` with review parsing, as one atomic edit."

**A7 event-type shape:**
```bash
grep -n "def emit\|HarnessEvent\|@dataclass" clawteam/events/bus.py clawteam/events/types.py | head -20
```
Record in `## A7 EventBus emit signature`:
- CONFIRMED `emit(self, event: HarnessEvent) -> list[Any]` — takes typed dataclass objects, not (name, payload) tuples
- DECISION: "Plan 02 adds `@dataclass class MidReviewThrash(HarnessEvent)` and `@dataclass class SycophancyCascadeDetected(HarnessEvent)` to `clawteam/events/types.py`. Emission sites call `bus.emit(MidReviewThrash(team_name=..., sprint_id=..., ...))`."

**A-spawn sync-to-asyncio bridge:**
```bash
# Look for existing spawn machinery
ls clawteam/harness/ | grep -i spawn
grep -rn "class.*Spawn\|def spawn_agent\|async def spawn" clawteam/harness/ clawteam/team/ 2>/dev/null | head -10
```
Record in `## A-spawn asyncio bridge`:
- Names of relevant modules/functions
- CONCLUSION (pick one based on grep):
  - If spawn is synchronous (most likely): "Plan 10 uses `loop.run_in_executor(None, spawn_reviewer_sync, role, state, review_sha)` inside each `asyncio.gather` task"
  - If spawn is already `async def`: "Plan 10 calls it directly within `asyncio.gather`"
- Record the exact function name Plan 10 should wrap/call.

**D-18 baseline (A6 confirmation):**
```bash
grep -n "INTERACTIVE-RUNTIME-DEFERRED\|SHA-PIN-DEFERRED" clawteam/templates/gstack/prompts/*.md
```
Record in `## A6 D-18 marker baseline`:
- Exact output (expect 5 matches total: pm.md:18, designer.md:17, reviewer.md:40, reviewer.md:45 (header `## SHA-PIN-DEFERRED`), reviewer.md:47 (body))
- Note: research said "4 lines" but greppable count is 5 (header counts). DECISION: "D-18 cleanup target is grep count = 0. Plan 14 removes all 5 lines including the reviewer.md `## SHA-PIN-DEFERRED` H2 heading."
- Record the baseline line numbers for Plan 14 reference.

**Summary table at bottom of PLAN_PREP_NOTES.md:**
```markdown
## Decisions Summary (consumed by downstream plans)

| Item | Decision | Consuming Plan |
|------|----------|----------------|
| Glob engine | {fnmatch or PurePosixPath.match or shim} | Plan 06 |
| Review-phase dispatch | NEW file clawteam/sprint/review_phase.py | Plan 10 |
| Ship gate class name | ShipApprovalGate at clawteam/harness/ship_approval_gate.py | Plan 04 |
| TOML parser edit | Plan 06 extends _parse_toml + adds ReviewRule/ReviewConfig | Plan 06 |
| Event type shape | @dataclass MidReviewThrash + SycophancyCascadeDetected in types.py | Plan 02 |
| Spawn-asyncio bridge | {loop.run_in_executor OR direct await} around {function name} | Plan 10 |
| D-18 baseline | 5 grep hits across pm/designer/reviewer .md files at lines {N}/{N}/{N},{N},{N} | Plan 14 |
```
  </action>
  <verify>
    <automated>grep -c "^## A" .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md | awk '{ exit ($1 >= 6) ? 0 : 1 }'</automated>
  </verify>
  <acceptance_criteria>
    - PLAN_PREP_NOTES.md has at least 6 top-level sections starting with `## A` (A4, A5, A6, A7, A9, A11, A-fnmatch, A-spawn)
    - Section `## Decisions Summary` contains a markdown table with rows for all 7 summary items
    - Each row references the consuming plan number (Plan 02, Plan 04, Plan 06, Plan 10, Plan 14)
    - D-18 baseline exact line numbers recorded (format `pm.md:18`, `designer.md:17`, `reviewer.md:40`, `reviewer.md:45`, `reviewer.md:47`)
    - A-spawn section names at least one concrete function/module (empty placeholder rejected)
  </acceptance_criteria>
  <done>All 5 substrate concerns have evidence-backed decisions; summary table populated; downstream plans can grep PLAN_PREP_NOTES.md to resolve open questions</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| planner ↔ executor | Incorrect prep findings propagate into wrong substrate |
| git working tree ↔ grep scans | Stale results if grep run in wrong cwd |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-01 | I (Information disclosure) | Wave-0 notes file | mitigate | Notes file never contains secrets; all content is grep output of public source and planner decisions |
| T-04-02 | T (Tampering) | Grep run in wrong directory | mitigate | All commands use explicit relative paths (`clawteam/...`); no cd; planner lives at repo root |
| T-04-03 | R (Repudiation) | Decision provenance | accept | PLAN_PREP_NOTES.md is committed to git under `.planning/` — audit via `git log` |
</threat_model>

<verification>
Overall Wave 0 checks:
- [ ] `.planning/phases/04-.../PLAN_PREP_NOTES.md` exists and is non-empty
- [ ] All 3 tasks completed; PLAN_PREP_NOTES.md contains sections A4, A5, A6, A7, A9, A11, A-fnmatch, A-spawn, + Decisions Summary
- [ ] grep empirical output embedded for each section (not "TBD" / "assumed" language)
- [ ] Decisions Summary table has 7 populated rows
</verification>

<success_criteria>
Wave 0 is complete when:
- [ ] Plan 02 / 04 / 06 / 10 / 14 can each open PLAN_PREP_NOTES.md and find concrete implementation decisions (class names, file paths, function signatures, matcher engine)
- [ ] No downstream plan re-runs the same grep to reconfirm A4/A5/A7/A9/A11
- [ ] D-18 baseline line numbers are recorded for later regression assertion
- [ ] `grep -c "TBD\|TODO\|ASSUMED" PLAN_PREP_NOTES.md` returns 0 (all assumptions resolved into decisions)
</success_criteria>

<output>
After completion, create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-01-wave0-substrate-prep-SUMMARY.md` with:
- Chosen glob engine + function signature
- Confirmed file path for Plan 10's new module
- Confirmed class name for Plan 04's gate
- D-18 baseline line-number map
- Spawn-asyncio bridge pattern
- Any surprises that warrant plan-set revision
</output>
