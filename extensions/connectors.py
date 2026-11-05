"""Provider adapter contracts and a concrete official box-score snapshot adapter.

Adapters remain thin: fetch/translate/provenance only. They do not fit models,
calibrate forecasts, or approve wagers.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping, Optional

from .data_ingestion import HistoricalObservation, PregameFeature
from .trusted_sources import TrustedSourcePolicy, canonical_payload_sha256


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
        raise NotImplementedError


class OfficialBoxScoreSnapshotAdapter(IProviderAdapter):
    """Concrete adapter for normalized official-source box-score snapshots.

    The injected fetcher permits API/database wiring without coupling network or
    credentials to the modeling package.
    """

    REQUIRED_FIELDS = {
        'event_id', 'player_id', 'team_id', 'stat', 'event_time',
        'outcome_available_at', 'retrieved_at', 'finalized', 'opportunity_count',
        'outcome_value', 'outcome_semantics',
    }

    def __init__(self, *, provider_id: str, policy: TrustedSourcePolicy,
                 fetcher: Callable[[datetime], List[Dict[str, Any]]]):
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError('provider_id required')
        if not isinstance(policy, TrustedSourcePolicy):
            raise ValueError('TrustedSourcePolicy required')
        if not callable(fetcher):
            raise ValueError('callable fetcher required')
        self._provider_id = provider_id
        self.policy = policy
        self.fetcher = fetcher

    @property
    def provider_id(self) -> str:
        return self._provider_id

    def fetch_raw_events(self, target_date: datetime) -> List[Dict[str, Any]]:
        if not isinstance(target_date, datetime) or target_date.tzinfo is None or target_date.utcoffset() is None:
            raise ValueError('timezone-aware target_date required')
        rows = self.fetcher(target_date)
        if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
            raise ValueError('fetcher must return list[dict]')
        return rows

    def map_to_canonical(self, raw_record: Mapping[str, Any]) -> HistoricalObservation:
        if not isinstance(raw_record, Mapping):
            raise ValueError('raw record mapping required')
        missing = self.REQUIRED_FIELDS - set(raw_record)
        if missing:
            raise ValueError(f'missing required fields: {sorted(missing)}')
        outcome_available_at = _parse_dt(raw_record['outcome_available_at'])
        retrieved_at = _parse_dt(raw_record['retrieved_at'])
        if retrieved_at < outcome_available_at:
            raise ValueError('retrieved_at cannot precede outcome_available_at')
        attestation = self.policy.evaluate(
            provider_id=self.provider_id,
            purpose='results',
            raw_record=raw_record,
            retrieved_at=retrieved_at,
            source_conflict=bool(raw_record.get('source_conflict', False)),
            finalized=raw_record['finalized'],
        )
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
        return HistoricalObservation(
            event_id=str(raw_record['event_id']),
            player_id=str(raw_record['player_id']),
            team_id=str(raw_record['team_id']),
            stat=str(raw_record['stat']),
            source=self.provider_id,
            event_time=_parse_dt(raw_record['event_time']),
            outcome_available_at=outcome_available_at,
            verification_status=attestation.status,
            verification_attestation=attestation,
            provenance_sha256=attestation.provenance_sha256,
            opportunity_count=int(raw_record['opportunity_count']),
            outcome_value=float(raw_record['outcome_value']),
            outcome_semantics=str(raw_record['outcome_semantics']),
            minutes=None if raw_record.get('minutes') is None else float(raw_record['minutes']),
            source_record_id=None if raw_record.get('source_record_id') is None else str(raw_record['source_record_id']),
            pregame_features=tuple(features),
        )

    def ingest(self, target_date: datetime) -> List[HistoricalObservation]:
        return [self.map_to_canonical(row) for row in self.fetch_raw_events(target_date)]
