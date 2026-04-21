---
phase: 04
plan: 13
type: execute
wave: 4
depends_on: [06, 07, 08, 09]
files_modified:
  - tests/fixtures/review_routing/renamed_ui_component.diff
  - tests/fixtures/review_routing/crypto_test_file.diff
  - tests/fixtures/review_routing/whitespace_only.diff
  - tests/fixtures/review_routing/package_json_dep_bump.diff
  - tests/fixtures/review_routing/auth_middleware_rewrite.diff
  - tests/fixtures/review_routing/cross_cutting_refactor.diff
  - tests/fixtures/review_routing/mixed_ui_and_api.diff
  - tests/fixtures/review_routing/generated_migration.diff
  - tests/fixtures/review_routing/expected_routing.json
  - tests/test_adversarial_routing.py
  - tests/test_state_machine_goldens.py
autonomous: true
requirements: [SPRINT-03, QUALITY-07]
must_haves:
  truths:
    - "8 fixture diffs exist under tests/fixtures/review_routing/ covering the adversarial set from §04-CONTEXT specifics."
    - "expected_routing.json declares the canonical participants set per fixture."
    - "Parametrized golden test iterates all 8 fixtures and asserts router output matches expected."
    - "State-machine golden tests enforce bijective transitions for all 3 state machines (office-hours, design-consultation, investigate)."
    - "Tests ALSO assert turn budgets match fixtures (catches monologue-collapse — Pitfall 7)."
  artifacts:
    - path: "tests/fixtures/review_routing/"
      provides: "8 adversarial diff fixtures + expected_routing.json"
      contains: "renamed_ui_component.diff"
    - path: "tests/test_adversarial_routing.py"
      provides: "Parametrized test over fixtures"
      contains: "def test_adversarial_diffs"
    - path: "tests/test_state_machine_goldens.py"
      provides: "Consolidated golden tests for 3 state machines"
      contains: "def test_state_machines_match_fixtures"
  key_links:
    - from: "tests/fixtures/review_routing/*.diff"
      to: "GstackReviewRouter.match"
      via: "Test extracts diff paths from fixture and feeds to router"
    - from: "expected_routing.json"
      to: "test_adversarial_diffs parametrization"
      via: "Fixture keys map to expected reviewer sets"
---

<objective>
Ship the 8-fixture adversarial routing golden test set (§04-CONTEXT specifics) and the consolidated state-machine golden tests across all 3 interactive skills. The routing goldens catch regressions like "renamed UI file should still pull designer" and "whitespace-only diff pulls only the floor". The state-machine goldens catch transition-table drift (e.g., accidental addition of a transition that bypasses a question).

Purpose: SPRINT-03 requires "verified by a routing golden test over at least 8 fixture diffs including adversarial cases". QUALITY-07 requires interactive skills to remain multi-turn; turn-budget assertions catch regression.

Output: 8 diff files + 1 expected_routing.json + 2 test files. No source code changes.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-CONTEXT.md

<interfaces>
From clawteam/harness/gstack_review_router.py (Plan 06):
```python
class GstackReviewRouter:
    def match(self, diff_paths: list[str], state) -> list[str]:
```

From Plan 07/08/09 fixtures:
- tests/fixtures/gstack_state_machines/office-hours.transitions.json (13 transitions)
- tests/fixtures/gstack_state_machines/design-consultation.transitions.json (15 transitions)
- tests/fixtures/gstack_state_machines/investigate.transitions.json (8 transitions)

Fixture diff format: unified git diff text. For routing tests we extract the list of modified paths by scanning `diff --git a/<path>` lines.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create 8 adversarial diff fixtures + expected_routing.json</name>
  <files>tests/fixtures/review_routing/renamed_ui_component.diff, tests/fixtures/review_routing/crypto_test_file.diff, tests/fixtures/review_routing/whitespace_only.diff, tests/fixtures/review_routing/package_json_dep_bump.diff, tests/fixtures/review_routing/auth_middleware_rewrite.diff, tests/fixtures/review_routing/cross_cutting_refactor.diff, tests/fixtures/review_routing/mixed_ui_and_api.diff, tests/fixtures/review_routing/generated_migration.diff, tests/fixtures/review_routing/expected_routing.json</files>
  <read_first>
    - clawteam/templates/gstack.toml (the 6 rules — ensure fixtures exercise them)
  </read_first>
  <action>
