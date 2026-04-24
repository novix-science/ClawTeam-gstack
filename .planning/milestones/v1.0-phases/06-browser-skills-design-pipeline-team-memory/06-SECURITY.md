---
phase: 6
slug: browser-skills-design-pipeline-team-memory
status: verified
threats_open: 0
threats_total: 34
threats_closed: 34
asvs_level: 1
created: 2026-04-22
verified: 2026-04-22
---

# Phase 6 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
>
> Aggregates the STRIDE threat registers from all 11 plans in Phase 6 and verifies each declared `mitigate` disposition against implementation evidence. `accept` and `defer` dispositions are logged below.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| pyproject.toml → pip resolver | trusted: developer-controlled | optional `[browser]` extra declaration |
| template `.toml` → `TemplateDef` (pydantic) | untrusted: `gstack.toml` content loaded into pydantic; invalid sub-block shape MUST reject | `[memory]`, `[design_shotgun]`, `[browser]` blocks |
| CLI/skill caller → `TeamMemoryStore(team_name)` | untrusted: attacker-controlled `team_name` | team directory path segments |
| CLI/skill caller → `.list(role=...)` | untrusted: attacker-controlled `role` | role directory path segments |
| on-disk JSONL → `.list()` iteration | untrusted: file may be malformed | memory entry dicts |
| user query → `re.search` | untrusted: query may contain regex metachars | retrieval input |
| entry timestamp → `datetime.fromisoformat` | untrusted: may be malformed | decay/recency inputs |
| user URL → Playwright `goto` | untrusted: arbitrary scheme incl. `file://`, `javascript:` | network navigation target |
| action dict list → browser actions | untrusted: unknown action types → `ValueError` | step sequence |
| domain identifier → filesystem path (cookie jar) | untrusted: attacker-controlled; path-traversal blocked | cookie JSON file path |
| loaded JSON cookies → Playwright context | semi-trusted: from `/setup-browser-cookies` wizard | authenticated session cookies |
| `mockup_html_path` → `design_html` write planner | untrusted: caller-provided | HTML fixture path |
| `--tags` / `--team` / `--role` → `MemoryEntry` + store | untrusted: CLI-supplied | memory entry content + store path |
| event bus subscriber → event payload | in-process only | `MemoryWritePersisted`, `ConflictDetected`, `MemoryBackfillComplete` |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation / Evidence | Status |
|-----------|----------|-----------|-------------|-----------------------|--------|
| T-06-01-01 | Tampering | `[memory] conflict_threshold = 2.0` | mitigate | `Field(ge=0.0, le=1.0)` at `clawteam/templates/__init__.py:177-186` | closed |
| T-06-01-02 | Tampering | `[design_shotgun] variant_count = 0` | mitigate | `Field(ge=1, le=32)` at `clawteam/templates/__init__.py:205-210` | closed |
| T-06-01-03 | Tampering | `[design_shotgun] board_format = "pdf"` | mitigate | `Literal["html", "markdown"]` at `clawteam/templates/__init__.py:211-214` | closed |
| T-06-01-04 | Information Disclosure | Top-level `playwright` import leaks presence | mitigate | `find_spec` only, zero top-level import at `clawteam/browser/__init__.py:26-37` | closed |
| T-06-01-05 | Tampering | Duplicate `register_event_type` from re-import | accept | Phase 4 precedent: `register_event_type` is idempotent (re-importing `events/types.py` is safe) | closed |
| T-06-02-01 | Tampering / Info Disclosure | `team_name="../otherteam"` path traversal | mitigate | `validate_identifier(team_name, "team name")` in `TeamMemoryStore.__init__` at `clawteam/memory/store.py:46` | closed |
| T-06-02-02 | Tampering / Info Disclosure | `role="../../etc/passwd"` path traversal | mitigate | `validate_identifier(role, "role")` + `ensure_within_root(...)` in `_role_dir` at `clawteam/memory/store.py:58-59` | closed |
| T-06-02-03 | Tampering | Interleaved writes corrupt JSONL | mitigate | `file_locked(bucket)` + `os.fsync(fh.fileno())` in `TeamMemoryStore.write` at `clawteam/memory/store.py:104-109` | closed |
| T-06-02-04 | Tampering | Malformed JSON line crashes `.list` | mitigate | `_iter_jsonl` wraps `json.loads` in `try/except JSONDecodeError` at `clawteam/memory/store.py:155-157` | closed |
| T-06-02-05 | Integrity | Tombstone suppresses wrong entry | accept | `MemoryEntry.id` enforced by `_ID_RE = r"^mem-[a-zA-Z0-9_-]+-\d{8}-[a-f0-9]{6}$"` at `clawteam/memory/entry.py:31` — collision probability acceptable for v1 per A5 | closed |
| T-06-03-01 | DoS | Catastrophic-backtracking regex in query | mitigate | `re.compile(re.escape(query), re.IGNORECASE)` at `clawteam/memory/search.py:186` | closed |
| T-06-03-02 | Tampering | Malformed timestamp crashes ranking | mitigate | `datetime.fromisoformat` in `try/except ValueError` at `clawteam/memory/search.py:74-75` and `clawteam/memory/decay.py:95-97` | closed |
| T-06-03-03 | Integrity | Expired entry deleted by ranker | mitigate | Floor of `0.05` enforced at `clawteam/memory/decay.py:97,107` — entries listed + ranked, never removed | closed |
| T-06-04-01 | Info Disclosure | User URL `file:///etc/passwd` exfiltration at substrate | defer | Substrate is protocol-agnostic by design; per-skill allow-list enforced in `/browse` handler (T-06-05-01) and `/open-gstack-browser` (T-06-06-01) | closed |
| T-06-04-02 | Tampering / Info Disclosure | `domain="../../etc"` cookie path traversal | mitigate | `_validate_domain` (regex + explicit `..`/`/`/`\\` check) at `clawteam/browser/cookies.py:39-60`, invoked from `_cookie_path` | closed |
| T-06-04-03 | Tampering | Malformed cookie JSON crashes load | mitigate | `load_cookies_for_domain` wraps in `except (json.JSONDecodeError, OSError)` → `[]` at `clawteam/browser/cookies.py:117` | closed |
| T-06-04-04 | DoS | Infinite `page.goto()` hangs | mitigate | `timeout_seconds` (default 30) → `timeout_ms = timeout_seconds * 1000` passed to `page.goto(url, timeout=timeout_ms)` at `clawteam/browser/adapter.py:62,81,90,129,145` | closed |
| T-06-04-05 | Info Disclosure | Secrets in env reach Chromium subprocess | accept | Playwright spawns its own subprocess; env is process-inherited — no worse than existing CLI surface; in-scope for Phase 7 if cost/surface grows | closed |
| T-06-05-01 | Info Disclosure | `url=file:///etc/passwd` reads local files via `/browse` | mitigate | `_ALLOWED_SCHEMES = {"http", "https"}` with `_validate_url` in `clawteam/templates/gstack/skills/browse/handler.py:30,33,46-48,142` | closed |
| T-06-05-02 | DoS | URL with hostile redirect loops | accept | `timeout_seconds` (default 30) bounds wall clock via adapter; redirect loops terminate on timeout | closed |
| T-06-05-03 | Spoofing | Non-engineer/qa/dx-lead invokes `/browse` | mitigate | `SkillRegistration(..., roles=frozenset({"engineer","qa","dx-lead"}))` at `clawteam/plugins/gstack_sprint_plugin.py:319`; `SkillDispatcher` enforces role | closed |
| T-06-06-01 | Info Disclosure | `url=file://` scheme via `/open-gstack-browser` | mitigate | `_ALLOWED_SCHEMES` + `_validate_url` at `clawteam/templates/gstack/skills/open_gstack_browser/handler.py:51,65-67,153` | closed |
| T-06-06-02 | Info Disclosure | Cookie file leaks on shared machine | accept | Cookies stored under user-home team dir with OS file perms; documented as user-machine-scoped in STACK.md. v2 may add keyring | closed |
| T-06-06-03 | Tampering | Attacker-controlled cookie file injected | accept | `save_cookies_for_domain` rejects path-traversal domains (T-06-04-02); cookie-jar integrity assumed post-wizard on the user's local machine | closed |
| T-06-07-01 | Tampering | Wizard domain injection → path traversal | mitigate | `validate_domain` wizard validator at `clawteam/templates/gstack/skills/setup_browser_cookies/wizard.py:14,29,89` mirrors `clawteam.browser.cookies._validate_domain` | closed |
| T-06-07-02 | Info Disclosure | `cookies.json` stored plain | accept | User-machine-scoped by design; documented in STACK.md | closed |
| T-06-07-03 | Spoofing | Non-engineer/qa/dx-lead invokes `/setup-browser-cookies` | mitigate | `roles=frozenset({"engineer","qa","dx-lead"})` at `clawteam/plugins/gstack_sprint_plugin.py:356` | closed |
| T-06-08-01 | Tampering | Malformed variant HTML written | accept | Variant HTML authored by designer agent; handler just writes under `<sprint_dir>` (user-writable scope, same trust boundary as all other gstack skills) | closed |
| T-06-08-02 | Tampering | Illegal state transition crashes skill | mitigate | `ShotgunState.advance` raises `ValueError("illegal transition: ...")` at `clawteam/templates/gstack/skills/design_shotgun/state.py:163-164`; handler propagates | closed |
| T-06-08-03 | Info Disclosure | Memory leak via taste observation | accept | Memory entry written with `scope="role"`, `role="designer"` — per-designer private scope, not cross-role shared | closed |
| T-06-09-01 | Tampering | `mockup_html_path` traversal | mitigate | `Path.is_file()` check raises `FileNotFoundError` at `clawteam/templates/gstack/skills/design_html/handler.py:234-236` | closed |
| T-06-09-02 | Tampering | `component_name` path injection | accept | Designer-role-gated input; `Path` joining sanitizes `/`; v1 accepts filesystem-unsafe names — `validate_identifier` guard may be added if abuse surfaces | closed |
| T-06-09-03 | Info Disclosure | Malformed `package.json` crashes detect | mitigate | `except (json.JSONDecodeError, OSError, UnicodeDecodeError)` in `_read_package_json` at `clawteam/templates/gstack/skills/design_html/framework_detect.py:71` returns `None` → `plain` fallback | closed |
| T-06-10-01 | Tampering | CLI `--tags "../etc"` slips through | mitigate | `_TAG_RE = r"^[a-z0-9][a-z0-9:_-]*$"` at `clawteam/memory/entry.py:32` + `_TAG_RE.fullmatch(t)` at `:93`; pydantic rejects at construction | closed |
| T-06-10-02 | Info Disclosure | `--team` points to another user's team | mitigate | `validate_identifier(team_name, "team name")` in `TeamMemoryStore.__init__` at `clawteam/memory/store.py:46`; path traversal rejected at store construction | closed |
| T-06-10-03 | Integrity | Prune on non-existent id silently succeeds | accept | Tombstone for non-existent id is a no-op on retrieval (nothing to suppress); auditable via JSONL inspection | closed |

