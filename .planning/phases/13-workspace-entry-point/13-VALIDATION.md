---
phase: 13
slug: workspace-entry-point
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-24
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (existing; v1.1 suite ran 1741 pass / 9 pre-existing flakes) |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/cli/test_commands.py tests/spawn/test_tmux_backend.py tests/spawn/test_adapters.py tests/sprint/test_conductor.py -x` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~45 seconds quick, ~4 min full |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 45 seconds (quick), 240 seconds (full)

---

## Per-Task Verification Map

> Task IDs follow `13-{plan}-{task}` convention once planner assigns them. Populated after planner completes.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | WS-01 | — | Clean REPL, no auto-injected message | unit + integration | `pytest tests/cli/test_open.py::test_open_no_goal_enters_clean_repl` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WS-02 | — | `post_launch_prompt` skipped when goal is None | unit | `pytest tests/spawn/test_adapters.py::test_no_goal_skips_post_launch_prompt` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WS-03 | — | `go` help tagline reworded; `go` behavior unchanged | unit | `pytest tests/cli/test_commands.py::test_go_help_tagline_is_shortcut` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WS-04 | — | `sprint start --goal` injects kickoff via `_inject_prompt_via_buffer` | unit + integration | `pytest tests/sprint/test_conductor.py::test_sprint_start_injects_kickoff` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/cli/test_open.py` — new file, stubs for `clawteam open` command (WS-01)
- [ ] `tests/spawn/test_adapters.py` — extend with `test_no_goal_skips_post_launch_prompt` (WS-02)
- [ ] `tests/cli/test_commands.py` — extend with `test_go_help_tagline_is_shortcut` (WS-03)
- [ ] `tests/sprint/test_conductor.py` — extend with `test_sprint_start_injects_kickoff` + `test_sprint_start_rejects_active_sprint_collision` + `test_sprint_start_retry_kickoff_partial` (WS-04)
- [ ] `tests/integration/test_open_sprint_start_flow.py` — new file, integration coverage for `open` → `sprint start` flow with scripted claude mock

*Existing infrastructure from v1.1 covers most of the spawn/sprint test harness. Wave 0 is surgical additions, not new framework.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `clawteam open gstack -n foo` lands user in a tmux session with 11 clean claude REPLs, zero messages sent | WS-01, WS-02 | Requires interactive tmux + real claude CLI binary; automated tests use mocks | 1. `cd /tmp/clawteam-uat-13 && git init`<br>2. `/home/jac/repos/ClawTeam-gstack/.venv/bin/clawteam open gstack -n foo`<br>3. Inspect every pane — each shows `> ` prompt with no prior message<br>4. In any pane type "hello" and press enter — agent responds as its role (turn count = 1, not 2) |
| `clawteam sprint start foo --goal "build X"` delivers kickoff to 11 live panes | WS-04 | Requires live panes from step above; automated test only verifies injection fn called | Continuing from WS-01/02 manual: `clawteam sprint start foo --goal "build a CSV CLI"` → each pane receives kickoff prompt as its next user message (visible in scrollback) |
| `clawteam sprint start foo --goal "..."` on a team with already-active sprint rejects cleanly | WS-04 | Requires live sprint state; test only verifies error path | After first sprint start, run `clawteam sprint start foo --goal "different"` → expect exit code != 0 and message "sprint `<id>` already active" |
| README canonical example shows `open` → `sprint start`; `go` in "Shortcuts" subsection | WS-03 | Human verification of documentation structure | Open `README.md`; verify the Quick Start section leads with `clawteam open` + `clawteam sprint start` before showing `go` as a shortcut |

---

## Validation Architecture (Nyquist dimension 8)

The phase's four REQs divide cleanly across automated vs. manual:

- **Automated-covered** (pytest + mocks):
  - `post_launch_prompt` conditional gating (WS-02)
  - `sprint start` injection mechanism reuse, active-sprint rejection, retry-kickoff state (WS-04)
  - `go` help tagline string (WS-03)
  - `open` command typer wiring + argument parsing (WS-01)

- **Manual-covered** (live tmux + real claude CLI):
  - "Zero turn-1 tokens consumed" empirical check — can only be verified by opening a real pane and counting messages
  - "Kickoff arrives as next user message" — requires watching the pane scrollback
  - README documentation shape — human judgment

**Frequency:** Every task commit → quick automated suite. Every plan wave → full suite. Before `/gsd-verify-work` gate → manual walkthrough on the CachyOS + fish shell development machine (the v1.0 UAT lesson: real-env reveals integration bugs that mocked tests miss).

**Blocking dimension:** Phase cannot pass verification without either the automated suite green AND the manual walkthrough completing, OR the user explicitly accepting `human_needed` status for the manual items.
