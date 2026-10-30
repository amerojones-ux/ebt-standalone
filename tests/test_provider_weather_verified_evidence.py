"""Synthetic tests for caller-asserted weather evidence boundary."""
import unittest

from extensions.weather_release_audit import OWNER
from extensions.weather_release_gate import REQUIREMENTS
from extensions.weather_verified_evidence import evaluate_verified_weather_evidence as check


def fixture():
    return {name: {"assertion_id": f"assertion{i:04d}test", "authority": "approved",
                   "externally_verified": True, "reviewer_role": OWNER[name]}
            for i, name in enumerate(REQUIREMENTS)}


class WeatherVerifiedEvidenceTests(unittest.TestCase):
    def test_no_assertions_holds(self):
        self.assertEqual(check({}, trusted_authorities=frozenset({"approved"}))["integration_status"], "HOLD")

    def test_untrusted_authority_holds(self):
        self.assertEqual(check(fixture(), trusted_authorities=frozenset())["integration_status"], "HOLD")

    def test_assertion_not_verified_holds(self):
        e = fixture()
        e["live_auth_verified"]["externally_verified"] = "true"
        self.assertEqual(check(e, trusted_authorities=frozenset({"approved"}))["integration_status"], "HOLD")

    def test_duplicate_assertion_holds(self):
        e = fixture()
        e["egress_enforced"]["assertion_id"] = e["protected_runner_reviewed"]["assertion_id"]
        self.assertEqual(check(e, trusted_authorities=frozenset({"approved"}))["integration_status"], "HOLD")

    def test_synthetic_approval_still_platform_hold(self):
        r = check(fixture(), trusted_authorities=frozenset({"approved"}))
        self.assertEqual(r["integration_status"], "APPROVED")
        self.assertEqual(r["forecast"], "HOLD")
        self.assertEqual(r["wager"], "NOT APPROVED")
        self.assertEqual(r["verification_boundary"], "CALLER_ASSERTED_EXTERNAL_VERIFICATION")

    def test_untrusted_metadata_not_echoed(self):
        r = check({"secret": "VERY_PRIVATE"}, trusted_authorities=frozenset({"approved"}))
        self.assertNotIn("VERY_PRIVATE", str(r))


if __name__ == "__main__":
    unittest.main()
