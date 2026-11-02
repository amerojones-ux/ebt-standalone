import unittest
from datetime import datetime, timezone, timedelta
from provider_verification import EndpointContract, Evidence, Verdict, evaluate

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
STAMP = NOW.isoformat()
CONTRACT = EndpointContract("example", "schedule", ("event_id", "status"), 3600)
GOOD = dict(http_status=200, payload={"event_id":"abc", "status":"scheduled"},
            published_at=STAMP, retrieved_at=STAMP, official_reconciled=True, authorized=True)

class VerificationTests(unittest.TestCase):
    def check(self, verdict, reason=None, **overrides):
        e = Evidence(**(GOOD | overrides))
        result = evaluate(CONTRACT, e, now=NOW)
        self.assertEqual(result.verdict, verdict)
        if reason:
            self.assertIn(reason, result.reasons)

    def test_pass(self): self.check(Verdict.PASS)
    def test_not_tested(self):
        self.assertEqual(evaluate(CONTRACT, None, now=NOW).verdict, Verdict.NOT_TESTED)
    def test_unauthorized(self): self.check(Verdict.FAIL, "AUTHORIZATION_FAILED", http_status=403)
    def test_rate_limited(self): self.check(Verdict.HOLD, "RATE_LIMITED", http_status=429)
    def test_missing_field(self): self.check(Verdict.FAIL, "REQUIRED_FIELDS_MISSING", payload={"event_id":"abc"})
    def test_null_field(self): self.check(Verdict.FAIL, "REQUIRED_FIELDS_MISSING", payload={"event_id":"abc","status":None})
    def test_stale(self):
        self.check(Verdict.HOLD, "SOURCE_STALE", published_at=(NOW-timedelta(hours=2)).isoformat())
    def test_refetch_not_fresh(self):
        self.check(Verdict.HOLD, "SOURCE_STALE", published_at=(NOW-timedelta(days=1)).isoformat(), retrieved_at=STAMP)
    def test_reconciliation(self): self.check(Verdict.HOLD, "OFFICIAL_RECONCILIATION_PENDING", official_reconciled=False)
    def test_missing_auth(self): self.check(Verdict.HOLD, "AUTHORIZATION_UNCONFIRMED", authorized=None)
    def test_future_publication(self):
        self.check(Verdict.HOLD, "TIMESTAMP_ORDER_INVALID", published_at=(NOW+timedelta(minutes=1)).isoformat())
    def test_naive_timestamp(self): self.check(Verdict.HOLD, "TIMESTAMP_UNVERIFIED", published_at="2026-11-01T12:00:00")
    def test_invalid_payload(self): self.check(Verdict.FAIL, "INVALID_PAYLOAD", payload=None)

if __name__ == "__main__":
    unittest.main()
