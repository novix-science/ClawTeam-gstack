"""reviewer ↔ designer cross-verifier: design-doc covers all 6 /office-hours forcing Qs.

§04-CONTEXT D-11. Reviewer verifies designer's design-doc.md maps to all 6
pm/`/office-hours` forcing questions by presence check on question ids
(not prose matching). DesignDoc schema already enforces min_length=6/max_length=6
on forcing_questions_addressed (Phase 3 Plan 03-03); this verifier adds the
semantic "values are exactly [1..6]" check.

Contract:
    (ok, reason) = verify_design_doc_covers_forcing_questions(design_doc, office_hours_state)

Where ``design_doc`` is a DesignDoc pydantic instance and
``office_hours_state`` can be either an OfficeHoursState instance OR a
separate artifact (we use design_doc's forcing_questions_addressed list
directly; office_hours_state is passed for future extensions like
matching question wording). The verifier's current check is on design_doc
alone — it returns True iff forcing_questions_addressed == sorted({1,2,3,4,5,6}).
"""

from __future__ import annotations

from typing import Any


_EXPECTED_QUESTION_IDS: frozenset[int] = frozenset({1, 2, 3, 4, 5, 6})


def verify_design_doc_covers_forcing_questions(
    design_doc: Any,
    office_hours_state: Any,
) -> tuple[bool, str]:
    """Return (ok, reason)."""
    del office_hours_state  # reserved for future prose-matching extension

    # Use sentinel so we can distinguish "attribute missing" from "= None".
    _sentinel = object()
    covered = getattr(design_doc, "forcing_questions_addressed", _sentinel)
    if covered is _sentinel or covered is None:
        return False, (
            "cross-verify: design-doc frontmatter lacks forcing_questions_addressed field"
        )
    if not isinstance(covered, list):
        return False, (
            f"cross-verify: forcing_questions_addressed expected list, got "
            f"{type(covered).__name__}"
        )

    covered_set: set[int] = set()
    for v in covered:
        # bool is a subclass of int but conceptually non-integer here.
        if isinstance(v, bool):
            return False, f"cross-verify: non-integer question id {v!r}"
        try:
            covered_set.add(int(v))
        except (ValueError, TypeError):
            return False, f"cross-verify: non-integer question id {v!r}"

    if len(covered) != len(covered_set):
        return False, (
            f"cross-verify: forcing_questions_addressed contains duplicates: {covered}"
        )

    if covered_set != _EXPECTED_QUESTION_IDS:
        missing = _EXPECTED_QUESTION_IDS - covered_set
        extra = covered_set - _EXPECTED_QUESTION_IDS
        parts = []
        if missing:
            parts.append(f"missing Q{sorted(missing)}")
        if extra:
            parts.append(f"out-of-range {sorted(extra)}")
        return False, (
            f"cross-verify: design-doc forcing_questions_addressed mismatch "
            f"expected [1..6]: {', '.join(parts)}"
        )

    return True, ""
