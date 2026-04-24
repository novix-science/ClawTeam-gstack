# Phase 9: Event-driven Coordination (close the feedback loop) - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Mode:** Smart discuss defaults accepted in text-mode fallback

<domain>
## Phase Boundary

This phase closes the feedback loop after phase work is done. It ensures task completion is emitted, watches current-phase tasks plus required artifacts, and wakes the leader with `[wake:phase]` when the phase is ready to advance.

</domain>

<decisions>
## Implementation Decisions

### Event Source
- Reuse the existing `TaskCompleted` event from `clawteam.events.types`.
- Treat `FileTaskStore.update(... status=completed ...)` as the authoritative emit path because `clawteam task update` already flows through it.

### Watcher
- Add a small `PhaseCompletionWatcher` under `clawteam/sprint/`.
- Use task metadata `phase` / `current_phase` to identify current-phase tasks.
- Check phase-required artifacts through `PHASE_REQUIREMENTS`.
- Wake the team leader role, defaulting to `ceo` when the team config has no `leader_role`.

### Wake UX
- Extend `wake_agent(kind="phase")` with concise `[wake:phase]` text.
- Use `force=True` for phase-complete wakes so a task/inbox wake debounce does not hide the transition signal.

### the agent's Discretion
- Exact registration point can be any reliable same-process path before task completion emit. The chosen path is `task update` registration before `TaskStore.update()`.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TaskCompleted` already exists and `FileTaskStore.update()` emits it.
- `wake_agent()` already supports task/inbox tmux injection and silent failure.
- `SprintState` stores `current_phase` and `artifacts`, and Phase 8 added `PHASE_REQUIREMENTS`.

### Established Patterns
- Event handlers must not crash the bus.
- Wake delivery is best-effort and should silently return false without tmux.
- Tests should monkeypatch wake delivery rather than invoke real tmux.

### Integration Points
- `clawteam task update` registers the watcher with the global bus before updating task state.
- `PhaseCompletionWatcher` reads sprint state files directly to avoid phase-registry side effects.

</code_context>

<specifics>
## Specific Ideas

- Wake text should include the phase name, number of tasks done, number of artifacts present, and the exact `clawteam sprint advance` command.

</specifics>

<deferred>
## Deferred Ideas

- Full end-to-end sprint regression remains Phase 11.

</deferred>
