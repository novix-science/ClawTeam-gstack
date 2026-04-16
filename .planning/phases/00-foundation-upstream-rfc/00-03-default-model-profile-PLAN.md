---
phase: 00-foundation-upstream-rfc
plan: 03
type: execute
wave: 1
depends_on: []
files_modified:
  - clawteam/config.py
  - tests/test_config.py
autonomous: true
requirements:
  - TEAM-06
tags: [config, pydantic, model-profile, cost-prevention]

must_haves:
  truths:
    - "ClawTeamConfig().default_model_profile equals the string 'balanced' when no value is supplied."
    - "ClawTeamConfig.model_fields contains 'default_model_profile' so downstream code can enumerate it."
    - "Deserialising an existing config.json that lacks 'default_model_profile' produces a model with default_model_profile='balanced' (additive-only, BC guaranteed)."
    - "get_effective('default_model_profile') returns ('balanced', 'default') when nothing is set — NO env-var override path (per ROADMAP Phase 0 success criterion 5: opt-in only via --model-profile CLI flag or config file, never via env var)."
  artifacts:
    - path: "clawteam/config.py"
      provides: "ClawTeamConfig.default_model_profile = 'balanced' field — scaffold only, NO env_map entry (ROADMAP criterion 5)"
      contains: "default_model_profile: str = \"balanced\""
    - path: "tests/test_config.py"
      provides: "Assertions that (a) default is 'balanced', (b) missing-field BC load produces 'balanced', (c) CLAWTEAM_DEFAULT_MODEL_PROFILE env var is IGNORED (regression guard against Pitfall #12 silent quality promotion)"
      contains: "default_model_profile"
  key_links:
    - from: "clawteam/config.py::ClawTeamConfig.default_model_profile"
      to: "clawteam/config.py::get_effective"
      via: "get_effective reads the field from config file only — env_map deliberately does NOT contain default_model_profile"
      pattern: "default_model_profile"
---

