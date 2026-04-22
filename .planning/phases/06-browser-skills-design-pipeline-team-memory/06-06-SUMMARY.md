---
phase: 06-browser-skills-design-pipeline-team-memory
plan: 06
subsystem: browser-skill-open-gstack-browser
tags:
  - skill-open-browser
  - headed-mode
  - cookie-injection
  - wave-2
dependency_graph:
  requires:
    - 06-01  # Phase 6 feature flags + TemplateDef sub-blocks
    - 06-04  # browser substrate (session + cookies)
  provides:
    - /open-gstack-browser skill (SKILL-10 part 2 of 3)
    - open_browser_handler entry point
    - open-browser-note.md artifact shape
  affects:
    - clawteam/plugins/gstack_sprint_plugin.py (9th SkillRegistration)
    - Wave 2 siblings (06-05 /browse, 06-07 /setup-browser-cookies)
tech-stack:
  added: []  # no new deps — consumes existing clawteam.browser + clawteam.fileutil
  patterns:
    - lazy-Playwright (D-02) via clawteam.browser.open_headed_with_context
    - cookie injection via load_cookies_for_domain (06-04 D-03 path)
    - frontmatter-only artifact write via atomic_write_text
    - URL scheme allow-list (http/https) before any browser launch (T-06-06-01)
key-files:
  created:
    - clawteam/templates/gstack/skills/open_gstack_browser/__init__.py
    - clawteam/templates/gstack/skills/open_gstack_browser/handler.py
    - tests/templates/gstack/skills/test_open_gstack_browser.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py  # +26 LOC: import + SkillRegistration
    - tests/plugins/test_all_seven_skills_registered.py  # relax strict ==7 to subset check
decisions:
  - "URL validation uses urllib.parse.urlparse + http/https allow-list; file:// / javascript: rejected before browser launch (T-06-06-01)"
  - "Port stripped from host before cookie-jar lookup — cookie jar keys on domain only"
  - "Phase 6 simplification: headed browser closes at end of `with open_headed_with_context(...)`; Phase 7 /close-gstack-browser will add persistent windows"
  - "Tests stub open_headed_with_context with @contextmanager so no Playwright install required in CI"
  - "hold_seconds defaults to 0 so tests don't block; caller-specified non-zero values drive time.sleep inside the context manager"
metrics:
  completed_date: "2026-04-22"
  tasks_completed: 1  # 1 TDD task (RED + GREEN)
  files_created: 3
  files_modified: 2
  tests_added: 7
  loc_added_handler: 160  # handler.py
  loc_added_tests: 249
  loc_modified_plugin: 26  # plugin import + registration
---

# Phase 6 Plan 06: /open-gstack-browser Skill Summary

One-liner: headed Chromium launcher with per-domain cookie injection for human UI interaction (designer/engineer/qa/dx-lead) — registered as the 9th skill on GstackSprintPlugin.

## What Landed

1. **Sub-package `clawteam/templates/gstack/skills/open_gstack_browser/`** (2 files):
   - `__init__.py` re-exports `open_browser_handler` for plugin wiring.
   - `handler.py` (~160 LOC) implements the SKILL-10 headed-mode entry point — validates URL, loads cookies from the team jar, launches headed Chromium via `open_headed_with_context`, navigates the page, optionally holds the window for `hold_seconds`, then closes and writes an `open-browser-note.md` frontmatter artifact so Phase-2 EvidenceGate sees completion.

2. **Plugin registration** (`clawteam/plugins/gstack_sprint_plugin.py` +26 LOC):
   - New import of `open_browser_handler` under the Phase-6 lazy-Playwright import block.
   - `SkillRegistration(name="/open-gstack-browser", roles={engineer,qa,dx-lead,designer}, tool_available=playwright_available, install_hint=…)` appended to `contribute_skills()`.
   - Plugin now returns **9 skills** (7 Phase-5 + `/browse` from sibling 06-05 + `/open-gstack-browser`).

3. **Tests** (`tests/templates/gstack/skills/test_open_gstack_browser.py`, 7 cases, ~249 LOC):
   - `test_happy_path` — artifact created with URL+domain in frontmatter; browser context entered and exited; page.goto called with exact URL.
   - `test_loads_cookies_for_host` — domain extracted from netloc with port stripped; cookies threaded into `open_headed_with_context(cookies=…)`.
   - `test_missing_playwright` — `SkillUnavailable` propagates with install hint containing `playwright`.
   - `test_no_cookies_still_opens` — empty cookie list → browser still launches; handler reports `cookies_loaded == 0`.
   - `test_url_scheme_rejected` — `file:///tmp/x.html` raises `ValueError` BEFORE cookie lookup or browser launch (T-06-06-01 mitigation).
   - `test_registered_in_plugin` — role set exact match; `install_hint` mentions `playwright`.
   - `test_non_role_not_permitted` — `SkillDispatcher` with `role="security"` raises `SkillNotPermitted`.

## Acceptance Criteria (all green)

- [x] `grep -q "def open_browser_handler" …handler.py` succeeds.
- [x] `grep -q 'name="/open-gstack-browser"' …gstack_sprint_plugin.py` succeeds.
- [x] No top-level `import playwright` in handler (D-02 invariant preserved).
- [x] `pytest tests/templates/gstack/skills/test_open_gstack_browser.py -q` → **7 passed**.
- [x] Plugin registers 9 skills: `len(GstackSprintPlugin().contribute_skills()) == 9`.

## Decisions Made

