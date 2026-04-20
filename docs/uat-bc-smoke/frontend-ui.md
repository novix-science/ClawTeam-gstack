# UAT BC Smoke — Frontend UI Design

Smoke-test deliverable from team `uat-bc-smoke`, agent `frontend-dev`. Demonstrates that the ClawTeam frontend-developer role can claim, execute, and close a task end-to-end. Pairs with `backend-api.md` from the same team. No production code is introduced.

## Scope

Minimal UI sketch for a hypothetical "Team Status" console that would consume the backend API described in `backend-api.md`. Sketch only — the purpose is protocol verification, not product delivery.

## Views

- **Team board** — kanban columns keyed on task `status` (`pending`, `in_progress`, `completed`, `blocked`). Cards show `subject`, `owner`, `priority`, and a lock badge when `lock` is set.
- **Task detail drawer** — opens on card click. Shows full task fields plus inbox thread between the task's owner and the tech-lead.
- **Agent roster** — sidebar listing agents in the team with current status (`active`, `idle`, `offline`) derived from `lifecycle` events.
- **Compose message** — modal form posting to `POST /teams/{team}/inbox`. Fields: `to` (agent select), `body` (textarea).

## Component shape

- `TeamBoard` — fetches `GET /teams/{team}/tasks`, groups by status, subscribes to updates (polling at first, SSE later).
- `TaskCard` — presentational; emits `onOpen(taskId)`.
- `TaskDrawer` — fetches `GET /teams/{team}/tasks/{id}`, hosts status-transition buttons that call `PATCH`.
- `InboxThread` — lazy-loaded inside the drawer.
- `AgentRoster` — sidebar, independent data source.

## State & data

- Server state via a query cache (TanStack Query or equivalent). Mutations invalidate the board query on success.
- Optimistic updates on status transitions; rollback on 4xx.
- Bearer token read from session storage, injected by a single fetch wrapper. Never stored in localStorage.

## UX rules

- Status transitions that violate the backend state machine are disabled in the UI, not just rejected on submit.
- Blocked tasks render a chip linking to the blocker; clicking it opens that task's drawer.
- Cross-team reads are hidden entirely — the team id is pinned at route level.

## Accessibility

- All interactive elements keyboard-reachable. Kanban drag-and-drop has a keyboard equivalent (status dropdown on each card).
- Drawer traps focus while open and restores focus on close.

## Out of scope for this smoke

Real components, routing, styling system, test suite, and build wiring. These would be follow-up phases if the orchestrator grew a UI surface.
