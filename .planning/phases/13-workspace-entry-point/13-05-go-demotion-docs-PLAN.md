---
phase: 13
plan: 05
type: execute
wave: 4
depends_on: [01, 02, 03, 04]
files_modified:
  - clawteam/solo.py
  - README.md
autonomous: true
requirements: [WS-03]
must_haves:
  truths:
    - "`clawteam go --help` help tagline contains the word 'shortcut' and references `open` or `sprint start`"
    - "`clawteam go \"build X\"` runtime behavior is byte-identical to HEAD — no functional change"
    - "README Quick Start / Primary Flow leads with `clawteam open` + `clawteam sprint start`, not `clawteam go`"
    - "`clawteam go` appears in a 'Shortcuts' subsection, still visible, no longer primary"
    - "No deprecation warning, no `--legacy` flag — zero-break migration for scripts/CI"
  artifacts:
    - path: clawteam/solo.py
      provides: "Reworded go help tagline under Daily use panel"
      contains: "one-shot: open + sprint start"
    - path: README.md
      provides: "Primary flow rewritten to `open` + `sprint start`; `go` moved to Shortcuts subsection"
      contains: "clawteam open"
  key_links:
    - from: "clawteam/solo.py::register_solo_commands (go registration)"
      to: "`clawteam go --help` output"
      via: "rich_help_panel + help= kwarg"
      pattern: "help=\"one-shot: open \\+ sprint start\""
    - from: "README.md ⚡ Primary Flow section"
      to: "clawteam open command"
      via: "canonical example"
      pattern: "clawteam open gstack"
---

<objective>
Demote `clawteam go` from primary flow to documented shortcut per WS-03. Two surgical edits:
1. Reword the `go` help tagline in `register_solo_commands` so `clawteam go --help` describes it as a shortcut for `open` + `sprint start`.
2. Rewrite the README's Primary Flow section so `clawteam open` + `clawteam sprint start` is the canonical example; `go` moves to a "Shortcuts" subsection.

Per 13-CONTEXT `go demotion` block:
- `go` STAYS in the `🎯 Daily use (solo)` Rich help panel — not hidden, just reworded
- Runtime semantics unchanged: `go <goal>` still = create team + start sprint + launch panes
- For existing team + new sprint, users compose `open` + `sprint start` (no extending `go` to take `--team <existing>`)
- Zero-break migration for scripts/CI: no deprecation warning, no `--legacy` flag, only docs change

Purpose: WS-03 complete. Phase 13 ships.

Output: 1-line tagline change in solo.py + README Primary Flow rewrite (two sections touched, third section added).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/phases/13-workspace-entry-point/13-CONTEXT.md
@.planning/phases/13-workspace-entry-point/13-VALIDATION.md
@clawteam/solo.py
@README.md
@tests/cli/test_commands.py

