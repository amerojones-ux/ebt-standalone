import unittest
from ebt_release_manifest import audit_manifest
from ebt_certification import CertificationHold

KEYS=("source_policy","identity","availability","schedule",
      "history","calibration","operational_signoff")
class ManifestTests(unittest.TestCase):
    def test_hold_and_reviewed_remain_unapproved(self):
        m={"schema_version":"1.0","gates":{k:{"status":"HOLD"} for k in KEYS}}
        result=audit_manifest(m)
        self.assertEqual(result["status"],"HOLD")
        self.assertFalse(result["forecast_approved"])
        self.assertEqual(result["manifest_sha256"],audit_manifest(m)["manifest_sha256"])
        m["gates"]={k:{"status":"REVIEWED","reviewer":"synthetic",
                        "evidence_ids":["fixture"]} for k in KEYS}
        result=audit_manifest(m)
        self.assertEqual(result["status"],"MANUAL_RELEASE_REVIEW_REQUIRED")
        self.assertFalse(result["forecast_approved"])
    def test_missing_evidence_or_gate_fails(self):
        m={"schema_version":"1.0","gates":{k:{"status":"HOLD"} for k in KEYS}}
        del m["gates"]["history"]
        with self.assertRaises(CertificationHold):
            audit_manifest(m)
        m["gates"]["history"]={"status":"REVIEWED","reviewer":"x"}
        with self.assertRaises(CertificationHold):
            audit_manifest(m)
if __name__=="__main__":
    unittest.main()
