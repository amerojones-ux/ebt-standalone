import unittest
from ebt_certification_summary import certification_summary
from ebt_evidence_readiness import REQUIRED

class SummaryTests(unittest.TestCase):
    def test_all_review_claims_still_hold(self):
        checks={name:{"status":"REVIEWED","reviewer":"fixture",
                      "evidence_ids":["synthetic"]} for name in REQUIRED}
        gates={name:{"status":"REVIEWED","reviewer":"fixture",
                     "evidence_ids":["synthetic"]} for name in
               ("source_policy","identity","availability","schedule",
                "history","calibration","operational_signoff")}
        summary=certification_summary(
            readiness_checks=checks,
            release_manifest={"schema_version":"1.0","gates":gates})
        self.assertEqual(summary["status"],"HOLD")
        self.assertFalse(summary["live_forecast_approved"])
        self.assertFalse(summary["production_deployment_approved"])
        self.assertFalse(summary["historical_truth_independently_verified"])
        self.assertEqual(summary["release_manifest"]["status"],
                         "MANUAL_RELEASE_REVIEW_REQUIRED")
if __name__=="__main__":
    unittest.main()