<interfaces>
<!-- Current `go` registration (solo.py:784-788 after Plan 13-04's edits): -->
```python
app.command(
    "go",
    help="Start work: create team + start sprint + launch agents (one-shot)",
    rich_help_panel=panel,
)(cmd_go)
```

<!-- Current README ⚡ Primary Flow (README.md:404-423): -->
```markdown
### ⚡ Primary Flow

​```bash
# Start a gstack team and sprint for one goal
clawteam go "Build the auth module"

# Check phase, tasks, agents, and pending questions
clawteam status

# Answer agent questions when status shows pending questions
clawteam answer

# Stop the active team and clean up when the sprint is done
clawteam stop
​```

`clawteam go` defaults to the gstack template, opens/attaches to the tmux team
view when possible, and writes the active-team pointer used by `status`,
`answer`, and `stop`. Pass `--no-attach` if you want to keep your current shell
free and use `clawteam status` as the main dashboard.
```

<!-- Current README Command Reference block (README.md:664-670) lists `go` first under "Solo workflow". Plan 13-05 updates this too. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Reword `go` help tagline in solo.py</name>
  <read_first>
    - clawteam/solo.py lines 779-810 (register_solo_commands — after Plan 13-04's insertion)
    - tests/cli/test_commands.py (the RED test that this task turns GREEN)
  </read_first>
  <behavior>
    - `clawteam go --help` output contains the word "shortcut" (case-insensitive)
    - `clawteam go --help` output references `open` or `sprint start`
    - `clawteam --help` still shows `go` under the `🎯 Daily use (solo)` panel (not hidden)
    - `cmd_go` function signature and body are UNCHANGED (runtime BC)
  </behavior>
  <action>
    In `clawteam/solo.py::register_solo_commands` (around line 784 after Plan 13-04's edits), change the `go` help tagline. ONE line change:

    BEFORE:
    ```python
    app.command(
        "go",
        help="Start work: create team + start sprint + launch agents (one-shot)",
        rich_help_panel=panel,
    )(cmd_go)
    ```

    AFTER:
    ```python
    app.command(
        "go",
        help="One-shot shortcut: `open` + `sprint start` in one command (advanced)",
        rich_help_panel=panel,
    )(cmd_go)
    ```

    Explicitly:
    - Contains "shortcut" (required for test_go_help_tagline_is_shortcut)
    - References `open` and `sprint start` (required for test_go_help_tagline_is_shortcut second assertion)
    - Stays under the same `panel` variable (🎯 Daily use (solo)) — still visible, just reworded
    - The `"(advanced)"` suffix mirrors the 13-CONTEXT wording: "Documented as advanced/one-shot, not the primary flow"

    Do NOT touch `cmd_go` itself. Do NOT touch any other command registration. This is a 1-line change.
  </action>
  <verify>
    <automated>uv run pytest tests/cli/test_commands.py -x -v 2>&1 | tail -15 && uv run clawteam go --help 2>&1 | head -10</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "One-shot shortcut: \`open\` + \`sprint start\`" clawteam/solo.py` returns 1
    - `grep -c "Start work: create team + start sprint + launch agents (one-shot)" clawteam/solo.py` returns 0 (old tagline removed)
    - `uv run clawteam go --help 2>&1 | grep -c -i "shortcut"` returns ≥ 1
    - `uv run clawteam go --help 2>&1 | grep -c -E "open|sprint start"` returns ≥ 1
    - `uv run pytest tests/cli/test_commands.py::TestGoDemotion::test_go_help_tagline_is_shortcut -x` exits 0
    - `uv run pytest tests/cli/test_commands.py::TestGoDemotion::test_go_runtime_signature_unchanged -x` exits 0
    - `git diff clawteam/solo.py | grep -c '^[-+][^-+]'` returns ≤ 4 (1 deletion + 1 addition + BC noise)
  </acceptance_criteria>
  <done>Tagline reworded; both Plan 13-01 go-demotion tests GREEN; cmd_go runtime unchanged.</done>
</task>

<task type="auto">
  <name>Task 2: Rewrite README Primary Flow to lead with `open` + `sprint start`</name>
  <read_first>
    - README.md lines 380-474 (full Quick Start section, Primary Flow + Advanced Flow)
    - README.md lines 660-703 (Command Reference block — the second place to update)
  </read_first>
  <action>
    Edit `README.md`. Three regions to update:

    **Region 1 — `### ⚡ Primary Flow` (lines 404-423):**

    REPLACE the current block with:

    ```markdown
    ### ⚡ Primary Flow

    The daily workflow is *workspace-style* — open your team first, then commit
    to a goal when you're ready.

    ​```bash
    # 1. Open a gstack team (no goal required — agents boot as clean claude REPLs)
    clawteam open gstack -n my-team

    # 2. Chat with the CEO pane to scope your idea, then commit to a goal
    clawteam sprint start my-team --goal "Build the auth module"

    # 3. Track progress; answer agent questions as they come up
    clawteam status
    clawteam answer

    # 4. Shut down cleanly when the sprint is done
    clawteam stop
    ​```

    `clawteam open` lands you inside a live 11-pane tmux team with no kickoff
    prompt burned. Use the CEO pane (or any agent pane) as an interactive REPL
    to refine what you want to build. When you're ready to start the sprint,
    `clawteam sprint start` delivers the kickoff to every pane at that moment.

    #### Shortcuts

    If you already know exactly what you want to build and don't need the
    pre-sprint chat loop, `clawteam go` composes `open` + `sprint start` into
    a single one-shot command:

    ​```bash
    clawteam go "Build the auth module"
    # Equivalent to:
    #   clawteam open gstack -n <auto-generated>
    #   clawteam sprint start <auto-generated> --goal "Build the auth module"
    ​```

    Use `go` for scripted / CI-style invocations where the goal is known
    upfront. Use `open` + `sprint start` for interactive day-to-day work.
    ```

    **Region 2 — Command Reference "Solo workflow" block (lines 664-670):**

    REPLACE:
    ```bash
    # ⭐ Solo workflow
    clawteam go "Build X"                    # create team + sprint + launch
    clawteam status                          # active-team dashboard
    clawteam answer                          # answer pending questions
    clawteam stop                            # clean shutdown
    ```

    WITH:
    ```bash
    # ⭐ Solo workflow (workspace-style)
    clawteam open gstack -n <team>           # open team, no goal required
    clawteam sprint start <team> --goal "X"  # commit to a goal, kick off agents
    clawteam status                          # active-team dashboard
    clawteam answer                          # answer pending questions
    clawteam stop                            # clean shutdown

    # ⭐ Shortcut: go = open + sprint start in one command
    clawteam go "Build X"                    # one-shot (advanced)
    ```

    **Region 3 — Do NOT edit any other section.** Specifically:
    - Do NOT edit README_CN.md or README_KR.md (those are separate translations; user didn't ask for them)
    - Do NOT edit the `### 🔧 Advanced Manual Flow` section (the `clawteam launch --goal` example there is independent and still valid)
    - Do NOT edit the `### 🤖 Agent-Assisted Flow` section

    Rationale: surgical scope per CLAUDE.md §3. Only the blocks that reference `go` as the primary / only flow get updated.
  </action>
  <verify>
    <automated>grep -c "clawteam open gstack" README.md && grep -c "clawteam sprint start" README.md && grep -c "Shortcut: go" README.md</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "clawteam open gstack" README.md` returns ≥ 2 (primary flow block + shortcut/command-ref block)
    - `grep -c "clawteam sprint start" README.md` returns ≥ 2 (primary flow + command reference)
    - `grep -c "#### Shortcuts" README.md` returns 1
    - `grep -c "workspace-style" README.md` returns ≥ 1
    - `grep -c "clawteam go \"Build" README.md` returns ≥ 1 (go still visible in Shortcuts)
    - `grep -c "one-shot (advanced)" README.md` returns 1
    - The Advanced Manual Flow section still exists (spot-check by `grep -c "### 🔧 Advanced Manual Flow" README.md` returning 1)
    - No changes to README_CN.md / README_KR.md (git diff shows only README.md modified for this task)
  </acceptance_criteria>
  <done>README Primary Flow leads with `open` + `sprint start`; Shortcuts subsection exists; go still visible; zero-break migration preserved.</done>
</task>

<task type="auto">
  <name>Task 3: Final Wave 4 gate — full suite + VALIDATION.md task-ID map + per-task-map status update</name>
  <read_first>
    - .planning/phases/13-workspace-entry-point/13-VALIDATION.md (per-task map with ⬜ pending cells)
  </read_first>
  <action>
    Step 1: Run the full suite one last time:
    ```bash
    uv run pytest tests/ --ignore=tests/integration/test_phase7_ten_sprint_load.py --tb=no -q 2>&1 | tail -15
    ```

    Expected: ALL tests GREEN (or existing-v1.1 pre-existing flakes noted in STATE.md, which were 9 out of 1741 on v1.1 close). Zero Phase 13 failures.

    Step 2: Update `.planning/phases/13-workspace-entry-point/13-VALIDATION.md` per-task-map:
    - Fill in real Task IDs for the four rows (e.g., `13-01-02` for the adapter test lives under Plan 13-01)
    - Set `Status` column from `⬜ pending` to `✅ green` for all four rows
    - Append a line below the table: `*Phase 13 complete 2026-04-24 — all 4 REQs GREEN in automated suite. Manual walkthrough pending (`clawteam open gstack -n uat13` → 11 clean REPLs → `clawteam sprint start uat13 --goal "X"` → 11 injections).*`

    Step 3: Print a final summary to console listing:
    - Wave 1 ✅ test scaffolding
    - Wave 2 ✅ adapter gating + sprint-start kickoff
    - Wave 3 ✅ open command
    - Wave 4 ✅ go demotion + docs
    - Next: live UAT per VALIDATION.md `Manual-Only Verifications` table (CachyOS + fish shell machine) — expected failure mode: none, but offer the walkthrough per the "live UAT > automated tests" memory rule.
  </action>
  <verify>
    <automated>uv run pytest tests/ --ignore=tests/integration/test_phase7_ten_sprint_load.py --tb=no -q 2>&1 | tail -5 && grep -c "Phase 13 complete 2026-04-24" .planning/phases/13-workspace-entry-point/13-VALIDATION.md</automated>
  </verify>
  <acceptance_criteria>
    - Full suite shows zero NEW failures vs. v1.1 baseline (any pre-existing flakes acceptable — STATE.md lists up to 9)
    - `grep -c "Phase 13 complete 2026-04-24" .planning/phases/13-workspace-entry-point/13-VALIDATION.md` returns 1
    - `grep -c "⬜ pending" .planning/phases/13-workspace-entry-point/13-VALIDATION.md` returns 0
    - `grep -c "✅ green" .planning/phases/13-workspace-entry-point/13-VALIDATION.md` returns ≥ 4
    - The final summary is printed to the execute-phase console output
  </acceptance_criteria>
  <done>Full suite GREEN; VALIDATION.md map updated; user informed that manual UAT walkthrough is the remaining gate.</done>
</task>

</tasks>

<verification>
```bash
# Phase 13 complete gate:
uv run pytest tests/ --ignore=tests/integration/test_phase7_ten_sprint_load.py

# Manual smoke:
uv run clawteam --help              # open and go both visible under Daily use panel
uv run clawteam go --help           # tagline mentions "shortcut"
uv run clawteam open --help         # registered, help describes it
grep -c "workspace-style" README.md # README Primary Flow rewritten
```
</verification>

<success_criteria>
- `clawteam go --help` tagline advertises it as a shortcut for `open` + `sprint start`
- `cmd_go` function signature + body unchanged (zero-break migration)
- README Primary Flow leads with `clawteam open` + `clawteam sprint start`
- README has a `#### Shortcuts` subsection listing `go` as an advanced one-shot
- README_CN.md / README_KR.md untouched (out of scope)
- VALIDATION.md per-task-map shows all 4 REQs ✅ green
- Full suite GREEN
- Phase 13 complete — WS-01, WS-02, WS-03, WS-04 all covered
</success_criteria>

<output>
After completion, create `.planning/phases/13-workspace-entry-point/13-05-SUMMARY.md` documenting:
- The 1-line tagline change + 3-region README rewrite
- The live-UAT walkthrough commands (from VALIDATION.md Manual-Only Verifications) the user should run on CachyOS + fish before `/gsd-verify-work`
- Pointer: "Phase 13 complete. Next: `/gsd-verify-work 13` (automated) → live UAT walkthrough → `/gsd-finalize-phase 13` → Phase 14 planning (Session Continuity: RELI-05, RELI-06, WS-05)."
</output>
