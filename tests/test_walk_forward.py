"""Chronological walk-forward validation tests."""
import unittest
from datetime import datetime, timezone

from extensions.walk_forward import WalkForwardValidator


class WalkForwardTests(unittest.TestCase):
    def test_windows_never_overlap_train_with_test(self):
        v = WalkForwardValidator(train_days=30, test_days=7, calibration_bins=5)
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 1, tzinfo=timezone.utc)
        windows = v.split_chronological_windows(start, end, step_days=7)
        self.assertTrue(windows)
        for w in windows:
            self.assertLessEqual(w['train_start'], w['train_end'])
            self.assertEqual(w['train_end'], w['test_start'])
            self.assertLess(w['test_start'], w['test_end'])

    def test_perfect_predictions_have_zero_brier_and_gap(self):
        v = WalkForwardValidator(calibration_bins=2)
        m = v.calculate_calibration_metrics([0.0, 1.0], [0, 1])
        self.assertAlmostEqual(m['brier_score'], 0.0)
        self.assertAlmostEqual(m['expected_calibration_error'], 0.0)
        self.assertFalse(m['calibration_verified'])
        self.assertEqual(m['certification_status'], 'HOLD')

    def test_known_brier_score(self):
        v = WalkForwardValidator(calibration_bins=2)
        m = v.calculate_calibration_metrics([0.25, 0.75], [0, 1])
        self.assertAlmostEqual(m['brier_score'], 0.0625)

    def test_invalid_probability_rejected(self):
        v = WalkForwardValidator()
        with self.assertRaises(ValueError):
            v.calculate_calibration_metrics([1.2], [1])

    def test_naive_time_rejected(self):
        v = WalkForwardValidator()
        with self.assertRaises(ValueError):
            v.split_chronological_windows(
                datetime(2026, 1, 1), datetime(2026, 4, 1, tzinfo=timezone.utc), 7)


if __name__ == '__main__':
    unittest.main()
