---
phase: 6
phase_name: Browser Skills, Design Pipeline & Team Memory
phase_slug: browser-skills-design-pipeline-team-memory
gathered: 2026-04-21
status: Ready for planning
source: /gsd-discuss-phase --auto (autonomous)
---

# Phase 6: Browser Skills, Design Pipeline & Team Memory — Context

<domain>
## Phase Boundary

Deliver the two biggest user-facing differentiators that make the "team that learns your taste" narrative real, plus the memory substrate that unlocks the full `/learn` product surface. Three deliverable clusters:

### Cluster A — Browser pipeline (`clawteam[browser]` extra)
1. **`clawteam[browser]` optional extra** — `pip install 'clawteam[browser]'` adds `playwright>=1.58,<2` as an optional dep. `playwright install chromium` provisions the runtime. On machines without the extra, every browser skill returns `SkillUnavailable` with install commands.
2. **`/browse`** (engineer, qa, dx-lead) — general-purpose headless browser navigation. Input: URL + optional action script (click, fill, screenshot). Output: `browse-result.md` with screenshot path + DOM hash + HTTP status.
3. **`/open-gstack-browser`** (engineer, qa, dx-lead, designer) — opens Chromium in head*ed* mode pre-seeded with sprint context (workspace branch URL or local dev server). UI for humans; headless for the skill's monitoring side-channel.
4. **`/setup-browser-cookies`** (engineer, qa, dx-lead) — one-time wizard to capture session cookies for a target domain (e.g., logged-in staging env). Stores under `~/.clawteam/teams/<team>/browser/cookies/<domain>.json` with `file_locked`.

### Cluster B — Design pipeline
5. **`/design-shotgun`** (designer) — mockup variant generation (default 4 variants, configurable), renders HTML previews to a comparison board under `sprints/<id>/design-board/`, supports iterative refinement. Writes taste-observation entries to designer's per-agent `/learn` memory scope per iteration citing which variant user picked + why.
6. **`/design-html`** (designer) — takes a chosen mockup, emits production HTML following the Pretext pattern. Auto-detects project framework (React/Svelte/Vue/plain HTML) from `package.json` + import analysis; outputs conforming source under `src/` (or framework equivalent).

### Cluster C — Team Memory substrate
7. **`TeamMemoryStore`** at `~/.clawteam/teams/<team>/memory/` with two-tier layout: `memory/team/` (shared) + `memory/agents/<role>/` (per-role private). Append-only JSONL writes with pydantic-validated frontmatter (id, author, sprint_id, phase, timestamp, tags, evidence_citation, confidence, learned_from).
8. **`/learn`** skill (agent-callable + `clawteam learn` CLI):
   - `learn write <scope> <title>` — writes JSONL entry with auto-assigned id, validates provenance.
   - `learn list <scope> [--tag]` — lists entries; filterable by tag.
   - `learn search <query>` — grep-first retrieval; ranks by recency × provenance-weight × decay.
   - `learn prune <id>` — soft-purge; appends tombstone JSONL entry.
9. **Provenance + decay + conflict detection:**
   - Entries without evidence_citation get lower retrieval rank (not blocked — flagged).
   - Per-tag TTL: `pattern` 90 days, `preference` indefinite, `incident` 180 days. Expired entries rank below unexpired; never auto-deleted.
   - Contradicting entries on same tag trigger `conflict_detected` event; writer sees "conflicts with X, resolve via `/learn --resolve`".
10. **High-impact gate:** `impact:high` tagged writes OR writes under `memory/team/decisions/` trigger `InteractionGate`-backed human confirmation. Entry staged in `memory-pending/` until human answers; on confirm, moves to permanent location.
11. **Reflect-phase backfill scanner:** First `/learn` invocation walks `_phase6_pending/` (Phase 3 stub location) and promotes retro entries to `memory/team/retros/` with `learned_from: sprint-reflect` metadata.
12. **Per-team namespace isolation:** No agent on team A can read `memory/team/` or `memory/agents/*` from team B. Enforced via path validation in all read/write APIs.

