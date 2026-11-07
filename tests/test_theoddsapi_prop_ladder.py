"""Synthetic tests for The Odds API per-event player-prop ladder contract."""
import unittest
from extensions.theoddsapi_prop_ladder import (
    assess_posted_ladder_coverage,
    parse_event_markets,
    parse_event_odds,
    public_event_markets_request,
    public_event_odds_requests,
)

EVENT="2147587132aa05de18df6c158da786ec"
SPORT="basketball_nba"
CAPTURE="2026-11-07T18:00:00Z"
COMMENCE="2026-11-07T20:00:00Z"


def discovery_payload():
    return {
        "id":EVENT,"sport_key":SPORT,"sport_title":"NBA",
        "commence_time":COMMENCE,"home_team":"Home","away_team":"Away",
        "bookmakers":[
            {"key":"fanduel","title":"FanDuel","markets":[
                {"key":"player_points"},{"key":"player_points_alternate"},{"key":"h2h"}]},
            {"key":"draftkings","title":"DraftKings","markets":[
                {"key":"player_points"},{"key":"player_rebounds_alternate"}]},
        ],
    }


def odds_payload(market_keys=("player_points","player_points_alternate","player_rebounds_alternate")):
    markets=[]
    if "player_points" in market_keys:
        markets.append({
            "key":"player_points","last_update":"2026-11-07T17:59:00Z",
            "outcomes":[
                {"name":"Over","description":"Player A","price":-110,"point":22.5},
                {"name":"Under","description":"Player A","price":-110,"point":22.5},
            ],
        })
    if "player_points_alternate" in market_keys:
        markets.append({
            "key":"player_points_alternate","last_update":"2026-11-07T17:58:30Z",
            "outcomes":[
                {"name":"Over","description":"Player A","price":-400,"point":15.5},
                {"name":"Over","description":"Player A","price":250,"point":29.5},
            ],
        })
    if "player_rebounds_alternate" in market_keys:
        markets.append({
            "key":"player_rebounds_alternate","last_update":"2026-11-07T17:58:00Z",
            "outcomes":[
                {"name":"Over","description":"Player B","price":-180,"point":4.5},
            ],
        })
    return {
        "id":EVENT,"sport_key":SPORT,"sport_title":"NBA",
        "commence_time":COMMENCE,"home_team":"Home","away_team":"Away",
        "bookmakers":[
            {"key":"fanduel","title":"FanDuel","markets":[m for m in markets if m["key"]!="player_rebounds_alternate"]},
            {"key":"draftkings","title":"DraftKings","markets":[m for m in markets if m["key"]!="player_points_alternate"]},
        ],
    }


class PropLadderTests(unittest.TestCase):
    def test_discovery_request_uses_documented_event_markets_route(self):
        plan=public_event_markets_request(SPORT,EVENT,["us","us2"])
        self.assertEqual(plan["path"],f"/v4/sports/{SPORT}/events/{EVENT}/markets")
        self.assertEqual(plan["query"]["regions"],"us,us2")
        self.assertEqual(plan["credential_query_key"],"apiKey")
        self.assertFalse(plan["network_enabled"])

    def test_event_odds_planner_chunks_all_markets_and_estimates_credits(self):
        plans=public_event_odds_requests(
            SPORT,EVENT,["us"],["player_points","player_points_alternate","player_first_basket"],
            max_markets_per_request=2)
        self.assertEqual(len(plans),2)
        self.assertEqual(plans[0]["query"]["oddsFormat"],"american")
        self.assertEqual(plans[0]["estimated_usage_credits"],2)
        self.assertEqual(plans[1]["estimated_usage_credits"],1)
        self.assertEqual(
            sum(len(x["market_keys"]) for x in plans),3)

    def test_planner_rejects_non_player_markets(self):
        with self.assertRaises(ValueError):
            public_event_odds_requests(SPORT,EVENT,["us"],["h2h"])

    def test_parse_discovery_preserves_market_keys_per_book(self):
        out=parse_event_markets(discovery_payload())
        by_book={x["bookmaker_key"]:x for x in out["bookmakers"]}
        self.assertEqual(
            by_book["fanduel"]["player_market_keys"],
            ["player_points","player_points_alternate"])
        self.assertNotIn("h2h",by_book["fanduel"]["player_market_keys"])

    def test_parse_odds_preserves_each_alternate_threshold(self):
        out=parse_event_odds(odds_payload(),captured_at=CAPTURE)
        rows=[r for r in out["records"] if r["market_key"]=="player_points_alternate"]
        self.assertEqual(len(rows),2)
        self.assertEqual({r["point"] for r in rows},{"15.5","29.5"})
        self.assertTrue(all(r["bookmaker_key"]=="fanduel" for r in rows))
        self.assertEqual(out["wager_status"],"NOT APPROVED")

    def test_parse_odds_rejects_post_capture_market_update(self):
        body=odds_payload()
        body["bookmakers"][0]["markets"][0]["last_update"]="2026-11-07T18:01:00Z"
        with self.assertRaises(ValueError):
            parse_event_odds(body,captured_at=CAPTURE)

    def test_complete_posted_ladder_verifies_book_market_pairs(self):
        discovery=parse_event_markets(discovery_payload())
        odds=parse_event_odds(odds_payload(),captured_at=CAPTURE)
        out=assess_posted_ladder_coverage(
            discovery,[odds],
            ["player_points","player_points_alternate","player_rebounds_alternate"])
        self.assertTrue(out["complete_posted_ladder_verified"])
        self.assertEqual(out["expected_bookmaker_market_pairs"],4)
        self.assertEqual(out["captured_bookmaker_market_pairs"],4)
        self.assertFalse(out["global_supported_market_catalog_complete"])

    def test_missing_discovered_book_market_pair_fails_coverage(self):
        discovery=parse_event_markets(discovery_payload())
        odds=parse_event_odds(
            odds_payload(("player_points","player_points_alternate")),
            captured_at=CAPTURE)
        out=assess_posted_ladder_coverage(
            discovery,[odds],
            ["player_points","player_points_alternate","player_rebounds_alternate"])
        self.assertFalse(out["complete_posted_ladder_verified"])
        self.assertIn(
            ["draftkings","player_rebounds_alternate"],
            out["missing_bookmaker_market_pairs"])

    def test_unposted_requested_market_is_reported_not_silently_dropped(self):
        discovery=parse_event_markets(discovery_payload())
        odds=parse_event_odds(odds_payload(),captured_at=CAPTURE)
        out=assess_posted_ladder_coverage(
            discovery,[odds],
            ["player_points","player_first_basket"])
        self.assertIn("player_first_basket",out["requested_not_seen_as_posted"])

    def test_duplicate_exact_ladder_outcome_rejected(self):
        body=odds_payload(("player_points",))
        body["bookmakers"][0]["markets"][0]["outcomes"].append(
            {"name":"Over","description":"Player A","price":-110,"point":22.5})
        with self.assertRaises(ValueError):
            parse_event_odds(body,captured_at=CAPTURE)


if __name__=="__main__":
    unittest.main()
