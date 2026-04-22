# Phase 6: Browser Skills, Design Pipeline & Team Memory — Research

**Researched:** 2026-04-22
**Domain:** Browser skill substrate (Playwright optional extra) + design-pipeline state machine + team memory JSONL substrate with provenance/decay/conflict-detection/human-gate
**Confidence:** HIGH on stack + architecture (all precedent in Phases 0-5 code); MEDIUM on memory-ranking formula weights (schema is rigorous; weights are tunable defaults, not empirically calibrated yet)
**Research flag:** MEDIUM — memory provenance+decay schema needed a planning pass per ROADMAP §Phase 6

---

## Summary

Phase 6 ships three tightly-coupled clusters on top of the now-mature Phase 3-5 substrate: (A) a `clawteam[browser]` optional extra with 3 browser skills all gated on a central `playwright_available()` helper, (B) 2 designer-role design skills (`/design-shotgun` is the only new multi-turn state machine in this phase — joins `/office-hours` as the second per-skill state machine in the codebase), and (C) a TeamMemoryStore substrate + `/learn` skill exposing write/list/search/prune with provenance-weighted ranking, per-tag TTL decay, cosine+sentiment conflict detection, and an InteractionGate-backed high-impact human confirmation gate. All three clusters follow precedent exactly: browser + design skills mirror Phase 5's sub-package shape (`clawteam/templates/gstack/skills/<name>/{__init__.py, handler.py, adapters.py?, state.py?}`); generic substrate (browser adapter + TeamMemoryStore) lives at `clawteam/browser/` and `clawteam/memory/` top-level; plugin wiring extends the existing `GstackSprintPlugin.contribute_skills()` list from 7 → 13.

The memory substrate is the phase's technical novelty. Two design choices drive safety: (1) **append-only JSONL with month buckets** (`memory/team/2026-04.jsonl`) preserves the immutable audit trail that makes PITFALLS #10 (memory poisoning) recoverable; (2) **provenance-weighted ranking formula** (`recency × provenance × decay`) is transparent — users can debug why an entry ranks low by eyeballing the three components, unlike opaque embedding similarity. Conflict detection uses a bag-of-words cosine + sentiment-opposition heuristic with a `gstack.toml [memory] conflict_threshold` knob; false positives emit an advisory event without blocking the write. The `/learn` write path fires through the same `InteractionGate` primitive Phase 4 shipped for Ship-phase approval — `impact:high` writes stage to `memory/<scope>/pending/<id>.jsonl` and promote to canonical location only on explicit confirmation.

**Primary recommendation:** Follow the Phase 5 10-plan wave structure exactly. Wave 0 = plan-prep + pyproject extra + doctor + top-level package skeletons. Wave 1 = generic substrate (browser adapter + MemoryEntry + TeamMemoryStore read/write/search) + 3 new events. Wave 2 = 3 browser skills in parallel. Wave 3 = 2 design skills + `/learn` CLI+skill (parallel). Wave 4 = high-impact gate + conflict detection + backfill scanner. Wave 5 = plugin wiring + integration test + per-team isolation test. Expect ~12 plans; 5 waves; most plans 2-3 tasks.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions (D-01 through D-17 — do NOT revisit)

- **D-01** `pyproject.toml [project.optional-dependencies] browser = ["playwright>=1.58,<2"]`. No auto-`playwright install chromium` — user opt-in only. `clawteam doctor` surfaces install hint.
- **D-02** Feature detection via `clawteam/browser/__init__.py::playwright_available() -> bool`. Import-guarded `try: import playwright` inside helper. No import-time side effects in skill modules.
- **D-03** Browser skills at `clawteam/templates/gstack/skills/{browse,open_gstack_browser,setup_browser_cookies,design_shotgun,design_html}/`. Generic `clawteam/browser/` substrate (new top-level) for adapter + session management.
- **D-04** `TeamMemoryStore` at `clawteam/memory/store.py` (new top-level, mirrors `clawteam/harness/`). Public API: `write(entry)`, `list(scope, tag=None)`, `search(query)`, `prune(id)`. `MemoryEntry` pydantic at `clawteam/memory/entry.py`.
- **D-05** Append-only JSONL at `~/.clawteam/teams/<team>/memory/{team/,agents/<role>/}/<YYYY-MM>.jsonl`. `file_locked()` + atomic append. Prune = tombstone record.
- **D-06** Grep-first retrieval (ripgrep if available, else stdlib `re`). Score = `recency × provenance × decay`. Recency = `1/(1+days/30)`. Provenance = 2.0 (user+evidence) / 1.0 (artifact) / 0.3 (self-inferred). Decay = 1.0 / 0.2 / 0.05.
- **D-07** `/learn` role-agnostic. Phase 3 Reflect-handler auto-invokes backfill scanner on first `/learn` call.
- **D-08** `/learn write` CLI signature: `--scope --role --title --evidence --tags --confidence --learned-from --impact "<body>"`. Evidence OPTIONAL; flagged not blocked (MEM-05).
- **D-09** `impact:high` OR `memory/team/decisions/` writes trigger `InteractionGate`. Staged at `memory/<scope>/pending/<id>.jsonl`. Question at `sprints/<id>/questions/memory-confirm-<id>.md`.
- **D-10** Conflict detection: BoW cosine > 0.75 + sentiment-opposition triggers `conflict_detected` event. Write NOT blocked. Threshold configurable via `gstack.toml [memory] conflict_threshold`.
- **D-11** First `/learn` invocation per team runs `backfill_scan()` walking `_phase6_pending/`. Idempotent via `.processed` sentinel.
- **D-12** `/design-shotgun` state machine. States: `initialized → variants_generating → board_rendered → user_picking → refining → converged|abandoned`. Variant count via `gstack.toml [design_shotgun] variant_count = 4`.
- **D-13** `/design-html` framework detection: react → svelte → vue → plain HTML. Multiple frameworks → question.md asking which target.
- **D-14** 3 min tests per memory-substrate capability (write, search, conflict).
- **D-15** Per-team isolation test: A cannot read B; path-traversal rejected.
- **D-16** Browser skill tests monkeypatch `sync_playwright`; never spin real Chromium.
- **D-17** Design skill tests use fixture mockups under `tests/fixtures/design_shotgun/`.

### Claude's Discretion

- Pydantic field shapes for `MemoryEntry` subfields (Optional, defaults, regex) — research recommends specific shapes below.
- Wave structure + parallelism — this research recommends 5 waves, ~12 plans.
- Question prompt text for `memory-confirm-<id>.md` — research drafts below.
- Plain-HTML fallback structure for `/design-html` — research recommends `index.html + styles.css + app.js` sibling set.
- Internal split of `clawteam/browser/` modules — research recommends `adapter.py`, `session.py`, `cookies.py`.

### Deferred Ideas (OUT OF SCOPE)

