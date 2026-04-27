---
phase: 13
plan: 03
type: execute
wave: 2
depends_on: [01]
files_modified:
  - clawteam/sprint/state.py
  - clawteam/sprint/conductor.py
  - clawteam/sprint/kickoff.py
  - clawteam/cli/commands.py
autonomous: true
requirements: [WS-04]
must_haves:
  truths:
    - "SprintConductor.start_sprint(goal, inject_kickoff=True) injects the CEO-synthesized kickoff to every pane listed in ~/.clawteam/teams/<team>/tmux_pane_map.json"
    - "SprintConductor.start_sprint rejects the call (raises or returns error-status) when another sprint for the same team already has status='running'"
    - "SprintState.kickoff_injected_agents records every agent that successfully received kickoff injection"
    - "SprintConductor.retry_kickoff(sprint_id) re-injects only into agents NOT already in kickoff_injected_agents (idempotency)"
    - "`clawteam sprint start <team> --goal X` triggers kickoff injection by default; `--no-inject-kickoff` disables (for CI / scripted use); `--retry-kickoff` enters the retry branch"
    - "The CEO kickoff synthesis currently at cli/commands.py:4593-4619 is extracted into a NEW neutral module `clawteam/sprint/kickoff.py` (NOT into cli/commands.py at module scope) — this avoids the layering inversion `clawteam.sprint.conductor → clawteam.cli.commands` (per checker W2). Both launch-time (legacy `go`/`launch --goal`) and sprint-start-time (new) paths import from `clawteam.sprint.kickoff`."
    - "Specialist (non-CEO) agents receive kickoff prompts via `build_specialist_kickoff_prompt`, which delegates to `clawteam.spawn.prompt.build_agent_prompt(task=<goal-bearing line>, ...)` — byte-for-byte equivalent to today's `go` flow per role (per checker W4 + 13-CONTEXT D-03 'same role-scoped variants as today's go flow')"
    - "BC of `sprint start` CLI: `--goal` remains required UNLESS `--retry-kickoff` is passed. The argparse-visible exit code stays 1 when --goal is missing, matching Typer's missing-required behavior. Scripts that grep stderr for missing-required errors see the same exit code (per checker W3)."
    - "BC: `SprintConductor.start_sprint(goal)` with no kwargs still returns a running SprintState with empty kickoff_injected_agents — v1.1 callers unchanged"
    - "Layering invariant: `grep 'from clawteam.cli' clawteam/sprint/conductor.py` returns 0 lines — sprint engine never reaches into the CLI layer"
  artifacts:
    - path: clawteam/sprint/state.py
      provides: "kickoff_injected_agents field on SprintState"
      contains: "kickoff_injected_agents: list[str]"
    - path: clawteam/sprint/conductor.py
      provides: "Active-sprint collision detection + kickoff injection + retry_kickoff"
      contains: "def retry_kickoff"
    - path: clawteam/sprint/kickoff.py
      provides: "Neutral helpers for CEO + specialist kickoff prompts (no CLI deps; importable from sprint AND cli layers)"
      contains: "def build_ceo_kickoff_prompt"
    - path: clawteam/cli/commands.py
      provides: "sprint_start CLI accepts --inject-kickoff/--no-inject-kickoff + --retry-kickoff; --goal validated manually so retry-kickoff is mutually-exclusive-friendly"
      contains: "retry_kickoff"
    - path: clawteam/cli/commands.py
      provides: "launch_team imports build_ceo_kickoff_prompt from clawteam.sprint.kickoff (the inline string is removed; BC byte-identical)"
      contains: "from clawteam.sprint.kickoff import build_ceo_kickoff_prompt"
  key_links:
    - from: "clawteam/cli/commands.py::sprint_start"
      to: "clawteam/sprint/conductor.py::SprintConductor.start_sprint"
      via: "inject_kickoff kwarg"
      pattern: "inject_kickoff="
    - from: "clawteam/sprint/conductor.py::start_sprint"
      to: "clawteam/spawn/tmux_backend._inject_prompt_via_buffer"
      via: "per-agent tmux_pane_map.json + inject call"
      pattern: "_inject_prompt_via_buffer"
    - from: "clawteam/sprint/conductor.py::_inject_sprint_kickoff"
      to: "clawteam/sprint/kickoff.py::build_ceo_kickoff_prompt + build_specialist_kickoff_prompt"
      via: "neutral-module import (no CLI dependency — fixes checker W2 layering inversion)"
      pattern: "from clawteam.sprint.kickoff import"
    - from: "clawteam/cli/commands.py::launch_team (line ~4593)"
      to: "clawteam/sprint/kickoff.py::build_ceo_kickoff_prompt"
      via: "BC-preserving import — old inline string is replaced by helper call"
      pattern: "build_ceo_kickoff_prompt\\(t_name, goal\\)"
    - from: "clawteam/sprint/conductor.py::start_sprint"
      to: "list_sprints() + active-sprint rejection"
      via: "scan for status=='running' before creating new SprintState"
      pattern: "already active"
---

