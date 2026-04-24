---
phase: 06-browser-skills-design-pipeline-team-memory
reviewed: 2026-04-22T00:00:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - clawteam/browser/__init__.py
  - clawteam/browser/adapter.py
  - clawteam/browser/cookies.py
  - clawteam/browser/session.py
  - clawteam/cli/commands.py
  - clawteam/events/types.py
  - clawteam/memory/__init__.py
  - clawteam/memory/backfill.py
  - clawteam/memory/conflict.py
  - clawteam/memory/decay.py
  - clawteam/memory/entry.py
  - clawteam/memory/high_impact_gate.py
  - clawteam/memory/search.py
  - clawteam/memory/store.py
  - clawteam/plugins/gstack_sprint_plugin.py
  - clawteam/templates/__init__.py
  - clawteam/templates/gstack/skills/browse/__init__.py
  - clawteam/templates/gstack/skills/browse/handler.py
  - clawteam/templates/gstack/skills/design_html/__init__.py
  - clawteam/templates/gstack/skills/design_html/framework_detect.py
  - clawteam/templates/gstack/skills/design_html/handler.py
  - clawteam/templates/gstack/skills/design_shotgun/__init__.py
  - clawteam/templates/gstack/skills/design_shotgun/handler.py
  - clawteam/templates/gstack/skills/design_shotgun/state.py
  - clawteam/templates/gstack/skills/learn/__init__.py
  - clawteam/templates/gstack/skills/learn/handler.py
  - clawteam/templates/gstack/skills/open_gstack_browser/__init__.py
  - clawteam/templates/gstack/skills/open_gstack_browser/handler.py
  - clawteam/templates/gstack/skills/setup_browser_cookies/__init__.py
  - clawteam/templates/gstack/skills/setup_browser_cookies/handler.py
  - clawteam/templates/gstack/skills/setup_browser_cookies/wizard.py
  - pyproject.toml
  - tests/fixtures/design_shotgun/picked.json
  - tests/fixtures/design_shotgun/variant-1/index.html
findings:
  critical: 0
  warning: 5
  info: 6
  total: 11
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-04-22T00:00:00Z
**Depth:** standard
**Files Reviewed:** 34 source files (tests and HTML/JSON fixtures excluded from analysis per agent rules — 30 test files spot-checked only for critical correctness issues)
**Status:** issues_found

## Summary

Phase 6 ships three browser skills (`/browse`, `/open-gstack-browser`, `/setup-browser-cookies`), two design skills (`/design-shotgun`, `/design-html`), and the team-memory substrate (`/learn`) plus three new `HarnessEvent` types. The code is well-structured, extensively documented, follows the Playwright lazy-import invariant (D-02) consistently, and applies careful path-traversal + URL allow-list defenses at skill boundaries.

Strengths noted:
- Browser substrate centralizes lazy Playwright import in `adapter._import_sync_playwright()` — `session.py` reuses it instead of duplicating, keeping D-02 audit surface to one line.
- Cookie domain validation uses a layered fail-fast (type check → path-traversal substring block → DNS regex fullmatch), with the same shape in `browser/cookies.py` and `setup_browser_cookies/wizard.py`.
- URL allow-list (`http`/`https` only) enforced before any browser launch in all three browser skill handlers.
- Memory store enforces `validate_identifier` + `ensure_within_root` for team + role path components.
- Bucket path in `TeamMemoryStore.bucket_path` re-validates month-bucket regex before filesystem access.
- Regex user input in `memory/search.py` is `re.escape`-d — ReDoS surface removed.
- Pydantic validators enforce scope/role coupling, tag format, and confidence bounds at construction time.

No Critical issues found. Five Warnings concern input validation gaps (primarily in `/design-html`) and overly-broad exception handling; six Info items cover code-quality polish.

## Warnings

### WR-01: `/design-html` does not validate `component_name` — filesystem path traversal possible

**File:** `clawteam/templates/gstack/skills/design_html/handler.py:66, 86, 102, 244`
**Issue:** `component_name` comes from `args["component_name"]` (default `"Hero"`) and is interpolated directly into an output filename via `src_dir / f"{component_name}.jsx"` (and the `.svelte` / `.vue` equivalents). A caller passing `component_name="../../etc/passwd"` or `component_name="..\\..\\conf"` would cause the emitted file to land outside `src_dir`. Although role gating restricts this skill to designers, per defense-in-depth (the same principle applied in `clawteam/browser/cookies._validate_domain`) this input must be constrained.
**Fix:**
```python
_COMPONENT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")

def _validate_component_name(name: str) -> str:
    if not isinstance(name, str) or not _COMPONENT_NAME_RE.fullmatch(name):
        raise ValueError(
            f"component_name must match [A-Za-z][A-Za-z0-9_]* (got {name!r})"
        )
    return name
```
Call from `design_html_handler` immediately after resolving `component_name`, and reject before any `_emit_*` call.

### WR-02: `/design-html` does not enforce that `project_root` / `mockup_html_path` stay within allowed roots