**Scope boundary (explicit exclusions):**
- Embedding-based memory retrieval (sqlite-vec) → v2 per STACK.md upgrade path. Phase 6 is grep-first only.
- Multi-team Conductor UI / board sprint panels → v2.
- Multi-sprint concurrency caps for `/design-shotgun` (e.g., 10 parallel shotgun sessions) → Phase 7.
- Cost dashboard consumption of `memory_write_persisted` / `conflict_detected` events → Phase 7.
- Browser-based cross-vendor coordination (`/pair-agent`) → v1.1/v2.

**Delete invariant (extends Phases 3-5):** Removing `clawteam/templates/gstack/skills/{browse,open_gstack_browser,setup_browser_cookies,design_shotgun,design_html,learn}/` + `clawteam/memory/` (NEW directory for TeamMemoryStore base) + all registrations must leave the rest of the codebase running unchanged. `TeamMemoryStore` is generic substrate (could upstream eventually) but is only instantiated via plugin contribution. Playwright dep is OPTIONAL — codebase must import-guard + degrade gracefully if missing.

</domain>

<decisions>
## Implementation Decisions

### Browser extra packaging (Area 1)

- **D-01:** **`pyproject.toml` `[project.optional-dependencies]` block adds `browser = ["playwright>=1.58,<2"]`.** `pip install 'clawteam[browser]'` works as written in ROADMAP. Post-install user must run `playwright install chromium` (documented in `clawteam doctor` recommendations + `SkillUnavailable` error hint). No `playwright install` is auto-run — too-heavy side effect.
  **Why:** Standard PEP 517 optional-extra pattern. Separation of concerns: package ships lockfile entry; binary provisioning is user opt-in.

- **D-02:** **Feature detection via `clawteam/browser/__init__.py::playwright_available() -> bool`** that tries `import playwright` under `try/except`. All 5 browser skills' `tool_available()` calls this helper. Zero import-time side effects in the skill modules themselves — skill handlers call `playwright_available()` at runtime, not import.
  **Why:** Prevents `import playwright` at skill-registration time (would crash import if Playwright absent). Test-friendly: mock via `monkeypatch.setattr(browser, "playwright_available", lambda: False)`.

- **D-03:** **Browser skills live at `clawteam/templates/gstack/skills/{browse,open_gstack_browser,setup_browser_cookies,design_shotgun,design_html}/`** mirroring Phase 4 + Phase 5 skill sub-package pattern. `__init__.py` (public), `handler.py` (skill impl), optional `state.py` for `/design-shotgun` iterative state, optional `adapters.py` for Playwright wrapping. **Additionally:** a shared `clawteam/browser/` module (NEW top-level, NOT under `templates/gstack/`) provides generic Playwright adapter + session management. This is generic substrate (non-gstack) — following the D-03 Phase 5 precedent (generic substrate at `clawteam/<name>/`, gstack-specific at `clawteam/templates/gstack/`).
  **Why:** Browser infrastructure is reusable by non-gstack templates (hedge-fund could add a market-scraping skill). Design skills are gstack-specific (live under templates/gstack/).

### Memory substrate (Area 2)

- **D-04:** **`TeamMemoryStore` at `clawteam/memory/store.py`** (NEW top-level). Generic substrate. Public API: `write(entry: MemoryEntry) -> str` (returns id), `list(scope, tag=None) -> list[MemoryEntry]`, `search(query) -> list[MemoryEntry]`, `prune(id) -> None`. Pydantic `MemoryEntry` model at `clawteam/memory/entry.py` with fields: `id`, `author`, `sprint_id`, `phase`, `timestamp`, `tags: list[str]`, `evidence`, `confidence`, `learned_from: Literal["user", "artifact", "self-inferred"]`, `scope: Literal["team", "role"]`, `role: str | None`.
  **Why:** Top-level package mirrors `clawteam/harness/`, `clawteam/events/` conventions. Pure pydantic + file-locked JSONL — no new deps.