- Embedding retrieval (sqlite-vec) → v2.
- Multi-team Conductor UI → v2.
- Multi-sprint concurrency caps for `/design-shotgun` → Phase 7.
- Cost dashboard consumption of new events → Phase 7.
- `/pair-agent` cross-vendor coordination → v1.1/v2.
- ML-based conflict detection (BERT) → v2.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MEM-01 | `TeamMemoryStore` at `~/.clawteam/teams/<team>/memory/` with `team/` + `agents/<role>/` | `clawteam/memory/store.py` substrate (Wave 1 Plan 06-02); layout fixed by D-05 |
| MEM-02 | Append-only JSONL with frontmatter (id, author, sprint_id, phase, timestamp, tags, evidence, confidence) | `MemoryEntry` pydantic (Code Example 1 below); `TeamMemoryStore.write()` append path uses `file_locked` + fsync |
| MEM-03 | Grep-first retrieval by tag+keyword, recency-weighted | Code Example 3 ranking formula; Wave 1 Plan 06-02 search() implementation |
| MEM-04 | `/learn` exposes write/list/search/prune via skill + CLI | Wave 3 Plan 06-07 (skill + CLI) |
| MEM-05 | Provenance tracking: entries without evidence rank lower (not blocked) | Code Example 3 provenance weight (0.3 no-evidence vs 2.0 user+evidence) |
| MEM-06 | High-impact writes require human confirmation via `InteractionGate` | Wave 4 Plan 06-09 gate integration; `InteractionGate` precedent from Phase 4 |
| MEM-07 | Per-tag TTL decay; expired entries rank below unexpired, never auto-deleted | Code Example 3 decay factor; `gstack.toml [memory] retention_*_days` keys |
| SKILL-10 | `/browse` + `/open-gstack-browser` + `/setup-browser-cookies` via Playwright optional extra | Wave 2 Plans 06-04, 06-05, 06-06 |
| SKILL-11 | `/design-shotgun` with variants + comparison board + taste memory | Wave 3 Plan 06-08 (state machine) |
| SKILL-12 | `/design-html` with framework detection | Wave 3 Plan 06-08 (companion) |
| QUALITY-10 | Memory provenance + decay + high-impact human gate (PITFALLS #10) | Covered by MEM-05/06/07 — no separate plan; integration test in Plan 06-11 |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Playwright driver + cookie store | Browser (substrate) | — | Generic browser automation; reusable by non-gstack templates |
| `/browse`, `/open-gstack-browser`, `/setup-browser-cookies` | Skill handler (gstack template) | Browser substrate | gstack-specific UX; delegates actual automation to substrate |
| `/design-shotgun`, `/design-html` | Skill handler (gstack template) | Browser substrate (for HTML rendering of variants) | Gstack-specific; calls browser substrate only for optional screenshotting |
| `MemoryEntry` schema + `TeamMemoryStore` | Memory substrate (top-level) | File I/O (existing `file_locked`) | Generic; could upstream eventually. Pure pydantic + JSONL — no new deps |
| `/learn` skill + `clawteam learn` CLI | Skill handler + CLI | Memory substrate | Skill dispatches via existing `SkillDispatcher`; CLI provides human parity |
| High-impact gate | Memory substrate | Existing `InteractionGate` (Phase 4) | Reuse — don't subclass unless needed |
| Conflict detection | Memory substrate | EventBus | Pure function on entry pair; emits advisory event via existing bus |
| Backfill scanner | Memory substrate | Phase 3 `_phase6_pending/` consumer | Idempotent one-shot on first `/learn` invocation per team |

---

## Standard Stack

### Core (no new required deps — enforces PROJECT.md "no new required runtime deps" rule)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic (existing) | >=2.0.0,<3.0.0 | `MemoryEntry` + conflict/event schemas | Existing hard dep; matches `ShipNotes`/`CanaryReport` precedent [VERIFIED: pyproject.toml dependencies block] |
| stdlib `json` + `re` | — | JSONL writer + grep-first retrieval | `ripgrep` preferred when available (faster); stdlib `re.search` fallback keeps zero-dep floor [CITED: D-06] |
| `clawteam.fileutil.file_locked` + `atomic_write_text` | existing | JSONL append + tombstone writes | Phase 2 primitive already serves gstack-sprint state, cost summaries [VERIFIED: clawteam/fileutil.py:28-84] |
| `clawteam.harness.interaction_gate.InteractionGate` | existing | High-impact memory-write human gate (D-09) | Phase 1 Plan 01-04 shipped this; ShipApprovalGate reuses (Phase 4 Plan 04-04) [VERIFIED: clawteam/harness/interaction_gate.py] |
| `clawteam.events.bus.EventBus` + `register_event_type` | existing | Emit `memory_write_persisted`, `conflict_detected`, `memory_backfill_complete` | Phase 5 precedent: `DeployRegressionDetected` same pattern [VERIFIED: clawteam/events/types.py:375-378] |
| `questionary` (existing) | >=2.0.1,<3.0.0 | `/setup-browser-cookies` wizard + `/design-shotgun` variant-pick prompt | Existing hard dep; `/setup-deploy` wizard precedent [VERIFIED: pyproject.toml; clawteam/templates/gstack/skills/setup_deploy/wizard.py] |

### Optional Extra (single new optional dep — matches STACK.md directive)

| Extra | Package | Version | Purpose | Gating |
|-------|---------|---------|---------|--------|
| `clawteam[browser]` | `playwright` | `>=1.58,<2` | Chromium driver for 3 browser skills + optional screenshot in `/design-shotgun` | `playwright_available()` helper; `SkillUnavailable` with install hint on missing [CITED: D-01] |

**Installation:**
```bash
pip install 'clawteam[browser]'
playwright install chromium  # user opt-in; never auto
```

**Version verification:** [VERIFIED: STACK.md line 30 states "Playwright >=1.58,<2 HIGH (PyPI verified)"]. Not re-verified against live registry this session — treat version pin as `[CITED: research/STACK.md §Optional Extras]`; Wave 0 plan-prep should `pip index versions playwright` to confirm current.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| JSONL memory | SQLite with schema | JSONL is grep-able + markdown-adjacent; SQLite is faster for >10K entries. Phase 6 is grep-first per STACK.md; sqlite-vec deferred to v2 |
| BoW cosine conflict detection | BERT / sentence-transformer | Adds 200MB model + runtime dep. Threshold tuning via `gstack.toml` knob good enough for v1 per D-10 |
| Playwright (our choice) | Puppeteer-python (pyppeteer) | Unmaintained; Playwright is Microsoft first-class [CITED: STACK.md line 44] |
| Central `playwright_available()` (our choice) | Per-skill `import playwright` guard | Central helper is testable via one monkeypatch; 3 skills share one call site [CITED: D-02] |

---

## Architecture Patterns

### System Architecture Diagram

```
                          ┌───────────────────────────┐
                          │  clawteam CLI / MCP surface
                          │  (existing)
                          └──────────┬────────────────┘
                                     ▼
    ┌─────────────────────────────────────────────────────────────┐
    │       GstackSprintPlugin.contribute_skills() (extended)       │
    │  7 existing (Phase 5) + 6 new (Phase 6) = 13 registrations   │
    └────────┬────────────────────────────────────────┬───────────┘
             │                                        │
             ▼                                        ▼
    ┌────────────────────────┐            ┌─────────────────────────┐
    │  SkillDispatcher        │            │  clawteam learn CLI     │
    │  (existing Phase 5)     │            │  (new Wave 3 Plan 06-07)│
    └────────┬────────────────┘            └────────┬────────────────┘
             │                                      │
             ▼                                      ▼
    ┌──────────────────────────────────────────────────────────────┐
    │   Phase 6 skill handlers                                      │
    │                                                                │
    │   browser:  /browse   /open-gstack-browser  /setup-browser-cookies
    │   design:   /design-shotgun (state machine)  /design-html     │
    │   memory:   /learn (write|list|search|prune|resolve|backfill) │
    └───┬────────────────┬─────────────────────┬────────────────────┘
        │                │                     │
        ▼                ▼                     ▼
  ┌──────────┐     ┌────────────┐     ┌─────────────────────┐
  │ clawteam │     │ fixtures   │     │ clawteam/memory/    │
  │ /browser/│     │ (design)   │     │  - entry.py         │
  │  adapter │     │            │     │  - store.py         │
  │  session │     │            │     │  - search.py        │
  │  cookies │     │            │     │  - conflict.py      │
  └───┬──────┘     └────────────┘     │  - decay.py         │
      │                               │  - backfill.py      │
      ▼                               └──────────┬──────────┘
  ┌───────────────────┐                          │
  │ playwright       │                          ▼
  │ (OPTIONAL — only │   ┌────────────────────────────────────────┐
  │  loaded when     │   │ ~/.clawteam/teams/<team>/              │
  │  extra installed)│   │   memory/                               │
  └───────────────────┘   │     team/<YYYY-MM>.jsonl               │
                          │     team/decisions/<YYYY-MM>.jsonl     │
                          │     team/pending/<id>.jsonl             │
                          │     agents/<role>/<YYYY-MM>.jsonl       │
                          │   browser/cookies/<domain>.json         │
                          │   _phase6_pending/<sprint>-retro.json   │
                          └────────────────────────────────────────┘
```

### Component Responsibilities

| File | Responsibility |
|------|---------------|
| `clawteam/browser/__init__.py` | `playwright_available()` feature-detect helper (import-guarded) |
| `clawteam/browser/adapter.py` | `sync_playwright` wrapper; navigate/click/fill/screenshot primitives |
| `clawteam/browser/session.py` | Cookie session load/persist; headed vs headless context factory |
| `clawteam/browser/cookies.py` | Cookie jar write/read with `file_locked` under `<team>/browser/cookies/<domain>.json` |
| `clawteam/memory/entry.py` | `MemoryEntry` pydantic model (Code Example 1) |
| `clawteam/memory/store.py` | `TeamMemoryStore(team_name)` with `write`/`list`/`search`/`prune` |
| `clawteam/memory/search.py` | Ranking function (Code Example 3); ripgrep detection |
| `clawteam/memory/conflict.py` | BoW cosine + sentiment opposition; returns `(similarity: float, contradicts: bool)` |
| `clawteam/memory/decay.py` | Per-tag TTL lookup; `decay_factor(entry, now)` pure function |
| `clawteam/memory/backfill.py` | `backfill_scan(team_name)` idempotent; walks `_phase6_pending/`; writes `.processed` sentinel |
| `clawteam/memory/events.py` (OR extend `clawteam/events/types.py`) | 3 new HarnessEvent dataclasses |
| `clawteam/templates/gstack/skills/browse/` | `/browse` skill sub-package (handler only) |
| `clawteam/templates/gstack/skills/open_gstack_browser/` | `/open-gstack-browser` skill sub-package |
| `clawteam/templates/gstack/skills/setup_browser_cookies/` | `/setup-browser-cookies` sub-package (handler + wizard.py mirroring setup_deploy) |
| `clawteam/templates/gstack/skills/design_shotgun/` | `/design-shotgun` state machine sub-package (handler + state.py) |
| `clawteam/templates/gstack/skills/design_html/` | `/design-html` sub-package (handler + framework_detect.py) |
| `clawteam/templates/gstack/skills/learn/` | `/learn` skill sub-package (handler delegates to TeamMemoryStore) |

### Pattern 1: Per-skill sub-package (Phase 4+5 precedent)

**What:** Every new skill = one sub-package under `clawteam/templates/gstack/skills/<slug>/` with `__init__.py` (re-exports handler + tool_available) + `handler.py` (the dispatcher entry) + optional `state.py`/`wizard.py`/`adapters.py`.
**When to use:** All 6 new Phase 6 skills.
**Example:** See `clawteam/templates/gstack/skills/codex/` (Phase 5 canonical minimal) or `clawteam/templates/gstack/skills/canary/` (handler + poller.py second module precedent).

### Pattern 2: State machine — ONLY `/design-shotgun`

**What:** Phase 4 `/office-hours` is the canonical state-machine skill (see `clawteam/templates/gstack/skills/office_hours/state.py`). `/design-shotgun` follows the same pattern: enum of states, transition table, `advance(event)` pure function, `state.json` persisted alongside sprint artifacts.
**When NOT to use:** The 5 other new skills (`/browse`, `/open-gstack-browser`, `/setup-browser-cookies`, `/design-html`, `/learn`) are linear pipelines or one-shot CLIs — NOT state machines. Pitfall 4 (Phase 5) locked the rule: `/ship`/`/land-and-deploy`/`/canary`/`/benchmark` are linear functions, not state machines. Only `/office-hours`, `/plan-design-review`, `/autoplan` are multi-turn state machines per QUALITY-07, and only `/design-shotgun` joins them in Phase 6.
**Example:** See Code Example 5 below (`/design-shotgun` state table).

### Pattern 3: Generic substrate at top-level, gstack-specific under templates/gstack/

**What:** `clawteam/browser/` and `clawteam/memory/` are GENERIC (could upstream). `clawteam/templates/gstack/skills/*` is gstack-specific. Precedent: Phase 5 D-03 locked this — `clawteam/spawn/invoke.py` is generic substrate, `clawteam/templates/gstack/skills/codex/` is gstack-specific.
**When to use:** Any new substrate that could plausibly serve a non-gstack template → top-level. Template-coupled UX → under `templates/gstack/skills/`.

### Anti-Patterns to Avoid

- **Don't import `playwright` at skill module load time.** Central `playwright_available()` import-guards the check. Skill handlers call the helper at runtime, NOT at import time. Would crash import if Playwright absent in a non-browser install. [CITED: D-02]
- **Don't hand-roll JSONL writes without `file_locked`.** Concurrent `/learn write` from parallel sprints will corrupt files. Every append path goes through `file_locked(target) + open(target, 'a').write(json.dumps(entry) + '\n')`.
- **Don't block on conflict.** D-10 says: write NOT blocked; conflict emits advisory event. Blocking would surprise users and slow the write path.
- **Don't auto-delete expired entries.** MEM-07 says: expired entries rank below unexpired, never deleted. Forensic recoverability matters.
- **Don't synthesize `MemoryEntry.id` from timestamp alone.** Use `mem-<team-slug>-<YYYYMMDD>-<hash6>` where hash6 is first 6 chars of SHA-256(body+tags+author). Collision-safe; grep-friendly.
- **Don't store Playwright artifacts (screenshots) inside JSONL.** JSONL is for text metadata; screenshots are binary files under `sprints/<id>/design-board/variant-<N>/` with a path ref in the entry's `evidence` field.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-turn prompt collection for cookie capture | Custom prompt loop | `questionary.text()` + `.select()` | Already in stack; /setup-deploy precedent |
| Interactive variant picker | Custom picker | `questionary.select()` with variant labels | Same |
| TOML read-modify-write for `gstack.toml [memory]`/`[design_shotgun]`/`[browser]` | Manual parsing | `tomllib.load()` + regex-splice (setup_deploy precedent) | Consistency with Phase 5 |
| Cosine similarity on bag-of-words | NumPy/scikit | `math.sqrt` + Counter | 2 entries × ~100 tokens is trivial; no numpy dep needed |
| Sentiment opposition heuristic | NLP library | Simple negation-word list + polarity-pair check (e.g., "prefer X" vs "avoid X"; "use X" vs "never X") | MVP detection; false-negatives acceptable per D-10 |
| Cookie jar serialization | Custom format | Playwright's own `context.cookies()` + `json.dumps()` | Playwright exposes serializable cookie list natively |
| Framework detection | AST parsing | `package.json` `dependencies`/`devDependencies` key check (react→svelte→vue order) | D-13 specifies this order; no code-walking needed |
| Backfill sentinel | Lock file | `.processed` empty file in `_phase6_pending/processed/<id>.processed` | Idempotency via mtime-ordered sentinel check |

**Key insight:** Memory substrate is a JSONL + markdown layer with transparent scoring. Every primitive a "real memory system" would pull from (vector index, embedding backend, NLP, ACID store) is replaced by stdlib + pydantic + `file_locked` + a documented formula. This preserves the "no new required deps" invariant and makes the v1 code PR-acceptable upstream.

---

## Code Examples

### Example 1: `MemoryEntry` pydantic schema ([CITED: D-04] + research elaboration for sub-fields)

```python
# clawteam/memory/entry.py
from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator
import re

_ID_RE = re.compile(r"^mem-[a-zA-Z0-9_-]+-\d{8}-[a-f0-9]{6}$")
_EVIDENCE_CITATION_RE = re.compile(r"^[^\0]+$")  # non-null; free-form path:line or ref

class MemoryEntry(BaseModel):
    """One memory entry (shared or per-role). Append-only to JSONL."""
    # Immutable identity
    id: str = Field(..., pattern=_ID_RE.pattern,
                    description="mem-<team>-<YYYYMMDD>-<6hex>")
    author: str = Field(..., min_length=1, max_length=200,
                        description="<role>@sprint-<id> or human@cli")
    sprint_id: str = Field(default="", max_length=200)
    phase: str = Field(default="", max_length=100)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Content
    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field(default="", max_length=20_000)
    tags: list[str] = Field(default_factory=list, max_length=32)

    # Provenance
    evidence: str = Field(default="",
                          description="path:line | artifact ref | URL; empty = flagged")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    learned_from: Literal["user", "artifact", "self-inferred", "sprint-reflect"]

    # Scoping
    scope: Literal["team", "role"] = "team"
    role: str | None = None  # required iff scope=="role"

    # Op (write | prune tombstone)
    op: Literal["write", "prune"] = "write"

    @field_validator("role")
    @classmethod
    def _role_presence_matches_scope(cls, v, info):
        scope = info.data.get("scope")
        if scope == "role" and not v:
            raise ValueError("scope='role' requires non-empty role")
        if scope == "team" and v:
            raise ValueError("scope='team' forbids role attribute")
        return v

    @field_validator("tags")
    @classmethod
    def _tags_lowercase_alnum(cls, tags):
        for t in tags:
            if not re.fullmatch(r"[a-z0-9:_-]+", t):
                raise ValueError(f"invalid tag {t!r}: lowercase alnum + : _ -")
        return tags
```

### Example 2: JSONL writer + month bucketing ([CITED: D-05])

```python
# clawteam/memory/store.py (excerpt — full version ~200 LOC)
from __future__ import annotations
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from clawteam.fileutil import file_locked
from clawteam.team.models import get_data_dir
from clawteam.paths import validate_identifier, ensure_within_root
from clawteam.memory.entry import MemoryEntry

_MEMORY_ROOT_KEY = "memory"

class TeamMemoryStore:
    def __init__(self, team_name: str) -> None:
        validate_identifier(team_name, "team name")
        self.team_name = team_name
        self._root = get_data_dir() / "teams" / team_name / _MEMORY_ROOT_KEY

    def _bucket_path(self, entry: MemoryEntry) -> Path:
        bucket = entry.timestamp[:7]  # YYYY-MM
        if entry.scope == "team":
            return self._root / "team" / f"{bucket}.jsonl"
        return self._root / "agents" / entry.role / f"{bucket}.jsonl"

    def _gen_id(self, author: str, title: str, tags: list[str]) -> str:
        payload = f"{author}|{title}|{','.join(sorted(tags))}"
        h = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:6]
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        slug = re.sub(r"[^a-zA-Z0-9_-]", "", self.team_name)[:24] or "team"
        return f"mem-{slug}-{date}-{h}"

    def write(self, entry: MemoryEntry) -> str:
        """Append entry to its month-bucketed JSONL. Returns entry.id."""
        bucket = self._bucket_path(entry)
        bucket.parent.mkdir(parents=True, exist_ok=True)
        # Path-traversal defense: resolve + verify stays under team root
        ensure_within_root(self._root, *bucket.relative_to(self._root).parts)
        payload = json.dumps(entry.model_dump(), ensure_ascii=False) + "\n"
        with file_locked(bucket):
            with bucket.open("a", encoding="utf-8") as fh:
                fh.write(payload)
                fh.flush()
                try:
                    import os as _os
                    _os.fsync(fh.fileno())  # durability
                except OSError:
                    pass  # tmpfs / network fs; best-effort
        return entry.id

    def prune(self, entry_id: str, *, scope: Literal["team", "role"], role: str | None = None) -> None:
        """Append a tombstone record — never mutate prior entries."""
        tombstone = MemoryEntry(
            id=entry_id,  # same id so retrieval can hide it
            author="system@prune",
            title=f"tombstone for {entry_id}",
            body="",
            tags=["tombstone"],
            evidence="",
            confidence=1.0,
            learned_from="user",
            scope=scope, role=role,
            op="prune",
        )
        self.write(tombstone)
```

### Example 3: Ranking formula ([CITED: D-06])

```python
# clawteam/memory/search.py (excerpt)
from __future__ import annotations
from datetime import datetime, timezone

# Per-tag TTL in days (MEM-07 + D-06)
_TTL_BY_TAG: dict[str, int] = {
    "pattern": 90,
    "preference": 365 * 100,  # effectively indefinite
    "incident": 180,
    "retro": 365,
    "decision": 365 * 5,
}
_DEFAULT_TTL_DAYS = 90

def recency_weight(ts: str, now: datetime) -> float:
    try:
        then = datetime.fromisoformat(ts)
    except ValueError:
        return 0.1  # malformed ts — deprioritize
    days = max(0.0, (now - then).total_seconds() / 86400.0)
    return 1.0 / (1.0 + days / 30.0)

def provenance_weight(entry) -> float:
    has_evidence = bool(entry.evidence)
    if entry.learned_from == "user" and has_evidence:
        return 2.0
    if entry.learned_from == "artifact" and has_evidence:
        return 1.0
    if entry.learned_from == "artifact" and not has_evidence:
        return 0.6  # flagged but not zeroed
    if entry.learned_from == "self-inferred":
        return 0.3
    # sprint-reflect (backfill)
    return 0.8

def decay_factor(entry, now: datetime) -> float:
    ttl = max((_TTL_BY_TAG.get(t, _DEFAULT_TTL_DAYS) for t in entry.tags), default=_DEFAULT_TTL_DAYS)
    try:
        then = datetime.fromisoformat(entry.timestamp)
    except ValueError:
        return 0.05
    days = (now - then).total_seconds() / 86400.0
    if days <= ttl:
        return 1.0
    if days <= 2 * ttl:
        return 0.2
    return 0.05  # never zero

def rank(entry, now: datetime) -> float:
    return recency_weight(entry.timestamp, now) * provenance_weight(entry) * decay_factor(entry, now)
```

### Example 4: Conflict detection — BoW cosine + negation heuristic ([CITED: D-10])

```python
# clawteam/memory/conflict.py
from __future__ import annotations
import re
from collections import Counter
from math import sqrt

_NEGATIONS = frozenset({"never", "avoid", "don't", "dont", "not", "stop", "refuse", "reject", "deprecated"})
_AFFIRMATIONS = frozenset({"always", "prefer", "use", "adopt", "embrace", "choose"})
_TOKEN_RE = re.compile(r"[a-z0-9]+")

def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())

def cosine_similarity(a: str, b: str) -> float:
    va, vb = Counter(_tokens(a)), Counter(_tokens(b))
    keys = set(va) | set(vb)
    if not keys:
        return 0.0
    dot = sum(va[k] * vb[k] for k in keys)
    na = sqrt(sum(v*v for v in va.values()))
    nb = sqrt(sum(v*v for v in vb.values()))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)

def sentiment_opposition(a_body: str, b_body: str) -> bool:
    """Return True if the two bodies express opposite sentiment on a shared subject.

    Heuristic: if one body contains a negation-keyword and the other contains
    an affirmation-keyword AND they overlap on >=2 content tokens, we call it
    opposition. False-positives are acceptable per D-10 (advisory-only).
    """
    a_toks = set(_tokens(a_body))
    b_toks = set(_tokens(b_body))
    shared_content = a_toks & b_toks - _NEGATIONS - _AFFIRMATIONS
    if len(shared_content) < 2:
        return False
    a_has_neg = bool(a_toks & _NEGATIONS)
    a_has_aff = bool(a_toks & _AFFIRMATIONS)
    b_has_neg = bool(b_toks & _NEGATIONS)
    b_has_aff = bool(b_toks & _AFFIRMATIONS)
    # one negates, the other affirms
    return (a_has_neg and b_has_aff) or (a_has_aff and b_has_neg)

def detect_conflict(new_entry, candidate_entries, threshold: float) -> tuple[str, float] | None:
    """Return (conflicting_id, similarity) if the new entry contradicts any candidate."""
    if not new_entry.tags:
        return None
    new_tag_set = set(new_entry.tags)
    for cand in candidate_entries:
        if not (set(cand.tags) & new_tag_set):
            continue
        if cand.scope != new_entry.scope:
            continue
        sim = cosine_similarity(new_entry.body, cand.body)
        if sim >= threshold and sentiment_opposition(new_entry.body, cand.body):
            return (cand.id, sim)
    return None
```

### Example 5: `/design-shotgun` state transition table ([CITED: D-12])

```python
# clawteam/templates/gstack/skills/design_shotgun/state.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

class DSState(str, Enum):
    INITIALIZED = "initialized"
    VARIANTS_GENERATING = "variants_generating"
    BOARD_RENDERED = "board_rendered"
    USER_PICKING = "user_picking"
    REFINING = "refining"
    CONVERGED = "converged"
    ABANDONED = "abandoned"

class DSEvent(str, Enum):
    GENERATE_REQUESTED = "generate_requested"
    VARIANTS_READY = "variants_ready"
    BOARD_PUBLISHED = "board_published"
    USER_PICKED = "user_picked"
    REFINE_REQUESTED = "refine_requested"
    CONVERGE = "converge"
    ABANDON = "abandon"

# (from_state, event) -> to_state. Missing key => illegal transition.
TRANSITIONS: dict[tuple[DSState, DSEvent], DSState] = {
    (DSState.INITIALIZED, DSEvent.GENERATE_REQUESTED): DSState.VARIANTS_GENERATING,
    (DSState.VARIANTS_GENERATING, DSEvent.VARIANTS_READY): DSState.BOARD_RENDERED,
    (DSState.BOARD_RENDERED, DSEvent.BOARD_PUBLISHED): DSState.USER_PICKING,
    (DSState.USER_PICKING, DSEvent.USER_PICKED): DSState.REFINING,
    (DSState.REFINING, DSEvent.REFINE_REQUESTED): DSState.VARIANTS_GENERATING,  # loop
    (DSState.REFINING, DSEvent.CONVERGE): DSState.CONVERGED,
    (DSState.INITIALIZED, DSEvent.ABANDON): DSState.ABANDONED,
    (DSState.VARIANTS_GENERATING, DSEvent.ABANDON): DSState.ABANDONED,
    (DSState.BOARD_RENDERED, DSEvent.ABANDON): DSState.ABANDONED,
    (DSState.USER_PICKING, DSEvent.ABANDON): DSState.ABANDONED,
    (DSState.REFINING, DSEvent.ABANDON): DSState.ABANDONED,
}

@dataclass
class VariantFixture:
    """4-variant fixture schema (D-17)."""
    variant_id: str  # "variant-1" .. "variant-N"
    title: str
    description: str
    html_path: str  # relative: "sprints/<sid>/design-board/variant-1/index.html"
    screenshot_path: str = ""  # optional; Playwright-generated on render
    design_tokens: dict[str, str] = field(default_factory=dict)

@dataclass
class ShotgunState:
    state: DSState = DSState.INITIALIZED
    sprint_id: str = ""
    variant_count: int = 4
    variants: list[VariantFixture] = field(default_factory=list)
    picked_variant_id: str = ""
    pick_reason: str = ""
    iteration: int = 0  # incremented on REFINE_REQUESTED loop

    def advance(self, event: DSEvent, **data) -> "ShotgunState":
        key = (self.state, event)
        if key not in TRANSITIONS:
            raise ValueError(f"illegal transition {self.state} + {event}")
        new_state = TRANSITIONS[key]
        # Pure return — caller persists via state.json
        return ShotgunState(
            state=new_state,
            sprint_id=self.sprint_id,
            variant_count=self.variant_count,
            variants=data.get("variants", self.variants),
            picked_variant_id=data.get("picked_variant_id", self.picked_variant_id),
            pick_reason=data.get("pick_reason", self.pick_reason),
            iteration=self.iteration + (1 if new_state == DSState.VARIANTS_GENERATING and self.iteration else 0),
        )
```

### Example 6: `pyproject.toml` `[project.optional-dependencies]` block ([CITED: D-01])

```toml
[project.optional-dependencies]
dev = [
    "pytest>=9.0.0,<10.0.0",
    "ruff>=0.1.0",
    "pyyaml>=6.0,<7.0",
]
p2p = [
    "pyzmq>=25.0.0,<27.0.0",
]
# Phase 6 Wave 0 (D-01): headless Chromium for /browse, /open-gstack-browser,
# /setup-browser-cookies, and optional screenshotting in /design-shotgun.
# Post-install step: `playwright install chromium` (user opt-in; never auto).
browser = [
    "playwright>=1.58,<2",
]
```

### Example 7: `playwright_available()` helper ([CITED: D-02])

```python
# clawteam/browser/__init__.py
"""Generic browser substrate (Phase 6 Wave 0, D-02/D-03).

Import-guarded feature detection so skill modules never crash on
missing Playwright. Tests monkeypatch this single helper instead of
patching `import playwright` in N skill modules.
"""
from __future__ import annotations
from importlib.util import find_spec

def playwright_available() -> bool:
    """Return True if the `playwright` package is importable.

    Uses `importlib.util.find_spec` — zero import-time side effects.
    Does NOT verify that Chromium itself is installed (a separate
    `playwright install chromium` step). Skills probe Chromium
    availability lazily at handler-call time via `sync_playwright()`.
    """
    return find_spec("playwright") is not None

__all__ = ["playwright_available"]
```

### Example 8: `memory-confirm-<id>.md` question template ([CITED: CONTEXT.md §specifics])

```markdown
---
question_id: memory-confirm-{id}
priority: blocking
scope: {team|role}
author: {role}@sprint-{sprint_id}
---

# Memory write: high-impact confirmation required

**Entry id:** {id}
**Scope:** {scope}
**Tags:** {tags joined ", "}
**Author:** {author}
**Evidence:** {evidence or "(none — flagged for lower retrieval rank)"}
**Confidence:** {confidence}

## Preview

> {body first 500 chars, quote-prefixed}

## Options

1. **Confirm** — promote to `memory/{scope}/{year-month}.jsonl` (permanent)
2. **Edit** — revise body/tags before confirming (reply with edited YAML body)
3. **Reject** — discard; tombstone written to `memory/{scope}/pending/` with `op: rejected`

Reply in `answers/memory-confirm-{id}.md` with `choice: confirm|edit|reject` in frontmatter.
```

### Example 9: Event dataclasses ([CITED: Phase 5 precedent + D-10])

```python
# Added to clawteam/events/types.py (mirroring Phase 5 Plan 05-02 pattern)
@dataclass
class MemoryWritePersisted(HarnessEvent):
    """A new MemoryEntry was appended to JSONL (advisory; Phase 7 cost dashboard)."""
    entry_id: str = ""
    scope: str = ""  # "team" or "role"
    role: str = ""
    tags: list[str] = field(default_factory=list)
    high_impact: bool = False

@dataclass
class ConflictDetected(HarnessEvent):
    """Two entries contradict on same tag (D-10). Advisory — write NOT blocked."""
    new_entry_id: str = ""
    conflicting_entry_id: str = ""
    similarity: float = 0.0
    shared_tags: list[str] = field(default_factory=list)
    scope: str = ""

@dataclass
class MemoryBackfillComplete(HarnessEvent):
    """Backfill scanner finished promoting _phase6_pending/ entries (D-11)."""
    team: str = ""
    entries_promoted: int = 0
    entries_skipped_already_processed: int = 0

register_event_type(MemoryWritePersisted)
register_event_type(ConflictDetected)
register_event_type(MemoryBackfillComplete)
```

---

## Per-Decision + Per-Skill Implementation Map

| Decision | Files touched | Test touchpoint |
|----------|--------------|-----------------|
| D-01 pyproject extra | `pyproject.toml` (add `browser` extra) | `tests/test_pyproject_optional_extras.py::test_browser_extra_present` |
| D-02 `playwright_available()` | `clawteam/browser/__init__.py` (new) | `tests/browser/test_feature_detection.py::{test_available_when_installed,test_unavailable_when_missing}` |
| D-03 substrate split | `clawteam/browser/{adapter,session,cookies}.py` + `clawteam/templates/gstack/skills/{browse,open_gstack_browser,setup_browser_cookies,design_shotgun,design_html}/` | per-skill tests under `tests/templates/gstack/skills/test_<slug>.py` |
| D-04 TeamMemoryStore | `clawteam/memory/store.py` + `entry.py` | `tests/memory/test_store_write_read.py` (3 min per D-14) |
| D-05 JSONL + month buckets | `clawteam/memory/store.py::_bucket_path` + `write` | `tests/memory/test_store_write_read.py::test_month_bucketing` |
| D-06 grep-first + ranking | `clawteam/memory/search.py` | `tests/memory/test_search_ranking.py::{test_recency,test_provenance,test_decay}` |
| D-07 role-agnostic `/learn` | `clawteam/templates/gstack/skills/learn/handler.py` (no roles gate restriction — `roles=frozenset(GSTACK_ROLES)`) | `tests/templates/gstack/skills/test_learn.py::test_role_agnostic` |
| D-08 CLI signature | `clawteam/cli/commands.py` (new `learn_app` subcommand group) | `tests/cli/test_learn_cli.py::test_write_signature_accepts_all_flags` |
| D-09 high-impact gate | `clawteam/memory/store.py::write` branches to `_stage_pending` when impact:high OR `scope=team/decisions` | `tests/memory/test_high_impact_gate.py::{test_staged_not_committed,test_confirmation_promotes,test_rejection_discards}` |
| D-10 conflict detection | `clawteam/memory/conflict.py` + `store.py::write` integration | `tests/memory/test_conflict.py::{test_cosine_above_threshold,test_sentiment_opposition,test_threshold_configurable,test_write_not_blocked}` |
| D-11 backfill scanner | `clawteam/memory/backfill.py::backfill_scan(team)` invoked from `/learn` handler first-call | `tests/memory/test_backfill.py::{test_promotes_phase6_pending,test_idempotent_on_rerun,test_emits_complete_event}` |
| D-12 `/design-shotgun` state machine | `clawteam/templates/gstack/skills/design_shotgun/{state.py,handler.py}` | `tests/templates/gstack/skills/test_design_shotgun.py` (fixtures under `tests/fixtures/design_shotgun/`) |
| D-13 `/design-html` framework detect | `clawteam/templates/gstack/skills/design_html/{handler.py,framework_detect.py}` | `tests/templates/gstack/skills/test_design_html.py::{test_detect_react,test_detect_svelte,test_detect_vue,test_detect_plain,test_multi_framework_asks_question}` |
| D-14 memory test count | (test files above, 3 min each) | enforced by pytest collection count |
| D-15 per-team isolation | `clawteam/memory/store.py::__init__` path validation; `tests/memory/test_cross_team_isolation.py` | `test_cross_team_isolation.py::{test_team_a_cannot_read_team_b,test_path_traversal_rejected}` |
| D-16 browser mock tests | `tests/browser/test_adapter.py` + `tests/templates/gstack/skills/test_browse.py` monkeypatch `sync_playwright` | See test files |
| D-17 design fixtures | `tests/fixtures/design_shotgun/{variant-1..4}/index.html` + `picked.json` | Referenced by `test_design_shotgun.py` |

### Per-skill implementation map

| Skill | Handler path | Key helpers | Plugin entry | Test file |
|-------|-------------|------------|--------------|-----------|
| `/browse` | `clawteam/templates/gstack/skills/browse/handler.py` | `clawteam/browser/adapter.py::navigate_and_screenshot` | `SkillRegistration(name="/browse", roles=frozenset({"engineer","qa","dx-lead"}), handler=browse_handler, tool_available=playwright_available, install_hint="pip install 'clawteam[browser]' && playwright install chromium")` | `tests/templates/gstack/skills/test_browse.py` |
| `/open-gstack-browser` | `.../open_gstack_browser/handler.py` | `clawteam/browser/session.py::open_headed_with_context` | `SkillRegistration(name="/open-gstack-browser", roles=frozenset({"engineer","qa","dx-lead","designer"}), handler=open_browser_handler, tool_available=playwright_available, install_hint=<same>)` | `test_open_gstack_browser.py` |
| `/setup-browser-cookies` | `.../setup_browser_cookies/{handler.py,wizard.py}` | `clawteam/browser/cookies.py::save_cookies_for_domain` + `questionary` | `SkillRegistration(name="/setup-browser-cookies", roles=frozenset({"engineer","qa","dx-lead"}), handler=setup_cookies_handler, tool_available=playwright_available, install_hint=<same>)` | `test_setup_browser_cookies.py` |
| `/design-shotgun` | `.../design_shotgun/{handler.py,state.py}` | `state.ShotgunState.advance` + `clawteam/browser/adapter.py` (optional screenshot) + `TeamMemoryStore` (taste write) | `SkillRegistration(name="/design-shotgun", roles=frozenset({"designer"}), handler=shotgun_handler, tool_available=None, install_hint="")` — renders HTML always works; screenshots only if browser extra present | `test_design_shotgun.py` |
| `/design-html` | `.../design_html/{handler.py,framework_detect.py}` | pure filesystem + `package.json` parse | `SkillRegistration(name="/design-html", roles=frozenset({"designer"}), handler=design_html_handler, tool_available=None, install_hint="")` | `test_design_html.py` |
| `/learn` | `.../learn/handler.py` | delegates to `clawteam/memory/store.py` + `clawteam/memory/backfill.py` | `SkillRegistration(name="/learn", roles=frozenset(GSTACK_ROLES), handler=learn_handler, tool_available=None, install_hint="")` | `test_learn.py` |

---

## Plan-Prep Verifications (A1..A9 — VERIFIED against actual code 2026-04-22)

| ID | Verification | Status | Evidence |
|----|--------------|--------|----------|
| **A1** | `pyproject.toml` has `[project.optional-dependencies]` table | **CONFIRMED** | `pyproject.toml` lines 30-46 show `[project.optional-dependencies]` with `dev` + `p2p` extras. Wave 0 plan appends `browser = ["playwright>=1.58,<2"]`. No new table creation needed. |
| **A2** | `clawteam doctor` detects chromium | **CONFIRMED** | `clawteam/cli/commands.py:37` `_DOCTOR_TOOLS` row `("chromium (Playwright)", "python-pkg", "playwright")`. `_doctor_install_hint` at line 56-60 has install hint per-OS. No additional doctor wiring needed for Chromium. Phase 6 Wave 0 can skip doctor-row additions. |
| **A3** | HarnessEvent + `register_event_type` pattern | **CONFIRMED** | `clawteam/events/types.py:14` `HarnessEvent` dataclass; `types.py:375-378` Phase 5 `register_event_type(DeployRegressionDetected)` + `WebVitalRegressionDetected` via bottom-of-module late import pattern. Phase 6 appends 3 more at bottom. |
| **A4** | `GstackSprintPlugin.contribute_skills()` returns 7 registrations currently; Phase 6 extends to 13 | **CONFIRMED** | `clawteam/plugins/gstack_sprint_plugin.py:154-257` `contribute_skills` returns exactly 7: /codex, /ship, /setup-deploy, /land-and-deploy, /document-release, /canary, /benchmark. Phase 6 adds 6 → 13 total. |
| **A5** | `atomic_append_line` helper exists OR `file_locked + open("a") + fsync` pattern | **ADJUSTED — no `atomic_append_line` exists** | `clawteam/fileutil.py:28-84` provides `atomic_write_text` (replace-semantics, mkstemp + os.replace) + `file_locked` (fcntl/msvcrt advisory lock). **No dedicated append helper.** Phase 6 Wave 1 uses `file_locked(bucket) + open("a") + fh.write + fh.flush + os.fsync` pattern inline in `TeamMemoryStore.write()` (see Code Example 2). Mirror into `clawteam/memory/store.py::_append_jsonl` as a private helper to avoid scattering the pattern — do NOT export as public utility yet (can be lifted to `fileutil.py` later if reused). |
| **A6** | Reflect handler writes `_phase6_pending/<sprint>-retro.json` | **CONFIRMED** | `clawteam/plugins/gstack_sprint_plugin.py:534-588` `_write_phase6_pending` method writes `<data_dir>/teams/<team>/_phase6_pending/<sprint>-retro.json`. Phase 6 Wave 4 `backfill.py::backfill_scan` consumes this exact path + shape. |
| **A7** | `gstack.toml` TemplateDef accepts unknown `[memory]`/`[design_shotgun]`/`[browser]` sub-blocks | **PARTIAL / ADJUSTED** | Phase 5 D-07 added `ShipConfig`/`DeployConfig`/`CanaryConfig`/`BenchmarkConfig` sub-blocks via `_parse_toml` reading `raw.get("ship")`, etc. (see `clawteam/templates/__init__.py:262-266`). But `TemplateDef` is a strict pydantic model — **unknown top-level keys raise ValidationError unless we extend `_parse_toml`**. Phase 6 Wave 0 MUST add `MemoryConfig`, `DesignShotgunConfig`, `BrowserConfig` pydantic models + `_parse_toml` reads for `raw.get("memory")`, `raw.get("design_shotgun")`, `raw.get("browser")` following the Phase 5 exact pattern. BC safety via `None` default. |
| **A8** | `InteractionGate` constructor accepts dynamic question path | **CONFIRMED** | `clawteam/harness/interaction_gate.py:67` `InteractionGate(sprint_dir: Path \| None = None)`. Pairs `questions/<id>.md` ↔ `answers/<id>.md` by stem. For Phase 6 D-09 memory-confirm: write `questions/memory-confirm-<id>.md`; wait for `answers/memory-confirm-<id>.md`. No subclass needed — direct reuse. |
| **A9** | `questionary` in stack | **CONFIRMED** | `pyproject.toml:25` `questionary>=2.0.1,<3.0.0` is a HARD dep. Used by `clawteam/cli/commands.py` + `clawteam/templates/gstack/skills/setup_deploy/wizard.py`. `/setup-browser-cookies` + `/design-shotgun` variant-pick reuse. Note: not locally importable via `python3 -c "import questionary"` in this bare env — that's because the project's venv isn't active in the shell, not because the dep is missing. |

---

## Common Pitfalls

### Pitfall 1: Importing Playwright at module load
**What goes wrong:** Any `import playwright` at module-top in `clawteam/templates/gstack/skills/browse/handler.py` crashes import on machines without the extra.
**Why it happens:** Python's import system resolves top-level imports eagerly.
**How to avoid:** Use `importlib.util.find_spec` in `playwright_available()` helper (Code Example 7) and `from playwright.sync_api import sync_playwright` INSIDE function bodies that actually need it. Mirror Phase 5 `/canary` handler's `lazy-import Playwright` precedent (see `clawteam/templates/gstack/skills/canary/handler.py` line 28 `find_spec` pattern).
**Warning signs:** Import-time `ModuleNotFoundError: No module named 'playwright'` surfacing before skill dispatch.

### Pitfall 2: Memory JSONL race on parallel writes
**What goes wrong:** Two agents writing simultaneously to `memory/team/2026-04.jsonl` interleave partial lines.
**Why it happens:** POSIX `O_APPEND` is atomic up to `PIPE_BUF` bytes (~4096) but `MemoryEntry` with 20KB body can exceed that.
**How to avoid:** Always `with file_locked(bucket):` around the write. `file_locked` takes an exclusive advisory lock via `fcntl.LOCK_EX` on Linux / `msvcrt.locking` on Windows.
**Warning signs:** Malformed JSONL lines in the file; entries merged with no separator.

### Pitfall 3: Path traversal via `team_name` or `role`
**What goes wrong:** `team_name="../otherteam"` lets team A read team B's memory.
**Why it happens:** Attacker-controlled strings concatenated into filesystem paths.
**How to avoid:** Every `TeamMemoryStore` API gate through `clawteam.paths.validate_identifier` + `ensure_within_root`. The `__init__` validates `team_name` once; `write()` re-validates the computed `bucket` stays under `self._root` via `ensure_within_root`.
**Warning signs:** Cross-team integration test (D-15) fails.

### Pitfall 4: Blocking the write on conflict detection
**What goes wrong:** User's `/learn write` hangs or raises when a similar entry already exists.
**Why it happens:** Interpreting conflict as a fail-closed event.
**How to avoid:** D-10 explicitly says "write is NOT blocked" — emit `ConflictDetected` event as advisory, let the write proceed, surface the conflict through the agent's output channel and optionally through `clawteam attend` later.
**Warning signs:** `/learn write` returns non-zero on conflict.

### Pitfall 5: Expiring entries by deleting them
**What goes wrong:** Losing forensic context on why a decision was made 6 months ago.
**Why it happens:** Intuitive "clean up stale data" instinct.
**How to avoid:** MEM-07 locks the rule — expired entries rank below unexpired (decay_factor drops to 0.2 then 0.05) but are NEVER auto-deleted. Search results for long queries still surface them, just at the bottom.
**Warning signs:** Audit trail gap; user says "but I told the team last quarter".

### Pitfall 6: Auto-running `playwright install chromium`
**What goes wrong:** `pip install 'clawteam[browser]'` triggers a 500 MB Chromium download without user consent.
**Why it happens:** Tempting to chain `post-install` hook.
**How to avoid:** D-01 locks it — `pip install` only pulls the Python wheel (~10 MB). User runs `playwright install chromium` separately. `clawteam doctor` surfaces the one-liner in install hints.
**Warning signs:** First-time `pip install` takes >1 minute.

### Pitfall 7: High-impact gate blocking on absent human
**What goes wrong:** `/learn write --impact high` hangs forever waiting for a sprint answer file that never arrives.
**Why it happens:** Treating the confirmation as synchronous.
**How to avoid:** D-09 stages entry to `memory/<scope>/pending/<id>.jsonl` and returns immediately. The pending entry can be resolved later via `clawteam learn --resolve <id>` or on next sprint when human answers the question.md. Never block the skill handler's return.
**Warning signs:** `/learn write` times out; sprint progress stalls.

### Pitfall 8: Framework detection picks wrong target in monorepo
**What goes wrong:** Monorepo with React host + Svelte island → `/design-html` silently emits React by detection order.
**Why it happens:** D-13's detect order (`react` → `svelte` → `vue`) is a race, not a ranking.
**How to avoid:** D-13 specifies: multiple frameworks present → emit `question.md` asking which. Always ask when ambiguous; never guess.
**Warning signs:** Designer complains "this HTML is for the wrong project".

### Pitfall 9: Backfill scanner double-processing on re-run
**What goes wrong:** Second `/learn` call re-imports the same retro entries, creating duplicates.
**Why it happens:** No idempotency check.
**How to avoid:** D-11 specifies `.processed` sentinel file per retro in `_phase6_pending/processed/<sprint>-retro.processed`. On re-run, skip already-processed entries. Emit `MemoryBackfillComplete` with both counts (promoted + skipped).
**Warning signs:** Duplicate entries in `memory/team/retros/`.

---

## Runtime State Inventory

Phase 6 is additive — adds new files under `~/.clawteam/teams/<team>/memory/` + `browser/cookies/` but renames nothing.

| Category | Items | Action |
|----------|-------|--------|
| Stored data | New: `~/.clawteam/teams/<team>/memory/{team,agents,pending}/*.jsonl`. Consumes (promotes) existing `_phase6_pending/*.json` written by Phase 3 Reflect handler. | Wave 1 creates dirs on first `TeamMemoryStore(team_name)`; Wave 4 promotes existing `_phase6_pending/` via backfill — no data migration |
| Live service config | None — Phase 6 has no external service registrations. | — |
| OS-registered state | None — no Task Scheduler/launchd entries. | — |
| Secrets/env vars | None added. Cookies live under `browser/cookies/` as JSON files — per STACK.md explicitly "not secrets" in v1 (user cookies for their own dev env). | — (future v2 may add keyring for cross-machine sync) |
| Build artifacts / installed packages | `playwright` wheel when `[browser]` extra installed; Chromium binary under `~/.cache/ms-playwright/` after `playwright install chromium`. | Neither auto-managed; documented via `clawteam doctor` |

**Nothing found in category:** Live service config / OS-registered / secrets — explicitly verified nothing exists (Phase 3 + Phase 5 did not emit to any of these categories; Phase 6 matches).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| `playwright` (Python) | 3 browser skills + optional `/design-shotgun` screenshot | ✗ (not in this env) | — | `SkillUnavailable` with install hint; `/design-shotgun` renders HTML only (no screenshots) |
| `questionary` | `/setup-browser-cookies` wizard + `/design-shotgun` pick | ✓ (hard dep per pyproject.toml) | >=2.0.1,<3 | — |
| `ripgrep` (optional, speeds up `/learn search`) | `clawteam/memory/search.py` | system-dependent | any | stdlib `re.search` over JSONL (slower but always works) |
| `pydantic` | `MemoryEntry` + event dataclasses | ✓ (hard dep) | >=2.0,<3 | — |
| `tomllib`/`tomli` | `gstack.toml [memory]` parsing | ✓ | stdlib 3.11+ / tomli 3.10 | — |

**Missing dependencies with no fallback:** None — Phase 6 is designed so every feature has a usable fallback when Playwright absent.

**Missing dependencies with fallback:** `playwright` → skills return `SkillUnavailable`; `ripgrep` → stdlib `re`.

---

## State of the Art

| Old approach | Current approach | When changed | Impact |
|--------------|------------------|--------------|--------|
| Sync `playwright` API | Sync API still canonical for CLI tools; async API for web servers | Playwright 1.0+ | We use `sync_playwright` — matches CLI + test monkeypatch patterns |
| Puppeteer-python (pyppeteer) | Playwright-python | 2022+ | Unmaintained; Playwright is Microsoft first-class |
| Cosine on TF-IDF | Embeddings + vector search | Deferred to v2 per STACK.md | Phase 6 uses BoW cosine — simpler, transparent, no new deps |
| SQLite-backed memory | JSONL + month buckets | Phase 6 chose JSONL | Grep-friendly; human-readable; trivially portable |

**Deprecated/outdated:** `pyppeteer`, `playwright-stealth` (author warns not robust) — both excluded per STACK.md.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Playwright 1.58+ Python package spans >=1.58,<2 range | Standard Stack | If upstream breaks API in 1.59+, skills break. Mitigation: pin upper bound at <2; Wave 0 `pip index versions playwright` sanity-check. |
| A2 | BoW cosine > 0.75 threshold is reasonable default for conflict detection | Code Example 4 / D-10 | False-positive or false-negative rate unknown; configurable via `gstack.toml [memory] conflict_threshold` so users can tune |
| A3 | Sentiment-opposition heuristic (negation vs affirmation word lists) catches >50% of real conflicts | Code Example 4 | Weak classifier; false-negatives acceptable per D-10 (advisory-only). If bad in practice, v2 can swap to BERT. |
| A4 | TTL defaults (pattern 90d, preference indefinite, incident 180d) match team-mental-model | Code Example 3 / D-06 | Subjective; configurable via `gstack.toml [memory] retention_*_days` |
| A5 | `sha256(body+tags+author)[:6]` is collision-resistant enough across a team's lifetime | Code Example 2 | ~16M collisions possible over 16M entries per day per team — accepted for v1 |
| A6 | `fsync` after each append is durable enough; not needed every write | Code Example 2 | Performance hit on slow FS; we call fsync best-effort (try/except on OSError) |
| A7 | Designer's per-role memory is the right scope for `/design-shotgun` taste observations | D-12 + SKILL-11 | If team wants shared taste, designer can manually `/learn write team --tags design,taste`. Default per-role matches "taste is individual" model |
| A8 | Plain-HTML fallback = `index.html + styles.css + app.js` triple | D-13 discretion | Conventional; if user prefers single-file HTML, they edit output |

All other claims are `[VERIFIED: <source>]` against code in this repository or `[CITED: <CONTEXT.md decision>]`.

---

## Open Questions

1. **Should `/design-shotgun` variant generation be real-LLM-driven in v1 or template-fixture-driven?**
   - What we know: D-17 says tests use fixtures. Production behavior unspecified.
   - What's unclear: Does `/design-shotgun` in live use generate 4 variants via LLM prompt, or does it shell out to another skill (e.g., `/design-consultation`)?
   - Recommendation: Wave 3 plan assumes designer agent's own LLM (the turn's model) generates the HTML bodies, the state machine only orchestrates transitions + file I/O. If wrong, refactor is local to `shotgun_handler._generate_variants`.

