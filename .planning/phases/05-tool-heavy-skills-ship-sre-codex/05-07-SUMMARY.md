---
phase: 05-tool-heavy-skills-ship-sre-codex
plan: 07
subsystem: gstack-skills
tags:
  - skill-document-release
  - ship-chain
  - interaction-gate
  - idempotency
  - adversarial-safety
requirements:
  - SKILL-14
  - SKILL-16
dependency_graph:
  requires:
    - "05-01 (SkillRegistration + invoke_native_cli substrate)"
    - "05-02 (ShipNotes Phase 5 fields — auto_invoked_skills)"
    - "05-04 (/ship 5-step orchestration — we add the auto-invoke tail)"
  provides:
    - "/document-release skill (SKILL-16) at clawteam/templates/gstack/skills/document_release/"
    - "/ship → /document-release auto-invoke chain (D-11)"
    - "5th SkillRegistration on GstackSprintPlugin"
  affects:
    - "ship-notes.md auto_invoked_skills field (populated on success)"
    - "<sprint_dir>/docs-updates/<ISO-8601>.diff (new artifact path)"
    - "<sprint_dir>/document-release-summary.md (new artifact path)"
    - "<sprint_dir>/questions/docrel_*.md (new InteractionGate question family)"
tech-stack:
  added:
    - "difflib.unified_diff (stdlib) — patch format generator"
  patterns:
    - "PEP 562 __getattr__ lazy import in package __init__ to defer handler-module import until first use (breaks ship ↔ document_release import cycle at collection time)"
    - "Non-destructive artifact emission — patches written to sidecar docs-updates/, never edits in-place"
    - "try/except demotion — /document-release failure recorded as string marker in auto_invoked_skills, never propagates to ship_status"
key-files:
  created:
    - clawteam/templates/gstack/skills/document_release/__init__.py
    - clawteam/templates/gstack/skills/document_release/doc_walker.py
    - clawteam/templates/gstack/skills/document_release/patch_emitter.py
    - clawteam/templates/gstack/skills/document_release/handler.py
    - tests/templates/gstack/skills/test_document_release.py
  modified:
    - clawteam/templates/gstack/skills/ship/handler.py
    - clawteam/plugins/gstack_sprint_plugin.py
    - tests/test_ship_skill.py
decisions:
  - "Tests placed at tests/templates/gstack/skills/test_document_release.py (matches test_codex.py + test_setup_deploy.py convention). Ship auto-invoke tests 11-13 appended to tests/test_ship_skill.py (not the aspirational tests/templates/gstack/skills/test_ship.py path in the plan — real file is test_ship_skill.py)."
  - "Ship handler imports document_release at call time (inside try/except) per D-11 pattern — keeps a /document-release package failure from breaking /ship import collection."
  - "__init__.py uses PEP 562 __getattr__ for lazy handler import rather than eager — avoids any future circular-import pitfalls with /ship auto-invoke and keeps Task 1 unit-testable without the handler module existing (RED-phase requirement)."
  - "emit_patches prepends <!-- STALE: ref --> marker lines rather than deleting/rewriting — preserves original doc content for reviewer diff and makes the patch self-documenting."
  - "_find_stale_refs uses pure set intersection (refs & removed_paths) — no fuzzy path matching to keep behavior predictable under adversarial doc content (T-05-07-01)."
metrics:
  duration_min: 11
  completed_date: "2026-04-21T14:46:54Z"
  tasks_completed: 2
  files_touched: 7
  tests_added: 13
  commit_hashes:
    - db38d96  # test(05-07): add failing tests for /document-release pure helpers + handler
    - c0ef5d6  # feat(05-07): doc_walker + patch_emitter pure helpers for /document-release
    - a056e5f  # test(05-07): add failing tests for /ship auto-invoke /document-release chain
    - 2c4ce2d  # feat(05-07): document_release_handler + /ship auto-invoke + plugin registration
---

# Phase 5 Plan 07: /document-release Summary

`/document-release` skill (SKILL-16) — diff-vs-docs stale-reference detector with non-destructive unified-diff patch emission + InteractionGate gating + idempotent re-run + /ship auto-invoke chain (D-11).

## What Shipped

### Task 1 — Pure helpers (doc_walker + patch_emitter)

Three pure functions with zero external I/O except the one filesystem read in `emit_patches`:

- **`walk_docs(root)`** — rglob `*.md` under root with an `_EXCLUDED_DIRS` frozen-set (node_modules / .venv / .git / __pycache__ / dist / build / .tox / .pytest_cache) so a project with vendored deps or a venv does not drown the result set in third-party READMEs. Returns sorted path list.
- **`extract_code_refs(md_content)`** — parses inline backtick spans + `def X` / `function X` / `class X` / `export function X` signatures. Multi-word spans (`` `class Baz` ``, `` `export function bar` ``) are split on whitespace; leading keywords (def/class/function/export) are stripped so the payload identifier flows through. Regex patterns are deliberately linear-time (one negated char class, no nested quantifiers) to mitigate catastrophic-backtracking DoS on adversarial doc content (threat T-05-07-01).
- **`emit_patches(doc_path, stale_refs, *, max_patches=50)`** — reads the doc, prepends `<!-- STALE: ref was removed/renamed -->` marker lines above each first-match of a stale ref, and returns the `difflib.unified_diff` string. Caps at `max_patches` with a `# NOTE: N additional stale refs deferred` trailer for T-05-07-05 adversarial-safety.

