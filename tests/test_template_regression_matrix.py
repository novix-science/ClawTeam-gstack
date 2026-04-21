"""Backwards-compatibility regression matrix for packaged template launches.

Exercises every packaged template's ``clawteam launch <template>`` flow through
a RecordingBackend mock. This covers launch-path compatibility only; prompt and
task-content semantics stay covered by ``tests/test_templates.py``.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from clawteam.cli.commands import app

# If the packaged template set changes, keep this list aligned with
# tests/test_templates.py so structure and launch coverage move together.
TEMPLATE_NAMES: list[str] = [
    "software-dev",
    "hedge-fund",
    "code-review",
    "harness-default",
    "research-paper",
    "strategy-room",
]


class RecordingBackend:
    """Capture spawn calls without starting real subprocesses."""

    def __init__(self):
        self.calls = []

    def spawn(self, **kwargs):
        self.calls.append(kwargs)
        return f"Agent '{kwargs['agent_name']}' spawned"

    def list_running(self):
        return []


@pytest.mark.parametrize("template", TEMPLATE_NAMES)
def test_template_launches_cleanly(template, monkeypatch, tmp_path):
    """Each packaged template must launch cleanly through the CLI."""

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    team_name = f"bc-matrix-{template}"
    result = runner.invoke(
        app,
        [
            "launch",
            template,
            "--team",
            team_name,
            "--goal",
            "BC regression smoke goal",
        ],
        env={
            "HOME": str(tmp_path),
            "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        },
    )

    assert result.exit_code == 0, (
        f"launch {template} failed (exit={result.exit_code}):\n{result.output}"
    )
    assert backend.calls, f"no agents spawned for {template}"

    for call in backend.calls:
        assert call.get("agent_name"), f"{template}: empty agent_name in spawn call"
        assert call.get("team_name") == team_name, (
            f"{template}: team_name mismatch: {call.get('team_name')!r}"
        )
        assert call.get("command"), f"{template}: empty command list in spawn call"
        assert isinstance(call["command"], list), (
            f"{template}: command is not a list: {type(call['command'])!r}"
        )


@pytest.mark.parametrize("template", TEMPLATE_NAMES)
def test_template_spawn_calls_preserve_skip_permissions_flag(
    template, monkeypatch, tmp_path
):
    """Each packaged template should inherit the default skip_permissions flag."""

    monkeypatch.setenv("CLAWTEAM_DATA_DIR", str(tmp_path / ".clawteam"))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    backend = RecordingBackend()
    monkeypatch.setattr("clawteam.spawn.get_backend", lambda _: backend)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "launch",
            template,
            "--team",
            f"skip-perms-{template}",
            "--goal",
            "BC regression - skip_permissions propagation",
        ],
        env={
            "HOME": str(tmp_path),
            "CLAWTEAM_DATA_DIR": str(tmp_path / ".clawteam"),
        },
    )

    assert result.exit_code == 0, (
        f"launch {template} failed for skip_permissions test:\n{result.output}"
    )
    assert backend.calls
    assert all(call.get("skip_permissions") is True for call in backend.calls), (
        f"{template}: one or more spawn calls had skip_permissions != True"
    )


# ===========================================================================
# Phase 3 cross-template isolation
# (Pitfall 14 + QUALITY-14 + success-criteria #2 + #7 + T-07-01 HIGH mitigation)
# ===========================================================================
#
# These tests verify that loading `GstackSprintPlugin` (Phase 3) does NOT
# contaminate any of the 6 pre-Phase-3 templates. Spawning each existing
# template with the plugin loaded must work identically to pre-Phase-3 —
# same phases, same roles, no Reflect-phase `_phase6_pending/` writes,
# no gstack-specific artifacts materialized on disk.
#
# Symmetry with `tests/test_gstack_team_spawn.py`:
# - `test_gstack_team_spawn.py` verifies the positive claim
#   ("spawn gstack -> see gstack").
# - These tests verify the negative claim
#   ("spawn anything-else -> do NOT see gstack").
# A single plan (03-09) owns both files so positive + negative coverage
# evolve together.


# Pre-Phase-3 templates — the 6 templates that must remain backwards-
# compatible under GstackSprintPlugin. Kept separate from TEMPLATE_NAMES
# above (which happens to share the same 6 today) so the launch-path
# suite and the Phase-3 isolation suite can diverge cleanly if future
# templates ship.
EXISTING_TEMPLATES_PHASE3: list[str] = [
    "software-dev",
    "hedge-fund",
    "code-review",
    "harness-default",
    "research-paper",
    "strategy-room",
]

# Threat T-09-02 mitigation: if a future editor removes an entry from the
# list thinking it's redundant, this assertion catches the drop at import
# time so success-criterion #7 coverage can't silently shrink.
assert len(EXISTING_TEMPLATES_PHASE3) == 6, (
    "EXISTING_TEMPLATES_PHASE3 must track all 6 pre-Phase-3 templates "
    "(Phase 3 success criterion #7)"
)


# Canonical 11 gstack role names. Duplicated here (instead of importing
# from the plugin module) so an accidental rename in the plugin is caught
# by the isolation assertions below rather than silently aliasing.
_GSTACK_ROLE_NAMES: set[str] = {
    "pm", "ceo", "eng-mgr", "designer", "dx-lead",
    "engineer", "reviewer", "qa", "security", "shipper", "sre",
}


@pytest.fixture
def gstack_plugin_loaded():
    """Load GstackSprintPlugin globally for the duration of the test.

    Mirrors the plugin-load mechanics PluginManager.discover() performs at
    startup, minus the EvidenceSchemaRegistry global-state touch (other
    test modules already own that registry's lifecycle; adding a second
    registration path here collides with test_gstack_plugin.py's setup).

    The fixture constructs a fresh plugin instance + minimal fake ctx,
    calls on_register, and yields the plugin. Tests drive event handlers
    on the yielded instance directly. No teardown required — plugin is
    garbage-collected at test exit; no global state was mutated.
    """
    from types import SimpleNamespace

    from clawteam.plugins.gstack_sprint_plugin import GstackSprintPlugin

    plugin = GstackSprintPlugin()
    # Minimal fake ctx — bus.subscribe is a no-op for isolation tests since
    # we drive `_on_phase_transition` directly rather than emitting events.
    ctx = SimpleNamespace(
        bus=SimpleNamespace(subscribe=lambda *a, **k: None),
    )
    plugin.on_register(ctx)
    yield plugin


@pytest.mark.parametrize("template", EXISTING_TEMPLATES_PHASE3)
def test_existing_template_spawn_unaffected_by_gstack_plugin(
    template, monkeypatch, tmp_path, gstack_plugin_loaded,
):
    """For each of the 6 existing templates: spawning it with
    GstackSprintPlugin loaded succeeds AND produces a `TeamConfig` with
    the template's own shape (NOT gstack's 11-role roster or 7-phase list).

    This is the Pitfall-14 + QUALITY-14 + success-criterion-#2 backwards-compat
    assertion, parametrized across all 6 pre-Phase-3 templates.

    Uses `team spawn` (03-02 UX-01 subcommand) rather than `launch` because
    the cross-template isolation hinge is `TeamConfig.template` (read by
    `GstackSprintPlugin._on_phase_transition`), and that value is set by
    `team spawn` + `launch` identically. Spawning via `team spawn` avoids
    the backend/subprocess surface entirely.
    """
    from typer.testing import CliRunner

    from clawteam.cli.commands import app
    from clawteam.team.manager import TeamManager

    runner = CliRunner()
    team_name = f"iso-{template}"
    result = runner.invoke(
        app, ["team", "spawn", template, "--name", team_name]
    )
    assert result.exit_code == 0, (
        f"spawning {template!r} with gstack plugin loaded failed:\n"
        f"  exit={result.exit_code}\n"
        f"  stdout={result.output}\n"
        f"  exception={result.exception!r}"
    )

    cfg = TeamManager.get_team(team_name)
    assert cfg is not None, f"TeamConfig not persisted for {template}"

    # 1. TeamConfig.template MUST NOT be "gstack". Existing templates declare
    #    no `role` on their agents, so the filter `[a.role for a in ... if a.role]`
    #    yields [] and `team spawn` / `launch` pass `template=""` into create_team
    #    (this is the cross-template discriminator 03-07 uses).
    assert getattr(cfg, "template", "") != "gstack", (
        f"TeamConfig.template for {template!r} = 'gstack' — plugin "
        f"contaminated a non-gstack spawn (T-07-01 / Pitfall 14 regression)"
    )

    # 2. Member roster MUST NOT be all 11 gstack roles. A partial overlap is
    #    allowed (e.g., some templates legitimately have 'engineer' or 'qa');
    #    a whole-set match signals contamination.
    member_names = {m.name for m in cfg.members}
    assert member_names != _GSTACK_ROLE_NAMES, (
        f"{template!r} materialized all 11 gstack roles — plugin "
        f"contamination"
    )

    # 3. Leader role MUST NOT be "ceo" (gstack's leader). Existing templates
    #    either leave it empty (Pattern 1 strict-additive default) or declare
    #    their own leader role in future.
    assert getattr(cfg, "leader_role", "") != "ceo", (
        f"{template!r} spawned with leader_role='ceo' — plugin contamination"
    )


@pytest.mark.parametrize("template", EXISTING_TEMPLATES_PHASE3)
def test_reflect_phase_does_not_trigger_phase6_pending_write_for_non_gstack(
    template, monkeypatch, tmp_path, gstack_plugin_loaded,
):
    """T-07-01 HIGH severity mitigation anchor (consumption-layer isolation).

    Emitting a Reflect-phase event for a non-gstack team MUST NOT trigger
    `GstackSprintPlugin._write_phase6_pending`. This is the 2nd of the
    2-layer coverage (03-07 unit-level `test_plugin_inert_for_non_gstack_team`
    is the 1st); the integration-level parametrize across all 6 templates
    makes the HIGH severity mitigable.
    """
    from pathlib import Path
    from types import SimpleNamespace

    from typer.testing import CliRunner

    from clawteam.cli.commands import app

    # Real TeamConfig on disk — _resolve_team_template (called by the
    # handler) must see `template=""` for non-gstack templates and bail.
    runner = CliRunner()
    team_name = f"reflect-{template}"
    spawn_result = runner.invoke(
        app, ["team", "spawn", template, "--name", team_name]
    )
    assert spawn_result.exit_code == 0, spawn_result.output

    # Emit the Reflect-phase event through the plugin's handler directly.
    # `to_phase == "reflect"` is the hot path the handler gates on; the
    # template check is the final filter under test.
    event = SimpleNamespace(
        to_phase="reflect",
        team_name=team_name,
        sprint_id="sprint-xyz",
    )
    gstack_plugin_loaded._on_phase_transition(event)

    # The handler MUST NOT have written `_phase6_pending/<sprint>-retro.json`.
    # Accept either "dir never created" or "dir exists but empty"; the only
    # failure mode is "placeholder json materialized".
    import os
    data_dir = Path(os.environ["CLAWTEAM_DATA_DIR"])
    pending_dir = data_dir / "teams" / team_name / "_phase6_pending"
    json_files = (
        list(pending_dir.glob("*.json")) if pending_dir.exists() else []
    )
    assert not json_files, (
        f"T-07-01 HIGH violation: non-gstack template {template!r} "
        f"triggered _phase6_pending write; found {[str(f) for f in json_files]}"
    )


def test_all_six_existing_templates_parse_with_gstack_loaded(gstack_plugin_loaded):
    """Success criterion #7: every existing template's `TemplateDef` loads
    cleanly with `GstackSprintPlugin` imported. No name conflicts, no
    import-time collisions between gstack's 7-phase list and each
    existing template's own phase declaration.
    """
    from clawteam.templates import load_template

    gstack_phases = [
        "think", "plan", "build", "review", "test", "ship", "reflect",
    ]

    for template in EXISTING_TEMPLATES_PHASE3:
        tmpl = load_template(template)
        assert tmpl.name == template
        # Each existing template has its own phase list (may be empty if it
        # relies on the global DEFAULT_PHASES). Phases MUST NOT match all 7
        # gstack phases — that would indicate contamination.
        tmpl_phases = getattr(tmpl, "phases", []) or []
        assert tmpl_phases != gstack_phases, (
            f"{template!r} phases list is identical to gstack's — "
            f"contamination (success criterion #7)"
        )
        # Existing templates shipped without `leader_role` (Pattern 1
        # strict-additive default = ""). If they suddenly declare
        # "ceo" (gstack's leader), that signals cross-template bleed.
        assert getattr(tmpl, "leader_role", "") != "ceo", (
            f"{template!r} declares leader_role='ceo' — template drift"
        )
