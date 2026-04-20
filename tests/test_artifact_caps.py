"""Tests for ArtifactStore.write() Phase 2 hook chain (Plan 02-06).

Covers:
  1. Size-cap enforcement (D-27) via ArtifactTooLargeError.
  2. BeforeFileWrite event emission and veto -> FrozenPathError (SAFETY-02).
  3. Backwards-compatible constructor (Pitfall #8).
  4. Write-path does NOT parse frontmatter (Pitfall #8 invariant — upstream-PR viability).
  5. Constructor cap kwarg override semantics (D-29 single-layer slice).
"""

from __future__ import annotations

import pytest

from clawteam.events.global_bus import get_event_bus, reset_event_bus
from clawteam.events.types import BeforeFileWrite
from clawteam.harness.artifacts import ArtifactStore
from clawteam.harness.errors import ArtifactTooLargeError

# FrozenPathError ships in clawteam/harness/freeze_registry.py per Plan 02-05
# (same wave as this plan). When Plan 02-05 has landed, we import the real
# error class; otherwise we fall back to ValueError, which matches the
# production code's lazy-import fallback in ArtifactStore.write (so the veto
# path raises ValueError in both scenarios — FrozenPathError *is* a
# ValueError subclass by design, so the test assertion still holds).
try:
    from clawteam.harness.freeze_registry import FrozenPathError
except ImportError:  # Plan 02-05 not yet merged into this worktree.
    FrozenPathError = ValueError  # type: ignore[misc,assignment]


@pytest.fixture
def fresh_bus():
    """Reset the global event bus between tests so subscribers don't leak."""
    reset_event_bus()
    yield get_event_bus()
    reset_event_bus()


def test_write_under_cap_succeeds(tmp_path, fresh_bus):
    store = ArtifactStore(tmp_path, "team", "harness", artifact_cap_bytes=100)
    out = store.write("spec.md", "hello")
    assert out.exists()
    assert out.read_text(encoding="utf-8") == "hello"


def test_write_over_per_file_cap_raises_artifact_too_large(tmp_path, fresh_bus):
    store = ArtifactStore(tmp_path, "team", "harness", artifact_cap_bytes=100)
    with pytest.raises(ArtifactTooLargeError) as exc_info:
        store.write("big.md", "x" * 200)
    msg = str(exc_info.value)
    assert "big.md" in msg
    assert "200" in msg
    assert "100" in msg
    assert "split" in msg.lower()


def test_write_without_explicit_cap_uses_none_default_and_no_check(tmp_path, fresh_bus):
    # BC path — existing templates construct without cap and write large artifacts.
    store = ArtifactStore(tmp_path, "team", "harness")
    out = store.write("huge.md", "x" * 1_000_000)
    assert out.exists()
    assert out.stat().st_size == 1_000_000


def test_write_emits_before_file_write_event(tmp_path, fresh_bus):
    captured: list[BeforeFileWrite] = []
    fresh_bus.subscribe(BeforeFileWrite, lambda e: captured.append(e))
    store = ArtifactStore(tmp_path, "team", "harness")
    store.write("foo.md", "hello")
    assert len(captured) == 1
    assert captured[0].path.endswith("foo.md")
    assert captured[0].size_bytes == 5


def test_write_raises_frozen_path_error_when_event_vetoed(tmp_path, fresh_bus):
    def veto_handler(evt: BeforeFileWrite) -> None:
        evt.veto = True
        evt.veto_reason = "blocked by /freeze /tmp"

    fresh_bus.subscribe(BeforeFileWrite, veto_handler)
    store = ArtifactStore(tmp_path, "team", "harness")
    with pytest.raises(FrozenPathError) as exc_info:
        store.write("x.md", "x")
    assert "blocked by /freeze" in str(exc_info.value)


def test_write_does_not_parse_frontmatter_pitfall8(tmp_path, fresh_bus):
    """Upstream-PR-viability invariant: write-path does NOT validate frontmatter.

    A hedge-fund or software-dev template may hand us a markdown file with a
    minimal frontmatter block that does NOT include `step_label` (required
    only by gstack's TurnEnvelope, validated in Plan 02-07's EvidenceGate).
    The write-path must pass this through untouched — no YAML parsing at all.
    """
    store = ArtifactStore(tmp_path, "team", "harness")
    content = "---\npersona: engineer\ndone: false\n---\nbody content\n"
    out = store.write("artifact.md", content)
    assert out.read_text(encoding="utf-8") == content


def test_write_preserves_existing_signature(tmp_path, fresh_bus):
    # BC: three-arg constructor + (name, content, metadata) write still works.
    store = ArtifactStore(tmp_path, "team", "harness")
    out = store.write("spec.md", "content", {"type": "specification", "phase": "plan"})
    assert out.exists()
    meta_path = tmp_path / "team" / "harness" / "artifacts" / "spec.md.meta.json"
    assert meta_path.exists()


def test_write_cap_three_layer_override_highest_wins(tmp_path, fresh_bus, monkeypatch):
    """D-29 slice for Plan 02-06: constructor-level resolution.

    Full 3-layer resolution (env + SprintState + constructor) lives in
    Plan 02-11 (SprintConductor); this plan's ArtifactStore receives the
    already-resolved cap via the constructor kwarg. Here we exercise the
    endpoints of that contract: no-cap => no check; cap set => cap wins.
    """
    # (a) No cap source -> no cap applied, large writes succeed.
    monkeypatch.delenv("CLAWTEAM_ARTIFACT_CAP_KB", raising=False)
    store_a = ArtifactStore(tmp_path / "a", "t", "h")
    store_a.write("ok.md", "x" * 200_000)  # no cap -> succeeds

    # (b) Env set, but constructor kwarg wins regardless of env value.
    monkeypatch.setenv("CLAWTEAM_ARTIFACT_CAP_KB", "10")  # 10 KB if env were consulted
    store_b = ArtifactStore(tmp_path / "b", "t", "h", artifact_cap_bytes=100)  # 100 bytes
    with pytest.raises(ArtifactTooLargeError):
        store_b.write("big.md", "x" * 200)
