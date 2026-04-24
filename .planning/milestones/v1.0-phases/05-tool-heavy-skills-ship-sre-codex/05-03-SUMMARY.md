---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 03
subsystem: skill-codex
tags:
  - skill-codex
  - native-cli-adapter
  - adversarial-test
  - skill-registration
  - sub-package

# Dependency graph
requires:
  - phase: 05-tool-heavy-skills-ship-sre-codex
    provides: Plan 05-01 wave-0 substrate (SkillRegistration dataclass, SkillUnavailable hierarchy, HarnessPlugin.contribute_skills hook, PluginManager.get_plugin_skills aggregator, SkillDispatcher, invoke_native_cli wrapper).
  - phase: 05-tool-heavy-skills-ship-sre-codex
    provides: Plan 05-02 wave-1 substrate (CodexReview pydantic schema already registered in GstackSprintPlugin.contribute_evidence_schemas under key 'codex-review').
  - phase: 03-gstack-team-methodology-port
    provides: GstackSprintPlugin canonical plugin class + fileutil.atomic_write_text + skills sub-package shape (office_hours / design_consultation / investigate as reference).
provides:
  - /codex skill handler (3 modes — review / adversarial / consultation) at clawteam/templates/gstack/skills/codex/handler.py
  - GstackSprintPlugin.contribute_skills() first real entry — /codex with roles={engineer, reviewer} + install_hint 'npm install -g @openai/codex'
  - tool_available() probe for SkillDispatcher pre-flight tool-availability gate
  - codex-review.md artifact writer with mode-tagged YAML frontmatter + CodexReview-conformant fields
affects:
  - 05-04 through 05-09 (sibling Wave 2-4 plans append to GstackSprintPlugin.contribute_skills list additively)
  - 07-* (future: engineer self-invokes /codex during Build phase; reviewer self-invokes during Review phase)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Skill sub-package (D-01) — __init__.py re-exports handler + probe; handler.py is single-file implementation"
    - "Tool-availability probe (shutil.which) returns bool; raised SkillUnavailable wraps binary + install_hint for doctor-parity surfacing"
    - "invoke_native_cli over direct subprocess.run — shell=False + scrub_env are centralised (T-05-03-01/02 mitigations live at the Wave 0 wrapper, NOT per-handler)"
    - "Hand-rolled YAML frontmatter emitter (no pyyaml runtime dep) matching Phase 3/5 schema-emit convention"
    - "Cheap-fail mode validation BEFORE CLI invocation — invalid mode raises ValueError before shutil.which / subprocess.run runs"

key-files:
  created:
    - clawteam/templates/gstack/skills/codex/__init__.py
    - clawteam/templates/gstack/skills/codex/handler.py
    - tests/templates/gstack/skills/test_codex.py
    - tests/templates/__init__.py
    - tests/templates/gstack/__init__.py
    - tests/templates/gstack/skills/__init__.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py

# Key decisions
decisions:
  - "Skill sub-package shape (D-01): __init__.py re-exports codex_handler + invoke_codex + tool_available; handler.py contains all implementation including hand-rolled YAML emitter. No state.py (Pitfall 4 — codex is NOT a state machine)."
  - "Verdict heuristic gated on mode: only mode='review' inspects stdout first line for 'lgtm'/'pass'/'approved' → 'pass', 'fail'/'reject'/'block' → 'fail', else 'n/a'. Adversarial/consultation modes always emit verdict='n/a' because their output is critique/design-discussion rather than gate-determinative."
  - "Handler raises ValueError (not pydantic.ValidationError) for invalid mode to fail-fast BEFORE CLI invocation; pydantic validation on CodexReview still guards the emitted artifact."
  - "Summary truncated to first 500 chars of stdout — T-05-03-04 accept posture (downstream EvidenceGate does not execute stored markdown; summary is agent-display only)."
  - "invoke_codex signature retains mode kwarg unused-by-CLI-today — preserves forward compatibility for a future --mode flag without changing handler call sites."
  - "Default CODEX_TIMEOUT=600s (10 min) vs invoke_native_cli default 120s — codex can be slow on long-file reviews."

