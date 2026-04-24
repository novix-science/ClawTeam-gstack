---
phase: 06-browser-skills-design-pipeline-team-memory
plan: 09
subsystem: skills/design
tags:
  - skill-design-html
  - framework-detection
  - production-html
  - designer-role
  - pure-filesystem

# Dependency graph
requires:
  - phase: 06-01
    provides: "Phase 6 scaffolding (REQUIREMENTS, CONTEXT, RESEARCH) + SKILL-12 slot"
  - phase: 05-01
    provides: "SkillRegistration + SkillDispatcher + SkillUnavailable hierarchy"
  - phase: 03-07
    provides: "GstackSprintPlugin skeleton exposing contribute_skills hook"

provides:
  - "clawteam.templates.gstack.skills.design_html.framework_detect.detect_framework / FrameworkDetection"
  - "clawteam.templates.gstack.skills.design_html.handler.design_html_handler"
  - "/design-html SkillRegistration (roles={designer})"
  - "Cluster B (design pipeline: /design-shotgun + /design-html) complete"

affects:
  - 06-08  # /design-shotgun's chosen variant is consumed by /design-html as mockup_html_path
  - 06-10  # Both /design-shotgun pick events and /design-html emissions can be logged via /learn

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-filesystem handler (Phase 5 /document-release precedent) — no external CLI, no Playwright, no subprocess; tool_available=None on SkillRegistration so dispatch never gates on tool presence."
    - "Framework detection via dataclass return (FrameworkDetection) rather than tuple — ambiguous/candidates fields let the handler and future callers introspect the detection decision without reparsing package.json."
    - "Non-destructive ambiguity handling (D-13 invariant) — multi-framework package.json never emits source; instead writes questions/design-html-framework-<digest>.md with the /document-release frontmatter shape (question_id / priority / origin_skill). Digest-based filename = idempotent re-runs against the same mockup."
    - "Framework emission templates embed the source mockup verbatim (React wraps in dangerouslySetInnerHTML; Svelte/Vue pass through as-is inside <template>). First-pass goal is 'renders without hand-editing', not production-quality — the designer refactors in a follow-up."
    - "Defence-in-depth on malformed package.json (T-06-09-03) — json.JSONDecodeError / OSError / UnicodeDecodeError downgrade to plain fallback rather than raising; handler never crashes on adversarial dep manifests."

key-files:
  created:
    - clawteam/templates/gstack/skills/design_html/__init__.py
    - clawteam/templates/gstack/skills/design_html/framework_detect.py
    - clawteam/templates/gstack/skills/design_html/handler.py
    - tests/templates/gstack/skills/test_design_html.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py  # import + SkillRegistration

# Decisions locked-in
decisions:
  - "/design-html binds to designer role only (D-13). Other roles get SkillNotPermitted — engineers who need a framework-aware emitter can invoke /design-shotgun → pick a variant → hand off to designer."
  - "Framework detection order is deterministic (react → svelte → vue → plain). Order only matters for the single-framework case (first match wins); multi-framework always surfaces as ambiguous to preserve designer intent."
  - "devDependencies counted equally with dependencies — component-library repos (React as peer/dev dep) still correctly detected."
  - "Ambiguous resolution via question.md, not args override. A v1 --framework=react arg was considered but rejected: the designer's intent is already captured in package.json; forcing an override would encourage Claude to skip the question gate."
  - "Plain-HTML fallback emits the full triple (index.html + styles.css + app.js) even though only index.html carries the mockup — the pair of empty scaffolds sets the designer up to split CSS / behaviour without recreating the file structure themselves."

# Execution metrics
metrics:
  duration: "11min"
  tasks_completed: 1
  files_changed: 5
  completed_date: "2026-04-22"
---

# Phase 6 Plan 09: /design-html Summary

