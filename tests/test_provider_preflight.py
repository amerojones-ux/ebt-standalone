"""Synthetic checks for offline seven-provider configuration preflight."""
import unittest

from extensions.provider_gateway import PROVIDERS
from extensions.provider_preflight import audit_intake, REQUIRED_GATE_NAMES

def fixture():
    return {
        "schema_version": 1,
        "release_gates": {
            "forecast": "HOLD", "wager": "NOT_APPROVED",
            "live_probe_requires": list(REQUIRED_GATE_NAMES),
        },
        "providers": {
            name: {
                "secret_name": secret,
                "product": "pending_subscribed_upstream_product" if name == "rapidapi" else
                           ("WeatherAPI.com" if name == "weather" else name),
                "reviewed_endpoint": "pending",
                "reviewed_auth_scheme": "pending",
                "entitlements": "pending",
            } for name, secret in PROVIDERS.items()
        },
    }

class ProviderPreflightTests(unittest.TestCase):
    def test_no_live_probe_or_approval(self):
        report = audit_intake(fixture())
        self.assertEqual(report["forecast"], "HOLD")
        self.assertEqual(report["wager"], "NOT_APPROVED")
        self.assertIs(report["live_probes_executed"], False)
        self.assertEqual(len(report["providers"]), 7)
        self.assertTrue(all(p["live_authentication"] == "NOT_TESTED" for p in report["providers"]))

    def test_missing_vendor_identified(self):
        report = audit_intake(fixture())
        rapid = next(p for p in report["providers"] if p["provider"] == "rapidapi")
        self.assertIn("subscribed_upstream_product", rapid["missing"])

    def test_rejects_release_gate_override(self):
        intake = fixture()
        intake["release_gates"]["forecast"] = "APPROVED"
        with self.assertRaises(ValueError):
            audit_intake(intake)

    def test_rejects_provider_secret_mismatch(self):
        intake = fixture()
        intake["providers"]["weather"]["secret_name"] = "WRONG"
        with self.assertRaises(ValueError):
            audit_intake(intake)

    def test_rejects_missing_egress_gate(self):
        intake = fixture()
        intake["release_gates"]["live_probe_requires"].remove("infrastructure_egress_allowlist")
        with self.assertRaises(ValueError):
            audit_intake(intake)

if __name__ == "__main__":
    unittest.main()
