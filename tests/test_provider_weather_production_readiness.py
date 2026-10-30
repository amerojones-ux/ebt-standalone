"""Negative tests for weather production readiness."""
import unittest
from extensions.weather_production_readiness import REQUIRED, assess_weather_production_readiness as assess


class ProductionReadinessTests(unittest.TestCase):
    def test_missing_all_blocks(self):
        r = assess({})
        self.assertEqual(r["readiness"], "BLOCKED")
        self.assertEqual(set(r["unmet_requirements"]), set(REQUIRED))

    def test_in_memory_replay_cannot_pass(self):
        e = {name: True for name in REQUIRED}
        e["durable_atomic_replay_store"] = False
        self.assertIn("durable_atomic_replay_store", assess(e)["unmet_requirements"])

    def test_all_claims_cannot_self_authorize(self):
        r = assess({name: True for name in REQUIRED})
        self.assertEqual(r["readiness"], "EXTERNAL_VERIFICATION_REQUIRED")
        self.assertEqual(r["production_deploy"], "NOT APPROVED")
        self.assertEqual(r["forecast"], "HOLD")
        self.assertEqual(r["wager"], "NOT APPROVED")

    def test_truthy_string_not_accepted(self):
        e = {name: True for name in REQUIRED}
        e["verified_live_authentication"] = "true"
        self.assertEqual(assess(e)["readiness"], "BLOCKED")

    def test_bad_input_blocks(self):
        self.assertEqual(assess(None)["readiness"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
