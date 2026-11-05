"""Trusted source policy, adapter, and provenance boundary tests."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from extensions.connectors import OfficialBoxScoreSnapshotAdapter
from extensions.data_ingestion import IngestionValidator
from extensions.trusted_sources import (
    SourceRule, TrustedSourcePolicy, canonical_payload_sha256)


T0 = datetime(2026, 11, 1, 18, 0, tzinfo=timezone.utc)
KEY = 'connector-policy-unit-test-key-32bytes'


def make_policy():
    return TrustedSourcePolicy(
        [SourceRule('NBA_OFFICIAL', 'A1', ('results', 'identity', 'availability', 'historical_stats'))],
        attestation_key=KEY)


def raw(finalized=True, conflict=False):
    return {
        'event_id': 'GAME-1', 'player_id': 'PLAYER-1', 'team_id': 'TEAM-1',
        'stat': 'made_fg', 'event_time': T0.isoformat(),
        'outcome_available_at': (T0 + timedelta(hours=3)).isoformat(),
        'retrieved_at': (T0 + timedelta(hours=4)).isoformat(),
        'finalized': finalized, 'source_conflict': conflict,
        'source_record_id': 'BOX-1', 'minutes': 34.0,
        'opportunity_count': 12, 'outcome_value': 5,
        'outcome_semantics': 'successes_of_opportunities',
        'pregame_features': [{
            'name': 'availability', 'value': 'ACTIVE',
            'available_at': (T0 - timedelta(hours=1)).isoformat(),
            'source': 'NBA_OFFICIAL',
        }],
    }


class TrustedConnectorTests(unittest.TestCase):
    def test_canonical_digest_is_order_independent(self):
        a = {'b': {'y': 2, 'x': 1}, 'a': [3, 4]}
        b = {'a': [3, 4], 'b': {'x': 1, 'y': 2}}
        self.assertEqual(canonical_payload_sha256(a), canonical_payload_sha256(b))

    def test_official_final_snapshot_is_policy_verified(self):
        p = make_policy()
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id='NBA_OFFICIAL', policy=p, fetcher=lambda _: [raw()])
        obs = adapter.ingest(T0)[0]
        self.assertEqual(obs.verification_status, 'VERIFIED')
        self.assertEqual(obs.provenance_sha256, canonical_payload_sha256(raw()))
        validator = IngestionValidator(T0 + timedelta(days=1), trusted_source_policy=p)
        self.assertTrue(validator.validate_observation(obs))

    def test_historical_backfill_retrieval_after_model_cutoff_is_allowed(self):
        p = make_policy()
        record = raw()
        record['retrieved_at'] = (T0 + timedelta(days=10)).isoformat()
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id='NBA_OFFICIAL', policy=p, fetcher=lambda _: [record])
        obs = adapter.ingest(T0)[0]
        # The historical outcome was available 3h after the event, before this cutoff.
        validator = IngestionValidator(T0 + timedelta(days=1), trusted_source_policy=p)
        self.assertTrue(validator.validate_observation(obs))

    def test_cross_provider_feature_requires_separate_attestation(self):
        p = make_policy()
        record = raw()
        record['pregame_features'][0]['source'] = 'OTHER_PROVIDER'
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id='NBA_OFFICIAL', policy=p, fetcher=lambda _: [record])
        with self.assertRaises(ValueError):
            adapter.ingest(T0)

    def test_pending_result_never_becomes_verified(self):
        p = make_policy()
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id='NBA_OFFICIAL', policy=p, fetcher=lambda _: [raw(finalized=False)])
        obs = adapter.ingest(T0)[0]
        self.assertEqual(obs.verification_status, 'PENDING')
        validator = IngestionValidator(T0 + timedelta(days=1), trusted_source_policy=p)
        self.assertFalse(validator.validate_observation(obs))

    def test_conflicting_result_forces_rejection(self):
        p = make_policy()
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id='NBA_OFFICIAL', policy=p, fetcher=lambda _: [raw(conflict=True)])
        obs = adapter.ingest(T0)[0]
        self.assertEqual(obs.verification_status, 'CONFLICTING')
        validator = IngestionValidator(T0 + timedelta(days=1), trusted_source_policy=p)
        self.assertFalse(validator.validate_observation(obs))

    def test_tampered_attestation_signature_is_rejected(self):
        p = make_policy()
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id='NBA_OFFICIAL', policy=p, fetcher=lambda _: [raw()])
        obs = adapter.ingest(T0)[0]
        tampered_att = replace(obs.verification_attestation, reason='tampered')
        tampered_obs = replace(obs, verification_attestation=tampered_att)
        validator = IngestionValidator(T0 + timedelta(days=1), trusted_source_policy=p)
        self.assertFalse(validator.validate_observation(tampered_obs))

    def test_untrusted_provider_cannot_issue_verified_result(self):
        p = make_policy()
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id='UNKNOWN_FEED', policy=p, fetcher=lambda _: [raw()])
        obs = adapter.ingest(T0)[0]
        self.assertEqual(obs.verification_status, 'UNVERIFIED')


if __name__ == '__main__':
    unittest.main()