- **D-05:** **Append-only JSONL persistence** at `~/.clawteam/teams/<team>/memory/{team/,agents/<role>/}/<YYYY-MM>.jsonl`. Month-bucketed for bounded file size + grep-friendly. All writes via `file_locked()` + `atomic_append_line()` (new helper in `clawteam/utils/io.py` if not present). Prune = append tombstone record (`{"id": X, "op": "prune", "ts": ...}`) — never rewrite history.
  **Why:** Immutable audit trail = MEM-02 floor. Month bucketing balances grep speed against file count. Soft-prune keeps forensic recoverability.

- **D-06:** **Grep-first retrieval via `ripgrep` if available, else stdlib `re.search` over JSONL line-by-line.** `learn search` builds a ranked list: score = `recency_weight × provenance_weight × decay_factor`. Recency weight = `1 / (1 + days_since_write / 30)`. Provenance weight = `2.0` if `learned_from == "user"` + evidence present, `1.0` if artifact-grounded, `0.3` if self-inferred. Decay factor = `1.0` if not expired, `0.2` if expired but < 2× TTL, `0.05` if > 2× TTL (never zero — expired entries stay discoverable).
  **Why:** Grep-first = zero new runtime deps. Scoring formula is transparent; users can debug "why isn't my entry ranking" by eyeballing the score components. Explicit weights > opaque neural ranking.

### `/learn` skill surface (Area 3)

- **D-07:** **`/learn` skill is role-agnostic** (unlike Phase 4/5 skills that bind to specific roles). Any agent can `/learn write`. Phase 3 Reflect-phase handler auto-invokes `/learn write team "sprint-<id>-retro"` via the backfill scanner (see D-11 below). Human invokes via `clawteam learn` Typer subcommand.
  **Why:** Memory writes come from every role + sprint phase; restricting to a subset would block the "team learns your taste" narrative. Safety is the impact-gate (D-09), not the author-role.

- **D-08:** **`/learn write` signature:** `/learn write --scope team|role --role <role-if-role-scope> --title "<title>" --evidence "<path:line|artifact-ref>" --tags tag1,tag2 --confidence 0.0-1.0 --learned-from user|artifact|self-inferred --impact low|medium|high "<body>"`. Impact defaults to `medium`. Confidence defaults to `0.7`. Evidence is OPTIONAL but skill emits a warning if absent (retrieval ranking downgrade applies).
  **Why:** Explicit schema catches misuse at the CLI layer. Optional evidence is flagged-not-blocked per MEM-05.

### High-impact gate + conflict detection (Area 4)

- **D-09:** **`impact:high` tag OR writes to `memory/team/decisions/`** trigger `InteractionGate`-backed confirmation. Entry staged to `memory/<scope>/pending/<id>.jsonl`. A question file lands at `sprints/<id>/questions/memory-confirm-<id>.md` with structured prompt. Answer file → promotes pending to permanent via `file_locked` move. Absent answer after sprint completion → entry stays pending (human can finalize later via `clawteam learn --resolve <id>`).
  **Why:** MEM-06 mandate. Staging+promote keeps the audit trail clean and reversible.

- **D-10:** **Conflict detection algorithm:** On `/learn write`, search existing entries with `any tag in tags` + same `scope`. For each match, compute assertion similarity (simple cosine on bag-of-words from body or explicit `contradicts: <id>` field). If similarity > 0.75 + sentiment-opposition heuristic triggers, emit `conflict_detected` event. Writer sees "conflicts with memory/X entry Y (score 0.82); resolve via `/learn --resolve`". The write is NOT blocked — user can choose to resolve after.
  **Why:** Avoids false-positive blocking; keeps memory audit-trail-first. Simple heuristic > ML classifier for v1; users can tune threshold via `gstack.toml [memory] conflict_threshold = 0.75`.

### Backfill scanner (Area 5)

