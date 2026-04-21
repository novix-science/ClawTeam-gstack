---
phase: 03-gstack-team-template-methodology-port
plan: 06
subsystem: role-prompts
tags: [gstack, role-prompts, rubric, stub, d-01, d-02, d-03, d-14, team-04]

# Dependency graph
requires:
  - plan: 03-01
    provides: upstream gstack skill fixtures + Wave 0 test scaffold for role prompts
  - plan: 03-04
    provides: EngineerEnvelope.engineer_diff_summary + ShipperEnvelope.shipper_step + SREEnvelope.sre_signal pydantic subclasses (envelope field names referenced verbatim)
  - plan: 03-05
    provides: 8 pure-rubric prompts + tests/test_gstack_role_prompts.py skeleton with xfailed cross-file test + permissive D-14 gate (>= 8)
provides:
  - clawteam/templates/gstack/prompts/engineer.md — D-01 implementation-discipline rubric (no upstream skill owns this; canonical to gstack Build phase)
  - clawteam/templates/gstack/prompts/shipper.md — D-02 honest Phase-5-deferred stub with rubric:none SIGNATURE flag (Phase 5 swap target)
  - clawteam/templates/gstack/prompts/sre.md — D-03 honest Phase-5-deferred stub with rubric:none SIGNATURE flag (Phase 5 swap target)
  - tests/test_gstack_role_prompts.py extended — 3 new D-01/D-02/D-03 tests + D-14 gate tightened to 11 + cross-file test un-xfailed
affects:
  - 03-07 (GstackSprintPlugin.contribute_prompts resolves all 11 prompt files — no missing roles)
  - Phase 5 (shipper.md + sre.md flagged as swap targets via rubric:none; Phase 5 plan task swaps rubric content in + bumps SIGNATURE to rubric:ship / rubric:sre)

# Tech tracking
tech-stack:
  added: []  # markdown files + test additions only; zero runtime code changes
  patterns:
    - "D-02/D-03 stub-with-flag: rubric:none in SIGNATURE line is intentional and grep-asserted. Phase 5's plan task uses `grep -l 'rubric:none' clawteam/templates/gstack/prompts/` to discover swap targets. If Phase 5 forgets to bump, CI grep still detects the flag."
    - "D-01 canonical rubric port: engineer.md content is authored directly from CONTEXT.md D-01 (not from upstream skill markdown) — no upstream /engineer skill exists. 7 grep-verifiable items per D-01."
    - "D-14 gate now spans all 11 prompts: max ≤ 4096B per file, avg ≤ 3072B, count == 11 (tightened from permissive >= 8 in 03-05)."
    - "TEAM-04 envelope-layer enforcement extended: each new prompt references its envelope subclass + required field by name (engineer_diff_summary / shipper_step / sre_signal). Persona-spoofing payloads get caught at the prompt-instruction layer in addition to envelope + conductor layers from 03-04 + 03-01."

key-files:
  created:
    - clawteam/templates/gstack/prompts/engineer.md  # 2025 bytes
    - clawteam/templates/gstack/prompts/shipper.md   # 933 bytes
    - clawteam/templates/gstack/prompts/sre.md       # 882 bytes
  modified:
    - tests/test_gstack_role_prompts.py  # +3 D-01/D-02/D-03 tests, D-14 tightened, cross-file un-xfailed
    - .planning/phases/03-gstack-team-template-methodology-port/deferred-items.md  # appended 03-06 entry for pre-existing test_sprint_conductor flake

key-decisions:
  - "engineer.md ships at 2025 bytes (target was ~1200B; 825B over target but WELL under 4096 hard cap). The rubric content per D-01 is canonical — all 7 grep-verifiable items (read-first, atomic-commit, SHA-pin, engineer_diff_summary, no-fix-without-investigation deferral, /codex stub, /ship stub) + signature line fit with readable headings. Tightening below 2KB would force single-paragraph prose that loses sectional clarity. D-14 budget is easily satisfied."
  - "shipper.md + sre.md ship at 933B + 882B respectively — both slightly above the ~600B target but honest about persona contract + envelope reference + Phase-5 stub language. Both honor D-14. The rubric:none flag is grep-asserted."
  - "Cross-file test `test_all_eleven_prompt_files_present` un-xfailed by removing the `@pytest.mark.xfail(...)` decorator; function body unchanged from 03-05. D-14 gate tightened from `>= 8` to `== 11`."
  - "Pre-existing test_sprint_conductor::test_resume_after_process_restart flake confirmed not caused by 03-06 (verified via `git stash` baseline run); logged to deferred-items.md. SCOPE BOUNDARY: this is a Phase 2 subprocess flake; out of 03-06 scope."