# Metrics
metrics:
  duration: ~25 minutes (including RED/GREEN cycles + cross-executor interaction handling)
  tasks_completed: 2
  files_created: 6
  files_modified: 1
  tests_added: 9
  tests_passed: 9
---

# Phase 5 Plan 03: /codex Skill Summary

Implements the /codex skill — cross-model independent second opinion via the OpenAI Codex CLI (SKILL-13) — as a two-file sub-package (`__init__.py` + `handler.py`) under `clawteam/templates/gstack/skills/codex/`, plus a `SkillRegistration` appended to `GstackSprintPlugin.contribute_skills()` with `roles={engineer, reviewer}` and `install_hint='npm install -g @openai/codex'`. The handler dispatches three modes (review / adversarial / consultation), writes a `codex-review.md` artifact tagged with the invoked mode in YAML frontmatter, and raises `SkillUnavailable` (carrying the install hint) when the codex binary is missing — never partial execution, never crash, never a stale artifact. D-15 adversarial-input safety is delegated to the Wave 0 `invoke_native_cli` wrapper (shell=False hard-coded, prompt flows through a dedicated kwarg as a literal positional arg).

## Objective Delivered

- `codex_handler(ctx, *, role, args={mode, target, prompt})` entry point invoked by `SkillDispatcher`.
- Three modes with distinct semantics: review (pass/fail verdict heuristic), adversarial (red-team critique, verdict='n/a'), consultation (open design Q, verdict='n/a').
- `tool_available()` probe (`shutil.which('codex') is not None`) used by `SkillDispatcher` to pre-flight gate the handler.
- `invoke_codex(prompt, *, mode, cwd, timeout)` helper that goes through `invoke_native_cli` — no direct `subprocess.run` in handler code.
- `codex-review.md` written atomically via `atomic_write_text` under `ctx.sprint_dir`; frontmatter conforms to the `CodexReview` pydantic schema shipped in Plan 05-02.
- Plugin registration on `GstackSprintPlugin` marks /codex as the first concrete Phase 5 skill (Wave 2-4 plans extend the list additively).

## Key Files

**Created**:

- `clawteam/templates/gstack/skills/codex/__init__.py` — public-API re-exports (codex_handler, invoke_codex, tool_available).
- `clawteam/templates/gstack/skills/codex/handler.py` — handler + probe + invoke helper + frontmatter emitter + verdict heuristic.
- `tests/templates/gstack/skills/test_codex.py` — 9 tests (6 handler + 3 plugin-wiring).
- `tests/templates/*/__init__.py` (3 files) — package-init scaffolding for the new test sub-tree.

**Modified**:

- `clawteam/plugins/gstack_sprint_plugin.py` — imports codex_handler + tool_available; adds `contribute_skills()` returning a list with the /codex entry.

## Tasks Completed

### Task 1 — Handler + sub-package (6 tests)

RED:

- Created 6 failing tests covering happy path, missing-tool `SkillUnavailable`, adversarial shell-metachar prompt, mode validation fail-fast, adversarial-mode verdict='n/a', and `tool_available()` bool probe.

GREEN:

- Implemented `handler.py` (~220 LOC) with:
  - `_VALID_MODES` frozenset guard (review/adversarial/consultation).
  - `_INSTALL_HINT = "npm install -g @openai/codex"` (single source of truth; mirrored by the plugin registration).
  - `_CODEX_TIMEOUT = 600.0` (10 min — codex can be slow on long-file reviews, vs invoke_native_cli default 120s).
  - `tool_available()` → `shutil.which("codex") is not None`.
  - `invoke_codex(prompt, *, mode, cwd, timeout)` → `invoke_native_cli(["codex","exec"], prompt=..., cwd=..., timeout=..., skip_permissions=True)`. Mode is NOT passed as a CLI flag (codex CLI has no --mode today) — it only tags the output artifact.
  - `_frontmatter_yaml(CodexReview)` → hand-rolled single-quoted-string YAML emitter (no pyyaml dep).
  - `_derive_verdict(mode, stdout)` → only mode='review' parses stdout for pass/fail markers; adversarial/consultation always 'n/a'.
  - `codex_handler(ctx, *, role, args)`:
    - Fail-fast mode/target validation BEFORE invoke.
    - Delegates CLI call to `invoke_codex` (which raises `SkillUnavailable` cleanly if tool missing — BEFORE any file write).
    - Derives verdict + truncates summary to 500 chars.
    - Atomically writes `codex-review.md` under `ctx.sprint_dir`.
    - Returns `{artifact_path, mode, stdout}`.

REFACTOR: none needed.

### Task 2 — Plugin registration (3 tests)

RED/GREEN combined — edited `GstackSprintPlugin`:

- Added imports: `SkillRegistration`, `codex_handler as _codex_handler`, `tool_available as _codex_tool_available`.
- Added `contribute_skills()` method returning a single-element list with the /codex entry.
- After sibling executors (Plans 05-04 + 05-05) landed, the method now returns three entries (`/codex` + `/ship` + `/setup-deploy`) — all three entries landed as a merged list in a single file snapshot (see Cross-Executor section below).

All 9 tests in `tests/templates/gstack/skills/test_codex.py` green:

```
.........                                                                [100%]
9 passed in 0.88s
```

## Acceptance Criteria

| Criterion | Status |
|---|---|
| `grep -q "def codex_handler" clawteam/templates/gstack/skills/codex/handler.py` | PASS |
| `grep -q "def tool_available" clawteam/templates/gstack/skills/codex/handler.py` | PASS |
| `grep -q "invoke_native_cli" clawteam/templates/gstack/skills/codex/handler.py` | PASS |
| `grep -c "shell=True" clawteam/templates/gstack/skills/codex/handler.py` returns 0 | PASS (0 matches) |
| `grep -q 'name="/codex"' clawteam/plugins/gstack_sprint_plugin.py` | PASS |
| `grep -q 'roles=frozenset({"engineer", "reviewer"})' clawteam/plugins/gstack_sprint_plugin.py` | PASS |
| `grep -q '"npm install -g @openai/codex"' clawteam/plugins/gstack_sprint_plugin.py` | PASS |
| `grep -q 'def contribute_skills' clawteam/plugins/gstack_sprint_plugin.py` | PASS |
| `pytest tests/templates/gstack/skills/test_codex.py -q` 9 passed | PASS |
| Plan verification: `GstackSprintPlugin().contribute_skills()[0].name == "/codex"` | PASS |

## Threat Model Status

All four T-05-03-* threat dispositions from the plan register are honoured:

| Threat ID | Category | Disposition | Where enforced |
|---|---|---|---|
| T-05-03-01 | Tampering — shell metachars in prompt | mitigate | `invoke_native_cli` shell=False + prompt-as-kwarg. Test `test_codex_adversarial_shell_metachar` asserts `captured["command"] == ["codex", "exec"]` (no splicing) and `captured["prompt"] == "; rm -rf /"` (literal). |
| T-05-03-02 | Information Disclosure — FAKE_SECRET leak to codex env | mitigate | `invoke_native_cli` default env = `scrub_env(os.environ)` from Plan 05-01. Handler never passes `env=...`. |
| T-05-03-03 | Spoofing — non-engineer/reviewer invokes /codex | mitigate | `SkillDispatcher` checks `role in reg.roles`. Test `test_codex_registration_dispatches_through_dispatcher` asserts designer → `SkillNotPermitted`. |
| T-05-03-04 | Tampering — malicious markdown in codex stdout summary | accept | Summary stored as string field, truncated to 500 chars. EvidenceGate does not execute stored markdown. |

