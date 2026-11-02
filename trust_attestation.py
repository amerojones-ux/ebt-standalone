"""Independently reviewed trust attestation gate.

A supplied boolean is never sufficient. The attestation must bind to the
exact evidence digest and independent official-source comparison, with a
trusted verifier identifier and a distinct source identity. This remains an
offline policy gate, NOT cryptographic authentication of the issuer.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from provider_contracts import parse_time

@dataclass(frozen=True)
class TrustAttestation:
    evidence_id: str
    evidence_sha256: str
    provider: str
    official_source: str
    verifier_id: str
    reviewed_at: str
    official_event_id: str
    provider_event_id: str
    status: str

def assess(att: TrustAttestation | None, *, evidence_id: str, digest: str,
           provider: str, now: datetime, approved_verifiers: frozenset[str],
           approved_official_sources: frozenset[str]) -> tuple[str,str]:
    if att is None:
        return ("HOLD","ATTESTATION_MISSING")
    if (not att.evidence_id or att.evidence_id != evidence_id or
        att.evidence_sha256 != digest or att.provider != provider):
        return ("FAIL","ATTESTATION_BINDING_MISMATCH")
    if att.verifier_id not in approved_verifiers or att.official_source not in approved_official_sources:
        return ("HOLD","REVIEWER_OR_OFFICIAL_SOURCE_UNTRUSTED")
    if att.official_source == provider:
        return ("HOLD","SOURCE_NOT_INDEPENDENT")
    if not att.official_event_id or att.official_event_id != att.provider_event_id:
        return ("HOLD","EVENT_IDENTITY_UNRECONCILED")
    reviewed = parse_time(att.reviewed_at)
    if reviewed is None or now.tzinfo is None or reviewed > now.astimezone(timezone.utc):
        return ("HOLD","REVIEW_TIME_INVALID")
    if att.status != "VERIFIED":
        return ("HOLD","ATTESTATION_NOT_VERIFIED")
    return ("PASS","REVIEW_RECORD_CONSISTENT_ISSUER_AUTH_UNPROVEN")