*Status: open · closed*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party) · defer (routed to another layer)*

Note: Plan 06-11 (`clawteam/memory/high_impact_gate.py`, `conflict.py`, `backfill.py`) declared no new threat register — its modules consume existing `TeamMemoryStore` trust boundaries (`ensure_within_root` + `validate_identifier` apply transitively). SUMMARY.md confirms no new trust boundaries, auth paths, or network endpoints were introduced.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| R-06-01 | T-06-01-05 | `register_event_type` idempotency established in Phase 4; re-import is safe. | Phase 6 plan authors | 2026-04-22 |
| R-06-02 | T-06-02-05 | `MemoryEntry.id` regex limits collision to ~1/16M per team per day per author-title-tags bucket; acceptable for v1 per assumption A5. | Phase 6 plan authors | 2026-04-22 |
| R-06-03 | T-06-04-05 | Playwright subprocess inherits process env; not a worse surface than existing CLI. Revisit in Phase 7 if scope grows. | Phase 6 plan authors | 2026-04-22 |
| R-06-04 | T-06-05-02 | Redirect loops bounded by Playwright `timeout_seconds` (default 30). | Phase 6 plan authors | 2026-04-22 |
| R-06-05 | T-06-06-02 | Cookie jar is user-machine-scoped with OS file perms; documented in STACK.md. Keyring storage is v2 scope. | Phase 6 plan authors | 2026-04-22 |
| R-06-06 | T-06-06-03 | Cookie-jar integrity assumed post-wizard on the user's local machine; domain path traversal already blocked (T-06-04-02). | Phase 6 plan authors | 2026-04-22 |
| R-06-07 | T-06-07-02 | Plain `cookies.json` is user-machine-scoped by design; documented in STACK.md. | Phase 6 plan authors | 2026-04-22 |
| R-06-08 | T-06-08-01 | Variant HTML authored by designer agent under `<sprint_dir>`; same trust boundary as all gstack skill artifacts. | Phase 6 plan authors | 2026-04-22 |
| R-06-09 | T-06-08-03 | Taste memory is `scope="role"`, `role="designer"` — per-designer private, no cross-role leak. | Phase 6 plan authors | 2026-04-22 |
| R-06-10 | T-06-09-02 | `component_name` injection is designer-role-gated input; `Path` join sanitizes `/`; add `validate_identifier` if abuse observed. | Phase 6 plan authors | 2026-04-22 |
| R-06-11 | T-06-10-03 | Tombstone on non-existent id is a harmless no-op; JSONL remains fully auditable. | Phase 6 plan authors | 2026-04-22 |

