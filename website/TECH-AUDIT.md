# Technical Audit — website/ (React + Vite, deployed to clawteam.us)

- Auditor: eng-mgr
- Sprint context: post-v1.0 landing page
- Scope: dead links, SEO, a11y, responsive, performance
- Deliverable class: edge-case-matrix (plan-eng-review rubric)
- Code changes: NONE (audit-only, per task directive)

## Sources inspected

- `website/index.html` (dev entry)
- `website/vite.config.mjs` (`outDir: ../docs`, `base: "./"`)
- `website/src/main.jsx`, `App.jsx`, `styles.css`
- `docs/index.html` (deployed build artifact — clawteam.us served from `docs/`)
- `docs/skills/clawteam/**` (link-target existence)
- `docs/site-assets/*` (bundle sizes)

No live HTTP fetch performed — findings are from static source + build-artifact inspection. An actual Lighthouse/axe run against the deployed URL would surface additional runtime findings.

## Severity summary

| Severity | Count |
| --- | --- |
| HIGH | 4 |
| MED | 7 |
| LOW | 4 |

Any HIGH is a ship-blocker on the next website revision per eng-mgr plan-review norms.

---

## 1. Dead / broken links

| ID | Severity | Target | Actual state at deploy root | Fix sketch |
| --- | --- | --- | --- | --- |
| L1 | **MED** | `skills/clawteam/SKILL.md` (App.jsx:57, 285) | File exists at `docs/skills/clawteam/SKILL.md` — path **resolves**. However it is served as raw Markdown (`.nojekyll` present, GH Pages will not render). Browsers receive `text/markdown` or `text/plain` — most download the file or show raw source. User expects a rendered doc page. | Either (a) link to the GitHub rendered URL `https://github.com/HKUDS/ClawTeam/blob/main/skills/clawteam/SKILL.md`, or (b) add a build step that converts the skill `.md` files to HTML (docusaurus / mdBook / markdown-it + a minimal template). Route (a) is a 5-minute fix; (b) is the right long-term answer. |
| L2 | **MED** | `skills/clawteam/references/cli-reference.md` (App.jsx:58, 228, 285) | Same as L1 — file exists, serves raw. | Same as L1. |
| L3 | **MED** | `skills/clawteam/references/workflows.md` (App.jsx:59) | Same as L1 — file exists, serves raw. | Same as L1. |
| L4 | LOW | `#top`, `#features`, `#gstack`, `#workflow`, `#docs` (App.jsx:215–216) | All anchor IDs exist in the DOM ✓. No action. | — |
| L5 | LOW | `https://github.com/HKUDS/ClawTeam#-quick-start` (App.jsx:56, 227) | External — not verified in-audit. README should have a `## 🚀 Quick Start` heading generating that anchor. | Spot-check manually or run a link checker (`lychee`) as a CI step. |

**Net**: no truly dead paths, but three card CTAs hit raw `.md` files — functionally broken UX. Treat as MED, not LOW.

---

## 2. SEO meta

Deployed `docs/index.html` (the served artifact) has only: charset, viewport, `description`, `title`. Everything below is **missing**:

| ID | Severity | Missing tag | Impact | Fix sketch (at `website/index.html` head) |
| --- | --- | --- | --- | --- |
| S1 | **HIGH** | `og:title`, `og:description`, `og:image`, `og:url`, `og:type="website"` | No social-share preview card. LinkedIn/Twitter/Slack posts render a blank or text-only unfurl — bad for a launch page. | Add 5 `<meta property="og:*">` tags. `og:image` should be `assets/teaser.png` (already in repo) rebuilt as 1200×630. |
| S2 | **HIGH** | `twitter:card="summary_large_image"`, `twitter:title`, `twitter:description`, `twitter:image` | Same as S1 for Twitter/X. | Mirror og:* values. |
| S3 | **MED** | `<link rel="canonical" href="https://clawteam.us/">` | Search engines may index duplicate trailing-slash / parameter variants separately. | One-line add. |
| S4 | **MED** | `<link rel="icon" href="...">` / apple-touch-icon | No favicon is declared — browsers fall back to `/favicon.ico` which does not exist in `docs/`. Tab shows generic globe icon. | Add `<link rel="icon" type="image/png" href="./site-assets/icon-rGtQ3W93.png">` (or better, bundle a small dedicated favicon — see P1). |
| S5 | LOW | `<meta name="theme-color" content="#09090b">` | Mobile browser chrome doesn't match page background. | One-line add. |
| S6 | LOW | `<meta name="robots" content="index,follow">` | Default already `index,follow`, but explicit is clearer. Optional. | Skip unless a no-index is ever needed. |

