"""Regression tests for the shared YAML scalar-quoting helper (Phase-5 REVIEW WR-01).

Before this helper existed, the four Phase-5 Wave-1 hand-rolled emitters
(/ship, /land-and-deploy, /canary, /benchmark) serialized strings via Python's
:func:`repr`, which produces Python string literals — NOT valid YAML 1.2.
Strings containing embedded single quotes, newlines, or backslashes produced
subtly wrong output when read by PyYAML (the library downstream EvidenceGate
consumers rely on).

These tests pin the new behavior:

* Single quotes inside strings are doubled per YAML 1.2 §7.4.2 — the ``repr``
  output would have switched to double-quoted form, breaking the parser shape
  invariant the four hand-rolled frontmatter READERS depend on.
* Multi-line strings fall back to JSON-encoded form so they remain a valid
  YAML flow scalar on a single frontmatter line. A raw ``repr`` emission
  would have embedded literal ``\\n`` escapes in single-quoted form — which
  a YAML 1.2 reader interprets as the four literal characters ``\\``, ``n``,
  NOT a newline.
* The round-trip through PyYAML produces the original Python string. This is
  the primary correctness check — PyYAML is what downstream tooling uses.
"""

from __future__ import annotations

import json

import pytest

from clawteam.templates.gstack.skills._yaml_emit import yaml_quote_string


def test_simple_string_single_quoted():
    """No special characters → single-quoted scalar."""
    assert yaml_quote_string("hello") == "'hello'"


def test_embedded_single_quote_doubled():
    """YAML 1.2 §7.4.2 single-quote doubling — NOT repr's switch to double quotes."""
    # repr("it's broken") emits `"it's broken"` (double-quoted form).
    # The hand-rolled frontmatter parsers strip matching outer quotes, so a
    # double-quoted payload with interior single quotes would either produce
    # `it's broken` (ok) or corrupt downstream PyYAML consumers. Our helper
    # standardizes on single-quoted form with `'` doubled.
    assert yaml_quote_string("it's broken") == "'it''s broken'"


def test_multiple_single_quotes_all_doubled():
    """All embedded ``'`` instances are doubled, not just the first."""
    assert yaml_quote_string("a'b'c") == "'a''b''c'"


def test_newline_falls_back_to_json_form():
    """Newlines switch to JSON-encoded form (valid YAML flow scalar)."""
    result = yaml_quote_string("a\nb")
    # JSON form: double-quoted with \n escape.
    assert result == '"a\\nb"'
    # And json.loads round-trips it to the original string.
    assert json.loads(result) == "a\nb"


def test_carriage_return_falls_back_to_json_form():
    """\\r is also a line-breaker YAML single-quoted scalars cannot hold."""
    result = yaml_quote_string("a\rb")
    assert json.loads(result) == "a\rb"


def test_backslash_safe_in_single_quoted():
    """Backslashes are LITERAL inside YAML single-quoted scalars — no escaping needed.

    ``repr`` would have emitted ``'a\\\\b'`` (double-backslash), which a YAML
    1.2 reader interprets as a literal two-character sequence ``a\\b`` —
    still technically correct but doubling the backslash count surprises
    downstream consumers. Our single-quoted form stays one-to-one.
    """
    # repr("a\\b") == "'a\\\\b'" — two backslashes escaped.
    # yaml_quote_string("a\\b") == "'a\\b'" — one literal backslash.
    assert yaml_quote_string("a\\b") == "'a\\b'"


def test_pyyaml_round_trip_with_single_quote():
    """The primary correctness check — PyYAML (used by downstream consumers)
    parses our output back to the original Python string.
    """
    pyyaml = pytest.importorskip("yaml")
    original = "it's a \"test\" value"
    quoted = yaml_quote_string(original)
    # Embed in minimal YAML document.
    parsed = pyyaml.safe_load(f"key: {quoted}\n")
    assert parsed == {"key": original}


def test_pyyaml_round_trip_with_newline():
    """Multi-line payload round-trips through PyYAML (JSON form path)."""
    pyyaml = pytest.importorskip("yaml")
    original = "line1\nline2\nline3"
    quoted = yaml_quote_string(original)
    parsed = pyyaml.safe_load(f"key: {quoted}\n")
    assert parsed == {"key": original}


def test_pyyaml_round_trip_with_backslash():
    """Backslash-containing payload round-trips via PyYAML."""
    pyyaml = pytest.importorskip("yaml")
    original = "C:\\Users\\foo"
    quoted = yaml_quote_string(original)
    parsed = pyyaml.safe_load(f"key: {quoted}\n")
    assert parsed == {"key": original}


def test_empty_string():
    """Empty string is a valid YAML scalar."""
    assert yaml_quote_string("") == "''"


# ---------------------------------------------------------------------------
# Integration — each of the four Wave-1 handlers now routes strings through
# yaml_quote_string(). We verify the output shape on a payload that would
# have broken the pre-fix repr() path.
# ---------------------------------------------------------------------------


