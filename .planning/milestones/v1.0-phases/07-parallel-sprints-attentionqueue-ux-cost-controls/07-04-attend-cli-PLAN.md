---
phase: 07-parallel-sprints-attentionqueue-ux-cost-controls
plan: 04
type: execute
wave: 3
depends_on: [07-03]
files_modified:
  - clawteam/cli/commands.py
  - clawteam/attention/auto_accept.py
  - tests/attention/test_attend_cli.py
  - tests/attention/test_auto_accept.py
autonomous: true
requirements:
  - INT-04
  - UX-06
  - QUALITY-05
tags:
  - cli
  - typer-subcommand
  - editor-launch
  - auto-accept-reversible

must_haves:
  truths:
    - "clawteam attend typer subcommand group registered via app.add_typer(attend_app, name='attend')"
    - "Default invocation (no subcommand) prints top-N ranked items (default N=10) as a rich table; --json emits JSON"
    - "clawteam attend --summary dispatches to build_digest and renders rows with count / age_bucket / tag"
    - "clawteam attend --auto-accept-reversible previews easy-reversibility items + writes answer.md on confirm with auto_accepted=true frontmatter"
    - "clawteam attend pick opens $EDITOR on the chosen question.md path; on editor exit the answer file presence is re-checked"
    - "Safe when no questions pending: 'No pending attention items.' message; exit code 0"
  artifacts:
    - path: clawteam/cli/commands.py
      provides: "attend subcommand group"
      contains: "attend_app = typer.Typer|app.add_typer(attend_app"
    - path: clawteam/attention/auto_accept.py
      provides: "Auto-accept helper with TTL preview"
      contains: "def preview_auto_accept|def apply_auto_accept"
  key_links:
    - from: clawteam/cli/commands.py
      to: clawteam/attention/queue.py
      via: "attend_root calls AttentionQueue.snapshot()"
      pattern: "AttentionQueue|snapshot"
    - from: clawteam/cli/commands.py
      to: clawteam/attention/digest.py
      via: "--summary dispatches build_digest"
      pattern: "build_digest"
---

<objective>
Wave 3 — `clawteam attend` CLI subcommand: default top-N view + `--summary` digest + `--auto-accept-reversible` preview/apply + `pick` subcommand launching $EDITOR. Covers INT-04, UX-06, QUALITY-05 user-facing behavior.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-CONTEXT.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-RESEARCH.md
@.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-03-attention-queue-PLAN.md

<interfaces>
From clawteam/attention (Plan 07-03):
```python
AttentionQueue.snapshot() -> list[AttentionItem]
AttentionItem  # frozen dataclass
build_digest(items) -> list[dict]
```

