---
phase: 04
plan: 01
subsystem: planning
tags: [wave-0, substrate-prep, research-resolution, glob-matching, event-bus, spawn-async]
requires: []
provides:
  - ".planning/phases/04-.../PLAN_PREP_NOTES.md with evidence-backed decisions for A4, A5, A6, A7, A9, A11, A-fnmatch, A-spawn"
  - "Custom glob-matching shim `_match_path()` portable to Python 3.10+ (verified against 11 test cases)"
  - "D-18 cleanup baseline (5-line marker count, exact line numbers)"
affects:
  - "Plan 02 (event types)"
  - "Plan 04 (ship gate class name + path)"
  - "Plan 06 (glob engine + TOML parser extension)"
  - "Plan 10 (dispatch review phase file + asyncio bridge)"
  - "Plan 14 (D-18 cleanup regression baseline)"
tech-stack:
  added: []
  patterns: ["evidence-backed-planner-prep", "custom-shim-over-stdlib", "sync-to-async-executor-bridge"]
key-files:
  created:
    - .planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md
  modified: []
decisions:
  - "A-fnmatch: portable custom shim `_match_path()` — neither stdlib `fnmatch.fnmatch` nor `PurePosixPath.match` handles globstar correctly on Python 3.10-3.12; `PurePosixPath.full_match` is 3.13+ only (rejected)."
  - "A4: Plan 10 CREATES `clawteam/sprint/review_phase.py` — no `_dispatch_*_phase` pattern exists today (conductor grep returned empty)."
  - "A5: TOML parser extension lands in one atomic edit — Plan 06 adds `ReviewRule(BaseModel)` + `ReviewConfig(BaseModel)` + `TemplateDef.review` field + `_parse_toml` review block together."
  - "A6: D-18 baseline is 5 grep hits (research said 4; H2 heading `## SHA-PIN-DEFERRED` at `reviewer.md:45` matches the cleanup regex). Plan 14 target: 0 hits."
  - "A7: `EventBus.emit(event: HarnessEvent)` takes typed dataclass instances — Plan 02 adds `MidReviewThrash` + `SycophancyCascadeDetected` as `@dataclass class Foo(HarnessEvent)`."
  - "A9: New gate is `ShipApprovalGate(InteractionGate)` at `clawteam/harness/ship_approval_gate.py` — existing `HumanApprovalGate(PhaseGate)` at `phases.py:91` untouched (zero BC risk)."
  - "A11: `force_interactive_phases` plumbing at conductor.py:19,222,239,247-248,520,522,544 — Plan 04 + Plan 11 do NOT edit the conductor; plugin `contribute_gates` hook is sufficient."
  - "A-spawn: all 3 SpawnBackend implementations are sync `def spawn() -> str` (subprocess/tmux/wsh); Plan 10 uses `loop.run_in_executor(None, _spawn_reviewer_sync, ...)` to parallelize via `asyncio.gather`."
metrics:
  duration: "25min"
  completed: 2026-04-21
---

# Phase 4 Plan 01: Wave 0 Substrate Prep Summary

**One-liner:** Resolved 5 plan-prep research verifications (A4/A5/A7/A9/A11 + glob semantics + spawn sync-vs-async + D-18 baseline) into evidence-backed decisions recorded in `PLAN_PREP_NOTES.md` — each decision row names the downstream consuming plan verbatim so Waves 1-3 never re-guess substrate shape.

## Tasks Completed

| Task | Name | Commit | Key output |
|------|------|--------|------------|
| 1+2+3 | Wave 0 evidence-backed substrate decisions | `c4ae8cc` | `PLAN_PREP_NOTES.md` with 8 `## A*` sections + Decisions Summary table (7 rows) |

Three plan tasks shared one output file (`PLAN_PREP_NOTES.md`) — committed atomically in one commit since the file is only consumable as a whole (individual sections reference each other).

## Commits Made

- `c4ae8cc` — `docs(04-01): write Wave 0 PLAN_PREP_NOTES.md with evidence-backed substrate decisions` (1 file, +699 LOC)

## Files Modified

| Action | Path | Purpose |
|--------|------|---------|
| Created | `.planning/phases/04-.../PLAN_PREP_NOTES.md` | Evidence-backed Wave 0 substrate-prep notes |

## Decisions Made (full detail in PLAN_PREP_NOTES.md Decisions Summary table)

| Item | Decision | Consuming Plan |
|------|----------|----------------|
| Glob engine | Custom shim `_match_path()` on top of stdlib `fnmatch` (portable Python 3.10+; full source verbatim in A-fnmatch section; verified against all 7 fixture cases + 4 edge cases) | Plan 06 |
| Review-phase dispatch | NEW file `clawteam/sprint/review_phase.py`; `async def dispatch_review_phase(state, plugin_manager, bus)` + conductor wrapper `_dispatch_review_phase(self, state)` | Plan 10 |
| Ship gate class name | `ShipApprovalGate(InteractionGate)` at `clawteam/harness/ship_approval_gate.py` | Plan 04 |
| TOML parser edit | `ReviewRule` + `ReviewConfig` + `TemplateDef.review` field + `_parse_toml` extension in ONE atomic commit in `clawteam/templates/__init__.py` | Plan 06 |
| Event type shape | `@dataclass class MidReviewThrash(HarnessEvent)` + `@dataclass class SycophancyCascadeDetected(HarnessEvent)` appended to `clawteam/events/types.py` | Plan 02 |
| Spawn-asyncio bridge | `loop.run_in_executor(None, _spawn_reviewer_sync, role, review_sha)` around synchronous `SpawnBackend.spawn(...)` | Plan 10 |
| D-18 baseline | 5 grep hits at `pm.md:18`, `designer.md:17`, `reviewer.md:40`, `reviewer.md:45` (H2), `reviewer.md:47` — Plan 14 target: 0 | Plan 14 |

