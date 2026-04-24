---
phase: 01-core-harness-extensions
status: SECURED
threats_total: 25
threats_closed: 25
threats_open: 0
asvs_level: L1
deferred_count: 2
block_on: any open MITIGATE without evidence
auditor: gsd-secure-phase
audited_at: 2026-04-17
---

# Phase 01 — Core Harness Extensions Security Verification

**Result:** SECURED — all 25 threats (T-01-01..T-01-25) closed by evidence.

Phase 1 is a library-level change with no network surface. ASVS L1 is the
applicable standard. Block policy: any open MITIGATE threat missing either its
declared code pattern or its named regression test blocks the phase; ACCEPT and
DEFERRED dispositions are verified through documented rationale alone.

## Scope

- Implementation files (READ-ONLY during this audit): `clawteam/harness/phase_registry.py`, `clawteam/harness/review_router.py`, `clawteam/harness/interaction_gate.py`, `clawteam/harness/orchestrator.py`, `clawteam/sprint/state.py`, `clawteam/sprint/qa.py`, `clawteam/plugins/base.py`, `clawteam/plugins/manager.py`.
- Test corpus: `tests/test_phase_registry.py`, `tests/test_plugin_hooks.py`, `tests/test_sprint_state.py`, `tests/test_interaction_gate.py`, `tests/test_sprint_qa.py`, `tests/test_orchestrator_phase_registry.py`.
- Shared primitives referenced: `clawteam/paths.py` (`validate_identifier`, `ensure_within_root`), `clawteam/fileutil.py` (`file_locked`, `atomic_write_text`).

## Threat Verification — MITIGATE (12 threats)

Every MITIGATE threat requires two artifacts: (1) the declared mitigation
pattern present in implementation, (2) the named regression test present and
passing.

