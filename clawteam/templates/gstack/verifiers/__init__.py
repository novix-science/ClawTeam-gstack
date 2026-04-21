"""Gstack cross-agent verifier functions (§04-CONTEXT D-11 — Plan 04-11).

Called by CrossAgentVerificationGate (Plan 04-03) with pydantic-validated
artifact models. Plugin-registered via GstackSprintPlugin.contribute_verification_pairs
(Plan 04-11) as (VerificationPair, verifier_callable) tuples resolved at plugin load.
"""
