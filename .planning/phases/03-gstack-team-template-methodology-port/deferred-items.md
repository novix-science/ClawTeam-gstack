# Phase 03 Deferred Items

Out-of-scope discoveries logged per execute-plan scope boundary rule. These are
NOT bugs caused by the logging plan — they are pre-existing WIP failures in
files owned by PARALLEL plans running in Wave 1.

## From 03-04 Execution (2026-04-20)

**Pre-existing failures observed when running full suite; all in files owned
by parallel Wave 1 plans, not by 03-04 (envelope_personas):**

- `tests/test_evidence_schemas.py::TestDesignDocSchema::test_valid_fixture_round_trips` — owned by **plan 03-03** (evidence-schemas). 03-03 WIP in progress in parallel.
- `tests/test_evidence_schemas.py::TestPlanDocSchema::test_valid_fixture_round_trips` — owned by **plan 03-03**.
- `tests/test_team_manager_memory.py::TestTeamSpawnCommand::test_spawn_gstack_creates_eleven_memory_dirs` — owned by **plan 03-07** (plugin-wiring / team spawn).
- `tests/test_team_manager_memory.py::TestTeamSpawnCommand::test_spawn_gstack_persists_template_and_leader_role` — owned by **plan 03-07**.
- `tests/test_team_manager_memory.py::TestTeamSpawnCommand::test_spawn_help_exposes_ux01_form` — owned by **plan 03-07**.
- `tests/test_team_manager_memory.py::TestTeamSpawnCommand::test_spawn_unknown_template_errors` — owned by **plan 03-07**.

**03-04 scope-only suite result:** 107 passed in scope (test_envelope_personas +
test_turn_envelope + test_evidence_gate + test_sprint_conductor +
test_template_regression_matrix). All Phase 2 BC preserved. All 43
test_envelope_personas cases pass.

**Action:** None required by 03-04. Parallel plans will fix their own tests
when they complete. Logged here per deferred-items protocol so the verifier
can see the context at phase-completion time.

## From 03-02 Execution (2026-04-21)

Plan 03-02 (template-roster-memory) is the owner of `tests/test_team_manager_memory.py`
(not 03-07 as stated above) — that file was authored by 03-02 Task 3 in
a separate agent session. All 12 tests in `tests/test_team_manager_memory.py`
PASS under 03-02's implementation (TeamManager.create_team roles kwarg +
`team spawn` Typer subcommand).

**Pre-existing failures observed by 03-02 when running full suite; NOT caused
by 03-02 changes (confirmed via `git stash` baseline run):**

- `tests/test_evidence_schemas.py::TestDesignDocSchema::test_valid_fixture_round_trips` — owned by **plan 03-03** (evidence-schemas).
- `tests/test_evidence_schemas.py::TestPlanDocSchema::test_valid_fixture_round_trips` — owned by **plan 03-03**.
- `tests/test_sprint_conductor.py::test_resume_after_process_restart` — pre-existing flake (subprocess-based); fails identically on `git stash` baseline, so not 03-02-caused. Likely a Phase 2 test-infra flake; out of 03-02 scope.

**03-02 scope-only suite result:** 97 passed (test_team_manager_memory +
test_manager + test_template_regression_matrix + test_gstack_template +
test_templates). All BC preserved across 6 existing templates.
