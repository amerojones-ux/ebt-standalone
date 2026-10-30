"""Synthetic weather evidence tests; no network or credentials."""
import unittest
from extensions.weather_evidence import validate_pregame_weather_evidence as check

BASE = {
    "provider": "weather",
    "issued_at_utc": "2026-10-30T10:00:00Z",
    "valid_at_utc": "2026-10-30T19:00:00Z",
    "venue_verified": True,
    "venue_type": "outdoor",
    "rights_verified": True,
    "feed_verified": True,
}


def run(record, **kwargs):
    return check(record, prediction_cutoff_utc="2026-10-30T15:00:00Z",
                 event_start_utc="2026-10-30T19:00:00Z", **kwargs)


class WeatherEvidenceTests(unittest.TestCase):
    def test_valid_is_research_only(self):
        result = run(BASE)
        self.assertEqual(result["status"], "RESEARCH_ONLY")
        self.assertTrue(result["weather_feature_eligible"])
        self.assertEqual(result["forecast"], "HOLD")

    def test_future_issue_blocked(self):
        self.assertEqual(run({**BASE, "issued_at_utc": "2026-10-30T16:00:00Z"})["reason"],
                         "temporal_leakage")

    def test_observed_postgame_blocked(self):
        self.assertEqual(run({**BASE, "issued_at_utc": "2026-10-30T20:00:00Z"})["reason"],
                         "temporal_leakage")

    def test_stale_blocked(self):
        self.assertEqual(run({**BASE, "issued_at_utc": "2026-10-28T10:00:00Z"})["reason"],
                         "stale_forecast")

    def test_wrong_event_window(self):
        self.assertEqual(run({**BASE, "valid_at_utc": "2026-10-30T21:00:00Z"})["reason"],
                         "wrong_event_window")

    def test_indoor_blocked(self):
        self.assertEqual(run({**BASE, "venue_type": "indoor"})["reason"],
                         "non_outdoor_or_unknown_venue")

    def test_unknown_venue_blocked(self):
        self.assertEqual(run({**BASE, "venue_verified": False})["reason"],
                         "unverified_venue")

    def test_unlicensed_blocked(self):
        self.assertEqual(run({**BASE, "rights_verified": False})["reason"],
                         "unverified_rights_or_feed")

    def test_naive_timestamp_blocked(self):
        self.assertEqual(run({**BASE, "issued_at_utc": "2026-10-30T10:00:00"})["reason"],
                         "invalid_timestamp")


if __name__ == "__main__":
    unittest.main()