2. **Should `/learn search` output include the score breakdown by default, or only with `--explain`?**
   - What we know: D-06 specifies the formula; CONTEXT.md §specifics shows `--explain` output.
   - Recommendation: default JSON output includes `score` only; `--explain` adds `recency`/`provenance`/`decay` component columns. Documented in Plan 06-07.

3. **On `/learn prune`, should the tombstone record itself be subject to the high-impact gate?**
   - What we know: D-09 gates high-impact WRITES; D-05 says prune = tombstone append.
   - Recommendation: Pruning is recoverable (original entry still in JSONL; tombstone just hides it at search time), so do NOT gate prunes. Tombstones bypass the high-impact gate even if the original entry was `impact:high`. Add an explicit rule in `TeamMemoryStore.prune`.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.x (existing, per `pyproject.toml:32`) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` (testpaths = ["tests"]) |
| Quick run command | `pytest tests/memory/ tests/browser/ tests/templates/gstack/skills/test_<slug>.py -x -q` |
| Full suite command | `pytest -q` |
| Phase gate command | `pytest tests/ -q && pytest tests/test_template_regression_matrix.py -q` (BC matrix) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | Plan |
|--------|----------|-----------|-------------------|------|
| MEM-01 | Two-tier layout exists | unit | `pytest tests/memory/test_store_write_read.py::test_two_tier_layout -x` | 06-02 |
| MEM-02 | JSONL append + frontmatter fields | unit | `pytest tests/memory/test_store_write_read.py::test_appends_with_frontmatter -x` | 06-02 |
| MEM-03 | Grep-first retrieval | unit | `pytest tests/memory/test_search_ranking.py -x` | 06-03 |
| MEM-04 | `/learn` 4 verbs | unit + integration | `pytest tests/templates/gstack/skills/test_learn.py tests/cli/test_learn_cli.py -x` | 06-07 |
| MEM-05 | Provenance ranking | unit | `pytest tests/memory/test_search_ranking.py::test_provenance_weight -x` | 06-03 |
| MEM-06 | High-impact gate | integration | `pytest tests/memory/test_high_impact_gate.py -x` | 06-09 |
| MEM-07 | TTL decay | unit | `pytest tests/memory/test_search_ranking.py::test_decay_factor -x` | 06-03 |
| SKILL-10 | 3 browser skills | per-skill | `pytest tests/templates/gstack/skills/test_browse.py test_open_gstack_browser.py test_setup_browser_cookies.py -x` | 06-04, 06-05, 06-06 |
| SKILL-11 | `/design-shotgun` state machine | per-skill + state | `pytest tests/templates/gstack/skills/test_design_shotgun.py -x` | 06-08 |
| SKILL-12 | `/design-html` framework detect | per-skill | `pytest tests/templates/gstack/skills/test_design_html.py -x` | 06-08 |
| QUALITY-10 | Memory poisoning defense | integration | `pytest tests/memory/test_high_impact_gate.py tests/memory/test_conflict.py tests/memory/test_search_ranking.py::test_decay_factor -x` | 06-09 + 06-11 |
| D-15 | Per-team isolation | integration | `pytest tests/memory/test_cross_team_isolation.py -x` | 06-02 + 06-11 |

### Sampling Rate
- **Per task commit:** `pytest tests/memory/ -x -q` (~5s) or `pytest tests/templates/gstack/skills/test_<slug>.py -x -q` (~2s)
- **Per wave merge:** `pytest tests/memory/ tests/browser/ tests/templates/gstack/skills/ tests/cli/ -q` (~30s)
- **Phase gate:** `pytest -q` full suite + `pytest tests/test_template_regression_matrix.py -q` (BC matrix QUALITY-14)

### Wave 0 Gaps
- [ ] `tests/memory/` directory — does not yet exist; Wave 0 `conftest.py` optional (most tests use tmp_path fixture)
- [ ] `tests/browser/` directory — does not yet exist
- [ ] `tests/fixtures/design_shotgun/variant-{1..4}/index.html` — create in Plan 06-08 as test fixtures (D-17)

*(No framework install needed — pytest 9.x already in dev-extras.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No user auth introduced in Phase 6 |
| V3 Session Management | partial | Browser session/cookie handling (D-03); cookies stored under `<team>/browser/cookies/<domain>.json` with `file_locked` — user-scoped not cross-machine |
| V4 Access Control | yes | Per-team memory isolation (D-15); path traversal defense via `validate_identifier` + `ensure_within_root` |
| V5 Input Validation | yes | `MemoryEntry` pydantic model validates every write; tag regex; scope literal; role coupling via `field_validator` |
| V6 Cryptography | no | No new crypto; cookies stored plain JSON (documented as user-machine-scoped) |
| V12 Files | yes | JSONL writes via `file_locked + atomic` pattern; browser cookie files under team data-dir (`ensure_within_root` guarded) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Cross-team memory leak via `team_name="../otherteam"` | Tampering / Info Disclosure | `validate_identifier` rejects `/`, `..`, `\`; `ensure_within_root` double-check at bucket path |
| JSONL corruption via interleaved writes | Tampering | `file_locked` + `fsync` (see Pitfall 2 / Code Example 2) |
| Memory poisoning via self-inferred bad patterns | Spoofing / Integrity | Provenance-weighted ranking (D-06 weight 0.3); high-impact gate (D-09); conflict detection (D-10); decay (D-06/MEM-07) |
| Cookie theft via `cookies_dir` path traversal | Info Disclosure | Domain argument goes through `validate_identifier` (alphanumeric + `.` only for domain); write via `ensure_within_root` |
| Shell injection in `/design-html` framework detect | Tampering | Read-only `package.json` JSON parse; no subprocess call; no user-string concatenation into shell |
| Playwright page.content() exfiltrating unrelated env | Info Disclosure | Headless browser launched via existing `scrub_env`-like pattern; `/browse` never opens `file://` URLs (reject in handler) |
| JSONL file bloat DoS | DoS | Month-bucketed (one file ≤ 31 days of entries); `body` capped at 20KB pydantic; `tags` capped at 32 |

