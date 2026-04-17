"""ReviewRouter Protocol forward-declaration (RFC 001 §4.3b).

Phase 1 locks only the hook point. The full interface — rule-file format,
SHA-pinning semantics, multi-signal aggregation, decorrelation rules — is
specified by a future Phase 4 RFC. Plugins that need review-time routing
under Phase 1 can implement this Protocol, but the harness does not yet
consume the routers (consumption lands with Phase 4's Review-phase wiring).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from clawteam.sprint.state import SprintState


class ReviewRouter(Protocol):
    """Rule that picks additional reviewer roles based on the diff.

    The only observable Phase 1 contract is the method signature below.
    Routers are consulted in plugin load order by `contribute_review_routers()`
    and return an ordered list of AgentRole entries to append to the
    Review-phase participant set.
    """

    def match(self, diff_paths: list[str], state: "SprintState") -> list[str]:
        """Return additional reviewer role names for this diff.

        An implementation raising from match() is skipped with a logged
        warning (per RFC 001 §4.3b req 4). Returning an empty list is
        the explicit "no additional reviewers" signal.
        """
        ...
