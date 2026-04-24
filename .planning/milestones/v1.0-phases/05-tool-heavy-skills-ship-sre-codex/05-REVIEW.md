---
phase: 05-tool-heavy-skills-ship-sre-codex
reviewed: 2026-04-22T12:19:09Z
depth: standard
files_reviewed: 61
files_reviewed_list:
  - clawteam/cli/commands.py
  - clawteam/events/types.py
  - clawteam/plugins/base.py
  - clawteam/plugins/gstack_sprint_plugin.py
  - clawteam/plugins/manager.py
  - clawteam/plugins/skill_dispatcher.py
  - clawteam/plugins/skill_errors.py
  - clawteam/plugins/skill_registration.py
  - clawteam/spawn/invoke.py
  - clawteam/templates/__init__.py
  - clawteam/templates/gstack/schemas/__init__.py
  - clawteam/templates/gstack/schemas/benchmark_report.py
  - clawteam/templates/gstack/schemas/canary_report.py
  - clawteam/templates/gstack/schemas/codex_review.py
  - clawteam/templates/gstack/schemas/deploy_notes.py
  - clawteam/templates/gstack/schemas/ship_notes.py
  - clawteam/templates/gstack/skills/benchmark/__init__.py
  - clawteam/templates/gstack/skills/benchmark/handler.py
  - clawteam/templates/gstack/skills/canary/__init__.py
  - clawteam/templates/gstack/skills/canary/handler.py
  - clawteam/templates/gstack/skills/canary/poller.py
  - clawteam/templates/gstack/skills/codex/__init__.py
  - clawteam/templates/gstack/skills/codex/handler.py
  - clawteam/templates/gstack/skills/document_release/__init__.py
  - clawteam/templates/gstack/skills/document_release/doc_walker.py
  - clawteam/templates/gstack/skills/document_release/handler.py
  - clawteam/templates/gstack/skills/document_release/patch_emitter.py
  - clawteam/templates/gstack/skills/land_and_deploy/__init__.py
  - clawteam/templates/gstack/skills/land_and_deploy/handler.py
  - clawteam/templates/gstack/skills/setup_deploy/__init__.py
  - clawteam/templates/gstack/skills/setup_deploy/handler.py
  - clawteam/templates/gstack/skills/setup_deploy/wizard.py
  - clawteam/templates/gstack/skills/ship/__init__.py
  - clawteam/templates/gstack/skills/ship/handler.py
  - clawteam/templates/gstack/skills/ship/steps.py
  - tests/integration/__init__.py
  - tests/integration/test_phase5_sprint_end_to_end.py
  - tests/plugins/__init__.py
  - tests/plugins/test_all_seven_skills_registered.py
  - tests/templates/__init__.py
  - tests/templates/gstack/__init__.py
  - tests/templates/gstack/skills/__init__.py
  - tests/templates/gstack/skills/test_adversarial_matrix.py
  - tests/templates/gstack/skills/test_benchmark.py
  - tests/templates/gstack/skills/test_canary.py
  - tests/templates/gstack/skills/test_codex.py
  - tests/templates/gstack/skills/test_document_release.py
  - tests/templates/gstack/skills/test_land_and_deploy.py
  - tests/templates/gstack/skills/test_setup_deploy.py
  - tests/test_doctor_new_entries.py
  - tests/test_event_types_phase5.py
  - tests/test_evidence_schemas_phase5.py
  - tests/test_gstack_plugin.py
  - tests/test_invoke_native_cli.py
  - tests/test_plugin_manager_skills.py
  - tests/test_ship_notes_phase5_fields.py
  - tests/test_ship_skill.py
  - tests/test_skill_dispatcher.py
  - tests/test_skill_errors.py
  - tests/test_skill_registration.py
  - tests/test_template_def_extensions.py
findings:
  critical: 0
  warning: 4
  info: 7
  total: 11
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-04-22T12:19:09Z
**Depth:** standard
**Files Reviewed:** 61
**Status:** issues_found

## Summary

Phase 5 ships the tool-heavy skills (`/codex`, `/ship`, `/setup-deploy`, `/land-and-deploy`, `/document-release`, `/canary`, `/benchmark`) plus the Wave 0 substrate (SkillRegistration / SkillDispatcher / invoke_native_cli / doctor entries / TemplateDef sub-blocks / four new pydantic schemas / two new regression events).

