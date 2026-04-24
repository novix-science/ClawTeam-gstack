---
phase: 08-workflow-contract
plan: 03
type: execute
wave: 2
depends_on: [08-01, 08-02]
files_modified:
  - tests/test_evidence_gate.py
  - tests/test_sprint_conductor.py
  - tests/test_cli_commands.py
  - .planning/phases/08-workflow-contract/08-VERIFICATION.md
requirements:
  - RELI-01
  - RELI-02
  - RELI-03
  - RELI-04
must_haves:
  truths:
    - "targeted Phase 8 tests pass"
    - "ruff check passes for changed Python files"
    - "verification artifact records the commands run and result"
---

<objective>
Lock the workflow contract with focused regression tests and a verification record for autonomous routing.
</objective>

<tasks>
- Run targeted pytest for the Phase 8 tests.
- Run `ruff check` on changed Python files and touched tests.
- Write `08-VERIFICATION.md` with `status: passed` only after targeted checks pass.
- If checks expose failures, fix the implementation rather than weakening the contract.
</tasks>