No new threat flags introduced beyond the plan's register.

## Deviations from Plan

**None functional** — plan executed exactly as written.

**One structural note (Rule 2 — auto-adjust for cross-executor conflict)**:

- **[Rule 2 — Auto-add missing handling] Graceful cross-executor stash interaction**
  - **Found during:** Task 1 commit + Task 2 commit.
  - **Issue:** Parallel executors for Plans 05-04 (`/ship`) and 05-05 (`/setup-deploy`) ran concurrently under the same working tree. Their `git commit` absorbed my staged files into their commits rather than leaving them for a Plan 05-03-tagged commit.
  - **Outcome:**
    - My test file `tests/templates/gstack/skills/test_codex.py` (Task 1 RED) was committed under `test(05-04): add failing tests for /ship skill (18 tests)` (commit `f3113d8`).
    - My Task 1 GREEN files (`clawteam/templates/gstack/skills/codex/__init__.py` + `handler.py`) were committed under `test(05-05): add failing tests for /setup-deploy skill (11 tests)` (commit `0b52021`).
    - My Task 2 plugin edits (`contribute_skills` method + two new imports) were committed under `feat(05-04): ship_handler + plugin registration (Task 2)` (commit `a991ea8`), which also added `/ship` and `/setup-deploy` entries alongside mine in a single merged method.
  - **Why I did NOT create recovery `feat(05-03)` commits:** rolling those sibling commits back would destroy their work; cherry-picking a synthetic `feat(05-03)` commit with identical tree would duplicate history. Functional correctness is preserved (all 9 tests green; plugin registration returns /codex entry with correct roles + hint).
  - **Audit path:** `git log --all --oneline` + `git blame clawteam/plugins/gstack_sprint_plugin.py | grep "/codex"` both surface the /codex registration even though it lives under an `05-04` commit.
  - **Precedent:** same pattern recorded in STATE.md for Plan 04-10 Task 3 (conductor.py edits landed under `docs(04-12)` commit).

## Authentication Gates Encountered

None — plan does not invoke any auth-gated binaries; all test monkeypatching is local.

## Deferred Issues

None introduced by Plan 05-03. Two tests (`test_gstack_plugin.py::test_six_evidence_schemas_registered` + `test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present`) fail under full-suite run due to pre-existing test-cross-contamination in the process-global `EvidenceSchemaRegistry` — both pass in isolation. This bug predates Plan 05-03 (noted in STATE.md as "05-01 defers test-cross-contamination ... logged at deferred-items.md").

## Self-Check

**Files on disk:**

- `clawteam/templates/gstack/skills/codex/__init__.py` — FOUND.
- `clawteam/templates/gstack/skills/codex/handler.py` — FOUND (221 LOC).
- `tests/templates/gstack/skills/test_codex.py` — FOUND (295 LOC, 9 tests).
- `tests/templates/__init__.py`, `tests/templates/gstack/__init__.py`, `tests/templates/gstack/skills/__init__.py` — FOUND.
- `clawteam/plugins/gstack_sprint_plugin.py` — modified; contribute_skills method present with /codex entry at index 0.

**Commits (all functional content shipped):**

- RED tests: committed in `f3113d8` (sibling absorption).
- Task 1 GREEN (handler): committed in `0b52021` (sibling absorption).
- Task 2 GREEN (plugin wiring): committed in `a991ea8` (sibling absorption, additive merge with /ship + /setup-deploy).

**Verification:**

- `pytest tests/templates/gstack/skills/test_codex.py -q` → 9 passed.
- `python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; s = GstackSprintPlugin().contribute_skills(); assert any(r.name == '/codex' and r.roles == frozenset({'engineer','reviewer'}) for r in s); print('ok')"` → ok.
- All 8 grep-level acceptance criteria pass.

## Self-Check: PASSED
