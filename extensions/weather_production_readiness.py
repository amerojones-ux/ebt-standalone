"""Fail-closed production readiness assessment for weather integration.

This module is a read-only readiness report, not a release authority.
It explicitly rejects test-only replay storage and caller-asserted trust.
"""
from __future__ import annotations
from collections.abc import Mapping

REQUIRED = (
    "durable_atomic_replay_store",
    "independent_key_trust_store",
    "independent_revocation_service",
    "authenticated_reviewer_approvals",
    "verified_evidence_provenance",
    "protected_live_transport",
    "verified_live_authentication",
    "verified_subscription_rights",
    "verified_data_retention_rights",
    "verified_model_calibration",
    "independent_security_review",
    "independent_release_authorization",
)


def assess_weather_production_readiness(evidence: Mapping[str, object]) -> dict[str, object]:
    """Explicit True is necessary, never sufficient, for actual authorization."""
    if not isinstance(evidence, Mapping):
        evidence = {}
    unmet = [key for key in REQUIRED if evidence.get(key) is not True]
    # This tool cannot authenticate evidence, so it never approves production.
    return {
        "component": "weather",
        "readiness": "BLOCKED" if unmet else "EXTERNAL_VERIFICATION_REQUIRED",
        "production_deploy": "NOT APPROVED",
        "forecast": "HOLD",
        "wager": "NOT APPROVED",
        "unmet_requirements": unmet,
        "evidence_authenticity": "NOT VERIFIED BY THIS MODULE",
    }
