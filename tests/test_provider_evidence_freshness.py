"""Synthetic tests for fail-closed provider evidence freshness."""
import unittest
from extensions.provider_evidence_freshness import assess_evidence_freshness

AS_OF = "2026-10-30T20:00:00Z"
def record(timestamp="2026-10-29T20:00:00Z"):
    return {"reviewed_at_utc": timestamp, "reviewer_id": "reviewer-1",
            "evidence_reference": "internal-reviewed-record"}

class ProviderEvidenceFreshnessTests(unittest.TestCase):
    def test_freshness_never_authenticates(self):
        result = assess_evidence_freshness(record(), as_of_utc=AS_OF)
        self.assertEqual(result["freshness"], "FRESHNESS_ONLY")
        self.assertIs(result["reviewer_authenticated"], False)
        self.assertEqual(result["live_ingestion"], "BLOCKED")

    def test_stale_and_future_rejected(self):
        old = assess_evidence_freshness(record("2026-08-01T20:00:00Z"), as_of_utc=AS_OF)
        future = assess_evidence_freshness(record("2026-11-01T20:00:00Z"), as_of_utc=AS_OF)
        self.assertEqual(old["freshness"], "STALE_REVIEW")
        self.assertEqual(future["freshness"], "FUTURE_REVIEW_REJECTED")

    def test_missing_review_metadata(self):
        item = record()
        item["reviewer_id"] = ""
        result = assess_evidence_freshness(item, as_of_utc=AS_OF)
        self.assertEqual(result["freshness"], "MISSING_REVIEW_PROVENANCE")

    def test_naive_timestamp_and_bool_age_rejected(self):
        with self.assertRaises(ValueError):
            assess_evidence_freshness(record("2026-10-29T20:00:00"), as_of_utc=AS_OF)
        with self.assertRaises(ValueError):
            assess_evidence_freshness(record(), as_of_utc=AS_OF, max_age_days=True)

if __name__ == "__main__":
    unittest.main()
