# UAT BC Smoke — Tech Spec

Team: `uat-bc-smoke`
Owner: tech-lead (6261c4d3cf49)
Purpose: UAT backward-compatibility smoke — exercise the multi-agent coordination
workflow end-to-end and verify no CLI regressions.

## Scope

This run verifies that the following BC-critical surfaces still behave:

1. `clawteam task list --owner` filtering and `clawteam board show` rendering.
2. Worker lifecycle: `task update --status in_progress` → commit → `--status completed`.
3. Inbox send/receive between leader and workers.
4. `clawteam lifecycle idle` and `clawteam cost report` commands.
5. Worktree merge path when all workstreams complete.

## Task Breakdown (auto-seeded)

| Task | Owner | Depends on |
|---|---|---|
| Create technical specification and task breakdown | `tech-lead` | — |
| Design and implement backend API endpoints | `backend-dev` | tech-spec |
| Implement frontend UI components | `frontend-dev` | tech-spec |
| Write unit and integration tests | `qa-engineer` | backend + frontend |
| Set up CI/CD pipeline | `devops` | — |

Workers are expected to treat this as a smoke drill — minimal artifacts, no
production code changes required. Each worker commits a single marker file under
`clawteam/smoke_artifacts/uat-bc-smoke-<role>.md` documenting their run.

## Exit Criteria

- All 5 seeded tasks reach `completed`.
- Tech-lead sends a final summary to the leader via `clawteam inbox send`.
- Cost report submitted via `clawteam cost report`.
- CLI command output shapes unchanged from prior release (visual diff sanity).

## Notes

Artifact lives under `clawteam/smoke_artifacts/` to avoid polluting `.planning/`
and keep the smoke run isolated from active Phase 3 work on
`gstack-integration`.