**One-liner:** Designer-invoked skill that takes a chosen mockup HTML from /design-shotgun, auto-detects the project's frontend framework from package.json (React → .jsx / Svelte → .svelte / Vue → .vue / plain → index.html + styles.css + app.js triple), and emits production-shape source at the appropriate root — with a non-guessing question.md fallback when multiple frameworks are present (D-13 mitigation).

## Context

Phase 6 Wave 3 Cluster B (design pipeline) final plan. /design-shotgun (06-08) converges on a single chosen variant whose HTML is pinned in `design-board/<variant>/index.html`. /design-html reads that path, introspects the project to decide React/Svelte/Vue/plain, and writes a single framework-appropriate file so the designer can hand off to engineering without a manual framework-scaffolding step. The skill is deliberately first-pass — the emitted source embeds the mockup verbatim (React via `dangerouslySetInnerHTML`, Svelte/Vue via template pass-through) because the goal is "compiles / renders without hand-editing", not production-ready JSX.

## What shipped

### framework_detect.py (~100 LOC)

Pure function `detect_framework(project_root: Path) -> FrameworkDetection` with the following decision rules (per D-13):

| Input                                   | `framework` | `source_root` | `ambiguous` | `candidates`       |
| --------------------------------------- | ----------- | ------------- | ----------- | ------------------ |
| No `package.json`                       | `"plain"`   | `""`          | `False`     | `[]`               |
| `package.json`, none of R/S/V           | `"plain"`   | `""`          | `False`     | `[]`               |
| `package.json`, only `react`            | `"react"`   | `"src"`       | `False`     | `[]`               |
| `package.json`, only `svelte`           | `"svelte"`  | `"src"`       | `False`     | `[]`               |
| `package.json`, only `vue`              | `"vue"`    | `"src"`       | `False`     | `[]`               |
| `package.json` with `react` + `svelte`  | `""`        | `""`          | `True`      | `["react","svelte"]` |
| Malformed JSON (JSONDecodeError)        | `"plain"`   | `""`          | `False`     | `[]`               |

Both `dependencies` and `devDependencies` are scanned (Test 7 coverage). `isinstance(..., dict)` guards prevent crashing on hostile package.json shapes where `dependencies` is a list or null (T-06-09-03 mitigation).

### handler.py (~250 LOC)

`design_html_handler(ctx, *, role, args)` — 6 emission paths:

1. **React** (`_emit_react`) — writes `<src>/<ComponentName>.jsx`. Content: import React + default-export function wrapping `<div dangerouslySetInnerHTML={{ __html: MOCKUP_HTML }} />`, with mockup embedded as a string literal via `!r`.
2. **Svelte** (`_emit_svelte`) — writes `<src>/<ComponentName>.svelte`. Content: empty `<script>` block + mockup HTML body.
3. **Vue** (`_emit_vue`) — writes `<src>/<ComponentName>.vue`. Content: `<template>` block with mockup + `<script>` default-export naming the component.
4. **Plain** (`_emit_plain`) — writes triple `index.html` (full mockup) + empty `styles.css` + empty `app.js` at project root.
5. **Ambiguous** (`_write_ambiguity_question`) — writes `<sprint>/questions/design-html-framework-<digest>.md` with frontmatter `question_id / priority=blocking / origin_skill=/design-html` + markdown body listing candidates and instructing the user to answer in `answers/<qid>.md`. **No framework emission** in this path — strict non-guessing invariant.
6. **Missing mockup path** — `FileNotFoundError` raised immediately (T-06-09-01 validation).

Every terminal state (emitted / awaiting_user) writes a `design-html-note.md` artifact with frontmatter (status / framework / target_paths / persona / step_label=design-html / done=true) — this is the /reflect-phase consumable.

### Plugin registration

```python
SkillRegistration(
    name="/design-html",
    roles=frozenset({"designer"}),
    handler=_design_html_handler,
    tool_available=None,   # pure filesystem — no CLI / Playwright
    install_hint="",
)
```

Registered between `/design-shotgun` (06-08) and `/learn` (06-10) in `contribute_skills`. Plugin now exposes 13 skills total (Phase-5 seven + Phase-6 browser triplet + design pipeline pair + /learn).

