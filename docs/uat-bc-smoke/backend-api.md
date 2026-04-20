# UAT BC Smoke — Backend API Design

Smoke-test deliverable from team `uat-bc-smoke`, agent `backend-dev`. Demonstrates that the ClawTeam backend-developer role can claim, execute, and close a task end-to-end. No production code is introduced.

## Scope

Minimal design sketch for a hypothetical "Team Status" API that the orchestrator could expose to agents in future iterations. Kept deliberately small — the purpose is protocol verification, not product delivery.

## Endpoints

- `GET /teams/{team}/tasks` — list tasks for a team. Query params: `status`, `owner`.
- `GET /teams/{team}/tasks/{id}` — fetch task detail.
- `PATCH /teams/{team}/tasks/{id}` — update `status` (`pending` | `in_progress` | `completed` | `blocked`).
- `POST /teams/{team}/inbox` — send a message to an agent. Body: `{to, from, body}`.

## Data model

Task: `id`, `subject`, `status`, `priority`, `owner`, `blocked_by[]`, `lock`, `created_at`, `updated_at`.

## Auth

Team-scoped bearer token. Agents receive their token from the orchestrator at dispatch time. No cross-team reads.

## Validation

- `status` transitions restricted to the state machine above (no `completed → pending`).
- `owner` must be a known agent id for the team.
- `blocked_by` entries must reference existing task ids in the same team.

## Out of scope for this smoke

Persistence backend, rate limiting, pagination, webhooks, and real implementation. These would be follow-up phases if the orchestrator grew a network surface.