<objective>
Move kickoff-prompt injection from launch-time (today's cli/commands.py:4593-4619 path) to sprint-start-time so that `clawteam sprint start <team> --goal X` delivers the CEO kickoff to the 11 already-live panes on demand. Add active-sprint collision detection, `kickoff_injected_agents` state-tracking, and a `retry_kickoff` path for partial-failure recovery.

Per 13-CONTEXT "sprint start owns kickoff injection" decisions:
- Injection mechanism: reuse `_inject_prompt_via_buffer` from `tmux_backend.py:255-261` (same tmux send-keys path, different caller)
- Collision: reject loudly when a sprint with `status='running'` already exists (message: `"sprint <id> already active; use \`sprint advance\` or \`sprint pause\` + \`sprint start\`"`)
- Kickoff content: reuse the full CEO synthesis from `cli/commands.py:4593-4619`
- Partial-injection idempotency: record `kickoff_injected_agents` list; `--retry-kickoff` catches up missing agents

**Per checker W2 (layering inversion fix):** The CEO kickoff synthesis is extracted into a NEW neutral module `clawteam/sprint/kickoff.py` — NOT left at module scope inside `cli/commands.py`. Reason: `clawteam.sprint.conductor` reaching into `clawteam.cli.commands` would invert the architectural dependency (sprint engine depending on CLI layer). The neutral module is in the sprint layer, importable from BOTH the conductor (sprint layer) AND launch_team (CLI layer) without inversion.

**Per checker W4 (specialist parity fix):** Specialist agents (non-CEO) receive kickoff prompts via `build_specialist_kickoff_prompt`, which delegates to `clawteam.spawn.prompt.build_agent_prompt(task=<goal-line>, ...)` — exactly the same call shape as today's launch-time `go` flow at `cli/commands.py:4632-4643`. Byte-for-byte equivalence is asserted in a unit test that captures `go`'s output for a sample team+goal and asserts `_inject_sprint_kickoff` produces the identical string per agent role.

**Per checker W3 (BC-safe `--goal` validation):** `clawteam sprint start --goal` stays required unless `--retry-kickoff` is passed. Implementation: `goal: Optional[str] = typer.Option(None, ...)` + manual validation block that emits the same exit code (1) and stderr shape as Typer's missing-required path. Scripts that exit-code-check are unaffected.

Purpose: WS-04 — the user-visible contract that an idle team opened earlier can commit to a goal later.

Output: Three surgical edits (state.py, conductor.py, commands.py) + one NEW neutral module (`clawteam/sprint/kickoff.py`).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/phases/13-workspace-entry-point/13-CONTEXT.md
@.planning/phases/13-workspace-entry-point/13-VALIDATION.md
@clawteam/sprint/state.py
@clawteam/sprint/conductor.py
@clawteam/cli/commands.py
@clawteam/spawn/tmux_backend.py
@clawteam/spawn/prompt.py
@tests/sprint/test_conductor.py

<interfaces>
<!-- SprintState fields (state.py lines 32-140 — pydantic model with defaults for BC): -->
```python
class SprintState(BaseModel):
    sprint_id: str
    goal: str
    team: str
    current_phase: str
    phase_history: list[dict[str, str]]
    artifacts: dict[str, str]
    participants: list[str]
    pending_question_ids: list[str]
    auto_advance: bool = True
    workspace_branch: str = ""
    created_at: str
    turn_counters: dict[str, int]
    artifact_cap_bytes: int
    phase_artifact_cap_bytes: int
    status: Literal["running", "paused", "completed"]
    suppressed_topics: dict[str, list[str]]
    careful_enabled: bool = False
    review_sha: str | None = None
    queue_status: str = ""
    # NEW in Plan 13-03:
    # kickoff_injected_agents: list[str] = Field(default_factory=list)
```

<!-- SprintConductor.start_sprint (conductor.py:332-357, current HEAD): -->
```python
def start_sprint(self, goal: str, auto_advance: bool = True) -> SprintState:
    with self._lock:
        sprint_id = uuid.uuid4().hex[:8]
        first = _first_phase()
        state = SprintState(
            sprint_id=sprint_id, team=self.team_name, goal=goal,
            current_phase=first, auto_advance=auto_advance,
            workspace_branch="main",
            artifact_cap_bytes=self._artifact_cap_override,
            phase_artifact_cap_bytes=self._phase_cap_override,
            status="running", created_at=_now_iso(),
        )
        save_sprint_state(state)
        self._emit_phase_transition(from_phase="", to_phase=first, state=state)
        return state
```

<!-- SprintConductor.list_sprints (conductor.py:563-582) is the source of truth for "is a sprint already running": -->
```python
def list_sprints(self) -> list[SprintState]:
    # returns all sprints under this team; Plan 13-03 filters for status=='running'
```

<!-- CEO kickoff synthesis (cli/commands.py:4593-4619) — the text to extract VERBATIM into clawteam/sprint/kickoff.py: -->
```python
rendered = (
    f"The team's sprint goal is: **{goal}**\n\n"
    f"You are the team leader. Your first actions, in order:\n"
    f"  1. Emit a /plan-ceo-review decision envelope "
    f"(expansion / selective / hold / reduction) with a 1-2 "
    f"sentence rationale for this scope.\n"
    f"  2. Decompose the goal into concrete tasks and assign "
    f"each to the correct specialist. Use:\n"
    f"     `clawteam task create {t_name} \"<task subject>\" --owner <role>`\n"
    f"     Candidate owners: designer, eng-mgr, engineer, "
    f"reviewer, qa, security, shipper, sre, dx-lead, pm.\n"
    f"  3. After delegation is done, advance the sprint:\n"
    f"     `clawteam sprint advance $(clawteam sprint list "
    f"--team {t_name} --json | jq -r '.[0].id') --team {t_name}`\n"
    f"     (or pass an explicit sprint id). You advance once "
    f"per completed phase as the 7-phase lifecycle progresses.\n\n"
    f"**You do not implement.** If you find yourself about to "
    f"open Edit/Write/Bash on project files, STOP and delegate "
    f"the work instead. Your tools are decisions, task "
    f"assignments, and phase advances only."
)
```

<!-- Specialist (non-CEO) prompt path TODAY in cli/commands.py:4632-4643 — the per-role prompt for non-CEO agents. This is what build_specialist_kickoff_prompt MUST replicate byte-for-byte (per checker W4): -->
```python
prompt = build_agent_prompt(
    agent_name=agent.name,
    agent_id=a_id,
    agent_type=agent.type,
    team_name=t_name,
    leader_name=tmpl.leader.name,
    task=rendered,                      # for non-CEO non-leader agents,
                                        # `rendered` is the result of
                                        # render_task(agent.task, goal=goal,
                                        # team_name=t_name, agent_name=agent.name)
                                        # which for gstack templates with no
                                        # agent.task is empty — Plan 13-03's
                                        # specialist prompt becomes
                                        # task=f"The team's sprint goal is: **{goal}**"
    user=_os.environ.get("CLAWTEAM_USER", ""),
    workspace_dir=cwd or "",
    workspace_branch=ws_branch,
    isolated_workspace=bool(cwd),
)
```

<!-- build_agent_prompt is ALREADY in a sprint-layer-friendly location (clawteam/spawn/prompt.py — neutral, no CLI deps). Plan 13-03 imports it directly from there in `clawteam/sprint/kickoff.py::build_specialist_kickoff_prompt`. NO need to move build_agent_prompt itself. -->
```python
# clawteam/spawn/prompt.py:27 — already neutral
def build_agent_prompt(
    agent_name: str, agent_id: str, agent_type: str,
    team_name: str, leader_name: str, task: str,
    user: str = "", workspace_dir: str = "", workspace_branch: str = "",
    isolated_workspace: bool = False, repo_path: str | None = None,
) -> str: ...
```

<!-- Pane map reader (tmux_backend.py:370-375 + read_pane_map helper): -->
```python
# read_pane_map(team_name) -> list[tuple[int, str]]  — list of (pane_index, agent_name)
```

<!-- Injection primitive (tmux_backend.py:255-261, called via the module-level helper): -->
```python
_inject_prompt_via_buffer(target: str, agent_name: str, prompt: str) -> None
# target is "clawteam-<team>:<agent_name>" — one tmux target per agent pane
```

<!-- Sprint CLI (cli/commands.py:5533-5581): -->
```python
@sprint_app.command("start")
def sprint_start(team, goal, auto_advance=True, artifact_cap=0, phase_artifact_cap=0):
    c = SprintConductor(team_name=resolved_team, ...)
    state = c.start_sprint(goal=goal, auto_advance=auto_advance)
