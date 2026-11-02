"""Offline evidence-to-release composition. All evidence is fail-closed.

This is not independent authentication: the caller must establish the trust
of the captured source and official comparison outside this module.
"""
from dataclasses import dataclass
from provider_contracts import Contract, Capture, verify
from provider_capture_integrity import CaptureRecord, verify_integrity
from provider_intake import ProviderIntake, evaluate_intake, IntakeStatus
from release_readiness import ReleaseEvidence, State, decide

@dataclass(frozen=True)
class EvidenceBundle:
    contract: Contract
    capture: Capture
    integrity_record: CaptureRecord
    intake: ProviderIntake

def verify_bundle(bundle: EvidenceBundle, *, now, reconciled_ids: frozenset[str]):
    schema_status, schema_reason = verify(bundle.contract, bundle.capture, now=now, reconciled_ids=reconciled_ids)
    digest_status, digest_reason = verify_integrity(bundle.integrity_record)
    intake_status, intake_reasons = evaluate_intake(bundle.intake)
    if bundle.capture.host != bundle.intake.api_host or bundle.capture.endpoint != bundle.intake.endpoint_id:
        return ("HOLD", ("CROSS_RECORD_IDENTITY_MISMATCH",))
    if bundle.capture.body != bundle.integrity_record.payload:
        return ("HOLD", ("CAPTURE_PAYLOAD_MISMATCH",))
    if bundle.capture.retrieved_at != bundle.integrity_record.retrieved_at:
        return ("HOLD", ("RETRIEVAL_TIMESTAMP_MISMATCH",))
    if schema_status != "PASS" or digest_status != "PASS" or intake_status is not IntakeStatus.VERIFIED:
        return ("HOLD", (schema_reason, digest_reason, *intake_reasons))
    return ("PASS", ("OFFLINE_EVIDENCE_CONSISTENT_NOT_AUTHENTICATED",))

def release_decision(evidence: ReleaseEvidence):
    return decide(evidence)
