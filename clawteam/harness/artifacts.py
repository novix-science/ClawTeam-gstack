"""Artifact storage for structured handoff between harness phases.

Phase 2 extension (Plan 02-06): the write path gains a pre-write hook chain:

    1. Size-cap check (D-27)  -> raise ArtifactTooLargeError on overflow.
    2. BeforeFileWrite emit   -> subscribers (Plan 02-10 freeze / careful) can veto.
       On veto: raise FrozenPathError(reason).
    3. Atomic write           -> existing behavior preserved (BC guarantee).

Pitfall #8 invariant (see 02-RESEARCH.md): the hook chain is content-agnostic.
No structured-header parsing, no schema validation, no content inspection at
write time. Header / envelope validation is scope-limited to
``EvidenceGate.check()`` (Plan 02-07) and applies only to gstack-sprint
artifacts; existing templates (software-dev, hedge-fund, code-review,
harness-default, research-paper, strategy-room) that write plain markdown must
continue to succeed unmodified — enforced by
``tests/test_template_regression_matrix.py`` (SC#10).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from clawteam.events.global_bus import get_event_bus
from clawteam.events.types import BeforeFileWrite
from clawteam.harness.errors import ArtifactTooLargeError


def _resolve_frozen_path_error() -> type[BaseException] | None:
    """Resolve ``FrozenPathError`` lazily to tolerate Wave 2 parallel execution.

    ``FrozenPathError`` ships in ``clawteam/harness/freeze_registry.py`` per
    Plan 02-05 (same wave as Plan 02-06). When Plan 02-05 has landed, the
    import succeeds and callers raise the structured error; otherwise we
    return ``None`` and the caller falls back to a generic ``ValueError``
    (which ``FrozenPathError`` subclasses by design, so downstream
    ``except ValueError`` blocks behave identically in both states).
    """
    try:
        from clawteam.harness.freeze_registry import FrozenPathError

        return FrozenPathError
    except Exception:  # pragma: no cover — Plan 02-05 may land in parallel
        return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_artifact_name(name: str) -> None:
    """Reject absolute paths and ``..`` traversal in artifact names (T-02-02 guard).

    ``self._dir / name`` uses ``Path.__truediv__`` which does NOT escape an
    absolute right-hand operand: ``Path('/tmp/a') / '/etc/shadow'`` resolves
    to ``/etc/shadow``. Validate at the top of ``write()`` so untrusted
    artifact names cannot escape the per-harness directory.
    """
    parts = Path(name).parts
    if Path(name).is_absolute() or ".." in parts:
        raise ValueError(
            f"invalid artifact name: {name!r} (absolute paths and .. segments rejected)"
        )


class ArtifactStore:
    """File-based artifact storage for harness phases."""

    def __init__(
        self,
        base_dir: Path,
        team_name: str,
        harness_id: str,
        *,
        artifact_cap_bytes: int | None = None,
    ) -> None:
        """Construct a per-team/per-harness artifact directory.

        ``artifact_cap_bytes`` is keyword-only (additive kwarg preserves BC —
        existing three-arg call sites in software-dev/hedge-fund templates
        continue to work). ``None`` means no cap (BC default).
        """
        self._dir = base_dir / team_name / harness_id / "artifacts"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cap = artifact_cap_bytes
        self._team_name = team_name  # surfaced to BeforeFileWrite.team_name

    def write(self, name: str, content: str, metadata: dict[str, Any] | None = None) -> Path:
        """Write an artifact file through the Phase 2 hook chain. Returns the path.

        Hook order (short-circuit on first rejection per §02-RESEARCH):
          0. Name validation (T-02-02 guard).
          1. Size cap (D-27)     -> raise ArtifactTooLargeError if over cap.
          2. BeforeFileWrite emit -> raise FrozenPathError if a subscriber vetoes.
          3. Atomic write         -> ``path.write_text`` (existing behavior).

        Pitfall #8 invariant (02-RESEARCH.md): this method is content-agnostic
        — no structured-header parsing, no schema validation, no content
        inspection. Existing templates that pass plain markdown (or markdown
        whose header block lacks ``step_label``) write successfully. Gstack
        envelope validation lives in ``EvidenceGate.check()`` (Plan 02-07),
        scoped to gstack sprints.
        """
        _validate_artifact_name(name)

        size_bytes = len(content.encode("utf-8"))

        # ── Hook 1: size cap (D-27) ──────────────────────────────────────
        if self._cap is not None and size_bytes > self._cap:
            stem = Path(name).stem
            suffix = Path(name).suffix
            suggestion = f"split into {stem}-part1{suffix} etc. or raise cap via --artifact-cap"
            raise ArtifactTooLargeError(
                f"{name}: {size_bytes} bytes exceeds per-file cap of {self._cap} bytes. "
                f"Suggestion: {suggestion}"
            )

        # ── Hook 2: BeforeFileWrite event emit + veto check (SAFETY-02) ──
        path = self._dir / name
        agent_name = ""
        if metadata:
            agent_name = str(metadata.get("agent", ""))

        event = BeforeFileWrite(
            team_name=self._team_name,
            agent_name=agent_name,
            path=str(path),
            size_bytes=size_bytes,
        )
        try:
            get_event_bus().emit(event)
        except Exception:
            # EventBus.emit already swallows subscriber crashes; this guards
            # against the bus itself failing to initialize (e.g. broken
            # config). Never let an infrastructure failure abort the write
            # path — fall through without veto.
            event.veto = False
        if event.veto:
            reason = event.veto_reason or f"{path} is vetoed by safety-rail subscriber"
            frozen_cls = _resolve_frozen_path_error()
            if frozen_cls is not None:
                raise frozen_cls(reason)
            # Fallback when Plan 02-05 hasn't shipped yet — preserve the
            # ValueError subclass shape (FrozenPathError subclasses
            # ValueError by design) so ``except ValueError`` clauses still
            # match the veto path.
            raise ValueError(reason)

        # ── Hook 3: atomic write (existing behavior preserved) ──────────
        path.write_text(content, encoding="utf-8")
        if metadata:
            meta_path = self._dir / f"{name}.meta.json"
            meta_path.write_text(
                json.dumps({**metadata, "written_at": _now_iso()}, indent=2),
                encoding="utf-8",
            )
        return path

    def read(self, name: str) -> str | None:
        """Read an artifact file. Returns None if not found."""
        path = self._dir / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
        return None

    def exists(self, name: str) -> bool:
        return (self._dir / name).is_file()

    def list_artifacts(self) -> list[dict[str, Any]]:
        """List all artifacts with metadata."""
        result = []
        for path in sorted(self._dir.iterdir()):
            if path.name.endswith(".meta.json"):
                continue
            entry: dict[str, Any] = {
                "name": path.name,
                "size": path.stat().st_size,
            }
            meta_path = self._dir / f"{path.name}.meta.json"
            if meta_path.is_file():
                try:
                    entry["metadata"] = json.loads(meta_path.read_text(encoding="utf-8"))
                except Exception:
                    pass
            result.append(entry)
        return result

    # ── Convenience methods for common artifact types ──

    def write_spec(self, content: str) -> Path:
        """Write the plan specification."""
        return self.write("spec.md", content, {"type": "specification", "phase": "plan"})

    def write_sprint_contract(self, contract_id: str, content: str) -> Path:
        """Write a sprint contract."""
        return self.write(
            f"sprint-contract-{contract_id}.json",
            content,
            {"type": "sprint_contract", "phase": "plan"},
        )

    def write_evaluation(self, content: str) -> Path:
        """Write evaluation results."""
        return self.write("eval-report.json", content, {"type": "evaluation", "phase": "verify"})

    def write_ship_manifest(self, content: str) -> Path:
        """Write the ship manifest."""
        return self.write("ship-manifest.json", content, {"type": "manifest", "phase": "ship"})
