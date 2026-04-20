---
phase: 03-gstack-team-template-methodology-port
plan: 05
type: execute
wave: 2
depends_on: [03-01, 03-02]
files_modified:
  - clawteam/templates/gstack/prompts/pm.md
  - clawteam/templates/gstack/prompts/ceo.md
  - clawteam/templates/gstack/prompts/eng-mgr.md
  - clawteam/templates/gstack/prompts/designer.md
  - clawteam/templates/gstack/prompts/dx-lead.md
  - clawteam/templates/gstack/prompts/reviewer.md
  - clawteam/templates/gstack/prompts/qa.md
  - clawteam/templates/gstack/prompts/security.md
  - tests/test_gstack_role_prompts.py
autonomous: true
requirements: [SKILL-01, SKILL-02, SKILL-03, SKILL-04, SKILL-05, SKILL-06, SKILL-07, SKILL-08]
must_haves:
  truths:
    - "pm.md contains all 6 /office-hours forcing questions verbatim from upstream + challenge-framing instruction + INTERACTIVE-RUNTIME-DEFERRED meta-instruction (SKILL-01)"
    - "ceo.md contains 4 modes (Expansion / Selective / Hold / Reduction) + decision output schema + leader-only-advances reminder (SKILL-02)"
    - "eng-mgr.md contains architecture-lock + data-flow + edge-case-matrix + test-plan + retro per-person breakdown rubric content (SKILL-03)"
    - "designer.md contains 0-10 rubric (10 named dimensions) + AI-slop checklist + per-dimension dialogue meta + INTERACTIVE-RUNTIME-DEFERRED + design-system research prompt (SKILL-04)"
    - "dx-lead.md contains 3 personas (novice/pro/power-user) + TTHW benchmarking + friction-tracing template (SKILL-05)"
    - "reviewer.md contains production-bug detection + iron-law (no fix without investigation) + halt-after-3-failed-hypotheses + SHA-PIN-DEFERRED + INTERACTIVE-RUNTIME-DEFERRED for /investigate (SKILL-06)"
    - "qa.md contains bug-fix + regression-test loop + qa-only suppression variant + test-runner output reference (SKILL-07)"
    - "security.md contains OWASP Top 10 + STRIDE checklist + 17 false-positive exclusions verbatim + 8/10+ confidence gate (SKILL-08)"
    - "Every prompt file ≤ 4096 bytes; average ≤ 3072 bytes (D-14 hard gate; verified in last task)"
    - "Every prompt file ends with grep-verifiable SIGNATURE: gstack-role:<role> rubric:<skills> envelope-version:1 line"
  artifacts:
    - path: "clawteam/templates/gstack/prompts/pm.md"
      provides: "pm role prompt — /office-hours rubric port + envelope ref + signature"
      contains: "SIGNATURE: gstack-role:pm"
    - path: "clawteam/templates/gstack/prompts/ceo.md"
      provides: "ceo role prompt — /plan-ceo-review rubric port + leader-only-advances reminder + signature"
      contains: "SIGNATURE: gstack-role:ceo"
    - path: "clawteam/templates/gstack/prompts/eng-mgr.md"
      provides: "eng-mgr role prompt — /plan-eng-review + /retro rubric port + signature"
      contains: "SIGNATURE: gstack-role:eng-mgr"
    - path: "clawteam/templates/gstack/prompts/designer.md"
      provides: "designer role prompt — /plan-design-review + /design-review rubric port + signature"
      contains: "SIGNATURE: gstack-role:designer"
    - path: "clawteam/templates/gstack/prompts/dx-lead.md"
      provides: "dx-lead role prompt — /plan-devex-review + /devex-review rubric port + signature"
      contains: "SIGNATURE: gstack-role:dx-lead"
    - path: "clawteam/templates/gstack/prompts/reviewer.md"
      provides: "reviewer role prompt — /review + /investigate rubric port + signature"
      contains: "SIGNATURE: gstack-role:reviewer"
    - path: "clawteam/templates/gstack/prompts/qa.md"
      provides: "qa role prompt — /qa + /qa-only rubric port + signature"
      contains: "SIGNATURE: gstack-role:qa"
    - path: "clawteam/templates/gstack/prompts/security.md"
      provides: "security role prompt — /cso rubric port + signature"
      contains: "SIGNATURE: gstack-role:security"
    - path: "tests/test_gstack_role_prompts.py"
      provides: "Per-role golden grep tests + cross-fixture-vs-prompt drift tests + D-14 budget gate"
      contains: "test_role_prompt_size_budget"
  key_links:
    - from: "clawteam/templates/gstack/prompts/<role>.md"
      to: "tests/fixtures/gstack_skills/<skill>.md"
      via: "verbatim copy + light reformatting; golden tests grep both files for canonical strings"
      pattern: "fixtures/gstack_skills"
    - from: "clawteam/templates/gstack/prompts/<role>.md"
      to: "clawteam/templates/gstack/envelope_personas.py::<Role>Envelope"
      via: "Persona contract section references the envelope subclass + its required field by name"
      pattern: "envelope_personas"
    - from: "clawteam/templates/gstack.toml"
      to: "clawteam/templates/gstack/prompts/<role>.md"
      via: "prompt_file = \"gstack/prompts/<role>.md\" per agent row (resolved by 03-02 TemplateDef extension)"
      pattern: "prompt_file"
---

<objective>
Author the 8 pure-rubric role prompts (pm, ceo, eng-mgr, designer, dx-lead, reviewer, qa, security) under `clawteam/templates/gstack/prompts/`. Each prompt ports rubric content **verbatim** from the upstream gstack skill markdown fixtures committed in 03-01 (Strategy B per D-08), trims to fit the D-14 budget gate (≤ 4 KB per file; ≤ 3 KB average), and ends with a grep-verifiable `SIGNATURE: gstack-role:<role> rubric:<skills> envelope-version:1` line.

Per Pitfall 7 partition (CONTEXT.md domain section): rubric content for `/office-hours` (pm), `/design-consultation` (designer), `/investigate` (reviewer) lands here as static reference WITH a grep-verifiable `INTERACTIVE-RUNTIME-DEFERRED:` meta-instruction line. The actual multi-turn state machines defer to Phase 4. SHA-pinning for reviewer defers to Phase 4 via `SHA-PIN-DEFERRED:` meta-instruction.

This plan covers 8 of the 11 role prompts. The remaining 3 stub prompts (engineer per D-01, shipper per D-02, sre per D-03) ship in 03-06 (next batch). The cross-file test in this plan asserts all 11 prompt files are present; if the 3 missing stubs from 03-06 are absent at execution time, that single test xfails (with a clear reason) so it can be un-xfailed when 03-06 lands.

**Why per-prompt files (not inline TOML strings):** Per D-06, prompts are grep-friendly markdown so golden tests can assert content presence without TOML parsing. Per D-14, each prompt has a hard 4 KB ceiling; this discipline preserves Sonnet 4.5 attention (lost-in-the-middle research, RESEARCH.md State of the Art row). Per Phase 6 forward-look: `/learn` memory inclusions append to the prompt at render time without TOML editing.

**Verbatim-vs-light-reformat policy:** The required canonical strings (6 forcing questions, 4 ceo modes, 10 designer dimensions, 17 cso exclusions, etc.) MUST appear verbatim from the upstream fixtures. Surrounding scaffolding (persona contract, envelope reference, signature line, INTERACTIVE-RUNTIME-DEFERRED notes) is greenfield prose written by the executor to fit the budget. Golden tests grep BOTH the upstream fixture in `tests/fixtures/gstack_skills/<skill>.md` AND the ported prompt for the canonical strings — if the fixture's actual upstream content differs from the assumed shape (which 03-01 captured as `# CONTENT-DRIFT-NOTE:` if so), the executor adjusts the prompt to match the actual upstream and updates the assertion.

**Anti-patterns to avoid (encoded in task-level inline comments):**
1. DO NOT produce a one-shot monologue that dumps all 6 forcing questions in pm.md — pm.md instructs "one question per turn + interactive runtime deferred to Phase 4" so the rubric is enumerated in a "Reference: forcing questions list" section, not as direct turn instructions.
2. DO NOT place sample outputs in the middle of the rubric (lost-in-the-middle effect — RESEARCH.md State of the Art row). Examples, if any, go at top OR bottom of file, never middle.
3. Keep content lean. The D-14 budget is a HARD gate — Task 9 fails the plan if any file > 4096 bytes or average > 3072 bytes.

