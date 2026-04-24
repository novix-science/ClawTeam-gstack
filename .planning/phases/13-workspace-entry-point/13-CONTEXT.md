# Phase 13: Workspace Entry Point - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Reshape the user-facing team launch surface so that opening a team no longer requires committing to a goal. Split today's monolithic `clawteam go <goal>` into three composable steps: `clawteam open` (create-or-resume team, no goal), `clawteam sprint start --goal "..."` (kickoff prompts get injected here, not at launch), and `clawteam go` (shortcut preserving one-shot semantics).

In scope for Phase 13: WS-01 (`open` command), WS-02 (launch = clean REPL when no goal), WS-03 (`go` demoted to shortcut), WS-04 (`sprint start` injects kickoff).

Out of scope (later phases): session persistence across re-open (Phase 14), idle-mode wake suppression (Phase 15), progressive pane layout (Phase 15).

</domain>

<decisions>
## Implementation Decisions

### Command surface (`clawteam open`)

- Full flag symmetry with `go`: accepts `--attach / --window / --tile / --name / --template` with identical defaults (attach + window + tile)
- Positional argument is the **template** name (`clawteam open [TEMPLATE]`); team name supplied via `-n/--name` — mirrors `launch` exactly, not `tmux attach`
- No args + no existing team → fail loud with "specify a template (new team) or a team name with `-n`"
- Template and existing team name collide (`open gstack -n gstack`) → team-name wins, resume existing; template is creation-only hint

### Clean-REPL launch behavior

- Skip `post_launch_prompt` injection by gating on `goal is not None` in `clawteam/spawn/adapters.py:132-133` — no goal = no injection at all (not empty-string injection)
- Role system prompts (ceo.md / pm.md / ...) are **still injected** via `--append-system-prompt` even when goal is absent — personas are part of "being in the team"; goal ≠ persona
- Pane identification uses tmux pane titles (`tmux select-pane -T "<role>"` at spawn time); `clawteam status` already shows the mapping — no "I'm <role>" probe message (that would burn turn 1 and defeat the purpose of clean REPL)
- At-rest pane shows claude CLI's default empty prompt (`> ` ready for input), nothing pre-printed

### `sprint start` owns kickoff injection

- Injection mechanism: reuse the existing `_inject_prompt_via_buffer` from `clawteam/spawn/tmux_backend.py:255-261`, called from `sprint start` instead of launch — same tmux send-keys path, different caller
- `sprint start <team>` when a sprint is already active → reject loudly: `"sprint <id> already active; use \`sprint advance\` or \`sprint pause\` + \`sprint start\`"`
- Kickoff content is the full CEO synthesis (from `clawteam/cli/commands.py:4593-4619`); other agents get the same role-scoped variants as today's `go` flow — preserves parity
- Partial-injection failure idempotency: record `kickoff_injected_agents: [...]` list in sprint state per pane that received kickoff; `sprint status` surfaces partial state; add `sprint start --retry-kickoff` for catch-up (not transactional — too complex to implement cleanly)

### `go` demotion

- Stays in `clawteam --help` "Daily use (solo)" panel but the one-liner is reworded to `"one-shot: open + sprint start"` — still visible, no longer primary
- Semantics unchanged: `go <goal>` = create team + start sprint + launch panes. For existing team + new sprint, users compose `open` + `sprint start` (no extending `go` to take `--team <existing>`)
- README primary-flow rewrite: canonical example becomes `clawteam open` → `clawteam sprint start` sequence; `go` moves to a "Shortcuts" subsection
- Zero-break migration for scripts/CI: `go`'s runtime behavior is identical; only docs change. No deprecation warning, no `--legacy` flag

### Claude's Discretion

- Exact CLI plumbing for the new `open` command (typer signatures, shared helper extraction with `go` and `launch`) — Claude picks idiomatic patterns for the codebase
- Sprint-state file schema delta for `kickoff_injected_agents` — Claude picks a field naming + storage shape consistent with existing sprint state
- README section ordering and wording beyond the canonical-example rewrite — Claude picks a tone consistent with v1.1's README style

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets

- `clawteam/cli/commands.py` — `go` command already assembled from `team spawn` + `sprint start` + `launch` primitives; the new `open` command is mostly `go` with the sprint-start step dropped and goal made optional
- `clawteam/spawn/adapters.py:132-133` — the exact branch where `post_launch_prompt` is set for interactive claude commands; gating here is the surgical edit
- `clawteam/spawn/tmux_backend.py:255-261` — `_inject_prompt_via_buffer` is already factored out of spawn; `sprint start` can call it directly on pre-existing panes
- `clawteam/cli/commands.py:4593-4619` — CEO kickoff synthesis is already a named helper; reusable from the `sprint start` path without duplication
- `clawteam/spawn/tmux_backend.py:370-375` — `tmux_pane_map.json` already records `agent → pane` mapping; `sprint start` reads this to know where to inject
- `clawteam/solo.py:194-200` — current "Team already exists" rejection is where `open` branches to resume-mode; `launch`'s reuse path (commit `c254315`) is the pattern

### Established Patterns

- **typer command grouping** — top-level commands live in `clawteam/cli/commands.py` with Rich help panels declared via `rich_help_panel="..."` on each decorator
- **Shared helper extraction** — `go` was built by composing `team spawn` + `sprint start` + `launch`; the same composition pattern applies in reverse when splitting into `open` + `sprint start`
- **Sprint state persistence** — `~/.clawteam/teams/<team>/sprints/<sprint-id>/STATE.md` + sibling structured JSON; new `kickoff_injected_agents` field follows the same file-locked atomic-write convention
- **Config-driven defaults** — attach / window / tile behavior is already a typer flag trio on `go`; re-declaring on `open` means shared-helper extraction, not re-implementation

### Integration Points

- `clawteam/cli/commands.py` — `open` command registration (new); `go` docstring + Rich help panel tagline (edit); README primary flow rewrite (edit `README.md`)
- `clawteam/solo.py` — team-already-exists branching: route `open` to resume, keep `go` as create-new
- `clawteam/spawn/adapters.py` — `post_launch_prompt` gating on goal presence
- `clawteam/sprint/conductor.py` (likely) — new `start --retry-kickoff` flag; injection fan-out logic; conflict rejection when active sprint exists
- Test harness — `tests/integration/test_gstack_sprint_end_to_end.py` from v1.1 exercises `go`; Phase 13 adds a test exercising `open` → `sprint start` split flow

</code_context>

<specifics>
## Specific Ideas

- Full backlog sketch with code:line refs in `.planning/backlog/v1.2-workspace-semantics.md`
- Product-model framing: "go = submit build.sh" (batch) vs "open = enter IDE" (workspace) — the user explicitly surfaced this on 2026-04-24
- The 4 v1.1 post-ship UX complaints this phase addresses: windows-then-tile flash (Phase 15), turn-1 burn on kickoff (WS-02), persistence gaps (Phase 14), goal-required-at-launch (WS-01) — all rooted in the same product-model mismatch

</specifics>

<deferred>
## Deferred Ideas

- **Retroactive `sessions.json` migration** for existing v1.1 teams — user explicitly chose forward-only migration on 2026-04-24. In Out of Scope of REQUIREMENTS.md.
- **Multi-team quick-switch** (`open` showing multiple teams in one tmux session) — Future Requirements in REQUIREMENTS.md; v1.2 stays single-active-team
- **Named workspace snapshots** — Future Requirements; v1.2 only supports most-recent-state resume
- **Session pruning / retention policy** for `~/.claude/projects/` — Future Requirements; claude CLI session files accumulate but lifecycle management is not this milestone's concern

</deferred>
