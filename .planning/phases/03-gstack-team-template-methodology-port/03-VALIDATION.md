---
phase: 3
slug: gstack-team-template-methodology-port
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `03-RESEARCH.md` §"Validation Architecture" (lines 903-958).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already in repo) |
| **Config file** | `pytest.ini` / `pyproject.toml` (existing) |
| **Quick run command** | `pytest tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py tests/test_envelope_personas.py -x` |
| **Full suite command** | `pytest tests/ -x` (must remain green — Phase 0 regression matrix dependency) |
| **Estimated runtime** | ~5 seconds quick / ~30 seconds wave / full suite per CI baseline |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py tests/test_envelope_personas.py -x` (~5s)
- **After every plan wave:** Run `pytest tests/test_gstack_template.py tests/test_gstack_plugin.py tests/test_gstack_role_prompts.py tests/test_envelope_personas.py tests/test_gstack_team_spawn.py tests/test_template_regression_matrix.py tests/test_evidence_schemas.py tests/test_sprint_conductor.py -x` (~30s)
- **Before `/gsd-verify-work`:** `pytest tests/ -x` must be green
- **Max feedback latency:** 30 seconds (wave-level); 5 seconds (per-commit)

---

## Per-Task Verification Map

> Source: `03-RESEARCH.md` §"Phase Requirements → Test Map". Plan task IDs (`{N}-{plan}-{task}`) populate during planning; this table assigns one-or-more REQ-IDs to its automated verification command. Plans MUST reference these commands in their `<automated>` blocks.

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| TEAM-01 | `gstack.toml` parses through existing template loader | unit | `pytest tests/test_gstack_template.py::test_parses_via_existing_loader -x` | ❌ W0 | ⬜ pending |
| TEAM-02 | All 11 distinct agents present in loaded template | unit | `pytest tests/test_gstack_template.py::test_eleven_agents_with_distinct_roles -x` | ❌ W0 | ⬜ pending |
| TEAM-03 | Each agent gets its own worktree desk via `WorkspaceManager` | integration | `pytest tests/test_gstack_team_spawn.py::test_eleven_worktrees_created -x` | ❌ W0 | ⬜ pending |
| TEAM-04 | Only ceo can call `SprintConductor.advance_phase` (other actors rejected) | unit | `pytest tests/test_gstack_plugin.py::test_only_ceo_advances_phase -x` | ❌ W0 | ⬜ pending |
| TEAM-05 | `--model-profile balanced` is default; `quality` and `budget` selectable | unit | `pytest tests/test_gstack_template.py::test_model_profile_defaults_to_balanced -x` | ❌ W0 | ⬜ pending |
| SKILL-01 | pm.md contains all 6 forcing questions + challenge-framing + INTERACTIVE-DEFERRED | golden | `pytest tests/test_gstack_role_prompts.py::test_pm_office_hours_rubric -x` | ❌ W0 | ⬜ pending |
| SKILL-02 | ceo.md contains 4 modes (Expansion/Selective/Hold/Reduction) + decision schema | golden | `pytest tests/test_gstack_role_prompts.py::test_ceo_plan_review_modes -x` | ❌ W0 | ⬜ pending |
| SKILL-03 | eng-mgr.md contains arch-lock + data-flow + edge-case matrix + test-plan + retro per-person | golden | `pytest tests/test_gstack_role_prompts.py::test_eng_mgr_plan_review_and_retro -x` | ❌ W0 | ⬜ pending |
| SKILL-04 | designer.md contains 0-10 rubric (10 dimensions) + AI-slop checklist + INTERACTIVE-DEFERRED for /design-consultation | golden | `pytest tests/test_gstack_role_prompts.py::test_designer_rubric -x` | ❌ W0 | ⬜ pending |
| SKILL-05 | dx-lead.md contains personas + TTHW + friction tracing | golden | `pytest tests/test_gstack_role_prompts.py::test_dx_lead_devex_review -x` | ❌ W0 | ⬜ pending |
| SKILL-06 | reviewer.md contains iron-law + halt-after-3 + SHA-PIN-DEFERRED + INTERACTIVE-DEFERRED for /investigate | golden | `pytest tests/test_gstack_role_prompts.py::test_reviewer_review_and_investigate -x` | ❌ W0 | ⬜ pending |
| SKILL-07 | qa.md contains bug-fix + regression-loop + qa-only mode suppression | golden | `pytest tests/test_gstack_role_prompts.py::test_qa_qa_only -x` | ❌ W0 | ⬜ pending |
| SKILL-08 | security.md contains OWASP Top 10 + STRIDE + 17 false-positive exclusions + 8/10+ confidence gate | golden | `pytest tests/test_gstack_role_prompts.py::test_security_cso_full_rubric -x` | ❌ W0 | ⬜ pending |
| SPRINT-06 | Reflect phase invokes `/learn` stub; placeholder file written under `_phase6_pending/<sprint_id>-retro.json` | integration | `pytest tests/test_gstack_plugin.py::test_reflect_phase_learn_stub_writes_placeholder -x` | ❌ W0 | ⬜ pending |
| UX-01 | `clawteam team spawn gstack --name <n>` end-to-end | integration | `pytest tests/test_sprint_cli.py::test_team_spawn_gstack -x` | ❌ W0 | ⬜ pending |
| UX-07 | `clawteam team show <n>` displays 11 members + sprint progress + cost rollup placeholders | integration | `pytest tests/test_cli_commands.py::test_team_show_gstack_dashboard -x` | ❌ W0 | ⬜ pending |
| (Cross-template isolation — success criterion #2) | Spawning `software-dev` does NOT register gstack phases | regression | `pytest tests/test_template_regression_matrix.py::test_software_dev_unaffected_by_gstack_plugin -x` | ✅ EXTEND | ⬜ pending |
| (Phase 0 regression matrix — success criterion #7) | All 6 existing templates spawn unchanged | regression | `pytest tests/test_template_regression_matrix.py -x` | ✅ EXTEND | ⬜ pending |
| (Per-persona envelopes — D-07) | All 11 personas have working envelope subclass with required reassertion field | unit | `pytest tests/test_envelope_personas.py -x` | ❌ W0 | ⬜ pending |
| (D-14 prompt budget) | Every `clawteam/templates/gstack/prompts/*.md` ≤ 4 KB; average ≤ 3 KB | gate | `wc -c clawteam/templates/gstack/prompts/*.md` (max ≤ 4096; avg ≤ 3072) | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

New test files the planner MUST create as Wave 0 (before any implementation file is touched), so subsequent waves have automated verification per Nyquist:

- [ ] `tests/test_gstack_template.py` — covers TEAM-01, TEAM-02, TEAM-05
- [ ] `tests/test_gstack_plugin.py` — covers TEAM-04, SPRINT-06, plugin-load isolation
- [ ] `tests/test_gstack_role_prompts.py` — covers SKILL-01..SKILL-08 (golden grep tests against signature lines + rubric content presence + `INTERACTIVE-RUNTIME-DEFERRED:` / `SHA-PIN-DEFERRED:` greppable strings)
- [ ] `tests/test_envelope_personas.py` — covers per-persona envelope subclasses across all 11 personas
- [ ] `tests/test_gstack_team_spawn.py` — covers TEAM-03, UX-01 integration
- [ ] `tests/fixtures/gstack_skills/` directory populated by Wave-0 `golden-trace-prep` task — WebFetched upstream gstack skill markdown for grep cross-checking (Strategy B per D-08)
- [ ] `tests/fixtures/gstack_artifacts/` directory — golden valid + stub-grade fixtures for the six EvidenceSchema models (DesignDoc, PlanDoc, TestReport, ReviewReport, ShipNotes, Retro)

Existing files to EXTEND (no new file creation):

- [ ] `tests/test_template_regression_matrix.py` — assert spawning each of the 6 existing templates does NOT trigger `GstackSprintPlugin.on_register` (cross-template isolation success criterion #2)
- [ ] `tests/test_evidence_schemas.py` (Phase 2 file) — validate the six new gstack schemas
- [ ] `tests/test_cli_commands.py` (existing) — `team show gstack` dashboard verification

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Verbatim rubric content lands in role prompts (the *spirit* matches upstream gstack methodology, beyond grep) | SKILL-01..SKILL-08 | Grep can verify presence of canonical strings, but cannot confirm a port is faithful to upstream methodology nuance | After Phase 3 lands: `git diff` each `clawteam/templates/gstack/prompts/<role>.md` against the corresponding `tests/fixtures/gstack_skills/<skill>.md` and read for spirit. Document any intentional divergence in commit message. |

*All other phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references (8 new test files + fixtures + 3 EXTENDs)
- [ ] No watch-mode flags (commands use `-x` for fail-fast, not `--watch`)
- [ ] Feedback latency < 30s wave-level; < 5s per-commit
- [ ] `nyquist_compliant: true` set in frontmatter after planner completes Wave 0 mapping

**Approval:** pending
