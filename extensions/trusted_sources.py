"""Trusted-source policy and provenance attestations for historical research data.

A SHA-256 digest provides deterministic lineage evidence, not source authenticity.
VERIFIED is assigned only by this policy after provider/tier/purpose checks.
"""
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Any, Dict, Mapping, Optional, Tuple


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
    policy_version: str
    verified_at: datetime
    reason: str = ''


def canonical_payload_sha256(raw_record: Mapping[str, Any]) -> str:
    if not isinstance(raw_record, Mapping):
        raise ValueError('raw_record mapping required')
    encoded = json.dumps(raw_record, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, default=str).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


class TrustedSourcePolicy:
    VALID_PURPOSES = {'identity', 'availability', 'historical_stats', 'results', 'environment'}

    def __init__(self, rules, *, policy_version='V7-source-policy-1'):
        if not isinstance(policy_version, str) or not policy_version.strip():
            raise ValueError('policy_version required')
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

    def evaluate(self, *, provider_id, purpose, raw_record, retrieved_at,
                 source_conflict=False, finalized=None):
        if not isinstance(retrieved_at, datetime) or retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            raise ValueError('timezone-aware retrieved_at required')
        digest = canonical_payload_sha256(raw_record)
        rule = self.rules.get(provider_id)
        if rule is None or not rule.active:
            return VerificationAttestation(
                'UNVERIFIED', provider_id, 'UNKNOWN', purpose, digest,
                self.policy_version, retrieved_at, 'provider not active in trusted-source policy')
        if purpose not in self.VALID_PURPOSES or purpose not in rule.allowed_purposes:
            return VerificationAttestation(
                'UNVERIFIED', provider_id, rule.tier, purpose, digest,
                self.policy_version, retrieved_at, 'purpose not allowed for provider')
        if source_conflict:
            return VerificationAttestation(
                'CONFLICTING', provider_id, rule.tier, purpose, digest,
                self.policy_version, retrieved_at, 'critical source conflict requires HOLD')
        if purpose == 'results' and finalized is not True:
            return VerificationAttestation(
                'PENDING', provider_id, rule.tier, purpose, digest,
                self.policy_version, retrieved_at, 'result not finalized')
        return VerificationAttestation(
            'VERIFIED', provider_id, rule.tier, purpose, digest,
            self.policy_version, retrieved_at, 'policy checks passed')
