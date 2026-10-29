"""Integration tests for scoreboard extraction's fail-closed event gate."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ebt_collect import NBA_URL, extract


def sample(status=1, home=1, away=2, game_id="0000000001"):
    return {"scoreboard": {"gameDate": "2026-10-30", "leagueId": "00",
        "games": [{"gameId": game_id, "gameStatus": status,
            "homeTeam": {"teamId": home}, "awayTeam": {"teamId": away},
            "gameTimeUTC": "2026-10-30T23:00:00Z"}]}}


class ExtractionGateIntegrationTests(unittest.TestCase):
    def run_extract(self, board, retrieved="2026-10-29T12:00:00Z"):
        with tempfile.TemporaryDirectory() as d:
            body = json.dumps(board).encode()
            digest = hashlib.sha256(body).hexdigest()
            Path(d, digest + ".bin").write_bytes(body)
            receipt = {"status": "COLLECTED", "schema_version": "1.0",
                "url": NBA_URL, "adapter": "nba_scoreboard",
                "raw_path": digest + ".bin", "raw_sha256": digest,
                "bytes": len(body), "retrieved_at": retrieved}
            return extract(receipt, d, parameters={"expected_date": "2026-10-30"})

    def test_valid_game_passes_structural_gate_only(self):
        result = self.run_extract(sample())
        self.assertTrue(result["extracted"]["event_gate_passed"])
        self.assertEqual(result["extracted"]["event_gate_checked"], 1)
        self.assertFalse(result["forecast_approved"])
        self.assertFalse(result["source_truth_verified"])

    def test_empty_scoreboard_not_marked_validated(self):
        board = sample()
        board['scoreboard']['games'] = []
        result = self.run_extract(board)
        self.assertFalse(result['extracted']['event_gate_passed'])
        self.assertEqual(result['extracted']['event_gate_checked'], 0)
        self.assertFalse(result['forecast_approved'])

    def test_late_scheduled_capture_holds(self):
        with self.assertRaises(ValueError):
            self.run_extract(sample(), retrieved="2026-10-31T00:00:00Z")

    def test_duplicate_teams_holds(self):
        with self.assertRaises(ValueError):
            self.run_extract(sample(home=1, away=1))

    def test_duplicate_event_holds(self):
        board = sample()
        board["scoreboard"]["games"].append(board["scoreboard"]["games"][0])
        with self.assertRaises(ValueError):
            self.run_extract(board)


if __name__ == "__main__":
    unittest.main()