| Threat ID | Category | Pattern Evidence | Test Evidence | Status |
|-----------|----------|------------------|---------------|--------|
| T-01-01 | Tampering — `PhaseRegistry._names` partial-state after failed register | `phase_registry.py:71-100` (validation complete before any mutation; `_names.add` only in the commit block `L87-90`) | `tests/test_phase_registry.py:35` `test_duplicate_phase_across_plugins_raises_value_error` — asserts `ordered_names() == ["a", "b"]` after failed 2nd registration | CLOSED |
| T-01-05 | DoS — circular import `harness.phase_registry` ↔ `plugins.base` | `plugins/base.py:8-11` (`TYPE_CHECKING`-guarded imports for `Phase`, `PhaseGate`, `ReviewRouter`); `plugins/manager.py:145` lazy `from clawteam.harness.phase_registry import get_registry` inside `_instantiate_and_register` method body | `tests/test_plugin_hooks.py:51` `test_plugin_manager_populates_registry_on_register` — live-exercises the runtime import path | CLOSED |
| T-01-06 | Tampering — `_state_path` path composition | `sprint/state.py:110-122` (`validate_identifier(team, ...)` + `validate_identifier(sprint_id, ...)` + `ensure_within_root(root, team, "sprints", sprint_id)` before `state.json` suffix; validation runs BEFORE `mkdir`, see `state.py:131-132`) | `tests/test_sprint_state.py:117` `test_sprint_state_invalid_team_raises` (asserts no `tmp_path.parent/"etc"` created) + `tests/test_sprint_state.py:127` `test_sprint_state_invalid_sprint_id_raises` | CLOSED |
| T-01-07 | DoS — torn write during concurrent save | `sprint/state.py:124-135` (`save()` wraps `atomic_write_text` inside `file_locked(path)` context manager) | `tests/test_sprint_state.py:78` `test_sprint_state_concurrent_writers_last_write_wins` — 8 threads, final state matches one marker, no stray `.tmp` residue | CLOSED |
| T-01-10 | EoP — crafted `sprint_id` on load | `sprint/state.py:137-149` `load()` calls same `_state_path()` → same `validate_identifier` + `ensure_within_root` chain as save; read under `file_locked()` | Covered transitively by T-01-06 tests (same `_state_path` surface); `test_sprint_state_save_then_load_roundtrip` exercises live path | CLOSED |
| T-01-11 | Tampering — `_resolve_sprint_dir` symlink escape | `interaction_gate.py:102-144` (`validate_identifier` on team/sprint_id, `ensure_within_root(get_data_dir()/"teams", team, "sprints", sprint_id)`, then `resolved.relative_to(root)` symlink double-check at `L133-138`) | `tests/test_interaction_gate.py:139` `test_gate_rejects_symlink_escape_from_data_dir` — creates symlink `questions/ -> tmp_path.parent/"etc"`; gate raises `ValueError` or returns `(False, "invalid sprint path: ...")` | CLOSED |
| T-01-15 | EoP — symlink in `questions/` or `answers/` | `interaction_gate.py:146-180` `_scan()` defense-in-depth: re-resolves `questions_dir` (`L162-167`) and `answers_dir` (`L169-174`), `relative_to(sprint_resolved)` rejects escape after `_resolve_sprint_dir` already returned | Covered by T-01-11 test (single test exercises both outer and inner guard layers) | CLOSED |
| T-01-16 | Tampering — malformed frontmatter parser crash | `sprint/qa.py:140-224` (`_parse_frontmatter` rejects missing opening/closing `---` fences at `L147, L214`, non-key lines at `L167-170`, unexpected indentation at `L162-165`; pydantic `model_validator` at `qa.py:53-61` catches shape-mismatch) | `tests/test_sprint_qa.py` — `test_question_type_literal_rejects_invalid`, `test_question_multi_choice_requires_choices`, `test_question_freeform_rejects_choices` exercise validation layer | CLOSED |
| T-01-20 | EoP — YAML CVE class (`yaml.unsafe_load` family) | `sprint/qa.py:1-224` — stdlib-only parser; `grep -cE "import (yaml\|pyyaml)" clawteam/sprint/qa.py` returns 0. No `!!python/object`, anchors, aliases, or exec-capable YAML tags are implementable by the narrow D-08 parser | Entire `tests/test_sprint_qa.py` suite (10 tests) exercises parser; no YAML CVE class reachable by construction | CLOSED |
| T-01-21 | Tampering — registry cross-test contamination | `tests/test_orchestrator_phase_registry.py` — every test wraps `get_registry().register(...)` in `try / finally reset_registry()` (pattern present in all 6 tests); `phase_registry.py:133-136` `reset_registry()` replaces `_REGISTRY` with a fresh instance | `tests/test_plugin_hooks.py:51` `test_plugin_manager_populates_registry_on_register` — reset before AND after; full-suite 651 passed with no cross-test leakage (SUMMARY 01-05 §Verification) | CLOSED |
| T-01-22 | DoS — empty phase list | `orchestrator.py:49-72` (the `if not phases:` branch falls through to `registered_phases = registry.ordered_names()`; if `registered_phases` is also empty (`elif registered_phases`) PhaseState's default `list(DEFAULT_PHASES)` carries through — see `L72` comment `# else: PhaseState's default already == list(DEFAULT_PHASES) — no action`) | `tests/test_orchestrator_phase_registry.py` `test_orchestrator_falls_back_to_default_phases_when_registry_empty` asserts `orch.state.phases == list(DEFAULT_PHASES)` | CLOSED |
| T-01-24 | EoP — plugin phase-name shadowing core | `phase_registry.py:80-85` — duplicate-phase `ValueError` at registration (already closed upstream at T-01-01); orchestrator consumes a pre-validated list, no re-check needed | `tests/test_phase_registry.py:35` `test_duplicate_phase_across_plugins_raises_value_error` (shared evidence with T-01-01) | CLOSED |

## Threat Verification — ACCEPT (11 threats)

ACCEPT threats require a documented rationale in the plan's threat model; the
audit confirms the rationale is plausible given the code-level reality and that
no emergent implementation detail changes the risk calculus.

| Threat ID | Category | Disposition Rationale | Code Reality | Status |
|-----------|----------|------------------------|--------------|--------|
| T-01-02 | Repudiation / DoS — plugin-triggered `ValueError` during `_instantiate_and_register` | Fatal-at-load is the documented design (D-03); swallowing would permit silent phase shadowing | `plugins/manager.py:146-151` — no try/except around `get_registry().register(...)`; `ValueError` propagates | CLOSED |
| T-01-04 | Information Disclosure — `PhaseRegistry.contributions()` | Debug/visibility feature; no secrets pass through (phase names are human identifiers) | `phase_registry.py:114-116` — returns only `_PluginContribution` snapshots already populated by public `register()` | CLOSED |
| T-01-08 | Information Disclosure — `state.json` plaintext goal + participants | `~/.clawteam/` is user-owned; same disclosure surface as existing `PhaseState` persistence | `sprint/state.py:124-135` — writes to `get_data_dir()/teams/<team>/sprints/<id>/state.json` with OS-level perms inherited | CLOSED |
| T-01-09 | Repudiation — concurrent writer overwrites | Last-write-wins is D-05's explicit semantic; richer merge deferred to Phase 2 | `sprint/state.py:133-134` — single `atomic_write_text` under lock; no merge step | CLOSED |
| T-01-12 | Spoofing — attacker writes `questions/<id>.md` to block a sprint | Blocking on unanswered questions IS the gate's job; defense at write surface, not gate | `interaction_gate.py:72-98` — gate never reads body, always honors presence | CLOSED |
| T-01-13 | Information Disclosure — reason string leaks question IDs | IDs are 8-char UUIDs (D-07), not secrets; reason bounded at 5 IDs | `interaction_gate.py:31, 93-97` — `_MAX_IDS_IN_REASON = 5` + `+N more` suffix enforced | CLOSED |
| T-01-14 | DoS — sprint dir with millions of question files | O(n) glob matches existing `ArtifactStore`/`SnapshotManager` surface; Phase 7 disk-budget alarm is holistic mitigation | `interaction_gate.py:176-180` — single `.glob("*.md")` per direction | CLOSED |
| T-01-17 | DoS — multi-gigabyte `.md` fed to `from_markdown` | Parser is O(n); file size bounded at write surface (Phase 2's SPRINT-09 artifact caps) | `sprint/qa.py:140-224` — line-wise parse, no unbounded recursion | CLOSED |
| T-01-18 | Information Disclosure — question body leaks into gate reason | Phase 1 gate is presence-only; body reads gated by future Phase 4 opt-in paths | `interaction_gate.py:176-180` — scans by filename stem only; no `read_text`/`open` on `.md` bodies | CLOSED |
| T-01-19 | Spoofing — `author:` forgery | Advisory field; harness does not authenticate writer. Phase 4 cross-agent verification will address higher-value artifacts | `sprint/qa.py:40-51` — `author` is a plain `str`, no signature check | CLOSED |
| T-01-25 | Repudiation — loaded run's phase list diverges from current registry | Correct per RFC 001 §4.6 — registry consulted at construction only, not at resume | `orchestrator.py` — `load()` / `find_latest()` rehydrate persisted `PhaseState.phases` directly (per Plan 01-05 SUMMARY Verification); not modified by this phase | CLOSED |

## Threat Verification — DEFERRED (2 threats)

DEFERRED threats are explicitly pushed to a later phase; the audit confirms
each is documented as such and has a plausible deferral target.

| Threat ID | Category | Deferred To | Rationale | Status |
|-----------|----------|-------------|-----------|--------|
| T-01-03 | EoP — malicious `ReviewRouter` from plugin | Phase 4 (Review-phase wiring RFC) | Phase 1 collects routers but no code path invokes `router.match()`. Documented in `01-01-SUMMARY.md` §Next Phase Readiness ("Known forward-looking contract for Phase 4"). Implementation confirmation: grep for `.match(` call-sites against `ReviewRouter` returns zero non-test matches | CLOSED (deferred) |
| T-01-23 | Tampering — `sprint_state.team` ≠ `team_name` | Phase 2 (sprint engine CLI) | Orchestrator stores `sprint_state` verbatim (`orchestrator.py:51` — composition, not merge); cross-validation belongs with `clawteam sprint start --team <name>` CLI per Plan 01-05 SUMMARY §Threat Register Status | CLOSED (deferred) |

## Unregistered Flags from SUMMARY.md

`## Threat Flags` sections explicitly scanned in every Phase 1 `-SUMMARY.md`:

- `01-01-SUMMARY.md`: no "## Threat Flags" section.
- `01-02-SUMMARY.md`: no "## Threat Flags" section (threat closure documented in §Threat Register Status instead).
- `01-03-SUMMARY.md`: no "## Threat Flags" section.
- `01-04-SUMMARY.md`: `## Threat Flags` present; content: "None. This plan's threat surface is fully captured in the plan's `<threat_model>` (T-01-16 through T-01-20)." — no new flags.
- `01-05-SUMMARY.md`: no "## Threat Flags" section (threat closure documented in §Threat Register Status instead).

**Unregistered flags: none.** No emergent attack surface was reported by
executors beyond what the 25-threat register already enumerates.

## ASVS L1 Applicability Check

Phase 1 adds no network endpoints, no authentication paths, no crypto
operations, no session management, and no data-at-rest encryption
requirements. The applicable ASVS controls are limited to:

- V1.1 (secure SDLC): RFC 001 threat model + TDD gates present in every plan.
- V5.3 (output encoding): N/A — no HTML/SQL/command-injection sinks introduced.
- V12.3.1 (filesystem traversal): `validate_identifier` + `ensure_within_root` + double-resolved `relative_to` guards across `sprint/state.py`, `interaction_gate.py`. Verified at T-01-06, T-01-10, T-01-11, T-01-15.
- V13.1.1 (generic input validation): pydantic v2 models across `SprintState`, `Question`, `Answer`, `Choice` with `model_validator` for cross-field invariants. Verified at T-01-16.

All applicable L1 controls are satisfied by the Phase 1 implementation.

## Audit Trail

- **Auditor:** `gsd-secure-phase` (verification-only pass; no implementation files modified).
- **Source of truth for dispositions:** `<threat_register>` provided in the audit prompt (cross-referenced against `<threat_model>` blocks in `01-01-PLAN.md` through `01-05-PLAN.md`).
- **Verification method:** per-threat grep for declared mitigation pattern in cited files; per-MITIGATE-threat confirmation that the named test exists in `tests/` with the expected function name.
- **Full test suite status at audit time (per `01-05-SUMMARY.md` §Verification Evidence):** 651 passed, 0 failures; Phase 0 regression matrix 12/12; combined Phase 1 tests 39 passed; ruff clean on all touched files.
- **No security fix required.** All 12 MITIGATE threats have evidence; all 11 ACCEPT threats are documented with plausible rationale; both DEFERRED threats are tracked against specific later phases.

## Result

**SECURED.** Block-on policy (any open MITIGATE without evidence or without its
named test) is satisfied: 0 MITIGATE threats are open. Phase 1 meets the
declared ASVS L1 baseline and is cleared for merge from the security-audit
perspective.