## Deviations from Plan

**None mechanically.** All 3 tasks produced their expected sections + artifacts. A few observations worth flagging as plan-set-revision signals (documented verbatim in the `## Surprises` section of `PLAN_PREP_NOTES.md`):

1. **A6 marker count 4 → 5.** Planner expected 4 D-18 marker lines; grep found 5 because the `## SHA-PIN-DEFERRED` H2 heading at `reviewer.md:45` matches the same regex as narrative paragraphs. Plan 14's acceptance criterion is `grep count = 0` (unambiguous).
2. **A11 line-number drift.** Planner expected `force_interactive_phases` at conductor.py:222/247/544; actual is 19/222/239/247-248/520/522/544 — the ctor-param line migrated from 247 → 239 during a Phase 2 docstring revision. All four structurally important lines still present; no plan change needed.
3. **Python version constraint forces shim over stdlib `full_match`.** `PurePosixPath.full_match` (Python 3.13+) would have been a 1-line call but is not portable to `pyproject.toml`'s `requires-python = ">=3.10"`. The shim adds ~35 LOC to Plan 06. Plan 06's test coverage MUST include the 7 fixture cases listed in A-fnmatch to lock globstar semantics.
4. **No existing `_dispatch_*_phase` seam.** Plan 10 is ESTABLISHING a pattern, not extending one. Plan 10 should document the shape as a reusable seam so later Ship/Test phase dispatchers (if added) can follow the same pattern.

**Shim correctness self-verified.** First shim draft passed 6/7 tests (failed `lib/crypto/aes.py` vs `**/crypto/**`); iterated to v3 which passes 11/11 (the 7 fixture cases + 4 additional edge cases for leading/trailing `**` and bare `**`). Final shim embedded verbatim in PLAN_PREP_NOTES.md A-fnmatch section.

## Authentication Gates

None. Wave 0 is pure read-only discovery + notes authoring — no external services touched.

## Next Wave Dependencies Satisfied

Wave 1 plans (02, 04, 06) and Wave 2 plans (10, 14) can grep `PLAN_PREP_NOTES.md` for their consumption contracts without re-running any of the Wave 0 verifications:

- **Plan 02** — opens `## A7` → reads the 2 new `@dataclass` definitions to append verbatim to `clawteam/events/types.py`.
- **Plan 04** — opens `## A9` → uses class name `ShipApprovalGate` + file path `clawteam/harness/ship_approval_gate.py`; reads `## A11` to confirm no conductor edit needed.
- **Plan 06** — opens `## A-fnmatch` → copies the `_match_path()` shim verbatim; opens `## A5` → adds `ReviewRule`/`ReviewConfig` + `TemplateDef.review` field + `_parse_toml` block in one atomic edit.
- **Plan 10** — opens `## A4` → creates `clawteam/sprint/review_phase.py`; opens `## A-spawn` → uses `loop.run_in_executor(None, _spawn_reviewer_sync, ...)` to parallelize `SpawnBackend.spawn()` calls via `asyncio.gather`.
- **Plan 14** — opens `## A6` → uses the 5-line baseline for pre-edit grep assertion; post-edit invariant: `grep -c "INTERACTIVE-RUNTIME-DEFERRED\|SHA-PIN-DEFERRED" clawteam/templates/gstack/prompts/*.md` totals 0.

## Verification

All `<verification>` gates from the plan passed:

- [x] `.planning/phases/04-.../PLAN_PREP_NOTES.md` exists and is non-empty (699 lines, 29KB).
- [x] All 3 tasks completed; sections A4, A5, A6, A7, A9, A11, A-fnmatch, A-spawn all present (8 `## A*` sections; plan required ≥6).
- [x] Empirical grep/python3 output embedded for every section (no "TBD"/"TODO"/"ASSUMED" — `grep -c` returns 0).
- [x] Decisions Summary table has 7 populated rows with consuming-plan numbers.
- [x] D-18 baseline line numbers recorded (format `pm.md:18`, `designer.md:17`, `reviewer.md:40`, `reviewer.md:45`, `reviewer.md:47`).
- [x] A-spawn section names concrete function (`SpawnBackend.spawn`) + concrete backends (subprocess/tmux/wsh).

## Threat Register Status

| Threat ID | Category | Component | Disposition | Outcome |
|-----------|----------|-----------|-------------|---------|
| T-04-01 | I (Info disclosure) | Wave-0 notes file | mitigate | ✅ No secrets in notes; only grep output of public source + planner decisions |
| T-04-02 | T (Tampering) | Grep in wrong dir | mitigate | ✅ All commands used explicit relative paths from repo root; no `cd` |
| T-04-03 | R (Repudiation) | Decision provenance | accept | ✅ Committed `c4ae8cc` under `.planning/` — audit via `git log` |

## Self-Check: PASSED

- `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/PLAN_PREP_NOTES.md` — FOUND (699 lines, committed in `c4ae8cc`).
- Commit `c4ae8cc` — FOUND in `git log`.
