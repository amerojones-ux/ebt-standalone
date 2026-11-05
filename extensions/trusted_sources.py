"""Trusted-source policy and HMAC-signed provenance attestations.

The signing key is injected at runtime and must never be committed. A SHA-256
payload digest preserves lineage; HMAC binds the policy decision to that digest.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import json
from typing import Any, Mapping, Tuple


@dataclass(frozen=True)
class SourceRule:
    provider_id: str
    tier: str
    allowed_purposes: Tuple[str, ...]
    active: bool = True


@dataclass(frozen=True)
class VerificationAttestation:
    status: str
    provider_id: str
    tier: str
    purpose: str
    provenance_sha256: str
    canonical_sha256: str
    policy_version: str
    verified_at: datetime
    reason: str
    signature_hmac_sha256: str


def canonical_payload_sha256(raw_record: Mapping[str, Any]) -> str:
    if not isinstance(raw_record, Mapping):
        raise ValueError('raw_record mapping required')
    encoded = json.dumps(raw_record, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, default=str).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


class TrustedSourcePolicy:
    VALID_PURPOSES = {'identity', 'availability', 'historical_stats', 'results', 'environment'}

    def __init__(self, rules, *, attestation_key, policy_version='V7-source-policy-1'):
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise ValueError('policy_version required')
        if isinstance(attestation_key, str):
            attestation_key = attestation_key.encode('utf-8')
        if not isinstance(attestation_key, (bytes, bytearray)) or len(attestation_key) < 16:
            raise ValueError('runtime attestation_key must be at least 16 bytes')
        self._key = bytes(attestation_key)
        self.policy_version = policy_version
        self.rules = {}
        for rule in rules:
            if not isinstance(rule, SourceRule):
                raise ValueError('SourceRule required')
            if rule.provider_id in self.rules:
                raise ValueError('duplicate provider rule')
            if rule.tier not in {'A1', 'B1', 'B2', 'ENVIRONMENT'}:
                raise ValueError('unsupported source tier')
            if not rule.allowed_purposes or any(p not in self.VALID_PURPOSES for p in rule.allowed_purposes):
                raise ValueError('invalid source purpose')
            self.rules[rule.provider_id] = rule

    def _signature(self, *, status, provider_id, tier, purpose, provenance_sha256,
                   canonical_sha256, verified_at, reason):
        body = {
            'status': status, 'provider_id': provider_id, 'tier': tier,
            'purpose': purpose, 'provenance_sha256': provenance_sha256,
            'canonical_sha256': canonical_sha256,
            'policy_version': self.policy_version,
            'verified_at': verified_at.isoformat(), 'reason': reason,
        }
        encoded = json.dumps(body, sort_keys=True, separators=(',', ':')).encode('utf-8')
        return hmac.new(self._key, encoded, hashlib.sha256).hexdigest()

    def _attest(self, *, status, provider_id, tier, purpose, digest, canonical_digest, verified_at, reason):
        signature = self._signature(
            status=status, provider_id=provider_id, tier=tier, purpose=purpose,
            provenance_sha256=digest, canonical_sha256=canonical_digest,
            verified_at=verified_at, reason=reason)
        return VerificationAttestation(
            status, provider_id, tier, purpose, digest, canonical_digest,
            self.policy_version, verified_at, reason, signature)

    def verify_attestation(self, attestation: VerificationAttestation) -> bool:
        if not isinstance(attestation, VerificationAttestation):
            return False
        if attestation.policy_version != self.policy_version:
            return False
        rule = self.rules.get(attestation.provider_id)
        if rule is None or not rule.active or rule.tier != attestation.tier:
            return False
        if attestation.purpose not in rule.allowed_purposes:
            return False
        expected = self._signature(
            status=attestation.status, provider_id=attestation.provider_id,
            tier=attestation.tier, purpose=attestation.purpose,
            provenance_sha256=attestation.provenance_sha256,
            canonical_sha256=attestation.canonical_sha256,
            verified_at=attestation.verified_at, reason=attestation.reason)
        return hmac.compare_digest(expected, attestation.signature_hmac_sha256)

    def issue_validation_receipt_signature(self, record_hash, forecast_cutoff):
        if not isinstance(record_hash, str) or len(record_hash) != 64:
            raise ValueError('64-character record_hash required')
        if not isinstance(forecast_cutoff, datetime) or forecast_cutoff.tzinfo is None or forecast_cutoff.utcoffset() is None:
            raise ValueError('timezone-aware forecast_cutoff required')
        body = (
            'VALIDATION_RECEIPT|' + self.policy_version + '|' +
            record_hash + '|' + forecast_cutoff.isoformat()
        ).encode('utf-8')
        return hmac.new(self._key, body, hashlib.sha256).hexdigest()

    def verify_validation_receipt_signature(self, record_hash, forecast_cutoff, signature):
        if not isinstance(signature, str):
            return False
        try:
            expected = self.issue_validation_receipt_signature(record_hash, forecast_cutoff)
        except ValueError:
            return False
        return hmac.compare_digest(expected, signature)

    def evaluate(self, *, provider_id, purpose, raw_record, retrieved_at,
                 canonical_record=None, source_conflict=False, finalized=None):
        if not isinstance(retrieved_at, datetime) or retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise ValueError('timezone-aware retrieved_at required')
        digest = canonical_payload_sha256(raw_record)
        canonical_digest = canonical_payload_sha256(raw_record if canonical_record is None else canonical_record)
        rule = self.rules.get(provider_id)
        if rule is None or not rule.active:
            return self._attest(
                status='UNVERIFIED', provider_id=provider_id, tier='UNKNOWN',
                purpose=purpose, digest=digest, canonical_digest=canonical_digest, verified_at=retrieved_at,
                reason='provider not active in trusted-source policy')
        if purpose not in self.VALID_PURPOSES or purpose not in rule.allowed_purposes:
            return self._attest(
                status='UNVERIFIED', provider_id=provider_id, tier=rule.tier,
                purpose=purpose, digest=digest, canonical_digest=canonical_digest, verified_at=retrieved_at,
                reason='purpose not allowed for provider')
        if source_conflict:
            return self._attest(
                status='CONFLICTING', provider_id=provider_id, tier=rule.tier,
                purpose=purpose, digest=digest, canonical_digest=canonical_digest, verified_at=retrieved_at,
                reason='critical source conflict requires HOLD')
        if purpose == 'results' and finalized is not True:
            return self._attest(
                status='PENDING', provider_id=provider_id, tier=rule.tier,
                purpose=purpose, digest=digest, canonical_digest=canonical_digest, verified_at=retrieved_at,
                reason='result not finalized')
        return self._attest(
            status='VERIFIED', provider_id=provider_id, tier=rule.tier,
            purpose=purpose, digest=digest, canonical_digest=canonical_digest, verified_at=retrieved_at,
            reason='policy checks passed')
