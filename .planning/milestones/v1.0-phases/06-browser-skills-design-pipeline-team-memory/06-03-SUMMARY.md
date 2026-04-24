---
phase: 06-browser-skills-design-pipeline-team-memory
plan: 03
subsystem: memory
tags: [memory-search, ranking-formula, ttl-decay, provenance-weight, grep-safe-regex]

# Dependency graph
requires:
  - phase: 06-01
    provides: MemoryConfig (retention_pattern_days, retention_incident_days)
  - phase: 06-02
    provides: MemoryEntry pydantic schema + TeamMemoryStore.list API
provides:
  - decay_factor(entry, now) — per-tag TTL with 1.0/0.2/0.05 tiers (D-06, MEM-07)
  - recency_weight(ts, now) — 1/(1 + days/30) smooth decay with malformed-ts defence
  - provenance_weight(entry) — D-06 + MEM-05 source-credibility weights
  - rank(entry, now) → SearchResult(entry, score, recency, provenance, decay)
  - search(store, query, scope, tag, role) — grep-safe keyword retrieval ranked desc
affects: [06-10 /learn search CLI, 06-11 conflict detection + high-impact gate]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Transparent multiplicative ranking (recency × provenance × decay) with component exposure on SearchResult for --explain UX"
    - "re.escape(query) pattern for user-supplied keyword → literal regex (ReDoS mitigation)"
    - "Defensive malformed-timestamp floors (decay=0.05, recency=0.1) — never crash the ranker"

key-files:
  created:
    - clawteam/memory/decay.py (per-tag TTL + decay_factor)
    - clawteam/memory/search.py (rank + search + component weights)
    - tests/memory/test_decay.py (11 tests)
    - tests/memory/test_search_ranking.py (17 tests)
    - .planning/phases/06-browser-skills-design-pipeline-team-memory/deferred-items.md
  modified:
    - clawteam/memory/__init__.py (re-export search + decay surface)

key-decisions:
  - "user + no-evidence gets provenance=1.2 (not 0 or 2.0) — user claims outrank un-cited artifacts but rank below cited users"
  - "artifact + no-evidence gets provenance=0.6 per MEM-05 (flagged, never zeroed) — entries stay discoverable"
  - "Multi-tag entries take MAX TTL — a pattern+preference entry follows preference (indefinite), not pattern (90d)"
  - "Regex metacharacters in user queries are re.escape-d — treat query as literal, eliminate ReDoS surface (T-06-03-01)"
  - "decay_factor floor = 0.05 (never 0.0) — honours MEM-07: expired entries discoverable but deprioritised"
  - "malformed timestamps never crash — decay returns 0.05, recency returns 0.1; defensive posture for long-lived JSONL"

patterns-established:
  - "Pattern: SearchResult exposes the 3 factor components (recency/provenance/decay) so --explain UX can tell users why an entry ranks where it does"
  - "Pattern: TTL table is a module-level dict overridable via MemoryConfig — adding a new tag TTL is a 1-line change"
  - "Pattern: Search delegates storage reads to TeamMemoryStore.list and never touches JSONL directly — single source of truth for tombstone suppression"

requirements-completed: [MEM-03, MEM-05, MEM-07, D-06]

# Metrics
duration: ~22 min
completed: 2026-04-22
---

# Phase 6 Plan 03: memory-search-rank Summary

**Transparent D-06 ranking — score = recency × provenance × decay — with per-tag TTL (pattern 90d, incident 180d, preference indefinite), grep-safe keyword search over title+body, and MEM-07 floor ensuring expired entries rank last but stay discoverable**

## Performance

- **Duration:** ~22 minutes
- **Started:** 2026-04-22T20:39:00Z
- **Completed:** 2026-04-22T21:00:36Z
- **Tasks:** 2 (both TDD with RED→GREEN cycles)
- **Files modified:** 5 (2 new substrate + 2 new test files + 1 init update)

## Accomplishments

