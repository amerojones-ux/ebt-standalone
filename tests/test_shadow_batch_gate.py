import unittest
from copy import deepcopy
from extensions.shadow_batch_gate import validate_batch

BASE = dict(forecast_id="f1",event_id="e1",subject_id="p1",competition="NBA",
market="points",comparator="GT",threshold="19.5",probability="0.7",
model_version="research",source_hash="test",issued_at="2026-11-02T18:00:00Z",
event_start="2026-11-02T19:00:00Z")

class BatchGateTests(unittest.TestCase):
 def test_valid_batch_stays_hold(self):
  b=deepcopy(BASE); b["forecast_id"]="f2"
  result=validate_batch([BASE,b])
  self.assertEqual(result["event_count"],1)
  self.assertEqual(result["forecast_count"],2)
  self.assertFalse(result["certified"])
 def test_duplicate_rejected(self):
  with self.assertRaises(ValueError): validate_batch([BASE,BASE])
 def test_conflicting_start_rejected(self):
  b=deepcopy(BASE); b["forecast_id"]="f2"; b["event_start"]="2026-11-02T20:00:00Z"
  with self.assertRaises(ValueError): validate_batch([BASE,b])
 def test_empty_rejected(self):
  with self.assertRaises(ValueError): validate_batch([])
 def test_invalid_record_rejected(self):
  b=deepcopy(BASE); b["probability"]="NaN"
  with self.assertRaises(ValueError): validate_batch([b])
