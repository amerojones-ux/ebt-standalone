import unittest
from ebt_calibration_audit import calibration_report
from ebt_certification import CertificationHold

def row(i,p=0.8,hit=True):
    return {"event_id":str(i),"player_id":"p","market":"points",
            "threshold":"10","predicted_probability":p,"hit":hit,
            "certified":True,"issued_at":"2026-10-28T10:00:00Z",
            "scheduled_start":"2026-10-28T23:00:00Z",
            "finalized_at":"2026-10-29T02:00:00Z"}

class CalibrationTests(unittest.TestCase):
    def test_brier_and_no_automatic_approval(self):
        result=calibration_report([row(1),row(2,0.2,False)],
                                  cutoff="2026-10-29T03:00:00Z",min_samples=2)
        self.assertAlmostEqual(result["brier_score"],0.04)
        self.assertTrue(result["minimum_sample_met"])
        self.assertFalse(result["calibration_approved"])
        self.assertFalse(result["outcome_truth_independently_verified"])
    def test_reject_duplicate_leakage_and_bad_probability(self):
        cases=([row(1),row(1)],
               [{**row(1),"issued_at":"2026-10-29T00:00:00Z"}],
               [row(1,float("nan"))],
               [{**row(1),"certified":False}])
        for case in cases:
            with self.subTest(case=case),self.assertRaises(CertificationHold):
                calibration_report(case,cutoff="2026-10-29T03:00:00Z")
if __name__=="__main__":
    unittest.main()
