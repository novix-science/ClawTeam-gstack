---
phase: 13
plan: 02
type: execute
wave: 2
depends_on: [01]
files_modified:
  - clawteam/spawn/adapters.py
  - clawteam/spawn/tmux_backend.py
  - clawteam/spawn/subprocess_backend.py
  - clawteam/spawn/wsh_backend.py
  - clawteam/spawn/invoke.py
  - clawteam/cli/commands.py
autonomous: true
requirements: [WS-02]
must_haves:
  truths:
    - "NativeCliAdapter.prepare_command accepts a new optional kwarg `goal: str | None = None`"
    - "When `goal is None` and the command is claude-interactive, post_launch_prompt is None — even if a non-empty `prompt` is passed (load-bearing WS-02 invariant)"
    - "When `goal is not None` and the command is claude-interactive with a matching `prompt`, post_launch_prompt == prompt (BC for `go`/`launch --goal X`)"
    - "When `goal` is not passed at all (legacy callers), behavior is identical to HEAD — post_launch_prompt derives from truthy `prompt` as today (BC for every non-WS-02 call site during the transition)"
    - "The three v1.1 prepare_command call sites in clawteam/spawn/*.py (tmux_backend, subprocess_backend, wsh_backend) that spawn agents from launch_team are audited: each now forwards `goal=<launch_team's goal parameter or None>` so WS-02 is load-bearing on the contract rather than on upstream caller hygiene"
    - "All upstream callers of `prepare_command` (audited per checker W1) are documented: each call site either (a) is in the launch path and forwards `goal=` per the contract, or (b) is documented as out-of-scope with rationale"
    - "Plan 13-04's future cmd_open is required by contract to honor the same upstream invariant: when `cmd_open` invokes the launch subprocess, it MUST pass `--goal ''` (or omit `--goal`) so launch_team forwards `goal=None` and the adapter gate fires"
    - "No other adapter gating branch (pi, openclaw, gemini, codex, claude-p-mode) is changed — WS-02 touches only claude-interactive"
  artifacts:
    - path: clawteam/spawn/adapters.py
      provides: "Goal-gated post_launch_prompt assignment for claude interactive"
      contains: "goal: str | None = None"
    - path: clawteam/spawn/tmux_backend.py
      provides: "spawn() threads goal down to prepare_command"
      contains: "goal=goal"
  key_links:
    - from: "clawteam/spawn/adapters.py::NativeCliAdapter.prepare_command"
      to: "clawteam/spawn/tmux_backend.py:255-261 (injection consumer)"
      via: "PreparedCommand.post_launch_prompt field"
      pattern: "goal is None"
    - from: "tests/spawn/test_adapters.py::TestPostLaunchPromptGating"
      to: "clawteam/spawn/adapters.py"
      via: "direct assertion on prepare_command(goal=...) return value"
      pattern: "goal=None"
    - from: "Plan 13-04 future cmd_open"
      to: "launch_team --goal omission"
      via: "contract: cmd_open never passes a non-empty --goal to launch_team"
      pattern: "subprocess.*launch.*--team.*(?!--goal)"
---

<objective>
Make WS-02 load-bearing on the adapter contract by threading a new optional `goal: str | None = None` kwarg through `NativeCliAdapter.prepare_command`. When `goal is None`, `post_launch_prompt` is forced to None for claude-interactive — regardless of whether a non-empty `prompt` was passed. This prevents accidental re-introduction of kickoff-at-launch when `open` (or any future caller) passes a non-empty `prompt` that isn't a sprint goal (e.g., a persona string or resume-hint).

Per 13-CONTEXT "Clean-REPL launch behavior":
- Gating happens at `clawteam/spawn/adapters.py` (per D-04 "gating here is the surgical edit")
- Role system prompts still flow via `--append-system-prompt` (persona ≠ goal)
- At-rest pane shows claude's default `> ` with nothing pre-printed

Per checker W1: the existing `elif prompt:` already short-circuits on falsy values, but that relies on every upstream caller passing `prompt=""` when no goal is given. Threading `goal` explicitly moves the contract from "upstream hygiene" to "adapter guarantee" — future refactors cannot regress it by accident. Task 2 (added per W1) AUDITS the upstream call sites in `cli/commands.py` and codifies the contract that `cmd_open` (Plan 13-04) must honor.

Purpose: Once shipped, `launch` (no `--goal`) and the future `open` command (which calls through to `launch`) both produce clean REPLs. `go` and `launch --goal X` are unaffected (they pass `goal=<value>`, matching their existing `prompt=<value>`).

