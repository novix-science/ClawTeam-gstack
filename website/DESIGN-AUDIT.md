# Landing Page Design Audit — Top 5 Wins

**Auditor:** designer (solo-f8d047)
**Date:** 2026-04-23
**Mode:** SELECTIVE — highest-leverage visual/UX improvements only
**Scope:** `website/src/App.jsx` + `website/src/styles.css` (hero, globe, clients, features, workflow, gstack, docs, footer)

**Rubric dimensions touched this pass:** IA (1), AI-slop (4), design-system alignment (5), responsive (6), overall (10). AI-slop risk is **LOW** — no blacklist markers hit (no default shadcn, no lorem-ipsum, no emoji-as-icon, no stock photos, branded orange/indigo palette). The problems are comprehension and dead weight, not aesthetics.

---

## #1 · Broken secondary CTA + half the footer links (HIGH)

The hero's `btn-ghost` **"CLI Reference"** points to `skills/clawteam/references/cli-reference.md`. The site builds to `../docs/` (see `vite.config.mjs:14`), but that markdown file lives at repo root `skills/clawteam/references/`, *not* under `docs/`. **Every relative `skills/...` href breaks when the site is deployed from `docs/`.** Affected:

- `App.jsx:228` — hero secondary CTA
- `App.jsx:57,58,59` — 3 of 4 doc cards
- `App.jsx:285` — footer Skill + CLI Reference links

This is the second-most-prominent CTA on the page pointing at a 404 (or, on GitHub Pages, a raw-text download). Credibility-breaking.

**Fix sketch (one-line):** swap to absolute GitHub blob URLs, e.g. `https://github.com/HKUDS/ClawTeam/blob/main/skills/clawteam/references/cli-reference.md`, or copy the `skills/` tree into `docs/` at build time.

---

## #2 · Duplicate client row right below the globe (HIGH)

The globe section labels 5 clients as orbit pins (Claude Code, Codex, OpenClaw, nanobot, Any CLI). The very next section is a **"Works with"** strip showing **the same 5 logos with the same labels**, in the same viewport scroll. Pure redundancy — the globe already *is* the "works with" statement.

**Fix sketch:** delete the entire `<section className="clients shell">` block (`App.jsx:236-239`). The globe carries the load. If a logos row is politically required, strip the labels and make it a 24-px monochrome icon strip so it reads as accent, not repetition.

---

## #3 · Hero conflates two products in <5s (HIGH)

The hero asks a cold visitor to parse two distinct concepts before they scroll:

- **Badge:** "Agent swarm orchestration · gstack team template"
- **H1:** "Coordinate any coding agent from one CLI" *(this is ClawTeam's value prop)*
- **Sub:** ClawTeam sentence + "One command hires the **gstack team** — 11 persistent specialists..." *(new vocabulary, new product)*

Result: a visitor doesn't know whether the thing they're evaluating is ClawTeam (the orchestration CLI), gstack (the 11-agent team), or both. The badge already leaks gstack before H1 lands. gstack gets its own flagship section below — let that section do the introducing.

**Fix sketch:**
- Badge → drop `· gstack team template`. Keep `Agent swarm orchestration`.
- Hero-sub → keep sentence 1 ("ClawTeam is the coordination layer for..."). **Cut** sentence 2 (the "gstack team — 11 persistent specialists" line). The gstack section reintroduces the same idea 1 scroll below with proper framing.

---

## #4 · Two competing primary CTAs, both point to GitHub (MED)

Header has `btn-primary` **"GitHub"** → `/HKUDS/ClawTeam`. Hero has `btn-primary` **"Get started"** → `/HKUDS/ClawTeam#-quick-start`. Both are white-filled primary buttons in the same viewport, both go to the same repo. The "primary action" is ambiguous, and the hero CTA offers zero new destination over the header.

**Fix sketch (pick one):**
- Demote header to `btn-ghost` with label **"GitHub ↗"** so there's exactly one primary button on first screen, OR
- Change hero primary from "Get started" to **"Install"** that copy-reveals `pip install clawteam` inline (the workflow section already shows this command — pull it forward).

---

## #5 · "Core capabilities" is dead weight between globe and gstack (MED)

Three feature cards — "Shared task graph", "Persistent coordination", "Git-aware execution" — sit between the (strong) globe+clients stack and the (strong) gstack section. The cards have **no icons** even though `styles.css:536-547` defines `.feature-icon` for exactly this purpose. Body copy is generic ("One board for blockers, priority, ownership..."). On scroll it reads like filler before the real story.

Also: gstack is labeled **"The flagship team"** yet appears *after* a generic capabilities section. Hierarchically the flagship should earn the scroll-weight ahead of generic cards.

**Fix sketch (cheapest):** cut the Features section entirely; the gstack phases + 11-role grid already proves the same claims with concrete specifics.
**Fix sketch (if keeping):** reorder so `#gstack` comes before `#features`, and rewrite the 3 cards to cite gstack mechanics (e.g. "Evidence gates — seven phases, no gameable artifact checks"). Adds icons via the existing `.feature-icon` rule.

---

## Lower-leverage notes (do not prioritize)

- **LOW** `.terminal-line` uses `white-space: nowrap` (`styles.css:351`); long commands like `clawteam spawn tmux claude-code --agent-name builder` clip on sub-500px widths. Decorative mockup, not load-bearing — fine to leave.
- **LOW** Roster grid is 4 columns × 11 cards = orphan row of 3. Aesthetic nit. 3-column would orphan 2; tolerate.
- **LOW** Mobile 375px hides `.orbit-nanobot` and `.orbit-any` (`styles.css:935-937`). Acceptable tradeoff; the globe still reads as multi-client.

---

## Ranked action list

| # | Severity | Effort | Fix |
|---|----------|--------|-----|
| 1 | HIGH | 5 min | Rewrite broken `skills/...` hrefs as absolute GitHub URLs (or copy tree into `docs/` at build) |
| 2 | HIGH | 2 min | Delete `<section className="clients shell">` |
| 3 | HIGH | 2 min | Trim badge to `Agent swarm orchestration`; drop sentence 2 of hero-sub |
| 4 | MED  | 2 min | Demote header `btn-primary` to `btn-ghost` + arrow glyph |
| 5 | MED  | 15 min | Cut `#features` OR reorder `#gstack` above `#features` and inject icons |

Ship #1–#3 first. They're all 2–5 minute edits and together remove the biggest comprehension + trust blockers on initial scroll.

SIGNATURE: gstack-role:designer rubric:plan-design-review+design-review envelope-version:1