---

## Wave Structure Recommendation

5 waves, 12 plans. Plans can execute in parallel within a wave (no cross-plan file conflicts per wave).

### Wave 0 — Plan-prep + optional extra + top-level packages (1 plan)

- **06-01-PLAN.md** (Wave 0) — `pyproject.toml [browser]` extra + `clawteam/browser/__init__.py::playwright_available()` + `clawteam/memory/` + `clawteam/browser/` package skeletons + 3 new events registered in `clawteam/events/types.py` + `MemoryConfig`/`DesignShotgunConfig`/`BrowserConfig` pydantic sub-blocks in `clawteam/templates/__init__.py` (per A7). Touches pyproject + events + templates + new empty packages.

### Wave 1 — Generic substrate (parallel — 2 plans)

- **06-02-PLAN.md** (Wave 1, parallel) — Memory substrate: `clawteam/memory/entry.py` (MemoryEntry) + `clawteam/memory/store.py` (TeamMemoryStore write/list/prune — no search/conflict yet) + per-team isolation tests (D-15).
- **06-03-PLAN.md** (Wave 1, parallel) — Memory search substrate: `clawteam/memory/search.py` (rank formula) + `clawteam/memory/decay.py` (TTL lookup) + ranking tests (recency/provenance/decay).
- **06-04-PLAN.md** (Wave 1, parallel) — Browser substrate: `clawteam/browser/adapter.py` + `session.py` + `cookies.py` + tests with monkey-patched `sync_playwright`.