Output: One new kwarg on `prepare_command`; updated gating logic; audit + update of all 3 in-repo production call sites (tmux_backend, subprocess_backend, wsh_backend) to forward `goal=` from their own `spawn()` signature; a corresponding `goal` kwarg added to the three backends' `spawn()` signatures; `launch_team` in `cli/commands.py` passes `goal=goal or None` (where `goal` is its existing `--goal` option) to `be.spawn`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/phases/13-workspace-entry-point/13-CONTEXT.md
@.planning/phases/13-workspace-entry-point/13-VALIDATION.md
@clawteam/spawn/adapters.py
@clawteam/spawn/tmux_backend.py
@clawteam/spawn/subprocess_backend.py
@clawteam/spawn/wsh_backend.py
@clawteam/spawn/invoke.py
@clawteam/cli/commands.py
@tests/test_adapters.py
@tests/spawn/test_adapters.py

<interfaces>
<!-- Current `prepare_command` signature (adapters.py:34-44): -->
```python
def prepare_command(
    self,
    command: list[str],
    *,
    prompt: str | None = None,
    cwd: str | None = None,
    skip_permissions: bool = False,
    interactive: bool = False,
    agent_name: str | None = None,
    container_env: dict[str, str] | None = None,
) -> PreparedCommand:
```

<!-- Current claude-interactive gate (adapters.py:131-140): -->
```python
elif prompt:
    if interactive and is_claude_command(normalized_command):
        post_launch_prompt = prompt
    elif is_codex_command(normalized_command):
        ...
```

<!-- Production call sites of prepare_command (from grep): -->
<!-- clawteam/spawn/tmux_backend.py:89  — spawn() via self._adapter -->
<!-- clawteam/spawn/tmux_backend.py:108 — resume_prepared (no prompt, so goal=None is fine) -->
<!-- clawteam/spawn/subprocess_backend.py:66 — spawn() via self._adapter -->
<!-- clawteam/spawn/subprocess_backend.py:84 — resume_prepared -->
<!-- clawteam/spawn/wsh_backend.py:260 — spawn() via self._adapter -->
<!-- clawteam/spawn/wsh_backend.py:285 — resume_prepared -->
<!-- clawteam/spawn/invoke.py:72 — _ADAPTER.prepare_command one-shot util -->
<!-- clawteam/cli/commands.py:836 — one-shot adapter invocation (NOT in launch path; separate feature) -->

<!-- backend.spawn() signatures (tmux_backend.py:45-59 is canonical; subprocess + wsh mirror): -->
```python
def spawn(
    self,
    command: list[str],
    agent_name: str, agent_id: str, agent_type: str, team_name: str,
    prompt: str | None = None,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
    skip_permissions: bool = False,
    system_prompt: str | None = None,
    is_leader: bool = False,
    keepalive: bool = False,
    # Plan 13-02 adds: goal: str | None = None
) -> str: ...
```

<!-- launch_team's `be.spawn(...)` call (cli/commands.py:4683-4696) — currently passes prompt=<rendered> where rendered is goal-derived (or persona-like) text. Plan 13-02 adds: goal=(goal or None). -->

