# Stack Research

**Domain:** Multi-agent AI coding-CLI coordination harness + gstack skill-pack integration
**Researched:** 2026-04-15
**Confidence:** HIGH
**Scope:** NEW additions only — existing ClawTeam deps (Python 3.10+, typer, pydantic v2, rich, questionary, mcp, pyzmq, pytest, ruff, hatchling) are not re-researched. See `.planning/codebase/STACK.md` for the baseline.

---

## Executive Recommendation

> **Ship the milestone on stdlib + what you already have.** ClawTeam already carries `questionary`, `rich`, `file_locked()`, `atomic_write_text()`, and `pydantic v2`. Four of five domain questions in the brief can be answered **without adding a single required dependency**. The one genuine new dep is Playwright — gated behind an optional extra `[browser]`, consistent with how `pyzmq` lives behind `[p2p]`.
>
> Budget: **zero new required deps**, **one new optional extra** (`clawteam[browser]`).

---

## Recommended Stack (NEW additions only)

### Required Core Additions

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| *(none)* | — | — | All core harness primitives (`PhaseRegistry`, `InteractionGate`, `AttentionQueue`, `/learn` memory) can be built on stdlib + `pydantic v2` + `file_locked()` already in-tree. Adding a required dep for what amounts to a JSONL + file-lock pattern would violate the constraint "no new required runtime deps for core harness extensions." | HIGH |

### Optional Extras (feature-gated)

| Extension | Package | Version | Purpose | Gating Mechanism | Confidence |
|-----------|---------|---------|---------|------------------|------------|
| `clawteam[browser]` | `playwright` | `>=1.58,<2` | Headless Chromium driver for `/browse`, `/design-shotgun`, `/pair-agent`, `/design-html` skills. Python 3.9–3.13 supported. | Import-guarded (`try: import playwright`); skill detects absence and emits a clear `playwright install chromium` hint, per the "Auto-installing external tools" out-of-scope rule. | HIGH (PyPI verified) |
| `clawteam[browser-stealth]` (optional-of-optional) | `patchright` | `>=1.58.2,<2` | Drop-in Playwright replacement that patches Runtime.enable / Console.enable leaks. Only pulls in instead of `playwright` when the user opts in for anti-bot scraping. | Feature-flag in `gstack.toml`; default uses vanilla `playwright`. | MEDIUM (PyPI verified; maker claims "undetectable with right setup" but caveats apply) |

### Deliberately NOT Added

These are the alternatives we investigated and **rejected** in favor of stdlib:

| Rejected Addition | What It Offers | Why Not | Confidence |
|-------------------|----------------|---------|------------|
| `persist-queue>=1.1` | Thread-safe SQLite/file-based priority queue with FIFO/FILO/ACK semantics. Mature, Python 3.8-3.14. | Adds SQLite schema management + opaque pickle-by-default serialization. Our `AttentionQueue` is a tiny JSONL + in-place priority sort that needs **human-readable** question files (they're already artifacts under `sprint/<id>/questions/<N>.md`). Using persist-queue would fight the "everything under `~/.clawteam/` is introspectable" design of the codebase. | HIGH |
| `aiodiskqueue` | Asyncio-native persistent queue. | ClawTeam's existing store is sync + file-locked; introducing an async dep for a poll-and-drain UX is overkill. CLI `attend` loop is interactive — sync is fine. | HIGH |
| `chromadb>=1.5.7` | Embedded vector DB with automatic embeddings + indexing. 21–23 MB wheel. | Massive footprint (21 MB) and pulls in embedding-model code. Team memory (`/learn`) is a per-role JSONL + markdown set — a few hundred lines of "prefer X over Y" observations, not a RAG corpus. Starting with keyword/recency retrieval defers the vector-search decision until we know `/learn` actually grows beyond grep range. | HIGH |
| `sqlite-vec>=0.1.9` | SQLite extension for KNN vector search, 160 KB wheel, dependency-free. | Still requires an embedding backend (API call or local model) we don't want to mandate. Reserved as a **v2 opt-in** if `/learn` stores per-team exceed ~2–3K entries and keyword search stops scaling. Pre-approved as the future vector store of choice (small, SQLite, no infra). | HIGH |
| `textual>=8.2.3` | Full TUI framework with OptionList/DataTable/reactivity. | `clawteam attend` is a question-answer loop, not a full application. `questionary` (already present) handles it natively with `ask()` + `select()` + `text()`; `rich.table.Table` (already present) renders priority queues. Reach for Textual in v2 if/when a multi-sprint conductor UI ships. | HIGH |
| `pyppeteer` (Puppeteer-Python port) | Python binding of the JS-first Puppeteer. | Unmaintained port that lags the JS original; `playwright-python` is Microsoft's first-class Python library with full feature parity. The 2026 browser-automation literature unanimously recommends Playwright for new Python projects. | HIGH |
| `playwright-stealth>=2.0.3` | Navigator.webdriver masking, languages override. | Author explicitly warns: "Don't expect this to bypass anything but the simplest of bot detection methods. Consider this a proof-of-concept starting point." For anything serious, `patchright` is the stronger option. We only need it if we target scraping-protected sites, which the gstack `/browse` skill doesn't need for its primary job (rendering/screenshots/clicks on apps under development). | HIGH |

---

## Primitive-by-Primitive Recommendations

### 1. AttentionQueue (cross-sprint pending-questions queue)

**Recommendation:** stdlib + existing `file_locked()` + `atomic_write_text()`.

**Rationale.** The data model is:
- One question = one markdown file `sprint/<id>/questions/<N>.md` + a sidecar JSON line in `~/.clawteam/teams/<team>/attention.jsonl` recording `{sprint_id, question_id, priority, asked_at, role, gate_id, status}`.
- Priority sort is `O(N log N)` over at most a few hundred entries (11 agents × handful of open questions × N sprints); Python's `list.sort()` handles this in microseconds.
- Concurrency: wrap read-modify-write with the existing `file_locked(attention_path)`; append-mode JSONL writes are already safe under POSIX `O_APPEND`.
- Answers round-trip through `sprint/<id>/answers/<N>.md` (artifacts, registered via existing `ArtifactStore`).

**Why not a real queue library.** The "queue" part of `AttentionQueue` is misleading — it's not FIFO consumption, it's a priority-sorted *view* over open-question files. Users want grep-able markdown, not pickled records inside SQLite. The ClawTeam constraint is already explicit: "file-locked atomic JSON/TOML persistence under `~/.clawteam/` — existing." This extension inherits that pattern.

**pydantic model** (goes in `clawteam/attention/models.py`):
```python
class AttentionItem(BaseModel):
    team: str
    sprint_id: str
    question_id: str
    priority: int  # lower = more urgent, per persist-queue convention
    asked_at: datetime
    role: str  # the agent role that asked
    gate_id: str  # which InteractionGate is blocking on this
    status: Literal["open", "answered", "abandoned"]
    question_path: Path
    answer_path: Path | None = None
```

**CLI surface** (rides on existing `typer`):
- `clawteam attend` — interactive answer loop using `questionary.select()` (pick next question by priority) + `questionary.text(multiline=True)` (enter answer). Already how ClawTeam handles interactive prompts (`clawteam/cli/commands.py`).
- `clawteam attend --all --json` — machine-readable dump for scripting.
- `rich.Table` renders the priority view (already the CLI convention per `clawteam/board/renderer.py`).

**Confidence:** HIGH.

### 2. `/learn` memory store (per-team pattern/pitfall/preference accumulation)

**Recommendation:** JSONL + markdown, one file per role per sprint, aggregated lazily on read. No vector store in v1.

**Storage layout:**
```
~/.clawteam/teams/<team>/memory/
├── roles/
│   ├── engineer.jsonl      # append-only, one learning per line
│   ├── reviewer.jsonl
│   ├── designer.jsonl
│   └── ...
├── shared.jsonl            # cross-role lessons (promoted from role-local)
└── index.json              # atomic-written summary: {role: count, last_updated}
```

**Per-line schema** (pydantic `Learning` model):
```python
class Learning(BaseModel):
    id: str  # ulid
    team: str
    role: str
    sprint_id: str
    category: Literal["pattern", "pitfall", "preference"]
    title: str        # short hook — grep target
    body: str         # 1-5 paragraph markdown
    tags: list[str]
    recorded_at: datetime
    source: str  # e.g. "review:PR#42" or "retro:sprint-7"
```

**Retrieval in v1:** keyword + recency + tag filter, all in-memory. Justified because:
- gstack's own `/learn` storage "is not detailed in docs" but its usage pattern is "review, search, prune, export" — that's a CRUD UX, not a RAG UX.
- A team accumulating ~100 learnings over 6 months is 100 lines × ~500 chars = 50 KB. Grep is optimal at that scale.
- Semantic search becomes worthwhile above ~1000 items with diverse phrasing; defer until we're there.

**v2 upgrade path:** `sqlite-vec` (160 KB extension) + any embedding provider. Schema migration is append-only: add an `embedding BLOB` column to a new `learnings_vec` virtual table; existing JSONL stays as the source of truth. Reserved as **the** memory-store upgrade if/when needed — it's SQLite, zero-infra, matches ClawTeam's "no services" posture.

**Gstack parity note:** The `/learn` command ported as a **team-shared ClawTeam skill** (per PROJECT.md "Team-level safety rails... /learn (team-shared)"), owned by the team rather than any single agent. Each role can still contribute.

**Confidence:** HIGH (storage design), MEDIUM (prediction that keyword search suffices — mitigated by clean upgrade path).

### 3. Headless browser tooling for `/browse`, `/design-shotgun`, `/pair-agent`

**Recommendation:** `playwright>=1.58,<2` (Python, async API) via a new optional extra `clawteam[browser]`. Feature-gated import with clear error on absence. Optional `patchright` upgrade path for users needing anti-bot.

**Why Playwright over Puppeteer.**
- Playwright has a **first-party Python binding** (`microsoft/playwright-python`, 1.58.0, released 2026-01-30). Puppeteer's Python port (`pyppeteer`) is unofficial and lags the upstream JS version.
- 2026 consensus across browser-automation surveys: Playwright wins on Python support, per-context proxy isolation, auto-wait reliability, and multi-browser coverage (Chromium + Firefox + WebKit from one API).
- gstack's own `/browse` skill is built on Playwright (JS/Bun runtime upstream) — porting to Python-Playwright keeps us close to the reference implementation's semantics.

**Install UX.**
```bash
pip install 'clawteam[browser]'         # adds playwright==1.58.*
playwright install chromium             # ~170 MB chromium download
```

Feature detection lives in the skill:
```python
# clawteam/skills/browse.py  (sketch)
try:
    from playwright.async_api import async_playwright  # type: ignore
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

def ensure_playwright() -> None:
    if not HAS_PLAYWRIGHT:
        raise SkillUnavailable(
            "Playwright not installed. Run:\n"
            "  pip install 'clawteam[browser]'\n"
            "  playwright install chromium"
        )
```

**Anti-bot / stealth strategy.** Three tiers, only unlock the higher one when needed:

| Tier | Library | Use When | Notes |
|------|---------|----------|-------|
| 1 (default) | `playwright` alone | gstack's own use case: browsing your app-under-development + screenshots + clicks. No site-level detection involved. | gstack-native `/open-gstack-browser`'s "anti-bot stealth" is, per the docs, **Chrome-for-Testing rebrand + persistent user-data-dir profile** — no runtime patching. We replicate this with `launch_persistent_context(user_data_dir=...)` and done. |
| 2 (opt-in) | `playwright-stealth>=2.0.3` | Light obfuscation when targeting simple bot checks. | Adds `navigator.webdriver` masking. Maintainer warns this only defeats "the simplest of bot detection methods." |
| 3 (opt-in, heavy) | `patchright>=1.58.2` | Serious scraping-protected sites (Cloudflare, Kasada, Datadome). | Drop-in replacement for playwright import; patches Runtime.enable / Console.enable leaks + closed shadow root access. Chromium-only. |

v1 targets Tier 1 only. Tier 2/3 are documented upgrade paths, not shipped.

**Persistent browser daemon pattern.** gstack upstream runs a persistent Chromium that stays alive across command invocations (3s first boot, 100-200ms per subsequent command). We can match this in Python with `async_playwright().start()` held in a background task inside the skill process, or — more naturally for ClawTeam — let the agent's spawned process own the browser context for the duration of the agent's lifetime. The agent is already long-lived (persistent desk), so the browser can live on its desk.

**Confidence:** HIGH (library choice), HIGH (tiering strategy).

### 4. Slash-command-to-methodology porting (gstack markdown skills → ClawTeam role prompts)

**Recommendation:** No library. Use existing `HarnessPlugin.contribute_prompts(phase, role)` + TOML-authored role prompts + a small in-tree markdown frontmatter parser.

**Why no library.** gstack skills are standard Claude Code skill files: `SKILL.md` with YAML frontmatter (`name`, `description`, optional `allowed-tools`) plus markdown body. The Claude Skills spec has a public schema on `code.claude.com/docs/en/skills` and Anthropic's `anthropics/skills` repo is the reference. Parsing this is ~30 lines of Python:

```python
# clawteam/skills/parser.py (sketch)
import yaml
from pathlib import Path
from typing import NamedTuple

class ParsedSkill(NamedTuple):
    name: str
    description: str
    body: str
    frontmatter: dict

def parse_skill_md(path: Path) -> ParsedSkill:
    text = path.read_text()
    if text.startswith("---\n"):
        _, fm, body = text.split("---\n", 2)
        fm_data = yaml.safe_load(fm) or {}
    else:
        fm_data = {}
        body = text
    return ParsedSkill(
        name=fm_data.get("name", path.stem),
        description=fm_data.get("description", ""),
        body=body.strip(),
        frontmatter=fm_data,
    )
```

`pyyaml` is already a transitive of `questionary` (via `prompt_toolkit`)... actually let me verify that claim: it's not — `prompt_toolkit` has no YAML dep. **Two options:**

**Option A (recommended): Ship `pyyaml` as a new required dep.** It's ~200 KB, universally available, no controversy. Adds one line to `pyproject.toml`.

**Option B: Roll a minimal `---`-delimited parser by hand.** Skill frontmatters are flat key-value; a ~15 LOC split+parse suffices. No new dep.

The constraint says "no new required runtime deps for core harness extensions." That tips us to **Option B** — handcoded flat-kv parser (`KEY: value` per line between `---` fences). Matches the constraint; rejects YAML-style nesting which gstack skills don't use anyway. (Verified: gstack `SKILL.md` frontmatters use only `name:`, `description:`, occasionally `allowed-tools:` as a flat list.)

**Porting strategy per PROJECT.md:**

| gstack skill type | Porting target | Mechanism |
|-------------------|----------------|-----------|
| Methodology/rubric (e.g. `/office-hours`, `/plan-ceo-review`, `/retro`, `/design-review`, `/review`, `/qa`) | Baked into the role's prompt | `HarnessPlugin.contribute_prompts(phase, role)` returns the skill body as an appended section to the role's system prompt. No runtime invocation — it's *baked in at spawn time*. |
| Tool-heavy (e.g. `/browse`, `/design-shotgun`, `/codex`, `/ship`, `/canary`) | New ClawTeam skill module under `clawteam/skills/` | Python implementation; agents invoke via MCP tool call. Ported logic, not ported markdown. |
| Safety rails (e.g. `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/autoplan`) | New harness primitives | `freeze` becomes a path-lock registered on `EventBus`; `autoplan` is the phase machinery itself. |

**What this means for the stack.** We need **no libraries** for the skill port itself. We need a parser (≤30 LOC handcoded), a prompt-concatenation convention (already present in `clawteam/harness/prompts.py`), and a skill registry pattern (mirror `clawteam/spawn/__init__.py`'s backend registry).

**Confidence:** HIGH.

### 5. Interactive CLI attention loops (`clawteam attend`)

**Recommendation:** `questionary` + `rich` — **already in ClawTeam**. No new deps.

**Pattern:**
```python
# clawteam/cli/attend.py (sketch)
import questionary
from rich.table import Table
from rich.console import Console

def cmd_attend(team: str | None = None):
    console = Console()
    queue = AttentionQueue.load(team=team)  # pydantic-validated

    while open_items := queue.open(sort_by="priority"):
        # Render priority view
        tbl = Table(title=f"Pending questions ({len(open_items)})")
        tbl.add_column("Priority"); tbl.add_column("Sprint")
        tbl.add_column("Role"); tbl.add_column("Question")
        for item in open_items[:10]:
            tbl.add_row(str(item.priority), item.sprint_id,
                        item.role, item.title)
        console.print(tbl)

        # Pick one
        choices = [f"{i.priority:>3}  {i.sprint_id}  {i.title[:60]}"
                   for i in open_items[:10]] + ["(skip all / exit)"]
        pick = questionary.select("Answer which?", choices=choices).ask()
        if pick.startswith("(skip"): break

        # Answer
        ans = questionary.text("Your answer:", multiline=True).ask()
        if ans:
            queue.answer(open_items[choices.index(pick)].question_id, ans)
```

**Why not Textual.** Textual is a full TUI framework with CSS, widgets, reactive state. `attend` is a 3-step interactive loop: *show list → pick one → type answer*. `questionary.select` + `questionary.text(multiline=True)` already maps 1:1 to that. Adding Textual for this is 1.2 MB of framework for ~10 LOC of value.

**Why not `prompt_toolkit` directly.** `questionary` *is* a thin wrapper over `prompt_toolkit` for exactly this use case. Using `prompt_toolkit` directly means re-implementing question-type widgets that `questionary` ships tested.

**When Textual would be justified (deferred).** A future "Conductor UI" (explicitly v2 per PROJECT.md "Multi-team Conductor UI — reserved for v2") — a full-screen dashboard showing all teams × sprints × agents × pending questions. That's a Textual use case. Not this milestone.

**Confidence:** HIGH.

---

## Installation (NEW additions only)

```bash
# v1 core (what actually ships) — no new required deps
pip install clawteam  # unchanged

# Optional browser feature (adds Playwright)
pip install 'clawteam[browser]'
playwright install chromium

# Optional browser + anti-bot stealth (tier 3)
pip install 'clawteam[browser-stealth]'  # pulls patchright instead of playwright
patchright install chromium
```

`pyproject.toml` additions:
```toml
[project.optional-dependencies]
# ... existing extras ...
browser = ["playwright>=1.58,<2"]
browser-stealth = ["patchright>=1.58.2,<2"]
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| stdlib + `file_locked()` for AttentionQueue | `persist-queue` | Only if you need message broker semantics (ACK, retry, dead-letter). We don't — questions are markdown artifacts. |
| JSONL for `/learn` | `sqlite-vec` | v2 when per-team memory exceeds ~2-3K entries or when queries need semantic matching. Pre-approved as the upgrade target. |
| JSONL for `/learn` | `chromadb` | Never recommended for this scope — 21 MB wheel, heavy RAG orientation. Appropriate for a product that *is* a vector-store, not for 100-line pattern notes. |
| `playwright` | `pyppeteer` | Never — unmaintained and lags upstream. |
| `playwright` (default) | `playwright-stealth` (tier 2) | Only for simple bot-checks. |
| `playwright` (default) | `patchright` (tier 3) | Only for scraping Cloudflare/Kasada/Datadome-protected sites. |
| `questionary` + `rich` | `textual` | Full-screen dashboard v2 (Conductor UI). Not this milestone. |
| Handcoded frontmatter parser | `pyyaml` | If skill frontmatters grow nested structures. Today they're flat kv. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `pyppeteer` | Unmaintained Python port of Puppeteer; lags feature-wise and the community has moved. | `playwright` (official Python binding from Microsoft). |
| `chromadb` for `/learn` memory | 21-23 MB wheel, bundles embedding + indexing stack. Vastly oversized for per-team pattern notes. | stdlib JSONL; `sqlite-vec` (160 KB) later if scale demands. |
| `persist-queue` for `AttentionQueue` | SQLite + pickle serialization obscures questions from grep/editor tools. Breaks the "everything under `~/.clawteam/` is inspectable" design. | stdlib + existing `file_locked()` + human-readable markdown artifacts. |
| `textual` for `clawteam attend` | Full TUI framework for a 3-step loop — massive overkill; brings 1.2 MB of runtime. | `questionary.select` + `questionary.text` (already present). |
| `pyyaml` as required dep | Violates the "no new required runtime deps" constraint for flat frontmatter parsing. | Handcoded flat-kv frontmatter parser (~15 LOC). |
| Auto-installing Chromium on first skill call | Per PROJECT.md out-of-scope: "Auto-installing external tools... support nightmare." | Fail gracefully with a clear setup hint: `pip install 'clawteam[browser]' && playwright install chromium`. |
| `playwright-stealth` as default for `/browse` | Author explicitly scopes it as "proof-of-concept" for simple detection only. Adds overhead + monkey-patches to no gain for normal use. | Vanilla `playwright` with `launch_persistent_context` for gstack-browser-equivalent behavior. |

---

## Stack Patterns by Variant

**If the user only runs `clawteam team spawn gstack` and never triggers a browser skill:**
- No new deps installed. Zero-footprint upgrade path from baseline ClawTeam.
- `/browse`, `/design-shotgun`, `/pair-agent` skills remain registered but print setup instructions on first invocation.

**If the user opts into the browser feature (`pip install 'clawteam[browser]'`):**
- `playwright==1.58.*` installed. `playwright install chromium` downloads the Chromium binary (~170 MB to `~/.cache/ms-playwright/`).
- `/browse` works headlessly; `/open-gstack-browser` launches a headed persistent-context browser.

**If the user needs anti-bot on a specific site (`pip install 'clawteam[browser-stealth]'`):**
- Installs `patchright` instead of vanilla `playwright`; import shim in `clawteam/skills/browse.py` picks whichever is present.
- Recommended user also runs `patchright install chromium` which downloads Chromium patched to remove Runtime/Console leaks.

**If the user has custom team memory needs beyond keyword search (v2):**
- `clawteam[memory-vec]` future extra pulls in `sqlite-vec` + a chosen embedding provider (e.g. a lightweight local SBERT via `sentence-transformers` *optional-of-optional*). v1 does not ship this.

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `playwright==1.58.0` | Python 3.9-3.13 | Released 2026-01-30; compatible with ClawTeam's 3.10+ floor. 5 classifiers confirm full support across 3.9-3.13. |
| `patchright==1.58.2` | Python 3.9-3.13 | Released 2026-03-07; drop-in replacement, same version scheme as upstream Playwright. Chromium only (no Firefox/WebKit). |
| `playwright-stealth==2.0.3` | Python 3.9-3.14 | Released 2026-04-04. Works only against simple bot checks. |
| `chromadb==1.5.7` | Python 3.9+ | Not recommended; included here for completeness. |
| `sqlite-vec==0.1.9` | Any Python w/ SQLite ≥3.35 | 160 KB; v2 upgrade candidate. Ships as pre-compiled wheels. |
| `persist-queue==1.1.0` | Python 3.8-3.14 | Not recommended; included for completeness. |
| `textual==8.2.3` | Python 3.9-3.14 | v2 Conductor-UI candidate; not needed for `attend`. |

**Existing baseline — DO NOT re-add:** `pydantic>=2.0,<3.0`, `typer>=0.12,<1.0`, `rich>=13.0,<15.0`, `questionary>=2.0.1,<3.0`, `mcp>=1.0`, `pyzmq>=25.0,<27.0` (extra `p2p`), `pytest>=9.0,<10.0`, `ruff>=0.1`. These are already in `pyproject.toml` and exercise the `file_locked()` + `atomic_write_text()` pattern we inherit.

---

## Sources

**Context7 (HIGH confidence):**
- `/microsoft/playwright-python` — installation, async/sync API surface, browser launch options
- `/mattwmaster58/playwright_stealth` — stealth integration patterns, author caveats
- `/asg017/sqlite-vec` — vector-search SQLite extension, footprint
- `/chroma-core/chroma` — embedded vector DB, install profile
- `/textualize/textual` — widget surface, OptionList, when it's worth reaching for
- `/prompt-toolkit/python-prompt-toolkit` — underlying interactive-CLI primitives

**Official docs & PyPI (HIGH confidence):**
- https://pypi.org/project/playwright/ — v1.58.0, 2026-01-30, Python 3.9-3.13
- https://pypi.org/project/playwright-stealth/ — v2.0.3, 2026-04-04, "proof-of-concept only" caveat
- https://pypi.org/project/patchright/ — v1.58.2, 2026-03-07, drop-in replacement claim
- https://pypi.org/project/sqlite-vec/ — v0.1.9, 2026-03-31, 160 KB wheel
- https://pypi.org/project/chromadb/ — v1.5.7, 2026-04-08, 21-23 MB wheel
- https://pypi.org/project/textual/ — v8.2.3, 2026-04-05
- https://pypi.org/project/persist-queue/ — v1.1.0, 2025-10-25
- https://code.claude.com/docs/en/skills — Claude Code skill schema (YAML frontmatter + markdown body)
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview — Agent Skills open standard

**Upstream references (HIGH confidence):**
- https://github.com/garrytan/gstack — gstack README, skill list, sprint model
- https://github.com/garrytan/gstack/blob/main/BROWSER.md — confirms `/browse` uses Playwright (JS/Bun) + Chrome for Testing rebrand; no runtime stealth patching
- https://gstacks.org/gstack-browser-automation-testing.html — persistent browser daemon architecture (3s cold boot, 100-200ms warm)

**Surveys / analysis (MEDIUM confidence — cross-checked against official docs):**
- https://www.firecrawl.dev/blog/playwright-vs-puppeteer — 2026 Playwright-over-Puppeteer consensus
- https://datadome.co/bot-management-protection/will-playwright-replace-puppeteer-for-bad-bot-play-acting — anti-bot detection surface comparison
- https://scrapfly.io/blog/posts/playwright-stealth-bypass-bot-detection — tier-by-tier stealth strategy
- https://turso.tech/blog/using-sqlite-as-your-llm-vector-database — sqlite-vec + LLM memory validation
- https://eric-tramel.github.io/blog/2026-02-07-searchable-agent-memory/ — JSONL-file-per-session memory pattern for agents

**Existing baseline (already inspected):**
- `/home/jac/repos/ClawTeam-gstack/.planning/codebase/STACK.md` — confirms `questionary`, `rich`, `pydantic v2` already present
- `/home/jac/repos/ClawTeam-gstack/.planning/codebase/ARCHITECTURE.md` — `file_locked()`, `atomic_write_text()`, `ensure_within_root()` primitives
- `/home/jac/repos/ClawTeam-gstack/clawteam/fileutil.py` — confirms file-lock + atomic-write implementation is production-ready

---

*Stack research for: ClawTeam gstack integration (v1 milestone)*
*Researched: 2026-04-15*
*Key insight: the cheapest shippable stack adds zero required deps and one optional extra. Defer vector-store, TUI, and queue-library decisions to v2 upgrade paths that are pre-shaped (sqlite-vec, Textual, persist-queue) without committing today.*