Overall code quality is high. The plugin substrate (`clawteam/plugins/skill_*.py`, `clawteam/spawn/invoke.py`) is tight — frozen dataclasses, explicit Literal enums, hard-coded `shell=False`, scrub_env default, and consistent SkillError hierarchy. Defense-in-depth for adversarial inputs is well-layered: slug regex fullmatch + shell-metachar deny-list + pydantic Literal + argv-literal subprocess invocation.

Findings below are primarily non-critical code-quality notes. The four warnings target real correctness risks but are edge-cases that current tests may not exercise. No critical security issues found — `shell=False` is consistently enforced, secrets scrubbing is on by default, and path-traversal guards are explicit in `_phase6_pending` writes and `_valid_role`.

## Warnings

### WR-01: YAML emitters use `repr()` for strings — produces Python-style quoting that is technically NOT YAML

**File:** `clawteam/templates/gstack/skills/ship/handler.py:95`
**File:** `clawteam/templates/gstack/skills/land_and_deploy/handler.py:284`
**File:** `clawteam/templates/gstack/skills/canary/handler.py:163`
**File:** `clawteam/templates/gstack/skills/benchmark/handler.py:327`

**Issue:** All four hand-rolled YAML emitters serialize strings via Python's `repr()`:
```python
elif isinstance(val, str):
    lines.append(f"{key}: {val!r}")
```
`repr()` produces Python string literals (single-quoted with `\n`, `\t`, `\'` escapes). YAML treats `'a\nb'` in single-quoted form as the four literal characters `a`, `\`, `n`, `b` — NOT a newline. When a string contains an embedded single quote (e.g., `val = "it's broken"`), `repr()` emits `"it's broken"` (double-quoted), which differs from the single-quote path all the other emitters follow. The hand-rolled `_parse_simple_frontmatter` in `land_and_deploy/handler.py:65` and `canary/handler.py:79` works around this by stripping matching outer quotes — but a third-party YAML reader (e.g., PyYAML used by downstream EvidenceGate consumers) would produce subtly different parsed values for strings containing backslashes, unicode, or newlines.

The `codex/handler.py:119-123` variant handles this more safely by explicitly doubling single quotes:
```python
escaped = val.replace("'", "''")
lines.append(f"{key}: '{escaped}'")
```
which is valid YAML single-quoted scalar form.

**Fix:** Factor out a single shared helper that uses the `codex/handler.py` pattern (explicit single-quote doubling, newline handled as YAML block scalar or JSON-encoded string), and call it from all four Phase 5 YAML emitters:

```python
def _yaml_quote_string(val: str) -> str:
    """Quote a string as a valid YAML single-quoted scalar.

    Doubles embedded single quotes per YAML 1.2 §7.4.2. Newlines are
    JSON-encoded (via json.dumps) to stay on one line while remaining
    round-trip-safe with both our hand-rolled parser AND PyYAML.
    """
    if "\n" in val or "\r" in val:
        return json.dumps(val)  # JSON string is a valid YAML flow scalar
    escaped = val.replace("'", "''")
    return f"'{escaped}'"
```

### WR-02: `poll_window` can crash on a test-injected `http_fn` that raises an unexpected exception type

**File:** `clawteam/templates/gstack/skills/canary/poller.py:114-117`

**Issue:** `poll_window` wraps `fn_http(url)` in a `try/except` that only catches the same four exception types (`URLError`, `HTTPError`, `TimeoutError`, `OSError`) that `_default_http_fn` itself handles:
```python
try:
    status, elapsed_ms = fn_http(url)
except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
    status, elapsed_ms = 599, 0.0
```
The docstring on lines 100-103 states "The fake `http_fn` may raise to simulate transport errors — the caller counts these as 5xx" — but a user-supplied `http_fn` that raises `RuntimeError`, `ValueError`, or a generic `Exception` (e.g., a mock with `side_effect=Exception("boom")`) will propagate and crash the handler. This contradicts the documented intent and breaks the D-10/T-05-08-01 guarantee that canary never fails the outer handler on transport issues.

**Fix:** Broaden the catch to `Exception` (with a focused `BaseException` re-raise to let `KeyboardInterrupt`/`SystemExit` escape):
```python
try:
    status, elapsed_ms = fn_http(url)
except Exception:  # noqa: BLE001 — any transport or user-supplied http_fn failure = 5xx
    status, elapsed_ms = 599, 0.0