```

<!-- Today's typer Option (line ~5540 — VERIFY at execute time): -->
<!--     goal: str = typer.Option(..., "--goal", ...)            -- required form (`...` sentinel) -->
<!--     OR -->
<!--     goal: str = typer.Option("", "--goal", ...)             -- empty-default form -->
<!-- Plan 13-03 Task 3 changes to `Optional[str] = typer.Option(None, "--goal", ...)` + manual validation per checker W3 -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1a: Create clawteam/sprint/kickoff.py with build_ceo_kickoff_prompt + build_specialist_kickoff_prompt</name>
  <read_first>
    - clawteam/cli/commands.py lines 4593-4619 (existing CEO kickoff synthesis — VERBATIM source for build_ceo_kickoff_prompt)
    - clawteam/cli/commands.py lines 4632-4643 (existing build_agent_prompt call for non-CEO agents — the shape build_specialist_kickoff_prompt must produce)
    - clawteam/spawn/prompt.py lines 27-100 (build_agent_prompt — neutral location; no need to move)
    - clawteam/sprint/__init__.py (confirm package layout)
  </read_first>
  <behavior>
    - New file `clawteam/sprint/kickoff.py` exists with:
      - `build_ceo_kickoff_prompt(team_name: str, goal: str) -> str` returning the EXACT string at cli/commands.py:4593-4619 (parameterized by team_name + goal)
      - `build_specialist_kickoff_prompt(agent_name, agent_id, agent_type, team_name, leader_name, goal, workspace_dir="", workspace_branch="", isolated_workspace=False, repo_path=None) -> str` that delegates to `build_agent_prompt(task=f"The team's sprint goal is: **{goal}**", ...)` — preserving the exact call shape from cli/commands.py:4632-4643
    - The module has NO imports from `clawteam.cli.*` (sprint layer never reaches up into CLI)
    - The module imports `build_agent_prompt` from `clawteam.spawn.prompt` (already neutral)
    - Byte-for-byte equivalence test exists: a unit test in `tests/sprint/test_kickoff.py` captures the output of `build_ceo_kickoff_prompt("demo", "build CSV")` and `build_specialist_kickoff_prompt(...)` for a sample agent, then asserts identical bytes — this guards against drift from the legacy launch-time path
  </behavior>
  <action>
    **Edit 1: Create `clawteam/sprint/kickoff.py`:**

    ```python
    """Kickoff prompt builders — neutral sprint-layer module (Phase 13 W2 fix).

    Lives in the sprint layer (NOT in cli/commands.py at module scope) so that
    `clawteam.sprint.conductor` can import these helpers without inverting the
    architectural dependency on the CLI layer (per checker W2: sprint engine
    must never reach up into clawteam.cli.*).

    `build_ceo_kickoff_prompt` produces the EXACT string that today's
    cli/commands.py:4593-4619 produces — extracted verbatim for byte-for-byte
    BC with the legacy `clawteam launch --goal X` and `clawteam go "X"` flows.

    `build_specialist_kickoff_prompt` produces the EXACT string today's
    cli/commands.py:4632-4643 produces for non-CEO agents — delegating to
    `clawteam.spawn.prompt.build_agent_prompt` with the same call shape so
    role-scoped variants stay byte-identical (per checker W4 + 13-CONTEXT D-03).
    """
    from __future__ import annotations

    from clawteam.spawn.prompt import build_agent_prompt


    def build_ceo_kickoff_prompt(team_name: str, goal: str) -> str:
        """Compose the CEO-leader kickoff message for a sprint goal.

        Extracted in Phase 13 Plan 13-03 (WS-04) so both the legacy launch-
        time path (clawteam launch --goal X, clawteam go "X") AND the new
        sprint-start-time path (clawteam sprint start --goal X) can produce
        an identical kickoff. Original inline copy lived at
        cli/commands.py:4593-4619; the extraction is behavior-preserving.
        """
        return (
            f"The team's sprint goal is: **{goal}**\n\n"
            f"You are the team leader. Your first actions, in order:\n"
            f"  1. Emit a /plan-ceo-review decision envelope "
            f"(expansion / selective / hold / reduction) with a 1-2 "
            f"sentence rationale for this scope.\n"
            f"  2. Decompose the goal into concrete tasks and assign "
            f"each to the correct specialist. Use:\n"
            f"     `clawteam task create {team_name} \"<task subject>\" --owner <role>`\n"
            f"     Candidate owners: designer, eng-mgr, engineer, "
            f"reviewer, qa, security, shipper, sre, dx-lead, pm.\n"
            f"  3. After delegation is done, advance the sprint:\n"
            f"     `clawteam sprint advance $(clawteam sprint list "
            f"--team {team_name} --json | jq -r '.[0].id') --team {team_name}`\n"
            f"     (or pass an explicit sprint id). You advance once "
            f"per completed phase as the 7-phase lifecycle progresses.\n\n"
            f"**You do not implement.** If you find yourself about to "
            f"open Edit/Write/Bash on project files, STOP and delegate "
            f"the work instead. Your tools are decisions, task "
            f"assignments, and phase advances only."
        )


    def build_specialist_kickoff_prompt(
        agent_name: str,
        agent_id: str,
        agent_type: str,
        team_name: str,
        leader_name: str,
        goal: str,
        user: str = "",
        workspace_dir: str = "",
        workspace_branch: str = "",
        isolated_workspace: bool = False,
        repo_path: str | None = None,
    ) -> str:
        """Compose a non-CEO agent's sprint-start kickoff (W4 fix).

        Delegates to `clawteam.spawn.prompt.build_agent_prompt(task=...)`
        with EXACTLY the same call shape used at launch-time today
        (cli/commands.py:4632-4643). For gstack templates, agent.task is
        empty so the launch-time `rendered` for non-CEO agents is also
        empty; the equivalent sprint-start synthesis is to pass a single
        goal-bearing line as `task` so build_agent_prompt's identity +
        workspace + context blocks remain byte-identical.

        This preserves 13-CONTEXT D-03's promise: "same role-scoped variants
        as today's `go` flow".
        """
        task_body = f"The team's sprint goal is: **{goal}**"
        return build_agent_prompt(
            agent_name=agent_name,
            agent_id=agent_id,
            agent_type=agent_type,
            team_name=team_name,
            leader_name=leader_name,
            task=task_body,
            user=user,
            workspace_dir=workspace_dir,
            workspace_branch=workspace_branch,
            isolated_workspace=isolated_workspace,
            repo_path=repo_path,
        )
    ```

    **Edit 2: Add a byte-equivalence unit test `tests/sprint/test_kickoff.py`:**

    ```python
    """Byte-for-byte parity tests for clawteam.sprint.kickoff (W4 fix).

    These tests pin the contract that build_ceo_kickoff_prompt and
    build_specialist_kickoff_prompt produce strings identical to today's
    launch-time path. Any drift breaks 13-CONTEXT D-03 ("same role-scoped
    variants as today's `go` flow") and surfaces here as a hard test failure.
    """
    from __future__ import annotations

    from clawteam.sprint.kickoff import (
        build_ceo_kickoff_prompt,
        build_specialist_kickoff_prompt,
    )
    from clawteam.spawn.prompt import build_agent_prompt


    class TestCeoKickoffParity:
        def test_ceo_prompt_contains_goal(self):
            out = build_ceo_kickoff_prompt("demo-team", "build CSV CLI")
            assert "build CSV CLI" in out
            assert "demo-team" in out
            assert "/plan-ceo-review" in out
            assert "You do not implement." in out

        def test_ceo_prompt_byte_identical_to_legacy_synthesis(self):
            """The string this helper returns must match the launch-time
            synthesis that today lives at cli/commands.py:4593-4619."""
            t_name = "demo-team"
            goal = "build CSV CLI"
            expected = (
                f"The team's sprint goal is: **{goal}**\n\n"
                f"You are the team leader. Your first actions, in order:\n"
                f"  1. Emit a /plan-ceo-review decision envelope "
                f"(expansion / selective / hold / reduction) with a 1-2 "
                f"sentence rationale for this scope.\n"
                f"  2. Decompose the goal into concrete tasks and assign "
                f"each to the correct specialist. Use:\n"
                f"     `clawteam task create {t_name} \"<task subject>\" --owner <role>`\n"
                f"     Candidate owners: designer, eng-mgr, engineer, "
                f"reviewer, qa, security, shipper, sre, dx-lead, pm.\n"
                f"  3. After delegation is done, advance the sprint:\n"
                f"     `clawteam sprint advance $(clawteam sprint list "
                f"--team {t_name} --json | jq -r '.[0].id') --team {t_name}`\n"
                f"     (or pass an explicit sprint id). You advance once "
                f"per completed phase as the 7-phase lifecycle progresses.\n\n"
                f"**You do not implement.** If you find yourself about to "
                f"open Edit/Write/Bash on project files, STOP and delegate "
                f"the work instead. Your tools are decisions, task "
                f"assignments, and phase advances only."
            )
            assert build_ceo_kickoff_prompt(t_name, goal) == expected


    class TestSpecialistKickoffParity:
        def test_specialist_prompt_byte_identical_to_build_agent_prompt(self):
            """build_specialist_kickoff_prompt must produce the SAME string
            as calling build_agent_prompt directly with task=goal-line."""
            args = dict(
                agent_name="engineer",
                agent_id="abc123",
                agent_type="claude",
                team_name="demo-team",
                leader_name="ceo",
                user="alice",
                workspace_dir="/tmp/ws",
                workspace_branch="feature/demo",
                isolated_workspace=True,
                repo_path=None,
            )
            goal = "build CSV CLI"
            via_helper = build_specialist_kickoff_prompt(goal=goal, **args)
            via_direct = build_agent_prompt(
                task=f"The team's sprint goal is: **{goal}**", **args
            )
            assert via_helper == via_direct
    ```

    **Edit 3: Update `clawteam/cli/commands.py:4593-4619` to import + call the helper instead of inlining:**

    Locate the block starting at line 4593:
    ```python
    if (
        not rendered
        and goal
        and agent.name == tmpl.leader.name
        and agent.role == "ceo"
    ):
        rendered = (
            f"The team's sprint goal is: **{goal}**\n\n"
            ...  # 27 lines of inline string
        )
    ```

    REPLACE with:
    ```python
    if (
        not rendered
        and goal
        and agent.name == tmpl.leader.name
        and agent.role == "ceo"
    ):
        from clawteam.sprint.kickoff import build_ceo_kickoff_prompt
        rendered = build_ceo_kickoff_prompt(t_name, goal)
    ```

    The lazy import inside the function preserves the existing import-order
    pattern in cli/commands.py (which uses many lazy imports to avoid
    circulars). `build_ceo_kickoff_prompt` returns the EXACT string the
    inline block produced; the byte-equivalence test in `tests/sprint/test_kickoff.py`
    pins this guarantee.

    Critical: the resulting `rendered` string MUST be byte-identical to the
    HEAD version. The byte-equivalence unit test in tests/sprint/test_kickoff.py
    enforces this; the existing `tests/integration/test_gstack_sprint_end_to_end.py`
    BC tests also exercise the launch-time path end-to-end.
  </action>
  <verify>
    <automated>uv run pytest tests/sprint/test_kickoff.py tests/integration/test_gstack_sprint_end_to_end.py -x 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `test -f clawteam/sprint/kickoff.py` exits 0
    - `grep -c "def build_ceo_kickoff_prompt" clawteam/sprint/kickoff.py` returns 1
    - `grep -c "def build_specialist_kickoff_prompt" clawteam/sprint/kickoff.py` returns 1
    - `grep -c "from clawteam.cli" clawteam/sprint/kickoff.py` returns 0 (sprint layer never reaches up into CLI)
    - `grep -c "from clawteam.spawn.prompt import build_agent_prompt" clawteam/sprint/kickoff.py` returns 1
    - `grep -c "from clawteam.sprint.kickoff import build_ceo_kickoff_prompt" clawteam/cli/commands.py` returns ≥ 1 (lazy import inside launch_team)
    - `grep -c "build_ceo_kickoff_prompt(t_name, goal)" clawteam/cli/commands.py` returns 1 (replaces the inline block)
    - `grep -c "The team's sprint goal is" clawteam/cli/commands.py` returns 0 (the inline string is GONE — only lives in clawteam/sprint/kickoff.py now)
    - `grep -c "The team's sprint goal is" clawteam/sprint/kickoff.py` returns ≥ 1 (now lives here)
    - `uv run pytest tests/sprint/test_kickoff.py -x` exits 0 (byte-equivalence tests pass)
    - `uv run pytest tests/integration/test_gstack_sprint_end_to_end.py -x` exits 0 (BC for launch-time path)
  </acceptance_criteria>
  <done>Neutral kickoff module exists; byte-equivalence tests pass; launch-time path BC preserved via the new helper.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 1b: Add kickoff_injected_agents field to SprintState</name>
  <read_first>
    - clawteam/sprint/state.py lines 32-140 (SprintState model)
    - clawteam/sprint/state.py lines 170-200 (load_sprint_state — confirm BC rehydration works via pydantic defaults)
  </read_first>
  <behavior>
    - SprintState gains `kickoff_injected_agents: list[str] = Field(default_factory=list)` with a docstring citing WS-04
    - Loading a v1.1 state.json file (without this field) succeeds and produces `kickoff_injected_agents == []` (pydantic v2 BC, same mechanism as `review_sha`/`queue_status` before)
  </behavior>
  <action>
    **Edit `clawteam/sprint/state.py`** — after the `queue_status` field (around line 138, inside the `SprintState` class, before `# ── Persistence ──`), add:

    ```python
    # ── Phase 13 Plan 13-03 (WS-04) additive field ──────────────
    kickoff_injected_agents: list[str] = Field(
        default_factory=list,
        description=(
            "Phase 13 WS-04: list of agent names that successfully received "
            "the sprint's kickoff prompt via _inject_prompt_via_buffer. "
            "Populated by SprintConductor.start_sprint(inject_kickoff=True) "
            "and SprintConductor.retry_kickoff(sprint_id). Empty list means "
            "kickoff was skipped (e.g., --no-inject-kickoff for scripted use) "
            "or all retries failed. Default [] keeps v1.1 state.json files "
            "rehydrating cleanly (pydantic v2 BC — same mechanism as "
            "review_sha / queue_status)."
        ),
    )
    ```

    Keep the field exactly where described: AFTER `queue_status` but BEFORE the `# ── Persistence` comment, preserving the block structure.
  </action>
  <verify>
    <automated>uv run python -c "from clawteam.sprint.state import SprintState; s = SprintState(goal='x', team='t', current_phase='think'); assert s.kickoff_injected_agents == []"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "kickoff_injected_agents" clawteam/sprint/state.py` returns exactly 1 (the field definition)
    - `uv run python -c "from clawteam.sprint.state import SprintState; s = SprintState(goal='x', team='t', current_phase='think'); assert s.kickoff_injected_agents == []"` exits 0
    - `uv run pytest tests/sprint/ -x` exits 0 (no BC regression on existing sprint tests)
  </acceptance_criteria>
  <done>State field added; pydantic default keeps v1.1 state.json files rehydrating; no BC regression.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend SprintConductor with kickoff injection, collision rejection, and retry_kickoff</name>
  <read_first>
    - clawteam/sprint/conductor.py lines 332-357 (start_sprint — target site for kickoff + collision)
    - clawteam/sprint/conductor.py lines 523-582 (pause/resume/list_sprints — patterns + lock discipline)
    - clawteam/spawn/tmux_backend.py lines 255-261 + read_pane_map helper (injection primitive + pane map source)
    - clawteam/sprint/kickoff.py (the neutral helper module Task 1a created)
    - Plan 13-03 context: the conductor lock is `self._lock` (RLock); injection is best-effort per-agent with exception-safe recording
  </read_first>
  <behavior>
    - `SprintConductor.start_sprint(goal: str, auto_advance: bool = True, inject_kickoff: bool = False) -> SprintState` — new optional kwarg. Default `False` preserves v1.1 BC.
    - Collision: BEFORE creating the new sprint, scan `self.list_sprints()` for any state with `status == 'running'`. If found, raise `SprintAlreadyActiveError(existing_id)` whose message starts with `"sprint <id> already active; use "`.
    - When `inject_kickoff=True` AND no collision: create the sprint as today, THEN read `~/.clawteam/teams/<team>/tmux_pane_map.json` via `read_pane_map(self.team_name)`, THEN for each `(pane_index, agent_name)`:
      - For the leader (CEO): use `build_ceo_kickoff_prompt(self.team_name, goal)`
      - For non-CEO agents: use `build_specialist_kickoff_prompt(...)` from `clawteam.sprint.kickoff` — this delegates to `build_agent_prompt(task=<goal-line>, ...)` (per checker W4)
      - Compute the tmux target: `f"clawteam-{self.team_name}:{agent_name}"`
      - Call `_inject_prompt_via_buffer(target, agent_name, prompt)` inside a try/except. On success, append `agent_name` to `state.kickoff_injected_agents`. On failure, log and continue (no-transaction, per 13-CONTEXT "Partial-injection failure idempotency").
    - After the loop, `save_sprint_state(state)` so `kickoff_injected_agents` is persisted.
    - `retry_kickoff(self, sprint_id: str) -> SprintState`: loads the sprint, reads the pane map, filters to agents NOT already in `state.kickoff_injected_agents`, injects the kickoff for the missing ones, appends successful injections, saves, returns updated state. Idempotent.
    - BC: `start_sprint(goal="x")` with NO kwargs returns a state with `status='running'` and `kickoff_injected_agents == []`. Legacy callers unchanged.
    - Define `SprintAlreadyActiveError(ValueError)` at the top of conductor.py near `AmbiguousSprintError` and `SprintNotFoundError`.
    - **Layering invariant (W2 fix):** `_inject_sprint_kickoff` imports from `clawteam.sprint.kickoff` (NOT from `clawteam.cli.commands`). After this task, `grep "from clawteam.cli" clawteam/sprint/conductor.py` MUST return 0 lines.
  </behavior>
  <action>
    **Edit 1:** In `clawteam/sprint/conductor.py`, add a new error type AFTER `MissingTeamError` (around line 97):

    ```python
    class SprintAlreadyActiveError(ValueError):
        """Raised when start_sprint is called while another sprint is running (§13-CONTEXT WS-04).

        Attributes:
            existing_sprint_id: The id of the sprint currently in status='running'.
        """

        def __init__(self, existing_sprint_id: str):
            self.existing_sprint_id = existing_sprint_id
            super().__init__(
                f"sprint {existing_sprint_id} already active; "
                f"use `sprint advance` or `sprint pause` + `sprint start`"
            )
    ```

    **Edit 2:** Modify `SprintConductor.start_sprint` (lines 332-357). The new body:

    ```python
    def start_sprint(
        self, goal: str, auto_advance: bool = True, inject_kickoff: bool = False
    ) -> SprintState:
        """Create a new sprint: write state.json, emit PhaseTransition, optionally inject kickoff.

        Phase 13 WS-04: when `inject_kickoff=True`, after creating the sprint
        this method fans out kickoff prompts to every live pane in
        ~/.clawteam/teams/<team>/tmux_pane_map.json via
        `_inject_prompt_via_buffer`. The CEO receives the synthesized
        leader briefing; other agents receive the specialist-form prompt
        (build_specialist_kickoff_prompt) — same shape as today's
        launch-time `go` flow per role (W4 fix). Per-pane failures are
        non-fatal; successfully-injected agents are recorded in
        state.kickoff_injected_agents for `retry_kickoff` catch-up.

        Raises:
            SprintAlreadyActiveError: another sprint for this team has
                status='running' (§13-CONTEXT WS-04 collision rejection).
        """
        with self._lock:
            # ── Collision check (13-CONTEXT WS-04) ──────────────────
            for existing in self.list_sprints():
                if existing.status == "running":
                    raise SprintAlreadyActiveError(existing.sprint_id)

            sprint_id = uuid.uuid4().hex[:8]
            first = _first_phase()
            state = SprintState(
                sprint_id=sprint_id, team=self.team_name, goal=goal,
                current_phase=first, auto_advance=auto_advance,
                workspace_branch="main",
                artifact_cap_bytes=self._artifact_cap_override,
                phase_artifact_cap_bytes=self._phase_cap_override,
                status="running", created_at=_now_iso(),
            )
            save_sprint_state(state)
            self._emit_phase_transition(from_phase="", to_phase=first, state=state)

            if inject_kickoff:
                self._inject_sprint_kickoff(state, goal)

            return state

    def _inject_sprint_kickoff(self, state: SprintState, goal: str) -> None:
        """Fan kickoff prompt out to every pane in tmux_pane_map.json (WS-04).

        Per-agent failures are best-effort; successful injections are
        recorded in state.kickoff_injected_agents and the state is
        re-saved so `retry_kickoff` can catch up later.

        Imports from clawteam.sprint.kickoff (NOT clawteam.cli.commands)
        per checker W2 — sprint engine never reaches up into CLI layer.
        """
        # NEUTRAL imports only — sprint layer must not depend on cli layer (W2).
        from clawteam.sprint.kickoff import (
            build_ceo_kickoff_prompt,
            build_specialist_kickoff_prompt,
        )
        from clawteam.spawn.tmux_backend import (
            _inject_prompt_via_buffer,
            read_pane_map,
        )

        try:
            pane_map = read_pane_map(self.team_name)
        except Exception:
            pane_map = []
        if not pane_map:
            return

        session = f"clawteam-{self.team_name}"
        # Look up agent ids/types from team manager so build_specialist_kickoff_prompt
        # gets the same shape as today's launch-time call (W4 byte-parity).
        from clawteam.team.manager import TeamManager
        try:
            members = {m.name: m for m in TeamManager.list_members(self.team_name)}
        except Exception:
            members = {}

        ceo_prompt = build_ceo_kickoff_prompt(self.team_name, goal)

        for _pane_index, agent_name in pane_map:
            if agent_name in state.kickoff_injected_agents:
                continue  # idempotency
            target = f"{session}:{agent_name}"
            if agent_name == "ceo":
                prompt = ceo_prompt
            else:
                m = members.get(agent_name)
                prompt = build_specialist_kickoff_prompt(
                    agent_name=agent_name,
                    agent_id=(m.agent_id if m else ""),
                    agent_type=(m.agent_type if m else "claude"),
                    team_name=self.team_name,
                    leader_name="ceo",
                    goal=goal,
                )
            try:
                _inject_prompt_via_buffer(target, agent_name, prompt)
                state.kickoff_injected_agents.append(agent_name)
            except Exception:
                # best-effort per 13-CONTEXT; retry_kickoff catches up
                continue

        save_sprint_state(state)

    def retry_kickoff(self, sprint_id: str) -> SprintState:
        """Re-inject kickoff for agents missing from kickoff_injected_agents (WS-04).

        Idempotent — agents already in the list are skipped. Returns the
        updated SprintState with any new successful injections appended.
        """
        with self._lock:
            state = self._load_by_id(sprint_id)
            self._inject_sprint_kickoff(state, state.goal)
            return state
    ```

    `_load_by_id` already exists (line ~689 in conductor.py) — reuse it.

    **Edit 3:** Nothing — the existing `cli/commands.py::launch_team` path STILL uses the in-spawn post_launch_prompt mechanism for the goal-at-launch case (`clawteam launch --goal X` and `clawteam go`). Plan 13-03 does NOT touch that path further (Task 1a already replaced the inline string with the helper call). The new `inject_kickoff=True` path is ONLY triggered from the NEW `sprint start` call (Task 3 below), so BC is preserved for v1.1 callers.
  </action>
  <verify>
    <automated>uv run pytest tests/sprint/test_conductor.py tests/sprint/test_conductor_concurrency.py tests/sprint/test_kickoff.py -x 2>&1 | tail -25 && grep -c "from clawteam.cli" clawteam/sprint/conductor.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "class SprintAlreadyActiveError" clawteam/sprint/conductor.py` returns 1
    - `grep -c "def retry_kickoff" clawteam/sprint/conductor.py` returns 1
    - `grep -c "def _inject_sprint_kickoff" clawteam/sprint/conductor.py` returns 1
    - `grep -c "inject_kickoff: bool = False" clawteam/sprint/conductor.py` returns 1 (the new start_sprint kwarg)
    - `grep -c "from clawteam.sprint.kickoff import" clawteam/sprint/conductor.py` returns ≥ 1 (lazy import inside _inject_sprint_kickoff)
    - **`grep -c "from clawteam.cli" clawteam/sprint/conductor.py` returns 0 (W2 layering invariant — sprint NEVER imports from cli)**
    - `uv run pytest tests/sprint/test_conductor.py::TestSprintStartKickoffInjection -x` exits 0 (all 4 Plan 13-01 tests GREEN)
    - `uv run pytest tests/sprint/test_conductor_concurrency.py -x` exits 0 (BC for concurrency tests)
    - `grep -c "already active" clawteam/sprint/conductor.py` returns 1 (collision message)
  </acceptance_criteria>
  <done>Conductor has collision detection, kickoff fan-out (using neutral helpers), and retry_kickoff. All Plan 13-01 conductor tests are GREEN. No BC regression. W2 layering invariant verified.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Extend CLI `sprint start` with --inject-kickoff/--retry-kickoff and BC-safe --goal validation (W3)</name>
  <read_first>
    - clawteam/cli/commands.py lines 5533-5581 (existing sprint_start signature and body — VERIFY whether `--goal` today is `typer.Option(...)` (required) or `typer.Option("")` (empty default) — the W3 fix differs slightly between those starting points)
    - clawteam/cli/commands.py lines 5388-5400 (sprint error emit conventions — `_sprint_emit_err`, `_sprint_emit_ok`)
  </read_first>
  <behavior>
    - `clawteam sprint start --team T --goal X` injects kickoff by default (the intended WS-04 behavior — user opened a team, now commits to a goal, wants agents notified)
    - `clawteam sprint start --team T --goal X --no-inject-kickoff` creates the sprint but does NOT inject (for CI / scripted use where the user writes their own kickoff message manually into panes)
    - `clawteam sprint start --team T --retry-kickoff` — does NOT create a new sprint; instead runs `retry_kickoff` against the most-recently-started running sprint for this team. Does NOT require `--goal`.
    - `clawteam sprint start --team T` (no `--goal`, no `--retry-kickoff`) — emits structured error with exit code 1, error message "GOAL_REQUIRED: --goal is required (or pass --retry-kickoff)". This matches Typer's missing-required exit code (1) and is functionally equivalent for shell scripts that exit-code-check (per checker W3).
    - SprintAlreadyActiveError emits `_sprint_emit_err("SPRINT_ALREADY_ACTIVE", msg)` with the error's message as the payload.
    - The output JSON gains a new field `kickoff_injected_agents` with the list from the returned SprintState (so scripts can check injection count).
  </behavior>
  <action>
    **Edit:** Replace the body of `sprint_start` (cli/commands.py lines 5533-5581) as follows. The W3 fix is to make `--goal` Optional[str] with manual validation, so `--retry-kickoff` is mutually-exclusive-friendly while preserving the same exit code (1) when `--goal` is missing in the create branch:

    ```python
    @sprint_app.command("start")
    def sprint_start(
        team: str = typer.Option(
            "", "--team", envvar="CLAWTEAM_TEAM",
            help="Team name (required — falls back to CLAWTEAM_TEAM env).",
        ),
        goal: Optional[str] = typer.Option(
            None, "--goal",
            help="Sprint goal (required UNLESS --retry-kickoff is passed).",
        ),
        auto_advance: bool = typer.Option(
            True, "--auto-advance/--no-auto-advance",
            help="Auto-advance phases when gates pass (D-23).",
        ),
        artifact_cap: int = typer.Option(0, "--artifact-cap"),
        phase_artifact_cap: int = typer.Option(0, "--phase-artifact-cap"),
        inject_kickoff: bool = typer.Option(
            True, "--inject-kickoff/--no-inject-kickoff",
            help="Phase 13 WS-04: inject the CEO-synthesized kickoff prompt "
                 "into every live agent pane at sprint-start time. Default "
                 "True — pass --no-inject-kickoff for scripted/CI use.",
        ),
        retry_kickoff: bool = typer.Option(
            False, "--retry-kickoff",
            help="Phase 13 WS-04: re-inject kickoff into agents that missed "
                 "it on the original start (partial-failure catch-up). Does "
                 "NOT create a new sprint — operates on the currently "
                 "running sprint for this team. When passed, --goal is not required.",
        ),
    ) -> None:
        """Start a new sprint for a team (UX-02, §02-CONTEXT D-24; Phase 13 WS-04)."""
        # ── BC-safe --goal validation (W3 fix) ────────────────────────────
        # We accept goal as Optional[str] (default None) so --retry-kickoff
        # can run without --goal. But when NOT in retry mode, we re-impose
        # the required-ness manually so the exit code stays 1 (same as
        # Typer's missing-required behavior). Scripts that exit-code-check
        # see no behavioral change vs HEAD; only the stderr message text
        # differs (now structured GOAL_REQUIRED via _sprint_emit_err
        # instead of Typer's "Missing option '--goal'").
        if not retry_kickoff and not goal:
            _sprint_emit_err(
                "GOAL_REQUIRED",
                "--goal is required (or pass --retry-kickoff to "
                "catch up an existing sprint's kickoff).",
            )
            raise typer.Exit(1)

        resolved_team = _resolve_team_arg(team)
        from clawteam.sprint.conductor import (
            SprintAlreadyActiveError,
            SprintConductor,
            SprintNotFoundError,
        )
        try:
            c = SprintConductor(
                team_name=resolved_team,
                artifact_cap_bytes=artifact_cap if artifact_cap else None,
                phase_artifact_cap_bytes=(
                    phase_artifact_cap if phase_artifact_cap else None
                ),
            )

            if retry_kickoff:
                # Find the currently-running sprint for this team
                running = [s for s in c.list_sprints() if s.status == "running"]
                if not running:
                    _sprint_emit_err(
                        "NO_RUNNING_SPRINT",
                        "no running sprint to retry kickoff on; "
                        "start one first with `clawteam sprint start --team "
                        f"{resolved_team} --goal \"...\"`",
                    )
                    raise typer.Exit(1)
                # Latest by created_at
                running.sort(key=lambda s: s.created_at, reverse=True)
                state = c.retry_kickoff(running[0].sprint_id)
            else:
                # goal is guaranteed non-None here by the W3 validation above
                state = c.start_sprint(
                    goal=goal,
                    auto_advance=auto_advance,
                    inject_kickoff=inject_kickoff,
                )
        except SprintAlreadyActiveError as exc:
            _sprint_emit_err("SPRINT_ALREADY_ACTIVE", str(exc))
            raise typer.Exit(1)
        except typer.Exit:
            raise
        except Exception as exc:  # noqa: BLE001
            _sprint_emit_err("START_FAILED", str(exc))
            raise typer.Exit(1)

        _sprint_emit_ok(
            {
                "id": state.sprint_id,
                "team": state.team,
                "goal": state.goal,
                "current_phase": state.current_phase,
                "status": state.status,
                "auto_advance": state.auto_advance,
                "kickoff_injected_agents": list(state.kickoff_injected_agents),
            }
        )
    ```

    **Critical W3 details:**
    - `goal: Optional[str] = typer.Option(None, ...)` — NOT `typer.Option("")` and NOT `typer.Option(...)`
    - The validation block immediately after the function header guarantees: if `retry_kickoff=False` AND `goal in (None, "")`, we emit `GOAL_REQUIRED` and exit 1
    - Exit code 1 matches Typer's missing-required default; scripts that just check `$?` see no behavioral change
    - The stderr text changes from Typer's `"Missing option '--goal' / '-g'"` to structured `_sprint_emit_err("GOAL_REQUIRED", ...)`, but this is a tradeoff documented in 13-VALIDATION.md (acceptable per the W3 option (a) "strictly safer" choice)
    - `import Optional` from `typing` if not already imported at the top of cli/commands.py

    Keep the module imports at the top of commands.py unchanged — `SprintConductor`, `SprintAlreadyActiveError`, `SprintNotFoundError` are imported inside the function body to match the existing lazy-import pattern in this file.
  </action>
  <verify>
    <automated>uv run pytest tests/sprint/test_conductor.py tests/test_cli_commands.py -x 2>&1 | tail -15 && uv run clawteam sprint start --help 2>&1 | head -40 && uv run clawteam sprint start --team nonexistent 2>&1 | head -5; echo "exit: $?"</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "retry_kickoff: bool = typer.Option" clawteam/cli/commands.py` returns 1
    - `grep -c "inject_kickoff: bool = typer.Option" clawteam/cli/commands.py` returns 1
    - `grep -c "goal: Optional\\[str\\] = typer.Option(\\s*None" clawteam/cli/commands.py` returns ≥ 1 (W3 fix — Optional with None default)
    - `grep -c "GOAL_REQUIRED" clawteam/cli/commands.py` returns ≥ 1 (manual validation block)
    - `grep -c "SPRINT_ALREADY_ACTIVE" clawteam/cli/commands.py` returns 1
    - `uv run clawteam sprint start --help` output contains `--inject-kickoff` AND `--retry-kickoff`
    - `uv run clawteam sprint start --help` output contains `--no-inject-kickoff`
    - `uv run clawteam sprint start --help` exits 0
    - `uv run clawteam sprint start --team somebody-not-real 2>&1 ; test $? -eq 1` succeeds (W3 BC: exit code 1 when --goal missing, same as HEAD)
    - `uv run pytest tests/sprint/test_conductor.py -x` still exits 0
  </acceptance_criteria>
  <done>CLI exposes both new flags; --goal is BC-safely optional (exit code 1 preserved); SPRINT_ALREADY_ACTIVE error path wired; BC preserved.</done>
