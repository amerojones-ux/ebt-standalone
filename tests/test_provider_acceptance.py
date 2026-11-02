import unittest
from copy import deepcopy
from extensions.provider_acceptance import validate_receipt

BASE = dict(provider="example-provider",endpoint_id="fixture-endpoint",
 checked_at="2026-11-02T16:00:00Z",status="PASS",coverage="NBA",
 schema_verified=True,rights_verified=True,identity_verified=True,
 freshness_verified=True)

class ProviderAcceptanceTests(unittest.TestCase):
 def test_complete_receipt_is_review_only(self):
  result=validate_receipt(BASE)
  self.assertTrue(result["eligible_for_review"])
  self.assertFalse(result["forecast_approved"])
 def test_failed_check_holds(self):
  r=deepcopy(BASE);r["freshness_verified"]=False
  self.assertEqual(validate_receipt(r)["status"],"HOLD")
 def test_credentials_rejected(self):
  r=deepcopy(BASE);r["api_key"]="do-not-store"
  with self.assertRaises(ValueError): validate_receipt(r)
 def test_invalid_time_rejected(self):
  r=deepcopy(BASE);r["checked_at"]="2026-11-02 16:00:00"
  with self.assertRaises(ValueError): validate_receipt(r)
 def test_missing_coverage_rejected(self):
  r=deepcopy(BASE);r["coverage"]=""
  with self.assertRaises(ValueError): validate_receipt(r)
 def test_invalid_flag_rejected(self):
  r=deepcopy(BASE);r["rights_verified"]="true"
  with self.assertRaises(ValueError): validate_receipt(r)