Existing CLI pattern (clawteam/cli/commands.py):
```python
config_app = typer.Typer(help="Configuration management")
app.add_typer(config_app, name="config")

@config_app.command("show")
def config_show(): ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: auto_accept helper (preview + apply with TTL)</name>
  <files>
    clawteam/attention/auto_accept.py,
    tests/attention/test_auto_accept.py
  </files>
  <read_first>
    clawteam/attention/queue.py (AttentionItem shape)
  </read_first>
  <behavior>
    - Test 1: `test_preview_filters_easy_only` — mixed items with {easy, medium, hard}; preview returns only easy.
    - Test 2: `test_preview_preserves_priority_order` — multiple easy items; preview output sorted by priority_score desc.
    - Test 3: `test_apply_writes_answer_file` — apply() creates `answers/<qid>.md` with frontmatter `auto_accepted: true`.
    - Test 4: `test_apply_contains_ttl_metadata` — answer.md includes `auto_accepted_at:` + `ttl_minutes: 15` keys.
    - Test 5: `test_apply_body_contains_placeholder` — body contains "Auto-accepted per --auto-accept-reversible".
    - Test 6: `test_apply_idempotent_skips_existing` — apply() on item with existing answer.md returns a 'skipped' status, does not overwrite.
    - Test 7: `test_apply_returns_applied_count` — apply([item1, item2]) returns `{'applied': [...], 'skipped': [...]}` with 2 applied.
  </behavior>
  <action>
**1. `clawteam/attention/auto_accept.py` (NEW, ~120 LOC):**

```python
"""Auto-accept-reversible helper (D-08).

D-08 locks: apply default-accept-with-TTL (15 min) to questions with
`reversibility: easy` frontmatter ONLY. Preview shows exactly what
would auto-accept; apply writes answer.md with `auto_accepted: true`
frontmatter so audit is clean.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from clawteam.attention.queue import AttentionItem

DEFAULT_TTL_MINUTES = 15


def preview_auto_accept(
    items: list[AttentionItem],
) -> list[AttentionItem]:
    """Return items eligible for --auto-accept-reversible, sorted by priority desc.

    Eligible = `reversibility == "easy"`. Medium and hard are always excluded.
    """
    easy = [i for i in items if i.reversibility == "easy"]
    return sorted(easy, key=lambda i: i.priority_score, reverse=True)


def apply_auto_accept(
    items: list[AttentionItem],
    *,
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
    now_fn=None,
) -> dict[str, Any]:
    """Write answer.md for each item with `auto_accepted: true` frontmatter.

    Returns {'applied': [list[qid]], 'skipped': [list[qid]]}. 'skipped'
    contains items whose answer file already exists.
    """
    _now = (now_fn or (lambda: datetime.now(timezone.utc))).__call__
    applied: list[str] = []
    skipped: list[str] = []
    for item in items:
        if item.reversibility != "easy":
            skipped.append(item.question_id)
            continue
        answer_path = item.question_path.parent.parent / "answers" / item.question_path.name
        if answer_path.exists():
            skipped.append(item.question_id)
            continue
        answer_path.parent.mkdir(parents=True, exist_ok=True)
        frontmatter = (
            f"---\n"
            f"auto_accepted: true\n"
            f"auto_accepted_at: {_now().isoformat()}\n"
            f"ttl_minutes: {ttl_minutes}\n"
            f"question_id: {item.question_id}\n"
            f"---\n"
        )
        body = (
            "Auto-accepted per --auto-accept-reversible. "
            "Default option: (first choice in question.md).\n"
            "\n"
            f"This answer was written by `clawteam attend --auto-accept-reversible` "
            f"against a question tagged `reversibility: easy`. TTL = {ttl_minutes} minutes."
        )
        answer_path.write_text(frontmatter + body, encoding="utf-8")
        applied.append(item.question_id)
    return {"applied": applied, "skipped": skipped}


__all__ = ["preview_auto_accept", "apply_auto_accept", "DEFAULT_TTL_MINUTES"]
```

**2. EDIT `clawteam/attention/__init__.py` — add auto_accept exports:**

```python
from clawteam.attention.auto_accept import (
    apply_auto_accept, preview_auto_accept, DEFAULT_TTL_MINUTES,
)

__all__ = [
    # ... existing ...
    "apply_auto_accept", "preview_auto_accept", "DEFAULT_TTL_MINUTES",
]
```

**3. Tests:** `tests/attention/test_auto_accept.py` (~120 LOC):

```python
from pathlib import Path
import pytest
from clawteam.attention.queue import AttentionItem
from clawteam.attention.auto_accept import apply_auto_accept, preview_auto_accept


def _mk_item(tmp_path, qid="q1", reversibility="easy", score=10.0):
    qdir = tmp_path / "teams" / "t" / "sprints" / "s" / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    qpath = qdir / f"{qid}.md"
    qpath.write_text("---\nurgency: high\n---\nbody\n")
    return AttentionItem(
        question_path=qpath, sprint_id="s", team="t", title=qid,
        urgency=2, blocking=False, age_hours=0.5, tags=(),
        reversibility=reversibility, priority_score=score,
    )


def test_preview_easy_only(tmp_path):
    items = [
        _mk_item(tmp_path, "a", "easy"),
        _mk_item(tmp_path, "b", "medium"),
        _mk_item(tmp_path, "c", "hard"),
    ]
    assert {i.question_id for i in preview_auto_accept(items)} == {"a"}


def test_preview_sort_desc(tmp_path):
    items = [
        _mk_item(tmp_path, "lo", "easy", score=5.0),
        _mk_item(tmp_path, "hi", "easy", score=25.0),
    ]
    preview = preview_auto_accept(items)
    assert [i.question_id for i in preview] == ["hi", "lo"]


def test_apply_writes_answer(tmp_path):
    item = _mk_item(tmp_path, "q1", "easy")
    result = apply_auto_accept([item])
    assert result["applied"] == ["q1"]
    answer = item.question_path.parent.parent / "answers" / item.question_path.name
    assert answer.exists()
    txt = answer.read_text()
    assert "auto_accepted: true" in txt
    assert "auto_accepted_at:" in txt
    assert "ttl_minutes: 15" in txt


def test_apply_body_contains_placeholder(tmp_path):
    item = _mk_item(tmp_path, "q1", "easy")
    apply_auto_accept([item])
    answer = item.question_path.parent.parent / "answers" / item.question_path.name
    assert "Auto-accepted per --auto-accept-reversible" in answer.read_text()


def test_apply_idempotent_skips_existing(tmp_path):
    item = _mk_item(tmp_path, "q1", "easy")
    apply_auto_accept([item])
    result2 = apply_auto_accept([item])
    assert result2["applied"] == []
    assert result2["skipped"] == ["q1"]


def test_apply_mixed(tmp_path):
    easy = _mk_item(tmp_path, "easy1", "easy")
    hard = _mk_item(tmp_path, "hard1", "hard")
    result = apply_auto_accept([easy, hard])
    assert result["applied"] == ["easy1"]
    assert result["skipped"] == ["hard1"]
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/attention/test_auto_accept.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "def preview_auto_accept" clawteam/attention/auto_accept.py` succeeds.
    - `grep -q "def apply_auto_accept" clawteam/attention/auto_accept.py` succeeds.
    - `pytest tests/attention/test_auto_accept.py -q` reports 6+ passed.
  </acceptance_criteria>
  <done>Auto-accept helper lives; Task 2 CLI wires --auto-accept-reversible to these functions.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: clawteam attend CLI subcommand (root + summary + auto-accept-reversible + pick)</name>
  <files>
    clawteam/cli/commands.py,
    tests/attention/test_attend_cli.py
  </files>
  <read_first>
    clawteam/cli/commands.py (existing typer.Typer subcommand pattern at lines 248-341 for config_app; team_app at 1272+),
    clawteam/attention (Plan 07-03 + Task 1 output)
  </read_first>
  <behavior>
    - Test 1: `test_attend_no_questions_exits_zero` — data_dir empty; `clawteam attend` prints "No pending" message; exit code 0.
    - Test 2: `test_attend_lists_top_n` — 3 questions; `clawteam attend -n 2` prints 2 rows; exit code 0; both highest-priority.
    - Test 3: `test_attend_json` — `clawteam attend --json` emits a JSON array with expected keys (`sprint_id`, `question_id`, `priority_score`, ...).
    - Test 4: `test_attend_summary` — `clawteam attend --summary` renders cluster count and highest_priority; JSON mode emits digest list.
    - Test 5: `test_attend_auto_accept_preview_requires_confirm` — `--auto-accept-reversible` WITHOUT `--yes` prints preview only; no answer.md written.
    - Test 6: `test_attend_auto_accept_with_yes_applies` — `--auto-accept-reversible --yes` writes answer.md for easy items.
    - Test 7: `test_attend_pick_calls_editor` — monkeypatch `subprocess.run` to capture args; `clawteam attend pick <qid>` invokes $EDITOR with the question path.
  </behavior>
  <action>
**1. `clawteam/cli/commands.py` — APPEND after cost_app block (around line 2814) the new `attend_app`:**

```python
# ============================================================================
# Phase 7 Plan 07-04: Attention Queue Commands (INT-04, UX-06, QUALITY-05)
# ============================================================================

attend_app = typer.Typer(help="Cross-sprint attention queue")
app.add_typer(attend_app, name="attend")


def _render_attend_items_human(items: list) -> None:
    if not items:
        console.print("[dim]No pending attention items.[/dim]")
        return
    table = Table(title=f"Top {len(items)} Pending Questions")
    table.add_column("#", style="dim", width=3)
    table.add_column("Priority", justify="right", style="green")
    table.add_column("Urg", width=4)
    table.add_column("Team", style="cyan")
    table.add_column("Sprint", style="magenta")
    table.add_column("Age", justify="right")
    table.add_column("Rev", width=6)
    table.add_column("Title")
    urgency_labels = {3: "CRIT", 2: "HIGH", 1: "norm", 0: "low"}
    for i, item in enumerate(items, start=1):
        age_s = f"{item.age_hours:.1f}h"
        u_lbl = urgency_labels.get(item.urgency, "?")
        u_style = {"CRIT": "bold red", "HIGH": "yellow"}.get(u_lbl, "")
        table.add_row(
            str(i),
            f"{item.priority_score:.1f}",
            f"[{u_style}]{u_lbl}[/{u_style}]" if u_style else u_lbl,
            item.team,
            item.sprint_id[:8],
            age_s,
            item.reversibility,
            item.title[:60],
        )
    console.print(table)


def _render_digest_human(digest: list[dict]) -> None:
    if not digest:
        console.print("[dim]No pending attention items.[/dim]")
        return
    table = Table(title="Attention Digest")
    table.add_column("Sprint", style="magenta")
    table.add_column("Tag", style="cyan")
    table.add_column("Age", style="dim")
    table.add_column("Count", justify="right")
    table.add_column("Top priority", justify="right", style="green")
    table.add_column("Representative title")
    for row in digest:
        table.add_row(
            row["sprint_id"][:8],
            row["tag"],
            row["age_bucket"],
            str(row["count"]),
            f"{row['highest_priority']:.1f}",
            row["representative_title"][:60],
        )
    console.print(table)


@attend_app.callback(invoke_without_command=True)
def attend_root(
    ctx: typer.Context,
    top_n: int = typer.Option(10, "--top", "-n", help="Number of top items to display"),
    summary: bool = typer.Option(False, "--summary", help="Digest view (group by sprint/tag/age)"),
    auto_accept_reversible: bool = typer.Option(
        False, "--auto-accept-reversible",
        help="Preview + apply auto-accept to reversibility=easy questions",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip --auto-accept-reversible preview confirm"),
):
    """Show the top-N pending questions across all teams' sprints.

    Default (no flags): priority-sorted table, top 10.
    --summary: digest view (grouped by sprint + tag cluster + age bucket).
    --auto-accept-reversible: preview easy-reversibility items; --yes to apply.
    """
    if ctx.invoked_subcommand is not None:
        return
    from clawteam.attention.queue import AttentionQueue
    from clawteam.attention.digest import build_digest
    from clawteam.attention.auto_accept import preview_auto_accept, apply_auto_accept

    queue = AttentionQueue()  # CLAWTEAM_DATA_DIR-respecting
    items = queue.snapshot(limit=top_n if not (summary or auto_accept_reversible) else None)

    if auto_accept_reversible:
        candidates = preview_auto_accept(items)
        data = {
            "preview_count": len(candidates),
            "items": [
                {
                    "question_id": c.question_id,
                    "sprint_id": c.sprint_id,
                    "team": c.team,
                    "title": c.title,
                    "priority_score": c.priority_score,
                }
                for c in candidates
            ],
        }
        def _human(d):
            console.print(
                f"[yellow]Preview — {len(candidates)} easy-reversibility question(s) would auto-accept:[/yellow]"
            )
            for c in candidates:
                console.print(f"  • {c.team}/{c.sprint_id[:8]} — {c.title} (priority={c.priority_score:.1f})")
            if not yes and candidates:
                console.print(
                    "\nRerun with [bold]--yes[/bold] to apply. TTL = 15 min per answer."
                )
            elif yes and candidates:
                result = apply_auto_accept(candidates)
                console.print(f"[green]OK[/green] applied={len(result['applied'])} skipped={len(result['skipped'])}")
        if yes and candidates:
            applied_result = apply_auto_accept(candidates)
            data["applied"] = applied_result["applied"]
            data["skipped"] = applied_result["skipped"]
        _output(data, _human)
        return

    if summary:
        digest = build_digest(items)
        data = {"digest": digest}
        _output(data, lambda d: _render_digest_human(d["digest"]))
        return

    # Default: top-N table.
    data = {
        "items": [
            {
                "question_id": i.question_id,
                "sprint_id": i.sprint_id,
                "team": i.team,
                "title": i.title,
                "urgency": i.urgency,
                "blocking": i.blocking,
                "age_hours": i.age_hours,
                "tags": list(i.tags),
                "reversibility": i.reversibility,
                "priority_score": i.priority_score,
            }
            for i in items
        ],
    }
    _output(data, lambda d: _render_attend_items_human(items))


@attend_app.command("pick")
def attend_pick(
    question_id: str = typer.Argument(..., help="Question id (stem of question.md) to open"),
    team: Optional[str] = typer.Option(None, "--team", help="Team filter (unambiguous if omitted)"),
):
    """Open the chosen question.md in $EDITOR; on save, gate unblocks next time it's checked."""
    from clawteam.attention.queue import AttentionQueue

    queue = AttentionQueue()
    items = queue.snapshot()
    matches = [i for i in items if i.question_id == question_id and (team is None or i.team == team)]
    if not matches:
        _output(
            {"error": f"No pending question matches {question_id!r}"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(1)
    if len(matches) > 1:
        _output(
            {
                "error": "Ambiguous question_id; pass --team to disambiguate",
                "candidates": [{"team": m.team, "sprint_id": m.sprint_id} for m in matches],
            },
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(2)
    item = matches[0]
    editor = os.environ.get("EDITOR", "vi")
    try:
        subprocess.run([editor, str(item.question_path)], check=False)
    except FileNotFoundError:
        _output(
            {"error": f"Editor not found: {editor}"},
            lambda d: console.print(f"[red]{d['error']}[/red]"),
        )
        raise typer.Exit(3)
    # After editor exits, check if the user created the answer file.
    answer_path = item.question_path.parent.parent / "answers" / item.question_path.name
    _output(
        {
            "question_id": question_id,
            "team": item.team,
            "sprint_id": item.sprint_id,
            "answered": answer_path.exists(),
            "answer_path": str(answer_path) if answer_path.exists() else None,
        },
        lambda d: console.print(
            f"[green]OK[/green] answer present at {d['answer_path']}"
            if d["answered"]
            else f"[yellow]No answer file yet — write it to {answer_path} to unblock.[/yellow]"
        ),
    )
```

Note: `subprocess`, `os`, `Optional` are already imported at the top of commands.py. `Table`, `console`, `Row`-like helpers already present.

**2. `tests/attention/test_attend_cli.py` (~230 LOC):**

```python
import json
import os
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app


def _write_question(data_dir, team, sprint, qid, **kwargs):
    qdir = data_dir / "teams" / team / "sprints" / sprint / "questions"
    qdir.mkdir(parents=True, exist_ok=True)
    urgency = kwargs.get("urgency", "normal")
    reversibility = kwargs.get("reversibility", "medium")
    title = kwargs.get("title", qid)
    (qdir / f"{qid}.md").write_text(
        f"---\nurgency: {urgency}\nblocking: false\ntags: []\n"
        f"reversibility: {reversibility}\ntitle: {title}\n---\nbody\n"
    )


@pytest.fixture
def runner(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path))
    return CliRunner(), tmp_path


def test_attend_no_questions(runner):
    r, _ = runner
    result = r.invoke(app, ["attend"])
    assert result.exit_code == 0
    assert "No pending" in result.stdout


def test_attend_top_n(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="low")
    _write_question(tmp, "t", "s", "q2", urgency="critical")
    _write_question(tmp, "t", "s", "q3", urgency="high")
    result = r.invoke(app, ["attend", "-n", "2"])
    assert result.exit_code == 0
    # Critical + high should be in the top 2 output.
    assert "q2" in result.stdout or "critical" in result.stdout.lower()


def test_attend_json(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="high")
    result = r.invoke(app, ["--json", "attend"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "items" in data
    assert data["items"][0]["question_id"] == "q1"


def test_attend_summary(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="high")
    _write_question(tmp, "t", "s", "q2", urgency="normal")
    result = r.invoke(app, ["--json", "attend", "--summary"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "digest" in data


def test_attend_auto_accept_preview_only(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="normal", reversibility="easy")
    result = r.invoke(app, ["attend", "--auto-accept-reversible"])
    assert result.exit_code == 0
    # No answer file written (no --yes).
    answer = tmp / "teams" / "t" / "sprints" / "s" / "answers" / "q1.md"
    assert not answer.exists()


def test_attend_auto_accept_yes_applies(runner):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", reversibility="easy")
    _write_question(tmp, "t", "s", "q2", reversibility="hard")
    result = r.invoke(app, ["attend", "--auto-accept-reversible", "--yes"])
    assert result.exit_code == 0
    assert (tmp / "teams" / "t" / "sprints" / "s" / "answers" / "q1.md").exists()
    assert not (tmp / "teams" / "t" / "sprints" / "s" / "answers" / "q2.md").exists()


def test_attend_pick_calls_editor(runner, monkeypatch):
    r, tmp = runner
    _write_question(tmp, "t", "s", "q1", urgency="high")
    captured = {}

    def fake_run(cmd, check=False, **kw):
        captured["cmd"] = cmd
        class R: returncode = 0
        return R()

    monkeypatch.setenv("EDITOR", "my-ed")
    monkeypatch.setattr(subprocess, "run", fake_run)
    result = r.invoke(app, ["attend", "pick", "q1"])
    assert result.exit_code == 0
    assert captured["cmd"][0] == "my-ed"
    assert "q1.md" in str(captured["cmd"][1])


def test_attend_pick_unknown_id(runner):
    r, _ = runner
    result = r.invoke(app, ["attend", "pick", "nonexistent"])
    assert result.exit_code == 1
```
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && pytest tests/attention/test_attend_cli.py tests/test_cli_commands.py -x -q</automated>
  </verify>
  <acceptance_criteria>
    - `grep -q "attend_app = typer.Typer" clawteam/cli/commands.py` succeeds.
    - `grep -q 'app.add_typer(attend_app, name="attend")' clawteam/cli/commands.py` succeeds.
    - `clawteam attend --help` (from pytest CliRunner) shows `--summary` and `--auto-accept-reversible` options.
    - `pytest tests/attention/test_attend_cli.py -q` reports 8 passed.
    - BC: `pytest tests/test_cli_commands.py -q` still green.
  </acceptance_criteria>
  <done>`clawteam attend` command group live; INT-04/UX-06/QUALITY-05 user-facing surface shipped.</done>
</task>

</tasks>

<verification>
1. `pytest tests/attention/ tests/test_cli_commands.py -q` — all green.
2. Manual smoke: `clawteam attend --help` shows the subcommand; `clawteam attend` returns exit 0 with "No pending" when empty.
</verification>

<success_criteria>
- Tasks 1-2 acceptance met.
- Three flavors of attend usage (default, --summary, --auto-accept-reversible) all work and emit correct JSON + human output.
- `clawteam attend pick <qid>` launches $EDITOR.
</success_criteria>

<output>
After completion, create `.planning/phases/07-parallel-sprints-attentionqueue-ux-cost-controls/07-04-SUMMARY.md`.
</output>
