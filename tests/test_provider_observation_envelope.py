"""Synthetic tests for offline observation envelope validation."""
import unittest
from extensions.provider_observation_envelope import validate_research_envelope

def sample():
    return {"provider":"sportsdata","league_id":"nba","event_id":"game-1",
            "team_id":"team-1","player_id":"player-1","source_record_id":"record-1",
            "source_as_of_utc":"2026-10-30T12:00:00Z",
            "captured_at_utc":"2026-10-30T12:01:00Z","status":"FOUND"}

NOW="2026-10-30T12:05:00Z"

class ProviderObservationEnvelopeTests(unittest.TestCase):
    def test_deterministic_structure_only(self):
        record=sample()
        one=validate_research_envelope(record,as_of_utc=NOW)
        two=validate_research_envelope(dict(reversed(list(record.items()))),as_of_utc=NOW)
        self.assertEqual(one["fingerprint"],two["fingerprint"])
        self.assertEqual(one["ingestion"],"BLOCKED")
        self.assertEqual(one["forecast"],"HOLD")
        self.assertIs(one["source_authenticated"],False)

    def test_future_and_reordered_chronology_rejected(self):
        record=sample()
        record["captured_at_utc"]="2026-10-30T11:59:00Z"
        with self.assertRaises(ValueError):
            validate_research_envelope(record,as_of_utc=NOW)
        record=sample()
        record["source_as_of_utc"]="2026-10-31T12:00:00Z"
        with self.assertRaises(ValueError):
            validate_research_envelope(record,as_of_utc=NOW)

    def test_stale_and_naive_time_rejected(self):
        record=sample()
        with self.assertRaises(ValueError):
            validate_research_envelope(record,as_of_utc=NOW,max_age_seconds=1)
        record["source_as_of_utc"]="2026-10-30T12:00:00"
        with self.assertRaises(ValueError):
            validate_research_envelope(record,as_of_utc=NOW)

    def test_unexpected_field_and_bad_id_rejected(self):
        record=sample()
        record["secret"]="do-not-store"
        with self.assertRaises(ValueError):
            validate_research_envelope(record,as_of_utc=NOW)
        record=sample()
        record["player_id"]="../invalid"
        with self.assertRaises(ValueError):
            validate_research_envelope(record,as_of_utc=NOW)

if __name__=="__main__":
    unittest.main()