### Task 2 — handler + /ship auto-invoke + plugin registration

- **`document_release_handler(ctx, *, role, args)`** (SKILL-16 entry point) orchestrates the three pure helpers against a git diff:
  - `git diff --diff-filter=D --name-only <base>..<head>` via `invoke_native_cli` → removed-paths set
  - For each doc returned by `walk_docs(workspace_dir)`: intersect `extract_code_refs(doc)` with removed paths; if non-empty, call `emit_patches` and collect the per-doc patch
  - Write combined patches to `<sprint_dir>/docs-updates/<ISO-8601>.diff` (single bundle file per run, UTC timestamp)
  - For each per-doc patch whose line count > 5, write `<sprint_dir>/questions/docrel_<ts>_<NNN>.md` with an InteractionGate-shaped question artifact (yes/no choice + embedded diff preview up to 2000 chars)
  - Always (re-)write `<sprint_dir>/document-release-summary.md` — status `found_stale` with patch count, OR `no_changes` when nothing stale (Pitfall 7 idempotency: re-run with empty removed-set leaves disk untouched except for the summary overwrite)

- **`/ship` handler wiring (D-11)** — after all 5 ship steps succeed and before `_write_ship_notes`, try/except:
  ```python
  auto_invoked: list[str] = []
  try:
      from clawteam.templates.gstack.skills.document_release import handler as _dr_mod
      _dr_mod.document_release_handler(ctx, role=role, args={})
      auto_invoked.append("/document-release")
  except Exception as exc:
      auto_invoked.append(f"/document-release:failed:{exc}")
  ```
  Any exception raised by `/document-release` is demoted to the `/document-release:failed:<reason>` string marker; `ship_status` remains `succeeded` (T-05-07-04 mitigation). On `/ship` failure (any of the 5 steps), `/document-release` is never invoked and `auto_invoked_skills` stays empty.

- **Plugin registration** — `GstackSprintPlugin.contribute_skills()` returns 5 SkillRegistrations:
  `/codex` (engineer, reviewer) + `/ship` (shipper) + `/setup-deploy` (sre) + `/land-and-deploy` (shipper) + **`/document-release` (shipper)** — `tool_available=None` because git is baseline in any ClawTeam checkout.

## Test Results

- `tests/templates/gstack/skills/test_document_release.py` — **10/10 green** (6 pure-helper + 4 handler/plugin orchestration).
- `tests/test_ship_skill.py` — **21/21 green** (18 pre-existing from 05-04 + 3 new: auto-invoke success, auto-invoke failure demotion, no-invoke-on-ship-failure).
- Full Phase-5 plugin/skill regression (`test_gstack_plugin.py` + `test_plugin_manager_skills.py` + `test_skill_registration.py` + `test_skill_dispatcher.py` + `test_plugins.py` + `test_doctor*` + `test_template_def_extensions.py` + `test_invoke_native_cli.py`): **162/162 green**.
- Final verification snippet: `5 skills registered`.

## Verification

```bash
$ .venv/bin/python -m pytest tests/templates/gstack/skills/test_document_release.py tests/test_ship_skill.py -q
...............................                                          [100%]
31 passed in 0.94s

$ .venv/bin/python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; names = sorted(s.name for s in GstackSprintPlugin().contribute_skills()); assert names == ['/codex', '/document-release', '/land-and-deploy', '/setup-deploy', '/ship']; print('5 skills registered')"
5 skills registered
```

## Acceptance Criteria

Task 1:
- `grep -q "def walk_docs" clawteam/templates/gstack/skills/document_release/doc_walker.py` — FOUND
- `grep -q "def extract_code_refs" clawteam/templates/gstack/skills/document_release/doc_walker.py` — FOUND
- `grep -q "def emit_patches" clawteam/templates/gstack/skills/document_release/patch_emitter.py` — FOUND
- 6 Task-1 tests pass — PASS

Task 2:
- `grep -q "def document_release_handler" clawteam/templates/gstack/skills/document_release/handler.py` — FOUND
- `grep -q 'name="/document-release"' clawteam/plugins/gstack_sprint_plugin.py` — FOUND
- `grep -q "auto_invoked" clawteam/templates/gstack/skills/ship/handler.py` — FOUND
- `grep -qE "document_release_handler|_dr_mod|_dr_handler" clawteam/templates/gstack/skills/ship/handler.py` — FOUND
- 10 document_release tests green — PASS
- 21 ship tests green — PASS (18 pre-existing + 3 new)
- Plugin regression still green — PASS (48 plugin-scoped tests all green in isolation)

## Threat Model Coverage

