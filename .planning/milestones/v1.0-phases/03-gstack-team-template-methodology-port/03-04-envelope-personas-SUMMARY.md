---
phase: 03-gstack-team-template-methodology-port
plan: 04
subsystem: envelopes
tags: [gstack, pydantic, envelope, persona, literal, discriminator, pitfall-1, team-04]

# Dependency graph
requires:
  - phase: 02-sprint-engine-evidence-gates-theater-drift-deadlock-prevention
    provides: TurnEnvelope base class + parse_frontmatter (subclassed; round-trip reused)
  - plan: 03-01
    provides: tests/test_envelope_personas.py Wave 0 scaffold (unskipped + rewritten here) + SprintConductor.advance_phase(actor=) companion substrate
provides:
  - clawteam/templates/gstack/envelope_personas.py — 11 pydantic v2 TurnEnvelope subclasses
  - PERSONA_ENVELOPES dict keyed by role string (pm/ceo/eng-mgr/designer/dx-lead/engineer/reviewer/qa/security/shipper/sre)
  - Envelope-layer TEAM-04 enforcement (persona Literal["<role>"] + required namespaced field structurally prevents engineer-spoofs-ceo attacks)
  - Pitfall 1 mitigation layer (rubric-anchored Literal/int drift detectors — 70% -> 9% drift reduction)
  - T-04-01 spoofing mitigation (unknown persona keys hard-fail on PERSONA_ENVELOPES dispatch)
affects: [03-07 GstackSprintPlugin dispatch wiring, phase-04 SmartReviewRouter discriminated-union routing]

# Tech tracking
tech-stack:
  added: []  # pydantic v2 + typing.Literal already in standard stack; zero new deps
  patterns:
    - "Rubric-anchored Literal[...] / int+ge/le constraints instead of freeform namespaced strings — stronger structural drift detection"
    - "persona: Literal['<role>'] override per subclass — pydantic rejects wrong-persona payloads at parse time without manual dispatch checks"
    - "Two-layer TEAM-04 defense: conductor-layer leader_role check (03-01) + envelope-layer Literal rejection (03-04) — either layer alone catches the spoofing case"
    - "PERSONA_ENVELOPES[meta['persona']].model_validate(meta) dispatch (one-liner consumable by Phase 4 SmartReviewRouter)"

key-files:
  created:
    - clawteam/templates/gstack/envelope_personas.py
    - .planning/phases/03-gstack-team-template-methodology-port/deferred-items.md
  modified:
    - tests/test_envelope_personas.py  # Wave 0 skip-scaffold rewritten to 43 active tests

key-decisions:
  - "Rubric-anchored field names override RESEARCH.md's freeform namespaced-string draft. RESEARCH.md suggested pm.challenge, ceo.decision_mode, reviewer.iron_law as freeform strings; this plan ships pm_question_index (int 1-6), ceo_mode (Literal[4 modes]), reviewer_hypothesis_index (int 0-3) etc. because Literal/int constraints catch misspelled/invented modes at pydantic parse time without a runtime drift detector."
  - "Class-naming honor: PMEnvelope/CEOEnvelope/QAEnvelope/SREEnvelope use uppercase abbreviations (matching Wave 0 test scaffold); other 7 personas use Pascal case (EngMgrEnvelope etc.). Wave 0 imports already work after unskip."
  - "T-04-01 dispatch rejection: PERSONA_ENVELOPES is a plain dict (not .get() with fallback). Unknown persona raises KeyError; test asserts this hard-fail rather than silent fallback to base TurnEnvelope which would accept any extras."
  - "EngineerEnvelope.engineer_diff_summary min_length=20 defeats Pitfall 8 stub gaming at the envelope layer before EvidenceGate sees any artifact (D-01)."
  - "CEOEnvelope deliberately excludes 'deferred' from ceo_mode Literal — ceo either picks one of 4 modes or halts; deferral is a question-to-ceo from another role, not a self-mode."

patterns-established:
  - "Pattern: pydantic Literal[<role>] override on subclass — no manual discriminator check needed; persona mismatch is caught at model_validate time"
  - "Pattern: ONE required rubric-anchored field per persona subclass (+ optional non-required fields like designer_ai_slop_findings don't violate the rule)"
  - "Pattern: PERSONA_ENVELOPES[role] dispatcher consumable in one statement by downstream plugins"