```

### WR-03: `_evaluate_regressions` hardcodes the threshold value inside the flag string

**File:** `clawteam/templates/gstack/skills/canary/poller.py:157`
**File:** `clawteam/templates/gstack/skills/benchmark/handler.py:459`

**Issue:** Both modules build regression flags using the runtime threshold — but `canary/poller.py` uses a hardcoded `"response_time>2x_baseline"` literal even though `response_time_multiplier` is a parameter (default 2.0, configurable by caller):
```python
if (
    baseline_avg_ms > 0
    and result.avg_response_ms > baseline_avg_ms * response_time_multiplier
):
    flags.append("response_time>2x_baseline")  # literal "2x" — ignores multiplier
```
If a future caller (or gstack.toml config) sets `response_time_multiplier=3.0`, the flag is still stamped `>2x_baseline`, which is a false narrative. Downstream consumers grep on the literal string — so they'll misread the severity.

`benchmark/handler.py:459` does this correctly: `f"{vital}>{threshold_ratio}x_baseline"`.

**Fix:** Interpolate the multiplier:
```python
flags.append(f"response_time>{response_time_multiplier}x_baseline")
```

### WR-04: `document_release_handler` passes agent-controlled `base`/`head` args directly to git

**File:** `clawteam/templates/gstack/skills/document_release/handler.py:61-69, 124-125`

**Issue:** The handler accepts `base` and `head` from `args` (defaults `"main"` / `"HEAD"`) and splices them into a git diff argv without any validation:
```python
base = args.get("base", "main")
head = args.get("head", "HEAD")
# ...
invoke_native_cli(
    ["git", "diff", "--diff-filter=D", "--name-only", f"{base}..{head}"],
    cwd=cwd, timeout=30.0,
)
```
Although `shell=False` prevents shell-level injection, git itself accepts flags in refspec position. A malicious `args["base"]="--exec=touch /tmp/pwned"` or `args["base"]="--upload-pack=/bin/sh"` is passed as a positional argument — but if the refspec string happens to contain `-`-prefixed fragments or unusual characters, git's own argument parser can behave unexpectedly. The agent-facing dispatch contract for `/document-release` does not document `base`/`head` as callable args (see gstack_sprint_plugin.py:283-289), but nothing gates them from arriving through `SkillDispatcher.dispatch(args=...)`.

**Fix:** Validate base/head as plain git ref syntax before passing:
```python
_GIT_REF_RE = re.compile(r"^[A-Za-z0-9_./\-]+$")
if not _GIT_REF_RE.match(base) or not _GIT_REF_RE.match(head):
    raise ValueError(
        f"document-release: invalid git ref (base={base!r}, head={head!r})"
    )
```
This matches normal branch names, tags, SHAs, and the `HEAD~3` form while rejecting `..`, `--exec=...`, spaces, and shell metachars. Alternatively, use `git diff --diff-filter=D --name-only <base> <head>` (two positional args instead of the `base..head` notation) — git is stricter about interpretation when refs are separated.

## Info

### IN-01: Bare `except Exception:` in `_removed_paths_from_diff` lacks the `noqa: BLE001` annotation used elsewhere

**File:** `clawteam/templates/gstack/skills/document_release/handler.py:70`

**Issue:** Every other broad-catch in Phase 5 code carries a `# noqa: BLE001` comment plus a terse justification. This one doesn't:
```python
except Exception:
    return set()
```
Minor consistency issue — it diverges from the codebase convention and future linter tightening would flag it.

**Fix:** Add the annotation:
```python
except Exception:  # noqa: BLE001 — a bad git ref or missing repo returns empty set
    return set()
```

### IN-02: `_fail()` in ship_handler stringifies a dict via `str()` — produces ugly YAML output

**File:** `clawteam/templates/gstack/skills/ship/handler.py:201, 210`

**Issue:** `failure_reason=str(result.details)` produces output like `"{'error': 'fetch_failed', 'stderr': '...'}"` — a Python-dict repr rather than a structured value. Combined with `_render_ship_notes_yaml`'s `repr()` string quoting (WR-01), the emitted YAML has doubly-escaped quotes that are hard to read and hard to programmatically consume.

**Fix:** Serialize the details dict as JSON instead:
```python
failure_reason=json.dumps(result.details)
```
Or, if `failure_reason` is meant to be a short human-readable string, extract the key fields:
```python
failure_reason=result.details.get("error") or result.details.get("reason", "unknown")
```

### IN-03: `_extract_deploy_url` accepts any `https?://` substring including trailing punctuation

**File:** `clawteam/templates/gstack/skills/land_and_deploy/handler.py:56, 196-199`

