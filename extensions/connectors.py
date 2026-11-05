"""Provider adapter contracts and a concrete official box-score snapshot adapter.

Adapters remain thin: fetch/translate/provenance only. They do not fit models,
calibrate forecasts, or approve wagers.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping

from .data_ingestion import HistoricalObservation, PregameFeature, canonical_historical_payload
from .trusted_sources import TrustedSourcePolicy


def _parse_dt(value):
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    else:
        raise ValueError('datetime or ISO-8601 string required')
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError('timezone-aware datetime required')
    return dt


class IProviderAdapter(ABC):
    @property
    @abstractmethod
    def provider_id(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def fetch_raw_events(self, target_date: datetime) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def map_to_canonical(self, raw_record: Mapping[str, Any]) -> HistoricalObservation:
        if not isinstance(raw_record, Mapping):
            raise ValueError('raw record mapping required')
        missing = self.REQUIRED_FIELDS - set(raw_record)
        if missing:
            raise ValueError(f'missing required fields: {sorted(missing)}')

        event_time = _parse_dt(raw_record['event_time'])
        outcome_available_at = _parse_dt(raw_record['outcome_available_at'])
        retrieved_at = _parse_dt(raw_record['retrieved_at'])
        if retrieved_at < outcome_available_at:
            raise ValueError('retrieved_at cannot precede outcome_available_at')

        features = []
        for item in raw_record.get('pregame_features', []):
            if not isinstance(item, Mapping):
                raise ValueError('pregame feature mapping required')
            feature_source = item.get('source', self.provider_id)
            if feature_source != self.provider_id:
                raise ValueError('cross-provider pregame features require their own adapter/attestation')
            features.append(PregameFeature(
                name=item['name'], value=item.get('value'),
                available_at=_parse_dt(item['available_at']),
                source=feature_source,
            ))

        normalized = {
            'event_id': str(raw_record['event_id']),
            'player_id': str(raw_record['player_id']),
            'team_id': str(raw_record['team_id']),
            'stat': str(raw_record['stat']),
            'source': self.provider_id,
            'event_time': event_time,
            'outcome_available_at': outcome_available_at,
            'opportunity_count': int(raw_record['opportunity_count']),
            'outcome_value': float(raw_record['outcome_value']),
            'outcome_semantics': str(raw_record['outcome_semantics']),
            'minutes': None if raw_record.get('minutes') is None else float(raw_record['minutes']),
            'source_record_id': None if raw_record.get('source_record_id') is None else str(raw_record['source_record_id']),
            'pregame_features': tuple(features),
        }
        canonical_record = canonical_historical_payload(**normalized)
        attestation = self.policy.evaluate(
            provider_id=self.provider_id,
            purpose='results',
            raw_record=raw_record,
            canonical_record=canonical_record,
            retrieved_at=retrieved_at,
            source_conflict=bool(raw_record.get('source_conflict', False)),
            finalized=raw_record['finalized'],
        )
        return HistoricalObservation(
            **normalized,
            verification_status=attestation.status,
            verification_attestation=attestation,
            provenance_sha256=attestation.provenance_sha256,
            canonical_sha256=attestation.canonical_sha256,
        )

    def ingest(self, target_date: datetime) -> List[HistoricalObservation]:
        return [self.map_to_canonical(row) for row in self.fetch_raw_events(target_date)]