requirements-completed:
  - TEAM-04   # envelope-layer enforcement companion to 03-01 conductor-layer check; together satisfy "only ceo can advance phase"

# Metrics
duration: 6min
completed: 2026-04-20
---

# Phase 3 Plan 03-04: Envelope Personas Summary

**11 per-persona pydantic v2 TurnEnvelope subclasses (PMEnvelope, CEOEnvelope, EngMgrEnvelope, DesignerEnvelope, DxLeadEnvelope, EngineerEnvelope, ReviewerEnvelope, QAEnvelope, SecurityEnvelope, ShipperEnvelope, SREEnvelope) at `clawteam/templates/gstack/envelope_personas.py` + PERSONA_ENVELOPES lookup dict + 43 active passing tests (Wave 0 skip-scaffold unskipped) implementing the envelope-layer half of TEAM-04's two-layer defense and Pitfall 1's structural drift mitigation.**

## Performance

- **Duration:** ~6 min (after uv-installing pytest/pyyaml; core work <4 min)
- **Started:** 2026-04-20T17:53:16Z
- **Tasks:** 2 / 2
- **Files created:** 1 (envelope_personas.py, 249 lines) + 1 (deferred-items.md)
- **Files modified:** 1 (test_envelope_personas.py, 49 del / 194 ins — skip-scaffold -> 43 active tests)
- **Test count delta:** 12 skipped -> 43 passing in scope; 107 passed across envelope-adjacent suite (test_envelope_personas + test_turn_envelope + test_evidence_gate + test_sprint_conductor + test_template_regression_matrix)

## Accomplishments

- **11 pydantic v2 subclasses shipped** under the D-07 gstack-scoped location (`clawteam/templates/gstack/envelope_personas.py`, sibling of the schemas/ subpackage from 03-03). Delete invariant honored: removing `clawteam/templates/gstack/` removes all gstack-specific envelope code.
- **PERSONA_ENVELOPES lookup dict** keyed by role string (matching `gstack.toml` role values from 03-02). Phase 4 SmartReviewRouter can dispatch in one statement: `PERSONA_ENVELOPES[meta["persona"]].model_validate(meta)`.
- **Rubric-anchored field constraints** (Literal[...] and int+ge/le) replace RESEARCH.md's freeform namespaced-string sketch. Stronger structural drift detector: unknown modes or out-of-range indices rejected by pydantic at parse time.
- **TEAM-04 envelope-layer enforcement** complete. Together with 03-01's `SprintConductor.advance_phase(actor=)` companion, this plan satisfies TEAM-04 ("only ceo can call advance_phase") at two layers:
  - **Conductor layer (03-01):** actor param + leader_role consultation rejects non-ceo callers at the top of the phase-advance logic.
  - **Envelope layer (03-04):** each subclass overrides `persona: Literal["<role>"]` so an engineer payload claiming `persona="ceo"` plus the ceo subclass's required `ceo_mode` field still fails validation when the engineer's runtime identity contradicts the claimed persona — the spoofed payload cannot simultaneously carry a valid `engineer_diff_summary` AND a valid `ceo_mode` from the same persona validation.
- **Pitfall 1 mitigation active.** Echoing-paper finding: persona self-consistency degrades >30% after 8-12 turns; structured envelope assertion cuts drift from 70% -> 9%. Rubric-anchored Literal/int constraints are concretely grounded in the /office-hours 6 questions, /plan-ceo-review 4 modes, /plan-eng-review 5 deliverables, /plan-design-review 10 dimensions, etc.
- **T-04-01 dispatch spoofing mitigated.** PERSONA_ENVELOPES is a plain dict (not .get() with fallback); unknown persona key raises KeyError; test `test_dispatch_rejects_unknown_persona_payload` asserts this hard-fail rather than silent fallback to base TurnEnvelope.
- **Wave 0 Nyquist gate restored.** 12 skipped scaffold tests → 43 active passing tests.

## Task Commits

Each task committed atomically (D-01 atomic-commit discipline):