- Shipped the D-06 ranking formula with fully transparent component factors — SearchResult exposes recency/provenance/decay separately so `/learn search --explain` (Plan 06-10) can show users *why* an entry ranks where it does.
- Honoured MEM-07 floor contract: decay_factor drops to 0.2 at TTL → 0.05 at 2×TTL but never to 0.0; expired entries appear last in search results, never filtered.
- Honoured MEM-05 flagged-not-blocked contract: artifact entries with no evidence get provenance=0.6 (not 0.0) — still discoverable, just deprioritised relative to cited artifacts (1.0) and cited users (2.0).
- Mitigated T-06-03-01 ReDoS risk by `re.escape`-ing user queries — no catastrophic-backtracking surface even if a user pastes in regex metacharacters.
- 28 new tests across decay + ranking covering TTL edge cases, malformed timestamps, clock-skew tolerance, provenance bucket matrix, keyword matching, case-insensitivity, expired-ordering, scope/tag filtering, and MemoryConfig TTL overrides.

## Task Commits

1. **Task 1: TTL table + decay_factor pure function** (TDD)
   - `af1fbd8` (test) — 11 failing decay tests
   - `a1d9d24` (feat) — decay_factor implementation

2. **Task 2: search.py — recency + provenance + rank + keyword search** (TDD)
   - `2019ff7` (test) — 17 failing ranking tests
   - `fe5d132` (feat) — search + recency + provenance + rank + init re-export

**Plan metadata:** (this commit) `docs(06-03): complete memory-search-rank plan`

## Files Created/Modified

- `clawteam/memory/decay.py` — Per-tag TTL table + `decay_factor(entry, now, *, memory_config)`. MAX-TTL rule for multi-tag entries, `MemoryConfig.retention_pattern_days` override, defensive malformed-timestamp and future-timestamp handling.
- `clawteam/memory/search.py` — `SearchResult` dataclass, `recency_weight`, `provenance_weight`, `rank`, and the `search(store, query, scope, tag, role)` entrypoint. Keyword match is case-insensitive via `re.compile(re.escape(query), re.IGNORECASE)`.
- `clawteam/memory/__init__.py` — Added `decay_factor`, `rank`, `search`, `SearchResult` to `__all__`.
- `tests/memory/test_decay.py` — 11 tests (pattern/incident/preference TTL tiers, MAX-TTL, unknown/empty tags, malformed/future timestamps, MemoryConfig override).
- `tests/memory/test_search_ranking.py` — 17 tests (recency curve, provenance matrix, rank composition, keyword match, case-insensitivity, rank ordering, tag/scope/role filtering, MEM-07 floor).

## Decisions Made

- **user + no-evidence = 1.2** (not in the original D-06 table). Rationale: a user claim without a file:line citation still outranks an un-cited artifact (0.6) but ranks below a cited user (2.0) or cited artifact (1.0). Prevents a cliff between 0 and 2.0 and keeps the ranking monotone in evidence-presence.
- **Recency formula `1 / (1 + days/30)`**: smooth decay, never hits zero, stays positive for even 50-year-old entries. Chosen over exponential because it's easier to reason about ("30 days = half, 90 days = quarter").
- **Decay floor 0.05** (not 0.0): MEM-07 requires expired entries to remain discoverable. A zero would multiply the composite score to zero and tie all expired entries, destroying the recency signal.
- **`re.escape` the query**, not a regex surface: the `/learn search` CLI (Plan 06-10) is explicitly positioned as grep, not regex. Treating the query as a literal matches user intent and eliminates the ReDoS attack surface at the same time.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Plan 06-02 substrate was referenced-but-not-committed**
- **Found during:** Task 1 RED commit
- **Issue:** Plan 06-03 imports `MemoryEntry` (from `clawteam.memory.entry`) and `TeamMemoryStore` (from `clawteam.memory.store`). Plan 06-02 runs in the same Wave 1 as 06-03. On inspection, `entry.py` + the Plan 06-02 test files were already committed (commits `1bf9ed9`, `46e4df8`, `8cc32d6`), but `store.py` + the 06-02 `__init__.py` update were staged-but-uncommitted.
- **Fix:** Neither file was created by me — they were pre-existing Plan 06-02 staged work. I proceeded with Plan 06-03 on top of the staged substrate; Plan 06-02's executor committed its own substrate immediately before my Task 2 GREEN (commit `98425bb`), so the final sequence is clean.
- **Files modified:** none (Plan 06-02 landed its own substrate).
- **Verification:** `pytest tests/memory/` — 53/53 passing covers 06-01 + 06-02 + 06-03.
- **Committed in:** n/a — this was a discovery, not a direct fix.

