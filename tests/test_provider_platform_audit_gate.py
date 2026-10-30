"""Fail-closed offline release-registry contract; no network, secrets or live feeds."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "config" / "platform_audit_gate_2026_10_30.json"
READINESS = ROOT / "config" / "module_readiness_2026_10_30.json"

class PlatformAuditGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads(AUDIT.read_text(encoding="utf-8"))
        cls.readiness = json.loads(READINESS.read_text(encoding="utf-8"))

    def test_release_stays_fail_closed(self):
        self.assertEqual(self.audit["release"]["forecast"], "HOLD")
        self.assertEqual(self.audit["release"]["wager"], "NOT_APPROVED")
        self.assertIs(self.audit["release"]["production_deployment"], False)
        self.assertEqual(self.readiness["forecast_mode"], "HOLD_RESEARCH_ONLY")
        self.assertEqual(self.readiness["wager_mode"], "NOT_APPROVED")
        self.assertIs(self.readiness["deployment_enabled"], False)

    def test_no_unverified_component_claims_live_readiness(self):
        components = self.audit["components"]
        self.assertGreaterEqual(len(components), 10)
        for name, state in components.items():
            with self.subTest(component=name):
                self.assertIs(state["live_verified"], False)
                self.assertTrue(state["blockers"])
                self.assertNotIn(state["implementation"], ("PRODUCTION", "LIVE_CERTIFIED", "APPROVED"))

    def test_required_release_stages_are_explicit(self):
        stages = self.audit["acceptance_order"]
        self.assertEqual(len(stages), len(set(stages)))
        self.assertIn("provider_rights_and_identity", stages)
        self.assertIn("temporal_calibration", stages)
        self.assertIn("independent_security_and_release_review", stages)

    def test_audit_cannot_override_existing_readiness(self):
        self.assertEqual(self.audit["scope"], "ebt-black-diamond-sports-only")
        self.assertFalse(any(v is True for v in self.readiness["live_integrations"].values()))

if __name__ == "__main__":
    unittest.main()