### Wave 2 — Browser skills (parallel — 3 plans)

- **06-05-PLAN.md** (Wave 2, parallel) — `/browse` skill + plugin registration.
- **06-06-PLAN.md** (Wave 2, parallel) — `/open-gstack-browser` skill + plugin registration.
- **06-07-PLAN.md** (Wave 2, parallel) — `/setup-browser-cookies` skill (handler + wizard) + plugin registration.

### Wave 3 — Design + learn skills (parallel — 3 plans)

- **06-08-PLAN.md** (Wave 3, parallel) — `/design-shotgun` state-machine skill + state.py + fixtures under `tests/fixtures/design_shotgun/` + plugin registration.
- **06-09-PLAN.md** (Wave 3, parallel) — `/design-html` skill + `framework_detect.py` + plugin registration.
- **06-10-PLAN.md** (Wave 3, parallel) — `/learn` skill handler + `clawteam learn` Typer CLI + plugin registration + memory `search()` integration (completes MEM-03/MEM-04 surface).

### Wave 4 — Memory guardrails (sequential — 1 plan, depends on 06-02/06-03/06-10)

- **06-11-PLAN.md** (Wave 4) — High-impact gate (D-09) + conflict detection integration in `TeamMemoryStore.write` (D-10) + backfill scanner (`clawteam/memory/backfill.py`, D-11) + wiring into `/learn` handler first-call + 3 test files (`test_high_impact_gate.py`, `test_conflict.py`, `test_backfill.py`).

