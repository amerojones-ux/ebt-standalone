"""Chronological walk-forward validation and probability diagnostics."""
from datetime import datetime, timedelta
from math import log
from typing import Dict, List

from .interfaces import IWalkForwardValidator


def _aware(value, name):
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f'{name} must be timezone-aware')


class WalkForwardValidator(IWalkForwardValidator):
    def __init__(self, *, train_days=60, test_days=7, calibration_bins=10):
        for name, value in [('train_days', train_days), ('test_days', test_days),
                            ('calibration_bins', calibration_bins)]:
            if type(value) is not int or value <= 0:
                raise ValueError(f'{name} must be a positive integer')
        self.train_days = train_days
        self.test_days = test_days
        self.calibration_bins = calibration_bins

    def split_chronological_windows(self, start_time: datetime, end_time: datetime,
                                    step_days: int) -> List[Dict[str, datetime]]:
        _aware(start_time, 'start_time'); _aware(end_time, 'end_time')
        if end_time <= start_time:
            raise ValueError('end_time must follow start_time')
        if type(step_days) is not int or step_days <= 0:
            raise ValueError('step_days must be a positive integer')

        first_test = start_time + timedelta(days=self.train_days)
        windows = []
        test_start = first_test
        while test_start < end_time:
            test_end = min(test_start + timedelta(days=self.test_days), end_time)
            if test_end <= test_start:
                break
            windows.append({
                'train_start': start_time,
                'train_end': test_start,
                'test_start': test_start,
                'test_end': test_end,
            })
            test_start += timedelta(days=step_days)
        return windows

    def calculate_calibration_metrics(self, simulated_probabilities: List[float],
                                      real_outcomes: List[int]) -> Dict[str, float]:
        if not isinstance(simulated_probabilities, list) or not isinstance(real_outcomes, list):
            raise ValueError('probability and outcome lists required')
        if len(simulated_probabilities) != len(real_outcomes) or not simulated_probabilities:
            raise ValueError('equal non-empty probability/outcome lists required')
        if any(isinstance(p, bool) or not isinstance(p, (int, float)) or p < 0 or p > 1
               for p in simulated_probabilities):
            raise ValueError('probabilities must lie in [0,1]')
        if any(type(y) is not int or y not in (0, 1) for y in real_outcomes):
            raise ValueError('binary outcomes required')

        n = len(real_outcomes)
        brier = sum((float(p) - y) ** 2 for p, y in zip(simulated_probabilities, real_outcomes)) / n
        eps = 1e-15
        log_loss = 0.0
        for p, y in zip(simulated_probabilities, real_outcomes):
            q = min(1 - eps, max(eps, float(p)))
            log_loss += -(y * log(q) + (1 - y) * log(1 - q))
        log_loss /= n

        bins = [[] for _ in range(self.calibration_bins)]
        for p, y in zip(simulated_probabilities, real_outcomes):
            idx = min(self.calibration_bins - 1, int(float(p) * self.calibration_bins))
            bins[idx].append((float(p), y))

        reliability = []
        weighted_gap = 0.0
        max_gap = 0.0
        for idx, values in enumerate(bins):
            lower = idx / self.calibration_bins
            upper = (idx + 1) / self.calibration_bins
            if not values:
                reliability.append({
                    'bin_lower': lower, 'bin_upper': upper, 'n': 0,
                    'mean_probability': None, 'observed_rate': None, 'gap': None})
                continue
            mean_p = sum(p for p, _ in values) / len(values)
            observed = sum(y for _, y in values) / len(values)
            gap = abs(mean_p - observed)
            weighted_gap += (len(values) / n) * gap
            max_gap = max(max_gap, gap)
            reliability.append({
                'bin_lower': lower, 'bin_upper': upper, 'n': len(values),
                'mean_probability': mean_p, 'observed_rate': observed, 'gap': gap})

        return {
            'n': n,
            'brier_score': brier,
            'log_loss': log_loss,
            'expected_calibration_error': weighted_gap,
            'max_calibration_gap': max_gap,
            'reliability_bins': reliability,
            'calibration_verified': False,
            'certification_status': 'HOLD',
        }