<!-- launch_team's own goal Option (cli/commands.py:4409): -->
<!--     goal: str = typer.Option("", "--goal", "-g", ...) -->
<!-- Empty string "" is the "no goal" signal; Plan 13-02 passes `goal=goal or None` so the adapter receives proper None. -->
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add `goal` kwarg to NativeCliAdapter.prepare_command and gate the claude-interactive branch</name>
  <read_first>
    - clawteam/spawn/adapters.py lines 31-146 (NativeCliAdapter.prepare_command — full method)
    - clawteam/spawn/adapters.py line 156 (`is_claude_command` helper)
    - tests/spawn/test_adapters.py (Plan 13-01 — the 4 RED tests we're turning GREEN)
    - tests/test_adapters.py::TestPrepareCommandPrompt lines 81-135 (existing BC tests — must stay GREEN)
  </read_first>
  <behavior>
    - Test 1 (was RED, now GREEN): `adapter.prepare_command(["claude"], prompt="", interactive=True, goal=None)` returns `PreparedCommand(post_launch_prompt=None)`.
    - Test 2 (was RED, now GREEN): `adapter.prepare_command(["claude"], prompt="build CSV CLI", interactive=True, goal=None)` returns `PreparedCommand(post_launch_prompt=None)` (load-bearing — goal gates, not prompt).
    - Test 3 (was RED, now GREEN): `adapter.prepare_command(["claude"], prompt="build CSV CLI", interactive=True, goal="build CSV CLI")` returns `PreparedCommand(post_launch_prompt="build CSV CLI")`.
    - Test 4 (was RED, now GREEN): `adapter.prepare_command(["claude"], prompt="build CSV CLI", interactive=True, goal=None)` returns post_launch_prompt=None — the `test_goal_none_ignores_non_empty_prompt` load-bearing assertion.
    - BC test (was GREEN, stays GREEN): `tests/test_adapters.py::TestPrepareCommandPrompt::test_claude_interactive_gets_post_launch_prompt` — calls `prepare_command(["claude"], prompt="hello", interactive=True)` WITHOUT the new `goal=` kwarg. Since `goal` defaults to None but the old behavior was "truthy prompt → inject", we need a BC shim: when the caller does NOT pass `goal` (sentinel), fall back to the truthy-`prompt` path. This is done via a sentinel default or by distinguishing `goal=None` (explicit) from "not passed".
    - Simpler option: add `goal` as an explicit-None-default kwarg but preserve the old truthy-`prompt` behavior IFF `goal is None AND prompt is truthy AND the caller is a legacy path`. That's ambiguous. A cleaner approach: add `goal` with a SENTINEL default (e.g., a private `_UNSET` object); when sentinel → fall back to `prompt`-based gating; when explicit `None` → force None; when explicit string → use as gate. This preserves BC for legacy call sites while letting new call sites pass `goal=None` explicitly for WS-02.
  </behavior>
  <action>
    Edit `clawteam/spawn/adapters.py`:

    **Edit 1** — add a module-level sentinel above `NativeCliAdapter`:

    ```python
    # Phase 13 WS-02 sentinel: distinguishes "caller did not pass goal"
    # (legacy BC path — fall back to truthy-prompt gating) from "caller
    # explicitly passed goal=None" (new WS-02 contract — force no injection).
    _GOAL_UNSET: str = "__GOAL_UNSET__"
    ```

    **Edit 2** — update `prepare_command` signature (adapters.py:34-44):

    BEFORE:
    ```python
    def prepare_command(
        self,
        command: list[str],
        *,
        prompt: str | None = None,
        cwd: str | None = None,
        skip_permissions: bool = False,
        interactive: bool = False,
        agent_name: str | None = None,
        container_env: dict[str, str] | None = None,
    ) -> PreparedCommand:
    ```

    AFTER:
    ```python
    def prepare_command(
        self,
        command: list[str],
        *,
        prompt: str | None = None,
        cwd: str | None = None,
        skip_permissions: bool = False,
        interactive: bool = False,
        agent_name: str | None = None,
        container_env: dict[str, str] | None = None,
        goal: str | None = _GOAL_UNSET,  # type: ignore[assignment]
    ) -> PreparedCommand:
    ```

    The type annotation is `str | None` to document the intended public contract; the sentinel `_GOAL_UNSET` is the actual runtime default so we can distinguish "not passed" from "explicitly None". (`# type: ignore[assignment]` suppresses the mypy complaint about assigning a string sentinel to a `str | None`-annotated param.)

    **Edit 3** — modify the claude-interactive gate (adapters.py:131-133):

    BEFORE:
    ```python
    elif prompt:
        if interactive and is_claude_command(normalized_command):
            post_launch_prompt = prompt
        elif is_codex_command(normalized_command):
            ...
    ```

    AFTER:
    ```python
    elif prompt:
        if interactive and is_claude_command(normalized_command):
            # WS-02 (Phase 13): post_launch_prompt is injected ONLY when the
            # caller explicitly passed a non-None `goal`. The sentinel default
            # `_GOAL_UNSET` preserves BC for legacy callers that don't know
            # about the kwarg yet (they rely on truthy-`prompt` gating, which
            # is what HEAD does). New callers (launch_team via the 3 backends)
            # pass goal=<launch_team.goal or None>; when --goal is omitted,
            # goal=None short-circuits here, producing a clean REPL.
            if goal is None:
                post_launch_prompt = None
            else:
                post_launch_prompt = prompt
        elif is_codex_command(normalized_command):
            ...
    ```

    Rationale for the sentinel: `test_claude_interactive_gets_post_launch_prompt` in `tests/test_adapters.py:102-107` calls `prepare_command(["claude"], prompt="hello", interactive=True)` without passing `goal=`. That test must stay GREEN. With the sentinel, `goal=_GOAL_UNSET` which is neither None nor a goal string → falls through to the legacy truthy-prompt path → `post_launch_prompt = prompt`. New call sites (Task 2) pass `goal=None` or `goal="some goal"` explicitly, activating the WS-02 gate.

    Do NOT touch the codex, pi, openclaw, gemini, or `claude -p` branches — those have their own prompt-delivery semantics and are out of WS-02 scope.
  </action>
  <verify>
    <automated>uv run pytest tests/spawn/test_adapters.py tests/test_adapters.py -x -v 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "goal: str | None = _GOAL_UNSET" clawteam/spawn/adapters.py` returns 1
    - `grep -c "_GOAL_UNSET" clawteam/spawn/adapters.py` returns ≥ 2 (sentinel definition + kwarg default)
    - `grep -c "WS-02 (Phase 13)" clawteam/spawn/adapters.py` returns 1 (inside the claude-interactive branch)
    - `grep -c "if goal is None:" clawteam/spawn/adapters.py` returns 1 (the load-bearing gate)
    - `uv run pytest tests/spawn/test_adapters.py -x` exits 0 (all 4 WS-02 tests GREEN)
    - `uv run pytest tests/test_adapters.py::TestPrepareCommandPrompt -x` exits 0 (BC preserved via sentinel — all legacy tests pass without being modified)
    - `grep -c "post_launch_prompt = prompt" clawteam/spawn/adapters.py` returns ≥ 2 (claude branch + codex branch — both call sites preserved)
  </acceptance_criteria>
  <done>Adapter has the `goal` kwarg with sentinel default; Plan 13-01's 4 WS-02 tests GREEN; legacy `tests/test_adapters.py` tests stay GREEN via the sentinel BC shim.</done>
</task>

<task type="auto">
  <name>Task 2: Audit upstream `prompt=` callers in cli/commands.py and codify the cmd_open contract (W1)</name>
  <read_first>
    - clawteam/cli/commands.py lines 4406-4416 (launch_team typer signature, including the `--goal` Option default of `""`)
    - clawteam/cli/commands.py lines 4577-4620 (the `rendered = render_task(...)` block + the CEO kickoff synthesis fallback that produces a non-empty `rendered` only when `goal` is truthy AND agent is the CEO leader)
    - clawteam/cli/commands.py lines 4683-4696 (the `be.spawn(prompt=prompt, ...)` call site — this is where `prompt=rendered` flows down into the adapter)
    - clawteam/spawn/prompt.py lines 27-50 (build_agent_prompt — confirms `task=rendered` is the goal-bearing slot; an empty `rendered` for non-CEO agents currently still produces a `prompt` string with the identity block but NO task body)
    - clawteam/cli/commands.py around line 836 (one-shot prepare_command call site; verify it is NOT in the launch path)
    - clawteam/harness/spawner.py (any `backend.spawn(prompt=...)` call sites — verify orchestrator-internal spawns do not leak goal-bearing prompts)
  </read_first>
  <behavior>
    - Every production call site that flows a `prompt=` value into `be.spawn(...)` (and thence into `prepare_command`) is documented: file, line range, what the `prompt` value contains today, and what the contract requires after Plan 13-02.
    - The contract that Plan 13-04's future `cmd_open` MUST honor is written down in this plan and in `cmd_open`'s read_first (Plan 13-04 Task 1a will pull this contract forward via @-reference): when `cmd_open` invokes `clawteam launch ...` as a subprocess, it MUST omit `--goal` (or pass `--goal ""`) so launch_team's typer Option resolves to `""`, which in turn causes `goal=(goal or None) → None` in the be.spawn call, which causes the adapter to gate post_launch_prompt to None. The contract is: `cmd_open never propagates a goal — that's `sprint start`'s job per WS-04`.
    - The audit produces no production code change beyond what Task 1 already required (the sentinel + gate); Task 2 ADDS the explicit forwarding (`goal=goal` in backends, `goal=(goal or None)` in launch_team) AND records the audit in the SUMMARY for posterity.
    - For each `prompt=` caller found, classify: (a) "in launch path, will forward goal=" (most), (b) "out of launch path, leave alone" (one-shot helpers), (c) "needs guard" (goal-bearing prompts produced by some other code path — e.g., harness/spawner.py).
    - Acceptance: `grep -n "prompt=" clawteam/cli/commands.py | grep -v test` returns at most ONE site that passes a non-empty `prompt` when `goal` is not also being forwarded — and that site is documented as "out of launch path" or "intentionally goal-bearing".
  </behavior>
  <action>
    **Step 1 — Run the audit grep:**

    ```bash
    grep -n "be\.spawn\|backend\.spawn\|_backend\.spawn\|\.prepare_command" clawteam/ --include="*.py" -r
    grep -n "prompt=" clawteam/cli/commands.py | grep -v "#"
    ```

    For each hit, classify in the SUMMARY:
    - **In launch path (must forward `goal=`):**
      - `clawteam/cli/commands.py:4683-4696` — launch_team's `be.spawn(prompt=prompt, ...)`. Action: pass `goal=(goal or None)` per Task 3 (was Task 2).
      - `clawteam/spawn/tmux_backend.py:89` — TmuxBackend.spawn's internal `self._adapter.prepare_command(prompt=prompt, ...)`. Action: forward `goal=goal` per Task 3.
      - `clawteam/spawn/subprocess_backend.py:66` — same pattern. Action: forward `goal=goal` per Task 3.
      - `clawteam/spawn/wsh_backend.py:260` — same pattern. Action: forward `goal=goal` per Task 3.
    - **Out of launch path (leave at sentinel default — legacy BC path):**
      - `clawteam/spawn/invoke.py:~72` — one-shot `_ADAPTER.prepare_command(...)` for utility invocations. Document: not in launch path; legacy callers fall through to truthy-prompt gating.
      - `clawteam/cli/commands.py:~836` — verify this is NOT in launch path (read context lines 820-860 to confirm); if it is a one-shot, leave alone.
    - **Resume paths (always pass `goal=None`):**
      - `clawteam/spawn/tmux_backend.py:108` — resume_prepared. Action: `goal=None` (resumes never carry kickoff).
      - `clawteam/spawn/subprocess_backend.py:84` — same.
      - `clawteam/spawn/wsh_backend.py:285` — same.
    - **Harness internal spawns (audit and likely leave alone):**
      - `clawteam/harness/spawner.py:83, 121` — orchestrator-internal harness agents that don't carry user goals. Document: not in launch_team path; sentinel default applies.

    **Step 2 — Codify the cmd_open contract (Plan 13-04 dependency):**

    Add a new file `.planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md` (a small contract document that Plan 13-04 Task 1a will read first):

    ```markdown
    # Plan 13-02 → Plan 13-04 contract: cmd_open MUST NOT propagate a goal

    ## Why this contract exists

    Plan 13-02 makes WS-02 load-bearing on the adapter contract via the new
    `goal: str | None = _GOAL_UNSET` kwarg on `NativeCliAdapter.prepare_command`.
    But the adapter only sees what its callers pass. If `cmd_open` calls
    `clawteam launch <template> --team <name> --goal "..."` (with a non-empty
    `--goal`), launch_team's typer Option will resolve to a truthy string,
    `(goal or None)` will be a truthy string, and the adapter's WS-02 gate
    will FIRE the post_launch_prompt path — defeating WS-01's clean-REPL
    promise.

    ## The contract

    `clawteam open` MUST NEVER propagate a goal to `clawteam launch`. The two
    legitimate forms:

    1. `subprocess.run([..., "launch", template, "--team", name])` — no `--goal`.
       launch_team's Option default kicks in: `goal=""` → `(goal or None) = None`
       → adapter gates → clean REPL. ✅
    2. `subprocess.run([..., "launch", template, "--team", name, "--goal", ""])` —
       explicit empty string. Same downstream behavior. ✅

    Forbidden: any form that passes `--goal "<non-empty string>"`. WS-04 owns
    goal injection — it happens later, in `clawteam sprint start --goal "..."`.

    ## Verification

    From Plan 13-04 Task 1b (the create branch):
    ```python
    launch_proc = subprocess.Popen(
        [sys.executable, "-m", "clawteam", "launch", template, "--team", team_name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    ```

    The argv list MUST NOT contain `"--goal"`. Plan 13-04 Task 2 asserts this
    via monkeypatched `subprocess.Popen` capturing the argv.

    ## Audit grep

    `grep -n "subprocess\\..*launch" clawteam/solo.py` after Plan 13-04 lands
    must show no `--goal` in any cmd_open code path.
    ```

    The contract document is small (≤ 50 lines), lives in the phase dir, and is referenced by Plan 13-04's Task 1a `<read_first>`.

    **Step 3 — Document the audit results in the SUMMARY** for this plan (will be written when the plan executes), so the next planner has a record of every call site classification.
  </action>
  <verify>
    <automated>grep -c "be\\.spawn\\|backend\\.spawn\\|_backend\\.spawn\\|\\.prepare_command" clawteam/ -r --include="*.py" && test -f .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md</automated>
  </verify>
  <acceptance_criteria>
    - The audit grep is run and every `prompt=`-bearing call site is classified into one of the four buckets above
    - `.planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md` exists with the cmd_open-must-not-propagate-goal contract
    - `grep -c "cmd_open MUST NEVER propagate a goal" .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md` returns 1
    - The SUMMARY for Plan 13-02 (written at end of execution) includes the classification table for all call sites
    - No production code is changed by Task 2 itself (this task is audit + contract docs only; the actual forwarding edits are in Task 3)
  </acceptance_criteria>
  <done>All `prompt=` call sites in the spawn/launch path are documented; the cmd_open contract is committed as a phase artifact; Plan 13-04 has a read_first target citing the contract.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Thread `goal` kwarg through all 3 spawn backends and launch_team call site</name>
  <read_first>
    - clawteam/spawn/tmux_backend.py lines 45-100 (spawn signature + prepare_command call)
    - clawteam/spawn/subprocess_backend.py lines 55-90 (same pattern)
    - clawteam/spawn/wsh_backend.py lines 250-290 (same pattern)
    - clawteam/cli/commands.py lines 4406-4416 (launch_team signature with --goal)
    - clawteam/cli/commands.py lines 4683-4696 (be.spawn call in launch_team)
    - clawteam/spawn/invoke.py lines 1-90 (one-shot helper — may also need forwarding if called from launch path; verify via grep)
    - .planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md (the contract Task 2 wrote — Plan 13-04 must honor it; this task makes the contract enforceable by completing the goal-forwarding chain)
  </read_first>
  <behavior>
    - `TmuxBackend.spawn(...)` gains optional kwarg `goal: str | None = None` (default None preserves any caller that doesn't set it).
    - `SubprocessBackend.spawn(...)` gains the same kwarg.
    - `WshBackend.spawn(...)` gains the same kwarg.
    - Each backend's internal `self._adapter.prepare_command(...)` call is updated to forward `goal=goal` so the adapter-level WS-02 gate activates.
    - The resume_prepared call in each backend forwards `goal=None` explicitly — resumes never carry a goal (they reconnect to an existing pane; no kickoff needed).
    - `launch_team` in `cli/commands.py:4683-4696` passes `goal=(goal or None)` to `be.spawn(...)`. `goal` here is the existing `--goal` option at `cli/commands.py:4409` which defaults to `""`; `goal or None` turns empty string into None so the adapter sees the right sentinel.
    - `invoke.py` top-level helper is audited: if its callers never pass a goal-ish prompt for claude-interactive, no change is needed (leave it at the sentinel default). Document the audit result inline.
  </behavior>
  <action>
    **Edit 1 — `clawteam/spawn/tmux_backend.py`:**

    Add `goal: str | None = None` to the `spawn` signature (after `keepalive: bool = False` around line 58):

    ```python
    def spawn(
        self,
        command: list[str],
        agent_name: str, agent_id: str, agent_type: str, team_name: str,
        prompt: str | None = None,
        env: dict[str, str] | None = None,
        cwd: str | None = None,
        skip_permissions: bool = False,
        system_prompt: str | None = None,
        is_leader: bool = False,
        keepalive: bool = False,
        goal: str | None = None,  # Phase 13 WS-02: explicit goal — gates post_launch_prompt
    ) -> str:
    ```

    Update the first `prepare_command` call (line 89) to forward `goal=goal`:

    ```python
    prepared = self._adapter.prepare_command(
        command,
        prompt=prompt,
        cwd=cwd,
        skip_permissions=skip_permissions,
        agent_name=agent_name,
        interactive=True,
        container_env=env_vars,
        goal=goal,  # Phase 13 WS-02: propagate goal; None → clean REPL
    )
    ```

    Update the `resume_prepared` call (line 108) to forward `goal=None`:

    ```python
    resume_prepared = self._adapter.prepare_command(
        resume_base,
        cwd=cwd,
        skip_permissions=skip_permissions,
        agent_name=agent_name,
        interactive=True,
        container_env=env_vars,
        goal=None,  # Phase 13 WS-02: resumes never carry a goal (no kickoff on reconnect)
    )
    ```

    **Edit 2 — `clawteam/spawn/subprocess_backend.py`:**

    Apply the same three changes: add `goal: str | None = None` to `spawn()`, forward `goal=goal` on line 66, forward `goal=None` on line 84 (the resume_prepared call).

    **Edit 3 — `clawteam/spawn/wsh_backend.py`:**

    Apply the same three changes on lines 260 (forward `goal=goal`) and 285 (forward `goal=None`), plus the `spawn()` signature addition.

    **Edit 4 — `clawteam/spawn/invoke.py`:**

    Read the file end-to-end (it's small — <100 lines). If the top-level `invoke` helper is called from any goal-aware code path, forward `goal=`. If it's used only for non-launch contexts (one-shot test invocations, CLI probing), leave the sentinel default in place and add a single-line comment noting that WS-02's gate does not apply to one-shot helper calls. Document the audit outcome explicitly in the summary.

    **Edit 5 — `clawteam/cli/commands.py` launch_team path:**

    At the `be.spawn(...)` call around line 4683-4696, add `goal=(goal or None)` as the last kwarg:

    ```python
    result = be.spawn(
        command=a_cmd,
        agent_name=agent.name,
        agent_id=a_id,
        agent_type=agent.type,
        team_name=t_name,
        prompt=prompt,
        system_prompt=system_prompt,
        env=a_env or None,
        cwd=cwd,
        skip_permissions=skip_permissions,
        is_leader=(agent.name == tmpl.leader.name),
        keepalive=True,
        goal=(goal or None),  # Phase 13 WS-02: None when --goal omitted → clean REPL
    )
    ```

    `goal` here refers to launch_team's own `--goal` typer Option (line 4409, default `""`). `goal or None` converts "" → None so the adapter receives the right sentinel.

    **Edit 6 — Audit `clawteam/cli/commands.py:836`:**

    That site is NOT in the launch_team path (grep + read around line 836 to confirm). If it is unrelated to WS-02, leave it unchanged and note in the summary. If it IS goal-aware, forward `goal=` accordingly.

    **Do NOT edit `clawteam/harness/spawner.py` backend.spawn calls (lines 83, 121)** unless they are in the launch_team path. These are likely orchestrator-internal spawns for harness agents that don't carry user goals; leave them using the default `goal=None`.

    Verify the audit scope:
    ```bash
    grep -rn "be\.spawn\|backend\.spawn\|_backend\.spawn" clawteam/ --include="*.py"
    ```
    For each hit, the executor records in the summary whether it was modified and why/why not.
  </action>
  <verify>
    <automated>uv run pytest tests/spawn/ tests/test_adapters.py tests/ -x --ignore=tests/integration/test_phase7_ten_sprint_load.py 2>&1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "goal: str | None = None" clawteam/spawn/tmux_backend.py` returns ≥ 1 (spawn signature)
    - `grep -c "goal: str | None = None" clawteam/spawn/subprocess_backend.py` returns ≥ 1
    - `grep -c "goal: str | None = None" clawteam/spawn/wsh_backend.py` returns ≥ 1
    - `grep -c "goal=goal" clawteam/spawn/tmux_backend.py` returns ≥ 1 (forwarded to first prepare_command)
    - `grep -c "goal=goal" clawteam/spawn/subprocess_backend.py` returns ≥ 1
    - `grep -c "goal=goal" clawteam/spawn/wsh_backend.py` returns ≥ 1
    - `grep -c "goal=None" clawteam/spawn/tmux_backend.py` returns ≥ 1 (resume_prepared explicit None)
    - `grep -c "goal=(goal or None)" clawteam/cli/commands.py` returns 1 (launch_team call site)
    - `uv run pytest tests/spawn/test_adapters.py tests/test_adapters.py -x` exits 0
    - `uv run pytest tests/integration/test_gstack_sprint_end_to_end.py -x` exits 0 (BC for end-to-end launch path)
    - `uv run pytest tests/ --ignore=tests/integration/test_phase7_ten_sprint_load.py --tb=no -q 2>&1 | tail -5` shows only the expected Plan 13-03/04/05 RED tests failing (not any spawn/backend BC failures)
  </acceptance_criteria>
  <done>All 3 backends thread `goal` through to the adapter; launch_team passes `goal=(goal or None)`; audit of `invoke.py` + `cli/commands.py:836` + `harness/spawner.py` is documented; WS-02 is now load-bearing on the adapter contract.</done>
</task>

<task type="auto">
  <name>Task 4: Run the scoped regression gate and confirm no BC loss</name>
  <read_first>
    - .planning/phases/13-workspace-entry-point/13-VALIDATION.md (Quick run command)
  </read_first>
  <action>
    Run:
    ```bash
    uv run pytest tests/spawn/ tests/test_adapters.py tests/integration/test_gstack_sprint_end_to_end.py -x 2>&1 | tail -20
    ```

    Expected state after Plan 13-02:
    - tests/spawn/test_adapters.py — GREEN (4 WS-02 tests now pass via the new `goal=` kwarg)
    - tests/test_adapters.py — GREEN (sentinel default preserves legacy-caller BC)
    - tests/integration/test_gstack_sprint_end_to_end.py — GREEN (launch_team still works; `go`-with-goal still injects kickoff at launch)
    - tests/cli/test_commands.py — still RED on test_go_help_tagline_is_shortcut (Plan 13-05 will GREEN)
    - tests/cli/test_open.py — still RED (Plan 13-04 will GREEN)
    - tests/sprint/test_conductor.py — still RED (Plan 13-03 will GREEN)

    If tests/spawn/test_adapters.py is NOT GREEN, the adapter edit is wrong — revisit Task 1.

    If tests/test_adapters.py has ANY new failure, WS-02 accidentally regressed an existing BC guarantee — the sentinel logic is wrong; revert and retry.

    If tests/integration/test_gstack_sprint_end_to_end.py regresses, the `goal=(goal or None)` forwarding in launch_team is wrong — check that when `--goal X` is passed, the adapter receives `goal="X"` (not None), and post_launch_prompt still gets set.
  </action>
  <verify>
    <automated>uv run pytest tests/spawn/ tests/test_adapters.py tests/integration/test_gstack_sprint_end_to_end.py -x 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `uv run pytest tests/spawn/test_adapters.py -x` exits 0
    - `uv run pytest tests/test_adapters.py -x` exits 0 (entire module, including BC tests for qwen/opencode/codex/gemini/nanobot/etc.)
    - `uv run pytest tests/integration/test_gstack_sprint_end_to_end.py -x` exits 0 (BC for goal-at-launch path)
    - No new failures in tests outside tests/cli/ and tests/sprint/test_conductor.py (those are owned by later plans)
  </acceptance_criteria>
  <done>Adapter-scoped tests and spawn-backend integration tests GREEN; only Plan 13-03/04/05's RED tests remain.</done>
</task>

</tasks>

<verification>
```bash
uv run pytest tests/spawn/ tests/test_adapters.py tests/integration/test_gstack_sprint_end_to_end.py -x
```
Must exit 0. The remaining RED tests in tests/cli/ and tests/sprint/ are owned by later plans.

Grep sanity:
```bash
grep -n "goal:" clawteam/spawn/adapters.py clawteam/spawn/tmux_backend.py clawteam/spawn/subprocess_backend.py clawteam/spawn/wsh_backend.py
```
Must show the kwarg addition on prepare_command and all 3 backend spawn signatures.
</verification>

<success_criteria>
- `NativeCliAdapter.prepare_command` accepts `goal: str | None = _GOAL_UNSET` (sentinel preserves BC)
- When `goal is None` is explicit, claude-interactive's `post_launch_prompt` is None
- When `goal` is not passed, legacy truthy-prompt behavior preserved
- All 3 backends (tmux, subprocess, wsh) thread `goal` through to `prepare_command`
- launch_team passes `goal=(goal or None)` to `be.spawn(...)`
- Plan 13-01's 4 WS-02 tests GREEN
- No BC regression in tests/test_adapters.py or tests/integration/test_gstack_sprint_end_to_end.py
- Upstream `prompt=` callers audited; cmd_open contract committed as `13-02-CONTRACT-cmd_open.md` (per checker W1)
</success_criteria>

<output>
After completion, create `.planning/phases/13-workspace-entry-point/13-02-SUMMARY.md` documenting:
- The exact diff for adapters.py (sentinel + gate)
- The forwarding edits in the 3 backends (spawn signature + 2 prepare_command call sites each)
- The launch_team edit
- The audit results from Task 2: classification table for every `prompt=` call site (in launch path / out of launch path / resume / harness internal)
- The cmd_open contract artifact: `.planning/phases/13-workspace-entry-point/13-02-CONTRACT-cmd_open.md`
- The audit results for `invoke.py`, `cli/commands.py:836`, and `harness/spawner.py` (modified? why/why not?)
- Confirmation that `tests/spawn/test_adapters.py` and `tests/test_adapters.py` are both GREEN
- Pointer: "Plan 13-03 (sprint-start injection + neutral kickoff module) can now run in parallel with the completed 13-02; Plan 13-04 (open command) depends on 13-02's clean-REPL guarantee AND on the cmd_open contract document Task 2 wrote."
</output>
