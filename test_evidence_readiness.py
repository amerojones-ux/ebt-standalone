import unittest
from ebt_evidence_readiness import evidence_readiness, REQUIRED
from ebt_certification import CertificationHold

class ReadinessTests(unittest.TestCase):
    def test_missing_evidence_is_hold(self):
        result=evidence_readiness({})
        self.assertEqual(set(result["missing_or_unreviewed"]),set(REQUIRED))
        self.assertFalse(result["forecast_approved"])
    def test_self_asserted_reviews_do_not_authorize_release(self):
        entries={key:{"status":"REVIEWED","reviewer":"fixture",
                      "evidence_ids":["synthetic"]} for key in REQUIRED}
        result=evidence_readiness(entries)
        self.assertEqual(result["missing_or_unreviewed"],[])
        self.assertEqual(result["release_status"],"HOLD")
        self.assertFalse(result["externally_authenticated"])
    def test_unknown_gate_rejected(self):
        with self.assertRaises(CertificationHold):
            evidence_readiness({"unexpected":{}})
if __name__=="__main__":
    unittest.main()
