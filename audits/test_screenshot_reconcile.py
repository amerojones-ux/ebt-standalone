"""Regression tests for screenshot audit, run with python -m unittest discover -s audits -p 'test_*.py'."""
import unittest
try:
    from audits.screenshot_reconcile import SLIPS, Leg, unique_legs, duplicate_counts, grade, decimal_from_american
except ModuleNotFoundError:
    from screenshot_reconcile import SLIPS, Leg, unique_legs, duplicate_counts, grade, decimal_from_american

class TestScreenshotAudit(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(sum(map(len, SLIPS.values())), 17)
        self.assertEqual(len(unique_legs()), 14)
        self.assertEqual(sorted(duplicate_counts().values()), [2, 2, 2])

    def test_unverified_is_hold(self):
        leg = Leg("A", "B", "points", 10)
        self.assertEqual(grade(leg, 20)["status"], "HOLD")
        self.assertEqual(grade(leg, None, True)["status"], "HOLD")

    def test_threshold_and_margin(self):
        leg = Leg("A", "B", "points", 10)
        self.assertEqual(grade(leg, 10, True)["status"], "HIT")
        self.assertEqual(grade(leg, 9, True)["status"], "MISS")
        self.assertEqual(grade(leg, 9, True)["margin"], -1)

    def test_bad_actual_rejected(self):
        with self.assertRaises(ValueError):
            grade(Leg("A", "B", "points", 10), -1, True)

    def test_odds_conversion(self):
        self.assertAlmostEqual(decimal_from_american(467), 5.67)
        self.assertAlmostEqual(decimal_from_american(-200), 1.5)
        with self.assertRaises(ValueError):
            decimal_from_american(0)

if __name__ == "__main__":
    unittest.main()