<objective>
Scaffold the default model profile field on `ClawTeamConfig` (TEAM-06 + Pitfall #12 cost-blowup prevention): a single pydantic v2 field `default_model_profile: str = "balanced"` added adjacent to the existing `default_profile` at `clawteam/config.py:54`. Deliberately NO env_map entry — per ROADMAP Phase 0 success criterion 5, opt-in to a non-default profile is restricted to `--model-profile` CLI flag or config file, never env var. This prevents the "silent quality promotion via an exported `CLAWTEAM_DEFAULT_MODEL_PROFILE=quality` shell" failure mode (Pitfall #12).

Purpose: Closes TEAM-06 (gstack.toml additive — existing templates unchanged because they never read this field; Phase 3's `gstack.toml` loader will). Establishes the resolution PATH; the actual profile-to-model mapping (Opus/Sonnet/Haiku per role) ships in Phase 3 (`gstack.toml`) and Phase 7 (cost observability with fallback ladder per QUALITY-12).

Output:
- Modified `clawteam/config.py`: one new pydantic field. NO env_map edit (deliberate divergence from `default_profile` pattern — see ROADMAP criterion 5).
- Extended `tests/test_config.py`: assertions verifying default value, backward-compat load, and a REGRESSION GUARD that `CLAWTEAM_DEFAULT_MODEL_PROFILE` env var is ignored by `get_effective`.

Scope boundary (per RESEARCH.md A1): Phase 0 does NOT ship the balanced/quality/budget → actual model-name mapping. That's Phase 3 + Phase 7 work. This plan only establishes the scaffold field.

Scope boundary (per PATTERNS.md §config.py): Do NOT add `Literal["balanced", "quality", "budget"]` validation. PROJECT.md defers the 3-value restriction to later phases; any string is accepted here, mirroring how `workspace: str = "auto"` accepts any string today. The three canonical values (per REQUIREMENTS.md TEAM-05) are **balanced**, **quality**, **budget** — NOT "cost".
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/00-foundation-upstream-rfc/00-RESEARCH.md
@.planning/phases/00-foundation-upstream-rfc/00-PATTERNS.md
@.planning/codebase/CONVENTIONS.md
@clawteam/config.py
@tests/test_config.py

<interfaces>
<!-- Exact current state of ClawTeamConfig + get_effective. -->

From clawteam/config.py:50-69 (ClawTeamConfig pydantic v2 BaseModel — add the new field immediately below default_profile at line 54):
```python
class ClawTeamConfig(BaseModel):
    data_dir: str = ""
    user: str = ""
    default_team: str = ""
    default_profile: str = ""                                # ← line 54; insert new field below
    transport: str = ""
    task_store: str = ""  # "file" (default) — extensible for redis/sql later
    workspace: str = "auto"  # "auto" | "always" | "never" | ""
    default_backend: str = "tmux"  # "tmux" | "subprocess"
    skip_permissions: bool = True  # pass --dangerously-skip-permissions to claude
    timezone: str = "UTC"  # display timezone for human-readable timestamps
    gource_path: str = ""  # custom path to gource binary (auto-detected if empty)
    gource_resolution: str = "1280x720"  # default viewport resolution
    gource_seconds_per_day: float = 0.5  # animation speed
    profiles: dict[str, AgentProfile] = Field(default_factory=dict)
    presets: dict[str, AgentPreset] = Field(default_factory=dict)
    spawn_prompt_delay: float = 2.0  # fallback wait (seconds) if TUI ready-detection times out
    spawn_ready_timeout: float = 30.0  # max seconds to poll for TUI readiness before fallback
    hooks: list[HookDef] = Field(default_factory=list)
    plugins: list[str] = Field(default_factory=list)
```

From clawteam/config.py:98-134 (get_effective: env_map contains the env-var overrides; add new entry adjacent to default_profile):
```python
def get_effective(key: str) -> tuple[str, str]:
    """Get effective value for a config key. Returns (value, source)."""
    env_map = {
        "data_dir": "CLAWTEAM_DATA_DIR",
        "user": "CLAWTEAM_USER",
        "default_team": "CLAWTEAM_TEAM_NAME",
        "default_profile": "CLAWTEAM_DEFAULT_PROFILE",       # ← line 107; insert new entry below
        "transport": "CLAWTEAM_TRANSPORT",
        ...
    }
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add default_model_profile field and env_map entry to ClawTeamConfig</name>
  <files>clawteam/config.py</files>
  <behavior>
    - ClawTeamConfig has a new field `default_model_profile: str = "balanced"` adjacent to `default_profile` (line 54).
    - The env_map in get_effective has a new entry `"default_model_profile": "CLAWTEAM_DEFAULT_MODEL_PROFILE"` adjacent to the existing `"default_profile": "CLAWTEAM_DEFAULT_PROFILE"` entry.
    - ClawTeamConfig() — no args — returns model with default_model_profile == "balanced".
    - Deserialising an existing config.json that doesn't have the new key loads successfully with default_model_profile == "balanced" (pydantic v2 missing-optional default behavior).
    - Serialising a default-constructed config and re-loading round-trips default_model_profile correctly.
  </behavior>
  <action>
    Modify `clawteam/config.py` with ONE additive edit (pydantic field only; env_map is deliberately NOT touched).

    ### Edit 1 — Insert new pydantic field at line 55 (immediately below `default_profile` at line 54)

    Current (lines 53-55):
    ```python
        default_team: str = ""
        default_profile: str = ""
        transport: str = ""
    ```

    Change to:
    ```python
        default_team: str = ""
        default_profile: str = ""
        default_model_profile: str = "balanced"  # model tier preset (balanced | quality | budget); NEVER silently 'quality'
        transport: str = ""
    ```

    Rules (per PATTERNS.md §clawteam/config.py, but renamed tier value to align with REQUIREMENTS.md TEAM-05):
    - Placement: immediately below `default_profile` at line 54 to keep related fields adjacent.
    - Type: `str` (not `Literal["balanced","quality","budget"]`). PROJECT.md defers value-validation to later phases; this field is the RESOLUTION PATH, not the constraint.
    - Default: `"balanced"` — MANDATORY per ROADMAP Phase 0 success criterion 5 + Pitfall #12. Never `"quality"`.
    - Trailing comment documents the three canonical tier values per REQUIREMENTS.md TEAM-05 (**balanced | quality | budget**). NOT "cost" — the user-facing flag is `--model-profile balanced|quality|budget`.
    - Simple scalar default — immediate value `= "balanced"`, NOT `Field(default_factory=...)`. (Sibling scalars at 51-66 all use direct defaults; only `profiles`, `presets`, `hooks`, `plugins` use `Field(default_factory=...)` because they're mutable containers.)

    ### Edit 2 — (INTENTIONALLY OMITTED) NO env_map entry

    Do NOT add `"default_model_profile": "CLAWTEAM_DEFAULT_MODEL_PROFILE"` to the `env_map` inside `get_effective`.

    Rationale (ROADMAP Phase 0 success criterion 5 is the source of truth):
    > "the template-loading code path rejects `quality` as a silent default (must be explicitly opted into via `--model-profile quality` or config)"

    Env-var opt-in is explicitly excluded from that list. Wiring `CLAWTEAM_DEFAULT_MODEL_PROFILE` into `env_map` would enable the exact "silent quality promotion via exported shell var" failure mode Pitfall #12 forbids. The scaffold deliberately diverges from the `default_profile` pattern on this point.

    RESEARCH.md line 711 reached the same conclusion: *"Keep `default_model_profile` OUT of the env-var map in `get_effective()`. Resolution order: CLI flag → template field → config file → hard-coded 'balanced'. No env-var shortcut."*

    PATTERNS.md originally recommended parity with `default_profile` (adding the env_map line); that recommendation is **superseded** by ROADMAP criterion 5 for this field. A separate pass updates PATTERNS.md to reflect this.

    ### Edit 3 — Docstring update on get_effective (lines 99-101)

    Current:
    ```python
    def get_effective(key: str) -> tuple[str, str]:
        """Get effective value for a config key. Returns (value, source).

        Priority: env var > config file > default.
        """
    ```

    Change to:
    ```python
    def get_effective(key: str) -> tuple[str, str]:
        """Get effective value for a config key. Returns (value, source).

        Priority: env var > config file > default.

        Note: ``default_model_profile`` is deliberately NOT in ``env_map`` — per the
        Phase 0 scaffold contract (ROADMAP success criterion 5), opt-in to a non-default
        profile is restricted to the ``--model-profile`` CLI flag or the config file.
        Calling ``get_effective("default_model_profile")`` returns the value from the
        config file if present, else the pydantic default ``"balanced"`` — env vars are
        ignored for this key to prevent Pitfall #12 silent quality promotion.
        """
    ```

    This documents the intent both for Phase 3 implementers and for anyone auditing why this one key diverges from the `default_profile` pattern.

    ### What NOT to do

    - Do NOT add `Literal["balanced","quality","budget"]` to the field type (PATTERNS.md §config.py "What NOT to add yet").
    - Do NOT add `default_model_profile` to the `env_map` in `get_effective`. ROADMAP success criterion 5 forbids env-var opt-in for this key. This is a deliberate divergence from the `default_profile` pattern and is the primary Pitfall #12 prevention baked into the scaffold layer.
    - Do NOT use the value "cost" anywhere in comments, tests, or docstrings. The three canonical tier values are **balanced | quality | budget** per REQUIREMENTS.md TEAM-05.
    - Do NOT add validation hooks or `model_validator` functions. Scope creep.
    - Do NOT write a new `resolve_model_profile` helper in this plan — that lives in Phase 3 per REQUIREMENTS.md traceability. Phase 0 only establishes the RESOLUTION PATH field; Phase 3 consumes it.
    - Do NOT modify `scalar_config_keys()` — that function auto-introspects `ClawTeamConfig.model_fields` and already excludes `profiles` / `presets` by name; `default_model_profile` will appear automatically in `clawteam config show` output.
    - Do NOT write a migration for existing user config.json files — pydantic v2 with `str = "balanced"` default handles the missing-key case natively on `model_validate`.

    After edits, run `ruff check clawteam/config.py` — no new lint should appear (this is a pure additive edit).
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && ruff check clawteam/config.py && python -c "from clawteam.config import ClawTeamConfig, get_effective; c = ClawTeamConfig(); assert c.default_model_profile == 'balanced', repr(c.default_model_profile); assert 'default_model_profile' in ClawTeamConfig.model_fields; print('config smoke OK')"</automated>
  </verify>
  <done>
    `clawteam/config.py` has `default_model_profile: str = "balanced"` field at line 55 (tier values documented as `balanced | quality | budget` per REQUIREMENTS.md TEAM-05). No env_map entry added (deliberate per ROADMAP criterion 5). Updated docstring on `get_effective` documents the divergence. Passes ruff. `ClawTeamConfig().default_model_profile == "balanced"` smoke check passes.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend tests/test_config.py with default_model_profile assertions</name>
  <files>tests/test_config.py</files>
  <behavior>
    - test_default_value_is_balanced: ClawTeamConfig().default_model_profile == "balanced".
    - test_field_present_in_model_fields: "default_model_profile" in ClawTeamConfig.model_fields.
    - test_backward_compat_missing_key_loads_with_default: a config.json lacking the new key deserialises cleanly with default_model_profile == "balanced" (additive-only BC per TEAM-06).
    - test_env_var_is_ignored_by_get_effective (REGRESSION GUARD against Pitfall #12): setting CLAWTEAM_DEFAULT_MODEL_PROFILE=quality in env does NOT cause get_effective("default_model_profile") to return "quality". The value must come from config file or the "balanced" default only. Env var is deliberately not in env_map per ROADMAP criterion 5.
    - test_default_without_env_or_file_is_balanced: with NO env var and NO config file changes, default_model_profile resolves to "balanced", NOT "quality". (Direct Pitfall #12 regression guard.)
    - test_serialisation_roundtrip_preserves_default: save_config + load_config round-trips the field value.
    - test_scalar_config_keys_includes_new_field: scalar_config_keys() auto-introspects model_fields; new field appears automatically for `clawteam config show`.
  </behavior>
  <action>
    First, read the existing `tests/test_config.py` to find the correct insertion point (add to the existing file rather than creating a new one — the file's name mirrors `clawteam/config.py` per TESTING.md convention). Open `tests/test_config.py` and append the new tests at the end.

    Append this block to the existing `tests/test_config.py`:

    ```python


    # ---------------------------------------------------------------------------
    # TEAM-06 / Pitfall #12 — default_model_profile scaffold (Phase 0 plan 00-03)
    # ---------------------------------------------------------------------------


    class TestDefaultModelProfile:
        """default_model_profile establishes the Phase 3 resolution path with a safe default."""

        def test_default_value_is_balanced(self):
            from clawteam.config import ClawTeamConfig

            cfg = ClawTeamConfig()
            assert cfg.default_model_profile == "balanced"

        def test_field_present_in_model_fields(self):
            from clawteam.config import ClawTeamConfig

            assert "default_model_profile" in ClawTeamConfig.model_fields

        def test_backward_compat_missing_key_loads_with_default(self):
            """An existing config.json without 'default_model_profile' must load cleanly."""
            from clawteam.config import ClawTeamConfig

            # Simulate a pre-Phase-0 serialised config: omit the new field entirely.
            legacy_json = {
                "data_dir": "",
                "default_profile": "some-existing-profile",
                "transport": "",
            }
            cfg = ClawTeamConfig.model_validate(legacy_json)
            assert cfg.default_model_profile == "balanced"
            assert cfg.default_profile == "some-existing-profile"

        def test_env_var_is_ignored_by_get_effective(self, monkeypatch):
            """Pitfall #12 regression: CLAWTEAM_DEFAULT_MODEL_PROFILE env var must NOT reach get_effective.

            ROADMAP Phase 0 success criterion 5 requires explicit opt-in via --model-profile
            CLI flag or config file only — never via env var. This test guards against a
            future PR accidentally adding the key back to env_map.
            """
            from clawteam.config import get_effective

            monkeypatch.setenv("CLAWTEAM_DEFAULT_MODEL_PROFILE", "quality")
            value, source = get_effective("default_model_profile")
            assert value == "balanced", (
                "default_model_profile must ignore CLAWTEAM_DEFAULT_MODEL_PROFILE env var; "
                f"got {value!r} from source {source!r}"
            )
            assert source == "default", (
                "env_map must not contain default_model_profile (Pitfall #12 prevention); "
                f"got source {source!r}"
            )

        def test_default_without_env_or_file_is_balanced(self, monkeypatch):
            """Pitfall #12 regression: no env, no file override → 'balanced', NEVER 'quality'."""
            from clawteam.config import get_effective

            monkeypatch.delenv("CLAWTEAM_DEFAULT_MODEL_PROFILE", raising=False)
            value, source = get_effective("default_model_profile")
            assert value == "balanced"
            assert source == "default"

        def test_serialisation_roundtrip_preserves_default(self, tmp_path, monkeypatch):
            """save_config + load_config preserves the default_model_profile field."""
            monkeypatch.setenv("HOME", str(tmp_path))
            from clawteam.config import ClawTeamConfig, config_path, load_config, save_config

            cfg = ClawTeamConfig(default_model_profile="quality")
            # Ensure parent dir exists (save_config uses atomic_write_text which requires it)
            config_path().parent.mkdir(parents=True, exist_ok=True)
            save_config(cfg)
            loaded = load_config()
            assert loaded.default_model_profile == "quality"

        def test_scalar_config_keys_includes_new_field(self):
            """scalar_config_keys() auto-introspects model_fields; new field appears automatically."""
            from clawteam.config import scalar_config_keys

            assert "default_model_profile" in scalar_config_keys()
    ```

    Rules (per PATTERNS.md §tests/test_config.py extension and TESTING.md):
    - APPEND to existing `tests/test_config.py` — do not create a new file.
    - Use class-grouped Style A (`TestDefaultModelProfile`) — consistent with the rest of `tests/test_config.py` which uses this style (per `codebase/TESTING.md` 20 files have `class Test...`; config tests are among them).
    - Lazy imports inside each test method (matches existing `tests/test_config.py` patterns where tests lazy-import from `clawteam.config`).
    - `monkeypatch.setenv` / `monkeypatch.delenv(..., raising=False)` for env var manipulation (TESTING.md standard pattern).
    - `isolated_data_dir` autouse fixture is active (sets HOME=tmp_path, CLAWTEAM_DATA_DIR=tmp_path/.clawteam) — so `config_path()` returns `tmp_path/.clawteam/config.json` NOT the real `~/.clawteam/config.json`. This is why the `test_serialisation_roundtrip_preserves_default` test can safely call `save_config()` without polluting the user's real config.
    - The `monkeypatch.setenv("HOME", str(tmp_path))` in the roundtrip test is belt-and-braces — the autouse fixture already sets HOME, but explicit is better here because the test reasons about `config_path()` which depends on HOME.
    - Section-separator comment block (`# ---- TEAM-06 / Pitfall #12 ----`) matches CONVENTIONS.md inline-section-banner style.
    - Plain `assert`, no `unittest.TestCase`.

    If the existing `tests/test_config.py` already has a `TestDefaultProfile` class, place the new `TestDefaultModelProfile` class immediately after it for symmetry.
  </action>
  <verify>
    <automated>cd /home/jac/repos/ClawTeam-gstack && ruff check tests/test_config.py && pytest tests/test_config.py::TestDefaultModelProfile -v</automated>
  </verify>
  <done>
    `tests/test_config.py` has a new `TestDefaultModelProfile` class appended (minimum 7 tests, including `test_env_var_is_ignored_by_get_effective` as the Pitfall #12 regression guard). All tests pass. Existing tests in the file are unaffected (pure append, no in-place edits). Ruff exit 0.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| env var → resolved default_model_profile | `CLAWTEAM_DEFAULT_MODEL_PROFILE` deliberately does NOT cross into config resolution (no env_map entry). An attacker with shell access setting `CLAWTEAM_DEFAULT_MODEL_PROFILE=quality` has no effect on the resolved profile. |
| config file → resolved default_model_profile | User-writable `~/.clawteam/config.json` could be modified by malware or another user on a shared host. Opt-in to non-default profile must happen here (or via `--model-profile` CLI flag in Phase 3). |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-00-11 | Elevation of Privilege (cost blowup) | `clawteam/config.py::ClawTeamConfig.default_model_profile` default | mitigate | Default is `"balanced"`, mandated by ROADMAP Phase 0 success criterion 5. `test_default_without_env_or_file_is_balanced` is an explicit regression guard: any future PR that changes the default triggers immediate test failure. This closes the "silently Opus on every spawn" cost-blowup pattern from Pitfall #12. |
| T-00-12 | Elevation of Privilege (cost blowup) | `CLAWTEAM_DEFAULT_MODEL_PROFILE=quality` stealth env override | mitigate (by design) | ROADMAP Phase 0 success criterion 5 restricts opt-in to `--model-profile` flag or config file — explicitly NOT env var. This plan deliberately omits the env_map entry that would wire the env var in (PATTERNS.md originally recommended adding it for parity with `default_profile`; that recommendation is superseded by the ROADMAP criterion for this field). `test_env_var_is_ignored_by_get_effective` is the direct regression guard: it sets the env var and asserts `get_effective("default_model_profile")` returns `("balanced", "default")`, not `("quality", "env")`. Any future PR that re-introduces the env_map entry fails this test. |
| T-00-13 | Tampering | user modifies config.json to set `default_model_profile: "experimental-8x-model"` | accept | No `Literal` validation in v1 — any string accepted. This is a DELIBERATE scope choice (PATTERNS.md "What NOT to add yet"). Future Phase 3 resolver can reject unknown profiles, but Phase 0 only scaffolds. Risk is low because an attacker with config.json write access already has bigger leverage. |
| T-00-14 | Information Disclosure | default_model_profile value printed in `clawteam config show` output | accept | `scalar_config_keys()` auto-includes the new field; `config show` will display it alongside other scalar config values. This is BY DESIGN — users need to see what profile they're using. Value is an enum-like string (`balanced` / `quality` / `budget` per REQUIREMENTS.md TEAM-05), not a secret. |
</threat_model>

<verification>
Phase-level verification:

```bash
cd /home/jac/repos/ClawTeam-gstack
ruff check clawteam/config.py tests/test_config.py
pytest tests/test_config.py -v --tb=short
python -c "from clawteam.config import ClawTeamConfig; c = ClawTeamConfig(); assert c.default_model_profile == 'balanced'; print('Scaffold OK')"
python -c "from clawteam.config import get_effective; v, s = get_effective('default_model_profile'); assert v == 'balanced' and s == 'default'; print('Priority OK')"
```

Expected:
- ruff exit 0 (additive edits only).
- All existing `tests/test_config.py` tests PASS (no BC regression).
- New `TestDefaultModelProfile` class: all 7 tests PASS.
- Config smoke: default is `balanced`, field is in model_fields.
- Priority smoke: clean env → `('balanced', 'default')`.

Env-var-ignored regression check (Pitfall #12 prevention — env var must NOT promote to quality):
```bash
CLAWTEAM_DEFAULT_MODEL_PROFILE=quality python -c "from clawteam.config import get_effective; v, s = get_effective('default_model_profile'); assert v == 'balanced' and s == 'default', f'env var leaked: got ({v!r}, {s!r})'; print('env var correctly ignored')"
```

Existing template BC (no existing template reads default_model_profile, so launch should be unaffected):
```bash
# If plan 00-04 has completed: its regression matrix will exercise all 6 templates and must still pass.
pytest tests/test_templates.py -q
```
</verification>

<success_criteria>
1. `clawteam/config.py` has new `default_model_profile: str = "balanced"` field immediately below `default_profile` (line ~55), with trailing comment documenting the three canonical tier values `balanced | quality | budget` per REQUIREMENTS.md TEAM-05.
2. `clawteam/config.py::get_effective::env_map` does NOT contain a `default_model_profile` entry — this is the deliberate divergence from the `default_profile` pattern, mandated by ROADMAP Phase 0 success criterion 5.
3. `clawteam/config.py::get_effective` docstring explains why `default_model_profile` is absent from `env_map` (Pitfall #12 prevention; opt-in via `--model-profile` CLI or config file only).
4. `ClawTeamConfig()` constructs with `default_model_profile == "balanced"`.
5. `get_effective("default_model_profile")` returns `("balanced", "default")` both when nothing is set AND when `CLAWTEAM_DEFAULT_MODEL_PROFILE=quality` is exported (env var is ignored by design).
6. `tests/test_config.py` gains a `TestDefaultModelProfile` class with ≥7 tests including the `test_env_var_is_ignored_by_get_effective` regression guard; all pass.
7. Existing `tests/test_config.py` tests unchanged and still pass (no in-place edits to existing tests).
8. `ruff check clawteam/config.py tests/test_config.py` exits 0.
9. Serialisation roundtrip preserves the field (save_config → load_config → same value).
10. BC guarantee: `ClawTeamConfig.model_validate({"data_dir": "", "default_profile": "x"})` (legacy JSON missing the new field) produces a valid model with `default_model_profile == "balanced"`.
11. No occurrence of the value `"cost"` as a tier name anywhere in the plan-modified files — the canonical values are `balanced`, `quality`, `budget`.
</success_criteria>

<output>
After completion, create `.planning/phases/00-foundation-upstream-rfc/00-03-SUMMARY.md` following `@$HOME/.claude/get-shit-done/templates/summary.md`, documenting:
- Field added: `default_model_profile: str = "balanced"` — Pitfall #12 cost-blowup prevention default.
- Canonical tier values: `balanced | quality | budget` per REQUIREMENTS.md TEAM-05 (NOT `cost` — previous draft referenced `cost` incorrectly; this was corrected before execution).
- Deliberate divergence from `default_profile` pattern: `default_model_profile` is NOT wired into `env_map`. Rationale: ROADMAP Phase 0 success criterion 5 restricts opt-in to `--model-profile` CLI flag or config file, never env var. Regression guard: `test_env_var_is_ignored_by_get_effective`.
- Explicit non-change: no `Literal[...]` validation (deferred to Phase 3 resolver per REQUIREMENTS.md traceability).
- Explicit non-change: no `resolve_model_profile` helper (Phase 3 scope per RESEARCH.md §Pattern 4).
- Hand-off to Phase 3: the resolver will add the `--model-profile` CLI flag and template-field precedence; Phase 0 guarantees that until then, no env var can silently promote to `quality`.
</output>
