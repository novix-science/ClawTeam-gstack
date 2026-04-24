---
phase: 06-browser-skills-design-pipeline-team-memory
plan: 05
subsystem: browser-skill
tags: [skill-browse, browser, playwright, url-allowlist, feature-detection]

requires:
  - phase: 06-01
    provides: "playwright_available feature-detection probe (clawteam.browser)"
  - phase: 06-04
    provides: "navigate_and_screenshot + action_script adapter (clawteam.browser.adapter, lazy Playwright)"

provides:
  - "/browse skill — general-purpose URL + optional action-script navigation for engineer/qa/dx-lead"
  - "browse-result.md artifact shape with dom_hash + http_status + screenshot_path frontmatter"
  - "URL scheme allow-list (http/https only) as a reusable security pattern — rejects file:// / javascript: / data: BEFORE any browser launch"
  - "browse_handler wiring through GstackSprintPlugin.contribute_skills (8th registration — first browser-skill in the plugin)"

affects: [06-06, 06-07, 06-12]  # open-gstack-browser, setup-browser-cookies, integration test

tech-stack:
  added: []
  patterns:
    - "URL allow-list validation BEFORE adapter invocation (T-06-05-01 mitigation pattern — reusable by 06-06 /open-gstack-browser)"
    - "Skill handler delegates ALL Playwright work to clawteam.browser adapter (D-02 invariant; no top-level playwright import in skill module)"
    - "Content-derived screenshot filename (sha256[:8]) for idempotent writes"
    - "Hand-rolled YAML frontmatter emitter (matches /codex /canary pattern — no pyyaml dep)"

key-files:
  created:
    - clawteam/templates/gstack/skills/browse/__init__.py
    - clawteam/templates/gstack/skills/browse/handler.py
    - tests/templates/gstack/skills/test_browse.py
  modified:
    - clawteam/plugins/gstack_sprint_plugin.py

key-decisions:
  - "URL scheme allow-list at skill boundary: validates BEFORE any browser call (adapter could also validate but pushing it up to the skill makes the security intent grep-able and prevents an accidental bypass if adapter is ever invoked from elsewhere)."
  - "Designer role INTENTIONALLY excluded from /browse — designers get /open-gstack-browser (headed, 06-06) where they can visually inspect rather than a headless navigation that only returns hash+status (T-06-05-03 trust-boundary)."
  - "action_script path sets dom_hash='n/a' because actions may mutate DOM non-deterministically; screenshot bytes still captured when actions include a screenshot step."
  - "Screenshot filename = 'browse-screenshot-<sha8>.png' co-located in sprint_dir — content-addressed so repeated runs are idempotent."

patterns-established:
  - "Skill handler deviation Rule-3 pattern: when parallel-wave executors touch a shared plugin file, use an atomic-write + immediate-commit pattern to minimize stomping windows (learned the hard way during Task 2)."
  - "Frontmatter_path fields are always RELATIVE to sprint_dir (tested explicitly in test_screenshot_path_relative_to_sprint_dir) — makes artifacts portable across machines."

requirements-completed: [SKILL-10, D-01, D-02, D-16]

duration: 17min
completed: 2026-04-22
---

# Phase 6 Plan 06-05: /browse Skill Summary

**First browser-skill in the gstack plugin: URL + optional actions navigation with strict http(s) allow-list, delegating all Playwright work to the lazy-import adapter from 06-04.**

## Performance

- **Duration:** ~17 min
- **Started:** 2026-04-22T11:25:53Z
- **Completed:** 2026-04-22T11:43:00Z (approx)
- **Tasks:** 2/2 (both TDD)
- **Files modified:** 4 (3 created + 1 modified)

## Accomplishments

- `/browse` skill handler implemented with URL allow-list, artifact write, and co-located PNG screenshot — 7 handler tests (happy path, missing Playwright, three rejected schemes, action_script dispatch, relative path) all green.
- Registered `/browse` in `GstackSprintPlugin.contribute_skills()` as the 8th entry (engineer/qa/dx-lead roles; tool_available = `playwright_available` lazy probe) — 3 plugin tests (registration, designer-not-permitted, unavailable-dispatch) all green.
- D-02 invariant preserved: no top-level playwright import in the handler module — verified by the acceptance-criteria grep (`^(import|from) playwright` returns empty).

## Task Commits

Each task was committed atomically (TDD RED → GREEN cycle):

1. **Task 1 RED: failing tests** — `6202171` (test: 10 failing tests for /browse handler + plugin wiring)
2. **Task 1 GREEN: handler + sub-package** — `ddfd1e2` (feat: browse_handler + __init__.py; 7/7 handler tests pass)
3. **Task 2 GREEN: plugin registration** — `933d14f` (feat: SkillRegistration(name="/browse") appended; 10/10 tests pass, 8 skills total)
4. **Task 2 fix: restore 06-06 register after pristine-base rebuild** — `0ea2877` (fix: ensure /open-gstack-browser stays registered; Rule 1 bug fix)

No separate REFACTOR commit — implementation landed clean at GREEN.

## Files Created/Modified

