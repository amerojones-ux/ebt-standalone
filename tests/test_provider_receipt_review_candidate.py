import unittest

from apisports_status_receipt import build_receipt as build_apisports
from theoddsapi_probe_receipt import build_receipt as build_odds
from weatherapi_probe_receipt import build_receipt as build_weather
from provider_receipt_review_candidate import build_review_candidate

COMMIT="a"*40
RUN="123456"

class ProviderReceiptReviewCandidateTests(unittest.TestCase):
    def test_weather_pass_becomes_review_only_candidate(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        c=build_review_candidate(r)
        self.assertEqual(c["provider"],"WeatherAPI")
        self.assertEqual(c["candidate_status"],"REVIEW_ONLY")
        self.assertFalse(c["readiness_mutation_permitted"])
        self.assertFalse(c["forecast_activation_permitted"])

    def test_odds_pass_becomes_review_only_candidate(self):
        r=build_odds(
            {"status":"PASS","category":"authenticated_zero_credit_sports_schema"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        self.assertEqual(build_review_candidate(r)["provider"],"The Odds API")

    def test_apisports_pass_becomes_review_only_candidate(self):
        r=build_apisports(
            {"status":"PASS","category":"authenticated_status_schema"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        self.assertEqual(build_review_candidate(r)["provider"],"API-Sports")

    def test_hold_receipt_rejected(self):
        r=build_weather(
            {"status":"HOLD","category":"transport_error"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        with self.assertRaises(ValueError):
            build_review_candidate(r)

    def test_tampered_receipt_rejected(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        r["status"]="HOLD"
        with self.assertRaises(ValueError):
            build_review_candidate(r)

    def test_missing_commit_rejected(self):
        r=build_odds(
            {"status":"PASS","category":"authenticated_zero_credit_sports_schema"},
            "2026-11-02T20:00:00+00:00","",RUN
        )
        with self.assertRaises(ValueError):
            build_review_candidate(r)

    def test_missing_run_id_rejected(self):
        r=build_apisports(
            {"status":"PASS","category":"authenticated_status_schema"},
            "2026-11-02T20:00:00+00:00",COMMIT,""
        )
        with self.assertRaises(ValueError):
            build_review_candidate(r)

    def test_candidate_contains_only_sanitized_provenance(self):
        r=build_weather(
            {"status":"PASS","category":"authenticated_schema_fresh"},
            "2026-11-02T20:00:00+00:00",COMMIT,RUN
        )
        c=build_review_candidate(r)
        rendered=repr(c).lower()
        self.assertNotIn("api_key",rendered)
        self.assertNotIn("headers",rendered)
        self.assertNotIn("response",rendered)
        self.assertNotIn("quota",rendered)

if __name__=="__main__":
    unittest.main()