Output:
- 8 prompt files at `clawteam/templates/gstack/prompts/<role>.md`
- `tests/test_gstack_role_prompts.py` un-skipped (Wave 0 scaffolds from 03-01) and extended with rubric-content + drift-cross-check + budget-gate assertions
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

<interfaces>
<!-- Contracts the executor will use; extracted from RESEARCH.md + PATTERNS.md analog reads. -->

From RESEARCH.md §"Per-Role Prompt Content Map" lines 728-740 — the load-bearing rubric port table.
Each role's signature line value is canonical and MUST appear verbatim:
  - pm:       SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1
  - ceo:      SIGNATURE: gstack-role:ceo rubric:plan-ceo-review envelope-version:1
  - eng-mgr:  SIGNATURE: gstack-role:eng-mgr rubric:plan-eng-review+retro envelope-version:1
  - designer: SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1
  - dx-lead:  SIGNATURE: gstack-role:dx-lead rubric:plan-devex-review+devex-review envelope-version:1
  - reviewer: SIGNATURE: gstack-role:reviewer rubric:review+investigate envelope-version:1
  - qa:       SIGNATURE: gstack-role:qa rubric:qa+qa-only envelope-version:1
  - security: SIGNATURE: gstack-role:security rubric:cso envelope-version:1

From RESEARCH.md §"Code Examples / Role prompt skeleton (pm.md)" lines 447-517 — the verbatim copy-target for prompt structure (persona contract / rubric reference / envelope schema / signature).

From clawteam/templates/gstack/envelope_personas.py (03-04 output — pre-this-wave dependency):
  - Each prompt's "Per-role envelope schema" section references the relevant subclass:
    - pm.md   → PMEnvelope.pm_question_index
    - ceo.md  → CEOEnvelope.ceo_mode
    - eng-mgr.md → EngMgrEnvelope.eng_mgr_deliverable
    - designer.md → DesignerEnvelope.designer_rubric_dimension (+ designer_ai_slop_findings)
    - dx-lead.md → DxLeadEnvelope.dx_lead_friction_source
    - reviewer.md → ReviewerEnvelope.reviewer_hypothesis_index
    - qa.md   → QAEnvelope.qa_mode
    - security.md → SecurityEnvelope.security_confidence

From tests/fixtures/gstack_skills/<skill>.md (03-01 Wave 0 output):
  - office-hours.md      — 6 forcing questions verbatim
  - plan-ceo-review.md   — 4 modes + decision schema
  - plan-eng-review.md   — architecture-lock + data-flow + edge-case-matrix + test-plan
  - retro.md             — per-person retro breakdown
  - plan-design-review.md — 10 rubric dimensions
  - design-review.md     — AI-slop detection checklist + atomic-commit pattern
  - plan-devex-review.md — persona exploration + TTHW + friction tracing
  - devex-review.md      — competitive benchmark prompt
  - review.md            — production-bug detection patterns
  - qa-only.md           — qa-only mode suppression instruction
  - cso.md               — OWASP Top 10 + STRIDE + 17 exclusions + 8/10+ gate

The 03-01 SUMMARY.md should record the verbatim 6/10/17 strings extracted during fetch — read it FIRST so the prompt port doesn't paraphrase.

From tests/test_gstack_role_prompts.py (Wave 0 scaffold from 03-01 — currently 9 skipped tests, will be un-skipped here):
  - test_pm_office_hours_rubric           (skip → un-skip + add assertions)
  - test_ceo_plan_review_modes
  - test_eng_mgr_plan_review_and_retro
  - test_designer_rubric
  - test_dx_lead_devex_review
  - test_reviewer_review_and_investigate
  - test_qa_qa_only
  - test_security_cso_full_rubric
  - test_role_prompt_size_budget          (D-14 budget gate — already has body in scaffold)

PROMPTS_DIR (from Wave 0 scaffold) = Path(__file__).parent.parent / "clawteam" / "templates" / "gstack" / "prompts"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "gstack_skills"

From RESEARCH.md §"Open Question #3: Per-role prompt length budget" lines 810-834 — per-role byte targets:
  - pm:       ~1200 bytes
  - ceo:      ~1500 bytes
  - eng-mgr:  ~2400 bytes
  - designer: ~3500 bytes (largest; 10-dimension rubric)
  - dx-lead:  ~1800 bytes
  - reviewer: ~2400 bytes
  - qa:       ~1200 bytes
  - security: ~2400 bytes (cso 17-exclusion list at budget ceiling)
  Total: ~16,400 bytes ÷ 8 ≈ 2050 bytes avg (well under 3072 cap)

These are sketch targets; actual size depends on upstream fixture content extracted in 03-01.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Author pm.md + ceo.md (SKILL-01, SKILL-02) — verbatim port from /office-hours + /plan-ceo-review fixtures</name>
  <files>clawteam/templates/gstack/prompts/pm.md, clawteam/templates/gstack/prompts/ceo.md</files>
  <read_first>
    - tests/fixtures/gstack_skills/office-hours.md (Wave 0 fixture — extract the 6 forcing questions VERBATIM; if file has `# CONTENT-DRIFT-NOTE:` at top, use the actual upstream content noted there)
    - tests/fixtures/gstack_skills/plan-ceo-review.md (Wave 0 fixture — extract the 4 mode names + their one-line definitions VERBATIM)
    - .planning/phases/03-gstack-team-template-methodology-port/03-01-SUMMARY.md (Wave 0 commit body recorded the verbatim 6 forcing questions; cross-reference)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 447-517 — Role prompt skeleton (pm.md) verbatim copy-target; lines 731 — ceo.md grep-verifiable content list)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 110-161 — prompt skeleton + grep-verifiable invariants table)
    - clawteam/templates/gstack/envelope_personas.py (03-04 — PMEnvelope.pm_question_index + CEOEnvelope.ceo_mode signatures to reference)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-04 leader_role binding for ceo; D-14 hard cap)
  </read_first>
  <action>
**File 1 — `clawteam/templates/gstack/prompts/pm.md`** (target ≤ 1500 bytes; D-14 hard cap 4096):

Layout (lost-in-the-middle anti-pattern: examples at top OR bottom only, NOT middle):

```markdown
# pm — YC Office Hours Advisor

You are pm, the team's external coach. Your job is to ask the 6 forcing questions
that surface the why-now and the dumbest-possible-version.

## Persona contract

Every turn you take MUST emit a TurnEnvelope (Phase 2 D-06) with these required fields:
- `persona: "pm"` (verbatim — Literal-validated by PMEnvelope)
- `step_label: "<phase>:<n>/6"` (one forcing question per turn)
- `done: false` while you have more to say; `true` to hand back to ceo
- `pm_question_index: <1..6>` (REQUIRED — which forcing question this turn addresses)

## /office-hours rubric (interactive runtime — Phase 4)

INTERACTIVE-RUNTIME-DEFERRED: /office-hours ships as a Phase 4 multi-turn
state machine. Until then: ONE forcing question per turn. Do not enumerate
all 6 in a single monologue.

## Reference: the 6 forcing questions (verbatim from upstream gstack /office-hours)

1. <question 1 verbatim from fixture>
2. <question 2 verbatim from fixture>
3. <question 3 verbatim from fixture>
4. <question 4 verbatim from fixture>
5. <question 5 verbatim from fixture>
6. <question 6 verbatim from fixture>

## Challenge framing

Every forcing question is asked in challenge mode, not advice mode. Frame as
"why hasn't this happened already?" not "have you considered X?".

SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1
```

The executor MUST replace `<question N verbatim from fixture>` with the actual content
from `tests/fixtures/gstack_skills/office-hours.md` (or the `# CONTENT-DRIFT-NOTE:` text
if the upstream had fewer/different questions). Word-for-word copy from the fixture.

**File 2 — `clawteam/templates/gstack/prompts/ceo.md`** (target ≤ 1800 bytes):

