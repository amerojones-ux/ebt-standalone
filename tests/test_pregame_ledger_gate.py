import unittest
from copy import deepcopy
from extensions.pregame_ledger_gate import validate_pregame_record

BASE = dict(forecast_id="f1", event_id="e1", subject_id="p1",
 competition="NBA", market="points", comparator="GT", threshold="19.5",
 probability="0.70", model_version="research-v1", source_hash="sha256:example",
 issued_at="2026-11-02T18:00:00Z", event_start="2026-11-02T19:00:00Z")

class PregameLedgerGateTests(unittest.TestCase):
 def test_valid_stays_hold(self):
  result = validate_pregame_record(BASE)
  self.assertEqual(result["status"], "HOLD_RESEARCH_ONLY")
  self.assertFalse(result["forecast_approved"])
 def test_missing(self):
  r=deepcopy(BASE); del r["event_id"]
  with self.assertRaises(ValueError): validate_pregame_record(r)
 def test_after_start(self):
  r=deepcopy(BASE); r["issued_at"]=r["event_start"]
  with self.assertRaises(ValueError): validate_pregame_record(r)
 def test_future_source(self):
  r=deepcopy(BASE); r["source_effective_at"]="2026-11-02T18:30:00Z"
  with self.assertRaises(ValueError): validate_pregame_record(r)
 def test_invalid_probability(self):
  for p in ("NaN", "Infinity", "1.1", "-0.1"):
   r=deepcopy(BASE); r["probability"]=p
   with self.assertRaises(ValueError): validate_pregame_record(r)
 def test_approval_block(self):
  r=deepcopy(BASE); r["wager_approved"]=True
  with self.assertRaises(ValueError): validate_pregame_record(r)
 def test_naive_time_block(self):
  r=deepcopy(BASE); r["issued_at"]="2026-11-02T18:00:00"
  with self.assertRaises(ValueError): validate_pregame_record(r)

if __name__ == "__main__":
 unittest.main()