Create each fixture diff as a minimal unified-diff excerpt. Content is illustrative; the ONLY load-bearing feature is the `diff --git a/<path> b/<path>` header lines — tests parse those to extract modified paths.

**`tests/fixtures/review_routing/renamed_ui_component.diff`** (renamed file; designer still pulled):
```diff
diff --git a/src/components/OldButton.tsx b/src/components/Button.tsx
similarity index 95%
rename from src/components/OldButton.tsx
rename to src/components/Button.tsx
--- a/src/components/OldButton.tsx
+++ b/src/components/Button.tsx
@@ -1,3 +1,3 @@
-export function OldButton() {
+export function Button() {
   return <button>Click</button>
 }
```

**`tests/fixtures/review_routing/crypto_test_file.diff`** (test file that imports crypto; security pulled):
```diff
diff --git a/tests/test_crypto_helpers.py b/tests/test_crypto_helpers.py
--- a/tests/test_crypto_helpers.py
+++ b/tests/test_crypto_helpers.py
@@ -1,3 +1,4 @@
 from lib.crypto.aes import encrypt
+from lib.crypto.keys import rotate

 def test_encrypt():
     pass
diff --git a/lib/crypto/keys.py b/lib/crypto/keys.py
new file mode 100644
--- /dev/null
+++ b/lib/crypto/keys.py
@@ -0,0 +1,3 @@
+def rotate():
+    pass
```

**`tests/fixtures/review_routing/whitespace_only.diff`** (no reviewers beyond floor):
```diff
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1,3 +1,3 @@
 # Project

-Description here.
+Description here.
```

**`tests/fixtures/review_routing/package_json_dep_bump.diff`** (dx-lead pulled):
```diff
diff --git a/package.json b/package.json
--- a/package.json
+++ b/package.json
@@ -10,7 +10,7 @@
   "dependencies": {
-    "react": "^18.2.0",
+    "react": "^18.3.0",
     "react-dom": "^18.2.0"
   }
 }
```

**`tests/fixtures/review_routing/auth_middleware_rewrite.diff`** (security pulled):
```diff
diff --git a/src/auth/middleware.py b/src/auth/middleware.py
--- a/src/auth/middleware.py
+++ b/src/auth/middleware.py
@@ -1,10 +1,15 @@
-def verify_token(token):
-    if not token:
-        return None
-    return jwt.decode(token)
+def verify_token(token):
+    if not token or len(token) < 10:
+        return None
+    try:
+        return jwt.decode(token, verify=True)
+    except InvalidTokenError:
+        return None
```

**`tests/fixtures/review_routing/cross_cutting_refactor.diff`** (multiple rule matches — union of reviewers):
```diff
diff --git a/src/components/Form.tsx b/src/components/Form.tsx
--- a/src/components/Form.tsx
+++ b/src/components/Form.tsx
@@ -1,3 +1,3 @@
 export function Form() {}
diff --git a/src/auth/tokens.py b/src/auth/tokens.py
--- a/src/auth/tokens.py
+++ b/src/auth/tokens.py
@@ -1,3 +1,3 @@
 def mint(): pass
diff --git a/app/api/users.ts b/app/api/users.ts
--- a/app/api/users.ts
+++ b/app/api/users.ts
@@ -1,3 +1,3 @@
 export async function GET() {}
diff --git a/package.json b/package.json
--- a/package.json
+++ b/package.json
@@ -1,3 +1,3 @@
 {}
```