- **D-11:** **First `/learn` invocation per team runs `backfill_scan()`** that walks `~/.clawteam/teams/<team>/_phase6_pending/` (the Phase 3 stub location per Phase 3 D-09). Each `.json` file → promoted to `memory/team/retros/<YYYY-MM>.jsonl` with `learned_from: sprint-reflect`, `tags: ["retro", "phase-reflect"]`, evidence pointing to the sprint's `retro.md` artifact. Backfill is idempotent (checks `_phase6_pending/processed/<id>.processed` sentinel file).
  **Why:** Phase 3 D-09 promised this backfill hook; Phase 6 delivers. Idempotency = safe re-runs.

### Design pipeline (Area 6)

- **D-12:** **`/design-shotgun` state machine** per Phase 4 state-machine pattern. States: `initialized → variants_generating → board_rendered → user_picking → refining → converged | abandoned`. Variant count configurable via `gstack.toml [design_shotgun] variant_count = 4` (default 4). Variants rendered as standalone HTML under `sprints/<id>/design-board/variant-<N>/`. User picks one → state machine writes taste-observation to designer's `memory/agents/designer/` via `/learn write`.
  **Why:** Phase 4 D-01..D-03 state-machine pattern is canonical for multi-turn interactive skills. Variant count is visible-configurable for teams that want 2 or 8.

- **D-13:** **`/design-html` framework detection:**
  1. Read `package.json` dependencies: `react` present → React/JSX; `svelte` present → Svelte; `vue` present → Vue; otherwise → plain HTML.
  2. If multiple frameworks present (e.g., a micro-frontend monorepo), emit `question.md` asking which framework to target.
  3. Output lands at the detected framework's source root (`src/` for React/Vue/Svelte, project root for plain HTML).
  **Why:** Explicit detection order > guessing. Question-first on ambiguity = safe default.

### Verification stringency (Area 7)

- **D-14:** **Memory substrate tests: 3 minimum per capability.** For `TeamMemoryStore.write`: write+read roundtrip; write with evidence vs without; write with impact:high triggers gate. For `.search`: recency ranking; provenance weighting; decay expiry. For conflict detection: same-tag similar-body triggers event; different-tag bypasses; threshold configurable.
  **Why:** Core primitive — breakage ripples through all `/learn` calls + Phase 3 backfill.

- **D-15:** **Per-team isolation test** (MEM-04 floor): Create team A + team B. Write entries to both. Assert team-A agent calling `memory.read()` scoped to A cannot read B's entries. Assert same for `memory.search()`. Assert path traversal attacks (`../teamB/...`) rejected by path validation.
  **Why:** Security-adjacent (cross-team data leak). Belongs in core tests, not afterthought.

- **D-16:** **Browser skill tests use `monkeypatch` to replace `playwright.sync_api.sync_playwright` with a mock** — tests never actually spin Chromium. Integration test: `/browse` happy path against mocked Playwright returning fixed HTML + screenshot bytes. Missing-playwright test: monkeypatches `playwright_available()` to return False; asserts `SkillUnavailable` with correct install-hint text.
  **Why:** Real Chromium in CI = expensive + flaky. Mock-based tests verify contract; real-browser testing happens at human UAT.

- **D-17:** **Design skill tests** use fixture mockups under `tests/fixtures/design_shotgun/` — 4 static HTML variants + 1 "picked" variant JSON. `/design-shotgun` state machine asserts: variants_generated count = 4; board_rendered file exists; user_picking state advances on taste-observation write; converged state emits proper memory entry.
  **Why:** Deterministic fixtures > live LLM-generated variants for unit tests.

### Claude's Discretion (planner picks; no need to ask user)

