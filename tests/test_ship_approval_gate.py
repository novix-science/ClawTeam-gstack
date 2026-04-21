"""Unit tests for clawteam/harness/ship_approval_gate.py (Plan 04-04)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from clawteam.harness.ship_approval_gate import ShipApprovalGate


_GOOD_SHA = "a1b2c3d4e5f6" + "0" * 28  # 40 chars

_GOOD_APPROVAL = f"""---
artifact_type: ship_approval
approved_by: alice@example.com
approved_at: 2026-04-21T14:32:00+00:00
sha_at_approval: {_GOOD_SHA}
approval_notes: LGTM
---

# Ship approval
Approved.
"""

_APPROVAL_MISSING_APPROVED_BY = f"""---
artifact_type: ship_approval
approved_at: 2026-04-21T14:32:00+00:00
sha_at_approval: {_GOOD_SHA}
---
body
"""

_APPROVAL_MISSING_APPROVED_AT = f"""---
artifact_type: ship_approval
approved_by: alice
sha_at_approval: {_GOOD_SHA}
---
body
"""

_APPROVAL_MISSING_SHA = """---
artifact_type: ship_approval
approved_by: alice
approved_at: 2026-04-21T14:32:00+00:00
---
body
"""

_APPROVAL_BAD_SHA = """---
artifact_type: ship_approval
approved_by: alice
approved_at: 2026-04-21T14:32:00+00:00
sha_at_approval: deadbeefdeadbeefdeadbeefdeadbeefdeadbeef
---
body
"""

_APPROVAL_MALFORMED = "no frontmatter here at all"


def _make_state(
    *,
    artifacts: dict | None = None,
    auto_advance: bool = True,
    review_sha: str | None = None,
    sprint_id: str = "abc12345",
):
    return SimpleNamespace(
        artifacts=artifacts or {},
        auto_advance=auto_advance,
        review_sha=review_sha,
        sprint_id=sprint_id,
    )


def test_passes_when_interaction_ok_and_approval_valid():
    gate = ShipApprovalGate()
    state = _make_state(
        artifacts={"ship-approval.md": _GOOD_APPROVAL},
        auto_advance=True,
        review_sha=_GOOD_SHA,
    )
    assert gate.check(state) == (True, "")


def test_blocks_when_approval_missing():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={}, auto_advance=True)
    ok, reason = gate.check(state)
    assert ok is False
    assert "ship-approval.md missing" in reason
    assert "clawteam sprint approve" in reason  # CLI hint


def test_blocks_when_approved_by_missing():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={"ship-approval.md": _APPROVAL_MISSING_APPROVED_BY})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing required field: approved_by" in reason


def test_blocks_when_approved_at_missing():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={"ship-approval.md": _APPROVAL_MISSING_APPROVED_AT})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing required field: approved_at" in reason


def test_blocks_when_sha_at_approval_missing():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={"ship-approval.md": _APPROVAL_MISSING_SHA})
    ok, reason = gate.check(state)
    assert ok is False
    assert "missing required field: sha_at_approval" in reason


def test_blocks_when_sha_mismatch():
    gate = ShipApprovalGate()
    state = _make_state(
        artifacts={"ship-approval.md": _APPROVAL_BAD_SHA},
        review_sha=_GOOD_SHA,
    )
    ok, reason = gate.check(state)
    assert ok is False
    assert "HEAD advanced" in reason or "does not match" in reason
    assert "re-approval" in reason


def test_passes_when_review_sha_unset():
    gate = ShipApprovalGate()
    state = _make_state(
        artifacts={"ship-approval.md": _GOOD_APPROVAL},
        review_sha=None,
    )
    # review_sha unset → Layer 4 skipped; layers 1-3 all pass.
    assert gate.check(state) == (True, "")


def test_ignores_auto_advance():
    """SPRINT-05: auto_advance=True is irrelevant when approval missing."""
    gate = ShipApprovalGate()
    state = _make_state(artifacts={}, auto_advance=True)
    ok, reason = gate.check(state)
    assert ok is False
    assert "ship-approval.md missing" in reason
    # And with approval present + auto_advance=True: passes.
    state2 = _make_state(
        artifacts={"ship-approval.md": _GOOD_APPROVAL},
        auto_advance=True,
        review_sha=_GOOD_SHA,
    )
    assert gate.check(state2) == (True, "")


def test_malformed_frontmatter_blocks():
    gate = ShipApprovalGate()
    state = _make_state(artifacts={"ship-approval.md": _APPROVAL_MALFORMED})
    ok, reason = gate.check(state)
    assert ok is False
    # Either malformed detection or "missing approved_by" depending on parse_frontmatter behavior.
    assert "ship-approval.md" in reason


def test_custom_artifact_name():
    gate = ShipApprovalGate(ship_approval_artifact="custom-ship-approval.md")
    state = _make_state(
        artifacts={"custom-ship-approval.md": _GOOD_APPROVAL},
        review_sha=_GOOD_SHA,
    )
    assert gate.check(state) == (True, "")


def test_inherits_from_interaction_gate():
    from clawteam.harness.interaction_gate import InteractionGate
    assert issubclass(ShipApprovalGate, InteractionGate)