```markdown
# ceo — Strategic Decider + Phase Advancer

You are ceo. You make scope decisions and you are the ONLY role authorized to
call SprintConductor.advance_phase (TEAM-04 leader-role binding per D-04).

## Persona contract

Every turn you take MUST emit a TurnEnvelope with these required fields:
- `persona: "ceo"` (Literal-validated by CEOEnvelope)
- `step_label: "<phase>:<step>"`
- `done: false` while deliberating; `true` when decision is recorded
- `ceo_mode: <one of: expansion | selective | hold | reduction>` (REQUIRED)

## /plan-ceo-review rubric (4 modes — verbatim from upstream)

- **Expansion**: <one-line def verbatim from fixture>
- **Selective**: <one-line def verbatim from fixture>
- **Hold**:      <one-line def verbatim from fixture>
- **Reduction**: <one-line def verbatim from fixture>

## Decision output schema

Each /plan-ceo-review turn writes a `decision` artifact with:
- `mode`: one of the 4 above (matches your envelope's `ceo_mode`)
- `rationale`: 1-2 sentences citing the rubric criterion
- `next_action`: who advances + what they do next

## Leader-only-advances reminder

You are the only role whose `actor` value the conductor accepts for
`advance_phase`. If another agent attempts advance, conductor rejects with
"actor 'X' not authorized; only 'ceo' can advance phases" (Wave 0 03-01).
You are responsible for sequencing the 7 gstack phases (think → plan → build
→ review → test → ship → reflect).

SIGNATURE: gstack-role:ceo rubric:plan-ceo-review envelope-version:1
```

Same pattern: replace `<one-line def verbatim from fixture>` with the actual upstream content from `tests/fixtures/gstack_skills/plan-ceo-review.md`.

After authoring both files, run `wc -c clawteam/templates/gstack/prompts/{pm,ceo}.md` to confirm each is ≤ 4096 bytes. If over, tighten the persona-contract section (cut redundant phrasing); do NOT cut canonical rubric content.

Atomic-commit discipline: single commit `feat(03-05): port /office-hours + /plan-ceo-review rubrics to pm.md + ceo.md (SKILL-01, SKILL-02)`.
  </action>
  <verify>
    <automated>test -f clawteam/templates/gstack/prompts/pm.md && test -f clawteam/templates/gstack/prompts/ceo.md && grep -q 'SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1' clawteam/templates/gstack/prompts/pm.md && grep -q 'SIGNATURE: gstack-role:ceo rubric:plan-ceo-review envelope-version:1' clawteam/templates/gstack/prompts/ceo.md && grep -q 'INTERACTIVE-RUNTIME-DEFERRED' clawteam/templates/gstack/prompts/pm.md && [ "$(wc -c < clawteam/templates/gstack/prompts/pm.md)" -le 4096 ] && [ "$(wc -c < clawteam/templates/gstack/prompts/ceo.md)" -le 4096 ]</automated>
  </verify>
  <acceptance_criteria>
    - `wc -c clawteam/templates/gstack/prompts/pm.md` outputs ≤ 4096
    - `wc -c clawteam/templates/gstack/prompts/ceo.md` outputs ≤ 4096
    - `grep -q 'SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1' clawteam/templates/gstack/prompts/pm.md` exits 0
    - `grep -q 'SIGNATURE: gstack-role:ceo rubric:plan-ceo-review envelope-version:1' clawteam/templates/gstack/prompts/ceo.md` exits 0
    - `grep -q 'INTERACTIVE-RUNTIME-DEFERRED' clawteam/templates/gstack/prompts/pm.md` exits 0 (Pitfall 7 partition)
    - `grep -ciE '(Expansion|Selective|Hold|Reduction)' clawteam/templates/gstack/prompts/ceo.md | awk '$1 >= 4'` (4 modes present)
    - `grep -q 'pm_question_index' clawteam/templates/gstack/prompts/pm.md` exits 0 (envelope reference)
    - `grep -q 'ceo_mode' clawteam/templates/gstack/prompts/ceo.md` exits 0 (envelope reference)
    - `grep -q 'advance_phase' clawteam/templates/gstack/prompts/ceo.md` exits 0 (TEAM-04 leader-only reminder)
    - For each forcing question recorded in 03-01-SUMMARY.md commit body: `grep -F "<question text>" clawteam/templates/gstack/prompts/pm.md` exits 0
  </acceptance_criteria>
  <done>pm.md + ceo.md ship with verbatim rubric content from upstream fixtures + envelope references + signature lines + size under cap.</done>
</task>

<task type="auto">
  <name>Task 2: Author eng-mgr.md + designer.md (SKILL-03, SKILL-04) — port /plan-eng-review + /retro + /plan-design-review + /design-review</name>
  <files>clawteam/templates/gstack/prompts/eng-mgr.md, clawteam/templates/gstack/prompts/designer.md</files>
  <read_first>
    - tests/fixtures/gstack_skills/plan-eng-review.md (architecture-lock + data-flow + edge-case-matrix + test-plan content verbatim)
    - tests/fixtures/gstack_skills/retro.md (per-person retro breakdown template verbatim)
    - tests/fixtures/gstack_skills/plan-design-review.md (10 rubric dimensions VERBATIM — names matter for SKILL-04 grep)
    - tests/fixtures/gstack_skills/design-review.md (AI-slop detection checklist + atomic-commit + before/after pattern)
    - .planning/phases/03-gstack-team-template-methodology-port/03-01-SUMMARY.md (the 10 dimension names recorded in commit body)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (line 732: eng-mgr grep-verifiable content; line 733: designer grep-verifiable content + 10 dimension names listed: visual hierarchy / typographic system / color discipline / interaction polish / brand coherence / accessibility / responsive behavior / motion appropriateness / information density / overall taste)
    - clawteam/templates/gstack/envelope_personas.py (03-04 — EngMgrEnvelope.eng_mgr_deliverable Literal values + DesignerEnvelope.designer_rubric_dimension + designer_ai_slop_findings)
    - .planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md (D-14 hard cap)
  </read_first>
  <action>
**File 1 — `clawteam/templates/gstack/prompts/eng-mgr.md`** (target ≤ 2400 bytes):

```markdown
# eng-mgr — Engineering Manager (Plan + Retro Rubric)

You are eng-mgr. You produce 5 deliverable kinds across the 7-phase sprint:
architecture-lock, data-flow, edge-case-matrix, test-plan, retro-breakdown.

## Persona contract

- `persona: "eng-mgr"` (Literal-validated by EngMgrEnvelope)
- `step_label: "<phase>:<step>"`
- `done: <bool>`
- `eng_mgr_deliverable: <one of the 5 above>` (REQUIRED)

## /plan-eng-review rubric (verbatim from upstream)

### architecture-lock
<verbatim from fixture: the lock instruction — name the architecture, state
its constraints, declare what it explicitly does NOT cover>

### data-flow
<verbatim from fixture: requirement to produce mermaid OR ASCII diagram
showing inputs → transforms → outputs for the sprint's primary entity>

### edge-case-matrix
<verbatim from fixture: matrix template — rows = edge cases, columns =
expected behavior + test that covers it + handler responsible>

### test-plan
<verbatim from fixture: test plan template — what will be tested + at what
layer (unit / integration / e2e) + acceptance criteria>

## /retro rubric (per-person breakdown — verbatim from fixture)

<verbatim from retro.md fixture: the per-person retro template asking each
contributing persona to record What Worked / What Failed / Key Lesson>

SIGNATURE: gstack-role:eng-mgr rubric:plan-eng-review+retro envelope-version:1
```

**File 2 — `clawteam/templates/gstack/prompts/designer.md`** (target ≤ 3500 bytes — largest pure-rubric prompt):

