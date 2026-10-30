"""Synthetic weather evidence-audit tests, no secrets or network."""
import unittest

from extensions.weather_release_gate import REQUIREMENTS
from extensions.weather_release_audit import OWNER, audit_weather_release


def records():
    return {name: {"passed": True, "reviewer_role": OWNER[name],
                   "evidence_id": f"review-{i:04d}-{name}"}
            for i, name in enumerate(REQUIREMENTS)}


class WeatherReleaseAuditTests(unittest.TestCase):
    def test_missing_evidence_holds(self):
        r = audit_weather_release({})
        self.assertEqual(r["audit_status"], "INCOMPLETE")
        self.assertEqual(r["integration_status"], "HOLD")

    def test_full_synthetic_metadata_not_platform_approval(self):
        r = audit_weather_release(records())
        self.assertEqual(r["audit_status"], "COMPLETE")
        self.assertEqual(r["integration_status"], "APPROVED")
        self.assertEqual(r["forecast"], "HOLD")
        self.assertEqual(r["wager"], "NOT APPROVED")

    def test_wrong_reviewer_fails(self):
        e = records()
        e["subscription_rights_verified"]["reviewer_role"] = "security"
        self.assertIn("subscription_rights_verified",
                      audit_weather_release(e)["unverified_evidence"])

    def test_reused_reference_fails(self):
        e = records()
        e["egress_enforced"]["evidence_id"] = e["protected_runner_reviewed"]["evidence_id"]
        self.assertEqual(audit_weather_release(e)["integration_status"], "HOLD")

    def test_secret_or_url_reference_rejected(self):
        e = records()
        e["live_auth_verified"]["evidence_id"] = "https://example.test?key=SECRET"
        self.assertEqual(audit_weather_release(e)["integration_status"], "HOLD")
        self.assertNotIn("SECRET", str(audit_weather_release(e)))

    def test_untrusted_truthy_pass_rejected(self):
        e = records()
        e["feed_schema_verified"]["passed"] = 1
        self.assertEqual(audit_weather_release(e)["integration_status"], "HOLD")


if __name__ == "__main__":
    unittest.main()
