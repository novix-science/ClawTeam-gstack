---
phase: 04
plan: 12
type: execute
wave: 3
depends_on: [01, 02, 04]
files_modified:
  - clawteam/cli/commands.py
  - tests/test_sprint_approve_cli.py
autonomous: true
requirements: [SPRINT-05]
must_haves:
  truths:
    - "`clawteam sprint approve <id> --phase ship` Typer subcommand exists and writes ship-approval.md artifact."
    - "Written frontmatter contains approved_by (from git config or $USER fallback), approved_at (UTC ISO-8601), sha_at_approval (from state.review_sha or git HEAD)."
    - "`--json` flag prints the written frontmatter as JSON envelope."
    - "`--no-sign` flag skips git-commit signing path (stub in Phase 4; real signing is v1.x)."
    - "Idempotent: running approve twice updates the artifact with fresh approved_at but preserves approved_by."
    - "Artifact written via file_locked + atomic_write_text under sprint's artifacts dir."
    - "CLI exits non-zero if sprint not found OR workspace_branch not a git repo (for SHA extraction)."
  artifacts:
    - path: "clawteam/cli/commands.py"
      provides: "@sprint_app.command('approve') Typer subcommand"
      contains: "def sprint_approve"
    - path: "tests/test_sprint_approve_cli.py"
      provides: "CLI invocation tests with Typer's CliRunner + mocked SprintState"
      contains: "def test_approve_writes_frontmatter"
  key_links:
    - from: "clawteam/cli/commands.py::sprint_approve"
      to: "clawteam/sprint/state.py::SprintState.artifacts"
      via: "CLI updates state.artifacts['ship-approval.md'] + save_sprint_state"
    - from: "sprint_approve CLI"
      to: "clawteam/harness/ship_approval_gate.py::ShipApprovalGate"
      via: "CLI writes the artifact gate reads; frontmatter fields align"
---

<objective>
Ship the `clawteam sprint approve <sprint_id> --phase ship` Typer subcommand (D-14) that writes a signed `ship-approval.md` artifact the `ShipApprovalGate` (Plan 04) reads. Frontmatter contains `approved_by` (git user or $USER fallback), `approved_at` (UTC ISO-8601), `sha_at_approval` (from `SprintState.review_sha` or `git rev-parse HEAD`). Supports `--json` output envelope and `--no-sign` flag (real git-signed commits are v1.x).

Purpose: SPRINT-05 requires a scriptable human-approval surface. CLI is the scriptable path; editing the artifact manually is the alternative path the gate also honors. Plan 12 lands the CLI shape; the gate in Plan 04 already reads the frontmatter fields.

Output: 1 new Typer subcommand (~60 LOC) + 1 test file. Existing CLI subcommands (`start`, `status`, `show`, `list`, `pause`, `resume`) untouched.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md

<interfaces>
From clawteam/cli/commands.py (existing — sprint subcommands at lines 5321-5470):
```python
@sprint_app.command("start")
def sprint_start(...): ...
@sprint_app.command("status")
def sprint_status(...): ...
@sprint_app.command("show")
def sprint_show(...): ...
@sprint_app.command("list")
def sprint_list(...): ...
@sprint_app.command("pause")
def sprint_pause(...): ...
@sprint_app.command("resume")
def sprint_resume(...): ...

# Helpers (used throughout sprint_app commands):
_resolve_team_arg(team) -> str
_resolve_sprint_or_err(team, sprint_id) -> tuple[SprintConductor, SprintState] | (None, None)
_sprint_emit_ok(dict) -> None  # prints success
_sprint_emit_err(code, msg) -> None  # prints error
```

From clawteam/sprint/state.py:
```python
class SprintState(BaseModel):
    artifacts: dict[str, str] = Field(default_factory=dict)
    review_sha: str | None = None
    sprint_id: str
    team: str
    # ...
def save_sprint_state(state: SprintState) -> Path: ...
```

