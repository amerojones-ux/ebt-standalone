import unittest
from extensions.provider_coverage_matrix import assess_coverage, PROVIDERS

NOW="2026-11-02T16:00:00Z"

class CoverageMatrixTests(unittest.TestCase):
 def test_missing_providers_hold(self):
  result=assess_coverage([],trusted_now=NOW)
  self.assertEqual(len(result["providers"]),7)
  self.assertFalse(result["all_reviewable"])
  self.assertFalse(result["live_connections_verified"])
 def test_unknown_provider_rejected(self):
  with self.assertRaises(ValueError):
   assess_coverage([{"provider":"unknown"}],trusted_now=NOW)
 def test_duplicate_provider_rejected(self):
  r={"provider":PROVIDERS[0]}
  with self.assertRaises(ValueError):
   assess_coverage([r,r],trusted_now=NOW)
 def test_non_list_rejected(self):
  with self.assertRaises(ValueError):
   assess_coverage({},trusted_now=NOW)
