"""Regression tests for the 20% material-shortfall research default."""
import unittest
from extensions.underperformance import evaluate_count_under


class UnderperformanceShortfallTests(unittest.TestCase):
    def test_default_is_twenty_percent_shortfall(self):
        # Baseline 10: material shortfall is an outcome of 8 or fewer.
        pmf = {'7': '0.2', '8': '0.3', '9': '0.3', '10': '0.2'}
        result = evaluate_count_under(pmf, '9.5', normal_baseline='10')
        self.assertEqual(result['severe_fraction'], '0.8')
        self.assertAlmostEqual(result['severe_underperformance_probability_modeled'], 0.5)
        self.assertAlmostEqual(result['market_under_probability_modeled'], 0.8)
        self.assertAlmostEqual(result['below_normal_probability_modeled'], 0.8)
        self.assertEqual(result['simulation_status'], 'NOT RUN')
        self.assertFalse(result['calibration_verified'])

    def test_explicit_legacy_fraction_is_preserved(self):
        pmf = {'5': '0.4', '8': '0.6'}
        result = evaluate_count_under(pmf, '8.5', normal_baseline='10', severe_fraction='0.5')
        self.assertEqual(result['severe_fraction'], '0.5')
        self.assertAlmostEqual(result['severe_underperformance_probability_modeled'], 0.4)

    def test_over_friendly_scenario_is_separate(self):
        pmf = {'6': '0.6', '10': '0.4'}
        recovery = {'6': '0.2', '10': '0.8'}
        result = evaluate_count_under(pmf, '8.5', normal_baseline='10', over_friendly_pmf=recovery)
        self.assertAlmostEqual(result['market_under_probability_modeled'], 0.6)
        self.assertAlmostEqual(result['over_friendly_recovery_under_probability_modeled'], 0.2)
        self.assertEqual(result['wager_status'], 'NOT APPROVED')


if __name__ == '__main__':
    unittest.main()