**Ship blockers**: S1 and S2. A marketing page without og:image is a self-inflicted wound on launch day.

---

## 3. Accessibility (static smoke)

| ID | Severity | Finding | File:line | Fix sketch |
| --- | --- | --- | --- | --- |
| A1 | **HIGH** | **No `:focus-visible` styles defined anywhere** in `styles.css`. Keyboard users cannot see which element is focused — all buttons, nav links, and doc cards rely on default browser outline which is often suppressed by agent stylesheets or interacts badly with the dark theme. | styles.css (absent) | Add a global rule: `a:focus-visible, button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 4px; }`. Cost: 4 lines. |
| A2 | **MED** | `--text-dim: #52525b` on `--bg: #09090b` ≈ **3.1:1 contrast** — fails WCAG 2.1 AA (4.5:1 for normal text). Used in: `.orbit-label` (styles.css:280), `.terminal-title` (337), `.terminal-output-block .t-dim` (377), `.footer` (828), `.step-num` label copy elsewhere. | styles.css:11 (token) | Lighten `--text-dim` to `#71717a` (≈ 4.8:1) or `#8a8a93`. Check that none of the contrasts relying on this become mushier than intended. |
| A3 | MED | `--text-secondary: #a1a1aa` on `--bg` ≈ **4.6:1** — passes AA by a hair, fails AAA. Used extensively (hero-sub, card bodies). | styles.css:9 | Bump to `#b4b4bd` if you want margin of safety. Not a blocker. |
| A4 | MED | No `prefers-reduced-motion` handling. The globe canvas spins continuously and agents pulse; the terminal cursor blinks; hover transforms translateY. Users with vestibular disorders get full motion. | App.jsx:170 (raf loop), styles.css:437 (blink), others | Add at top of styles.css: `@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }`. In App.jsx:80–174, early-return the rAF loop (but still draw a single static frame) when `window.matchMedia('(prefers-reduced-motion: reduce)').matches`. |
| A5 | LOW | SVG client icons (IconClaude, IconCodex, etc.) in App.jsx:4–33 have no `aria-hidden="true"` despite being decorative (each is rendered next to a visible `<span>` label). Screen readers may announce the raw SVG paths or nothing, depending on engine. | App.jsx:4–33 | Add `aria-hidden="true"` to the `<svg>` tag of all five icon components. |
| A6 | LOW | Nav has `<nav>` landmark ✓, but no `aria-label` distinguishing it from the footer links. Multiple nav landmarks without labels confuse screen readers. | App.jsx:216, 283 | `<nav aria-label="Primary">` and `<nav aria-label="Footer">` (or convert footer to a plain `<div>` since it's already inside `<footer>`). |
| A7 | LOW | No skip-link for keyboard users. Tab order forces through nav every page load. | App.jsx:211 | Add `<a className="skip-link" href="#top">Skip to content</a>` as first child; style off-screen until `:focus`. |

Canvas treatment: ✓ `aria-hidden="true"` set correctly (App.jsx:178–179, 181–182).

---

## 4. Responsive breakpoints

| ID | Severity | Breakpoint | Finding | Fix sketch |
| --- | --- | --- | --- | --- |
| R1 | **MED** | 375px (iPhone SE) | `.terminal-line { white-space: nowrap }` (styles.css:351) combined with `.terminal { overflow: hidden }` (styles.css:313) clips long command lines like `clawteam spawn tmux claude-code --agent-name builder` (50+ chars @ 0.8rem mono). Users see truncated commands — the marquee feature of the page is an unreadable mockup on mobile. | styles.css:351, 343–348 | Two options: (a) at `@media (max-width: 600px)`: shrink `.terminal-body` font to `0.68rem`, or (b) allow wrap: `white-space: pre-wrap` and accept 2-line commands. (a) preserves the mockup aesthetic; (b) preserves readability. Prefer (b) + mono font keeps it terminal-like. |
| R2 | LOW | 375px | Hero h1 `clamp(2rem, 9vw, 2.8rem)` → at 375px = 33.75px → 2.11rem. Legible. OK. | — |
| R3 | LOW | 768px | `.hero` collapses to 1-col at 960px (styles.css:846), good. `.steps` collapses at 960 too, good. Between 600px and 960px the `.phase-pill` uses `flex: 1 1 calc(33% - 8px)` which can yield awkward widths but doesn't break. | Optional polish. |
| R4 | LOW | 600px | Orbit labels `nanobot` and `any` are `display: none` (styles.css:935) — acknowledged trade-off; three labels remain. No issue. | — |
| R5 | LOW | Zoomed 200% (a11y reflow) | Not statically verifiable. Likely OK because most containers use `max-width` + clamp. | Manual verification recommended before next ship. |

---

## 5. Performance

| ID | Severity | Finding | Evidence | Fix sketch |
| --- | --- | --- | --- | --- |
| P1 | **HIGH** | **`icon-rGtQ3W93.png` is 816 KB** and is the single largest asset on the page. It is imported at `App.jsx:2` as the header logo, rendered at 32×32 px (`.logo img { width: 32px; height: 32px; }` styles.css:105). Shipping ~820 KB to display 1024 px² is a ~100× waste. Also blocks LCP if it is above the fold. | `du -h docs/site-assets/icon-rGtQ3W93.png` → 816K | (a) Resize source `assets/icon.png` to 128×128 (for retina) and reconvert to WebP — expect ≤ 10 KB. (b) Import `icon.webp` with a PNG fallback if needed. (c) Separately ship a small favicon (32×32 ICO or PNG) for S4. Do NOT ship the full-resolution icon unless it's used as an OG image (and even then, compress). |
| P2 | **MED** | `@import url("https://fonts.googleapis.com/css2?family=Inter...&family=JetBrains+Mono...&display=swap")` at styles.css:1. CSS `@import` creates a render-blocking waterfall: HTML → CSS parse → fonts.googleapis.com → fonts.gstatic.com. Costs ~200–400 ms on cold loads. | styles.css:1 | Move to `<head>` in `website/index.html`: `<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap">`. Remove the `@import` line. |
| P3 | MED | No `visibilitychange` handler on the canvas rAF loop (App.jsx:170). Modern browsers throttle rAF in hidden tabs (usually to 1 Hz or full pause) so real impact is small, but there is no defensive handling — on some platforms (Firefox with background tabs prefs, Safari in certain BF-cache states, Electron wrappers) the loop can keep running and drain CPU/battery. | App.jsx:170–174 | Inside `useEffect`, add: `const onVis = () => { if (document.hidden) cancelAnimationFrame(raf); else raf = requestAnimationFrame(draw); }; document.addEventListener('visibilitychange', onVis);` and clean up in the return. |
| P4 | LOW | Scroll handler is `{passive: true}` ✓ (App.jsx:172). Good. No action. | App.jsx:172 | — |
| P5 | LOW | JS bundle 161 KB (minified, not gzipped). Reasonable for React + app code. CSS 13 KB. Acceptable. | `docs/site-assets/*` | Optional: add Brotli precompression in the deployment layer (GH Pages doesn't support custom compression; most browsers get gzip automatically). Not actionable without a different host. |
| P6 | LOW | `emptyOutDir: false` in vite.config.mjs:15 — stale asset files accumulate in `docs/` over time, inflating the repo and risking orphaned references if hashed filenames change. | vite.config.mjs:15 | Either flip to `true` and accept the diff churn, or add a prebuild script that prunes `docs/site-assets/*` before Vite writes. Today this is cosmetic; it will become a real problem if someone deletes a hashed asset and the old one is still referenced by a cached HTML. |

---

## Overall scorecard

| Pillar | Verdict | Critical blockers |
| --- | --- | --- |
| Dead links | **FLAG** — all paths resolve, but three card CTAs deliver raw Markdown | L1, L2, L3 |
| SEO | **BLOCK** — missing og/twitter cards and favicon | S1, S2, S4 |
| A11y | **BLOCK** — no focus-visible styles, text-dim fails AA contrast | A1, A2 |
| Responsive | **PASS with a MED fix** — terminal mockup clips on 375px | R1 |
| Performance | **BLOCK** — 816 KB logo; render-blocking font import | P1, P2 |

Four HIGH items (S1, S2, A1, P1) are ship-blockers on the next website revision. Per plan-review precedent (architecture-lock rubric), merging the fix set should be **one bundled change** — the whole audit shares the same file (`website/src/App.jsx`, `styles.css`, `index.html`) and splitting would be churn.

## Recommended next step

- Route this doc to `designer` + `engineer` for a single fix-pass sprint.
- Eng-mgr re-review required only if HIGH fixes are deferred.
- No architecture-lock change needed; this is execution-layer cleanup.

— eng-mgr · 2026-04-23
