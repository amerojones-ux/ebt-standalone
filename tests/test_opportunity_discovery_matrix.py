"""Synthetic regression tests for the V7/V7.1 opportunity-discovery matrix."""
import unittest

from extensions.opportunity_discovery_matrix import (
    competing_risk_probabilities,
    detect_role_reallocation,
    discover_count_market_expressions,
    evaluate_rare_event_quotes,
    reconcile_result_claim,
)


PMF = {
    "0":"0.02","1":"0.03","2":"0.10","3":"0.20",
    "4":"0.25","5":"0.20","6":"0.12","7":"0.08",
}
POLICY = {
    "safe_modeled_probability_min":"0.80",
    "tail_modeled_probability_min":"0.10",
    "minimum_probability_edge":"0.03",
}
LOCK = "2026-11-07T00:00:00-06:00"


class OpportunityDiscoveryMatrixTests(unittest.TestCase):
    def test_safe_alt_and_tail_value_are_separate(self):
        quotes = [
            {
                "market_id":"p-2plus","book":"Synthetic","comparator":"GE","threshold":"2",
                "american_odds":-500,"quoted_at":"2026-11-07T00:01:00-06:00",
                "ingested_at":"2026-11-07T00:02:00-06:00","price_verified":True,
            },
            {
                "market_id":"p-6plus","book":"Synthetic","comparator":"GE","threshold":"6",
                "american_odds":700,"quoted_at":"2026-11-07T00:01:00-06:00",
                "ingested_at":"2026-11-07T00:02:00-06:00","price_verified":True,
            },
        ]
        out = discover_count_market_expressions(
            PMF, quotes, projection_locked_at=LOCK, market_family_policy=POLICY)
        lanes = {x["market_id"]:x["lane"] for x in out["expressions"]}
        self.assertEqual(lanes["p-2plus"], "SAFE_ALT_RESEARCH")
        self.assertEqual(lanes["p-6plus"], "TAIL_VALUE_RESEARCH")
        self.assertEqual(out["wager_status"], "NOT APPROVED")
        self.assertFalse(out["calibration_verified"])

    def test_market_ingestion_before_projection_lock_is_rejected(self):
        quote = [{
            "market_id":"x","book":"Synthetic","comparator":"GE","threshold":"2",
            "american_odds":-200,"quoted_at":"2026-11-06T23:00:00-06:00",
            "ingested_at":"2026-11-06T23:30:00-06:00","price_verified":True,
        }]
        with self.assertRaises(ValueError):
            discover_count_market_expressions(
                PMF, quote, projection_locked_at=LOCK, market_family_policy=POLICY)

    def test_confirmed_role_change_forces_full_rerun(self):
        before = {
            "A":{"availability":"ACTIVE","role":"STARTER","expected_opportunity":"30",
                 "available_at":"2026-11-07T16:00:00-06:00"},
            "B":{"availability":"ACTIVE","role":"BENCH","expected_opportunity":"10",
                 "available_at":"2026-11-07T16:00:00-06:00"},
        }
        after = {
            "A":{"availability":"OUT","role":"OUT","expected_opportunity":"0",
                 "available_at":"2026-11-07T17:00:00-06:00"},
            "B":{"availability":"ACTIVE","role":"STARTER","expected_opportunity":"35",
                 "available_at":"2026-11-07T17:00:00-06:00"},
        }
        out = detect_role_reallocation(
            before, after, event_start="2026-11-07T19:00:00-06:00",
            unit="minutes", official_confirmation=True, source_status="FOUND",
            material_share_threshold="0.10")
        self.assertEqual(out["decision_action"], "FULL_RERUN_REQUIRED")
        self.assertTrue(out["forced_absence_detected"])
        self.assertEqual(out["beneficiaries"][0]["player_id"], "B")

    def test_unconfirmed_role_change_holds(self):
        before = {
            "A":{"availability":"ACTIVE","role":"STARTER","expected_opportunity":"30",
                 "available_at":"2026-11-07T16:00:00-06:00"}
        }
        after = {
            "A":{"availability":"OUT","role":"OUT","expected_opportunity":"0",
                 "available_at":"2026-11-07T17:00:00-06:00"}
        }
        out = detect_role_reallocation(
            before, after, event_start="2026-11-07T19:00:00-06:00",
            unit="minutes", official_confirmation=False, source_status="STALE",
            material_share_threshold="0.10")
        self.assertEqual(out["decision_action"], "HOLD_FOR_CONFIRMATION")

    def test_competing_risk_probability_mass(self):
        out = competing_risk_probabilities({"A":"2","B":"1"}, no_event_hazard="1")
        total = sum(out["candidate_probabilities"].values()) + out["no_event_probability"]
        self.assertAlmostEqual(total, 1.0)
        self.assertAlmostEqual(out["candidate_probabilities"]["A"], 0.5)

    def test_rare_event_value_never_enters_black_diamond_survival(self):
        quotes = [{
            "candidate_id":"A","book":"Synthetic","american_odds":700,
            "quoted_at":"2026-11-07T00:01:00-06:00",
            "ingested_at":"2026-11-07T00:02:00-06:00","price_verified":True,
        }]
        out = evaluate_rare_event_quotes(
            {"A":"0.20","B":"0.15"}, quotes, model_locked_at=LOCK,
            minimum_probability_edge="0.03", minimum_modeled_probability="0.10")
        row = out["candidates"][0]
        self.assertEqual(row["lane"], "ASYMMETRIC_VALUE_RESEARCH")
        self.assertFalse(row["black_diamond_survival_eligible"])
        self.assertEqual(row["wager_status"], "NOT APPROVED")

    def test_conflicting_screenshot_claim_is_quarantined(self):
        official = {
            "event_id":"G1","participant_a_id":"A","participant_b_id":"B",
            "score_a":119,"score_b":95,"player_stats":{"P:assists":2},
        }
        claim = {
            "event_id":"G1","participant_a_id":"A","participant_b_id":"B",
            "score_a":110,"score_b":99,"player_stats":{"P:assists":6},
        }
        out = reconcile_result_claim(claim, official)
        self.assertEqual(out["status"], "QUARANTINED")
        self.assertFalse(out["eligible_for_model_learning"])
        self.assertGreaterEqual(len(out["conflicts"]), 2)

    def test_reconciled_claim_is_only_learning_eligible(self):
        official = {
            "event_id":"G1","participant_a_id":"A","participant_b_id":"B",
            "score_a":119,"score_b":95,"player_stats":{"P:assists":2},
        }
        out = reconcile_result_claim(dict(official), official)
        self.assertEqual(out["status"], "RECONCILED")
        self.assertTrue(out["eligible_for_model_learning"])


if __name__ == "__main__":
    unittest.main()