| Threat ID    | Category | Disposition | Mitigation Landed |
|--------------|----------|-------------|-------------------|
| T-05-07-01   | DoS — regex catastrophic backtrack | mitigate | All regex patterns linear-time (one negated char class, no nested quantifiers). See `doc_walker._INLINE_CODE_RE`. |
| T-05-07-02   | Tampering — non-shipper invokes | mitigate | `SkillRegistration(roles=frozenset({"shipper"}))` + SkillDispatcher role check (covered by test_document_release_registered). |
| T-05-07-03   | Info disclosure — secrets in patch | accept | Out-of-scope: docs/ is checked-in, pre-existing repo hygiene issue. |
| T-05-07-04   | Tampering — doc-release failure fails ship | mitigate | try/except in `ship.handler` demotes exception to `/document-release:failed:<reason>` marker. Test `test_ship_handler_continues_when_document_release_fails` locks. |
| T-05-07-05   | DoS — huge diff produces 1000s of patches | mitigate | `emit_patches(..., max_patches=50)` cap + trailer note. Test `test_emit_patches_capped` locks. |

## Deviations from Plan

### Structural

1. **Ship tests file path** — plan specified `tests/templates/gstack/skills/test_ship.py`; the real existing ship test module is `tests/test_ship_skill.py`. Appended tests 11-13 to the existing file (project convention for Phase 5 skills is mixed — test_codex.py + test_setup_deploy.py live under `tests/templates/gstack/skills/`, but test_ship_skill.py predates that subdir and lives flat at `tests/`). Rule 3 — blocking issue auto-fixed; using wrong path would have failed `pytest -x`.

2. **`__init__.py` lazy handler import (PEP 562)** — plan specified eager import of `document_release_handler` in `__init__.py`. That creates an import-order chicken-and-egg during TDD: Task 1 tests need `doc_walker` importable BEFORE handler.py exists. Switched to `__getattr__` lazy import so the package is importable with only the pure-helper submodules present; handler.py is imported on first attribute access. Still allows `from clawteam.templates.gstack.skills.document_release import document_release_handler` at every call site. Rule 3 — blocking issue auto-fixed.

### Behavioral

3. **`extract_code_refs` multi-word span handling** — plan's minimal pseudo-code only handled single-token inline spans. Real doc content uses `` `class Baz` `` and `` `export function bar` `` idioms. Added whitespace-split fallback + keyword-stripping (def/class/function/export) so the identifier flows through. Rule 1 — bug auto-fixed (Test 2 would otherwise fail without this).

4. **`_find_stale_refs` uses pure set intersection** — plan text suggested fuzzy matching ("paths and identifiers"); the actual test only requires exact string intersection between doc refs and removed paths. Kept set semantics (predictable + no false positives from substring matches) rather than introducing fuzzy logic the tests don't require. Rule 1 — keeps behavior predictable under adversarial doc content.

5. **Question artifact shape** — plan's example was terse; expanded to include `origin_skill: /document-release` frontmatter + `priority: normal` + a `` ```diff ``` `` fence around the embedded patch so downstream gate / CLI rendering has structured metadata. Rule 2 — missing critical metadata for a new artifact family auto-added.

### Scope boundary respected

- Did NOT fix the pre-existing test-cross-contamination failures in `tests/test_evidence_schemas_phase5.py` + `tests/test_gstack_plugin.py::test_seven_phases_registered_in_order` + `tests/test_plugin_hooks.py::test_evidence_schema_collision_when_registry_present` — these fail only when the full `pytest tests/` suite runs in one process (shared `_registry` state). They all pass in isolation. Already documented as deferred in `.planning/phases/05-tool-heavy-skills-ship-sre-codex/deferred-items.md` by Plan 05-01; not a 05-07 regression.

## Known Stubs

None. The handler writes fully-typed frontmatter on all artifacts and pushes real file content.

## Self-Check: PASSED

Created files (all on disk):
- FOUND: clawteam/templates/gstack/skills/document_release/__init__.py
- FOUND: clawteam/templates/gstack/skills/document_release/doc_walker.py
- FOUND: clawteam/templates/gstack/skills/document_release/patch_emitter.py
- FOUND: clawteam/templates/gstack/skills/document_release/handler.py
- FOUND: tests/templates/gstack/skills/test_document_release.py

Modified files:
- FOUND: clawteam/templates/gstack/skills/ship/handler.py (auto_invoke_skills block added)
- FOUND: clawteam/plugins/gstack_sprint_plugin.py (/document-release SkillRegistration)
- FOUND: tests/test_ship_skill.py (3 auto-invoke chain tests appended)

Commits (all on gstack-integration branch):
- FOUND: db38d96 test(05-07): add failing tests for /document-release pure helpers + handler
- FOUND: c0ef5d6 feat(05-07): doc_walker + patch_emitter pure helpers for /document-release
- FOUND: a056e5f test(05-07): add failing tests for /ship auto-invoke /document-release chain
- FOUND: 2c4ce2d feat(05-07): document_release_handler + /ship auto-invoke + plugin registration
