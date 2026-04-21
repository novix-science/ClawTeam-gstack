"""Gstack interactive skill state machines (§04-CONTEXT D-01).

Each subpackage hosts one Phase-4 interactive state machine:

- office_hours/ — pm's 6-forcing-question Socratic loop (Plan 04-07)
- design_consultation/ — designer's 7-dimension rubric dialogue (Plan 04-08)
- investigate/ — reviewer's per-hypothesis iron-law loop with auto-freeze (Plan 04-09)

State persists under ~/.clawteam/teams/<team>/sprints/<id>/skills/<skill>/<role>/state.json
via file_locked + atomic_write_text (Phase 2 convention).
"""
