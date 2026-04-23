# IMPROVE-SPEC: Website improvement scope

**Status:** SPEC (intent-lock before planning)
**Author:** pm (YC-advisor)
**Date:** 2026-04-23
**User ask:** "把网站改进一下" (improve the website)
**Mode:** SELECTIVE expansion — highest-leverage wins, no redesign.
**Target file set:** `website/` (React + Vite, builds to `../docs/`)

---

## 1. Who is this landing page for?

The page is built for **developers evaluating ClawTeam as an agent orchestration tool**. Evidence from the current build:

| Signal | What it tells us |
|---|---|
| Primary CTA is `pip install clawteam` | CLI-first; assumes terminal-native user |
| Hero sub: "Claude Code, Codex, OpenClaw, nanobot, any terminal-native client" | Users already have at least one coding-agent CLI installed |
| Doc cards link to `SKILL.md` + `cli-reference.md` | Readers who think in agent-skills and CLI flags |
| No "Contribute" / "Join discussion" section | Not optimizing for contributors |
| No end-user product framing (no screenshots of a finished app) | Not optimizing for non-developers |

**Not the audience:** enterprise buyers, end-users of apps built with ClawTeam, casual AI enthusiasts, contributors hunting a first-issue.

**Primary persona:** a dev who already uses Claude Code / Codex, has heard about swarm-orchestration, and is deciding in the next 60 seconds whether to `pip install` or close the tab.

**Secondary persona:** AI-platform evaluator comparing ClawTeam to LangGraph / CrewAI / AutoGen and deciding whether to invest time reading docs.

---

## 2. What action is this page optimizing for?

In descending visible priority on the current build:

1. **Click through to GitHub** — `GitHub` button in header + 2 hero CTAs + footer all route to `github.com/HKUDS/ClawTeam`. This is the *actual* primary funnel; a star is a side-effect, but the intent is "send the user to the repo so they read the README and run `pip install`".
2. **Install the CLI** — visible in the `pip install clawteam` code block in step 01. This is the page's only in-place conversion.
3. **Read docs before committing** — doc cards (SKILL guide, CLI reference) for users who want proof before installing.

**Single success metric if we had to pick one:** `pip install clawteam` invocations traceable to a website visit (or, as proxy: GitHub Quick-Start section views + star-rate on sessions referred from the landing page).

**What the page is NOT optimizing for:** newsletter signups, demo-request forms, Discord/Slack joins, paid conversions. Good — no pretence of a product-funnel.

---

## 3. What does "improve" mean in this user's context, right now?

Context: **v1.0 milestone closed yesterday (2026-04-22).** The tonal shift before/after v1.0 matters:

- **Before v1.0:** the landing page's job is "generate interest, explain the idea, prove it isn't vaporware."
- **After v1.0:** the landing page's job is "convert interest into install *because the thing is now stable*."

The current page is still tuned for the pre-v1.0 job. Evidence:

| Current state | Post-v1.0 gap |
|---|---|
| News section (in README) latest entry: `v0.2.0` on 2026-03-23 | v1.0 shipped yesterday — page does not reflect the credibility jump |
| Hero badge: "Agent swarm orchestration · gstack team template" | No "v1.0 stable" or equivalent trust signal |
| No benchmarks, no user counts, no "real sprint" artifacts | After v1.0 we can prove it works with evidence, not just claims |
| Copy inconsistency: hero says "one command hires the gstack team," step 02 shows generic `spawn-team <name>` — the *flagship* command `clawteam team spawn gstack` only appears in section copy, never in a code block | A curious dev who copies step 02 does not get the v1.0 gstack — they get the generic path |

So "improve" here most plausibly means: **bring the page up to the credibility level v1.0 earned, and tighten the first-install experience so the CTA actually lands.** Not a redesign. Not new sections. Tighten what's there.

---

## 4. Three candidate improvement themes (ranked by leverage)

### Theme A — Signal v1.0 + add one piece of concrete proof  ⭐ HIGHEST LEVERAGE

**Why:** v1.0 is the single biggest thing that changed since the page was written. If a returning visitor sees no difference from last week, the page is *actively* under-selling the project. For new visitors, v1.0 is the trust signal that unlocks `pip install`.

**Concrete scope:**
- Add a `v1.0` pill to the hero badge row, or update the hero sub to mention "v1.0 stable (Apr 2026)."
- Update the News section in README (which the site currently inherits narratively).
- Add **one** piece of post-v1.0 proof in the hero-adjacent area — suggested: a compact "what a sprint produced" artifact (commit count, PR merged, agent turns) OR one short testimonial-style quote from a real run.