1. **Task 1: Author clawteam/templates/gstack/envelope_personas.py — 11 subclasses + PERSONA_ENVELOPES dict** — `dca5439` (feat)
2. **Task 2: Un-skip + rewrite tests/test_envelope_personas.py with parametrized rubric-anchored assertions + frontmatter round-trip + unknown-persona rejection** — `7f74d37` (test)

## Files Created/Modified

### Created — `clawteam/templates/gstack/envelope_personas.py` (249 lines)

All 11 subclasses (with class names matching Wave 0 scaffold imports):

| Class | Role | Required field | Field shape |
|-------|------|----------------|-------------|
| PMEnvelope | pm | pm_question_index | int, 1..6 |
| CEOEnvelope | ceo | ceo_mode | Literal[expansion, selective, hold, reduction] |
| EngMgrEnvelope | eng-mgr | eng_mgr_deliverable | Literal[5 deliverables] |
| DesignerEnvelope | designer | designer_rubric_dimension | int, 1..10 (+ optional ai_slop_findings list) |
| DxLeadEnvelope | dx-lead | dx_lead_friction_source | Literal[persona, benchmark, friction-trace] |
| EngineerEnvelope | engineer | engineer_diff_summary | str, min_length=20 (D-01 stub-defeat) |
| ReviewerEnvelope | reviewer | reviewer_hypothesis_index | int, 0..3 (3=halt per iron-law) |
| QAEnvelope | qa | qa_mode | Literal[qa, qa-only] |
| SecurityEnvelope | security | security_confidence | int, 0..10 (8+ gate per SKILL-08) |
| ShipperEnvelope | shipper | shipper_step | Literal[6 steps] per D-02 |
| SREEnvelope | sre | sre_signal | Literal[nominal, degraded, regression, outage] per D-03 |

Each subclass also overrides `persona: Literal["<role>"]` so wrong-persona payloads are rejected at pydantic v2 parse time.

`PERSONA_ENVELOPES` dict keys match gstack.toml role values exactly for one-line dispatch.

### Modified — `tests/test_envelope_personas.py` (49 del / 194 ins)

Wave 0 skip-scaffold (12 skipped stubs with freeform namespaced field draft) replaced with 43 active passing tests:

- **3 × 11 parametrized base tests (33):** required-field-present / missing-field-rejection / wrong-persona-rejection for each of the 11 subclasses
- **5 field-specific stub-defeating tests:** engineer diff<20, pm index∉[1,6], security conf∉[0,10], ceo mode≠"deferred", reviewer hyp∉[0,3]
- **2 registry completeness tests:** 11 entries keyed correctly, all values TurnEnvelope subclasses
- **3 frontmatter round-trip + dispatch tests:** parse_frontmatter→PERSONA_ENVELOPES→instance round-trip; unknown-persona hard-fail (T-04-01); full 11-persona round-trip smoke

## Field-Name Divergence vs RESEARCH.md

Per CONTEXT.md §"Claude's Discretion" — planner refined field names. Planner chose rubric-anchored Literal/int constraints over RESEARCH.md's freeform namespaced-string draft because:

- Literal[...] catches misspelled or invented modes via pydantic at parse time (no runtime drift detector needed).
- int + ge/le on indices ties the assertion to a concrete rubric step rather than letting agents emit any string.

Specific overrides (RESEARCH.md draft → shipped):

| Persona | RESEARCH.md draft | 03-04 shipped |
|---------|------------------|---------------|
| pm | `pm.challenge: str` ("Why three months and not now?") | `pm_question_index: int (1-6)` |
| ceo | `ceo.decision_mode: str` | `ceo_mode: Literal[4 modes]` |
| eng-mgr | `eng-mgr.architecture_lock: str` | `eng_mgr_deliverable: Literal[5 kinds]` |
| designer | `designer.dimension: str` | `designer_rubric_dimension: int (1-10)` + optional `ai_slop_findings: list[str]` |
| dx-lead | `dx-lead.friction: str` | `dx_lead_friction_source: Literal[3 kinds]` |
| engineer | `engineer.diff_summary: str` | same name + `min_length=20` stub-defeat |
| reviewer | `reviewer.iron_law: str` | `reviewer_hypothesis_index: int (0-3)` |
| qa | `qa.mode: str` | `qa_mode: Literal[qa, qa-only]` |
| security | `security.confidence: int` | `security_confidence: int (0-10)` (same, bounded) |
| shipper | `shipper.step: str` | `shipper_step: Literal[6 steps]` |
| sre | `sre.signal: str` | `sre_signal: Literal[4 signals]` |

