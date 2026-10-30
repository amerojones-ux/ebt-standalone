"""Synthetic policy tests; no secrets or network."""
import unittest
from extensions.provider_policy import evaluate_use
from extensions.provider_gateway import ProviderGateError


class ProviderPolicyTests(unittest.TestCase):
    def test_market_quotes_never_train_independent_projection(self):
        for p in ("therundown", "theoddsapi"):
            with self.subTest(provider=p):
                d = evaluate_use(p, "independent_projection", documented_entitlement=True)
                self.assertEqual(d.status, "DENIED")
                self.assertEqual(d.forecast, "HOLD")

    def test_rapidapi_requires_upstream_identity(self):
        self.assertEqual(evaluate_use("rapidapi", "live_ingestion").status, "BLOCKED")
        self.assertEqual(evaluate_use("rapidapi", "live_ingestion",
                                      upstream_provider="unknown").status, "BLOCKED")

    def test_stats_sources_not_automatically_approved(self):
        for p in ("sportsdata", "apisports", "sportradar"):
            with self.subTest(provider=p):
                self.assertEqual(evaluate_use(p, "independent_projection",
                                              documented_entitlement=True).status, "BLOCKED")

    def test_weather_requires_feature_mapping(self):
        self.assertEqual(evaluate_use("weather", "independent_projection").status, "BLOCKED")

    def test_market_comparison_limited_to_market_sources(self):
        self.assertEqual(evaluate_use("sportradar", "market_comparison").status, "BLOCKED")

    def test_invalid_provider_rejected(self):
        with self.assertRaises(ProviderGateError):
            evaluate_use([], "historical_training")

    def test_invalid_purpose_rejected(self):
        with self.assertRaises(ProviderGateError):
            evaluate_use("sportradar", "deploy_production")


if __name__ == "__main__":
    unittest.main()
