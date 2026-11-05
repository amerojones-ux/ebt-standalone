"""API-Sports Basketball historical mapping and edge-case tests."""
import unittest
from datetime import datetime, timedelta, timezone

from extensions.apisports_basketball_historical import (
    PROVIDER_ID, audit_edge_case_policy, classify_game_status,
    map_player_statistics, parse_minutes,
)
from extensions.connectors import OfficialBoxScoreSnapshotAdapter
from extensions.data_ingestion import IngestionValidator, resolve_provider_revisions
from extensions.trusted_sources import SourceRule, TrustedSourcePolicy

T0 = datetime(2026, 1, 10, 1, 0, tzinfo=timezone.utc)
KEY = "apisports-basketball-historical-test-key"


def policy():
    return TrustedSourcePolicy(
        [SourceRule(PROVIDER_ID, "B2", ("results", "historical_stats"))],
        attestation_key=KEY,
    )


def game(status="FT"):
    return {
        "id": 9001,
        "date": T0.isoformat(),
        "status": {"short": status, "long": "test"},
    }


def player(points=16, minutes="32:53"):
    return {
        "game": {"id": 9001},
        "team": {"id": 132},
        "player": {"id": 4237, "name": "Test Player"},
        "type": "starters",
        "minutes": minutes,
        "field_goals": {"total": 0, "attempts": 1, "percentage": None},
        "threepoint_goals": {"total": 4, "attempts": 10, "percentage": None},
        "freethrows_goals": {"total": 4, "attempts": 4, "percentage": None},
        "rebounds": {"total": 4},
        "assists": 1,
        "points": points,
    }


class APISportsHistoricalTests(unittest.TestCase):
    def test_documented_final_states_only(self):
        self.assertTrue(classify_game_status("FT").final_stats_eligible)
        self.assertTrue(classify_game_status("AOT").final_stats_eligible)
        for status in ("NS", "Q1", "HT", "OT", "POST", "CANC", "SUSP", "AWD", "ABD"):
            self.assertFalse(classify_game_status(status).final_stats_eligible)

    def test_postponed_and_awarded_fail_closed(self):
        post = audit_edge_case_policy(game("POST"))
        awarded = audit_edge_case_policy(game("AWD"))
        self.assertEqual(post["category"], "POSTPONED")
        self.assertEqual(awarded["category"], "AWARDED_HOLD")
        self.assertFalse(post["settlement_eligible"])
        self.assertFalse(awarded["settlement_eligible"])

    def test_minutes_parsing(self):
        self.assertAlmostEqual(parse_minutes("32:30"), 32.5)
        self.assertIsNone(parse_minutes(None))
        with self.assertRaises(ValueError):
            parse_minutes("12:60")

    def test_final_player_stats_map_without_injury_inference(self):
        rows = map_player_statistics(
            game(), player(minutes="8:00"),
            outcome_available_at=T0 + timedelta(hours=3),
            retrieved_at=T0 + timedelta(hours=4),
            stats=("points", "rebounds", "assists"),
        )
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["minutes"], 8.0)
        self.assertEqual(rows[0]["pregame_features"], [])
        self.assertNotIn("injury", rows[0])
        self.assertEqual(rows[0]["outcome_semantics"], "count")
        self.assertEqual(rows[0]["opportunity_count"], 0)

    def test_conversion_stats_preserve_attempt_denominator(self):
        rows = map_player_statistics(
            game(), player(),
            outcome_available_at=T0 + timedelta(hours=3),
            retrieved_at=T0 + timedelta(hours=4),
            stats=("threepoint_goals", "freethrows_goals"),
        )
        three = rows[0]
        free = rows[1]
        self.assertEqual((three["outcome_value"], three["opportunity_count"]), (4.0, 10))
        self.assertEqual((free["outcome_value"], free["opportunity_count"]), (4.0, 4))
        self.assertEqual(three["outcome_semantics"], "successes_of_opportunities")

    def test_nonfinal_game_emits_no_stats(self):
        rows = map_player_statistics(
            game("SUSP"), player(),
            outcome_available_at=T0 + timedelta(hours=3),
            retrieved_at=T0 + timedelta(hours=4),
        )
        self.assertEqual(rows, [])

    def test_availability_time_is_never_inferred(self):
        with self.assertRaises(TypeError):
            map_player_statistics(
                game(), player(), retrieved_at=T0 + timedelta(hours=4))

    def test_stat_correction_is_cutoff_safe_and_latest_revision_wins(self):
        p = policy()
        first_raw = map_player_statistics(
            game(), player(points=16),
            outcome_available_at=T0 + timedelta(hours=3),
            retrieved_at=T0 + timedelta(hours=4),
            stats=("points",),
        )[0]
        corrected_raw = map_player_statistics(
            game(), player(points=17),
            outcome_available_at=T0 + timedelta(hours=5),
            retrieved_at=T0 + timedelta(hours=6),
            stats=("points",),
        )[0]
        adapter = OfficialBoxScoreSnapshotAdapter(
            provider_id=PROVIDER_ID, policy=p,
            fetcher=lambda _: [first_raw, corrected_raw],
        )
        observations = adapter.ingest(T0)

        early = IngestionValidator(
            T0 + timedelta(hours=4, minutes=30), trusted_source_policy=p)
        early_batch = early.validate_batch(observations)
        self.assertEqual(len(early_batch["accepted"]), 1)
        early_resolved = resolve_provider_revisions(
            early_batch["accepted"], trusted_source_policy=p)
        self.assertEqual(
            early_resolved["rows"][0].observation.outcome_value, 16.0)

        late = IngestionValidator(
            T0 + timedelta(hours=7), trusted_source_policy=p)
        late_batch = late.validate_batch(observations)
        self.assertEqual(len(late_batch["accepted"]), 2)
        resolved = resolve_provider_revisions(
            late_batch["accepted"], trusted_source_policy=p)
        self.assertEqual(resolved["rows"][0].observation.outcome_value, 17.0)
        self.assertTrue(resolved["audit"][0]["correction_observed"])
        self.assertEqual(resolved["audit"][0]["revision_count"], 2)


if __name__ == "__main__":
    unittest.main()
