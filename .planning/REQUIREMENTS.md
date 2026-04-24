# Requirements — ClawTeam-gstack v1.2 Workspace Semantics

**Milestone goal:** Shift the team from a one-shot task runner to a persistent workspace — users open the team first, commit to a goal later, and conversations survive across terminal re-opens.

**Origin:** Scoped from live code inspection of v1.1-shipped `clawteam/spawn/tmux_backend.py`, `solo.py`, and `keepalive.py` during the post-v1.1 UX review on 2026-04-24. Full sketch: `.planning/backlog/v1.2-workspace-semantics.md`.

**Milestone constraint recap:**
- Phase numbering continues from v1.1 (starts at phase 13)
- No new required runtime dependencies
- Backwards compatibility with v1.1 teams preserved via forward-only migration (see Out of Scope)
- Each phase must include a Nyquist VALIDATION.md (v1.1 audit lesson)

---

## v1.2 Requirements (9 REQs)

### Workspace Entry (WS) — command-model shift

The user's entry point becomes "open the workspace, think later," not "submit a build task."

- [ ] **WS-01**: User can run `clawteam open [template]` without a goal argument and land inside a live 11-agent team (no sprint started, no kickoff prompt consumed)
- [ ] **WS-02**: When a team is opened without a goal, every agent pane presents as a clean `claude` REPL — no initial message is injected, no turn-1 tokens are consumed
- [ ] **WS-03**: `clawteam go <goal>` remains as a shortcut that runs `open` + `sprint start` in one command; documented as advanced/one-shot, not the primary flow
- [ ] **WS-04**: User can start a sprint on an already-open team with `clawteam sprint start <team> --goal "..."`, and kickoff prompts are delivered to agents only at that moment (not at launch)
- [ ] **WS-05**: When `sprint start` runs on a team where the user has already chatted with the CEO agent in idle mode, the CEO continues in its existing `claude` session — the kickoff message arrives as a continuation of that dialogue, not a session reset

### Session Continuity (RELI) — conversations survive re-open

Agent dialogues persist across terminal close / laptop reboot.

- [ ] **RELI-05**: Every agent spawn records its `claude` session id to `~/.clawteam/teams/<team>/sessions.json`, written via the existing `clawteam session save` module (no new storage layer)
- [ ] **RELI-06**: User can run `clawteam open <existing-team>` and every agent's prior conversation is restored via `claude --resume <session-id>`; the tmux pane layout is rebuilt from the saved `tmux_pane_map.json`
- [ ] **RELI-07**: When no sprint is active on a team, agents do not poll, auto-wake, or receive idle-heartbeat events; they respond only when the user sends a message in their pane

### Launch UX (UX) — visual polish

Team launch feels progressive, not flashy.

- [ ] **UX-04**: Team launch shows progressive pane appearance — the first agent uses `tmux new-window`; agents 2 through 11 use `tmux split-window` inside the same window with `select-layout tiled` after each split. No final "windows → merged panes" flash.

---

## Future Requirements (deferred)

Items that surfaced during v1.2 scoping but are intentionally out of this milestone:

- **Retroactive session-map migration** — auto-populate `sessions.json` for existing v1.1 teams by scanning `~/.claude/projects/`. Deferred per user decision (2026-04-24): forward-only migration is simpler and avoids heuristic mismatches. Revisit if users report friction.
- **Multi-team workspace layout** — `clawteam open` handling multiple named teams in one tmux session with quick-switch keybindings. v1.2 stays single-active-team.
- **Named workspace snapshots** — `clawteam snapshot save/restore <name>` for point-in-time team state capture. v1.2 only supports the most-recent-state resume.
- **Session pruning / retention policy** — claude CLI session files accumulate in `~/.claude/projects/`; clawteam doesn't yet manage their lifecycle.

---

## Out of Scope

Explicit exclusions for v1.2 with reasoning:

- **Multi-user / remote team sharing** — v1.2 stays local + single-user. Reason: product-model shift (workspace semantics) is already a meaningful surface change; multi-user adds auth, sync, and permissions complexity orthogonal to the workspace concept.
- **Replacing `~/.claude/projects/` with clawteam-owned session storage** — claude CLI remains the session-of-record; clawteam only tracks session-id pointers. Reason: duplicating claude CLI's storage adds consistency burden; the pointer model is enough for resume.
- **Mid-session agent model swap** — agents stay on whatever model `claude` CLI is configured with. Reason: model override mid-conversation is a claude CLI concern, not a workspace concern.
- **Observability / cost tracking resurrection** — the Phase 7 cost stack deletion stands. Reason: v1.0 decision; unchanged by workspace semantics.
- **Retroactive session-map scan for v1.1 teams** (see Future Requirements above) — v1.1 teams on first v1.2 `open` start fresh (no session resume). Reason: user explicitly chose forward-only migration on 2026-04-24. Simpler code, cheaper to test, no heuristic directory-name matching of `~/.claude/projects/`.

---

## Traceability (filled by roadmapper)

<!-- Roadmapper will populate REQ-ID → phase mapping below. -->

| REQ-ID | Phase | Plan |
|--------|-------|------|
| WS-01 | TBD | TBD |
| WS-02 | TBD | TBD |
| WS-03 | TBD | TBD |
| WS-04 | TBD | TBD |
| WS-05 | TBD | TBD |
| RELI-05 | TBD | TBD |
| RELI-06 | TBD | TBD |
| RELI-07 | TBD | TBD |
| UX-04 | TBD | TBD |

---

## Open questions (for planning phase, not this doc)

These are HOW-level decisions deferred to `/gsd-discuss-phase` or `/gsd-plan-phase`, not scope questions:

1. Should `clawteam open` inherit `--attach` / `--window` / `--tile` flags from `go`? (UX default)
2. What's the "idle-mode" signal to agents — a system prompt ("no active task, wait for user instruction"), or no prompt at all (pure REPL)? (RELI-07 impl detail)