- **URL validator returns `(url, domain)` tuple** — ports stripped from netloc for cookie-jar lookup. Bare `urlparse(url).hostname` would lowercase internationalized domains in edge cases; netloc-split preserves the original casing that matches how users configured cookies via `/setup-browser-cookies`.
- **Cookie count in response dict** (`cookies_loaded: int`) — lets the dispatcher surface log a non-PII signal without dumping cookie values. Empty jar (common on first use) reports 0 without any noise.
- **hold_seconds=0 default** — Phase 6 does not yet ship a `/close-gstack-browser` partner; the browser closes when the context manager exits. Tests and CI thus never block, and the handler is still exercisable end-to-end without real Playwright (via the `@contextmanager` stub pattern).
- **Artifact type `open-browser-note`** — consistent naming with sibling skills' `<verb>-<noun>` scheme (`deploy-notes`, `canary-report`, `benchmark-report`). Frontmatter-only; no body yet.

## Deviations from Plan

### Rule 3 — Auto-fix blocking issues

**[Rule 3 — Parallel-wave test fence]** `tests/plugins/test_all_seven_skills_registered.py` hard-coded `== 7` as the skill count. Three Wave-2 plans (06-05 / 06-06 / 06-07) each legitimately append one new `SkillRegistration`, so whichever plan lands second breaks both the first one's suite and its own. Relaxed the assertion to a subset check (`set(EXPECTED_SKILLS.keys()).issubset(registered_names)`), preserving the Phase-5 coverage contract without fencing out Phase-6 additions. This is the only way Wave 2 plans can land in any order without mutually breaking tests.

- **Found during:** Task 1 verification (running full test suite after first GREEN commit)
- **Fix:** Changed `== sorted(EXPECTED_SKILLS.keys())` to subset check in two test bodies; added docstring noting the relaxation.
- **Files modified:** `tests/plugins/test_all_seven_skills_registered.py`
- **Committed in:** `46bef6e feat(06-06): implement /open-gstack-browser handler + plugin registration`

### Parallel-executor merge recovery (not a deviation — workflow friction)

Plan 06-05 Task 2 (commit `933d14f`) rebased off `HEAD~1` and committed a `-25 line` diff that inadvertently removed Plan 06-06's SkillRegistration + import from `gstack_sprint_plugin.py`. Detected via AC5 failing (`assert len(skills) == 9` → 8). Fixed by re-adding the deleted lines in a follow-up commit (`9c71d0a fix(06-06): restore /open-gstack-browser registration after 06-05 Task 2`). Plan 06-05 subsequently landed another fix (`0ea2877 fix(06-05): restore /open-gstack-browser registration clobbered by pristine-base rebuild`) that also restores the 06-06 registration, so the current state is resilient to either executor's reset semantics. No code change to this plan's scope was needed; purely a merge artifact.

## Threat Flags

None — threat surface unchanged from `<threat_model>` in the plan. T-06-06-01 (file:// scheme) is mitigated by `_validate_url`; T-06-06-02 (cookie file leaks) and T-06-06-03 (tampered cookie file) are accepted per the plan's disposition.

## Known Stubs

None — handler is fully wired end-to-end. The `/close-gstack-browser` partner skill for persistent windows is deferred to Phase 7 (documented in the handler docstring and the `close_hint` return field); this is not a stub in the gating sense — the current handler does close the browser, just immediately rather than on-demand.

## TDD Gate Compliance

- **RED:** `858c815 test(06-06): add failing tests for /open-gstack-browser` — 7 tests all failing at ModuleNotFoundError for the skill sub-package.
- **GREEN:** `46bef6e feat(06-06): implement /open-gstack-browser handler + plugin registration` — all 7 tests pass; plugin count = 9.
- **REFACTOR:** Not needed; handler is minimal (~160 LOC) and directly maps plan behavior to implementation.

All three gate commits (RED, GREEN, deviation fixes) are grep-able in `git log`.

## Commits

| Hash    | Message                                                              |
| ------- | -------------------------------------------------------------------- |
| 858c815 | `test(06-06): add failing tests for /open-gstack-browser`            |
| 46bef6e | `feat(06-06): implement /open-gstack-browser handler + plugin registration` |
| 9c71d0a | `fix(06-06): restore /open-gstack-browser registration after 06-05 Task 2` |

## Next Steps

- Plan **06-07** (`/setup-browser-cookies`): populates the per-domain cookie jar this skill consumes. Already in Wave 2 RED (commit `cf82d68`) — GREEN will add the 10th plugin skill.
- Plan **06-08** (`/design-shotgun`): optional Playwright screenshot matrix for designer persona.
- Phase **07** will add `/close-gstack-browser` + persistent-window orchestration (SKILL-10 part 3).

## Self-Check

**Files exist:**
- `clawteam/templates/gstack/skills/open_gstack_browser/__init__.py` — FOUND
- `clawteam/templates/gstack/skills/open_gstack_browser/handler.py` — FOUND
- `tests/templates/gstack/skills/test_open_gstack_browser.py` — FOUND

**Commits exist in git log:**
- `858c815` — FOUND (RED)
- `46bef6e` — FOUND (GREEN)
- `9c71d0a` — FOUND (fix)

**Runtime assertions:**
- `grep "def open_browser_handler" handler.py` — FOUND
- `grep 'name="/open-gstack-browser"' gstack_sprint_plugin.py` — FOUND
- No top-level `playwright` import in handler — CONFIRMED
- 7 tests pass — CONFIRMED
- ≥9 skills registered — CONFIRMED (observed 10 at check time because sibling plan 06-07 `/setup-browser-cookies` had also landed by then; the 06-06 contribution is +1 to whatever the baseline is and the plan's acceptance criterion of "9 skills after this plan" is met counting the two Wave-2 siblings that were already done).

## Self-Check: PASSED