- Pydantic field shapes for `MemoryEntry` subfields (which are Optional, default values, regex constraints).
- Wave structure + parallelism — planner determines from file dependencies. Likely Wave 0 (playwright extra + clawteam/browser/ substrate + clawteam/memory/ substrate), Wave 1 (3 browser skills parallel), Wave 2 (3 design + /learn skills), Wave 3 (high-impact gate + conflict detection + backfill scanner), Wave 4 (integration + plugin wiring).
- Question prompt text for memory-confirm-<id>.md — planner picks; must include `scope`, `tag highlights`, `body preview`, and `Confirm / Reject / Edit` options.
- Plain-HTML fallback structure for `/design-html` — planner picks a conventional structure (index.html + styles.css + app.js) if no framework detected.
- Internal split of `clawteam/browser/` modules (adapter.py vs session.py vs cookies.py) — planner picks.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 6 deliverable specifications (load-bearing)

- `.planning/ROADMAP.md` §"Phase 6: Browser Skills, Design Pipeline & Team Memory" (lines 271-297) — phase goal, 10 success criteria, requirements.
- `.planning/REQUIREMENTS.md` MEM-01..07, SKILL-10..12, QUALITY-10 verbatim.

### Project-locked context

- `.planning/PROJECT.md` §"Key Decisions" — Python 3.10+, no new *required* runtime deps, persistence under `get_data_dir()`, per-team namespace isolation.

### Phase 3 substrate (Phase 6 extends)

- `.planning/phases/03-gstack-team-template-methodology-port/03-CONTEXT.md` D-09 Reflect-phase `_phase6_pending/` stub location + backfill promise.
- `clawteam/plugins/gstack_sprint_plugin.py::on_register` Reflect-phase handler — writes retros to `_phase6_pending/` (Phase 3) + Phase 6 D-11 scanner promotes these.

### Phase 4 substrate (Phase 6 reuses)

- `clawteam/harness/interaction_gate.py` — high-impact memory gate (D-09) subclasses or reuses directly.
- `clawteam/events/bus.py` + `clawteam/events/types.py` — Phase 6 adds `memory_write_persisted`, `conflict_detected`, `memory_backfill_complete` event dataclasses following Phase 4 MidReviewThrash pattern.

### Phase 5 substrate (Phase 6 extends skill machinery)

- `clawteam/plugins/skill_registration.py` + `skill_dispatcher.py` — 6 new Phase 6 skills (`/browse`, `/open-gstack-browser`, `/setup-browser-cookies`, `/design-shotgun`, `/design-html`, `/learn`) register via this.
- `clawteam/spawn/invoke.py::invoke_native_cli` — if any browser skill shells out to CLI binaries.
- `clawteam/events/hooks.py` `clawteam doctor` — add Playwright + chromium detection entries.
- `clawteam/templates/gstack/skills/` — 6 new skill sub-packages mirror Phase 4/5 layout.

### Research foundation

- `.planning/research/STACK.md` "Playwright as optional extra" + "grep-first team memory, embeddings in v2".
- `.planning/research/ARCHITECTURE.md` Pattern 5 (TeamMemory layered) + `/learn` skill rules.
- `.planning/research/PITFALLS.md` Pitfall 10 (memory poisoning — ship-blocker; provenance + decay + human-gate all prevent), Pitfall 3 (context exhaustion — partially mitigated via MemGPT-tiered memory design).
- `.planning/research/FEATURES.md` P1 list for `/browse`, `/design-shotgun`, `/design-html`, `/learn`.

### Phase 5 precedent (close analog)

- `.planning/phases/05-tool-heavy-skills-ship-sre-codex/05-CONTEXT.md` D-01 (skill sub-package shape), D-03 (NativeCliAdapter), D-04 (missing-tool detection pattern).

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- `clawteam/plugins/skill_registration.py` + `skill_dispatcher.py` — 6 new skills register via existing machinery (no new hooks).
- `clawteam/harness/interaction_gate.py` — high-impact write gate reuses.
- `clawteam/events/bus.py` + `types.py` — add 3 new event dataclasses.
- `clawteam/events/hooks.py::scrub_env` + `clawteam doctor` — add Playwright + chromium detection entries.
- `clawteam/plugins/gstack_sprint_plugin.py` — extend `contribute_skills()` with 6 new SkillRegistration (total: 16 Phase 4+5+6 skills).
- `clawteam/plugins/gstack_sprint_plugin.py::on_register` Reflect-phase handler — adds `/learn` auto-invoke on retro (D-11 backfill).
- `questionary` (already in stack) — `/setup-browser-cookies` + `/design-shotgun` interactive prompts.