**`tests/fixtures/review_routing/mixed_ui_and_api.diff`** (designer + dx-lead + reviewer-floor):
```diff
diff --git a/src/components/Dashboard.tsx b/src/components/Dashboard.tsx
--- a/src/components/Dashboard.tsx
+++ b/src/components/Dashboard.tsx
@@ -1,3 +1,3 @@
 export function Dashboard() {}
diff --git a/app/api/dashboard/route.ts b/app/api/dashboard/route.ts
--- a/app/api/dashboard/route.ts
+++ b/app/api/dashboard/route.ts
@@ -1,3 +1,3 @@
 export async function GET() {}
```

**`tests/fixtures/review_routing/generated_migration.diff`** (reviewer-floor only):
```diff
diff --git a/migrations/20260421_add_user_table.sql b/migrations/20260421_add_user_table.sql
new file mode 100644
--- /dev/null
+++ b/migrations/20260421_add_user_table.sql
@@ -0,0 +1,5 @@
+CREATE TABLE users (
+    id SERIAL PRIMARY KEY,
+    email TEXT NOT NULL
+);
diff --git a/docs/changelog.md b/docs/changelog.md
--- a/docs/changelog.md
+++ b/docs/changelog.md
@@ -1,3 +1,4 @@
 # Changelog
+2026-04-21: Added users table.
```

