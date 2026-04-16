---
phase: 00-foundation-upstream-rfc
plan: 07
subsystem: docs
tags: [rfc, upstream, phase-registry, plugin-hooks, gap-closure, harnessplugin, contribute_phase_roles, contribute_review_routers]

requires:
  - phase: 00-05-upstream-rfc
    provides: "RFC 001 covering PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate; 8-section Rust-style structure and software-dev.toml worked compatibility baseline."
provides:
  - "Expanded RFC 001 documenting all three optional HarnessPlugin hooks (`contribute_phases`, `contribute_phase_roles`, `contribute_review_routers`) with empty-collection defaults and additive-only guarantees."
  - "Forward-declared `ReviewRouter` Protocol shape (Phase 1 locks the hook point; full interface deferred to Phase 4 RFC)."
  - "Extended §4.7 Compatibility Guarantees (5 → 8 items) explicitly covering each hook's empty default."
  - "Extended §4.8 Worked Example showing software-dev.toml unchanged with all three hooks defaulting to empty."
  - "RFC index title cell (docs/rfcs/README.md) synced with the three-hook RFC title."
affects:
  - phase-01-core-harness-extensions
  - phase-04-interactive-routing-verification
  - upstream-rfc-review

tech-stack:
  added: []
  patterns:
    - "Sibling subsection pattern: mirror existing §4.3 shape (signature → Requirements list → empty-default-matters paragraph → ABC ASCII box → plugin-use example → empty-default-behavior one-liner) for each new hook"
    - "Surgical RFC expansion preserving every non-targeted paragraph verbatim; additive §4.3a / §4.3b numbering leaves §4.4-§4.8 cross-references intact"
    - "Forward declaration of Phase 4 surface (`ReviewRouter` Protocol) without locking the full interface"

key-files:
  created:
    - .planning/phases/00-foundation-upstream-rfc/00-07-rfc-expand-hooks-SUMMARY.md
  modified:
    - docs/rfcs/001-phase-registry.md
    - docs/rfcs/README.md

key-decisions:
  - "Preserved §4.3 original body verbatim as the anchor shape; added §4.3a and §4.3b as siblings rather than rewriting or renumbering — keeps existing §4.4-§4.8 section numbers and internal cross-references stable."
  - "Forward-declared `ReviewRouter` as a `typing.Protocol` with a single `match(diff_paths, state) -> list[AgentRole]` method; deferred full interface (rule-file format, SHA-pinning semantics, multi-signal aggregation) to a future Phase 4 RFC. Phase 1 only locks the hook point."
  - "Rewrote §8 Q5 (now-answered by §4.3a) to a genuine open question about review-router precedence ordering (load-order vs explicit priority hint). Kept Q count at 6."
  - "Expanded Section 1 Summary from 'four primitives' to 'six primitives' grouped as 1 registry + 3 hooks + 2 runtime types, with an explicit justification paragraph for why the three hooks are proposed together (shared design invariant: single additive extension surface)."
  - "Extended §4.7 from 5 guarantees to 8, with each new hook's empty-collection default and APPEND-only Review-router semantics called out explicitly."

patterns-established:
  - "Gap-closure plans on documentation artifacts are surgical expansions that match the acceptance criterion verbatim, not rewrites — future doc gaps should follow this add-subsection-mirroring-existing-shape pattern."
  - "When a new hook is added to the plugin ABC, redraw the ASCII relation box in the same subsection, preserving the cumulative set of methods. This keeps each subsection self-contained for upstream review readers."

requirements-completed: []

# Metrics
duration: 5 min 23 sec
completed: 2026-04-16
---

# Phase 0 Plan 07: RFC Expand Hooks Summary

**Expanded RFC 001 from one `HarnessPlugin` hook (`contribute_phases`) to all three named in Phase 0 success criterion #4 (`contribute_phases` + `contribute_phase_roles` + `contribute_review_routers`), each with signature, empty-collection default, additive-only contract, and a gstack-illustrative plugin-use example; `software-dev.toml` worked baseline now shows all three hooks defaulting to empty.**

## Performance