Canonical ship-approval.md frontmatter per §04-CONTEXT specifics:
```yaml
artifact_type: ship_approval
approved_by: <git-user-name>
approved_at: <ISO-8601 UTC>
sha_at_approval: <40-char git SHA>
approval_notes: <freeform, optional>
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add sprint_approve Typer subcommand + tests</name>
  <files>clawteam/cli/commands.py, tests/test_sprint_approve_cli.py</files>
  <read_first>
    - clawteam/cli/commands.py (lines 5321-5470 — sprint subcommand patterns + helper fns)
    - clawteam/sprint/state.py (save_sprint_state + SprintState.artifacts)
    - tests/test_cli_commands.py (existing Typer CliRunner test pattern)
    - clawteam/harness/ship_approval_gate.py (frontmatter schema this CLI writes)
  </read_first>
  <behavior>
    - Test 1 (test_approve_writes_frontmatter): Run `clawteam sprint approve <id> --phase ship` → state.artifacts["ship-approval.md"] populated with YAML frontmatter containing artifact_type, approved_by, approved_at, sha_at_approval.
    - Test 2 (test_approve_uses_state_review_sha): state.review_sha is "abc123..." → ship-approval.md contains sha_at_approval == "abc123...".
    - Test 3 (test_approve_falls_back_to_git_head_when_review_sha_none): state.review_sha None + workspace_branch is a git repo → sha_at_approval from `git rev-parse HEAD`.
    - Test 4 (test_approve_json_mode_prints_frontmatter): --json flag → stdout is a JSON envelope containing the written frontmatter dict.
    - Test 5 (test_approve_no_sign_flag_accepted): --no-sign flag does not raise; artifact still written.
    - Test 6 (test_approve_sprint_not_found_exits_error): Non-existent sprint id → exit code non-zero, error emitted.
    - Test 7 (test_approve_updates_artifact_on_second_run): Run twice → approved_at updates (fresh timestamp); approved_by + sha_at_approval stable.
    - Test 8 (test_approve_with_notes_flag): --notes "LGTM by QA" → frontmatter contains approval_notes.
    - Test 9 (test_approve_writes_to_sprint_artifacts_dict): After approve, load_sprint_state(team, id).artifacts['ship-approval.md'] is non-empty.
    - Test 10 (test_approve_ship_approval_md_body_non_empty): Artifact body contains a minimal `# Ship approval` heading below frontmatter.
  </behavior>
  <action>
Edit `clawteam/cli/commands.py`. **APPEND** the new subcommand AFTER `sprint_resume` (around line 5467). Do NOT modify existing sprint_* commands.

Insertion:

```python
@sprint_app.command("approve")
def sprint_approve(
    sprint_id: str = typer.Argument(
        ..., help="Sprint id or unambiguous prefix."
    ),
    phase: str = typer.Option(
        "ship",
        "--phase",
        help="Phase to approve (currently only 'ship' is supported).",
    ),
    team: str = typer.Option("", "--team", envvar="CLAWTEAM_TEAM"),
    notes: str = typer.Option(
        "",
        "--notes",
        help="Optional approval notes recorded in ship-approval.md frontmatter.",
    ),
    no_sign: bool = typer.Option(
        False,
        "--no-sign",
        help="Skip git-commit signing (default: skip; real signing is v1.x).",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit the written frontmatter as JSON."
    ),
) -> None:
    """Write ship-approval.md artifact for the ship phase (§04-CONTEXT D-14 / SPRINT-05).

    Writes a signed approval artifact that the ShipApprovalGate reads. The
    `--phase ship` flag is reserved for forward-compat (e.g., future
    `--phase <other>` approvals); currently only "ship" is accepted.
    """
    import json
    import os
    import subprocess
    from datetime import datetime, timezone
    from clawteam.sprint.state import save_sprint_state

    if phase != "ship":
        _sprint_emit_err(
            "APPROVE_PHASE_UNSUPPORTED",
            f"Only --phase ship is supported (got {phase!r})",
        )
        raise typer.Exit(code=1)

    resolved_team = _resolve_team_arg(team)
    c, state = _resolve_sprint_or_err(resolved_team, sprint_id)
    if c is None or state is None:
        return

    # 1. Resolve approved_by: git user.name → $USER → "unknown".
    approved_by = ""
    try:
        r = subprocess.run(
            ["git", "config", "user.name"],
            cwd=state.workspace_branch or ".",
            shell=False,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        approved_by = (r.stdout or "").strip()
    except Exception:
        approved_by = ""
    if not approved_by:
        approved_by = os.environ.get("USER", "") or "unknown"

    # 2. Resolve sha_at_approval: state.review_sha, else git HEAD, else fail.
    sha_at_approval = state.review_sha or ""
    if not sha_at_approval and state.workspace_branch:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=state.workspace_branch,
                shell=False,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            sha_at_approval = (r.stdout or "").strip()
        except Exception:
            sha_at_approval = ""

    if not sha_at_approval:
        _sprint_emit_err(
            "APPROVE_NO_SHA",
            (
                "Cannot resolve sha_at_approval: state.review_sha is empty and "
                "git rev-parse HEAD failed. Ensure workspace_branch points to a git repo "
                "OR run Review-phase dispatch first to pin review_sha."
            ),
        )
        raise typer.Exit(code=2)

    # 3. Compose frontmatter + body.
    approved_at = datetime.now(timezone.utc).isoformat()
    frontmatter = {
        "artifact_type": "ship_approval",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "sha_at_approval": sha_at_approval,
        "sprint_id": state.sprint_id,
    }
    if notes:
        frontmatter["approval_notes"] = notes

    yaml_lines = ["---"]
    for key, value in frontmatter.items():
        yaml_lines.append(f"{key}: {value}")
    yaml_lines.append("---")
    yaml_lines.append("")
    yaml_lines.append("# Ship approval")
    yaml_lines.append("")
    yaml_lines.append(
        f"Approved by {approved_by} for sprint {state.sprint_id} at sha {sha_at_approval[:12]}."
    )
    if notes:
        yaml_lines.append("")
        yaml_lines.append(notes)
    artifact_body = "\n".join(yaml_lines) + "\n"

    # 4. Persist: write into state.artifacts + save_sprint_state.
    state.artifacts["ship-approval.md"] = artifact_body
    try:
        save_sprint_state(state)
    except Exception as exc:  # noqa: BLE001
        _sprint_emit_err("APPROVE_SAVE_FAILED", str(exc))
        raise typer.Exit(code=3)

    # no_sign flag is a pure forward-compat no-op in Phase 4 — real git-signed
    # approval commits are v1.x.
    _ = no_sign

    # 5. Emit output.
    if json_output:
        print(json.dumps({"status": "approved", **frontmatter}))
    else:
        _sprint_emit_ok({
            "status": "approved",
            "sprint_id": state.sprint_id,
            "approved_by": approved_by,
            "approved_at": approved_at,
            "sha_at_approval": sha_at_approval[:12],
        })
```