**File:** `clawteam/templates/gstack/skills/design_html/handler.py:234-241`
**Issue:** Both paths are taken verbatim from `args` with only an `is_file()` existence check on the mockup. `project_root` is then written into with `atomic_write_text` (React/Svelte/Vue emit inside `project_root / "src"`, plain emits `index.html` + `styles.css` + `app.js` at `project_root`). A caller can pass `project_root="/etc"` or `mockup_html_path="/etc/shadow"` and get arbitrary-path reads (from mockup) plus arbitrary-path writes (to project_root). Paired with role gating this is lower severity than a Critical, but the skill writes to arbitrary disk locations without a containment root.
**Fix:** Document the trust boundary explicitly (skill trusts designer-role callers); OR add a `_resolve_project_root(ctx, args)` helper that requires `project_root` to be within `get_data_dir()` or an explicit `ctx.workspace_root`, calling `ensure_within_root` — consistent with `TeamMemoryStore` treatment of `team_dir`.

### WR-03: Broad `except Exception: pass` in `learn_handler._ensure_backfilled` and three spots in `backfill.py` / `learn/handler.py` silently swallow all failures

**File:** `clawteam/memory/backfill.py:117`, `clawteam/templates/gstack/skills/learn/handler.py:60, 188, 192, 206`
**Issue:** Four `except Exception: pass`/`continue` blocks swallow every exception including `KeyboardInterrupt` side-effects via `BaseException` subclasses that do pass through (acceptable), AND `SystemExit`/`MemoryError` (not captured since they inherit `BaseException`, OK) — but they also swallow programmer errors, misconfiguration, data-dir permission issues, etc. The intent is "backfill/conflict emission is advisory, never block the /learn path" (documented clearly in docstrings), but silent failure means a permanent bug in `detect_conflicts` would never surface in logs.
**Fix:** Keep the broad catch but log the exception so operators can debug without stepping through pdb:
```python
import logging
_LOG = logging.getLogger(__name__)

try:
    backfill_scan(team=team_name, root=get_data_dir())
except Exception as exc:
    _LOG.warning("backfill_scan swallowed exception for team=%s", team_name, exc_info=exc)
```
Apply same pattern to `_emit_conflict_events` catch-alls and `backfill.py:117`.

### WR-04: `_invoke_learn` in CLI catches `(ValueError, Exception)` — the first class is redundant and all programmer errors become exit-1

**File:** `clawteam/cli/commands.py:5721`
**Issue:** `except (ValueError, Exception) as exc` is equivalent to `except Exception as exc` (since `ValueError` is an `Exception` subclass). The redundancy is harmless syntactically but, more importantly, this catches and re-raises ALL exceptions (including `AttributeError`, `TypeError` from a future refactor bug) as `typer.Exit(1)` with only `str(exc)` for forensics. Operators lose traceback when running without `--json`.
**Fix:**
```python
try:
    return learn_handler(_learn_ctx(team), role="cli", args=args)
except ValueError as exc:
    _output({"error": str(exc)}, lambda d: console.print(f"[red]Error:[/red] {d['error']}"))
    raise typer.Exit(code=1)
except Exception as exc:
    _output(
        {"error": f"Unexpected: {type(exc).__name__}: {exc}"},
        lambda d: console.print(f"[red]Unexpected:[/red] {d['error']}"),
    )
    # Re-raise for debuggability in dev; Typer will print traceback
    raise
```

### WR-05: `TeamMemoryStore.list` swallows `MemoryEntry` validation errors with bare `except Exception`

**File:** `clawteam/memory/store.py:189-191`
**Issue:** Invalid entries on disk are silently skipped (`continue`). This is consistent with the `T-06-02-04 malformed line` threat-model posture (and tests verify it), but the too-broad `except Exception` also catches programmer errors (e.g., a future `MemoryEntry` field rename whose Pydantic error looks like a validation error). A poisoned record that triggers a real bug would be indistinguishable from legitimate legacy-data issues.
**Fix:** Narrow to pydantic's `ValidationError`:
```python
from pydantic import ValidationError

try:
    entry = MemoryEntry(**raw)
except ValidationError:
    continue
```
Leaves `TypeError` / `KeyError` as loud failures that indicate a bug rather than bad data.

## Info

### IN-01: `design_html._emit_react` uses `dangerouslySetInnerHTML` with unescaped mockup HTML

**File:** `clawteam/templates/gstack/skills/design_html/handler.py:68-78`
**Issue:** The emitted React component embeds `MOCKUP_HTML` (the raw mockup HTML from disk) and injects it via `dangerouslySetInnerHTML={{ __html: MOCKUP_HTML }}`. The mockup is expected to be designer-controlled (trusted) per the workflow contract, but the generated code has no warning comment in the emitted output. A downstream engineer reviewing `Hero.jsx` might not realize that **runtime** XSS depends on mockup provenance. Note: by D-13 this is a "first-pass skeleton to compile" and refactoring is expected; the docstring notes this already.
**Fix:** Add a `// TODO(security): mockup HTML is injected verbatim via dangerouslySetInnerHTML...` comment line at the top of the emitted React file so the refactoring eng can see the risk at point of use:
```python
content = (
    f"// Auto-emitted by /design-html ({component_name}.jsx)\n"
    f"// Source mockup digest: {digest}\n"
    f"// SECURITY TODO: dangerouslySetInnerHTML below trusts the mockup source.\n"
    f"// Replace with idiomatic JSX before shipping to production.\n"
    ...
)
```