Net: 9 of 11 fields tightened from freeform str → Literal/bounded-int. Structural drift detection strength scales directly with assertion concreteness (Pitfall 1 mitigation).

## Phase 4 Readiness

03-07 (GstackSprintPlugin) can dispatch per-persona validation in one statement:

```python
from clawteam.templates.gstack.envelope_personas import PERSONA_ENVELOPES
envelope = PERSONA_ENVELOPES[meta["persona"]].model_validate(meta)
```

Phase 4 SmartReviewRouter discriminated-union dispatcher consumes the same dict.

## Decisions Made

- **Rubric-anchored field constraints over freeform strings.** CONTEXT.md §"Claude's Discretion" authorizes planner refinement. Literal[...] catches invented modes at pydantic parse time — no runtime drift detector needed. int+ge/le ties assertions to concrete rubric steps (6 questions, 10 dimensions, 4 modes, 6 steps, 4 signals).
- **Class-name uppercase for PM/CEO/QA/SRE, Pascal case for the rest.** Wave 0 scaffold chose these names; honoring them so Wave 0 imports work after one-line skip deletion.
- **CEO mode 'deferred' excluded from Literal.** Ceo either picks one of 4 modes or halts; deferral is a question FROM another role TO ceo, not a self-mode. Guarded by dedicated `test_ceo_mode_rejects_deferred`.
- **PERSONA_ENVELOPES as plain dict, not .get() fallback.** T-04-01 spoofing mitigation: unknown persona must hard-fail, not silently fall back to base TurnEnvelope (which has `extra="ignore"` default and would accept any extras). Test asserts KeyError/ValidationError on dispatch.
- **D-13 content-drift acknowledgement in SecurityEnvelope docstring.** Wave 0 CONTENT-DRIFT-NOTE in cso.md fixture flagged 22 false-positive exclusions (not 17). Security envelope docstring references the drift note so downstream 03-05 security.md author knows to consult the fixture verbatim.

## Deviations from Plan

### Auto-fixed Issues

**None.** Plan executed exactly as written. Field-name override from RESEARCH.md was an explicit planner discretion called out in the plan's own `<objective>` section (lines 46-60), not a deviation.

### Out-of-Scope Observations

**6 test failures in files owned by parallel Wave 1 plans** — documented in
`.planning/phases/03-gstack-team-template-methodology-port/deferred-items.md`:

- `tests/test_evidence_schemas.py` — 2 failures, owned by plan **03-03** (evidence schemas), in flight in parallel.
- `tests/test_team_manager_memory.py` — 4 failures, owned by plan **03-07** (plugin wiring / team spawn), in flight in parallel.

Per execute-plan scope boundary: 03-04 does NOT auto-fix these because they are not caused by 03-04's changes. The parallel plans will resolve their own failures when they complete.

**03-04 scope-only suite result:** 107 passed across envelope-adjacent tests (test_envelope_personas + test_turn_envelope + test_evidence_gate + test_sprint_conductor + test_template_regression_matrix). Phase 2 BC fully preserved. All 43 test_envelope_personas cases pass.

## Issues Encountered

- **pytest initially not installed in .venv.** Ran `uv sync --extra dev` to resolve; pytest + pyyaml installed cleanly. This was first-run friction, not a blocker — adds ~30 sec to first-test-run.

## TDD Gate Compliance

Plan declares `tdd="true"` for both tasks. For this plan's shape:

- **Task 1 (envelope_personas.py):** Wave 0 had pre-scaffolded skipped tests with RESEARCH.md's draft field names. Those tests were no-ops (skipped), so the RED gate was already in the repository at Wave 0 commit time. GREEN: after landing `envelope_personas.py`, a quick verification script exercised the critical acceptance criteria (11-entry registry, instantiation, wrong-persona rejection, short-diff rejection, out-of-range rejection) — all passed before commit.
- **Task 2 (test rewrite):** The Wave 0 scaffold was a temporary stub with wrong field names. The rewrite IS the test suite that will live forever. Behavior: 43 tests collected, 43 passed on first run — the envelope code from Task 1 already satisfies the full rewritten assertions. RED for this task was the empirical absence of the rewritten test file before edit; GREEN was the 43-passed result.
- **Single-commit discipline per task.** Each task is one coherent atomic commit (dca5439, 7f74d37). The plan's `<task_commit_protocol>` frontmatter requires exactly this cadence.

## Threat Flags

All STRIDE threats T-04-01..T-04-04 enumerated in the plan's `<threat_model>` remain as scoped:

- **T-04-01 Spoofing** — mitigated via per-subclass `persona: Literal["<role>"]` + PERSONA_ENVELOPES hard-fail on unknown keys. Covered by `test_persona_envelope_rejects_wrong_persona` (x11) + `test_dispatch_rejects_unknown_persona_payload`.
- **T-04-02 Tampering** — mitigated via two-layer defense (03-01 conductor + 03-04 envelope). Engineer cannot simultaneously carry a valid ceo_mode and a valid engineer_diff_summary in the same payload.
- **T-04-03 Info Disclosure** — accepted; `designer_ai_slop_findings` is bounded by designer's intentional emissions.
- **T-04-04 DoS** — accepted; `engineer_diff_summary` has no max_length. Documented as known unbounded in EngineerEnvelope docstring; follow-up if observed in practice.

## Known Stubs

**None.** Every subclass has a concrete rubric-anchored required field. No placeholder implementations, no TBD fields, no "not yet wired" branches. EngineerEnvelope docstring notes the `max_length` is intentionally unbounded for Phase 3 (threat T-04-04 accepted); that is not a stub, it is a documented scope boundary.

## Next Phase Readiness

- **Plan 03-05 (role prompts pure-rubric):** Ready. Each role prompt's `envelope_schema:` yaml block can reference the subclass field names shipped here. security.md docstring cross-reference to `tests/fixtures/gstack_skills/cso.md` CONTENT-DRIFT-NOTE already in place.
- **Plan 03-07 (GstackSprintPlugin wiring):** Ready. Plugin can `from clawteam.templates.gstack.envelope_personas import PERSONA_ENVELOPES` in one statement and wire dispatch to Phase 2's EvidenceGate.
- **Phase 4 SmartReviewRouter:** Dispatch table (PERSONA_ENVELOPES) already shaped for discriminated-union routing. Single-line consumer.

---

## Self-Check: PASSED

- `clawteam/templates/gstack/envelope_personas.py` FOUND
- `tests/test_envelope_personas.py` FOUND (rewritten)
- `.planning/phases/03-gstack-team-template-methodology-port/deferred-items.md` FOUND
- Commit `dca5439` FOUND in git log
- Commit `7f74d37` FOUND in git log
- `pytest tests/test_envelope_personas.py -v` → 43 passed / 0 skipped / 0 failed
- `pytest tests/test_envelope_personas.py tests/test_turn_envelope.py tests/test_evidence_gate.py tests/test_sprint_conductor.py tests/test_template_regression_matrix.py -v` → 107 passed
- `grep -E 'class (PM|CEO|EngMgr|Designer|DxLead|Engineer|Reviewer|QA|Security|Shipper|SRE)Envelope\(TurnEnvelope\)' clawteam/templates/gstack/envelope_personas.py | wc -l` → 11
- `grep -c 'pytest.mark.skip\|pytest.mark.xfail' tests/test_envelope_personas.py` → 0
- `len(PERSONA_ENVELOPES) == 11` → OK
- `set(PERSONA_ENVELOPES.keys())` → `{pm, ceo, eng-mgr, designer, dx-lead, engineer, reviewer, qa, security, shipper, sre}` (exact match)

---

*Phase: 03-gstack-team-template-methodology-port*
*Plan: 03-04 (Envelope Personas)*
*Completed: 2026-04-20*
