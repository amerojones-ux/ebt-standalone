"""Historical ingestion and opportunity fitting invariants."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from extensions.data_ingestion import (
    HistoricalObservation, IngestionValidator, ObservationValidationError, PregameFeature,
    reconcile_canonical_observations, canonical_historical_payload)
from extensions.opportunity_fitter import OpportunityEfficiencyFitter
from extensions.trusted_sources import SourceRule, TrustedSourcePolicy


BASE = datetime(2026, 11, 1, 18, 0, tzinfo=timezone.utc)
CUTOFF = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)
KEY = 'unit-test-attestation-key-32-bytes'


def policy():
    return TrustedSourcePolicy(
        [SourceRule('official', 'A1', ('results', 'availability', 'identity', 'historical_stats')),
         SourceRule('secondary', 'B1', ('results', 'historical_stats'))],
        attestation_key=KEY)


def make_obs(**changes):
    p = changes.pop('_policy', policy())
    available = changes.get('outcome_available_at', BASE + timedelta(hours=4))
    source = changes.get('source', 'official')
    normalized = dict(
        event_id=changes.get('event_id', 'EV-001'),
        player_id=changes.get('player_id', 'PL-01'),
        team_id=changes.get('team_id', 'TM-01'),
        stat=changes.get('stat', 'made_fg'),
        source=source,
        event_time=changes.get('event_time', BASE),
        outcome_available_at=available,
        opportunity_count=changes.get('opportunity_count', 10),
        outcome_value=changes.get('outcome_value', 4),
        outcome_semantics=changes.get('outcome_semantics', 'successes_of_opportunities'),
        minutes=changes.get('minutes', 32.0),
        source_record_id=changes.get('source_record_id'),
        pregame_features=changes.get('pregame_features', (PregameFeature(
            name='availability', value='ACTIVE',
            available_at=BASE - timedelta(hours=1), source=source),)),
    )
    canonical = canonical_historical_payload(**normalized)
    raw_for_attestation = {
        'record': normalized['event_id'], 'version': 1, 'source': source,
        'canonical': canonical,
    }
    retrieved_at = changes.get('retrieved_at', available)
    att = p.evaluate(
        provider_id=source, purpose='results', raw_record=raw_for_attestation,
        canonical_record=canonical, retrieved_at=retrieved_at, finalized=True)
    return HistoricalObservation(
        **normalized,
        verification_status='VERIFIED',
        verification_attestation=att,
        provenance_sha256=att.provenance_sha256,
        canonical_sha256=att.canonical_sha256,
    ), p



class HistoricalPipelineTests(unittest.TestCase):
    def test_timezone_naive_cutoff_rejected(self):
        with self.assertRaises(ObservationValidationError):
            IngestionValidator(datetime(2026, 11, 2, 18, 0),
                               trusted_source_policy=policy())

    def test_post_cutoff_outcome_rejected(self):
        obs, p = make_obs(outcome_available_at=CUTOFF + timedelta(seconds=1))
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        self.assertFalse(validator.validate_observation(obs))

    def test_post_event_feature_rejected(self):
        obs, p = make_obs(pregame_features=(PregameFeature(
            name='late_feature', value=1, available_at=BASE, source='official'),))
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        self.assertFalse(validator.validate_observation(obs))

    def test_duplicate_provider_evidence_rejected(self):
        p = policy()
        first, _ = make_obs(_policy=p)
        second, _ = make_obs(_policy=p)
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        self.assertTrue(validator.validate_observation(first))
        self.assertFalse(validator.validate_observation(second))

    def test_cross_source_evidence_is_preserved_then_reconciled_once(self):
        p = policy()
        official, _ = make_obs(_policy=p)
        secondary, _ = make_obs(_policy=p, source='secondary')
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        clean = validator.validate_batch([official, secondary])['accepted']
        self.assertEqual(len(clean), 2)
        reconciled = reconcile_canonical_observations(clean, trusted_source_policy=p)
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0]['evidence_count'], 2)
        self.assertTrue(reconciled[0]['has_a1'])
        self.assertEqual(reconciled[0]['observation'].source, 'official')

    def test_cross_source_result_conflict_fails_closed(self):
        p = policy()
        official, _ = make_obs(_policy=p)
        secondary, _ = make_obs(_policy=p, source='secondary', outcome_value=5)
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        clean = validator.validate_batch([official, secondary])['accepted']
        with self.assertRaises(ObservationValidationError):
            reconcile_canonical_observations(clean)

    def test_generic_count_can_exceed_opportunities(self):
        points, p = make_obs(stat='points', opportunity_count=10, outcome_value=24,
                             outcome_semantics='count')
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        self.assertTrue(validator.validate_observation(points))

    def test_conversion_successes_cannot_exceed_opportunities(self):
        bad, p = make_obs(opportunity_count=10, outcome_value=11)
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        self.assertFalse(validator.validate_observation(bad))

    def test_sparse_fitter_falls_back_to_global_distribution(self):
        fitter = OpportunityEfficiencyFitter({'8': '0.25', '10': '0.75'},
                                             trusted_source_policy=policy(),
                                             prior_alpha='2', prior_beta='3')
        fit = fitter.fit_predictive_pmf([])
        self.assertAlmostEqual(sum(fit['predictive_pmf'].values()), 1.0)
        self.assertEqual(fit['posterior_alpha'], '2')
        self.assertEqual(fit['posterior_beta'], '3')
        self.assertFalse(fit['calibration_verified'])

    def test_forged_validation_receipt_is_rejected_by_fitter(self):
        p = policy()
        obs, _ = make_obs(_policy=p)
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        validated = validator.validate_or_raise(obs)
        forged = replace(validated, validation_signature_hmac_sha256='0' * 64)
        fitter = OpportunityEfficiencyFitter(
            {'8': '0.5', '10': '0.5'}, trusted_source_policy=p,
            prior_alpha='2', prior_beta='3')
        with self.assertRaises(ValueError):
            fitter.fit_predictive_pmf([forged])

    def test_valid_history_updates_efficiency_posterior(self):
        p = policy()
        first, _ = make_obs(_policy=p)
        second, _ = make_obs(
            _policy=p, event_id='EV-002', event_time=BASE + timedelta(hours=6),
            outcome_available_at=BASE + timedelta(hours=10),
            opportunity_count=8, outcome_value=5,
            pregame_features=(PregameFeature(
                name='availability', value='ACTIVE',
                available_at=BASE + timedelta(hours=5), source='official'),))
        validator = IngestionValidator(CUTOFF, trusted_source_policy=p)
        clean = validator.validate_batch([first, second])['accepted']
        fitter = OpportunityEfficiencyFitter({'8': '0.5', '10': '0.5'},
                                             trusted_source_policy=p,
                                             prior_alpha='2', prior_beta='3',
                                             shrinkage_games=2)
        fit = fitter.fit_predictive_pmf(clean)
        self.assertEqual(fit['n_observations'], 2)
        self.assertEqual(fit['posterior_alpha'], '11')
        self.assertEqual(fit['posterior_beta'], '12')
        self.assertAlmostEqual(sum(fit['opportunity_pmf'].values()), 1.0)
        self.assertAlmostEqual(sum(fit['predictive_pmf'].values()), 1.0)


if __name__ == '__main__':
    unittest.main()