**`tests/fixtures/review_routing/expected_routing.json`** (the oracle):
```json
{
  "renamed_ui_component": {
    "diff_files": ["src/components/Button.tsx", "src/components/OldButton.tsx"],
    "expected_participants": ["designer", "reviewer"],
    "note": "Renamed UI file still pulls designer; both old+new paths considered (git diff --name-only emits both)."
  },
  "crypto_test_file": {
    "diff_files": ["tests/test_crypto_helpers.py", "lib/crypto/keys.py"],
    "expected_participants": ["reviewer", "security"],
    "note": "lib/crypto/keys.py matches **/crypto/** → security."
  },
  "whitespace_only": {
    "diff_files": ["README.md"],
    "expected_participants": ["reviewer"],
    "note": "No rules match README.md; floor only."
  },
  "package_json_dep_bump": {
    "diff_files": ["package.json"],
    "expected_participants": ["dx-lead", "reviewer"],
    "note": "package.json rule pulls dx-lead."
  },
  "auth_middleware_rewrite": {
    "diff_files": ["src/auth/middleware.py"],
    "expected_participants": ["reviewer", "security"],
    "note": "src/auth/** rule pulls security."
  },
  "cross_cutting_refactor": {
    "diff_files": ["src/components/Form.tsx", "src/auth/tokens.py", "app/api/users.ts", "package.json"],
    "expected_participants": ["designer", "dx-lead", "reviewer", "security"],
    "note": "Union of designer (UI) + security (auth) + dx-lead (api + package)."
  },
  "mixed_ui_and_api": {
    "diff_files": ["src/components/Dashboard.tsx", "app/api/dashboard/route.ts"],
    "expected_participants": ["designer", "dx-lead", "reviewer"],
    "note": "UI + api = designer + dx-lead + floor."
  },
  "generated_migration": {
    "diff_files": ["migrations/20260421_add_user_table.sql", "docs/changelog.md"],
    "expected_participants": ["reviewer"],
    "note": "Migrations + docs not routed; floor only."
  }
}
```
  </action>
  <verify>
    <automated>python3 -c "import json; d = json.load(open('tests/fixtures/review_routing/expected_routing.json')); assert len(d) == 8; print('OK', list(d.keys()))"</automated>
  </verify>
  <acceptance_criteria>
    - ls tests/fixtures/review_routing/*.diff | wc -l returns 8
    - ls tests/fixtures/review_routing/expected_routing.json succeeds
    - expected_routing.json keys are exactly: renamed_ui_component, crypto_test_file, whitespace_only, package_json_dep_bump, auth_middleware_rewrite, cross_cutting_refactor, mixed_ui_and_api, generated_migration
    - Each diff file contains at least one `diff --git` header line
    - Each expected_routing entry includes "reviewer" in expected_participants (floor check)
  </acceptance_criteria>
  <done>8 adversarial diffs + oracle JSON exist</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Parametrized golden test for adversarial routing</name>
  <files>tests/test_adversarial_routing.py</files>
  <read_first>
    - tests/fixtures/review_routing/expected_routing.json (Task 1)
    - clawteam/harness/gstack_review_router.py (Plan 06)
    - clawteam/plugins/gstack_sprint_plugin.py (after Plan 11 — contribute_review_routers returns router with rules loaded)
    - clawteam/templates/gstack.toml (after Plan 06 — the 6 rules)
  </read_first>
  <behavior>
    - Test (parametrized, 8 cases): For each fixture in expected_routing.json, extract diff_files, feed to GstackReviewRouter (constructed from loaded gstack.toml rules), assert sorted(result) == sorted(expected_participants).
    - Test 2 (test_diff_file_extraction_from_unified_diff): Helper `_extract_paths_from_diff(diff_text) -> list[str]` returns paths from `diff --git a/... b/...` lines including renames.
    - Test 3 (test_each_expected_set_contains_reviewer_floor): All 8 fixtures include "reviewer" — sanity check on oracle.
  </behavior>
  <action>
Create `tests/test_adversarial_routing.py`:

```python
"""8-fixture adversarial routing golden test (Plan 04-13 — SPRINT-03)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from clawteam.harness.gstack_review_router import GstackReviewRouter
from clawteam.templates import load_template


_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "review_routing"
_EXPECTED = json.loads((_FIXTURE_DIR / "expected_routing.json").read_text(encoding="utf-8"))


def _extract_paths_from_diff(diff_text: str) -> list[str]:
    """Extract modified+renamed paths from a unified git diff (handles a/ + b/ both)."""
    paths: set[str] = set()
    for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)", diff_text, re.MULTILINE):
        paths.add(m.group(1))
        paths.add(m.group(2))
    # Also handle rename from/to lines.
    for m in re.finditer(r"^rename from (\S+)", diff_text, re.MULTILINE):
        paths.add(m.group(1))
    for m in re.finditer(r"^rename to (\S+)", diff_text, re.MULTILINE):
        paths.add(m.group(1))
    return sorted(paths)


@pytest.fixture
def gstack_router() -> GstackReviewRouter:
    tmpl = load_template("gstack")
    return GstackReviewRouter(list(tmpl.review.rules))


@pytest.mark.parametrize("fixture_name,spec", list(_EXPECTED.items()))
def test_adversarial_diffs(fixture_name: str, spec: dict, gstack_router):
    """Each adversarial diff produces the expected participant set."""
    diff_path = _FIXTURE_DIR / f"{fixture_name}.diff"
    assert diff_path.exists(), f"missing fixture diff: {diff_path}"
    diff_text = diff_path.read_text(encoding="utf-8")
    extracted_paths = _extract_paths_from_diff(diff_text)

    # Sanity: expected_routing.json declares diff_files that should appear
    # in extracted_paths (superset check — extraction may include a/+b/ both).
    for declared in spec["diff_files"]:
        assert declared in extracted_paths, (
            f"{fixture_name}: declared diff_file {declared!r} not in extracted paths {extracted_paths}"
        )

    state = SimpleNamespace(workspace_branch="", review_sha="")
    result = gstack_router.match(extracted_paths, state)
    assert sorted(result) == sorted(spec["expected_participants"]), (
        f"{fixture_name}: got {sorted(result)}, expected {sorted(spec['expected_participants'])} "
        f"(note: {spec.get('note', '—')})"
    )


def test_extract_paths_handles_renames():
    text = """diff --git a/src/old.tsx b/src/new.tsx
rename from src/old.tsx
rename to src/new.tsx"""
    paths = _extract_paths_from_diff(text)
    assert "src/old.tsx" in paths
    assert "src/new.tsx" in paths


def test_extract_paths_handles_new_file():
    text = """diff --git a/lib/newfile.py b/lib/newfile.py
new file mode 100644"""
    paths = _extract_paths_from_diff(text)
    assert "lib/newfile.py" in paths


def test_all_expected_sets_contain_reviewer_floor():
    """Sanity: every adversarial case still includes reviewer floor."""
    for name, spec in _EXPECTED.items():
        assert "reviewer" in spec["expected_participants"], (
            f"{name} oracle missing reviewer floor"
        )


def test_fixture_count_is_8():
    assert len(_EXPECTED) == 8
    diff_files = list(_FIXTURE_DIR.glob("*.diff"))
    assert len(diff_files) == 8
```
  </action>
  <verify>
    <automated>pytest tests/test_adversarial_routing.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - pytest tests/test_adversarial_routing.py -x -q exits 0 (8 parametrized + 4 helper tests = 12 pass)
    - Each of 8 adversarial cases is independently asserted (parametrize IDs visible in output)
  </acceptance_criteria>
  <done>8 adversarial diffs + oracle JSON drive a parametrized golden test asserting routing correctness</done>
</task>

<task type="auto">
  <name>Task 3: Consolidated state-machine golden tests</name>
  <files>tests/test_state_machine_goldens.py</files>
  <read_first>
    - tests/fixtures/gstack_state_machines/office-hours.transitions.json (Plan 07)
    - tests/fixtures/gstack_state_machines/design-consultation.transitions.json (Plan 08)
    - tests/fixtures/gstack_state_machines/investigate.transitions.json (Plan 09)
    - clawteam/templates/gstack/skills/office_hours/state.py (Plan 07)
    - clawteam/templates/gstack/skills/design_consultation/state.py (Plan 08)
    - clawteam/templates/gstack/skills/investigate/state.py (Plan 09)
  </read_first>
  <behavior>
    - Test (parametrized over 3 state machines): For each (fixture_path, transitions_dict, turn_budget_constant, final_states_constant):
      - Assert fixture JSON's `transitions` bijectively matches the in-code dict's triples.
      - Assert fixture's `turn_budget` matches the constant.
      - Assert fixture's `final_states` matches the constant.
  </behavior>
  <action>
Create `tests/test_state_machine_goldens.py`:

```python
"""Consolidated state-machine goldens (Plan 04-13 — QUALITY-07 regression defense).

Cross-cuts Plan 07/08/09 per-skill tests: asserts each skill's in-code
_TRANSITIONS dict + TURN_BUDGET + _FINAL_STATES agree with the fixture JSON
under tests/fixtures/gstack_state_machines/. Useful for catching drift where
one edit touches fixture without code (or vice versa).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


_FIXTURE_DIR = Path(__file__).parent / "fixtures" / "gstack_state_machines"


# ── Golden machinery ─────────────────────────────────────────────────

def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text(encoding="utf-8"))


# Parametrize over (skill_name, fixture_filename, module_import_path).
# Each module exposes: _TRANSITIONS, TURN_BUDGET, _FINAL_STATES
STATE_MACHINES = [
    ("office-hours", "office-hours.transitions.json",
     "clawteam.templates.gstack.skills.office_hours.state"),
    ("design-consultation", "design-consultation.transitions.json",
     "clawteam.templates.gstack.skills.design_consultation.state"),
    ("investigate", "investigate.transitions.json",
     "clawteam.templates.gstack.skills.investigate.state"),
]


@pytest.mark.parametrize("skill,fixture_name,module_path", STATE_MACHINES)
def test_transitions_match_fixture(skill, fixture_name, module_path):
    import importlib
    mod = importlib.import_module(module_path)
    transitions = getattr(mod, "_TRANSITIONS")

    fx = _load_fixture(fixture_name)
    code_triples = {(k[0], k[1], v) for k, v in transitions.items()}
    fx_triples = {(t["from"], t["event"], t["to"]) for t in fx["transitions"]}

    assert code_triples == fx_triples, (
        f"[{skill}] transition drift\n"
        f"  only in code: {sorted(code_triples - fx_triples)}\n"
        f"  only in fixture: {sorted(fx_triples - code_triples)}"
    )


@pytest.mark.parametrize("skill,fixture_name,module_path", STATE_MACHINES)
def test_turn_budget_matches_fixture(skill, fixture_name, module_path):
    import importlib
    mod = importlib.import_module(module_path)
    turn_budget = getattr(mod, "TURN_BUDGET")
    fx = _load_fixture(fixture_name)
    assert turn_budget == fx["turn_budget"], (
        f"[{skill}] TURN_BUDGET={turn_budget} vs fixture={fx['turn_budget']}"
    )


@pytest.mark.parametrize("skill,fixture_name,module_path", STATE_MACHINES)
def test_final_states_match_fixture(skill, fixture_name, module_path):
    import importlib
    mod = importlib.import_module(module_path)
    final_states = getattr(mod, "_FINAL_STATES")
    fx = _load_fixture(fixture_name)
    assert set(final_states) == set(fx["final_states"]), (
        f"[{skill}] final_states={set(final_states)} vs fixture={set(fx['final_states'])}"
    )


def test_all_state_machines_covered():
    """Sanity: 3 state machines = 3 fixture files."""
    fixtures = list(_FIXTURE_DIR.glob("*.transitions.json"))
    assert len(fixtures) == 3, (
        f"Expected 3 state-machine fixtures, found: {[f.name for f in fixtures]}"
    )


def test_monologue_collapse_detector():
    """Pitfall 7: turn budgets enforce multi-turn progression.

    Each state machine must have turn_budget > number of final states + 1
    (i.e., at least the initial + each transition cycle costs one turn).
    Office-hours: 13 turns for 6 questions (11-13 acceptable).
    Design-consultation: 15 turns for 7 dimensions.
    Investigate: 12-turn budget accounts for up to 3 hypothesis cycles.
    """
    oh = _load_fixture("office-hours.transitions.json")
    dc = _load_fixture("design-consultation.transitions.json")
    inv = _load_fixture("investigate.transitions.json")
    assert oh["turn_budget"] >= 10, "office-hours budget too low; monologue risk"
    assert dc["turn_budget"] >= 10, "design-consultation budget too low"
    assert inv["turn_budget"] >= 8, "investigate budget too low"
```
  </action>
  <verify>
    <automated>pytest tests/test_state_machine_goldens.py -x -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - pytest tests/test_state_machine_goldens.py -x -q exits 0 (12 tests = 3 parametrized groups × 3 + 2 misc)
    - All 3 state machines bijectively match their fixtures
  </acceptance_criteria>
  <done>Consolidated golden harness catches any future drift between fixture JSON and in-code transition tables</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

Test fixtures are committed to git; no external input.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-04-41 | T (Tampering) | Fixture drift between diff + oracle | mitigate | Golden tests assert diff paths appear in extracted_paths; any new rule requires both sides updated |
| T-04-42 | I | Diff fixture content | accept | Fixtures are synthetic; no real secrets |
</threat_model>

<verification>
- [ ] `pytest tests/test_adversarial_routing.py tests/test_state_machine_goldens.py -x -q` exits 0
- [ ] `ls tests/fixtures/review_routing/*.diff | wc -l` == 8
- [ ] `ls tests/fixtures/gstack_state_machines/*.transitions.json | wc -l` == 3
- [ ] Plan 06/07/08/09 in-plan tests still pass (fixture addition doesn't break them)
</verification>

<success_criteria>
- [ ] 8 adversarial routing fixtures drive a parametrized golden test
- [ ] 3 state-machine fixtures drive a consolidated bijective golden test
- [ ] 12 routing tests + 12 state-machine golden tests all pass
- [ ] Catches regressions where rule edits forget to update fixtures (and vice versa)
</success_criteria>

<output>
Create `.planning/phases/04-interactive-state-machines-smart-review-routing-cross-agent-verification/04-13-adversarial-routing-golden-tests-SUMMARY.md`.
</output>
