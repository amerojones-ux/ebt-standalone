"""Synthetic player-prop normalization tests; no live API access."""
import unittest
from extensions.prop_market_normalizer import normalize_prop_quote as norm

BASE = {"provider": "theoddsapi", "league_id": "nba", "event_id": "event1",
        "player_id": "player1", "bookmaker_id": "book1", "market": "rebounds",
        "side": "under", "line": "9.5",
        "source_as_of_utc": "2026-10-30T19:00:00Z"}


def run(record):
    return norm(record, as_of_utc="2026-10-30T19:01:00Z")


class PropMarketNormalizerTests(unittest.TestCase):
    def test_valid_quote_research_only(self):
        r = run(BASE)
        self.assertEqual(r["line"], "9.5")
        self.assertEqual(r["use"], "market_comparison_only")
        self.assertEqual(r["forecast"], "HOLD")

    def test_market_not_model_source(self):
        with self.assertRaises(ValueError):
            run({**BASE, "provider": "sportsdata"})

    def test_future_quote_rejected(self):
        with self.assertRaises(ValueError):
            run({**BASE, "source_as_of_utc": "2026-10-30T19:02:00Z"})

    def test_stale_quote_rejected(self):
        with self.assertRaises(ValueError):
            run({**BASE, "source_as_of_utc": "2026-10-30T18:00:00Z"})

    def test_invalid_line_rejected(self):
        for val in ("NaN", "-1", "Infinity", True):
            with self.subTest(val=val), self.assertRaises(ValueError):
                run({**BASE, "line": val})

    def test_unsupported_market_rejected(self):
        with self.assertRaises(ValueError):
            run({**BASE, "market": "unknown_market"})

    def test_unverified_identity_rejected(self):
        with self.assertRaises(ValueError):
            run({**BASE, "player_id": "player 1"})


if __name__ == "__main__":
    unittest.main()
