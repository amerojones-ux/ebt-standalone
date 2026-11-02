import unittest
from copy import deepcopy
from extensions.provider_evidence_gate import assess_provider_evidence

BASE = dict(provider="fixture",endpoint_id="fixture",checked_at="2026-11-02T16:00:00Z",
status="PASS",coverage="NBA",schema_verified=True,rights_verified=True,
identity_verified=True,freshness_verified=True,http_status=200,record_count=3,
response_sha256="a"*64,data_as_of="2026-11-02T15:59:00Z")
NOW="2026-11-02T16:01:00Z"

class ProviderEvidenceTests(unittest.TestCase):
 def test_complete_is_review_only_not_verified(self):
  r=assess_provider_evidence(BASE,trusted_now=NOW)
  self.assertEqual(r["status"],"REVIEW_ONLY")
  self.assertFalse(r["independently_verified"])
  self.assertFalse(r["forecast_approved"])
 def test_missing_digest_holds(self):
  x=deepcopy(BASE);del x["response_sha256"]
  self.assertEqual(assess_provider_evidence(x,trusted_now=NOW)["status"],"HOLD")
 def test_stale_receipt_holds(self):
  self.assertEqual(assess_provider_evidence(BASE,trusted_now="2026-11-02T19:00:00Z")["status"],"HOLD")
 def test_future_receipt_rejected(self):
  with self.assertRaises(ValueError): assess_provider_evidence(BASE,trusted_now="2026-11-02T15:00:00Z")
 def test_empty_response_holds(self):
  x=deepcopy(BASE);x["record_count"]=0
  self.assertEqual(assess_provider_evidence(x,trusted_now=NOW)["status"],"HOLD")
 def test_old_data_holds(self):
  x=deepcopy(BASE);x["data_as_of"]="2026-11-01T10:00:00Z"
  self.assertEqual(assess_provider_evidence(x,trusted_now=NOW)["status"],"HOLD")
 def test_future_data_holds(self):
  x=deepcopy(BASE);x["data_as_of"]="2026-11-02T16:01:00Z"
  self.assertEqual(assess_provider_evidence(x,trusted_now=NOW)["status"],"HOLD")