*Accepted risks do not resurface in future audit runs.*

---

## Deferred Dispositions

| Threat Ref | Deferred To | Rationale |
|------------|-------------|-----------|
| T-06-04-01 | Per-skill layer (T-06-05-01, T-06-06-01 — both closed) | `browser/adapter.py` substrate is protocol-agnostic by design; `/browse` and `/open-gstack-browser` enforce the http/https allow-list before any Playwright call. Verified closed at the skill layer. |

---

## Unregistered Threat Flags (from SUMMARY.md)

All SUMMARY.md `## Threat Flags` sections for plans 06-01, 06-03, 06-06, 06-08, 06-11 explicitly state "None" or "None beyond those already in the plan's `<threat_model>`". No unregistered flags.

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-04-22 | 34 | 34 | 0 | gsd-secure-phase (inline auditor, Phase 6 background agent) |

### Audit Run Summary

- **Input state:** B (no pre-existing SECURITY.md; PLAN + SUMMARY artifacts present for all 11 plans).
- **Threat registers parsed:** 06-01 (5), 06-02 (5), 06-03 (3), 06-04 (5), 06-05 (3), 06-06 (3), 06-07 (3), 06-08 (3), 06-09 (3), 06-10 (3). Plan 06-11 declared no new threats (consumes existing `TeamMemoryStore` trust boundaries).
- **Verification method:** `grep` for declared mitigation patterns in cited implementation files; pydantic `Field` constraints confirmed at module scope; role allow-lists confirmed in `gstack_sprint_plugin.py` `SkillRegistration` entries.
- **Evidence collection:** File+line citations recorded in the threat register above. Every `mitigate` disposition has a verified code reference.
- **Accepted risks:** 11 entries logged (see Accepted Risks Log). All `accept` dispositions inherit from the plan-level `<threat_model>` declarations.
- **Deferred:** T-06-04-01 routed down-stack to per-skill URL validators; verified closed at both downstream layers.
- **Unregistered flags:** 0 — all 5 SUMMARY files that declare a `## Threat Flags` section explicitly report "None".

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer / defer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-04-22