### Tests (14 total, all green)

1-7 — `detect_framework` pure function: react, svelte, vue, plain (no pkg.json), plain (pkg.json without frontend dep), ambiguous (react + svelte both present), devDependencies scanned.
8-11 — Handler emission: react writes Hero.jsx, svelte writes Hero.svelte, vue writes Hero.vue (with `<template>` block), plain writes index.html + styles.css + app.js triple (3 paths in result).
12 — Ambiguous emission: question.md written with react + svelte mentioned, `status=awaiting_user`, **no** framework source emitted (assert Hero.jsx / index.html absent).
13 — Missing mockup path → FileNotFoundError.
14 — Plugin registration: `/design-html` present with `roles == frozenset({"designer"})` and callable handler.

Total Wave-3 suite green: 14 design-html + 5 plugin-coverage = 19 passing.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 3 — Blocking] Parallel-executor plugin-file conflict**
- **Found during:** Task 1 (plugin registration)
- **Issue:** Plan 06-08 and 06-10 executors were editing `clawteam/plugins/gstack_sprint_plugin.py` concurrently. 06-08's GREEN commit (a5dfcd9) deleted the `/learn` import/registration while adding `/design-shotgun`; 06-10's follow-up commit (788347f) re-added `/learn` **and** picked up my local `/design-html` import + registration edits that had not yet been committed.
- **Fix:** My `/design-html` registration ended up committed inside 788347f by the parallel 06-10 executor. To complete my own plan I only needed to commit the three `clawteam/templates/gstack/skills/design_html/*.py` module files — the plugin change was already in HEAD. Verified final state has all 13 skills (imports + SkillRegistrations aligned) and test suite green.
- **Files modified:** None by me (plugin diff was empty at commit time).
- **Commit:** 4852e9d (GREEN; carries only the design_html skill module files).

### Rule 2 auto-adds

**1. Test-14 relaxation to subset contract**
- **Plan requirement:** "12 skills registered after this plan."
- **Applied:** The test asserts `/design-html` is registered with `roles={designer}` via subset check — not a strict `len(skills) == 12` — because Wave-3 plans 06-08 / 06-09 / 06-10 run in parallel and each adds a skill. A strict equality check would race under parallel execution. Matches the precedent in `tests/plugins/test_all_seven_skills_registered.py` which was explicitly relaxed from equality to subset in Phase 6 Wave 2 for this same reason.

## Authentication gates

None. Skill is pure filesystem; no CLI / Playwright / external auth touched.

## Known stubs

None. All emission paths write concrete content:
- React wrapper embeds mockup HTML as a string literal (renders immediately).
- Svelte / Vue pass the mockup through their template blocks.
- Plain triple writes the mockup into `index.html`; `styles.css` and `app.js` are intentional empty scaffolds the designer fills in (documented in the emitted comment header).

## Self-Check: PASSED

- [x] `clawteam/templates/gstack/skills/design_html/__init__.py` exists
- [x] `clawteam/templates/gstack/skills/design_html/framework_detect.py` exists with `def detect_framework` + `class FrameworkDetection`
- [x] `clawteam/templates/gstack/skills/design_html/handler.py` exists with `def design_html_handler`
- [x] `tests/templates/gstack/skills/test_design_html.py` exists with 14 tests
- [x] `grep -q 'name="/design-html"' clawteam/plugins/gstack_sprint_plugin.py` succeeds
- [x] `pytest tests/templates/gstack/skills/test_design_html.py -q` → 14 passed
- [x] `pytest tests/plugins/ -q` → 5 passed (BC preserved)
- [x] Total plugin skill count: 13 (Phase-5 seven + Phase-6 browser triplet + design pipeline pair + /learn)
- [x] Commits: f0f9437 (test RED) + 4852e9d (feat GREEN)
- [x] No deletions introduced by commit 4852e9d
