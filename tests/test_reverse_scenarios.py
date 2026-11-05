"""Three-scenario research-only reverse-under regression tests."""
import unittest
from extensions.reverse_scenarios import scenario_under_diagnostic


class ReverseScenarioTests(unittest.TestCase):
    def test_recovery_can_defeat_baseline_under(self):
        a = {'5': '0.9', '10': '0.1'}
        b = {'5': '0.7', '10': '0.3'}
        c = {'5': '0.1', '10': '0.9'}
        result = scenario_under_diagnostic(a, b, c, '8.5', baseline='10')
        self.assertAlmostEqual(result['minimum_scenario_exact_under'], 0.1)
        self.assertAlmostEqual(result['scenarios']['MC1_baseline']['modeled_material_shortfall'], 0.9)
        self.assertFalse(result['certified_85_percent'])
        self.assertIsNone(result['calibrated_probability'])
        self.assertEqual(result['simulation_status'], 'NOT RUN')

    def test_rejects_truncated_probability_mass(self):
        with self.assertRaises(ValueError):
            scenario_under_diagnostic({'5': '0.5'}, {'5': '1'}, {'5': '1'}, '8.5', baseline='10')

    def test_rejects_invalid_material_fraction(self):
        with self.assertRaises(ValueError):
            scenario_under_diagnostic({'5': '1'}, {'5': '1'}, {'5': '1'},
                                      '8.5', baseline='10', material_fraction='1.1')


if __name__ == '__main__':
    unittest.main()
