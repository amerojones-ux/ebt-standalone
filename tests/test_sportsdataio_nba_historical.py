"""SportsDataIO NBA historical mapping tests."""
import unittest
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from extensions.connectors import OfficialBoxScoreSnapshotAdapter
from extensions.data_ingestion import IngestionValidator
from extensions.entity_resolution import (
    CanonicalEntity, EntityResolutionRegistry, canonicalize_provider_record,
)
from extensions.sportsdataio_nba_historical import (
    PROVIDER_ID, classify_game_status, extract_player_crossrefs, map_box_score,
    parse_sportsdataio_datetime,
)
from extensions.trusted_sources import SourceRule, TrustedSourcePolicy

ET = ZoneInfo("America/New_York")
KEY = "sportsdataio-nba-historical-test-key-32"
GAME_START = datetime(2026, 1, 10, 19, 30, tzinfo=ET)
UPDATED = datetime(2026, 1, 10, 22, 15, tzinfo=ET)
RETRIEVED = datetime(2026, 1, 11, 4, 0, tzinfo=timezone.utc)


def box_score(status="Final", points=24, updated=UPDATED):
    return {
        "Game": {
            "GameID": 500,
            "GlobalGameID": 9000500,
            "Status": status,
            "DateTime": GAME_START.replace(tzinfo=None).isoformat(),
            "Updated": updated.replace(tzinfo=None).isoformat(),
            "AwayTeam": "LAL",
            "HomeTeam": "NY",
            "AwayTeamID": 20,
            "HomeTeamID": 6,
            "GlobalAwayTeamID": 20020,
            "GlobalHomeTeamID": 20006,
        },
        "PlayerGames": [{
            "StatID": 10001,
            "GameID": 500,
            "GlobalGameID": 9000500,
            "PlayerID": 100,
            "TeamID": 20,
            "Name": "Test Player",
            "IsGameOver": True,
            "Updated": updated.replace(tzinfo=None).isoformat(),
            "Minutes": 34,
            "Points": points,
            "Rebounds": 8,
            "Assists": 6,
            "Steals": 2,
            "BlockedShots": 1,
            "Turnovers": 3,
            "FieldGoalsMade": 9,
            "FieldGoalsAttempted": 18,
            "ThreePointersMade": 3,
            "ThreePointersAttempted": 8,
            "FreeThrowsMade": 3,
            "FreeThrowsAttempted": 4,
        }],
    }


def policy():
    return TrustedSourcePolicy(
        [SourceRule(PROVIDER_ID, "B2", ("results", "historical_stats"))],
        attestation_key=KEY,
    )


def registry():
    r = EntityResolutionRegistry()
    r.register_canonical(CanonicalEntity(
        "event:lal-ny-2026-01-10", "event", "LAL @ NY"))
    r.register_canonical(CanonicalEntity(
        "team:lal", "team", "Los Angeles Lakers"))
    r.register_canonical(CanonicalEntity(
        "player:test", "player", "Test Player"))
    r.bind_provider_identity(
        entity_type="event", provider_id=PROVIDER_ID,
        provider_entity_id="global:9000500",
        canonical_id="event:lal-ny-2026-01-10")
    r.bind_provider_identity(
        entity_type="team", provider_id=PROVIDER_ID,
        provider_entity_id="20", canonical_id="team:lal")
    r.bind_provider_identity(
        entity_type="player", provider_id=PROVIDER_ID,
        provider_entity_id="100", canonical_id="player:test")
    return r