</task>

<task type="auto">
  <name>Task 4: Full-suite regression gate for Wave 2</name>
  <read_first>
    - .planning/phases/13-workspace-entry-point/13-VALIDATION.md (Full suite command: `uv run pytest tests/`)
  </read_first>
  <action>
    Run the VALIDATION.md full suite:
    ```bash
    uv run pytest tests/ -x --ignore=tests/integration/test_phase7_ten_sprint_load.py 2>&1 | tail -30
    ```

    (`test_phase7_ten_sprint_load.py` is a v1.0 load test intentionally excluded from quick iteration — match the v1.1 convention.)

    Expected outcomes after Plan 13-02 + Plan 13-03 both land:
    - tests/sprint/test_kickoff.py — GREEN (Plan 13-03 Task 1a byte-equivalence)
    - tests/spawn/test_adapters.py — GREEN (Plan 13-02)
    - tests/sprint/test_conductor.py — GREEN (Plan 13-03)
    - tests/cli/test_open.py — RED still (Plan 13-04 not yet landed — expected)
    - tests/cli/test_commands.py::test_go_help_tagline_is_shortcut — RED still (Plan 13-05 not yet landed — expected)
    - tests/cli/test_commands.py::test_go_runtime_signature_unchanged — GREEN (nothing changed `cmd_go`)
    - tests/integration/test_open_sprint_start_flow.py — xfail (as-designed)
    - Everything else — GREEN (BC check)

    If ANY test OUTSIDE the 4 expected-RED files goes red, that's a BC regression — revisit Task 1-3 to find the leak. If a pydantic v2 deserialization error appears on existing state.json fixtures, verify the `default_factory=list` default is present on `kickoff_injected_agents`.
  </action>
  <verify>
    <automated>uv run pytest tests/ --ignore=tests/integration/test_phase7_ten_sprint_load.py --tb=no -q 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - The full suite run prints a final line showing failures are ONLY in tests/cli/test_open.py (3 tests) and tests/cli/test_commands.py::test_go_help_tagline_is_shortcut (1 test) and tests/integration/test_open_sprint_start_flow.py (2 xfails)
    - Total failures ≤ 4 (the 3 open-command RED + 1 go-tagline RED) and xfails ≤ 2 (integration stubs)
    - Zero NEW failures in any file outside tests/cli/ and tests/integration/test_open_sprint_start_flow.py
  </acceptance_criteria>
  <done>Wave 2 regression gate passes; only expected Plan 13-04/13-05 RED tests remain.</done>
