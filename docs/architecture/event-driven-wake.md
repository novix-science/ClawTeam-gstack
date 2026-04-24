# Event-Driven Wake Architecture

ClawTeam agents should react to pushed runtime notifications, not burn turns
polling `task list` or `inbox receive`. The wake path injects a short user
message into the agent pane when new work arrives, then the agent pulls the
full record with the normal CLI command.

## Wake Kinds

`clawteam/wake.py::wake_agent(team, agent, kind, preview, force=False)` is the
shared injection entrypoint.

| Kind | Trigger | Injected action |
|------|---------|-----------------|
| `task` | `clawteam task create <team> ... --owner <agent>` | Pull assigned work with `clawteam task list <team> --owner <agent>` |
| `inbox` | inbox send/broadcast paths | Pull messages with `clawteam inbox receive <team> --agent <agent>` |
| `phase` | `PhaseCompletionWatcher` sees current-phase tasks and required artifacts complete | Leader runs `clawteam sprint advance <sprint> --team <team>` |
| `custom` | direct caller-provided wake | Caller-specific preview text |

Wake delivery is best-effort. If there is no tmux session, no pane map, or the
target pane cannot be resolved, `wake_agent()` returns `False` and the caller
continues.

## Pane Lookup

Wake injection depends on the tmux pane map written by the tmux backend:

```text
<data>/teams/<team>/tmux_pane_map.json
```

The map stores `pane_index -> agent_name`. `wake_agent()` loads it through
`clawteam.spawn.tmux_backend.read_pane_map()`, resolves the pane index to a
live tmux pane id with `tmux list-panes`, then injects text with:

```bash
tmux send-keys -t <pane-id> -l "<wake text>"
tmux send-keys -t <pane-id> Enter
```

The debounce file lives at:

```text
<data>/teams/<team>/_wake/<agent>.ts
```

Repeated non-forced wakes to the same agent within three seconds are skipped.
Phase completion wakes pass `force=True` because they are sparse and
state-machine relevant.

## Phase Completion

`clawteam/sprint/phase_completion_watcher.py` subscribes to `TaskCompleted`.
On each completion it:

1. scans running sprint state files for the team;
2. filters tasks whose metadata phase matches the sprint's current phase;
3. checks all those tasks are completed;
4. checks current-phase required artifacts from `PHASE_REQUIREMENTS`;
5. wakes the team leader with `kind="phase"`.

`clawteam task update <id> --status completed` registers this watcher before
emitting the completion event, so the CLI path gets the feedback loop without
extra setup.

## Nudge

Nudge is separate from wake. Wake is event-driven work arrival; nudge is an
idle reminder.

The tmux backend configures an `alert-silence` hook that runs:

```bash
clawteam nudge #{pane_id}
```

`clawteam/nudge.py` maps pane id back to team and agent, reads the latest sprint
state, and injects a short role-card reminder. Its debounce is 60 seconds and
uses:

```text
<data>/teams/<team>/_nudge/<pane-id>.ts
```

## Adding a New Wake Kind

1. Add formatting for the new `kind` in `wake_agent()`.
2. Call `wake_agent(team, agent, kind="<new-kind>", preview="<short context>")`
   from the event producer.
3. Keep the injected text short and include the exact CLI command the agent
   should run to pull full state.
4. Add a test with a fake pane map and fake `tmux` command, or monkeypatch
   `wake.subprocess.run` as existing wake tests do.
