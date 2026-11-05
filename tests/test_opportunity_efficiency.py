"""Research model mathematical invariants; synthetic inputs only."""
import unittest
from extensions.opportunity_efficiency import (
    beta_binomial_pmf, mixture_opportunity_pmf, validate_shared_opportunity_budget)


class OpportunityEfficiencyTests(unittest.TestCase):
    def test_beta_binomial_uniform_prior(self):
        p = beta_binomial_pmf(2, 0, 0)
        self.assertAlmostEqual(p['0'], 1 / 3)
        self.assertAlmostEqual(p['1'], 1 / 3)
        self.assertAlmostEqual(p['2'], 1 / 3)
        self.assertAlmostEqual(sum(p.values()), 1.0)

    def test_mixture_preserves_all_mass_and_tail(self):
        p = mixture_opportunity_pmf({'0': '0.25', '2': '0.75'}, 2, 2)
        self.assertAlmostEqual(sum(p.values()), 1.0)
        self.assertIn('2', p)
        self.assertGreater(p['0'], 0.25)

    def test_invalid_opportunity_distribution_rejected(self):
        with self.assertRaises(ValueError):
            mixture_opportunity_pmf({'1': '0.5'}, 1, 1)

    def test_shared_budget(self):
        self.assertTrue(validate_shared_opportunity_budget({'a': 7, 'b': 3}, 10))
        with self.assertRaises(ValueError):
            validate_shared_opportunity_budget({'a': 7, 'b': 4}, 10)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            beta_binomial_pmf(5, -1, 2)


if __name__ == '__main__':
    unittest.main()