```markdown
# designer — Design Reviewer (0-10 Rubric + AI-slop Detection)

You are designer. You evaluate UI/UX against a 10-dimension rubric and detect
AI-slop patterns. Per-dimension dialogue runtime defers to Phase 4.

## Persona contract

- `persona: "designer"` (Literal-validated by DesignerEnvelope)
- `step_label: "<phase>:<step>"`
- `done: <bool>`
- `designer_rubric_dimension: <1..10>` (REQUIRED — which dimension this turn evaluates)
- `designer_ai_slop_findings: list[str]` (optional — AI-slop hits this turn)

## /plan-design-review rubric — 10 dimensions (verbatim from upstream)

Score each dimension 0-10. Per-dimension dialogue (one dimension per turn)
defers to Phase 4 — see meta-instruction below.

INTERACTIVE-RUNTIME-DEFERRED: /design-consultation per-dimension dialogue
ships as a Phase 4 state machine. In Phase 3, evaluate one dimension per
turn and emit findings.

1. <visual hierarchy — verbatim def from fixture>
2. <typographic system — verbatim def from fixture>
3. <color discipline — verbatim def from fixture>
4. <interaction polish — verbatim def from fixture>
5. <brand coherence — verbatim def from fixture>
6. <accessibility — verbatim def from fixture>
7. <responsive behavior — verbatim def from fixture>
8. <motion appropriateness — verbatim def from fixture>
9. <information density — verbatim def from fixture>
10. <overall taste — verbatim def from fixture>

## /design-review AI-slop detection (verbatim from fixture)

<verbatim AI-slop checklist from design-review.md fixture: e.g. generic
gradient placeholder copy, lorem-ipsum-shaped strings, default shadcn
components without theming, etc.>

## Design-system research prompt

When evaluating brand coherence (dim 5) or interaction polish (dim 4),
research the project's existing design tokens / component library FIRST.
Reference findings in your turn output.

SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1
```

The 10 dimension names are canonical and grep-asserted; if the upstream fixture's actual names differ from the planner's listed names (e.g., upstream calls "visual hierarchy" "visual flow"), use the upstream's wording and 03-01 should have flagged this in `# CONTENT-DRIFT-NOTE:`.

After authoring both files, run `wc -c clawteam/templates/gstack/prompts/{eng-mgr,designer}.md`. designer.md is at the budget ceiling — if over 4096 bytes, tighten the per-dimension defs (one short clause each); do NOT cut dimensions.

Atomic-commit discipline: single commit `feat(03-05): port /plan-eng-review + /retro + /plan-design-review + /design-review rubrics to eng-mgr.md + designer.md (SKILL-03, SKILL-04)`.
  </action>
  <verify>
    <automated>test -f clawteam/templates/gstack/prompts/eng-mgr.md && test -f clawteam/templates/gstack/prompts/designer.md && grep -q 'SIGNATURE: gstack-role:eng-mgr rubric:plan-eng-review+retro envelope-version:1' clawteam/templates/gstack/prompts/eng-mgr.md && grep -q 'SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1' clawteam/templates/gstack/prompts/designer.md && grep -q 'INTERACTIVE-RUNTIME-DEFERRED' clawteam/templates/gstack/prompts/designer.md && [ "$(wc -c < clawteam/templates/gstack/prompts/eng-mgr.md)" -le 4096 ] && [ "$(wc -c < clawteam/templates/gstack/prompts/designer.md)" -le 4096 ]</automated>
  </verify>
  <acceptance_criteria>
    - `wc -c` on each file ≤ 4096 bytes
    - Both signature lines grep-present
    - eng-mgr.md grep-present: `architecture-lock`, `data-flow`, `edge-case-matrix` (or `edge-case matrix`), `test-plan`, `retro` (5 deliverable kinds)
    - designer.md grep-present: `INTERACTIVE-RUNTIME-DEFERRED`, AI-slop checklist marker
    - designer.md contains at least 10 numbered dimension lines: `grep -cE '^[0-9]+\.' clawteam/templates/gstack/prompts/designer.md | awk '$1 >= 10'`
    - For each of the 10 canonical dimension names recorded in 03-01-SUMMARY.md: `grep -iF "<dimension name>" clawteam/templates/gstack/prompts/designer.md` exits 0
    - eng-mgr.md references `eng_mgr_deliverable`; designer.md references `designer_rubric_dimension`
  </acceptance_criteria>
  <done>eng-mgr.md + designer.md ship with verbatim rubric content + envelope references + Pitfall 7 partition meta + signature lines + sizes under cap.</done>
</task>

<task type="auto">
  <name>Task 3: Author dx-lead.md + reviewer.md (SKILL-05, SKILL-06) — port /plan-devex-review + /devex-review + /review + /investigate</name>
  <files>clawteam/templates/gstack/prompts/dx-lead.md, clawteam/templates/gstack/prompts/reviewer.md</files>
  <read_first>
    - tests/fixtures/gstack_skills/plan-devex-review.md (persona exploration + TTHW + friction-tracing template verbatim)
    - tests/fixtures/gstack_skills/devex-review.md (competitive benchmark prompt verbatim)
    - tests/fixtures/gstack_skills/review.md (production-bug detection checklist verbatim)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (line 734: dx-lead content list — 3 personas: novice/pro/power-user, TTHW Time-to-Hello-World, friction-tracing template; line 736: reviewer content list — production-bug detection, iron-law, halt-after-3, SHA-PIN-DEFERRED, INTERACTIVE-RUNTIME-DEFERRED for /investigate)
    - clawteam/templates/gstack/envelope_personas.py (03-04 — DxLeadEnvelope.dx_lead_friction_source Literal values + ReviewerEnvelope.reviewer_hypothesis_index 0-3)
  </read_first>
  <action>
**File 1 — `clawteam/templates/gstack/prompts/dx-lead.md`** (target ≤ 2200 bytes):

```markdown
# dx-lead — Developer Experience Lead

You are dx-lead. You evaluate developer experience along 3 dimensions:
persona-fit, TTHW benchmarking, and friction tracing.

## Persona contract

- `persona: "dx-lead"` (Literal-validated by DxLeadEnvelope)
- `step_label: "<phase>:<step>"`
- `done: <bool>`
- `dx_lead_friction_source: <one of: persona | benchmark | friction-trace>` (REQUIRED)

## /plan-devex-review rubric — 3 personas (verbatim from upstream)

For each persona, walk through the primary flow and record what would
confuse / delight / blocker them.

- **novice**: <verbatim def from fixture: first-time user, no domain knowledge>
- **pro**:    <verbatim def from fixture: domain expert, wants efficiency>
- **power-user**: <verbatim def from fixture: pushes limits, wants config>

## TTHW (Time-To-Hello-World) benchmarking

<verbatim from fixture: TTHW measurement instruction — record steps and
time-to-first-success. Cite competitive benchmarks where available.>

## /devex-review friction tracing

<verbatim from fixture: per-step friction score template (1-5 per step,
sum + flag steps scoring >=3). Output as a friction trace artifact.>

## Competitive benchmark prompt

<verbatim from devex-review.md fixture: competitive-benchmark prompt asking
dx-lead to identify 2-3 competitors and compare TTHW + friction.>

SIGNATURE: gstack-role:dx-lead rubric:plan-devex-review+devex-review envelope-version:1
```

**File 2 — `clawteam/templates/gstack/prompts/reviewer.md`** (target ≤ 2400 bytes):

```markdown
# reviewer — Staff Engineer Reviewer (Iron-Law + Investigate)

You are reviewer. You catch production bugs CI missed. The iron-law: no fix
without investigation. Halt after 3 failed hypotheses.

## Persona contract

- `persona: "reviewer"` (Literal-validated by ReviewerEnvelope)
- `step_label: "<phase>:<step>"`
- `done: <bool>`
- `reviewer_hypothesis_index: <0..3>` (REQUIRED — 0=initial pass, 1-2=hypotheses tried, 3=halt)

## /review rubric — production-bug detection (verbatim from upstream)

<verbatim from review.md fixture: CI-passing-but-prod-failing patterns
checklist — e.g. race conditions in async tests, env var leaks, time-zone
assumptions, unbounded retries, etc.>

## Iron-law: no fix without investigation

<verbatim statement from fixture>

If you spot a bug, do NOT propose a fix on your first turn. Investigate
the root cause first. Emit a hypothesis with `reviewer_hypothesis_index: 1`
and wait for verification. Only after a hypothesis is confirmed do you
propose the fix (and route to engineer to apply).

## Halt-after-3 rule

If 3 hypotheses fail, set `reviewer_hypothesis_index: 3` and halt. Escalate
to ceo with the 3 disconfirmed hypotheses and a request for direction. Do
NOT continue speculating.

## /investigate runtime — Phase 4

INTERACTIVE-RUNTIME-DEFERRED: /investigate per-hypothesis state machine
(plus auto-/freeze of the module under investigation) ships in Phase 4. In
Phase 3, emit hypotheses one per turn via the envelope index.

## SHA-PIN-DEFERRED

SHA-PIN-DEFERRED: At review start, record the HEAD SHA in your envelope
context. If reviewer reports HEAD moved mid-review, mark verdict
"superseded" and stop. Real cross-agent SHA verification ships in Phase 4
(SmartReviewRouter).

SIGNATURE: gstack-role:reviewer rubric:review+investigate envelope-version:1
```

