"""Synthetic reconciliation tests. No provider endpoints or credentials."""
import unittest
from extensions.provider_gateway import ProviderGateError
from extensions.provider_reconciliation import reconcile_numeric

NOW = "2026-10-30T15:10:00Z"
BASE = {
    "status": "FOUND", "league_id": "NBA", "event_id": "game-001",
    "team_id": "team-01", "player_id": "player-01",
    "stat": "rebounds", "unit": "count", "value": 8,
    "source_as_of_utc": "2026-10-30T15:00:00Z",
}
A = {**BASE, "provider": "sportradar"}
B = {**BASE, "provider": "sportsdata"}


class ReconciliationTests(unittest.TestCase):
    def test_matching_independent_sources(self):
        result = reconcile_numeric([A, B], as_of_utc=NOW)
        self.assertEqual(result["provider_count"], 2)
        self.assertEqual(result["value"], 8)
        self.assertEqual(result["forecast"], "HOLD")

    def test_one_provider_cannot_vote_twice(self):
        with self.assertRaises(ProviderGateError):
            reconcile_numeric([A, A], as_of_utc=NOW)

    def test_conflicting_value_rejected(self):
        with self.assertRaises(ProviderGateError):
            reconcile_numeric([A, {**B, "value": 9}], as_of_utc=NOW)

    def test_conflicting_player_rejected(self):
        with self.assertRaises(ProviderGateError):
            reconcile_numeric([A, {**B, "player_id": "other"}], as_of_utc=NOW)

    def test_conflicting_units_rejected(self):
        with self.assertRaises(ProviderGateError):
            reconcile_numeric([A, {**B, "unit": "yards"}], as_of_utc=NOW)

    def test_stale_rejected(self):
        with self.assertRaises(ProviderGateError):
            reconcile_numeric([A, {**B, "source_as_of_utc": "2026-10-30T12:00:00Z"}], as_of_utc=NOW)

    def test_nan_rejected(self):
        with self.assertRaises(ProviderGateError):
            reconcile_numeric([A, {**B, "value": float("nan")}], as_of_utc=NOW)

    def test_duplicate_conflict_rejected(self):
        with self.assertRaises(ProviderGateError):
            reconcile_numeric([A, {**A, "value": 9}, B], as_of_utc=NOW)

    def test_tolerance_is_explicit(self):
        result = reconcile_numeric([A, {**B, "value": 8.1}], as_of_utc=NOW,
                                   absolute_tolerance=0.2)
        self.assertAlmostEqual(result["value"], 8.05)

    def test_bad_tolerance_rejected(self):
        with self.assertRaises(ProviderGateError):
            reconcile_numeric([A, B], as_of_utc=NOW, absolute_tolerance=float("inf"))


if __name__ == "__main__":
    unittest.main()
