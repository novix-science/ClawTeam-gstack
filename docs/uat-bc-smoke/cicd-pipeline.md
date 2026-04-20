# UAT BC Smoke — CI/CD Pipeline Design

Smoke-test deliverable from team `uat-bc-smoke`, agent `devops`. Demonstrates that the ClawTeam devops-engineer role can claim, execute, and close a task end-to-end. Pairs with `backend-api.md` and `frontend-ui.md` from the same team. No production code is introduced.

## Scope

Minimal pipeline sketch for the hypothetical "Team Status" service described in `backend-api.md` and `frontend-ui.md`. Sketch only — the purpose is protocol verification, not pipeline delivery. The existing `.github/workflows/ci.yml` (lint + pytest matrix) remains the authoritative CI for this repo; this document is forward-looking design for the imagined product.

## Stages

1. **Lint** — `ruff check` on backend, `eslint`/`tsc --noEmit` on frontend. Fails fast; no later stage runs on lint failure.
2. **Unit test** — pytest for backend, vitest for frontend. Matrix: Python 3.10–3.12 × {ubuntu-latest}. Coverage reported but not gated in smoke.
3. **Integration test** — spins up the backend against an ephemeral SQLite, drives it from a thin HTTP client. Verifies state-machine transitions from `backend-api.md`.
4. **Build** — backend wheel, frontend static bundle. Artifacts uploaded with commit SHA.
5. **Deploy (non-prod)** — on merge to `main`, push artifacts to a staging environment. Smoke check hits `GET /teams/{team}/tasks` and expects `200`.
6. **Promote (prod)** — manual approval gate. Same artifacts, no rebuild.

## Environments

- **ci** — ephemeral per-job, no persistence.
- **staging** — always-on, mirrors prod shape, seeded with fixture team.
- **prod** — gated by manual approval and a passing staging smoke.

Each environment has its own bearer-token issuer (see `backend-api.md` auth). Tokens never cross environments; CI reads staging/prod tokens from GitHub Actions environment secrets.

## Infrastructure as code

- Single Terraform root per environment. State in remote backend, per-env workspace.
- Application deploy via a thin container image (`python:3.12-slim` base). Image digest pinned in the deploy manifest.
- No manual cloud console changes — drift is detected by `terraform plan` running on a nightly cron and posting diffs to the team inbox.

## Secrets

- GitHub Actions environment secrets for deploy credentials and bearer-issuer keys.
- No secrets in repo, in images, or in logs. PR workflows get a read-only token; deploy workflows require `workflow_dispatch` or a protected branch.

## Observability

- Structured JSON logs (one line per request) shipped to the platform log sink.
- Three SLIs on the backend: request success rate, P95 latency for `GET /teams/{team}/tasks`, inbox-delivery lag. Alerts route to the team inbox as `monitoring:` messages.
- Pipeline runs themselves emit a `lifecycle` event per stage so the orchestrator dashboard can render a deploy timeline.

## Security posture

- Dependency scanning (`pip-audit`, `npm audit`) in the lint stage. High-severity findings block merge.
- Image scan on build (trivy or equivalent). Critical CVEs block promote.
- Branch protection on `main`: required checks = lint + unit + integration; linear history; no force push.

## Rollback

- Promote re-deploys the previous artifact by SHA — no "rollback" command needed, just re-run the last known-good promote.
- Database migrations (if introduced later) must be backward-compatible within a release window. Smoke scope has no persistence, so this is a future-phase concern.

## Out of scope for this smoke

Real pipeline YAML for the imagined service, real Terraform modules, real container registry, SLO definitions, on-call rotation, and chaos testing. These would be follow-up phases if the orchestrator grew a deployable service surface.