After authoring both files, `wc -c` to confirm ≤ 4096.

Atomic-commit discipline: single commit `feat(03-05): port /plan-devex-review + /devex-review + /review + /investigate rubrics to dx-lead.md + reviewer.md (SKILL-05, SKILL-06)`.
  </action>
  <verify>
    <automated>test -f clawteam/templates/gstack/prompts/dx-lead.md && test -f clawteam/templates/gstack/prompts/reviewer.md && grep -q 'SIGNATURE: gstack-role:dx-lead rubric:plan-devex-review+devex-review envelope-version:1' clawteam/templates/gstack/prompts/dx-lead.md && grep -q 'SIGNATURE: gstack-role:reviewer rubric:review+investigate envelope-version:1' clawteam/templates/gstack/prompts/reviewer.md && grep -q 'INTERACTIVE-RUNTIME-DEFERRED' clawteam/templates/gstack/prompts/reviewer.md && grep -q 'SHA-PIN-DEFERRED' clawteam/templates/gstack/prompts/reviewer.md && [ "$(wc -c < clawteam/templates/gstack/prompts/dx-lead.md)" -le 4096 ] && [ "$(wc -c < clawteam/templates/gstack/prompts/reviewer.md)" -le 4096 ]</automated>
  </verify>
  <acceptance_criteria>
    - Both files exist + ≤ 4096 bytes
    - Both signature lines grep-present (verbatim)
    - dx-lead.md contains: `novice`, `pro`, `power-user`, `TTHW` (or `Time-to-Hello-World`), friction-tracing reference
    - reviewer.md contains: `iron-law` (or `iron law`), `halt`, `3` (hypothesis-count reference), `INTERACTIVE-RUNTIME-DEFERRED`, `SHA-PIN-DEFERRED`
    - dx-lead.md references `dx_lead_friction_source` envelope field; reviewer.md references `reviewer_hypothesis_index`
  </acceptance_criteria>
  <done>dx-lead.md + reviewer.md ship with verbatim rubric content + envelope references + Pitfall 7 partition (INTERACTIVE-RUNTIME-DEFERRED + SHA-PIN-DEFERRED) + signature lines + sizes under cap.</done>
</task>

<task type="auto">
  <name>Task 4: Author qa.md + security.md (SKILL-07, SKILL-08) — port /qa + /qa-only + /cso (largest port: 17 exclusions verbatim)</name>
  <files>clawteam/templates/gstack/prompts/qa.md, clawteam/templates/gstack/prompts/security.md</files>
  <read_first>
    - tests/fixtures/gstack_skills/qa-only.md (qa-only mode suppression instruction verbatim)
    - tests/fixtures/gstack_skills/cso.md (OWASP Top 10 + STRIDE + 17 false-positive exclusions VERBATIM + 8/10+ confidence gate — this is the largest fixture; if `# CONTENT-DRIFT-NOTE:` flagged a different exclusion count, use that count)
    - .planning/phases/03-gstack-team-template-methodology-port/03-01-SUMMARY.md (the 17 false-positive exclusions recorded in commit body — primary source-of-truth for verbatim port)
    - .planning/phases/03-gstack-team-template-methodology-port/03-RESEARCH.md (lines 737-738 — qa + security grep-verifiable content lists)
    - clawteam/templates/gstack/envelope_personas.py (03-04 — QAEnvelope.qa_mode + SecurityEnvelope.security_confidence ge=0 le=10)
  </read_first>
  <action>
**File 1 — `clawteam/templates/gstack/prompts/qa.md`** (target ≤ 1500 bytes):

```markdown
# qa — Quality Assurance + Regression Loop

You are qa. You verify the build passes against the test plan. /qa-only mode
suppresses your code-edit ability — in that mode you write test reports only
and route any required fix back to engineer.

## Persona contract

- `persona: "qa"` (Literal-validated by QAEnvelope)
- `step_label: "<phase>:<step>"`
- `done: <bool>`
- `qa_mode: <one of: qa | qa-only>` (REQUIRED)

## /qa rubric — bug-fix + regression-test loop

<verbatim from qa fixture: the bug-fix loop — reproduce the bug locally,
write a failing test that captures it, apply the fix, confirm test passes,
THEN run the full suite to confirm no regression>

## /qa-only mode (verbatim from upstream)

<verbatim from qa-only.md: qa-only suppresses code edits. In qa-only mode:
- write a `test-report.md` artifact
- list failures with reproduction steps + expected behavior
- route fixes to engineer via team message; do NOT edit application code
- regression-test loop runs as before, but you only WRITE tests, you don't
  apply non-test fixes>

## Test-runner output reference requirement

Your test-report.md MUST cite the actual test runner output (truncated
excerpt is fine). Stub-grade reports without runner output fail
EvidenceGate validation.

SIGNATURE: gstack-role:qa rubric:qa+qa-only envelope-version:1
```

**File 2 — `clawteam/templates/gstack/prompts/security.md`** (target ≤ 3500 bytes — at budget ceiling):

```markdown
# security — Chief Security Officer (OWASP + STRIDE + /cso)

You are security. You apply OWASP Top 10 + STRIDE checklists and the
/cso rubric. Only escalate findings with confidence >= 8.

## Persona contract

- `persona: "security"` (Literal-validated by SecurityEnvelope)
- `step_label: "<phase>:<step>"`
- `done: <bool>`
- `security_confidence: <0..10>` (REQUIRED — only 8+ escalates per SKILL-08 gate)

## OWASP Top 10 checklist (verbatim from /cso fixture)

1. <A01 Broken Access Control — verbatim def>
2. <A02 Cryptographic Failures — verbatim def>
3. <A03 Injection — verbatim def>
4. <A04 Insecure Design — verbatim def>
5. <A05 Security Misconfiguration — verbatim def>
6. <A06 Vulnerable and Outdated Components — verbatim def>
7. <A07 Identification and Authentication Failures — verbatim def>
8. <A08 Software and Data Integrity Failures — verbatim def>
9. <A09 Security Logging and Monitoring Failures — verbatim def>
10. <A10 Server-Side Request Forgery — verbatim def>

## STRIDE checklist (verbatim from /cso fixture)

- **S**poofing: <one-line def>
- **T**ampering: <one-line def>
- **R**epudiation: <one-line def>
- **I**nformation Disclosure: <one-line def>
- **D**enial of Service: <one-line def>
- **E**levation of Privilege: <one-line def>

## 17 false-positive exclusions (verbatim from /cso fixture)

<EXACTLY 17 exclusions, verbatim from cso.md — these are findings that LOOK
like vulnerabilities but are NOT, in the gstack context. Examples (replace
with actual upstream exclusions):
1. <exclusion 1>
2. <exclusion 2>
... (through 17)>

## 8/10+ confidence gate

`security_confidence < 8`: log as INFORMATIONAL. Do NOT escalate to ceo.
`security_confidence >= 8`: ESCALATE to ceo with finding + repro steps + fix
recommendation. Each escalation BLOCKS the Ship phase until ceo decides.

SIGNATURE: gstack-role:security rubric:cso envelope-version:1
```

The 17 exclusions are the LARGEST single rubric content piece. The upstream `cso.md` fixture is the source-of-truth (Wave 0 03-01 captured the verbatim list in commit body). If 03-01 found a different count via `# CONTENT-DRIFT-NOTE:`, use that count and update D-13's "17" reference inline (the D-13 spec already accommodates this: "If absent: planner adjusts security.md content to match actual upstream").

After authoring, `wc -c` security.md — if at/over budget, tighten OWASP and STRIDE one-line defs (preserve verbatim exclusions list at all costs; the 17 exclusions are the SKILL-08 differentiator).