</task>

</tasks>

<verification>
```bash
# Plan 13-03 scoped gate:
uv run pytest tests/sprint/test_kickoff.py tests/sprint/test_conductor.py tests/sprint/test_conductor_concurrency.py tests/test_cli_commands.py -x

# Layering invariant (W2 fix):
grep "from clawteam.cli" clawteam/sprint/conductor.py  # must return 0 lines
grep "from clawteam.cli" clawteam/sprint/kickoff.py    # must return 0 lines

# Wave 2 full regression:
uv run pytest tests/ --ignore=tests/integration/test_phase7_ten_sprint_load.py --tb=no -q
```
</verification>

<success_criteria>
- `clawteam/sprint/kickoff.py` exists with `build_ceo_kickoff_prompt` + `build_specialist_kickoff_prompt` (W2 + W4 fix)
- `SprintState.kickoff_injected_agents` persists successful injections
- `SprintConductor.start_sprint(inject_kickoff=True)` fans kickoff to every pane in tmux_pane_map.json (CEO via build_ceo_kickoff_prompt; specialists via build_specialist_kickoff_prompt → build_agent_prompt — byte-identical to today's go flow per role per W4)
- Collision rejection: SprintAlreadyActiveError raised on second start with status='running'
- `retry_kickoff(sprint_id)` catches up missing agents idempotently
- CLI exposes `--inject-kickoff/--no-inject-kickoff` and `--retry-kickoff`
- `--goal` validation is BC-safe via Optional[str] + manual validation; exit code 1 preserved (W3 fix)
- CEO kickoff synthesis lives in exactly one place (`clawteam/sprint/kickoff.py`) and is called from both launch-time (BC) and sprint-start-time (new)
- Layering invariant verified: `grep "from clawteam.cli" clawteam/sprint/conductor.py` returns 0 lines (W2 fix)
- Byte-equivalence test exists pinning the W4 invariant
- All 4 Plan 13-01 conductor tests go GREEN
- No regression in any other test file
</success_criteria>

<output>
After completion, create `.planning/phases/13-workspace-entry-point/13-03-SUMMARY.md` documenting:
- The new `clawteam/sprint/kickoff.py` module (W2 + W4 fix) — what's in it, why it lives in the sprint layer not cli layer
- The exact kickoff-injection fan-out algorithm (CEO via build_ceo_kickoff_prompt; specialists via build_specialist_kickoff_prompt → build_agent_prompt — byte-parity with today's go flow per role)
- The W3 BC-safe --goal validation: Optional[str] + manual validation, exit code 1 preserved
- Confirmation that `grep "from clawteam.cli" clawteam/sprint/conductor.py` returns 0 lines (layering invariant)
- Pointer for Plan 13-04: "`clawteam open` can now assume `sprint start` owns injection — `open` just needs to create-or-resume the team with clean REPLs. Honor the cmd_open contract at `.planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md`."
- Sprint-state schema delta: `kickoff_injected_agents: list[str]` on SprintState
</output>