# Verification
verification:
  gated: D-14 byte budget + D-01/D-02/D-03 grep content + cross-file presence
  result: PASS
  evidence: |
    D-14 byte budget (11 files):
      pm.md        2091 bytes
      ceo.md       1966 bytes
      eng-mgr.md   2139 bytes
      designer.md  2531 bytes
      dx-lead.md   2076 bytes
      engineer.md  2025 bytes  (NEW)
      reviewer.md  2227 bytes
      qa.md        1710 bytes
      security.md  2905 bytes
      shipper.md    933 bytes  (NEW)
      sre.md        882 bytes  (NEW)
      ----
      Total: 21,485 bytes
      Count: 11 (== assert gate)
      Average: 1,953 bytes (<= 3072 soft cap, PASS)
      Max: 2,905 bytes on security.md (<= 4096 hard cap, PASS)

    D-01 content checklist (engineer.md):
      [OK] read-first-before-write instruction
      [OK] Atomic-commit discipline (one logical change per commit + plan task ID ref)
      [OK] SHA-pin awareness at Build-phase start (HEAD SHA in envelope context)
      [OK] engineer_diff_summary envelope assertion (min_length=20 stub-defeating)
      [OK] no-fix-without-investigation deferral (routes to reviewer /investigate iron-law)
      [OK] Phase-5 tool-availability stub: /codex + /ship
      [OK] SIGNATURE: gstack-role:engineer rubric:implementation-discipline envelope-version:1

    D-02 content checklist (shipper.md):
      [OK] Persona contract (one paragraph identity)
      [OK] shipper_step envelope assertion + 6 Literal values (prep/pushing/pr-open/merged/deployed/verified)
      [OK] Phase-5 stub: /ship + /land-and-deploy + ship-notes.md + <pending> placeholder
      [OK] SIGNATURE: gstack-role:shipper rubric:none envelope-version:1 (swap flag)

    D-03 content checklist (sre.md):
      [OK] Persona contract
      [OK] sre_signal envelope assertion + 4 Literal values (nominal/degraded/regression/outage)
      [OK] Phase-5 stub: /canary + /benchmark + /setup-deploy + canary-report.md / benchmark-report.md
      [OK] SIGNATURE: gstack-role:sre rubric:none envelope-version:1 (swap flag)

  signatures: |
    All 11 files end with grep-verifiable SIGNATURE: gstack-role:<role> rubric:<...> envelope-version:1 line.
    grep -l '^SIGNATURE: gstack-role' clawteam/templates/gstack/prompts/*.md | wc -l → 11
    grep -l 'rubric:none' clawteam/templates/gstack/prompts/*.md → shipper.md + sre.md (exactly 2, as intended)

  tests: |
    pytest tests/test_gstack_role_prompts.py -q → 13 passed in 0.06s
    Tests: 8 SKILL tests from 03-05 (pm/ceo/eng-mgr/designer/dx-lead/reviewer/qa/security) +
           3 new D-01/D-02/D-03 tests (engineer/shipper/sre) +
           test_role_prompt_size_budget (D-14 gate, tightened to == 11) +
           test_all_eleven_prompt_files_present (un-xfailed, pure pass)
    grep -c '@pytest.mark.xfail' tests/test_gstack_role_prompts.py → 0 (no remaining xfails)

commits:
  - "a444304 feat(03-06): port D-01 implementation-discipline rubric to engineer.md"
  - "b934364 feat(03-06): port D-02 shipper + D-03 sre minimal stubs (Phase-5-deferred)"
  - "0a9bf7c test(03-06): add engineer + shipper + sre rubric tests; tighten D-14 to all 11; un-xfail cross-file count"

# Deviations
deviations:
  - issue: "--no-verify flag blocked by repo pre-commit hook (block-no-verify@1.1.2)"
    auto-fixed: true
    fix: "Spawning orchestrator directive said to use --no-verify to avoid Wave 3 contention. Repo policy forbids bypassing hooks. Committed normally; no contention observed (other Wave 3 agent's scope was clawteam/plugins/, zero file overlap with 03-06's scope). Commits landed cleanly between the other Wave 3 agent's commits."
    impact: "none — both Wave 3 agents shipped in parallel without conflict"
  - issue: "Pre-existing test_sprint_conductor::test_resume_after_process_restart failure when running full suite"
    auto-fixed: false
    fix: "Confirmed pre-existing via git stash baseline run — fails identically with zero local changes. Out of 03-06 scope per SCOPE BOUNDARY rule. Already logged in deferred-items.md under 03-02 and 03-05 executions; appended 03-06 entry for transparency."
    impact: "none — 03-06 scope-only tests (13/13) pass. Flake owned by Phase 2 test-infra; not a 03-06 regression."

# Metrics
metrics:
  tasks: 3
  files_created: 3
  files_modified: 2
  commits: 3
  duration: "~15min"
  completed: "2026-04-21"

---

# Phase 03 Plan 06: role-prompts-stubs Summary

Completed the 11-prompt role prompt set by authoring engineer.md (D-01 substantive
implementation-discipline rubric, 2025B), shipper.md (D-02 honest Phase-5-deferred
stub, 933B), and sre.md (D-03 honest Phase-5-deferred stub, 882B). Extended
tests/test_gstack_role_prompts.py with 3 new D-01/D-02/D-03 grep tests, tightened
the D-14 budget gate to assert `len(sizes) == 11`, and un-xfailed
`test_all_eleven_prompt_files_present`.

## D-01 / D-02 / D-03 Content Landing

| Decision | File | Size | Rubric flag | Key grep items landed |
|----------|------|------|-------------|----------------------|
| D-01 | engineer.md | 2025B | rubric:implementation-discipline | read-first, atomic-commit, SHA+HEAD, engineer_diff_summary, no-fix-without-investigation + iron-law, /codex, /ship |
| D-02 | shipper.md  | 933B  | rubric:none (swap flag) | shipper_step, 6 Literals, /ship, /land-and-deploy, ship-notes.md, `<pending>` |
| D-03 | sre.md      | 882B  | rubric:none (swap flag) | sre_signal, 4 Literals, /canary, /benchmark, /setup-deploy, canary-report.md, benchmark-report.md |

## D-14 Budget Recomputation (11 files)

- **Max:** 2,905 bytes (security.md) — under 4,096B hard cap, PASS
- **Avg:** 1,953 bytes (21,485 / 11) — under 3,072B soft cap, PASS
- **Count:** 11 — exact match to `== 11` tightened assertion

## Test Delta

tests/test_gstack_role_prompts.py grew by 3 new test functions
(test_engineer_implementation_discipline_rubric, test_shipper_minimal_stub,
test_sre_minimal_stub) plus 2 in-place edits (D-14 gate tightened;
`@pytest.mark.xfail` removed from test_all_eleven_prompt_files_present).
Active tests: 13 (was 9 passing + 1 xfail in 03-05). Zero xfails remaining.
pytest tests/test_gstack_role_prompts.py → 13 passed in 0.06s.

## 03-07 Plugin Resolution Readiness

All 11 (role, prompt_file) pairs resolve to a present file — no missing entries.
03-07's GstackSprintPlugin.contribute_prompts will iterate gstack.toml's
`[[template.agents]]` rows and find a prompt_file under
`clawteam/templates/gstack/prompts/` for each of: pm, ceo, eng-mgr, designer,
dx-lead, engineer, reviewer, qa, security, shipper, sre.

## Phase 5 Swap Roadmap

Phase 5's plan task uses `grep -l 'rubric:none' clawteam/templates/gstack/prompts/`
to identify swap targets. Today this returns exactly shipper.md + sre.md. Phase 5
swaps their rubric content with the full /ship+/land-and-deploy pipeline
(shipper) and /canary+/benchmark+/setup-deploy pipeline (sre), then bumps the
SIGNATURE line to `rubric:ship` and `rubric:sre` respectively. The
`rubric:none` grep is the trust handoff — if Phase 5 forgets the bump, CI still
catches the stub flag.

**Requirements closed:** TEAM-04 (envelope-layer enforcement extended to
engineer/shipper/sre — each prompt references its envelope subclass + required
field by name, adding a prompt-instruction layer of persona-spoofing defense on
top of 03-04's envelope layer + 03-01's conductor actor layer).

## Self-Check: PASSED

- [x] engineer.md exists — FOUND (2025B)
- [x] shipper.md exists — FOUND (933B)
- [x] sre.md exists — FOUND (882B)
- [x] tests/test_gstack_role_prompts.py contains 3 new D-01/D-02/D-03 tests — FOUND (lines 322/371/405)
- [x] test_all_eleven_prompt_files_present un-xfailed — FOUND (no @pytest.mark.xfail in file)
- [x] D-14 gate tightened to `== 11` — FOUND (line 440)
- [x] Commit a444304 (engineer.md) — FOUND
- [x] Commit b934364 (shipper + sre stubs) — FOUND
- [x] Commit 0a9bf7c (test updates + deferred-items) — FOUND
- [x] pytest tests/test_gstack_role_prompts.py: 13 passed, 0 failed, 0 xfailed
- [x] All 11 prompts present: `ls clawteam/templates/gstack/prompts/*.md | wc -l` → 11
- [x] `grep -l 'rubric:none' clawteam/templates/gstack/prompts/*.md` → shipper.md + sre.md (exactly 2)