- **Duration:** 5 min 23 sec
- **Started:** 2026-04-16T10:52:24Z
- **Completed:** 2026-04-16T10:57:47Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Closed Phase 0 UAT Gap 2 (test 6, severity major): RFC 001 now names and specifies all three optional HarnessPlugin hooks — the UAT evidence `grep contribute_(phase_roles|review_routers) docs/rfcs/001-phase-registry.md` moves from 0 hits each to 14 and 12 hits respectively.
- Satisfied ROADMAP Phase 0 success criterion #4 in full (three optional hooks with empty defaults, PhaseRegistry class shape, additive-only guarantees, and a worked software-dev.toml example showing unchanged behavior).
- Added §4.3a (`contribute_phase_roles()`) and §4.3b (`contribute_review_routers()`) mirroring the existing §4.3 shape — each with signature, numbered Requirements list, empty-default paragraph, updated HarnessPlugin ABC ASCII box, gstack-illustrative plugin-use code example, and closing empty-default-behavior one-liner.
- Extended §4.7 Compatibility Guarantees from 5 to 8 items covering each hook's empty-collection default, APPEND-only Review-router semantics, and independence between the three hooks.
- Extended §4.8 Worked Example trace + behavior list (5 → 8 items) documenting that `software-dev.toml` gets zero behavior change because all three hooks return empty collections.
- Rewrote §8 Q5 (now answered by §4.3a) to a genuine open question about review-router precedence ordering (load-order vs explicit priority hint); Q list remains 6 items.
- Synchronized RFC index row in `docs/rfcs/README.md` with the expanded RFC title cell so a reader scanning the index sees all three hooks named.
- Forward-declared `ReviewRouter` as a `typing.Protocol` with a single `match()` method, deferring full interface (rule-file format, SHA-pinning, multi-signal aggregation) to a future Phase 4 RFC — Phase 1 only locks the hook point.

## Task Commits

Each task was committed atomically with `--no-verify` (parallel executor mode):

1. **Task 1: Expand RFC 001 to cover all three HarnessPlugin hooks** — `772bdbd` (docs)
2. **Task 2: Update docs/rfcs/README.md index to reflect expanded RFC title** — `b1f6919` (docs)

## Files Created/Modified

- `docs/rfcs/001-phase-registry.md` — Expanded from 637 lines to 846 lines (+231 insertions, -22 deletions in Task 1 commit). Frontmatter `title:`, H1, §1 Summary, §4.3-closing, §4.3a (new), §4.3b (new), §4.7 Compatibility Guarantees, §4.8 Worked Example trace + behavior list, and §8 Q5 all updated. §4.3 body, §4.4-§4.6, §2-§3, §5-§7 preserved verbatim.
- `docs/rfcs/README.md` — Line 27 (RFC 001 index row) title cell updated to name all three hooks. Preamble, process section, link target, status cell (`Draft`), and target-phase cell (`Phase 1`) preserved verbatim.
- `.planning/phases/00-foundation-upstream-rfc/00-07-rfc-expand-hooks-SUMMARY.md` — this execution summary.

## Decisions Made

- **Additive subsection numbering (§4.3a / §4.3b) instead of renumbering §4.4-§4.8.** Rationale: Plan 05's §4.4-§4.8 bodies are unchanged substrate; renumbering would break upstream PR diff readability and any future internal cross-references. `4.3a` / `4.3b` numbering is a standard RFC device for insertions between existing sections.
- **`ReviewRouter` forward-declared as a Protocol, not fully specified.** Rationale: Plan 05's scope discipline ("only Phase 1 primitives are specified normatively") extends here; the full `ReviewRouter` interface belongs to the Phase 4 RFC that will land review routing code. The Phase 1 RFC only needs to lock the hook point so Phase 1's plugin ABC accepts `contribute_review_routers()` without binding upstream reviewers to interface details that may shift by Phase 4.
- **Summary count change from 'four primitives' to 'six primitives' (1 registry + 3 hooks + 2 types) with an explicit justification paragraph.** Rationale: The plan asked for a grouped enumeration; the justification paragraph ("shared design invariant: single additive extension surface, not three different mechanisms in three different RFCs") pre-empts the obvious upstream reviewer question "why not three separate RFCs?"
- **§8 Q5 rewritten to review-router precedence ordering instead of deleted.** Rationale: The plan explicitly offered either option (rewrite OR delete and renumber). Rewriting preserves the Q count at 6 and opens a concrete Phase 4 discussion ("load-order vs explicit priority hint") with a recommendation baked in (start with load-order, match PhaseRegistry §4.2 rule).
- **§4.3 closing sentence replaced with a bridge paragraph, not deleted.** Rationale: The original "No other plugin methods need semantic changes to support this RFC" is factually wrong after the expansion (now three plugin hooks, not one). The bridge paragraph preserves the transition flow from §4.3 into §4.3a / §4.3b while stating the new-shape invariant ("empty collection default, no abstract-method requirement, no side effects beyond plugin-scoped registry at load time").