- **clawteam/templates/gstack/skills/browse/__init__.py** (NEW, 10 LOC) — Sub-package public API; re-exports `browse_handler`.
- **clawteam/templates/gstack/skills/browse/handler.py** (NEW, 185 LOC) — Handler, URL allow-list (`_validate_url`), artifact writer (`_write_artifact` + `_format_fm_value`), delegates to `clawteam.browser.navigate_and_screenshot` / `action_script`.
- **tests/templates/gstack/skills/test_browse.py** (NEW, 315 LOC) — 10 tests: 7 handler (happy path, missing Playwright, 3 scheme rejections, action_script dispatch, relative screenshot path) + 3 plugin (registration, designer not permitted, unavailable via dispatcher).
- **clawteam/plugins/gstack_sprint_plugin.py** (MODIFIED, +25 LOC net) — Added import of `browse_handler` + `playwright_available`, appended 8th `SkillRegistration`.

## Decisions Made

See `key-decisions` in the frontmatter above. Notably:

- **URL allow-list at skill boundary, not adapter boundary.** Pushing it up to the skill handler means a future caller that routes through some other path (not going through `/browse`) can't bypass the check. Also keeps the security intent grep-visible (`_ALLOWED_SCHEMES` frozenset).
- **Designer role intentionally excluded** — /browse returns only dom_hash + http_status + PNG; designers need headed visual inspection, which is 06-06's /open-gstack-browser. Enforced via `frozenset({"engineer","qa","dx-lead"})`.
- **Content-derived screenshot filename** — `browse-screenshot-<sha256[:8]>.png` — repeated navigations of the same page produce the same filename (idempotent writes, no stale screenshots piling up).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Accidentally removed 06-06's /open-gstack-browser registration during Task 2 atomic rewrite.**
- **Found during:** Task 2 (after committing the /browse registration).
- **Issue:** Wave-2 parallel executors (06-05, 06-06, 06-07) were all touching `clawteam/plugins/gstack_sprint_plugin.py` concurrently. My Task 2 commit rebuilt the plugin from a pristine HEAD base that predated 06-06's commit `46bef6e`, which accidentally deleted 06-06's import + SkillRegistration for /open-gstack-browser.
- **Fix:** Compensating commit `0ea2877` restored the plugin to the post-06-06 state + my /browse entry (9 skills total). 06-06 executor had independently committed `9c71d0a` with the same fix between my bad commit and my compensating commit, so my fix became a 1-line cleanup (trailing blank line).
- **Files modified:** `clawteam/plugins/gstack_sprint_plugin.py`
- **Verification:** `len(GstackSprintPlugin().contribute_skills()) == 9` (7 Phase 5 + /browse + /open-gstack-browser).
- **Committed in:** `0ea2877` (fix commit).

**2. [Rule 3 - Blocking] Parallel-wave file churn required adopting an atomic-write pattern.**
- **Found during:** Task 2, multiple attempts.
- **Issue:** Three concurrent executors (06-05, 06-06, 06-07) were editing the plugin file. Traditional `Edit` tool calls and `git add` were being stomped by other workers' writes between my edit and my commit.
- **Fix:** Switched to a Python-script-based atomic-write: read pristine HEAD → apply only 06-05 hunks → `os.replace` atomically → immediately `git add + commit` in a single Bash invocation (minimizes the stomping window). This landed the /browse registration cleanly.
- **Commit:** `933d14f`

## Authentication Gates

None — /browse does not touch external auth.

## Threat Model Compliance

All three plan threats addressed:

| Threat ID | Disposition | Implemented |
|-----------|-------------|-------------|
| T-06-05-01 (file:// / javascript: / data: info-disclosure) | mitigate | `_validate_url` frozenset allow-list, tested by test_url_scheme_rejected_{file,javascript,data} — 3 tests. |
| T-06-05-02 (hostile-redirect DoS) | accept | `timeout_seconds` (default 30) from adapter bounds wall clock; no plan action required. |
| T-06-05-03 (non-engineer/qa/dx-lead tampering) | mitigate | `SkillRegistration.roles = frozenset({"engineer","qa","dx-lead"})`, tested by test_designer_not_permitted. |

## Verification Commands (Plan §verification)

```bash
# 1. All /browse + plugin tests green
pytest tests/templates/gstack/skills/test_browse.py tests/plugins/ -q
# → 15 passed (10 /browse + 5 plugin)

# 2. Plugin registration surface
python -c "from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin; \
           print(len(GstackSprintPlugin().contribute_skills()), 'skills')"
# → 9 skills (7 Phase 5 + /browse + /open-gstack-browser from co-wave 06-06)

# 3. D-02 invariant — no top-level playwright import in handler
grep -E "^(import|from) playwright" clawteam/templates/gstack/skills/browse/handler.py
# → (nothing)
```

## Self-Check: PASSED

Files verified present on disk:
- `clawteam/templates/gstack/skills/browse/__init__.py` — FOUND
- `clawteam/templates/gstack/skills/browse/handler.py` — FOUND
- `tests/templates/gstack/skills/test_browse.py` — FOUND
- `clawteam/plugins/gstack_sprint_plugin.py` — FOUND (modified)
- `.planning/phases/06-browser-skills-design-pipeline-team-memory/06-05-SUMMARY.md` — FOUND

Commits verified in git log:
- `6202171` (test RED) — FOUND
- `ddfd1e2` (Task 1 GREEN) — FOUND
- `933d14f` (Task 2 GREEN) — FOUND
- `0ea2877` (Task 2 fix: restore /open-gstack-browser) — FOUND