**Effort:** one session, no structural changes.
**Risk:** low — pure copy + tiny component edits.
**Conversion theory:** removes the #1 credibility objection ("is this actually maintained / ready?").

---

### Theme B — Fix the command inconsistency so the first copy-paste actually works  ⭐ MEDIUM-HIGH LEVERAGE

**Why:** The page says "one command hires the **gstack team**" in the hero, then in "How it works" step 02 the code block is `clawteam team spawn-team my-team -d "Docs + engineering"` — which is the *generic* command, not the gstack flagship. A developer who trusts the hero and copy-pastes step 02 does not end up with the 11-agent gstack team they were promised. This is a literal promise-vs-delivery bug in the conversion funnel.

**Concrete scope:**
- Make step 02's code block `clawteam team spawn gstack` (the flagship) with a one-line caption that the generic `spawn-team <name>` is also available for custom teams.
- OR, flip the narrative: demote the gstack reference in the hero and keep the generic path primary. Either is fine; what's broken is the mismatch.
- Verify the terminal mockup in the hero is consistent with whichever command is the hero-path.

**Effort:** ~30 min, one file.
**Risk:** low — need to verify `clawteam team spawn gstack` is the supported syntax (appears in the gstack section but not in any code block).
**Conversion theory:** removes the "first command I copy-pasted doesn't match the promise" friction — the dead-weight bounce that happens silently.

---

### Theme C — Replace the static terminal mockup with a short live-sprint demo  ⭐ HIGH LEVERAGE, HIGHER EFFORT

**Why:** The hero's terminal mockup is static and shows a contrived `team status` table. Post-v1.0 we have a real product that does something visible. "Show, don't tell" the 11-agent swarm working — this is the single strongest argument the page can make for *why ClawTeam is different*.

**Concrete scope (cheapest form):**
- Record one 20–40s asciinema of an actual gstack sprint (or a cleaned-up excerpt), embed it where the `TerminalMockup` component currently renders.
- Alternative: a short looping MP4/WebM of the tmux grid with agents working.
- Keep the static mockup as fallback for no-JS/prefers-reduced-motion.

**Effort:** one session for recording + embed + accessibility fallback.
**Risk:** medium — needs a clean recording, accessibility handling, file-size care.
**Conversion theory:** moves the page from "clever concept" to "holy shit that's real" — the emotional unlock that turns a docs-skim into a `pip install`.

---

## 5. Rejected / de-prioritized candidates (explicit)

| Candidate | Why rejected |
|---|---|
| "Fix dead doc links" | Verified: relative links (`skills/clawteam/SKILL.md`, `skills/clawteam/references/cli-reference.md`) resolve in the production build because Vite `outDir` is `../docs/` and `docs/skills/...` exists on disk. Not dead in deployed form. |
| Full redesign / new sections | Explicitly out of scope per CEO "SELECTIVE, no redesign." |
| Add pricing / waitlist / email capture | Not the conversion model. The funnel is `pip install`, not lead-gen. |
| Add a blog / changelog page | Higher effort, lower leverage than in-place v1.0 signal (Theme A). Revisit after v1.1. |
| Add i18n (zh / ko) | README has translations; landing page English-only is appropriate for the CLI-dev audience. Not a v1.0 gap. |

---

## 6. Recommended execution order

**If we ship only one thing:** Theme A (v1.0 signal + one piece of proof). It's the smallest change with the biggest "the page now matches reality" return.

**If we ship two:** A + B. Combined, they close the credibility gap *and* the copy-paste-works gap — both pre-install friction points. Estimated one working session total.

**If we ship three:** A + B + C, in that order. C depends on having a real post-v1.0 sprint to record, so order matters.

**Do not:** pick C without A — a slick demo for a project whose News section still says v0.2.0 looks staged, not shipped.

---

## 7. Open questions for CEO before planning kicks off

1. Is `clawteam team spawn gstack` the supported v1.0 flagship syntax, or should the hero be rewritten around `spawn-team <name>`? (Theme B hinges on this.)
2. Is there an existing post-v1.0 artifact (sprint output, testimonial, benchmark) we can cite, or does Theme A need a fresh one generated?
3. Is the `../docs/` output still the production deploy target (GitHub Pages), so we don't need to change build config?

---

*Intent locked. Hand back to ceo for planning/delegation.*
