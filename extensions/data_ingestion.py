"""Leakage-resistant historical observation contract for offline sports research.

Provider adapters must translate into this schema and pass validation before any
record reaches fitting, simulation, backtesting, or certification code.
"""
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
import math
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .trusted_sources import TrustedSourcePolicy, VerificationAttestation, canonical_payload_sha256


class ObservationValidationError(ValueError):
    pass


def _require_aware(value: datetime, field_name: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ObservationValidationError(f'{field_name} must be timezone-aware')


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ObservationValidationError(f'{field_name} must be non-empty text')


@dataclass(frozen=True)
class PregameFeature:
    name: str
    value: Any
    available_at: datetime
    source: str


@dataclass(frozen=True)
class HistoricalObservation:
    event_id: str
    player_id: str
    team_id: str
    stat: str
    source: str
    event_time: datetime
    outcome_available_at: datetime
    verification_status: str
    verification_attestation: Optional[VerificationAttestation]
    provenance_sha256: str
    canonical_sha256: str
    opportunity_count: int
    outcome_value: float
    outcome_semantics: str = 'count'
    minutes: Optional[float] = None
    source_record_id: Optional[str] = None
    pregame_features: Tuple[PregameFeature, ...] = field(default_factory=tuple)


def canonical_historical_payload(*, event_id, player_id, team_id, stat, source,
                                 event_time, outcome_available_at, opportunity_count,
                                 outcome_value, outcome_semantics, minutes,
                                 source_record_id, pregame_features):
    return {
        'event_id': event_id, 'player_id': player_id, 'team_id': team_id,
        'stat': stat, 'source': source,
        'event_time': event_time.isoformat(),
        'outcome_available_at': outcome_available_at.isoformat(),
        'opportunity_count': opportunity_count,
        'outcome_value': outcome_value,
        'outcome_semantics': outcome_semantics,
        'minutes': minutes,
        'source_record_id': source_record_id,
        'pregame_features': [
            {'name': f.name, 'value': f.value,
             'available_at': f.available_at.isoformat(), 'source': f.source}
            for f in pregame_features
        ],
    }


def canonical_observation_payload(obs: HistoricalObservation):
    return canonical_historical_payload(
        event_id=obs.event_id, player_id=obs.player_id, team_id=obs.team_id,
        stat=obs.stat, source=obs.source, event_time=obs.event_time,
        outcome_available_at=obs.outcome_available_at,
        opportunity_count=obs.opportunity_count, outcome_value=obs.outcome_value,
        outcome_semantics=obs.outcome_semantics, minutes=obs.minutes,
        source_record_id=obs.source_record_id, pregame_features=obs.pregame_features)


@dataclass(frozen=True)
class ValidatedObservation:
    observation: HistoricalObservation
    forecast_cutoff: datetime
    record_hash: str


class IngestionValidator:
    """Fail-closed temporal/data-integrity gate."""
    VALID_SEMANTICS = {'count', 'successes_of_opportunities'}

    def __init__(self, forecast_cutoff: datetime, *, trusted_source_policy: TrustedSourcePolicy):
        _require_aware(forecast_cutoff, 'forecast_cutoff')
        if not isinstance(trusted_source_policy, TrustedSourcePolicy):
            raise ObservationValidationError('trusted_source_policy required')
        self.forecast_cutoff = forecast_cutoff
        self.trusted_source_policy = trusted_source_policy
        self._seen_identities = set()

    @staticmethod
    def canonical_identity_key(obs: HistoricalObservation) -> Tuple[str, str, str, str]:
        return (obs.event_id, obs.player_id, obs.team_id, obs.stat)

    @staticmethod
    def evidence_identity_key(obs: HistoricalObservation) -> Tuple[str, str, str, str, str, str]:
        source_record = obs.source_record_id or obs.provenance_sha256
        return (obs.event_id, obs.player_id, obs.team_id, obs.stat, obs.source, source_record)

    @staticmethod
    def generate_record_hash(obs: HistoricalObservation) -> str:
        payload = {
            'event_id': obs.event_id, 'player_id': obs.player_id,
            'team_id': obs.team_id, 'stat': obs.stat, 'source': obs.source,
            'source_record_id': obs.source_record_id,
            'event_time': obs.event_time.isoformat(),
            'outcome_available_at': obs.outcome_available_at.isoformat(),
            'verification_status': obs.verification_status,
            'provenance_sha256': obs.provenance_sha256,
            'canonical_sha256': obs.canonical_sha256,
            'verification_attestation': None if obs.verification_attestation is None else {
                'status': obs.verification_attestation.status,
                'provider_id': obs.verification_attestation.provider_id,
                'tier': obs.verification_attestation.tier,
                'purpose': obs.verification_attestation.purpose,
                'provenance_sha256': obs.verification_attestation.provenance_sha256,
                'canonical_sha256': obs.verification_attestation.canonical_sha256,
                'policy_version': obs.verification_attestation.policy_version,
                'verified_at': obs.verification_attestation.verified_at.isoformat(),
            },
            'minutes': obs.minutes, 'opportunity_count': obs.opportunity_count,
            'outcome_value': obs.outcome_value,
            'outcome_semantics': obs.outcome_semantics,
            'pregame_features': [
                {'name': f.name, 'value': f.value,
                 'available_at': f.available_at.isoformat(), 'source': f.source}
                for f in obs.pregame_features
            ],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str)
        return hashlib.sha256(canonical.encode('utf-8')).hexdigest()

    def validate_or_raise(self, obs: HistoricalObservation) -> ValidatedObservation:
        if not isinstance(obs, HistoricalObservation):
            raise ObservationValidationError('HistoricalObservation required')
        for field_name in ('event_id', 'player_id', 'team_id', 'stat', 'source'):
            _require_text(getattr(obs, field_name), field_name)
        if obs.source_record_id is not None:
            _require_text(obs.source_record_id, 'source_record_id')
        if obs.verification_status != 'VERIFIED':
            raise ObservationValidationError('verification_status must be VERIFIED')
        if not isinstance(obs.provenance_sha256, str) or len(obs.provenance_sha256) != 64:
            raise ObservationValidationError('64-character provenance_sha256 required')
        if not isinstance(obs.canonical_sha256, str) or len(obs.canonical_sha256) != 64:
            raise ObservationValidationError('64-character canonical_sha256 required')
        attestation = obs.verification_attestation
        if not isinstance(attestation, VerificationAttestation) or attestation.status != 'VERIFIED':
            raise ObservationValidationError('policy-issued VERIFIED attestation required')
        if not self.trusted_source_policy.verify_attestation(attestation):
            raise ObservationValidationError('verification attestation signature/policy invalid')
        if attestation.provider_id != obs.source:
            raise ObservationValidationError('attestation provider/source mismatch')
        if attestation.provenance_sha256 != obs.provenance_sha256:
            raise ObservationValidationError('attestation provenance mismatch')
        if attestation.canonical_sha256 != obs.canonical_sha256:
            raise ObservationValidationError('attestation canonical digest mismatch')
        recomputed_canonical = canonical_payload_sha256(canonical_observation_payload(obs))
        if recomputed_canonical != obs.canonical_sha256:
            raise ObservationValidationError('canonical observation changed after attestation')
        if attestation.purpose != 'results':
            raise ObservationValidationError('historical outcome requires results attestation')
        _require_aware(attestation.verified_at, 'verification_attestation.verified_at')
        if attestation.verified_at < obs.outcome_available_at:
            raise ObservationValidationError('source retrieval cannot precede outcome availability')

        _require_aware(obs.event_time, 'event_time')
        _require_aware(obs.outcome_available_at, 'outcome_available_at')
        if obs.outcome_available_at <= obs.event_time:
            raise ObservationValidationError('outcome cannot be knowable before or at event start')
        if obs.outcome_available_at >= self.forecast_cutoff:
            raise ObservationValidationError('outcome is not safely available before forecast cutoff')

        if obs.minutes is not None:
            if isinstance(obs.minutes, bool) or not isinstance(obs.minutes, (int, float)):
                raise ObservationValidationError('minutes must be numeric or None')
            if not math.isfinite(float(obs.minutes)) or obs.minutes < 0:
                raise ObservationValidationError('minutes must be finite and nonnegative')
        if type(obs.opportunity_count) is not int or obs.opportunity_count < 0:
            raise ObservationValidationError('opportunity_count must be a nonnegative integer')
        if isinstance(obs.outcome_value, bool) or not isinstance(obs.outcome_value, (int, float)):
            raise ObservationValidationError('outcome_value must be numeric')
        if not math.isfinite(float(obs.outcome_value)) or obs.outcome_value < 0:
            raise ObservationValidationError('outcome_value must be finite and nonnegative')
        if obs.outcome_semantics not in self.VALID_SEMANTICS:
            raise ObservationValidationError('unsupported outcome_semantics')
        if obs.outcome_semantics == 'successes_of_opportunities':
            if int(obs.outcome_value) != obs.outcome_value:
                raise ObservationValidationError('conversion successes must be integer-valued')
            if obs.outcome_value > obs.opportunity_count:
                raise ObservationValidationError('conversion successes cannot exceed opportunities')

        feature_names = set()
        for feature in obs.pregame_features:
            if not isinstance(feature, PregameFeature):
                raise ObservationValidationError('PregameFeature required')
            _require_text(feature.name, 'feature.name')
            _require_text(feature.source, 'feature.source')
            _require_aware(feature.available_at, f'feature[{feature.name}].available_at')
            if feature.available_at >= obs.event_time:
                raise ObservationValidationError(
                    f'pregame feature {feature.name} was not available before event start')
            if feature.available_at >= self.forecast_cutoff:
                raise ObservationValidationError(
                    f'pregame feature {feature.name} is after forecast cutoff')
            if feature.name in feature_names:
                raise ObservationValidationError(f'duplicate pregame feature: {feature.name}')
            feature_names.add(feature.name)

        identity = self.evidence_identity_key(obs)
        if identity in self._seen_identities:
            raise ObservationValidationError('duplicate provider evidence record')
        self._seen_identities.add(identity)
        return ValidatedObservation(
            observation=obs,
            forecast_cutoff=self.forecast_cutoff,
            record_hash=self.generate_record_hash(obs),
        )

    def validate_observation(self, obs: HistoricalObservation) -> bool:
        try:
            self.validate_or_raise(obs)
            return True
        except ObservationValidationError:
            return False

    def validate_batch(self, rows: Iterable[HistoricalObservation]) -> Dict[str, List[Any]]:
        accepted, rejected = [], []
        for obs in rows:
            try:
                accepted.append(self.validate_or_raise(obs))
            except ObservationValidationError as exc:
                rejected.append({'observation': obs, 'reason': str(exc)})
        return {'accepted': accepted, 'rejected': rejected}


def reconcile_canonical_observations(rows):
    """Collapse cross-source evidence into one canonical row without double counting.

    Requires already validated rows. Conflicting results fail closed. A1 evidence
    is preferred as primary; all evidence provenance hashes remain in metadata.
    """
    groups = {}
    for validated in rows:
        if not isinstance(validated, ValidatedObservation):
            raise ObservationValidationError('ValidatedObservation required')
        obs = validated.observation
        if obs.outcome_available_at >= validated.forecast_cutoff:
            raise ObservationValidationError('validated receipt violates historical cutoff')
        key = IngestionValidator.canonical_identity_key(obs)
        groups.setdefault(key, []).append(validated)

    reconciled = []
    for key, evidence in groups.items():
        observations = [x.observation for x in evidence]
        semantics = {x.outcome_semantics for x in observations}
        outcomes = {float(x.outcome_value) for x in observations}
        opportunities = {x.opportunity_count for x in observations}
        if len(semantics) != 1 or len(outcomes) != 1 or len(opportunities) != 1:
            raise ObservationValidationError(
                f'conflicting cross-source evidence for canonical identity {key}')
        ordered = sorted(
            evidence,
            key=lambda x: (
                0 if x.observation.verification_attestation.tier == 'A1' else 1,
                x.observation.outcome_available_at,
                x.observation.source,
            ))
        primary_validated = ordered[0]
        primary = primary_validated.observation
        reconciled.append({
            'validated_observation': primary_validated,
            'observation': primary,
            'canonical_identity': key,
            'evidence_count': len(evidence),
            'sources': tuple(x.observation.source for x in ordered),
            'provenance_sha256': tuple(x.observation.provenance_sha256 for x in ordered),
            'primary_tier': primary.verification_attestation.tier,
            'has_a1': any(x.observation.verification_attestation.tier == 'A1' for x in evidence),
            'crosscheck_count': max(0, len(evidence) - 1),
        })
    return reconciled
