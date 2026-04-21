"""/ship skill — 5-step Build-to-Ship pipeline (SKILL-14, Phase 5 Plan 05-04).

Per CONTEXT.md D-05 + RESEARCH.md Pitfall 4: this is NOT a persisted state
machine; it's a linear pipeline of pure-function steps. On failure the user
re-runs, not "resumes from step N". See neighboring skill packages
(office_hours/ design_consultation/ investigate/) for the interactive
state-machine pattern — /ship deliberately does not use it.

Public surface (import on demand so sub-modules remain independently
testable):

- :class:`StepResult`, :func:`sync_main`, :func:`run_tests`,
  :func:`audit_coverage`, :func:`push`, :func:`open_pr`
  — from ``clawteam.templates.gstack.skills.ship.steps``
- :func:`ship_handler`, :func:`gh_available`
  — from ``clawteam.templates.gstack.skills.ship.handler``
"""
