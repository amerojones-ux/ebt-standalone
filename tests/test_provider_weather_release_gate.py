"""Offline tests for the independent weather integration release gate."""
import unittest

from extensions.weather_release_gate import REQUIREMENTS, evaluate_weather_release


class WeatherReleaseGateTests(unittest.TestCase):
    def test_empty_evidence_holds(self):
        r = evaluate_weather_release({})
        self.assertEqual(r["integration_status"], "HOLD")
        self.assertEqual(set(r["unmet_requirements"]), set(REQUIREMENTS))
        self.assertFalse(r["weather_feature_eligible"])

    def test_missing_one_requirement_holds(self):
        evidence = {name: True for name in REQUIREMENTS}
        evidence["data_retention_rights_verified"] = False
        r = evaluate_weather_release(evidence)
        self.assertEqual(r["unmet_requirements"], ["data_retention_rights_verified"])
        self.assertEqual(r["integration_status"], "HOLD")

    def test_truthy_values_not_accepted(self):
        for invalid in ("true", 1, [], None):
            with self.subTest(invalid=invalid):
                evidence = {name: True for name in REQUIREMENTS}
                evidence["live_auth_verified"] = invalid
                self.assertEqual(evaluate_weather_release(evidence)["integration_status"], "HOLD")

    def test_all_evidence_only_approves_integration(self):
        evidence = {name: True for name in REQUIREMENTS}
        r = evaluate_weather_release(evidence)
        self.assertEqual(r["integration_status"], "APPROVED")
        self.assertEqual(r["forecast"], "HOLD")
        self.assertEqual(r["wager"], "NOT APPROVED")

    def test_invalid_input_holds(self):
        self.assertEqual(evaluate_weather_release(None)["integration_status"], "HOLD")

    def test_secrets_never_echoed(self):
        r = evaluate_weather_release({"secret": "SENSITIVE"})
        self.assertNotIn("SENSITIVE", str(r))


if __name__ == "__main__":
    unittest.main()
