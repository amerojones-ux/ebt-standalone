"""Historical ingestion and opportunity fitting invariants."""
import unittest
from datetime import datetime, timedelta, timezone

from extensions.data_ingestion import (
    HistoricalObservation, IngestionValidator, ObservationValidationError, PregameFeature)
from extensions.opportunity_fitter import OpportunityEfficiencyFitter


BASE = datetime(2026, 11, 1, 18, 0, tzinfo=timezone.utc)
CUTOFF = datetime(2026, 11, 2, 18, 0, tzinfo=timezone.utc)


def make_obs(**changes):
    raw = dict(
        event_id='EV-001', player_id='PL-01', team_id='TM-01', stat='made_fg',
        source='official', event_time=BASE,
        outcome_available_at=BASE + timedelta(hours=4),
        verification_status='VERIFIED', opportunity_count=10, outcome_value=4,
        outcome_semantics='successes_of_opportunities', minutes=32.0,
        pregame_features=(PregameFeature(
            name='availability', value='ACTIVE',
            available_at=BASE - timedelta(hours=1), source='official'),),
    )
    raw.update(changes)
    return HistoricalObservation(**raw)


class HistoricalPipelineTests(unittest.TestCase):
    def test_timezone_naive_cutoff_rejected(self):
        with self.assertRaises(ObservationValidationError):
            IngestionValidator(datetime(2026, 11, 2, 18, 0))

    def test_post_cutoff_outcome_rejected(self):
        validator = IngestionValidator(CUTOFF)
        obs = make_obs(outcome_available_at=CUTOFF + timedelta(seconds=1))
        self.assertFalse(validator.validate_observation(obs))

    def test_post_event_feature_rejected(self):
        validator = IngestionValidator(CUTOFF)
        obs = make_obs(pregame_features=(PregameFeature(
            name='late_feature', value=1, available_at=BASE, source='official'),))
        self.assertFalse(validator.validate_observation(obs))

    def test_duplicate_identity_rejected_even_across_sources(self):
        validator = IngestionValidator(CUTOFF)
        first = make_obs()
        second = make_obs(source='independent_crosscheck')
        self.assertTrue(validator.validate_observation(first))
        self.assertFalse(validator.validate_observation(second))

    def test_generic_count_can_exceed_opportunities(self):
        validator = IngestionValidator(CUTOFF)
        points = make_obs(stat='points', opportunity_count=10, outcome_value=24,
                          outcome_semantics='count')
        self.assertTrue(validator.validate_observation(points))

    def test_conversion_successes_cannot_exceed_opportunities(self):
        validator = IngestionValidator(CUTOFF)
        bad = make_obs(opportunity_count=10, outcome_value=11)
        self.assertFalse(validator.validate_observation(bad))

    def test_sparse_fitter_falls_back_to_global_distribution(self):
        fitter = OpportunityEfficiencyFitter({'8': '0.25', '10': '0.75'},
                                             prior_alpha='2', prior_beta='3')
        fit = fitter.fit_predictive_pmf([])
        self.assertAlmostEqual(sum(fit['predictive_pmf'].values()), 1.0)
        self.assertEqual(fit['posterior_alpha'], '2')
        self.assertEqual(fit['posterior_beta'], '3')
        self.assertFalse(fit['calibration_verified'])

    def test_valid_history_updates_efficiency_posterior(self):
        validator = IngestionValidator(CUTOFF)
        rows = [
            make_obs(),
            make_obs(event_id='EV-002', event_time=BASE + timedelta(hours=6),
                     outcome_available_at=BASE + timedelta(hours=10),
                     opportunity_count=8, outcome_value=5,
                     pregame_features=(PregameFeature(
                         name='availability', value='ACTIVE',
                         available_at=BASE + timedelta(hours=5), source='official'),)),
        ]
        clean = validator.validate_batch(rows)['accepted']
        fitter = OpportunityEfficiencyFitter({'8': '0.5', '10': '0.5'},
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
