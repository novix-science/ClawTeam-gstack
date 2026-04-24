---
phase: 2
slug: sprint-engine-evidence-gates-theater-drift-deadlock-prevention
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-17
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing — `tests/conftest.py` already present) |
| **Config file** | `pyproject.toml` (pytest section) + `tests/conftest.py` |
| **Quick run command** | `pytest tests/ -x --ff -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~90 seconds (full) / ~15 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/<task-scope>/ -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green (including regression matrix)
- **Max feedback latency:** 90 seconds

---

## Per-Task Verification Map

*(Populated by planner from RESEARCH.md §Validation Architecture — 48 REQ-ID → test mappings across 10 new test files.)*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-XX-YY | XX | W | REQ-{code} | T-02-{id} / — | {expected secure behavior} | unit/integration/regression | `{command}` | ✅ / ❌ W0 | ⬜ pending |

Per RESEARCH.md §Validation Architecture, expected coverage:

- **Unit tests** (fast, isolated): `EvidenceGate`, `TurnEnvelope`, `FreezeRegistry`, theater detector, cycle detector, artifact-cap enforcement.
- **Integration tests** (stateful, file-system): sprint pause/resume across orchestrator restart, test-command re-execution cache, freeze audit JSONL round-trip, CLI `--json` envelope shape.
- **Regression matrix** (cross-template): `tests/test_template_regression_matrix.py` green across all 6 packaged templates (software-dev, hedge-fund, code-review, harness-default, research-paper, strategy-room).

---

## Wave 0 Requirements

- [ ] `tests/test_evidence_gate.py` — EvidenceGate 4-check protocol (frontmatter / stub / blacklist / test-rerun)
- [ ] `tests/test_turn_envelope.py` — pydantic `TurnEnvelope` validation on `TeamMessage` + artifact frontmatter
- [ ] `tests/test_freeze_registry.py` — `/freeze`, `/unfreeze`, `/guard`, `/careful` behavior + audit JSONL
- [ ] `tests/test_theater_detector.py` — `forced_progress_gate` 2-turn-per-agent trigger + recovery
- [ ] `tests/test_cycle_detector.py` — `DefaultRoutingPolicy` round-trip detection + suppression + escalation
- [ ] `tests/test_artifact_caps.py` — per-file 50 KB + per-phase 500 KB enforcement paths
- [ ] `tests/test_sprint_conductor.py` — pause/resume cycle with `HarnessOrchestrator` restart
- [ ] `tests/test_sprint_cli.py` — `clawteam sprint start/status/show/list/pause/resume` + `--json`
- [ ] `tests/test_before_events.py` — `BeforeToolCall` + `BeforeFileWrite` veto semantics + MCP error translation
- [ ] `tests/conftest.py` — extend with fixtures for sprint-scoped `~/.clawteam/teams/<team>/sprints/<id>/` tmp dir

*Regression matrix (`tests/test_template_regression_matrix.py`) already exists from Phase 0; no new file, but must remain green.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `deploy_url` HEAD probe against a real 2xx URL | SPRINT-02 (D-05) | Requires reachable external URL; Phase 5's `/ship` wires the real allowlist | Start sprint, write `ship-notes.md` with `deploy_url: https://example.com/`, confirm `EvidenceGate.check()` passes; confirm `deploy_url: https://nonexistent.invalid/` fails with the recorded response/timeout reason |
| CLI end-to-end ergonomics (`sprint start` → `status` → `pause` → `resume`) on real shell | UX-02..05, UX-09 | UX quality (JSON envelope clarity, prefix disambiguation messaging) not easy to spec as an assertion | Run the full CLI cycle against a freshly created team fixture; confirm human-readable output matches `docs/rfcs/001-phase-registry.md` §CLI examples |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 90s
- [ ] Phase 0 regression matrix still green
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