### Wave 5 — Integration (sequential — 1 plan)

- **06-12-PLAN.md** (Wave 5) — End-to-end test: spawn team, write high-impact entry, confirm via answer file, observe promotion; trigger conflict via contradicting entry, verify event emit; run `/learn search` with provenance + decay + recency verifying ordering; cross-team isolation assertion (D-15). Adversarial matrix: 6 skills × 3 cases (happy/missing-tool/adversarial-input) = 18-case parametrize per Phase 5 Plan 05-10 precedent. Plugin-registration coverage assertion: `GstackSprintPlugin.contribute_skills()` returns exactly 13 unique names.

### Per-plan scope sketches (approximate LOC + task count)

| Plan | Tasks | LOC added (code) | LOC added (tests) |
|------|-------|-----------------|------------------|
| 06-01 Wave 0 | 3 | ~180 | ~120 |
| 06-02 MemEntry+Store | 2 | ~220 | ~250 |
| 06-03 MemSearch+Decay | 2 | ~180 | ~220 |
| 06-04 Browser substrate | 3 | ~260 | ~300 |
| 06-05 /browse | 2 | ~160 | ~180 |
| 06-06 /open-gstack-browser | 2 | ~160 | ~160 |
| 06-07 /setup-browser-cookies | 2 | ~200 | ~220 |
| 06-08 /design-shotgun | 3 | ~320 | ~300 |
| 06-09 /design-html | 2 | ~220 | ~220 |
| 06-10 /learn + CLI | 3 | ~300 | ~300 |
| 06-11 Gate+Conflict+Backfill | 3 | ~280 | ~360 |
| 06-12 Integration + adversarial | 3 | ~80 | ~500 |
| **Totals** | **30** | **~2560** | **~3130** |