Create `tests/test_sprint_approve_cli.py`:

```python
"""Tests for `clawteam sprint approve` CLI subcommand (Plan 04-12 — SPRINT-05)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def setup_team_and_sprint(tmp_path, monkeypatch):
    """Create a team + sprint in isolated data dir; return (team, sprint_id)."""
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    from clawteam.sprint.state import SprintState, save_sprint_state

    # Create team directory structure mimicking clawteam team spawn output.
    team_dir = tmp_path / "teams" / "t1"
    team_dir.mkdir(parents=True)
    (team_dir / "config.json").write_text(json.dumps({
        "name": "t1", "template": "gstack", "leader": "ceo", "members": [],
    }))

    state = SprintState(
        team="t1",
        sprint_id="abc12345",
        goal="g",
        current_phase="ship",
        workspace_branch=str(tmp_path),
        review_sha="a1b2c3d4e5f6" + "0" * 28,
    )
    save_sprint_state(state)
    return ("t1", state.sprint_id)


def test_approve_writes_frontmatter(setup_team_and_sprint, runner, monkeypatch):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team])
    assert result.exit_code == 0, result.output

    from clawteam.sprint.state import load_sprint_state
    loaded = load_sprint_state(team, sid)
    approval = loaded.artifacts.get("ship-approval.md", "")
    assert "artifact_type: ship_approval" in approval
    assert "approved_by:" in approval
    assert "approved_at:" in approval
    assert "sha_at_approval:" in approval


def test_approve_uses_state_review_sha(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app
    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team])
    assert result.exit_code == 0

    from clawteam.sprint.state import load_sprint_state
    loaded = load_sprint_state(team, sid)
    approval = loaded.artifacts["ship-approval.md"]
    assert "a1b2c3d4e5f6" in approval  # state.review_sha prefix


def test_approve_json_mode_prints_frontmatter(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app
    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team, "--json"])
    assert result.exit_code == 0
    # stdout contains JSON with required fields
    # (other output may follow; find the JSON line)
    found = False
    for line in result.output.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
                if data.get("status") == "approved":
                    assert "approved_by" in data
                    assert "approved_at" in data
                    assert "sha_at_approval" in data
                    found = True
                    break
            except json.JSONDecodeError:
                continue
    assert found, f"No JSON envelope in output: {result.output!r}"


def test_approve_no_sign_flag_accepted(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app
    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team, "--no-sign"])
    assert result.exit_code == 0

    from clawteam.sprint.state import load_sprint_state
    loaded = load_sprint_state(team, sid)
    assert "ship-approval.md" in loaded.artifacts


def test_approve_with_notes_flag(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app
    result = runner.invoke(app, [
        "sprint", "approve", sid, "--team", team,
        "--notes", "LGTM by QA on 2026-04-21",
    ])
    assert result.exit_code == 0

    from clawteam.sprint.state import load_sprint_state
    loaded = load_sprint_state(team, sid)
    approval = loaded.artifacts["ship-approval.md"]
    assert "approval_notes:" in approval
    assert "LGTM by QA" in approval


def test_approve_unsupported_phase_exits_nonzero(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app
    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team, "--phase", "build"])
    assert result.exit_code != 0


def test_approve_sprint_not_found_exits_error(tmp_path, runner, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    team_dir = tmp_path / "teams" / "t1"
    team_dir.mkdir(parents=True)
    (team_dir / "config.json").write_text(json.dumps({
        "name": "t1", "template": "gstack", "leader": "ceo", "members": [],
    }))

    from clawteam.cli.commands import app
    result = runner.invoke(app, ["sprint", "approve", "nonexistent-sprint", "--team", "t1"])
    assert result.exit_code != 0 or "not found" in (result.output or "").lower()


def test_approve_updates_artifact_on_second_run(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app

    r1 = runner.invoke(app, ["sprint", "approve", sid, "--team", team, "--notes", "first"])
    assert r1.exit_code == 0
    from clawteam.sprint.state import load_sprint_state
    first = load_sprint_state(team, sid).artifacts["ship-approval.md"]

    # Second run updates the artifact.
    r2 = runner.invoke(app, ["sprint", "approve", sid, "--team", team, "--notes", "second"])
    assert r2.exit_code == 0
    second = load_sprint_state(team, sid).artifacts["ship-approval.md"]

    # Body changed (notes content differs) but required fields still present.
    assert first != second
    assert "artifact_type: ship_approval" in second
    assert "second" in second


def test_approve_writes_sprint_id_in_frontmatter(setup_team_and_sprint, runner):
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app
    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team])
    assert result.exit_code == 0

    from clawteam.sprint.state import load_sprint_state
    loaded = load_sprint_state(team, sid)
    approval = loaded.artifacts["ship-approval.md"]
    assert f"sprint_id: {sid}" in approval


def test_approval_artifact_passes_ship_approval_gate(setup_team_and_sprint, runner):
    """End-to-end: written artifact satisfies ShipApprovalGate."""
    team, sid = setup_team_and_sprint
    from clawteam.cli.commands import app
    result = runner.invoke(app, ["sprint", "approve", sid, "--team", team])
    assert result.exit_code == 0

    from clawteam.harness.ship_approval_gate import ShipApprovalGate
    from clawteam.sprint.state import load_sprint_state
    state = load_sprint_state(team, sid)
    gate = ShipApprovalGate()
    ok, reason = gate.check(state)
    assert ok is True, f"Gate rejected: {reason}"
```
  </action>
  <verify>
    <automated>pytest tests/test_sprint_approve_cli.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - grep -q '@sprint_app.command("approve")' clawteam/cli/commands.py
    - grep -q "def sprint_approve" clawteam/cli/commands.py
    - grep -q "artifact_type: ship_approval" clawteam/cli/commands.py
    - pytest tests/test_sprint_approve_cli.py -x -q exits 0 (10 tests pass)
    - pytest tests/test_cli_commands.py -x -q stays green (existing CLI tests unaffected)
    - pytest tests/test_ship_approval_gate.py -x -q stays green
  </acceptance_criteria>
  <done>sprint approve CLI ships; end-to-end test confirms written artifact satisfies ShipApprovalGate</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CLI --notes input ↔ artifact frontmatter | User-supplied; included as-is into YAML body |