class SportsDataIOHistoricalTests(unittest.TestCase):
    def test_naive_provider_times_are_interpreted_as_eastern(self):
        parsed = parse_sportsdataio_datetime(
            "2026-01-10T19:30:00", "DateTime")
        self.assertEqual(parsed.tzinfo, ET)
        self.assertEqual(parsed.hour, 19)

    def test_only_normal_final_states_ingest(self):
        self.assertTrue(classify_game_status("Final")["final_stats_eligible"])
        self.assertTrue(classify_game_status("F/OT")["final_stats_eligible"])
        for status in (
            "Scheduled", "InProgress", "Suspended", "Postponed",
            "Delayed", "Canceled", "Forfeit", "NotNecessary",
        ):
            self.assertFalse(classify_game_status(status)["final_stats_eligible"])

    def test_forfeit_requires_a1_settlement(self):
        decision = classify_game_status("Forfeit")
        self.assertEqual(decision["category"], "FORFEIT_HOLD")
        self.assertFalse(decision["settlement_eligible"])

    def test_final_box_score_maps_count_and_conversion_stats(self):
        rows = map_box_score(
            box_score(), retrieved_at=RETRIEVED,
            stats=("points", "rebounds", "assists", "threepoint_goals"),
        )
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["event_id"], "global:9000500")
        self.assertEqual(rows[0]["player_id"], "100")
        self.assertEqual(rows[0]["outcome_available_at"], UPDATED.isoformat())
        self.assertEqual(rows[0]["outcome_value"], 24.0)
        self.assertEqual(rows[0]["outcome_semantics"], "count")
        three = rows[-1]
        self.assertEqual(three["outcome_value"], 3.0)
        self.assertEqual(three["opportunity_count"], 8)
        self.assertEqual(
            three["outcome_semantics"], "successes_of_opportunities")

    def test_updated_is_conservative_availability_boundary(self):
        late_update = datetime(2026, 1, 12, 9, 0, tzinfo=ET)
        retrieved = datetime(2026, 1, 12, 15, 0, tzinfo=timezone.utc)
        rows = map_box_score(
            box_score(updated=late_update), retrieved_at=retrieved,
            stats=("points",))
        p = policy()
        canonical = canonicalize_provider_record(
            rows[0], provider_id=PROVIDER_ID, registry=registry())
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id=PROVIDER_ID, policy=p, fetcher=lambda _: [canonical])
        obs = adapter.ingest(retrieved)[0]

        before_correction = IngestionValidator(
            datetime(2026, 1, 12, 8, 0, tzinfo=ET),
            trusted_source_policy=p,
        )
        self.assertFalse(before_correction.validate_observation(obs))

        after_correction = IngestionValidator(
            datetime(2026, 1, 12, 10, 0, tzinfo=ET),
            trusted_source_policy=p,
        )
        self.assertTrue(after_correction.validate_observation(obs))

    def test_canonicalization_precedes_cross_provider_reconciliation(self):
        rows = map_box_score(
            box_score(), retrieved_at=RETRIEVED, stats=("points",))
        out = canonicalize_provider_record(
            rows[0], provider_id=PROVIDER_ID, registry=registry())
        self.assertEqual(out["event_id"], "event:lal-ny-2026-01-10")
        self.assertEqual(out["team_id"], "team:lal")
        self.assertEqual(out["player_id"], "player:test")

    def test_nonfinal_box_score_emits_no_rows(self):
        self.assertEqual(
            map_box_score(
                box_score(status="Postponed"),
                retrieved_at=RETRIEVED, stats=("points",)),
            [],
        )

    def test_player_crossrefs_use_documented_ids(self):
        refs = extract_player_crossrefs({
            "PlayerID": 100,
            "SportRadarPlayerID": "sr-100",
            "RotoWirePlayerID": 555,
            "StatsPlayerID": 777,
            "SportsDirectPlayerID": None,
        })
        self.assertEqual(refs["sportsdataio_player_id"], 100)
        self.assertEqual(refs["sportradar_player_id"], "sr-100")
        self.assertEqual(refs["rotowire_player_id"], 555)
        self.assertNotIn("sportsdirect_player_id", refs)

    def test_player_game_not_over_fails_closed(self):
        bad = box_score()
        bad["PlayerGames"][0]["IsGameOver"] = False
        with self.assertRaises(ValueError):
            map_box_score(bad, retrieved_at=RETRIEVED, stats=("points",))


if __name__ == "__main__":
    unittest.main()