---

## Sources

### Primary (HIGH confidence)
- `.planning/phases/06-browser-skills-design-pipeline-team-memory/06-CONTEXT.md` — D-01..D-17 + plan-prep A1..A9 verbatim
- `.planning/REQUIREMENTS.md` — MEM-01..07, SKILL-10..12, QUALITY-10
- `.planning/ROADMAP.md` lines 271-297 — Phase 6 SC list, research-flag MEDIUM
- `clawteam/plugins/gstack_sprint_plugin.py` — current contribute_skills returning 7 registrations [VERIFIED 2026-04-22]
- `clawteam/plugins/skill_registration.py` — SkillRegistration dataclass shape
- `clawteam/events/types.py` — HarnessEvent + register_event_type pattern
- `clawteam/harness/interaction_gate.py` — InteractionGate reuse target
- `clawteam/fileutil.py` — file_locked + atomic_write_text (no atomic_append_line)
- `clawteam/paths.py` — validate_identifier + ensure_within_root
- `clawteam/templates/__init__.py` — TemplateDef + _parse_toml extension precedent
- Phase 5 Plans 05-01..05-10 — skill sub-package shape + integration test pattern
- `.planning/research/STACK.md` — Playwright 1.58 pin + grep-first memory directive
- `.planning/research/ARCHITECTURE.md` — Pattern 5 TeamMemory layered
- `.planning/research/PITFALLS.md` — Pitfall 10 memory poisoning

### Secondary (MEDIUM confidence)
- Canonical references from CONTEXT.md — Phase 3 `_phase6_pending/` stub location confirmed via grep

### Tertiary (LOW confidence)
- BoW cosine + sentiment threshold calibration (0.75) — heuristic, no empirical dataset in research sources. Configurable via `gstack.toml [memory] conflict_threshold` so users can tune.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all deps verified against `pyproject.toml`; Playwright version pin cited from STACK.md
- Architecture: HIGH — every pattern has a Phase 4/5 precedent in-repo
- Pitfalls: HIGH — Pitfalls 1, 2, 6 directly map to Pitfalls #5, #4, #1 handled in Phases 4-5; Pitfalls 4-5 are policy locks from CONTEXT.md
- Ranking formula weights: MEDIUM — defaults documented; configurable
- Conflict threshold (0.75): LOW — tunable; no empirical calibration in sources

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (30 days — stable stack, only Playwright version float risk)