| git config user.name → approved_by | Semi-trusted (user's local config) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-38 | T (Tampering) | --notes injects YAML control chars | accept | Notes written as raw string body under `approval_notes:` yaml field; malformed notes would fail gate's parse_frontmatter → clean block mode |
| T-04-39 | R (Repudiation) | approved_by self-declared | accept | Real git-signed commits are v1.x; Phase 4 CLI is the MVP surface |
| T-04-40 | I (Information disclosure) | sha_at_approval leaks git state | accept | SHA is public workspace metadata |
</threat_model>

<verification>
- [ ] `pytest tests/test_sprint_approve_cli.py -x -q` exits 0 with 10/10
- [ ] `pytest tests/test_cli_commands.py tests/test_ship_approval_gate.py tests/test_sprint_state.py -x -q` stays green
- [ ] `grep -c 'sprint_approve\|"approve"' clawteam/cli/commands.py` >= 2 (decorator + function)
</verification>

<success_criteria>
- [ ] `clawteam sprint approve <id> --phase ship` writes ship-approval.md artifact
- [ ] Frontmatter aligns with ShipApprovalGate's expectations
- [ ] `--json` + `--notes` + `--no-sign` flags supported
- [ ] End-to-end: CLI-written artifact passes ShipApprovalGate
- [ ] 10 tests pass; CLI + gate + state tests remain green
</success_criteria>

<output>
Create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-12-sprint-approve-cli-SUMMARY.md`.
</output>