**2. [Rule 1 - Test Data Bug] id_suffix used non-hex characters**
- **Found during:** Task 2 GREEN first pytest run
- **Issue:** Two tests (`test_search_role_scope`, `test_search_empty_query_returns_all`) used `id_suffix="ggg001"` / `"hhh001"` / `"hhh002"` / `"hhh003"`, which fail `MemoryEntry.id` pattern `[a-f0-9]{6}`.
- **Fix:** Renamed to `"aa1001"` / `"aa1002"` / `"bb1001"` / `"bb1002"` / `"bb1003"` — valid hex.
- **Files modified:** `tests/memory/test_search_ranking.py`
- **Verification:** Re-ran `pytest tests/memory/test_search_ranking.py` — 17/17 GREEN.
- **Committed in:** `fe5d132` (Task 2 GREEN commit).

---

**Total deviations:** 2 (1 Rule 3 blocking-dependency discovery, 1 Rule 1 test-data bug).
**Impact on plan:** Neither deviation touched the plan's scope — test-data fix was a typo in my own test fixture, dependency discovery was a cross-plan synchronisation quirk handled by Plan 06-02's executor. No scope creep.

## Issues Encountered

- **9 pre-existing test-ordering failures in the broader suite** (`tests/test_gstack_plugin.py`, `tests/test_evidence_schemas_phase5.py`, `tests/test_plugin_hooks.py`). Reproducible on the pre-06-03 baseline (commit `98425bb`); unrelated to memory-search-rank. Logged in `deferred-items.md` per scope-boundary rules.

## Threat Flags

_None beyond those already in the plan's `<threat_model>` — all three threat IDs (T-06-03-01 ReDoS, T-06-03-02 malformed-timestamp, T-06-03-03 ranker-never-deletes) are mitigated in code + have corresponding tests._

## Next Phase Readiness

- **Plan 06-10 /learn CLI** can now `from clawteam.memory import search, rank, SearchResult` and delegate directly — the `--explain` flag lights up component weights automatically via `SearchResult.recency/provenance/decay`.
- **Plan 06-11 conflict-detection + high-impact gate** can compose on top of `rank()` — the plan explicitly defers `clawteam/memory/conflict.py` (cosine-on-BoW + sentiment-opposition heuristic) per this plan's `Do NOT` list.
- **Plan 06-12 /sprint-reflect backfill** benefits from `provenance_weight("sprint-reflect") = 0.8` which is landed and tested here.

---
*Phase: 06-browser-skills-design-pipeline-team-memory*
*Plan: 03 (memory-search-rank)*
*Completed: 2026-04-22*

## Self-Check: PASSED

- All 7 declared files exist on disk.
- All 4 declared Task commit hashes (`af1fbd8`, `a1d9d24`, `2019ff7`, `fe5d132`) are present in `git log`.
- `pytest tests/memory/` — 53/53 passing (entry=10, store=15, decay=11, search=17).
- `python -c "from clawteam.memory import search, rank, SearchResult, decay_factor, TeamMemoryStore, MemoryEntry"` — import succeeds.

## TDD Gate Compliance

- Task 1 RED `af1fbd8` → GREEN `a1d9d24` (test before impl). ✓
- Task 2 RED `2019ff7` → GREEN `fe5d132` (test before impl). ✓
- No refactor commits needed — both GREENs landed clean.
