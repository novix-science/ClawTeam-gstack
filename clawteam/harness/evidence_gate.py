"""EvidenceGate — 4-check protocol extending ArtifactRequiredGate.

§02-CONTEXT D-01..D-05. §02-RESEARCH §Pattern 3. Phase 2 ships the gate class;
Phase 3's ``GstackSprintPlugin`` registers the six gstack artifact schemas and
binds the gate to each of the 7 phases.

Existing templates keep using ``ArtifactRequiredGate`` — ``EvidenceGate`` is
opt-in via plugin (Pitfall #8 invariant; §02-CONTEXT §domain "out of scope").

Four-check protocol per artifact:
1. Presence (inherited from :class:`ArtifactRequiredGate`).
2. Frontmatter YAML parse + pydantic validation via
   :func:`clawteam.harness.evidence_schemas.get_schema` (Plan 02-04).
3. Stub detection: required ``## Section`` body ≤ 100 bytes + regex
   blacklist on the body (TBD / TODO / xxx+ / placeholder / Lorem ipsum).
4. Post-check dispatch (keyed on ``artifact_type``):
   - ``test-report`` → :meth:`EvidenceGate._run_test_command` runs
     ``test_command`` via ``subprocess.run`` (shell=False, cwd=workspace,
     300 s timeout) with a SHA256 content-hash cache.
   - ``ship-notes`` → :meth:`EvidenceGate._check_deploy_url` HEAD-probes
     ``deploy_url`` with a 10 s timeout (via an injectable checker).
After all per-artifact checks, a per-phase artifact-cap check runs
(§02-CONTEXT D-28) against :attr:`SprintState.phase_artifact_cap_bytes`.

Injection seams (Pitfall #10 / T-02-01 residual-SSRF contract):
- ``subprocess_runner``: default is stdlib ``subprocess.run`` with
  ``shell=False``. Tests inject a fake to avoid real command execution.
- ``deploy_url_checker``: default is stdlib ``urllib.request`` HEAD probe.
  Tests inject a fake for CI offline safety; Phase 5 ``/ship`` will inject
  an allowlist-checker wrapper around the default (T-02-01 mitigation
  contract — do NOT remove this seam; SSRF is deliberately un-mitigated
  in Phase 2 until the allowlist ships).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from clawteam.fileutil import atomic_write_text, file_locked
from clawteam.harness.evidence_schemas import get_schema
from clawteam.harness.phases import ArtifactRequiredGate
from clawteam.team.envelope import MalformedEnvelopeError, parse_frontmatter
from clawteam.team.models import get_data_dir

# ── Stub detection constants (§02-CONTEXT D-03) ────────────────────────────

STUB_REGEX_BLACKLIST: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bTBD\b", re.IGNORECASE), "TBD"),
    (re.compile(r"\bTODO\b"), "TODO"),
    (re.compile(r"\bxxx+\b", re.IGNORECASE), "xxx"),
    (re.compile(r"\bplaceholder\b", re.IGNORECASE), "placeholder"),
    (re.compile(r"Lorem ipsum", re.IGNORECASE), "Lorem ipsum"),
]

STUB_MIN_SECTION_BYTES = 100
TEST_COMMAND_TIMEOUT_SECONDS = 300
DEPLOY_URL_HEAD_TIMEOUT_SECONDS = 10


# ── Default injectable helpers (tests override; see module docstring) ─────


def _default_head_check(
    url: str, timeout: int = DEPLOY_URL_HEAD_TIMEOUT_SECONDS
) -> tuple[int, dict]:
    """Stdlib HTTP HEAD probe — default ``deploy_url_checker``.

    Returns ``(status_code, headers_dict)``. Pitfall #10: tests MUST inject a
    fake. Phase 5 ``/ship`` will compose an allowlist-checker wrapper around
    this to mitigate T-02-01 (residual SSRF vector until allowlist ships).
    """
    from urllib.request import Request, urlopen

    req = Request(url, method="HEAD")  # noqa: S310 — T-02-01 residual (Phase 5 mitigates)
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.status, dict(resp.headers)


def _default_subprocess_runner(
    cmd: list[str], cwd: str, timeout: int
) -> subprocess.CompletedProcess:
    """Stdlib ``subprocess.run`` — default test-command runner.

    Pitfall #4 / T-02-03: ``shell=False`` + explicit ``cwd`` + ``timeout``;
    no shell interpretation of ``;``, ``&&``, ``|``, ``$()``. Callers pass
    the command as a list produced by ``str.split()`` (stricter than
    ``shlex.split`` — quoted payloads cannot inject arguments).
    """
    return subprocess.run(  # noqa: S603 — shell=False + timeout per T-02-03 mitigation
        cmd,
        cwd=cwd,
        timeout=timeout,
        shell=False,
        capture_output=True,
        text=True,
    )


def detect_stub(body: str, required_sections: list[str]) -> str | None:
    """3-layer stub detection (§02-CONTEXT D-03).

    Layer 3 (blacklist) runs first — it emits the line number which is useful
    operator context even if a section is also sub-threshold.

    Layer 2 (required ## section body ≤ 100 bytes) runs second.

    Returns ``None`` on pass; returns a reason string on fail.
    """
    # Layer 3: blacklist (line-number lookup first — cheap + useful).
    for regex, name in STUB_REGEX_BLACKLIST:
        m = regex.search(body)
        if m:
            line_num = body[: m.start()].count("\n") + 1
            return f"blacklisted marker '{name}' at line {line_num}"

    # Layer 2: each required ## section must have > STUB_MIN_SECTION_BYTES body.
    for section in required_sections:
        pattern = re.compile(
            rf"^##\s+{re.escape(section)}\s*\n(.*?)(?=\n##\s|\Z)",
            re.DOTALL | re.MULTILINE,
        )
        m = pattern.search(body)
        if not m:
            return f"required section '## {section}' missing"
        section_body = m.group(1).strip()
        if len(section_body.encode("utf-8")) <= STUB_MIN_SECTION_BYTES:
            return f"'## {section}': stub section ≤ {STUB_MIN_SECTION_BYTES} bytes"

    return None


# ── Gate class ─────────────────────────────────────────────────────────────


class EvidenceGate(ArtifactRequiredGate):
    """4-check protocol: presence → frontmatter → stub → post-check.

    Opt-in via Phase 3 ``GstackSprintPlugin``; existing templates (software-dev,
    hedge-fund, etc.) keep using :class:`ArtifactRequiredGate` unchanged.
    """

    def __init__(
        self,
        artifact_names: list[str],
        *,
        required_sections: dict[str, list[str]] | None = None,
        deploy_url_checker: Callable[[str, int], tuple[int, dict]] | None = None,
        subprocess_runner: Callable[..., subprocess.CompletedProcess] | None = None,
    ) -> None:
        super().__init__(artifact_names)
        self._required_sections = required_sections or {}
        self._head_check = deploy_url_checker or _default_head_check
        self._subprocess_run = subprocess_runner or _default_subprocess_runner

    # The ``state`` argument is duck-typed to :class:`SprintState` (Plan 02-03);
    # the base :class:`PhaseState` also satisfies the contract used here.
    def check(self, state) -> tuple[bool, str]:  # type: ignore[override]
        # Layer 1: presence — inherited (returns "Missing artifacts: ..." reason).
        ok, reason = super().check(state)
        if not ok:
            return ok, reason

        for name in self.artifact_names:
            raw = state.artifacts.get(name, "")

            # Layer 2: frontmatter parse + schema dispatch.
            try:
                meta, body = parse_frontmatter(raw)
            except MalformedEnvelopeError as exc:
                return False, f"{name}: {exc}"

            atype = meta.get("artifact_type", "")
            if not atype:
                return False, f"{name}: frontmatter missing artifact_type"

            schema_cls = get_schema(atype)
            if schema_cls is None:
                return False, (
                    f"{name}: Unregistered artifact_type {atype!r}. Phase 3 plugin must register."
                )

            try:
                schema_cls.model_validate(meta)
            except Exception as exc:
                return False, f"{name}: frontmatter invalid: {exc}"

            # Layer 3: stub detection (sections + blacklist).
            stub_issue = detect_stub(body, self._required_sections.get(name, []))
            if stub_issue:
                return False, f"{name}: {stub_issue}"

            # Layer 4: post-check dispatch (test_command / deploy_url).
            post_ok, post_reason = self._post_check(name, meta, body, state)
            if not post_ok:
                return False, post_reason

        # Layer 4b: per-phase artifact-cap check (§02-CONTEXT D-28).
        phase_cap = getattr(state, "phase_artifact_cap_bytes", None)
        if phase_cap:
            total = sum(len(v.encode("utf-8")) for v in state.artifacts.values())
            if total > phase_cap:
                return False, (
                    f"phase cap exceeded: {total} bytes > {phase_cap} bytes. "
                    f"Suggestion: artifact_compaction — "
                    f"[A: discard, B: raise cap, C: split phase]."
                )

        return True, ""

    # ── Dispatch ───────────────────────────────────────────────────────

    def _post_check(self, name: str, meta: dict, body: str, state) -> tuple[bool, str]:
        """Dispatch per-artifact post-checks (§02-CONTEXT D-04, D-05)."""
        atype = meta.get("artifact_type", "")
        if atype == "test-report":
            return self._run_test_command(name, meta, state)
        if atype == "ship-notes":
            return self._check_deploy_url(name, meta)
        return True, ""

    # ── test_command re-run + cache (§02-CONTEXT D-04) ────────────────

    def _run_test_command(self, name: str, meta: dict, state) -> tuple[bool, str]:
        cmd_str = meta.get("test_command", "")
        if not cmd_str:
            return False, f"{name}: frontmatter missing test_command"

        artifact_body = state.artifacts.get(name, "")
        content_hash = hashlib.sha256(artifact_body.encode("utf-8")).hexdigest()

        cache = self._load_test_verify_cache(state)
        cache_key = f"{name}:{cmd_str}"
        cache_entry = cache.get(cache_key)
        if (
            cache_entry
            and cache_entry.get("artifact_hash") == content_hash
            and cache_entry.get("last_exit_code") == 0
        ):
            return True, ""

        cmd_parts = cmd_str.split()
        try:
            completed = self._subprocess_run(
                cmd_parts,
                cwd=state.workspace_branch or ".",
                timeout=TEST_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return False, (f"{name}: test_command timed out after {TEST_COMMAND_TIMEOUT_SECONDS}s")

        entry = {
            "artifact_hash": content_hash,
            "test_command": cmd_str,
            "last_run_at": datetime.now(timezone.utc).isoformat(),
            "last_exit_code": completed.returncode,
        }
        cache[cache_key] = entry
        self._save_test_verify_cache(state, cache)

        if completed.returncode != 0:
            # T-02-18 (accepted): stderr tail may leak secrets; v1 accepts this.
            err_lines = (completed.stderr or "").strip().splitlines()
            tail = err_lines[-1] if err_lines else ""
            return False, (f"{name}: test_command exited with code {completed.returncode}: {tail}")

        return True, ""

    # ── test_verify_cache.json persistence (§02-CONTEXT D-04) ─────────

    def _cache_path(self, state) -> Path:
        return (
            get_data_dir()
            / "teams"
            / state.team
            / "sprints"
            / state.sprint_id
            / "test_verify_cache.json"
        )

    def _load_test_verify_cache(self, state) -> dict:
        p = self._cache_path(state)
        if not p.exists():
            return {}
        with file_locked(p):
            return json.loads(p.read_text(encoding="utf-8"))

    def _save_test_verify_cache(self, state, cache: dict) -> None:
        p = self._cache_path(state)
        p.parent.mkdir(parents=True, exist_ok=True)
        with file_locked(p):
            atomic_write_text(p, json.dumps(cache, indent=2, ensure_ascii=False))

    # ── deploy_url HEAD dereference (§02-CONTEXT D-05) ────────────────

    def _check_deploy_url(self, name: str, meta: dict) -> tuple[bool, str]:
        url = meta.get("deploy_url", "")
        if not url:
            return False, f"{name}: frontmatter missing deploy_url"
        try:
            status, _headers = self._head_check(url, DEPLOY_URL_HEAD_TIMEOUT_SECONDS)
        except Exception as exc:
            return False, f"{name}: deploy_url unreachable: {exc}"
        if not (200 <= status < 400):
            return False, f"{name}: deploy_url returned HTTP {status}"
        return True, ""