## Deviations from Plan

None - plan executed exactly as written.

**Total deviations:** 0 auto-fixed (0 Rule 1, 0 Rule 2, 0 Rule 3)
**Impact on plan:** None.

## Issues Encountered

- Worktree base commit on spawn was `bc69bc0c` instead of the required `3f3411da`. Hard-reset to `3f3411da` per the worktree_branch_check protocol; reset succeeded on first try. Cause: normal parallel executor setup — one of the previously-merged wave-1/2 agents had advanced the integration branch locally.
- `.planning/STATE.md` showed as modified in the working tree at startup (diff against base shows progress counters and timestamps bumped by the orchestrator when dispatching this wave). Per parallel_execution rules, STATE.md was deliberately excluded from both task commits; only explicit `git add docs/rfcs/*.md` staging was used so the STATE.md diff remained in the working tree untouched.

## User Setup Required

None - no external service configuration required. This is a docs-only scope expansion; no Python code, no environment variables, no new dependencies.

## Next Phase Readiness

- Phase 0 UAT test 6 (Gap 2) is now green: RFC 001 documents all three optional HarnessPlugin hooks with signatures, empty defaults, additive-only contracts, and software-dev.toml worked example.
- Phase 0 ROADMAP success criterion #4 is fully satisfied.
- Phase 1 implementation plan (when it comes) can now reference `contribute_phase_roles()` and `contribute_review_routers()` by name knowing the upstream-facing RFC locks their signatures and empty-default semantics.
- Phase 4 (routing/verification) has a hook point reserved in the Phase 1 RFC (`contribute_review_routers` + `ReviewRouter` Protocol forward-declaration). The full `ReviewRouter` interface is explicitly deferred — Phase 4's own RFC will specify rule-file format, SHA-pinning, and multi-signal aggregation.
- Out-of-band follow-up still pending (not in this plan's scope): the human owner opens the upstream PR against HKUDS/ClawTeam with these two expanded files; obtains ≥1 maintainer acknowledgement before Phase 1 code lands per ROADMAP Phase 0 success criterion 4.
- BC regression confirmed: `.venv-sys/bin/python -m pytest tests/ -q --tb=no -x` → 610 passed, 0 failed (docs-only plan touched no Python).

## Self-Check: PASSED

- Found: `docs/rfcs/001-phase-registry.md` (modified, 846 lines, ≥750 target)
- Found: `docs/rfcs/README.md` (modified, three hooks named in index row)
- Found: commit `772bdbd` — `docs(00-07): expand RFC 001 to document contribute_phase_roles and contribute_review_routers hooks`
- Found: commit `b1f6919` — `docs(00-07): sync RFC index title with expanded RFC 001 (three hooks)`
- Verified: §4.3, §4.3a, §4.3b all present with correct heading format
- Verified: all 8 numbered sections (§1-§8) still present
- Verified: §4.4 (`SprintState`), §4.5 (`InteractionGate`), §4.6 (Integration Contract) unchanged section numbers
- Verified: `contribute_phase_roles` mentioned 14 times (plan target: ≥2)
- Verified: `contribute_review_routers` mentioned 12 times (plan target: ≥2)
- Verified: all three method signatures appear in python fences
- Verified: BC regression 610 tests pass

---
*Phase: 00-foundation-upstream-rfc*
*Completed: 2026-04-16*
