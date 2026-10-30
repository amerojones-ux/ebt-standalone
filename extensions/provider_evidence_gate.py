"""Offline evidence-quality gate for provider onboarding.

Never reads API credentials, makes network calls or approves forecast/wager use.
Input is sanitized metadata, not a provider payload or legal authorization.
"""
from __future__ import annotations
from collections.abc import Mapping

REQUIRED = (
    "vendor_product_reviewed",
    "exact_endpoint_reviewed",
    "auth_transport_reviewed",
    "subscription_scope_verified",
    "model_use_rights_verified",
    "retention_rights_verified",
    "historical_scope_verified",
    "canonical_identity_mapping_verified",
    "timestamp_provenance_verified",
    "protected_execution_environment_verified",
    "egress_policy_verified",
    "independent_reviewer_approved",
)

def evaluate_provider_evidence(provider: str, evidence: Mapping[str, object]) -> dict[str, object]:
    if not isinstance(provider, str) or not provider or len(provider) > 64 or not provider.replace("_", "").isalnum():
        raise ValueError("invalid provider identifier")
    if not isinstance(evidence, Mapping):
        raise ValueError("evidence must be a mapping")
    missing = [name for name in REQUIRED if evidence.get(name) is not True]
    # The caller cannot self-attest independently verified provider rights.
    # Even complete metadata requires external corroboration and live checks.
    return {
        "provider": provider,
        "evidence_completeness": "INCOMPLETE" if missing else "CLAIMED_COMPLETE_UNVERIFIED",
        "missing_requirements": missing,
        "credential_validity": "NOT_VERIFIED",
        "licensed_feed": "NOT_VERIFIED",
        "production_ingestion": "BLOCKED",
        "forecast": "HOLD",
        "wager": "NOT APPROVED",
    }