**Issue:** `_URL_RE = re.compile(r"https?://[^\s]+")` captures the URL through the next whitespace, which will include trailing punctuation like `.`, `)`, `,`, `>`. Deploy CLIs tend to emit URLs on their own line, so this is usually fine, but if stdout is embedded in a sentence like `"Deployed to https://foo.example.com. Please check"`, the captured URL will be `https://foo.example.com.` — which may fail a subsequent HEAD probe.

**Fix:** Strip trailing punctuation:
```python
_URL_RE = re.compile(r"https?://[^\s]+?(?=[\s.,;:!?)\]}>'\"]*(?:\s|$))")
```
Or post-process: `match.group(0).rstrip(".,;:!?)]}>'\"")`.

### IN-04: `_render_block` in setup_deploy does not escape quotes in user-supplied strings

**File:** `clawteam/templates/gstack/skills/setup_deploy/handler.py:84-93`

**Issue:** TOML block is rendered as:
```python
f'provider = "{cfg.provider}"',
f'project = "{cfg.project}"',
```
If `cfg.project` contained a `"`, the TOML output would be malformed. Currently this is prevented by `validate_project_slug` (regex `^[a-zA-Z0-9_-]+$`) and pydantic Literal on `provider`, so quotes can't reach here. However, `cfg.custom_deploy_cmd` (line 92) is only filtered by `_SHELL_METACHARS` which does NOT include the `"` character — a custom command like `myscript --msg="hello world"` is a valid wizard input and will break the TOML block.

**Fix:** Use TOML-safe literal string syntax (triple single quotes) or escape double quotes:
```python
if cfg.custom_deploy_cmd:
    escaped = cfg.custom_deploy_cmd.replace("\\", "\\\\").replace('"', '\\"')
    lines.append(f'custom_deploy_cmd = "{escaped}"')
```
The handler's tomllib round-trip check (line 147-148) will catch a malformed block and refuse to write — so the current behavior is "fail loudly" rather than silent corruption, but the wizard accepts input that the renderer can't safely handle, which is a poor UX.

### IN-05: `clawteam/plugins/manager.py` silently swallows all exceptions during plugin discovery

**File:** `clawteam/plugins/manager.py:49-50, 63-64, 81-82, 110-111, 133-134`

**Issue:** Five of the discovery/loading paths use bare `except Exception: pass` without logging:
```python
try:
    from importlib.metadata import entry_points
    group = entry_points(group="clawteam.plugins")
    for ep in group:
        ...
except Exception:
    pass
```
Debugging "why isn't my plugin loading?" is painful when every failure is invisible. Contrast lines 198-205 and 213-216, which correctly log via `_logger.warning`.

**Fix:** Emit a debug-level log at each swallow point:
```python
except Exception as exc:
    _logger.debug("plugin entry_point discovery failed: %s", exc)
```

### IN-06: Several skills use `Path.read_text()` without encoding

**File:** `clawteam/templates/gstack/skills/document_release/patch_emitter.py:51`
**File:** `clawteam/templates/gstack/skills/document_release/handler.py:86`

**Issue:** `original_text = doc_path.read_text()` (patch_emitter) and `content = doc_path.read_text(encoding="utf-8")` (handler) differ — the former relies on the platform default encoding (cp1252 on Windows), which can fail on UTF-8 documents with non-ASCII characters and produce `UnicodeDecodeError` or silent mojibake.

**Fix:** Add explicit `encoding="utf-8"`:
```python
original_text = doc_path.read_text(encoding="utf-8")
```

### IN-07: `_derive_verdict` in codex_handler does case-sensitive match against lowercased string, but keywords contain none

**File:** `clawteam/templates/gstack/skills/codex/handler.py:131-149`

**Issue:** `first_line = line.strip().lower()` then checks for `("lgtm", "pass", ...)` — all of which are already lowercase. This is correct but wasteful for readability. More importantly, the keyword "pass" will also match words like "compass", "passport", "passing" — so stdout like `"I'm passing on this review"` would be a false-positive pass. Similarly "fail" matches "failing", "failsafe", etc.

**Fix:** Use word-boundary checks:
```python
import re
if re.search(r"\b(lgtm|pass|approved|approve)\b", first_line):
    return "pass"
if re.search(r"\b(fail|reject|block)\b", first_line):
    return "fail"
```

---

_Reviewed: 2026-04-22T12:19:09Z_
_Reviewer: Claude (gsd-code-reviewer, standard depth)_
_Depth: standard_