### New Top-Level Packages

- `clawteam/browser/` — generic Playwright adapter + session management + cookie store. Import-guarded; imports nothing at module load if Playwright absent.
- `clawteam/memory/` — TeamMemoryStore + MemoryEntry pydantic + search/prune logic + conflict detection.

### Established Patterns

- **Per-skill sub-package** — Phase 4 D-01 + Phase 5 D-01. 6 new Phase 6 skills follow.
- **`tool_available()` per-skill helper** — Phase 5 D-04. Browser skills use `clawteam/browser/__init__.py::playwright_available()` central function.
- **`invoke_native_cli` for external CLI** — Phase 5 D-03. Browser skills don't need CLI; `/design-html` might shell out to `prettier` (optional).
- **`file_locked` + `atomic_append_line`** — memory JSONL writes.
- **Pydantic schemas with registration** — memory adds 3 event dataclasses + 1 MemoryEntry model; no EvidenceSchemaRegistry entries (memory is not phase-artifact).
- **EventBus emission** — 3 new event types.
- **gstack.toml additive sub-blocks** — `[memory]`, `[design_shotgun]`, `[browser]` pydantic config models.

### Integration Points

- `GstackSprintPlugin.contribute_skills()` extends with 6 new SkillRegistration.
- `GstackSprintPlugin.on_register` Reflect-phase handler adds `/learn --backfill` auto-invoke.
- `clawteam/plugins/gstack_sprint_plugin.py` instantiates `TeamMemoryStore(team_name)` lazily on first memory access.
- `clawteam/cli/commands.py::learn` Typer subcommand — `clawteam learn {write,list,search,prune,resolve}`.
- `tests/test_template_regression_matrix.py` — extend with cross-template isolation test for memory (team-A-agent cannot read team-B-memory).

</code_context>

<specifics>
## Specific Ideas

- **MemoryEntry JSONL schema (canonical):**
  ```json
  {
    "id": "mem-<team-slug>-<YYYYMMDD>-<hash6>",
    "author": "engineer@sprint-<id>",
    "sprint_id": "<sprint-id>",
    "phase": "<phase-name>",
    "timestamp": "<ISO-8601>",
    "tags": ["pattern", "async", "impact:medium"],
    "evidence": "src/auth/token.py:42-58",
    "confidence": 0.85,
    "learned_from": "artifact",
    "scope": "team",
    "role": null,
    "body": "...markdown body...",
    "op": "write"
  }
  ```

- **memory-confirm-`<id>`.md question template:**
  ```markdown
  # Memory write: high-impact confirmation required

  **Entry id:** mem-myteam-20260421-abc123
  **Scope:** team
  **Tags:** impact:high, decision, architecture
  **Author:** eng-mgr@sprint-042
  **Evidence:** docs/rfcs/007-queue-backpressure.md

  ## Preview

  > We migrated from sync Redis queue to async stream per RFC 007 because
  > we observed 10× p99 latency improvements under 10k rps load.

  ## Options

  1. Confirm — promote to memory/team/decisions/
  2. Edit — revise body/tags before confirming
  3. Reject — discard
  ```

- **`gstack.toml` additive sub-blocks:**
  ```toml
  [memory]
  conflict_threshold = 0.75
  retention_pattern_days = 90
  retention_incident_days = 180

  [design_shotgun]
  variant_count = 4
  board_format = "html"  # html | markdown

  [browser]
  headless = true
  timeout_seconds = 30
  cookies_dir = "<team-data-dir>/browser/cookies"
  ```

