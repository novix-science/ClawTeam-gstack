# Phase 1 Smoke — P05 Verify — Tech Spec

Team: `phase1-smoke-p05-verify`
Owner: tech-lead (bd9a749996fe)
Purpose: BC smoke verify — exercise the phase1 coordination workflow end-to-end.

## Scope
This is a backward-compatibility smoke run. The intent is to verify:

1. Tech-lead can create a task breakdown and mark its own task in/out of progress.
2. Worker roles (backend-dev, frontend-dev, qa-engineer, devops) each pick up
   their auto-seeded task and drive it through the lifecycle.
3. Inbox, task list, lifecycle idle, and cost reporting commands still work.
4. Final merge/cleanup path is exercised by the leader.

## Task Breakdown (auto-seeded)
- `backend-dev`  — Design and implement backend API endpoints
- `frontend-dev` — Implement frontend UI components
- `qa-engineer`  — Write unit and integration tests
- `devops`       — Set up CI/CD pipeline
- `tech-lead`    — Create technical specification and task breakdown (this doc)

## Exit Criteria
- All seeded tasks reach `completed`.
- Tech-lead emits a final summary to the leader via `clawteam inbox send`.
- Cost report submitted via `clawteam cost report`.
- No BC regressions observed in CLI output shapes.

## Notes
No production code changes are required for this smoke pass. Artifact lives
under `clawteam/smoke_artifacts/` to avoid polluting planning dirs.
