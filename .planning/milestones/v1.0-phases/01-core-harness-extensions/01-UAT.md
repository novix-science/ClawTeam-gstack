---
status: complete
phase: 01-core-harness-extensions
source:
  - 01-01-SUMMARY.md
  - 01-02-SUMMARY.md
  - 01-03-SUMMARY.md
  - 01-04-SUMMARY.md
  - 01-05-SUMMARY.md
started: 2026-04-20T00:00:00Z
updated: 2026-04-20T12:56:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Existing template BC — software-dev still spawns
expected: |
  Run from repo root:
    .venv-sys/bin/clawteam launch software-dev --team uat-bc-smoke --goal "UAT BC check" &
    sleep 10
    .venv-sys/bin/clawteam team status uat-bc-smoke
  Expected: `team status` prints a table with 5 members (tech-lead, backend-dev,
  frontend-dev, qa-engineer, devops). Cleanup with:
    .venv-sys/bin/clawteam team cleanup uat-bc-smoke --force
result: pass

### 2. SprintState round-trip on disk
expected: |
  Run from repo root:
    uv run python -c "
    from clawteam.sprint.state import SprintState
    s = SprintState(goal='uat-check', team='uat-ss', current_phase='discuss',
                    created_at='2026-04-20T00:00:00Z')
    path = s.save(team='uat-ss')
    print('saved to:', path)
    loaded = SprintState.load(team='uat-ss', sprint_id=s.sprint_id)
    assert loaded.goal == 'uat-check'
    print('round-trip OK')
    "
  Expected: prints a path under ~/.clawteam/teams/uat-ss/sprints/<8hex>/state.json
  then 'round-trip OK'. No exception.

result: pass

### 3. InteractionGate blocks on unanswered question, unblocks after answer
expected: |
  Run from repo root:
    uv run python -c "
    import os, tempfile
    from pathlib import Path
    tmp = tempfile.mkdtemp()
    os.environ['CLAWTEAM_DATA_DIR'] = tmp
    from clawteam.sprint.state import SprintState
    from clawteam.harness.interaction_gate import InteractionGate

    s = SprintState(goal='g', team='uat-gate', sprint_id='aabbccdd',
                    current_phase='plan', created_at='2026-04-20T00:00:00Z')
    s.save(team='uat-gate')
    qdir = Path(tmp) / 'teams' / 'uat-gate' / 'sprints' / 'aabbccdd' / 'questions'
    adir = Path(tmp) / 'teams' / 'uat-gate' / 'sprints' / 'aabbccdd' / 'answers'
    qdir.mkdir(parents=True); adir.mkdir(parents=True)
    (qdir / 'q1.md').write_text('?')

    g = InteractionGate()
    p, r = g.check(s); print('unanswered:', p, '|', r)
    (adir / 'q1.md').write_text('answered')
    p, r = g.check(s); print('answered:', p, '|', r)
    "
  Expected:
    unanswered: False | Open questions: q1
    answered: True |

result: pass

### 4. Question/Answer markdown round-trip
expected: |
  Run from repo root:
    uv run python -c "
    from clawteam.sprint.qa import Question, Choice
    q = Question(id='qabc1234', slug='pick-stack', type='multi-choice',
                 created_at='2026-04-20T00:00:00Z', sprint_id='sprint01',
                 phase='plan', author='pm',
                 choices=[Choice(id='a', label='React'), Choice(id='b', label='Vue')])
    md = q.to_markdown(body='Which framework?\n')
    q2 = Question.from_markdown(md)
    assert q2.id == q.id and q2.type == 'multi-choice' and len(q2.choices) == 2
    print('ok — round-trip preserved', len(q2.choices), 'choices')
    "
  Expected: prints 'ok — round-trip preserved 2 choices'. No exception.

result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