### IN-02: `learn_handler._do_write` returns `high_impact=True` unconditionally when gate fires, and `"impact:high" in entry.tags` as separate key — inconsistent shape

**File:** `clawteam/templates/gstack/skills/learn/handler.py:150-157, 171`
**Issue:** Two paths through `_do_write` return `high_impact`:
- Gate path (line 154): `"high_impact": True` regardless of tag — the gate can fire on non-`impact:high` tags (e.g., `decisions:`).
- Normal path (line 171): `"high_impact": "impact:high" in entry.tags` — only checks one tag.
A caller reading `result["high_impact"]` sees different semantics depending on whether the gate fired. Since the gate branch also carries `"status": "pending_confirmation"` vs `"written"`, the two results are distinguishable, but the semantic overload is subtle.
**Fix:** Either rename the gate-path field to `"gate_reason"` (already present as `"reason"`) and drop `high_impact=True`, OR make both paths compute `high_impact` from the same `check_high_impact(entry)[0]` predicate so semantics match.

### IN-03: `adapter.py navigate_and_screenshot` uses `page.content().encode("utf-8", errors="replace")` — the error handler is load-bearing but undocumented in behavior

**File:** `clawteam/browser/adapter.py:98`
**Issue:** `errors="replace"` silently substitutes `U+FFFD` for bad bytes — produces a stable `dom_hash` but a subtly different hash from the "strict" interpretation. No test covers the replacement path (unlikely to trigger since `page.content()` returns `str` from Playwright and should already be valid UTF-16 surrogate-pair-clean). Left as-is this is a defensive nit but harmless.
**Fix:** Either add a brief docstring note (`dom_hash is stable across encoding anomalies`) or switch to `errors="strict"` and let a truly corrupt DOM raise.

### IN-04: `design_shotgun/handler.py` passes `team_name = getattr(ctx, "team_name", "") or "default"` — silent fall-through

**File:** `clawteam/templates/gstack/skills/design_shotgun/handler.py:293`
**Issue:** If `ctx.team_name` is missing the handler silently constructs a `TeamMemoryStore("default")` — the user's taste observation lands in a wrong (or shared) team bucket. Tests likely use `default` on purpose, but production misconfiguration would silently write cross-team.
**Fix:** Fail loudly when team_name is absent (unless the skill is genuinely team-free; design-shotgun is not — the taste memory has a team scope):
```python
team_name = getattr(ctx, "team_name", "")
if not team_name and action == "pick":
    raise ValueError("ctx.team_name is required for /design-shotgun pick (writes role memory)")
```

### IN-05: Magic numbers in `memory/decay.py` and `memory/search.py` — consider named constants

**File:** `clawteam/memory/decay.py:88, 98, 105-107`, `clawteam/memory/search.py:77`
**Issue:** Several numeric constants (`0.05`, `0.2`, `1.0`, `86400.0`, `30.0`, `0.1`) are inline. Values are documented in docstrings, but a future ratio change needs to hit two files. Existing `_DEFAULT_TTL_BY_TAG` + `_INDEFINITE_DAYS` show the module can handle named constants.
**Fix:** Add `_EXPIRED_DECAY = 0.05`, `_STALE_DECAY = 0.2`, `_FRESH_DECAY = 1.0`, `_SECONDS_PER_DAY = 86400.0`, `_RECENCY_HALFLIFE_DAYS = 30.0`, `_MALFORMED_TIMESTAMP_RECENCY = 0.1` near the `_DEFAULT_TTL_BY_TAG` dict.

### IN-06: `entry.py` `_role_presence_matches_scope` relies on pydantic v2 declaration-order validation

**File:** `clawteam/memory/entry.py:79-87`
**Issue:** The validator reads `info.data.get("scope")` — this is populated only if `scope` was validated BEFORE `role`. Pydantic v2 validates in declaration order by default (scope at line 73 precedes role at line 74), so this works today. If a future refactor reorders fields alphabetically (Python 3.7+ dicts are insertion-ordered but class-body code may change) the validator silently becomes a no-op: `info.data.get("scope")` returns `None`, and neither branch fires.
**Fix:** Use `@model_validator(mode="after")` for cross-field invariants — insensitive to field declaration order:
```python
from pydantic import model_validator

@model_validator(mode="after")
def _check_scope_role(self) -> "MemoryEntry":
    if self.scope == "role" and not self.role:
        raise ValueError("scope='role' requires non-empty role")
    if self.scope == "team" and self.role:
        raise ValueError("scope='team' forbids role attribute")
    return self
```

---

_Reviewed: 2026-04-22T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
