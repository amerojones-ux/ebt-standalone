"""Synthetic provider evidence gate regression tests."""
import unittest
from extensions.provider_evidence_gate import REQUIRED, evaluate_provider_evidence

class ProviderEvidenceGateTests(unittest.TestCase):
    def test_missing_evidence_blocks_ingestion(self):
        result = evaluate_provider_evidence("weather", {})
        self.assertEqual(result["evidence_completeness"], "INCOMPLETE")
        self.assertEqual(set(result["missing_requirements"]), set(REQUIRED))
        self.assertEqual(result["production_ingestion"], "BLOCKED")

    def test_caller_claims_cannot_grant_approval(self):
        result = evaluate_provider_evidence("rapidapi", {name: True for name in REQUIRED})
        self.assertEqual(result["evidence_completeness"], "CLAIMED_COMPLETE_UNVERIFIED")
        self.assertEqual(result["licensed_feed"], "NOT_VERIFIED")
        self.assertEqual(result["credential_validity"], "NOT_VERIFIED")
        self.assertEqual(result["forecast"], "HOLD")
        self.assertEqual(result["wager"], "NOT APPROVED")

    def test_non_boolean_evidence_is_not_accepted(self):
        result = evaluate_provider_evidence("sportradar", {name: "true" for name in REQUIRED})
        self.assertEqual(set(result["missing_requirements"]), set(REQUIRED))

    def test_invalid_provider_identifier_rejected(self):
        for value in ("", "../secret", "provider with spaces", 123):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    evaluate_provider_evidence(value, {})

if __name__ == "__main__":
    unittest.main()