def test_ship_notes_handles_embedded_single_quote(tmp_path, monkeypatch):
    """Regression: failure_reason containing ``'`` must produce valid YAML."""
    from clawteam.templates.gstack.skills.ship import handler
    from clawteam.templates.gstack.skills.ship.steps import StepResult

    monkeypatch.setattr(handler, "gh_available", lambda: True)
    # Fail on run_tests with a failure_reason that contains a single quote.
    monkeypatch.setattr(
        handler, "sync_main",
        lambda cwd, branch, **kw: StepResult(True, {}),
    )
    monkeypatch.setattr(
        handler, "run_tests",
        lambda cwd, sprint_dir, **kw: StepResult(
            False, {"error": "it's broken", "stderr": "line1\nline2"},
        ),
    )

    sprint_dir = tmp_path / "sprint-001"
    sprint_dir.mkdir()

    class _Ctx:
        def __init__(self) -> None:
            self.sprint_dir = sprint_dir
            self.workspace_dir = tmp_path
            self.sprint_id = "sprint-001"
            self.branch = "feature/x"

    out = handler.ship_handler(
        _Ctx(), role="shipper",
        args={"title": "T", "body": "B", "branch": "feature/x"},
    )
    assert out["ship_status"] == "failed"

    # The emitted YAML must parse with PyYAML (the strict downstream parser).
    pyyaml = pytest.importorskip("yaml")
    raw = (sprint_dir / "ship-notes.md").read_text()
    # Extract the frontmatter block.
    assert raw.startswith("---\n")
    end = raw.find("\n---", 4)
    assert end != -1
    fm_text = raw[4:end]
    parsed = pyyaml.safe_load(fm_text)
    assert isinstance(parsed, dict)
    # ship_status round-trips to a plain python string.
    assert parsed.get("ship_status") == "failed"
    # failure_reason holds the dict-stringified payload — critically, the
    # embedded `'` does NOT break the YAML parse (pre-fix repr() would have
    # emitted a double-quoted form that downstream tools mis-parse).
    assert "it's broken" in str(parsed.get("failure_reason", ""))


def test_deploy_notes_pyyaml_safe(tmp_path):
    """Regression: deploy.md frontmatter parses with PyYAML after WR-01 fix."""
    from clawteam.templates.gstack.schemas.deploy_notes import DeployNotes
    from clawteam.templates.gstack.skills.land_and_deploy.handler import (
        _render_deploy_notes_yaml,
    )

    schema = DeployNotes(
        artifact_type="deploy-notes",
        deploy_status="succeeded",
        deploy_url="https://it's-a-test.example.com/path",
        provider="custom",
        deployed_at="2025-01-01T00:00:00+00:00",
        commit_sha="abc1234",
        sprint_id="sprint-001",
        created_at="2025-01-01T00:00:00+00:00",
    )
    out = _render_deploy_notes_yaml(schema)

    pyyaml = pytest.importorskip("yaml")
    # Strip the outer `---` delimiters so we can feed the inner block to PyYAML.
    assert out.startswith("---\n")
    end = out.find("\n---", 4)
    assert end != -1
    inner = out[4:end]
    parsed = pyyaml.safe_load(inner)
    assert parsed["deploy_url"] == "https://it's-a-test.example.com/path"


def test_canary_report_pyyaml_safe(tmp_path):
    """Regression: canary-report.md parses with PyYAML after WR-01 fix."""
    from clawteam.templates.gstack.schemas.canary_report import CanaryReport
    from clawteam.templates.gstack.skills.canary.handler import (
        _render_canary_report_yaml,
    )

    schema = CanaryReport(
        artifact_type="canary-report",
        canary_status="clean",
        window_seconds=60,
        http_2xx_count=10,
        http_5xx_count=0,
        avg_response_ms=100.0,
        pre_deploy_avg_response_ms=0.0,
        baseline_missing=True,
        js_console_errors=["TypeError: it's undefined"],
        regression_flags=[],
        sprint_id="sprint's-001",
        created_at="2025-01-01T00:00:00+00:00",
    )
    out = _render_canary_report_yaml(schema)

    pyyaml = pytest.importorskip("yaml")
    assert out.startswith("---\n")
    end = out.find("\n---", 4)
    assert end != -1
    inner = out[4:end]
    parsed = pyyaml.safe_load(inner)
    # sprint_id with embedded quote round-trips correctly.
    assert parsed["sprint_id"] == "sprint's-001"


def test_benchmark_report_pyyaml_safe(tmp_path):
    """Regression: benchmark-report.md parses with PyYAML after WR-01 fix."""
    from clawteam.templates.gstack.schemas.benchmark_report import BenchmarkReport
    from clawteam.templates.gstack.skills.benchmark.handler import (
        _render_report_yaml,
    )

    schema = BenchmarkReport(
        artifact_type="benchmark-report",
        benchmark_status="clean",
        lcp_ms=1234.0,
        fid_ms=80.0,
        cls_score=0.05,
        ttfb_ms=150.0,
        dom_loaded_ms=100.0,
        regression_flags=[],
        measured_with="lighthouse",
        sprint_id="a'b",
        created_at="2025-01-01T00:00:00+00:00",
    )
    out = _render_report_yaml(schema)

    pyyaml = pytest.importorskip("yaml")
    assert out.startswith("---\n")
    end = out.find("\n---", 4)
    assert end != -1
    inner = out[4:end]
    parsed = pyyaml.safe_load(inner)
    assert parsed["sprint_id"] == "a'b"