- **Ranking score debug output** (for `learn search --explain`):
  ```
  mem-abc123  score=1.42  recency=0.95 provenance=2.0 decay=1.0  tags=pattern,async
  mem-def456  score=0.38  recency=0.22 provenance=1.0 decay=0.2  tags=pattern,deprecated
  ```

- **Conflict event payload:**
  ```python
  @dataclass(frozen=True)
  class ConflictDetected(HarnessEvent):
    new_entry_id: str
    conflicting_entry_id: str
    similarity: float
    shared_tags: list[str]
    scope: str
  ```

</specifics>

<deferred>
## Deferred Ideas

### To Phase 7 (parallel + cost + attention)
- Cost dashboard consumption of memory_write_persisted + conflict_detected events — Phase 7.
- Multi-sprint concurrency for `/design-shotgun` (e.g., 10 shotgun sessions across sprints) — Phase 7.
- AttentionQueue for memory-confirm questions (cross-sprint prioritization) — Phase 7.

### To v1.1 / v2
- Embedding-based retrieval (sqlite-vec) — v2. Phase 6 is grep-first per STACK.md.
- `/pair-agent` cross-vendor browser coordination — v1.1/v2 per FEATURES.md P2.
- ML-based conflict detection (BERT or similar) — v2. Phase 6 uses cosine-on-BoW.
- Multi-team Conductor UI / board sprint panels — v2.
- Custom design-shotgun variant strategies beyond "N random variants" (e.g., "golden-ratio exploration") — v1.x.
- Per-team memory retention policies in UI (non-config-file edit) — v1.x.

### Reviewed Todos (not folded)
None — `.planning/todos/pending/` is empty.

</deferred>

<plan_prep_verifications>
## Plan-Prep Verification Tasks (must run BEFORE main planning)

| ID | Verification | Action if fails |
|----|--------------|-----------------|
| A1 | `pyproject.toml` has a `[project.optional-dependencies]` table; if not, add it. | Planner adds in Wave 0. |
| A2 | `clawteam doctor` already detects chromium (from Phase 0 / 5); re-confirm entry exists. | Phase 0 D-04 promised this; verify. |
| A3 | `clawteam/events/types.py` HarnessEvent dataclass pattern still follows Phase 4 MidReviewThrash (frozen dataclass + register_event_type call). | Phase 4 D-19 locked; re-confirm no drift. |
| A4 | `GstackSprintPlugin.contribute_skills()` now returns 10 Phase 4+5 skills; Phase 6 extends to 16 (adds 6). | Re-count via `len(plugin.contribute_skills())`. |
| A5 | `clawteam/utils/io.py::atomic_append_line` helper exists OR `file_locked` + `open(mode="a")` with fsync is the current pattern. | If neither, planner adds minimal helper. |
| A6 | `~/.clawteam/teams/<team>/_phase6_pending/` directory creation (from Phase 3 D-09) is still emitted by Reflect handler. | Phase 3 SUMMARY confirms; re-verify. |
| A7 | `gstack.toml` TemplateDef accepts unknown `[memory]`, `[design_shotgun]`, `[browser]` sub-blocks (Phase 5 D-07 confirmed `extra="ignore"` at TemplateDef level; Phase 6 adds new ship/deploy/canary/benchmark pattern extends). | Phase 5 Plan 01 landed sub-block pattern; Phase 6 follows the same extension. |
| A8 | `clawteam/harness/interaction_gate.py::InteractionGate` constructor accepts question path dynamically. | Phase 4 D-13 HumanApprovalGate reuses; re-confirm shape. |
| A9 | `questionary` is in stack (Phase 5 D-07 confirmed); re-verify. | `python -c "import questionary"`. |

</plan_prep_verifications>

---

*Phase: 06-browser-skills-design-pipeline-team-memory*
*Context gathered: 2026-04-21 via /gsd-discuss-phase --auto (autonomous)*
*Decisions: D-01 through D-17 (17 locked); plus 9 plan-prep verification tasks*
*Next: /gsd-plan-phase 6*