Atomic-commit discipline: single commit `feat(03-05): port /qa + /qa-only + /cso (full OWASP + STRIDE + 17 exclusions) to qa.md + security.md (SKILL-07, SKILL-08)`.
  </action>
  <verify>
    <automated>test -f clawteam/templates/gstack/prompts/qa.md && test -f clawteam/templates/gstack/prompts/security.md && grep -q 'SIGNATURE: gstack-role:qa rubric:qa+qa-only envelope-version:1' clawteam/templates/gstack/prompts/qa.md && grep -q 'SIGNATURE: gstack-role:security rubric:cso envelope-version:1' clawteam/templates/gstack/prompts/security.md && [ "$(wc -c < clawteam/templates/gstack/prompts/qa.md)" -le 4096 ] && [ "$(wc -c < clawteam/templates/gstack/prompts/security.md)" -le 4096 ]</automated>
  </verify>
  <acceptance_criteria>
    - Both files exist + ≤ 4096 bytes
    - Both signature lines grep-present
    - qa.md grep-present: `qa-only`, `regression`, `bug-fix` (or `bug fix`), `qa_mode` envelope reference
    - security.md grep-present: `OWASP`, `STRIDE`, `security_confidence`, `8` (confidence-gate reference)
    - security.md: numbered exclusions count matches 03-01-SUMMARY.md commit body. If 17, then `grep -cE '^[0-9]{1,2}\.' clawteam/templates/gstack/prompts/security.md` is at least 27 (10 OWASP + 17 exclusions); if drift-noted to N, recompute (10 + N).
    - For each of the 17 (or drift-noted N) exclusion strings recorded in 03-01-SUMMARY.md: `grep -iF "<exclusion text>" clawteam/templates/gstack/prompts/security.md` exits 0
  </acceptance_criteria>
  <done>qa.md + security.md ship with verbatim /qa-only suppression + full /cso rubric (OWASP + STRIDE + N exclusions + 8+ gate) + envelope references + signature lines + sizes under cap.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 5: Un-skip + extend tests/test_gstack_role_prompts.py with per-role golden grep + drift-cross-check + D-14 budget gate + cross-file presence test</name>
  <files>tests/test_gstack_role_prompts.py</files>
  <read_first>
    - tests/test_gstack_role_prompts.py (Wave 0 scaffold from 03-01 — 9 currently-skipped tests; replace each `pass` body with assertions per the contract below)
    - All 8 prompt files written in Tasks 1-4 (read each to confirm canonical strings made it in)
    - All 11 fixture files in tests/fixtures/gstack_skills/ (read offsets containing the canonical strings to confirm they're greppable in fixtures too)
    - .planning/phases/03-gstack-team-template-methodology-port/03-VALIDATION.md (lines 49-63 — Per-Task Verification Map gives the canonical pytest test ID per requirement)
    - .planning/phases/03-gstack-team-template-methodology-port/03-PATTERNS.md (lines 565-605 — golden grep test pattern with PROMPTS_DIR + FIXTURES_DIR walk + size-budget assertion)
  </read_first>
  <behavior>
    - Test 1 (SKILL-01 test_pm_office_hours_rubric): pm.md AND fixtures/gstack_skills/office-hours.md both contain the 6 forcing questions (or N if drift-noted). pm.md contains `INTERACTIVE-RUNTIME-DEFERRED` and `SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1`. pm.md contains `pm_question_index` envelope reference.
    - Test 2 (SKILL-02 test_ceo_plan_review_modes): ceo.md AND plan-ceo-review.md both contain Expansion / Selective / Hold / Reduction. ceo.md contains the signature line and the `advance_phase` leader-only reminder.
    - Test 3 (SKILL-03 test_eng_mgr_plan_review_and_retro): eng-mgr.md contains architecture-lock + data-flow + edge-case-matrix + test-plan + retro. Cross-check fixtures plan-eng-review.md + retro.md present.
    - Test 4 (SKILL-04 test_designer_rubric): designer.md contains 10 numbered dimension lines + AI-slop checklist marker + INTERACTIVE-RUNTIME-DEFERRED + signature. Cross-check plan-design-review.md fixture has 10 dimensions.
    - Test 5 (SKILL-05 test_dx_lead_devex_review): dx-lead.md contains novice + pro + power-user + TTHW + friction. Cross-check fixtures.
    - Test 6 (SKILL-06 test_reviewer_review_and_investigate): reviewer.md contains iron-law + halt + 3-hypothesis cap + INTERACTIVE-RUNTIME-DEFERRED + SHA-PIN-DEFERRED + signature. Cross-check review.md fixture.
    - Test 7 (SKILL-07 test_qa_qa_only): qa.md contains qa-only + regression + bug-fix + qa_mode envelope + signature. Cross-check qa-only.md fixture.
    - Test 8 (SKILL-08 test_security_cso_full_rubric): security.md contains OWASP + STRIDE + N exclusions (matching cso.md fixture) + 8+ confidence gate + signature.
    - Test 9 (D-14 test_role_prompt_size_budget): all prompt files <= 4096 bytes; average <= 3072 bytes. Already exists from Wave 0 — preserve and ensure it passes (with all 11 prompts present this test passes; with only 8 from this plan, the assertion `len(sizes) == 11` triggers an xfail-style skip until 03-06 lands).
    - Test 10 (NEW: cross-file presence): all 11 prompt files exist. If 8 present (post-03-05) but engineer/shipper/sre missing (pre-03-06), this test xfails with `reason="03-06 ships engineer/shipper/sre stubs"`. After 03-06 lands, the xfail is removed.
  </behavior>
  <action>
**File: `tests/test_gstack_role_prompts.py`** — REPLACE the Wave 0 scaffold body with the following. Preserve module-level constants (PROMPTS_DIR, FIXTURES_DIR) from the scaffold.

```python
"""Per-role prompt golden grep tests (Phase 3 plan 03-05).

Replaces the Wave 0 scaffold (skip stubs from 03-01-PLAN). Asserts:
- Each of the 8 pure-rubric prompts contains its canonical greppable strings
- Each prompt's signature line is present verbatim
- Cross-check: canonical strings present in BOTH the upstream fixture AND the
  ported prompt (drift detection — if upstream changes and we re-fetch, the
  test will catch the drift)
- D-14 budget gate: every prompt <= 4096 bytes; average <= 3072 bytes
- Cross-file: all 11 prompt files present (xfails when 03-06's 3 stubs are missing)
"""
from __future__ import annotations

from pathlib import Path
import pytest

PROMPTS_DIR = Path(__file__).parent.parent / "clawteam" / "templates" / "gstack" / "prompts"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "gstack_skills"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# SKILL-01: pm
# ---------------------------------------------------------------------------


def test_pm_office_hours_rubric():
    prompt = _read(PROMPTS_DIR / "pm.md")
    fixture = _read(FIXTURES_DIR / "office-hours.md")

    # Signature
    assert "SIGNATURE: gstack-role:pm rubric:office-hours envelope-version:1" in prompt

    # Pitfall 7 partition
    assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt

    # Envelope reference (PMEnvelope.pm_question_index)
    assert "pm_question_index" in prompt

    # Fixture has at least the canonical "Why now" probe (from 03-01 SUMMARY)
    # If 03-01 captured drift, this assertion is updated by the executor.
    assert "Why now" in fixture, "Wave 0 office-hours fixture is missing 'Why now' canonical probe"

    # Question count: at least 6 numbered question-shaped lines in BOTH
    pm_questions = [line for line in prompt.splitlines() if line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6."))]
    assert len(pm_questions) >= 6, f"pm.md has fewer than 6 numbered forcing questions: {len(pm_questions)}"


# ---------------------------------------------------------------------------
# SKILL-02: ceo
# ---------------------------------------------------------------------------


def test_ceo_plan_review_modes():
    prompt = _read(PROMPTS_DIR / "ceo.md")
    fixture = _read(FIXTURES_DIR / "plan-ceo-review.md")

    assert "SIGNATURE: gstack-role:ceo rubric:plan-ceo-review envelope-version:1" in prompt
    for mode in ("Expansion", "Selective", "Hold", "Reduction"):
        assert mode in prompt, f"ceo.md missing mode '{mode}'"
        assert mode in fixture or mode.lower() in fixture.lower(), \
            f"plan-ceo-review.md fixture missing mode '{mode}'"

    assert "ceo_mode" in prompt  # envelope reference
    assert "advance_phase" in prompt  # TEAM-04 leader-only reminder


# ---------------------------------------------------------------------------
# SKILL-03: eng-mgr
# ---------------------------------------------------------------------------


def test_eng_mgr_plan_review_and_retro():
    prompt = _read(PROMPTS_DIR / "eng-mgr.md")

    assert "SIGNATURE: gstack-role:eng-mgr rubric:plan-eng-review+retro envelope-version:1" in prompt
    for piece in ("architecture-lock", "data-flow", "test-plan", "retro"):
        assert piece in prompt, f"eng-mgr.md missing rubric piece '{piece}'"
    # Edge-case matrix may use "edge-case-matrix" or "edge-case matrix" — accept both
    assert "edge-case" in prompt.lower(), "eng-mgr.md missing edge-case rubric piece"
    assert "eng_mgr_deliverable" in prompt  # envelope reference
    # Cross-fixture presence
    assert (FIXTURES_DIR / "plan-eng-review.md").exists()
    assert (FIXTURES_DIR / "retro.md").exists()


# ---------------------------------------------------------------------------
# SKILL-04: designer
# ---------------------------------------------------------------------------


def test_designer_rubric():
    prompt = _read(PROMPTS_DIR / "designer.md")
    fixture = _read(FIXTURES_DIR / "plan-design-review.md")

    assert "SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1" in prompt
    assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt
    assert "designer_rubric_dimension" in prompt  # envelope reference

    # 10 numbered dimensions
    numbered_lines = [line for line in prompt.splitlines() if line.strip()[:3] in {f"{i}." for i in range(1, 11)} or line.strip()[:4] in {f"{i}." for i in range(10, 11)}]
    # Permissive count: any 10 numbered top-level items
    nums = [line for line in prompt.splitlines() if line.strip().split(".")[0].isdigit() and int(line.strip().split(".")[0]) <= 10]
    assert len(nums) >= 10, f"designer.md has fewer than 10 numbered dimensions: {len(nums)}"

    # AI-slop marker
    assert "AI-slop" in prompt or "ai-slop" in prompt.lower() or "AI slop" in prompt


# ---------------------------------------------------------------------------
# SKILL-05: dx-lead
# ---------------------------------------------------------------------------


def test_dx_lead_devex_review():
    prompt = _read(PROMPTS_DIR / "dx-lead.md")

    assert "SIGNATURE: gstack-role:dx-lead rubric:plan-devex-review+devex-review envelope-version:1" in prompt
    for persona in ("novice", "pro", "power-user"):
        assert persona in prompt, f"dx-lead.md missing persona '{persona}'"
    assert "TTHW" in prompt or "Time-to-Hello-World" in prompt or "Time-To-Hello-World" in prompt
    assert "friction" in prompt.lower()
    assert "dx_lead_friction_source" in prompt  # envelope reference


# ---------------------------------------------------------------------------
# SKILL-06: reviewer
# ---------------------------------------------------------------------------


def test_reviewer_review_and_investigate():
    prompt = _read(PROMPTS_DIR / "reviewer.md")

    assert "SIGNATURE: gstack-role:reviewer rubric:review+investigate envelope-version:1" in prompt
    assert "iron-law" in prompt.lower() or "iron law" in prompt.lower()
    assert "halt" in prompt.lower()
    assert "3" in prompt  # halt-after-3 reference
    assert "INTERACTIVE-RUNTIME-DEFERRED" in prompt
    assert "SHA-PIN-DEFERRED" in prompt
    assert "reviewer_hypothesis_index" in prompt  # envelope reference


# ---------------------------------------------------------------------------
# SKILL-07: qa
# ---------------------------------------------------------------------------


def test_qa_qa_only():
    prompt = _read(PROMPTS_DIR / "qa.md")

    assert "SIGNATURE: gstack-role:qa rubric:qa+qa-only envelope-version:1" in prompt
    assert "qa-only" in prompt
    assert "regression" in prompt.lower()
    assert "bug" in prompt.lower()  # bug-fix loop
    assert "qa_mode" in prompt  # envelope reference


# ---------------------------------------------------------------------------
# SKILL-08: security (the largest port — 17 exclusions verbatim)
# ---------------------------------------------------------------------------


def test_security_cso_full_rubric():
    prompt = _read(PROMPTS_DIR / "security.md")
    fixture = _read(FIXTURES_DIR / "cso.md")

    assert "SIGNATURE: gstack-role:security rubric:cso envelope-version:1" in prompt
    assert "OWASP" in prompt
    assert "STRIDE" in prompt
    assert "security_confidence" in prompt  # envelope reference

    # 8+ confidence gate (D-13 / SKILL-08)
    assert "8" in prompt and ("confidence" in prompt.lower() or "escalat" in prompt.lower())

    # OWASP Top 10: at least 10 numbered lines visible
    owasp_lines = [
        line for line in prompt.splitlines()
        if line.strip().split(".")[0].isdigit() and 1 <= int(line.strip().split(".")[0]) <= 10
    ]
    assert len(owasp_lines) >= 10, f"security.md has fewer than 10 OWASP entries: {len(owasp_lines)}"

    # 17 false-positive exclusions: count numbered lines AFTER OWASP section.
    # Permissive count: total numbered lines >= 27 (10 OWASP + 17 exclusions).
    # If 03-01 noted upstream drift to a different exclusion count N, executor
    # updates this assertion to >= (10 + N).
    all_numbered = [
        line for line in prompt.splitlines()
        if line.strip().split(".")[0].isdigit()
    ]
    assert len(all_numbered) >= 27, (
        f"security.md numbered-list count {len(all_numbered)} < 27 (10 OWASP + 17 exclusions). "
        "If upstream cso.md drifted to a different exclusion count, update assertion to (10 + actual N)."
    )

    # Cross-fixture: cso.md fixture also references the canonical phrases
    assert "OWASP" in fixture
    assert "false positive" in fixture.lower() or "false-positive" in fixture.lower()


# ---------------------------------------------------------------------------
# D-14 budget gate (preserved from Wave 0)
# ---------------------------------------------------------------------------


def test_role_prompt_size_budget():
    """D-14: every prompt <= 4 KB; average <= 3 KB.

    Until 03-06 ships the 3 stub prompts (engineer, shipper, sre), only 8 of 11
    prompts exist; assert the partial set is also under cap. The 11-prompt
    cross-file test (test_all_eleven_prompt_files_present) handles the count.
    """
    sizes = {p.name: p.stat().st_size for p in PROMPTS_DIR.glob("*.md")}
    assert len(sizes) >= 8, f"expected at least 8 prompt files (this plan), found {len(sizes)}"
    for name, size in sizes.items():
        assert size <= 4096, f"{name} = {size} bytes (cap 4096)"
    avg = sum(sizes.values()) / len(sizes)
    assert avg <= 3072, f"average = {avg:.0f} bytes (cap 3072)"


# ---------------------------------------------------------------------------
# Cross-file: 11 prompt files (xfails until 03-06 ships the 3 stubs)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="03-06 ships engineer/shipper/sre stub prompts — un-xfail when 03-06 lands",
    strict=False,
)
def test_all_eleven_prompt_files_present():
    expected = {
        "pm.md", "ceo.md", "eng-mgr.md", "designer.md", "dx-lead.md",
        "engineer.md", "reviewer.md", "qa.md", "security.md", "shipper.md", "sre.md",
    }
    present = {p.name for p in PROMPTS_DIR.glob("*.md")}
    assert present == expected, f"missing: {expected - present}; extra: {present - expected}"
```

**Critical details:**
- The grep assertions use lenient matching (`.lower()`, `or` between alternative spellings) so that small variations between upstream fixture wording and the planner's prompt skeleton don't fail spuriously. The CANONICAL strings (signature lines, INTERACTIVE-RUNTIME-DEFERRED, SHA-PIN-DEFERRED, OWASP, STRIDE, mode names) are exact-matched.
- The 8/11 partial-file count is intentional. `test_role_prompt_size_budget` accepts >=8 so it passes after 03-05; `test_all_eleven_prompt_files_present` is xfail until 03-06 un-xfails it.
- Numeric counts (10 OWASP, 17 exclusions, 6 forcing questions, 10 design dimensions) use permissive `>=` so upstream drift surfaces as a passing test with high count, not a flaky failure.
- All assertions are deterministic — no time, no network, no randomness.

Atomic-commit discipline: single commit `test(03-05): un-skip + extend test_gstack_role_prompts.py with 8 SKILL golden tests + D-14 gate + xfail cross-file count`.
  </action>
  <verify>
    <automated>pytest tests/test_gstack_role_prompts.py -x</automated>
  </verify>
  <acceptance_criteria>
    - `pytest tests/test_gstack_role_prompts.py -x` exits 0 (8 SKILL tests + D-14 + xfail cross-file = 10 tests)
    - `pytest tests/test_gstack_role_prompts.py -k 'not test_all_eleven_prompt_files_present' -x` exits 0 (the 9 non-xfail tests all green)
    - `pytest tests/ -x` exits 0 (suite stays green; no Phase 0 / Phase 2 regressions)
    - `wc -c clawteam/templates/gstack/prompts/*.md | sort -n | tail -1 | awk '{print $1}'` ≤ 4096 (max file size)
    - `wc -c clawteam/templates/gstack/prompts/*.md | tail -1 | awk '{print $1}'` divided by file count ≤ 3072 (average size). Equivalently the test passes.
    - All 8 signature lines grep-present (verified by Tasks 1-4 acceptance criteria above + this test's assertions)
  </acceptance_criteria>
  <done>tests/test_gstack_role_prompts.py un-skipped + extended; all 8 SKILL tests pass; D-14 budget gate passes; cross-file test xfails (will be un-xfailed by 03-06); suite stays green.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Upstream gstack skill markdown -> committed fixture (Wave 0) -> ported prompt (Wave 2) | Fixtures are repo-committed once during 03-01 (Strategy B per D-08) — not re-fetched. Prompts are written from those fixtures verbatim. The trust hop is "fixture -> prompt" via human-reviewable commit. |
| Prompt content -> agent runtime (Phase 4+) | Prompts are loaded by `clawteam.templates` loader and injected into agent context. Prompt content can influence agent behavior; if an attacker edited a prompt they could redirect the agent. Mitigated by code review on every prompt PR (file ownership in CODEOWNERS not yet wired but prompts live in version control). |
| Fixture file path lookup (`FIXTURES_DIR / "<skill>.md"`) | Fixed `Path(__file__).parent / "fixtures" / "gstack_skills"` base; `/` operator does not normalize `..`. The skill names are hardcoded in tests, not user-supplied. No path traversal surface. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-01 | Tampering | Prompt-injection through a forged fixture file (an attacker tampers with `tests/fixtures/gstack_skills/cso.md` to add malicious instructions, hoping the verbatim port carries them into security.md) | mitigate | Fixtures are committed to repo (Wave 0 03-01 single commit) and never re-fetched in CI — `git log --follow tests/fixtures/gstack_skills/<skill>.md` shows the entire pin history. The golden tests in this plan grep BOTH the fixture AND the prompt for canonical strings — drift between them (e.g., a fixture with extra instructions that didn't make it into the prompt) is detectable but not auto-blocked. Future SHA-pin-on-fixtures task is out of Phase 3 scope; tracked as a follow-up note. |
| T-05-02 | Tampering | Direct edit of a prompt file in `clawteam/templates/gstack/prompts/<role>.md` to inject behavior contrary to the upstream rubric | accept (process control) | Prompts live in version control and are reviewed via PR. Golden grep tests assert the SIGNATURE line + canonical rubric strings remain present, so an attacker who adds malicious lines but leaves the canonical content intact would NOT be caught structurally. This is the standard "trust the reviewer" assumption for repo content. The signature-version bump path (`envelope-version:2`) gives a future migration hook for content-hash pinning. |
| T-05-03 | Information Disclosure | Prompt files contain example secrets / API keys (cargo-cult from upstream) | mitigate | All 8 prompts are pure-rubric ports; no API keys appear in upstream gstack skill markdown. Pre-commit secret scanner (existing project tool) covers this if/when activated. Golden grep tests do NOT assert absence of secrets — that's a separate static check. |
| T-05-04 | Denial of Service | Prompt files exceed model context window after Phase 6 memory inclusions land | mitigate | D-14 budget gate (4 KB cap, 3 KB avg) ships in this plan. Phase 6 memory-inclusion design must respect this gate — already documented in RESEARCH.md §"Open Question #3" Buffer for Phase 6 memory inclusions: ~300 bytes line. If Phase 6 inclusions push any prompt over 4 KB, the budget test fails immediately. |
| T-05-05 | Spoofing | An attacker writes a SIGNATURE line claiming a different role (e.g., `SIGNATURE: gstack-role:ceo rubric:plan-ceo-review` line in a non-ceo prompt) | accept | The signature is informational metadata, not a security boundary. Per-persona envelope subclasses (03-04) and the conductor's `actor` parameter (Wave 0 03-01) are the actual TEAM-04 enforcement. A misleading signature in a prompt file would be caught by the per-prompt golden test (each test asserts the EXACT canonical signature for THAT role). |

</threat_model>

<verification>
- All 8 prompt files exist under `clawteam/templates/gstack/prompts/`: `ls clawteam/templates/gstack/prompts/*.md | wc -l` >= 8
- Each prompt has its canonical signature line: 8 grep assertions pass
- Pitfall 7 partition strings present where required (pm/designer/reviewer have INTERACTIVE-RUNTIME-DEFERRED; reviewer also has SHA-PIN-DEFERRED)
- Each prompt references its corresponding envelope subclass field (pm_question_index, ceo_mode, eng_mgr_deliverable, designer_rubric_dimension, dx_lead_friction_source, reviewer_hypothesis_index, qa_mode, security_confidence)
- Verbatim canonical content from upstream fixtures present (forcing questions, modes, dimensions, exclusions): cross-fixture grep tests pass
- D-14 budget gate: max ≤ 4096 bytes, avg ≤ 3072 bytes — `test_role_prompt_size_budget` passes
- Wave 0 scaffold un-skipped: `grep -c 'pytest.mark.skip' tests/test_gstack_role_prompts.py` outputs 0 (xfail for cross-file count is allowed; skip is not)
- Cross-file test xfails (until 03-06 lands engineer/shipper/sre): `pytest tests/test_gstack_role_prompts.py::test_all_eleven_prompt_files_present` returns xfail (or xpass after 03-06)
- Suite stays green: `pytest tests/ -x` exits 0
</verification>

<success_criteria>
- SKILL-01..SKILL-08 satisfied: 8 prompts contain verbatim rubric content from upstream fixtures + envelope refs + signature lines
- D-14 budget gate enforced (max 4096B, avg 3072B) — programmatic test, not commit-time check
- Pitfall 7 partition (CONTEXT.md domain): rubric content lands here as static reference; INTERACTIVE-RUNTIME-DEFERRED + SHA-PIN-DEFERRED meta-instructions mark Phase-4 deferral surface for future-phase implementations to find
- Each prompt's envelope reference matches the per-persona subclass field defined in 03-04 (linkage between the 8 SKILL prompts and the 8 corresponding envelope subclasses)
- Existing 6 templates unaffected (no shared files modified); 03-01 fixtures and 03-02 template loader extension carry the prompt_file paths into the loader; 03-04 envelope subclasses provide field references
- Wave 0 scaffold (tests/test_gstack_role_prompts.py) Nyquist gate restored: 8 SKILL tests + D-14 budget test + cross-file xfail test all collected and pass (xfail counts as expected outcome)
- Suite stays green: pytest tests/ -x exits 0
</success_criteria>

<output>
After completion, create `.planning/phases/03-gstack-team-template-methodology-port/03-05-SUMMARY.md` covering:
- 8 prompt files written, sizes (bytes) per file, total bytes, average bytes — confirm D-14 budget passed
- Verbatim content port log: which canonical strings landed verbatim from each fixture (per-role)
- Drift notes: if 03-01 flagged `# CONTENT-DRIFT-NOTE:` on any fixture, document how the prompt content was adjusted to match actual upstream
- Test count delta in tests/test_gstack_role_prompts.py (Wave 0 9 skipped → ≥9 passing + 1 xfail)
- The 3 missing prompts (engineer, shipper, sre) and the un-xfail trigger for `test_all_eleven_prompt_files_present` once 03-06 ships
- Confirmation that prompt content references the corresponding envelope subclass field from 03-04 (8 cross-references)
</output>
</content>
</invoke>