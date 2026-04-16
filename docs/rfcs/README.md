# RFCs

Design proposals for upstream-bound changes to the ClawTeam harness. Each RFC
targets a specific phase in the v1 gstack-integration roadmap and documents the
additive-only contract that keeps existing templates (`software-dev.toml`,
`hedge-fund.toml`, `code-review.toml`, `harness-default.toml`,
`research-paper.toml`, `strategy-room.toml`) unchanged.

## Process

1. **Draft**: Author writes an RFC using the Rust-style template. RFC 001 is the
   canonical example for this repository.
2. **Review**: The RFC is opened against the upstream ClawTeam repository. The
   target outcome is at least one maintainer acknowledgement before the
   companion implementation lands.
3. **Accepted**: Status changes from `Draft` to `Accepted`; implementation work
   references the RFC number directly.
4. **Rejected**: Status changes to `Rejected` with rationale captured in the RFC.

This mirror under `docs/rfcs/` stays authoritative for the fork even if the
upstream discussion is still open.

## Index

| # | Title | Status | Target Phase |
|---|-------|--------|--------------|
| [001](001-phase-registry.md) | PhaseRegistry + HarnessPlugin.contribute_phases + SprintState + InteractionGate | Draft | Phase 1 |
