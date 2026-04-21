"""qa ↔ engineer cross-verifier: test-report must reference engineer's diff files.

§04-CONTEXT D-11. Defeats Pitfall 8 gate-gaming extension: qa cannot write
a test-report citing pytest output on files engineer never touched.

Contract:
    (ok, reason) = verify_test_report_matches_engineer_output(test_report, engineer_output)

Where ``test_report`` is a TestReport pydantic instance and
``engineer_output`` is a pydantic instance with a ``files_changed`` / ``diff_summary``
attribute listing paths engineer modified or added. The verifier checks that
at least one file name from engineer's diff appears in test_report.test_command
or test_report's files_tested field (if present).

If Phase 3's build-report / engineer output schema differs, the verifier
falls back gracefully (accesses via getattr with sensible defaults).
"""

from __future__ import annotations

from typing import Any


def verify_test_report_matches_engineer_output(
    test_report: Any,
    engineer_output: Any,
) -> tuple[bool, str]:
    """Return (ok, reason)."""
    # Extract engineer diff file list (tolerant of schema variations).
    diff_files: list[str] = []
    for attr in ("files_changed", "diff_files", "files_added", "diff_summary"):
        val = getattr(engineer_output, attr, None)
        if val:
            if isinstance(val, list):
                diff_files.extend(str(p) for p in val)
            elif isinstance(val, str):
                diff_files.extend(
                    [line.strip() for line in val.splitlines() if line.strip()]
                )

    if not diff_files:
        return False, (
            "cross-verify: engineer diff summary is empty; cannot confirm "
            "test-report references actual engineer changes"
        )

    # Extract test-report evidence (test_command + files_tested).
    test_command = str(getattr(test_report, "test_command", "") or "")
    files_tested = getattr(test_report, "files_tested", None) or []
    if not isinstance(files_tested, list):
        files_tested = []
    files_tested_str = [str(p) for p in files_tested]

    search_corpus = test_command + " " + " ".join(files_tested_str)

    # Any engineer diff file (or its basename, or stem) must appear in the corpus.
    for path in diff_files:
        basename = path.rsplit("/", 1)[-1]
        # Stem = basename without final extension (handles "pytest -k test_user"
        # vs diff entry "a/b/test_user.py" — covers the basename-without-suffix
        # case that fnmatch would otherwise miss).
        stem = basename.rsplit(".", 1)[0] if "." in basename else basename
        if (
            path in search_corpus
            or basename in search_corpus
            or (stem and stem in search_corpus)
        ):
            return True, ""

    return False, (
        f"cross-verify: test-report (test_command={test_command!r}, "
        f"files_tested={files_tested_str}) references none of engineer's "
        f"{len(diff_files)} modified file(s): {diff_files[:5]}"
        f"{'...' if len(diff_files) > 5 else ''}"
    )
